# Evidence and application handoff

> **Archive — not current operating instructions.** Historical documentation at [e9d71b843651](https://github.com/Protonmatter/wifi-hardware-time/commit/e9d71b84365122ff2640e240b20fc1dbb834388a). Relative links are rebased for reading. [Exact original bytes](../originals/docs__evidence__README.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

This area defines how research observations can be passed to application software without silently becoming accuracy guarantees. It separates raw records, structural validation, clock conversion and synchronization. The format and replay tools exist, but hardware capabilities remain subject to their own sampling, identity, lifecycle and independent-reference requirements.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** A QUTS client-owned byte return is now located statically. Keep client ownership, server publication, firmware identity and timing accuracy as separate qualification states. See [current findings](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/knowledge/current-findings.md).
<!-- /historical-context -->

## Documents

- [Complete-event hardware handoff](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/complete-event-hardware-handoff.md): refreshed installed-file evidence, RawService's existing-protocol requirement and the concrete producer integration deliverable.
- [Source-operation records](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/source-operation-record.md): tested metadata-and-original-byte packaging through the native broker, with strict consumer expectations and no clock capability promotion.
- [Live device-service positive control](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/device-service-positive-control.md): one exact-driver GET returned eight fixed test bytes; a live transport result, separate from firmware timing.
- [Driver event-return integration](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/driver-event-return-integration.md): traced request-queue lifecycle and the required kernel copy, response, cancellation and teardown contract.
- [Concurrent raw-event broker](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/raw-event-response-broker.md): tested native-library/application boundary for fixtures and unqualified replay.
- [Qualification audit, 2026-10-04](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/qualification-audit-2026-10-04.md): exact driver catalog verification, selected publisher signatures, 247 offline tests with zero skips, and published-head CI.
- [Bounded live QUTS enumeration](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/quts-enumeration-2026-10-04.md): two devices enumerated, neither attributable to the active Wi-Fi adapter; record retrieval was not attempted.
- [Proposed hardware-time boundary](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/api-direction.md).
- [Clock evidence contract v1](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/evidence-contract.md).
- [Acceptance gate for a complete raw timestamp export](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/raw-timestamp-export-gate.md).
- [Owned timestamp export prototype](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/owned-timestamp-export-prototype.md): offline C ownership and rejection rules, with synthetic records only.
- [Research delivery: evidence contract, lifecycle and predictive checks](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/research-delivery-2026-10-02.md).

## Orientation

- [Glossary](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/glossary.md): clock, driver and evidence terms.
- [Reading guide](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/README.md): choose a question rather than a filename.
- [Maintained tools](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/evidence/README.md).

## Workflow diagram

The [adoption diagram source](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/diagrams/adoption-timestamp-path.mmd) shows how local host reads remain separate from future hardware conversion. Read the [embedded diagram and legend](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/clock-models/packet-to-clock-map.md#6-proposed-adoption-architecture) for current versus proposed steps.
