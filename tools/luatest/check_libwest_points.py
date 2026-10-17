"""Check (or print) the LIBWEST_POINTS table of mods/sgl64/uf_west_library_missions.lua (Library West After Dark,
course 5, LEVEL_BBH, an interior stage) against its sources and, once it exists, the built level.

1. Source values (drift > 0.5 m fails), in order of preference:
   a. data/uf/libwest_points.json (written by the stage build from the BUILT collision, when it exists): any point
      record { "name": ..., "game": [X, floor Y, Z] } whose name is in JSON_NAMES below overrides the layout value of
      that LIBWEST_POINTS key.
   b. data/uf/libwest_layout.json (the layout research, map metres) through its own transform (centre_m (38.9, 285.6)):
          X = (x - 38.9) * 100,  Y = z * 100,  Z = -(y - 285.6) * 100
      either straight from its "missions" anchors (spawn, the act 1 Boos on the terrace / quiet floor / grad floor,
      the coffee cup, the seeker start, the hider release, the circulation desk star, the hiding spots) or from the
      layout geometry with the rules below (RULES), which are the ones the Lua comments state.
2. Layout sanity (no build needed): every standing point lies on walkable floor of its storey (inside the floor
   outline or an outdoor terrace zone, outside non-walkable zones, props, stair halls and the Plaza Hall void, 0.4 m
   clear of the inferred columns) unless it is meant to be inside a stair hall (landings, stairwell Boos) or on a prop
   (the coffee cup on its counter, the act 3 star on the circulation counter); the act 1 barriers cover the seven
   F1-F3 doors of the west and east stair halls (0.3 m past both jambs); every rolling-ladder deck stays beside its
   3.6 m range (never inside it), inside its range's length and clear of the columns and the next row; a Boo's
   home is inside its floor (or stair hall / terrace) and not inside a prop; a spawned star's 4 m hump stays under its
   storey's ceiling; the hide-and-seek arena (two rectangles) holds the layout's arena polygon, both release points
   and every hiding spot, and not the seeker's desk; the coffee run's route estimate fits its par time; every
   coordinate fits SM64's s16 range.
3. The built level (mods/sgl64/levels/bbh/area_1/collision.inc.c, when it exists), with SM64's find_floor rule
   (floors = normal.y > 0.01; a floor counts up to 78 units above the probe): every standing anchor has a floor within
   0.5 m of its Y when probed from 2 m above (the missions' own geometry probes do the same), nothing static sits in a
   rolling ladder's travel box (deck + 1.6 m of rider headroom), no static floor or ceiling sits in a star's column,
   and the doors the three acts need are open (no static triangle in the doorway: the stair-hall doors of F2 / F4 /
   F6, the NW / NE stair halls' doors on F1-F3 and their roof doors, the 4th floor's north terrace door, and the
   5th floor's stair doors, which the build leaves open for the missions to lock with Lua barriers).
   Fix round (technical review: car A's F1 doorway had a 0.2 m strip with no floor, an invisible wall that trapped
   anyone who dropped into the shaft):
   * DOOR WALK-THROUGH: from every door anchor of libwest_points.json (circulation doors / elevator doors, the study
     rooms' and rooms' doors, the terrace doors) 3 m forward and 3 m back along its facing in 4-unit steps (SM64
     ground steps: the next floor within 78 units up), no CRACK: a strip with no floor (out of bounds = a wall in
     SM64) with walkable floor at the same level again after it. A walk that ends out of bounds (a closed elevator,
     a terrace edge) is no crack. elevator_a_door_F1 must exist and walk through.
   * FLOOR-CRACK SCAN (numpy; skipped without it): a 5-unit raster of the flat floors at every storey height; no
     strip <= 45 units wide without floor between floor on both sides (along x or z) that no wall covers (no wall
     within 30 units at 0.6 m over the floor).
Usage (from anywhere):
  tools/.venv/bin/python -I tools/luatest/check_libwest_points.py          check, exit 1 on any finding
  tools/.venv/bin/python -I tools/luatest/check_libwest_points.py --print  print the source values (Lua syntax)
  ... --layout   ignore data/uf/libwest_points.json (layout only)
SGL_BBH_POINTS / SGL_BBH_COLLISION: check a scratch build instead.
"""
import json
import math
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
LUA = os.path.join(ROOT, "mods", "sgl64", "uf_west_library_missions.lua")
LAYOUT = os.path.join(ROOT, "data", "uf", "libwest_layout.json")
POINTS_JSON = os.environ.get("SGL_BBH_POINTS") or os.path.join(ROOT, "data", "uf", "libwest_points.json")
COLLISION = os.environ.get("SGL_BBH_COLLISION") or os.path.join(ROOT, "mods", "sgl64", "levels", "bbh", "area_1",
                                                                "collision.inc.c")
TOL = 50                   # game units (0.5 m)
S16 = 32767
COLUMN_HALF_M = 0.35       # the inferred structural columns (columns_m are centre points)
STAND_CLEAR_M = 0.4        # a standing anchor from a column
BARRIER_MARGIN_M = 0.3     # an act 1 barrier reaches this far past both door jambs
STAR_HUMP = 400            # bhvStarSpawnCoordinates: y = lerp(from, to) + sins(t * 0x8000 / 30) * 400
STAR_SIZE = 60
RUN_SPEED_MS = 6.0         # coffee run: a careful runner's average (Mario runs 9.6 m/s on the flat)
PAR_S, GOLD_S = 60, 45     # uf_west_library_missions.lua act 2 spec

# ------------------------------------------------------------------------------------------- the rules
# (keep in step with the LIBWEST_POINTS comments in uf_west_library_missions.lua)
GOAL_M = (38.9, 261.0)          # act 1 goal: the 6th floor's big window (the aisle between the window desk and the
                                # reading tables, 1.1 m north of the layout's act 1 star anchor)
STAR_UP_M = 0.8                 # every spawned star floats 0.8 m over its floor (the hump clears the 5.4 m ceiling)
ESC_FOOT_BACK_M = 0.5           # the escalator marker: the up lane's foot, 0.5 m into the vestibule
ESC_TOP_IN_M = 1.1              # ... and the top landing, 1.1 m past the escalators' top
DOOR_OUT_M = 0.8                # NW / NE stair hall doors: the marker 0.8 m in front of the door (in the stacks)
TOWER_DOOR_OUT_M = 1.8          # the 4th floor's north terrace door: the marker 1.8 m out on the terrace
HALL_DOOR_OUT_M = 1.3           # west / east stair hall doors: the marker 1.3 m out of the hall ...
HALL_DOOR_NORTH_M = 0.7         # ... on F4 / F6 by the door's north part (a column stands 0.6 m off its middle)
LADDER_FACE_GAP_M = 0.5         # a rolling ladder's deck centre: 0.5 m in front of its range's south face ...
LADDER_TOP_M = 1.5              # ... with its step 1.5 m up (a standing single jump peaks at 2.2 m)
LADDER_HALF_X_M, LADDER_HALF_Z_M = 0.7, 0.35   # its deck: 1.4 x 0.7 m
RUN_START_M = (38.9, 266.2)     # act 2: the grad reading room aisle between reading table 2 and group rooms A / B
CUP_STAND_BACK_M = 1.4          # act 2: where a runner stands to grab the cup (west of the counter)
# act 1 Boos: the layout's anchors, moved off the column grid; two in the NW / NE stairwells (their F3 -> roof turn
# landing, z 15) instead of the layout's 3rd-floor one (act 1 never leaves those stairwells on F3)
BOOS1 = [
    ("STACKS WEST", "F2", (28.3, 303.2), None),
    ("STACKS EAST", "F2", (49.2, 303.2), None),
    ("NW STAIRWELL", "stair_nw", None, 15.0),
    ("NE STAIRWELL", "stair_ne", None, 15.0),
    ("ROOF TERRACE", "F4", "boo:3", None),
    ("QUIET FLOOR", "F4", "boo:4", None),
    ("GRAD READING ROOM", "F6", "boo:5", None),
]
# act 2 Boos: the turn landings of the west (z 9, 21) and east (z 15, 27) stair halls (the layout's three + one more,
# two in each hall between the 6th and the 2nd floor)
BOOS2 = [("WEST STAIRWELL 2-3F", "stair_w", 9.0), ("WEST STAIRWELL 4-5F", "stair_w", 21.0),
         ("EAST STAIRWELL 3-4F", "stair_e", 15.0), ("EAST STAIRWELL 5-6F", "stair_e", 27.0)]
