#!/usr/bin/env python3
"""Publish only approved synthetic model/poster artifacts; never copy photo evaluations.

Run with python3 tools/likeness/export_showcase.py (requires Pillow) after rebuilding
and validating dist/likeness-integrated. Output is committed for static hosting.
"""
import hashlib
import json
from pathlib import Path
import shutil
import struct
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'dist/likeness-integrated'
DEST = ROOT / 'companion/app/public/showcase'
CATALOG = ROOT / 'companion/app/src/data/character-showcase.json'


def main():
    source = json.loads((SOURCE / 'catalog.json').read_text())
    expected = {f'{group}{n:02}' for group, count in [('f', 6), ('h', 8), ('b', 5), ('c', 4)] for n in range(1, count + 1)}
    assert {entry['id'] for entry in source} == expected and len(source) == 23
    DEST.mkdir(parents=True, exist_ok=True)
    entries, provenance = [], []
    for entry in source:
        assert entry['integrated'] and entry['validation'], entry['id']
        model = SOURCE / f"models/{entry['id']}/model.glb"
        raw = model.read_bytes()
        magic, version, size = struct.unpack_from('<4sII', raw)
        assert magic == b'glTF' and version == 2 and size == len(raw)
        json_size, kind = struct.unpack_from('<II', raw, 12)
        assert kind == 0x4e4f534a
        gltf = json.loads(raw[20:20 + json_size])
        assert all('uri' not in item for item in gltf.get('buffers', []) + gltf.get('images', [])), 'GLB must be self-contained'
        shutil.copyfile(model, DEST / f"{entry['id']}.glb")
        with Image.open(SOURCE / f"models/{entry['id']}/poster.png") as img:
            img.convert('RGB').save(DEST / f"{entry['id']}.webp", 'WEBP', quality=85)
        entries.append({key: entry[key] for key in ['id', 'group', 'label', 'profile', 'headTarget', 'bodyTarget', 'headRadius', 'bodyRadius']})
        provenance.append({'id': entry['id'], 'glb_sha256': hashlib.sha256(raw).hexdigest()})
    CATALOG.write_text(json.dumps(entries, indent=2) + '\n')
    (DEST / 'provenance.json').write_text(json.dumps({'source': 'Approved integrated synthetic shape studies; fixed specs, no reference photos or inference.', 'models': provenance}, indent=2) + '\n')
    print(f'Exported {len(entries)} self-contained models and WebP posters ({sum(p.stat().st_size for p in DEST.iterdir()) / 1024 / 1024:.2f} MiB).')


if __name__ == '__main__':
    main()
