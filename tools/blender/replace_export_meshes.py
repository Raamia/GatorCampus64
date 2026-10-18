"""Replace selected visual meshes in a DynOS export without replacing its level.

Useful when installed collision, interiors or other meshes have newer changes.
Reuses existing materials; refuses references to unavailable display lists or
vertices. The caller must back up the destination before writing it.
"""
from pathlib import Path
import re

DEFINITION = re.compile(r'^(Vtx|Gfx) (\w+)\[[^\]]*\] = \{\n.*?^\};\n', re.M | re.S)
EXTERN = re.compile(r'^extern (?:Vtx|Gfx) (\w+)\[[^\]]*\];\n', re.M)


def replace_meshes(source_dir, target_dir, names):
    source_dir, target_dir = Path(source_dir), Path(target_dir)
    slot = source_dir.name
    assert target_dir.name == slot
    prefixes = [slot + '_dl_' + re.sub(r'[^a-zA-Z0-9_]', '_', name) + '_mesh_layer_' for name in names]
    selected = lambda name: any(name.startswith(p) for p in prefixes)
    src = (source_dir / 'model.inc.c').read_text()
    old = (target_dir / 'model.inc.c').read_text()
    new_blocks = [m.group(0) for m in DEFINITION.finditer(src) if selected(m.group(2))]
    new_names = {m.group(2) for m in DEFINITION.finditer(src) if selected(m.group(2))}
    old_blocks = [m for m in DEFINITION.finditer(old) if selected(m.group(2))]
    assert old_blocks, f'No matching target meshes: {names}'
    # A completely hidden mesh can disappear from the new export. Keep an empty
    # root list so existing geo layouts do not need to change.
    for m in old_blocks:
        name = m.group(2)
        if re.search(r'_mesh_layer_\d+$', name) and name not in new_names:
            new_blocks.append(f'Gfx {name}[] = {{\n\tgsSPEndDisplayList(),\n}};\n')
            new_names.add(name)
    for prefix in prefixes:
        assert any(m.group(2).startswith(prefix) for m in old_blocks), f'Missing target mesh: {prefix}'
    available = {m.group(2) for m in DEFINITION.finditer(old) if not selected(m.group(2))} | new_names
    for block in new_blocks:
        for ref in re.findall(r'gsSP(?:DisplayList|Vertex)\((\w+)', block):
            assert ref in available, f'New mesh needs missing symbol {ref}'
    insertion = ''.join(new_blocks)
    first = True

    def sub(m):
        nonlocal first
        if not selected(m.group(2)):
            return m.group(0)
        if first:
            first = False
            return insertion
        return ''

    new = DEFINITION.sub(sub, old)
    strip = lambda text: DEFINITION.sub(lambda m: '' if selected(m.group(2)) else m.group(0), text)
    assert strip(new) == strip(old), 'Unrelated model declarations must remain byte-identical'
    header = (target_dir / 'header.inc.h').read_text()
    header = EXTERN.sub(lambda m: '' if selected(m.group(1)) else m.group(0), header)
    externs = []
    for block in new_blocks:
        declaration = block.split(' = {', 1)[0]
        externs.append('extern ' + declaration + ';\n')
    (target_dir / 'model.inc.c').write_text(new)
    (target_dir / 'header.inc.h').write_text(header + '\n' + ''.join(externs))
    return {'meshes': names, 'declarations': len(new_blocks)}
