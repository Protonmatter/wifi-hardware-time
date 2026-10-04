# Current research findings

We can read diagnostic counters and locate application-owned byte returns. Ghidra now identifies a QUTS network-discovery requirement that the active Wi-Fi adapter does not advertise, explaining a selected omission path. This does not rule out its separate private diagnostics. Offline tests and selected signatures pass; a complete attributable Wi-Fi timing event and its relationship to the host clock remain unqualified.

## Contents

- [Established findings](#established-findings)
- [What changed](#what-changed)
- [The remaining connection](#the-remaining-connection)
- [Qualification boundaries](#qualification-boundaries)
- [Continue or reproduce](#continue-or-reproduce)

## Established findings

Snapshot: 2026-10-04. This page is the current interpretation; dated experiment
reports preserve what was observed in their original runs.

| Area | Established result | Practical use |
|---|---|---|
| Private TSF/SoC reports | Exact-build counter observations and action-dependent cache/refresh behavior | Diagnostic records and rejection fixtures |
| FTM ranging | Aggregate results and selected signed-difference processing | Ranging diagnostics; no four-time clock-offset input |
| Management RX | Candidate firmware fields, frame lifetime and selected metadata reduction | Identify where a complete-event copy would need to occur |
| Packet log | Located producer, reservation and return candidates; cursor can precede copy | Prevent unsafe ring polling from being promoted |
| MLO offset cache | Located locked writes and lifecycle-related state | Investigate radio-link relationships separately from QPC |
| Authored exporter | Owned synthetic management/MLO records with rejection and lifecycle tests | Substantive software qualification and an eventual integration boundary |
| QPST/QXDM | Connection interfaces, buffer-return contract and WLAN definition leads | Target the useful interfaces and avoid misleading timestamp accessors |
| Installed QUTS | Client deserialization allocates a byte array for diagnostic payloads | Real static ownership evidence for a possible application return path |
| Live QUTS enumeration | Two returned device locations match a processor and USB device, not the active PCI Wi-Fi adapter; no record acquired | Narrows the missing adapter-to-protocol connection; does not prove absent hardware support |
| Native QUTS discovery | Ghidra locates a network-device control-endpoint advertisement check; the active adapter lacks that advertisement and its USB fallback | Explains one omission path; target the actual vendor transport rather than force a protocol on an unrelated device |
| Qualification audit | Exact driver catalog membership accepted; selected package signatures verified; 247 tests passed with zero skips | Closes the prior compiler/fixture gap; unsigned QUTS files and timing qualification remain separate |

## What changed

The [assumption ledger](assumptions-and-corrections.md) records the evidence and
scope behind each correction. The largest recent changes are:

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
  PCI adapter satisfies neither. This is a static explanation, not a captured
  live rejection branch or proof that other Wi-Fi diagnostic paths are absent.
- Extended Ghidra analysis also locates a separate MHI DIAG branch that constructs
  a `Device::Protocol::Diag` object. The [follow-up](../adapters/quts-mhi-route-validation.md)
  resolves QCDM-description and `mhi.*?` parent predicates and the DIAG connection
  wrapper. FastConnect attribution and its Wi-Fi producer connection remain open.
- The discovery worker's 12,235 recognized instructions are now exported without
  truncation. Two passive OS traces did not pass event-coverage validation; the
  corrected system-registry capture was not executed after UAC cancellation.
- The previously skipped native C and Windows BSS image tests passed after
  configuring the installed toolchain and exact fixtures. Published revision
  `5d6695c` has successful hosted CI; later revisions require their own hosted
  results. The MHI follow-up also passed all 247 local tests with zero skips.

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
