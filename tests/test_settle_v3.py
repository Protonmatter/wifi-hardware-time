import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fractions import Fraction
import unittest
from research.clock_models.causal_provider import AvailableSample, conditions
from research.clock_models.settle import (INTERSECT_SPAN_S, SETTLEMENT_POLICY_VERSION, SETTLEMENT_POLICY_VERSION_V3,
                                          policy_version, settle, settle_replay)

HZ = 10_000_000


def at(qpc):
    return Fraction(9_000_000_000) + Fraction(qpc, 10) * Fraction(1_000_037, 1_000_000)


def sample(sequence, lower, width_ticks, delay=1):
    upper = lower + width_ticks
    return AvailableSample(sequence, int(at(lower + width_ticks // 3)), lower, upper, upper + delay)


class SettleV3Tests(unittest.TestCase):
    def test_policy_version_tracks_the_parameters(self):
        self.assertEqual(policy_version(), SETTLEMENT_POLICY_VERSION)
        self.assertEqual(policy_version(25, 0), SETTLEMENT_POLICY_VERSION_V3)
        self.assertEqual(policy_version(0, 10), SETTLEMENT_POLICY_VERSION_V3)
        self.assertEqual(INTERSECT_SPAN_S, 10)

    def test_defaults_reproduce_v2_exactly(self):
        samples = [sample(i, 1_000_000 + i * 20_000_000, 2_540) for i in range(8)]
        for event in range(30_000_000, 130_000_000, 3_333_333):
            v2 = settle(event, samples, samples[-1].available_qpc, HZ, affine=False)
            same = settle(event, samples, samples[-1].available_qpc, HZ, affine=False, jump_us=0, intersect_span_s=0)
            self.assertEqual(v2, same)
            self.assertEqual(v2.settlement_policy_version, SETTLEMENT_POLICY_VERSION)

    def test_far_narrow_window_tightens_a_near_wide_bracket(self):
        # Narrow 20-us windows 1 s out; the nearest neighbours have 1-ms windows.
        samples = [sample(1, 0, 200), sample(2, 9_000_000, 10_000), sample(3, 11_000_000, 10_000),
                   sample(4, 20_000_000, 200)]
        event = 10_000_000
        v2 = settle(event, samples, samples[-1].available_qpc, HZ, affine=False)
        v3 = settle(event, samples, samples[-1].available_qpc, HZ, affine=False, intersect_span_s=INTERSECT_SPAN_S)
        self.assertEqual((v2.earlier_sequence, v2.later_sequence), (2, 3))
        self.assertLess(v3.half_width_us, v2.half_width_us)
        # Sample 4 arrives after the bracket's cutoff, so it cannot narrow this result.
        self.assertEqual(v3.rate_bound_sequences, (1, 2, 3))
        self.assertLessEqual(v3.low_us, at(event))
        self.assertGreaterEqual(v3.high_us, at(event))
        self.assertEqual(v3.settlement_policy_version, SETTLEMENT_POLICY_VERSION_V3)

    def test_unavailable_or_out_of_span_samples_are_ignored(self):
        samples = [sample(1, 0, 200), sample(2, 9_000_000, 10_000), sample(3, 11_000_000, 10_000),
                   sample(4, 20_000_000, 200, delay=900_000_000)]
        event = 10_000_000
        cutoff = samples[2].available_qpc
        v3 = settle(event, samples, cutoff, HZ, affine=False, intersect_span_s=INTERSECT_SPAN_S)
        self.assertNotIn(4, v3.rate_bound_sequences)
        narrow = settle(event, samples, cutoff, HZ, affine=False, intersect_span_s=0)
        far = settle(event, samples[1:3], cutoff, HZ, affine=False, intersect_span_s=INTERSECT_SPAN_S)
        self.assertEqual(far.half_width_us, narrow.half_width_us)

    def test_jump_allowance_widens_and_is_recorded(self):
        samples = [sample(i, 1_000_000 + i * 20_000_000, 2_540) for i in range(6)]
        event = 50_000_000
        plain = settle(event, samples, samples[-1].available_qpc, HZ, affine=False)
        jumped = settle(event, samples, samples[-1].available_qpc, HZ, affine=False, jump_us=25)
        self.assertEqual(jumped.half_width_us, plain.half_width_us + 25)
        self.assertEqual(jumped.jump_us, 25)
        self.assertEqual(jumped.conditions[:4], conditions(25))

    def test_replay_reports_v3_parameters(self):
        samples = [sample(i, 1_000_000 + i * 20_000_000, 2_540) for i in range(8)]
        result = settle_replay(samples, HZ, HZ, affine=False, jump_us=25, intersect_span_s=INTERSECT_SPAN_S)
        self.assertEqual(result['settlement_policy_version'], SETTLEMENT_POLICY_VERSION_V3)
        self.assertEqual((result['jump_us'], result['intersect_span_s']), ('25', 10))
        self.assertEqual(result['states'], dict(settled=result['events']))


if __name__ == '__main__':
    unittest.main()
