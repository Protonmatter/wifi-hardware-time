import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import contextlib
import copy
from fractions import Fraction
import io
import json
import tempfile
import unittest
from unittest.mock import patch
from research.clock_models import sub_ms_acceptance
from research.clock_models.sample_screen import ContinuityBreak, Request, Sample, Screen
from research.clock_models.sub_ms_acceptance import ACCEPTANCE_VERSION, CRITERIA, evaluate, main

PASSING = {
    'causal-v3': dict(coverage_request_interval=0.9991, incompatible=[], whole_recording_continuity_eligible=True,
                  continuity_invalidations=[], durations_ticks=dict(acquiring='0', tracking='9', stale='0', invalid='0')),
    'settle-v3': dict(settle=dict(sub_millisecond_share=1.0, half_width_us=dict(median=199.1))),
    'wander': dict(wander=dict(model_half_width_us=dict(median=148.3), holdout_violations=0)),
}
TIMING = dict(completed=True, spacing_s=1.0, delivery_s=dict(median=0.006, p99=0.012, max=0.05),
              accepted_gap_s=dict(median=1.004, max=3.1), delivery_missing=0)


class AcceptanceTests(unittest.TestCase):
    def test_passing_run(self):
        result = evaluate(PASSING, TIMING)
        self.assertTrue(result['passed'])
        self.assertEqual([c['name'] for c in result['checks']], list(CRITERIA))

    def test_each_criterion_can_fail_alone(self):
        breaks = {
            'guaranteed_live_coverage_min': lambda r, t: r['causal-v3'].update(coverage_request_interval=0.93),
            'incompatible_max': lambda r, t: r['causal-v3'].update(incompatible=[dict(sequence=4)]),
            'settled_sub_ms_share_min': lambda r, t: r['settle-v3']['settle'].update(sub_millisecond_share=0.99),
            'settled_median_max_us': lambda r, t: r['settle-v3']['settle']['half_width_us'].update(median=281.0),
            'model_median_max_us': lambda r, t: r['wander']['wander']['model_half_width_us'].update(median=200.0),
            'model_holdout_violations_max': lambda r, t: r['wander']['wander'].update(holdout_violations=1),
            'delivery_p99_max_s': lambda r, t: t['delivery_s'].update(p99=1.9),
            'delivery_missing_max': lambda r, t: t.update(delivery_missing=2),
            'median_gap_ratio_max': lambda r, t: t['accepted_gap_s'].update(median=2.005),
        }
        self.assertEqual(set(breaks), set(CRITERIA))
        for name, mutate in breaks.items():
            replays, timing = copy.deepcopy(PASSING), copy.deepcopy(TIMING)
            mutate(replays, timing)
            result = evaluate(replays, timing)
            with self.subTest(criterion=name):
                self.assertFalse(result['passed'])
                self.assertEqual([c['name'] for c in result['checks'] if not c['passed']], [name])

    def test_acceptance_version_and_prerequisites_listed(self):
        result = evaluate(PASSING, TIMING)
        self.assertEqual(ACCEPTANCE_VERSION, 'wht/sub-ms-acceptance-v2')
        self.assertEqual(result['schema'], ACCEPTANCE_VERSION)
        self.assertEqual([p['name'] for p in result['prerequisites']],
                         ['run_completed', 'whole_recording_continuity_eligible', 'no_continuity_invalidations',
                          'no_invalid_time'])
        self.assertTrue(all(p['passed'] for p in result['prerequisites']))

    def test_each_prerequisite_fails_alone_while_numerical_checks_pass(self):
        breaks = {
            'run_completed': lambda r, t: t.update(completed=False),
            'whole_recording_continuity_eligible':
                lambda r, t: r['causal-v3'].update(whole_recording_continuity_eligible=False),
            'no_continuity_invalidations':
                lambda r, t: r['causal-v3'].update(continuity_invalidations=[dict(sequence=9)]),
            'no_invalid_time': lambda r, t: r['causal-v3']['durations_ticks'].update(invalid='49797460'),
        }
        for name, mutate in breaks.items():
            replays, timing = copy.deepcopy(PASSING), copy.deepcopy(TIMING)
            mutate(replays, timing)
            result = evaluate(replays, timing)
            with self.subTest(prerequisite=name):
                self.assertFalse(result['passed'])
                self.assertTrue(all(c['passed'] for c in result['checks']))
                self.assertEqual([p['name'] for p in result['prerequisites'] if not p['passed']], [name])

    def test_non_boolean_completed_is_not_accepted(self):
        self.assertFalse(evaluate(PASSING, dict(TIMING, completed=1))['passed'])

    def test_missing_prerequisite_inputs_are_rejected(self):
        for key in ('whole_recording_continuity_eligible', 'continuity_invalidations', 'durations_ticks'):
            replays = copy.deepcopy(PASSING)
            del replays['causal-v3'][key]
            with self.subTest(key=key), self.assertRaises(KeyError):
                evaluate(replays, TIMING)
        timing = copy.deepcopy(TIMING)
        del timing['completed']
        with self.assertRaises(KeyError):
            evaluate(PASSING, timing)

    def test_missing_review_interval_is_rejected(self):
        replays = copy.deepcopy(PASSING)
        del replays['causal-v3']['coverage_request_interval']
        with self.assertRaises(KeyError):
            evaluate(replays, TIMING)

    def test_empty_results_fail_instead_of_crashing(self):
        replays = copy.deepcopy(PASSING)
        replays['settle-v3']['settle'].update(half_width_us=None, sub_millisecond_share=None)
        result = evaluate(replays, TIMING)
        self.assertFalse(result['passed'])
        failed = {c['name'] for c in result['checks'] if not c['passed']}
        self.assertEqual(failed, {'settled_sub_ms_share_min', 'settled_median_max_us'})

    def test_todays_smoke_numbers_fail_on_delivery_cadence_and_width(self):
        today = copy.deepcopy(PASSING)
        today['causal-v3']['coverage_request_interval'] = 0.92884
        today['settle-v3']['settle']['half_width_us']['median'] = 280.429
        timing = dict(completed=True, spacing_s=1.0, delivery_s=dict(median=1.486, p99=1.999, max=2.167),
                      accepted_gap_s=dict(median=2.005, max=4.009), delivery_missing=0)
        failed = {c['name'] for c in evaluate(today, timing)['checks'] if not c['passed']}
        self.assertEqual(failed, {'guaranteed_live_coverage_min', 'settled_median_max_us', 'delivery_p99_max_s',
                                  'median_gap_ratio_max'})


