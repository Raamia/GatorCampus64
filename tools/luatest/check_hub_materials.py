"""Reject duplicate DynOS definitions and unresolved hub material lighting."""
from collections import Counter
from pathlib import Path
import re
import sys


def check(root):
    text = (root / 'mods/sgl64/levels/castle_grounds/model.inc.c').read_text()
    names = re.findall(r'^(?:Gfx|Lights1|Vtx|u8)\s+(\w+)\s*(?:\[|=)', text, re.M)
    duplicates = [name for name, count in Counter(names).items() if count > 1]
    if duplicates:
        raise ValueError('Duplicate hub definitions: ' + ', '.join(duplicates))
    lights = set(re.findall(r'Lights1\s+(\w+)\s*=', text))
    references = set(re.findall(r'gsSPSetLights1\((\w+)\)', text))
    if not references or not references <= lights:
        raise ValueError('Missing hub material lights: ' + ', '.join(references - lights))
    print(f'Hub materials: unique definitions; {len(references)} resolved daylight lights')


if __name__ == '__main__':
    check(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2])
