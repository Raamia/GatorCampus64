"""Shared NPC placement policy, source receipts, exclusions and coverage gates."""
from pathlib import Path
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parents[2]
CONFIG = 'data/uf/npc_navigation.json'
SLOTS = {'SGL_HUB_LEVEL': 'castle_grounds', 'LEVEL_BOB': 'bob', 'LEVEL_WF': 'wf',
         'LEVEL_JRB': 'jrb', 'LEVEL_CCM': 'ccm', 'LEVEL_BBH': 'bbh'}


def settings(root=ROOT):
    data = json.loads((root / CONFIG).read_text())
    if data['schema'] != 1:
        raise ValueError('Unsupported NPC navigation schema')
    for region in data['outdoor_regions'].values():
        low, high = region['height_range']
        if not math.isfinite(low) or not math.isfinite(high) or low >= high:
            raise ValueError('Invalid outdoor height range')
    for box in data['exclusions']:
        if box['slot'] not in SLOTS.values() or box['area'] < 1:
            raise ValueError('Invalid exclusion area')
        if len(box['min']) != 3 or len(box['max']) != 3 or any(
                not math.isfinite(a) or not math.isfinite(b) or a >= b
                for a, b in zip(box['min'], box['max'])):
            raise ValueError('Invalid exclusion bounds')
    return data


def fingerprint(paths, root=ROOT):
    digest = hashlib.sha256()
    for path in sorted(set(str(p) for p in paths)):
        content = (root / path).read_bytes()  # missing required inputs fail closed
        digest.update(path.encode() + b'\0' + hashlib.sha256(content).digest())
    return digest.hexdigest()


def dependencies(slot, area):
    return [CONFIG, 'tools/npcs/navigation.py', 'tools/npcs/geometry.py',
            f'mods/sgl64/levels/{slot}/script.c',
            f'mods/sgl64/levels/{slot}/area_{area}/collision.inc.c']


def excluded(config, slot, area, x, y, z, radius, height):
    return any(box['slot'] == slot and box['area'] == area
               and x + radius > box['min'][0] and x - radius < box['max'][0]
               and y + height > box['min'][1] and y < box['max'][1]
               and z + radius > box['min'][2] and z - radius < box['max'][2]
               for box in config['exclusions'])


def supported(col, x, z, low, high, radius=60, height=200, min_normal=0.94):
    """A supported footprint in an explicit floor band, never a sky-down query.

    Multiple floors in the band are ambiguous: reject instead of selecting a
    planter/roof. Interior callers keep separate authored floor bands.
    """
    floor = col.floor(x, high - 78, z)
    if floor is None or floor[0] < low or floor[1] < min_normal:
        return None
    y = floor[0]
    lower = col.floor(x, y - 79, z)
    if lower is not None and lower[0] >= low:
        return None
    footprint = [y]
    for dx, dz in ((-radius, 0), (radius, 0), (0, -radius), (0, radius)):
        f = col.floor(x + dx, min(high, y + 25) - 78, z + dz)
        if f is None or f[1] < min_normal or abs(f[0] - y) > 25 or f[0] < low:
            return None
        footprint.append(f[0])
    if col.body_blocked(x, z, max(footprint) + 15, y + height, radius):
        return None
    return y


def coverage(config, slot, area, nodes, links):
    connected = {i for edge in links for i in edge}
    rows = []
    for region in config['coverage_regions']:
        if region['slot'] != slot or region['area'] != area:
            continue
        x0, z0, x1, z1 = region['bounds']
        count = sum(i in connected and x0 <= x <= x1 and z0 <= z <= z1
                    for i, (x, y, z) in enumerate(nodes, 1))
        rows.append(f"{region['name']}: {count} connected nodes")
        if count < region['minimum_nodes']:
            raise ValueError(f"NPC coverage lost: {rows[-1]} (need {region['minimum_nodes']})")
    return rows
