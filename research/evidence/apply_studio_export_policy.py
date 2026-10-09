"""Apply the repository's static SVG export policy to a rebuilt Studio HTML.

Default checks without writing. --write changes only the explicit HTML file.
Exit 0: policy matches/applied; 1: drift/invalid input/I/O; 2: invalid arguments.
No network/device calls. Rebuild the pinned upstream HTML to roll back.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / 'docs/overview/archify-studio/static-export-policy.js'
START = '// BEGIN WHT STATIC EXPORT POLICY\n'
END = '// END WHT STATIC EXPORT POLICY\n'
CALL = '  sanitizeStaticSvg(clone,r.title);\n'
ANCHOR = "  download(new XMLSerializer().serializeToString(clone),(r.id||'diagram')+'.svg','image/svg+xml');closeDialog('export-dialog');"


def patched(source: str, policy: str) -> str:
    block = START + policy.rstrip() + '\n' + END
    if START in source or END in source or CALL in source:
        if source.count(block) != 1 or source.count(CALL) != 1:
            raise ValueError('Incomplete or different local export policy; rebuild from the pinned upstream source')
        if block + 'function exportSVG(){' not in source or CALL + ANCHOR not in source:
            raise ValueError('Export policy is outside its expected call site')
        return source
    if source.count('function exportSVG(){') != 1 or source.count(ANCHOR) != 1:
        raise ValueError('Unrecognized Studio exporter; review the new renderer before applying')
    return source.replace('function exportSVG(){', block + 'function exportSVG(){', 1).replace(ANCHOR, CALL + ANCHOR, 1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--html', type=Path, required=True)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    try:
        raw = args.html.read_bytes()
        source = raw.decode('utf-8')
        result = patched(source, POLICY.read_text(encoding='utf-8'))
        if source == result:
            print('Unchanged')
            return 0
        if not args.write:
            print('Export policy missing; use --write to apply', file=sys.stderr)
            return 1
        args.html.write_bytes(result.encode('utf-8'))
        print('Applied')
        return 0
    except (OSError, UnicodeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
