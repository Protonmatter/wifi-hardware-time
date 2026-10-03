from pathlib import Path
from fractions import Fraction
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experiments/qualcomm'))
from analyze_clock_pairing_hypothesis import assess


class PairingTests(unittest.TestCase):
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
        self.assertFalse(assess([(1,100,101),(2,200,201),(3,500,501)])['affine_feasible'])

    def test_unknown_constant_bias_cannot_be_detected(self):
        a=assess([(1,10,12),(2,20,22),(3,30,32)])
        b=assess([(1,1010,1012),(2,1020,1022),(3,1030,1032)])
        self.assertEqual(a['slope_interval'],b['slope_interval'])
        self.assertFalse(b['fresh_sampling_validated'])

    def test_bad_dimensions_order_and_widths(self):
        for points in ([],[(1,2,3)],[(1,2,3),(1,4,5),(2,6,7)],[(1,4,3),(2,5,6),(3,7,8)],[(True,1,2),(2,3,4),(3,5,6)]):
            with self.assertRaises(ValueError):assess(points)


if __name__=='__main__':unittest.main()
