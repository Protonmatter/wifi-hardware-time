# Wi-Fi Hardware Time

Research into exposing Wi-Fi hardware clocks, packet timestamps, and clock correlation through a reusable API.

The initial investigation covers the **ALFA AWUS036AXML / MediaTek MT7921AUN** on Linux and Windows, and a **Qualcomm FastConnect 7800** Windows ARM64 driver. It includes source-backed findings, narrow diagnostic tools, and explicit qualification limits.

**Status: research and diagnostic prototypes. No end-to-end PTP synchronization or timing-accuracy claim has been validated.**

## What has been established

| Backend | Evidence | Remaining gap |
|---|---|---|
| Linux mt76 / MT7921 USB | TSF read/write callbacks, RX descriptor timing, USB TX-status processing, defined TX timestamp field | A reliable error-reporting snapshot API, TX semantics, reset epochs, PHC/socket timestamp integration |
| Windows MediaTek 1.0.0.119 x64 | Static private register read/write and firmware response paths | Live hardware qualification; standard NDIS timestamp exposure unproven |
| Windows Qualcomm 1.0.4374.1300 ARM64 | Live private host getters and one firmware TSF report captured through ETW | IOCTL does not return TSF; repeated sampling, hardware cross-timestamps, and accuracy remain unqualified |

On the inspected Qualcomm system, standard timestamp-capability and cross-timestamp APIs returned Win32 **23 / ERROR_CRC**. Failed queries are not interpreted as capability absence. Cached beacon timestamps and an FTM responder advertisement were observed; neither establishes local hardware packet timestamp accuracy.

## Contents

- [ALFA / MediaTek investigation](docs/axml.md)
- [Qualcomm private timing path](docs/qualcomm.md)
- [Validation ledger and limits](docs/validation.md)
- [Proposed API boundary](docs/api-direction.md)
- [Operations and reproducibility](docs/OPERATIONS.md)
- [TSF capture and offline series analysis](docs/OPERATIONS.md#capture-and-analyze-a-tsf-series)
- [Pinned sources and provenance](docs/sources.md)

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

It discovers the actual active driver, enforces an exact binary hash and command layout, and builds the request without opening the private device. `--execute` explicitly enables one private request. Read the [operations guide](docs/OPERATIONS.md) before using that option. A TSF read can submit a firmware action even though it does not enable automatic reporting or reset a counter.

## Publication boundary

This repository contains authored research notes and tools. Proprietary driver installers, SYS/DLL files, firmware, raw disassembly, ETL/packet captures, and endpoint-specific identifiers are excluded. Driver hashes identify the inspected artifacts; they do not grant redistribution rights. Obtain vendor software from its legitimate source.

The initial import does not select a distribution license. Third-party sources remain governed by their respective licenses; they are linked rather than vendored.
