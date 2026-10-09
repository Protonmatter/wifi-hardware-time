# Windows timestamp queries and failure attribution

> **Archive — not current operating instructions.** Historical documentation at [e9d71b843651](https://github.com/Protonmatter/wifi-hardware-time/commit/e9d71b84365122ff2640e240b20fc1dbb834388a). Relative links are rebased for reading. [Exact original bytes](../originals/docs__windows-timestamps__README.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

Why do standard timestamp queries fail on this Windows adapter? The reports progress from error-code ambiguity to live invalid-query diagnostics and static tracing of completion handling. The refined experiment improves trace health and interface association, but does not identify the first rejecting component or demonstrate working hardware or packet timestamps.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** Vendor/private transport research continues alongside documented Windows APIs. No new hardware-to-QPC result is established by file inspection. See [current findings](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/knowledge/current-findings.md).
<!-- /historical-context -->

NDIS is the Windows network-driver framework; an OID identifies a driver query. A cross timestamp pairs hardware and host counter readings. ETW is Windows event tracing. See the [glossary](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/glossary.md).

## Read the evidence in order

| File | Question answered |
|---|---|
| [windows-timestamp-path-followup.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/windows-timestamps/windows-timestamp-path-followup.md) | Are caller layouts wrong, and can error 23 mean something other than a physical CRC fault? |
| [ndis-status-observation-path.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/windows-timestamps/ndis-status-observation-path.md) | Which event schemas could expose the original status, and what does interface identity mean? |
| [ndis-status-capture-2026-10-03.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/windows-timestamps/ndis-status-capture-2026-10-03.md) | What did the first bounded live capture observe, and what trace-health checks were missing? |
| [ndis-rejection-origin-analysis.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/windows-timestamps/ndis-rejection-origin-analysis.md) | Does the event identify who created the error, or merely who forwarded it? |
| [ndis-refined-experiment.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/windows-timestamps/ndis-refined-experiment.md) | What did individual query timing, matching topology snapshots and complete trace-health checks resolve? |

Start with the refined experiment for the latest recorded result; use earlier reports for the evidence behind each conclusion. Validation statements in those reports describe their recorded investigation, not new tests performed by reading this index.

## Research tools

- [probe_timestamp_caps.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/windows_timestamps/probe_timestamp_caps.py) and [native_caps.c](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/windows_timestamps/native_caps.c): public capability queries in Python and native code.
- [Build-NdisExperiment.ps1](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/windows_timestamps/Build-NdisExperiment.ps1): reproducible native helper build.
- [Capture-NdisTimestampStatus.ps1](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/windows_timestamps/Capture-NdisTimestampStatus.ps1): first capture harness.
- [Capture-NdisTimestampStatusV2.ps1](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/windows_timestamps/Capture-NdisTimestampStatusV2.ps1): refined bounded capture workflow.
- [ndis_query_probe.c](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/windows_timestamps/ndis_query_probe.c) and [ndis_trace_health.c](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/windows_timestamps/ndis_trace_health.c): single-query observation and trace-health helpers.
- [Export-NdisNamedEvents.ps1](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/windows_timestamps/Export-NdisNamedEvents.ps1) and [NdisV2Health.ps1](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/windows_timestamps/NdisV2Health.ps1): named event export and capture-health checks.
- [ndis_evidence.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/windows_timestamps/ndis_evidence.py) and [analyze_ndis_run.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/windows_timestamps/analyze_ndis_run.py): offline evidence validation and classification.

Follow the [refined experiment’s preconditions and commands](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/windows-timestamps/ndis-refined-experiment.md#build-run-and-analyze) before live collection. Return to the [documentation index](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/README.md).
