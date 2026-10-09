# Owned timestamp exporter: offline prototype

> **Archive — not current operating instructions.** Historical documentation at [e9d71b843651](https://github.com/Protonmatter/wifi-hardware-time/commit/e9d71b84365122ff2640e240b20fc1dbb834388a). Relative links are rebased for reading. [Exact original bytes](../originals/research__export_contract__README.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

These software prototypes own and validate bounded records at an application
handoff boundary. The original C timestamp exporter accepts synthetic records;
the raw broker and source-record layer also support unqualified saved replay.
They do not open a device, implement a kernel handler or qualify a hardware clock.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** A QUTS client-owned byte return is now located statically. Keep client ownership, server publication, firmware identity and timing accuracy as separate qualification states. See [current findings](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/knowledge/current-findings.md).
<!-- /historical-context -->

## Contents

- [Source-operation records](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/source-operation-record.md): [Python encoder/consumer](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/export_contract/source_record.py) keeps original bytes, operation metadata and explicit unknowns together inside the existing broker payload. Diagnostic fixtures/replay only.
- [Concurrent raw-event response broker](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/raw-event-response-broker.md): native user-mode queue, complete publication, application read tickets, cancellation, loss counters and two-stage shutdown. Fixture/replay only; the Qualcomm kernel adapter remains unconnected.
- [Owned MLO and management-event extension](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/owned-event-extension.md): tested software ownership, decoding, rejection and generation behavior; separate from live hardware qualification.
- [Contract, limits and validation](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/owned-timestamp-export-prototype.md)
- [C API and fixed layout](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/export_contract/timestamp_export.h)
- [Exporter implementation](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/export_contract/timestamp_export.c)
- [Offline native regression harness](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/tests/native_timestamp_export.c)
- [Windows build and test script](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/export_contract/Test-TimestampExport.ps1)

## Run

With installed Visual Studio C tools and SDK, as an ordinary user:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File research/export_contract/Test-TimestampExport.ps1 -Architecture arm64
```

Use `-Architecture x64` for an x64 target. The script builds and runs only the
offline tests. Exit 0 means those checks passed; exit 1 means build/test failure.
The executable and objects are written under ignored `artifacts/owned-export-*`.
No dependencies are downloaded. Remove that generated directory to undo the build.

On hosts with `cc`, `clang`, `gcc`, or developer-shell `cl` on PATH:

```powershell
python -m unittest discover -s tests -p test_native_export_contract.py -v
```

The Python runner uses a temporary output directory and skips if no compiler is
available. Set `WIFI_TIME_NATIVE_CC` to an executable name or path to require a
specific compiler; an unresolved explicit choice fails. It accepts no extra flags
in that variable. Compilation/test timeouts are 60/15 seconds.

The C record is **native endian** with checked offsets and size. It is a proposed
application contract, not a cross-endian wire format or production driver ABI.
All state operations require caller serialization; no live lock is qualified.
