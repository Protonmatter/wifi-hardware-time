# Receive shutdown: what stops, waits and frees

> **Archive — not current operating instructions.** Historical documentation at [e9d71b843651](https://github.com/Protonmatter/wifi-hardware-time/commit/e9d71b84365122ff2640e240b20fc1dbb834388a). Relative links are rebased for reading. [Exact original bytes](../originals/docs__tsf__receive-shutdown-contract.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

The selected shutdown path now connects PCI disable, receive cleanup, completion-reference polling, thread-stop helpers and later pool release. Several operations have weaker completion guarantees than their names suggest: a drain status is ignored, another timeout returns without a success result, and an interrupt-unregister helper clears a software flag. These static findings constrain an exporter; they do not demonstrate a live race or qualify safe teardown.

## Contents

- [Scope and connected paths](#scope-and-connected-paths)
- [Completion-reference polling](#completion-reference-polling)
- [Thread waits and interrupt state](#thread-waits-and-interrupt-state)
- [Consequences for the exporter](#consequences-for-the-exporter)
- [Reproduction and validation](#reproduction-and-validation)

## Scope and connected paths

This is the file-only phase of the
[complete-event implementation plan](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/complete-event-2026-10-05/engineering-plan.md),
using the same exact ARM64 image as the
[DMA backing contract](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/dma-backing-contract.md). No stop, reset, suspend, private
request or live kernel-memory read was performed. RVAs are file-analysis locations.

```text
hif_disable (0x196c90), when enabled
    |
    +-> clear enabled state
    +-> bus-disable callback +0xa0
    |      PCI table writer selects 0x1b57a0
    |        set stop flag -> DPC drain -> CE/ring cleanup -> thread-stop helpers
    +-> clear device field +0x9a0
    +-> hif_stop (0x1b4640), when started
    |      completion shutdown -> remaining CE cleanup -> clear started state
    +-> remaining HAL teardown

Separate inspected adapter-close tail (0x1865b0)
    IRQ-state helper -> cached MDL release -> backing-block release -> context free
```

**Legend:** arrows show selected static call order. The two chains are not a
proof that every normal/error/reset lifecycle executes them with all producers
already excluded. CE means copy engine; HAL means hardware abstraction layer;
DPC means deferred procedure call. See the [glossary](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/glossary.md).

The concrete links are:

| Location | Observed operation | Qualification consequence |
|---|---|---|
| `0x196d10..0x196d24` | Clear enabled field, call bus-disable dispatcher, release helper and shutdown helper | Ordered calls in the selected enabled branch |
| `0x1ec9c0`, store `0x1eca0c` | Install PCI bus-disable function `0x1b57a0` at HIF `+0xa0` | Resolves that indirect target for the inspected bus setup |
| `0x1b57ec..0x1b57f4` | Call DPC drain, overwrite the return register, then call CE cleanup | No branch on the drain result in this caller |
| `0x1b5488` | Poll selected DPC/pending-message/MPDispatch state; selected failure paths return `0xc` | Raw status meaning must not be invented; the selected caller ignores it |
| `0x1b55a4..0x1b55e0` | MPDispatch-only outstanding-state path can log and still return zero | Zero is not a general certificate that every callback has finished |
| `0x1b4698` | Call completion shutdown before remaining cleanup | Caller receives no checked shutdown-success result |
| `0x186780`, `0x1867b4` | Release cached MDLs before backing blocks in the selected close tail | Located free ordering; complete prior callback exclusion remains unproven |

This pass does not classify these branches as exploitable defects or assert that
the running adapter ever reached the failure conditions. Existing callers may
have additional preconditions not established by this bounded trace.

## Completion-reference polling

`0x1b32d8` first removes pending completion records under the queue lock. It
releases their network buffers and reduces each pipe's completion reference count.
It then polls the per-pipe field at HIF `+0x510 + pipe_index * 0x60`.

- A positive reference count can trigger another drain/poll round.
- Each wait round requests a total of **50,000 microseconds** through repeated
  small `KeStallExecutionProcessor` calls.
- The selected counter permits **21 rounds**, a nominal requested stall sum of
  **1.05 seconds**. This excludes queue processing, lock contention, callback
  scheduling and stall overhead. It is not a bounded wall-clock shutdown time.
- On exhaustion, the routine logs a timeout and skips its local completion-space
  and lock cleanup block, then returns. Its caller continues subsequent cleanup.

The units come from the inspected arguments and the
[stall API contract](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-kestallexecutionprocessor).
No duration was measured here. In particular, the 1.05-second arithmetic is not
a firmware-drain guarantee or an accuracy measurement.

## Thread waits and interrupt state

The PCI disable path also calls two thread-stop helpers:

| Helper | Thread handle | Stop event | Selected behavior |
|---|---|---|---|
| `0x1b5e90` | HIF `+0xaf0` | `+0xac0` | Reference thread object, signal event, wait only if reference succeeded, close handle |
| `0x1b5dd8` | HIF `+0xa58` | `+0xa28` | Same pattern for a different thread/event |

Their `KeWaitForSingleObject` timeout pointer is null, which requests an indefinite
wait. A failed object-reference branch skips that wait. These helpers therefore
do not establish a universally bounded join, nor do two thread waits cover all
possible callback sources. [Wait contract](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-kewaitforsingleobject).

The function identified by the diagnostic name `ol_ath_pci_unregister_interrupt`
at `0x1b6860` logs and clears adapter field `+0x2ec`. Its selected body is not an
interrupt/DPC join. The function's name must not be used as evidence that all
interrupt work has completed elsewhere.

## Consequences for the exporter

The required producer integration needs its own explicit completion evidence:

1. Deny new exporter admissions before stopping the source.
2. Establish that device writes and the relevant callbacks have stopped or retain
   valid ownership until their copy completes.
3. Join every entered exporter callback and settle every application request.
4. Publish only complete records; account for discarded or unobservable data.
5. Free backing storage only after those conditions hold. A timeout must remain
   a failed/unfinished shutdown rather than permission to free referenced memory.

The current broker's user-mode lifecycle tests remain useful. They do not execute
the driver paths above. A new companion process/driver also cannot retrofit
producer rundown merely by maintaining its own reference count.

The unresolved edges are **complete callback-source coverage**, **live source
coherency**, **DMA-enabler release ordering relative to all users**, and the
**actual producer-to-application interface**. They remain false in the inspector's
qualification fields. Further work needs either evidence for those exact edges
or an integration whose contract directly supplies them.

## Reproduction and validation

`inspect_tsf_ingress.py` now emits `manual_receive_shutdown` and selected shutdown
imports in addition to the existing ingress/DMA evidence. It fingerprints the
functions and checks selected instructions; broader interpretation is manual,
not an automatically proven call graph.

```powershell
python research/tsf/inspect_tsf_ingress.py `
  --driver 'C:\path\to\owned\qcwlanhmt8380.sys' `
  --output artifacts/receive-shutdown-new.json
python -m unittest discover -s tests -p test_tsf_ingress.py -v
```

Use a new output file and configure `WIFI_TIME_DRIVER_FIXTURE` for image tests.
The [existing runbook](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/tsf-event-ingress-and-owned-copy.md#reproduction-and-validation)
defines bounds, permissions, exit codes and cleanup. No elevation is required.
Private source and trace receipts are under
`artifacts/export-route-reassessment-20261005/`.

Six bounded Ghidra runs exported **29 distinct functions**, all complete and
without decompilation failures. The [execution record](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/complete-event-2026-10-05/decision-log.md)
records **320 passing configured offline tests with zero skips** and remaining
gates. Live teardown, complete-event return
and timing accuracy are not qualified by this file-only investigation.
