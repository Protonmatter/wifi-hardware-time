"""Analyze a TSF bound run, or preview a legacy evidence bundle. Offline only.

Legacy bundles are previews: the old gate admitted them, but foreign-report
classification and own-loss accounting did not run live. Nothing here enables
a clock provider or claims accuracy against UTC.
"""
from __future__ import annotations

import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import argparse
from collections import Counter
from fractions import Fraction
import json

from research.clock_models.beacon_consistency import Beacon, check_beacons
from research.clock_models.bracket_bound import Window, coverage, sliding_bounds
from research.clock_models.sample_screen import Sample, freshness_filter, request_from_receipt, screen
from research.clock_models.soc_domain_test import soc_domain
from research.evidence.validate_research_bundle import validate_bundle

MAX_FILE_BYTES = 512 * 1024 * 1024
QPC_CLOCK_TYPE = 1  # ETW logfile ClientContext: 1 = QPC, 2 = system time, 3 = CPU cycle counter
REQUIRED_DURATION_S = 3600
UNVERIFIED_CONDITIONS = (
    'causal capture: each TSF was sampled after its request left the host and before its report was logged '
    '(a constant capture delay is invisible to the freshness screen)',
    'affine clock within each 60-second span: TSF follows one constant rate between samples',
    'station TSF equals access point TSF (802.11 synchronization; coarse beacon check only)',
)


def _f(value: Fraction) -> float:
    return round(float(value), 3)


