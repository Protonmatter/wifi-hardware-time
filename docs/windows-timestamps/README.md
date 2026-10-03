# Windows timestamp queries and failure attribution

Why do standard timestamp queries fail on this Windows adapter? The reports progress from error-code ambiguity to live invalid-query diagnostics and static tracing of completion handling. The refined experiment improves trace health and interface association, but does not identify the first rejecting component or demonstrate working hardware or packet timestamps.

NDIS is the Windows network-driver framework; an OID identifies a driver query. A cross timestamp pairs hardware and host counter readings. ETW is Windows event tracing. See the [glossary](../glossary.md).

## Read the evidence in order

| File | Question answered |
|---|---|
| [windows-timestamp-path-followup.md](windows-timestamp-path-followup.md) | Are caller layouts wrong, and can error 23 mean something other than a physical CRC fault? |
| [ndis-status-observation-path.md](ndis-status-observation-path.md) | Which event schemas could expose the original status, and what does interface identity mean? |
| [ndis-status-capture-2026-10-03.md](ndis-status-capture-2026-10-03.md) | What did the first bounded live capture observe, and what trace-health checks were missing? |
| [ndis-rejection-origin-analysis.md](ndis-rejection-origin-analysis.md) | Does the event identify who created the error, or merely who forwarded it? |
| [ndis-refined-experiment.md](ndis-refined-experiment.md) | What did individual query timing, matching topology snapshots and complete trace-health checks resolve? |

Start with the refined experiment for the latest recorded result; use earlier reports for the evidence behind each conclusion. Validation statements in those reports describe their recorded investigation, not new tests performed by reading this index.

## Research tools

- [probe_timestamp_caps.py](../../research/windows_timestamps/probe_timestamp_caps.py) and [native_caps.c](../../research/windows_timestamps/native_caps.c): public capability queries in Python and native code.
- [Build-NdisExperiment.ps1](../../research/windows_timestamps/Build-NdisExperiment.ps1): reproducible native helper build.
- [Capture-NdisTimestampStatus.ps1](../../research/windows_timestamps/Capture-NdisTimestampStatus.ps1): first capture harness.
- [Capture-NdisTimestampStatusV2.ps1](../../research/windows_timestamps/Capture-NdisTimestampStatusV2.ps1): refined bounded capture workflow.
- [ndis_query_probe.c](../../research/windows_timestamps/ndis_query_probe.c) and [ndis_trace_health.c](../../research/windows_timestamps/ndis_trace_health.c): single-query observation and trace-health helpers.
- [Export-NdisNamedEvents.ps1](../../research/windows_timestamps/Export-NdisNamedEvents.ps1) and [NdisV2Health.ps1](../../research/windows_timestamps/NdisV2Health.ps1): named event export and capture-health checks.
- [ndis_evidence.py](../../research/windows_timestamps/ndis_evidence.py) and [analyze_ndis_run.py](../../research/windows_timestamps/analyze_ndis_run.py): offline evidence validation and classification.

Follow the [refined experiment’s preconditions and commands](ndis-refined-experiment.md#build-run-and-analyze) before live collection. Return to the [documentation index](../README.md).
