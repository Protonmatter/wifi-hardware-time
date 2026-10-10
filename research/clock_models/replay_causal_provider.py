"""Replay recorded runs through the causal TSF provider. Offline only.

Modes: retrospective (rate-only bound, samples on both sides of each gap), settle (two-phase
timestamps: events on a 1 s grid settled once a later sample has arrived), causal-etw (availability
one tick after the report's ETW timestamp; reproduces the earlier review), and causal-arrival
(availability at the recorded reader boundary). Results are a causal clock-model replay conditioned
on offline sample screening: samples are qualified by sample_screen.screen() over the whole run.
"""
from __future__ import annotations

import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import argparse
from dataclasses import asdict
from fractions import Fraction
import hashlib
import json
import subprocess

from research.clock_models.analyze_bound_run import _lines, load_run
from research.clock_models.causal_provider import (CONDITIONS, PROVIDER_POLICY_VERSION, ROUNDING_ALLOWANCE_US,
                                                   AvailableSample, CausalProvider)
from research.clock_models.rate_bound import DEFAULT_JUMP_US, retrospective_max_half_width
from research.clock_models.sample_screen import LISTEN_TIMEOUT_S, screen
from research.clock_models.settle import INTERSECT_SPAN_S, settle_replay
from research.clock_models.replay_wander import replay_wander

ROOT = Path(__file__).resolve().parents[2]
SETTLE_STEP_S = 1
WANDER_PPM = 2
V3_MODES = ('settle-v3', 'causal-v3', 'wander')
SCREENING_LABEL = 'causal clock-model replay conditioned on offline sample screening'
ARRIVAL_ORDER_POLICY_VERSION = 'wht/arrival-order-v2'
AVAILABILITY_RULES = {
    'causal-etw': 'one QPC tick after the report ETW timestamp (reproduces the earlier review)',
    'causal-arrival': ('max of the reader-thread receipt of the delay record (the last record a sample needs) '
                       'and the request completion QPC; later queueing and ingestion latency not included'),
}


def arrival_map(live_records: list[dict]) -> dict[int, int]:
    """Report ETW timestamp -> reader receipt QPC of that group's delay record."""
    seen, pending = {}, None
    for record in live_records:
        if record.get('kind') == 'report':
            pending = record['raw_timestamp']
        elif record.get('kind') == 'delay' and pending is not None:
            seen[pending] = record['received_qpc']
            pending = None
    return seen


def availability(sample, mode: str, delay_seen: dict[int, int], completed: dict[int, int]) -> int:
    if mode == 'causal-etw':
        return sample.upper_qpc + 1
    if mode == 'causal-arrival':
        if sample.upper_qpc not in delay_seen:
            raise ValueError(f'No recorded delay-record receipt for sample {sample.sequence}')
        return max(delay_seen[sample.upper_qpc], completed[sample.sequence], sample.upper_qpc + 1)
    raise ValueError(f'Unknown mode {mode}')


