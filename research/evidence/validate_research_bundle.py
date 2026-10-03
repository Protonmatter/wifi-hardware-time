"""Validate experimental clock evidence without importing the research repo.

This is an offline contract tool, not a clock runtime or trust authenticator.
Exit 0: structurally consistent observation bundle; exit 1: rejected input.
"""
from dataclasses import dataclass
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

DRIVER = 'ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115'


@dataclass(frozen=True)
class Validation:
    observation_count: int
    conversion_qualified: bool = False
    utc_qualified: bool = False


def _keys(value: Any, keys: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != set(keys.split()):
        raise ValueError('Missing or unsupported object fields')
    return value


def _decimal(value: Any, maximum: int = (1 << 63)-1) -> int:
    if type(value) is not str or not re.fullmatch(r'0|[1-9][0-9]{0,19}',value):
        raise ValueError('Require canonical decimal string')
    result=int(value)
    if result > maximum: raise ValueError('Counter overflow')
    return result


def _hex(value: Any, length: int = 64) -> None:
    if type(value) is not str or not re.fullmatch('[0-9a-f]{'+str(length)+'}',value):
        raise ValueError('Invalid provenance digest')


def validate_bundle(data: Any) -> Validation:
    _keys(data,'manifest observations')
    m=_keys(data['manifest'],'schema evidence_kind qualification bundle_id source_id epoch_id continuity association driver_sha256 counter_width counter_unit qpc_frequency_hz trace_loss adapter_endpoints_up source input_sha256')
    constants=dict(schema='wifi-clock-evidence/v1',qualification='experimental-observation-only',
        source_id='source-0',epoch_id='capture-0',continuity='unverified-between-observations',
        association='request-window-no-firmware-id',driver_sha256=DRIVER,counter_unit='raw-ticks-unqualified')
    if any(m[k] != v for k,v in constants.items()): raise ValueError('Unsupported contract, build or claim')
    if m['evidence_kind'] not in ('synthetic','hardware-observation'):raise ValueError('Unknown evidence kind')
    if type(m['counter_width']) is not int or m['counter_width'] != 64 or m['trace_loss'] is not False or m['adapter_endpoints_up'] is not True:
        raise ValueError('Invalid width, loss or endpoint status')
    if _decimal(m['qpc_frequency_hz']) == 0:raise ValueError('Zero frequency')
    _hex(m['bundle_id'])
    source=_keys(m['source'],'base_revision working_tree_sha256 exporter_sha256 publication_status')
    _hex(source['base_revision'],40);_hex(source['working_tree_sha256']);_hex(source['exporter_sha256'])
    if source['publication_status'] != 'local-unreviewed':raise ValueError('Unsupported publication claim')
    hashes=m['input_sha256']
    required={'session.json','raw-timing.jsonl','adapter-before.json','adapter-after.json'}
    if type(hashes) is not dict or not required.issubset(hashes):raise ValueError('Missing evidence digests')
    request_names=set(hashes)-required
    if not request_names or not all(re.fullmatch(r'request(?:-[0-9]{3})?\.json',name) for name in request_names):
        raise ValueError('Unsupported evidence filenames')
    for digest in hashes.values():_hex(digest)
    canonical=(json.dumps(hashes,sort_keys=True,separators=(',', ':'))+'\n').encode('utf-8')
    if hashlib.sha256(canonical).hexdigest() != m['bundle_id']:
        raise ValueError('Bundle identity does not match input digest map')
    samples=data['observations']
    if type(samples) is not list or not 1 <= len(samples) <= 12 or len(request_names) != len(samples):
        raise ValueError('Invalid observation count')
    if 'request.json' in request_names and len(request_names) != 1:raise ValueError('Mixed request names')
    previous=None
    for index,s in enumerate(samples):
        _keys(s,'sequence action tsf_raw soc_raw global_tsf_raw host_before_qpc host_completed_qpc report_qpc sampling_interval external_uncertainty_ns soc_semantics')
        if type(s['sequence']) is not int or s['sequence'] != index+1 or type(s['action']) is not int or s['action'] not in (3,4):
            raise ValueError('Sequence or action mismatch')
        if s['sampling_interval'] is not None or s['external_uncertainty_ns'] is not None:
            raise ValueError('Unqualified sampling or accuracy claim')
        semantics='cached_or_unknown' if s['action'] == 3 else 'capture_requested_not_atomic'
        if s['soc_semantics'] != semantics:raise ValueError('Freshness semantics mismatch')
        tsf=_decimal(s['tsf_raw'],(1 << 64)-1)
        _decimal(s['soc_raw'],(1 << 64)-1);_decimal(s['global_tsf_raw'],(1 << 64)-1)
        begin=_decimal(s['host_before_qpc']);completed=_decimal(s['host_completed_qpc']);report=_decimal(s['report_qpc'])
        if completed < begin or report < begin:raise ValueError('Invalid observation window')
        if previous is not None and (begin <= max(previous[0],previous[1]) or tsf <= previous[2]):
            raise ValueError('Overlap or counter discontinuity')
        previous=(completed,report,tsf)
    return Validation(len(samples))


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('bundle',type=Path)
    args=parser.parse_args()
    try:
        if args.bundle.stat().st_size > 1_048_576:raise ValueError('Bundle exceeds 1 MiB contract limit')
        result=validate_bundle(json.loads(args.bundle.read_text(encoding='utf-8')))
        print(json.dumps(vars(result)));return 0
    except (OSError,ValueError,TypeError) as error:
        print(f'Evidence rejected: {error}',file=sys.stderr);return 1


if __name__ == '__main__':raise SystemExit(main())
