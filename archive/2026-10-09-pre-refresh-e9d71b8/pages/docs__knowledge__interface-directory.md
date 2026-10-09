# Important interfaces, files and strings

> **Archive — not current operating instructions.** Historical documentation at [e9d71b843651](https://github.com/Protonmatter/wifi-hardware-time/commit/e9d71b84365122ff2640e240b20fc1dbb834388a). Relative links are rebased for reading. [Exact original bytes](../originals/docs__knowledge__interface-directory.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

This directory ranks useful starting points by what the evidence supports. Names help navigate source and binaries; they do not confer a stable API or authorize a hardware command. Use the full generated index for every authored reference, then return to the linked finding to understand its build, clock domain and qualification limit.

## Contents

- [Timing producers and private paths](#timing-producers-and-private-paths)
- [Vendor interfaces](#vendor-interfaces)
- [Files and package names](#files-and-package-names)
- [Interpretation terms](#interpretation-terms)

## Timing producers and private paths

| Name / token | Meaning and qualification | Read |
|---|---|---|
| `qcwlanhmt8380.sys`, `1.0.4374.1300` | Exact inspected ARM64 driver; offsets require its pinned SHA-256 | [Qualcomm](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/qualcomm.md) |
| `0x5012`, action `3`, action `4`, report `0x5005` | Selected TSF control/report path; response association and sampling remain unqualified | [Transport contract](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/qualcomm-minimal-transport-contract.md) |
| `0x169678`, `0x16aaf8`, `0x16ab60`, `0x18d540` | TSF null-barrier wrapper, barrier dispatcher and peer/vdev deletion queues | [Action-4 completion](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/action4-completion-and-report-contract.md) |
| `HTCSendPktsMultiple`, `HTCTrySend`, `HTCIssuePackets`, `0x1b9140`, `0x1b9400`, `0x1b7e38` | Endpoint admission can succeed before packet issue; no firmware sampling fence established | [Queue trace](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/action4-completion-and-report-contract.md#what-the-send-path-completes) |
| `DoSendCompletion`, `0x1b7690`, `0x1b40a0` | Endpoint completion callback and selected HIF send target; sampling meaning unqualified | [Completion boundary](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/action4-completion-and-report-contract.md) |
| `decode_tsf_report.py`, `reference-48`, `reference-60`, `0x18b` | Owned diagnostic TLV decoding; explicit reference schema and false live-clock gates | [Offline tools](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/action4-completion-and-report-contract.md#implemented-offline-tools) |
| `wmi_control_rx`, `0x168ce0`, `0x215928`, `0x216b00` | Original WMI event header/length, registration and selected TSF callback | [Connected ingress](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/tsf-event-ingress-and-owned-copy.md#the-connected-receive-path) |
| `WMI_CAPTUREH_EVENTID`, `0x1e003`, `0x1ddb90`, `0x1ddb50` | Separate beamforming callback/cache pointer getter; no owned TSF return | [Trace candidates](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/firmware-trace-return-candidates.md#captureh-is-a-separate-event) |
| `Data20.msc`, `25950`, `wlan_vdev_tsf_report`, `0x1d011`, `0x1b01a0`, `0x1b1128` | Fuller counter/identity definition, version-gated copied diagnostics and later formatter; no live record or application return qualified | [Firmware diagnostic producer](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/firmware-trace-return-candidates.md#the-fuller-firmware-diagnostic-report) |
| `0x98742004`, `0x122d58`, `qdss_trace_config_v1.cfg`, `qdss_trace_config_v2.cfg` | QDSS DMA controls and installed configuration; no live execution or timing-record schema | [QDSS control/configuration](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/firmware-trace-return-candidates.md) |
| `QMI_WLFW_QDSS_TRACE_SAVE_IND_V01`, `0x41`, `0x14b778`, `0x14e9c8`, `0x14f448` | Save indication, QMI chunk acquisition and file output; distinct from WMI event `0x5005` | [QDSS file route](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/firmware-trace-return-candidates.md#qdss-has-a-firmware-to-file-path) |
| `wmitlv_check_and_pad_tlvs`, `0x1ba4e0`, `0x1ba8b0` | Generic decoder and fixed-TLV padding copy; header retained, allocation size differs from received size | [Normalization](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/tsf-event-ingress-and-owned-copy.md#length-and-normalization) |
| `0x1bda9c`, `0x1bb558`, `0x1bb56c` | TSF cleanup table entry, allocated-slot check and wrapper release | [Callback lifetime](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/tsf-event-ingress-and-owned-copy.md#ownership-and-the-copy-point) |
| `inspect_tsf_ingress.py`, `EventSnapshot`, `event-wire` | File-only static inspector and owned original-event diagnostic form; no live source attestation | [Reproduction](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/tsf-event-ingress-and-owned-copy.md#reproduction-and-validation) |
| `HTCRxCompletionHandler`, `0x1f5f20`, `0x1f58b0`, `0x143218` | Transport header, receive callback and aggregate length; not a contiguity proof | [Transport boundary](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/tsf-event-ingress-and-owned-copy.md#upstream-transport-length-and-contiguity) |
| `0x169220`, `0x006ae0`, `+0x198` | WMI send completion and selected pooled-buffer reference/recycle path | [Return and ownership limits](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/tsf-event-ingress-and-owned-copy.md#existing-return-candidates) |
| `0x3975d8`, `0x4081a0`, `0x3975e8` | General command, filtered completion and event-history bases; separate contents | [History distinctions](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/tsf-event-ingress-and-owned-copy.md#existing-return-candidates) |
| `HtcEventSnapshot`, `htc-wire`, `--expected-endpoint` | Owned diagnostic transport envelope; explicit expected endpoint and exact lengths, with live attribution still false | [Owned software record](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/tsf-event-ingress-and-owned-copy.md#owned-software-record) |
| `hif_post_init`, `hif_start`, `0x1b3a98`, `0x1b4518`, `+0x950`, `+0x978`, `+0x988` | Pending callback block, active installation and receive callback | [HIF producer](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/hif-receive-buffer-producer.md#connected-producer-path) |
| `HIF_PCI_CE_recv_data`, `hif_completion_thread`, `0x1b17f0`, `0x1b2f18` | Receive queue writer and dispatcher; one buffer/count per completion | [Completion record](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/hif-receive-buffer-producer.md#completion-identity-and-byte-count) |
| `0x0067a0`, `0x006eb0`, `0x1b3b30` | Pool checkout/reset, conditional cache synchronization and receive replenishment | [Source geometry](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/hif-receive-buffer-producer.md#buffer-geometry-and-synchronization) |
| `0x3933f0`, `0x3934f0`, `0x1f2370`, `0x1f49a0` | CE operation tables and completion readers; live selection not inspected | [Descriptor-to-buffer association](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/hif-receive-buffer-producer.md#completion-identity-and-byte-count) |
| `0x1f4290` | CE descriptor history; no WMI payload ownership and no established QPC pair | [History limits](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/hif-receive-buffer-producer.md#why-the-copy-engine-history-is-insufficient) |
| `rb_publish`, `rb_begin_read`, `rb_read`, `rb_cancel`, `rb_close`, `rb_destroy` | Concurrent user-mode raw-response API; fixture/replay provenance, no installed driver ABI | [Broker contract](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/raw-event-response-broker.md) |
| `WHTR`, `RB_HEADER_BYTES`, `application_read_ticket`, `software_generation` | Pointer-free response format and host software identities; no firmware-token binding | [Response layout](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/raw-event-response-broker.md#response-format) |
| `WlanDeviceServiceCommand`, `Invoke-DeviceServiceControl.ps1`, `0x12a2a0` | One live fixed-pattern GET through the exact driver; no TSF/FTM event return or hardware sampling claim | [Live control](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/device-service-positive-control.md) |
| `wht_management_rx`, `0x1a8160`, `WMI_MGMT_RX_EVENT` | Selected management-frame reduction path; complete-event copy must precede cleanup | [Management producer](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/qualcomm-management-timing-producer.md) |
| `0x32e5d8`, `0x3958b8`, `AllocateCommonBufferWithBounds`, `WdfDmaEnablerWdmGetDmaAdapter` | Backing-allocator selector, framework DMA adapter and common-buffer operation; static, without live coherency qualification | [DMA backing contract](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/dma-backing-contract.md) |
| `hif_disable`, `0x196c90`, `0x1b57a0`, `0x1b5488`, `0x1b32d8` | PCI disable, DPC drain with ignored status, completion-reference polling and timeout | [Receive shutdown](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/receive-shutdown-contract.md) |
| `wht_packetlog_offload_write`, `0x220e90` | Packet-log input writer; copied payload has no established complete-management-event identity | [Producer trace](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/memory-ring/packetlog-producer-trace.md) |
| `wht_packetlog_reserve`, `wht_packetlog_copy`, `wht_ihv_request` | Reservation, selected reader and request-completion bridge | [Ghidra navigation](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/ghidra-workspace.md) |
| `HTT_T2H_MSG_TYPE_MLO_TIMESTAMP_OFFSET_IND`, `0x28`, `0x10c` | Firmware message/internal event and cache-writing lead; units and export are not qualified | [MLO cache](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/memory-ring/mlo-cache-and-symbol-search.md) |
| `t3_del`, `t4_del`, tag `0x2b` | Selected per-record FTM difference processing; names are not absolute-time proof | [Relationship trace](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/clock-models/clock-relationship-investigation.md) |
| `WDI_TLV_BSS_ENTRY_AGE_INFO`, `HostTimeStamp`, `ullHostTimestamp` | BSS host/system-time path, not radio receive-clock export | [Host-time origin](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/windows-bss-host-time.md) |
| `ullTimestamp`, `tsf_info`, `raw_frame` | Peer timestamp / cache-frame leads; keep peer and local clocks distinct | [BSS serializer](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/qualcomm-bss-serialization.md) |
| `CaptureInterfaceHardwareCrossTimestamp`, `OID_TIMESTAMP_GET_CROSSTIMESTAMP` | Documented sampling contract; no working Qualcomm hardware/QPC result established | [Windows path](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/windows-timestamps/windows-timestamp-path-followup.md) |
| `Observe-WifiDataPath.ps1`, `dumpcap`, `EN10MB`, `host_hiprec_unsynced` | Bounded capture and explicit elevation receipts; the observed timestamp options are host clocks | [Live packet baseline](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/acquisition/packet-capture-and-elevation.md) |

## Vendor interfaces

For the newly installed x86 QMSL 6.1.365.1, use the [current runtime map](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/qmsl-runtime-365.md), not the older 6.1.48.1 RVAs: V2 registration `0x107740`, setter `0x1313b0`, listener `0x135f60`, worker `0x129720`, payload transfer `0x155d20`, stop `0x129980`, and getter `0x1083b0` -> `0x111ae0`. These are image-relative virtual addresses (RVAs), not raw file offsets; no live timing operation is qualified.

| Call, field or string | Located behavior / limit |
|---|---|
| `Qualcomm.AtlasQutsRequest`, `IAtlasQutsRequest`, `IAtlasQutsSecurity` | QPST COM connection-management interfaces |
| `AddQpstConnection`, `RemoveQpstConnection`, `IsQpstConnectionExits` | Service/handle map operations in selected server routines |
| `IsUsingQUTS` | Selected 496 routine writes false; not a demonstrated detector |
| `Global\AtlasQutsRequestMemoryObject` | Coordination shared-memory name; not an established timing ring |
| `GetItemBuffer`, `GetItemSize`, `GetItemDLFBuffer` | QXDM owned-array candidate and related accessors; empty-result ambiguity and format transformation matter |
| `GetItemTimestamp`, `GetItemSpecificTimestamp` | QXDM store time versus target time with fallback |
| `getDeviceList`, `getProtocolList` | QUTS enumeration declarations; empty lists can also mean failure. No device enumeration invoked by the archive inspection |
| `ValidateDevice`, `QCDeviceControlFile`, `QCDeviceProtocol` | Native network discovery and protocol metadata. The current PCI Wi-Fi key lacks the control-file advertisement; see the [Ghidra gate trace](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/quts-discovery-gate.md) |
| `Discovered MHI Diag protocol`, `0x1a2d58`, `0x17fa18` | QCDM-description and MHI-parent predicates leading to DIAG-object construction; see [matched fields and limits](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/quts-mhi-route-validation.md) |
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
| QUTS `0x20ee28`, `0x231938`, `0x227280` | Register receiveData callback, admit retained buffers and insert the DIAG receive queue |
| QUTS `0x1357e0`, `0x136a48`, `0x146ce8` | HDLC/non-HDLC frame readers and retained escape state |
| QUTS `0x135090`, `0x134ac0` | CRC residue comparison and separate empty-payload predicate |
| QUTS `0x22cf48`, `0x1ef3c8`, `0x441830` | Stream cursor, copied decoded payload and retained incoming-packet queue item |
| Driver `WLANLIB`, `{9b4a1918-78c7-4148-8eb5-2e580f5ba530}` | Enabled interface attributed by exact-device enumeration and matching registration in the pinned Wi-Fi driver |
| Driver `0x436000`, `0x11c948`, `0x0293c0`, `0x0298c0` | WLANLIB registration, interface-state helper and IOCTL dispatch; no live operation sent |
| Driver `0x11bfb8`, `0x81802c04`, `0x11bd90` | Qmux query/pending notification and one-byte completion; not timing data |
| Driver `0x11d4c0`, `0xc3502406`, `0x437340` | ART2 command envelope and subcommand dispatcher, with a runtime state gate |
| Driver `0x11e840`, `0x220182`, `0x11fad0`, `0x33bde0` | iwpriv path into the existing named command table used by the bounded TSF probe |
| Driver `0x1a4ad8`, `0x1a4e10`, `0x1a4f80` | UTF attachment, segmented-event producer and consuming payload fetch |
| UTF context `+0x38240`, `+0x38248`, `+0x38250`, `+0x38259` | Payload pointer, published length, accumulated length and next-segment state; no qualified snapshot/epoch |
| ART2 subcommand `0x13`, adapter `+0x8948` | Four-byte overall error getter; bypasses the selected test-state gate but supplies no clock |
| `createDataQueue`, `getDataQueueItems`, `removeDataQueue` | QUTS diagnostic queue lifecycle with count/timeout retrieval |
| `sendRequestAsync`, `getResponseAsync`, `getAllResponsesAsync` | Service transaction association; request calls can affect hardware and were not executed |
| `RawService.initializeService`, `initializeServiceQmi`, `initializeServiceWithOptions`, `onAsyncResponse` | Existing protocol handle required; notification carries protocol/transaction handles, without event bytes. See [hardware handoff](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/complete-event-hardware-handoff.md) |
| `DiagPacket.Read`, `TBinaryProtocol.ReadBinary`, `TCompactProtocol.ReadBinary` | Located managed-byte allocation and deserialization path |
| `binaryPayload`, `errorCode`, `transactionId`, `sessionIndex`, `protocolIndex` | Bytes, status and distinct identity scopes |
| `timeStampData`, `hwTimeStampData`, `receiveTimeData`, `INT64_MIN` | DIAG/interpolated, QDSS and host time plus the DiagPacket missing-hardware-time sentinel |
| `Wlan_FwRttMeasurementRequest`, `Wlan_FwRttResponse` | Database definition leads; firmware/schema match not established |
| `QLIB_ConnectServer_UserDefinedTransport`, `QLIB_SendSync` | Older QMSL transport/association leads; they do not implement a device transport themselves |
| `QLIB_DIAG_GetNextPhoneLog`, `0x119d30`, `0x126ca0`, `0x136680` | QMSL 6.1.48.1 copy/pop path; no destination-capacity parameter and no qualified timeout bound. [Details](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/qmsl-diagnostic-queue.md) |
| `QLIB_DIAG_GetMultipleLogs`, `0x1322a0`, `0x1304e0` | Batch getter can modify logging masks; not passive retrieval |
| `QLIB_ConfigureCallBacks_V2`, `0x11e280`, `asyncFQMessageCB` | Original binary and optional JSON callback lead; copied application ownership, actual producer and teardown remain to qualify |
| `QC.QMSLPhone.LogMessage.getTimeStamp` | Display formatter discards 16 low bits; not the raw timestamp or a QPC conversion |
| `FTM_WLAN_TLV2_Create16`, selector `358`, `rtt_Data`, `rtt_Size` | Installed WLAN RTT method's QMSL builder/result names; not IOCTL numbers |
| `FTM_WLAN_TLV2_CreateQ5`, selector `20043` | Separate inherited RTT method with a narrowed converted result |
| `QDBRD_ReadUSB`, `QDBRD_ReadUSBCompletion`, `QDBDSP_IoStop` | QUD USB request/completion pattern and cancellation boundary |
| `IOCTL_QCDEV_GET_SERVICE_FILE`, `IOCTL_QCDEV_DPL_STATS` | QUD QMI service selection and USB statistics, not the Wi-Fi private protocol |

See [archive evidence](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/qualcomm-archive-transport-findings.md) and
[vendor WLAN methods](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/qualcomm-software-center-timing-leads.md).

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
See the [glossary](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/glossary.md) and [assumption ledger](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/knowledge/assumptions-and-corrections.md).

For the full authored-source directory, use the [reference index](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/knowledge/reference-index.md).
