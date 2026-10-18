"""Build north-up minimap textures and Lua transforms from the campus/indoor plans.

Requires Pillow. Run from any directory: python tools/campus/build_minimap.py
Map data (c) OpenStreetMap contributors, ODbL 1.0. Indoor sources are recorded in
individual data/uf/*_layout.json files. These maps show plans, not navigation meshes.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/uf'
OUT = ROOT / 'mods/sgl64'
SIZE = 256
BG = (17, 29, 42, 255)
FLOOR = (43, 62, 77, 255)
EDGE = (113, 142, 160, 255)
records = []


def load(name):
    return json.loads((DATA / name).read_text())


def canvas(bounds, center):
    xmin, ymin, xmax, ymax = bounds
    span = max(xmax - xmin, ymax - ymin)
    left, top = (xmin + xmax - span) / 2, (ymin + ymax + span) / 2
    image = Image.new('RGBA', (SIZE, SIZE), BG)
    draw = ImageDraw.Draw(image)

    def project(points):
        return [((p[0] - left) * (SIZE - 1) / span, (top - p[1]) * (SIZE - 1) / span) for p in points]

    transform = dict(minX=round((left - center[0]) * 100), minZ=round(-(top - center[1]) * 100), span=round(span * 100))
    return image, draw, project, transform


def save(image, transform, key, level, area, label, height=None):
    texture = 'sgl_minimap_' + key
    image.save(OUT / 'textures' / (texture + '.png'))
    records.append(dict(texture=texture, level=level, area=area, label=label, height=height, **transform))


campus = load('campus.json')
identities = {'hub': ('LEVEL_CASTLE_GROUNDS', 'CAMPUS'), 'swamp': ('LEVEL_BOB', 'THE SWAMP'),
              'reitz_eng': ('LEVEL_WF', 'REITZ'), 'lake_alice': ('LEVEL_JRB', 'LAKE ALICE')}
for stage in load('stages.json')['stages']:
    if stage['key'] not in identities:
        continue
    box = stage['bounds_m']
    bounds = box['xmin'], box['ymin'], box['xmax'], box['ymax']
    image, draw, project, transform = canvas(bounds, stage['center_m'])

    def nearby(points):
        return points and max(p[0] for p in points) >= bounds[0] and min(p[0] for p in points) <= bounds[2] and max(p[1] for p in points) >= bounds[1] and min(p[1] for p in points) <= bounds[3]

    for area in campus['areas']:
        pts, tags = area.get('pts', []), area['tags']
        if len(pts) < 3 or not nearby(pts):
            continue
        water = tags.get('natural') == 'water' or 'water' in tags or tags.get('waterway') == 'riverbank'
        green = tags.get('natural') in ('wood', 'scrub') or tags.get('landuse') in ('grass', 'forest') or tags.get('leisure') in ('park', 'garden', 'pitch')
        if water or green:
            draw.polygon(project(pts), fill=(31, 80, 110, 255) if water else (29, 55, 49, 255))
    for way in campus['ways']:
        pts, tags = way.get('pts', []), way['tags']
        highway = tags.get('highway')
        if len(pts) < 2 or not nearby(pts) or not highway or highway in ('corridor', 'construction', 'proposed'):
            continue
        walking = highway in ('footway', 'path', 'pedestrian', 'steps', 'cycleway')
        draw.line(project(pts), fill=(139, 160, 169, 255) if walking else (65, 83, 99, 255), width=1 if walking else 3)
    for building in campus['buildings']:
        pts = building.get('pts', [])
        if len(pts) >= 3 and nearby(pts):
            draw.polygon(project(pts), fill=FLOOR, outline=EDGE, width=1)
    level, label = identities[stage['key']]
    save(image, transform, stage['key'], level, 1, label)

for key, level, area, label in [('marston', 'LEVEL_CCM', 1, 'MARSTON'), ('libwest', 'LEVEL_BBH', 1, 'LIBRARY WEST'), ('reitz_interior', 'LEVEL_WF', 2, 'REITZ')]:
    layout = load(key + '_layout.json')
    # Reitz's instant warp keeps area 1's world frame, not the plan's centroid.
    center = [-470, -293] if key == 'reitz_interior' else layout['center_m']
    for floor in layout['floors']:
        points = list(floor['outline_m'])
        for zone in floor['zones']:
            points.extend(zone.get('poly_m', []))
        bounds = min(p[0] for p in points) - 5, min(p[1] for p in points) - 5, max(p[0] for p in points) + 5, max(p[1] for p in points) + 5
        image, draw, project, transform = canvas(bounds, center)
        draw.polygon(project(floor['outline_m']), fill=FLOOR, outline=EDGE, width=2)
        for hole in floor.get('holes_m', []):
            poly = hole.get('poly_m', []) if isinstance(hole, dict) else hole
            if len(poly) >= 3:
                draw.polygon(project(poly), fill=BG, outline=EDGE)
        for zone in floor['zones']:
            poly = zone.get('poly_m', [])
            if len(poly) >= 3:
                draw.polygon(project(poly), fill=FLOOR, outline=(78, 101, 119, 255))
        for wall in floor.get('walls_m', []):
            if len(wall) == 4:
                draw.line(project([wall[:2], wall[2:]]), fill=EDGE, width=1)
        for opening in floor.get('openings', []):
            if 'a_m' in opening and 'b_m' in opening:
                draw.line(project([opening['a_m'], opening['b_m']]), fill=(151, 202, 211, 255), width=2)
        for vertical in layout['vertical']:
            poly = vertical.get('poly_m', [])
            if floor['id'] in vertical.get('floors', []) and len(poly) >= 3 and 'stair' in vertical.get('type', ''):
                draw.polygon(project(poly), fill=(125, 87, 49, 255), outline=(230, 166, 89, 255))
        save(image, transform, key + '_' + floor['id'].lower(), level, area, label + ' ' + floor['id'], round(floor['z_game_m'] * 100))

script = (OUT / 'levels/castle_grounds/script.c').read_text()
doors = []
for match in re.finditer(r'OBJECT\(MODEL_NONE,\s*(-?\d+),\s*(-?\d+),\s*(-?\d+),\s*0,\s*-?\d+,\s*0,\s*(0x[0-9A-Fa-f]+),\s*id_bhvSglDoor\)', script):
    x, y, z, params = match.groups()
    doors.append(dict(x=int(x), y=int(y), z=int(z), door=int(params, 16) >> 24))
lines = ['-- GENERATED by tools/campus/build_minimap.py. Map data (c) OpenStreetMap contributors, ODbL 1.0.', 'SGL_MINIMAP_MAPS = {']
for row in records:
    fields = [f'level = {row.pop("level")}']
    fields.extend(f'{key} = {json.dumps(value)}' for key, value in row.items() if value is not None)
    lines.append('    { ' + ', '.join(fields) + ' },')
lines.extend(['}', 'SGL_MINIMAP_DOORS = {'])
for door in doors:
    lines.append('    { ' + ', '.join(f'{k} = {v}' for k, v in door.items()) + ' },')
lines.extend(['}', ''])
(OUT / 'sgl_minimap_data.lua').write_text('\n'.join(lines))
print(f'Generated {len(records)} minimap textures and {len(doors)} campus destinations.')

arrow = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
ImageDraw.Draw(arrow).polygon([(16, 2), (28, 28), (16, 23), (4, 28)], fill=(214, 240, 255, 255), outline=(5, 12, 21, 255), width=3)
arrow.save(OUT / 'textures/sgl_minimap_player.png')

# coopdx sends .tex containers to clients, not source PNGs. Ship these explicitly:
# production may skip automatic PNG conversion when other compiled textures exist.
for name in [row['texture'] for row in records] + ['sgl_minimap_player']:
    subprocess.run([sys.executable, str(ROOT / 'tools/texture_to_tex.py'),
                    str(OUT / 'textures' / (name + '.png'))], check=True)
