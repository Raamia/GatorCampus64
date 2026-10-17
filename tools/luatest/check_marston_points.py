"""Check (or print) the MARSTON_POINTS table of mods/sgl64/uf_marston_missions.lua (Marston Science Library,
course 4, LEVEL_CCM, an interior stage) against its sources and, once it exists, the built level.

1. Source values (drift > 0.5 m fails), in order of preference:
   a. data/uf/marston_points.json (written by the stage build from the BUILT collision, when it exists): any
      point record { "name": ..., "game": [X, floor Y, Z] } whose name is in JSON_NAMES below overrides the
      layout value of that MARSTON_POINTS key.
   b. data/uf/marston_layout.json (the layout research, map metres) through the stages.json transform of the
      marston window (centre_m (-59.6, -98.9)):
          X = (x + 59.6) * 100,  Y = z * 100,  Z = -(y + 98.9) * 100
      either straight from its "missions" anchors (spawn, act 2 start, kiosks K1/K2/K4) or from the layout
      geometry with the rules below (RULES), which are the ones the Lua comments state.
2. Layout sanity (no build needed): every standing point lies on walkable floor of its storey (inside the
   floor outline or an outdoor zone, outside non-walkable zones, props and the atrium void) unless it is ON a
   prop (textbooks on furniture tops), 0.4 m clear of the columns; the Shusher patrols keep 0.6 m from props,
   columns and walls and stay out of the void; the act 1 lifts stay inside the atrium void 0.5 m from its edges
   and 0.8 m from its free columns; the act 1 barriers cover every stair / core / elevator 2 door of floors 1-4
   (0.3 m past both jambs); every pair of kiosks lit together is out of one player's reach in the 4 s booking
   window (two floors apart, or >= MIN_KIOSK_PATH_M of straight legs through the nearest stair / core /
   elevator door, + 10 m per storey climbed); a spawned star's 4 m hump (bhvStarSpawnCoordinates) stays under
   its storey's ceiling; every coordinate fits SM64's s16 range.
3. The built level (mods/sgl64/levels/ccm/area_1/collision.inc.c, when it exists), with SM64's find_floor rule
   (floors = normal.y > 0.01; a floor counts up to 78 units above the probe): every standing anchor has a floor
   within 0.5 m of its Y when probed from 2 m above (the missions' own geometry probes do the same), nothing
   static sits in a lift's travel box (deck + 2 m of rider headroom), and no static floor or ceiling sits in a
   star's column (its spot -0.5 m .. +4.6 m: the hump and the star's size).
4. Airborne collision of the built level (fix round), with coopdx v1.5.1's AIRBORNE rules (perform_air_step sets
   gFindWallDirectionAirborne, so walls push the vanilla way: an airborne Mario within 50 units of a wall plane, on
   EITHER side, is pushed to its front side; plus find_floor / find_ceil and the 160-unit ceiling rule):
   a. every slab-edge face (the 0.6 m fascia of a hole in a floor: the chute hatch, the atrium balconies) faces INTO
      the hole, away from the slab (inverted ones popped players falling through the hatch back onto F2);
   b. the book-chute hatch: players stepping off its rim on every side, at walking to running speed, land on the
      slide (SURFACE_SLIPPERY);
   c. no wall at least 2 m tall that is thinner than 12 units (two opposite faces closer than a 48 u/f long jump's
      quarter step) stands between two open floor spaces: an airborne player would be thrown through it (glass rooms
      such as L129, act 3's lock).
Usage (from anywhere):
  tools/.venv/bin/python -I tools/luatest/check_marston_points.py          check, exit 1 on any finding
  tools/.venv/bin/python -I tools/luatest/check_marston_points.py --print  print the source values (Lua syntax)
  ... --layout   ignore data/uf/marston_points.json (layout only)
"""
import json
import math
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
LUA = os.path.join(ROOT, "mods", "sgl64", "uf_marston_missions.lua")
LAYOUT = os.path.join(ROOT, "data", "uf", "marston_layout.json")
# SGL_CCM_POINTS / SGL_CCM_COLLISION: check a scratch build instead
POINTS_JSON = os.environ.get("SGL_CCM_POINTS") or os.path.join(ROOT, "data", "uf", "marston_points.json")
COLLISION = os.environ.get("SGL_CCM_COLLISION") or os.path.join(ROOT, "mods", "sgl64", "levels", "ccm", "area_1",
                                                                 "collision.inc.c")
TOL = 50                   # game units (0.5 m)
S16 = 32767
COLUMN_HALF_M = 0.35       # the inferred module columns (columns_m are centre points)
STAND_CLEAR_M = 0.4        # a standing anchor from a column
PATROL_CLEAR_M = 0.6       # a Shusher (Toad, ~0.4 m radius) from props, columns and the void
PATROL_WALL_M = 0.5        # ... and from the floor outline (walls)
LIFT_VOID_CLEAR_M = 0.5    # a lift deck from the atrium void's edges (railings)
LIFT_COLUMN_CLEAR_M = 0.8  # ... and from its free columns
BARRIER_MARGIN_M = 0.3     # an act 1 barrier reaches this far past both door jambs
MIN_KIOSK_PATH_M = 45.0    # one player cannot run this (plus the stairs) inside the 4 s window
STAIR_M_PER_STOREY = 10.0
STAR_HUMP = 400            # bhvStarSpawnCoordinates: sins(t * 0x8000 / 30) * 400 over the line to its target
STAR_SIZE = 60

# ------------------------------------------------------------------------------------------- the rules
# (keep in step with the MARSTON_POINTS comments in uf_marston_missions.lua)
RAIL_M = 1.0               # atrium balcony railings (layout atrium.game.railing_m)
SHAFT_FRONT_M = 1.0        # the out-of-order shaft's marker: 1 m in front of elevator 1's F2 door (doors face south)
LIFT_HALF_M = 1.1          # act 1 book-cart lifts: 2.2 x 2.2 m decks ...
LIFT_CLEAR_M = 0.6         # ... 0.6 m inside the void's east (lift A) / west (lift B) edge, on its centre line
GOAL_M = (-62.0, -80.0)    # act 1 goal: the 5th-floor north reading room (centre of an 8 m disc)
CLIMB_STAR_M = (-64.0, -79.6, 0.8)   # act 1 star: the reading room's middle aisle, 3 m from the column, 0.8 m up
QUIET_STAR_M = (-87.1, -99.0, 0.8)   # act 2 star: the west window desk's aisle (design 7.3 act 2's goal), 0.8 m up
ROOM_STAR_UP_M = 0.8       # act 3 star: the layout's L129 star spot, 0.8 m over the floor (the hump clears 5.4 m)
K3_MOVED_M = (-45.5, -105.0)  # kiosk K3 on the 4th floor's quiet study (the layout's 3rd-floor K3 is a 3.4 s run
                              # from K2 up the grand stair: see MIN_KIOSK_PATH_M)
