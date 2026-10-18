"""Check the texture containers coopdx actually distributes to joining clients."""
from pathlib import Path
import re
import struct
import sys


def check(root):
    mod = root / 'mods/sgl64'
    names = set(re.findall(r'texture = "([^"]+)"', (mod / 'sgl_minimap_data.lua').read_text()))
    names.add('sgl_minimap_player')
    if len(names) < 2:
        raise ValueError('No minimap artwork declared')
    for name in sorted(names):
        png = (mod / 'textures' / (name + '.png')).read_bytes()
        path = mod / 'textures' / (name + '.tex')
        if not path.exists():
            raise ValueError(f'Missing client texture: {path}; run tools/campus/build_minimap.py')
        data = path.read_bytes()
        size = data[1] if len(data) > 1 else 0
        if (len(data) < size + 6 or data[0] != 2
                or data[2:2+size] != name.encode('ascii')
                or struct.unpack('<I', data[2+size:6+size])[0] != len(png)
                or data[6+size:] != png or not png.startswith(b'\x89PNG\r\n\x1a\n')):
            raise ValueError(f'Invalid or stale client texture: {path}')
    print(f'Minimap client textures: {len(names)} valid containers match source PNGs')


if __name__ == '__main__':
    check(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2])
