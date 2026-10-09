
import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fractions import Fraction
import unittest
from research.clock_models.analyze_clock_pairing_hypothesis import assess, compare_counters


class PairingTests(unittest.TestCase):
    def test_equal_counter_bins_have_no_artificial_affine_slope_ceiling(self):
        result = assess([(0, 0, 0), (0, 4, 4), (0, 9, 9)])
        self.assertTrue(result['nominal_scale_feasible'])
        self.assertTrue(result['affine_feasible'])
        self.assertEqual(result['slope_interval']['lower'], {'numerator': '8', 'denominator': '1'})
        self.assertIsNone(result['slope_interval']['upper'])
        self.assertEqual(result['example_conditional_model']['slope'], {'numerator': '8', 'denominator': '1'})

    def test_common_rate_with_equal_bins_keeps_endpoint_ratio_undefined(self):
        result = compare_counters([(0, 0, 0, 0), (0, 0, 4, 4), (0, 0, 9, 9)])
        self.assertTrue(result['common_rate_feasible_under_assumptions'])
        self.assertIsNone(result['common_rate_interval']['upper'])
        self.assertIsNone(result['reported_endpoint_increment_ratio'])
        self.assertIsNone(result['reported_endpoint_increment_difference_ppm'])

    def test_quantized_affine_models_retain_exact_truth_above_float_precision(self):
        ratio = lambda r: Fraction(int(r['numerator']), int(r['denominator']))
        for slope in (Fraction(1, 10), Fraction(10), Fraction(31, 3)):
            for offset in (Fraction(1, 3), Fraction(1 << 55) + Fraction(1, 3)):
                points = []
                for i, phase in enumerate((Fraction(0), Fraction(99_999, 100_000), Fraction(1, 2))):
                    raw = (1 << 50) + i * 100
                    host = slope * (raw + phase) + offset
                    points.append((raw, int(host), int(host)))
                with self.subTest(slope=slope, offset=offset):
                    result = assess(points)
                    self.assertTrue(result['affine_feasible'])
                    self.assertLessEqual(ratio(result['slope_interval']['lower']), slope)
                    self.assertGreaterEqual(ratio(result['slope_interval']['upper']), slope)
                    self.assertLessEqual(max(lo - slope * (raw + 1) for raw, lo, hi in points), offset)
                    self.assertGreaterEqual(min(hi + 1 - slope * raw for raw, lo, hi in points), offset)

    def test_quantized_counter_and_qpc_intervals_admit_nominal_slope(self):
        result = assess([(10, 100, 100), (20, 201, 201), (30, 302, 302)])
        self.assertTrue(result['nominal_scale_feasible'])
        self.assertTrue(result['affine_feasible'])
        interval = result['slope_interval']
        ratio = lambda r: Fraction(int(r['numerator']), int(r['denominator']))
        self.assertLessEqual(ratio(interval['lower']), 10)
        self.assertGreaterEqual(ratio(interval['upper']), 10)
        self.assertEqual(ratio(interval['lower']), Fraction(201, 21))
        self.assertEqual(ratio(interval['upper']), Fraction(203, 19))

    def test_adjacent_integer_bins_do_not_divide_by_zero(self):
        result = assess([(10, 100, 100), (11, 110, 110), (12, 120, 120)])
        self.assertTrue(result['nominal_scale_feasible'])
        self.assertTrue(result['affine_feasible'])

    def test_common_rate_can_fit_nonconstant_reported_difference(self):
        result=compare_counters([(100,100,990,1010),(200,201,1990,2020),(300,302,2990,3040)])
        self.assertTrue(result['common_rate_feasible_under_assumptions'])
        self.assertEqual(result['reported_tsf_minus_soc_span_raw'],'2')
        self.assertFalse(result['simultaneous_sampling_validated'])
        self.assertFalse(result['conversion_qualified'])

    def test_disjoint_conditional_slopes_do_not_fit_common_rate(self):
        result=compare_counters([(100,200,999,1001),(200,400,1999,2001),(300,600,2999,3001)])
        self.assertFalse(result['common_rate_feasible_under_assumptions'])
        self.assertIsNone(result['common_rate_interval'])

    def test_counter_comparison_rejects_bad_dimensions_and_backward_soc(self):
        for rows in ([(1,2,3)]*3,[(1,1,10,11),(2,0,20,21),(3,3,30,31)]):
            with self.assertRaises(ValueError):compare_counters(rows)

    def test_nominal_scale_with_constant_offset(self):
        points=[(10**12+i*1000000,10*(10**12+i*1000000)+99,10*(10**12+i*1000000)+101) for i in range(3)]
        result=assess(points)
        self.assertTrue(result['nominal_scale_feasible'])
        self.assertTrue(result['affine_feasible'])
        self.assertFalse(result['conversion_qualified'])
        self.assertIsNone(result['external_uncertainty_ns'])

    def test_rate_mismatch_rejects_nominal_but_accepts_affine(self):
        points=[]
        for i in range(3):
            s=1000000*i;h=10*s+400*i+100
            points.append((s,h-1,h+1))
        result=assess(points)
        self.assertFalse(result['nominal_scale_feasible']);self.assertTrue(result['affine_feasible'])
        lo=result['slope_interval']['lower'];hi=result['slope_interval']['upper']
        self.assertLessEqual(Fraction(int(lo['numerator']),int(lo['denominator'])),Fraction(25001,2500))
        self.assertGreaterEqual(Fraction(int(hi['numerator']),int(hi['denominator'])),Fraction(25001,2500))

    def test_no_affine_fit(self):
        # Counter gaps are wide enough that one-unit quantization cannot fit the curvature.
        self.assertFalse(assess([(100,100,101),(200,200,201),(300,500,501)])['affine_feasible'])

    def test_unknown_constant_bias_cannot_be_detected(self):
        a=assess([(1,10,12),(2,20,22),(3,30,32)])
        b=assess([(1,1010,1012),(2,1020,1022),(3,1030,1032)])
        self.assertEqual(a['slope_interval'],b['slope_interval'])
        self.assertFalse(b['fresh_sampling_validated'])

    def test_bad_dimensions_order_and_widths(self):
        for points in ([],[(1,2,3)],[(1,2,3),(0,4,5),(2,6,7)],[(1,4,3),(2,5,6),(3,7,8)],[(True,1,2),(2,3,4),(3,5,6)]):
            with self.assertRaises(ValueError):assess(points)


if __name__=='__main__':unittest.main()
