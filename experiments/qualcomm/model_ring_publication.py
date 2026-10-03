"""Finite publication counterexample, not a driver emulator or live ring reader.

The model assumes no caller lock/quiescence, one reserving writer and two atomic
copies (a stronger copier than a real bytewise copy). Even equal copies and a
stable reservation position cannot establish completion under these assumptions.
No driver bytes, timestamps or endpoint data are read. CLI prints synthetic JSON.
"""
from __future__ import annotations

from collections.abc import Iterator
import json
from typing import Any


def schedules(left: tuple[str, ...], right: tuple[str, ...]) -> Iterator[tuple[str, ...]]:
    if not left:
        yield right
    elif not right:
        yield left
    else:
        for tail in schedules(left[1:], right):
            yield (left[0],) + tail
        for tail in schedules(left, right[1:]):
            yield (right[0],) + tail


def simulate(schedule: tuple[str, ...]) -> dict[str, Any]:
    if schedule not in tuple(schedules(('reserve', 'prefix', 'payload'), ('copy1', 'copy2'))):
        raise ValueError('Expected one order-preserving five-operation schedule')
    buffer = bytearray(b'old!')
    position = 0
    snapshots = []
    complete = False
    complete_at_second_copy = False
    for action in schedule:
        if action == 'reserve':
            position = 4
        elif action == 'prefix':
            buffer[:2] = b'ne'
        elif action == 'payload':
            buffer[2:] = b'w!'
            complete = True
        else:
            snapshots.append(dict(position=position, bytes=buffer.decode('ascii')))
            if action == 'copy2':
                complete_at_second_copy = complete
    return dict(schedule=list(schedule), snapshots=snapshots,
                naive_double_copy_accepts=snapshots[0] == snapshots[1] and snapshots[1]['position'] == 4,
                complete_at_second_copy=complete_at_second_copy)


def assess_model() -> dict[str, Any]:
    cases = [simulate(case) for case in schedules(('reserve', 'prefix', 'payload'), ('copy1', 'copy2'))]
    bad = [case['schedule'] for case in cases if case['naive_double_copy_accepts'] and not case['complete_at_second_copy']]
    return dict(schema='ring-publication-counterexample/v1', interleavings=len(cases),
                false_acceptance_schedules=bad, copies_atomic_in_model=True,
                caller_quiescence_assumed=False, live_torn_copy_observed=False,
                retrieval_qualified=False)


if __name__ == '__main__':
    print(json.dumps(assess_model(), indent=2))
