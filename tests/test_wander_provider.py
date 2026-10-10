import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fractions import Fraction
import unittest
from research.clock_models.causal_provider import AvailableSample
from research.clock_models.rate_bound import rate_limits
from research.clock_models.wander_provider import WANDER_POLICY_VERSION, WanderProvider, constant_rate_interval

HZ = 10_000_000
RATE = Fraction(1_000_037, 10_000_000)  # +37 ppm TSF us per QPC tick


def at(qpc, rate=RATE):
    return Fraction(9_000_000_000) + rate * qpc


def samples(count, spacing=10_000_000, width=2_540, delay=40_000, clock=at):
    out = []
    for i in range(count):
        lower = 1_000_000 + i * spacing
        out.append(AvailableSample(i, int(clock(lower + width // 3)), lower, lower + width, lower + width + delay))
    return out


class ConstantRateIntervalTests(unittest.TestCase):
    def test_interval_contains_the_true_rate_and_narrows_with_span(self):
        limits = rate_limits(HZ)
        short = constant_rate_interval(samples(5), limits)
        long = constant_rate_interval(samples(60), limits)
        for interval in (short, long):
            self.assertLessEqual(interval[0], RATE)
            self.assertGreaterEqual(interval[1], RATE)
        self.assertLess(long[1] - long[0], short[1] - short[0])

    def test_rate_change_inside_the_span_is_infeasible(self):
        def kink(qpc):
            return at(qpc) if qpc < 300_000_000 else at(300_000_000) + Fraction(1_000_150, 10_000_000) * (qpc - 300_000_000)
        self.assertIsNone(constant_rate_interval(samples(60, clock=kink), rate_limits(HZ)))

    def test_matches_the_affine_polygon_rate_projection(self):
        from research.clock_models.bracket_bound import Window, window_bound
        group = samples(8, spacing=7_000_003)
        bound = window_bound([Window(s.tsf_us, s.lower_qpc, s.upper_qpc) for s in group], HZ)
        rates = [rate for rate, _ in bound.vertices]
        self.assertEqual(constant_rate_interval(group, rate_limits(HZ)), (min(rates), max(rates)))


class WanderProviderTests(unittest.TestCase):
    def test_model_is_narrower_contains_truth_and_never_widens_the_guarantee(self):
        provider = WanderProvider(HZ, wander_ppm=2)
        for item in samples(40):
            self.assertIn(provider.check_model(item), (None, True))
            provider.ingest(item)
        query = samples(40)[-1].available_qpc + 15_000_000  # 1.5 s holdover
        result = provider.estimate(query)
        self.assertEqual(result.state, 'tracking')
        self.assertLess(result.half_width_us, result.guaranteed.half_width_us)
        self.assertGreaterEqual(result.low_us, result.guaranteed.low_us)
        self.assertLessEqual(result.high_us, result.guaranteed.high_us)
        self.assertLessEqual(result.low_us, at(query))
        self.assertGreaterEqual(result.high_us, at(query))
        self.assertEqual(result.policy_version, WANDER_POLICY_VERSION)
        self.assertIn('learned rate', provider.conditions[-1])

    def test_unavailable_until_min_samples(self):
        provider = WanderProvider(HZ, wander_ppm=2, min_samples=5)
        for item in samples(4):
            provider.ingest(item)
        result = provider.estimate(samples(4)[-1].available_qpc)
        self.assertEqual(result.state, 'unavailable')
        self.assertEqual(result.guaranteed.state, 'tracking')

    def test_holdout_flags_a_rate_step_that_the_guarantee_still_accepts(self):
        provider = WanderProvider(HZ, wander_ppm=1)
        fast = Fraction(1_000_187, 10_000_000)  # +187 ppm: inside the 200-ppm prior
        def step(qpc):
            return at(qpc) if qpc < 400_000_000 else at(400_000_000) + fast * (qpc - 400_000_000)
        verdicts = []
        for item in samples(60, clock=step):
            verdicts.append(provider.check_model(item))
            self.assertTrue(provider.ingest(item).compatible)
        self.assertIn(False, verdicts)

    def test_parameter_validation(self):
        for kwargs in (dict(wander_ppm=-1), dict(wander_ppm=201), dict(wander_ppm=2, span_s=0),
                       dict(wander_ppm=2, min_samples=1), dict(wander_ppm=1.5)):
            with self.subTest(**kwargs), self.assertRaises(ValueError):
                WanderProvider(HZ, **kwargs)


if __name__ == '__main__':
    unittest.main()
