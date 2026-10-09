# Live driver-to-application byte-return control

A bounded live test returned the expected eight bytes through the installed Qualcomm driver's test service and the Windows WLAN API. This establishes a real byte-return route beyond the user-mode broker demonstration. The bytes are a fixed test pattern, not firmware measurements. A complete TSF producer still needs to be connected to a return mechanism with its original metadata and lifetime intact.

<!-- research-history:2026-10-09 -->
**Research context (2026-10-09):** Scoped technical reference. Build-specific findings and operational prerequisites retain their stated scope. [Current account](../research-history/README.md) · [Timeline](../research-history/timeline.md) · [Previous version](../../archive/2026-10-09-pre-refresh-e9d71b8/pages/docs__evidence__device-service-positive-control.md).
<!-- /research-history -->

## Contents

- [Observed result](#observed-result)
- [What produced the bytes](#what-produced-the-bytes)
- [The broader completion inventory](#the-broader-completion-inventory)
- [Repeatable control and permissions](#repeatable-control-and-permissions)
- [Validation and remaining dependency](#validation-and-remaining-dependency)
- [Glossary](#glossary)

## Observed result

Date: **2026-10-05**. Exact ARM64 `qcwlanhmt8380.sys` file hash:

```text
ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115
```

The installed package version was `1.0.4374.1300`; the SYS resource's separate
file version is `1.0.0.17731`. The selected interface was Up before and after each
attempt. Its GUID, driver path, version and hash matched across preflight/postflight.
Private interface identifiers remain in ignored local receipts.

| Check | Non-elevated attempt | Elevated attempt |
|---|---|---|
| WLAN handle open | Success | Success |
| Service enumeration | Access denied, code `5` | Success, five service GUIDs |
| Service commands sent | **0** | **1** fixed test GET |
| GET return status | Not attempted | Success, code `0` |
| Returned length and bytes | No result | **8**, `0102030405060708` |
| WLAN handle close | Success | Success |
| Adapter postflight | Matched | Matched |

The elevated process was launched through normal Windows `RunAs`/UAC, under the
user's existing authorization. The receipt records `elevated: true`. The probe
does not bypass UAC or elevate itself. The first attempt's failure was preserved;
the elevated attempt has a separate output directory.

The elevated GET's host QPC bracket was **1,665 ticks at 10,000,000 ticks/second**:
**166.5 microseconds** for this one call. That is API round-trip duration, not a
latency distribution, a hardware-read bracket, timer frequency measurement or
synchronization accuracy. It includes small local wrapper overhead. The returned
pattern contains no timestamp.

Private evidence is in `artifacts/tsf-consumer-return-20261005/`:

- `control-standard/result.json`: permission failure, zero service commands.
- `control-elevated/result.json`: successful fixed GET, QPC observations and identity checks.
- `control-elevated/control.stdout.txt`: native API statuses and returned bytes.
- `control-elevated/build.txt`: clean ARM64 build with `/W4 /WX`.
- `elevation-launch.json`: elevated-process launch record.

The live native source SHA-256 was
`e1a231de9b6f8c36390c5a7ed9507a0e0ad0b640a6c0f7851bdaaf19b9a3f6e0`;
its executable SHA-256 was
`83bb7010878d2267f42971e1f2b3cddbce0d1347478c63a899124f68e76cab7b`.
The binary and private receipts are not public Git contents.

## What produced the bytes

The selected service is `24364cfe-2ae8-4ed5-9643-a061f700ad5f`, opcode **1**,
with no input data. This is an inspected vendor operation, not an invented opcode.

```text
LIVE: application calls WlanDeviceServiceCommand
      exact interface + test-service GUID + opcode 1
                         |
                         v
STATIC: GUID dispatcher 0x1331d0 selects test handler 0x12a2a0
        handler uses the fixed eight-byte literal at 0x12a4b0
                         |
                         v
STATIC: serializer 0x1618c0 -> completion helper 0x13a890
        selected success path copies into the request's output
                         |
                         v
LIVE: caller receives 8 bytes, verifies every byte, closes WLAN handle
```

**Legend:** LIVE marks observed API results; STATIC marks the matching exact-file
implementation. Kernel stacks were not captured, so this is not a live trace of
each internal instruction. The fixed GET branch constructs the test pattern
without a firmware command in its inspected path. No TSF, FTM, test-mode, SAR,
antenna-setting or notification-trigger operation was sent.

Microsoft documents the service GUID, opcode, input/output buffers, returned-byte
count and administrative privilege requirement for
[WlanDeviceServiceCommand](https://learn.microsoft.com/en-us/windows/win32/api/wlanapi/nf-wlanapi-wlandeviceservicecommand).
The native control allows this one GET only, checks that the service was enumerated,
uses a 64-byte output buffer and accepts exactly eight matching bytes on success.
It cannot accept an arbitrary service, opcode or input payload.

## The broader completion inventory

This pass exported 62 selected functions covering the common completion helper,
its 70 direct-call sites, the service serializer and their overlapping callers.
All selected Ghidra exports completed without decompilation failure or instruction
truncation. The [offline inspector](../../research/adapters/inspect_private_exports.py)
now records manually reviewed argument roles and fingerprints their code windows:

- **59 calls:** null payload and zero payload length at the call to `0x13a890`.
- **11 calls:** a variable payload pointer/length can be supplied. An actual payload
  is conditional on the producer and status; this does not mean 11 timing APIs.

| Possible-payload call | Producer/role in inspected function |
|---|---|
| `0x02ecec` | 802.11 statistics |
| `0x12a430` | Fixed test-pipeline bytes, used by this live control |
| `0x12a998` | SAR configuration/state |
| `0x12acd4` | Antenna configuration/state |
| `0x12ae78` | Interface configuration |
| `0x12e860` | Nested IHV dispatch output, including previously investigated private returns |
| `0x12f5c8` | Power-management protocol offload |
| `0x1308dc` | Receive-segment-coalescing statistics |
| `0x130ce4` | Automatic power-save state |
| `0x1310b0` | Next action dialog token |
| `0x133178` | Supported device-service list |

This covers the identified immediate call sites, not every nested producer,
indirect call, unsolicited indication or firmware route. Status-only calls may
still belong to operations whose eventual data arrives elsewhere. The FTM task's
status completion therefore does not replace its separate aggregate indication.

Fresh tracing also corroborated two **existing** findings:

- The TSF callback `0x1f6980` stores a low-word difference, rather than the full
  report. See [private TSF returns](../tsf/private-tsf-fast-paths.md).
- The unsolicited service helper `0x137ca8` has test-pattern and SAR callers.
  This control did not subscribe to or exercise it. See
  [notification routing](../ftm/ftm-notification-routing.md).

## Repeatable control and permissions

The [PowerShell launcher](../../research/adapters/Invoke-DeviceServiceControl.ps1)
preflights one explicit interface. Default preview creates no output directory and
sends no service query. Build-only mode requires installed Visual Studio/Windows
SDK tools but never opens a WLAN handle.

```powershell
# Read-only identity preflight; substitute the selected interface index.
powershell.exe -NoProfile -File research/adapters/Invoke-DeviceServiceControl.ps1 -InterfaceIndex 20

# Compile and run software rejection tests, without an adapter.
powershell.exe -NoProfile -File research/adapters/Invoke-DeviceServiceControl.ps1 `
  -BuildOnly -Architecture arm64 -OutputDirectory artifacts/service-control-build-new

# One bounded live control, from a normally elevated PowerShell session.
powershell.exe -NoProfile -File research/adapters/Invoke-DeviceServiceControl.ps1 `
  -Execute -TestGet -InterfaceIndex 20 -OutputDirectory artifacts/service-control-live-new
```

- Preconditions: exact running Qualcomm driver file/hash, package version and Up
  adapter; installed compiler/SDK; a new output directory under repo `artifacts`.
- `-Execute` without `-TestGet` performs enumeration only. Enumeration itself can
  require administrative rights, as documented for
  [WlanGetSupportedDeviceServices](https://learn.microsoft.com/en-us/windows/win32/api/wlanapi/nf-wlanapi-wlangetsupporteddeviceservices).
- The helper verifies index-to-GUID identity again, records the actual token's
  elevated status, frees the service list and closes its WLAN handle.
- The launcher bounds its owned native child to 30 seconds, then allows up to
  five seconds for termination. Timeout means unknown execution outcome; it does
  not prove service/firmware cancellation or permit automatic retry.
- Exit `0`: selected mode passed. Exit `1`: preflight/build/API/validation failure.
  Native malformed arguments return `2`. Binding errors are usage failures.
- Rollback: no configuration was changed. Preserve evidence before removing only
  the chosen generated directory. Process exit is not a firmware drain or epoch.

The returned service-list `dwIndex` is application-owned and not meaningful output
from this query. The control uses the bounded item count and its own loop index.
See the [Microsoft list structure](https://learn.microsoft.com/en-us/windows/win32/api/wlanapi/ns-wlanapi-wlan_device_service_guid_list).

## Validation and remaining dependency

Offline tests exercise exact-pattern acceptance, wrong status/length/data rejection,
invalid CLI options, child exit-code preservation, timeout/termination and forbidden
flag combinations. Independent review identified and corrected the `dwIndex` check
and preservation of native results when postflight fails. No remaining P0/P1/P2
issue was reported in the reviewed control.

Local validation passed: **302 tests, zero skips**, with the installed ARM64
compiler and exact owned driver/Windows fixtures configured. Python compilation,
PowerShell parsing, documentation links, workflow consistency, script-catalog
hashes and Git whitespace checks also passed. PSScriptAnalyzer was not installed.

The CI workflow now builds/self-tests this control and runs the launcher tests
without hardware. Hosted CI on earlier revision `6f6ed8c` does not validate this
follow-up; the containing revision's checks are tracked in
[PR #3](https://github.com/Protonmatter/wifi-hardware-time/pull/3).

**The remaining connection is the producer.** The installed driver has delivered
the fixed control response successfully. It has not delivered an original `0x5005`
event, complete RX descriptor/frame or pre-aggregation FTM event through this
service. That needs a demonstrated existing producer route or vendor/instrumented
driver integration. The [driver integration contract](driver-event-return-integration.md)
still applies, including full source ownership, publication, loss and shutdown.
Hardware-to-QPC sampling remains a separate requirement.

## Glossary

- **Positive control:** a known expected result used to verify a transport or procedure.
- **Service GUID / opcode:** identifiers selecting a vendor service and its operation.
- **SAR:** specific absorption rate; the inspected service handles radio-exposure state.
- **IHV:** independent hardware vendor; an IHV envelope can carry vendor-defined data.
- **QPC:** host performance counter; here it measures API call duration only.
