"""Build conservative crowd stroll graphs for demo destinations from exported collision.

python3 -I tools/npcs/area_routes.py [--check]
Only authored floor elevations are sampled; no roof/table/stair guessing. Links require
continuous supported floor and body clearance. Disconnected rooms remain separate.
An area whose heights are 'terrain' (an outdoor stage with a stage_terrain.py heightfield, e.g. the
Reitz stage) samples the ground where the heightfield says it is instead: nodes and links follow the
slopes, still on supported, gently sloped ground with body clearance.
The existing OSM sidewalk graph still serves the hub.
"""
from functools import lru_cache
from pathlib import Path
import json
import math
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from campus_routes import Collision

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'mods/sgl64/sgl_campus_npc_areas.lua'
# slot, level, area, floor elevations, grid pitch, interior
AREAS = [
    ('bob', 'LEVEL_BOB', 1, [-1000, 0], 600, False),
    ('wf', 'LEVEL_WF', 1, 'terrain', 600, False),
    ('jrb', 'LEVEL_JRB', 1, [0, 20, 50], 600, False),
    ('wf', 'LEVEL_WF', 2, [-600, 0, 600, 1200, 1800, 2400, 2900, 3400], 200, True),
    ('ccm', 'LEVEL_CCM', 1, [-600, 0, 600, 1200, 1800], 200, True),
    ('bbh', 'LEVEL_BBH', 1, [0, 600, 1200, 1800, 2400, 3000], 200, True),
]


