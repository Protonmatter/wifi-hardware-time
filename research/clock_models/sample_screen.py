"""Classify TSF trace records into owned action-4 samples. Offline, fail-closed.

Our request logs a command record (action 4) before its report group; scans and
other activity produce report groups without one. Classification is structural
and never proves the firmware identity of a report. A report counts for a
request only inside the acceptance window after the request's host QPC.
"""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from fractions import Fraction

TIMING_KINDS = ('command', 'report', 'soc_timer', 'delay')
MAX_WINDOW_US = 2_000
LISTEN_TIMEOUT_S = 5
FRESHNESS_PPM = 100
US_PER_S = 1_000_000


@dataclass(frozen=True)
class Request:
    sequence: int
    lower_qpc: int
    succeeded: bool


@dataclass(frozen=True)
class Sample:
    sequence: int
    tsf_us: int
    soc_raw: int
    lower_qpc: int
    upper_qpc: int


@dataclass(frozen=True)
class Screen:
    accepted: tuple[Sample, ...]
    rejected: tuple[tuple[int, str], ...]
    foreign_groups: int
    foreign_commands: int
    own_losses: int
    duration_s: Fraction
    expected_misattributed: Fraction
    # Screened-out samples that still carry a report (late or stale), for diagnostics only.
    rejected_samples: tuple[tuple[str, Sample], ...] = ()


def request_from_receipt(sequence: int, receipt: dict, *, session: dict | None = None,
                         qpc_hz: int | None = None) -> Request:
    if 'schema' in receipt or 'session_id' in receipt or session is not None:
        from research.tsf.sampler_receipts import normalize
        lower, succeeded = normalize(sequence, receipt, session, qpc_hz)
        return Request(sequence, lower, succeeded)
    lower = receipt.get('qpc_request_before')
    if type(lower) is not int:
        raise ValueError('Receipt lacks integer qpc_request_before')
    if receipt.get('firmware_action') != 4:
        raise ValueError('Only action-4 receipts are admitted')
    succeeded = (receipt.get('success') is True and receipt.get('handle_closed') is True
                 and not receipt.get('cancel_requested'))
    return Request(sequence, lower, succeeded)


def _events(records: list[dict]) -> list[dict]:
    timing = [r for r in records if r.get('kind') in TIMING_KINDS]
    if any(type(r.get('raw_timestamp')) is not int for r in timing):
        raise ValueError('Timing record without integer raw_timestamp')
    timing.sort(key=lambda r: r['raw_timestamp'])  # Stable: ties keep emission order.
    events, index = [], 0
    while index < len(timing):
        record = timing[index]
        if record['kind'] == 'command':
            events.append(dict(type='command', ts=record['raw_timestamp'], vdev=record['vdev'], action=record['action']))
            index += 1
            continue
        if record['kind'] != 'report' or [r['kind'] for r in timing[index + 1:index + 3]] != ['soc_timer', 'delay']:
            raise ValueError('Report group is not report, soc_timer, delay in order')
        report, soc, delay = timing[index:index + 3]
        tsf, soc_raw = report['tsf_raw'], soc['soc_timer_raw']
        delay_ok = ((tsf - soc_raw) & 0xffffffff) == delay['tsf_delay_raw'] and delay['vdev'] == report['vdev']
        events.append(dict(type='report', ts=report['raw_timestamp'], vdev=report['vdev'], tsf=tsf, soc=soc_raw, delay_ok=delay_ok))
        index += 3
    return events


def _fresh(previous: Sample, current: Sample, qpc_hz: int) -> bool:
    shortest = Fraction((current.lower_qpc - previous.upper_qpc) * US_PER_S, qpc_hz)
    longest = Fraction((current.upper_qpc - previous.lower_qpc) * US_PER_S, qpc_hz)
    low = shortest * (US_PER_S - FRESHNESS_PPM) / US_PER_S - 1
    high = longest * (US_PER_S + FRESHNESS_PPM) / US_PER_S + 1
    return low <= current.tsf_us - previous.tsf_us <= high