def _rank(values: list, share: Fraction):
    ordered = sorted(values)
    return ordered[max(0, -(-share.numerator * len(ordered) // share.denominator) - 1)]


def summarize(samples: list[Sample], qpc_hz: int, beacons: tuple[Beacon, ...] | list[Beacon] = ()) -> dict:
    if not samples:
        return dict(sample_count=0, proven_half_width_us=None, coverage=0.0, coverage_exact='0',
                    infeasible_spans=[], soc_domain=None, beacon_check=check_beacons(list(beacons), []))
    windows = [Window(s.tsf_us, s.lower_qpc, s.upper_qpc) for s in samples]
    spans = sliding_bounds(windows, qpc_hz)
    widths = [s.max_half_width_us for s in spans if s.feasible]
    covered = coverage(spans, windows[0].lower_qpc, windows[-1].upper_qpc) if spans else Fraction(0)
    window_us = [Fraction((w.upper_qpc - w.lower_qpc) * 1_000_000, qpc_hz) for w in windows]
    spacing = [Fraction(b.lower_qpc - a.lower_qpc, qpc_hz) for a, b in zip(windows, windows[1:])]
    try:
        soc = soc_domain(samples)
    except ValueError as error:
        soc = dict(error=str(error))
    return dict(
        sample_count=len(samples), span_count=len(spans),
        infeasible_spans=[dict(start_qpc=s.start_qpc, end_qpc=s.end_qpc, samples=s.sample_count) for s in spans if not s.feasible],
        coverage=_f(covered), coverage_exact=str(covered),
        proven_half_width_us=dict(median=_f(_rank(widths, Fraction(1, 2))), p95=_f(_rank(widths, Fraction(95, 100))),
                                  max=_f(max(widths)), max_exact=str(max(widths))) if widths else None,
        window_width_us=dict(min=_f(min(window_us)), median=_f(_rank(window_us, Fraction(1, 2))), max=_f(max(window_us))),
        request_spacing_s=dict(median=_f(_rank(spacing, Fraction(1, 2))), max=_f(max(spacing))) if spacing else None,
        soc_domain=soc, beacon_check=check_beacons(list(beacons), spans))


def frequency(value: int | str) -> int:
    """Accept an integer or the evidence bundle's decimal-string QPC frequency."""
    if type(value) is str and value.isdigit():
        value = int(value)
    if type(value) is not int or value <= 0:
        raise ValueError('QPC frequency must be a positive integer')
    return value


def _lines(path: Path) -> list[dict]:
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError(f'{path.name} exceeds size limit')
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def analyze_legacy(path: Path) -> dict:
    data = json.loads(path.read_text(encoding='utf-8'))
    validate_bundle(data)
    hz = frequency(data['manifest']['qpc_frequency_hz'])

    def samples(action: int) -> list[Sample]:
        return [Sample(o['sequence'], int(o['tsf_raw']), int(o['soc_raw']), int(o['host_before_qpc']), int(o['report_qpc']))
                for o in data['observations'] if o['action'] == action]
    action4, rejected4 = freshness_filter(samples(4), hz)
    action3 = samples(3)
    _, rejected3 = freshness_filter(action3, hz)
    return dict(schema='wht/tsf-host-bound-legacy-preview-v1', bundle_id=data['manifest']['bundle_id'], preview=True,
                not_screened=['foreign-report classification', 'own-loss accounting'],
                action4=summarize(action4, hz), action4_freshness_rejections=len(rejected4),
                action3_freshness=dict(samples=len(action3), rejected=len(rejected3)))


def load_run(folder: Path) -> dict:
    result = json.loads((folder / 'run-result.json').read_text(encoding='utf-8'))
    hz = frequency(result['qpc_frequency_hz'])
    records = _lines(folder / 'raw-timing.jsonl')
    header = next((r for r in records if r.get('kind') == 'header'), None)
    if header is None or header['perf_frequency_hz'] != hz or header['events_lost'] or header['buffers_lost']:
        raise ValueError('Trace header missing, mismatched or lossy')
    if header.get('clock_type') != QPC_CLOCK_TYPE:
        raise ValueError('Trace clock is not QPC; raw timestamps cannot be used as QPC ticks')
    receipts = _lines(folder / 'requests.jsonl')
    requests = [request_from_receipt(r['sequence'], r) for r in receipts]
    # The cache can refresh during the call, so a returned beacon predates only the call's return.
    beacons = [Beacon(b['qpc_after'], b['ap_tsf_us']) for b in _lines(folder / 'beacons.jsonl')]
    session = json.loads((folder / 'session.json').read_text(encoding='utf-8')) if (folder / 'session.json').exists() else {}
    workload_path = folder / 'workload.json'
    workload = json.loads(workload_path.read_text(encoding='utf-8')) if workload_path.exists() else None
    # Run label only (campaign folder / condition): unique per run, without exposing local paths.
    resolved = folder.resolve()
    identity = dict(folder=f'{resolved.parent.name}/{resolved.name}', session=session.get('SessionName'),
                    condition=result.get('condition'),
                    duration_s=result.get('duration_s'),
                    workload=None if workload is None else {k: workload.get(k) for k in
                                                            ('stop_requested', 'download_stalled', 'downloaded_bytes')})
    return dict(qpc_hz=hz, records=records, requests=requests, beacons=beacons, completed=result.get('success') is True,
                identity=identity)


def analyze_run(folder: Path) -> dict:
    data = load_run(folder)
    result = screen(data['records'], data['requests'], data['qpc_hz'])
    reasons = Counter(reason for _, reason in result.rejected)
    return dict(schema='wht/tsf-host-bound-run-v1', run_completed=data['completed'], run=data['identity'],
                screen=dict(request_count=len(data['requests']), accepted_count=len(result.accepted),
                            rejected_count=len(result.rejected), rejected_by_reason=dict(reasons),
                            foreign_groups=result.foreign_groups, foreign_commands=result.foreign_commands,
                            own_losses=result.own_losses, duration_s=_f(result.duration_s),
                            expected_misattributed=_f(result.expected_misattributed),
                            expected_misattributed_exact=str(result.expected_misattributed)),
                analysis=summarize(list(result.accepted), data['qpc_hz'], data['beacons']),
                shared_clock_link='assumed from 802.11 station TSF adoption; coarse beacon check only',
                accuracy_vs_utc=None, clock_provider_enabled=False)


def evaluate(idle: dict, load: dict) -> dict:
    verdict = {}
    for name, run in (('idle', idle), ('load', load)):
        widths, info, analysis = run['analysis']['proven_half_width_us'], run['screen'], run['analysis']
        beacon = analysis['beacon_check']
        identity = run.get('run') or {}
        workload = identity.get('workload') or {}
        criteria = dict(
            run_completed=run['run_completed'],
            condition_recorded=identity.get('condition') == name,
            duration_at_least_3600s=type(identity.get('duration_s')) is int and identity['duration_s'] >= REQUIRED_DURATION_S,
            max_bound_below_1000us=widths is not None and Fraction(widths['max_exact']) < 1000,
            coverage_at_least_90pct=Fraction(analysis['coverage_exact']) >= Fraction(9, 10),
            rejected_at_most_1pct=info['request_count'] > 0 and Fraction(info['rejected_count'], info['request_count']) <= Fraction(1, 100),
            misattribution_below_0_05=Fraction(info['expected_misattributed_exact']) < Fraction(5, 100),
            beacon_checked_without_violation=beacon['checked'] > 0 and beacon['violations'] == 0)
        if name == 'load':
            criteria['workload_completed'] = (workload.get('stop_requested') is True and workload.get('download_stalled') is False
                                              and type(workload.get('downloaded_bytes')) is int and workload['downloaded_bytes'] > 0)
        criteria['stretch_100us'] = widths is not None and Fraction(widths['max_exact']) <= 100
        verdict[name] = criteria
    idle_id, load_id = idle.get('run') or {}, load.get('run') or {}
    verdict['distinct_runs'] = (idle_id.get('folder') is not None and idle_id.get('folder') != load_id.get('folder')
                                and idle_id.get('session') is not None and idle_id.get('session') != load_id.get('session'))
    verdict['passed'] = verdict['distinct_runs'] and all(
        all(v for k, v in verdict[n].items() if k != 'stretch_100us') for n in ('idle', 'load'))
    # The checks cannot establish these; a pass is a conditional bound, never a proven physical bound.
    verdict['conditional_on'] = list(UNVERIFIED_CONDITIONS)
    verdict['physical_bound_proven'] = False
    return verdict


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='mode', required=True)
    legacy = sub.add_parser('legacy', help='Preview saved evidence bundles')
    legacy.add_argument('bundles', type=Path, nargs='+')
    one = sub.add_parser('run', help='Analyze one run folder')
    one.add_argument('folder', type=Path)
    both = sub.add_parser('evaluate', help='Apply the predeclared pass/fail criteria')
    both.add_argument('idle', type=Path)
    both.add_argument('load', type=Path)
    args = parser.parse_args()
    try:
        if args.mode == 'legacy':
            output = [analyze_legacy(path) for path in args.bundles]
        elif args.mode == 'run':
            output = analyze_run(args.folder)
        else:
            idle, load = analyze_run(args.idle), analyze_run(args.load)
            output = dict(idle=idle, load=load, verdict=evaluate(idle, load))
        print(json.dumps(output, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f'Analysis rejected: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
