# Acquisition and lifecycle: tools

These tools collect and assess timing observations, enforce request limits and stop admission when reports are ambiguous or evidence is lost. They distinguish healthy cleanup from proof that firmware work has drained. The historical strict campaign remains quarantined; the later bound profile and optional persistent sampler have separate admission/evidence rules. Lifecycle preparation does not authorize reset, suspend or roaming experiments.

<!-- research-history:2026-10-09 -->
**Research context (2026-10-09):** Tool guide. Use the linked account for goals, result versions, failed assumptions and remaining qualification gates. [Current account](../../docs/research-history/README.md) · [Timeline](../../docs/research-history/timeline.md) · [Previous version](../../archive/2026-10-09-pre-refresh-e9d71b8/pages/research__acquisition__README.md).
<!-- /research-history -->

## Files

| File | Role |
|---|---|
| [run_bound_campaign.py](run_bound_campaign.py) | Exact-build bounded idle/load controller, trace/workload acceptance, adapter-scoped lock and durable unfinished/quarantine records; optional persistent mode. See the [sampler contract](../../docs/acquisition/persistent-tsf-sampler.md) and [all campaign attempts](../../docs/acquisition/tsf-host-bound-results.md). Live execution is separate from preview/offline checks. |
| [persistent_sampler.py](persistent_sampler.py) | Persistent worker/native-operation abstraction, receipts and explicit pending/completion/resource ownership. Normal smoke success does not qualify real cancellation or firmware drain. |
| [bss_reader.py](bss_reader.py) | Public Windows BSS cache reader for the coarse beacon consistency check; host query timing is not radio-reception timing. |
| [Observe-WifiDataPath.ps1](Observe-WifiDataPath.ps1), [wifi-path.wprp](wifi-path.wprp) | Bounded Npcap capture with optional paired CPU tracing, explicit privilege/cleanup receipts and exact-driver checks. See the [live baseline and elevation record](../../docs/acquisition/packet-capture-and-elevation.md). |
| [Observe-QutsRegistry.ps1](Observe-QutsRegistry.ps1), [quts-registry.wprp](quts-registry.wprp) | Preview-first OS registry observer with 32 MiB buffers and bracketed start/end controls. See the [qualified query capture](../../docs/adapters/quts-live-gate-and-commonio.md). |
| [export_registry_trace.c](export_registry_trace.c) | Bounded offline native ETL reader; selected process events plus global key lifecycle. Raw output remains private. |
| [analyze_quts_registry.py](analyze_quts_registry.py) | Offline exact-build query/stack attribution, control coverage and rejection rules. Successful analysis alone does not mean qualification. |
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

- [Persistent TSF sampler v1](../../docs/acquisition/persistent-tsf-sampler.md): optional session reuse, offline validation and phase 2 limits.

- [Findings and procedures](../../docs/acquisition/README.md).
- [Operations and current admission state](../../docs/overview/OPERATIONS.md).
- [Glossary](../../docs/glossary.md) and [migration guide](../../docs/overview/repository-layout.md).
- Keep outputs in ignored `artifacts/`. A successful command is not a timing-accuracy claim.
