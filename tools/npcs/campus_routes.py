"""Walking routes for the campus NPCs: the hub's mapped sidewalks, kept where the built level is walkable.

Reads the OSM footways of data/uf/campus.json (highway = footway / path / pedestrian, incl. crosswalks; no
steps, corridors, tunnels or bridges) inside the hub's play zone, maps them to game units the way
tools/campus/stage_data.py does (X = (x - cx) * 100, Z = -(y - cy) * 100), and keeps every stretch that the
built hub (mods/sgl64/levels/castle_grounds/area_1/collision.inc.c) can walk:

  - a floor under every sample (every SAMPLE units), flat (normal y >= MIN_NY) and near ground level
  - no step along the way (floor change between samples <= MAX_STEP)
  - no static wall / roof / prop within CLEAR units sideways, from knee to head height
  - no level-script object (trees, signs, poles, Goombas) within OBJ_GAP units

The largest connected network is written to mods/sgl64/sgl_campus_npc_routes.lua as nodes + links.
Usage: python3 -I tools/npcs/campus_routes.py [--check]   (--check: exit 1 if the Lua file is out of date)
"""
import json
import math
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import navigation as nav

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "luatest"))

CAMPUS = os.path.join(ROOT, "data", "uf", "campus.json")
STAGES = os.path.join(ROOT, "data", "uf", "stages.json")
LEVEL = os.path.join(ROOT, "mods", "sgl64", "levels", "castle_grounds")
OUT = os.path.join(ROOT, "mods", "sgl64", "sgl_campus_npc_routes.lua")

WALK_HIGHWAYS = {"footway", "path", "pedestrian"}
INSET_M = 8.0       # stay this far inside the play zone (its edge has invisible boundary walls)
SIMPLIFY = 60       # Douglas-Peucker tolerance for the route polylines (units)
MAX_LINK = 600      # longer links are split, so turning points stay close to the sidewalk
SAMPLE = 40         # walkability sample spacing along a link
MIN_NY = 0.94       # floor normal y (about 20 degrees)
MAX_STEP = 25       # floor change between two samples
CLEAR = 75          # sideways clearance: an NPC (about 0.5 m wide) keeps up to 0.35 m right of the line
OBJ_GAP = 110
KNEE, HEAD = 30, 190
MERGE = 30          # vertices closer than this become one node (OSM junctions share their node)


from geometry import Collision


def script_objects():
    s = open(os.path.join(LEVEL, "script.c")).read()
    a0 = s.index("AREA(1,")
    a1 = s.index("END_AREA()", a0)
    return [(int(m.group(1)), int(m.group(3)))
            for m in re.finditer(r"OBJECT(?:_WITH_ACTS)?\(\s*\w+,\s*(-?\d+),\s*(-?\d+),\s*(-?\d+),", s[a0:a1])]


def simplify(pts, tol):
    if len(pts) < 3:
        return pts
    (ax, az), (bx, bz) = pts[0], pts[-1]
    dx, dz = bx - ax, bz - az
    n = math.hypot(dx, dz) or 1.0
    far, idx = -1.0, 0
    for i in range(1, len(pts) - 1):
        d = abs((pts[i][0] - ax) * dz - (pts[i][1] - az) * dx) / n
        if d > far:
            far, idx = d, i
    if far <= tol:
        return [pts[0], pts[-1]]
    return simplify(pts[:idx + 1], tol)[:-1] + simplify(pts[idx:], tol)


