# The missing hardware event connection

The application can retain and validate owned bytes, and a live driver control has returned a fixed test pattern. We still need a demonstrated operation that copies a real timing event before its source storage is released. The current installed Qualcomm route is no-go until supported/vendor/instrumented producer access is demonstrated. QMSL 6.1.365.1 now supplies completed static callback evidence, but no attributable live timing endpoint or bounded lifecycle.

**Current decision, 2026-10-06:** read the
[complete-event gate evaluation and reopening criteria](hardware-route-decision-2026-10-06.md).
The [current QMSL installation and trace](../adapters/qmsl-runtime-365.md) supersede
the runtime-absence snapshot below. Its selected worker/listener path is already
traced; it is not pending work. The 2026-10-05 file-only report is retained as
historical evidence. Linux is a conditional alternate, not an adopted route.
The later [WPP installation assessment](wpp-external-2311-file-assessment.md)
adds trace-configuration leads without establishing original timing-event
emission or changing that decision; no supplied tool or trigger was executed.

## Contents

- [What the new check establishes](#what-the-new-check-establishes)
- [Why RawService does not close the connection](#why-rawservice-does-not-close-the-connection)
- [The concrete integration handoff](#the-concrete-integration-handoff)
- [Accepting the first hardware record](#accepting-the-first-hardware-record)
- [Reproduction and limits](#reproduction-and-limits)
- [Glossary](#glossary)

## What the new check establishes

This **2026-10-05 file-only refresh** inspected installed files without loading
vendor code or contacting a device. It is additional static evidence, not another
live QUTS discovery or TSF campaign. Its missing-runtime conclusion applies to
that search date only, before the later QMSL/QSPR installation.

| Inspected input | SHA-256 | Result |
|---|---|---|
| `QC.CTE.WLANTestSuite.dll` | `33a982738130e42164ae9481e5cad9c0d4a316e48779a5c7d3c534718345c19f` | Matches the previously inspected assembly 2.0.79.1, whose metadata references QMSL FastConnect 6.1.360.1 |
| `QUTSService.exe` | `30dc1fac9c9fb7a5672fb665daf33f72c8bc3456fa545bd169c7ae77eb4863b6` | Matches the inspected server file; file identity does not attest a running process |
| `RawService.thrift` | `a58ade682b65577fccb89cbea753edc1212f9061ab29db560fda1f8d15d481ec` | Binary request/response interface over an existing protocol handle |
| `ClientCallback.thrift` | `5f1475d58ba1f2272e356a05c9200b9a75670be4bb838fb59bdf32e2043266f5` | Asynchronous response notification carries protocol and transaction handles, without payload bytes |

The filename search completed with exit code 0 and empty error output for all
five selected roots: the two Qualcomm Program Files directories, `C:/Qualcomm`,
and the Qualcomm `QIK` and `SoftwareCenter` directories under ProgramData.
It listed **2,170 files** in total. No filename matched `QMSL` or
`QTMDotNetKernel`. The installed WLAN assembly and cached WLAN subsystem packages
were present.

This search did not inspect unexpanded archive contents, follow linked directory
trees or scan the whole computer. A renamed or embedded implementation could be
outside its coverage. The result narrows the available local inputs; it does not
prove that a compatible runtime does not exist elsewhere.

The matching assembly makes the earlier
[inherited RTT method inspection](../adapters/qualcomm-software-center-timing-leads.md#what-the-timing-methods-expose)
reusable. Those wrappers still need their QMSL implementation to establish the
transport, device selection, returned lengths and field meaning. Builder values
`358` and `20043` are not newly qualified firmware commands or IOCTLs.

## Why RawService does not close the connection

The installed interface declaration supports the following narrow conclusions:

| Interface element | Declared behavior | What remains unproven |
|---|---|---|
| `initializeService`, `initializeServiceQmi`, `initializeServiceWithOptions` | Every variant requires a `protocolHandle`; QMI adds a service ID | An attributable protocol for this FastConnect adapter and the effects of opening it |
| `sendRequest` | Takes protocol-formatted bytes and a timeout; returns binary data, with an empty result on error | A safe timing operation, original event preservation and firmware completion meaning |
| `sendRequestAsync` | Returns a service transaction ID used for later response retrieval | Association with a firmware request, packet or exchange |
| `getResponseAsync`, `getAllResponsesAsync` | Retrieve responses for that transaction; retrieved responses are cleared in QUTS according to the comments | Server publication consistency, complete-event boundaries, loss and cancellation behavior |
| `isAsyncResponseFinished` | Reports whether further responses are expected for the transaction | A firmware drain or hardware sampling fence |
| `onAsyncResponse` in `ClientCallback.thrift` | Notification includes protocol handle and transaction ID | Event bytes or a hardware sampling timestamp in that notification |

There is no unsolicited-record queue getter declared in this **RawService**
interface. QUTS's separate diagnostic queue methods remain useful candidates;
this finding does not assert their absence from QUTS as a whole. Connection
options also include QDSS/ADPL configuration, whose presence does not establish
a Wi-Fi event source or make initialization passive.

The [earlier live discovery](quts-enumeration-2026-10-04.md) and
[attributed discovery-query trace](../adapters/quts-live-gate-and-commonio.md)
still bound what we know about this adapter's QUTS connection. No RawService
method was called in this refresh. Inspecting its declaration does not qualify
the corresponding server implementation or establish a new endpoint.

## The concrete integration handoff

The [source-validity follow-up](../tsf/hif-receive-buffer-producer.md#pool-construction-and-descriptor-admission)
now connects pool construction and HIF binding and traces nonfatal MDL-allocation
branches. The selected WMI copy boundary is before `0x168d7c`, ahead of header
removal and normalization. These refine requirements 1 and 2 below; they do not
install a producer adapter or qualify live memory access.

The first useful deliverable is **one diagnostic record retaining the complete
original event at a declared capture boundary**. Its timing semantics may remain
explicitly unknown initially. A hardware clock provider needs further evidence.

```text
Timing producer in the exact driver / firmware
    |
    | Valid source spans, successful synchronization, callback still owns access
    v
Complete event copied into independently owned storage
    |
    | Entire copy published, exact lengths and loss/continuity status retained
    v
Demonstrated response interface returns owned application bytes
    |
    | Validate operation, provenance, structure and source identity
    v
Diagnostic record retained by the application
    |
    ? Clock meaning, firmware association and fresh hardware/QPC sampling
    v
Possible future clock input
```

**Legend:** the arrows describe the required flow, not a completed live pipeline.
The question mark is an additional qualification gate. Copying a wrapper that
contains pointers does not retain the objects to which those pointers refer.

Any candidate integration package or instrumented build must answer these items:

1. **Compatibility and entry route.** Identify the actual adapter, driver and
   firmware builds, interface, operation framing, access requirements and state
   effects. Our inspected driver is `qcwlanhmt8380.sys`, INF/package version
   `1.0.4374.1300`, SHA-256
   `ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`.
   A different build requires a new trace. A QMSL package must satisfy the actual
   assembly dependencies and host architecture; version matching alone does not
   establish a supported transport to this laptop's adapter.
2. **Producer and capture boundary.** For the TSF route, identify the original
   `0x5005` event before reduction at `0x216b00`. The
   [HIF copy points A/B](../tsf/hif-receive-buffer-producer.md) are alternative
   earlier locations, with stricter buffer/coherency requirements. State whether
   the export preserves the WMI event or the enclosing HTC message; retain the
   original header and applicable trailer for that declared boundary. Do not
   describe padded/normalized bytes as the original firmware extent.
3. **Lifetime and publication.** Establish valid spans, capacity, received length
   and any fragment assembly before copying. Finish the payload and metadata
   before publication. Producer-buffer reuse must not change application bytes.
   Specify cancellation, disconnect, teardown and output-too-small behavior.
4. **Identity and loss.** Retain event/source identifiers, exact returned length,
   validity, known loss and continuity information. Label unknown firmware loss,
   request identity, clock domain and hardware epoch as unknown. An application
   ticket or service transaction ID is insufficient evidence of firmware identity.
5. **Host timing observations.** Describe precisely where each QPC read occurs.
   Callback-entry or copy-completion readings measure host handling. They do not
   establish when firmware sampled the counter.

A supported complete-event interface could satisfy this without full driver
source. If no such interface is available, an instrumented producer path is
needed. A companion driver or a user-mode DLL alone cannot provide access to the
private receive callback. The
[existing eight-byte control](device-service-positive-control.md) remains evidence
for its own return path, without changing the data it produces.

The [driver integration contract](driver-event-return-integration.md) defines
the required copy, request ownership and teardown behavior in more detail.
The nested IHV query/control avenue remains deferred at the user's request.

## Accepting the first hardware record

Before a live attempt, review the full selected operation and its state effects.
Prefer a single existing event through a qualified retrieval operation. A path
requiring logging changes, test mode or a new firmware request needs its own
reviewed experiment. This handoff does not release the private campaign quarantine.

- **Attribute it:** bind the actual device, running driver provenance, producer
  and declared event boundary to the returned bytes.
- **Retain it:** keep original bytes, declared and actual lengths, source metadata
  and retrieval status. A complete byte copy is useful even before timestamp
  fields are fully decoded; no clock admission follows from that alone.
- **Prove ownership:** exercise producer-buffer reuse and inspect the publication
  mechanism. Test pressure, cancellation and teardown separately with bounded
  cases. One successful retrieval cannot establish all of them.
- **Reject ambiguity:** wrong producer/build, partial or overwritten records,
  unexplained loss, stale continuity and ambiguous association must prevent use
  as a clock sample. Preserve rejected evidence for diagnosis.
- **Keep clocks separate:** qualify field meanings and a fresh hardware-to-QPC
  relationship independently. Accuracy still needs an independent reference.

The [source-operation record](source-operation-record.md) currently accepts
fixtures and saved replay. A future live adapter needs a reviewed live provenance
contract and consumer support; it must not label hardware data as a fixture to
bypass that boundary.

## Reproduction and limits

The existing file-inspection command produced three private receipts:
`artifacts/complete-event-refresh-20261005/{thrift,wlan-assembly,quts-server}/receipt.json`.
`filename-search.json` records the filename-search roots, counts, candidates,
exit codes and error-file locations. Vendor files and their contents remain
outside public Git.

Example: run from the repository root, using a new output directory whose parent
already exists. This reads files as data and needs no elevation.

```powershell
pwsh -NoProfile -File research/adapters/Invoke-QualcommStaticInspection.ps1 `
  -Operation Files -InputPath 'C:/Program Files/Qualcomm/QUTS/Thrift' `
  -OutputDirectory './artifacts/my-thrift-refresh' -Apply
```

The [inspection runbook](../adapters/static-inspection-runbook.md) defines bounds,
parameters, exit codes, unchanged repeats and private-output cleanup. No vendor
methods, private IOCTLs, firmware commands, logging changes, resets or system-clock
changes were executed here. This refresh supplies no new live ownership,
sampling, accuracy or hosted-CI qualification.

## Glossary

- **Producer:** the code that creates or receives the event before another layer
  reduces, copies or releases it.
- **Owned bytes:** storage whose validity no longer depends on the original
  receive buffer or callback lifetime.
- **IDL / Thrift:** an interface declaration and the RPC format/tooling used here.
  The declaration describes calls; it does not prove implementation behavior.
- **Protocol handle:** a service-side reference to a discovered communication
  protocol. It is not a hardware counter or firmware event identifier.
- **QPC:** Windows's performance-counter timebase. A host reading needs a proven
  sampling relationship before it can be paired with a radio counter.
