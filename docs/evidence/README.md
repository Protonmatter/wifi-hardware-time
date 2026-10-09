# Evidence and application handoff

This area defines how research observations can be passed to application software without silently becoming accuracy guarantees. It separates raw records, structural validation, clock conversion and synchronization. The format and replay tools exist, but hardware capabilities remain subject to their own sampling, identity, lifecycle and independent-reference requirements.

<!-- research-history:2026-10-09 -->
**Research context (2026-10-09):** Maintained reading guide. Use the linked account for goals, result versions, failed assumptions and remaining qualification gates. [Current account](../research-history/README.md) · [Timeline](../research-history/timeline.md) · [Previous version](../../archive/2026-10-09-pre-refresh-e9d71b8/pages/docs__evidence__README.md).
<!-- /research-history -->

## Documents

- [Research results and related downstream work](../research-history/results-and-validation.md): separate acquisitions, conditional models, software qualification and current gaps.
- [Complete-event hardware handoff](complete-event-hardware-handoff.md): refreshed installed-file evidence, RawService's existing-protocol requirement and the concrete producer integration deliverable.
- [Source-operation records](source-operation-record.md): tested metadata-and-original-byte packaging through the native broker, with strict consumer expectations and no clock capability promotion.
- [Live device-service positive control](device-service-positive-control.md): one exact-driver GET returned eight fixed test bytes; a live transport result, separate from firmware timing.
- [Driver event-return integration](driver-event-return-integration.md): traced request-queue lifecycle and the required kernel copy, response, cancellation and teardown contract.
- [Concurrent raw-event broker](raw-event-response-broker.md): tested native-library/application boundary for fixtures and unqualified replay.
- [Qualification audit, 2026-10-04](qualification-audit-2026-10-04.md): exact driver catalog verification, selected publisher signatures, 247 offline tests with zero skips, and published-head CI.
- [Bounded live QUTS enumeration](quts-enumeration-2026-10-04.md): two devices enumerated, neither attributable to the active Wi-Fi adapter; record retrieval was not attempted.
- [Proposed hardware-time boundary](api-direction.md).
- [Clock evidence contract v1](evidence-contract.md).
- [Acceptance gate for a complete raw timestamp export](raw-timestamp-export-gate.md).
- [Owned timestamp export prototype](owned-timestamp-export-prototype.md): offline C ownership and rejection rules, with synthetic records only.
- [Research delivery: evidence contract, lifecycle and predictive checks](research-delivery-2026-10-02.md).

## Orientation

- [Glossary](../glossary.md): clock, driver and evidence terms.
- [Reading guide](../README.md): choose a question rather than a filename.
- [Maintained tools](../../research/evidence/README.md).

## Workflow diagram

The [adoption diagram source](diagrams/adoption-timestamp-path.mmd) shows how local host reads remain separate from future hardware conversion. Read the [embedded diagram and legend](../clock-models/packet-to-clock-map.md#6-proposed-adoption-architecture) for current versus proposed steps.
