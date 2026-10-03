# NDIS rejection-origin analysis

Which component first rejected the timestamp queries? Static analysis shows that the recorded event repeats a supplied completion status; its location marker does not name the rejecting layer. Missing timestamp-cache branches return a different status, narrowing the possibilities without identifying the live branch or proving absent hardware support.

NDIS is the Windows network-driver framework; an OID identifies a driver query. A completion reports a finished request and can forward another component’s error. An RVA locates code within the exact binary. See the [glossary](../glossary.md).

## Contents

- [Result and limit](#result-and-limit)
- [Provenance and scope](#provenance-and-scope)
- [Public completion argument to event payload](#public-completion-argument-to-event-payload)
- [Timestamp-specific NDIS handlers](#timestamp-specific-ndis-handlers)
- [Other INVALID_OID references do not prove its origin here](#other-invalid_oid-references-do-not-prove-its-origin-here)
- [What still requires runtime evidence](#what-still-requires-runtime-evidence)
- [Capability and accuracy implications](#capability-and-accuracy-implications)
- [Validation and remaining limits](#validation-and-remaining-limits)

Date: 2026-10-03. This is an exact-build, read-only static follow-up to the
[live status capture](ndis-status-capture-2026-10-03.md) and
[interface/producer investigation](ndis-status-observation-path.md).

## Result and limit

**Event 10111 reports a status already present in the completion context; it does
not establish where INVALID_OID originated.** The inspected flow can carry a
status supplied through a filter completion API, and forwards that status to an
overlying filter completion callback after logging it. Location `0x10001` is a
constant inserted by the event writer, not an encoded rejecting-layer identity.

A useful discriminator was found: the specific NDIS timestamp capability and
current-configuration cache handler returns **`0xc00000bb` / NOT_SUPPORTED**
when its cached information is missing. It does **not** return the captured
`0xc0010017` / INVALID_OID from those branches. The cross-timestamp precheck uses
the same NOT_SUPPORTED result for absent or disabled prerequisites.

Therefore the observed INVALID_OID cannot be explained simply as the direct
output of these missing-cache branches. This does not prove the miniport generated
it: dispatch eligibility, another NDIS path, cached earlier errors, filter
processing, or a lower driver's result remain possible. No runtime branch or
kernel object was observed in this static pass.

## Provenance and scope

- Installed ARM64 `ndis.sys`, version `10.0.26100.8521`, SHA-256
  `d90b185d403966577fe5f8bed708a4b09c8da68730690e89f9ad41304792f64a`.
- PE image base `0x140000000`; all addresses below are **RVAs**, independent of
  the actual loaded base. Public exports were resolved from the on-disk export
  directory, not guessed from function names.
- Microsoft `dumpbin` version `14.44.35228.0` was used on bounded address ranges.
  PE table/literal references were located in memory with existing Python tools;
  no binary, bulk disassembly, or proprietary source was copied into the repo.
- The previous event metadata and SDK definitions were reused. No symbols were
  downloaded, debugger attached, runtime kernel memory read, or system/process
  state modified. No additional hardware query or trace was issued.

Private structure names are not assigned merely from their offsets. The tables
below use terms such as completion context and cached pointer as descriptions of
observed data flow. Public NDIS_OID_REQUEST semantics are grounded in exported
API arguments and Microsoft's definition.

## Public completion argument to event payload

Microsoft defines `NdisFOidRequestComplete(FilterHandle, OidRequest, Status)` as
the filter's completion of a previously pending request. The second argument is
an NDIS_OID_REQUEST pointer and the third is its completion status. That status
can reflect work performed by lower drivers; completing a request is not itself
proof of originating its failure.
[Filter completion API](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ndis/nf-ndis-ndisfoidrequestcomplete).

The exact binary has the following connected paths:

| RVA | Observed operation | Implication |
|---|---|---|
| `0x64740` | Public `NdisFOidRequestComplete` export | Known argument contract gives request-pointer type and incoming status |
| `0x64768..0x64770`, `0x647d0` | Saves second argument as request; stores third-argument status at request offset `0x50` on this branch | Status comes from completion caller, not event formatting |
| `0x647dc..0x647f8` | Supplies worker address `0x638e0` and filter context to an indirect scheduling/helper call | Static path to the filter completion worker; actual scheduling branch is not observed live |
| `0x638f8..0x63910` | Worker takes its current request, reads status at request `+0x50`, and constructs a stack context with request at `+0x20` and status at `+0x28` | Tracks both values into the common completion context |
| `0x63950..0x63954` | Calls common routine `0x64250` with that context | Connects worker to the event producer |
| `0x6427c`, `0x6428c`, `0x642e0..0x642f0` | Reads request, examines a request-associated object and selects a filter object on its type-5 branch | Event interface can be a filter interface, consistent with the raw interface-table result |
| `0x644b0..0x644d8` | Reads filter identity fields, OID from request `+0x20`, status from context `+0x28`; supplies event descriptor `0xe3130` to writer `0x4cf10` | Exact source of the 10111 fields on this producer path |
| `0x644dc..0x644f0`, `0x63720..0x637a4` | Passes filter context, request pointer and same status onward to completion processing; dispatches an indirect completion target or the known NdisFOidRequestComplete target | A logged filter completion can propagate rather than originate the error |

The event descriptor at `0xe3130` is 10111/version 0. The writer at `0x4cf10`
places the OID argument in the fourth 4-byte payload slot, the status in the fifth
slot, and constant `0x10001` in the sixth slot. This explains why the field named
`RequestType` contained `0x00a00001` and `0x00a00002` in the saved trace.

This strengthens the earlier interpretation: the public request-pointer origin
and data flow identify `DATA.Oid` at offset `0x20`, rather than the public
RequestType enum at offset 4. Preserve the original schema name in raw records
and annotate its interpretation by binary/provider version.
[NDIS_OID_REQUEST definition](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/oidrequest/ns-oidrequest-ndis_oid_request).

**Location meaning is limited to this emission site.** Its constant is not
calculated from the OID, status, adapter, lower driver, or branch that created the
failure. It identifies the writer's fixed marker in this inspected code. It cannot
be decoded as “NDIS rejected,” “filter rejected,” or “miniport rejected.”

The miniport completion export `NdisMOidRequestComplete` at `0x64b50` likewise
accepts a caller-supplied third-argument status and routes completion through
several branches. Its documented contract allows driver-determined error status.
The static presence of this entry point does not prove that the recorded request
reached or returned from it.
[Miniport completion API](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ndis/nf-ndis-ndismoidrequestcomplete).

### Refined capture: ActivityID is explicitly interface-scoped

The later local capture `artifacts/NdisStatusV2-791fd1e90c60` contains six
timestamp-related event 10111 records: two for each of capability, active
configuration, and cross timestamp. Reading its saved `named-events.json`
confirmed that all six EventHeader ActivityIDs equal their payload `IfGuid`,
with only two distinct identities reused across the three operations. No raw
GUID is published here.

Targeted static inspection explains this identity directly:

| RVA | Argument/data flow |
|---|---|
| `0x644b4` and `0x644bc` | The producer puts the same filter-interface GUID pointer into `x3` for the payload and `x2` for the activity argument |
| `0x4cf3c` | The event writer adds the incoming `x3` GUID as a 16-byte payload descriptor |
| `0x4cf7c` | Calls common helper `0x62a8`, retaining the incoming activity pointer in `x2` |
| `0x62c0..0x62d8` | Rearranges payload/count arguments, explicitly sets `x3=0`, preserves `x2`, and tail-calls imported `EtwWriteTransfer` through IAT RVA `0xff940` |

The kernel API's third argument is ActivityId and fourth is RelatedActivityId.
Consequently, this event producer explicitly supplies the interface GUID as its
ActivityId and NULL as RelatedActivityId. It does not inherit the query process's
generated activity GUID on this path.
[EtwWriteTransfer contract](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-etwwritetransfer).

This confirms an **interface-scoped activity**, not a per-request token. Matching
the kernel activity to IfGuid is useful for understanding the producer, but adds
no independent application-to-kernel request identity. Repetition of this activity
across different OIDs is expected. The query's own marker activity can establish
its marker bracket without establishing activity propagation into NDIS.

The offline analyzer must not promote `event.activity_id == event.IfGuid` into
complete request binding. Preserve a separate classification for matching OID,
QPC bracket and same-run topology, and retain incomplete request identity until
an independent request/clone or explicitly propagated activity relationship is
observed. No new query or trace was performed for this confirmation.

## Timestamp-specific NDIS handlers

The on-disk dispatch records directly bind these OIDs to handlers:

| Dispatch record RVA | OID | Handler RVA |
|---|---|---|
| `0xe1de8` | `0x00a00001` capability | `0xb0e50` |
| `0xe1e00` | `0x00a00002` current configuration | `0xb0e50` |
| `0xe1e18` | `0x00a00003` cross timestamp | `0xaee50` |

Handler `0xb0e50` checks request type and output-buffer capacity, then selects
cached pointer `+0x1680` for capability or `+0x1688` for current configuration from
its adapter-associated object. Those member names are inferred from the explicit
OID comparison and returned data, not recovered private type information.

| Branch | Exact observed result |
|---|---|
| Request type is not the query form, `0xb0ec0..0xb0ed0` | Writes `0xc00000bb` |
| Supplied buffer is shorter than `0x36`, `0xb0edc..0xb0ef4` | Writes required length and `0xc0010014` |
| Capability cached pointer absent, `0xb0f14..0xb0f3c` | Writes `0xc00000bb` and reports handled |
| Current-configuration cached pointer absent, `0xb0f74..0xb0f9c` | Writes `0xc00000bb` and reports handled |
| Valid cached pointer, `0xb0fb4..0xb1004` | Copies bounded cached data, sets written length and success |

The local constant at `0xb1028` is `0xc00000bb`, not INVALID_OID. This distinction
matters: lack of cached advertisement is a plausible capability issue, but the
specific missing-cache branches inspected here do not generate the observed
status. Whether those handlers were selected during capture remains unknown.

Cross handler `0xaee50` checks query type and at least a `0x20`-byte NDIS output
buffer. It then requires both cached capability/configuration pointers and the
current configuration's cross-timestamp flag at offset `0x10`. The relevant
checks are `0xaef10..0xaefb8`; failed prerequisites write `0xc00000bb`. On the
eligible path at `0xaefe0..0xaeff0`, it leaves the request for further processing;
this precheck does not synthesize a hardware timestamp.

This agrees with Microsoft's distinction between NDIS-maintained capability state
and the miniport's actual cross-timestamp service. A miniport with current cross
support enabled must service the cross-timestamp OID; disabled support may return
NOT_SUPPORTED. No such active state or successful service has been demonstrated
on this adapter by the existing failed queries.
[Cross-timestamp requirements](https://learn.microsoft.com/en-us/windows-hardware/drivers/network/oid-timestamp-get-crosstimestamp).

## Other INVALID_OID references do not prove its origin here

The inspected executable sections contain literal references to INVALID_OID in
several other routines. The routines around `0x48490` and `0x52230` compare cached
per-OID status values against INVALID_OID/NOT_SUPPORTED and can copy an existing
status into a completion context. Comparison with a status constant is not proof
that the routine generated it.

A separate routine at `0xaf020` directly supplies INVALID_OID for an inappropriate
request type, but its dispatch entry identifies OID `0x0001020d`, not either
timestamp capability OID. It is not evidence that this branch handled the saved
requests. The literal scan is a navigation aid, not an exhaustive proof of all
possible arithmetic, indirect, cached or lower-driver sources of that value.

## What still requires runtime evidence

The exact rejecting layer cannot be recovered from the existing 10111
records. They lack the request pointer, clone/original relationship, lower-module
call target, synchronous return value, and the first write of the failing status.
Static code shows available paths but not which request object traversed them.

To qualify the origin, a future dedicated diagnostic method would need to observe:

1. A specific public call and its OID request object, including clones or
   substitutions when crossing filters; snapshot interface/filter topology in the
   same acquisition epoch.
2. NDIS dispatch eligibility and the selected handler/lower callback for that
   request, distinguishing NDIS-handled completion from forwarding.
3. Every relevant synchronous return or pending completion status, locating the
   earliest INVALID_OID value rather than its propagation at an upper boundary.
4. The final user-mode translation for that same request, with trace-loss and
   lifetime checks.

The common routine contains additional diagnostic writer calls carrying request
and status arguments, but this pass did not qualify their provider, decode
metadata, enablement conditions, or complete coverage. They are not an executable
collection recipe. Request-pointer-bearing event 10101 would help where emitted,
but its absence in the existing capture cannot be repaired by guessing a pointer
from event 10111's fourth field. A debugger or independently qualified tracing
method is needed for the remaining dynamic attribution; none was used here.

## Capability and accuracy implications

- **Hardware/QPC cross timestamp:** the required software path includes accepted
  capability/current state and a working miniport cross service. The discovered
  precheck supplies no bypass and no timestamp. It does not justify a private
  request or a configuration change.
- **Software packet timestamps:** these use QPC and do not require NIC-clock/QPC
  conversion, but still require a supported and enabled miniport/system timestamp
  path plus socket configuration. Host application QPC samples remain a different
  event reference point. The current failed capability queries do not establish
  working software packet timestamp delivery.
- **General packet timestamps:** the documented Winsock facility is for UDP; RX
  ancillary data and TX timestamp IDs require their own delivery, loss and
  reference-point qualification. Nothing here establishes arbitrary TCP, raw
  802.11 frame or per-retry timestamp delivery.
  [Winsock timestamping](https://learn.microsoft.com/en-us/windows/win32/winsock/winsock-timestamping).
- **Raw FTM and accuracy:** this pass did not inspect or qualify new FTM sample
  access. An OID rejection explanation cannot recover per-exchange samples or
  demonstrate ranging/clock accuracy. A successful observation path would still
  need independently established event semantics and reference uncertainty.

## Validation and remaining limits

Verified exact file hash, architecture, public export RVAs, relevant dispatch
records, bounded producer/completion/capability-handler disassembly, and primary
Microsoft API contracts. No code was changed and no live test was performed.
The static coverage ends at alternative request dispatch/callback paths and
runtime cached state; exact originating rejection layer and complete request
identity remain unqualified. No physical hardware-absence or accuracy claim is
made. Only this authored report was added; no commit or push was performed.
