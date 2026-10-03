"""Synthetic instruction tests and optional owned-file inspection; no live access."""
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments/qualcomm'))
from inspect_timing_boundaries import decode_word_load, decode_pair_load, inspect_boundaries


class BoundaryTests(unittest.TestCase):
    def test_unsigned_word_load_preserves_registers_and_offset(self):
        self.assertEqual(decode_word_load(0xb9400000 | (11 << 10) | (9 << 5) | 8),
                         dict(base=9, register=8, offset=44, width=32))

    def test_signed_pair_offset(self):
        self.assertEqual(decode_pair_load(0x29400000 | (127 << 15) | (5 << 10) | (19 << 5) | 4),
                         dict(base=19, registers=[4, 5], offsets=[-4, 0], width=32))

    def test_other_widths_stores_and_addressing_modes_reject(self):
        for word in (0xf9400000, 0xb9000000, 0xb8400400, True, -1, 1 << 32):
            with self.subTest(word=word), self.assertRaises(ValueError):
                decode_word_load(word)
        for word in (0xa9400000, 0x29000000, 0x29c00000, True):
            with self.subTest(word=word), self.assertRaises(ValueError):
                decode_pair_load(word)

    def test_wrong_image_rejects_before_interpretation(self):
        with self.assertRaisesRegex(ValueError, 'qualified build'):
            inspect_boundaries(b'wrong image')

    @unittest.skipUnless(os.environ.get('WIFI_TIME_DRIVER_FIXTURE'), 'Owned fixture unavailable')
    def test_exact_image_boundaries(self):
        result = inspect_boundaries(Path(os.environ['WIFI_TIME_DRIVER_FIXTURE']).read_bytes())
        self.assertEqual(result['tsf_report_word_offsets'], [4, 8, 12, 16, 20, 40, 44])
        self.assertEqual(result['rx_diagnostic_word_offsets'], [96, 104])
        dump = [r for r in result['direct_branches'] if r['target_rva'] == '0x22e2a0']
        self.assertEqual(len(dump), 5)
        self.assertEqual(result['reset_diagnostics_routine_name'], 'EvtNetDeviceCollectResetDiagnostics')
        self.assertFalse(result['live_retrieval_qualified'])
        self.assertFalse(result['packet_timestamp_export_qualified'])
        self.assertFalse(result['complete_call_coverage'])


if __name__ == '__main__':
    unittest.main()