# act 2: the eight lost textbooks (map m) and what they lie on (a prop id = its top, None = the floor)
BOOKS = [
    ("VIEW COUNTER", (-66.0, -70.1), "window_desks_n"),
    ("READING TABLE", (-57.0, -73.0), "reading_tables_n_1"),
    ("ATRIUM RAIL", (-55.0, -91.6), None),
    ("EAST TERRACE", (-47.0, -100.0), None),
    ("ELEVATOR LOBBY", (-73.75, -91.8), None),
    ("COMPUTER ROW", (-84.35, -88.35), "computers_f5"),
    ("CARREL TOP", (-76.5, -101.0), "carrels_w_3"),
    ("BACK AISLE", (-78.75, -104.5), None),
]
# act 2: the Shushers' patrols on floor 5 (map m): north reading room (ping-pong: middle aisle west, west aisle
# south, south band east), west reading room (a loop through two carrel aisles and both end bands), the corridor
# south of the core (ping-pong)
PATROLS = {
    "patrol_n": [(-59.0, -78.0), (-68.6, -78.0), (-68.6, -89.9), (-59.0, -89.9)],
    "patrol_w": [(-83.25, -94.0), (-83.25, -107.15), (-74.25, -107.15), (-74.25, -94.0)],
    "patrol_c": [(-86.5, -91.8), (-66.5, -91.8)],
}
PATROL_LOOP = {"patrol_n": False, "patrol_w": True, "patrol_c": False}
KIOSK_NAMES = ["1F BY ROOM L129", "2F ATRIUM", "4F QUIET STUDY", "5F WEST WING"]
# the side a player stands on to punch each kiosk (D-pad Down lands there, KIOSK_STAND_M away, facing the kiosk):
# K1 from the north (L127's glass is 2.5 m east), K2 from the south (the service desk counter is north), K3 from the
# west (the aisle between carrel rows 4 and 5), K4 from the east (the corridor)
KIOSK_YAW = [0x0000, 0x8000, 0x4000, 0xC000]
KIOSK_STAND_M = 2.2
SIDE_BY_SIDE_M = 0.8       # teleported players land up to this far round the spot (globalIndex % 8)
KIOSK_SETS = {2: (1, 4), 3: (1, 3, 4), 4: (1, 2, 3, 4)}   # lit kiosks by players here (uf_marston_missions.lua)
FLOOR_Z = {"F1": -6.0, "F2": 0.0, "F3": 6.0, "F4": 12.0, "F5": 18.0}

# MARSTON_POINTS key -> marston_points.json point names that may provide it (the build's names are not fixed
# yet: the layout's mission anchor names first)
JSON_NAMES = {
    "spawn": ("spawn_0x0A", "spawn"),
    "quiet_start": ("act2_start", "design_act2_quiet_floor_start"),
    "climb_star": ("act1_star",),
    "quiet_star": ("act2_star",),
    "room_star": ("act3_star",),
}


# ------------------------------------------------------------------------------------------- geometry
def pip(pt, poly):
    x, y = pt
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xi = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if xi > x:
                inside = not inside
    return inside


def seg_dist(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
    return math.hypot(p[0] - (ax + t * dx), p[1] - (ay + t * dy))


def poly_dist(p, poly):
    """0 inside, else the distance to the polygon's boundary."""
    if pip(p, poly):
        return 0.0
    return min(seg_dist(p, poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly)))


def edge_dist(p, poly):
    return min(seg_dist(p, poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly)))


def rect_of(prop):
    if "poly_m" in prop:
        return prop["poly_m"]
    (x, y), (w, d) = prop["pos_m"], prop.get("size_m", (0.6, 0.6))
    return [(x - w / 2, y - d / 2), (x + w / 2, y - d / 2), (x + w / 2, y + d / 2), (x - w / 2, y + d / 2)]


def sample_polyline(pts, loop, step=0.25):
    segs = list(zip(pts, pts[1:])) + ([(pts[-1], pts[0])] if loop else [])
    out = []
    for a, b in segs:
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(1, int(L / step))
        for i in range(n + 1):
            t = i / n
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


# ------------------------------------------------------------------------------------------- sources
class Layout:
    def __init__(self):
        self.d = json.load(open(LAYOUT))
        self.cx, self.cy = self.d["center_m"]
        self.floors = {f["id"]: f for f in self.d["floors"]}
        self.vertical = {v["id"]: v for v in self.d["vertical"]}

    def game(self, x, y, z):
        return (int(round((x - self.cx) * 100)), int(round(z * 100)), int(round(-(y - self.cy) * 100)))

    def gx(self, x):
        return int(round((x - self.cx) * 100))

    def gz(self, y):
        return int(round(-(y - self.cy) * 100))

    def prop(self, fid, pid):
        for p in self.floors[fid]["props"]:
            if p["id"] == pid:
                return p
        raise KeyError(pid)

    def zone(self, fid, zid):
        for z in self.floors[fid]["zones"]:
            if z["id"] == zid:
                return z
        raise KeyError(zid)

    def atrium(self):
        return self.vertical["atrium"]["poly_m"]


def json_points(use_json):
    if not use_json or not os.path.exists(POINTS_JSON):
        return {}
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
    walk(json.load(open(POINTS_JSON)))
    return named


