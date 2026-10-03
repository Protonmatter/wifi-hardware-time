"""Guarded exact-build Qualcomm campaign. Windows/admin, explicit --execute.

Twelve captures: 3 idle and 3 local-workload repetitions of each approved sequence.
No reset, WLAN-profile change, FTM, register access, network workload or clock write.
Any failure leaves a persistent quarantine marker; this tool never clears it on retry.
"""
from __future__ import annotations
import argparse
import ctypes as ct
import datetime
import hashlib
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
import uuid

from campaign_gate import ReportGate
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from qualcomm_protocol import QUALIFIED_SHA256,validate_driver
from export_clock_evidence import normalize_run,export_sanitized
from campaign_admission import Admission,transition

PROVIDER='{bb6f5b93-635c-47be-816f-e895e77064a8}'
KINDS=('command','report','soc_timer','delay')
SEQUENCES={'read':[3]*12,'mixed':[3,3,4,3,3,4,3,3,4,3,3]}


def utc() -> str:return datetime.datetime.now(datetime.timezone.utc).isoformat()


def save(path: Path,data: object) -> None:
    path.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def run(command: list[str],timeout: float=30) -> subprocess.CompletedProcess:
    result=subprocess.run(command,capture_output=True,text=True,timeout=timeout)
    if result.returncode:raise RuntimeError(f'Command failed ({Path(command[0]).name}, exit {result.returncode}): {result.stderr[:400]}')
    return result


class TraceOwner:
    def __init__(self,session: str,folder: Path):
        self.session=session;self.folder=folder;self.attempted=False

    def start(self,options: list[str]) -> None:
        self.attempted=True
        result=run(['logman','start',self.session,*options])
        (self.folder/'trace-start.txt').write_text(result.stdout)

    def stop(self) -> None:
        if self.attempted:
            result=run(['logman','stop',self.session,'-ets'])
            (self.folder/'trace-stop.txt').write_text(result.stdout)
            self.attempted=False


def finalize_run(path: Path,summary: dict,verify) -> dict:
    summary.update(success=False,validation='pending')
    save(path,summary)
    try:
        summary.update(verify() or {})
        summary.update(success=True,validation='passed')
    except BaseException as error:
        summary.update(success=False,validation='failed',error=str(error))
        save(path,summary);raise
    save(path,summary)
    return summary


class Clock:
    def __init__(self):
        self.k=ct.WinDLL('kernel32',use_last_error=True)
        self.k.QueryPerformanceCounter.argtypes=[ct.POINTER(ct.c_int64)]
        self.k.QueryPerformanceFrequency.argtypes=[ct.POINTER(ct.c_int64)]
        self.k.CreateEventW.argtypes=[ct.c_void_p,ct.c_int,ct.c_int,ct.c_wchar_p];self.k.CreateEventW.restype=ct.c_void_p
        self.k.SetEvent.argtypes=[ct.c_void_p];self.k.SetEvent.restype=ct.c_int
        self.k.CloseHandle.argtypes=[ct.c_void_p];self.k.CloseHandle.restype=ct.c_int
        self.k.GetProcessTimes.argtypes=[ct.c_void_p,*([ct.POINTER(ct.c_uint64)]*4)]
        self.k.GetProcessTimes.restype=ct.c_int
        f=ct.c_int64()
        if not self.k.QueryPerformanceFrequency(ct.byref(f)) or f.value<=0:raise RuntimeError('No QPC frequency')
        self.frequency=f.value

    def now(self) -> int:
        q=ct.c_int64()
        if not self.k.QueryPerformanceCounter(ct.byref(q)):raise RuntimeError('QPC read failed')
        return q.value

    def cpu_seconds(self,process: subprocess.Popen) -> float:
        times=[ct.c_uint64() for _ in range(4)]
        # CPython Windows Popen retains the original process handle after exit;
        # avoid reopening by PID, which could refer to a reused process ID.
        if not self.k.GetProcessTimes(int(process._handle),*[ct.byref(t) for t in times]):
            raise ct.WinError(ct.get_last_error())
        return (times[2].value+times[3].value)/10_000_000


def identity(index: int) -> dict:
    data=json.loads(run(['powershell.exe','-NoProfile','-File',str(Path(__file__).with_name('Get-CampaignIdentity.ps1')),
                         '-InterfaceIndex',str(index)]).stdout)
    if data['Status']!='Up' or data['DriverVersion']!='1.0.4374.1300' or data['ServiceState']!='Running' or data['DriverFileName'].lower()!='qcwlanhmt8380.sys':
        raise RuntimeError('Adapter not Up on qualified driver')
    validate_driver(Path(data['DriverPath']).read_bytes())
    return data


