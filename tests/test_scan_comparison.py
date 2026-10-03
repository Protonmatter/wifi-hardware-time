"""Offline bounds and attribution regressions for a documented scan experiment."""

import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ctypes
import unittest
import json
import tempfile
from types import SimpleNamespace
from unittest.mock import Mock,patch

from research.acquisition.run_scan_comparison import ScanGate,ScanClient,GUID,Notification,scan_completion,assess_trial
from research.acquisition.run_passive_observation import QUALIFIED_NATIVE,sha
from test_passive_observation import controls,decoded
from research.acquisition import run_scan_comparison as comparison


def report():return dict(kind='report',raw_timestamp=100,vdev=0,tsf_raw=1000)
def complete(qpc=110):return dict(kind='scan_client_notification',source=8,code=7,qpc=qpc)
def request():return dict(status=0,qpc_before=90,qpc_after=95,qpc_frequency_hz=10000000,notification_registration_status=0,notification_registered_qpc=80)


class ScanTests(unittest.TestCase):
    def test_native_guid_and_source_pins(self):
        self.assertEqual(ctypes.sizeof(GUID),16)
        self.assertEqual(ctypes.alignment(GUID),4)
        root=Path(__file__).resolve().parents[1]
        for p,h in QUALIFIED_NATIVE.items():
            if p.endswith('.c'):self.assertEqual(sha(root/p),h,p)

    def test_baseline_activity_and_private_admission_reject(self):
        for event in (report(),dict(kind='lifecycle',source=8,code=7,invalidates=False,qpc=110)):
            gate=ScanGate()
            with self.assertRaises(ValueError):gate.consume(event)
        with self.assertRaises(ValueError):ScanGate().arm(3,0)

    def test_treatment_observes_but_never_admits_and_caps(self):
        gate=ScanGate();gate.begin_scan(90)
        for _ in range(64):gate.consume(report())
        self.assertFalse(gate.complete)
        with self.assertRaises(ValueError):gate.consume(report())
        gate=ScanGate();gate.begin_scan(90)
        with self.assertRaises(ValueError):gate.consume(dict(kind='command',raw_timestamp=100,vdev=0,action=3))

    def test_late_baseline_and_bad_fields_reject(self):
        for update in (dict(raw_timestamp=89),dict(raw_timestamp=True),dict(vdev=True),dict(tsf_raw=-1)):
            gate=ScanGate();gate.begin_scan(90)
            with self.subTest(update=update),self.assertRaises(ValueError):gate.consume(dict(report(),**update))

    def test_completion_requires_one_in_window_and_no_failure(self):
        self.assertEqual(scan_completion([complete()],request(),10000000),110)
        self.assertIsNone(scan_completion([],request(),10000000))
        for records in ([complete(89)],[complete(40000091)],[complete(),complete(111)],[dict(complete(),code=8)]):
            with self.subTest(records=records),self.assertRaises(ValueError):scan_completion(records,request(),10000000)

    def test_completed_trial_does_not_claim_firmware_identity(self):
        events=[report(),dict(kind='soc_timer',raw_timestamp=101,g_tsf_raw=0,soc_timer_raw=500),dict(kind='delay',raw_timestamp=102,vdev=0,tsf_delay_raw=500)]
        for event in events:event['raw_timestamp']+=80000000
        req=dict(request(),qpc_before=80000090,qpc_after=80000095,quiet_started_qpc=0)
        ctl=controls()
        for record in ctl:record['qpc']=0
        result=assess_trial(ctl+events,decoded(events),req,10000000,[complete(80000110)])
        self.assertEqual(result['reports_after_scan_call'],1)
        self.assertFalse(result['firmware_initiator_identified'])
        self.assertFalse(result['clock_relationship_qualified'])

    def test_short_baseline_is_rejected_offline(self):
        ctl=controls()
        for record in ctl:record['qpc']=0
        with self.assertRaisesRegex(ValueError,'quiet'):
            assess_trial(ctl,decoded(),dict(request(),quiet_started_qpc=0),10000000,[complete()])

    def test_post_call_clock_failure_preserves_attempt_and_status(self):
        client=object.__new__(ScanClient);client.used=False;client.attempted=False;client.receipt=None
        client.registration_status=0;client.registered_qpc=80
        client.handle=None;client.guid=GUID();client.dll=SimpleNamespace(WlanScan=Mock(return_value=0))
        clock=SimpleNamespace(now=Mock(side_effect=[90,RuntimeError('post-call counter failed')]),frequency=10000000)
        with self.assertRaises(RuntimeError):client.scan(clock)
        client.dll.WlanScan.assert_called_once()
        self.assertTrue(client.attempted)
        self.assertEqual(client.receipt['status'],0)

    def test_request_handle_notification_requires_matching_interface(self):
        client=object.__new__(ScanClient);client.guid=GUID();client.notifications=[];client.callback_errors=[];client.notification_headers=[]
        client.clock=SimpleNamespace(now=lambda:123)
        event=Notification();event.source=8;event.code=7
        client._notification(ctypes.pointer(event),None)
        self.assertEqual(client.notifications,[complete(123)])
        event.guid.data1=1
        client._notification(ctypes.pointer(event),None)
        self.assertEqual(len(client.notifications),1)
        self.assertEqual(len(client.notification_headers),2)
        self.assertFalse(client.notification_headers[1]['selected_interface'])

    def test_unregistered_notification_path_rejects(self):
        with self.assertRaises(ValueError):scan_completion([complete()],dict(request(),notification_registration_status=5),10000000)

    def test_conflicting_observer_notifications_reject(self):
        ctl=controls()
        for row in ctl:row['qpc']=0
        req=dict(request(),qpc_before=80000090,qpc_after=80000095,quiet_started_qpc=0)
        native=dict(kind='lifecycle',source=8,code=7,qpc=80000110,invalidates=False)
        own=[complete(80000110)]
        assess_trial(ctl+[native],decoded(),req,10000000,own)
        for extra in ([dict(native,code=8)],[native,native],[dict(native,qpc=80000000)]):
            with self.subTest(extra=extra),self.assertRaises(ValueError):assess_trial(ctl+extra,decoded(),req,10000000,own)
        gate=ScanGate();gate.begin_scan(90)
        with self.assertRaises(ValueError):gate.consume(dict(native,code=8))

    def test_deadline_failure_still_collects_diagnostic_tail(self):
        with tempfile.TemporaryDirectory() as temporary:
            req=dict(request(),qpc_before=90000010,qpc_after=90000015)
            clock=SimpleNamespace(frequency=10000000,now=Mock(side_effect=[10000000,90000000,200000000]))
            observer=Mock(ready=True,association='synthetic',records=controls())
            client=SimpleNamespace(scan=Mock(return_value=req),receipt=req,close=lambda:0,
                unregister_status=0,close_status=0,attempted=True,notifications=[],notification_headers=[],callback_errors=[])
            with patch.object(comparison,'Clock',return_value=clock),patch.object(comparison,'identity',return_value={'InterfaceGuid':'synthetic'}),patch.object(comparison,'same_identity'),patch.object(comparison,'TraceOwner',return_value=Mock(session='synthetic-session')),patch.object(comparison,'Observer',return_value=observer),patch.object(comparison,'ScanClient',return_value=client),patch.object(comparison,'run',return_value=SimpleNamespace(stdout='\n'.join(json.dumps(r) for r in decoded()))):
                result=comparison.trial(Path(temporary)/'trial',1,{'InterfaceGuid':'synthetic'},None)
            self.assertEqual([c.args[0] for c in observer.wait.call_args_list],[2.5,8,8])
            self.assertFalse(result['success'])
            self.assertTrue(any('deadline' in e.lower() for e in result['errors']))
