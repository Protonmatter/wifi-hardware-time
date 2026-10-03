import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experiments/qualcomm'))
from analyze_ftm_deltas import analyze, signed_delta


def fixture():
    return dict(schema='qcom-ftm-deltas/v1',driver_sha256='ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115',
                etl_sha256='1'*64,preview_sha256='2'*64,trace_health_sha256='3'*64,
                trace_events_lost=0,trace_buffers_lost=0,provider_events=5,
                events=[dict(field=k,value=str(v),ordinal=i+1,thread_id=7) for i,(k,v) in enumerate([
                    ('t3_del',80301671),('t4_del',80307643),('rtt',5972)])])


class DeltaTests(unittest.TestCase):
    def test_observed_delta_triplet(self):
        result=analyze(fixture())
        self.assertEqual(result['matched_triplets'],1)
        self.assertFalse(result['clock_offset_identifiable'])
        self.assertFalse(result['tsf_relationship_validated'])
        self.assertIsNone(result['absolute_event_time_unit'])

    def test_signed_modulo_subtraction(self):
        self.assertEqual(signed_delta(1,0),-1)
        self.assertEqual(signed_delta(0xffffffff,2),3)
        self.assertEqual(signed_delta(0,0x80000000),-2147483648)
        for bad in (True,-1,1<<32,1.5):
            with self.assertRaises(ValueError):signed_delta(bad,0)

    def test_rejects_loss_incomplete_wrong_order_thread_and_arithmetic(self):
        for mutation in ('loss','partial','duplicate','thread','math','number','build'):
            data=copy.deepcopy(fixture())
            if mutation=='loss':data['trace_events_lost']=1
            if mutation=='partial':data['events'].pop()
            if mutation=='duplicate':data['events'][1]=data['events'][0].copy()
            if mutation=='thread':data['events'][1]['thread_id']=8
            if mutation=='math':data['events'][2]['value']='5973'
            if mutation=='number':data['events'][0]['value']='080301671'
            if mutation=='build':data['driver_sha256']='0'*64
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):analyze(data)

    def test_empty_evidence_rejected(self):
        data=fixture();data['events']=[]
        with self.assertRaises(ValueError):analyze(data)

    def test_intervals_do_not_identify_offset(self):
        results=[]
        for offset in (250,10000):
            t1=1000000;t2=t1+100+offset;t3=t2+80;t4=t1+100+80+100
            results.append((t3-t2,t4-t1,signed_delta(t3-t2,t4-t1)))
        self.assertEqual(results[0],results[1])


if __name__=='__main__':unittest.main()
