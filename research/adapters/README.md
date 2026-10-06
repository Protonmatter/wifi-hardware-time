# Adapter discovery: tools

These tools identify the adapter, inspect its advertised services and read cached management-frame information. They establish which device and driver are being studied, not whether its timestamps are accurate. Use their findings to select the correct backend before attempting a separately qualified acquisition experiment.

<!-- current-context:2026-10-04 -->
**Current context (2026-10-04):** Later archive and installed-file inspection located QUTS client-owned byte returns and corrected vendor package/version assumptions; exact adapter-to-producer association remains open. See [current findings](../../docs/knowledge/current-findings.md).
<!-- /current-context -->

## Files

| File | Role |
|---|---|
| [inspect_ihv_queries.py](inspect_ihv_queries.py) | File-only query/control producer map, including GPIO submission and bus-interface attribution; see [findings](../../docs/adapters/ihv-query-producer-map.md). No selector execution. |
| [Invoke-DeviceServiceControl.ps1](Invoke-DeviceServiceControl.ps1) / [device_service_control.c](device_service_control.c) | Default identity preview, offline build/self-test, or bounded enumeration and one fixed-pattern GET. See [live control and runbook](../../docs/evidence/device-service-positive-control.md). |
| [Invoke-QualcommStaticInspection.ps1](Invoke-QualcommStaticInspection.ps1) | Scriptify entry point for preview/apply static inspection; see [runbook](../../docs/adapters/static-inspection-runbook.md). Internal `package_tools` workers are invoked through this gate. |
| [ghidra/TraceAtlasQuts.java](ghidra/TraceAtlasQuts.java) | Exact-hash QPSTServer 496 trace. Default preview; add `--apply` for a new private output directory. |
| [ghidra/TraceQmslQueue.java](ghidra/TraceQmslQueue.java) | Exact-hash QMSL FastConnect 6.1.48.1 x86 trace into a new private directory; selected exports, one caller level and explicit incomplete-output rejection. See [queue findings and command](../../docs/adapters/qmsl-diagnostic-queue.md#reproduction-and-limits). |
| [ghidra/TraceQutsDiscovery.java](ghidra/TraceQutsDiscovery.java) | Pinned native QUTS discovery/protocol traces; private assembly and decompilation exports. Default includes one caller level; optional `scope:seeds-only` limits export to selected functions. See [callback/framing seeds](../../docs/adapters/quts-callback-framing-and-wlanlib.md#reproduction-and-validation). |
| [inspect_qik_inventory.py](inspect_qik_inventory.py) | Validate decoded vendor package file associations, sizes and PE metadata without loading code. See [archive findings](../../docs/adapters/qualcomm-archive-transport-findings.md) for reproduction and limits. |
| [ghidra/TraceQualcommPacketlog.java](ghidra/TraceQualcommPacketlog.java) | Bounded exact-image cross-reference and private assembly/decompilation exports; see [producer findings](../../docs/memory-ring/packetlog-producer-trace.md). |
| [ghidra/AnnotateQualcommTiming.java](ghidra/AnnotateQualcommTiming.java) | Exact-hash Ghidra annotations and private decompilation reports. See the [offline workspace guide](../../docs/adapters/ghidra-workspace.md). |
| [inspect_windows_bss_time.py](inspect_windows_bss_time.py) | Hash-gated offline Windows BSS host-time range inventory; no device or runtime memory access. |
| [inspect_management_rx.py](inspect_management_rx.py) | Offline exact-build management-event schema, handoffs, cleanup and history exclusion; no live capture. See the [producer findings](../../docs/adapters/qualcomm-management-timing-producer.md). |
| [cached_beacon.c](cached_beacon.c) | Probe or native helper; consult its header and the matching research report before use. |
| [device_services.c](device_services.c) | Probe or native helper; consult its header and the matching research report before use. |
| [Get-QualcommAdapter.ps1](Get-QualcommAdapter.ps1) | Read-only adapter/driver identity discovery. |
| [inspect_private_exports.py](inspect_private_exports.py) | Inspect an owned exact-build driver file and record selected private return-path offsets and hashes; no device access. |
| [inspect_wlanlib_dispatch.py](inspect_wlanlib_dispatch.py) | File-only selector and code-window inventory for WLANLIB. Keeps IOCTL, WMI and status namespaces separate; no request execution or timing qualification. See [dispatch findings](../../docs/adapters/wlanlib-dispatch-and-completion.md). |

## Read before running

- [Findings and procedures](../../docs/adapters/README.md).
- [Operations and current admission state](../../docs/overview/OPERATIONS.md).
- [Glossary](../../docs/glossary.md) and [migration guide](../../docs/overview/repository-layout.md).
- Keep outputs in ignored `artifacts/`. A successful command is not a timing-accuracy claim.
