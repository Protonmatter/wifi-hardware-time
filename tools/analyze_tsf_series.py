"""Offline analysis of bounded TSF captures; no device access or network calls.

Usage: python analyze_tsf_series.py RUN_DIRECTORY
Requires raw-timing.jsonl from decode_tsf_etl.exe. Outputs analysis-series.json.
Exit 0: internally consistent observed series. Exit 1: missing/ambiguous evidence.
Clock rate estimates are relative to host event times, not absolute accuracy.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import median
from typing import Any


def distribution(values: list[float]) -> dict[str, float]:
    return {"min": min(values), "median": median(values), "max": max(values)}


def analyze(requests: list[dict[str, Any]], events: list[dict[str, Any]],
            expected_count: int | None = None) -> dict[str, Any]:
    headers = [e for e in events if e["kind"] == "header"]
    summaries = [e for e in events if e["kind"] == "summary"]
    if len(headers) != 1 or len(summaries) != 1 or not requests:
        raise ValueError("Require one trace header/summary and at least one request")
    if expected_count is not None and (not 1 <= expected_count <= 12 or len(requests) != expected_count):
        raise ValueError("Request count does not match the planned capture count")
    header, summary = headers[0], summaries[0]
    frequency = header["perf_frequency_hz"]
    if (header["clock_type"] != 1 or frequency <= 0 or header["events_lost"]
            or header["buffers_lost"] or summary["process_status"] or summary["close_status"]):
        raise ValueError("Trace is not a successfully decoded loss-free QPC trace")
    requests = sorted(requests, key=lambda r: r["qpc_request_before"])
    identity = (requests[0]["driver_sha256"], requests[0]["interface_index"])
    for request in requests:
        if (request["qpc_frequency_hz"] != frequency or not request["success"]
                or not request["handle_closed"] or request["command"] != "tsf_read_value"
                or request["firmware_action"] != 3
                or (request["driver_sha256"], request["interface_index"]) != identity
                or request["qpc_request_completed"] < request["qpc_request_before"]):
            raise ValueError("Request failed, clock mismatch, or unexpected action")
    commands = [e for e in events if e["kind"] == "command"]
    reports = [e for e in events if e["kind"] == "report"]
    soc_events = [e for e in events if e["kind"] == "soc_timer"]
    delays = [e for e in events if e["kind"] == "delay"]
    if not (len(commands) == len(reports) == len(soc_events) == len(delays) == len(requests)):
        raise ValueError("Missing or extra command/report/SoC events; do not infer correlation")
    samples: list[dict[str, Any]] = []
    for index, request in enumerate(requests):
        start = request["qpc_request_before"]
        stop = requests[index + 1]["qpc_request_before"] if index + 1 < len(requests) else float("inf")
        window = [e for e in events if "raw_timestamp" in e and start <= e["raw_timestamp"] < stop]
        selected = {kind: [e for e in window if e["kind"] == kind]
                    for kind in ("command", "report", "soc_timer", "delay")}
        if any(len(values) != 1 for values in selected.values()):
            raise ValueError("Request window has missing or ambiguous timing records")
        command, report, soc, delay = (selected[kind][0] for kind in selected)
        if (command["action"] != 3 or command["vdev"] != report["vdev"]
                or report["vdev"] != delay["vdev"]
                or not command["raw_timestamp"] <= report["raw_timestamp"] <= soc["raw_timestamp"] <= delay["raw_timestamp"]
                or request["qpc_request_completed"] >= stop):
            raise ValueError("Unexpected action, vdev, event order, or overlapping requests")
        expected_delay = (report["tsf_raw"] - soc["soc_timer_raw"]) & 0xFFFFFFFF
        if delay["tsf_delay_raw"] != expected_delay:
            raise ValueError("Delay differs from the modulo-32-bit counter difference")
        samples.append({
            "sample": index + 1,
            "tsf_raw": report["tsf_raw"], "soc_timer_raw": soc["soc_timer_raw"],
            "global_tsf_raw": soc["g_tsf_raw"], "report_qpc": report["raw_timestamp"],
            "host_request_duration_us": (request["qpc_request_completed"] - start) * 1e6 / frequency,
            "report_log_after_request_before_us": (report["raw_timestamp"] - start) * 1e6 / frequency,
            "report_log_after_observed_completion_us": (report["raw_timestamp"] - request["qpc_request_completed"]) * 1e6 / frequency,
        })
    result: dict[str, Any] = {
        "sample_count": len(samples), "qpc_frequency_hz": frequency,
        "correlation": "one command/report per nonoverlapping request window; no firmware transaction ID",
        "all_reports_logged_after_observed_completion": all(s["report_log_after_observed_completion_us"] > 0 for s in samples),
        "all_delay_low_words_match": True,
        "host_request_duration_us": distribution([s["host_request_duration_us"] for s in samples]),
        "report_log_after_observed_completion_us": distribution([s["report_log_after_observed_completion_us"] for s in samples]),
        "samples": samples, "absolute_accuracy_validated": False,
        "firmware_sampling_instant_validated": False,
    }
    if len(samples) > 1:
        elapsed = (samples[-1]["report_qpc"] - samples[0]["report_qpc"]) / frequency
        if elapsed <= 0:
            raise ValueError("Nonpositive observation span")
        result["observation_span_s"] = elapsed
        for field in ("tsf_raw", "soc_timer_raw"):
            differences = [samples[i][field] - samples[i - 1][field] for i in range(1, len(samples))]
            result[field + "_strictly_increasing"] = all(d > 0 for d in differences)
            # Raw ticks per host second, not a claim about hardware oscillator accuracy.
            result[field + "_endpoint_ticks_per_host_second"] = (samples[-1][field] - samples[0][field]) / elapsed
            result[field + "_adjacent_ticks_per_host_second"] = distribution([
                differences[i - 1] * frequency / (samples[i]["report_qpc"] - samples[i - 1]["report_qpc"])
                for i in range(1, len(samples))
            ])
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    session = json.loads((args.run / "session.json").read_text(encoding="utf-8-sig"))
    request_paths = sorted(args.run.glob("request-*.json"))
    if request_paths and (args.run / "request.json").exists():
        raise ValueError("Mixed single-request and series files; use one capture directory")
    if not request_paths:
        request_paths = [args.run / "request.json"]
    requests = [json.loads(path.read_text(encoding="utf-8-sig")) for path in request_paths]
    events = [json.loads(line) for line in (args.run / "raw-timing.jsonl").read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    result = analyze(requests, events, expected_count=session.get("SampleCount", 1))
    (args.run / "analysis-series.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "samples"}, indent=2))


if __name__ == "__main__":
    main()