HZ = 10_000_000


def tsf(qpc):
    return int(Fraction(9_000_000_000) + Fraction(qpc, 10) * Fraction(1_000_037, 1_000_000))


def run_cli(*, completed=True, break_last=False, count=40):
    """Drive main() with real replay_run and run_timing; only the data loaders are patched."""
    accepted, live, receipts, requests = [], [], [], []
    for i in range(1, count + 1):
        lower, upper = i * HZ, i * HZ + 2_540
        accepted.append(Sample(i, tsf(lower + 800), 0, lower, upper))
        live += [dict(kind='report', raw_timestamp=upper), dict(kind='delay', received_qpc=upper + 50_000)]
        receipts.append(dict(sequence=i, qpc_request_completed=upper + 10))
        requests.append(Request(i, lower, True))
    rejected, breaks = (), ()
    if break_last:  # the last report goes backwards; screening closes the accepted segment before it
        bad = accepted.pop()
        bad = Sample(bad.sequence, 100, 0, bad.lower_qpc, bad.upper_qpc)
        rejected = (('suspected_tsf_discontinuity', bad),)
        breaks = (ContinuityBreak(accepted[-1].sequence, bad.sequence, accepted[-1].tsf_us, bad.tsf_us,
                                  bad.lower_qpc),)
    screened = Screen(tuple(accepted), tuple((s.sequence, r) for r, s in rejected), 0, 0, 0, Fraction(count),
                      Fraction(0), rejected, continuity_closed=bool(breaks), continuity_breaks=breaks)
    data = dict(qpc_hz=HZ, records=[], requests=requests, completed=completed,
                identity=dict(folder='synthetic', session='synthetic'))
    lines = lambda path: live if path.name == 'live-observer.jsonl' else receipts
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder / 'session.json').write_text(json.dumps(dict(Plan=dict(spacing_s=1.0))), encoding='utf-8')
        out = io.StringIO()
        with patch('research.clock_models.replay_causal_provider.load_run', return_value=data), \
                patch('research.clock_models.replay_causal_provider.screen', return_value=screened), \
                patch('research.clock_models.replay_causal_provider._revision', return_value={}), \
                patch('research.clock_models.replay_causal_provider._lines', side_effect=lines), \
                patch.object(sub_ms_acceptance, 'load_run', return_value=data), \
                patch.object(sub_ms_acceptance, 'screen', return_value=screened), \
                patch.object(sub_ms_acceptance, '_lines', side_effect=lines), \
                patch.object(sys, 'argv', ['sub_ms_acceptance.py', str(folder)]), \
                contextlib.redirect_stdout(out):
            code = main()
    return code, json.loads(out.getvalue())


