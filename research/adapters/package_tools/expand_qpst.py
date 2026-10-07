"""Decode the inspected QPST BIN/103 -> InstallShield v3 layout as files.

Use the preview/hash-gated PowerShell entry point. No installer is executed.
Generated member filenames never use vendor-controlled paths.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import logging
from pathlib import Path
import struct
import zlib
import pefile

LIMIT = 512 * 1024 * 1024


def decode_members(data: bytes) -> list[tuple[str, bytes]]:
    offset = data.rfind(b'ISSetupStream\0')
    if offset < 0 or offset + 46 > len(data):
        raise ValueError('Missing InstallShield stream header')
    count, version = struct.unpack_from('<HI', data, offset + 14)
    if not 1 <= count <= 128 or version != 3:
        raise ValueError('Unsupported InstallShield profile')
    offset += 46
    entries = []
    total = 0
    for _ in range(count):
        if offset + 24 > len(data):
            raise ValueError('Truncated member header')
        name_length, flags = struct.unpack_from('<II', data, offset)
        length = struct.unpack_from('<I', data, offset + 10)[0]
        unicode_flag = struct.unpack_from('<H', data, offset + 22)[0]
        offset += 24
        if not 2 <= name_length <= 520 or name_length % 2 or offset + name_length + length > len(data):
            raise ValueError('Invalid member extent')
        if flags != 6 or unicode_flag != 1:
            raise ValueError('Unsupported member encoding')
        name = data[offset:offset+name_length].decode('utf-16le').rstrip('\0')
        seed = name.encode('utf-8')
        if not seed:
            raise ValueError('Empty member name')
        offset += name_length
        key = bytes(v ^ (0x13, 0x35, 0x86, 7)[i % 4] for i, v in enumerate(seed))
        packed = bytes((~(key[(i % 1024) % len(key)] ^ ((v << 4 | v >> 4) & 255))) & 255
                       for i, v in enumerate(data[offset:offset+length]))
        offset += length
        inflater = zlib.decompressobj()
        value = inflater.decompress(packed, LIMIT + 1)
        if len(value) > LIMIT or inflater.unconsumed_tail:
            raise ValueError('Expanded member exceeds limit')
        value += inflater.flush(max(1, LIMIT + 1 - len(value)))
        total += len(value)
        if len(value) > LIMIT or total > 1024**3 or not inflater.eof or inflater.unused_data:
            raise ValueError('Incomplete, trailing or oversized compressed member')
        entries.append((name, value))
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        if args.input.is_symlink() or args.input.stat().st_size > LIMIT:
            raise ValueError('Invalid input extent')
        data = args.input.read_bytes()
        image = pefile.PE(data=data)
        try:
            resources = [lang.data.struct for kind in image.DIRECTORY_ENTRY_RESOURCE.entries
                         if str(kind.name) == 'BIN' for name in kind.directory.entries
                         if name.id == 103 for lang in name.directory.entries]
            if len(resources) != 1:
                raise ValueError('Expected one BIN/103 resource')
            resource = resources[0]
            nested = image.get_data(resource.OffsetToData, resource.Size)
            if len(nested) != resource.Size:
                raise ValueError('Truncated resource')
        finally:
            image.close()
        entries = decode_members(nested)
        args.output.mkdir(parents=False, exist_ok=False)
        rows = []
        for index, (name, value) in enumerate(entries):
            output_name = 'QPST.msi' if name == 'QPST 2.7.msi' else f'member-{index:03d}.bin'
            with (args.output/output_name).open('xb') as stream:
                stream.write(value)
            rows.append({'name': name, 'file': output_name, 'bytes': len(value),
                         'sha256': hashlib.sha256(value).hexdigest()})
        print(json.dumps({'schema': 'wht/qpst-static-members-v1', 'members': rows,
                          'scope': 'static decoding, no installer execution'}, indent=2))
        return 0
    except (OSError, ValueError, AttributeError, zlib.error, pefile.PEFormatError) as error:
        logging.error('Extraction failed: %s', error)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