# act 1 barriers ("closed for cleaning"): every F1-F3 door of the west and east stair halls
BARRIER_DOORS = [("stair_w", "F1"), ("stair_w", "F2"), ("stair_w", "F3"), ("stair_w", "F3_east"),
                 ("stair_e", "F1"), ("stair_e", "F2"), ("stair_e", "F3")]
# act 3: the arena polygon as two rectangles: the neck (x 16.1..61.5, y 287.6..295.9) and the north wing with its
# bays, stair towers and curved front (x 4.8..73.0, y 295.6..320.07)
ARENA_NECK_M = (16.1, 61.5, 287.6, 295.9)
ARENA_WING_M = (4.8, 73.0, 295.6, 320.07)
# act 3 hiding spots: the layout's eight, three moved off the column grid (the Bloomberg spot next to the terminal)
HIDE_NAMES = ["1F COMPACT STACKS", "1F CURVED GLASS BAY", "1F WEST WINDOWS", "2F NE STAIR AISLE",
              "2F EAST WINDOW SEATS", "3F MICROFORM CABINETS", "3F OVERSIZED FOLIOS", "3F BLOOMBERG TERMINAL"]
HIDE_MOVED_M = {3: (59.67, 306.8), 5: (57.0, 300.9), 7: (44.6, 291.4)}
FLOORS = ["F1", "F2", "F3", "F4", "F5", "F6"]

SHAFT_OUT_M = 0.7               # the out-of-order elevator shaft (car A): its door, 0.7 m out (north)
# act 1-3: the 5th floor's stair doors are open gaps in the build; the missions lock them ("STAFF ONLY")
STAFF_DOORS = [("stair_w", "F5_locked"), ("stair_e", "F5_locked")]

# LIBWEST_POINTS key -> libwest_points.json point names (the build's actN_ keys use the design act numbers) and the
# height added to the measured floor (stars float over their floor / counter)
JSON_NAMES = {
    "spawn": (("spawn_0x0A", 0),),
    "climb_star": (("act1_star_target", int(STAR_UP_M * 100)),),
    "cup": (("act5_cup", 0),),
    "desk": (("act2_seeker_start", 0),),
    "desk_star": (("act2_star_target", 5),),
    "release_w": (("act2_hider_release", 0),),
    "release_e": (("act2_hider_release_east", 0),),
    "shaft_door": (("elevator_a_door_F2", 0),),
    "esc_top": (("escalator_top", 0),),
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
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


def poly_dist(p, poly):
    """0 inside, else the distance to the polygon's edge"""
    if pip(p, poly):
        return 0.0
    return min(seg_dist(p, poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly)))


def bbox(poly):
    xs = [q[0] for q in poly]
    ys = [q[1] for q in poly]
    return min(xs), max(xs), min(ys), max(ys)


# ------------------------------------------------------------------------------------------- sources
class Layout:
    def __init__(self):
        self.d = json.load(open(LAYOUT))
        self.cx, self.cy = self.d["center_m"]
        self.floors = {f["id"]: f for f in self.d["floors"]}
        self.cores = {c["id"]: c for c in self.d["vertical"]}
        self.miss = self.d["missions"]

    def gx(self, x):
        return int(round((x - self.cx) * 100))

    def gz(self, y):
        return int(round(-(y - self.cy) * 100))

    def game(self, x, y, z):
        return (self.gx(x), int(round(z * 100)), self.gz(y))

    def zfloor(self, fid):
        return self.floors[fid]["z_game_m"]

    def prop(self, fid, pid):
        for p in self.floors[fid]["props"]:
            if p["id"] == pid:
                return p
        raise KeyError(pid)

    def door(self, core, key):
        c = self.cores[core]
        doors = (c.get("game") or {}).get("doors") or c.get("doors")
        a, b, facing = doors[key]
        return a, b, facing

    def hall_box(self, core):
        return bbox(self.cores[core]["poly_m"])


def json_points(use_json):
    if not use_json or not os.path.exists(POINTS_JSON):
        return {}
    out = {}

    def walk(o):
        if isinstance(o, dict):
            if isinstance(o.get("name"), str) and isinstance(o.get("game"), list) and len(o["game"]) == 3:
                out[o["name"]] = tuple(int(round(v)) for v in o["game"])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(json.load(open(POINTS_JSON)))
    return out


def rnd10(v):
    return int(round(v / 10.0)) * 10