def replay(events: list, qpc_hz: int, start: int, end: int, review_interval: tuple[int, int] | None = None,
           rate_prior_ppm: int = 200, threshold_us: int = 1_000, jump_us=0) -> dict:
    """Feed accepted/rejected samples and continuity diagnostics by their availability.

    Simultaneously available samples use capture order as a tie-break only. Skips
    preserve original availability, elapsed denominators and already-issued history.
    """
    provider = CausalProvider(qpc_hz, rate_prior_ppm, threshold_us, jump_us)
    segments, t = [], start
    incompatible, rejected_checked, ingested = [], [], 0
    late_history_skipped = []
    continuity_invalidations = []
    worst_before_next = None
    worst_uncertainty_before_next = None

    def advance(to: int) -> None:
        nonlocal t
        to = min(max(to, t), end)
        if to > t:
            if provider.invalid_reason is not None:
                segments.append((t, to, 'invalid', None))
            elif provider.count == 0:
                segments.append((t, to, 'acquiring', None))
            else:
                segments.append((t, to, 'model', provider.stale_from_qpc()))
            t = to

    for kind, reason, item in sorted(events, key=lambda e: (e[2].available_qpc, e[2].lower_qpc,
                                                          e[2].upper_qpc, e[2].sequence)):
        advance(item.available_qpc)
        if kind == 'continuity':
            provider.invalidate(f'sample {item.sequence}: suspected TSF discontinuity; epoch decision required')
            continuity_invalidations.append(dict(sequence=item.sequence, reason=reason,
                                                 available_qpc=item.available_qpc))
        elif kind == 'accepted':
            if provider.last_capture_end is not None and item.lower_qpc <= provider.last_capture_end:
                late_history_skipped.append(dict(sequence=item.sequence,
                    reason='capture_overlaps_or_precedes_last_ingested', lower_qpc=item.lower_qpc,
                    upper_qpc=item.upper_qpc, available_qpc=item.available_qpc,
                    last_ingested_capture_end_qpc=provider.last_capture_end))
                continue
            if provider.count and provider.invalid_reason is None:
                estimate = provider.estimate(item.available_qpc)
                width = estimate.half_width_us
                worst_before_next = width if worst_before_next is None else max(worst_before_next, width)
                uncertainty = estimate.uncertainty_us
                worst_uncertainty_before_next = (uncertainty if worst_uncertainty_before_next is None else
                                                 max(worst_uncertainty_before_next, uncertainty))
            result = provider.ingest(item)
            if result.compatible:
                ingested += 1
            else:
                incompatible.append(dict(sequence=item.sequence, reason=result.reason))
        else:
            try:
                compatible = provider.check(item).compatible
            except ValueError:
                compatible = None  # Not checkable against the ordered history.
            rejected_checked.append(dict(sequence=item.sequence, reason=reason, compatible=compatible))
    advance(end)

    def durations(lo: int, hi: int) -> dict[str, Fraction]:
        totals = dict(acquiring=Fraction(0), tracking=Fraction(0), stale=Fraction(0), invalid=Fraction(0))
        for s0, s1, kind, stale_from in segments:
            a, b = max(s0, lo), min(s1, hi)
            if b <= a:
                continue
            if kind == 'model':
                tracking = min(max(stale_from - a, 0), b - a)
                totals['tracking'] += tracking
                totals['stale'] += (b - a) - tracking
            else:
                totals[kind] += b - a
        return totals

    declared = durations(start, end)
    stale_intervals = []
    for s0, s1, kind, stale in segments:
        if kind != 'model' or stale >= s1:
            continue
        lo, hi = max(s0, stale), s1
        if stale_intervals and stale_intervals[-1][1] == lo:
            stale_intervals[-1] = (stale_intervals[-1][0], hi)
        else:
            stale_intervals.append((lo, hi))
    stale_runs = [hi - lo for lo, hi in stale_intervals]
    out = dict(label=SCREENING_LABEL, rate_prior_ppm=rate_prior_ppm, threshold_us=threshold_us,
               quantization='window widened by 1 QPC tick; TSF value widened by 1 us',
               uncertainty_rule='exact interval half-width plus conservative 1/2 us for integer-estimate rounding',
               rounding_allowance_us=str(ROUNDING_ALLOWANCE_US),
               declared_interval_qpc=[start, end],
               durations_ticks={k: str(v) for k, v in declared.items()},
               coverage_declared=round(float(declared['tracking'] / (end - start)), 6),
               samples_ingested=ingested, incompatible=incompatible, rejected_checked=rejected_checked,
               arrival_order_policy_version=ARRIVAL_ORDER_POLICY_VERSION,
               arrival_order_policy=('availability order; capture order breaks equal-availability ties; '
                                     'skip and account for historical captures without changing availability'),
               late_history_skipped=late_history_skipped,
               continuity_invalidations=continuity_invalidations,
               max_half_width_before_next_sample_us=None if worst_before_next is None else round(float(worst_before_next), 3),
               max_half_width_before_next_sample_exact=None if worst_before_next is None else str(worst_before_next),
               max_uncertainty_before_next_sample_us=(None if worst_uncertainty_before_next is None else
                                                     round(float(worst_uncertainty_before_next), 3)),
               max_uncertainty_before_next_sample_exact=(None if worst_uncertainty_before_next is None else
                                                        str(worst_uncertainty_before_next)),
               stale_interval_count=len(stale_runs),
               longest_stale_s=round(float(max(stale_runs) / qpc_hz), 6) if stale_runs else 0.0,
               provider_policy_version=PROVIDER_POLICY_VERSION, jump_us=str(jump_us),
               conditions=list(provider.conditions))
    if review_interval is not None:
        lo, hi = review_interval
        window = durations(lo, hi)
        out['review_interval_qpc'] = [lo, hi]
        out['coverage_review_interval'] = round(float(window['tracking'] / (hi - lo)), 6)
    return out


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def _revision() -> dict:
    try:
        head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True, timeout=20).stdout.strip()
        dirty = bool(subprocess.run(['git', 'status', '--porcelain', '--', 'research'], cwd=ROOT, capture_output=True,
                                    text=True, timeout=20).stdout.strip())
        return dict(commit=head or None, research_tree_modified=dirty)
    except (OSError, subprocess.SubprocessError):
        return dict(commit=None, research_tree_modified=None)


