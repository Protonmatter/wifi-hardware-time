# Assumptions challenged by evidence

Several plausible shortcuts became incorrect when we followed the bytes or repeated acquisition. This ledger states what changed, why it changed and what the result permits. A disproven interpretation does not erase the underlying measurement. An untested connection remains open even when both endpoints have been located independently.

## Contents

- [How to read the status](#how-to-read-the-status)
- [Acquisition and hardware interpretation](#acquisition-and-hardware-interpretation)
- [Vendor packages and application returns](#vendor-packages-and-application-returns)
- [Claims that remain open](#claims-that-remain-open)

## How to read the status

- **Disproved within scope:** inspected bytes or observed behavior contradict the interpretation.
- **Superseded snapshot:** later files or observations change the current state, not history.
- **Supported within scope:** the evidence supports a specific mechanism or software behavior.
- **Open:** the evidence does not decide the question.

## Acquisition and hardware interpretation

| Earlier interpretation or hypothesis | Status and correction | Evidence / consequence |
|---|---|---|
| Successful private TSF IOCTL completion returns a fresh counter tuple | Disproved for the selected return path: counters arrive asynchronously through diagnostics | [TSF transport](../adapters/qualcomm-minimal-transport-contract.md); keep completion time separate from sampling |
| Successful initial repeated capture qualifies all later reports | Disproved as a general rule: later unmatched reports triggered quarantine | [Campaign disposition](../acquisition/private-campaign-2026-10-03-quarantine.md); no automatic rearming |
| Increasing counters or a small regression residual prove fresh paired samples | Open sampling semantics; neither establishes a common sampling instant | [Counter-rate analysis](../clock-models/counter-rate-identifiability.md) |
| Restarting a collector drains old firmware work | Open; host process/session lifetime is not firmware lifetime | [Association and quarantine](../tsf/tsf-association-and-quarantine-disposition.md) |
| Copying the event wrapper preserves its frame and timing data | Disproved for pointer-bearing temporary wrappers | [Management producer/lifetime](../adapters/qualcomm-management-timing-producer.md); copy owned payloads before cleanup |
| The management callback forwards the candidate timing block | Disproved for the selected reduced handoff | [Management RX handoff](../adapters/qualcomm-management-rx-handoff.md) |
| A packet-log cursor or two equal reads establish a safe snapshot | Disproved by publication order and the modeled counterexample | [Ring boundary investigation](../memory-ring/timing-boundary-investigation-2026-10-03.md) |
| The packet-log writer preserves the complete original management event | Not established: it transforms a log header and copies a separate opaque payload | [Packet-log producer](../memory-ring/packetlog-producer-trace.md) |
| The inspected packet length helper proves contiguous bytes | Disproved: the selected helper reports aggregate fragment length | [MLO/cache follow-up](../memory-ring/mlo-cache-and-symbol-search.md) |
| FTM aggregate RTT or its variance supplies clock offset/uncertainty | Disproved as a supported interpretation of the current output | [FTM provenance](../ftm/ftm-result-provenance.md); raw variance remains unqualified |
| `t3_del` / `t4_del` names establish absolute event values | Open: selected code establishes subtraction and aggregation, not absolute clock semantics | [Clock relationship](../clock-models/clock-relationship-investigation.md) |
| `ullTimestamp` is the local Qualcomm receive clock | Disproved: it comes from the peer's Beacon/Probe Response timestamp | [BSS serialization](../adapters/qualcomm-bss-serialization.md) |
| `ullHostTimestamp` is a hardware receive timestamp | Disproved as that clock-domain claim: the inspected branches use Windows system time/cache age logic | [Host-time origin](../adapters/windows-bss-host-time.md); runtime age-flag state remains unknown |
| Missing private OID handling proves timestamp hardware is unsupported | Unsupported inference: NDIS capability handling and the hardware are distinct | [Documented API follow-up](../windows-timestamps/windows-timestamp-path-followup.md) |
| A matching native PDB has been obtained | Not established by the bounded search | [Symbol search](../memory-ring/mlo-cache-and-symbol-search.md); RSDS match is required |
| Synthetic exporter tests have no practical value | Disproved as a software-engineering assessment: they validate ownership, rejection and lifecycle contracts | [Owned-event extension](../evidence/owned-event-extension.md); they do not establish live hardware accuracy |

## Vendor packages and application returns

All rows below use the [2026-10-04 archive/installed-file investigation](../adapters/qualcomm-archive-transport-findings.md).

| Earlier interpretation or hypothesis | Status and correction | Practical consequence |
|---|---|---|
| The QPST merge module describes the entire 496 package | Disproved: the nested MSI contains 154 files and a 496 server, distinct from the 495 merge-module server | Preserve nested provenance rather than labeling the whole package with one component version |
| QUTS-related names imply a raw timing transport in QPST | Narrowed: located COM interfaces implement connection bookkeeping; selected `IsUsingQUTS` writes false | Do not use the shared-memory name as a packet-ring contract |
| The failed QXDM download establishes absence of useful contents | Disproved as an inference: later download/extraction recovered interfaces and WLAN timing definitions | Retrieval failure is incomplete evidence |
| The old QMSL import library contains the runtime implementation | Disproved by short import records targeting an absent DLL | Symbol inventory is useful, but not a loadable timing backend |
| QMSL `FTM_*` automatically means IEEE Fine Timing Measurement | Disproved terminology equivalence: that API prefix denotes factory test mode | Establish each ranging method separately before use |
| All QMSL 6.1 assemblies can satisfy the current WLAN dependency | Unsupported: current metadata references 6.1.360.1, while earlier snapshots referenced other versions | Match exact assembly/ABI requirements |
| QUTS service/client files are absent now | Superseded: fresh search found an ARM64 service, managed client and Thrift IDLs; a later bounded run performed enumeration | File presence and enumeration are observed; running-image attestation and Wi-Fi protocol association remain limited. See the [live report](../evidence/quts-enumeration-2026-10-04.md) |
| A target-specific QXDM accessor always yields a target timestamp | Disproved by documented fallback to the generic item-store timestamp | Origin/fallback must be explicit in downstream admission |
| An empty QXDM buffer proves a valid empty record | Disproved: error and empty payload can share the same result | Require an independently valid record contract |
| QDSS hardware time equals Wi-Fi TSF or QPC | Open, with no demonstrated clock relationship | Preserve its separate domain and missing-value sentinel |
| QUTS has no identifiable application-owned binary return | Challenged by stronger evidence: generated packet reader calls a concrete Thrift reader that allocates a new byte array | Client ownership pattern is supported statically; server snapshot and Wi-Fi producer connection remain open |
| No Wi-Fi entry in QUTS means no private Wi-Fi diagnostic path exists | Unsupported inference: the selected native network-discovery path requires a control-endpoint advertisement or USB fallback absent on this PCI adapter | [Ghidra discovery gate](../adapters/quts-discovery-gate.md); separate discovery, transport implementation and hardware capability |
| QUTS ignores all network-class devices | Disproved for the inspected enumerator: it explicitly includes `NET`, then applies additional validation | [Native discovery trace](../adapters/quts-discovery-gate.md); the later control-endpoint check matters |
| Zero ETW loss counters prove observation coverage | Disproved by missing start controls in attempts 04–05 despite zero reported losses | [Qualified follow-up](../adapters/quts-live-gate-and-commonio.md): require retained start/end controls as well as loss health |
| The identified QUTS control-endpoint query has only static evidence | Superseded: attempt 06 attributes 12 live missing-value results to the exact adapter key and expected call stack | Query and status established; the following conditional instruction and firmware-event delivery remain separate |
| CommonIo or an MHI label implies one usable Wi-Fi transport | Unsupported: CommonIo has multiple implementations and open semantics; the selected Usb path resolves a discovered endpoint and can configure communication state | Trace the endpoint writer and owning device before live record retrieval |
| The discovered endpoint writer is still unknown | Resolved statically: `ScanDevices` builds entry `+0x894` after validation/admission, using the returned control-name component or description fallback | [Endpoint writer](../adapters/quts-endpoint-writer-and-receive.md); the current PCI adapter's admission failure remains |
| No native owned receive-copy path has been located | Superseded: `ReadFromDevice` feeds a 128 KiB scratch buffer, then separate reference-counted buffers receive copies of at most 16 KiB | Positive implementation evidence; protocol framing, consumer retention and Wi-Fi producer identity remain separate |
| Read success or one callback means one complete firmware record | Unsupported: successful zero-byte reads are possible and chunk boundaries are imposed by the transport worker | Check actual length and qualified framing before record admission |
| A cancel request establishes bounded shutdown | Unsupported: cancellation needs completion; the selected close caller passes an unlimited worker-wait sentinel | [Cancellation trace](../adapters/quts-endpoint-writer-and-receive.md#cancellation-and-completion); no live cancellation or finite deadline qualified |
| QUD USB request ownership can be adopted unchanged | Open and unsafe to assume: selected failure/teardown branches need correction or validation | Carry exactly-once completion and bounded teardown requirements into our implementation |
| Vendor FILETIME comments saying 1600 define the Windows epoch | Disproved against Microsoft's 1601 contract | Treat the local comment as inconsistent and verify actual conversion |

## Claims that remain open

- The exact firmware producer and byte layout for a complete live timing record.
- Fresh TSF/SoC sampling, split-word correction and reference instant.
- Matching QUTS transaction identity to firmware request or unsolicited event identity.
- Server-side publication safety, end-to-end loss visibility and epoch/reset behavior.
- Raw four-event FTM export and arbitrary packet/retry timestamp association.
- Hardware-to-QPC conversion, calibrated accuracy and sub-millisecond synchronization.

The next step is described in [current findings](current-findings.md). None of
these corrections authorizes a disruptive experiment or changes the campaign quarantine.