def sources(use_json=True):
    L = Layout()
    jp = json_points(use_json)
    src, why = {}, {}

    def put(k, v, w):
        src[k] = v
        why[k] = w

    m = L.miss
    a1, a2, a3, a5 = (m["design_act1_all_nighter"], m["design_act2_quiet_hours_hide_and_seek"],
                      m["design_act3_ghost_of_finals_past"], m["design_act5_coffee_run"])
    put("spawn", tuple(m["spawn"]["game_xyz"]), "missions.spawn")
    ob = bbox(L.floors["F1"]["outline_m"])
    put("zone", {"x0": L.gx(ob[0]), "x1": L.gx(ob[1]), "z0": L.gz(ob[3]), "z1": L.gz(ob[2])}, "F1-F3 outline bbox")
    for i, fid in enumerate(FLOORS):
        put("y_f%d" % (i + 1), int(round(L.zfloor(fid) * 100)), "floors[%s].z_game_m" % fid)
    put("clear", int(round(L.floors["F1"]["clear_height_game_m"] * 100)), "clear_height_game_m")

    # stair halls, landings, the tower
    for key, core in (("hall_w", "stair_w"), ("hall_e", "stair_e"), ("hall_nw", "stair_nw"), ("hall_ne", "stair_ne")):
        x0, x1, y0, y1 = L.hall_box(core)
        put(key, {"x0": L.gx(x0), "x1": L.gx(x1), "z0": L.gz(y1), "z1": L.gz(y0)}, "vertical.%s.poly_m" % core)
    for key, core in (("land_w", "stair_w"), ("land_e", "stair_e")):
        g = L.cores[core]["game"]
        lx = (g["lanes_m"][0][0] + g["lanes_m"][1][1]) / 2
        ly = (g["floor_landing_y_m"][0] + g["floor_landing_y_m"][1]) / 2
        put(key, (rnd10(L.gx(lx)), 0, rnd10(L.gz(ly))), "%s floor landing centre (Y per floor)" % core)
    tb = bbox(L.floors["F4"]["outline_m"])
    north = [o for o in L.floors["F4"]["openings"] if o["id"] == "door_terrace_n"][0]["a_m"][1]
    put("tower", {"x0": L.gx(tb[0]), "x1": L.gx(tb[1]), "z0": L.gz(north), "z1": L.gz(tb[2])},
        "F4 outline bbox up to its north face (the terrace door's wall, y %.1f)" % north)

    ph = bbox(L.cores["plaza_hall"]["game"].get("poly_m") or [z for z in L.floors["F2"]["zones"] if z["id"] == "f2_plaza_void"][0]["poly_m"])
    put("lobby", {"x0": L.gx(ph[0]), "x1": L.gx(ph[1]), "z0": L.gz(ph[3]), "z1": L.gz(ph[2])}, "the Plaza Hall (F2 void) bbox")
    eg = L.cores["escalators"]["game"]
    put("esc_band", {"x0": L.gx(eg["lanes_m"][0][0]), "x1": L.gx(eg["lanes_m"][1][1]), "z0": L.gz(eg["top_m"][1]),
                     "z1": L.gz(eg["bottom_m"][1])}, "escalators lanes x bottom..top")

    # act 1
    put("climb_goal", L.game(GOAL_M[0], GOAL_M[1], L.zfloor("F6")), "GOAL_M on F6")
    sx, sy = a1["star"]["pos_m"]
    put("climb_star", L.game(sx, sy, L.zfloor("F6") + STAR_UP_M), "act 1 star anchor, %.1f m over F6" % STAR_UP_M)
    esc = L.cores["escalators"]["game"]
    ul = esc["up_lane_m"]
    put("esc_foot", (rnd10(L.gx((ul[0] + ul[1]) / 2)), 0, rnd10(L.gz(esc["bottom_m"][1] - ESC_FOOT_BACK_M))),
        "escalators.up_lane foot - %.1f m" % ESC_FOOT_BACK_M)
    put("esc_top", (rnd10(L.gx(esc["top_m"][0])), int(esc["top_z_game_m"] * 100),
                    rnd10(L.gz(esc["top_m"][1] + ESC_TOP_IN_M))), "escalators.top_m + %.1f m" % ESC_TOP_IN_M)
    for key, core in (("door_nw", "stair_nw"), ("door_ne", "stair_ne")):
        a, b, _ = L.door(core, "F2")
        put(key, (rnd10(L.gx((a[0] + b[0]) / 2)), int(L.zfloor("F2") * 100), rnd10(L.gz(a[1] - DOOR_OUT_M))),
            "%s F2 door - %.1f m (south, into the stacks)" % (core, DOOR_OUT_M))
    dn = [o for o in L.floors["F4"]["openings"] if o["id"] == "door_terrace_n"][0]
    put("tower_door", (rnd10(L.gx((dn["a_m"][0] + dn["b_m"][0]) / 2)), int(L.zfloor("F4") * 100),
                       rnd10(L.gz(dn["a_m"][1] + TOWER_DOOR_OUT_M))), "door_terrace_n + %.1f m north" % TOWER_DOOR_OUT_M)
    for key, core, dk, fid, sign in (("f4_door_w", "stair_w", "F4_east", "F4", 1), ("f4_door_e", "stair_e", "F4", "F4", -1),
                                     ("f6_door_w", "stair_w", "F6", "F6", 1), ("f6_door_e", "stair_e", "F6", "F6", -1)):
        a, b, _ = L.door(core, dk)
        put(key, (rnd10(L.gx(a[0] + sign * HALL_DOOR_OUT_M)), int(L.zfloor(fid) * 100),
                  rnd10(L.gz((a[1] + b[1]) / 2 + HALL_DOOR_NORTH_M))),
            "%s %s door %+.1f m (x), %.1f m north of its middle" % (core, dk, sign * HALL_DOOR_OUT_M, HALL_DOOR_NORTH_M))
    rows = []
    for core, fk in BARRIER_DOORS:
        a, b, _ = L.door(core, fk)
        fid = fk.split("_")[0]
        rows.append({"x0": L.gx(a[0]), "z0": L.gz(a[1]), "x1": L.gx(b[0]), "z1": L.gz(b[1]), "y": int(L.zfloor(fid) * 100)})
    put("stair_doors", rows, "vertical[].game.doors (BARRIER_DOORS)")
    rows = []
    for core, fk in STAFF_DOORS:
        a, b, _ = L.door(core, fk)
        rows.append({"x0": L.gx(a[0]), "z0": L.gz(a[1]), "x1": L.gx(b[0]), "z1": L.gz(b[1]), "y": int(L.zfloor("F5") * 100)})
    put("staff_doors", rows, "vertical[].game.doors F5_locked (STAFF_DOORS)")
    ea = [e for e in L.cores["elevators_main"]["elevators"] if e["id"] == "elev_a"][0]
    (ax, ay), (bx, by) = ea["door_m"]
    put("shaft_door", (rnd10(L.gx((ax + bx) / 2)), int(L.zfloor("F2") * 100), rnd10(L.gz(ay + SHAFT_OUT_M))),
        "elevators_main.elev_a door + %.1f m (north)" % SHAFT_OUT_M)
    rows = []
    for name, where, pos, z in BOOS1:
        if isinstance(pos, str):
            p = a1["boos"][int(pos.split(":")[1])]
            gx, gy, gz = p["game_xyz"]
        elif pos is None:
            g = L.cores[where]["game"]
            lx = (g["lanes_m"][0][0] + g["lanes_m"][1][1]) / 2
            ly = (g["turn_landing_y_m"][0] + g["turn_landing_y_m"][1]) / 2
            gx, gy, gz = rnd10(L.gx(lx)), int(z * 100), rnd10(L.gz(ly))
        else:
            gx, gy, gz = L.game(pos[0], pos[1], L.zfloor(where))
        rows.append({"x": gx, "y": gy, "z": gz, "name": name})
    put("boos1", rows, "BOOS1 (layout boos / stair-hall turn landings)")
    rows = []
    for tr in a1["book_ladder_tracks"]:
        fid = tr["floor"]
        rp = L.prop(fid, tr["range"])
        rx0, rx1, ry0, ry1 = bbox(rp["poly_m"])
        x0, x1 = max(tr["a_m"][0], rx0), min(tr["b_m"][0], rx1)
        rows.append({"x0": L.gx(x0), "x1": L.gx(x1), "z": L.gz(ry0 - LADDER_FACE_GAP_M),
                     "y": int(round((L.zfloor(fid) + LADDER_TOP_M) * 100))})
    put("ladders", rows, "book_ladder_tracks + their ranges' south faces")

    # act 2
    put("run_start", L.game(RUN_START_M[0], RUN_START_M[1], L.zfloor("F6")), "RUN_START_M on F6")
    cup = a5["cup"]["game_xyz"]
    put("cup", tuple(cup), "missions.design_act5_coffee_run.cup")
    put("cup_stand", (cup[0] - int(CUP_STAND_BACK_M * 100), 0, cup[2]), "cup - %.1f m (x)" % CUP_STAND_BACK_M)
    a, b, _ = L.door("stair_w", "F2")
    put("f2_door_w", (rnd10(L.gx(a[0] - HALL_DOOR_OUT_M)), int(L.zfloor("F2") * 100), rnd10(L.gz((a[1] + b[1]) / 2))),
        "stair_w F2 door - %.1f m (west)" % HALL_DOOR_OUT_M)
    a, b, _ = L.door("stair_e", "F2")
    put("f2_door_e", (rnd10(L.gx((a[0] + b[0]) / 2)), int(L.zfloor("F2") * 100), rnd10(L.gz(a[1] + HALL_DOOR_OUT_M))),
        "stair_e F2 door + %.1f m (north)" % HALL_DOOR_OUT_M)
    rows = []
    for name, core, z in BOOS2:
        g = L.cores[core]["game"]
        lx = (g["lanes_m"][0][0] + g["lanes_m"][1][1]) / 2
        ly = (g["turn_landing_y_m"][0] + g["turn_landing_y_m"][1]) / 2
        rows.append({"x": rnd10(L.gx(lx)), "y": int(z * 100), "z": rnd10(L.gz(ly)), "name": name})
    put("boos2", rows, "BOOS2 (stair-hall turn landings)")

    # act 3
    put("desk", tuple(a2["seeker_start"]["game_xyz"]), "missions.design_act2.seeker_start")
    put("desk_star", tuple(a2["star"]["game_xyz"]), "missions.design_act2.star")
    rel = a2["hider_release"]
    put("release_w", tuple(rel["game_xyz"]), "missions.design_act2.hider_release")
    put("release_e", L.game(2 * L.cx - rel["pos_m"][0], rel["pos_m"][1], rel["z_game_m"]), "hider_release mirrored (x)")
    for key, r in (("arena_neck", ARENA_NECK_M), ("arena_wing", ARENA_WING_M)):
        put(key, {"x0": L.gx(r[0]), "x1": L.gx(r[1]), "z0": L.gz(r[3]), "z1": L.gz(r[2])}, key.upper() + "_M")
    rows = []
    for i, (spot, name) in enumerate(zip(a2["hiding_spots"], HIDE_NAMES)):
        if i in HIDE_MOVED_M:
            gx, gy, gz = L.game(HIDE_MOVED_M[i][0], HIDE_MOVED_M[i][1], spot["z_game_m"])
        else:
            gx, gy, gz = spot["game_xyz"]
        rows.append({"x": gx, "y": gy, "z": gz, "name": name})
    put("hide_spots", rows, "missions.design_act2.hiding_spots (HIDE_MOVED_M)")

    for key, names in JSON_NAMES.items():
        for n, dy in names:
            if n in jp:
                put(key, (jp[n][0], jp[n][1] + dy, jp[n][2]), "libwest_points.json " + n + (" + %d" % dy if dy else ""))
                break
    return src, why, L, a3


