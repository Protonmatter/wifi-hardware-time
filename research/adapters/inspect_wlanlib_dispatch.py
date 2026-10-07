"""Inventory selected WLANLIB selectors in the exact owned driver file.

File-only inspection: no device handles, vendor code loading or firmware access.
Reports scalar constants, code-window hashes and selected instruction matches,
not a disassembly listing.
The named semantics come from the linked manual trace, not automatic proof of
control flow. Exit 0: receipt written; 1: rejected input/I/O; 2: CLI error.
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

from research.tsf.qualcomm_protocol import QUALIFIED_SHA256, validate_driver
from research.windows_timestamps.ndis_evidence import write_json_new

MAX_IMAGE_BYTES = 16 * 1024 * 1024
# Explicitly distinguish IOCTL selectors from status codes and WMI namespaces.
IOCTLS = (
    ("qmux_nas_info", 0x11C364, 0x81802C00),
    ("qmux_5g_state_query_or_wait", 0x11C368, 0x81802C04),
    ("qmux_coexistence_config", 0x11C36C, 0x81802C08),
    ("art2_test_dispatch", 0x11D6EC, 0xC3502406),
    ("iwpriv_command", 0x11F84C, 0x00220182),
    ("station_link_stats", 0x11F884, 0x002201CC),
    ("fips_mode", 0x11F89C, 0x0022020E),
    ("fips_request", 0x11F8A0, 0x00220212),
    ("fips_event", 0x11F8A4, 0x00220216),
    ("fips_extended_event", 0x11F8A8, 0x00220218),
    ("qdss_debug", 0x11F8B0, 0x98742004),
)
OTHER_CONSTANTS = (
    ("wmi_utf_command", "wmi_command_id", 0x1A4D8C, 0x1D002),
    ("wmi_utf_event", "wmi_event_id", 0x1A4BB0, 0x1D002),
    ("qmux_unsupported", "ntstatus", 0x11C370, 0xC00000BB),
    ("art2_unsupported", "ntstatus", 0x11D6F0, 0xC00000BB),
)
CODE_WINDOWS = (
    ("device_io_control", 0x0293C0),
    ("secondary_io_control", 0x0298C0),
    ("qmux_dispatch", 0x11BFB8),
    ("qmux_completion", 0x11BD90),
    ("art2_dispatch", 0x437340),
    ("utf_producer", 0x1A4E10),
    ("utf_fetch", 0x1A4F80),
    ("iwpriv_dispatch", 0x11E840),
    ("qmux_manual_queue_configuration", 0x436CF0),
    ("qmux_force_complete", 0x11C4D8),
    ("qmux_notification_schedule", 0x11C6E0),
    ("qmux_context_free", 0x11C640),
    ("control_deinitialize", 0x329E8),
    ("self_managed_suspend", 0x36C90),
)
# Selected ARM64 instruction identities, not an automated control-flow proof.
PENDING_CHECKS = (
    ("manual_dispatch_and_false_power_management", 0x436D38, 0xD2800068),
    ("store_dispatch_and_power_fields", 0x436D3C, 0xF80343E8),
    ("queue_handle_destination", 0x436D9C, 0x910F02C4),
    ("lock_handle_destination", 0x436E38, 0x910F22C2),
    ("force_complete_queue", 0x11C580, 0xF941E2A1),
    ("force_complete_retrieve", 0x11C588, 0xF9427908),
    ("force_complete_release_lock", 0x11C5B0, 0xF944E908),
    ("force_complete_status_argument", 0x11C5F0, 0x2A1703E2),
    ("force_complete_operation", 0x11C5FC, 0xF9441D08),
    ("deinitialize_calls_force_complete", 0x32A80, 0x9403A696),
    ("suspend_calls_force_complete", 0x36D8C, 0x940395D3),
    ("terminate_calls_context_free", 0x31218, 0x9403AD0A),
    ("deinitialize_purges_other_queue", 0x32A94, 0xF941D901),
)
METHODS = ("METHOD_BUFFERED", "METHOD_IN_DIRECT", "METHOD_OUT_DIRECT", "METHOD_NEITHER")


def ioctl_fields(value: int) -> dict[str, Any]:
    """Decode an explicitly identified selector; do not infer a constant's role."""
    if type(value) is not int or not 0 <= value <= 0xFFFFFFFF:
        raise ValueError("IOCTL must be an unsigned 32-bit integer")
    return dict(device_type=hex(value >> 16), access_bits=(value >> 14) & 3,
                function=hex((value >> 2) & 0xFFF), method=METHODS[value & 3])


