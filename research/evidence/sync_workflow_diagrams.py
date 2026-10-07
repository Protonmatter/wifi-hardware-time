"""Preview/synchronize canonical Mermaid blocks using the checked-in manifest."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
BLOCK = re.compile(r'```mermaid\n(.*?)\n```', re.S)


def contained(root: Path, relative: str, suffix: str) -> Path:
    path = root/relative
    if path.suffix != suffix or path.is_symlink() or not path.resolve().is_relative_to((root/'docs').resolve()):
        raise ValueError('Diagram manifest path must stay inside docs with its expected suffix')
    return path


def updates(root: Path) -> dict[Path, str]:
    manifest = json.loads((root/'docs/knowledge/diagram-manifest.json').read_text())
    groups: dict[Path, dict[int, str]] = {}
    for item in manifest['diagrams']:
        source = contained(root, item['source'], '.mmd').read_text(encoding='utf-8').strip()
        for target in item['targets']:
            path = contained(root, target['file'], '.md')
            number = target['block']
            if type(number) is not int or number < 0 or number in groups.setdefault(path, {}):
                raise ValueError('Invalid or duplicate diagram target')
            groups[path][number] = source
    changed = {}
    for path, sources in groups.items():
        text = path.read_text(encoding='utf-8')
        matches = list(BLOCK.finditer(text))
        if max(sources) >= len(matches):
            raise ValueError(f'Missing diagram block in {path.name}')
        new = text
        for number in sorted(sources, reverse=True):
            match = matches[number]
            new = new[:match.start(1)] + sources[number] + new[match.end(1):]
        if new != text:
            changed[path] = new
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--write', action='store_true')
    mode.add_argument('--check', action='store_true')
    args = parser.parse_args()
    changes = updates(ROOT)
    if args.write:
        for path, text in changes.items():
            path.write_bytes(text.encode('utf-8'))
    print(json.dumps({'changed': [p.relative_to(ROOT).as_posix() for p in changes],
                      'applied': args.write}))
    return int(args.check and bool(changes))


if __name__ == '__main__':
    raise SystemExit(main())