# ------------------------------------------------------------------------------------------- Lua side
def lua_points():
    text = open(LUA).read()
    body = text[text.index("local function libwest_points() return {"):]
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
            print("missing in LIBWEST_POINTS: %s (source %s)" % (k, v))
            bad += 1
        elif isinstance(v, list):
            if not isinstance(have, list) or len(have) != len(v):
                print("%s: %s rows in LIBWEST_POINTS, %d in the source" % (k, len(have) if isinstance(have, list) else "no", len(v)))
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
def layout_sanity(lua, L):
    bad = 0

    def m_of(X, Z):
        return (X / 100.0 + L.cx, -Z / 100.0 + L.cy)

    def fid_of(Y):
        k = int(round(Y / 600.0))
        return FLOORS[k] if 0 <= k < len(FLOORS) and abs(Y - k * 600) < 1 else None

    halls = {c: L.cores[c]["poly_m"] for c in ("stair_w", "stair_e", "stair_nw", "stair_ne")}

    def in_core(fid, p):
        for c in L.d["vertical"]:
            if c["type"] in ("stair", "elevator_bank", "elevator", "escalator") and c.get("poly_m") and fid in c.get("floors", []):
                if pip(p, c["poly_m"]):
                    return c["id"]
            for e in c.get("elevators", []):
                if fid in c.get("floors", []) and pip(p, e["poly_m"]):
                    return e["id"]
        return None

    def standing(name, X, Y, Z, on_prop=None, in_hall=None, floating=False):
        nonlocal bad
        p = m_of(X, Z)
        fid = fid_of(Y)
        if in_hall is not None:
            if not pip(p, halls[in_hall]):
                print("LAYOUT %s (%.2f, %.2f) is not inside %s" % (name, p[0], p[1], in_hall))
                bad += 1
            return
        if on_prop is not None:
            fid_p, pid = on_prop
            pr = L.prop(fid_p, pid)
            if poly_dist(p, pr["poly_m"]) > 0.05:
                print("LAYOUT %s (%.2f, %.2f) is not on %s" % (name, p[0], p[1], pid))
                bad += 1
            top = int(round((L.zfloor(fid_p) + pr["height_m"]) * 100))
            if not (top - 10 <= Y <= top + 120):          # (the build may make a counter a few cm lower)
                print("LAYOUT %s Y %d is not just over %s's top (%d)" % (name, Y, pid, top))
                bad += 1
            return
        if fid is None:
            print("LAYOUT %s: Y %d is not a floor height" % (name, Y))
            bad += 1
            return
        f = L.floors[fid]
        outdoor = None
        if not pip(p, f["outline_m"]):
            for z in f["zones"]:
                if z["type"] == "terrace" and pip(p, z["poly_m"]):
                    outdoor = z["id"]
            if outdoor is None:
                print("LAYOUT %s (%.2f, %.2f) is outside the %s outline" % (name, p[0], p[1], fid))
                bad += 1
                return
        for z in f["zones"]:
            if not z.get("walkable", True) and pip(p, z["poly_m"]):
                print("LAYOUT %s (%.2f, %.2f) is in the non-walkable %s" % (name, p[0], p[1], z["id"]))
                bad += 1
        core = in_core(fid, p)
        if core is not None:
            print("LAYOUT %s (%.2f, %.2f) is inside %s" % (name, p[0], p[1], core))
            bad += 1
        for pr in f["props"]:
            if "poly_m" in pr and pip(p, pr["poly_m"]):
                if floating and pr.get("height_m", 9) <= 1.0:
                    continue
                print("LAYOUT %s (%.2f, %.2f) is inside prop %s" % (name, p[0], p[1], pr["id"]))
                bad += 1
        if not floating:
            for c in f.get("columns_m", []):
                if abs(p[0] - c[0]) < COLUMN_HALF_M + STAND_CLEAR_M and abs(p[1] - c[1]) < COLUMN_HALF_M + STAND_CLEAR_M:
                    print("LAYOUT %s (%.2f, %.2f) is %.2f m from column (%.2f, %.2f)" % (name, p[0], p[1],
                                                                                     math.hypot(p[0] - c[0], p[1] - c[1]), c[0], c[1]))
                    bad += 1

    def xyz(k):
        return lua[k]

    for k in ("spawn", "climb_goal", "esc_foot", "esc_top", "door_nw", "door_ne", "tower_door", "f4_door_w", "f4_door_e",
              "f6_door_w", "f6_door_e", "run_start", "cup_stand", "f2_door_w", "f2_door_e", "desk", "release_w", "release_e",
              "shaft_door"):
        standing(k, *xyz(k))
    standing("door_nw (F3)", lua["door_nw"][0], lua["y_f3"], lua["door_nw"][2])
    standing("door_ne (F3)", lua["door_ne"][0], lua["y_f3"], lua["door_ne"][2])
    standing("roof door nw (F4 terrace)", lua["door_nw"][0], lua["y_f4"], lua["door_nw"][2])
    standing("roof door ne (F4 terrace)", lua["door_ne"][0], lua["y_f4"], lua["door_ne"][2])
    for k, hall in (("land_w", "stair_w"), ("land_e", "stair_e")):
        standing(k, lua[k][0], 0, lua[k][2], in_hall=hall)
    standing("cup", *lua["cup"], on_prop=("F1", "coffee_counter"))
    standing("desk_star", *lua["desk_star"], on_prop=("F2", "circ_counter"))
    for i, s in enumerate(lua["hide_spots"]):
        standing("hide_spots[%d] %s" % (i + 1, s["name"]), s["x"], s["y"], s["z"])
    for i, b in enumerate(lua["boos1"]):
        hall = {"NW STAIRWELL": "stair_nw", "NE STAIRWELL": "stair_ne"}.get(b["name"])
        standing("boos1[%d] %s" % (i + 1, b["name"]), b["x"], b["y"], b["z"], in_hall=hall, floating=True)
    for i, b in enumerate(lua["boos2"]):
        hall = "stair_w" if "WEST" in b["name"] else "stair_e"
        standing("boos2[%d] %s" % (i + 1, b["name"]), b["x"], b["y"], b["z"], in_hall=hall)
        # a turn landing: half way between two floors
        if b["y"] % 600 != 300:
            print("LAYOUT boos2[%d]: Y %d is not a turn landing (floor + 3 m)" % (i + 1, b["y"]))
            bad += 1

    # barriers: on the door line, 0.3 m past both jambs (the mission adds the margin), 7 doors
    if len(lua["stair_doors"]) != len(BARRIER_DOORS):
        print("LAYOUT %d act 1 barriers, want %d" % (len(lua["stair_doors"]), len(BARRIER_DOORS)))
        bad += 1
    for i, (d, (core, fk)) in enumerate(zip(lua["stair_doors"], BARRIER_DOORS)):
        a, b, _ = L.door(core, fk)
        if abs(math.hypot(d["x1"] - d["x0"], d["z1"] - d["z0"]) / 100 - math.dist(a, b)) > 0.05:
            print("LAYOUT stair_doors[%d] is not the width of %s %s" % (i + 1, core, fk))
            bad += 1
        if d["x0"] != d["x1"] and d["z0"] != d["z1"]:
            print("LAYOUT stair_doors[%d] is not axis-aligned" % (i + 1))
            bad += 1

    if len(lua["staff_doors"]) != len(STAFF_DOORS):
        print("LAYOUT %d staff-only barriers, want %d" % (len(lua["staff_doors"]), len(STAFF_DOORS)))
        bad += 1
    for i, (d, (core, fk)) in enumerate(zip(lua["staff_doors"], STAFF_DOORS)):
        a, b, _ = L.door(core, fk)
        if d["y"] != lua["y_f5"] or abs(math.hypot(d["x1"] - d["x0"], d["z1"] - d["z0"]) / 100 - math.dist(a, b)) > 0.05:
            print("LAYOUT staff_doors[%d] is not %s's 5th-floor door" % (i + 1, core))
            bad += 1

    # rolling ladders: beside the range (never in it), inside its length, clear of columns and the next row
    tracks = L.miss["design_act1_all_nighter"]["book_ladder_tracks"]
    hx, hz = LADDER_HALF_X_M, LADDER_HALF_Z_M
    for i, (ld, tr) in enumerate(zip(lua["ladders"], tracks)):
        fid = tr["floor"]
        f = L.floors[fid]
        rp = L.prop(fid, tr["range"])
        rx0, rx1, ry0, ry1 = bbox(rp["poly_m"])
        x0, x1 = ld["x0"] / 100.0 + L.cx, ld["x1"] / 100.0 + L.cx
        yc = -ld["z"] / 100.0 + L.cy
        deck = (x0, x1, yc - hz, yc + hz)          # the swept deck (map m)
        if not (rx0 - 0.01 <= x0 and x1 <= rx1 + 0.01 and x1 - x0 >= 2 * hx + 2.0):
            print("LAYOUT ladders[%d] track %.2f..%.2f is not inside %s (%.2f..%.2f) or too short" % (i + 1, x0, x1, rp["id"], rx0, rx1))
            bad += 1
        if not (ry0 - 0.3 <= deck[3] < ry0):
            print("LAYOUT ladders[%d] deck y %.2f..%.2f is not just in front of %s's south face %.2f" % (i + 1, deck[2], deck[3], rp["id"], ry0))
            bad += 1
        for pr in f["props"]:
            if "poly_m" not in pr or pr["id"] == rp["id"]:
                continue
            px0, px1, py0, py1 = bbox(pr["poly_m"])
            if px0 < deck[1] and deck[0] < px1 and py0 < deck[3] + 1.6 and deck[2] - 1.6 < py1 and pr["type"] == "range":
                gap = min(abs(deck[2] - py1), abs(py0 - deck[3]))
                if gap < 1.6:
                    print("LAYOUT ladders[%d] leaves %.2f m of aisle to %s" % (i + 1, gap, pr["id"]))
                    bad += 1
        for c in f.get("columns_m", []):
            if deck[0] - COLUMN_HALF_M < c[0] < deck[1] + COLUMN_HALF_M and deck[2] - COLUMN_HALF_M < c[1] < deck[3] + COLUMN_HALF_M:
                print("LAYOUT ladders[%d] sweeps through column (%.2f, %.2f)" % (i + 1, c[0], c[1]))
                bad += 1
        if ld["y"] != int(round((L.zfloor(fid) + LADDER_TOP_M) * 100)) or (rp["height_m"] < 3.0):
            print("LAYOUT ladders[%d]: step %d, range %.1f m" % (i + 1, ld["y"], rp["height_m"]))
            bad += 1

    # stars: the hump (from the floor / the desk front up to the star) stays under the storey's ceiling
    for name, star, frm in (("climb_star", lua["climb_star"], (lua["climb_star"][0], lua["y_f6"], lua["climb_star"][2])),
                            ("run star", (lua["run_start"][0], lua["run_start"][1] + int(STAR_UP_M * 100), lua["run_start"][2]),
                             lua["run_start"]),
                            ("desk_star", lua["desk_star"], lua["desk"])):
        floor = max(y for y in (lua["y_f%d" % k] for k in range(1, 7)) if y <= frm[1])
        peak = (star[1] + frm[1]) / 2.0 + STAR_HUMP + STAR_SIZE
        if peak > floor + lua["clear"]:
            print("LAYOUT %s: its spawn hump peaks at %.0f, over the ceiling %d" % (name, peak, floor + lua["clear"]))
            bad += 1

    # act 3: the arena rectangles hold the layout's arena polygon, the releases and the spots; not the desk
    def in_arena(X, Z):
        for k in ("arena_neck", "arena_wing"):
            r = lua[k]
            if r["x0"] <= X <= r["x1"] and r["z0"] <= Z <= r["z1"]:
                return True
        return False
    poly = L.miss["design_act2_quiet_hours_hide_and_seek"]["arena"]["poly_m"]
    for (x, y) in poly:
        if not in_arena(L.gx(x), L.gz(y)):
            print("LAYOUT arena vertex (%.2f, %.2f) is outside the arena rectangles" % (x, y))
            bad += 1
    for k in ("release_w", "release_e"):
        if not in_arena(lua[k][0], lua[k][2]):
            print("LAYOUT %s is outside the arena" % k)
            bad += 1
    for s in lua["hide_spots"]:
        if not in_arena(s["x"], s["z"]) or s["y"] > lua["y_f3"]:
            print("LAYOUT hide spot %s is outside the arena" % s["name"])
            bad += 1
    if in_arena(lua["desk"][0], lua["desk"][2]):
        print("LAYOUT the seeker's desk is inside the arena")
        bad += 1

    # act 2: a route estimate (straight legs + 18.7 m per storey of switchback stair hall) vs the par time
    def d3(a, b):
        return math.dist((a[0], a[2]), (b[0], b[2])) / 100.0
    down = (d3(lua["run_start"], lua["f6_door_e"]) + 4 * 18.7 + d3(lua["land_e"], lua["f2_door_e"])
            + d3(lua["f2_door_e"], lua["esc_top"]) + 12.0 + d3(lua["esc_foot"], lua["cup_stand"]))
    trip = 2 * down
    est = trip / RUN_SPEED_MS
    if not (GOLD_S < PAR_S and est <= PAR_S * 0.95):
        print("LAYOUT coffee run: %.0f m round trip ~ %.0f s at %.1f m/s does not fit par %d s" % (trip, est, RUN_SPEED_MS, PAR_S))
        bad += 1

    # every coordinate fits SM64's s16 range
    def each(v, name):
        nonlocal bad
        if isinstance(v, dict):
            for k, x in v.items():
                each(x, name + "." + k)
        elif isinstance(v, (list, tuple)):
            for i, x in enumerate(v):
                each(x, "%s[%d]" % (name, i + 1))
        elif isinstance(v, int) and abs(v) > S16:
            print("LAYOUT %s = %d is out of s16" % (name, v))
            bad += 1
    each(lua, "LIBWEST_POINTS")
    return bad, trip, est


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
            self.tris.append((a, b, c, nx, ny, nz, -(nx * x1 + ny * y1 + nz * z1)))
        self.floors = [t for t in self.tris if t[4] > 0.01]
        self.H = 400                       # floors hashed by 4 m cells (find_floor is called a lot by the door walks)
        self.fhash = {}
        for t in self.floors:
            xs, zs = [v[0] for v in t[:3]], [v[2] for v in t[:3]]
            for cx in range(math.floor(min(xs) / self.H), math.floor(max(xs) / self.H) + 1):
                for cz in range(math.floor(min(zs) / self.H), math.floor(max(zs) / self.H) + 1):
                    self.fhash.setdefault((cx, cz), []).append(t)

    def find_floor(self, x, y, z):
        best = None
        for (a, b, c, nx, ny, nz, oo) in self.fhash.get((math.floor(x / self.H), math.floor(z / self.H)), ()):
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

    def crosses_segment(self, a, b, y0, y1):
        """a static wall triangle whose plane cuts the doorway segment a -> b (x, z) between heights y0 and y1"""
        hits = 0
        for (p, q, r, nx, ny, nz, oo) in self.tris:
            if abs(ny) > 0.7:
                continue
            for k in range(1, 8):
                t = k / 8.0
                x, z = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
                for y in (y0, (y0 + y1) / 2.0, y1):
                    if abs(nx * x + ny * y + nz * z + oo) < 8 and self._inside(p, q, r, nx, ny, nz, (x, y, z)):
                        hits += 1
        return hits

    def segment_hits(self, p, q):
        """any static triangle crossed by the segment p -> q (Moller-Trumbore): what a collision ray would hit"""
        dx, dy, dz = q[0] - p[0], q[1] - p[1], q[2] - p[2]
        for (a, b, c, nx, ny, nz, oo) in self.tris:
            e1 = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
            e2 = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
            h = (dy * e2[2] - dz * e2[1], dz * e2[0] - dx * e2[2], dx * e2[1] - dy * e2[0])
            det = e1[0] * h[0] + e1[1] * h[1] + e1[2] * h[2]
            if abs(det) < 1e-9:
                continue
            f = 1.0 / det
            sv = (p[0] - a[0], p[1] - a[1], p[2] - a[2])
            u = f * (sv[0] * h[0] + sv[1] * h[1] + sv[2] * h[2])
            if u < 0 or u > 1:
                continue
            qv = (sv[1] * e1[2] - sv[2] * e1[1], sv[2] * e1[0] - sv[0] * e1[2], sv[0] * e1[1] - sv[1] * e1[0])
            v = f * (dx * qv[0] + dy * qv[1] + dz * qv[2])
            if v < 0 or u + v > 1:
                continue
            t = f * (e2[0] * qv[0] + e2[1] * qv[1] + e2[2] * qv[2])
            if 0 < t < 1:
                return True
        return False

    @staticmethod
    def _inside(a, b, c, nx, ny, nz, pt):
        # barycentric test projected on the dominant plane axis
        ax, ay, az = a
        bx, by, bz = b
        cx, cy, cz = c
        px, py, pz = pt
        if abs(nx) >= abs(nz):
            u = [(ay, az), (by, bz), (cy, cz)]
            p2 = (py, pz)
        else:
            u = [(ax, ay), (bx, by), (cx, cy)]
            p2 = (px, py)

        def sgn(p1, p2_, p3):
            return (p1[0] - p3[0]) * (p2_[1] - p3[1]) - (p2_[0] - p3[0]) * (p1[1] - p3[1])
        d1, d2, d3 = sgn(p2, u[0], u[1]), sgn(p2, u[1], u[2]), sgn(p2, u[2], u[0])
        neg = d1 < 0 or d2 < 0 or d3 < 0
        pos = d1 > 0 or d2 > 0 or d3 > 0
        return not (neg and pos)


