"""File-only exact-build IHV route checks. No private operation is executed."""
import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pefile
from research.adapters.inspect_ihv_queries import MAX_BYTES, inspect_image, main


class IhvQueryTests(unittest.TestCase):
    def test_reject_input_before_pe_interpretation(self):
        with patch("research.adapters.inspect_ihv_queries.pefile.PE") as parser:
            for data in (b"", b"MZ" + b"\0" * 1024, bytearray(4), b"\0" * (MAX_BYTES + 1)):
                with self.subTest(kind=type(data), size=len(data)), self.assertRaises(ValueError):
                    inspect_image(data)
            parser.assert_not_called()

    def test_cli_preserves_existing_file_and_missing_input_has_no_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "receipt.json"
            for existing in (False, True):
                if existing:
                    output.write_text("keep", encoding="utf-8")
                with patch("sys.argv", ["inspect", "--driver", str(root / "absent.sys"),
                                       "--output", str(output)]), contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as raised:
                        main()
                self.assertEqual(raised.exception.code, 1)
                if existing:
                    self.assertEqual(output.read_text(), "keep")
                else:
                    self.assertFalse(output.exists())

    @unittest.skipUnless(os.environ.get("WIFI_TIME_DRIVER_FIXTURE"), "Owned exact-build fixture not configured")
    def test_owned_routes_keep_control_and_timing_qualification_separate(self):
        data = Path(os.environ["WIFI_TIME_DRIVER_FIXTURE"]).read_bytes()
        result = inspect_image(data)
        self.assertEqual(len(result["selectors"]), 15)
        self.assertEqual(len(result["ranges"]), 14)
        self.assertEqual(result["dispatch"]["query"], "0x39528")
        self.assertEqual(result["gpio"]["command_id"], "0x1e002")
        self.assertEqual(result["gpio"]["gpio_number"], 1)
        self.assertEqual(result["bus_read"]["get_bus_data_offset"], "0x398")
        calls = {(item["rva"], item["target_rva"]) for item in result["selected_direct_branches"]}
        for edge in (("0x3980c", "0x3a950"), ("0x3984c", "0x2d6f0"),
                     ("0x39a30", "0xcb48"), ("0xcb64", "0x183058")):
            self.assertIn(edge, calls)
        for flag in ("live_request_sent", "complete_call_coverage", "read_only_profile_qualified",
                     "complete_timing_event_export_qualified", "hardware_qpc_qualified"):
            self.assertFalse(result[flag])
        with self.assertRaisesRegex(ValueError, "qualified build"):
            inspect_image(data[:-1] + bytes([data[-1] ^ 1]))

    @unittest.skipUnless(os.environ.get("WIFI_TIME_DRIVER_FIXTURE"), "Owned exact-build fixture not configured")
    def test_inner_fences_reject_altered_selector_gpio_and_bus_contract(self):
        data = Path(os.environ["WIFI_TIME_DRIVER_FIXTURE"]).read_bytes()
        pe = pefile.PE(data=data)
        try:
            for rva in (0x39BF8, 0x183114, 0xCB54, 0x2F1E4, 0x2EF790):
                altered = bytearray(data)
                altered[pe.get_offset_from_rva(rva)] ^= 1
                # Test only: bypass outer hash validation to reach inner checks.
                with self.subTest(rva=hex(rva)), patch("research.adapters.inspect_ihv_queries.validate_driver"), self.assertRaises(ValueError):
                    inspect_image(bytes(altered))
        finally:
            pe.close()


if __name__ == "__main__":
    unittest.main()
