"""Owned diagnostic observations from the existing saved TSF evidence contract.

This first profile cannot qualify a clock input. Hashes identify supplied content,
not authenticity, firmware identity, or physical continuity. No device or file I/O.
"""
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

from research.evidence.validate_research_bundle import validate_bundle


def validate_observation(record: dict) -> dict[str, Any]:
    """Validate an entire evidence bundle and select a one-based observation.

    Input keys: schema='tsf-evidence-selection/v1', bundle, sequence. Output is
    a detached diagnostic record, not a qualified timestamp or a mutable alias
    into the input. No caller-supplied quality/freshness overrides are accepted.
    """
    if type(record) is not dict or set(record) != {'schema', 'bundle', 'sequence'}:
        raise ValueError('unsupported_selection_fields')
    if record['schema'] != 'tsf-evidence-selection/v1':
        raise ValueError('unsupported_selection_schema')
    sequence = record['sequence']
    if type(sequence) is not int or not 1 <= sequence <= 12:
        raise ValueError('invalid_sequence')
    bundle = record['bundle']
    try:
        result = validate_bundle(bundle)
    except (ValueError, TypeError, KeyError) as error:
        raise ValueError('invalid_evidence_bundle') from error
    if sequence > result.observation_count:
        raise ValueError('sequence_not_present')
    # Detach before publication. Concurrent mutation by a caller while validation
    # runs is outside this pure API contract; the file reader supplies private data.
    owned = copy.deepcopy(bundle)
    canonical = json.dumps(owned, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    digest = hashlib.sha256(canonical).hexdigest()
    manifest = owned['manifest']
    sample = owned['observations'][sequence - 1]
    return dict(
        schema='tsf-diagnostic-observation/v1',
        evidence_kind=manifest['evidence_kind'], qualification='diagnostic-only',
        sequence=sequence, action=sample['action'],
        tsf_raw=sample['tsf_raw'], soc_raw=sample['soc_raw'],
        global_tsf_raw=sample['global_tsf_raw'], soc_semantics=sample['soc_semantics'],
        storage_bits=manifest['counter_width'], meaningful_bits=None,
        counter_unit=manifest['counter_unit'], counter_rate_hz=None,
        source_id=manifest['source_id'], epoch_id=manifest['epoch_id'],
        source_binding='bundle-local-anonymized',
        continuity=manifest['continuity'], association=manifest['association'],
        bundle_id=manifest['bundle_id'], bundle_sha256=digest,
        capture_key=f"{digest}:{manifest['epoch_id']}",
        host_qpc=dict(frequency_hz=manifest['qpc_frequency_hz'],
                      request_before=sample['host_before_qpc'],
                      request_completed=sample['host_completed_qpc'],
                      report_log=sample['report_qpc']),
        freshness='unknown', sample_age_ns=None, sampling_interval_qpc=None,
        external_uncertainty_ns=None, clock_input_eligible=False,
        provenance=dict(driver_sha256=manifest['driver_sha256'],
                        source=manifest['source'], input_sha256=manifest['input_sha256']),
    )
