"""Offline exact-build management RX schema and selected handoff evidence.

No device access, capture, driver loading or state change. Offsets and hashes only.
Exit 0: inspected; 1: input/I/O rejected; 2: CLI misuse. Output must be new.
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
from research.memory_ring.inspect_timing_boundaries import decode_pair_load
from research.tsf.inspect_tsf_report_contract import word_load_offsets
from research.tsf.inspect_tsf_routes import scan_words
from research.tsf.qualcomm_protocol import validate_driver
from research.windows_timestamps.ndis_evidence import write_json_new

RANGES = (
    ('event_registration', 0x1A5B30, 0x1A5B48),
    ('event_control_dispatch', 0x168CE0, 0x169150),
    ('event_decoder_core', 0x1BA4E0, 0x1BA914),
    ('event_cleanup_entry', 0x1BAE60, 0x1BAEB8),
    ('event_cleanup_selector_root', 0x1BC1F8, 0x1BC218),
    ('management_cleanup_selector', 0x1BC5D8, 0x1BC5F8),
    ('management_cleanup_slots', 0x1BC6E4, 0x1BC7D0),
    ('event_cleanup_tail', 0x1BB564, 0x1BB588),
    ('event_history_time', 0x185A20, 0x185A30),
    ('management_handler', 0x1A8160, 0x1A8540),
    ('metadata_conversion', 0x1A6080, 0x1A6180),
    ('management_enqueue', 0x104230, 0x104418),
    ('management_dequeue', 0x103D70, 0x103FD0),
    ('port_receive', 0x101AC8, 0x1021B8),
    ('fallback_receive', 0x1021B8, 0x102378),
    ('fallback_port_handoff', 0x103468, 0x103680),
    ('callback_registration', 0xB8808, 0xB8824),
    ('callback_prefix', 0xB5DD0, 0xB6038),
    ('raw_frame_dump', 0x1A6028, 0x1A6080),
    ('station_bss_indication', 0x25780, 0x25A98),
    ('bss_entry_builder', 0x57830, 0x57B58),
    ('bss_list_serializer', 0x161A50, 0x161A78),
    ('rx_channel_lookup', 0x5D718, 0x5D998),
    ('cache_device_context_copy', 0xEA230, 0xEA268),
    ('cache_to_bss_arguments', 0x20BE8, 0x20C1C),
    ('beacon_parser', 0x94F10, 0x95C38),
    ('mbssid_parser', 0x9E818, 0x9EFA8),
    ('mbssid_profile_parser', 0x9E378, 0x9E4E8),
    ('mbssid_profile_handoff', 0x987D8, 0x98940),
    ('frame_to_cache_prefix', 0x9CEA8, 0x9CF24),
    ('cache_ingress', 0xEC1D0, 0xEC628),
    ('cache_update', 0xE9A00, 0xEB0A8),
    ('cache_update_bridge', 0xE8110, 0xE8600),
)


def decode_history_exclusion(data: bytes, base_rva: int) -> dict[str, Any]:
    """Decode the selected four-instruction history filter, not arbitrary code.

    MOVZ W8,event; CMP X9,0; CCMP W19,W8,4,NE; B.EQ target.
    X9 is the history pointer and W19 the event in the manually traced caller.
    A null pointer or the matching event sets Z and takes the bypass branch.
    Caller context, executable reachability and all other paths remain manual.
    """
    if (type(data) is not bytes or len(data) != 16 or type(base_rva) is not int
            or not 0 <= base_rva <= 0xfffffff0 or base_rva % 4):
        raise ValueError('Expected four aligned instructions and a 32-bit RVA')
    move, compare, conditional_compare, branch = struct.unpack('<4I', data)
    if (move & 0xffe0001f != 0x52800008 or compare != 0xf100013f
            or conditional_compare != 0x7a481264 or branch & 0xff00001f != 0x54000000):
        raise ValueError('Unsupported history-filter instructions')
    immediate = (branch >> 5) & 0x7ffff
    if immediate & 0x40000:
        immediate -= 0x80000
    target = base_rva + 12 + immediate * 4
    if not 0 <= target <= 0xffffffff:
        raise ValueError('History branch target outside 32-bit RVA space')
    return dict(excluded_event_id=(move >> 5) & 0xffff, bypass_target_rva=hex(target))


def inspect_image(data: bytes) -> dict[str, Any]:
    validate_driver(data)
    pe = pefile.PE(data=data)
    try:
        layout = find_event_layout(pe.get_data(TABLE_RVA, TABLE_BYTES), 0x7001)
        header = layout['entries'][0]
        pairs = [decode_pair_load(struct.unpack('<I', pe.get_data(rva, 4))[0])
                 for rva in (0x1A8374, 0x1A83A0)]
        if any(pair['base'] != 19 for pair in pairs):
            raise ValueError('Unexpected header base register')
        # X22 holds the decoded wrapper here. W22 overwrites it at 0x1a8364.
        # Inventory only unsigned-immediate LDR X; manual review covers aliases.
        wrapper_bytes = pe.get_data(0x1A81D0, 0x1A8364 - 0x1A81D0)
        pointer_offsets = sorted({((word >> 10) & 0xFFF) * 8
                                  for (word,) in struct.iter_unpack('<I', wrapper_bytes)
                                  if word & 0xFFC00000 == 0xF9400000 and (word >> 5) & 31 == 22})
        # Exact-build generated serializer table, not a live firmware layout.
        field_va, count, container_bytes = struct.unpack('<QHH', pe.get_data(0x3084E0, 12))
        field_rva = field_va - pe.OPTIONAL_HEADER.ImageBase
        if count != 8 or container_bytes != 0x90 or field_rva != 0x3083C0:
            raise ValueError('Unexpected BSS container schema')
        fields = []
        for index in range(count):
            entry_rva = field_rva + index * 24
            tag, offset, count_code, optional_code = struct.unpack('<4H', pe.get_data(entry_rva + 16, 8))
            fields.append(dict(tag=tag, offset=offset, count_code=count_code, optional_code=optional_code))
        branches, ranges = [], []
        for name, start, end in RANGES:
            raw = pe.get_data(start, end - start)
            if len(raw) != end - start:
                raise ValueError('Truncated code range')
            ranges.append(dict(name=name, start_rva=hex(start), end_rva_exclusive=hex(end),
                               sha256=hashlib.sha256(raw).hexdigest()))
            branches.extend(scan_words(raw, start, {0x16A078, 0x15A3A4, 0x1A6080,
                                                     0x104230, 0x101AC8, 0x1021B8,
                                                     0x103468, 0x9CEA8, 0x99520,
                                                     0x1A6028, 0x1A49B0, 0x25780, 0x57830,
                                                     0x161A50, 0x13C430, 0x1A17D0,
                                                     0x94F10, 0x9E378, 0x987D8,
                                                     0xEC1D0, 0xE8110, 0xE9A00,
                                                     0x1BA4E0, 0x1BAE60, 0x185A20,
                                                     0x7740, 0x1BB564})['direct_branches'])
        cache_time_import = history_time_import = None
        for entry in pe.DIRECTORY_ENTRY_IMPORT:
            for item in entry.imports:
                if item.address - pe.OPTIONAL_HEADER.ImageBase == 0x2ED120 and item.name:
                    cache_time_import = item.name.decode('ascii')
                if item.address - pe.OPTIONAL_HEADER.ImageBase == 0x2ED3C0 and item.name:
                    history_time_import = item.name.decode('ascii')
        return dict(schema='qualcomm-management-rx-static/v1',
                    driver_sha256=hashlib.sha256(data).hexdigest(), event_id=0x7001,
                    schema_entry_rva=hex(TABLE_RVA + layout['table_offset']),
                    header_expected_bytes=header['element_size'], header_tag=header['tag'],
                    decoded_slots=len(layout['entries']),
                    schema_slots=layout['entries'],
                    selected_wrapper_pointer_load_offsets=pointer_offsets,
                    selected_wrapper_word_load_offsets=word_load_offsets(wrapper_bytes, 22),
                    bss_container_schema=dict(table_rva='0x3084e0', fields_rva=hex(field_rva),
                                              container_bytes=container_bytes, fields=fields),
                    cache_time_import=cache_time_import,
                    event_lifetime=dict(
                        cleanup_allocation_flag_load_offsets=word_load_offsets(
                            pe.get_data(0x1BC6E4, 0x1BC7D0 - 0x1BC6E4), 19),
                        history_filter=decode_history_exclusion(pe.get_data(0x168F88, 16), 0x168F88),
                        history_time_import=history_time_import,
                        live_ownership_qualified=False, hardware_qpc_bracket_established=False),
                    host_cache_tick_literal=hex(struct.unpack('<Q', pe.get_data(0xEC620, 8))[0]),
                    selected_unsigned_word_load_offsets=word_load_offsets(
                        pe.get_data(0x1A81F8, 0x200), 19),
                    selected_pair_load_offsets=[pair['offsets'] for pair in pairs],
                    ranges=ranges, direct_branches=branches,
                    coverage='selected load forms only; byte loads and pointer dataflow require manual inspection',
                    firmware_layout_qualified=False, hardware_pair_export_qualified=False,
                    live_capture_performed=False)
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