def main():
    stage = next(s for s in json.load(open(STAGES))["stages"] if s["key"] == "hub")
    cx, cy = stage["center_m"]
    pb = stage["play_bounds_m"]
    x0, x1 = (pb["xmin"] + INSET_M - cx) * 100, (pb["xmax"] - INSET_M - cx) * 100
    z0, z1 = -(pb["ymax"] - INSET_M - cy) * 100, -(pb["ymin"] + INSET_M - cy) * 100
    col = Collision(os.path.join(LEVEL, "area_1", "collision.inc.c"))
    objs = script_objects()

    config = nav.settings(Path(ROOT))
    low, high = config['outdoor_regions']['castle_grounds']['height_range']

    def walkable(x, z):
        if not (x0 <= x <= x1 and z0 <= z <= z1):
            return None
        y = nav.supported(col, x, z, low, high, CLEAR, HEAD, MIN_NY)
        if y is None or nav.excluded(config, 'castle_grounds', 1, x, y, z, CLEAR, HEAD):
            return None
        if any(math.hypot(ox-x, oz-z) < OBJ_GAP for ox, oz in objs):
            return None
        return y

    def link_ok(a, b):
        n = max(1, int(math.dist(a[:2], b[:2]) // SAMPLE))
        prev = None
        for i in range(n + 1):
            t = i / n
            h = walkable(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            if h is None or (prev is not None and abs(h - prev) > MAX_STEP):
                return False
            prev = h
        return True

    raw = []
    for w in json.load(open(CAMPUS))["ways"]:
        tags = w.get("tags", {})
        if tags.get("highway") not in WALK_HIGHWAYS or tags.get("tunnel") or tags.get("bridge") \
                or tags.get("indoor") or tags.get("level") not in (None, "0"):
            continue
        pts = [((x - cx) * 100, -(y - cy) * 100) for x, y in w["pts"]]
        if any(x0 - 2000 <= x <= x1 + 2000 and z0 - 2000 <= z <= z1 + 2000 for x, z in pts):
            raw.append(pts)
    # junctions (a vertex shared by two ways, or any way's end) survive the simplification
    uses = {}
    for pts in raw:
        for k, p in enumerate(pts):
            key = (round(p[0]), round(p[1]))
            uses[key] = uses.get(key, 0) + (2 if k in (0, len(pts) - 1) else 1)
    ways = []
    for pts in raw:
        out, start = [], 0
        for k in range(1, len(pts)):
            if k == len(pts) - 1 or uses[(round(pts[k][0]), round(pts[k][1]))] > 1:
                out += simplify(pts[start:k + 1], SIMPLIFY)[0 if not out else 1:]
                start = k
        ways.append(out)

    nodes, index, links = [], {}, set()

    def node(x, z):
        key = (round(x / MERGE), round(z / MERGE))
        if key not in index:
            h = walkable(x, z)
            index[key] = None if h is None else len(nodes)
            if h is not None:
                nodes.append((x, z, h))
        return index[key]

    for pts in ways:
        dense = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            n = max(1, math.ceil(math.dist(a, b) / MAX_LINK))
            dense += [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n) for i in range(1, n + 1)]
        ids = [node(x, z) for x, z in dense]
        for i, j in zip(ids, ids[1:]):
            if i is not None and j is not None and i != j and link_ok(nodes[i], nodes[j]):
                links.add((min(i, j), max(i, j)))

    # largest connected network
    adj = {i: set() for i in range(len(nodes))}
    for i, j in links:
        adj[i].add(j)
        adj[j].add(i)
    best, seen = [], set()
    for s in adj:
        if s in seen or not adj[s]:
            continue
        comp, stack = [], [s]
        seen.add(s)
        while stack:
            u = stack.pop()
            comp.append(u)
            for v in adj[u]:
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
        if len(comp) > len(best):
            best = comp
    keep = sorted(best)
    renum = {old: new for new, old in enumerate(keep, 1)}
    out_links = sorted((renum[i], renum[j]) for i, j in links if i in renum and j in renum)
    length = sum(math.dist(nodes[i][:2], nodes[j][:2]) for i, j in links if i in renum)

    final_nodes = [(round(nodes[i][0]), round(nodes[i][2]), round(nodes[i][1])) for i in keep]
    if len(out_links) < config['outdoor_regions']['castle_grounds']['minimum_links']:
        raise ValueError('Hub crowd route coverage below configured minimum')
    for summary in nav.coverage(config, 'castle_grounds', 1, final_nodes, out_links):
        print(summary)
    receipt = nav.fingerprint(nav.dependencies('castle_grounds', 1) +
        ['tools/npcs/campus_routes.py', 'data/uf/campus.json', 'data/uf/stages.json'], Path(ROOT))
    lines = [
        '-- Source SHA256: ' + receipt,
        "-- GENERATED by tools/npcs/campus_routes.py from data/uf/campus.json (OSM footways) and the built hub's",
        "-- collision. Do not edit; re-run the script after rebuilding levels/castle_grounds.",
        "-- The campus NPCs (sgl_campus_npcs.lua) walk these links. Map data (c) OpenStreetMap contributors, ODbL 1.0.",
        f"-- {len(keep)} nodes, {len(out_links)} links, {length / 100:.0f} m of sidewalk.",
        "SGL_CAMPUS_ROUTES = {",
        "    nodes = {  -- { x, y, z }",
    ]
    row = []
    for old in keep:
        x, z, h = nodes[old]
        row.append("{ %d, %d, %d }," % (round(x), round(h), round(z)))
        if len(row) == 6:
            lines.append("        " + " ".join(row))
            row = []
    if row:
        lines.append("        " + " ".join(row))
    lines.append("    },")
    lines.append("    links = {  -- node index pairs")
    for k in range(0, len(out_links), 10):
        lines.append("        " + " ".join("{ %d, %d }," % l for l in out_links[k:k + 10]))
    lines.append("    },")
    lines.append("}")
    text = "\n".join(lines) + "\n"

    if "--check" in sys.argv:
        ok = os.path.isfile(OUT) and open(OUT).read() == text
        print("campus_routes: " + ("OK" if ok else "sgl_campus_npc_routes.lua is out of date; re-run the script"))
        return 0 if ok else 1
    with open(OUT, "w") as f:
        f.write(text)
    print(f"campus_routes: {len(keep)} nodes, {len(out_links)} links, {length / 100:.0f} m "
          f"(of {len(nodes)} walkable nodes from {len(ways)} ways) -> {os.path.relpath(OUT, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
