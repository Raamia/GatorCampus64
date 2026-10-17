"""Course 2, AREA 2: the J. WAYNE REITZ UNION INTERIOR (level slot wf, LEVEL_WF area 2), built from the real
building plan (data/uf/reitz_interior_layout.json, docs/reitz_interior_layout.md: the Reitz Union's public indoor
wayfinding geometry registered to the OSM footprint, room names checked against the 2025 printed level maps) and
109 reference photos (reference/interiors/reitz/index.json), with the interior kit (tools/campus/interior_kit.py)
and the Reitz kit (tools/campus/interior_kit_reitz.py: int_ru_* materials, plan geometry, photo-matched props).

Pure Python (no bpy): build() returns a Reitz object holding an interior_kit.Kit of the whole interior (map metres,
z up, campus.json origin), the per-group Lighting for the vertex-colour bake, the instant-warp entrance strips,
the elevator teleport pads, the pickups plan, the preview cameras and the build notes.
tools/campus/build_stage.py reitz_eng turns it into area 2 of mods/sgl64/levels/wf/ (build_interior.build_area);
tools/campus/build_interior.py -- reitz --no-export --previews renders it alone (previews only: area 2 is only
ever exported together with area 1 by build_stage.py).

    tools/.venv/bin/python -I tools/campus/interiors/reitz.py --selftest     (geometry checks, no Blender)

THE SAME FRAME AS AREA 1. Area 2 uses the outdoor stage's centre (stages.json reitz_eng, (-470, -293)), so a map
point is the same game point in both areas. The doors of the exterior landmark (area 1, landmarks/
reitz_reitz_union.py) and the doors in here line up in plan: walking through one is a vanilla INSTANT_WARP
(floor types SURFACE_INSTANT_WARP_1B..1E) with zero horizontal offset, only the vertical offset between the
flattened outdoor grade and the real levels (ENTRANCES below). The strip that warps IN lies just inside the door
line in area 1; the strip that warps OUT lies just outside it in area 2, so a step never bounces back.

Vertical frame (game metres; real ~4.5 m floor-to-floor, NOTES): LL -6, G 0, L1 6, L2 12, L3 18 (the roof of the
main building at 24), the tower L4 24, hotel L5 29, L6 34 (roof 39). 5.4 m clear under 0.6 m slabs (4.4 m in the
tower). Plans 1:1.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))           # tools/campus/interiors
CAMPUS_TOOLS = os.path.dirname(HERE)                        # tools/campus
ROOT = os.path.abspath(os.path.join(CAMPUS_TOOLS, "..", ".."))
if CAMPUS_TOOLS not in sys.path:
    sys.path.insert(0, CAMPUS_TOOLS)

import interior_kit_reitz as R  # noqa: E402  (registers the int_ru_* materials first)
import interior_kit as K  # noqa: E402

LAYOUT_PATH = os.path.join(ROOT, "data", "uf", "reitz_interior_layout.json")
CAMPUS_PATH = os.path.join(ROOT, "data", "uf", "campus.json")

# ------------------------------------------------------------------ stage identity (docs/flow.md 9.2)
KEY = "reitz"
SLOT = "wf"
AREA = 2
LEVEL_CONST = "LEVEL_WF"
COURSE_CONST = "COURSE_WF"
DOOR = 2
CENTER = (-470.0, -293.0)              # stages.json reitz_eng centre = area 1's frame (instant warps keep x, y)
MUSIC = "SEQ_LEVEL_HOT"                # the stage's music: an instant warp never changes the music (area.c)
TERRAIN = "TERRAIN_STONE"              # indoor footsteps (area 1 keeps TERRAIN_GRASS)
BACKGROUND = "OCEAN_SKY"
FOG_RGB = (200, 206, 216)              # the stage's haze (build_stage patches every area with the same fit)
COL_SLIDE = "COL slide"
SPAWN_NOTE = ("area 2 spawn 0x0A (bhvSpinAirborneWarp) in the Ground-level atrium lounge; only debug warps "
              "(warp_to_warpnode / area 2) use it: players walk in through the real doors (instant warps)")
POINTS_COORDINATES_MAP_M = ("x = east, y = north, z = game metres above the Ground Level floor (LL -6, G 0, L1 6, L2 12, "
                            "L3 18, L4 24, L5 29, L6 34); origin = Century Tower; same frame as area 1")
POINTS_NOTE = "Reitz Union interior (area 2 of levels/wf), measured on the built collision of area 2."
PREVIEW_OVERVIEW = ((60.0, -95.0, 120.0), (60.0, 5.0, 8.0), 40.0)

# ------------------------------------------------------------------ vertical frame
FLOORS = ("LL", "G", "L1", "L2", "L3", "L4", "L5", "L6")
Z = {"LL": -6.0, "G": 0.0, "L1": 6.0, "L2": 12.0, "L3": 18.0, "L4": 24.0, "L5": 29.0, "L6": 34.0}
SLAB = 0.6
CLEAR = {f: 5.4 for f in FLOORS}
CLEAR.update({"L4": 4.4, "L5": 4.4, "L6": 4.4})
ROOF_Z = {"main": 24.0, "tower": 39.0}
ATRIUM_TOP = 25.6                      # cedar ceiling over the atrium voids (L3 ceiling 23.4 + a 2.2 m clerestory)
WALL_T = 0.20                          # interior partitions (visual faces at +-0.1 m of the plan centre-line)
EXT_T = 0.30                           # exterior walls
DOOR_H = 2.6                           # door head (real 2.13 m doors; camera + co-op)
GLASS_DOOR_H = 3.0
RAIL_H = 1.07                          # 42" guard rail
FLOOR_STEP = 4.5                       # visual floor / ceiling split (vertex-colour bake resolution)
CEIL_STEP = 6.0
FASCIA = 1.2                           # atrium balcony fascia depth below the floor (white curved bands)

# the zones that are overlays / duplicates in the plan data (not floors of their own)
OVERLAY_ZONES = {"food_court", "dance_studios"}
WALK_TYPES = {"corridor", "atrium_floor", "vestibule", "meeting_room", "ballroom", "auditorium", "gallery", "chamber",
              "game_room", "esports", "cafe_bar", "hotel_lobby", "studio", "event_room"}
SEALED_IDS = {"sg_print_lab", "g_corridor_03", "l1_corridor_05", "l2_corridor_07", "l3_corridor_01"}
OPEN_IDS = {"hotel_room_516", "hotel_room_501_502", "l5_hotel_balcony_8"}
ATRIUM_SEALED_VOIDS = {"l3_atrium_void_02"}
VOID_TYPES = {"atrium_void"}
DOUBLE_TYPES = {"double_height"}
OUTSIDE_TYPES = {"adjacent_building", "exterior_walkway", "balcony"}

# ------------------------------------------------------------------ entrances (area 1 <-> area 2 instant warps)
# a, b: the door line (map m), n: outward normal; area-1 strip A goes from the line INTO the building (depth_in),
# area-2 strip B from the line OUT (depth_out). z1 = area 1 floor at the door, z2 = area 2 floor.
# index: instant-warp index (SURFACE_INSTANT_WARP_1B + index); the same index in both areas, opposite offsets.
ENTRANCES = [
    {"id": "north", "name": "North Entrance (Level 1, 2016 wing)", "index": 1,
     "a": (-384.6, -258.0), "b": (-376.3, -258.0), "n": (0.0, 1.0), "z1": 0.0, "z2": 6.0,
     "depth_in": 2.2, "depth_out": 2.4, "floor": "L1",
     "note": "the four door leaves at the back of the recess under the 2016 wing's overhang (area 1 carves the "
             "recess: landmarks/reitz_reitz_union.py); inside the vestibule, Info Desk and the atrium balconies"},
    {"id": "south_terrace", "name": "South Terrace doors (Ground)", "index": 2,
     "a": (-388.2, -286.3), "b": (-381.2, -286.3), "n": (0.0, -1.0), "z1": 2.0, "z2": 0.0,
     "depth_in": 2.0, "depth_out": 2.3, "floor": "G",
     "note": "Ground-level doors from the South Terrace / amphitheater into the atrium lounge (J. WAYNE REITZ UNION "
             "letters above; ru_south_ground_entrance). Area 1's terrace deck is 2.0 m (flattened site)."},
    {"id": "south_exit_l1", "name": "Level 1 south exit (the food court door of area 1)", "index": 3,
     "a": (-377.66, -288.84), "b": (-374.46, -288.88), "n": (0.0, -1.0), "z1": 2.0, "z2": 6.0,
     "depth_in": 2.0, "depth_out": 2.2, "floor": "L1",
     "note": "area 1's former FOOD COURT door (OSM entrance 11261533459) on the 2016 wing's south face: in here the "
             "Level 1 landing of the terrace stairs and the South Exit Level 1 doors into the food court hall",
     "porch": [(-378.4, -288.84), (-370.4, -288.95), (-370.4, -283.0), (-378.4, -283.0)],
     "open_doors": [(-373.5, -283.0, -371.1, -283.0)]},
    {"id": "north_ground", "name": "Ground north doors (core, under the Level 1 bridge)", "index": 0,
     "a": (-420.4, -244.5), "b": (-417.8, -244.5), "n": (0.0, 1.0), "z1": 0.0, "z2": 0.0,
     "depth_in": 2.0, "depth_out": 2.3, "floor": "G",
     "note": "the Ground-level north door east of SG Bike Repair (plan door g_ext_door_07), into the corridor that "
             "runs down to the hotel reception / atrium corridor (area 1: under the north colonnade canopy)"},
]
WARP_MAT = {0: "COL warp_1B", 1: "COL warp_1C", 2: "COL warp_1D", 3: "COL warp_1E"}
WARP_UP = 0.02                         # warp floors 2 cm over the floors they meet (find_floor takes the highest)
TEXTURE_SCRIPT = "interior_kit_reitz.py"   # build_stage runs it (--textures) before building this area
WARP_SURFACE = {0: "SURFACE_INSTANT_WARP_1B", 1: "SURFACE_INSTANT_WARP_1C", 2: "SURFACE_INSTANT_WARP_1D",
                3: "SURFACE_INSTANT_WARP_1E"}


def instant_warps():
    """[(index, area-1 -> area-2 offset in game units (x, y, z))] (area 2 uses the negated offsets)."""
    out = {}
    for e in ENTRANCES:
        dz = e["z2"] - e["z1"]
        off = (0, int(round(dz * 100)), 0)
        if e["index"] in out and out[e["index"]] != off:
            raise ValueError(f"entrance {e['id']}: index {e['index']} already has offset {out[e['index']]}")
        out[e["index"]] = off
    return sorted(out.items())


# ------------------------------------------------------------------ elevators: Blue bank teleport cabs
# Two of the four Blue cars per floor are open: the NORTH-WEST car goes UP a floor, the NORTH-EAST car DOWN
# (vanilla bhvFadingWarp pads: stand still in the car -> teleport fade to the paired car). Node ids 0x40+.
BLUE_CARS = {"up": (-448.8, -269.6), "down": (-441.3, -269.6)}
BLUE_ORDER = ("LL", "G", "L1", "L2", "L3", "L4", "L5", "L6")
PAD_NODE0 = 0x40
PAD_RADIUS_DM = 7

NOTES = {
    "frame": "Area 2 shares area 1's frame (centre (-470, -293)); the doors line up in plan, instant warps add "
             "only the vertical offset between area 1's flattened grade and the real level (+6 north entrance, -2 "
             "South Terrace, +4 Level 1 south exit, 0 Ground north door).",
    "floor_height": "Floors 6.0 m apart (real ~4.5 m), 5.4 m clear; the tower floors (L4-L6) 5.0 m apart (real "
                    "~3.2 m hotel floors), 4.4 m clear. Plans 1:1 (the registered wayfinding geometry).",
    "grand_ballroom": "Double height: L2 floor to the L3 roof line, 11.4 m clear (real ~7 m, estimated from photos).",
    "rion_ballroom": "Top floor, so its ceiling rises 2 m above the L3 corridor ceiling (7.4 m clear).",
    "atrium": "Ground to a cedar ceiling at 25.6 m over the voids (L3 ceiling + a 2.2 m clerestory band).",
    "sealed": "Offices, restrooms, kitchens, back-of-house rooms, the stair shafts and most hotel rooms are closed "
              "doors (no photos; not public). Open: corridors, the atrium, vestibules, every meeting room, the "
              "ballrooms, the Auditorium, the Gallery, the Senate Chamber, the Game Room, the Gator Esports Center, "
              "Orange & Brew, the Arts & Crafts Center and the dance studios, the Level 4 event rooms, hotel rooms "
              "516 and 501/502 and a balcony.",
    "elevators": "The Blue elevators (the only bank that reaches the hotel) are vanilla teleport pads: two open cars "
                 "per floor (north-west UP, north-east DOWN). The Orange and service elevators are closed.",
    "brands": "Food court storefronts carry generic signs (BURGERS, PIZZA, WOK, ...) in the real counters' colours; "
              "no brand marks.",
    "inferred": "No public photo of: the hotel reception, the Info Desk, Orange & Brew, Subway / The Market, the "
                "stairwells, restrooms, hotel corridors. Those are drawn plainly (the plan + the house finishes).",
}


# ================================================================== layout
class Zone:
    __slots__ = ("id", "name", "type", "poly", "bb", "area", "cls", "fid", "style")

    def __init__(self, z, fid):
        self.id, self.name, self.type = z["id"], z["name"], z["type"]
        self.poly = R.ccw([tuple(p) for p in z["poly_m"]])
        self.bb = R.bbox(self.poly)
        self.area = abs(R.signed_area(self.poly))
        self.fid = fid
        self.cls = "S"
        self.style = None

    def contains(self, p):
        x, y = p
        b = self.bb
        return b[0] - 1e-6 <= x <= b[2] + 1e-6 and b[1] - 1e-6 <= y <= b[3] + 1e-6 and R.pip(p, self.poly)


class Floor:
    def __init__(self, fd, footprint):
        self.id = fd["id"]
        self.z = Z[self.id]
        self.clear = CLEAR[self.id]
        self.data = fd
        self.outline = R.ccw([tuple(p) for p in fd["outline_m"]])
        self.holes = [R.ccw([tuple(p) for p in h]) for h in fd["holes_m"]]
        self.zones = []
        for z in fd["zones"]:
            if z["id"] in OVERLAY_ZONES:
                continue
            zn = Zone(z, self.id)
            c = R.centroid(zn.poly)
            inside_fp = R.pip(c, footprint) or R.poly_dist(c, footprint) < 2.5
            if z["type"] in VOID_TYPES:
                zn.cls = "V"
            elif z["type"] in DOUBLE_TYPES:
                zn.cls = "S"           # the Grand Ballroom's upper volume: no Level 3 floor (the L2 room rises)
            elif z["id"] in OPEN_IDS:
                zn.cls = "W"
            elif z["type"] in OUTSIDE_TYPES or not inside_fp:
                zn.cls = "O"
            elif z["type"] in WALK_TYPES and z["id"] not in SEALED_IDS:
                zn.cls = "W"
            else:
                zn.cls = "S"
            self.zones.append(zn)
        self.overlays = {z["id"]: R.ccw([tuple(p) for p in z["poly_m"]]) for z in fd["zones"] if z["id"] in OVERLAY_ZONES}
        # the atrium voids: the plan draws the scissor stair as a chevron cut into the void; the void is its hull
        # (the stairs are built by dress_atrium). The small oval void on L3 lies inside a closed suite: sealed.
        for zn in self.zones:
            if zn.cls == "V":
                if zn.id in ATRIUM_SEALED_VOIDS:
                    zn.cls = "S"
                    continue
                zn.poly = R.ccw(R.convex_hull(zn.poly))
                zn.bb = R.bbox(zn.poly)
        self.holes = [R.ccw(R.convex_hull(h)) for h in self.holes if not any(R.pip(R.centroid(h), z.poly) for z in self.zones
                                                                         if z.id in ATRIUM_SEALED_VOIDS)]
        self.voids = [z.poly for z in self.zones if z.cls == "V"]
        for h in self.holes:
            if not any(R.pip(R.centroid(h), v) for v in self.voids):
                self.voids.append(h)
        self.no_walls = []              # regions where plan walls are dropped (the stair chevron, set by Reitz)
        self.open_ww = []               # regions where walkable-to-walkable plan walls are dropped
        self.walls = [tuple(w) for w in fd["walls_m"]]
        self.doors = [tuple(d) for d in fd["doors_m"]]

    def zone_at(self, p):
        best = None
        for z in self.zones:
            if z.contains(p) and (best is None or z.area < best.area):
                best = z
        return best

    def cls_at(self, p):
        for v in self.voids:
            if R.pip(p, v):
                return "V", None
        z = self.zone_at(p)
        if z is None:
            return "O", None
        return z.cls, z

    def walk_zones(self):
        return [z for z in self.zones if z.cls == "W"]

    def zone(self, zid):
        return next((z for z in self.zones if z.id == zid), None)


def load_layout(path=LAYOUT_PATH):
    with open(path) as f:
        return json.load(f)


# ================================================================== styles
def zone_style(z):
    """Floor / wall / ceiling materials, ceiling height and light kind of a walkable zone (from the photos)."""
    fid, t, zid = z.fid, z.type, z.id
    s = {"floor": "int_ru_terrazzo", "wall": "int_ru_wall", "ceil": "int_ru_tile_ceiling", "clear": CLEAR[fid],
         "light": "troffer", "spacing": 3.6, "accent": None, "base": "int_ru_black", "tint": None}
    if t == "corridor":
        if fid == "LL":
            s.update(floor="int_ru_fc_tile")
        elif fid == "L4":
            s.update(floor="int_ru_carpet_grey", wall="int_ru_wall_grey")
        elif fid in ("L5", "L6"):
            s.update(floor="int_ru_carpet_hotel", wall="int_ru_wall_cream", light="down", spacing=3.0)
        else:
            s.update(light="down", spacing=3.4)
    elif t == "meeting_room":
        s.update(floor="int_ru_carpet_meeting", light="linear", spacing=2.8,
                 accent="int_ru_wall_royal" if fid == "G" else "int_ru_wall_greyblue")
    elif t == "ballroom":
        if zid == "grand_ballroom":
            s.update(floor="int_ru_carpet_ballroom", wall="int_ru_wall_grey", ceil="int_ru_tile_ceiling",
                     clear=Z["L3"] + CLEAR["L3"] - Z["L2"], light="coffer", spacing=5.0)
        else:
            s.update(floor="int_ru_maple", wall="int_ru_wall", clear=CLEAR["L3"] + 2.0, light="linear", spacing=3.6)
    elif t == "auditorium":
        s.update(floor="int_ru_carpet_aud", wall="int_ru_wall_grey", ceil="int_ru_slat_dark", light="cove",
                 spacing=3.0)
    elif t == "gallery":
        s.update(floor="int_ru_concrete_dark", ceil="int_ru_black", light="track", spacing=2.4)
    elif t == "chamber":
        s.update(floor="int_ru_carpet_aud", wall="int_ru_wall_cream", light="down", spacing=2.6)
    elif t == "game_room":
        s.update(floor="int_ru_plank", wall="int_ru_wall_navy", light="troffer", spacing=3.6, base="int_ru_black")
    elif t == "esports":
        s.update(floor="int_ru_concrete_dark", wall="int_ru_hex", ceil="int_ru_black", light="esports", spacing=3.0)
    elif t == "cafe_bar":
        s.update(floor="int_ru_terrazzo", wall="int_ru_wall_cream", light="down", spacing=3.0)
    elif t == "hotel_lobby":
        s.update(floor="int_ru_terrazzo", wall="int_ru_wall_cream", light="down", spacing=2.8)
    elif t == "studio":
        if zid.startswith("dance"):
            s.update(floor="int_ru_dance", wall="int_ru_wall", light="linear", spacing=3.0)
        else:
            s.update(floor="int_ru_paving", wall="int_ru_wall", light="troffer")
    elif t == "event_room":
        if zid == "arredondo_cafe":
            s.update(floor="int_ru_carpet_olive", wall="int_ru_wall_cream", light="down", spacing=2.8)
        else:
            s.update(floor="int_ru_carpet_grey", wall="int_ru_wall_greyblue", light="down", spacing=2.6)
    elif t == "hotel_room":
        s.update(floor="int_ru_carpet_hotel", wall="int_ru_wall_cream", accent="int_ru_wall_royal", light="lamp",
                 ceil="int_ru_white")
    elif t == "balcony":
        s.update(floor="int_ru_paving", wall="int_ru_brick", ceil="int_ru_soffit", light="none")
    elif t in ("vestibule", "atrium_floor"):
        s.update(light="down", spacing=3.0)
    elif t == "elevator_car":
        s.update(floor="int_ru_carpet_grey", wall="int_ru_steel", ceil="int_ru_white", light="car", clear=2.7,
                 base="int_ru_steel")
    if fid in ("L4", "L5", "L6") and t != "hotel_room":
        s["clear"] = min(s["clear"], CLEAR[fid])
    return s


# ================================================================== the build
class Reitz:
    def __init__(self, layout):
        self.layout = layout
        self.footprint = R.ccw([tuple(p) for p in layout["footprint"]["poly_m"]])
        self.floors = {f["id"]: Floor(f, self.footprint) for f in layout["floors"]}
        # Ground: the plan's stair chevron walls inside the atrium (under the Level 1 voids) are dropped
        # (and the free-standing partitions between the two lounge floors): walkable-to-walkable runs inside the hull
        # of both Level 1 voids are dropped; walls of closed rooms (the Orange & Brew restroom block) stay
        l1v = self.floors["L1"].voids
        self.floors["G"].no_walls = [R.shrink(v, 0.3) for v in l1v]
        self.floors["G"].open_ww = [R.ccw(R.convex_hull([p for v in l1v for p in v]))]
        self.cars = {}
        for i, fid in enumerate(BLUE_ORDER):
            F = self.floors[fid]
            for kind, pt in BLUE_CARS.items():
                if (kind == "up" and i == len(BLUE_ORDER) - 1) or (kind == "down" and i == 0):
                    continue
                zn = F.zone_at(pt)
                if zn is None or zn.type != "elevator":
                    continue
                zn.cls = "W"
                zn.type = "elevator_car"
                self.cars[(fid, kind)] = zn
        for f in self.floors.values():
            for z in f.zones:
                if z.cls == "W":
                    z.style = zone_style(z)
        self.kit = K.Kit()
        self.lighting = {}
        self.points = {}
        self.pickups = []
        self.views = []
        self.notes = dict(NOTES)
        self.stats = {}
        self.pads = []            # elevator teleport pads
        self.warp_strips = []     # area-2 instant warp strips (for the report)
        self.extra_objects = []
        self.layout_out = None
        self.door_open = {}       # (fid, door index) -> kind
        self.lights_skip = set()

    def kit_add(self, prop, group, tag=None, x=0.0, y=0.0, z=0.0, facing=0.0):
        return self.kit.add(prop, x, y, z, facing, tag=tag, group=group)


# ---------------------------------------------------------------- wall runs
def _side_samples(F, a, b, off):
    """Classes of the two sides of wall a-b sampled every ~0.5 m: [(s0, s1, (clsL, zoneL), (clsR, zoneR))] runs."""
    L = math.dist(a, b)
    if L < 0.05:
        return []
    dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    lx, ly = -dy, dx            # left normal
    n = max(1, int(math.ceil(L / 0.5)))
    samples = []
    for k in range(n):
        s = (k + 0.5) * L / n
        p = (a[0] + dx * s, a[1] + dy * s)
        cl = F.cls_at((p[0] + lx * off, p[1] + ly * off))
        cr = F.cls_at((p[0] - lx * off, p[1] - ly * off))
        samples.append((k * L / n, (k + 1) * L / n, cl, cr))
    runs = []
    for s0, s1, cl, cr in samples:
        key = (cl[0], cl[1].id if cl[1] else None, cr[0], cr[1].id if cr[1] else None)
        if runs and runs[-1][4] == key:
            runs[-1][1] = s1
        else:
            runs.append([s0, s1, cl, cr, key])
    return [(r[0], r[1], r[2], r[3]) for r in runs]


def _door_cuts(F, a, b):
    """Door intervals (s0, s1, door index, exterior flag) lying on wall a-b."""
    L = math.dist(a, b)
    if L < 0.05:
        return []
    dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    out = []
    for i, d in enumerate(F.doors):
        p, q = (d[0], d[1]), (d[2], d[3])
        if R.seg_point_dist(p, a, b) > 0.2 or R.seg_point_dist(q, a, b) > 0.2:
            continue
        s0 = (p[0] - a[0]) * dx + (p[1] - a[1]) * dy
        s1 = (q[0] - a[0]) * dx + (q[1] - a[1]) * dy
        s0, s1 = min(s0, s1), max(s0, s1)
        s0, s1 = max(0.0, s0), min(L, s1)
        if s1 - s0 > 0.3:
            out.append((s0, s1, i, int(d[4]) if len(d) > 4 else 0))
    return out


# ---------------------------------------------------------------- exterior wall look (from the photos)
def _region(x, y):
    """Which part of the building a plan point is in (landmark blocks): E (2016 wing), CURVE (curved SE glass
    facade of the south wing), S (south wing), C (1967 core), W (ballroom wing), T (tower)."""
    if x > -410.6:
        return "E"
    if y < -281.0:
        if x > -421.5 and y > -320.0:
            return "CURVE"
        return "S"
    if x < -462.0:
        return "W"
    return "C"


def window_spec(fid, a, b, zone):
    """(sill, head, kind) of the windows in an exterior wall a-b of a walkable zone, or None.
    kind: curtain (floor-to-ceiling glass with mullions), ribbon (a horizontal band), clerestory."""
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    reg = _region(mx, my)
    zid = zone.id if zone else ""
    clear = zone.style["clear"] if zone is not None and zone.style else CLEAR[fid]
    if fid in ("L5", "L6"):
        return (0.9, 3.2, "ribbon")
    if fid == "L4":
        return (0.25, clear - 0.35, "curtain")
    if fid == "LL":
        return None
    if reg == "E":
        if fid == "G":
            return (0.0, 3.2, "curtain") if zid == "south_terrace_vestibule" else None
        return (0.0, clear, "curtain")
    if reg == "CURVE":
        return (0.0 if fid in ("G", "L1") else 0.6, clear - (0.0 if fid in ("G", "L1") else 0.4), "curtain")
    if zid == "grand_ballroom":
        return (8.6, 10.6, "clerestory") if my > -255.0 else None
    if zid == "game_room":
        return (2.7, 3.7, "ribbon")
    if zid in ("gator_esports_center", "auditorium", "the_gallery", "senate_chamber"):
        return None
    if fid == "L3" and zid.startswith("meeting_33"):
        return (0.8, 3.9, "curtain")
    if fid == "L1":
        return (0.0, 3.4, "curtain")
    if fid in ("L2", "L3"):
        return (1.0, 3.2, "ribbon")
    return (1.0, 3.0, "ribbon")


def facade_mat(fid, a, b):
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    reg = _region(mx, my)
    if reg == "E" and fid != "G":
        return "int_ru_white"
    if reg == "CURVE":
        return "int_ru_white"
    if fid in ("L4", "L5", "L6"):
        return "int_ru_brick"
    return "int_ru_brick"


# ---------------------------------------------------------------- generic floor pieces
def _wall_ao(z, z0, z1):
    k = 1.0 - 0.28 * max(0.0, 1.0 - (z - z0) / 0.9)
    k *= 1.0 - 0.10 * max(0.0, 1.0 - (z1 - z) / 0.8)
    return k


def wall_face(V, a, b, z0, z1, mat, step=5.0, base=None, base_h=0.10, tint=None, holes=()):
    """Interior wall face a -> b (normal on the right), split every `step` m (vertex bake) with a dark base strip;
    holes: [(s0, s1, h0, h1)] rectangles left open (door gaps / windows)."""
    L = math.dist(a, b)
    if L < 0.02 or z1 - z0 < 0.02:
        return
    dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    cuts_s = {0.0, L}
    for h in holes:
        cuts_s.update((max(0.0, min(L, h[0])), max(0.0, min(L, h[1]))))
    n = int(math.ceil(L / step))
    cuts_s.update(L * k / n for k in range(1, n))
    ss = sorted(cuts_s)
    cuts_z = {z0, z1}
    if base:
        cuts_z.add(z0 + base_h)
    for h in holes:
        cuts_z.update((max(z0, min(z1, h[2])), max(z0, min(z1, h[3]))))
    zz = sorted(c for c in cuts_z if z0 - 1e-6 <= c <= z1 + 1e-6)
    for i in range(len(ss) - 1):
        s0, s1 = ss[i], ss[i + 1]
        if s1 - s0 < 1e-4:
            continue
        sm = (s0 + s1) / 2
        for j in range(len(zz) - 1):
            za, zb = zz[j], zz[j + 1]
            if zb - za < 1e-4:
                continue
            zm = (za + zb) / 2
            if any(h[0] < sm < h[1] and h[2] < zm < h[3] for h in holes):
                continue
            m = base if (base and zb <= z0 + base_h + 1e-6) else mat
            p0 = (a[0] + dx * s0, a[1] + dy * s0)
            p1 = (a[0] + dx * s1, a[1] + dy * s1)
            V.poly([(p0[0], p0[1], za), (p1[0], p1[1], za), (p1[0], p1[1], zb), (p0[0], p0[1], zb)], m,
                   ao=[_wall_ao(za, z0, z1), _wall_ao(za, z0, z1), _wall_ao(zb, z0, z1), _wall_ao(zb, z0, z1)],
                   tint=tint if m == mat else None)


def col_face(C, a, b, z0, z1, holes=(), step=10.24, mat=K.COL):
    """(C may be a list: the quads are appended for merge_col_walls)"""
    """Collision wall a -> b (normal on the right) with rectangular holes, split every `step` m."""
    L = math.dist(a, b)
    if L < 0.02:
        return
    dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    ss = {0.0, L}
    n = int(math.ceil(L / step))
    ss.update(L * k / n for k in range(1, n))
    for h in holes:
        ss.update((max(0.0, min(L, h[0])), max(0.0, min(L, h[1]))))
    ss = sorted(ss)
    zz = sorted({z0, z1} | {max(z0, min(z1, h[2])) for h in holes} | {max(z0, min(z1, h[3])) for h in holes})
    for i in range(len(ss) - 1):
        s0, s1 = ss[i], ss[i + 1]
        if s1 - s0 < 1e-4:
            continue
        sm = (s0 + s1) / 2
        p0 = (a[0] + dx * s0, a[1] + dy * s0)
        p1 = (a[0] + dx * s1, a[1] + dy * s1)
        for j in range(len(zz) - 1):
            za, zb = zz[j], zz[j + 1]
            if zb - za < 1e-4:
                continue
            zm = (za + zb) / 2
            if any(h[0] < sm < h[1] and h[2] < zm < h[3] for h in holes):
                continue
            q = [(p0[0], p0[1], za), (p1[0], p1[1], za), (p1[0], p1[1], zb), (p0[0], p0[1], zb)]
            if isinstance(C, list):
                C.append(q)
            else:
                C.poly(q, mat)


def merge_col_walls(quads, tol=0.02, min_len=0.35):
    """Join collinear, touching vertical collision quads with the same z range (one face per straight wall); pieces
    shorter than min_len (plan jogs between longer walls: Mario's 0.5 m radius cannot pass them) are dropped."""
    out = []
    groups = {}
    for q in quads:
        (x0, y0, za), (x1, y1, _), _, (_, _, zb) = q
        L = math.hypot(x1 - x0, y1 - y0)
        if L < min_len:
            continue
        dx, dy = (x1 - x0) / L, (y1 - y0) / L
        ang = round(math.degrees(math.atan2(dy, dx)) % 360.0, 1)
        off = round(-dy * x0 + dx * y0, 2)            # signed distance of the line from the origin
        groups.setdefault((ang, off, round(za, 3), round(zb, 3)), []).append((dx * x0 + dy * y0, dx * x1 + dy * y1, q))
    for (ang, off, za, zb), segs in groups.items():
        segs.sort()
        cur = None
        for s0, s1, q in segs:
            if cur is not None and s0 <= cur[1] + tol and s1 - cur[0] < 10.24:
                if s1 > cur[1]:
                    cur = [cur[0], s1, cur[2], q[1], q[2]]
                continue
            if cur is not None:
                out.append([cur[2], cur[3], cur[4], (cur[2][0], cur[2][1], cur[4][2])])
            cur = [s0, s1, q[0], q[1], q[2]]
        if cur is not None:
            out.append([cur[2], cur[3], cur[4], (cur[2][0], cur[2][1], cur[4][2])])
    return out


def door_leaves(V, a, b, z0, h, mat, off=0.03, frame="int_ru_steel"):
    """Closed door leaf / leaves (once-mapped door texture) on the face a -> b (normal right), with a frame."""
    w = math.dist(a, b)
    n = 2 if w > 1.35 else 1
    dx, dy = (b[0] - a[0]) / w, (b[1] - a[1]) / w
    for k in range(n):
        p0 = (a[0] + dx * w * k / n, a[1] + dy * w * k / n)
        p1 = (a[0] + dx * w * (k + 1) / n, a[1] + dy * w * (k + 1) / n)
        u0, u1 = (0.0, 1.0) if (k % 2 == 0) else (1.0, 0.0)
        R.panel(V, p0, p1, z0, z0 + h, mat, off=off, u0=u0, u1=u1, ao=0.95)
    nx, ny = dy, -dx
    for p in (a, b):
        V.box(p[0] - 0.05, p[1] - 0.05, z0, p[0] + 0.05, p[1] + 0.05, z0 + h + 0.08, frame, faces="+x-x+y-y")
    R.panel(V, (a[0] - dx * 0.05, a[1] - dy * 0.05), (b[0] + dx * 0.05, b[1] + dy * 0.05), z0 + h, z0 + h + 0.08, frame,
            off=off + 0.01)


def mullions(V, a, b, z0, z1, bay=1.5, mat="int_ru_steel", t=0.05, transoms=()):
    L = math.dist(a, b)
    if L < 0.1:
        return
    n = max(1, int(round(L / bay)))
    dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    for k in range(n + 1):
        p = (a[0] + dx * L * k / n, a[1] + dy * L * k / n)
        V.box(p[0] - t, p[1] - t, z0, p[0] + t, p[1] + t, z1, mat, faces="+x-x+y-y")
    for zt in transoms:
        R.seg_box(V, a, b, t, zt - t, zt + t, mat, faces="sidetopbot")


def threshold(V, C, a, b, n, z, depth, mat):
    """Floor strip across a door gap (wall line a-b, n = unit normal), overlapping both rooms (lesson: collision
    decks overlap at seams)."""
    d = depth / 2
    q = [(a[0] - n[0] * d, a[1] - n[1] * d), (b[0] - n[0] * d, b[1] - n[1] * d),
         (b[0] + n[0] * d, b[1] + n[1] * d), (a[0] + n[0] * d, a[1] + n[1] * d)]
    q = R.ccw(q)
    V.poly([(p[0], p[1], z) for p in q], mat, ao=1.0)
    C.poly([(p[0], p[1], z) for p in q], K.COL)


def entrance_at(fid, a, b):
    """The ENTRANCES record whose door line overlaps wall piece a-b on floor fid (area 2), or None."""
    for e in ENTRANCES:
        if e["floor"] != fid:
            continue
        ea, eb = e["a"], e["b"]
        if R.seg_point_dist(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), ea, eb) < 0.6:
            return e
    return None


