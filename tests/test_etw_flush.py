import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ctypes as ct
import unittest
from research.acquisition.etw_flush import (EVENT_TRACE_CONTROL_FLUSH, EventTraceProperties, PropertiesBuffer,
                                            TraceFlusher)


class FakeAdvapi:
    def __init__(self, status):
        self.status, self.calls = status, []

    def ControlTraceW(self, handle, name, properties, code):
        buffer = ct.cast(properties, ct.POINTER(PropertiesBuffer)).contents
        self.calls.append((handle, name, code, buffer.p.Wnode.BufferSize, buffer.p.LoggerNameOffset))
        buffer.p.EventsLost = 0
        return self.status


class TraceFlusherTests(unittest.TestCase):
    def test_properties_layout_matches_evntrace_h_on_64_bit(self):
        if ct.sizeof(ct.c_void_p) != 8:
            self.skipTest('64-bit layout')
        self.assertEqual(ct.sizeof(EventTraceProperties), 120)
        self.assertEqual(EventTraceProperties.LoggerThreadId.offset, 104)
        self.assertEqual(PropertiesBuffer.name.offset, 120)

    def test_flush_calls_control_trace_with_named_session_and_records_qpc(self):
        api, ticks = FakeAdvapi(0), iter((10, 25))
        receipt = TraceFlusher('WifiBound-abc', lambda: next(ticks), api=api).flush()
        self.assertEqual(api.calls, [(0, 'WifiBound-abc', EVENT_TRACE_CONTROL_FLUSH, ct.sizeof(PropertiesBuffer), 120)])
        self.assertEqual(receipt, dict(started_qpc=10, finished_qpc=25, status=0, events_lost=0,
                                       realtime_buffers_lost=0))

    def test_failed_flush_is_returned_not_raised(self):
        receipt = TraceFlusher('WifiBound-abc', lambda: 1, api=FakeAdvapi(4201)).flush()
        self.assertEqual(receipt['status'], 4201)

    def test_live_selection_is_explicit(self):
        with self.assertRaises(ValueError):
            TraceFlusher('WifiBound-abc', lambda: 1)
        with self.assertRaises(ValueError):
            TraceFlusher('', lambda: 1, api=FakeAdvapi(0))


if __name__ == '__main__':
    unittest.main()
