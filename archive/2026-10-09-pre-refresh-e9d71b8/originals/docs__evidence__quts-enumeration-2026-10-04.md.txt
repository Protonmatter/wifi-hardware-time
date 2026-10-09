# Bounded live QUTS enumeration, 2026-10-04

One local QUTS session returned two devices, but neither could be attributed to
the active Qualcomm Wi-Fi adapter. No diagnostic record was read. This narrows
the missing transport connection without proving absent hardware support. Wi-Fi
remained Up on driver 1.0.4374.1300. Running-process image identity and all hardware
timing claims retain explicit limitations.

## Contents

- [What ran](#what-ran)
- [What the devices establish](#what-the-devices-establish)
- [Cleanup and identity limits](#cleanup-and-identity-limits)
- [Validation and reproducibility](#validation-and-reproducibility)
- [Next dependency](#next-dependency)

## What ran

The separate `quts-bounded-enumeration` task performed one session against the
already-running local service on 2026-10-04, approximately 16:50 America/New_York.
QUTS is Qualcomm's diagnostic transport service. RPC means a remote procedure
call; here all RPCs used the local loopback address, not a remote computer.

- The authored Python client used the standard library and a fixed five-method
  allowlist. It loaded no vendor DLL and launched no vendor executable.
- One registration allocated temporary host-side manager/callback transports.
  Three local TCP connections were opened and subsequently closed.
- Each call had a five-second absolute deadline, within a thirty-second total
  network budget. Reads did not extend that deadline. Responses were bounded
  to 1 MiB, 256 collection items and twelve nesting levels.
- The helper requested no logging-mask or device-mode change, firmware request,
  private TSF/FTM request, scan, restart, reset, suspend, roam or clock adjustment.
  Internal activity of the existing native service was not instrumented.

| Method | Count | Observed result |
|---|---:|---|
| `getQutsApplicationPort` | 1 | Port matched a pre-existing QUTS process listener |
| `registerSecureClient` | 1 | One manager/callback port pair allocated |
| `getDeviceList` | 1 | Two devices returned |
| `getProtocolList` | 2 | One protocol entry for each device |
| `getLastError` | 3 | `DEVICE_NO_ERROR (0)`, empty error strings |
| Diagnostic initialization, queue creation, or record retrieval | 0 | Stopped before access because Wi-Fi attribution was absent |

The helper reported 0.220 seconds including input hash checks. The longest RPC
bracket was registration at 90.5184 ms. These are single-run host delivery
measurements, not an estimate of timestamp precision or hardware performance.

## What the devices establish

PnP means Windows Plug and Play device identity. The worker compared the returned
physical locations with present PnP devices and the active adapter's location
paths. This is stronger evidence than matching the word "Qualcomm" in a name.

| Enumerated description | Independent location match | Active PCI Wi-Fi match |
|---|---|---|
| Snapdragon X 12-core X1E80100 CPU | One present `Processor` device | No |
| Qualcomm USB Type-C Device | One present `USBDevice` | No |

Both protocol entries reported `PROT_UNKNOWN (-1)`, `OPEN_NONE (0)` and no
services. Their `STATE_AVAILABLE (0)` value does not establish responsiveness:
the inspected local interface definition permits that value for unknown
protocols without validation. Both also reported `CONNECT_USB (0)`; this remains
service output, not independent proof that the processor's transport is USB.

No PCI Wi-Fi identity was returned. Error code zero supports successful query
operation in this session; it does not establish complete hardware discovery.
Neither the absence of a matching device nor an empty service list proves that
the Wi-Fi hardware cannot provide diagnostics through another configuration or
interface.

## Cleanup and identity limits

- All three socket objects closed without a reported close error.
- The allocated server listeners remained in the immediate snapshot, then were
  absent in a read-only observation approximately 31 seconds later. Remaining
  `TimeWait` entries are closed-connection bookkeeping. This supports transport
  reclamation; internal server-object destruction was not observed.
- The final check found the same Up Wi-Fi interface, PnP identity and driver
  version, and the original running QUTS service process. No configuration
  rollback was required.
- Preflight hashed installed files and associated listeners with existing PIDs
  (process identifiers). It did not establish each process's executable path.
  A post-run limited-information process query returned Windows error 5,
  Access denied. There was no elevation or second session.

The result is **successful enumeration with ambiguous running-image attestation**.
Attestation here means evidence tying the observed process to the inspected
executable file; it is distinct from publisher-signature verification. Even a
matching path and disk hash would not prove in-memory code identity. The separate
[signature audit](qualification-audit-2026-10-04.md#publisher-signature-verification)
also reports the inspected QUTS service/client files as unsigned under Authenticode.

The final helper was strengthened after the live run: it rejects missing or
mismatched application image paths/hashes before service contact and returns a
failure for socket-cleanup or final adapter/service identity errors. Those changes
were tested offline only. They do not retroactively qualify the earlier session.
The initially executed helper source was not snapshotted before those edits.
Retained RPC and state evidence documents the observed session, but the final
source is not an immutable reproduction of the code executed in that session.
Future acquisitions need a pre-run source snapshot and hash as well as input pins.

## Validation and reproducibility

Standalone authored deliverables remain in the separate task's `outputs/`:

- `Invoke-QutsBoundedEnumeration.ps1`: preview by default; explicit execution
  requires a new private evidence directory and an already-running service.
- `quts_bounded_enumeration.py`: bounded protocol client with no record-access,
  queue-creation or firmware-command implementation.
- `test_quts_bounded_enumeration.py`: 22 offline tests covering malformed inputs,
  deadlines, method/sequence identity, no retry, cleanup and process-image gates.
- `QUTS-BOUNDED-REPORT.md`: full local report and reproduction commands.

Python compilation, all 22 offline tests, PowerShell parsing and preview passed.
PSScriptAnalyzer was unavailable; Windows PowerShell 5.1 runtime compatibility was
not tested. The stronger helper was not live-rerun and is expected to block under
the present process-access limitation. Private RPC replies, identity comparisons
and cleanup receipts remain in that task's `work/live-enumeration-01/`; none are
included in this repository. No diagnostic payload was acquired.

The [separate offline audit](qualification-audit-2026-10-04.md) passed all 247
repository tests with zero skips and verified hosted CI for published revision
`5d6695c`. Those hosted runs do not cover this report or the standalone helpers.
No new commit, push or merge was made for this validation work.

## Next dependency

The subsequent [Ghidra investigation](../adapters/quts-discovery-gate.md) identifies
a concrete native network-device advertisement check absent on the current PCI
adapter. This explains a selected omission path without changing the original
session's acquisition or process-attestation limitations.

First identify a driver/firmware-to-QUTS bridge that reports the exact Wi-Fi
adapter and an attributable diagnostic protocol. Then establish that retrieving
an existing record does not enable device logging or change its mode. The local
service-initialization APIs can open DIAG/QMI connections, connection options can
enable QDSS configuration, and queue APIs describe registration for incoming data;
this run did not establish a passive existing-record contract for them.

A returned record would still need its firmware producer, schema, clock domain,
units, width, event identity, validity, loss and epoch semantics. QPC (Windows's
high-resolution host counter) only bracketed RPC delivery here. No firmware-event
association, server copy consistency, fresh hardware sampling, hardware-to-QPC
conversion, calibrated accuracy or sub-millisecond synchronization was validated.
No independent reference or second controlled node was available.