def pieces_avoiding(tris, voids, coarse, fine, margin=1.0):
    """Convex pieces of triangles on a `coarse` grid (0 = the triangles themselves), re-cut on a `fine` grid where they
    come within `margin` of a void; pieces whose centroid lies in a void are dropped."""
    vb = [(R.bbox(v), v) for v in voids]
    base = R.grid_pieces(tris, coarse) if coarse > 0 else [list(t) for t in tris]
    out = []
    for pc in base:
        b = R.bbox(pc)
        near = [v for (vx0, vy0, vx1, vy1), v in vb
                if not (vx0 - margin > b[2] or vx1 + margin < b[0] or vy0 - margin > b[3] or vy1 + margin < b[1])]
        if near:
            # only if the piece really comes close to a void edge (not just its bounding box)
            near = [v for v in near if any(R.pip(p, v) for p in pc) or any(R.pip(p, pc) for p in v)
                    or min(R.poly_dist(p, v) for p in pc) < margin
                    or min(R.poly_dist(p, pc) for p in v) < margin]
        if not near:
            out.append(pc)
            continue
        for q in R.grid_pieces(R.earclip(pc) if len(pc) > 3 else [tuple(pc)], fine):
            c = R.centroid(q)
            if any(R.pip(c, v) for v in near):
                continue
            out.append(q)
    return out


def _bb_overlap(a, b):
    return not (a[0] >= b[2] or b[0] >= a[2] or a[1] >= b[3] or b[1] >= a[3])


def _convex_parts(poly):
    """A polygon as convex holes for R.subtract: itself when convex, else its triangles."""
    a = R.ccw(R.clean(poly))
    n = len(a)
    if n >= 3 and all(R._cross(a[k - 1], a[k], a[(k + 1) % n]) >= -1e-9 for k in range(n)):
        return [a]
    return [list(t) for t in R.triangulate(a)]


