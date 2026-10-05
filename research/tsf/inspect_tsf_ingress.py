"""Exact-build, file-only TSF event ingress and callback-lifetime evidence.

No device access or acquisition. Inspect an owned driver file and emit addresses,
code hashes and explicitly scoped manual conclusions. Exit 0 inspection,
1 rejected input/I/O, 2 CLI misuse. Output must be new with an existing parent.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
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
RANGES = (
    ("tsf_registration", 0x21599C, 0x2159B4),
    ("control_rx", 0x168CE0, 0x169148),
    ("tlv_decoder", 0x1BA4E0, 0x1BAA50),
    ("schema_lookup", 0x1BDFE0, 0x1BE148),
    ("cleanup_wrapper", 0x1BAE60, 0x1BAE70),
    ("event_cleanup_selector", 0x1BC580, 0x1BC5D8),
    ("one_slot_cleanup", 0x1BB558, 0x1BB57C),
    ("report_handler", 0x216B00, 0x216CCC),
    ("htc_rx_header", 0x1F5F20, 0x1F6558),
    ("htc_rx_callback", 0x1F58B0, 0x1F59F4),
    ("aggregate_buffer_length", 0x143218, 0x1432D4),
    ("wmi_send_completion", 0x169220, 0x169524),
    ("buffer_release", 0x6AE0, 0x6C08),
    ("hif_callback_registration", 0x1B3A98, 0x1B3B30),
    ("hif_callback_install", 0x1B4518, 0x1B4640),
    ("hif_receive_queue_writer", 0x1B17F0, 0x1B1A2C),
    ("hif_completion_dispatch", 0x1B2F18, 0x1B32D8),
    ("hif_receive_replenish", 0x1B3B30, 0x1B3DA8),
    ("hif_ce_callback_registration", 0x1B3548, 0x1B36CC),
    ("pooled_buffer_checkout", 0x67A0, 0x6904),
    ("receive_buffer_map", 0x6D40, 0x6EA0),
    ("receive_buffer_sync", 0x6EB0, 0x6FE0),
    ("ce_status_receive", 0x1F49A0, 0x1F4BCC),
    ("ce_descriptor_history", 0x1F4290, 0x1F4368),
)


def inspect_image(data: bytes) -> dict[str, Any]:
    if type(data) is not bytes or len(data) > MAX_BYTES:
        raise ValueError("Require driver bytes within the 16 MiB bound")
    validate_driver(data)
    pe = pefile.PE(data=data)
    try:
        layout = find_event_layout(pe.get_data(TABLE_RVA, TABLE_BYTES), 0x5005)
        expected = dict(tag=0x18B, element_size=60, variable_flag=0, count_code=510)
        if layout["entries"] != [expected]:
            raise ValueError("Unexpected TSF event descriptor")
        # Check selected literal instructions; all other path interpretation is
        # manual, anchored by the exact image and the emitted code-window hashes.
        checks = {
            0x2159A4: 0xD2800003,  # MOV X3,#0 (registration context)
            0x2159A8: 0x528A00A1,  # MOV W1,#0x5005
            0x168E08: 0x2A1703E2,  # MOV W2,W23 (original payload length)
            0x16901C: 0x2A1703E2,  # same length passed to handler
            0x1BA834: 0xB9000D1F,  # borrowed slot allocation flag = 0
            0x1BA8C0: 0xB9000D09,  # allocated slot flag from W9 = 1
            0x1B4598: 0x91254282,  # callback-copy source HIF +0x950
            0x1B45A0: 0x9125E280,  # callback-copy destination HIF +0x978
            0x1B3124: 0xF9001F7A,  # received count -> network buffer +0x38
            0x1B3130: 0xF944BE60,  # active callback context +0x978
            0x1B3134: 0xF944C668,  # active receive callback +0x988
        }
        for rva, instruction in checks.items():
            if pe.get_data(rva, 4) != struct.pack("<I", instruction):
                raise ValueError(f"Selected instruction mismatch at {rva:#x}")
        cleanup_entry = 0x1BDA90 + (0x5005 - 0x5002) * 4
        cleanup_delta = struct.unpack("<i", pe.get_data(cleanup_entry, 4))[0]
        cleanup_target = 0x1BB558 + cleanup_delta * 4
        if cleanup_target != 0x1BB558:
            raise ValueError("TSF cleanup no longer selects one slot")
        ce_operations = []
        for table, post, receive in ((0x3933F0, 0x1F2120, 0x1F2370),
                                     (0x3934F0, 0x1F46D0, 0x1F49A0)):
            for slot, expected_target in ((0x30, post), (0x40, receive)):
                target = struct.unpack("<Q", pe.get_data(table + slot, 8))[0] - pe.OPTIONAL_HEADER.ImageBase
                if target != expected_target:
                    raise ValueError("Unexpected copy-engine operation table")
                ce_operations.append(dict(table_rva=hex(table), slot=hex(slot), target_rva=hex(target)))
        ranges = []
        branches = []
        targets = {0x16A078, 0x1BA4E0, 0x1BAE60, 0x1BAE70, 0x15A3A4, 0x7740, 0x2EC050,
                   0x67A0, 0x6D40, 0x6EB0, 0x1B2F18, 0x1B3B30, 0x1F2D48, 0x1F3A30, 0x1F3A68}
        for name, start, end in RANGES:
            raw = pe.get_data(start, end - start)
            if len(raw) != end - start:
                raise ValueError("Incomplete inspection range")
            ranges.append(dict(name=name, start_rva=hex(start), end_rva_exclusive=hex(end),
                               sha256=hashlib.sha256(raw).hexdigest()))
            branches.extend(scan_words(raw, start, targets)["direct_branches"])
        return dict(
            schema="wht/tsf-event-ingress-static-v1", driver_sha256=hashlib.sha256(data).hexdigest(),
            event_id="0x5005", handler_rva="0x216b00", callback_registration_context=0,
            event_schema=layout, schema_entry_rva=hex(TABLE_RVA + layout["table_offset"]),
            cleanup_table_entry_rva=hex(cleanup_entry), cleanup_target_rva=hex(cleanup_target),
            decoded_slot=dict(bytes=16, pointer_offset=0, count_offset=8, allocated_offset=12),
            original_length_source="logical receive-buffer +0x38 after four-byte WMI-header removal; low 32 bits passed to decoder and callback, not attested wire extent",
            manual_normalization="short fixed TLV: allocate 60, zero, copy original bytes without rewriting its TLV header; equal/larger: borrow input",
            manual_lifetime="callback return precedes decoded-slot cleanup and original-buffer release",
            manual_transport=dict(
                htc_header_bytes=8, advertised_payload_length_offset=2,
                trailer_present_mask=2, trailer_length_offset=4,
                dispatched_wmi_length="aggregate buffer length minus eight HTC bytes and trailer; not an exact advertised-payload equality check",
                contiguous_source_span_qualified=False,
                receive_callback_offset="endpoint +0x18", receive_context_offset="endpoint +0x8",
                send_completion_rva="0x169220", pooled_buffer_reference_count_offset="0x198",
                endpoint_zero_copy="separate HTC control-message buffer, not the selected nonzero WMI callback route",
                command_history="general outgoing-payload history differs from filtered completion history and payload-free event history",
            ),
            ce_operation_tables=ce_operations,
            manual_hif_producer=dict(
                callback_block_bytes=40, pending_block_offset="0x950", active_block_offset="0x978",
                active_receive_callback_offset="0x988",
                completion_record=dict(bytes=64, next_offset="0x0", type_offset="0x8", receive_type=2,
                                       pipe_offset="0x18", buffer_offset="0x20", bytes_offset="0x30",
                                       metadata_offsets=["0x34", "0x38"]),
                pool_reset_bytes=480,
                pooled_buffer=dict(base_offset="0x10", capacity_offset="0x28", data_offset="0x30",
                                   logical_length_offset="0x38", cached_mdl_offset="0x68",
                                   extra_fragment_count_offset="0x158", pool_offset="0x170"),
                geometry="selected posted pooled-buffer path resets fragment metadata; HIF queues records without joining payloads",
                cache_sync="helper called before queue publication; KeFlushIoBuffers depends on an existing or successfully allocated MDL",
                copy_candidate="after synchronization and before the HTC receive callback, while the completed buffer is retained",
                descriptor_count_source="alternate table uses descriptor +8 low16; status table uses descriptor +0 upper16",
                history=dict(record_bytes=40, descriptor_bytes=16, copied_wmi_payload=False,
                             cursor_precedes_record_writes=True),
                active_ce_table_observed=False, live_source_span_qualified=False,
                live_cache_sync_qualified=False, exporter_connected=False,
            ),
            ranges=ranges, selected_direct_branches=branches,
            evidence_scope="exact image and selected instructions/table; manual path analysis, not driver execution",
            runtime_wire_length_verified=False, logical_length_is_wire_extent_qualified=False,
            live_callback_ownership_qualified=False,
            application_export_established=False, response_association_qualified=False,
            fresh_sampling_qualified=False, hardware_qpc_qualified=False, live_request_sent=False,
        )
    finally:
        pe.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--driver", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise ValueError("Output already exists")
        with args.driver.open("rb") as stream:
            data = stream.read(MAX_BYTES + 1)
        result = inspect_image(data)
        write_json_new(args.output, result)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, pefile.PEFormatError) as error:
        parser.exit(1, f"TSF ingress inspection rejected: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
