"""Optional owned-driver checks of the selected management-frame handoff."""
import os
from pathlib import Path
import struct
import unittest

from research.adapters import inspect_management_rx
from research.adapters.inspect_management_rx import inspect_image


class ManagementRxPathTests(unittest.TestCase):
    def test_history_filter_decodes_event_and_signed_branch(self):
        # Authored ARM64 instructions, independent of an owned driver fixture.
        # An unsigned branch displacement or shifted MOVZ would give wrong evidence.
        self.assertTrue(hasattr(inspect_management_rx, 'decode_history_exclusion'))
        for event in (0, 0x7001, 0xffff):
            for displacement in (-16, 76):
                code = struct.pack('<4I', 0x52800008 | event << 5,
                                   0xf100013f, 0x7a481264,
                                   0x54000000 | ((displacement // 4) & 0x7ffff) << 5)
                with self.subTest(event=event, displacement=displacement):
                    self.assertEqual(inspect_management_rx.decode_history_exclusion(code, 0x1000),
                                     {'excluded_event_id': event,
                                      'bypass_target_rva': hex(0x100c + displacement)})

    def test_history_filter_rejects_incomplete_or_different_control_flow(self):
        self.assertTrue(hasattr(inspect_management_rx, 'decode_history_exclusion'))
        words = [0x52800008 | 0x7001 << 5, 0xf100013f, 0x7a481264, 0x54000260]
        valid = struct.pack('<4I', *words)
        for value in (None, bytearray(valid), valid[:-1], valid + b'\0'):
            with self.subTest(value=type(value)), self.assertRaises(ValueError):
                inspect_management_rx.decode_history_exclusion(value, 0x1000)
        for index, mask in ((0, 1 << 21), (0, 1), (1, 1 << 10), (2, 1), (3, 1)):
            changed = words.copy()
            changed[index] ^= mask
            with self.subTest(index=index, mask=mask), self.assertRaises(ValueError):
                inspect_management_rx.decode_history_exclusion(struct.pack('<4I', *changed), 0x1000)
        for address in (True, -4, 1, 0x100000000, 0xfffffff0):
            with self.subTest(address=address), self.assertRaises(ValueError):
                inspect_management_rx.decode_history_exclusion(valid, address)

    @unittest.skipUnless(os.environ.get('WIFI_TIME_DRIVER_FIXTURE'), 'Owned driver fixture not configured')
    def test_management_lifetime_and_history_exclusion(self):
        result = inspect_image(Path(os.environ['WIFI_TIME_DRIVER_FIXTURE']).read_bytes())
        self.assertIn('event_lifetime', result)
        lifetime = result['event_lifetime']
        self.assertEqual(lifetime['cleanup_allocation_flag_load_offsets'], list(range(12, 192, 16)))
        self.assertEqual(lifetime['history_filter'],
                         {'excluded_event_id': 0x7001, 'bypass_target_rva': '0x168fe0'})
        self.assertEqual(lifetime['history_time_import'], 'KeQuerySystemTimePrecise')
        for site, target in [('0x168e0c', '0x1ba4e0'), ('0x1690c8', '0x1bae60'),
                             ('0x1bc730', '0x7740'), ('0x1bc7cc', '0x1bb564'),
                             ('0x1bb570', '0x7740')]:
            self.assertIn(dict(rva=site, target_rva=target, link=site != '0x1bc7cc'),
                          result['direct_branches'])
        self.assertFalse(lifetime['live_ownership_qualified'])
        self.assertFalse(lifetime['hardware_qpc_bracket_established'])

    def test_unknown_driver_rejected(self):
        with self.assertRaisesRegex(ValueError, 'qualified build'):
            inspect_image(b'not a driver')

    @unittest.skipUnless(os.environ.get('WIFI_TIME_DRIVER_FIXTURE'), 'Owned driver fixture not configured')
    def test_management_schema_and_selected_handoff(self):
        result = inspect_image(Path(os.environ['WIFI_TIME_DRIVER_FIXTURE']).read_bytes())
        self.assertEqual(result['event_id'], 0x7001)
        self.assertEqual(result['header_expected_bytes'], 72)
        self.assertEqual(result['header_tag'], 44)
        self.assertEqual(result['decoded_slots'], 12)
        self.assertEqual(result['selected_unsigned_word_load_offsets'], [12, 16, 20, 68])
        self.assertEqual(result['selected_pair_load_offsets'], [[36, 40], [28, 32]])
        self.assertIn(dict(rva='0x1a84e4', target_rva='0x104230', link=True), result['direct_branches'])
        self.assertFalse(result['hardware_pair_export_qualified'])
        self.assertFalse(result['live_capture_performed'])

    @unittest.skipUnless(os.environ.get('WIFI_TIME_DRIVER_FIXTURE'), 'Owned driver fixture not configured')
    def test_optional_slots_and_downstream_callback_remain_unqualified(self):
        result = inspect_image(Path(os.environ['WIFI_TIME_DRIVER_FIXTURE']).read_bytes())
        self.assertEqual([(slot['tag'], slot['element_size']) for slot in result['schema_slots']],
                         [(44, 72), (17, 1), (18, 20), (978, 20), (18, 16), (18, 20),
                          (18, 20), (17, 1), (18, 12), (18, 8), (18, 8), (17, 1)])
        self.assertEqual(result['selected_wrapper_pointer_load_offsets'], [0, 16])
        self.assertEqual(result['selected_wrapper_word_load_offsets'], [24])
        branches = result['direct_branches']
        self.assertIn(dict(rva='0x1022e8', target_rva='0x103468', link=True), branches)
        self.assertIn(dict(rva='0x1035f4', target_rva='0x101ac8', link=True), branches)
        self.assertIn(dict(rva='0xb5f98', target_rva='0x9cea8', link=True), branches)
        self.assertIn(dict(rva='0x1a606c', target_rva='0x1a49b0', link=True), branches)
        self.assertFalse(result['hardware_pair_export_qualified'])
        self.assertFalse(result['firmware_layout_qualified'])

    @unittest.skipUnless(os.environ.get('WIFI_TIME_DRIVER_FIXTURE'), 'Owned driver fixture not configured')
    def test_bss_serializer_schema_and_selected_producer(self):
        result = inspect_image(Path(os.environ['WIFI_TIME_DRIVER_FIXTURE']).read_bytes())
        schema = result['bss_container_schema']
        self.assertEqual(schema['container_bytes'], 144)
        self.assertEqual([(field['tag'], field['offset']) for field in schema['fields']],
                         [(2, 4), (9, 16), (10, 40), (11, 64), (58, 72),
                          (13, 80), (186, 104), (274, 120)])
        for site, target in [('0x2580c', '0x57830'), ('0x259a0', '0x161a50'),
                             ('0x259cc', '0x13c430'), ('0xea264', '0x1a17d0'),
                             ('0x20c18', '0x25780')]:
            self.assertIn(dict(rva=site, target_rva=target, link=True), result['direct_branches'])
        self.assertFalse(result['hardware_pair_export_qualified'])

    @unittest.skipUnless(os.environ.get('WIFI_TIME_DRIVER_FIXTURE'), 'Owned driver fixture not configured')
    def test_mbssid_context_and_host_cache_time_routes(self):
        result = inspect_image(Path(os.environ['WIFI_TIME_DRIVER_FIXTURE']).read_bytes())
        self.assertEqual(result['cache_time_import'], 'KeQueryTimeIncrement')
        self.assertEqual(result['host_cache_tick_literal'], '0xfffff78000000320')
        for site, target in [('0x95694', '0x1a17d0'), ('0x9eaec', '0x9e378'),
                             ('0x9ec94', '0x987d8'), ('0x98938', '0x9cea8'),
                             ('0x9cf1c', '0xec1d0'), ('0xec278', '0x94f10'),
                             ('0xec4bc', '0x15a3a4'), ('0xec5a4', '0xe8110'),
                             ('0xe8340', '0xe9a00'), ('0xea0ac', '0x15a3a4'),
                             ('0xea828', '0x15a3a4')]:
            self.assertIn(dict(rva=site, target_rva=target, link=True), result['direct_branches'])
        self.assertFalse(result['hardware_pair_export_qualified'])


if __name__ == '__main__':
    unittest.main()
