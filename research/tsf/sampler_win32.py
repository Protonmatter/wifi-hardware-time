"""Explicitly selected Win32 action-4 backend; constructor injection keeps tests offline.

Limited duplication of qualcomm_probe.py (c620f47) preserves the audited reference.
Only a terminal result permits release of the OVERLAPPED and its buffers/event.
"""
from __future__ import annotations

import ctypes as ct
from dataclasses import dataclass
import os

from research.tsf.tsf_sampler import IoResult, PollResult


class Overlapped(ct.Structure):
    _fields_ = [('Internal', ct.c_size_t), ('InternalHigh', ct.c_size_t),
                ('Offset', ct.c_uint32), ('OffsetHigh', ct.c_uint32), ('hEvent', ct.c_void_p)]


@dataclass
class Operation:
    incoming: object
    outgoing: object
    overlapped: Overlapped
    returned: ct.c_uint32
    submitted: bool = False
    terminal: bool = False
    released: bool = False


class Win32Kernel:
    def __init__(self, *, live: bool = False, api=None, last_error=None):
        if api is None:
            if not live or os.name != 'nt':
                raise ValueError('Explicit Windows live selection required')
            api = ct.WinDLL('kernel32', use_last_error=True)
        self.k, self.error = api, last_error or ct.get_last_error
        self.handle = None
        self.operation = None  # Additional strong ownership until terminal release.
        signatures = {
            'CreateFileW': ([ct.c_wchar_p, ct.c_uint32, ct.c_uint32, ct.c_void_p, ct.c_uint32, ct.c_uint32, ct.c_void_p], ct.c_void_p),
            'CreateEventW': ([ct.c_void_p, ct.c_int, ct.c_int, ct.c_wchar_p], ct.c_void_p),
            'CloseHandle': ([ct.c_void_p], ct.c_int),
            'DeviceIoControl': ([ct.c_void_p, ct.c_uint32, ct.c_void_p, ct.c_uint32, ct.c_void_p, ct.c_uint32,
                                 ct.POINTER(ct.c_uint32), ct.POINTER(Overlapped)], ct.c_int),
            'WaitForSingleObject': ([ct.c_void_p, ct.c_uint32], ct.c_uint32),
            'CancelIoEx': ([ct.c_void_p, ct.POINTER(Overlapped)], ct.c_int),
            'GetOverlappedResult': ([ct.c_void_p, ct.POINTER(Overlapped), ct.POINTER(ct.c_uint32), ct.c_int], ct.c_int),
        }
        for name, (args, result) in signatures.items():
            fn = getattr(self.k, name)
            fn.argtypes, fn.restype = args, result

    def open(self) -> None:
        if self.handle is not None:
            raise RuntimeError('Device already opened')
        handle = self.k.CreateFileW(r'\\.\QcomWifi', 0x80000000, 3, None, 3, 0x40000000, None)
        if handle in (None, 0, ct.c_void_p(-1).value):
            raise OSError(self.error(), 'Private device open failed')
        self.handle = handle

    def allocate(self, payload: bytes) -> Operation:
        if self.handle is None or self.operation is not None or len(payload) != 128:
            raise RuntimeError('Invalid allocation or outstanding operation')
        # This backend also rejects non-action-4 payloads if called outside Sampler.
        from research.tsf.qualcomm_protocol import build_request
        if payload != build_request('tsf_read_value', payload[20:26], tsf_action=4):
            raise ValueError('Only the audited action-4 payload is supported')
        incoming, outgoing = (ct.c_ubyte * 128).from_buffer_copy(payload), (ct.c_ubyte * 100)()
        event = self.k.CreateEventW(None, True, False, None)
        if not event:
            raise OSError(self.error(), 'Completion event creation failed')
        self.operation = Operation(incoming, outgoing, Overlapped(hEvent=event), ct.c_uint32())
        return self.operation

    def _result(self, op: Operation, ok: bool, error: int) -> IoResult:
        return IoResult(ok, error, op.returned.value,
                        bytes(op.outgoing[:op.returned.value]) if ok and op.returned.value <= 100 else b'')

    def submit(self, op: Operation) -> IoResult:
        if op is not self.operation or op.submitted or op.released:
            raise RuntimeError('Invalid operation submission')
        op.submitted = True
        ok = bool(self.k.DeviceIoControl(self.handle, 0x00220182, op.incoming, 128, op.outgoing, 100,
                                         ct.byref(op.returned), ct.byref(op.overlapped)))
        error = 0 if ok else self.error()
        op.terminal = ok or error != 997
        return self._result(op, ok, error)

    def poll(self, op: Operation, timeout_ms: int) -> PollResult:
        if op is not self.operation or op.released or not 0 < timeout_ms <= 50:
            raise RuntimeError('Invalid bounded poll')
        wait = self.k.WaitForSingleObject(op.overlapped.hEvent, timeout_ms)
        if wait not in (0, 258):
            return PollResult(wait, None)
        ok = bool(self.k.GetOverlappedResult(self.handle, ct.byref(op.overlapped), ct.byref(op.returned), False))
        error = 0 if ok else self.error()
        if not ok and (error == 996 or op.overlapped.Internal == 0x103):
            return PollResult(wait, None)
        # Errors in using the API (invalid handle/parameter) cannot prove completion.
        if not ok and error in (6, 87):
            return PollResult(0xffffffff, None)
        op.terminal = True
        return PollResult(wait, self._result(op, ok, error))

    def cancel(self, op: Operation) -> tuple[bool, int]:
        ok = bool(self.k.CancelIoEx(self.handle, ct.byref(op.overlapped)))
        return ok, 0 if ok else self.error()

    def release(self, op: Operation) -> bool:
        if op.submitted and not op.terminal:
            raise RuntimeError('Cannot release unresolved native operation')
        if op.released:
            return True
        if not self.k.CloseHandle(op.overlapped.hEvent):
            return False
        op.released = True
        self.operation = None
        return True

    def close(self) -> bool:
        if self.operation is not None:
            raise RuntimeError('Operation resources still owned')
        if self.handle is None:
            return True
        if not self.k.CloseHandle(self.handle):
            return False
        self.handle = None
        return True