def build_floor(RZ, F):
    """Generic shell of one floor: floors, ceilings, walls (both sides as needed), doors, windows, balcony edges."""
    fid, z = F.id, F.z
    g = fid
    P = K.Prop("floor_" + fid)
    V, C = P.visual, P.collision
    above = RZ.floors.get(FLOORS[FLOORS.index(fid) + 1]) if fid != FLOORS[-1] else None
    voids_above = list(above.voids) if above is not None else []
    if fid == "L3":
        voids_above = []
    stats = {"walls": 0, "doors_open": 0, "doors_closed": 0}
    CW = []        # collision wall quads, merged before they are emitted
    CC = []        # collision ceilings
    ceil_groups = {}   # ceiling height -> zone polygons (collision: merged 3 m rectangles, exact next to voids)
    floor_polys = []   # walkable zones (collision floor: merged 3 m rectangles; exact cells next to voids / doors)
    # -- floors + ceilings per walkable zone. The plan's corridor polygons are envelopes that also cover rooms
    #    (meeting rooms, the atrium, the Arredondo corridor...), so every zone loses the smaller walkable zones
    #    that overlap it: no doubled (z-fighting) floors or ceilings.
    WZ = F.walk_zones()
    inner, inner_ceil = {}, {}
    for zn in WZ:
        hs, hc = [], []
        for o in WZ:
            if o is zn or o.area >= zn.area or not _bb_overlap(o.bb, zn.bb):
                continue
            parts = _convex_parts(o.poly)
            hs.extend(parts)
            if o.type != "atrium_floor":        # the atrium zones draw no ceiling of their own
                hc.extend(parts)
        inner[zn.id], inner_ceil[zn.id] = hs, hc
    zone_zc = []
    for zn in WZ:
        st = zn.style
        R.floor_poly(V, zn.poly, z - 0.02, st["floor"], step=FLOOR_STEP, cut=list(F.voids) + inner[zn.id])
        floor_polys.append(R.offset_poly(R.clean(zn.poly, 0.12, 0.03), 0.06))
        zc = z + st["clear"]
        top_voids = voids_above if st["clear"] <= CLEAR[fid] + 0.01 else []
        if zn.type == "atrium_floor":
            continue
        tris = R.triangulate(zn.poly)
        cut = list(top_voids) + list(F.voids) + inner_ceil[zn.id]
        zone_zc.append((zn, round(zc, 3)))
        for pc in R.subtract(R.grid_pieces(tris, CEIL_STEP), cut):
            c = R.centroid(pc)
            near = min((R.poly_dist(c, v) for v in top_voids), default=99.0)
            mat = "int_ru_cedar" if (near < 3.2 and zn.type in ("corridor", "atrium_floor", "vestibule")
                                     and fid in ("G", "L1", "L2", "L3")) else st["ceil"]
            V.poly([(x, y, zc) for x, y in reversed(R.ccw(pc))], mat, ao=0.95)
        ceil_groups.setdefault(round(zc, 3), []).append(R.clean(zn.poly, 0.12, 0.03))
    # -- walls: collect the runs, choose the meeting rooms' accent walls, then build
    runs_all = []
    for w in F.walls:
        a, b = (w[0], w[1]), (w[2], w[3])
        L0 = math.dist(a, b)
        if L0 < 0.05:
            continue
        dx, dy = (b[0] - a[0]) / L0, (b[1] - a[1]) / L0
        ext = WALL_T / 2
        a2 = (a[0] - dx * ext, a[1] - dy * ext)
        b2 = (b[0] + dx * ext, b[1] + dy * ext)
        runs = _side_samples(F, a, b, 0.35)
        doors = _door_cuts(F, a, b)
        L = math.dist(a2, b2)
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        if any(R.pip(mid, nw) for nw in F.no_walls):
            continue
        open_ww = any(R.pip(mid, ow) for ow in F.open_ww)
        for s0, s1, (cl, zl), (cr, zr) in runs:
            if open_ww and cl == "W" and cr == "W":
                continue
            if "W" not in (cl, cr) and "V" not in (cl, cr) and "O" not in (cl, cr):
                continue
            if "W" not in (cl, cr) and "V" not in (cl, cr) and cl == cr:
                continue
            r0 = 0.0 if s0 < 1e-6 else s0 + ext
            r1 = L if s1 > L0 - 1e-6 else s1 + ext
            pa = (a2[0] + dx * r0, a2[1] + dy * r0)
            pb = (a2[0] + dx * r1, a2[1] + dy * r1)
            RL = math.dist(pa, pb)
            dl = []
            for d0, d1, di, dext in doors:
                q0, q1 = d0 + ext - r0, d1 + ext - r0
                if q1 <= 0.05 or q0 >= RL - 0.05:
                    continue
                dl.append((max(0.0, q0), min(RL, q1), di, dext))
            runs_all.append({"pa": pa, "pb": pb, "L": (cl, zl), "R": (cr, zr), "doors": dl, "accent": set()})
    # accent wall per meeting / hotel room: its longest run without a door, facing away from the corridor
    for zn in F.walk_zones():
        if not zn.style.get("accent"):
            continue
        best = None
        for r in runs_all:
            for side in ("L", "R"):
                cls, z_ = r[side]
                if cls != "W" or z_ is not zn or r["doors"]:
                    continue
                o = r["R" if side == "L" else "L"]
                if o[0] == "W" and o[1] is not None and o[1].type == "corridor":
                    continue
                Lr = math.dist(r["pa"], r["pb"])
                if best is None or Lr > best[0]:
                    best = (Lr, r, side)
        if best is not None and best[0] > 2.5:
            best[1]["accent"].add(best[2])
            zn.style["accent_wall"] = (best[1]["pa"], best[1]["pb"])
    for r in runs_all:
        _wall_run(RZ, F, V, C, CW, r["pa"], r["pb"], r["L"], r["R"], r["doors"], stats, r["accent"])
    for q in merge_col_walls(CW):
        C.poly(q, K.COL)
    # collision floor: 3 m cells over the walkable zones merged into rectangles (spilling under walls into closed
    # rooms is harmless); exact (cell minus hole) next to this floor's voids, the Grand Ballroom's upper volume and
    # the entrance door lines (no floor beyond an area-2 warp strip)
    door_boxes = []
    for e in ENTRANCES:                  # the outside of each area-2 door line (only the warp strip is floor there)
        if e["floor"] == fid:
            a, b, n = e["a"], e["b"], e["n"]
            ex = ((b[0] - a[0]) / math.dist(a, b), (b[1] - a[1]) / math.dist(a, b))
            a2 = (a[0] - ex[0] * 1.0, a[1] - ex[1] * 1.0)
            b2 = (b[0] + ex[0] * 1.0, b[1] + ex[1] * 1.0)
            door_boxes.append(R.ccw([a2, b2, (b2[0] + n[0] * 4.0, b2[1] + n[1] * 4.0),
                                     (a2[0] + n[0] * 4.0, a2[1] + n[1] * 4.0)]))
    favoid = list(F.voids) + [z_.poly for z_ in F.zones if z_.type in DOUBLE_TYPES] + door_boxes
    rects, exact = R.rect_cover(floor_polys, 3.0, avoid=favoid)
    for (x0, y0, x1, y1) in rects:
        C.poly([(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)], K.COL)
    for pc in exact:
        C.poly([(x, y, z) for x, y in R.ccw(pc)], K.COL)
    avoid = list(F.voids) + list(voids_above) + [z_.poly for z_ in F.zones if z_.type in DOUBLE_TYPES]
    for zc, polys in ceil_groups.items():
        # smaller rooms of another ceiling height inside this group's envelopes are cut out of it
        own = [zn for zn, zz in zone_zc if zz == zc]
        other = [o.poly for o, zz in zone_zc if zz != zc
                 and any(o.area < zn.area and _bb_overlap(o.bb, zn.bb) for zn in own)]
        rects, exact = R.rect_cover(polys, 3.0, avoid=avoid + other)
        for (x0, y0, x1, y1) in rects:
            CC.append([(x0, y0, zc), (x0, y1, zc), (x1, y1, zc), (x1, y0, zc)])
        for pc in exact:
            CC.append([(x, y, zc) for x, y in reversed(R.ccw(pc))])
    for q in CC:
        C.poly(q, K.COL)
    RZ.stats.setdefault("floors", {})[fid] = stats
    RZ.kit_add(P, g, tag=f"shell_{fid}")
    return P


def _side_pts(pa, pb, side, t):
    """The face line of a wall run on `side` ('L' / 'R'), oriented so its normal points to that side."""
    L = math.dist(pa, pb)
    dx, dy = (pb[0] - pa[0]) / L, (pb[1] - pa[1]) / L
    lx, ly = -dy, dx
    if side == "L":
        a = (pa[0] + lx * t, pa[1] + ly * t)
        b = (pb[0] + lx * t, pb[1] + ly * t)
        return b, a, (lx, ly)          # b -> a has its right-hand normal = left of pa -> pb
    a = (pa[0] - lx * t, pa[1] - ly * t)
    b = (pb[0] - lx * t, pb[1] - ly * t)
    return a, b, (-lx, -ly)


def _wall_run(RZ, F, V, C, CW, pa, pb, left, right, doors, stats, accent=()):
    fid, z = F.id, F.z
    RL = math.dist(pa, pb)
    if RL < 0.05:
        return
    stats["walls"] += 1
    sides = {"L": left, "R": right}
    ext_wall = "O" in (left[0], right[0])
    t = (EXT_T if ext_wall else WALL_T) / 2
    # door handling on this run
    holes = []          # (s0, s1, z0 rel, z1 rel) in run coordinates, for both faces
    door_recs = []
    for d0, d1, di, dext in doors:
        kinds = {left[0], right[0]}
        ent = entrance_at(fid, (pa[0] + (pb[0] - pa[0]) * d0 / RL, pa[1] + (pb[1] - pa[1]) * d0 / RL),
                          (pa[0] + (pb[0] - pa[0]) * d1 / RL, pa[1] + (pb[1] - pa[1]) * d1 / RL))
        open_ext = any(R.seg_point_dist(((pa[0] + (pb[0] - pa[0]) * (d0 + d1) / 2 / RL),
                                          (pa[1] + (pb[1] - pa[1]) * (d0 + d1) / 2 / RL)), (od[0], od[1]), (od[2], od[3])) < 0.6
                       for e in ENTRANCES if e["floor"] == fid for od in e.get("open_doors", ()))
        if open_ext and ent is None:
            ent = True
        if kinds == {"W"}:
            holes.append((d0, d1, 0.0, DOOR_H))
            door_recs.append(("open", d0, d1))
            stats["doors_open"] += 1
        elif "W" in kinds and ent is not None:
            holes.append((d0, d1, 0.0, GLASS_DOOR_H))
            door_recs.append(("entrance", d0, d1))
        elif "W" in kinds:
            door_recs.append(("closed_ext" if "O" in kinds else "closed", d0, d1))
            stats["doors_closed"] += 1
    for side in ("L", "R"):
        cls, zn = sides[side]
        ocls, ozn = sides["R" if side == "L" else "L"]
        fa, fb, nrm = _side_pts(pa, pb, side, t)

        def S(s):
            return s if side == "R" else RL - s
        hs = [(min(S(h[0]), S(h[1])), max(S(h[0]), S(h[1])), z + h[2], z + h[3]) for h in holes]
        if cls == "W":
            st = zn.style
            h = st["clear"]
            mat = st["wall"]
            if side in accent and st.get("accent"):
                mat = st["accent"]
            win = window_spec(fid, pa, pb, zn) if ocls == "O" else None
            hh = list(hs)
            if ozn is not None and ozn.id == "food_court_servery":
                hh.extend(_storefront_holes(fa, fb, z))
            if win is not None:
                hh.append((0.0, math.dist(fa, fb), z + win[0], z + win[1]))
            base = "int_ru_black" if zn.type not in ("hotel_room",) else "int_ru_wall"
            wall_face(V, fa, fb, z, z + h, mat, base=st["base"] if st["base"] else base, holes=hh)
            col_face(CW, fa, fb, z, z + h, holes=[x for x in hs])
            if win is not None:
                _window(V, C, fa, fb, z, win, nrm, t, ocls)
            # chair rail in meeting rooms / corridors of the 2016 wing (photos: white chair rail at ~0.9 m)
            if zn.type in ("meeting_room", "chamber"):
                _rail_strip(V, fa, fb, z + 0.88, z + 0.96, hs, nrm)
            for kind, d0, d1 in door_recs:
                s0, s1 = sorted((S(d0), S(d1)))
                da = (fa[0] + (fb[0] - fa[0]) * s0 / max(1e-6, math.dist(fa, fb)),
                      fa[1] + (fb[1] - fa[1]) * s0 / max(1e-6, math.dist(fa, fb)))
                db = (fa[0] + (fb[0] - fa[0]) * s1 / max(1e-6, math.dist(fa, fb)),
                      fa[1] + (fb[1] - fa[1]) * s1 / max(1e-6, math.dist(fa, fb)))
                if kind in ("closed", "closed_ext"):
                    dm = _door_mat(zn, ozn, kind)
                    door_leaves(V, da, db, z, min(2.4 if dm != "int_ru_door_glass" else 2.8, h - 0.3), dm)
                elif kind in ("open", "entrance"):
                    hd = DOOR_H if kind == "open" else GLASS_DOOR_H
                    # jambs + head trim on this face
                    V.box(da[0] - 0.05, da[1] - 0.05, z, da[0] + 0.05, da[1] + 0.05, z + hd, "int_ru_steel" if kind == "entrance" else "int_ru_wood_panel", faces="+x-x+y-y")
                    V.box(db[0] - 0.05, db[1] - 0.05, z, db[0] + 0.05, db[1] + 0.05, z + hd, "int_ru_steel" if kind == "entrance" else "int_ru_wood_panel", faces="+x-x+y-y")
        elif cls == "O" and ocls in ("W", "S"):
            # exterior facade band of this storey (visual)
            z0 = z - (SLAB if fid not in ("LL", "G") else 0.4)
            ztop = z + (ozn.style["clear"] if (ocls == "W" and ozn.style) else F.clear)
            if fid in ("L3",) or (fid in ("L6",)):
                ztop += SLAB + 0.9          # parapet
            win = window_spec(fid, pa, pb, ozn) if ocls == "W" else None
            hh = list(hs)
            if win is not None:
                hh.append((0.0, math.dist(fa, fb), z + win[0], z + win[1]))
            elif ocls == "S" and fid not in ("LL",):
                # sealed rooms: dark window band seen from outside (offices behind glass)
                hh.append((0.6, max(0.6, math.dist(fa, fb) - 0.6), z + 1.0, z + 3.1))
                _dark_band(V, fa, fb, z + 1.0, z + 3.1)
            wall_face(V, fa, fb, z0, ztop, facade_mat(fid, pa, pb), step=4.0, holes=hh)
        elif cls == "V" and ocls == "W":
            # balcony edge: fascia into the void + railing on the slab edge
            _balcony_edge(V, C, fa, fb, z, F)
        elif cls == "V" and ocls == "O":
            # the void meets the outside: the 2016 wing's tall south glazing over the Ground lounge
            ca = (fa[0] - nrm[0] * t, fa[1] - nrm[1] * t)
            cb = (fb[0] - nrm[0] * t, fb[1] - nrm[1] * t)
            R.quad_wall(V, ca, cb, z - SLAB, z + F.clear, "int_ru_glass", ao=1.0)
            mullions(V, ca, cb, z - SLAB, z + F.clear, bay=1.6, t=0.05, transoms=(z, z + 2.7))
            col_face(CW, fa, fb, z - SLAB, z + F.clear)
        elif cls == "V" and ocls == "S":
            # a solid wall facing the void (shafts, rooms): full storey + slab band
            wall_face(V, fa, fb, z - SLAB, z + F.clear, "int_ru_wall", holes=hs)
            col_face(CW, fa, fb, z - SLAB, z + F.clear)
    # door heads + thresholds for open doors (one header box across the wall thickness)
    for kind, d0, d1 in door_recs:
        if kind not in ("open", "entrance"):
            continue
        hd = DOOR_H if kind == "open" else GLASS_DOOR_H
        da = (pa[0] + (pb[0] - pa[0]) * d0 / RL, pa[1] + (pb[1] - pa[1]) * d0 / RL)
        db = (pa[0] + (pb[0] - pa[0]) * d1 / RL, pa[1] + (pb[1] - pa[1]) * d1 / RL)
        n = ((pb[1] - pa[1]) / RL, -(pb[0] - pa[0]) / RL)
        lw = left[1].style["clear"] if left[0] == "W" and left[1] and left[1].style else F.clear
        rw = right[1].style["clear"] if right[0] == "W" and right[1] and right[1].style else F.clear
        top = min(lw, rw)
        R.seg_box(V, da, db, t, z + hd, z + top, "int_ru_wall", faces="bot")
        C.poly([(da[0] - n[0] * t, da[1] - n[1] * t, z + hd), (db[0] - n[0] * t, db[1] - n[1] * t, z + hd),
                (db[0] + n[0] * t, db[1] + n[1] * t, z + hd), (da[0] + n[0] * t, da[1] + n[1] * t, z + hd)],
               K.COL, normal_hint=(0, 0, -1))
        # jamb faces (wall thickness) visual + collision
        for p, sgn in ((da, 1), (db, -1)):
            q0 = (p[0] + n[0] * t, p[1] + n[1] * t)
            q1 = (p[0] - n[0] * t, p[1] - n[1] * t)
            dir_ = ((pb[0] - pa[0]) / RL * sgn, (pb[1] - pa[1]) / RL * sgn)
            V.poly([(q0[0], q0[1], z), (q1[0], q1[1], z), (q1[0], q1[1], z + hd), (q0[0], q0[1], z + hd)],
                   "int_ru_wood_panel" if kind == "open" else "int_ru_steel", normal_hint=(dir_[0], dir_[1], 0))
            C.poly([(q0[0], q0[1], z), (q1[0], q1[1], z), (q1[0], q1[1], z + hd), (q0[0], q0[1], z + hd)], K.COL,
                   normal_hint=(dir_[0], dir_[1], 0))
        if kind == "open":
            zl = left[1].style["floor"] if left[1] and left[1].style else "int_ru_terrazzo"
            threshold(V, C, da, db, n, z, 2 * t + 0.5, zl)


def _storefront_holes(fa, fb, z, near=0.5, h=3.9):
    """Openings in the corridor face of the servery wall where the SERVERY_FRONTS storefronts are."""
    L = math.dist(fa, fb)
    if L < 0.2:
        return []
    dx, dy = (fb[0] - fa[0]) / L, (fb[1] - fa[1]) / L
    out = []
    for a, b, *_ in SERVERY_FRONTS:
        ss = []
        n = 24
        for k in range(n + 1):
            p = (a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n)
            if R.seg_point_dist(p, fa, fb) < near:
                ss.append((p[0] - fa[0]) * dx + (p[1] - fa[1]) * dy)
        if len(ss) >= 2:
            s0, s1 = max(0.0, min(ss)), min(L, max(ss))
            if s1 - s0 > 0.4:
                out.append((s0, s1, z, z + h))
    return out


def _door_mat(zn, ozn, kind):
    if kind == "closed_ext":
        return "int_ru_door_glass"
    t = ozn.type if ozn is not None else ""
    if t in ("restroom", "service", "room", "elevator") and (ozn is None or not ozn.name.startswith("Stair")):
        return "int_ru_door" if t == "restroom" else "int_ru_door_steel" if t in ("service", "elevator") else "int_ru_door"
    if t in ("office", "office_suite", "retail", "dining_retail", "food_servery"):
        return "int_ru_door_glass" if t in ("office_suite", "retail", "dining_retail") else "int_ru_door"
    if zn.type == "ballroom" or (ozn is not None and ozn.type == "ballroom"):
        return "int_ru_door_walnut"
    return "int_ru_door"


def _rail_strip(V, a, b, z0, z1, holes, nrm):
    L = math.dist(a, b)
    if L < 0.1:
        return
    cuts = [(0.0, L)]
    for h in holes:
        if h[2] < z1 and h[3] > z0:
            nc = []
            for c0, c1 in cuts:
                if h[1] <= c0 or h[0] >= c1:
                    nc.append((c0, c1))
                    continue
                if h[0] > c0:
                    nc.append((c0, h[0]))
                if h[1] < c1:
                    nc.append((h[1], c1))
            cuts = nc
    dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    for c0, c1 in cuts:
        if c1 - c0 < 0.1:
            continue
        p0 = (a[0] + dx * c0 + nrm[0] * 0.015, a[1] + dy * c0 + nrm[1] * 0.015)
        p1 = (a[0] + dx * c1 + nrm[0] * 0.015, a[1] + dy * c1 + nrm[1] * 0.015)
        R.quad_wall(V, p0, p1, z0, z1, "int_ru_white", ao=1.0)


