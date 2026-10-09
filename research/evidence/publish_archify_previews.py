"""Publish script-free SVG previews from the pinned classic Archify renderer.

Check is read-only. Write rerenders all seven authored specifications using an
explicit external checkout, materializes static paint, and updates preview hashes.
This deliberately supports the classic semantic SVG classes used by this set;
it is not a general HTML/CSS screenshot engine. No browser or network is used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / 'docs/overview/archify-tsf'
SVG_NS = 'http://www.w3.org/2000/svg'
PAINT = {'fill', 'stroke', 'stroke-width', 'stroke-dasharray', 'stroke-linecap',
         'stroke-linejoin', 'opacity', 'fill-opacity', 'stroke-opacity', 'color',
         'font-size', 'font-weight', 'text-anchor', 'vector-effect'}


def properties(body: str) -> dict[str, str]:
    return {key.strip(): value.strip() for declaration in body.split(';')
            if ':' in declaration for key, value in [declaration.split(':', 1)]}


def portable_svg(html: str, source_hash: str) -> bytes:
    """Keep renderer geometry and labels; resolve classic light semantic paint."""
    match = re.search(r'<svg\b.*?</svg>', html, re.S)
    if not match or not re.fullmatch(r'[0-9a-f]{64}', source_hash):
        raise ValueError('Missing SVG or invalid source digest')
    svg = ET.fromstring(match.group())
    css = '\n'.join(re.findall(r'<style>(.*?)</style>', html, re.S))
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    rules = re.findall(r'([^{}]+)\{([^{}]*)\}', css)
    variables: dict[str, str] = {}
    for selector, body in rules:
        if selector.strip() in (':root,[data-theme="dark"]', ':root,\n    [data-theme="dark"]', '[data-theme="light"]'):
            variables.update(properties(body))

    def resolve(value: str) -> str:
        def token(m: re.Match[str]) -> str:
            if m[1] not in variables:
                raise ValueError('Unresolved paint token: ' + m[1])
            return variables[m[1]]
        result = re.sub(r'var\((--[\w-]+)\)', token, value)
        if 'var(' in result:
            raise ValueError('Unsupported dynamic paint')
        return result

    used_classes = {name for element in svg.iter() for name in element.attrib.get('class', '').split()}
    class_rules: list[tuple[str, dict[str, str]]] = []
    for selector, body in rules:
        for part in selector.split(','):
            simple = re.fullmatch(r'(?:svg\s+)?(?:\.semantic-sigil\s+)?\.([\w-]+)', part.strip())
            if simple and simple[1] in used_classes:
                class_rules.append((simple[1], {k: resolve(v) for k, v in properties(body).items() if k in PAINT}))
    view = svg.attrib['viewBox'].split()
    if len(view) != 4 or any(not re.fullmatch(r'\d+(?:\.\d+)?', v) for v in view) or float(view[2]) <= 0 or float(view[3]) <= 0:
        raise ValueError('Invalid intrinsic SVG dimensions')
    svg.set('xmlns', SVG_NS)
    svg.set('width', view[2])
    svg.set('height', view[3])
    svg.set('font-family', 'Consolas, DejaVu Sans Mono, Liberation Mono, monospace')
    svg.set('data-specification-sha256', source_hash)
    svg.insert(0, ET.Element('rect', {'x':view[0], 'y':view[1], 'width':view[2],
                                    'height':view[3], 'fill':'#ffffff'}))
    for element in svg.iter():
        if element.tag.rsplit('}', 1)[-1] in ('script', 'foreignObject', 'iframe', 'animate'):
            raise ValueError('Executable or embedded content is not a static preview')
        classes = element.attrib.get('class', '').split()
        for name, paints in class_rules:
            if name in classes:
                element.attrib.update(paints)
        for name, value in properties(element.attrib.pop('style', '')).items():
            if name in PAINT:
                element.set(name, resolve(value))
        for name, value in list(element.attrib.items()):
            if name.lower().startswith('on') or (name.rsplit('}', 1)[-1] in ('href', 'src') and not value.startswith('#')):
                raise ValueError('External or executable SVG attribute')
            if re.search(r'url\(["\s]*(?:https?:|file:|//)', value):
                raise ValueError('External SVG paint')
            element.set(name, resolve(value))
        if 'semantic-sigil' in classes:
            for child in element:
                child.set('vector-effect', 'non-scaling-stroke')
    ET.indent(svg, space='  ')
    return ET.tostring(svg, encoding='utf-8', xml_declaration=True) + b'\n'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--write', action='store_true')
    mode.add_argument('--check', action='store_true')
    parser.add_argument('--archify-cli', type=Path)
    args = parser.parse_args()
    try:
        manifest_path = FOLDER / 'manifest.json'
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        if args.write:
            if args.archify_cli is None:
                parser.error('--write requires --archify-cli')
            cli = args.archify_cli.resolve(strict=True)
            tool_root = cli.parents[2]
            revision = subprocess.check_output(['git', '-C', str(tool_root), 'rev-parse', 'HEAD'], text=True).strip()
            if revision != manifest['archify_revision']:
                raise ValueError('Archify checkout revision does not match manifest')
            subprocess.run(['git', '-C', str(tool_root), 'diff', '--exit-code', 'HEAD', '--', 'archify'], check=True, stdout=subprocess.DEVNULL)
        generated: list[tuple[Path, bytes]] = []
        for item in manifest['diagrams']:
            slug = item['slug']
            if not re.fullmatch(r'[a-z]+(?:-[a-z]+)*', slug):
                raise ValueError('Invalid diagram slug')
            spec = FOLDER / (slug + '.json')
            digest = hashlib.sha256(spec.read_bytes()).hexdigest()
            if digest != item['specification_sha256']:
                raise ValueError('Specification hash drift: ' + slug)
            destination = FOLDER / 'previews' / (slug + '.svg')
            if args.write:
                output = ROOT / 'artifacts/archify-previews' / (slug + '.html')
                output.parent.mkdir(parents=True, exist_ok=True)
                subprocess.run(['node', str(cli), 'render', item['type'], str(spec), str(output), '--quality', 'showcase'], check=True, stdout=subprocess.DEVNULL)
                data = portable_svg(output.read_text(encoding='utf-8'), digest)
                item['preview_sha256'] = hashlib.sha256(data).hexdigest()
                generated.append((destination, data))
            else:
                data = destination.read_bytes()
                if hashlib.sha256(data).hexdigest() != item['preview_sha256'] or digest not in data.decode('utf-8'):
                    raise ValueError('Preview hash/source drift: ' + slug)
        if args.write:
            for path, data in generated:
                path.parent.mkdir(parents=True, exist_ok=True)
                if not path.exists() or path.read_bytes() != data:
                    path.write_bytes(data)
            manifest_path.write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8', newline='\n')
        print(json.dumps({'diagrams':len(manifest['diagrams']), 'applied':args.write}))
        return 0
    except (OSError, ValueError, KeyError, ET.ParseError, subprocess.CalledProcessError) as exc:
        print(json.dumps({'error':str(exc)}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
