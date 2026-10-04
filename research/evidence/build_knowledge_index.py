"""Index authored research only. Default previews; --write updates generated docs.

Tokens are navigation aids, not a call graph or evidence of runtime support.
Vendor artifacts, reproduction snapshots, generated indexes and Git internals
are excluded. No code from the indexed sources is imported or executed.
"""
from __future__ import annotations
import argparse
import ast
from collections import defaultdict
import hashlib
import json
import logging
from pathlib import Path
import re
import stat

ROOT = Path(__file__).resolve().parents[2]
GENERATED = {'docs/knowledge/research-index.json', 'docs/knowledge/reference-index.md',
             'docs/knowledge/document-review.md'}
EXTENSIONS = {'.md', '.mmd', '.py', '.ps1', '.c', '.h', '.java', '.yml'}
EXCLUDED_PARTS = {'artifacts', 'vendor', 'downloads', 'local', 'evidence',
                  'reproductions', '__pycache__', '.git'}


def linked(path: Path) -> bool:
    return path.is_symlink() or bool(getattr(path.lstat(), 'st_file_attributes', 0)
                                    & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400))


def source_paths(root: Path) -> list[Path]:
    for ancestor in (root, *root.parents):
        if linked(ancestor):
            raise ValueError('Source root cannot traverse a linked path')
    paths = [root / 'README.md'] if (root / 'README.md').is_file() else []
    for directory in ('docs', 'research', 'tests', 'skills', '.github/workflows'):
        parent = root / directory
        if parent.exists() and any(linked(p) for p in (parent, *parent.parents) if p.is_relative_to(root)):
            raise ValueError('Source path cannot traverse a linked directory')
        if parent.exists() and linked(parent):
            raise ValueError('Source roots must not be symlinks')
        for p in parent.rglob('*') if parent.exists() else []:
            if linked(p):
                raise ValueError('Source links are not accepted')
            relative = p.relative_to(root).as_posix()
            # Authored docs/evidence and research/evidence are intentionally allowed.
            parts = tuple(part.casefold() for part in p.relative_to(parent).parts)
            # Only docs/evidence and research/evidence are authored exceptions.
            # A deeper evidence directory is ignored capture material.
            if directory in {'docs', 'research'} and parts and parts[0] == 'evidence':
                parts = parts[1:]
            excluded = set(parts) & EXCLUDED_PARTS
            if p.is_file() and p.suffix in EXTENSIONS and relative not in GENERATED and not excluded:
                paths.append(p)
    if any(linked(path) for path in paths):
        raise ValueError('Linked source files are not accepted')
    return sorted(set(paths), key=lambda path: path.relative_to(root).as_posix())


def tokens(text: str, suffix: str) -> list[tuple[str, str, int]]:
    result: list[tuple[str, str, int]] = []
    if suffix == '.py':
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                result.append((node.name, 'definition', node.lineno))
            elif isinstance(node, ast.Call):
                result.append((ast.unparse(node.func), 'python-call', node.lineno))
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                result.append((node.value, 'authored-string', node.lineno))
    for number, line in enumerate(text.splitlines(), 1):
        if suffix in {'.md', '.mmd'}:
            result.extend((m.group(1), 'documented-term', number)
                          for m in re.finditer(r'(?<!`)`([^`\n]+)`(?!`)', line))
        elif suffix != '.py':
            result.extend((m.group(1), 'call-token', number)
                          for m in re.finditer(r'\b([A-Za-z_]\w*(?:::\w+)*)\s*\(', line)
                          if m.group(1) not in {'if', 'for', 'while', 'switch', 'sizeof', 'catch'})
            result.extend((m.group(1), 'authored-string', number)
                          for m in re.finditer(r'"([^"\n]{1,160})"', line))
            result.extend((m.group(1), 'definition', number)
                          for m in re.finditer(r'\bfunction\s+([\w-]+)', line, re.I))
    clean = []
    for term, kind, line in result:
        term = term.strip()
        if not term or len(term) > 160 or '\n' in term or '\r' in term:
            continue
        if re.search(r'[A-Z]:[/\\]Users[/\\]|gh[pousr]_[A-Za-z0-9]{12,}', term, re.I):
            continue
        clean.append((term, kind, line))
    return clean


