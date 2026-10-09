# Qualcomm BSS serialization: frame, age and vendor context

The traced BSS path preserves peer-advertised timestamps and optionally exports Multiple-BSSID profile metadata. Its 28-byte context is profile-processing state in the inspected writers, not a recovered hardware clock. The cache also stores host tick-based aging values. Windows host time follows a separate path, so these fields do not establish a simultaneous radio/host sample.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** Later archive and installed-file inspection located QUTS client-owned byte returns and corrected vendor package/version assumptions; exact adapter-to-producer association remains open. See [current findings](../knowledge/current-findings.md).
<!-- /historical-context -->

## Contents

- [Scope and evidence](#scope-and-evidence)
- [Exact builder and indication](#exact-builder-and-indication)
- [Host age and vendor context](#host-age-and-vendor-context)
- [Decoded context writers](#decoded-context-writers)
- [Retained frame and cache time](#retained-frame-and-cache-time)
- [The Windows-specific pointer hypothesis](#the-windows-specific-pointer-hypothesis)
- [Validation and next work](#validation-and-next-work)

## Scope and evidence

- **BSS:** a wireless network context reported to Windows.
- **TLV:** a typed byte field, described by a tag, length and value.
- **RVA:** an image-relative analysis address, not an application call target.
- **Vendor context:** opaque bytes maintained by the hardware vendor; a name
  does not establish their physical meaning.
- Exact ARM64 driver: `qcwlanhmt8380.sys` 1.0.4374.1300, SHA-256
  `ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`.
- Method: owned-file inspection and bounded fresh disassembly comparison.
  No scan, private request, trace, pointer dereference or device change.

The supplied public-source narrative is a search hypothesis. An older
[Qualcomm trace artifact](https://github.com/edk2-porting/WOA-Drivers-debug/blob/16a42d2e08496b9780b43061705869bb0fe40249/tmf/3776a640-afc1-365f-bede-4bec1f0d7b9a.tmf)
does name cache insertion and BSS enumeration routines, but targets a different
driver. Names, structure layouts and firmware semantics are not transferred from
that artifact to this build. Public Linux/Android fields likewise require an
exact-build connection before they can describe these runtime objects.

## Exact builder and indication

Read the following selected chain from top to bottom. It is static evidence;
the complete management-RX-to-cache insertion chain remains under investigation.

| Stage | Exact-build operation | Consequence |
|---|---|---|
| Cache-side caller `0x20be8..0x20c18` | Supplies frame-related arguments and object `+0x394` to `0x25780` | A concrete cache-to-report call site; entire enclosing routine is not qualified here |
| `StaWdiScanBssEntryListIndication`, `0x25780` | Calls builder `0x57830` at `0x2580c` | Resolves the station reporting builder |
| `PortConstructBssEntry`, `0x57830` | Allocates a zeroed 144-byte container plus frame bytes and optional 28-byte context | Creates owned storage for selected report inputs |
| Frame copy `0x57a14..0x57a24` | Copies input bytes and selects beacon versus probe member using subtype `0x80` | Preserves supplied frame bytes; their upstream transformations still need tracing |
| List construction `0x25938..0x25984` | Copies 144-byte containers into a report array while backing allocations remain retained | Temporary pointer-bearing containers remain internal |
| Serializer call `0x259a0` | Calls `0x161a50`, whose descriptor root is `0x308100` | Converts the internal list to a serialized indication |
| Indication `0x259b0..0x259cc` | Uses selector `0x3e` and common sender `0x13c430` | Selected BSS-list reporting path toward Windows |
| Cleanup `0x259d0..0x25a48` | Releases serialized output and the retained container/backing allocations | Not an application-accessible pointer queue |

The generated BSS container schema at `0x3084e0` describes eight members in
144 bytes. Its field table begins at `0x3083c0`:

| Tag | Container offset | Member role |
|---|---|---|
| `0x02` | `+0x04` | BSSID |
| `0x09` | `+0x10` | Probe response bytes |
| `0x0a` | `+0x28` | Beacon bytes |
| `0x0b` | `+0x40` | Signal information |
| `0x3a` | `+0x48` | Channel information |
| `0x0d` | `+0x50` | Optional vendor device context |
| `0xba` | `+0x68` | Optional age information |
| `0x112` | `+0x78` | Additional member, not decoded here |

These offsets belong to the internal serialization container. They are not
on-air frame offsets, RX descriptor offsets or `WLAN_BSS_ENTRY` offsets.

## Host age and vendor context

**Age:** the complete inspected builder zeroes the container and sets optional
flags for frame bytes and, conditionally, device context. It does not populate
`+0x68` or enable the age member. Therefore this selected construction path does
not establish a driver-supplied age timestamp. Other builders may behave
differently. The separate [Windows host-time trace](windows-bss-host-time.md)
now identifies the OS-side source and cache-to-API copy, with configuration and
cache-refresh caveats.

Microsoft defines BSS age as host discovery time, with system-time APIs as its
source. That public contract is not evidence that this particular builder supplies
the optional field. See [BSS age information](https://learn.microsoft.com/en-us/windows-hardware/drivers/network/wdi-tlv-bss-entry-age-info).

**Vendor context:** when its input predicate passes, `0x57a70..0x57a9c` copies
exactly 28 bytes into owned backing storage and enables the device-context member.
The inspected caller passes cache-object `+0x394`. A cache-update window at
`0xea230..0xea268` copies 28 bytes from another object's `+0x248` into that region.
The follow-up below identifies concrete writers and profile-processing semantics.
Live contents and every possible writer remain unqualified.

## Decoded context writers

**Multiple-BSSID (MBSSID)** lets one transmitted beacon describe additional BSS
profiles. These profile identifiers and addresses are unrelated to clock IDs.

The exact driver labels `0x94f10` as `ieee80211_parse_beacon` and `0x9e818` as
`util_scan_parse_mbssid`. The selected writers establish this 28-byte layout:

| Context offset | Inspected content | Evidence |
|---|---|---|
| `+0x00` | Profile index; zero in the base-beacon initialization | `0x9e47c..0x9e488` copies the index from the parsed profile element |
| `+0x01` | Byte-sized profile capacity derived from `1 << MaxBSSIDIndicator` | `0x95678..0x95690` and `0x9e984..0x9e998`; not a count of observed frames |
| `+0x02..+0x07` | Transmitting BSSID, six address bytes | Base parser copies frame-header `+0x10`; profile parser copies the supplied transmitting address at `0x9e46c..0x9e478` |
| `+0x08`, `+0x0c`, `+0x10`, `+0x14` | 32-bit profile-fragment/assembly state | `0x9ea70`, `0x9e3ec`, `0x9eaa0`, `0x9e448` and `0x9e4dc`; exact public field names are not assigned |
| `+0x18` | Profile-expansion processing flag | Set to one at `0x9ec88`; the consumer at `0x98ac8..0x98acc` uses it to avoid another parse through `0x9e818` |
| `+0x19..+0x1b` | Zero in the inspected initialization/copy paths | Remaining bytes of the zeroed 28-byte object; no timestamp meaning assigned |

The base parser zeroes a temporary, writes the address and profile-capacity byte,
and copies all 28 bytes to parsed-object `+0x248` at `0x95694`. The MBSSID path
also constructs profile state in a stack object, uses helper `0x9e378`, and passes
that context through `0x987d8` and `0x9cea8` to cache ingress `0xec1d0`.
At `0xec4a8..0xec4bc`, a non-null supplied context replaces parsed-object `+0x248`.
The existing update then copies it to cache `+0x394` and ultimately the optional
BSS device context.

No counter read or 64-bit timestamp assignment appears in these inspected
context producers. This classifies the observed payload family as MBSSID state;
it does not certify every runtime value or exclude unrelated writers elsewhere.

## Retained frame and cache time

The retained cache contains distinct objects and time values:

| Cache field | Data source / meaning in the inspected path |
|---|---|
| `+0x88`, eight bytes | Peer-advertised timestamp copied from the start of the received beacon/probe body, via parsed-object `+0x18`, at `0xea098..0xea0ac` |
| `+0x6c`, 32 bits | Low word of the host tick-derived millisecond value passed into cache update; written at `0xea090..0xea0a4` |
| `+0x70`, 32 bits | Host tick-derived time used by signal-aging/filter logic; conditional update at `0xea318..0xea320` |
| `+0x318`, 32 bits | Previous `+0x6c` retained when the frame subtype changes at `0xea07c..0xea08c` |
| `+0xa0`, pointer | Owned retained frame-body allocation |
| `+0xa8`, 16 bits | Retained body length, potentially including appended saved information elements |
| `+0xaa`, 16 bits | Allocated capacity in the selected allocation path |
| `+0xb0`, pointer | Information elements start at retained body `+12` |
| `+0xb8/+0xba`, 16 bits | Information-element lengths maintained by the selected update |

The peer timestamp source is explicit: `0xec270` passes full frame `+24` as the
beacon/probe body to the parser; `0x95088..0x9508c` retains that pointer at parsed
`+0x18`. Cache update later copies its first eight bytes to `+0x88`.

At `0xec55c..0xec5f4`, ingress obtains `KeQueryTimeIncrement`, reads the Windows
shared-data tick count (literal at `0xec620`), multiplies those values and divides
by 10,000. The result is host tick-derived milliseconds. The value is passed
through `0xe8110` to `0xe9a00`; it is not the AP counter, radio RX TSF, QPC or the
1601-based Windows system timestamp. No conversion between these domains is
qualified by this arithmetic.

The body is copied from the caller's frame `+24`: bridge sites `0xe830c` and
`0xe8390` supply that pointer. Update `0xea730..0xea828` checks allocation capacity,
allocates if required, and copies the body. `0xea838` sets the IE pointer to body
`+12`. A later branch can append saved IE bytes from cache `+0x320` and update the
lengths (`0xea85c..0xea894`). The cache also has alternate-frame retention branches.
Consequently, an exported BSS body must not automatically be treated as a complete,
untouched original MPDU or atomically paired with every independently updated
cache time field.

## The Windows-specific pointer hypothesis

The earlier management-RX conversion at `0x1a6080` stores a pointer at output
`+0x30`. Its producer is `0x5d718`, which tail-calls `0x5d750`. The latter's
diagnostic name is `ieee80211_find_dot11_channel_extend`; its caller supplies
the receive frequency and channel-selection parameters.

That evidence identifies a channel lookup, not a verified instance of the public
`mgmt_rx_event_params.rx_params` member. The returned object's complete contents
are not decoded here, and other Windows-specific objects may exist. A public
structure comment alone cannot assign a Windows binary pointer's identity.

The selected WMI handler still does not read header `+0x34/+0x38/+0x3c`. The new
BSS serializer does not overturn that earlier bounded finding. A tuple combining
peer TSF, local RX TSF and host observation time remains a hypothesis requiring
actual producer/consumer evidence.

## Validation and next work

The existing [management inspector](../../research/adapters/inspect_management_rx.py)
now includes six additional code ranges and the generated BSS field table.
Its fixture test checks tag/offset pairs and selected call connections. Decoder
outputs inventory locations; manual inspection supplies the behavioral conclusions.

```powershell
python research/adapters/inspect_management_rx.py --driver 'C:\path\to\owned\qcwlanhmt8380.sys' --output artifacts/bss-inspection-new.json
python -m unittest discover -s tests -p test_management_rx_path.py -v
```

The tool needs ordinary file-read permission, bounds its input and never overwrites
an output. Exit codes are 0 for inspection, 1 for rejected input/I/O, and 2 for CLI
misuse. Outputs belong under ignored `artifacts/`; there is no device rollback.
Follow-up receipts are in `artifacts/BssSerializationInvestigation/`.

The context/cache follow-up adds eight ranges and an import/literal receipt under
`artifacts/BssCacheWritersInvestigation/`. All constants are read from owned files;
the tool never reads the shared-data address from kernel memory.

Next: qualify a producer carrying local hardware receive time and its identity.
The observed MBSSID context and host cache times do not supply that missing record.
No new live request is justified solely by a serializer location. See the
[management handoff](qualcomm-management-rx-handoff.md) and
[raw-export gate](../evidence/raw-timestamp-export-gate.md).
