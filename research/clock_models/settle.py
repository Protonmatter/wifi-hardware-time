"""Settle event timestamps after the fact: the second phase of a two-phase TSF timestamp.

An event's QPC is recorded immediately; once a sample captured after the event has become available,
the event is bracketed and gets the rate-only bound from the samples on both sides (the guarantee)
plus a constant-rate best estimate from nearby samples (a stronger assumption). An event-overlapping
capture can narrow a complete bracket but never establish either side. Only samples available by
the reported settle time are used. Offline research code; contract in
docs/overview/2026-10-08-causal-provider-design.md.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from fractions import Fraction

from research.clock_models.bracket_bound import Window, window_bound
from research.clock_models.causal_provider import AvailableSample, conditions
from research.clock_models.rate_bound import envelope, rate_limits

AFFINE_HALF_SPAN_S = 30
AFFINE_CONDITION = 'best estimate only: assumes one constant rate within the surrounding 60-second span'
SETTLEMENT_POLICY_VERSION = 'wht/settlement-v2'
SETTLEMENT_POLICY_VERSION_V3 = 'wht/settlement-v3'
INTERSECT_SPAN_S = 10


def policy_version(jump_us=0, intersect_span_s: int = 0) -> str:
    """v2: nearest bracket pair only, no jump allowance. v3: any other setting."""
    return SETTLEMENT_POLICY_VERSION if jump_us == 0 and intersect_span_s == 0 else SETTLEMENT_POLICY_VERSION_V3


@dataclass(frozen=True)
class Settled:
    event_qpc: int
    state: str  # settled | pending | unbracketed | inconsistent
    low_us: Fraction | None = None
    high_us: Fraction | None = None
    midpoint_us: Fraction | None = None
    half_width_us: Fraction | None = None
    affine_low_us: Fraction | None = None
    affine_high_us: Fraction | None = None
    affine_half_width_us: Fraction | None = None
    settled_at_qpc: int | None = None
    earlier_sequence: int | None = None
    later_sequence: int | None = None
    conditions: tuple[str, ...] = conditions()
    settlement_policy_version: str = SETTLEMENT_POLICY_VERSION
    rate_bound_sequences: tuple[int, ...] = ()
    jump_us: int | Fraction = 0


def settle(event_qpc: int, samples: list[AvailableSample], now_qpc: int, qpc_hz: int,
           rate_prior_ppm: int = 200, affine: bool = True, jump_us=0, intersect_span_s: int = 0) -> Settled:
    """Settle one event using only samples available at now_qpc. Samples are one epoch, in capture order.

    intersect_span_s > 0 also intersects the envelope of every sample available by the
    reported cutoff whose window lies within that many seconds of the event (v3).
    """
    if type(event_qpc) is not int or type(now_qpc) is not int:
        raise ValueError('Event and settle times must be integer QPC values')
    if type(intersect_span_s) is not int or intersect_span_s < 0:
        raise ValueError('Intersection span must be a non-negative integer number of seconds')
    version, stated = policy_version(jump_us, intersect_span_s), conditions(jump_us)
    if any(b.lower_qpc <= a.upper_qpc for a, b in zip(samples, samples[1:])):
        raise ValueError('Samples must be in capture order with non-overlapping windows')
    # The quantized window includes its extra QPC tick; a window straddling
    # the event cannot prove either side of the bracket.
    available = [s for s in samples if s.available_qpc <= now_qpc]
    before = [s for s in available if s.upper_qpc + 1 <= event_qpc]
    if not before:
        return Settled(event_qpc, 'unbracketed', conditions=stated, settlement_policy_version=version,
                       jump_us=jump_us)
    earlier = before[-1]
    later = next((s for s in available if s.lower_qpc > event_qpc), None)
    if later is None:
        return Settled(event_qpc, 'pending', earlier_sequence=earlier.sequence, conditions=stated,
                       settlement_policy_version=version, jump_us=jump_us)
    limits = rate_limits(qpc_hz, rate_prior_ppm)
    lo1, hi1 = envelope(earlier.tsf_us, earlier.lower_qpc, earlier.upper_qpc, event_qpc, limits, jump_us)
    lo2, hi2 = envelope(later.tsf_us, later.lower_qpc, later.upper_qpc, event_qpc, limits, jump_us)
    low, high = max(lo1, lo2), min(hi1, hi2)
    settled_at = max(later.available_qpc, earlier.available_qpc)
    # An overlapping capture cannot establish a bracket side. Once a bracket
    # exists, its envelope can narrow the result only if already available at
    # the reported cutoff (which may be earlier than this call's now_qpc).
    overlaps = [s for s in available if s.lower_qpc <= event_qpc < s.upper_qpc + 1
                and s.available_qpc <= settled_at]
    span = intersect_span_s * qpc_hz
    # v3: every other sample available by the cutoff is valid evidence too; a far
    # narrow window can beat a near wide one. The span only bounds the work.
    extra = [s for s in available if span and s.available_qpc <= settled_at
             and s not in (earlier, later) and s not in overlaps
             and event_qpc - span <= s.upper_qpc and s.lower_qpc <= event_qpc + span]
    for sample in (*overlaps, *extra):
        lo, hi = envelope(sample.tsf_us, sample.lower_qpc, sample.upper_qpc, event_qpc, limits, jump_us)
        low, high = max(low, lo), min(high, hi)
    # Capture order: identical to v2 when there are no extra samples.
    sequences = tuple(s.sequence for s in sorted([earlier, *overlaps, *extra, later], key=lambda s: s.lower_qpc))
    if low > high:
        return Settled(event_qpc, 'inconsistent', earlier_sequence=earlier.sequence, later_sequence=later.sequence,
                       rate_bound_sequences=sequences, conditions=stated, settlement_policy_version=version,
                       jump_us=jump_us)
    estimate = (_affine(event_qpc, samples, settled_at, qpc_hz, rate_prior_ppm, jump_us) if affine
                else (None, None, None))
    return Settled(event_qpc, 'settled', low, high, (low + high) / 2, (high - low) / 2, *estimate,
                   settled_at_qpc=settled_at,
                   earlier_sequence=earlier.sequence, later_sequence=later.sequence,
                   rate_bound_sequences=sequences,
                   conditions=stated + (AFFINE_CONDITION,), settlement_policy_version=version,
                   jump_us=jump_us)


def _affine(event_qpc: int, samples: list[AvailableSample], now_qpc: int, qpc_hz: int, rate_prior_ppm: int,
            jump_us=0):
    span = AFFINE_HALF_SPAN_S * qpc_hz
    members = [s for s in samples if s.available_qpc <= now_qpc
               and event_qpc - span <= s.lower_qpc and s.upper_qpc <= event_qpc + span]
    if len(members) < 3 or not any(s.upper_qpc < event_qpc for s in members) or not any(s.lower_qpc > event_qpc for s in members):
        return None, None, None
    bound = window_bound([Window(s.tsf_us, s.lower_qpc, s.upper_qpc) for s in members], qpc_hz, rate_prior_ppm,
                         jump_us)
    if not bound.feasible:
        return None, None, None
    low, high = bound.predict(event_qpc)
    return low, high, (high - low) / 2


def _quantiles(values: list, shares=(Fraction(1, 2), Fraction(9, 10), Fraction(99, 100))) -> dict:
    ordered = sorted(values)
    pick = lambda share: ordered[max(0, -(-share.numerator * len(ordered) // share.denominator) - 1)]
    out = {f'p{int(share * 100)}' if share != Fraction(1, 2) else 'median': round(float(pick(share)), 3) for share in shares}
    out['max'] = round(float(ordered[-1]), 3)
    return out


def settle_replay(samples: list[AvailableSample], qpc_hz: int, step_qpc: int, affine: bool = True,
                  rate_prior_ppm: int = 200, jump_us=0, intersect_span_s: int = 0) -> dict:
    """Settle events on a regular grid between the first and last capture, each at its earliest settle time."""
    if type(step_qpc) is not int or step_qpc <= 0:
        raise ValueError('Replay step must be a positive integer')
    if not samples:
        raise ValueError('Need samples')
    states, waits, widths, affine_widths = Counter(), [], [], []
    event = samples[0].upper_qpc + 1
    while event < samples[-1].lower_qpc:
        # Capture order need not be arrival order. The first complete bracket
        # exists once any true-before and any true-after sample are available.
        earlier_at = min(s.available_qpc for s in samples if s.upper_qpc + 1 <= event)
        later_at = min(s.available_qpc for s in samples if s.lower_qpc > event)
        now = max(earlier_at, later_at)
        result = settle(event, samples, now, qpc_hz, rate_prior_ppm, affine, jump_us, intersect_span_s)
        states[result.state] += 1
        if result.state == 'settled':
            waits.append(Fraction(result.settled_at_qpc - event, qpc_hz))
            widths.append(result.half_width_us)
            if result.affine_half_width_us is not None:
                affine_widths.append(result.affine_half_width_us)
        event += step_qpc
    count = sum(states.values())
    return dict(events=count, step_s=round(step_qpc / qpc_hz, 6), states=dict(states),
                settlement_policy_version=policy_version(jump_us, intersect_span_s),
                jump_us=str(jump_us), intersect_span_s=intersect_span_s,
                actual_settled_grid_max_half_width_us=round(float(max(widths)), 3) if widths else None,
                actual_settled_grid_max_half_width_exact=str(max(widths)) if widths else None,
                wait_s=_quantiles(waits) if waits else None,
                half_width_us=_quantiles(widths) if widths else None,
                affine_half_width_us=_quantiles(affine_widths) if affine_widths else None,
                affine_estimate_count=len(affine_widths),
                affine_estimate_share=round(len(affine_widths) / count, 6) if count else None,
                sub_millisecond_share=round(sum(1 for w in widths if w < 1_000) / count, 6) if count else None,
                rate_prior_ppm=rate_prior_ppm, conditions=list(conditions(jump_us)) + [AFFINE_CONDITION])
