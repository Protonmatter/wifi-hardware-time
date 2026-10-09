# Owned MLO and management-event records

The existing C exporter now has a separate interface for owning MLO messages and management-frame evidence. Tests establish useful software behavior: source buffers can be reused after publication, reference fields decode correctly, malformed records are rejected, and losses and generations are tracked. The implementation remains an offline prototype because no running-driver producer is connected. Software results and hardware qualification are recorded separately.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** A QUTS client-owned byte return is now located statically. Keep client ownership, server publication, firmware identity and timing accuracy as separate qualification states. See [current findings](../knowledge/current-findings.md).
<!-- /historical-context -->

## Contents

- [Implemented behavior](#implemented-behavior)
- [Records and capability boundaries](#records-and-capability-boundaries)
- [Call sequence](#call-sequence)
- [Bounded event-return investigation](#bounded-event-return-investigation)
- [Validation and operation](#validation-and-operation)
- [Next dependency](#next-dependency)

## Implemented behavior

- The original `te_record` remains 208 bytes and its `te_*` API is unchanged.
- The additive `te_event_*` API owns a two-record queue of diagnostic events.
- MLO publication retains all 32 original bytes and decodes the pinned reference
  layout into separate fields. The original firmware device ID is retained
  separately from the caller's normalized host device ID.
- Management publication owns the 72-byte reference header, a Beacon or Probe
  Response of 36–4096 bytes, and an optional 20-byte reordering/timing block.
  It checks reference TLV tags/sizes, declared frame length, frame type, unsupported
  DS/Order/protection/fragment flags and information-element bounds. Frames use
  the basic 24-byte management header and exclude a trailing FCS. Retry is allowed.
  The optional block is copied, not
  interpreted as a qualified hardware timestamp.
- All publication copies finish before the queue count advances. This commit
  point relies on the caller serializing operations and stabilizing the input.
- Readers receive owned copies. They can outlive the source callback buffers.
- Duplicate/nonincreasing software sequence numbers, identity mismatches and old
  generations are rejected. These checks validate supplied metadata; they do
  not authenticate firmware identity or detect a mislabeled late firmware event.
- Capacity drops consume the admitted sequence and increment a saturating loss
  counter. Each record includes cumulative software losses/rejections at enqueue.
- Quarantine flushes pending records and rejects new publication/read operations.
  A strictly newer epoch and generation clears the synthetic quarantine. That
  declaration is not proof of firmware drain.
- Close flushes the queue and rejects subsequent publication, reads and generation
  changes. Reinitialization requires a new session under the caller contract.

These are implemented software properties, not merely proposed behavior. They
remain subject to the documented preconditions and test coverage below.

## Records and capability boundaries

`te_event_meta` identifies the synthetic source, clock, peer/link, session, epoch,
generation and software sequence. Clock and link zero are valid identifiers when
identity is explicitly present. Management frames require a nonzero synthetic
peer identity; MLO records do not inherently identify an AP.

`callback_entry_qpc` and `qpc_frequency` are caller-supplied host observations.
Their presence does not claim that the radio sampled a clock at callback entry.
The prototype itself does not call QPC or read hardware.

| Capability | Current result |
|---|---|
| Synthetic MLO diagnostics | Implemented copy, reference decoding and rejection behavior |
| Synthetic management diagnostics | Implemented owned frame/header/optional-block copying and structural validation |
| Raw TSF acquisition | Not supplied by this interface |
| Hardware RX/TX timestamps | Not qualified; record flag stays zero |
| Hardware-to-QPC conversion | Not qualified; record flag stays zero |
| Live clock eligibility | Zero for every record |

`te_event_capabilities()` advertises only the two synthetic diagnostic bits.
No successful MLO or management record enables the other capabilities.

Both interfaces use native-endian C structures. MLO bytes and reference TLV
headers are decoded explicitly as little endian. This is not a kernel IOCTL ABI,
an authenticated wire protocol or a stable cross-language SDK layout. The event
record is several KiB; this userspace prototype must not be placed on a kernel
stack without a separate implementation and review.

## Call sequence

```text
Initialize synthetic identity
  -> publish MLO or management event from stable, nonoverlapping input spans
     -> validate identity and structure
     -> copy complete record
     -> publish queue count
  -> read an owned diagnostic record
  -> quarantine on uncertain continuity, or close on teardown
```

Every operation requires caller serialization. No input/output buffer may
overlap the state or another buffer passed to the same operation. Initialization
must precede use. The API performs no device access and retains no input pointers.

Reference source and exact-build observations are in the
[MLO report](../memory-ring/mlo-cache-and-symbol-search.md) and
[management-RX handoff](../adapters/qualcomm-management-rx-handoff.md).

## Bounded event-return investigation

The follow-up stopped at the planned boundary: **no verified application return
for these complete events was established**. It did establish useful constraints:

| Question | Selected exact-build finding | Consequence |
|---|---|---|
| Can the known subscriber select `0x10c`? | Bridge `0x217150` has five direct calls from packet-log subscription `0x217530`; their selected events are `0x101`, `0x102`, `0x106`, `0x109`, `0x108` | This caller does not provide an MLO subscription recipe |
| Is event subscription itself a userspace API? | `0x1fb880` is bound through an internal operations-table slot; no application-facing registrar was established | An internal function pointer is not an IOCTL contract |
| Where is an HTT length available? | Helper `0x143218` sums current and additional packet fragments in selected buffer modes | A total packet length does not certify a contiguous span at the callback pointer |
| Does the HTC service API return events to applications? | `0x1b6e08` connects internal service callbacks; selected callers include HTT/WMI transport setup | Callback storage alone does not establish a userspace completion path |
| Can management metadata be copied before reduction? | The decoded wrapper carries a header, frame pointer/count and optional slots; the selected callback later reduces metadata | Preserve validated slots while owned by the callback; do not retain wrapper pointers |

The public/private candidate investigation remains exact-build and bounded.
It does not prove that every vendor diagnostic mode lacks a return interface.
No new private request, callback installation, packet logging change or live
memory read was attempted. The existing packet-log completion path still lacks
the required complete-event schema and snapshot guarantee.

## Validation and operation

Build and run as an ordinary user with the existing Visual Studio/SDK toolchain:

```powershell
./research/export_contract/Test-TimestampExport.ps1 -Architecture arm64
```

The same harness runs with `-Architecture x64` on a suitable Windows host and
through `test_native_export_contract.py` with a configured local C compiler.
Existing hosted jobs exercise it on Linux and Windows; results must be checked
for the published revision. No compiler, dependency or driver is downloaded by
the harness. Exit 0 means its offline checks passed; exit 1 means build/test
failure. Generated binaries stay under ignored `artifacts/`.

The new tests cover owned-copy behavior after source mutation, explicit raw/host
device IDs, 64-bit word order, reserved layout bits, malformed/truncated/oversized
inputs, incomplete information elements, identity mismatch, duplicate and old
generation rejection, queue overflow, loss metadata, quarantine and close.
Both the original exporter and new event API are exercised in one native run.

Publication checkpoint: implementation commit `7641aea87665cb8bd007ae327846081affab36cf`
is in [PR #3](https://github.com/Protonmatter/wifi-hardware-time/pull/3).
[Hosted run 37212980927](https://github.com/Protonmatter/wifi-hardware-time/actions/runs/37212980927)
passed both jobs: Linux discovered 218 tests (199 passed, 19 fixture/platform
skips), and Windows passed its native C harness and syntax/helper checks.
The local run passed all 218 with the private fixtures and ARM64 native toolchain.
Hosted success qualifies these software checks, not an unconnected hardware path.

An independent read-only review identified the initially permissive DS/Order
flag check. A native reproducer failed before the correction; the corrected
profile rejects each unsupported flag on both frame types without consuming
the sequence, then accepts a corrected Retry frame using that same sequence.

Rollback requires only removing generated artifacts or reverting the authored
changes. No system or driver setting needs restoration. Full local byte exports
and source buffers remain private.

## Next dependency

The running-driver milestone needs a vendor-supported return mechanism or a
controlled instrumented producer with proven buffer extent, ownership and
identity. At MLO callback entry, copy the event: the cache is updated afterward.
For management RX, preserve the frame and timing metadata before reduction.

The prototype supplies the receiving software contract and tests for that work.
It does not supply a kernel hook, firmware-ready signal or callback permission.
Hardware/QPC correlation and downstream clock-provider enablement remain separate
qualification steps. The previously requested no-disruption boundary remains.
