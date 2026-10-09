# Wi-Fi Hardware Time

> **Archive — not current operating instructions.** Historical documentation at [fdcc22f80ad1](https://github.com/Protonmatter/wifi-hardware-time/commit/fdcc22f80ad173a2f4f2844c0f6b666794fda54a). Relative links are rebased for reading. [Exact original bytes](../originals/README.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

Research into exposing Wi-Fi hardware clocks, packet timestamps, and clock correlation through a reusable API.

The initial investigation covers the **ALFA AWUS036AXML / MediaTek MT7921AUN** on Linux and Windows, and a **Qualcomm FastConnect 7800** Windows ARM64 driver. It includes source-backed findings, narrow diagnostic tools, and explicit qualification limits.

**Status: research and diagnostic prototypes. No end-to-end PTP synchronization or timing-accuracy claim has been validated.**

The latest [private campaign is quarantined](https://github.com/Protonmatter/wifi-hardware-time/blob/fdcc22f80ad173a2f4f2844c0f6b666794fda54a/docs/qualification/private-campaign-2026-10-03-quarantine.md)
after unmatched TSF reports. The cleanup repair has offline regressions and one
successful [passive live check](https://github.com/Protonmatter/wifi-hardware-time/blob/fdcc22f80ad173a2f4f2844c0f6b666794fda54a/docs/qualification/passive-and-retrieval-validation-2026-10-03.md);
it does not rearm acquisition or qualify the rejected capture.

## What has been established

| Backend | Evidence | Remaining gap |
|---|---|---|
| Linux mt76 / MT7921 USB | TSF read/write callbacks, RX descriptor timing, USB TX-status processing, defined TX timestamp field | A reliable error-reporting snapshot API, TX semantics, reset epochs, PHC/socket timestamp integration |
| Windows MediaTek 1.0.0.119 x64 | Static private register read/write and firmware response paths | Live hardware qualification; standard NDIS timestamp exposure unproven |
| Windows Qualcomm 1.0.4374.1300 ARM64 | Repeated TSF reports, action-dependent SoC refresh, and six successful FTM operations | Exact sampling/simultaneity, independent-reference accuracy, safe registers, and arbitrary packet timestamps remain unqualified |

On the inspected Qualcomm system, standard timestamp-capability and cross-timestamp APIs returned Win32 **23 / ERROR_CRC**, including elevated queries. Failed queries are not interpreted as capability absence. FTM operations succeeded, but their reported RTT values did not agree with a rough distance estimate; no calibrated ranging accuracy is claimed.

## Contents

- [Findings, validation scripts and historical source catalog](https://github.com/Protonmatter/wifi-hardware-time/blob/fdcc22f80ad173a2f4f2844c0f6b666794fda54a/docs/validation-execution-catalog.md)
- [Unmatched TSF reports and a pre-ETW memory-log lead](https://github.com/Protonmatter/wifi-hardware-time/blob/fdcc22f80ad173a2f4f2844c0f6b666794fda54a/docs/qualification/unmatched-tsf-and-memory-log.md)
- [Passive live validation and scan attribution lead](https://github.com/Protonmatter/wifi-hardware-time/blob/fdcc22f80ad173a2f4f2844c0f6b666794fda54a/docs/qualification/passive-and-retrieval-validation-2026-10-03.md)
- [Controlled scan/TSF results](https://github.com/Protonmatter/wifi-hardware-time/blob/fdcc22f80ad173a2f4f2844c0f6b666794fda54a/docs/qualification/scan-tsf-results-2026-10-03.md)
- [Qualification gap closure ledger](https://github.com/Protonmatter/wifi-hardware-time/blob/fdcc22f80ad173a2f4f2844c0f6b666794fda54a/docs/qualification/gap-closure-ledger.md)

Current direction: [private timing acquisition](https://github.com/Protonmatter/wifi-hardware-time/blob/fdcc22f80ad173a2f4f2844c0f6b666794fda54a/docs/qualification/private-timing-acquisition-plan.md).
Private exact-build interfaces are first-class research candidates; public NDIS
support is not a prerequisite for the Qualcomm research backend.

- [ALFA / MediaTek investigation](https://github.com/Protonmatter/wifi-hardware-time/blob/fdcc22f80ad173a2f4f2844c0f6b666794fda54a/docs/axml.md)
- [Qualcomm private timing path](https://github.com/Protonmatter/wifi-hardware-time/blob/fdcc22f80ad173a2f4f2844c0f6b666794fda54a/docs/qualcomm.md)
- [Validation ledger and limits](https://github.com/Protonmatter/wifi-hardware-time/blob/fdcc22f80ad173a2f4f2844c0f6b666794fda54a/docs/validation.md)
- [Proposed API boundary](https://github.com/Protonmatter/wifi-hardware-time/blob/fdcc22f80ad173a2f4f2844c0f6b666794fda54a/docs/api-direction.md)
- [Operations and reproducibility](https://github.com/Protonmatter/wifi-hardware-time/blob/fdcc22f80ad173a2f4f2844c0f6b666794fda54a/docs/OPERATIONS.md)
- [TSF capture and offline series analysis](https://github.com/Protonmatter/wifi-hardware-time/blob/fdcc22f80ad173a2f4f2844c0f6b666794fda54a/docs/OPERATIONS.md#capture-and-analyze-a-tsf-series)
- [Exact-build latch and FTM experiments](https://github.com/Protonmatter/wifi-hardware-time/blob/fdcc22f80ad173a2f4f2844c0f6b666794fda54a/docs/experiments.md)
- [FTM aggregation and TSF report provenance](https://github.com/Protonmatter/wifi-hardware-time/blob/fdcc22f80ad173a2f4f2844c0f6b666794fda54a/docs/ftm-result-provenance.md)
- [Research-to-userspace-clock roadmap](https://github.com/Protonmatter/wifi-hardware-time/blob/fdcc22f80ad173a2f4f2844c0f6b666794fda54a/docs/superpowers/plans/2026-10-02-research-to-userspace-clock.md)
- [Offline evidence contract and downstream handoff](https://github.com/Protonmatter/wifi-hardware-time/blob/fdcc22f80ad173a2f4f2844c0f6b666794fda54a/docs/evidence-contract.md)
- [Held-out observation-quality results](https://github.com/Protonmatter/wifi-hardware-time/blob/fdcc22f80ad173a2f4f2844c0f6b666794fda54a/docs/qualification/qualcomm-observation-matrix.md)
- [Lifecycle invalidation rules](https://github.com/Protonmatter/wifi-hardware-time/blob/fdcc22f80ad173a2f4f2844c0f6b666794fda54a/docs/qualification/lifecycle-matrix.md)
- [Guarded live acquisition campaign and execution status](https://github.com/Protonmatter/wifi-hardware-time/blob/fdcc22f80ad173a2f4f2844c0f6b666794fda54a/docs/qualification/live-acquisition-campaign.md)
- [Completed idle/workload campaign results](https://github.com/Protonmatter/wifi-hardware-time/blob/fdcc22f80ad173a2f4f2844c0f6b666794fda54a/docs/qualification/acquisition-campaign-2026-10-02-results.md)
- [Packet-to-clock workflow diagrams and uncertainty map](https://github.com/Protonmatter/wifi-hardware-time/blob/fdcc22f80ad173a2f4f2844c0f6b666794fda54a/docs/packet-to-clock-map.md)
- [FTM and TSF/SoC clock-relationship investigation](https://github.com/Protonmatter/wifi-hardware-time/blob/fdcc22f80ad173a2f4f2844c0f6b666794fda54a/docs/qualification/clock-relationship-investigation.md)
- [Pre-aggregation FTM export investigation](https://github.com/Protonmatter/wifi-hardware-time/blob/fdcc22f80ad173a2f4f2844c0f6b666794fda54a/docs/qualification/ftm-raw-access-followup.md)
- [Windows cross-timestamp error and packet timestamp paths](https://github.com/Protonmatter/wifi-hardware-time/blob/fdcc22f80ad173a2f4f2844c0f6b666794fda54a/docs/qualification/windows-timestamp-path-followup.md)
- [NDIS raw-status observation path](https://github.com/Protonmatter/wifi-hardware-time/blob/fdcc22f80ad173a2f4f2844c0f6b666794fda54a/docs/qualification/ndis-status-observation-path.md)
- [Bounded live NDIS status capture](https://github.com/Protonmatter/wifi-hardware-time/blob/fdcc22f80ad173a2f4f2844c0f6b666794fda54a/docs/qualification/ndis-status-capture-2026-10-03.md)
- [Refined NDIS experiment and capability qualification](https://github.com/Protonmatter/wifi-hardware-time/blob/fdcc22f80ad173a2f4f2844c0f6b666794fda54a/docs/qualification/ndis-refined-experiment.md)
- [NDIS rejection origin and interface-scoped activities](https://github.com/Protonmatter/wifi-hardware-time/blob/fdcc22f80ad173a2f4f2844c0f6b666794fda54a/docs/qualification/ndis-rejection-origin-analysis.md)
- [FTM notification and TSF routing](https://github.com/Protonmatter/wifi-hardware-time/blob/fdcc22f80ad173a2f4f2844c0f6b666794fda54a/docs/qualification/ftm-notification-routing.md)
- [TSF/SoC rate identifiability](https://github.com/Protonmatter/wifi-hardware-time/blob/fdcc22f80ad173a2f4f2844c0f6b666794fda54a/docs/qualification/counter-rate-identifiability.md)
- [Stronger timestamp paths and equipment gates](https://github.com/Protonmatter/wifi-hardware-time/blob/fdcc22f80ad173a2f4f2844c0f6b666794fda54a/docs/qualification/backend-and-reference-next-steps.md)
- [Pinned sources and provenance](https://github.com/Protonmatter/wifi-hardware-time/blob/fdcc22f80ad173a2f4f2844c0f6b666794fda54a/docs/sources.md)

## Quick start

Python 3.11 or later is the intended baseline. The original local inspection used Python 3.14 on Windows ARM64. The public test workflow uses Python 3.11.

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

The protocol tests are offline and do not open a device. The optional driver-fixture test is skipped unless `WIFI_TIME_DRIVER_FIXTURE` points to a locally owned copy of the exact qualified SYS file.

For documented Windows timestamp-capability queries, first identify the interface:

```powershell
Get-NetAdapter | Select-Object Name, ifIndex, InterfaceDescription, Status
python tools/probe_timestamp_caps.py --if-index 7
```

Replace `7` with the intended interface index. The tool reads supported/active capabilities and requests one cross timestamp only if the active configuration advertises it. It does not enable timestamping or change adapter settings.

The Qualcomm private probe **previews by default**:

```powershell
python tools/qualcomm_probe.py --if-index 7 --command get_hostdbglvl
```

It discovers the actual active driver, enforces an exact binary hash and command layout, and builds the request without opening the private device. `--execute` explicitly enables one private request. Read the [operations guide](https://github.com/Protonmatter/wifi-hardware-time/blob/fdcc22f80ad173a2f4f2844c0f6b666794fda54a/docs/OPERATIONS.md) before using that option. A TSF read can submit a firmware action even though it does not enable automatic reporting or reset a counter.

## Publication boundary

This repository contains authored research notes and tools. Proprietary driver installers, SYS/DLL files, firmware, raw disassembly, ETL/packet captures, and endpoint-specific identifiers are excluded. Driver hashes identify the inspected artifacts; they do not grant redistribution rights. Obtain vendor software from its legitimate source.

The initial import does not select a distribution license. Third-party sources remain governed by their respective licenses; they are linked rather than vendored.
