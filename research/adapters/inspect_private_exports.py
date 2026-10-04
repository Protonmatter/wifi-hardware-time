"""Inspect selected private return paths in an owned, exact-build SYS file.

No device handles, firmware commands, traces or kernel-memory reads. The receipt
contains offsets, hashes and selected static observations, not proprietary code
or endpoint paths. It does not qualify either route for live use. Exit codes:
0 inspection completed; 1 rejected input/I/O; 2 invalid CLI arguments.
"""
from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import argparse
import hashlib
import json
import struct
from typing import Any

import pefile

from research.tsf.inspect_tsf_routes import scan_words
from research.tsf.qualcomm_protocol import validate_driver
from research.windows_timestamps.ndis_evidence import write_json_new

# End offsets are exclusive. These are manually inspected ranges, not a claim
# that all callers, indirect dispatch targets or device services are covered.
RANGES = (
    ('getter_dispatch_entry', 0x124440, 0x124484),
    ('getter_dispatch_rx_stats', 0x1248CC, 0x124914),
    ('rx_stats_formatter', 0x127E88, 0x12812C),
    ('rx_stats_refresh_helper', 0x308F0, 0x30CB8),
    ('stats_request_helper', 0x30220, 0x303F8),
    ('text_result_append', 0x124110, 0x124220),
    ('test_service_handler', 0x12A2A0, 0x12A4B8),
    ('device_service_completion', 0x13A890, 0x13AB28),
    ('interface_service_handler', 0x12ACF0, 0x12AEF0),
    ('interface_service_dispatch', 0x51960, 0x51A50),
    ('interface_mac_getter', 0x505B0, 0x50758),
    ('interface_association_getter', 0x502C0, 0x505B0),
    ('ihv_request_handler', 0x12E4F0, 0x12E8E8),
    ('nic_specific_dispatch', 0x11CDE8, 0x11D4C0),
)


def inspect_image(data: bytes) -> dict[str, Any]:
    """Bind manually traced candidates to the qualified file before extraction."""
    validate_driver(data)
    pe = pefile.PE(data=data)
    try:
        record = pe.get_data(0x33E038, 28)
        fields = struct.unpack_from('<IIBB', record)
        if fields != (0, 250, 1, 0) or record[10:].split(b'\0')[0] != b'get_rx_stats':
            raise ValueError('Unexpected RX statistics command record')
        ranges = []
        calls = []
        targets = {0x127E88, 0x308F0, 0x30220, 0x303F8, 0x124110, 0x1618C0, 0x13A890,
                   0x51960, 0x502C0, 0x505B0, 0x50758, 0x512B0, 0x164BD8, 0x7740,
                   0x11CDE8, 0x1619B0, 0x11CA70, 0x39E38, 0x3A5B8, 0x39528}
        for name, start, end in RANGES:
            raw = pe.get_data(start, end - start)
            if len(raw) != end - start:
                raise ValueError(f'Truncated inspection range: {name}')
            ranges.append(dict(name=name, start_rva=hex(start), end_rva_exclusive=hex(end),
                               sha256=hashlib.sha256(raw).hexdigest()))
            calls.extend(scan_words(raw, start, targets)['direct_branches'])
        return_branches, sections = [], []
        for section in pe.sections:
            if not section.Characteristics & 0x20000000:
                continue
            raw = section.get_data()[:section.Misc_VirtualSize]
            length = len(raw) - len(raw) % 4
            return_branches.extend(scan_words(raw[:length], section.VirtualAddress,
                                              {0x13A890, 0x1618C0})['direct_branches'])
            sections.append(dict(rva=hex(section.VirtualAddress), aligned_bytes_scanned=length))
        imports = {}
        for entry in pe.DIRECTORY_ENTRY_IMPORT:
            for item in entry.imports:
                rva = item.address - pe.OPTIONAL_HEADER.ImageBase
                if rva in (0x2ED0F8, 0x2ED120, 0x2ED190):
                    imports[hex(rva)] = item.name.decode('ascii') if item.name else f'ordinal:{item.ordinal}'
        return dict(
            schema='qualcomm-private-export-static/v1',
            driver_sha256=hashlib.sha256(data).hexdigest(),
            ranges=ranges,
            get_rx_stats=dict(record_rva='0x33e038', selector=fields[1],
                              dispatcher_rva='0x124440', formatter_rva='0x127e88',
                              format_string_rva='0x29a158'),
            test_service=dict(handler_rva='0x12a2a0', payload_literal_rva='0x12a4b0',
                              fixed_eight_byte_payload_matches=pe.get_data(0x12A4B0, 8) == bytes(range(1, 9))),
            selected_direct_calls=calls, selected_imports=imports,
            return_inventory=dict(executable_sections=sections, direct_branches=return_branches,
                                  coverage='aligned B/BL candidates only; code context and indirect routes require review'),
            complete_call_coverage=False, live_request_sent=False,
            complete_timestamp_export_qualified=False,
        )
    finally:
        pe.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--driver', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise ValueError('Output already exists')
        with args.driver.open('rb') as stream:
            data = stream.read(16 * 1024 * 1024 + 1)
        if len(data) > 16 * 1024 * 1024:
            raise ValueError('Driver exceeds inspection bound')
        result = inspect_image(data)
        write_json_new(args.output, result)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, pefile.PEFormatError) as error:
        parser.exit(1, f'Static inspection rejected: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())
