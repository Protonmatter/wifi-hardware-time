# Before HTC: the receive-buffer producer and copy contract

> **Archive — not current operating instructions.** Historical documentation at [e9d71b843651](https://github.com/Protonmatter/wifi-hardware-time/commit/e9d71b84365122ff2640e240b20fc1dbb834388a). Relative links are rebased for reading. [Exact original bytes](../originals/docs__tsf__hif-receive-buffer-producer.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

We have connected the posted receive buffer, copy-engine completion, HIF queue and HTC callback in the exact driver. The selected pooled-buffer path resets fragment metadata and queues one buffer per completion; it does not join payload fragments in HIF. Two copy points retain the transport header. A live exporter still needs capacity, synchronization, lifetime and publication checks before returning independently owned application bytes.

## Contents

- [Scope and terms](#scope-and-terms)
- [Connected producer path](#connected-producer-path)
- [Buffer geometry and synchronization](#buffer-geometry-and-synchronization)
- [Pool construction and descriptor admission](#pool-construction-and-descriptor-admission)
- [Completion identity and byte count](#completion-identity-and-byte-count)
- [Copy opportunities](#copy-opportunities)
- [Why the copy-engine history is insufficient](#why-the-copy-engine-history-is-insufficient)
- [Reproduce and validate](#reproduce-and-validate)

## Scope and terms

Static inspection on 2026-10-05 of ARM64 `qcwlanhmt8380.sys` `1.0.4374.1300`,
SHA-256 `ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`.
RVAs below are offsets in that image, not userspace call addresses.

- **HIF:** the driver's host-interface layer.
- **HTC:** host-target communication, whose receive callback is `0x1f5f20`.
- **CE:** copy engine, a device transport mechanism that moves data to/from host memory.
- **DMA:** direct memory access, through which a device transfers data without a CPU byte-copy loop.
- **MDL:** a Windows memory descriptor list describing a buffer's memory range.
- **Coalescing:** joining pieces into one contiguous buffer.
- **Pool:** reusable storage. A recycled address does not identify the same event.

This report extends the [transport and normalization trace](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/tsf-event-ingress-and-owned-copy.md).
No private command, kernel-memory read, hook, logging change or device reset was performed.

## Connected producer path

```text
Posted receive buffer
  Pool checkout resets metadata; map one receive address
       |
       v
Copy-engine completion
  Recover byte count and the posted buffer's saved context
       |
       v
HIF receive writer (0x1b17f0)
  One 64-byte queue record: pipe + buffer pointer + received count + metadata
  Invoke cache-synchronization helper
       |
       +---- COPY A: after synchronization, before publishing to HIF queue
       |            [proposed exporter; not installed]
       v
HIF completion dispatcher (0x1b2f18)
  Remove record; write received count to buffer's logical-length field
       |
       +---- COPY B: before invoking HTC, while header is still present
       |            [proposed exporter; not installed]
       v
HTC receive (0x1f5f20) -> WMI receive -> normalize TLV -> TSF handler
       |
       v
Release payload ownership; recycle completion record
```

Solid arrows are static connections, not a new live execution trace. Neither copy
branch exists as a connected application exporter. A host timestamp at A or B
would describe host processing of received data, not the earlier hardware sample.

| Step | Exact-build location | Evidence |
|---|---|---|
| Register HTC callbacks | `0x1b3a98` | Copy a 40-byte callback/context block into HIF `+0x950` |
| Install active callbacks | `0x1b4518`, copy at `0x1b45a4` | Copy that block to HIF `+0x978`; receive callback becomes `+0x988` |
| Register CE receive writer | `0x1b3548`, call at `0x1b360c` | Supply `0x1b17f0` and the pipe context to the receive-registration helper |
| Replenish receives | `0x1b3b30` | Allocate/reset a pooled buffer, map it, post its context and receive address |
| Write receive completion | `0x1b17f0` | Set record type 2 and preserve the buffer, byte count and raw metadata |
| Synchronize before queue publication | call `0x1b18fc` to `0x006eb0` | Selected helper can invoke `KeFlushIoBuffers` before queue linking |
| Dispatch completed receive | `0x1b2f18` | Remove queue record under its lock, then call the active receive callback |
| Enter HTC | `0x1b3124..0x1b3148` | Store received count at buffer `+0x38`, load context `+0x978` and callback `+0x988`, invoke it |

The name `hif_completion_thread` does not prove a dedicated OS thread: the receive
writer directly calls it. Live execution level and teardown synchronization still
need qualification before choosing an exporter allocation/locking strategy.

## Buffer geometry and synchronization

The posted path calls pooled checkout `0x0067a0` with no headroom, eight-byte
alignment and flags zero. On a successful pool removal, that routine:

1. Saves the backing virtual address, DMA address, capacity and cached MDL.
2. Clears the buffer object's `0x1e0` bytes of metadata.
3. Restores the backing allocation, sets its pool owner, alignment offset and
reference count, and starts with logical length zero.

That reset clears metadata, not the backing payload. An exporter must copy only
validated received bytes, never the whole allocation or an inferred padded extent.

Relevant buffer-relative fields are:

| Offset | Meaning in the inspected pooled path |
|---|---|
| `+0x10` | Backing virtual base |
| `+0x20` | Backing DMA address |
| `+0x28` | Retained allocation extent, also used when constructing an MDL |
| `+0x30` | Current data offset into the allocation |
| `+0x38` | Logical length, later set from the completion count |
| `+0x68` | Cached MDL, when present |
| `+0x158` | Extra-fragment count cleared by checkout |
| `+0x170` | Pool owner |
| `+0x198` | Reference count |

The selected mapper at `0x006d40` sets one mapping entry for this pooled path.
The receive queue writer does not join payloads or add fragment descriptors.
This supports a **single-buffer candidate for this selected path**. It does not
qualify every representation supported by the generic buffer-length helper.

The synchronization helper `0x006eb0` uses a cached MDL when available. Otherwise
it attempts to allocate one; the flush call depends on that allocation succeeding.
The helper returns no success status to the receive writer. Its invocation alone
therefore cannot attest the live synchronization outcome or MDL coverage.
Microsoft documents `KeFlushIoBuffers` as a cache-maintenance operation for the
range described by its MDL; it is not a buffer-ownership transfer or a clock sample.
[Microsoft API contract](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-keflushiobuffers).

Before copying, a live backend must establish the actual geometry and require
`data_offset <= capacity` and `received_bytes <= capacity - data_offset`. It must
also verify the expected empty fragment state and source lifetime. No live values
for those fields were read in this pass. The inspected HIF queue is not a new
capacity-validation API merely because it retains the received count.

## Pool construction and descriptor admission

The follow-up trace resolves where the cached MDL originates. It also rejects an
otherwise tempting inference: successful pool initialization or a zero return
from the mapping helper does **not** establish that an MDL-backed flush occurred.
An MDL describes memory; it does not itself establish data freshness or ownership.

| Step | Exact-build location | Selected static behavior |
|---|---|---|
| Construct pool in `ol_ath_open` | `0x187c20`, geometry at `0x187dd4..0x187ebc` | Allocate `0x3880` metadata objects of `0x1e0` bytes; give each a retained capacity of `0x800` bytes |
| Allocate backing blocks | `0x187ed4..0x187fa8` | Obtain `0x1c4` blocks of `0x10000` bytes, subdivided into 32 buffers per block; store each buffer's virtual/DMA addresses |
| Create cached MDL | `0x187fd0..0x188034` | Allocate from each buffer's base and capacity; store the result at buffer `+0x68` |
| Null-MDL branch | `0x188004..0x188024` | Log allocation failure and continue the loop; this branch does not abort it |
| Bind pool to HIF | caller `0x188080..0x18808c`, store `0x1972c0` | Pass the pool into `hif_open`, which stores it at HIF context `+0x118`, the field used by the inspected replenishment path |
| Preserve cached descriptor on checkout | `0x0067a0` | Save and restore `+0x68` across metadata reset; does not require a non-null descriptor |
| Temporary mapping MDL fails | `0x006dd8` to `0x006e7c`, return `0x006e84` | Skip the flush and still return zero from the selected mapping helper |
| Temporary receive-sync MDL fails | `0x006f18` to `0x006f84` | Skip the flush and return from the void synchronization helper |

The mapping helper's temporary MDL is freed after use rather than installed in
buffer `+0x68`. A successful temporary allocation at posting therefore does not
guarantee a cached MDL at receive completion. A failure at completion cannot be
excluded by observing only the earlier map return value.

The backing-memory allocator also has two branches, selected by a global at
`0x32e5d8`. Through `0x0082b0` and `0x007c10`, it reaches `0x007988`:

- With a zero selector, the branch calls `MmAllocateContiguousMemorySpecifyCache`.
  The fifth argument comes from allocation request `+0x28`; the pool constructor
  supplies `1`, corresponding to `MmCached`. The assembly preserves this argument
  even though the approximate C export omitted it. Microsoft's
  [allocation signature](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-mmallocatecontiguousmemoryspecifycache)
  and [cache-type definition](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ne-wdm-_memory_caching_type)
  define its meaning.
- With a nonzero selector, it uses an indirect operation at table `+0x110`.
  The [DMA contract follow-up](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/dma-backing-contract.md) now identifies this as
  `AllocateCommonBufferWithBounds`, reached through a framework-supplied adapter.
  The selector's file initializer and located configuration writer both supply
  `1`. This favors the common-buffer path statically; live selection and coherency
  remain unobserved. That call also requests cached memory explicitly.

**Exporter consequence:** source admission needs evidence for the actual buffer,
allocation mode and required synchronization. Presence in the pool, a nominal
capacity of 2 KiB, an MDL pointer or a successful mapping return is insufficient
on its own. Validate actual geometry and lifetime before copying. These are
static failure-path findings, not an observed allocation failure, stale payload
or defect in the running driver's DMA behavior.

## Completion identity and byte count

The common receive-drain wrapper at `0x1f2d48` calls slot `+0x40` of the selected CE
operation table. File inspection resolves both table variants:

| Table RVA | Receive-post function (`+0x30`) | Completion reader (`+0x40`) |
|---|---|---|
| `0x3933f0` | `0x1f2120` | `0x1f2370` |
| `0x3934f0` | `0x1f46d0` | `0x1f49a0` |

The target-type predicate selects the table during configuration. Its live value
was not read. In the second variant, the posting function stores the buffer
context in a ring-indexed array. The completion reader takes the byte count from
the upper 16 bits of descriptor word zero, returns the saved buffer context,
clears the consumed context slot and advances the ring. The alternate reader
takes the count from the low 16 bits at descriptor `+8`.

The HIF writer receives its initial record through callback arguments and drains
additional completions through that wrapper. Its 64-byte queue record contains:

- Next-record pointer at `+0`, receive type 2 at `+8`.
- Pipe context at `+0x18` and network-buffer pointer at `+0x20`.
- Received-byte count at `+0x30` and raw metadata words at `+0x34`, `+0x38`.

These identities connect a transport completion to its posted buffer. They do
not establish which action-4 request caused the firmware TSF sample. A ring index,
buffer address or host queue sequence can be reused; none is a firmware clock epoch.

## Copy opportunities

**A: after `0x006eb0` returns, before the receive writer links its batch into the
HIF queue.** This can retain completion metadata and the original transport bytes
before HIF queue delay. It requires a stronger check of synchronization success
than the existing void helper provides, and a bounded copy/publication design.

**B: at the dispatcher receive branch before `0x1b3148`.** The dispatcher has the
completion record and retained buffer; HTC has not removed its header yet. The
payload must be copied before calling HTC, because downstream code mutates buffer
offsets and can release it. The completion record is recycled after the callback.

For either point, the application record should contain:

- Owned original bytes plus received count, allocation/span checks and transport
  advertised length kept as separate facts.
- A scoped host observation ID, raw completion metadata with explicit validity,
  and separately established firmware/clock identities.
- Host times named by their observation point; source loss and continuity state.
- A complete/publication marker written only after the copy finishes, with bounded
  reader, cancellation and teardown behavior.

Kernel pointers stay internal. A host-generated ID must not be presented as a
firmware response token. One CE completion must not automatically become one TSF
record: the existing strict `htc-wire` profile accepts only one matching envelope.
Neither opportunity supplies an existing callable userspace return mechanism.

The [concurrent raw-response broker](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/raw-event-response-broker.md)
now implements the application-side queue and response lifecycle. Its Windows DLL
is user-mode code; it cannot be called at these kernel copy points. The kernel-side
copy/return adapter remains the missing connection.

## Why the copy-engine history is insufficient

The lower completion readers call another history writer at `0x1f4290`. It uses
40-byte records with a type, ring index, direct shared-data time load, a 16-byte
descriptor snapshot and a buffer-context value. **It does not copy the WMI payload.**

Its cursor can advance before the record fields are written. It therefore supplies
neither a qualified concurrent snapshot nor payload ownership. The time load is
not a demonstrated hardware/QPC pair. Reading that history would not recover a
complete TSF record or resolve sampling accuracy.

## Reproduce and validate

The existing inspector now covers this producer chain:

```powershell
python research/tsf/inspect_tsf_ingress.py `
  --driver 'C:\path\to\owned\qcwlanhmt8380.sys' `
  --output artifacts/hif-producer-new.json
python -m unittest discover -s tests -p test_tsf_ingress.py -v
```

- Python 3.11+, existing dependencies and ordinary file permissions.
- The inspector requires the exact image and a new output file with an existing
  parent. It reads at most 16 MiB plus one rejection byte; output is metadata/hashes.
- Exit `0`: inspection succeeded; `1`: rejected input/I/O; `2`: CLI misuse.
- Set `WIFI_TIME_DRIVER_FIXTURE` to include owned-image tests. Without it those
  tests skip; that is not image qualification.
- No device changes, elevation or operational rollback. Raw Ghidra exports stay
  under ignored `artifacts/tsf-hif-producer-20261005/`.

The inspector checks selected callback-copy/count instructions and both CE table
targets, and fingerprints the traced functions. Manual analysis supplies the
broader path interpretation. Its live geometry, synchronization, table-selection
and exporter flags remain false. Hosted checks belong to the exact containing
revision in [PR #3](https://github.com/Protonmatter/wifi-hardware-time/pull/3/checks).

The source-validity follow-up adds pool-constructor and backing-allocation
fingerprints, import identities, the nonfatal MDL branch and HIF pool binding.
Its new `manual_pool_admission` result is explicitly static. Raw Ghidra evidence
is private under `artifacts/tsf-source-validity-20261005/`.

Local validation on 2026-10-05:

- Python compilation and the configured full suite passed: **295 tests, zero skips**,
  including native C and exact Windows-image fixtures. Two owned-image checks
  were added for callback installation, completion handoff and CE table evidence.
- Knowledge-index consistency, documentation navigation, diagram synchronization
  and diff whitespace checks passed. This report uses a plain-text diagram.
- Ghidra produced 27 complete function exports across 25 distinct functions,
  including rejected offset-match candidates; none was truncated or failed.
- Active Qualcomm Wi-Fi remained Up on driver `1.0.4374.1300` with the same hash.
  No administrator elevation was requested.

These validate static evidence and tooling, not a live owned event, DMA coherence,
request association, hardware-to-QPC conversion or synchronization accuracy.
Publication and hosted checks are recorded separately from this local evidence.

**Later source-validity follow-up on the same date:** all **317 configured offline
tests passed with zero skips**, including seven ingress tests. Five bounded
Ghidra runs exported 12 functions with complete instruction lists and successful
decompilation; the selected findings were checked against ARM64 instructions.
The final read-only adapter check reported **Up / 1.0.4374.1300**. No elevation,
private request, memory read or driver modification was used. These results
preceded publication; revision-specific hosted checks are tracked separately in
[PR #3](https://github.com/Protonmatter/wifi-hardware-time/pull/3).

Return to [TSF research](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/README.md) or [the event-ingress report](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/tsf-event-ingress-and-owned-copy.md).
