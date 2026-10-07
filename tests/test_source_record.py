"""Diagnostic source-envelope identity, extent and qualification regressions."""
import hashlib
import json
import struct
import unittest
from unittest.mock import patch

from research.export_contract.source_record import (
    SourceRecord, build_source_record, decode_broker_source, decode_source_record, operation_profile,
)


def event() -> bytes:
    return struct.pack("<I15I", 0x5005, (0x18B << 16) | 56, 7, 123, 1, 456, 2,
                       0, 1, 2, 0, 0, 0, 0, 0, 0)


def canonical(record: dict) -> bytes:
    return (json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")


def fixture(**changes) -> SourceRecord:
    arguments = dict(operation="qcom-tsf-wmi-reference-60-v1", provenance="fixture",
                     session=11, generation=7, source=9, sequence=1, source_loss_count=None,
                     continuity="unknown", host_interval=None)
    arguments.update(changes)
    return build_source_record(event(), **arguments)


def read(wire: bytes, **changes) -> SourceRecord:
    arguments = dict(expected_operation="qcom-tsf-wmi-reference-60-v1", expected_session=11,
                     expected_generation=7, expected_source=9, expected_sequence=1)
    arguments.update(changes)
    return decode_source_record(wire, **arguments)


def response(payload: bytes, *, origin: int = 1, losses: int = 0) -> bytes:
    raw = bytearray(96 + len(payload))
    struct.pack_into("<4sHHIIII", raw, 0, b"WHTR", 1, 96, len(raw), len(payload), origin, 0)
    struct.pack_into("<6Q", raw, 24, 11, 7, 9, 1, losses, 0)
    struct.pack_into("<IIQQ", raw, 72, 1 if origin == 1 else 3, 0, 2, 0)
    raw[96:] = payload
    return bytes(raw)


def consume(raw: bytes, **changes) -> dict:
    arguments = dict(expected_ticket=2, expected_session=11, expected_generation=7,
                     expected_source=9, expected_operation="qcom-tsf-wmi-reference-60-v1",
                     expected_sequence=1)
    arguments.update(changes)
    return decode_broker_source(raw, **arguments)


class SourceRecordTests(unittest.TestCase):
    def test_builder_rejects_unbounded_or_unknown_metadata_before_encoding(self):
        for change in (dict(provenance="x" * 10000), dict(continuity="x" * 10000),
                       dict(host_interval={str(i): i for i in range(100)}),
                       dict(host_interval=dict(meaning="callback-copy", qpc_frequency="1" * 10000, before="0", after="1")),
                       dict(transport_endpoint=True)):
            with self.subTest(change=list(change)), patch("research.export_contract.source_record._canonical") as encode:
                with self.assertRaises(ValueError):
                    fixture(**change)
                encode.assert_not_called()

    def test_owns_metadata_and_retains_unknowns_and_raw_counters(self):
        interval = dict(meaning="callback-copy", qpc_frequency="10000000", before="100", after="101")
        snapshot = fixture(host_interval=interval)
        interval["before"] = "999"
        decoded = read(snapshot.wire).diagnostic()
        self.assertEqual(decoded["host_interval"]["before"], "100")
        self.assertEqual(decoded["payload"]["hex"], event().hex())
        self.assertEqual(decoded["payload_diagnostic"]["reference_view"]["tsf_raw"], str(2**32 + 123))
        self.assertIsNone(decoded["source_loss_count"])
        self.assertIsNone(decoded["hardware_epoch"])
        self.assertIsNone(decoded["hardware_sampling_interval_qpc"])
        self.assertFalse(decoded["clock_input_eligible"])
        self.assertFalse(decoded["quarantine_release_qualified"])
        decoded["software_scope"]["session"] = "999"
        self.assertEqual(snapshot.diagnostic()["software_scope"]["session"], "11")
        profile = operation_profile("qcom-tsf-wmi-reference-60-v1")
        profile["producer"] = "changed"
        self.assertNotEqual(operation_profile(profile["id"])["producer"], "changed")

    def test_source_and_broker_identity_do_not_substitute_for_each_other(self):
        raw = fixture().wire
        for change in (dict(expected_session=12), dict(expected_generation=8), dict(expected_source=10),
                       dict(expected_sequence=2), dict(expected_operation="qcom-fixed-test-get-v1"),
                       dict(expected_sequence=True)):
            with self.subTest(change=change), self.assertRaises(ValueError):
                read(raw, **change)
        # Valid outer identity cannot mask a source record from another generation.
        with self.assertRaisesRegex(ValueError, "identity_mismatch"):
            consume(response(fixture(generation=8).wire))
        with self.assertRaisesRegex(ValueError, "provenance_mismatch"):
            consume(response(raw, origin=2))
        with self.assertRaises(ValueError):
            consume(response(raw), expected_ticket=3)

    def test_unknown_fields_false_claims_corruption_and_noncanonical_input_reject(self):
        base = json.loads(fixture().wire)
        changes = (("live_clock_eligible", True), ("hardware_epoch", "1"),
                   ("firmware_request_identity", "2"), ("firmware_identity", "known"),
                   ("driver_sha256", "0" * 64), ("profile_sha256", "0" * 64),
                   ("source_observation_sequence", True), ("source_loss_count", "00"),
                   ("continuity", "verified"), ("clock", dict(id=0, unit="ns", meaningful_bits=64)))
        for key, value in changes:
            data = dict(base, **{key: value})
            with self.subTest(key=key), self.assertRaises(ValueError):
                SourceRecord(canonical(data))
        for raw in (fixture().wire[:-2], fixture().wire + b"x", b"{}", b"[", b" " * 4097,
                    b'{"schema":"a","schema":"b"}', b"[" * 1500 + b"]" * 1500,
                    fixture().wire.replace(b'"source_loss_count":null', b'"source_loss_count":NaN'),
                    bytearray(fixture().wire)):
            with self.subTest(length=len(raw)), self.assertRaises(ValueError):
                SourceRecord(raw)
        for field, value in (("length", 63), ("sha256", "0" * 64), ("hex", "00" * 64)):
            changed = json.loads(fixture().wire)
            changed["payload"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                SourceRecord(canonical(changed))

    def test_header_semantics_still_checked_after_payload_digest_is_recomputed(self):
        base = json.loads(fixture().wire)
        for offset in (0, 4):
            raw = bytearray(event())
            raw[offset] ^= 1
            base["payload"] = dict(length=len(raw), hex=raw.hex(), sha256=hashlib.sha256(raw).hexdigest())
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                SourceRecord(canonical(base))
        with self.assertRaises(ValueError):
            fixture(operation="qcom-tsf-wmi-reference-48-v1")

    def test_reported_gaps_quarantine_but_zero_loss_does_not_qualify_continuity(self):
        unknown = consume(response(fixture().wire))
        self.assertIsNone(unknown["source"]["source_loss_count"])
        lost = consume(response(fixture(source_loss_count=1, continuity="gap-reported").wire))
        self.assertTrue(lost["quarantine_required"])
        self.assertTrue(consume(response(fixture().wire, losses=1))["quarantine_required"])
        with self.assertRaises(ValueError):
            fixture(source_loss_count=1)
        zero = consume(response(fixture(source_loss_count=0).wire))
        self.assertEqual(zero["source"]["continuity"], "unknown")
        self.assertFalse(zero["quarantine_release_qualified"])
        self.assertFalse(zero["clock_input_eligible"])

    def test_host_call_and_fixed_pattern_never_become_tsf_sampling_evidence(self):
        interval = dict(meaning="api-call", qpc_frequency="10000000", before="100", after="1765")
        control = build_source_record(bytes(range(1, 9)), operation="qcom-fixed-test-get-v1",
            provenance="replay-unqualified", session=11, generation=7, source=9, sequence=1,
            source_loss_count=None, continuity="unknown", host_interval=interval,
            capture_evidence_sha256=hashlib.sha256(b"synthetic control receipt").hexdigest())
        result = consume(response(control.wire, origin=2), expected_operation="qcom-fixed-test-get-v1",
                         expected_evidence_sha256=hashlib.sha256(b"synthetic control receipt").hexdigest())
        self.assertFalse(result["source"]["payload_diagnostic"]["contains_timestamp"])
        self.assertFalse(result["hardware_qpc_qualified"])
        for digest in (None, "0" * 64, "not-a-digest"):
            with self.subTest(digest=digest), self.assertRaises(ValueError):
                consume(response(control.wire, origin=2), expected_operation="qcom-fixed-test-get-v1",
                        expected_evidence_sha256=digest)
        tsf = fixture(host_interval=interval).diagnostic()
        self.assertIsNone(tsf["hardware_sampling_interval_qpc"])
        self.assertFalse(tsf["firmware_association_qualified"])
        for host in (dict(interval, meaning="hardware-latch"), dict(interval, meaning="callback-copy", after="99"),
                     dict(interval, meaning="callback-copy", qpc_frequency="0")):
            with self.subTest(host=host), self.assertRaises(ValueError):
                fixture(host_interval=host)

    def test_htc_profile_retains_transport_bytes_and_requires_expected_endpoint(self):
        trailer = b"\x01\x02\x03\x04"
        raw = struct.pack("<BBHBBBB", 2, 2, len(event()) + len(trailer), len(trailer), 0, 0, 0) + event() + trailer
        record = build_source_record(raw, operation="qcom-tsf-htc-reference-60-v1", provenance="fixture",
            session=11, generation=7, source=9, sequence=1, source_loss_count=None, continuity="unknown",
            host_interval=None, transport_endpoint=2)
        result = consume(response(record.wire), expected_operation="qcom-tsf-htc-reference-60-v1", expected_endpoint=2)
        self.assertEqual(result["source"]["payload_diagnostic"]["raw_htc_trailer_hex"], trailer.hex())
        for endpoint in (None, True, 0, 3):
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError):
                consume(response(record.wire), expected_operation="qcom-tsf-htc-reference-60-v1", expected_endpoint=endpoint)

    def test_both_reference_layouts_and_envelopes_have_positive_cases(self):
        old = struct.pack("<I12I", 0x5005, (0x18B << 16) | 44, 7, 123, 1, 456, 2, 0, 1, 2, 1, 0, 0)
        for size, wmi in ((48, old), (60, event())):
            for representation in ("wmi", "htc"):
                profile = f"qcom-tsf-{representation}-reference-{size}-v1"
                endpoint = 2 if representation == "htc" else None
                raw = struct.pack("<BBHBBBB", 2, 0, len(wmi), 0, 0, 0, 0) + wmi if endpoint else wmi
                with self.subTest(profile=profile):
                    record = build_source_record(raw, operation=profile, provenance="fixture", session=11,
                        generation=7, source=9, sequence=1, source_loss_count=None, continuity="unknown",
                        host_interval=None, transport_endpoint=endpoint)
                    result = consume(response(record.wire), expected_operation=profile, expected_endpoint=endpoint)
                    self.assertEqual(result["source"]["payload_diagnostic"]["received_event_bytes"], size + 4)
                    self.assertFalse(result["clock_input_eligible"])


if __name__ == "__main__":
    unittest.main()
