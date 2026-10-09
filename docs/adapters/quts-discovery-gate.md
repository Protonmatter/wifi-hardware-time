# Why QUTS did not enumerate the Wi-Fi diagnostic endpoint

Ghidra located a concrete discovery requirement in the installed QUTS executable.
Its network-device path checks for a registry-advertised control endpoint, with a
Qualcomm composite-USB fallback. The active PCI Wi-Fi adapter has neither. This
explains a specific route by which it can be omitted from QUTS enumeration; it
does not establish that the Wi-Fi driver lacks private diagnostic capabilities.

<!-- research-history:2026-10-09 -->
**Research context (2026-10-09):** Scoped technical reference. Build-specific findings and operational prerequisites retain their stated scope. [Current account](../research-history/README.md) · [Timeline](../research-history/timeline.md) · [Previous version](../../archive/2026-10-09-pre-refresh-e9d71b8/pages/docs__adapters__quts-discovery-gate.md).
<!-- /research-history -->

**Later live validation:** [attempt 06](quts-live-gate-and-commonio.md) captured
12 failed queries on this adapter's driver key with the expected QUTS stack
addresses and all 20 positive controls. The static results below remain the
control-flow explanation; the following conditional instruction was not traced.

## Contents

- [Scope and identities](#scope-and-identities)
- [The discovered gate](#the-discovered-gate)
- [What protocol enumeration actually returns](#what-protocol-enumeration-actually-returns)
- [Independent source and historical log evidence](#independent-source-and-historical-log-evidence)
- [What this changes](#what-this-changes)
- [Reproduce in Ghidra](#reproduce-in-ghidra)
- [Validation and limits](#validation-and-limits)

## Scope and identities

This 2026-10-04 follow-up used file-only Ghidra analysis, existing log files and
read-only Windows device/registry queries. It did not start another QUTS session,
load a vendor DLL, open a private device, change registry values, enable logging,
restart services or adjust clocks.

| Input | Identity |
|---|---|
| `QUTS.exe` | Native ARM64, file/product version `3,96,2`; SHA-256 `8e6de10a298f8378e9d289ad11a33018654a29d155e56588f9427d53ed639297` |
| Active Wi-Fi driver | `qcwlanhmt8380.sys` version `1.0.4374.1300`, rechecked SHA-256 `ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115` |
| Source comparison | `QUD_Source_1.00.94.2.zip`, archive identity in the [archive report](qualcomm-archive-transport-findings.md#scope-and-provenance) |
| Tool | Ghidra 12.1.4, existing x64 JDK 21 setup; target language `AARCH64:LE:64:v8A`, Windows compiler specification |

RVA means an address relative to the image base. For this imported executable,
add `0x140000000` to an RVA to navigate in Ghidra. These addresses are not live
process addresses. Names inferred from strings and control flow are research
labels, not matching private debug symbols.

## The discovered gate

The enumerator at **RVA `0x0b3b58`** requests present Windows devices and examines
their setup classes. It explicitly recognizes `NET`, as well as processor,
ports, modem and selected USB classes. The claim that QUTS simply ignores every
network adapter would therefore be incorrect.

The selected network branch calls a routine at **RVA `0x0b2490`**, identified by
its `ValidateDevice` logging strings. It reads the device's driver registry key
under `SYSTEM\CurrentControlSet\Control\Class\<driver-key>`.

For a network-class device:

1. It reads `NetCfgInstanceId` and optionally `QCAdvertisedMtu`.
2. It queries **`QCDeviceControlFile`**. A successful query marks the device active
   for this discovery path. Presence alone is not a successful open or protocol test.
3. If that query fails, the selected fallback requires the device instance string
   to contain both **`VID_05C6`** and **`&MI_`**, identifying the expected Qualcomm
   composite-USB pattern.
4. Otherwise it writes false to the active output. A separate reset-state check
   can also clear that output for recognized Qualcomm-driver entries.
5. The caller checks the output before retaining the discovered device.

This is visible in ARM64 instructions, not only approximate decompiler C:

| RVA | Selected operation |
|---|---|
| `0x0b2ca4` | Forms the address of the `QCDeviceControlFile` name |
| `0x0b2ccc` | Calls the imported registry-query function |
| `0x0b2cd4` | Branches on successful query status |
| `0x0b2cdc` / `0x0b2cf8` | Prepares the two fallback substring checks |
| `0x0b2d14` / `0x0b2d1c` | Selects false / true |
| `0x0b2d28` | Stores that result through the active-output pointer |
| `0x0b5164` | Caller invokes `ValidateDevice` on the selected path |
| `0x0b5170` / `0x0b5174` | Compares the active output with one and skips retention otherwise |

A read-only query resolved the active adapter's own driver key through its PnP
property; it did not guess a numbered registry subkey. PnP is Windows Plug and
Play device identity.

| Current adapter observation | Result |
|---|---|
| Setup class and transport identity | `Net`, PCI |
| `NetCfgInstanceId` | Present, string |
| `QCDeviceControlFile` | Absent |
| `QCDeviceProtocol` | Absent |
| `QCDeviceStamp`, `QCDeviceGeneration`, `QCAdvertisedMtu`, `QCDeviceSSR` | Absent |
| Composite-USB fallback | Active PCI identity does not contain the required pair |
| Interface state | Up, same driver version |

**Interpretation:** the current metadata fails this recovered network discovery
gate. This is a static explanation corroborated by current registry observations.
No debugger captured the live process taking that branch, and other discovery
paths have not been exhaustively excluded. The pre-existing running-image
[attestation limitation](../evidence/quts-enumeration-2026-10-04.md#cleanup-and-identity-limits)
still applies.

## What protocol enumeration actually returns

The RPC `getProtocolList` block at **RVA `0x645f28`**, inside the full-analysis
function beginning at **`0x645f18`**, looks up an existing device
by handle through **`0x198968`**, then calls **`0x637e50`** to build the returned
list from that device's existing protocol objects. The selected path is not an
exhaustive probe of every Windows network adapter's private IOCTLs.

The `Unknown::createConnection` path at **RVA `0x2e9168`** checks an associated
object at `this + 0x358`. If present, it delegates through that object's virtual
call. If absent, it constructs the unknown-protocol error. The override routine
at **`0x1c0ca0`** and attachment routine at **`0x2ea058`** show that selecting a
protocol involves constructing/attaching a protocol object, not just changing
the display label. No override was executed in this investigation.

The earlier live result remains precise: two entries with unknown protocols and
no services, neither attributable to Wi-Fi. QUTS contains diagnostic machinery;
the missing demonstrated connection is from this Wi-Fi adapter to a usable
registered protocol instance. An unknown CPU or Type-C entry is not a substitute.

### A separate MHI DIAG path

The extended analysis recovered runtime type information (RTTI), which describes
C++ object types even without a matching PDB. The discovery worker at `0x1a64d0`
has a branch associated with `Discovered MHI Diag protocol`. MHI means Modem Host
Interface, a distinct host/device transport lead.

- The selected branch applies predicates through `0x1a2d58`, using string objects
  at RVAs `0x1894620` and `0x1894640`. Their initial file contents are empty C++
  string objects; their runtime initialization and exact matching expressions
  have not been traced. Empty file bytes do not establish empty runtime values.
- That branch calls `0x17fa18`, which allocates an object, calls `0x1dd3b8`, and
  assigns vtables identified by RTTI as `Rc::Heap<Device::Protocol::Diag>`.
- This establishes more than a DIAG-related string: a selected discovery branch
  reaches an actual diagnostic-protocol object construction pattern.
- It does not establish a matching MHI device for FastConnect, a connection to
  its timing producer, or a successful live record. The NET registry gate must
  not be generalized into a claim that every possible QUTS route is excluded.

The next bounded trace for this alternative is the initialization of those matcher
objects, the matched device metadata and the resulting connection implementation.
The subsequent [MHI route validation](quts-mhi-route-validation.md) resolves the
literal matcher initializers, maps description/parent inputs and traces the DIAG
connection factory. It preserves the remaining live-acquisition limits.

## Independent source and historical log evidence

The downloaded source contains `tools/qcdev/qclpc/scandev.cpp`. Its
`ValidateDevice` network branch performs the same registry check and USB fallback;
the caller only retains entries when `bActive` is true. `scandev.h` defines
`QC_SPEC_NET` as `QCDeviceControlFile` and the related registry field names.

| Comparison file | SHA-256 | Relevant source locations |
|---|---|---|
| `scandev.cpp` | `ccff0a47927327a161b8e44f0ce6c9eab15fe679b7e04cf7527ba85a0feb9eca` | `ValidateDevice`, approximately lines 995–1077; caller approximately 1737–1774 |
| `scandev.h` | `a3801258e7e594c249bfd8d73f5bb98fef9c95c77b2a479fb1db7f724f90cf30` | Registry names and device classes, approximately lines 52–89 |
| `qdpublic.h` | `1b15759df5a9d98b361bfc92dcb081daadf547ae5b34e088ea0b32537e80f750` | Internal discovery protocol constants, approximately lines 72–86 |

This is corroborating older source, not a source certificate for QUTS 3.96.2.
The modern binary has additional paths and fields. In particular, the older
discovery constants use `0x00` for unknown and `0x30` for DIAG; the Thrift RPC enum
uses `-1` for unknown and `0` for DIAG. These number spaces must not be conflated.

The same source tree's `QdIoQmi.cpp` makes the control-endpoint requirement concrete:
`QCWWAN_OpenService` opens a control file, sends `IOCTL_QCDEV_GET_SERVICE_FILE`,
then opens the returned per-service name for overlapped I/O. This is a distinct
QMI/WWAN transport contract. Its existence does not make the Wi-Fi driver's
private request format compatible, and none of these opens or IOCTLs was executed.

An existing compressed QUTS log from the 2026-10-03 startup records the CPU and
Type-C entries being added as unknown protocols, followed by available-state
transitions. That corroborates their placeholder interpretation; it is not a
new acquisition or a runtime trace of the Wi-Fi rejection branch.

The same historical log reports unavailable Connectivity and QDSS parsing licenses
during database loading. That is a separate operational lead. It does not prove
licensing caused the adapter's discovery omission or that raw acquisition requires
the same entitlement. No licensing state was changed or bypassed.

## What this changes

- **Supported:** a concrete network discovery contract is now located, and the
  active adapter lacks its selected control-endpoint advertisement.
- **Corrected:** neither the absence of a QUTS Wi-Fi entry nor a placeholder's
  available state establishes Wi-Fi diagnostic capability or incapability.
- **Still useful:** the separate exact-build `QcomWifi` private IOCTL path and
  firmware timing investigations remain valid leads. QUTS does not automatically
  wrap them merely because the device is Qualcomm-branded.
- **Next target:** identify an installed vendor WLAN transport or driver component
  that implements the required control endpoint, or implement a reviewed bridge
  to a demonstrated Wi-Fi event producer. Match its wire protocol and ownership
  contract before attempting acquisition.
- **Not an implementation:** creating `QCDeviceControlFile` manually would only
  change discovery metadata. It would not create an endpoint, implement DIAG/QMI,
  preserve an event or establish a clock relationship.

## Reproduce in Ghidra

Use the existing [Ghidra setup](ghidra-workspace.md). Keep databases, logs,
assembly and decompiler output private. The authored
[TraceQutsDiscovery.java](../../research/adapters/ghidra/TraceQutsDiscovery.java)
accepts only the pinned QUTS application/service hashes, ARM64 language, Windows
compiler and expected image base. Output directories must be new.

The whole-program analysis limit is **900 seconds**, increased from 180 at the
user's request. Each selected decompilation is limited to **120 seconds**,
increased from 20. These are separate limits; startup, import, exports and saving
add elapsed time. At most 32 seeds, 96 selected functions and 256 incoming
references per seed are accepted. Assembly exports default to 4,096 instructions;
`max-instructions:32768` raises the per-function export cap for the large discovery
worker, with an accepted range through 65,536. Truncation is always reported.

```powershell
# Use the actual existing project, verified Ghidra/JDK paths, and a NEW output.
$env:JAVA_HOME = '<verified-jdk-root>'
& '<ghidra-root>/support/analyzeHeadless.bat' '<private-project-dir>' QutsDiscovery `
  -process QUTS.exe -analysisTimeoutPerFile 900 -max-cpu 4 `
  -scriptPath '<repo>/research/adapters/ghidra' `
  -postScript TraceQutsDiscovery.java '<new-private-output>' `
  b2490 b3b58 637e50 198968 645f28 2e9168
```

After analysis, `-noanalysis -readOnly` permits bounded follow-up exports without
saving project changes. `entry:` explicitly permits defining a reviewed function
start in the analysis database if absent; these entry points were checked against
the pinned PE's ARM64 exception table. It does not patch executable bytes. Plain
hexadecimal seeds use existing functions/references. Unresolved seeds appear in
the receipt; zero selected functions now raises an error. Do not interpret the
headless process exit code alone as success: inspect the receipt and log.

## Validation and limits

The first 180-second analysis timed out and left incomplete function/reference
analysis. Its first string-seeded export resolved zero functions and is not
positive call-graph evidence. The script was corrected to reject that case.
Subsequent bounded passes used reviewed code entries and exported assembly and
approximate C, with per-function completion receipts. A wrong-image negative
check rejected the existing QPST image before creating output.
The corrected zero-function guard was exercised at header RVA `1` and rejected
the export without a success receipt. The first negative-test candidate, RVA
`0`, had a genuine incoming code reference and was therefore not a zero-function
fixture; its export and the failed test expectation are preserved privately.
An independent PE read matched eight decisive instruction sites against Ghidra's
export and confirmed the registry-query and substring-check import bindings.
The QUTS and Wi-Fi driver file hashes were rechecked in that pass.

The extended whole-program analysis **completed successfully in 826 seconds**
within the 900-second limit. Its first follow-up export correctly rejected an
explicit entry that overlapped Ghidra's now-established function boundary. A
read-only rerun using existing boundaries exported **22 completed decompilations**
with zero decompilation failures. Twenty-one assembly exports were complete;
the large discovery worker at `0x1a64d0` was explicitly truncated at 4,096
instructions. Its decompiled C was exported, but this is not complete assembly
review of that worker. The selected network gate's assembly export is complete.
A six-function read-only MHI follow-up also completed all decompilations; its
duplicate export of the same large worker retained the same explicit assembly
truncation. The three selected helper exports were complete.

Private artifacts are under ignored `artifacts/quts-ghidra-discovery-20261004/`:
input hashes, source hashes, per-pass script snapshots, Ghidra project/logs,
candidate references, selected function exports, registry observations and
historical-log selections. Proprietary source, binaries and endpoint identifiers
are not copied into public documentation.
The 14 documentation/layout/index/diagram checks passed, the generated index was
refreshed and checked, and `git diff --check` passed. Final Wi-Fi observation
remained Up on driver `1.0.4374.1300`. No commit, push or hosted CI run was made
for this follow-up.

Decompiler warnings and missing matching PDB symbols remain. The decisive gate
was checked against ARM64 assembly and the older source, but the complete program
and every indirect caller have not been qualified. No fresh diagnostic record,
firmware-event association, server-side concurrent-copy contract, hardware-to-QPC
sampling or timing accuracy was established by this pass.
