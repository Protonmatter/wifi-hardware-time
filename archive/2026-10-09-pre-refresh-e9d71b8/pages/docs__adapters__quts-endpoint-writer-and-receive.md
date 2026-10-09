# QUTS endpoint construction and receive ownership

> **Archive — not current operating instructions.** Historical documentation at [e9d71b843651](https://github.com/Protonmatter/wifi-hardware-time/commit/e9d71b84365122ff2640e240b20fc1dbb834388a). Relative links are rebased for reading. [Exact original bytes](../originals/docs__adapters__quts-endpoint-writer-and-receive.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

We located the writer of QUTS's stored endpoint path and followed a real receive
path into separately owned byte buffers. The endpoint comes from device discovery
and registry validation; received data is divided into transport chunks before
protocol decoding. This closes two static-analysis gaps. A live FastConnect
endpoint, complete firmware record and bounded cancellation behavior remain unproven.

## Contents

- [Scope and evidence](#scope-and-evidence)
- [Where the endpoint comes from](#where-the-endpoint-comes-from)
- [How received bytes become owned chunks](#how-received-bytes-become-owned-chunks)
- [Cancellation and completion](#cancellation-and-completion)
- [Where record boundaries belong](#where-record-boundaries-belong)
- [Reproduce the trace](#reproduce-the-trace)
- [Next experiment and glossary](#next-experiment-and-glossary)

## Scope and evidence

This is an offline follow-up to the [qualified discovery-query capture](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/quts-live-gate-and-commonio.md).
It inspects the same ARM64 `QUTS.exe`, version `3,96,2`, SHA-256:

```text
8e6de10a298f8378e9d289ad11a33018654a29d155e56588f9427d53ed639297
```

Ghidra 12.1.4 reused the analyzed project in read-only mode. Function names below
come from embedded diagnostic text, recovered C++ type information and inspected
call relationships. They are not matching private PDB symbols. Critical endpoint
stores and helper calls were checked against ARM64 instructions as well as the
approximate C output.

No diagnostic endpoint was opened, vendor API executed, read cancelled, or
firmware command sent in this pass. A final Windows adapter-state query still
reported Wi-Fi **Up** on driver **1.0.4374.1300**. This pass does not repeat the
earlier live registry experiment or establish a live receive result.

All addresses below are **RVAs**: offsets relative to the executable's base.
The imported Ghidra base is `0x140000000`. Structure offsets refer to the named
object; the same numeric offset in another object is unrelated.

## Where the endpoint comes from

The writer is in `ScanDevices`, RVA **`0x0b3b58`**. It uses Windows SetupAPI to
enumerate devices, obtains the driver registry-key name and device instance ID,
and passes them to `ValidateDevice` at **`0x0b2490`**.

For the selected network-class path:

1. `ValidateDevice` queries `QCDeviceControlFile` into its temporary UTF-16
   buffer at RVA `0x192d1f0`.
2. The previously traced admission rule checks the query result and its specific
   composite-USB fallback. The enumerator checks the resulting active flag at
   `0x0b5170` / `0x0b5174`, before constructing the published entry.
3. On a successful network control-name result, the return logic at
   `0x0b2eb4`–`0x0b2f00` selects the final name component after a backslash when
   present. This is an observed implementation, not a general path-normalization API.
4. The enumerator writes the `\\.\` prefix into entry **`+0x894`**, then appends
   the returned control name. The relevant stores are at `0x0b5640`–`0x0b5748`.
   Its null-result alternative appends the discovered description. That
   alternative does not bypass the earlier active-device check.
5. It terminates the wide string within a 512-character destination and creates
   a narrow-character companion at **`+0xc94`**.

The temporary validation buffer is therefore copied into the discovered entry;
the stored endpoint is not merely a pointer into that temporary buffer.

```text
One SetupAPI device
    | driver registry key + device instance ID
    v
ValidateDevice
    | QCDeviceControlFile result + active flag
    v
Admission check ------------------ rejected device: no entry from this branch
    | admitted
    v
Build endpoint: \\.\ + returned control name
    | copy characters into entry +0x894
    v
Reconcile discovered-device lists
    | publish descriptor pointers to entry-owned strings
    v
CommonIo transport -> QcDevice::OpenDevice -> CreateFileW
```

Arrows show the inspected static path. They do not claim that the active Wi-Fi
adapter traversed the admitted branch.

The same enumerator calls `SetupDiGetDeviceInstanceIdW` and distinguishes `USB\`,
`PCI\` and `QC_BUS\` instance strings. It also obtains hardware/location metadata
and logs the description with the instance ID. A description alone is therefore
insufficient for physical-device attribution.

The reconciliation routine at **`0x0b0830`** compares the description, endpoint
and additional identity/state fields. Before its callback, it publishes pointers
to strings held inside the entry:

| Descriptor pointer field | Backing storage in the entry |
|---|---|
| `+0x28` | Description at `+0x94` |
| `+0x30` | Endpoint path at `+0x894` |
| `+0x38` | Selected network metadata at `+0x2494` |
| `+0x40` | Location-related string at `+0x1c94` |

These are internal callback pointers. Copying the descriptor alone does not own
its strings. Any future application export must copy the needed text while its
producer permits access, or prove an equivalent retained-owner contract.

The later [callback/framing and WLANLIB follow-up](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/quts-callback-framing-and-wlanlib.md)
closes the static callback-to-DIAG connection and identifies an enabled vendor
interface on the active FastConnect device. The unresolved arrows below record
the boundary of this earlier pass, not an absence of the subsequently traced code.

**FastConnect implication:** the earlier qualified capture observed the missing
`QCDeviceControlFile` result for this PCI adapter. The new writer trace connects
that missing advertisement to endpoint construction. It does not create an
endpoint, establish an MHI association, or rule out a separate Wi-Fi transport.
The class name `Usb` must not be treated as proof of the physical bus: its lower
helper has multiple dispatch branches.

## How received bytes become owned chunks

The selected receive chain is distinct from the earlier `WriteFile` path:

| RVA | Observed operation |
|---|---|
| `0x2a9b78` | `Device::Communication::RxWorker::onRun` |
| `0x0b71c0` | `QcDevice::ReadFromDevice`, including the Windows overlapped-read branch |
| `0x2a7cd0` | `RxWorker::callbackData`, divides a completed read into callback chunks |
| `0x137760` | Buffer assignment: allocate as needed, copy bytes, then set logical length |
| `0x2aae30` | Store the transport callback pair and update an existing receive worker |
| `0x2ac3d8` | Store the worker callback context/function pair under its lock |

The worker obtains the open handle from its associated `Usb` object at **`+0xa0`**.
It allocates a reusable **`0x20000` byte / 128 KiB** buffer and requests up to that
many bytes from `ReadFromDevice`.

- The returned byte count is initialized to zero.
- A nonzero result is processed only when its size is at most `0x20000`.
- Zero bytes produce no data callback in the inspected loop.
- Oversized counts enter an invalid-size handling path rather than being copied
  as valid input. This check occurs after I/O; it is not proof of the underlying
  driver's memory safety.
- Read success is not equivalent to data arrival: the helper has a timeout path
  that returns success with a zero byte count.
- Read-error handling also depends on the `Usb` object's flag at `+0x88`: the
  inspected failure branch closes/exits when that flag is zero. Its other branch
  can continue. The flag's runtime meaning is not qualified, so an exporter must
  not infer a universal failed-read rejection policy from the byte-count checks.

For each admitted read, the worker visits offsets in **`0x4000` byte / 16 KiB**
steps. `callbackData` chooses the smaller of 16 KiB and the remaining byte count.
It creates a new reference-counted `Device::Buffer` and calls `0x137760` to copy
that portion of the reusable read buffer.

For this newly allocated object, the assignment path allocates payload storage,
performs `memcpy`, then stores the logical length. The callback therefore gets
a separate owned byte buffer, rather than a view into the next read's scratch
storage. The producer releases its local reference after the callback; a consumer
that keeps the object beyond the callback must retain a reference or copy bytes.
Allocation-failure behavior and concurrent consumer behavior were not live-tested.

```text
Device handle
    | ReadFile / GetOverlappedResult
    v
Reusable 128 KiB read buffer + actual byte count
    | reject oversized result; ignore zero-byte result
    v
For each portion of at most 16 KiB
    | allocate Device::Buffer -> copy payload -> set length
    v
Callback(context, reference-counted buffer)
    |
    ? concrete DIAG registration / queue association still needs closure
    |
    v
Protocol framing and validation -> complete diagnostic record
    |
    ? exact Wi-Fi firmware producer and timestamp schema still missing
```

`?` marks an unclosed connection. A 16 KiB chunk is a software delivery boundary;
it is not established as an 802.11 frame, one DIAG packet or one firmware event.
The first-chunk boolean is used by this callback path; no hardware sampling
meaning has been established for it.

## Cancellation and completion

The inspected Windows read branch creates a private event and stack-local
`OVERLAPPED` structure, calls `ReadFile`, and checks for `ERROR_IO_PENDING`.
Pending reads go to **`GetOverlappedResult(..., TRUE)`**. That call waits for the
operation to complete and reports its transferred-byte count; it has no explicit
timeout argument. See Microsoft's [completion contract](https://learn.microsoft.com/en-us/windows/win32/api/ioapiset/nf-ioapiset-getoverlappedresult).

The helper closes its event after that return. Its stack-local operation state
and caller-owned payload buffer therefore remain available while the selected
pending-read wait is executing. This is a useful static lifetime pattern; it is
not a live test of cancellation, device removal or a malfunctioning driver.

The normal `Usb::close` sequence at **`0x2a89a8`** is:

1. Request worker stop through **`0x106d08`**.
2. Call **`0x2a8d60`**, which stores `-1` in the shared handle field and calls
   **`CancelIoEx(handle, NULL)`** for the saved handle.
3. Close through **`QcDevice::CloseDevice`, `0x0b7038`**; its ordinary Windows-file
   branch reaches `CloseHandle`.
4. Wait for the worker using **`0x106e30`**, then release worker/thread references.

The selected close caller obtains its wait argument from **`0x100e90`**. The
three instructions at that address store **`0x8000000000000000`** into the supplied
object. `waitForStop` recognizes this sentinel and selects **`0xffffffff`**, its
unlimited-wait path. Consequently, the located shutdown sequence does **not**
establish a bounded cancellation deadline.

The generic wait helper also contains a `TerminateThread` fallback for a finite
wait that expires. The selected caller's unlimited sentinel does not establish
execution of that fallback. It must not be reported as an observed forced stop.

Microsoft states that [CancelIoEx requests cancellation without waiting for completion](https://learn.microsoft.com/en-us/windows/win32/api/ioapiset/nf-ioapiset-cancelioex).
Its return alone does not permit buffer or `OVERLAPPED` reuse. A future bounded
collector must preserve those objects until completion is accounted for, including
the race where the read completes normally after cancellation was requested.

## Where record boundaries belong

The separate DIAG worker at **`0x219a58`** passes a buffer-backed stream to
**`DiagRxWorker::readPackets`, `0x22d038`**. This routine calls through a frame-stream
object and contains frame-error, CRC-error and response-routing branches.
**`0x1e9848`** performs a runtime type check for
`System::Net::NonHdlc::FrameStream` and handles its invalid-frame status.

This establishes a protocol-framing layer beyond raw transport reads. It does
not yet validate every framing mode, checksum rule, partial-frame carry-over,
resynchronization path or connection from the transport callback to that worker.
The private exports provide concrete targets for those checks.

No TSF, SoC, FTM event time, clock ID or hardware-to-QPC sample was decoded in
this pass. The owned byte path is useful implementation evidence; its exact Wi-Fi
producer and schema still determine whether it can carry the timing record we need.

## Reproduce the trace

Use [TraceQutsDiscovery.java](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/adapters/ghidra/TraceQutsDiscovery.java)
on the existing hash-pinned ARM64 project. Preconditions are the locally owned
binary, analyzed Ghidra project, JDK and **new private output directories**.
No elevation or device access is needed.

```text
analyzeHeadless <project-directory> QutsDiscovery
  -process QUTS.exe -noanalysis -readOnly
  -scriptPath <repository>/research/adapters/ghidra
  -postScript TraceQutsDiscovery.java <new-private-output>
  max-instructions:32768 <seed-RVAs>
```

Run each seed group separately and preserve the executed script and `receipt.tsv`:

| Question | Seed RVAs |
|---|---|
| Discovered-list publication and validation buffer | `192b1b0 192d1f0` |
| Endpoint writer and OS receive/cancel callers | `b3b58 f97348 f97288 f97380` |
| Receive worker and chunk publication | `b71c0 2a9b78 2a7cd0` |
| Copy semantics and shutdown helpers | `137760 106d08 106e30 b7038` |
| Callback registration | `2aae30 fdd400 2ac3d8` |
| DIAG framing and non-HDLC checks | `219a58 22d038 1e9848` |

The exporter includes one reference level from each seed. A broad utility helper
can therefore export many callers; those extra files do not establish that every
caller belongs to this receive path. Every selected receipt must show completed
decompilation, complete instruction export and zero failures. Headless process
exit alone is insufficient because script errors can leave a zero process exit.

For the small `0x100e90` sentinel helper, navigate to its address in Ghidra and
check the move, store and return directly. This pass additionally recorded the
exact file bytes and decoded immediate in a private verification receipt.

Outputs, hashes, approximate C and assembly remain under ignored
`artifacts/quts-endpoint-rx-20261004/`. Cleanup only concerns those chosen output
directories; no OS or device state needs rollback. No new dependency or production
transport implementation was added.

Validation in this pass:

- Eight Ghidra passes produced receipts with zero decompilation failures and no
  instruction-export truncation in their selected functions.
- The input binary hash and the sentinel constructor's instruction encoding were
  verified independently from the file; receipts remain private.
- Ten targeted documentation, knowledge-index and diagram-consistency tests passed.
  Generated-index checks and Git whitespace checks passed.
- Executable repository code was unchanged in this pass, so the full 262-test
  suite from the preceding capture/decoder pass was not rerun. No live receive,
  cancellation or complete-record test was claimed from these offline checks.

## Next experiment and glossary

The writer and receive-copy locations were established in this pass. The later
[follow-up](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/quts-callback-framing-and-wlanlib.md) advances items 1 and 2 below;
live complete-record and timing qualification remain open:

1. Close the concrete callback-to-DIAG registration and queue association, then
   inspect the selected frame-stream decoder's incomplete and invalid cases.
2. Attribute an existing diagnostic endpoint to the exact FastConnect device
   stack using device identity and its actual registration source. Do not invent
   an endpoint or add `QCDeviceControlFile` merely to pass discovery.
3. With an attributable endpoint and reviewed initialization, qualify one existing
   record: exact returned length, retained ownership, cancellation completion,
   framing, producer identity and loss/epoch information.
4. Qualify timestamp fields and fresh hardware/QPC correlation separately. A
   successful copied read does not establish a hardware sampling instant.

- **Endpoint:** the Windows device path used to open a transport handle.
- **SetupAPI:** Windows APIs for identifying devices and their properties.
- **Owned buffer:** storage whose lifetime is held by an object/reference, rather
  than borrowed from a producer's reusable scratch buffer.
- **Chunk / record:** a portion delivered by the transport / a complete unit
  recognized by the protocol. Their boundaries can differ.
- **Overlapped I/O:** Windows asynchronous I/O with operation state kept until
  completion, even when cancellation has been requested.
- **HDLC / CRC:** a framing family / an error-detection checksum. Neither supplies
  firmware request identity or clock meaning by itself.

At analysis completion, these changes were local and had no hosted CI result.
Publication and subsequent checks are tracked in [PR #3](https://github.com/Protonmatter/wifi-hardware-time/pull/3).
Static evidence and offline CI do not establish live endpoint operation,
server-side consistency or timing accuracy.
