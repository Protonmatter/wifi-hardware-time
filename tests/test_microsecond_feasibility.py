import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import contextlib
import io
import json
import tempfile
import unittest
from research.clock_models import microsecond_feasibility as mf


QUALIFIED = dict(name='synthetic_qualified_path', known_read_point=True, bounded_pairing=True,
                 fresh=True, attributable=True)
FULL_BUDGET = dict(event_placement_us=1.0, pairing_us=1.0, rate_error_times_age_us=1.0,
                   asymmetry_us=1.0, epoch_changes_us=0.0, reference_us=1.0)


class ProfileTests(unittest.TestCase):
    def test_default_profile_is_predeclared(self):
        profile = mf.validate_profile(mf.DEFAULT_PROFILE)
        self.assertEqual(profile['target_us'], 10)
        self.assertEqual(profile['reference'], 'ap_tsf')
        self.assertEqual(set(mf.REQUIRED_CONDITIONS), set(profile['conditions']))

    def test_invalid_profiles_are_rejected(self):
        for bad in (dict(mf.DEFAULT_PROFILE, target_us=3), dict(mf.DEFAULT_PROFILE, target_us='10'),
                    dict(mf.DEFAULT_PROFILE, reference='host_qpc'),
                    dict(mf.DEFAULT_PROFILE, conditions=['idle']),
                    dict(mf.DEFAULT_PROFILE, scope='')):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                mf.validate_profile(bad)


class CaptureGateTests(unittest.TestCase):
    def test_baseline_candidates_are_all_killed(self):
        result = mf.baseline()
        self.assertFalse(result['passed'])
        self.assertEqual(result['verdict'], 'killed_at_gate1_no_qualified_capture_path')
        self.assertFalse(any(g['candidates'][i]['qualified']
                             for g in result['gates'][:1] for i in range(len(mf.CANDIDATE_BASELINE))))
        self.assertFalse(result['physical_bound_proven'])

    def test_candidate_requires_every_gate1_property(self):
        for missing in ('known_read_point', 'bounded_pairing', 'fresh', 'attributable'):
            candidate = dict(QUALIFIED, **{missing: False})
            with self.subTest(missing=missing):
                self.assertFalse(mf.evaluate_capture_path(candidate)['qualified'])
        self.assertTrue(mf.evaluate_capture_path(QUALIFIED)['qualified'])


class ErrorBudgetTests(unittest.TestCase):
    def test_unknown_terms_are_not_zero(self):
        result = mf.evaluate_error_budget(dict(FULL_BUDGET, reference_us=None), 10)
        self.assertEqual(result['unknown_terms'], ['reference_us'])
        self.assertIsNone(result['total_us'])
        self.assertFalse(result['within_target'])

    def test_complete_budget_sums_and_compares(self):
        result = mf.evaluate_error_budget(FULL_BUDGET, 10)
        self.assertEqual(result['total_us'], 5.0)
        self.assertTrue(result['within_target'])
        self.assertFalse(mf.evaluate_error_budget(
            dict(FULL_BUDGET, pairing_us=20.0), 10)['within_target'])

    def test_invalid_budget_term_is_rejected(self):
        with self.assertRaises(ValueError):
            mf.evaluate_error_budget(dict(FULL_BUDGET, pairing_us=-1.0), 10)


class QualificationTests(unittest.TestCase):
    def test_all_gates_pass_but_physical_bound_stays_false(self):
        result = mf.evaluate(mf.DEFAULT_PROFILE, [QUALIFIED], FULL_BUDGET, [1.0, -4.0, 9.0],
                             model_half_width_us=150.0)
        self.assertTrue(result['passed'])
        self.assertFalse(result['physical_bound_proven'])
        residuals = result['gates'][2]['residuals']
        self.assertEqual(residuals['max_us'], 9.0)
        self.assertEqual(result['model_half_width_us'], 150.0)

    def test_residual_over_target_fails_gate3(self):
        result = mf.evaluate(mf.DEFAULT_PROFILE, [QUALIFIED], FULL_BUDGET, [11.0])
        self.assertFalse(result['passed'])
        self.assertFalse(result['gates'][2]['passed'])

    def test_model_width_alone_cannot_pass(self):
        result = mf.evaluate(mf.DEFAULT_PROFILE, mf.CANDIDATE_BASELINE, FULL_BUDGET, [],
                             model_half_width_us=1.0)
        self.assertFalse(result['passed'])
        self.assertEqual(result['verdict'], 'killed_at_gate1_no_qualified_capture_path')

    def test_cli_baseline_exits_2_and_evidence_can_pass(self):
        original = sys.argv
        try:
            sys.argv = ['microsecond_feasibility.py']
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = mf.main()
            self.assertEqual(code, 2)
            self.assertEqual(json.loads(out.getvalue())['verdict'],
                             'killed_at_gate1_no_qualified_capture_path')
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'evidence.json'
                path.write_text(json.dumps(dict(profile=mf.DEFAULT_PROFILE, candidates=[QUALIFIED],
                                                error_budget=FULL_BUDGET, residuals_us=[2.0])),
                                encoding='utf-8')
                sys.argv = ['microsecond_feasibility.py', '--evidence', str(path)]
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    code = mf.main()
                self.assertEqual(code, 0)
                self.assertTrue(json.loads(out.getvalue())['passed'])
        finally:
            sys.argv = original


if __name__ == '__main__':
    unittest.main()
