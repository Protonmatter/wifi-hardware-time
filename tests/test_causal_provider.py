import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fractions import Fraction
import math
import unittest
from research.clock_models.causal_provider import AvailableSample, CausalProvider

HZ = 10_000_000
NOMINAL = Fraction(1, 10)


def at(qpc):
    return 9_000_000_000 + qpc * NOMINAL


def sample(i, lower, delay=1, tsf=None, offset=700):
    upper = lower + 4_000
    value = int(at(lower + offset)) if tsf is None else tsf
    return AvailableSample(i, value, lower, upper, upper + delay)


class VariableClock:
    """Rate alternates between +150 and -150 ppm every 0.7 s."""

    rates = (NOMINAL * Fraction(1_000_150, 1_000_000), NOMINAL * Fraction(999_850, 1_000_000))

    def at(self, qpc):
        value, t, k = Fraction(9_000_000_000), 0, 0
        while t + 7_000_000 <= qpc:
            value += self.rates[k % 2] * 7_000_000
            t += 7_000_000
            k += 1
        return value + self.rates[k % 2] * (qpc - t)


class CausalProviderTests(unittest.TestCase):
    def test_acquiring_until_the_first_sample(self):
        provider = CausalProvider(HZ)
        self.assertEqual(provider.estimate(0).state, 'acquiring')
        provider.ingest(sample(1, 1_000_000))
        self.assertEqual(provider.estimate(1_005_000).state, 'tracking')

    def test_exact_stale_boundary_and_recovery(self):
        provider = CausalProvider(HZ)
        provider.ingest(sample(1, 1_000_000))
        boundary = provider.stale_from_qpc()
        before, after = math.ceil(boundary) - 1, math.ceil(boundary)
        self.assertEqual(provider.estimate(before).state, 'tracking')
        self.assertLess(provider.estimate(before).uncertainty_us, 1_000)
        self.assertEqual(provider.estimate(after).state, 'stale')
        self.assertGreaterEqual(provider.estimate(after).uncertainty_us, 1_000)
        provider.ingest(sample(2, after + 10))
        self.assertEqual(provider.estimate(after + 10 + 4_001).state, 'tracking')

    def test_incompatible_sample_latches_invalid_without_changing_the_model(self):
        provider = CausalProvider(HZ)
        provider.ingest(sample(1, 1_000_000))
        provider.ingest(sample(2, 21_000_000))
        frozen = provider.model()
        result = provider.ingest(sample(3, 41_000_000, tsf=int(at(41_000_700)) + 50_000))  # 50 ms ahead
        self.assertFalse(result.compatible)
        self.assertEqual(provider.model(), frozen)
        self.assertEqual(provider.estimate(41_010_000).state, 'invalid')
        provider.ingest(sample(4, 61_000_000))  # Still latched: later good samples do not clear it.
        self.assertEqual(provider.estimate(61_010_000).state, 'invalid')
        provider.reset()
        self.assertEqual(provider.estimate(61_010_000).state, 'acquiring')
        self.assertEqual(provider.estimate(61_010_000).epoch, 1)

    def test_delayed_delivery_stays_consistent(self):
        provider = CausalProvider(HZ)
        for i in range(5):
            self.assertTrue(provider.ingest(sample(i + 1, 1_000_000 + i * 30_000_000, delay=19_000_000)).compatible)

    def test_variable_rate_clock_is_consistent_and_contained(self):
        clock, provider = VariableClock(), CausalProvider(HZ)
        for i in range(8):
            lower = 1_000_000 + i * 20_000_000
            capture = lower + 700 + (i * 991) % 3_000
            item = AvailableSample(i + 1, int(clock.at(capture)), lower, lower + 4_000, lower + 4_001 + 15_000_000)
            self.assertTrue(provider.ingest(item).compatible)
            for q in range(item.available_qpc, item.available_qpc + 5_000_000, 999_999):
                estimate = provider.estimate(q)
                self.assertLessEqual(estimate.low_us, clock.at(q))
                self.assertGreaterEqual(estimate.high_us, clock.at(q))

    def test_queries_and_samples_cannot_travel_back_in_time(self):
        provider = CausalProvider(HZ)
        provider.ingest(sample(1, 1_000_000, delay=1_000))
        with self.assertRaises(ValueError):
            provider.estimate(1_000_000)  # before the sample became available
        with self.assertRaises(ValueError):
            provider.ingest(sample(2, 500_000))  # window before the previous sample
        with self.assertRaises(ValueError):
            provider.ingest(AvailableSample(3, 1, 30_000_000, 30_004_000, 30_004_000))  # available before window end

    def test_integer_estimate_uncertainty_covers_rounding(self):
        provider = CausalProvider(HZ)
        provider.ingest(sample(1, 1_000_000))
        estimate = provider.estimate(7_777_777)
        self.assertIsInstance(estimate.estimate_us, int)
        self.assertGreaterEqual(estimate.uncertainty_us, estimate.half_width_us)
        self.assertLessEqual(estimate.estimate_us - estimate.uncertainty_us, estimate.low_us)
        self.assertGreaterEqual(estimate.estimate_us + estimate.uncertainty_us, estimate.high_us)
        self.assertIn('causal capture', ' '.join(estimate.conditions))

    def test_rounding_expanded_uncertainty_controls_tracking_and_expiry(self):
        provider = CausalProvider(HZ)
        provider.ingest(sample(1, 1_000_000))
        # Query the final tick before half-width expiry. The old state
        # remained tracking even when rounding made the usable radius >= 1 ms.
        half_width_expiry = (2_000 - provider.c_high + provider.c_low) / (provider.b - provider.a)
        query = math.ceil(half_width_expiry) - 1
        estimate = provider.estimate(query)
        self.assertLess(estimate.half_width_us, 1_000)
        self.assertGreaterEqual(estimate.uncertainty_us, 1_000)
        self.assertEqual(estimate.state, 'stale')
        self.assertEqual(estimate.uncertainty_us, estimate.half_width_us + Fraction(1, 2))
        expiry = provider.stale_from_qpc()
        self.assertEqual((provider.c_high - provider.c_low + (provider.b - provider.a) * expiry) / 2
                         + Fraction(1, 2), 1_000)
        for qpc in (math.ceil(expiry) - 1, math.ceil(expiry), math.ceil(half_width_expiry)):
            current = provider.estimate(qpc)
            self.assertEqual(current.state == 'tracking', current.uncertainty_us < 1_000)

    def test_check_does_not_ingest(self):
        provider = CausalProvider(HZ)
        provider.ingest(sample(1, 1_000_000))
        frozen = provider.model()
        self.assertFalse(provider.check(sample(2, 21_000_000, tsf=1)).compatible)
        self.assertEqual(provider.model(), frozen)
        self.assertEqual(provider.estimate(21_010_000).state, 'tracking')

    def test_explicit_continuity_failure_latches(self):
        provider = CausalProvider(HZ)
        provider.ingest(sample(1, 1_000_000))
        provider.invalidate('association changed')
        estimate = provider.estimate(2_000_000)
        self.assertEqual((estimate.state, estimate.reason), ('invalid', 'association changed'))


if __name__ == '__main__':
    unittest.main()