def inspect_image(data: bytes) -> dict[str, Any]:
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("Driver exceeds 16 MiB inspection bound")
    validate_driver(data)
    pe = pefile.PE(data=data)
    try:
        def scalar(rva: int, expected: int) -> int:
            raw = pe.get_data(rva, 4)
            if len(raw) != 4 or struct.unpack("<I", raw)[0] != expected:
                raise ValueError(f"Unexpected scalar at {rva:#x}")
            return struct.unpack("<I", raw)[0]

        selectors = [dict(name=name, rva=hex(rva), value=hex(scalar(rva, value)),
                          **ioctl_fields(value)) for name, rva, value in IOCTLS]
        constants = [dict(name=name, namespace=namespace, rva=hex(rva),
                          value=hex(scalar(rva, value)))
                     for name, namespace, rva, value in OTHER_CONSTANTS]
        pending_checks = [dict(name=name, rva=hex(rva), matched=True)
                          for name, rva, word in PENDING_CHECKS
                          if scalar(rva, word) == word]
        drain_status = [dict(rva=hex(rva), value=hex(scalar(rva, 0xC00002B6)))
                        for rva in (0x32CAC, 0x36E68)]
        windows = []
        for name, rva in CODE_WINDOWS:
            raw = pe.get_data(rva, 64)
            if len(raw) != 64:
                raise ValueError(f"Truncated code window at {rva:#x}")
            windows.append(dict(name=name, rva=hex(rva), bytes=64,
                                sha256=hashlib.sha256(raw).hexdigest()))
        return dict(schema="wht/wlanlib-dispatch-static-v1", driver_sha256=QUALIFIED_SHA256,
                    ioctl_selectors=selectors, other_constants=constants, code_windows=windows,
                    evidence_scope="scalar identity, 64-byte windows and selected instruction matches; manual control-flow trace is separate",
                    event_fetch_format="uint32 length followed by cached UTF payload; fetch clears cached length",
                    cache_state_offsets=dict(payload_pointer="0x38240", published_length_u16="0x38248",
                                             accumulated_length="0x38250", next_segment="0x38259"),
                    pending_request_lifecycle=dict(
                        evidence="selected exact instructions plus separate manual Ghidra trace",
                        instruction_checks=pending_checks,
                        queue_handle_offset="0x3c0", wait_lock_offset="0x3c8",
                        dispatch="manual", power_managed=False,
                        force_complete_rva="0x11c4d8",
                        drain_status_name="STATUS_DEVICE_REMOVED", drain_status_literals=drain_status,
                        selected_callers=["0x329e8", "0x36c90"],
                        separately_purged_queue_offset="0x3b0",
                        context_free_rva="0x11c640", context_free_caller_rva="0x31188",
                        manual_request_flow="forward: framework owns; retrieve: driver owns; complete: do not reuse",
                        manual_drain="retrieve under wait lock, release lock, complete with supplied status; repeat until retrieval fails",
                        manual_limit="queue drain is not demonstrated admission closure, producer rundown or firmware drain",
                        complete_call_coverage=False, live_cancellation_qualified=False,
                        producer_rundown_qualified=False, firmware_drain_qualified=False,
                        timing_producer_connected=False),
                    live_request_sent=False, runtime_mode_observed=False,
                    concurrent_copy_qualified=False, timing_schema_qualified=False,
                    hardware_qpc_qualified=False)
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
            data = stream.read(MAX_IMAGE_BYTES + 1)
        result = inspect_image(data)
        write_json_new(args.output, result)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, pefile.PEFormatError) as error:
        parser.exit(1, f"WLANLIB inspection rejected: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
