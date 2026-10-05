# Qualcomm private outputs: statistics, test data and interface information

The inspected Qualcomm return paths carry radio statistics, fixed test bytes or interface information. A real allocated-buffer response path exists, but no complete hardware timestamp producer has been connected to it. A new caller inventory makes the remaining search reproducible without treating a successful return mechanism as a working clock source.

**2026-10-05 follow-up:** the [live device-service positive control](../evidence/device-service-positive-control.md)
returned the fixed eight-byte test payload through the installed driver. It also
classifies all 70 identified direct completion calls: 59 null-payload calls and
11 possible-payload calls. Timing-event delivery remains unqualified.

<!-- current-context:2026-10-04 -->
**Current context (2026-10-04):** Later archive and installed-file inspection located QUTS client-owned byte returns and corrected vendor package/version assumptions; exact adapter-to-producer association remains open. See [current findings](../knowledge/current-findings.md).
<!-- /current-context -->

## Contents

- [Scope and terms](#scope-and-terms)
- [Receive-statistics getter](#receive-statistics-getter)
- [Device-service test getter](#device-service-test-getter)
- [Backward trace from the return helpers](#backward-trace-from-the-return-helpers)
- [IHV binary request bridge](#ihv-binary-request-bridge)
- [Reproduce the offline evidence](#reproduce-the-offline-evidence)
- [Decision and remaining work](#decision-and-remaining-work)

## Scope and terms

- **Build:** Qualcomm FastConnect 7800 ARM64 driver `1.0.4374.1300`.
- **SHA-256:** `ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`.
- **Static inspection:** read the driver as a file; do not execute its functions.
- **RVA:** relative virtual address, an offset within the driver image. These
  offsets identify evidence for this build, not callable public interfaces.
- **Getter:** a command intended to return information. Its name does not prove
  that it avoids internal changes, requests or waits.
- **Payload:** the data carried inside a response envelope.
- **RX:** receive. **MCS:** modulation and coding selection. **GI:** guard interval
  between symbols. **NSS:** number of spatial streams. **RSSI:** signal strength.
- See the [glossary](../glossary.md) for clock and acquisition terminology.

The findings below cover selected handlers and their immediate return paths.
They do not establish the absence of another export elsewhere in the driver.

## Receive-statistics getter

The named-command record at RVA `0x33e038` identifies `get_rx_stats`, selector
250. The getter dispatcher at `0x124440` reaches formatter `0x127e88` through
the call at `0x124908`.

| Stage | What the inspected code does | Consequence |
|---|---|---|
| Output check | Requires the extended output layout marker `0xaa` and at least `0x100` bytes in its declared text capacity | The legacy fixed output layout is not sufficient for this handler |
| Refresh | Calls helper `0x308f0` with mask `0x7f` before formatting | This is not simply a copy of a passive timestamp record |
| Radio fields | Reads context fields and formats bandwidth, MCS, GI, modulation, NSS and two RSSI values; the rate slot is literal `NA` | The inspected format contains radio statistics, not a raw clock value or packet identity |
| Text return | Appends text through `0x124110`; a conditional second-context path can append another result | Returned text has no established packet/exchange or epoch attribution |
| Final helper | Calls `0x308f0` again with mask zero and the low byte of a request argument | Request arguments can select additional helper behavior; this route is not added to the live allowlist |

The refresh helper has concrete state effects:

- Writes selection flags at context offset `+0x9a60` and copies cached signal
  fields into its statistics area.
- Checks host-derived cache-age values before selected refresh operations.
- Can reset an event, call statistics-request helper `0x30220`, and wait through
  `KeWaitForSingleObject` when that helper reports a pending operation.
- Can call another helper at `0x303f8`. A nonzero argument also reaches an
  additional indirect callback. Those downstream operations are not qualified
  here for live invocation.

These facts establish that calling the getter can do more than read existing
bytes. They do not establish every firmware side effect, a live latency bound,
or that every invocation refreshes its values. Internal host cache times are not
hardware sampling timestamps and are not exported by the inspected format.

## Device-service test getter

The handler at RVA `0x12a2a0` labels its opcode-1 path as a test-pipeline GET.
Its payload construction is explicit:

1. Load eight fixed bytes from literal storage at `0x12a4b0`. The bytes are the
   integers 1 through 8 in order.
2. Pass the eight-byte payload to the response serializer at `0x1618c0`.
3. Pass the serialized result to common completion helper `0x13a890`.
4. Free the serializer's temporary output after that helper returns.

The inspected common helper checks caller output capacity and copies a successful
nonempty payload after a 16-byte response header. It then follows framework
completion or context-cleanup branches. This identifies a return mechanism in
the binary; it does not prove that an application can successfully invoke it on
the current adapter.

There is no hardware-counter or FTM-buffer read in the direct GET payload
construction. Even if a future transport test returned these bytes successfully,
that would establish delivery of test data, not a hardware clock source.

## Backward trace from the return helpers

An **IOCTL** is an application-to-driver control request. Finding a driver
function that completes a response does not establish which external request can
reach it, what access it requires or whether its payload is a timestamp.

The follow-up inventories aligned direct branches in executable sections:

- **70 direct-call candidates** target common completion helper `0x13a890`.
- **Four direct-call candidates** target serializer `0x1618c0`.
- These counts are not counts of usable application APIs. The scanner covers
  immediate branches only; embedded data, indirect calls and runtime dispatch
  require separate review. The later [argument inventory](../evidence/device-service-positive-control.md#the-broader-completion-inventory)
  classifies these call sites; nested producers and indirect routes remain separate.

One of the four serializer callers, at `0x12ae5c`, receives dynamically allocated
data rather than the test payload. Following its producer identifies an interface
configuration service, with the diagnostic name `IfConfigServiceHandler`.

| Stage / RVA | Observed operation | Meaning for hardware-time research |
|---|---|---|
| Handler `0x12acf0` | Resolves the selected port, passes the service opcode and optional request data to `0x51960` | External service binding and live reachability remain unqualified |
| Dispatch `0x51960` | Opcode 1 calls `0x505b0`; opcode 2 calls `0x502c0`; opcode `0x8001` calls `0x50758`; other selectors return unsupported | These are nested service opcodes, not top-level IOCTL codes |
| Getter `0x505b0` | Builds a 24-byte output with interface/link address information on its populated-result path | Potential topology information; does not establish a timer ID or TSF mapping |
| Getter `0x502c0` | Builds a 100-byte output with association information and conditional per-link records | Interface state is not a timestamped receive-event record |
| Serializer at `0x12ae5c` | Serializes the returned data when the result descriptor marks a payload present | The descriptor's presence flag is not hardware-timestamp validity |
| Completion at `0x12ae78` | Passes serialized pointer, length and status to `0x13a890` | Concrete payload-to-completion connection, not a qualified hardware exporter |
| Cleanup `0x12ae7c..0x12ae94` | Frees the serialized buffer and, conditionally, the producer allocation after completion helper return | Preserves the distinction between temporary producer storage and the completion copy |

The internal producer descriptor uses a length at `+0`, pointer at `+8` and
payload-presence flag at `+0x10`. This is an inspected internal layout, **not**
a userspace structure or an instruction to dereference a kernel pointer.

The setter target has the diagnostic name `Port11DeviceServiceSetMloLinkActive`.
Its complete operational effects were not qualified. A shared serializer does
not make every opcode read-only, so this service is not added to the live allowlist.

This result supplies a useful return-path model: allocate a result, serialize it,
copy it through completion, then release the temporary allocations. It does not
connect the management RX header, TSF report or pre-aggregation FTM buffer to
that model. The interface getters' helper tree and all fields are not fully
decoded; no hidden-timestamp absence claim is made for every dependency.

The next candidates must be selected by tracing their **actual payload source**.
An input request ID, successful completion or a larger output buffer cannot
substitute for that producer connection. No new native probe is enabled by this
inventory; the top-level service binding, lengths, ownership and side effects
must first be established for the specific candidate.

## IHV binary request bridge

Another nonempty completion caller, `0x12e860`, belongs to the routine labelled
`WdiPropertyIhvRequestHdlr` at `0x12e4f0`. IHV means independent hardware vendor.
This is a broader binary request/response route than the interface-information
service above. It is a concrete transport lead, not a timestamp getter.

| Stage / RVA | Statically observed connection | Remaining qualification |
|---|---|---|
| `0x12e648..0x12e66c` | Pass the request payload to decoder `0x161e58` after accounting for outer header lengths | External request binding and full validation of caller-controlled lengths |
| `0x12e6b8..0x12e728` | Allocate a temporary buffer using adjusted output capacity, zero it, then copy decoded request bytes into it | Allocation/copy assumptions need separate review before any live probe |
| `0x12e734..0x12e750` | Pass the selected port, buffer, input/output lengths and result-count pointers to `MpNicSpecificExtension`, `0x11cde8` | Identify a concrete timestamp-producing operation within this dispatcher |
| `0x11cf10..0x11cfcc` | Decode either an extended 24-byte envelope or a shorter selector form | These inner selectors are not automatically top-level IOCTL codes |
| `0x11d090`, `0x11d144`, `0x11d1a0`, `0x11d1c4` | Reach alternative dispatch helpers, including query/set/method-shaped argument paths | Their operation trees and side effects are not fully classified here |
| `0x12e75c..0x12e7a0` | On successful nonempty output, describe the temporary buffer using the returned byte count and serialize through `0x1619b0` | No raw TSF, RX or FTM producer has been bound to this output |
| `0x12e84c..0x12e860` | Send serialized bytes/status through common completion `0x13a890` | Live application reachability, permissions and timing remain untested |

This path is synchronous in the inspected local control flow: dispatch returns,
then its output is serialized. That observation does not prove that a nested
operation avoids firmware waits, samples fresh hardware, or has safe cancellation.
The response transports whatever the selected producer returns; it cannot
reconstruct timing fields previously discarded by another path.

The callable target and request format for an application remain unqualified.
The bridge is therefore kept outside the live allowlist. The next investigation
should bind one specific read operation to a timing producer and verify its
buffer-length, ownership, state-change and error contracts end to end.

The [packet-log follow-up](../memory-ring/packetlog-return-path.md) now connects
one binary source to this bridge: a combined header/body copy through a resolved
operations table. It also identifies outer-selector precedence, position advance
before payload copy and a stop path that can free storage. No complete WMI event,
safe live snapshot or application invocation is established by that connection.

## Reproduce the offline evidence

Use the existing Python dependencies and a locally owned copy of this exact SYS
file. Normal read permission is sufficient; elevation is not required by the
inspector. It reads at most 16 MiB plus one rejection byte and never loads the
driver or opens a device handle.

```powershell
$env:WIFI_TIME_DRIVER_FIXTURE = 'C:\path\to\owned\qcwlanhmt8380.sys'
python research/adapters/inspect_private_exports.py `
  --driver $env:WIFI_TIME_DRIVER_FIXTURE `
  --output artifacts/private-export-static.json
python -m unittest discover -s tests -p test_private_export_routes.py -v
```

- `--driver`: existing exact-build driver file. Other hashes are rejected before
  route extraction.
- `--output`: new JSON receipt; an existing file is never overwritten. Choose a
  new filename for a repeat run.
- **Output:** fourteen selected range hashes, command identity, selected direct-call
  offsets, three imported helper names, the fixed-payload comparison and a
  bounded direct-branch inventory for the two return helpers.
- **Interpretation:** range hashes and instruction matches support repeatability.
  The behavioral conclusions above come from manual control/data-flow inspection;
  the tool is not a general disassembler or a proof of all reachable behavior.
- **Exit codes:** 0 means offline inspection completed; 1 means rejected input or
  file failure; 2 means invalid command-line usage. Zero is not live qualification.
- **Rollback:** no device/system state changes. The only persistent output is the
  requested local receipt.

For this investigation, fresh installed `dumpbin /disasm:nobytes` output matched
the saved exact-build disassembly in all eight selected ranges: 932 instruction
or literal lines. The locally retained range-validation and inspector receipts
have identical range hashes. Proprietary disassembly and the driver remain out
of Git; the reusable inspector emits neither their bytes nor the driver path.

The backward-trace follow-up adds four ranges and stores separate receipts under
ignored `artifacts/PrivateReturnFollowup/`. The original eight-range evidence is
retained. Regression tests cover the new producer/serializer/completion branches,
the exact-build caller counts and continued rejection of a hardware-export claim.
The later IHV follow-up adds two more ranges, with receipts under ignored
`artifacts/IhvReturnInvestigation/`; earlier receipts remain unchanged.

## Decision and remaining work

- Keep `get_rx_stats` outside the existing live command allowlist. Its output
  does not meet the timestamp need, and its refresh behavior needs separate
  qualification before any proposed use.
- Do not mistake the test-service serializer for an existing hardware exporter.
  A driver change that substitutes hardware records would need its own ownership,
  completion, concurrency and identity design.
- Continue searching only where a concrete producer-to-return path can be traced.
  The unresolved [normal RX boundary](qualcomm-rx-export-boundary.md) and
  [FTM ownership boundary](../ftm/ftm-buffer-ownership-and-identity.md) describe
  the records and lifetimes any candidate must preserve.
- The [complete-record gate](../evidence/raw-timestamp-export-gate.md) remains
  closed. No private command, trace, register access or hardware experiment was
  performed for this report. No downstream capability is promoted.
