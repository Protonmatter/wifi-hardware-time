"""Real exporter stdio failures must prevent a successful export exit status."""
from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from typing import Iterator
import unittest

ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def _temporary_output_directory() -> Iterator[str]:
    temporary = tempfile.TemporaryDirectory(prefix="trace-export-output-")
    try:
        yield temporary.name
    finally:
        # An exited Windows executable can remain briefly locked. Retry only
        # that cleanup failure; never suppress it or mask other I/O failures.
        for attempt in range(11):
            try:
                temporary.cleanup()
                break
            except PermissionError as error:
                if attempt == 10:
                    raise PermissionError(
                        f"Test output cleanup still denied after one second: {temporary.name}"
                    ) from error
                time.sleep(0.1)


class TraceExportOutputTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Requires Windows SDK and native Windows pipes")
    def test_buffered_output_failure_rejects_both_exports(self) -> None:
        configured = os.environ.get("WIFI_TIME_NATIVE_CC")
        compiler = shutil.which(configured or "cl")
        if not compiler:
            if configured:
                self.fail("Configured compiler unavailable")
            self.skipTest("MSVC developer environment unavailable")
        if Path(compiler).name.lower() not in {"cl", "cl.exe"}:
            self.fail("This Windows exporter test requires MSVC")
        with _temporary_output_directory() as directory:
            # Only the real file preflight sees this byte. ETW reading is stubbed.
            (Path(directory) / "synthetic-input.etl").write_bytes(b"x")
            for profile, flags in (("tsf", ["/DTEST_TSF_EXPORTER"]), ("registry", [])):
                with self.subTest(profile=profile):
                    binary = Path(directory) / f"{profile}.exe"
                    command = [compiler, "/nologo", "/W4", "/WX", "/O2", *flags,
                               str(ROOT / "tests/native_trace_export_output.c"), f"/Fe{binary}",
                               "/link", "advapi32.lib"]
                    built = subprocess.run(command, cwd=directory, capture_output=True,
                                           text=True, timeout=60, check=False)
                    self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
                    good = subprocess.run([str(binary), "good"], cwd=directory,
                                          capture_output=True, text=True, timeout=5, check=False)
                    self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
                    rows = [json.loads(line) for line in good.stdout.splitlines()]
                    self.assertEqual([row["kind"] for row in rows], ["header", "summary"])
                    self.assertEqual(rows[-1]["exported"], 0)
                    self.assertEqual(rows[-1]["process_status"], 0)
                    self.assertEqual(rows[-1]["close_status"], 0)
                    self.assertIs(rows[-1]["bound_failure"], False)
                    broken = subprocess.run([str(binary), "broken"], cwd=directory,
                                            capture_output=True, text=True, timeout=5, check=False)
                    self.assertEqual(broken.returncode, 1,
                                     f"{profile} returned success despite a broken output pipe: "
                                     + broken.stdout + broken.stderr)


if __name__ == "__main__":
    unittest.main()
