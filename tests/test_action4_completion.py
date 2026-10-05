"""Offline action-4 image checks, without sending requests or opening devices."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from research.tsf.inspect_action4_completion import MAX_BYTES, WINDOWS, inspect_image

ROOT = Path(__file__).resolve().parents[1]


class Action4CompletionTests(unittest.TestCase):
    def test_reject_unknown_build_wrong_type_and_oversize(self) -> None:
        for data in (b"not the driver", bytearray(64), None, bytes(MAX_BYTES + 1)):
            with self.subTest(data_type=type(data)), self.assertRaises(ValueError):
                inspect_image(data)

    def test_cli_refuses_overwrite_and_leaves_no_receipt_on_bad_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            driver = Path(tmp) / "unqualified.sys"
            driver.write_bytes(b"not the driver")
            output = Path(tmp) / "receipt.json"
            command = [sys.executable, str(ROOT / "research/tsf/inspect_action4_completion.py"),
                       "--driver", str(driver), "--output", str(output)]
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(output.exists())
            output.write_text("preserve me", encoding="utf-8")
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 1)
            self.assertIn("already exists", result.stderr)
            self.assertEqual(output.read_text(encoding="utf-8"), "preserve me")

    @unittest.skipUnless(os.environ.get("WIFI_TIME_DRIVER_FIXTURE"), "Owned exact-build driver not configured")
    def test_owned_image_evidence_and_mutation_rejection(self) -> None:
        data = Path(os.environ["WIFI_TIME_DRIVER_FIXTURE"]).read_bytes()
        result = inspect_image(data)
        self.assertEqual(result["optional_barrier_argument"], 0)
        self.assertEqual(result["manually_traced_barrier_types"],
                         {"0x6002": "peer-delete queue", "0x5002": "vdev-delete queue"})
        self.assertEqual([(item["name"], int(item["rva"], 16), item["bytes"])
                          for item in result["code_windows"]], list(WINDOWS))
        for item in result["code_windows"]:
            self.assertEqual(len(item["sha256"]), 64)
        for field in ("request_completion_is_sampling_fence_qualified",
                      "response_association_qualified", "fresh_sampling_qualified", "live_request_sent"):
            self.assertIs(result[field], False)
        with self.assertRaisesRegex(ValueError, "qualified build"):
            inspect_image(data[:-1] + bytes([data[-1] ^ 1]))


if __name__ == "__main__":
    unittest.main()