def sources(use_json=True):
    """-> (values in MARSTON_POINTS order, origin per key, info for the sanity checks)"""
    L = Layout()
    M = L.d["missions"]
    out, origin = {}, {}
    info = {"layout": L}

    def put(k, v, why):
        out[k] = v
        origin[k] = why

    atr = L.atrium()
    ax0, ax1 = min(p[0] for p in atr), max(p[0] for p in atr)
    ay0, ay1 = min(p[1] for p in atr), max(p[1] for p in atr)
    aym = (ay0 + ay1) / 2

    put("spawn", tuple(M["spawn"]["game_xyz"]), "layout missions.spawn")
    xs, ys = [], []
    for f in L.d["floors"]:
        xs += [p[0] for p in f["outline_m"]]
        ys += [p[1] for p in f["outline_m"]]
    put("zone", {"x0": L.gx(min(xs)), "x1": L.gx(max(xs)), "z0": L.gz(max(ys)), "z1": L.gz(min(ys))},
        "bounding box of every floor outline")
    for fid, z in FLOOR_Z.items():
        put("y_" + fid.lower(), int(round(z * 100)), "layout floors[%s].z_game_m" % fid)
    put("rail", int(round(RAIL_M * 100)), "layout vertical.atrium.game.railing_m")
    put("clear", int(round(L.floors["F5"]["clear_height_game_m"] * 100)), "layout floors.clear_height_game_m")

    # act 1
    put("climb_goal", L.game(GOAL_M[0], GOAL_M[1], FLOOR_Z["F5"]), "rule GOAL_M (F5 north reading room)")
    put("climb_star", L.game(CLIMB_STAR_M[0], CLIMB_STAR_M[1], FLOOR_Z["F5"] + CLIMB_STAR_M[2]), "rule CLIMB_STAR_M")
    gs = L.vertical["grand_stair"]["game"]["bottom_m"]
    put("stair_foot", L.game(gs[0], gs[1], FLOOR_Z["F2"]), "layout grand_stair.game.bottom_m (F2)")
    put("atrium", {"x0": L.gx(ax0), "x1": L.gx(ax1), "z0": L.gz(ay1), "z1": L.gz(ay0)}, "layout vertical.atrium.poly_m")
    lz = L.gz(aym)
    off = (LIFT_CLEAR_M + LIFT_HALF_M) * 100
    rail = int(round(RAIL_M * 100))
    put("lift_a", {"x": L.gx(ax1) - int(off), "z": lz, "bottom": int(FLOOR_Z["F3"] * 100) + rail,
                   "top": int(FLOOR_Z["F4"] * 100) + rail, "half": int(LIFT_HALF_M * 100)},
        "rule: east edge of the void - 1.7 m, railing top F3 -> F4")
    put("lift_b", {"x": L.gx(ax0) + int(off), "z": lz, "bottom": int(FLOOR_Z["F4"] * 100) + rail,
                   "top": int(FLOOR_Z["F5"] * 100) + rail, "half": int(LIFT_HALF_M * 100)},
        "rule: west edge of the void + 1.7 m, railing top F4 -> F5")
    put("board_a", (L.gx(ax1) + 120, int(FLOOR_Z["F3"] * 100), lz), "rule: F3 floor 1.2 m east of the void, lift A's line")
    put("board_b", (L.gx(ax0) - 110, int(FLOOR_Z["F4"] * 100), lz), "rule: F4 walkway 1.1 m west of the void, lift B's line")
    e1 = L.vertical["core"]["elevators"][0]["door_m"]
    put("shaft_door", L.game((e1[0][0] + e1[1][0]) / 2, e1[0][1] - SHAFT_FRONT_M, FLOOR_Z["F2"]),
        "layout core.elevators[1].door_m (F2), 1 m in front of it")
    doors = []
    for fid in ("F1", "F2", "F3", "F4"):
        y = int(FLOOR_Z[fid] * 100)
        for sid in ("stair_ne", "stair_sw"):
            a, b, _ = L.vertical[sid]["game"]["doors"][fid]
            doors.append({"x0": L.gx(a[0]), "z0": L.gz(a[1]), "x1": L.gx(b[0]), "z1": L.gz(b[1]), "y": y})
        a, b, _ = L.vertical["core"]["stair"]["door"]
        doors.append({"x0": L.gx(a[0]), "z0": L.gz(a[1]), "x1": L.gx(b[0]), "z1": L.gz(b[1]), "y": y})
        a, b = L.vertical["core"]["elevators"][1]["door_m"]
        doors.append({"x0": L.gx(a[0]), "z0": L.gz(a[1]), "x1": L.gx(b[0]), "z1": L.gz(b[1]), "y": y})
    put("stair_doors", doors, "layout vertical: NE / SW stair, core stair and elevator 2 doors of F1-F4")

    # act 2
    put("quiet_start", tuple(M["design_act2_quiet_floor"]["start"]["game_xyz"]), "layout missions act 2 start")
    put("quiet_star", L.game(QUIET_STAR_M[0], QUIET_STAR_M[1], FLOOR_Z["F5"] + QUIET_STAR_M[2]), "rule QUIET_STAR_M")
    books = []
    for name, (x, y), on in BOOKS:
        z = FLOOR_Z["F5"] + (L.prop("F5", on)["height_m"] if on else 0.0)
        X, Y, Z = L.game(x, y, z)
        books.append({"x": X, "y": Y, "z": Z, "name": name})
    put("books", books, "rule BOOKS (F5 floor or the top of the prop named)")
    for key, pts in PATROLS.items():
        put(key, [{"x": L.gx(x), "z": L.gz(y)} for x, y in pts], "rule PATROLS[%s]" % key)

    # act 3
    K = M["design_act3_group_study_room_booking"]["kiosks"]
    kiosks = []
    for i, kid in enumerate(("K1", "K2", "K3", "K4")):
        if kid == "K3":
            X, Y, Z = L.game(K3_MOVED_M[0], K3_MOVED_M[1], FLOOR_Z["F4"])
        else:
            X, Y, Z = K[kid]["game_xyz"]
        kiosks.append({"x": X, "y": Y, "z": Z, "yaw": KIOSK_YAW[i], "name": KIOSK_NAMES[i]})
    put("kiosks", kiosks, "layout missions act 3 kiosks K1, K2, K4; rule K3_MOVED_M")
    l129 = L.zone("F1", "L129")["poly_m"]
    l128 = L.zone("F1", "L128")["poly_m"]
    l130 = L.zone("F1", "L130")["poly_m"]
    dx = min(p[0] for p in l129)
    dy0, dy1 = max(p[1] for p in l130), min(p[1] for p in l128)
    put("room_door", {"x0": L.gx(dx), "z0": L.gz(dy0), "x1": L.gx(dx), "z1": L.gz(dy1), "y": int(FLOOR_Z["F1"] * 100)},
        "rule: L129's west face between L130's north wall and L128's south wall")
    st = M["design_act3_group_study_room_booking"]["star"]["pos_m"]
    put("room_star", L.game(st[0], st[1], FLOOR_Z["F1"] + ROOM_STAR_UP_M), "layout act 3 star pos_m, 0.8 m up")
    cx = sum(p[0] for p in l129) / len(l129)
    cy = sum(p[1] for p in l129) / len(l129)
    put("room_center", L.game(round(cx, 2), round(cy, 2), FLOOR_Z["F1"]), "L129 polygon centre (F1)")

    # marston_points.json overrides
    named = json_points(use_json)
    info["json"] = bool(named)
    for key, names in JSON_NAMES.items():
        for n in names:
            if n in named:
                put(key, tuple(int(v) for v in named[n]["game"]), "marston_points.json " + n)
                break
    return out, origin, info


