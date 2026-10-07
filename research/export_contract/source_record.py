"""Bound operation metadata and original bytes for diagnostic broker replay.

No acquisition, filesystem/network access, installed-driver ABI or clock grant.
Canonical UTF-8 JSON fits the broker's existing opaque payload. Hashes identify
supplied content; they do not authenticate a producer or make its claims true.
Unknown firmware, clock and sampling properties remain explicit null values.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any

from research.export_contract.read_raw_response import MAX_PAYLOAD, decode_response
from research.tsf.decode_tsf_report import MAX_HTC_BYTES, decode_event, decode_htc_event
from research.tsf.qualcomm_protocol import QUALIFIED_SHA256

SCHEMA = "wht/source-operation-record/v1"
_PROFILE_LAYOUTS = (("qcom-fixed-test-get-v1", None),
                    ("qcom-tsf-wmi-reference-48-v1", "reference-48"),
                    ("qcom-tsf-wmi-reference-60-v1", "reference-60"),
                    ("qcom-tsf-htc-reference-48-v1", "reference-48"),
                    ("qcom-tsf-htc-reference-60-v1", "reference-60"))
_FIELDS = {"schema", "operation_profile", "profile_sha256", "provenance", "driver_sha256",
           "software_scope", "source_observation_sequence", "source_loss_count", "continuity",
           "firmware_identity", "firmware_request_identity", "hardware_epoch", "clock",
           "host_interval", "transport_endpoint", "capture_evidence_sha256", "payload"}


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def operation_profile(name: str) -> dict[str, Any]:
    """Return a detached description. This is code-defined scope, not attestation."""
    if type(name) is not str or name not in dict(_PROFILE_LAYOUTS):
        raise ValueError("unsupported_operation_profile")
    layout = dict(_PROFILE_LAYOUTS)[name]
    fixed = layout is None
    return dict(
        id=name, profile_version=1,
        entry_route="saved bytes through user-mode broker",
        original_entry_route="WlanDeviceServiceCommand" if fixed else None,
        framing=("eight fixed bytes" if fixed else "original HTC envelope, WMI header, TLV and opaque trailer"
                 if "-htc-" in name else "four-byte WMI header plus original TLV"),
        selector="24364cfe-2ae8-4ed5-9643-a061f700ad5f/opcode-1" if fixed else "WMI event 0x5005",
        selector_precedence="matched test-service handler" if fixed else "not a callable request selector",
        state_effects="replay has no device effects",
        original_state_effects="fixed test-data construction; selected path has no firmware command" if fixed else None,
        producer="driver test literal in inspected path" if fixed else "supplied TSF event, producer unattested",
        returned_bytes="01 through 08" if fixed else layout,
        completion_meaning="broker application read completed; no firmware sampling implication",
        live_source_connected=False, complete_timing_operation_qualified=False,
    )


def _keys(value: Any, expected: set[str]) -> None:
    if type(value) is not dict or len(value) != len(expected) or set(value) != expected:
        raise ValueError("unsupported_or_missing_fields")


def _uint(value: Any, *, positive: bool = False) -> int:
    if type(value) is not str or not re.fullmatch(r"0|[1-9][0-9]{0,19}", value):
        raise ValueError("noncanonical_uint64")
    number = int(value)
    if number > 2**64 - 1 or (positive and not number):
        raise ValueError("uint64_out_of_range")
    return number


def _number(value: Any, *, positive: bool = False) -> str:
    if type(value) is not int or not (1 if positive else 0) <= value <= 2**64 - 1:
        raise ValueError("require_uint64_integer")
    return str(value)


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def _host_interval(host: Any) -> None:
    if host is None:
        return
    _keys(host, {"meaning", "qpc_frequency", "before", "after"})
    if host["meaning"] not in ("api-call", "callback-copy", "replay-processing"):
        raise ValueError("unsupported_host_observation")
    _uint(host["qpc_frequency"], positive=True)
    if _uint(host["after"]) < _uint(host["before"]):
        raise ValueError("reversed_host_interval")


def _evidence_digest(value: Any, provenance: str) -> None:
    if value is None:
        if provenance == "replay-unqualified":
            raise ValueError("replay_requires_capture_evidence_digest")
    elif type(value) is not str or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("invalid_capture_evidence_digest")


def _parse(wire: bytes) -> dict[str, Any]:
    if type(wire) is not bytes or not 1 <= len(wire) <= MAX_PAYLOAD:
        raise ValueError("require_bounded_immutable_source_record")
    try:
        record = json.loads(wire.decode("ascii"), object_pairs_hook=_unique)
        _keys(record, _FIELDS)
        if _canonical(record) != wire:
            raise ValueError("noncanonical_source_record")
    except (UnicodeError, RecursionError, OverflowError) as error:
        raise ValueError("invalid_source_record_encoding") from error
    if record["schema"] != SCHEMA or record["driver_sha256"] != QUALIFIED_SHA256:
        raise ValueError("unsupported_schema_or_driver")
    profile = operation_profile(record["operation_profile"])
    if record["profile_sha256"] != hashlib.sha256(_canonical(profile)).hexdigest():
        raise ValueError("operation_profile_digest_mismatch")
    if record["provenance"] not in ("fixture", "replay-unqualified"):
        raise ValueError("unsupported_provenance")
    _evidence_digest(record["capture_evidence_sha256"], record["provenance"])
    _keys(record["software_scope"], {"session", "generation", "source"})
    for value in record["software_scope"].values():
        _uint(value, positive=True)
    _uint(record["source_observation_sequence"], positive=True)
    loss = record["source_loss_count"]
    if loss is not None:
        _uint(loss)
    if record["continuity"] not in ("unknown", "gap-reported"):
        raise ValueError("unsupported_continuity_claim")
    if loss is not None and int(loss) > 0 and record["continuity"] != "gap-reported":
        raise ValueError("loss_requires_gap_disposition")
    for field in ("firmware_identity", "firmware_request_identity", "hardware_epoch"):
        if record[field] is not None:
            raise ValueError("unsupported_firmware_identity_claim")
    if record["clock"] != dict(id=None, unit=None, meaningful_bits=None):
        raise ValueError("unsupported_clock_semantics")
    _host_interval(record["host_interval"])
    payload = record["payload"]
    _keys(payload, {"length", "sha256", "hex"})
    if type(payload["length"]) is not int or not 1 <= payload["length"] <= MAX_HTC_BYTES:
        raise ValueError("unsupported_original_payload_size")
    if type(payload["hex"]) is not str or not re.fullmatch(r"[0-9a-f]+", payload["hex"]) or len(payload["hex"]) != 2 * payload["length"]:
        raise ValueError("invalid_original_bytes")
    raw = bytes.fromhex(payload["hex"])
    if hashlib.sha256(raw).hexdigest() != payload["sha256"]:
        raise ValueError("payload_digest_mismatch")
    layout = dict(_PROFILE_LAYOUTS)[profile["id"]]
    htc = "-htc-" in profile["id"]
    endpoint = record["transport_endpoint"]
    if htc:
        if type(endpoint) is not int or not 1 <= endpoint <= 8:
            raise ValueError("require_explicit_transport_endpoint")
    elif endpoint is not None:
        raise ValueError("unexpected_transport_endpoint")
    if layout is None:
        if raw != bytes(range(1, 9)):
            raise ValueError("fixed_control_payload_mismatch")
    else:
        _decode_payload(record)
    return record


def _decode_payload(record: dict[str, Any]) -> dict[str, Any]:
    layout = dict(_PROFILE_LAYOUTS)[record["operation_profile"]]
    if layout is None:
        return dict(kind="fixed-test-pattern", contains_timestamp=False)
    raw = bytes.fromhex(record["payload"]["hex"])
    arguments = dict(event_id=0x5005, reference_layout=layout,
                     origin="fixture" if record["provenance"] == "fixture" else "captured-unqualified")
    if "-htc-" in record["operation_profile"]:
        return decode_htc_event(raw, representation="htc-wire", expected_endpoint=record["transport_endpoint"],
                                **arguments).diagnostic()
    return decode_event(raw, representation="event-wire", **arguments).diagnostic()


@dataclass(frozen=True)
class SourceRecord:
    wire: bytes

    def __post_init__(self) -> None:
        _parse(self.wire)

    def diagnostic(self) -> dict[str, Any]:
        record = _parse(self.wire)
        decoded = _decode_payload(record)
        record.update(operation=operation_profile(record["operation_profile"]),
                      payload_diagnostic=decoded,
                      source_record_sha256=hashlib.sha256(self.wire).hexdigest(),
                      source_assertions_authenticated=False, source_copy_qualified=False,
                      firmware_association_qualified=False, hardware_qpc_qualified=False,
                      clock_input_eligible=False, freshness="unknown", sample_age_ns=None,
                      hardware_sampling_interval_qpc=None,
                      quarantine_release_qualified=False,
                      quarantine_required=record["continuity"] == "gap-reported")
        return record


def build_source_record(raw: bytes, *, operation: str, provenance: str, session: int,
                        generation: int, source: int, sequence: int,
                        source_loss_count: int | None, continuity: str,
                        host_interval: dict[str, str] | None, transport_endpoint: int | None = None,
                        capture_evidence_sha256: str | None = None) -> SourceRecord:
    """Inputs must remain stable during the call; never retain a caller's mapping."""
    if type(raw) is not bytes or not 1 <= len(raw) <= MAX_HTC_BYTES:
        raise ValueError("require_bounded_immutable_original_bytes")
    if type(provenance) is not str or provenance not in ("fixture", "replay-unqualified"):
        raise ValueError("unsupported_provenance")
    if type(continuity) is not str or continuity not in ("unknown", "gap-reported"):
        raise ValueError("unsupported_continuity_claim")
    _evidence_digest(capture_evidence_sha256, provenance)
    _host_interval(host_interval)
    if transport_endpoint is not None and (type(transport_endpoint) is not int or not 1 <= transport_endpoint <= 8):
        raise ValueError("invalid_transport_endpoint")
    profile = operation_profile(operation)
    record = dict(schema=SCHEMA, operation_profile=operation,
        profile_sha256=hashlib.sha256(_canonical(profile)).hexdigest(), provenance=provenance,
        driver_sha256=QUALIFIED_SHA256,
        software_scope=dict(session=_number(session, positive=True), generation=_number(generation, positive=True),
                            source=_number(source, positive=True)),
        source_observation_sequence=_number(sequence, positive=True),
        source_loss_count=None if source_loss_count is None else _number(source_loss_count), continuity=continuity,
        firmware_identity=None, firmware_request_identity=None, hardware_epoch=None,
        clock=dict(id=None, unit=None, meaningful_bits=None), host_interval=host_interval,
        transport_endpoint=transport_endpoint,
        capture_evidence_sha256=capture_evidence_sha256,
        payload=dict(length=len(raw), sha256=hashlib.sha256(raw).hexdigest(), hex=raw.hex()))
    return SourceRecord(_canonical(record))


