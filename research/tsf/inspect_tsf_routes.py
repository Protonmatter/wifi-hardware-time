"""Offline, exact-build ARM64 TSF route inventory. Reads the owned SYS as a file.

No device, trace, firmware command, disassembler installation or kernel access.
Outputs RVAs/counts only, not instructions or proprietary bytes. Exit 0 means
inspection completed; 1 means rejected input/I/O; 2 means CLI usage error.
No output overwrite. This bounded scan cannot prove complete call coverage.
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

TARGETS={0x1955e8:'tsf_command_builder',0x18e910:'auto_report_wrapper',
         0x18e9e0:'read_value_wrapper',0x216b00:'tsf_report_handler',
         0x8b78:'memory_log_writer',0x8d20:'memory_log_copy',
         0x8a88:'memory_log_recent_span',0x230a50:'host_memory_log_file_dump'}


def scan_words(data: bytes, base_rva: int, targets: set[int]) -> dict[str,Any]:
    """Decode only immediate B/BL and MOVZ 0x5012 at aligned word locations.

    Executable PE sections may contain data; matches still require code-context
    inspection. Indirect calls and synthesized command constants are not covered.
    """
    if type(data) is not bytes or len(data)%4 or type(base_rva) is not int or not 0<=base_rva<=0xffffffff or base_rva%4:
        raise ValueError('Expected aligned code bytes and RVA')
    branches=[];immediates=[]
    for offset in range(0,len(data),4):
        word=struct.unpack_from('<I',data,offset)[0];rva=base_rva+offset
        if word&0x7c000000==0x14000000:
            delta=word&0x3ffffff
            if delta&0x2000000:delta-=0x4000000
            target=rva+delta*4
            if target in targets:
                branches.append(dict(rva=hex(rva),target_rva=hex(target),link=bool(word&0x80000000)))
        # MOVZ Wd/Xd with shift zero, not MOVK or a shifted partial constant.
        if word&0x7f800000==0x52800000 and (word>>5)&0xffff==0x5012 and (word>>21)&3==0:
            immediates.append(hex(rva))
    return dict(direct_branches=branches,command_immediate_rvas=immediates)


def inspect_image(data: bytes) -> dict[str,Any]:
    validate_driver(data)
    pe=pefile.PE(data=data)
    try:
        branches=[];immediates=[];sections=[]
        for section in pe.sections:
            if not section.Characteristics&0x20000000:continue
            raw=section.get_data()[:section.Misc_VirtualSize]
            length=len(raw)-len(raw)%4
            found=scan_words(raw[:length],section.VirtualAddress,set(TARGETS))
            branches.extend(found['direct_branches']);immediates.extend(found['command_immediate_rvas'])
            sections.append(dict(rva=hex(section.VirtualAddress),aligned_bytes_scanned=length))
        # Search aligned on-disk absolute VA entries. Runtime-constructed pointers,
        # RVAs, encoded pointers and indirect targets are deliberately not inferred.
        pointers={hex(target):[] for target in TARGETS}
        for section in pe.sections:
            raw=section.get_data()[:section.Misc_VirtualSize]
            for offset in range((-section.VirtualAddress)%8,len(raw)-7,8):
                value=struct.unpack_from('<Q',raw,offset)[0]-pe.OPTIONAL_HEADER.ImageBase
                if value in TARGETS:pointers[hex(value)].append(hex(section.VirtualAddress+offset))
        imports={}
        for entry in pe.DIRECTORY_ENTRY_IMPORT:
            for item in entry.imports:
                rva=item.address-pe.OPTIONAL_HEADER.ImageBase
                if rva in (0x2ed358,0x2ed360,0x2ed2f8,0x2ed310,0x2ed278):
                    imports[hex(rva)]=item.name.decode('ascii') if item.name else f'ordinal:{item.ordinal}'
        return dict(schema='qualcomm-tsf-static-routes/v1',driver_sha256=hashlib.sha256(data).hexdigest(),
            targets={hex(k):v for k,v in TARGETS.items()},executable_sections=sections,
            direct_branches=branches,command_immediate_rvas=immediates,aligned_absolute_pointer_rvas=pointers,
            selected_imports=imports,memory_log_capacity_bytes=struct.unpack('<I',pe.get_data(0x32e058,4))[0],
            complete_call_coverage=False,firmware_initiator_identified=False,private_request_sent=False)
    finally:pe.close()


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--driver',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try:
        if args.output.exists():raise ValueError('Output already exists')
        with args.driver.open('rb') as stream:data=stream.read(16*1024*1024+1)
        if len(data)>16*1024*1024:raise ValueError('Driver exceeds inspection bound')
        result=inspect_image(data)
        write_json_new(args.output,result)
        print(json.dumps(result,indent=2))
        return 0
    except (OSError,ValueError,pefile.PEFormatError) as error:
        parser.exit(1,f'Static inspection rejected: {error}\n')


if __name__=='__main__':raise SystemExit(main())
