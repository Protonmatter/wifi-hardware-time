"""Normalize bounded saved Qualcomm captures. Offline; never opens a device.

Outputs contain raw numeric timing and hashes, so remain local pending review.
Exit 0: export completed; exit 1: invalid evidence or output failure.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from qualcomm_protocol import QUALIFIED_SHA256
from validate_research_bundle import validate_bundle

SCHEMA = 'wifi-clock-evidence/v1'
QUALIFICATION = 'experimental-observation-only'


def _integer(value: Any, name: str, maximum: int = (1 << 63)-1) -> int:
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError(f'Invalid integer: {name}')
    return value


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()


@dataclass(frozen=True)
class EvidenceBundle:
    manifest: dict[str, Any]
    observations: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class ExportReceipt:
    sha256: str
    observation_count: int


def _provenance() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[1]
    revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root, check=True,
                              capture_output=True, text=True).stdout.strip()
    # Include uncommitted and untracked authored files without exposing their text.
    names = subprocess.run(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
                           cwd=root, check=True, capture_output=True).stdout.decode().split('\0')
    file_hashes = {name: _digest((root/name).read_bytes()) if (root/name).is_file() else None
                   for name in sorted(set(names)-{''})}
    return {'base_revision': revision, 'working_tree_sha256': _digest(_canonical(file_hashes)),
            'exporter_sha256': _digest(Path(__file__).read_bytes()),
            'publication_status': 'local-unreviewed'}


def normalize_run(run: Path, *, evidence_kind: str = 'hardware-observation') -> EvidenceBundle:
    if evidence_kind not in ('hardware-observation', 'synthetic'):
        raise ValueError('Unknown evidence kind')
    session = _read(run/'session.json')
    paths = sorted(run.glob('request-*.json'))
    if paths and (run/'request.json').exists():
        raise ValueError('Mixed single and series requests')
    if not paths:
        paths = [run/'request.json']
    count = _integer(session.get('SampleCount', 1), 'SampleCount', 12)
    if not count or len(paths) != count:
        raise ValueError('Incomplete planned capture')
    requests = [_read(path) for path in paths]
    events = [json.loads(line) for line in (run/'raw-timing.jsonl').read_text(encoding='utf-8-sig').splitlines() if line.strip()]
    headers = [e for e in events if e.get('kind') == 'header']
    summaries = [e for e in events if e.get('kind') == 'summary']
    if len(headers) != 1 or len(summaries) != 1 or events[0] != headers[0] or events[-1] != summaries[0]:
        raise ValueError('Missing or misplaced trace boundary')
    header, summary = headers[0], summaries[0]
    for name in ('events_lost', 'buffers_lost'):
        if _integer(header[name], name) != 0: raise ValueError('Trace loss')
    for name in ('process_status', 'close_status'):
        if _integer(summary[name], name) != 0: raise ValueError('Trace decoding failure')
    frequency = _integer(header['perf_frequency_hz'], 'frequency')
    if not frequency or type(header['clock_type']) is not int or header['clock_type'] != 1:
        raise ValueError('Require QPC trace')
    actions = session.get('Actions', [3]*count)
    if type(actions) is not list or len(actions) != count or any(type(a) is not int or a not in (3,4) for a in actions):
        raise ValueError('Unsupported action sequence')
    index = _integer(requests[0]['interface_index'], 'interface_index')
    adapter_paths = [run/'adapter-before.json',run/'adapter-after.json']
    for path in adapter_paths:
        adapter = _read(path)
        if adapter.get('Status') != 'Up' or adapter.get('DriverVersion') != '1.0.4374.1300' or type(adapter.get('ifIndex')) is not int or adapter['ifIndex'] != index:
            raise ValueError('Adapter endpoint mismatch or not Up')
    starts = []
    for i, request in enumerate(requests):
        start = _integer(request['qpc_request_before'], 'request start')
        completed = _integer(request['qpc_request_completed'], 'request completion')
        if (request['success'] is not True or request['handle_closed'] is not True or
            request['command'] != 'tsf_read_value' or request['driver_sha256'] != QUALIFIED_SHA256 or
            _integer(request['interface_index'], 'interface') != index or
            _integer(request['qpc_frequency_hz'], 'request frequency') != frequency or
            _integer(request['firmware_action'], 'action') != actions[i] or completed < start):
            raise ValueError('Invalid request, build, target or action')
        if starts and (start <= starts[-1] or requests[i-1]['qpc_request_completed'] >= start):
            raise ValueError('Overlapping or unordered requests')
        starts.append(start)
    kinds = ('command','report','soc_timer','delay')
    if any(sum(e.get('kind') == kind for e in events) != count for kind in kinds):
        raise ValueError('Missing or duplicate records')
    for event in events[1:-1]:
        if event.get('kind') not in kinds: raise ValueError('Unknown trace record')
        _integer(event['raw_timestamp'], 'event timestamp')
    observations = []
    vdev = None
    for i, request in enumerate(requests):
        stop = starts[i+1] if i+1 < count else (1 << 63)
        selected = [[e for e in events[1:-1] if e['kind'] == kind and starts[i] <= e['raw_timestamp'] < stop] for kind in kinds]
        if any(len(group) != 1 for group in selected):
            raise ValueError('Ambiguous request window; no firmware transaction ID')
        command, report, soc, delay = [group[0] for group in selected]
        if not command['raw_timestamp'] <= report['raw_timestamp'] <= soc['raw_timestamp'] <= delay['raw_timestamp']:
            raise ValueError('Unexpected event order')
        identities = [_integer(e['vdev'], 'vdev', 255) for e in (command,report,delay)]
        if len(set(identities)) != 1 or (vdev is not None and identities[0] != vdev):
            raise ValueError('Mixed vdev')
        vdev = identities[0]
        if _integer(command['action'], 'command action') != actions[i]: raise ValueError('Wrong command action')
        tsf = _integer(report['tsf_raw'], 'TSF', (1 << 64)-1)
        soc_raw = _integer(soc['soc_timer_raw'], 'SoC', (1 << 64)-1)
        global_tsf = _integer(soc['g_tsf_raw'], 'global TSF', (1 << 64)-1)
        if _integer(delay['tsf_delay_raw'], 'delay', (1 << 32)-1) != ((tsf-soc_raw)&0xffffffff):
            raise ValueError('Wrong delay arithmetic')
        if observations and tsf <= int(observations[-1]['tsf_raw']):
            raise ValueError('Counter discontinuity; do not join epochs')
        observations.append(dict(sequence=i+1, action=actions[i], tsf_raw=str(tsf), soc_raw=str(soc_raw),
            global_tsf_raw=str(global_tsf), host_before_qpc=str(starts[i]),
            host_completed_qpc=str(request['qpc_request_completed']), report_qpc=str(report['raw_timestamp']),
            sampling_interval=None, external_uncertainty_ns=None,
            soc_semantics='cached_or_unknown' if actions[i] == 3 else 'capture_requested_not_atomic'))
    inputs = [run/'session.json',run/'raw-timing.jsonl',*paths,*adapter_paths]
    input_hashes = {path.name:_digest(path.read_bytes()) for path in inputs}
    bundle_id = _digest(_canonical(input_hashes))
    manifest = dict(schema=SCHEMA, evidence_kind=evidence_kind, qualification=QUALIFICATION,
        bundle_id=bundle_id, source_id='source-0', epoch_id='capture-0',
        continuity='unverified-between-observations', association='request-window-no-firmware-id',
        driver_sha256=QUALIFIED_SHA256, counter_width=64, counter_unit='raw-ticks-unqualified',
        qpc_frequency_hz=str(frequency), trace_loss=False, adapter_endpoints_up=True,
        source=_provenance(), input_sha256=input_hashes)
    return EvidenceBundle(manifest, tuple(observations))


def export_sanitized(bundle: EvidenceBundle, output: Path) -> ExportReceipt:
    data=dict(manifest=bundle.manifest, observations=list(bundle.observations))
    validate_bundle(data)
    payload = _canonical(data)
    # Never replace an existing result, including one left from a failed run.
    with output.open('xb') as stream:
        stream.write(payload)
    return ExportReceipt(_digest(payload), len(bundle.observations))


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--synthetic',action='store_true')
    args=parser.parse_args()
    try:
        result=export_sanitized(normalize_run(args.run,evidence_kind='synthetic' if args.synthetic else 'hardware-observation'), args.output)
        print(json.dumps(dict(sha256=result.sha256, observation_count=result.observation_count)))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        print(f'Export failed: {type(error).__name__}: {error}',file=sys.stderr)
        return 1


if __name__ == '__main__': raise SystemExit(main())