def replay_run(folder: Path, mode: str) -> dict:
    data = load_run(folder)
    hz = data['qpc_hz']
    result = screen(data['records'], data['requests'], hz)
    accepted = list(result.accepted)
    files = ('raw-timing.jsonl', 'requests.jsonl', 'live-observer.jsonl', 'run-result.json')
    # Preserve the existing availability formula; include new evidence inputs in provenance.
    if (folder / 'sampler-session.json').exists():
        files += ('sampler-session-start.json', 'sampler-session.json', 'sampler-schedule.jsonl')
    meta = dict(schema='wht/causal-provider-replay-v1', mode=mode, run=data['identity']['folder'],
                session=data['identity']['session'], source=_revision(),
                inputs={name: _sha256(folder / name) for name in files if (folder / name).exists()},
                screening_policy='sample_screen.screen() over the complete recording',
                screening_policy_version=result.policy_version,
                whole_recording_continuity_eligible=not result.continuity_closed,
                screened_segment_scope=('accepted prefix before suspected discontinuity' if result.continuity_closed
                                        else 'accepted samples over the complete recording'),
                screen=dict(accepted=len(accepted), rejected=len(result.rejected),
                            rejected_with_reports=len(result.rejected_samples),
                            continuity_closed=result.continuity_closed,
                            continuity_breaks=[asdict(item) for item in result.continuity_breaks]))
    if mode == 'retrospective':
        retro = retrospective_max_half_width(accepted, hz)
        meta.update(label='retrospective rate-only bound conditioned on offline sample screening',
                    max_half_width_us=round(float(retro['max_half_width_us']), 3),
                    max_half_width_exact=str(retro['max_half_width_us']),
                    worst_gap_s=round(float(retro['worst_gap_s']), 3), gap_count=retro['gap_count'],
                    rate_prior_ppm=retro['rate_prior_ppm'], quantization=retro['quantization'],
                    conditions=list(CONDITIONS))
        return meta
    completed = {r['sequence']: r['qpc_request_completed'] for r in _lines(folder / 'requests.jsonl')}
    if mode in ('settle-v3', 'wander'):
        delay_seen = arrival_map(_lines(folder / 'live-observer.jsonl'))
        items = [AvailableSample(s.sequence, s.tsf_us, s.lower_qpc, s.upper_qpc,
                                 availability(s, 'causal-arrival', delay_seen, completed)) for s in accepted]
        meta['availability_rule'] = AVAILABILITY_RULES['causal-arrival']
        if mode == 'settle-v3':
            meta.update(label='two-phase settled timestamps (v3) conditioned on offline sample screening',
                        settle=settle_replay(items, hz, step_qpc=SETTLE_STEP_S * hz, jump_us=DEFAULT_JUMP_US,
                                             intersect_span_s=INTERSECT_SPAN_S))
            return meta
        start = data['requests'][0].lower_qpc
        end = data['requests'][-1].lower_qpc + LISTEN_TIMEOUT_S * hz
        meta.update(wander=replay_wander(items, hz, start, end, wander_ppm=WANDER_PPM, jump_us=DEFAULT_JUMP_US))
        return meta
    if mode == 'settle':
        delay_seen = arrival_map(_lines(folder / 'live-observer.jsonl'))
        items = [AvailableSample(s.sequence, s.tsf_us, s.lower_qpc, s.upper_qpc,
                                 availability(s, 'causal-arrival', delay_seen, completed)) for s in accepted]
        retro = retrospective_max_half_width(accepted, hz)
        settled = settle_replay(items, hz, step_qpc=SETTLE_STEP_S * hz)
        meta.update(label='two-phase settled timestamps conditioned on offline sample screening',
                    availability_rule=AVAILABILITY_RULES['causal-arrival'],
                    quantization=retro['quantization'],
                    settle=settled,
                    settlement_policy_version=settled['settlement_policy_version'],
                    actual_settled_grid_max_half_width_us=settled['actual_settled_grid_max_half_width_us'],
                    actual_settled_grid_max_half_width_exact=settled['actual_settled_grid_max_half_width_exact'],
                    retrospective_consecutive_pair_max_half_width_us=round(float(retro['max_half_width_us']), 3),
                    retrospective_consecutive_pair_max_half_width_exact=str(retro['max_half_width_us']),
                    worst_settled_half_width_any_instant_us=round(float(retro['max_half_width_us']), 3),
                    worst_settled_half_width_any_instant_exact=str(retro['max_half_width_us']),
                    worst_settled_half_width_any_instant_scope=(
                        'retrospective consecutive-sample bound; '
                        'not a bound on earliest-available nonadjacent settlements caused by '
                        'overlapping capture windows or out-of-order arrival; legacy field aliases the '
                        'retrospective consecutive-pair maximum, not the actual settled grid maximum'))
        return meta
    jump_us = DEFAULT_JUMP_US if mode == 'causal-v3' else 0
    mode = 'causal-arrival' if mode == 'causal-v3' else mode
    delay_seen = arrival_map(_lines(folder / 'live-observer.jsonl')) if mode == 'causal-arrival' else {}
    events = [('accepted', None, AvailableSample(s.sequence, s.tsf_us, s.lower_qpc, s.upper_qpc,
                                                  availability(s, mode, delay_seen, completed))) for s in accepted]
    rejected_uncheckable = []
    for reason, s in result.rejected_samples:
        try:
            events.append(('rejected', reason, AvailableSample(s.sequence, s.tsf_us, s.lower_qpc, s.upper_qpc,
                                                               availability(s, mode, delay_seen, completed))))
        except (ValueError, KeyError) as error:
            if reason == 'suspected_tsf_discontinuity':
                raise ValueError(f'Cannot determine continuity break availability for sample {s.sequence}: {error}') from error
            rejected_uncheckable.append(dict(sequence=s.sequence, reason=reason,
                                             error=f'{type(error).__name__}: {error}'))
    # The backward comparison needs both observations. Keep rejection receipts
    # unchanged, and publish a separate diagnostic event once both are available.
    available_items = {item.sequence: item for _, _, item in events}
    continuity_diagnostics = []
    for diagnostic in result.continuity_breaks:
        try:
            previous, current = (available_items[diagnostic.previous_sequence], available_items[diagnostic.sequence])
        except KeyError as error:
            raise ValueError(f'Cannot determine continuity break availability for sample {diagnostic.sequence}') from error
        known_at = max(previous.available_qpc, current.available_qpc)
        continuity_diagnostics.append(dict(sequence=current.sequence, previous_sequence=previous.sequence,
                                           sample_available_qpc=current.available_qpc,
                                           previous_available_qpc=previous.available_qpc, available_qpc=known_at))
        events.append(('continuity', 'suspected_tsf_discontinuity',
                       AvailableSample(current.sequence, current.tsf_us, current.lower_qpc,
                                       current.upper_qpc, known_at)))
    meta['continuity_diagnostics'] = continuity_diagnostics
    start = data['requests'][0].lower_qpc
    end = data['requests'][-1].lower_qpc + LISTEN_TIMEOUT_S * hz
    available = sorted(e[2].available_qpc for e in events if e[0] == 'accepted')
    meta['availability_rule'] = AVAILABILITY_RULES[mode]
    meta['rejected_uncheckable'] = rejected_uncheckable
    review_interval = (available[0], available[-1]) if len(available) >= 2 and available[0] < available[-1] else None
    meta.update(replay(events, hz, start, end, review_interval, jump_us=jump_us))
    return meta


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('--mode', choices=('retrospective', 'settle', 'causal-etw', 'causal-arrival', 'all',
                                           *V3_MODES, 'v3'), default='all')
    args = parser.parse_args()
    try:
        modes = {'all': ('retrospective', 'settle', 'causal-etw', 'causal-arrival'), 'v3': V3_MODES}.get(
            args.mode, (args.mode,))
        print(json.dumps({mode: replay_run(args.folder, mode) for mode in modes}, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f'Replay rejected: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
