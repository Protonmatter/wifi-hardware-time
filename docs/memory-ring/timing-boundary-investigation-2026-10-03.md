# Timing producer, return-path and qualification boundaries

Driver inspection narrowed memory-log access to diagnostic and recovery paths and located receive timestamp fields. An offline model showed that two equal buffer copies can still contain unfinished records. No live corruption was measured, no safe getter was qualified, and restart, sleep and roaming remain preparation only.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** The QUTS client is a separate owned-byte return candidate. It does not repair the existing ring publication or temporary-buffer lifetime gaps. See [current findings](../knowledge/current-findings.md).
<!-- /historical-context -->

A ring is a circular buffer that overwrites old entries; publication means a writer has finished making a record readable. A getter reads data through a defined interface. RVA is an offset within the driver image. RX means receive, TX means transmit, and PPDU is a physical-layer transmission unit. See the [glossary](../glossary.md) for related terms.

## Contents

- [Ring retrieval: remaining direct consumers narrowed](#ring-retrieval-remaining-direct-consumers-narrowed)
- [TSF request identity and sampling](#tsf-request-identity-and-sampling)
- [Raw FTM identity and export](#raw-ftm-identity-and-export)
- [A concrete RX descriptor timestamp location](#a-concrete-rx-descriptor-timestamp-location)
- [Required evidence for every requested capability](#required-evidence-for-every-requested-capability)
- [Reproduction and scope](#reproduction-and-scope)

Date: 2026-10-03, America/New_York. Starting revision: `fdcc22f80ad173a2f4f2844c0f6b666794fda54a`.
This pass reads the installed driver file and existing disassembly, freshly
disassembles bounded ranges, and runs offline models. It does not acquire live
ring contents, send private requests, run scans, change logging, reset the adapter,
suspend the host, force a roam or alter a clock. The user selected preparation
only for disruptive tests. No hardware capability is promoted.

Driver: ARM64 1.0.4374.1300, SHA-256
`ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`.
All addresses below are on-disk RVAs, not runtime addresses or callable APIs.
Driver identity alone does not qualify the loaded firmware version or schema.

## Ring retrieval: remaining direct consumers narrowed

The [earlier ring investigation](unmatched-tsf-and-memory-log.md) identified
reservation before copying and a separate full-copy/file path. This pass resolves
the recent-span consumer and inventories all direct callers of the two MHI dump
routines across executable sections.

| Consumer/call site | Exact-build evidence | Consequence |
|---|---|---|
| Recent-span call `0x2a5d4` | Inside routine `0x2a1e0`; diagnostic label at `0x252d10` is `EvtNetDeviceCollectResetDiagnostics` | Device reset diagnostics, not a userspace polling entry point |
| Recent-span helper `0x8a88` | Samples position masked to 21 bits; returns a pointer to at most 1 MiB of a contiguous span | Returns original storage, not a copied or pinned record set; not necessarily the most recent complete records across wrap |
| Following indirect call `0x2a618` | Passes framework globals, device, length and span pointer; exact runtime table target not resolved | Consistent with reset-diagnostic storage, but API identity is an inference, not an observed runtime binding |
| General dump call `0x364cc` | In `WlanOsCrashCallback`, routine `0x36370`, label `0x2542d0` | Crash-related path |
| General dump call `0x22888c` | In `MHIForceRDDMMode`, routine `0x2286c8`, label `0x2e6b30` | Forced diagnostic-dump path |
| General dump call `0x22d71c` | In `BHIFirmwareDownloadWorkItem`, routine `0x22d470`, label `0x2e7c00`; reached on nonzero result branch | Firmware-download failure handling |
| General dump calls `0x22ed8c`, `0x22edd4` | In `bhi_rddm`, routine `0x22ed30`, label `0x2e7e70` | RDDM/recovery handling |
| Memory-log-only calls `0x437034`, `0x43727c` | Previously identified device cleanup and self-managed-I/O flush | Lifecycle consumers remain unsuitable as a polling contract |

The recent-span caller also contains a conditional call through the import slot
for `KeBugCheckEx` at `0x2a5c4`. This does not mean every diagnostics invocation
crashes. It is an additional reason not to invoke this internal routine as a
getter. The scan covers immediate B/BL calls, not all indirect/computed routes.

Microsoft limits `NetDeviceStoreResetDiagnostics` to the reset-diagnostics
callback and accepts at most 1 MiB. Its lifecycle documentation describes
synchronization with selected power-down callbacks; it does not establish that
every driver logger is stopped. The observed argument shape and span limit are
consistent with this contract, but do not prove the unresolved table target.
[API contract](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/netdevice/nf-netdevice-netdevicestoreresetdiagnostics),
[reset sequence](https://learn.microsoft.com/en-us/windows-hardware/drivers/netcx/platform-level-device-reset).

### Why two equal copies cannot certify publication

The key distinction is **reserved space versus finished data**. A writer can
claim space before filling it. Quiescence means no writer can change the buffer;
a commit marker would tell a reader that a record is complete.

`model_ring_publication.py` explores all ten program-order-preserving schedules
of a writer's reserve/prefix/payload operations and a reader's two snapshots.
It grants each snapshot atomic copying, which is stronger than a real memcpy.
It assumes no external lock or established writer quiescence. Two schedules
produce equal snapshots and the expected reservation position before completion:

1. reserve, copy, copy, prefix, payload: both copies contain old bytes;
2. reserve, prefix, copy, copy, payload: both copies contain mixed old/new bytes.

This refutes the proposed inference under the model assumptions. It does not
measure live corruption, model ARM memory reordering, or prove callers lack
synchronization. A valid getter needs established writer exclusion/quiescence,
or producer-provided commit/version semantics with lifetime and overwrite rules.
Adding a checksum only in the reader does not create a producer commit marker.
No getter, concurrent-copy guarantee or retrieval latency is qualified.

## TSF request identity and sampling

TSF is the Wi-Fi timing counter; SoC denotes the reported system-on-chip counter.
A vdev is a virtual device, and a TLV header identifies a type-length-value record.
Neither identifies a unique request unless the producer supplies that contract.

The builder allocates/sends 20 bytes. In the inspected body at `0x195690` and
`0x1956a0`, explicit stores populate a TLV header, vdev and action; this pass does
not assign semantics to the other allocation bytes or lower transport metadata.
No added request token is justified by that unused space.

The report handler loads 32-bit words from incoming offsets
`+0x04,+0x08,+0x0c,+0x10,+0x14,+0x28,+0x2c`. Its retained callback at
`0x216c30..0x216c48` passes a vdev byte and low-word TSF-minus-SoC difference.
It does not return the full tuple or a request/epoch token through that callback.
The inspector mechanically reproduces the word-load offsets; interpretation of
the surrounding callback still depends on reviewed data flow.

Unconsumed report bytes are not presumed empty or meaningless. No external getter
or producer schema for them has been found. The observed report/log path has no
qualified identity that binds a private request against concurrent scan activity.
See the [three scan experiments](../acquisition/scan-tsf-results-2026-10-03.md).

The command-return time, report-log time and event callback are different host
events. A copied counter pair or memory barrier in host code cannot establish
when firmware sampled the counters or that both counters latched together.
Actions 3/4 retain their previously demonstrated cache/refresh behavior only.

## Raw FTM identity and export

FTM (Fine Timing Measurement) is a Wi-Fi ranging exchange. Raw export would retain
the individual event records before the driver combines them into a result.

Freshly checked range `0x147964..0x147978` compares the low 16 bits of the response
word at `+0x08` with an 8-bit request-context value at `+0x89ec`. This is a bounded
internal correlation check, not an on-air exchange/fragment identity contract.
An 8-bit value cannot by itself provide indefinite uniqueness across requests;
its allocation/reuse and late-response handling still need qualification.

The previously reconstructed complete-buffer parser and aggregate completion
remain separate from the device-service notification path. The inspector
reproduces direct call inventories for those targets; it does not recover the
opaque per-frame bytes, units, epoch, validity flags or absolute event values.
Raw FTM export remains blocked on a real return path and schema, not on a more
permissive parser for the current aggregate callback.
[Raw-access findings](../ftm/ftm-raw-access-followup.md),
[notification routing](../ftm/ftm-notification-routing.md).

## A concrete RX descriptor timestamp location

A descriptor is metadata accompanying received data. PHY means the physical radio
layer; MPDU is a MAC-layer frame, and NBL is a Windows network buffer list.
Finding a field in a descriptor does not yet connect it to an application's packet.

The diagnostic routine at `0x2195e0` retains its input descriptor pointer in x19.
At `0x219c00`, a 32-bit pair load places descriptor `+0x60` and `+0x64` in the
first two formatting argument registers. At `0x219c0c`, the next pair supplies
`+0x68` and `+0x6c`. The format at `0x2e4190` labels the first and third values
as the high and low words of `ppdu_start_timestamp`; the intervening word is PHY
metadata. These high/low words are **not adjacent**.

The single direct caller at `0x219cf0` passes its buffer argument plus eight
bytes. Therefore the diagnostic mapping is descriptor `+0x60/+0x68`, or that
wrapper buffer `+0x68/+0x70`. These are not offsets into an on-air frame, NBL,
userspace packet buffer or a universally applicable Qualcomm descriptor.

The logger is level-gated (`0x219608..0x219618` and `0x219aa4..0x219ab0`). No
logging configuration was changed and no live descriptor was collected. A name
suggesting PPDU start does not establish units, validity, oscillator, epoch,
physical reference point, per-MPDU mapping or delivery for arbitrary packets.
No TX timestamp path is established by this RX diagnostic. This is a concrete
next data-flow target, not evidence of NDIS/socket timestamp export.

## Required evidence for every requested capability

| Capability | Current result | Evidence needed to close it |
|---|---|---|
| Safe live ring retrieval | No qualified caller envelope | Versioned existing getter or deliberately instrumented driver return path; access control, length checks, lifetime, bounded cleanup and complete-record semantics |
| Concurrent-copy consistency | Naive cursor/double-copy inference disproved in finite model | Producer commit protocol or verified writer quiescence; concurrent/wrap/overwrite stress with independent completeness oracle |
| Exact request identity | TSF callback insufficient; FTM has bounded internal check | Propagated request/epoch identity, concurrency handling, timeout quarantine, duplicate/reuse tests and packet/exchange binding where needed |
| Fresh simultaneous sampling | Not established | Producer latch semantics and independent observation of reference instants; stale and delayed-completion negative cases |
| Hardware/QPC conversion | No qualified fresh tuple | Same-sample hardware value within an established QPC bracket, clock units/epoch/rate, validity and interval error; independently validate conversion |
| Raw absolute FTM | Complete buffer exists internally; no exported absolute records | Export before reduction with widths/units/validity, fragments, peer/burst/dialog identity and all relevant event times |
| RX timestamps | Descriptor diagnostic fields located statically | Live descriptor-to-packet association, reference point/domain, aggregation/retry semantics, complete export and loss accounting |
| TX timestamps | No new route qualified | Completion descriptor and request association, first/final/retry reference point and clock domain; RX findings do not enable TX |
| Restart/suspend/roam | Preparation only; earlier single restart remains historical | Separately controlled lifecycle cases with continuous observer evidence and fail-closed invalidation; see prepared runbook |
| Calibrated accuracy/sub-ms sync | Required equipment and semantics absent | Controlled peer plus characterized independent comparison, reference uncertainty, held-out runs and full error distribution |

The documented cross-timestamp contract explicitly brackets the hardware sample
with system timestamps. A userspace API-call bracket containing a cached value
does not satisfy it.
[Windows cross-timestamp structure](https://learn.microsoft.com/en-us/windows/win32/api/iphlpapi/ns-iphlpapi-interface_hardware_crosstimestamp).
The same acquisition obligation applies to a private equivalent; public API
availability is not a prerequisite for researching one.

## Reproduction and scope

```powershell
python research/memory_ring/inspect_timing_boundaries.py --driver '<owned exact-build SYS>' --output artifacts/timing-boundaries-new.json
python research/memory_ring/model_ring_publication.py
python -m unittest discover -s tests -p test_timing_boundaries.py -v
python -m unittest discover -s tests -p test_ring_publication_model.py -v
```

The inspector requires existing `pefile`, rejects a mismatched file before
interpretation, reads at most 16 MiB and creates output exclusively. No elevation
or hardware access is required. Output has hashes, RVAs and interpreted field
locations, not proprietary bytes. The model has a fixed five-operation scope
and prints synthetic JSON. No device rollback applies to either tool.

Local evidence: `artifacts/TimingBoundaries-47b6ab8cdf68`, containing inspector
output, finite-model result, six fresh bounded disassemblies and a content-hash
manifest. Disassembly and installed paths stay private. The scanner does not
establish an exhaustive call graph, live values or firmware semantics.

Local validation: 149 tests passed with the owned-driver fixture enabled;
without it, 146 passed and three fixture-dependent tests skipped. Python syntax,
relative links and diff checks passed. Wrong-image and existing-output CLI checks
returned exit 1; the wrong-image case created no result and the existing output
retained its hash. Source hashes and those results are in `validation-receipt.json`.

The final read-only check found Wi-Fi Up with driver 1.0.4374.1300 and the same
qualified SYS hash. The original private-quarantine hash was unchanged, and the
failed-observation lock remained. A successful Windows Temp enumeration found
zero `wlanhost*` files; no dump was triggered to create one. This is neither a
live-ring read nor a guarantee that no other diagnostic file exists elsewhere.

At investigation completion, this follow-up had local validation only and was
not yet committed or pushed. Publication and any hosted CI must be checked against
the exact later revision; prior runs do not validate new changes. The
[lifecycle qualification preparation](../acquisition/lifecycle-qualification-preparation.md)
records the next controlled cases without authorizing execution.