def _dark_band(V, a, b, z0, z1):
    L = math.dist(a, b)
    if L < 1.4:
        return
    dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    p0 = (a[0] + dx * 0.6, a[1] + dy * 0.6)
    p1 = (b[0] - dx * 0.6, b[1] - dy * 0.6)
    R.quad_wall(V, p0, p1, z0, z1, "int_ru_glass_blue", ao=1.0)


def _window(V, C, a, b, z, win, nrm, t, ocls):
    """A glass pane in the wall plane (translucent, both sides), sill / head reveals, mullions."""
    sill, head, kind = win
    L = math.dist(a, b)
    if L < 0.3:
        return
    # pane in the wall centre plane
    ca = (a[0] - nrm[0] * t, a[1] - nrm[1] * t)
    cb = (b[0] - nrm[0] * t, b[1] - nrm[1] * t)
    R.quad_wall(V, ca, cb, z + sill, z + head, "int_ru_glass", ao=1.0)
    bay = 1.5 if kind != "clerestory" else 2.0
    mullions(V, ca, cb, z + sill, z + head, bay=bay, t=0.04,
             transoms=() if head - sill < 2.5 else (z + sill + min(2.7, (head - sill) * 0.55),))
    if sill > 0.05:
        V.poly([(a[0], a[1], z + sill), (b[0], b[1], z + sill), (cb[0], cb[1], z + sill), (ca[0], ca[1], z + sill)],
               "int_ru_white", normal_hint=(0, 0, 1))
    V.poly([(a[0], a[1], z + head), (ca[0], ca[1], z + head), (cb[0], cb[1], z + head), (b[0], b[1], z + head)],
           "int_ru_white", normal_hint=(0, 0, -1))


def _balcony_edge(V, C, a, b, z, F):
    """Atrium balcony edge (ru_atrium_enr_lounge, ru_atrium_hdr_flickr): a white fascia band dropping FASCIA below
    the floor with an LED cove, a cut-out picket railing with a silver cap; collision: the railing (both sides)
    and the slab edge facing INTO the void (lesson: floor-hole edges face into the hole)."""
    L = math.dist(a, b)
    if L < 0.05:
        return
    # a -> b has its normal toward the void (side line of the V side)
    R.quad_wall(V, a, b, z - SLAB - FASCIA * 0.5, z + 0.12, "int_ru_white", ao=1.0)
    nx, ny = (b[1] - a[1]) / L, -(b[0] - a[0]) / L
    # fascia underside (soffit lip) + LED cove line
    ia = (a[0] - nx * 0.35, a[1] - ny * 0.35)
    ib = (b[0] - nx * 0.35, b[1] - ny * 0.35)
    V.poly([(a[0], a[1], z - SLAB - FASCIA * 0.5), (ia[0], ia[1], z - SLAB - FASCIA * 0.5),
            (ib[0], ib[1], z - SLAB - FASCIA * 0.5), (b[0], b[1], z - SLAB - FASCIA * 0.5)], "int_ru_white",
           normal_hint=(0, 0, -1), ao=0.9)
    R.quad_wall(V, (ib[0], ib[1]), (ia[0], ia[1]), z - SLAB - FASCIA * 0.5, z - SLAB, "int_ru_white", ao=0.85)
    led_a = (a[0] + nx * 0.01, a[1] + ny * 0.01)
    led_b = (b[0] + nx * 0.01, b[1] + ny * 0.01)
    R.quad_wall(V, led_a, led_b, z - 0.1, z - 0.04, "int_ru_led", glow=True)
    # railing: pickets (double-sided cut-out) slightly inboard of the edge, top rail
    ra = (a[0] - nx * 0.12, a[1] - ny * 0.12)
    rb = (b[0] - nx * 0.12, b[1] - ny * 0.12)
    V.poly([(ra[0], ra[1], z), (rb[0], rb[1], z), (rb[0], rb[1], z + RAIL_H), (ra[0], ra[1], z + RAIL_H)],
           "int_ru_picket", uvs=[(0, 0), (L / 1.1, 0), (L / 1.1, 1), (0, 1)], ao=1.0)
    R.seg_box(V, ra, rb, 0.04, z + RAIL_H, z + RAIL_H + 0.06, "int_ru_steel", faces="sidetop")
    # curb on the slab edge
    R.seg_box(V, (a[0] - nx * 0.06, a[1] - ny * 0.06), (b[0] - nx * 0.06, b[1] - ny * 0.06), 0.06, z, z + 0.12,
              "int_ru_white", faces="sidetop")
    # collision: railing block + slab edge into the void
    R.col_seg(C, ra, rb, 0.08, z, z + RAIL_H + 0.06, K.COL_NOCAM)
    C.poly([(a[0], a[1], z - SLAB), (b[0], b[1], z - SLAB), (b[0], b[1], z), (a[0], a[1], z)], K.COL)


# ---------------------------------------------------------------- ceiling fixtures (+ bake lights)
def _grid_points(poly, spacing, margin=0.8):
    x0, y0, x1, y1 = R.bbox(poly)
    pts = []
    nx = max(1, int((x1 - x0 - 2 * margin) / spacing) + 1)
    ny = max(1, int((y1 - y0 - 2 * margin) / spacing) + 1)
    ox = x0 + (x1 - x0 - (nx - 1) * spacing) / 2
    oy = y0 + (y1 - y0 - (ny - 1) * spacing) / 2
    for i in range(nx):
        for j in range(ny):
            p = (ox + i * spacing, oy + j * spacing)
            if R.pip(p, poly) and R.poly_dist(p, poly) > margin * 0.7:
                pts.append(p)
    if not pts:
        c = R.centroid(poly)
        if R.pip(c, poly):
            pts.append(c)
    return pts


LIGHT_WARM = (1.0, 0.96, 0.88)
LIGHT_COOL = (0.94, 0.97, 1.0)


def build_lights(RZ, F, skip=()):
    fid, z = F.id, F.z
    P = K.Prop("lights_" + fid)
    V = P.visual
    for zn in F.walk_zones():
        st = zn.style
        kind = st["light"]
        if zn.id in skip or kind in ("none", "coffer", "esports", "cove", "track"):
            continue
        if zn.type == "atrium_floor":
            continue
        zc = z + st["clear"] - 0.01
        sp = st["spacing"]
        voids_above = []
        pts = _grid_points(zn.poly, sp, margin=0.9 if kind != "car" else 0.4)
        for (x, y) in pts:
            if kind == "troffer":
                V.poly([(x - 0.3, y - 0.6, zc), (x - 0.3, y + 0.6, zc), (x + 0.3, y + 0.6, zc), (x + 0.3, y - 0.6, zc)],
                       "int_light", uvs=[(0, 0), (0, 1), (1, 1), (1, 0)], glow=True)
                P.lights.append(K.Light((x, y, zc - 0.3), radius=6.5, strength=0.26, color=LIGHT_COOL))
            elif kind == "linear":
                V.poly([(x - 1.2, y - 0.06, zc), (x - 1.2, y + 0.06, zc), (x + 1.2, y + 0.06, zc), (x + 1.2, y - 0.06, zc)],
                       "int_ru_led", glow=True)
                P.lights.append(K.Light((x, y, zc - 0.3), radius=6.0, strength=0.27, color=LIGHT_COOL))
            elif kind in ("down", "lamp", "car"):
                r = 0.12
                V.poly([(x - r, y - r, zc), (x - r, y + r, zc), (x + r, y + r, zc), (x + r, y - r, zc)], "int_ru_led",
                       glow=True)
                P.lights.append(K.Light((x, y, zc - 0.3), radius=5.5 if kind != "car" else 2.6,
                                        strength=0.24 if kind != "lamp" else 0.16, color=LIGHT_WARM))
    RZ.kit_add(P, fid, tag="lights_" + fid)
    return P


# ---------------------------------------------------------------- entrances (area 2 side)
def build_entrances(RZ):
    """Area-2 instant-warp strips (raw collision, SURFACE_INSTANT_WARP_1x) just outside each entrance, the porch
    floors, and the outside paving under them (visual)."""
    for e in ENTRANCES:
        F = RZ.floors[e["floor"]]
        P = K.Prop("entrance_" + e["id"])
        V, C = P.visual, P.collision
        a, b, n = e["a"], e["b"], e["n"]
        z2 = e["z2"]
        dpt = e["depth_out"]
        strip = R.ccw([a, b, (b[0] + n[0] * dpt, b[1] + n[1] * dpt), (a[0] + n[0] * dpt, a[1] + n[1] * dpt)])
        R.col_floor(C, strip, z2 + WARP_UP, mat=WARP_MAT[e["index"]], raw=True)
        R.floor_poly(V, strip, z2 - 0.02, "int_ru_paving", step=3.0)
        if e.get("porch"):
            porch = R.ccw(e["porch"])
            R.col_floor(C, R.offset_poly(porch, 0.05), z2)
            R.floor_poly(V, porch, z2 - 0.02, "int_ru_paving", step=3.0)
            # landing rails (east / west sides of the porch, the stairs go down beyond them)
            xs = [p[0] for p in porch]
            ys = [p[1] for p in porch]
            for xr in (min(xs), max(xs)):
                ra, rb = (xr, min(ys)), (xr, max(ys))
                V.poly([(ra[0], ra[1], z2), (rb[0], rb[1], z2), (rb[0], rb[1], z2 + RAIL_H), (ra[0], ra[1], z2 + RAIL_H)],
                       "int_ru_picket", uvs=[(0, 0), (math.dist(ra, rb) / 1.1, 0), (math.dist(ra, rb) / 1.1, 1), (0, 1)])
                R.col_seg(C, ra, rb, 0.08, z2, z2 + RAIL_H, K.COL_NOCAM)
            # the slab under the landing (seen from the terrace)
            R.floor_poly(V, porch, z2 - 0.4, "int_ru_white", step=9.0, down=True)
        RZ.warp_strips.append({"entrance": e["id"], "index": e["index"], "surface": WARP_SURFACE[e["index"]],
                               "z_m": z2, "poly_m": [list(map(lambda v: round(v, 2), p)) for p in strip],
                               "to_area": 1, "offset_units": [0, int(round((e["z1"] - e["z2"]) * 100)), 0]})
        RZ.kit_add(P, e["floor"], tag="entrance_" + e["id"])
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        RZ.points.setdefault("entrances", {})[e["id"]] = {
            "inside": {"name": f"interior_{e['id']}_inside", "p": [mid[0] - n[0] * 1.5, mid[1] - n[1] * 1.5,
                                                                   F.z if not e.get("porch") else z2], "kind": "ground"},
            "outside_strip": {"name": f"interior_{e['id']}_strip", "p": [mid[0] + n[0] * dpt / 2, mid[1] + n[1] * dpt / 2, z2],
                              "kind": "ground"}}


