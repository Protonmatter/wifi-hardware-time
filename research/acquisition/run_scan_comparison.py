"""Exact-interface quiet/scan/quiet comparison. Windows/admin, explicit --execute.

At most three documented WlanScan calls, one per bounded trial. No private IOCTL,
reset, profile/configuration change, register access, or system-clock write.
Scans may temporarily increase network latency. Stops on interference/failure.
All raw outputs are private. Existing private acquisition quarantine is preserved.
Exit 0 means valid experimental records, not firmware identity/clock qualification.
Exit 1 is rejection/failure; exit 2 is CLI usage. No automatic retry or rearm.
"""
from __future__ import annotations

import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import argparse
import ctypes as ct
import hashlib
import json
import time
import uuid

from research.acquisition.run_acquisition_campaign import Clock,Observer,TraceOwner,ReportGate,identity,same_identity,save,run,utc,ROOT,PROVIDER,KINDS
from research.acquisition.run_passive_observation import assess,sha,QUALIFIED_NATIVE,PINNED_PATHS as PASSIVE_PINS,reserve_capture
from research.windows_timestamps.ndis_evidence import load_json,decode_json
from research.acquisition.analyze_quarantined_tsf import integer

PINNED_PATHS=(*PASSIVE_PINS,'research/acquisition/run_scan_comparison.py')
QUIET_SECONDS=8
TAIL_SECONDS=8
COMPLETION_SECONDS=4
# At most three clients per bounded worker. Keep callbacks alive until process
# exit even if native deregistration/handle cleanup reports a failure.
_CALLBACK_KEEPALIVE=[]


class GUID(ct.Structure):
    _fields_=[('data1',ct.c_uint32),('data2',ct.c_uint16),('data3',ct.c_uint16),('data4',ct.c_ubyte*8)]


class Notification(ct.Structure):
    _fields_=[('source',ct.c_uint32),('code',ct.c_uint32),('guid',GUID),('data_size',ct.c_uint32),('data',ct.c_void_p)]


class ScanClient:
    """Only documented WLAN handle/scan functions; retain handle through tail."""
    def __init__(self,guid: str,clock: Clock):
        self.guid=GUID.from_buffer_copy(uuid.UUID(guid.strip('{}')).bytes_le)
        self.clock=clock;self.notifications=[];self.notification_headers=[];self.callback_errors=[];self.unregister_status=None
        self.dll=ct.WinDLL('wlanapi.dll');self.handle=ct.c_void_p()
        self.dll.WlanOpenHandle.argtypes=[ct.c_uint32,ct.c_void_p,ct.POINTER(ct.c_uint32),ct.POINTER(ct.c_void_p)]
        self.dll.WlanScan.argtypes=[ct.c_void_p,ct.POINTER(GUID),ct.c_void_p,ct.c_void_p,ct.c_void_p]
        self.dll.WlanCloseHandle.argtypes=[ct.c_void_p,ct.c_void_p]
        self.dll.WlanRegisterNotification.argtypes=[ct.c_void_p,ct.c_uint32,ct.c_int,ct.c_void_p,ct.c_void_p,ct.c_void_p,ct.POINTER(ct.c_uint32)]
        for name in ('WlanOpenHandle','WlanScan','WlanCloseHandle','WlanRegisterNotification'):getattr(self.dll,name).restype=ct.c_uint32
        version=ct.c_uint32()
        status=self.dll.WlanOpenHandle(2,None,ct.byref(version),ct.byref(self.handle))
        if status:raise OSError(f'WlanOpenHandle status {status}')
        self.used=False;self.attempted=False;self.receipt=None
        callback_type=ct.WINFUNCTYPE(None,ct.POINTER(Notification),ct.c_void_p)
        self._callback=callback_type(self._notification)
        _CALLBACK_KEEPALIVE.append(self)
        previous=ct.c_uint32()
        self.registration_status=int(self.dll.WlanRegisterNotification(self.handle,8,False,ct.cast(self._callback,ct.c_void_p),None,None,ct.byref(previous)))
        if self.registration_status:
            self.dll.WlanCloseHandle(self.handle,None);self.handle=None
            raise OSError(f'WlanRegisterNotification status {self.registration_status}')
        try:self.registered_qpc=clock.now()
        except BaseException:
            self.close();raise

    def _notification(self,data,context):
        try:
            event=data.contents
            qpc=self.clock.now();selected=bytes(event.guid)==bytes(self.guid)
            if len(self.notification_headers)>=256:
                if not self.callback_errors:self.callback_errors.append('Notification header limit')
                return
            self.notification_headers.append(dict(source=int(event.source),code=int(event.code),qpc=qpc,selected_interface=selected))
            if not selected or event.source!=8 or event.code not in (7,8):return
            self.notifications.append(dict(kind='scan_client_notification',source=int(event.source),code=int(event.code),qpc=qpc))
        except BaseException as error:
            if not self.callback_errors:self.callback_errors.append(str(error))

    def scan(self,clock: Clock) -> dict:
        if self.used:raise ValueError('Only one scan per client/trial')
        self.used=True
        before=clock.now()
        self.receipt=dict(api='WlanScan',status=None,qpc_before=before,qpc_after=None,
            qpc_frequency_hz=clock.frequency,private_requests=0,api_entry_attempted=True,
            notification_registration_status=self.registration_status,notification_registered_qpc=self.registered_qpc)
        self.attempted=True
        self.receipt['status']=int(self.dll.WlanScan(self.handle,ct.byref(self.guid),None,None,None))
        self.receipt['qpc_after']=clock.now()
        return self.receipt

    def close(self) -> int:
        previous=ct.c_uint32()
        self.unregister_status=int(self.dll.WlanRegisterNotification(self.handle,0,False,None,None,None,ct.byref(previous)))
        self.close_status=int(self.dll.WlanCloseHandle(self.handle,None));self.handle=None
        return self.unregister_status or self.close_status


