"""Replay recorded runs through the causal TSF provider. Offline only.

Modes: retrospective (rate-only bound, samples on both sides of each gap), causal-etw (availability
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
from fractions import Fraction
import hashlib
import json
import subprocess

from research.clock_models.analyze_bound_run import _lines, load_run
from research.clock_models.causal_provider import CONDITIONS, AvailableSample, CausalProvider
from research.clock_models.rate_bound import retrospective_max_half_width
from research.clock_models.sample_screen import LISTEN_TIMEOUT_S, screen

ROOT = Path(__file__).resolve().parents[2]
SCREENING_LABEL = 'causal clock-model replay conditioned on offline sample screening'
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
           rate_prior_ppm: int = 200, threshold_us: int = 1_000) -> dict:
    """Feed ('accepted' | 'rejected', reason, AvailableSample) events in availability order."""
    provider = CausalProvider(qpc_hz, rate_prior_ppm, threshold_us)
    segments, t = [], start
    incompatible, rejected_checked, ingested = [], [], 0
    worst_before_next = None

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

    for kind, reason, item in sorted(events, key=lambda e: e[2].available_qpc):
        advance(item.available_qpc)
        if kind == 'accepted':
            if provider.count and provider.invalid_reason is None:
                width = provider.estimate(item.available_qpc).half_width_us
                worst_before_next = width if worst_before_next is None else max(worst_before_next, width)
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
    stale_runs = [min(s1, end) - max(s0, stale) for s0, s1, kind, stale in segments
                  if kind == 'model' and stale < s1]
    out = dict(label=SCREENING_LABEL, rate_prior_ppm=rate_prior_ppm, threshold_us=threshold_us,
               quantization='window widened by 1 QPC tick; TSF value widened by 1 us',
               declared_interval_qpc=[start, end],
               durations_ticks={k: str(v) for k, v in declared.items()},
               coverage_declared=round(float(declared['tracking'] / (end - start)), 6),
               samples_ingested=ingested, incompatible=incompatible, rejected_checked=rejected_checked,
               max_half_width_before_next_sample_us=None if worst_before_next is None else round(float(worst_before_next), 3),
               max_half_width_before_next_sample_exact=None if worst_before_next is None else str(worst_before_next),
               stale_interval_count=len(stale_runs),
               longest_stale_s=round(float(max(stale_runs) / qpc_hz), 6) if stale_runs else 0.0,
               conditions=list(CONDITIONS))
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
    meta = dict(schema='wht/causal-provider-replay-v1', mode=mode, run=data['identity']['folder'],
                session=data['identity']['session'], source=_revision(),
                inputs={name: _sha256(folder / name) for name in files if (folder / name).exists()},
                screening_policy='sample_screen.screen() over the complete recording',
                screen=dict(accepted=len(accepted), rejected=len(result.rejected),
                            rejected_with_reports=len(result.rejected_samples)))
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
    delay_seen = arrival_map(_lines(folder / 'live-observer.jsonl')) if mode == 'causal-arrival' else {}
    events = [('accepted', None, AvailableSample(s.sequence, s.tsf_us, s.lower_qpc, s.upper_qpc,
                                                  availability(s, mode, delay_seen, completed))) for s in accepted]
    for reason, s in result.rejected_samples:
        try:
            events.append(('rejected', reason, AvailableSample(s.sequence, s.tsf_us, s.lower_qpc, s.upper_qpc,
                                                               availability(s, mode, delay_seen, completed))))
        except (ValueError, KeyError):
            pass
    start = data['requests'][0].lower_qpc
    end = data['requests'][-1].lower_qpc + LISTEN_TIMEOUT_S * hz
    available = sorted(e[2].available_qpc for e in events if e[0] == 'accepted')
    meta['availability_rule'] = AVAILABILITY_RULES[mode]
    meta.update(replay(events, hz, start, end, (available[0], available[-1])))
    return meta


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('--mode', choices=('retrospective', 'causal-etw', 'causal-arrival', 'all'), default='all')
    args = parser.parse_args()
    try:
        modes = ('retrospective', 'causal-etw', 'causal-arrival') if args.mode == 'all' else (args.mode,)
        print(json.dumps({mode: replay_run(args.folder, mode) for mode in modes}, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f'Replay rejected: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
