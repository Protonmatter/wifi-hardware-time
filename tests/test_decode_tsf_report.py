"""Synthetic structural/ownership checks, never a firmware acquisition test."""
from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

from research.tsf.decode_tsf_report import (
    EventSnapshot, HtcEventSnapshot, ReportSnapshot, decode_event, decode_htc_event, decode_report,
)

ROOT = Path(__file__).resolve().parents[1]


def fixture(size: int = 60, *, flag: int = 1, word9: int = 0) -> bytes:
    # Synthetic recognizable high/low words; these are not hardware readings.
    words = [(0x18B << 16) | (size - 4), 7, 0x89ABCDEF, 0xFEDCBA98,
             0x76543210, 0x12345678, 0, flag, 2, word9, 0, 0]
    if size == 60:
        words.extend((0xFFFFFFFF, 0xFFFFFFFF, 0))
    return struct.pack(f"<{len(words)}I", *words)


def decode(data: bytes | bytearray, **overrides: object) -> ReportSnapshot:
    args = dict(event_id=0x5005, reference_layout="reference-60",
                origin="fixture", representation="wire")
    args.update(overrides)
    return decode_report(data, **args)


class OwnedTsfReportTests(unittest.TestCase):
    def test_u64_values_survive_json_and_zero_clock_id_is_not_missing(self) -> None:
        result = decode(fixture()).diagnostic()
        view = json.loads(json.dumps(result))["reference_view"]
        self.assertEqual(view["tsf_raw"], str(0xFEDCBA9889ABCDEF))
        self.assertEqual(view["qtimer_raw"], str(0x1234567876543210))
        self.assertEqual(view["tqm_raw"], str(2**64 - 1))
        self.assertEqual(view["global_tsf_raw"], "0")
        self.assertEqual(view["candidate_tsf_id"], 0)
        self.assertEqual(view["candidate_mac_id"], 2)
        self.assertEqual(view["candidate_report_class"], "tsf")
        self.assertEqual(bytes.fromhex(result["raw_tlv_hex"]), fixture())
        self.assertEqual(result["present_word_offsets"], list(range(4, 60, 4)))

    def test_legacy_word9_is_validity_and_never_a_report_class(self) -> None:
        old = decode(fixture(48, flag=0, word9=1), reference_layout="reference-48").diagnostic()
        new = decode(fixture(flag=0, word9=1)).diagnostic()
        self.assertEqual(old["reference_view"]["candidate_mac_id"], 2)
        self.assertIsNone(new["reference_view"]["candidate_mac_id"])
        self.assertEqual(old["reference_view"]["candidate_report_class"], "not-defined-by-this-layout")
        self.assertEqual(new["reference_view"]["candidate_report_class"], "uplink-delay")
        self.assertNotIn("tqm_raw", old["reference_view"])
        self.assertNotIn(48, old["present_word_offsets"])

    def test_unrecognized_flags_preserve_raw_values_without_candidate_identity(self) -> None:
        for flag in (0, 2, 0xFFFFFFFF):
            with self.subTest(flag=flag):
                view = decode(fixture(flag=flag, word9=55)).diagnostic()["reference_view"]
                self.assertEqual(view["tsf_id_valid_raw"], flag)
                self.assertIsNone(view["candidate_tsf_id"])
                self.assertIsNone(view["candidate_mac_id"])
                self.assertEqual(view["candidate_report_class"], "unknown")

    def test_snapshot_owns_bytes_and_each_diagnostic_is_detached(self) -> None:
        source = bytearray(fixture())
        snapshot = decode(source)
        source[:] = bytes(60)
        first = snapshot.diagnostic()
        first["reference_view"]["tsf_raw"] = "changed"
        first["present_word_offsets"].clear()
        self.assertEqual(snapshot.raw_tlv, fixture())
        self.assertNotEqual(snapshot.diagnostic()["reference_view"]["tsf_raw"], "changed")
        self.assertEqual(len(snapshot.diagnostic()["present_word_offsets"]), 14)
        with self.assertRaises(FrozenInstanceError):
            snapshot.raw_tlv = b""

    def test_reject_partial_extra_padded_wrong_tag_and_wrong_length(self) -> None:
        wrong_tag = bytearray(fixture())
        struct.pack_into("<I", wrong_tag, 0, (0x18C << 16) | 56)
        wrong_length = bytearray(fixture())
        struct.pack_into("<I", wrong_length, 0, (0x18B << 16) | 44)
        for data in (b"", fixture()[:-1], fixture() + b"\0", fixture(48) + bytes(12),
                     wrong_tag, wrong_length, memoryview(fixture()), "not bytes"):
            with self.subTest(data_type=type(data)), self.assertRaises(ValueError):
                decode(data)

    def test_reject_wrong_event_implicit_layout_and_normalized_input(self) -> None:
        for kwargs in ({"event_id": 0x5012}, {"event_id": True}, {"event_id": 20485.0},
                       {"reference_layout": "auto"}, {"reference_layout": []},
                       {"reference_layout": "reference-48"}, {"origin": "qualified"},
                       {"origin": None}, {"representation": "normalized"},
                       {"representation": True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                decode(fixture(), **kwargs)

    def test_constructor_cannot_bypass_immutable_structure_validation(self) -> None:
        for data, layout, origin in ((bytearray(fixture()), "reference-60", "fixture"),
                                     (b"", "reference-60", "fixture"),
                                     (fixture(), "auto", "fixture"),
                                     (fixture(), "reference-60", "qualified")):
            with self.subTest(layout=layout), self.assertRaises(ValueError):
                ReportSnapshot(data, layout, origin)

    def test_rewritten_padding_cannot_attest_wire_origin_or_qualify_clocks(self) -> None:
        raw = bytearray(fixture(48) + bytes(12))
        # Rewriting the header can mimic a real 60-byte record. File analysis
        # cannot detect that fabrication; it must never attest live provenance.
        struct.pack_into("<I", raw, 0, (0x18B << 16) | 56)
        result = decode(raw, origin="captured-unqualified").diagnostic()
        for field in ("firmware_schema_qualified", "source_publication_qualified",
                      "response_association_qualified", "simultaneous_sampling_qualified",
                      "hardware_qpc_qualified", "live_clock_eligible"):
            self.assertIs(result[field], False)
        for field in ("counter_unit", "meaningful_counter_bits", "epoch", "host_sampling_interval"):
            self.assertIsNone(result[field])
        self.assertNotIn("action", result)

    def test_cli_diagnostic_succeeds_but_clock_admission_rejects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "synthetic-report.bin"
            path.write_bytes(fixture())
            command = [sys.executable, str(ROOT / "research/tsf/decode_tsf_report.py"), str(path),
                       "--event-id", "0x5005", "--reference-layout", "reference-60",
                       "--origin", "fixture", "--representation", "wire"]
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(json.loads(result.stdout)["live_clock_eligible"])
            result = subprocess.run(command + ["--require-clock-input"], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertIn("Clock input remains unqualified", result.stderr)
            path.unlink()
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")


class OwnedTsfEventTests(unittest.TestCase):
    def decode(self, raw: bytes | bytearray, **overrides: object) -> EventSnapshot:
        args = dict(event_id=0x5005, reference_layout="reference-60",
                    origin="fixture", representation="event-wire")
        args.update(overrides)
        return decode_event(raw, **args)

    def test_preserves_original_header_length_and_full_event_after_source_reuse(self) -> None:
        original = struct.pack("<I", 0xA5005005) + fixture()
        source = bytearray(original)
        snapshot = self.decode(source)
        source[:] = bytes(64)
        result = snapshot.diagnostic()
        self.assertEqual(snapshot.raw_event, original)
        self.assertEqual(bytes.fromhex(result["raw_wmi_event_hex"]), original)
        self.assertEqual(result["wmi_header_upper_byte_raw"], 0xA5)
        self.assertEqual(result["received_event_bytes"], 64)
        self.assertEqual(result["original_payload_bytes"], 60)
        self.assertIsNone(result["host_time_observations"])
        self.assertIsNone(result["host_sampling_interval"])
        self.assertFalse(result["response_association_qualified"])
        self.assertFalse(result["live_clock_eligible"])
        result["reference_view"]["tsf_raw"] = "mutated"
        self.assertNotEqual(snapshot.diagnostic()["reference_view"]["tsf_raw"], "mutated")

    def test_older_original_event_and_normalized_copy_are_distinct(self) -> None:
        original = struct.pack("<I", 0x5005) + fixture(48)
        result = self.decode(original, reference_layout="reference-48").diagnostic()
        self.assertEqual(result["received_event_bytes"], 52)
        self.assertEqual(result["original_payload_bytes"], 48)
        self.assertNotIn("tqm_raw", result["reference_view"])
        # This is a simulated padding operation, not execution of vendor code.
        with self.assertRaisesRegex(ValueError, "length mismatch"):
            self.decode(original + bytes(12))

    def test_reject_mismatched_headers_partial_extra_normalized_and_mutable_constructor(self) -> None:
        original = struct.pack("<I", 0x5005) + fixture()
        for raw, kwargs in ((original[:-1], {}), (original + b"\0", {}),
                            (struct.pack("<I", 0x5012) + fixture(), {}),
                            (struct.pack("<I", 0x5005), {}), (fixture(), {}),
                            (original, {"event_id": 0x5012}),
                            (original, {"event_id": True}),
                            (original, {"representation": "normalized"}),
                            (original, {"reference_layout": "auto"}),
                            (memoryview(original), {})):
            with self.subTest(kwargs=kwargs, size=len(raw)), self.assertRaises(ValueError):
                self.decode(raw, **kwargs)
        with self.assertRaises(ValueError):
            EventSnapshot(bytearray(original), "reference-60", "fixture")

    def test_cli_event_wire_mode_is_diagnostic_and_clock_admission_still_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "synthetic-event.bin"
            path.write_bytes(struct.pack("<I", 0x5005) + fixture())
            command = [sys.executable, str(ROOT / "research/tsf/decode_tsf_report.py"), str(path),
                       "--event-id", "0x5005", "--reference-layout", "reference-60",
                       "--origin", "fixture", "--representation", "event-wire"]
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["schema"], "wht/owned-tsf-event-diagnostic-v1")
            result = subprocess.run(command + ["--require-clock-input"], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            path.write_bytes(path.read_bytes() + b"\0")
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")


class OwnedHtcEventTests(unittest.TestCase):
    def fixture(self, *, trailer: bytes = b"", endpoint: int = 2, size: int = 60) -> bytes:
        event = struct.pack("<I", 0xA5005005) + fixture(size)
        header = bytearray(8)
        header[0] = endpoint
        header[1] = 2 if trailer else 0
        struct.pack_into("<H", header, 2, len(event) + len(trailer))
        header[4] = len(trailer)
        return bytes(header) + event + trailer

    def decode(self, data: bytes | bytearray, **overrides: object) -> HtcEventSnapshot:
        args = dict(event_id=0x5005, reference_layout="reference-60", origin="fixture",
                    representation="htc-wire", expected_endpoint=2)
        args.update(overrides)
        return decode_htc_event(data, **args)

    def test_complete_envelope_owns_header_event_and_opaque_trailer(self) -> None:
        trailer = bytes.fromhex("0104000002010000")
        original = self.fixture(trailer=trailer)
        source = bytearray(original)
        snapshot = self.decode(source)
        source[:] = bytes(len(source))
        result = snapshot.diagnostic()
        self.assertEqual(bytes.fromhex(result["raw_htc_envelope_hex"]), original)
        self.assertEqual(bytes.fromhex(result["raw_htc_trailer_hex"]), trailer)
        self.assertEqual(result["received_htc_bytes"], 80)
        self.assertEqual(result["advertised_htc_payload_bytes"], 72)
        self.assertEqual(result["received_event_bytes"], 64)
        self.assertEqual(result["original_payload_bytes"], 60)
        self.assertEqual(result["wmi_header_upper_byte_raw"], 0xA5)
        self.assertTrue(result["transport_envelope_present"])
        for field in ("live_clock_eligible", "endpoint_association_qualified",
                      "trailer_semantics_qualified", "header_flags_semantics_qualified",
                      "source_contiguity_qualified", "hardware_qpc_qualified"):
            self.assertFalse(result[field])
        self.assertIsNone(result["host_sampling_interval"])

    def test_rejects_aggregate_length_mismatch_partial_and_extra_bytes(self) -> None:
        good = self.fixture()
        short_header_length = bytearray(good)
        struct.pack_into("<H", short_header_length, 2, 60)
        long_header_length = bytearray(good)
        struct.pack_into("<H", long_header_length, 2, 68)
        for raw in (good[:-1], good + b"\0", short_header_length, long_header_length,
                    b"", bytes(328), [good[:8], good[8:]]):
            with self.subTest(kind=type(raw)), self.assertRaises(ValueError):
                self.decode(raw)

    def test_declared_endpoint_does_not_allow_zero_mismatch_or_coercion(self) -> None:
        for endpoint in (0, 1, 9, -1, True, 2.0, None):
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError):
                self.decode(self.fixture(), expected_endpoint=endpoint)
        with self.assertRaises(ValueError):
            self.decode(self.fixture(endpoint=0))
        with self.assertRaises(ValueError):
            HtcEventSnapshot(bytearray(self.fixture()), 2, "reference-60", "fixture")

    def test_trailer_extent_rejects_and_maximum_opaque_trailer_preserves(self) -> None:
        for size in (0, 1, 3, 65):
            raw = bytearray(self.fixture())
            raw[1] = 2
            raw[4] = size
            with self.subTest(size=size), self.assertRaises(ValueError):
                self.decode(raw)
        trailer = bytes(range(255))
        result = self.decode(self.fixture(trailer=trailer)).diagnostic()
        self.assertEqual(result["htc_trailer_bytes"], 255)
        self.assertEqual(bytes.fromhex(result["raw_htc_trailer_hex"]), trailer)
        self.assertFalse(result["trailer_semantics_qualified"])

    def test_uninterpreted_flags_and_unflagged_control_byte_are_retained(self) -> None:
        raw = bytearray(self.fixture(size=48))
        raw[1] = 0x80  # No trailer flag; do not invent semantics for other bits.
        raw[4] = 99
        result = self.decode(raw, reference_layout="reference-48").diagnostic()
        self.assertEqual(result["htc_flags_raw"], 0x80)
        self.assertEqual(result["htc_trailer_bytes"], 0)
        self.assertEqual(bytes.fromhex(result["raw_htc_header_hex"])[4], 99)
        self.assertFalse(result["header_flags_semantics_qualified"])

    def test_inner_event_and_representation_cannot_bypass_validation(self) -> None:
        raw = bytearray(self.fixture())
        struct.pack_into("<I", raw, 8, 0x5012)
        with self.assertRaises(ValueError):
            self.decode(raw)
        for kwargs in ({"event_id": 0x5012}, {"representation": "event-wire"},
                       {"reference_layout": "auto"}, {"origin": "qualified"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.decode(self.fixture(), **kwargs)

    def test_cli_requires_endpoint_and_keeps_clock_gate_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "synthetic-htc.bin"
            path.write_bytes(self.fixture())
            command = [sys.executable, str(ROOT / "research/tsf/decode_tsf_report.py"), str(path),
                       "--event-id", "0x5005", "--reference-layout", "reference-60",
                       "--origin", "fixture", "--representation", "htc-wire"]
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 2)
            command.extend(("--expected-endpoint", "2"))
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["schema"], "wht/owned-tsf-htc-diagnostic-v1")
            result = subprocess.run(command + ["--require-clock-input"], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