def build(slot, area, heights, pitch):
    base = ROOT / f'mods/sgl64/levels/{slot}'
    col = Collision(base / f'area_{area}/collision.inc.c')
    script = (base / 'script.c').read_text()
    block = re.search(rf'\bAREA\({area},.*?END_AREA\(\)', script, re.S).group()
    objects = [tuple(map(int, xyz)) for xyz in re.findall(
        r'OBJECT(?:_WITH_ACTS)?\(\s*\w+,\s*(-?\d+),\s*(-?\d+),\s*(-?\d+)', block)]
    vertices = [v for bucket in col.floors.values() for tri in bucket for v in tri[:3]]
    x0, x1 = max(-30000, min(v[0] for v in vertices)), min(30000, max(v[0] for v in vertices))
    z0, z1 = max(-30000, min(v[2] for v in vertices)), min(30000, max(v[2] for v in vertices))
    del vertices
    if area == 1 and slot in ('bob', 'wf', 'jrb'):
        key = {'bob': 'swamp', 'wf': 'reitz_eng', 'jrb': 'lake_alice'}[slot]
        stage = next(s for s in json.loads((ROOT / 'data/uf/stages.json').read_text())['stages'] if s['key'] == key)
        cx, cz = stage['center_m']
        bounds = stage['play_bounds_m']
        # Match the hub's 8 m perimeter inset: do not spawn beyond the playable
        # boundary just because the exported backdrop contains supporting floor.
        x0, x1 = max(x0, (bounds['xmin'] + 8 - cx) * 100), min(x1, (bounds['xmax'] - 8 - cx) * 100)
        z0, z1 = max(z0, -(bounds['ymax'] - 8 - cz) * 100), min(z1, -(bounds['ymin'] + 8 - cz) * 100)

    terrain = heights == 'terrain'
    if terrain:
        sys.path.insert(0, str(ROOT / 'tools/campus'))
        from stage_terrain import height_m
        key = {'bob': 'swamp', 'wf': 'reitz_eng', 'jrb': 'lake_alice'}[slot]
        stage = next(s for s in json.loads((ROOT / 'data/uf/stages.json').read_text())['stages'] if s['key'] == key)
        tcx, tcy = stage['center_m']

        @lru_cache(maxsize=300000)
        def ground(x, z):
            # the ground floor where the heightfield puts it (not a roof, bench or table above it)
            # the heightfield is smooth while the exported ground is flat triangles, so allow a little
            # play; 45 cm still rejects benches, ledges and roofs above the ground
            expect = round(height_m(key, tcx + x / 100.0, tcy - z / 100.0) * 100)
            floor = col.floor(x, expect + 40, z)
            if floor is None or floor[1] < 0.97 or abs(floor[0] - expect) > 45:
                return None
            return floor[0]

    def blocked_t(x, z, y0, y1, r):
        # like col.blocked, but a sloped floor triangle (the ground tiles) blocks only where its plane
        # actually rises into y0..y1 over the box: its bounding box alone spans metres of height
        seen = set()
        for gx in range(int(x - r) // col.CELL, int(x + r) // col.CELL + 1):
            for gz in range(int(z - r) // col.CELL, int(z + r) // col.CELL + 1):
                for t in col.solids.get((gx, gz), ()):
                    if id(t) in seen:
                        continue
                    seen.add(id(t))
                    a, b, c, nx, ny, nz, oo = t
                    xs, ys, zs = (a[0], b[0], c[0]), (a[1], b[1], c[1]), (a[2], b[2], c[2])
                    if not (max(xs) > x - r and min(xs) < x + r and max(ys) > y0 and min(ys) < y1
                            and max(zs) > z - r and min(zs) < z + r):
                        continue
                    if ny > 0.5:
                        top = max(-(px * nx + pz * nz + oo) / ny
                                  for px in (x - r, x, x + r) for pz in (z - r, z, z + r))
                        if top < y0:
                            continue
                    return True
        return False

    @lru_cache(maxsize=300000)
    def safe_t(x, z):
        y = ground(x, z)
        if y is None:
            return None
        for dx, dz in [(-60, 0), (60, 0), (0, -60), (0, 60)]:
            f = ground(x + dx, z + dz)
            if f is None or abs(f - y) > 20:
                return None
        if blocked_t(x, z, y + 25, y + 200, 75):
            return None
        if any(abs(oy - y) < 250 and math.hypot(ox - x, oz - z) < 160 for ox, oy, oz in objects):
            return None
        return y

    @lru_cache(maxsize=300000)
    def safe(x, y, z):
        # Query below the engine's +78 floor allowance to avoid selecting a desk
        # or adjacent floor above the requested elevation.
        for dx, dz in [(0, 0), (-60, 0), (60, 0), (0, -60), (0, 60)]:
            floor = col.floor(x + dx, y - 70, z + dz)
            if floor is None or floor[1] < 0.99 or abs(floor[0] - y) > 2:
                return False
        if col.blocked(x, z, y + 25, y + 200, 75):
            return False
        if any(abs(oy - y) < 250 and math.hypot(ox - x, oz - z) < 160 for ox, oy, oz in objects):
            return False
        return True

    def link_ok(a, b):
        if terrain:
            steps = math.ceil(math.hypot(b[0] - a[0], b[2] - a[2]) / 40)
            prev = a[1]
            for k in range(steps + 1):
                y = safe_t(round(a[0] + (b[0] - a[0]) * k / steps), round(a[2] + (b[2] - a[2]) * k / steps))
                if y is None or abs(y - prev) > 15:
                    return False
                prev = y
            return True
        steps = math.ceil(math.dist(a, b) / 40)
        return all(safe(*(round(a[j] + (b[j] - a[j]) * k / steps) for j in range(3)))
                   for k in range(steps + 1))

    nodes, index, links = [], {}, []
    if terrain:
        for x in range(math.ceil(x0 / pitch) * pitch, int(x1) + 1, pitch):
            for z in range(math.ceil(z0 / pitch) * pitch, int(z1) + 1, pitch):
                y = safe_t(x, z)
                if y is not None:
                    index[(x, z)] = len(nodes)
                    nodes.append((x, y, z))
    else:
        for y in heights:
            for x in range(math.ceil(x0 / pitch) * pitch, int(x1) + 1, pitch):
                for z in range(math.ceil(z0 / pitch) * pitch, int(z1) + 1, pitch):
                    if safe(x, y, z):
                        index[(x, y, z)] = len(nodes)
                        nodes.append((x, y, z))
    for i, (x, y, z) in enumerate(nodes):
        for key in ([(x + pitch, z), (x, z + pitch)] if terrain else [(x + pitch, y, z), (x, y, z + pitch)]):
            j = index.get(key)
            if j is not None and link_ok(nodes[i], nodes[j]):
                links.append((i, j))
    keep = sorted({i for link in links for i in link})
    remap = {old: new for new, old in enumerate(keep, 1)}
    return [nodes[i] for i in keep], [(remap[a], remap[b]) for a, b in links]


def main():
    lines = ['-- GENERATED by tools/npcs/area_routes.py from built area collision; do not edit.',
             '-- Flat supported paths with 0.75 m clearance; separate floors/rooms are never joined through walls.',
             'SGL_CROWD_AREAS = {']
    for slot, level, area, heights, pitch, indoor in AREAS:
        nodes, links = build(slot, area, heights, pitch)
        if not links:
            raise RuntimeError(f'{slot} area {area} has no safe crowd paths')
        print(f'{slot} area {area}: {len(nodes)} nodes, {len(links)} links', flush=True)
        lines += [f'    {{ level = {level}, area = {area}, indoor = {str(indoor).lower()},', '      nodes = {']
        for i in range(0, len(nodes), 6):
            lines.append('        ' + ' '.join('{ %d, %d, %d },' % p for p in nodes[i:i+6]))
        lines += ['      }, links = {']
        for i in range(0, len(links), 10):
            lines.append('        ' + ' '.join('{ %d, %d },' % p for p in links[i:i+10]))
        lines += ['      } },']
    lines += ['}']
    output = '\n'.join(lines) + '\n'
    if '--check' in sys.argv:
        if not OUT.exists() or OUT.read_text() != output:
            raise SystemExit('area_routes: stale output; run tools/npcs/area_routes.py')
        print('area_routes: OK')
    else:
        OUT.write_text(output)


if __name__ == '__main__':
    main()
