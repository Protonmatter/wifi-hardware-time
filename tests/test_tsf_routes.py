"""Synthetic ARM64 words only; optional exact-file scan never opens a device."""

import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import struct
import os
import unittest

from research.tsf.inspect_tsf_routes import scan_words, inspect_image


class RouteTests(unittest.TestCase):
    def test_forward_and_backward_direct_branches(self):
        # B +8; BL -4; BLR x0. Only the two immediate branches have targets.
        data=struct.pack('<III',0x14000002,0x97ffffff,0xd63f0000)
        result=scan_words(data,0x1000,{0x1008,0x1000})
        self.assertEqual(result['direct_branches'],[
            dict(rva='0x1000',target_rva='0x1008',link=False),
            dict(rva='0x1004',target_rva='0x1000',link=True)])

    def test_immediate_command_scan_excludes_shifted_value(self):
        movz=0x52800000|(0x5012<<5)|3
        data=struct.pack('<III',movz,movz|(1<<21),0x54000000)
        result=scan_words(data,0x1000,set())
        self.assertEqual(result['command_immediate_rvas'],['0x1000'])

    def test_invalid_alignment_rejects(self):
        for data,base in ((b'123',0x1000),(b'1234',0x1001),(b'1234',True)):
            with self.subTest(base=base),self.assertRaises(ValueError):scan_words(data,base,set())

    def test_unqualified_driver_rejected_before_scan(self):
        with self.assertRaisesRegex(ValueError,'qualified build'):inspect_image(b'not a driver')

    @unittest.skipUnless(os.environ.get('WIFI_TIME_DRIVER_FIXTURE'),'Owned exact-build driver fixture not configured')
    def test_owned_fixture_reports_memory_log_routes(self):
        result=inspect_image(Path(os.environ['WIFI_TIME_DRIVER_FIXTURE']).read_bytes())
        self.assertEqual(result['memory_log_capacity_bytes'],2*1024*1024)
        self.assertEqual(result['selected_imports']['0x2ed358'],'ExSystemTimeToLocalTime')
        self.assertIn(dict(rva='0x230b50',target_rva='0x8d20',link=True),result['direct_branches'])
        self.assertIn(dict(rva='0x95ec',target_rva='0x8b78',link=True),result['direct_branches'])
        self.assertFalse(result['complete_call_coverage'])
