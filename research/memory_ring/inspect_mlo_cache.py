"""Offline exact-build MLO cache and native symbol identity inventory.

Reads a locally owned SYS as data. No device, debugger attachment or network.
Reports selected ranges, immediate-constant candidates and RSDS identity; it
does not prove exhaustive reader coverage, firmware semantics or safe export.
Output must be new. Exit 0: inspected; 1: rejected input/I/O; 2: CLI misuse.
"""
from __future__ import annotations

import sys
from pathlib import Path, PureWindowsPath

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import argparse
import hashlib
import json
import struct
from typing import Any
import uuid

import pefile

from research.tsf.qualcomm_protocol import validate_driver
from research.tsf.inspect_tsf_routes import scan_words
from research.windows_timestamps.ndis_evidence import write_json_new

RANGES = (
    ('mlo_offset_handler', 0x1FD7E0, 0x1FDA24),
    ('htt_mlo_dispatch', 0x1FCD48, 0x1FCD54),
    ('pdev_allocate_and_zero', 0x1C31D0, 0x1C31FC),
    ('internal_event_callback', 0x1FB804, 0x1FB830),
    ('pdev_deinit', 0x1C6428, 0x1C6684),
    ('pdev_detach', 0x1C6688, 0x1C6774),
)
VALUES = frozenset({*range(0x5FF0, 0x6010), 0x6010, 0x10C})


def parse_rsds(data: bytes) -> dict[str, Any]:
    """Return native symbol identity without exposing the embedded build path."""
    if type(data) is not bytes or not 25 <= len(data) <= 4096 or data[:4] != b'RSDS':
        raise ValueError('Expected bounded native RSDS record')
    name_bytes, terminator, _ = data[24:].partition(b'\0')
    if not terminator or not name_bytes:
        raise ValueError('Missing terminated PDB filename')
    name = PureWindowsPath(name_bytes.decode('utf-8')).name
    if not name.lower().endswith('.pdb') or any(ord(c) < 32 for c in name):
        raise ValueError('Unexpected PDB filename')
    guid = uuid.UUID(bytes_le=data[4:20])
    age = struct.unpack_from('<I', data, 20)[0]
    return dict(format='RSDS', pdb_name=name, guid=str(guid), age=age,
                symbol_store_key=guid.hex.upper() + format(age, 'x').upper())


def scan_constants(data: bytes, base_rva: int) -> list[dict[str, Any]]:
    """Find selected MOVZ, ADD-immediate and integer unsigned LD/ST offsets.

    This is candidate generation, not dataflow or a disassembler. Executable
    sections can include literal data. MOVK, register arithmetic, aliases and
    whole-object copies are not exhaustively modeled.
    """
    if type(data) is not bytes or len(data) % 4 or type(base_rva) is not int or not 0 <= base_rva <= 0xFFFFFFFF or base_rva % 4:
        raise ValueError('Expected aligned bytes and nonnegative 32-bit RVA')
    rows = []
    for offset in range(0, len(data), 4):
        word = struct.unpack_from('<I', data, offset)[0]
        value, kind = None, None
        if word & 0x7F800000 == 0x52800000 and (word >> 21) & 3 == 0:
            value, kind = (word >> 5) & 0xFFFF, 'movz_immediate'
        elif word & 0x7F000000 == 0x11000000:
            value = ((word >> 10) & 0xFFF) << (12 if word & (1 << 22) else 0)
            kind = 'add_immediate'
        elif word & 0x3B000000 == 0x39000000 and not word & 0x04000000:
            value = ((word >> 10) & 0xFFF) << ((word >> 30) & 3)
            kind = 'integer_unsigned_memory_offset'
        if value in VALUES:
            rows.append(dict(rva=hex(base_rva + offset), value=hex(value), kind=kind))
    return rows


def inspect_image(data: bytes) -> dict[str, Any]:
    validate_driver(data)
    pe = pefile.PE(data=data)
    try:
        debug = []
        for entry in getattr(pe, 'DIRECTORY_ENTRY_DEBUG', []):
            if entry.struct.Type == 2:
                debug.append(parse_rsds(pe.get_data(entry.struct.AddressOfRawData,
                                                   entry.struct.SizeOfData)))
        if len(debug) != 1:
            raise ValueError('Expected one native symbol identity')
        candidates, ranges, branches = [], [], []
        for section in pe.sections:
            if section.Characteristics & 0x20000000:
                raw = section.get_data()[:section.Misc_VirtualSize]
                candidates.extend(scan_constants(raw[:len(raw) // 4 * 4], section.VirtualAddress))
        for name, start, end in RANGES:
            raw = pe.get_data(start, end - start)
            if len(raw) != end - start:
                raise ValueError('Truncated selected range')
            ranges.append(dict(name=name, start_rva=hex(start), end_rva_exclusive=hex(end),
                               sha256=hashlib.sha256(raw).hexdigest()))
            branches.extend(scan_words(raw, start, {0x1FD7E0, 0x1FB730, 0x7528, 0x1A3548,
                                                   0x70B0, 0x1FB6C0})['direct_branches'])
        image_base = pe.OPTIONAL_HEADER.ImageBase
        main_ops = struct.unpack('<Q', pe.get_data(0x392AC0, 8))[0] - image_base
        detach = struct.unpack('<Q', pe.get_data(main_ops + 0x38, 8))[0] - image_base
        deinit = struct.unpack('<Q', pe.get_data(main_ops + 0x40, 8))[0] - image_base
        return dict(schema='qualcomm-mlo-cache-static/v1', driver_sha256=hashlib.sha256(data).hexdigest(),
                    native_symbols=debug[0], ranges=ranges, direct_branches=branches,
                    lifecycle_ops=dict(main_table_rva=hex(main_ops), detach_wrapper_rva=hex(detach),
                                       deinit_wrapper_rva=hex(deinit)),
                    constant_candidates=candidates,
                    reader_coverage='selected immediate forms only; manual classification required',
                    independent_reader_proven=False, runtime_cache_observed=False,
                    timestamp_units_live_qualified=False, owned_export_qualified=False,
                    hardware_qpc_relation_qualified=False, clock_input_eligible=False)
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
