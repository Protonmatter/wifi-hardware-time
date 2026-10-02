import struct
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments' / 'qualcomm'))
from decode_ftm_response import decode


class ResponseTests(unittest.TestCase):
    def test_layout_and_signed_value(self):
        data=bytearray(104);data[:6]=bytes.fromhex('020304050607')
        struct.pack_into('<H',data,14,2)
        struct.pack_into('<i',data,16,-40)
        struct.pack_into('<i',data,28,-123)
        result=decode(bytes(data))
        self.assertEqual(result['reported_rtt_ps'],-123)
        self.assertEqual(result['reported_rssi_dbm'],-40)
        self.assertNotIn('bssid',result)
        self.assertFalse(result['distance_accuracy_validated'])

    def test_bad_size(self):
        for size in (0,103,105):
            with self.assertRaises(ValueError):decode(bytes(size))

    def test_failure_fields_not_interpreted(self):
        data=bytearray(104);struct.pack_into('<I',data,8,1)
        self.assertNotIn('reported_rtt_ps',decode(bytes(data)))

    def test_zero_measurements_rejected(self):
        with self.assertRaises(ValueError):decode(bytes(104))


if __name__=='__main__':unittest.main()
