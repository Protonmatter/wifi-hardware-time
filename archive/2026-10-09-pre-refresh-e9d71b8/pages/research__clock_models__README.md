# Clock relationship analysis: tools

> **Archive — not current operating instructions.** Historical documentation at [e9d71b843651](https://github.com/Protonmatter/wifi-hardware-time/commit/e9d71b84365122ff2640e240b20fc1dbb834388a). Relative links are rebased for reading. [Exact original bytes](../originals/research__clock_models__README.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

These tools compare saved counter observations with host timing and test competing conversion models. They can reveal inconsistent assumptions and prediction limits, but cannot establish the physical sampling instant from a good fit. Treat their output as conditional research evidence, not calibrated uncertainty or an enabled clock conversion.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** QUTS and QXDM expose distinct hardware-origin, interpolated and host-delivery times. Owned bytes do not establish fresh hardware-to-QPC sampling or an accuracy bound. See [current findings](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/knowledge/current-findings.md).
<!-- /historical-context -->

## Files

| File | Role |
|---|---|
| [analyze_clock_pairing_hypothesis.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/clock_models/analyze_clock_pairing_hypothesis.py) | Offline analysis/model or file transformation; see the tool header for inputs. |
| [analyze_observation_quality.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/clock_models/analyze_observation_quality.py) | Offline analysis/model or file transformation; see the tool header for inputs. |

## Read before running

- [Findings and procedures](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/clock-models/README.md).
- [Operations and current admission state](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/OPERATIONS.md).
- [Glossary](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/glossary.md) and [migration guide](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/repository-layout.md).
- Keep outputs in ignored `artifacts/`. A successful command is not a timing-accuracy claim.
