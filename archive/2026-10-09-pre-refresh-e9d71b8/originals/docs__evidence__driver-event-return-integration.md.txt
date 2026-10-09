# Connecting a driver-owned event to an application

The application broker already returns independently owned replay bytes. The next component must copy a real receive event inside the driver and deliver it through a separately defined interface. We have now traced the existing notification queue's creation, success completion and shutdown drain. That is a useful implementation reference, but it still carries one state byte and is not connected to the TSF producer.

The subsequent [live device-service control](device-service-positive-control.md)
now demonstrates a separate eight-byte return through the installed driver. Its
source is a fixed test pattern; the source-copy and timing requirements below remain.

The [complete-event hardware handoff](complete-event-hardware-handoff.md) records
the latest installed-file check and the concrete vendor-interface or instrumented
producer deliverable. QUTS RawService still requires an attributable protocol;
its interface declaration does not create that connection.

## Contents

- [What the exact driver establishes](#what-the-exact-driver-establishes)
- [Two queues with different owners](#two-queues-with-different-owners)
- [Required producer and response contract](#required-producer-and-response-contract)
- [Cancellation and shutdown](#cancellation-and-shutdown)
- [Implementation gates and acceptance tests](#implementation-gates-and-acceptance-tests)
- [Repeat the static inspection](#repeat-the-static-inspection)
- [Glossary](#glossary)

## What the exact driver establishes

This is a **2026-10-05 static follow-up**, using the same ARM64 INF/package driver
version `1.0.4374.1300` and SHA-256 documented in the
[WLANLIB dispatch investigation](../adapters/wlanlib-dispatch-and-completion.md#scope-and-identities).
The SYS resource's separate `FileVersion` is `1.0.0.17731`; the hash pins the actual file.
Addresses are relative virtual addresses (RVAs), not live kernel pointers.
The selected Ghidra decompilations were checked against ARM64 instructions.

| Location | Observed operation | What this establishes |
|---|---|---|
| `0x436cf0`–`0x436e50`, inside device creation | Create manual, non-power-managed queue at device context `+0x3c0`; create wait lock at `+0x3c8`; both parented to the WDF device | A concrete pending-request queue and its selected lock |
| `0x11bfb8` | Nonzero input to `0x81802c04` forwards the request to that queue | Existing asynchronous state-notification operation |
| `0x11c6e0` | Check queue state/count and schedule `0x11bd90` | Work scheduling for the state notification |
| `0x11bd90` | Retrieve one request under the wait lock, release the lock, write the boolean and complete with one byte | A bounded output-copy/completion pattern after request retrieval |
| `0x11c4d8` | Retrieve under the same lock, release it, complete with supplied status, repeat until retrieval fails | Explicit forced completion of pending requests |
| `0x329e8` and `0x36c90` | Selected deinitialization and suspend branches call that drain with `0xc00002b6`, `STATUS_DEVICE_REMOVED` | Error completion is part of selected lifecycle paths |
| `0x31188` → `0x11c640` | Adapter termination reaches freeing and clearing the Qmux context | Located context release; not a complete callback-rundown proof |

Important distinctions from this trace:

- The manual queue's configuration has zero callback fields, including its
  canceled-on-queue callback. Its parent relationship does not establish a
  hardware shutdown order or a particular callback execution level.
- After the forced drain, the selected callers invoke
  `WdfIoQueuePurgeSynchronously` on **`+0x3b0`**, a different power-managed queue.
  Do not attribute that purge to the notification queue at **`+0x3c0`**.
- The forced-completion routine itself does not stop new queue admission or
  join producer callbacks. We have not proven the complete surrounding lifecycle.
  This is a limit of the trace, not a demonstrated live race in the vendor driver.
- The conditional suspend branch is identified statically. No suspend, adapter
  reset or cancellation race was executed in this follow-up.

Framework table offsets include queue creation `+0x4c0`, queue state `+0x4c8`,
request retrieval `+0x4f0`, synchronous purge `+0x520`, status-only completion
`+0x838`, completion with byte count `+0x848`, forwarding `+0x8c8`, and wait-lock
create/acquire/release `+0x9c0/+0x9c8/+0x9d0`. These map to Microsoft's
[KMDF function-index definitions](https://github.com/microsoft/Windows-Driver-Frameworks/blob/main/src/publicinc/wdf/kmdf/1.27/wdffuncenum.h).
The queue fields are interpreted using its
[public queue structure](https://github.com/microsoft/Windows-Driver-Frameworks/blob/main/src/publicinc/wdf/kmdf/1.27/wdfio.h).

## Two queues with different owners

The following is the **proposed adapter**, not an installed implementation.
It separates received data from application requests so a slow or canceled
application cannot retain a borrowed receive buffer.

```text
PRODUCER SIDE: inside vendor-supported / instrumented driver

Copy point A or B, while receive storage is still valid
    |
    | Check source spans, coherency, identity and admission generation
    v
Copy complete event into an adapter-owned nonpaged slot
    |
    | Finish payload + metadata BEFORE making the slot visible
    v
Ready-event queue ---------------------+
                                      |
APPLICATION SIDE                      v
Read request -> WDF manual queue -> Delivery worker
                WDF owns waiting      | Pair one owned event and one request
                request               | Copy exact bytes into request output
                                      v
                              CompleteWithInformation
                                      |
                                      v
                         Application owns returned bytes
                                      |
                                      v
                         Validate driver response envelope
                                      |
                                      v
                       Native broker / application decoder
```

**Legend:** solid arrows describe the proposed ownership transfers. The
[current broker](raw-event-response-broker.md) implements only the user-mode
portion. An **owned** event remains valid independently of the producer buffer;
a copied pointer or wrapper does not satisfy that requirement.

## Required producer and response contract

**Working rule:** qualify the complete operation—entry route, framing, selector
precedence, state effects, producer, returned bytes and completion meaning.
The eight-byte device-service control is positive evidence for its exact return
path. Each timing operation needs its own qualification. The nested IHV
query/control investigation is deferred exploratory work, not the next active
clock integration step.

1. **Establish an integration point.** Use driver source, a supported vendor
   callback/export, or another demonstrated complete-event interface. A companion
   driver cannot reach a private callback merely by attaching to the device stack.
   Existing Qmux selectors keep their one-byte ABI; this design does not patch them.
2. **Validate the source before copying.** At
   [copy point A or B](../tsf/hif-receive-buffer-producer.md), establish actual
   allocation capacity, data offset, received count, fragment layout and callback
   lifetime. Check `offset <= capacity` and `count <= capacity - offset`.
   Reject an unknown or invalid span rather than truncating it.
3. **Establish DMA coherency.** A call to the inspected cache helper is insufficient
   when its fallback allocation can fail without a returned status. The adapter
   needs a producer contract that demonstrates successful synchronization for the
   actual buffer. A caller-supplied boolean cannot manufacture that guarantee.
4. **Keep the entire event.** Copy transport header, original payload and applicable
   trailer before normalization or reuse. Preserve declared and actual extents,
   endpoint/pipe and source identifiers. Reject unsupported fragmentation until
   its full assembly contract is demonstrated.
5. **Publish atomically to readers.** Preallocate bounded nonpaged storage appropriate
   to the measured callback execution level. Finish every field before advertising
   a ready entry using a reviewed synchronization mechanism. The user-mode broker's
   process lock is not a kernel or DMA synchronization primitive.
6. **Account for loss and discontinuity.** Track local overflow, rejected copies and
   source-reported loss separately. If firmware loss is not observable, report it
   as unknown, not zero. Latch continuity failures even if there is no later payload
   on which to attach the status. Stop admission on unknown continuity until reviewed.
7. **Define the driver response envelope.** Include version, exact returned length,
   driver/firmware provenance, device/source identity, copy point, software session
   and generation, event ordinal, loss status and original bytes. Explicitly label
   unknown clock domain, units, meaningful bit width, request association and
   sampling instant. Those unknowns permit diagnostic retention, not clock admission.
8. **Keep host observations honest.** If QPC is read at callback entry/copy completion,
   label those moments. They bound host handling only until fresh firmware sampling
   and association are proven. Neither completion nor arrival establishes a latch.

The broker's existing `WHTR` version 1 envelope lacks the complete driver-source
contract above and accepts only fixture/unqualified-replay provenance. Integration
must define and validate a source envelope and its consumer before accepting live
data. Do not relabel live data as a fixture or infer missing fields from application
tickets. A software generation identifies admission continuity; it is not a
hardware clock epoch.

The [source-operation record layer](source-operation-record.md) now implements
that packaging boundary for diagnostic fixtures and saved replay. It preserves
explicit unknowns and rejects mismatched operation/source metadata through the
native broker. It does not add a live producer or change the required driver-side
validity, ownership and sampling contract.

## Cancellation and shutdown

**Waiting requests:** forward a validated read to a manual WDF queue belonging to
the same device. After successful forwarding, WDF owns and can cancel it. A failed
forward leaves completion with the driver. Do not touch a successfully forwarded
request, and account for framework reentrancy before the forwarding call returns.
These rules come from Microsoft's
[forwarding contract](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdfrequest/nf-wdfrequest-wdfrequestforwardtoioqueue).

**Delivery:** serialize event selection and request pairing in one delivery worker.
Retrieve a request only when a complete owned event is ready. After
[successful retrieval](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdfio/nf-wdfio-wdfioqueueretrievenextrequest),
the driver owns it: validate capacity, copy bounded bytes and complete once with
the exact initialized byte count. If output is too small, retain the event and
return a defined size error; never publish a successful partial event.
Schedule delivery on both request arrival and event publication, with a synchronized
worker-state handshake that cannot miss a wakeup between its final check and exit.

**Cancellation races:** cancellation can win while WDF owns the waiting request;
after retrieval, immediate bounded completion can win instead. The application must
observe the actual completion result before freeing its output storage. If a design
holds a retrieved request for further asynchronous work, it additionally needs
the cancellation/normal-completion arbitration required by
[WdfRequestMarkCancelableEx](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdfrequest/nf-wdfrequest-wdfrequestmarkcancelableex).
Do not add an unbounded firmware wait after retrieval.

**Shutdown order required for the new adapter:**

- Close producer and request admission under a defined lifecycle gate.
- Unregister or stop the producer and wait for already-entered callbacks to leave.
- Cancel queued requests and settle any request already claimed by the delivery
  worker; do not wait while holding a lock that worker or cancellation requires.
- Join delivery work, account for/discard remaining events, then release storage.
- Handle per-file cleanup separately so closing one client cannot expose or
  discard another client's data. Define quotas, access control and single-client
  versus multi-client delivery before opening an interface.

[WdfIoQueuePurgeSynchronously](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdfio/nf-wdfio-wdfioqueuepurgesynchronously)
can help cancel and wait for requests, but requires `PASSIVE_LEVEL` and must not
be called from the listed I/O request handlers. It does not join an arbitrary
firmware callback or prove firmware drain. A teardown deadline expiring must report
failure and retain still-referenced storage; it cannot justify freeing live memory.

## Implementation gates and acceptance tests

The current environment has a user-mode ARM64 compiler and Windows SDK. The
inspected SDK installation has no `km/ntddk.h` or WDF kernel headers. A kernel
implementation additionally needs an appropriate WDK, an actual producer integration
mechanism and a separately reviewed test/signing/deployment path. Installing build
tools alone would not connect the Qualcomm callback.

| Test | Required evidence before promotion |
|---|---|
| Source lifetime | Overwrite/recycle original storage after copy; application bytes remain unchanged |
| Publication | Concurrent producer/readers never observe partial metadata or payload |
| Bounds | Bad capacity/offset/count, fragment and trailer cases rejected without partial return |
| Pressure | Every overflow/rejection counted; unknown source loss visibly invalidates continuity |
| Cancellation | Cancel before/at/after retrieval; exactly one terminal completion and no stale buffer access |
| Shutdown | Stop with pending requests and callbacks; no new admission, no missed completion or use after free |
| Client cleanup | Closing one handle releases only its requests/state; late completion cannot reuse freed storage |
| Timing meaning | Independently establish clock identity, units, producer association and sampling semantics |

The existing native broker tests cover the analogous **user-mode software** cases.
They are valuable reusable tests, but do not execute WDF, DMA, the private firmware
path or hardware-to-QPC correlation. No kernel adapter or new live export is claimed.

## Repeat the static inspection

Use the existing [WLANLIB inspection command](../adapters/wlanlib-dispatch-and-completion.md#repeatable-inspection).
Its receipt now includes `pending_request_lifecycle`: selected instruction checks,
two drain-status literals, distinct queue offsets and false live-qualification flags.
No device is opened and no elevation is required. The command retains its existing
input/output bounds, refusal to overwrite and exit codes.

Ghidra seeds for this follow-up:

- `436000 11bd90 11c640`: setup, success completion and context free.
- `11c558 11c764 297ff0`: bounded drain/scheduling functions and identifying string.
- `11c4d8 11c640`: direct callers of drain and free.

Private exports and receipts are under
`artifacts/driver-response-continuation-20261005/`. Three bounded passes completed
with zero decompilation failures and complete selected instruction exports.
The repeatable inspector checks exact bytes/scalars; the full lifecycle interpretation
remains manual, and indirect-call coverage is not exhaustive.

This follow-up follows published commit `6f6ed8c`. That commit's successful hosted
CI does not validate these later edits; the containing revision's checks are
tracked separately in [PR #3](https://github.com/Protonmatter/wifi-hardware-time/pull/3).

Local validation for this follow-up:

- `python -m compileall -q research tests`: passed.
- `python -m unittest discover -s tests -v`, with the installed ARM64 compiler and
  hash-pinned owned driver/Windows fixtures configured: **300 tests, zero skips**.
- Focused WLANLIB suite: six tests passed, including altered-instruction and
  status-literal rejection with the outer hash gate bypassed only inside the test.
- Offline inspector: receipt written from the exact driver; no device opened.
- Documentation links, workflow-source consistency, generated indexes and
  `git diff --check`: passed at this checkpoint.
- Read-only adapter check: active Wi-Fi remained Up, version `1.0.4374.1300`.
  No elevation, private request, reset, suspend or firmware change was performed.
- Independent review found no P0/P1/P2 defects or material qualification overclaims.
  Its two minor suggestions were applied: assert all 13 instruction checks remain
  present, and distinguish the package version from the SYS resource version.

## Glossary

- **WDF / KMDF:** Microsoft's framework for managing kernel driver objects and requests.
- **Nonpaged storage:** memory available without paging it in from disk.
- **DMA coherency:** making device-written memory reliably visible to the CPU.
- **Publication:** the point at which a fully initialized record becomes visible to a reader.
- **Rundown:** stop new work and wait until existing users release access before freeing data.
- **ABI:** the exact calling and data-format agreement between components.
- **QPC:** the host performance counter; its relationship to a radio clock must be measured.
