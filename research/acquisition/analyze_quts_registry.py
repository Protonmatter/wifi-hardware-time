"""Offline, exact-build registry/stack correlation. Never accesses a device.

Input is private JSONL from export_registry_trace plus capture receipts. Output
contains counts and limits, not registry paths, PIDs, pointers or payloads.
Exit 0 means analysis completed, including an unqualified result; 1 malformed input.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import json
import logging
from pathlib import Path
import re
import struct
from typing import Any

QUTS_HASH = "8e6de10a298f8378e9d289ad11a33018654a29d155e56588f9427d53ed639297"
EXPECTED_RVAS = (0xB2CD0, 0xB5168, 0xB5DDC)
MISSING = 0xC0000034
MAX_BYTES = 128 * 1024 * 1024


def integer(value: Any) -> int:
    if type(value) is int and 0 <= value <= 0xFFFFFFFFFFFFFFFF:
        return value
    if isinstance(value, str) and re.fullmatch(r"[0-9]{1,20}", value):
        return integer(int(value))
    raise ValueError("Expected an unsigned 64-bit integer, not a floating point value")


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON field")
        result[key] = value
    return result


@dataclass(frozen=True)
class Registry:
    qpc: int
    pid: int
    tid: int
    opcode: int
    status: int
    key: int
    name: str


@dataclass(frozen=True)
class Stack:
    qpc: int
    pid: int
    tid: int
    frames: tuple[int, ...]


def decode(row: dict[str, Any]) -> Registry | Stack:
    kind = row.get("kind")
    if integer(row["version"]) != 2:
        raise ValueError("Unqualified event version")
    flags = integer(row["flags"])
    if not flags & 0x40 or flags & 0x20:
        raise ValueError("Only observed 64-bit event layout is supported")
    raw = row["payload"]
    if not isinstance(raw, str) or len(raw) > 131070 or len(raw) % 2 or not re.fullmatch(r"[0-9a-fA-F]*", raw):
        raise ValueError("Invalid payload encoding/length")
    data = bytes.fromhex(raw)
    opcode = integer(row["opcode"])
    if kind == "registry":
        if not 10 <= opcode <= 27 or len(data) < 26 or (len(data) - 24) % 2 or data[-2:] != b"\0\0":
            raise ValueError("Incomplete or unsupported registry payload")
        _, status, _, key = struct.unpack_from("<QIIQ", data)
        name = data[24:-2].decode("utf-16le", errors="strict")
        if "\0" in name:
            raise ValueError("Embedded terminator in registry name")
        return Registry(integer(row["timestamp"]), integer(row["pid"]), integer(row["tid"]), opcode, status, key, name)
    if kind == "stack":
        if opcode != 32 or len(data) < 24 or (len(data) - 16) % 8 or (len(data) - 16) // 8 > 192:
            raise ValueError("Incomplete or unsupported stack payload")
        stamp, pid, tid = struct.unpack_from("<QII", data)
        frames = struct.unpack("<" + "Q" * ((len(data) - 16) // 8), data[16:])
        return Stack(stamp, pid, tid, frames)
    raise ValueError("Unexpected event kind")


def read_json(path: Path) -> Any:
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("Input exceeds 128 MiB")
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=unique_object)


def read_export(path: Path) -> tuple[dict[str, Any], list[Registry | Stack], dict[str, Any]]:
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("Export exceeds 128 MiB")
    with path.open(encoding="utf-8-sig") as stream:
        items = [json.loads(line, object_pairs_hook=unique_object) for line in stream if line.strip()]
    if not all(isinstance(item, dict) for item in items):
        raise ValueError("Every export item must be an object")
    if len(items) < 2 or len(items) > 2_000_002 or items[0].get("kind") != "header" or items[-1].get("kind") != "summary":
        raise ValueError("Missing header/summary or record bound exceeded")
    header, summary = items[0], items[-1]
    if integer(header["clock_type"]) != 1 or integer(header["pointer_size"]) != 8 or integer(header["frequency"]) == 0:
        raise ValueError("Only raw QPC with 64-bit pointers is qualified")
    if summary.get("bound_failure") is not False or integer(summary["process_status"]) or integer(summary["close_status"]):
        raise ValueError("Native export incomplete")
    if integer(summary["exported"]) != len(items) - 2:
        raise ValueError("Export count mismatch")
    return header, [decode(item) for item in items[1:-1]], summary


def analyze(header: dict[str, Any], events: list[Registry | Stack], before: dict[str, Any],
            after: dict[str, Any], run: dict[str, Any], controls: list[dict[str, Any]], health: str) -> dict[str, Any]:
    reasons: list[str] = []
    if before != after or before.get("status") != "Up" or before.get("driver_version") != "1.0.4374.1300":
        reasons.append("identity_or_lifecycle_mismatch")
    if not all(run.get(key) is True for key in ("trace_started", "trace_stopped")) or run.get("error") is not None:
        reasons.append("capture_or_cleanup_not_complete")
    if integer(header["events_lost"]) or integer(header["buffers_lost"]):
        reasons.append("file_reports_loss")
    for label in ("Dropped event", "Events Lost"):
        hits = re.findall(re.escape(label) + r"\s*:\s*([0-9]+)", health)
        if len(hits) != 1 or int(hits[0]) != 0:
            reasons.append("controller_loss_or_missing_health")
    bases: dict[int, int] = {}
    for process in before["processes"]:
        if process["sha256"].lower() != QUTS_HASH:
            raise ValueError("Unqualified QUTS image")
        pid = integer(process["process_id"])
        base = int(process["module_base"], 16)
        if not pid or pid in bases or base <= 0:
            raise ValueError("Invalid/duplicate process identity")
        bases[pid] = base
    if not 1 <= len(bases) <= 8:
        raise ValueError("Process count outside qualified bound")
    driver = before["driver_key"].lower()
    if not re.fullmatch(r"\{4d36e972-e325-11ce-bfc1-08002be10318\}\\[0-9]{4}", driver):
        raise ValueError("Unexpected network driver-key form")
    target = re.compile(r"^\\registry\\machine\\system\\(?:currentcontrolset|controlset[0-9]{3})\\control\\class\\" + re.escape(driver) + r"$", re.I)
    registry = sorted((e for e in events if isinstance(e, Registry)), key=lambda e: e.qpc)
    stacks: dict[tuple[int, int, int], list[Stack]] = defaultdict(list)
    for e in events:
        if isinstance(e, Stack):
            stacks[e.pid, e.tid, e.qpc].append(e)
    identities = Counter((e.pid, e.tid, e.qpc) for e in registry if e.opcode == 16)
    lifecycle_counts = Counter((e.key, e.qpc) for e in registry if e.opcode in (22, 23, 24, 25))
    key_paths: dict[int, str | None] = {}
    candidates, matched = 0, 0
    rejected: Counter[str] = Counter()
    statuses: Counter[str] = Counter()
    for e in registry:
        if e.opcode in (22, 23, 24, 25) and lifecycle_counts[e.key, e.qpc] > 1:
            # Equal timestamps do not order a key's lifecycle across ETW buffers.
            # Poison this generation until a later distinct delete/create pair.
            key_paths[e.key] = None
        elif e.opcode == 23:  # global KCB delete, not an individual handle close
            key_paths.pop(e.key, None)
        elif e.opcode in (22, 24, 25) and e.status == 0:
            prior = key_paths.get(e.key)
            if e.key in key_paths and (prior is None or prior.lower() != e.name.lower()):
                key_paths[e.key] = None  # unexplained reuse; wait for delete/new creation
            else:
                key_paths[e.key] = e.name
        elif e.opcode == 16 and e.pid in bases and e.name == "QCDeviceControlFile":
            if (e.key, e.qpc) in lifecycle_counts:
                rejected["ambiguous_key_lifecycle_order"] += 1
                continue
            path = key_paths.get(e.key)
            if path is None or not target.fullmatch(path):
                rejected["unbound_or_other_key"] += 1
                continue
            candidates += 1
            ident = (e.pid, e.tid, e.qpc)
            if identities[ident] != 1:
                rejected["ambiguous_registry_identity"] += 1
                continue
            expected = {bases[e.pid] + rva for rva in EXPECTED_RVAS}
            matches = [s for s in stacks[ident] if expected <= set(s.frames)]
            if len(matches) != 1:
                rejected["missing_or_ambiguous_expected_stack"] += 1
                continue
            matched += 1
            statuses[f"0x{e.status:08x}"] += 1
    control_matches = Counter()
    expected_controls = Counter((phase, name) for phase in ("start", "end")
                                for name in ("NetCfgInstanceId", "QCDeviceControlFile") for _ in range(5))
    actual_controls = Counter((c["phase"], c["name"]) for c in controls)
    if actual_controls != expected_controls or len(controls) != 20:
        reasons.append("missing_control_receipts")
    elif integer(run.get("control_qpc_frequency", 0)) != integer(header["frequency"]):
        reasons.append("control_clock_mismatch")
    else:
        prior_end: dict[tuple[int, int], int] = {}
        for c in controls:
            pid, tid = integer(c["pid"]), integer(c["tid"])
            start, end = integer(c["before_qpc"]), integer(c["after_qpc"])
            if pid != integer(run["control_process_id"]) or end <= start or start <= prior_end.get((pid, tid), 0):
                raise ValueError("Invalid/overlapping control interval")
            prior_end[pid, tid] = end
            expected_present = c["name"] == "NetCfgInstanceId"
            if c["value_present"] is not expected_present:
                reasons.append("control_value_assumption_changed")
                continue
            expected_status = 0 if expected_present else MISSING
            hits = [e for e in registry if e.opcode == 16 and e.pid == pid and e.tid == tid
                    and e.name == c["name"] and start <= e.qpc <= end and e.status == expected_status
                    and identities[e.pid, e.tid, e.qpc] == 1]
            if hits:
                control_matches[c["phase"], c["name"]] += 1
    if control_matches != expected_controls:
        reasons.append("positive_control_coverage_incomplete")
    return {"schema": "wht/quts-registry-analysis-v1", "target_queries": candidates,
            "queries_with_exact_stack": matched, "query_status_counts": dict(sorted(statuses.items())),
            "rejections": dict(sorted(rejected.items())), "controls_matched": sum(control_matches.values()),
            "control_matches_by_phase_and_name": {f"{p}:{n}": count for (p, n), count in sorted(control_matches.items())},
            "qualification_limits": sorted(set(reasons)), "capture_coverage_qualified": not reasons,
            "live_query_callsite_validated": not reasons and statuses.get(f"0x{MISSING:08x}", 0) > 0,
            "conditional_branch_instruction_validated": False, "hardware_qpc_sampling_validated": False,
            "firmware_event_delivery_validated": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export", type=Path)
    parser.add_argument("capture_directory", type=Path)
    args = parser.parse_args()
    try:
        header, events, _ = read_export(args.export)
        root = args.capture_directory
        controls = read_json(root / "positive-controls.json") if (root / "positive-controls.json").is_file() else []
        result = analyze(header, events, read_json(root / "identity-before.json"),
                         read_json(root / "identity-after.json"), read_json(root / "result.json"),
                         controls, (root / "wpr-3.stdout.txt").read_text(encoding="utf-8-sig"))
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError, struct.error) as error:
        logging.error("Registry analysis rejected: %s", error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
