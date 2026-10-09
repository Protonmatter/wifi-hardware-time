# Management RX timing: producer fields, ownership and host correlation

The declared receive event contains a stronger timing lead than the BSS cache: a block matching public Qualcomm reordering metadata, with a link identifier, packet counter and additional timing fields. This pass also traces its temporary lifetime and finds that the driver's event history skips management RX. These are static findings; a live, application-owned timestamp record and a hardware-to-QPC relationship are still missing.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** Later archive and installed-file inspection located QUTS client-owned byte returns and corrected vendor package/version assumptions; exact adapter-to-producer association remains open. See [current findings](../knowledge/current-findings.md).
<!-- /historical-context -->

## Contents

- [Outcome and scope](#outcome-and-scope)
- [Candidate producer fields](#candidate-producer-fields)
- [Where one event must be preserved](#where-one-event-must-be-preserved)
- [What the host-time path actually records](#what-the-host-time-path-actually-records)
- [Next acquisition requirements](#next-acquisition-requirements)
- [Reproduction and validation](#reproduction-and-validation)
- [Source provenance and glossary](#source-provenance-and-glossary)

## Outcome and scope

| Requested dependency | What this pass establishes | What remains open |
|---|---|---|
| Verify the timing producer | A public schema match for a second timing block, plus explicit reference-field meanings | Actual firmware population, timer identity, validity, units and split-word behavior |
| Preserve one event | The selected callback receives temporary decoded data; cleanup covers all twelve declared slots | An implemented, qualified copy/export mechanism and one real returned event |
| Establish host correlation | The inspected history branch excludes this event; its time helper uses system time | A fresh hardware/QPC sampling relationship |

- Checkout baseline: `a87fd034d537c9a1a863969e8ea4c4b3b13d9ec9`, with existing local research changes.
- Exact ARM64 driver: `qcwlanhmt8380.sys` 1.0.4374.1300, SHA-256
  `ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`.
- Packaged `wlanfw20.mbn`: SHA-256
  `74f2ffde049d523cba7bc7660f4d9806110bbe1d1ecac9565f50028652a861f3`.
  The package is not proof of the running firmware identity.
- No device access, scan, trace, private request, register read, firmware change
  or clock adjustment. Existing acquisition quarantine remains in force.

## Candidate producer fields

### The additional reordering block

The exact driver declares management event `0x7001` with twelve decoded slots.
Slot 3 has tag **978 (`0x3d2`)**, element size **20 bytes** and fixed-size shape.
Independent evaluation of the pinned public TLV enum assigns the same tag to
`wmi_mgmt_rx_reo_params`; its five 32-bit fields occupy 20 bytes. The public event
table places it in the same slot after the header, frame and extended RSSI array.
This is a schema match, not evidence that a live event contained the block.
See [the pinned TLV definitions](https://github.com/OnePlusOSS/android_kernel_modules_and_devicetree_oneplus_sm8650/blob/38d50357db2728300a61b6f757f2d3a09651c155/vendor/qcom/opensource/wlan/fw-api/fw/wmi_tlv_defs.h).

The [pinned WMI reference](https://github.com/OnePlusOSS/android_kernel_modules_and_devicetree_oneplus_sm8650/blob/38d50357db2728300a61b6f757f2d3a09651c155/vendor/qcom/opensource/wlan/fw-api/fw/wmi_unified.h)
describes these candidate fields. Offsets include this block's own TLV header:

| Offset | Reference field | Reference meaning |
|---|---|---|
| `+0x00` | `tlv_header` | Tag and length |
| `+0x04` | `global_timestamp` | 32-bit microsecond time associated with the last firmware-forwarded management frame; described as common across chips |
| `+0x08` | `mgmt_pkt_ctr_link_info` | Bits 12–14: protocol link ID; bit 15: packet-counter validity; bits 16–31: management packet counter |
| `+0x0c` | `rx_ppdu_duration_us` | Receive duration in microseconds |
| `+0x10` | `mpdu_end_timestamp` | MPDU-end time in microseconds, based on the HWMLO timer |

The main reference header separately describes the local RX TSF low word as
descriptor-derived and its high word as a subsequent register read. Its signed
`tsf_delta` can be zero when the peer timestamp is unavailable.

Interpretation rules for future evidence:

- The packet-counter validity bit does not certify every timestamp in the block.
- A protocol link ID is not automatically a hardware timer ID or clock epoch.
- A 16-bit packet counter can wrap. It does not establish permanent uniqueness.
- The phrase common across chips does not establish synchronization across
  independent laptops or a relationship to QPC.
- PPDU start, MPDU end, peer-advertised TSF and local TSF remain separate events
  and clock-domain candidates. Do not subtract them without a verified mapping.
- Do not concatenate split TSF words as an atomic sample until the producer's
  rollover handling is established. Do not invent a correction based on an
  assumed firmware delay.

The selected Windows handler reads only the header/frame slots and does not
forward the original decoded wrapper. The additional block is therefore a
candidate for preservation **before that reduction**, not a new discovered
userspace getter. See [the management handoff](qualcomm-management-rx-handoff.md).

### Descriptor evidence is narrower than firmware semantics

The corrected Linux WCN7850 descriptor uses the QCN9274 layout. Its timestamp
high word, PHY metadata and low word occur at descriptor `+0x60`, `+0x64` and
`+0x68`, matching the Windows diagnostic locations. The old WCN7850-specific
structure was removed because its layout was incorrect, not merely renamed.
See [the corrective patch](https://lists.infradead.org/pipermail/ath12k/2024-October/003901.html)
and [Linux v6.13 descriptor definitions](https://github.com/torvalds/linux/blob/v6.13/drivers/net/wireless/ath/ath12k/rx_desc.h).

The Linux comments describe PPDU-start time on the medium and make PPDU-start
status dependent on first-MPDU context. This is an additional validity question
to resolve for the Windows producer; a generic descriptor-completion bit alone
must not become a timestamp qualification rule. The pinned Qualcomm kiwi/v2
header independently has the same split-field arrangement. Its declaration
does not by itself establish the active clock rate.

### Packaged firmware inspection

The packaged image hash matches the side investigation. A bounded ELF-header
inspection finds no section-header table. A printable-string search found no
management-RX/TSF-producer anchor matching the searched names. This does not
establish that the producer is absent: names can be omitted and some referenced
code can be outside file-backed segments. No exact producer disassembly, live
firmware identification or split-word algorithm was recovered in this pass.

## Where one event must be preserved

The shared dispatcher already studied for FTM also dispatches event `0x7001`.
The management-specific cleanup case is now followed explicitly:

| Location | Selected static operation | Ownership consequence |
|---|---|---|
| `0x168df8..0x168e0c` | Call decoder `0x1ba4e0` with event payload and length | Produces a temporary wrapper containing pointers/counts |
| `0x169004..0x169034` | Invoke the registered handler with that wrapper | Identified opportunity to preserve event data during callback ownership |
| `0x1690c0..0x1690c8` | Call cleanup `0x1bae60` after callback return | Wrapper cannot be retained as an application record |
| `0x1bc5e8..0x1bc5f4` | Match selector `0x7001` and branch to `0x1bc6e4` | Selects the management-event cleanup case |
| `0x1bc6e4..0x1bc7cc` | Check allocation flags at `12 + 16*n`, for slots 0–11 | Free allocated, non-null slot data; borrowed slots still depend on original event storage |
| `0x1bb564..0x1bb574` | Finish conditional slot cleanup, free wrapper and null its owner pointer | All wrapper slots share this temporary lifetime boundary |
| `0x1690cc..0x169100` | Continue through original event-buffer release paths | Borrowed event data does not become independently owned |

The decoder can borrow original input or allocate normalized storage. Copying
the wrapper alone would preserve pointers, not the pointed-to data. Original
wire lengths and normalized slot sizes should be recorded separately.

For an instrumented or vendor-supported exporter, the bounded record needs:

- Original event selector and payload bytes, or an explicitly defined complete
  set of copied slots with presence, lengths and normalization status.
- The frame from that same event, not a later BSS-cache lookup.
- Main timing header and reordering block, including absent/invalid states.
- Producer/source identifiers and reset/continuity evidence, kept separate from
  a host-assigned record sequence.
- Publication and loss state, followed by a copy into application-owned storage.

No kernel pointer may escape as a substitute for those copies. The callback's
IRQL, synchronization, bounded allocation strategy and teardown behavior still
need qualification before implementing a live driver-side exporter. The
[existing C prototype](../evidence/owned-timestamp-export-prototype.md) remains
synthetic-only; its 64-byte demonstration payload is not a complete management
event transport.

## What the host-time path actually records

At `0x168f88..0x168f94`, the inspected dispatcher compares the event selector with
`0x7001` and branches to `0x168fe0`, bypassing the event-history write. A null
history pointer also takes that branch. The inspector now decodes this exact
four-instruction pattern and rejects different control flow.

For other eligible events, the history writer calls `0x185a20`, resolving to
`KeQuerySystemTimePrecise`. This is Windows system time, not QPC, and the writer
does not archive the event payload. These are static branch findings; other
logging facilities and runtime configuration are not exhaustively covered.

This removes that particular history as a source of host timing for management
frames. Adding QPC reads around a future event copy would measure host handling
of an already received message. It would not enclose the earlier radio sample.
Microsoft's [cross-timestamp contract](https://learn.microsoft.com/en-us/windows/win32/api/iphlpapi/ns-iphlpapi-interface_hardware_crosstimestamp)
instead requires the hardware clock read to occur between the two host reads.

An eventual record should name host observations by what they measure, such as
callback entry or copy completion. Hardware sampling brackets and conversion
uncertainty remain unavailable until separately established. QPC is a host
interval counter; a derived application clock can map to it without pretending
that delayed firmware delivery was a simultaneous measurement.

## Next acquisition requirements

1. **Bind the producer.** Obtain the matching firmware implementation or a
   vendor-supported event export and establish which timer supplies each field.
   Confirm units, meaningful width, optional-field presence, invalid cases,
   rollover and reset behavior. The current package/header match is insufficient.
2. **Return one complete event.** Use that qualified route to capture before
   reduction, preserve all relevant bytes in owned storage and return one bounded
   record. Reject partial, mismatched, reused, ambiguous or late records. No such
   live route or record was established in this pass.
3. **Qualify correlation independently.** Demonstrate fresh hardware/QPC sampling
   or another justified timing relationship. Callback latency and a fitted line
   alone do not satisfy this requirement.

The [raw-export gate](../evidence/raw-timestamp-export-gate.md) stays closed.
The downstream provider remains diagnostic-only. No new IOCTL, firmware command,
register access or driver patch follows from these addresses or declarations.

## Reproduction and validation

Use normal file-read permission, Python 3.11+ and existing repository dependencies.
No elevation, vendor runtime, device handle or network connection is required by
the inspector. The output parent must exist and the output file must be new:

```powershell
$env:WIFI_TIME_DRIVER_FIXTURE = 'C:\path\to\owned\qcwlanhmt8380.sys'
python research/adapters/inspect_management_rx.py --driver $env:WIFI_TIME_DRIVER_FIXTURE --output artifacts/management-producer-new.json
python -B -m unittest discover -s tests -p test_management_rx_path.py -v
```

- The inspector adds `event_lifetime`, allocation-flag load offsets, the selected
  history exclusion, its time import and range hashes to the existing receipt.
- Exit 0: inspection completed. Exit 1: input/I/O rejected. Exit 2: CLI misuse.
- Input is limited to 16 MiB; the exact driver hash is required. Existing outputs
  are never overwritten. There is no device rollback; only local receipts exist.
- Eight additional ranges, 663 instruction/literal lines, matched fresh
  disassembly against the retained exact-build disassembly.
- Eight focused tests passed, including all owned-image cases. Authored decoder
  cases cover signed branch offsets, malformed/truncated instructions, shifted
  constants, changed branch conditions and invalid/out-of-range addresses.
- `python -m compileall -q research tests` passed. Full
  `python -B -m unittest discover -s tests -v` passed 206 tests with no skips,
  using the owned driver/Windows image fixtures and an initialized ARM64 MSVC
  compiler for the native synthetic exporter harness.
- Tests validate offline interpretation. They do not prove live lifetime,
  firmware contents, simultaneous sampling or timing accuracy.

Local source snapshots and receipts are under ignored
`artifacts/ManagementProducerInvestigation/`. Public findings contain no driver
bytes, firmware, live frames or endpoint identifiers.

## Source provenance and glossary

All Qualcomm source references above use revision
`38d50357db2728300a61b6f757f2d3a09651c155` of the OnePlus-published vendor tree:

| File | Downloaded-file SHA-256 |
|---|---|
| `fw/wmi_unified.h` | `5dd488e9080baad7c4aae327db585817ab4bebd4845ba87ad9116062bf461179` |
| `fw/wmi_tlv_defs.h` | `b1bb42cd8faadd70184ddcd8ef22de1bca5e352748461de2005499ed17c90f7f` |
| [`hw/kiwi/v2/rx_msdu_end.h`](https://github.com/OnePlusOSS/android_kernel_modules_and_devicetree_oneplus_sm8650/blob/38d50357db2728300a61b6f757f2d3a09651c155/vendor/qcom/opensource/wlan/fw-api/hw/kiwi/v2/rx_msdu_end.h) | `f2208982fd20c39b279ee9f0f46b935089c58c85cbc34bd1f25aa0553403a995` |

- **WMI:** firmware/host message interface in this context.
- **REO:** receive reordering; it helps organize frames arriving on multiple links.
- **PPDU / MPDU / MSDU:** physical radio transmission / MAC frame / delivered data
  unit. They are different levels and need not have a one-to-one relationship.
- **HWMLO:** hardware multi-link-operation timer named in the reference. No
  equivalence to TSF, a global TSF report or QPC is established here.
- **Slot:** one decoded pointer/count entry, not an independently owned payload.
- **IRQL:** Windows kernel execution level, which constrains permitted operations.
- **Epoch:** a period of established clock continuity, not merely process uptime.

See the [shared glossary](../glossary.md) for the broader clock terminology.