# ------------------------------------------------------------------------------------------- Lua side
def lua_points():
    text = open(LUA).read()
    body = text[text.index("local function marston_points() return {"):]
    body = body[:body.index("\n} end\n")]
    body = "\n".join(re.sub(r"--.*$", "", line) for line in body.split("\n"))
    out = {}
    for m in re.finditer(r"^\s{4}([a-z_0-9]+)\s*=\s*(-?\d+)\s*,", body, re.M):
        out[m.group(1)] = int(m.group(2))
    for m in re.finditer(r"^\s{4}([a-z_0-9]+)\s*=\s*\{\s*x\s*=\s*(-?\d+),\s*y\s*=\s*(-?\d+),\s*z\s*=\s*(-?\d+)\s*\}", body, re.M):
        out[m.group(1)] = tuple(int(m.group(i)) for i in (2, 3, 4))
    for m in re.finditer(r"^\s{4}([a-z_0-9]+)\s*=\s*\{([^{}\n]*)\},", body, re.M):
        if m.group(1) in out:
            continue
        out[m.group(1)] = dict((k, int(v)) for k, v in re.findall(r"(\w+)\s*=\s*(-?\d+)", m.group(2)))
    for m in re.finditer(r"^\s{4}([a-z_0-9]+)\s*=\s*\{[ \t]*\n(.*?)^\s{4}\},", body, re.M | re.S):
        rows = []
        for row in re.findall(r"\{([^{}]*)\}", m.group(2)):
            kv = dict((k, int(v)) for k, v in re.findall(r"(\w+)\s*=\s*(-?\d+)", row))
            nm = re.search(r'name\s*=\s*"([^"]*)"', row)
            if nm:
                kv["name"] = nm.group(1)
            rows.append(kv)
        out[m.group(1)] = rows
    return out


def compare(src, lua):
    bad = 0
    for k, v in src.items():
        have = lua.get(k)
        if have is None:
            print("missing in MARSTON_POINTS: %s (source %s)" % (k, v))
            bad += 1
        elif isinstance(v, list):
            if not isinstance(have, list) or len(have) != len(v):
                print("%s: %s rows in MARSTON_POINTS, %d in the source" % (k, len(have) if isinstance(have, list) else "no", len(v)))
                bad += 1
                continue
            for i, (h, s) in enumerate(zip(have, v)):
                for key, sv in s.items():
                    hv = h.get(key)
                    if key == "name":
                        if hv != sv:
                            print("NAME %s[%d]: %r vs source %r" % (k, i + 1, hv, sv))
                            bad += 1
                    elif hv is None or abs(hv - sv) > TOL:
                        print("DRIFT %s[%d].%s: %s vs source %s" % (k, i + 1, key, hv, sv))
                        bad += 1
        elif isinstance(v, dict):
            for key, sv in v.items():
                hv = have.get(key) if isinstance(have, dict) else None
                if hv is None or abs(hv - sv) > TOL:
                    print("DRIFT %s.%s: %s vs source %s" % (k, key, hv, sv))
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


# ------------------------------------------------------------------------------------------- layout sanity
def floor_of_y(y):
    for fid, z in FLOOR_Z.items():
        if abs(y - z * 100) < 250:
            return fid
    return None