class ScanGate(ReportGate):
    """Observation-only gate. Does not associate TSF records with any request."""
    def __init__(self):
        super().__init__();self.scan_begin=None;self.observed_count=0;self.previous_qpc=-1

    @property
    def complete(self):return False

    def arm(self,*args,**kwargs):self._fail('private_admission_not_supported')

    def begin_scan(self,qpc: int):
        if self.reason or self.scan_begin is not None:self._fail('scan_already_started_or_rejected')
        self.scan_begin=integer(qpc,63)

    def consume(self,record: dict):
        if self.reason:self._fail(self.reason)
        kind=record.get('kind')
        if self.scan_begin is None and (kind in KINDS or (kind=='lifecycle' and record.get('source')==8 and record.get('code') in (7,8))):
            self._fail('quiet_baseline_contaminated')
        if kind=='lifecycle' and record.get('source')==8 and record.get('code')==8:self._fail('observed_scan_failure')
        if kind=='command':self._fail('unexpected_private_tsf_command')
        if kind not in KINDS:
            super().consume(record);return
        try:
            stamp=integer(record['raw_timestamp'],63)
            if stamp<self.scan_begin or stamp<self.previous_qpc or self.observed_count>=64:raise ValueError('Late/unordered/excess timing records')
            if kind in ('report','delay'):integer(record['vdev'],32)
            if kind=='report':integer(record['tsf_raw'])
            if kind=='soc_timer':integer(record['soc_timer_raw']);integer(record['g_tsf_raw'])
            if kind=='delay':integer(record['tsf_delay_raw'],32)
        except (ValueError,KeyError,TypeError):self._fail('invalid_observation')
        self.previous_qpc=stamp;self.observed_count+=1


def scan_completion(records: list[dict],request: dict,frequency: int) -> int | None:
    before=integer(request['qpc_before'],63);after=integer(request['qpc_after'],63)
    if type(request['status']) is not int or request['status']!=0 or request['qpc_frequency_hz']!=frequency or after<before:
        raise ValueError('Scan request did not qualify')
    if type(request.get('notification_registration_status')) is not int or request['notification_registration_status']!=0 or integer(request['notification_registered_qpc'],63)>before:
        raise ValueError('Calling-client notification registration not qualified')
    notifications=[r for r in records if r.get('kind')=='scan_client_notification' and r.get('source')==8 and r.get('code') in (7,8)]
    if any(r['code']==8 for r in notifications) or len(notifications)>1:raise ValueError('Failed or ambiguous scan notification')
    if not notifications:return None
    qpc=integer(notifications[0]['qpc'],63)
    if not before<=qpc<=before+COMPLETION_SECONDS*frequency:raise ValueError('Scan notification outside deadline')
    return qpc