DOOR_WALK = 300            # 3 m either way along a door anchor's facing
DOOR_STEP = 4
CRACK_MAX = 45             # a floor gap this wide or less between floors at one level is a crack (unless a wall covers it)


def door_anchors(path):
    """(name, (X, Y, Z), game_yaw) of every door anchor of libwest_points.json"""
    d = json.load(open(path))
    out = []

    def put(e):
        if isinstance(e, dict) and "game" in e and "game_yaw" in e and e.get("game_yaw") is not None:
            out.append((e["name"], tuple(e["game"]), int(e["game_yaw"], 16) if isinstance(e["game_yaw"], str) else int(e["game_yaw"])))
    for e in d.get("circulation", []):
        if "door" in e["name"] or "elevator" in e["name"]:
            put(e)
    for key in ("group_study_rooms", "rooms"):
        for e in d.get(key, []):
            put(e.get("door"))
    for e in d.get("terraces", []):
        if "door" in e.get("name", ""):
            put(e)
    return out


def walk_cracks(col, X, Y, Z, yaw):
    """walk DOOR_WALK units from (X, Y, Z) along yaw (SM64 sins / coss), ground steps; -> list of crack strings"""
    a = yaw / 65536.0 * 2 * math.pi
    sx, sz = math.sin(a), math.cos(a)
    cur = col.find_floor(X, Y + 20, Z)
    if cur is None:
        return ["no floor at the anchor"]
    out = []
    gap = None
    for k in range(1, DOOR_WALK // DOOR_STEP + 1):
        px, pz = X + sx * DOOR_STEP * k, Z + sz * DOOR_STEP * k
        f = col.find_floor(px, cur + 1, pz)
        if f is None:
            if gap is None:
                gap = DOOR_STEP * k
            continue
        if gap is not None:
            if abs(f - cur) <= 78:
                out.append("no floor %d..%d units out (at %d, %d)" % (gap, DOOR_STEP * k, round(px), round(pz)))
            gap = None
        if f > cur + 78:
            break                          # a step / a stair flight: the walk ends
        cur = f
    return out


def crack_scan(path, levels):
    """[(level, x0, x1, z0, z1, cells)] of floor cracks (see the module doc); None without numpy"""
    try:
        import numpy as np
    except ImportError:
        return None
    src = open(path).read()
    verts = np.array([[int(v) for v in m] for m in
                      re.findall(r"COL_VERTEX\(\s*(-?\d+),\s*(-?\d+),\s*(-?\d+)\s*\)", src)], dtype=np.float64)
    idx = np.array([[int(m.group(i)) for i in (1, 2, 3)] for m in
                    re.finditer(r"COL_TRI(?:_SPECIAL)?\(\s*(\d+),\s*(\d+),\s*(\d+)", src)], dtype=np.int64)
    T = verts[idx]
    v1, v2, v3 = T[:, 0], T[:, 1], T[:, 2]
    n = np.cross(v2 - v1, v3 - v2)
    mag = np.linalg.norm(n, axis=1)
    ok = mag > 1e-4
    ny = np.where(ok, n[:, 1] / np.where(ok, mag, 1), 0)
    is_floor, is_wall = ok & (ny > 0.01), ok & (np.abs(ny) <= 0.01)
    S = 5
    X0, X1, Z0, Z1 = (int(T[:, :, 0].min()) - 100, int(T[:, :, 0].max()) + 100, int(T[:, :, 2].min()) - 100,
                      int(T[:, :, 2].max()) + 100)
    nx_, nz_ = (X1 - X0) // S, (Z1 - Z0) // S
    xs = X0 + (np.arange(nx_) + 0.5) * S
    zs = Z0 + (np.arange(nz_) + 0.5) * S
    out = []
    for L in levels:
        cov = np.zeros((nx_, nz_), dtype=bool)
        for i in np.nonzero(is_floor & (np.abs(T[:, :, 1] - L).max(axis=1) <= 2))[0]:
            (x1, _, z1), (x2, _, z2), (x3, _, z3) = T[i]
            ix0 = max(0, int((min(x1, x2, x3) - X0) // S) - 1)
            ix1 = min(nx_ - 1, int((max(x1, x2, x3) - X0) // S) + 1)
            iz0 = max(0, int((min(z1, z2, z3) - Z0) // S) - 1)
            iz1 = min(nz_ - 1, int((max(z1, z2, z3) - Z0) // S) + 1)
            gx, gz = np.meshgrid(xs[ix0:ix1 + 1], zs[iz0:iz1 + 1], indexing="ij")
            e1 = (z1 - gz) * (x2 - x1) - (x1 - gx) * (z2 - z1)
            e2 = (z2 - gz) * (x3 - x2) - (x2 - gx) * (z3 - z2)
            e3 = (z3 - gz) * (x1 - x3) - (x3 - gx) * (z1 - z3)
            cov[ix0:ix1 + 1, iz0:iz1 + 1] |= (e1 >= 0) & (e2 >= 0) & (e3 >= 0)     # SM64's own floor winding test
        gap = np.zeros_like(cov)
        reach = CRACK_MAX // S
        for axis in (0, 1):
            lo, hi = np.zeros_like(cov), np.zeros_like(cov)
            for dd in range(1, reach + 1):
                lo |= np.roll(cov, dd, axis=axis)
                hi |= np.roll(cov, -dd, axis=axis)
            gap |= ~cov & lo & hi
        cells = np.argwhere(gap)
        if len(cells) == 0:
            continue
        P = np.stack([xs[cells[:, 0]], np.full(len(cells), L + 60.0), zs[cells[:, 1]]], axis=1)
        keep = np.ones(len(P), dtype=bool)
        for w in np.nonzero(is_wall & (T[:, :, 1].min(axis=1) <= L + 60) & (T[:, :, 1].max(axis=1) >= L + 60))[0]:
            a, b = T[w][np.argsort(T[w][:, 1])][[0, 2]]     # the wall's horizontal extent (its lowest / highest corners)
            xa, xb = T[w][:, 0].min() - 35, T[w][:, 0].max() + 35
            za, zb = T[w][:, 2].min() - 35, T[w][:, 2].max() + 35
            m = keep & (P[:, 0] > xa) & (P[:, 0] < xb) & (P[:, 2] > za) & (P[:, 2] < zb)
            if not m.any():
                continue
            # distance in plan from the wall's footprint segment (the two corners farthest apart in x / z)
            pts2 = T[w][:, [0, 2]]
            dmax, seg = -1.0, None
            for i0 in range(3):
                for i1 in range(i0 + 1, 3):
                    dd = np.linalg.norm(pts2[i0] - pts2[i1])
                    if dd > dmax:
                        dmax, seg = dd, (pts2[i0], pts2[i1])
            p0, p1 = seg
            sub = np.nonzero(m)[0]
            q = P[sub][:, [0, 2]]
            dv = p1 - p0
            L2 = float(dv @ dv) or 1.0
            t = np.clip(((q - p0) @ dv) / L2, 0.0, 1.0)
            dist = np.linalg.norm(q - (p0 + t[:, None] * dv), axis=1)
            keep[sub[dist < 30]] = False
        pts = P[keep]
        if len(pts):
            out.append((L, int(pts[:, 0].min()), int(pts[:, 0].max()), int(pts[:, 2].min()), int(pts[:, 2].max()), len(pts)))
    return out


def check_built(lua, L, bad):
    if not os.path.exists(COLLISION):
        print("check_libwest_points: levels/bbh not built yet: collision checks skipped")
        return bad, 0
    col = Collision(COLLISION)
    n = 0

    def floor_at(name, X, Y, Z):
        nonlocal bad, n
        n += 1
        h = col.find_floor(X, Y + 200, Z)
        if h is None or abs(h - Y) > TOL:
            print("BUILT %s (%d, %d, %d): floor %s" % (name, X, Y, Z, "none" if h is None else "%.0f" % h))
            bad += 1
    for k in ("spawn", "climb_goal", "esc_foot", "esc_top", "door_nw", "door_ne", "tower_door", "f4_door_w", "f4_door_e",
              "f6_door_w", "f6_door_e", "run_start", "cup_stand", "f2_door_w", "f2_door_e", "desk", "release_w", "release_e",
              "shaft_door"):
        floor_at(k, *lua[k])
    for k in ("door_nw", "door_ne"):
        floor_at(k + " (F3)", lua[k][0], lua["y_f3"], lua[k][2])
        floor_at(k + " (roof)", lua[k][0], lua["y_f4"], lua[k][2])
    for s in lua["hide_spots"]:
        floor_at("hide spot " + s["name"], s["x"], s["y"], s["z"])
    for b in lua["boos1"] + lua["boos2"]:
        floor_at("Boo " + b["name"], b["x"], b["y"], b["z"])
    for i, ld in enumerate(lua["ladders"]):
        n += 1
        hx, hz = LADDER_HALF_X_M * 100, LADDER_HALF_Z_M * 100
        hits = col.in_box(ld["x0"] + 1, ld["x1"] - 1, ld["y"] - 51, ld["y"] + 160, ld["z"] - hz, ld["z"] + hz)
        if hits:
            print("BUILT ladders[%d]: %d static triangles in its travel box" % (i + 1, len(hits)))
            bad += 1
    # act 3: the stacks block the lantern (the collision ray of its line of sight): from the aisle in front of each
    # ladder's 3 m range, a chest-high line across the range to the aisle behind it hits the range's collision
    for i, ld in enumerate(lua["ladders"]):
        n += 1
        xm = (ld["x0"] + ld["x1"]) / 2.0
        y = ld["y"] - int(LADDER_TOP_M * 100) + 100
        if not col.segment_hits((xm, y, ld["z"] + 60), (xm, y, ld["z"] - 260)):
            print("BUILT ladders[%d]: nothing blocks a line of sight across its range (shelves must stop the lantern)" % (i + 1))
            bad += 1
    for name, star, frm in (("climb_star", lua["climb_star"], lua["y_f6"]), ("desk_star", lua["desk_star"], lua["y_f2"])):
        n += 1
        top = (star[1] + frm) / 2.0 + STAR_HUMP + STAR_SIZE
        hs = col.surfaces_in_column(star[0], star[2], star[1] + 10, top, 40)
        if hs:
            print("BUILT %s: static surfaces in its spawn column at %s" % (name, sorted(set(int(h) for h in hs))[:5]))
            bad += 1
    # the doorways the acts need are open
    need = [("stair_w", "F5_locked"), ("stair_e", "F5_locked"),
            ("stair_w", "F2"), ("stair_e", "F2"), ("stair_w", "F4_east"), ("stair_e", "F4"), ("stair_w", "F6"),
            ("stair_e", "F6"), ("stair_nw", "F1"), ("stair_nw", "F2"), ("stair_nw", "F3"), ("stair_nw", "F4_roof"),
            ("stair_ne", "F1"), ("stair_ne", "F2"), ("stair_ne", "F3"), ("stair_ne", "F4_roof")]
    for core, key in need:
        n += 1
        a, b, _ = L.door(core, key)
        fid = key.split("_")[0]
        ga, gb = (L.gx(a[0]), L.gz(a[1])), (L.gx(b[0]), L.gz(b[1]))
        y = L.zfloor(fid) * 100
        if col.crosses_segment(ga, gb, y + 40, y + 190):
            print("BUILT %s %s door is closed (static wall in the doorway)" % (core, key))
            bad += 1
    dn = [o for o in L.floors["F4"]["openings"] if o["id"] == "door_terrace_n"][0]
    n += 1
    if col.crosses_segment((L.gx(dn["a_m"][0]), L.gz(dn["a_m"][1])), (L.gx(dn["b_m"][0]), L.gz(dn["b_m"][1])), 1840, 1990):
        print("BUILT the 4th floor's north terrace door is closed")
        bad += 1
    # door walk-through (fix round): no crack in any doorway, both ways
    nd = 0
    if os.path.exists(POINTS_JSON):
        doors = door_anchors(POINTS_JSON)
        if not any(nm == "elevator_a_door_F1" for nm, _, _ in doors):
            print("BUILT door walk: elevator_a_door_F1 missing from %s" % os.path.relpath(POINTS_JSON, ROOT))
            bad += 1
        for nm, (X, Y, Z), yaw in doors:
            for yw, way in ((yaw, "forward"), ((yaw + 0x8000) & 0xFFFF, "back")):
                n += 1
                nd += 1
                for c in walk_cracks(col, X, Y, Z, yw):
                    print("BUILT door walk %s %s: %s" % (nm, way, c))
                    bad += 1
    # floor-crack scan (fix round)
    cr = crack_scan(COLLISION, [int(lua["y_f%d" % k]) for k in range(1, 7)])
    if cr is None:
        print("check_libwest_points: numpy missing: floor-crack scan skipped")
    else:
        n += 1
        for (lv, x0, x1, z0, z1, cells) in cr:
            print("BUILT floor crack at y %d: x %d..%d z %d..%d (%d cells of 5 units, no wall over it)" % (lv, x0, x1, z0, z1, cells))
            bad += 1
    print("check_libwest_points: %d collision checks on %s (%d triangles; %d door walks, crack scan %s)"
          % (n, os.path.relpath(COLLISION, ROOT), len(col.tris), nd, "skipped" if cr is None else "6 storeys"))
    return bad, n


# ------------------------------------------------------------------------------------------- print
def fmt_lua(src):
    lines = []
    for k, v in src.items():
        if isinstance(v, int):
            lines.append("    %s = %d," % (k, v))
        elif isinstance(v, tuple):
            lines.append("    %s = { x = %d, y = %d, z = %d }," % (k, v[0], v[1], v[2]))
        elif isinstance(v, dict):
            lines.append("    %s = { %s }," % (k, ", ".join("%s = %d" % kv for kv in v.items())))
        else:
            lines.append("    %s = {" % k)
            for row in v:
                parts = []
                for kk, vv in row.items():
                    parts.append('%s = "%s"' % (kk, vv) if isinstance(vv, str) else "%s = %d" % (kk, vv))
                lines.append("        { %s }," % ", ".join(parts))
            lines.append("    },")
    return "\n".join(lines)


def main():
    use_json = "--layout" not in sys.argv
    src, why, L, _ = sources(use_json)
    if "--print" in sys.argv:
        print(fmt_lua(src))
        for k, w in why.items():
            print("-- %s: %s" % (k, w))
        return 0
    lua = lua_points()
    bad = compare(src, lua)
    if bad:
        print("check_libwest_points: %d value(s) drifted from their sources (--print shows fresh ones)" % bad)
        return 1
    lb, trip, est = layout_sanity(lua, L)
    bad += lb
    bad, _ = check_built(lua, L, bad)
    if bad:
        print("check_libwest_points: %d finding(s)" % bad)
        return 1
    print("check_libwest_points: OK (%d values of LIBWEST_POINTS match %s; layout checks passed; coffee run %.0f m "
          "round trip, ~%.0f s at %.1f m/s, par %d s)" % (len(src), "data/uf/libwest_points.json + data/uf/libwest_layout.json"
                                                         if os.path.exists(POINTS_JSON) and use_json else "data/uf/libwest_layout.json",
                                                         trip, est, RUN_SPEED_MS, PAR_S))
    return 0


if __name__ == "__main__":
    sys.exit(main())