def layout_sanity(lua, info):
    L = info["layout"]
    bad = 0

    def m_of(X, Z):
        return (X / 100 + L.cx, -Z / 100 + L.cy)

    def standing(name, X, Y, Z, on_prop=None):
        nonlocal bad
        fid = floor_of_y(Y if on_prop is None else Y - int(round(L.prop(floor_of_y(Y - 200) or "F5", on_prop)["height_m"] * 100)))
        if fid is None:
            print("STAND %s: Y %d is no floor level" % (name, Y))
            bad += 1
            return
        f = L.floors[fid]
        p = m_of(X, Z)
        outdoor = [z for z in f["zones"] if z.get("enclosure") in ("parapet", "open") and z["type"] in ("terrace", "porch", "roof_deck")]
        if not pip(p, f["outline_m"]) and not any(pip(p, z["poly_m"]) for z in outdoor):
            print("STAND %s at map (%.2f, %.2f) %s: outside the floor" % (name, p[0], p[1], fid))
            bad += 1
        for z in f["zones"]:
            if not z.get("walkable", True) and pip(p, z["poly_m"]):
                print("STAND %s at map (%.2f, %.2f) %s: inside the non-walkable zone %s" % (name, p[0], p[1], fid, z["id"]))
                bad += 1
        for pr in f["props"]:
            if pr["id"] == on_prop:
                if not pip(p, rect_of(pr)):
                    print("STAND %s: not on its prop %s" % (name, on_prop))
                    bad += 1
                continue
            if pr["type"] in ("wall_sign",):
                continue
            if pip(p, rect_of(pr)):
                print("STAND %s at map (%.2f, %.2f) %s: inside the prop %s" % (name, p[0], p[1], fid, pr["id"]))
                bad += 1
        for c in f["columns_m"]:
            if max(abs(p[0] - c[0]), abs(p[1] - c[1])) < COLUMN_HALF_M + STAND_CLEAR_M:
                print("STAND %s: %.2f m from the column at %s" % (name, math.hypot(p[0] - c[0], p[1] - c[1]), c))
                bad += 1
        if fid != "F2" and pip(p, L.atrium()):
            print("STAND %s at map (%.2f, %.2f) %s: over the atrium void" % (name, p[0], p[1], fid))
            bad += 1

    for key in ("spawn", "climb_goal", "stair_foot", "board_a", "board_b", "shaft_door", "quiet_start", "room_center"):
        X, Y, Z = lua[key]
        standing(key, X, Y, Z)
    on = {b[0]: b[2] for b in BOOKS}
    for b in lua["books"]:
        standing("book " + b["name"], b["x"], b["y"], b["z"], on.get(b["name"]))
    # teleport spots (D-pad Down, a Shusher sending you back): the spot and the side-by-side ring round it, all on
    # walkable floor, in the same room as the spot (glass / walled rooms) and 0.3 m clear of that room's walls
    def room_of(fid, p):
        for z in L.floors[fid]["zones"]:
            if z.get("enclosure") in ("glass", "wall", "glass_partial") and pip(p, z["poly_m"]):
                return z
        return None

    def stand_ring(name, X, Y, Z):
        nonlocal bad
        fid = floor_of_y(Y)
        home = room_of(fid, m_of(X, Z))
        for dx, dz in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            px, pz = X + dx * SIDE_BY_SIDE_M * 100, Z + dz * SIDE_BY_SIDE_M * 100
            standing("%s (+%d,%d)" % (name, dx, dz), px, Y, pz)
            p = m_of(px, pz)
            room = room_of(fid, p)
            if room is not home:
                print("STAND %s (+%d,%d): lands in %s, not %s" % (name, dx, dz, room and room["id"], home and home["id"]))
                bad += 1
            for z in L.floors[fid]["zones"]:
                if z.get("enclosure") in ("glass", "wall", "glass_partial") and edge_dist(p, z["poly_m"]) < 0.3:
                    print("STAND %s (+%d,%d): %.2f m from the wall of %s" % (name, dx, dz, edge_dist(p, z["poly_m"]), z["id"]))
                    bad += 1
    stand_ring("act 2 start", *lua["quiet_start"])
    for i, k in enumerate(lua["kiosks"]):
        standing("kiosk %d" % (i + 1), k["x"], k["y"], k["z"])
        a = k.get("yaw", 0) / 65536 * 2 * math.pi
        stand_ring("kiosk %d stand" % (i + 1), k["x"] - math.sin(a) * KIOSK_STAND_M * 100, k["y"],
                   k["z"] - math.cos(a) * KIOSK_STAND_M * 100)
        # the kiosk is a 1 m box: keep 0.9 m round it clear of props and columns
        f = L.floors[floor_of_y(k["y"])]
        p = m_of(k["x"], k["z"])
        for pr in f["props"]:
            if poly_dist(p, rect_of(pr)) < 0.9:
                print("KIOSK %d: %.2f m from the prop %s" % (i + 1, poly_dist(p, rect_of(pr)), pr["id"]))
                bad += 1
    for key in ("climb_star", "quiet_star", "room_star"):
        X, Y, Z = lua[key]
        fid = floor_of_y(Y - 90)
        top = (FLOOR_Z[fid] * 100) + lua["clear"]
        if Y + STAR_HUMP + STAR_SIZE > top:
            print("STAR %s at y %d: its 4 m hump reaches %d over a %d ceiling" % (key, Y, Y + STAR_HUMP + STAR_SIZE, top))
            bad += 1
        standing(key + " (floor below)", X, int(FLOOR_Z[fid] * 100), Z)

    # Shusher patrols (floor 5)
    f5 = L.floors["F5"]
    for key, loop in PATROL_LOOP.items():
        pts = [m_of(r["x"], r["z"]) for r in lua[key]]
        worst = None
        for p in sample_polyline(pts, loop):
            if not pip(p, f5["outline_m"]) or edge_dist(p, f5["outline_m"]) < PATROL_WALL_M:
                worst = worst or "wall at map (%.2f, %.2f)" % p
            if poly_dist(p, L.atrium()) < PATROL_CLEAR_M:
                worst = worst or "atrium void at map (%.2f, %.2f)" % p
            for z in f5["zones"]:
                if not z.get("walkable", True) and poly_dist(p, z["poly_m"]) < PATROL_CLEAR_M:
                    worst = worst or "zone %s at map (%.2f, %.2f)" % (z["id"], p[0], p[1])
            for pr in f5["props"]:
                if poly_dist(p, rect_of(pr)) < PATROL_CLEAR_M:
                    worst = worst or "prop %s at map (%.2f, %.2f)" % (pr["id"], p[0], p[1])
            for c in f5["columns_m"]:
                if math.hypot(p[0] - c[0], p[1] - c[1]) < COLUMN_HALF_M + PATROL_CLEAR_M:
                    worst = worst or "column %s at map (%.2f, %.2f)" % (c, p[0], p[1])
            core = L.vertical["core"]["poly_m"]
            if poly_dist(p, core) < PATROL_WALL_M:
                worst = worst or "west core at map (%.2f, %.2f)" % p
        if worst:
            print("PATROL %s: too close to the %s" % (key, worst))
            bad += 1
    # the act 2 start: out of every patrol's hearing of a walking player and of its sight (5 m)
    sx, _, sz = lua["quiet_start"]
    sp = m_of(sx, sz)
    for key, loop in PATROL_LOOP.items():
        pts = [m_of(r["x"], r["z"]) for r in lua[key]]
        d = min(math.hypot(p[0] - sp[0], p[1] - sp[1]) for p in sample_polyline(pts, loop))
        if d < 5.0:
            print("PATROL %s passes %.1f m from the act 2 start (want >= 5 m)" % (key, d))
            bad += 1

    # act 1 lifts in the void
    atr = L.atrium()
    a = lua["atrium"]
    cols = L.vertical["atrium"]["game"]["free_columns"]
    for key in ("lift_a", "lift_b"):
        lf = lua[key]
        h = lf["half"]
        corners = [m_of(lf["x"] + sx * h, lf["z"] + sz * h) for sx in (-1, 1) for sz in (-1, 1)]
        for c in corners:
            if not pip(c, atr) or edge_dist(c, atr) < LIFT_VOID_CLEAR_M:
                print("LIFT %s: deck corner map (%.2f, %.2f) within %.1f m of the void's edge" % (key, c[0], c[1], LIFT_VOID_CLEAR_M))
                bad += 1
        for col in cols:
            px = min(max(col[0], min(c[0] for c in corners)), max(c[0] for c in corners))
            py = min(max(col[1], min(c[1] for c in corners)), max(c[1] for c in corners))
            if math.hypot(col[0] - px, col[1] - py) < COLUMN_HALF_M + LIFT_COLUMN_CLEAR_M:
                print("LIFT %s: %.2f m from the free column %s" % (key, math.hypot(col[0] - px, col[1] - py), col))
                bad += 1
        if lf["bottom"] - 51 <= 600:
            print("LIFT %s: its underside (%d) reaches floor 3's level (the grand stair)" % (key, lf["bottom"] - 51))
            bad += 1
    if lua["lift_a"]["top"] != lua["lift_b"]["bottom"]:
        print("LIFTS: lift A's top (%d) is not lift B's bottom (%d): one floor each" % (lua["lift_a"]["top"], lua["lift_b"]["bottom"]))
        bad += 1

    # act 1 barriers cover the doors
    want = sources(False)[0]["stair_doors"]
    for w in want:
        hit = False
        for b in lua["stair_doors"]:
            if b["y"] == w["y"] and abs(b["x0"] - w["x0"]) <= 5 and abs(b["z0"] - w["z0"]) <= 5 and abs(b["x1"] - w["x1"]) <= 5 \
                    and abs(b["z1"] - w["z1"]) <= 5:
                hit = True
        if not hit:
            print("BARRIER: no act 1 barrier for the door %s" % w)
            bad += 1

    # act 3 kiosk pairs
    stairs = []
    V = L.vertical
    for fid in FLOOR_Z:
        pass

    def door_at(sid, fid):
        if sid == "core":
            a, b, _ = V["core"]["stair"]["door"]
        elif sid == "elev_2":
            a, b = V["core"]["elevators"][1]["door_m"]
        else:
            d = V[sid]["game"]["doors"].get(fid)
            if d is None:
                return None
            a, b, _ = d
        return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)

    def path_m(ka, kb):
        fa, fb = floor_of_y(ka["y"]), floor_of_y(kb["y"])
        pa, pb = m_of(ka["x"], ka["z"]), m_of(kb["x"], kb["z"])
        ia, ib = list(FLOOR_Z).index(fa), list(FLOOR_Z).index(fb)
        if ia == ib:
            return math.hypot(pa[0] - pb[0], pa[1] - pb[1]), "same floor"
        best, via = None, None
        for sid in ("stair_ne", "stair_sw", "core", "elev_2"):
            da, db = door_at(sid, fa), door_at(sid, fb)
            if da is None or db is None:
                continue
            d = math.hypot(pa[0] - da[0], pa[1] - da[1]) + math.hypot(pb[0] - db[0], pb[1] - db[1]) + STAIR_M_PER_STOREY * abs(ia - ib)
            if best is None or d < best:
                best, via = d, sid
        if {fa, fb} == {"F2", "F3"}:
            gs = V["grand_stair"]["game"]
            bot, top = gs["bottom_m"], gs["top_m"]
            p2, p3 = (pa, pb) if fa == "F2" else (pb, pa)
            d = math.hypot(p2[0] - bot[0], p2[1] - bot[1]) + math.hypot(p3[0] - top[0], p3[1] - top[1]) + STAIR_M_PER_STOREY
            if d < best:
                best, via = d, "grand_stair"
        if {fa, fb} == {"F1", "F2"}:
            ch = V["book_chute"]["game"]
            p2, p1 = (pa, pb) if fa == "F2" else (pb, pa)
            d = math.hypot(p2[0] - ch["top_m"][0], p2[1] - ch["top_m"][1]) + math.hypot(p1[0] - ch["bottom_m"][0], p1[1] - ch["bottom_m"][1])
            if d < best:
                best, via = d, "book_chute"
        return best, via

    ks = lua["kiosks"]
    info["kiosk_paths"] = {}
    for n, lit in KIOSK_SETS.items():
        for i in lit:
            for j in lit:
                if i < j:
                    d, via = path_m(ks[i - 1], ks[j - 1])
                    info["kiosk_paths"][(i, j)] = (d, via)
                    fa, fb = floor_of_y(ks[i - 1]["y"]), floor_of_y(ks[j - 1]["y"])
                    apart = abs(list(FLOOR_Z).index(fa) - list(FLOOR_Z).index(fb))
                    if apart == 0 or (apart < 2 and d < MIN_KIOSK_PATH_M):
                        print("KIOSKS %d-%d (%d players): %.1f m via %s (want >= %.0f m, or two floors apart)"
                              % (i, j, n, d, via, MIN_KIOSK_PATH_M))
                        bad += 1

    # the study-room lock is on L129's door line, between its neighbours' walls
    rd = lua["room_door"]
    if rd["x0"] != rd["x1"] or abs(rd["z1"] - rd["z0"]) < 120:
        print("ROOM DOOR: %s is not a >= 1.2 m opening on L129's west face" % rd)
        bad += 1

    # s16
    def each(v, name):
        nonlocal bad
        if isinstance(v, dict):
            for k, x in v.items():
                each(x, name + "." + k)
        elif isinstance(v, (list, tuple)):
            for i, x in enumerate(v):
                each(x, "%s[%d]" % (name, i + 1))
        elif isinstance(v, int) and abs(v) > S16 and not name.endswith(".yaw"):
            print("S16 %s = %d" % (name, v))
            bad += 1
    each(lua, "MARSTON_POINTS")
    return bad


