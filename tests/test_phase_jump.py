import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fractions import Fraction
import unittest
from research.clock_models.bracket_bound import Window, window_bound
from research.clock_models.causal_provider import CONDITIONS, AvailableSample, CausalProvider, conditions
from research.clock_models.rate_bound import DEFAULT_JUMP_US, beacon_jump_allowance_us, envelope, rate_limits

HZ = 10_000_000
LIMITS = rate_limits(HZ)
BEACON = 1_024_000  # 102.4 ms in QPC ticks


def sawtooth(qpc):
    """Nominal-rate AP trajectory; the station runs 40 ppm fast and re-adopts the AP value every beacon."""
    return Fraction(9_000_000_000) + Fraction(qpc, 10) + Fraction(40, 1_000_000) * Fraction(qpc % BEACON, 10)


class PhaseJumpTests(unittest.TestCase):
    def test_declared_allowance_is_six_beacon_periods_at_forty_ppm_rounded_up(self):
        self.assertEqual(beacon_jump_allowance_us(), 25)  # 6 * 102.4 ms * 40 ppm = 24.576 us
        self.assertEqual(DEFAULT_JUMP_US, 25)
        self.assertEqual(beacon_jump_allowance_us(100, 1, 40), 5)
        for bad in ((0, 6, 40), (100, -1, 40), (100, 6, 4.0)):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                beacon_jump_allowance_us(*bad)

    def test_envelope_widens_each_side_by_the_allowance_only(self):
        base = envelope(1_000, 100, 200, 10_000, LIMITS)
        widened = envelope(1_000, 100, 200, 10_000, LIMITS, 25)
        self.assertEqual((widened[0], widened[1]), (base[0] - 25, base[1] + 25))
        with self.assertRaises(ValueError):
            envelope(1_000, 100, 200, 10_000, LIMITS, -1)

    def test_beacon_adoption_breaks_the_jump_free_envelope_but_not_the_widened_one(self):
        # Capture just before an adoption; query just after it. The station value
        # drops by about 4 us while the rate-only slack is far below 1 us.
        lower = 10 * BEACON - 120
        sample_tsf = int(sawtooth(lower))
        query = 10 * BEACON + 50
        low0, high0 = envelope(sample_tsf, lower, lower, query, LIMITS)
        low1, high1 = envelope(sample_tsf, lower, lower, query, LIMITS, 5)
        self.assertFalse(low0 <= sawtooth(query) <= high0)
        self.assertTrue(low1 <= sawtooth(query) <= high1)

    def test_provider_with_allowance_contains_the_sawtooth_and_states_it(self):
        provider = CausalProvider(HZ, jump_us=5)
        self.assertEqual(provider.conditions, conditions(5))
        self.assertNotEqual(conditions(5)[1], CONDITIONS[1])
        self.assertEqual(conditions(0), CONDITIONS)
        for i in range(30):
            lower = 5_000_000 + i * 7_777_777
            provider.ingest(AvailableSample(i, int(sawtooth(lower + 300)), lower, lower + 2_000, lower + 2_001))
            for query in (lower + 2_001, lower + 2_001 + BEACON // 3, lower + 7_000_000):
                estimate = provider.estimate(query)
                self.assertNotEqual(estimate.state, 'invalid')
                self.assertLessEqual(estimate.low_us, sawtooth(query))
                self.assertGreaterEqual(estimate.high_us, sawtooth(query))
                self.assertEqual(estimate.conditions, conditions(5))

    def test_affine_polygon_accepts_the_allowance(self):
        windows = [Window(int(sawtooth(q + 300)), q, q + 2_000) for q in range(1_000_000, 300_000_000, 9_999_991)]
        bound = window_bound(windows, HZ, jump_us=5)
        self.assertTrue(bound.feasible)
        for q in (50_000_000, 150_000_000):
            low, high = bound.predict(q)
            self.assertLessEqual(low, sawtooth(q))
            self.assertGreaterEqual(high, sawtooth(q))
        self.assertLessEqual(window_bound(windows, HZ).sample_count, bound.sample_count)
        with self.assertRaises(ValueError):
            window_bound(windows, HZ, jump_us=-1)


if __name__ == '__main__':
    unittest.main()