def assess_trial(live: list[dict],offline: list[dict],request: dict,frequency: int,notifications: list[dict]) -> dict:
    result=assess(live,offline,frequency)
    quiet=integer(request['quiet_started_qpc'],63)
    if request['qpc_before']-quiet<QUIET_SECONDS*frequency:raise ValueError('Short quiet baseline')
    for kind in ('ready','health','connection'):
        if not any(r.get('kind')==kind and integer(r['qpc'],63)<=quiet for r in live):
            raise ValueError('Missing readiness before quiet baseline')
    completion=scan_completion(notifications,request,frequency)
    if completion is None:raise ValueError('Missing scan completion')
    # The native observer is a separate client. Validate its interference signals
    # independently; a duplicate across clients is not two physical completions.
    observed=[dict(r,kind='scan_client_notification') for r in live if r.get('kind')=='lifecycle' and r.get('source')==8 and r.get('code') in (7,8)]
    scan_completion(observed,request,frequency)
    events=offline[1:-1]
    if any(r['kind']=='command' or r['raw_timestamp']<request['qpc_before'] for r in events):
        raise ValueError('Private timing command or quiet-baseline timing present')
    result.update(reports_after_scan_call=result['counts']['report'],scan_completion_qpc=completion,
        scan_notification_request_identity_qualified=False,firmware_initiator_identified=False)
    return result


