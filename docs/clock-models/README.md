# Clock relationships and uncertainty

A counter value becomes useful time only when its clock, event and conversion are understood. These reports map timestamp locations and test models against saved observations. They explain why a good fit or small residual cannot establish calibrated accuracy, especially when sampling instants and independent references are missing.

<!-- current-context:2026-10-04 -->
**Current context (2026-10-04):** QUTS and QXDM expose distinct hardware-origin, interpolated and host-delivery times. Owned bytes do not establish fresh hardware-to-QPC sampling or an accuracy bound. See [current findings](../knowledge/current-findings.md).
<!-- /current-context -->

## Documents

- [Two-phase TSF timestamps: settled results](settled-timestamps.md).
- [Causal TSF provider: replay results](causal-provider-replay.md).
- [TSF-to-host bound preview on saved action-4 samples](tsf-host-bound-preview.md).
- [Qualifying the TSF, FTM and host-clock relationships](clock-relationship-investigation.md).
- [TSF versus SoC: what the reported increments can identify](counter-rate-identifiability.md).
- [Packet-to-clock timestamp map and uncertainty ledger](packet-to-clock-map.md).
- [Offline observation quality: first downstream work package](qualcomm-observation-matrix.md).

## Orientation

- [Glossary](../glossary.md): clock, driver and evidence terms.
- [Reading guide](../README.md): choose a question rather than a filename.
- [Maintained tools](../../research/clock_models/README.md).

## Diagram sources

- [Packet path](diagrams/packets-timestamp-path.mmd).
- [Uncertainty flow](diagrams/uncertainty-timestamp-path.mmd).
- Both appear with explanations and legends in the [packet-to-clock map](packet-to-clock-map.md).
