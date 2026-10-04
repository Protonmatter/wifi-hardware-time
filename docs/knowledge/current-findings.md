# Current research findings

We can read diagnostic counters, explain several reductions of timing data, and locate application-owned byte-return mechanisms. The newest evidence adds QXDM WLAN definitions and the installed QUTS client. A complete timing event from this exact Wi-Fi adapter is still missing. Keep software correctness, successful acquisition and calibrated clock accuracy as separate claims.

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
list alone cannot distinguish an absent protocol from a failed query.

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
- [Repeatable static inspection runbook](../adapters/static-inspection-runbook.md).
- [Interface directory](interface-directory.md) and [searchable reference index](reference-index.md).
- [Packet-to-clock workflow](../clock-models/packet-to-clock-map.md).
- [Current qualification ledger](../overview/gap-closure-ledger.md).
- [Repository skill](../../skills/qualcomm-timing-research/SKILL.md).

Publication and hosted checks are recorded on the active research PR. A green
offline suite does not change any of the live qualification states above.
