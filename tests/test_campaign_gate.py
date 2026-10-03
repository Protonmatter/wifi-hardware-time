
import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import unittest
from research.acquisition.campaign_gate import ReportGate


def events():
    return [dict(kind='command',raw_timestamp=110,vdev=0,action=3),
            dict(kind='report',raw_timestamp=120,vdev=0,tsf_raw=1000),
            dict(kind='soc_timer',raw_timestamp=121,soc_timer_raw=500,g_tsf_raw=0),
            dict(kind='delay',raw_timestamp=122,vdev=0,tsf_delay_raw=500)]


class GateTests(unittest.TestCase):
    def test_legacy_observer_health_is_rejected_before_admission(self):
        for record in (dict(kind='ready'),dict(kind='health',events_lost=0)):
            with self.subTest(record=record),self.assertRaises(ValueError):ReportGate().consume(record)

    def test_controller_health_checks_all_loss_counters_and_status(self):
        healthy=dict(kind='health',health_source='controller_query',query_status=0,
                     events_lost=0,log_buffers_lost=0,real_time_buffers_lost=0)
        gate=ReportGate();gate.consume(dict(kind='ready',health_schema='controller-query/v1'));gate.consume(healthy)
        for field,value in [('query_status',5),('events_lost',1),('log_buffers_lost',1),('real_time_buffers_lost',1),('events_lost',False),('events_lost',-1)]:
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):
                ReportGate().consume(dict(healthy,**{field:value}))

    def test_one_complete_group_then_next_request(self):
        gate=ReportGate();gate.arm(3,100)
        for event in events():gate.consume(event)
        gate.finish(dict(success=True,handle_closed=True,qpc_request_before=105,qpc_request_completed=115))
        gate.arm(4,200)
        self.assertFalse(gate.complete)

    def test_timeout_is_permanent_for_object(self):
        gate=ReportGate();gate.arm(3,100);gate.quarantine('timeout')
        with self.assertRaises(ValueError):gate.consume(events()[0])
        with self.assertRaises(ValueError):gate.arm(3,200)

    def test_unsolicited_duplicate_wrong_action_and_lifecycle_stop(self):
        for mutation in ('unsolicited','duplicate','action','lifecycle','loss','disconnect'):
            gate=ReportGate()
            if mutation != 'unsolicited':gate.arm(3,100)
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                if mutation=='duplicate':gate.consume(events()[0]);gate.consume(events()[0])
                elif mutation=='action':gate.consume(dict(events()[0],action=4))
                elif mutation=='lifecycle':gate.consume(dict(kind='lifecycle',invalidates=True))
                elif mutation=='loss':gate.consume(dict(kind='health',events_lost=1))
                elif mutation=='disconnect':gate.consume(dict(kind='connection',connected=False,changed=False))
                else:gate.consume(events()[0])
            self.assertIsNotNone(gate.reason)

    def test_cancel_even_if_success_is_rejected(self):
        gate=ReportGate();gate.arm(3,100)
        for event in events():gate.consume(event)
        with self.assertRaises(ValueError):gate.finish(dict(success=True,handle_closed=True,cancel_requested=True,qpc_request_before=105,qpc_request_completed=115))

    def test_report_preceding_actual_request_rejected(self):
        gate=ReportGate();gate.arm(3,100)
        for event in events():gate.consume(event)
        with self.assertRaises(ValueError):gate.finish(dict(success=True,handle_closed=True,qpc_request_before=130,qpc_request_completed=140))


if __name__ == '__main__':unittest.main()
