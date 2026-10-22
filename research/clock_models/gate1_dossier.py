"""Validate a saved Gate 1 dossier offline. Never qualifies or authorizes hardware.

Exit 0: supplied assertions are consistent (synthetic stays synthetic-only).
Exit 2: a valid dossier has unresolved or failed consistency checks.
Exit 1: malformed/unreadable input or evidence-integrity failure.
"""
from __future__ import annotations

import argparse
from datetime import date
from fractions import Fraction
import hashlib
import json
import logging
from pathlib import Path
import re
import stat

from research.clock_models import cross_timestamp_intake as intake

SCHEMA_PATH = Path(__file__).with_name('gate1_dossier.schema.json')
REPORT_SCHEMA = 'wht/gate1-dossier-report-v1'
MAX_MANIFEST_BYTES = 4 * 1024 * 1024
PARTITION = ('completed_success', 'completed_failure', 'confirmed_cancelled', 'unresolved')
LOSS_FIELDS = ('export_lost', 'firmware_lost')
REASON_FIELDS = ('duplicates', 'foreign', 'timing_invalid')
CEILINGS = dict(event_placement_ns=2000, pairing_ns=2000, rate_error_times_age_ns=1000,
                asymmetry_ns=1000, epoch_changes_ns=0, reference_ns=2000)


def load_schema() -> dict:
    """The shipped schema is local data; no remote $ref is retrieved."""
    return json.loads(SCHEMA_PATH.read_text(encoding='utf-8'))


def _shape(value: object, rule: dict, schema: dict, path: str = '$') -> None:
    """Validate the closed subset used by the shipped JSON Schema, not arbitrary schemas."""
    if '$ref' in rule:
        prefix = '#/$defs/'
        if not rule['$ref'].startswith(prefix):
            raise ValueError('Only local schema definitions are supported')
        return _shape(value, schema['$defs'][rule['$ref'][len(prefix):]], schema, path)
    kinds = {'null': type(None), 'boolean': bool, 'integer': int,
             'string': str, 'array': list, 'object': dict}
    allowed = rule.get('type')
    if allowed is not None:
        names = allowed if isinstance(allowed, list) else [allowed]
        if type(value) not in [kinds[name] for name in names]:
            raise ValueError(f'{path}: invalid type')
    if 'const' in rule and (type(value) is not type(rule['const']) or value != rule['const']):
        raise ValueError(f'{path}: wrong constant')
    if 'enum' in rule and value not in rule['enum']:
        raise ValueError(f'{path}: unknown enumeration')
    if value is None:
        return
    if type(value) is str:
        if not rule.get('minLength', 0) <= len(value) <= rule.get('maxLength', len(value)) or (
                'pattern' in rule and not re.search(rule['pattern'], value)):
            raise ValueError(f'{path}: invalid text')
    elif type(value) is int:
        if not rule.get('minimum', value) <= value <= rule.get('maximum', value):
            raise ValueError(f'{path}: integer out of range')
    elif type(value) is list:
        if not rule.get('minItems', 0) <= len(value) <= rule.get('maxItems', len(value)):
            raise ValueError(f'{path}: array length out of range')
        for i, item in enumerate(value):
            _shape(item, rule['items'], schema, f'{path}[{i}]')
    elif type(value) is dict:
        if not rule.get('minProperties', 0) <= len(value) <= rule.get('maxProperties', len(value)):
            raise ValueError(f'{path}: object size out of range')
        properties = rule.get('properties', {})
        if not set(rule.get('required', ())) <= value.keys():
            raise ValueError(f'{path}: missing required field')
        for key, item in value.items():
            if type(key) is not str or not key.strip():
                raise ValueError(f'{path}: invalid object key')
            child = properties.get(key, rule.get('additionalProperties', False))
            if child is False:
                raise ValueError(f'{path}: unexpected field {key}')
            _shape(item, child, schema, f'{path}.{key}')


