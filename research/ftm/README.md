# Wi-Fi ranging: tools

These tools investigate Fine Timing Measurement, the Wi-Fi ranging procedure, and the aggregate results returned by the inspected driver. They check completeness and reproduce arithmetic from saved data. They do not expose four qualified absolute exchange times or turn ranging success into a synchronized application clock.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** QXDM WLAN RTT definitions are a new schema lead. They have not been matched to a complete live four-event export from this adapter. See [current findings](../../docs/knowledge/current-findings.md).
<!-- /historical-context -->

## Files

| File | Role |
|---|---|
| [inspect_ftm_ingress.py](inspect_ftm_ingress.py) | Offline exact-build event-schema, dispatch and cleanup evidence; see the [ownership report](../../docs/ftm/ftm-ingress-to-owned-response.md). |
| [analyze_ftm_deltas.py](analyze_ftm_deltas.py) | Offline analysis/model or file transformation; see the tool header for inputs. |
| [Capture-FtmOnce.ps1](Capture-FtmOnce.ps1) | Bounded experiment controller/launcher; explicit execution and prerequisites apply. |
| [decode_ftm_response.py](decode_ftm_response.py) | Offline analysis/model or file transformation; see the tool header for inputs. |
| [Export-FtmDeltaEvents.ps1](Export-FtmDeltaEvents.ps1) | Offline analysis/model or file transformation; see the tool header for inputs. |
| [ftm_once.c](ftm_once.c) | Probe or native helper; consult its header and the matching research report before use. |
| [ftm_result.h](ftm_result.h) | Shared validation, admission or result rules; not a standalone hardware command. |
| [FtmDeltaLog.ps1](FtmDeltaLog.ps1) | Evidence parsing, health checks or read-only topology support. |
| [model_ftm_selection.py](model_ftm_selection.py) | Offline analysis/model or file transformation; see the tool header for inputs. |

## Read before running

- [Findings and procedures](../../docs/ftm/README.md).
- [Operations and current admission state](../../docs/overview/OPERATIONS.md).
- [Glossary](../../docs/glossary.md) and [migration guide](../../docs/overview/repository-layout.md).
- Keep outputs in ignored `artifacts/`. A successful command is not a timing-accuracy claim.
