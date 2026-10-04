"""Offline exact-build TSF schema and selected handler field-coverage inventory.

Read an owned driver file only. No device access, requests or quarantine writes.
Emits offsets/hashes, never driver bytes. Exit 0: inspection; 1: rejected input;
2: CLI misuse. A completed inspection does not qualify firmware semantics.
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

from research.ftm.inspect_ftm_ingress import find_event_layout, TABLE_RVA, TABLE_BYTES
from research.tsf.qualcomm_protocol import validate_driver
from research.windows_timestamps.ndis_evidence import write_json_new

RANGES = (
    ('command_allocator', 0x168BD8, 0x168C50),
    ('command_builder', 0x1955E8, 0x1956E8),
    ('report_handler', 0x216B00, 0x216CCC),
    ('report_word_copy', 0x216B9C, 0x216BD4),
)


def word_load_offsets(data: bytes, base_register: int) -> list[int]:
    """Decode only LDR Wt,[Xn,#unsigned_immediate], not general ARM64 dataflow."""
    if type(data) is not bytes or len(data) % 4 or type(base_register) is not int or not 0 <= base_register <= 31:
        raise ValueError('Expected word-aligned bytes and register number')
    return sorted({((word >> 10) & 0xFFF) * 4
                   for (word,) in struct.iter_unpack('<I', data)
                   if word & 0xFFC00000 == 0xB9400000 and (word >> 5) & 31 == base_register})


def inspect_image(data: bytes) -> dict[str, Any]:
    validate_driver(data)
    pe = pefile.PE(data=data)
    try:
        layout = find_event_layout(pe.get_data(TABLE_RVA, TABLE_BYTES), 0x5005)
        if len(layout['entries']) != 1:
            raise ValueError('Unexpected TSF schema')
        entry = layout['entries'][0]
        loads = word_load_offsets(pe.get_data(0x216B9C, 0x38), 9)
        header = struct.unpack('<I', pe.get_data(0x1956E4, 4))[0]
        ranges = [dict(name=name, start_rva=hex(start), end_rva_exclusive=hex(end),
                       sha256=hashlib.sha256(pe.get_data(start, end - start)).hexdigest())
                  for name, start, end in RANGES]
        return dict(schema='qualcomm-tsf-report-contract-static/v1',
                    driver_sha256=hashlib.sha256(data).hexdigest(), ranges=ranges,
                    schema_entry_rva=hex(TABLE_RVA + layout['table_offset']),
                    report_tag=entry['tag'], report_expected_bytes=entry['element_size'],
                    command_tag=header >> 16, command_expected_bytes=(header & 0xFFFF) + 4,
                    selected_report_word_offsets=loads,
                    unconsumed_payload_word_offsets=sorted(set(range(4, entry['element_size'], 4)) - set(loads)),
                    coverage='selected word-copy block; manually inspect the full handler',
                    runtime_wire_length_verified=False, response_association_qualified=False,
                    fresh_sampling_qualified=False, live_request_sent=False)
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
        parser.exit(1, f'Inspection rejected: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())