# ------------------------------------------------------------------------------------------- collision
class Collision:
    """Static collision of an exported area (COL_VERTEX / COL_TRI), SM64 surface rules."""

    def __init__(self, path):
        src = open(path).read()
        verts = [tuple(int(v) for v in m) for m in re.findall(r"COL_VERTEX\(\s*(-?\d+),\s*(-?\d+),\s*(-?\d+)\s*\)", src)]
        self.tris = []
        self.types = {}
        stype = None
        for m in re.finditer(r"COL_TRI_INIT\((\w+),|COL_TRI(?:_SPECIAL)?\(\s*(\d+),\s*(\d+),\s*(\d+)", src):
            if m.group(1) is not None:
                stype = m.group(1)
                continue
            a, b, c = (verts[int(m.group(i))] for i in (2, 3, 4))
            self.types[(a, b, c)] = stype
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

    def in_box(self, x0, x1, y0, y1, z0, z1):
        hits = []
        for t in self.tris:
            pts = list(t[:3]) + [tuple(sum(v[i] for v in t[:3]) / 3 for i in range(3))]
            for (x, y, z) in pts:
                if x0 < x < x1 and y0 < y < y1 and z0 < z < z1:
                    hits.append(t)
                    break
        return hits


def check_built(lua, bad):
    if not os.path.exists(COLLISION):
        print("check_marston_points: levels/ccm not built: collision checks skipped")
        return bad
    col = Collision(COLLISION)
    n = 0
    pts = [(k, lua[k]) for k in ("spawn", "climb_goal", "stair_foot", "board_a", "board_b", "shaft_door", "quiet_start",
                                 "room_center")]
    pts += [("book " + b["name"], (b["x"], b["y"], b["z"])) for b in lua["books"]]
    pts += [("kiosk %d" % (i + 1), (k["x"], k["y"], k["z"])) for i, k in enumerate(lua["kiosks"])]
    for name, (x, y, z) in pts:
        n += 1
        h = col.find_floor(x, y + 200, z)
        if h is None or abs(h - y) > TOL:
            print("NO FLOOR %s at (%d, %d, %d): found %s" % (name, x, y, z, "none" if h is None else "%.0f" % h))
            bad += 1
    for key in ("lift_a", "lift_b"):
        lf = lua[key]
        n += 1
        h = lf["half"]
        hits = col.in_box(lf["x"] - h, lf["x"] + h, lf["bottom"] - 51, lf["top"] + 200, lf["z"] - h, lf["z"] + h)
        if hits:
            print("LIFT %s: %d static triangle(s) in its travel box, e.g. %s" % (key, len(hits), hits[0][:3]))
            bad += 1
    # the act 1 book cart (uf_marston_missions.lua sgl_marston_cart_of: 0.5 m from each lift, a 2.2 m deck at lift A's
    # top): nothing static in its travel box (deck + 1.6 m for a standing rider; the chandelier ring hangs above)
    la, lb, ch = lua["lift_a"], lua["lift_b"], 110
    sgn = -1 if lb["x"] < la["x"] else 1
    east, west = la["x"] + sgn * (la["half"] + 50 + ch), lb["x"] - sgn * (lb["half"] + 50 + ch)
    n += 1
    hits = col.in_box(min(east, west) - ch, max(east, west) + ch, la["top"] - 51, la["top"] + 160, la["z"] - ch, la["z"] + ch)
    if hits:
        print("BOOK CART: %d static triangle(s) in its travel box, e.g. %s" % (len(hits), hits[0][:3]))
        bad += 1
    for key in ("climb_star", "quiet_star", "room_star"):
        n += 1
        x, y, z = lua[key]
        hits = col.surfaces_in_column(x, z, y - 50, y + STAR_HUMP + STAR_SIZE, 60)
        if hits:
            print("STAR %s at (%d, %d, %d): a static floor / ceiling in its column at y %s (the spawn humps 4 m)"
                  % (key, x, y, z, sorted(set(int(h) for h in hits))[:5]))
            bad += 1
    print("check_marston_points: %d collision checks on %s (%d triangles)" % (n, os.path.relpath(COLLISION, ROOT), len(col.tris)))
    return check_airborne(col, bad)


