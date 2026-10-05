"""Selected exact-build ingress evidence and rejection tests; no device I/O."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from research.tsf.inspect_tsf_ingress import MAX_BYTES, inspect_image

ROOT = Path(__file__).resolve().parents[1]


class TsfIngressTests(unittest.TestCase):
    def test_rejects_unknown_image_types_and_bounds(self) -> None:
        for raw in (b"not the driver", bytearray(64), None, bytes(MAX_BYTES + 1)):
            with self.subTest(kind=type(raw)), self.assertRaises(ValueError):
                inspect_image(raw)

    def test_cli_no_overwrite_and_no_false_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            driver = Path(tmp) / "missing.sys"
            output = Path(tmp) / "receipt.json"
            command = [sys.executable, str(ROOT / "research/tsf/inspect_tsf_ingress.py"),
                       "--driver", str(driver), "--output", str(output)]
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(output.exists())
            output.write_text("preserve", encoding="utf-8")
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 1)
            self.assertIn("already exists", result.stderr)
            self.assertEqual(output.read_text(encoding="utf-8"), "preserve")

    @unittest.skipUnless(os.environ.get("WIFI_TIME_DRIVER_FIXTURE"), "Owned exact-build driver not configured")
    def test_exact_image_schema_registration_and_cleanup(self) -> None:
        raw = Path(os.environ["WIFI_TIME_DRIVER_FIXTURE"]).read_bytes()
        result = inspect_image(raw)
        self.assertEqual(result["event_schema"]["entries"],
                         [dict(tag=395, element_size=60, variable_flag=0, count_code=510)])
        self.assertEqual(result["schema_entry_rva"], "0x39003c")
        self.assertEqual(result["cleanup_table_entry_rva"], "0x1bda9c")
        self.assertEqual(result["cleanup_target_rva"], "0x1bb558")
        self.assertEqual(result["decoded_slot"], dict(bytes=16, pointer_offset=0, count_offset=8, allocated_offset=12))
        branches = {(item["rva"], item["target_rva"]) for item in result["selected_direct_branches"]}
        self.assertIn(("0x2159b0", "0x16a078"), branches)
        self.assertIn(("0x168e0c", "0x1ba4e0"), branches)
        self.assertIn(("0x1690c8", "0x1bae60"), branches)
        self.assertIn(("0x1ba8b0", "0x15a3a4"), branches)
        transport = result["manual_transport"]
        self.assertEqual(transport["htc_header_bytes"], 8)
        self.assertFalse(transport["contiguous_source_span_qualified"])
        self.assertEqual(transport["send_completion_rva"], "0x169220")
        self.assertEqual(transport["pooled_buffer_reference_count_offset"], "0x198")
        for field in ("runtime_wire_length_verified", "logical_length_is_wire_extent_qualified",
                      "live_callback_ownership_qualified",
                      "application_export_established", "response_association_qualified",
                      "fresh_sampling_qualified", "hardware_qpc_qualified", "live_request_sent"):
            self.assertIs(result[field], False)
        with self.assertRaisesRegex(ValueError, "qualified build"):
            inspect_image(raw[:-1] + bytes([raw[-1] ^ 1]))

    @unittest.skipUnless(os.environ.get("WIFI_TIME_DRIVER_FIXTURE"), "Owned exact-build driver not configured")
    def test_owned_callback_install_and_receive_handoff(self) -> None:
        result = inspect_image(Path(os.environ["WIFI_TIME_DRIVER_FIXTURE"]).read_bytes())
        producer = result["manual_hif_producer"]
        self.assertEqual(producer["callback_block_bytes"], 40)
        self.assertEqual(producer["active_block_offset"], "0x978")
        self.assertEqual(producer["active_receive_callback_offset"], "0x988")
        self.assertEqual(producer["completion_record"]["bytes"], 64)
        self.assertEqual(producer["completion_record"]["receive_type"], 2)
        self.assertEqual(producer["completion_record"]["buffer_offset"], "0x20")
        self.assertEqual(producer["completion_record"]["bytes_offset"], "0x30")
        branches = {(item["rva"], item["target_rva"]) for item in result["selected_direct_branches"]}
        self.assertIn(("0x1b45a4", "0x15a3a4"), branches)
        self.assertIn(("0x1b360c", "0x1f3a68"), branches)
        self.assertIn(("0x1b18fc", "0x6eb0"), branches)
        self.assertIn(("0x1b19b8", "0x1b2f18"), branches)
        self.assertIn(("0x1b3bf4", "0x67a0"), branches)

    @unittest.skipUnless(os.environ.get("WIFI_TIME_DRIVER_FIXTURE"), "Owned exact-build driver not configured")
    def test_owned_operation_tables_do_not_qualify_live_geometry_or_history_copy(self) -> None:
        result = inspect_image(Path(os.environ["WIFI_TIME_DRIVER_FIXTURE"]).read_bytes())
        self.assertEqual(result["ce_operation_tables"], [
            dict(table_rva="0x3933f0", slot="0x30", target_rva="0x1f2120"),
            dict(table_rva="0x3933f0", slot="0x40", target_rva="0x1f2370"),
            dict(table_rva="0x3934f0", slot="0x30", target_rva="0x1f46d0"),
            dict(table_rva="0x3934f0", slot="0x40", target_rva="0x1f49a0"),
        ])
        producer = result["manual_hif_producer"]
        self.assertEqual(producer["pool_reset_bytes"], 0x1E0)
        self.assertEqual(producer["pooled_buffer"]["capacity_offset"], "0x28")
        self.assertEqual(producer["pooled_buffer"]["data_offset"], "0x30")
        self.assertEqual(producer["history"]["descriptor_bytes"], 16)
        self.assertFalse(producer["history"]["copied_wmi_payload"])
        self.assertTrue(producer["history"]["cursor_precedes_record_writes"])
        for field in ("active_ce_table_observed", "live_source_span_qualified",
                      "live_cache_sync_qualified", "exporter_connected"):
            self.assertIs(producer[field], False)


if __name__ == "__main__":
    unittest.main()
