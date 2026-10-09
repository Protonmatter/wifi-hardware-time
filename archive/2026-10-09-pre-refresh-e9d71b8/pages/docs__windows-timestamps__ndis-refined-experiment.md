# Refined NDIS experiment and capability qualification

> **Archive — not current operating instructions.** Historical documentation at [e9d71b843651](https://github.com/Protonmatter/wifi-hardware-time/commit/e9d71b84365122ff2640e240b20fc1dbb834388a). Relative links are rebased for reading. [Exact original bytes](../originals/docs__windows-timestamps__ndis-refined-experiment.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

Does a more carefully bounded trace identify the failing timestamp path? The refined run matched interface snapshots and validated trace health around three failed public queries. Its events remain associated by timing and adapter relationships rather than unique request identity, so the original rejection source and hardware timing capability remain unqualified.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** Vendor/private transport research continues alongside documented Windows APIs. No new hardware-to-QPC result is established by file inspection. See [current findings](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/knowledge/current-findings.md).
<!-- /historical-context -->

NDIS is the Windows network-driver framework; an OID identifies a driver query. ETW is Windows event tracing. QPC is the Windows host counter; a cross timestamp pairs hardware and host observations. Topology means the adapter and filter relationships. See the [glossary](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/glossary.md).

## Contents

- [What was implemented and run](#what-was-implemented-and-run)
- [Live results](#live-results)
- [Why complete request binding remains false](#why-complete-request-binding-remains-false)
- [Requested capability acceptance](#requested-capability-acceptance)
- [Build, run and analyze](#build-run-and-analyze)
- [Validation scope](#validation-scope)

Date: 2026-10-03 America/New_York. Starting research revision:
`dd4a92a7988ab848f4672fdb045e71c099ccf809`. This implements the same-run topology,
individual-query and trace-health refinement of the [first live capture](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/windows-timestamps/ndis-status-capture-2026-10-03.md).

## What was implemented and run

- SDK-native single-operation probes for supported capabilities, active
  configuration and a direct hardware cross timestamp. Each process resolves the
  selected interface, assigns a unique activity, captures PID/TID and native QPC
  bounds, and retains values only on public API success.
- Two ETW marker events around each call, outside the API's QPC bracket. Native
  metadata and Get-WinEvent named payloads must agree one-to-one by provider
  sequence, event ID/version, PID/TID and activity before payloads are joined.
- Raw interface and interface-stack snapshots before and after acquisition.
  The full graph is retained; unresolved unrelated vertices are inventoried.
  Missing target ancestors, identity/state changes, graph changes or cycles reject.
- Final controller query/stop statistics, finalized ETL header, full offline
  processing/close results, size limit and provider-count parity checks.
- Strict offline classifications that do not infer the original failure source,
  complete request lifecycle, uninterrupted topology continuity or clock accuracy.

One run completed after a User Account Control (UAC) prompt granted administrator privileges. Local directory:
`artifacts/NdisStatusV2-791fd1e90c60`. ETL SHA-256:
`aed4293eda8c8e850b4f5b45d8848f3233ac0897ba93346baa489333d968e0eb`.
It contains private interface identities and stays outside Git.

The exact selected Qualcomm adapter remained Up with driver 1.0.4374.1300 and
the pinned SYS hash. The experiment sent three documented public queries,
with no private IOCTL, firmware command, packet transmission, adapter/profile
configuration, register access, or system-clock change.

## Live results

| Operation | API duration in this run | Public result | Matching raw status records | Classification |
|---|---:|---|---|---|
| Supported timestamp capabilities | 100.7 us | 23 | Two 10111 records: `0xc0010017` | Temporal stack candidate |
| Active timestamp configuration | 84.9 us | 23 | Two 10111 records: `0xc0010017` | Temporal stack candidate |
| Direct hardware cross timestamp | 347.0 us | 23; values null | Two 10111 records: `0xc0010017` | Temporal stack candidate |

A **temporal stack candidate** matches the query’s time window, OID and adapter relationships, but lacks a unique request identity.

These durations are individual API-call measurements, not distributions,
firmware sampling times, calibrated latency bounds or clock accuracy.

Both snapshots contained 65 interface rows and 44 edges. Their complete rows and
edges matched; five unresolved vertices were outside the target ancestor graph.
The two matching filter identities were three and four hops above the selected
adapter in both snapshots. Matching before-and-after snapshots cannot exclude temporary changes between
them. The table APIs also do not capture the whole graph at one instant.

The trace contained 147 native records: 139 NDIS, six application markers and two
other metadata records. The two readers agreed on all 145 selected-provider records.
Thirty-one event-10016 records were explicitly excluded from the supported decoder
contract, retained in the exclusion inventory, and were outside all query brackets.
All six application markers matched their process/thread/activity and enclosed the
corresponding API call. No unsupported event fell inside a query bracket.

Controller QUERY and STOP both returned 0 with EventsLost, LogBuffersLost and
RealTimeBuffersLost all zero. STOP reported seven buffers written. The finalized
ETL header also reported seven buffers, zero event/buffer loss, positive StartTime
and EndTime, 64-bit pointers and QPC frequency 10,000,000 Hz. ProcessTrace and
CloseTrace returned 0. The file was 57,344 bytes, below the 8 MiB cap. The exact
session was not found by the post-stop query; that result was not access denied.

## Why complete request binding remains false

The matched kernel events carry **interface-scoped activities**. Each ActivityID
equals its payload IfGuid; the two filter GUIDs recur across all three queries.
They do not equal the probe's unique activity. No related activity was exposed.

Static analysis confirms this is intentional argument flow into EtwWriteTransfer,
not merely failed marker propagation. See [rejection-origin analysis](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/windows-timestamps/ndis-rejection-origin-analysis.md).
The correlator has a regression that prevents an interface activity from being
promoted to request binding even if a supplied query uses that same GUID.

The exact public NdisFOidRequestComplete path also shows that 10111 reports a
status already supplied to completion processing. Location `0x10001` is a fixed
writer marker, not the originating layer. The timestamp handlers' inspected
missing-cache/disabled branches return NOT_SUPPORTED, not this INVALID_OID.
Consequently the first rejecting component and actual dispatch branch remain
unestablished. Repeating these same event fields cannot supply a missing request
pointer, clone relationship or first status-producing branch.

## Requested capability acceptance

| Capability | Implemented/validated here | Remaining prerequisite |
|---|---|---|
| Per-API observation | One operation per process, exact host bracket, unique user activity and marker validation | Kernel identity propagation is separate |
| Application-to-kernel identity | Same-run target stack and temporal/OID association | Request/clone identifiers and complete request lifecycle; current 10111 activities are not request IDs |
| Original rejection layer | Completion status propagation and timestamp handler distinctions | Actual dispatch and first error-producing return/completion for that request |
| Hardware-to-QPC cross timestamp | Standard probe implemented and directly executed | Successful tuple; this build returned 23 with null values |
| Raw absolute FTM export | Prior exact-build producer/export audit retained | Qualified private or public raw response route plus widths, units, validity, exchange identity and clock domain |
| Arbitrary packet timestamps | Kept separate from FTM and cross-clock queries | Working packet timestamp delivery, packet/retry identity and physical reference point |
| Simultaneous TSF/SoC sampling | Explicitly not inferred from host request bounds | Producer-side latch semantics or independently bounded sampling skew |
| Calibrated accuracy / sub-ms synchronization | Qualification gates remain closed | Controlled second node and independent characterized reference; user reconfirmed neither is available |

This diagnostic result does not qualify a clock provider for use. An error-free test suite
does not replace any missing physical observation. FTM averages/deltas and raw
variance still cannot supply the missing clock phase or uncertainty.

## Build, run and analyze

Required: Windows ARM64, installed MSVC/Windows SDK, Python 3.11+, exact approved
adapter/driver, and administrator approval for the temporary trace. Build and
offline analysis do not require elevation. No new dependency is installed.

```powershell
powershell.exe -NoProfile -File research/windows_timestamps/Build-NdisExperiment.ps1 -Architecture arm64
$adapter = Get-NetAdapter -Name 'Wi-Fi'
$build = (Resolve-Path artifacts/ndis-experiment-arm64).Path
$manifestHash = (Get-FileHash (Join-Path $build 'manifest.json')).Hash
# Run the following in an elevated PowerShell, using a NEW output directory:
powershell.exe -NoProfile -File research/windows_timestamps/Capture-NdisTimestampStatusV2.ps1 -InterfaceIndex $adapter.ifIndex -ExpectedInterfaceGuid $adapter.InterfaceGuid -BuildDirectory $build -ExpectedManifestSha256 $manifestHash -PythonPath (Get-Command python.exe).Source -OutputDirectory artifacts/NdisStatusV2-<unique-id>
python research/windows_timestamps/analyze_ndis_run.py artifacts/NdisStatusV2-<unique-id> --output artifacts/NdisStatusV2-<unique-id>/analysis.json
```

The build manifest binds current source and executable hashes; keep all capture
helpers unchanged while acquisition runs. The run records source hashes and
the installed NDIS hash. Hashes provide provenance, not artifact authentication.
Native output is lossless numeric JSON/JSONL. Named payloads preserve original
field names. The exact-build RequestType-as-OID interpretation is separately gated.

Every launched child has a timeout and finite termination wait. Exact adapter
checks occur outside the live trace; the in-trace snapshot child is bounded.
Cleanup is attempted after uncertain startup. Failed native stop triggers a
bounded exact-session logman recovery attempt and retains failure qualification.
If externally interrupted, stop only the SessionName saved in session.json.

Capture exit 0 means acquisition/cleanup completed, not qualification. Exit 1
means failure. Analysis exit 0 includes inconclusive/temporal candidates; rejected
evidence exits 1, argument errors 2. Output creation is exclusive. Do not publish
the raw output, interface tables, identities, compiler paths or ETL.

## Validation scope

ARM64 and x64 native builds passed `/W4 /WX /O2 /Brepro`; ARM64 build also passed
under Windows PowerShell 5.1. Both executables' help paths were exercised without
acquisition. Synthetic tests cover malformed fields, duplicate JSON, excessive
nesting, nonfinite values, native-width overflow, marker loss, topology changes,
unresolved target paths, conflicting events, trace loss and interface activities.
The final local research suite passed 97 tests with the owned driver fixture.
PowerShell parser, child timeout and health-gate checks passed. Independent review
findings were fixed with regression coverage before final validation.

Hosted CI builds the x64 helpers and executes offline checks only; it does not run
elevated tracing or hardware experiments. Hosted results are reported separately
on the existing PR. No adapter or clock state needs rollback after a successful
capture beyond the already completed trace cleanup.
