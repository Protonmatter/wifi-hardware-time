# TSF event ingress: original bytes, normalization and ownership

The exact driver retains a logical TSF payload length but can replace its pointer with a padded copy before the handler runs. Its upstream transport also has a separate declared length and can count fragmented buffers. We have traced these distinctions and callback cleanup. The offline decoder preserves supplied transport/event bytes; a live owned export and sampling-to-QPC correlation remain open.

## Contents

- [Scope and terms](#scope-and-terms)
- [The connected receive path](#the-connected-receive-path)
- [Upstream transport length and contiguity](#upstream-transport-length-and-contiguity)
- [Length and normalization](#length-and-normalization)
- [Ownership and the copy point](#ownership-and-the-copy-point)
- [Existing return candidates](#existing-return-candidates)
- [Owned software record](#owned-software-record)
- [A defensible host interval](#a-defensible-host-interval)
- [Reproduction and validation](#reproduction-and-validation)

## Scope and terms

Static inspection on 2026-10-05: ARM64 `qcwlanhmt8380.sys`, version `1.0.4374.1300`,
SHA-256 `ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`.
An RVA is an offset from that image's loaded base, not an application call address.

- **WMI:** Qualcomm's host/firmware message interface in this investigation.
- **TLV:** a tag, a declared length and the corresponding value bytes.
- **Original event:** here, the four-byte WMI header and its payload, excluding earlier transport headers.
- **Normalization:** adapting input to the driver's expected size, including adding zeros for absent fields.
- **Borrowed:** storage owned by the receive path, with a limited lifetime.
- **Owned:** copied bytes whose lifetime is controlled by the recipient.
- **QPC:** Windows's host interval counter; see the [glossary](../glossary.md).

This extends the [action-4 completion trace](action4-completion-and-report-contract.md)
and shared [management-event lifetime analysis](../adapters/qualcomm-management-timing-producer.md).
The private campaign's quarantine has not changed.

## The connected receive path

```text
HTC buffer: eight-byte transport header + declared payload + optional trailer
       |
       v
HTC receive -> strip transport header/trailer -> endpoint callback
  Keep declared length, aggregate length and contiguous spans distinct
       |
       v
Receive buffer: four-byte WMI header + event payload
       |
       v
wmi_control_rx (0x168ce0)
  Read low 24 header bits as event selector
  Remove four header bytes; retain payload pointer and received length
       |
       +---- preferred export point: copy saved header + original payload
       |                             [live exporter not implemented]
       v
wmitlv_check_and_pad_tlvs (0x1ba4e0)
       +---- short TLV ------> allocate 60 bytes, zero, copy original TLV
       +---- equal/long TLV -> borrow original input pointer
       |
       v
One decoded slot: pointer + element count + allocated flag
       |
       v
Registered 0x5005 handler (0x216b00), also passed original payload length
  Copy selected counter words; reduce to a low-word difference
       |
       v
Callback returns -> free allocated slot/wrapper -> release original buffer
```

Arrows show static control/data flow, not measured timing. The export branch is a
proposed integration point. Copying a pointer does not extend its data's lifetime.

| Connection | Exact-build evidence |
|---|---|
| Receive registration | `0x169e08` supplies `0x168ce0` while connecting the WMI control service |
| TSF registration | `0x21599c..0x2159b0` supplies event `0x5005`, handler `0x216b00` and null extra context to registry `0x16a078` |
| Header extraction | `0x168d7c..0x168d80` reads the header and masks its low 24 bits |
| Logical payload length | `0x168df8` loads receive-buffer `+0x38`, after removing the four-byte header |
| Decoder call | `0x168e08..0x168e0c` passes the low 32 bits of that length to `0x1ba4e0` |
| Callback call | `0x169004..0x169034` supplies the registered handler/context, decoded wrapper and same original length |
| Field reduction | `0x216b00` reads selected words through slot zero; it does not consume the separate length argument |
| Cleanup | `0x1690c0..0x169100` cleans decoded storage before releasing the original receive buffer |

Registration proves a selected static connection, not which live registry instance
or firmware producer supplied a historical report.

## Upstream transport length and contiguity

The [producer follow-up](hif-receive-buffer-producer.md) now connects the posted
pooled-buffer path, CE completion context and HIF queue. That selected path resets
fragment metadata and does not join payloads in its queue. It narrows the source
geometry without qualifying live capacity, synchronization or every buffer type.

The next upstream function, `HTCRxCompletionHandler` at `0x1f5f20`, reads an
eight-byte HTC transport header. HTC means host-target communication. Its header
contains an endpoint byte at `+0`, flags at `+1`, a little-endian 16-bit payload
length at `+2`, and a trailer length at `+4` when flag `0x02` is set.

The selected path checks that the buffer-length helper's result covers the
advertised payload plus eight bytes; it does not require exact equality. For
nonzero endpoints it supplies a callback length derived from:

```text
WMI event length = aggregate buffer length - 8 HTC bytes - trailer length
WMI TLV payload length = that result - 4 WMI bytes
```

This is a correction to treating buffer `+0x38` as a certified firmware wire
extent. The helper at `0x143218` can sum fragment lengths. Its total does not
prove a contiguous readable span beginning at the head pointer. The selected
path writes its calculated length back to `+0x38`; live fragment state and equality
with the advertised HTC payload were not inspected.

An eventual export must therefore preserve and reconcile:

- The original HTC header and its advertised extent.
- The logical aggregate length and the actual accessible spans or a qualified
  coalescing operation that joins them.
- Trailer presence, length and original bytes, separately from the WMI event.
- The WMI envelope and declared TLV extent already described below.

The receive-callback helper `0x1f58b0` invokes endpoint `+0x18` with context `+0x8`
when its multiple-packet callback is null. The service-connection code at
`0x1b6e08` copies the WMI registration's callback/context into those endpoint
slots. This connects transport dispatch to `wmi_control_rx`; it is not an
application subscription API or live endpoint attestation.

The trailer parser at `0x1f5c68` processes credit records with type 1. No TSF
request-token binding was established there. Other header bits and trailer bytes
remain uninterpreted evidence; a transport sequence is not automatically a
firmware request identifier.

## Length and normalization

Keep three lengths distinct:

1. **Logical payload length:** buffer `+0x38` after removing the WMI header;
   reconcile it with the upstream transport extent before calling it wire length.
2. **Declared TLV extent:** low 16 TLV-header bits plus four bytes for this fixed TLV.
3. **Expected decoded size:** 60 bytes from schema entry `0x39003c`.

That entry declares one fixed TLV: tag `0x18b`, size 60, `count_code=510`. On this
path the count code produces **one element when the TLV exceeds its four-byte
header**. It does not mean 510 elements or 60 received bytes. The 16-byte decoded
slot holds a pointer at `+0`, element count at `+8` and allocation flag at `+12`.

For one well-formed fixed TLV within the received payload:

| Original extent | Selected decoder operation | Interpretation |
|---|---|---|
| 48 bytes | Allocate 60, zero all 60, copy 48; allocation flag 1 | Last 12 bytes came from normalization |
| 60 bytes | Borrow input; allocation flag 0 | No size-padding allocation on this branch |
| More than 60 | Log a truncation warning, then borrow input; allocation flag 0 | The selected branch does not erase the header or copy only 60 bytes |

The padding copy at `0x1ba8b0` retains the original TLV header. A padded 48-byte
TLV therefore still declares 44 value bytes. Allocation size is not field presence.
Pointer/count publication occurs at `0x1ba8c4..0x1ba8d0`.

Generic decoder success is weaker than complete-record validation:

- Its selected loop can finish without consuming trailing bytes after the one
  expected descriptor; exact payload consumption is not established.
- Input shorter than a TLV header can return a zeroed wrapper without a populated
  slot. Decoder success alone does not establish a usable report.
- Our offline decoder rejects missing, partial, extra or padded input rather than
  inheriting that tolerance. No malformed input was sent to the driver.

**Actual running-firmware wire length remains unmeasured.** These findings locate
the length and explain possible transformations; they do not prove a live 48- or
60-byte response.

## Ownership and the copy point

**Selected boundary for a source-based or instrumented WMI exporter:** retain the
event before the original header load at `0x168d7c`, after obtaining and validating
the source span. This is more precise than simply saying "before `0x216b00`":

- For the selected pooled representation, the source is buffer `+0x10` plus
  offset `+0x30`. Logical length `+0x38` still includes the four-byte WMI header.
- `0x168d7c` reads that header; `0x168d80` retains only its low 24 bits as the
  dispatch selector. Save all four original bytes, including the upper byte.
- `0x168d94` stores the shortened logical length and `0x168da4` stores the advanced
  data offset. `0x168e0c` subsequently calls the normalizing decoder.
- The selected code reads the header before a local length check. An exporter
  must validate its own source span before reading or copying it; reaching this
  instruction is not an independent bounds certificate.
- The source length still derives from the earlier HTC processing. Preserve
  separately validated HTC metadata at A/B if investigating the transport extent;
  do not recover it by reading backward from a WMI pointer without a span contract.

These addresses identify an integration location, not an application API. No
breakpoint, hook or driver patch was installed. The inspector reports this as
`manual_wmi_copy_boundary`, with live source validation and installation false.
The [pool admission follow-up](hif-receive-buffer-producer.md#pool-construction-and-descriptor-admission)
also establishes why a successful map call cannot replace a coherency contract.

For `0x5005`, cleanup table entry `0x1bda9c` resolves to `0x1bb558`: check slot-zero's
allocation flag, then free its non-null pointer only when allocated. The common
tail at `0x1bb56c..0x1bb574` frees the wrapper and clears its owner pointer. The
dispatcher subsequently releases the original receive buffer.

- Normalized allocations end at callback cleanup.
- Borrowed bytes depend on the original receive-buffer lifetime.
- Copying the descriptor preserves neither lifetime.

The preferred instrumented/vendor-export point is **before the decoder call**,
with the WMI header saved before removal. Copy original header, payload and lengths
into independent storage while source access is valid; publish only after the
entire copy completes. Preserve event identity, loss and continuity information.
Preserve the earlier HTC envelope too when investigating how the logical length
was formed. Do not pass an aggregate fragment count to a flat-pointer copy.

A callback-side export could preserve a verified original TLV extent when its
header survives normalization. It must not copy 60 bytes merely because the schema
expects 60, and must account separately for the envelope and trailing bytes. The
pre-decoder boundary avoids those reconstruction steps.

No userspace return operation is connected to this point yet. Live implementation
still needs execution-level constraints, stable source access, bounded allocation
or a preallocated queue, publication consistency, loss reporting, cancellation and
teardown. No driver patch or hook was installed.

One release branch at `0x006ae0` decrements the pooled buffer's reference count at
`+0x198`. When it reaches zero, the buffer can return to its pool. Other branches
use different release operations. None establishes a userspace lifetime merely
because the numeric address remains unchanged.

## Existing return candidates

| Candidate | Located behavior | Consequence for TSF |
|---|---|---|
| Registered WMI send completion, `0x169220` | Releases the outgoing command buffer and transport cookie; updates selected command history | A transport completion, not an owned `0x5005` response |
| General command history, base pointer `0x3975d8` | Can copy up to 1024 outgoing payload bytes, with system time, into 128 records of stride `0x418` | Could preserve an action-4 request, not its firmware result |
| Selected command-completion history, base `0x4081a0` | Records a filtered command set; the filter excludes `0x5012` | Do not confuse an identically numbered event with a command in this namespace |
| Event history, base pointer `0x3975e8` | 128 records of 16 bytes, holding event ID and system time; no event-payload copy | Cannot recover the missing raw timing fields |
| Endpoint-zero control-message copy in `0x1f5f20` | Copies up to 256 bytes into HTC control storage and signals a kernel event | A separate control route, not the selected nonzero WMI callback route |
| HTC hex dump, `0x1f5720` | Formats bytes into diagnostic text; inspected receive calls cover errors or trailers | No normal complete TSF record-return path established |

These are distinct mechanisms. In particular, the general command history can
contain `0x5012` even though the selected completion history excludes it. Neither
is the incoming TSF report. Runtime history enablement and safe history retrieval
were not tested. No logging mask was changed to exercise the dump paths.

## Owned software record

The [decoder](../../research/tsf/decode_tsf_report.py) now accepts `event-wire`:

- Preserve all four WMI header bytes, including the uninterpreted upper byte.
- Require event selector `0x5005`; never treat it as a unique request token.
- Retain exact event/TLV bytes, original lengths and separate hashes.
- Require one exact 48- or 60-byte TLV under an explicit reference layout: a
  complete WMI event of 52 or 64 bytes, respectively.
- Take one immutable snapshot before interpreting either header or payload.
  Source must be stable during copying; post-copy source mutation is tested.
- Keep host observations absent and every live-clock qualification field false.

These are diagnostic reference profiles, not firmware-version negotiation. Declaring
`event-wire` cannot attest where bytes were copied. Source/schema identity, live
copy consistency and association still require acquisition evidence.
`--require-clock-input` continues to reject.

The additional `htc-wire` mode retains the eight-byte HTC header, WMI event and
optional trailer in one immutable envelope. It requires `--expected-endpoint`
from 1 through 8 and rejects endpoint zero, a mismatch, truncation or extra bytes
beyond the advertised HTC extent. It also checks the trailer's outer extent and
preserves its bytes without asserting that its records or other flag bits are valid.

Exact-length acceptance is deliberately stricter than the inspected driver path.
Supplying an expected endpoint is a caller assertion, not proof of live WMI
association. Source contiguity, endpoint attribution, trailer/flag semantics and
all clock qualifications remain false. No diagnostic mode reads kernel memory.

## A defensible host interval

The target is `request-start QPC <= fresh hardware sample <= report-entry QPC`.
Each part needs evidence:

- **Lower bound:** this request caused a new sample after request start. A changing
  counter or one pending host request cannot exclude cached/unsolicited/late reports.
- **Upper bound:** that same report contains the completed sample before report-entry
  QPC. Preserve association and producer sampling order.
- **Clock relationship:** establish identity, units, validity, split-word behavior
  and the relationship between sampled counters before fitting a conversion.
- **Continuity:** reject ambiguous epochs, loss and late data. Host process restart
  does not prove that firmware work has drained.

Variable delivery latency can widen a valid bound without invalidating it, provided
the causal conditions hold. The bound alone would not prove simultaneous TSF/SoC
latching or calibrated synchronization accuracy.

The existing conditional event-history write uses `KeQuerySystemTimePrecise`, not
QPC. Unlike management event `0x7001`, `0x5005` is not excluded by that selected
comparison. Live history enablement was not inspected, and no report-entry QPC
was acquired in this pass.

## Reproduction and validation

From the repository root, Python 3.11+ and existing dependencies:

```powershell
python research/tsf/inspect_tsf_ingress.py `
  --driver 'C:\path\to\owned\qcwlanhmt8380.sys' `
  --output artifacts/tsf-ingress-new.json

python research/tsf/decode_tsf_report.py artifacts/synthetic-tsf-event.bin `
  --event-id 0x5005 --reference-layout reference-60 `
  --origin fixture --representation event-wire

python research/tsf/decode_tsf_report.py artifacts/synthetic-htc-event.bin `
  --event-id 0x5005 --reference-layout reference-60 `
  --origin fixture --representation htc-wire --expected-endpoint 2

python -m unittest discover -s tests -p test_tsf_ingress.py -v
python -m unittest discover -s tests -p test_decode_tsf_report.py -v
```

- Supply the example event file; no live firmware event is bundled.
- Ordinary file permissions suffice; no elevation or UAC request was used.
- Inspector: exact image, at most 16 MiB plus one rejection byte, new output file
  with an existing parent. Outputs addresses/hashes, not driver bytes.
- Event decoder: at most 64 bytes plus one rejection byte in `event-wire` mode.
  `htc-wire` allows at most 327 plus one: eight header bytes, up to 64 WMI bytes
  and up to 255 trailer bytes. These are tool/profile bounds, not a device maximum.
  The example endpoint 2 is synthetic, not a discovered live endpoint.
  `--expected-endpoint` is required only for `htc-wire`.
  Both modes emit diagnostic JSON on stdout.
  Hardware-derived raw output belongs in ignored private evidence locations.
- Exit `0`: diagnostic success; `1`: rejected input/I/O/unqualified clock admission;
  `2`: CLI misuse. No hardware changes or operational rollback.
- Set `WIFI_TIME_DRIVER_FIXTURE` to include the exact-image test. Absent fixtures
  skip that test; a skip does not qualify the image.

Ghidra receipts in `artifacts/tsf-event-boundary-20261005/` record two complete
passes of five and seven functions with one overlap: eleven distinct functions,
no decompilation failures or truncation. The inspector verifies selected
registration/length/flag instructions, schema, cleanup target and range hashes;
broader interpretation remains manual.

The subsequent return-route passes are under `artifacts/tsf-return-route-20261005/`:
three transport functions, four receive/history functions and five framing
functions, with one overlap. All eleven distinct functions exported and decompiled
without truncation or failure. They add the callback bridge, pooled-release path,
aggregate-length helper, trailer parser and the distinct history/control-copy routes.

Local validation on 2026-10-05:

- Python compilation passed for `research` and `tests`.
- The configured full suite passed **293 tests with zero skips**, including native
  C and exact Windows-image fixtures. The transport follow-up adds seven tests to
  the earlier 286-test suite.
- Index consistency, documentation navigation, existing diagram synchronization
  and diff whitespace checks passed. This page's new diagram is plain text.
- Both Ghidra receipts and the exact-build ingress-inspection receipt completed.
- All three return-route Ghidra receipts and the extended inspector completed.
- Final interface check: active Qualcomm Wi-Fi Up, driver `1.0.4374.1300`, same
  driver hash. No elevation, firmware request, logging-mask change or device-mode change.

Tests cover selected static evidence, header retention, exact-length rejection
and detached software ownership. They do not exercise firmware, concurrent kernel
copying or physical timing. Hosted results must be checked on the exact containing
revision in [PR #3](https://github.com/Protonmatter/wifi-hardware-time/pull/3/checks),
separately from these local results.

Return to [TSF research](README.md) or [current findings](../knowledge/current-findings.md).
