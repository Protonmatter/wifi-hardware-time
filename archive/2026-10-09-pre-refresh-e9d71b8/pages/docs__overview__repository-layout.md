# Repository layout and file-location guide

> **Archive — not current operating instructions.** Historical documentation at [e9d71b843651](https://github.com/Protonmatter/wifi-hardware-time/commit/e9d71b84365122ff2640e240b20fc1dbb834388a). Relative links are rebased for reading. [Exact original bytes](../originals/docs__overview__repository-layout.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

The repository now groups maintained scripts, reports and diagram sources by the research question they address. This guide maps old paths to their new locations and explains the compatibility boundary. Command options and evidence rules remain intact, but relocated launch inputs need new manifests and do not inherit fresh hardware qualification.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** Current findings now include complete vendor package inventories, QUTS client ownership and a correction ledger. Historical acquisitions retain their original scope and limits. See [current findings](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/knowledge/current-findings.md).
<!-- /historical-context -->

## Contents

- [Folder roles](#folder-roles)
- [Migration and qualification](#migration-and-qualification)
- [Old-to-new paths](#old-to-new-paths)

## Folder roles

- `research/<topic>/`: maintained scripts and native helper sources.
- `docs/<topic>/`: findings, procedures and topic reading guides.
- `docs/<topic>/diagrams/`: editable Mermaid sources; matching diagrams appear in the reports.
- `tests/`: offline regressions shared across research areas.
- `fixtures/`: synthetic evidence, with its original schemas preserved.
- `docs/reproductions/`: immutable historical source snapshots, stored as text.
- `artifacts/`: ignored local captures and generated outputs.

See the [reading guide](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/README.md) and [glossary](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/glossary.md).

## Migration and qualification

- The old source paths are moved, not duplicate copies or wrappers. Use the new command path with the same options.
- Internal Python imports, PowerShell siblings, build paths and CI commands now use the topic layout.
- Hash-pinned live manifests name the exact scripts they launch. Old path sets are rejected; do not rewrite historical receipts to present them as a new run.
- The decoder C source is byte-identical. The observer C source changes only its decoder include path. A regression reverses that one change and verifies the previously qualified source hash. The relocated source has a new explicit pin; no native binary was changed or rebuilt as a qualification claim.
- Private and failed-observation quarantine markers remain untouched. Reorganization is not a rearm decision or live validation.
- Downstream references pinned to an older Git revision remain valid historical citations. The adopted evidence schema and fixture contents do not change.

## Old-to-new paths

| Previous path | Current location |
|---|---|
| `docs/OPERATIONS.md` | [docs/overview/OPERATIONS.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/OPERATIONS.md) |
| `docs/api-direction.md` | [docs/evidence/api-direction.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/api-direction.md) |
| `docs/axml.md` | [docs/adapters/axml.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/axml.md) |
| `docs/diagrams/adoption-timestamp-path.mmd` | [docs/evidence/diagrams/adoption-timestamp-path.mmd](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/diagrams/adoption-timestamp-path.mmd) |
| `docs/diagrams/ftm-timestamp-path.mmd` | [docs/ftm/diagrams/ftm-timestamp-path.mmd](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/ftm/diagrams/ftm-timestamp-path.mmd) |
| `docs/diagrams/packets-timestamp-path.mmd` | [docs/clock-models/diagrams/packets-timestamp-path.mmd](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/clock-models/diagrams/packets-timestamp-path.mmd) |
| `docs/diagrams/qualcomm-timestamp-path.mmd` | [docs/tsf/diagrams/qualcomm-timestamp-path.mmd](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/diagrams/qualcomm-timestamp-path.mmd) |
| `docs/diagrams/uncertainty-timestamp-path.mmd` | [docs/clock-models/diagrams/uncertainty-timestamp-path.mmd](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/clock-models/diagrams/uncertainty-timestamp-path.mmd) |
| `docs/evidence-contract.md` | [docs/evidence/evidence-contract.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/evidence-contract.md) |
| `docs/experiments.md` | [docs/acquisition/experiments.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/acquisition/experiments.md) |
| `docs/ftm-result-provenance.md` | [docs/ftm/ftm-result-provenance.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/ftm/ftm-result-provenance.md) |
| `docs/packet-to-clock-map.md` | [docs/clock-models/packet-to-clock-map.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/clock-models/packet-to-clock-map.md) |
| `docs/qualcomm.md` | [docs/adapters/qualcomm.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/qualcomm.md) |
| `docs/qualification/acquisition-campaign-2026-10-02-results.md` | [docs/acquisition/acquisition-campaign-2026-10-02-results.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/acquisition/acquisition-campaign-2026-10-02-results.md) |
| `docs/qualification/backend-and-reference-next-steps.md` | [docs/adapters/backend-and-reference-next-steps.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/backend-and-reference-next-steps.md) |
| `docs/qualification/clock-relationship-investigation.md` | [docs/clock-models/clock-relationship-investigation.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/clock-models/clock-relationship-investigation.md) |
| `docs/qualification/counter-rate-identifiability.md` | [docs/clock-models/counter-rate-identifiability.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/clock-models/counter-rate-identifiability.md) |
| `docs/qualification/ftm-notification-routing.md` | [docs/ftm/ftm-notification-routing.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/ftm/ftm-notification-routing.md) |
| `docs/qualification/ftm-raw-access-followup.md` | [docs/ftm/ftm-raw-access-followup.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/ftm/ftm-raw-access-followup.md) |
| `docs/qualification/gap-closure-ledger.md` | [docs/overview/gap-closure-ledger.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/gap-closure-ledger.md) |
| `docs/qualification/lifecycle-matrix.md` | [docs/acquisition/lifecycle-matrix.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/acquisition/lifecycle-matrix.md) |
| `docs/qualification/lifecycle-qualification-preparation.md` | [docs/acquisition/lifecycle-qualification-preparation.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/acquisition/lifecycle-qualification-preparation.md) |
| `docs/qualification/live-acquisition-campaign.md` | [docs/acquisition/live-acquisition-campaign.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/acquisition/live-acquisition-campaign.md) |
| `docs/qualification/ndis-refined-experiment.md` | [docs/windows-timestamps/ndis-refined-experiment.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/windows-timestamps/ndis-refined-experiment.md) |
| `docs/qualification/ndis-rejection-origin-analysis.md` | [docs/windows-timestamps/ndis-rejection-origin-analysis.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/windows-timestamps/ndis-rejection-origin-analysis.md) |
| `docs/qualification/ndis-status-capture-2026-10-03.md` | [docs/windows-timestamps/ndis-status-capture-2026-10-03.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/windows-timestamps/ndis-status-capture-2026-10-03.md) |
| `docs/qualification/ndis-status-observation-path.md` | [docs/windows-timestamps/ndis-status-observation-path.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/windows-timestamps/ndis-status-observation-path.md) |
| `docs/qualification/observer-passive-qualification-2026-10-03.md` | [docs/acquisition/observer-passive-qualification-2026-10-03.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/acquisition/observer-passive-qualification-2026-10-03.md) |
| `docs/qualification/passive-and-retrieval-validation-2026-10-03.md` | [docs/acquisition/passive-and-retrieval-validation-2026-10-03.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/acquisition/passive-and-retrieval-validation-2026-10-03.md) |
| `docs/qualification/private-acquisition-latency.md` | [docs/acquisition/private-acquisition-latency.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/acquisition/private-acquisition-latency.md) |
| `docs/qualification/private-campaign-2026-10-03-quarantine.md` | [docs/acquisition/private-campaign-2026-10-03-quarantine.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/acquisition/private-campaign-2026-10-03-quarantine.md) |
| `docs/qualification/private-timing-acquisition-plan.md` | [docs/acquisition/private-timing-acquisition-plan.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/acquisition/private-timing-acquisition-plan.md) |
| `docs/qualification/private-tsf-fast-paths.md` | [docs/tsf/private-tsf-fast-paths.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/private-tsf-fast-paths.md) |
| `docs/qualification/qualcomm-observation-matrix.md` | [docs/clock-models/qualcomm-observation-matrix.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/clock-models/qualcomm-observation-matrix.md) |
| `docs/qualification/research-delivery-2026-10-02.md` | [docs/evidence/research-delivery-2026-10-02.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/research-delivery-2026-10-02.md) |
| `docs/qualification/scan-comparison-plan.md` | [docs/acquisition/scan-comparison-plan.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/acquisition/scan-comparison-plan.md) |
| `docs/qualification/scan-tsf-results-2026-10-03.md` | [docs/acquisition/scan-tsf-results-2026-10-03.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/acquisition/scan-tsf-results-2026-10-03.md) |
| `docs/qualification/timing-boundary-investigation-2026-10-03.md` | [docs/memory-ring/timing-boundary-investigation-2026-10-03.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/memory-ring/timing-boundary-investigation-2026-10-03.md) |
| `docs/qualification/unmatched-tsf-and-memory-log.md` | [docs/memory-ring/unmatched-tsf-and-memory-log.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/memory-ring/unmatched-tsf-and-memory-log.md) |
| `docs/qualification/windows-timestamp-path-followup.md` | [docs/windows-timestamps/windows-timestamp-path-followup.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/windows-timestamps/windows-timestamp-path-followup.md) |
| `docs/sources.md` | [docs/overview/sources.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/sources.md) |
| `docs/superpowers/plans/2026-10-02-research-to-userspace-clock.md` | [docs/overview/2026-10-02-research-to-userspace-clock.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/2026-10-02-research-to-userspace-clock.md) |
| `docs/validation-execution-catalog.md` | [docs/overview/validation-execution-catalog.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/validation-execution-catalog.md) |
| `docs/validation.md` | [docs/overview/validation.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/validation.md) |
| `experiments/qualcomm/Build-NdisExperiment.ps1` | [research/windows_timestamps/Build-NdisExperiment.ps1](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/windows_timestamps/Build-NdisExperiment.ps1) |
| `experiments/qualcomm/Capture-FtmOnce.ps1` | [research/ftm/Capture-FtmOnce.ps1](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/ftm/Capture-FtmOnce.ps1) |
| `experiments/qualcomm/Capture-LatchExperiment.ps1` | [research/tsf/Capture-LatchExperiment.ps1](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/tsf/Capture-LatchExperiment.ps1) |
| `experiments/qualcomm/Capture-NdisTimestampStatus.ps1` | [research/windows_timestamps/Capture-NdisTimestampStatus.ps1](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/windows_timestamps/Capture-NdisTimestampStatus.ps1) |
| `experiments/qualcomm/Capture-NdisTimestampStatusV2.ps1` | [research/windows_timestamps/Capture-NdisTimestampStatusV2.ps1](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/windows_timestamps/Capture-NdisTimestampStatusV2.ps1) |
| `experiments/qualcomm/Export-FtmDeltaEvents.ps1` | [research/ftm/Export-FtmDeltaEvents.ps1](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/ftm/Export-FtmDeltaEvents.ps1) |
| `experiments/qualcomm/Export-NdisNamedEvents.ps1` | [research/windows_timestamps/Export-NdisNamedEvents.ps1](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/windows_timestamps/Export-NdisNamedEvents.ps1) |
| `experiments/qualcomm/Export-TsfContext.ps1` | [research/acquisition/Export-TsfContext.ps1](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/acquisition/Export-TsfContext.ps1) |
| `experiments/qualcomm/FtmDeltaLog.ps1` | [research/ftm/FtmDeltaLog.ps1](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/ftm/FtmDeltaLog.ps1) |
| `experiments/qualcomm/Get-CampaignIdentity.ps1` | [research/acquisition/Get-CampaignIdentity.ps1](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/acquisition/Get-CampaignIdentity.ps1) |
| `experiments/qualcomm/Invoke-PassiveObservation.ps1` | [research/acquisition/Invoke-PassiveObservation.ps1](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/acquisition/Invoke-PassiveObservation.ps1) |
| `experiments/qualcomm/NdisV2Health.ps1` | [research/windows_timestamps/NdisV2Health.ps1](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/windows_timestamps/NdisV2Health.ps1) |
| `experiments/qualcomm/analyze_clock_pairing_hypothesis.py` | [research/clock_models/analyze_clock_pairing_hypothesis.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/clock_models/analyze_clock_pairing_hypothesis.py) |
| `experiments/qualcomm/analyze_ftm_deltas.py` | [research/ftm/analyze_ftm_deltas.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/ftm/analyze_ftm_deltas.py) |
| `experiments/qualcomm/analyze_latch.py` | [research/tsf/analyze_latch.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/tsf/analyze_latch.py) |
| `experiments/qualcomm/analyze_ndis_run.py` | [research/windows_timestamps/analyze_ndis_run.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/windows_timestamps/analyze_ndis_run.py) |
| `experiments/qualcomm/analyze_observation_quality.py` | [research/clock_models/analyze_observation_quality.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/clock_models/analyze_observation_quality.py) |
| `experiments/qualcomm/analyze_quarantined_tsf.py` | [research/acquisition/analyze_quarantined_tsf.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/acquisition/analyze_quarantined_tsf.py) |
| `experiments/qualcomm/analyze_scan_comparison.py` | [research/acquisition/analyze_scan_comparison.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/acquisition/analyze_scan_comparison.py) |
| `experiments/qualcomm/campaign_gate.py` | [research/acquisition/campaign_gate.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/acquisition/campaign_gate.py) |
| `experiments/qualcomm/decode_ftm_response.py` | [research/ftm/decode_ftm_response.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/ftm/decode_ftm_response.py) |
| `experiments/qualcomm/ftm_once.c` | [research/ftm/ftm_once.c](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/ftm/ftm_once.c) |
| `experiments/qualcomm/ftm_result.h` | [research/ftm/ftm_result.h](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/ftm/ftm_result.h) |
| `experiments/qualcomm/inspect_timing_boundaries.py` | [research/memory_ring/inspect_timing_boundaries.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/memory_ring/inspect_timing_boundaries.py) |
| `experiments/qualcomm/inspect_tsf_routes.py` | [research/tsf/inspect_tsf_routes.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/tsf/inspect_tsf_routes.py) |
| `experiments/qualcomm/live_observer.c` | [research/acquisition/live_observer.c](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/acquisition/live_observer.c) |
| `experiments/qualcomm/model_ftm_selection.py` | [research/ftm/model_ftm_selection.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/ftm/model_ftm_selection.py) |
| `experiments/qualcomm/model_ring_publication.py` | [research/memory_ring/model_ring_publication.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/memory_ring/model_ring_publication.py) |
| `experiments/qualcomm/ndis_evidence.py` | [research/windows_timestamps/ndis_evidence.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/windows_timestamps/ndis_evidence.py) |
| `experiments/qualcomm/ndis_query_probe.c` | [research/windows_timestamps/ndis_query_probe.c](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/windows_timestamps/ndis_query_probe.c) |
| `experiments/qualcomm/ndis_trace_health.c` | [research/windows_timestamps/ndis_trace_health.c](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/windows_timestamps/ndis_trace_health.c) |
| `experiments/qualcomm/run_acquisition_campaign.py` | [research/acquisition/run_acquisition_campaign.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/acquisition/run_acquisition_campaign.py) |
| `experiments/qualcomm/run_passive_observation.py` | [research/acquisition/run_passive_observation.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/acquisition/run_passive_observation.py) |
| `experiments/qualcomm/run_scan_comparison.py` | [research/acquisition/run_scan_comparison.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/acquisition/run_scan_comparison.py) |
| `tools/Capture-TsfReport.ps1` | [research/tsf/Capture-TsfReport.ps1](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/tsf/Capture-TsfReport.ps1) |
| `tools/Get-QualcommAdapter.ps1` | [research/adapters/Get-QualcommAdapter.ps1](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/adapters/Get-QualcommAdapter.ps1) |
| `tools/analyze_tsf_series.py` | [research/tsf/analyze_tsf_series.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/tsf/analyze_tsf_series.py) |
| `tools/cached_beacon.c` | [research/adapters/cached_beacon.c](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/adapters/cached_beacon.c) |
| `tools/campaign_admission.py` | [research/acquisition/campaign_admission.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/acquisition/campaign_admission.py) |
| `tools/decode_tsf_etl.c` | [research/tsf/decode_tsf_etl.c](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/tsf/decode_tsf_etl.c) |
| `tools/device_services.c` | [research/adapters/device_services.c](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/adapters/device_services.c) |
| `tools/export_clock_evidence.py` | [research/evidence/export_clock_evidence.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/evidence/export_clock_evidence.py) |
| `tools/native_caps.c` | [research/windows_timestamps/native_caps.c](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/windows_timestamps/native_caps.c) |
| `tools/observation_lifecycle.py` | [research/acquisition/observation_lifecycle.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/acquisition/observation_lifecycle.py) |
| `tools/probe_timestamp_caps.py` | [research/windows_timestamps/probe_timestamp_caps.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/windows_timestamps/probe_timestamp_caps.py) |
| `tools/qualcomm_probe.py` | [research/tsf/qualcomm_probe.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/tsf/qualcomm_probe.py) |
| `tools/qualcomm_protocol.py` | [research/tsf/qualcomm_protocol.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/tsf/qualcomm_protocol.py) |
| `tools/validate_research_bundle.py` | [research/evidence/validate_research_bundle.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/evidence/validate_research_bundle.py) |
