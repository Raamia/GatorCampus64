"""Check (or print) the LAKE_POINTS table of mods/sgl64/uf_lake_missions.lua (Lake Alice, course 3, LEVEL_JRB)
against its sources and, once it exists, the built level.

1. Source points (drift > 0.5 m fails), in order of preference:
   a. data/uf/lake_points.json (schema sgl64.lake_points/1, written by `build_stage.py -- lake_alice` from the
      BUILT collision), by point name (JSON_NAMES / JSON_LISTS below): spawn, boardwalk, west bog, the 15 lily
      pads, the observation deck, its star target and the star's start point, the Skeeter spots, act 1's
      lurking big gators, the small bog's middle (the nest), act 2's big-gator spots, the census stations and
      the bat barns' exits.
   b. without such a point: the landmark modules tools/campus/landmarks/lake_alice_water.py and
      lake_alice_shore.py (LANDMARKS "spots" / "markers", map metres, z = metres above the generator's collision
      ground) through the stages.json transform of the lake_alice window (centre (-1760, -660) m):
          X = (x + 1760) * 100,  Y = z * 100,  Z = -(y + 660) * 100,
      and stage_lake.py's rules (imported: pure Python) for the deck (DECK_TOP / DECK_R_IN on the lake-centre
      deck site), act 1's star (deck_point(STAR_U_M), STAR_UP_M) and its start (STAR_FROM_*), the big gators'
      homes (BIG_GATOR_SPOTS, act1_lurk_spots()) and the Skeeter spots (7 m beside lily pads 3, 6, 9, 12, 14,
      alternating sides).
   Derived entries are recomputed here with the rules the Lua comments state: the act 2 basking-gator line (end
   pad -> GATOR_BEND -> the small bog's south shore) with each gator's yaw and the HIGHEST lake bed under its
   back (a sunk gator stays 0.7 m over it), the star spots.
2. Lake sanity from the water module (no build needed): every gator, big-gator home, lurking-gator home and
   Skeeter spot is open water (depth >= MIN_DEPTH_M, clear of bog islands, lily pads and cypress trunks), a
   lurking gator's home is LURK_PAD_CLEAR_M from every lily pad's edge, act 1's star and its start point are
   outside the pavilion roof (deck frame, PAV_ROOF + STAR_ROOF_CLEAR_M), the census stations are >= 60 m apart
   (one player cannot staff two), every coordinate fits SM64's s16 range.
3. The built level (mods/sgl64/levels/jrb/area_1/collision.inc.c, when it exists), with SM64's find_floor
   rule (floors = normal.y > 0.01; a floor counts up to 78 units above the probe): every standing anchor has a
   floor within 0.5 m of its Y when probed from 2 m above (the missions' own geometry probes do the same),
   nothing static sticks into a gator's swept box (its back between sunk and surfaced, plus a rider), the
   gators, big gators and lurking gators float inside a water box (COL_WATER_BOX) whose surface is
   LAKE_POINTS.water_y, and no static floor or ceiling sits in a star's column (its spot -0.5 m .. +2.6 m: the
   vanilla star spawn rises 2.1 m over its target before it settles).
Usage (from anywhere):
  tools/.venv/bin/python -I tools/luatest/check_lake_points.py          check, exit 1 on any finding
  tools/.venv/bin/python -I tools/luatest/check_lake_points.py --print  print the source values (Lua syntax)
  ... --module   ignore data/uf/lake_points.json (landmark modules only)
"""
import json
import math
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
LUA = os.path.join(ROOT, "mods", "sgl64", "uf_lake_missions.lua")
LEVEL_DIR = os.path.join(ROOT, "mods", "sgl64", "levels", "jrb")
COLLISION = os.path.join(LEVEL_DIR, "area_1", "collision.inc.c")
TOL = 50                 # game units (0.5 m)
S16 = 32767
MIN_DEPTH_M = 1.6        # open water under a gator / big gator / Skeeter (Mario swims below 1 m)
LAST_GATOR_DEPTH_M = 0.8 # the last gator lies by the nest's underwater skirt (it barely sinks there)
SKEETER_DEPTH_M = 1.0
MIN_STATION_GAP_M = 60.0
DECK_TOP_M, DECK_R_IN_M = 0.2, 4.5   # stage_lake.py observation deck (fallback without the JSON)

