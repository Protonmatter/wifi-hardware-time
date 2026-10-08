import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ctypes as ct
import struct
import unittest
from research.acquisition.bss_reader import (ENTRY_SIZE, WLAN_BSS_ENTRY, WLAN_CONNECTION_ATTRIBUTES, CacheEntryUnavailable,
                                             parse_bss_list, single_stamp)


def entry(bssid: bytes, timestamp: int) -> bytes:
    raw = bytearray(ENTRY_SIZE)
    raw[WLAN_BSS_ENTRY.dot11Bssid.offset:WLAN_BSS_ENTRY.dot11Bssid.offset + 6] = bssid
    struct.pack_into('<Q', raw, WLAN_BSS_ENTRY.ullTimestamp.offset, timestamp)
    return bytes(raw)


class BssReaderTests(unittest.TestCase):
    def test_structure_layout_matches_wlanapi(self):
        self.assertEqual(ct.sizeof(WLAN_BSS_ENTRY), 360)
        self.assertEqual(WLAN_BSS_ENTRY.dot11Bssid.offset, 40)
        self.assertEqual(WLAN_BSS_ENTRY.ullTimestamp.offset, 72)
        self.assertEqual(ct.sizeof(WLAN_CONNECTION_ATTRIBUTES), 604)

    def test_parse_selects_connected_bssid(self):
        mine, other = bytes(range(6)), bytes(range(6, 12))
        body = entry(other, 1) + entry(mine, 123456789)
        buffer = struct.pack('<II', 8 + len(body), 2) + body
        self.assertEqual(parse_bss_list(buffer, mine), [123456789])

    def test_missing_or_duplicate_cache_entry_is_a_distinct_skippable_error(self):
        self.assertEqual(single_stamp([42]), 42)
        for stamps in ([], [1, 2]):
            with self.subTest(stamps=stamps), self.assertRaises(CacheEntryUnavailable) as caught:
                single_stamp(stamps)
            self.assertEqual(caught.exception.count, len(stamps))
        self.assertFalse(issubclass(CacheEntryUnavailable, RuntimeError))  # association changes stay RuntimeError

    def test_parse_rejects_truncated_list(self):
        with self.assertRaises(ValueError):
            parse_bss_list(struct.pack('<II', 8, 3), bytes(6))


if __name__ == '__main__':
    unittest.main()
