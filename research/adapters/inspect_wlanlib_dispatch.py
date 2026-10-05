"""Inventory selected WLANLIB selectors in the exact owned driver file.

File-only inspection: no device handles, vendor code loading or firmware access.
Reports scalar constants and code-window hashes, not proprietary instructions.
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
        windows = []
        for name, rva in CODE_WINDOWS:
            raw = pe.get_data(rva, 64)
            if len(raw) != 64:
                raise ValueError(f"Truncated code window at {rva:#x}")
            windows.append(dict(name=name, rva=hex(rva), bytes=64,
                                sha256=hashlib.sha256(raw).hexdigest()))
        return dict(schema="wht/wlanlib-dispatch-static-v1", driver_sha256=QUALIFIED_SHA256,
                    ioctl_selectors=selectors, other_constants=constants, code_windows=windows,
                    evidence_scope="scalar identity and 64-byte windows; manual control-flow trace is separate",
                    event_fetch_format="uint32 length followed by cached UTF payload; fetch clears cached length",
                    cache_state_offsets=dict(payload_pointer="0x38240", published_length_u16="0x38248",
                                             accumulated_length="0x38250", next_segment="0x38259"),
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
