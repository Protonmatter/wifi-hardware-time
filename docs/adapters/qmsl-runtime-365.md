# Installed QMSL 6.1.365.1: binding, callbacks and transport

The completed installation supplies a current x86 QMSL runtime and QSPR 6.0 interfaces. File-only inspection narrows the earlier version concern: the relevant assemblies and references are not strong-named, so their different version numbers alone do not require binding redirects. The new native callback path is located, while log getters retain important size and blocking limitations. No vendor library was executed or connected to the Wi-Fi adapter.

<!-- research-history:2026-10-09 -->
**Research context (2026-10-09):** Scoped technical reference. Build-specific findings and operational prerequisites retain their stated scope. [Current account](../research-history/README.md) · [Timeline](../research-history/timeline.md) · [Previous version](../../archive/2026-10-09-pre-refresh-e9d71b8/pages/docs__adapters__qmsl-runtime-365.md).
<!-- /research-history -->

## Scope and provenance

Inspection date: 2026-10-06, America/New_York. These findings apply to the exact files below. Native addresses are RVAs relative to image base `0x10000000`; they are not live pointers or supported invocation recipes.

| File | Current identity | SHA-256 |
|---|---|---|
| `QMSLFastConnect_MSVC22R.dll` | Native x86, file version 6.1.365.1 | `437efd33f33b64295375a1f44b272704ee3902a8c908b8147b7de7ba5988f15e` |
| `QC.QMSLFastConnect.dll` | Assembly 6.1.365.1; ILOnly, Requires32Bit; .NET Framework 4.7.2 | `bd061688884f2bc737b4342aa843ad504705029ac7f36c409c88d8d24fe23b2e` |
| `QC.CTE.WLANTestSuite.dll` | Assembly 2.0.79.1; ILOnly, Requires32Bit | `33a982738130e42164ae9481e5cad9c0d4a316e48779a5c7d3c534718345c19f` |
| `QTMDotNetKernelInterface.dll` | Assembly 6.0.0.0; ILOnly, Requires32Bit | `1908f91694597a07f9e442442f3ac004b73f6b41eb0b17125f41ff6dee059825` |
| `QTMInterface.dll` | Assembly 6.0.0.0; ILOnly | `c7c713e09fc50e9d3651be3d4b8151a5a1f57cc3734305730680c120ec271e91` |

The older [6.1.48.1 investigation](qmsl-diagnostic-queue.md) remains historical evidence. This pass independently inspected the new image; matching names or similar behavior do not justify copying old RVAs.

## Managed binding and the 32-bit host

WLAN 2.0.79.1 references QMSL 6.1.360.1, QTMDotNetKernelInterface 5.1309.8481.20772 and selected TILIB assemblies at 2.0.90.1. Their inspected reference records contain no public-key token. The inspected WLAN/QMSL/QSPR assembly definitions also contain no public key or StrongNameSigned flag.

.NET Framework does not check assembly versions for assemblies without strong names. Therefore the metadata version differences, and absence of corresponding binding redirects in `QSPR.exe.config`, do not establish a loader failure or a need to edit the configuration. This conclusion follows from the observed metadata and Microsoft's [assembly-resolution contract](https://learn.microsoft.com/en-us/dotnet/framework/deployment/how-the-runtime-locates-assemblies). File location, dependency availability and API compatibility still matter.

The inspected QSPR loading chain is:

```text
TestKernelManager.LoadDotNetTest
    -> DotNetKernel.LoadTestDLL
        -> loadTestAssembly / TestAssembly constructor
            -> Assembly.LoadFrom
            -> GetAssemblyAttributes / GetTypes
```

`LoadTestDLL` also contains license/error handling and architecture diagnostics. This is an actual loader implementation, not proof that this WLAN plugin has loaded successfully. No license validation or vendor startup was executed.

A bounded metadata comparison found **149 direct, non-nested QMSL method references** in the WLAN assembly, with every referenced type/method name present in the new managed QMSL assembly. Overload signatures, nested/generic resolution, field compatibility, transitive dependencies and runtime behavior were not qualified by this name check.

An authored x86 .NET Framework smoke program ran successfully with four-byte pointers under CLR `4.0.30319.42000`. It referenced no vendor assembly. This proves a 32-bit CLR process can run on this host, not that QSPR/QMSL loading, entitlement or hardware access works. The managed/native QMSL path must not be loaded into an ARM64 process.

