# Access to pre-aggregation FTM records: offline follow-up

Can this Windows build expose individual absolute ranging timestamps? Inspection confirms an internal measurement buffer, but the established caller and logging paths return aggregates or time differences. No supported raw-timestamp export was found in the inspected paths; unknown record fields, clock meaning, and exchange identity still need qualification.

<!-- current-context:2026-10-04 -->
**Current context (2026-10-04):** QXDM WLAN RTT definitions are a new schema lead. They have not been matched to a complete live four-event export from this adapter. See [current findings](../knowledge/current-findings.md).
<!-- /current-context -->

FTM (Fine Timing Measurement) is Wi-Fi ranging; RTT is round-trip time. An ETL is a saved Windows event trace. An ABI defines how binary components exchange arguments and data; an RVA locates evidence within one binary. See the [glossary](../glossary.md).

## Contents

- [Evidence identity and scope](#evidence-identity-and-scope)
- [What the supported Windows contracts return](#what-the-supported-windows-contracts-return)
- [Exact-build boundaries before aggregation](#exact-build-boundaries-before-aggregation)
- [Saved ETLs contain rendered messages, not an exposed record blob](#saved-etls-contain-rendered-messages-not-an-exposed-record-blob)
- [Vendor transport is available as an API mechanism, not a raw-FTM contract](#vendor-transport-is-available-as-an-api-mechanism-not-a-raw-ftm-contract)
- [Required raw-data contract and next probe](#required-raw-data-contract-and-next-probe)
- [Validation and remaining limits](#validation-and-remaining-limits)

Current follow-up: [timing boundaries](../memory-ring/timing-boundary-investigation-2026-10-03.md) rechecked the bounded internal FTM identity comparison. It did not establish raw absolute export; this report's findings remain applicable.

Status: **no supported export of absolute FTM event timestamps has been established
on the inspected Windows build**. The existing path exposes logged delta operands
and an aggregate ranging result. Windows provides extensible vendor communication
mechanisms, but their existence does not supply a Qualcomm raw-measurement contract.

This follow-up read installed binary files, saved disassembly and three existing
ETLs, and consulted Microsoft documentation. It sent no private requests, initiated
no FTM exchange, changed no diagnostic setting, and performed no device-memory or
kernel-memory access. Only this report was added. Vendor binaries, disassembly,
raw records and endpoint identifiers are not included in the report.

## Evidence identity and scope

The following installed file hashes were recomputed and matched the earlier
qualification. RVAs below refer only to these exact binaries; they are not API
entry points or runtime call targets.

| File | SHA-256 |
|---|---|
| `qcwlanhmt8380.sys` | `ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115` |
| `wlanapi.dll` | `925f1c50e1c86d625aeb87e39a307e067a3e6f54eedbd8a598d64423203c234b` |
| `locationframework.dll` | `1ab04f90fdd1b0b920e4cf0f50bdde41b2824804f4006eed7a532d83bfd108e0` |

The driver is the ARM64 1.0.4374.1300 build. The DLL file versions read in this
pass were 10.0.26100.9278 and 10.0.26100.8972, respectively. The driver hash was
checked against the locally retained `qualcomm-pe.json` identity, and relevant
driver ranges were freshly disassembled using the installed MSVC `dumpbin`.
No complete audit of all driver routes or firmware implementations is claimed.

The [clock-relationship investigation](../clock-models/clock-relationship-investigation.md)
establishes the 64-byte record reduction and saved delta replay. The
[FTM provenance report](ftm-result-provenance.md) establishes later filtering
and aggregation. Those findings are prerequisites, not evidence that the
unconsumed bytes have now been recovered.

## What the supported Windows contracts return

WiFiCx is the Windows Wi-Fi driver framework. Its documented FTM completion carries responses per target. Its response
schema includes target identity/status, measurement count, signal information,
bandwidth, RTT, variance, optional propagation information, and location-report
information. The documented fields do not include four absolute event times,
their counter epochs, or a per-exchange timestamp association. This is a limit
of the inspected contract, not proof that the firmware lacks those quantities.
See [FTM completion](https://learn.microsoft.com/en-us/windows-hardware/drivers/netcx/ndis-status-wdi-indication-request-ftm-complete)
and [WiFiCx FTM response](https://learn.microsoft.com/en-us/windows-hardware/drivers/netcx/wdi-tlv-ftm-response).

The RTT unit is picoseconds. Some response tables still display an unsigned
type, while Microsoft's WDI 1.1.9 change history explicitly records a change to
signed RTT. The existing exact-build decoder retains the signed 32-bit result
verified in the Windows consumer. Neither documentation establishes the units
or width of an unexported absolute firmware timestamp. See
[RTT](https://learn.microsoft.com/en-us/windows-hardware/drivers/network/wdi-tlv-rtt)
and [WDI changes](https://learn.microsoft.com/en-us/windows-hardware/drivers/network/wdi-doc-change-history).

The installed DLL still exports `WlanInternalRequestFTM` at RVA `0x21780` and
`WlanInternalCancelFTMRequest` at `0x21560`, verified by PE export inspection.
Export presence does not make their private ABI a supported public interface.
The previously reconstructed 104-byte callback and its current decoder expose
aggregate fields; they do not expose the opaque 16 bytes in each earlier firmware
record. Repeating that callback request alone has no demonstrated mechanism for
recovering those bytes. The prior callback reconstruction, including its limits,
is documented in [experiments](../acquisition/experiments.md#ftm-request-and-callback).

## Exact-build boundaries before aggregation

Fresh inspection of the OEM response handler at `0x1477f0` and measurement parser
at `0x146ef0` provides more precise requirements for a future record export:

| Range | Observed operation | Implication for a future exporter |
|---|---|---|
| `0x147890`–`0x1478dc` | Require at least `0x18` response-header bytes; check header tag `0x21`; route subtype 4 toward measurement parsing | Preserve and validate envelope length, tag and subtype before interpreting a record |
| `0x147964`–`0x147978` | Compare low 16 bits of the response word at `+0x08` with an 8-bit value in driver request context | There is an internal request correlation check; it is not a proven on-air dialog/follow-up token or a globally unique exchange ID |
| `0x1479a4`–`0x147a58` | Manage fragment accumulation, reject accumulated size at or above `0x1388`, append response data after the `0x18` header, and test the more-fragments bit | An isolated fragment cannot safely be treated as a complete measurement record set |
| `0x147a80`–`0x147a98` | Call the measurement parser for subtype 4 when the final fragment arrives, then clear accumulated length | A future supported export must occur while complete data is available and retain its association metadata |
| `0x146f68`–`0x1470a8` | Check measurement/header/container tags `0x29`, `0x10`, `0x2a`, and the following container before walking records | Per-record fields need their surrounding response and peer context |
| `0x147148`–`0x14718c` | Bounds-check the next 64-byte record, check tag `0x2b`, and subtract two 32-bit words at `+0x18` and `+0x1c` | Confirms the delta operand widths and reduction; it does not establish absolute timestamp widths |
| `0x1471bc`–`0x14742c` | Log selected delta/result/radio fields; the inspected record loop does not load `+0x08..+0x17` | These bytes remain an investigation target, not an implemented log-based extraction path |

The assembly accesses and control flow above were observed directly. Semantic
labels for unknown header bits, record version, physical sampling point, and
absolute clock domain have deliberately not been assigned. Historical layouts
from another firmware family cannot qualify this installed firmware's contract.

The response handler therefore has a concrete internal pre-aggregation buffer.
That fact does **not** establish a supported caller interface to obtain it.
Inspecting it through an arbitrary memory read, patch or debugger would be a
different workstream and was not performed.

## Saved ETLs contain rendered messages, not an exposed record blob

The three existing `ftm.etl` files were read with `Get-WinEvent -Oldest`. For the
WLAN diagnostic provider used by the extractor, every returned event had one
`System.String` property. The inventory was:

| Saved run | Event ID 1, one string | Event ID 19, one string |
|---|---:|---:|
| `WifiFtm-83d68ef1a7aa` | 3080 | 2618 |
| `WifiFtm-89003fb1ba0a` | 4266 | 3928 |
| `WifiFtm-43963cbc551c` | 1327 | 839 |

This is a payload-shape inventory for that provider in those files. It does not
exclude a textual hex dump, another provider, disabled instrumentation, or an
alternate firmware reporting mode. The inspected FTM record-loop logging sites
and the existing strict parser establish access to `t3_del`, `t4_del`, and signed
`rtt`; they do not establish a log site for the opaque 16-byte region. No raw
firmware record was recovered during this pass. ETL hashes for these runs are
retained in [FTM provenance](ftm-result-provenance.md#replay-evidence).

## Vendor transport is available as an API mechanism, not a raw-FTM contract

Microsoft documents enumeration of device-service GUIDs and vendor commands with
a service GUID (unique service identifier), opcode (operation selector) and input/output buffers. These APIs do not assign a
standard raw-FTM opcode or payload schema. A command must come from the applicable
vendor contract; guessing an opcode is not justified by enumeration. See
[service enumeration](https://learn.microsoft.com/en-us/windows/win32/api/wlanapi/nf-wlanapi-wlangetsupporteddeviceservices)
and [device-service command](https://learn.microsoft.com/en-us/windows/win32/api/wlanapi/nf-wlanapi-wlandeviceservicecommand).

An earlier saved elevated enumeration returned five service GUIDs and recorded
zero service commands sent. This pass read that artifact; it did not repeat the
live enumeration. Fresh static inspection supplies a useful constraint:

- The supported-services handler at `0x13312c`–`0x133158` publishes five entries
  from the constant table at `0x33e060`.
- The command dispatcher at `0x133334`–`0x1333ac` searches four 24-byte
  GUID/handler entries beginning at `0x2ff070`.
- Those entries point to `0x12a2a0`, `0x12a4c0`, `0x12a9b0`, and `0x12acf0`.
  Nearby diagnostic names identify test-pipeline, SAR, antenna, and interface
  configuration handlers. No raw-FTM command is established by these four names
  or by their presence in this dispatcher.

Five advertised services consequently cannot be assumed to mean five working
command routes, much less a raw-ranging route. This bounded dispatcher inspection
does not exclude other indications, nested vendor protocols, or separately gated
functionality.

A documented unsolicited-notification route also exists. A client registers for
device services and the device-service notification source; notifications carry
a service GUID, opcode, size and opaque vendor blob. Microsoft explicitly states
that registration does not validate driver support. No FTM-associated notification
or record schema has been identified here. See
[notification registration](https://learn.microsoft.com/en-us/windows/win32/api/wlanapi/nf-wlanapi-wlanregisterdeviceservicenotification)
and [notification payload](https://learn.microsoft.com/en-us/windows/win32/api/wlanapi/ns-wlanapi-wlan_device_service_notification_data).

`WlanIhvControl` is another documented vendor-control envelope. Its generic
buffers do not define FTM timestamps or grant a safe operation to try. It remains
a candidate only if the vendor identifies a supported contract for this build.
See [IHV control](https://learn.microsoft.com/en-us/windows/win32/api/wlanapi/nf-wlanapi-wlanihvcontrol).

## Required raw-data contract and next probe

Before designing an exporter, obtain an exact-build vendor/OEM contract or
supported diagnostic schema answering all of the following:

1. How the raw per-exchange response reaches the caller, including service/API,
   version, opcode if any, access requirements, and whether registration or
   enabling export changes firmware state.
2. Absolute event fields: byte offsets, byte order, meaningful bit widths,
   wrap behavior, units, epoch/reset rules, and physical transmit/receive
   reference points. Treat the 16 unconsumed bytes as opaque until resolved.
3. Validity: one-sided versus two-sided measurements, failed exchanges, stale
   or unavailable timestamps, sentinel values, per-chain duplication, and error
   bounds. Aggregate success is insufficient.
4. Identity: request and response IDs, fragment sequence, peer, burst index,
   dialog/follow-up tokens, and which identifiers associate all four events
   with the same exchange. An internal request ID and a BSSID alone are not
   a complete exchange identity.
5. Clock relationship: whether the event timestamps share a counter with TSF,
   SoC or another clock; any conversion, compensation and calibration already
   applied; and how uncertainty is exposed.

**The next useful supported probe is conditional on that contract.** If the vendor
identifies an already-enabled unsolicited raw-report service, implement a bounded
notification collector for that exact GUID and schema, first validating parsing
against a saved vendor-provided fixture. A later explicitly authorized live check
could subscribe without sending vendor commands and observe one separately
authorized FTM operation. Limit duration and bytes, validate callback lengths,
record loss/truncation, unregister, close handles, and keep payloads private.
Registration success or a blob of the expected length alone must not qualify it.

If no supported service exists, request a vendor-supported diagnostic export of
one complete subtype-4 response before aggregation, with its schema and matching
exchange metadata. Repeating the existing aggregate FTM request cannot resolve
the missing contract. No new probe was implemented or executed in this pass.

## Validation and remaining limits

- Recomputed the three exact binary hashes and inspected DLL exports using
  `pefile`; no DLL functions were invoked.
- Freshly disassembled the listed bounded driver ranges using installed MSVC
  `dumpbin /disasm:nobytes /range:...`; read four handler pointers from the
  on-disk PE image. Only authored behavioral conclusions are retained here.
- Read the three saved ETLs and counted provider event IDs/property types;
  no raw messages or endpoint identifiers were written into this report.
- Cross-checked documented response, command and notification contracts against
  the linked primary Microsoft sources.
- Reviewed the Markdown diff and local links. This documentation-only change
  does not alter parsers or runtime behavior, so no new code tests were added.

Remaining limits: installed firmware identity/schema parity, actual raw event
contents, absolute widths/units/epochs, per-exchange validity and identity,
notification delivery, sampling semantics and external accuracy all remain
unqualified. A future export needs separate validation at each of these boundaries.
There is no operational rollback: this pass made no system or device changes.
