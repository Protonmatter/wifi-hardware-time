"""Decode peer-advertised TSF from a saved ordinary 802.11 management frame.

Input is one raw MPDU, without radiotap/PCAP headers; optional trailing FCS must
be declared. No capture, scan, requests, device access or clock qualification.
Output includes peer addresses: keep real capture results out of public Git.
Exit 0: structural diagnostic decode; 1: rejected input; 2: CLI usage error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
from typing import Any
import zlib

MAX_FRAME_BYTES = 4096  # Inspection bound, not the standard's maximum frame size.


def _mac(value: bytes) -> str:
    return ':'.join(f'{byte:02x}' for byte in value)


def decode_management_tsf(frame: bytes, *, fcs_present: bool = False) -> dict[str, Any]:
    """Return an owned structural observation; never infer local RX time or a reply.

    Supported profile: protocol version zero, unfragmented ordinary beacon/probe
    response with a 24-byte header. IE lengths are checked; their internal
    semantics, mandatory presence, authentication and MLO mapping are not decoded.
    """
    if type(frame) is not bytes or type(fcs_present) is not bool:
        raise ValueError('invalid_input_type')
    if not 36 + (4 if fcs_present else 0) <= len(frame) <= MAX_FRAME_BYTES:
        raise ValueError('invalid_frame_length')
    mpdu = frame
    if fcs_present:
        mpdu = frame[:-4]
        if struct.unpack('<I', frame[-4:])[0] != zlib.crc32(mpdu):
            raise ValueError('bad_fcs')
    control = struct.unpack_from('<H', mpdu)[0]
    subtype = (control >> 4) & 15
    if control & 15 or subtype not in (5, 8):
        raise ValueError('unsupported_frame_type')
    if control & 0xC300:  # Protected, Order/alternate header, ToDS or FromDS.
        raise ValueError('unsupported_header_layout')
    sequence_control = struct.unpack_from('<H', mpdu, 22)[0]
    if control & 0x0400 or sequence_control & 15:
        raise ValueError('fragmented_frame_unsupported')
    receiver, transmitter, bssid = mpdu[4:10], mpdu[10:16], mpdu[16:22]
    if any(not any(address) or address[0] & 1 for address in (transmitter, bssid)):
        raise ValueError('invalid_source_address')
    # Limit the profile to ordinary broadcast beacons and unicast/broadcast probes.
    broadcast = b'\xff' * 6
    if not any(receiver) or (receiver[0] & 1 and receiver != broadcast):
        raise ValueError('unsupported_receiver_address')
    if subtype == 8 and receiver != broadcast:
        raise ValueError('unsupported_beacon_receiver')
    position, elements = 36, 0
    while position < len(mpdu):
        if len(mpdu) - position < 2:
            raise ValueError('truncated_information_element')
        end = position + 2 + mpdu[position + 1]
        if end > len(mpdu):
            raise ValueError('truncated_information_element')
        elements += 1
        position = end
    tsf, interval, capability = struct.unpack_from('<QHH', mpdu, 24)
    return dict(
        schema='wifi-management-tsf-diagnostic/v1', qualification='diagnostic-only',
        input_origin='unverified-supplied-bytes', live_acquisition=False,
        frame_sha256=hashlib.sha256(frame).hexdigest(), frame_bytes=len(frame),
        event_kind='beacon' if subtype == 8 else 'probe-response',
        request_association='not-applicable' if subtype == 8 else 'unestablished',
        request_id=None, receiver=_mac(receiver), retry=bool(control & 0x0800),
        sequence_number=sequence_control >> 4,
        peer_tsf_raw=str(tsf), peer_tsf_unit='microseconds', field_bits=64,
        clock=dict(domain='peer-advertised-bss-tsf', scope='claimed-transmitter-bssid',
                   transmitter=_mac(transmitter), bssid=_mac(bssid),
                   hardware_timer_id=None, link_id=None, epoch=None),
        beacon_interval_tu=interval, capability=capability, information_elements=elements,
        fcs_status='verified' if fcs_present else 'not-provided',
        source_authenticated=False, local_rx_timestamp=None, host_qpc=None,
        sample_age_ns=None, sampling_reference_qualified=False, clock_input_eligible=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('frame', type=Path)
    parser.add_argument('--fcs-present', action='store_true', help='Validate a trailing four-byte FCS')
    args = parser.parse_args()
    try:
        if not args.frame.is_file():
            raise OSError('input_unavailable')
        with args.frame.open('rb') as stream:
            data = stream.read(MAX_FRAME_BYTES + 1)
        result = decode_management_tsf(data, fcs_present=args.fcs_present)
        print(json.dumps(result, allow_nan=False))
        return 0
    except OSError:
        reason = 'input_unavailable'
    except ValueError as error:
        reason = str(error)
    print(json.dumps(dict(status='rejected', reason=reason, live_acquisition=False)))
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
