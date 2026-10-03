"""Exact-build on-disk timing boundaries, not callable addresses or live access.

Only decodes narrow ARM64 load forms and inventories direct branches. No device,
IOCTL, trace, register read, debugger or firmware operation. Output is exclusive.
Exit 0: inspection completed; 1: rejected input/I/O; 2: CLI usage error.
"""
from __future__ import annotations

import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import argparse
import hashlib
import json
import struct
from typing import Any

import pefile

from research.tsf.qualcomm_protocol import validate_driver
from research.windows_timestamps.ndis_evidence import write_json_new
from research.tsf.inspect_tsf_routes import scan_words

TARGETS = {
    0x8a88: 'recent_ring_span', 0x8d20: 'ring_copy',
    0x22e2a0: 'mhi_save_dump', 0x22e6b0: 'mhi_save_memory_log',
    0x230a50: 'host_memory_log_file', 0x2195e0: 'rx_descriptor_diagnostic',
    0x137ca8: 'device_service_notification', 0x146ef0: 'merged_ftm_parser',
}


def require_word(word: int) -> None:
    if type(word) is not int or not 0 <= word <= 0xffffffff:
        raise ValueError('Expected unsigned 32-bit instruction')


def decode_word_load(word: int) -> dict[str, Any]:
    """LDR Wt,[Xn,#unsigned_imm12*4] only, not an arbitrary ARM decoder."""
    require_word(word)
    if word & 0xffc00000 != 0xb9400000:
        raise ValueError('Expected unsigned-offset 32-bit LDR')
    return dict(base=(word >> 5) & 31, register=word & 31,
                offset=((word >> 10) & 0xfff) * 4, width=32)


def decode_pair_load(word: int) -> dict[str, Any]:
    """LDP Wt,Wt2,[Xn,#signed_imm7*4], without writeback."""
    require_word(word)
    if word & 0xffc00000 != 0x29400000:
        raise ValueError('Expected signed-offset 32-bit LDP without writeback')
    immediate = (word >> 15) & 127
    if immediate & 64:
        immediate -= 128
    return dict(base=(word >> 5) & 31, registers=[word & 31, (word >> 10) & 31],
                offsets=[immediate * 4, immediate * 4 + 4], width=32)


def inspect_boundaries(data: bytes) -> dict[str, Any]:
    validate_driver(data)
    pe = pefile.PE(data=data)
    try:
        def word(rva: int) -> int:
            return struct.unpack('<I', pe.get_data(rva, 4))[0]

        report_sites = [0x216b9c, 0x216ba4, 0x216bac, 0x216bb4,
                        0x216bbc, 0x216bc4, 0x216bcc]
        report_loads = [dict(rva=hex(rva), **decode_word_load(word(rva))) for rva in report_sites]
        if any(load['base'] != 9 for load in report_loads):
            raise ValueError('Unexpected report input base register')
        rx_loads = [dict(rva=hex(rva), **decode_pair_load(word(rva))) for rva in (0x219c00, 0x219c0c)]
        if [(x['base'], x['registers']) for x in rx_loads] != [(19, [4, 5]), (19, [6, 7])]:
            raise ValueError('Unexpected RX diagnostic argument registers')
        branches = []
        for section in pe.sections:
            if section.Characteristics & 0x20000000:
                raw = section.get_data()[:section.Misc_VirtualSize]
                branches.extend(scan_words(raw[:len(raw) // 4 * 4], section.VirtualAddress,
                                           set(TARGETS))['direct_branches'])
        name = pe.get_data(0x252d10, 64).split(b'\0')[0].decode('ascii')
        if name != 'EvtNetDeviceCollectResetDiagnostics':
            raise ValueError('Unexpected reset diagnostic label')
        # These offsets are descriptor-relative, not packet/on-air byte offsets.
        return dict(schema='qualcomm-timing-boundaries/v1', driver_sha256=hashlib.sha256(data).hexdigest(),
                    tsf_report_loads=report_loads,
                    tsf_report_word_offsets=[x['offset'] for x in report_loads],
                    rx_diagnostic_loads=rx_loads,
                    rx_diagnostic_word_offsets=[x['offsets'][0] for x in rx_loads],
                    reset_diagnostics_routine_name=name,
                    targets={hex(k): v for k, v in TARGETS.items()}, direct_branches=branches,
                    complete_call_coverage=False, live_retrieval_qualified=False,
                    packet_timestamp_export_qualified=False, firmware_request_identity_qualified=False,
                    hardware_qpc_conversion_qualified=False, private_request_sent=False)
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
        result = inspect_boundaries(data)
        write_json_new(args.output, result)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, pefile.PEFormatError) as error:
        parser.exit(1, f'Timing boundary inspection rejected: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())
