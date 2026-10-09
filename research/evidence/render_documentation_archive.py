"""Deterministic reading copies from pinned Git Markdown; no I/O or execution.

Exact originals stay unchanged. Reading copies normalize UTF-8/line endings,
rebase inline Markdown destinations against the supplied Git object inventory,
and add a historical-source notice. The caller verifies the source Git bytes.
"""
from __future__ import annotations
from collections.abc import Mapping
import json
import posixpath
import re
from urllib.parse import quote

REPOSITORY = 'https://github.com/Protonmatter/wifi-hardware-time'


def parse_manifest(text: str) -> dict:
    """Reject ambiguous duplicate names at every JSON object level."""
    def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key in archive manifest')
            result[key] = value
        return result
    def invalid_constant(value: str) -> None:
        raise ValueError('Non-standard JSON constant in archive manifest')
    data = json.loads(text, object_pairs_hook=unique_object, parse_constant=invalid_constant)
    if not isinstance(data, dict):
        raise ValueError('Archive manifest must be a JSON object')
    return data


def render_snapshot_index(name: str, data: Mapping) -> bytes:
    """Reproduce the retained index prose and its complete source/copy table."""
    revision = data['source_revision']
    if name == '2026-10-09-publication-parent-da4f55e':
        lines = ['# Publication-parent documentation supplement, 2026-10-09', '',
                 'This snapshot preserves the three Markdown files changed and the one added between the initial review baseline and the actual publication parent. It supplements the complete initial snapshot without overwriting it.', '',
                 f'Source: `{revision}`. Combine the [145-file initial snapshot](../2026-10-09-pre-refresh-e9d71b8/README.md) with these four parent versions, replacing the three matching paths, to recover all 146 Markdown files at the publication parent. The archive tests verify every resulting byte against that Git tree.', '',
                 '[Archive catalogue](../README.md) · [Manifest](manifest.json) · [Current guide](../../docs/research-history/README.md)', '',
                 'Exact originals remain byte-preserved. Readable copies are deterministically rendered from Git source with historical notices and commit-pinned links. This is historical evidence, not current operating instructions.', '',
                 '| Source path | Reading copy | Exact original |', '|---|---|---|']
    else:
        lines = [f'# Documentation archive: {name}', '',
                 'This is a historical documentation snapshot. It preserves the original wording and source identity; it does not authorize commands or turn historical findings into current capabilities.', '',
                 f"Source: `{revision}`. Captured {data['captured_date']} ({data['timezone']}). The complete pre-refresh snapshot includes every tracked Markdown file; smaller milestone snapshots preserve selected entry points.", '',
                 '[Current research guide](../../docs/research-history/README.md) · [All archives](../README.md) · [SHA-256 manifest](manifest.json)', '',
                 'Reading copies add this provenance notice and rebase relative links. Exact original bytes are stored as `.md.txt` to distinguish them from current documentation. Binaries, raw captures and source code are not copied. Historical linked attachments remain at their immutable Git source; private inputs remain private.', '',
                 '| Original path | Reading copy | Exact original |', '|---|---|---|']
    for row in sorted(data['files'], key=lambda item: item['source_path']):
        lines.append(f"| `{row['source_path']}` | [Read]({row['reading_path']}) | [Bytes]({row['original_path']}) |")
    return ('\n'.join(lines)+'\n').encode('utf-8')


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
