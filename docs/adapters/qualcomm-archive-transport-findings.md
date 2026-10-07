# Qualcomm archive and installed transport findings

Static inspection recovered the QPST connection interfaces, QXDM's binary-buffer API and WLAN timing definitions, and a locally present QUTS client that allocates application-owned packet bytes. These are useful transport and schema findings. The missing connection is still specific: show that this laptop's Wi-Fi timing producer delivers the required event through one of those interfaces.

## Contents

- [Scope and provenance](#scope-and-provenance)
- [QPST: what the QUTS names implement](#qpst-what-the-quts-names-implement)
- [QXDM: complete declared payload inventory](#qxdm-complete-declared-payload-inventory)
- [QUD: request ownership and completion](#qud-request-ownership-and-completion)
- [Installed QUTS: a stronger application boundary](#installed-quts-a-stronger-application-boundary)
- [Matching the current WLAN stack](#matching-the-current-wlan-stack)
- [What can move downstream](#what-can-move-downstream)
- [Reproduction and validation](#reproduction-and-validation)
- [Glossary](#glossary)

## Scope and provenance

Snapshot: **2026-10-04**. Sources were downloaded from the listed mirror and read
as files. No vendor installer, COM server, vendor assembly or device command was
executed. Windows Installer database queries used read-only mode; COM type-library
inspection used an extracted `.tlb` with `REGKIND_NONE`, which disables
[type-library registration](https://learn.microsoft.com/en-us/windows/win32/api/oleauto/nf-oleauto-loadtypelibex).

| Download | SHA-256 |
|---|---|
| [QPST.2.7.496.zip](https://mirrors.lolinet.com/software/windows/Qualcomm/QPST/QPST.2.7.496.zip) | `a96187427241ea6d5ed777f08384584515cc8df2d6bd97f35e8ee04d0cdf1568` |
| [QXDM.4.0.450.2.Windows-x86.7z](https://mirrors.lolinet.com/software/windows/Qualcomm/QXDM/QXDM.4.0.450.2.Windows-x86.7z) | `aecbbba1f825eac5660b4fcd25623b4f259ac4304a8fcbd7049d68167948f866` |
| [QUD_Source_1.00.94.2.zip](https://mirrors.lolinet.com/software/windows/Qualcomm/QPST/QUD_Source_1.00.94.2.zip) | `14d6f0d9ac978187fe10f9305ac67664a85d86207a78e77e97137ac7c2588da3` |

Hashes establish which bytes were inspected. Publisher signatures were not
validated in this original static pass. The subsequent
[qualification audit](../evidence/qualification-audit-2026-10-04.md#publisher-signature-verification)
records selected signed and unsigned components separately. Raw packages, schemas, database contents, proprietary decompilation
and source copies stay under ignored `artifacts/lolinet-static-2026-10-04/`.
No patched package was used.

## QPST: what the QUTS names implement

The actual nesting is:

```text
QPST ZIP
  -> Qualcomm setup wrapper
     -> BIN/103 resource: InstallShield launcher
        -> ISSetupStream: QPST 2.7.msi
           -> Data1.cab: 154 files

Separate ZIP member: QPST_MergeModule.msm -> older reusable component
```

Arrows mean containment and static extraction, not installer execution.
The InstallShield stream was decoded and its zlib stream reached its end with
no unused bytes. All 154 MSI File-table entries matched cabinet members and
declared sizes. The standalone merge module reports QPSTServer **2.7.0.495**;
the nested MSI contains QPSTServer **2.7.0.496**. The earlier manifest therefore
did not describe the complete installer payload.

| Component | Architecture / file version | Established role |
|---|---|---|
| `QPSTServer.exe` | Native/mixed PE x86, `2.7.0.496` | Local COM server registered by the package for `Qualcomm.AtlasQutsRequest` |
| `QpstMarshal.dll` | Native x86, `2.7.0.496` | COM/RPC proxy component; exports standard proxy entry points including `GetProxyDllInfo` |
| `SerialPortLib.dll` | Native x86, `2.7.0.496` | Separate transport-related component; not evidence of a WCN7850 timing endpoint |
| `GobiConnectionMgmt.dll` | Native x86, `3.0.6.0` | Additional connection-management component; not a FastConnect runtime substitute |

The MSI Registry table maps CLSID
`{377702D0-D7CE-41FA-A997-41A5A1308419}` to `bin\QPSTServer.exe`.
Its extracted type library declares:

- `IAtlasQutsRequest`: `AddQpstConnection(serviceName, protocolHandle)`,
  `RemoveQpstConnection(serviceName)` and `IsUsingQUTS(...)`.
- `IAtlasQutsSecurity`: `IsQpstConnectionExits(serviceName, protocolHandle, ...)`.
  `Exits` is the spelling in this interface.
- The interfaces carry connection-management arguments, not timestamp buffers.

Selected Ghidra traces on the **496** server resolve the named routines to these
RVAs (offsets from image base `0x400000`):

| Routine identified by its diagnostic string | RVA | Selected behavior |
|---|---|---|
| `AddQpstConnection` | `0x215330` | Opens the named shared-memory object, uses a critical section and updates a service/64-bit-handle map |
| `RemoveQpstConnection` | `0x215930` | Removes a matching map entry and invokes the update helper |
| `IsQpstConnectionExits` | `0x2157c0` | Looks up a service and compares the two words of its stored handle under a critical section |
| `IsUsingQUTS` | `0x215900` | The selected function checks the output pointer, writes zero and returns success; it is not a demonstrated live QUTS detector |

`QPSTServer.exe` SHA-256:
`14c4575859dc92200cd22d5c9f4c22a4d626d76f9ed837908c1d010296eae4e0`.
Whole-program Ghidra analysis hit its 180-second limit. A subsequent bounded,
no-analysis pass resolved seven selected string references and decompiled their
containing routines. This supports the listed paths, not an exhaustive call graph.

**Practical result:** these are real callable COM interface definitions with a
located server implementation. Their inspected purpose is connection coordination.
The shared-memory name is not evidence of a packet/timestamp stream.

## QXDM: complete declared payload inventory

The previously failing download succeeded. Its EXE is a managed **QIK 1.0.96.4**
wrapper containing a QCC package. The wrapper's IL and field layouts were read
without loading it. A separate file-only helper decoded its blocks; no vendor
deserializer, license flow or installer was invoked.

- Main package: **333 files**, **19 directory entries**, and 335 QCC blocks
  including metadata and index.
- All **15 declared embedded packages** were inspected, plus their one embedded
  QIKTool package: **17 QCC containers**, **591 blocks**, **557 file entries**.
- Every extracted block's size and hash was checked. Every container index
  matched the decoded block offsets. Every declared file matched a data block.
- The 557 entries include **130 PE files**. These are entries across packages,
  not necessarily unique binaries. Architecture, version-resource presence,
  imports, exports and hashes were recorded for each.
- No file named for QMSL FastConnect, a QUTS runtime or a native `.pdb` was found
  in this declared QIK payload tree. This excludes separately acquired dependencies.
- Microsoft prerequisite installers were inventoried as files; their internal
  redistributable payloads were not recursively unpacked.

| Candidate | Architecture / version | Why it matters |
|---|---|---|
| `QXDM.exe` | Native x86, file version `4.0.450.0`; enclosing package `4.0.450.2` | Implements the diagnostic application and its automation surface |
| `qxdm.idl`, `QXDM.tlb` | Interface descriptions, not executable code | Declare item-buffer and timestamp accessors |
| `Interop.QXDMLib.dll` | Managed PE I386, file version `1.0.0.0` | Managed COM interop surface; PE machine alone does not establish managed bitness |
| `ConnectivityModule.dll` | Native x86; no version resource found | Exports display/workspace registration methods; not a demonstrated device transport |
| `ExtConnectivity.db` | Non-PE data; container package `1.0.59.1` | Contains WLAN RTT and TSF-related diagnostic definition text |
| `ExtDiag.db` | Non-PE data; container package `1.0.59.1` | Additional diagnostic definitions; not itself a callable library |
| `QXDMUserGuide.pdf` | Bundled guide `80-V1241-25 C`, 84 pages | Explains timestamp fallback and buffer-return ambiguity |

### Application buffer contract

`qxdm.idl:462-486` declares item type, processor ID, subscription ID, timestamp
accessors, `GetItemSize`, `GetItemBuffer` and `GetItemDLFBuffer`.
`GetItemBuffer` returns `SAFEARRAY(BYTE)`: a marshaled byte-array return candidate,
rather than a kernel pointer. Live copying, item retention and concurrent store
changes were not tested.

The bundled guide, pages 74-76, adds important limits:

- The generic timestamp is assigned when the item enters QXDM's item store.
- A target-specific timestamp accessor can return the generic timestamp when
  the item has no target-assigned timestamp. Successful retrieval is insufficient
  evidence of a hardware timestamp.
- The buffer-header option chooses between QXDM's full item and its payload.
  It does not promise the original WMI transport envelope.
- An empty returned array can mean either an error or a valid empty payload.
- The DLF accessor transforms the record to a legacy log-file representation.

### WLAN timing definitions

Bounded printable-string inspection of `ExtConnectivity.db` located definitions
named `Wlan_FwRttMeasurementRequest`, `Wlan_FwRttResponse` and WLAN RTT event names.
Their surrounding text describes request ID, token/fragment information, AP
address, burst index, status, measurement completion and timing units in
picoseconds. Separate event descriptions name MAC/vdev identity and request and
callback TSF values.

These are **schema leads**, not decoded live records. The database format and
field-to-byte layout were not fully reconstructed. One timing description says
`T3-T3`; it must not silently be corrected to `T3-T2`. Absolute event values,
meaningful widths, clock selection and applicability to this firmware remain open.

## QUD: request ownership and completion

The selected source is a **USB driver stack**. Its QDSS function driver exposes
interface GUID `{E093662A-FF18-4579-8681-506E9F561D3D}` and file suffixes
`\TRACE`, `\DEBUG`, and `\DPL` (`qdss/QDBMAIN.h`, `QDBDEV.h`, `QDBDEV.c`).

```text
Application read buffer
  -> WDF read request and request-owned memory
  -> selected USB IN pipe
  -> USB completion supplies transferred byte count
  -> original request completes to the application
```

This is a transport path. An application read is not automatically associated
with a previously transmitted firmware command, frame or clock sample.

- `QDBRD_ReadUSB` retrieves the request's output-memory object and formats the
  USB read against it. It retains the memory object in request context.
- `QDBRD_ReadUSBCompletion` takes the USB completion's byte count, sets the
  request information on success and completes the original request.
- The debug write path similarly uses request-owned input memory and USB completion.
- `QDBDSP_IoDeviceControl` handles buffered statistics and parent/device-ID
  requests. Those IOCTLs do not return Wi-Fi timing events.
- `QDBDSP_IoStop` requests cancellation on purge or acknowledges suspension.
  Cancellation initiation does not itself prove that a firmware response drained.
- `QDBRD_PipeDrainStop` clears a resubmission flag. Its explicit cancellation
  loop is commented out; a separate completion/wait path tracks outstanding work.
- The NDIS control path's `IOCTL_QCDEV_GET_SERVICE_FILE` accepts a QMI service
  type, obtains a client and returns a service-file name. It is not the installed
  Wi-Fi miniport's private TSF protocol. The NDIS source also contains explicit
  wireless-WAN selection (`ndis/MPINI.c`).

**Source concerns before reuse:**

| Priority | Source / symbol | Concern and required validation |
|---|---|---|
| P2 | `qdss/QDBRD.c:345`, `QDBRD_ReadUSB` | The immediate `WdfRequestSend == FALSE` branch decrements a counter but does not visibly complete the original request. Fault-inject this branch and require exactly one completion before adopting the pattern. |
| P2 | `qdss/QDBWT.c:211`, `QDBWT_WriteUSB` | The analogous immediate-send failure branch logs status without an explicit completion. Require the same failure-path test. |
| P2 | `qdss/QDBPNP.c:446`, `QDBPNP_WaitForDrainToStop` | A loop retries a timed wait while work remains, without an overall deadline. A bounded exporter needs explicit teardown timeout and terminal-state handling. |

These are static findings in the inspected source, not reproduced failures of
an installed QUD driver. No third-party source was modified. Its completion
pattern is useful design evidence; it is not qualified as a drop-in exporter.

## Installed QUTS: a stronger application boundary

A fresh file inventory found QUTS under the vendor installation. This supersedes
the earlier absence observation for these paths. It does not establish how or
when the files were installed, whether the service is operational, or device access.

| File | Current evidence |
|---|---|
| `QUTSService.exe` | Native ARM64; no PE version resource found; SHA-256 `30dc1fac9c9fb7a5672fb665daf33f72c8bc3456fa545bd169c7ae77eb4863b6` |
| `QUTSClient_csharp.dll` | Assembly `1.0.0.0`, .NET Framework 4.5, I386/ILOnly without Requires32Bit; SHA-256 `085ce63b9d661e206ae97e81f249bb71b5099982c4b67013595ee63c62a9d059` |
| `Thrift.dll` | File version `0.10.0.1`; SHA-256 `85e3d1499f4d3c881a689056d1ada9b2d1829b785e245920cf1fa29cb4028353` |
| `Common.thrift` | Packet schema; SHA-256 `6a48a9d153d485e2d6cb62bb8737a6454beb3bf27ebb46f47b5b4c0feb8d5d06` |
| `DiagService.thrift` | Query/queue interfaces; SHA-256 `bc9d9251594ee03fb95e7e4300fd8606234e900685b11c0c6a6498fc2e696c70` |

The local IDLs declare device/protocol enumeration, queue creation/retrieval and
asynchronous request/response retrieval. `getDataQueueItems` returns
`list<DiagPacket>` with a requested count and timeout. `getResponseAsync` uses a
transaction ID and consumes a successfully retrieved response; its comments
restrict the supported return flags. These contracts must not be treated as
equivalent to the richer queue-return configuration.

### A located owned-byte return pattern

File-only IL inspection established:

```text
Serialized diagnostic response
  -> Common.DiagPacket.Read
  -> Thrift TProtocol.ReadBinary
  -> concrete binary/compact reader allocates byte[] and calls ReadAll
  -> packet BinaryPayload property retains that array
```

This is substantive **static client-ownership evidence**. It removes the need
for this client path to retain a driver-ring pointer. It does not prove server-side
snapshot consistency or connect the response to the laptop's timing producer.

### Keep the timestamp fields separate

`Common.thrift:686-781` describes optional fields. Check `errorCode`, field
presence and the requested return configuration before using them.

| Field | Stated meaning | Required restriction |
|---|---|---|
| `binaryPayload` | Diagnostic bytes starting at the command code | Validate that record's schema; it is not promised to be an intact WMI event |
| `timeStampData` | DIAG-assigned time for selected packet types; interpolated for others | Reject interpolation as a hardware sample; 100 ns representation is not 100 ns accuracy |
| `hwTimeStampData` | QDSS-assigned time, represented in 100 ns ticks | For `DiagPacket`, reject sentinel `INT64_MIN`; QDSS time is not automatically TSF or PPDU time |
| `receiveTimeData` | Time QUTS received the packet | A host delivery observation, not a hardware sampling bracket |
| `transactionId` | Request transaction association where available | Do not equate it with a firmware token or unsolicited event identity without proof |
| `sessionIndex`, `protocolIndex` | Positions in the service's packet streams | Not firmware generation counters or proof of lossless capture |
| Processor / QDSS source IDs | Diagnostic source identity | Not automatically a Wi-Fi link's clock ID |

The IDL's FILETIME comments say 1600. Microsoft's
[FILETIME contract](https://learn.microsoft.com/en-us/windows/win32/api/minwinbase/ns-minwinbase-filetime)
uses **1601-01-01 UTC**. Treat the local comment as a documentation inconsistency;
verify conversion against observed values before accepting absolute time.
Other packet structures use different missing-time sentinels; the rule above is
specific to `DiagPacket`.

Health-report configuration exists, including a WLAN subsystem selection.
Its reset/timer operations would change collection state and were not invoked.
No per-record firmware epoch or end-to-end loss guarantee has been established.

## Matching the current WLAN stack

- The active Wi-Fi interface was **Up**, driver **1.0.4374.1300**, enumerated on
  **PCI**. The inspected QUD path is USB; no bridge between them was established.
- Installed `qcwlanhmt8380.sys` still hashes to
  `ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`.
- Installed `QC.CTE.WLANTestSuite.dll` is assembly **2.0.79.1**, SHA-256
  `33a982738130e42164ae9481e5cad9c0d4a316e48779a5c7d3c534718345c19f`.
  It references **QC.QMSLFastConnect 6.1.360.1** and requires a 32-bit managed host.
- The earlier 2.0.81.1 / 6.1.364.1 pair remains a historical snapshot, not the
  current dependency requirement. The separate QMSL-QCNTool import library does
  not implement either dependency.
- The bounded current search in the Qualcomm installation roots still did not
  locate QMSL FastConnect, QMSL_WLAN_Transport or QTMDotNetKernelInterface DLLs.
  The newly located QUTS client is a separate interface, not a replacement assembly.
- No QUTS connection, private IOCTL, logging-mask change, adapter reset, firmware
  command or system-clock adjustment was performed in this pass.

## What can move downstream

The application-owned byte-return pattern and these rejection rules can inform
`userspace-clock` contracts now. They do not enable its hardware provider.

1. Preserve original binary bytes and packet schema/version alongside decoded fields.
2. Reject missing optional fields, error responses and schema-specific sentinels.
3. Mark delivery time, interpolated time and hardware-origin time separately.
4. Keep service transaction IDs separate from firmware request/exchange identity.
5. Require complete fragment assembly, bounded lengths and explicit loss/epoch state.
6. Keep hardware-to-QPC sampling separate from all delivery-time observations.

The next bounded experiment should first establish that QUTS can enumerate a
diagnostic protocol attributable to this exact adapter, without changing device
mode or logging masks. Enumeration can return empty lists on failure; record
query health and treat empty results as inconclusive. If a protocol is attributed,
qualify one existing record with raw bytes,
identity and length. Then match the WLAN definition to the actual producer and
firmware revision. If no such protocol is exposed, the missing driver/firmware
bridge remains the next dependency. A queue restart is not proof of firmware drain.

## Reproduction and validation

The maintained, file-only tool is
[inspect_qik_inventory.py](../../research/adapters/inspect_qik_inventory.py).
It requires Python 3.11+ and the repository's existing `pefile` dependency. It
accepts one already-decoded block directory, reads no device, emits JSON to stdout,
and exits 0 on success or 1 on invalid input. It performs no writes unless stdout
is redirected. Rollback is removal of the operator-selected output; no system
configuration is changed.

```powershell
python research/adapters/inspect_qik_inventory.py `
  artifacts/lolinet-static-2026-10-04/extracted/qxdm-blocks
python -m unittest discover -s tests -p test_qik_inventory.py -v
python -m compileall -q research tests
python -m unittest discover -s tests -v
```

The tool rejects missing, partial, duplicate and unmapped data blocks, ambiguous
metadata fields and malformed executable payloads. It records hashes and PE
metadata. It does not independently authenticate the original package or validate
the extractor's container offsets; those were checked separately for this run.

Private reproduction artifacts include:

| Local artifact | Purpose |
|---|---|
| `extract-qcc.ps1` | Authored static QCC block decoder; keeps package-decoding material in memory and does not emit it |
| `inspect-typelib.ps1` | Authored type-library metadata reader using `REGKIND_NONE` |
| `TraceAtlasQuts.java` | Authored bounded Ghidra string-reference/decompilation pass |
| `reports/qcc-index-validation.json` | Index offsets, counts, file sizes and hash checks for 17 containers |
| `reports/*-validated-inventory.json` | Full per-file inventories, including QPST's 154 MSI payload files |
| `reports/qpst-msi-tables.json` | Read-only MSI table evidence; records the unavailable TypeLib table query explicitly |
| `reports/quts-*-il.json` | File-only client and byte-array reader evidence |

Historical validation from the initial static-investigation snapshot, before
tool promotion and hardening (not the current PR-head result):

- Python compilation passed; the nine authored inventory tests passed.
- Full discovery ran 227 tests: 225 passed and two skipped. The unchanged native
  C export test had no compiler on PATH, and the Windows BSS image test lacked
  its separately configured image fixtures.
- Documentation navigation/layout checks passed as part of that suite.
- Both authored private PowerShell helpers passed parser validation.
- The final adapter check still reported Up / 1.0.4374.1300.
- No commit or push was made in this pass.

For the promoted tools and current publication checks, use the
[refresh validation record](../knowledge/refresh-validation.md) and
[script catalog](../../catalog/scripts.json).
The subsequent [qualification audit](../evidence/qualification-audit-2026-10-04.md)
closed both skipped tests: all 247 tests passed with the ARM64 compiler and exact
fixtures configured. It also verified successful hosted runs for published
revision `5d6695c`. The [live QUTS enumeration](../evidence/quts-enumeration-2026-10-04.md)
returned no protocol attributable to the active Wi-Fi adapter.

Extraction additionally used 7-Zip 26.00, PE resource reads, and the side project's
`Inspect-DotNetAssembly.ps1` / `Inspect-ManagedIL.ps1` tools. The InstallShield
format investigation consulted the
[pinned ISx source](https://github.com/Coldblackice/InstallShield-installer-extractor-ISx/blob/3c4177ddd0519244490ff8e78d380110c8dacdc8/ISx.c);
its executable was not run. The QXDM guide was read as PDF text, not executed.

No live performance, firmware-event association, complete absolute FTM export,
arbitrary packet timestamping, QPC conversion or calibrated accuracy was validated.
At this investigation's original validation checkpoint, hosted CI had not run
for these changes. Current publication and review status are tracked in the
[gap ledger](../overview/gap-closure-ledger.md).

## Glossary

- **COM / type library / IDL:** a Windows component interface, its compiled
  description, and a source description of callable methods and data types.
- **Thrift:** a message protocol and code generator used here for client/service calls.
- **QIK / QCC:** the package wrapper and block container identified in this installer.
- **QUTS:** Qualcomm's tool/device communication service; availability is separate
  from support for a specific adapter and diagnostic protocol.
- **QDSS:** Qualcomm diagnostic/debug trace transport; its timestamp domain must
  be related to the desired radio clock before use.
- **QMI:** Qualcomm's service-message interface, used in the selected USB/WWAN path.
- **WDF / IRP:** Windows driver-framework objects and operating-system I/O requests.
- **Owned bytes:** application storage whose lifetime does not depend on retaining
  a temporary driver pointer. Ownership alone does not establish timestamp meaning.
- **QPC:** Windows' high-resolution host performance counter.

Return to [adapter research](README.md) or the
[complete-event requirements](../ftm/ftm-ingress-to-owned-response.md).
