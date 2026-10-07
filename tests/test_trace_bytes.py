"""Byte audit rejects incomplete exports without promoting logs into firmware events."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from research.tsf.audit_trace_bytes import PROVIDER, audit_export, payload_view

ROOT = Path(__file__).resolve().parents[1]
TEXT = b"OL: receive WMI_VDEV_TSF_REPORT_EVENTID on 0, tsf: 123 4"


def records(payload: bytes = TEXT + b"\0") -> list[dict]:
    return [dict(kind="header", schema="wht/tsf-trace-bytes-v1", provider=PROVIDER,
                 clock_type=1, frequency="10000000", events_lost=0, buffers_lost=0),
            dict(kind="event",ordinal=2,family="report",timestamp="7654321",id=1,
                 version=0,opcode=0,flags=0,extended_data_count=0,length=len(payload),hex=payload.hex()),
            dict(kind="summary",events=3,wlan_events=1,exported=1,payload_bytes=len(payload),
                 process_status=0,close_status=0,bound_failure=False)]


def encoded(rows: list[dict]) -> bytes:
    return ("\n".join(json.dumps(row) for row in rows)+"\n").encode()


class TraceByteAuditTests(unittest.TestCase):
    def test_numeric_fields_and_no_clock_admission(self):
        report=audit_export(encoded(records()))
        self.assertEqual(report["observations"][0]["numeric_words"],[0,123,4])
        self.assertEqual(report["assessment"],"selected-userdata-is-numeric-text")
        self.assertFalse(report["clock_eligible"])
        self.assertFalse(report["original_firmware_event_recovered"])
        self.assertEqual(report["quarantine_disposition"],"unchanged")

    def test_raw_trailing_binary_is_not_hidden_by_nul(self):
        raw=TEXT+b"\0\x05\x50\0\0"
        report=audit_export(encoded(records(raw)))
        event=report["observations"][0]
        self.assertEqual(event["trailing_bytes"],4)
        self.assertEqual(event["trailing_nonzero_bytes"],2)
        self.assertEqual(report["assessment"],"additional-byte-review-required")

    def test_zero_padding_is_counted_and_missing_nul_is_visible(self):
        view=payload_view(TEXT+b"\0\0\0","report")
        self.assertEqual(view["classification"],"numeric-text-with-zero-tail")
        self.assertEqual(view["trailing_bytes"],2)
        self.assertFalse(payload_view(TEXT,"report")["nul_terminated"])

    def test_all_numeric_formats_and_uint32_bound(self):
        for name, raw in (("command",b"WMI_VDEV_TSF_TSTAMP_ACTION_CMDID: vdev_id=0 tsf_action=4"),
                          ("soc_timer",b"OL: g_tsf: 1 2; soc_timer: 3 4"),
                          ("delay",b"OL: set vdev-0 tsf_delay=4294967295")):
            with self.subTest(name=name):
                self.assertTrue(payload_view(raw+b"\r\n\0",name)["exact_numeric_text"])
        self.assertFalse(payload_view(TEXT.replace(b"123",b"4294967296"),"report")["exact_numeric_text"])
        signed=payload_view(b"OL: g_tsf: -2147483648 2147483647; soc_timer: 4294967295 0","soc_timer")
        self.assertEqual(signed["numeric_words"],[-2147483648,2147483647,4294967295,0])
        self.assertFalse(payload_view(b"OL: g_tsf: 2147483648 0; soc_timer: 0 0","soc_timer")["exact_numeric_text"])

    def test_partial_text_extra_text_wrong_family_and_non_ascii_are_unqualified(self):
        for raw in (TEXT[:-2],TEXT+b" extra",TEXT+b"\xff",b"\0"+TEXT):
            with self.subTest(raw=raw):
                self.assertEqual(payload_view(raw,"report")["classification"],"requires-byte-review")
        self.assertFalse(payload_view(TEXT,"delay")["exact_numeric_text"])

    def test_missing_and_failed_completion_are_rejected(self):
        rows=records()
        with self.assertRaises(ValueError): audit_export(encoded(rows[:-1]))
        for key,value in (("process_status",1223),("close_status",5),("bound_failure",True),
                          ("bound_failure",0),("exported",2),("payload_bytes",1)):
            changed=copy.deepcopy(rows);changed[-1][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError): audit_export(encoded(changed))

    def test_truncated_and_malformed_payload_exports_are_rejected(self):
        for key,value in (("length",1),("length",True),("hex","00 zz"),("ordinal",0),
                          ("timestamp",str(2**63)),("flags",True),("version",256),("id",2)):
            changed=records();changed[1][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError): audit_export(encoded(changed))

    def test_duplicate_json_and_duplicate_ordinals_rejected(self):
        with self.assertRaises(ValueError):
            audit_export(encoded(records()).replace(b'"kind": "event"',b'"kind": "event", "kind": "event"'))
        rows=records();rows.insert(2,copy.deepcopy(rows[1]));rows[-1].update(exported=2,wlan_events=2,payload_bytes=2*rows[1]["length"])
        with self.assertRaises(ValueError): audit_export(encoded(rows))

    def test_unrecognized_fields_do_not_silently_extend_the_contract(self):
        for index in range(3):
            rows=records();rows[index]["hardware_clock_id"]=0
            with self.subTest(index=index),self.assertRaises(ValueError): audit_export(encoded(rows))

    def test_loss_and_extended_data_never_disappear(self):
        rows=records();rows[0].update(events_lost=2,buffers_lost=1);rows[1]["extended_data_count"]=1
        result=audit_export(encoded(rows))
        self.assertEqual(result["trace_loss"],dict(events_lost=2,buffers_lost=1))
        self.assertEqual(result["records_with_uninspected_extended_data"],1)
        self.assertFalse(result["clock_eligible"])

    def test_empty_selection_is_inconclusive(self):
        rows=records();del rows[1];rows[-1].update(exported=0,payload_bytes=0)
        self.assertEqual(audit_export(encoded(rows))["assessment"],"no-selected-records")

    @unittest.skipUnless(os.name=="nt","Windows SDK/API test")
    def test_native_build_classifier_and_rejection_without_hardware(self):
        compiler=shutil.which(os.environ.get("WIFI_TIME_NATIVE_CC") or "cl")
        if not compiler:
            if os.environ.get("WIFI_TIME_NATIVE_CC"): self.fail("Configured compiler unavailable")
            self.skipTest("MSVC developer environment unavailable")
        with tempfile.TemporaryDirectory() as directory:
            binary=Path(directory)/"trace-bytes.exe"
            built=subprocess.run([compiler,"/nologo","/W4","/WX","/O2",
                                  str(ROOT/"research/tsf/export_tsf_trace_bytes.c"),f"/Fe{binary}",
                                  "/link","advapi32.lib"],cwd=directory,capture_output=True,text=True,timeout=60)
            self.assertEqual(built.returncode,0,built.stdout+built.stderr)
            for args,code in ((["--self-test"],0),(["--help"],0),([],2),(["--unknown"],2),
                              ([str(Path(directory)/"missing.etl")],1)):
                with self.subTest(args=args):
                    result=subprocess.run([str(binary),*args],capture_output=True,text=True,timeout=5)
                    self.assertEqual(result.returncode,code,result.stdout+result.stderr)


if __name__=="__main__": unittest.main()
