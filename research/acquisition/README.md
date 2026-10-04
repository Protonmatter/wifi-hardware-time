# Acquisition and lifecycle: tools

These tools collect and assess timing observations, enforce request limits and stop admission when reports are ambiguous or evidence is lost. They distinguish healthy cleanup from proof that firmware work has drained. Private acquisition remains quarantined, and lifecycle preparation does not authorize reset, suspend or roaming experiments.

<!-- current-context:2026-10-04 -->
**Current context (2026-10-04):** The private campaign remains quarantined. The new QUTS client ownership finding does not establish firmware drain, report association or a new live acquisition. See [current findings](../../docs/knowledge/current-findings.md).
<!-- /current-context -->

## Files

| File | Role |
|---|---|
| [Observe-QutsRegistry.ps1](Observe-QutsRegistry.ps1), [quts-registry.wprp](quts-registry.wprp) | Preview-first, exact-identity passive OS registry observer. The final system-provider profile is prepared but not live-qualified; see the [coverage record](../../docs/adapters/quts-mhi-route-validation.md). |
| [analyze_quarantined_tsf.py](analyze_quarantined_tsf.py) | Offline analysis/model or file transformation; see the tool header for inputs. |
| [analyze_scan_comparison.py](analyze_scan_comparison.py) | Offline analysis/model or file transformation; see the tool header for inputs. |
| [campaign_admission.py](campaign_admission.py) | Shared validation, admission or result rules; not a standalone hardware command. |
| [campaign_gate.py](campaign_gate.py) | Shared validation, admission or result rules; not a standalone hardware command. |
| [Export-TsfContext.ps1](Export-TsfContext.ps1) | Offline analysis/model or file transformation; see the tool header for inputs. |
| [Get-CampaignIdentity.ps1](Get-CampaignIdentity.ps1) | Read-only adapter/driver identity discovery. |
| [Invoke-PassiveObservation.ps1](Invoke-PassiveObservation.ps1) | Bounded experiment controller/launcher; explicit execution and prerequisites apply. |
| [live_observer.c](live_observer.c) | Probe or native helper; consult its header and the matching research report before use. |
| [observation_lifecycle.py](observation_lifecycle.py) | Offline analysis/model or file transformation; see the tool header for inputs. |
| [run_acquisition_campaign.py](run_acquisition_campaign.py) | Bounded experiment controller/launcher; explicit execution and prerequisites apply. |
| [run_passive_observation.py](run_passive_observation.py) | Bounded experiment controller/launcher; explicit execution and prerequisites apply. |
| [run_scan_comparison.py](run_scan_comparison.py) | Bounded experiment controller/launcher; explicit execution and prerequisites apply. |

## Read before running

- [Findings and procedures](../../docs/acquisition/README.md).
- [Operations and current admission state](../../docs/overview/OPERATIONS.md).
- [Glossary](../../docs/glossary.md) and [migration guide](../../docs/overview/repository-layout.md).
- Keep outputs in ignored `artifacts/`. A successful command is not a timing-accuracy claim.
