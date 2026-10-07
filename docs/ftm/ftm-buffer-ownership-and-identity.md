# FTM buffer ownership, request reuse and parse completion

The complete FTM response lives in a reusable driver-owned buffer, and its request identifier wraps after 256 increments. Receiving a final fragment is also different from successfully parsing its contents. These findings define requirements for a trustworthy raw export, but the inspected paths still do not return complete timestamp records to userspace.

<!-- current-context:2026-10-04 -->
**Current context (2026-10-04):** QXDM WLAN RTT definitions are a new schema lead. They have not been matched to a complete live four-event export from this adapter. See [current findings](../knowledge/current-findings.md).
<!-- /current-context -->

**Terms:** FTM is Wi-Fi ranging. A fragment is part of a response; aggregation
combines measurements. Ownership determines who may retain or release a buffer.
An epoch distinguishes periods of continuity. RVAs identify on-disk code, not
safe runtime entry points. See the [glossary](../glossary.md).

## Contents

- [Scope](#scope)
- [Who owns the complete response](#who-owns-the-complete-response)
- [What the request byte identifies](#what-the-request-byte-identifies)
- [Completion has separate stages](#completion-has-separate-stages)
- [Another dump candidate](#another-dump-candidate)
- [Exporter implications and validation](#exporter-implications-and-validation)

## Scope

Date: 2026-10-03, America/New_York. Research baseline
`0e866ed6b2409231c100af75a6aef97c6bdd2fa3`. The inspected ARM64 driver is version
1.0.4374.1300, SHA-256
`ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`.

This is file inspection and finite arithmetic checking. No FTM exchange, device
request, runtime memory read, debugger, logging change or lifecycle operation
was performed. The [previous export investigation](ftm-raw-access-followup.md)
and [notification routing](ftm-notification-routing.md) supply the earlier scope.

## Who owns the complete response

| Exact-build location | Operation | Meaning for retrieval |
|---|---|---|
| `RttInit`, `0x145e7c..0x145e8c` | Clear `context+0x89e0` for `0x2f8` bytes | Request and accumulation state are reinitialized |
| `0x145fb4..0x145fc0` | Allocate `0x1388` bytes and retain the pointer at `context+0x8a48` | Driver owns persistent 5,000-byte merge storage |
| `0x147a28..0x147a50` | Append payload after incoming response `+0x18` | Original fragment envelopes are outside the merged payload |
| `0x147a98` | Reset accumulated length after parsing | Allocation remains and can be reused; reset does not publish an immutable record |
| `RttDeinit`, `0x145d84..0x145d94` | Free and null the retained buffer pointer | A retained raw pointer has no independently established caller lifetime |

No ownership transfer to userspace was identified. Bytes left behind after the
length reset are not a valid retained-record API. An export needs an owned copy
before reuse and separate request/subtype/fragment metadata.

Deinitialization unregisters event `0x27004` later at `0x145dd8..0x145de0`.
That local ordering alone does not prove callback serialization or a live race;
surrounding lifecycle exclusion remains outside this finding.

## What the request byte identifies

The outbound and inbound association can now be connected:

1. `0x146acc..0x146af8` reads, increments and stores the byte at `context+0x89ec`,
   then copies it to temporary request `+0x0a`.
2. The installed operations slot `+0x37690` selects builder `0x1db390`.
3. At `0x1db464..0x1db478`, the builder writes the zero-extended byte to outgoing
   buffer `+0x0c`; it submits command `0x27001`.
4. Incoming handler `0x147964..0x147978` compares response `+0x08` low 16 bits
   with the current request-context byte.

Consequences:

- The value wraps `255 -> 0 -> 1`, repeating after 256 increments.
- Increment happens before submission, so it is not a successful-exchange count.
- Request preparation groups compatible targets. The byte is not a proven
  per-peer, per-frame, burst, dialog or epoch identifier.
- The inspected timeout/cancel paths pass the current byte without incrementing
  it. Cancellation does not certify that delayed reports have drained.
- A host-generated wider sequence number cannot, by itself, distinguish an old
  response carrying the same reused firmware byte.

The installation path is reconstructed from the file; this pass did not observe
which function-table instance was active at runtime.

## Completion has separate stages

The response handler tests `flags & 0x3e` at `0x1479a4..0x1479d8`. Zero resets
the accumulated length; a nonzero value appends without an expected-next-value
comparison in this handler. Bit 0 separately indicates more fragments.

These local predicates do not independently prove ordered, duplicate-free,
complete fragments. Transport guarantees outside this scope remain unknown;
this is not a claim that live duplicate or reordered fragments were accepted.

The parser then has its own success boundary:

- It writes some derived target values before later structural validation.
- Invalid structure returns an error at `0x147554..0x147558`.
- Its successful path signals `KeSetEvent(context+0x89f8)` at
  `0x14755c..0x147578`. This is host task signaling, not a hardware sampling fence.
- The outer handler calls the parser at `0x147a88`, clears length at `0x147a98`
  and returns zero at `0x147a9c` without propagating that parser result.

Therefore final-fragment receipt, outer-handler success, structural parse
success and valid ranging measurements must remain separate states. Changed
target values or a zero outer return value cannot certify a complete raw record.

## Another dump candidate

Byte-dump helper `0x1db760` has a direct caller at `0x1dcb10`. That caller is
labeled `wmi_unified_nat_keep_alive_send`; it supplies a newly built outgoing
NAT keep-alive payload and submits command `0x17002`. This is not an identified
raw-FTM response export. Together with the earlier location-information-only
dump, it narrows another candidate without proving all possible exports absent.

## Exporter implications and validation

A useful export needs:

- An immutable complete payload copy, made before reuse, with an explicit
  structural parse result.
- Original envelope/fragment identity, request generation, peer/exchange identity
  and clock epoch; the wrapping byte alone is insufficient.
- Separate timestamp units, meaningful widths, validity and physical event
  definitions. The opaque per-record region has not gained those semantics.
- Bounds, duplicate/loss accounting, cleanup and a defined userspace return ABI.

The [acceptance gate](../evidence/raw-timestamp-export-gate.md) remains closed.
The existing aggregate callback does not provide this record.

Eight freshly disassembled ranges containing 1,333 instruction lines matched the
retained disassembly. The driver hash and relevant copy/free/synchronization
imports were checked. Finite checks reproduce byte wrap and the limited append
predicate; they are not firmware emulation or observed hardware corruption.
Authored notes and receipts are under ignored `artifacts/FtmExportInvestigation/`.
