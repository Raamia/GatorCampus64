"""Check (or print) the REITZ_POINTS table of mods/sgl64/wf_reitz_missions.lua against its sources and the
built level.

1. Source points (drift > 0.5 m fails), in order of preference:
   a. data/uf/reitz_points.json (schema sgl64.reitz_points/1, written by tools/campus/build_stage.py
      reitz_eng from the BUILT collision; data/uf/reitz_eng_points.json is accepted too): named points
      {"name": ..., "game": [X, floor Y, Z]} anywhere in the file, the act boxes and the token list.
   b. without the JSON: the landmark modules (tools/campus/landmarks/reitz_*.py LANDMARKS spots / markers,
      map metres, z = metres above grade) through the stages.json transform of the reitz_eng window:
      X = (x - cx) * 100, Y = z * 100, Z = -(y - cy) * 100. Tokens off the modules are skipped then.
   Derived values are always recomputed: console_2 (console_1 mirrored across the atrium centre), crane_z
   (ledge north edge - platform half depth 153 - 20) and gate_y (reitz_malachowsky.py floor levels).
2. The built level (mods/sgl64/levels/wf/area_1/collision.inc.c, when it exists), with SM64's find_floor
   rule (floors = normal.y > 0.01; a floor counts up to 78 units above the probe):
   - every floor anchor (climb points, tokens, consoles, the star ledge, the lift track foot, the star
     spots' floors) has a floor within 0.5 m of its Y when probed from 2 m above, as the missions' own
     geometry probes do;
   - the two crane lanes of act 3 (the platform's sweep plus a rider's height) and the two operator
     consoles (2 m around the switch) are clear of static collision (apart from the atrium floor and the
     star ledge's lip);
   - the act 1 window-washer lift's travel is clear, and its deck at the top is within 0.3 m of the
     parapet floor (step across).
Usage (from anywhere):
  tools/.venv/bin/python -I tools/luatest/check_reitz_points.py          check, exit 1 on any finding
  tools/.venv/bin/python -I tools/luatest/check_reitz_points.py --print  print the source values
  ... --module   compare with the landmark modules even when the JSON exists
"""
import json
import math
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
LUA = os.path.join(ROOT, "mods", "sgl64", "wf_reitz_missions.lua")
COLLISION = os.path.join(ROOT, "mods", "sgl64", "levels", "wf", "area_1", "collision.inc.c")
TOL = 50            # game units (0.5 m)
PLAT_HALF_X, PLAT_TOP, PLAT_BOTTOM, PLAT_HALF_Z = 256, 26, 25, 153
RIDER_H = 186       # deck top + Mario's height (1.6 m) + a little
LIFT_HALF_X, LIFT_HALF_Z = 120, 160     # window-washer lift deck (wf_reitz_missions.lua: 1.2 x 1.6 m half sizes)


# ------------------------------------------------------------------------------------------- Lua side
def lua_points():
    text = open(LUA).read()
    body = text[text.index("REITZ_POINTS = {"):]
    body = body[:body.index("\n}\n")]
    out = {}
    for m in re.finditer(r"^\s{4}([a-z_0-9]+)\s*=\s*\{\s*x\s*=\s*(-?\d+),\s*y\s*=\s*(-?\d+),\s*z\s*=\s*(-?\d+)\s*\}",
                         body, re.M):
        out[m.group(1)] = tuple(int(m.group(i)) for i in (2, 3, 4))
    for m in re.finditer(r"^\s{4}([a-z_0-9]+)\s*=\s*\{\s*(x0\s*=.*?)\}", body, re.M):
        out[m.group(1)] = {k: int(v) for k, v in re.findall(r"(\w+)\s*=\s*(-?\d+)", m.group(2))}
    toks = re.findall(r"\{\s*x\s*=\s*(-?\d+),\s*y\s*=\s*(-?\d+),\s*z\s*=\s*(-?\d+),\s*name\s*=\s*\"([^\"]+)\"", body)
    out["tokens"] = [(int(x), int(y), int(z), n) for x, y, z, n in toks]
    m = re.search(r"crane_z\s*=\s*(-?\d+)", body)
    out["crane_z"] = int(m.group(1)) if m else None
    m = re.search(r"gate_y\s*=\s*\{([^}]*)\}", body)
    out["gate_y"] = [int(v) for v in re.findall(r"-?\d+", m.group(1))] if m else []
    return out


