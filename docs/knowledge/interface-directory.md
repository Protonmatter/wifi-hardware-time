# Important interfaces, files and strings

This directory ranks useful starting points by what the evidence supports. Names help navigate source and binaries; they do not confer a stable API or authorize a hardware command. Use the full generated index for every authored reference, then return to the linked finding to understand its build, clock domain and qualification limit.

## Contents

- [Timing producers and private paths](#timing-producers-and-private-paths)
- [Vendor interfaces](#vendor-interfaces)
- [Files and package names](#files-and-package-names)
- [Interpretation terms](#interpretation-terms)

## Timing producers and private paths

| Name / token | Meaning and qualification | Read |
|---|---|---|
| `qcwlanhmt8380.sys`, `1.0.4374.1300` | Exact inspected ARM64 driver; offsets require its pinned SHA-256 | [Qualcomm](../adapters/qualcomm.md) |
| `0x5012`, action `3`, action `4`, report `0x5005` | Selected TSF control/report path; response association and sampling remain unqualified | [Transport contract](../adapters/qualcomm-minimal-transport-contract.md) |
| `wht_management_rx`, `0x1a8160`, `WMI_MGMT_RX_EVENT` | Selected management-frame reduction path; complete-event copy must precede cleanup | [Management producer](../adapters/qualcomm-management-timing-producer.md) |
| `wht_packetlog_offload_write`, `0x220e90` | Packet-log input writer; copied payload has no established complete-management-event identity | [Producer trace](../memory-ring/packetlog-producer-trace.md) |
| `wht_packetlog_reserve`, `wht_packetlog_copy`, `wht_ihv_request` | Reservation, selected reader and request-completion bridge | [Ghidra navigation](../adapters/ghidra-workspace.md) |
| `HTT_T2H_MSG_TYPE_MLO_TIMESTAMP_OFFSET_IND`, `0x28`, `0x10c` | Firmware message/internal event and cache-writing lead; units and export are not qualified | [MLO cache](../memory-ring/mlo-cache-and-symbol-search.md) |
| `t3_del`, `t4_del`, tag `0x2b` | Selected per-record FTM difference processing; names are not absolute-time proof | [Relationship trace](../clock-models/clock-relationship-investigation.md) |
| `WDI_TLV_BSS_ENTRY_AGE_INFO`, `HostTimeStamp`, `ullHostTimestamp` | BSS host/system-time path, not radio receive-clock export | [Host-time origin](../adapters/windows-bss-host-time.md) |
| `ullTimestamp`, `tsf_info`, `raw_frame` | Peer timestamp / cache-frame leads; keep peer and local clocks distinct | [BSS serializer](../adapters/qualcomm-bss-serialization.md) |
| `CaptureInterfaceHardwareCrossTimestamp`, `OID_TIMESTAMP_GET_CROSSTIMESTAMP` | Documented sampling contract; no working Qualcomm hardware/QPC result established | [Windows path](../windows-timestamps/windows-timestamp-path-followup.md) |

## Vendor interfaces

| Call, field or string | Located behavior / limit |
|---|---|
| `Qualcomm.AtlasQutsRequest`, `IAtlasQutsRequest`, `IAtlasQutsSecurity` | QPST COM connection-management interfaces |
| `AddQpstConnection`, `RemoveQpstConnection`, `IsQpstConnectionExits` | Service/handle map operations in selected server routines |
| `IsUsingQUTS` | Selected 496 routine writes false; not a demonstrated detector |
| `Global\AtlasQutsRequestMemoryObject` | Coordination shared-memory name; not an established timing ring |
| `GetItemBuffer`, `GetItemSize`, `GetItemDLFBuffer` | QXDM owned-array candidate and related accessors; empty-result ambiguity and format transformation matter |
| `GetItemTimestamp`, `GetItemSpecificTimestamp` | QXDM store time versus target time with fallback |
| `getDeviceList`, `getProtocolList` | QUTS enumeration declarations; empty lists can also mean failure. No device enumeration invoked by the archive inspection |
| `ValidateDevice`, `QCDeviceControlFile`, `QCDeviceProtocol` | Native network discovery and protocol metadata. The current PCI Wi-Fi key lacks the control-file advertisement; see the [Ghidra gate trace](../adapters/quts-discovery-gate.md) |
| `Discovered MHI Diag protocol`, `0x1a2d58`, `0x17fa18` | QCDM-description and MHI-parent predicates leading to DIAG-object construction; see [matched fields and limits](../adapters/quts-mhi-route-validation.md) |
| `0x1ef198`, `0x313b38`, `0x27f970` | DIAG connection factory, derived constructor and base constructor; FastConnect endpoint association remains unqualified |
| `0x0b2cd0`, `0x0b5168`, `0x0b5ddc` | Expected QUTS return RVAs observed together in 12 matched stacks from the qualified registry capture |
| `0x27ad70`, `0x277e40`, protocol `+0x118` | CommonIo getter, base constructor and retained transport reference |
| `0x17efc0`, `0x17ef18`, `0x17ee80`, `0x17ede8` | Usb, QmiIo, Ethernet and CommandIo factories; distinct transport implementations |
| `0x2aa050`, `0x0b6920`, entry `+0x894` | Selected Usb open, QcDevice endpoint open and stored endpoint path; static, not a demonstrated Wi-Fi open |
| `0x2ab358`, `0x0b7500` | Selected Usb send and QcDevice WriteFile path; not a receive getter |
| `0x0b3b58`, stores `0x0b5640`–`0x0b5748` | ScanDevices constructs endpoint at entry `+0x894` from validated discovery data |
| `0x0b0830`, descriptor `+0x30` | Device-list reconciliation publishes a pointer to entry-owned endpoint text; copying the wrapper does not copy its strings |
| `0x0b71c0`, `0x2a9b78` | ReadFromDevice and communication RxWorker; up to 128 KiB per read, with actual byte count |
| `0x2a7cd0`, `0x137760` | Copy portions of at most 16 KiB into owned Device::Buffer objects before callbacks |
| `0x2aae30`, `0x2ac3d8` | Transport callback-pair registration and propagation to the worker under its lock |
| `0x2a89a8`, `0x2a8d60`, `0x0b7038` | Selected close sequence, CancelIoEx request and CloseDevice; not a bounded live cancellation result |
| `0x100e90`, `0x106e30`, `0x8000000000000000` | Default wait sentinel constructor, waitForStop and selected unlimited wait; not a host timestamp sample |
| `0x22d038`, `0x1e9848` | DIAG readPackets and NonHdlc FrameStream status check; concrete framing targets, not a qualified Wi-Fi schema |
| `createDataQueue`, `getDataQueueItems`, `removeDataQueue` | QUTS diagnostic queue lifecycle with count/timeout retrieval |
| `sendRequestAsync`, `getResponseAsync`, `getAllResponsesAsync` | Service transaction association; request calls can affect hardware and were not executed |
| `DiagPacket.Read`, `TBinaryProtocol.ReadBinary`, `TCompactProtocol.ReadBinary` | Located managed-byte allocation and deserialization path |
| `binaryPayload`, `errorCode`, `transactionId`, `sessionIndex`, `protocolIndex` | Bytes, status and distinct identity scopes |
| `timeStampData`, `hwTimeStampData`, `receiveTimeData`, `INT64_MIN` | DIAG/interpolated, QDSS and host time plus the DiagPacket missing-hardware-time sentinel |
| `Wlan_FwRttMeasurementRequest`, `Wlan_FwRttResponse` | Database definition leads; firmware/schema match not established |
| `QLIB_ConnectServer_UserDefinedTransport`, `QLIB_SendSync` | Older QMSL transport/association leads; they do not implement a device transport themselves |
| `FTM_WLAN_TLV2_Create16`, selector `358`, `rtt_Data`, `rtt_Size` | Installed WLAN RTT method's QMSL builder/result names; not IOCTL numbers |
| `FTM_WLAN_TLV2_CreateQ5`, selector `20043` | Separate inherited RTT method with a narrowed converted result |
| `QDBRD_ReadUSB`, `QDBRD_ReadUSBCompletion`, `QDBDSP_IoStop` | QUD USB request/completion pattern and cancellation boundary |
| `IOCTL_QCDEV_GET_SERVICE_FILE`, `IOCTL_QCDEV_DPL_STATS` | QUD QMI service selection and USB statistics, not the Wi-Fi private protocol |

See [archive evidence](../adapters/qualcomm-archive-transport-findings.md) and
[vendor WLAN methods](../adapters/qualcomm-software-center-timing-leads.md).

## Files and package names

- `QPST.2.7.496.zip`, `QPST_MergeModule.msm`, `QPST 2.7.msi`, `QPSTServer.exe`,
  `QpstMarshal.dll`, `SerialPortLib.dll`: separate containers and implementations.
- `QXDM.4.0.450.2.Windows-x86.7z`, `qxdm.idl`, `QXDM.tlb`, `ExtConnectivity.db`,
  `ExtDiag.db`, `ConnectivityModule.dll`: application interfaces and definition data.
- `QUD_Source_1.00.94.2.zip`, `QDBMAIN.h`, `QDBRD.c`, `QDBWT.c`, `QDBPNP.c`,
  `MPIOC.c`: USB/WWAN source with specific completion and teardown concerns.
- `QUTSService.exe`, `QUTSClient_csharp.dll`, `Thrift.dll`, `Common.thrift`,
  `DiagService.thrift`, `DeviceManager.thrift`: current installed transport/client leads.
- `QC.CTE.WLANTestSuite.dll`, `QC.QMSLFastConnect`, `QTMDotNetKernelInterface`,
  `QMSL_WLAN_Transport.dll`, `QMSL_MSVC10R.lib`: distinguish installed assembly,
  missing runtime requirements and an import-only library.

## Interpretation terms

`clock_id`, `clock_epoch`, `QPC`, `TSF`, `SoC`, `PPDU`, `FTM`, `RTT`, `WMI`,
`HTT`, `QDSS`, `QUTS`, `QMI`, `QMSL`, `WDF`, `IOCTL`, `RSDS`, `PDB`,
`owned bytes`, `freshness`, `quarantine`, `reference instant`, `interpolation`,
`resolution`, `accuracy` and `calibration` are not interchangeable concepts.
See the [glossary](../glossary.md) and [assumption ledger](assumptions-and-corrections.md).

For the full authored-source directory, use the [reference index](reference-index.md).
