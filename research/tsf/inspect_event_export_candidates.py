"""Exact-build, file-only CAPTUREH/QDSS return-path inventory.

No requests, configuration changes, register access or DMA mapping. Metadata and
manual static findings only. Raw vendor bytes stay private. Exit 0 inspected,
1 rejected input/I/O, 2 CLI misuse. Output must be new; parent must exist.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pefile

from research.ftm.inspect_ftm_ingress import TABLE_BYTES, TABLE_RVA, find_event_layout
from research.tsf.inspect_tsf_routes import scan_words
from research.tsf.qualcomm_protocol import validate_driver
from research.windows_timestamps.ndis_evidence import write_json_new

MAX_BYTES = 16 * 1024 * 1024
CONFIG_HASHES = {
    "2f319ff82e661606c1bdd3b6520c99a8e972a84839b116be9a69fb86bbbb5eac": "qdss_trace_config_v1.cfg",
    "d1f7d7ffc5178aae14f0725055c5a32535b45f10b124c190b253c222f6f990f9": "qdss_trace_config_v2.cfg",
}
CATALOG_SHA256 = "44f472870771bb5022764e62e29c1f5625d53b47b0e0a79cd86849b5a446bbaa"
CATALOG_IDS = {68,69,70,25041,25948,25949,25950,27860}
RANGES = (
    ("driver_directory",0x2F258,0x2F444),
    ("captureh_attach",0x1DD9C0,0x1DDAA4),
    ("captureh_detach",0x1DDAB0,0x1DDB44),
    ("captureh_pointer_getter",0x1DDB50,0x1DDB70),
    ("captureh_callback",0x1DDB90,0x1DDC8C),
    ("private_control_dispatch",0x11E840,0x11F834),
    ("qdss_private_control",0x122D58,0x1232E8),
    ("qdss_config_loader",0x1496C0,0x149894),
    ("qmi_indication_dispatch",0x149B40,0x149F48),
    ("qdss_save_decode",0x14B778,0x14B870),
    ("qmi_queue_copy",0x150290,0x1503E8),
    ("qdss_notification_registration",0x14BBA8,0x14BD5C),
    ("qdss_internal_dispatch",0x14B400,0x14B680),
    ("qdss_segment_address",0x14ADF8,0x14AE94),
    ("qdss_dma_save",0x14D8B8,0x14DCB4),
    ("qdss_dma_file_writer",0x14BEF0,0x14C078),
    ("qdss_chunk_fetch",0x14E9C8,0x14EDA8),
    ("qdss_file_writer",0x14F448,0x14F584),
    ("firmware_diag_registration",0x1ADA30,0x1ADD20),
    ("firmware_catalog_parser",0x1ADED0,0x1AE324),
    ("firmware_diag_receive_copy",0x1B01A0,0x1B0568),
    ("firmware_diag_queue_consumer",0x1AE5E0,0x1AE7D4),
    ("firmware_diag_record_decoder",0x1B1128,0x1B16EC),
)


def summarize_config(data: bytes) -> dict[str, Any]:
    """Lexical inventory only: uncommented directives do not imply runtime use."""
    if type(data) is not bytes or not 1 <= len(data) <= 65536:
        raise ValueError("Require 1..65536 immutable configuration bytes")
    try:
        lines = data.decode("ascii").splitlines()
    except UnicodeError as error:
        raise ValueError("Require ASCII configuration text") from error
    if len(lines) > 2048 or any(len(line) > 1024 for line in lines):
        raise ValueError("Configuration line bounds exceeded")
    sequences: list[str] = []
    commented: list[str] = []
    subsystems: set[str] = set()
    suspicious: list[int] = []
    timing: set[str] = set()
    for number, line in enumerate(lines, 1):
        text = line.strip()
        disabled = text.startswith("//")
        body = text[2:].strip() if disabled else text.split("//",1)[0].strip()
        match = re.fullmatch(r"seq_type:([a-zA-Z0-9_]+);", body)
        if match:
            (commented if disabled else sequences).append(match[1])
        if disabled:
            continue
        match = re.fullmatch(r"subsys_cfg_start:([a-zA-Z0-9_]+);", body)
        if match:
            subsystems.add(match[1])
        if "0x0x" in body.lower():
            suspicious.append(number)
        key = body.split(":",1)[0]
        if re.search(r"tsf|timestamp|qtimer|qtime|ftm", key, re.I):
            timing.add(key)
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                uncommented_sequence_types=sequences, commented_sequence_types=commented,
                named_subsystems=sorted(subsystems), repeated_hex_prefix_lines=suspicious,
                timing_named_directives=sorted(timing),
                interpretation="lexical inventory; no register/mask semantics or firmware parser validation",
                configuration_applied=False, runtime_selection_known=False,
                firmware_record_schema_qualified=False)


def summarize_catalog(data: bytes) -> dict[str, Any]:
    """Select catalog definitions, not measured values or a binary-record decoder."""
    if type(data) is not bytes or not 1 <= len(data) <= 4*1024*1024:
        raise ValueError("Require bounded immutable catalog bytes")
    lines=data.splitlines()
    if len(lines)>50000 or any(len(line)>16384 for line in lines):
        raise ValueError("Catalog line bounds exceeded")
    header=re.fullmatch(rb"VERSION:([0-9]{1,10})",lines[0])
    if header is None or int(header[1])>0xFFFFFFFF:
        raise ValueError("Invalid catalog version header")
    selected: dict[int,dict[str,Any]]={}
    for number,line in enumerate(lines[1:],2):
        row=re.fullmatch(rb"([0-9]{1,5}),([^,]*),(.*)",line)
        if row is None or int(row[1]) not in CATALOG_IDS:
            continue
        identifier=int(row[1])
        if identifier in selected:
            raise ValueError("Duplicate selected catalog message")
        try:
            signature=row[2].decode("ascii")
            description=row[3].decode("ascii")
        except UnicodeError as error:
            raise ValueError("Non-ASCII selected catalog definition") from error
        source=re.match(r"\[\s*([A-Za-z0-9_.-]+)\s*:\s*([0-9]+)\s*\]",description)
        if source is None or not re.fullmatch(r"[A-Za-z0-9]*",signature):
            raise ValueError("Unexpected selected catalog entry")
        selected[identifier]=dict(id=identifier,line=number,signature=signature,
            source_file=source[1],source_line=int(source[2]),
            named_fields=re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*=",description),
            definition_sha256=hashlib.sha256(line).hexdigest())
    if not selected:
        raise ValueError("No selected timing definitions")
    return dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),version=int(header[1]),
                selected_records=[selected[key] for key in sorted(selected)],
                scope="selected message definitions only; other catalog entries remain opaque",
                live_record_observed=False,runtime_firmware_version_matched=False,
                qdss_stream_binding_qualified=False,clock_eligible=False)


def inspect_image(data: bytes) -> dict[str, Any]:
    if type(data) is not bytes or len(data) > MAX_BYTES:
        raise ValueError("Require immutable driver bytes within 16 MiB")
    validate_driver(data)
    pe = pefile.PE(data=data)
    try:
        event = struct.unpack("<I",pe.get_data(0x1DDAAC,4))[0]
        ioctl = struct.unpack("<I",pe.get_data(0x11F8B0,4))[0]
        diag_event = struct.unpack("<I",pe.get_data(0x1ADD20,4))[0]
        layout = find_event_layout(pe.get_data(TABLE_RVA,TABLE_BYTES),event)
        if event != 0x1E003 or ioctl != 0x98742004 or diag_event != 0x1D011 or layout["entries"] != [dict(tag=194,element_size=16,variable_flag=0,count_code=510)]:
            raise ValueError("Unexpected selectors or CAPTUREH schema")
        markers = {0x1DDC54:0xB9000114, 0x1DDC6C:0x97FDF1CE,
                   0x14EAE0:0x52800841, 0x14EAE4:0x9403949F,
                   0x14EB50:0x5283000D, 0x14ED8C:0x940001AF}
        for rva,expected in markers.items():
            if struct.unpack("<I",pe.get_data(rva,4))[0] != expected:
                raise ValueError(f"Unexpected instruction at {rva:#x}")
        windows, branches = [], []
        targets={start for _,start,_ in RANGES}|{0x16A078,0x15A3A4,0x233D60,0x233788}
        for name,start,end in RANGES:
            raw=pe.get_data(start,end-start)
            if len(raw) != end-start:
                raise ValueError("Incomplete code window")
            windows.append(dict(name=name,start_rva=hex(start),end_rva_exclusive=hex(end),
                                sha256=hashlib.sha256(raw).hexdigest()))
            branches.extend(scan_words(raw,start,targets)["direct_branches"])
        return dict(
            schema="wht/firmware-trace-return-candidates-static-v1",
            driver_sha256=hashlib.sha256(data).hexdigest(),code_windows=windows,
            selected_direct_branches=branches,
            firmware_diag=dict(wmi_event_id=hex(diag_event),receive_rva="0x1b01a0",
                catalog="Data20.msc",candidate_message_id=25950,catalog_version_gate=True,
                copy="separate payload allocation and copy before queued publication",
                consumer="0x1ae5e0 -> 0x1b1128; format using catalog, then free queued bytes",
                formatted_memory_cache_bytes=128,
                original_tsf_wmi_event_preserved=False,owned_application_return_qualified=False,
                source_span_qualified=False,live_execution_observed=False),
            captureh=dict(event_id=hex(event),schema_entries=layout["entries"],
                allocation_bytes=0x804,payload_capacity_bytes=0x800,cache_pointer_rva="0x3f3980",
                getter="borrowed cache pointer and length; no owned application copy",
                publication="length stored before copy; no inspected lock or generation protocol",
                framing="callback registered through normalizing WMI dispatcher; flat argument copy is not original-wire proof",
                original_tsf_event_return=False,live_execution_observed=False),
            qdss=dict(qmi_save_indication="0x41",internal_message="0x1f",chunk_request="0x42",
                chunk_limit_bytes=6144,decoded_save_object_bytes=0x508,internal_queue_copy_bytes=0x9C8,
                return_routes=["source-0: selected DMA spans to file","source-1: QMI chunks assembled to file"],
                default_filename="qdss_trace.bin",directory="SystemRoot/Temp",
                private_ioctl=hex(ioctl),request_bytes=104,response_bytes=100,
                controls={"0":"allocate/zero/map DMA memory into caller; not a record getter",
                          "1":"unmap/free selected or all tracked allocations",
                          "3":"copy cached 16-bit device-context field; not a timestamp"},
                config_loader_rva="0x1496c0",config_directory_writer_rva="0x2f258",
                config_filenames=list(CONFIG_HASHES.values()),config_gate_name="qdssTraceEnable",
                runtime_gate_known=False,firmware_writer_to_user_mapping_qualified=False,
                complete_file_delivery_qualified=False,firmware_record_schema_qualified=False,
                tsf_event_content_qualified=False),
            interpretation_scope="exact-build manual trace with selected instruction/table checks; not exhaustive indirect-call analysis",
            live_request_sent=False,configuration_applied=False,source_ownership_qualified=False,
            hardware_qpc_qualified=False,clock_eligible=False)
    finally:
        pe.close()


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--driver",type=Path,required=True)
    parser.add_argument("--config",type=Path,action="append",default=[],help="Optional pinned sidecar; at most two")
    parser.add_argument("--catalog",type=Path,help="Optional pinned Data20.msc; definitions only")
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    try:
        if args.output.exists():
            raise ValueError("Output already exists")
        if len(args.config)>2:
            raise ValueError("At most two config files")
        result=inspect_image(read_file(args.driver,MAX_BYTES))
        configs=[]
        for path in args.config:
            summary=summarize_config(read_file(path,65536))
            digest=summary["sha256"]
            if digest not in CONFIG_HASHES or any(x["sha256"]==digest for x in configs):
                raise ValueError("Unknown or duplicate configuration snapshot")
            configs.append(dict(file=CONFIG_HASHES[digest],**summary))
        result["configurations"]=configs
        result["catalog"]=None
        if args.catalog is not None:
            catalog=summarize_catalog(read_file(args.catalog,4*1024*1024))
            if catalog["sha256"]!=CATALOG_SHA256:
                raise ValueError("Unknown catalog snapshot")
            result["catalog"]=catalog
        write_json_new(args.output,result)
        print(json.dumps(dict(status="inspected",code_windows=len(result["code_windows"]),
                              configurations=len(configs),live_request_sent=False)))
        return 0
    except (OSError,ValueError,pefile.PEFormatError) as error:
        parser.exit(1,f"Firmware trace inspection rejected: {error}\n")


def read_file(path: Path, limit: int) -> bytes:
    if not path.is_file() or path.is_symlink():
        raise ValueError("Require a regular unlinked file")
    with path.open("rb") as stream:
        data=stream.read(limit+1)
    if len(data)>limit:
        raise ValueError("Input file exceeds bound")
    return data


if __name__=="__main__":
    raise SystemExit(main())
