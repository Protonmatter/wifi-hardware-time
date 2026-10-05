"""File-only WLANLIB provenance and negative-input checks."""
import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.adapters.inspect_wlanlib_dispatch import inspect_image, ioctl_fields, main


class WlanlibDispatchTests(unittest.TestCase):
    def test_methods_are_not_direction_or_safety_claims(self):
        fields = ioctl_fields(0xC3502406)
        self.assertEqual(fields, dict(device_type="0xc350", access_bits=0,
                                     function="0x901", method="METHOD_OUT_DIRECT"))
        self.assertEqual(ioctl_fields(0x81802C04)["method"], "METHOD_BUFFERED")

    def test_selector_requires_uint32_without_coercion(self):
        for value in (-1, 2**32, True, 1.0, "0x220182"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                ioctl_fields(value)

    def test_unknown_driver_never_reaches_pe_parsing(self):
        with patch("research.adapters.inspect_wlanlib_dispatch.pefile.PE") as parse:
            for value in (b"", b"MZ" + b"\0" * 1024):
                with self.assertRaisesRegex(ValueError, "qualified build"):
                    inspect_image(value)
            parse.assert_not_called()

    def test_existing_output_preserved_and_missing_input_leaves_no_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "receipt.json"
            for exists in (False, True):
                if exists:
                    output.write_text("preserve", encoding="utf-8")
                with patch("sys.argv", ["inspect", "--driver", str(root / "absent.sys"),
                                       "--output", str(output)]), contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as raised:
                        main()
                self.assertEqual(raised.exception.code, 1)
                if exists:
                    self.assertEqual(output.read_text(), "preserve")
                else:
                    self.assertFalse(output.exists())

    @unittest.skipUnless(os.environ.get("WIFI_TIME_DRIVER_FIXTURE"), "Owned exact-build fixture not configured")
    def test_owned_image_keeps_namespaces_and_qualification_separate(self):
        data = Path(os.environ["WIFI_TIME_DRIVER_FIXTURE"]).read_bytes()
        result = inspect_image(data)
        selectors = {item["name"]: item for item in result["ioctl_selectors"]}
        self.assertEqual(selectors["iwpriv_command"]["value"], "0x220182")
        self.assertEqual(len(result["ioctl_selectors"]), 11)
        self.assertEqual({item["namespace"] for item in result["other_constants"]},
                         {"wmi_command_id", "wmi_event_id", "ntstatus"})
        for field in ("live_request_sent", "runtime_mode_observed", "concurrent_copy_qualified",
                      "timing_schema_qualified", "hardware_qpc_qualified"):
            self.assertFalse(result[field])
        with self.assertRaisesRegex(ValueError, "qualified build"):
            inspect_image(data[:-1] + bytes([data[-1] ^ 1]))


if __name__ == "__main__":
    unittest.main()
