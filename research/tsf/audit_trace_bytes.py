"""Audit saved WlanLogger UserData bytes; never interpret ETW text as a WMI event.

Offline only. Raw output stays private. Zero selected records is inconclusive.
No loss/freshness/clock qualification or quarantine disposition is changed.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import logging
from pathlib import Path
import re
import subprocess
from typing import Any

MAX_ETL = 64 * 1024 * 1024
MAX_EXPORT = 16 * 1024 * 1024
PROVIDER = "bb6f5b93-635c-47be-816f-e895e77064a8"
PATTERNS = {
    "command": rb"WMI_VDEV_TSF_TSTAMP_ACTION_CMDID: vdev_id=([0-9]+) tsf_action=([0-9]+)",
    "report": rb"OL: receive WMI_VDEV_TSF_REPORT_EVENTID on (-?[0-9]+), tsf: ([0-9]+) ([0-9]+)",
    "soc_timer": rb"OL: g_tsf: (-?[0-9]+) (-?[0-9]+); soc_timer: ([0-9]+) ([0-9]+)",
    "delay": rb"OL: set vdev-(-?[0-9]+) tsf_delay=([0-9]+)",
}
SIGNED_FIELDS = {"command": (), "report": (0,), "soc_timer": (0,1), "delay": (0,)}


def payload_view(raw: bytes, family: str) -> dict[str, Any]:
    if type(raw) is not bytes or not 1 <= len(raw) <= 65535 or family not in PATTERNS:
        raise ValueError("invalid_payload_or_family")
    head, separator, tail = raw.partition(b"\0")
    match = re.fullmatch(PATTERNS[family] + rb"(?:\r?\n)?", head)
    valid = match is not None and all(
        len(x) <= 11 and (-(2**31) <= int(x) < 2**31 if i in SIGNED_FIELDS[family]
                         else 0 <= int(x) <= 0xFFFFFFFF)
        for i,x in enumerate(match.groups()))
    return dict(
        sha256=hashlib.sha256(raw).hexdigest(), length=len(raw),
        text_bytes=len(head), nul_terminated=bool(separator), trailing_bytes=len(tail),
        trailing_nonzero_bytes=sum(x != 0 for x in tail),
        exact_numeric_text=valid,
        numeric_words=[int(x) for x in match.groups()] if valid else None,
        classification="numeric-text-only" if valid and not tail else
                       "numeric-text-with-zero-tail" if valid and not any(tail) else
                       "requires-byte-review",
        original_wmi_event_established=False,
    )


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def _uint(value: Any, maximum: int = 2**64 - 1) -> int:
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError("invalid_unsigned_integer")
    return value


def _keys(value: dict[str, Any], expected: str) -> None:
    if set(value) != set(expected.split()):
        raise ValueError("missing_or_unknown_fields")


def _decimal(value: Any) -> int:
    if type(value) is not str or not re.fullmatch(r"-?(0|[1-9][0-9]{0,18})", value):
        raise ValueError("invalid_int64_string")
    number = int(value)
    if not -(2**63) <= number < 2**63:
        raise ValueError("int64_out_of_range")
    return number


def audit_export(data: bytes) -> dict[str, Any]:
    if type(data) is not bytes or not 1 <= len(data) <= MAX_EXPORT:
        raise ValueError("invalid_export_size")
    lines = data.splitlines()
    if not 2 <= len(lines) <= 10002 or any(len(line) > 132000 for line in lines):
        raise ValueError("invalid_line_bounds")
    rows = [json.loads(line, object_pairs_hook=_unique) for line in lines]
    if any(type(row) is not dict for row in rows):
        raise ValueError("invalid_record")
    header, summary = rows[0], rows[-1]
    _keys(header,"kind schema provider clock_type frequency events_lost buffers_lost")
    _keys(summary,"kind events wlan_events exported payload_bytes process_status close_status bound_failure")
    if (header.get("kind") != "header" or header.get("schema") != "wht/tsf-trace-bytes-v1"
            or header.get("provider") != PROVIDER or summary.get("kind") != "summary"):
        raise ValueError("missing_or_wrong_envelope")
    if (_uint(summary["process_status"]) or _uint(summary["close_status"])
            or summary["bound_failure"] is not False):
        raise ValueError("incomplete_native_export")
    if _uint(header["clock_type"]) > 3 or _decimal(header["frequency"]) < 0:
        raise ValueError("invalid_clock_header")
    losses = {key: _uint(header[key]) for key in ("events_lost", "buffers_lost")}
    total = _uint(summary["events"], 2000000)
    wlan = _uint(summary["wlan_events"], total)
    if _uint(summary["exported"], wlan) != len(rows) - 2:
        raise ValueError("record_count_mismatch")
    payload_bytes, previous = 0, 0
    observations = []
    for row in rows[1:-1]:
        _keys(row,"kind ordinal family timestamp id version opcode flags extended_data_count length hex")
        if row.get("kind") != "event" or row.get("family") not in PATTERNS or row.get("id") != 1:
            raise ValueError("unexpected_event")
        ordinal = _uint(row["ordinal"], total)
        if ordinal <= previous:
            raise ValueError("duplicate_or_reordered_event")
        previous = ordinal
        _decimal(row["timestamp"])
        for key, limit in (("id",65535),("flags",65535),("version",255),("opcode",255),("extended_data_count",65535)):
            _uint(row[key], limit)
        size = _uint(row["length"], 65535)
        text = row["hex"]
        if type(text) is not str or len(text) != size * 2 or not re.fullmatch(r"(?:[0-9a-f]{2})+", text):
            raise ValueError("payload_length_or_hex_mismatch")
        raw = bytes.fromhex(text)
        payload_bytes += len(raw)
        view = payload_view(raw, row["family"])
        observations.append(dict(ordinal=ordinal, family=row["family"], timestamp=row["timestamp"],
                                 extended_data_count=row["extended_data_count"], **view))
    if payload_bytes > 4 * 1024 * 1024 or _uint(summary["payload_bytes"]) != payload_bytes:
        raise ValueError("payload_total_mismatch")
    reviews = sum(x["classification"] == "requires-byte-review" for x in observations)
    extended = sum(x["extended_data_count"] != 0 for x in observations)
    return dict(
        schema="wht/tsf-trace-byte-audit-v1", export_sha256=hashlib.sha256(data).hexdigest(),
        native_export_complete=True, selected_records=len(observations),
        families=dict(sorted(Counter(x["family"] for x in observations).items())),
        classifications=dict(sorted(Counter(x["classification"] for x in observations).items())),
        payload_bytes=payload_bytes, records_requiring_byte_review=reviews,
        records_with_uninspected_extended_data=extended, trace_loss=losses,
        raw_clock_type=header["clock_type"], raw_clock_frequency=header["frequency"],
        assessment="no-selected-records" if not observations else
                   "selected-userdata-is-numeric-text" if not reviews else "additional-byte-review-required",
        observations=observations, original_firmware_event_recovered=False,
        hardware_qpc_qualified=False, clock_eligible=False, quarantine_disposition="unchanged",
        scope="Selected saved WlanLogger event-1 UserData only; extended-data contents and other events not exported",
    )


def _hash_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exporter", required=True, type=Path)
    parser.add_argument("--etl", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path, help="NEW private directory")
    args = parser.parse_args()
    try:
        if not args.exporter.is_file() or args.exporter.is_symlink():
            raise ValueError("exporter_missing_or_linked")
        if not args.etl.is_file() or args.etl.is_symlink() or not 1 <= args.etl.stat().st_size <= MAX_ETL:
            raise ValueError("invalid_etl")
        input_hash, exporter_hash = _hash_file(args.etl), _hash_file(args.exporter)
        args.output.mkdir(parents=False, exist_ok=False)
        raw_path = args.output / "selected-userdata.jsonl"
        with raw_path.open("xb") as output, (args.output / "native-stderr.txt").open("xb") as error:
            result = subprocess.run([str(args.exporter.resolve()), str(args.etl.resolve())],
                                    stdout=output, stderr=error, timeout=60, check=False)
        if result.returncode != 0:
            raise ValueError(f"native_export_failed_{result.returncode}; partial output retained")
        if _hash_file(args.etl) != input_hash or _hash_file(args.exporter) != exporter_hash:
            raise ValueError("input_or_exporter_changed_during_read")
        if raw_path.stat().st_size > MAX_EXPORT:
            raise ValueError("oversized_export")
        report = audit_export(raw_path.read_bytes())
        report.update(input_etl_sha256=input_hash, exporter_sha256=exporter_hash,
                      native_exit=result.returncode, new_hardware_acquisition=False)
        (args.output / "audit.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        print(json.dumps({key:report[key] for key in ("assessment","selected_records","families","classifications","trace_loss")}))
        return 0
    except (OSError, ValueError, KeyError, TypeError, RecursionError, subprocess.TimeoutExpired) as error:
        logging.error("Saved-byte audit failed: %s", error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