# act 2 geometry (keep in step with the comments in uf_lake_missions.lua LAKE_POINTS)
GATOR_BEND = (-1716.0, -600.0)       # map m: the gator line turns north here, on the west rim of deep_1
GATOR_LEN_M, GATOR_W_M = 4.4, 1.6    # a basking gator's back (collision box)
GATOR_GAP_M = 2.0                    # water between two gators (a running jump)
GATOR_PAD_GAP_M = 2.0                # end pad edge -> first gator
GATOR_NEST_GAP_M = 1.2               # last gator -> the nest island's shore
SINK_M = 1.6                         # a sunk gator's back under the water surface (lua: SINK_DEPTH)
BED_CLEAR_M = 0.7                    # ... or this far over the highest bed under it (lua: BED_CLEAR)
SURF_LIFT_M = 0.12                   # an up gator's back over the water (lua: SURF_LIFT)
PLAT_THICK = 51                      # checkerboard platform: deck top 26 over its origin, underside 25 below
STAR_ROOF_CLEAR_M = 0.8              # act 1's star (and its start) this far outside the pavilion roof's eave
STAR_RISE = 260                      # a spawned star rises 210 units over its target (+ the star's size)
SKEETER_PADS = (2, 5, 8, 11, 13)     # stage_lake.py: 7 m beside these pads (0-based), alternating sides

# LAKE_POINTS key -> lake_points.json point name
JSON_NAMES = {
    "spawn_field": "spawn_0x0A",
    "boardwalk": "act1_boardwalk_mid",
    "bog": "act1_west_bog_top",
    "deck": "act1_deck_center",
    "deck_star": "act1_star_target",
    "deck_star_from": "act1_star_from",
    "nest": "act2_nest_island_top",
    "census_houses": "act4_station_houses",
    "census_gardens": "act4_station_gardens",
    "census_boardwalk": "act4_station_boardwalk",
    "bat_exit_2010": "act4_bat_exit_0",
    "bat_exit_2017": "act4_bat_exit_1",
}
# LAKE_POINTS list -> (JSON name pattern, count)
JSON_LISTS = {"pads": ("act1_pad_%02d", 15), "skeeters": ("act1_skeeter_%d", 5), "big_gators": ("act2_big_gator_%d", 3),
              "lurk_gators": ("act1_lurk_gator_%d", 2)}


# ------------------------------------------------------------------------------------------- sources
def stage_center():
    stages = json.load(open(os.path.join(ROOT, "data", "uf", "stages.json")))
    return [s for s in stages["stages"] if s["key"] == "lake_alice"][0]["center_m"]


def modules():
    sys.path.insert(0, os.path.join(ROOT, "tools", "campus"))
    from landmarks import lake_alice_shore as S, lake_alice_water as W
    by = {}
    for mod in (W, S):
        for L in mod.LANDMARKS:
            by[L["slug"]] = L
    return W, by


def stage_lake():
    """tools/campus/stage_lake.py: its rules are pure Python at import (Blender only inside the builders)."""
    sys.path.insert(0, os.path.join(ROOT, "tools", "campus"))
    import stage_lake as SL
    return SL


def game(cx, cy, x, y, z):
    return (int(round((x - cx) * 100)), int(round(z * 100)), int(round(-(y - cy) * 100)))


def game_yaw(dx, dy):
    """Map direction (east, north) -> SM64 yaw (0 = +Z = south, 0x4000 = +X = east)."""
    return int(round(math.atan2(dx, -dy) / (2 * math.pi) * 65536)) & 0xFFFF


