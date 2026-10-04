"""Authored ordinary management frames; no real capture or adapter access."""
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

from research.tsf.decode_management_tsf import decode_management_tsf

ROOT = Path(__file__).resolve().parents[1]


def frame(subtype=8, tsf=0xFEDCBA9876543210, receiver=b'\xff'*6, flags=0, sequence=0x1230):
    header = struct.pack('<HH', (subtype << 4) | flags, 0)
    header += receiver + bytes.fromhex('020000000001') + bytes.fromhex('020000000002')
    return header + struct.pack('<HQHH', sequence, tsf, 100, 1) + b'\x00\x00\x01\x01\x82'


class ManagementTsfTests(unittest.TestCase):
    def test_beacon_has_peer_clock_without_request_or_local_rx_time(self):
        result = decode_management_tsf(frame())
        self.assertEqual(result['peer_tsf_raw'], str(0xFEDCBA9876543210))
        self.assertEqual(result['peer_tsf_unit'], 'microseconds')
        self.assertEqual(result['event_kind'], 'beacon')
        self.assertEqual(result['request_association'], 'not-applicable')
        self.assertIsNone(result['request_id'])
        self.assertEqual(result['clock']['transmitter'], '02:00:00:00:00:01')
        self.assertEqual(result['clock']['bssid'], '02:00:00:00:00:02')
        self.assertIsNone(result['clock']['hardware_timer_id'])
        self.assertIsNone(result['clock']['link_id'])
        self.assertIsNone(result['clock']['epoch'])
        self.assertIsNone(result['local_rx_timestamp'])
        self.assertFalse(result['clock_input_eligible'])

    def test_unicast_and_broadcast_probe_do_not_invent_request_matches(self):
        for receiver in (b'\xff'*6, bytes.fromhex('020000000003')):
            with self.subTest(receiver=receiver):
                result = decode_management_tsf(frame(5, receiver=receiver))
                self.assertEqual(result['event_kind'], 'probe-response')
                self.assertEqual(result['request_association'], 'unestablished')
                self.assertIsNone(result['request_id'])

    def test_same_counter_different_bss_remains_separate(self):
        a = frame()
        b = a[:16] + bytes.fromhex('020000000004') + a[22:]
        first, second = decode_management_tsf(a), decode_management_tsf(b)
        self.assertEqual(first['peer_tsf_raw'], second['peer_tsf_raw'])
        self.assertNotEqual(first['clock'], second['clock'])

    def test_retry_is_preserved_not_new_exchange_proof(self):
        result = decode_management_tsf(frame(flags=0x0800))
        self.assertTrue(result['retry'])
        self.assertEqual(result['sequence_number'], 0x123)

    def test_fcs_present_must_be_valid(self):
        raw = frame()
        with_fcs = raw + struct.pack('<I', zlib.crc32(raw))
        self.assertEqual(decode_management_tsf(with_fcs, fcs_present=True)['fcs_status'], 'verified')
        with self.assertRaisesRegex(ValueError, 'bad_fcs'):
            decode_management_tsf(with_fcs[:-1] + bytes([with_fcs[-1] ^ 1]), fcs_present=True)

    def test_rejects_unsupported_layouts(self):
        for value in (frame(4), frame(flags=1), frame(flags=0x0100),
                      frame(flags=0x4000), frame(flags=0x8000),
                      frame(flags=0x0400), frame(sequence=0x1231)):
            with self.subTest(value=value[:2].hex()), self.assertRaises(ValueError):
                decode_management_tsf(value)

    def test_rejects_truncation_bad_ie_and_oversize(self):
        for value in (b'', frame()[:35], frame()[:-1], frame() + b'\x02',
                      frame() + b'\x02\x04\x01', b'x'*4097):
            with self.subTest(length=len(value)), self.assertRaises(ValueError):
                decode_management_tsf(value)

    def test_rejects_wrong_types_and_bad_source_addresses(self):
        for value in (bytearray(frame()), 'frame', None):
            with self.assertRaises(ValueError):
                decode_management_tsf(value)
        with self.assertRaises(ValueError):
            decode_management_tsf(frame(), fcs_present=1)
        for pos in (10, 16):
            data = frame()
            for address in (b'\0'*6, b'\xff'*6):
                with self.assertRaises(ValueError):
                    decode_management_tsf(data[:pos] + address + data[pos+6:])

    def test_cli_is_saved_file_only_and_structured(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'authored.bin'
            path.write_bytes(frame())
            cli = ROOT/'research/tsf/decode_management_tsf.py'
            result = subprocess.run([sys.executable, str(cli), str(path)], capture_output=True,
                                    text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['event_kind'], 'beacon')
            path.write_bytes(b'bad')
            rejected = subprocess.run([sys.executable, str(cli), str(path)], capture_output=True,
                                      text=True, timeout=10)
            self.assertEqual(rejected.returncode, 1)
            self.assertEqual(json.loads(rejected.stdout)['status'], 'rejected')


if __name__ == '__main__':
    unittest.main()
