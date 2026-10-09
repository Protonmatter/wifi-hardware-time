# QUTS: observed discovery failure and the underlying transport

A corrected five-second trace captured QUTS querying the active Wi-Fi adapter's
missing control-endpoint value at the code location identified in Ghidra. All
20 control reads were present. Separately, static analysis now reaches a concrete
Windows endpoint-opening path beneath `CommonIo`. This advances discovery and
transport attribution; a Wi-Fi firmware timing record remains unavailable.

<!-- research-history:2026-10-09 -->
**Research context (2026-10-09):** Scoped technical reference. Build-specific findings and operational prerequisites retain their stated scope. [Current account](../research-history/README.md) · [Timeline](../research-history/timeline.md) · [Previous version](../../archive/2026-10-09-pre-refresh-e9d71b8/pages/docs__adapters__quts-live-gate-and-commonio.md).
<!-- /research-history -->

## Contents

- [Scope and provenance](#scope-and-provenance)
- [What the live capture proves](#what-the-live-capture-proves)
- [Why the earlier attempts did not qualify](#why-the-earlier-attempts-did-not-qualify)
- [How the query is associated](#how-the-query-is-associated)
- [What CommonIo contains](#what-commonio-contains)
- [Reproduce and validate](#reproduce-and-validate)
- [Next dependency and glossary](#next-dependency-and-glossary)

## Scope and provenance

Observation date: **2026-10-04**. The successful capture is private attempt `06`,
with a five-second observation interval and additional setup, control and save
time. It follows the [earlier route investigation](quts-mhi-route-validation.md).

| Component | Exact identity |
|---|---|
| `QUTS.exe` | ARM64, version `3,96,2`; SHA-256 `8e6de10a298f8378e9d289ad11a33018654a29d155e56588f9427d53ed639297` |
| Wi-Fi driver | `qcwlanhmt8380.sys`, version `1.0.4374.1300`; SHA-256 `ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115` |
| Executed observer | SHA-256 `525dad8f8fe3853be69351fd440cd9471941d6b1f60aa2878bee48e7ad67c956` |
| Executed WPR profile | SHA-256 `1fc7a009f62ce28937269d05d5fde6b17bb452262ea364fb70d069b7fb48f839` |
| Static analysis | Ghidra 12.1.4; existing analyzed project, read-only, no whole-program reanalysis |

The observer checked adapter and process identity before and after capture.
Wi-Fi remained **Up** with the same driver version. Elevated checks bound each
selected QUTS process to its executable path, disk hash, creation time and module
base. This is not an attestation of every byte of its live executable memory.

The campaign used Windows registry tracing and read-only registry controls.
It sent no QUTS RPC, private device IOCTL or firmware command, and made no device,
service, WLAN, logging-mask or clock change. Every started trace stopped its own
named instance. Raw traces and machine identifiers remain in ignored
`artifacts/quts-commonio-20261004/`.

## What the live capture proves

| Check | Observed result |
|---|---|
| Known positive controls | **20/20**: five reads of each of two values, at both start and end |
| QUTS queries on the exact active adapter key | **12** queries of `QCDeviceControlFile` |
| Returned kernel status | All 12: `0xC0000034`, `STATUS_OBJECT_NAME_NOT_FOUND` |
| Matched call stacks | **12/12**, each containing the three expected return addresses in one stack record |
| ETL loss counters | Zero events and buffers lost |
| WPR controller health | Zero events lost and dropped events |
| Native export | Complete; `ProcessTrace` and `CloseTrace` succeeded; no record/output-bound failure |

The stack return RVAs are `0x0b2cd0`, `0x0b5168` and `0x0b5ddc`. An RVA is an
offset within the executable; adding the captured process's module base gives
the address used for matching. These locations connect the registry query to
the inspected validation caller and discovery thread.

**Supported conclusion:** QUTS executed the selected control-endpoint query for
this adapter and it failed because that value was not found. Combined with the
[static gate](quts-discovery-gate.md) and the adapter's PCI identity, this supports
the explanation for its omission from this discovery route.

**Still separate:** the trace does not record execution of the following CPU
conditional branch, a live MHI connection, a firmware timing event, a hardware
sampling instant, or a hardware-to-QPC conversion. It does not show that all
private Wi-Fi diagnostic routes are absent. Registry queries in this report are
not QUTS device/protocol RPC results; the earlier enumeration remains its own run.

## Why the earlier attempts did not qualify

| Attempt | Result and disposition |
|---|---|
| 01–03 | Earlier manifest-provider attempts lacked coverage; the first corrected-profile launch was cancelled. See the historical report. |
| 04: 8 MiB collector | Registry and stack events appeared, but the observer's controls were not retained. Useful partial evidence only. |
| 05: 8 MiB, bracketed start/end controls | Nine end controls survived; no start controls did. Zero reported loss did not establish complete observation coverage. |
| 06: 32 MiB, process/loader metadata, short settling interval | All 20 controls and 12 attributed query failures were retained. This is the qualifying capture. |

The first native export of attempt 06 exceeded its conservative 64 MiB output
budget and explicitly reported failure. The same saved trace was then exported
with a **128 MiB output budget**, retaining the **64 MiB input-file limit** and
two-million-event limit. No new hardware experiment was needed. The complete
export is `raw-events-v3-private.jsonl`; the failed partial export is retained.

The trace file is 52,297,728 bytes. Its total decoded stream contains 345,199
events, including 131,421 registry events and 73,923 stack events. These are
whole-trace totals, not counts of Wi-Fi timing records. The memory-buffer budget
does not bound metadata added when WPR saves the final ETL.

## How the query is associated

```text
Known registry reads at start and end
  |  Host QPC before/after each read, process ID and thread ID
  v
Saved Windows trace -----------> Positive-control coverage and loss checks
  |
  +--> Registry key lifecycle ---> Exact adapter's driver-key path
  |         (create/delete/rundown, including other processes)
  |
  +--> QueryValue event ----------> Status + original QPC + process/thread
  |                                      |
  +--> StackWalk event -------------------+ match all three identity fields
                                         |
                                         v
                         Expected QUTS return addresses in ONE stack
                                         |
                                         v
                        Attributed registry failure, not firmware time
```

Arrows show evidence joins, not packet flow. The decoder follows the documented
[registry event layout](https://learn.microsoft.com/en-us/windows/win32/etw/registry-typegroup1)
and [StackWalk identity fields](https://learn.microsoft.com/en-us/windows/win32/etw/stackwalk-event).

- The stack's embedded timestamp identifies the original event. Its delivery
  timestamp must not replace it.
- Registry key-control-block lifecycle events bind the key to its path. An
  `OpenKey` payload alone is not treated as the newly opened key's identity.
- Key deletion, unexplained reuse and same-timestamp lifecycle ambiguity reject
  attribution. Global lifecycle records are retained even for other processes.
- Duplicate query identities, duplicate qualifying stacks, or addresses split
  across stack records reject the join.
- A missing control, changed identity, incomplete export or nonzero/absent loss
  metadata blocks qualification. Missing target queries alone cannot prove that
  QUTS never queried the device.
- Control QPC brackets measure host registry operations. They do not bracket a
  NIC clock read and cannot be reused as hardware cross timestamps.

## What CommonIo contains

`CommonIo` is a shared transport interface. The DIAG protocol retains a
reference to it at object offset `+0x118`: constructor RVA `0x277e40` stores the
reference and getter `0x27ad70` returns it. `Diag::doSimpleConnect` at `0x1f38e0`
checks its state through virtual slot `+0x40` and opens it through slot `+0x48`.
The discovery worker creates that transport before choosing the DIAG protocol.

Recovered C++ type information and factory calls distinguish these implementations:

| Factory RVA | Allocated implementation | Inspected open method |
|---|---|---|
| `0x17efc0` | `Device::Communication::Usb` | `0x2aa050`, reaches `QcDevice::OpenDevice` |
| `0x17ef18` | `Device::Communication::QmiIo` | `0x294e80`, throws an invalid-open exception on this generic entry |
| `0x17ee80` | `Device::Communication::Ethernet` | `0x290f68`, throws an unsupported-I/O exception |
| `0x17ede8` | `Device::Communication::CommandIo` | `0x290280`, sets local state; not proof of a hardware open |

This prevents a misleading inference: a class or protocol label does not prove
that a particular device can be opened through it. The MHI predicate does not
uniquely identify which earlier transport-selection branch populated `CommonIo`.
No live discovery object has yet been bound to FastConnect on this route.

The concrete Windows-file path under the `Usb` implementation is:

```text
DIAG protocol's retained CommonIo reference
    -> virtual open slot +0x48
    -> Usb::open, RVA 0x2aa050
    -> QcDevice::OpenDevice, RVA 0x0b6920
    -> find discovered entry by description (entry +0x94)
    -> obtain stored endpoint path (entry +0x894)
    -> CreateFileW(endpoint, read/write, shared read/write, OPEN_EXISTING,
                   normal attributes + overlapped I/O)
    -> retain handle in Usb object at +0xa0
```

This is one inspected branch, not the entire function. Other branches handle
libusb/EUD and special QDSS/DPL naming. The common Windows-file branch can call
`SetCommState` and `SetCommTimeouts`; opening it is therefore not automatically a
passive existing-record read. Its failure log mentions a read-only attempt, but
this inspected branch shows no second `CreateFileW` proving that fallback.

Separately, `Usb` virtual slot `+0x60` resolves to `0x2ab358`, which reaches
`QcDevice::SendToDevice` at `0x0b7500`: `WriteFile`, then `GetOverlappedResult` for
pending I/O, with a returned byte count. This is a send path, not a receive getter.
Neither the transport name nor a generic shared-buffer argument identifies a
firmware timestamp schema or proves complete-record delivery.

## Reproduce and validate

**Capture prerequisites:** Windows 11, pinned installed QUTS/driver, elevated
console for execution, and a new private output directory. Preview requires no
elevation. The observer has no interactive prompts inside its execution path.

```powershell
./research/acquisition/Observe-QutsRegistry.ps1 -Seconds 5
# Execute only when a new live observation is intended:
./research/acquisition/Observe-QutsRegistry.ps1 -Execute -Seconds 5 `
  -OutputDirectory '<new-private-capture-directory>'
```

**Offline decoding:** in an ARM64 Visual Studio developer shell, build the
authored reader. It uses Windows trace APIs only; it does not load vendor code or
open a device. Select the PIDs from the private before-snapshot and the control
PID from the capture receipt.

```powershell
cl /nologo /W4 /WX /O2 research/acquisition/export_registry_trace.c `
  /Fe:<private-output>/export_registry_trace.exe `
  /Fo:<private-output>/export_registry_trace.obj advapi32.lib
<private-output>/export_registry_trace.exe <capture>/registry.etl `
  <quts-pid> <control-pid> > <new-private-output>.jsonl
python research/acquisition/analyze_quts_registry.py `
  <new-private-output>.jsonl <capture>
python -m unittest discover -s tests -p test_quts_registry_analysis.py -v
```

Use UTF-8/ASCII output redirection, such as PowerShell 7 or `cmd` redirection;
Windows PowerShell 5.1's default UTF-16 text redirection is not accepted by the
JSONL decoder. Include every selected QUTS PID, within the reader's eight-PID cap.
The reader retains global key-lifecycle events in addition to selected PIDs.

Exit codes:

- Observer: `0` means preview/capture completed; `1` means blocked/failed. Capture
  completion alone is not evidence qualification.
- Native reader: `0` complete export, `1` input/read/bound failure, `2` bad arguments.
- Python analyzer: `0` analysis completed, including an explicitly unqualified
  result; `1` malformed input. Consumers must inspect the qualification fields.

Cleanup/rollback: stop or cancel only the unique WPR instance named in the
private `result.json`. Offline tools change only their output files. No registry,
device or firmware rollback was needed for these observations.

Ghidra reproduction uses the existing hash-pinned project with `-noanalysis
-readOnly`, the existing `TraceQutsDiscovery.java`, and a fresh output for each
pass. Useful seed groups are `27ad70 277e40 1dead8`, `17efc0 17ef18 17ee80 17ede8`,
`2a7528 291458 28e3c8 290888`, `2aa050 294e80 290f68 290280`, and `b6920 b7500`.
Use `max-instructions:32768`. The actual `Usb` heap vtable is at RVA `0xfaa920`;
the underlying `Usb` vtable is at `0xfdd350`. Validate the slots against the exact
file before following indirect calls.

Validation on this local tree:

- Python compilation and full unittest discovery: **262 passed, zero skips**,
  with the ARM64 compiler and exact driver/Windows image fixtures configured.
- The 15 new offline tests cover malformed layouts, duplicate identities,
  mismatched stacks, deleted/reused keys, missing controls, loss and cleanup failure.
- Native ETL reader: ARM64 `cl /W4 /WX /O2` succeeded. Help, invalid/overflow PID,
  missing-file and non-ETL input checks returned the expected exit codes.
- PowerShell parser and Windows PowerShell 5.1 preview passed. The successful
  elevated capture used the script/profile hashes recorded above.
- Knowledge-index consistency, documentation navigation, diagram-source
  consistency and Git whitespace checks passed. No Mermaid source changed.
- PSScriptAnalyzer was unavailable. Hosted CI had not run at analysis completion;
  subsequent publication checks are tracked in PR #3.

## Next dependency and glossary

The [endpoint-writer and receive follow-up](quts-endpoint-writer-and-receive.md)
now locates that writer in `ScanDevices`, the `ReadFromDevice` helper and an owned
chunk-copy path. Concrete callback-to-DIAG association, an attributable live
FastConnect endpoint and bounded cancellation remain open. Do not create a
registry advertisement to bypass discovery; a label cannot create the missing
kernel transport.

After endpoint attribution, establish a bounded nonmutating receive operation
and its complete-record contract: returned length, cancellation, ownership,
producer/schema, timestamp clock, units, width, validity, identity and epoch.
Fresh hardware/QPC sampling remains a separate dependency. There is still no
second controlled node or independent reference for calibrated synchronization.

- **CommonIo:** QUTS's common interface for different communication transports.
- **DIAG:** Qualcomm diagnostic protocol; it does not identify a particular radio.
- **MHI:** Modem Host Interface, a transport-family lead in this discovery code.
- **ETL / ETW / WPR:** saved Windows trace / Windows event tracing / trace recorder.
- **QPC:** QueryPerformanceCounter, the Windows host performance counter.
- **KCB:** registry key control block, whose lifecycle helps bind key identities.
- **RVA / vtable:** executable-relative address / C++ virtual-method table.

Hosted CI on the earlier `01d2c51` revision predates this work. See
[PR #3](https://github.com/Protonmatter/wifi-hardware-time/pull/3) for publication
and checks tied to each pushed revision. Software tests do not substitute for a
firmware event or calibrated timing result.