def decode_source_record(wire: bytes, *, expected_operation: str, expected_session: int,
                         expected_generation: int, expected_source: int,
                         expected_sequence: int, expected_endpoint: int | None = None,
                         expected_evidence_sha256: str | None = None) -> SourceRecord:
    source = SourceRecord(wire)
    value = source.diagnostic()
    _evidence_digest(expected_evidence_sha256, value["provenance"])
    operation_profile(expected_operation)
    if "-htc-" in expected_operation:
        if type(expected_endpoint) is not int or not 1 <= expected_endpoint <= 8:
            raise ValueError("require_expected_transport_endpoint")
    elif expected_endpoint is not None:
        raise ValueError("unexpected_expected_endpoint")
    scope = dict(session=_number(expected_session, positive=True), generation=_number(expected_generation, positive=True),
                 source=_number(expected_source, positive=True))
    if (value["operation_profile"] != expected_operation or value["software_scope"] != scope
            or value["source_observation_sequence"] != _number(expected_sequence, positive=True)
            or value["transport_endpoint"] != expected_endpoint
            or value["capture_evidence_sha256"] != expected_evidence_sha256):
        raise ValueError("source_operation_or_software_identity_mismatch")
    return source


def decode_broker_source(response: bytes, *, expected_ticket: int, expected_session: int,
                         expected_generation: int, expected_source: int,
                         expected_operation: str, expected_sequence: int,
                         expected_endpoint: int | None = None,
                         expected_evidence_sha256: str | None = None) -> dict[str, Any]:
    broker = decode_response(response, expected_ticket=expected_ticket, expected_session=expected_session,
                             expected_generation=expected_generation, expected_source=expected_source)
    source = decode_source_record(bytes.fromhex(broker["payload_hex"]), expected_operation=expected_operation,
                                  expected_session=expected_session, expected_generation=expected_generation,
                                  expected_source=expected_source, expected_sequence=expected_sequence,
                                  expected_endpoint=expected_endpoint, expected_evidence_sha256=expected_evidence_sha256).diagnostic()
    if source["provenance"] != broker["origin"]:
        raise ValueError("broker_source_provenance_mismatch")
    gap = int(broker["software_overflow_losses_before"]) > 0 or int(broker["software_rejects_before"]) > 0
    return dict(schema="wht/broker-source-observation/v1", source=source, broker=broker,
                quarantine_required=gap or source["quarantine_required"], clock_input_eligible=False,
                hardware_qpc_qualified=False, firmware_association_qualified=False,
                quarantine_release_qualified=False)
