import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fractions import Fraction
import unittest
from research.clock_models.bracket_bound import Window, window_bound, sliding_bounds, coverage

HZ = 10_000_000
RATE = Fraction(999_960, 10_000_000)  # station TSF 40 ppm slow, in us per QPC tick


def truth(qpc):
    return 5_000_000_000 + qpc * RATE


def windows(count, spacing=20_000_000, jump_after=None, jump_us=0):
    out = []
    for i in range(count):
        lower = 1_000_000 + i * spacing
        capture = lower + 1_000 + (i * 37) % 1_500
        tsf = int(truth(capture)) + (jump_us if jump_after is not None and i > jump_after else 0)
        out.append(Window(tsf, lower, lower + 5_000))
    return out


class BracketBoundTests(unittest.TestCase):
    def test_truth_lies_inside_every_prediction(self):
        sample = windows(10)
        bound = window_bound(sample, HZ)
        self.assertTrue(bound.feasible)
        for qpc in range(sample[0].lower_qpc, sample[-1].upper_qpc, 7_777_777):
            low, high = bound.predict(qpc)
            self.assertLessEqual(low, truth(qpc))
            self.assertGreaterEqual(high, truth(qpc))

    def test_single_window_half_width_is_exact(self):
        bound = window_bound([Window(5_000_000, 0, 10_000)], HZ)
        expected = (1 + Fraction(100_020, 1_000_000) * 10_001) / 2
        self.assertEqual(bound.half_width_us(5_000), expected)

    def test_inconsistent_windows_are_infeasible(self):
        bound = window_bound([Window(1_000, 0, 100), Window(51_000, 10_000, 10_100)], HZ)
        self.assertFalse(bound.feasible)
        with self.assertRaises(ValueError):
            bound.predict(0)

    def test_invalid_input_is_rejected(self):
        with self.assertRaises(ValueError):
            Window(1, 10, 5)
        with self.assertRaises(ValueError):
            window_bound([], HZ)
        with self.assertRaises(ValueError):
            window_bound([Window(1, 0, 1)], 0)

    def test_rate_interval_contains_truth(self):
        low, high = window_bound(windows(10), HZ).rate_ppm()
        self.assertLessEqual(low, -40)
        self.assertGreaterEqual(high, -40)

    def test_sliding_spans_are_sub_millisecond_and_cover_the_run(self):
        sample = windows(30)
        spans = sliding_bounds(sample, HZ)
        self.assertTrue(spans)
        self.assertTrue(all(s.feasible and s.max_half_width_us < 1000 for s in spans))
        self.assertGreaterEqual(coverage(spans, sample[0].lower_qpc, sample[-1].upper_qpc), Fraction(9, 10))

    def test_tsf_jump_makes_spans_infeasible(self):
        spans = sliding_bounds(windows(30, jump_after=14, jump_us=5_000), HZ)
        self.assertTrue(any(not s.feasible for s in spans))


if __name__ == '__main__':
    unittest.main()
