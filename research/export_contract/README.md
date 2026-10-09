# Owned timestamp exporter: offline prototype

These software prototypes own and validate bounded records at an application
handoff boundary. The original C timestamp exporter accepts synthetic records;
the raw broker and source-record layer also support unqualified saved replay.
They do not open a device, implement a kernel handler or qualify a hardware clock.

<!-- research-history:2026-10-09 -->
**Research context (2026-10-09):** Tool guide. Use the linked account for goals, result versions, failed assumptions and remaining qualification gates. [Current account](../../docs/research-history/README.md) · [Timeline](../../docs/research-history/timeline.md) · [Previous version](../../archive/2026-10-09-pre-refresh-e9d71b8/pages/research__export_contract__README.md).
<!-- /research-history -->

## Contents

- [Source-operation records](../../docs/evidence/source-operation-record.md): [Python encoder/consumer](source_record.py) keeps original bytes, operation metadata and explicit unknowns together inside the existing broker payload. Diagnostic fixtures/replay only.
- [Concurrent raw-event response broker](../../docs/evidence/raw-event-response-broker.md): native user-mode queue, complete publication, application read tickets, cancellation, loss counters and two-stage shutdown. Fixture/replay only; the Qualcomm kernel adapter remains unconnected.
- [Owned MLO and management-event extension](../../docs/evidence/owned-event-extension.md): tested software ownership, decoding, rejection and generation behavior; separate from live hardware qualification.
- [Contract, limits and validation](../../docs/evidence/owned-timestamp-export-prototype.md)
- [C API and fixed layout](timestamp_export.h)
- [Exporter implementation](timestamp_export.c)
- [Offline native regression harness](../../tests/native_timestamp_export.c)
- [Windows build and test script](Test-TimestampExport.ps1)

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