def same_identity(current: dict,baseline: dict) -> None:
    for field in ('ifIndex','InterfaceGuid','PnPDeviceID','DriverVersion','DriverPath','ServiceState','Status'):
        if current[field]!=baseline[field]:raise RuntimeError(f'Identity/state changed: {field}')


class Observer:
    def __init__(self,session: str,index: int,folder: Path,clock: Clock):
        self.clock=clock;self.queue=queue.Queue();self.records=[];self.association=None
        self.ready=False;self.stopped=None;self.closing=False
        self.stop_name='Local\\WifiTimeStop-'+uuid.uuid4().hex
        self.stop=clock.k.CreateEventW(None,True,False,self.stop_name)
        if not self.stop:raise ct.WinError(ct.get_last_error())
        self.file=(folder/'live-observer.jsonl').open('w',encoding='utf-8')
        self.errors=(folder/'observer-stderr.txt').open('w',encoding='utf-8')
        try:
            self.process=subprocess.Popen([str(ROOT/'artifacts/live_observer.exe'),session,str(index),self.stop_name],
                                          stdout=subprocess.PIPE,stderr=self.errors,text=True,bufsize=1)
        except BaseException:
            clock.k.CloseHandle(self.stop);self.file.close();self.errors.close();raise
        self.reader=threading.Thread(target=self._read,daemon=True);self.reader.start()

    def _read(self):
        try:
            for line in self.process.stdout:
                self.queue.put((self.clock.now(),line))
        finally:self.queue.put((self.clock.now(),None))

    def pump(self,gate: ReportGate) -> None:
        while True:
            try:received,line=self.queue.get_nowait()
            except queue.Empty:break
            if line is None:
                if not self.closing:raise RuntimeError('Observer ended unexpectedly')
                continue
            record=json.loads(line);record['received_qpc']=received
            self.records.append(record);self.file.write(json.dumps(record)+'\n');self.file.flush()
            if record['kind']=='observer_stopped':
                self.stopped=record
                if not self.closing:raise RuntimeError('Observer stopped unexpectedly')
                continue
            if record['kind']=='ready':
                if self.ready or record['perf_frequency_hz']!=self.clock.frequency:raise RuntimeError('Observer clock mismatch')
                self.ready=True
            if record['kind']=='connection' and record.get('connected'):
                association=record['association']
                if self.association is not None and self.association!=association:raise RuntimeError('Observed AP changed')
                self.association=association
            gate.consume(record)
        if self.process.poll() is not None and not self.closing:raise RuntimeError('Observer process exited')

    def wait(self,seconds: float,gate: ReportGate) -> None:
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            self.pump(gate);time.sleep(0.02)
        self.pump(gate)

    def close(self,gate: ReportGate) -> None:
        self.closing=True
        # The controller stopped the ETW session first, allowing its final buffers
        # to drain naturally. Signal only if the consumer fails to finish in time.
        try:
            self.process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            self.clock.k.SetEvent(self.stop)
            try:self.process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                self.process.kill();self.process.wait(timeout=5)
                raise RuntimeError('Observer forced termination; cleanup unqualified')
        finally:
            self.reader.join(timeout=2)
            self.clock.k.CloseHandle(self.stop)
        try:
            self.pump(gate)
            if self.reader.is_alive() or self.process.returncode or not self.stopped or self.stopped['failed']:
                raise RuntimeError('Observer cleanup failed')
        finally:
            self.file.close();self.errors.close();self.process.stdout.close()


def workload(stop_path: Path,output: Path) -> int:
    # One process, SHA-256 on a fixed 64 KiB buffer; 10 ms work / 10 ms sleep.
    start=time.monotonic();cpu=time.process_time();cycles=0;payload=bytes(65536)
    while not stop_path.exists() and time.monotonic()-start<120:
        end=time.monotonic()+0.010
        while time.monotonic()<end:hashlib.sha256(payload).digest();cycles+=1
        time.sleep(0.010)
    save(output,dict(workload='sha256-one-process-10ms-on-10ms-off',wall_seconds=time.monotonic()-start,
                     cpu_seconds=time.process_time()-cpu,hash_operations=cycles,stop_requested=stop_path.exists()))
    return 0 if stop_path.exists() else 1


