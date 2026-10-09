# WPP External 2.3.1.1: installed tooling and route limits

The supplied WPP installation adds concrete WLAN ETL collection and diagnostic-bridge configuration tooling. File inspection does not establish that its loggers emit a complete original timing event from the selected Wi-Fi adapter. The current Qualcomm hardware route therefore remains no-go. The useful new evidence is the available package, its exact scripts and their state effects, rather than a demonstrated live producer connection.

## Scope and exact files

Inspected on 2026-10-06, America/New_York, after the separate host acceptance
campaign finished. The supplied installation label/directory is **2.3.1.1**;
the main executable's Windows FileVersion and ProductVersion are both
**1.0.0.0**. These are different identity fields and must not be substituted for
one another. Its configuration declares .NET Framework 4.7.2.

A bounded recursive inventory found **88 files, 10,193,949 bytes**, with no
reparse points. Every file was hashed; selected identities are below. Private
inventory receipt SHA-256:
`6feb0c46b1f9e516250c6cfe4171dadd024d561b0fe5cca05f017d488fc1829d`.
The inventory contains relative names, sizes and hashes, not copied vendor
payloads. Vendor scripts, PDF extraction and rendered pages remain private.
Version-resource metadata was recorded for the 12 EXE/DLL files in a separate
private receipt with SHA-256
`213c0f394f4792f25f8cf91194983d43b131a7d487993f6d05731c4f1c0ea514`.

| File within the installation | Bytes | SHA-256 |
|---|---:|---|
| `Qualcomm_WPPv2.exe` | 1,076,224 | `252257f421423908741f4ee082dcef9f5c479477fed967090d5a832ce8f27036` |
| `Qualcomm_WPPv2.exe.config` | 3,078 | `e29cae8ffa107d3d218fe9081e3c775bda8e52599a42cb99d3d2ddf53973a78e` |
| `readmeV2.pdf` | 624,291 | `19b2f84f0ad21ae0109d428d82477df4dd98132302f0336387b9e7f724cbf7af` |
| `common/wpwlansetup.bat` | 184,920 | `a6f58bc0d7497abaaad7c2576636ed9915c24029e09017b84470b18d196d5bed` |
| `script/wifi/wifi_trigger_default.bat` | 159 | `ea6a6c623d81698bd72056e80c92badfa93154c281893bc6b01fad124c9ec0b8` |
| `script/wifi/DisableWifi.bat` | 134 | `660cc47b95f21ecb9407fd4bacbf9c2569adb174f0970e7a38c4732144291b88` |
| `common/QCDiagBridgeController.exe` | 56,832 | `2b5a26ac6030ec2716080d40107fb50d4e9337c0c6d37eab679b20b662aee487` |
| `common/default.xml` | 86,732 | `1c2866ea10358ca69c04eaa62614c958a899c4ca27a6d48536564fea8661d002` |

No installed executable, DLL or script was invoked. Reading version resources,
hashing files, parsing the PDF and rendering its pages did not start vendor code,
trace collection or a device operation. No registry, logging, driver or service
state was changed, and no package/SDK installation was performed.

## What the supplied guide and scripts establish

The 11-page installed guide, `readmeV2.pdf`, describes a Windows software trace
collection application. Pages 2-3 identify Windows SDK tools `tracefmt.exe`,
`tracelog.exe`, `tracepdb.exe`, `traceview.exe` and `tracewpp.exe`; the Wi-Fi
feature list names start/stop collection. Page 6 distinguishes manual collection,
autologging after boot, sequential limits and circular overwriting. Page 9 asks
for relevant PDBs when formatting logs. These statements describe the package
workflow, not what a particular driver emits.

None of those five SDK executables appears in this installation's 88-file
inventory. A bounded follow-up found **all five already installed elsewhere**
under the existing Windows Kits root, in each of the `arm64`, `x64` and `x86`
directories: `C:/Program Files (x86)/Windows Kits/10/bin/10.0.26100.0/<arch>/`.
All 15 files have ProductVersion `10.0.26100.7705` and FileVersion
`10.0.26100.7705 (WinBuild.160101.0800)`. The SDK directory version and binary
resource version are distinct. None of the five names resolved through
`Get-Command -CommandType Application -All` in this session.

The follow-up checked PATH and the standard Program Files / Program Files (x86)
Windows Kits roots only; the latter was the sole existing root. Every discovered
file's size, version resources and SHA-256 were recorded without invocation.
Private SDK inventory receipt SHA-256:
`87ab6a198773c3f29bc00e77be7d8d9fc4df77db9268b9f0af6d3dde50115525`.
Selected ARM64 hashes are recorded here; x64/x86 hashes remain in that receipt.