def freshness_filter(samples: list[Sample], qpc_hz: int) -> tuple[list[Sample], list[tuple[int, str]]]:
    """Reject a sample whose TSF step cannot fit its host interval at 100 ppm."""
    accepted, rejected = [], []
    for sample in samples:
        if accepted and not _fresh(accepted[-1], sample, qpc_hz):
            rejected.append((sample.sequence, 'stale_or_inconsistent'))
            continue
        accepted.append(sample)
    return accepted, rejected


def screen(records: list[dict], requests: list[Request], qpc_hz: int) -> Screen:
    if type(qpc_hz) is not int or qpc_hz <= 0:
        raise ValueError('QPC frequency must be a positive integer')
    if not requests or any(b.lower_qpc <= a.lower_qpc for a, b in zip(requests, requests[1:])):
        raise ValueError('Requests must be non-empty and strictly ordered')
    events = _events(records)
    stamps = [e['ts'] for e in events]
    timeout = LISTEN_TIMEOUT_S * qpc_hz
    accept_ticks = MAX_WINDOW_US * qpc_hz // US_PER_S
    limits = [(r.lower_qpc, min(r.lower_qpc + timeout, n.lower_qpc)) for r, n in zip(requests, requests[1:])]
    limits.append((requests[-1].lower_qpc, requests[-1].lower_qpc + timeout))
    claimed: set[int] = set()
    rejected, candidates, rejected_samples = [], [], []
    own_losses = foreign_groups = foreign_commands = 0
    for request, (begin, end) in zip(requests, limits):
        accept_end = min(begin + accept_ticks, end - 1)
        first, split, last = bisect_left(stamps, begin), bisect_right(stamps, accept_end), bisect_left(stamps, end)
        claimed.update(range(first, last))
        window = events[first:split]
        later = events[split:last]
        commands = [e for e in window if e['type'] == 'command']
        reports = [e for e in window if e['type'] == 'report']
        # A request can own at most one report. Count the guaranteed excess
        # even when ambiguity causes this entire sample to be rejected.
        foreign_groups += max(0, len(reports) - 1)
        later_reports = [e for e in later if e['type'] == 'report']
        foreign_commands += sum(e['type'] == 'command' for e in later)
        reason = None
        if not request.succeeded:
            reason = 'request_failed'
        elif len(commands) != 1 or commands[0]['action'] != 4:
            reason = 'command_record_missing_or_extra'
        elif not reports:
            reason = 'late_report' if later_reports else 'own_loss'
            if later_reports:
                late = later_reports[0]
                rejected_samples.append(('late_report', Sample(request.sequence, late['tsf'], late['soc'],
                                                               request.lower_qpc, late['ts'])))
            later_reports = later_reports[1:]
        elif len(reports) > 1:
            reason = 'multiple_reports_in_window'
        else:
            command, report = commands[0], reports[0]
            if report['ts'] < command['ts']:
                reason = 'report_before_command'
            elif report['vdev'] != command['vdev']:
                reason = 'vdev_mismatch'
            elif not report['delay_ok']:
                reason = 'delay_arithmetic'
            else:
                candidates.append(Sample(request.sequence, report['tsf'], report['soc'], request.lower_qpc, report['ts']))
        foreign_groups += len(later_reports)
        if reason in ('own_loss', 'late_report'):
            own_losses += 1
        if reason:
            rejected.append((request.sequence, reason))
    accepted, stale = freshness_filter(candidates, qpc_hz)
    rejected.extend(stale)
    stale_sequences = {sequence for sequence, _ in stale}
    rejected_samples.extend(('stale_or_inconsistent', s) for s in candidates if s.sequence in stale_sequences)
    unclaimed = [e for i, e in enumerate(events) if i not in claimed]
    foreign_groups += sum(e['type'] == 'report' for e in unclaimed)
    foreign_commands += sum(e['type'] == 'command' for e in unclaimed)
    duration = Fraction(limits[-1][1] - limits[0][0], qpc_hz)
    expected = own_losses * Fraction(foreign_groups) / duration * Fraction(MAX_WINDOW_US, US_PER_S)
    return Screen(tuple(accepted), tuple(sorted(rejected)), foreign_groups, foreign_commands,
                  own_losses, duration, expected, tuple(sorted(rejected_samples, key=lambda item: item[1].sequence)))
