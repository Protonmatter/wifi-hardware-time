# Timing and driver terms in plain language

Wi-Fi timing crosses several clocks, software layers and evidence types. This glossary explains the terms used throughout the research so that a fast response, precise-looking number or successful command is not mistaken for accurate time. Each distinction affects what an application can safely conclude from a timestamp.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** Current findings now include complete vendor package inventories, QUTS client ownership and a correction ledger. Historical acquisitions retain their original scope and limits. See [current findings](knowledge/current-findings.md).
<!-- /historical-context -->

## Contents

- [Clocks and measurements](#clocks-and-measurements)
- [Wi-Fi and packets](#wi-fi-and-packets)
- [Windows and driver interfaces](#windows-and-driver-interfaces)
- [Evidence and reliability](#evidence-and-reliability)

## Clocks and measurements

| Term | Meaning here |
|---|---|
| Timestamp | A number associated with a specified event. Its clock and event definition must also be known. |
| Clock domain | The counter, units and reference used to interpret a timestamp. Numbers from different domains cannot simply be subtracted. |
| Epoch | An identity for a period of assumed continuity. A reset or uncertain transition can end it; this is not necessarily a calendar date. |
| Tick / frequency | One counter increment / increments per second. The stored number of bits does not determine either rate or accuracy. |
| QPC | QueryPerformanceCounter, Windows' host interval-timing counter. It is not UTC and is not the Wi-Fi adapter's counter. |
| TSF | Timing Synchronization Function: Wi-Fi's timing mechanism and associated timer. An AP's TSF is not automatically UTC or the laptop's clock. |
| SoC / QTIMER | System-on-chip / a platform timer name. The reported field's exact units, source and relationship to QPC must be established for this build. |
| Cross timestamp | A related hardware-clock sample and host-clock samples, ideally with a known before/after sampling bracket. |
| Latch / simultaneous sample | Hardware captures a value at a particular instant / captures multiple values at the same established instant. A later software copy is not proof of either. |
| Offset / rate difference | How far two clocks are apart / how quickly that separation changes. |
| Affine model | A scale-and-offset conversion, `host = rate * counter + offset`. A fitted equation can still contain unknown bias. |
| Residual | Difference between data and a model prediction. Small residuals do not establish small error against real time. |
| Resolution / precision / accuracy | Smallest represented step / repeatability or spread / closeness to the intended reference. These are different properties. |
| Latency / jitter | Time taken to deliver or compute a result / variation in that delay. Neither necessarily describes hardware timestamp error. |
| Freshness / age | Whether a result is recent enough for a stated purpose / time since its defined observation or sampling point. |
| Holdover | Continuing an estimate without fresh reference samples. Error can grow with age and rate uncertainty. |
| Calibration / independent reference | Characterizing error against a known reference / a comparison source not derived from the quantity being tested. |
| Uncertainty / error bound | A stated measure or limit of possible error under explicit assumptions. Unknown terms cannot be replaced by zero. |
| p50 / p95 / p99 | Percentiles: half, 95% or 99% of measured values are at or below the reported value under the chosen method. |
| ms / us / ns / ps | Millisecond, microsecond, nanosecond, picosecond: 10^-3, 10^-6, 10^-9 and 10^-12 seconds. Small units do not imply equally small error. |
| UTC / PTP / PHC | Civil time reference / Precision Time Protocol for network synchronization / a PTP hardware clock interface. Their presence does not prove accuracy on this adapter. |

## Wi-Fi and packets

| Term | Meaning here |
|---|---|
| AP / SSID / BSSID | Access point / network name / identifier of a particular basic service set, usually represented by a MAC address. One network name can cover several AP radios. |
| TX / RX / RF | Transmit / receive / radio-frequency activity. A host send call and physical transmission are different events. |
| MAC / PHY | Medium-access control / physical radio layer. Timestamp meaning depends on where in these layers the event is defined. |
| Packet / frame / descriptor | Higher-level network data unit / link-layer transmitted unit / driver or device metadata describing data and status. A descriptor is not an on-air header. |
| PPDU / MPDU / MSDU | Physical-layer transmission unit / MAC frame / MAC service data unit. Aggregation can put several smaller units inside a larger transmission. |
| A-MPDU / A-MSDU | Forms of aggregation that combine several MAC frames or service data units. One timestamp may apply to a shared transmission. |
| ACK / retry | Acknowledgment that a frame was received / another transmission attempt. A logical packet can have multiple RF attempts. |
| FTM / RTT | Fine Timing Measurement, a Wi-Fi ranging procedure / round-trip time. Ranging success does not reveal clock offset without additional event data. |
| t1, t2, t3, t4 | Labels for four events in a two-way timing exchange. Always read the local definition of which clock and event each label uses. |
| Dialog token / burst / fragment | Exchange identifier / group of measurements / part of a larger response. All need correct association before records can be combined. |
| Roaming / reassociation | Moving association between AP radios / establishing an association again. A reconnect to the same BSSID is not proof of a roam. |
| vdev / link ID | Driver virtual-interface / radio-link identifier. It is not necessarily a unique request or exchange identifier. |
| RSSI / MCS / NSS / GI | Received signal strength / modulation and coding selection / spatial-stream count / guard interval. Radio metadata, not clock quality by itself. |

## Windows and driver interfaces

| Term | Meaning here |
|---|---|
| QUTS / QXDM / QPST | Qualcomm communication service / diagnostic application / support tools. A product being installed does not prove an adapter-specific timing path. |
| QMSL / QSPR / QDART | Qualcomm library / test framework / test-tool suite. Match their actual assembly and transport dependencies. |
| QDSS / QMI | Qualcomm diagnostic trace transport / service-message interface. Neither name identifies a Wi-Fi clock domain by itself. |
| QIK / QCC | The inspected package wrapper and block-container format. Static extraction reads files without running an installer. |
| COM / IDL / type library | Windows component interface / interface-description source / compiled interface metadata. Reading a type library does not invoke its server. |
| Thrift / deserialization | A client-service protocol / decoding its bytes into client objects. The inspected readers allocate application byte arrays. |
| SAFEARRAY / owned bytes | A COM array representation / storage retained by the application independently of a temporary driver pointer. This does not prove producer consistency. |
| Interpolation / fallback / sentinel | A derived value / replacement value / marker for an unavailable value. Check each schema before admitting a hardware sample. |
| RSDS / PDB | Native debug identity record / program database containing symbols. A PDB must match the binary identity, not merely its filename. |
| API / ABI | Software interface / binary-level calling and data-layout rules. An exported function is not necessarily a supported public API. |
| Driver / firmware / NIC | Host software controlling hardware / software running on the device / network interface controller. Completion at one layer may precede work at another. |
| NDIS / miniport / filter | Windows networking framework / adapter driver role / intermediate network driver. An observed failure may have been propagated from another layer. |
| OID / IOCTL | Network object query/control identifier / general device-control request. A successful request return does not prove a hardware sample was taken. |
| WDI / WiFiCx / WMI | Windows wireless driver interfaces / Wi-Fi class extension / here, Qualcomm's Wireless Module Interface to firmware. This WMI is not Windows Management Instrumentation. |
| ETW / ETL | Event Tracing for Windows / a saved trace file. Its event time may describe logging, not the radio event. |
| NBL / socket ancillary data | NET_BUFFER_LIST, a Windows networking buffer structure / metadata delivered beside socket data. Both can carry timestamps if a path supports them. |
| DLL / SYS / export | User-mode library / driver binary / callable symbol published by a binary. None alone establishes a qualified contract. |
| ARM64 / PE / RVA | Processor instruction architecture / Windows binary format / address relative to an image's base. A documented RVA is an inspection location, not a safe runtime call. |
| TLV | Type/tag, length and value record structure. Checking the tag alone does not validate the whole record. |
| UAC / privilege | Windows elevation prompt / permission level. Elevation grants access; it does not establish operation safety or correctness. |
| DMA / PCIe / USB | Direct memory access / internal peripheral transport / Universal Serial Bus. Their buffering and delivery behavior can affect observations. |
| RDDM / MHI / PLDR | Device diagnostic-dump mode / modem-host interface transport / platform-level device reset. These are diagnostic or recovery paths, not automatically safe getters. |

## Evidence and reliability

| Term | Meaning here |
|---|---|
| Ring buffer / wrap | A fixed-size buffer reused in a circle / returning to its start. Old records may be overwritten. |
| Reservation / commit | Claiming buffer space / publishing that its content is complete. Advancing the first does not prove the second. |
| Torn copy / quiescence | A copy mixing incomplete updates / an established period without writers. Repeating a copy does not establish quiescence. |
| Request identity / provenance | How a response is tied to its initiating operation / where data and tools came from. Nearby timestamps are weaker than a propagated unique identifier. |
| Hash / manifest / source pin | Content fingerprint / inventory of acquisition inputs / a required exact input hash. Matching hashes identify bytes, not the truth of a measurement. |
| Fixture / replay / synthetic | Test input / reanalysis of saved data / constructed data. Distinguish these from a new hardware experiment. |
| Trace loss / drain | Missing trace records / completion and retrieval of pending work. Zero reported loss does not prove every producer emitted a record. |
| Fail closed / quarantine | Reject when required evidence is missing / retain a blocked state after ambiguity or failure. Restarting a process does not establish firmware drain. |
| Qualification / CI | Evidence supporting a scoped capability / automated software checks. Passing CI is not live hardware qualification. |

Return to the [reading guide](README.md) to choose a topic. Reports also define
the terms most important to their own conclusions; the glossary is a reference,
not a prerequisite for understanding each document's opening synopsis.