def _ceil(value: Fraction) -> int:
    return -(-value.numerator // value.denominator)


def _unknown(value: object) -> bool:
    return value is None or (isinstance(value, str) and value.strip().casefold() in
                             ('unknown', 'todo', 'unavailable', 'not supplied'))


def audit(data: dict, evidence_root: Path) -> dict:
    """Check declared records and arithmetic; original bytes/meaning still require review."""
    schema = load_schema()
    _shape(data, schema, schema)
    references = intake._verify_references(data['references'], evidence_root)
    blockers: list[str] = []

    def block(message: str) -> None:
        if message not in blockers:
            blockers.append(message)

    def citations(items: list, label: str, required: bool = True) -> None:
        if required and not items:
            raise ValueError(f'{label}: evidence citations required')
        seen = set()
        for item in items:
            key = (item['reference'], item['locator'])
            if item['reference'] not in references or key in seen:
                raise ValueError(f'{label}: missing or duplicate citation')
            seen.add(key)
            if (data['provenance'] == 'retained_evidence'
                    and data['references'][item['reference']]['kind'] == 'synthetic'):
                block(f'{label}:synthetic_reference_in_retained_dossier')

    def measurement_citations(items: list, label: str) -> None:
        if not any(data['references'][item['reference']]['kind'] == 'retained_evidence' for item in items):
            block(label + ':retained_measurement_reference_required')

    for name, entry in data['scope'].items():
        if _unknown(entry):
            block('scope:' + name + ':unknown')
    for key in ('reference_clock_id', 'host_reference_clock_id'):
        if not _unknown(data['scope'][key]) and data['scope'][key] == data['scope']['candidate_clock_id']:
            block('scope:' + key + ':aliases_candidate_clock')
    candidate = data['stage'] == 'candidate_evidence_review'
    for group, key in (('vendor', 'vendor_answers'), ('dossier', 'dossier_reviews'), ('gate1', 'gate1_reviews')):
        for name, review in data[key].items():
            label = group + ':' + name
            established = review['status'] in ('met', 'established', 'not_applicable')
            known = review['status'] != 'unknown'
            citations(review['citations'], label, known)
            if known and (not review['reviewer'] or not review['reviewed_on']):
                raise ValueError(f'{label}: reviewer and date required')
            if known and _unknown(review['reviewer']):
                block(label + ':unknown_reviewer')
            if review['reviewed_on'] is not None:
                try:
                    parsed = date.fromisoformat(review['reviewed_on'])
                except ValueError as error:
                    raise ValueError(f'{label}: invalid review date') from error
                if parsed.isoformat() != review['reviewed_on']:
                    raise ValueError(f'{label}: date must be YYYY-MM-DD')
            if not established and (not review['open_action'] or not review['owner']):
                raise ValueError(f'{label}: unresolved review requires an owner and open action')
            if not established and (_unknown(review['open_action']) or _unknown(review['owner'])):
                block(label + ':unknown_owner_or_action')
            if established and review['basis'] == 'unknown':
                block(label + ':unknown_basis')
            if group != 'gate1' or candidate:
                if not established:
                    block(label + ':' + review['status'])
            if data['provenance'] == 'retained_evidence' and review['basis'] == 'synthetic':
                block(label + ':synthetic_basis_in_retained_dossier')
            if review['basis'] == 'measurement':
                measurement_citations(review['citations'], label)
            if candidate and name in ('G1-P', 'G1-F') and established:
                if review['basis'] not in ('measurement', 'synthetic'):
                    block(label + ':measurement_basis_required')

    for name, entry in data['interfaces'].items():
        citations(entry['citations'], 'interface:' + name, entry['status'] != 'unknown')
        if entry['status'] == 'measured':
            measurement_citations(entry['citations'], 'interface:' + name)
        if entry['status'] in ('unknown', 'unsupported'):
            block('interface:' + name + ':' + entry['status'])
        if name in ('I-AR', 'I-HR', 'I-HQ') and entry['independent_of_candidate'] is not True:
            block('interface:' + name + ':not_independent')

    plan = data['plan']
    for name, value in plan.items():
        if name != 'training_freeze_qpc' and (_unknown(value) or (
                name == 'state_effects' and any(_unknown(item) for item in value))):
            block('plan:' + name + ':unknown')
    if plan['model_kind'] == 'static' and plan['training_freeze_qpc'] is None:
        block('plan:static_training_freeze_unknown')
    if plan['model_kind'] == 'adaptive' and plan['training_freeze_qpc'] is not None:
        raise ValueError('Adaptive mode uses policy/update provenance, not static training freeze')
    if plan['reference_values_used_for_candidate']:
        block('candidate_uses_reference_values')
    for name, reference in plan['artifact_references'].items():
        label = 'plan:artifact_references:' + name
        if _unknown(reference):
            block(label + ':unknown')
        elif reference not in references:
            raise ValueError(label + ': missing source reference')
        else:
            citations([{'reference': reference, 'locator': 'entire artifact'}], label)
            if name == 'policy' and plan['policy_sha256'] is not None:
                if references[reference]['sha256'] != plan['policy_sha256']:
                    raise ValueError(label + ': policy hash does not match saved artifact')

    budget = data['budget']
    if budget['proposed_ceilings_ns'] != CEILINGS:
        raise ValueError('Proposed ceilings must match package revision 1; actual bounds stay separate')
    actual = budget['actual_bounds_ns']
    for term, value in actual.items():
        evidence = budget['bound_evidence'][term]
        citations(evidence['citations'], 'budget:' + term, value is not None)
        if value is not None and _unknown(evidence['justification']):
            block('budget:' + term + ':missing_bound_justification')
        if value is not None and value > CEILINGS[term]:
            block('budget:' + term + ':proposed_ceiling_exceeded')
    unknown_terms = [key for key, value in actual.items() if value is None]
    total = None if unknown_terms else sum(actual.values())
    if total is not None and total > 10000:
        block('actual_budget_exceeds_10us')

    # Preserve input order; require strictly increasing snapshots per independent ledger key.
    latest: dict[tuple, dict] = {}
    last_known: dict[tuple, dict[str, int]] = {}
    snapshots = []
    for row in data['ledger_snapshots']:
        key = tuple(row[k] for k in ('condition', 'session_id', 'epoch', 'layer'))
        label = 'ledger:' + ':'.join(key)
        citations(row['citations'], label)
        if candidate and data['provenance'] == 'retained_evidence':
            measurement_citations(row['citations'], label)
        if row['epoch'] != data['scope']['clock_epoch']:
            block(label + ':epoch_mismatch')
        counts = [row[k] for k in PARTITION]
        if row['issued'] is not None and all(v is not None for v in counts):
            if sum(counts) != row['issued']:
                raise ValueError(label + ': request partition does not reconcile')
        else:
            block(label + ':unknown_partition')
        previous = latest.get(key)
        if previous:
            if row['snapshot_qpc'] <= previous['snapshot_qpc']:
                raise ValueError(label + ': snapshot cutoff must increase')
        known = last_known.setdefault(key, {})
        for metric in ('issued', 'completed_success', 'completed_failure', 'confirmed_cancelled',
                       'host_timeouts') + LOSS_FIELDS + REASON_FIELDS:
            value = row[metric]
            if value is not None:
                if metric in known and value < known[metric]:
                    raise ValueError(label + ': cumulative counter decreased')
                known[metric] = value
        latest[key] = row
        snapshots.append(dict(condition=row['condition'], session_id=row['session_id'], epoch=row['epoch'],
                              layer=row['layer'], snapshot_qpc=row['snapshot_qpc'], issued=row['issued'],
                              partition={k: row[k] for k in PARTITION}, host_timeouts=row['host_timeouts'],
                              nonterminal_metrics={k: row[k] for k in LOSS_FIELDS + REASON_FIELDS}))
    for key, row in latest.items():
        label = 'ledger:' + ':'.join(key)
        if row['unresolved'] is None or row['unresolved'] > 0:
            block(label + ':unresolved_operations')
        if row['host_timeouts'] is None:
            block(label + ':host_timeouts:unknown')
        for metric in LOSS_FIELDS:
            if row[metric] is None or row[metric] > 0:
                block(label + ':' + metric + ':unknown_or_nonzero')
        for metric in REASON_FIELDS:
            if row[metric] is None:
                block(label + ':' + metric + ':unknown')
    for condition in ('idle', 'load'):
        selected = [r for k, r in latest.items()
                    if k[0] == condition and k[3] == plan['request_ledger_layer']]
        if candidate and not selected:
            block('missing_' + condition + '_request_ledger')
        if selected and all(r['issued'] is not None for r in selected):
            limit = plan['max_requests_per_condition']
            if limit is not None and sum(r['issued'] for r in selected) > limit:
                block('ledger:' + condition + ':request_limit_exceeded')

    rows = []
    ids = set()
    counts = {condition: {'supplied': 0, 'admitted': 0, 'unavailable': 0}
              for condition in ('idle', 'load')}
    frequency = data['scope']['qpc_frequency_hz']
    for row in data['comparisons']:
        label = 'comparison:' + row['id']
        if row['id'] in ids:
            raise ValueError('Comparison IDs must be unique across the dossier')
        ids.add(row['id'])
        citations(row['citations'], label)
        if candidate and data['provenance'] == 'retained_evidence':
            measurement_citations(row['citations'], label)
        if not row['capture_qpc_lower'] <= row['capture_qpc_upper'] <= row['available_qpc']:
            raise ValueError(label + ': capture/availability order is contradictory')
        issues = []
        def issue(condition: bool, message: str) -> None:
            if condition:
                issues.append(message)
        issue(row['epoch'] != data['scope']['clock_epoch'], 'epoch_mismatch')
        issue(row['available_qpc'] > row['evidence_cutoff_qpc'], 'source_after_cutoff')
        issue(row['evidence_cutoff_qpc'] > row['returned_qpc'], 'cutoff_after_return')
        issue(row['returned_qpc'] > row['deadline_qpc'], 'missed_deadline')
        issue(row['returned_qpc'] < row['event_qpc'] or row['deadline_qpc'] < row['event_qpc'], 'return_before_event')
        latency = plan['max_return_latency_ms']
        issue(latency is not None and (row['deadline_qpc'] - row['event_qpc']) * 1000 > latency * frequency,
              'deadline_exceeds_plan_limit')
        if plan['publication_mode'] == 'immediate':
            issue(row['evidence_cutoff_qpc'] > row['event_qpc'], 'immediate_cutoff_after_event')
        else:
            issue(row['evidence_cutoff_qpc'] < row['event_qpc'], 'settled_cutoff_before_event')
        if plan['training_freeze_qpc'] is not None:
            issue(plan['training_freeze_qpc'] > min(row['event_qpc'], row['evidence_cutoff_qpc']), 'training_after_event')
        key = tuple(row[k] for k in ('condition', 'session_id', 'epoch', 'ledger_layer'))
        issue(key not in latest, 'missing_source_ledger')
        if key in latest:
            issue(latest[key]['snapshot_qpc'] < row['returned_qpc'], 'ledger_snapshot_before_return')
            issue(latest[key]['issued'] == 0, 'source_ledger_has_no_issued_operations')
        half = _ceil(Fraction((row['capture_qpc_upper'] - row['capture_qpc_lower']) * 1_000_000_000, 2 * frequency))
        pair = None if row['capture_error_bound_ns'] is None else half + row['capture_error_bound_ns']
        issue(pair is None, 'unknown_pairing_error')
        issue(pair is not None and pair > CEILINGS['pairing_ns'], 'pairing_ceiling_exceeded')
        issue(row['capture_qpc_lower'] == row['capture_qpc_upper'], 'equal_qpc_needs_separate_review')
        distance = max(abs(row['event_qpc'] - row['capture_qpc_lower']),
                       abs(row['event_qpc'] - row['capture_qpc_upper']))
        age = None if row['hidden_age_bound_ns'] is None else (
            Fraction(distance * 1_000_000_000, frequency) + row['hidden_age_bound_ns'])
        rate = None if age is None or plan['rate_bound_ppm'] is None else _ceil(age * plan['rate_bound_ppm'] / 1_000_000)
        issue(rate is None, 'unknown_rate_age_error')
        issue(rate is not None and rate > CEILINGS['rate_error_times_age_ns'], 'rate_age_ceiling_exceeded')
        if not row['admitted'] and not row['reason']:
            raise ValueError(label + ': unavailable record needs a reason')
        if row['admitted']:
            if pair is not None and actual['pairing_ns'] is not None and pair > actual['pairing_ns']:
                issues.append('actual_budget_understates_pairing')
            if rate is not None and actual['rate_error_times_age_ns'] is not None and rate > actual['rate_error_times_age_ns']:
                issues.append('actual_budget_understates_rate_age')
            for message in issues:
                block(label + ':' + message)
        accepted = row['admitted'] and not issues
        count = counts[row['condition']]
        count['supplied'] += 1
        count['admitted'] += int(accepted)
        count['unavailable'] += int(not accepted)
        rows.append(dict(id=row['id'], condition=row['condition'], admitted_consistently=accepted,
                         issues=issues, bracket_half_width_ns=half, pairing_error_ns=pair,
                         event_distance_qpc=distance, rate_error_ns=rate, reason=row['reason']))
    if candidate:
        for condition, count in counts.items():
            if not count['admitted']:
                block('missing_admitted_' + condition + '_comparison')

    synthetic = data['provenance'] == 'synthetic'
    consistent = not blockers
    return {'schema': REPORT_SCHEMA, 'package_id': data['package_id'], 'package_revision': data['package_revision'],
            'provenance': data['provenance'], 'stage': data['stage'], 'references': references,
            'consistency_passed': consistent, 'blockers': blockers,
            'verdict': 'incomplete_dossier' if blockers else 'synthetic_consistency_only' if synthetic else 'ready_for_semantic_review',
            'semantic_review_ready': consistent and not synthetic,
            'gate1_reviews_complete': all(v['status'] == 'met' for v in data['gate1_reviews'].values()),
            'budget': {'proposed_total_ns': sum(CEILINGS.values()), 'unknown_terms': unknown_terms,
                       'actual_total_ns': total, 'actual_within_target': total is not None and total <= 10000},
            'ledger_snapshots': snapshots, 'conditions': counts, 'comparisons': rows,
            'gate1_qualified': False, 'physical_bound_proven': False, 'experiment_authorized': False,
            'gate2_qualified': False,
            'limitations': 'Consistency of supplied assertions only. Hashes do not authenticate provenance, '
            'source completeness, review truth, hidden model inputs, ownership, independent reference accuracy or hardware behavior.'}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dossier', type=Path, nargs='?')
    parser.add_argument('--schema', action='store_true', help='Print the shipped JSON Schema without reading a dossier')
    args = parser.parse_args(argv)
    if args.schema and args.dossier is not None or not args.schema and args.dossier is None:
        parser.error('Supply a dossier path or --schema')
    try:
        if args.schema:
            print(json.dumps(load_schema(), indent=2, allow_nan=False))
            return 0
        info = args.dossier.stat()
        if (args.dossier.is_symlink() or not stat.S_ISREG(info.st_mode)
                or info.st_size > MAX_MANIFEST_BYTES):
            raise ValueError('Dossier must be an ordinary file of at most 4 MiB')
        with args.dossier.open('rb') as stream:
            original = stream.read(MAX_MANIFEST_BYTES + 1)
        if len(original) > MAX_MANIFEST_BYTES:
            raise ValueError('Dossier exceeds 4 MiB')
        data = json.loads(original.decode('utf-8'), object_pairs_hook=intake._unique_object,
                          parse_constant=intake._reject_constant, parse_float=intake._finite_float)
        result = audit(data, args.dossier.absolute().parent)
        result['manifest_sha256'] = hashlib.sha256(original).hexdigest()
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0 if result['consistency_passed'] else 2
    except (OSError, ValueError, TypeError, RecursionError) as error:
        logging.error('Gate 1 dossier rejected: %s', error)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
