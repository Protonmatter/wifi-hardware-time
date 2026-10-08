"""Offline ownership tests: injected kernel only; no private device is opened."""
import contextlib
import importlib
import unittest


class Clock:
    frequency = 10_000_000

    def __init__(self):
        self.t = 1.0

    def monotonic(self):
        return self.t

    def now(self):
        return round(self.t * self.frequency)

    def sleep(self, seconds):
        self.t += seconds


class Owner:
    def __init__(self):
        self.alive = True
        self.permitted = 1
        self.before_submit = None

    def check(self):
        if not self.alive:
            raise RuntimeError('controller lost')

    @contextlib.contextmanager
    def authorize(self, sequence):
        self.check()
        if sequence != self.permitted:
            raise RuntimeError('no fresh permit')
        self.permitted = None
        if self.before_submit:
            self.before_submit()
        yield


class Kernel:
    def __init__(self, api, clock):
        self.api, self.clock = api, clock
        self.initial = api.IoResult(True, 0, 4, b'\x00' * 4)
        self.polls = []
        self.cancel_result = (True, 0)
        self.opens = self.closes = self.releases = self.submissions = 0
        self.operations = []
        self.payloads = []
        self.close_ok = True

    def open(self):
        self.opens += 1

    def allocate(self, payload):
        operation = object()
        self.operations.append(operation)
        self.payloads.append(payload)
        return operation

    def submit(self, operation):
        self.submissions += 1
        if isinstance(self.initial, BaseException):
            raise self.initial
        return self.initial

    def poll(self, operation, timeout_ms):
        assert 0 < timeout_ms <= 50
        self.clock.sleep(timeout_ms / 1000)
        if self.polls:
            value = self.polls.pop(0)
            if isinstance(value, BaseException):
                raise value
            return value
        return self.api.PollResult(258, None)

    def cancel(self, operation):
        if isinstance(self.cancel_result, BaseException):
            raise self.cancel_result
        return self.cancel_result

    def release(self, operation):
        self.releases += 1
        return True

    def close(self):
        self.closes += 1
        return self.close_ok


class SamplerTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('research.tsf.tsf_sampler'), 'persistent sampler missing')
        self.api = importlib.import_module('research.tsf.tsf_sampler')
        self.clock, self.owner, self.records = Clock(), Owner(), []
        self.kernel = Kernel(self.api, self.clock)
        self.identity_calls = 0

        def identity():
            self.identity_calls += 1
            return dict(interface_index=7, adapter_guid='fixture-adapter', driver_sha256=self.api.QUALIFIED_SHA256,
                        mac_hex='020000000001', identity_validated=True)

        self.sampler = self.api.Sampler(self.kernel, self.clock, self.owner, self.records.append, identity,
                                       session_id='fixture-session')
        self.sampler.start()

    def pending(self):
        self.kernel.initial = self.api.IoResult(False, 997, 0, b'')
        self.sampler.submit(1)

    def deadline(self):
        self.clock.t += 2.0
        self.sampler.step()

    def test_immediate_success_keeps_handle_and_resets_next_request(self):
        self.sampler.submit(1)
        first = self.sampler.receipt.copy()
        self.owner.permitted = 2
        self.kernel.initial = self.api.IoResult(True, 0, 0, b'')
        self.sampler.submit(2)
        self.assertTrue(first['success'])
        self.assertTrue(first['completion_established'])
        self.assertNotIn('handle_closed', first)
        self.assertFalse(first['cancel_requested'])
        self.assertEqual(self.sampler.receipt['response_hex'], '')
        self.assertEqual((self.identity_calls, self.kernel.opens, self.kernel.closes, self.kernel.releases), (1, 1, 0, 2))
        self.assertIsNot(self.kernel.operations[0], self.kernel.operations[1])

    def test_payload_matches_audited_action4(self):
        from research.tsf.qualcomm_protocol import build_request
        self.sampler.submit(1)
        self.assertEqual(self.kernel.payloads[0], build_request('tsf_read_value', bytes.fromhex('020000000001'), tsf_action=4))
        self.assertEqual(self.kernel.payloads[0][28:36], b'\x01\x00\x00\x00\x00\x00\x00\x00')
        self.assertEqual(len(self.kernel.payloads[0]), 128)
        with self.assertRaises(TypeError):
            self.sampler.submit(2, command='arbitrary')

    def test_pending_then_success_no_early_release(self):
        self.pending()
        self.sampler.step()
        self.assertEqual(self.kernel.releases, 0)
        self.kernel.polls.append(self.api.PollResult(0, self.api.IoResult(True, 0, 0, b'')))
        self.sampler.step()
        self.assertTrue(self.sampler.receipt['success'])
        self.assertEqual(self.kernel.releases, 1)
        self.assertEqual(self.sampler.state.value, 'READY')

    def test_deadline_normal_completion_and_cancelled_completion_stay_failed(self):
        self.pending()
        self.deadline()
        self.assertTrue(self.sampler.receipt['deadline_exceeded'])
        self.assertTrue(self.sampler.receipt['cancel_requested'])
        self.kernel.polls.append(self.api.PollResult(0, self.api.IoResult(True, 0, 0, b'')))
        self.sampler.step()
        self.assertFalse(self.sampler.receipt['success'])
        self.assertTrue(self.sampler.receipt['terminal_success'])
        self.assertEqual(self.sampler.state.value, 'STOPPED')
        self.assertTrue(self.sampler.close())

    def test_cancel_abort_is_terminal_but_not_success(self):
        self.pending()
        self.deadline()
        self.kernel.polls.append(self.api.PollResult(0, self.api.IoResult(False, 995, 0, b'')))
        self.sampler.step()
        self.assertTrue(self.sampler.receipt['completion_established'])
        self.assertEqual(self.sampler.receipt['terminal_error'], 995)
        self.assertFalse(self.sampler.receipt['success'])

    def test_not_found_does_not_establish_completion(self):
        self.kernel.cancel_result = (False, 1168)
        self.pending()
        self.deadline()
        for _ in range(5):
            self.sampler.step()
        self.assertEqual(self.sampler.receipt['cancel_error'], 1168)
        self.assertFalse(self.sampler.receipt['completion_established'])
        self.assertEqual(self.kernel.releases, 0)

    def test_never_completes_retains_resources_and_rejects_new_requests(self):
        self.pending()
        self.deadline()
        operation = self.sampler.operation
        for _ in range(10):
            self.sampler.step()
        self.assertFalse(self.sampler.close())
        self.assertIs(self.sampler.operation, operation)
        self.assertEqual(self.sampler.state.value, 'QUARANTINED_DRAIN_PENDING')
        self.assertEqual((self.kernel.releases, self.kernel.closes), (0, 0))
        with self.assertRaises(RuntimeError):
            self.sampler.submit(2)
        self.assertIsNone(self.sampler.receipt['qpc_request_completed'])

    def test_wait_error_and_exception_preserve_ownership(self):
        self.pending()
        self.kernel.polls = [self.api.PollResult(0xffffffff, None), RuntimeError('poll failed')]
        self.sampler.step()
        self.sampler.step()
        self.assertFalse(self.sampler.close())
        self.assertEqual((self.kernel.releases, self.kernel.closes), (0, 0))

    def test_controller_loss_at_submission_boundary_never_submits(self):
        self.owner.before_submit = lambda: setattr(self.owner, 'alive', False)
        self.sampler.submit(1)
        self.assertEqual(self.kernel.submissions, 0)
        self.assertIsNone(self.sampler.receipt['qpc_request_before'])
        self.assertFalse(self.sampler.receipt['success'])

    def test_controller_loss_during_wait_cancels_and_drains(self):
        self.pending()
        self.owner.alive = False
        self.sampler.step()
        self.assertTrue(self.sampler.receipt['cancel_requested'])
        self.assertFalse(self.sampler.close())
        self.kernel.polls.append(self.api.PollResult(0, self.api.IoResult(False, 995, 0, b'')))
        self.sampler.step()
        self.assertTrue(self.sampler.close())

    def test_submission_exception_is_ambiguous_and_retained(self):
        self.kernel.initial = RuntimeError('exception after native submit')
        self.sampler.submit(1)
        self.assertFalse(self.sampler.close())
        self.assertEqual(self.kernel.releases, 0)

    def test_close_pending_requests_cancel_without_releasing(self):
        self.pending()
        self.assertFalse(self.sampler.close())
        self.assertTrue(self.sampler.receipt['cancel_requested'])
        self.assertEqual((self.kernel.closes, self.kernel.releases), (0, 0))

    def test_repeated_clean_close_closes_once(self):
        self.sampler.submit(1)
        self.assertTrue(self.sampler.close())
        self.assertTrue(self.sampler.close())
        self.assertEqual(self.kernel.closes, 1)
        with self.assertRaises(RuntimeError):
            self.sampler.submit(2)
        self.assertTrue(self.sampler.session['handle_closed'])
        self.assertEqual(self.sampler.session['outstanding_operations'], 0)

    def test_terminal_error_stops_session(self):
        self.kernel.initial = self.api.IoResult(False, 5, 0, b'')
        self.sampler.submit(1)
        self.assertEqual(self.sampler.state.value, 'STOPPED')
        self.assertFalse(self.sampler.receipt['success'])

    def test_returned_capacity_violation_fails_closed(self):
        self.kernel.initial = self.api.IoResult(True, 0, 101, b'x' * 101)
        self.sampler.submit(1)
        self.assertFalse(self.sampler.receipt['success'])
        self.assertEqual(self.sampler.state.value, 'STOPPED')

    def test_no_permit_or_stale_sequence_never_submits(self):
        self.owner.permitted = None
        self.sampler.submit(1)
        self.assertEqual(self.kernel.submissions, 0)
        self.assertFalse(self.sampler.receipt['success'])

    def test_receipt_write_failure_stops_before_submission(self):
        def broken(record):
            raise OSError('disk full')
        self.sampler.sink = broken
        self.sampler.submit(1)
        self.assertEqual(self.kernel.submissions, 0)
        self.assertFalse(self.sampler.receipt['success'])


if __name__ == '__main__':
    unittest.main()
