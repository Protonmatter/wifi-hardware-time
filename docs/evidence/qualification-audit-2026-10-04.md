# Offline qualification audit, 2026-10-04

The existing offline suite passes **247 tests with zero skips** when the installed
ARM64 compiler and exact owned Windows/Qualcomm image fixtures are supplied.
The exact Qualcomm driver validates against its signed catalog. Selected QPST
and QXDM components also have valid publisher signatures. These results strengthen
software and file-provenance evidence; they do not establish a live Wi-Fi timing
record, a server snapshot contract, or calibrated clock accuracy.

<!-- research-history:2026-10-09 -->
**Research context (2026-10-09):** Dated evidence or historical plan. This dated report or plan retains its original evidence and execution scope; later results and publication status are in the research account. [Current account](../research-history/README.md) · [Timeline](../research-history/timeline.md) · [Previous version](../../archive/2026-10-09-pre-refresh-e9d71b8/pages/docs__evidence__qualification-audit-2026-10-04.md).
<!-- /research-history -->

## Scope and revision

This audit read files and existing evidence, verified signatures, compiled and ran
the repository's authored offline harness, and queried GitHub publication state.
It did not connect to QUTS or a device, execute vendor code, change logging, issue
private requests, install software, reset an adapter, or adjust clocks. A separate
live investigation must state its own acquisition result.

