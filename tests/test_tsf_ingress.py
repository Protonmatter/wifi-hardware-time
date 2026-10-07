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

    @unittest.skipUnless(os.environ.get("WIFI_TIME_DRIVER_FIXTURE"), "Owned exact-build driver not configured")
    def test_pool_constructor_and_mapping_are_not_sync_attestations(self) -> None:
        result = inspect_image(Path(os.environ["WIFI_TIME_DRIVER_FIXTURE"]).read_bytes())
        pool = result["manual_pool_admission"]
        self.assertEqual(pool["constructor_rva"], "0x187c20")
        self.assertEqual(pool["buffer_count"], 0x3880)
        self.assertEqual(pool["backing_block_bytes"] // pool["buffer_capacity_bytes"], 32)
        self.assertEqual(pool["backing_blocks"] * 32, pool["buffer_count"])
        self.assertEqual(pool["hif_pool_store_rva"], "0x1972c0")
        self.assertFalse(pool["null_cached_mdl_aborts_allocation_loop"])
        self.assertFalse(pool["map_return_zero_proves_flush"])
        self.assertFalse(pool["live_allocator_branch_observed"])
        self.assertFalse(pool["live_coherency_qualified"])
        self.assertEqual(result["selected_allocation_imports"], {
            "0x2ed418": "MmAllocateContiguousMemorySpecifyCache",
            "0x2ed440": "IoAllocateMdl",
            "0x2ed450": "MmBuildMdlForNonPagedPool",
        })
        branches = {(item["rva"], item["target_rva"]) for item in result["selected_direct_branches"]}
        self.assertIn(("0x188018", "0x188024"), branches)
        self.assertIn(("0x18808c", "0x1971f0"), branches)

    @unittest.skipUnless(os.environ.get("WIFI_TIME_DRIVER_FIXTURE"), "Owned exact-build driver not configured")
    def test_wmi_copy_boundary_precedes_header_loss_and_does_not_install_an_export(self) -> None:
        result = inspect_image(Path(os.environ["WIFI_TIME_DRIVER_FIXTURE"]).read_bytes())
        boundary = result["manual_wmi_copy_boundary"]
        self.assertEqual(boundary["before_header_load_rva"], "0x168d7c")
        self.assertEqual(boundary["selector_mask_rva"], "0x168d80")
        self.assertEqual(boundary["length_store_rva"], "0x168d94")
        self.assertEqual(boundary["offset_store_rva"], "0x168da4")
        self.assertEqual(boundary["decoder_call_rva"], "0x168e0c")
        self.assertLess(int(boundary["before_header_load_rva"], 16),
                        int(boundary["length_store_rva"], 16))
        self.assertFalse(boundary["source_span_validated_by_inspector"])
        self.assertFalse(boundary["exporter_installed"])
        self.assertFalse(result["application_export_established"])
        self.assertFalse(result["hardware_qpc_qualified"])

    @unittest.skipUnless(os.environ.get("WIFI_TIME_DRIVER_FIXTURE"), "Owned exact-build driver not configured")
    def test_common_buffer_contract_is_named_without_promoting_live_coherency(self) -> None:
        result = inspect_image(Path(os.environ["WIFI_TIME_DRIVER_FIXTURE"]).read_bytes())
        dma = result["manual_dma_contract"]
        self.assertEqual(dma["selector_file_value"], 1)
        self.assertEqual(dma["selector_writer_value"], 1)
        self.assertEqual(dma["adapter_global_rva"], "0x3958b8")
        self.assertEqual(dma["wdf_function_indices"], {
            "WdfDmaEnablerCreate": 94, "WdfDmaEnablerWdmGetDmaAdapter": 385,
            "WdfMemoryGetBuffer": 194, "WdfObjectDelete": 208,
        })
        self.assertEqual(dma["dma_operation_slots"], {
            "FreeCommonBuffer": "0x18", "AllocateCommonBufferWithBounds": "0x110",
        })
        self.assertEqual(dma["cache_type_override"], "MmCached")
        self.assertEqual(dma["allocation_flags"], 0)
        self.assertEqual(dma["returned_dma_address_kind"], "device logical address")
        self.assertEqual(dma["enabler_address_width_override"], 36)
        self.assertEqual(dma["enabler_dma_version_override"], 3)
        for flag in ("live_adapter_observed", "live_allocator_branch_observed",
                     "live_coherency_qualified", "teardown_order_qualified"):
            self.assertFalse(dma[flag])
        self.assertFalse(result["application_export_established"])
        branches = {(item["rva"], item["target_rva"]) for item in result["selected_direct_branches"]}
        self.assertIn(("0x32898", "0x2e268"), branches)
        self.assertIn(("0x328bc", "0x35ba8"), branches)

    @unittest.skipUnless(os.environ.get("WIFI_TIME_DRIVER_FIXTURE"), "Owned exact-build driver not configured")
    def test_shutdown_timeouts_do_not_become_successful_rundown(self) -> None:
        result = inspect_image(Path(os.environ["WIFI_TIME_DRIVER_FIXTURE"]).read_bytes())
        shutdown = result["manual_receive_shutdown"]
        self.assertEqual(shutdown["pci_disable_target_rva"], "0x1b57a0")
        self.assertEqual(shutdown["dpc_drain_failure_status"], 12)
        self.assertFalse(shutdown["pci_caller_checks_dpc_drain_status"])
        completion = shutdown["completion_shutdown"]
        self.assertEqual(completion["rva"], "0x1b32d8")
        self.assertEqual(completion["max_stall_rounds"], 21)
        self.assertEqual(completion["stall_us_per_round"], 50000)
        self.assertFalse(completion["nominal_stall_sum_is_wall_clock_bound"])
        self.assertFalse(completion["caller_receives_success_status"])
        self.assertFalse(shutdown["live_rundown_qualified"])
        self.assertFalse(shutdown["dma_enabler_release_order_qualified"])
        branches = {(item["rva"], item["target_rva"]) for item in result["selected_direct_branches"]}
        for pair in (("0x196d14", "0x196ad8"), ("0x196d24", "0x1b4488"),
                     ("0x1b57ec", "0x1b5488"), ("0x1b57f4", "0x1b1f58"),
                     ("0x1b4698", "0x1b32d8"), ("0x186780", "0x186128"),
                     ("0x1867b4", "0x8520")):
            self.assertIn(pair, branches)

    @unittest.skipUnless(os.environ.get("WIFI_TIME_DRIVER_FIXTURE"), "Owned exact-build driver not configured")
    def test_thread_wait_and_unregister_flag_keep_their_actual_scope(self) -> None:
        result = inspect_image(Path(os.environ["WIFI_TIME_DRIVER_FIXTURE"]).read_bytes())
        shutdown = result["manual_receive_shutdown"]
        self.assertEqual(shutdown["thread_waits"], [
            dict(rva="0x1b5e90", handle_offset="0xaf0", signal_offset="0xac0"),
            dict(rva="0x1b5dd8", handle_offset="0xa58", signal_offset="0xa28"),
        ])
        self.assertIsNone(shutdown["thread_wait_timeout_pointer"])
        self.assertTrue(shutdown["thread_wait_requires_reference_success"])
        self.assertEqual(shutdown["unregister_flag"],
                         dict(rva="0x1b6860", adapter_flag_offset="0x2ec", value=0))
        self.assertFalse(shutdown["unregister_flag_is_callback_join"])
        self.assertFalse(result["application_export_established"])
        self.assertFalse(result["fresh_sampling_qualified"])


if __name__ == "__main__":
    unittest.main()
