# WLANLIB requests, completion and the ART2 event cache

WLANLIB reaches the same private-command machinery used by the existing QcomWifi
TSF probe. We also connected an ART2 firmware test-event producer to an IOCTL
payload return, and traced a separate one-byte state notification. These are real
return mechanisms. Neither yet supplies an attributable timing record: the ART2
cache drops transport metadata, consumes state on retrieval and lacks qualified
copy/association guarantees.

## Contents

- [Scope and identities](#scope-and-identities)
- [One device with two access names](#one-device-with-two-access-names)
- [Request families](#request-families)
- [Request ownership and completion](#request-ownership-and-completion)
- [What 5G in use means here](#what-5g-in-use-means-here)
- [Where to look for timing returns](#where-to-look-for-timing-returns)
- [The ART2 producer-to-return chain](#the-art2-producer-to-return-chain)
- [Consequences for a usable clock](#consequences-for-a-usable-clock)
- [Repeatable inspection](#repeatable-inspection)
- [Remaining qualification and glossary](#remaining-qualification-and-glossary)

## Scope and identities

This follows the [WLANLIB interface attribution](quts-callback-framing-and-wlanlib.md).
The inspected driver remains ARM64 `qcwlanhmt8380.sys`, version `1.0.4374.1300`,
SHA-256:

```text
ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115
```

The work was file-only Ghidra analysis and offline inventory, plus a final
read-only adapter-state check. No WLANLIB handle was opened, private request sent,
factory mode enabled, register accessed or clock changed. The active interface
remained **Up** on the same driver version. Runtime mode flags were not inspected.

All addresses below are RVAs in this exact image. Add `0x140000000` to navigate
in Ghidra. Decompiled C is approximate; important gates, copy operations and
publication stores were also checked in ARM64 instructions. Raw vendor bytes and
private output stay in ignored `artifacts/wlanlib-dispatch-20261004/`.

## One device with two access names

The selected successful path through `WlanPciDrvEvtDeviceAdd`, **`0x436000`**:

- Assigns the device name `\Device\QcomWifi`.
- Creates `\DosDevices\QcomWifi` for its WDF device handle.
- Registers class `{9b4a1918-78c7-4148-8eb5-2e580f5ba530}` with reference string
  `WLANLIB` using that same handle.
- Configures the device-control queues whose handlers are `0x0293c0` and
  `0x0298c0`.

The existing [bounded private probe](../../research/tsf/qualcomm_probe.py) opens
`\\.\QcomWifi` and sends `0x00220182`. This investigation traced that selector
through `MPDispatch_iwpriv` at `0x11e840`, then `0x11fad0`, into the command table
at `0x33bde0` already checked by
[qualcomm_protocol.py](../../research/tsf/qualcomm_protocol.py).

**Consequence:** the attributable WLANLIB interface improves device identity, but
changing the access name does not establish a new TSF return path. The earlier
observation—TSF reports arrive asynchronously rather than in the immediate reply—
still applies to the qualified command path. Actual open behavior, permissions
and multi-instance alias behavior were not retested here.

## Request families

An IOCTL is a device-control selector. Its transfer method describes how Windows
makes buffers available; it does not say whether the operation is read-only or
whether its payload is a clock value.

| Family and handler | Selected operation | Observed result/effect |
|---|---|---|
| Qmux, `0x11bfb8` | `0x81802c00` | Copies nine input bytes into context and schedules a NAS-information work item. A control operation. |
| Qmux, `0x11bfb8` | `0x81802c04` | Input byte zero selects a current state query. Nonzero queues the request for a later state notification. |
| Qmux, `0x11bfb8` | `0x81802c08` | Copies a coexistence configuration byte and schedules work. A configuration operation. |
| ART2, `0x11d4c0` → `0x437340` | `0xc3502406` | Test-command envelope: command send, cached event fetch, status, memory and board-data operations. |
| iwpriv, `0x11e840` → `0x11fad0` | `0x00220182` | Existing named private-command dispatch, including the previously inspected TSF command table. |
| iwpriv, `0x11e840` | Other inspected selectors | Station/link statistics, FIPS test operations/events, QDSS/debug commands and side-effecting operations. No new timing schema qualified. |

The Qmux selectors are buffered I/O. The ART2 and `0x00220182` selectors use
`METHOD_OUT_DIRECT`; that name does not mean they are pure reads. The FIPS-related
handlers `0x1299f0`, `0x129318`, `0x1295e0` and `0x128e50` were followed sufficiently
to identify their family, not promoted as timing interfaces.

The ART2 envelope starts with two little-endian 32-bit values: command and content
length. Its outer handler requires at least eight input bytes and checks content
length against the remaining input. Most subcommands additionally require the
adapter's state field at `+0x648` to equal one. Subcommand `0x13` bypasses that
particular gate and returns a four-byte overall error value from adapter `+0x8948`.
It is not a clock getter. The actual runtime state was not read.

The name `MPDispatch_ftm` here is tied to ART2 test operations and UTF test events.
It is not evidence that this envelope exports IEEE 802.11 Fine Timing Measurement
departure/arrival timestamps. A specific payload would still need its own schema.

## Request ownership and completion

The [driver-event integration follow-up](../evidence/driver-event-return-integration.md)
adds exact queue creation, forced error completion, conditional suspend/deinitialization
callers and context release. It distinguishes the notification queue from the
different queue purged by its callers, then defines the remaining producer/export contract.

The selected framework calls were matched to Microsoft's
[WDF function-index definitions](https://github.com/microsoft/Windows-Driver-Frameworks/blob/main/src/publicinc/wdf/kmdf/1.27/wdffuncenum.h).
The ARM64 table uses eight-byte entries:

| Table offset | Framework operation |
|---|---|
| `+0x868` / `+0x870` | Retrieve input / output buffer |
| `+0x8c8` | Forward request to another I/O queue |
| `+0x4f0` | Retrieve the next request from a queue |
| `+0x848` | Complete request with status and information/byte count |

`WifiDeviceIoControl`, **`0x0293c0`**, routes selected families to the secondary
queue. Its normal completion path uses the handler's returned byte count. A
**`STATUS_PENDING` (`0x103`)** result skips immediate completion. The secondary
handler, **`0x0298c0`**, follows the same pending-versus-complete distinction.

The concrete Qmux notification path is:

```text
Application's state-notification request
    | selector 0x81802c04, nonzero input byte
    v
MPDispatch_qmux -> forward to manual pending queue -> STATUS_PENDING
    | WDF owns the queued request
    v
WlanQmuxIndicateConnStatus, 0x11c6e0
    | schedules completion work
    v
Complete5GInUseIrpWorkItemRoutine, 0x11bd90
    | retrieve request under the queue lock
    | retrieve at least one output byte
    | compute the current boolean state
    v
CompleteWithInformation(status, 1 byte on success)
```

The driver's name for the value is **5G in use**. The [channel-field follow-up](#what-5g-in-use-means-here)
supports interpreting this as the **5 GHz Wi-Fi band**, rather than cellular 5G.
Its helper iterates Wi-Fi contexts and reduces their state to a boolean. No radio
timestamp, packet identity or sampling bracket is constructed in this path.

While a request is queued, the framework owns it and can cancel it; after successful
retrieval, the driver owns it again. This follows Microsoft's
[forwarding](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdfrequest/nf-wdfrequest-wdfrequestforwardtoioqueue)
and [retrieval](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdfio/nf-wdfio-wdfioqueueretrievenextrequest)
contracts. We did not execute the cancellation/retrieval race, prove a deadline,
or establish firmware drain from framework request completion.

Return lengths also need interpretation:

- The asynchronous Qmux completion above reports one byte on success.
- The generic Qmux and iwpriv wrappers can report the supplied output capacity;
  it is not automatically the number of meaningful fields written.
- ART2 uses a subcommand-produced count. Some malformed-input branches can return
  success with zero bytes, so successful I/O alone is insufficient validation.
- WDF output-buffer ownership through completion does not establish that a
  separately maintained firmware cache was copied consistently.

## What 5G in use means here

The follow-up inspected these exact-build functions and their ARM64 instructions:

| Location | Selected operation |
|---|---|
| Predicate `0x11ca20` | Calls `0x071550`, then loads the object at context `+0x1a38` and tests bit 8 (`0x100`) of its 64-bit field at `+8` |
| Helper `0x071550` | Tests bit 4 of the context word at `+0x1e4`; this is an additional eligibility gate, not a timestamp |
| `Ap11HandleAPOpchanECSA`, `0x00eed8` | Uses that context's `+0x1a38` object to report the current operating channel |
| `ieee80211_chan2mode`, `0x05c660` | Treats the channel object's first 16 bits as frequency and its `+8` field as channel flags; diagnostic text names those fields |
| `0x05fa00` | Reads the channel object's first 16-bit value, with a special sentinel branch |

This is strong static evidence for a Wi-Fi channel/band predicate. The
[public 802.11 channel flag definitions](https://www.wireshark.org/docs/wsar_html/packet-ieee80211-radiotap-defs_8h_source.html)
also assign `0x100` to `IEEE80211_CHAN_5GHZ`. That source corroborates the
interpretation; it is not a schema certificate for every Windows channel flag.
Runtime flag contents, behavior across 5/6 GHz transitions, and MLO combinations
were not tested. Earlier bare “5G” wording should not be read as a demonstrated
cellular-state result.

**Changing the input byte cannot change the payload contract.** For
`0x81802c04`, zero selects an immediate query and any nonzero byte selects the
pending-notification path. An “802.11” byte would still select one of those
branches. Returning timing data requires an operation whose producer, schema,
copy lifetime and completion semantics explicitly provide that data. We can reuse
the queue/completion design in an exporter we control; this is not permission or
a method to alter the installed driver's ABI.

Private follow-up evidence is under
`artifacts/wlanlib-alternatives-20261004/`. The first broad channel-helper export
hit the 96-function caller bound; it supplied no completed receipt. The bounded
repeat selected interior RVAs `05c674` and `05fa04` to export just the containing
functions with the unchanged public Ghidra script. Do not treat the failed broad
run as a completed trace or increase unrelated bounds simply to suppress it.

## Where to look for timing returns

Prioritize a producer with a defined event before choosing its return envelope:

1. **Management receive before metadata reduction.** The
   [management-event handler and lifetime trace](qualcomm-management-timing-producer.md)
   at `0x1a8160` has the frame and candidate timing fields in the same event.
   The next exporter would copy the header, frame and relevant timing block while
   callback access is valid. The current reduced handoff does not preserve them.
2. **FTM before aggregation.** Follow the
   [FTM notification routing](../ftm/ftm-notification-routing.md) and response
   producer. Establish raw event values, units, validity and exchange identity;
   aggregate round-trip time cannot supply the missing absolute event contract.
3. **An existing allocated-result return.** The
   [IHV/device-service bridge](qualcomm-private-output-routes.md) supplies real
   serialization and owned-copy patterns. Classify the actual producers reaching
   completion `0x13a890`, rather than treating its 70 direct-call candidates as
   70 usable timing APIs. A confirmed timing producer must be connected to one.
4. **Existing TSF observations as a separate capability.** Preserve their
   [response-association and quarantine rules](../tsf/tsf-association-and-quarantine-disposition.md).
   The second access name does not turn asynchronous reports into a synchronous
   fresh getter. A TSF reading alone is not packet timestamp qualification.

The packet log and ART2 cache remain investigation leads. Their publication and
identity gaps preclude treating the current getters as safe polling interfaces.
The [live packet-capture baseline](../acquisition/packet-capture-and-elevation.md)
helps observe traffic; it does not fill these missing producer contracts.

## The ART2 producer-to-return chain

This is positive static evidence for a firmware-byte return path:

```text
Firmware UTF test event
    | registered by ol_ath_utf_attach, 0x1a4ad8
    v
ol_ath_utf_event, 0x1a4e10
    | interpret 16-byte segment header
    | append bytes after that header into context-owned cache
    v
Cached payload pointer +0x38240, published 16-bit length +0x38248
    | ART2 subcommand 2 via 0xc3502406
    v
Getter 0x1a4f80 -> output uint32 length + payload bytes
    | clear cached published length
    v
WDF request completes with returned length + 4
```

The related send path, ART2 subcommand 1, calls **`0x1a4bb8`**. It clears the
published event length, divides a command into segments of at most `0xfc` bytes
and submits WMI UTF command messages. Both the selected command ID and event ID
are numerically `0x1d002`, but they belong to different directional namespaces;
equal numbers do not bind a response to a request.

The receive callback and getter reveal why this is not yet a trustworthy event API:

1. The producer reads total length and segment index/count from a 16-byte header,
   then copies only bytes after it. The fetch result does not preserve that header.
2. A sequence mismatch logs a message and continues. A final total-length mismatch
   also logs and then reaches the length-publication store. Nonzero published
   length therefore does not prove a complete, correctly ordered message.
3. The selected producer does not demonstrate validation of the send-side message
   reference against an outstanding request. Segment sequence is not request identity.
4. The fetch reads cached length more than once. Its caller checks output capacity
   before entering the getter, which separately writes the length and copies bytes.
   A shared lock covering the producer and this whole read sequence was not established.
5. Fetching clears published length; sending a new command clears it too. These
   operations change cache state and can affect other consumers or pending data.
6. The inspected attach allocates `0x800` bytes for the UTF cache. Outer event-length
   validation, accumulation capacity and lifetime across teardown were not exhaustively
   proven. No malformed firmware data was injected to test them.

The mismatch behavior was checked at instructions `0x1a4ebc`–`0x1a4ee4` and
`0x1a4f2c`–`0x1a4f58`. The getter's repeated length loads and clear are visible at
`0x1a4fa4`–`0x1a4fe8`. These support a qualification limitation, not a claim that
a particular live corruption or memory-safety failure occurred.

The mode gate is another independent requirement. Presence of this code in the
installed driver does not establish that a production connection can safely use
its test-event path. No ART2 operation has been added to the live allowlist.

## Consequences for a usable clock

| Needed property | Result from this investigation |
|---|---|
| Attributable application interface | WLANLIB and its relationship to the QcomWifi device path are understood statically. |
| Concrete request completion | Located for synchronous private commands and a queued one-byte notification. |
| Firmware producer connected to a byte return | Located for UTF test events, with cache consumption and validity gaps. |
| Raw TSF / SoC / ranging event meaning | No new clock-domain, unit, width or reference-instant contract established. |
| Complete event and request identity | Not supplied by the selected ART2 length-plus-payload wrapper. |
| Concurrent-copy consistency and epoch | Unqualified; neither request completion nor cache clearing is an epoch boundary. |
| Hardware-to-QPC relationship | Still a separate measurement requirement. |

The QUTS framing map remains useful as a reference for retained bytes and protocol
record boundaries. These WLANLIB requests are not thereby proven to use QUTS's
DIAG stream or its CRC/queue guarantees. The live private campaign remains quarantined.

## Repeatable inspection

The new [offline inventory tool](../../research/adapters/inspect_wlanlib_dispatch.py)
reads a locally owned SYS file, verifies the existing exact-build checks, and writes
selected scalar constants plus short code-window hashes. It does not load the driver,
open a device or execute the recorded selectors. IOCTLs, WMI IDs and NTSTATUS values
are kept in separate fields.

```powershell
python research/adapters/inspect_wlanlib_dispatch.py `
  --driver '<owned-qcwlanhmt8380.sys>' `
  --output '<new-private-receipt.json>'
python -m unittest discover -s tests -p test_wlanlib_dispatch.py -v
```

- Preconditions: Python with the repository's existing dependencies, the pinned
  owned file and an existing private output parent directory. No elevation.
- Input limit: 16 MiB. Existing outputs are refused rather than overwritten.
- Exit codes: `0` receipt written, `1` rejected input/I/O, `2` CLI usage error.
- Receipt limits: scalar identity, 64-byte code-window hashes and selected pending-queue
  instruction checks; the manual control-flow trace remains separate. Qualification
  flags remain false.
- Rollback: only the chosen output file needs removal. There are no device or
  configuration changes to reverse.

For Ghidra, reuse `TraceQualcommPacketlog.java` on the hash-pinned project with
`-noanalysis -readOnly`. Use new output directories and inspect every receipt:

| Question | Seeds |
|---|---|
| Three top-level families | `11bfb8 11d4c0 11e840` |
| ART2 and Qmux workers | `437340 11ca20 11c4a0 11c380` |
| Existing private command and notification return | `11fad0 126e50 11bd90` |
| UTF send/fetch | `1a4bb8 1a4f80` |
| Firmware-event producer and initialization | `2c3f40 1a4e10 1a4ad8` |
| Qmux lifecycle | `298348 298400 11c6e0` |

No whole-program reanalysis, instruction-cap increase or new dependency was needed.

Validation on this tree:

- Python compilation and the configured full suite passed: **267 tests, zero skips**.
- Five new tests cover selector types/methods, wrong or modified driver images,
  preserved existing output, missing input and separation of qualification states.
- The offline CLI produced a new receipt from the exact driver with 11 selected
  IOCTLs, separately typed WMI/status constants and eight code-window hashes.
- Eight Ghidra passes recorded zero decompilation failures and complete instruction
  exports for their selected functions. These are bounded traces, not exhaustive
  proof of indirect control flow or live concurrency.
- Knowledge-index, documentation/diagram consistency and Git whitespace checks
  passed at the static-analysis checkpoint. Publication and hosted CI for the
  containing revision are tracked separately in [PR #3](https://github.com/Protonmatter/wifi-hardware-time/pull/3).

## Remaining qualification and glossary

The next useful path must preserve **one timing event**, rather than merely return
some firmware bytes. For an ART2-derived experiment, prerequisites include a
reviewed runtime-mode requirement, matched firmware payload schema, strict segment
and message association, consistent cache copying, loss reporting and teardown
rules. A different supported normal-operation return path or an instrumented
driver may be needed to preserve those properties.

Do not use the one-byte Qmux notification or overall-error getter as a timestamp,
and do not promote the existing TSF command solely because it is reachable through
WLANLIB. Both would leave the original clock semantics unresolved.

- **WDF:** Windows Driver Frameworks, which manages request and queue objects.
- **Qmux:** the driver's named control/coexistence interface family here.
- **ART2 / UTF:** the inspected test-command family / its firmware test-event path.
- **Published length:** a field advertising available cached bytes, not proof of
  their validity, identity or simultaneous capture.
- **Completion:** the end of an I/O request; it is not necessarily the firmware's
  measurement instant.

Hosted CI on `1522bca` predates this follow-up and cannot validate it. Check the
containing revision's hosted result separately. Live private-request behavior and
timing accuracy remain unqualified.
