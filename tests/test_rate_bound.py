import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fractions import Fraction
import unittest
from research.clock_models.rate_bound import envelope, gap_max_half_width, rate_limits, retrospective_max_half_width
from research.clock_models.sample_screen import Sample

HZ = 10_000_000
NOMINAL = Fraction(1, 10)  # TSF microseconds per QPC tick at 10 MHz


class VariableClock:
    """TSF whose rate switches between +150 and -150 ppm of nominal every 0.7 s: inside a 200 ppm limit."""

    def __init__(self, start_tsf=9_000_000_000, period=7_000_000):
        self.start, self.period = start_tsf, period
        self.rates = (NOMINAL * Fraction(1_000_150, 1_000_000), NOMINAL * Fraction(999_850, 1_000_000))

    def at(self, qpc: int) -> Fraction:
        value, t, k = Fraction(self.start), 0, 0
        while t + self.period <= qpc:
            value += self.rates[k % 2] * self.period
            t += self.period
            k += 1
        return value + self.rates[k % 2] * (qpc - t)


def samples(clock, count=8, spacing=20_000_000):
    out = []
    for i in range(count):
        lower = 1_000_000 + i * spacing
        capture = lower + 700 + (i * 991) % 3_000
        out.append(Sample(i + 1, int(clock.at(capture)), 0, lower, lower + 4_000))
    return out


class RateBoundTests(unittest.TestCase):
    def test_rate_limits_are_exact(self):
        a, b = rate_limits(HZ, 200)
        self.assertEqual((a, b), (NOMINAL * Fraction(999_800, 1_000_000), NOMINAL * Fraction(1_000_200, 1_000_000)))

    def test_envelope_includes_quantization(self):
        a, b = rate_limits(HZ, 200)
        low, high = envelope(1_000, 0, 10_000, 10_001, (a, b))  # query at the widened window end
        self.assertEqual(low, 1_000)
        self.assertEqual(high, 1_001 + b * 10_001)

    def test_variable_rate_truth_stays_inside_both_neighbours(self):
        clock, limits = VariableClock(), rate_limits(HZ, 200)
        series = samples(clock)
        for earlier, later in zip(series, series[1:]):
            for q in range(earlier.lower_qpc, later.upper_qpc + 2, 1_234_567):
                lows, highs = zip(envelope(earlier.tsf_us, earlier.lower_qpc, earlier.upper_qpc, q, limits),
                                  envelope(later.tsf_us, later.lower_qpc, later.upper_qpc, q, limits))
                truth = clock.at(q)
                self.assertLessEqual(max(lows), truth)
                self.assertGreaterEqual(min(highs), truth)

    def test_gap_maximum_is_exact_against_a_dense_check(self):
        clock, limits = VariableClock(), rate_limits(HZ, 200)
        earlier, later = samples(clock, count=2)
        exact = gap_max_half_width(earlier, later, limits)
        dense = Fraction(0)
        for q in range(earlier.lower_qpc, later.upper_qpc + 2, 9_973):
            lows, highs = zip(envelope(earlier.tsf_us, earlier.lower_qpc, earlier.upper_qpc, q, limits),
                              envelope(later.tsf_us, later.lower_qpc, later.upper_qpc, q, limits))
            dense = max(dense, (min(highs) - max(lows)) / 2)
        self.assertGreaterEqual(exact, dense)
        self.assertLess(exact - dense, 2)  # within the grid step times the slope

    def test_retrospective_maximum_reports_the_worst_gap(self):
        clock = VariableClock()
        series = samples(clock, count=4)
        widest = Sample(5, int(clock.at(series[-1].lower_qpc + 70_000_000)), 0,
                        series[-1].lower_qpc + 70_000_000 - 700, series[-1].lower_qpc + 70_000_000 + 3_300)
        result = retrospective_max_half_width(series + [widest], HZ, 200)
        self.assertEqual(result['worst_gap_index'], 3)
        self.assertGreater(result['max_half_width_us'], gap_max_half_width(series[0], series[1], rate_limits(HZ, 200)))

    def test_inconsistent_neighbours_are_reported(self):
        first = Sample(1, 1_000_000, 0, 0, 1_000)
        second = Sample(2, 1_000_000 + 50_000, 0, 10_000, 11_000)  # 5 ms of TSF in 1 ms of QPC
        with self.assertRaises(ValueError):
            retrospective_max_half_width([first, second], HZ, 200)


if __name__ == '__main__':
    unittest.main()
