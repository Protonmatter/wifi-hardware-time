# Wi-Fi ranging: tools

> **Archive — not current operating instructions.** Historical documentation at [e9d71b843651](https://github.com/Protonmatter/wifi-hardware-time/commit/e9d71b84365122ff2640e240b20fc1dbb834388a). Relative links are rebased for reading. [Exact original bytes](../originals/research__ftm__README.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

These tools investigate Fine Timing Measurement, the Wi-Fi ranging procedure, and the aggregate results returned by the inspected driver. They check completeness and reproduce arithmetic from saved data. They do not expose four qualified absolute exchange times or turn ranging success into a synchronized application clock.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** QXDM WLAN RTT definitions are a new schema lead. They have not been matched to a complete live four-event export from this adapter. See [current findings](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/knowledge/current-findings.md).
<!-- /historical-context -->

## Files

| File | Role |
|---|---|
| [inspect_ftm_ingress.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/ftm/inspect_ftm_ingress.py) | Offline exact-build event-schema, dispatch and cleanup evidence; see the [ownership report](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/ftm/ftm-ingress-to-owned-response.md). |
| [analyze_ftm_deltas.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/ftm/analyze_ftm_deltas.py) | Offline analysis/model or file transformation; see the tool header for inputs. |
| [Capture-FtmOnce.ps1](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/ftm/Capture-FtmOnce.ps1) | Bounded experiment controller/launcher; explicit execution and prerequisites apply. |
| [decode_ftm_response.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/ftm/decode_ftm_response.py) | Offline analysis/model or file transformation; see the tool header for inputs. |
| [Export-FtmDeltaEvents.ps1](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/ftm/Export-FtmDeltaEvents.ps1) | Offline analysis/model or file transformation; see the tool header for inputs. |
| [ftm_once.c](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/ftm/ftm_once.c) | Probe or native helper; consult its header and the matching research report before use. |
| [ftm_result.h](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/ftm/ftm_result.h) | Shared validation, admission or result rules; not a standalone hardware command. |
| [FtmDeltaLog.ps1](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/ftm/FtmDeltaLog.ps1) | Evidence parsing, health checks or read-only topology support. |
| [model_ftm_selection.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/ftm/model_ftm_selection.py) | Offline analysis/model or file transformation; see the tool header for inputs. |

## Read before running

- [Findings and procedures](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/ftm/README.md).
- [Operations and current admission state](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/OPERATIONS.md).
- [Glossary](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/glossary.md) and [migration guide](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/repository-layout.md).
- Keep outputs in ignored `artifacts/`. A successful command is not a timing-accuracy claim.
