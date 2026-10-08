"""ABI conformance with a fake DLL; even on Windows this opens no device."""
import ctypes as ct
import importlib
import unittest
from unittest.mock import patch


class Fn:
    def __init__(self, call):
        self.call = call
    def __call__(self, *args):
        return self.call(*args)


class Win32Tests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('research.tsf.sampler_win32'), 'Win32 adapter missing')
        self.api = importlib.import_module('research.tsf.sampler_win32')

    def test_live_api_cannot_load_without_explicit_selection(self):
        with patch.object(ct, 'WinDLL', create=True, side_effect=AssertionError('hardware path')):
            with self.assertRaises(ValueError):
                self.api.Win32Kernel()

    def test_native_arguments_and_finite_polling(self):
        calls = []
        dll = type('DLL', (), {})()
        dll.CreateFileW = Fn(lambda *args: calls.append(('open', args)) or 42)
        dll.CreateEventW = Fn(lambda *args: calls.append(('event', args)) or 43)
        dll.CloseHandle = Fn(lambda handle: calls.append(('close', handle)) or 1)
        dll.CancelIoEx = Fn(lambda *args: 0)
        dll.WaitForSingleObject = Fn(lambda handle, ms: calls.append(('wait', ms)) or 258)
        dll.GetOverlappedResult = Fn(lambda *args: 0)
        def submit(handle, ioctl, incoming, n_in, outgoing, n_out, count, ov):
            calls.append(('submit', handle, ioctl, bytes(incoming), n_in, n_out))
            ct.cast(ov, ct.POINTER(self.api.Overlapped)).contents.Internal = 0x103
            return 0
        dll.DeviceIoControl = Fn(submit)
        kernel = self.api.Win32Kernel(api=dll, last_error=lambda: 997)
        kernel.open()
        from research.tsf.qualcomm_protocol import build_request
        payload = build_request('tsf_read_value', b'\x02\x00\x00\x00\x00\x01', tsf_action=4)
        operation = kernel.allocate(payload)
        kernel.submit(operation)
        kernel.error = lambda: 996
        self.assertEqual(calls[-1], ('submit', 42, 0x00220182, payload, 128, 100))
        self.assertIsNone(kernel.poll(operation, 50).result)
        self.assertEqual(calls[-1], ('wait', 50))
        self.assertEqual(kernel.cancel(operation), (False, 996))
        with self.assertRaises(RuntimeError):
            kernel.release(operation)
        self.assertNotIn(('close', 43), calls)


if __name__ == '__main__':
    unittest.main()
