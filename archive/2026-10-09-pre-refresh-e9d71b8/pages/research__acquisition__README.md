# Acquisition and lifecycle: tools

> **Archive — not current operating instructions.** Historical documentation at [e9d71b843651](https://github.com/Protonmatter/wifi-hardware-time/commit/e9d71b84365122ff2640e240b20fc1dbb834388a). Relative links are rebased for reading. [Exact original bytes](../originals/research__acquisition__README.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

These tools collect and assess timing observations, enforce request limits and stop admission when reports are ambiguous or evidence is lost. They distinguish healthy cleanup from proof that firmware work has drained. Private acquisition remains quarantined, and lifecycle preparation does not authorize reset, suspend or roaming experiments.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** The private campaign remains quarantined. The new QUTS client ownership finding does not establish firmware drain, report association or a new live acquisition. See [current findings](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/knowledge/current-findings.md).
<!-- /historical-context -->

## Files

| File | Role |
|---|---|
| [Observe-WifiDataPath.ps1](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/acquisition/Observe-WifiDataPath.ps1), [wifi-path.wprp](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/acquisition/wifi-path.wprp) | Bounded Npcap capture with optional paired CPU tracing, explicit privilege/cleanup receipts and exact-driver checks. See the [live baseline and elevation record](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/acquisition/packet-capture-and-elevation.md). |
| [Observe-QutsRegistry.ps1](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/acquisition/Observe-QutsRegistry.ps1), [quts-registry.wprp](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/acquisition/quts-registry.wprp) | Preview-first OS registry observer with 32 MiB buffers and bracketed start/end controls. See the [qualified query capture](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/quts-live-gate-and-commonio.md). |
| [export_registry_trace.c](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/acquisition/export_registry_trace.c) | Bounded offline native ETL reader; selected process events plus global key lifecycle. Raw output remains private. |
| [analyze_quts_registry.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/acquisition/analyze_quts_registry.py) | Offline exact-build query/stack attribution, control coverage and rejection rules. Successful analysis alone does not mean qualification. |
| [analyze_quarantined_tsf.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/acquisition/analyze_quarantined_tsf.py) | Offline analysis/model or file transformation; see the tool header for inputs. |
| [analyze_scan_comparison.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/acquisition/analyze_scan_comparison.py) | Offline analysis/model or file transformation; see the tool header for inputs. |
| [campaign_admission.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/acquisition/campaign_admission.py) | Shared validation, admission or result rules; not a standalone hardware command. |
| [campaign_gate.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/acquisition/campaign_gate.py) | Shared validation, admission or result rules; not a standalone hardware command. |
| [Export-TsfContext.ps1](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/acquisition/Export-TsfContext.ps1) | Offline analysis/model or file transformation; see the tool header for inputs. |
| [Get-CampaignIdentity.ps1](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/acquisition/Get-CampaignIdentity.ps1) | Read-only adapter/driver identity discovery. |
| [Invoke-PassiveObservation.ps1](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/acquisition/Invoke-PassiveObservation.ps1) | Bounded experiment controller/launcher; explicit execution and prerequisites apply. |
| [live_observer.c](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/acquisition/live_observer.c) | Probe or native helper; consult its header and the matching research report before use. |
| [observation_lifecycle.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/acquisition/observation_lifecycle.py) | Offline analysis/model or file transformation; see the tool header for inputs. |
| [run_acquisition_campaign.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/acquisition/run_acquisition_campaign.py) | Bounded experiment controller/launcher; explicit execution and prerequisites apply. |
| [run_passive_observation.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/acquisition/run_passive_observation.py) | Bounded experiment controller/launcher; explicit execution and prerequisites apply. |
| [run_scan_comparison.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/acquisition/run_scan_comparison.py) | Bounded experiment controller/launcher; explicit execution and prerequisites apply. |

## Read before running

- [Persistent TSF sampler v1](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/acquisition/persistent-tsf-sampler.md): optional session reuse, offline validation and phase 2 limits.

- [Findings and procedures](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/acquisition/README.md).
- [Operations and current admission state](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/OPERATIONS.md).
- [Glossary](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/glossary.md) and [migration guide](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/repository-layout.md).
- Keep outputs in ignored `artifacts/`. A successful command is not a timing-accuracy claim.