| ARM64 SDK file | SHA-256 |
|---|---|
| `tracefmt.exe` | `b91aa20df3507307e0119032b9708e69927961b6c39a9b410138e86077f91a8c` |
| `tracelog.exe` | `a3cb58ae52e078eafb3ccecded534595f04429533300a07a83d8f4d112e05201` |
| `tracepdb.exe` | `7a153af268d93c044deb2cbe378412e0b915569e8c4c80aeda1bafe95eac60f3` |
| `traceview.exe` | `1b06dad944b725873a71a7d45603da1d90646c4c7a431815774dac6c6a2bd3cb` |
| `tracewpp.exe` | `2726b5bd4d39efc64cd5e5e6c61dd9bfc48561daa2128500b843047ee287341c` |

The trace executables are available as files, but WPP's discovery/loading of
them and their execution remain untested. No tool was copied, PATH changed or
SDK installed by this follow-up. The original WPP package inventory also contains
no filename-matched WLAN driver PDB or TMF. The
GUI's PDB and USB/camera symbols do not prove a symbol match for the inspected
Wi-Fi driver. No PDB identity or live provider readiness was qualified.

Selected script evidence, tied to the hash above:

| Location / symbol | Static result | Consequence |
|---|---|---|
| `script/wifi/wifi_trigger_default.bat`, lines 1-5 | Requests full Wi-Fi logging, then disables and enables the Wi-Fi device | This trigger is state-changing and disruptive; it is not an existing-record-only read |
| `common/wpwlansetup.bat`, `__configQcWlanLogLevel`, lines 4277-4319 | Full mode reaches host logging settings, firmware logging and diagnostic-bridge message configuration | Logging setup has explicit configuration effects; settings changes need their own bounded experiment and rollback |
| `startQcWlanTrace`, lines 1917-1945 | Defines a WLAN ETL trace and passes it to the trace-start helper | A concrete existing-provider collection lead; no original-event payload schema is established |
| `__getQcWlanStatement`, lines 1562-1588; `__startQcWlanFwTrace`, lines 2040-2058 | Firmware trace admission depends on selected hardware/driver predicates and both firmware/driver diagnostic flags | Presence of the batch file does not prove the current adapter satisfies those predicates |
| `startQcDiagBridgeTraceForWlanIfNeeded`, lines 2246-2279 | Conditional bridge collection requires firmware diagnostic availability and a located bridge service key | Bundled bridge helpers do not prove the service is installed, the adapter is connected to it or a timing producer is reachable |
| `configQcDiagBridgeMessageLevelsWlanFW`, lines 2079-2113 | Selected full mode constructs message settings and changes diagnostic-router configuration | This is a concrete configuration lead, with additional state effects; it is not evidence that any requested report is emitted |
| `common/default.xml` | Declares a diagnostic-bridge logging configuration containing numeric packet selections | A configuration file does not provide the original WMI timing-event schema or a producer-to-client association |

No runtime predicate was evaluated and no setting was applied. Source inspection
of these selected script branches is not a complete review of the GUI or every
helper. The existence of another trace configuration does not contradict the
[saved trace-byte audit](../tsf/saved-trace-byte-audit.md), which remains scoped
to its selected historical captures.

## Effect on the hardware route decision

The installation and SDK follow-up close **file-availability questions** and
supply specific WLAN/firmware/bridge collection leads. They do not close any complete-event
hardware gate in the [route decision](hardware-route-decision-2026-10-06.md):
no emitting callsite with complete original timing bytes was newly established;
no exact live adapter-to-producer association, source span/lifetime, complete
owned return, loss/continuity contract or bounded teardown was demonstrated.
ETL receipt time and formatted log timestamps remain separate from radio
sampling time.

Reopen the trace route only after evidence identifies a matching producer or
emitting callsite that retains the required original bytes and identity, together
with a reviewable exact-target collection profile, state effects, loss limits,
bounded cleanup and rollback. A later separately authorized finite capture must
then demonstrate the record and ownership. WPP availability alone does not
authorize the supplied trigger, remove quarantine or select Linux.

## Validation and limits

All 88 hashes were re-read and matched the initial inventory. The PDF's 11 pages
were extracted for local reading, and relevant pages 3, 6 and 9 were rendered and
visually checked. File/version/hash inventory and selected source-text review
and all 15 SDK file/version/hash checks are the validation performed here. GUI launch, dependency resolution, driver
symbol matching, provider enumeration, collection, conversion, live cleanup,
hardware timestamps and accuracy were not tested.
