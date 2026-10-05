# Current research findings

We can read diagnostic counters and trace real byte-return mechanisms. WLANLIB is attributable to FastConnect and reaches the existing QcomWifi private commands. An ART2 firmware-event producer now connects to a cached payload fetch, but discarded metadata, cache consumption and validity/concurrency gaps prevent timing qualification. QUTS framing and ownership are mapped separately; no new complete timing event or hardware-to-host relationship is established.

## Contents

- [Established findings](#established-findings)
- [What changed](#what-changed)
- [The remaining connection](#the-remaining-connection)
- [Qualification boundaries](#qualification-boundaries)
- [Continue or reproduce](#continue-or-reproduce)

## Established findings

Baseline snapshot: 2026-10-04, with an action-4 offline follow-up on 2026-10-05.
This page is the current interpretation; dated experiment reports preserve what
was observed in their original runs.

| Area | Established result | Practical use |
|---|---|---|
| Private TSF/SoC reports | Exact-build counter observations and action-dependent cache/refresh behavior | Diagnostic records and rejection fixtures |
| Action-4 submission | The inspected HTC queue can return success with accepted work still queued; optional barriers serve deletion queues | Reject request-return QPC as a sampling fence; preserve complete reports with the new diagnostic decoder |
| TSF event ingress | Logical payload length reaches decoder and callback; fixed-TLV padding retains the original header; exact one-slot cleanup is mapped | Prefer an owned header/payload copy before normalization; actual live wire length and export remain open |
| HTC transport and return candidates | Logical callback length can derive from an aggregate buffer length; WMI send completion releases outgoing data; separate control/history paths do not establish TSF response return | Preserve declared transport extent and accessible spans; strict offline envelope decoding rejects length/endpoint mismatches |
| HIF receive producer | Posted pooled metadata reset, CE saved-context return, cache-helper call and one-buffer completion queue connect to HTC | Two copy opportunities before header removal; live capacity, synchronization and application return remain unqualified |
| FTM ranging | Aggregate results and selected signed-difference processing | Ranging diagnostics; no four-time clock-offset input |
| Management RX | Candidate firmware fields, frame lifetime and selected metadata reduction | Identify where a complete-event copy would need to occur |
| Packet log | Located producer, reservation and return candidates; cursor can precede copy | Prevent unsafe ring polling from being promoted |
| MLO offset cache | Located locked writes and lifecycle-related state | Investigate radio-link relationships separately from QPC |
| Authored exporter | Owned synthetic management/MLO records with rejection and lifecycle tests | Substantive software qualification and an eventual integration boundary |
| Concurrent raw responses | Native user-mode broker owns complete bytes and handles read tickets, overflow, cancellation, timeout and close; a Python DLL consumer decodes synthetic replay | Tested application-side integration; kernel copy/return adapter and live source qualification remain open |
| QPST/QXDM | Connection interfaces, buffer-return contract and WLAN definition leads | Target the useful interfaces and avoid misleading timestamp accessors |
| Installed QUTS | Client deserialization allocates a byte array for diagnostic payloads | Real static ownership evidence for a possible application return path |
| Live QUTS enumeration | Two returned device locations match a processor and USB device, not the active PCI Wi-Fi adapter; no record acquired | Narrows the missing adapter-to-protocol connection; does not prove absent hardware support |
| Native QUTS discovery | Ghidra locates a network-device control-endpoint advertisement check; the active adapter lacks that advertisement and its USB fallback | Explains one omission path; target the actual vendor transport rather than force a protocol on an unrelated device |
| Live discovery-query attribution | 12 missing-value results on the active adapter key, with matching QUTS stacks and 20/20 control reads | Establishes the selected query's live execution and status; does not directly trace the following CPU branch |
| CommonIo transport | Shared interface with distinct implementations; selected Usb open resolves a discovered endpoint into `CreateFileW` | Attribute the actual endpoint and owning device; a DIAG/MHI label does not establish a Wi-Fi connection |
| Endpoint writer | `ScanDevices` constructs entry `+0x894` from discovery/validation data after the active-device gate | Connects the missing network advertisement to endpoint construction; does not create a FastConnect endpoint |
| Native receive ownership | A 128 KiB reusable read buffer feeds separate owned callback chunks of at most 16 KiB | Real copy/ownership implementation located; chunk boundaries are not complete-record boundaries |
| Receive cancellation | Located stop, cancel, close and worker-wait paths; selected wait uses an unlimited sentinel | Requires a separately qualified bounded shutdown contract before operational use |
| QUTS callback and framing | Static callback registration reaches a retained-buffer queue, partial-frame state, CRC checking and copied decoded payloads | Locate protocol rejection/loss rules and the remaining native-item-to-client association |
| FastConnect WLANLIB interface | Read-only device enumeration finds an enabled vendor interface; its GUID/reference match registration in the exact driver | An attributable private-interface lead, not yet a QUTS DIAG stream or timing export |
| WLANLIB dispatch/completion | Same selected WDF device as QcomWifi; Qmux notification completes with a one-byte state; iwpriv reaches the existing TSF table | Separate request completion from hardware sampling and meaningful output length |
| ART2 firmware-byte return | UTF producer feeds a length-plus-payload fetch, which consumes cached state; mismatch logging does not always reject publication | Concrete producer/return connection, with mode, identity, copy and timing-schema qualification still open |
| Live Npcap baseline | 589 Ethernet-format packets; only host timestamp types advertised; adapter remained Up on the exact driver | Useful traffic observation; paired kernel trace was not collected after a canceled administrator launch |
| Qualification audit | Exact driver catalog membership accepted; selected package signatures verified; 247 tests passed with zero skips | Closes the prior compiler/fixture gap; unsigned QUTS files and timing qualification remain separate |

## What changed

The [assumption ledger](assumptions-and-corrections.md) records the evidence and
scope behind each correction. The largest recent changes are:

- A [concurrent raw-event broker](../evidence/raw-event-response-broker.md) now
  implements the application-response lifecycle with internal locking and a
  pointer-free little-endian format. Real native threads and a Python DLL consumer
  test software ownership. This does not connect the internal Qualcomm callbacks
  to userspace or make application read tickets into firmware response tokens.
- The [HIF producer trace](../tsf/hif-receive-buffer-producer.md) connects active
  callback installation, pooled receive buffers, CE completion identity and the
  dispatcher call into HTC. It supports a narrower single-buffer candidate for
  this selected path, not a general contiguity assumption. The CE history retains
  a descriptor and buffer context without copying the WMI payload.
- The [upstream transport trace](../tsf/tsf-event-ingress-and-owned-copy.md#upstream-transport-length-and-contiguity)
  distinguishes HTC's advertised payload length from the aggregate length used
  to form the WMI handoff. The latter is not proof of contiguous source bytes or
  exact wire extent. The decoder now has a strict `htc-wire` diagnostic profile.
  [Return candidates](../tsf/tsf-event-ingress-and-owned-copy.md#existing-return-candidates)
  include send completion, three distinct histories and endpoint-zero control
  storage; none establishes a live complete TSF response to an application.
- The [TSF ingress trace](../tsf/tsf-event-ingress-and-owned-copy.md) connects event
  registration, original-length handoff, short-TLV padding and callback cleanup.
  A padded 48-byte input still declares its original 44-byte value length; it
  must not be treated as 60 firmware-supplied bytes. The diagnostic decoder now
  preserves a supplied WMI header and TLV together, but has no live acquisition
  backend or clock-admission qualification.
- The [action-4 completion trace](../tsf/action4-completion-and-report-contract.md)
  follows the sender into the HTC endpoint queue. Success does not require a
  firmware sampling completion. Its optional barrier routes peer/vdev deletion
  requests, so it is not an established shortcut to synchronous TSF sampling.
  New offline tools fingerprint that exact code and decode owned report bytes
  under explicit reference layouts. Live publication and clock admission remain
  unqualified; this follow-up has not rerun the private campaign.
- QUTS service/client files are now found locally. Earlier absence reports remain
  true only of their stated snapshots/searches.
- QPST's complete installer contains server 2.7.0.496; its separate merge module
  contains 2.7.0.495. A component listing did not describe the full package.
- QXDM's failed download was an incomplete inspection. Successful extraction
  later recovered 17 declared QIK containers and 557 file entries.
- Timestamp-named accessors may return host-assigned or interpolated values.
  Ownership, timestamp origin and timing accuracy need independent validation.
- The installed WLAN assembly is now 2.0.79.1, referencing QMSL FastConnect
  6.1.360.1. Preserve the earlier assembly/version pair as historical evidence.
- Live enumeration is now observed, but no returned protocol maps to the exact
  Wi-Fi adapter. Running-process executable-path checks were denied; the run
  therefore retains an explicit image-attestation limitation.
- Ghidra and the downloaded QUD discovery source identify the
  [network discovery gate](../adapters/quts-discovery-gate.md):
  `QCDeviceControlFile` or a specific Qualcomm composite-USB fallback. The current
  PCI adapter satisfies neither. The [qualified live follow-up](../adapters/quts-live-gate-and-commonio.md)
  now corroborates the failed query and exact callsite. It does not prove that
  other Wi-Fi diagnostic paths are absent or directly trace the following branch.
- Extended Ghidra analysis also locates a separate MHI DIAG branch that constructs
  a `Device::Protocol::Diag` object. The [follow-up](../adapters/quts-mhi-route-validation.md)
  resolves QCDM-description and `mhi.*?` parent predicates and the DIAG connection
  wrapper. FastConnect attribution and its Wi-Fi producer connection remain open.
- The discovery worker's 12,235 recognized instructions are now exported without
  truncation. Earlier passive traces failed coverage or were cancelled. Attempt 06
  uses 32 MiB collector buffers and retains every start/end control; zero loss
  counters alone were insufficient to qualify earlier attempts.
- The lower `CommonIo` trace distinguishes Usb, QmiIo, Ethernet and CommandIo.
  The inspected Usb open may configure communication state/timeouts, so a future
  passive-read claim must account for connection initialization too.
- The [endpoint and receive trace](../adapters/quts-endpoint-writer-and-receive.md)
  locates the endpoint writer and copied transport chunks. The later
  [callback/framing trace](../adapters/quts-callback-framing-and-wlanlib.md) closes
  registration through `receiveData`, the locked queue and frame decoding.
  Explicit pressure-drop paths make loss reporting a separate requirement.
- Fresh exact-device enumeration identifies WLANLIB, and the pinned Wi-Fi driver
  registers the matching GUID/reference string. Missing QUTS discovery metadata
  therefore does not mean there is no vendor interface. Its timing semantics and
  native-record-to-client association remain open.
- The [WLANLIB dispatch trace](../adapters/wlanlib-dispatch-and-completion.md)
  ties the interface to the existing QcomWifi device and private-command table.
  Its ART2 path carries test-event bytes, but drops the segment envelope and can
  publish length after logging mismatches. The fetch clears cache state and has
  no demonstrated reader/writer snapshot lock or timing-event identity contract.
- The Qmux “5G in use” follow-up traces a Wi-Fi channel flag, supporting **5 GHz
  Wi-Fi**, not a demonstrated cellular-state interpretation. Its input byte
  selects query or wait; it cannot select a new response schema.
- [Packet capture and elevation](../acquisition/packet-capture-and-elevation.md)
  now records a successful non-elevated Npcap run, a canceled normal administrator
  launch, and repeatable privilege/child-cleanup receipts. Nanosecond pcapng
  representation is not evidence of radio timestamp accuracy.
- The previously skipped native C and Windows BSS image tests passed after
  configuring the installed toolchain and exact fixtures. Published revision
  `1522bca` has successful PR and push hosted checks. Its local suite passed all
  262 tests with zero skips. The callback/framing, WLANLIB and packet-observer
  follow-ups require their containing revision's own hosted checks in
  [PR #3](https://github.com/Protonmatter/wifi-hardware-time/pull/3).

## The remaining connection

```text
Exact Wi-Fi firmware timing producer
             |
             ?  Adapter-to-diagnostic-protocol connection NOT established
             |
QUTS diagnostic record / QXDM item
             |
             +--> owned client bytes: static implementation located
             |
             ?  Radio clock, event identity, validity and epoch need qualification
             |
Application observation admitted for a specific capability
             |
             ?  Fresh hardware-to-QPC sampling is a separate requirement
             |
Clock conversion / synchronization / system discipline
```

`?` marks a missing evidence connection. Arrows below a question mark are not
claims that the full pipeline has run. Prefer bounded protocol enumeration and
one attributable existing record before any new firmware request or logging change.
QUTS documents that enumeration can return an empty list on failure. An empty
list alone cannot distinguish an absent protocol from a failed query. The
[first bounded live run](../evidence/quts-enumeration-2026-10-04.md) checked query
health separately and stopped on missing Wi-Fi attribution before record access.

## Qualification boundaries

- The private campaign remains quarantined. Service/client restarts do not prove
  that old firmware reports drained.
- Reset, suspend and roaming remain preparation only under the current authorization.
- No independent timing reference or second controlled node was reported available.
- NTP offset and a roughly estimated AP distance cannot establish calibrated
  hardware timestamp accuracy or demonstrate sub-millisecond synchronization.
- Preserve raw integer fields and clock-domain labels. Numeric resolution is
  not accuracy; a QDSS timestamp is not automatically a Wi-Fi TSF/PPDU timestamp.
- This research repository owns findings and experiments. `userspace-clock`
  owns maintained application providers and independent capability gates.

## Continue or reproduce

- [Archive and installed transport evidence](../adapters/qualcomm-archive-transport-findings.md).
- [Offline qualification and signatures](../evidence/qualification-audit-2026-10-04.md).
- [Live QUTS enumeration and its limits](../evidence/quts-enumeration-2026-10-04.md).
- [Ghidra trace of the native QUTS discovery gate](../adapters/quts-discovery-gate.md).
- [MHI route, full assembly and live-validation status](../adapters/quts-mhi-route-validation.md).
- [Repeatable static inspection runbook](../adapters/static-inspection-runbook.md).
- [Interface directory](interface-directory.md) and [searchable reference index](reference-index.md).
- [Packet-to-clock workflow](../clock-models/packet-to-clock-map.md).
- [Current qualification ledger](../overview/gap-closure-ledger.md).
- [Repository skill](../../skills/qualcomm-timing-research/SKILL.md).

Publication and hosted checks are recorded on the active research PR. A green
offline suite does not change any of the live qualification states above.
