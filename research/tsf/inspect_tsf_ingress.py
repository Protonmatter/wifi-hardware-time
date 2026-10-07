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
    ("receive_pool_constructor", 0x187C20, 0x1885E8),
    ("hif_pool_binding", 0x1971F0, 0x197334),
    ("tracked_backing_allocation", 0x82B0, 0x8514),
    ("zeroed_backing_allocation", 0x7C10, 0x7C64),
    ("backing_allocator_selection", 0x7988, 0x7C08),
    ("backing_buffer_release", 0x7C68, 0x7D4C),
    ("adapter_configuration_apply", 0x2E268, 0x2E72C),
    ("adapter_allocation", 0x32650, 0x329DC),
    ("dma_enabler_and_adapter", 0x35BA8, 0x35D04),
    ("hif_disable", 0x196C90, 0x196DB8),
    ("hif_bus_disable_dispatch", 0x196AD8, 0x196B08),
    ("pci_bus_operations", 0x1EC9C0, 0x1ECA70),
    ("pci_disable", 0x1B57A0, 0x1B587C),
    ("pci_dpc_drain", 0x1B5488, 0x1B5600),
    ("ce_disable_cleanup", 0x1B1F58, 0x1B202C),
    ("completion_shutdown", 0x1B32D8, 0x1B3548),
    ("hif_stop", 0x1B4640, 0x1B472C),
    ("thread_stop_af0", 0x1B5E90, 0x1B5F48),
    ("thread_stop_a58", 0x1B5DD8, 0x1B5E90),
    ("interrupt_unregister_flag", 0x1B6860, 0x1B68B4),
    ("pool_mdl_release", 0x186128, 0x1861DC),
    ("adapter_close_release_tail", 0x1865B0, 0x186864),
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
            0x168D7C: 0xB9400108,  # original header load through X8
            0x168D80: 0x12005D13,  # event selector masks upper header byte
            0x168D94: 0xF9001E88,  # pooled logical-length update
            0x168DA4: 0xF90002E9,  # pooled data-offset update
            0x187DD4: 0x52871008,  # pool buffer count 0x3880
            0x187E60: 0xD281001A,  # each retained capacity 0x800
            0x187FA0: 0x710712FF,  # 0x1c4 backing blocks
            0x188000: 0xF90036C0,  # store IoAllocateMdl result, possibly null
            0x188004: 0xB50000C0,  # non-null branch to MDL construction
            0x188018: 0x14000003,  # null branch continues allocation loop
            0x1972C0: 0xF9008E78,  # retain supplied pool at HIF +0x118
            0x6DD8: 0xB4000534,   # map: null temporary MDL skips flush
            0x6E84: 0x52800000,   # map still returns zero
            0x6F18: 0xB4000374,   # sync: null temporary MDL skips flush
            0x7A54: 0xB9402A84,   # direct allocation cache type from request +0x28
            0x2E410: 0x52800035,  # MOV W21,#1 used by selector writer
            0x2E670: 0xB905D915,  # write selector global at 0x32e5d8
            0x35C50: 0xF9417908,  # WDF table +0x2f0: create DMA enabler
            0x35CC0: 0xF9460508,  # WDF table +0xc08: get DMA adapter
            0x35CE0: 0xF9000520,  # returned adapter -> global 0x3958b8
            0x79CC: 0x52800028,   # cache enum 1 (MmCached)
            0x79D0: 0xB90013E8,   # cache enum stored for pointer argument
            0x7A04: 0x910043E5,   # X5 points to cache enum
            0x7A08: 0x52800004,   # W4 flags = 0
            0x7A0C: 0xF9408908,   # DMA_OPERATIONS +0x110
            0x7CD8: 0xF9400D48,   # DMA_OPERATIONS +0x18: free common buffer
            0x196D10: 0xB9044A7F,  # clear HIF enabled state
            0x196AE4: 0xF9405008,  # bus-disable target from HIF +0xa0
            0x1ECA0C: 0xA909A009,  # install slots +0x98/+0xa0
            0x1B57F0: 0xAA1303E0,  # overwrite X0 after DPC drain, no status branch
            0x1B559C: 0x52800180,  # DPC drain failure return 0xc
            0x1B55E0: 0x52800000,  # MPDispatch-only branch can return zero
            0x1B3428: 0x52986A16,  # 50000 microseconds requested per stall round
            0x1B3468: 0x710052FF,  # compare completed rounds against 20
            0x1B3490: 0x14000027,  # timeout path goes to epilogue, bypasses local free
            0x1B5F00: 0xD2800004,  # null timeout on first thread wait
            0x1B5E48: 0xD2800004,  # null timeout on second thread wait
            0x1B5EF0: 0x37F801B4,  # reference failure skips first thread wait
            0x1B5E38: 0x37F801B4,  # reference failure skips second thread wait
            0x1B689C: 0xB902EE7F,  # unregister helper clears adapter +0x2ec
        }
        for rva, instruction in checks.items():
            if pe.get_data(rva, 4) != struct.pack("<I", instruction):
                raise ValueError(f"Selected instruction mismatch at {rva:#x}")
        expected_imports = {
            0x2ED418: "MmAllocateContiguousMemorySpecifyCache",
            0x2ED440: "IoAllocateMdl",
            0x2ED450: "MmBuildMdlForNonPagedPool",
        }
        allocation_imports = {
            item.address - pe.OPTIONAL_HEADER.ImageBase: item.name.decode("ascii")
            for entry in pe.DIRECTORY_ENTRY_IMPORT for item in entry.imports
            if item.name and item.address - pe.OPTIONAL_HEADER.ImageBase in expected_imports
        }
        if allocation_imports != expected_imports:
            raise ValueError("Unexpected allocation import identities")
        expected_shutdown_imports = {
            0x2ED008: "KeStallExecutionProcessor", 0x2ED048: "NdisMSleep",
            0x2ED0F8: "KeWaitForSingleObject", 0x2ED270: "ObReferenceObjectByHandle",
            0x2ED278: "ZwClose",
        }
        shutdown_imports = {
            item.address - pe.OPTIONAL_HEADER.ImageBase: item.name.decode("ascii")
            for entry in pe.DIRECTORY_ENTRY_IMPORT for item in entry.imports
            if item.name and item.address - pe.OPTIONAL_HEADER.ImageBase in expected_shutdown_imports
        }
        if shutdown_imports != expected_shutdown_imports:
            raise ValueError("Unexpected shutdown import identities")
        selector_value = struct.unpack("<I", pe.get_data(0x32E5D8, 4))[0]
        address_width, dma_version = struct.unpack("<II", pe.get_data(0x35D08, 8))
        if (selector_value, address_width, dma_version) != (1, 36, 3):
            raise ValueError("Unexpected allocator selector or DMA configuration constants")
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
                   0x67A0, 0x6D40, 0x6EB0, 0x1B2F18, 0x1B3B30, 0x1F2D48, 0x1F3A30, 0x1F3A68,
                   0x188024, 0x1971F0, 0x82B0, 0x7C10, 0x7988, 0x2E268, 0x35BA8,
                   0x196AD8, 0x1B3EC0, 0x1B4488, 0x1B32D8, 0x1B2BA0, 0x1B2180,
                   0x1B5488, 0x1B1F58, 0x1EE020, 0x1B5E90, 0x1B5DD8, 0x186128,
                   0x8520, 0x6AE0}
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
            selected_allocation_imports={hex(rva): name for rva, name in sorted(allocation_imports.items())},
            selected_shutdown_imports={hex(rva): name for rva, name in sorted(shutdown_imports.items())},
            manual_pool_admission=dict(
                constructor_rva="0x187c20", buffer_count=0x3880,
                backing_blocks=0x1C4, backing_block_bytes=0x10000, buffer_capacity_bytes=0x800,
                buffer_metadata_bytes=0x1E0, cached_mdl_store_rva="0x188000",
                null_cached_mdl_aborts_allocation_loop=False,
                hif_pool_store_rva="0x1972c0", hif_pool_offset="0x118",
                map_null_mdl_branch_rva="0x6dd8", map_return_zero_proves_flush=False,
                sync_null_mdl_branch_rva="0x6f18",
                allocator_selector_global_rva="0x32e5d8",
                direct_allocation="zero-selector branch calls MmAllocateContiguousMemorySpecifyCache with request +0x28; pool request supplies 1 (MmCached)",
                alternate_allocation="nonzero-selector branch resolves to AllocateCommonBufferWithBounds at DMA_OPERATIONS +0x110; live selection/coherency remain unobserved",
                live_allocator_branch_observed=False, live_coherency_qualified=False,
                evidence_scope="selected static branches and pool binding; no live allocation failure or corrupt data demonstrated",
            ),
            manual_dma_contract=dict(
                selector_file_value=selector_value, selector_writer_rva="0x2e670", selector_writer_value=1,
                selection_scope="on-disk initializer and located configuration writer favor the common-buffer route; not an exhaustive writer or runtime audit",
                adapter_global_rva="0x3958b8", adapter_store_rva="0x35ce0",
                wdf_function_indices={"WdfDmaEnablerCreate": 94, "WdfDmaEnablerWdmGetDmaAdapter": 385,
                                      "WdfMemoryGetBuffer": 194, "WdfObjectDelete": 208},
                public_wdf_commit="b6191d9543441329154da32f7ab9bdd97228dd3c",
                dma_operation_slots={"FreeCommonBuffer": "0x18", "AllocateCommonBufferWithBounds": "0x110"},
                operations_layout_scope="documented DMA_OPERATIONS member order with ARM64 eight-byte pointer alignment",
                enabler_address_width_override=address_width, enabler_dma_version_override=dma_version,
                cache_type_override="MmCached", allocation_flags=0,
                returned_dma_address_kind="device logical address",
                returned_cpu_address_kind="CPU virtual address",
                preferred_node="starts at zero and retries through the stored KeQueryHighestNodeNumber result",
                free_record="length +0, device logical address +8, CPU virtual address +16, cache enum +24",
                cache_contract="explicit cached allocation is not proof of adapter coherency or a completed cache flush",
                live_adapter_observed=False, live_allocator_branch_observed=False,
                live_coherency_qualified=False, teardown_order_qualified=False,
            ),
            manual_wmi_copy_boundary=dict(
                before_header_load_rva="0x168d7c", selector_mask_rva="0x168d80",
                length_store_rva="0x168d94", offset_store_rva="0x168da4",
                decoder_call_rva="0x168e0c",
                pooled_source="buffer +0x10 base plus +0x30 offset; +0x38 logical length still includes WMI header at this boundary",
                original_header="retain all four bytes, not only the low-24-bit selector",
                source_span_validated_by_inspector=False, exporter_installed=False,
                evidence_scope="source/instrumented integration location, not a callable application interface or hook recipe",
            ),
            manual_receive_shutdown=dict(
                hif_disable_rva="0x196c90", pci_disable_target_rva="0x1b57a0",
                bus_disable_slot="0xa0", bus_operations_writer_rva="0x1ec9c0",
                pci_order=["set +0x430", "DPC drain", "CE cleanup", "ring cleanup",
                           "thread stop +0xaf0", "thread stop +0xa58"],
                dpc_drain_rva="0x1b5488", dpc_drain_failure_status=12,
                pci_caller_checks_dpc_drain_status=False,
                dpc_drain_zero_limit="selected MPDispatch-reference timeout branch logs conditionally then returns zero",
                completion_shutdown=dict(
                    rva="0x1b32d8", queue_offset="0x4b8", pipe_stride="0x60",
                    reference_offset="0x510", max_stall_rounds=21, stall_us_per_round=50000,
                    nominal_stall_sum_is_wall_clock_bound=False,
                    caller_receives_success_status=False,
                    timeout_effect="log and return, bypassing this routine's completion-space/lock free block; caller continues",
                ),
                thread_waits=[dict(rva="0x1b5e90", handle_offset="0xaf0", signal_offset="0xac0"),
                              dict(rva="0x1b5dd8", handle_offset="0xa58", signal_offset="0xa28")],
                thread_wait_timeout_pointer=None, thread_wait_requires_reference_success=True,
                unregister_flag=dict(rva="0x1b6860", adapter_flag_offset="0x2ec", value=0),
                unregister_flag_is_callback_join=False,
                selected_close_release_order=["0x186128 cached MDLs", "0x8520 backing blocks"],
                live_rundown_qualified=False, dma_enabler_release_order_qualified=False,
                all_callback_producers_covered=False, observed_live_race=False,
                evidence_scope="bounded static shutdown paths; not a complete lifecycle proof or a demonstrated driver defect",
            ),
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
