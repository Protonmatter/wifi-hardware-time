# Management RX: frame bytes survive, candidate local timestamps do not follow

The selected Qualcomm management-frame handler copies received frame bytes into a packet and queues radio metadata separately. It does not read the header positions that a vendor reference labels as local RX TSF. This locates a concrete export boundary, but no application interface returning the frame and its local hardware timestamp together has been established.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** Later archive and installed-file inspection located QUTS client-owned byte returns and corrected vendor package/version assumptions; exact adapter-to-producer association remains open. See [current findings](../knowledge/current-findings.md).
<!-- /historical-context -->

## Contents

- [Scope](#scope)
- [Frame and metadata handoff](#frame-and-metadata-handoff)
- [Optional slots and downstream consumers](#optional-slots-and-downstream-consumers)
- [Candidate timestamp semantics](#candidate-timestamp-semantics)
- [Why the BSS cache is a different contract](#why-the-bss-cache-is-a-different-contract)
- [Next integration and validation](#next-integration-and-validation)

## Scope

Exact ARM64 driver `qcwlanhmt8380.sys` 1.0.4374.1300, SHA-256
`ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`.
This pass inspected the owned file and saved disassembly, then compared selected
ranges with fresh disassembly. No capture, scan, device command or logging change.

**Terms:** RX means receive. A management frame includes beacons and probe
responses. WMI is the firmware/host message interface. A TLV is a tag, length and
value. An RVA is relative to the image base and requires PE section mapping to
locate file bytes. A BSS is a wireless network context. See the [glossary](../glossary.md).

## Frame and metadata handoff

| Exact-build evidence | Observed operation | Implication |
|---|---|---|
| `0x1a5b30..0x1a5b44` | Register handler `0x1a8160` for event `0x7001` | Connects this handler to management-frame reception for the inspected initialization path |
| Schema entry `0x38fbec` | Twelve decoded slots; first is tag `0x2c`, expected size 72 bytes, followed by a variable byte-array slot | The event has header and frame data; expected size does not prove every runtime wire length |
| `0x1a81d0..0x1a8250` | Read first-slot header; build compact radio metadata from signal, channel/frequency, rate, PHY and status positions | No access to the candidate local timestamp positions in this construction |
| `0x1a8264..0x1a8270` | Compare header frame length with decoded byte-array count | Bounds the selected frame copy before allocation |
| `0x1a8280..0x1a831c` | Allocate packet storage, set length and copy bytes from decoded slot 1 | The frame body, including its peer-advertised timestamp when present, is preserved internally |
| `0x1a8444..0x1a8450` | Convert compact metadata through `0x1a6080` into a zero-initialized 64-byte block | Converts selected radio fields; does not receive the original WMI header pointer |
| `0x1a84d8..0x1a84e4` | Call enqueue helper `0x104230` with packet and converted metadata | A selected acceptance path reaches the management queue; other branches drop the packet |
| `0x1042e4..0x1042f8` | Store packet pointer and copy 64 metadata bytes into an 88-byte queue node | Establishes an internal owned metadata copy, not a userspace export |
| `0x103ec8..0x103f1c` | Dequeue and hand packet/metadata to port-specific or fallback processing | Original firmware-header timestamp fields are not arguments to this handoff |

Manual inspection of the full handler finds no read of header `+0x34`, `+0x38`
or `+0x3c`. The handler also does not retain the original header pointer in the
queued node. Its selected logging site emits addresses and radio parameters,
not those timestamp words. This is bounded evidence for this path, not proof
that every receive mode or alternate export lacks timestamps.

The conversion helper writes radio metadata and obtains a context pointer.
Its complete downstream use was not reconstructed, and no claim is made here
about precisely where the eventual Windows host timestamp is generated.

## Optional slots and downstream consumers

The next offline pass followed the decoded wrapper and the queue's consumers.
It found additional internal processing, but no recovered route around the
earlier loss of candidate timestamp fields.

**Decoded wrapper:** this is the host-side collection of pointers and counts
produced by the firmware message decoder, not the raw message itself.

- At `0x1a81d0`, the handler reads slot 0's header pointer.
- At `0x1a8268`, it reads slot 1's byte count at wrapper `+0x18`.
- At `0x1a82b0` and `0x1a8314`, it reads slot 1's frame pointer at `+0x10`.
- Manual inspection finds no access to slots 2 through 11 or forwarding of
  the wrapper to a consumer. Register X22 stops representing the wrapper when
  a write to W22 at `0x1a8364` replaces its value.

The schema table declares these slots. A declaration does not establish that
an optional slot was present in any live event or identify its firmware meaning.

| Slot | Tag | Element size in bytes | Variable flag |
|---|---|---|---|
| 0 | 44 | 72 | 0 |
| 1 | 17 | 1 | 1 |
| 2 | 18 | 20 | 1 |
| 3 | 978 | 20 | 0 |
| 4 | 18 | 16 | 1 |
| 5, 6 | 18 | 20 | 1 |
| 7 | 17 | 1 | 1 |
| 8 | 18 | 12 | 1 |
| 9, 10 | 18 | 8 | 1 |
| 11 | 17 | 1 | 1 |

**Downstream consumers:** the fallback at `0x1021b8` enumerates eligible port
contexts and calls `0x103468`. That helper can clone the packet for another port
or transfer the original packet to the final recipient. At `0x1035ec..0x1035f4`,
it forwards the existing metadata pointer to the same per-port routine,
`0x101ac8`. This does not reconstruct the discarded firmware fields.

The per-port routine has an indirect callback at context `+0x3600`. A selected
initialization path at `0xb8818..0xb8820` assigns function `0xb5dd0` to it.
The calls at `0x101c14` and `0x102084` supply port, packet, frame subtype and
the reduced metadata. The inspected callback prefix includes beacon/probe
subtype checks and passes the packet/frame and reduced metadata to `0x9cea8`
at `0xb5f98`. This is an internal processing route. Full callback behavior,
all possible registrations and any eventual application return remain unproven.

**Conditional raw-frame logging:** the handler can call `0x1a6028` with only
the frame pointer and length. That helper passes them to the byte-dump routine
`0x1a49b0`; the original firmware header is not an argument. Enabling this log
would therefore not, by itself, recover a frame/local-RX-timestamp pair. Its
runtime output, delivery and completeness were not tested, and logging was
not enabled.

The practical next requirement remains a copy **before** the metadata reduction,
or a separately demonstrated producer that retains the timing fields. Neither
the optional-slot declarations nor the callback address is a usable API.

## Candidate timestamp semantics

The [pinned vendor reference header](https://github.com/OnePlusOSS/android_kernel_modules_and_devicetree_oneplus_sm8650/blob/38d50357db2728300a61b6f757f2d3a09651c155/vendor/qcom/opensource/wlan/fw-api/fw/wmi_unified.h)
defines `wmi_mgmt_rx_hdr` fields consistent with the inspected 72-byte layout:

- `+0x34`: candidate `tsf_delta`, described as a signed local/remote TSF
  difference stored in an unsigned word. Zero can mean remote TSF unavailable;
  it must not automatically mean zero clock offset.
- `+0x38`: candidate `rx_tsf_l32`, described as copied from the hardware RX
  descriptor's timestamp.
- `+0x3c`: candidate `rx_tsf_u32`, described as read from a TSF register after
  reception.
- `+0x40`: candidate `pdev_id`, physical-MAC context.

These labels are other-platform reference evidence, not a qualified schema for
the firmware currently running. The Windows handler's channel-frequency access
at `+0x44` is consistent with this layout, but positional agreement is insufficient
to establish runtime values, units, validity or clock mapping.

The split-word description also requires producer-side rollover investigation.
For illustration, low word `0xfffffffe` captured in high-word generation 1 and
a later high-word read of 2 cannot simply be concatenated without accounting
for a possible wrap. This is a possible failure mechanism, not an observed
firmware defect; the firmware may already compensate. Simultaneous 64-bit
sampling must not be assumed from the presence of two words.

## Why the BSS cache is a different contract

Microsoft documents `WLAN_BSS_ENTRY.ullTimestamp` as the peer's timestamp from
a beacon/probe response. `ullHostTimestamp` is a host time in 100-nanosecond units
from the Windows epoch. Its information-element blob can combine elements from
different received frames. See [WLAN_BSS_ENTRY](https://learn.microsoft.com/en-us/windows/win32/api/wlanapi/ns-wlanapi-wlan_bss_entry).

The existing `cached_beacon.c` helper reads this cache without requesting a scan.
It cannot supply an original raw MPDU or establish that the host timestamp is
the local hardware RX TSF. Building a synthetic frame from that cache would not
create the missing hardware-timestamp/frame pair. It was not executed in this pass.

## Next integration and validation

The [producer and lifetime follow-up](qualcomm-management-timing-producer.md)
matches slot 3 to a public reordering/timing structure, traces cleanup of all
twelve slots and establishes that the selected event-history writer skips
management event `0x7001`. The additional fields remain reference-schema
candidates; no live event or hardware/QPC pair has been obtained.

The [BSS serialization follow-up](qualcomm-bss-serialization.md) now resolves the
selected station indication and container builder. Its optional 28-byte context
is MBSSID profile state in the subsequently inspected writers, not a recovered
local hardware timestamp.

The concrete candidate copy point is while the management-event handler owns
both its decoded header and frame, before it narrows metadata and the generic
event machinery releases its temporary input. A qualified exporter would need:

1. An owned, bounded copy of the same event's header, original lengths, frame and
   relevant optional metadata, with validated completion/lifetime rules.
2. Exact firmware semantics, validity and clock-source identity for the local
   timestamp, including split-word rollover behavior.
3. A preserved distinction between peer-advertised TSF, local RX time and host
   observation time, with a separately qualified conversion.
4. A real application return interface and positive/negative capture fixtures.

This may require an existing vendor facility or source-level driver integration.
The observed internal queue is not a pointer an application may read or a safe
polling API. No new capture route is qualified by this analysis, so none was run.

The reusable inspector reads an owned file, requires no elevation, limits input
to 16 MiB plus one rejection byte and creates one new JSON receipt:

```powershell
python research/adapters/inspect_management_rx.py `
  --driver 'C:\path\to\owned\qcwlanhmt8380.sys' `
  --output artifacts/management-rx-new.json
python -m unittest discover -s tests -p test_management_rx_path.py -v
```

Output parent must exist; existing output is not overwritten. Exit 0 means
offline inspection, 1 means input/I/O rejection, and 2 means CLI misuse. There
is no device rollback; only the requested receipt is created.

The first pass compared five ranges, 592 instruction/literal lines, with fresh
disassembly. The follow-up adds six ranges for the downstream paths and raw-frame
logger; separate receipts preserve the original evidence.
The small instruction decoders inventory selected word/pair loads only; byte
loads, pointer aliases and complete dataflow require the manual inspection above.
Tests cover unknown-build rejection, the owned schema/handoff fixture, all twelve
schema slots, selected wrapper loads and downstream direct-call associations.
The small decoders do not automatically establish full pointer dataflow or
resolve the indirect callback; those conclusions use the bounded manual trace.
Receipts stay under ignored `artifacts/ManagementRxInvestigation/` and
`artifacts/ManagementRxFollowup/`.

See the [autonomous frame decoder](../tsf/autonomous-management-tsf.md) and
[clock/event identity rules](../tsf/tsf-association-and-quarantine-disposition.md#clock-identity-is-separate-from-event-identity).
The original private campaign remains quarantined, and no clock accuracy or
hardware-to-QPC relationship is established here.
