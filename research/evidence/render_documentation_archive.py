"""Deterministic reading copies from pinned Git Markdown; no I/O or execution.

Exact originals stay unchanged. Reading copies normalize UTF-8/line endings,
rebase inline Markdown destinations against the supplied Git object inventory,
and add a historical-source notice. The caller verifies the source Git bytes.
"""
from __future__ import annotations
from collections.abc import Mapping
import posixpath
import re
from urllib.parse import quote

REPOSITORY = 'https://github.com/Protonmatter/wifi-hardware-time'


def render_reading_copy(source_path: str, revision: str, original: bytes,
                        objects: Mapping[str, str]) -> bytes:
    if not re.fullmatch(r'[0-9a-f]{40}', revision) or objects.get(source_path) != 'blob':
        raise ValueError('Expected a full source revision and a recorded Markdown blob')
    text = original.decode('utf-8-sig').replace('\r\n', '\n')

    def destination(match: re.Match[str]) -> str:
        target = match[1]
        if re.match(r'[A-Za-z][A-Za-z0-9+.-]*:', target) or target.startswith('#'):
            return match[0]
        file, separator, anchor = target.partition('#')
        path = posixpath.normpath(posixpath.join(posixpath.dirname(source_path), file))
        kind = 'tree' if path == '.' else objects.get(path)
        if kind not in ('tree', 'blob'):
            raise ValueError(f'Relative destination absent from pinned Git tree: {path}')
        url = f'{REPOSITORY}/{kind}/{revision}/{quote(path)}'
        return '](' + url + (separator + anchor if separator else '') + ')'

    # Destination-only replacement also handles multiline labels and linked images.
    rendered = re.sub(r'\]\(([^)\n]+)\)', destination, text)
    first, rest = rendered.split('\n', 1)
    stem = source_path.replace('/', '__')
    notice = (f'> **Archive — not current operating instructions.** Historical documentation at '
              f'[{revision[:12]}]({REPOSITORY}/commit/{revision}). '
              'Relative links are rebased for reading. '
              f'[Exact original bytes](../originals/{stem}.txt) · [Archive index](../README.md) · '
              '[Current research](../../../docs/research-history/README.md).\n')
    return (first + '\n\n' + notice + rest).encode('utf-8')
