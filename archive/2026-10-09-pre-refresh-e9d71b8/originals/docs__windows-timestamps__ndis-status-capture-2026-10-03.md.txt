# Bounded live NDIS status capture

What did the first live trace reveal about failed timestamp queries? Four diagnostic events reported invalid-query status during the two public calls, strengthening that explanation for error 23. Interface relationships were checked afterward, and trace-health records were incomplete, so exact request attribution and the original rejecting layer remain unresolved.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** Vendor/private transport research continues alongside documented Windows APIs. No new hardware-to-QPC result is established by file inspection. See [current findings](../knowledge/current-findings.md).
<!-- /historical-context -->

NDIS is the Windows network-driver framework; an OID identifies a driver query. ETW is Windows event tracing, and ETL is its saved trace format. QPC is the host counter used to time events. See the [glossary](../glossary.md).

## Contents

- [Acquisition](#acquisition)
- [Observed request-error records](#observed-request-error-records)
- [What changed in the diagnosis](#what-changed-in-the-diagnosis)
- [Harness validation and next refinement](#harness-validation-and-next-refinement)

Date: 2026-10-03 America/New_York. This experiment followed publication of research
commit `dd4a92a7988ab848f4672fdb045e71c099ccf809`. It adds live evidence to the
[metadata investigation](ndis-status-observation-path.md).

## Acquisition

User Account Control (UAC) elevation granted administrator privileges. `Capture-NdisTimestampStatus.ps1` created one unique
Microsoft-Windows-NDIS session with Request keyword `0x1`, verbose level 5 and
an 8 MiB binary file limit. It ran the existing pinned native capability executable
once, making exactly the supported-capability and active-capability public queries.
It then stopped its own session and processed the saved ETL offline.

The exact interface GUID/index, driver version and installed SYS hash were checked
before and after. The driver remained `1.0.4374.1300`, SHA-256
`ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`, and the adapter
remained Up. No private IOCTL, firmware command, adapter setting, channel setting,
profile, register or system clock was changed. The ETW session was temporary;
its contents are local diagnostic metadata, not packet capture.

Local evidence directory: `artifacts/NdisStatus-59568b625be1`. Raw identifiers and
request data remain ignored. ETL SHA-256:
`5906d3787a8a91311a94b14a6fc6f6910fba8821ce689e02dabbed932ddff67e`.
The launch receipt's script hash matched the script after execution. The pinned
native executable hashes are enforced by the script; they were existing builds,
not newly rebuilt binaries in this experiment.

| Check | Result |
|---|---|
| Interface index-to-LUID conversion | 0 |
| Supported timestamp capabilities | 23 |
| Active timestamp capabilities | 23 |
| Trace start / stop child exits | 0 / 0 |
| Offline ProcessTrace / CloseTrace | 0 / 0 |
| Header events lost / buffers lost | 0 / 0 |
| ETL size | 24,576 bytes, below 8 MiB cap |
| Header clock / frequency | QPC / 10,000,000 Hz |
| Exact-session post-stop query | Session not found; not an access-denied result |

The native decoder counted six total trace records. Get-WinEvent exposed five:
one header and four NDIS events. This pass did not independently reconcile the
extra metadata record. Final controller loss statistics and header EndTime were
not retained by this first harness. Therefore report the observed header/process
checks, not a stronger complete controller/consumer parity qualification.

## Observed request-error records

No 10101 or 10102 event was exposed. All four NDIS records were **10111/version 0**.
The native probe process was bracketed from `04:26:08.3197184Z` to
`04:26:08.3674212Z`. All four events occurred inside that UTC window, under kernel
System PID 4. They are not direct user-process-ID matches.

| Event order | Payload field named RequestType | Raw Status | Location |
|---|---|---|---|
| 1 | `0x00a00001` | `0xc0010017` | 65537 |
| 2 | `0x00a00001` | `0xc0010017` | 65537 |
| 3 | `0x00a00002` | `0xc0010017` | 65537 |
| 4 | `0x00a00002` | `0xc0010017` | 65537 |

Those RequestType values numerically equal the two queried timestamp OIDs in the
same order. Preserve the schema's actual field name: event 10111 has neither an
Oid field nor a request-pointer field. Do not cast RequestType as a pointer or
perform a 10101-style pointer join on it.

Subsequent exact-build producer inspection found that the fourth payload value
comes from offset `+0x20` of the request-like object, matching the installed SDK's
`NDIS_OID_REQUEST.DATA.Oid` offset rather than its RequestType member. The event
writer places it in the slot named RequestType and writes Location `0x10001`.
This supports the OID interpretation for this producer; it is not a portable
schema rename or a complete private-object type proof. See the updated
[producer analysis](ndis-status-observation-path.md).

The event interface identities initially failed a comparison with Get-NetAdapter.
Read-only follow-up through documented `GetIfTable2Ex(MibIfTableRaw)` found both
identities uniquely, with GUID, index and LUID agreeing. Both were filter interfaces,
not hardware interfaces. `GetIfStackTable` showed directed lower-layer paths of
three and four hops to the exact saved Qualcomm target. One was classified as a
QoS filter. Thus a physical-adapter-only inventory would wrongly discard relevant
stack events.

The topology—the relationships between adapter and filter interfaces—was observed after capture, not snapshotted in the acquisition epoch.
This supports attribution to the selected adapter stack but does not prove the
topology was identical at event time. Preserve that temporal limit alongside the
lack of user-PID and request-pointer association.
The local `inspect_stack_local.py` and `topology-postcapture-local.json` preserve
the SDK-checked table layouts, read-only API calls and graph comparison. Their raw
interface data remain in the ignored capture directory.

## What changed in the diagnosis

Legacy invalid-OID status is now **observed in live NDIS diagnostics**, not merely
reproduced in a status-conversion test. Its event values, timing and subsequently
resolved stack membership are consistent with the two timestamp API failures.
This substantially strengthens the invalid-OID explanation for Win32 error 23.

It does not prove that a physical CRC fault occurred, identify the original layer
that decided the request was invalid, prove absent hardware capability, or supply
a working hardware cross timestamp. The driver/stack can reject a software
exposure path even when underlying silicon has timing features. The direct
cross-timestamp operation was not part of this two-query capture.

## Harness validation and next refinement

Before elevation, PowerShell syntax validation and actual Windows PowerShell 5.1
child-helper tests covered zero/nonzero process exits and timeout termination.
Preflight review identified an unbounded post-kill wait; it was replaced with a
finite second wait and a regression that rejects parameterless WaitForExit calls.
The recorded timeout test returned within its bound. Cleanup is attempted even
after uncertain session startup; cleanup failures produce an explicit failure
receipt with the exact session recovery instruction.

To reproduce, resolve the exact target identity locally and supply a new output
directory. Requires elevation and the pinned local native builds:

```powershell
powershell.exe -NoProfile -File research/windows_timestamps/Capture-NdisTimestampStatus.ps1 -InterfaceIndex <index> -ExpectedInterfaceGuid <guid> -OutputDirectory artifacts/NdisStatus-<unique-id>
powershell.exe -NoProfile -File tests/Test-NdisCaptureHelpers.ps1
```

Do not publish the output directory. Exit 0 means acquisition and cleanup completed,
not conclusive request attribution. Exit 1 means failure; unsupported/missing
native builds fail before tracing. If interrupted externally, stop only the
SessionName recorded in that run's session.json.

The later [refined experiment](ndis-refined-experiment.md) addresses these
collection gaps. The first capture identified the following requirements:
record raw interface/stack topology before and after,
capture each public query's own bracket, and retain final controller/header health
metadata. Preserve the exact-build producer evidence for how 10111 populates the
field named RequestType and its Location code; it does not establish a portable
decoder contract. None of this requires treating FTM support as generic
packet timestamp support or changing adapter configuration.
