# Current research findings

> **Archive — not current operating instructions.** Historical documentation at [1fc9bed58df4](https://github.com/Protonmatter/wifi-hardware-time/commit/1fc9bed58df4abd6fc28ae883670d05adff47cd0). Relative links are rebased for reading. [Exact original bytes](../originals/docs__knowledge__current-findings.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

**Review update:** [Integrated PR reconciliation](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/overview/pr-reconciliation-2026-10-08.md) corrects acquisition failure paths, uncertainty expiry and settlement. Revised smoke tracking coverage is 92.862589%; original capture and analysis records remain preserved.

We can acquire diagnostic TSF observations through a persistent exact-build worker and calculate conditional TSF-to-QPC intervals from screened records. The first five-minute persistent idle smoke completed cleanly. Complete original-event export, physical capture timing, AP/UTC accuracy and multi-device synchronization remain separate unqualified capabilities.

**Current result, 2026-10-08:** the [persistent sampler smoke](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/acquisition/persistent-tsf-smoke-2026-10-08.md) completed 139 real pending-to-success requests, accepted 138 samples offline, and closed with no outstanding I/O or trace loss. Arrival-aware tracking was 92.884% over the declared 302.999-second interval. All 297 replayed event-grid points settled with median/max conditional rate-only half-widths of 280.429/614.883 us after a median 2.341-second wait. The exact retrospective covered-interval maximum was 648.30025 us. The [math reference](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/clock-models/tsf-mathematics.md) states the assumptions and the [phase 2 roadmap](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/overview/persistent-tsf-next-steps.md) separates research, implementation, testing and qualification gates. No online sample admission is implemented.

**Separate complete-event decision, 2026-10-06:** the installed Qualcomm original-event export route is
[no-go pending demonstrated supported/vendor/instrumented producer access](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/evidence/hardware-route-decision-2026-10-06.md).
The current QMSL callback trace is complete for its static scope; repeating it
does not supply an attributable endpoint or bounded vendor lifecycle. Retain
the nested IHV map as deferred exploratory research and the private campaign as
quarantined. Linux remains a conditional alternate requiring a physical target
and explicit selection. Independently, the coordinator reports S8's local host
profile passed and S9's local patch was preserved/verified without publication;
S3 now has a reviewed five-profile replay provider, CLI, immutable observations
and 15 passing focused tests. The downstream suite passed 64 tests after
acceptance-verifier corrections; unchanged original measurements still pass.
Four calls exceeded 1 ms, so the p99 result is not a worst-case latency bound.
These local results enable no radio clock capability and are not yet published.

The [PR #3 software review](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/overview/pr3-review-2026-10-06.md) subsequently
corrected four reproduced source defects and passed 344 configured repository
tests. Source review, saved-evidence reanalysis and offline subprocess/native
tests leave the hardware gates unchanged. Subsequent publication, fresh hosted
CI and merge state are tracked on [PR #3](https://github.com/Protonmatter/wifi-hardware-time/pull/3).

The installed [WPP External 2.3.1.1 assessment](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/evidence/wpp-external-2311-file-assessment.md)
adds concrete ETL collection/configuration leads. Its scripts can change logging
and restart the Wi-Fi device; their presence does not demonstrate a complete
original timing-event return. No vendor tool was executed and the no-go remains.

The [complete-event implementation plan](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/overview/complete-event-2026-10-05/engineering-plan.md)
records the completed route comparison and bounded receive-lifetime audit. The
[qualification ledger](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/overview/gap-closure-ledger.md) and
[component review map](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/overview/pr3-component-review-map-2026-10-06.md) now pin
current work and exact PR base/head. The remaining native implementation needs a supported or
instrumented producer integration; packet filters and existing trace names alone
do not supply it.

## Contents

- [Established findings](#established-findings)
- [What changed](#what-changed)
- [The remaining connection](#the-remaining-connection)
- [Qualification boundaries](#qualification-boundaries)
- [Continue or reproduce](#continue-or-reproduce)

## Established findings

**2026-10-08 persistent sampling:** normal live session reuse and clean shutdown are established for one 300-second idle run on the qualified build. Requested one-second slots produced actual 2.005-second median and 4.009-second maximum gaps with the report wait retained. Cancellation, timeout recovery, firmware drain, long-run/load qualification and independent accuracy were not tested by this smoke. [Results and input/source hashes](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/acquisition/persistent-tsf-smoke-2026-10-08.md).

**2026-10-08 settled timestamps:** with [two-phase timestamps](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/clock-models/settled-timestamps.md), all 7,195 events in the two counted runs (one per second) settled below 1 ms after a median wait of about 3 s: guarantee median about 310 to 325 us, worst 895 us idle and 786 us loaded; constant-rate best estimate median about 127 to 130 us. Assumptions and offline screening as below.

**2026-10-08 causal provider replay:** a [causal provider](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/clock-models/causal-provider-replay.md) replayed over both counted runs reproduces the review figures exactly. Using each sample only from its recorded arrival (median about 2 s after capture), it kept a conditional sub-millisecond interval for 78.7% of the idle hour and 72.4% of the loaded hour, flagging the rest as stale, with no inconsistent sample. Screening was offline.

**2026-10-08 TSF-to-host bound:** the [live bound campaign](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/acquisition/tsf-host-bound-results.md) passed every predeclared criterion. Over one hour idle and one hour under CPU and network load, the station TSF was bounded at any QPC instant to a conditional worst case of 352 us and 191 us respectively, with medians of about 135 to 140 us. The bound assumes causal capture inside each window and a constant rate within each 60-second span; with only a 200 ppm rate limit the retrospective bound is 895 us and 786 us, while a causal (live) bound reported by review reaches about 1.7 ms and 1.3 ms in the longest gaps, so a live provider must expire its sub-millisecond guarantee during long gaps. Attribution used the driver's command record, and freshness, trace completeness and a coarse beacon check were screened for every sample. The link from station TSF to access point TSF remains an assumption on this equipment, and no clock provider is enabled.

**2026-10-06 installation follow-up:** [QMSL 6.1.365.1 and QSPR 6.0 interfaces](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/adapters/qmsl-runtime-365.md) are now present. The relevant assemblies are weak-named, so their reference-version differences alone do not require binding redirects. The new native image independently reconnects callback registration, worker delivery, listener invocation and payload ownership transfer. Getter size limits and unbounded startup/stop waits remain. Live Wi-Fi attribution and complete timing-event return are still open.

Baseline snapshot: 2026-10-04, with an action-4 offline follow-up on 2026-10-05.
This page is the current interpretation; dated experiment reports preserve what
was observed in their original runs.

| Area | Established result | Practical use |
|---|---|---|
| Installed QMSL 6.1.365.1 | New exact-hash trace; original-byte callback and worker/listener path; weak-name binding evidence and authored x86 CLR smoke | Use current-build addresses and review actual endpoint/initialization/lifecycle before invocation; no live source enabled |
| Installed WPP External 2.3.1.1 | 88 files hashed; guide and selected Wi-Fi/diagnostic-bridge scripts inspected without execution; GUI resource version 1.0.0.0 | Collection tooling is present; exact provider payload, target predicates, dependencies, ownership and live cleanup remain unqualified |
| Supplied QMSL 6.1.48.1 runtime | Native log copy/pop and callback registration located; batch getter can change logging masks; managed wrapper has size/length limits and a lossy timestamp formatter | [Queue contract](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/adapters/qmsl-diagnostic-queue.md); pursue original-byte callbacks with explicit ownership, not batch polling or formatted timestamps; exact Wi-Fi producer remains unconnected |
| Private TSF/SoC reports | Exact-build counter observations and action-dependent cache/refresh behavior | Diagnostic records and rejection fixtures |
| Saved TSF trace bytes | Two historical captures contain 88 selected UserData payloads, all numeric text plus one NUL; no trailing bytes or extended-data items | No complete firmware event hidden after the parsed text in these selected payloads; no new acquisition or clock qualification |
| CAPTUREH and QDSS alternatives | Separate beamforming cache; QDSS firmware-trace-to-file paths, DMA mapping control and matching MAC/PHY configuration files located | Real byte-production/return leads; original TSF content, mapping producer, schema and live completeness remain unqualified |
| Firmware catalog and copied diagnostics | Data20.msc entry 25950 names TSF/QTIMER/TQM and vdev/MAC/TSF IDs; WMI diagnostic event `0x1d011` feeds a version-gated allocated-copy queue and formatter | Stronger timing-producer lead; no captured matching-version record or owned application binary return; distinct from QDSS |
| Action-4 submission | The inspected HTC queue can return success with accepted work still queued; optional barriers serve deletion queues | Reject request-return QPC as a sampling fence; preserve complete reports with the new diagnostic decoder |
| TSF event ingress | Logical payload length reaches decoder and callback; fixed-TLV padding retains the original header; exact one-slot cleanup is mapped | Prefer an owned header/payload copy before normalization; actual live wire length and export remain open |
| HTC transport and return candidates | Logical callback length can derive from an aggregate buffer length; WMI send completion releases outgoing data; separate control/history paths do not establish TSF response return | Preserve declared transport extent and accessible spans; strict offline envelope decoding rejects length/endpoint mismatches |
| HIF receive producer | Posted pooled metadata reset, CE saved-context return, cache-helper call and one-buffer completion queue connect to HTC | Two copy opportunities before header removal; live capacity, synchronization and application return remain unqualified |
| Source validity follow-up | Pool construction and HIF binding are traced; cached-MDL allocation failure continues the loop, and mapping can return zero after a temporary-MDL failure | Select the WMI boundary before `0x168d7c`; require actual span/coherency evidence rather than inferring it from pool membership or mapping success |
| DMA backing contract | Selector initializer/writer favor the framework-provided DMA adapter and `AllocateCommonBufferWithBounds`; the call requests cached memory and returns a device logical address separately from the CPU pointer | Named allocation/lifetime contract; common-buffer allocation alone does not qualify coherency, callback teardown or an application export |
| Receive shutdown | PCI disable target, ignored DPC-drain status, completion polling/timeout, conditional thread waits and later pool release are traced | A returned stop function or cleared software flag does not prove all relevant users have finished; live rundown and producer export remain open |
| FTM ranging | Aggregate results and selected signed-difference processing | Ranging diagnostics; no four-time clock-offset input |
| Management RX | Candidate firmware fields, frame lifetime and selected metadata reduction | Identify where a complete-event copy would need to occur |
| Packet log | Located producer, reservation and return candidates; cursor can precede copy | Prevent unsafe ring polling from being promoted |
| MLO offset cache | Located locked writes and lifecycle-related state | Investigate radio-link relationships separately from QPC |
| Authored exporter | Owned synthetic management/MLO records with rejection and lifecycle tests | Substantive software qualification and an eventual integration boundary |
| Concurrent raw responses | Native user-mode broker owns complete bytes and handles read tickets, overflow, cancellation, timeout and close; a Python DLL consumer decodes synthetic replay | Tested application-side integration; kernel copy/return adapter and live source qualification remain open |
| Source-operation records | Operation profile, original WMI/HTC bytes, provenance, software identities and unknown/loss fields survive native publication and decoding together | Diagnostic integration for fixtures/replay; no firmware identity, sampling or clock capability granted |
| Live device-service control | One elevated fixed-pattern GET returned exactly eight expected bytes through the installed driver; identity/state matched afterward | Live transport positive control; 166.5 microseconds is one API duration, not a hardware sampling bracket |
| Nested IHV queries — deferred | Selected query cases can reach scans, GPIO output, channel-control callbacks or host-state clearing; device-information read resolves to PCI configuration space | Retained for later exploration at the user's request; no active clock-path or live-operation promotion |
| Driver request lifecycle | Manual notification queue, forced completion and selected deinitialization/suspend callers traced; their WDF purge targets a different queue | Concrete request-ownership reference for the exporter; producer rundown and live connection still unqualified |
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

The [assumption ledger](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/knowledge/assumptions-and-corrections.md) records the evidence and
scope behind each correction. The largest recent changes are:

- The [firmware message catalog](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/tsf/firmware-trace-return-candidates.md#the-fuller-firmware-diagnostic-report) supplies a precise next target: message 25950 and the original diagnostic bytes before `0x1b1128` formats them. The copied kernel queue is located; the two saved WlanLogger traces contain no selected FWLOG/report/action text, despite positive host-report controls. No live record or clock capability was obtained.
- The [firmware trace candidates](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/tsf/firmware-trace-return-candidates.md) locate a QDSS save indication and binary file writers in the pinned driver, plus its installed configuration files. CAPTUREH is a separate event with a borrowed cache getter. Neither path is promoted to a complete TSF event return or a clock source.
- The [saved-trace byte audit](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/tsf/saved-trace-byte-audit.md) preserves complete selected ETW UserData and checks bytes the numeric parser could ignore. All 88 selected records in two saved captures contain only numeric text and a terminator. The original firmware-event copy and fresh-sampling requirements remain open.
- The [source-operation record](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/evidence/source-operation-record.md) now binds
  original bytes and interpretation metadata inside the existing broker payload.
  Native tests cover full HTC/WMI preservation, while replay of the saved live
  fixed-byte control preserves its distinct operation and receipt digest. Clock
  admission and quarantine release remain disabled; the IHV query avenue stays deferred.
- The [IHV query-producer map](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/adapters/ihv-query-producer-map.md) follows the
  remaining generic payload route into specific controls and data sources. In
  particular, selector `0xffb00004` constructs GPIO-output command `0x1e002`, and
  the device-information callback resolves to a parent-bus configuration read.
  This is static evidence only; none of these operations was executed.
- A [live device-service control](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/evidence/device-service-positive-control.md)
  now supplements software-only broker evidence. The first non-elevated query was
  denied and sent no service command; the separately elevated control returned
  the expected eight bytes. The expanded completion inventory narrows 70 direct
  calls to 11 possible payload sources, without establishing a timing producer.
- The [driver integration contract](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/evidence/driver-event-return-integration.md)
  now separates the event-data queue from waiting application requests. The exact
  driver drains Qmux notification requests with a supplied error status, but this
  does not establish producer shutdown or firmware drain. Live source metadata
  also needs a defined envelope beyond the broker's fixture/replay response.
- A [concurrent raw-event broker](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/evidence/raw-event-response-broker.md) now
  implements the application-response lifecycle with internal locking and a
  pointer-free little-endian format. Real native threads and a Python DLL consumer
  test software ownership. This does not connect the internal Qualcomm callbacks
  to userspace or make application read tickets into firmware response tokens.
- The [HIF producer trace](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/tsf/hif-receive-buffer-producer.md) connects active
  callback installation, pooled receive buffers, CE completion identity and the
  dispatcher call into HTC. It supports a narrower single-buffer candidate for
  this selected path, not a general contiguity assumption. The CE history retains
  a descriptor and buffer context without copying the WMI payload.
- The [upstream transport trace](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/tsf/tsf-event-ingress-and-owned-copy.md#upstream-transport-length-and-contiguity)
  distinguishes HTC's advertised payload length from the aggregate length used
  to form the WMI handoff. The latter is not proof of contiguous source bytes or
  exact wire extent. The decoder now has a strict `htc-wire` diagnostic profile.
  [Return candidates](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/tsf/tsf-event-ingress-and-owned-copy.md#existing-return-candidates)
  include send completion, three distinct histories and endpoint-zero control
  storage; none establishes a live complete TSF response to an application.
- The [TSF ingress trace](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/tsf/tsf-event-ingress-and-owned-copy.md) connects event
  registration, original-length handoff, short-TLV padding and callback cleanup.
  A padded 48-byte input still declares its original 44-byte value length; it
  must not be treated as 60 firmware-supplied bytes. The diagnostic decoder now
  preserves a supplied WMI header and TLV together, but has no live acquisition
  backend or clock-admission qualification.
- The [action-4 completion trace](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/tsf/action4-completion-and-report-contract.md)
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
  [network discovery gate](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/adapters/quts-discovery-gate.md):
  `QCDeviceControlFile` or a specific Qualcomm composite-USB fallback. The current
  PCI adapter satisfies neither. The [qualified live follow-up](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/adapters/quts-live-gate-and-commonio.md)
  now corroborates the failed query and exact callsite. It does not prove that
  other Wi-Fi diagnostic paths are absent or directly trace the following branch.
- Extended Ghidra analysis also locates a separate MHI DIAG branch that constructs
  a `Device::Protocol::Diag` object. The [follow-up](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/adapters/quts-mhi-route-validation.md)
  resolves QCDM-description and `mhi.*?` parent predicates and the DIAG connection
  wrapper. FastConnect attribution and its Wi-Fi producer connection remain open.
- The discovery worker's 12,235 recognized instructions are now exported without
  truncation. Earlier passive traces failed coverage or were cancelled. Attempt 06
  uses 32 MiB collector buffers and retains every start/end control; zero loss
  counters alone were insufficient to qualify earlier attempts.
- The lower `CommonIo` trace distinguishes Usb, QmiIo, Ethernet and CommandIo.
  The inspected Usb open may configure communication state/timeouts, so a future
  passive-read claim must account for connection initialization too.
- The [endpoint and receive trace](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/adapters/quts-endpoint-writer-and-receive.md)
  locates the endpoint writer and copied transport chunks. The later
  [callback/framing trace](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/adapters/quts-callback-framing-and-wlanlib.md) closes
  registration through `receiveData`, the locked queue and frame decoding.
  Explicit pressure-drop paths make loss reporting a separate requirement.
- Fresh exact-device enumeration identifies WLANLIB, and the pinned Wi-Fi driver
  registers the matching GUID/reference string. Missing QUTS discovery metadata
  therefore does not mean there is no vendor interface. Its timing semantics and
  native-record-to-client association remain open.
- The [WLANLIB dispatch trace](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/adapters/wlanlib-dispatch-and-completion.md)
  ties the interface to the existing QcomWifi device and private-command table.
  Its ART2 path carries test-event bytes, but drops the segment envelope and can
  publish length after logging mismatches. The fetch clears cache state and has
  no demonstrated reader/writer snapshot lock or timing-event identity contract.
- The Qmux “5G in use” follow-up traces a Wi-Fi channel flag, supporting **5 GHz
  Wi-Fi**, not a demonstrated cellular-state interpretation. Its input byte
  selects query or wait; it cannot select a new response schema.
- [Packet capture and elevation](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/acquisition/packet-capture-and-elevation.md)
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

The [hardware handoff](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/evidence/complete-event-hardware-handoff.md) retains the
2026-10-05 RawService inspection: initialization requires an existing protocol
handle and response notification carries handles rather than event bytes.
Its runtime-absence search is now historical. The
[installed 6.1.365.1 investigation](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/adapters/qmsl-runtime-365.md) establishes
current runtime files and a selected worker/listener ownership chain, while
leaving actual vendor loading, exact live Wi-Fi attribution and bounded shutdown
unqualified. Weak-name reference differences alone do not require binding redirects.

The concrete missing prerequisite is demonstrated access to a supported complete-
event interface or instrumented producer with valid copying and owned application
return. The [S2 decision](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/evidence/hardware-route-decision-2026-10-06.md) records
the no-go and what evidence reopens each route. No live operation is selected;
this refresh adds no live acquisition or clock qualification.

```text
Exact Wi-Fi firmware timing producer
             |
             ?  Complete event copied while producer storage remains valid
             |
Supported vendor interface OR instrumented driver return
             |
             ?  Timing producer-to-response connection NOT established
             |
Owned application bytes
             |  QUTS client copy located; broker tested with fixtures/replay
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
claims that the full pipeline has run. A newly identified protocol must be bound
to the exact adapter before retrieving an existing record. QUTS documents that
enumeration can return an empty list on failure. An empty
list alone cannot distinguish an absent protocol from a failed query. The
[first bounded live run](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/evidence/quts-enumeration-2026-10-04.md) checked query
health separately and stopped on missing Wi-Fi attribution before record access.
Repeating that discovery without a new endpoint or changed evidence would not
establish the missing producer connection. The next hardware attempt depends on
a concrete operation or integration package satisfying the handoff above.

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

- [Archive and installed transport evidence](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/adapters/qualcomm-archive-transport-findings.md).
- [Offline qualification and signatures](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/evidence/qualification-audit-2026-10-04.md).
- [Live QUTS enumeration and its limits](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/evidence/quts-enumeration-2026-10-04.md).
- [Ghidra trace of the native QUTS discovery gate](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/adapters/quts-discovery-gate.md).
- [MHI route, full assembly and live-validation status](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/adapters/quts-mhi-route-validation.md).
- [Repeatable static inspection runbook](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/adapters/static-inspection-runbook.md).
- [Interface directory](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/knowledge/interface-directory.md) and [searchable reference index](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/knowledge/reference-index.md).
- [Packet-to-clock workflow](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/clock-models/packet-to-clock-map.md).
- [Current qualification ledger](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/overview/gap-closure-ledger.md).
- [Repository skill](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/skills/qualcomm-timing-research/SKILL.md).

Publication and hosted checks are recorded on the active research PR. A green
offline suite does not change any of the live qualification states above.
