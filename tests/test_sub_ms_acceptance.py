import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import copy
import unittest
from research.clock_models.sub_ms_acceptance import CRITERIA, evaluate

PASSING = {
    'causal-v3': dict(coverage_declared=0.9991, incompatible=[]),
    'settle-v3': dict(settle=dict(sub_millisecond_share=1.0, half_width_us=dict(median=199.1))),
    'wander': dict(wander=dict(model_half_width_us=dict(median=148.3), holdout_violations=0)),
}
TIMING = dict(spacing_s=1.0, delivery_s=dict(median=0.006, p99=0.012, max=0.05),
              accepted_gap_s=dict(median=1.004, max=3.1), delivery_missing=0)


class AcceptanceTests(unittest.TestCase):
    def test_passing_run(self):
        result = evaluate(PASSING, TIMING)
        self.assertTrue(result['passed'])
        self.assertEqual([c['name'] for c in result['checks']], list(CRITERIA))

    def test_each_criterion_can_fail_alone(self):
        breaks = {
            'guaranteed_live_coverage_min': lambda r, t: r['causal-v3'].update(coverage_declared=0.93),
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

    def test_todays_smoke_numbers_fail_on_delivery_cadence_and_width(self):
        today = copy.deepcopy(PASSING)
        today['causal-v3']['coverage_declared'] = 0.92884
        today['settle-v3']['settle']['half_width_us']['median'] = 280.429
        timing = dict(spacing_s=1.0, delivery_s=dict(median=1.486, p99=1.999, max=2.167),
                      accepted_gap_s=dict(median=2.005, max=4.009), delivery_missing=0)
        failed = {c['name'] for c in evaluate(today, timing)['checks'] if not c['passed']}
        self.assertEqual(failed, {'guaranteed_live_coverage_min', 'settled_median_max_us', 'delivery_p99_max_s',
                                  'median_gap_ratio_max'})


if __name__ == '__main__':
    unittest.main()
