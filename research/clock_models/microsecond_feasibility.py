"""Gated microsecond-class feasibility for TSF time. Offline evaluation only.

The current action-4 path yields conditional 100-microsecond-class intervals:
its capture window sets a floor near half of roughly 250 us, and no AP or UTC
calibration exists. This module predeclares what a microsecond-class claim
would require and evaluates supplied evidence against those gates. It never
turns model half-widths into accuracy and always reports
physical_bound_proven as False; only a live qualification against an
independent reference could change that, outside this offline evaluator.
"""
from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import argparse
import json
import math
import statistics

FEASIBILITY_VERSION = 'wht/microsecond-feasibility-v1'
TARGETS_US = (1, 10, 50)
REFERENCES = ('ap_tsf', 'peer_station', 'utc')
REQUIRED_CONDITIONS = ('idle', 'load')

DEFAULT_PROFILE = dict(target_us=10, reference='ap_tsf', conditions=list(REQUIRED_CONDITIONS),
                       scope='single adapter, driver and host until separately qualified')

# Documented status of each candidate on the qualified Qualcomm profile.
# Every entry currently fails at least one Gate 1 requirement; see
# docs/clock-models/packet-to-clock-map.md and docs/tsf/ evidence notes.
CANDIDATE_BASELINE = (
    dict(name='windows_hardware_cross_timestamp', known_read_point=False, bounded_pairing=False,
         fresh=False, attributable=False,
         blocker='No demonstrated INTERFACE_HARDWARE_CROSSTIMESTAMP path for this TSF source'),
    dict(name='ndis_packet_timestamp', known_read_point=False, bounded_pairing=False,
         fresh=False, attributable=False,
         blocker='NDIS timestamp capability queries fail on the qualified driver'),
    dict(name='beacon_tsf_with_local_rx', known_read_point=False, bounded_pairing=False,
         fresh=False, attributable=True,
         blocker='Cached beacon pair has unknown cache age and a different RX reference point'),
    dict(name='rx_descriptor_ppdu_words', known_read_point=False, bounded_pairing=False,
         fresh=False, attributable=False,
         blocker='Descriptor +0x60/+0x68 units, clock domain and packet identity are unknown'),
    dict(name='ftm_raw_event_times', known_read_point=False, bounded_pairing=False,
         fresh=False, attributable=False,
         blocker='Only aggregate RTT is exposed; raw t1 to t4 are not available'),
)

ERROR_BUDGET_TERMS = ('event_placement_us', 'pairing_us', 'rate_error_times_age_us',
                      'asymmetry_us', 'epoch_changes_us', 'reference_us')


def validate_profile(profile: dict) -> dict:
    if type(profile) is not dict:
        raise ValueError('Microsecond profile must be an object')
    target = profile.get('target_us')
    if type(target) not in (int, float) or isinstance(target, bool) or target not in TARGETS_US:
        raise ValueError(f'target_us must be one of {TARGETS_US}')
    if profile.get('reference') not in REFERENCES:
        raise ValueError(f'reference must be one of {REFERENCES}')
    conditions = profile.get('conditions')
    if type(conditions) not in (list, tuple) or not set(REQUIRED_CONDITIONS) <= set(conditions):
        raise ValueError(f'conditions must include {REQUIRED_CONDITIONS}')
    if not profile.get('scope'):
        raise ValueError('Microsecond profile requires a stated scope')
    return dict(target_us=target, reference=profile['reference'], conditions=list(conditions),
                scope=profile['scope'])


def evaluate_capture_path(candidate: dict) -> dict:
    """Gate 1: a fresh, attributable event time with a known read point and bounded QPC pairing."""
    if type(candidate) is not dict or not candidate.get('name'):
        raise ValueError('Capture candidate requires a name')
    checks = {key: candidate.get(key) is True
              for key in ('known_read_point', 'bounded_pairing', 'fresh', 'attributable')}
    return dict(name=candidate['name'], qualified=all(checks.values()), checks=checks,
                blocker=candidate.get('blocker'))


def evaluate_error_budget(budget: dict, target_us: float) -> dict:
    """Gate 2: every term bounded; unknown is not zero."""
    if type(budget) is not dict:
        raise ValueError('Error budget must be an object')
    unknown, total = [], 0.0
    for term in ERROR_BUDGET_TERMS:
        value = budget.get(term)
        if value is None:
            unknown.append(term)
        elif type(value) not in (int, float) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
            raise ValueError(f'Error budget term {term} must be finite and non-negative')
        else:
            total += float(value)
    return dict(terms=dict(budget), unknown_terms=unknown, total_us=None if unknown else total,
                within_target=not unknown and total <= target_us)


def _residual_stats(residuals) -> dict | None:
    if not residuals:
        return None
    absolute = [abs(float(value)) for value in residuals]
    return dict(count=len(absolute), median_us=statistics.median(absolute),
                max_us=max(absolute))


def evaluate(profile: dict, candidates, budget, residuals_us, model_half_width_us=None) -> dict:
    """Evaluate Gates 0 to 3. Residuals and model half-widths stay separate."""
    profile = validate_profile(profile)
    if residuals_us is not None and (type(residuals_us) not in (list, tuple) or
                                     any(type(v) not in (int, float) or isinstance(v, bool) or not math.isfinite(v)
                                         for v in residuals_us)):
        raise ValueError('residuals_us must be finite numbers')
    gate1 = [evaluate_capture_path(candidate) for candidate in candidates]
    qualified_paths = [item['name'] for item in gate1 if item['qualified']]
    gate2 = evaluate_error_budget(budget or {}, profile['target_us'])
    residuals = _residual_stats(residuals_us)
    gate3_passed = bool(qualified_paths) and gate2['within_target'] and residuals is not None \
        and residuals['max_us'] <= profile['target_us']
    gates = [dict(name='gate1_capture_path', passed=bool(qualified_paths), qualified_paths=qualified_paths,
                  candidates=gate1),
             dict(name='gate2_error_budget', passed=gate2['within_target'], **gate2),
             dict(name='gate3_residuals_vs_reference', passed=gate3_passed and gate2['within_target']
                  and bool(qualified_paths), residuals=residuals,
                  note='Measured residuals against the named reference; not model half-widths')]
    return dict(schema=FEASIBILITY_VERSION, profile=profile, gates=gates,
                model_half_width_us=model_half_width_us,
                passed=all(gate['passed'] for gate in gates),
                verdict=('candidate_microsecond_path_qualified_for_live_confirmation' if gate3_passed
                         else 'killed_at_gate1_no_qualified_capture_path' if not qualified_paths
                         else 'not_qualified'),
                physical_bound_proven=False,
                scope='offline evaluation of supplied evidence; no live hardware qualification')


def baseline() -> dict:
    return evaluate(DEFAULT_PROFILE, CANDIDATE_BASELINE, {}, [], model_half_width_us=dict(
        settled_v2_median_us=133.371, settled_v3_median_us=158.371, floor_us=127))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, help='JSON with profile, candidates, error_budget, residuals_us')
    args = parser.parse_args()
    try:
        if args.evidence is None:
            result = baseline()
        else:
            data = json.loads(args.evidence.read_text(encoding='utf-8'))
            result = evaluate(data.get('profile', DEFAULT_PROFILE), data.get('candidates', []),
                              data.get('error_budget', {}), data.get('residuals_us', []),
                              data.get('model_half_width_us'))
        print(json.dumps(result, indent=2))
        return 0 if result['passed'] else 2
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f'Microsecond feasibility rejected: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
