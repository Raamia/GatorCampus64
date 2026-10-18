"""Make normal-lit exported materials independent of previously drawn actors.

Vertex-lit/unlit materials and existing light values are preserved. Run with
--check to reject missing lights, duplicate definitions or dangling light loads.
"""
import argparse
from collections import Counter
from pathlib import Path
import re

DL = re.compile(r'^Gfx (mat_(?!revert_)\w+)\[\] = \{\n(.*?)^\};', re.M | re.S)
MODE = re.compile(r'gsSP(Set|Clear)GeometryMode\(([^)]*)\)')
LOAD = re.compile(r'gsSP(?:SetLights\d|Light|LightColor)\(')


def needs_light(body):
    lit = True  # SM64 engine default, including materials with no mode commands
    for op, flags in MODE.findall(body):
        if 'G_LIGHTING' in [f.strip() for f in flags.split('|')]:
            lit = op == 'Set'
    return lit and not LOAD.search(body)


def check_source(src, require_lights=True):
    names = re.findall(r'^(?:Gfx|Lights\d|Vtx|u8)\s+(\w+)\s*(?:\[|=)', src, re.M)
    duplicates = [n for n, count in Counter(names).items() if count > 1]
    if duplicates:
        raise ValueError('Duplicate definitions: ' + ', '.join(duplicates))
    defined = set(re.findall(r'Lights\d\s+(\w+)\s*=', src))
    refs = set(re.findall(r'gsSPSetLights\d\((\w+)\)', src))
    if refs - defined:
        raise ValueError('Unresolved lights: ' + ', '.join(sorted(refs - defined)))
    missing = [m[1] for m in DL.finditer(src) if needs_light(m[2])]
    if require_lights and missing:
        raise ValueError('Materials inherit actor lights: ' + ', '.join(missing))
    return missing


def fix_level(level_dir):
    path = Path(level_dir) / 'model.inc.c'
    src = path.read_text()
    missing = check_source(src, require_lights=False)
    definitions = []
    def repair(m):
        if m[1] not in missing:
            return m[0]
        name = m[1][4:] + '_lights'
        if not re.search(r'Lights1\s+' + re.escape(name) + r'\s*=', src):
            definitions.append(f'Lights1 {name} = gdSPDefLights1(0x8C, 0x8C, 0x8C, 0xFF, 0xFF, 0xFF, 0x28, 0x28, 0x28);\n')
        return m[0].replace(m[2], '\tgsSPSetLights1(' + name + '),\n' + m[2], 1)
    result = DL.sub(repair, src)
    result = ''.join(definitions) + result
    check_source(result)
    if missing:
        path.write_text(result)
        header = Path(level_dir) / 'header.inc.h'
        if header.exists():
            text = header.read_text()
            for definition in definitions:
                name = definition.split()[1]
                text += f'\nextern Lights1 {name};\n'
            header.write_text(text)
    return len(missing)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('levels', nargs='+', type=Path)
    args = parser.parse_args()
    for level in args.levels:
        if args.check:
            check_source((level / 'model.inc.c').read_text())
            print(f'{level.name}: material lighting OK')
        else:
            print(f'{level.name}: repaired {fix_level(level)} materials')