## Concrete connection paths

The current managed QMSL P/Invoke declarations for the inspected connection, getter and legacy callback methods name `QMSLFastConnect_MSVC22R.dll` with C calling convention. The native DLL exports V2 callback registration, but no dedicated V2 declaration appeared in the inspected managed method-name/P/Invoke selection. A native export does not automatically become a supported managed API.

WLAN `DutCommon.ConnectQUTS` selects library mode 2, sets target/debug/receive-timeout parameters, requests available device/protocol handles, chooses a result and calls `connectToServerWithWaitByHandleID`. The current native path is:

| Step | Selected implementation |
|---|---|
| Enumerate handle list | `QLIB_GetAvailablePhonesHandleIDList` `0x109ab0` -> `0x1207f0` |
| Obtain QUTS service object | `0x11f390`; installs `Quts::CService` vtable `0x49aa9c` |
| Enumerate via service | Slot `+0x4c` -> `0x11f190` -> `0x1272c0` -> `0x146020` |
| Connect by existing handles | `QLIB_ConnectServerWithWaitByHandleID` `0x107a40`; service slot `+0x50` -> `0x11fb10` -> `0x127480` -> `0x145490` |

The service object's construction can initialize its client state; it must not be classified as passive file lookup. The handle connection includes polling, context initialization and cleanup branches. An advertised wait parameter is not proof that every nested operation is bounded.

This chain still requires discovered device/protocol identities. It does not supply a new mapping from the current PCI Wi-Fi adapter to QUTS, nor a connection from the firmware TSF event to a diagnostic record. The earlier [QUTS discovery findings](quts-live-gate-and-commonio.md) remain relevant; installing QMSL alone does not reverse them.

The separate `ConnectUserTransportDLL` route checks for a DLL and calls `LoadUserDefinedTransportLibraryAndConnectDUT`. That implementation resolves five names: `OpenUserDefinedTransport`, `UserDefinedSend`, `UserDefinedReceive`, `UserDefinedFlushTxRx`, and `CloseUserDefinedTransport`, then opens the transport. A filename search in the three Qualcomm installation roots found no `QMSL_WLAN_Transport.dll`, `Qcmbr.exe` or `FTM_DAEMON.exe`. This is bounded filename evidence, not proof that every alternative transport is absent.

## New-build getter and callback findings

| Boundary | 6.1.365.1 finding | Consequence |
|---|---|---|
| Managed `Phone.DIAG_GetNextPhoneLog` | Allocates 2,046 bytes; selected success branch copies the application array length; returns a Boolean rather than actual record length | Remains unqualified as a complete-record adapter |
| Native getter `0x1083b0` -> `0x111ae0` | Queue is at context `+0x1064`; accepts returned length up to `0x3400` and copies it to caller storage; no destination capacity | Size restriction must be established before using the managed wrapper; no live overrun is claimed |
| Getter timeout | Selected `0x111ae0` does not read its third stack argument; returns with `RET 0xc` | The timeout does not bound this implementation |
| Queue pop `0x130780` | Mutex wait uses `INFINITE`; copies and consumes the selected record | Blocking and destructive dequeue semantics remain explicit |
| Batch getter `0x1082e0` -> `0x111650` | Reaches `0x1122e0` with activation enabled before collection; consumes nonmatching records | Do not use it as an existing-record-only passive getter |
| V2 callback registration | `0x107740` -> `0x1103a0` -> `0x1313b0`; stores callback/context at listener `+0x7034/+0x7038` | Concrete registration path, not live delivery proof |
| Listener callback invocation | `0x135f60` invokes V2 with original binary length/pointer, additional payload arguments and resource context | Copy within the valid invocation lifetime; context is not firmware transaction identity |

The listener separately prepares a queue representation that can remove an eight-byte `0x98` envelope before invoking the callback with the original pointer. Its initial selected length checks permit 2 through `0x3400` bytes, so this pass does not establish a safe short-envelope input contract. No malformed packet was submitted. The callback cannot repair an earlier internal copy; upstream validity remains a separate prerequisite.

The 13,312-byte native ceiling and 2,046-byte managed allocation are independently reconfirmed in this build. Producer restrictions and actual marshalling would need qualification before calling that wrapper. No live memory error or exploitability claim is made.