# ------------------------------------------------------------------------------------------- sources
# REITZ_POINTS name -> reitz_points.json point name
JSON_NAMES = {
    "roof_goal": "rooftop_goal_penthouse",
    "roof_star": "rooftop_star_target",
    "climb_start": "rooftop_start_ravine_terrace",
    "climb_awning": "rooftop_climb_05",
    "ballroom_roof": "rooftop_climb_06",
    "podium_roof": "rooftop_podium_west",
    "tower_roof": "rooftop_tower_roof_center",
    "lift_bottom": "rooftop_lift_bottom",
    "lift_top": "rooftop_lift_top",
    "token_star": "token_star_north_lawn",
    "ledge_star": "robotics_star_ledge",
    "robotics_star": "robotics_star_target",
    "atrium_floor": "robotics_atrium_center",
    "console_1": "robotics_console",
}
# points that are not standing spots (no floor exactly at Y): skipped by the floor probe
AIR = {"roof_star", "robotics_star", "lift_top"}


def g_of(v):
    return tuple(int(round(c)) for c in v)


def json_path():
    for name in ("reitz_points.json", "reitz_eng_points.json"):
        p = os.path.join(ROOT, "data", "uf", name)
        if os.path.exists(p):
            return p
    return None


def json_points(jpath):
    data = json.load(open(jpath))
    named = {}

    def walk(o):
        if isinstance(o, dict):
            if isinstance(o.get("name"), str) and isinstance(o.get("game"), list) and len(o["game"]) == 3:
                named.setdefault(o["name"], g_of(o["game"]))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(data)
    out = {}
    for lua_name, jname in JSON_NAMES.items():
        if jname not in named:
            raise SystemExit("%s has no point %r (for REITZ_POINTS.%s)" % (os.path.basename(jpath), jname, lua_name))
        out[lua_name] = named[jname]
    a1, a2 = data["act1_rooftop"], data["act2_robotics_lab"]
    z = a1["climb_zone"]
    out["roof_zone"] = {"x0": z["x0"], "x1": z["x1"], "z0": z["z0"], "z1": z["z1"]}
    b = a2["atrium_box"]
    out["atrium"] = {"x0": b["x0"], "x1": b["x1"], "z0": b["z0"], "z1": b["z1"], "y": b["y0"], "ceil": b["y1"]}
    b = a2["star_ledge_box"]
    out["ledge"] = {"x0": b["x0"], "x1": b["x1"], "z0": b["z0"], "z1": b["z1"], "y": b["y0"]}
    out["tokens"] = []
    for t in data["act5_meal_swipe_tokens"]["red_coins"]:
        name = t["name"].replace("token_", "").replace("_", " ").upper()
        out["tokens"].append(g_of(t["game"]) + (name,))
    out["_stars"] = data.get("stars", [])
    return out


def stage_center():
    stages = json.load(open(os.path.join(ROOT, "data", "uf", "stages.json")))
    return [s for s in stages["stages"] if s["key"] == "reitz_eng"][0]["center_m"]


def modules():
    sys.path.insert(0, os.path.join(ROOT, "tools", "campus"))
    from landmarks import reitz_malachowsky as M, reitz_reitz_union as R, reitz_weil_eng_clocktower as W
    by = {}
    for mod in (M, R, W):
        for L in mod.LANDMARKS:
            by[L["slug"]] = L
    return by


def module_points():
    cx, cy = stage_center()
    L = modules()

    def g(p):
        return (round((p[0] - cx) * 100), round(p[2] * 100), round(-(p[1] - cy) * 100))

    ru, ma = L["reitz_union"]["spots"], L["malachowsky_hall"]
    out = {
        "roof_goal": g(ru["roof_star"]),
        "roof_star": g((ru["roof_star"][0], ru["roof_star"][1], ru["roof_star"][2] + 1.2)),
        "climb_start": g(ru["ravine_terrace_1"]),
        "climb_awning": g(ru["awning_3"]),
        "ballroom_roof": g(ru["ballroom_roof"]),
        "podium_roof": g(ru["podium_roof_west"]),
        "tower_roof": g(ru["tower_roof_center"]),
        "lift_bottom": g(ru["window_washer_lift_bottom"]),
        "lift_top": g(ru["window_washer_lift_top"]),
        "ledge_star": g(ma["spots"]["star_ledge"]),
        "robotics_star": g((ma["spots"]["star_ledge"][0], ma["spots"]["star_ledge"][1], ma["spots"]["star_ledge"][2] + 1.2)),
        "atrium_floor": g(ma["spots"]["atrium_floor"]),
        "console_1": g(ma["spots"]["atrium_console"]),
    }
    ab, lb = ma["markers"]["atrium_box_m"], ma["markers"]["star_ledge_m"]

    def box(bx, y0, extra):
        xs = [round((x - cx) * 100) for x in bx["x"]]
        zs = [round(-(y - cy) * 100) for y in bx["y"]]
        d = {"x0": min(xs), "x1": max(xs), "z0": min(zs), "z1": max(zs), "y": round(y0 * 100)}
        d.update(extra)
        return d
    out["atrium"] = box(ab, ab["z"][0], {"ceil": round(ab["z"][1] * 100)})
    out["ledge"] = box(lb, lb["z"], {})
    # tokens that sit on module geometry (the rest are measured by the stage build only); Weil's and
    # Malachowsky's are on their climb routes (stage_points.reitz_token_spots: the last ridge point of the
    # Weil roof run, the first glass box at 12 m)
    wroute = L["weil_hall"].get("climb_route_m", [])
    ridge = [p for p in wroute[:-1] if len(p) > 2 and p[2] >= 23.9]
    box = next((p for p in ma.get("climb_route_m", []) if len(p) > 2 and p[2] >= 11.9), None)
    out["_tokens_partial"] = {
        "ENGINEERING PLAZA SCULPTURE": g(L["engineering_plaza"]["spots"]["sculpture_top"]),
        "LIBERTY POND FOUNTAIN": g(L["reitz_amphitheater"]["spots"]["liberty_pond_fountain"]),
    }
    if ridge:
        out["_tokens_partial"]["WEIL ROOF RIDGE"] = g(ridge[-1])
    if box:
        out["_tokens_partial"]["MALACHOWSKY GLASS STAIR"] = g(box)
    return out


