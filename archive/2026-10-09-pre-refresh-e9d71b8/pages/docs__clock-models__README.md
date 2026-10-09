# Clock relationships and uncertainty

> **Archive — not current operating instructions.** Historical documentation at [e9d71b843651](https://github.com/Protonmatter/wifi-hardware-time/commit/e9d71b84365122ff2640e240b20fc1dbb834388a). Relative links are rebased for reading. [Exact original bytes](../originals/docs__clock-models__README.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

A counter value becomes useful time only when its clock, event and conversion are understood. These reports map timestamp locations and test models against saved observations. They explain why a good fit or small residual cannot establish calibrated accuracy, especially when sampling instants and independent references are missing.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** QUTS and QXDM expose distinct hardware-origin, interpolated and host-delivery times. Owned bytes do not establish fresh hardware-to-QPC sampling or an accuracy bound. See [current findings](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/knowledge/current-findings.md).
<!-- /historical-context -->

## Documents

- [Current mathematics: rate envelopes, availability, settlement and affine polygon](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/clock-models/tsf-mathematics.md).
- [Persistent sampler live smoke and interpretation](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/acquisition/persistent-tsf-smoke-2026-10-08.md).
- [Next research, implementation and testing gates](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/persistent-tsf-next-steps.md).
- [Two-phase TSF timestamps: settled results](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/clock-models/settled-timestamps.md).
- [Causal TSF provider: replay results](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/clock-models/causal-provider-replay.md).
- [TSF-to-host bound preview on saved action-4 samples](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/clock-models/tsf-host-bound-preview.md).
- [Qualifying the TSF, FTM and host-clock relationships](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/clock-models/clock-relationship-investigation.md).
- [TSF versus SoC: what the reported increments can identify](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/clock-models/counter-rate-identifiability.md).
- [Packet-to-clock timestamp map and uncertainty ledger](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/clock-models/packet-to-clock-map.md).
- [Offline observation quality: first downstream work package](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/clock-models/qualcomm-observation-matrix.md).

## Orientation

- [Glossary](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/glossary.md): clock, driver and evidence terms.
- [Reading guide](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/README.md): choose a question rather than a filename.
- [Maintained tools](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/clock_models/README.md).

## Diagram sources

- [Packet path](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/clock-models/diagrams/packets-timestamp-path.mmd).
- [Uncertainty flow](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/clock-models/diagrams/uncertainty-timestamp-path.mmd).
- Both appear with explanations and legends in the [packet-to-clock map](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/clock-models/packet-to-clock-map.md).
