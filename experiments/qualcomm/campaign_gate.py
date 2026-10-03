"""Fail-closed live report admission; does not establish firmware sampling/drain."""
from typing import Any


class ReportGate:
    def __init__(self) -> None:
        self.reason: str | None=None
        self.action: int | None=None
        self.begin=0
        self.records: list[dict[str,Any]]=[]
        self.vdev: int | None=None
        self.last_tsf: int | None=None

    def quarantine(self,reason: str) -> None:
        if self.reason is None:self.reason=reason

    def _fail(self,reason: str) -> None:
        self.quarantine(reason)
        raise ValueError(self.reason)

    @property
    def complete(self) -> bool:
        return self.reason is None and len(self.records)==4

    def arm(self,action: int,begin: int) -> None:
        if self.reason or self.action is not None or type(action) is not int or action not in (3,4):
            self._fail('cannot_arm_quarantined_or_pending_request')
        self.action=action;self.begin=begin;self.records=[]

    def consume(self,event: dict[str,Any]) -> None:
        if self.reason:self._fail(self.reason)
        kind=event.get('kind')
        if kind=='lifecycle':
            if event.get('invalidates'):self._fail('lifecycle_notification')
            return
        if kind=='health':
            names=('query_status','events_lost','log_buffers_lost','real_time_buffers_lost')
            if event.get('health_source')!='controller_query' or any(type(event.get(name)) is not int or not 0<=event[name]<=0xffffffff for name in names):
                self._fail('unqualified_live_trace_health')
            if event['query_status']:self._fail('live_trace_health_query_failed')
            if any(event[name] for name in names[1:]):self._fail('live_trace_loss')
            return
        if kind=='connection':
            if not event.get('connected') or event.get('changed'):self._fail('association_changed_or_query_failed')
            return
        if kind=='ready':
            if event.get('health_schema')!='controller-query/v1':self._fail('unqualified_observer_protocol')
            return
        if kind not in ('command','report','soc_timer','delay'):self._fail('unexpected_observer_record')
        expected=('command','report','soc_timer','delay')
        if self.action is None or len(self.records)>=4 or kind!=expected[len(self.records)]:
            self._fail('unsolicited_duplicate_or_out_of_order_record')
        timestamp=event.get('raw_timestamp')
        if type(timestamp) is not int or timestamp < self.begin or (self.records and timestamp<self.records[-1]['raw_timestamp']):
            self._fail('late_or_unordered_timestamp')
        if kind=='command' and event.get('action')!=self.action:self._fail('wrong_action')
        if kind in ('command','report','delay'):
            vdev=event.get('vdev')
            if type(vdev) is not int or (self.vdev is not None and vdev!=self.vdev):self._fail('vdev_changed')
            self.vdev=vdev
        self.records.append(event)
        if self.complete:
            tsf=self.records[1]['tsf_raw'];soc=self.records[2]['soc_timer_raw']
            if ((tsf-soc)&0xffffffff)!=event['tsf_delay_raw']:self._fail('delay_arithmetic_mismatch')
            if self.last_tsf is not None and tsf<=self.last_tsf:self._fail('counter_discontinuity')

    def finish(self,request: dict[str,Any]) -> None:
        if not self.complete or request.get('success') is not True or request.get('handle_closed') is not True or request.get('cancel_requested'):
            self._fail('incomplete_failed_or_cancelled_request')
        begin=request['qpc_request_before'];end=request['qpc_request_completed']
        if begin<self.begin or end<begin or any(e['raw_timestamp']<begin for e in self.records):
            self._fail('report_not_in_actual_request_window')
        self.last_tsf=self.records[1]['tsf_raw'];self.action=None;self.records=[]
