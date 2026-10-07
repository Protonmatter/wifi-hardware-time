"""Offline exact-build FTM event ingress and lifetime evidence.

Read an owned SYS file, never a running driver. Emit schema metadata, range hashes
and selected branch offsets; no binary payloads or input paths. This does not
acquire FTM data or qualify an application export. Exit 0: inspected; 1: input/I/O
rejected; 2: CLI usage error. Output files are created exclusively.
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

EVENT_ID = 0x27004
TABLE_RVA = 0x38FAE0
TABLE_BYTES = 0x404 * 4
# Exclusive end offsets. Manual analysis supplies the behavioral interpretation.
RANGES = (
    ('ftm_registration', 0x145E90, 0x145EC8),
    ('event_registry', 0x16A030, 0x16A158),
    ('control_rx', 0x168CE0, 0x169150),
    ('event_decoder_core', 0x1BA4E0, 0x1BA914),
    ('event_schema_lookup', 0x1BDFE0, 0x1BE148),
    ('event_cleanup_dispatch', 0x1BAE60, 0x1BDF80),
    ('ftm_handler', 0x1477F0, 0x147AC8),
    ('history_time_thunk', 0x185A20, 0x185A30),
)


def find_event_layout(data: bytes, event_id: int) -> dict[str, Any]:
    """Decode the bounded on-disk schema table, not a live firmware response.

    Entry headers contain a 24-bit event selector and an 8-bit descriptor count.
    count_code is an encoded schema field, not an observed measurement count.
    Validate the whole supplied table, including entries after the selected one.
    """
    if type(data) is not bytes or not data or len(data) % 4 or len(data) > TABLE_BYTES:
        raise ValueError('Expected a nonempty bounded word-aligned schema table')
    if type(event_id) is not int or not 0 <= event_id <= 0xFFFFFF:
        raise ValueError('Expected a 24-bit event selector')
    offset = 0
    match = None
    while offset < len(data):
        header = struct.unpack_from('<I', data, offset)[0]
        count = header >> 24
        end = offset + 4 * (count + 1)
        if end > len(data):
            raise ValueError('Truncated schema entry')
        if header & 0xFFFFFF == event_id:
            if match is not None:
                raise ValueError('Ambiguous duplicate event selector')
            entries = []
            for position in range(offset + 4, end, 4):
                word = struct.unpack_from('<I', data, position)[0]
                entries.append(dict(tag=word & 0xFFF, element_size=(word >> 12) & 0x1FF,
                                    variable_flag=(word >> 30) & 1, count_code=(word >> 21) & 0x1FF))
            match = dict(table_offset=offset, entries=entries)
        offset = end
    if match is None:
        raise ValueError('Event selector absent from schema table')
    return match


def inspect_image(data: bytes) -> dict[str, Any]:
    validate_driver(data)
    pe = pefile.PE(data=data)
    try:
        table = pe.get_data(TABLE_RVA, TABLE_BYTES)
        if len(table) != TABLE_BYTES:
            raise ValueError('Truncated schema table')
        layout = find_event_layout(table, EVENT_ID)
        layout['entry_rva'] = hex(TABLE_RVA + layout['table_offset'])
        ranges = []
        branches = []
        targets = {0x16A078, 0x16A030, 0x1BA4E0, 0x1BAE60, 0x1BDFE0,
                   0x185A20, 0x146EF0, 0x7740}
        for name, start, end in RANGES:
            raw = pe.get_data(start, end - start)
            if len(raw) != end - start:
                raise ValueError(f'Truncated range: {name}')
            ranges.append(dict(name=name, start_rva=hex(start), end_rva_exclusive=hex(end),
                               sha256=hashlib.sha256(raw).hexdigest()))
            branches.extend(scan_words(raw, start, targets)['direct_branches'])
        history_import = None
        for entry in pe.DIRECTORY_ENTRY_IMPORT:
            for item in entry.imports:
                if item.address - pe.OPTIONAL_HEADER.ImageBase == 0x2ED3C0 and item.name:
                    history_import = item.name.decode('ascii')
        return dict(schema='qualcomm-ftm-ingress-static/v1',
                    driver_sha256=hashlib.sha256(data).hexdigest(),
                    event_id=EVENT_ID, event_layout=layout,
                    cleanup_selector=struct.unpack('<I', pe.get_data(0x1BDD58, 4))[0],
                    history_time_import=history_import, ranges=ranges, direct_branches=branches,
                    complete_call_coverage=False, live_acquisition=False,
                    application_export_established=False)
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
