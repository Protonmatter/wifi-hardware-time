# QMSL diagnostic queues: bytes, ownership and timing limits

**Later installed build:** [QMSL 6.1.365.1](qmsl-runtime-365.md) is now installed and independently traced. That report covers weak-name assembly binding, current callback/worker delivery and shutdown waits. Addresses and findings below retain their original 6.1.48.1 scope.

The supplied QDART installer contains an older, inspectable QMSL runtime. Its log getter copies queued bytes to caller storage, but the selected API does not accept a destination capacity, its timeout is not used by that implementation, and the managed wrapper has a smaller fixed buffer. These findings help define a future adapter; they do not establish a connection to this Surface's timing producer.

## Contents

- [Scope and identities](#scope-and-identities)
- [Single-record return](#single-record-return)
- [Batch getter changes logging state](#batch-getter-changes-logging-state)
- [Managed wrapper and timestamp display](#managed-wrapper-and-timestamp-display)
- [Transport and producer attribution](#transport-and-producer-attribution)
- [Implementation requirements](#implementation-requirements)
- [Reproduction and limits](#reproduction-and-limits)

## Scope and identities

Static inspection on 2026-10-05; no vendor DLL execution or device operation.
An RVA is an address relative to the beginning of a particular binary image.
Every address below belongs to the selected x86 library, not the ARM64 Wi-Fi driver.

| Component | Identity |
|---|---|
| QDART installer | `QDART-Connectivity1.0-00099.exe`, SHA-256 `e9b7cfd335f8f29c026023191656516b44041ff10ab2473c50d90b3f6726b1b8` |
| Native runtime | `QMSLFastConnect_MSVC10R.dll`, version 6.1.48.1, SHA-256 `e3db8a1d93ba762a9929604c37d9d45591187a6a1eae15cc29abb22505c71dd3` |
| Managed wrapper | `QC.QMSLFastConnect.dll`, assembly 6.1.48.1, SHA-256 `834f824d458ad03cc32183a195a0a38f5eb63581d6b9c6afbe68592b27a46a24` |
| WLAN transport | `QMSL_WLAN_Transport.dll`, version 6.1.48.1, SHA-256 `fc2d202a44cb7ba35b306a85f2fb2a29d547f3347b8ff4937b81c23deab8306e` |

The native DLLs are x86. The managed image has ILOnly metadata; its I386 PE field
alone does not establish its process-bitness requirements. Its selected P/Invoke
declaration names `QMSLFastConnect_MSVC10R.dll` and the C calling convention.

The [installed WLAN assembly inventory](qualcomm-archive-transport-findings.md)
recorded a dependency on 6.1.360.1. The newly supplied 6.1.48.1 library corrects a
broad absence assumption; it does not satisfy that exact version requirement.

## Single-record return

`QLIB_DIAG_GetNextPhoneLog`, RVA `0x119d30`, resolves the resource context and
calls `0x126ca0`. The selected implementation:

1. Uses the queue at context offset `+0x1068`.
2. Calls queue pop `0x136680`, which waits on its mutex with `INFINITE`.
3. Copies the front entry into temporary storage and removes it while locked.
4. Checks the returned 16-bit length against `0x3400` (13,312 bytes).
5. Copies that many bytes into the caller's destination and writes the length.

This is evidence of a copy into caller storage, rather than a borrowed queue
pointer. It is not complete size or concurrency qualification:

- No caller destination capacity is supplied or checked at the selected return.
- The `0x3400` check follows the queue-to-temporary copy. It cannot establish the
  safety of that earlier copy; producer bounds must be traced separately.
- The advertised timeout argument is unused by `0x126ca0`. A mutex wait can still
  block. A nominal timeout therefore cannot be used as a strict acquisition bound.
- An empty queue makes the internal pop return false. The outer caller length is
  not established as freshly updated on every failure; callers must ignore it
  unless success and validity are separately established.
- Popping consumes a record. Failed later validation does not restore it.

The selected producer helper `0x136610` holds the same queue mutex while the
`0x136430` helper copies a fixed `0x3402`-byte record container into owned storage.
It updates the count before unlocking and signals an event afterward. If the
configured queue limit is exceeded, it advances the oldest entry and reduces the
count. This establishes a pressure-drop branch, not a measured loss rate or an
application-visible loss counter. Cancellation and concurrent teardown remain open.

## Batch getter changes logging state

`QLIB_DIAG_GetMultipleLogs` (`0x11bac0` -> `0x1322a0`) is not a passive alternative:

- It calls `0x1304e0` with activation enabled before collecting records.
- That path queries the log range/current mask and can submit an updated mask.
- Its helper `0x12b6b0` builds DIAG command `0x73`; operation 3 is the selected
  set-mask path, while operations 1 and 4 query related state.
- The collection loop consumes queue entries, retaining only selected log matches.
  Other popped records are not restored by this loop.
- It uses `GetTickCount` for a host timeout loop. This is not a firmware timestamp
  or a bounded guarantee around the nested mutex waits.

These are static reachable operations, not live effects. Do not use this batch
getter for an experiment restricted to existing records and unchanged logging masks.

## Managed wrapper and timestamp display

File-only IL inspection of `QC.QMSLPhone.Phone.DIAG_GetNextPhoneLog` shows that it:

- Allocates a **2,046-byte** intermediate byte array.
- Calls the native getter with that array and a separate 16-bit result length.
- Tests the application array's length against `returned length - 4`.
- On the selected success branch, copies the **application array length**, not
  the returned record length, starting at source offset zero.
- Returns a Boolean; this public wrapper does not return the native record length.

The native getter's selected ceiling exceeds the managed intermediate capacity.
We have not established that the producer restricts every record to 2,046 bytes.
This is a static compatibility concern, not a demonstrated live overrun. An
application wrapper must not adopt this method as its complete-record contract.
Its actual marshalling, oversized records and failure behavior need separate tests.

`QC.QMSLPhone.LogMessage.getTimeStamp()` reads its timestamp field, shifts it right
by **16 bits**, multiplies by **0.00125**, then formats a time-of-day string. Thus:

- Lower-bit differences disappear before display.
- One increment of the retained integer represents 1.25 ms in this formatter.
- The formatter is unsuitable for retaining microsecond-scale distinctions.
- This does not establish the raw timestamp's clock, epoch, fine-bit meaning or
  relationship to TSF/QTIMER. Preserve the raw integer and its source schema.

## Transport and producer attribution

The WLAN transport's selected open path connects COM or IPv4 TCP, with default
TCP port 2390. Its local route can launch `Qcmbr.exe`; open is not passive lookup.
`UserDefinedReceive` supplies transport chunks, not a qualified firmware record.

The MSI File table contains 1,043 entries. It names Bluetooth, NFC and UWB bridge
executables, but no `Qcmbr.exe` or `FTM_DAEMON.exe`. Filename inspection of the
installed Qualcomm directories and available extracted research trees also found
no such executable. These are scoped searches; separately supplied or renamed
implementations remain possible. A bridge for another radio is not evidence of
a WLAN timing path.

The package's core header describes DLF replay feeding the log queue. A DLF is a
saved diagnostic-log file. The selected implementation confirms a file reader:
`QLIB_Playback_DLF` -> `0x127a20` -> `0x13f0c0` -> internal dispatch `0x13ec70`.
Queue availability alone cannot establish live-device provenance.

There is also a more useful application-copy lead: `QLIB_ConfigureCallBacks_V2`
(`0x11a9e0`) installs a binary-plus-JSON callback. The supplied header declares
binary length/pointer, JSON length/pointer, and a resource context. It requires
the application to copy callback buffers before their storage can change. JSON
is optional and described for QUTS mode; it is not itself a hardware-time record.

The receive router at `0x123dc0` invokes the callback with its original input
pointer/length and optional additional payload. Separately it can strip an
eight-byte `0x98` envelope when building the queue representation. Thus a callback
copy could preserve information that the single-log getter does not return.
The router has already built its internal copy before invoking the callback;
this observation does not establish safe handling of every malformed input.
No callback was registered or executed in this investigation.

Registration follows `0x11a9e0` -> `0x126610` -> `0x11e280`; the final setter
stores the callback at router `+0x7034` and resource context at `+0x7038`.
The shared dispatch constructor `0x160bd0` allocates/copies binary bytes;
`0x160c50` additionally allocates/copies the optional JSON bytes. Queue insertion
at `0x13eb20` constructs a `QpstEvent` object. That recovered class name does not
prove which live transport was selected. Allocation-failure, worker/listener
binding, deregistration and concurrent teardown still require qualification.

```text
Exact Wi-Fi timing producer?
         | missing adapter/record association
         v
Transport delivery              Saved diagnostic replay
         |                               |
         +---------------+---------------+
                         v
                  internal dispatch
                         ? worker/listener binding not closed in this trace
                         |
             +-----------+-----------------------+
             v                                   v
     original-byte callback              reduced queue record
             |                                   |
     copy during callback                 QMSL log queue
             |                                   |
             |                            locked copy + pop
             |                                   |
             +-----------------+-----------------+
                              |
                              v
                  application-owned bytes
                              |
                   validate complete source record
                              v
                 research observation / raw evidence

? = connection not established for this adapter.
No arrow establishes hardware-to-QPC conversion or clock accuracy.
```

## Implementation requirements

Before adopting this route, establish all of the following:

1. An exact adapter/transport connection and compatible runtime identity.
2. Producer bounds, record framing, loss and replay-versus-live provenance.
3. Capacity-safe copying with explicit valid length; no display-string conversion.
4. Cancellation and teardown that remain bounded when a native getter blocks.
5. A complete timing record with firmware schema and clock/event identity.

The [firmware diagnostic catalog](../tsf/firmware-trace-return-candidates.md)
defines message 25950 with candidate TSF/QTIMER/TQM and identity fields. It is not
an established DIAG log code accepted by `GetMultipleLogs`. WMI event IDs,
firmware catalog IDs and diagnostic log identifiers are different namespaces;
no translation between them has been demonstrated here.

Hardware-to-QPC sampling remains a separate requirement even after a complete
diagnostic record can be returned. The private acquisition campaign stays
quarantined under the [current qualification boundaries](../knowledge/current-findings.md#qualification-boundaries).

## Reproduction and limits

Private evidence resides in `artifacts/vendor-wcn785x-20261005/`:

- Input/member hashes and selected payload inventory.
- File-only managed metadata, IL and P/Invoke inspection.
- Selected native assembly and Ghidra exports; these are approximate analysis,
  not original vendor source or proof of runtime execution.
- Static archive/installed filename searches; not exhaustive product absence.

The authored [TraceQmslQueue.java](../../research/adapters/ghidra/TraceQmslQueue.java)
requires the pinned image hash, x86 language, Windows compiler specification and
image base `0x10000000`. It accepts one new private output directory and 1-32
explicit RVAs, exports at most 96 functions and rejects incomplete decompilation
or an instruction export that exceeds 4,096 instructions. Selected functions in
this pass fit that bound; no increase was needed. Per-function decompilation is
bounded at 90 seconds. No network, elevation or device access is required.

After importing the exact file into a separate Ghidra project, run this example
from the repository directory. Set the existing Ghidra/JDK paths for your host:

```powershell
$headless = '<Ghidra>/support/analyzeHeadless.bat'
$projectDirectory = '<private project directory>'
$newOutput = '<new private output directory>'
& $headless $projectDirectory QmslQueue `
  -process qmslfastconnect_msvc10r.dll -readOnly -noanalysis `
  -scriptPath (Join-Path (Get-Location) 'research/adapters/ghidra') `
  -postScript TraceQmslQueue.java $newOutput `
  119d30 126ca0 136680 1322a0 1304e0 11a9e0 11e280
```

The initial whole-image analysis used `-analysisTimeoutPerFile 1200` and completed
in 296 seconds. This is not an exhaustive correctness review of the product.
Require `WHT_TRACE_OK`, a receipt with zero failures, and complete exports; a
headless process exit code alone is insufficient. A rejected run can leave
partial output and must not be represented as complete. Retry into a fresh
directory; rollback removes only the selected private output, not vendor files.

Use the [static inspection runbook](static-inspection-runbook.md) for hash gates,
new output directories and private artifact handling. Do not execute the installer
or load the DLL merely to inspect it. Live framing, cancellation races, firmware
association, hardware sampling and synchronization accuracy remain unvalidated.
