"""Exact-build packet-log evidence, not live ring retrieval or safe-IOCTL tests."""
import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.memory_ring.inspect_packetlog_return import inspect_image, main


class PacketlogReturnTests(unittest.TestCase):
    def test_unknown_build_rejected(self):
        with self.assertRaisesRegex(ValueError, 'qualified build'):
            inspect_image(b'MZ-invalid')

    def test_existing_output_and_missing_input_do_not_write(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'receipt.json'
            output.write_text('preserve', encoding='utf-8')
            for exists in (True, False):
                if not exists:
                    output.unlink()
                with patch('sys.argv', ['inspect', '--driver', str(Path(folder) / 'absent.sys'),
                                       '--output', str(output)]), contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as raised:
                        main()
                self.assertEqual(raised.exception.code, 1)
                self.assertEqual(output.exists(), exists)
                if exists:
                    self.assertEqual(output.read_text(), 'preserve')

    @unittest.skipUnless(os.environ.get('WIFI_TIME_DRIVER_FIXTURE'), 'Owned driver fixture unavailable')
    def test_outer_selector_precedence_and_combined_copy_route(self):
        result = inspect_image(Path(os.environ['WIFI_TIME_DRIVER_FIXTURE']).read_bytes())
        self.assertEqual(result['selectors'], {'outer_start': '0xff500001',
                                             'outer_combined_copy': '0xff500002',
                                             'inner_header': '0xff500001',
                                             'inner_body': '0xff500002'})
        # The outer branch reaches a combined read, not the inner header/body cases.
        for site, target in [('0x11d3d4', '0x37e00'), ('0x37e68', '0xcdd8'),
                             ('0x12e750', '0x11cde8'), ('0x12e7a0', '0x1619b0'),
                             ('0x12e860', '0x13a890')]:
            self.assertIn(dict(rva=site, target_rva=target, link=True), result['direct_branches'])
        self.assertEqual(result['operations_table']['slots'],
                         [{'offset': '0x270', 'entry_rva': '0x341ab0', 'target_rva': '0x18ae30'},
                          {'offset': '0x278', 'entry_rva': '0x341ab8', 'target_rva': '0x18ae40'}])
        for site, target in [('0x18ae30', '0x1ebe50'), ('0x18ae40', '0x1ebdc0')]:
            self.assertIn(dict(rva=site, target_rva=target, link=False), result['direct_branches'])

    @unittest.skipUnless(os.environ.get('WIFI_TIME_DRIVER_FIXTURE'), 'Owned driver fixture unavailable')
    def test_producer_copy_and_stop_release_do_not_qualify_snapshot(self):
        result = inspect_image(Path(os.environ['WIFI_TIME_DRIVER_FIXTURE']).read_bytes())
        for site, target in [('0x1ebe34', '0x1ebbf8'), ('0x1ebec4', '0x1ebbf8'),
                             ('0x220f44', '0x220ac0'), ('0x220b04', '0x220b18'),
                             ('0x220f80', '0x1a17d0'), ('0x221010', '0x220ac0'),
                             ('0x2172cc', '0x221320'), ('0x2173a0', '0x221428'),
                             ('0x221418', '0x1a17d0'), ('0x221500', '0x1a17d0'),
                             ('0x2210d8', '0x1a17d0'), ('0x1ec1b0', '0x1ebee0'),
                             ('0x1ebf94', '0x96e0')]:
            self.assertIn(dict(rva=site, target_rva=target, link=True), result['direct_branches'])
        self.assertTrue(all(not result[name] for name in
                            ('live_request_sent', 'snapshot_safety_qualified',
                             'complete_management_event_export_qualified', 'clock_input_eligible')))
        self.assertNotIn(os.environ['WIFI_TIME_DRIVER_FIXTURE'], str(result))

    @unittest.skipUnless(os.environ.get('WIFI_TIME_DRIVER_FIXTURE'), 'Owned driver fixture unavailable')
    def test_htt_producer_binding_does_not_promote_management_export(self):
        result = inspect_image(Path(os.environ['WIFI_TIME_DRIVER_FIXTURE']).read_bytes())
        self.assertEqual(result['producer_tables'], {
            'root_rva': '0x392ac0', 'common_ops_pointer_rva': '0x392ac8',
            'common_ops_rva': '0x3925f0', 'subscription_slot': '0x88',
            'subscription_target_rva': '0x1fb880',
        })
        for site, target in [('0x2175a4', '0x217150'), ('0x1fcca8', '0x1fb730'),
                             ('0x1fb760', '0x1c4fe8'), ('0x2173b8', '0x220e90'),
                             ('0x1fcf1c', '0x6ae0')]:
            self.assertIn(dict(rva=site, target_rva=target, link=True), result['direct_branches'])
        self.assertEqual(len(result['ranges']), 32)
        self.assertTrue(all(not result[name] for name in (
            'runtime_subscription_observed', 'firmware_packetlog_schema_qualified',
            'complete_management_event_export_qualified', 'clock_input_eligible')))


if __name__ == '__main__':
    unittest.main()