def build(root: Path) -> dict[str, object]:
    index: dict[str, set[tuple[str, str, int]]] = defaultdict(set)
    files = []
    for path in source_paths(root):
        rel = path.relative_to(root).as_posix()
        data = path.read_bytes()
        text = data.decode('utf-8-sig').replace('\r\n', '\n')
        files.append({'path': rel, 'sha256': hashlib.sha256(text.encode('utf-8')).hexdigest()})
        index[path.name].add(('filename', rel, 1))
        for term, kind, line in tokens(text, path.suffix):
            index[term].add((kind, rel, line))
    return {'schema': 'wht/authored-reference-index-v1', 'files': files,
            'hash_basis': 'UTF-8 text without BOM, CRLF normalized to LF; binary provenance is separate',
            'terms': [{'term': term, 'references': [{'kind': kind, 'path': path, 'line': line}
                       for kind, path, line in sorted(refs)]}
                      for term, refs in sorted(index.items(), key=lambda x: x[0])],
            'scope': 'authored-source tokens only; not proof of execution, API stability or hardware support'}


def rendered_files(data: dict[str, object]) -> dict[str, str]:
    files = data['files']
    md = ['# Research reference index', '',
          'Find the calls, file names, terms and short strings recorded in this research. '
          'The machine-readable index links each token to its authored source and line. '
          'Use the current findings and assumption ledger to interpret evidence; a source '
          'match does not establish a working API.', '', '## Contents', '',
          '- [Search](#search)', '- [Evidence entry points](#evidence-entry-points)',
          '- [Source files](#source-files)', '', '## Search', '',
          f"Indexed **{len(files)} source files** and **{len(data['terms'])} distinct terms**.", '',
          'The [JSON index](research-index.json) includes Python definitions/calls, '
          'C/Java/PowerShell call-shaped tokens, authored short strings and Markdown code terms. '
          'Vendor binaries, local artifacts, historical reproduction sources and generated indexes '
          'are excluded. Unresolved call-shaped tokens are explicitly labeled.', '',
          '```powershell', 'python research/evidence/build_knowledge_index.py --find GetItemBuffer',
          'python research/evidence/build_knowledge_index.py --find 0x5005',
          'python research/evidence/build_knowledge_index.py --check', '```', '',
          '## Evidence entry points', '',
          '- [Current findings](current-findings.md): capabilities and remaining dependencies.',
          '- [Assumptions and corrections](assumptions-and-corrections.md): what changed and why.',
          '- [Important interfaces and strings](interface-directory.md): evidence-ranked starting points.',
          '- [Glossary](../glossary.md): concepts and abbreviations.', '',
          '## Source files', '', 'Hashes use UTF-8 text with LF newlines so the navigation index is portable across checkouts. Binary evidence hashes remain separate.', '', '| File | Normalized text SHA-256 prefix |', '|---|---|']
    for item in files:
        rel = item['path']
        md.append(f"| [{rel}](../../{rel}) | `{item['sha256'][:12]}` |")
    # Keep one entry per line so a generated navigation index does not dominate
    # human PR review with hundreds of thousands of formatting-only lines.
    parts = ['{']
    for key in ('schema', 'hash_basis', 'scope'):
        parts.append('  '+json.dumps(key)+': '+json.dumps(data[key])+',')
    for key in ('files', 'terms'):
        parts.append('  '+json.dumps(key)+': [')
        parts.extend('    '+json.dumps(item, ensure_ascii=True)+(',' if i+1 < len(data[key]) else '')
                     for i, item in enumerate(data[key]))
        parts.append('  ]'+(',' if key == 'files' else ''))
    parts.append('}')
    return {'docs/knowledge/research-index.json': '\n'.join(parts)+'\n',
            'docs/knowledge/reference-index.md': '\n'.join(md)+'\n'}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--write', action='store_true')
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--find')
    args = parser.parse_args()
    try:
        root = args.root.absolute()
        if not root.is_dir():
            raise ValueError('Repository root must exist')
        data = build(root)
        if args.find is not None:
            matches = [entry for entry in data['terms'] if args.find.casefold() in entry['term'].casefold()]
            print(json.dumps(matches, indent=2))
            return 0
        outputs = rendered_files(data)
        changed = [name for name, text in outputs.items()
                   if not (root/name).is_file() or (root/name).read_text(encoding='utf-8') != text]
        if args.write:
            for name in changed:
                target = root/name
                if target.is_symlink() or any(p.is_symlink() for p in target.parents if p != root.parent):
                    raise ValueError('Linked output paths are not accepted')
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(outputs[name].encode('utf-8'))
        print(json.dumps({'status': 'Changed' if args.write and changed else 'Unchanged' if not changed else 'WouldChange',
                          'files': changed, 'indexed_files': len(data['files']), 'terms': len(data['terms'])}))
        return 1 if args.check and changed else 0
    except (OSError, ValueError, SyntaxError) as error:
        logging.error('Index failed: %s', error)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