The audited source revision was `5d6695c0ad59631e301aafc7e689977468ada0b9`.
Before this document was created, the working tree was clean. A fresh remote-ref
query matched that revision on `investigate-packet-export`; [PR #3](https://github.com/Protonmatter/wifi-hardware-time/pull/3)
was open, targeting `main`, with the same head. Both the
[pull-request run](https://github.com/Protonmatter/wifi-hardware-time/actions/runs/37232139403)
and [push run](https://github.com/Protonmatter/wifi-hardware-time/actions/runs/37232136722)
were completed successfully, including `protocol` and `windows-syntax` jobs.
These hosted results apply to that source revision, not to this subsequently
authored document or future changes. No commit, push or merge occurred in this audit.

Earlier reports describing their work as local or uncommitted remain historical
snapshots. They are not the current publication state of the audited source.

## What the evidence supports

| Claim | Audit result | Remaining requirement |
|---|---|---|
| Application owns QUTS diagnostic payload bytes | Supported statically in the exact managed client and Thrift DLL. The saved file-only IL records show `DiagPacket.Read` calling `ReadBinary`, assigning `BinaryPayload`, and concrete readers allocating byte arrays before `ReadAll`. Current file hashes still match those records. | Does not establish what the server copied or which firmware producer supplied it. No vendor assembly was executed. |
| Authored exporter owns complete synthetic records | Existing native ARM64 regression passed, including its ownership, structural rejection, generation, quarantine, close and loss-accounting checks. | Caller serialization and stable input remain preconditions. No live driver producer is connected by these tests. |
| QUTS delivers this adapter's required firmware timing event | Not established by the evidence audited here. Located client methods and WLAN schema names are useful leads. | An attributable live protocol and record, matched schema/build, clock identity, validity and event identity. Absence of proof is not proof of unsupported hardware. |
| A service transaction identifies the firmware event | Not established. Service transaction association and firmware/exchange identity have different scopes. | A demonstrated mapping, including unsolicited/late records and fragment identity. |
| QUTS server copies a consistent complete event | Not established by client deserialization. Owning a newly allocated client buffer only establishes that buffer's lifetime. | Producer lifetime, copy-before-publication ordering, completeness, loss and epoch behavior on the server path. |
| Saved counter fits establish hardware-to-QPC conversion | Not established; the six mixed-bundle analyses still explicitly reject this promotion. | Qualified fresh sampling brackets, units, reference instant, continuity and independent validation. |
| Numeric timestamp resolution establishes accuracy | Not established. DIAG/interpolated, QDSS, host-delivery, TSF and QPC domains must remain distinct. | An independent reference or controlled node experiment and an attributable uncertainty budget. None was available to this audit. |

The installed `Common.thrift` and `DiagService.thrift` hashes also match the
[archive investigation](../adapters/qualcomm-archive-transport-findings.md).
The schema-specific missing-value and field-presence rules in that investigation
remain relevant; a successful byte return does not promote a delivery timestamp
or interpolated value to a hardware sampling instant.

## Publisher-signature verification

`Get-AuthenticodeSignature -LiteralPath` checked each listed installed or extracted
file. Windows SDK ARM64 `signtool verify /pa /all /v` additionally checked the eight
selected package files. The driver received an explicit kernel-policy catalog
membership check: `signtool verify /v /kp /c <catalog> <driver>`.

`Valid` means these Windows trust-verification calls accepted the signature under
this machine's policy and trust state at audit time. It is not a code-safety or
hardware-capability certification. No separate fresh online revocation audit was
performed. `NotSigned` means the checks found no recognized Authenticode signature;
it does not authenticate or discredit the installation's provenance. No signed
package containing the unsigned installed QUTS or WLAN files was verified here.

| Installed file | SHA-256 | Result |
|---|---|---|
| `QUTSService.exe` | `30dc1fac9c9fb7a5672fb665daf33f72c8bc3456fa545bd169c7ae77eb4863b6` | `NotSigned`, signature type `None` |
| `QUTSClient_csharp.dll` | `085ce63b9d661e206ae97e81f249bb71b5099982c4b67013595ee63c62a9d059` | `NotSigned`, signature type `None` |
| `Thrift.dll` | `85e3d1499f4d3c881a689056d1ada9b2d1829b785e245920cf1fa29cb4028353` | `NotSigned`, signature type `None` |
| `QC.CTE.WLANTestSuite.dll` | `33a982738130e42164ae9481e5cad9c0d4a316e48779a5c7d3c534718345c19f` | `NotSigned`, signature type `None`; current assembly remains 2.0.79.1 |
| `qcwlanhmt8380.sys` | `ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115` | `Valid`, signature type `Catalog`; explicit catalog membership succeeded |
| `qcwlanhmt8380.cat` | `76f90201bd8d4e24fdfaf15e4ae43480b9a02a6d7cb571fbe15322ffc0f0bfe1` | `Valid`, signature type `Authenticode` |

The driver catalog signer is **Microsoft Windows Hardware Compatibility Publisher**;
the timestamp signer is **Microsoft Time-Stamp Service**. The explicit membership
check returned exit 0 with one file verified, zero warnings and zero errors. Its
timestamp was verified; the displayed signing date was 2025-07-24. Certificate
expiration dates alone should not replace the recorded timestamp-aware result.

| Selected downloaded-package component | SHA-256 | Authenticode / SignTool result |
|---|---|---|
| `QPST.2.7.496.1.exe` wrapper | `191b6784c9eb56b7269327348ca32a2e180411eb02f6c5e615e36cb43bcf4981` | `Valid`; exit 0 |
| Nested `QPST 2.7.msi` | `edb111bda47846edb57a4e62563a509a774fa1ebeee7460f4d00cec31dc03182` | `NotSigned`; exit 1, no signature found |
| `QPST_MergeModule.msm` | `f8ad01cfba3cee3b22dfe094db6057db83ff1ee21799b7b3e281bc8df93bf187` | `Valid`; exit 0 |
| `QPSTServer.exe` 2.7.0.496 | `14c4575859dc92200cd22d5c9f4c22a4d626d76f9ed837908c1d010296eae4e0` | `Valid`; exit 0 |
| `QpstMarshal.dll` | `89b56dab32262881d714eca2ccf47de9ddf45b4b2ed6e82c9ff9527ff42f6bab` | `NotSigned`; exit 1, no signature found |
| `SerialPortLib.dll` | `ee609726c82ff5eaf242a5a570d27ab4fa695d6a2f028c555bcd587007600f4e` | `NotSigned`; exit 1, no signature found |
| `QXDM.4.0.450.2.Windows-x86.exe` QIK wrapper | `55ad3c7c6532d52c4eca3a7790c178ad4e44aa946dc98573d5af7d3a4d1999e7` | `NotSigned`; exit 1, no signature found |
| Extracted `QXDM.exe` 4.0.450.0 | `523a760f8d8d0101fd99096a0e13779c23507dfae3cfae6972f687c417ab7075` | `Valid`; exit 0 |

All four accepted package signatures identify **Qualcomm Technologies, Inc.**,
with **Symantec Time Stamping Services Signer - G4** timestamps. SignTool verified
one signature and timestamp per accepted file with zero warnings/errors. Displayed
signing dates were 2020-03-19 for the QPST wrapper/server, 2020-02-21 for the merge
module and 2020-06-30 for QXDM. Raw trust-chain output is retained privately.

The three source ZIP/7z archive hashes were rechecked and match the published
[download identities](../adapters/qualcomm-archive-transport-findings.md#scope-and-provenance).
Archive identity is separate from publisher authentication. This was a bounded
component audit, not signature verification of every file in every archive. No
signature result is assigned to QUD source text. Extracted payloads with cabinet
keys or `.bin` filenames were copied byte-for-byte to conventional executable
filenames in the private audit directory for verification; their hashes were
matched first, and they were never executed.

## Offline validation and reproduction

The installed MSVC `14.44.35207` ARM64-host/ARM64-target environment was initialized
in a child PowerShell process with `Enter-VsDevShell`. Only that process received
`WIFI_TIME_NATIVE_CC`, `WIFI_TIME_DRIVER_FIXTURE`, `WIFI_TIME_WIFICX_FIXTURE`, and
`WIFI_TIME_WLANMSM_FIXTURE`. No user or machine environment variables changed.
The native test compiled the authored C sources with `/std:c11 /W4 /WX /O2` and
executed its offline harness. The standalone `Test-TimestampExport.ps1` runner was
not invoked; its same C harness was exercised through full unittest discovery.

Each fixture was SHA-256 checked before configuration:

| Fixture | Exact SHA-256 |
|---|---|
| Qualcomm driver | `ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115` |
| `wificx.sys` | `7587df7324f4daa70af890edae6e60316b2277a2bb6e21b29ecf6d71f3f3635d` |
| `wlanmsm.dll` | `2e80a99a59d604df8f4c05da0149792acca3f7f50d4fcfae5196493b1d91055b` |

| Command / check | Result |
|---|---|
| `python -m compileall -q research tests` | Exit 0 |
| `python -m unittest discover -s tests -v` in the scoped compiler/fixture environment | 247 tests, zero failures, zero skips; 19.166 seconds |
| `analyze_clock_pairing_hypothesis.py <saved-bundle> --compare-counters` for six existing mixed runs | All six commands exited 0, three action-4 samples each |
| Signature checks above | Four selected package signatures and exact driver catalog membership accepted; unsigned cases retained as unsigned |
| Read-only remote branch, PR and Actions queries | Matching head and successful runs recorded above |

The six pairing replays reproduce common-rate feasibility under the stated
unproven host-window/unit assumptions. The nominal fixed 10-QPC-ticks-per-raw-tick
model is infeasible for both counters in every replay. Each output retains
`conversion_qualified: false`, `simultaneous_sampling_validated: false` and
`external_uncertainty_ns: null`. The campaign remains quarantined. Replaying saved
evidence does not admit new records or make old acquisition windows valid sampling
brackets; see [counter-rate identifiability](../clock-models/counter-rate-identifiability.md).

Private reproduction artifacts are under ignored
`artifacts/qualification-audit-ad8a8e1ff964/`: `run-suite.ps1`, fixture/toolchain
receipts, full test output, installed/package signature JSON, SignTool logs,
download/IDL hashes, six pairing outputs and summary, and exact PR/run JSON.
The audit summary is `qualification-summary.json`. Raw paths, vendor files and
diagnostic evidence remain outside public Git. This dated document is the only
authored repository file added by the audit.

## Remaining limits

No independent timing reference, second controlled node, fresh firmware timing
event, end-to-end loss test, server concurrency test, live QPC pairing, or hardware
accuracy measurement was produced. No claim about all possible vendor protocols
is supported by an absent or empty record. Positive client/exporter ownership
results remain useful, independently of those open acquisition and accuracy gates.
