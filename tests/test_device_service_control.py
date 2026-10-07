"""Compile/self-test the positive control without opening a WLAN handle."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DeviceServiceControlTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Requires Windows SDK and native Windows ABI")
    def test_native_fixed_response_and_cli_rejections_without_hardware(self):
        configured = os.environ.get("WIFI_TIME_NATIVE_CC")
        compiler = shutil.which(configured or "cl")
        if not compiler:
            if configured:
                self.fail("Configured compiler unavailable")
            self.skipTest("MSVC developer shell not configured")
        if Path(compiler).name.lower() not in {"cl", "cl.exe"}:
            self.fail("This Windows probe test requires MSVC")
        with tempfile.TemporaryDirectory(prefix="device-service-control-") as directory:
            binary = Path(directory) / "probe.exe"
            command = [compiler, "/nologo", "/W4", "/WX", "/O2",
                       str(ROOT / "research/adapters/device_service_control.c"), f"/Fe{binary}",
                       "/link", "wlanapi.lib", "iphlpapi.lib", "ole32.lib", "advapi32.lib"]
            built = subprocess.run(command, cwd=directory, capture_output=True, text=True, timeout=60)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            for args, expected in ((["--self-test"], 0), (["--help"], 0), ([], 2),
                                   (["--execute", "0", "bad-guid"], 2),
                                   (["--execute", "20", "bad-guid"], 2),
                                   (["--execute", "20", "bad-guid", "--arbitrary-opcode"], 2)):
                with self.subTest(args=args):
                    result = subprocess.run([str(binary), *args], capture_output=True, text=True, timeout=5)
                    self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
                    self.assertNotIn('"test_get_attempted":true', result.stdout)

    @unittest.skipUnless(os.name == "nt", "Requires Windows PowerShell child process")
    def test_launcher_rejection_exit_and_timeout_without_adapter_queries(self):
        powershell = shutil.which("powershell.exe")
        self.assertIsNotNone(powershell)
        result = subprocess.run([powershell, "-NoProfile", "-File",
                                 str(ROOT / "tests/Test-DeviceServiceControl.ps1")],
                                cwd=ROOT, capture_output=True, text=True, timeout=25)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
