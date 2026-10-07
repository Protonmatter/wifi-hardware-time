"""Synthetic schema bounds and optional owned-file ingress inspection."""
import os
from pathlib import Path
import struct
import unittest

from research.ftm.inspect_ftm_ingress import find_event_layout, inspect_image


class IngressTests(unittest.TestCase):
    def test_variable_and_fixed_layout_words(self):
        data = struct.pack('<IIII', (3 << 24) | 0x27004,
                           0x11 | (1 << 12) | (510 << 21) | (1 << 30),
                           0x293 | (20 << 12) | (510 << 21),
                           0x11 | (1 << 12) | (510 << 21) | (1 << 30))
        result = find_event_layout(data, 0x27004)
        self.assertEqual(result['table_offset'], 0)
        self.assertEqual(result['entries'][0], dict(tag=17, element_size=1, variable_flag=1, count_code=510))
        self.assertEqual(result['entries'][1], dict(tag=659, element_size=20, variable_flag=0, count_code=510))

    def test_rejects_truncated_unaligned_duplicate_missing_and_oversized(self):
        header = struct.pack('<I', 0x27004)
        cases = (b'', b'123', struct.pack('<I', (2 << 24) | 0x27004),
                 header + header, struct.pack('<I', 0x5005), b'\0' * 4116,
                 header + struct.pack('<I', (1 << 24) | 0x5005))
        for data in cases:
            with self.subTest(length=len(data)), self.assertRaises(ValueError):
                find_event_layout(data, 0x27004)

    def test_rejects_invalid_selector(self):
        for selector in (True, -1, 0x1000000, '0x27004'):
            with self.subTest(selector=selector), self.assertRaises(ValueError):
                find_event_layout(struct.pack('<I', 0x27004), selector)

    def test_unknown_build_rejected(self):
        with self.assertRaisesRegex(ValueError, 'qualified build'):
            inspect_image(b'not the owned driver')

    @unittest.skipUnless(os.environ.get('WIFI_TIME_DRIVER_FIXTURE'), 'Owned exact-build fixture not configured')
    def test_owned_fixture_connects_registration_decoder_and_cleanup(self):
        result = inspect_image(Path(os.environ['WIFI_TIME_DRIVER_FIXTURE']).read_bytes())
        self.assertEqual(result['event_layout']['entry_rva'], '0x3900c8')
        self.assertEqual(len(result['event_layout']['entries']), 3)
        self.assertEqual(result['history_time_import'], 'KeQuerySystemTimePrecise')
        self.assertEqual(result['cleanup_selector'], 0x27004)
        self.assertIn(dict(rva='0x168e0c', target_rva='0x1ba4e0', link=True), result['direct_branches'])
        self.assertIn(dict(rva='0x1690c8', target_rva='0x1bae60', link=True), result['direct_branches'])
        self.assertFalse(result['live_acquisition'])
        self.assertFalse(result['application_export_established'])


if __name__ == '__main__':
    unittest.main()
