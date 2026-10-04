# Owned timestamp exporter: offline prototype

This C11 prototype owns and validates bounded synthetic records at an application
handoff boundary. It does not open a device, implement a kernel handler, expose an
IOCTL, or qualify real timestamp meaning. Every accepted record is explicitly
synthetic and has `live_clock_eligible == 0`.

## Contents

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
