"""Inventory selected BSS time ranges in two exact owned Windows ARM64 files.

Offline file reads only: no symbols download, device access or runtime addresses.
Range hashes support manual analysis; they do not prove timestamp semantics.
Exit 0: inspected; 1: input/I/O rejected; 2: CLI misuse. Output must be new.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pefile

from research.windows_timestamps.ndis_evidence import write_json_new

MAX_IMAGE_BYTES = 16 * 1024 * 1024
IMAGE_HASHES = {
    'wificx': '7587df7324f4daa70af890edae6e60316b2277a2bb6e21b29ecf6d71f3f3635d',
    'wlanmsm': '2e80a99a59d604df8f4c05da0149792acca3f7f50d4fcfae5196493b1d91055b',
}
# End-exclusive ranges selected by manual inspection, not function-size recovery.
RANGES = {
    'wificx': (
        ('CPort::IncorporateBSSEntryList', 0x6DE8, 0x71C8),
        ('CPort::OnBSSEntryNotification', 0x71C8, 0x75E0),
        ('CBSSListManager::ReceiveBeaconOrProbe', 0x9260, 0x9918),
        ('CBSSEntry::UpdateBSSEntry', 0x9BE0, 0x9D50),
        ('wificx::utils::QuerySystemTime', 0x1E888, 0x1E8A0),
        ('CSystem::get_CurrentTime', 0x28210, 0x28248),
        ('CPort::IncorporateBSSEntryList_staging', 0x66568, 0x66790),
        ('CBSSEntry::FillDot11BSSEntry', 0x7A318, 0x7A428),
        ('CBSSEntry::OnLinkQualityUpdate', 0x7E310, 0x7E380),
        ('CBSSListManager::ReceiveBeaconOrProbe_staging', 0x7E958, 0x7EE78),
        ('CBSSEntry::SetBeaconOrProbeResponse', 0x7FA00, 0x7FCE0),
        ('CBSSEntry::SetBeaconOrProbeResponseForMRsnO', 0x7FD30, 0x7FFE0),
        ('CBSSEntry_vtable_prefix', 0xF2770, 0xF27A0),
    ),
    'wlanmsm': (
        ('IniDot11MsmScanMgrCopyBssEntry', 0x2EB68, 0x2ED78),
    ),
}


def read_image(path: Path) -> bytes:
    """Read one bounded owned image; never load or execute it."""
    with path.open('rb') as stream:
        data = stream.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError('Image exceeds inspection bound')
    return data


def inspect_image(data: bytes, image: str) -> dict[str, Any]:
    """Return an exact-build range inventory without code bytes or file paths."""
    if image not in IMAGE_HASHES:
        raise ValueError('Unsupported image identity')
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError('Image exceeds inspection bound')
    digest = hashlib.sha256(data).hexdigest()
    if digest != IMAGE_HASHES[image]:
        raise ValueError(f'{image} is not the qualified build')
    pe = pefile.PE(data=data, fast_load=True)
    try:
        if pe.FILE_HEADER.Machine != 0xAA64:
            raise ValueError('Expected ARM64 image')
        ranges = []
        for name, start, end in RANGES[image]:
            raw = pe.get_data(start, end - start)
            if len(raw) != end - start:
                raise ValueError('Truncated inspection range')
            ranges.append(dict(name=name, start_rva=hex(start),
                               end_rva_exclusive=hex(end), bytes=len(raw),
                               sha256=hashlib.sha256(raw).hexdigest()))
        return dict(image=image, sha256=digest, machine=hex(pe.FILE_HEADER.Machine),
                    ranges=ranges)
    finally:
        pe.close()


def inspect_images(wificx: bytes, wlanmsm: bytes) -> dict[str, Any]:
    return dict(schema='windows-bss-time-static/v1',
                images=[inspect_image(wificx, 'wificx'), inspect_image(wlanmsm, 'wlanmsm')],
                coverage='exact-build selected range inventory; semantics require manual inspection',
                runtime_path_qualified=False, hardware_pair_export_qualified=False,
                live_capture_performed=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wificx', type=Path, required=True)
    parser.add_argument('--wlanmsm', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise ValueError('Output already exists')
        result = inspect_images(read_image(args.wificx), read_image(args.wlanmsm))
        write_json_new(args.output, result)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, pefile.PEFormatError) as error:
        parser.exit(1, f'Inspection rejected: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())
