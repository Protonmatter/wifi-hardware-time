"""Inspect the exact owned driver file for action-4 submission evidence.

File-only: no device opens, requests, kernel memory or quarantine changes.
Output contains addresses/hashes and manually reviewed path classifications,
not vendor code. Exit 0 inspection, 1 rejected input/I/O, 2 CLI misuse.
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

from research.tsf.qualcomm_protocol import validate_driver
from research.windows_timestamps.ndis_evidence import write_json_new

MAX_BYTES = 16 * 1024 * 1024
WINDOWS = (
    ("action_selection", 0x18E9E0, 0x48),
    ("command_builder", 0x1955E8, 0x100),
    ("send_wrapper", 0x169678, 8),
    ("send_core", 0x169680, 0x760),
    ("barrier_type_dispatch", 0x16AAF8, 0x64),
    ("peer_delete_enqueue", 0x16AB60, 64),
    ("vdev_delete_enqueue", 0x18D540, 64),
    ("htc_send_multiple", 0x1B9140, 64),
    ("htc_queue_busy_branch", 0x1B9840, 0xC0),
    ("htc_issue_packets", 0x1B7E38, 64),
    ("htc_send_completion", 0x1B7690, 64),
    ("report_handler", 0x216B00, 64),
)


def inspect_image(data: bytes) -> dict[str, Any]:
    if type(data) is not bytes or len(data) > MAX_BYTES:
        raise ValueError("Require driver bytes within the 16 MiB bound")
    validate_driver(data)
    pe = pefile.PE(data=data)
    try:
        # MOVZ X4,#0 followed by B to 0x169680. This is a selected instruction
        # check, not an automatic proof of completion semantics in all callees.
        if pe.get_data(0x169678, 8) != struct.pack("<II", 0xD2800004, 0x14000001):
            raise ValueError("Send wrapper no longer clears the optional barrier")
        windows = []
        for name, rva, count in WINDOWS:
            raw = pe.get_data(rva, count)
            if len(raw) != count:
                raise ValueError(f"Incomplete code window at {rva:#x}")
            windows.append(dict(name=name, rva=hex(rva), bytes=count,
                                sha256=hashlib.sha256(raw).hexdigest()))
        return dict(
            schema="wht/action4-completion-static-v1",
            driver_sha256=hashlib.sha256(data).hexdigest(), code_windows=windows,
            evidence_scope="exact image, selected wrapper instructions and code-window hashes; path semantics require the accompanying manual trace",
            optional_barrier_argument=0,
            manually_traced_barrier_types={"0x6002": "peer-delete queue", "0x5002": "vdev-delete queue"},
            manually_traced_transport="HTCSendPktsMultiple -> HTCTrySend; success can leave accepted commands queued",
            report_event_id="0x5005", report_handler_rva="0x216b00",
            request_completion_is_sampling_fence_qualified=False,
            response_association_qualified=False, fresh_sampling_qualified=False,
            live_request_sent=False,
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
        parser.exit(1, f"Action-4 inspection rejected: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
