"""Offline trace-path evidence and configuration lexical boundaries."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from research.tsf.inspect_event_export_candidates import MAX_BYTES,inspect_image,summarize_config,summarize_catalog

ROOT=Path(__file__).resolve().parents[1]


class EventExportCandidateTests(unittest.TestCase):
    def test_catalog_definitions_are_not_live_measurements_or_qdss_schema(self):
        data=b"VERSION:123\n99999,?,opaque\xff\n25950,iII,[ wlan_vdev.c : 8 ] vdev_id = %d, tsf_low = %x, tsf_high = %x\n"
        result=summarize_catalog(data)
        self.assertEqual(result["version"],123)
        self.assertEqual(result["selected_records"][0]["named_fields"],["vdev_id","tsf_low","tsf_high"])
        self.assertEqual(result["selected_records"][0]["source_file"],"wlan_vdev.c")
        for key in ("live_record_observed","runtime_firmware_version_matched","qdss_stream_binding_qualified","clock_eligible"):
            self.assertIs(result[key],False)

    def test_catalog_rejects_ambiguous_or_unbounded_definitions(self):
        row=b"25950,i,[ file.c : 1 ] vdev_id = %d\n"
        for data in (b"",b"VERSION:4294967296\n"+row,b"VERSION:1\n"+row+row,
                     b"VERSION:1\nno rows\n",b"VERSION:1\n25950,i,unknown format\n",bytes(4*1024*1024+1)):
            with self.subTest(size=len(data)),self.assertRaises(ValueError): summarize_catalog(data)
    def test_reject_unknown_driver_type_and_size(self):
        for data in (b"not a driver",bytearray(64),None,bytes(MAX_BYTES+1)):
            with self.subTest(kind=type(data)),self.assertRaises(ValueError): inspect_image(data)

    def test_comments_are_not_enabled_configuration(self):
        data=(b"seq_type:mac_event_trace;\r\n //seq_type:mac_tlv_trace;\r\n"
              b"subsys_cfg_start:pmac0;\r\nseq_type:lpm_trace; // note\r\n")
        result=summarize_config(data)
        self.assertEqual(result["uncommented_sequence_types"],["mac_event_trace","lpm_trace"])
        self.assertEqual(result["commented_sequence_types"],["mac_tlv_trace"])
        self.assertEqual(result["named_subsystems"],["pmac0"])
        self.assertFalse(result["configuration_applied"])
        self.assertFalse(result["runtime_selection_known"])

    def test_lexical_anomaly_is_preserved_not_repaired_or_executed(self):
        data=b"//item:0x0x01;\nitem:0x0x02;\nqtimer_mode:unknown;\n"
        result=summarize_config(data)
        self.assertEqual(result["repeated_hex_prefix_lines"],[2])
        self.assertEqual(result["timing_named_directives"],["qtimer_mode"])
        self.assertEqual(data,b"//item:0x0x01;\nitem:0x0x02;\nqtimer_mode:unknown;\n")
        self.assertFalse(result["firmware_record_schema_qualified"])

    def test_config_bounds_and_encoding_rejected(self):
        for data in (b"",bytearray(5),b"\xff",b"a"*1025,b"\n"*2049,b"x"*65537):
            with self.subTest(size=len(data)),self.assertRaises(ValueError): summarize_config(data)

    def test_cli_preserves_output_and_rejects_invalid_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);driver=root/"invalid.sys";driver.write_bytes(b"invalid")
            output=root/"result.json"
            cmd=[sys.executable,str(ROOT/"research/tsf/inspect_event_export_candidates.py"),
                 "--driver",str(driver),"--output",str(output)]
            result=subprocess.run(cmd,capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,1)
            self.assertFalse(output.exists())
            output.write_text("keep")
            result=subprocess.run(cmd,capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,1)
            self.assertIn("already exists",result.stderr)
            self.assertEqual(output.read_text(),"keep")

    @unittest.skipUnless(os.environ.get("WIFI_TIME_DRIVER_FIXTURE"),"Owned exact-build driver required")
    def test_owned_paths_keep_selector_namespaces_and_qualifications_separate(self):
        data=Path(os.environ["WIFI_TIME_DRIVER_FIXTURE"]).read_bytes()
        result=inspect_image(data)
        self.assertEqual(result["captureh"]["event_id"],"0x1e003")
        self.assertEqual(result["captureh"]["schema_entries"][0]["element_size"],16)
        self.assertEqual(result["qdss"]["private_ioctl"],"0x98742004")
        self.assertEqual(result["qdss"]["qmi_save_indication"],"0x41")
        self.assertEqual(result["qdss"]["internal_message"],"0x1f")
        self.assertEqual(result["qdss"]["chunk_request"],"0x42")
        self.assertEqual(result["firmware_diag"]["wmi_event_id"],"0x1d011")
        self.assertFalse(result["firmware_diag"]["owned_application_return_qualified"])
        self.assertNotEqual(result["qdss"]["decoded_save_object_bytes"],result["qdss"]["internal_queue_copy_bytes"])
        for key in ("live_request_sent","configuration_applied","source_ownership_qualified","hardware_qpc_qualified","clock_eligible"):
            self.assertIs(result[key],False)
        branches={(x["rva"],x["target_rva"]) for x in result["selected_direct_branches"]}
        self.assertIn(("0x14eae4","0x233d60"),branches)
        self.assertIn(("0x14ed8c","0x14f448"),branches)
        self.assertIn(("0x1dda90","0x16a078"),branches)
        with self.assertRaises(ValueError): inspect_image(data[:-1]+bytes([data[-1]^1]))


if __name__=="__main__": unittest.main()
