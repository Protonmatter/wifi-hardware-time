"""Check or refresh declared TSF headline blocks from versioned retained-run results.

Default/--check writes nothing and exits 1 on drift. --write updates only the
declared Markdown blocks, using UTF-8/LF; unchanged repeats write nothing.
Exit 0: synchronized (or written); 1: drift/input/I/O error; 2: argument error.
No device, network, or privileged operation. Historical source JSON is read only.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
from fractions import Fraction
import json
import logging
import math
from pathlib import Path
import posixpath
import re

ROOT = Path(__file__).resolve().parents[2]
SOURCE = 'docs/overview/postmerge-corrections-2026-10-08.json'
TARGETS = {
    'README.md': ('smoke',),
    'docs/knowledge/current-findings.md': ('smoke', 'hours'),
    'docs/overview/gap-closure-ledger.md': ('smoke',),
    'docs/overview/persistent-tsf-next-steps.md': ('smoke',),
    'docs/knowledge/assumptions-and-corrections.md': ('smoke',),
    'docs/clock-models/tsf-mathematics.md': ('smoke',),
}


def _integer(value: object, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f'{name} must be a nonnegative integer')
    return value


def _number(value: object, name: str) -> str:
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError(f'{name} must be a finite nonnegative number')
    return f'{value:.3f}'


def _metrics(data: dict, name: str) -> dict:
    run = data['runs'][name]['corrected']
    percentage = Fraction(run['tracking_percent_exact'])
    if not 0 <= percentage <= 100:
        raise ValueError('Tracking percentage outside 0..100')
    with localcontext() as context:
        context.prec = 40
        coverage = format(Decimal(percentage.numerator) / Decimal(percentage.denominator), '.6f')
    screen, settlement = run['screen'], run['settlement']
    requests = _integer(screen['request_count'], 'requests')
    accepted = _integer(screen['accepted_count'], 'accepted')
    events = _integer(settlement['events'], 'events')
    settled = _integer(settlement['states'].get('settled', 0), 'settled')
    if accepted > requests or settled > events:
        raise ValueError('Result count exceeds its denominator')
    return dict(coverage=coverage, requests=requests, accepted=accepted, events=events, settled=settled,
                median=_number(settlement['half_width_us']['median'], 'median half-width'),
                maximum=_number(settlement['half_width_us']['max'], 'maximum half-width'),
                wait=_number(settlement['wait_s']['median'], 'median wait'))


def _render(key: str, metrics: dict, source_link: str) -> str:
    if key == 'smoke':
        m = metrics['persistent_smoke']
        return (f"**Current retained smoke analysis:** {m['requests']} recorded requests, "
                f"{m['accepted']} offline-screened samples; **{m['coverage']}%** tracking coverage "
                f"under the conditional integer-estimate uncertainty threshold. **{m['settled']}/{m['events']}** "
                f"event-grid points settled, with median/max rate-only half-widths of "
                f"{m['median']}/{m['maximum']} us and median wait {m['wait']} s. "
                f"[Versioned results and source pins]({source_link}). "
                'This is offline-screened replay of the retained capture, not online admission or calibrated AP/UTC accuracy.')
    if key == 'hours':
        rows = ['| Retained run | Corrected tracking coverage | Settled event-grid points |',
                '|---|---:|---:|']
        for name, label in (('hour_idle', 'Idle hour'), ('hour_load', 'Loaded hour')):
            m = metrics[name]
            rows.append(f"| {label} | {m['coverage']}% | {m['settled']}/{m['events']} |")
        return '\n'.join(rows) + f'\n\n[Versioned corrected results]({source_link}); conditional replay with offline screening.'
    raise ValueError(f'Unknown headline block: {key}')


def synchronize(root: Path = ROOT, *, write: bool = False) -> list[str]:
    try:
        data = json.loads((root / SOURCE).read_text(encoding='utf-8'))
        if (data['schema'] != 'wht/review-reconciliation-v1'
                or data['qualification'] != 'conditional-research' or data['physical_bound_proven'] is not False
                or not re.fullmatch(r'[0-9a-f]{40}', data['corrected_source_commit'])):
            raise ValueError('Unknown result schema, source pin or qualification')
        metrics = {name: _metrics(data, name) for name in ('persistent_smoke', 'hour_idle', 'hour_load')}
    except (KeyError, TypeError, ZeroDivisionError) as error:
        raise ValueError(f'Incomplete or invalid TSF result source: {error}') from error
    changes = {}
    # Validate every source/block before writing any page.
    for name, keys in TARGETS.items():
        original = (root / name).read_text(encoding='utf-8')
        rendered = original
        found = re.findall(r'<!-- tsf-headlines:([^ ]+) -->', original)
        endings = re.findall(r'<!-- /tsf-headlines:([^ ]+) -->', original)
        if sorted(found) != sorted(keys) or sorted(endings) != sorted(keys):
            raise ValueError(f'{name}: missing, unknown or duplicate headline markers')
        for key in keys:
            start, end = f'<!-- tsf-headlines:{key} -->', f'<!-- /tsf-headlines:{key} -->'
            pattern = re.escape(start) + r'\n.*?\n' + re.escape(end)
            link = posixpath.relpath(SOURCE, posixpath.dirname(name) or '.')
            block = start + '\n' + _render(key, metrics, link) + '\n' + end
            rendered, count = re.subn(pattern, lambda _: block, rendered, flags=re.DOTALL)
            if count != 1:
                raise ValueError(f'{name}: malformed headline block {key}')
        if rendered != original:
            changes[name] = rendered
    if write:
        for name, rendered in changes.items():
            (root / name).write_text(rendered, encoding='utf-8', newline='\n')
    return list(changes)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--write', action='store_true')
    args = parser.parse_args()
    try:
        changed = synchronize(write=args.write)
        print(json.dumps(dict(source=SOURCE, changed=changed, applied=args.write)))
        return 0 if args.write or not changed else 1
    except (OSError, ValueError) as error:
        logging.error('TSF headline synchronization failed: %s', error)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
