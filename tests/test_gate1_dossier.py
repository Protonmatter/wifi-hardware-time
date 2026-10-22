"""Synthetic dossier regressions; never accesses a device or vendor runtime."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from research.clock_models import gate1_dossier as gd
from research.clock_models import microsecond_feasibility as mf

FIXTURES = Path(__file__).parent / 'fixtures/gate1_dossier'


class DossierTests(unittest.TestCase):
    def setUp(self):
        self.root = FIXTURES
        self.data = json.loads((self.root / 'complete-synthetic.json').read_text(encoding='utf-8'))

    def audit(self, data=None):
        return gd.audit(self.data if data is None else data, self.root)

    def test_complete_synthetic_only_checks_consistency(self):
        before = copy.deepcopy(self.data)
        result = self.audit()
        self.assertTrue(result['consistency_passed'])
        self.assertEqual(result['verdict'], 'synthetic_consistency_only')
        for flag in ('gate1_qualified', 'physical_bound_proven', 'experiment_authorized',
                     'semantic_review_ready', 'gate2_qualified'):
            self.assertIs(result[flag], False)
        self.assertEqual(before, self.data)
        self.assertEqual(result, self.audit())
        self.assertNotIn('candidates', result)

    def test_incomplete_fixture_keeps_unknown_budget_null(self):
        data = json.loads((self.root / 'incomplete-synthetic.json').read_text(encoding='utf-8'))
        result = self.audit(data)
        self.assertFalse(result['consistency_passed'])
        self.assertIsNone(result['budget']['actual_total_ns'])
        self.assertIn('reference_ns', result['budget']['unknown_terms'])
        self.assertIn('vendor:Q05:unknown', result['blockers'])

    def test_adversarial_fixture_rejects_hindsight_and_unresolved_ledger(self):
        data = json.loads((self.root / 'adversarial-synthetic.json').read_text(encoding='utf-8'))
        result = self.audit(data)
        self.assertFalse(result['consistency_passed'])
        self.assertIn('comparison:idle-event:source_after_cutoff', result['blockers'])
        self.assertTrue(any('unresolved' in b for b in result['blockers']))

    def test_missing_and_extra_fields_rejected(self):
        for mutation in ('missing', 'extra', 'flag'):
            data = copy.deepcopy(self.data)
            if mutation == 'missing':
                del data['vendor_answers']['Q13']
            elif mutation == 'extra':
                data['plan']['unexpected'] = 1
            else:
                data['gate1_qualified'] = True
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.audit(data)

    def test_types_and_integer_ranges_are_strict(self):
        for value in (True, 0, 1.0, 1.2, 2**64):
            data = copy.deepcopy(self.data)
            data['scope']['qpc_frequency_hz'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.audit(data)

    def test_hash_and_portable_path_guards(self):
        for value in ('../outside.json', 'C:\\outside.json', 'source.json:stream',
                      'https://example.com/source', '/tmp/source.json'):
            data = copy.deepcopy(self.data)
            data['references']['source']['path'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.audit(data)
        self.data['references']['source']['sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            self.audit()

    def test_hash_pinned_synthetic_bytes_survive_git_line_endings(self):
        for reference in self.data['references'].values():
            raw = (self.root / reference['path']).read_bytes()
            self.assertNotIn(b'\r', raw)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), reference['sha256'])

    def test_citation_and_review_metadata_required(self):
        for field, value in [('citations', []), ('reviewer', None),
                             ('reviewed_on', '2026-02-30')]:
            data = copy.deepcopy(self.data)
            data['dossier_reviews']['D01'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.audit(data)
        self.data['vendor_answers']['Q01']['citations'][0]['reference'] = 'missing'
        with self.assertRaises(ValueError):
            self.audit()

    def test_contract_review_does_not_require_measured_gate1(self):
        self.data['stage'] = 'contract_review'
        self.data['comparisons'] = []
        self.data['ledger_snapshots'] = []
        for review in self.data['gate1_reviews'].values():
            review.update(status='unknown', basis='unknown', citations=[], reviewer=None,
                          reviewed_on=None, open_action='Need separately authorized evidence')
        result = self.audit()
        self.assertTrue(result['consistency_passed'])
        self.assertFalse(result['gate1_reviews_complete'])
        self.assertFalse(result['gate1_qualified'])

    def test_candidate_review_requires_gate1_and_both_conditions(self):
        self.data['gate1_reviews']['G1-F']['status'] = 'not_met'
        self.data['gate1_reviews']['G1-F']['open_action'] = 'Need freshness evidence'
        self.data['comparisons'] = self.data['comparisons'][:1]
        result = self.audit()
        self.assertIn('gate1:G1-F:not_met', result['blockers'])
        self.assertIn('missing_admitted_load_comparison', result['blockers'])

    def test_synthetic_provenance_cannot_be_laundered(self):
        self.data['provenance'] = 'retained_evidence'
        result = self.audit()
        self.assertFalse(result['semantic_review_ready'])
        self.assertTrue(any('synthetic' in b for b in result['blockers']))

    def test_independent_reference_and_epoch(self):
        self.data['interfaces']['I-AR']['independent_of_candidate'] = False
        self.data['comparisons'][0]['epoch'] = 'different-epoch'
        result = self.audit()
        self.assertIn('interface:I-AR:not_independent', result['blockers'])
        self.assertIn('comparison:idle-event:epoch_mismatch', result['blockers'])

    def test_immediate_and_settled_cutoffs_and_deadlines(self):
        self.data['comparisons'][0]['available_qpc'] = self.data['comparisons'][0]['event_qpc'] + 1
        self.assertIn('comparison:idle-event:source_after_cutoff', self.audit()['blockers'])
        self.data = json.loads((self.root / 'complete-synthetic.json').read_text())
        self.data['plan']['publication_mode'] = 'settled'
        row = self.data['comparisons'][0]
        row.update(capture_qpc_lower=row['event_qpc'] + 10,
                   capture_qpc_upper=row['event_qpc'] + 12,
                   available_qpc=row['event_qpc'] + 20,
                   evidence_cutoff_qpc=row['event_qpc'] + 30,
                   returned_qpc=row['event_qpc'] + 35,
                   deadline_qpc=row['event_qpc'] + 40)
        self.assertTrue(self.audit()['consistency_passed'])
        row['returned_qpc'] = row['deadline_qpc'] + 1
        self.assertIn('comparison:idle-event:missed_deadline', self.audit()['blockers'])

    def test_drift_uses_event_distance_not_delivery_delay(self):
        self.data['plan']['publication_mode'] = 'settled'
        row = self.data['comparisons'][0]
        row.update(event_qpc=100, capture_qpc_lower=50_100, capture_qpc_upper=50_102,
                   available_qpc=50_103, evidence_cutoff_qpc=50_104,
                   returned_qpc=50_105, deadline_qpc=100_000)
        result = self.audit()
        self.assertGreater(result['comparisons'][0]['rate_error_ns'], 1000)
        self.assertIn('comparison:idle-event:rate_age_ceiling_exceeded', result['blockers'])

    def test_large_ticks_exact_math_and_equal_qpc(self):
        result = self.audit()
        self.assertGreater(self.data['comparisons'][0]['event_qpc'], 2**53)
        self.assertEqual(result['comparisons'][0]['bracket_half_width_ns'], 100)
        row = self.data['comparisons'][0]
        row['capture_qpc_upper'] = row['capture_qpc_lower']
        self.assertIn('comparison:idle-event:equal_qpc_needs_separate_review', self.audit()['blockers'])

    def test_ledger_conservation_and_snapshot_monotonicity(self):
        self.data['ledger_snapshots'][0]['issued'] += 1
        with self.assertRaises(ValueError):
            self.audit()
        self.data = json.loads((self.root / 'complete-synthetic.json').read_text())
        previous = self.data['ledger_snapshots'][0]
        later = copy.deepcopy(previous)
        later['snapshot_qpc'] += 100
        later['completed_success'] = 0
        later['unresolved'] = 1
        self.data['ledger_snapshots'].append(later)
        with self.assertRaises(ValueError):
            self.audit()

    def test_timeout_metrics_are_not_terminal_and_layers_not_summed(self):
        self.data['ledger_snapshots'][0]['host_timeouts'] = 1
        result = self.audit()
        self.assertTrue(result['consistency_passed'])
        other = copy.deepcopy(self.data['ledger_snapshots'][0])
        other['layer'] = 'firmware_event'
        other['completed_success'] = 0
        other['unresolved'] = 1
        self.data['ledger_snapshots'].append(other)
        self.assertTrue(any('unresolved' in b for b in self.audit()['blockers']))

    def test_model_freeze_and_reference_leakage(self):
        self.data['plan']['reference_values_used_for_candidate'] = True
        self.data['plan']['model_kind'] = 'static'
        self.data['plan']['training_freeze_qpc'] = self.data['comparisons'][0]['event_qpc'] + 1
        result = self.audit()
        self.assertIn('candidate_uses_reference_values', result['blockers'])
        self.assertIn('comparison:idle-event:training_after_event', result['blockers'])

    def test_unknown_and_known_budget_not_confused_with_proposals(self):
        result = self.audit()
        self.assertIsNone(result['budget']['actual_total_ns'])
        self.assertFalse(result['budget']['actual_within_target'])
        self.data['budget']['actual_bounds_ns'] = copy.deepcopy(self.data['budget']['proposed_ceilings_ns'])
        self.supply_budget_evidence()
        result = self.audit()
        self.assertEqual(result['budget']['actual_total_ns'], 8000)
        self.assertFalse(result['physical_bound_proven'])

    def supply_budget_evidence(self):
        for record in self.data['budget']['bound_evidence'].values():
            record.update(citations=copy.deepcopy(self.data['comparisons'][0]['citations']),
                          justification='Synthetic assertion only, including fail-closed epoch handling')

    def test_known_budget_needs_term_evidence_including_zero(self):
        self.data['budget']['actual_bounds_ns']['epoch_changes_ns'] = 0
        with self.assertRaises(ValueError):
            self.audit()
        self.supply_budget_evidence()
        self.data['budget']['bound_evidence']['epoch_changes_ns']['justification'] = None
        self.assertIn('budget:epoch_changes_ns:missing_bound_justification', self.audit()['blockers'])

    def test_actual_budget_cannot_understate_record_arithmetic(self):
        self.supply_budget_evidence()
        self.data['budget']['actual_bounds_ns'].update(pairing_ns=199, rate_error_times_age_ns=0)
        result = self.audit()
        self.assertIn('comparison:idle-event:actual_budget_understates_pairing', result['blockers'])
        self.assertIn('comparison:idle-event:actual_budget_understates_rate_age', result['blockers'])

    def test_proposal_ceilings_cannot_be_relaxed_by_input(self):
        self.data['budget']['proposed_ceilings_ns']['pairing_ns'] += 1
        with self.assertRaises(ValueError):
            self.audit()

    def test_actual_budget_checks_each_ceiling_and_total(self):
        self.supply_budget_evidence()
        self.data['budget']['actual_bounds_ns'] = {key: 3000 for key in gd.CEILINGS}
        result = self.audit()
        self.assertIn('actual_budget_exceeds_10us', result['blockers'])
        self.assertIn('budget:epoch_changes_ns:proposed_ceiling_exceeded', result['blockers'])

    def test_unresolved_review_requires_owner_and_action(self):
        entry = self.data['vendor_answers']['Q01']
        entry.update(status='unknown', open_action='Obtain supported contract', owner=None)
        with self.assertRaises(ValueError):
            self.audit()
        entry['owner'] = 'unknown'
        self.assertIn('vendor:Q01:unknown_owner_or_action', self.audit()['blockers'])

    def test_reference_clock_cannot_alias_candidate(self):
        self.data['scope']['reference_clock_id'] = self.data['scope']['candidate_clock_id']
        self.assertIn('scope:reference_clock_id:aliases_candidate_clock', self.audit()['blockers'])

    def test_candidate_pairing_needs_measurement_declaration(self):
        self.data['gate1_reviews']['G1-P']['basis'] = 'contract'
        self.assertIn('gate1:G1-P:measurement_basis_required', self.audit()['blockers'])
        self.data['gate1_reviews']['G1-P']['basis'] = 'measurement'
        self.assertIn('gate1:G1-P:retained_measurement_reference_required', self.audit()['blockers'])

    def test_retained_label_only_reaches_semantic_review(self):
        # In-memory hostile declarations exercise flags; this is never a retained fixture.
        self.data['provenance'] = 'retained_evidence'
        for reference in self.data['references'].values():
            reference['kind'] = 'retained_evidence'
        for group in ('vendor_answers', 'dossier_reviews', 'gate1_reviews'):
            for review in self.data[group].values():
                review['basis'] = 'measurement'
        result = self.audit()
        self.assertEqual(result['verdict'], 'ready_for_semantic_review')
        self.assertTrue(result['semantic_review_ready'])
        self.assertIsNone(result['budget']['actual_total_ns'])
        for flag in ('gate1_qualified', 'gate2_qualified', 'physical_bound_proven', 'experiment_authorized'):
            self.assertFalse(result[flag])

    def test_unknown_partition_and_missing_request_layer_block(self):
        self.data['ledger_snapshots'][0]['issued'] = None
        self.data['plan']['request_ledger_layer'] = 'driver_operation'
        result = self.audit()
        self.assertTrue(any('unknown_partition' in b for b in result['blockers']))
        self.assertIn('missing_idle_request_ledger', result['blockers'])

    def test_request_limit_sums_sessions_but_not_layers_or_snapshots(self):
        self.data['plan']['max_requests_per_condition'] = 1
        later = copy.deepcopy(self.data['ledger_snapshots'][0])
        later['snapshot_qpc'] += 1
        self.data['ledger_snapshots'].append(later)
        other_layer = copy.deepcopy(later)
        other_layer['layer'] = 'driver_operation'
        self.data['ledger_snapshots'].append(other_layer)
        self.assertTrue(self.audit()['consistency_passed'])
        other_session = copy.deepcopy(later)
        other_session['session_id'] = 'second-session'
        self.data['ledger_snapshots'].append(other_session)
        self.assertIn('ledger:idle:request_limit_exceeded', self.audit()['blockers'])

    def test_late_completion_preserves_original_timeout_snapshot(self):
        early = copy.deepcopy(self.data['ledger_snapshots'][0])
        early.update(snapshot_qpc=early['snapshot_qpc'] - 1, completed_success=0,
                     unresolved=1, host_timeouts=1)
        self.data['ledger_snapshots'][0]['host_timeouts'] = 1
        self.data['ledger_snapshots'].insert(0, early)
        result = self.audit()
        self.assertTrue(result['consistency_passed'])
        self.assertEqual(result['ledger_snapshots'][0]['partition']['unresolved'], 1)
        self.assertEqual(result['ledger_snapshots'][1]['partition']['unresolved'], 0)
        self.assertEqual(result['ledger_snapshots'][1]['host_timeouts'], 1)

    def test_source_loss_and_snapshot_cutoff_block(self):
        self.data['ledger_snapshots'][0]['firmware_lost'] = None
        self.data['ledger_snapshots'][0]['snapshot_qpc'] = self.data['comparisons'][0]['returned_qpc'] - 1
        result = self.audit()
        self.assertTrue(any('firmware_lost' in b for b in result['blockers']))
        self.assertIn('comparison:idle-event:ledger_snapshot_before_return', result['blockers'])

    def test_known_rejection_metrics_visible_without_changing_request_partition(self):
        self.data['ledger_snapshots'][0].update(duplicates=2, foreign=3, timing_invalid=1)
        result = self.audit()
        self.assertTrue(result['consistency_passed'])
        self.assertEqual(result['ledger_snapshots'][0]['nonterminal_metrics']['duplicates'], 2)
        self.assertEqual(result['ledger_snapshots'][0]['issued'], 1)
        self.data['ledger_snapshots'][0]['foreign'] = None
        self.assertTrue(any('foreign:unknown' in b for b in self.audit()['blockers']))

    def test_later_snapshot_cannot_erase_source_loss_or_rejections(self):
        for metric in gd.LOSS_FIELDS + gd.REASON_FIELDS:
            data = copy.deepcopy(self.data)
            early = data['ledger_snapshots'][0]
            early[metric] = 1
            later = copy.deepcopy(early)
            later.update(snapshot_qpc=early['snapshot_qpc'] + 1)
            later[metric] = 0
            data['ledger_snapshots'].append(later)
            with self.subTest(metric=metric), self.assertRaises(ValueError):
                self.audit(data)

    def test_unknown_snapshot_cannot_hide_cumulative_counter_decrease(self):
        for metric in ('issued', 'completed_success', 'host_timeouts') + gd.LOSS_FIELDS + gd.REASON_FIELDS:
            data = copy.deepcopy(self.data)
            final = data['ledger_snapshots'][0]
            early = copy.deepcopy(final)
            early.update(snapshot_qpc=final['snapshot_qpc'] - 2)
            early[metric] += 1
            if metric == 'issued':
                early['unresolved'] += 1
            elif metric == 'completed_success':
                early['issued'] += 1
            middle = copy.deepcopy(early)
            middle.update(snapshot_qpc=final['snapshot_qpc'] - 1)
            middle[metric] = None
            data['ledger_snapshots'][0:1] = [early, middle, final]
            with self.subTest(metric=metric), self.assertRaises(ValueError):
                self.audit(data)

    def test_unknown_final_timeout_count_blocks_consistency(self):
        self.data['ledger_snapshots'][0]['host_timeouts'] = None
        self.assertTrue(any('host_timeouts:unknown' in b for b in self.audit()['blockers']))

    def test_zero_issued_source_ledger_cannot_support_admitted_comparison(self):
        self.data['ledger_snapshots'][0].update(issued=0, completed_success=0)
        self.assertIn('comparison:idle-event:source_ledger_has_no_issued_operations', self.audit()['blockers'])

    def test_measured_review_and_interface_require_measurement_sources(self):
        self.data['references']['source']['kind'] = 'documentation'
        self.data['vendor_answers']['Q01']['basis'] = 'measurement'
        self.data['interfaces']['I-HQ']['status'] = 'measured'
        result = self.audit()
        self.assertIn('vendor:Q01:retained_measurement_reference_required', result['blockers'])
        self.assertIn('interface:I-HQ:retained_measurement_reference_required', result['blockers'])

    def test_retained_candidate_records_cannot_use_only_documentation(self):
        self.data['provenance'] = 'retained_evidence'
        self.data['references']['source']['kind'] = 'documentation'
        self.data['references']['measurement'] = dict(self.data['references']['source'], kind='retained_evidence')
        for group in ('vendor_answers', 'dossier_reviews', 'gate1_reviews'):
            for review in self.data[group].values():
                review['basis'] = 'contract'
        for key in ('G1-P', 'G1-F'):
            self.data['gate1_reviews'][key].update(basis='measurement', citations=[{
                'reference': 'measurement', 'locator': '/synthetic-only-test-declaration'}])
        result = self.audit()
        self.assertIn('comparison:idle-event:retained_measurement_reference_required', result['blockers'])
        self.assertTrue(any(b.startswith('ledger:idle:') and b.endswith('retained_measurement_reference_required')
                            for b in result['blockers']))

    def test_policy_hash_requires_matching_saved_policy_reference(self):
        self.data['plan']['policy_sha256'] = 'f' * 64
        with self.assertRaises(ValueError):
            self.audit()

    def test_collector_artifact_pins_are_complete_and_resolvable(self):
        pins = self.data['plan'].get('artifact_references', {})
        self.assertEqual(set(pins), {'collector_source', 'collector_build', 'collector_config', 'policy'})
        pins['collector_config'] = None
        self.assertIn('plan:artifact_references:collector_config:unknown', self.audit()['blockers'])
        pins['collector_config'] = 'not-a-reference'
        with self.assertRaises(ValueError):
            self.audit()

    def test_unknown_policy_pin_and_hash_stay_blocking(self):
        self.data['plan']['policy_sha256'] = None
        self.data['plan']['artifact_references']['policy'] = None
        result = self.audit()
        self.assertIn('plan:policy_sha256:unknown', result['blockers'])
        self.assertIn('plan:artifact_references:policy:unknown', result['blockers'])
        self.assertFalse(result['gate1_qualified'])

    def test_unavailable_record_retained_without_becoming_admitted(self):
        row = copy.deepcopy(self.data['comparisons'][0])
        row.update(id='rejected-event', admitted=False, reason='Unknown physical capture error',
                   capture_error_bound_ns=None)
        self.data['comparisons'].append(row)
        result = self.audit()
        self.assertTrue(result['consistency_passed'])
        self.assertEqual(result['conditions']['idle'], dict(supplied=2, admitted=1, unavailable=1))
        self.assertIn('unknown_pairing_error', result['comparisons'][-1]['issues'])
        self.assertFalse(result['comparisons'][-1]['admitted_consistently'])

    def test_contradictory_capture_and_duplicate_event_rejected(self):
        row = self.data['comparisons'][0]
        row['capture_qpc_lower'] = row['capture_qpc_upper'] + 1
        with self.assertRaises(ValueError):
            self.audit()
        row['capture_qpc_lower'] = row['capture_qpc_upper'] - 1
        self.data['comparisons'].append(copy.deepcopy(row))
        with self.assertRaises(ValueError):
            self.audit()

    def test_deadline_plan_and_unknown_hidden_age_block(self):
        row = self.data['comparisons'][0]
        row['deadline_qpc'] = row['event_qpc'] + self.data['scope']['qpc_frequency_hz']
        row['hidden_age_bound_ns'] = None
        result = self.audit()
        self.assertIn('comparison:idle-event:deadline_exceeds_plan_limit', result['blockers'])
        self.assertIn('comparison:idle-event:unknown_rate_age_error', result['blockers'])

    def test_adaptive_mode_does_not_accept_static_freeze(self):
        self.data['plan']['training_freeze_qpc'] = 1
        with self.assertRaises(ValueError):
            self.audit()

    def test_unknown_state_effect_cannot_be_hidden_in_a_nonempty_list(self):
        self.data['plan']['state_effects'] = ['unknown']
        self.assertIn('plan:state_effects:unknown', self.audit()['blockers'])

    def test_cli_rejects_nonregular_and_oversized_manifests(self):
        module = 'research.clock_models.gate1_dossier'
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'large.json'
            p.write_bytes(b' ' * (gd.MAX_MANIFEST_BYTES + 1))
            for target in (p, Path(directory)):
                r = subprocess.run([sys.executable, '-m', module, str(target)],
                                   capture_output=True, text=True, timeout=10)
                self.assertEqual(r.returncode, 1, r.stderr)
                self.assertIn('ordinary file', r.stderr)

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'POSIX FIFO test')
    def test_cli_rejects_fifo_without_opening_or_hanging(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'pipe.json'
            os.mkfifo(p)
            r = subprocess.run([sys.executable, '-m', 'research.clock_models.gate1_dossier', str(p)],
                               capture_output=True, text=True, timeout=10)
            self.assertEqual(r.returncode, 1)

    def test_cli_schema_strict_json_and_exit_codes(self):
        module = 'research.clock_models.gate1_dossier'
        r = subprocess.run([sys.executable, '-m', module, '--schema'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), gd.load_schema())
        for name, expected in [('complete-synthetic.json', 0), ('incomplete-synthetic.json', 2),
                               ('adversarial-synthetic.json', 2)]:
            r = subprocess.run([sys.executable, '-m', module, str(self.root / name)],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, expected, r.stderr)
            report = json.loads(r.stdout)
            self.assertFalse(report['gate1_qualified'])
            self.assertEqual(report['manifest_sha256'], hashlib.sha256((self.root / name).read_bytes()).hexdigest())
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'bad.json'
            for raw in ('{"schema":1,"schema":2}', '{"x":NaN}', '{"x":1e999}', '[]'):
                p.write_text(raw, encoding='utf-8')
                r = subprocess.run([sys.executable, '-m', module, str(p)], capture_output=True, text=True)
                self.assertEqual(r.returncode, 1)
                self.assertNotIn('Traceback', r.stderr)

    def test_existing_baseline_preserved(self):
        self.assertEqual(mf.baseline()['verdict'], 'killed_at_gate1_no_qualified_capture_path')


if __name__ == '__main__':
    unittest.main()
