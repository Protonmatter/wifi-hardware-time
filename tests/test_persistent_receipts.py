import copy
import importlib
import unittest
import json
from pathlib import Path
import tempfile

from research.clock_models.sample_screen import Request, request_from_receipt
from research.tsf.qualcomm_protocol import QUALIFIED_SHA256


def evidence():
    session = dict(schema='wht/persistent-tsf-session-v1', session_id='s', clock='QPC',
                   qpc_frequency_hz=10_000_000, identity_validated=True, handle_opened=True,
                   handle_closed=False, handle_close_attempted=False, outstanding_operations=0,
                   failed=False, state='READY', started_qpc=1, request_count=1,
                   identity=dict(driver_sha256=QUALIFIED_SHA256, interface_index=7,
                                 adapter_guid='fixture', identity_validated=True))
    request = dict(schema='wht/persistent-tsf-request-v1', session_id='s', sequence=1,
                   clock='QPC', qpc_frequency_hz=10_000_000, qpc_request_before=10,
                   qpc_request_completed=20, command='tsf_read_value', firmware_action=4,
                   ioctl='0x00220182', input_bytes=128, output_capacity=100,
                   driver_sha256=QUALIFIED_SHA256, interface_index=7,
                   initial_success=True, initial_error=0, wait_result=None,
                   deadline_exceeded=False, cancel_requested=False, cancel_accepted=None,
                   cancel_error=None, completion_established=True, terminal_success=True,
                   terminal_error=0, returned_bytes=0, response_hex='', success=True)
    return request, session


class ReceiptTests(unittest.TestCase):
    def test_run_loader_requires_verified_lifecycle_and_session_start(self):
        from test_analyze_bound_run import write_run
        from research.clock_models.analyze_bound_run import load_run
        request, session = evidence()
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            write_run(folder, count=1)
            request.update(qpc_request_before=10_000_000, qpc_request_completed=10_000_500)
            (folder / 'requests.jsonl').write_text(json.dumps(request) + '\n')
            with self.assertRaises(ValueError):
                load_run(folder)
            (folder / 'sampler-session-start.json').write_text(json.dumps(session))
            (folder / 'sampler-session.json').write_text(json.dumps(session))
            self.assertFalse(load_run(folder)['completed'])
            closed = dict(session, state='CLOSED', handle_closed=True, handle_close_attempted=True, ended_qpc=20_000_000)
            (folder / 'sampler-session.json').write_text(json.dumps(closed))
            self.assertTrue(load_run(folder)['completed'])
            (folder / 'sampler-session-start.json').write_text(json.dumps(dict(session, session_id='other')))
            with self.assertRaises(ValueError):
                load_run(folder)

    def test_persistent_normalizes_without_fake_closure(self):
        request, session = evidence()
        before = copy.deepcopy((request, session))
        self.assertEqual(request_from_receipt(1, request, session=session, qpc_hz=10_000_000), Request(1, 10, True))
        self.assertEqual((request, session), before)
        self.assertNotIn('handle_closed', request)

    def test_missing_or_corrupt_session_fails_closed(self):
        request, session = evidence()
        cases = [None, {}, dict(session, schema='unknown'), dict(session, session_id='other'),
                 dict(session, qpc_frequency_hz=1), dict(session, identity_validated=False),
                 dict(session, handle_opened=False), dict(session, started_qpc=11),
                 dict(session, outstanding_operations=1), dict(session, state='QUARANTINED_DRAIN_PENDING')]
        for value in cases:
            with self.subTest(session=value), self.assertRaises(ValueError):
                request_from_receipt(1, request, session=value, qpc_hz=10_000_000)

    def test_unknown_schema_and_incomplete_request_rejected(self):
        request, session = evidence()
        cases = [dict(request, schema='unknown'), dict(request, sequence=2), dict(request, clock='FILETIME'),
                 dict(request, qpc_request_completed=None), dict(request, completion_established=False),
                 dict(request, driver_sha256='bad'), dict(request, qpc_request_completed=9),
                 dict(request, response_hex='xyz'), dict(request, returned_bytes=101),
                 dict(request, cancel_requested='false'), dict(request, deadline_exceeded=0),
                 dict(request, initial_error=None), dict(request, initial_success=False),
                 dict(request, handle_closed=True), dict(request, initial_success=False, initial_error=5)]
        for field in request:
            missing = request.copy()
            del missing[field]
            cases.append(missing)
        for value in cases:
            with self.subTest(request=value), self.assertRaises(ValueError):
                request_from_receipt(1, value, session=session, qpc_hz=10_000_000)

    def test_timeout_or_cancellation_never_becomes_success(self):
        request, session = evidence()
        for change in (dict(deadline_exceeded=True, success=False),
                       dict(cancel_requested=True, cancel_accepted=False, cancel_error=1168, success=False)):
            self.assertFalse(request_from_receipt(1, dict(request, **change), session=session).succeeded)

    def test_legacy_decisions_unchanged(self):
        for success in (True, False, None):
            for closed in (True, False, None):
                for cancelled in (True, False, None):
                    receipt = dict(qpc_request_before=5, firmware_action=4, success=success,
                                   handle_closed=closed, cancel_requested=cancelled)
                    self.assertEqual(request_from_receipt(1, receipt).succeeded,
                                     success is True and closed is True and not cancelled)

    def test_request_eligibility_distinct_from_campaign_completion(self):
        request, session = evidence()
        self.assertEqual(request_from_receipt(1, request, session=session), Request(1, 10, True))
        module = importlib.import_module('research.tsf.sampler_receipts')
        self.assertFalse(module.session_clean(session))
        closed = dict(session, state='CLOSED', handle_closed=True, handle_close_attempted=True, ended_qpc=30)
        self.assertTrue(module.session_clean(closed))
        self.assertFalse(module.session_clean(dict(closed, failed=True)))
        self.assertFalse(module.session_clean(dict(closed, outstanding_operations=1)))
        self.assertFalse(module.session_clean(dict(closed, failure='event close failed')))

    def test_pending_success_is_consistent_and_earlier_success_survives_later_session_failure(self):
        request, session = evidence()
        request.update(initial_success=False, initial_error=997, wait_result=0)
        self.assertTrue(request_from_receipt(1, request, session=session).succeeded)
        self.assertTrue(request_from_receipt(1, request, session=dict(session, failed=True, failure='later failure')).succeeded)


if __name__ == '__main__':
    unittest.main()
