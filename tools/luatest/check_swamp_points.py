"""Check (or print) the SWAMP_POINTS table of mods/sgl64/swamp_missions.lua against its source.

Source, in order of preference:
  1. data/uf/swamp_points.json (schema sgl64.swamp_points/1, written by tools/campus/build_stage.py swamp
     from the BUILT collision): named points {"name": ..., "game": [X, floor Y, Z]} anywhere in the file,
     the level-script stars (stars[].game_units) and races.stair_sprint.waypoints. The tower footprint
     (climb_zone) is not in the JSON and always comes from the stadium module.
  2. tools/campus/landmarks/swamp_stadium.py LANDMARKS[0] spots / markers (map metres, z = metres above
     grade) through the stages.json transform of the swamp window:
     X = (x - cx) * 100, Y = z * 100, Z = -(y - cy) * 100.
Usage (from anywhere):
  tools/.venv/bin/python -I tools/luatest/check_swamp_points.py          check, exit 1 on drift > 0.5 m
  tools/.venv/bin/python -I tools/luatest/check_swamp_points.py --print  print the source values
  ... --module   check against the stadium module even when the JSON exists
"""
import json
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
LUA = os.path.join(ROOT, "mods", "sgl64", "swamp_missions.lua")
TOL = 50  # game units (0.5 m)


def lua_points():
    text = open(LUA).read()
    body = text[text.index("SWAMP_POINTS = {"):]
    body = body[:body.index("\n}\n")]
    pts = {}
    for m in re.finditer(r"^\s*([a-z_]+)\s*=\s*\{\s*x\s*=\s*(-?\d+),\s*y\s*=\s*(-?\d+),\s*z\s*=\s*(-?\d+)", body, re.M):
        pts[m.group(1)] = tuple(int(m.group(i)) for i in (2, 3, 4))
    cps = re.findall(r"\{\s*x\s*=\s*(-?\d+),\s*y\s*=\s*(-?\d+),\s*z\s*=\s*(-?\d+),\s*name", body)
    for i, c in enumerate(cps):
        pts["sprint_cp_%d" % (i + 1)] = tuple(int(v) for v in c)
    zone = re.search(r"climb_zone\s*=\s*\{\s*x0\s*=\s*(-?\d+),\s*x1\s*=\s*(-?\d+),\s*z0\s*=\s*(-?\d+),\s*z1\s*=\s*(-?\d+)", body)
    if zone:
        pts["climb_zone"] = tuple(int(zone.group(i)) for i in range(1, 5))
    return pts


# SWAMP_POINTS name -> swamp_points.json point name
JSON_NAMES = {
    "field_center": "field_center",
    "scoreboard_top": "secret_south_board_top",
    "climb_goal": "press_box_roof_star_spot",
    "climb_start": "kickoff_climb_00",
    "climb_bgd": "bull_gator_deck",
    "climb_ledge_top": "kickoff_climb_11",
    "climb_decks": "kickoff_climb_13",
    "climb_pole": "pole_bgd_to_press_box_roof",
    "button_nw": "endzone_corner_NW",
    "button_ne": "endzone_corner_NE",
    "button_se": "endzone_corner_SE",
    "button_sw": "endzone_corner_SW",
    "sprint_start": "stair_sprint_00",
    "sprint_star": "rc_south_ramp_terrace",
}


def json_points(jpath):
    data = json.load(open(jpath))
    named = {}

    def walk(o):
        if isinstance(o, dict):
            if isinstance(o.get("name"), str) and isinstance(o.get("game"), list) and len(o["game"]) == 3:
                named.setdefault(o["name"], tuple(int(round(v)) for v in o["game"]))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(data)
    out = {}
    for lua_name, json_name in JSON_NAMES.items():
        if json_name not in named:
            raise SystemExit("swamp_points.json has no point %r (for SWAMP_POINTS.%s)" % (json_name, lua_name))
        out[lua_name] = named[json_name]
    wps = data["races"]["stair_sprint"]["waypoints"]
    for i, wp in enumerate(wps[1:]):
        out["sprint_cp_%d" % (i + 1)] = tuple(int(round(v)) for v in wp["game"])
    act1 = [st for st in data.get("stars", []) if st.get("act") == 1]
    if act1:
        out["climb_star"] = tuple(int(round(v)) for v in act1[0]["game_units"])
    return out


def source_points():
    jpath = os.path.join(ROOT, "data", "uf", "swamp_points.json")
    if os.path.exists(jpath) and "--module" not in sys.argv:
        out = json_points(jpath)
        mod, _ = module_points()
        out["climb_zone"] = mod["climb_zone"]
        return out, os.path.relpath(jpath, ROOT) + " (+ climb_zone from the stadium module)"
    return module_points()


def module_points():
    sys.path.insert(0, os.path.join(ROOT, "tools", "campus"))
    import itertools
    from landmarks import swamp_stadium as S
    stages = json.load(open(os.path.join(ROOT, "data", "uf", "stages.json")))
    cx, cy = [s for s in stages["stages"] if s["key"] == "swamp"][0]["center_m"]
    L = S.LANDMARKS[0]
    sp, mk = L["spots"], L["markers"]

    def g(p):
        return (round((p[0] - cx) * 100), round(p[2] * 100), round(-(p[1] - cy) * 100))

    out = {
        "field_center": g(sp["field_center"]),
        "scoreboard_top": g(sp["south_board_top"]),
        "climb_goal": g(sp["press_box_roof_star"]),
        "climb_start": g(L["climb_route_m"][0]),
        "climb_bgd": g(sp["bull_gator_deck"]),
        "climb_ledge_top": g(L["climb_route_m"][11]),
        "climb_decks": g(L["climb_route_m"][13]),
        "climb_pole": g(next(q["base_m"] for q in mk["poles"] if q["name"] == "bgd_to_press_box_roof")),
        "button_nw": g(sp["endzone_button_NW"]),
        "button_ne": g(sp["endzone_button_NE"]),
        "button_se": g(sp["endzone_button_SE"]),
        "button_sw": g(sp["endzone_button_SW"]),
        "sprint_start": g(mk["stair_sprint_m"][0]),
        "sprint_star": g(sp["south_ramp_terrace"]),
    }
    for i, p in enumerate(mk["stair_sprint_m"][1:]):
        out["sprint_cp_%d" % (i + 1)] = g(p)
    corners = [S.to_map(u, v) for u, v in itertools.product((-130.0, -80.0), (-56.0, 56.0))]
    xs = [round((x - cx) * 100) for x, _ in corners]
    zs = [round(-(y - cy) * 100) for _, y in corners]
    out["climb_zone"] = (min(xs), max(xs), min(zs), max(zs))
    return out, "tools/campus/landmarks/swamp_stadium.py"


def main():
    src, where = source_points()
    if "--print" in sys.argv:
        for k, v in src.items():
            print("    %s = %s," % (k, v))
        return 0
    have = lua_points()
    bad = 0
    for k, v in src.items():
        if k not in have:
            print("missing in SWAMP_POINTS: %s (source %s)" % (k, v))
            bad += 1
            continue
        d = max(abs(a - b) for a, b in zip(have[k], v))
        if d > TOL:
            print("DRIFT %s: swamp_missions.lua %s vs source %s (%.1f m)" % (k, have[k], v, d / 100))
            bad += 1
    print("check_swamp_points: %d anchors vs %s, %d mismatch(es)" % (len(src), where, bad))
    return 1 if bad else 0


sys.exit(main())