## Worker-to-listener delivery and shutdown

The new image closes the selected software worker/listener connection:

```text
Diag_FTM constructor 0x10e7b0
    -> listener at context +0x10d0 (constructor 0x130f40)
    -> CQLibEvents at context +0x103c (constructor 0x128f60)
    -> register listener, vtable slot +4 -> 0x129650
        -> worker thread 0x129720
            -> transfer event payload ownership with 0x155d20
            -> pop old queue entry with 0x1298c0
            -> registered listener vtable slot +4
                -> CQLibEventListener table 0x4bb4e4
                -> router 0x135f60
                    -> V2 callback stored at listener +0x7034
```

This worker path does not make another deep copy at dequeue. `0x155d20` transfers binary/additional-payload pointers and lengths into its working event, clears the source ownership flag at `+0x1c`, and marks the destination as owner before the queue entry is popped. Application code still needs its own copy while the callback bytes remain valid. This establishes a selected software transfer mechanism, not a complete proof of every producer, allocation-failure or malformed-record path.

The worker holds the listener-list critical section during dispatch. Listener removal at `0x129900` uses that same critical section and removes a matching entry. That is meaningful synchronization evidence for the selected path; it is not a complete teardown guarantee, and callback reentrancy/registration replacement remains unqualified.

Two waits constrain an adapter design:

* Registration `0x129650` starts the worker and waits indefinitely for its ready event.
* Stop `0x129980` signals stop/wakeup, waits **1,000 ms**, then on a nonzero wait result waits indefinitely for an event and the thread handle. The first one-second wait is therefore not a bounded shutdown contract.

The selected event/listener destructors are located at `0x129160` and `0x131250`. Full caller ordering, pending producer callbacks and safe live cancellation still need qualification. No thread was created or stopped in the vendor runtime during this investigation.

## Reproduce the exact-build trace

The updated [TraceQmslQueue.java](../../research/adapters/ghidra/TraceQmslQueue.java) accepts only the two pinned x86 builds, with Windows compiler specification and image base `0x10000000`. It records the selected image version. Existing argument, function, reference, instruction, timeout and no-overwrite limits remain unchanged.

After importing the new exact image into a separate private Ghidra project:

```powershell
$headless = '<Ghidra>/support/analyzeHeadless.bat'
$project = '<private project directory>'
$out = '<new private output directory>'
& $headless $project Qmsl365 -process QMSLFastConnect_MSVC22R.dll `
  -readOnly -noanalysis `
  -scriptPath (Join-Path (Get-Location) 'research/adapters/ghidra') `
  -postScript TraceQmslQueue.java $out 107740 1083b0 111ae0 1313b0 135f60
```

Choose separate passes for other seeds when necessary. A whole-image import used `-analysisTimeoutPerFile 1200 -max-cpu 4`; Ghidra reported 369 seconds of analysis. Whole-image analyzer warnings do not negate complete selected exports, but selected success is not exhaustive program correctness. Require `WHT_TRACE_OK`, zero receipt failures and complete selected assembly/decompilation outputs.

Use the [static inspection wrapper](static-inspection-runbook.md) for preview/apply/unchanged file inventories and the existing file-only metadata/IL tools for managed evidence. Keep all vendor bytes, raw exports, local paths and identifiers private. No installer, application, firmware request, logging mask or system-clock change is part of this recipe.

## Qualification boundary

Validation in this pass: 11 successful new-build trace passes exported 103 distinct functions; 26 repeated assembly exports matched. The original helper first rejected the new image. The updated helper passed the old-build regression and rejected an unknown image and an existing output directory without replacing its receipt. The configured repository suite passed all 340 tests with zero skips; Python compilation, 33 PowerShell parser checks, knowledge-index checks, workflow-embed synchronization and whitespace checks passed. These are local results; no new hosted CI or live acquisition ran.

The new installation makes a current runtime available for investigation. It does not establish live Wi-Fi attribution, complete timing-event delivery, safe cancellation, firmware drain, hardware-to-QPC sampling or synchronization accuracy. The private acquisition quarantine is unchanged. The next operation still needs the [complete-event hardware handoff](../evidence/complete-event-hardware-handoff.md).
