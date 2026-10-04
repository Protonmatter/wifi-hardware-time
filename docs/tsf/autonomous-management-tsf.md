# Autonomous TSF observations from saved management frames

A saved beacon or probe response can expose the peer's advertised TSF without matching a private host request. The new decoder preserves frame identity separately from clock identity and never invents local receive time or request association. It provides an offline diagnostic building block; live capture, clock mapping and freshness remain separate qualification tasks.

## Contents

- [What is implemented](#what-is-implemented)
- [Run and consume](#run-and-consume)
- [Identity and timing limits](#identity-and-timing-limits)
- [Validation and next connection](#validation-and-next-connection)

## What is implemented

`research/tsf/decode_management_tsf.py` accepts one ordinary, unfragmented 802.11
beacon or probe-response MPDU. MPDU means the MAC frame itself, starting with
Frame Control; PCAP and radiotap capture headers must already be removed by a
separately qualified capture reader. It has no capture or scan function.

- Decode the 64-bit little-endian peer timestamp, beacon interval and capability.
- Preserve receiver, transmitter, BSSID, sequence number and retry bit.
- Keep the advertised peer clock separate from absent local RX/QPC observations.
- For a beacon, request association is `not-applicable`. For either unicast or
  broadcast probe responses it is `unestablished`; destination alone is insufficient.
- Validate element lengths and, when declared present, the trailing frame check
  sequence (FCS). FCS detects corruption; it does not authenticate the transmitter.

The fixed-field layout follows the [Linux 802.11 management-frame structures](https://github.com/torvalds/linux/blob/master/include/linux/ieee80211.h).
Linux's [BSS reporting interface](https://cdn.kernel.org/doc/html/latest/driver-api/80211/cfg80211.html)
likewise distinguishes the TSF sent by a peer from local reception metadata.
These references establish format/meaning, not the behavior of this Windows NIC.

## Run and consume

Python 3.11+, standard library only. From the repository root:

```powershell
python research/tsf/decode_management_tsf.py path/to/saved-frame.bin
python research/tsf/decode_management_tsf.py path/to/saved-frame-with-fcs.bin --fcs-present
python -m unittest discover -s tests -p test_management_tsf.py -v
```

```python
from research.tsf.decode_management_tsf import decode_management_tsf

record = decode_management_tsf(saved_frame_bytes, fcs_present=False)
peer_tsf_us = int(record['peer_tsf_raw'])
assert record['clock_input_eligible'] is False
```

- Input must be immutable `bytes` for the API, or an existing raw-frame file for
  the CLI. Maximum accepted input is 4096 bytes, an inspection limit rather than
  a claim about the standard's maximum size.
- Choose FCS presence from capture provenance. It cannot always be inferred from
  the bytes; an incorrect option is not guaranteed to be detectable.
- Output is JSON stdout, including peer addresses. Keep real capture files and
  results private. The tool does not write output files or alter device state.
- Exit 0 means structural diagnostic decoding; 1 means rejected/unavailable
  input; 2 means CLI usage error. No elevation, network access or rollback needed.
- Reject unsupported frame types, version, DS/protection/alternate-header flags,
  fragments, invalid source-address forms, unsupported receiver forms, short
  fixed fields, truncated information elements and invalid declared FCS.

The narrow profile accepts broadcast beacons and unicast/broadcast probe responses.
It does not decode protected or special-format beacons, decrypt anything, validate
mandatory information elements, parse MLO subelements or reassemble fragments.

## Identity and timing limits

| Output | Meaning |
|---|---|
| `clock.domain` | Peer-advertised BSS TSF, not the local Qualcomm TSF or QPC |
| `clock.transmitter`, `clock.bssid` | Source claims in the frame, not authenticated device identity |
| `clock.hardware_timer_id`, `clock.link_id`, `clock.epoch` | Null; no mapping or continuity evidence supplied |
| `peer_tsf_raw`, `peer_tsf_unit` | Exact decimal counter value and the timestamp field's microsecond unit |
| `field_bits=64` | On-air field width; does not prove accuracy or physical implementation precision |
| `frame_sha256` | Identity of supplied bytes, not a globally unique transmission or replay detector |
| `sequence_number`, `retry` | Preserved frame metadata; do not prove an exchange/session match |
| `local_rx_timestamp`, `host_qpc`, `sample_age_ns` | Null; file-read time cannot substitute for receive/sample time |
| `input_origin` | Unverified supplied bytes, which may be synthetic, stale or replayed |
| `clock_input_eligible=false` | No active clock model may consume this profile as qualified timing evidence |

Two equal numeric TSF values from different BSS/source contexts must remain
separate. Equal source addresses across captures do not prove the same clock
epoch: AP restart, address reuse and spoofing remain possible. Parsing an
autonomous observation does not resolve any of those questions.

## Validation and next connection

Nine tests use authored frames, including a large 64-bit counter value, distinct
BSS claims, both probe destinations, retries, FCS corruption, malformed lengths,
unsupported layouts/types and CLI success/rejection. No test frame is a recorded
radio observation. No real frame was captured or replayed to qualify this decoder
in this pass, and the firmware-report evidence format was not changed.

The next integration requires a real capture with qualified provenance plus a
local hardware RX timestamp and its own clock identity/reference point. Preserve
the pair as **peer advertised TSF + local receive timestamp**; do not substitute
one for the other. Then establish propagation/reference-point and host-clock
relationships before clock admission. The existing private-request quarantine is
unchanged; a different observation profile cannot retroactively pass that campaign.

The [management RX handoff trace](../adapters/qualcomm-management-rx-handoff.md)
locates the internal frame copy and metadata narrowing. It does not establish
an application export preserving the candidate local RX TSF fields.

See [clock versus event identity](tsf-association-and-quarantine-disposition.md#clock-identity-is-separate-from-event-identity)
and the [complete-record gate](../evidence/raw-timestamp-export-gate.md).
