"""Offline protocol guards; never accesses a network device."""

import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os
import struct
import unittest

from research.tsf.qualcomm_protocol import build_request, validate_driver


class ProtocolTests(unittest.TestCase):
    def test_fixed_getter_layout(self) -> None:
        mac = bytes.fromhex('020102030405')
        packet = build_request('get_hostdbglvl', mac)
        self.assertEqual(len(packet), 128)
        self.assertEqual(packet[:20], b'get_hostdbglvl' + bytes(6))
        self.assertEqual(packet[20:26], mac)
        self.assertEqual(packet[26:], bytes(102))

    def test_tsf_read_is_fixed_positive_argument(self) -> None:
        packet = build_request('tsf_read_value', bytes.fromhex('020102030405'))
        self.assertEqual(len(packet), 128)
        self.assertEqual(packet[28:32], b'\1\0\0\0')
        self.assertEqual(struct.unpack_from('<I', packet, 32), (1,))
        self.assertEqual(packet[36:], bytes(92))

    def test_unapproved_commands_rejected(self) -> None:
        for name in ('read_reg', 'write_reg', 'tsf_auto_report', 'reset', 'tsf_read_value\0', 'A'*100):
            with self.subTest(name=name), self.assertRaises(ValueError):
                build_request(name, bytes.fromhex('020102030405'))

    def test_qtimer_capture_changes_only_argument(self) -> None:
        mac = bytes.fromhex('020102030405')
        read = build_request('tsf_read_value', mac)
        capture = build_request('tsf_read_value', mac, tsf_action=4)
        self.assertEqual(read[:32], capture[:32])
        self.assertEqual(read[36:], capture[36:])
        self.assertEqual(struct.unpack_from('<I', capture, 32), (0,))
        self.assertEqual(capture[28], 1)

    def test_invalid_actions_and_getter_capture_rejected(self) -> None:
        mac = bytes.fromhex('020102030405')
        for action in (-1, 0, 1, 2, 5, 255, True, 3.0):
            with self.subTest(action=action), self.assertRaises(ValueError):
                build_request('tsf_read_value', mac, tsf_action=action)
        with self.assertRaises(ValueError):
            build_request('get_hostdbglvl', mac, tsf_action=4)

    def test_invalid_selectors_rejected(self) -> None:
        for mac in (b'', bytes(6), bytes(7), bytes.fromhex('ffffffffffff'), bytes.fromhex('010102030405')):
            with self.subTest(mac=mac.hex()), self.assertRaises(ValueError):
                build_request('get_hostdbglvl', mac)

    def test_unqualified_binary_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_driver(b'not the qualified driver')

    @unittest.skipUnless(os.environ.get('WIFI_TIME_DRIVER_FIXTURE'), 'Optional locally owned driver fixture not supplied')
    def test_actual_binary_and_altered_binary(self) -> None:
        data = Path(os.environ['WIFI_TIME_DRIVER_FIXTURE']).read_bytes()
        validate_driver(data)
        modified = bytearray(data)
        modified[-1] ^= 1
        with self.assertRaises(ValueError):
            validate_driver(bytes(modified))


if __name__ == '__main__':
    unittest.main()
