"""Compile/run the offline C contract when a local compiler is on PATH.

No compiler installation or network access. MSVC needs an initialized developer
environment; the PowerShell runner supplies that environment on Windows.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class NativeExportContractTests(unittest.TestCase):
    def test_native_contract(self) -> None:
        configured = os.environ.get("WIFI_TIME_NATIVE_CC")
        compiler = shutil.which(configured) if configured else next(
            (path for name in ("cl", "cc", "clang", "gcc")
             if (path := shutil.which(name))), None
        )
        if not compiler:
            if configured:
                self.fail("WIFI_TIME_NATIVE_CC does not resolve to a compiler")
            self.skipTest("No C compiler on PATH; run Test-TimestampExport.ps1 on Windows")
        repo = Path(__file__).resolve().parents[1]
        sources = [repo / "tests/native_timestamp_export.c",
                   repo / "research/export_contract/timestamp_export.c"]
        with tempfile.TemporaryDirectory(prefix="owned-timestamp-export-") as temp:
            binary = Path(temp) / ("contract.exe" if os.name == "nt" else "contract")
            if Path(compiler).name.lower() in {"cl", "cl.exe"}:
                command = [compiler, "/nologo", "/std:c11", "/W4", "/WX", "/O2",
                           *map(str, sources), f"/Fe{binary}"]
            else:
                command = [compiler, "-std=c11", "-Wall", "-Wextra", "-Werror",
                           "-pedantic", "-O2", *map(str, sources), "-o", str(binary)]
            build = subprocess.run(command, cwd=temp, capture_output=True, text=True,
                                   timeout=60, check=False)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            run = subprocess.run([str(binary)], cwd=temp, capture_output=True,
                                 text=True, timeout=15, check=False)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn("all offline contract checks passed", run.stdout)