# ------------------------------------------------------------------------------------------- airborne rules
HATCH = (-1140, -1020, -2250, -2090)   # the F2 book-chute hatch (game X / Z), F2 floor Y 0
SLAB_TOPS = (0, 600, 1200, 1800, 2400)
THIN_UNITS = 12                        # 48 u/f / 4 quarter steps
CELL = 256


class Air:
    """Spatial-hashed SM64 surfaces for the airborne checks (vanilla air wall push, find_floor / find_ceil)."""

    def __init__(self, col):
        self.floors, self.ceils, self.walls = {}, {}, {}
        self.wall_list = []
        for t in col.tris:
            a, b, c, nx, ny, nz, oo = t
            ys = (a[1], b[1], c[1])
            rec = {"v": (a, b, c), "n": (nx, ny, nz), "oo": oo, "lo": min(ys) - 5, "hi": max(ys) + 5,
                   "xproj": abs(nx) > 0.707}
            if ny > 0.01:
                grid, pad = self.floors, 0
            elif ny < -0.01:
                grid, pad = self.ceils, 0
            else:
                grid, pad = self.walls, 220
                self.wall_list.append(rec)
            xs, zs = (a[0], b[0], c[0]), (a[2], b[2], c[2])
            for i in range(int((min(xs) - pad) // CELL), int((max(xs) + pad) // CELL) + 1):
                for j in range(int((min(zs) - pad) // CELL), int((max(zs) + pad) // CELL) + 1):
                    grid.setdefault((i, j), []).append(rec)

    @staticmethod
    def _cell(x, z):
        return (int(x // CELL), int(z // CELL))

    def find_floor(self, x, y, z):
        x, y, z = int(x), int(y), int(z)
        best, bs = -11000.0, None
        for s in self.floors.get(self._cell(x, z), ()):
            (x1, _, z1), (x2, _, z2), (x3, _, z3) = s["v"]
            if (z1 - z) * (x2 - x1) - (x1 - x) * (z2 - z1) < 0 or (z2 - z) * (x3 - x2) - (x2 - x) * (z3 - z2) < 0 \
                    or (z3 - z) * (x1 - x3) - (x3 - x) * (z1 - z3) < 0:
                continue
            nx, ny, nz = s["n"]
            h = -(x * nx + nz * z + s["oo"]) / ny
            if h >= best and y - (h - 78.0) >= 0:
                best, bs = h, s
        return best, bs

    def find_ceil(self, x, y, z):
        x, y, z = int(x), int(y), int(z)
        best = 20000.0
        for s in self.ceils.get(self._cell(x, z), ()):
            (x1, _, z1), (x2, _, z2), (x3, _, z3) = s["v"]
            if (z1 - z) * (x2 - x1) - (x1 - x) * (z2 - z1) > 0 or (z2 - z) * (x3 - x2) - (x2 - x) * (z3 - z2) > 0 \
                    or (z3 - z) * (x1 - x3) - (x3 - x) * (z1 - z3) > 0:
                continue
            nx, ny, nz = s["n"]
            h = -(x * nx + nz * z + s["oo"]) / ny
            if h <= best and y - (h + 78.0) <= 0:
                best = h
        return best

    def walls_air(self, pos, off_y, radius=50.0):
        """vanilla find_wall_collisions (airborne in coopdx v1.5.1): two-sided, pushes to the front side"""
        x, z, y = pos[0], pos[2], pos[1] + off_y
        dx = dz = 0.0
        hit = False
        for s in self.walls.get(self._cell(x, z), ()):
            if y < s["lo"] or y > s["hi"]:
                continue
            nx, ny, nz = s["n"]
            offset = nx * x + ny * y + nz * z + s["oo"]
            if offset < -radius or offset > radius:
                continue
            (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = s["v"]
            if s["xproj"]:
                w1, w2, w3, p, sgn = -z1, -z2, -z3, -z, nx > 0
            else:
                w1, w2, w3, p, sgn = x1, x2, x3, x, nz > 0
            e = ((y1 - y) * (w2 - w1) - (w1 - p) * (y2 - y1), (y2 - y) * (w3 - w2) - (w2 - p) * (y3 - y2),
                 (y3 - y) * (w1 - w3) - (w3 - p) * (y1 - y3))
            if (sgn and max(e) > 0) or (not sgn and min(e) < 0):
                continue
            dx += nx * (radius - offset)
            dz += nz * (radius - offset)
            hit = True
        pos[0] += dx
        pos[2] += dz
        return hit

    def fall(self, pos, vel, frames=90):
        """ACT_FREEFALL-like air steps (gravity 4, terminal -75) -> landing (pos, floor) or (pos, None)"""
        pos, vel = list(pos), list(vel)
        floor_h, _ = self.find_floor(pos[0], pos[1], pos[2])
        for _ in range(frames):
            vel[1] = max(vel[1] - 4.0, -75.0)
            for _q in range(4):
                nxt = [pos[i] + vel[i] / 4.0 for i in range(3)]
                self.walls_air(nxt, 150.0)
                self.walls_air(nxt, 30.0)
                fh, fl = self.find_floor(nxt[0], nxt[1], nxt[2])
                ch = self.find_ceil(nxt[0], nxt[1] + 80, nxt[2])
                if fl is None:
                    if nxt[1] <= floor_h:
                        return pos, None
                    pos[1] = nxt[1]
                    vel[0] = vel[2] = 0.0
                    break
                if nxt[1] <= fh:
                    if ch - fh > 160:
                        pos = [nxt[0], fh, nxt[2]]
                    return pos, fl
                if nxt[1] + 160 > ch:
                    if vel[1] >= 0:
                        vel[1] = 0.0
                        break
                    pos[1] = nxt[1]
                    vel[0] = vel[2] = 0.0
                    break
                pos, floor_h = nxt, fh
        return pos, None

    def is_slab(self, x, z, top):
        fh, _ = self.find_floor(x, top + 1, z)
        return abs(fh - top) < 1 and abs(self.find_ceil(x, top - 59, z) - (top - 60)) < 1

    def ray_back(self, x, y, z, dx, dz, maxd=300.0):
        """the first wall a horizontal ray meets is seen from behind (the ray starts inside a solid)"""
        best = None
        for s in self.walls.get(self._cell(x, z), []) + self.walls.get(self._cell(x + dx * maxd, z + dz * maxd), []):
            if y < s["lo"] + 5 or y > s["hi"] - 5:
                continue
            nx, ny, nz = s["n"]
            den = nx * dx + nz * dz
            if abs(den) < 1e-6:
                continue
            d = -(nx * x + ny * y + nz * z + s["oo"]) / den
            if d <= 0 or d > maxd or (best is not None and d >= best[0]):
                continue
            hx, hz = x + dx * d, z + dz * d
            tx, tz = -nz, nx
            pts = [(tx * v[0] + tz * v[2], v[1]) for v in s["v"]]
            q = (tx * hx + tz * hz, y)
            cr = [(pts[(k + 1) % 3][0] - pts[k][0]) * (q[1] - pts[k][1]) - (pts[(k + 1) % 3][1] - pts[k][1]) * (q[0] - pts[k][0])
                  for k in range(3)]
            if min(cr) < 0 < max(cr):
                continue
            best = (d, den > 0)
        return best is not None and best[1]

    def open_at(self, x, y, z):
        fh, fl = self.find_floor(x, y + 20, z)
        if fl is None or y - fh > 120:
            return False
        return sum(self.ray_back(x, y + 50, z, dx, dz) for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))) < 2


def check_airborne(col, bad):
    air = Air(col)
    # a. slab-edge faces face into their hole
    inverted, edges = [], 0
    for s in air.wall_list:
        (a, b, c) = s["v"]
        ys = sorted({a[1], b[1], c[1]})
        if len(ys) != 2 or ys[1] - ys[0] != 60 or ys[1] not in SLAB_TOPS:
            continue
        cx, cz = (a[0] + b[0] + c[0]) / 3, (a[2] + b[2] + c[2]) / 3
        nx, _, nz = s["n"]
        front, back = air.is_slab(cx + nx * 10, cz + nz * 10, ys[1]), air.is_slab(cx - nx * 10, cz - nz * 10, ys[1])
        if back and not front:
            edges += 1
        elif front and not back:
            inverted.append((int(cx), ys[1], int(cz)))
    if inverted:
        print("SLAB EDGE %d face(s) face into their slab instead of the hole (an airborne player is pushed back onto the "
              "floor), e.g. %s" % (len(inverted), inverted[:4]))
        bad += 1
    # b. stepping off the chute hatch's rim lands on the slide
    x0, x1, z0, z1 = HATCH
    trials, missed = 0, []
    for side in ("n", "s", "e", "w"):
        for f in (0.2, 0.5, 0.8):
            if side in ("n", "s"):
                x, z = x0 + (x1 - x0) * f, (z0 + 1 if side == "n" else z1 - 1)
                ux, uz = 0.0, (1.0 if side == "n" else -1.0)
            else:
                x, z = (x1 - 1 if side == "e" else x0 + 1), z0 + (z1 - z0) * f
                ux, uz = (-1.0 if side == "e" else 1.0), 0.0
            for sp in (6.0, 16.0, 32.0):
                trials += 1
                pos, fl = air.fall((x, 0.0, z), (ux * sp, 0.0, uz * sp))
                if fl is None or fl["v"] is None or col_type_of(col, fl) != "SURFACE_SLIPPERY":
                    missed.append((side, f, sp, [int(v) for v in pos]))
    if missed:
        print("CHUTE HATCH %d of %d step-offs do not land on the slide, e.g. %s" % (len(missed), trials, missed[:3]))
        bad += 1
    # c. thin walls between open spaces
    by_n = {}
    for s in air.wall_list:
        by_n.setdefault((round(s["n"][0], 3), round(s["n"][2], 3)), []).append(s)
    thin = []
    for s in air.wall_list:
        a = s["v"]
        ya = [v[1] for v in a]
        if max(ya) - min(ya) < 200:
            continue
        nx, _, nz = s["n"]
        tx, tz = -nz, nx
        la = [tx * v[0] + tz * v[2] for v in a]
        for o in by_n.get((round(-nx, 3) + 0.0, round(-nz, 3) + 0.0), ()):
            sep = nx * (a[0][0] - o["v"][0][0]) + nz * (a[0][2] - o["v"][0][2])
            if not 0 < sep < THIN_UNITS:
                continue
            yb = [v[1] for v in o["v"]]
            y0, y1 = max(min(ya), min(yb)), min(max(ya), max(yb))
            lb = [tx * v[0] + tz * v[2] for v in o["v"]]
            l0, l1 = max(min(la), min(lb)), min(max(la), max(lb))
            if y1 - y0 < 40 or l1 - l0 < 20:
                continue
            base = tx * a[0][0] + tz * a[0][2]
            cx, cz = a[0][0] + tx * ((l0 + l1) / 2 - base), a[0][2] + tz * ((l0 + l1) / 2 - base)
            feet = max(y0 - 25, air.find_floor(cx + nx * 60, y0 + 30, cz + nz * 60)[0])
            if feet + 30 > y1 + 5:
                continue
            if air.open_at(cx + nx * 60, feet, cz + nz * 60) and air.open_at(cx - nx * (sep + 60), feet, cz - nz * (sep + 60)):
                thin.append((int(cx), int(feet), int(cz), round(sep)))
                break
    if thin:
        print("THIN WALL %d wall face(s) under %d units thick between two open spaces (an airborne player is thrown "
              "through), e.g. %s" % (len(thin), THIN_UNITS, thin[:4]))
        bad += 1
    print("check_marston_points: airborne checks: %d slab-edge faces into their holes, %d chute-hatch step-offs on the "
          "slide, %d thin walls" % (edges, trials - len(missed), len(thin)))
    return bad


def col_type_of(col, rec):
    return col.types.get(rec["v"])


def fmt_lua(src):
    def row(d):
        parts = []
        for k, v in d.items():
            parts.append('%s = "%s"' % (k, v) if isinstance(v, str) else "%s = %d" % (k, v))
        return "{ " + ", ".join(parts) + " }"
    lines = []
    for k, v in src.items():
        if isinstance(v, list):
            lines.append("    %s = {" % k)
            for r in v:
                lines.append("        %s," % row(r))
            lines.append("    },")
        elif isinstance(v, dict):
            lines.append("    %s = %s," % (k, row(v)))
        elif isinstance(v, int):
            lines.append("    %s = %d," % (k, v))
        else:
            lines.append("    %s = { x = %d, y = %d, z = %d }," % (k, v[0], v[1], v[2]))
    return "\n".join(lines)


def main():
    src, origin, info = sources("--layout" not in sys.argv)
    where = ("data/uf/marston_points.json + " if info["json"] else "") + "data/uf/marston_layout.json"
    if "--print" in sys.argv:
        print(fmt_lua(src))
        for k, v in origin.items():
            print("--   %-14s <- %s" % (k, v))
        return 0
    lua = lua_points()
    bad = compare(src, lua)
    bad += layout_sanity(lua, info)
    bad = check_built(lua, bad)
    n = sum(len(v) if isinstance(v, (list, dict)) else 1 for v in src.values())
    if bad:
        print("check_marston_points: %d finding(s) (MARSTON_POINTS vs %s)" % (bad, where))
        return 1
    paths = ", ".join("K%d-K%d %.0f m" % (i, j, d) for (i, j), (d, _) in sorted(info.get("kiosk_paths", {}).items()))
    print("check_marston_points: OK (%d values of MARSTON_POINTS match %s; layout checks passed; kiosk paths %s)"
          % (n, where, paths))
    return 0


if __name__ == "__main__":
    sys.exit(main())