# ---------------------------------------------------------------- Blue elevator teleport cabs
def build_elevators(RZ):
    """Open Blue cars: steel cab trim, a handrail, the destination floor sign over the door (outside) and inside;
    the bhvFadingWarp pads (objects) are returned in RZ.pads for the area builder."""
    links = []
    for i in range(len(BLUE_ORDER) - 1):
        lo, hi = BLUE_ORDER[i], BLUE_ORDER[i + 1]
        if (lo, "up") in RZ.cars and (hi, "down") in RZ.cars:
            links.append((lo, hi))
    atlas = {"LL": 0, "G": 1, "L1": 2, "L2": 3, "L3": 4, "L4": 5, "L5": 6, "L6": 7}
    for k, (lo, hi) in enumerate(links):
        up_node, down_node = PAD_NODE0 + 2 * k, PAD_NODE0 + 2 * k + 1
        for fid, kind, node, partner, dest in ((lo, "up", up_node, down_node, hi), (hi, "down", down_node, up_node, lo)):
            zn = RZ.cars[(fid, kind)]
            F = RZ.floors[fid]
            c = R.centroid(zn.poly)
            facing = 90.0 if c[0] < -445.0 else 270.0
            RZ.pads.append({"name": f"Elevator {fid} {kind}", "node": node, "dest_node": partner, "floor": fid,
                            "dest_floor": dest, "pos_m": (c[0], c[1], F.z), "facing_deg": facing,
                            "bparams": "0x%02X%02X0000" % (PAD_RADIUS_DM, node), "behavior": "bhvFadingWarp"})
            P = K.Prop(f"car_{fid}_{kind}")
            V = P.visual
            # destination sign over the door (lobby side) + inside the cab
            sx = c[0] + (1.2 if facing == 90.0 else -1.2)
            cell = atlas[dest]
            u0, v0 = (cell % 4) * 0.25, 1.0 - (cell // 4 + 1) * 0.5
            fa, fb = (sx, c[1] - 0.35), (sx, c[1] + 0.35)
            if facing == 270.0:
                fa, fb = fb, fa
            R.panel(V, fa, fb, F.z + 2.75, F.z + 3.45, "int_ru_floor_atlas", off=0.02, u0=u0, u1=u0 + 0.25, v0=v0,
                    v1=v0 + 0.5, glow=True)
            arrow = "^" if kind == "up" else "v"
            # handrail on the back wall
            bx = c[0] - (0.9 if facing == 90.0 else -0.9)
            V.box(bx - 0.03, c[1] - 0.6, F.z + 0.9, bx + 0.03, c[1] + 0.6, F.z + 0.95, "int_ru_steel",
                  faces="+x-x+y-y+z")
            RZ.kit_add(P, fid, tag=f"car_{fid}_{kind}")
            RZ.points.setdefault("elevators", {})[f"{fid}_{kind}"] = {
                "name": f"interior_elevator_{fid}_{kind}", "p": [c[0], c[1], F.z], "kind": "ground", "node": "0x%02X" % node,
                "to": dest, "arrow": arrow}
    RZ.stats["elevator_links"] = [list(x) for x in links]


# ================================================================== assembly
SPAWN = {"pos_m": (-399.0, -278.5), "z_game_m": 0.0, "facing_deg": 0.0}


def build(backdrop=True, dress=True):
    lay = load_layout()
    RZ = Reitz(lay)
    for fid in FLOORS:
        build_floor(RZ, RZ.floors[fid])
    build_entrances(RZ)
    build_elevators(RZ)
    if dress:
        for fn in DRESSERS:
            fn(RZ)
    for fid in FLOORS:
        build_lights(RZ, RZ.floors[fid], skip=RZ.lights_skip)
    if backdrop:
        build_backdrop(RZ)
    # lighting: one bake per group (the floor's own fixtures; daylight ambient)
    groups = RZ.kit.groups()
    by_group = {g: [] for g in groups}
    for t, g, p in RZ.kit.items:
        by_group[g].extend(p.lights)
    for g in groups:
        if g == "ext":
            RZ.lighting[g] = K.Lighting([], sky=(0.86, 0.86, 0.84), ground=(0.58, 0.57, 0.55), key=(0.5, -0.4, 0.75),
                                        key_strength=0.22)
        else:
            RZ.lighting[g] = K.Lighting(by_group[g], sky=(0.66, 0.66, 0.68), ground=(0.52, 0.51, 0.50),
                                        key=(0.45, 0.62, 0.64), key_strength=0.10)
    RZ.pickups = list(PICKUPS)
    RZ.layout_out = {"entrance": {"spawn": {"pos_m": list(SPAWN["pos_m"]), "z_game_m": SPAWN["z_game_m"],
                                            "facing_deg": SPAWN["facing_deg"]}}}
    RZ.layout = RZ.layout_out
    RZ.views = [(n, c, t, m, f) for n, c, t, m, f, _ in make_views(RZ)]
    RZ.stats["lights"] = sum(len(v) for v in by_group.values())
    RZ.stats["instant_warps"] = [{"index": i, "area1_to_area2_units": list(o)} for i, o in instant_warps()]
    return RZ


def report(M):
    return M.kit.report()


DRESSERS = []
VIEWS = []
# coins and hearts of area 2 (stage_pickups.Placer on the area's own collision). The food court line replaces the
# one area 1's removed fake food court had (the course keeps its coins), the rest reward exploring the building.
PICKUPS = [
    {"kind": "coin_line", "name": "food court coins", "pos": (-438.0, -318.0, 6.0), "facing": 90.0},
    {"kind": "coin_line", "name": "bowling lane 7 coins", "pos": (-446.17, -318.0, 0.0), "facing": 0.0},
    {"kind": "coin_line", "name": "atrium lounge coins", "pos": (-386.0, -279.5, 0.0), "facing": 90.0},
    {"kind": "coin", "name": "atrium landing G coin", "pos": (-400.0, -271.3, 3.0)},
    {"kind": "coin", "name": "atrium landing L1 coin", "pos": (-400.0, -271.3, 9.0)},
    {"kind": "coin", "name": "atrium landing L2 coin", "pos": (-400.0, -271.3, 15.0)},
    {"kind": "coin_ring", "name": "grand ballroom coins", "pos": (-488.5, -264.0, 12.0)},
    {"kind": "coin_line", "name": "rion ballroom coins", "pos": (-440.6, -300.5, 18.0), "facing": 90.0},
    {"kind": "coin_line", "name": "esports aisle coins", "pos": (-463.6, -292.0, 0.0), "facing": 0.0},
    {"kind": "heart", "name": "hotel corridor heart", "pos": (-440.0, -274.0, 29.0)},
    {"kind": "1up", "name": "uf letters 1-up", "pos": (-411.33, -265.6, 2.95)},
]


def build_backdrop(RZ):
    """Outside the glass (visual only): ground planes at the real grades (North Lawn / tabling plaza at Level 1,
    the South Terrace + amphitheater at Ground), Liberty Pond, the roofs of the building, neighbours."""
    P = K.Prop("backdrop")
    V = P.visual
    # main roof over the L3 outline (seen from the tower floors)
    l3 = RZ.floors["L3"]
    R.floor_poly(V, RZ.footprint, ROOF_Z["main"], "roof_gravel", step=12.0)
    RZ.kit_add(P, "ext", tag="backdrop")


def selftest():
    import time
    t0 = time.time()
    M = build()
    rep = report(M)
    print(f"reitz: {len(M.kit.items)} items, visual {rep['total']['visual']} tris, collision {rep['total']['collision']} "
          f"tris, {M.stats.get('lights')} lights, {len(M.pads)} pads, {len(M.warp_strips)} strips "
          f"({time.time() - t0:.1f}s)")
    by = {}
    for r in rep["items"]:
        g = by.setdefault(r["group"], [0, 0])
        g[0] += r["visual"]
        g[1] += r["collision"]
    for g, (v, c) in by.items():
        print(f"   {g:6s} visual {v:7d} collision {c:6d}")
    print("   stats", json.dumps(M.stats.get("floors")))
    probs = []
    for t, g, p in M.kit.items:
        for poly in p.visual.polys:
            if not K.known_material(poly.mat):
                probs.append((t, poly.mat))
    print("problems:", probs[:10] or "none")
    return probs



# ================================================================== the atrium (2016 wing): G lounge, voids L1-L3
# the plan's stair chevron (L1-L3 voids): tip, outer arm ends, inner tip (map m)
CHEVRON = {"tip": (-401.2, -271.3), "ne": (-395.6, -265.7), "se": (-397.3, -275.3), "inner": (-398.6, -271.3)}
STAIR_W = 1.8
LANDING_ALONG = 2.2


def _unit2(a, b):
    L = math.dist(a, b)
    return ((b[0] - a[0]) / L, (b[1] - a[1]) / L)


def atrium_stairs(RZ):
    """The scissor stairs crossing the west void (ru_atrium_hdr_flickr, ru_atrium_enr_vertical, ru_atrium_construction):
    per storey a flight up the south-east arm to a landing at the chevron tip, a flight up the north-east arm to the
    next floor's balcony. White stringers + soffits, terrazzo treads, picket rails."""
    tip, ne, se, inner = CHEVRON["tip"], CHEVRON["ne"], CHEVRON["se"], CHEVRON["inner"]
    dne, dse = _unit2(tip, ne), _unit2(tip, se)
    # arm midlines: half the arm width inside the outer edge
    nne = (dne[1], -dne[0])          # right of the NE arm (toward the inner chevron)
    nse = (-dse[1], dse[0])          # left of the SE arm (toward the inner chevron)
    w2 = STAIR_W / 2
    mne0 = (tip[0] + nne[0] * w2, tip[1] + nne[1] * w2)
    mse0 = (tip[0] + nse[0] * w2, tip[1] + nse[1] * w2)
    info = []
    storeys = [("G", "L1"), ("L1", "L2"), ("L2", "L3")]
    for lo, hi in storeys:
        Flo, Fhi = RZ.floors[lo], RZ.floors[hi]
        z0, z1 = Flo.z, Fhi.z
        zl = (z0 + z1) / 2
        P = K.Prop(f"atrium_stair_{lo}")
        V, C = P.visual, P.collision
        # SE flight: bottom where the arm leaves this floor's slab (the void edge), or the SE end on Ground
        void_lo = next((v for v in Flo.voids if R.pip(tip, v)), None)
        void_hi = next(v for v in Fhi.voids if R.pip(tip, v))
        s_land = LANDING_ALONG
        if void_lo is not None:
            t_se = R.seg_intersect(mse0, dse, void_lo)
        else:
            t_se = R.seg_intersect(mse0, dse, next(v for v in RZ.floors["L1"].voids if R.pip(tip, v))) + 1.0
        t_ne = R.seg_intersect(mne0, dne, void_hi)
        a_se = (mse0[0] + dse[0] * (t_se + 0.05), mse0[1] + dse[1] * (t_se + 0.05))
        b_se = (mse0[0] + dse[0] * s_land, mse0[1] + dse[1] * s_land)
        a_ne = (mne0[0] + dne[0] * s_land, mne0[1] + dne[1] * s_land)
        b_ne = (mne0[0] + dne[0] * (t_ne + 0.05), mne0[1] + dne[1] * (t_ne + 0.05))
        f1 = R.stair_flight(V, C, a_se, b_se, z0, zl, STAIR_W)
        f2 = R.stair_flight(V, C, a_ne, b_ne, zl, z1, STAIR_W)
        # landing: hull of the first LANDING_ALONG metres of both arms
        pts = [tip]
        for d_, n_ in ((dne, nne), (dse, nse)):
            pts.append((tip[0] + d_[0] * (s_land + 0.05), tip[1] + d_[1] * (s_land + 0.05)))
            pts.append((tip[0] + d_[0] * (s_land + 0.05) + n_[0] * STAIR_W, tip[1] + d_[1] * (s_land + 0.05) + n_[1] * STAIR_W))
        land = R.ccw(R.convex_hull(pts))
        R.floor_poly(V, land, zl, "int_ru_terrazzo", step=99.0)
        R.floor_poly(V, land, zl - 0.35, "int_ru_white", step=99.0, down=True)
        for pa, pb in R.edges(land):
            R.quad_wall(V, pb, pa, zl - 0.35, zl + 0.02, "int_ru_white", ao=0.9)
            R.quad_wall(V, pa, pb, zl - 0.35, zl, "int_ru_white", ao=0.9)
        R.col_floor(C, R.offset_poly(land, 0.08), zl)
        # landing rail on the open (west) sides
        tipo = (tip[0] - (dne[0] + dse[0]) * 0.05, tip[1] - (dne[1] + dse[1]) * 0.05)
        for d_ in (dne, dse):
            ra, rb = tipo, (tip[0] + d_[0] * s_land, tip[1] + d_[1] * s_land)
            V.poly([(ra[0], ra[1], zl), (rb[0], rb[1], zl), (rb[0], rb[1], zl + RAIL_H), (ra[0], ra[1], zl + RAIL_H)],
                   "int_ru_picket", uvs=[(0, 0), (math.dist(ra, rb) / 1.1, 0), (math.dist(ra, rb) / 1.1, 1), (0, 1)])
            R.seg_box(V, ra, rb, 0.035, zl + RAIL_H, zl + RAIL_H + 0.06, "int_ru_steel", faces="sidetop")
            R.col_seg(C, ra, rb, 0.08, zl, zl + RAIL_H + 0.06, K.COL_NOCAM)
        RZ.kit_add(P, lo, tag=f"atrium_stair_{lo}")
        info.append({"storey": f"{lo}-{hi}", "se": f1, "ne": f2, "landing_z": zl})
        RZ.points.setdefault("atrium", {})[f"stair_landing_{lo}"] = {
            "name": f"interior_atrium_landing_{lo}", "p": [tip[0] + (dne[0] + dse[0]) * 1.0, tip[1] + (dne[1] + dse[1]) * 1.0, zl],
            "kind": "ground"}
    RZ.stats["atrium_stairs"] = info


def atrium_top(RZ):
    """Over the west void: the clerestory band (L3 ceiling 23.4 -> 25.6) and the cedar slat ceiling with dark
    curved ribs (ru_atrium_hdr_flickr, ru_atrium_enr_vertical; 'patterned on a gator's underbelly')."""
    F = RZ.floors["L3"]
    void = next(v for v in F.voids if R.pip(CHEVRON["tip"], v))
    z0 = F.z + CLEAR["L3"]
    z1 = ATRIUM_TOP
    P = K.Prop("atrium_top")
    V, C = P.visual, P.collision
    for a, b in R.edges(void):
        # inner faces (facing into the void): the hull is CCW, so b -> a has the normal toward the inside
        mid_y = (a[1] + b[1]) / 2
        north = mid_y > -268.5
        if north and math.dist(a, b) > 1.0:
            R.quad_wall(V, b, a, z0, z0 + 0.3, "int_ru_white")
            R.quad_wall(V, b, a, z0 + 0.3, z1 - 0.2, "int_ru_glass")
            mullions(V, b, a, z0 + 0.3, z1 - 0.2, bay=1.6, t=0.04)
            R.quad_wall(V, b, a, z1 - 0.2, z1, "int_ru_white")
        else:
            R.quad_wall(V, b, a, z0, z1, "int_ru_white", ao=0.9)
        R.quad_wall(V, a, b, z0, z1 + 0.6, "int_ru_white")
        C.poly([(b[0], b[1], z0), (a[0], a[1], z0), (a[0], a[1], z1), (b[0], b[1], z1)], K.COL)
    # cedar vault: the hull lifted 1.2 m along its long axis, split in strips; dark ribs across
    xs = [p[0] for p in void]
    x0, x1 = min(xs), max(xs)
    yc = sum(p[1] for p in void) / len(void)
    nstrip = 10
    for k in range(nstrip):
        xa = x0 + (x1 - x0) * k / nstrip
        xb = x0 + (x1 - x0) * (k + 1) / nstrip
        strip = R.clip_convex(void, xa, -400.0, xb, 0.0)
        if not strip:
            continue
        pts = []
        for p in reversed(R.ccw(strip)):
            # vault: highest along the mid line, + a gentle wave along x (the "underbelly" ribs)
            dy = abs(p[1] - yc)
            zz = z1 + 1.2 * max(0.0, 1.0 - (dy / 5.5) ** 2) + 0.25 * math.sin((p[0] - x0) / 3.0)
            pts.append((p[0], p[1], zz))
        V.poly(pts, "int_ru_cedar", ao=0.95)
    for k in range(1, 6):
        xr = x0 + (x1 - x0) * k / 6
        ys = [p[1] for p in void]
        seg = R.clip_convex(void, xr - 0.08, -400.0, xr + 0.08, 0.0)
        if not seg:
            continue
        ya, yb = min(p[1] for p in seg), max(p[1] for p in seg)
        prev = None
        for j in range(7):
            yy = ya + (yb - ya) * j / 6
            dy = abs(yy - yc)
            zz = z1 + 1.2 * max(0.0, 1.0 - (dy / 5.5) ** 2) + 0.25 * math.sin((xr - x0) / 3.0) - 0.06
            cur = (xr + 0.6 * math.sin(j * 0.5), yy, zz)
            if prev is not None:
                V.poly([(prev[0] - 0.12, prev[1], prev[2]), (prev[0] + 0.12, prev[1], prev[2]), (cur[0] + 0.12, cur[1], cur[2]),
                        (cur[0] - 0.12, cur[1], cur[2])], "int_ru_slat_dark", normal_hint=(0, 0, -1), ao=0.8)
            prev = cur
    # pendant downlights hanging into the atrium (ru_atrium_enr_lounge)
    for (px, py) in ((-408.0, -270.5), (-402.5, -268.0), (-405.5, -273.5)):
        P.lights.append(K.Light((px, py, 21.0), radius=14.0, strength=0.30, color=LIGHT_WARM))
    C.poly([(p[0], p[1], z1) for p in reversed(void)], K.COL)
    RZ.kit_add(P, "L3", tag="atrium_top")


def atrium_lounge(RZ):
    """Ground-floor lounge (ru_atrium_enr_lounge, ru_atrium_enr_vertical): blue patterned carpet insets under navy /
    taupe club chairs, orange swivel chairs and taupe coffee tables; the giant orange UF letters on the gator-skin
    wall (ru_atrium_uf_letters_flickr: plan 'UF Letters' (-409.5, -264.6)), the Swamp Boss gator head (plan), the free
    library (plan), navy gator tracks in the terrazzo (ru_floor_gator_tracks)."""
    F = RZ.floors["G"]
    z = F.z
    P = K.Prop("atrium_lounge")
    V, C = P.visual, P.collision
    west = F.zone("atrium")
    east = F.zone("atrium_east")
    l1v = RZ.floors["L1"].voids
    # carpet insets (overlay at the floor height; the terrazzo base is 2 cm lower)
    rugs = [[(-412.6, -274.2), (-405.0, -274.7), (-404.2, -267.2), (-412.5, -267.6)],
            [(-392.6, -281.8), (-385.0, -281.8), (-385.0, -275.2), (-391.0, -275.2)]]
    for rug in rugs:
        R.floor_poly(V, R.ccw(rug), z, "int_ru_carpet_atrium", step=3.0)
    # furniture clusters on the rugs: two club chairs + a swivel chair around a coffee table
    clusters = [((-410.3, -270.9), 0.0), ((-406.6, -270.5), 15.0), ((-410.0, -268.6), 180.0), ((-406.9, -273.0), 190.0),
                ((-389.0, -278.0), 0.0), ((-387.3, -280.4), 200.0)]
    k = 0
    for (cx, cy), rot in clusters:
        RZ.kit_add(R.coffee_table(1.1, 0.6, col=False), "G", tag=f"lounge_table_{k}", x=cx, y=cy, facing=rot)
        K.col_box(C, cx - 1.6, cy - 1.6, z, cx + 1.6, cy + 1.6, z + 0.48, K.COL_NOCAM)
        for j, (dx, dy, f, kind) in enumerate(((-1.1, 0.0, 90.0, "club"), (1.1, 0.0, 270.0, "club"),
                                               (0.0, 1.0, 180.0, "swivel"), (0.0, -1.05, 0.0, "club2"))):
            a = math.radians(rot)
            px = cx + dx * math.cos(a) + dy * math.sin(a)
            py = cy - dx * math.sin(a) + dy * math.cos(a)
            if kind == "swivel":
                prop = R.lounge_chair("int_fabric_orange", swivel=True, col=False)
            elif kind == "club2":
                prop = R.lounge_chair("int_ru_fabric_taupe", "int_ru_fabric_navy", col=False)
            else:
                prop = R.lounge_chair(col=False)
            RZ.kit_add(prop, "G", tag=f"lounge_chair_{k}_{j}", x=px, y=py, facing=(f + rot) % 360)
        k += 1
    # UF letters (facing south) on the gator-skin wall panel behind them
    RZ.kit_add(R.uf_letters(2.6, 0.7), "G", tag="uf_letters", x=-409.4, y=-265.6, facing=180.0)
    wall_a, wall_b = (-414.0, -264.36), (-404.6, -264.36)
    R.panel(V, wall_a, wall_b, z, z + 5.3, "int_ru_gator_skin", off=0.13, u0=0.0, u1=math.dist(wall_a, wall_b) / 1.4,
            v0=0.0, v1=5.3 / 1.4)
    R.panel(V, (-413.7, -264.36), (-404.9, -264.36), z + 4.5, z + 5.1, "int_ru_sign_union", off=0.16, glow=False)
    # Swamp Boss gator head (plan object at (-397.3, -271.1)), under the stair landing; free library (plan)
    RZ.kit_add(R.gator_head(1.0), "G", tag="swamp_boss", x=-397.3, y=-271.1, facing=90.0)
    RZ.kit_add(R.free_library(4.6, 1.5), "G", tag="free_library", x=-386.1, y=-271.2, facing=270.0)
    # gator tracks: footprints along a winding steel strip from the South Terrace doors into the lounge
    path = [(-385.0, -284.6), (-387.5, -281.0), (-391.5, -278.6), (-395.0, -278.2), (-399.5, -276.6)]
    for (pa, pb) in zip(path, path[1:]):
        V.poly([(pa[0] - 0.03, pa[1], z + 0.002), (pb[0] - 0.03, pb[1], z + 0.002), (pb[0] + 0.03, pb[1], z + 0.002),
                (pa[0] + 0.03, pa[1], z + 0.002)], "int_ru_steel", normal_hint=(0, 0, 1))
    for i in range(14):
        s = i / 13.0
        segs = len(path) - 1
        si = min(segs - 1, int(s * segs))
        f = s * segs - si
        pa, pb = path[si], path[si + 1]
        cx, cy = pa[0] + (pb[0] - pa[0]) * f, pa[1] + (pb[1] - pa[1]) * f
        d = _unit2(pa, pb)
        side = 0.35 if i % 2 else -0.35
        px, py = cx - d[1] * side, cy + d[0] * side
        ang = math.atan2(d[1], d[0])
        pts = []
        for (u, v) in ((-0.18, -0.18), (0.18, -0.18), (0.18, 0.18), (-0.18, 0.18)):
            pts.append((px + u * math.cos(ang) - v * math.sin(ang), py + u * math.sin(ang) + v * math.cos(ang), z + 0.004))
        V.poly(pts, "int_ru_gator_track", uvs=[(0, 1), (0, 0), (1, 0), (1, 1)], normal_hint=(0, 0, 1))
    RZ.kit_add(P, "G", tag="atrium_lounge")
    RZ.points.setdefault("atrium", {})["lounge"] = {"name": "interior_atrium_lounge", "p": [-404.0, -271.0, 0.0],
                                                    "kind": "ground"}
    RZ.points["atrium"]["uf_letters_top"] = {"name": "interior_uf_letters_top", "p": [-411.33, -265.6, 2.95],
                                             "kind": "ground"}


def level1_extras(RZ):
    """Level 1 by the north entrance: the Info Desk (plan object; no photo: inferred), the Putting Green, RecRe Box
    and Giant Chess Board (plan objects by the east stair), the FOOD COURT / wayfinding signs."""
    F = RZ.floors["L1"]
    z = F.z
    RZ.kit_add(R.info_desk(3.0), "L1", tag="info_desk", x=-397.7, y=-261.0, z=z, facing=180.0)
    P = K.Prop("l1_extras")
    V, C = P.visual, P.collision
    R.panel(V, (-399.2, -259.95), (-396.2, -259.95), z + 2.6, z + 3.4, "int_ru_sign_info", off=0.0, glow=True)
    # putting green (plan (-370, -260)): a green carpet with a cup
    pg = [(-370.0, -260.7), (-368.4, -260.7), (-368.4, -259.6), (-370.0, -259.6)]
    R.floor_poly(V, R.ccw(pg), z + 0.02, "int_ru_gator_green", step=9.0)
    # giant chess board (plan (-365.2, -263.8))
    for i in range(4):
        for j in range(4):
            x0, y0 = -366.5 + i * 0.62, -265.2 + j * 0.7
            V.poly([(x0, y0, z + 0.01), (x0 + 0.62, y0, z + 0.01), (x0 + 0.62, y0 + 0.7, z + 0.01), (x0, y0 + 0.7, z + 0.01)],
                   "int_ru_white" if (i + j) % 2 else "int_ru_black", normal_hint=(0, 0, 1))
    for i, (cx, cy) in enumerate(((-366.0, -264.8), (-364.8, -263.0), (-365.4, -264.1), (-364.3, -264.5))):
        R.cyl(V, cx, cy, 0.18, z, z + 0.7, "int_ru_white" if i % 2 else "int_ru_black", n=6)
    RZ.kit_add(P, "L1", tag="l1_extras")


DRESSERS.extend([atrium_stairs, atrium_top, atrium_lounge, level1_extras])


# ================================================================== Ground: Game Room + Gator Esports Center
LANES_ORIGIN = (-445.35, -308.3)        # foul line centre (layout props_extra bowling_lanes: pins at the south wall)


def game_room(RZ):
    """The Game Room (Ground, under the food court; 2025-26 renovation photos ru_gr_*): 14 Brunswick lanes running
    south with the pins at the south wall, navy curved booth pits behind the approaches, the black overhead truss
    with score monitors, the video wall over the pins; the billiards hall (9 tables + snooker, square LED frames,
    blue / orange carpet) in the north-west; table tennis, air hockey and foosball by the high ribbon windows;
    arcade cabinets under hex neon; the service desk with the REITZ UNION GAME ROOM wall graphic."""
    F = RZ.floors["G"]
    z = F.z
    lx, ly = LANES_ORIGIN
    lanes = R.bowling_lane_set(14)
    RZ.kit_add(lanes, "G", tag="bowling_lanes", x=lx, y=ly, facing=0.0)
    pitch, x0 = lanes.info["pitch"], lanes.info["lanes_x0"]
    P = K.Prop("game_room_misc")
    V, C = P.visual, P.collision
    # booth pits behind the approaches (one per lane pair), facing the lanes (south), ball racks between them
    for i in range(7):
        bx = lx + x0 + 0.11 + (2 * i + 1) * pitch - 0.055
        RZ.kit_add(R.booth(2.9), "G", tag=f"booth_{i}", x=bx, y=ly + 6.6, facing=180.0)
        if i < 6:
            RZ.kit_add(R.ball_rack(1.1), "G", tag=f"ball_rack_{i}", x=bx + pitch, y=ly + 6.2, facing=0.0)
    # billiards hall (ru_gr_billiards_room): gator-scale carpet, two rows of tables along the dark north wall under
    # square LED frames (9 pool tables + the snooker table), cue racks on the wall
    carpet = [(-459.2, -297.2), (-440.6, -297.2), (-440.6, -282.3), (-459.2, -282.3)]
    R.floor_poly(V, R.ccw(carpet), z, "int_ru_carpet_billiards", step=4.5)
    k = 0
    for ty, xs in ((-285.3, (-456.0, -451.3, -446.6, -441.9)), (-290.8, (-456.0, -451.3, -446.6)),
                   (-295.0, (-456.0, -451.3, -446.6))):
        for tx in xs:
            if k >= 9:
                break
            RZ.kit_add(R.billiard_table(), "G", tag=f"pool_{k}", x=tx, y=ty, facing=0.0)
            RZ.kit_add(R.led_frame(3.4, 2.2, z + 3.6), "G", tag=f"pool_led_{k}", x=tx, y=ty, facing=0.0)
            k += 1
    RZ.kit_add(R.billiard_table(3.57, 1.78), "G", tag="snooker", x=-437.2, y=-294.6, facing=0.0)
    RZ.kit_add(R.led_frame(4.0, 2.4, z + 3.6), "G", tag="snooker_led", x=-437.2, y=-294.6, facing=0.0)
    for j, cx_ in enumerate((-457.2, -452.6, -447.9, -443.2)):
        RZ.kit_add(R.cue_rack(), "G", tag=f"cue_rack_{j}", x=cx_, y=-282.3, z=z, facing=180.0)
    # wall graphics: GAME ROOM over the billiards (north wall), and by the service desk
    R.panel(V, (-458.6, -282.25), (-450.0, -282.25), z + 1.4, z + 5.2, "int_ru_sign_gameroom", off=0.12)
    R.panel(V, (-433.0, -289.95), (-426.0, -289.95), z + 1.2, z + 4.7, "int_ru_sign_gameroom", off=0.12)
    # service desk (plan object 'Game Room Service Desk'): L-shaped counter, navy front, white top
    for (ax0, ay0, ax1, ay1) in ((-441.4, -291.2, -440.5, -286.9), (-441.4, -291.3, -432.9, -290.4)):
        V.box(ax0, ay0, z, ax1, ay1, z + 1.05, "int_ru_uf_blue", faces="+x-x+y-y")
        V.box(ax0 - 0.05, ay0 - 0.05, z + 1.05, ax1 + 0.05, ay1 + 0.05, z + 1.1, "int_ru_white", faces="+x-x+y-y+z")
        K.col_box(C, ax0, ay0, z, ax1, ay1, z + 1.1, K.COL_NOCAM)
    # table games along the east side (ribbon windows: ru_gr_foosball_windows, ru_gr_ping_pong)
    RZ.kit_add(R.ping_pong(), "G", tag="ping_pong_1", x=-427.0, y=-299.8, facing=0.0)
    RZ.kit_add(R.ping_pong(), "G", tag="ping_pong_2", x=-427.0, y=-305.0, facing=0.0)
    RZ.kit_add(R.air_hockey(), "G", tag="air_hockey_1", x=-428.0, y=-310.6, facing=90.0)
    RZ.kit_add(R.air_hockey(), "G", tag="air_hockey_2", x=-428.0, y=-314.2, facing=90.0)
    RZ.kit_add(R.foosball(), "G", tag="foosball_1", x=-423.8, y=-318.0, facing=90.0)
    RZ.kit_add(R.foosball(), "G", tag="foosball_2", x=-428.2, y=-318.0, facing=90.0)
    # arcade row along the south wall (east part) under hex neon (ru_gr_arcade, ru_gr_arcade_2)
    for i in range(11):
        RZ.kit_add(R.arcade_cabinet(), "G", tag=f"arcade_{i}", x=-432.2 + i * 0.95, y=-329.4, facing=0.0)
    for i in range(3):
        R.panel(V, (-432.0 + i * 3.4 + 2.8, -330.25), (-432.0 + i * 3.4, -330.25), z + 2.3, z + 3.7, "int_ru_hex_neon",
                off=0.12, glow=True)
    # ceiling fans over the booth pits (ru_gr_lanes_overview_2)
    for i in range(4):
        fx, fy = lx - 9.0 + i * 6.0, ly + 7.5
        zc = z + CLEAR["G"]
        V.box(fx - 0.04, fy - 0.04, zc - 0.6, fx + 0.04, fy + 0.04, zc, "int_ru_black", faces="+x-x+y-y")
        for a in range(4):
            ang = a * math.pi / 2 + 0.3
            bx, by = fx + 0.75 * math.cos(ang), fy + 0.75 * math.sin(ang)
            V.poly([(fx, fy, zc - 0.6), (bx + 0.1 * math.sin(ang), by - 0.1 * math.cos(ang), zc - 0.62),
                    (bx - 0.1 * math.sin(ang), by + 0.1 * math.cos(ang), zc - 0.62)], "int_ru_black", normal_hint=(0, 0, -1))
    # lights over the lanes (the masking + video wall glow, the approach troffers)
    P.lights.append(K.Light((lx, ly - 18.0, z + 4.0), radius=12.0, strength=0.25, color=(0.7, 0.8, 1.0)))
    RZ.kit_add(P, "G", tag="game_room_misc")
    pts = RZ.points.setdefault("game_room", {})
    pts["foul_line"] = {"name": "interior_bowling_foul_line", "p": [lx, ly + 1.0, z], "kind": "ground"}
    pts["head_pin_lane_7"] = {"name": "interior_bowling_pins_lane7", "p": [lx - 0.85, ly - 17.0, z], "kind": "ground"}
    pts["billiards"] = {"name": "interior_billiards", "p": [-447.2, -287.4, z], "kind": "ground"}


def esports(RZ):
    """Gator Esports Center (Ground; builder photos ru_es_oelrich_*, ru_es_overview, ru_es_pods): a long narrow
    dark room off the Game Room: PC stations with blue edge light along the west wall and a back-to-back island,
    the lit GATOR ESPORTS CENTER sign on the end wall, white hex neon on the charcoal hex walls, a red bench,
    couch co-op screens at the north end."""
    F = RZ.floors["G"]
    z = F.z
    zn = F.zone("gator_esports_center")
    P = K.Prop("esports_misc")
    V, C = P.visual, P.collision
    # west wall row (facing west) + a double island in the middle (south half)
    RZ.kit_add(R.esports_row(12, double=False), "G", tag="es_row_west", x=-465.95, y=-298.0, facing=90.0)
    RZ.kit_add(R.esports_row(6, double=True), "G", tag="es_island", x=-461.6, y=-303.0, facing=90.0)
    # red bench along the east wall (north part) (ru_es_oelrich_9188)
    V.box(-460.1, -296.0, z, -459.5, -284.0, z + 0.45, "int_ru_red", faces="+x-x+y-y+z")
    K.col_box(C, -460.1, -296.0, z, -459.5, -284.0, z + 0.45, K.COL_NOCAM)
    # couch co-op screens at the north end (ru_es_oelrich_9003)
    for i, yy in enumerate((-280.0, -283.0)):
        R.panel(V, (-465.6, yy - 0.9), (-465.6, yy + 0.9), z + 1.1, z + 2.1, "int_ru_game_screen", off=0.1, glow=True)
        RZ.kit_add(R.sofa(1.8, "int_ru_leather_grey"), "G", tag=f"es_couch_{i}", x=-462.8, y=yy, facing=270.0)
    # console stations along the east wall, south half (ru_es_overview: TVs on low black cabinets)
    for i, yy in enumerate((-306.6, -304.2, -301.8, -299.4)):
        V.box(-460.1, yy - 1.0, z, -459.55, yy + 1.0, z + 0.75, "int_ru_black", faces="-x+y-y+z")
        K.col_box(C, -460.1, yy - 1.0, z, -459.55, yy + 1.0, z + 0.75, K.COL_NOCAM)
        R.panel(V, (-459.75, yy + 0.65), (-459.75, yy - 0.65), z + 0.95, z + 1.75, "int_ru_game_screen", off=0.0,
                glow=True)
        RZ.kit_add(R.lounge_chair("int_ru_black", "int_ru_black", w=0.6, d=0.6, col=False), "G", tag=f"es_console_chair_{i}",
                   x=-461.0, y=yy, z=z, facing=270.0)
    # the lit GATOR ESPORTS CENTER sign across the south end wall (facing north), a blue LED cove over it, hex
    # neon clusters on both long walls, blue cove strips along the ceiling edges (ru_es_overview, ru_es_pods)
    R.panel(V, (-459.6, -308.95), (-465.7, -308.95), z + 2.7, z + 4.3, "int_ru_sign_esports", off=0.1, glow=True)
    V.box(-465.7, -308.95, z + 4.45, -459.6, -308.75, z + 4.55, "int_ru_led", faces="+y-z", glow=True,
          tint=(0.35, 0.5, 1.0))
    P.lights.append(K.Light((-462.6, -307.0, z + 3.5), radius=6.0, strength=0.35, color=(0.75, 0.82, 1.0)))
    for k, yy in enumerate(range(-305, -279, 4)):
        if k % 2 == 0 and yy > -298:
            R.panel(V, (-459.5, yy + 1.2), (-459.5, yy - 1.2), z + 2.0, z + 3.8, "int_ru_hex_neon", off=0.02, glow=True)
        elif k % 2 == 1:
            R.panel(V, (-465.85, yy - 1.2), (-465.85, yy + 1.2), z + 2.0, z + 3.8, "int_ru_hex_neon", off=0.02, glow=True)
    for xx, sgn in ((-459.6, -1), (-465.8, 1)):
        V.box(min(xx, xx + 0.12 * sgn), -308.8, z + 4.9, max(xx, xx + 0.12 * sgn), -277.2, z + 4.96, "int_ru_led",
              faces="-z", glow=True, tint=(0.3, 0.45, 1.0))
    # dome pendant lights + blue glow (the bake: dim room, cool light)
    for yy in range(-306, -278, 4):
        R.cyl(V, -462.6, yy, 0.35, z + 4.6, z + 4.8, "int_ru_glass_blue", n=6, top=False, bottom=True)
        P.lights.append(K.Light((-462.6, yy, z + 4.2), radius=5.0, strength=0.28, color=(0.55, 0.65, 1.0)))
    RZ.kit_add(P, "G", tag="esports_misc")
    RZ.points.setdefault("game_room", {})["esports"] = {"name": "interior_esports", "p": [-462.4, -293.0, z],
                                                         "kind": "ground"}


DRESSERS.extend([game_room, esports])


# ================================================================== Level 1: food court
SERVERY_FRONTS = [   # (wall points a -> b on the servery outline, generic sign, back-wall paint, side paint)
    ((-447.9, -310.6), (-453.1, -310.4), "int_ru_vend_wok", "int_ru_red", "int_ru_wall_cream"),
    ((-441.0, -312.0), (-446.5, -310.9), "int_ru_vend_taco", "int_ru_paint_sky", "int_ru_paint_lime"),
    ((-435.5, -309.8), (-440.0, -312.1), "int_ru_vend_mac", "int_ru_paint_lime", "int_ru_paint_sky"),
    ((-433.2, -303.0), (-433.2, -307.4), "int_ru_vend_smoothie", "int_ru_paint_lime", "int_ru_paint_sky"),
    ((-433.2, -297.4), (-433.2, -302.2), "int_ru_vend_burger", "int_ru_uf_blue", "int_ru_wall_cream"),
    ((-424.3, -291.6), (-424.3, -296.6), "int_ru_vend_pizza", "int_ru_paint_sky", "int_ru_paint_lime"),
    ((-424.3, -286.6), (-424.3, -290.8), "int_ru_vend_halal", "int_ru_black", "int_ru_wall_cream"),
    ((-455.5, -302.0), (-455.5, -307.2), "int_ru_vend_coffee", "int_ru_cherry", "int_ru_wall_cream"),
]


def food_court(RZ):
    """Level 1 food court (ru_food_court_counter_2023, ru_food_court_sonic_2025, ru_dining_windows, OSM food court
    outline w1315821081): the enclosed vendor block (servery) with its storefronts along the curved front, the
    tan / brown checker queue ring under a cream curved soffit, the grey-beige tiled seating hall with white
    columns, wood + navy chairs, high-tops along the curved SE glass."""
    F = RZ.floors["L1"]
    z = F.z
    serv = F.zone("food_court_servery")
    P = K.Prop("food_court_misc")
    V, C = P.visual, P.collision
    fc = F.overlays.get("food_court")
    # seating-hall tile (overlay at the floor height over the OSM food court outline, minus the servery)
    if fc:
        R.floor_poly(V, fc, z - 0.01, "int_ru_fc_tile", step=FLOOR_STEP, holes=[serv.poly])
    # queue ring: a 2.6 m band of checker tile around the servery
    ring = R.offset_poly(serv.poly, 2.6)
    R.floor_poly(V, ring, z, "int_ru_fc_checker", step=FLOOR_STEP, holes=[R.offset_poly(serv.poly, 0.12)])
    # curved soffit band over the servery front (cream), at 4.0 m (photo: ~3 m real), 1.8 m deep
    zs = z + 4.0
    so = R.offset_poly(serv.poly, 1.8)
    for (a, b), (a2, b2) in zip(R.edges(serv.poly), R.edges(so)):
        V.poly([(a[0], a[1], zs), (b[0], b[1], zs), (b2[0], b2[1], zs), (a2[0], a2[1], zs)], "int_ru_soffit",
               normal_hint=(0, 0, -1), ao=0.95)
        R.quad_wall(V, a2, b2, zs, zs + 0.7, "int_ru_soffit", ao=0.9)
        # downlights in the soffit
        mx, my = (a[0] + a2[0] + b[0] + b2[0]) / 4, (a[1] + a2[1] + b[1] + b2[1]) / 4
        if math.dist(a, b) > 2.0:
            V.poly([(mx - 0.12, my - 0.12, zs - 0.01), (mx - 0.12, my + 0.12, zs - 0.01), (mx + 0.12, my + 0.12, zs - 0.01),
                    (mx + 0.12, my - 0.12, zs - 0.01)], "int_ru_led", glow=True)
            P.lights.append(K.Light((mx, my, zs - 0.4), radius=4.0, strength=0.2, color=LIGHT_WARM))
    # storefronts: the servery wall gets openings (build_floor reads RZ.storefront_holes) and a counter prop
    for i, (a, b, sign, back, side) in enumerate(SERVERY_FRONTS):
        w = math.dist(a, b)
        cxm, cym = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        # the storefront faces OUT of the servery: right-hand normal of a -> b for a CCW outline is outward
        nx, ny = (b[1] - a[1]) / w, -(b[0] - a[0]) / w
        if R.pip((cxm + nx * 0.5, cym + ny * 0.5), serv.poly):
            nx, ny = -nx, -ny
        facing = math.degrees(math.atan2(nx, ny)) % 360.0
        RZ.kit_add(R.storefront(w, sign, back, side, h=3.9), "L1", tag=f"storefront_{i}", x=cxm, y=cym, z=z, facing=facing)
    # seating: tables in the south hall, the east hall and along the curved glass
    k = 0
    for yy in (-316.0, -319.5, -323.0, -326.5):
        for xx in (-452.0, -447.5, -443.0, -438.5, -434.0, -429.5, -425.0):
            if R.pip((xx, yy), F.zone("l1_corridor_08").poly):
                RZ.kit_add(R.cafe_table_set(chair_mat="int_ru_fabric_navy", frame="int_ru_wood_panel"), "L1",
                           tag=f"fc_table_{k}", x=xx, y=yy, z=z, facing=(k * 37) % 90)
                k += 1
    for (xx, yy) in ((-420.0, -300.0), (-417.5, -306.0), (-420.0, -312.0), (-416.0, -292.5), (-410.5, -298.0)):
        RZ.kit_add(R.cafe_table_set(chair_mat="int_ru_fabric_navy", frame="int_ru_wood_panel"), "L1", tag=f"fc_table_{k}",
                   x=xx, y=yy, z=z, facing=15.0 * (k % 3))
        k += 1
    for j, (xx, yy) in enumerate(((-411.6, -309.5), (-411.0, -304.0), (-408.6, -299.6), (-405.4, -295.4),
                                   (-401.5, -291.6), (-397.0, -287.8))):
        RZ.kit_add(R.high_top(), "L1", tag=f"fc_hightop_{j}", x=xx, y=yy, z=z)
    # white square columns of the hall (photo; positions inferred on an 8 m grid)
    for (cx, cy) in ((-446.0, -320.5), (-438.0, -320.5), (-430.0, -320.5), (-418.5, -296.0), (-418.5, -304.0)):
        V.box(cx - 0.3, cy - 0.3, z, cx + 0.3, cy + 0.3, z + F.clear, "int_ru_white", faces="+x-x+y-y")
        K.col_box(C, cx - 0.3, cy - 0.3, z, cx + 0.3, cy + 0.3, z + F.clear, K.COL)
    # FOOD COURT sign over the queue ring (east)
    R.panel(V, (-424.0, -287.5), (-424.0, -283.0), z + 4.75, z + 5.35, "int_ru_sign_foodcourt", off=0.0, glow=True)
    RZ.kit_add(P, "L1", tag="food_court_misc")
    RZ.points.setdefault("food_court", {})["center"] = {"name": "interior_food_court_center", "p": [-438.0, -318.0, z],
                                                         "kind": "ground"}


DRESSERS.extend([food_court])


# ================================================================== Level 2 + 3: ballrooms, auditorium, gallery
def _wall_strip(V, a, b, z0, z1, mat, off=0.02, tile=None, glow=False):
    """A strip on the wall line a -> b, facing RIGHT of a -> b (tile: projected UVs; once otherwise)."""
    L = math.dist(a, b)
    if L < 0.05:
        return
    nx, ny = (b[1] - a[1]) / L, -(b[0] - a[0]) / L
    pa = (a[0] + nx * off, a[1] + ny * off)
    pb = (b[0] + nx * off, b[1] + ny * off)
    V.poly([(pa[0], pa[1], z0), (pb[0], pb[1], z0), (pb[0], pb[1], z1), (pa[0], pa[1], z1)], mat, glow=glow, ao=1.0)


def _room_inside_edges(zn, inset=0.1):
    """The room polygon's edges oriented so their right-hand normal points INTO the room (CW order), inset."""
    poly = R.offset_poly(zn.poly, -inset)
    cwp = list(reversed(R.ccw(poly)))
    return R.edges(cwp)


def grand_ballroom(RZ):
    """Grand Ballroom (L2, west wing, double height; ru_os_grand_ballroom_1..4): royal-blue wave carpet, light-grey
    walls with a darker dado, pilasters, the band of white 3-D triangular acoustic panels, four drop-down screens,
    walnut doors (the plan's doors), a coffered ceiling with luminous slat fields inside a downlit soffit, the
    clerestory band high on the north wall; theatre rows facing the stage + podium on the south wall."""
    F = RZ.floors["L2"]
    z = F.z
    zn = F.zone("grand_ballroom")
    st = zn.style
    zc = z + st["clear"]
    P = K.Prop("grand_ballroom")
    V, C = P.visual, P.collision
    x0, y0, x1, y1 = R.bbox(zn.poly)
    # wall bands on every inside edge (ru_os_grand_ballroom_1..4): slate dado to the door heads with a white trim,
    # light-grey upper wall, a band of white 3-D acoustic triangles beside the drop-down screens, white
    # pilasters; screens: three on the stage (south) wall, two on the north wall; clerestory high on the north wall
    for a, b in _room_inside_edges(zn, 0.11):
        L = math.dist(a, b)
        if L < 1.0:
            continue
        dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx, ny = dy, -dx
        mid_y = (a[1] + b[1]) / 2
        _wall_strip(V, a, b, z + 0.1, z + 3.3, "int_ru_wall_slate", off=0.0)
        _wall_strip(V, a, b, z + 3.3, z + 3.4, "int_ru_white", off=0.01)
        screens = []
        if L > 20.0:
            ts = (0.2, 0.5, 0.8) if mid_y < y0 + 1.0 else (0.3, 0.7)
            screens = [(L * t_ - 2.7, L * t_ + 2.7) for t_ in ts]
        for s0, s1 in screens:
            R.panel(V, (a[0] + dx * s0, a[1] + dy * s0), (a[0] + dx * s1, a[1] + dy * s1), z + 4.0, z + 7.0,
                    "int_ru_proj_screen", off=0.05)
            sc = (s0 + s1) / 2
            P.lights.append(K.Light((a[0] + dx * sc + nx * 1.5, a[1] + dy * sc + ny * 1.5, z + 5.5), radius=5.0,
                                    strength=0.18, color=LIGHT_COOL))
        # acoustic band in the gaps between screens (and on the short walls)
        cuts = [(0.0, 0.0)] + screens + [(L, L)]
        for (p0, p1), (q0, q1) in zip(cuts, cuts[1:]):
            g0, g1 = p1 + 0.6, q0 - 0.6
            if g1 - g0 > 1.2:
                _wall_strip(V, (a[0] + dx * g0, a[1] + dy * g0), (a[0] + dx * g1, a[1] + dy * g1), z + 3.7, z + 4.9,
                            "int_ru_acoustic", off=0.04)
        # pilasters every ~5.5 m (kept clear of the screens)
        n = max(1, int(L / 5.5))
        for k in range(1, n):
            sk = L * k / n
            if any(s0 - 0.5 < sk < s1 + 0.5 for s0, s1 in screens):
                continue
            px, py = a[0] + dx * sk, a[1] + dy * sk
            q0 = (px - dx * 0.4, py - dy * 0.4)
            q1 = (px + dx * 0.4, py + dy * 0.4)
            R.seg_box(V, (q0[0] + nx * 0.14, q0[1] + ny * 0.14), (q1[0] + nx * 0.14, q1[1] + ny * 0.14), 0.14, z, zc - 1.0,
                      "int_ru_white", faces="sideends")
        if mid_y > y1 - 1.0:          # north wall: clerestory band high up (ru_os_grand_ballroom_3)
            ca, cb = (a[0] + dx * 1.0, a[1] + dy * 1.0), (b[0] - dx * 1.0, b[1] - dy * 1.0)
            _wall_strip(V, ca, cb, z + 8.6, z + 10.0, "int_ru_window_view", off=0.03)
            mullions(V, (ca[0] + nx * 0.05, ca[1] + ny * 0.05), (cb[0] + nx * 0.05, cb[1] + ny * 0.05), z + 8.6, z + 10.0,
                     bay=2.2, t=0.05)
    # stage + podium (south wall, centre) and theatre rows facing it
    cxs = (x0 + x1) / 2
    RZ.kit_add(R.stage_platform(9.0, 3.2, h=0.6), "L2", tag="gb_stage", x=cxs, y=y0 + 2.0, z=z, facing=0.0)
    RZ.kit_add(R.podium(), "L2", tag="gb_podium", x=cxs + 3.0, y=y0 + 2.4, z=z + 0.6, facing=0.0)
    RZ.kit_add(R.chair_rows(14, 30, pitch=0.95, aisle_every=10, aisle_w=1.6, kind="navy"), "L2", tag="gb_rows",
               x=cxs, y=y0 + 5.6, z=z, facing=180.0)
    # banquet rounds in the back third (photo 3 / 4 mix)
    for i, xx in enumerate((-506.0, -501.5, -475.5, -471.0)):
        for j, yy in enumerate((-254.0, -258.5)):
            RZ.kit_add(R.round_table(0.9, top="int_ru_drape"), "L2", tag=f"gb_round_{i}_{j}", x=xx, y=yy, z=z)
    # coffered ceiling: perimeter soffit 2.4 m wide at zc - 1.0 with downlights, 2 x 4 luminous coffers at zc
    zsof = zc - 1.0
    inner = (x0 + 2.4, y0 + 2.4, x1 - 2.4, y1 - 2.4)
    ring = [(x0, y0, x1, inner[1]), (x0, inner[3], x1, y1), (x0, inner[1], inner[0], inner[3]), (inner[2], inner[1], x1, inner[3])]
    for (rx0, ry0, rx1, ry1) in ring:
        V.poly([(rx0, ry0, zsof), (rx0, ry1, zsof), (rx1, ry1, zsof), (rx1, ry0, zsof)], "int_ru_white", ao=0.95)
    for (ax, ay), (bx_, by_) in R.edges([(inner[0], inner[1]), (inner[2], inner[1]), (inner[2], inner[3]), (inner[0], inner[3])]):
        R.quad_wall(V, (ax, ay), (bx_, by_), zsof, zc, "int_ru_white", ao=0.9)
    ncx, ncy = 4, 2
    bw = 0.8
    cw_ = (inner[2] - inner[0] - (ncx + 1) * bw) / ncx
    ch_ = (inner[3] - inner[1] - (ncy + 1) * bw) / ncy
    for i in range(ncx):
        for j in range(ncy):
            ax = inner[0] + bw + i * (cw_ + bw)
            ay = inner[1] + bw + j * (ch_ + bw)
            V.poly([(ax, ay, zc), (ax, ay + ch_, zc), (ax + cw_, ay + ch_, zc), (ax + cw_, ay, zc)], "int_ru_coffer",
                   uvs=[(0, 0), (0, ch_ / 1.2), (cw_ / 1.2, ch_ / 1.2), (cw_ / 1.2, 0)], glow=True)
            P.lights.append(K.Light((ax + cw_ / 2, ay + ch_ / 2, zc - 2.0), radius=12.0, strength=0.30, color=LIGHT_COOL))
    # beams between coffers (dropped 0.5 m)
    for i in range(ncx + 1):
        bx0 = inner[0] + i * (cw_ + bw)
        V.box(bx0, inner[1], zc - 0.5, bx0 + bw, inner[3], zc, "int_ru_white", faces="+x-x-z")
    for j in range(ncy + 1):
        by0 = inner[1] + j * (ch_ + bw)
        V.box(inner[0], by0, zc - 0.5, inner[2], by0 + bw, zc, "int_ru_white", faces="+y-y-z")
    # soffit downlights
    for k in range(18):
        t = k / 18.0
        for (px, py) in ((x0 + 1.2 + (x1 - x0 - 2.4) * t, y0 + 1.2), (x0 + 1.2 + (x1 - x0 - 2.4) * t, y1 - 1.2)):
            V.poly([(px - 0.12, py - 0.12, zsof - 0.01), (px - 0.12, py + 0.12, zsof - 0.01), (px + 0.12, py + 0.12, zsof - 0.01),
                    (px + 0.12, py - 0.12, zsof - 0.01)], "int_ru_led", glow=True)
            P.lights.append(K.Light((px, py, zsof - 0.5), radius=6.0, strength=0.18, color=LIGHT_WARM))
    RZ.kit_add(P, "L2", tag="grand_ballroom")
    RZ.points.setdefault("ballrooms", {})["grand_stage"] = {"name": "interior_grand_ballroom_stage", "p": [cxs, y0 + 2.0, z + 0.6],
                                                             "kind": "ground"}
    RZ.points["ballrooms"]["grand_center"] = {"name": "interior_grand_ballroom", "p": [cxs, (y0 + y1) / 2 + 6.0, z],
                                              "kind": "ground"}


def rion_ballroom(RZ):
    """Rion Ballroom (L3, south wing; ru_os_rion_ballroom): maple floor, white walls with dark-grey vertical panels,
    an acoustic tile ceiling crossed by red-brown wood slat beams, linear pendants, a small stage and theatre rows."""
    F = RZ.floors["L3"]
    z = F.z
    zn = F.zone("rion_ballroom")
    zc = z + zn.style["clear"]
    P = K.Prop("rion")
    V, C = P.visual, P.collision
    x0, y0, x1, y1 = R.bbox(zn.poly)
    for a, b in _room_inside_edges(zn, 0.11):
        L = math.dist(a, b)
        n = int(L / 3.2)
        dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        for k in range(1, n, 2):
            p0 = (a[0] + dx * (L * k / n - 0.6), a[1] + dy * (L * k / n - 0.6))
            p1 = (a[0] + dx * (L * k / n + 0.6), a[1] + dy * (L * k / n + 0.6))
            _wall_strip(V, p0, p1, z + 0.6, zc - 0.6, "int_ru_wall_grey", off=0.03)
    # wood slat beams across the ceiling (N-S) + linear pendants
    for k in range(1, 7):
        bx = x0 + (x1 - x0) * k / 7
        V.box(bx - 0.4, y0, zc - 0.45, bx + 0.4, y1, zc, "int_ru_cedar", faces="+x-x-z")
        V.box(bx + 2.0, y0 + 3.0, zc - 1.6, bx + 2.1, y1 - 3.0, zc - 1.55, "int_ru_led", faces="-z+x-x", glow=True)
        P.lights.append(K.Light((bx + 2.0, (y0 + y1) / 2, zc - 2.0), radius=11.0, strength=0.26, color=LIGHT_COOL))
    RZ.kit_add(R.stage_platform(6.0, 2.6, h=0.5), "L3", tag="rion_stage", x=(x0 + x1) / 2, y=y0 + 1.6, z=z, facing=0.0)
    RZ.kit_add(R.chair_rows(12, 24, pitch=0.95, aisle_every=12, aisle_w=1.6, kind="navy"), "L3", tag="rion_rows",
               x=(x0 + x1) / 2, y=y0 + 4.6, z=z, facing=180.0)
    RZ.kit_add(P, "L3", tag="rion")
    RZ.lights_skip.add("rion_ballroom")
    RZ.points.setdefault("ballrooms", {})["rion"] = {"name": "interior_rion_ballroom", "p": [(x0 + x1) / 2, y1 - 3.0, z],
                                                      "kind": "ground"}


def auditorium(RZ):
    """Auditorium (L2, 299 seats; ru_os_auditorium_1..3): navy seats with honey-wood arms on a raked floor, wood
    panel walls by the screen, navy accent walls, dark wood slat ceiling bands with white LED coves. The screen is
    on the west end wall (inferred from the plan: the angled stage walls)."""
    F = RZ.floors["L2"]
    z = F.z
    zn = F.zone("auditorium")
    zc = z + zn.style["clear"]
    P = K.Prop("auditorium")
    V, C = P.visual, P.collision
    x0, y0, x1, y1 = R.bbox(zn.poly)
    # stage at the west end + screen
    sx = x0 + 1.0
    V.box(x0 + 0.3, y0 + 3.0, z, x0 + 3.2, y1 - 3.0, z + 0.7, "int_ru_black", faces="+x+y-y+z",
          mats={"+z": "int_ru_wood_panel"})
    C.prism([(x0 + 0.3, y0 + 3.0), (x0 + 3.2, y0 + 3.0), (x0 + 3.2, y1 - 3.0), (x0 + 0.3, y1 - 3.0)], z, z + 0.7, K.COL,
            top=K.COL)
    R.panel(V, (x0 + 0.45, y0 + 4.0), (x0 + 0.45, y1 - 4.0), z + 1.8, z + 4.8, "int_ru_proj_screen", off=0.0)
    # screen wall navy, the angled walls beside it honey-wood panelling, the long side walls light grey with
    # tall wood panels at intervals (ru_os_auditorium_1..3)
    for a, b in _room_inside_edges(zn, 0.11):
        L = math.dist(a, b)
        if L < 0.6:
            continue
        mx = (a[0] + b[0]) / 2
        if mx < x0 + 2.5:
            _wall_strip(V, a, b, z + 0.1, zc - 0.3, "int_ru_wall_navy" if L > 4.0 else "int_ru_wood_panel", off=0.02)
        elif L > 8.0:
            dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            for k in range(1, int(L / 6.0) + 1):
                sk = L * k / (int(L / 6.0) + 1)
                _wall_strip(V, (a[0] + dx * (sk - 0.6), a[1] + dy * (sk - 0.6)), (a[0] + dx * (sk + 0.6), a[1] + dy * (sk + 0.6)),
                            z + 0.1, z + 3.6, "int_ru_wood_panel", off=0.03)
    # raked seating: rows step up 0.18 m toward the east; seat rows (aud texture from behind = navy backs)
    nrows = 11
    row_d = (x1 - x0 - 6.0) / nrows
    for r in range(nrows):
        rx0 = x0 + 5.0 + r * row_d
        zr = z + 0.18 * r
        if r > 0:
            V.box(rx0, y0 + 0.8, z, rx0 + row_d, y1 - 0.8, zr, "int_ru_carpet_aud", faces="+z-x",
                  mats={"-x": "int_ru_wall_navy"})
            C.prism([(rx0, y0 + 0.8), (rx0 + row_d, y0 + 0.8), (rx0 + row_d, y1 - 0.8), (rx0, y1 - 0.8)], z, zr, K.COL,
                    top=K.COL)
        rows = R.chair_rows(1, 22, pitch=row_d, aisle_every=11, aisle_w=1.2, kind="aud", seat_h=0.44)
        RZ.kit_add(rows, "L2", tag=f"aud_row_{r}", x=rx0 + 0.75, y=(y0 + y1) / 2, z=zr, facing=270.0)
    # ceiling: dark slat bands with LED coves (zone ceiling is int_ru_slat_dark) -> cove strips
    for k in range(1, 5):
        cx_ = x0 + (x1 - x0) * k / 5
        V.box(cx_ - 0.08, y0 + 1.0, zc - 0.25, cx_ + 0.08, y1 - 1.0, zc - 0.2, "int_ru_led", faces="-z", glow=True)
        P.lights.append(K.Light((cx_, (y0 + y1) / 2, zc - 0.8), radius=9.0, strength=0.24, color=LIGHT_WARM))
    RZ.kit_add(P, "L2", tag="auditorium")
    RZ.points.setdefault("ballrooms", {})["auditorium_stage"] = {"name": "interior_auditorium_stage",
                                                                  "p": [x0 + 1.8, (y0 + y1) / 2, z + 0.7], "kind": "ground"}


def gallery(RZ):
    """The Gallery (L2, by the Auditorium; ru_the_gallery): white walls, a black ceiling with track lights, a dark
    floor, framed art, Eames-style lounge chairs."""
    F = RZ.floors["L2"]
    z = F.z
    zn = F.zone("the_gallery")
    zc = z + zn.style["clear"]
    P = K.Prop("gallery")
    V = P.visual
    for a, b in _room_inside_edges(zn, 0.12):
        L = math.dist(a, b)
        if L < 3.5:
            continue
        dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        m = 0.8
        R.panel(V, (a[0] + dx * m, a[1] + dy * m), (b[0] - dx * m, b[1] - dy * m), z + 1.1, z + 2.7, "int_ru_art",
                off=0.02, u0=0.0, u1=max(1.0, round((L - 2 * m) / 3.0)))
    x0, y0, x1, y1 = R.bbox(zn.poly)
    for k in range(4):
        tx = x0 + 1.5 + (x1 - x0 - 3.0) * k / 3
        V.box(tx - 0.03, y0 + 1.0, zc - 0.15, tx + 0.03, y1 - 1.0, zc - 0.1, "int_ru_steel", faces="-z+x-x")
        P.lights.append(K.Light((tx, (y0 + y1) / 2, zc - 1.0), radius=6.5, strength=0.32, color=LIGHT_WARM))
    for j, (cx_, cy_) in enumerate(((-427.5, -255.0), (-425.5, -256.5), (-423.5, -255.2))):
        RZ.kit_add(R.lounge_chair("int_ru_black", "int_ru_black", w=0.7, d=0.75), "L2", tag=f"gallery_chair_{j}",
                   x=cx_, y=cy_, z=z, facing=30.0 * j)
    RZ.kit_add(P, "L2", tag="gallery")


# ================================================================== Ground: Senate Chamber
def senate_chamber(RZ):
    """Senate Chamber (G; ru_os_chamber): curved tiers of grey desks with navy high-back chairs facing the dais;
    a cherry wall with chevron reveals behind the dais, US and Florida flags, cream walls."""
    F = RZ.floors["G"]
    z = F.z
    zn = F.zone("senate_chamber")
    P = K.Prop("senate")
    V, C = P.visual, P.collision
    x0, y0, x1, y1 = R.bbox(zn.poly)
    cx_ = (x0 + x1) / 2
    # dais wall (north, on the wall's inside face) + dais
    north = max((e for e in _room_inside_edges(zn, 0.11) if math.dist(*e) > 10.0), key=lambda e: e[0][1] + e[1][1])
    (na, nb) = north
    def _on_north(x):
        t_ = (x - na[0]) / (nb[0] - na[0])
        return (x, na[1] + (nb[1] - na[1]) * t_)
    xa, xb = (cx_ + 4.5, cx_ - 4.5) if nb[0] < na[0] else (cx_ - 4.5, cx_ + 4.5)
    _wall_strip(V, _on_north(xa), _on_north(xb), z + 0.1, z + zn.style["clear"] - 0.05, "int_ru_chevron", off=0.03)
    V.box(cx_ - 5.0, y1 - 3.6, z, cx_ + 5.0, y1 - 0.2, z + 0.45, "int_ru_cherry", faces="+x-x-y+z",
          mats={"+z": "int_ru_carpet_aud"})
    C.prism([(cx_ - 5.0, y1 - 3.6), (cx_ + 5.0, y1 - 3.6), (cx_ + 5.0, y1 - 0.2), (cx_ - 5.0, y1 - 0.2)], z, z + 0.45,
            K.COL, top=K.COL)
    V.box(cx_ - 3.5, y1 - 3.3, z + 0.45, cx_ + 3.5, y1 - 2.6, z + 1.5, "int_ru_dais", faces="-y+x-x+z",
          mats={"+z": "int_ru_wall_grey"}, uvs={"-y": [(0, 0), (1, 0), (1, 1), (0, 1)]})
    K.col_box(C, cx_ - 3.5, y1 - 3.3, z + 0.45, cx_ + 3.5, y1 - 2.6, z + 1.5, K.COL_NOCAM, bottom=True)
    for fx, (u0, u1) in ((cx_ + 4.4, (0.0, 0.47)), (cx_ - 4.4, (0.53, 1.0))):
        V.box(fx - 0.03, y1 - 0.9, z + 0.45, fx + 0.03, y1 - 0.84, z + 3.0, "int_ru_steel", faces="+x-x+y-y")
        V.poly([(fx, y1 - 0.88, z + 2.0), (fx + 0.9, y1 - 0.88, z + 2.0), (fx + 0.9, y1 - 0.88, z + 2.9), (fx, y1 - 0.88, z + 2.9)],
               "int_ru_flags", uvs=[(u0, 0), (u1, 0), (u1, 1), (u0, 1)], normal_hint=(0, -1, 0))
    RZ.kit_add(R.senate_tiers(4, r0=7.0, dr=1.5, a0=-58.0, a1=58.0, rise=0.18, seg=8), "G", tag="senate_tiers",
               x=cx_, y=y1 - 1.5, z=z, facing=180.0)
    RZ.kit_add(P, "G", tag="senate")
    RZ.points.setdefault("rooms", {})["senate_dais"] = {"name": "interior_senate_dais", "p": [cx_, y1 - 1.8, z + 0.45],
                                                         "kind": "ground"}


# ================================================================== meeting rooms (G310-G330, 2315-2365, 2101-2108, 3305-3320)
def _room_frame(zn):
    """(origin at the accent wall centre, facing INTO the room, room width along the wall, depth) of a room."""
    aw = zn.style.get("accent_wall") if zn.style else None
    if aw is None:
        x0, y0, x1, y1 = R.bbox(zn.poly)
        return ((x0 + x1) / 2, y0, 0.0, x1 - x0, y1 - y0)
    a, b = aw
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    L = math.dist(a, b)
    dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    nx, ny = -dy, dx
    c = R.centroid(zn.poly)
    if (c[0] - mx) * nx + (c[1] - my) * ny < 0:
        nx, ny = -nx, -ny
    depth = max((p[0] - mx) * nx + (p[1] - my) * ny for p in zn.poly)
    facing = math.degrees(math.atan2(nx, ny)) % 360.0
    return (mx, my, facing, L, depth)


MEETING_KIND = {"meeting_G325": "classroom", "meeting_3305": "u_shape", "meeting_3310": "classroom",
                "meeting_2345": "boardroom", "meeting_2350": "boardroom", "meeting_2104": "boardroom",
                "meeting_2108": "boardroom", "meeting_2020": "boardroom"}


def meeting_rooms(RZ):
    """Every meeting room: carpet tile, white walls + one accent wall (royal blue on Ground, pale grey-blue upstairs),
    the white chair rail, linear LED ceilings (build_floor), a projector screen on the accent wall, framed art; set
    up as in the room photos: rows of black stacking chairs + a navy draped table (most rooms), classroom tables
    (G325, 3310), a U of tables (3305), a boardroom table + wall TV (2345 / 2350)."""
    for fid in ("G", "L2", "L3"):
        F = RZ.floors[fid]
        z = F.z
        for zn in F.walk_zones():
            if zn.type != "meeting_room":
                continue
            mx, my, facing, W, D = _room_frame(zn)
            kind = MEETING_KIND.get(zn.id, "rows")
            P = K.Prop("meeting_" + zn.id)
            V = P.visual
            f = math.radians(facing)
            fx, fy = math.sin(f), math.cos(f)          # into the room
            tx, ty = fy, -fx                           # along the wall (right of facing)
            # projector screen on the accent wall
            if W > 4.0 and D > 4.0:
                sw = min(3.6, W * 0.45)
                pa = (mx + tx * sw / 2 + fx * 0.14, my + ty * sw / 2 + fy * 0.14)
                pb = (mx - tx * sw / 2 + fx * 0.14, my - ty * sw / 2 + fy * 0.14)
                R.panel(V, pa, pb, z + 1.4, z + 3.6, "int_ru_proj_screen", off=0.0)
            if kind == "rows" and D > 5.0 and W > 4.0:
                rows = max(2, int((D - 3.4) / 0.95))
                per = max(4, int((W - 1.6 - 1.2) / 0.5))
                prop = R.chair_rows(rows, per, pitch=0.95, aisle_every=per // 2 if per > 10 else 0, aisle_w=1.2,
                                    kind="black")
                d0 = 2.6 + (rows - 1) * 0.95 + 0.45
                RZ.kit_add(prop, fid, tag=f"rows_{zn.id}", x=mx + fx * d0, y=my + fy * d0, z=z, facing=(facing + 180.0) % 360)
                # navy draped table by the accent wall (corner)
                RZ.kit_add(R.draped_table(1.6, 0.75), fid, tag=f"drape_{zn.id}",
                           x=mx + fx * 1.2 + tx * (W / 2 - 1.4), y=my + fy * 1.2 + ty * (W / 2 - 1.4), z=z, facing=facing)
            elif kind == "classroom" and D > 4.0:
                n = max(2, int((D - 2.8) / 1.6))
                for r in range(n):
                    for side in (-1, 1):
                        RZ.kit_add(R.folding_table(1.8, 0.6), fid, tag=f"class_{zn.id}_{r}_{side}",
                                   x=mx + fx * (2.4 + r * 1.6) + tx * side * 1.2,
                                   y=my + fy * (2.4 + r * 1.6) + ty * side * 1.2, z=z, facing=(facing + 180.0) % 360)
            elif kind == "u_shape" and D > 5.0:
                for (u, v, rot) in ((-1.6, 3.2, 90.0), (-1.6, 5.0, 90.0), (1.6, 3.2, 270.0), (1.6, 5.0, 270.0),
                                    (0.0, 6.3, 180.0)):
                    RZ.kit_add(R.folding_table(1.8, 0.6), fid, tag=f"u_{zn.id}_{u}_{v}",
                               x=mx + fx * v + tx * u, y=my + fy * v + ty * u, z=z, facing=(facing + rot) % 360)
            elif kind == "boardroom":
                c = R.centroid(zn.poly)
                L_ = max(2.4, min(5.0, D - 2.2))
                RZ.kit_add(R.folding_table(L_, 1.2, top="int_ru_wall_cream", chairs=3), fid, tag=f"board_{zn.id}",
                           x=c[0], y=c[1], z=z, facing=(facing + 90.0) % 360)
            RZ.kit_add(P, fid, tag=f"meeting_{zn.id}")


# ================================================================== Level 4, hotel, Lower Level
def level4(RZ):
    """Level 4 (tower): the Arredondo Cafe (olive carpet, wood + cherry chairs, full-height windows, a projection
    screen; ru_os_arredondo_cafe) and Matthew's Suite (grey-blue walls, white millwork, round tables with navy
    chairs, framed historic photos; ru_os_matthews_1..4)."""
    F = RZ.floors["L4"]
    z = F.z
    ar = F.zone("arredondo_cafe")
    k = 0
    for xx in (-451.0, -446.5, -442.0, -437.5, -433.0, -428.5, -425.5):
        for yy in (-260.5, -264.5):
            if R.pip((xx, yy), ar.poly) and R.poly_dist((xx, yy), ar.poly) > 1.0:
                RZ.kit_add(R.cafe_table_set(0.8, chair_mat="int_ru_fabric_taupe", frame="int_ru_cherry",
                                            top="int_ru_cherry"), "L4", tag=f"arr_table_{k}", x=xx, y=yy, z=z, facing=0.0)
                k += 1
    for yy in (-268.0, -271.5, -275.0):
        for xx in (-429.5, -425.5):
            if R.pip((xx, yy), ar.poly) and R.poly_dist((xx, yy), ar.poly) > 1.0:
                RZ.kit_add(R.cafe_table_set(0.8, chair_mat="int_ru_fabric_taupe", frame="int_ru_cherry",
                                            top="int_ru_cherry"), "L4", tag=f"arr_table_{k}", x=xx, y=yy, z=z, facing=0.0)
                k += 1
    ms = F.zone("matthews_suite")
    c = R.centroid(ms.poly)
    for j, (dx, dy) in enumerate(((-3.0, 1.6), (3.0, 1.6), (0.0, -1.8))):
        RZ.kit_add(R.round_table(0.75, top="int_ru_bed", chair_mat="int_ru_fabric_navy", chairs=7), "L4",
                   tag=f"matthews_round_{j}", x=c[0] + dx, y=c[1] + dy, z=z)
    P = K.Prop("matthews_photos")
    V = P.visual
    for a, b in _room_inside_edges(ms, 0.12):
        L = math.dist(a, b)
        if L > 3.0:
            dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            R.panel(V, (a[0] + dx * 0.6, a[1] + dy * 0.6), (b[0] - dx * 0.6, b[1] - dy * 0.6), z + 1.2, z + 2.4,
                    "int_ru_photos", off=0.02, u0=0.0, u1=max(1.0, round((L - 1.2) / 3.0)))
    RZ.kit_add(P, "L4", tag="matthews_photos")


def hotel(RZ):
    """Reitz Union Hotel (L5-L6): the corridor; room 516 (queen bed with royal-blue skirt, cherry headboard,
    nightstands + lamps, dresser + TV, the royal-blue accent wall; ru_hotel_room), suite 501/502 (blue sofa, cream
    armchairs, cherry coffee table; ru_hotel_suite) and room 516's balcony (white slotted balustrade;
    ru_hotel_balcony). Every other room is a closed door."""
    F = RZ.floors["L5"]
    z = F.z
    r516 = F.zone("hotel_room_516")
    mx, my, facing, W, D = _room_frame(r516)
    f = math.radians(facing)
    fx, fy = math.sin(f), math.cos(f)
    RZ.kit_add(R.bed_set(), "L5", tag="hotel_bed", x=mx + fx * 0.15, y=my + fy * 0.15, z=z, facing=facing)
    RZ.kit_add(R.dresser_tv(), "L5", tag="hotel_dresser", x=mx + fx * (D - 0.65), y=my + fy * (D - 0.65), z=z,
               facing=(facing + 180.0) % 360)
    suite = F.zone("hotel_room_501_502")
    c = R.centroid(suite.poly)
    RZ.kit_add(R.sofa(2.0), "L5", tag="suite_sofa", x=c[0], y=c[1] + 1.8, z=z, facing=180.0)
    RZ.kit_add(R.coffee_table(1.2, 0.6, mat="int_ru_cherry"), "L5", tag="suite_table", x=c[0], y=c[1] + 0.4, z=z)
    for j, dx in enumerate((-1.5, 1.5)):
        RZ.kit_add(R.lounge_chair("int_ru_fabric_taupe", "int_ru_fabric_taupe"), "L5", tag=f"suite_chair_{j}",
                   x=c[0] + dx, y=c[1] - 0.6, z=z, facing=0.0 if dx < 0 else 0.0)
    # balcony balustrade (white slotted concrete) along the outer edge of balcony 8
    bal = F.zone("l5_hotel_balcony_8")
    P = K.Prop("hotel_balcony")
    V, C = P.visual, P.collision
    if bal is not None:
        x0, y0, x1, y1 = R.bbox(bal.poly)
        ra, rb = (x1 - 0.1, y0), (x1 - 0.1, y1)
        R.seg_box(V, ra, rb, 0.1, z, z + 1.1, "int_ru_white", faces="sideends_top")
        for k in range(int((y1 - y0) / 0.4)):
            yy = y0 + 0.2 + k * 0.4
            V.box(x1 - 0.21, yy - 0.04, z + 0.2, x1 + 0.01, yy + 0.04, z + 0.9, "int_ru_black", faces="+x-x")
        R.col_seg(C, ra, rb, 0.1, z, z + 1.1, K.COL)
        RZ.kit_add(R.high_top(1.0, 0.3, 2), "L5", tag="balcony_table", x=(x0 + x1) / 2 - 0.2, y=(y0 + y1) / 2, z=z)
    RZ.kit_add(P, "L5", tag="hotel_balcony")
    # hotel corridor sign by the elevators
    P2 = K.Prop("hotel_sign")
    R.panel(P2.visual, (-444.0, -272.6), (-446.4, -272.6), z + 2.2, z + 3.4, "int_ru_sign_hotel", off=0.0, glow=True)
    RZ.kit_add(P2, "L5", tag="hotel_sign")


def lower_level(RZ):
    """Lower Level: the Arts & Crafts Center (entrance mural with the ACC roundel; craft tables and shelves;
    ru_acc_entrance_mural, ru_acc_studio) and Dance Studios A + B (black sprung floor, mirror wall, ballet barre;
    ru_os_dance_1/2)."""
    F = RZ.floors["LL"]
    z = F.z
    P = K.Prop("ll_misc")
    V, C = P.visual, P.collision
    for zid in ("dance_studio_a", "dance_studio_b"):
        zn = F.zone(zid)
        if zn is None:
            continue
        x0, y0, x1, y1 = R.bbox(zn.poly)
        # mirror wall on the east side (inside face), barre in front
        a, b = (x1 - 0.12, y0 + 0.3), (x1 - 0.12, y1 - 0.3)
        _wall_strip(V, b, a, z + 0.25, z + 2.6, "int_ru_mirror", off=0.0)
        V.box(x1 - 0.5, y0 + 0.5, z + 1.0, x1 - 0.44, y1 - 0.5, z + 1.06, "int_ru_steel", faces="+x-x+y-y+z")
    acc = F.zone("arts_crafts_center")
    if acc is not None:
        x0, y0, x1, y1 = R.bbox(acc.poly)
        for k, (xx, yy) in enumerate(((-455.0, -250.0), (-451.0, -250.0), (-455.0, -256.0), (-451.0, -256.0),
                                      (-455.0, -262.0))):
            RZ.kit_add(R.folding_table(2.0, 1.0, top="int_ru_wall_cream", chairs=2), "LL", tag=f"acc_table_{k}",
                       x=xx, y=yy, z=z, facing=0.0)
        V.box(x0 + 0.15, y0 + 2.0, z, x0 + 0.6, y0 + 8.0, z + 2.0, "int_ru_wood_panel", faces="+x+y-y+z")
        R.panel(V, (x0 + 0.62, y0 + 2.2), (x0 + 0.62, y0 + 7.8), z + 0.2, z + 1.9, "int_ru_books", off=0.0)
    # the ACC mural on the corridor wall by its entrance (east face of the ACC's east wall)
    R.panel(V, (-444.38, -257.0), (-444.38, -253.0), z + 0.6, z + 4.6, "int_ru_mural_acc", off=0.0)
    RZ.kit_add(P, "LL", tag="ll_misc")


DRESSERS.extend([grand_ballroom, rion_ballroom, auditorium, gallery, senate_chamber, meeting_rooms, level4, hotel,
                 lower_level])


# ================================================================== preview cameras (photo-matched)
def _room_view(RZ, fid, zid, back=0.9, h=1.65, side=0.35):
    """Camera in the back of a room looking at its accent wall (the room photos are taken that way)."""
    zn = RZ.floors[fid].zone(zid)
    mx, my, facing, W, D = _room_frame(zn)
    f = math.radians(facing)
    fx, fy = math.sin(f), math.cos(f)
    tx, ty = fy, -fx
    z = RZ.floors[fid].z
    cam = (mx + fx * (D - back) + tx * W * side, my + fy * (D - back) + ty * W * side, z + h)
    tgt = (mx + fx * 0.5 - tx * W * 0.1, my + fy * 0.5 - ty * W * 0.1, z + h - 0.2)
    return cam, tgt


def make_views(RZ):
    """[(name, camera, target, mario or None, vfov, photo)]: the preview cameras, each matched to a reference photo
    (reference/interiors/reitz/photos/) as far as its unknown viewpoint can be read from the picture."""
    v = [
        ("reitz_atrium_lounge", (-384.0, -279.2, 1.5), (-405.0, -271.0, 6.8), None, 62.0, "ru_atrium_enr_lounge.webp"),
        ("reitz_atrium_stairs", (-389.6, -271.0, 20.0), (-404.0, -271.6, 8.5), None, 72.0, "ru_atrium_enr_vertical.webp"),
        ("reitz_atrium_up", (-391.0, -275.5, 1.6), (-402.5, -268.5, 19.0), None, 76.0, "ru_atrium_hdr_flickr.jpg"),
        ("reitz_uf_letters", (-409.0, -272.5, 1.6), (-409.4, -264.5, 2.5), None, 58.0, "ru_atrium_uf_letters_flickr.jpg"),
        ("reitz_game_room_lanes", (-458.2, -301.2, 1.7), (-441.0, -306.4, 1.6), None, 60.0, "ru_gr_lanes_overview_2.jpg"),
        ("reitz_bowling_lane", (-446.2, -306.0, 1.75), (-446.2, -327.0, 1.9), None, 58.0, "ru_gr_lane_screens.jpg"),
        ("reitz_billiards", (-458.6, -289.6, 1.6), (-440.0, -285.4, 1.5), None, 62.0, "ru_gr_billiards_room.jpg"),
        ("reitz_esports", (-461.2, -294.5, 1.7), (-463.0, -309.0, 3.0), None, 66.0, "ru_es_overview.jpg"),
        ("reitz_food_court", (-430.8, -309.6, 7.6), (-428.6, -292.0, 7.3), None, 62.0, "ru_food_court_counter_2023.jpeg"),
        ("reitz_food_court_burgers", (-426.6, -299.8, 7.6), (-433.2, -299.8, 8.6), None, 62.0, "ru_food_court_sonic_2025.jpg"),
        ("reitz_grand_ballroom", (-488.5, -250.6, 14.8), (-488.5, -275.0, 14.4), None, 62.0, "ru_os_grand_ballroom_1.jpg"),
        ("reitz_rion_ballroom", (-425.5, -322.8, 19.8), (-455.0, -299.0, 19.6), None, 62.0, "ru_os_rion_ballroom.jpg"),
        ("reitz_auditorium", (-433.4, -251.5, 15.6), (-454.0, -251.5, 13.7), None, 58.0, "ru_os_auditorium_3.jpg"),
        ("reitz_senate_chamber", (-402.6, -261.6, 2.5), (-408.6, -246.0, 1.4), None, 62.0, "ru_os_chamber.jpg"),
        ("reitz_gallery", (-421.5, -259.8, 13.6), (-430.0, -250.0, 13.4), None, 62.0, "ru_the_gallery.jpg"),
        ("reitz_arredondo", (-423.8, -275.8, 25.6), (-452.0, -259.0, 25.2), None, 62.0, "ru_os_arredondo_cafe.jpg"),
        ("reitz_hotel_room", (-430.6, -274.4, 30.6), (-426.0, -268.5, 29.9), None, 66.0, "ru_hotel_room.jpg"),
        ("reitz_dance_studio", (-402.4, -279.0, -4.4), (-389.5, -270.0, -4.8), None, 62.0, "ru_os_dance_1.jpg"),
        ("reitz_acc_mural", (-440.0, -255.0, -4.4), (-444.4, -255.0, -3.8), None, 62.0, "ru_acc_entrance_mural.jpg"),
        ("reitz_north_vestibule", (-380.5, -270.0, 7.6), (-380.5, -255.0, 8.4), None, 64.0, None),
        ("reitz_south_terrace_doors", (-385.0, -276.0, 1.6), (-385.0, -290.0, 2.2), None, 64.0, None),
        ("reitz_elevator_lobby", (-445.0, -275.5, 1.7), (-445.0, -268.0, 1.6), None, 66.0, None),
    ]
    for name, fid, zid, photo in (("reitz_meeting_g310", "G", "meeting_G310", "ru_os_g310_g320.jpg"),
                                  ("reitz_meeting_2315", "L2", "meeting_2315", "ru_os_2315_2330.jpg"),
                                  ("reitz_meeting_3305", "L3", "meeting_3305", "ru_os_3305.jpg"),
                                  ("reitz_matthews", "L4", "matthews_suite", "ru_os_matthews_1.jpg")):
        try:
            cam, tgt = _room_view(RZ, fid, zid)
            v.append((name, cam, tgt, None, 64.0, photo))
        except Exception:  # noqa: BLE001
            pass
    return v


def views_json(RZ, path):
    out = []
    for name, cam, tgt, mario, fov, photo in make_views(RZ):
        out.append({"name": name, "loc": list(cam), "tgt": list(tgt), "fov": fov, "mario": mario, "photo": photo,
                    "res": [1200, 800]})
    json.dump(out, open(path, "w"), indent=1)
    return out


# ==== END (keep the __main__ block last) ====
if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(1 if selftest() else 0)
    if "--views-json" in sys.argv:
        print(len(views_json(build(dress=False), sys.argv[sys.argv.index("--views-json") + 1])), "views")
