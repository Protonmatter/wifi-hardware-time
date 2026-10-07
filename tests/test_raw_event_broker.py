"""Build actual native broker and exercise native threads plus a Python consumer."""
from __future__ import annotations
import ctypes as c
import inspect
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import unittest

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from research.export_contract.read_raw_response import decode_response
from research.tsf.decode_tsf_report import decode_event
from research.export_contract.source_record import SourceRecord, build_source_record, decode_broker_source

ROOT = Path(__file__).resolve().parents[1]


class RawResponseTests(unittest.TestCase):
    def fixture(self) -> bytearray:
        raw = bytearray(100)
        struct.pack_into("<4sHHIIII", raw, 0, b"WHTR", 1, 96, 100, 4, 1, 0)
        struct.pack_into("<6Q", raw, 24, 11, 7, 9, 1, 0, 0)
        struct.pack_into("<IIQQ", raw, 72, 1, 0, 2, 0)
        raw[96:] = b"test"
        return raw

    def decode(self, raw: bytes | bytearray, **changes: int):
        args = dict(expected_ticket=2, expected_session=11, expected_generation=7, expected_source=9)
        args.update(changes)
        return decode_response(raw, **args)

    def test_owned_response_and_software_identity_only(self):
        raw = self.fixture()
        result = self.decode(raw)
        raw[:] = bytes(len(raw))
        self.assertEqual(result["payload_hex"], b"test".hex())
        self.assertEqual(result["application_read_ticket"], "2")
        self.assertFalse(result["live_clock_eligible"])
        self.assertFalse(result["source_copy_qualified"])

    def test_rejects_partial_mismatched_claims_and_unknown_fields(self):
        for data in (self.fixture()[:-1], self.fixture() + b"\0", b"", memoryview(self.fixture())):
            with self.subTest(kind=type(data)), self.assertRaises(ValueError):
                self.decode(data)
        for offset in (0, 4, 6, 8, 12, 16, 20, 24, 32, 40, 48, 72, 76, 80, 88):
            raw = self.fixture()
            raw[offset] ^= 1
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                self.decode(raw)
        for change in ({"expected_ticket": 1}, {"expected_ticket": True},
                       {"expected_session": 0}, {"expected_generation": 2**64}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.decode(self.fixture(), **change)

    def test_mutable_source_growth_is_bounded_at_snapshot(self):
        raw = self.fixture()
        ready, changed = threading.Event(), threading.Event()
        lines, first_line = inspect.getsourcelines(decode_response)
        snapshot_line = first_line + next(i for i, text in enumerate(lines) if text.strip().startswith("raw = bytes("))
        def grow():
            if ready.wait(5):
                raw.extend(b"x" * 4096)
                struct.pack_into("<II", raw, 8, len(raw), len(raw) - 96)
                changed.set()
        worker = threading.Thread(target=grow)
        def before_copy(frame, event, arg):
            if event == "line" and frame.f_code is decode_response.__code__ and frame.f_lineno == snapshot_line:
                ready.set()
                if not changed.wait(5):
                    raise RuntimeError("growth worker did not respond")
            return before_copy
        previous = sys.gettrace()
        worker.start()
        try:
            sys.settrace(before_copy)
            with self.assertRaises(ValueError):
                self.decode(raw)
        finally:
            sys.settrace(previous)
            ready.set()
            worker.join(6)
        self.assertFalse(worker.is_alive())


class NativeRawBrokerTests(unittest.TestCase):
    def test_native_concurrency_and_shared_library_consumer(self):
        configured = os.environ.get("WIFI_TIME_NATIVE_CC")
        compiler = shutil.which(configured) if configured else next(
            (found for name in ("cl", "cc", "clang", "gcc") if (found := shutil.which(name))), None)
        if not compiler:
            if configured:
                self.fail("WIFI_TIME_NATIVE_CC does not resolve to a compiler")
            self.skipTest("No C compiler; use an installed developer shell")
        msvc = Path(compiler).name.lower() in {"cl", "cl.exe"}
        source = ROOT / "research/export_contract/raw_event_broker.c"
        harness = ROOT / "tests/native_raw_event_broker.c"
        with tempfile.TemporaryDirectory(prefix="raw-response-broker-") as tmp:
            binary = Path(tmp) / ("broker.exe" if os.name == "nt" else "broker")
            library = Path(tmp) / ("broker.dll" if os.name == "nt" else "broker.so")
            if msvc:
                prefix = [compiler, "/nologo", "/std:c11", "/W4", "/WX", "/O2"]
                native = prefix + [str(harness), str(source), f"/Fe{binary}"]
                shared = prefix + ["/LD", "/DRB_BUILD_SHARED", str(source), f"/Fe{library}"]
            else:
                prefix = [compiler, "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic", "-O2", "-pthread"]
                native = prefix + [str(harness), str(source), "-o", str(binary)]
                shared = prefix + ["-shared", "-fPIC", str(source), "-o", str(library)]
            for command in (native, shared):
                result = subprocess.run(command, cwd=tmp, capture_output=True, text=True, timeout=60)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([str(binary)], cwd=tmp, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("all raw broker software checks passed", result.stdout)
            self.assertIn("readers=1", result.stdout)
            self.assertIn("readers=4", result.stdout)
            # Load in a CHILD process so Windows releases the DLL before cleanup.
            child = subprocess.run([sys.executable, str(Path(__file__).resolve()), str(library)],
                                   cwd=ROOT, capture_output=True, text=True, timeout=15)
            self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
            self.assertIn("Python consumer decoded owned TSF replay", child.stdout)
            self.assertIn("Bound source metadata and complete HTC bytes survived native publication", child.stdout)


def bind_library(library: str):
    dll = c.CDLL(library)
    dll.rb_create.argtypes = [c.c_uint64, c.c_uint64, c.c_uint64, c.c_uint32]
    dll.rb_create.restype = c.c_void_p
    dll.rb_publish.argtypes = [c.c_void_p, c.c_uint64, c.c_void_p, c.c_size_t, c.c_size_t, c.c_size_t, c.c_uint32]
    dll.rb_begin_read.argtypes = [c.c_void_p, c.POINTER(c.c_uint64)]
    dll.rb_read.argtypes = [c.c_void_p, c.c_uint64, c.c_void_p, c.c_size_t, c.c_uint32,
                            c.POINTER(c.c_size_t), c.POINTER(c.c_size_t)]
    dll.rb_close.argtypes = [c.c_void_p]
    dll.rb_destroy.argtypes = [c.POINTER(c.c_void_p)]
    return dll


def source_record_roundtrip(library: str, record: SourceRecord, *, expected_operation: str,
                            provenance: str, session: int, generation: int, source_id: int,
                            sequence: int, endpoint: int | None = None,
                            evidence_sha256: str | None = None) -> dict:
    """Software-only native integration helper, also usable with saved private replay."""
    if provenance not in ("fixture", "replay-unqualified"):
        raise ValueError("unsupported replay provenance")
    dll = bind_library(library)
    broker = c.c_void_p(dll.rb_create(session, generation, source_id, 1 if provenance == "fixture" else 2))
    if not broker: raise RuntimeError("create failed")
    try:
        source = c.create_string_buffer(b"prefix" + record.wire)
        if dll.rb_publish(broker, generation, source, len(source), 6, len(record.wire),
                          1 if provenance == "fixture" else 3) != 0:
            raise RuntimeError("source publication failed")
        c.memset(source, 0, len(source))
        ticket = c.c_uint64()
        if dll.rb_begin_read(broker, c.byref(ticket)) != 0: raise RuntimeError("begin failed")
        output = c.create_string_buffer(4192)
        written, required = c.c_size_t(), c.c_size_t()
        if dll.rb_read(broker, ticket.value, output, len(output), 0, c.byref(written), c.byref(required)) != 0:
            raise RuntimeError("read failed")
        result = decode_broker_source(output.raw[:written.value], expected_ticket=ticket.value,
            expected_session=session, expected_generation=generation, expected_source=source_id,
            expected_operation=expected_operation, expected_sequence=sequence, expected_endpoint=endpoint,
            expected_evidence_sha256=evidence_sha256)
        c.memset(output, 0, len(output))
        if result["source"]["payload"] != record.diagnostic()["payload"]:
            raise RuntimeError("source payload changed")
        return result
    finally:
        dll.rb_close(broker)
        if dll.rb_destroy(c.byref(broker)) != 0: raise RuntimeError("destroy failed")


def application_roundtrip(library: str) -> None:
    dll = bind_library(library)
    broker = c.c_void_p(dll.rb_create(11, 7, 9, 2))
    if not broker: raise RuntimeError("broker creation failed")
    try:
        event = struct.pack("<I15I", 0x5005, (0x18B << 16) | 56, 7, 123, 1, 456, 2, 0, 1, 2, 0, 0, 0, 0, 0, 0)
        source = c.create_string_buffer(b"prefix" + event)
        if dll.rb_publish(broker, 7, source, len(source), 6, len(event), 3) != 0:
            raise RuntimeError("publish failed")
        c.memset(source, 0, len(source))
        ticket = c.c_uint64()
        if dll.rb_begin_read(broker, c.byref(ticket)) != 0: raise RuntimeError("begin failed")
        output = c.create_string_buffer(4192)
        written, required = c.c_size_t(), c.c_size_t()
        if dll.rb_read(broker, ticket.value, output, len(output), 0, c.byref(written), c.byref(required)) != 0:
            raise RuntimeError("read failed")
        response = decode_response(output.raw[:written.value], expected_ticket=ticket.value,
                                   expected_session=11, expected_generation=7, expected_source=9)
        payload = bytes.fromhex(response["payload_hex"])
        if payload != event: raise RuntimeError("copy changed")
        decoded = decode_event(payload, event_id=0x5005, reference_layout="reference-60",
                               origin="fixture", representation="event-wire").diagnostic()
        if decoded["live_clock_eligible"]: raise RuntimeError("clock gate changed")
        print("Python consumer decoded owned TSF replay; hardware unqualified")
    finally:
        dll.rb_close(broker)
        if dll.rb_destroy(c.byref(broker)) != 0: raise RuntimeError("destroy failed")
    trailer = b"\x01\x02\x03\x04"
    envelope = struct.pack("<BBHBBBB", 2, 2, len(event) + len(trailer), len(trailer), 0, 0, 0) + event + trailer
    record = build_source_record(envelope, operation="qcom-tsf-htc-reference-60-v1", provenance="fixture",
        session=11, generation=7, source=9, sequence=1, source_loss_count=None, continuity="unknown",
        host_interval=None, transport_endpoint=2)
    result = source_record_roundtrip(library, record, expected_operation="qcom-tsf-htc-reference-60-v1",
        provenance="fixture", session=11, generation=7, source_id=9, sequence=1, endpoint=2)
    if result["clock_input_eligible"] or result["source"]["source_loss_count"] is not None:
        raise RuntimeError("source qualification or loss semantics changed")
    if result["source"]["payload_diagnostic"]["raw_htc_trailer_hex"] != trailer.hex():
        raise RuntimeError("transport trailer lost")
    print("Bound source metadata and complete HTC bytes survived native publication; hardware unqualified")


if __name__ == "__main__":
    application_roundtrip(sys.argv[1])
