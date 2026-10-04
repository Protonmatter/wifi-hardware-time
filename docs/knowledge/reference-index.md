# Research reference index

Find the calls, file names, terms and short strings recorded in this research. The machine-readable index links each token to its authored source and line. Use the current findings and assumption ledger to interpret evidence; a source match does not establish a working API.

## Contents

- [Search](#search)
- [Evidence entry points](#evidence-entry-points)
- [Source files](#source-files)

## Search

Indexed **226 source files** and **5847 distinct terms**.

The [JSON index](research-index.json) includes Python definitions/calls, C/Java/PowerShell call-shaped tokens, authored short strings and Markdown code terms. Vendor binaries, local artifacts, historical reproduction sources and generated indexes are excluded. Unresolved call-shaped tokens are explicitly labeled.

```powershell
python research/evidence/build_knowledge_index.py --find GetItemBuffer
python research/evidence/build_knowledge_index.py --find 0x5005
python research/evidence/build_knowledge_index.py --check
```

## Evidence entry points

- [Current findings](current-findings.md): capabilities and remaining dependencies.
- [Assumptions and corrections](assumptions-and-corrections.md): what changed and why.
- [Important interfaces and strings](interface-directory.md): evidence-ranked starting points.
- [Glossary](../glossary.md): concepts and abbreviations.

## Source files

Hashes use UTF-8 text with LF newlines so the navigation index is portable across checkouts. Binary evidence hashes remain separate.

| File | Normalized text SHA-256 prefix |
|---|---|
| [.github/workflows/offline-checks.yml](../../.github/workflows/offline-checks.yml) | `8812f1d4847f` |
| [docs/acquisition/acquisition-campaign-2026-10-02-results.md](../../docs/acquisition/acquisition-campaign-2026-10-02-results.md) | `9497bd3fc5f6` |
| [docs/acquisition/experiments.md](../../docs/acquisition/experiments.md) | `757ecf58decd` |
| [docs/acquisition/lifecycle-matrix.md](../../docs/acquisition/lifecycle-matrix.md) | `ff94ba6c1774` |
| [docs/acquisition/lifecycle-qualification-preparation.md](../../docs/acquisition/lifecycle-qualification-preparation.md) | `893035af4f25` |
| [docs/acquisition/live-acquisition-campaign.md](../../docs/acquisition/live-acquisition-campaign.md) | `beebdf691f97` |
| [docs/acquisition/observer-passive-qualification-2026-10-03.md](../../docs/acquisition/observer-passive-qualification-2026-10-03.md) | `e61d91daea97` |
| [docs/acquisition/passive-and-retrieval-validation-2026-10-03.md](../../docs/acquisition/passive-and-retrieval-validation-2026-10-03.md) | `491e8b28239c` |
| [docs/acquisition/private-acquisition-latency.md](../../docs/acquisition/private-acquisition-latency.md) | `49e23fdcc97d` |
| [docs/acquisition/private-campaign-2026-10-03-quarantine.md](../../docs/acquisition/private-campaign-2026-10-03-quarantine.md) | `a9b8c563ee32` |
| [docs/acquisition/private-timing-acquisition-plan.md](../../docs/acquisition/private-timing-acquisition-plan.md) | `147aae2851af` |
| [docs/acquisition/README.md](../../docs/acquisition/README.md) | `fa257e06bf36` |
| [docs/acquisition/scan-comparison-plan.md](../../docs/acquisition/scan-comparison-plan.md) | `5c2a312cd514` |
| [docs/acquisition/scan-tsf-results-2026-10-03.md](../../docs/acquisition/scan-tsf-results-2026-10-03.md) | `26ea16e56034` |
| [docs/acquisition/timing-qualification-validation-2026-10-04.md](../../docs/acquisition/timing-qualification-validation-2026-10-04.md) | `eb03fb30c7e4` |
| [docs/adapters/axml.md](../../docs/adapters/axml.md) | `db1bd219145b` |
| [docs/adapters/backend-and-reference-next-steps.md](../../docs/adapters/backend-and-reference-next-steps.md) | `9da7599bbb12` |
| [docs/adapters/diagrams/vendor-return-paths.mmd](../../docs/adapters/diagrams/vendor-return-paths.mmd) | `060abaf8a568` |
| [docs/adapters/ghidra-workspace.md](../../docs/adapters/ghidra-workspace.md) | `c7338e8eb501` |
| [docs/adapters/qualcomm-archive-transport-findings.md](../../docs/adapters/qualcomm-archive-transport-findings.md) | `b4eae40206ac` |
| [docs/adapters/qualcomm-bss-serialization.md](../../docs/adapters/qualcomm-bss-serialization.md) | `7e35c2ffac65` |
| [docs/adapters/qualcomm-management-rx-handoff.md](../../docs/adapters/qualcomm-management-rx-handoff.md) | `4db69f6d1969` |
| [docs/adapters/qualcomm-management-timing-producer.md](../../docs/adapters/qualcomm-management-timing-producer.md) | `f858a84bd15a` |
| [docs/adapters/qualcomm-minimal-transport-contract.md](../../docs/adapters/qualcomm-minimal-transport-contract.md) | `d296018f3eb0` |
| [docs/adapters/qualcomm-private-output-routes.md](../../docs/adapters/qualcomm-private-output-routes.md) | `3db8d273ea50` |
| [docs/adapters/qualcomm-rx-export-boundary.md](../../docs/adapters/qualcomm-rx-export-boundary.md) | `e350bdd2ad10` |
| [docs/adapters/qualcomm-software-center-timing-leads.md](../../docs/adapters/qualcomm-software-center-timing-leads.md) | `e29b1e10617c` |
| [docs/adapters/qualcomm.md](../../docs/adapters/qualcomm.md) | `0549a1d14d80` |
| [docs/adapters/README.md](../../docs/adapters/README.md) | `a33a53dc3159` |
| [docs/adapters/static-inspection-runbook.md](../../docs/adapters/static-inspection-runbook.md) | `cdfaac15ce49` |
| [docs/adapters/windows-bss-host-time.md](../../docs/adapters/windows-bss-host-time.md) | `c1d8d6725b1d` |
| [docs/clock-models/clock-relationship-investigation.md](../../docs/clock-models/clock-relationship-investigation.md) | `36cdf2738990` |
| [docs/clock-models/counter-rate-identifiability.md](../../docs/clock-models/counter-rate-identifiability.md) | `fc7ac3dc7bc5` |
| [docs/clock-models/diagrams/ftm-reduction.mmd](../../docs/clock-models/diagrams/ftm-reduction.mmd) | `75cab435f2de` |
| [docs/clock-models/diagrams/packets-timestamp-path.mmd](../../docs/clock-models/diagrams/packets-timestamp-path.mmd) | `4382b7f2c647` |
| [docs/clock-models/diagrams/uncertainty-timestamp-path.mmd](../../docs/clock-models/diagrams/uncertainty-timestamp-path.mmd) | `e6e28e10885e` |
| [docs/clock-models/packet-to-clock-map.md](../../docs/clock-models/packet-to-clock-map.md) | `4e3e4314bb78` |
| [docs/clock-models/qualcomm-observation-matrix.md](../../docs/clock-models/qualcomm-observation-matrix.md) | `4ec14c29650d` |
| [docs/clock-models/README.md](../../docs/clock-models/README.md) | `bee9e1e5a820` |
| [docs/evidence/api-direction.md](../../docs/evidence/api-direction.md) | `cf1792471da3` |
| [docs/evidence/diagrams/adoption-timestamp-path.mmd](../../docs/evidence/diagrams/adoption-timestamp-path.mmd) | `4ead3659baca` |
| [docs/evidence/evidence-contract.md](../../docs/evidence/evidence-contract.md) | `66dd3741d0db` |
| [docs/evidence/owned-event-extension.md](../../docs/evidence/owned-event-extension.md) | `802d62b7fbc6` |
| [docs/evidence/owned-timestamp-export-prototype.md](../../docs/evidence/owned-timestamp-export-prototype.md) | `29c305f3a563` |
| [docs/evidence/raw-timestamp-export-gate.md](../../docs/evidence/raw-timestamp-export-gate.md) | `6e8785dff522` |
| [docs/evidence/README.md](../../docs/evidence/README.md) | `df091e70cd66` |
| [docs/evidence/research-delivery-2026-10-02.md](../../docs/evidence/research-delivery-2026-10-02.md) | `a6863efa34d5` |
| [docs/ftm/diagrams/ftm-timestamp-path.mmd](../../docs/ftm/diagrams/ftm-timestamp-path.mmd) | `f2e1ac10e568` |
| [docs/ftm/diagrams/notification-routing.mmd](../../docs/ftm/diagrams/notification-routing.mmd) | `29a86f20c87c` |
| [docs/ftm/ftm-buffer-ownership-and-identity.md](../../docs/ftm/ftm-buffer-ownership-and-identity.md) | `0bb903d08578` |
| [docs/ftm/ftm-ingress-to-owned-response.md](../../docs/ftm/ftm-ingress-to-owned-response.md) | `bd5ad46f1d71` |
| [docs/ftm/ftm-notification-routing.md](../../docs/ftm/ftm-notification-routing.md) | `7e8aaeb7f7e7` |
| [docs/ftm/ftm-raw-access-followup.md](../../docs/ftm/ftm-raw-access-followup.md) | `0f3d5b59bebb` |
| [docs/ftm/ftm-result-provenance.md](../../docs/ftm/ftm-result-provenance.md) | `b92a2ddb2d94` |
| [docs/ftm/README.md](../../docs/ftm/README.md) | `ac7d5eb3d3b6` |
| [docs/glossary.md](../../docs/glossary.md) | `838e3c21d99f` |
| [docs/knowledge/assumptions-and-corrections.md](../../docs/knowledge/assumptions-and-corrections.md) | `ddd334640ee3` |
| [docs/knowledge/current-findings.md](../../docs/knowledge/current-findings.md) | `18ab1cf0e5b6` |
| [docs/knowledge/interface-directory.md](../../docs/knowledge/interface-directory.md) | `e815e062b45f` |
| [docs/knowledge/refresh-validation.md](../../docs/knowledge/refresh-validation.md) | `65d4637595fc` |
| [docs/knowledge/workflow-diagrams.md](../../docs/knowledge/workflow-diagrams.md) | `cb387f0069df` |
| [docs/memory-ring/diagrams/report-vs-ring.mmd](../../docs/memory-ring/diagrams/report-vs-ring.mmd) | `6c655d36bf66` |
| [docs/memory-ring/mlo-cache-and-symbol-search.md](../../docs/memory-ring/mlo-cache-and-symbol-search.md) | `8bb3e293cf2a` |
| [docs/memory-ring/packetlog-producer-trace.md](../../docs/memory-ring/packetlog-producer-trace.md) | `5fd013840581` |
| [docs/memory-ring/packetlog-return-path.md](../../docs/memory-ring/packetlog-return-path.md) | `2c6a3f1f088e` |
| [docs/memory-ring/README.md](../../docs/memory-ring/README.md) | `c74a8452329e` |
| [docs/memory-ring/timing-boundary-investigation-2026-10-03.md](../../docs/memory-ring/timing-boundary-investigation-2026-10-03.md) | `3bef48b93894` |
| [docs/memory-ring/unmatched-tsf-and-memory-log.md](../../docs/memory-ring/unmatched-tsf-and-memory-log.md) | `11870e0953ca` |
| [docs/overview/2026-10-02-research-to-userspace-clock.md](../../docs/overview/2026-10-02-research-to-userspace-clock.md) | `dfa65e864054` |
| [docs/overview/2026-10-03-first-hardware-clock-plan.md](../../docs/overview/2026-10-03-first-hardware-clock-plan.md) | `76aa080d9cc0` |
| [docs/overview/gap-closure-ledger.md](../../docs/overview/gap-closure-ledger.md) | `12dbef41a057` |
| [docs/overview/OPERATIONS.md](../../docs/overview/OPERATIONS.md) | `325c7d5a27eb` |
| [docs/overview/README.md](../../docs/overview/README.md) | `4a76b26022da` |
| [docs/overview/repository-layout.md](../../docs/overview/repository-layout.md) | `3b542e8223f3` |
| [docs/overview/sources.md](../../docs/overview/sources.md) | `1e0f5cbfc2c0` |
| [docs/overview/validation-execution-catalog.md](../../docs/overview/validation-execution-catalog.md) | `70a4fb777721` |
| [docs/overview/validation.md](../../docs/overview/validation.md) | `5b05ec97f5fb` |
| [docs/README.md](../../docs/README.md) | `950681bca95a` |
| [docs/tsf/autonomous-management-tsf.md](../../docs/tsf/autonomous-management-tsf.md) | `adc80d5cc2d7` |
| [docs/tsf/diagrams/qualcomm-timestamp-path.mmd](../../docs/tsf/diagrams/qualcomm-timestamp-path.mmd) | `1254dc02ffc8` |
| [docs/tsf/private-tsf-fast-paths.md](../../docs/tsf/private-tsf-fast-paths.md) | `4a494dbc4185` |
| [docs/tsf/README.md](../../docs/tsf/README.md) | `51c2c1214369` |
| [docs/tsf/tsf-association-and-quarantine-disposition.md](../../docs/tsf/tsf-association-and-quarantine-disposition.md) | `f72ac44a5b88` |
| [docs/tsf/tsf-evidence-reader.md](../../docs/tsf/tsf-evidence-reader.md) | `8663d588b98d` |
| [docs/windows-timestamps/ndis-refined-experiment.md](../../docs/windows-timestamps/ndis-refined-experiment.md) | `bc6f4fcd7439` |
| [docs/windows-timestamps/ndis-rejection-origin-analysis.md](../../docs/windows-timestamps/ndis-rejection-origin-analysis.md) | `778de55577d3` |
| [docs/windows-timestamps/ndis-status-capture-2026-10-03.md](../../docs/windows-timestamps/ndis-status-capture-2026-10-03.md) | `930769e1df64` |
| [docs/windows-timestamps/ndis-status-observation-path.md](../../docs/windows-timestamps/ndis-status-observation-path.md) | `198efa2f3422` |
| [docs/windows-timestamps/README.md](../../docs/windows-timestamps/README.md) | `5e702eb2b715` |
| [docs/windows-timestamps/windows-timestamp-path-followup.md](../../docs/windows-timestamps/windows-timestamp-path-followup.md) | `577bef786a3d` |
| [README.md](../../README.md) | `70c9b289deb7` |
| [research/acquisition/analyze_quarantined_tsf.py](../../research/acquisition/analyze_quarantined_tsf.py) | `ec7beb1f4e8f` |
| [research/acquisition/analyze_scan_comparison.py](../../research/acquisition/analyze_scan_comparison.py) | `53ca52b97c8d` |
| [research/acquisition/campaign_admission.py](../../research/acquisition/campaign_admission.py) | `3fbcc1b190c5` |
| [research/acquisition/campaign_gate.py](../../research/acquisition/campaign_gate.py) | `1d347eea2011` |
| [research/acquisition/Export-TsfContext.ps1](../../research/acquisition/Export-TsfContext.ps1) | `9376b83b83ed` |
| [research/acquisition/Get-CampaignIdentity.ps1](../../research/acquisition/Get-CampaignIdentity.ps1) | `2955126771e2` |
| [research/acquisition/Invoke-PassiveObservation.ps1](../../research/acquisition/Invoke-PassiveObservation.ps1) | `7ef262fcd61a` |
| [research/acquisition/live_observer.c](../../research/acquisition/live_observer.c) | `d9fbeebe8e90` |
| [research/acquisition/observation_lifecycle.py](../../research/acquisition/observation_lifecycle.py) | `38c030610f30` |
| [research/acquisition/README.md](../../research/acquisition/README.md) | `94b943f090dc` |
| [research/acquisition/run_acquisition_campaign.py](../../research/acquisition/run_acquisition_campaign.py) | `2441e402d286` |
| [research/acquisition/run_passive_observation.py](../../research/acquisition/run_passive_observation.py) | `73f59f63c534` |
| [research/acquisition/run_scan_comparison.py](../../research/acquisition/run_scan_comparison.py) | `d9d4a3596ed5` |
| [research/adapters/cached_beacon.c](../../research/adapters/cached_beacon.c) | `c6ac75115a82` |
| [research/adapters/device_services.c](../../research/adapters/device_services.c) | `dae2dac610a2` |
| [research/adapters/Get-QualcommAdapter.ps1](../../research/adapters/Get-QualcommAdapter.ps1) | `065ffad62964` |
| [research/adapters/ghidra/AnnotateQualcommTiming.java](../../research/adapters/ghidra/AnnotateQualcommTiming.java) | `89e3b0b23f2d` |
| [research/adapters/ghidra/TraceAtlasQuts.java](../../research/adapters/ghidra/TraceAtlasQuts.java) | `baae8731ab45` |
| [research/adapters/ghidra/TraceQualcommPacketlog.java](../../research/adapters/ghidra/TraceQualcommPacketlog.java) | `0429c7eba643` |
| [research/adapters/inspect_management_rx.py](../../research/adapters/inspect_management_rx.py) | `54abff40c5da` |
| [research/adapters/inspect_private_exports.py](../../research/adapters/inspect_private_exports.py) | `ed20202a71a8` |
| [research/adapters/inspect_qik_inventory.py](../../research/adapters/inspect_qik_inventory.py) | `ade4e664ddc4` |
| [research/adapters/inspect_windows_bss_time.py](../../research/adapters/inspect_windows_bss_time.py) | `b0cdb123c85e` |
| [research/adapters/Invoke-QualcommStaticInspection.ps1](../../research/adapters/Invoke-QualcommStaticInspection.ps1) | `55aa6e749020` |
| [research/adapters/package_tools/Expand-QccBlocks.ps1](../../research/adapters/package_tools/Expand-QccBlocks.ps1) | `817d861c092a` |
| [research/adapters/package_tools/expand_qpst.py](../../research/adapters/package_tools/expand_qpst.py) | `281d00e4f129` |
| [research/adapters/package_tools/inspect_files.py](../../research/adapters/package_tools/inspect_files.py) | `fa1bc578c3fb` |
| [research/adapters/package_tools/Read-MsiTables.ps1](../../research/adapters/package_tools/Read-MsiTables.ps1) | `f74d47953a38` |
| [research/adapters/package_tools/Read-TypeLibrary.ps1](../../research/adapters/package_tools/Read-TypeLibrary.ps1) | `09fde4ca4dca` |
| [research/adapters/README.md](../../research/adapters/README.md) | `f5ff4095775d` |
| [research/clock_models/analyze_clock_pairing_hypothesis.py](../../research/clock_models/analyze_clock_pairing_hypothesis.py) | `c2bc6fd87880` |
| [research/clock_models/analyze_observation_quality.py](../../research/clock_models/analyze_observation_quality.py) | `eb5263987e77` |
| [research/clock_models/README.md](../../research/clock_models/README.md) | `900bf9db38f8` |
| [research/evidence/build_knowledge_index.py](../../research/evidence/build_knowledge_index.py) | `2ff070278aa5` |
| [research/evidence/export_clock_evidence.py](../../research/evidence/export_clock_evidence.py) | `a9c4e6892f90` |
| [research/evidence/hardware_observation.py](../../research/evidence/hardware_observation.py) | `ee18d8e79d2c` |
| [research/evidence/README.md](../../research/evidence/README.md) | `b8b828633765` |
| [research/evidence/sync_workflow_diagrams.py](../../research/evidence/sync_workflow_diagrams.py) | `137739ca6ca3` |
| [research/evidence/Update-ResearchKnowledge.ps1](../../research/evidence/Update-ResearchKnowledge.ps1) | `4547d8e08593` |
| [research/evidence/validate_research_bundle.py](../../research/evidence/validate_research_bundle.py) | `d6af87e49ac2` |
| [research/export_contract/README.md](../../research/export_contract/README.md) | `35a4fc25906c` |
| [research/export_contract/Test-TimestampExport.ps1](../../research/export_contract/Test-TimestampExport.ps1) | `8377dfdefbfd` |
| [research/export_contract/timestamp_export.c](../../research/export_contract/timestamp_export.c) | `8fa9d3fcb47e` |
| [research/export_contract/timestamp_export.h](../../research/export_contract/timestamp_export.h) | `dcdb2dae085f` |
| [research/ftm/analyze_ftm_deltas.py](../../research/ftm/analyze_ftm_deltas.py) | `a672af1110d0` |
| [research/ftm/Capture-FtmOnce.ps1](../../research/ftm/Capture-FtmOnce.ps1) | `bf60881064b8` |
| [research/ftm/decode_ftm_response.py](../../research/ftm/decode_ftm_response.py) | `a39a852e66bb` |
| [research/ftm/Export-FtmDeltaEvents.ps1](../../research/ftm/Export-FtmDeltaEvents.ps1) | `9a28129f33f2` |
| [research/ftm/ftm_once.c](../../research/ftm/ftm_once.c) | `11f849276b0e` |
| [research/ftm/ftm_result.h](../../research/ftm/ftm_result.h) | `1c27922f4c0c` |
| [research/ftm/FtmDeltaLog.ps1](../../research/ftm/FtmDeltaLog.ps1) | `0c7663527a4f` |
| [research/ftm/inspect_ftm_ingress.py](../../research/ftm/inspect_ftm_ingress.py) | `7f19dd32d6f3` |
| [research/ftm/model_ftm_selection.py](../../research/ftm/model_ftm_selection.py) | `54d545523807` |
| [research/ftm/README.md](../../research/ftm/README.md) | `48d10eef7ac1` |
| [research/memory_ring/inspect_mlo_cache.py](../../research/memory_ring/inspect_mlo_cache.py) | `0d1fe59ebd6a` |
| [research/memory_ring/inspect_packetlog_return.py](../../research/memory_ring/inspect_packetlog_return.py) | `2b2bf5d45eb6` |
| [research/memory_ring/inspect_timing_boundaries.py](../../research/memory_ring/inspect_timing_boundaries.py) | `2b0afe150ec9` |
| [research/memory_ring/model_ring_publication.py](../../research/memory_ring/model_ring_publication.py) | `adbf0e478923` |
| [research/memory_ring/README.md](../../research/memory_ring/README.md) | `ac86c3197c6b` |
| [research/README.md](../../research/README.md) | `424defb4ff11` |
| [research/tsf/analyze_latch.py](../../research/tsf/analyze_latch.py) | `8f18b8d98b2c` |
| [research/tsf/analyze_tsf_series.py](../../research/tsf/analyze_tsf_series.py) | `f457510b74c7` |
| [research/tsf/Capture-LatchExperiment.ps1](../../research/tsf/Capture-LatchExperiment.ps1) | `dd61f470c07f` |
| [research/tsf/Capture-TsfReport.ps1](../../research/tsf/Capture-TsfReport.ps1) | `3229c4b2185e` |
| [research/tsf/decode_management_tsf.py](../../research/tsf/decode_management_tsf.py) | `6d138e9e6305` |
| [research/tsf/decode_tsf_etl.c](../../research/tsf/decode_tsf_etl.c) | `5cb31b87aed8` |
| [research/tsf/inspect_tsf_report_contract.py](../../research/tsf/inspect_tsf_report_contract.py) | `dd9c54d4c168` |
| [research/tsf/inspect_tsf_routes.py](../../research/tsf/inspect_tsf_routes.py) | `e3bb97d99992` |
| [research/tsf/qualcomm_probe.py](../../research/tsf/qualcomm_probe.py) | `73f3bd49ef9a` |
| [research/tsf/qualcomm_protocol.py](../../research/tsf/qualcomm_protocol.py) | `ad839192c1b0` |
| [research/tsf/read_tsf_evidence.py](../../research/tsf/read_tsf_evidence.py) | `ebe7305387a2` |
| [research/tsf/README.md](../../research/tsf/README.md) | `b9af829d7082` |
| [research/windows_timestamps/analyze_ndis_run.py](../../research/windows_timestamps/analyze_ndis_run.py) | `a78f6488071c` |
| [research/windows_timestamps/Build-NdisExperiment.ps1](../../research/windows_timestamps/Build-NdisExperiment.ps1) | `956aff3ba824` |
| [research/windows_timestamps/Capture-NdisTimestampStatus.ps1](../../research/windows_timestamps/Capture-NdisTimestampStatus.ps1) | `32f00e7c974d` |
| [research/windows_timestamps/Capture-NdisTimestampStatusV2.ps1](../../research/windows_timestamps/Capture-NdisTimestampStatusV2.ps1) | `646f9ac0549c` |
| [research/windows_timestamps/Export-NdisNamedEvents.ps1](../../research/windows_timestamps/Export-NdisNamedEvents.ps1) | `8a924415325f` |
| [research/windows_timestamps/native_caps.c](../../research/windows_timestamps/native_caps.c) | `c6b4cb3ba761` |
| [research/windows_timestamps/ndis_evidence.py](../../research/windows_timestamps/ndis_evidence.py) | `29b846fd40c2` |
| [research/windows_timestamps/ndis_query_probe.c](../../research/windows_timestamps/ndis_query_probe.c) | `42e5bae99d08` |
| [research/windows_timestamps/ndis_trace_health.c](../../research/windows_timestamps/ndis_trace_health.c) | `d6c50d668dfc` |
| [research/windows_timestamps/NdisV2Health.ps1](../../research/windows_timestamps/NdisV2Health.ps1) | `a16d3e8b5557` |
| [research/windows_timestamps/probe_timestamp_caps.py](../../research/windows_timestamps/probe_timestamp_caps.py) | `fea92b8ffd48` |
| [research/windows_timestamps/README.md](../../research/windows_timestamps/README.md) | `ba3432c6f0e2` |
| [skills/qualcomm-timing-research/SKILL.md](../../skills/qualcomm-timing-research/SKILL.md) | `6c9d34afbd78` |
| [tests/native_ftm_result.c](../../tests/native_ftm_result.c) | `e23553339699` |
| [tests/native_timestamp_export.c](../../tests/native_timestamp_export.c) | `c8202461af14` |
| [tests/Test-FtmDeltaLogParser.ps1](../../tests/Test-FtmDeltaLogParser.ps1) | `c8624b012da8` |
| [tests/Test-NdisCaptureHelpers.ps1](../../tests/Test-NdisCaptureHelpers.ps1) | `4c7459c3b151` |
| [tests/Test-NdisV2Health.ps1](../../tests/Test-NdisV2Health.ps1) | `3b07c051a367` |
| [tests/Test-NdisV2Preflight.ps1](../../tests/Test-NdisV2Preflight.ps1) | `b9dbce9159ba` |
| [tests/Test-PassiveLauncher.ps1](../../tests/Test-PassiveLauncher.ps1) | `c2f5d0abf341` |
| [tests/Test-ScanContextSummary.ps1](../../tests/Test-ScanContextSummary.ps1) | `84ed8746f69b` |
| [tests/test_analyze_latch.py](../../tests/test_analyze_latch.py) | `17461a88eb1e` |
| [tests/test_analyze_tsf_series.py](../../tests/test_analyze_tsf_series.py) | `080e5ae955cc` |
| [tests/test_campaign_controller.py](../../tests/test_campaign_controller.py) | `4a67efa7608b` |
| [tests/test_campaign_gate.py](../../tests/test_campaign_gate.py) | `d7590b368736` |
| [tests/test_clock_pairing_hypothesis.py](../../tests/test_clock_pairing_hypothesis.py) | `5261e0ce7a7e` |
| [tests/test_documentation_navigation.py](../../tests/test_documentation_navigation.py) | `5dac016c2228` |
| [tests/test_evidence_contract.py](../../tests/test_evidence_contract.py) | `8d716fe0ed82` |
| [tests/test_export_clock_evidence.py](../../tests/test_export_clock_evidence.py) | `da39f56697fc` |
| [tests/test_ftm_delta_log_parser.py](../../tests/test_ftm_delta_log_parser.py) | `9c8ee6266bf9` |
| [tests/test_ftm_delta_relationship.py](../../tests/test_ftm_delta_relationship.py) | `6aea29de5f35` |
| [tests/test_ftm_ingress.py](../../tests/test_ftm_ingress.py) | `e24f1ce27c6e` |
| [tests/test_ftm_response.py](../../tests/test_ftm_response.py) | `d84a9c2897a8` |
| [tests/test_ftm_selection.py](../../tests/test_ftm_selection.py) | `0a0f6a22f67c` |
| [tests/test_hardware_observation.py](../../tests/test_hardware_observation.py) | `373ac4bb5f56` |
| [tests/test_knowledge_index.py](../../tests/test_knowledge_index.py) | `2835b65df94a` |
| [tests/test_lifecycle_evidence.py](../../tests/test_lifecycle_evidence.py) | `a5a8e1a98125` |
| [tests/test_management_rx_path.py](../../tests/test_management_rx_path.py) | `7d6b16367baf` |
| [tests/test_management_tsf.py](../../tests/test_management_tsf.py) | `4d910521c97c` |
| [tests/test_mlo_cache.py](../../tests/test_mlo_cache.py) | `b948ba1080f6` |
| [tests/test_native_export_contract.py](../../tests/test_native_export_contract.py) | `5276cdc81137` |
| [tests/test_ndis_evidence.py](../../tests/test_ndis_evidence.py) | `6cbfc9194192` |
| [tests/test_ndis_run.py](../../tests/test_ndis_run.py) | `0bc9da0f96a4` |
| [tests/test_observation_quality.py](../../tests/test_observation_quality.py) | `a2f64d489142` |
| [tests/test_observer_drain.py](../../tests/test_observer_drain.py) | `e2f9aa288de4` |
| [tests/test_packetlog_return.py](../../tests/test_packetlog_return.py) | `afebcce544db` |
| [tests/test_passive_observation.py](../../tests/test_passive_observation.py) | `e737a27dbc7c` |
| [tests/test_private_export_routes.py](../../tests/test_private_export_routes.py) | `ef0d0c301dd3` |
| [tests/test_qik_inventory.py](../../tests/test_qik_inventory.py) | `e14b563d2cb6` |
| [tests/test_qualcomm_protocol.py](../../tests/test_qualcomm_protocol.py) | `dcf25de3126f` |
| [tests/test_quarantined_tsf.py](../../tests/test_quarantined_tsf.py) | `d61f48c0d3d9` |
| [tests/test_read_tsf_evidence.py](../../tests/test_read_tsf_evidence.py) | `c0ea33b069f1` |
| [tests/test_research_layout.py](../../tests/test_research_layout.py) | `6cc62e5d0625` |
| [tests/test_ring_publication_model.py](../../tests/test_ring_publication_model.py) | `9a6fcec1e071` |
| [tests/test_scan_comparison.py](../../tests/test_scan_comparison.py) | `61d5ecc0b798` |
| [tests/test_scan_postmortem.py](../../tests/test_scan_postmortem.py) | `efa6f9491d9a` |
| [tests/test_static_inspection.py](../../tests/test_static_inspection.py) | `63473f44c6d2` |
| [tests/test_timing_boundaries.py](../../tests/test_timing_boundaries.py) | `facac334de65` |
| [tests/test_tsf_report_contract.py](../../tests/test_tsf_report_contract.py) | `0d8a83ee060c` |
| [tests/test_tsf_routes.py](../../tests/test_tsf_routes.py) | `b461867a2900` |
| [tests/test_validation_archive.py](../../tests/test_validation_archive.py) | `4b880ac2bfb0` |
| [tests/test_windows_bss_time.py](../../tests/test_windows_bss_time.py) | `defb090e6d97` |
| [tests/test_workflow_diagrams.py](../../tests/test_workflow_diagrams.py) | `b1577f449b54` |
