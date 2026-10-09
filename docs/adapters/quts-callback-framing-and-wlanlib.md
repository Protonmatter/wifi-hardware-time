# QUTS callback framing and the FastConnect WLANLIB interface

The transport callback is now connected statically to the DIAG receive queue and
frame decoder. We located partial-frame retention, multiple-record processing,
CRC rejection and owned copies of decoded payloads. Separately, Windows exposes
an enabled WLANLIB interface on the exact FastConnect device, registered by the
pinned driver. Its connection to a Wi-Fi timing producer remains unqualified.

<!-- research-history:2026-10-09 -->
**Research context (2026-10-09):** Scoped technical reference. Build-specific findings and operational prerequisites retain their stated scope. [Current account](../research-history/README.md) · [Timeline](../research-history/timeline.md) · [Previous version](../../archive/2026-10-09-pre-refresh-e9d71b8/pages/docs__adapters__quts-callback-framing-and-wlanlib.md).
<!-- /research-history -->

## Contents

- [Scope and publication](#scope-and-publication)
- [The callback connection](#the-callback-connection)
- [Framing and rejection behavior](#framing-and-rejection-behavior)
- [Ownership and teardown](#ownership-and-teardown)
- [The attributable WLANLIB interface](#the-attributable-wlanlib-interface)
- [Reproduction and validation](#reproduction-and-validation)
- [Remaining work and glossary](#remaining-work-and-glossary)

## Scope and publication

This follows [endpoint construction and receive ownership](quts-endpoint-writer-and-receive.md).
The preceding work was published as commit
[`1522bcafad5cfb87a739da76afd3129b62b8c0ff`](https://github.com/Protonmatter/wifi-hardware-time/commit/1522bcafad5cfb87a739da76afd3129b62b8c0ff)
in [PR #3](https://github.com/Protonmatter/wifi-hardware-time/pull/3).
Its [PR workflow](https://github.com/Protonmatter/wifi-hardware-time/actions/runs/37245396482)
and [push workflow](https://github.com/Protonmatter/wifi-hardware-time/actions/runs/37245394037)
both passed. Those hosted results precede this follow-up.

The new investigation combines file-only Ghidra analysis with Windows device
enumeration. It did not open WLANLIB, issue a private IOCTL, connect a DIAG client,
change logging masks, or execute a firmware command. Wi-Fi remained Up on driver
`1.0.4374.1300`. Raw interface paths and machine identifiers remain private.

Exact inputs:

| Binary | SHA-256 |
|---|---|
| ARM64 `QUTS.exe`, version `3,96,2` | `8e6de10a298f8378e9d289ad11a33018654a29d155e56588f9427d53ed639297` |
| ARM64 `qcwlanhmt8380.sys`, version `1.0.4374.1300` | `ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115` |

All code locations below are executable-relative offsets, or RVAs. Add
`0x140000000` to navigate in these imported Ghidra programs. Identical offsets in
different binaries or object types do not identify the same operation.

## The callback connection

Initialization at **`0x20ee28`** retrieves the protocol's `CommonIo` object and
registers a pair containing the DIAG worker context and
**`DiagRxWorker::receiveData`, `0x231938`**. The registration is visible in ARM64
instructions at `0x20f178`–`0x20f1a0`, through virtual slot `+0x78`.

For the selected `Usb` transport, that slot resolves to `0x2aae30`, which stores
the callback pair and propagates it to the communication worker through
`0x2ac3d8`. This closes the earlier missing **static callback association**.

The receiving method:

- Retains the incoming `Device::Buffer` reference.
- Uses the DIAG worker's lock at object `+0xe0`.
- Enqueues through `0x227280` into the list rooted at `+0xd0`.
- Increments queue bookkeeping and signals the worker.
- Has explicit early-return/drop paths, including critical-memory and
  queue-pressure handling. A callback invocation is not guaranteed admission.

The DIAG worker at **`0x219a58`** takes the same lock, retains the front buffer,
removes the queue node through `0x223c20`, and assigns the buffer to its persistent
memory-stream object. It resets that stream's cursor before calling
**`readPackets`, `0x22d038`**.

```text
Communication RxWorker
    | owns a copied Device::Buffer chunk
    v
Registered receiveData callback, 0x231938
    | memory/queue-pressure checks
    +------------------------------> drop path / warning
    | admitted: retain reference under lock
    v
DIAG receive queue
    | pop while retaining buffer; update cursor-backed stream
    v
readPackets -> selected frame-stream decoder
    | retain incomplete state OR return a complete frame
    | reject empty/bad-CRC frame before normal routing
    v
Copy decoded payload -> response routing / incoming-packet queue
    |
    ? exact service-return and Wi-Fi producer association remains open
```

Arrows show inspected software calls and ownership transfers. The question mark
is an evidence gap; this diagram is not a captured firmware event.

## Framing and rejection behavior

Initialization selects the HDLC frame-stream implementation through `0x254548`.
There is also a non-HDLC switch at `0x254d38`. Both retain a stream object rather
than treating every transport callback as one record.

| Requested case | Inspected implementation | Qualification limit |
|---|---|---|
| Record split across reads | HDLC retains partial payload at frame-stream `+0x18`; the escape filter retains its escape state. Non-HDLC retains incomplete header/payload bytes at its own `+0x18`. | Static state handling found; no controlled fragmented firmware record replayed. |
| Several records in one read | Memory stream `0x22cf48` advances its cursor by actual bytes consumed. `readPackets` repeatedly asks for one frame and loops after routing it. | Multiple-record path is present; no live count/identity fixture acquired. |
| Invalid checksum | HDLC frame validator `0x135090` checks payload plus saved CRC bytes against a residue. Failed validation returns to the read loop before ordinary response routing. | Exact checker located; no claim that every framing mode uses that checksum. |
| Incomplete frame | Selected constructors set the mode byte to zero; exhaustion retains partial state and reports no completed frame. | Timeout, disconnect and reconnect disposition must be qualified separately. |
| Oversized HDLC accumulation | Reader `0x1357e0` detects size above `0x4400`, clears the accumulated frame and consumes toward a delimiter. | This is a parser bound, not a hardware packet-size specification. |
| Invalid non-HDLC structure | `0x136a48` checks framing structure and records invalid status; `0x1e9848` handles that status and includes an HDLC fallback. | Recovery/resynchronization and mode transitions are not fully qualified. |

### HDLC details

The frame reader at **`0x1357e0`** wraps an escape filter at **`0x146ce8`**.
The inspected filter recognizes `0x7d` escaping and `0x7e` boundaries. Its retained
state permits an escape sequence to cross a source-buffer boundary. This does not
establish behavior for every malformed escape sequence; those need targeted tests.

At a completed frame, `0x134e80` separates the final two CRC bytes from the payload.
Virtual frame slot `+0x68` resolves to **`0x135090`**, which updates a checksum over
the payload and saved CRC and compares the result with **`0x0f47`**. That literal
is the observed implementation residue, not a claim that the complete checksum
algorithm has been independently reconstructed.

The frame's `+0x30` virtual method, **`0x134ac0`**, checks whether its payload is
empty. It is **not** the CRC check. Keeping these predicates distinct matters
when identifying why a record was discarded.

### Non-HDLC details

The reader at **`0x136a48`** inspects a four-byte header beginning with `0x7e, 0x01`,
uses the little-endian 16-bit length at header `+2`, and checks a trailing marker.
It has retained-state paths for short headers, short payloads and a marker deferred
to a later read. Its frame-stream object also maintains validity/state bytes.

These are decoded software framing fields. They are not TSF units, a firmware
request token, a radio-link identity or a hardware sampling timestamp.

## Ownership and teardown

We can now follow ownership further than the transport callback:

1. `0x227280` retains a reference when inserting the received chunk into a queue
   node. The callback's own reference can then be released.
2. The consumer retains the buffer before `0x223c20` removes the node and releases
   that node's reference. The memory stream holds its own reference.
3. The frame decoder retains unfinished bytes between source chunks.
4. On the selected complete-frame route, `readPackets` calls **`0x1ef3c8`** to
   allocate a new `Device::Buffer` and copy the decoded payload through `0x137760`.
   This separates the routed payload from the reusable frame accumulator.
5. An incoming-packet route reaches **`0x440a48`** and queue insertion
   **`0x441830`**, which retains the payload reference in the queued item.

The previously located managed client allocates its own returned byte array.
This pass has not bound a specific native queued item, service response and
client array together. Server-side snapshot consistency and a live complete-event
return therefore remain separate requirements.

On stop, `0x219a58` unregisters the communication callback by passing a zeroed
pair through `CommonIo +0x78`. The setter and callback execution use the worker's
lock. Destruction at `0x1e10d0` releases queued buffer references, frame-stream
state and worker objects. This demonstrates cleanup code, not successful delivery
of every pending record.

The [unlimited wait and cancellation limits](quts-endpoint-writer-and-receive.md#cancellation-and-completion)
still apply. Neither queue release nor process/session restart proves that old
firmware work has drained. No epoch token connecting these queue objects to a
firmware reset boundary was established here.

The explicit memory/queue-pressure drop paths are also relevant downstream:
retaining a buffer safely does not establish loss-free acquisition. Any exporter
must expose loss/ambiguity and invalidate affected relationships instead of
silently treating the remaining records as a complete sequence.

## The attributable WLANLIB interface

A fresh, read-only `pnputil /enum-devices` query targeted the active FastConnect
PCI instance and requested its interfaces, relations, services and stack. It
returned **nine enabled interfaces**:

- Four in `GUID_DEVINTERFACE_NET` (`{cac88484-7515-4c03-82e6-71a87abac361}`).
- Four in `GUID_NDIS_LAN_CLASS` (`{ad498944-762f-11d0-8dcb-00c04fc3358c}`).
- One with class **`{9b4a1918-78c7-4148-8eb5-2e580f5ba530}`** and reference string
  **`WLANLIB`**.

The first two class names were verified in the installed Windows SDK
`ndisguid.h`. The device's effective stack was `qcwlan`, `ACPI`, `pci`.
Full endpoint paths, adapter instance IDs and per-interface reference GUIDs stay
in the private evidence.

The exact driver contains both the WLANLIB class GUID and reference string:

| Driver RVA | Meaning established in this pass |
|---|---|
| `0x2ef090` | The WLANLIB interface-class GUID data |
| `0x438c30` | UTF-16 `WLANLIB` reference string |
| `0x436000` | `WlanPciDrvEvtDeviceAdd`; constructs the reference string and calls the interface-registration path |
| `0x436ea4` | GUID argument at the registration callsite |
| `0x11c948` | `WlanSetWlanLibIfState`, an interface-state helper with a Qmux-context condition |
| `0x0293c0`, `0x0298c0` | `WifiDeviceIoControl` and its secondary request-dispatch path |

The registration matches the interface enumerated for the exact active device.
This is stronger than a friendly-name guess or a generic MHI string match.

The request handlers contain IOCTL dispatch and request-completion paths, including
forwarding to power-managed/manual queues. That does **not** establish a `ReadFile`
DIAG stream, a passive operation, a timing-event schema or a QUTS association.
The dispatch targets `0x11bfb8`, `0x11d4c0` and `0x11e840` are concrete next inspection
points. No selector was invoked and no interface state was changed.

The earlier missing `QCDeviceControlFile` result remains valid. The corrected
interpretation is: **this adapter has an attributable vendor interface, while the
selected QUTS discovery/DIAG connection remains unqualified.** These are different
claims.

The subsequent [dispatch/completion investigation](wlanlib-dispatch-and-completion.md)
connects WLANLIB to the existing QcomWifi device and follows Qmux, ART2 and iwpriv
requests. It locates a UTF firmware-event fetch while documenting why that cache
does not yet supply a trustworthy timing record.

## Reproduction and validation

Use the existing hash-gated Ghidra exporters in read-only mode on the analyzed
projects, with a new private output directory for every pass:

| Tool/program | Seed RVAs |
|---|---|
| `TraceQutsDiscovery.java`, `QUTS.exe` | `fbe830 fbefe0 fbf028` for named receive/mode methods |
| Same | `231938 254548 254d38` for registration and mode callers |
| Same | `1355d0 136888 227280 1e10d0` for stream construction, queue ownership and teardown |
| Same | `1357e0 136a48 1d6ee8 20ee28` for frame readers and initialization |
| Same | `146ce8 223c20 440a48` for escaping and queue handoffs |
| Same | `135090 22cf48` for CRC acceptance and stream-cursor behavior |
| `TraceQualcommPacketlog.java`, `qcwlanhmt8380.sys` | `2ef090 438c30`, then `293c0 298c0` for WLANLIB registration/dispatch |

The QUTS exporter now accepts **`scope:seeds-only`**, after the optional instruction
limit and before the seed list. This exports only the functions containing the
specified addresses, without traversing callers:

```text
-postScript TraceQutsDiscovery.java <new-private-output>
  max-instructions:32768 scope:seeds-only 1ef3c8 134cd0 134e10 441830
```

The original attempt to export those widely referenced helpers exceeded the
96-function bound. That failure was retained; the limit was not raised. The new
scope produced exactly the four selected functions. Default caller traversal
remains available, and unsupported scope values reject before output creation.
All existing hash, architecture, instruction and function bounds remain in force.

For the device snapshot, obtain the instance ID from a fresh exact-adapter lookup
and use it only in a private output:

```powershell
pnputil /enum-devices /instanceid '<exact-active-device-instance>' `
  /interfaces /relations /stack /services /drivers
```

This enumerates device information; it does not open WLANLIB or start firmware
acquisition. Ghidra output is similarly offline. Raw results and executed-script
snapshots are kept under ignored `artifacts/quts-callback-framing-20261004/`.

Validation must distinguish successful Ghidra script receipts from process exit
codes: the tool can report a script error despite a zero process exit. Check each
receipt for completion and truncation, and retain failed attempts separately.

Validation on this follow-up tree:

- **262 local tests passed, zero skips**, with the installed ARM64 compiler and
  pinned driver/Windows fixtures; Python compilation also passed.
- Twelve positive Ghidra receipts completed without decompilation failure or
  instruction-export truncation for their selected functions.
- The new seeds-only scope exported four selected functions. A default invocation
  still exported its seed plus caller with the 4,096-instruction default.
- Invalid `scope:all` rejected before creating output. The earlier function-bound
  failure is retained and is not counted among successful passes.
- Both binary hashes were reverified. The device snapshot contained nine enabled
  interfaces on the targeted device, including the matched WLANLIB interface.
- Index, diagram-source and whitespace checks passed. Hosted CI for this later
  follow-up is separate from the successful `1522bca` publication; use the
  containing revision's checks in [PR #3](https://github.com/Protonmatter/wifi-hardware-time/pull/3).

## Remaining work and glossary

- **Closed statically:** callback registration, admitted-queue retention, stream
  cursor, selected partial-frame states, CRC rejection, decoded-payload copying
  and queued payload retention.
- **Observed through Windows enumeration:** an enabled WLANLIB interface on the
  exact FastConnect device, with matching registration in its pinned driver.
- **Still open:** live fragmented/multiple/bad-frame fixtures, cancellation races,
  pressure-loss reporting, cross-epoch invalidation, native-item-to-client-response
  association, and a Wi-Fi firmware timing producer behind that interface.
- **Separate clock requirement:** no fresh hardware/QPC sample or calibrated
  synchronization result was obtained.

The [next dispatch pass](wlanlib-dispatch-and-completion.md) now records the selected
WLANLIB request/completion rules. A usable timing export still requires
an operation that returns the relevant event and its ownership, identity, validity
and clock meaning; an enabled interface alone does not supply those semantics.

**Glossary:** a callback is a registered function invoked on data arrival; a queue
retains items until a consumer handles them; a frame decoder recognizes complete
protocol units across arbitrary read boundaries; CRC is an error-detection
checksum; an epoch identifies a period of clock continuity. Reference ownership
and protocol validity answer different questions.
