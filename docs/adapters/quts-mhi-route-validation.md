# QUTS MHI route and live-validation status

The MHI discovery patterns and their input fields are now traced, and the large
worker has a complete export of its Ghidra-recognized instructions. The branch
constructs DIAG protocol and connection objects, but no FastConnect endpoint or
firmware record has been demonstrated. The later corrected capture now binds
12 failed control-endpoint queries to the traced code, with all 20 controls present.
Hosted checks must be tied to a published
revision and do not establish hardware qualification.

<!-- research-history:2026-10-09 -->
**Research context (2026-10-09):** Scoped technical reference. Build-specific findings and operational prerequisites retain their stated scope. [Current account](../research-history/README.md) · [Timeline](../research-history/timeline.md) · [Previous version](../../archive/2026-10-09-pre-refresh-e9d71b8/pages/docs__adapters__quts-mhi-route-validation.md).
<!-- /research-history -->

The [live query and CommonIo follow-up](quts-live-gate-and-commonio.md) is the
current result. Earlier attempts below retain their original dispositions.

## Contents

- [What is established](#what-is-established)
- [Matcher initialization and inputs](#matcher-initialization-and-inputs)
- [Connection construction](#connection-construction)
- [Live observations and failed coverage](#live-observations-and-failed-coverage)
- [Assembly export limit](#assembly-export-limit)
- [Reproduction and validation](#reproduction-and-validation)
- [Remaining gates](#remaining-gates)

## What is established

This is a 2026-10-04 follow-up to the [network discovery gate](quts-discovery-gate.md)
and [first live enumeration](../evidence/quts-enumeration-2026-10-04.md). It uses
the same ARM64 `QUTS.exe` version `3,96,2`, SHA-256
`8e6de10a298f8378e9d289ad11a33018654a29d155e56588f9427d53ed639297`.
Offsets below are RVAs; add `0x140000000` for the offline Ghidra address.

| Requested claim | Current result |
|---|---|
| Live execution of the selected registry query | Now demonstrated in follow-up attempt 06: 12 failed queries, exact adapter-key binding and matching stacks. The following conditional instruction was not directly traced. |
| Live MHI transport | Not demonstrated. No service connection or firmware command was attempted. |
| FastConnect-to-MHI association | Not demonstrated. Discovery predicates are now explicit, but no matching attributable endpoint is established. |
| Firmware-event identity and complete-record delivery | Still open. Discovery-event string ownership and DIAG object construction are different from firmware-packet ownership. |
| Hardware-to-QPC sampling | Still open. Host trace delivery, process identity and static control flow do not supply a hardware sampling bracket. |
| Hosted CI at the validation check | New changes had not been published. PR #3's successful checks applied to `5d6695c`; later publication requires its own exact-revision check. |

## Matcher initialization and inputs

MHI means Modem Host Interface. In this investigation it identifies a transport
selection route; it is not proof of a particular Wi-Fi chip or timing producer.

| Global string object | Initializer RVA | Stored pattern | Selected input |
|---|---|---|---|
| `0x1894620` | `0x00e670` | `.*?QCDM\|.*?qcdm` | Discovery event's `DevDesc` |
| `0x1894640` | `0x00e620` | `mhi.*?` | Discovery event's `ParentDev` |
| `0x1894730` | `0x00e6c0` | `.*?SAHARA` | Neighbouring Sahara branch |
| `0x1894750` | `0x00e5d0` | `.*?FIREHOSE` | Neighbouring Firehose branch |

The backslash before the vertical bar in this Markdown table is formatting;
the actual DIAG pattern is `.*?QCDM|.*?qcdm`.

The original empty file bytes were the initial representation of C++ string
objects. The initializers construct their values and register destructors. They
were not evidence that the runtime matching patterns were empty.

The input mapping follows the producer and consumer:

- `addDiscoveryEvent` at `0x18a488` logs the incoming description as `DevDesc`
  and the pointer at input offset `+0x54` as `ParentDev`.
- It copies the description into the queued event at `+0x18` and parent text at
  `+0x58`. The event copy helper `0x1864f8` preserves these string fields.
- Worker `0x1a64d0` tests the description through `0x1a2d58` at `0x1ae490`, then
  tests the copied parent text at `0x1ae4b0` before the selected MHI DIAG branch.
- An additional packed-flag condition precedes these tests. Its numeric low-nibble
  check is visible; this report does not assign an unproved hardware meaning to it.

These are the QUTS discovery fields. `ParentDev` must not be silently substituted
with an arbitrary Windows PnP parent's friendly name. This pass identifies the
literal patterns and field flow, not every regular-expression-engine edge case.

A bounded present-device friendly-name search returned the FastConnect network
and Bluetooth entries and no `MHI`/`QCDM` name match. A name search is not an
exhaustive device-interface inventory or a hardware-incapability result.

## Connection construction

The selected chain is now more concrete:

```text
Discovery event: DevDesc + ParentDev + flags
    -> pattern predicates at 0x1a2d58
    -> DIAG object factory 0x17fa18
    -> Device::Protocol::Diag constructor 0x1dd3b8

Selected virtual connection method at 0x1ef198
    -> Device::DiagConnection constructor 0x313b38
    -> Device::Connection base constructor 0x27f970
```

The connection factory was resolved from the DIAG vtable's `+0x100` slot. Recovered
C++ runtime type information identifies the allocated types. This is positive
static implementation evidence, not a live open or a packet-return observation.

The protocol's `connect` path at `0x1ed228` checks availability, can create logging
state, calls `doSimpleConnect` at `0x1f38e0`, and performs further initialization.
The lower path depends on a `Device::Communication::CommonIo` object. The selected
connection wrapper is therefore not by itself the complete hardware transport.
Neither attaching a DIAG label nor constructing the object establishes a passive
existing-record retrieval contract.

## Live observations and failed coverage

The authorized observations used normal Windows tracing, with no private Wi-Fi
IOCTL, QUTS RPC, device-mode change, firmware logging-mask change or reset.
The original attempts 01–02 used a unique WPR instance, an 8 MiB memory buffer budget,
exact adapter/driver checks, and source/profile snapshots taken before tracing.

| Attempt | Observation | Disposition |
|---|---|---|
| 01, 20 seconds | Manifest registry provider with executable-name filter; zero registry-provider events; zero reported losses | Coverage not established. Empty output cannot prove QUTS inactivity. |
| 02, 5 seconds | Same manifest provider without the process filter; observer also issued known read-only registry queries; zero registry-provider events and zero reported losses | Positive control missing: coverage failed. The earlier filter alone is not established as the cause. |
| 03, corrected system-registry profile | Preview and profile-details validation passed; UAC was cancelled | Not executed. No trace directory or recording was created. |

The positive control was explicitly from the observer's PID, not a QUTS process:
five reads each of the active driver key's `NetCfgInstanceId` and
`QCDeviceControlFile`. These were reads only. Their absence means the second
trace cannot support a negative claim about the vendor process.

Both executed captures stopped their own instance successfully and reported
unchanged adapter and QUTS-process identities. Elevation allowed the script to
read each running QUTS executable path, current disk hash and module base. That
improves process/file association compared with the earlier access-denied run;
it does not attest all in-memory code or retroactively qualify that earlier run.

The corrected profile uses the documented system `Registry` keyword with
`RegistryQueryValue` and `RegistryOpenKey` stack collection, as confirmed against
the installed WPR profile. The later [qualified capture](quts-live-gate-and-commonio.md)
increases the buffer budget to 32 MiB and verifies both start and end controls.
Microsoft distinguishes the [system registry tracing path](https://learn.microsoft.com/en-us/windows/win32/etw/registry)
from ordinary event-provider configuration; see also the
[WPR command reference](https://learn.microsoft.com/en-us/windows-hardware/test/wpt/wpr-command-line-options).

## Assembly export limit

The 4,096 cap limited the text export per function. It did not stop whole-program
analysis or cap the decompiler's input. For this worker, increasing it was useful:

- New argument: `max-instructions:32768`.
- Accepted range: 4,096 through 65,536; default remains 4,096.
- Actual worker export: **12,235 recognized instructions**, marked complete.
- Matcher pass: **17 completed decompilations**, all assembly exports complete.
- The 900-second whole-analysis and 120-second per-decompilation limits remain
  unchanged; the existing analyzed project was reused without whole reanalysis.

Complete here means all instructions in Ghidra's current function body. It does
not mean every runtime path, indirect call or function-boundary inference is
proven correct. Larger exports do not strengthen timing accuracy claims.

## Reproduction and validation

Use [TraceQutsDiscovery.java](../../research/adapters/ghidra/TraceQutsDiscovery.java)
with `-noanalysis -readOnly` on the existing pinned project:

```text
-postScript TraceQutsDiscovery.java <new-private-output> max-instructions:32768 1894620 1894640 1894730 1894750 1a64d0 1dd3b8
```

The colon form avoids the Windows batch launcher splitting an equals-sign argument.
The initial equals-sign attempt was rejected before export; it is retained as a
failed invocation, not counted as a successful trace.

The prepared OS observer is
[Observe-QutsRegistry.ps1](../../research/acquisition/Observe-QutsRegistry.ps1),
with [quts-registry.wprp](../../research/acquisition/quts-registry.wprp).

```powershell
# Preview and validate the profile; no recording is started.
./research/acquisition/Observe-QutsRegistry.ps1 -Seconds 5
# In an elevated console, when the next live observation is intended:
./research/acquisition/Observe-QutsRegistry.ps1 -Execute -Seconds 5 `
  -OutputDirectory '<new-private-evidence-directory>'
```

Execution fails before recording if exact driver/process identity cannot be
obtained. The observer records its unique instance name and stops that instance
in normal completion or cancels it on failure. A forcibly interrupted host may
require the exact-instance cleanup command shown in the script header. Exit zero
means capture completed; event coverage, loss and identity must still be reviewed.
The memory budget bounds collector buffers, not all metadata added to the final ETL.

Raw traces, process identities, Ghidra exports, receipts, failed attempts and
cancelled-elevation evidence remain under ignored
`artifacts/quts-mhi-validation-20261004/`. They are not public-source inputs.

Local validation on the completed tree:

- Python compilation and full unittest discovery: **247 passed, zero skips**,
  with the installed ARM64 compiler and pinned Windows/driver fixtures configured.
- PowerShell parser, native WPR profile preview and Windows PowerShell 5.1 preview:
  passed. The unelevated-execution guard rejected before creating output.
- Ghidra's 32,768-instruction override exported the worker completely. A value of
  65,537 rejected before output creation; omission retained the 4,096 default.
- The matcher, connection and event-boundary passes completed their selected
  decompilations. No whole-program reanalysis was needed for these follow-ups.
- PSScriptAnalyzer was unavailable. These local results describe the earlier
  tree; the follow-up report covers the subsequent elevated live path.

The first hosted run on `b2e8b12` reproduced a script-catalog hash mismatch on
both platforms: the new observer was registered from LF bytes, while the existing
repository attributes require `.ps1` checkouts to use CRLF. The catalog was
corrected to the required CRLF file hash, without weakening the integrity test.
A fresh checkout with automatic line-ending conversion disabled
verified all registered hashes because the explicit repository attributes still
apply. Prior execution receipts retain the actual bytes used in those captures.

## Remaining gates

1. Preserve the distinction now established by the qualified capture: query status
   and matching stack addresses validate the selected syscall path; the following
   conditional instruction remains a static inference, not a direct execution trace.
2. Match an actual endpoint's discovery metadata and lower transport to FastConnect.
   Then establish a nonmutating existing-record access path before reading one.
3. Preserve timestamp domain, units, width, event identity, validity, loss and epoch
   in an owned firmware record. Device discovery records do not substitute for it.
4. Qualify fresh hardware/QPC sampling separately. No independent reference or
   second controlled node was available for calibrated synchronization validation.
5. Publish the reviewed source revision before claiming hosted CI for it. Existing
   PR-head checks cannot validate uncommitted work.
