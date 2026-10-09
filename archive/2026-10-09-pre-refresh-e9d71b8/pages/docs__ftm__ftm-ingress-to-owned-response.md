# FTM ingress to an application-owned response: the remaining handoff

> **Archive — not current operating instructions.** Historical documentation at [e9d71b843651](https://github.com/Protonmatter/wifi-hardware-time/commit/e9d71b84365122ff2640e240b20fc1dbb834388a). Relative links are rebased for reading. [Exact original bytes](../originals/docs__ftm__ftm-ingress-to-owned-response.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

The driver-side path into the FTM handler is now traced through event decoding, registration and cleanup. Its temporary decoded object does not become application-owned, and its event history stores host time rather than measurement payloads. A complete export still needs a bounded copy during valid ownership, preserved identity and an explicit application return contract.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** QXDM WLAN RTT definitions are a new schema lead. They have not been matched to a complete live four-event export from this adapter. See [current findings](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/knowledge/current-findings.md).
<!-- /historical-context -->

## Contents

- [Scope and terms](#scope-and-terms)
- [Verified driver-side connection](#verified-driver-side-connection)
- [Decoded object and lifetime](#decoded-object-and-lifetime)
- [Event history is not a payload archive](#event-history-is-not-a-payload-archive)
- [The missing application handoff](#the-missing-application-handoff)
- [Reproduce and validate](#reproduce-and-validate)

## Scope and terms

- **FTM:** Fine Timing Measurement, the Wi-Fi ranging procedure.
- **Firmware event:** a message from the adapter to its host driver. Receiving
  that message is later than the physical radio event it may describe.
- **TLV:** a tag, length and value describing one field or group of bytes.
- **Borrowed pointer:** access to storage owned elsewhere; retaining its address
  does not extend that storage's lifetime.
- **Owned response:** data copied into storage with a defined lifetime controlled
  by the recipient, rather than an address into temporary driver memory.
- **RVA:** offset in the inspected driver image, not a supported call address.
- **Epoch:** a generation of clock continuity; a host sequence alone does not
  establish which firmware epoch produced a delayed response.

This is static analysis of Qualcomm ARM64 driver `1.0.4374.1300`, SHA-256
`ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`.
It adds the ingress side of the [buffer-ownership investigation](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/ftm/ftm-buffer-ownership-and-identity.md).
No running-driver memory, private command, trace, FTM exchange or setting was
accessed for this work. Driver identity does not qualify the loaded firmware's
timestamp schema.

## Verified driver-side connection

Read this table from top to bottom. Each arrow is a statically traced handoff,
not a newly observed live execution.

| Step | Exact-build evidence | Data and ownership consequence |
|---|---|---|
| Event buffer -> dispatcher | `wmi_control_rx`, `0x168ce0`; `0x168d7c..0x168dd8` | Extract the low 24-bit event selector and advance past the four-byte transport header |
| Payload -> decoded object | `0x168df8..0x168e0c` calls `0x1ba4e0` | Supply payload pointer, length, event selector and an output-object pointer |
| Event selector -> registered FTM handler | `0x145eac..0x145ec0` registers `0x1477f0` for `0x27004`; registry `0x16a078`, lookup `0x16a030` | Connect the FTM registration to the dispatcher's handler table |
| Decoded object -> callback | `0x169004..0x169034` | Pass the decoded object, payload length and registered callback context to the selected handler |
| First decoded entry -> merge storage | `0x147874..0x147898`, `0x147a28..0x147a50` | Read the first entry's pointer/count; copy its fragment body after the 24-byte OEM envelope into persistent driver storage |
| Final fragment -> parser | `0x147a80..0x147a98` | Parse assembled data, then reset accumulated length; storage remains reusable |
| Callback return -> cleanup | `0x1690c0..0x169100` | Release decoded-object allocations, then invoke a release path for the original event buffer |

Registry fields are connected on both sides: registration writes the handler at
`(index+0x83)*8`, its context at `(index+0x183)*8`, and event ID at `(index+6)*4`.
Lookup compares the event ID and checks that its handler is non-null. Dispatch
loads the same handler/context positions. This resolves the indirect call for
the inspected registration path; it does not inspect the live table instance.

The current FTM handler was registered with a null extra callback context. The
registry is a driver-internal facility, not a userspace subscription API.

## Decoded object and lifetime

The event-schema lookup at `0x1bdfe0` selects the event table beginning at
`0x38fae0`. The `0x27004` entry is at `0x3900c8` and declares three descriptors:

| Decoded entry | Expected outer TLV tag | Encoded element size | Variable flag | Meaning established here |
|---|---|---|---|---|
| 0 | `0x11` | 1 byte | 1 | The FTM handler reads this entry's pointer and byte count |
| 1 | `0x293` | 20 bytes | 0 | Schema shape only; no timestamp semantics assigned |
| 2 | `0x11` | 1 byte | 1 | Schema shape only; no timestamp semantics assigned |

All three have schema `count_code=510`. That encoded value is **not** evidence
of 510 measurements or a 510-byte live response. These outer transport tags also
must not be confused with the inner OEM measurement tags already documented.

The generic decoder allocates a descriptor array with 16 bytes per entry. Each
entry contains a pointer at `+0`, count at `+8` and allocation flag at `+12`:

- Its direct-reference branch stores a pointer into the original input and a
  zero allocation flag (`0x1ba820..0x1ba838`).
- Normalization branches can allocate/copy storage and set the allocation flag
  (`0x1ba730..0x1ba7d8`, `0x1ba83c..0x1ba8c0`).
- The common publication instructions store the pointer and count at
  `0x1ba8c4..0x1ba8d0`.

Consequently, seeing a decoded object does not imply it owns all referenced
bytes. For this table's first variable byte-array entry, the inspected normal
decode branch uses the direct-reference form. This is static branch reasoning,
not a live observation of the firmware payload.

After the callback, cleanup wrapper `0x1bae60` selects its event branch using
`0x27004` (literal at `0x1bdd58`). The branch at `0x1bb238` checks allocation flags
for all three entries and frees allocated non-null storage. The shared tail at
`0x1bb56c..0x1bb574` frees and nulls the decoded object. Borrowed input bytes are
handled by the subsequent event-buffer release path; not every release implies
an immediate free, because that path can use reference counts.

This establishes two separate lifetime limits:

- The decoded wrapper and any normalization allocations are temporary callback
  data. They cannot be handed to an application as retained pointers.
- The merge buffer persists longer, but its logical contents reset/reuse. Its
  address is not an immutable complete response either.

The event decoder's structural success is not proof that OEM fragments are
complete, that the inner measurement parser succeeds, or that timestamps have
known meaning. Those remain separate checks.

## Event history is not a payload archive

Before calling the registered handler, an optional branch at
`0x168f80..0x168fdc` writes an event-history slot:

- A 128-slot index wraps with mask `0x7f`.
- Each slot is 16 bytes. The inspected writer stores the event selector at
  offset zero and supplies slot `+8` to time helper `0x185a20`.
- That helper resolves through import `0x2ed3c0` to
  `KeQuerySystemTimePrecise`.
- The inspected writer does not copy the event payload into the history slot.

This is a host system-time observation during dispatch, before the FTM callback.
It is neither a hardware timestamp nor a QPC sampling bracket. The clock unit's
representation does not establish sampling accuracy. No safe application getter,
publication protocol or concurrent snapshot contract for this history is claimed.

## The missing application handoff

The observed chain ends inside the driver. The existing aggregate completion
does not return the original per-measurement records. A proposed integration
would need the following additional boundaries; **none is implemented here**:

| Boundary | Required behavior | Why it matters |
|---|---|---|
| Capture during ownership | Copy the needed ingress bytes, lengths and original envelope metadata while their owner guarantees access | Avoid stale pointers and preserve information omitted by merge/aggregation |
| Validate and associate | Retain structural status, fragment order/loss, actual request/peer/exchange identifiers and producer generation evidence | The wrapping request byte and final-fragment flag are insufficient |
| Publish an immutable result | Use bounded storage, explicit commit/completion, overflow accounting and reset/teardown exclusion | An equal-copy polling heuristic does not prove safe publication |
| Return owned bytes | Define a versioned response with lengths/status and copy into recipient-owned storage | Application lifetime must not depend on a recycled driver buffer |
| Qualify clock meaning | Establish source, units, meaningful width, reference event and validity for each value | Successfully exporting opaque bytes is diagnostic access, not a clock capability |

FTM offers a bounded first instrumentation candidate because its merge allocation
and final-fragment parser boundary are identified. This does not make that site
safe to patch: callback execution context, exclusion, cancellation and teardown
must be qualified in an authorized driver implementation. Preserve ingress
metadata separately because the merge copy excludes each original envelope.

The RX alternative similarly needs a copy while the original descriptor is owned,
before buffer reuse, followed by a defined export of timestamp and packet metadata.
Its [normal receive path](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/qualcomm-rx-export-boundary.md) still has no
established complete-record return interface.

An existing vendor facility could satisfy these boundaries if its actual ABI and
producer connection are established. Otherwise they require source-level driver
instrumentation or vendor cooperation. An application wrapping the current
aggregate callback cannot recover fields already omitted from that response.
The [complete-record gate](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/raw-timestamp-export-gate.md) remains closed.

## Reproduce and validate

The inspector needs existing Python dependencies, normal read permission and the
owned exact-build SYS file. It does not require elevation or contact the adapter.

```powershell
$env:WIFI_TIME_DRIVER_FIXTURE = 'C:\path\to\owned\qcwlanhmt8380.sys'
python research/ftm/inspect_ftm_ingress.py `
  --driver $env:WIFI_TIME_DRIVER_FIXTURE `
  --output artifacts/ftm-ingress-static.json
python -m unittest discover -s tests -p test_ftm_ingress.py -v
```

- `--driver` selects the owned file; other builds are rejected before extraction.
  The CLI reads at most 16 MiB plus one rejection byte.
- `--output` must name a new file in an existing directory. Existing output is
  not overwritten. The JSON contains offsets, hashes, schema fields and selected
  branch matches, not driver bytes, live measurements or the input path.
- Exit 0 means offline inspection completed; 1 means input/I/O failure; 2 means
  invalid CLI usage. There is no operational rollback; only a local receipt is
  created.
- Tests cover synthetic table bounds, missing/duplicate selectors, malformed
  trailing entries and exact-build rejection. The owned-file test is optional
  in CI and was run locally. These are not live record-admission tests.

Fresh disassembly matched all eight selected ranges, comprising 4,061 instruction
or literal lines. The inspector's range hashes match that comparison receipt.
The large cleanup range includes dispatch cases not all manually traced; this
pass specifically follows event `0x27004`. Aligned branch scans can include data
words and do not prove complete call coverage. Behavioral conclusions rely on
the manual path inspection described above.

Local receipts remain under ignored `artifacts/FtmIngressInvestigation/`.
No proprietary binary, disassembly, endpoint identity or live response is added
to Git. This validates the stated static connection and lifetime boundaries,
not an application export, fresh hardware sampling or calibrated accuracy.
