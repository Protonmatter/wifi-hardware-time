"""Decode an owned broker response, never a device or firmware clock.

File-only CLI: JSON on stdout. Exit 0 decoded, 1 rejected input/I/O, 2 CLI misuse.
Raw response bytes may be sensitive; keep acquired material outside public Git.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
from typing import Any

HEADER = 96
MAX_PAYLOAD = 4096


def decode_response(data: bytes | bytearray, *, expected_ticket: int,
                    expected_session: int, expected_generation: int,
                    expected_source: int) -> dict[str, Any]:
    for value in (expected_ticket, expected_session, expected_generation, expected_source):
        if type(value) is not int or not 1 <= value <= 2**64 - 1:
            raise ValueError("Require explicit nonzero uint64 software identities")
    if type(data) not in (bytes, bytearray):
        raise ValueError("Require owned response bytes")
    # Bound the copy itself, then validate the immutable snapshot. A mutable
    # source can resize between an earlier length check and this operation.
    raw = bytes(data[:HEADER + MAX_PAYLOAD + 1])
    if not HEADER <= len(raw) <= HEADER + MAX_PAYLOAD:
        raise ValueError("Require a complete bounded owned response")
    magic, version, header, total, payload, origin, capabilities = struct.unpack_from("<4sHHIIII", raw)
    if magic != b"WHTR" or version != 1 or header != HEADER or total != len(raw) or payload != total - HEADER or not payload:
        raise ValueError("Malformed broker header or response extent")
    if origin not in (1, 2) or capabilities != 0:
        raise ValueError("Unqualified origin or unsupported capability claim")
    session, generation, source, sequence, losses, rejects = struct.unpack_from("<6Q", raw, 24)
    point, reserved, ticket, reserved2 = struct.unpack_from("<IIQQ", raw, 72)
    if (ticket, session, generation, source) != (expected_ticket, expected_session, expected_generation, expected_source):
        raise ValueError("Application response identity mismatch")
    if not sequence or reserved or reserved2 or (origin == 1 and point not in (1, 2)) or (origin == 2 and point != 3):
        raise ValueError("Invalid observation metadata")
    return dict(schema="wht/application-raw-response-v1", origin={1: "fixture", 2: "replay-unqualified"}[origin],
                application_read_ticket=str(ticket), software_session=str(session),
                software_generation=str(generation), source_scope=str(source),
                host_observation_sequence=str(sequence), software_overflow_losses_before=str(losses),
                software_rejects_before=str(rejects), declared_copy_point=point,
                payload_hex=raw[HEADER:].hex(), response_sha256=hashlib.sha256(raw).hexdigest(),
                hardware_source_connected=False, firmware_association_qualified=False,
                source_copy_qualified=False, hardware_qpc_qualified=False, live_clock_eligible=False)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", type=Path)
    for field in ("ticket", "session", "generation", "source"):
        p.add_argument("--expected-" + field, type=lambda s: int(s, 0), required=True)
    a = p.parse_args()
    try:
        with a.input.open("rb") as stream:
            raw = stream.read(HEADER + MAX_PAYLOAD + 1)
        result = decode_response(raw, expected_ticket=a.expected_ticket,
                                 expected_session=a.expected_session,
                                 expected_generation=a.expected_generation, expected_source=a.expected_source)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError) as error:
        p.exit(1, f"Raw response rejected: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
