# Packet-log return path and its limits

> **Archive — not current operating instructions.** Historical documentation at [e9d71b843651](https://github.com/Protonmatter/wifi-hardware-time/commit/e9d71b84365122ff2640e240b20fc1dbb834388a). Relative links are rebased for reading. [Exact original bytes](../originals/docs__memory-ring__packetlog-return-path.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

An existing private response path can copy the driver's binary packet log into a returned buffer. This is a concrete transport lead, but it does not yet return one trustworthy management event. The log writer can advance its position before copying a payload, the inspected reader has no matching snapshot lock, and stopping the logger can free its storage. No live request was sent.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** The QUTS client is a separate owned-byte return candidate. It does not repair the existing ring publication or temporary-buffer lifetime gaps. See [current findings](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/knowledge/current-findings.md).
<!-- /historical-context -->

## Contents

- [Outcome and scope](#outcome-and-scope)
- [The connected return path](#the-connected-return-path)
- [Selector precedence matters](#selector-precedence-matters)
- [What the log preserves](#what-the-log-preserves)
- [Copy, publication and teardown](#copy-publication-and-teardown)
- [Other return candidates](#other-return-candidates)
- [Next dependency and disposition](#next-dependency-and-disposition)
- [Reproduce the static checks](#reproduce-the-static-checks)
- [Glossary](#glossary)

## Outcome and scope

- Research baseline: `ebe1f21158d0b1f6ec00d7782217a0d77f0c19ca`.
- Inspected ARM64 driver: `qcwlanhmt8380.sys` 1.0.4374.1300, SHA-256
  `ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`.
- Evidence: owned file, existing disassembly, fresh disassembly of selected
  ranges, operations-table pointers and offline tests.
- No device open, IOCTL, trace, packet-log start/stop, register read or clock change.

This **packet log** is a separate buffer family from the formatted diagnostic
memory log used in the earlier TSF investigation. Its return path does not
retroactively qualify retrieval from that other ring.

The new result connects a real binary source to the previously identified IHV
response bridge. Application invocation, full input/output validation, source
identity, record completeness and safe snapshot behavior remain unqualified.

## The connected return path

Read the table from top to bottom. Each connection is static and build-specific;
the addresses identify code, not callable userspace APIs.

| Stage | Exact-build evidence | Data carried |
|---|---|---|
| Vendor request handler | `WdiPropertyIhvRequestHdlr`, `0x12e4f0`; call at `0x12e750` | Temporary input/output buffer passed to `MpNicSpecificExtension`, `0x11cde8` |
| Selected combined-read branch | `0x11d3b4..0x11d3d4` calls `0x37e00` | Buffer, capacity and output-count pointers |
| Result envelope | `0x37e00..0x37ea8` | A 12-byte prefix followed by packet-log output; capacity/count handling still needs a complete external-contract review |
| Header and body copy | `0xcdd8..0xce9c` invokes operations slots `+0x270` and `+0x278` | Header first, then body at the returned header-byte offset |
| Operations table | Initializer `0x188174..0x18817c` installs table `0x341840` | Slot `+0x270` is `0x18ae30`; slot `+0x278` is `0x18ae40` |
| Leaf forwarding functions | `0x18ae30` branches to `0x1ebe50`; `0x18ae40` to `0x1ebdc0` | Resolve the two indirect targets for this installed-table path |
| Packet-log readers | `0x1ebe50`, `0x1ebdc0`, shared copier `0x1ebbf8` | Eight-byte log header and ring content, with local cursor/wrap handling |
| Serialize returned bytes | After successful dispatch, `0x12e75c..0x12e7a0` calls `0x1619b0` | Temporary buffer and returned byte count |
| Complete the request | `0x12e860` calls `0x13a890` | Response copied through the existing completion mechanism |

This is stronger than finding an isolated copier. It still does not prove that
an application can safely invoke this operation or that the copied source is
consistent. Full external framing, access control, length/error handling and
all upstream synchronization are not certified here.

Microsoft's [WlanIhvControl](https://learn.microsoft.com/en-us/windows/win32/api/wlanapi/nf-wlanapi-wlanihvcontrol)
provides a generic vendor-control envelope. Its existence does not specify this
driver's payload schema or make these internal selectors a supported request.

## Selector precedence matters

The same numbers have different roles depending on where dispatch begins:

| Internal selector | Outer `MpNicSpecificExtension` behavior | Inner query-dispatch behavior |
|---|---|---|
| `0xff500001` | Intercepted and routed to `Hw11PktlogStart` (`0xd020`) | Has a header-reader case through `0xcfa0` |
| `0xff500002` | Intercepted and routed to the combined envelope/copy helper (`0x37e00`) | Has a body-reader case through `0xcf58` |

The outer cases run before generic query/set/method dispatch. Therefore the
inner header-reader case is not a recipe for a harmless header query through
this IHV bridge. Calling the first selector there can start packet logging.
These are internal selector observations, not top-level IOCTL numbers or an
approved request encoding. No selector was added to a live allowlist.

## What the log preserves

Two inspected producers have explicit payload copies:

- `process_offload_pktlog` at `0x220e90` extracts a payload length from its input,
  obtains ring storage through `0x220ac0`, then copies bytes from input `+0x10`
  at `0x220f80`.
- `process_pktlog_lite` at `0x220f98` obtains a packet length and reserves storage,
  then copies the selected packet data at `0x2210d8`.
- Callback dispatch `0x217300` reaches the offload producer for its local event
  value `0x101`. The lite callback at `0x217270` reaches the other producer for
  values `0x108` and `0x109`. These are callback selectors, not WMI event IDs.

The first producer copies opaque payload bytes, not merely formatted text.
However, no mapping from those bytes to the complete WMI management event
`0x7001`, its original header, or its reordering/timing block was established.
Nor was a packet-log payload bound to a valid RX descriptor timestamp/frame pair.
Other producer cases and their formats remain outside this selected trace.

The additional RX-labelled cases do not establish descriptor retention either:

- `process_rx_info`, `0x221428`, checks a supplied buffer length against a
  16-byte logging header and its declared payload length, then copies the bytes
  after that header at `0x221500`. It does not itself identify the known split
  PPDU timestamp fields.
- The alternative RX callback at `0x221320` writes local log type `0x16` and
  copies a packet's current data view at `0x221418`. That view is not automatically
  the original descriptor prefix, an entire on-air frame or a WMI header.
- The callback dispatch contains different consumers for event `0x102`. Its
  presence alone cannot determine which payload format a runtime record uses.

These paths preserve bytes, but the required same-event frame/timestamp schema
and its active producer registration still need to be bound explicitly.

The context lookup at `0x2171e0` obtains a global module context and follows an
indirect lookup with selector zero. The lookup does not simply return the
interface argument passed into the reader. Runtime device/link/clock association
must therefore be established separately; an application-selected interface GUID
is insufficient proof of the returned log's physical source.

The [Ghidra producer follow-up](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/memory-ring/packetlog-producer-trace.md) now connects the
offload writer to HTT packet-log message type `0x08`, internal event `0x101`,
subscription and callback dispatch. It does not connect that opaque payload to
the complete WMI management event. Firmware record semantics and snapshot safety
remain unqualified.

## Copy, publication and teardown

### The ring position is not a demonstrated completion marker

The reservation helper at `0x220b18` writes a record header, updates the ring
position at backing-buffer `+0x0c` (`0x220d84`) and returns a destination pointer.
Its optional lock is released before return. The caller copies the payload later.

The table offsets used for the optional lock calls, `0x9e0` and `0x9e8`, agree
with WDF spin-lock acquire/release indices 316 and 317 in Microsoft's
[framework header](https://github.com/microsoft/Windows-Driver-Frameworks/blob/main/src/publicinc/wdf/kmdf/1.27/wdffuncenum.h).
This is an ABI correspondence, not a live inspection of the framework table.

The inspected header reader, body reader and shared copier do not acquire that
lock or check a separate completed-record marker. The offload payload copy is
outside the reservation helper's locking window. The lite producer reacquires
the optional lock for its copy, but reservation still occurred earlier and the
reader does not participate in that lock in the inspected bodies.

Without additional caller exclusion, the sequence can be:

1. Writer fills a record header and advances the ring position.
2. Reader copies the apparent record while its payload is still old or unfinished.
3. Writer copies the new payload.

This identifies a missing publication guarantee. It is not an observed live
torn copy or a claim that no upstream exclusion exists. A later application-owned
copy would preserve the bytes it received, including any inconsistency already
present in the source. Repeated equal copies would not create a completion fence.

### Stop is not a freeze-and-retain contract

The successful stop/reset path at `0x1ec0e0` disables the selected logging path,
clears state and can call `0x1ebee0` at `0x1ec1b0`. That release helper clears the
stored backing pointer and frees its previous allocation through `0x96e0`.

Stopping the logger and then reading the old buffer cannot be assumed to provide
a stable snapshot. A usable freeze/read/resume operation would need to preserve
the allocation, drain or exclude all writers, define ownership and establish
completion. No such operation was identified or executed here.

## Other return candidates

The remaining two immediate callers of the device-service serializer at
`0x1618c0` were classified:

- `sar2ServiceHandler`, `0x12a4c0`: power-backoff/antenna configuration, state and
  small information/status responses.
- `antServiceHandler`, `0x12a9b0`: selected antenna parameter queries/sets and
  one-byte results.

Together with the earlier fixed test response and interface-information service,
all four direct callers of this serializer have selected-path classifications.
This does not classify every dependency or all seventy callers of the common
completion helper. The packet-log IHV route uses serializer `0x1619b0` instead.

The unsolicited indication search found the `IHV_EVENT` name in a selector-to-name
routine, but no complete-event producer was connected to it. A named indication
or generated serializer entry alone is not an implemented event-return path.

## Next dependency and disposition

**Keep this path outside live acquisition.** The exact missing requirements are:

1. Bind a real packet-log producer/type to the full timing/frame record, or
   establish that this log cannot carry the needed WMI event and close that lead.
2. Prove source identity and snapshot lifetime across writer activity, wrap,
   teardown and any global-context selection.
3. Qualify the complete external request/response encoding, all lengths, errors
   and permissions. Preserve the outer/inner selector distinction.
4. Only then run one bounded read with explicit record completeness and loss
   checks. No logging start/stop, mode change or quarantine rearm is implied.

The alternative remains an exporter integrated at the original management-event
callback, before reduction, with a bounded owned copy and explicit completion.
The [management producer report](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/qualcomm-management-timing-producer.md)
defines that boundary. A companion application cannot reconstruct omitted bytes
or add a producer-side publication guarantee by wrapping the existing copier.

Hardware/QPC correlation remains a separate requirement after safe acquisition.
The [complete-record gate](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/raw-timestamp-export-gate.md) remains
closed; no timestamp or accuracy capability is promoted.

## Reproduce the static checks

Use Python 3.11+, existing repository dependencies and an owned exact-build SYS
file. Normal file-read permission is sufficient. No elevation, device handle,
new dependency or network access is required by the inspector.

```powershell
$env:WIFI_TIME_DRIVER_FIXTURE = 'C:\path\to\owned\qcwlanhmt8380.sys'
python research/memory_ring/inspect_packetlog_return.py --driver $env:WIFI_TIME_DRIVER_FIXTURE --output artifacts/packetlog-return-new.json
python -B -m unittest discover -s tests -p test_packetlog_return.py -v
```

- Input limit: 16 MiB. Unknown driver hashes are rejected before inspection.
- Output: thirty-two range hashes, selected branch locations, operations-table
  entries, producer subscription-table pointers, selector literals and explicit
  unqualified capability flags. The original pass covered twenty-three ranges;
  the producer follow-up adds nine.
- Output must be new and its parent directory must exist. Exit 0 means inspection
  completed; 1 means rejected input/I/O; 2 means CLI misuse.
- Rollback: only a local receipt is created; no device or system state changes.
- Fresh disassembly matched **23 ranges and 2,732 instruction/literal lines**,
  including the two additional RX-labelled producer ranges.
- Five focused tests passed with the owned-image fixture enabled. They cover
  build rejection, output preservation, missing input, selected route/table
  extraction, the HTT producer binding and continued rejection of
  live-safety/timestamp qualification.
- Full local syntax and unittest validation passed: **210 tests, no skips**,
  with the owned driver/Windows image fixtures and ARM64 native harness enabled.
- Branch scans do not prove complete control flow or indirect-call coverage.
  Behavioral interpretations above use manual inspection of the selected paths.

Private receipts remain under ignored `artifacts/CompleteEventReturnInvestigation/`.
No proprietary binary, full disassembly, real packet or endpoint identity is
published with these findings.

## Glossary

- **IHV:** independent hardware vendor; here, the vendor-specific control path.
- **Packet log:** binary diagnostic records from selected packet-processing paths.
- **Reservation:** assigning space for a record before its bytes are all written.
- **Publication:** making a complete record available to consumers.
- **Snapshot:** a consistent copy from an identified point in the buffer's lifetime.
- **Quiescence:** an established condition in which relevant writers cannot run.
- **RVA:** offset within this driver image, not a userspace function address.

See the [shared glossary](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/glossary.md) for additional terms.
