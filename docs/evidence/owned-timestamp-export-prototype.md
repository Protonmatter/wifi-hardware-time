# Owned timestamp export prototype

The repository now implements an offline C11 exporter that copies and validates
bounded synthetic timestamp records before publication. This provides an owned
application boundary for testing meaning declarations, identity, validity and
lifetime. It does **not** satisfy the [real raw timestamp acceptance gate](raw-timestamp-export-gate.md).

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** A QUTS client-owned byte return is now located statically. Keep client ownership, server publication, firmware identity and timing accuracy as separate qualification states. See [current findings](../knowledge/current-findings.md).
<!-- /historical-context -->

Every accepted record has synthetic provenance and `live_clock_eligible == 0`.
There is no hardware backend, device access, private IOCTL, kernel handler, driver
patch, firmware drain, QPC bracket or calibrated timing claim. The layout uses
native endian integers; it is not yet a production or cross-endian transport ABI.

## Contents

- [Purpose and files](#purpose-and-files)
- [Record and identity contract](#record-and-identity-contract)
- [Publication, lifetime and health](#publication-lifetime-and-health)
- [Build and validation](#build-and-validation)
- [Limits and next dependency](#limits-and-next-dependency)
- [Glossary](#glossary)

## Purpose and files

The [header](../../research/export_contract/timestamp_export.h) declares the API,
the [implementation](../../research/export_contract/timestamp_export.c) owns the
queue, and the [native harness](../../tests/native_timestamp_export.c) supplies
synthetic fixtures. The [PowerShell runner](../../research/export_contract/Test-TimestampExport.ps1)
builds and executes the harness; the [Python runner](../../tests/test_native_export_contract.py)
integrates it with existing offline unittest discovery when a compiler is present.

The existing [saved-evidence observation contract](../../research/evidence/hardware_observation.py)
remains a separate diagnostic format. This prototype does not convert that evidence
into new hardware semantics or alter downstream capability flags.

## Record and identity contract

`te_record` contains no pointers. Its 208 bytes comprise fourteen `uint32_t`
fields, eleven `uint64_t` fields and 64 inline payload bytes. Compile-time offsets
and size assertions reject incompatible layouts; the declared fields account for
every byte, so no C padding is exported. Reserved fields and unused payload bytes
must be zero. The profile, units and reference enums accept only defined values.

| Fields | Meaning and acceptance rule |
|---|---|
| `schema`, `size` | Version 1 and exactly 208 bytes; partial or oversized input is rejected. |
| `timestamp`, `unit`, `rate_hz`, `meaningful_bits` | Unsigned 64-bit storage, ticks per second, width 1–64; upper bits outside that width must be zero. Zero timestamps are representable. |
| `reference` | Explicit simulated RX-start or TX-start reference; these names do not establish actual PHY/MAC event semantics. |
| `source_scope`, `clock_id` | Scope and source-clock label, separate from event identity. Clock label zero is valid, not an unknown sentinel. |
| `session`, `epoch`, `generation` | Fixed nonzero software-session ID; increasing software epoch and independently declared synthetic-backend generation. |
| `event_id`, `peer_id`, `link_id` | Nonzero monotonically increasing event ordinal per generation, scoped peer ID and link label. Link zero is valid. |
| `profile`, `request_token`, `token_binding` | Autonomous profile requires no token and binding zero. Solicited profile requires a nonzero backend-associated token and explicit backend binding. |
| `timestamp_valid`, `complete` | Both must equal one. This checks declarations, not the truth of an upstream parser or hardware flag. |
| `provenance`, `live_clock_eligible` | Synthetic only; eligibility must remain zero. No hardware/driver/firmware provenance is invented. |
| `payload_size`, `payload` | At most 64 owned inline bytes; unused tail must be zero. No fragment assembly is performed. |

`te_init` binds profile, clock semantics, source, session, peer and link. Publication
must match that binding and the current epoch/generation. Changing those fixed
identities requires closing the old context and explicitly initializing a new
context. Reinitializing a live context violates the API lifetime contract.
The caller must allocate a fresh session identity for each new instance. Context
lifetime is in-process only: there is no persistent quarantine store. Close,
reinitialization or process restart cannot prove firmware drain or safely clear a
real acquisition quarantine. The harness uses synthetic sessions only.

Autonomous observations need no request ID. For solicited records, `te_begin`
registers the expected event and backend token. Event ordinals and tokens must
increase within a generation; token reuse is deliberately rejected there. A host
tag is rejected as association proof. These synthetic declarations must eventually
be replaced with independently evidenced producer bindings; a caller setting an
enum cannot authenticate hardware provenance.

## Publication, lifetime and health

The exact concurrency model is **external serialization**. One owner must hold
the same lock, or execute on one thread, around every operation on a context,
including initialization, publication, reads, health snapshots, cancellation,
generation changes and close. Input must remain stable for the entire call; output
and input buffers must be valid and must not overlap the context or one another.
The library has no internal lock, atomics, allocation or retained caller pointers.
Publication is atomic only under that caller-enforced contract. No concurrent
kernel callback, IRQL, live-lock or full asynchronous IOCTL cancellation behavior
is implemented or qualified.

`te_publish` copies a complete input to private stack storage, validates every
field, then writes the owned queue slot before incrementing the published count.
Invalid records never partially update a queue slot. Bad, mismatched, duplicate,
reordered or stale records increment the rejection counter. The two-slot FIFO
drops the newest admitted event when full, increments loss, and consumes that
event identity so a repeated dropped event cannot be silently republished.

`te_read` returns exactly one complete record. A short buffer, null output or other
failed read leaves queue and caller output unchanged; a valid `written` pointer
receives zero on failure. Success writes 208 bytes, consumes one slot and clears
it. The caller owns its returned copy after the call, including across close or
later generation changes. No record contains a producer pointer to dereference
after buffer reuse or teardown.

`te_snapshot` exports a bounded, pointer-free 64-byte health structure with schema,
size, cumulative loss/rejection counts, session/epoch/generation, queued count,
quarantine and closed state. It also works after close. To associate health with a
read, hold the same serialization lock across **both** `te_read` and `te_snapshot`;
do not release it between those calls. Consumers must inspect loss and rejection
counts rather than treating `TE_OK` as loss-free acquisition. Counts saturate at
`UINT64_MAX` and are retained across generation transitions; reinitialization starts
a new software context and resets them.

Timeout or cancellation of an active solicited request quarantines that generation.
Further publications and requests are rejected. Previously completed queued
records remain readable with their original identities; quarantine remains visible
through the health snapshot. Only `te_new_generation` with **both** a greater
software epoch and a greater explicitly backend-identified synthetic generation
clears quarantine. Software epoch advancement or a host tag alone is rejected.
The transition clears queued old records and counts them as loss. It cannot prove
firmware drain or distinguish real producer generations without a qualified backend.
Close also clears the queue, counts discarded records, and rejects subsequent I/O.

| Status | Meaning |
|---|---|
| `TE_OK` | Structural operation succeeded, never hardware qualification. |
| `TE_INVALID` | Unsupported, malformed or incomplete record/argument. |
| `TE_MISMATCH` | Current identity or active request binding differs. |
| `TE_STALE` | Duplicate/reordered event, reused token, or non-increasing generation. |
| `TE_FULL` | New admitted record was dropped; inspect loss count. |
| `TE_SMALL_BUFFER`, `TE_EMPTY` | No record consumed or output bytes written. |
| `TE_QUARANTINED`, `TE_CLOSED`, `TE_BUSY` | Lifecycle prevents the requested operation. |

## Build and validation

Preconditions: existing Visual Studio C compiler and Windows SDK for the desired
target, or a C11 compiler on PATH for the Python runner. Ordinary user permissions
are sufficient. No dependency installation or network access is performed.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File research/export_contract/Test-TimestampExport.ps1 -Architecture arm64
python -m unittest discover -s tests -p test_native_export_contract.py -v
python -m compileall -q research/export_contract tests/test_native_export_contract.py
```

The Windows script accepts `-Architecture arm64` (default) or `x64`, compiles with
`/std:c11 /W4 /WX /O2 /Brepro`, and executes the resulting native harness. Output
is confined to ignored `artifacts/owned-export-<architecture>`. Exit 0 means offline
tests passed; exit 1 means compilation or execution failed. Expected success text:
`owned timestamp export: all offline contract checks passed`.

The Python runner uses temporary output, compiler/test timeouts of 60/15 seconds,
and skips if no compiler is on PATH. `WIFI_TIME_NATIVE_CC` selects one executable
name/path; if explicitly configured but unavailable, the test fails. MSVC requires
an initialized developer environment. The PowerShell script provides one.

Actual local validation on 2026-10-03 used installed ARM64 MSVC 14.44.35207. The
native adversarial harness passed with warnings treated as errors. The initial
test-first placeholder failed its first initialization assertion; the zero-ID and
health-snapshot additions were also observed failing before implementation. Tests
cover invalid widths, high bits, schema/size, validity, payload bounds/tail, identity
mismatch, token binding, queue overflow, public health, short-buffer immutability,
owned-copy lifetime, duplicates, timeout/cancellation, old-generation rejection,
flush accounting, counter saturation and 64-bit maximum values.

Rollback: remove the generated `artifacts/owned-export-<architecture>` directory
after preserving any desired build evidence. The source change is isolated to
the exporter, harness, runner and this document. No device or persistent system
state needs rollback.

## Limits and next dependency

The model publishes one complete event at a time. FTM on-air token interpretation,
fragment reassembly, fragment
sequence qualification, timestamp-valid producer flags, peer/link mappings,
independent generation identity, hardware meaning, exact firmware schemas and
hardware-to-host conversion remain unqualified. A stale pointer supplied directly
by a caller violates the valid-buffer precondition; this C API cannot safely probe
arbitrary memory. Bounds checking does not make arbitrary pointers safe.

This is one proposed payload boundary for a future supported exporter. It reserves
no IOCTL number and is not an installed driver ABI. A real adapter must establish
the safe producer-copy point, supply exact build/schema provenance and pass the
negative cases in the raw gate before the first bounded hardware acquisition.
Synthetic success does not authorize or complete that acquisition.

## Glossary

- **Owned record:** a value copy whose lifetime is independent of producer storage.
- **Source clock:** the counter domain; separate from the frame/exchange event.
- **Epoch:** software continuity label; not evidence that firmware drained reports.
- **Generation:** backend-declared producer lifetime identity, synthetic in this model.
- **Quarantine:** lifecycle state rejecting further admissions after uncertainty.
- **Structural acceptance:** fields and lifecycle satisfy this local schema; it does
  not authenticate their physical meaning or qualify a clock.
