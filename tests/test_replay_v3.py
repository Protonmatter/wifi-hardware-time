import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fractions import Fraction
import tempfile
import unittest
from unittest.mock import patch
from research.clock_models.causal_provider import PROVIDER_POLICY_VERSION, AvailableSample
from research.clock_models.rate_bound import DEFAULT_JUMP_US
from research.clock_models.replay_causal_provider import V3_MODES, replay_run
from research.clock_models.replay_wander import replay_wander
from research.clock_models.sample_screen import Request, Sample, Screen
from research.clock_models.settle import SETTLEMENT_POLICY_VERSION_V3
from research.clock_models.wander_provider import WANDER_POLICY_VERSION

HZ = 10_000_000


def tsf(qpc):
    return int(Fraction(9_000_000_000) + Fraction(qpc, 10) * Fraction(1_000_037, 1_000_000))


def available(count=30, spacing=10_000_000, width=2_540, delay=40_000):
    out = []
    for i in range(count):
        lower = 1_000_000 + i * spacing
        out.append(AvailableSample(i, tsf(lower + width // 3), lower, lower + width, lower + width + delay))
    return out


def recorded(count=40, spacing=10_000_000, delivery=50_000):
    accepted, live, receipts, requests = [], [], [], []
    for i in range(1, count + 1):
        lower = i * spacing
        upper = lower + 2_540
        accepted.append(Sample(i, tsf(lower + 800), 0, lower, upper))
        live.extend([dict(kind='report', raw_timestamp=upper), dict(kind='delay', received_qpc=upper + delivery)])
        receipts.append(dict(sequence=i, qpc_request_completed=upper + 10))
        requests.append(Request(i, lower, True))
    return accepted, live, receipts, requests


def run_mode(mode, **kwargs):
    accepted, live, receipts, requests = recorded(**kwargs)
    data = dict(qpc_hz=HZ, records=[], requests=requests, identity=dict(folder='synthetic', session='synthetic'))
    screened = Screen(tuple(accepted), (), 0, 0, 0, Fraction(len(accepted)), Fraction(0), ())
    with tempfile.TemporaryDirectory() as directory, \
            patch('research.clock_models.replay_causal_provider.load_run', return_value=data), \
            patch('research.clock_models.replay_causal_provider.screen', return_value=screened), \
            patch('research.clock_models.replay_causal_provider._revision', return_value={}), \
            patch('research.clock_models.replay_causal_provider._lines',
                  side_effect=lambda p: live if p.name == 'live-observer.jsonl' else receipts):
        return replay_run(Path(directory), mode)


class ReplayV3Tests(unittest.TestCase):
    def test_v3_mode_names(self):
        self.assertEqual(V3_MODES, ('settle-v3', 'causal-v3', 'wander'))

    def test_causal_v3_uses_arrival_availability_and_the_jump_allowance(self):
        v3, v2 = run_mode('causal-v3'), run_mode('causal-arrival')
        self.assertEqual(v3['jump_us'], str(DEFAULT_JUMP_US))
        self.assertEqual(v2['jump_us'], '0')
        self.assertEqual(v3['provider_policy_version'], PROVIDER_POLICY_VERSION)
        self.assertEqual(v3['availability_rule'], v2['availability_rule'])
        self.assertEqual(Fraction(v3['max_half_width_before_next_sample_exact']),
                         Fraction(v2['max_half_width_before_next_sample_exact']) + DEFAULT_JUMP_US)
        self.assertEqual(v3['incompatible'], [])

    def test_settle_v3_reports_its_policy(self):
        result = run_mode('settle-v3')
        self.assertEqual(result['settle']['settlement_policy_version'], SETTLEMENT_POLICY_VERSION_V3)
        self.assertEqual(result['settle']['states'], dict(settled=result['settle']['events']))

    def test_wander_mode_reports_holdout(self):
        result = run_mode('wander')['wander']
        self.assertEqual(result['policy_version'], WANDER_POLICY_VERSION)
        self.assertEqual(result['holdout_violations'], 0)
        self.assertLess(result['model_half_width_us']['median'], result['guaranteed_half_width_us']['median'])


class ReplayWanderTests(unittest.TestCase):
    def test_grid_replay_reports_both_layers_and_holdout(self):
        items = available(30)
        result = replay_wander(items, HZ, items[0].lower_qpc, items[-1].available_qpc, wander_ppm=2, jump_us=0)
        self.assertEqual(result['holdout_violations'], 0)
        self.assertGreater(result['holdout_checked'], 20)
        self.assertGreater(result['guaranteed_tracking_share'], 0.9)
        self.assertLess(result['model_half_width_us']['median'], result['guaranteed_half_width_us']['median'])
        self.assertEqual(result['queries'], sum(result['guaranteed_states'].values()))
        with self.assertRaises(ValueError):
            replay_wander(items, HZ, 5, 5, wander_ppm=2)

    def test_holdout_violations_surface_in_replay_on_rate_step(self):
        cutover_qpc = 400_000_000
        fast_rate = Fraction(1_000_187, 1_000_000)  # +187 ppm: inside the 200-ppm prior
        def step_tsf(qpc):
            if qpc < cutover_qpc:
                return int(Fraction(9_000_000_000) + Fraction(qpc, 10) * Fraction(1_000_037, 1_000_000))
            else:
                at_cutover = int(Fraction(9_000_000_000) + Fraction(cutover_qpc, 10) * Fraction(1_000_037, 1_000_000))
                return at_cutover + int(fast_rate * (qpc - cutover_qpc) // 10)
        items = []
        for i in range(60):
            lower = 1_000_000 + i * 10_000_000
            items.append(AvailableSample(i, step_tsf(lower + 2_540 // 3), lower, lower + 2_540, lower + 2_540 + 40_000))
        result = replay_wander(items, HZ, items[0].lower_qpc, items[-1].available_qpc, wander_ppm=1, jump_us=0)
        self.assertGreater(result['holdout_violations'], 0, 'Expected violations with wander_ppm=1 on rate step')
        self.assertTrue(len(result['holdout_violation_sequences']) > 0, 'Violations should be non-empty')
        # All violations should come from samples after the cutover
        for seq in result['holdout_violation_sequences']:
            self.assertGreater(seq, cutover_qpc // 10_000_000, 'Violations should be after cutover sample')
        # Guaranteed provider should never go invalid despite rate step
        self.assertEqual(result['guaranteed_states'].get('invalid', 0), 0, 'Guaranteed provider should not invalidate')


if __name__ == '__main__':
    unittest.main()
