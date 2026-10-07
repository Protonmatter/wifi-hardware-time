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


def _lines(path: Path) -> list[dict]:
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError(f'{path.name} exceeds size limit')
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def analyze_legacy(path: Path) -> dict:
    data = json.loads(path.read_text(encoding='utf-8'))
    validate_bundle(data)
    hz = data['manifest']['qpc_frequency_hz']

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
    hz = result['qpc_frequency_hz']
    if type(hz) is not int or hz <= 0:
        raise ValueError('Run lacks a positive QPC frequency')
    records = _lines(folder / 'raw-timing.jsonl')
    header = next((r for r in records if r.get('kind') == 'header'), None)
    if header is None or header['perf_frequency_hz'] != hz or header['events_lost'] or header['buffers_lost']:
        raise ValueError('Trace header missing, mismatched or lossy')
    receipts = _lines(folder / 'requests.jsonl')
    requests = [request_from_receipt(r['sequence'], r) for r in receipts]
    beacons = [Beacon(b['qpc_before'], b['ap_tsf_us']) for b in _lines(folder / 'beacons.jsonl')]
    return dict(qpc_hz=hz, records=records, requests=requests, beacons=beacons, completed=result.get('success') is True)


def analyze_run(folder: Path) -> dict:
    data = load_run(folder)
    result = screen(data['records'], data['requests'], data['qpc_hz'])
    reasons = Counter(reason for _, reason in result.rejected)
    return dict(schema='wht/tsf-host-bound-run-v1', run_completed=data['completed'],
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
        criteria = dict(
            run_completed=run['run_completed'],
            max_proven_error_below_1000us=widths is not None and Fraction(widths['max_exact']) < 1000,
            coverage_at_least_90pct=Fraction(analysis['coverage_exact']) >= Fraction(9, 10),
            rejected_at_most_1pct=info['request_count'] > 0 and Fraction(info['rejected_count'], info['request_count']) <= Fraction(1, 100),
            misattribution_below_0_05=Fraction(info['expected_misattributed_exact']) < Fraction(5, 100),
            beacon_checked_without_violation=beacon['checked'] > 0 and beacon['violations'] == 0)
        criteria['stretch_100us'] = widths is not None and Fraction(widths['max_exact']) <= 100
        verdict[name] = criteria
    verdict['passed'] = all(all(v for k, v in verdict[n].items() if k != 'stretch_100us') for n in ('idle', 'load'))
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
