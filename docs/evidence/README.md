# Evidence and application handoff

This area defines how research observations can be passed to application software without silently becoming accuracy guarantees. It separates raw records, structural validation, clock conversion and synchronization. The format and replay tools exist, but hardware capabilities remain subject to their own sampling, identity, lifecycle and independent-reference requirements.

## Documents

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
