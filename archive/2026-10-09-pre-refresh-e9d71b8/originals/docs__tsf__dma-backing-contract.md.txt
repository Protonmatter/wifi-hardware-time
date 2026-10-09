# Receive-buffer allocation: the Windows DMA connection

The previously unnamed allocation call is now connected to Windows's common-buffer API through a framework-created DMA adapter. The inspected initializer and configuration writer favor this route, which explicitly requests cached memory and returns separate CPU and device addresses. This narrows the exporter's memory contract; it does not prove live coherency, safe teardown or a timing-event return to an application.

## Contents

- [What the exact driver establishes](#what-the-exact-driver-establishes)
- [What the buffer addresses mean](#what-the-buffer-addresses-mean)
- [Cache visibility and lifetime](#cache-visibility-and-lifetime)
- [Reproduce and validate](#reproduce-and-validate)
- [Glossary](#glossary)

## What the exact driver establishes

This 2026-10-05 static follow-up uses the same ARM64 image and SHA-256 as the
[HIF producer investigation](hif-receive-buffer-producer.md#scope-and-terms).
Addresses below are image-relative offsets, not callable userspace addresses.

| Evidence | Location | Supported conclusion |
|---|---|---|
| Allocator selector | Global `0x32e5d8` | Its on-disk initial value is `1` |
| Configuration writer | `0x2e410`, `0x2e670` | Loads constant `1` and stores it to that global; it does not copy a user-configured value into this selector |
| Initialization caller | `0x32898`, then `0x328bc` | Applies that configuration before calling the DMA-enabler setup helper |
| Create DMA enabler | `0x35ba8`, table load `0x35c50` | Framework table offset `0x2f0`, index 94: `WdfDmaEnablerCreate` |
| Obtain DMA adapter | table load `0x35cc0`, store `0x35ce0` | Offset `0xc08`, index 385: `WdfDmaEnablerWdmGetDmaAdapter`; its return goes to global `0x3958b8` |
| Allocate common buffer | `0x7988`, operation load `0x7a0c` | Follow adapter `+8` to its operation table, then call slot `+0x110`: `AllocateCommonBufferWithBounds` |
| Release helper | `0x7c68`, operation load `0x7cd8` | Selected nonzero-selector branch calls table slot `+0x18`: `FreeCommonBuffer` |

Framework indices are checked against Microsoft's
[pinned function-index header](https://github.com/microsoft/Windows-Driver-Frameworks/blob/b6191d9543441329154da32f7ab9bdd97228dd3c/src/publicinc/wdf/kmdf/1.33/wdffuncenum.h).
The operation-slot identification combines the traced adapter origin with the
[DMA_ADAPTER structure](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_dma_adapter)
and [DMA_OPERATIONS member order](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_dma_operations),
using ARM64 eight-byte pointer alignment. It is not an offset-only name guess.

The enabler's configuration constants request address width **36** and WDM DMA
version **3**. These describe DMA addressing/API selection, not timestamp width
or timer frequency. Field interpretation follows Microsoft's
[configuration structure](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdfdmaenabler/ns-wdfdmaenabler-_wdf_dma_enabler_config).

```text
Configuration sets allocator selector to 1
    |
    v
WDF creates DMA enabler -> returns associated DMA_ADAPTER
    |                           |
    |                           v
    |                  DMA_OPERATIONS table +0x110
    |                           |
    |                           v
    |                  AllocateCommonBufferWithBounds
    |                    /                  \
    |                   v                    v
    |            CPU virtual address    Device logical address
    |                   |                    |
    +-------------------+--------------------+
                        v
              Backing block split into pooled receive buffers
```

**Legend:** arrows show connected static data/control flow. The selector's live
value, actual allocation calls and active DMA adapter were not observed. The
initializer and located writer support the common-buffer route as the expected
path; this is not an exhaustive audit of indirect writes or runtime changes.

## What the buffer addresses mean

The selected call supplies a length, address bounds, zero allocation flags, a
pointer to cache type `1` (`MmCached`), and a preferred node number. Node attempts
start at zero and extend through the saved `KeQueryHighestNodeNumber` result.
The node number is an allocation-placement parameter, not a radio-link identity.

Two different addresses come back:

- The function result is the **CPU virtual address**, which the driver can use
  to access the allocation while its lifetime and synchronization permit it.
- The output argument supplies a **device logical address**, which is used for
  DMA. It must not be treated as a CPU pointer or substituted with a separately
  calculated physical address. This distinction is explicit in Microsoft's
  [common-buffer contract](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nc-wdm-pallocate_common_buffer_with_bounds).

The previously traced pool constructor preserves these separately, then advances
each by the per-buffer offset. Its 2 KiB buffer capacity remains a source bound,
not proof that a completion's length is valid.

## Cache visibility and lifetime

The call passes an explicit cached-memory override rather than a null/default
cache argument. Microsoft states that a caller requesting `MmCached` for a
noncoherent adapter is responsible for flushing the cache. Thus the name
"common buffer" alone does not establish that CPU reads see completed device
writes. [Allocation/cache contract](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nc-wdm-pallocate_common_buffer_with_bounds).

This reinforces the [MDL failure-path finding](hif-receive-buffer-producer.md#pool-construction-and-descriptor-admission):
neither mapping success nor the existence of a receive-pool entry establishes
the necessary coherency. It does **not** demonstrate that this adapter is
noncoherent or that a skipped flush caused stale data.

The release helper reads a retained record containing length at `+0`, device
logical address at `+8`, CPU virtual address at `+16`, and cache enum at `+24`.
After the selected free operation, it deletes the associated WDF memory object.
That is a located release pattern, not proof of teardown ordering against an
active receive callback or export worker. The subsequent
[receive-shutdown trace](receive-shutdown-contract.md) locates drain, timeout and
thread-wait paths while retaining those qualification limits. Microsoft's
[free contract](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nc-wdm-pfree_common_buffer)
also requires the matching allocation parameters and forbids freeing only part
of a common buffer; a pooled 2 KiB slice is not a separate backing allocation.

The DMA-adapter pointer's documented lifetime depends on its enabler object.
An exporter must therefore establish callback completion and allocation lifetime
before teardown frees either the buffer or the objects supporting it.
[Framework adapter lifetime](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdfdmaenabler/nf-wdfdmaenabler-wdfdmaenablerwdmgetdmaadapter).

The [selected WMI copy boundary](tsf-event-ingress-and-owned-copy.md#ownership-and-the-copy-point)
remains before header mutation. This follow-up supplies a stronger allocation
contract for that work. It adds no event getter, kernel hook, live copy, firmware
association or hardware-to-QPC relationship.

## Reproduce and validate

The existing file-only inspector now emits `manual_dma_contract`, including the
selector's **file** value, selected instruction checks, named table slots and
false live-coherency/teardown/export qualification states.

```powershell
python research/tsf/inspect_tsf_ingress.py `
  --driver 'C:\path\to\owned\qcwlanhmt8380.sys' `
  --output artifacts/dma-contract-new.json
python -m unittest discover -s tests -p test_tsf_ingress.py -v
```

Use a new output file and configure `WIFI_TIME_DRIVER_FIXTURE` to include the
exact-image tests. The [existing runbook](tsf-event-ingress-and-owned-copy.md#reproduction-and-validation)
defines permissions, size bounds, exit codes and cleanup. No elevation is needed.

Private receipts and Ghidra exports are under
`artifacts/tsf-dma-contract-20261005/`. The public reference receipt pins Microsoft
WDF commit `b6191d9543441329154da32f7ab9bdd97228dd3c` and downloaded file hashes.
These files were inspected as data. No device operation or runtime global read
was performed. Hosted checks require publication of this revision.

Local validation for this follow-up:

- **318 configured offline tests passed, zero skips**, including eight ingress
  tests and the existing native/image fixtures; Python compilation passed.
- Two bounded Ghidra runs exported eight function instances across six distinct
  functions, without truncation or decompilation failure. Selected instructions
  were checked against the approximate C output and documented API contracts.
- A fresh inspector receipt preserves all false live-qualification states.
- The final read-only Wi-Fi check reported **Up**, driver **1.0.4374.1300**.
- No elevation, private request, kernel-memory read or device change was used.

These validate the static evidence and tools. Live buffer coherency, producer
publication, teardown safety, firmware identity and clock conversion remain open.

## Glossary

- **DMA:** direct memory access, used by the device to transfer data to host memory.
- **Common buffer:** an allocation addressable by both the CPU and device through
  their respective address mappings.
- **Cache coherency:** the rules ensuring that CPU and device accesses observe
  the intended data rather than stale cached contents.
- **WDF / DMA enabler:** Windows Driver Frameworks and the object configuring a
  driver's DMA support.
- **Static prediction:** behavior implied by inspected code and initial values,
  distinguished from observing that behavior on the running machine.
