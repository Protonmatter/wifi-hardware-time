"""Synthetic rejection tests; no device access or hardware qualification."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import struct
import tempfile
import unittest

from research.acquisition import analyze_quts_registry as a

BASE = 0x180000000
DRIVER = r"{4d36e972-e325-11ce-bfc1-08002be10318}\0042"
PATH = "\\REGISTRY\\MACHINE\\SYSTEM\\ControlSet001\\Control\\Class\\" + DRIVER


def fixture():
    header = dict(kind="header", clock_type=1, pointer_size=8, frequency="10000000",
                  events_lost=0, buffers_lost=0)
    before = dict(status="Up", driver_version="1.0.4374.1300", driver_key=DRIVER,
                  processes=[dict(process_id=100, module_base=hex(BASE), sha256=a.QUTS_HASH)])
    run = dict(trace_started=True, trace_stopped=True, error=None,
               control_process_id=200, control_qpc_frequency="10000000")
    events = [a.Registry(1, 4, 4, 22, 0, 50, PATH),
              a.Registry(1000, 100, 101, 16, a.MISSING, 50, "QCDeviceControlFile"),
              a.Stack(1000, 100, 101, tuple(BASE + rva for rva in a.EXPECTED_RVAS))]
    controls = []
    for phase, offset in (("start", 10), ("end", 2000)):
        for i in range(10):
            name = "NetCfgInstanceId" if i % 2 == 0 else "QCDeviceControlFile"
            start = offset + i * 10
            controls.append(dict(phase=phase, pid=200, tid=201, name=name,
                                 before_qpc=str(start), after_qpc=str(start + 5),
                                 value_present=i % 2 == 0))
            events.append(a.Registry(start + 2, 200, 201, 16, 0 if i % 2 == 0 else a.MISSING, 50, name))
    return dict(header=header, events=events, before=before, after=deepcopy(before),
                run=run, controls=controls, health="Dropped event: 0\nEvents Lost: 0\n")


class AssociationTests(unittest.TestCase):
    def test_complete_controls_and_exact_stack_validate_only_query_callsite(self):
        result = a.analyze(**fixture())
        self.assertTrue(result["live_query_callsite_validated"])
        self.assertEqual(result["controls_matched"], 20)
        self.assertEqual(result["query_status_counts"], {"0xc0000034": 1})
        for field in ("conditional_branch_instruction_validated", "hardware_qpc_sampling_validated",
                      "firmware_event_delivery_validated"):
            self.assertFalse(result[field])

    def test_stack_must_match_original_qpc_pid_tid_and_all_addresses(self):
        for change in (dict(qpc=1001), dict(pid=101), dict(tid=102), dict(frames=(BASE + a.EXPECTED_RVAS[0],))):
            with self.subTest(change=change):
                f = fixture()
                f["events"][2] = replace(f["events"][2], **change)
                self.assertFalse(a.analyze(**f)["live_query_callsite_validated"])

    def test_duplicate_query_or_qualifying_stack_is_quarantined(self):
        for index in (1, 2):
            with self.subTest(index=index):
                f = fixture()
                f["events"].append(f["events"][index])
                self.assertFalse(a.analyze(**f)["live_query_callsite_validated"])

    def test_separate_kernel_stack_does_not_invalidate_one_exact_user_stack(self):
        f = fixture()
        f["events"].append(a.Stack(1000, 100, 101, (0xFFFF000000001234,)))
        self.assertTrue(a.analyze(**f)["live_query_callsite_validated"])

    def test_addresses_split_between_stacks_are_not_joined(self):
        f = fixture()
        stack = f["events"][2]
        f["events"][2] = replace(stack, frames=stack.frames[:1])
        f["events"].append(replace(stack, frames=stack.frames[1:]))
        self.assertFalse(a.analyze(**f)["live_query_callsite_validated"])

    def test_only_global_kcb_lifecycle_binds_key_not_openkey(self):
        for event in (replace(fixture()["events"][0], opcode=12),
                      replace(fixture()["events"][0], name=PATH[:-4] + "0043")):
            f = fixture()
            f["events"][0] = event
            self.assertEqual(a.analyze(**f)["target_queries"], 0)

    def test_deleted_reused_or_tied_key_is_rejected(self):
        for event in (a.Registry(999, 999, 999, 23, 0, 50, ""),
                      a.Registry(999, 999, 999, 22, 0, 50, PATH + "other"),
                      a.Registry(1000, 999, 999, 23, 0, 50, "")):
            f = fixture()
            f["events"].append(event)
            self.assertFalse(a.analyze(**f)["live_query_callsite_validated"])

    def test_delete_then_create_allows_new_key_generation(self):
        f = fixture()
        f["events"].extend([a.Registry(900, 999, 999, 23, 0, 50, ""),
                            a.Registry(901, 999, 999, 22, 0, 50, PATH)])
        self.assertTrue(a.analyze(**f)["live_query_callsite_validated"])

    def test_missing_start_end_or_late_control_does_not_qualify(self):
        for index in (0, 10):
            f = fixture()
            f["controls"].pop(index)
            self.assertFalse(a.analyze(**f)["capture_coverage_qualified"])
        f = fixture()
        f["events"][3] = replace(f["events"][3], qpc=9999)
        self.assertFalse(a.analyze(**f)["capture_coverage_qualified"])

    def test_loss_missing_health_and_lifecycle_reject(self):
        variants = []
        for field in ("events_lost", "buffers_lost"):
            f = fixture(); f["header"][field] = 1; variants.append(f)
        for health in ("", "Dropped event: 1\nEvents Lost: 0", "Dropped event: 0\nEvents Lost: 0\nEvents Lost: 0"):
            f = fixture(); f["health"] = health; variants.append(f)
        f = fixture(); f["after"]["status"] = "Down"; variants.append(f)
        f = fixture(); f["run"]["trace_stopped"] = False; variants.append(f)
        f = fixture(); f["run"]["control_qpc_frequency"] = "1"; variants.append(f)
        for f in variants:
            self.assertFalse(a.analyze(**f)["capture_coverage_qualified"])

    def test_control_intervals_and_image_identity_reject(self):
        for mutate in (lambda f: f["controls"][1].update(before_qpc="15"),
                       lambda f: f["controls"][0].update(after_qpc="10"),
                       lambda f: f["controls"][0].update(pid=100),
                       lambda f: f["before"]["processes"][0].update(sha256="0" * 64)):
            f = fixture(); mutate(f)
            with self.assertRaises(ValueError):
                a.analyze(**f)


class DecodeTests(unittest.TestCase):
    def row(self, kind="registry"):
        if kind == "registry":
            payload = struct.pack("<QIIQ", 88, a.MISSING, 0, 50) + "QCDeviceControlFile\0".encode("utf-16le")
        else:
            payload = struct.pack("<QIIQ", 99, 100, 101, BASE)
        return dict(kind=kind, timestamp="1234", pid=4, tid=5, flags=64,
                    version=2, opcode=16 if kind == "registry" else 32, payload=payload.hex())

    def test_stack_uses_original_event_identity_not_stack_delivery(self):
        self.assertEqual(a.decode(self.row("stack")), a.Stack(99, 100, 101, (BASE,)))
        self.assertEqual(a.decode(self.row()).name, "QCDeviceControlFile")

    def test_malformed_payloads_versions_and_widths_reject(self):
        row = self.row()
        for change in (dict(version=1), dict(flags=32), dict(flags=96), dict(payload="zz"),
                       dict(payload=row["payload"][:-2]), dict(payload=row["payload"][:-4]),
                       dict(payload="00" * 24 + "00d80000"), dict(opcode=1), dict(kind="unknown"),
                       dict(payload="00" * 24 + "00000000")):
            with self.subTest(change=change), self.assertRaises(ValueError):
                a.decode(dict(row, **change))
        for payload in ("00" * 16, "00" * 25, "00" * (16 + 193 * 8)):
            with self.assertRaises(ValueError):
                a.decode(dict(self.row("stack"), payload=payload))

    def test_integer_never_rounds_or_accepts_out_of_range(self):
        self.assertEqual(a.integer(str(2**64 - 1)), 2**64 - 1)
        for value in (True, 1.0, -1, "1.0", "-1", 2**64, str(2**64)):
            with self.assertRaises(ValueError):
                a.integer(value)

    def test_export_footer_count_clock_and_duplicate_fields_are_required(self):
        header = fixture()["header"]
        footer = dict(kind="summary", process_status=0, close_status=0, bound_failure=False, exported=1)
        valid = [header, self.row(), footer]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            def write(items):
                path.write_text("\n".join(json.dumps(item) for item in items), encoding="utf-8")
            write(valid)
            self.assertEqual(len(a.read_export(path)[1]), 1)
            for items in (valid[:-1], [header, self.row(), dict(footer, exported=2)],
                          [header, self.row(), dict(footer, bound_failure=True)],
                          [header, self.row(), dict(footer, process_status=5)],
                          [dict(header, clock_type=2), self.row(), footer],
                          [dict(header, pointer_size=4), self.row(), footer]):
                write(items)
                with self.assertRaises(ValueError):
                    a.read_export(path)
            path.write_text('{"field":1,"field":2}', encoding="utf-8")
            with self.assertRaises(ValueError):
                a.read_json(path)


if __name__ == "__main__":
    unittest.main()