def capture(campaign: Path,index: int,baseline: dict,clock: Clock,name: str,actions: list[int],loaded: bool,
            expected_association: str | None,smoke: bool=False) -> dict:
    folder=campaign/name;folder.mkdir()
    session='WifiCampaign-'+uuid.uuid4().hex[:12]
    gate=ReportGate();observer=None;worker=None;failure=None;requests=[]
    trace=TraceOwner(session,folder);active_probe=None;admission=None
    begin=clock.now();cpu=time.process_time();children_cpu=0.0
    save(folder/'session.json',dict(SessionName=session,StartedUtc=utc(),SampleCount=len(actions),Actions=actions,MaxMB=32))
    try:
        before=identity(index);same_identity(before,baseline);save(folder/'adapter-before.json',before)
        trace.start(['-p',PROVIDER,'0x2000000000000010','0xff','-o',str(folder/'tsf.etl'),
                    '-f','bincirc','-max','32','-rt','-ct','perf','-ft','00:00:01','-ets'])
        observer=Observer(session,index,folder,clock)
        observer.wait(2.5,gate)
        if not observer.ready or observer.association is None:raise RuntimeError('Observer readiness/association not established')
        if expected_association is not None and observer.association!=expected_association:raise RuntimeError('AP changed between captures')
        if loaded:
            worker=subprocess.Popen([sys.executable,__file__,'--workload',str(folder/'workload-stop'),str(folder/'workload.json')],
                                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            observer.wait(1,gate)
        for number,action in enumerate(actions,1):
            current=identity(index);same_identity(current,baseline)
            observer.pump(gate)
            if worker is not None and worker.poll() is not None:raise RuntimeError('Workload exited prematurely')
            request_path=folder/f'request-{number:03}.json'
            gate.arm(action,clock.now())
            control=folder/f'submission-{number:03}.json'
            save(control,dict(state='prepared',pid=None,abort_requested=False))
            admission=Admission(control,'Local\\WifiAdmission-'+uuid.uuid4().hex,create=True)
            permitted=False
            with (folder/f'probe-{number:03}.stdout').open('w') as stdout,(folder/f'probe-{number:03}.stderr').open('w') as stderr:
                process=subprocess.Popen([sys.executable,str(ROOT/'tools/qualcomm_probe.py'),'--if-index',str(index),
                    '--command','tsf_read_value','--tsf-action',str(action),'--execute','--output',str(request_path),
                    '--campaign-control',str(control),'--campaign-mutex',admission.name],stdout=stdout,stderr=stderr)
                active_probe=process
                with admission.locked():
                    tracking=json.loads(control.read_text());tracking['pid']=process.pid;save(control,tracking)
                deadline=time.monotonic()+15
                while process.poll() is None or not gate.complete:
                    observer.pump(gate)
                    if not permitted:
                        with admission.locked():
                            if json.loads(control.read_text())['state']=='ready':
                                observer.pump(gate)
                                transition(control,'permit');permitted=True
                    if process.poll() is not None and process.returncode:raise RuntimeError('Private probe failed')
                    if time.monotonic()>deadline:
                        save(folder/'pending-probe.json',dict(pid=process.pid,still_running=process.poll() is None))
                        # Never kill a process whose overlapped IOCTL may still own buffers.
                        raise RuntimeError('Request/report deadline; pending probe retained if draining')
                    time.sleep(0.02)
                if process.returncode:raise RuntimeError('Private probe failed')
                children_cpu+=clock.cpu_seconds(process)
            request=json.loads(request_path.read_text(encoding='utf-8'))
            if request['driver_sha256']!=QUALIFIED_SHA256 or request['qpc_frequency_hz']!=clock.frequency:raise RuntimeError('Request build/clock mismatch')
            records=list(gate.records)
            gate.finish(request);requests.append(request)
            save(folder/f'admission-{number:03}.json',dict(sequence=number,action=action,records=records,accepted_qpc=clock.now()))
            active_probe=None;admission.close();admission=None
            # Retain minimum historical spacing; ETW delivery adds latency.
            observer.wait(0.5 if name.find('mixed')>=0 else 0.25,gate)
        observer.wait(2.0,gate)
    except BaseException as error:
        gate.quarantine(str(error));failure=str(error)
        if admission is not None:
            try:
                with admission.locked():transition(admission.path,'abort')
            except BaseException as revoke_error:
                failure+=f'; admission revoke uncertain: {revoke_error}'
        if active_probe is not None:
            save(folder/'pending-probe.json',dict(pid=active_probe.pid,still_running=active_probe.poll() is None,
                submission_control=str(admission.path) if admission else None,forced_termination=False))
    finally:
        if admission is not None:admission.close()
        if worker is not None:
            (folder/'workload-stop').touch()
            try:
                worker.wait(timeout=5)
                if worker.returncode:raise RuntimeError('Workload ended without controlled stop')
            except BaseException as error:
                failure=failure or str(error)
                if worker.poll() is None:worker.kill();worker.wait(timeout=5)
        try:trace.stop()
        except BaseException as error:failure=failure or f'Trace cleanup: {error}'
        if observer is not None:
            try:observer.close(gate)
            except BaseException as error:failure=failure or f'Observer cleanup: {error}'
        try:
            after=identity(index);save(folder/'adapter-after.json',after);same_identity(after,baseline)
        except BaseException as error:failure=failure or f'Final identity: {error}'
    summary=dict(name=name,success=False,validation='failed' if failure else 'pending',error=failure,request_count=len(requests),
                 planned_count=len(actions),wall_seconds=(clock.now()-begin)/clock.frequency,
                 controller_cpu_seconds=time.process_time()-cpu,probe_cpu_seconds=children_cpu,
                 cpu_scope='controller and private-probe processes only; excludes PowerShell discovery, kernel and logman',
                 firmware_sampling_validated=False,external_uncertainty_ns=None)
    save(folder/'run-result.json',summary)
    if failure:raise RuntimeError(f'{name}: {failure}')
    def verify():
        decoded=run([str(ROOT/'artifacts/decode_tsf_etl.exe'),str(folder/'tsf.etl')])
        (folder/'raw-timing.jsonl').write_text(decoded.stdout,encoding='utf-8')
        offline=[json.loads(line) for line in decoded.stdout.splitlines()]
        live=[{k:v for k,v in event.items() if k!='received_qpc'} for event in observer.records if event['kind'] in KINDS]
        timing=[event for event in offline if event['kind'] in KINDS]
        if live!=timing:raise RuntimeError(f'{name}: live/offline timing records disagree')
        result=dict(live_offline_records_equal=True,observer_cpu_seconds=clock.cpu_seconds(observer.process),
                    observer_clean_stop=True,association=observer.association)
        if smoke:
            if timing or offline[0]['events_lost'] or offline[0]['buffers_lost']:
                raise RuntimeError('Passive observer preflight contained timing activity or trace loss')
        else:
            receipt=export_sanitized(normalize_run(folder),folder/'evidence.json')
            result['evidence_sha256']=receipt.sha256
        return result
    return finalize_run(folder/'run-result.json',summary,verify)


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--if-index',type=int)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--workload',nargs=2,metavar=('STOP','OUTPUT'))
    args=parser.parse_args()
    if args.workload:return workload(Path(args.workload[0]),Path(args.workload[1]))
    if os.name!='nt' or not args.if_index or args.if_index<1:parser.error('Windows and explicit positive --if-index required')
    if not args.execute:
        print(json.dumps(dict(execute=False,runs=12,requests=138,private_device_opened=False)));return 0
    if not ct.windll.shell32.IsUserAnAdmin():raise SystemExit('Administrator launch required')
    marker=ROOT/'artifacts/qualcomm-campaign-active-or-quarantined.json'
    if marker.exists():raise SystemExit('Campaign quarantine/active marker exists; no automatic rearm')
    clock=Clock();baseline=identity(args.if_index)
    for executable in ('live_observer.exe','decode_tsf_etl.exe'):
        if not (ROOT/'artifacts'/executable).is_file():raise SystemExit(f'Missing {executable}')
    campaign=ROOT/'artifacts'/('QualcommCampaign-'+uuid.uuid4().hex[:12]);campaign.mkdir()
    with marker.open('x',encoding='utf-8') as file:json.dump(dict(state='active',path=str(campaign),started_utc=utc()),file)
    results=[];association=None
    save(campaign/'campaign.json',dict(started_utc=utc(),driver_sha256=QUALIFIED_SHA256,planned_runs=12,planned_requests=138,
        sequences=SEQUENCES,minimum_spacing_ms=dict(read=250,mixed=500),report_process_deadline_s=15,
        collector_binaries={name:hashlib.sha256((ROOT/'artifacts'/name).read_bytes()).hexdigest() for name in ('live_observer.exe','decode_tsf_etl.exe')}))
    try:
        for repetition in range(1,3):
            name=f'passive-observer-{repetition}'
            print(json.dumps(dict(event='observer_preflight',run=name,utc=utc())),flush=True)
            result=capture(campaign,args.if_index,baseline,clock,name,[],False,association,smoke=True)
            association=result['association']
            save(campaign/f'{name}.json',result)
        for phase in ('idle','workload'):
            for sequence,actions in SEQUENCES.items():
                for repetition in range(1,4):
                    name=f'{phase}-{sequence}-{repetition}'
                    print(json.dumps(dict(event='run_start',run=name,utc=utc())),flush=True)
                    result=capture(campaign,args.if_index,baseline,clock,name,actions,phase=='workload',association)
                    association=result.pop('association');results.append(result)
                    save(campaign/'results.json',results)
                    print(json.dumps(dict(event='run_complete',run=name,requests=result['request_count'])),flush=True)
        save(campaign/'final.json',dict(success=True,runs=len(results),quarantined=False,completed_utc=utc()))
        marker.unlink()
        print(json.dumps(dict(campaign=str(campaign),success=True)),flush=True);return 0
    except BaseException as error:
        failure=dict(state='quarantined',path=str(campaign),reason=str(error),completed_runs=len(results),utc=utc(),automatic_rearm=False)
        save(marker,failure);save(campaign/'final.json',failure)
        print(json.dumps(failure),flush=True);return 1


if __name__=='__main__':raise SystemExit(main())
