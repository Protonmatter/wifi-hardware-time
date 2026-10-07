"""Bounded instruction decoding and optional exact-build schema evidence."""
import os
from pathlib import Path
import struct
import unittest

from research.tsf.inspect_tsf_report_contract import inspect_image, word_load_offsets


class TsfReportContractTests(unittest.TestCase):
    def test_only_selected_base_unsigned_word_loads_are_counted(self):
        # LDR W4,[X9,#4]; STR W4,[X9,#4]; LDR X4,[X9,#8]; LDR W5,[X8,#8].
        words = (0xB9400000 | (1 << 10) | (9 << 5) | 4,
                 0xB9000000 | (1 << 10) | (9 << 5) | 4,
                 0xF9400000 | (1 << 10) | (9 << 5) | 4,
                 0xB9400000 | (2 << 10) | (8 << 5) | 5)
        self.assertEqual(word_load_offsets(struct.pack('<4I', *words), 9), [4])

    def test_bad_input_and_unknown_build_reject(self):
        for data, base in [(b'abc', 9), (b'1234', True), (b'1234', 32)]:
            with self.subTest(base=base), self.assertRaises(ValueError):
                word_load_offsets(data, base)
        with self.assertRaisesRegex(ValueError, 'qualified build'):
            inspect_image(b'not a driver')

    @unittest.skipUnless(os.environ.get('WIFI_TIME_DRIVER_FIXTURE'), 'Owned exact-build driver not configured')
    def test_owned_schema_and_handler_coverage(self):
        result = inspect_image(Path(os.environ['WIFI_TIME_DRIVER_FIXTURE']).read_bytes())
        self.assertEqual(result['report_expected_bytes'], 60)
        self.assertEqual(result['report_tag'], 0x18B)
        self.assertEqual(result['command_expected_bytes'], 20)
        self.assertEqual(result['selected_report_word_offsets'], [4, 8, 12, 16, 20, 40, 44])
        self.assertEqual(result['unconsumed_payload_word_offsets'], [24, 28, 32, 36, 48, 52, 56])
        self.assertFalse(result['runtime_wire_length_verified'])
        self.assertFalse(result['response_association_qualified'])
        self.assertFalse(result['fresh_sampling_qualified'])


if __name__ == '__main__':
    unittest.main()
