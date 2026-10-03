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
        self.assertEqual(len(result['ranges']), 8)
        self.assertFalse(result['live_request_sent'])
        self.assertFalse(result['complete_timestamp_export_qualified'])
        self.assertFalse(result['complete_call_coverage'])
        self.assertNotIn(os.environ['WIFI_TIME_DRIVER_FIXTURE'], json.dumps(result))


if __name__ == '__main__':
    unittest.main()
