"""Offline private-route evidence checks; the optional fixture is an owned file."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.adapters.inspect_private_exports import inspect_image, main


class PrivateExportTests(unittest.TestCase):
    def test_unknown_or_modified_file_rejected(self):
        for data in (b'', b'MZ' + b'\0' * 1024):
            with self.subTest(length=len(data)), self.assertRaisesRegex(ValueError, 'qualified build'):
                inspect_image(data)

    def test_existing_output_preserved_before_read(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'receipt.json'
            output.write_text('preserve me', encoding='utf-8')
            with patch('sys.argv', ['inspect', '--driver', str(Path(folder) / 'absent.sys'),
                                    '--output', str(output)]), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    main()
            self.assertEqual(raised.exception.code, 1)
            self.assertEqual(output.read_text(encoding='utf-8'), 'preserve me')

    def test_missing_driver_does_not_create_receipt(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'receipt.json'
            with patch('sys.argv', ['inspect', '--driver', str(Path(folder) / 'absent.sys'),
                                    '--output', str(output)]), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    main()
            self.assertEqual(raised.exception.code, 1)
            self.assertFalse(output.exists())

    @unittest.skipUnless(os.environ.get('WIFI_TIME_DRIVER_FIXTURE'), 'Owned exact-build fixture not configured')
    def test_owned_file_binds_routes_without_claiming_live_export(self):
        result = inspect_image(Path(os.environ['WIFI_TIME_DRIVER_FIXTURE']).read_bytes())
        self.assertEqual(result['get_rx_stats']['selector'], 250)
        self.assertTrue(result['test_service']['fixed_eight_byte_payload_matches'])
        self.assertEqual(result['selected_imports']['0x2ed0f8'], 'KeWaitForSingleObject')
        self.assertIn(dict(rva='0x127f08', target_rva='0x308f0', link=True), result['selected_direct_calls'])
        self.assertIn(dict(rva='0x1280f4', target_rva='0x308f0', link=True), result['selected_direct_calls'])
        self.assertEqual(len(result['ranges']), 14)
        self.assertFalse(result['live_request_sent'])
        self.assertFalse(result['complete_timestamp_export_qualified'])
        classified = result['completion_argument_inventory']
        self.assertEqual(len(classified['sites']), 70)
        self.assertEqual(sum(row['payload_possible'] for row in classified['sites']), 11)
        self.assertEqual(classified['null_payload_calls'], 59)
        fixed = next(row for row in classified['sites'] if row['call_rva'] == '0x12a430')
        self.assertEqual(fixed['manual_role'], 'fixed test-pipeline bytes')
        self.assertFalse(classified['hardware_timing_producer_connected'])

    @unittest.skipUnless(os.environ.get('WIFI_TIME_DRIVER_FIXTURE'), 'Owned exact-build fixture not configured')
    def test_ihv_binary_response_bridge_is_traced_but_not_qualified(self):
        result = inspect_image(Path(os.environ['WIFI_TIME_DRIVER_FIXTURE']).read_bytes())
        for site, target in [('0x12e750', '0x11cde8'), ('0x12e7a0', '0x1619b0'),
                             ('0x12e860', '0x13a890'), ('0x11d090', '0x11ca70'),
                             ('0x11d144', '0x39e38'), ('0x11d1a0', '0x3a5b8'),
                             ('0x11d1c4', '0x39528')]:
            self.assertIn(dict(rva=site, target_rva=target, link=True), result['selected_direct_calls'])
        self.assertFalse(result['complete_timestamp_export_qualified'])
        self.assertFalse(result['live_request_sent'])
        self.assertFalse(result['complete_call_coverage'])
        self.assertNotIn(os.environ['WIFI_TIME_DRIVER_FIXTURE'], json.dumps(result))

    @unittest.skipUnless(os.environ.get('WIFI_TIME_DRIVER_FIXTURE'), 'Owned exact-build fixture not configured')
    def test_return_inventory_and_interface_dispatch(self):
        result = inspect_image(Path(os.environ['WIFI_TIME_DRIVER_FIXTURE']).read_bytes())
        inventory = result['return_inventory']
        self.assertEqual(len(inventory['direct_branches']), 74)
        self.assertEqual(sum(row['target_rva'] == '0x13a890'
                             for row in inventory['direct_branches']), 70)
        self.assertEqual(sum(row['target_rva'] == '0x1618c0'
                             for row in inventory['direct_branches']), 4)
        self.assertTrue(all(row['link'] for row in inventory['direct_branches']))
        self.assertTrue(inventory['executable_sections'])
        calls = result['selected_direct_calls']
        for site, target in [('0x12ae10', '0x51960'), ('0x519a4', '0x502c0'),
                             ('0x519b0', '0x505b0'), ('0x519f0', '0x50758'),
                             ('0x12ae5c', '0x1618c0'), ('0x12ae78', '0x13a890')]:
            self.assertIn(dict(rva=site, target_rva=target, link=True), calls)
        self.assertFalse(result['complete_call_coverage'])
        self.assertFalse(result['complete_timestamp_export_qualified'])


if __name__ == '__main__':
    unittest.main()