def derived(src, lua):
    out = {}
    a = src.get("atrium") or lua.get("atrium")
    c1 = src.get("console_1") or lua.get("console_1")
    if a and c1:
        out["console_2"] = (a["x0"] + a["x1"] - c1[0], c1[1], c1[2])
    led = src.get("ledge") or lua.get("ledge")
    if led:
        out["crane_z"] = led["z0"] - PLAT_HALF_Z - 20
    try:
        floors = modules()["malachowsky_hall"]["markers"]["levels_m"]["floors"]
        out["gate_y"] = [round(f * 100) for f in floors[:5]]
    except Exception as e:  # noqa: BLE001
        print("note: gate_y not checked (%s)" % e)
    return out


# ------------------------------------------------------------------------------------------- collision
class Collision:
    """Static collision of an exported area (COL_VERTEX / COL_TRI), SM64 surface rules."""

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
            oo = -(nx * x1 + ny * y1 + nz * z1)
            self.tris.append((a, b, c, nx, ny, nz, oo))
        self.floors = [t for t in self.tris if t[4] > 0.01]

    def find_floor(self, x, y, z):
        """Highest floor at (x, z) whose height is at most y + 78 (SM64), or None."""
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

    def in_box(self, x0, x1, y0, y1, z0, z1, skip=None):
        """Triangles whose bounding box overlaps the box (minus those `skip` accepts)."""
        hits = []
        for t in self.tris:
            xs, ys, zs = [v[0] for v in t[:3]], [v[1] for v in t[:3]], [v[2] for v in t[:3]]
            if max(xs) <= x0 or min(xs) >= x1 or max(ys) <= y0 or min(ys) >= y1 or max(zs) <= z0 or min(zs) >= z1:
                continue
            if skip is not None and skip(t, xs, ys, zs):
                continue
            hits.append(t)
        return hits


