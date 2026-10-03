# Windows timestamp APIs: tools

These tools query standard Windows timestamp interfaces and analyze where their requests and completion records travel. They help explain unsuccessful capability queries without assuming the hardware lacks timestamps. Native build helpers, trace collectors and offline analyzers have different effects; read the matching experiment before executing a command.

## Files

| File | Role |
|---|---|
| [analyze_ndis_run.py](analyze_ndis_run.py) | Offline analysis/model or file transformation; see the tool header for inputs. |
| [Build-NdisExperiment.ps1](Build-NdisExperiment.ps1) | Native compilation and build provenance; does not run acquisition. |
| [Capture-NdisTimestampStatus.ps1](Capture-NdisTimestampStatus.ps1) | Bounded experiment controller/launcher; explicit execution and prerequisites apply. |
| [Capture-NdisTimestampStatusV2.ps1](Capture-NdisTimestampStatusV2.ps1) | Bounded experiment controller/launcher; explicit execution and prerequisites apply. |
| [Export-NdisNamedEvents.ps1](Export-NdisNamedEvents.ps1) | Offline analysis/model or file transformation; see the tool header for inputs. |
| [native_caps.c](native_caps.c) | Probe or native helper; consult its header and the matching research report before use. |
| [ndis_evidence.py](ndis_evidence.py) | Evidence parsing, health checks or read-only topology support. |
| [ndis_query_probe.c](ndis_query_probe.c) | Probe or native helper; consult its header and the matching research report before use. |
| [ndis_trace_health.c](ndis_trace_health.c) | Probe or native helper; consult its header and the matching research report before use. |
| [NdisV2Health.ps1](NdisV2Health.ps1) | Evidence parsing, health checks or read-only topology support. |
| [probe_timestamp_caps.py](probe_timestamp_caps.py) | Probe or native helper; consult its header and the matching research report before use. |

## Read before running

- [Findings and procedures](../../docs/windows-timestamps/README.md).
- [Operations and current admission state](../../docs/overview/OPERATIONS.md).
- [Glossary](../../docs/glossary.md) and [migration guide](../../docs/overview/repository-layout.md).
- Keep outputs in ignored `artifacts/`. A successful command is not a timing-accuracy claim.
