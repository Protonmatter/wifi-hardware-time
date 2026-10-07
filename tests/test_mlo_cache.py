"""Offline symbol identity and bounded constant decoding, never live cache tests."""
import contextlib
import io
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import uuid

from research.memory_ring.inspect_mlo_cache import inspect_image, main, parse_rsds, scan_constants


class MloCacheTests(unittest.TestCase):
    def test_rsds_identity_preserves_guid_age_but_not_build_directory(self):
        guid = uuid.UUID('12345678-1234-5678-9012-345678901234')
        record = b'RSDS' + guid.bytes_le + struct.pack('<I', 10) + b'C:\\private-build\\driver.pdb\0'
        result = parse_rsds(record)
        self.assertEqual(result, dict(format='RSDS', pdb_name='driver.pdb', guid=str(guid), age=10,
                                     symbol_store_key='12345678123456789012345678901234A'))
        self.assertNotIn('private-build', str(result))

    def test_invalid_symbol_records_rejected(self):
        for data in (b'', b'NB10' + b'\0' * 30, b'RSDS' + b'\0' * 20,
                     b'RSDS' + b'\0' * 20 + b'a.pdb',
                     b'RSDS' + b'\0' * 20 + b'a.dll\0',
                     b'RSDS' + b'\0' * 20 + b'a\npdb.pdb\0'):
            with self.subTest(data=data), self.assertRaises(ValueError):
                parse_rsds(data)

    def test_immediate_forms_include_shift_and_scaled_offset(self):
        # MOVZ X10,#0x5ff0; ADD X9,X20,#6,LSL#12; LDR X8,[X0,#0x6000].
        words = [0xD28BFE0A, 0x91401A89, 0xF9700008]
        rows = scan_constants(struct.pack('<3I', *words), 0x1000)
        self.assertEqual(rows, [
            dict(rva='0x1000', value='0x5ff0', kind='movz_immediate'),
            dict(rva='0x1004', value='0x6000', kind='add_immediate'),
            dict(rva='0x1008', value='0x6000', kind='integer_unsigned_memory_offset'),
        ])

    def test_partial_constants_and_unaligned_input_not_misclassified(self):
        # MOVK and shifted MOVZ do not establish these complete constants.
        self.assertEqual(scan_constants(struct.pack('<3I', 0xF28BFE0A, 0xD2ABFE0A, 0xD503201F), 0), [])
        for data, rva in ((b'\0', 0), (b'\0' * 4, 1), (b'', -4), (b'', True)):
            with self.assertRaises(ValueError):
                scan_constants(data, rva)

    def test_wrong_build_rejected(self):
        with self.assertRaisesRegex(ValueError, 'qualified build'):
            inspect_image(b'MZ-invalid')

    def test_cli_preserves_existing_output_and_rejects_missing_input(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'receipt.json'
            output.write_text('preserve', encoding='utf-8')
            for exists in (True, False):
                if not exists:
                    output.unlink()
                with patch('sys.argv', ['inspect', '--driver', str(Path(folder) / 'missing.sys'),
                                       '--output', str(output)]), contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as error:
                        main()
                self.assertEqual(error.exception.code, 1)
                self.assertEqual(output.exists(), exists)
                if exists:
                    self.assertEqual(output.read_text(), 'preserve')

    @unittest.skipUnless(os.environ.get('WIFI_TIME_DRIVER_FIXTURE'), 'Owned exact-build fixture unavailable')
    def test_owned_image_symbol_and_ordering_evidence_remain_unqualified(self):
        result = inspect_image(Path(os.environ['WIFI_TIME_DRIVER_FIXTURE']).read_bytes())
        self.assertEqual(result['native_symbols'], {
            'format': 'RSDS', 'pdb_name': 'qcwlanhmt8380.pdb',
            'guid': 'dfe3ade4-eb12-4165-b34a-3aaa18371c82', 'age': 1,
            'symbol_store_key': 'DFE3ADE4EB124165B34A3AAA18371C821',
        })
        for site, target in [('0x1fcd50', '0x1fd7e0'), ('0x1fd904', '0x1fb730'),
                             ('0x1c31e8', '0x7528'), ('0x1c31f8', '0x1a3548'),
                             ('0x1c6664', '0x1fb6c0'), ('0x1c675c', '0x70b0')]:
            self.assertIn(dict(rva=site, target_rva=target, link=True), result['direct_branches'])
        self.assertEqual(result['lifecycle_ops'], dict(main_table_rva='0x392280',
                         detach_wrapper_rva='0x1c3550', deinit_wrapper_rva='0x1c3500'))
        self.assertIn(dict(rva='0x1fd938', value='0x5ff0', kind='movz_immediate'),
                      result['constant_candidates'])
        self.assertIn(dict(rva='0x1fd9a0', value='0x6000', kind='add_immediate'),
                      result['constant_candidates'])
        self.assertTrue(all(not result[key] for key in (
            'independent_reader_proven', 'runtime_cache_observed', 'timestamp_units_live_qualified',
            'owned_export_qualified', 'hardware_qpc_relation_qualified', 'clock_input_eligible')))


if __name__ == '__main__':
    unittest.main()
