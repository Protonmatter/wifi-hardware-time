import copy
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from analyze_tsf_series import analyze


def fixture():
    requests, events = [], [dict(kind="header", clock_type=1, perf_frequency_hz=10000000, events_lost=0, buffers_lost=0)]
    for i in range(3):
        base = 10000000 * (i + 1)
        tsf, soc = 1000000 * (i + 1), 2000000 * (i + 1)
        requests.append(dict(qpc_request_before=base, qpc_request_completed=base + 100,
                             qpc_frequency_hz=10000000, success=True, handle_closed=True,
                             driver_sha256="synthetic-fixture", interface_index=7,
                             command="tsf_read_value", firmware_action=3))
        events.extend([
            dict(kind="command", raw_timestamp=base + 50, vdev=0, action=3),
            dict(kind="report", raw_timestamp=base + 1000, vdev=0, tsf_raw=tsf),
            dict(kind="soc_timer", raw_timestamp=base + 1001, soc_timer_raw=soc, g_tsf_raw=0),
            dict(kind="delay", raw_timestamp=base + 1002, vdev=0, tsf_delay_raw=(tsf - soc) & 0xFFFFFFFF),
        ])
    events.append(dict(kind="summary", process_status=0, close_status=0))
    return requests, events


class SeriesTests(unittest.TestCase):
    def test_exact_synthetic_rates_and_wrap_arithmetic(self):
        result = analyze(*fixture())
        self.assertEqual(result["sample_count"], 3)
        self.assertEqual(result["tsf_raw_endpoint_ticks_per_host_second"], 1000000)
        self.assertEqual(result["soc_timer_raw_endpoint_ticks_per_host_second"], 2000000)
        self.assertEqual(result["report_log_after_observed_completion_us"]["median"], 90)
        self.assertFalse(result["absolute_accuracy_validated"])

    def test_trace_loss_and_frequency_mismatch_rejected(self):
        requests, events = fixture()
        bad = copy.deepcopy(events)
        bad[0]["events_lost"] = 1
        with self.assertRaises(ValueError): analyze(requests, bad)
        requests[0]["qpc_frequency_hz"] = 1
        with self.assertRaises(ValueError): analyze(requests, events)

    def test_missing_and_duplicate_report_rejected(self):
        requests, events = fixture()
        with self.assertRaises(ValueError): analyze(requests, events[:2] + events[3:])
        with self.assertRaises(ValueError): analyze(requests, events + [events[2]])

    def test_wrong_vdev_or_delay_rejected(self):
        requests, events = fixture()
        bad = copy.deepcopy(events)
        bad[2]["vdev"] = 1
        with self.assertRaises(ValueError): analyze(requests, bad)
        events[4]["tsf_delay_raw"] = 7
        with self.assertRaises(ValueError): analyze(requests, events)

    def test_completion_after_report_is_reported_not_assumed(self):
        requests, events = fixture()
        requests[0]["qpc_request_completed"] += 2000
        self.assertFalse(analyze(requests, events)["all_reports_logged_after_observed_completion"])

    def test_partial_series_rejected(self):
        requests, events = fixture()
        with self.assertRaises(ValueError): analyze(requests, events, expected_count=12)
        self.assertEqual(analyze(requests, events, expected_count=3)["sample_count"], 3)

    def test_mixed_adapter_or_build_rejected(self):
        requests, events = fixture()
        for field, value in (("interface_index", 8), ("driver_sha256", "other-build")):
            bad = copy.deepcopy(requests)
            bad[1][field] = value
            with self.assertRaises(ValueError): analyze(bad, events)

    def test_extra_delay_outside_request_window_rejected(self):
        requests, events = fixture()
        extra = dict(events[4], raw_timestamp=1)
        with self.assertRaises(ValueError): analyze(requests, events + [extra])


if __name__ == "__main__":
    unittest.main()
