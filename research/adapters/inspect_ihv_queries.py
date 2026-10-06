"""Exact-build, file-only IHV query-route evidence; never send these selectors.

Reads <=16 MiB from an owned SYS file, rejects other hashes, and writes a new
receipt. Roles below are manual Ghidra interpretations, not automatic flow proof.
No vendor code loading, device handles or kernel-memory access. Exit 0 receipt,
1 rejected input/I/O, 2 CLI usage. Existing output is never overwritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
from typing import Any
import uuid

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pefile
from research.tsf.inspect_tsf_routes import scan_words
from research.tsf.qualcomm_protocol import validate_driver
from research.windows_timestamps.ndis_evidence import write_json_new

MAX_BYTES = 16 * 1024 * 1024
RANGES = (
    ("outer_extension", 0x11CDE8, 0x11D48C),
    ("port_forwarder", 0x11CA70, 0x11CDD8),
    ("query_dispatch", 0x39528, 0x39B24),
    ("set_dispatch", 0x3A5B8, 0x3A774),
    ("method_dispatch", 0x39E38, 0x39ED4),
    ("scan_start", 0x2D6F0, 0x2DA5C),
    ("bss_query", 0x38958, 0x389F8),
    ("bss_port_dispatch", 0x54EE0, 0x55014),
    ("channel_control", 0x3A950, 0x3A9F0),
    ("gpio_wrapper", 0xCB48, 0xCB68),
    ("gpio_command", 0x183058, 0x18310C),
    ("record_region_clear", 0xCBE8, 0xCC18),
    ("device_information", 0x2F180, 0x2F208),
    ("bus_interface_init", 0x437AA8, 0x437B94),
)
# These are inner selector literals. They are NOT top-level IOCTL numbers or a
# live allowlist. Outer cases can intercept a selector before query dispatch.
SELECTORS = (
    (0x39BA0, 0xFF01010E, "channel-list construction"),
    (0x39BCC, 0xFF000080, "scan initiation"),
    (0x39BD0, 0xFF000081, "BSS enumeration wrapper"),
    (0x39BD4, 0xFF000084, "specific-channel control"),
    (0x39BD8, 0xFF500010, "packet-log stop path; see separate lifecycle report"),
    (0x39BDC, 0xFF210004, "sum of two counter helpers"),
    (0x39BE0, 0xFF500001, "inner packet-log header; outer path starts logging"),
    (0x39BE4, 0xFF500002, "inner packet-log body; outer combined return"),
    (0x39BE8, 0xFF500003, "packet-log configuration helper"),
    (0x39BEC, 0xFF50000B, "PCI configuration-space read at offset zero"),
    (0x39BF0, 0xFF500014, "write one to host context +0x36240"),
    (0x39BF4, 0xFF500015, "write zero to host context +0x36240"),
    (0x39BF8, 0xFFB00004, "GPIO-output command submission"),
    (0x39BFC, 0xFFB00005, "one-byte status through indirect hardware operation"),
    (0x39C00, 0xFFB00009, "clear portions of 100 host records and a byte field"),
)


def inspect_image(data: bytes) -> dict[str, Any]:
    if type(data) is not bytes or len(data) > MAX_BYTES:
        raise ValueError("Require immutable driver bytes within 16 MiB")
    validate_driver(data)
    pe = pefile.PE(data=data)
    try:
        def require_word(rva: int, value: int) -> None:
            if pe.get_data(rva, 4) != struct.pack("<I", value):
                raise ValueError(f"Unexpected selected word at {rva:#x}")

        selectors = []
        for rva, value, role in SELECTORS:
            require_word(rva, value)
            selectors.append(dict(literal_rva=hex(rva), selector=hex(value), manual_role=role))
        for rva, value in ((0x183110, 0x009A0008), (0x183114, 0x1E002),
                           (0xCB4C, 0x7100003F), (0xCB50, 0x1A9F17E2),
                           (0xCB54, 0x52800021), (0x2F1DC, 0x52800001),
                           (0x2F1E0, 0xF941B500), (0x2F1E4, 0xF941CD08),
                           (0x39ED8, 0x0D01035C), (0x11D494, 0x0D01035C)):
            require_word(rva, value)
        bus_guid = str(uuid.UUID(bytes_le=pe.get_data(0x2EF790, 16)))
        if bus_guid != "496b8280-6f25-11d0-beaf-08002be2092f":
            raise ValueError("Unexpected bus interface GUID")
        ranges, calls = [], []
        targets = {0x39528, 0x39E38, 0x3A5B8, 0x11CA70, 0x11CDE8, 0x2D6F0,
                   0x38958, 0x54EE0, 0x3A950, 0xCB48, 0x183058, 0x169678,
                   0xCBE8, 0x2F180, 0x39C10, 0xD1C0}
        for name, start, end in RANGES:
            raw = pe.get_data(start, end - start)
            if len(raw) != end - start:
                raise ValueError("Truncated evidence range")
            ranges.append(dict(name=name, start_rva=hex(start), end_rva_exclusive=hex(end),
                               sha256=hashlib.sha256(raw).hexdigest()))
            calls.extend(scan_words(raw, start, targets)["direct_branches"])
        return dict(schema="wht/ihv-query-routes-static-v1",
            driver_sha256=hashlib.sha256(data).hexdigest(), selectors=selectors, ranges=ranges,
            selected_direct_branches=calls,
            dispatch=dict(query="0x39528", set="0x3a5b8", method="0x39e38",
                forwarder="0x11ca70", outer="0x11cde8", method_reentry_selector="0xd01035c",
                outer_rejects_same_reentry_selector=True),
            gpio=dict(command_id="0x1e002", tlv_tag="0x9a", command_bytes=12,
                gpio_number=1, output_argument="1 when input word is zero, otherwise 0",
                hardware_effect_observed=False),
            bus_read=dict(guid=bus_guid, interface_base="0x360", context_offset="0x368",
                get_bus_data_offset="0x398", data_type=0, requested_offset=0,
                expected_returned_bytes=4, source="PCI configuration space, not radio MMIO"),
            manual_scope="selected exact-build routes; role labels require the manual trace, not just literal matches",
            live_request_sent=False, complete_call_coverage=False, read_only_profile_qualified=False,
            complete_timing_event_export_qualified=False, hardware_qpc_qualified=False)
    finally:
        pe.close()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--driver", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    try:
        if a.output.exists():
            raise ValueError("Output already exists")
        with a.driver.open("rb") as stream:
            data = stream.read(MAX_BYTES + 1)
        result = inspect_image(data)
        write_json_new(a.output, result)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, pefile.PEFormatError) as error:
        p.exit(1, f"IHV query inspection rejected: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
