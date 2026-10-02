"""Offline protocol guards; never accesses a network device."""
import os
import sys
from pathlib import Path
import struct
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from qualcomm_protocol import build_request, validate_driver


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
