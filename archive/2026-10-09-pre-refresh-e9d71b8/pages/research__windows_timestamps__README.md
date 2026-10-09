# Windows timestamp APIs: tools

> **Archive — not current operating instructions.** Historical documentation at [e9d71b843651](https://github.com/Protonmatter/wifi-hardware-time/commit/e9d71b84365122ff2640e240b20fc1dbb834388a). Relative links are rebased for reading. [Exact original bytes](../originals/research__windows_timestamps__README.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

These tools query standard Windows timestamp interfaces and analyze where their requests and completion records travel. They help explain unsuccessful capability queries without assuming the hardware lacks timestamps. Native build helpers, trace collectors and offline analyzers have different effects; read the matching experiment before executing a command.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** Vendor/private transport research continues alongside documented Windows APIs. No new hardware-to-QPC result is established by file inspection. See [current findings](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/knowledge/current-findings.md).
<!-- /historical-context -->

## Files

| File | Role |
|---|---|
| [analyze_ndis_run.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/windows_timestamps/analyze_ndis_run.py) | Offline analysis/model or file transformation; see the tool header for inputs. |
| [Build-NdisExperiment.ps1](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/windows_timestamps/Build-NdisExperiment.ps1) | Native compilation and build provenance; does not run acquisition. |
| [Capture-NdisTimestampStatus.ps1](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/windows_timestamps/Capture-NdisTimestampStatus.ps1) | Bounded experiment controller/launcher; explicit execution and prerequisites apply. |
| [Capture-NdisTimestampStatusV2.ps1](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/windows_timestamps/Capture-NdisTimestampStatusV2.ps1) | Bounded experiment controller/launcher; explicit execution and prerequisites apply. |
| [Export-NdisNamedEvents.ps1](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/windows_timestamps/Export-NdisNamedEvents.ps1) | Offline analysis/model or file transformation; see the tool header for inputs. |
| [native_caps.c](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/windows_timestamps/native_caps.c) | Probe or native helper; consult its header and the matching research report before use. |
| [ndis_evidence.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/windows_timestamps/ndis_evidence.py) | Evidence parsing, health checks or read-only topology support. |
| [ndis_query_probe.c](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/windows_timestamps/ndis_query_probe.c) | Probe or native helper; consult its header and the matching research report before use. |
| [ndis_trace_health.c](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/windows_timestamps/ndis_trace_health.c) | Probe or native helper; consult its header and the matching research report before use. |
| [NdisV2Health.ps1](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/windows_timestamps/NdisV2Health.ps1) | Evidence parsing, health checks or read-only topology support. |
| [probe_timestamp_caps.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/windows_timestamps/probe_timestamp_caps.py) | Probe or native helper; consult its header and the matching research report before use. |

## Read before running

- [Findings and procedures](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/windows-timestamps/README.md).
- [Operations and current admission state](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/OPERATIONS.md).
- [Glossary](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/glossary.md) and [migration guide](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/repository-layout.md).
- Keep outputs in ignored `artifacts/`. A successful command is not a timing-accuracy claim.
