"""Bounded passive ETW observation while private acquisition remains quarantined.

Windows/admin and explicit --execute; requires a hashed, exact-source manifest.
No private device open, IOCTL, firmware command or change to campaign quarantine.
Exit 0: complete healthy observation (possibly stopped on timing activity).
Exit 1: preflight/observation/cleanup failure. Exit 2: invalid CLI usage.
All capture outputs contain private evidence and belong in ignored artifacts.
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
import uuid

from research.acquisition.run_acquisition_campaign import Clock,Observer,TraceOwner,identity,same_identity,save,run,utc,ROOT,PROVIDER,KINDS
from research.acquisition.campaign_gate import ReportGate
from research.acquisition.analyze_quarantined_tsf import summarize_timing
from research.windows_timestamps.ndis_evidence import load_json,decode_json

PINNED_PATHS=('research/acquisition/run_passive_observation.py',
    'research/acquisition/Invoke-PassiveObservation.ps1',
    'research/acquisition/run_acquisition_campaign.py','research/acquisition/campaign_gate.py',
    'research/acquisition/live_observer.c','research/tsf/decode_tsf_etl.c',
    'research/acquisition/analyze_quarantined_tsf.py','research/windows_timestamps/ndis_evidence.py',
    'research/acquisition/Get-CampaignIdentity.ps1','research/tsf/qualcomm_protocol.py',
    'artifacts/live_observer.exe','artifacts/decode_tsf_etl.exe')

# Selected binaries and matching sources from the completed passive qualification.
# Observer source differs only in its relocated decoder include; a regression
# verifies normalization to the qualified original source hash. No binary changed.
# A new native build still requires its own qualification and deliberate pin update.
QUALIFIED_NATIVE={
    'artifacts/live_observer.exe':'afc40361b7037213cf3315a1765205f65bc1e90ebabefb5293796b42e7e3e134',
    'artifacts/decode_tsf_etl.exe':'eef943146fcafc7d7cb00285e0c4d02345fe528af23ae5c6586d6bab14f43bc7',
    'research/acquisition/live_observer.c':'d9fbeebe8e9061410821a6bc7d5d5547fb8e43aa5aa0f28e9d468627dc6c0f70',
    'research/tsf/decode_tsf_etl.c':'5cb31b87aed849c006295cbd53461c3fdc820660668d4b7d4a242dc18683cea9'}


def sha(path: Path) -> str:return hashlib.sha256(path.read_bytes()).hexdigest()


def reserve_capture(parent: Path) -> Path:
    folder=parent/'capture'
    folder.mkdir()  # Exclusive: replaying a manifest must never replace evidence.
    return folder


def assess(live: list[dict],offline: list[dict],frequency: int) -> dict:
    """Validate the complete saved tail; never admit or arm a private request."""
    ready=[r for r in live if r.get('kind')=='ready']
    stops=[r for r in live if r.get('kind')=='observer_stopped']
    if len(ready)!=1 or ready[0].get('perf_frequency_hz')!=frequency or len(stops)!=1:
        raise ValueError('Incomplete readiness/stop evidence')
    stop=stops[0]
    if stop.get('failed') is not False or type(stop.get('process_status')) is not int or stop['process_status'] not in (0,1223) or type(stop.get('close_status')) is not int or stop['close_status'] not in (0,7007):
        raise ValueError('Unqualified observer stop')
    gate=ReportGate();health=0;connections=0;association=None
    for record in live:
        kind=record.get('kind')
        if kind in KINDS or kind=='observer_stopped':continue
        gate.consume(record)
        if kind=='health':health+=1
        if kind=='connection':
            if type(record.get('query_status')) is not int or record['query_status']!=0 or record.get('connected') is not True or record.get('changed') is not False:
                raise ValueError('Unqualified connection evidence')
            if type(record.get('association')) is not str or not record['association']:raise ValueError('Missing association')
            if association is not None and record['association']!=association:raise ValueError('Association changed')
            association=record['association'];connections+=1
    if not health or not connections:raise ValueError('Missing health/connection evidence')
    result=summarize_timing(offline)
    if result['qpc_frequency_hz']!=frequency:raise ValueError('Offline clock mismatch')
    timing=[{k:v for k,v in r.items() if k!='received_qpc'} for r in live if r.get('kind') in KINDS]
    if timing!=offline[1:-1]:raise ValueError('Live/offline records disagree')
    result.update(health_records=health,connection_records=connections,live_offline_equal=True,
        firmware_drain_proven=False,clock_relationship_qualified=False,private_requests=0)
    return result


def observe(folder: Path,manifest: dict,marker: Path) -> dict:
    clock=Clock();baseline=identity(manifest['interface_index'])
    if baseline['InterfaceGuid'].strip('{}').lower()!=manifest['interface_guid'].strip('{}').lower():
        raise ValueError('Selected interface changed')
    save(folder/'adapter-before.json',baseline)
    session='WifiPassive-'+uuid.uuid4().hex[:12]
    save(folder/'session.json',dict(SessionName=session,seconds=manifest['seconds'],private_requests=0,started_utc=utc()))
    trace=TraceOwner(session,folder);observer=None;gate=ReportGate();errors=[];timing_stop=False
    begin=clock.now()
    try:
        trace.start(['-p',PROVIDER,'0x2000000000000010','0xff','-o',str(folder/'tsf.etl'),
            '-f','bincirc','-max','32','-rt','-ct','perf','-ft','00:00:01','-ets'])
        observer=Observer(session,manifest['interface_index'],folder,clock)
        observer.wait(manifest['seconds'],gate)
    except BaseException as error:
        timing_stop=gate.reason=='unsolicited_duplicate_or_out_of_order_record'
        if not timing_stop:errors.append(str(error))
    finally:
        try:trace.stop()
        except BaseException as error:errors.append(f'Trace cleanup: {error}')
        if observer is not None:
            try:observer.close(gate)
            except BaseException as error:errors.append(f'Observer cleanup: {error}')
        try:
            final=identity(manifest['interface_index']);save(folder/'adapter-after.json',final);same_identity(final,baseline)
        except BaseException as error:errors.append(f'Final identity: {error}')
    result=dict(success=False,errors=errors,stopped_on_timing=timing_stop,private_requests=0,
        requested_seconds=manifest['seconds'],total_wall_seconds=(clock.now()-begin)/clock.frequency,
        firmware_drain_proven=False,clock_relationship_qualified=False)
    try:
        decoded=run([str(ROOT/'artifacts/decode_tsf_etl.exe'),str(folder/'tsf.etl')])
        (folder/'raw-timing.jsonl').write_text(decoded.stdout,encoding='utf-8')
        offline=[json.loads(line) for line in decoded.stdout.splitlines()]
        if observer is None:raise ValueError('Observer missing')
        result['assessment']=assess(observer.records,offline,clock.frequency)
        cleanup=load_json(folder/'observer-cleanup.json')
        if cleanup.get('observer_clean_stop') is not True or cleanup.get('evidence_drained') is not True:
            raise ValueError('Cleanup receipt did not qualify')
        result['cleanup']=cleanup
    except BaseException as error:errors.append(f'Offline validation: {error}')
    result['quarantine_unchanged']=sha(marker)==manifest['quarantine_sha256']
    if not result['quarantine_unchanged']:errors.append('Private quarantine marker changed')
    result['success']=not errors
    save(folder/'result.json',result)
    return result


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--manifest-sha256',required=True)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    try:
        folder=args.manifest.resolve().parent
        if not folder.is_relative_to((ROOT/'artifacts').resolve()):raise ValueError('Manifest must be under ignored artifacts')
        with args.manifest.open('rb') as stream:raw=stream.read(65537)
        if len(raw)>65536 or hashlib.sha256(raw).hexdigest()!=args.manifest_sha256:raise ValueError('Manifest hash/size changed')
        manifest=decode_json(raw)
        if manifest.get('schema')!='qualcomm-passive-manifest/v1':raise ValueError('Manifest schema mismatch')
        if type(manifest.get('seconds')) is not int or not 1<=manifest['seconds']<=30:raise ValueError('Duration must be 1..30 seconds')
        if type(manifest.get('interface_index')) is not int or manifest['interface_index']<=0:raise ValueError('Explicit interface required')
        if type(manifest.get('interface_guid')) is not str:raise ValueError('Explicit interface identity required')
        if set(manifest['hashes'])!=set(PINNED_PATHS):raise ValueError('Missing source/binary provenance')
        for path in PINNED_PATHS:
            if sha(ROOT/path)!=manifest['hashes'][path]:raise ValueError('Input changed: '+path)
        for path,expected in QUALIFIED_NATIVE.items():
            if manifest['hashes'][path]!=expected:raise ValueError('Native observer/decoder qualification changed: '+path)
        marker=ROOT/'artifacts/qualcomm-campaign-active-or-quarantined.json'
        if sha(marker)!=manifest['quarantine_sha256'] or load_json(marker).get('state')!='quarantined':
            raise ValueError('Expected unchanged private quarantine')
        if not args.execute:
            print(json.dumps(dict(execute=False,seconds=manifest['seconds'],private_requests=0)));return 0
        if not ct.windll.shell32.IsUserAnAdmin():raise ValueError('Administrator token required')
        folder=reserve_capture(folder)
        lock=ROOT/'artifacts/passive-observation-active.json'
        token=uuid.uuid4().hex
        with lock.open('x',encoding='utf-8') as stream:json.dump(dict(token=token,folder=str(folder)),stream)
        result=observe(folder,manifest,marker)
        if result['success']:
            if load_json(lock).get('token')!=token:raise ValueError('Passive lock ownership changed')
            lock.unlink()
        print(json.dumps({k:v for k,v in result.items() if k not in ('assessment','cleanup')},indent=2))
        return 0 if result['success'] else 1
    except (OSError,ValueError,KeyError,TypeError,AttributeError) as error:
        parser.exit(1,f'Passive observation rejected: {error}\n')


if __name__=='__main__':raise SystemExit(main())
