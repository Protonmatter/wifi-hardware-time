# Windows timestamp path follow-up

Investigation date: 2026-10-02 America/New_York; fresh probe timestamp
2026-10-03T03:57:37Z. Research checkout HEAD when recording this note:
`a65ab66bdcaeac90cac6dff0c22cc3a200cd54bd`.

## Result

The existing documented Windows probes still return **23 / ERROR_CRC** on the
active Qualcomm adapter. No capability flags or cross timestamp were obtained.
The current probe layouts agree with the installed SDK and the inspected OS
implementation. No concrete ABI defect was found.

There is a specific alternative explanation for the CRC wording: the installed
OS status converter maps legacy `NDIS_STATUS_INVALID_OID` to the same Win32 error
23. The timestamp API implementation passes returned NDIS statuses through that
converter. This is a reproduced translation and a statically established possible
return path, **not proof that the live query returned INVALID_OID**. The original
kernel/NDIS status and exact failing branch were not captured.

Hardware-to-QPC sampling and general packet timestamps therefore remain separate,
unqualified capabilities. Private TSF diagnostic reports and successful FTM
operations do not qualify either capability.

## Bounded live evidence

Read-only adapter discovery selected the one active Qualcomm FastConnect 7800
interface. Endpoint identifiers are omitted from this note. The adapter was Up
before and after the queries; driver version remained `1.0.4374.1300` and its
active SYS file SHA-256 was
`ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`.
OS build was `26200.9457`, process architecture ARM64, and the token was not
elevated.

| Probe | Result |
|---|---|
| Python `GetInterfaceSupportedTimestampCapabilities` | 23; capabilities null |
| Python `GetInterfaceActiveTimestampCapabilities` | 23; capabilities null |
| Python conditional cross query | Skipped because active-capability query failed |
| Native SDK capability probe: interface-index-to-LUID conversion | 0 |
| Native supported / active capability queries | 23 / 23 |
| Native direct `CaptureInterfaceHardwareCrossTimestamp` | 23; no tuple interpreted |
| Native WLAN open / service enumeration / close | 0 / 5 / 0; zero service commands |

The service-enumeration access denial is distinct from the timestamp errors. No
elevation was attempted. Existing tools were inspected before execution:
`tools/probe_timestamp_caps.py`, `tools/native_caps.c`, and
`tools/device_services.c`. Each capability tool was run once; the existing
device-services tool made one direct cross query. No timestamp settings, adapter
state, profiles, clocks, or registry values were changed; no packets or private
device-service commands were sent by these probes.

The native executables were existing local ARM64 builds, not rebuilt in this
pass. Their PE imports match the documented query functions used here. This is
not a fresh source-to-binary reproducibility claim.

| Local executable | SHA-256 |
|---|---|
| `artifacts/native_caps.exe` | `53970033dd327b68d465f7569da020df0a119061bde8d8a25b955e5cad3a2712` |
| `artifacts/device_services.exe` | `3016bf31a411f5739d73d7010d1d8889334d06c823a9884b8d0e070fc59e34bf` |

## ABI and source inspection

Installed SDK: `10.0.26100.0`, `um/iphlpapi.h`. The declarations under
`NTDDI_VERSION >= NTDDI_WIN10_FE` match the maintained probe:

| Object | Size | Relevant byte offsets |
|---|---:|---|
| `INTERFACE_TIMESTAMP_CAPABILITIES` | 24 | frequency 0; cross support 8; hardware flags 9; software flags 20 |
| `INTERFACE_HARDWARE_CROSSTIMESTAMP` | 24 | first QPC 0; hardware counter 8; second QPC 16 |

Python `ctypes` sizes/offsets and the native probe's printed capability layout
agree. The DLL implementation clears 24 output bytes and copies cross timestamps
to offsets 0, 8, and 16. The API takes a pointer to `NET_LUID`; the tools first
convert the explicitly selected interface index, then pass the LUID by address.
They use the function's DWORD return value and do not treat the failed output
buffer as evidence.

