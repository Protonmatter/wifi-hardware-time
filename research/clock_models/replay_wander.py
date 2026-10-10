"""Grid replay of the guaranteed provider beside the learned-rate model. Offline only.

Queries run on a fixed QPC grid; samples are ingested in availability order before
any query at or after their availability. Each model check happens before ingest
(out of sample), so holdout violations measure the declared learned-rate assumption.
"""
from __future__ import annotations

from fractions import Fraction

from research.clock_models.causal_provider import AvailableSample
from research.clock_models.wander_provider import WANDER_POLICY_VERSION, WanderProvider

GRID_STEP_S = Fraction(1, 10)


def _quantiles(values: list[Fraction]) -> dict | None:
    if not values:
        return None
    ordered = sorted(values)
    pick = lambda share: ordered[max(0, -(-share.numerator * len(ordered) // share.denominator) - 1)]
    return dict(median=round(float(pick(Fraction(1, 2))), 3), p90=round(float(pick(Fraction(9, 10))), 3),
                p99=round(float(pick(Fraction(99, 100))), 3), max=round(float(ordered[-1]), 3))


def _diagnostic(item) -> dict:
    """Accept a mapping or named object with available_qpc and sequence."""
    get = item.__getitem__ if isinstance(item, dict) else lambda key: getattr(item, key)
    return dict(sequence=get('sequence'), available_qpc=get('available_qpc'))


def replay_wander(items: list[AvailableSample], qpc_hz: int, start: int, end: int, *, wander_ppm: int,
                  jump_us=0, rate_prior_ppm: int = 200, threshold_us: int = 1_000, continuity=()) -> dict:
    if not start < end:
        raise ValueError('Empty replay interval')
    provider = WanderProvider(qpc_hz, wander_ppm=wander_ppm, rate_prior_ppm=rate_prior_ppm,
                              threshold_us=threshold_us, jump_us=jump_us)
    order = sorted(items, key=lambda s: (s.available_qpc, s.lower_qpc, s.sequence))
    diagnostics = sorted((_diagnostic(d) for d in continuity), key=lambda d: (d['available_qpc'], d['sequence']))
    late_history_skipped, continuity_invalidations, diag_index = [], [], 0
    step = int(GRID_STEP_S * qpc_hz)
    states_g: dict[str, int] = {}
    states_m: dict[str, int] = {}
    widths_g, widths_m, holdout, index = [], [], [], 0
    for query in range(start, end, step):
        while True:
            diag_due = diag_index < len(diagnostics) and diagnostics[diag_index]['available_qpc'] <= query
            sample_due = index < len(order) and order[index].available_qpc <= query
            if diag_due and (not sample_due or diagnostics[diag_index]['available_qpc'] <= order[index].available_qpc):
                diagnostic = diagnostics[diag_index]
                diag_index += 1
                provider.guaranteed.invalidate(
                    f"sample {diagnostic['sequence']}: suspected TSF discontinuity; epoch decision required")
                continuity_invalidations.append(diagnostic)
                continue
            if not sample_due:
                break
            item = order[index]
            index += 1
            last_end = provider.guaranteed.last_capture_end
            if last_end is not None and item.lower_qpc <= last_end:
                late_history_skipped.append(dict(sequence=item.sequence,
                    reason='capture_overlaps_or_precedes_last_ingested', lower_qpc=item.lower_qpc,
                    upper_qpc=item.upper_qpc, available_qpc=item.available_qpc,
                    last_ingested_capture_end_qpc=last_end))
                continue
            verdict = provider.check_model(item)
            if verdict is not None:
                holdout.append(dict(sequence=item.sequence, compatible=verdict))
            provider.ingest(item)
        result = provider.estimate(query)
        states_g[result.guaranteed.state] = states_g.get(result.guaranteed.state, 0) + 1
        states_m[result.state] = states_m.get(result.state, 0) + 1
        if result.guaranteed.half_width_us is not None:
            widths_g.append(result.guaranteed.half_width_us)
        if result.half_width_us is not None:
            widths_m.append(result.half_width_us)
    # Diagnostics that become available at or after the replay end do not change any state.
    for diagnostic in diagnostics[diag_index:]:
        continuity_invalidations.append(diagnostic)
    total = sum(states_g.values())
    violations = [h['sequence'] for h in holdout if not h['compatible']]
    return dict(label='grid replay: guaranteed rate-only provider and labeled learned-rate model',
                policy_version=WANDER_POLICY_VERSION, wander_ppm=wander_ppm, jump_us=str(jump_us),
                grid_step_s=float(GRID_STEP_S), queries=total,
                guaranteed_states=states_g, model_states=states_m,
                guaranteed_tracking_share=round(states_g.get('tracking', 0) / total, 6),
                model_tracking_share=round(states_m.get('tracking', 0) / total, 6),
                guaranteed_half_width_us=_quantiles(widths_g), model_half_width_us=_quantiles(widths_m),
                holdout_checked=len(holdout), holdout_violations=len(violations),
                holdout_violation_sequences=violations[:50],
                late_history_skipped=late_history_skipped, continuity_invalidations=continuity_invalidations,
                conditions=list(provider.conditions))