def check_built(lua, bad):
    if not os.path.exists(COLLISION):
        print("check_reitz_points: levels/wf not built: collision checks skipped")
        return bad
    col = Collision(COLLISION)
    n = 0
    floor_pts = [(k, v) for k, v in lua.items() if isinstance(v, tuple) and len(v) == 3 and k not in AIR]
    floor_pts += [("token %s" % t[3], t[:3]) for t in lua["tokens"]]
    for name, (x, y, z) in floor_pts:
        n += 1
        h = col.find_floor(x, y + 200, z)
        if h is None or abs(h - y) > TOL:
            print("NO FLOOR %s at (%d, %d, %d): found %s" % (name, x, y, z, "none" if h is None else "%.0f" % h))
            bad += 1
    # act 3: the crane lanes and the consoles are clear
    a, led, cz = lua["atrium"], lua["ledge"], lua["crane_z"]
    mid = (a["x0"] + a["x1"]) // 2
    lanes = [(a["x0"], mid), (mid, a["x1"])]
    lip = lambda t, xs, ys, zs: min(zs) >= led["z0"] - 1 and min(ys) >= led["y"] - 70       # the ledge itself
    flat = lambda t, xs, ys, zs: max(ys) <= a["y"] + 1                                      # the atrium floor
    for k, (x0, x1) in enumerate(lanes, 1):
        hits = col.in_box(x0 + 20, x1 - 20, a["y"] + 1, led["y"] + RIDER_H, cz - PLAT_HALF_Z - 40, cz + PLAT_HALF_Z + 40,
                          lambda t, xs, ys, zs: lip(t, xs, ys, zs) or flat(t, xs, ys, zs))
        n += 1
        if hits:
            print("LANE %d of the robotics cranes crosses %d static triangle(s), e.g. %s" % (k, len(hits), hits[0][:3]))
            bad += 1
    for name in ("console_1", "console_2"):
        x, y, z = lua[name]
        hits = col.in_box(x - 200, x + 200, y + 1, y + 300, z - 200, z + 200, flat)
        n += 1
        if hits:
            print("CONSOLE %s is not clear: %d static triangle(s) within 2 m, e.g. %s" % (name, len(hits), hits[0][:3]))
            bad += 1
    # act 1: the window-washer lift's travel (deck 2.4 x 3.2 m from the podium roof to the parapet top, plus a
    # rider) is clear of static collision, and at the top the parapet floor starts within 0.3 m east of the
    # deck (a step across, no jump; technical review)
    lb, lt = lua.get("lift_bottom"), lua.get("lift_top")
    if lb and lt:
        lx, lz = lt[0], lt[2]
        hits = col.in_box(lx - LIFT_HALF_X, lx + LIFT_HALF_X, lb[1] + 1, lt[1] + RIDER_H, lz - LIFT_HALF_Z, lz + LIFT_HALF_Z)
        n += 1
        if hits:
            print("LIFT track crosses %d static triangle(s), e.g. %s" % (len(hits), hits[0][:3]))
            bad += 1
        n += 1
        h = col.find_floor(lx + LIFT_HALF_X + 30, lt[1] + 10, lz)
        if h is None or abs(h - lt[1]) > 5:
            print("LIFT top: no parapet floor (%d) within 0.3 m east of the deck (found %s)" % (lt[1], h))
            bad += 1
    # the crane deck at its top meets the ledge: deck top = ledge floor, 0.2 m short of its edge
    h = col.find_floor(mid // 2 + a["x0"] // 2, led["y"] + 200, led["z0"] + 50)
    n += 1
    if h is None or abs(h - led["y"]) > 5:
        print("STAR LEDGE floor not at %d next to the crane lane (found %s)" % (led["y"], h))
        bad += 1
    print("check_reitz_points: %d collision checks on %s (%d triangles)" % (n, os.path.relpath(COLLISION, ROOT), len(col.tris)))
    return bad


# ------------------------------------------------------------------------------------------- main
def main():
    jpath = json_path()
    use_json = jpath is not None and "--module" not in sys.argv
    src = json_points(jpath) if use_json else module_points()
    where = os.path.relpath(jpath, ROOT) if use_json else "tools/campus/landmarks/reitz_*.py"
    lua = lua_points()
    der = derived(src, lua)
    if "--print" in sys.argv:
        for k, v in src.items():
            if not k.startswith("_"):
                print("    %s = %s," % (k, v))
        for k, v in der.items():
            print("    %s = %s,   -- derived" % (k, v))
        return 0
    bad = 0
    n = 0
    for k, v in src.items():
        if k.startswith("_"):
            continue
        n += 1
        have = lua.get(k)
        if have is None:
            print("missing in REITZ_POINTS: %s (source %s)" % (k, v))
            bad += 1
        elif k == "tokens":
            if len(have) != len(v):
                print("TOKENS: %d in REITZ_POINTS, %d in the source" % (len(have), len(v)))
                bad += 1
            for i, (h, s) in enumerate(zip(have, v)):
                d = max(abs(a - b) for a, b in zip(h[:3], s[:3]))
                if d > TOL or h[3] != s[3]:
                    print("DRIFT token %d: %s vs source %s (%.1f m)" % (i + 1, h, s, d / 100))
                    bad += 1
        elif isinstance(v, dict):
            for kk, vv in v.items():
                if abs(have.get(kk, 1e9) - vv) > TOL:
                    print("DRIFT %s.%s: %s vs source %s" % (k, kk, have.get(kk), vv))
                    bad += 1
        else:
            d = max(abs(a - b) for a, b in zip(have, v))
            if d > TOL:
                print("DRIFT %s: wf_reitz_missions.lua %s vs source %s (%.1f m)" % (k, have, v, d / 100))
                bad += 1
    for name, s in src.get("_tokens_partial", {}).items():
        n += 1
        h = next((t for t in lua["tokens"] if t[3] == name), None)
        if h is None or max(abs(a - b) for a, b in zip(h[:3], s)) > TOL:
            print("DRIFT token %s: %s vs module %s" % (name, h, s))
            bad += 1
    for k, v in der.items():
        n += 1
        have = lua.get(k)
        if (isinstance(v, list) and have != v) or (isinstance(v, tuple) and max(abs(a - b) for a, b in zip(have, v)) > TOL) \
                or (isinstance(v, int) and abs(have - v) > TOL):
            print("DRIFT %s (derived): %s vs %s" % (k, have, v))
            bad += 1
    print("check_reitz_points: %d anchors vs %s (+ derived), %d mismatch(es)" % (n, where, bad))
    bad = check_built(lua, bad)
    return 1 if bad else 0


sys.exit(main())
