"""Read saved TSF evidence as owned diagnostic observations, never as a live clock.

No device access, firmware requests, writes or quarantine changes. Input must be
an existing wifi-clock-evidence/v1 JSON file, at most 1 MiB. Output is JSON stdout.
Exit 0: diagnostic replay; 1: rejected/unavailable; 2: invalid CLI arguments.
--require-clock-input always rejects the currently supported unqualified profile.
"""
from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import argparse
import json
from typing import Any

from research.evidence.hardware_observation import validate_observation
from research.evidence.validate_research_bundle import validate_bundle

MAX_BYTES = 1_048_576


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate_json_key')
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError('nonfinite_json_value')


def load_observations(path: Path) -> list[dict[str, Any]]:
    """Read one bounded file and return detached records in capture order.

    This proves only consistency of the supplied saved bundle. It cannot detect
    an attacker rewriting all evidence or an unreported firmware event.
    """
    if not path.is_file():
        raise OSError('input_unavailable')
    with path.open('rb') as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('input_too_large')
    try:
        bundle = json.loads(data.decode('utf-8-sig'), object_pairs_hook=_unique_pairs,
                            parse_constant=_reject_constant)
    except (UnicodeError, ValueError, RecursionError) as error:
        raise ValueError('invalid_json') from error
    try:
        count = validate_bundle(bundle).observation_count
    except (ValueError, TypeError, KeyError) as error:
        raise ValueError('invalid_evidence_bundle') from error
    return [validate_observation(dict(schema='tsf-evidence-selection/v1', bundle=bundle, sequence=i))
            for i in range(1, count + 1)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('--sequence', type=int, help='One-based observation to return; default is all')
    parser.add_argument('--require-clock-input', action='store_true',
                        help='Reject unless the profile qualifies for clock use (none currently do)')
    args = parser.parse_args()
    try:
        observations = load_observations(args.bundle)
        if args.sequence is not None:
            if not 1 <= args.sequence <= len(observations):
                raise ValueError('sequence_not_present')
            observations = [observations[args.sequence - 1]]
        if args.require_clock_input:
            raise ValueError('clock_input_unqualified')
        print(json.dumps(dict(schema='tsf-evidence-replay/v1', status='diagnostic-only',
                              live_acquisition=False, observations=observations), allow_nan=False))
        return 0
    except OSError:
        reason = 'input_unavailable'
    except ValueError as error:
        reason = str(error)
    print(json.dumps(dict(status='rejected', reason=reason, live_acquisition=False)))
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