The older `NTDDI_WIN10_RS5` branch of this SDK header has versioned structures.
The older [Winsock example](https://learn.microsoft.com/en-us/windows/win32/winsock/winsock-timestamping)
sets a `Version` member, whereas the current
[cross-timestamp structure reference](https://learn.microsoft.com/en-us/windows/win32/api/iphlpapi/ns-iphlpapi-interface_hardware_crosstimestamp)
has three 64-bit fields. Adding the old member to the current probe would break
the current layout. A future build should preserve its SDK/target metadata.

## Why error 23 does not identify a CRC fault

Microsoft documents `ERROR_NOT_SUPPORTED` as the supported-capability query
result for a non-timestamp-aware adapter. This run returned 23 instead, so that
documented unsupported result was not observed.
[Supported-capability API](https://learn.microsoft.com/en-us/windows/win32/api/iphlpapi/nf-iphlpapi-getinterfacesupportedtimestampcapabilities).

Read-only local inspection used PE exports/imports and Microsoft `dumpbin` against
the installed ARM64 `iphlpapi.dll`, file version `10.0.26100.1`, SHA-256
`b98fa18aa4d2333da270bea8ea29f889cd26197a8ae1353ab92c06998e876e0a`.
These are revision-specific code observations, not public ABI promises:

- Supported and active exports at RVAs `0x1c270` and `0x1c100` pass timestamp OIDs
  `0x00a00001` and `0x00a00002` to a shared helper at `0x1c2a8`.
- The helper can fail during interface/device lookup, during the OS
  `DeviceIoControl` call, or during conversion of the returned NDIS status.
  After successful `DeviceIoControl`, it reads status at internal buffer offset
  `0x24` and calls the status-conversion helper at `0x39d58`.
- The cross export at `0x1bfc0` uses OID `0x00a00003` and the same conversion
  helper. Only after success does it copy the returned hardware/QPC tuple.
- The converter special-cases an invalid-length status and otherwise passes
  negative status values to imported `RtlNtStatusToDosError`.

SDK `shared/ndis/status.h:49` defines legacy `NDIS_STATUS_INVALID_OID` as
`0xc0010017`. The following pure status conversions were executed without device
access:

| Converter input | Win32 output on this host |
|---|---:|
| `0xc0010017` — legacy `NDIS_STATUS_INVALID_OID` | 23 |
| `0xc000003f` — `STATUS_CRC_ERROR` | 23 |
| `0xc00000bb` — `STATUS_NOT_SUPPORTED` | 50 |

Do not confuse the legacy NDIS value with `STATUS_NDIS_INVALID_OID`
(`0xc0230017`) from `ntstatus.h`. Microsoft documents the converter as a mapping
to system errors and provides no inverse operation.
[RtlNtStatusToDosError](https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-rtlntstatustodoserror).
Thus 23 alone cannot recover the original status or locate the failing layer.

The invalid-OID explanation is now a concrete hypothesis. To establish it,
capture the existing documented API call's failing branch and pre-conversion
status on a dedicated diagnostic run, or obtain that information from Microsoft
or the driver vendor. No debugger attachment, hooks, kernel tracing, new IOCTL,
or undocumented API invocation was used here. Repeating the same public query
alone will not resolve this remaining ambiguity.

Also, NDIS answers `OID_TIMESTAMP_CAPABILITY` using the miniport's earlier
capability indication. Absence of an explicit driver OID handler therefore does
not prove absent hardware support.
[NDIS capability OID](https://learn.microsoft.com/en-us/windows-hardware/drivers/network/oid-timestamp-capability).

## Hardware-to-QPC sampling contract

The documented cross-timestamp path requires QPC, hardware-clock capture, and QPC
in that order, close together. An implementation with a more accurate paired
capture can return equal first/second QPC values. These are driver-provided
capture reference points, unlike application request-completion or ETW report
times. [NDIS cross-timestamp contract](https://learn.microsoft.com/en-us/windows-hardware/drivers/network/oid-timestamp-get-crosstimestamp).

If a future query succeeds, preserve the tuple, QPC frequency, adapter/build
identity, and acquisition epoch. Check return status, ordering and continuity
before fitting a relation. The QPC span characterizes the reported acquisition
bracket; it does not by itself establish external accuracy or UTC. A midpoint
mapping requires explicit assumptions, numerical tests, fresh observations, and
expiry. Restart or unknown continuity invalidates an old mapping.

Do not equate `HardwareClockTimestamp` with the private Qualcomm TSF or cached
SoC timer without evidence that they are the same clock domain. Hardware
frequency reported by capability metadata is nominal, may be zero, and is not a
calibrated rate guarantee.
[Capability structure](https://learn.microsoft.com/en-us/windows/win32/api/iphlpapi/ns-iphlpapi-interface_timestamp_capabilities).
This investigation obtained no tuple from which to establish any such relation.

## General packet timestamps are a separate qualification

| Path | Event reference point | Clock domain | Packet identity / limitation |
|---|---|---|---|
| Application QPC around send/receive | Application call or receipt | Host QPC | Application event; not an RF timestamp |
| Miniport software timestamp | RX early after arrival; TX late before hardware handoff | Host QPC | NBL/socket delivery; hardware queues and Wi-Fi retries remain outside that reference point |
| NIC hardware timestamp | Hardware frame receipt/transmission with driver delay correction | NIC hardware clock | Must establish frame association and hardware-to-QPC relation separately |
| Private Qualcomm TSF report | Diagnostic counter observation | Raw unqualified counter | No arbitrary application packet identifier |
| FTM result | Specialized ranging exchange/aggregation | FTM-specific semantics | Does not establish general RX/TX datagram timestamp delivery |

NDIS hardware timestamps attach to an NBL; on TX with multiple NET_BUFFERs,
Microsoft specifies the first NET_BUFFER's timestamp. A missing expected hardware
timestamp is represented by zero. Software timestamps use QPC at the miniport
boundary. These semantics do not identify every 802.11 retry or aggregate
subframe. [NDIS packet timestamp attachment](https://learn.microsoft.com/en-us/windows-hardware/drivers/network/attaching-timestamps-to-packets).

The documented Winsock path is UDP. RX uses `WSARecvMsg` and `SO_TIMESTAMP`; TX
associates `WSASendMsg` with a unique `SO_TIMESTAMP_ID`, then retrieves the result
by ID through `SIO_GET_TX_TIMESTAMP`. Results may arrive later, return
`WSAEWOULDBLOCK`, or be dropped when the socket timestamp buffer fills. Socket
configuration and system-level configuration are both needed.
[Winsock timestamping](https://learn.microsoft.com/en-us/windows/win32/winsock/winsock-timestamping).

PTP-only flags do not establish general UDP coverage: inspect successful active
`AllReceive`, `AllTransmit`, or `TaggedTransmit` capabilities appropriate to the
direction. Hardware and software timestamp modes cannot be assumed active
together. [Hardware capability flags](https://learn.microsoft.com/en-us/windows/win32/api/iphlpapi/ns-iphlpapi-interface_hardware_timestamp_capabilities).
Configuration keywords describe driver-controlled enablement; this pass did not
modify them. [Standard timestamp keywords](https://learn.microsoft.com/en-us/windows-hardware/drivers/network/standardized-inf-keywords-for-ndis-packet-timestamping).

For a future controlled packet experiment, record socket/session plus unique
datagram ID, direction, interface, timestamp source, raw ticks, epoch and
completion/missing status. Never reuse a timed-out TX identifier within a socket
session: a delayed result must not become a later datagram's timestamp. Poll only
within a bounded deadline. Establish separately whether hardware timestamps refer
to first RF attempt, final retry, acknowledgement, or another point; the reviewed
general APIs do not settle Qualcomm's Wi-Fi retry semantics. No UDP experiment,
packet capture, TCP timestamp API qualification, or retry correlation ran here.

## Validation and next discriminating work

- Inspected existing probe source, SDK declarations, native PE imports and OS DLL
  return paths. Compared Python/native layouts; no ABI correction justified.
- Repeated the existing documented capability and cross queries non-elevated;
  observed failures above and confirmed the adapter remained Up afterward.
- Reproduced status-code aliasing using only `RtlNtStatusToDosError`.
- Next investigate the original status behind error 23 and compare the same
  SDK-built queries with a known-capable NIC. No such comparison NIC was assumed
  available or tested here.
- Packet-path qualification follows successful capability discovery and explicit
  bounded UDP test design. RF retry/aggregation semantics and reference accuracy
  require separate evidence; a successful cross timestamp alone is insufficient.

Only this authored note was written. No probe code, binary, configuration,
dependency, service, or system clock was changed. No commit or push was performed.

## Debugger availability follow-up

A bounded read-only inventory did not find a usable native ARM64 user-mode
debugger in this session:

- `Get-Command cdb.exe,windbg.exe,windbgx.exe,ntsd.exe` found no executable on PATH.
- Neither the Program Files nor Program Files (x86) Windows Kits 10 `Debuggers`
  directory exists.
- Current-user `Get-AppxPackage` returned no WinDbg/debugging package; the user's
  WindowsApps alias directory contained no matching debugger executable.
- The standard HKLM/HKCU uninstall inventories returned no entry named WinDbg or
  Debugging Tools.
- Direct enumeration of the protected machine WindowsApps directory was denied
  to this non-elevated session. Consequently, this is a statement about tools
  discoverable and usable here, not proof that no debugger exists anywhere or
  for another account.

**Blocker:** no executable path for a native ARM64 debugger was discovered, so
observing the original status before conversion remains unperformed. No debugger
was started, installed, or downloaded; no existing process was attached, and no
DLL was modified. If an existing debugger path becomes available, first validate
its ARM64 architecture and then agree a bounded plan that launches only the
existing documented native probe as a new child and observes the returned status
at the identified API conversion boundary. No direct private request is needed
to investigate that branch.