def polyline_at(pts, s):
    """Point and unit direction at arc length s along the polyline."""
    for a, b in zip(pts, pts[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if s <= L:
            t = s / L
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t), ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
        s -= L
    a, b = pts[-2], pts[-1]
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    return b, ((b[0] - a[0]) / L, (b[1] - a[1]) / L)


def polyline_len(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def gator_bed(W, x, y, ux, uy):
    """Highest lake bed (m) under a gator's back centred at (x, y), long axis (ux, uy)."""
    best = -99.0
    for al in (-GATOR_LEN_M / 2, 0.0, GATOR_LEN_M / 2):
        for ac in (-GATOR_W_M / 2, 0.0, GATOR_W_M / 2):
            best = max(best, W.terrain_z(x + ux * al + uy * ac, y + uy * al - ux * ac))
    return best


def json_data(use_json):
    p = os.path.join(ROOT, "data", "uf", "lake_points.json")
    if not use_json or not os.path.exists(p):
        return None, {}
    data = json.load(open(p))
    named = {}

    def walk(o):
        if isinstance(o, dict):
            if isinstance(o.get("name"), str) and isinstance(o.get("game"), list) and len(o["game"]) == 3:
                named.setdefault(o["name"], o)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(data)
    return data, named


def homes_of(named, key, W, cx, cy, fallback, rule):
    """Big-gator homes (x, z, bed) from the JSON water points (bed = their floor_below_m), else from the
    stage_lake.py rule (map metres, bed = the water module's terrain)."""
    pat, n = JSON_LISTS[key]
    if all((pat % k) in named for k in range(n)):
        out = []
        for k in range(n):
            rec = named[pat % k]
            fb = rec.get("floor_below_m")
            bed = fb if fb is not None else W.terrain_z(rec["map_m"][0], rec["map_m"][1])
            out.append((int(rec["game"][0]), int(rec["game"][2]), int(round(bed * 100))))
        return out, "json " + pat.replace("%d", "N")
    out = []
    for (x, y) in fallback:
        X, _, Z = game(cx, cy, x, y, 0)
        out.append((X, Z, int(round(W.terrain_z(x, y) * 100))))
    return out, rule


def sources(use_json=True):
    """-> (points dict in game units, origin of each key, info for the lake checks)"""
    cx, cy = stage_center()
    W, L = modules()
    ws, ss = L["lake_alice_water"]["spots"], L["lake_alice_water"]["markers"]
    sh = {}
    for slug in ("bat_barns", "lake_boardwalks", "bat_house_field", "museum_road_edge", "baughman_center"):
        sh.update(L[slug]["spots"])
    data, named = json_data(use_json)

    def g(p, dz=0.0):
        return game(cx, cy, p[0], p[1], p[2] + dz)

    def gj(rec):
        return tuple(int(round(c)) for c in rec["game"])

    water_z = ss["water"]["surface_z_m"]
    out, origin = {}, {}
    out["water_y"] = int(round(water_z * 100))
    origin["water_y"] = "lake_alice_water markers.water"
    if data is not None and isinstance(data.get("water"), dict) and "surface_game_y" in data["water"]:
        out["water_y"], origin["water_y"] = int(data["water"]["surface_game_y"]), "json water.surface_game_y"

    def spot(name, d, key, dz=0.0):
        jn = JSON_NAMES.get(name)
        if jn in named:
            out[name], origin[name] = gj(named[jn]), "json " + jn
        else:
            out[name], origin[name] = g(d[key], dz), "module " + key

    spot("spawn_field", sh, "spawn_field")
    # act 1: north boardwalk -> west bog -> the north_shallows lily pads -> the observation deck
    spot("boardwalk", sh, "north_boardwalk_mid")
    spot("bog", ws, "island_1_top")
    site = ws["lake_center_deck_site"]
    spot("deck", {"site": (site[0], site[1], DECK_TOP_M)}, "site")
    r_in = DECK_R_IN_M
    try:
        r_in = data["act1_boardwalk_welcome"]["deck"]["geometry"]["inradius_m"]
    except (TypeError, KeyError):
        pass
    out["deck_r"], origin["deck_r"] = int(round(r_in * 100)), "deck inradius"
    SL = stage_lake()
    st_xy = SL.deck_point(SL.STAR_U_M)
    spot("deck_star", {"star": (st_xy[0], st_xy[1], SL.DECK_TOP + SL.STAR_UP_M)}, "star")
    sf_xy = SL.deck_point(SL.STAR_FROM_U_M)
    spot("deck_star_from", {"from": (sf_xy[0], sf_xy[1], SL.STAR_FROM_Z_M)}, "from")
    pads = sorted((p for p in ss["lily_pads"] if p["route"] == "north_shallows"), key=lambda p: p["i"])
    rows = []
    for i, p in enumerate(pads):
        jn = JSON_LISTS["pads"][0] % i
        if jn in named:
            rows.append(gj(named[jn]) + (int(round(named[jn].get("radius_m", p["r_m"]) * 100)),))
        else:
            rows.append(g(p["pos_m"]) + (int(round(p["r_m"] * 100)),))
    out["pads"], origin["pads"] = rows, "json act1_pad_NN" if JSON_LISTS["pads"][0] % 0 in named else "module lily_pads"
    sk = []
    for k, i in enumerate(SKEETER_PADS):
        jn = JSON_LISTS["skeeters"][0] % k
        if jn in named:
            sk.append(gj(named[jn]))
            continue
        a_, b_ = pads[i - 1]["pos_m"], pads[i]["pos_m"]
        f = math.atan2(b_[0] - a_[0], b_[1] - a_[1])
        side = 1 if k % 2 == 0 else -1
        ox, oy = math.cos(f) * side, -math.sin(f) * side
        sk.append(game(cx, cy, b_[0] + ox * 7.0, b_[1] + oy * 7.0, water_z))
    out["skeeters"], origin["skeeters"] = sk, "json act1_skeeter_N" if JSON_LISTS["skeeters"][0] % 0 in named else "derived"
    out["lurk_gators"], origin["lurk_gators"] = homes_of(named, "lurk_gators", W, cx, cy,
                                                         [p for p, _ in SL.act1_lurk_spots()], "stage_lake.act1_lurk_spots()")
    # act 2: the gator line, end pad -> GATOR_BEND -> the small bog's south shore
    spot("nest", ws, "island_3_top")
    out["nest_star"], origin["nest_star"] = (out["nest"][0], out["nest"][1] + 120, out["nest"][2]), "derived"
    ring = ss["island_rings_m"][2]
    nest = ws["island_3_top"]
    hit = None
    bx, by_ = GATOR_BEND
    for i in range(len(ring)):
        a, b = ring[i], ring[(i + 1) % len(ring)]
        den = (nest[0] - bx) * (b[1] - a[1]) - (nest[1] - by_) * (b[0] - a[0])
        if abs(den) < 1e-9:
            continue
        t = ((a[0] - bx) * (b[1] - a[1]) - (a[1] - by_) * (b[0] - a[0])) / den
        u = ((a[0] - bx) * (nest[1] - by_) - (a[1] - by_) * (nest[0] - bx)) / den
        if 0 <= t <= 1 and 0 <= u <= 1 and (hit is None or t < hit):
            hit = t
    shore = (bx + (nest[0] - bx) * hit, by_ + (nest[1] - by_) * hit)
    end = pads[-1]
    line = [(end["pos_m"][0], end["pos_m"][1]), GATOR_BEND, shore]
    total = polyline_len(line)
    s0 = end["r_m"] + GATOR_PAD_GAP_M + GATOR_LEN_M / 2
    s1 = total - GATOR_NEST_GAP_M - GATOR_LEN_M / 2
    n = int((s1 - s0) // (GATOR_LEN_M + GATOR_GAP_M)) + 1
    step = (s1 - s0) / (n - 1)
    gators = []
    for i in range(n):
        (x, y), (ux, uy) = polyline_at(line, s0 + i * step)
        X, _, Z = game(cx, cy, x, y, 0)
        gators.append((X, Z, game_yaw(ux, uy), int(round(gator_bed(W, x, y, ux, uy) * 100))))
    out["gators"], origin["gators"] = gators, "derived"
    out["gator_bend"], origin["gator_bend"] = game(cx, cy, GATOR_BEND[0], GATOR_BEND[1], water_z), "derived"
    big, origin["big_gators"] = homes_of(named, "big_gators", W, cx, cy, [p for p, _ in SL.BIG_GATOR_SPOTS],
                                         "stage_lake.BIG_GATOR_SPOTS")
    out["big_gators"] = big
    # act 3: census stations and the bat barns
    spot("census_houses", sh, "census_houses")
    spot("census_gardens", sh, "census_gardens")
    spot("census_boardwalk", sh, "census_boardwalk")
    spot("bat_exit_2010", sh, "barn2010_bat_exit")
    spot("bat_exit_2017", sh, "barn2017_bat_exit")
    h = out["census_houses"]
    out["census_star"], origin["census_star"] = (h[0], h[1] + 150, h[2]), "derived"
    info = {"W": W, "SL": SL, "cx": cx, "cy": cy, "line": line, "step": step, "shore": shore,
            "pads_m": [p["pos_m"] + [p["r_m"]] for p in ss["lily_pads"]], "cypress": ss["cypress"],
            "water_z": water_z, "json": data is not None}
    return out, origin, info


# ------------------------------------------------------------------------------------------- Lua side
def lua_points():
    text = open(LUA).read()
    body = text[text.index("local function lake_points() return {"):]
    body = body[:body.index("\n} end\n")]
    body = "\n".join(re.sub(r"--.*$", "", line) for line in body.split("\n"))
    out = {}
    for m in re.finditer(r"^\s{4}([a-z_0-9]+)\s*=\s*(-?\d+)\s*,", body, re.M):
        out[m.group(1)] = int(m.group(2))
    for m in re.finditer(r"^\s{4}([a-z_0-9]+)\s*=\s*\{\s*x\s*=\s*(-?\d+),\s*y\s*=\s*(-?\d+),\s*z\s*=\s*(-?\d+)\s*\}", body, re.M):
        out[m.group(1)] = tuple(int(m.group(i)) for i in (2, 3, 4))
    # lists: name = { { k = v, ... }, ... }
    for m in re.finditer(r"^\s{4}([a-z_0-9]+)\s*=\s*\{[ \t]*\n(.*?)^\s{4}\},", body, re.M | re.S):
        rows = []
        for row in re.findall(r"\{([^{}]*)\}", m.group(2)):
            kv = dict((k, int(v)) for k, v in re.findall(r"(\w+)\s*=\s*(-?\d+)", row))
            rows.append(kv)
        out[m.group(1)] = rows
    return out


LIST_KEYS = {
    "pads": ("x", "y", "z", "r"),
    "skeeters": ("x", "y", "z"),
    "gators": ("x", "z", "yaw", "bed"),
    "big_gators": ("x", "z", "bed"),
    "lurk_gators": ("x", "z", "bed"),
}
AIR = {"deck_star", "deck_star_from", "nest_star", "census_star", "regatta_star", "gator_bend", "bat_exit_2010",
       "bat_exit_2017"}
STARS = ("deck_star", "nest_star", "census_star", "regatta_star")


# ------------------------------------------------------------------------------------------- collision
class Collision:
    """Static collision of an exported area (COL_VERTEX / COL_TRI / COL_WATER_BOX), SM64 surface rules."""

    def __init__(self, path):
        src = open(path).read()
        verts = [tuple(int(v) for v in m) for m in re.findall(r"COL_VERTEX\(\s*(-?\d+),\s*(-?\d+),\s*(-?\d+)\s*\)", src)]
        self.tris = []
        for m in re.finditer(r"COL_TRI(?:_SPECIAL)?\(\s*(\d+),\s*(\d+),\s*(\d+)", src):
            a, b, c = (verts[int(m.group(i))] for i in (1, 2, 3))
            (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = a, b, c
            nx = (y2 - y1) * (z3 - z2) - (z2 - z1) * (y3 - y2)
            ny = (z2 - z1) * (x3 - x2) - (x2 - x1) * (z3 - z2)
            nz = (x2 - x1) * (y3 - y2) - (y2 - y1) * (x3 - x2)
            mag = math.sqrt(nx * nx + ny * ny + nz * nz)
            if mag == 0:
                continue
            nx, ny, nz = nx / mag, ny / mag, nz / mag
            self.tris.append((a, b, c, nx, ny, nz, -(nx * x1 + ny * y1 + nz * z1)))
        self.floors = [t for t in self.tris if t[4] > 0.01]
        self.water = [tuple(int(v) for v in m) for m in
                      re.findall(r"COL_WATER_BOX\(\s*[^,]+,\s*(-?\d+),\s*(-?\d+),\s*(-?\d+),\s*(-?\d+),\s*(-?\d+)\s*\)", src)]

    def find_floor(self, x, y, z):
        best = None
        for (a, b, c, nx, ny, nz, oo) in self.floors:
            (x1, _, z1), (x2, _, z2), (x3, _, z3) = a, b, c
            if (z1 - z) * (x2 - x1) - (x1 - x) * (z2 - z1) < 0:
                continue
            if (z2 - z) * (x3 - x2) - (x2 - x) * (z3 - z2) < 0:
                continue
            if (z3 - z) * (x1 - x3) - (x3 - x) * (z1 - z3) < 0:
                continue
            h = -(x * nx + nz * z + oo) / ny
            if y - (h - 78.0) < 0:
                continue
            if best is None or h > best:
                best = h
        return best

    def surfaces_in_column(self, x, z, y0, y1, r):
        """Heights of non-wall surfaces (floors and ceilings) over the square (x, z) +- r between y0 and y1."""
        out = []
        for (a, b, c, nx, ny, nz, oo) in self.tris:
            if abs(ny) <= 0.01:
                continue
            (x1, _, z1), (x2, _, z2), (x3, _, z3) = a, b, c
            for px, pz in ((x, z), (x - r, z - r), (x + r, z - r), (x - r, z + r), (x + r, z + r)):
                e1 = (z1 - pz) * (x2 - x1) - (x1 - px) * (z2 - z1)
                e2 = (z2 - pz) * (x3 - x2) - (x2 - px) * (z3 - z2)
                e3 = (z3 - pz) * (x1 - x3) - (x3 - px) * (z1 - z3)
                if (e1 >= 0 and e2 >= 0 and e3 >= 0) or (e1 <= 0 and e2 <= 0 and e3 <= 0):
                    h = -(px * nx + pz * nz + oo) / ny
                    if y0 < h < y1:
                        out.append(h)
        return out

    def water_at(self, x, z):
        """Surface y of the water box over (x, z) (SM64 tests loX < x < hiX strictly), or None."""
        for x1, z1, x2, z2, y in self.water:
            if min(x1, x2) < x < max(x1, x2) and min(z1, z2) < z < max(z1, z2):
                return y
        return None

    def in_box(self, cxz, yaw, hw, hl, y0, y1):
        """Triangles that reach into the rotated box (centre (x, z), yaw, half width / length, y0..y1),
        tested on the triangle's vertices and centroid."""
        cx, cz = cxz
        s, c = math.sin(yaw / 65536 * 2 * math.pi), math.cos(yaw / 65536 * 2 * math.pi)
        hits = []
        for t in self.tris:
            pts = list(t[:3]) + [tuple(sum(v[i] for v in t[:3]) / 3 for i in range(3))]
            for (x, y, z) in pts:
                dx, dz = x - cx, z - cz
                lz, lx = dx * s + dz * c, dx * c - dz * s
                if abs(lx) <= hw and abs(lz) <= hl and y0 < y < y1:
                    hits.append(t)
                    break
        return hits


# ------------------------------------------------------------------------------------------- checks
def lake_sanity(src, info):
    bad = 0
    W, cx, cy = info["W"], info["cx"], info["cy"]

    def m_of(X, Z):
        return X / 100 + cx, -Z / 100 + cy

    def open_water(name, X, Z, clear, min_depth=MIN_DEPTH_M):
        nonlocal bad
        x, y = m_of(X, Z)
        d = W.water_depth(x, y)
        if d < min_depth or W.island_at(x, y) is not None:
            print("LAKE %s at map (%.1f, %.1f): only %.2f m of water" % (name, x, y, d))
            bad += 1
        for px, py, _, pr in info["pads_m"]:
            if math.hypot(px - x, py - y) < pr + clear:
                print("LAKE %s at map (%.1f, %.1f) is on a lily pad (%.1f, %.1f)" % (name, x, y, px, py))
                bad += 1
        for c in info["cypress"]:
            if math.hypot(c["pos_m"][0] - x, c["pos_m"][1] - y) < c["trunk_r_m"] + clear:
                print("LAKE %s at map (%.1f, %.1f) hits a cypress trunk" % (name, x, y))
                bad += 1
        return d

    half_diag = math.hypot(GATOR_LEN_M / 2, GATOR_W_M / 2)
    last = len(src["gators"]) - 1
    for i, gt in enumerate(src["gators"]):
        open_water("gator %d" % (i + 1), gt[0], gt[1], half_diag + 0.3, LAST_GATOR_DEPTH_M if i == last else MIN_DEPTH_M)
    for i, b in enumerate(src["big_gators"]):
        open_water("big gator %d" % (i + 1), b[0], b[1], 1.0)
    SL = info["SL"]
    for i, b in enumerate(src["lurk_gators"]):
        open_water("lurking gator %d" % (i + 1), b[0], b[1], 1.0)
        x, y = m_of(b[0], b[1])
        for px, py, _, pr in info["pads_m"]:
            if math.hypot(px - x, py - y) - pr < SL.LURK_PAD_CLEAR_M - 0.05:
                print("LAKE lurking gator %d at map (%.1f, %.1f): only %.1f m from a lily pad's edge (want %.1f)"
                      % (i + 1, x, y, math.hypot(px - x, py - y) - pr, SL.LURK_PAD_CLEAR_M))
                bad += 1
    (dcx, dcy), t0 = SL.deck_frame()
    for key in ("deck_star", "deck_star_from"):
        x, y = m_of(src[key][0], src[key][2])
        du, dv = x - dcx, y - dcy
        u, v = du * math.cos(t0) + dv * math.sin(t0), -du * math.sin(t0) + dv * math.cos(t0)
        if max(abs(u), abs(v)) < SL.PAV_ROOF + STAR_ROOF_CLEAR_M:
            print("STAR %s at deck frame (%.2f, %.2f): under the pavilion roof (+-%.1f m)" % (key, u, v, SL.PAV_ROOF))
            bad += 1
    for i, s in enumerate(src["skeeters"]):
        open_water("skeeter %d" % (i + 1), s[0], s[2], 1.0, SKEETER_DEPTH_M)
    for i, gt in enumerate(src["gators"]):
        X, Z = gt[0], gt[1]
        if math.hypot(X - src["deck"][0], Z - src["deck"][2]) < src["deck_r"] / math.cos(math.pi / 8) + 260:
            print("LAKE gator %d overlaps the observation deck" % (i + 1))
            bad += 1
    st = [src["census_houses"], src["census_gardens"], src["census_boardwalk"]]
    for i in range(3):
        for j in range(i + 1, 3):
            d = math.hypot(st[i][0] - st[j][0], st[i][2] - st[j][2]) / 100
            if d < MIN_STATION_GAP_M:
                print("CENSUS stations %d and %d only %.1f m apart" % (i + 1, j + 1, d))
                bad += 1
    for k, v in src.items():
        vals = []
        if isinstance(v, tuple):
            vals = list(v)
        elif isinstance(v, list):
            for r in v:
                vals += list(r)
        elif isinstance(v, int):
            vals = [v]
        for n in vals:
            if abs(n) > S16 and k not in ("gators",):
                print("RANGE %s: %d is outside SM64's s16 range" % (k, n))
                bad += 1
    return bad


def compare(src, lua):
    bad = 0
    for k, v in src.items():
        have = lua.get(k)
        if have is None:
            print("missing in LAKE_POINTS: %s (source %s)" % (k, v))
            bad += 1
        elif k in LIST_KEYS:
            keys = LIST_KEYS[k]
            if len(have) != len(v):
                print("%s: %d in LAKE_POINTS, %d in the source" % (k.upper(), len(have), len(v)))
                bad += 1
                continue
            for i, (h, s) in enumerate(zip(have, v)):
                for key, sv in zip(keys, s):
                    tol = 0x200 if key == "yaw" else TOL
                    hv = h.get(key)
                    diff = None if hv is None else (((hv - sv + 0x8000) & 0xFFFF) - 0x8000 if key == "yaw" else hv - sv)
                    if diff is None or abs(diff) > tol:
                        print("DRIFT %s[%d].%s: %s vs source %s" % (k, i + 1, key, hv, sv))
                        bad += 1
        elif isinstance(v, int):
            if have != v:
                print("DRIFT %s: %s vs source %s" % (k, have, v))
                bad += 1
        else:
            d = max(abs(a - b) for a, b in zip(have, v))
            if d > TOL:
                print("DRIFT %s: %s vs source %s (%.1f m)" % (k, have, v, d / 100))
                bad += 1
    return bad


def check_built(lua, bad):
    if not os.path.exists(COLLISION):
        print("check_lake_points: levels/jrb not built: collision checks skipped")
        return bad
    col = Collision(COLLISION)
    n = 0
    floor_pts = [(k, v) for k, v in lua.items() if isinstance(v, tuple) and k not in AIR]
    floor_pts += [("pad %d" % (i + 1), (p["x"], p["y"], p["z"])) for i, p in enumerate(lua["pads"])]
    for name, (x, y, z) in floor_pts:
        n += 1
        h = col.find_floor(x, y + 200, z)
        if h is None or abs(h - y) > TOL:
            print("NO FLOOR %s at (%d, %d, %d): found %s" % (name, x, y, z, "none" if h is None else "%.0f" % h))
            bad += 1
    wy = lua["water_y"]
    hw, hl = GATOR_W_M * 50 + 30, GATOR_LEN_M * 50 + 30
    surf = wy + int(round(SURF_LIFT_M * 100))
    for i, gt in enumerate(lua["gators"]):
        n += 2
        # the gator's swept box: its underside when sunk (the Lua rule) up to a rider over its surfaced back
        sunk = min(surf, max(wy - int(SINK_M * 100), gt["bed"] + int(round(BED_CLEAR_M * 100))))
        hits = col.in_box((gt["x"], gt["z"]), gt["yaw"], hw, hl, sunk - PLAT_THICK, surf + 300)
        if hits:
            print("GATOR %d: %d static triangle(s) inside its box, e.g. %s" % (i + 1, len(hits), hits[0][:3]))
            bad += 1
        if col.water_at(gt["x"], gt["z"]) != wy:
            print("GATOR %d at (%d, %d): no water box with surface %d over it (found %s)"
                  % (i + 1, gt["x"], gt["z"], wy, col.water_at(gt["x"], gt["z"])))
            bad += 1
    for key in ("big_gators", "lurk_gators"):
        for i, b in enumerate(lua[key]):
            n += 1
            if col.water_at(b["x"], b["z"]) != wy:
                print("%s %d at (%d, %d): no water box with surface %d over it" % (key.upper(), i + 1, b["x"], b["z"], wy))
                bad += 1
    for key in STARS:
        n += 1
        x, y, z = lua[key]
        hits = col.surfaces_in_column(x, z, y - 50, y + STAR_RISE, 60)
        if hits:
            print("STAR %s at (%d, %d, %d): a static floor / ceiling in its column at y %s (the spawn rises 2.1 m)"
                  % (key, x, y, z, sorted(set(int(h) for h in hits))[:5]))
            bad += 1
    print("check_lake_points: %d collision checks on %s (%d triangles, %d water boxes)"
          % (n, os.path.relpath(COLLISION, ROOT), len(col.tris), len(col.water)))
    return bad


def fmt_lua(src, info):
    def row(keys, vals):
        return "{ " + ", ".join("%s = %d" % (k, v) for k, v in zip(keys, vals)) + " }"
    lines = []
    for k, v in src.items():
        if k in LIST_KEYS:
            lines.append("    %s = {" % k)
            for r in v:
                lines.append("        %s," % row(LIST_KEYS[k], r))
            lines.append("    },")
        elif isinstance(v, int):
            lines.append("    %s = %d," % (k, v))
        else:
            lines.append("    %s = %s," % (k, row(("x", "y", "z"), v)))
    lines.append("-- gator spacing %.2f m, nest shore at map (%.2f, %.2f)" % (info["step"], info["shore"][0], info["shore"][1]))
    return "\n".join(lines)


def main():
    src, origin, info = sources("--module" not in sys.argv)
    nj = sum(1 for v in origin.values() if v.startswith("json"))
    where = ("data/uf/lake_points.json (%d entries) + " % nj if info["json"] else "") + "tools/campus/landmarks/lake_alice_*.py"
    if "--print" in sys.argv:
        print(fmt_lua(src, info))
        for k, v in origin.items():
            print("--   %-16s <- %s" % (k, v))
        return 0
    bad = lake_sanity(src, info)
    lua = lua_points()
    bad += compare(src, lua)
    bad = check_built(lua, bad)
    n = sum(len(v) if isinstance(v, list) else 1 for v in src.values())
    if bad:
        print("check_lake_points: %d finding(s) (LAKE_POINTS vs %s)" % (bad, where))
        return 1
    print("check_lake_points: OK (%d values of LAKE_POINTS match %s; lake checks passed)" % (n, where))
    return 0


if __name__ == "__main__":
    sys.exit(main())
