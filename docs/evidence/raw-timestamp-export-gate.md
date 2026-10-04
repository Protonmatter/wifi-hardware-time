# Acceptance gate for one trustworthy raw timestamp export

The next milestone requires one real hardware acquisition that returns a complete, attributable timestamp record. Internal buffer locations, successful requests and structurally valid synthetic data do not meet it. This gate lists the required fields and rejection cases, and records which prerequisites remain missing before downstream collection or latency work proceeds.

**Terms:** ABI means the calling and buffer-layout contract. Attribution connects
a record to its actual event or request. An epoch marks a period of continuity.
Meaningful width is the number of counter bits defined by the producer, which
may differ from the storage size. See the [glossary](../glossary.md).

## Contents

- [Current disposition](#current-disposition)
- [Required evidence](#required-evidence)
- [Negative qualification cases](#negative-qualification-cases)
- [Decision and next dependency](#decision-and-next-dependency)

## Current disposition

As of the 2026-10-03 normal-RX and pre-aggregation-FTM investigation:

- Documentation integration is complete on the default branches.
- Internal producer and buffer paths are better understood.
- No existing safe userspace return interface for the required complete record
  was established in the inspected paths.
- No new bounded live export acquisition was attempted. Its prerequisites are
  not met; no hardware timestamp was invented from a host log time or model.
- The private campaign remains quarantined. Reset, suspend and roaming remain
  preparation only. Steps 3 and 4 of the requested sequence remain gated.

This gate is an acceptance specification, not an implemented decoder, provider or
hardware qualification certificate. The existing experimental evidence schema
and downstream capability flags remain unchanged.

The separate [owned-export C prototype](owned-timestamp-export-prototype.md)
now exercises software record ownership and rejection rules with synthetic data.
It does not connect to the running driver or satisfy the required real acquisition.

The [owned-event extension](owned-event-extension.md) now implements separate
synthetic MLO and management records with tested ownership, reference decoding,
loss tracking and rejection rules. These are positive software qualification
results; a real producer connection remains the separate hardware dependency.

## Required evidence

| Requirement | What would satisfy it | Current gap |
|---|---|---|
| Acquisition interface | Exact-build public/private ABI with bounded lengths, status and owned result lifetime | Internal paths identified; safe return mechanism missing |
| Raw value and units | Actual producer value, declared clock domain, unit and meaningful bit width | RX split storage words identified; timing semantics unqualified |
| Event reference point | Defined transmit/receive event or capture point for the recorded value | Diagnostic PPDU-start label is not independent event-point qualification |
| Identity | Source clock/domain and generation, separately from frame/report/exchange identity; request binding only when claiming a solicited response | RX PPDU ID and TSF clock ID are distinct leads; internal FTM request byte is not an on-air dialog token |
| Completeness | Owned record before overwrite/reuse, explicit finalization and structural validity | FTM merge storage is reused; outer success does not imply parser success |
| Validity and loss | Timestamp-specific validity, complete fragments, duplicate/drop accounting | Descriptor completion and local fragment predicates are insufficient alone |
| Epoch/reset | Evidence separating old and new producer generations | No proven late-report isolation or firmware drain |
| Host timing | Explicitly named host observations and, if claimed, a demonstrated fresh hardware/QPC bracket | Callback/log time does not establish a hardware sampling bracket |
| Provenance | Exact hardware, driver, firmware/schema and acquisition-source identity | Driver identity known; loaded firmware/schema contract remains unqualified |

Unknown fields may still be retained as diagnostics. They cannot be relabeled as
known to make this complete-record gate pass. Caller-supplied assertions also do
not authenticate producer semantics.

Autonomous observations such as captured beacons do not need a host request ID.
They need identified event/source-clock provenance and qualified capture timing.
A beacon's embedded peer TSF and its local hardware RX timestamp are separate
clock-domain observations. See [clock versus event identity](../tsf/tsf-association-and-quarantine-disposition.md#clock-identity-is-separate-from-event-identity).

## Negative qualification cases

These are required future exporter tests, not claims that a live exporter has
passed them. Existing model tests cover only their explicitly documented scope.

| Case | Required result |
|---|---|
| Mismatched request/peer/link/exchange | Reject association; retain diagnostic evidence |
| Missing start, fragment gap, duplicate or reordered fragments | Reject unless independently qualified transport semantics resolve completeness |
| Correct reused 8-bit FTM value but old generation | Reject; an added host sequence number alone is not disambiguation |
| Partial parse updates followed by structural error | No successful record publication |
| Pointer valid-looking after buffer reuse or teardown | No retrieval through the stale pointer; reject stale ownership |
| Equal ring copies with stable reservation position | No completeness claim without producer commit or exclusion semantics |
| Timeout followed by a late response | Preserve quarantine; do not assign the response to the next request |
| Missing timestamp-valid flag, unknown units or clock domain | Diagnostic-only record, not complete timestamp capability |
| Loss, identity/build change or cleanup failure | Fail the bounded acquisition and retain evidence |

## Decision and next dependency

The required successful hardware case has not occurred, so the milestone is
**not complete**. Do not proceed to steps 3 and 4 merely because these documents,
static checks or a synthetic validator pass review.

The dependency is a real export contract: either a verified existing route or a
separately authorized instrumented driver/vendor diagnostic facility that copies
and identifies records at the established boundaries. It must then supply fixtures
and one bounded live result for the checks above. Arbitrary register/kernel-memory
access and recovery-triggered dumps are not substitutes for that contract.

Supporting findings:

- [Packet-log return path](../memory-ring/packetlog-return-path.md): binary source connected to IHV completion, with unresolved event contents, snapshot safety and selector/framing requirements.
- [Management timing producer and lifetime](../adapters/qualcomm-management-timing-producer.md): additional reference-schema timing fields, temporary callback ownership and a management-event history exclusion; no live export or hardware/QPC qualification.
- [Normal receive path](../adapters/qualcomm-rx-export-boundary.md).
- [FTM buffer ownership and identity](../ftm/ftm-buffer-ownership-and-identity.md).
- [FTM ingress and application handoff](../ftm/ftm-ingress-to-owned-response.md): temporary decoded storage, cleanup and the still-missing owned export.
- [Private output routes](../adapters/qualcomm-private-output-routes.md): radio-statistics refresh and fixed test payload, neither a complete timestamp export.
- [Ring and timestamp boundaries](../memory-ring/timing-boundary-investigation-2026-10-03.md).
