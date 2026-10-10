"""Sub-millisecond acceptance for one recorded run under the v3 policies. Offline only.

Passing is conditional research evidence for the declared assumptions; it is not
calibrated AP/UTC accuracy and does not prove where inside its window a TSF was read.
"""
from __future__ import annotations

import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import argparse
from fractions import Fraction
import json
import statistics

from research.clock_models.analyze_bound_run import _lines, load_run
from research.clock_models.replay_causal_provider import V3_MODES, arrival_map, replay_run
from research.clock_models.sample_screen import screen

ACCEPTANCE_VERSION = 'wht/sub-ms-acceptance-v2'
CRITERIA = dict(
    guaranteed_live_coverage_min=0.995,   # causal-v3 coverage_review_interval (first to last sample availability)
    incompatible_max=0,                   # causal-v3 incompatible samples
    settled_sub_ms_share_min=1.0,         # settle-v3 sub_millisecond_share
    settled_median_max_us=250,            # settle-v3 rate-only median half-width
    model_median_max_us=180,              # learned-rate model median half-width
    model_holdout_violations_max=0,       # out-of-sample learned-rate failures
    delivery_p99_max_s=0.1,               # report delay-record receipt after report timestamp
    delivery_missing_max=0,                # accepted samples without a delay-record receipt
    median_gap_ratio_max=1.1,             # median accepted gap / requested spacing
)


def _p(values: list[float], share: Fraction) -> float:
    ordered = sorted(values)
    return ordered[max(0, -(-share.numerator * len(ordered) // share.denominator) - 1)]


def run_timing(folder: Path) -> dict:
    data = load_run(folder)
    hz = data['qpc_hz']
    accepted = list(screen(data['records'], data['requests'], hz).accepted)
    seen = arrival_map(_lines(folder / 'live-observer.jsonl'))
    delivery = [(seen[s.upper_qpc] - s.upper_qpc) / hz for s in accepted if s.upper_qpc in seen]
    gaps = [(b.lower_qpc - a.lower_qpc) / hz for a, b in zip(accepted, accepted[1:])]
    spacing = json.loads((folder / 'session.json').read_text(encoding='utf-8'))['Plan']['spacing_s']
    if not delivery or not gaps:
        raise ValueError('Run lacks delivery receipts or accepted gaps')
    return dict(completed=data['completed'], spacing_s=spacing, accepted=len(accepted), delivery_missing=len(accepted) - len(delivery),
                delivery_s=dict(median=statistics.median(delivery), p99=_p(delivery, Fraction(99, 100)),
                                max=max(delivery)),
                accepted_gap_s=dict(median=statistics.median(gaps), max=max(gaps)))


def evaluate(replays: dict, timing: dict, criteria: dict = CRITERIA) -> dict:
    causal, settle, model = replays['causal-v3'], replays['settle-v3']['settle'], replays['wander']['wander']
    observed = dict(
        guaranteed_live_coverage_min=causal['coverage_review_interval'],
        incompatible_max=len(causal['incompatible']),
        settled_sub_ms_share_min=settle['sub_millisecond_share'],
        settled_median_max_us=(settle['half_width_us'] or {}).get('median'),
        model_median_max_us=(model['model_half_width_us'] or {}).get('median'),
        model_holdout_violations_max=model['holdout_violations'],
        delivery_p99_max_s=timing['delivery_s']['p99'],
        delivery_missing_max=timing['delivery_missing'],
        median_gap_ratio_max=timing['accepted_gap_s']['median'] / timing['spacing_s'],
    )
    durations = causal['durations_ticks']
    prerequisites = [dict(name=name, value=value, passed=passed) for name, value, passed in (
        ('run_completed', timing['completed'], timing['completed'] is True),
        ('whole_recording_continuity_eligible', causal['whole_recording_continuity_eligible'],
         causal['whole_recording_continuity_eligible'] is True),
        ('no_continuity_invalidations', causal['continuity_invalidations'],
         len(causal['continuity_invalidations']) == 0),
        ('no_invalid_time', durations['invalid'], Fraction(durations['invalid']) == 0))]
    checks = []
    for name, limit in criteria.items():
        value = observed[name]
        passed = value is not None and (value >= limit if name.endswith('_min') else value <= limit)
        checks.append(dict(name=name, value=value, limit=limit, passed=passed))
    return dict(schema=ACCEPTANCE_VERSION, passed=all(c['passed'] for c in prerequisites + checks),
                prerequisites=prerequisites, checks=checks,
                scope='conditional research evidence under the declared v3 assumptions; not AP/UTC calibration')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    args = parser.parse_args()
    try:
        replays = {mode: replay_run(args.folder, mode) for mode in V3_MODES}
        result = evaluate(replays, run_timing(args.folder))
        print(json.dumps(dict(result, replays=replays), indent=2))
        return 0 if result['passed'] else 2
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f'Acceptance rejected: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