def trial(folder: Path,index: int,baseline: dict,expected_association: str | None) -> dict:
    folder.mkdir();clock=Clock();gate=ScanGate();observer=None;client=None;errors=[];request=None;quiet=None
    trace=TraceOwner('WifiScanCompare-'+uuid.uuid4().hex[:12],folder)
    save(folder/'session.json',dict(SessionName=trace.session,started_utc=utc(),quiet_seconds=QUIET_SECONDS,tail_seconds=TAIL_SECONDS,max_scan_calls=1))
    try:
        current=identity(index);same_identity(current,baseline);save(folder/'adapter-before.json',current)
        trace.start(['-p',PROVIDER,'0x2000000000000010','0xff','-o',str(folder/'tsf.etl'),'-f','bincirc','-max','32','-rt','-ct','perf','-ft','00:00:01','-ets'])
        observer=Observer(trace.session,index,folder,clock)
        observer.wait(2.5,gate)
        if not observer.ready or observer.association is None or not any(r.get('kind')=='health' for r in observer.records):raise ValueError('Observer not ready/healthy')
        if expected_association is not None and observer.association!=expected_association:raise ValueError('Association changed across trials')
        quiet=clock.now();save(folder/'quiet-start.json',dict(qpc=quiet,qpc_frequency_hz=clock.frequency))
        observer.wait(QUIET_SECONDS,gate)
        current=identity(index);same_identity(current,baseline)
        client=ScanClient(baseline['InterfaceGuid'],clock)
        observer.pump(gate);gate.begin_scan(clock.now())
        request=client.scan(clock);request['quiet_started_qpc']=quiet;save(folder/'scan-request.json',request)
        if request['status']!=0:raise ValueError(f"WlanScan rejected with status {request['status']}; no retry")
        completion=None
        while clock.now()<=request['qpc_before']+COMPLETION_SECONDS*clock.frequency:
            observer.pump(gate)
            if client.callback_errors:raise ValueError('Scan callback failed')
            completion=scan_completion(list(client.notifications),request,clock.frequency)
            if completion is not None:break
            time.sleep(0.02)
        if completion is None:errors.append('Scan completion deadline; diagnostic tail retained without qualification')
        observer.wait(TAIL_SECONDS,gate)
    except BaseException as error:errors.append(str(error))
    finally:
        if client is not None:
            if client.receipt is not None:
                request=dict(client.receipt,quiet_started_qpc=quiet)
                try:save(folder/'scan-request.json',request)
                except BaseException as error:errors.append(f'Scan receipt persistence: {error}')
            try:
                status=client.close();save(folder/'scan-client-close.json',dict(status=status,unregister_status=client.unregister_status,close_status=client.close_status))
                save(folder/'scan-client-notifications.json',dict(records=client.notifications,headers=client.notification_headers,callback_errors=client.callback_errors))
                if client.callback_errors:raise ValueError('Scan callback failed')
                if status:raise ValueError(f'WlanCloseHandle status {status}')
            except BaseException as error:errors.append(f'Scan client cleanup: {error}')
        try:trace.stop()
        except BaseException as error:errors.append(f'Trace cleanup: {error}')
        if observer is not None:
            try:observer.close(gate)
            except BaseException as error:errors.append(f'Observer cleanup: {error}')
        try:
            current=identity(index);save(folder/'adapter-after.json',current);same_identity(current,baseline)
        except BaseException as error:errors.append(f'Final identity: {error}')
    result=dict(success=False,errors=errors,scan_calls=int(client is not None and client.attempted),private_requests=0,firmware_drain_proven=False,
        association=observer.association if observer else None,clock_relationship_qualified=False)
    try:
        raw=run([str(ROOT/'artifacts/decode_tsf_etl.exe'),str(folder/'tsf.etl')]).stdout
        (folder/'raw-timing.jsonl').write_text(raw,encoding='utf-8')
        if request is None or observer is None:raise ValueError('No completed scan call/observer')
        result['assessment']=assess_trial(observer.records,[json.loads(line) for line in raw.splitlines()],request,clock.frequency,list(client.notifications))
        if load_json(folder/'observer-cleanup.json').get('observer_clean_stop') is not True:raise ValueError('Unqualified observer cleanup')
    except BaseException as error:errors.append(f'Offline validation: {error}')
    result['success']=not errors;save(folder/'result.json',result);return result


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True);parser.add_argument('--manifest-sha256',required=True)
    parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    try:
        folder=args.manifest.resolve().parent
        if not folder.is_relative_to((ROOT/'artifacts').resolve()):raise ValueError('Manifest outside artifacts')
        with args.manifest.open('rb') as stream:raw=stream.read(65537)
        if len(raw)>65536 or hashlib.sha256(raw).hexdigest()!=args.manifest_sha256:raise ValueError('Manifest size/hash changed')
        manifest=decode_json(raw)
        trials=manifest.get('trials');prior=manifest.get('prior_scan_attempts',0)
        if manifest.get('schema')!='qualcomm-scan-comparison/v1' or type(trials) is not int or type(prior) is not int or not 1<=trials<=3 or not 0<=prior<=2 or prior+trials>3:raise ValueError('Exceeded three-call experiment budget')
        index=manifest['interface_index']
        if type(index) is not int or index<=0:raise ValueError('Explicit interface required')
        uuid.UUID(manifest['interface_guid'].strip('{}'))
        if set(manifest['hashes'])!=set(PINNED_PATHS):raise ValueError('Provenance set mismatch')
        for p in PINNED_PATHS:
            if sha(ROOT/p)!=manifest['hashes'][p]:raise ValueError('Input changed: '+p)
        for p,h in QUALIFIED_NATIVE.items():
            if manifest['hashes'][p]!=h:raise ValueError('Native qualification changed: '+p)
        marker=ROOT/'artifacts/qualcomm-campaign-active-or-quarantined.json'
        if sha(marker)!=manifest['quarantine_sha256'] or load_json(marker).get('state')!='quarantined':raise ValueError('Expected unchanged quarantine')
        if not args.execute:
            print(json.dumps(dict(execute=False,trials=trials,prior_scan_attempts=prior,max_scan_calls=3,private_requests=0)));return 0
        if not ct.windll.shell32.IsUserAnAdmin():raise ValueError('Administrator required for tracing')
        folder=reserve_capture(folder)
        lock=ROOT/'artifacts/passive-observation-active.json';token=uuid.uuid4().hex
        with lock.open('x',encoding='utf-8') as stream:json.dump(dict(token=token,folder=str(folder)),stream)
        outcome=dict(success=False,trials=[],private_requests=0,errors=[])
        try:
            baseline=identity(index)
            if baseline['InterfaceGuid'].strip('{}').lower()!=manifest['interface_guid'].strip('{}').lower():raise ValueError('Target identity changed')
            save(folder/'baseline.json',baseline);association=None
            for number in range(1,trials+1):
                if sha(marker)!=manifest['quarantine_sha256']:raise ValueError('Quarantine marker changed')
                result=trial(folder/f'trial-{number}',index,baseline,association)
                outcome['trials'].append(result);save(folder/'campaign.json',outcome)
                print(json.dumps(dict(trial=number,success=result['success'],scan_calls=result['scan_calls'],errors=result['errors'])),flush=True)
                if not result['success']:raise ValueError('Trial rejected; remaining trials not run')
                association=result['association']
            outcome['success']=True
        except BaseException as error:outcome['errors'].append(str(error))
        outcome['quarantine_unchanged']=sha(marker)==manifest['quarantine_sha256']
        if not outcome['quarantine_unchanged']:outcome['success']=False;outcome['errors'].append('Quarantine changed')
        save(folder/'campaign.json',outcome)
        if outcome['success']:
            if load_json(lock).get('token')!=token:raise ValueError('Lock ownership changed')
            lock.unlink()
        return 0 if outcome['success'] else 1
    except (OSError,ValueError,KeyError,TypeError,AttributeError) as error:parser.exit(1,f'Scan comparison rejected: {error}\n')


if __name__=='__main__':raise SystemExit(main())
