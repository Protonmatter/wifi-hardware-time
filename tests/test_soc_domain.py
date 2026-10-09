import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fractions import Fraction
import unittest
from research.clock_models.sample_screen import Sample
from research.clock_models.soc_domain_test import soc_domain


def series(drift_ppm, count=61, spacing=600_000_000):
    out = []
    for i in range(count):
        lower = 1_000 + i * spacing
        capture = lower + 2_000
        soc = int(Fraction(capture, 10) * (1 + Fraction(drift_ppm, 1_000_000)))
        out.append(Sample(i + 1, 0, soc, lower, lower + 5_000))
    return out


class SocDomainTests(unittest.TestCase):
    def test_equal_integer_bins_are_compatible_with_nominal_motion(self):
        samples = [Sample(i + 1, 0, 0, qpc, qpc) for i, qpc in enumerate((0, 4, 9))]
        result = soc_domain(samples)
        self.assertTrue(result['compatible_with_qpc_domain'])
        self.assertIsNone(result['rate_interval']['upper'])

    def test_long_constant_count_rejects_nominal_without_claiming_no_affine_fit(self):
        samples = [Sample(i + 1, 0, 0, qpc, qpc) for i, qpc in enumerate((0, 9, 20))]
        result = soc_domain(samples)
        self.assertFalse(result['compatible_with_qpc_domain'])
        self.assertFalse(result['rate_interval_contains_nominal'])
        self.assertEqual(result['fixed_rate_gap_qpc_ticks'], 9)

    def test_integer_soc_bins_contain_actual_shared_domain(self):
        # Continuous SoC values 10, 20.1, 30.2 really equal QPC / 10.
        samples = [Sample(i + 1, 0, soc, qpc, qpc)
                   for i, (soc, qpc) in enumerate(((10, 100), (20, 201), (30, 302)))]
        result = soc_domain(samples)
        self.assertTrue(result['fixed_rate_feasible'])
        self.assertTrue(result['rate_interval_contains_nominal'])
        self.assertTrue(result['compatible_with_qpc_domain'])
        self.assertEqual(result['fixed_rate_offset_interval_qpc_ticks'], {'lower': -8, 'upper': 1})
        self.assertFalse(result['shared_oscillator_proven'])

    def test_quantization_does_not_absorb_large_fixed_rate_disagreement(self):
        samples = [Sample(i + 1, 0, soc, qpc, qpc)
                   for i, (soc, qpc) in enumerate(((10, 100), (20, 201), (30, 330)))]
        result = soc_domain(samples)
        self.assertFalse(result['compatible_with_qpc_domain'])
        self.assertGreater(result['fixed_rate_gap_qpc_ticks'], 0)

    def test_same_domain_is_compatible(self):
        result = soc_domain(series(0))
        self.assertTrue(result['fixed_rate_feasible'])
        self.assertTrue(result['compatible_with_qpc_domain'])
        self.assertFalse(result['shared_oscillator_proven'])

    def test_one_ppm_separate_clock_is_rejected_over_an_hour(self):
        result = soc_domain(series(1))
        self.assertFalse(result['fixed_rate_feasible'])
        self.assertFalse(result['compatible_with_qpc_domain'])
        self.assertGreater(result['fixed_rate_gap_qpc_ticks'], 0)

    def test_requires_three_samples(self):
        with self.assertRaises(ValueError):
            soc_domain(series(0, count=2))


if __name__ == '__main__':
    unittest.main()
