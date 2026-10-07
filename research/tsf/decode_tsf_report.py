"""Decode owned TSF report TLV bytes under explicit public reference layouts.

Diagnostic file processing only, never acquisition or clock admission. The
reference layouts are not a certificate of the installed Windows firmware ABI.
Accept one 48- or 60-byte original TLV, including its four-byte header. Do not
feed a normalized/padded decoder object here. A file cannot attest wire origin
or live producer consistency. Source bytes must be stable while copying.
The event-wire form additionally preserves the original four-byte WMI header;
it does not include lower transport headers or establish request identity.
The htc-wire form preserves an eight-byte HTC header and optional opaque trailer,
under strict exact-length and caller-declared endpoint checks. It is not capture.
Exit 0 diagnostic decode, 1 rejected/unqualified input, 2 CLI misuse.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import struct
from typing import Any

LAYOUT_BYTES = {"reference-48": 48, "reference-60": 60}
ORIGINS = ("fixture", "captured-unqualified")
REPORT_EVENT = 0x5005
REPORT_TAG = 0x18B
MAX_HTC_BYTES = 8 + 64 + 255  # header + largest supported WMI event + trailer


@dataclass(frozen=True)
class ReportSnapshot:
    """Application-owned immutable bytes; no assertion about the live producer."""

    raw_tlv: bytes
    reference_layout: str
    declared_origin: str

    def __post_init__(self) -> None:
        if type(self.raw_tlv) is not bytes:
            raise ValueError("Snapshot requires immutable owned bytes")
        if type(self.reference_layout) is not str or self.reference_layout not in LAYOUT_BYTES:
            raise ValueError("Choose an explicit reference layout")
        if type(self.declared_origin) is not str or self.declared_origin not in ORIGINS:
            raise ValueError("Declare fixture or captured-unqualified provenance")
        if len(self.raw_tlv) != LAYOUT_BYTES[self.reference_layout]:
            raise ValueError("Length does not match the selected reference layout")
        header = struct.unpack_from("<I", self.raw_tlv)[0]
        if header >> 16 != REPORT_TAG or (header & 0xFFFF) != len(self.raw_tlv) - 4:
            raise ValueError("TLV tag or declared length mismatch; padding is not wire evidence")

    def diagnostic(self) -> dict[str, Any]:
        words = struct.unpack("<" + "I" * (len(self.raw_tlv) // 4), self.raw_tlv)

        def wide(index: int) -> str:
            return str(words[index] | (words[index + 1] << 32))

        modern = self.reference_layout == "reference-60"
        # In the older reference, MAC validity has its own word. The newer
        # reference repurposes that word as report type and shares TSF validity.
        tsf_valid = words[7]
        mac_valid = tsf_valid if modern else words[9]
        reference_view = dict(
            vdev_raw=words[1], tsf_raw=wide(2), qtimer_raw=wide(4),
            tsf_id_raw=words[6], tsf_id_valid_raw=tsf_valid, mac_id_raw=words[8],
            candidate_tsf_id=words[6] if tsf_valid == 1 else None,
            candidate_mac_id=words[8] if mac_valid == 1 else None,
            global_tsf_raw=wide(10),
        )
        if modern:
            reference_view.update(
                report_type_raw=words[9],
                candidate_report_class={0: "tsf", 1: "uplink-delay"}.get(words[9], "unknown"),
                tqm_raw=wide(12), use_tqm_timer_raw=words[14],
            )
        else:
            reference_view.update(mac_id_valid_raw=words[9], candidate_report_class="not-defined-by-this-layout")
        return dict(
            schema="wht/owned-tsf-report-diagnostic-v1",
            declared_origin=self.declared_origin, reference_layout=self.reference_layout,
            supplied_event_id=hex(REPORT_EVENT), received_bytes=len(self.raw_tlv),
            payload_sha256=hashlib.sha256(self.raw_tlv).hexdigest(),
            raw_tlv_hex=self.raw_tlv.hex(), present_word_offsets=list(range(4, len(self.raw_tlv), 4)),
            reference_view=reference_view,
            field_presence_scope="bytes in supplied TLV; caller-declared original-wire representation is not attested",
            word_validity_scope="public reference interpretation only; unknown flag encodings do not produce candidate clock IDs",
            counter_unit=None, meaningful_counter_bits=None, epoch=None,
            host_sampling_interval=None, firmware_schema_qualified=False,
            source_publication_qualified=False, response_association_qualified=False,
            simultaneous_sampling_qualified=False, hardware_qpc_qualified=False,
            live_clock_eligible=False,
        )


def decode_report(data: bytes | bytearray, *, event_id: int, reference_layout: str,
                  origin: str, representation: str) -> ReportSnapshot:
    if type(data) not in (bytes, bytearray) or len(data) > 60:
        raise ValueError("Require at most 60 owned input bytes")
    if type(event_id) is not int or event_id != REPORT_EVENT:
        raise ValueError("Require report event 0x5005, not command 0x5012")
    if type(representation) is not str or representation != "wire":
        raise ValueError("Normalized objects need original wire bytes and presence evidence")
    return ReportSnapshot(bytes(data), reference_layout, origin)


@dataclass(frozen=True)
class EventSnapshot:
    """Owned WMI header and TLV; no pointers or claims about a live copy boundary."""

    raw_event: bytes
    reference_layout: str
    declared_origin: str

    def __post_init__(self) -> None:
        if type(self.raw_event) is not bytes or not 4 <= len(self.raw_event) <= 64:
            raise ValueError("Require an immutable bounded original WMI event")
        header = struct.unpack_from("<I", self.raw_event)[0]
        decode_report(self.raw_event[4:], event_id=header & 0xFFFFFF,
                      reference_layout=self.reference_layout, origin=self.declared_origin,
                      representation="wire")

    def diagnostic(self) -> dict[str, Any]:
        header = struct.unpack_from("<I", self.raw_event)[0]
        result = decode_report(self.raw_event[4:], event_id=header & 0xFFFFFF,
                               reference_layout=self.reference_layout, origin=self.declared_origin,
                               representation="wire").diagnostic()
        result.update(
            schema="wht/owned-tsf-event-diagnostic-v1",
            raw_wmi_event_hex=self.raw_event.hex(), wmi_header_raw=hex(header),
            wmi_header_upper_byte_raw=header >> 24,
            event_sha256=hashlib.sha256(self.raw_event).hexdigest(),
            received_event_bytes=len(self.raw_event), original_payload_bytes=len(self.raw_event) - 4,
            envelope_scope="four-byte WMI header and one original TLV; excludes HTC/PCIe headers",
            event_identity_scope="selector extracted from supplied bytes; no request token, firmware epoch or attested producer",
            host_time_observations=None,
            transport_envelope_present=False, source_contiguity_qualified=False,
        )
        return result


def decode_event(data: bytes | bytearray, *, event_id: int, reference_layout: str,
                 origin: str, representation: str) -> EventSnapshot:
    if type(data) not in (bytes, bytearray) or not 4 <= len(data) <= 64:
        raise ValueError("Require 4 to 64 owned input bytes")
    if type(event_id) is not int or event_id != REPORT_EVENT:
        raise ValueError("Require report event 0x5005, not command 0x5012")
    if type(representation) is not str or representation != "event-wire":
        raise ValueError("Require the original WMI header plus TLV")
    # One snapshot before interpreting the header or its payload. This assumes
    # stable input during the call; it is not a concurrent kernel-copy primitive.
    return EventSnapshot(bytes(data), reference_layout, origin)


def _htc_bounds(raw: bytes, expected_endpoint: int) -> tuple[int, int]:
    if type(raw) is not bytes or not 8 <= len(raw) <= MAX_HTC_BYTES:
        raise ValueError("Require one immutable bounded HTC envelope")
    if type(expected_endpoint) is not int or not 1 <= expected_endpoint <= 8:
        raise ValueError("Declare a nonzero endpoint in 1..8; endpoint zero is a separate control path")
    if raw[0] != expected_endpoint:
        raise ValueError("HTC endpoint does not match the declared source")
    payload_length = struct.unpack_from("<H", raw, 2)[0]
    if len(raw) != 8 + payload_length:
        raise ValueError("Received bytes must exactly match the advertised HTC extent")
    trailer_length = raw[4] if raw[1] & 2 else 0
    if raw[1] & 2 and not 4 <= trailer_length <= payload_length:
        raise ValueError("Invalid HTC trailer extent")
    return payload_length, trailer_length


@dataclass(frozen=True)
class HtcEventSnapshot:
    """Complete supplied envelope, with endpoint attribution still unqualified."""

    raw_htc: bytes
    expected_endpoint: int
    reference_layout: str
    declared_origin: str

    def __post_init__(self) -> None:
        _, trailer = _htc_bounds(self.raw_htc, self.expected_endpoint)
        end = len(self.raw_htc) - trailer
        EventSnapshot(self.raw_htc[8:end], self.reference_layout, self.declared_origin)

    def diagnostic(self) -> dict[str, Any]:
        payload, trailer = _htc_bounds(self.raw_htc, self.expected_endpoint)
        end = len(self.raw_htc) - trailer
        result = EventSnapshot(self.raw_htc[8:end], self.reference_layout, self.declared_origin).diagnostic()
        result.update(
            schema="wht/owned-tsf-htc-diagnostic-v1",
            raw_htc_envelope_hex=self.raw_htc.hex(), raw_htc_header_hex=self.raw_htc[:8].hex(),
            htc_sha256=hashlib.sha256(self.raw_htc).hexdigest(),
            received_htc_bytes=len(self.raw_htc), advertised_htc_payload_bytes=payload,
            htc_flags_raw=self.raw_htc[1], htc_endpoint_raw=self.raw_htc[0],
            declared_expected_endpoint=self.expected_endpoint,
            htc_trailer_bytes=trailer, raw_htc_trailer_hex=self.raw_htc[end:].hex(),
            transport_envelope_present=True, endpoint_association_qualified=False,
            trailer_semantics_qualified=False, header_flags_semantics_qualified=False,
            envelope_scope="one supplied HTC envelope with exact advertised extent; WMI event and opaque trailer preserved separately",
        )
        return result


def decode_htc_event(data: bytes | bytearray, *, event_id: int, reference_layout: str,
                     origin: str, representation: str, expected_endpoint: int) -> HtcEventSnapshot:
    if type(data) not in (bytes, bytearray) or not 8 <= len(data) <= MAX_HTC_BYTES:
        raise ValueError("Require one bounded HTC envelope")
    if type(event_id) is not int or event_id != REPORT_EVENT:
        raise ValueError("Require report event 0x5005, not command 0x5012")
    if type(representation) is not str or representation != "htc-wire":
        raise ValueError("Require an original HTC envelope")
    return HtcEventSnapshot(bytes(data), expected_endpoint, reference_layout, origin)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--event-id", type=lambda value: int(value, 0), required=True)
    parser.add_argument("--reference-layout", choices=tuple(LAYOUT_BYTES), required=True)
    parser.add_argument("--origin", choices=ORIGINS, required=True)
    parser.add_argument("--representation", choices=("wire", "event-wire", "htc-wire", "normalized"), required=True)
    parser.add_argument("--expected-endpoint", type=int,
                        help="Required only for htc-wire; caller-declared source, not live attribution")
    parser.add_argument("--require-clock-input", action="store_true",
                        help="Always rejects this diagnostic-only decoder")
    args = parser.parse_args()
    if (args.representation == "htc-wire") != (args.expected_endpoint is not None):
        parser.error("--expected-endpoint is required only with --representation htc-wire")
    try:
        limit = {"wire": 60, "event-wire": 64, "htc-wire": MAX_HTC_BYTES, "normalized": 60}[args.representation]
        with args.input.open("rb") as stream:
            raw = stream.read(limit + 1)
        kwargs = dict(event_id=args.event_id, reference_layout=args.reference_layout,
                      origin=args.origin, representation=args.representation)
        if args.representation == "htc-wire":
            report = decode_htc_event(raw, expected_endpoint=args.expected_endpoint, **kwargs)
        else:
            decoder = decode_event if args.representation == "event-wire" else decode_report
            report = decoder(raw, **kwargs)
        if args.require_clock_input:
            raise ValueError("Clock input remains unqualified")
        print(json.dumps(report.diagnostic(), indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError) as error:
        parser.exit(1, f"TSF report rejected: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
