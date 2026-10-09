# Observing timestamp OID status through existing NDIS events

> **Archive — not current operating instructions.** Historical documentation at [e9d71b843651](https://github.com/Protonmatter/wifi-hardware-time/commit/e9d71b84365122ff2640e240b20fc1dbb834388a). Relative links are rebased for reading. [Exact original bytes](../originals/docs__windows-timestamps__ndis-status-observation-path.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

Can existing Windows events reveal the status hidden by error 23? Metadata identified a candidate event, and a later capture found invalid-query status on interfaces above the selected adapter. The recorded events lack request pointers, so timing and interface relationships support association without proving the original rejecting component.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** Vendor/private transport research continues alongside documented Windows APIs. No new hardware-to-QPC result is established by file inspection. See [current findings](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/knowledge/current-findings.md).
<!-- /historical-context -->

NDIS is the Windows network-driver framework; an OID identifies a driver query. ETW is Windows event tracing, and ETL is its saved trace format. A miniport is the adapter-facing driver; filters sit above it. See the [glossary](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/glossary.md).

## Contents

- [New result](#new-result)
- [Subsequent live result and interface identity resolution](#subsequent-live-result-and-interface-identity-resolution)
- [Installed schema and exact correlation fields](#installed-schema-and-exact-correlation-fields)
- [Existing records and provider alternatives](#existing-records-and-provider-alternatives)
- [Why capability advertisement matters](#why-capability-advertisement-matters)
- [Original proposed bounded experiment](#original-proposed-bounded-experiment)
- [Reproduce this metadata-only investigation](#reproduce-this-metadata-only-investigation)

Initial metadata inspection: 2026-10-03, approximately 04:17 UTC. Research HEAD:
`dd4a92a7988ab848f4672fdb045e71c099ccf809`.

**Follow-up status:** a subsequently authorized live capture did run and recovered
four event 10111 records with raw status `0xc0010017`. Their interface identities
resolve to filter modules above the selected adapter in a post-capture stack
snapshot. See [the live acquisition receipt](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/windows-timestamps/ndis-status-capture-2026-10-03.md)
and the result subsection below. The earlier metadata-only phase and original
proposed experiment remain recorded separately; they are not claims that the
later capture never occurred.

## New result

The installed **Microsoft-Windows-NDIS event 10101, version 0** provides a
concrete debugger-free candidate for observing the status before Win32 error
translation. Its payload contains **the OID, raw status, interface identity, and
request pointer together**. Its message identifies completion by NDIS on behalf
of a miniport. This is particularly relevant to the timestamp capability and
current-configuration queries, which NDIS can answer from cached miniport
indications.

The initial pass established the event schema, not that the failing timestamp API path
emits this event. Both NDIS event-log channels were disabled, the queried channels
had no matching retained records, and three representative saved ETLs contained
no Microsoft-Windows-NDIS provider records. At that point no original status had
been recovered. The subsequent capture strengthens the invalid-OID explanation
in [the preceding investigation](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/windows-timestamps/windows-timestamp-path-followup.md), with the
attribution limits detailed below.

During the initial metadata-only pass, no trace was started, log channel enabled, hardware query issued, administrator
prompt opened, debugger attached, event log cleared, or system state changed.
Only this report was written.

## Subsequent live result and interface identity resolution

The parent investigation performed the authorized capture at approximately
04:26 UTC; the full acquisition and trace-health limitations are recorded in the
[separate receipt](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/windows-timestamps/ndis-status-capture-2026-10-03.md). The saved payload has four
10111/version-0 events: the fourth field, named `RequestType`, is `0x00a00001`
twice and then `0x00a00002` twice. All statuses are `0xc0010017`; all Location
values are 65537 (`0x10001`). No 10101 pointer-bearing event was recovered.

The initial Get-NetAdapter comparison rejected both event interface identities.
Read-only IP Helper follow-up resolved that mismatch:

| Check | Result |
|---|---|
| `GetIfTable2Ex(MibIfTableRaw=1)` / `GetIfStackTable` | Both return 0 |
| Saved target index and GUID | Exactly one raw-table match |
| Both event GUID/index/LUID tuples | Each matches exactly one raw-table interface |
| Both event interfaces | `FilterInterface=true`, `HardwareInterface=false` |
| Interface type / physical medium | 71 / 9 for both |
| Directed lower-layer path to saved target | Three hops and four hops |

The metadata fields refer to **filter-module interfaces**, not necessarily the
physical miniport's own interface GUID. GetIfTable2Ex includes filter interfaces
at either normal or raw level; raw level selects directly reported interface
state rather than state at the top of its filter stack. GetIfStackTable supplies
the immediate higher-to-lower relationships used in the directed path search.
[Raw interface enumeration](https://learn.microsoft.com/en-us/windows/win32/api/netioapi/nf-netioapi-getiftable2ex),
[interface-stack relationships](https://learn.microsoft.com/en-us/windows/win32/api/netioapi/nf-netioapi-getifstacktable).

The reproducible local reader and receipt are retained under ignored evidence:

- `artifacts/NdisStatus-59568b625be1/inspect_stack_local.py`
- `artifacts/NdisStatus-59568b625be1/topology-postcapture-local.json`

The reader checks the current 64-bit layout against the installed SDK declaration:
pointer size 8, WCHAR size 2, MIB_IF_ROW2 size 1352 and first table row offset 8;
MIB_IFSTACK_ROW size 8 and first stack row offset 4. Table counts are bounded,
returned memory is released with FreeMibTable in finally blocks, and the receipt
binds the saved session/event inputs and reader to SHA-256 digests. Only matching
interface/path metadata is persisted; stdout contains sanitized comparisons.
The receipt starts at `2026-10-03T04:34:27.908475Z` and has SHA-256
`bbff9d1a63ea2c518210a1b6a429ef3fd8a39f01cc7da47a31b56893f383ef64`.
The script and receipt contain or process private interface identities and must
remain local.

This is a **post-capture** topology receipt, not a same-epoch topology snapshot.
It establishes current stack membership and substantially supports the event
association; it cannot prove that topology was unchanged at the instant of the
capture. It also does not add a missing request pointer or originating process
identity to event 10111.

### Targeted producer inspection of the misleading field name

Bounded read-only inspection of the same hashed ARM64 ndis.sys found a 10111/v0
event descriptor at RVA `0xe3130`, referenced by the producer near
`0x644a8..0x644d8`. The producer loads the fourth payload argument from offset
`0x20` of its request object; the event writer at RVA `0x4cf10` emits this as a
4-byte field, emits the supplied status separately, and supplies constant
`0x10001` for Location. This matches the captured Location and the values in the
field named RequestType.

In the documented 64-bit NDIS_OID_REQUEST layout, RequestType is at offset 4 and
DATA.Oid is at offset `0x20`. Thus the inspected load is consistent with an OID,
not the request-type enum; the observed values also equal the two queried OIDs.
[NDIS_OID_REQUEST definition](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/oidrequest/ns-oidrequest-ndis_oid_request).
This interpretation is based on the exact producer load, public layout, and
observed values. Private object types were not independently recovered from PDBs,
and no kernel memory was inspected. Preserve the manifest field name in raw
records and treat its OID interpretation as build-specific; do not silently turn
it into a portable decoder contract.

The defensible conclusion is now **live NDIS invalid-OID diagnostics strongly
associated with the queried adapter stack and timestamp OIDs**, rather than
only a status-converter hypothesis. The original rejecting component, exact
request lifecycle, and hardware capability remain unproven. Filter completion
events may reflect an error propagated from lower layers; they do not prove that
the named filter itself created the error. This follow-up issued no new timestamp
or private hardware query and started no additional trace.

## Installed schema and exact correlation fields

Provider `Microsoft-Windows-NDIS`:
`{cdead503-17f5-4a3e-b7ae-df8cc2902eb9}`. Installed metadata exposes 166 event
definitions. Resource/message binary is the installed `ndis.sys`, version
`10.0.26100.8521`, SHA-256
`d90b185d403966577fe5f8bed708a4b09c8da68730690e89f9ad41304792f64a`.
OS build is `26200.9457`. These event details are local build observations;
re-enumerate metadata on another build.

Event 10101 has Diagnostic channel, Request task, level **5 / Verbose** and
keyword **Request = 0x1**, plus the channel keyword `0x4000000000000000`.
The numeric task is 1 and opcode is `win:Info` / 0 for both 10101 and 10102.
Its message describes an OID completed by NDIS for the miniport and includes
status and completion flag. Payload order:

| Field | Manifest input type | Meaning available from schema |
|---|---|---|
| `IfGuid` | `win:GUID` | Interface identity |
| `IfIndex` | `win:UInt32` | Interface index |
| `NetLuid` | `win:UInt64` | Interface LUID |
| `Request` | `win:Pointer` | Request-object pointer, not an application transaction ID |
| `CompleteRequest` | `win:Boolean` | Completion flag; preserve its value |
| `Status` | `win:HexInt32` | Raw 32-bit status field, before any consumer formatting |
| `Oid` | `win:UInt32` | OID value, displayed in hexadecimal |

SDK `10.0.26100.0/shared/ntddndis.h` independently defines the target OIDs:

| OID | Value | Existing public query |
|---|---|---|
| `OID_TIMESTAMP_CAPABILITY` | `0x00a00001` | `GetInterfaceSupportedTimestampCapabilities` |
| `OID_TIMESTAMP_CURRENT_CONFIG` | `0x00a00002` | `GetInterfaceActiveTimestampCapabilities` |
| `OID_TIMESTAMP_GET_CROSSTIMESTAMP` | `0x00a00003` | `CaptureInterfaceHardwareCrossTimestamp` |

The public-function/OID mapping was established in the preceding local DLL
inspection. No direct OID call is required for the proposed experiment.

Other installed event templates have useful but different evidence:

| Event/version | Fields beyond interface identity | Constraint |
|---|---|---|
| 10018/0, 10102/0 | `Request` pointer, `Status`, `Location` | Completion to filter/miniport; no OID in these payloads |
| 10111/0, 10112/0 | `RequestType` UInt32, `Status`, `Location` | Despite similar completion message wording, field four is **not** a request pointer |
| 10052/0 | `Oid`, `Status`, `Location` | PnP query error; no request pointer; keyword 0x2, level 3 |
| 10074/0 | `Error`, `Oid`, `Set` | Power-specific failure, not evidence of general timestamp OID completion |
| 10401/0 | `NetLuid` only | Timestamping change notification; no capability flags, status, or frequency |

Events 10018, 10102, 10111 and 10112 also use Request keyword 0x1 and level 5.
The installed manifest has only three payloads containing a field named `Oid`:
10052, 10074 and 10101. It does not expose an all-purpose request-start event
with an OID in this inspected set. Event 10402's capability fields concern power
management, not timestamp capabilities.

### Correlation rules

Decode by provider GUID, event ID **and version**, using named fields. Preserve
the 32-bit status as hexadecimal; do not substitute the Win32 error message.
Require the selected interface GUID/LUID and OID to match. Retain ETW timestamp,
process/thread metadata and ActivityID if present, but do not assume an ActivityID
exists or that a kernel completion runs in the originating application thread.

Event 10101 can identify a timestamp OID without relying on nearest timestamps.
Join an additional completion only on the same interface and `Request` pointer
within the same acquisition lifetime, with consistent ordering. Kernel pointers
can be reused; they are not durable IDs. A `RequestType` value from event 10111
or 10112 must never be used as the pointer join key. Multiple matching OIDs or
reused pointers in a window make attribution ambiguous unless the complete
request lifetime resolves them.

Use TDH or the manifest-named EventData fields rather than casting raw bytes to a
naturally aligned C structure. `win:Boolean` is a 4-byte ETW Boolean, while
`win:Pointer` follows the trace pointer width. These must not be confused with
the one-byte Windows BOOLEAN fields in the timestamp-capability API structure.

The existing native capability probe issues one supported and one active query,
so their different OIDs help distinguish them. An isolated invocation and tight
host-time window strengthen attribution, but do not prove that no concurrent
system client issued the same OID. Retain the `CompleteRequest` flag and all
matching records; do not assume every 10101 occurrence is a final completion.

## Existing records and provider alternatives

Read-only `wevtutil gl` shows both `Microsoft-Windows-NDIS/Diagnostic` (Analytic)
and `/Operational` disabled. Bounded queries for events 10052, 10101, 10102 and
10401 returned no matching retained events. This says nothing about events that
were never collected.

The following existing local ETLs were queried by provider name, with no matching
NDIS events:

- `artifacts/WifiTime-6ee1b42080dc/tsf.etl`
- `artifacts/reset/WifiReset-323c1fa40d1c/reset.etl`
- `artifacts/QualcommCampaign-ecfaed68f20e/idle-read-1/tsf.etl`

A separate first-ten-event read of the first file succeeded and showed ETW
header/WLAN provider IDs, confirming that the file reader worked. Other saved
ETLs were inventoried but not exhaustively decoded. No raw payload or endpoint
identifier was copied into this report.

`logman query providers` additionally exposes
`Microsoft-Windows-NetAdapterCim-Diag`, GUID
`{6cc2405d-817f-4886-886f-d5d1643210f0}`, with flags such as
`NDISWMI_TRACE_CALL`, `GENERAL`, and `HWINFO`. However, `Get-WinEvent -ListProvider`
does not expose a matching registered manifest. Its flag metadata alone does not
establish a raw OID completion schema or packet identity. It is a weaker candidate
than the concrete NDIS event above. No installed manifest-backed provider whose
name matches NetAdapter was returned by that inventory.

NDIS-PacketCapture is a separate provider; capturing packet bytes is not needed
to ask whether event 10101 reveals an OID status. It was not enabled.

## Why capability advertisement matters

Microsoft specifies that a participating miniport reports timestamp capabilities
through `NdisMIndicateStatusEx` with `NDIS_STATUS_TIMESTAMP_CAPABILITY`, normally
during `MiniportInitializeEx`. The payload includes `NDIS_TIMESTAMP_CAPABILITIES`.
This advertisement describes support, separately from enablement.
[Capability indication](https://learn.microsoft.com/en-us/windows-hardware/drivers/network/ndis-status-timestamp-capability).

The current-configuration indication follows capability advertisement; NDIS
rejects current configuration if capability indication has not occurred first.
Changes require updated indications. This identifies an additional failure
boundary: support may be absent from NDIS's accepted state even if firmware has
other private timing functionality.
[Current-configuration indication](https://learn.microsoft.com/en-us/windows-hardware/drivers/network/ndis-status-timestamp-current-config).

NDIS answers capability and current-configuration OIDs using those indications.
Therefore a missing explicit OID dispatch case in Qualcomm code is not decisive.
An event showing NDIS itself completing the OID would be more informative than
another search for the private driver's handler.
[Capability OID](https://learn.microsoft.com/en-us/windows-hardware/drivers/network/oid-timestamp-capability),
[current-configuration OID](https://learn.microsoft.com/en-us/windows-hardware/drivers/network/oid-timestamp-current-config).

The inspected event 10401 does not contain the advertisement payload. Neither its
presence nor absence would reveal the advertised flags or prove that an earlier
indication was accepted. This pass did not restart the adapter to replay
initialization, instrument `NdisMIndicateStatusEx`, or establish the Qualcomm
driver's actual advertisement behavior.

## Original proposed bounded experiment

This was the proposal from the metadata-only phase. A subsequently approved
variant was executed; see the live result above. The detailed health controls
below remain requirements for a refined capture and must not be assumed to have
all been implemented by the first harness.

Existing `logman`, `netsh`, and `wevtutil` executables are available. A separately
authorized, temporary ETW session can test the concrete event without installing
a debugger or permanently enabling event-log channels. Session creation may
require additional tracing privileges; stop on access denial rather than
automatically elevating. Microsoft documents provider/keyword/level filtering,
bounded buffers, maximum file size and QPC session clocks.
[Logman trace options](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/logman-create-trace).

Use a descriptive dedicated session name such as `WifiTime-NdisTimestampStatus`,
refuse to start if that name already exists, and use a new private output file under ignored artifacts,
only the NDIS provider, Request keyword `0x1`, Verbose level `5`, QPC clock, 64 KiB
buffers (2 minimum / 8 maximum), and a 16 MiB maximum **sequential** file. Do not
add the broad Diagnostic channel keyword or packet-capture provider. The proposed
start command, with an exclusively owned session/output name, is:

```powershell
logman create trace <unique-session> -p Microsoft-Windows-NDIS 0x1 5 `
  -o <new-private-output.etl> -f bin -max 16 -bs 64 -nb 2 8 -ct perf -ets
```

Before execution, put that command and the following steps under a bounded
controller with cleanup; the command alone is not a complete experiment:

1. Resolve the exact active interface identity and driver hash. Verify the native
   capability executable and use its explicitly selected interface index. Record
   QPC frequency, UTC and QPC bounds, process ID, and a fresh run identifier.
2. Start the uniquely owned ETW session. Issue no probe if session startup fails.
3. Run **one** existing `native_caps.exe <selected-index>` invocation, with a
   10-second child-process timeout. Capture its two public API results and QPC
   bounds. No private query, restart or configuration change is needed.
4. Stop only the session created by this run in `finally`, using
   `logman stop <unique-session> -ets`. Require the controller to cap the trace at
   30 seconds and verify the named session is gone. If cleanup fails, report its
   exact session name and explicit stop command; never stop unrelated sessions.
5. Decode offline and check ETL completeness/loss. Keep raw interface IDs and
   request pointers local. Extract versioned event 10101 records for the selected
   interface and OIDs 0x00a00001/2, preserving status and completion flag. Compare
   any exact-pointer completion records rather than choosing the closest event.

### Loss and completion evidence required

The controller should preserve final `EVENT_TRACE_PROPERTIES.EventsLost`,
`LogBuffersLost`, `RealTimeBuffersLost`, and `BuffersWritten` returned by
`ControlTrace` QUERY/STOP, along with the control-call results. EventsLost and
LogBuffersLost must be zero for a file-based result; RealTimeBuffersLost is a
separate delivery-loss counter relevant if real-time mode is used.
[Controller statistics](https://learn.microsoft.com/en-us/windows/win32/api/evntrace/ns-evntrace-event_trace_properties).

Offline, open the stopped ETL with `OpenTraceW` and retain
`EVENT_TRACE_LOGFILEW.LogfileHeader.EventsLost`, `.BuffersLost`, `.EndTime`,
`.ReservedFlags` (clock type), `.PerfFreq`, `.PointerSize`, and `.BuffersWritten`.
Require zero header loss counts, finalized EndTime, and the expected QPC clock
and positive frequency. Read to completion and require successful `ProcessTrace`
and `CloseTrace`. A maximum-size stop, truncated file, missing stop result, or
decoder failure is inconclusive even if a readable counter says zero.
[ETL header fields](https://learn.microsoft.com/en-us/windows/win32/api/evntrace/ns-evntrace-trace_logfile_header).

Do not use the outer `EVENT_TRACE_LOGFILEW.EventsLost` member: Microsoft marks it
unused. Raw QPC event times require `PROCESS_TRACE_MODE_RAW_TIMESTAMP`; otherwise
ProcessTrace normally converts them to system time.
[ETL consumption contract](https://learn.microsoft.com/en-us/windows/win32/api/evntrace/ns-evntrace-event_trace_logfilew).

On the inspected saved ETL, Get-WinEvent returned the trace-header event
(ID 0, version 2, provider `68fdd900-4a3e-11d1-84f4-0000f80464e3`) with
`Properties.Count = 0` and no named EventData payload. Therefore Get-WinEvent
alone did not expose its lost counts in this environment. The existing offline
`artifacts/decode_tsf_etl.exe` did expose header loss counts 0/0, QPC clock type 1,
frequency 10,000,000, and successful ProcessTrace/CloseTrace on that same saved
file. Its source `research/tsf/decode_tsf_etl.c:64` uses the correct LogfileHeader fields.
Reuse that header-check approach independently of the new NDIS event decoder;
its current WLAN event parser is not an NDIS decoder. No new trace was involved
in this check.

Zero loss does not prove provider emission or correct filtering. If there is no
matching event, state only that the configured collection did not expose it.

The first experiment tests capability/current-config status only. A later,
separately bounded direct cross query can target 0x00a00003 if this event path is
useful. Do not widen provider masks, enable channels, or cycle the adapter merely
because the first run produces no event.

Success is an unambiguous raw status for the requested OID, followed by a
consistent public return code. `0xc0010017` would support the legacy invalid-OID
translation hypothesis for that operation; it would not prove physical hardware
absence. A different raw status changes the diagnosis. No matching event means
this event path did not yield the necessary evidence in that run, not that the
OID was accepted, rejected by firmware, or unsupported. Trace loss or multiple
plausible matches make the result inconclusive.

## Reproduce this metadata-only investigation

These commands inspect metadata and existing records; they do not enable traces:

```powershell
$provider = Get-WinEvent -ListProvider Microsoft-Windows-NDIS
$provider.Events | Where-Object Id -in 10101,10102,10018,10111,10112,10401 |
    Select-Object Id, Version, Level, Task, Keywords, Template
netsh trace show provider name=Microsoft-Windows-NDIS
wevtutil gl Microsoft-Windows-NDIS/Diagnostic
wevtutil gl Microsoft-Windows-NDIS/Operational
logman query providers Microsoft-Windows-NetAdapterCim-Diag
```

`netsh trace show provider` is the documented metadata discovery route; its
`start` subcommand was not used.
[Netsh trace reference](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/netsh-trace).

Initial metadata-only validation: local schema/keyword inspection, SDK OID confirmation,
read-only log queries, three saved-ETL provider queries, one bounded ETL reader
sanity check, and official Microsoft documentation review. Not validated in that initial phase: event
emission for these API calls, tracing permission, raw status, loss handling in a
new session, and causal application-to-kernel request correlation. No runtime
code, dependencies, settings, binaries, commits or pushes were changed.
