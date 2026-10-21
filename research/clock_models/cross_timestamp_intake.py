"""Read-only audit of saved Windows NIC/QPC tuples; never qualifies Gate 1.

Usage: python -m research.clock_models.cross_timestamp_intake MANIFEST.json
Exit 0: structurally ready for semantic review; 2: unresolved intake blockers;
1: invalid input or unreadable evidence. No network or adapter access occurs.
See docs/clock-models/replacement-timestamp-acquisition.md for the contract.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
import logging
import math
from pathlib import Path, PureWindowsPath
import re

INPUT_SCHEMA = 'wht/cross-timestamp-intake-v1'
REPORT_SCHEMA = 'wht/cross-timestamp-intake-report-v1'
CLAIMS = ('known_read_point', 'bounded_pairing', 'fresh', 'attributable')
CONDITIONS = ('idle', 'load')
SCOPE_FIELDS = ('adapter', 'driver_sha256', 'firmware', 'os_build', 'host', 'clock_domain')
SHA256 = re.compile(r'[0-9a-f]{64}')


def _object(value: object, name: str) -> dict:
    if type(value) is not dict:
        raise ValueError(f'{name} must be an object')
    return value


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{name} must be nonempty text')
    return value


def _integer(value: object, name: str, minimum: int = 0, maximum: int = 2**64 - 1) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f'{name} must be an integer in [{minimum}, {maximum}]')
    return value


def _ratio(value: Fraction) -> dict[str, int]:
    return {'numerator': value.numerator, 'denominator': value.denominator}


def _verify_references(references: object, root: Path) -> dict:
    references = _object(references, 'references')
    if not references:
        raise ValueError('references must include retained source evidence')
    verified = {}
    for name, entry in references.items():
        _text(name, 'reference name')
        entry = _object(entry, 'reference')
        rel = _text(entry.get('path'), 'reference path')
        # Treat both Windows and POSIX syntax as unsafe if they escape the bundle.
        parts = rel.replace('\\', '/').split('/')
        if (Path(rel).is_absolute() or PureWindowsPath(rel).drive or ':' in rel
                or any(part in ('', '.', '..') for part in parts)):
            raise ValueError('reference path must be relative within the evidence bundle')
        digest = _text(entry.get('sha256'), 'reference sha256')
        if SHA256.fullmatch(digest) is None:
            raise ValueError('reference sha256 must contain 64 lowercase hex characters')
        path = root.joinpath(*parts)
        # Resolve before reading, rejecting junctions/symlinks outside the bundle.
        try:
            contained = path.resolve(strict=True).is_relative_to(root.resolve(strict=True))
        except RuntimeError as error:
            # Python 3.11/3.12 report symlink loops as RuntimeError, not OSError.
            raise ValueError(f'reference path cannot be resolved: {name}') from error
        if not contained:
            raise ValueError('reference resolves outside the evidence bundle')
        if not path.is_file():
            raise ValueError('reference must identify a regular file')
        with path.open('rb') as stream:
            actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        if actual != digest:
            raise ValueError(f'reference hash mismatch: {name}')
        verified[name] = {'path': '/'.join(parts), 'sha256': actual}
    return verified


def audit(data: dict, evidence_root: Path) -> dict:
    """Check supplied assertions and raw tuples, without certifying their meaning.

    Half-width is exactly (QPC2-QPC1)*1e6/(2*frequency). It bounds only the
    reported bracket, conditional on a current hardware read inside it. It is
    not a full error budget, a freshness test, or evidence of AP synchronization.
    """
    data = _object(data, 'manifest')
    if data.get('schema') != INPUT_SCHEMA:
        raise ValueError(f'schema must be {INPUT_SCHEMA}')
    provenance = data.get('provenance')
    if provenance not in ('synthetic', 'retained_capture'):
        raise ValueError('provenance must be synthetic or retained_capture')
    scope = _object(data.get('scope'), 'scope')
    scope = {key: _text(scope.get(key), f'scope.{key}') for key in SCOPE_FIELDS}
    if SHA256.fullmatch(scope['driver_sha256']) is None:
        raise ValueError('scope.driver_sha256 must contain 64 lowercase hex characters')
    frequency = _integer(data.get('qpc_frequency_hz'), 'qpc_frequency_hz', 1)
    limit = _integer(data.get('pairing_limit_us'), 'pairing_limit_us', 1, 10)
    references = _verify_references(data.get('references'), evidence_root)
    claims = _object(data.get('claims'), 'claims')
    blockers = []
    if provenance == 'synthetic':
        blockers.append('synthetic_evidence')
    if scope['clock_domain'].strip().casefold() == 'unknown':
        blockers.append('unknown_clock_domain')
    normalized_claims = {}
    for name in CLAIMS:
        claim = _object(claims.get(name), f'claims.{name}')
        basis = claim.get('basis')
        if basis not in ('unknown', 'documented', 'measured'):
            raise ValueError(f'claims.{name}.basis must be unknown, documented or measured')
        statement = _text(claim.get('statement'), f'claims.{name}.statement')
        refs = claim.get('references')
        if (type(refs) is not list or any(type(ref) is not str or ref not in references for ref in refs)
                or len(set(refs)) != len(refs)):
            raise ValueError(f'claims.{name}.references must name unique verified references')
        if basis != 'unknown' and not refs:
            raise ValueError(f'claims.{name} requires evidence references')
        if basis == 'unknown' or (name in ('bounded_pairing', 'fresh') and basis != 'measured'):
            blockers.append('unresolved_' + name)
        normalized_claims[name] = {'basis': basis, 'statement': statement, 'references': refs}
    attempts = data.get('attempts')
    if type(attempts) is not list:
        raise ValueError('attempts must be an array including all failed and successful requests')
    counts = {condition: {'attempts': 0, 'successful': 0, 'failed': 0, 'over_limit': 0}
              for condition in CONDITIONS}
    rows, identities = [], set()
    for attempt in attempts:
        row = _object(attempt, 'attempt')
        condition = row.get('condition')
        if condition not in CONDITIONS:
            raise ValueError('attempt condition must be idle or load')
        epoch = _text(row.get('epoch'), 'attempt.epoch')
        identity = _text(row.get('attempt_id'), 'attempt.attempt_id')
        if (epoch, identity) in identities:
            raise ValueError('duplicate (epoch, attempt_id)')
        identities.add((epoch, identity))
        ref = row.get('reference')
        if type(ref) is not str or ref not in references:
            raise ValueError('attempt.reference must identify verified source evidence')
        status = _integer(row.get('status'), 'attempt.status', maximum=2**32 - 1)
        counts[condition]['attempts'] += 1
        result = {'condition': condition, 'epoch': epoch, 'attempt_id': identity,
                  'reference': ref, 'status': status, 'bracket_half_width_us': None}
        if status:
            counts[condition]['failed'] += 1
        else:
            before = _integer(row.get('qpc_before'), 'qpc_before', 1)
            hardware = _integer(row.get('hardware_ticks'), 'hardware_ticks', 1)
            after = _integer(row.get('qpc_after'), 'qpc_after', before)
            width = Fraction((after - before) * 1_000_000, 2 * frequency)
            result.update(qpc_before=before, hardware_ticks=hardware, qpc_after=after,
                          bracket_half_width_us=_ratio(width))
            counts[condition]['successful'] += 1
            counts[condition]['over_limit'] += int(width > limit)
            if before == after and 'equal_qpc_requires_capture_error_evidence' not in blockers:
                blockers.append('equal_qpc_requires_capture_error_evidence')
        rows.append(result)
    accounting = _object(data.get('attempt_accounting'), 'attempt_accounting')
    normalized_accounting = {}
    for condition, count in counts.items():
        entry = _object(accounting.get(condition), f'attempt_accounting.{condition}')
        ref = entry.get('reference')
        if type(ref) is not str or ref not in references:
            raise ValueError('attempt accounting requires a verified source reference')
        if 'issued' not in entry:
            raise ValueError('attempt accounting requires an issued count or explicit null')
        issued = entry['issued']
        if issued is None:
            count.update(issued=None, unrepresented=None)
            blockers.append(f'unknown_{condition}_attempt_count')
        else:
            issued = _integer(issued, f'attempt_accounting.{condition}.issued')
            if issued < count['attempts']:
                raise ValueError(f'{condition} issued count is smaller than supplied attempts')
            count.update(issued=issued, unrepresented=issued - count['attempts'])
            if issued > count['attempts']:
                blockers.append(f'unrepresented_{condition}_attempts')
        normalized_accounting[condition] = {'issued': issued, 'reference': ref}
        if not count['successful']:
            blockers.append(f'missing_{condition}_capture')
    if any(count['failed'] for count in counts.values()):
        blockers.append('capture_failures_present')
    if any(count['over_limit'] for count in counts.values()):
        blockers.append('pairing_limit_exceeded')
    return {'schema': REPORT_SCHEMA, 'scope': scope, 'provenance': provenance,
            'qpc_frequency_hz': frequency, 'pairing_limit_us': limit,
            'references': references, 'claims': normalized_claims,
            'attempt_accounting': normalized_accounting,
            'conditions': counts, 'attempts': rows, 'blockers': blockers,
            'verdict': 'intake_blocked' if blockers else 'ready_for_semantic_review',
            'gate1_qualified': False, 'physical_bound_proven': False,
            'qualification_boundary': 'File integrity and supplied assertions only. Human review, '
            'AP-TSF clock mapping, complete error budget and independent validation remain required.'}


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f'non-finite JSON constant: {value}')


def _finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError('JSON number exceeds finite floating-point range')
    return number


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    args = parser.parse_args(argv)
    try:
        original = args.manifest.read_bytes()
        data = json.loads(original.decode('utf-8'), object_pairs_hook=_unique_object,
                          parse_constant=_reject_constant, parse_float=_finite_float)
        result = audit(data, args.manifest.absolute().parent)
        result['manifest_sha256'] = hashlib.sha256(original).hexdigest()
        print(json.dumps(result, indent=2, allow_nan=False))
        return 2 if result['blockers'] else 0
    except (OSError, ValueError, TypeError, RecursionError) as error:
        logging.error('Cross-timestamp intake rejected: %s', error)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
