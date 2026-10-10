"""Explicit flush of the campaign's real-time ETW session; no session control on import.

Real-time consumers receive events only when a buffer is flushed, and the minimum
flush timer is one second, so a report group can wait one to two seconds for delivery.
ControlTraceW(EVENT_TRACE_CONTROL_FLUSH) delivers non-empty buffers now. A failed flush
is evidence, not a run failure: the session's one-second timer still delivers.
"""
from __future__ import annotations

import ctypes as ct
import os

EVENT_TRACE_CONTROL_FLUSH = 3
NAME_CHARS = 1024


class WnodeHeader(ct.Structure):
    _fields_ = [('BufferSize', ct.c_uint32), ('ProviderId', ct.c_uint32), ('HistoricalContext', ct.c_uint64),
                ('TimeStamp', ct.c_int64), ('Guid', ct.c_ubyte * 16), ('ClientContext', ct.c_uint32),
                ('Flags', ct.c_uint32)]


class EventTraceProperties(ct.Structure):
    _fields_ = [('Wnode', WnodeHeader), ('BufferSize', ct.c_uint32), ('MinimumBuffers', ct.c_uint32),
                ('MaximumBuffers', ct.c_uint32), ('MaximumFileSize', ct.c_uint32), ('LogFileMode', ct.c_uint32),
                ('FlushTimer', ct.c_uint32), ('EnableFlags', ct.c_uint32), ('AgeLimit', ct.c_int32),
                ('NumberOfBuffers', ct.c_uint32), ('FreeBuffers', ct.c_uint32), ('EventsLost', ct.c_uint32),
                ('BuffersWritten', ct.c_uint32), ('LogBuffersLost', ct.c_uint32),
                ('RealTimeBuffersLost', ct.c_uint32), ('LoggerThreadId', ct.c_void_p),
                ('LogFileNameOffset', ct.c_uint32), ('LoggerNameOffset', ct.c_uint32)]


class PropertiesBuffer(ct.Structure):
    # UTF-16 name storage sized in bytes so the layout is identical on every host.
    _fields_ = [('p', EventTraceProperties), ('name', ct.c_uint16 * NAME_CHARS), ('file', ct.c_uint16 * NAME_CHARS)]


class TraceFlusher:
    def __init__(self, session: str, now, *, live: bool = False, api=None):
        if not session or len(session) >= NAME_CHARS:
            raise ValueError('Session name required and shorter than 1024 characters')
        if api is None:
            if not live or os.name != 'nt':
                raise ValueError('Explicit Windows live selection required')
            api = ct.WinDLL('advapi32')
            api.ControlTraceW.argtypes = [ct.c_uint64, ct.c_wchar_p, ct.POINTER(EventTraceProperties), ct.c_uint32]
            api.ControlTraceW.restype = ct.c_uint32
        self.session, self.now, self.api = session, now, api

    def flush(self) -> dict:
        buffer = PropertiesBuffer()
        buffer.p.Wnode.BufferSize = ct.sizeof(PropertiesBuffer)
        buffer.p.LoggerNameOffset = PropertiesBuffer.name.offset
        buffer.p.LogFileNameOffset = PropertiesBuffer.file.offset
        started = self.now()
        status = int(self.api.ControlTraceW(0, self.session, ct.cast(ct.pointer(buffer), ct.POINTER(EventTraceProperties)),
                                            EVENT_TRACE_CONTROL_FLUSH))
        finished = self.now()
        return dict(started_qpc=started, finished_qpc=finished, status=status,
                    events_lost=buffer.p.EventsLost, realtime_buffers_lost=buffer.p.RealTimeBuffersLost)