class AcceptanceEndToEndTests(unittest.TestCase):
    def test_clean_complete_run_passes(self):
        code, result = run_cli()
        self.assertEqual(code, 0)
        self.assertTrue(result['passed'])
        self.assertTrue(all(p['passed'] for p in result['prerequisites']))

    def test_incomplete_run_is_rejected(self):
        code, result = run_cli(completed=False)
        self.assertEqual(code, 2)
        self.assertFalse(result['passed'])
        self.assertEqual([p['name'] for p in result['prerequisites'] if not p['passed']], ['run_completed'])
        self.assertTrue(all(c['passed'] for c in result['checks']))

    def test_lifecycle_unclean_run_is_rejected(self):
        # load_run's lifecycle-to-completed path is covered by tests/test_persistent_receipts.py; this test
        # covers the acceptance half: completed=False rejects the run.
        code, result = run_cli(completed=False)
        self.assertEqual(code, 2)
        self.assertFalse(result['passed'])

    def test_continuity_break_after_a_passing_prefix_is_rejected(self):
        code, result = run_cli(break_last=True)
        self.assertEqual(code, 2)
        self.assertFalse(result['passed'])
        failed = {p['name'] for p in result['prerequisites'] if not p['passed']}
        self.assertEqual(failed, {'whole_recording_continuity_eligible', 'no_continuity_invalidations',
                                  'no_invalid_time'})
        self.assertTrue(all(c['passed'] for c in result['checks']))


def build_real(count=300, jump_from=None, jump_us=0, fail_from=None, final_extra_us=0, final_received=None):
    """Raw ETW-shaped records so the real screen() runs; only the file loaders are patched."""
    records, live, receipts, requests = [], [], [], []
    for i in range(1, count + 1):
        lower, upper = i * HZ, i * HZ + 2_540
        ok = fail_from is None or i < fail_from
        requests.append(Request(i, lower, ok))
        receipts.append(dict(sequence=i, qpc_request_completed=upper + 10))
        if not ok:
            continue
        value = tsf(lower + 800) + (jump_us if jump_from is not None and i >= jump_from else 0)
        if i == count:
            value += final_extra_us
        soc = 12345
        records += [dict(kind='command', raw_timestamp=lower + 100, vdev=0, action=4),
                    dict(kind='report', raw_timestamp=upper, vdev=0, tsf_raw=value),
                    dict(kind='soc_timer', raw_timestamp=upper, soc_timer_raw=soc),
                    dict(kind='delay', raw_timestamp=upper, vdev=0, tsf_delay_raw=(value - soc) & 0xffffffff)]
        received = final_received if i == count and final_received else upper + 50_000
        live += [dict(kind='report', raw_timestamp=upper), dict(kind='delay', received_qpc=received)]
    data = dict(qpc_hz=HZ, records=records, requests=requests, completed=True,
                identity=dict(folder='synthetic', session='synthetic'))
    return data, live, receipts


def run_real(**kwargs):
    data, live, receipts = build_real(**kwargs)
    lines = lambda path: live if path.name == 'live-observer.jsonl' else receipts
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder / 'session.json').write_text(json.dumps(dict(Plan=dict(spacing_s=1.0))), encoding='utf-8')
        out = io.StringIO()
        with patch('research.clock_models.replay_causal_provider.load_run', return_value=data), \
                patch('research.clock_models.replay_causal_provider._revision', return_value={}), \
                patch('research.clock_models.replay_causal_provider._lines', side_effect=lines), \
                patch.object(sub_ms_acceptance, 'load_run', return_value=data), \
                patch.object(sub_ms_acceptance, '_lines', side_effect=lines), \
                patch.object(sys, 'argv', ['sub_ms_acceptance.py', str(folder)]), \
                contextlib.redirect_stdout(out):
            code = main()
    return code, json.loads(out.getvalue())


class AcceptanceTailTests(unittest.TestCase):
    def failed(self, result):
        return [c['name'] for c in result['prerequisites'] + result['checks'] if not c['passed']]

    def test_clean_300_request_run_passes(self):
        code, result = run_real()
        self.assertEqual(code, 0, self.failed(result))
        self.assertGreater(result['replays']['causal-v3']['coverage_request_interval'], 0.995)

    def test_forward_tsf_jump_over_the_tail_is_rejected(self):
        code, result = run_real(jump_from=271, jump_us=1_000_000)
        self.assertEqual(code, 2)
        self.assertIn('guaranteed_live_coverage_min', self.failed(result))
        causal = result['replays']['causal-v3']
        self.assertGreater(causal['screen']['rejected'], 0)
        self.assertLess(causal['coverage_request_interval'], 0.995)

    def test_failed_requests_over_the_tail_are_rejected(self):
        code, result = run_real(fail_from=271)
        self.assertEqual(code, 2)
        self.assertIn('guaranteed_live_coverage_min', self.failed(result))

    def test_late_final_sample_violating_learned_rate_is_rejected(self):
        # The final accepted sample arrives after the last 0.1 s grid query but before the replay end.
        end = 300 * HZ + 5 * HZ
        code, result = run_real(final_extra_us=300, final_received=end - 1)
        self.assertEqual(code, 2)
        self.assertEqual(result['replays']['wander']['wander']['holdout_violations'], 1)
        self.assertEqual(self.failed(result), ['model_holdout_violations_max'])
        code, result = run_real(final_extra_us=300)
        self.assertEqual(code, 2)
        self.assertEqual(self.failed(result), ['model_holdout_violations_max'])


if __name__ == '__main__':
    unittest.main()
