"""Inspect an exact owned driver file for packet-log copy/return connections.

No live memory, device access, requests, logging changes or firmware execution.
Receipts contain offsets, selectors and hashes, not driver bytes or device IDs.
Exit 0: offline inspection; 1: rejected input/I/O; 2: CLI misuse. New output only.
These internal selectors do not specify a safe or supported userspace request.
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

RANGES = (
    ('ihv_request', 0x12E4F0, 0x12E8E8),
    ('nic_specific_dispatch', 0x11CDE8, 0x11D4C0),
    ('inner_query_dispatch', 0x39528, 0x39C0C),
    ('combined_result_envelope', 0x37E00, 0x37EB8),
    ('combined_hardware_copy', 0xCDD8, 0xCE9C),
    ('hardware_header_copy', 0xCFA0, 0xCFE4),
    ('hardware_body_copy', 0xCF58, 0xCF9C),
    ('operations_table_install', 0x188168, 0x188184),
    ('packetlog_thunks', 0x18AE00, 0x18AE44),
    ('packetlog_header_reader', 0x1EBE50, 0x1EBEDC),
    ('packetlog_body_reader', 0x1EBDC0, 0x1EBE4C),
    ('packetlog_copy', 0x1EBBF8, 0x1EBDBC),
    ('packetlog_context_lookup', 0x2171E0, 0x21726C),
    ('packetlog_reservation', 0x220AC0, 0x220DDC),
    ('offload_payload_writer', 0x220E90, 0x220F98),
    ('lite_payload_writer', 0x220F98, 0x22110C),
    ('packetlog_event_dispatch', 0x217270, 0x217400),
    ('packetlog_rx_packet_copy', 0x221320, 0x221428),
    ('packetlog_rx_info_copy', 0x221428, 0x221550),
    ('packetlog_stop_reset', 0x1EC0E0, 0x1EC1CC),
    ('packetlog_storage_release', 0x1EBEE0, 0x1EBFAC),
    ('sar_service', 0x12A4C0, 0x12A9AC),
    ('antenna_service', 0x12A9B0, 0x12ACE4),
    ('packetlog_callback_init', 0x216CD0, 0x216DFC),
    ('packetlog_subscribe', 0x217530, 0x217650),
    ('datapath_subscription_bridge', 0x217150, 0x2171E0),
    ('datapath_event_dispatch', 0x1FB730, 0x1FB878),
    ('datapath_event_subscribe', 0x1FB880, 0x1FBA08),
    ('htt_message_receive', 0x1FC970, 0x1FCF48),
    ('htt_receive_registration', 0x1FEFC8, 0x1FF08C),
    ('datapath_operations_install', 0x1CB8C4, 0x1CB8D0),
    ('mlo_offset_candidate', 0x1FD7E0, 0x1FDA24),
)


def inspect_image(data: bytes) -> dict[str, Any]:
    """Extract exact-file evidence; manual review supplies dataflow semantics."""
    validate_driver(data)
    pe = pefile.PE(data=data)
    try:
        def word(rva: int) -> int:
            raw = pe.get_data(rva, 4)
            if len(raw) != 4:
                raise ValueError('Truncated selector')
            return struct.unpack('<I', raw)[0]

        targets = {0x11CDE8, 0x1619B0, 0x13A890, 0x1618C0, 0x37E00,
                   0xCDD8, 0xD020, 0xCF58, 0xCFA0, 0x1EBE50, 0x1EBDC0,
                   0x1EBBF8, 0x2171E0, 0x220AC0, 0x220B18, 0x1A17D0,
                   0x15A3A4, 0x1EBEE0, 0x96E0, 0x220E90, 0x220F98,
                   0x221320, 0x221428,
                   0x151750, 0x151820, 0x151A38, 0x1A3738, 0x1A3B30,
                   0x217150, 0x1FB730, 0x1C4FE8, 0x1B6E08, 0x1FD7E0,
                   0x6AE0}
        ranges, branches = [], []
        for name, start, end in RANGES:
            raw = pe.get_data(start, end - start)
            if len(raw) != end - start:
                raise ValueError('Truncated inspection range')
            ranges.append(dict(name=name, start_rva=hex(start), end_rva_exclusive=hex(end),
                               sha256=hashlib.sha256(raw).hexdigest()))
            branches.extend(scan_words(raw, start, targets)['direct_branches'])
        slots = []
        for offset in (0x270, 0x278):
            entry = 0x341840 + offset
            raw = pe.get_data(entry, 8)
            if len(raw) != 8:
                raise ValueError('Truncated operations table')
            target = struct.unpack('<Q', raw)[0] - pe.OPTIONAL_HEADER.ImageBase
            slots.append(dict(offset=hex(offset), entry_rva=hex(entry), target_rva=hex(target)))
        def pointer_rva(rva: int) -> int:
            raw = pe.get_data(rva, 8)
            if len(raw) != 8:
                raise ValueError('Truncated producer operations pointer')
            target = struct.unpack('<Q', raw)[0] - pe.OPTIONAL_HEADER.ImageBase
            if not 0 <= target < pe.OPTIONAL_HEADER.SizeOfImage:
                raise ValueError('Producer operations pointer outside image')
            return target

        common_ops = pointer_rva(0x392AC8)
        subscription = pointer_rva(common_ops + 0x88)
        return dict(
            schema='qualcomm-packetlog-return-static/v1',
            driver_sha256=hashlib.sha256(data).hexdigest(),
            selectors=dict(outer_start=hex(word(0x11D498)), outer_combined_copy=hex(word(0x11D49C)),
                           inner_header=hex(word(0x39BE0)), inner_body=hex(word(0x39BE4))),
            operations_table=dict(base_rva='0x341840', slots=slots),
            producer_tables=dict(root_rva='0x392ac0', common_ops_pointer_rva='0x392ac8',
                                 common_ops_rva=hex(common_ops), subscription_slot='0x88',
                                 subscription_target_rva=hex(subscription)),
            ranges=ranges, direct_branches=branches,
            coverage='selected exact-file ranges and immediate branches; indirect binding and semantics need manual review',
            live_request_sent=False, snapshot_safety_qualified=False,
            complete_management_event_export_qualified=False, clock_input_eligible=False,
            runtime_subscription_observed=False, firmware_packetlog_schema_qualified=False,
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
        parser.exit(1, f'Inspection rejected: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())
