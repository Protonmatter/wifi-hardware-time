
import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import unittest
from research.acquisition.analyze_scan_comparison import characterize
from test_passive_observation import controls,decoded


class PostmortemTests(unittest.TestCase):
    def test_late_completion_preserves_failed_outcome(self):
        request=dict(api='WlanScan',status=0,qpc_before=80000000,qpc_after=80001000,qpc_frequency_hz=10000000,quiet_started_qpc=0)
        live=controls()
        for r in live:r['qpc']=0
        notifications=dict(records=[dict(kind='scan_client_notification',source=8,code=7,qpc=140000000)])
        result=characterize(request,live,decoded(),dict(success=False,scan_calls=1,private_requests=0),dict(observer_clean_stop=True,evidence_drained=True),notifications)
        self.assertEqual(result['client_completion_delay_ns'],6000000000)
        self.assertFalse(result['controller_success']);self.assertFalse(result['clock_qualified'])

    def test_missing_completion_is_unknown_not_zero(self):
        req=dict(api='WlanScan',status=0,qpc_before=80000000,qpc_after=80001000,qpc_frequency_hz=10000000,quiet_started_qpc=0)
        result=characterize(req,controls(),decoded(),dict(success=False,scan_calls=1,private_requests=0),dict(observer_clean_stop=True,evidence_drained=True),None)
        self.assertIsNone(result['client_completion_delay_ns'])
        self.assertFalse(result['client_notifications_collected'])
        req['qpc_after']=79999999
        with self.assertRaises(ValueError):characterize(req,controls(),decoded(),dict(success=False,scan_calls=1,private_requests=0),dict(observer_clean_stop=True,evidence_drained=True),None)
