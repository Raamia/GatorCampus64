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
VAULT_RISE = 2.0                       # the cedar vault's rise over ATRIUM_TOP along its crown
ATRIUM_TOP = 25.6                      # cedar ceiling over the atrium voids (L3 ceiling 23.4 + a 2.2 m clerestory)
WALL_T = 0.20                          # interior partitions (visual faces at +-0.1 m of the plan centre-line)
EXT_T = 0.30                           # exterior walls
DOOR_H = 2.6                           # door head (real 2.13 m doors; camera + co-op)
GB_SOFFIT = 9.3                        # Grand Ballroom perimeter soffit (fidelity-4; coffers at the 11.4 m clear)
GB_END_SOFFIT = 8.3                    # ... lowered end soffit over the east clerestory band
GB_END_D = 4.0                         # ... its depth from the east end wall
GB_AISLE = 2.0                         # ... aisles between the theatre-row blocks (design pass; was 1.6)
GB_CENTRE_AISLE = 3.2                  # ... the centre aisle on the podium axis (fidelity-4 round 2: two blocks)
SUITE_ID = "hotel_room_501_502"        # hotel suite: sitting room (501, south) | bedroom (502, north)
SUITE_SPLIT_Y = -284.52                # ... the partition between them (fidelity-4 round 2), centre line
MEETING_CLEAR = 3.9                    # G / L2 / L3 meeting rooms + Senate Chamber: dropped lay-in ceiling (photos ~2.7-3 m)
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
# plan partitions dropped between these walkable zones: the Arredondo Cafe's window ring (ru_os_arredondo_cafe: the
# full-height window wall with roller shades is right at the tables)
OPEN_PAIRS = {frozenset(("arredondo_cafe", "l4_corridor_04"))}
OPEN_IDS = {"hotel_room_516", "hotel_room_501_502", "l5_hotel_balcony_8"}
ATRIUM_SEALED_VOIDS = {"l3_atrium_void_02"}
# plain white soffit bays instead of the near-void cedar band (x0, y0, x1, y1 map m, by floor): the Ground ceiling
# under the Level 1 balcony over the UF letters (ru_atrium_uf_letters_flickr: white soffit with downlights)
WHITE_SOFFITS = {"G": [(-414.8, -267.9, -403.2, -263.8)]}
GLASS_VESTIBULES = {"north_entrance", "south_terrace_vestibule"}   # entrance vestibules: glass boxes (photos)
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
     "porch": [(-378.4, -288.84), (-370.4, -288.95), (-370.4, -283.0), (-378.4, -283.0)], "strip_gap": 0.0,
     "open_doors": [(-373.5, -283.0, -371.1, -283.0)]},
    {"id": "north_ground", "name": "Ground north doors (core, under the Level 1 bridge)", "index": 0,
     "a": (-420.4, -244.5), "b": (-417.8, -244.5), "n": (0.0, 1.0), "z1": 0.0, "z2": 0.0,
     "depth_in": 2.0, "depth_out": 2.3, "floor": "G",
     "note": "the Ground-level north door east of SG Bike Repair (plan door g_ext_door_07), into the corridor that "
             "runs down to the hotel reception / atrium corridor (area 1: under the north colonnade canopy)"},
]
WARP_MAT = {0: "COL warp_1B", 1: "COL warp_1C", 2: "COL warp_1D", 3: "COL warp_1E"}
STRIP_GAP = 0.10                       # area-2 strips start this far outside the door line (no shared edge)
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
    "rion_ballroom": "Top floor, so its ceiling rises 0.6 m above the L3 corridor ceiling (6.0 m clear; the photo reads "
                     "about 5 m).",
    "meeting_rooms": "Ground (G310-G330, the Senate Chamber), L2 and L3 meeting rooms have a dropped lay-in ceiling at "
                     "3.9 m (photos ~2.7-3 m), raised for the camera.",
    "stair_halls": "The enclosed stair halls are not built (closed doors, sealed shafts; no photos): floors connect by "
                   "the Blue elevator pads and the atrium scissor stairs.",
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
                 accent="int_ru_wall_royal" if fid == "G" else "int_ru_wall_slateblue")
        if zid == "meeting_G315":
            s["accent"] = "int_ru_wall_paleblue"     # fix round 4 (fidelity-3 blocking; ru_os_g315 'pale blue accent wall')
        if fid in ("G", "L2", "L3"):
            # dropped lay-in ceiling (ru_os_2315_2330, ru_os_3315_3320: ~2.7-3 m real): drawn + a collision ceiling at
            # ceil_h; the walls and the plain ceiling above stay at the floor's clear height, so the wall collision
            # still merges with the corridor side (the ceiling groups are unchanged). Fidelity-3 (round 2): Ground's
            # G310-G330 too (ru_os_g310_g320, ru_os_g330: ~3 m, about 1.4x the door; 5.4 m made the royal-blue accent
            # walls tall slabs instead of wide low bands)
            s["ceil_h"] = MEETING_CLEAR
    elif t == "ballroom":
        if zid == "grand_ballroom":
            s.update(floor="int_ru_carpet_ballroom", wall="int_ru_wall_grey", ceil="int_ru_tile_ceiling",
                     clear=Z["L3"] + CLEAR["L3"] - Z["L2"], light="coffer", spacing=5.0)
        else:
            s.update(floor="int_ru_maple", wall="int_ru_wall", clear=CLEAR["L3"] + 0.6, light="linear", spacing=3.6)
    elif t == "auditorium":
        # fix round 4 (fidelity-4 pass): mid-grey fabric walls under the dark slats (ru_os_auditorium_1..3; the pale
        # int_ru_wall_grey read far brighter than the photos)
        s.update(floor="int_ru_carpet_aud", wall="int_ru_wall_aud", ceil="int_ru_slat_dark", light="cove",
                 spacing=3.0)
    elif t == "gallery":
        s.update(floor="int_ru_concrete_dark", ceil="int_ru_black", light="track", spacing=2.4)
    elif t == "chamber":
        s.update(floor="int_ru_carpet_chamber", wall="int_ru_wall_cream", light="down", spacing=2.6)
        s["ceil_h"] = MEETING_CLEAR         # fidelity-3 (round 2; ru_os_chamber): the same dropped lay-in ceiling
    elif t == "game_room":
        s.update(floor="int_ru_plank", wall="int_ru_wall_navy", light="troffer", spacing=3.6, base="int_ru_black")
    elif t == "esports":
        # ru_es_oelrich_9352: wood-look plank floor; near-black hex walls (ru_es_overview)
        s.update(floor="int_ru_wood_lvt", wall="int_ru_hex", ceil="int_ru_black", light="esports", spacing=3.0)
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
            # fix round 5 (fidelity-4, improvement 2; ru_os_matthews_1/3/4): white baseboards (were black)
            s.update(floor="int_ru_carpet_grey", wall="int_ru_wall_greyblue", light="down", spacing=2.6,
                     base="int_ru_white")
    elif t == "hotel_room":
        # fix round 4 (fidelity-4 pass, improvement 8): white walls (ru_hotel_room, ru_hotel_suite; the cream baked a
        # dull beige-grey)
        s.update(floor="int_ru_carpet_hotel", wall="int_ru_wall", accent="int_ru_wall_royal", light="lamp",
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
        if zid == "matthews_suite" and abs(b[1] - a[1]) < 0.3 * abs(b[0] - a[0]) and my < -287.5:
            # fix round 5 (fidelity-4, improvement 4; ru_os_matthews_1): the suite's long south wall is solid pale
            # blue-grey with a row of four frames; the glass is the west end wall only
            return None
        return (0.25, clear - 0.35, "curtain")
    if fid == "LL":
        return None
    if reg == "E":
        if fid == "G":
            return (0.0, 3.2, "curtain") if zid == "south_terrace_vestibule" else None
        return (0.0, clear, "curtain")
    if zid == "game_room":
        # fidelity-3 (round 2; ru_gr_foosball_windows, ru_gr_ping_pong): the east windows by the table games have a
        # solid charcoal dado to ~1.1 m, then glass to the ceiling (the CURVE rule made them floor-to-ceiling)
        if mx > -422.0:
            # fix round 4 (fidelity-3; ru_gr_foosball_windows): a ~1.9 m band under a charcoal bulkhead (the glass to
            # the raised 5.4 m ceiling read as a curtain wall of trees); the wall above the head takes the dado's
            # int_ru_wall_charcoal (the game-room 'curtain' rule in the wall run)
            return (1.1, 3.0, "curtain")
        return (2.7, 3.7, "ribbon")
    if reg == "CURVE":
        return (0.0 if fid in ("G", "L1") else 0.6, clear - (0.0 if fid in ("G", "L1") else 0.4), "curtain")
    if zid == "grand_ballroom":
        return (8.6, 10.6, "clerestory") if my > -255.0 else None
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
                (C.nocam if mat == K.COL_NOCAM and isinstance(C, ColWalls) else C).append(q)
            else:
                C.poly(q, mat)


class ColWalls(list):
    """Collision wall quads of one floor (merged before they are emitted); .nocam holds the walls the camera passes
    through (NOCAM_CORRIDORS), merged and emitted separately as SURFACE_NO_CAM_COLLISION."""
    def __init__(self):
        super().__init__()
        self.nocam = []


# design pass (camera): long corridor side walls with CLOSED rooms behind them are SURFACE_NO_CAM_COLLISION, so the
# gameplay camera can pull back through them (it sees through the back-face-culled wall, as in vanilla SM64); Mario
# still collides. (floor, zone id or None = any walkable zone, plan bbox x0, y0, x1, y1 or None)
NOCAM_CORRIDORS = [
    ("L5", "l5_reitz_union_hotel", None),                       # the 1.5-2 m hotel corridor ring
    ("L6", "l6_reitz_union_hotel", None),
    ("G", "g_corridor_02", (-452.0, -279.0, -424.0, -272.6)),   # the G elevator corridor (~2 m)
    ("LL", None, (-427.6, -275.2, -424.7, -266.4)),             # the freestanding LL wall block (view gp10)
]


def _core_room(F, ozn):
    """fix round 2 (design): a sealed room that does not reach the facade (the hotel core: elevators, service,
    linen rooms; their nearest vertex is >= 5 m from the floor outline, the guest rooms' ~1.5-1.9 m)."""
    if ozn is None or ozn.cls != "S":
        return False
    return min(R.poly_dist(p, F.outline) for p in ozn.poly) > 3.0


def _nocam_wall(fid, zn, ocls, fa, fb, core=False):
    if ocls not in ("S", "O") or zn is None:
        return False
    mx, my = (fa[0] + fb[0]) / 2, (fa[1] + fb[1]) / 2
    for f, zid, bb in NOCAM_CORRIDORS:
        if f != fid or (zid is not None and zn.id != zid):
            continue
        if ocls == "O" and bb is None:
            continue                     # an exterior wall: the camera must stay in the building
        if core and zid is not None and bb is None:
            # fix round 2 (design): the hotel ring keeps NO_CAM on the guest-room side only. A camera that swung
            # through the core-side walls crossed the core and was hidden by the far corridor's walls (follow-cam
            # sweep: Mario hidden in 17.9% / 27.9% of L5 / L6 samples); the core walls now stop it.
            continue
        if bb is None or (bb[0] <= mx <= bb[2] and bb[1] <= my <= bb[3]):
            return True
    return False


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


def _entrance_door_pair(V, a, b, z0, leaf_h=2.45, top=GLASS_DOOR_H):
    """fix round 2 (fidelity, ru_ribbon_cutting_doors): one bay of the north entrance door bank, VISUAL only (the
    opening stays walkable: the warp strip is just outside): a pair of glazed leaves in white / light aluminium with
    WIDE stiles and a deep bottom rail, tall steel pulls on both faces by the meeting stiles, a white transom bar at
    the leaf head and transom glass above it (the four bays read as doors, not as the fixed curtain glass)."""
    w = math.dist(a, b)
    if w < 0.6:
        return
    dx, dy = (b[0] - a[0]) / w, (b[1] - a[1]) / w
    nx, ny = dy, -dx
    n = 2 if w > 1.35 else 1

    def at(s_):
        return (a[0] + dx * s_, a[1] + dy * s_)
    # fix round 2 (design): the door bank is the first thing seen on arrival: clear glass (alpha 0.14, neutral)
    # fix round 5 (design, improvement 3): the leaves (no collision) take the faint glass (alpha 0.08, no sheen)
    R.panel(V, a, b, z0, z0 + top, "int_ru_glass_faint")
    R.panel(V, b, a, z0, z0 + top, "int_ru_glass_faint")
    st, hl = 0.11, 0.035                    # stile width, half depth
    for k in range(n):
        s0, s1 = w * k / n, w * (k + 1) / n
        for (u0, u1) in ((s0, s0 + st), (s1 - st, s1)):
            R.seg_box(V, at(u0), at(u1), hl, z0, z0 + leaf_h, "int_ru_white", faces="sideends", ao=0.95)
        R.seg_box(V, at(s0 + st), at(s1 - st), hl, z0, z0 + 0.26, "int_ru_white", faces="sidetop", ao=0.95)
        R.seg_box(V, at(s0 + st), at(s1 - st), hl, z0 + leaf_h - 0.12, z0 + leaf_h, "int_ru_white", faces="sidebot",
                  ao=0.95)
        # pull: a tall steel bar standing off both faces, beside the meeting stile (or the latch side)
        sp = s1 - st - 0.1 if (k == 0 and n == 2) else s0 + st + 0.1
        px, py = at(sp)
        for sg in (-1, 1):
            cx, cy = px + nx * sg * 0.08, py + ny * sg * 0.08
            V.box(cx - 0.018, cy - 0.018, z0 + 0.85, cx + 0.018, cy + 0.018, z0 + 1.95, "int_ru_steel",
                  faces="+x-x+y-y")
            for zz in (z0 + 0.95, z0 + 1.85):
                R.seg_box(V, (px + nx * sg * 0.035, py + ny * sg * 0.035), (cx, cy), 0.012, zz - 0.012, zz + 0.012,
                          "int_ru_steel", faces="side")
    # transom bar over the leaves, transom glass above (to the opening head)
    R.seg_box(V, at(0.0), at(w), 0.06, z0 + leaf_h, z0 + leaf_h + 0.14, "int_ru_white", faces="sidebot", ao=0.95)
    R.seg_box(V, at(0.0), at(w), 0.05, z0 + top - 0.08, z0 + top, "int_ru_white", faces="sidebot", ao=0.95)


def _elevator_doors(V, a, b, z0, fa, fb):
    """Closed elevator entrance (no public photo; fidelity-4): one pair of brushed-steel sliding doors (the texture
    carries the centre seam) in a steel frame, and a call-button plate beside it on the wall face fa -> fb."""
    w = math.dist(a, b)
    if w < 0.3:
        return
    dx, dy = (b[0] - a[0]) / w, (b[1] - a[1]) / w
    R.panel(V, a, b, z0, z0 + 2.3, "int_ru_door_elev", off=0.03, ao=0.95)
    for p in (a, b):
        V.box(p[0] - 0.06, p[1] - 0.06, z0, p[0] + 0.06, p[1] + 0.06, z0 + 2.4, "int_ru_steel", faces="+x-x+y-y")
    R.panel(V, (a[0] - dx * 0.06, a[1] - dy * 0.06), (b[0] + dx * 0.06, b[1] + dy * 0.06), z0 + 2.3, z0 + 2.4,
            "int_ru_steel", off=0.04)
    L = math.dist(fa, fb)
    sb = (b[0] - fa[0]) * (fb[0] - fa[0]) / max(L, 1e-6) + (b[1] - fa[1]) * (fb[1] - fa[1]) / max(L, 1e-6)
    sa = (a[0] - fa[0]) * (fb[0] - fa[0]) / max(L, 1e-6) + (a[1] - fa[1]) * (fb[1] - fa[1]) / max(L, 1e-6)
    for s_, sgn in ((max(sa, sb), 1.0), (min(sa, sb), -1.0)):
        sc = s_ + sgn * 0.38
        if 0.15 < sc < L - 0.15:
            ux, uy = (fb[0] - fa[0]) / L, (fb[1] - fa[1]) / L
            R.panel(V, (fa[0] + ux * (sc - 0.08), fa[1] + uy * (sc - 0.08)), (fa[0] + ux * (sc + 0.08), fa[1] + uy * (sc + 0.08)),
                    z0 + 1.0, z0 + 1.32, "int_ru_call_button", off=0.025, glow=True)
            break


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


# fix round 5 (fidelity-2): the Level 1 outdoor dining terrace (outdoor_dining_area) opens from the south hall
# through its west glass door (plan door x -431.1, y -337.0 .. -335.3): a walkable doorway (it was a closed door and
# the terrace an unreachable empty strip). The north door (y -318.4) stays closed.
TERRACE_OPEN_DOORS = [(-431.1, -337.0, -431.1, -335.3)]


def _terrace_door(fid, mid):
    return fid == "L1" and any(R.seg_point_dist(mid, (od[0], od[1]), (od[2], od[3])) < 0.6
                               for od in TERRACE_OPEN_DOORS)


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


def _clip_pieces(pc, tris, tbbs):
    """Convex piece pc intersected with a union of CCW triangles -> convex pieces (pc itself when fully inside)."""
    bx0, by0, bx1, by1 = R.bbox(pc)
    area = abs(R.signed_area(pc))
    out, tot = [], 0.0
    for t_, (tx0, ty0, tx1, ty1) in zip(tris, tbbs):
        if tx1 <= bx0 or tx0 >= bx1 or ty1 <= by0 or ty0 >= by1:
            continue
        q = list(pc)
        for a, b in R.edges(t_):
            q = R.clip_halfplane(q, a, b, keep_left=True)
            if not q:
                break
        if q:
            ar = abs(R.signed_area(q))
            if ar > 1e-3:
                out.append(q)
                tot += ar
    if tot >= area - 1e-3:
        return [pc]
    return out


def _clip_outline(pc, outline, tris, tbbs):
    """Convex piece pc intersected with the (concave) floor outline -> few convex pieces: pc itself when inside,
    else the outline clipped to pc (Sutherland-Hodgman by pc's edges) triangulated; triangle-wise as a fallback."""
    area = abs(R.signed_area(pc))
    if all(R.pip(p, outline) for p in pc):
        cut = False
        for a, b in R.edges(outline):
            if R.pip(a, pc) or R.pip(b, pc):
                cut = True
                break
        if not cut:
            return [pc]
    q = list(outline)
    for a, b in R.edges(R.ccw(pc)):
        q = R.clip_halfplane(q, a, b, keep_left=True)
        if not q:
            return []
    ar = abs(R.signed_area(q))
    if ar >= area - 1e-3:
        return [pc]
    if ar < 1e-3:
        return []
    try:
        q = R.clean(R.ccw(q), 0.005, 0.0005)
        n = len(q)
        if n >= 3 and all(R._cross(q[k - 1], q[k], q[(k + 1) % n]) >= -1e-9 for k in range(n)):
            return [q]
        tr = [list(t) for t in R.triangulate(q)]
        if abs(sum(abs(R.signed_area(t)) for t in tr) - ar) < 1e-3:
            return tr
    except Exception:  # noqa: BLE001
        pass
    return _clip_pieces(pc, tris, tbbs)


def _bb_overlap(a, b):
    return not (a[0] >= b[2] or b[0] >= a[2] or a[1] >= b[3] or b[1] >= a[3])


def _convex_parts(poly):
    """A polygon as convex holes for R.subtract: itself when convex, else its triangles."""
    a = R.ccw(R.clean(poly))
    n = len(a)
    if n >= 3 and all(R._cross(a[k - 1], a[k], a[(k + 1) % n]) >= -1e-9 for k in range(n)):
        return [a]
    return [list(t) for t in R.triangulate(a)]


def _clip_to_convex(pc, poly):
    q = list(pc)
    for a, b in R.edges(R.ccw(poly)):
        q = R.clip_halfplane(q, a, b, keep_left=True)
        if not q:
            return []
    return q


def _band_pieces(base, bands, mat, white=()):
    """Convex ceiling pieces -> [(piece, material)]: inside the cedar bands (convex) int_ru_cedar, the rest `mat`;
    the WHITE_SOFFITS rectangles white (each split exactly, no per-piece choice)."""
    out = [(pc, mat) for pc in (R.subtract(base, bands) if bands else base)]
    done = []
    for bnd in bands:
        bb = R.bbox(bnd)
        for pc in base:
            if not _bb_overlap(R.bbox(pc), bb):
                continue
            q = _clip_to_convex(pc, bnd)
            if q and abs(R.signed_area(q)) > 1e-4:
                for q2 in (R.subtract([R.ccw(q)], done) if done else [R.ccw(q)]):
                    out.append((q2, "int_ru_cedar"))
        done.append(bnd)
    for (x0, y0, x1, y1) in white:
        rect = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        nxt = []
        for pc, m in out:
            if not _bb_overlap(R.bbox(pc), (x0, y0, x1, y1)):
                nxt.append((pc, m))
                continue
            q = R.clip_convex(list(pc), x0, y0, x1, y1)
            if q and len(q) >= 3 and abs(R.signed_area(q)) > 1e-4:
                nxt.append((R.ccw(q), "int_ru_white"))
            nxt.extend((q2, m) for q2 in R.subtract([pc], [rect]))
        out = nxt
    return [(pc, m) for pc, m in out if len(pc) >= 3 and abs(R.signed_area(pc)) > 1e-4]


def _clip_seg(a, b, poly):
    """The part of segment a-b inside a convex polygon (or None)."""
    t0, t1 = 0.0, 1.0
    d = (b[0] - a[0], b[1] - a[1])
    for p, q in R.edges(R.ccw(poly)):
        e = (q[0] - p[0], q[1] - p[1])
        num = e[0] * (a[1] - p[1]) - e[1] * (a[0] - p[0])      # >= 0 inside (left of the CCW edge)
        den = e[0] * d[1] - e[1] * d[0]
        if abs(den) < 1e-12:
            if num < 0:
                return None
            continue
        t = -num / den
        if den > 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 >= t1:
            return None
    return (a[0] + d[0] * t0, a[1] + d[1] * t0), (a[0] + d[0] * t1, a[1] + d[1] * t1)


def _void_edge_fill(F, V, C, CW):
    """Fix round 2 (blocking): the atrium voids are convex hulls of the plan's chevron cuts, so stretches of their
    edges carry no plan wall: walkable floor there had no rail (Mario walked off, e.g. the L3 east edge), and sealed
    suites there showed their hollow backs. Every atrium void edge is sampled: walkable outside without a balcony edge
    -> _balcony_edge (fascia, pickets, collision); sealed outside without a plan wall -> a solid wall into the void."""
    if F.id not in ("L1", "L2", "L3"):
        return 0
    z = F.z
    segs = getattr(F, "balc_segs", [])
    built = 0
    for v in F.voids:
        if R.centroid(v)[0] < -425.0:
            continue
        for a, b in R.edges(R.ccw(v)):
            L = math.dist(a, b)
            if L < 0.3:
                continue
            ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            nx, ny = uy, -ux                       # outward (right of a CCW edge)
            n = max(1, int(math.ceil(L / 0.25)))
            labels = []
            for i in range(n):
                sm = (i + 0.5) * L / n
                p = (a[0] + ux * sm, a[1] + uy * sm)
                cls, _zn = F.cls_at((p[0] + nx * 0.35, p[1] + ny * 0.35))
                lab = None
                if cls == "W":
                    if not any(R.seg_point_dist(p, sa, sb) < 0.35 for sa, sb in segs):
                        lab = "W"
                elif cls == "S":
                    if not any(R.seg_point_dist(p, (w[0], w[1]), (w[2], w[3])) < 0.35 for w in F.walls):
                        lab = "S"
                labels.append(lab)
            i = 0
            while i < n:
                lab = labels[i]
                j = i
                while j < n and labels[j] == lab:
                    j += 1
                s0, s1 = i * L / n, j * L / n
                if lab is not None and s1 - s0 >= 0.2:
                    pa = (a[0] + ux * s0, a[1] + uy * s0)
                    pb = (a[0] + ux * s1, a[1] + uy * s1)
                    if lab == "W":
                        _balcony_edge(V, C, pb, pa, z, F)
                    else:
                        wall_face(V, pb, pa, z - SLAB - FASCIA * 0.5, z + F.clear, "int_ru_wall")
                    built += 1
                i = j
    return built


def _sealed_backing(F, V):
    """Fix round 2 (blocking): the camera passes the NO_CAM hotel corridor walls (and the G elevator corridor's)
    into the sealed rooms behind them, which had no floor or ceiling (Lakitu showed the corridor floating over the
    L4 rooms). Each such room gets a cheap backing box: floor, ceiling and inward walls, but no wall on the corridor
    side (that one would hide Mario from a camera standing in the room)."""
    sel = []
    for f, zid, bb in NOCAM_CORRIDORS:
        if f != F.id or f == "LL":
            continue
        cor = [zn for zn in F.walk_zones() if (zid is None or zn.id == zid)
               and (bb is None or _bb_overlap(zn.bb, bb))]
        if zid is None:
            cor = [zn for zn in cor if zn.type == "corridor"]
        for zn in F.zones:
            if zn.cls != "S" or zn.area > 120.0 or zn.type in DOUBLE_TYPES or zn in sel:
                continue
            if zid is not None and bb is None and _core_room(F, zn):
                continue                    # design r2: the hotel core walls stop the camera (no backing needed)
            box = bb if bb is not None else None
            if box is not None and not _bb_overlap(zn.bb, (box[0] - 0.6, box[1] - 0.6, box[2] + 0.6, box[3] + 0.6)):
                continue
            if not any(_bb_overlap(zn.bb, (c.bb[0] - 0.6, c.bb[1] - 0.6, c.bb[2] + 0.6, c.bb[3] + 0.6)) and
                       min(R.poly_dist(p, c.poly) for p in zn.poly) < 0.6 for c in cor):
                continue
            if any(_bb_overlap(zn.bb, w.bb) and (R.pip(R.centroid(w.poly), zn.poly) or R.pip(R.centroid(zn.poly), w.poly))
                   for w in F.walk_zones()):
                continue                    # an envelope over walkable rooms: no doubled floors
            sel.append(zn)
    z = F.z
    floor_mat = "int_ru_carpet_hotel" if F.id in ("L5", "L6") else "int_ru_carpet_grey"
    for zn in sel:
        poly = R.ccw(R.offset_poly(zn.poly, -0.2))
        if abs(R.signed_area(poly)) < 1.0:
            continue
        R.floor_poly(V, poly, z - 0.03, floor_mat, step=99.0)
        R.floor_poly(V, poly, z + F.clear, "int_ru_wall", step=99.0, down=True)
        for a, b in R.edges(poly):
            L = math.dist(a, b)
            if L < 0.1:
                continue
            ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            cls, oz = F.cls_at((mid[0] + uy * 0.6, mid[1] - ux * 0.6))
            if cls == "W":
                continue                    # the corridor side (or a walkable neighbour): stays see-through
            if cls == "S" and oz in sel:
                # fix round 2 (design): no wall between two backed rooms. Each such wall faced into its own room,
                # so a camera that had swung into room B was blind to Mario in front of room A (follow-cam sweep)
                continue
            R.quad_wall(V, b, a, z - 0.03, z + F.clear, "int_ru_wall_cream", ao=0.85)
    return len(sel)


def _void_caps(F, above, V, CC):
    """Fix round 2 (blocking): the part of a Level 1 atrium void that the Level 2 void does not continue (the east
    void 02 under the sealed student-engagement suites) is capped at the Level 1 ceiling (11.4): white tile with
    downlights, the cedar band within 3 m of the Level 2 void, a white fascia where the cap meets that void, and a
    collision ceiling (it was open to the sky: ru_atrium_enr_lounge shows a closed double-height east end)."""
    if F.id != "L1" or above is None:
        return 0
    zc = F.z + F.clear
    up = [R.ccw(R.convex_hull(u)) for u in above.voids]
    n_caps = 0
    for v in F.voids:
        caps = [c for c in R.subtract([R.ccw(R.convex_hull(v))], up) if abs(R.signed_area(c)) > 0.05]
        if sum(abs(R.signed_area(c)) for c in caps) < 4.0:
            continue
        caps = [R.ccw(c) for c in caps]
        bands = [R.ccw(R.convex_hull(R.offset_poly(u, 3.0))) for u in up]
        for pc, mat in _band_pieces(R.grid_pieces(caps, CEIL_STEP), bands, "int_ru_tile_ceiling"):
            V.poly([(x, y, zc) for x, y in reversed(R.ccw(pc))], mat, ao=0.95)
        for c in caps:
            CC.append([(x, y, zc) for x, y in reversed(R.ccw(c))])
        # downlights on a 3 m grid (outside the cedar band)
        for c in caps:
            for (px, py) in _grid_points(c, 3.0, margin=0.8):
                if any(R.pip((px, py), bnd) for bnd in bands):
                    continue
                V.poly([(px - 0.22, py + 0.22, zc - 0.01), (px + 0.22, py + 0.22, zc - 0.01),
                        (px + 0.22, py - 0.22, zc - 0.01), (px - 0.22, py - 0.22, zc - 0.01)], "int_ru_led", glow=True,
                       normal_hint=(0, 0, -1))
        # the fascia on the cap's edge along the Level 2 void (both faces: seen from the void and from under the cap)
        for u in up:
            for a, b in R.edges(u):
                sg = _clip_seg(a, b, R.ccw(R.convex_hull(v)))
                if sg is None or math.dist(*sg) < 0.1:
                    continue
                pa, pb = sg
                R.quad_wall(V, pb, pa, zc - 0.6, above.z, "int_ru_white", ao=0.95)    # into the Level 2 void
                R.quad_wall(V, pa, pb, zc - 0.6, zc, "int_ru_white", ao=0.85)         # under the cap
        n_caps += len(caps)
    return n_caps


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
    CW = ColWalls()   # collision wall quads, merged before they are emitted (+ .nocam: NOCAM_CORRIDORS)
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
        # fix round 2 (blocking): the cedar soffit band under each balcony is ONE polygon (the void above offset by
        # 3.2 m, clipped to the zone), cut out of the tile ceiling: no per-piece material (sawtooth cedar slivers)
        cedar_ok = zn.type in ("corridor", "atrium_floor", "vestibule") and fid in ("G", "L1", "L2", "L3")
        bands = [R.ccw(R.convex_hull(R.offset_poly(v, 3.2))) for v in top_voids] if cedar_ok else []
        for pc, mat in _band_pieces(R.subtract(R.grid_pieces(tris, CEIL_STEP), cut), bands, st["ceil"],
                                    WHITE_SOFFITS.get(fid, ())):
            V.poly([(x, y, zc) for x, y in reversed(R.ccw(pc))], mat, ao=0.95)
            if st.get("ceil_h"):
                V.poly([(x, y, z + st["ceil_h"]) for x, y in reversed(R.ccw(pc))], st["ceil"], ao=0.95)
        if st.get("ceil_h"):
            for t_ in R.triangulate(R.clean(zn.poly, 0.12, 0.03)):
                C.poly([(x, y, z + st["ceil_h"]) for x, y in reversed(R.ccw(t_))], K.COL)
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
            if cl == "W" and cr == "W" and zl is not None and zr is not None and frozenset((zl.id, zr.id)) in OPEN_PAIRS:
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
                # fix round 4 (technical blocking): a door that straddles a class change belongs to the run holding
                # its middle. The LL print-lab door [-403.0,-266.7..-265.8] lies 0.42 m in a W|W run (corridor |
                # dance studio sample) and 0.48 m in the W|S run: the W|W part was cut as an open 0.42 m slot
                # straight into the sealed room. Here it stays solid wall; the owning run closes the door.
                sm = (d0 + d1) / 2
                own = next((rr for rr in runs if rr[0] - 1e-6 <= sm <= rr[1] + 1e-6), None)
                if own is not None and not (own[0] <= s0 + 1e-6 and own[1] >= s1 - 1e-6) \
                        and {own[2][0], own[3][0]} != {cl, cr} and {own[2][0], own[3][0]} - {"W"}:
                    continue
                dl.append((max(0.0, q0), min(RL, q1), di, dext))
            runs_all.append({"pa": pa, "pb": pb, "L": (cl, zl), "R": (cr, zr), "doors": dl, "accent": set()})
    # accent wall per meeting / hotel room: its longest run without a door, facing away from the corridor.
    # Ground meeting rooms (ru_os_g310_g320, ru_os_g330): the royal blue is the CORRIDOR end wall, the one with the
    # two honey-wood doors (EXIT signs) at its ends; the long side walls stay white with art + wainscot
    for zn in F.walk_zones():
        if not zn.style.get("accent"):
            continue
        best = None
        corridor_end = (F.id == "G" and zn.type == "meeting_room") or zn.id in FRONT_DOOR_WALL
        end_wall = zn.id in FRONT_END_WALL
        if end_wall:
            dmids = [d[2] for d in _room_doors(F, zn)]
            x0_, y0_, x1_, y1_ = R.bbox(zn.poly)
            long_ = max(x1_ - x0_, y1_ - y0_)
        if zn.id in FRONT_DOOR_WALL:
            # fix round 4 (fidelity-4 pass; ru_os_3315_3320): the door wall is often split into several runs (the
            # door bays face the corridor, the bay between backs onto a sealed room), so one run alone can be too
            # short (3315: two 2 m door runs, so the front fell to a door-less side wall; 3320: a 2.5 m front).
            # Group this room's runs by wall line, take the line carrying the most doors (then the longest) as the
            # front of the room, and paint the accent on every run of it
            lines_ = []
            for r in runs_all:
                for side in ("L", "R"):
                    cls, z_ = r[side]
                    if cls != "W" or z_ is not zn:
                        continue
                    Lr = math.dist(r["pa"], r["pb"])
                    if Lr < 0.4:
                        continue
                    d_ = ((r["pb"][0] - r["pa"][0]) / Lr, (r["pb"][1] - r["pa"][1]) / Lr)
                    if d_[0] < -1e-6 or (abs(d_[0]) <= 1e-6 and d_[1] < 0):
                        d_ = (-d_[0], -d_[1])
                    off_ = -d_[1] * r["pa"][0] + d_[0] * r["pa"][1]
                    rmid = ((r["pa"][0] + r["pb"][0]) / 2, (r["pa"][1] + r["pb"][1]) / 2)
                    # same line: near-parallel and the run's midpoint within 0.8 m of the line
                    ln = next((l_ for l_ in lines_ if abs(d_[0] * l_["d"][1] - d_[1] * l_["d"][0]) < 0.1
                               and abs(-l_["d"][1] * rmid[0] + l_["d"][0] * rmid[1] - l_["off"]) < 0.8), None)
                    if ln is None:
                        ln = {"d": d_, "off": off_, "runs": []}
                        lines_.append(ln)
                    ln["runs"].append((r, side, Lr))
            sc_best = None
            for ln in lines_:
                nd = sum(len(r["doors"]) for r, _s, _l in ln["runs"])
                tot = sum(l_ for _r, _s, l_ in ln["runs"])
                if nd and tot >= 4.0 and (sc_best is None or (nd, tot) > sc_best[0]):
                    sc_best = ((nd, tot), ln)
            if sc_best is not None:
                ln = sc_best[1]
                d_ = ln["d"]
                ends = [p for r, _s, _l in ln["runs"] for p in (r["pa"], r["pb"])]
                ss = [p[0] * d_[0] + p[1] * d_[1] for p in ends]
                a_ = ends[ss.index(min(ss))]
                b_ = ends[ss.index(max(ss))]
                if zn.id not in WHITE_SCREEN_WALL and zn.id not in NO_ACCENT:
                    for r, s_, _l in ln["runs"]:
                        r["accent"].add(s_)
                zn.style["accent_wall"] = (a_, b_)
                zn.style["front_runs"] = [(r["pa"], r["pb"]) for r, _s, _l in ln["runs"]]
                continue
        if zn.id in ACCENT_DIR:
            # fix round 5 (fidelity-4, improvement 1; ru_os_2355_2365): the slate-blue is a named END wall (the rows
            # face it down the room's length); 2365 had picked its 14.9 m long wall (turned 90 degrees)
            ux_, uy_ = ACCENT_DIR[zn.id]
            for r in runs_all:
                for side in ("L", "R"):
                    cls, z_ = r[side]
                    if cls != "W" or z_ is not zn:
                        continue
                    Lr = math.dist(r["pa"], r["pb"])
                    if Lr < 2.5 or abs((r["pb"][0] - r["pa"][0]) * ux_ + (r["pb"][1] - r["pa"][1]) * uy_) > 0.3 * Lr:
                        continue
                    sc = (r["pa"][0] + r["pb"][0]) / 2 * ux_ + (r["pa"][1] + r["pb"][1]) / 2 * uy_
                    if best is None or sc > best[3] + 0.3 or (abs(sc - best[3]) <= 0.3 and Lr > best[0]):
                        best = (Lr, r, side, sc)
        # fix round 4: FRONT_DOOR_WALL rooms take a door-carrying run first, else the corridor-facing rule
        for door_front in ((True, False) if zn.id in FRONT_DOOR_WALL else (False,)):
            if best is not None:
                break
            for r in runs_all:
                for side in ("L", "R"):
                    cls, z_ = r[side]
                    if cls != "W" or z_ is not zn:
                        continue
                    o = r["R" if side == "L" else "L"]
                    Lr = math.dist(r["pa"], r["pb"])
                    if door_front:
                        # fix round 4: the run carrying the most of the room's doors (then the longest)
                        if not r["doors"] or o[0] != "W" or Lr < 2.5:
                            continue
                        sc = (len(r["doors"]), Lr)
                        if best is None or sc > best[3]:
                            best = (Lr, r, side, sc)
                        continue
                    if corridor_end:
                        if not (o[0] == "W" and o[1] is not None and o[1].type == "corridor"):
                            continue
                        Lr = math.dist(r["pa"], r["pb"])
                        if best is None or Lr > best[0]:
                            best = (Lr, r, side)
                        continue
                    if r["doors"]:
                        continue
                    if zn.id == SUITE_ID and (r["pa"][1] + r["pb"][1]) / 2 < SUITE_SPLIT_Y:
                        continue            # fidelity-4 r2: the sitting room's blue wall is the partition (hotel())
                    if o[0] == "W" and o[1] is not None and o[1].type == "corridor" and not end_wall:
                        continue            # (2335 / 2340: the blue end wall may back onto a corridor)
                    if o[0] in ("O", "V"):
                        continue            # never the window wall (ru_os_3310: clear glass along the room)
                    Lr = math.dist(r["pa"], r["pb"])
                    if end_wall:
                        # fix round 4 (fidelity-4 pass): a real END wall, across the room's long axis (a part of
                        # the long wall had won for 2335)
                        ax_ = (1.0, 0.0) if x1_ - x0_ >= y1_ - y0_ else (0.0, 1.0)
                        if abs((r["pb"][0] - r["pa"][0]) * ax_[0] + (r["pb"][1] - r["pa"][1]) * ax_[1]) > 0.3 * Lr:
                            continue
                        # fix round 4 (fidelity-4 blocking; ru_os_2335_2340): the blue is the SHORT end wall next to
                        # the door (on the long wall beside it); 9+ rows face it down the room's length
                        if Lr < 2.5 or Lr > 0.7 * long_ or not dmids:
                            continue
                        rm = ((r["pa"][0] + r["pb"][0]) / 2, (r["pa"][1] + r["pb"][1]) / 2)
                        # fix round 4 (fidelity-4 pass): the door is on the RIGHT-hand long wall as you face the blue
                        # end wall (2335: the west end, its door 3 m along the north wall; was the east end)
                        cz_ = R.centroid(zn.poly)
                        vd = (rm[0] - cz_[0], rm[1] - cz_[1])
                        rv = (vd[1], -vd[0])
                        rd = [dm for dm in dmids if (dm[0] - rm[0]) * rv[0] + (dm[1] - rm[1]) * rv[1] > 0]
                        sc = -min(math.dist(rm, dm) for dm in (rd or dmids)) - (0.0 if rd else 100.0)
                        if best is None or sc > best[3]:
                            best = (Lr, r, side, sc)
                        continue
                    if best is None or Lr > best[0]:
                        best = (Lr, r, side)
        if best is not None and best[0] > 2.5:
            if zn.id not in WHITE_SCREEN_WALL and zn.id not in NO_ACCENT and zn.id != "hotel_room_516":
                # (516: the frame stays on this run, the royal blue moves to the bath block face; _hotel_516)
                best[1]["accent"].add(best[2])
            zn.style["accent_wall"] = (best[1]["pa"], best[1]["pb"])
    F.balc_segs = []
    for r in runs_all:
        _wall_run(RZ, F, V, C, CW, r["pa"], r["pb"], r["L"], r["R"], r["doors"], stats, r["accent"])
    stats["void_edge_fill"] = _void_edge_fill(F, V, C, CW)
    stats["void_caps"] = _void_caps(F, above, V, CC)
    stats["sealed_backing"] = _sealed_backing(F, V)
    for q in merge_col_walls(CW):
        C.poly(q, K.COL)
    for q in merge_col_walls(CW.nocam):
        C.poly(q, K.COL_NOCAM)
    stats["nocam_walls"] = len(CW.nocam)
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
    # clipped to the floor outline (+ the open balconies): the 3 m cells must not spill outside the facades
    # (invisible exterior ledges / aprons Mario could reach from the Level 1 porch)
    keep = [R.ccw(t_) for t_ in R.triangulate(F.outline)]
    kbb = [R.bbox(t_) for t_ in keep]
    balc = [R.offset_poly(zn.poly, 0.1) for zn in F.walk_zones() if zn.id in OPEN_IDS]
    for pc in [[(x0, y0), (x1, y0), (x1, y1), (x0, y1)] for (x0, y0, x1, y1) in rects] + [R.ccw(pc) for pc in exact]:
        if any(R.pip(R.centroid(pc), b_) for b_ in balc):
            C.poly([(x, y, z) for x, y in R.ccw(pc)], K.COL)
            continue
        for piece in _clip_outline(pc, F.outline, keep, kbb):
            C.poly([(x, y, z) for x, y in R.ccw(piece)], K.COL)
    avoid = list(F.voids) + list(voids_above) + [z_.poly for z_ in F.zones if z_.type in DOUBLE_TYPES]
    for zc, polys in ceil_groups.items():
        # smaller rooms of another ceiling height inside this group's envelopes are cut out of it
        own = [zn for zn, zz in zone_zc if zz == zc]
        other = [o.poly for o, zz in zone_zc if zz != zc
                 and any(o.area < zn.area and _bb_overlap(o.bb, zn.bb) for zn in own)]
        # fix round 5 (design pass, improvement 7): a LOWER ceiling's 3 m cover cells spilled into the taller zone
        # next to it (the 2.7 m elevator-car ceilings put a 2.7 m invisible soffit over the L6 hotel corridor at
        # x -444..-438, y -268.5..-267; the camera ended above it). Taller neighbours are avoided too, so the cells
        # along them are exact pieces of the low zone only (a higher ceiling spilling over a lower one is harmless:
        # the lower ceiling is found first). Such a low zone (smaller than a taller zone it touches) gets its exact
        # triangulated outline instead of 3 m cells.
        low = [k for k, zn in enumerate(own)
               if any(o.area > zn.area and zz > zc + 0.05 and _bb_overlap(o.bb, zn.bb) for o, zz in zone_zc)]
        if low and len(own) == len(polys):
            holes = [h for a in avoid + other for h in _convex_parts(a)]
            for k in low:
                for t_ in R.triangulate(polys[k]):
                    for pc in R.subtract([R.ccw(t_)], holes):
                        CC.append([(x, y, zc) for x, y in reversed(R.ccw(pc))])
            polys = [p for k, p in enumerate(polys) if k not in low]
        rects, exact = R.rect_cover(polys, 3.0, avoid=avoid + other) if polys else ([], [])
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


def _closed_look(F):
    """Fidelity-4 (round 2; ru_os_2315_2330, ru_os_2345_2350, ru_os_3305): the L2 / L3 meeting rooms' corridor doors
    are closed walnut leaves with a narrow vision lite. Each meeting room keeps ONE walk-through door (its first
    plan door to a corridor, else to its neighbour room); its other plan doors between two walkable zones (the
    second corridor door, the doors between adjoining rooms) are drawn closed and walled. -> {door index}."""
    got = getattr(F, "_closed_look", None)
    if got is not None:
        return got
    out = set()
    if F.id in ("L2", "L3"):
        info = []
        for i, d in enumerate(F.doors):
            m = ((d[0] + d[2]) / 2, (d[1] + d[3]) / 2)
            L = math.dist((d[0], d[1]), (d[2], d[3]))
            if L < 0.3:
                continue
            nx, ny = (d[3] - d[1]) / L, -(d[2] - d[0]) / L
            ca, za = F.cls_at((m[0] + nx * 0.35, m[1] + ny * 0.35))
            cb, zb = F.cls_at((m[0] - nx * 0.35, m[1] - ny * 0.35))
            if ca != "W" or cb != "W" or za is None or zb is None or za is zb:
                continue
            info.append((i, za, zb))
        keep, cand = set(), set()
        for zn in F.walk_zones():
            if zn.type != "meeting_room":
                continue
            mine = [(i, (zb if za is zn else za)) for i, za, zb in info if zn in (za, zb)]
            if not mine:
                continue
            corr = [i for i, o in mine if o.type != "meeting_room"]
            keep.add(corr[0] if corr else mine[0][0])
            cand.update(i for i, _ in mine)
        out = cand - keep
    if F.id == "G":
        # fix round 5 (fidelity-3; ru_os_g330): the G325 / G330 connecting door (plan x -368.4..-366.2, y -271.3) is a
        # closed wood leaf under an EXIT sign; it was an open 2.2 m gap that showed G325's royal wall like a blue
        # door. Both rooms keep their corridor doors.
        for i, d in enumerate(F.doors):
            m = ((d[0] + d[2]) / 2, (d[1] + d[3]) / 2)
            if abs(m[0] + 367.3) < 0.4 and abs(m[1] + 271.3) < 0.3:
                out.add(i)
    F._closed_look = out
    return out


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
        open_ext = open_ext or _terrace_door(fid, (pa[0] + (pb[0] - pa[0]) * (d0 + d1) / 2 / RL,
                                                   pa[1] + (pb[1] - pa[1]) * (d0 + d1) / 2 / RL))
        if open_ext and ent is None:
            ent = True
        if kinds == {"W"} and di in _closed_look(F):
            door_recs.append(("closed", d0, d1))         # fidelity-4 r2: a meeting room's second door, closed
            stats["doors_closed"] += 1
        elif kinds == {"W"}:
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
        if cls == "W" and ocls == "V":
            # an atrium balcony edge: no wall, no doors (the plan's segments on the void line are the railing);
            # the V side builds the open edge (_balcony_edge: fascia, picket rail, slab edge)
            continue
        if cls == "W" and zn.type == "balcony" and ocls == "O":
            # fix round 2 (blocking; ru_hotel_balcony): an open balcony has no facade wall or glass on its outer edge,
            # only the white slotted balustrade (hotel()); an invisible guard keeps Mario on it
            col_face(CW, fa, fb, z, z + zn.style["clear"], mat=K.COL_NOCAM)
            continue
        if cls == "W":
            st = zn.style
            h = st["clear"]
            mat = st["wall"]
            if side in accent and st.get("accent"):
                mat = st["accent"]
            win = window_spec(fid, pa, pb, zn) if ocls == "O" else None
            if win is not None and zn.id == "game_room" and win[2] == "curtain":
                mat = "int_ru_wall_charcoal"        # fidelity-3 (round 2): the dark-grey dado under the east windows
            if zn.id == "game_room" and all(-459.6 <= p_[0] <= -440.0 and -297.5 <= p_[1] <= -281.0 for p_ in (pa, pb)):
                # fix round 4 (fidelity-3 blocking; ru_gr_billiards_room 'dark walls'): the billiards hall's walls are
                # a warm charcoal panel, not the lanes' navy (navy walls + blue felt + blue carpet read blue-on-blue)
                mat = "int_ru_wall_billiards"
            hh = list(hs)
            if ozn is not None and ozn.id == "food_court_servery":
                hh.extend(_storefront_holes(fa, fb, z))
            if win is not None:
                hh.append((0.0, math.dist(fa, fb), z + win[0], z + win[1]))
            base = "int_ru_black" if zn.type not in ("hotel_room",) else "int_ru_wall"
            # the north entrance vestibule is a glass box (aluminium frames, ru_ribbon_cutting_doors): its inner
            # walls are glass storefront with a steel base and a transom bar over the door heads
            vest_glass = (ocls == "W" and sorted((zn.type, getattr(ozn, "type", None)))[0] in ("atrium_floor", "corridor")
                          and bool({zn.id, getattr(ozn, "id", None)} & GLASS_VESTIBULES))
            # fix round 2 (blocking): room 516 opens onto its balcony through a floor-to-ceiling glass wall + slider
            if ocls == "W" and "balcony" in (zn.type, getattr(ozn, "type", None)):
                vest_glass = True
            # fix round 2 (blocking; ru_es_oelrich_8951): the Gator Esports Center fronts the Game Room's billiards
            # with a glass storefront (steel base, transom; the glass door, sign and TVs: game_room())
            es_front = False
            if ocls == "W" and {zn.id, getattr(ozn, "id", None)} == {"game_room", "gator_esports_center"} \
                    and abs(pa[0] + 459.4) < 0.4 and abs(pb[0] + 459.4) < 0.4 and RL > 10.0:
                vest_glass = True
                es_front = True
            if es_front:
                # fix round 4 (fidelity-3 blocking; ru_es_oelrich_8951 / 9352): dark smoked glass, ONE layer (the
                # Game Room side; the milky int_ru_glass x 2 read as a frosted pale wall), black base and transom
                if zn.id == "game_room":
                    wall_face(V, fa, fb, z, z + h, "int_ru_glass_smoke", base="int_ru_black", holes=hh)
                    _rail_strip(V, fa, fb, z + GLASS_DOOR_H, z + GLASS_DOOR_H + 0.1, hs, nrm, mat="int_ru_black")
                else:
                    # fix round 5 (fidelity-3 blocking; ru_es_oelrich_9188 / 9215 / 9352, ru_es_overview): seen from
                    # INSIDE the arena the storefront is a solid near-black hex wall (the red-bench run and south of
                    # the door bay; every inside photo is a dark room) with smoked glass only in the door / sign / TV
                    # bay (y -296.0 .. -291.8). The faces are one-sided, so each side sees exactly one smoked layer
                    # and the Game Room still looks into the blue-lit arena through its own.
                    LF = math.dist(fa, fb)

                    def _ps(s_, fa=fa, fb=fb, LF=LF):
                        return (fa[0] + (fb[0] - fa[0]) * s_ / LF, fa[1] + (fb[1] - fa[1]) * s_ / LF)
                    if abs(fb[1] - fa[1]) > 1.0:
                        b0_, b1_ = sorted(((-296.0 - fa[1]) / (fb[1] - fa[1]) * LF, (-291.8 - fa[1]) / (fb[1] - fa[1]) * LF))
                    else:
                        b0_, b1_ = 0.0, LF
                    b0_, b1_ = max(0.0, b0_), min(LF, b1_)
                    for s0_, s1_, gl_ in ((0.0, b0_, False), (b0_, b1_, True), (b1_, LF, False)):
                        if s1_ - s0_ < 0.05:
                            continue
                        hp_ = [(max(h_[0], s0_) - s0_, min(h_[1], s1_) - s0_, h_[2], h_[3]) for h_ in hh
                               if h_[1] > s0_ and h_[0] < s1_]
                        wall_face(V, _ps(s0_), _ps(s1_), z, z + h, "int_ru_glass_smoke" if gl_ else mat,
                                  base="int_ru_black", holes=hp_)
                    _rail_strip(V, fa, fb, z + GLASS_DOOR_H, z + GLASS_DOOR_H + 0.1, hs, nrm, mat="int_ru_black")
            elif vest_glass:
                # fix round 2 (design): the entrance vestibules get the clear glass and a thinner transom (the
                # milky int_ru_glass x 2 layers hazed the atrium reveal on arrival; the 10 cm transom was the top
                # L1 camera occluder after the trees)
                vest_ = bool({zn.id, getattr(ozn, "id", None)} & GLASS_VESTIBULES)
                # fix round 5 (design, improvement 3): the north vestibule's inner bank is the second layer the
                # arrival camera looks through (door leaves + bank): faint glass there; the south one stays as is
                gm_ = ("int_ru_glass_faint" if "north_entrance" in {zn.id, getattr(ozn, "id", None)}
                       else "int_ru_glass_clear") if vest_ else "int_ru_glass"
                wall_face(V, fa, fb, z, z + h, gm_, base="int_ru_steel", holes=hh)
                _rail_strip(V, fa, fb, z + GLASS_DOOR_H - (0.05 if vest_ else 0.0), z + GLASS_DOOR_H + (0.0 if vest_ else 0.1),
                            hs, nrm, mat="int_ru_steel")
            elif zn.id in ROYAL_BAY and side in accent and st.get("accent"):
                # fix round 5 (fidelity-3; ru_os_g325): the royal blue is a bay lit by a row of wall-washers, with the
                # white wall (and the wood door) to its left and a white return to its right; the whole 11 m run
                # was royal. White wall round the bay (it is a hole in the white face, so nothing is coplanar), the
                # once-mapped scallop texture in the bay, the chair rail on the white parts only
                LF = math.dist(fa, fb)
                ux_, uy_ = (fb[0] - fa[0]) / LF, (fb[1] - fa[1]) / LF
                q0_, q1_ = sorted(((p_[0] - fa[0]) * ux_ + (p_[1] - fa[1]) * uy_ for p_ in ROYAL_BAY[zn.id]))
                q0_, q1_ = max(0.0, q0_), min(LF, q1_)
                hb_ = min(h, st.get("ceil_h", h))             # the bay ends at the dropped ceiling (white above)
                bay_ = [(q0_, q1_, z - 1.0, z + hb_)] if q1_ - q0_ > 0.05 else []
                bse_ = st["base"] if st["base"] else base
                wall_face(V, fa, fb, z, z + h, st["wall"], base=bse_, holes=hh + bay_)
                _rail_strip(V, fa, fb, z + 0.88, z + 0.96, hs + bay_, nrm)
                ba_ = (fa[0] + ux_ * q0_, fa[1] + uy_ * q0_)
                bb_ = (fa[0] + ux_ * q1_, fa[1] + uy_ * q1_)
                if bay_:
                    wall_face(V, ba_, bb_, z, z + 0.10, bse_)
                    R.panel(V, ba_, bb_, z + 0.10, z + hb_, "int_ru_wall_royal_wash", off=0.0)
                # the three wall-washer cans in the ceiling in front of the bay (1.5 cm under the ceiling)
                for k_ in range(3 if bay_ else 0):
                    s_ = q0_ + (q1_ - q0_) * (k_ + 0.5) / 3
                    cx_, cy_ = fa[0] + ux_ * s_ + nrm[0] * 0.55, fa[1] + uy_ * s_ + nrm[1] * 0.55
                    zc_ = z + st.get("ceil_h", h)
                    V.box(cx_ - 0.11, cy_ - 0.11, zc_ - 0.035, cx_ + 0.11, cy_ + 0.11, zc_ - 0.015, "int_ru_led",
                          faces="-z+x-x+y-y", glow=True)
            else:
                wall_face(V, fa, fb, z, z + h, mat, base=st["base"] if st["base"] else base, holes=hh)
            col_face(CW, fa, fb, z, z + h, holes=[x for x in hs],
                     mat=K.COL_NOCAM if (not any(r[0] in ("open", "entrance") for r in door_recs)
                                         and _nocam_wall(fid, zn, ocls, fa, fb, core=_core_room(F, ozn))) else K.COL)
            if win is not None:
                # fix round 2 (fidelity, ru_ribbon_cutting_doors): the curtain glass + its mullions / transom stop at
                # the north entrance's four door bays (_entrance_door_pair fills them with the door bank)
                bank = []
                if fid == "L1":
                    LF = max(1e-6, math.dist(fa, fb))
                    for kind_, d0_, d1_ in door_recs:
                        if kind_ != "entrance":
                            continue
                        s0_, s1_ = sorted((S(d0_), S(d1_)))
                        mx_ = fa[0] + (fb[0] - fa[0]) * (s0_ + s1_) / 2 / LF
                        my_ = fa[1] + (fb[1] - fa[1]) * (s0_ + s1_) / 2 / LF
                        if abs(my_ + 257.95) < 0.3 and -385.0 < mx_ < -376.0:
                            bank.append((s0_, s1_))
                        elif _terrace_door(fid, (mx_, my_)):
                            bank.append((s0_, s1_))
                if bank:
                    LF = max(1e-6, math.dist(fa, fb))
                    cuts = [0.0]
                    for s0_, s1_ in sorted(bank):
                        cuts += [s0_, s1_]
                    cuts.append(LF)
                    terr_ = zn.id == "l1_corridor_08" and ocls == "O"
                    for u0_, u1_ in zip(cuts[0::2], cuts[1::2]):
                        if u1_ - u0_ > 0.3:
                            _window(V, C, (fa[0] + (fb[0] - fa[0]) * u0_ / LF, fa[1] + (fb[1] - fa[1]) * u0_ / LF),
                                    (fa[0] + (fb[0] - fa[0]) * u1_ / LF, fa[1] + (fb[1] - fa[1]) * u1_ / LF),
                                    z, win, nrm, t, ocls, glass="int_ru_glass" if terr_ else "int_ru_glass_clear")
                    if terr_:
                        # fix round 5 (fidelity-2): over the open terrace doorway, transom glass from the door head
                        # to the curtain glass head, in the pane plane (a steel bar at the door head)
                        for s0_, s1_ in bank:
                            ta_ = (fa[0] + (fb[0] - fa[0]) * s0_ / LF - nrm[0] * t,
                                   fa[1] + (fb[1] - fa[1]) * s0_ / LF - nrm[1] * t)
                            tb_ = (fa[0] + (fb[0] - fa[0]) * s1_ / LF - nrm[0] * t,
                                   fa[1] + (fb[1] - fa[1]) * s1_ / LF - nrm[1] * t)
                            R.quad_wall(V, ta_, tb_, z + GLASS_DOOR_H + 0.08, z + win[1], "int_ru_glass", ao=1.0)
                            R.seg_box(V, ta_, tb_, 0.05, z + GLASS_DOOR_H, z + GLASS_DOOR_H + 0.08, "int_ru_steel",
                                      faces="side", ao=0.95)
                else:
                    _window(V, C, fa, fb, z, win, nrm, t, ocls)
            # chair rail in meeting rooms / corridors of the 2016 wing (photos: white chair rail at ~0.9 m)
            # fix round 4 (fidelity-3; ru_os_g330 / g310_g320 / g325): no rail across a Ground room's accent wall
            # (the photos show the blue wall clean; the white rail read as a line across it)
            if zn.type in ("meeting_room", "chamber") and not (fid == "G" and side in accent and st.get("accent")):
                _rail_strip(V, fa, fb, z + 0.88, z + 0.96, hs, nrm)
            for kind, d0, d1 in door_recs:
                s0, s1 = sorted((S(d0), S(d1)))
                da = (fa[0] + (fb[0] - fa[0]) * s0 / max(1e-6, math.dist(fa, fb)),
                      fa[1] + (fb[1] - fa[1]) * s0 / max(1e-6, math.dist(fa, fb)))
                db = (fa[0] + (fb[0] - fa[0]) * s1 / max(1e-6, math.dist(fa, fb)),
                      fa[1] + (fb[1] - fa[1]) * s1 / max(1e-6, math.dist(fa, fb)))
                if kind in ("closed", "closed_ext"):
                    dm = _door_mat(zn, ozn, kind)
                    if dm == "int_ru_door_elev":
                        _elevator_doors(V, da, db, z, fa, fb)
                    else:
                        door_leaves(V, da, db, z, min(2.4 if dm != "int_ru_door_glass" else 2.8, h - 0.3), dm)
                elif kind in ("open", "entrance"):
                    hd = DOOR_H if kind == "open" else GLASS_DOOR_H
                    # jambs + head trim on this face
                    # aluminium frames at entrances and round the vestibules (ru_ribbon_cutting_doors), wood elsewhere
                    jm = "int_ru_steel" if (kind == "entrance" or "vestibule" in (zn.type, getattr(ozn, "type", None))
                                            or _meeting_door(fid, zn, ozn)) else "int_ru_wood_panel"
                    V.box(da[0] - 0.05, da[1] - 0.05, z, da[0] + 0.05, da[1] + 0.05, z + hd, jm, faces="+x-x+y-y")
                    V.box(db[0] - 0.05, db[1] - 0.05, z, db[0] + 0.05, db[1] + 0.05, z + hd, jm, faces="+x-x+y-y")
                    if kind == "entrance" and fid == "L1" and abs((da[1] + db[1]) / 2 + 257.95) < 0.3 \
                            and -385.0 < (da[0] + db[0]) / 2 < -376.0:
                        _entrance_door_pair(V, (da[0] - nrm[0] * t, da[1] - nrm[1] * t),
                                            (db[0] - nrm[0] * t, db[1] - nrm[1] * t), z)
        elif cls == "O" and ocls == "W" and getattr(ozn, "type", None) == "balcony":
            continue                        # open balcony: no facade band (fix round 2)
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
            vest = "vestibule" in (getattr(left[1], "type", None), getattr(right[1], "type", None))
            # fidelity-4 r2: the meeting rooms' open doorways get painted returns (the wood returns read as door
            # leaves standing open into the L2 / L3 corridors)
            jret = "int_ru_wall" if _meeting_door(fid, left[1], right[1]) else \
                ("int_ru_wood_panel" if (kind == "open" and not vest) else "int_ru_steel")
            V.poly([(q0[0], q0[1], z), (q1[0], q1[1], z), (q1[0], q1[1], z + hd), (q0[0], q0[1], z + hd)],
                   jret,
                   normal_hint=(dir_[0], dir_[1], 0))
            C.poly([(q0[0], q0[1], z), (q1[0], q1[1], z), (q1[0], q1[1], z + hd), (q0[0], q0[1], z + hd)], K.COL,
                   normal_hint=(dir_[0], dir_[1], 0))
        if kind == "open":
            zl = left[1].style["floor"] if left[1] and left[1].style else "int_ru_terrazzo"
            threshold(V, C, da, db, n, z, 2 * t + 0.5, zl)


def _storefront_holes(fa, fb, z, near=0.5, h=None):
    """Openings in the corridor face of the servery wall where the SERVERY_FRONTS storefronts are."""
    h = FC_FRONT_H if h is None else h
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


def _meeting_door(fid, za, zb):
    return fid in ("L2", "L3") and "meeting_room" in (getattr(za, "type", None), getattr(zb, "type", None))


def _door_mat(zn, ozn, kind):
    if kind == "closed_ext":
        return "int_ru_door_glass"
    t = ozn.type if ozn is not None else ""
    if t == "elevator":
        return "int_ru_door_elev"           # brushed-steel sliding doors + call buttons (fidelity-4)
    if t == "hotel_room":
        return "int_ru_door_hotel"          # cherry guest-room door with a brass number plate (fidelity-4)
    if t in ("restroom", "service", "room", "elevator") and (ozn is None or not ozn.name.startswith("Stair")):
        return "int_ru_door" if t == "restroom" else "int_ru_door_steel" if t in ("service", "elevator") else "int_ru_door"
    if t in ("office", "office_suite", "retail", "dining_retail", "food_servery"):
        return "int_ru_door_glass" if t in ("office_suite", "retail", "dining_retail") else "int_ru_door"
    if zn.type == "ballroom" or (ozn is not None and ozn.type == "ballroom"):
        return "int_ru_door_walnut"
    if zn.fid in ("L2", "L3") and "meeting_room" in (zn.type, t):
        return "int_ru_door_meeting"        # fidelity-4 r2: walnut leaf, narrow vision lite, lever
    return "int_ru_door"


def _rail_strip(V, a, b, z0, z1, holes, nrm, mat="int_ru_white"):
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
        R.quad_wall(V, p0, p1, z0, z1, mat, ao=1.0)


def _dark_band(V, a, b, z0, z1):
    L = math.dist(a, b)
    if L < 1.4:
        return
    dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    p0 = (a[0] + dx * 0.6, a[1] + dy * 0.6)
    p1 = (b[0] - dx * 0.6, b[1] - dy * 0.6)
    R.quad_wall(V, p0, p1, z0, z1, "int_ru_glass_blue", ao=1.0)


def _window(V, C, a, b, z, win, nrm, t, ocls, glass="int_ru_glass"):
    """A glass pane in the wall plane (translucent, both sides), sill / head reveals, mullions."""
    sill, head, kind = win
    L = math.dist(a, b)
    if L < 0.3:
        return
    # pane in the wall centre plane
    ca = (a[0] - nrm[0] * t, a[1] - nrm[1] * t)
    cb = (b[0] - nrm[0] * t, b[1] - nrm[1] * t)
    R.quad_wall(V, ca, cb, z + sill, z + head, glass, ao=1.0)
    bay = 1.5 if kind != "clerestory" else 2.0
    mullions(V, ca, cb, z + sill, z + head, bay=bay, t=0.04,
             transoms=() if head - sill < 2.5 else (z + sill + min(2.7, (head - sill) * 0.55),))
    if sill > 0.05:
        V.poly([(a[0], a[1], z + sill), (b[0], b[1], z + sill), (cb[0], cb[1], z + sill), (ca[0], ca[1], z + sill)],
               "int_ru_white", normal_hint=(0, 0, 1))
    # fix round 4 (fidelity-1): the head reveal sits 1.5 cm under the head (a full-height pane's reveal was coplanar
    # with the ceiling: 26 + 43 z-fighting strips at the north vestibule and across Level 1 east)
    zh = z + head - 0.015
    V.poly([(a[0], a[1], zh), (ca[0], ca[1], zh), (cb[0], cb[1], zh), (b[0], b[1], zh)],
           "int_ru_white", normal_hint=(0, 0, -1))


def _balcony_edge(V, C, a, b, z, F):
    """Atrium balcony edge (ru_atrium_enr_lounge, ru_atrium_hdr_flickr): a white fascia band dropping FASCIA below
    the floor with an LED cove, a cut-out picket railing with a silver cap; collision: the railing (both sides)
    and the slab edge facing INTO the void (lesson: floor-hole edges face into the hole)."""
    L = math.dist(a, b)
    if L < 0.05:
        return
    if hasattr(F, "balc_segs"):
        F.balc_segs.append((a, b))
    # a -> b has its normal toward the void (side line of the V side)
    zb = z - SLAB - FASCIA * 0.5            # fascia bottom
    R.quad_wall(V, a, b, zb + 0.20, z + 0.12, "int_ru_white", ao=1.0)
    nx, ny = (b[1] - a[1]) / L, -(b[0] - a[0]) / L

    def inb(p, d):                          # d metres in from the void edge (under the slab)
        return (p[0] - nx * d, p[1] - ny * d)
    # design pass: the band's bottom edge is rounded in two facets (ru_atrium_enr_lounge: curved white bands; the
    # vertex light shades the facets apart), then the soffit lip
    for (d0, h0), (d1, h1), sh in (((0.0, 0.20), (0.06, 0.07), 0.94), ((0.06, 0.07), (0.16, 0.0), 0.86)):
        a0, b0, a1, b1 = inb(a, d0), inb(b, d0), inb(a, d1), inb(b, d1)
        V.poly([(a1[0], a1[1], zb + h1), (b1[0], b1[1], zb + h1), (b0[0], b0[1], zb + h0), (a0[0], a0[1], zb + h0)],
               "int_ru_white", normal_hint=(nx * 0.7, ny * 0.7, -0.7), ao=sh)
    # fascia underside (soffit lip) + LED cove line
    ia, ib = inb(a, 0.35), inb(b, 0.35)
    la, lb = inb(a, 0.16), inb(b, 0.16)
    V.poly([(la[0], la[1], zb), (ia[0], ia[1], zb), (ib[0], ib[1], zb), (lb[0], lb[1], zb)], "int_ru_white",
           normal_hint=(0, 0, -1), ao=0.9)
    R.quad_wall(V, (ib[0], ib[1]), (ia[0], ia[1]), z - SLAB - FASCIA * 0.5, z - SLAB, "int_ru_white", ao=0.85)
    led_a = (a[0] + nx * 0.01, a[1] + ny * 0.01)
    led_b = (b[0] + nx * 0.01, b[1] + ny * 0.01)
    R.quad_wall(V, led_a, led_b, z - 0.1, z - 0.04, "int_ru_led", glow=True)
    # railing: pickets (double-sided cut-out) slightly inboard of the edge, top rail; open where a scissor-stair
    # flight meets this slab edge (STAIR_GAPS, filled by build() before the floors)
    ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    runs = [(0.0, L)]
    for gp, gd in STAIR_GAPS.get(F.id, ()):
        # interval of the edge within the flight's rails, near its end point. Fix round 2 (blocking): only on the
        # edge line the flight actually crosses (it opened metres of rail on neighbouring edges at shallow angles),
        # and 0.2 m narrower than the flight's own rails, so the balcony rail's collision overlaps their ends
        if R.seg_point_dist(gp, a, b) > 1.5:
            continue
        if abs((gp[0] - a[0]) * uy - (gp[1] - a[1]) * ux) > 0.3:
            continue
        c0 = gd[0] * (a[1] - gp[1]) - gd[1] * (a[0] - gp[0])
        c1 = gd[0] * uy - gd[1] * ux
        if abs(c1) < 1e-6:
            continue
        w = STAIR_W / 2 - 0.25
        s0, s1 = sorted(((-w - c0) / c1, (w - c0) / c1))
        nr = []
        for r0, r1 in runs:
            if s1 <= r0 or s0 >= r1:
                nr.append((r0, r1))
                continue
            if s0 > r0:
                nr.append((r0, s0))
            if s1 < r1:
                nr.append((s1, r1))
        runs = nr
    # design pass (wayfinding): the floor number on the fascia beside each scissor-stair end (read from the flight)
    for gp, gd in STAIR_GAPS.get(F.id, ()):
        key = (F.id, round(gp[0], 1), round(gp[1], 1))
        if key in FASCIA_NUMS or R.seg_point_dist(gp, a, b) > 1.5:
            continue
        sg = (gp[0] - a[0]) * ux + (gp[1] - a[1]) * uy
        cs = next((c for c in (sg + 1.9, sg - 1.9) if 0.6 <= c <= L - 0.6), None)
        if cs is None:
            continue
        FASCIA_NUMS.add(key)
        cell = FLOOR_CELL[F.id]
        u0, v0 = (cell % 4) * 0.25, 1.0 - (cell // 4 + 1) * 0.5
        R.panel(V, (a[0] + ux * (cs - 0.45), a[1] + uy * (cs - 0.45)), (a[0] + ux * (cs + 0.45), a[1] + uy * (cs + 0.45)),
                zb + 0.22, zb + 1.07, "int_ru_floor_atlas", off=0.025, u0=u0, u1=u0 + 0.25, v0=v0, v1=v0 + 0.5,
                glow=True)
    for r0, r1 in runs:
        if r1 - r0 < 0.08:
            continue
        pa_ = (a[0] + ux * r0, a[1] + uy * r0)
        pb_ = (a[0] + ux * r1, a[1] + uy * r1)
        Lr = r1 - r0
        ra = (pa_[0] - nx * 0.12, pa_[1] - ny * 0.12)
        rb = (pb_[0] - nx * 0.12, pb_[1] - ny * 0.12)
        V.poly([(ra[0], ra[1], z), (rb[0], rb[1], z), (rb[0], rb[1], z + RAIL_H), (ra[0], ra[1], z + RAIL_H)],
               "int_ru_picket", uvs=[(0, 0), (Lr / 1.1, 0), (Lr / 1.1, 1), (0, 1)], ao=1.0)
        R.seg_box(V, ra, rb, 0.04, z + RAIL_H, z + RAIL_H + 0.06, "int_ru_steel", faces="sidetop")
        # curb on the slab edge
        R.seg_box(V, (pa_[0] - nx * 0.06, pa_[1] - ny * 0.06), (pb_[0] - nx * 0.06, pb_[1] - ny * 0.06), 0.06, z,
                  z + 0.12, "int_ru_white", faces="sidetop")
        # collision: the railing block (both faces + ends; 30 cm thick: no vanilla push-through from behind)
        # fix round 5 (technical blocking 1; spotfall_r): 30 cm is less than Mario's 0.5 m wall radius, so at the
        # flight junctions (where the end caps let him close in on the floor face) the block's VOID face pulled him
        # through it into the void (284 falls at three junctions). The block now runs 0.6 m thick, its extra 0.3 m
        # outboard over the void (the floor face stays where it was), except where that outboard part would reach
        # into a scissor flight's walkway (|offset from the flight axis| < 0.66 m): there it keeps the 0.3 m block.
        thin = []
        for gp, gd in STAIR_GAPS.get(F.id, ()):
            if R.seg_point_dist(gp, a, b) > 3.0:
                continue
            c0_ = gd[0] * (a[1] - gp[1]) - gd[1] * (a[0] - gp[0])
            c1_ = gd[0] * uy - gd[1] * ux
            c2_ = gd[0] * ny - gd[1] * nx
            if abs(c1_) < 1e-6:
                continue
            ends = []
            for dd in (0.03, 0.33):
                ends += [(-0.66 - c0_ - c2_ * dd) / c1_, (0.66 - c0_ - c2_ * dd) / c1_]
            thin.append((min(ends), max(ends)))
        segs = [(r0, r1, True)]
        for t0, t1 in thin:
            nsg = []
            for q0, q1, thick in segs:
                if not thick or t1 <= q0 or t0 >= q1:
                    nsg.append((q0, q1, thick))
                    continue
                if t0 > q0:
                    nsg.append((q0, t0, True))
                nsg.append((max(q0, t0), min(q1, t1), False))
                if t1 < q1:
                    nsg.append((t1, q1, True))
            segs = nsg
        for q0, q1, thick in segs:
            if q1 - q0 < 0.02:
                continue
            ca_ = (a[0] + ux * q0 + nx * (0.03 if thick else -0.12), a[1] + uy * q0 + ny * (0.03 if thick else -0.12))
            cb_ = (a[0] + ux * q1 + nx * (0.03 if thick else -0.12), a[1] + uy * q1 + ny * (0.03 if thick else -0.12))
            R.col_seg(C, ca_, cb_, 0.3 if thick else 0.15, z, z + RAIL_H + 0.06, K.COL_NOCAM)
    # collision: slab edge into the void
    C.poly([(a[0], a[1], z - SLAB), (b[0], b[1], z - SLAB), (b[0], b[1], z), (a[0], a[1], z)], K.COL)


STAIR_GAPS = {}     # floor id -> [(point on the slab edge, flight direction)] (scissor-stair ends; _stair_ends)
FASCIA_NUMS = set()     # (floor, stair-end point) that already carry a floor number on the fascia (_balcony_edge)
FLOOR_CELL = {"LL": 0, "G": 1, "L1": 2, "L2": 3, "L3": 4, "L4": 5, "L5": 6, "L6": 7}   # int_ru_floor_atlas cells


def _stair_ends(RZ):
    """Where the atrium scissor-stair flights meet a balcony slab edge (same geometry as atrium_stairs)."""
    tip, ne, se = CHEVRON["tip"], CHEVRON["ne"], CHEVRON["se"]
    dne, dse = _unit2(tip, ne), _unit2(tip, se)
    nne = (dne[1], -dne[0])
    nse = (-dse[1], dse[0])
    w2 = STAIR_W / 2
    mne0 = (tip[0] + nne[0] * w2, tip[1] + nne[1] * w2)
    mse0 = (tip[0] + nse[0] * w2, tip[1] + nse[1] * w2)
    out = {}
    for lo, hi in (("G", "L1"), ("L1", "L2"), ("L2", "L3")):
        Flo, Fhi = RZ.floors[lo], RZ.floors[hi]
        void_lo = next((v for v in Flo.voids if R.pip(tip, v)), None)
        void_hi = next(v for v in Fhi.voids if R.pip(tip, v))
        if void_lo is not None:
            t_se = R.seg_intersect(mse0, dse, void_lo)
            out.setdefault(lo, []).append(((mse0[0] + dse[0] * t_se, mse0[1] + dse[1] * t_se), dse))
        t_ne = R.seg_intersect(mne0, dne, void_hi)
        out.setdefault(hi, []).append(((mne0[0] + dne[0] * t_ne, mne0[1] + dne[1] * t_ne), dne))
    return out


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
        zc = z + st.get("ceil_h", st["clear"]) - 0.01
        sp = st["spacing"]
        # no fixture over a void (this floor's or the next floor's: there is no ceiling there)
        nxt = RZ.floors.get(FLOORS[FLOORS.index(fid) + 1]) if fid != FLOORS[-1] else None
        voids_above = list(F.voids) + (list(nxt.voids) if nxt is not None else [])
        pts = _grid_points(zn.poly, sp, margin=0.9 if kind != "car" else 0.4)
        pts = [p for p in pts if not any(R.pip(p, v) or R.poly_dist(p, v) < 0.5 for v in voids_above)]
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
        # the warp strip starts STRIP_GAP outside the door line (area 1's strip ends exactly on it: a shared edge
        # resolves to both warps -> a flip every frame); a plain floor covers the gap
        g0 = e.get("strip_gap", STRIP_GAP)
        a_, b_ = (a[0] + n[0] * g0, a[1] + n[1] * g0), (b[0] + n[0] * g0, b[1] + n[1] * g0)
        strip = R.ccw([a_, b_, (b[0] + n[0] * dpt, b[1] + n[1] * dpt), (a[0] + n[0] * dpt, a[1] + n[1] * dpt)])
        R.col_floor(C, strip, z2 + WARP_UP, mat=WARP_MAT[e["index"]], raw=True)
        if g0 > 0:
            # fix round 2 (blocking): the gap floor starts 0.15 m INSIDE the door line, under the clipped interior
            # floor's edge (it stopped 3-7 cm short of the line: a NULL-floor crack -> death warp / invisible wall)
            ai, bi = (a[0] - n[0] * 0.15, a[1] - n[1] * 0.15), (b[0] - n[0] * 0.15, b[1] - n[1] * 0.15)
            R.col_floor(C, R.ccw([ai, bi, (b_[0] + n[0] * 0.02, b_[1] + n[1] * 0.02),
                                  (a_[0] + n[0] * 0.02, a_[1] + n[1] * 0.02)]), z2)
        # fix round 2: 3 mm over the interior floor's base (z - 0.02): the floor's clipped edge runs a few cm past the
        # door line, and the two met coplanar there (0.41 m2 of zero-offset strips at the north door)
        # fix round 4 (fidelity-1): 1.2 cm over the floor's base, not 3 mm (5.98 vs 5.983 m rounded to the same game
        # unit, 598: the north door line still z-fought over an 8 cm strip in the installed export)
        R.floor_poly(V, R.ccw([a, b, (b[0] + n[0] * dpt, b[1] + n[1] * dpt), (a[0] + n[0] * dpt, a[1] + n[1] * dpt)]),
                     z2 - 0.008, "int_ru_paving", step=3.0)
        if e.get("porch"):
            porch = R.ccw(e["porch"])
            R.col_floor(C, R.offset_poly(porch, 0.05), z2)
            R.floor_poly(V, porch, z2 - 0.008, "int_ru_paving", step=3.0)
            # landing rails (east / west sides of the porch, the stairs go down beyond them)
            xs = [p[0] for p in porch]
            ys = [p[1] for p in porch]
            rails = [((xr, min(ys)), (xr, max(ys))) for xr in (min(xs), max(xs))]
            # south edge beside the door line (the strip is the only way out), at the door line
            ys_ = (a[1] + b[1]) / 2
            ax0, bx0 = sorted((a[0], b[0]))
            rails += [((min(xs), ys_), (ax0, ys_)), ((bx0, ys_), (max(xs), ys_))]
            for ra, rb in rails:
                if math.dist(ra, rb) < 0.1:
                    continue
                V.poly([(ra[0], ra[1], z2), (rb[0], rb[1], z2), (rb[0], rb[1], z2 + RAIL_H), (ra[0], ra[1], z2 + RAIL_H)],
                       "int_ru_picket", uvs=[(0, 0), (math.dist(ra, rb) / 1.1, 0), (math.dist(ra, rb) / 1.1, 1), (0, 1)])
                R.seg_box(V, ra, rb, 0.035, z2 + RAIL_H, z2 + RAIL_H + 0.06, "int_ru_steel", faces="sidetop")
                # rail + an invisible guard above it (no hopping off the landing onto the facades)
                R.col_seg(C, ra, rb, 0.15, z2 - 0.3, z2 + 5.2, K.COL_NOCAM)
            # the facade behind the landing (north): exterior walls / glass collide only from inside, so a solid
            # face toward the landing, open at the food court doors
            yn = max(ys) - 0.17
            ods = sorted((min(o[0], o[2]), max(o[0], o[2])) for o in e.get("open_doors", ()))
            xa_ = min(xs)
            for d0, d1 in ods + [(max(xs), max(xs))]:
                if d0 - xa_ > 0.05:
                    C.poly([(xa_, yn, z2 - 0.3), (d0, yn, z2 - 0.3), (d0, yn, z2 + 6.0), (xa_, yn, z2 + 6.0)], K.COL,
                           normal_hint=(0, -1, 0))
                xa_ = d1
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
            # destination sign over the door, on the lobby face of the wall (design pass: it sat 0.35 m inside the
            # car, behind the door header)
            xs_ = [q[0] for q in zn.poly]
            sx = (max(xs_) + WALL_T / 2 + 0.01) if facing == 90.0 else (min(xs_) - WALL_T / 2 - 0.01)
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


def wayfinding(RZ):
    """Design pass (wayfinding, ru_* signage: UF blue panels, white caps, an orange rule): on every floor a big
    floor number over each Blue elevator car (lobby face, over its destination sign) and a two-face sign hanging
    in the middle of the Blue elevator lobby naming the floor's destinations with arrows (interior_kit_reitz
    WAYFIND / int_ru_wayfind_<floor>); the stair ends carry the floor number on the atrium fascia (_balcony_edge)."""
    lobby = {}
    for (fid, kind), zn in sorted(RZ.cars.items()):
        F = RZ.floors[fid]
        c = R.centroid(zn.poly)
        xs_ = [q[0] for q in zn.poly]
        west = c[0] < -445.0
        xf = (max(xs_) + WALL_T / 2) if west else (min(xs_) - WALL_T / 2)
        lz = F.cls_at((xf + (1.0 if west else -1.0), c[1]))[1]
        zc = F.z + (lz.style["clear"] if lz is not None and lz.style else F.clear)
        zt = min(F.z + 4.85, zc - 0.35)
        zb_ = max(F.z + 3.55, zt - 1.3)
        fa, fb = (xf, c[1] - 0.65), (xf, c[1] + 0.65)
        if not west:
            fa, fb = fb, fa
        cell = FLOOR_CELL[fid]
        u0, v0 = (cell % 4) * 0.25, 1.0 - (cell // 4 + 1) * 0.5
        P = K.Prop(f"floor_number_{fid}_{kind}")
        R.panel(P.visual, fa, fb, zb_, zt, "int_ru_floor_atlas", off=0.03, u0=u0, u1=u0 + 0.25, v0=v0, v1=v0 + 0.5,
                glow=True)
        RZ.kit_add(P, fid, tag=f"floor_number_{fid}_{kind}")
        lb = lobby.setdefault(fid, {"x": [], "y": [], "zc": zc})
        lb["x"].append(xf)
        lb["y"].append(c[1])
    for fid, lb in lobby.items():
        F = RZ.floors[fid]
        xc = sum(lb["x"]) / len(lb["x"]) if len(lb["x"]) > 1 else -444.8
        yc = sum(lb["y"]) / len(lb["y"]) - 1.4      # just south of the car doors: clear of the floor numbers' view
        zc = lb["zc"]
        zt, zb_ = zc - 0.55, zc - 1.75
        P = K.Prop(f"wayfind_{fid}")
        V = P.visual
        w2 = 1.2
        # north face (int_ru_wayfind_<floor>) and south face (_s; L5 / L6: no arrows, the same texture)
        south = f"int_ru_wayfind_{fid}" if fid in ("L5", "L6") else f"int_ru_wayfind_{fid}_s"
        R.panel(V, (xc + w2, yc), (xc - w2, yc), zb_, zt, f"int_ru_wayfind_{fid}", off=0.03, glow=True)
        R.panel(V, (xc - w2, yc), (xc + w2, yc), zb_, zt, south, off=0.03, glow=True)
        R.seg_box(V, (xc - w2 - 0.02, yc), (xc + w2 + 0.02, yc), 0.045, zt, zt + 0.05, "int_ru_steel", faces="sidetop")
        R.seg_box(V, (xc - w2 - 0.02, yc), (xc + w2 + 0.02, yc), 0.045, zb_ - 0.05, zb_, "int_ru_steel",
                  faces="sideends_top")
        for xr in (xc - w2 + 0.3, xc + w2 - 0.3):
            V.box(xr - 0.012, yc - 0.012, zt + 0.05, xr + 0.012, yc + 0.012, zc, "int_ru_steel", faces="+x-x+y-y")
        RZ.kit_add(P, fid, tag=f"wayfind_{fid}")
        RZ.points.setdefault("wayfinding", {})[fid] = {"name": f"interior_wayfind_{fid}", "p": [xc, yc, F.z],
                                                       "kind": "ground"}


# ================================================================== assembly
SPAWN = {"pos_m": (-399.0, -278.5), "z_game_m": 0.0, "facing_deg": 0.0}


def build(backdrop=True, dress=True):
    lay = load_layout()
    RZ = Reitz(lay)
    EXTRA_PICKUPS.clear()
    FASCIA_NUMS.clear()
    STAIR_GAPS.clear()
    STAIR_GAPS.update(_stair_ends(RZ))
    for fid in FLOORS:
        build_floor(RZ, RZ.floors[fid])
    build_entrances(RZ)
    build_elevators(RZ)
    wayfinding(RZ)
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
        elif g in ("G", "L1"):
            # the double-height atrium floors are daylit from the clerestory and the south glazing (ru_atrium_enr_lounge
            # reads ~146 mean luminance against ~120 at the shared ambient): a brighter ambient on these two
            RZ.lighting[g] = K.Lighting(by_group[g], sky=(0.74, 0.74, 0.75), ground=(0.57, 0.56, 0.55),
                                        key=(0.45, 0.62, 0.64), key_strength=0.10)
        elif g in ("L5", "L6"):
            # fix round 4 (fidelity-4 pass, improvement 8): the hotel floors read bright white in ru_hotel_room /
            # ru_hotel_suite (the shared ambient baked their white walls a dull beige-grey)
            RZ.lighting[g] = K.Lighting(by_group[g], sky=(0.72, 0.72, 0.73), ground=(0.56, 0.55, 0.54),
                                        key=(0.45, 0.62, 0.64), key_strength=0.10)
        else:
            RZ.lighting[g] = K.Lighting(by_group[g], sky=(0.66, 0.66, 0.68), ground=(0.52, 0.51, 0.50),
                                        key=(0.45, 0.62, 0.64), key_strength=0.10)
    RZ.pickups = list(PICKUPS) + list(EXTRA_PICKUPS)
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
    {"kind": "coin_ring", "name": "grand ballroom coins", "pos": (-488.5, -252.6, 12.0)},   # open floor behind the rows
    {"kind": "coin_line", "name": "rion ballroom coins", "pos": (-440.6, -300.5, 18.0), "facing": 90.0},
    {"kind": "coin_line", "name": "esports aisle coins", "pos": (-463.6, -292.0, 0.0), "facing": 0.0},
    {"kind": "heart", "name": "hotel corridor heart", "pos": (-440.0, -274.0, 29.0)},
    {"kind": "1up", "name": "uf letters 1-up", "pos": (-411.33, -265.6, 2.95)},
    # design pass (fun): the floors that had nothing (LL, L4, L5 / L6 corridors) and L3 get a coin line each; a
    # 1-up on top of the Swamp Boss gator head (jump on it). Per-flight scissor-stair coins, the Grand Ballroom
    # stage line and the billiard-table coins are added by their builders (EXTRA_PICKUPS).
    {"kind": "coin_line", "name": "dance studio coins", "pos": (-396.2, -270.5, -6.0), "facing": 90.0},
    {"kind": "coin_line", "name": "l3 elevator lobby coins", "pos": (-444.8, -271.0, 18.0), "facing": 0.0},
    {"kind": "coin_line", "name": "arredondo cafe coins", "pos": (-432.0, -262.5, 24.0), "facing": 90.0},
    {"kind": "coin_line", "name": "l5 hotel lobby coins", "pos": (-444.8, -273.0, 29.0), "facing": 0.0},
    {"kind": "coin_line", "name": "l6 hotel lobby coins", "pos": (-444.8, -273.0, 34.0), "facing": 0.0},
    {"kind": "1up", "name": "swamp boss 1-up", "pos": (-397.3, -271.1, 0.9)},
    # fix round 4 (design pass, improvement 2): a coin ring on the L1 outdoor dining terrace (the reward for finding
    # the way out through the south hall; >= 4 m of open reachable floor all round in the reachability flood)
    # fix round 5 (technical improvement 2): the ring fell back to a 5-coin line that crossed the terrace glass (coin
    # 3 behind it, coin 4 on the unreachable terrace): a line along the south hall, wholly inside it, by the glass
    # fix round 5 (fidelity-2): the terrace opens from the south hall (TERRACE_OPEN_DOORS): the line moves out onto it,
    # down the middle of its east leg (x -420.75 .. -418.1, clear of the south leg's patio tables)
    {"kind": "coin_line", "name": "outdoor dining terrace coins", "pos": (-419.4, -326.0, 6.0), "facing": 0.0},
    # fix round 5 (design pass, improvement 4 / fun): the Arts & Crafts Center had no pickups: a coin line down its
    # east aisle (past the mural and the two studio doors) and a coin on the kiln lid (a small hop)
    {"kind": "coin_line", "name": "acc east aisle coins", "pos": (-448.6, -257.0, -6.0), "facing": 0.0},
    {"kind": "coin", "name": "acc kiln lid coin", "pos": (-457.9, -266.7, -4.92)},
    # ... and a coin line down the Game Room's east window strip (past the table games)
    {"kind": "coin_line", "name": "game room window coins", "pos": (-422.8, -309.0, 0.0), "facing": 0.0},
]
# fix round 4 (design pass, improvement 2): Goomba spots checked in the reachability flood (>= 2 m of open floor all
# round). NOT placed: build_interior.build_area (the area-module path, shared with other stages, not this module's
# to edit) has no "goomba" branch in its pickup loop, so kind "goomba" in PICKUPS would be dropped silently. Adding
# `elif k == "goomba": Pl.goomba(name, p, it.get("facing", 0.0))` there and appending these to PICKUPS places them.
GOOMBA_SPOTS = [
    {"kind": "goomba", "name": "game room goomba 1", "pos": (-423.5, -304.5, 0.0), "facing": 0.0},
    {"kind": "goomba", "name": "game room goomba 2", "pos": (-424.5, -312.5, 0.0), "facing": 180.0},
    {"kind": "goomba", "name": "ll corridor goomba", "pos": (-407.5, -272.5, -6.0), "facing": 90.0},
]
EXTRA_PICKUPS = []      # filled by the room builders during build() (stairs, Grand Ballroom stage, billiards)


POND_C = (-369.37, -335.81)            # Liberty Pond (area 1: landmarks/reitz_reitz_union.POND_C), r ~24 m


def _tree_clear(RZ, tx, ty, r, z0, z1, margin=1.0):
    """True when a tree canopy (square of half-size r, z0..z1 above Ground) keeps clear of every zone (walkable,
    sealed or void) of every floor whose storey overlaps it: no backdrop tree inside the building."""
    for F in RZ.floors.values():
        if z1 < F.z - SLAB - 0.1 or z0 > F.z + F.clear + 0.1:
            continue
        box = (tx - r - margin, ty - r - margin, tx + r + margin, ty + r + margin)
        for zn in F.zones:
            if zn.cls == "O" or not _bb_overlap(zn.bb, box):
                continue
            if R.pip((tx, ty), zn.poly) or R.poly_dist((tx, ty), zn.poly) < r + margin:
                return False
        if R.pip((tx, ty), F.outline) or R.poly_dist((tx, ty), F.outline) < r * 0.6:
            return False
    return True


AMPHI_C = (-392.5, -305.0)     # centre of the curved SE facade (the footprint's arc, r ~15 m): the amphitheater bowl


def _amphitheater(RZ, V):
    """Fix round 2 (fidelity-2; ru_os_amphitheatre, ru_dining_windows): what the curved SE glass looks out on.
    Tall oaks and a pine standing close against the curve (canopies ~7-16 m above Ground, so they fill the food-court
    glass from the sill up), the amphitheater's stepped grass terraces in the bowl the curve wraps, and the umbrella
    terrace by the South Terrace doors. Visual only (out of bounds)."""
    cx, cy = AMPHI_C
    # stepped grass terraces: ring sectors facing south-east, rising toward the facade (stage at the bottom)
    a0, a1 = math.radians(100.0), math.radians(178.0)
    nseg = 10
    for k, (r_in, r_out) in enumerate(((3.6, 5.2), (5.2, 6.8), (6.8, 8.4), (8.4, 10.0))):
        zt = 0.42 * (k + 1) - 0.12
        for i in range(nseg):
            t0 = a0 + (a1 - a0) * i / nseg
            t1 = a0 + (a1 - a0) * (i + 1) / nseg
            pi0 = (cx + r_in * math.cos(t0), cy + r_in * math.sin(t0))
            pi1 = (cx + r_in * math.cos(t1), cy + r_in * math.sin(t1))
            po0 = (cx + r_out * math.cos(t0), cy + r_out * math.sin(t0))
            po1 = (cx + r_out * math.cos(t1), cy + r_out * math.sin(t1))
            V.poly([(pi0[0], pi0[1], zt), (pi1[0], pi1[1], zt), (po1[0], po1[1], zt), (po0[0], po0[1], zt)],
                   "grass", normal_hint=(0, 0, 1), ao=1.0)
            # concrete riser facing the stage (the inner arc)
            R.quad_wall(V, pi1, pi0, -0.12, zt, "concrete", ao=0.8)
        # end caps
        for t_ in (a0, a1):
            pi = (cx + r_in * math.cos(t_), cy + r_in * math.sin(t_))
            po = (cx + r_out * math.cos(t_), cy + r_out * math.sin(t_))
            if t_ == a0:
                R.quad_wall(V, pi, po, -0.12, zt, "concrete", ao=0.8)
            else:
                R.quad_wall(V, po, pi, -0.12, zt, "concrete", ao=0.8)
    # the stage: a low concrete half-disc at the bottom of the bowl
    st = [(cx, cy)] + [(cx + 3.4 * math.cos(a0 + (a1 - a0) * i / 6), cy + 3.4 * math.sin(a0 + (a1 - a0) * i / 6))
                       for i in range(7)]
    R.floor_poly(V, R.ccw(st), 0.08, "concrete", step=9.0)
    # tall trees close against the curve (between y -325 and -282): oaks + one pine
    trees = [((-408.0, -321.5), "oak"), ((-405.2, -311.0), "pine"), ((-403.4, -301.8), "oak"),
             ((-397.4, -295.6), "oak"), ((-389.4, -293.4), "pine"), ((-410.5, -330.0), "oak")]
    # fix round 4 (fidelity-2 blocking; ru_dining_windows): the crowns sit LOWER (about 3-11 m above Ground, tops 1-5
    # m over the Level 1 floor) so the food-court glass shows treetops from the sill up to ~2/3 of its height with
    # sky above (they ran 6.8-17 m: canopy above the window head, open lawn and trunks below), plus an understory
    # of lower crowns between the trunks
    placed = []
    for k, ((tx, ty), kind) in enumerate(trees):
        if kind == "oak":
            r1 = 3.4 + (k % 2) * 0.5
            if not _tree_clear(RZ, tx, ty, r1, 3.0, 11.2, margin=0.4):
                r1 = 2.6
                if not _tree_clear(RZ, tx, ty, r1, 3.0, 11.2, margin=0.3):
                    continue
            R.cyl(V, tx, ty, 0.42, -0.15, 5.0, "bark", n=6, top=False)
            # fix round 4 (fidelity-2 pass): the dense crown tops at 2.6-3.2 m over the L1 floor (~55-60% of the
            # glass, sky above it as in ru_dining_windows; they reached 5 m, ~95% of the glass), a smaller,
            # irregular top tier above
            zt = 8.6 + 0.6 * (k % 2)
            # fix round 5 (fidelity-2; ru_dining_windows: separate rounded crowns with sky between them, not one
            # flat-topped hedge): a lower body to 1.4 m under the old top, then three staggered crown lumps whose
            # tops vary by ~1.3 m (no side face on another's plane)
            # (round 5 iteration: the body narrower (0.8 r1) and lower, each tree's crown height varied, lumps
            # spread over ~2 m: the first pass still read as one level band in the matched 'dining' view)
            zt += (0.0, 0.9, -0.5, 0.5, -0.2, 0.7)[k % 6]
            rb = r1 * 0.8
            V.box(tx - rb, ty - rb, 3.4, tx + rb, ty + rb, zt - 2.0, "leaves_oak", faces="+x-x+y-y+z-z")
            sg = 1 if k % 2 else -1
            for (ox, oy, hu, top, mat, bot) in ((-0.38 * sg, -0.3, 0.52, zt + 0.2, "leaves_oak", 2.3),
                                                (0.42 * sg, 0.34, 0.44, zt - 1.0, "leaves_oak2", 2.4),
                                                (0.18 * sg, -0.52, 0.34, zt + 0.9, "leaves_oak2", 2.5)):
                # closed lumps (they overhang the narrower body), each bottom at its own height (no shared plane)
                cx_, cy_ = tx + ox * r1, ty + oy * r1
                V.box(cx_ - hu * r1, cy_ - hu * r1 * 0.9, zt - bot, cx_ + hu * r1, cy_ + hu * r1 * 0.9, top, mat,
                      faces="+x-x+y-y+z-z")
            placed.append((tx, ty))
        else:
            if not _tree_clear(RZ, tx, ty, 2.8, 3.0, 12.4, margin=0.3):
                continue
            R.cyl(V, tx, ty, 0.3, -0.15, 10.4, "bark", n=6, top=False)
            for (zb, zt_, rr) in ((3.6, 6.6, 2.8), (6.6, 8.4, 2.1), (8.4, 9.6, 1.4), (9.6, 10.6, 0.7)):
                V.box(tx - rr, ty - rr, zb, tx + rr, ty + rr, zt_, "leaves_pine", faces="+x-x+y-y+z-z")
            placed.append((tx, ty))
    for (ax_, ay_), (bx_, by_) in zip(placed, placed[1:]):
        ux_, uy_ = (ax_ + bx_) / 2, (ay_ + by_) / 2
        if math.dist((ax_, ay_), (bx_, by_)) < 4.0 or not _tree_clear(RZ, ux_, uy_, 2.0, 2.0, 7.8, margin=0.3):
            continue
        R.cyl(V, ux_, uy_, 0.22, -0.15, 3.0, "bark", n=5, top=False)
        # fix round 5 (fidelity-2): the understory lower and narrower (its 7.6 m top bridged the crowns into a hedge)
        V.box(ux_ - 1.6, uy_ - 1.6, 2.4, ux_ + 1.6, uy_ + 1.6, 6.9, "leaves_oak2", faces="+x-x+y-y+z-z")
    # umbrella terrace (South Terrace, east of the bowl): round tables under navy umbrellas
    for (ux, uy) in ((-386.6, -293.6), (-382.0, -292.8), (-377.4, -293.2), (-384.4, -297.6), (-379.6, -297.4)):
        R.cyl(V, ux, uy, 0.55, -0.12, 0.74, "int_ru_white", n=8)
        R.cyl(V, ux, uy, 0.04, 0.74, 2.5, "int_ru_steel", n=4, top=False)
        apex = (ux, uy, 2.85)
        ring = [(ux + 1.4 * math.cos(2 * math.pi * i / 8), uy + 1.4 * math.sin(2 * math.pi * i / 8)) for i in range(8)]
        for i in range(8):
            p0, p1 = ring[i], ring[(i + 1) % 8]
            V.poly([(p0[0], p0[1], 2.3), (p1[0], p1[1], 2.3), apex], "int_ru_fabric_navy", ao=1.0)
            V.poly([apex, (p1[0], p1[1], 2.3), (p0[0], p0[1], 2.3)], "int_ru_fabric_navy", ao=0.8)


TERRACE_TABLES = ((-427.6, -336.15), (-424.4, -336.15), (-421.3, -336.15))   # the south leg's patio tables


def _terrace_dress(RZ, F, zn, P):
    """fix round 5 (fidelity-2; ru_south_terrace_seating): the Level 1 outdoor dining terrace, entered from the south
    hall through its west door (TERRACE_OPEN_DOORS). Collision on the terrace side of the glass walls it shares with
    the hall and corridor 03 (their walls faced the hall only: once in, Mario would walk out through the glass) on the
    inset outline (the facade faces' plane), the doorway cut out; black metal patio tables with attached seats along
    the south leg (the photo's covered-terrace seating)."""
    z = F.z
    poly = R.ccw(zn.poly)
    t = EXT_T / 2
    ins = _inset_ortho(poly, t)
    for i in range(len(poly)):
        pa, pb = poly[i], poly[(i + 1) % len(poly)]
        L = math.dist(pa, pb)
        if L < 0.3:
            continue
        mid = ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)
        out_pt = (mid[0] + (pb[1] - pa[1]) / L * 0.4, mid[1] - (pb[0] - pa[0]) / L * 0.4)
        if F.cls_at(out_pt)[0] not in ("W", "S"):
            continue                      # the open east edge keeps its rail guard (build_backdrop)
        a_, b_ = ins[(i + 1) % len(ins)], ins[i]          # reversed: the normal (right of a_ -> b_) faces in
        La = math.dist(a_, b_)
        ux, uy = (b_[0] - a_[0]) / La, (b_[1] - a_[1]) / La
        holes = []
        for od in TERRACE_OPEN_DOORS:
            if R.seg_point_dist(((od[0] + od[2]) / 2, (od[1] + od[3]) / 2), pa, pb) < 0.6:
                s0 = (od[0] - a_[0]) * ux + (od[1] - a_[1]) * uy
                s1 = (od[2] - a_[0]) * ux + (od[3] - a_[1]) * uy
                holes.append((min(s0, s1), max(s0, s1), z - 1.0, z + GLASS_DOOR_H))
        col_face(P.collision, a_, b_, z, z + 4.2, holes=holes, mat=K.COL_NOCAM)
    for k, (tx, ty) in enumerate(TERRACE_TABLES):
        RZ.kit_add(R.patio_table(rot=math.radians(20.0 * (k % 2))), "L1", tag=f"terrace_table_{k}", x=tx, y=ty, z=z)


def build_backdrop(RZ):
    """Outside the glass (visual only): the main roof (minus the tower, whose L4 floor sits at the same height), the
    grade around the building (paving apron + lawn at Ground, the North Lawn plaza at Level 1 by the north entrance),
    the Level 1 outdoor walkway + outdoor dining slabs with their canopy and rail (they roof the Ground rooms under
    them: Gator Esports), Liberty Pond with the oaks round it, and a tree line all round."""
    P = K.Prop("backdrop")
    V = P.visual
    fp = RZ.footprint
    # main roof over the L3 outline, the tower (L4 outline) cut out
    l4 = RZ.floors["L4"].outline
    R.floor_poly(V, fp, ROOF_Z["main"], "roof_gravel", step=12.0, cut=[R.ccw(t) for t in R.triangulate(l4)])
    # grade: paving apron (the South Terrace and the walks) round the building, lawn beyond, the pond cut out
    hull = R.ccw(R.convex_hull(fp))
    apron = R.ccw(R.offset_poly(hull, 9.0))
    lawn = R.ccw(R.offset_poly(hull, 75.0))
    pond = [(POND_C[0] + 23.5 * math.cos(2 * math.pi * k / 16), POND_C[1] + 23.5 * math.sin(2 * math.pi * k / 16))
            for k in range(16)]
    # fix round 4 (technical blocking): the apron's hole is the Ground outline, not the roof footprint: the upper
    # floors' overhangs (west wing, food court, Game Room, South Terrace) left sky below the grade line through the
    # Ground glazing (71 of 376 rays from inside the Ground / LL glass hit nothing)
    R.floor_poly(V, apron, -0.12, "sidewalk", step=8.0, holes=[RZ.floors["G"].outline], cut=[pond])
    R.floor_poly(V, lawn, -0.15, "grass", step=16.0, holes=[apron], cut=[pond])
    R.floor_poly(V, pond, -0.45, "water", step=12.0)
    R.floor_poly(V, pond, -1.10, "asphalt", step=12.0)        # the pond bed: no sky through the translucent water
    for pa, pb in R.edges(R.ccw(pond)):
        R.quad_wall(V, pb, pa, -1.10, -0.12, "concrete", ao=0.8)
    # North Lawn plaza at Level 1 in front of the north entrance (the 2016 wing's north doors are at grade there)
    # (it follows the Level 1 outline: the rooms west of the recess' diagonal wall are building, not plaza)
    plaza = R.ccw([(-366.0, -257.9), (-366.0, -236.0), (-411.0, -236.0), (-411.0, -243.7), (-397.6, -244.4),
                   (-393.0, -257.3)])
    R.floor_poly(V, plaza, 5.88, "sidewalk", step=6.0)
    for pa, pb in R.edges(plaza):
        if min(pa[1], pb[1]) > -257.0 or abs(pa[0] - pb[0]) < 0.01:
            R.quad_wall(V, pa, pb, -0.15, 5.88, "concrete", ao=0.85)
    # the 2016 north entrance recess under the wing's overhang (area 1: landmarks/reitz_reitz_union RECESS /
    # NORTH_COLS, +6 m since area 1's Level 1 grade is 0), clipped to the open part of area 2's Level 1 outline
    # (the diagonal room wall (-393.0, -257.3) -> (-397.6, -244.4) on the west): the white soffit at the Level 2 slab
    # underside (11.4) with linear lights, three white columns along the overhang edge, the east side wall and the
    # fascia at the face (ru_north_entrance_hotelsite, ru_north_entrance_enr_dusk). Visual only: the warp strip is
    # the way out.
    rx1, ryf, rzs = -370.9, -243.6, 11.4
    diag_a, diag_b = (-393.0, -257.3), (-397.6, -244.4)
    soffit = R.ccw([diag_a, (rx1, -257.95), (rx1, ryf), (-397.3, ryf), diag_b])
    R.floor_poly(V, soffit, rzs, "int_ru_white", step=6.0, down=True)
    for ly in (-255.6, -251.6, -247.6):
        xd = diag_a[0] + (ly - diag_a[1]) / (diag_b[1] - diag_a[1]) * (diag_b[0] - diag_a[0])
        lx0 = xd + 1.0
        while lx0 + 2.0 < rx1 - 0.8:
            lx1 = min(lx0 + 4.4, rx1 - 0.8)
            V.poly([(lx0, ly + 0.07, rzs - 0.01), (lx1, ly + 0.07, rzs - 0.01), (lx1, ly - 0.07, rzs - 0.01),
                    (lx0, ly - 0.07, rzs - 0.01)], "int_ru_led", glow=True, normal_hint=(0, 0, -1))
            lx0 = lx1 + 1.8
    R.quad_wall(V, (-397.3, ryf), (rx1, ryf), rzs - 0.45, rzs, "int_ru_white", ao=0.9)          # fascia, inner face
    R.quad_wall(V, (rx1, ryf - 0.12), (-397.3, ryf - 0.12), rzs - 0.45, rzs + 0.6, "int_ru_white", ao=0.95)
    R.quad_wall(V, (rx1, ryf), (rx1, -257.95), 5.88, rzs, "int_ru_white", ao=0.85)              # east side wall
    for cx in (-394.0, -385.5, -377.0):
        R.cyl(V, cx, ryf - 0.75, 0.35, 5.88, rzs, "int_ru_white", n=8, top=False)
    # Level 1 outdoor walkway (west) + outdoor dining (south): concrete slab, soffit, canopy, rail
    F1 = RZ.floors["L1"]
    for zn in F1.zones:
        if zn.cls != "O" or zn.type != "exterior_walkway":
            continue
        z = F1.z
        R.floor_poly(V, zn.poly, z - 0.04, "sidewalk", step=6.0)
        if zn.id == "outdoor_dining_area":
            # fix round 4 (fidelity-2 blocking): the terrace is reachable from the south hall (open at x -431.1): a
            # collision floor on the whole paving (only the strip under l1_corridor_08's cells was floor: an
            # invisible wall 2 m short of the rail for 15 m)
            for t_ in R.triangulate(zn.poly):
                P.collision.poly([(x, y, z) for x, y in R.ccw(t_)], K.COL)
            _terrace_dress(RZ, F1, zn, P)
        # the slab's underside is cut where it roofs Ground rooms (Gator Esports): their own ceilings sit at the same
        # 5.4 m, and the coplanar soffit z-fought with the black esports ceiling (fidelity pass 3)
        under = [pc for o in RZ.floors["G"].walk_zones() if _bb_overlap(o.bb, R.bbox(zn.poly))
                 for pc in _convex_parts(o.poly)]
        R.floor_poly(V, zn.poly, z - SLAB, "int_ru_white", step=9.0, down=True, cut=under)
        R.floor_poly(V, zn.poly, z + 4.2, "int_ru_white", step=9.0, down=True)
        R.floor_poly(V, zn.poly, z + 4.4, "roof_gravel", step=9.0)
        for pa, pb in R.edges(R.ccw(zn.poly)):
            L = math.dist(pa, pb)
            if L < 0.05:
                continue
            mid = ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)
            out_pt = (mid[0] + (pb[1] - pa[1]) / L * 0.4, mid[1] - (pb[0] - pa[0]) / L * 0.4)
            oz = F1.zone_at(out_pt)
            if oz is not None and oz.cls in ("W", "S"):
                continue
            if zn.id == "outdoor_dining_area" and L > 0.3:
                # fix round 4 (fidelity-2 blocking): an invisible guard on the terrace's outer edge, up to the canopy
                # (no hopping the rail into the visual-only grade), facing the terrace
                P.collision.poly([(pb[0], pb[1], z - 0.2), (pa[0], pa[1], z - 0.2), (pa[0], pa[1], z + 4.2),
                                  (pb[0], pb[1], z + 4.2)], K.COL_NOCAM)
            # outer edges: slab band, canopy fascia, a picket rail
            R.quad_wall(V, pa, pb, z - SLAB, z, "int_ru_white", ao=0.9)
            R.quad_wall(V, pb, pa, z - SLAB, z, "int_ru_white", ao=0.9)
            R.quad_wall(V, pa, pb, z + 4.2, z + 4.4, "int_ru_white", ao=0.9)
            R.quad_wall(V, pb, pa, z + 4.2, z + 4.4, "int_ru_white", ao=0.9)
            L = math.dist(pa, pb)
            if L > 0.5:
                V.poly([(pa[0], pa[1], z), (pb[0], pb[1], z), (pb[0], pb[1], z + RAIL_H), (pa[0], pa[1], z + RAIL_H)],
                       "int_ru_picket", uvs=[(0, 0), (L / 1.1, 0), (L / 1.1, 1), (0, 1)])
            # canopy piers (fidelity pass 2): square white piers on the outer edge, <= 6.5 m apart, so the west
            # glass of the food court looks out on the covered walkway to the Bookstore
            if L > 3.0:
                n_p = int(math.ceil(L / 6.5))
                ux, uy = (pb[0] - pa[0]) / L, (pb[1] - pa[1]) / L
                inx, iny = -uy, ux              # left of pa -> pb on a CCW zone: into the walkway
                for k in range(n_p + 1):
                    if k == 0 and L < 6.0:
                        continue
                    px = pa[0] + ux * L * k / n_p + inx * 0.35
                    py = pa[1] + uy * L * k / n_p + iny * 0.35
                    V.box(px - 0.22, py - 0.22, z, px + 0.22, py + 0.22, z + 4.2, "int_ru_white", faces="+x-x+y-y")
        # fidelity-2: the free-standing glass door pair that stood 0.4 m outside the walkway's west slab edge
        # (doors_m (-463.0, -329.8)-(-463.1, -334.0)) is gone: it sat behind the full-length rail, 6 m above the
        # lawn, with nothing behind it, and the UF Bookstore is SOUTH of the walkway (zone x -454.8..-418.3,
        # y -415..-357, at the end of its south leg), not west. The plan door stays listed in the layout data.
    # oaks round Liberty Pond and along the South Terrace (low-poly: trunk + two canopy blocks)
    trees = [(POND_C[0] + 31.0 * math.cos(math.radians(a_)), POND_C[1] + 31.0 * math.sin(math.radians(a_)))
             for a_ in range(0, 360, 30)]
    trees += [(-412.0, -346.0), (-398.0, -350.0), (-352.0, -300.0), (-345.0, -282.0), (-350.0, -262.0),
              (-430.0, -350.0), (-445.0, -352.0)]
    fp_big = R.offset_poly(hull, 4.0)
    for k, (tx, ty) in enumerate(trees):
        if R.pip((tx, ty), fp_big):
            continue
        # fix round 2 (blocking): the OSM footprint hull misses the Level 1 hall south of the food court (to y -357):
        # two 'South Terrace' oaks stood inside it. Every tree is now checked against the zones of every floor.
        if not _tree_clear(RZ, tx, ty, 4.4, -0.2, 9.0):
            continue
        h = 5.0 + (k % 3) * 0.8
        R.cyl(V, tx, ty, 0.35, -0.15, h, "bark", n=6, top=False)
        r1 = 3.4 + (k % 2) * 0.6
        V.box(tx - r1, ty - r1, h - 0.6, tx + r1, ty + r1, h + 2.4, "leaves_oak", faces="+x-x+y-y+z-z")
        V.box(tx - r1 * 0.6, ty - r1 * 0.6, h + 2.4, tx + r1 * 0.6, ty + r1 * 0.6, h + 3.8, "leaves_oak",
              faces="+x-x+y-y+z")
    _amphitheater(RZ, V)
    # tree line all round (a wall of trees through every window, ru_dining_windows)
    ring = R.ccw(R.offset_poly(hull, 70.0))
    for pa, pb in R.edges(ring):
        R.quad_wall(V, pb, pa, -0.15, 18.0, "treeline", ao=1.0)
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
    # meeting-room furniture (rows, drapes, classroom / U / boardroom tables) must sit inside its own room: fail when
    # more than 5 % of a set's visual vertices fall outside the zone (fidelity review r1: 18 sets were outside)
    zones = {zn.id: zn for F in M.floors.values() for zn in F.zones}
    worst = []
    for t, g, p in M.kit.items:
        pre = next((q for q in ("rows_", "drape_", "class_", "u_", "board_") if t.startswith(q)), None)
        if pre is None:
            continue
        rest = t[len(pre):]
        zid = max((z for z in zones if rest == z or rest.startswith(z + "_")), key=len, default=None)
        if zid is None:
            continue
        poly = R.offset_poly(zones[zid].poly, 0.05)
        pts = [q for pl in p.visual.polys for q in pl.pts]
        if not pts:
            continue
        out = sum(1 for q in pts if not R.pip((q[0], q[1]), poly)) / len(pts)
        worst.append((out, t))
        if out > 0.05:
            probs.append((t, f"{out:.0%} of its vertices outside {zid}"))
    worst.sort(reverse=True)
    print(f"   room furniture: {len(worst)} sets, worst outside share "
          f"{', '.join(f'{t} {o:.1%}' for o, t in worst[:3]) or 'none'}")
    print("problems:", probs[:10] or "none")
    return probs



# ================================================================== the atrium (2016 wing): G lounge, voids L1-L3
# the plan's stair chevron (L1-L3 voids): tip, outer arm ends, inner tip (map m)
CHEVRON = {"tip": (-401.2, -271.3), "ne": (-395.6, -265.7), "se": (-397.3, -275.3), "inner": (-398.6, -271.3)}
STAIR_W = 1.8
LANDING_ALONG = 2.2
STAIR_STRINGER = 0.24                  # design pass: white stringer depth under the treads (kit default 0.35)
LANDING_T = 0.22                       # ... landing slab thickness (was 0.35)


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
        # design pass: slimmer stringers (0.24 m, was 0.35) so the flights read light (ru_atrium_hdr_flickr)
        f1 = R.stair_flight(V, C, a_se, b_se, z0, zl, STAIR_W, stringer=STAIR_STRINGER)
        f2 = R.stair_flight(V, C, a_ne, b_ne, zl, z1, STAIR_W, stringer=STAIR_STRINGER)
        # a coin trail up both flights (design pass: landing to landing; the landing coins are in PICKUPS)
        for nm, pa_, pb_, za, zb_ in (("se", a_se, b_se, z0, zl), ("ne", a_ne, b_ne, zl, z1)):
            for t_ in (0.3, 0.7):
                EXTRA_PICKUPS.append({"kind": "coin", "name": f"atrium stair {lo} {nm} coin {int(t_ * 10)}",
                                      "pos": (pa_[0] + (pb_[0] - pa_[0]) * t_, pa_[1] + (pb_[1] - pa_[1]) * t_,
                                              za + (zb_ - za) * t_)})
        # landing: hull of the first LANDING_ALONG metres of both arms
        pts = [tip]
        for d_, n_ in ((dne, nne), (dse, nse)):
            pts.append((tip[0] + d_[0] * (s_land + 0.05), tip[1] + d_[1] * (s_land + 0.05)))
            pts.append((tip[0] + d_[0] * (s_land + 0.05) + n_[0] * STAIR_W, tip[1] + d_[1] * (s_land + 0.05) + n_[1] * STAIR_W))
        land = R.ccw(R.convex_hull(pts))
        R.floor_poly(V, land, zl, "int_ru_terrazzo", step=99.0)
        R.floor_poly(V, land, zl - LANDING_T, "int_ru_white", step=99.0, down=True)
        for pa, pb in R.edges(land):
            R.quad_wall(V, pb, pa, zl - LANDING_T, zl + 0.02, "int_ru_white", ao=0.9)
            R.quad_wall(V, pa, pb, zl - LANDING_T, zl, "int_ru_white", ao=0.9)
        R.col_floor(C, R.offset_poly(land, 0.08), zl)
        # landing rail on the open (west) sides
        tipo = (tip[0] - (dne[0] + dse[0]) * 0.05, tip[1] - (dne[1] + dse[1]) * 0.05)
        for d_ in (dne, dse):
            ra, rb = tipo, (tip[0] + d_[0] * s_land, tip[1] + d_[1] * s_land)
            V.poly([(ra[0], ra[1], zl), (rb[0], rb[1], zl), (rb[0], rb[1], zl + RAIL_H), (ra[0], ra[1], zl + RAIL_H)],
                   "int_ru_picket", uvs=[(0, 0), (math.dist(ra, rb) / 1.1, 0), (math.dist(ra, rb) / 1.1, 1), (0, 1)])
            R.seg_box(V, ra, rb, 0.035, zl + RAIL_H, zl + RAIL_H + 0.06, "int_ru_steel", faces="sidetop")
            R.col_seg(C, ra, rb, 0.12, zl, zl + RAIL_H + 0.06, K.COL_NOCAM)
        # fix round 2 (blocking): the landing's inner (east) edge between the two flights is railed too (it was open:
        # a 3 / 9 / 15 m fall beside the landing coins)
        sl = s_land + 0.05
        ne_in = (tip[0] + dne[0] * sl + nne[0] * STAIR_W, tip[1] + dne[1] * sl + nne[1] * STAIR_W)
        se_in = (tip[0] + dse[0] * sl + nse[0] * STAIR_W, tip[1] + dse[1] * sl + nse[1] * STAIR_W)
        toward = _unit2(((ne_in[0] + se_in[0]) / 2, (ne_in[1] + se_in[1]) / 2), tip)
        ra = (ne_in[0] + toward[0] * 0.06, ne_in[1] + toward[1] * 0.06)
        rb = (se_in[0] + toward[0] * 0.06, se_in[1] + toward[1] * 0.06)
        Lr = math.dist(ra, rb)
        V.poly([(ra[0], ra[1], zl), (rb[0], rb[1], zl), (rb[0], rb[1], zl + RAIL_H), (ra[0], ra[1], zl + RAIL_H)],
               "int_ru_picket", uvs=[(0, 0), (Lr / 1.1, 0), (Lr / 1.1, 1), (0, 1)])
        R.seg_box(V, ra, rb, 0.035, zl + RAIL_H, zl + RAIL_H + 0.06, "int_ru_steel", faces="sidetop")
        R.col_seg(C, ra, rb, 0.12, zl, zl + RAIL_H + 0.06, K.COL_NOCAM)
        # ... and each flight's inner rail line continues 0.45 m back over the landing (collision only, facing the
        # landing): no wedge at the corner where the short inner rail meets the flights' rails
        for d_, n_ in ((dne, nne), (dse, nse)):
            q0 = (tip[0] + d_[0] * (s_land - 0.45) + n_[0] * 1.75, tip[1] + d_[1] * (s_land - 0.45) + n_[1] * 1.75)
            q1 = (tip[0] + d_[0] * (s_land + 0.1) + n_[0] * 1.75, tip[1] + d_[1] * (s_land + 0.1) + n_[1] * 1.75)
            C.poly([(q0[0], q0[1], zl - 0.3), (q1[0], q1[1], zl - 0.3), (q1[0], q1[1], zl + RAIL_H + 0.06),
                    (q0[0], q0[1], zl + RAIL_H + 0.06)], K.COL_NOCAM, normal_hint=(-n_[0], -n_[1], 0))
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
        # the clerestory reads as a dark glazed ring under the cedar lens (ru_atrium_enr_vertical,
        # ru_atrium_hdr_flickr): glass with dark mullions on every long side, a white sill
        if math.dist(a, b) > 1.0 and min(a[0], b[0]) > max(p_[0] for p_ in void) - 0.6:
            R.quad_wall(V, b, a, z0, z1, "int_ru_metal_panel", ao=0.85)     # fix round 4: behind the east bulkhead
        elif math.dist(a, b) > 1.0:
            R.quad_wall(V, b, a, z0, z0 + 0.3, "int_ru_white")
            R.quad_wall(V, b, a, z0 + 0.3, z1 - 0.2, "int_ru_glass")
            mullions(V, b, a, z0 + 0.3, z1 - 0.2, bay=1.6, mat="int_ru_slat_dark", t=0.06)
            R.quad_wall(V, b, a, z1 - 0.2, z1, "int_ru_slat_dark")
        else:
            R.quad_wall(V, b, a, z0, z1, "int_ru_white", ao=0.9)
        R.quad_wall(V, a, b, z0, z1 + 0.6, "int_ru_white")
        C.poly([(b[0], b[1], z0), (a[0], a[1], z0), (a[0], a[1], z1), (b[0], b[1], z1)], K.COL)
    # cedar vault (ru_atrium_enr_vertical, ru_atrium_hdr_flickr): a lens-shaped barrel rising VAULT_RISE along the
    # long (x) axis, built as a cell grid so the curve shows; three long dark ribs sweep along it, hanging below
    # the cedar; a dark band rings the top of the clerestory
    xs = [p[0] for p in void]
    x0, x1 = min(xs), max(xs)
    ys = [p[1] for p in void]
    yc = (min(ys) + max(ys)) / 2

    def _half_w(x):
        seg = R.clip_convex(void, x - 0.02, -400.0, x + 0.02, 0.0)
        if not seg:
            return 0.5, yc
        ya, yb = min(p[1] for p in seg), max(p[1] for p in seg)
        return max(0.5, (yb - ya) / 2), (ya + yb) / 2

    # fix round 4 (fidelity-1 blocking; ru_atrium_enr_vertical, ru_atrium_hdr_flickr, ru_atrium_construction_2015):
    # the cedar spans the void WALL TO WALL between the dark clerestory bands (it was a pointed 'football' lens over
    # 61 % of the void with white corner soffits): the cross-section still rises VAULT_RISE along the crown, the long
    # section stays near full height and only eases down at the west end wall; two long dark ribs sweep along it and
    # bow APART toward the east; the cedar ends against a convex silver metal-panel bulkhead across the east end
    # (dropping to the L3 ceiling line over the stair landings, a row of small downlights along its lower edge).
    # No lens lip, no white corners, no drum pendants (none in enr_vertical at that storey).
    BULGE = 1.8
    xe = x1 - 0.05

    def _lb(x):
        return max(0.3, _half_w(x)[0] - 0.01)

    def _ly(x):
        return _half_w(x)[1]

    def _lz(x, v):
        t_ = max(0.0, min(1.0, (x - x0) / max(1e-3, xe - x0)))
        ease = math.sqrt(max(0.0, 1.0 - (1.0 - t_) ** 6))        # 0 at the west end wall, ~1 from a third along
        return z1 + VAULT_RISE * (1.0 - v * v) * ease
    nx_, nv_ = 28, 10
    gx = [x0 + 0.01 + (xe - x0 - 0.01) * i / nx_ for i in range(nx_ + 1)]
    gv = [-1.0 + 2.0 * j / nv_ for j in range(nv_ + 1)]

    def _lp(x, v):
        return (x, _ly(x) + v * _lb(x), _lz(x, v))
    for i in range(nx_):
        for j in range(nv_):
            q = [_lp(gx[i], gv[j]), _lp(gx[i + 1], gv[j]), _lp(gx[i + 1], gv[j + 1]), _lp(gx[i], gv[j + 1])]
            V.poly([q[0], q[1], q[2]], "int_ru_cedar", normal_hint=(0, 0, -1), ao=0.95)
            V.poly([q[0], q[2], q[3]], "int_ru_cedar", normal_hint=(0, 0, -1), ao=0.95)
    for sgn in (-1, 1):
        prev = None
        for k in range(29):
            x = x0 + 0.6 + (xe - BULGE * 0.72 - x0 - 0.6) * k / 28     # fix round 5: ribs run into the full-width drum
            s_ = (x - x0) / max(1e-3, xe - x0)
            frac = sgn * (0.16 + 0.42 * s_ ** 1.3)
            cur = (x, _ly(x) + frac * _lb(x), _lz(x, frac) - 0.14)
            if prev is not None:
                d = _unit2(prev[:2], cur[:2])
                ox, oy = -d[1] * 0.14, d[0] * 0.14
                V.poly([(prev[0] - ox, prev[1] - oy, prev[2]), (cur[0] - ox, cur[1] - oy, cur[2]),
                        (cur[0] + ox, cur[1] + oy, cur[2]), (prev[0] + ox, prev[1] + oy, prev[2])], "int_ru_slat_dark",
                       normal_hint=(0, 0, -1), ao=0.8)
                for sg in (-1, 1):
                    V.poly([(prev[0] + sg * ox, prev[1] + sg * oy, prev[2]), (cur[0] + sg * ox, cur[1] + sg * oy, cur[2]),
                            (cur[0] + sg * ox, cur[1] + sg * oy, cur[2] + 0.18),
                            (prev[0] + sg * ox, prev[1] + sg * oy, prev[2] + 0.18)],
                           "int_ru_slat_dark", normal_hint=(sg * -d[1], sg * d[0], 0), ao=0.7)
            prev = cur
    # dark clerestory head band (all round, just under the cedar edge)
    for a, b in R.edges(void):
        if math.dist(a, b) > 0.3:
            ia = (a[0] + (R.centroid(void)[0] - a[0]) * 0.004, a[1] + (R.centroid(void)[1] - a[1]) * 0.004)
            ib = (b[0] + (R.centroid(void)[0] - b[0]) * 0.004, b[1] + (R.centroid(void)[1] - b[1]) * 0.004)
            R.quad_wall(V, ib, ia, z1 - 0.5, z1 + 0.02, "int_ru_slat_dark", ao=0.8)
    # the east bulkhead: a half-sine in plan bulging BULGE m into the void, silver grid-seamed panels from the L3
    # ceiling line (z0) to above the crown, a flat panel soffit under it with a row of small downlights
    # fix round 5 (fidelity-1 blocking; ru_atrium_hdr_flickr, ru_atrium_construction_2015, ru_atrium_enr_vertical):
    # the drum spans the WHOLE east end of the void (it was sized from a slice at the slanted tip, so it covered only
    # the SE corner, 3.4 m, beside a flat panel band). ya_..yb_ = the void's full y extent over its last 1.5 m; the
    # arc's back edge follows the void's own east boundary (so its ends meet the end corners) and bulges BULGE into
    # the void at mid-width. The soffit stops exactly on the void edge (no overlap with the L3 ceiling tiles).
    eseg = R.clip_convex(void, x1 - 1.5, -400.0, x1 + 0.1, 0.0)
    ya_, yb_ = min(p[1] for p in eseg) + 0.01, max(p[1] for p in eseg) - 0.01

    def _xb(y):
        s_ = R.clip_convex(void, x1 - 3.0, y - 0.005, x1 + 0.1, y + 0.005)
        return max(p[0] for p in s_) if s_ else x1 - 1.5
    nb = 16
    ys_ = sorted(set([round(ya_ + (yb_ - ya_) * u / nb, 4) for u in range(nb + 1)]
                     + [p[1] for p in void if p[0] > x1 - 1.5 and ya_ < p[1] < yb_]))
    back = [(_xb(y), y) for y in ys_]
    arc = [(bx_ - BULGE * math.sin(math.pi * (y - ya_) / (yb_ - ya_)), y) for bx_, y in back]
    zt = z1 + VAULT_RISE + 0.3
    cen = R.centroid(void)
    for pa, pb in zip(arc, arc[1:]):
        mx_, my_ = (pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2
        nh = (cen[0] - mx_, cen[1] - my_, 0.0)
        Lh = math.hypot(nh[0], nh[1])
        V.poly([(pa[0], pa[1], z0), (pb[0], pb[1], z0), (pb[0], pb[1], zt), (pa[0], pa[1], zt)], "int_ru_metal_panel",
               normal_hint=(nh[0] / Lh, nh[1] / Lh, 0.0), ao=0.9)
    soff = R.ccw(list(arc) + list(reversed(back)))
    R.floor_poly(V, R.clean(soff, 0.01, 0.0), z0, "int_ru_metal_panel", step=3.0, down=True, ao=0.85)
    for u in range(2, nb - 1):
        by = ya_ + (yb_ - ya_) * u / nb
        bx = _xb(by) - BULGE * math.sin(math.pi * u / nb) + 0.35
        V.poly([(bx - 0.09, by - 0.09, z0 - 0.015), (bx + 0.09, by - 0.09, z0 - 0.015), (bx + 0.09, by + 0.09, z0 - 0.015),
                (bx - 0.09, by + 0.09, z0 - 0.015)], "int_ru_led", glow=True, normal_hint=(0, 0, -1))
    # the atrium's warm downlight (the old pendants' light, now from the vault and the bulkhead row)
    for (px, py) in ((-408.0, -270.5), (-402.5, -268.0), (-405.5, -273.5)):
        P.lights.append(K.Light((px, py, 21.0), radius=14.0, strength=0.30, color=LIGHT_WARM))
    C.poly([(p[0], p[1], z1) for p in reversed(void)], K.COL)
    RZ.kit_add(P, "L3", tag="atrium_top")


def _inset_ortho(poly, d):
    """fix round 4 (design pass): a CCW axis-aligned (orthogonal) polygon inset by d: each vertex moves d along both
    adjacent edges' inward normals (exact for convex and reflex right-angle corners)."""
    n = len(poly)
    out = []
    for i in range(n):
        p0, p1, p2 = poly[i - 1], poly[i], poly[(i + 1) % n]
        def nin(a_, b_):
            L_ = math.dist(a_, b_)
            return (-(b_[1] - a_[1]) / L_, (b_[0] - a_[0]) / L_)       # left of a -> b (CCW: inside)
        n1, n2 = nin(p0, p1), nin(p1, p2)
        out.append((round(p1[0] + d * (n1[0] + n2[0]), 4), round(p1[1] + d * (n1[1] + n2[1]), 4)))
    return out


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
    # rug 1 fills the west void's floor (ru_atrium_enr_lounge: one large dark-navy carpet under ~10 clusters), but
    # stops 2 m short of the UF letters (ru_atrium_uf_letters_flickr / _wall: open terrazzo in front of them)
    rugs = [[(-413.2, -275.1), (-402.6, -275.6), (-402.6, -267.5), (-413.2, -267.5)],
            # fix round 4 (fidelity-1): rug 2 runs east across the east void's empty terrazzo (x -385 .. -378.2) under
            # four more lounge groups (ru_atrium_enr_lounge: furniture fills the floor)
            [(-392.6, -281.8), (-378.2, -281.8), (-378.2, -270.6), (-384.6, -270.6), (-384.6, -275.2),
             (-391.0, -275.2)]]
    for rug in rugs:
        # fix round 4 (design pass, improvement 9): seen at a grazing angle from the South Terrace arrival the blue
        # zigzag field read as a pool of water: a dark 0.3 m border band around each rug (the field is the rug
        # inset by 0.3 m, the band is the ring between: both at the overlay height, side by side, no overlap)
        outer = R.ccw(rug)
        inner = _inset_ortho(outer, 0.3)
        R.floor_poly(V, inner, z, "int_ru_carpet_atrium", step=3.0)
        R.floor_poly(V, outer, z, "int_ru_black", step=3.0, holes=(list(reversed(inner)),))
    # furniture clusters on the rugs: a 3 x 2 grid on rug 1 (3.5 m pitch, 0.6 m aisles between the collision
    # blocks; the cross aisle keeps the lounge anchor (-404, -271) on the floor), two + four on rug 2.
    # fix round 4 (fidelity-1, ru_atrium_enr_lounge: tan/wood 14% of the photo's furniture band vs 1.6% rendered,
    # navy 10% vs 27%): each group is a navy 2-3 seat sofa (tan seat cushions, tan wood side panels) facing a tan
    # wood coffee table, with bright orange club chairs / swivel tubs and a navy club chair with wood arms opposite
    # (was: four plum / navy club chairs + one orange swivel around a taupe table)
    clusters = [((-411.4, -273.1), 0.0), ((-407.9, -273.2), 190.0), ((-404.4, -273.2), 10.0),
                ((-411.4, -269.0), 200.0), ((-407.9, -269.0), 15.0), ((-404.4, -269.0), 185.0),
                ((-389.0, -278.0), 0.0), ((-387.3, -280.4), 200.0),
                ((-382.4, -278.9), 180.0), ((-379.3, -278.9), 10.0), ((-382.6, -274.2), 195.0),
                ((-379.4, -274.2), 0.0)]
    k = 0
    for (cx, cy), rot in clusters:
        RZ.kit_add(R.coffee_table(1.25, 0.62, mat="int_ru_wood_tan", top="int_ru_wood_tan", col=False), "G",
                   tag=f"lounge_table_{k}", x=cx, y=cy, facing=rot)
        hb = 1.45 if k < 6 else 1.6
        if k < 8:
            K.col_box(C, cx - hb, cy - hb, z, cx + hb, cy + hb, z + 0.48, K.COL_NOCAM)
        elif k % 2 == 0:
            # the east void's groups pair up in rows: one block per row (the area's collision budget)
            ox_, oy_ = clusters[k + 1][0]
            K.col_box(C, min(cx, ox_) - 1.3, cy - 1.3, z, max(cx, ox_) + 1.3, cy + 1.3, z + 0.48, K.COL_NOCAM)
        a = math.radians(rot)

        def _put(prop, dx, dy, f, tag):
            px = cx + dx * math.cos(a) + dy * math.sin(a)
            py = cy - dx * math.sin(a) + dy * math.cos(a)
            RZ.kit_add(prop, "G", tag=tag, x=px, y=py, facing=(f + rot) % 360)
        # the sofa behind the table (-y), facing it; three seats on every third group
        _put(R.lounge_sofa(2.25 if k % 3 == 1 else 1.75), 0.0, -1.0, 0.0, f"lounge_sofa_{k}")
        # opposite (+y): an orange club chair and a navy wood-armed club chair (or a second orange / a swivel tub)
        left = R.lounge_chair("int_ru_fabric_orange", "int_ru_fabric_orange", col=False, arm="int_ru_wood_tan")
        if k % 2 == 0:
            right = R.lounge_chair("int_ru_fabric_navy", "int_ru_leather_navy", col=False, arm="int_ru_wood_tan")
        elif k % 4 == 1:
            right = R.lounge_chair("int_ru_fabric_orange", swivel=True, col=False)
        else:
            right = R.lounge_chair("int_ru_fabric_plum", "int_ru_fabric_taupe", col=False, arm="int_ru_wood_tan")
        _put(left, -0.5, 1.02, 180.0, f"lounge_chair_{k}_0")
        _put(right, 0.5, 1.02, 180.0, f"lounge_chair_{k}_1")
        k += 1
    # UF letters (facing south) on the gator-skin wall panel behind them
    RZ.kit_add(R.uf_letters(2.6, 0.7), "G", tag="uf_letters", x=-409.4, y=-265.6, facing=180.0)
    # fix round 4 (technical improvement): the gap between the letters' plinth and the 20 cm Senate Chamber wall is
    # filled (collision only, up to 2.2 m: below the letters' top, a reward spot): stepping off the plinth's back
    # pushed Mario through the thin wall
    K.col_box(P.collision, -411.95, -265.3, z, -406.85, -264.47, z + 2.2, K.COL_NOCAM)
    wall_a, wall_b = (-414.0, -264.36), (-404.6, -264.36)
    # fix round 4 (fidelity-1): the texture maps over 2 m (plates about 2x larger in world size)
    # fix round 5 (fidelity-1): the recipe now has 3 x 3 taupe plates on a cream network per tile, mapped over 1.0 m
    # (~0.33 m plates, the photo's ~0.3-0.4 m)
    R.panel(V, wall_a, wall_b, z, z + 5.3, "int_ru_gator_skin", off=0.13, u0=0.0, u1=math.dist(wall_a, wall_b) / 1.0,
            v0=0.0, v1=5.3 / 1.0)
    # fix round 2 (fidelity, ru_atrium_uf_letters_flickr): the gator-skin wall is washed by spots (it reads light /
    # cream in the photo; under the Level 1 soffit the baked light left it a mid grey)
    for wx in (-412.2, -409.3, -406.4):
        P.lights.append(K.Light((wx, -265.7, 4.6), radius=5.5, strength=0.32, color=LIGHT_WARM))
    # fix round 4 (fidelity-1, ru_atrium_uf_letters_wall): a warm wash aimed at the letter FRONTS (they baked to a
    # brick red (166,56,17) under the Level 1 soffit against the photo's (241,119,17))
    for wx in (-410.6, -408.2):
        P.lights.append(K.Light((wx, -267.3, 1.9), radius=4.5, strength=0.45, color=LIGHT_WARM))
    # WELCOME TO THE REITZ UNION banner hung on the Level 1 balcony rail above the letters (the void's north edge
    # (-413.6, -266.9) -> (-395.6, -265.7); ru_atrium_uf_letters_flickr), on the void side of the pickets
    ea, eb = (-413.6, -266.9), (-395.6, -265.7)
    ba = (ea[0] + (eb[0] - ea[0]) * 0.08, ea[1] + (eb[1] - ea[1]) * 0.08)
    bb = (ea[0] + (eb[0] - ea[0]) * 0.47, ea[1] + (eb[1] - ea[1]) * 0.47)
    R.panel(V, ba, bb, RZ.floors["L1"].z + 0.05, RZ.floors["L1"].z + 1.0, "int_ru_banner_welcome", off=0.09)
    # Swamp Boss gator head (plan object at (-397.3, -271.1)), under the stair landing; free library (plan)
    RZ.kit_add(R.gator_head(1.0), "G", tag="swamp_boss", x=-397.3, y=-271.1, facing=90.0)
    RZ.kit_add(R.free_library(4.6, 1.5), "G", tag="free_library", x=-386.1, y=-271.2, facing=270.0)
    # gator tracks: footprints along a winding steel strip from the South Terrace doors into the lounge
    # (on bare terrazzo: south of the second rug and its two lounge clusters; ru_floor_gator_tracks)
    base = [(-385.4, -285.4), (-388.6, -284.2), (-392.4, -283.4), (-394.0, -282.6), (-396.2, -280.4), (-399.5, -277.2)]
    # fix round 2 (fidelity, ru_floor_gator_tracks): the strip is a continuous S-curve (a sine wiggle of amplitude
    # 0.35 m, wavelength 2.5 m laid along the base line), and the prints alternate close beside it, each turned to the
    # local tangent (it was a 6-point polyline that read straight)
    blen = sum(math.dist(pa, pb) for pa, pb in zip(base, base[1:]))

    def _on_base(dist_):
        si = 0
        while si < len(base) - 2 and dist_ > math.dist(base[si], base[si + 1]):
            dist_ -= math.dist(base[si], base[si + 1])
            si += 1
        pa, pb = base[si], base[si + 1]
        f = min(1.0, dist_ / max(1e-6, math.dist(pa, pb)))
        return (pa[0] + (pb[0] - pa[0]) * f, pa[1] + (pb[1] - pa[1]) * f), _unit2(pa, pb)
    nseg = int(blen / 0.12)
    path = []
    for i in range(nseg + 1):
        dist_ = blen * i / nseg
        (bx, by), d = _on_base(dist_)
        w = 0.35 * math.sin(2 * math.pi * dist_ / 2.5)
        path.append((bx - d[1] * w, by + d[0] * w))
    # smooth the corners of the base line (3-tap average; the ends stay put)
    for _ in range(3):
        path = [path[0]] + [((p0[0] + 2 * p1[0] + p2[0]) / 4, (p0[1] + 2 * p1[1] + p2[1]) / 4)
                            for p0, p1, p2 in zip(path, path[1:], path[2:])] + [path[-1]]

    def _tan(i):
        pa, pb = path[max(0, i - 1)], path[min(len(path) - 1, i + 1)]
        return _unit2(pa, pb)
    # fix round 4 (fidelity-1, ru_floor_gator_tracks): a thin BRIGHT stainless line, 4 cm (was a 7 cm mid-grey strip
    # that read darker and heavier than the terrazzo); flat colour, so no texel line to shimmer
    hw = 0.02
    for i in range(len(path) - 1):
        pa, pb = path[i], path[i + 1]
        ta, tb = _tan(i), _tan(i + 1)
        V.poly([(pa[0] + ta[1] * hw, pa[1] - ta[0] * hw, z + 0.002), (pb[0] + tb[1] * hw, pb[1] - tb[0] * hw, z + 0.002),
                (pb[0] - tb[1] * hw, pb[1] + tb[0] * hw, z + 0.002), (pa[0] - ta[1] * hw, pa[1] + ta[0] * hw, z + 0.002)],
               "int_ru_steel_bright", normal_hint=(0, 0, 1), glow=True)     # polished: brighter than the terrazzo
    plen = sum(math.dist(pa, pb) for pa, pb in zip(path, path[1:]))
    nprint = max(12, int(plen / 1.0))          # alternating prints about 1 m apart (ru_floor_gator_tracks)
    cum = [0.0]
    for pa, pb in zip(path, path[1:]):
        cum.append(cum[-1] + math.dist(pa, pb))
    for i in range(nprint):
        dist_ = 0.3 + (plen - 0.6) * i / (nprint - 1.0)      # arc-length spacing along the strip
        si = max(0, min(len(path) - 2, next((k for k in range(len(cum) - 1) if cum[k + 1] >= dist_), len(path) - 2)))
        pa, pb = path[si], path[si + 1]
        f = min(1.0, max(0.0, (dist_ - cum[si]) / max(1e-6, cum[si + 1] - cum[si])))
        cx, cy = pa[0] + (pb[0] - pa[0]) * f, pa[1] + (pb[1] - pa[1]) * f
        d = _unit2(path[max(0, si - 2)], path[min(len(path) - 1, si + 3)])
        side = 0.3 if i % 2 else -0.3
        px, py = cx - d[1] * side, cy + d[0] * side
        ang = math.atan2(d[1], d[0])
        pts = []
        for (u, v) in ((-0.2, -0.2), (0.2, -0.2), (0.2, 0.2), (-0.2, 0.2)):
            pts.append((px + u * math.cos(ang) - v * math.sin(ang), py + u * math.sin(ang) + v * math.cos(ang), z + 0.004))
        V.poly(pts, "int_ru_gator_track", uvs=[(0, 1), (0, 0), (1, 0), (1, 1)], normal_hint=(0, 0, 1))
    orange_brew_front(V, P, z)
    RZ.kit_add(P, "G", tag="atrium_lounge")
    RZ.points.setdefault("atrium", {})["lounge"] = {"name": "interior_atrium_lounge", "p": [-404.0, -271.0, 0.0],
                                                    "kind": "ground"}
    RZ.points["atrium"]["uf_letters_top"] = {"name": "interior_uf_letters_top", "p": [-411.33, -265.6, 2.95],
                                             "kind": "ground"}


# fix round 5 (fidelity-1, ru_atrium_enr_lounge right third): the lounge's south side (the slanted SW facade's inner
# face, (-396.93, -282.72) -> (-406.18, -291.77), facing the lounge) was a blank cream wall ~13 m long. The photo
# shows the Orange & Brew front there: a low white ledge, tall glazed bays with dark bronze mullions ~1.2 m apart, warm
# lit interiors with posters behind, a transom bar under the white wall / soffit. Visual only, on the wall's room side:
# panels 5 cm off the wall (no coplanar faces; 3 cm read as coplanar to the origin-offset z-fight scan on the slanted
# run), mullions / transom / ledge cap 6.5-21.5 cm off it (inside Mario's 24 cm foot wall radius: the wall's own
# collision is unchanged, nothing new to stand on or snag).
OB_FRONT = [((-396.93, -282.72), (-402.68, -288.06), 0.2, 0.2, 2),     # (a, b, inset at a, inset at b, door bay)
            ((-402.54, -287.92), (-406.18, -291.77), 0.4, 0.2, None)]


def orange_brew_front(V, P, z):
    BAY = 1.25
    for a, b, ia, ib, door in OB_FRONT:
        L = math.dist(a, b)
        d = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
        n = (d[1], -d[0])                                   # right of a -> b: into the lounge
        a2 = (a[0] + d[0] * ia, a[1] + d[1] * ia)
        L2 = L - ia - ib
        nb = max(1, int(round(L2 / BAY)))
        w = L2 / nb

        def at(s_, off):
            return (a2[0] + d[0] * s_ + n[0] * off, a2[1] + d[1] * s_ + n[1] * off)
        for i in range(nb):
            pa, pb = at(i * w, 0.0), at((i + 1) * w, 0.0)
            if i == door:
                # the glass door bay into Orange & Brew, a white panel over it
                R.panel(V, pa, pb, z + 0.02, z + 2.4, "int_ru_door_glass", off=0.05)
                R.panel(V, pa, pb, z + 2.4, z + 2.98, "int_ru_white", off=0.05)
                continue
            R.panel(V, pa, pb, z + 0.1, z + 0.98, "int_ru_white", off=0.05)                   # the low white ledge
            u0, u1 = (0.0, 1.0) if i % 2 == 0 else (1.0, 0.0)                             # mirrored: variety
            R.panel(V, pa, pb, z + 0.98, z + 2.98, "int_ru_cafe_bay", off=0.05, u0=u0, u1=u1, glow=True)
            R.seg_box(V, at(i * w + 0.02, 0.14), at((i + 1) * w - 0.02, 0.14), 0.075, z + 0.96, z + 1.02,
                      "int_ru_white", faces="sideends_top_bot")                          # the ledge cap
        for i in range(nb + 1):                                                          # bronze mullions
            s_ = min(max(i * w, 0.04), L2 - 0.04)
            R.seg_box(V, at(s_, 0.065), at(s_, 0.15), 0.04, z + 0.02, z + 2.97, "int_ru_slat_dark",
                      faces="sideends_top")
        R.seg_box(V, at(0.0, 0.1075), at(L2, 0.1075), 0.0425, z + 2.98, z + 3.1, "int_ru_slat_dark",
                  faces="sideends_top_bot")                                              # the transom bar
        if door is not None:
            c0 = (door + 0.5) * w
            R.panel(V, at(c0 - 1.0, 0.0), at(c0 + 1.0, 0.0), z + 3.3, z + 4.3, "int_ru_sign_ob", off=0.05)
        for i in range(0, nb, 2):
            P.lights.append(K.Light(at((i + 0.5) * w, 1.2)[:2] + (z + 2.3,), radius=3.2, strength=0.22,
                                    color=LIGHT_WARM))


# fix round 5 (fidelity-1 improvement 4; ru_atrium_enr_vertical): the void's east (far) end walls at Levels 2 and 3
# read as plain white walls with small framed pictures; the photo shows the balconies wrapping the far end with glass
# office fronts under the bulkhead. The centre runs of those end walls (between their glass doors) get glazed office
# bays: an office-interior glass card 4 cm off each wall segment (no coplanar faces), silver mullions and a head bar
# 4.5-13 cm off it. Visual only (inside Mario's wall radius; the walls' collision is unchanged). Segments: (north end,
# south end) of each west-facing wall face, from the plan walls; 0.18 m inset at both ends (the faces overlap there).
EAST_END_OFFICES = {
    "L2": [((-387.69, -270.21), (-388.01, -267.31))[::-1], ((-387.81, -271.69), (-387.69, -269.99))[::-1],
           ((-388.01, -275.29), (-387.79, -271.49))[::-1]],
    "L3": [((-388.78, -268.42), (-389.12, -266.82))[::-1], ((-388.59, -270.51), (-388.81, -268.21))[::-1],
           ((-388.6, -271.5), (-388.6, -270.3))[::-1], ((-388.71, -272.79), (-388.59, -271.29))[::-1],
           ((-388.81, -274.19), (-388.69, -272.59))[::-1], ((-389.12, -275.27), (-388.77, -273.98))[::-1]],
}


def east_end_offices(RZ):
    for fl, segs in EAST_END_OFFICES.items():
        z = RZ.floors[fl].z
        P = K.Prop(f"east_offices_{fl}")
        V = P.visual
        for a, b in segs:
            if a[1] < b[1]:
                a, b = b, a                                   # north -> south: the right normal faces west (the void)
            L = math.dist(a, b)
            d = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
            n = (d[1], -d[0])
            ins = 0.18
            L2 = L - 2 * ins
            nb = max(1, int(round(L2 / 1.25)))
            w = L2 / nb

            def at(s_, off):
                return (a[0] + d[0] * (ins + s_) + n[0] * off, a[1] + d[1] * (ins + s_) + n[1] * off)
            for i in range(nb):
                u0, u1 = (0.0, 1.0) if (i + len(fl)) % 2 == 0 else (1.0, 0.0)
                R.panel(V, at(i * w, 0.0), at((i + 1) * w, 0.0), z + 0.1, z + 2.7, "int_ru_office_bay", off=0.04,
                        u0=u0, u1=u1)
            for i in range(nb + 1):
                s_ = min(max(i * w, 0.035), L2 - 0.035)
                R.seg_box(V, at(s_, 0.045), at(s_, 0.12), 0.035, z + 0.1, z + 2.69, "int_ru_steel", faces="sideends_top")
            R.seg_box(V, at(0.0, 0.0825), at(L2, 0.0825), 0.0375, z + 2.7, z + 2.8, "int_ru_steel",
                      faces="sideends_top_bot")
        RZ.kit_add(P, fl, tag=f"east_offices_{fl}")


def level1_extras(RZ):
    """Level 1 by the north entrance: the Info Desk (plan object; no photo: inferred), the Putting Green, RecRe Box
    and Giant Chess Board (plan objects by the east stair), the FOOD COURT / wayfinding signs."""
    F = RZ.floors["L1"]
    z = F.z
    # plan object 'Info Desk': 2.7 x 1.0 m at (-399.1..-396.4, -261.3..-260.3); a curved navy counter (inferred)
    RZ.kit_add(R.info_desk(3.12, d=0.7, front="int_ru_wall_navy"), "L1", tag="info_desk", x=-397.75, y=-261.0, z=z,
               facing=180.0)
    P = K.Prop("l1_extras")
    V, C = P.visual, P.collision
    R.panel(V, (-399.2, -259.95), (-396.2, -259.95), z + 2.6, z + 3.4, "int_ru_sign_info", off=0.0, glow=True)
    # fix round 4 (fidelity-1; no photo, inferred): the desk stood alone against a blank white wall between two wood
    # doors. A navy accent panel fills the 3 m wall behind it (6 cm proud of the wall face at y -259.8, up to 5 cm
    # under the ceiling), with the white J. WAYNE REITZ UNION cut-out letters above the INFORMATION DESK sign
    R.panel(V, (-399.04, -259.86), (-396.26, -259.86), z + 0.1, z + 5.35, "int_ru_wall_navy", off=0.0)
    R.panel(V, (-398.95, -259.9), (-396.35, -259.9), z + 3.75, z + 5.05, "int_ru_sign_union", off=0.0)
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


# fix round 4 (technical blocking): the atrium rail junctions (flight rail end | balcony rail end) left pockets of
# thin one-sided NO_CAM faces Mario squeezed through (spotfall.py: 362 / 1023 / 164 / 165 / 140 falls at the five
# spots). A closed collision post (four outward faces + top, NO_CAM, rail height) fills each pocket, centred on the
# void points the walks fell from (plan m, floor). Collision only: the rendered pickets are continuous there.
# (plugs that the walks showed standing ON walkable floor - start points inside them - are left out: L2 (-393.3,
# -266.0) and the L2 SE flight foot; those junctions stay as the round-3 build had them)
# L3 kink: the wedge between the kink rail's east face and the main rail's west face, at the main rail's end cap
# (game x 7807..7812, z -1847: the opposing pushes cancelled and Mario slid down it into the void)
RAIL_PLUGS = [("L1", -398.2, -276.3, 0.24), ("L1", -397.0, -276.6, 0.2),
              ("L2", -393.8, -265.4, 0.24),
              ("L3", -394.25, -266.95, 0.24), ("L3", -393.4, -266.8, 0.2),
              ("L3", -391.90, -274.48, 0.12)]


def rail_plugs(RZ):
    P = K.Prop("rail_plugs")
    for fid, x, y, h in RAIL_PLUGS:
        z = RZ.floors[fid].z
        K.col_box(P.collision, x - h, y - h, z - 0.05, x + h, y + h, z + RAIL_H + 0.06, K.COL_NOCAM)
        # fix round 5 (technical improvement 0): every plug that stays is a rendered newel post (it stood as an
        # invisible post on walkable floor); 1 cm inside its collision on every side
        P.visual.box(x - h + 0.01, y - h + 0.01, z, x + h - 0.01, y + h - 0.01, z + RAIL_H + 0.05, "int_ru_white",
                     faces="+x-x+y-y+z")
    RZ.kit_add(P, "L1", tag="rail_plugs")


DRESSERS.extend([atrium_stairs, atrium_top, atrium_lounge, level1_extras, rail_plugs, east_end_offices])


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
            RZ.kit_add(R.ball_rack(1.1, front_only=True), "G", tag=f"ball_rack_{i}", x=bx + pitch, y=ly + 6.2, facing=0.0)
    # billiards hall (ru_gr_billiards_room): gator-scale carpet, two rows of tables along the dark north wall under
    # square LED frames (9 pool tables + the snooker table), cue racks on the wall
    # fix round 4 (fidelity-3; ru_es_oelrich_8951): the 2.6 m strip in front of the Esports glass is the grey plank
    # lounge floor (the zone's int_ru_plank), the carpet starts at the first table row
    carpet = [(-456.6, -297.2), (-440.6, -297.2), (-440.6, -282.3), (-456.6, -282.3)]
    R.floor_poly(V, R.ccw(carpet), z, "int_ru_carpet_billiards", step=4.5)
    # fix round 4 (fidelity-3; ru_gr_entry_graphic): the service desk + the GAME ROOM wall stand on the same blue
    # patterned carpet (it was the plank floor); it abuts the billiards carpet on x -440.6 (shared edge, no overlap)
    carpet2 = [(-440.6, -297.2), (-425.1, -297.2), (-425.1, -290.0), (-440.6, -290.0)]
    R.floor_poly(V, R.ccw(carpet2), z, "int_ru_carpet_billiards", step=4.5)
    k = 0
    # (fix round 2: shifted 1 m east, the arcade + esports bar stand along the storefront west of them)
    for ty, xs in ((-285.3, (-455.0, -450.3, -445.6, -440.9)), (-290.8, (-455.0, -450.3, -445.6)),
                   (-295.0, (-455.0, -450.3, -445.6))):
        for tx in xs:
            if k >= 9:
                break
            RZ.kit_add(R.billiard_table(), "G", tag=f"pool_{k}", x=tx, y=ty, facing=0.0)
            if k in (0, 5, 8):          # design pass: a coin on three of the tables' felt (jump up)
                EXTRA_PICKUPS.append({"kind": "coin", "name": f"billiards table {k} coin", "pos": (tx, ty, z + 0.79)})
            RZ.kit_add(R.led_frame(3.4, 2.2, z + 3.6), "G", tag=f"pool_led_{k}", x=tx, y=ty, facing=0.0)
            k += 1
    RZ.kit_add(R.billiard_table(3.57, 1.78), "G", tag="snooker", x=-437.2, y=-294.6, facing=0.0)
    RZ.kit_add(R.led_frame(4.0, 2.4, z + 3.6), "G", tag="snooker_led", x=-437.2, y=-294.6, facing=0.0)
    for j, cx_ in enumerate((-457.2, -452.6, -447.9, -443.2)):
        RZ.kit_add(R.cue_rack(), "G", tag=f"cue_rack_{j}", x=cx_, y=-282.3, z=z, facing=180.0)
    # wall graphics: GAME ROOM over the billiards (north wall), and by the service desk
    # fix round 4 (fidelity-3 blocking): the GAME ROOM graphic sits east along the billiards wall, above the cue
    # racks (the photo's west end is a plain dark wall with the racks); a 1.5 cm proud face (decal rule)
    # fix round 5 (fidelity-3; ru_gr_wall_graphic_billiards): its own graphic, GAME ROOM / THE UNIVERSITY OF FLORIDA
    # with the planets and a bowling ball (it reused the desk mural's REITZ UNION GAME ROOM)
    R.panel(V, (-447.85, -281.5), (-443.85, -281.5), z + 3.3, z + 5.05, "int_ru_sign_gameroom_uf", off=0.015)
    # fix round 4 (fidelity-3; ru_gr_entry_graphic): the desk graphic is wall-filling (10 x 4.2 m from behind the
    # counter nearly to the ceiling; it was a 7 x 3.5 m framed panel), 4 cm proud of the wall face
    R.panel(V, (-435.6, -290.0), (-425.6, -290.0), z + 0.9, z + 5.1, "int_ru_sign_gameroom", off=0.04)
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
    # fix round 5 (design pass, improvement 5; ru_gr_booth_detail, ru_gr_booths): the open plank south of the
    # table games (x -427..-424, y -320.5..-325.5, clear of the Goomba spots in GOOMBA_SPOTS) gets a seating cluster:
    # two navy curved booths with their low tables, facing each other
    RZ.kit_add(R.booth(2.9), "G", tag="gr_east_booth_n", x=-425.5, y=-320.6, facing=180.0)
    RZ.kit_add(R.booth(2.9), "G", tag="gr_east_booth_s", x=-425.5, y=-325.4, facing=0.0)
    # fix round 2 (blocking; ru_es_oelrich_8951, ru_gr_esports_bridge_billiards, ru_gr_arcade, ru_gr_arcade_2): the
    # arcade cabinets stand against the Esports Center's glass storefront on the billiards side (they were at the
    # pin end, sliced by the service-corridor walls), with the blue kiosk, the black high-top bar with a steel
    # foot rail and stools, and navy / tan ottomans; over the storefront the GATOR ESPORTS CENTER sign above the
    # glass door and a row of TVs
    xs_ = -459.3                                          # the storefront's game-room face
    for i in range(8):
        RZ.kit_add(R.arcade_cabinet(), "G", tag=f"arcade_{i}", x=xs_ + 0.5, y=-283.6 - i * 0.95, facing=90.0)
    V.box(xs_ + 0.15, -292.85, z, xs_ + 0.85, -292.15, z + 1.55, "int_ru_uf_blue", faces="+x-x+y-y+z")      # kiosk
    R.panel(V, (xs_ + 0.86, -292.75), (xs_ + 0.86, -292.25), z + 1.0, z + 1.45, "int_ru_game_screen", off=0.0, glow=True)
    K.col_box(C, xs_ + 0.15, -292.85, z, xs_ + 0.85, -292.15, z + 1.55, K.COL_NOCAM)
    # glass door in the storefront (visual; the plan's door into the Esports Center is the north one)
    # fix round 5 (fidelity-3; ru_es_oelrich_8951): a black-framed door of the storefront's own dark glass (the pale
    # int_ru_door_glass leaves read as a grey-white double door): stiles, rails and the meeting stile 3 cm proud of
    # the Game Room face (butted, never overlapping), steel pull bars 1.5 cm proud of the frame
    da_, db_ = -294.75, -293.05
    for y0f, y1f in ((da_ - 0.05, da_ + 0.07), (db_ - 0.07, db_ + 0.05)):
        R.panel(V, (xs_, y0f), (xs_, y1f), z, z + 2.88, "int_ru_black", off=0.03)
    for z0f, z1f in ((0.0, 0.22), (2.72, 2.88)):
        R.panel(V, (xs_, da_ + 0.07), (xs_, db_ - 0.07), z + z0f, z + z1f, "int_ru_black", off=0.03)
    R.panel(V, (xs_, -293.96), (xs_, -293.84), z + 0.22, z + 2.72, "int_ru_black", off=0.03)
    for yb_ in (-294.12, -293.68):
        R.panel(V, (xs_, yb_ - 0.02), (xs_, yb_ + 0.02), z + 0.85, z + 1.45, "int_ru_steel", off=0.045)
    _esports_sign(V, (xs_, -296.0), (xs_, -291.8), z + 3.02, z + 3.46, off=0.1)
    for k_ in range(9):
        y0_ = -283.0 - k_ * 2.65
        R.panel(V, (xs_, y0_ - 1.5), (xs_, y0_), z + 3.65, z + 4.5, "int_ru_black", off=0.1)
        R.panel(V, (xs_, y0_ - 1.42), (xs_, y0_ - 0.08), z + 3.7, z + 4.45, "int_ru_game_screen", off=0.12, glow=True)
    # high-top bar counter + steel foot rail + stools. Fix round 4 (fidelity-3; ru_es_oelrich_8951): the bar runs
    # PERPENDICULAR to the glass, out over the plank strip (it stood along the glass, hidden behind the pool
    # tables), stools on its south side facing north
    V.box(xs_ + 0.1, -297.15, z, xs_ + 3.5, -296.6, z + 1.07, "int_ru_black", faces="+x-x+y-y+z")
    V.box(xs_ + 0.2, -297.2, z + 0.2, xs_ + 3.4, -297.15, z + 0.25, "int_ru_steel", faces="-y+z-z")
    K.col_box(C, xs_ + 0.1, -297.2, z, xs_ + 3.5, -296.6, z + 1.07, K.COL_NOCAM)
    for j_ in range(4):
        sx = xs_ + 0.6 + j_ * 0.85
        R.cyl(V, sx, -297.65, 0.03, z, z + 0.72, "int_ru_steel", n=4, top=False)
        R.cyl(V, sx, -297.65, 0.2, z + 0.72, z + 0.78, "int_ru_black", n=8)
    # ottomans (navy / tan)
    for j_, (ox_, oy_, om) in enumerate(((xs_ + 1.3, -299.9, "int_ru_fabric_navy"), (xs_ + 2.2, -300.1, "int_ru_fabric_taupe"),
                                         (xs_ + 1.6, -300.9, "int_ru_fabric_taupe"))):
        V.box(ox_ - 0.25, oy_ - 0.25, z, ox_ + 0.25, oy_ + 0.25, z + 0.45, om, faces="+x-x+y-y+z")
    # the service corridor between the lanes and the east games (plan walls x -431.3 / -429.4) is back of house:
    # a closed steel door across its open north end (it was a 24 m navy dead end)
    V.box(-431.3, -304.9, z, -429.4, -304.7, z + CLEAR["G"], "int_ru_wall_navy", faces="+y-y")
    K.col_box(C, -431.3, -304.9, z, -429.4, -304.7, z + CLEAR["G"], K.COL)
    door_leaves(V, (-429.65, -304.68), (-431.05, -304.68), z, 2.4, "int_ru_door_steel")
    for i in range(1, 3):
        R.panel(V, (-432.0 + i * 3.4 + 2.8, -330.25), (-432.0 + i * 3.4, -330.25), z + 2.3, z + 3.7, "int_ru_hex_neon",
                off=0.12, glow=True)
    # fix round 5 (fidelity-3; ru_gr_arcade_2 'arcade cabinets, hex neon wall'): a second bank of lit arcade cabinets
    # backed onto the hex-neon south wall of the table-games strip (its south 10 m was empty plank); facing north,
    # one merged collision block for the bank (collision budget)
    for i in range(6):
        RZ.kit_add(_nocol(R.arcade_cabinet()), "G", tag=f"arcade_s_{i}", x=-427.575 + i * 0.95, y=-329.8, facing=0.0)
    K.col_box(C, -427.935, -330.225, z, -422.465, -329.125, z + 1.85, K.COL_NOCAM)
    # fix round 5 (fidelity-3; ru_es_oelrich_8951): the black square column at the Esports frontage with its lit
    # portrait screen, the navy / tan ottomans in front of it (the photo's left foreground)
    V.box(-456.6, -299.6, z, -455.8, -298.8, z + CLEAR["G"], "int_ru_black", faces="+x-x+y-y")
    R.panel(V, (-455.8, -299.45), (-455.8, -298.95), z + 0.7, z + 2.1, "int_ru_game_screen", off=0.02, glow=True)
    K.col_box(C, -456.6, -299.6, z, -455.8, -298.8, z + CLEAR["G"], K.COL_NOCAM)
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


def _esports_sign(V, a, b, z0, z1, off=0.02):
    """The lit GATOR ESPORTS CENTER line across a -> b (facing right of a -> b, reading from a): four quads, the
    256 x 16 px line of tx_sign_esports_part (strips 0 / 1 in int_ru_sign_esports, 2 / 3 in int_ru_sign_esports_b;
    strip 0 / 2 = rows 0-15 = v 0.5-1). Letters fill 14 / 16 of z0..z1."""
    for q_ in range(4):
        pa = (a[0] + (b[0] - a[0]) * q_ / 4, a[1] + (b[1] - a[1]) * q_ / 4)
        pb = (a[0] + (b[0] - a[0]) * (q_ + 1) / 4, a[1] + (b[1] - a[1]) * (q_ + 1) / 4)
        R.panel(V, pa, pb, z0, z1, "int_ru_sign_esports" if q_ < 2 else "int_ru_sign_esports_b", off=off,
                glow=True, v0=0.5 if q_ % 2 == 0 else 0.0, v1=1.0 if q_ % 2 == 0 else 0.5)


def esports(RZ):
    """Gator Esports Center (Ground; builder photos ru_es_oelrich_*, ru_es_overview, ru_es_pods): a long narrow
    dark room off the Game Room: PC stations with blue edge light along the west wall and a back-to-back island,
    the lit one-line GATOR ESPORTS CENTER sign on a bulkhead at the end wall, white-blue hex neon on the near-black
    hex walls, a wood-look floor, glass dome pendants, a red bench, couch co-op screens at the north end."""
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
    # the lit GATOR ESPORTS CENTER sign (ru_es_overview): ONE long line of big white letters across a black
    # bulkhead on the south end wall, a blue LED underline below the letters; hex neon clusters on both long walls,
    # blue cove strips along the ceiling edges (ru_es_overview, ru_es_pods)
    yb = -308.45                                    # bulkhead front (0.5 m proud of the end wall)
    # fidelity-3 (round 2; ru_es_overview): the bold italic letters with their blue halo FILL the band: a 256 px line
    # in four 1.48 m quads (_esports_sign), letters ~0.5 m tall over ~5.4 m, the bulkhead band 0.95 m round them
    V.box(-465.7, -308.95, z + 3.35, -459.6, yb, z + 4.3, "int_ru_black", faces="+y-z")
    _esports_sign(V, (-459.7, yb), (-465.6, yb), z + 3.55, z + 4.13)
    V.box(-465.4, yb, z + 3.42, -459.9, yb + 0.05, z + 3.46, "int_ru_led", faces="+y-z+z", glow=True,
          tint=(0.3, 0.5, 1.0))
    P.lights.append(K.Light((-462.6, -307.0, z + 3.5), radius=6.0, strength=0.35, color=(0.75, 0.82, 1.0)))
    for k, yy in enumerate(range(-305, -279, 4)):
        if k % 2 == 0 and yy > -298:
            R.panel(V, (-459.5, yy + 1.2), (-459.5, yy - 1.2), z + 2.0, z + 3.8, "int_ru_hex_neon", off=0.02, glow=True)
        elif k % 2 == 1:
            R.panel(V, (-465.85, yy - 1.2), (-465.85, yy + 1.2), z + 2.0, z + 3.8, "int_ru_hex_neon", off=0.02, glow=True)
    for xx, sgn in ((-459.6, -1), (-465.8, 1)):
        V.box(min(xx, xx + 0.12 * sgn), -308.8, z + 4.9, max(xx, xx + 0.12 * sgn), -277.2, z + 4.96, "int_ru_led",
              faces="-z", glow=True, tint=(0.3, 0.45, 1.0))
    # big glass dome pendants over the PC rows (ru_es_overview, ru_es_stations) + blue glow (dim room, cool light)
    zc = z + zn.style["clear"]
    domes = [(-464.9, yy) for yy in (-302.5, -299.0, -295.5, -292.5)] + [(-461.6, -304.5), (-461.6, -301.5)] + \
            [(-462.6, -286.0), (-462.6, -281.5)]
    for dx_, dy_ in domes:
        V.box(dx_ - 0.02, dy_ - 0.02, z + 4.2, dx_ + 0.02, dy_ + 0.02, zc, "int_ru_black", faces="+x-x+y-y")
        rings = [(0.07, z + 4.2), (0.28, z + 4.1), (0.40, z + 3.94), (0.45, z + 3.76)]
        for (ra, za), (rb, zb) in zip(rings, rings[1:]):
            for k in range(8):
                a0_, a1_ = 2 * math.pi * k / 8, 2 * math.pi * (k + 1) / 8
                V.poly([(dx_ + rb * math.cos(a0_), dy_ + rb * math.sin(a0_), zb),
                        (dx_ + rb * math.cos(a1_), dy_ + rb * math.sin(a1_), zb),
                        (dx_ + ra * math.cos(a1_), dy_ + ra * math.sin(a1_), za),
                        (dx_ + ra * math.cos(a0_), dy_ + ra * math.sin(a0_), za)], "int_ru_glass_blue")
        V.poly([(dx_ + 0.3 * math.cos(2 * math.pi * k / 8), dy_ + 0.3 * math.sin(2 * math.pi * k / 8), z + 3.95)
                for k in reversed(range(8))], "int_ru_led", glow=True, tint=(0.62, 0.7, 0.9), normal_hint=(0, 0, -1))
        P.lights.append(K.Light((dx_, dy_, z + 3.4), radius=4.5, strength=0.26, color=(0.6, 0.7, 1.0)))
    RZ.kit_add(P, "G", tag="esports_misc")
    RZ.points.setdefault("game_room", {})["esports"] = {"name": "interior_esports", "p": [-462.4, -293.0, z],
                                                         "kind": "ground"}


GN_SOFFIT = 3.9                 # Ground north-door corridor soffit (fidelity-3, round 2; = MEETING_CLEAR, for the camera)
GN_CORR = [(-421.2, -262.4), (-418.29, -262.4), (-418.1, -244.6), (-423.5, -244.5), (-423.6, -249.7), (-421.1, -249.8)]


def g_north_corridor(RZ):
    """fidelity-3 (round 2): the Ground north door (warp door x -420.4..-417.8) opened onto a blank white 2.9 m x
    5.4 m x 18 m tube. The plan run stays; it gets what makes the arrival read as the Reitz: a lower lay-in soffit
    (3.9 m, collision ceiling too) with downlights and a fascia where it meets the main corridor, a lit EXIT sign
    hung over the door, the Ground wayfinding blade (GAME ROOM / ESPORTS ahead, ATRIUM left, HOTEL DESK right) and a
    drinking-fountain + AED niche on the restroom wall."""
    F = RZ.floors["G"]
    z = F.z
    P = K.Prop("g_north_corridor")
    V, C = P.visual, P.collision
    zs = z + GN_SOFFIT
    poly = R.ccw(GN_CORR)
    V.poly([(x, y, zs) for x, y in reversed(poly)], "int_ru_tile_ceiling", ao=0.95)
    for t_ in R.triangulate(poly):
        C.poly([(x, y, zs) for x, y in reversed(R.ccw(t_))], K.COL)
    # fascia where the soffit meets the 5.4 m main corridor (faces south)
    R.quad_wall(V, (-421.2, -262.4), (-418.29, -262.4), zs, z + CLEAR["G"], "int_ru_wall")
    V.box(-421.2, -262.45, zs - 0.12, -418.29, -262.35, zs, "int_ru_white", faces="-y+y-z")
    # downlights in the soffit
    for yy in (-246.6, -250.2, -253.8, -257.4, -261.0):
        r = 0.12
        V.poly([(-419.75 - r, yy - r, zs - 0.01), (-419.75 - r, yy + r, zs - 0.01), (-419.75 + r, yy + r, zs - 0.01),
                (-419.75 + r, yy - r, zs - 0.01)], "int_ru_led", glow=True)
        P.lights.append(K.Light((-419.75, yy, zs - 0.3), radius=5.0, strength=0.26, color=LIGHT_WARM))
    P.lights.append(K.Light((-422.3, -247.2, zs - 0.3), radius=4.0, strength=0.2, color=LIGHT_WARM))
    # lit EXIT sign hung from the soffit just inside the door (faces the corridor, south)
    xd = (-420.4 + -417.8) / 2
    for dx_ in (-0.2, 0.2):
        V.box(xd + dx_ - 0.01, -245.06, z + 3.05, xd + dx_ + 0.01, -245.04, zs, "int_ru_steel", faces="+x-x+y-y")
    V.box(xd - 0.3, -245.1, z + 2.8, xd + 0.3, -245.0, z + 3.05, "int_ru_white", faces="+x-x+y-y-z+z")
    R.panel(V, (xd - 0.28, -245.1), (xd + 0.28, -245.1), z + 2.82, z + 3.03, "int_ru_exit", off=0.006, glow=True,
            v0=0.28, v1=0.72)
    # the Ground wayfinding blade across the corridor, both faces (reader walking in from the door: the N face)
    xc, yc, w2 = -419.75, -251.6, 0.75
    for dx_ in (-0.55, 0.55):
        V.box(xc + dx_ - 0.01, yc - 0.01, z + 3.35, xc + dx_ + 0.01, yc + 0.01, zs, "int_ru_steel", faces="+x-x+y-y")
    V.box(xc - w2, yc - 0.03, z + 2.75, xc + w2, yc + 0.03, z + 3.35, "int_ru_uf_blue", faces="+x-x-z+z")
    R.panel(V, (xc + w2, yc), (xc - w2, yc), z + 2.75, z + 3.35, "int_ru_wayfind_G", off=0.035, glow=True)
    R.panel(V, (xc - w2, yc), (xc + w2, yc), z + 2.75, z + 3.35, "int_ru_wayfind_G_s", off=0.035, glow=True)
    # drinking-fountain + AED niche on the west (restroom) wall: a slate recess panel, a bi-level steel fountain,
    # the white AED cabinet with its sign
    xw = -421.08
    V.box(xw, -257.9, z, xw + 0.02, -255.3, z + 2.3, "int_ru_wall_slate", faces="+x")
    V.box(xw, -257.95, z + 2.3, xw + 0.06, -255.25, z + 2.36, "int_ru_white", faces="+x-z+z")
    for (y0_, y1_, h_) in ((-257.6, -257.0, 0.86), (-256.95, -256.35, 1.0)):
        V.box(xw, y0_, z + h_ - 0.3, xw + 0.45, y1_, z + h_, "int_ru_steel", faces="+x+y-y+z-z")
        V.box(xw + 0.1, y0_ + 0.1, z + h_ + 0.001, xw + 0.38, y1_ - 0.1, z + h_ + 0.002, "int_ru_black", faces="+z")
    K.col_box(C, xw, -257.6, z, xw + 0.45, -256.35, z + 1.0, K.COL_NOCAM)
    V.box(xw, -256.1, z + 1.15, xw + 0.18, -255.5, z + 1.85, "int_ru_white", faces="+x+y-y+z-z")
    R.panel(V, (xw + 0.181, -256.06), (xw + 0.181, -255.54), z + 1.2, z + 1.8, "int_ru_aed", off=0.0)
    R.panel(V, (xw + 0.02, -256.1), (xw + 0.02, -255.5), z + 1.95, z + 2.22, "int_ru_aed", off=0.0, v0=0.62, v1=1.0)
    RZ.kit_add(P, "G", tag="g_north_corridor")


DRESSERS.extend([game_room, esports, g_north_corridor])


# ================================================================== Level 1: food court
SERVERY_FRONTS = [   # (wall points a -> b on the servery outline, generic sign, back-wall paint, side paint, style)
    # placed by the layout's food_vendors pins (props_extra L1: mvf_pins + osm_pins; generic signs, no brands)
    # fidelity-2: slot 0 is the photographed one (ru_food_court_counter_2023: the empty former counter by the lime
    # wall + sky-blue post: pale-blue siding, white top, a plain cream fascia, no sign); the red wok counter moved
    # one slot east and the pizza slot gave way to it
    ((-447.9, -310.6), (-453.1, -310.4), None, "int_ru_wall_cream", "int_ru_wall_cream", "photo"),          # (2023)
    ((-441.0, -312.0), (-446.5, -310.9), "int_ru_vend_wok", "int_ru_red", "int_ru_wall_cream", "wok"),       # Panda (MVF)
    ((-435.5, -309.8), (-440.0, -312.1), "int_ru_vend_halal", "int_ru_black", "int_ru_paint_lime", "halal"),  # Halal Shack
    ((-433.2, -303.0), (-433.2, -307.4), "int_ru_vend_coffee", "int_ru_mosaic", "int_ru_maple_panel", "coffee"),  # Starbucks
    ((-433.2, -298.9), (-433.2, -302.2), "int_ru_vend_mac", "int_ru_paint_lime", "int_ru_paint_sky", "mac"),  # Mac Shack
    ((-424.9, -297.2), (-432.0, -297.15), "int_ru_vend_burger", "int_ru_fc_tile", "int_ru_white", "burger"),  # Sonic
    ((-424.3, -291.6), (-424.3, -296.6), "int_ru_vend_smoothie", "int_ru_paint_lime", "int_ru_paint_sky", "shakes"),
    ((-424.3, -286.6), (-424.3, -290.8), "int_ru_vend_taco", "int_ru_paint_sky", "int_ru_paint_lime", "tacos"),  # Latin
]
# per-vendor finishes (fidelity pass 2): ru_food_court_sonic_2025 (navy fascia over a white-framed opening, neon name,
# bright white kitchen with a row of blue-lit menu screens, dark counter, wood-look panel right, red neon swirl
# left), ru_starbucks_2017 (maple counter + side panels, orange / green / cream mosaic, black chalkboards), the
# wok counter red / black; the others keep the pale-blue siding of ru_food_court_counter_2023.
# fidelity-2: no boxed sign panels: the names are channel letters straight on each vendor's fascia (Sonic: ~0.9 m
# glowing red-orange letters ~4.4 m wide); Sonic's opening shows ~1 m of busy steel kitchen under four landscape
# menu screens; the coffee counter carries espresso machines, a register and a lit pastry case
_FASCIA = dict(open_h=2.8, letters_w=3.0, letters_h=0.62)
VENDOR_STYLES = {
    "photo": {"counter": "int_ru_counter_front", "top": "int_ru_white", "fascia": "int_ru_wall_cream", "open_h": 2.7,
              "no_menu": True, "kitchen": True, "left_panel": ("int_ru_paint_lime", 1.0, None, "int_ru_paint_sky")},
    "wok": dict(_FASCIA, counter="int_ru_counter_red", top="int_ru_black", fascia="int_ru_black",
                letters="int_ru_vletters_wok", letters_w=2.4),
    "halal": dict(_FASCIA, fascia="int_ru_black", letters="int_ru_vletters_halal", letters_w=2.6),
    "mac": dict(_FASCIA, fascia="int_ru_wall_cream", letters="int_ru_vletters_mac", letters_w=3.0, letters_h=0.5),
    "shakes": dict(_FASCIA, fascia="int_ru_wall_cream", letters="int_ru_vletters_shakes", letters_w=3.6),
    "tacos": dict(_FASCIA, fascia="int_ru_wall_cream", letters="int_ru_vletters_tacos", letters_w=3.0),
    "coffee": {"counter": "int_ru_maple_panel", "top": "int_ru_black", "side": "int_ru_maple_panel",   # fix round 4
               "back_counter": "int_ru_maple_panel", "menu": "int_ru_chalkboard", "menu_glow": False, "menu_w": 3.4,
               # fix round 5 (fidelity-2; ru_starbucks_2017): the chalkboards hang high on the mosaic, their
               # bottoms about head height (they sat at 1.6-2.35 m, mid-wall)
               "menu_z": (1.95, 2.65), "hood": False, "coffee_bar": True,
               "fascia": "int_ru_maple_panel", "open_h": 2.8, "letters": "int_ru_vletters_coffee", "letters_w": 2.8,
               "letters_h": 0.55},
    "burger": {"counter": "int_ru_counter_navy", "top": "int_ru_white", "side": "int_ru_white",
               "menu": "int_ru_menu_screen", "menu_w": 3.6, "menu_n": 4, "menu_gap": 0.08, "menu_y": -0.75,
               "menu_z": (1.92, 2.38), "hood": False, "kitchen": True,
               "fascia": "int_ru_counter_navy", "open_h": 2.6, "frame": "int_ru_white",
               "letters": "int_ru_sign_burger_glow", "letters_w": 4.2, "letters_h": 0.86,
               "left_panel": ("int_ru_counter_navy", 1.5, "int_ru_neon_swirl_tall"), "panel_decal_full": True,
               # fix round 4 (fidelity-2): the neon (a cutout now, no card) runs ~1.3 x 2.5 m from counter height
               # to just under the sign, straight on the navy wall (it was a 1.26 x 2.13 m dim framed panel)
               "panel_decal_w": 1.3, "panel_decal_z": (0.95, 3.45), "panel_decal_y": 0.135,
               "right_panel": ("int_ru_wood_panel", 0.8), "light": 0.5},
}
FC_RING_ENDS = ((-455.6, -308.0), (-424.2, -286.3))   # the checker ring / soffit run: SW corner -> NE block's east face
FC_RING_DEPTH = 2.6        # the queue ring and the cream soffit over it (ru_food_court_counter_2023)
FC_SOFFIT_Z = 3.6          # soffit underside above L1 (photo ~2.9 m; raised for the camera; fidelity-2: 4.0 -> 3.6)
FC_FRONT_H = 3.6           # storefront openings / kitchen ceilings up to the soffit (fidelity-2: was 3.9)
# the hall tile runs to the glass (the OSM food court outline stops ~1.2 m short of the curved SE glass): the
# overlay's east part is replaced by the l1_corridor_08 edge (outdoor dining nook + curved glass)
FC_HALL_EAST = [(-420.85, -326.9), (-420.8, -318.4), (-416.6, -318.5), (-416.6, -320.0), (-412.4, -320.0),
                (-412.2, -305.2), (-411.0, -300.8), (-398.5, -284.9), (-396.3, -283.2), (-394.0, -282.9),
                (-394.0, -281.4)]


def _fc_front_path(serv_poly):
    """The servery outline (CCW) from FC_RING_ENDS[0] to FC_RING_ENDS[1]: the storefront run only (the west strip
    and the north side are back of house)."""
    P = R.ccw(serv_poly)
    i0 = min(range(len(P)), key=lambda k: math.dist(P[k], FC_RING_ENDS[0]))
    i1 = min(range(len(P)), key=lambda k: math.dist(P[k], FC_RING_ENDS[1]))
    out, k = [], i0
    while True:
        out.append(P[k])
        if k == i1:
            break
        k = (k + 1) % len(P)
    return out


FC_SOFFIT_STOP_Y = -299.6     # fix round 4 (fidelity-2): the south-front soffit ends here on the x -433.2 face
FC_BULK = (-433.2, -424.3, -297.15, 0.55)   # Sonic wall bulkhead: x0, x1, wall line y, depth


def _fc_soffit_runs(inner):
    """fix round 4 (fidelity-2): the queue-ring path split into the soffit runs: the south front + the coffee / mac
    east face up to FC_SOFFIT_STOP_Y, and the NE block's east face (shakes, tacos); none over the burger face."""
    a_run, b_run = [], []
    for p, q in zip(inner, inner[1:]):
        if not a_run:
            a_run.append(p)
        if abs(p[0] - q[0]) < 0.3 and abs(p[0] + 433.2) < 0.3 and q[1] > FC_SOFFIT_STOP_Y > p[1]:
            a_run.append((p[0] + (q[0] - p[0]) * (FC_SOFFIT_STOP_Y - p[1]) / (q[1] - p[1]), FC_SOFFIT_STOP_Y))
            break
        a_run.append(q)
    for i, p in enumerate(inner):
        if abs(p[0] + 424.3) < 0.3 and abs(p[1] + 297.2) < 0.3:
            b_run = inner[i:]
            break
    return [r for r in (a_run, b_run) if len(r) >= 2]


def _fc_sonic_wall(V, z):
    """fix round 4 (fidelity-2; ru_food_court_sonic_2025): over the burger storefront (fascia top at FC_FRONT_H) the
    navy wall runs on up to a shallow cream bulkhead under the lay-in ceiling."""
    x0, x1, yw, dep = FC_BULK
    zc = z + CLEAR["L1"]
    zb = zc - 0.62
    a, b = (x0 + 0.02, yw + 0.05), (x1 - 0.02, yw - 0.05)      # the wall line (-433.2, -297.1) -> (-424.3, -297.2)
    _wall_strip(V, a, b, z + FC_FRONT_H, zb + 0.01, "int_ru_counter_navy", off=0.13)   # 3 cm proud of the face
    # the navy wraps the 1.2 m of wall left of the storefront (to the mac corner) from the base up (the photo's navy
    # wall runs on left of the neon)
    # fix round 5 (technical blocking 2): 3 cm further out (at 0.13 it lay 0.02 u off the servery wall face)
    _wall_strip(V, a, (-432.0, -297.115), z + 0.10, z + FC_FRONT_H, "int_ru_counter_navy", off=0.16)
    V.box(x0, yw - dep, zb, x1, yw - 0.1, zc - 0.005, "int_ru_soffit", faces="-y-z+x", ao=0.92)


# fix round 5 (fidelity-2; ru_food_court_sonic_2025: the photo's most visible foreground props): black stanchion
# posts with black belt barriers on the checker floor in front of the burger counter (counter front ~y -297.9): a
# line 1.6 m out from it and a return to the counter at the west end (a queue lane, open to the east)
FC_STANCHIONS = ((-431.3, -298.35), (-431.3, -299.5), (-429.8, -299.5), (-428.3, -299.5), (-426.8, -299.5),
                 (-425.3, -299.5))


def _fc_stanchions(V, z):
    """Visual only (Mario walks through the belts: no thin invisible-looking collision walls in the queue)."""
    for (px, py) in FC_STANCHIONS:
        R.cyl(V, px, py, 0.15, z, z + 0.025, "int_ru_black", n=8)
        R.cyl(V, px, py, 0.028, z + 0.025, z + 0.95, "int_ru_black", n=5, top=False)
        R.cyl(V, px, py, 0.04, z + 0.95, z + 0.99, "int_ru_black", n=6, bottom=True)
    for (ax, ay), (bx, by) in zip(FC_STANCHIONS, FC_STANCHIONS[1:]):
        L = math.dist((ax, ay), (bx, by))
        ux, uy = (bx - ax) / L, (by - ay) / L
        a_ = (ax + ux * 0.045, ay + uy * 0.045)
        b_ = (bx - ux * 0.045, by - uy * 0.045)
        R.seg_box(V, a_, b_, 0.006, z + 0.86, z + 0.91, "int_ru_black", faces="side")


def _offset_open(path, d, simplify=1.0, arc_seg=4, chaikin=2):
    """Smooth outward (right-hand) offset of an open CCW polyline: tiny jogs dropped, convex corners rounded with
    arcs, concave ones mitred, then Chaikin corner cutting (end points kept) -> the curved soffit edge."""
    S = [path[0]]
    for p in path[1:-1]:
        if math.dist(p, S[-1]) >= simplify:
            S.append(p)
    if math.dist(path[-1], S[-1]) < simplify and len(S) > 1:
        S.pop()
    S.append(path[-1])
    segs = []
    for a, b in zip(S, S[1:]):
        L = math.dist(a, b)
        t = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
        segs.append((a, b, t, (t[1], -t[0])))
    out = [(segs[0][0][0] + segs[0][3][0] * d, segs[0][0][1] + segs[0][3][1] * d)]
    for (a0, b0, t0, n0), (a1, b1, t1, n1) in zip(segs, segs[1:]):
        v = b0
        cr = t0[0] * t1[1] - t0[1] * t1[0]
        if cr > 1e-6:      # left turn on a CCW outline: convex corner -> arc
            a_s, a_e = math.atan2(n0[1], n0[0]), math.atan2(n1[1], n1[0])
            while a_e < a_s:
                a_e += 2 * math.pi
            for k in range(arc_seg + 1):
                a_ = a_s + (a_e - a_s) * k / arc_seg
                out.append((v[0] + math.cos(a_) * d, v[1] + math.sin(a_) * d))
        else:              # concave / straight: mitre (intersection of the two offset lines)
            p0 = (a0[0] + n0[0] * d, a0[1] + n0[1] * d)
            p1 = (a1[0] + n1[0] * d, a1[1] + n1[1] * d)
            den = t0[0] * t1[1] - t0[1] * t1[0]
            if abs(den) < 1e-6:
                out.append((v[0] + n0[0] * d, v[1] + n0[1] * d))
            else:
                u = ((p1[0] - p0[0]) * t1[1] - (p1[1] - p0[1]) * t1[0]) / den
                out.append((p0[0] + t0[0] * u, p0[1] + t0[1] * u))
    a, b, t, n = segs[-1]
    out.append((b[0] + n[0] * d, b[1] + n[1] * d))
    for _ in range(chaikin):
        sm = [out[0]]
        for p, q in zip(out, out[1:]):
            sm.append((0.75 * p[0] + 0.25 * q[0], 0.75 * p[1] + 0.25 * q[1]))
            sm.append((0.25 * p[0] + 0.75 * q[0], 0.25 * p[1] + 0.75 * q[1]))
        sm.append(out[-1])
        out = sm
    clean = [out[0]]
    for p in out[1:]:
        if math.dist(p, clean[-1]) > 0.15:
            clean.append(p)
    return clean


def _fc_hall_poly(fc):
    """The food court overlay with its east side replaced by FC_HALL_EAST (the hall tile reaches the glass)."""
    i0 = min(range(len(fc)), key=lambda k: math.dist(fc[k], (-421.4, -326.9)))
    i1 = min(range(len(fc)), key=lambda k: math.dist(fc[k], (-399.0, -281.4)))
    out, k = [], i1
    while True:          # the overlay from the north-east corner round the west side to the south-east nook
        out.append(fc[k])
        if k == i0:
            break
        k = (k + 1) % len(fc)
    return R.ccw(out + FC_HALL_EAST)


def food_court(RZ):
    """Level 1 food court (ru_food_court_counter_2023, ru_food_court_sonic_2025, ru_starbucks_2017,
    ru_dining_windows, OSM food court outline w1315821081): the enclosed vendor block (servery) with its storefronts
    along the curved south front, the east face and the NE block, the tan / brown checker queue ring in front of the
    storefronts under a deep curved cream soffit, the white large-format tiled seating hall (to the glass) with white
    columns, wood + navy chairs, high-tops along the curved SE glass."""
    F = RZ.floors["L1"]
    z = F.z
    serv = F.zone("food_court_servery")
    P = K.Prop("food_court_misc")
    V, C = P.visual, P.collision
    fc = F.overlays.get("food_court")
    # seating-hall tile (overlay at the floor height over the OSM food court outline + the strip to the glass)
    if fc:
        R.floor_poly(V, _fc_hall_poly(fc), z - 0.01, "int_ru_fc_tile", step=FLOOR_STEP, holes=[serv.poly])
    # queue ring + soffit: one band in front of the storefront run, its outer edge a smooth curve (rounded corners
    # along the curved south front and round the NE block), FC_RING_DEPTH deep
    inner = _fc_front_path(serv.poly)
    outer = _offset_open(inner, FC_RING_DEPTH)
    band = inner + list(reversed(outer))
    ring_in = _offset_open(inner, 0.12, simplify=0.0, arc_seg=2, chaikin=0)   # clear of the kitchen floors
    R.floor_poly(V, ring_in + list(reversed(outer)), z, "int_ru_fc_checker", step=FLOOR_STEP)
    zs = z + FC_SOFFIT_Z
    # fix round 4 (fidelity-2; ru_food_court_sonic_2025): the cream soffit stops on the coffee / mac east face
    # (FC_SOFFIT_STOP_Y) and starts again round the NE block's east face: in front of the burger storefront the
    # lay-in troffer ceiling runs up to a shallow cream bulkhead over a floor-to-bulkhead navy wall (the 2.6 m
    # soffit band ran in front of it and tucked the storefront under a heavy cream band)
    soffits = _fc_soffit_runs(inner)
    for s_in in soffits:
        s_out = _offset_open(s_in, FC_RING_DEPTH)
        R.floor_poly(V, s_in + list(reversed(s_out)), zs, "int_ru_soffit", step=FLOOR_STEP, down=True, ao=0.95)
        for a, b in zip(s_out, s_out[1:]):
            R.quad_wall(V, a, b, zs, zs + 0.7, "int_ru_soffit", ao=0.9)
        R.quad_wall(V, s_in[0], s_out[0], zs, zs + 0.7, "int_ru_soffit", ao=0.9)
        R.quad_wall(V, s_out[-1], s_in[-1], zs, zs + 0.7, "int_ru_soffit", ao=0.9)
    soffit_polys = [s_in + list(reversed(_offset_open(s_in, FC_RING_DEPTH))) for s_in in soffits]
    _fc_sonic_wall(V, z)
    # downlights: two staggered rows along the soffit, every ~1.6 m (a warm light every fourth of the outer row)
    for s_in in soffits:
        for frac, start in ((0.62, 0.6), (0.25, 1.4)):
            mid = _offset_open(s_in, FC_RING_DEPTH * frac)
            acc, nxt, k = 0.0, start, (0 if frac > 0.5 else 2)
            for a, b in zip(mid, mid[1:]):
                L = math.dist(a, b)
                while acc + L >= nxt:
                    t = (nxt - acc) / L
                    mx, my = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
                    V.poly([(mx - 0.1, my - 0.1, zs - 0.01), (mx - 0.1, my + 0.1, zs - 0.01),
                            (mx + 0.1, my + 0.1, zs - 0.01), (mx + 0.1, my - 0.1, zs - 0.01)], "int_ru_led",
                           glow=True)
                    if k % 4 == 1 and frac > 0.5:
                        P.lights.append(K.Light((mx, my, zs - 0.4), radius=4.5, strength=0.22, color=LIGHT_WARM))
                    k += 1
                    nxt += 1.6
                acc += L
    # fidelity-2: black security-camera domes under the soffit over the south front (ru_food_court_counter_2023)
    cam_path = _offset_open(inner, 0.55)
    acc, nxt = 0.0, 1.2
    for a, b in zip(cam_path, cam_path[1:]):
        L = math.dist(a, b)
        while acc + L >= nxt and nxt < 18.0:
            t = (nxt - acc) / L
            R.cyl(V, a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, 0.09, zs - 0.11, zs - 0.005, "int_ru_black",
                  n=6, top=False, bottom=True)
            nxt += 2.3
        acc += L
    # the SW corner of the servery (ru_food_court_counter_2023, left edge): a lime wall with a sky-blue column
    # beside the first counter
    sw_a, sw_b = inner[0], inner[1]
    Ld = math.dist(sw_a, sw_b)
    if Ld > 1.2:
        cut = (sw_a[0] + (sw_b[0] - sw_a[0]) * (Ld - 0.7) / Ld, sw_a[1] + (sw_b[1] - sw_a[1]) * (Ld - 0.7) / Ld)
        _wall_strip(V, sw_a, cut, z + 0.12, zs, "int_ru_paint_lime", off=0.03)
        _wall_strip(V, cut, sw_b, z + 0.12, zs, "int_ru_paint_sky", off=0.06)
    # storefronts: the servery wall gets openings (build_floor reads RZ.storefront_holes) and a counter prop
    for i, (a, b, sign, back, side, sty) in enumerate(SERVERY_FRONTS):
        w = math.dist(a, b)
        cxm, cym = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        # the storefront faces OUT of the servery: right-hand normal of a -> b for a CCW outline is outward
        nx, ny = (b[1] - a[1]) / w, -(b[0] - a[0]) / w
        if R.pip((cxm + nx * 0.5, cym + ny * 0.5), serv.poly):
            nx, ny = -nx, -ny
        facing = math.degrees(math.atan2(nx, ny)) % 360.0
        RZ.kit_add(R.storefront(w, sign, back, side, h=FC_FRONT_H, style=VENDOR_STYLES.get(sty)), "L1", tag=f"storefront_{i}",
                   x=cxm, y=cym, z=z, facing=facing)
    _fc_stanchions(V, z)
    # seating: tables in the south hall, the east hall and along the curved glass
    # fidelity-2: the south hall's 7 x 4 grid of single tables (28 collision blocks) became rows of table pairs
    # pushed together (ru_food_court_counter_2023: the hall full of tables in rows): 5 pairs a row = 40 tables,
    # one merged collision block per pair (20 blocks: the collision budget)
    k = 0
    hall08 = F.zone("l1_corridor_08").poly
    # fix round 4 (fidelity-2; ru_food_court_counter_2023: open queue floor beside the counter run, tables only
    # further on): the rows start 3.5 m further south (was -316.0 .. -326.5)
    for yy in (-319.5, -323.0, -326.5, -330.0):
        for xx in (-451.0, -445.0, -439.0, -433.0, -427.0):
            if not all(R.pip((xx + sx * 1.375, yy + sy * 0.375), hall08) for sx in (-1, 1) for sy in (-1, 1)):
                continue
            for sgn in (-1, 1):
                RZ.kit_add(_nocol(R.cafe_table_set(chair_mat="int_ru_fabric_navy", frame="int_ru_wood_panel")), "L1",
                           tag=f"fc_table_{k}", x=xx + sgn * 1.0, y=yy, z=z, facing=0.0)
                k += 1
            K.col_box(C, xx - 1.375, yy - 0.375, z, xx + 1.375, yy + 0.375, z + 0.75, K.COL_NOCAM)
    for (xx, yy) in ((-420.0, -300.0), (-417.5, -306.0), (-420.0, -312.0), (-416.0, -292.5), (-414.6, -299.4)):
        RZ.kit_add(R.cafe_table_set(chair_mat="int_ru_fabric_navy", frame="int_ru_wood_panel"), "L1", tag=f"fc_table_{k}",
                   x=xx, y=yy, z=z, facing=15.0 * (k % 3))
        k += 1
    # high-tops along the inside of the curved SE glass (ru_dining_windows): 1.15 m in from the glass line
    for j, (xx, yy) in enumerate(((-413.41, -309.48), (-412.92, -303.48), (-410.4, -298.18), (-407.14, -294.03),
                                   (-403.81, -289.79), (-400.24, -285.25))):
        RZ.kit_add(R.high_top(), "L1", tag=f"fc_hightop_{j}", x=xx, y=yy, z=z)
    # white square columns of the hall (photo; positions inferred on an 8 m grid). fidelity-2: the south row moved
    # from y -320.5 to -321.1 (the chairs of the y -319.5 tables reached 0.1 m into them)
    cols_ = ((-446.0, -321.1), (-438.0, -321.1), (-430.0, -321.1), (-418.5, -296.0), (-418.5, -304.0))
    for (cx, cy) in cols_:
        V.box(cx - 0.3, cy - 0.3, z, cx + 0.3, cy + 0.3, z + F.clear, "int_ru_white", faces="+x-x+y-y")
        K.col_box(C, cx - 0.3, cy - 0.3, z, cx + 0.3, cy + 0.3, z + F.clear, K.COL)
    _fc_fidelity2(RZ, F, P, serv, fc, band, cols_, k, soffit_polys)
    # FOOD COURT sign over the queue ring (east)
    R.panel(V, (-424.0, -287.5), (-424.0, -283.0), z + 4.75, z + 5.35, "int_ru_sign_foodcourt", off=0.0, glow=True)
    RZ.kit_add(P, "L1", tag="food_court_misc")
    RZ.points.setdefault("food_court", {})["center"] = {"name": "interior_food_court_center", "p": [-438.0, -318.0, z],
                                                         "kind": "ground"}


DRESSERS.extend([food_court])

FC_BOOTH_YS = (-289.2, -291.35, -293.5, -295.65, -297.8, -299.95, -302.1, -304.25)   # west strip booth centres


def _fc_fidelity2(RZ, F, P, serv, fc, band, cols_, k, soffit_polys=None):
    """Fix round 2, fidelity-2 (ru_food_court_counter_2023, ru_food_court_booths_2016): a regular grid of glowing
    2 x 4 lay-in troffers over the seating hall, a run of orange booths under the west glass (the 4 m west strip),
    and more tables in the east hall between the NE block and the curved glass."""
    z = F.z
    V, C = P.visual, P.collision
    hall = F.zone("l1_corridor_08").poly
    hp = _fc_hall_poly(fc) if fc else hall
    zc = z + CLEAR["L1"] - 0.04
    # -- troffers: 0.6 x 1.2 m every 2.4 m (long axis east-west), clear of the soffit band, the servery, columns
    n_tr = 0
    for i in range(-24, 25):
        for j in range(-24, 25):
            x, y = -437.6 + i * 2.4, -317.6 + j * 2.4
            sp = soffit_polys or [band]        # fix round 4: troffers run up to the Sonic bulkhead (no soffit)
            if not (R.pip((x, y), hall) and R.pip((x, y), hp)) or R.pip((x, y), serv.poly) or \
                    any(R.pip((x, y), b_) for b_ in sp):
                continue
            if min(R.poly_dist((x, y), b_) for b_ in sp) < 0.9 or R.poly_dist((x, y), hall) < 0.9:
                continue
            if FC_BULK[0] - 0.7 < x < FC_BULK[1] + 0.7 and y > FC_BULK[2] - FC_BULK[3] - 0.65:
                continue
            if any(math.dist((x, y), c) < 1.0 for c in cols_):
                continue
            x0, x1, y0, y1 = x - 0.6, x + 0.6, y - 0.3, y + 0.3
            V.poly([(x0, y0, zc), (x0, y1, zc), (x1, y1, zc), (x1, y0, zc)], "int_ru_troffer",
                   uvs=[(0, 0), (0, 1), (1, 1), (1, 0)], glow=True)
            for a_, b_ in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
                R.quad_wall(V, b_, a_, zc, zc + 0.04, "int_ru_white")
            n_tr += 1
            if n_tr % 6 == 0:
                P.lights.append(K.Light((x, y, zc - 0.6), radius=5.0, strength=0.12, color=LIGHT_COOL))
    # -- booths under the west glass: the table ends against the wall, benches facing north / south
    wx = lambda y: -459.1 - 0.4 * (y + 282.0) / 45.7 + 0.17          # inside face of the west wall
    for j, yy in enumerate(FC_BOOTH_YS):
        RZ.kit_add(R.diner_booth(), "L1", tag=f"fc_booth_{j}", x=wx(yy), y=yy, z=z, facing=0.0)
    xb = max(wx(y_) for y_ in FC_BOOTH_YS)
    K.col_box(C, xb - 0.05, FC_BOOTH_YS[-1] - 1.05, z, xb + 1.25, FC_BOOTH_YS[0] + 1.05, z + 0.76, K.COL_NOCAM)
    # -- denser east hall: pairs of tables pushed together (6 chairs, one merged collision block per pair: the
    # collision budget) on a 3.0 x 4.4 m grid between the NE block's queue ring and the curved glass
    taken = [(-420.0, -300.0), (-417.5, -306.0), (-420.0, -312.0), (-416.0, -292.5), (-414.6, -299.4)]
    tops = [(-413.41, -309.48), (-412.92, -303.48), (-410.4, -298.18), (-407.14, -294.03), (-403.81, -289.79),
            (-400.24, -285.25)]
    doors = [((d[0] + d[2]) / 2, (d[1] + d[3]) / 2) for d in F.doors]

    def rect_d(c, p, hu, hv):          # distance from point p to the axis-aligned (u = y) rectangle at c
        dx = max(0.0, abs(p[0] - c[0]) - hv)
        dy = max(0.0, abs(p[1] - c[1]) - hu)
        return math.hypot(dx, dy)
    added = 0
    pairs = []
    for i in range(6):
        for j in range(10):
            x, y = -422.4 + i * 3.0, -318.6 + j * 4.4
            hu, hv = 1.85, 0.85
            corners = [(x + sx * hv, y + sy * hu) for sx in (-1, 1) for sy in (-1, 1)]
            if not all(R.pip(q, hall) and R.pip(q, hp) and not R.pip(q, serv.poly) and not R.pip(q, band)
                       for q in corners + [(x, y)]):
                continue
            if min(R.poly_dist(q, band) for q in corners) < 1.0 or min(R.poly_dist(q, hall) for q in corners) < 0.7:
                continue
            if any(rect_d((x, y), c, hu, hv) < 0.9 for c in cols_) or \
                    any(rect_d((x, y), t, hu, hv) < 1.5 for t in taken) or \
                    any(rect_d((x, y), t, hu, hv) < 1.3 for t in tops) or \
                    any(rect_d((x, y), d, hu, hv) < 1.8 for d in doors):
                continue
            if any(abs(x - px) < 2.6 and abs(y - py) < 4.2 for px, py in pairs):
                continue
            for sgn in (-1, 1):
                RZ.kit_add(_nocol(R.cafe_table_set(chair_mat="int_ru_fabric_navy", frame="int_ru_wood_panel")), "L1",
                           tag=f"fc_table_{k}", x=x, y=y + sgn * 1.0, z=z, facing=0.0)
                k += 1
            K.col_box(C, x - 0.375, y - 1.375, z, x + 0.375, y + 1.375, z + 0.75, K.COL_NOCAM)
            pairs.append((x, y))
            added += 2
            if len(pairs) >= 10:
                break
        if len(pairs) >= 10:
            break
    print(f"REITZ fidelity-2 food court: {n_tr} troffers, {added} east-hall tables, {len(FC_BOOTH_YS)} booths")


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
    walls with a darker dado, walnut doors (the plan's doors), then the upper wall: big drop-down screens (about twice
    the door height, from ~1.5 door heights up to just under the soffit) alternating with full bays of white 3-D
    triangular acoustic panels between white pilasters; a coffered ceiling with luminous fields inside a downlit
    perimeter soffit; the clerestory band on the EAST short end wall under a lowered end soffit (ru_os_grand_ballroom_3
    looks down the long axis with the stage on the right long wall and the lit window band on the far end wall; the
    compass end is not known from the photos, so the end that keeps that composition with the stage on the south
    wall is used); theatre rows facing the stage + podium on the south wall, banquet rounds at the back."""
    F = RZ.floors["L2"]
    z = F.z
    zn = F.zone("grand_ballroom")
    st = zn.style
    zc = z + st["clear"]
    P = K.Prop("grand_ballroom")
    V, C = P.visual, P.collision
    x0, y0, x1, y1 = R.bbox(zn.poly)
    zsof = z + GB_SOFFIT                # perimeter soffit (raised-panel coffers above it, up to zc)
    zend = z + GB_END_SOFFIT            # lowered end soffit over the clerestory (east end)
    zs0, zs1 = z + 3.9, z + 8.9         # screens: ~1.5 x .. ~3.4 x the 2.6 m door head
    sw = 7.0                            # screen width (16:10-ish, ru_os_grand_ballroom_1)
    xe = x1 - GB_END_D                  # west edge of the end soffit

    def pil(a, dx, dy, nx, ny, sk, ztop):
        px, py = a[0] + dx * sk, a[1] + dy * sk
        q0, q1 = (px - dx * 0.3, py - dy * 0.3), (px + dx * 0.3, py + dy * 0.3)
        R.seg_box(V, (q0[0] + nx * 0.12, q0[1] + ny * 0.12), (q1[0] + nx * 0.12, q1[1] + ny * 0.12), 0.12, z + 0.1, ztop,
                  "int_ru_white", faces="sideends")

    HB = _built_wall_index(RZ)
    for a, b in _room_inside_edges(zn, 0.11):
        L = math.dist(a, b)
        if L < 1.0:
            continue
        dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx, ny = dy, -dx
        mid_x, mid_y = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        east = mid_x > x1 - 1.0
        ztop = zend if east else zsof
        # fix round 5 (technical blocking 2): every layer on this wall moves out by sh so the slate band stands
        # 1.5 cm proud of the BUILT wall face (it lay 0.1 u off the grey wall: ~20-40 m2 of flicker on the north
        # wall; the acoustic / clerestory strips on the east wall likewise)
        sh = _strip_shift(HB, a, b, z + 0.1, ztop)
        a, b = (a[0] + nx * sh, a[1] + ny * sh), (b[0] + nx * sh, b[1] + ny * sh)
        _wall_strip(V, a, b, z + 0.1, z + 3.3, "int_ru_wall_slate", off=0.0)
        _wall_strip(V, a, b, z + 3.3, z + 3.4, "int_ru_white", off=0.01)
        screens = []
        if L > 20.0 and not east:
            gap = (L - 4 * sw) / 5.0
            slots = [gap * (k + 1) + sw * k for k in range(4)]
            use = (0, 1, 2, 3) if mid_y < y0 + 1.0 else (1, 2)       # stage (south) wall: four; north wall: two
            screens = [(slots[k], slots[k] + sw) for k in use]
        elif L > 12.0 and not east:
            screens = [(L / 2 - sw / 2, L / 2 + sw / 2)]               # west end: one screen
        for s0, s1 in screens:
            R.panel(V, (a[0] + dx * s0, a[1] + dy * s0), (a[0] + dx * s1, a[1] + dy * s1), zs0, zs1,
                    "int_ru_proj_screen", off=0.08)     # fix round 4 (technical): 0.2 u off the wall at 0.05
            sc = (s0 + s1) / 2
            P.lights.append(K.Light((a[0] + dx * sc + nx * 1.5, a[1] + dy * sc + ny * 1.5, z + 6.0), radius=6.0,
                                    strength=0.18, color=LIGHT_COOL))
        # pilasters at both edges of every screen, then every <= 4.6 m along the bays between them
        cuts = [(0.0, 0.0)] + screens + [(L, L)]
        piers = []
        for (p0, p1), (q0, q1) in zip(cuts, cuts[1:]):
            g0, g1 = p1 + (0.45 if p1 > 0.0 else 0.0), q0 - (0.45 if q0 < L else 0.0)
            if p1 > 0.0:
                piers.append(p1 + 0.3)
            if q0 < L:
                piers.append(q0 - 0.3)
            if g1 - g0 > 0.8:
                n = max(1, int(math.ceil((g1 - g0) / 4.6)))
                for k in range(1, n):
                    piers.append(g0 + (g1 - g0) * k / n)
        for sk in piers:
            if 0.3 < sk < L - 0.3:
                pil(a, dx, dy, nx, ny, sk, ztop)
        # acoustic bays: full height between the pilasters (no blank band up to the soffit)
        za0, za1 = z + 3.6, ztop - 0.02
        if east:
            za1 = z + 6.2                    # under the clerestory
        marks = sorted([0.0, L] + [m for s in screens for m in s] + piers)
        for m0, m1 in zip(marks, marks[1:]):
            if any(s0 - 0.01 <= (m0 + m1) / 2 <= s1 + 0.01 for s0, s1 in screens):
                continue
            g0, g1 = m0 + (0.3 if m0 > 0.0 else 0.15), m1 - (0.3 if m1 < L else 0.15)
            if g1 - g0 > 0.5:
                _wall_strip(V, (a[0] + dx * g0, a[1] + dy * g0), (a[0] + dx * g1, a[1] + dy * g1), za0, za1,
                            "int_ru_acoustic", off=0.04)
        if east:
            # the clerestory band (ru_os_grand_ballroom_3): lit glazing under the lowered end soffit
            ca, cb = (a[0] + dx * 0.4, a[1] + dy * 0.4), (b[0] - dx * 0.4, b[1] - dy * 0.4)
            _wall_strip(V, ca, cb, z + 6.2, z + 6.5, "int_ru_white", off=0.03)
            _wall_strip(V, ca, cb, z + 6.5, z + 8.0, "int_ru_window_view", off=0.03, glow=True)
            _wall_strip(V, ca, cb, z + 8.0, zend - 0.02, "int_ru_white", off=0.03)
            mullions(V, (ca[0] + nx * 0.05, ca[1] + ny * 0.05), (cb[0] + nx * 0.05, cb[1] + ny * 0.05), z + 6.5, z + 8.0,
                     bay=1.8, t=0.05)
    # stage + podium (south wall, centre) and theatre rows facing it
    cxs = (x0 + x1) / 2
    RZ.kit_add(R.stage_platform(9.0, 3.2, h=0.6), "L2", tag="gb_stage", x=cxs, y=y0 + 2.0, z=z, facing=0.0)
    # fidelity-4 r2: the podium stands centre-front on the stage, on the axis of the wide centre aisle
    # (ru_os_grand_ballroom_1); 0.75 m clear of the stage coin line at y0 + 2.0
    RZ.kit_add(R.podium(), "L2", tag="gb_podium", x=cxs, y=y0 + 3.0, z=z + 0.6, facing=0.0)
    # design pass: 2.0 m aisles (ru_os_grand_ballroom_1 / _2 show clear aisles) with one collision box per seat
    # block, so the aisles are walkable floor up to the stage (the rows were one 0.46 m slab)
    # fidelity-4 r2: two blocks of 15 with a 3.2 m centre aisle running to the podium (ru_os_grand_ballroom_1; was 3
    # blocks of 10, a block in front of the podium)
    RZ.kit_add(R.chair_rows(14, 30, pitch=0.95, aisle_every=15, aisle_w=GB_CENTRE_AISLE, kind="navy", col_blocks=True),
               "L2",
               tag="gb_rows", x=cxs, y=y0 + 5.6, z=z, facing=180.0)
    EXTRA_PICKUPS.append({"kind": "coin_line", "name": "grand ballroom stage coins", "pos": (cxs - 0.9, y0 + 2.0, z + 0.6),
                          "facing": 90.0})
    # banquet rounds in the back third (photo 3 / 4 mix)
    for i, xx in enumerate((-506.0, -501.5, -475.5, -471.0)):
        for j, yy in enumerate((-254.0, -258.5)):
            RZ.kit_add(R.round_table(0.9, top="int_ru_drape"), "L2", tag=f"gb_round_{i}_{j}", x=xx, y=yy, z=z)
    # ceiling: perimeter soffit (zsof) and the lowered east end soffit (zend), both clipped to the room; 2 x 4
    # luminous coffers at zc inside
    inner = (x0 + 2.4, y0 + 2.4, xe, y1 - 2.4)
    inset = R.offset_poly(zn.poly, -0.1)
    pieces = R.grid_pieces(R.triangulate(inset), 4.0)
    inner_poly = [(inner[0], inner[1]), (inner[2], inner[1]), (inner[2], inner[3]), (inner[0], inner[3])]
    end_poly = [(xe, y0 - 2.0), (x1 + 2.0, y0 - 2.0), (x1 + 2.0, y1 + 2.0), (xe, y1 + 2.0)]
    for pc in R.subtract(pieces, [inner_poly, end_poly]):
        V.poly([(x, y, zsof) for x, y in reversed(R.ccw(pc))], "int_ru_white", ao=0.95)
    for pc in pieces:
        q = R.clip_convex(pc, xe, y0 - 2.0, x1 + 2.0, y1 + 2.0)
        if q and len(q) >= 3 and abs(R.signed_area(q)) > 1e-4:
            V.poly([(x, y, zend) for x, y in reversed(R.ccw(q))], "int_ru_white", ao=0.95)
    for (ax, ay), (bx_, by_) in R.edges([(inner[0], inner[1]), (inner[2], inner[1]), (inner[2], inner[3]), (inner[0], inner[3])]):
        R.quad_wall(V, (ax, ay), (bx_, by_), zsof, zc, "int_ru_white", ao=0.9)
    # the step from the end soffit up to the perimeter soffit, facing west
    ylo = max(p[1] for p in inset if p[1] < (y0 + y1) / 2) + 0.05
    yhi = min(p[1] for p in inset if p[1] > (y0 + y1) / 2) - 0.05
    R.quad_wall(V, (xe, ylo), (xe, yhi), zend, zsof, "int_ru_white", ao=0.9)
    ncx, ncy = 4, 2
    bw = 0.8
    cw_ = (inner[2] - inner[0] - (ncx + 1) * bw) / ncx
    ch_ = (inner[3] - inner[1] - (ncy + 1) * bw) / ncy
    for i in range(ncx):
        for j in range(ncy):
            ax = inner[0] + bw + i * (cw_ + bw)
            ay = inner[1] + bw + j * (ch_ + bw)
            # fix round 2 (blocking): the coffers sat exactly on the shell's tile ceiling (z-fight); they hang 0.1 m
            # below it now, still recessed 0.4 m between the 0.5 m beams
            zcf = zc - 0.10
            V.poly([(ax, ay, zcf), (ax, ay + ch_, zcf), (ax + cw_, ay + ch_, zcf), (ax + cw_, ay, zcf)], "int_ru_coffer",
                   uvs=[(0, 0), (0, ch_ / 1.2), (cw_ / 1.2, ch_ / 1.2), (cw_ / 1.2, 0)], glow=True)
            P.lights.append(K.Light((ax + cw_ / 2, ay + ch_ / 2, zc - 2.0), radius=12.0, strength=0.30, color=LIGHT_COOL))
    # beams between coffers (dropped 0.5 m)
    for i in range(ncx + 1):
        bx0 = inner[0] + i * (cw_ + bw)
        V.box(bx0, inner[1], zc - 0.5, bx0 + bw, inner[3], zc, "int_ru_white", faces="+x-x-z")
    for j in range(ncy + 1):
        by0 = inner[1] + j * (ch_ + bw)
        V.box(inner[0], by0, zc - 0.5, inner[2], by0 + bw, zc, "int_ru_white", faces="+y-y-z")
    # soffit downlights (long sides), two rows on the end soffit

    def dl(px, py, zz, warm=True):
        V.poly([(px - 0.12, py - 0.12, zz - 0.01), (px - 0.12, py + 0.12, zz - 0.01), (px + 0.12, py + 0.12, zz - 0.01),
                (px + 0.12, py - 0.12, zz - 0.01)], "int_ru_led", glow=True)
        P.lights.append(K.Light((px, py, zz - 0.5), radius=6.0, strength=0.18, color=LIGHT_WARM if warm else LIGHT_COOL))
    for k in range(16):
        t = (k + 0.5) / 16.0
        for py in (y0 + 1.2, y1 - 1.2):
            dl(x0 + 1.2 + (xe - x0 - 1.6) * t, py, zsof)
    for k in range(9):
        py = y0 + 1.6 + (y1 - y0 - 3.2) * k / 8.0
        for px in (x1 - 1.3, x1 - 3.0):
            dl(px, py, zend)
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
        dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx, ny = dy, -dx
        # narrow dark-grey vertical panels (ru_os_rion_ballroom: ~0.6 m wide, ~2 m apart)
        n = int(L / 2.0)
        for k in range(1, n):
            sk = L * k / n
            p0 = (a[0] + dx * (sk - 0.3), a[1] + dy * (sk - 0.3))
            p1 = (a[0] + dx * (sk + 0.3), a[1] + dy * (sk + 0.3))
            _wall_strip(V, p0, p1, z + 0.6, zc - 0.9, "int_ru_wall_slate", off=0.03)
        # light cove along the top of every wall: a white lip with a glowing strip under it, washing the wall
        _wall_strip(V, a, b, zc - 0.62, zc - 0.5, "int_ru_led", off=0.05, glow=True)
        _wall_strip(V, a, b, zc - 0.5, zc - 0.02, "int_ru_white", off=0.06)
        for k in range(max(1, int(L / 7.0))):
            sk = L * (k + 0.5) / max(1, int(L / 7.0))
            P.lights.append(K.Light((a[0] + dx * sk + nx * 0.6, a[1] + dy * sk + ny * 0.6, zc - 1.2), radius=5.0,
                                    strength=0.14, color=LIGHT_WARM))
    # dark red-brown (mahogany) wood beams across the ceiling (N-S): fidelity-4 round 2, 7 beams about 4.2 m apart
    # (was 11 cedar beams at 2.8 m: a striped wood ceiling); ru_os_rion_ballroom: few dark beams, the white tile
    # ceiling and its rows of round downlights dominate. A linear LED line runs mid-bay in every other bay.
    nb = 8
    for k in range(1, nb):
        bx = x0 + (x1 - x0) * k / nb
        V.box(bx - 0.2, y0, zc - 0.45, bx + 0.2, y1, zc, "int_ru_mahogany", faces="+x-x-z")
        if k < nb - 1 and k % 2 == 1:
            lx = bx + (x1 - x0) / nb / 2
            V.box(lx - 0.05, y0 + 1.2, zc - 0.08, lx + 0.05, y1 - 1.2, zc - 0.02, "int_ru_led", faces="-z+x-x", glow=True)
            P.lights.append(K.Light((lx, (y0 + y1) / 2, zc - 1.5), radius=10.0, strength=0.22, color=LIGHT_COOL))
    # fidelity-4 r2: a wider stage with a 4 m black drape that stands clear of the south wall (the drape sat at the
    # wall line, hidden), the first row 2.4 m off the stage; the rows fill the floor in three blocks
    # (ru_os_rion_ballroom; was 12 x 24 in two), one low collision box as before
    RZ.kit_add(R.stage_platform(8.0, 2.6, h=0.5, drape_h=4.0), "L3", tag="rion_stage", x=(x0 + x1) / 2, y=y0 + 2.0,
               z=z, facing=0.0)
    # fix round 4 (fidelity-4 pass): dark navy pads in cherry frames (ru_os_rion_ballroom; were royal-blue banquet)
    RZ.kit_add(R.chair_rows(16, 36, pitch=0.95, aisle_every=12, aisle_w=1.6, kind="rion"), "L3", tag="rion_rows",
               x=(x0 + x1) / 2, y=y0 + 5.7, z=z, facing=180.0)
    RZ.kit_add(P, "L3", tag="rion")
    RZ.lights_skip.add("rion_ballroom")
    RZ.points.setdefault("ballrooms", {})["rion"] = {"name": "interior_rion_ballroom", "p": [(x0 + x1) / 2, y1 - 3.0, z],
                                                      "kind": "ground"}


def _span_y(poly, x):
    """The y extent of a polygon along the vertical line at x (None if it misses)."""
    ys = []
    for (ax, ay), (bx, by) in zip(poly, poly[1:] + poly[:1]):
        if (ax - x) * (bx - x) <= 0 and abs(bx - ax) > 1e-9:
            ys.append(ay + (by - ay) * (x - ax) / (bx - ax))
    return (min(ys), max(ys)) if len(ys) >= 2 else None


AUD_CROSS_ROW = 6        # fix round 5 (fidelity-4): the row left out as the railed cross aisle (6 front rows, 4 rear)


def auditorium(RZ):
    """Auditorium (L2, 299 seats; ru_os_auditorium_1..3): honey-wood seat shells (navy fabric) in continuous rows
    with side aisles on a raked floor, a railed cross-aisle in front of the first row, the screen between navy
    pilasters on the end wall, honey-wood panel blocks with exit doors either side, light-grey side walls with tall
    wood panels, a dark slat ceiling crossed by thick bright LED coves. The screen is on the west end wall
    (inferred from the plan: the angled stage walls)."""
    F = RZ.floors["L2"]
    z = F.z
    zn = F.zone("auditorium")
    zc = z + zn.style["clear"]
    P = K.Prop("auditorium")
    V, C = P.visual, P.collision
    x0, y0, x1, y1 = R.bbox(zn.poly)
    inset = R.offset_poly(zn.poly, -0.15)
    # stage at the west end + screen between navy pilasters (the straight end wall y -254.2 .. -249.0)
    V.box(x0 + 0.3, y0 + 3.0, z, x0 + 3.2, y1 - 3.0, z + 0.7, "int_ru_black", faces="+x+y-y+z",
          mats={"+z": "int_ru_wood_panel"})
    C.prism([(x0 + 0.3, y0 + 3.0), (x0 + 3.2, y0 + 3.0), (x0 + 3.2, y1 - 3.0), (x0 + 0.3, y1 - 3.0)], z, z + 0.7, K.COL,
            top=K.COL)
    sp = _span_y(zn.poly, x0 + 0.2) or (y0 + 4.0, y1 - 4.0)
    # fix round 4 (fidelity-4 pass; ru_os_auditorium_2/3): the screen fills the bay between slimmer navy pilasters,
    # nearly down to the stage and nearly square (was 3.8 x 3.0 m at z+1.5, navy showing below it)
    ys0, ys1 = sp[0] + 0.47, sp[1] - 0.47
    sz0 = z + 0.95
    sz1 = min(zc - 0.6, sz0 + (ys1 - ys0) * 0.92)
    # fix round 5 (fidelity-4, improvement 5b; ru_os_auditorium_1..3): no black border (the texture's frame texels
    # are cropped off): the screen fills the bay edge to edge
    R.panel(V, (x0 + 0.45, ys0), (x0 + 0.45, ys1), sz0, sz1, "int_ru_proj_screen", off=0.0, u0=0.07, u1=0.93,
            v0=0.08, v1=0.92)
    for yy in (sp[0] + 0.22, sp[1] - 0.22):
        V.box(x0 + 0.05, yy - 0.22, z + 0.7, x0 + 0.55, yy + 0.22, zc - 0.25, "int_ru_wall_navy", faces="+x+y-y")
    # screen wall navy, the angled walls beside it honey-wood panel blocks with an exit door each, the long side
    # walls light grey with tall wood panels at intervals (ru_os_auditorium_1..3)
    for a, b in _room_inside_edges(zn, 0.11):
        L = math.dist(a, b)
        if L < 0.6:
            continue
        mx = (a[0] + b[0]) / 2
        dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        if mx < x0 + 2.5:
            if L > 4.5:
                _wall_strip(V, a, b, z + 0.1, zc - 0.3, "int_ru_wall_navy", off=0.02)
            else:
                # fix round 5 (fidelity-4 blocking): 1.5 cm nearer the wall (at 0.02 the strip lay 0.5 mm behind the
                # plan door leaf on the north stage-end wall and z-fought with it)
                _wall_strip(V, a, b, z + 0.1, zc - 0.3, "int_ru_wood_panel", off=0.005)
                if L > 2.4:
                    # the honey-wood block: proud of the wall, an exit door + EXIT sign on its outer half
                    nx, ny = dy, -dx
                    R.panel(V, a, b, z + 0.1, z + 3.4, "int_ru_wood_panel", off=0.12)
                    side = 0.72 if (a[1] + b[1]) / 2 > (y0 + y1) / 2 else 0.28
                    sc = L * side
                    # fix round 5 (fidelity-4 blocking): the leaves stand 0.17 off the wall line (8 cm proud of the
                    # block): at 0.13 the north leaf lay 0.5 mm off the next short wall's wood strip and z-fought
                    da = (a[0] + dx * (sc - 0.5) + nx * 0.17, a[1] + dy * (sc - 0.5) + ny * 0.17)
                    db = (a[0] + dx * (sc + 0.5) + nx * 0.17, a[1] + dy * (sc + 0.5) + ny * 0.17)
                    door_leaves(V, da, db, z, 2.3, "int_ru_door")
                    R.panel(V, (a[0] + dx * (sc - 0.21), a[1] + dy * (sc - 0.21)),
                            (a[0] + dx * (sc + 0.21), a[1] + dy * (sc + 0.21)), z + 2.5, z + 2.7, "int_ru_exit",
                            off=0.16, glow=True, v0=0.28, v1=0.72)
        elif L > 8.0:
            # fix round 5 (fidelity-4, improvement 5d; ru_os_auditorium_1..3): narrow vertical honey-wood strips
            # down the long side walls (were 1.2 m panels every 6 m, which read as plain grey), clear of the doors
            ad_ = [dm for _da, _db, dm, _dn in _room_doors(F, zn)]
            n_ = int(L / 1.6)
            for k in range(1, n_):
                sk = L * k / n_
                q_ = (a[0] + dx * sk, a[1] + dy * sk)
                if any(math.dist(q_, dm) < 1.0 for dm in ad_):
                    continue
                _wall_strip(V, (q_[0] - dx * 0.13, q_[1] - dy * 0.13), (q_[0] + dx * 0.13, q_[1] + dy * 0.13),
                            z + 0.1, zc - 0.6, "int_ru_wood_panel", off=0.03)
    # raked seating: rows step up 0.18 m toward the east; continuous rows (no centre aisle), side aisles >= 1.2 m,
    # each row as wide as the room allows at its depth (the north-east corner is cut on the diagonal)
    nrows = 11
    row_d = (x1 - x0 - 6.0) / nrows
    for r in range(nrows):
        rx0 = x0 + 5.0 + r * row_d
        zr = z + 0.18 * r
        if r > 0:
            # fix round 4 (technical blocking): the last riser's back (+x) and every row's ends (+-y) are rendered
            # (the collision back face was an invisible 1.9 m wall seen from the Gallery door)
            V.box(rx0, y0 + 0.8, z, rx0 + row_d, y1 - 0.8, zr, "int_ru_carpet_aud",
                  faces="+z-x+y-y" + ("+x" if r == nrows - 1 else ""),
                  mats={"-x": "int_ru_wall_navy", "+x": "int_ru_wall_navy", "+y": "int_ru_wall_navy",
                        "-y": "int_ru_wall_navy"})
        spans = [_span_y(inset, xx) for xx in (rx0 + 0.15, rx0 + 0.75, rx0 + 1.2)]
        spans = [sp_ for sp_ in spans if sp_]
        if not spans:
            continue
        ylo, yhi = max(sp_[0] for sp_ in spans), min(sp_[1] for sp_ in spans)
        seats = int((yhi - ylo - 2 * 1.3) / 0.5)
        if seats < 4:
            continue
        if r == AUD_CROSS_ROW:
            # fix round 5 (fidelity-4, improvement 5a; ru_os_auditorium_1..3): a cross aisle between the front and
            # rear sections, a steel pipe rail on its rear (upper) edge, open at the side aisles
            xr_ = rx0 + row_d - 0.06
            zr_ = zr
            V.box(xr_ - 0.03, ylo + 0.2, zr_ + 0.92, xr_ + 0.03, yhi - 0.2, zr_ + 0.98, "int_ru_steel",
                  faces="+x-x+y-y+z-z")
            npost = max(2, int((yhi - ylo - 0.4) / 1.8) + 1)
            for k in range(npost):
                yp_ = ylo + 0.2 + (yhi - ylo - 0.4) * k / (npost - 1)
                yp_ = min(max(yp_, ylo + 0.23), yhi - 0.23)
                V.box(xr_ - 0.025, yp_ - 0.025, zr_, xr_ + 0.025, yp_ + 0.025, zr_ + 0.92, "int_ru_steel",
                      faces="+x-x+y-y")
            C.poly([(xr_ + 0.03, ylo + 0.2, zr_), (xr_ + 0.03, yhi - 0.2, zr_), (xr_ + 0.03, yhi - 0.2, zr_ + 0.98),
                    (xr_ + 0.03, ylo + 0.2, zr_ + 0.98)], K.COL_NOCAM)
            C.poly([(xr_ - 0.03, yhi - 0.2, zr_), (xr_ - 0.03, ylo + 0.2, zr_), (xr_ - 0.03, ylo + 0.2, zr_ + 0.98),
                    (xr_ - 0.03, yhi - 0.2, zr_ + 0.98)], K.COL_NOCAM)
            continue
        rows = R.chair_rows(1, seats, pitch=row_d, aisle_every=0, kind="aud", seat_h=0.44)
        RZ.kit_add(rows, "L2", tag=f"aud_row_{r}", x=rx0 + 0.75, y=(ylo + yhi) / 2, z=zr, facing=270.0)
    # rake collision: one ramp through the middle of every step top (+-9 cm at the step edges; SM64 practice for
    # stairs), its back and side faces (fidelity-4: was a prism per step, ~90 tris more)
    xa, xb = x0 + 5.0 + row_d, x0 + 5.0 + nrows * row_d
    ya_, yb_ = y0 + 0.8, y1 - 0.8
    za_, zb_ = z + 0.09, z + 0.18 * (nrows - 0.5)
    C.poly([(xa, ya_, za_), (xb, ya_, zb_), (xb, yb_, zb_), (xa, yb_, za_)], K.COL)
    C.poly([(xb, ya_, z), (xb, yb_, z), (xb, yb_, zb_), (xb, ya_, zb_)], K.COL)
    C.poly([(xa, ya_, z), (xb, ya_, z), (xb, ya_, zb_), (xa, ya_, za_)], K.COL)
    C.poly([(xa, yb_, z), (xa, yb_, za_), (xb, yb_, zb_), (xb, yb_, z)], K.COL)
    # fix round 4 (technical blocking): the Gallery door (-431.9, -249.8..-248.9) opens onto the 1 m strip behind
    # the top row: a carpeted stair climbs south along the back wall to the top row (0.18 m risers), so the rake
    # is walkable from its only public door (it was walled off by the 1.9 m back face)
    xs0, xs1 = xb, x1 - 0.02
    yd = -249.85
    nst = nrows - 1
    rise = (zb_ - z) / (nst + 0.5)
    tread = 0.52
    for k in range(nst):
        yk1, yk0 = yd - k * tread, yd - (k + 1) * tread
        V.box(xs0, yk0, z, xs1, yk1, z + rise * (k + 1), "int_ru_carpet_aud", faces="+z+y",
              mats={"+y": "int_ru_wall_navy"})
    yt = yd - nst * tread
    ye = _span_y(zn.poly, x1 - 0.5)
    ye = (ye[0] + 0.15) if ye else yt - 0.5
    V.box(xs0, ye, z, xs1, yt, zb_ - rise * 0.5, "int_ru_carpet_aud", faces="+z")
    C.poly([(xs0, yd, z + rise * 0.5), (xs0, yt, zb_ - rise * 0.5), (xs1, yt, zb_ - rise * 0.5),
            (xs1, yd, z + rise * 0.5)], K.COL)
    C.poly([(xs0, yt, zb_ - rise * 0.5), (xs0, ye - 0.1, zb_ - rise * 0.5), (xs1, ye - 0.1, zb_ - rise * 0.5),
            (xs1, yt, zb_ - rise * 0.5)], K.COL)
    # a rail along the top row's back edge north of the stair (the drop into the strip by the door)
    V.box(xb - 0.05, yd + 0.05, zb_ - 0.09, xb + 0.0, yb_ - 0.1, zb_ + 0.9, "int_ru_wood_panel", faces="+x-x+z+y-y")
    C.poly([(xb - 0.05, yb_, zb_ - 0.2), (xb - 0.05, yd, zb_ - 0.2), (xb - 0.05, yd, zb_ + 0.98),
            (xb - 0.05, yb_, zb_ + 0.98)], K.COL_NOCAM)
    # the railed cross-aisle in front of the first row: a navy parapet with a honey-wood cap, open at both ends
    xr = x0 + 4.55
    spr = _span_y(inset, xr)
    if spr:
        ya, yb = spr[0] + 1.3, spr[1] - 1.3
        V.box(xr - 0.08, ya, z, xr + 0.08, yb, z + 0.9, "int_ru_wall_navy", faces="+x-x+y-y")
        V.box(xr - 0.11, ya - 0.03, z + 0.9, xr + 0.11, yb + 0.03, z + 0.98, "int_ru_wood_panel", faces="+x-x+y-y+z")
        C.poly([(xr + 0.11, ya, z), (xr + 0.11, yb, z), (xr + 0.11, yb, z + 0.98), (xr + 0.11, ya, z + 0.98)], K.COL_NOCAM)
        C.poly([(xr - 0.11, yb, z), (xr - 0.11, ya, z), (xr - 0.11, ya, z + 0.98), (xr - 0.11, yb, z + 0.98)], K.COL_NOCAM)
    # ceiling: dark slat field (zone ceiling int_ru_slat_dark) crossed by thick bright LED coves, each in a dark lip
    for k in range(1, 7):
        cx_ = x0 + (x1 - x0) * k / 7
        spc = _span_y(inset, cx_)
        if not spc:
            continue
        ya, yb = spc[0] + 0.4, spc[1] - 0.4
        V.box(cx_ - 0.36, ya, zc - 0.32, cx_ + 0.36, yb, zc - 0.26, "int_ru_led", faces="-z", glow=True)
        V.box(cx_ - 0.42, ya, zc - 0.36, cx_ - 0.36, yb, zc, "int_ru_black", faces="-x-z")
        V.box(cx_ + 0.36, ya, zc - 0.36, cx_ + 0.42, yb, zc, "int_ru_black", faces="+x-z")
        # fix round 5 (fidelity-4, improvement 5c): dimmer coves (0.30; median luminance 48-59 vs the photos' 18-30)
        P.lights.append(K.Light((cx_, (ya + yb) / 2, zc - 0.9), radius=9.0, strength=0.24, color=LIGHT_WARM))
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
    # in front of the wall face (the plan line + WALL_T / 2 is not parallel to the zone edge: ~1.5 cm slant)
    # fidelity-3 (round 2; ru_os_chamber): ONE once-mapped cherry feature wall (three courses of large panels, a
    # broad chevron of diagonal reveals) up to the dropped ceiling, instead of a tiled 0.6 m zigzag
    zc_ = z + zn.style.get("ceil_h", zn.style["clear"])
    R.panel(V, _on_north(xa), _on_north(xb), z + 0.1, zc_ - 0.05, "int_ru_chevron", off=0.10)
    V.box(cx_ - 5.0, y1 - 3.6, z, cx_ + 5.0, y1 - 0.2, z + 0.45, "int_ru_cherry", faces="+x-x-y+z",
          mats={"+z": "int_ru_carpet_chamber"})
    C.prism([(cx_ - 5.0, y1 - 3.6), (cx_ + 5.0, y1 - 3.6), (cx_ + 5.0, y1 - 0.2), (cx_ - 5.0, y1 - 0.2)], z, z + 0.45,
            K.COL, top=K.COL)
    # the dais desk: a plain cherry front with a dark kick strip and a grey top; the photo's small navy
    # UF FLORIDA plaques (int_ru_dais, the plaque cropped by UVs) instead of the big UF roundel
    V.box(cx_ - 3.5, y1 - 3.3, z + 0.45, cx_ + 3.5, y1 - 2.6, z + 1.5, "int_ru_cherry", faces="-y+x-x+z",
          mats={"+z": "int_ru_wall_grey"})
    V.box(cx_ - 3.48, y1 - 3.31, z + 0.45, cx_ + 3.48, y1 - 3.3, z + 0.55, "int_ru_black", faces="-y")
    for px_ in (cx_ - 1.6, cx_ + 1.6):
        R.panel(V, (px_ - 0.32, y1 - 3.3), (px_ + 0.32, y1 - 3.3), z + 1.08, z + 1.24, "int_ru_dais", off=0.012,
                u0=10 / 64, u1=54 / 64, v0=(31 - 18) / 32, v1=(32 - 8) / 32)
    K.col_box(C, cx_ - 3.5, y1 - 3.3, z + 0.45, cx_ + 3.5, y1 - 2.6, z + 1.5, K.COL_NOCAM, bottom=True)
    # the two cherry podiums at the dais ends with the UF FLORIDA plaque (ru_os_chamber)
    for px_ in (cx_ - 4.2, cx_ + 4.2):
        RZ.kit_add(R.podium(), "G", tag=f"senate_podium_{'w' if px_ < cx_ else 'e'}", x=px_, y=y1 - 3.0, z=z + 0.45,
                   facing=180.0)
    # ru_os_chamber: the US flag at the left end of the cherry panel (seen from the seats: west), Florida's at the
    # right (east)
    for fx, (u0, u1) in ((cx_ - 4.4, (0.0, 0.47)), (cx_ + 4.4, (0.53, 1.0))):
        V.box(fx - 0.03, y1 - 0.9, z + 0.45, fx + 0.03, y1 - 0.84, z + 3.0, "int_ru_steel", faces="+x-x+y-y")
        V.poly([(fx, y1 - 0.88, z + 2.0), (fx + 0.9, y1 - 0.88, z + 2.0), (fx + 0.9, y1 - 0.88, z + 2.9), (fx, y1 - 0.88, z + 2.9)],
               "int_ru_flags", uvs=[(u0, 0), (u1, 0), (u1, 1), (u0, 1)], normal_hint=(0, -1, 0))
    # ru_os_chamber: 7 curved rows of desks filling the room to ~3 m from the back wall; each row's arc is clamped to
    # 9.6 m either side of the centre line (the side walls are 10.3 m away)
    RZ.kit_add(R.senate_tiers(7, r0=6.0, dr=1.25, a0=-50.0, a1=50.0, rise=0.15, seg=8, half_w=9.6), "G",
               tag="senate_tiers", x=cx_, y=y1 - 1.5, z=z, facing=180.0)
    _ceiling_projector(V, P, cx_, y1 - 9.5, zc_, (0.0, -1.0))
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


def _room_doors(F, zn, tol=0.4):
    """The plan doors on a room's boundary: [(a, b, mid, inward unit normal)]."""
    out = []
    for d in F.doors:
        a, b = (d[0], d[1]), (d[2], d[3])
        L = math.dist(a, b)
        if L < 0.3:
            continue
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        if R.poly_dist(mid, zn.poly) > tol:
            continue
        nx, ny = -(b[1] - a[1]) / L, (b[0] - a[0]) / L
        if not R.pip((mid[0] + nx * 0.5, mid[1] + ny * 0.5), zn.poly):
            nx, ny = -nx, -ny
            if not R.pip((mid[0] + nx * 0.5, mid[1] + ny * 0.5), zn.poly):
                continue
        out.append((a, b, mid, (nx, ny)))
    return out


def _meeting_walls(F, zn, V, fx, fy, upstairs=False):
    """Ground meeting rooms (ru_os_g310_g320, ru_os_g330): white raised-panel wainscot under the chair rail on the
    white walls, a row of small framed prints on the long interior side walls, EXIT signs over the doors.
    upstairs (L2 / L3: ru_os_3315_3320, ru_os_2355_2365): no wainscot; a row of larger framed photos / art."""
    z = F.z
    doors = _room_doors(F, zn)
    aw = zn.style.get("accent_wall")
    nprint = 0
    # fix round 4 (fidelity-4 pass, improvement 1): upstairs the art follows the room photos, per room (None: bare
    # white walls, as in ru_os_3305 / 2315_2330 / 2335_2340 / 2360)
    pmode = UPSTAIRS_PRINTS.get(zn.id) if upstairs else "all"
    side_cands = []
    for a, b in R.edges(list(reversed(R.ccw(zn.poly)))):
        L = math.dist(a, b)
        if L < 1.0:
            continue
        dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx, ny = dy, -dx                        # right of a -> b = into the room (CW order)
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        is_front = False
        if aw is not None:
            La = max(1e-6, math.dist(*aw))
            par = abs(dx * (aw[1][0] - aw[0][0]) + dy * (aw[1][1] - aw[0][1])) / La
            if par > 0.9 and R.seg_point_dist(mid, aw[0], aw[1]) < 0.35:
                if pmode != "front_row":
                    continue                    # the blue accent wall itself
                is_front = True
        outside = F.cls_at((mid[0] - nx * 0.45, mid[1] - ny * 0.45))[0]
        face = (EXT_T if outside == "O" else WALL_T) / 2 + 0.015
        gaps = []
        for da, db, dm, dn in doors:
            if abs((dm[0] - a[0]) * nx + (dm[1] - a[1]) * ny) > 0.35:
                continue
            s0 = (da[0] - a[0]) * dx + (da[1] - a[1]) * dy
            s1 = (db[0] - a[0]) * dx + (db[1] - a[1]) * dy
            if max(s0, s1) < -0.2 or min(s0, s1) > L + 0.2:
                continue
            gaps.append((min(s0, s1) - 0.15, max(s0, s1) + 0.15))
        spans = [(0.15, L - 0.15)]
        for g0, g1 in sorted(gaps):
            nxt = []
            for s0, s1 in spans:
                if g1 <= s0 or g0 >= s1:
                    nxt.append((s0, s1))
                    continue
                if g0 > s0:
                    nxt.append((s0, g0))
                if g1 < s1:
                    nxt.append((g1, s1))
            spans = nxt

        def P(s_, a=a, dx=dx, dy=dy, nx=nx, ny=ny, face=face):
            return (a[0] + dx * s_ + nx * face, a[1] + dy * s_ + ny * face)
        if is_front:
            # ru_os_3315_3320: one row of ~11 small black-framed photos along the white front wall, between and
            # beside the two doors (int_ru_prints cells: dark frame, white mat)
            slots = []
            for s0, s1 in spans:
                n = int((s1 - s0 - 0.2) / 0.62)
                st = s0 + (s1 - s0 - (n - 1) * 0.62) / 2
                slots += [st + k * 0.62 for k in range(max(0, n))]
            if len(slots) > 11:
                c0 = (len(slots) - 11) // 2
                slots = slots[c0:c0 + 11]
            fr = zn.style.get("front_runs") or [aw]
            for sc in slots:
                j = nprint % 8
                nprint += 1
                u0, v0 = (j % 4) * 0.25, (0.5 if j < 4 else 0.0)
                # on the true wall face: the room polygon's edge can sit a few cm off the wall runs' line (the
                # frames hid inside the wall), so measure from the nearest wall run of the front line
                q = (a[0] + dx * sc, a[1] + dy * sc)
                pa_, pb_ = min(fr, key=lambda rr: R.seg_point_dist(q, rr[0], rr[1]))
                Le = max(1e-6, math.dist(pa_, pb_))
                e = ((pb_[0] - pa_[0]) / Le, (pb_[1] - pa_[1]) / Le)
                if e[1] * nx - e[0] * ny < 0:
                    e = (-e[0], -e[1])
                nn = (e[1], -e[0])
                t_ = (q[0] - pa_[0]) * e[0] + (q[1] - pa_[1]) * e[1]
                fc = (pa_[0] + e[0] * t_ + nn[0] * (WALL_T / 2 + 0.025), pa_[1] + e[1] * t_ + nn[1] * (WALL_T / 2 + 0.025))
                R.panel(V, (fc[0] - e[0] * 0.21, fc[1] - e[1] * 0.21), (fc[0] + e[0] * 0.21, fc[1] + e[1] * 0.21),
                        z + 1.50, z + 1.98, "int_ru_prints", off=0.0, u0=u0, u1=u0 + 0.25, v0=v0, v1=v0 + 0.5)
            continue
        for s0, s1 in spans:
            if s1 - s0 >= 0.3 and not upstairs:
                R.panel(V, P(s0), P(s1), z + 0.10, z + 0.88, "int_ru_wainscot", u0=0.0, u1=round(s1 - s0, 3))
        # prints: the long interior side walls (exterior walls carry the ribbon windows)
        if outside == "O" or L < 4.0 or abs(dx * fx + dy * fy) < 0.7:
            continue
        aw_n = ART_WALL.get(zn.id)
        if aw_n is not None and nx * aw_n[0] + ny * aw_n[1] < 0.7:
            continue                            # fix round 5 (fidelity-4): the named art wall only (2355 / 2365)
        if pmode in ("long5", "one"):
            side_cands.append((sum(s1_ - s0_ for s0_, s1_ in spans), spans, P))
            continue
        if pmode != "all":
            continue
        pitch, hw, pz0, pz1 = (2.0, 0.45, 1.45, 2.25) if upstairs else (1.7, 0.34, 1.55, 2.15)
        for s0, s1 in spans:
            n = int((s1 - s0 - 0.6) / pitch)
            if n < 1:
                continue
            st = s0 + (s1 - s0 - (n - 1) * pitch) / 2
            for k in range(n):
                sc = st + k * pitch
                j = nprint % 8
                nprint += 1
                u0, v0 = (j % 4) * 0.25, (0.5 if j < 4 else 0.0)
                R.panel(V, P(sc - hw), P(sc + hw), z + pz0, z + pz1, "int_ru_prints", off=0.01,
                        u0=u0, u1=u0 + 0.25, v0=v0, v1=v0 + 0.5)
    if side_cands:
        # ru_os_2355_2365: five colourful pieces along ONE long wall; ru_os_3310: a single frame
        _tot, spans, P = max(side_cands, key=lambda c_: c_[0])
        cap = 5 if pmode == "long5" else 1
        slots = []
        for s0, s1 in spans:
            n = int((s1 - s0 - 0.6) / 2.0)
            st = s0 + (s1 - s0 - (n - 1) * 2.0) / 2
            slots += [st + k * 2.0 for k in range(max(0, n))]
        if len(slots) > cap:
            c0 = (len(slots) - cap) // 2
            slots = slots[c0:c0 + cap]
        for sc in slots:
            j = nprint % 8
            nprint += 1
            if zn.id in ART_WALL:
                # fix round 5 (fidelity-4, improvement 1; ru_os_2355_2365): wide colourful landscape canvases
                # (~1.2 x 0.8 m, no white mat), 4.5 cm proud of the wall face (2355's east wall is
                # slanted: its 1 cm-rounded vertices brought a 2.5 cm offset within the z-fight tolerance)
                u0, v0 = (j % 2) * 0.5, (0.5 if (j // 2) % 2 == 0 else 0.0)
                R.panel(V, P(sc - 0.6), P(sc + 0.6), z + 1.40, z + 2.20, "int_ru_canvas", off=0.03,
                        u0=u0, u1=u0 + 0.5, v0=v0, v1=v0 + 0.5)
                continue
            u0, v0 = (j % 4) * 0.25, (0.5 if j < 4 else 0.0)
            R.panel(V, P(sc - 0.45), P(sc + 0.45), z + 1.45, z + 2.25, "int_ru_prints", off=0.01,
                    u0=u0, u1=u0 + 0.25, v0=v0, v1=v0 + 0.5)
    # EXIT signs over the doors, room side (int_ru_exit: the sign is texture rows 9-22)
    for da, db, dm, dn in doors:
        d = (-dn[1], dn[0])
        # fix round 5 (fidelity-3; ru_os_g330): a door whose plan midpoint lies outside the room (G330's slanted north
        # wall: 4 cm) put its sign 1 cm BEHIND the wall face; on Ground the sign steps out by that much (<= 15 cm)
        ex_ = 0.0
        if F.id == "G" and not R.pip(dm, zn.poly):
            ex_ = min(0.15, R.poly_dist(dm, zn.poly))
        R.panel(V, (dm[0] - d[0] * 0.21, dm[1] - d[1] * 0.21), (dm[0] + d[0] * 0.21, dm[1] + d[1] * 0.21),
                z + DOOR_H + 0.14, z + DOOR_H + 0.34, "int_ru_exit", off=WALL_T / 2 + 0.03 + ex_, glow=True, v0=0.28,
                v1=0.72)


def _ceiling_projector(V, P, x, y, zc, f):
    """Ceiling projector on a drop rod (ru_os_chamber, ru_os_g310_g320), lens toward the screen wall (-f)."""
    V.box(x - 0.025, y - 0.025, zc - 0.62, x + 0.025, y + 0.025, zc, "int_ru_black", faces="+x-x+y-y")
    V.box(x - 0.25, y - 0.25, zc - 0.80, x + 0.25, y + 0.25, zc - 0.62, "int_ru_white", faces="+x-x+y-y-z+z")
    lx, ly = x - f[0] * 0.26, y - f[1] * 0.26
    V.box(lx - 0.06, ly - 0.06, zc - 0.77, lx + 0.06, ly + 0.06, zc - 0.65, "int_ru_black", faces="+x-x+y-y-z")


EMPTY_ROOMS = set()                     # (fidelity-3: ru_os_g330 shows rows of chairs facing the blue wall)
# fix round 4 (fidelity-4 blocking): the front of the room (screen housing, projector, the rows' facing) is the wall
# WITH the doors, as in the photos. ru_os_2315_2330 / ru_os_2360: the slate-blue between the corridor doors;
# ru_os_3315_3320: a white front wall with the two doors and a row of small framed photos (no blue).
FRONT_DOOR_WALL = {"meeting_2315", "meeting_2320", "meeting_2325", "meeting_2330", "meeting_2360", "meeting_3315",
                   "meeting_3320"}
# ru_os_2335_2340: the blue is the short end wall, the room's door on the long wall right next to it
FRONT_END_WALL = {"meeting_2335", "meeting_2340"}
# fix round 5 (fidelity-4, improvement 1; ru_os_2355_2365): the rows face a slate-blue END wall (here the north one,
# unit vector out of the room), the five landscape canvases hang on the long DOOR wall (ART_WALL: the inward normal of
# that wall). 2355 = the photo (canvases on the right-hand east wall); 2365 is its mirror twin (canvases on the west)
ACCENT_DIR = {"meeting_2355": (0.0, 1.0), "meeting_2365": (0.0, 1.0)}
ART_WALL = {"meeting_2355": (-1.0, 0.0), "meeting_2365": (1.0, 0.0)}
# all-white rooms: ru_os_2345_2350 (wall TV beside the door), ru_os_3315_3320
# fix round 5 (fidelity-3; ru_os_g325): rooms whose accent is a royal BAY on the accent wall (two plan points spanning
# it), white wall round it, lit by wall-washers (int_ru_wall_royal_wash): G325's 7.8 m bay, white door wall to its west
ROYAL_BAY = {"meeting_G325": ((-369.2, -261.8), (-361.4, -261.8))}
NO_ACCENT = {"meeting_2345", "meeting_2350", "meeting_3315", "meeting_3320"}
# fix round 4 (fidelity-4 pass, improvement 1): the upstairs art per room, from the photos (rooms not listed: bare)
UPSTAIRS_PRINTS = {"meeting_2355": "long5", "meeting_2365": "long5", "meeting_3315": "front_row",
                   "meeting_3320": "front_row", "meeting_3310": "one"}
PILASTER_WALL = {"meeting_2360"}        # fix round 4 (fidelity-4 pass): white pilasters on the blue front wall
# fix round 4 (fidelity-4 pass, improvement 6): ru_os_2345_2350 has no ceiling projector / screen housing
NO_PROJECTOR = {"meeting_2345", "meeting_2350"}
WHITE_SCREEN_WALL = {"meeting_3305"}   # fix round 2: ru_os_3305's pull-down screen drops in front of a WHITE wall
MEETING_KIND = {"meeting_G325": "classroom", "meeting_3305": "u_shape", "meeting_3310": "hollow",
                "meeting_2345": "boardroom", "meeting_2350": "boardroom", "meeting_2104": "boardroom",
                "meeting_2108": "boardroom", "meeting_2020": "boardroom"}


def _nocol(prop):
    """A kit prop without its own collision (a run of tables gets one merged block: collision budget)."""
    prop.collision.polys = []
    return prop


def _runs_of(us, gap):
    """Group sorted positions into runs whose neighbours are at most `gap` apart."""
    out = []
    for u in sorted(us):
        if out and u - out[-1][-1] <= gap:
            out[-1].append(u)
        else:
            out.append([u])
    return out


def _col_rect(C, c, a, ha, hb, z0, z1, mat=None):
    """One collision block: a rectangle centred at c, half-lengths ha along unit a and hb across it."""
    b = (-a[1], a[0])
    pts = [(c[0] + a[0] * sa * ha + b[0] * sb * hb, c[1] + a[1] * sa * ha + b[1] * sb * hb)
           for sa, sb in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    K.col_prism(C, R.ccw(pts), z0, z1, mat or K.COL_NOCAM)


def meeting_rooms(RZ):
    """Every meeting room: carpet tile, white walls + one accent wall (royal blue on Ground, pale grey-blue upstairs),
    the white chair rail, linear LED ceilings (build_floor); upstairs a projector screen on the accent wall; on
    Ground (ru_os_g310_g320, ru_os_g330) the blue corridor end wall stays bare, with a ceiling projector and a
    retracted screen housing, raised-panel wainscot and a row of framed prints on the white walls; set
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
            if fid == "G" and W > 4.0 and D > 4.0:
                # ru_os_g310_g320 / ru_os_g330: no screen on the blue wall; a ceiling projector and a retracted
                # screen housing at the ceiling in front of the blue wall (fidelity-3 round 2: the dropped ceiling)
                zc = z + zn.style.get("ceil_h", zn.style["clear"])
                sw = min(3.6, W * 0.45)
                R.seg_box(V, (mx + tx * sw / 2 + fx * 0.55, my + ty * sw / 2 + fy * 0.55),
                          (mx - tx * sw / 2 + fx * 0.55, my - ty * sw / 2 + fy * 0.55), 0.08, zc - 0.16, zc,
                          "int_ru_wall_grey", faces="sideends_bot")
                pd = min(D * 0.5, 7.0)
                _ceiling_projector(V, P, mx + fx * pd, my + fy * pd, zc, (fx, fy))
                _meeting_walls(F, zn, V, fx, fy)
            elif W > 4.0 and D > 4.0 and zn.id in NO_PROJECTOR:
                _meeting_walls(F, zn, V, fx, fy, upstairs=True)    # fidelity-4 pass: walls + EXIT signs, no projector
            elif W > 4.0 and D > 4.0 and zn.id not in NO_PROJECTOR:
                # fix round 2 (blocking; ru_os_2315_2330, 2335_2340, 2355_2365, 2360, 3315_3320): no permanent
                # wall screen upstairs; a ceiling projector and a retracted screen housing, as on Ground. 3305: the
                # pull-down screen is down, in front of a white wall (ru_os_3305)
                zc = z + zn.style.get("ceil_h", zn.style["clear"])
                sw = min(3.6, W * 0.45)
                ha = (mx + tx * sw / 2 + fx * 0.45, my + ty * sw / 2 + fy * 0.45)
                hb = (mx - tx * sw / 2 + fx * 0.45, my - ty * sw / 2 + fy * 0.45)
                R.seg_box(V, ha, hb, 0.08, zc - 0.16, zc, "int_ru_wall_grey", faces="sideends_bot")
                if zn.id in WHITE_SCREEN_WALL:
                    R.panel(V, (ha[0] - fx * 0.02, ha[1] - fy * 0.02), (hb[0] - fx * 0.02, hb[1] - fy * 0.02),
                            z + 1.1, zc - 0.16, "int_ru_proj_screen", off=0.0)
                if zn.id in PILASTER_WALL:
                    # fix round 4 (fidelity-4 pass; ru_os_2360): white pilasters split the slate-blue front wall into
                    # panel bays (both ends + the middle), proud of the wall, floor to ceiling
                    for u_ in (-W / 2 + 0.2, 0.0, W / 2 - 0.2):
                        pc = (mx + tx * u_ + fx * (WALL_T / 2 + 0.075), my + ty * u_ + fy * (WALL_T / 2 + 0.075))
                        R.seg_box(V, (pc[0] - tx * 0.2, pc[1] - ty * 0.2), (pc[0] + tx * 0.2, pc[1] + ty * 0.2), 0.06,
                                  z + 0.02, zc - 0.01, "int_ru_white", faces="sideends")
                _ceiling_projector(V, P, mx + fx * min(D * 0.5, 6.0), my + fy * min(D * 0.5, 6.0), zc, (fx, fy))
                _meeting_walls(F, zn, V, fx, fy, upstairs=True)
            # the room's width across the facing (the accent wall can be shorter than the room: G330, 2335)
            proj = [(p[0] - mx) * tx + (p[1] - my) * ty for p in zn.poly]
            tmid = (min(proj) + max(proj)) / 2
            Wr = max(proj) - min(proj)
            fproj = [(p[0] - mx) * fx + (p[1] - my) * fy for p in zn.poly]
            if kind == "rows" and D > 5.0 and W > 4.0 and zn.id not in EMPTY_ROOMS:
                # Ground: leave ~1.6 m behind the rows for the navy draped table (ru_os_g330: in the foreground)
                rows = max(2, int((D - 3.4 - (1.6 if fid == "G" else 0.0)) / 0.95))
                per = max(4, int((Wr - 1.6 - 1.2) / 0.5))
                # chair_rows: row 0 at the origin facing local +y, the rows run toward local -y; placed facing the
                # screen wall (facing + 180) the rows run back INTO the room from the front row at 2.6 m
                d0 = 2.6
                ox, oy = mx + tx * tmid + fx * d0, my + ty * tmid + fy * d0
                for _try in range(10):
                    prop = R.chair_rows(rows, per, pitch=0.95, aisle_every=per // 2 if per > 10 else 0, aisle_w=1.2,
                                        kind="black")
                    pl = prop.placed(ox, oy, z, (facing + 180.0) % 360)
                    pts = [v for pl_ in pl.visual.polys for v in pl_.pts]
                    inside = sum(1 for v in pts if R.pip((v[0], v[1]), zn.poly) or R.poly_dist((v[0], v[1]), zn.poly) < 0.12)
                    if not pts or inside >= (1.0 if fid == "G" else 0.98) * len(pts):
                        break
                    # shrink to fit odd-shaped rooms (narrower than the screen wall somewhere); Ground rooms narrow
                    # the rows first (G330: the slanted blue wall overstates the room's width), then drop rows
                    if fid == "G" and per > 6:
                        per -= 2
                    elif _try % 2 == 0 and per > 6:
                        per -= 2
                    elif rows > 2:
                        rows -= 1
                    else:
                        per = max(4, per - 2)
                RZ.kit_add(prop, fid, tag=f"rows_{zn.id}", x=ox, y=oy, z=z, facing=(facing + 180.0) % 360)
                if fid == "G":
                    # ru_os_g330 / ru_os_g310_g320: the navy draped table stands behind the rows, by a side wall
                    dt = d0 + rows * 0.95 + 0.6
                    tb = R.draped_table(1.6, 0.75)
                    inner = R.offset_poly(zn.poly, -0.15)
                    for off in (Wr / 2 - 1.4, Wr / 2 - 2.4, -(Wr / 2 - 2.4), Wr / 2 - 3.4, 0.0):
                        cand = (mx + tx * (tmid + off) + fx * dt, my + ty * (tmid + off) + fy * dt)
                        pts = [v for pl_ in tb.placed(cand[0], cand[1], z, facing).visual.polys for v in pl_.pts]
                        if pts and all(R.pip((v[0], v[1]), inner) for v in pts):
                            RZ.kit_add(tb, fid, tag=f"drape_{zn.id}", x=cand[0], y=cand[1], z=z, facing=facing)
                            break
                else:
                    # navy draped table by the accent wall (corner); fix round 4: a corner clear of the room's doors
                    # (the front wall now carries the doors in 2315-2330 / 2335-2340 / 2360 / 3315-3320)
                    dmid_ = [d[2] for d in _room_doors(F, zn)]
                    cands = [(mx + fx * 1.2 + tx * (W / 2 - 1.4), my + fy * 1.2 + ty * (W / 2 - 1.4)),
                             (mx + fx * 1.2 - tx * (W / 2 - 1.4), my + fy * 1.2 - ty * (W / 2 - 1.4)),
                             (mx + fx * (D - 1.2) + tx * (W / 2 - 1.4), my + fy * (D - 1.2) + ty * (W / 2 - 1.4)),
                             (mx + fx * (D - 1.2) - tx * (W / 2 - 1.4), my + fy * (D - 1.2) - ty * (W / 2 - 1.4))]
                    inner_ = R.offset_poly(zn.poly, -0.5)
                    pick = next((c_ for c_ in cands if R.pip(c_, inner_) and
                                 all(math.dist(c_, dm) > 2.3 for dm in dmid_)), None)
                    if pick is not None:
                        RZ.kit_add(R.draped_table(1.6, 0.75), fid, tag=f"drape_{zn.id}", x=pick[0], y=pick[1], z=z,
                                   facing=facing)
            elif kind == "classroom" and D > 4.0 and fid == "G":
                # fix round 5 (fidelity-3; ru_os_g325): the rows of training tables fill the room's width, three
                # 1.8 m tables a side of a centre aisle (they were two tables a row in a 4 m block, the west half of
                # the 14 m room bare carpet); tables that would cross a wall or block a door are dropped. One merged
                # no-cam block per run of tables covers the tables AND their chairs (the chairs had no collision);
                # rows 2.3 m apart leave a 1 m walkway between a row's chair backs and the next row's tables
                n = max(2, int((D - 1.2 - 0.95 - 2.2) / 2.3) + 1)
                zp = R.offset_poly(zn.poly, 0.05)
                dmid_ = [d[2] for d in _room_doors(F, zn)]
                for r in range(n):
                    dv = 2.2 + r * 2.3
                    for side in (-1, 1):
                        kept = []
                        for k_ in range(3):
                            u = tmid + side * (1.55 + k_ * 1.9)
                            tx_, ty_ = mx + fx * dv + tx * u, my + fy * dv + ty * u
                            tb = _nocol(R.folding_table(1.8, 0.6))
                            pts = [v for pl_ in tb.placed(tx_, ty_, z, (facing + 180.0) % 360).visual.polys
                                   for v in pl_.pts]
                            if not pts or sum(1 for v in pts if not R.pip((v[0], v[1]), zp)) > 0.03 * len(pts):
                                continue
                            if any(math.dist((tx_, ty_), dm) < 1.9 for dm in dmid_):
                                continue
                            RZ.kit_add(tb, fid, tag=f"class_{zn.id}_{r}_{side}_{k_}", x=tx_, y=ty_, z=z,
                                       facing=(facing + 180.0) % 360)
                            kept.append(u)
                        for grp in _runs_of(kept, 1.95):
                            uc = (min(grp) + max(grp)) / 2
                            # tables (-0.32) to chair backs (+0.95) along the facing (the chairs are room-side)
                            _col_rect(P.collision, (mx + fx * (dv + 0.315) + tx * uc, my + fy * (dv + 0.315) + ty * uc),
                                      (tx, ty), (max(grp) - min(grp)) / 2 + 0.9, 0.635, z, z + 0.74)
            elif kind == "classroom" and D > 4.0:
                n = max(2, int((D - 2.8) / 1.6))
                zp = R.offset_poly(zn.poly, 0.05)
                for r in range(n):
                    for side in (-1, 1):
                        tb = R.folding_table(1.8, 0.6)
                        tx_, ty_ = mx + fx * (2.4 + r * 1.6) + tx * side * 1.2, my + fy * (2.4 + r * 1.6) + ty * side * 1.2
                        pts = [v for pl_ in tb.placed(tx_, ty_, z, (facing + 180.0) % 360).visual.polys for v in pl_.pts]
                        if pts and sum(1 for v in pts if not R.pip((v[0], v[1]), zp)) > 0.03 * len(pts):
                            continue            # tapered rooms (3310): drop the tables that would cross the wall
                        RZ.kit_add(tb, fid, tag=f"class_{zn.id}_{r}_{side}", x=tx_, y=ty_, z=z,
                                   facing=(facing + 180.0) % 360)
            elif kind == "u_shape" and D > 5.0:
                # fix round 2 (ru_os_3305): the U's legs run nearly the room's length, 8 chairs a leg
                ul = max(1.6, min(Wr / 2 - 1.5, 3.4))
                n_leg = max(2, int((D - 3.8) / 1.8))
                for k in range(n_leg):
                    v = 2.3 + 0.9 + k * 1.8
                    for u, rot in ((-ul, 90.0), (ul, 270.0)):
                        RZ.kit_add(_nocol(R.folding_table(1.8, 0.6, chairs=4, chair="office")), fid, tag=f"u_{zn.id}_{k}_{int(u > 0)}",
                                   x=mx + fx * v + tx * (tmid + u), y=my + fy * v + ty * (tmid + u), z=z,
                                   facing=(facing + rot) % 360)
                vh = 2.3 + n_leg * 1.8 + 0.3
                m = max(1, int((2 * ul - 0.6) / 1.8))
                for k in range(m):
                    u = -(m - 1) * 0.9 + k * 1.8
                    RZ.kit_add(_nocol(R.folding_table(1.8, 0.6, chairs=4, chair="office")), fid, tag=f"u_{zn.id}_head_{k}",
                               x=mx + fx * vh + tx * (tmid + u), y=my + fy * vh + ty * (tmid + u), z=z,
                               facing=(facing + 180.0) % 360)
                # merged collision: one block per leg + the head
                vm = 2.3 + n_leg * 0.9
                for u in (-ul, ul):
                    _col_rect(P.collision, (mx + fx * vm + tx * (tmid + u), my + fy * vm + ty * (tmid + u)), (fx, fy),
                              n_leg * 0.9, 0.3, z, z + 0.74)
                _col_rect(P.collision, (mx + fx * vh + tx * tmid, my + fy * vh + ty * tmid), (tx, ty), m * 0.9, 0.3,
                          z, z + 0.74)
            elif kind == "hollow":
                # fix round 2 (ru_os_3310): long tables in a hollow square on the full room, chairs all round
                hu = max(1.8, (max(proj) - min(proj)) / 2 - 1.6)
                fm = (min(fproj) + max(fproj)) / 2
                hv = max(1.5, (max(fproj) - min(fproj)) / 2 - 1.5)
                cx_, cy_ = mx + tx * tmid + fx * fm, my + ty * tmid + fy * fm
                zp = R.offset_poly(zn.poly, 0.05)
                k_ = 0
                for along, half, side_off, rots in ((True, hu, hv, (facing + 180.0, facing)),
                                                    (False, hv - 0.9, hu, (facing + 270.0, facing + 90.0))):
                    n = max(1, int(2 * half / 1.8))
                    for sgn, rot in ((1, rots[0]), (-1, rots[1])):
                        for i in range(n):
                            o = -(n - 1) * 0.9 + i * 1.8
                            if along:
                                px, py = cx_ + tx * o + fx * side_off * sgn, cy_ + ty * o + fy * side_off * sgn
                            else:
                                px, py = cx_ + fx * o + tx * side_off * sgn, cy_ + fy * o + ty * side_off * sgn
                            tb = R.folding_table(1.8, 0.6, chairs=3, chair="office")
                            pts = [v for pl_ in tb.placed(px, py, z, rot % 360).visual.polys for v in pl_.pts]
                            if pts and sum(1 for v in pts if not R.pip((v[0], v[1]), zp)) > 0.03 * len(pts):
                                continue
                            RZ.kit_add(_nocol(tb), fid, tag=f"hollow_{zn.id}_{k_}", x=px, y=py, z=z, facing=rot % 360)
                            k_ += 1
                        # one merged collision block per side
                        if along:
                            cc = (cx_ + fx * side_off * sgn, cy_ + fy * side_off * sgn)
                            _col_rect(P.collision, cc, (tx, ty), n * 0.9, 0.3, z, z + 0.74)
                        else:
                            cc = (cx_ + tx * side_off * sgn, cy_ + ty * side_off * sgn)
                            _col_rect(P.collision, cc, (fx, fy), n * 0.9, 0.3, z, z + 0.74)
            elif kind == "boardroom":
                # fix round 2 (ru_os_2345_2350): the table runs along the room's long side (~6 m, 7 chairs a side),
                # and a wall TV hangs on the white end wall
                c = R.centroid(zn.poly)
                L_ = max(2.4, min(6.2, Wr - 2.8))
                nch = max(3, int(L_ / 0.85))
                top_ = "int_ru_maple_light" if zn.id in NO_PROJECTOR else "int_ru_wall_cream"   # 2345_2350: maple
                for sgn, rot in ((1, facing + 180.0), (-1, facing)):
                    # two back-to-back 0.6 m tables along the long wall (local x = t): chairs on both long sides
                    RZ.kit_add(_nocol(R.folding_table(L_, 0.6, top=top_, chairs=nch, chair="office")), fid,
                               tag=f"board_{zn.id}_{int(sgn > 0)}", x=c[0] + fx * 0.3 * sgn, y=c[1] + fy * 0.3 * sgn,
                               z=z, facing=rot % 360)
                _col_rect(P.collision, c, (tx, ty), L_ / 2, 0.6, z, z + 0.74)
                te = max(proj) - 0.13
                ce = (c[0] - mx) * fx + (c[1] - my) * fy
                tw, tz0, tz1 = 0.75, z + 1.25, z + 2.1
                if zn.id in NO_PROJECTOR:
                    # fix round 4 (fidelity-4 pass; ru_os_2345_2350): a large (~1.5 m) wall TV right beside the door
                    # on the end wall, on the side with room for it (2350: left of the door, as photographed)
                    gaps_ = []
                    for da, db, dm, dn in _room_doors(F, zn):
                        if abs((dm[0] - mx) * tx + (dm[1] - my) * ty - max(proj)) < 0.5:
                            dd_ = [(q[0] - mx) * fx + (q[1] - my) * fy for q in (da, db)]
                            gaps_.append((min(dd_) - 0.3, max(dd_) + 0.3))
                    lo_, hi_ = min(fproj) + 0.3, max(fproj) - 0.3
                    sp_ = [(lo_, hi_)]
                    for g0, g1 in gaps_:
                        sp_ = [q for s0_, s1_ in sp_ for q in ((s0_, min(s1_, g0)), (max(s0_, g1), s1_)) if q[1] - q[0] > 0.05]
                    if sp_:
                        q = max(sp_, key=lambda q_: q_[1] - q_[0])
                        tw = max(0.5, min(0.78, (q[1] - q[0]) / 2 - 0.05))
                        ce = (q[0] + tw + 0.05) if gaps_ and abs(q[0] - max(g1 for _g, g1 in gaps_)) < 0.01 else \
                            (q[1] - tw - 0.05) if gaps_ else (q[0] + q[1]) / 2
                        tz0, tz1 = z + 1.1, z + 1.1 + tw * 2 * 0.58
                # fix round 4 (fidelity-4 pass): a -> b runs along -f so the screen faces INTO the room (it faced the
                # end wall, so the game's back-face culling hid it)
                ta = (mx + tx * te + fx * (ce + tw), my + ty * te + fy * (ce + tw))
                tb_ = (mx + tx * te + fx * (ce - tw), my + ty * te + fy * (ce - tw))
                R.panel(V, ta, tb_, tz0, tz1, "int_ru_tv_hotel", off=0.0, glow=True)
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
    col = ARREDONDO_COLUMN
    # fidelity-4 round 2 (ru_os_arredondo_cafe): a denser staggered grid of square tables (3.3 x 3.3 m: 33 sets,
    # was ~14 in 482 m2; one 10-triangle collision box each, so not denser), wood-back chairs with tan-orange
    # seats; kept clear of the stone column, the plan doors and the cafe coin line (y -262.5, x -435.2 .. -428.8)
    doors_ = [((d[0] + d[2]) / 2, (d[1] + d[3]) / 2) for d in F.doors
              if R.poly_dist(((d[0] + d[2]) / 2, (d[1] + d[3]) / 2), ar.poly) < 0.4]
    for ri, yy in enumerate((-259.3, -262.6, -265.9, -269.2, -272.5, -275.8)):
        for j in range(14):
            xx = -452.3 + j * 3.3 + (0.0 if ri % 2 == 0 else 0.825)
            if math.dist((xx, yy), col) < 1.9:
                continue
            if abs(yy + 262.5) < 1.3 and -436.6 < xx < -427.4:
                continue
            if any(math.dist((xx, yy), dm) < 1.7 for dm in doors_):
                continue
            if R.pip((xx, yy), ar.poly) and R.poly_dist((xx, yy), ar.poly) > 1.0:
                RZ.kit_add(R.cafe_table_set(0.8, chair_mat="int_ru_seat_tan", frame="int_ru_cherry",
                                            top="int_ru_cherry", seat_box=True), "L4", tag=f"arr_table_{k}", x=xx, y=yy,
                           z=z, facing=0.0)
                k += 1
    _arredondo_dress(RZ, F, ar)
    ms = F.zone("matthews_suite")
    c = R.centroid(ms.poly)
    # fix round 4 (fidelity-4 pass; ru_os_matthews_1/2): the floor is filled with round tables in two rows of
    # three (the photos show 5-7 tables; was 3)
    for j, (dx, dy) in enumerate(((-4.0, 1.75), (-0.15, 1.75), (3.7, 1.75), (-4.0, -1.75), (-0.15, -1.75),
                                  (3.7, -1.75))):
        # fix round 5 (fidelity-4, improvement 3): white tops on pedestals, thick-backed navy chairs on silver legs
        RZ.kit_add(R.round_table(0.75, top="int_ru_bed", chair_mat="int_ru_fabric_navy", chairs=7, pedestal=True), "L4",
                   tag=f"matthews_round_{j}", x=c[0] + dx, y=c[1] + dy, z=z)
    P = K.Prop("matthews_photos")
    V = P.visual
    F4 = RZ.floors["L4"]
    mdoors = _room_doors(F4, ms)
    zc = z + ms.style.get("ceil_h", ms.style["clear"])
    walls_ = []
    for a, b in _room_inside_edges(ms, 0.12):
        L = math.dist(a, b)
        if L > 3.0:
            dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            # fix round 2 (blocking): never on the window wall (the frames floated in front of the L4 curtain glass;
            # ru_os_matthews_1/2: the photos hang on the solid grey-blue walls)
            nx_, ny_ = dy, -dx
            row4 = False
            if any(F4.cls_at((a[0] + dx * L * t_ - nx_ * 0.45, a[1] + dy * L * t_ - ny_ * 0.45))[0] == "O"
                   for t_ in (0.2, 0.5, 0.8)):
                if window_spec("L4", a, b, ms) is not None:
                    continue
                row4 = True             # fix round 5 (fidelity-4): the solid south wall (ru_os_matthews_1)
            gaps = []
            for da, db, dm, dn in mdoors:
                if abs((dm[0] - a[0]) * nx_ + (dm[1] - a[1]) * ny_) > 0.5:
                    continue
                s0_ = (da[0] - a[0]) * dx + (da[1] - a[1]) * dy
                s1_ = (db[0] - a[0]) * dx + (db[1] - a[1]) * dy
                gaps.append((min(s0_, s1_) - 0.35, max(s0_, s1_) + 0.35))
            walls_.append((L, a, b, dx, dy, gaps, row4))

    def _Pm(a, dx, dy, s_):
        return (a[0] + dx * s_, a[1] + dy * s_)

    def _frame(a, dx, dy, sc, z0, z1, k):
        R.panel(V, _Pm(a, dx, dy, sc - 0.40), _Pm(a, dx, dy, sc + 0.40), z0, z1, "int_ru_photos", off=0.02,
                u0=0.5 * (k % 2), u1=0.5 * (k % 2) + 0.5)
    kf = 0
    for L, a, b, dx, dy, gaps, row4 in walls_:
        free = lambda s0_, s1_: all(s1_ <= g0 or s0_ >= g1 for g0, g1 in gaps)  # noqa: E731
        if row4:
            # ru_os_matthews_1: a single row of four frames along the solid south wall
            for k4 in range(4):
                sc = L * (k4 + 1) / 5
                if free(sc - 0.45, sc + 0.45):
                    # on the exterior wall's inner face (EXT_T / 2 from the plan line) + 2.5 cm
                    R.panel(V, _Pm(a, dx, dy, sc - 0.40), _Pm(a, dx, dy, sc + 0.40), z + 1.50, z + 2.16,
                            "int_ru_photos", off=EXT_T / 2 + 0.025 - 0.12, u0=0.5 * (kf % 2), u1=0.5 * (kf % 2) + 0.5)
                    kf += 1
        elif L > 9.0:
            # ru_os_matthews_2: cream-matted framed documents (~0.8 x 0.65 m, ~0.45 m apart), a 2-row grid of three
            # next to the door, then single frames down the wall
            sc = L - 0.9
            while sc > 3.3 and not free(sc - 2 * 1.25 - 0.45, sc + 0.45):
                sc -= 0.25
            for col in range(3):
                for z0_ in (z + 1.25, z + 2.10):
                    _frame(a, dx, dy, sc - col * 1.25, z0_, z0_ + 0.66, kf)
                    kf += 1
            sc -= 3 * 1.25 + 0.6
            while sc > 0.8:
                if free(sc - 0.45, sc + 0.45):
                    _frame(a, dx, dy, sc, z + 1.55, z + 2.21, kf)
                    kf += 1
                    sc -= 1.7
                else:
                    sc -= 0.25
        else:
            # the end wall with the door: the projection screen beside it (ru_os_matthews_2), no frames
            spans_ = [(0.3, L - 0.3)]
            for g0, g1 in sorted(gaps):
                nxt = []
                for s0_, s1_ in spans_:
                    if g1 <= s0_ or g0 >= s1_:
                        nxt.append((s0_, s1_))
                        continue
                    if g0 > s0_:
                        nxt.append((s0_, g0))
                    if g1 < s1_:
                        nxt.append((g1, s1_))
                spans_ = nxt
            s0_, s1_ = max(spans_, key=lambda q: q[1] - q[0])
            w_ = min(3.4, s1_ - s0_ - 0.3)
            if w_ > 2.0:
                sm = (s0_ + s1_) / 2
                sa, sb = _Pm(a, dx, dy, sm - w_ / 2), _Pm(a, dx, dy, sm + w_ / 2)
                R.panel(V, sa, sb, z + 1.25, min(zc - 0.45, z + 1.25 + w_ * 0.62), "int_ru_proj_screen", off=0.03)
                nx_, ny_ = dy, -dx
                pm = _Pm(a, dx, dy, sm)
                _ceiling_projector(V, P, pm[0] + nx_ * 5.0, pm[1] + ny_ * 5.0, zc, (nx_, ny_))
    _matthews_anteroom(F4, F4.zone("l4_matthews_suite"), V, z)
    # fix round 5 (fidelity-4, improvement 2; ru_os_matthews_1..4): white crown moulding round the suite too
    _crown(F4, ms, V, z + ms.style.get("ceil_h", ms.style["clear"]))
    RZ.kit_add(P, "L4", tag="matthews_photos")


def _crown(F, zn, V, zc, h=0.12):
    """A white crown-moulding strip under the ceiling on a room's solid walls (4 cm proud of the wall face; not
    on the window wall)."""
    for a, b in _room_inside_edges(zn, 0.12):
        L = math.dist(a, b)
        if L < 0.6:
            continue
        dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx_, ny_ = dy, -dx
        if any(F.cls_at((a[0] + dx * L * t_ - nx_ * 0.45, a[1] + dy * L * t_ - ny_ * 0.45))[0] == "O"
               for t_ in (0.2, 0.5, 0.8)):
            continue
        R.panel(V, a, b, zc - h, zc - 0.005, "int_ru_white", off=0.02, ao=1.0)


def _matthews_anteroom(F, an, V, z):
    """fix round 5 (fidelity-4, improvement 2; ru_os_matthews_3 / _4): the anteroom's walls are full of cream-matted
    framed historic photos (2 x 2 groups, stacked pairs, a row of three with a larger centre one), white double closet
    doors beside the wood door, white base (zone_style) and crown. Frames 4 cm proud of the wall face."""
    zc = z + an.style.get("ceil_h", an.style["clear"])
    doors = _room_doors(F, an)
    kf = 0
    for a, b in _room_inside_edges(an, 0.12):
        L = math.dist(a, b)
        if L < 0.8:
            continue
        dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx_, ny_ = dy, -dx
        if any(F.cls_at((a[0] + dx * L * t_ - nx_ * 0.45, a[1] + dy * L * t_ - ny_ * 0.45))[0] in ("O", "V")
               for t_ in (0.2, 0.5, 0.8)):
            continue
        gaps = []
        for da, db, dm, dn in doors:
            if abs((dm[0] - a[0]) * nx_ + (dm[1] - a[1]) * ny_) > 0.5:
                continue
            s0_ = (da[0] - a[0]) * dx + (da[1] - a[1]) * dy
            s1_ = (db[0] - a[0]) * dx + (db[1] - a[1]) * dy
            gaps.append((min(s0_, s1_) - 0.3, max(s0_, s1_) + 0.3))
        spans = [(0.15, L - 0.15)]
        for g0, g1 in sorted(gaps):
            nxt = []
            for s0_, s1_ in spans:
                if g1 <= s0_ or g0 >= s1_:
                    nxt.append((s0_, s1_))
                    continue
                if g0 > s0_:
                    nxt.append((s0_, g0))
                if g1 < s1_:
                    nxt.append((g1, s1_))
            spans = nxt

        def at(s_, a=a, dx=dx, dy=dy):
            return (a[0] + dx * s_, a[1] + dy * s_)

        def frame(sc, hw, z0, z1):
            nonlocal kf
            R.panel(V, at(sc - hw), at(sc + hw), z0, z1, "int_ru_photos", off=0.02, u0=0.5 * (kf % 2),
                    u1=0.5 * (kf % 2) + 0.5)
            kf += 1
        if L > 6.0 and gaps:
            # the long wall with the wood door: two white double closets right beside it (ru_os_matthews_3)
            g0, g1 = min(gaps, key=lambda g: abs((g[0] + g[1]) / 2 - L / 2))
            side = 1.0 if (L - g1) > g0 else -1.0
            s_ = g1 if side > 0 else g0
            for k in range(2):
                for leaf in range(2):
                    c0 = s_ + side * (0.05 + k * 1.45 + leaf * 0.66)
                    c1 = c0 + side * 0.64
                    R.panel(V, at(min(c0, c1)), at(max(c0, c1)), z + 0.02, z + 2.35, "int_ru_wainscot", off=0.02,
                            u0=0.0, u1=1.0, v0=0.0, v1=2.0)
            cl0, cl1 = sorted((s_, s_ + side * (0.05 + 1.45 + 1.32 + 0.2)))
            nxt = []
            for s0_, s1_ in spans:
                if cl1 <= s0_ or cl0 >= s1_:
                    nxt.append((s0_, s1_))
                    continue
                if cl0 > s0_:
                    nxt.append((s0_, cl0))
                if cl1 < s1_:
                    nxt.append((cl1, s1_))
            spans = nxt
        for s0_, s1_ in spans:
            w = s1_ - s0_
            m = (s0_ + s1_) / 2
            if w >= 2.2:
                # a row of three, the centre one larger (ru_os_matthews_4's far wall)
                frame(m, 0.34, z + 1.30, z + 2.15)
                frame(m - 0.75, 0.24, z + 1.50, z + 2.05)
                frame(m + 0.75, 0.24, z + 1.50, z + 2.05)
                if w >= 3.6:
                    for sg in (-1.0, 1.0):
                        for z0_ in (z + 1.15, z + 1.85):
                            frame(m + sg * 1.45, 0.22, z0_, z0_ + 0.55)
            elif w >= 1.3:
                # a 2 x 2 group (ru_os_matthews_3 / _4 side walls)
                for sg in (-1.0, 1.0):
                    for z0_ in (z + 1.15, z + 1.85):
                        frame(m + sg * 0.3, 0.22, z0_, z0_ + 0.55)
            elif w >= 0.6:
                for z0_ in (z + 1.15, z + 1.85):
                    frame(m, 0.22, z0_, z0_ + 0.55)
    _crown(F, an, V, zc)


ARREDONDO_COLUMN = (-437.5, -262.5)    # the stone-clad column mid-room (ru_os_arredondo_cafe; position estimated)
ARREDONDO_SCREEN = (-421.8, -265.0, 4.8)   # projection screen: x of its face, centre y, width (fidelity-4 round 2)


def _arredondo_dress(RZ, F, ar):
    """Arredondo Cafe (ru_os_arredondo_cafe): the stone-clad central column and roller shades on the window wall,
    lowered to different heights bay by bay."""
    z = F.z
    zc = z + ar.style["clear"]
    P = K.Prop("arredondo_dress")
    V, C = P.visual, P.collision
    cx, cy = ARREDONDO_COLUMN
    if R.pip((cx, cy), ar.poly):
        V.box(cx - 0.45, cy - 0.45, z, cx + 0.45, cy + 0.45, zc, "int_ru_stone_clad", faces="+x-x+y-y")
        V.box(cx - 0.5, cy - 0.5, z, cx + 0.5, cy + 0.5, z + 0.12, "int_ru_black", faces="+x-x+y-y+z")
        K.col_box(C, cx - 0.45, cy - 0.45, z, cx + 0.45, cy + 0.45, zc, K.COL)
    k = 0
    ring = [zn_ for zn_ in (ar, F.zone("l4_corridor_04")) if zn_ is not None]     # OPEN_PAIRS: one space
    for a, b in [e for zn_ in ring for e in R.edges(list(reversed(R.ccw(zn_.poly))))]:
        L = math.dist(a, b)
        if L < 1.5:
            continue
        dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx, ny = dy, -dx                                  # into the room
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        if F.cls_at((mid[0] - nx * 0.45, mid[1] - ny * 0.45))[0] != "O":
            continue
        n = max(1, int(round(L / 1.6)))
        for j in range(n):
            s0, s1 = L * j / n + 0.04, L * (j + 1) / n - 0.04
            drop = (0.7, 1.3, 1.0, 1.6, 0.9)[k % 5]
            k += 1
            _wall_strip(V, (a[0] + dx * s0, a[1] + dy * s0), (a[0] + dx * s1, a[1] + dy * s1), zc - 0.12 - drop,
                        zc - 0.05, "int_ru_shade", off=EXT_T / 2 + 0.12)
        _wall_strip(V, a, b, zc - 0.14, zc - 0.02, "int_ru_white", off=EXT_T / 2 + 0.16)
    # fidelity-4 round 2: the large ceiling-hung projection screen centred on the far (east) end, the focal point of
    # ru_os_arredondo_cafe, in front of the east glass (corridor-04 strip), with its case + rods, and the ceiling
    # projector mid-room. Visual only (the screen's foot is 1.6 m up).
    sx_, sy_, sw_ = ARREDONDO_SCREEN
    R.panel(V, (sx_, sy_ + sw_ / 2), (sx_, sy_ - sw_ / 2), z + 1.25, z + 3.95, "int_ru_proj_screen", off=0.0)
    R.panel(V, (sx_ + 0.01, sy_ - sw_ / 2), (sx_ + 0.01, sy_ + sw_ / 2), z + 1.25, z + 3.95, "int_ru_black", off=0.0)
    V.box(sx_ - 0.08, sy_ - sw_ / 2 - 0.15, z + 3.95, sx_ + 0.1, sy_ + sw_ / 2 + 0.15, z + 4.1, "int_ru_black",
          faces="+x-x+y-y-z")
    for dy_ in (-sw_ / 2 + 0.2, sw_ / 2 - 0.2):
        V.box(sx_ - 0.015, sy_ + dy_ - 0.015, z + 4.1, sx_ + 0.015, sy_ + dy_ + 0.015, zc, "int_ru_steel", faces="+x-x+y-y")
    px_, py_ = -437.0, sy_
    V.box(px_ - 0.22, py_ - 0.2, zc - 0.5, px_ + 0.22, py_ + 0.2, zc - 0.36, "int_ru_white", faces="+x-x+y-y-z")
    V.box(px_ - 0.03, py_ - 0.03, zc - 0.36, px_ + 0.03, py_ + 0.03, zc, "int_ru_steel", faces="+x-x+y-y")
    V.box(px_ + 0.22, py_ - 0.07, zc - 0.47, px_ + 0.23, py_ + 0.07, zc - 0.39, "int_ru_black", faces="+x")
    RZ.kit_add(P, "L4", tag="arredondo_dress")


def hotel(RZ):
    """Reitz Union Hotel (L5-L6): the corridor; room 516 (queen bed with royal-blue skirt, cherry headboard,
    nightstands + lamps, dresser + TV, the royal-blue accent wall; ru_hotel_room), suite 501/502 (_hotel_suite: the
    sitting room of ru_hotel_suite + a bedroom) and room 516's balcony (white slotted balustrade;
    ru_hotel_balcony). Every other room is a closed door."""
    F = RZ.floors["L5"]
    z = F.z
    r516 = F.zone("hotel_room_516")
    mx, my, facing, W, D = _room_frame(r516)
    f = math.radians(facing)
    fx, fy = math.sin(f), math.cos(f)
    # ru_hotel_room: the royal-blue accent wall carries the cherry dresser + wall TV + mirror; the cherry headboard
    # stands on the cream wall opposite
    RZ.kit_add(R.bed_set(), "L5", tag="hotel_bed", x=mx + fx * (D - 0.15), y=my + fy * (D - 0.15), z=z,
               facing=(facing + 180.0) % 360)
    _hotel_516(RZ, F, r516, mx, my, fx, fy)
    _hotel_suite(RZ, F, F.zone(SUITE_ID))
    # balcony balustrade (white slotted concrete) along the outer edge of balcony 8
    bal = F.zone("l5_hotel_balcony_8")
    P = K.Prop("hotel_balcony")
    V, C = P.visual, P.collision
    if bal is not None:
        x0, y0, x1, y1 = R.bbox(bal.poly)
        ra, rb = (x1 - 0.1, y0), (x1 - 0.1, y1)
        # fix round 4 (fidelity-4 pass; ru_hotel_balcony): real open slots, not black boxes on a solid wall: a low
        # white curb, a deep white top rail and white fins ~0.16 m wide with ~0.24 m of open sky between them (the
        # collision stays one solid 1.1 m wall: the slots are far too narrow for Mario anyway)
        R.seg_box(V, ra, rb, 0.1, z, z + 0.2, "int_ru_white", faces="sideends_top")
        R.seg_box(V, ra, rb, 0.13, z + 0.9, z + 1.1, "int_ru_white", faces="sideends_top_bot")
        nf = int((y1 - y0 - 0.16) / 0.4)
        f0 = y0 + (y1 - y0 - nf * 0.4) / 2
        for k in range(nf + 1):
            yy = f0 + k * 0.4
            V.box(x1 - 0.2, yy - 0.08, z + 0.2, x1, yy + 0.08, z + 0.9, "int_ru_white", faces="+x-x+y-y")
        R.col_seg(C, ra, rb, 0.1, z, z + 1.1, K.COL)
        # fix round 4 (fidelity-4 pass; ru_hotel_balcony): the cream soffit overhead (the underside of the Level 6
        # balcony) with a deep cream edge beam along the outer side; a ceiling collision face to match
        zs = z + bal.style.get("clear", CLEAR["L5"]) if bal.style else z + CLEAR["L5"]
        # fix round 5 (fidelity-4 / technical blocking): 1.5 cm under the zone's own int_ru_soffit (it lay exactly on
        # it at zs and z-fought over the balcony)
        V.poly([(x0, y0, zs - 0.015), (x0, y1, zs - 0.015), (x1, y1, zs - 0.015), (x1, y0, zs - 0.015)],
               "int_ru_wall_cream", normal_hint=(0, 0, -1), ao=1.0)
        R.seg_box(V, (x1 - 0.16, y0), (x1 - 0.16, y1), 0.16, zs - 0.42, zs - 0.01, "int_ru_wall_cream",
                  faces="sideends_bot")
        C.poly([(x0, y0, zs), (x0, y1, zs), (x1, y1, zs), (x1, y0, zs)], K.COL)
        RZ.kit_add(R.high_top(1.0, 0.3, 2), "L5", tag="balcony_table", x=(x0 + x1) / 2 - 0.2, y=(y0 + y1) / 2, z=z)
    RZ.kit_add(P, "L5", tag="hotel_balcony")
    # hotel corridor sign by the elevators
    P2 = K.Prop("hotel_sign")
    R.panel(P2.visual, (-444.0, -272.6), (-446.4, -272.6), z + 2.2, z + 3.4, "int_ru_sign_hotel", off=0.0, glow=True)
    RZ.kit_add(P2, "L5", tag="hotel_sign")


def _pleats(V, x0, x1, y_wall, z0, z1, mat, n, d0=0.04, d1=0.12):
    """A pleated curtain on a wall facing +y (the wall face at y_wall): n folds between x0 and x1."""
    pts = [(x0 + (x1 - x0) * k / (2 * n), y_wall + (d1 if k % 2 else d0)) for k in range(2 * n + 1)]
    for a, b in zip(pts, pts[1:]):
        V.poly([(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)], mat, normal_hint=(0, 1, 0),
               ao=1.0)


def _hotel_suite(RZ, F, zn):
    """Suite 501 / 502 (fidelity-4 round 2; ru_hotel_suite). The plan zone is two rooms (two corridor doors): a
    partition at SUITE_SPLIT_Y makes the south part the sitting room the photo shows and the north part the bedroom.
    The photo looks at the solid east wall (back wall: the blue sofa between two cherry end tables with white-shade
    lamps, a framed aqua print over it, a cherry coffee table), with the royal-blue accent wall + a large palm print
    on the left (the partition's south face) and the window wall on the right (the balcony side: pleated gold drapes,
    a white sheer, a navy patterned valance); two rounded butterscotch leather loveseats face each other across the
    coffee table. Preview camera reitz_hotel_suite."""
    if zn is None:
        return
    z = F.z
    zc = z + zn.style["clear"]
    P = K.Prop("hotel_suite")
    V, C = P.visual, P.collision
    ys0, ys1 = SUITE_SPLIT_Y - 0.1, SUITE_SPLIT_Y + 0.1          # partition faces
    xw, xe = -445.8, -440.65                                     # into the west wall .. the window-notch wall face
    V.box(xw, ys0, z, xe, ys1, zc, "int_ru_wall", faces="+y-y", mats={"-y": "int_ru_wall_royal"})
    V.box(xw, ys0 - 0.015, z, xe, ys0, z + 0.1, "int_ru_black", faces="-y+z")
    V.box(xw, ys1, z, xe, ys1 + 0.015, z + 0.1, "int_ru_black", faces="+y+z")
    K.col_box(C, xw, ys0, z, xe, ys1, zc, K.COL)
    # sitting room: back (east) wall face x -440.0, window wall face y -289.25
    xb, yw = -440.0, -289.25
    yc = (yw + ys0) / 2
    RZ.kit_add(R.sofa(2.0), "L5", tag="suite_sofa", x=xb - 0.02, y=yc, z=z, facing=270.0)
    for j, dy in enumerate((-1.42, 1.42)):
        RZ.kit_add(R.lamp_table(), "L5", tag=f"suite_lamp_{j}", x=xb - 0.33, y=yc + dy, z=z)
    # framed aqua print over the sofa (right half of int_ru_print_suite), shadow-box sides
    R.panel(V, (xb, yc + 0.6), (xb, yc - 0.6), z + 1.25, z + 1.95, "int_ru_print_suite", off=0.05, u0=0.5, u1=1.0)
    V.box(xb - 0.05, yc - 0.6, z + 1.25, xb, yc + 0.6, z + 1.95, "int_ru_black", faces="+y-y+z-z")
    # the large palm print on the blue partition (left half)
    R.panel(V, (-443.7, ys0), (-441.8, ys0), z + 1.2, z + 2.15, "int_ru_print_suite", off=0.05, u0=0.0, u1=0.5)
    V.box(-443.7, ys0 - 0.05, z + 1.2, -441.8, ys0, z + 2.15, "int_ru_black", faces="+x-x+z-z")
    # cherry coffee table + the two loveseats facing each other, turned a little toward the room
    V.box(-442.15, yc - 0.6, z + 0.38, -441.55, yc + 0.6, z + 0.44, "int_ru_cherry", faces="+x-x+y-y+z")
    for sx_ in (-442.1, -441.6):
        for sy_ in (yc - 0.55, yc + 0.5):
            V.box(sx_, sy_, z, sx_ + 0.05, sy_ + 0.05, z + 0.38, "int_ru_cherry", faces="+x-x+y-y")
    K.col_box(C, -442.15, yc - 0.6, z, -441.55, yc + 0.6, z + 0.44, K.COL_NOCAM)
    RZ.kit_add(R.loveseat_round(), "L5", tag="suite_loveseat_n", x=-442.35, y=ys0 - 0.42, z=z, facing=200.0)
    RZ.kit_add(R.loveseat_round(), "L5", tag="suite_loveseat_s", x=-442.35, y=yw + 0.47, z=z, facing=340.0)
    # window wall: navy valance across, gold drapes at both ends (the east one over the balcony slider), a sheer
    V.box(-445.78, yw, z + 3.0, xb, yw + 0.22, z + 3.45, "int_ru_valance_navy", faces="+y-z")
    _pleats(V, -441.05, xb - 0.03, yw, z + 0.02, z + 3.0, "int_ru_drape_gold", 4)
    _pleats(V, -445.74, -445.0, yw, z + 0.02, z + 3.0, "int_ru_drape_gold", 3)
    _pleats(V, -442.3, -441.05, yw, z + 0.02, z + 3.0, "int_ru_bed", 5, d0=0.02, d1=0.06)
    P.lights.append(K.Light((-442.6, yc, z + 3.2), radius=6.0, strength=0.3, color=LIGHT_WARM))
    P.lights.append(K.Light((-441.2, yc, z + 2.2), radius=3.5, strength=0.22, color=LIGHT_WARM))
    RZ.kit_add(P, "L5", tag="hotel_suite")
    # bedroom (502): the bed's headboard against the partition's north face
    RZ.kit_add(R.bed_set(), "L5", tag="suite_bed", x=-443.25, y=ys1 + 0.02, z=z, facing=0.0)


def _hotel_516(RZ, F, zn, mx, my, fx, fy):
    """Room 516 (ru_hotel_room). Fidelity-4 round 2: the photo looks north with the royal-blue wall on the LEFT
    carrying the cherry dresser and the wall TV, the cherry headboard + nightstands + lamps AHEAD (the north wall,
    hotel()) and the window on the right (the balcony glass). So the royal blue is the east face of the entry / bath
    block in the room's west bay (the plan's notch beside the corridor door), which carries the dresser + TV, with
    the bath door at its south end; the room frame's south wall stays cream with the cherry desk + navy chair, and
    the cherry-framed mirror hangs on the notch wall (x -429.6). The room-frame origin (mx, my) is the south wall
    centre, facing (fx, fy) into the room."""
    z = F.z
    P = K.Prop("hotel_516")
    V, C = P.visual, P.collision
    tx, ty = fy, -fx                                   # along the south wall (right of facing)
    w0 = 0.12                                          # the wall face, from the room frame origin

    def Wp(u, v):
        return (mx + tx * u + fx * v, my + ty * u + fy * v)

    def wbox(u0, u1, v0, v1, z0, z1, mat, faces, col=None):
        ps = [Wp(u0, v0), Wp(u1, v1)]
        bx0, by0 = min(p[0] for p in ps), min(p[1] for p in ps)
        bx1, by1 = max(p[0] for p in ps), max(p[1] for p in ps)
        V.box(bx0, by0, z0, bx1, by1, z1, mat, faces=faces)
        if col:
            K.col_box(C, bx0, by0, z0, bx1, by1, z1, col)
    # desk + navy chair on the cream south wall, west of the camera corner
    wbox(-2.1, -0.9, w0, w0 + 0.62, z + 0.72, z + 0.76, "int_ru_cherry", "+x-x+y-y+z-z")
    for uu in (-2.05, -0.95):
        wbox(uu - 0.04, uu + 0.04, w0 + 0.04, w0 + 0.58, z, z + 0.72, "int_ru_cherry", "+x-x+y-y")
    wbox(-1.75, -1.25, w0 + 0.75, w0 + 1.25, z, z + 0.46, "int_ru_fabric_navy", "+x-x+y-y+z")
    wbox(-1.75, -1.25, w0 + 1.17, w0 + 1.25, z + 0.46, z + 0.95, "int_ru_fabric_navy", "+x-x+y-y+z")
    # entry / bath block: the west bay beside the corridor door (x < -430.65), wall-high; its east face is the blue
    # wall of the photo
    x0, y0, x1, y1 = R.bbox(zn.poly)
    notch_y = max(p[1] for p in zn.poly if p[0] < x0 + 0.2 and p[1] < (y0 + y1) / 2)   # -272.3: the notch's south wall
    bx0, bx1 = x0 + 0.1, x0 + 1.55
    by0, by1 = notch_y + 0.1, y1 - 0.1
    zt = z + zn.style["clear"]
    V.box(bx0, by0, z, bx1, by1, zt, "int_ru_wall_royal", faces="+x")
    V.box(bx1, by0 + 1.0, z, bx1 + 0.015, by1, z + 0.1, "int_ru_wall", faces="+x+z-y")
    C.poly([(bx1, by0, z), (bx1, by1, z), (bx1, by1, zt), (bx1, by0, zt)], K.COL)     # the only exposed face (+x)
    door_leaves(V, (bx1, by0 + 0.1), (bx1, by0 + 0.95), z, 2.2, "int_ru_door_hotel")
    # dresser (1.8 m, cherry, drawer reveals) on the blue face, the TV on the wall above it
    yd0, yd1 = by0 + 1.15, by0 + 2.95
    V.box(bx1, yd0, z, bx1 + 0.55, yd1, z + 0.86, "int_ru_cherry", faces="+x+y-y+z")
    K.col_box(C, bx1, yd0, z, bx1 + 0.55, yd1, z + 0.86, K.COL_NOCAM)
    for k in range(1, 3):
        R.panel(V, (bx1 + 0.555, yd0 + 0.02), (bx1 + 0.555, yd1 - 0.02), z + 0.28 * k, z + 0.28 * k + 0.02,
                "int_ru_black", off=0.0)
    ym = (yd0 + yd1) / 2
    V.box(bx1, ym - 0.72, z + 1.18, bx1 + 0.03, ym + 0.72, z + 2.02, "int_ru_black", faces="+y-y+z-z")
    R.panel(V, (bx1, ym - 0.7), (bx1, ym + 0.7), z + 1.2, z + 2.0, "int_ru_tv_hotel", off=0.035)
    # cherry-framed mirror on the notch wall (x -429.6, facing east)
    xm = -429.5
    V.box(xm, -273.9, z + 0.95, xm + 0.03, -273.2, z + 2.15, "int_ru_cherry", faces="+x+y-y+z-z")
    R.panel(V, (xm, -273.84), (xm, -273.26), z + 1.01, z + 2.09, "int_ru_glass", off=0.035, ao=1.0)
    RZ.kit_add(P, "L5", tag="hotel_516")


def hotel_reception(RZ):
    """Reitz Union Hotel reception (Ground; plan prop reitz_union_hotel_reception_desk along the west wall, x ~-456.8,
    y -273.0..-267.9; no photo, so built from the house finishes): a honey-wood front counter with a navy reveal, a
    white top and a black kick, a white back counter, the royal-blue sign wall with REITZ UNION HOTEL, two monitors
    and three drum pendants over the desk."""
    F = RZ.floors["G"]
    z = F.z
    zn = F.zone("hotel_reception")
    if zn is None:
        return
    P = K.Prop("hotel_reception")
    V, C = P.visual, P.collision
    west = min(_room_inside_edges(zn, WALL_T / 2 + 0.01), key=lambda e: e[0][0] + e[1][0])
    (wa, wb) = west

    def wx(y):
        return wa[0] + (wb[0] - wa[0]) * (y - wa[1]) / (wb[1] - wa[1])
    ys, yn = -272.9, -268.0
    x0 = max(wx(ys), wx(yn)) + 0.01
    # royal-blue sign wall behind the desk + the lit hotel sign
    R.panel(V, (wx(-273.6), -273.6), (wx(-267.3), -267.3), z + 0.10, z + 3.8, "int_ru_wall_royal", off=0.012)
    R.panel(V, (wx(-271.65), -271.65), (wx(-269.25), -269.25), z + 2.3, z + 3.5, "int_ru_sign_hotel", off=0.03,
            glow=True)
    # back counter (white) on the wall
    V.box(x0, ys + 0.1, z, x0 + 0.55, yn - 0.1, z + 0.9, "int_ru_white", faces="+x-y+y+z")
    K.col_box(C, x0, ys + 0.1, z, x0 + 0.55, yn - 0.1, z + 0.9, K.COL_NOCAM)
    # front counter: wood front, navy reveal, white transaction top, black kick
    fx0, fx1 = x0 + 1.25, x0 + 1.95
    V.box(fx0, ys, z + 0.12, fx1, yn, z + 1.05, "int_ru_wood_panel", faces="+x-x+y-y")
    V.box(fx0 + 0.05, ys + 0.05, z, fx1 - 0.05, yn - 0.05, z + 0.12, "int_ru_black", faces="+x-x+y-y")
    V.box(fx0 - 0.05, ys - 0.05, z + 1.05, fx1 + 0.05, yn + 0.05, z + 1.10, "int_ru_white", faces="+x-x+y-y+z-z")
    V.box(fx0 - 0.30, ys + 0.05, z + 0.74, fx0, yn - 0.05, z + 0.78, "int_ru_white", faces="-x+y-y+z-z")
    R.panel(V, (fx1, ys), (fx1, yn), z + 0.84, z + 0.94, "int_ru_counter_navy", off=0.012)
    for yy in (ys, yn):
        nrm = -1 if yy == ys else 1
        R.panel(V, (fx0, yy) if nrm < 0 else (fx1, yy), (fx1, yy) if nrm < 0 else (fx0, yy), z + 0.84, z + 0.94,
                "int_ru_counter_navy", off=0.012)
    K.col_box(C, fx0 - 0.05, ys - 0.05, z, fx1 + 0.05, yn + 0.05, z + 1.10, K.COL_NOCAM)
    # two monitors on the staff side, backs to the lobby
    for my_ in (-271.4, -269.5):
        V.box(fx0 - 0.2, my_ - 0.26, z + 0.78, fx0 - 0.16, my_ + 0.26, z + 1.12, "int_ru_black", faces="+x-x+y-y+z")
        R.panel(V, (fx0 - 0.21, my_ + 0.24), (fx0 - 0.21, my_ - 0.24), z + 0.80, z + 1.10, "int_ru_game_screen",
                off=0.0, glow=True)
    # drum pendants over the counter (navy shades, glowing undersides) + warm light
    zc = z + zn.style["clear"]
    for py in (-272.0, -270.45, -268.9):
        px = (fx0 + fx1) / 2
        V.box(px - 0.015, py - 0.015, z + 3.2, px + 0.015, py + 0.015, zc, "int_ru_black", faces="+x-x+y-y")
        R.cyl(V, px, py, 0.24, z + 2.95, z + 3.2, "int_ru_wall_navy", n=8, top=True, bottom=False)
        V.poly([(px + 0.22 * math.cos(2 * math.pi * k / 8), py + 0.22 * math.sin(2 * math.pi * k / 8), z + 2.96)
                for k in reversed(range(8))], "int_ru_led", glow=True, tint=(1.0, 0.92, 0.78), normal_hint=(0, 0, -1))
        P.lights.append(K.Light((px, py, z + 2.6), radius=4.0, strength=0.3, color=LIGHT_WARM))
    RZ.kit_add(P, "G", tag="hotel_reception")


def _acc_studio(V, C, z):
    """fix round 4 (design pass, improvement 4; ru_acc_studio 'tables, shelving'; the pottery corner is inferred: the
    ACC runs wheel-throwing classes): the LL was the barest floor (0.7 prop tris / m2). Along the ACC's north wall a
    wood cubby unit (6 x 3 open cubbies, a few bright supply bins) and a steel work-sink counter; across the south
    end three pottery wheels (grey splash pans, steel wheel heads, stools) and an electric kiln in the SW corner.
    Low collision blocks (no camera collision); the door strip at x -447.3..-445.4 and the table aisles stay clear."""
    # cubby unit against the north wall (inside face ~ y -244.65)
    yb, yf, x0, x1, h = -244.68, -245.08, -457.8, -453.0, 1.5
    V.box(x0, yf, z, x1, yb, z + h, "int_ru_black", faces="-y+x-x+z")
    ncol, nrow = 6, 3
    for i in range(ncol + 1):
        xx = x0 + (x1 - x0) * i / ncol
        V.box(xx - 0.025, yf - 0.03, z, xx + 0.025, yf, z + h, "int_ru_maple_panel", faces="-y+x-x+z")
    for j in range(nrow + 1):
        zz = z + 0.06 + (h - 0.08) * j / nrow
        V.box(x0, yf - 0.03, zz - 0.025, x1, yf, zz + 0.025, "int_ru_maple_panel", faces="-y+z-z")
    # fix round 5 (design pass, improvement 4): the cubby unit read as a thin dark strip at camera distance: 12 of
    # the 18 cubbies hold saturated supply bins (orange / blue / green / red / lime / sky)
    bins = ("int_ru_orange_uf", "int_ru_uf_blue", "int_ru_gator_green", "int_ru_red", "int_ru_paint_lime",
            "int_ru_paint_sky", "int_ru_uf_blue", "int_ru_orange_uf", "int_ru_red", "int_ru_gator_green",
            "int_ru_paint_sky", "int_ru_orange_uf")
    for k, (ci, rj) in enumerate(((0, 0), (1, 0), (2, 0), (3, 0), (5, 0), (0, 1), (2, 1), (3, 1), (4, 1), (1, 2),
                                  (3, 2), (5, 2))):
        cx0 = x0 + (x1 - x0) * ci / ncol + 0.08
        cx1 = x0 + (x1 - x0) * (ci + 1) / ncol - 0.08
        zb = z + 0.06 + (h - 0.08) * rj / nrow + 0.03
        V.box(cx0, yf - 0.01, zb, cx1, yb - 0.05, zb + 0.28, bins[k], faces="-y+x-x+z")
    K.col_box(C, x0, yf - 0.03, z, x1, yb, z + h, K.COL_NOCAM)
    # work-sink counter (two basins), east of the cubbies
    sx0, sx1, sy0 = -451.9, -448.7, -245.28
    V.box(sx0, sy0, z, sx1, yb, z + 0.88, "int_ru_white", faces="-y+x-x")
    V.box(sx0 - 0.02, sy0 - 0.02, z + 0.88, sx1 + 0.02, yb, z + 0.92, "int_ru_steel", faces="-y+x-x+z")
    for bx in (-451.0, -449.6):
        V.box(bx - 0.4, sy0 + 0.08, z + 0.921, bx + 0.4, yb - 0.08, z + 0.94, "int_ru_black", faces="+z")
        V.box(bx - 0.02, yb - 0.1, z + 0.92, bx + 0.02, yb - 0.06, z + 1.22, "int_ru_steel", faces="+x-x-y+z")
        V.box(bx - 0.02, yb - 0.3, z + 1.18, bx + 0.02, yb - 0.06, z + 1.22, "int_ru_steel", faces="+x-x-y+z-z")
    V.box(sx0, sy0 - 0.005, z + 0.05, sx1, sy0, z + 0.12, "int_ru_black", faces="-y")      # kick
    K.col_box(C, sx0, sy0, z, sx1, yb, z + 0.92, K.COL_NOCAM)
    # three pottery wheels across the south end (thrower faces north), stools behind
    # fix round 5 (design pass, improvement 4): at 6.5-10 m the wheels read as grey boxes: a wide white 8-sided
    # splash pan on each body and a terracotta clay lump on the wheel head (the round head reads from the camera)
    for wx in (-455.0, -452.6, -450.2):
        wy = -265.5
        V.box(wx - 0.32, wy - 0.38, z, wx + 0.32, wy + 0.38, z + 0.42, "int_ru_wall_grey", faces="+x-x+y-y+z")
        R.cyl(V, wx, wy + 0.06, 0.34, z + 0.42, z + 0.56, "int_ru_white", n=8, top=True, bottom=False)   # splash pan
        R.cyl(V, wx, wy + 0.06, 0.15, z + 0.56, z + 0.76, "int_ru_clay", n=8, top=True, bottom=False)    # clay lump
        R.cyl(V, wx, wy - 0.85, 0.17, z, z + 0.48, "int_ru_black", n=6, top=True, bottom=False)          # stool
        K.col_box(C, wx - 0.32, wy - 0.38, z, wx + 0.32, wy + 0.38, z + 0.56, K.COL_NOCAM)
    # electric kiln in the SW corner (octagonal steel drum on a stand, a grey lid)
    # fix round 5 (design pass, improvement 4): a ~1 m bright steel drum with a grey lid and a black lid handle
    kx, ky = -457.9, -266.7
    R.cyl(V, kx, ky, 0.5, z + 0.2, z + 1.0, "int_ru_steel_bright", n=8, top=False, bottom=False)
    R.cyl(V, kx, ky, 0.53, z + 1.0, z + 1.08, "int_ru_wall_grey", n=8, top=True, bottom=False)
    V.box(kx - 0.18, ky - 0.03, z + 1.08, kx + 0.18, ky + 0.03, z + 1.13, "int_ru_black", faces="+x-x+y-y+z")  # handle
    V.box(kx - 0.35, ky - 0.35, z, kx + 0.35, ky + 0.35, z + 0.2, "int_ru_black", faces="+x-x+y-y")
    V.box(kx + 0.08, ky + 0.50, z + 0.5, kx + 0.3, ky + 0.52, z + 0.72, "int_ru_black", faces="+y+x-x+z")  # control box
    K.col_box(C, kx - 0.53, ky - 0.53, z, kx + 0.53, ky + 0.53, z + 1.08, K.COL_NOCAM)
    # fix round 5 (design pass, improvement 4; ru_acc_studio: student work on every wall): a band of student
    # paintings on the blank south wall (its face is slightly skewed: y -267.688 at x -447.9, -267.521 at x -457.8,
    # measured on the export) and the two east step walls (faces x -447.4 south of the door strip, x -447.2 north
    # of the mural), 1.7 cm off the wall (no coplanar faces), above the wheels and the kiln
    def yf_(x_):
        return -267.688 - 0.01687 * (x_ + 447.9)
    # (1.0 x 1.3 m each: the first 0.8 x 1.1 m try read as small frames from the 10 m camera). The west wall
    # north of the book shelf gets six more (its face: x -458.569 at y -246.5, -458.677 at y -259.2)
    def xw_(y_):
        return -458.569 + 0.0085 * (y_ + 246.5)
    k = 0
    for i in range(8):
        xe = -447.9 - i * 1.3
        R.panel(V, (xe, yf_(xe)), (xe - 1.0, yf_(xe - 1.0)), z + 1.35, z + 2.65, "int_ru_student_art", off=0.017,
                u0=(k % 4) * 0.25, u1=(k % 4) * 0.25 + 0.25)
        k += 1
    for xw, yn in ((-447.4, -264.2), (-447.4, -265.9), (-447.2, -249.9), (-447.2, -251.6)):
        R.panel(V, (xw, yn), (xw, yn - 1.0), z + 1.35, z + 2.65, "int_ru_student_art", off=0.017,
                u0=(k % 4) * 0.25, u1=(k % 4) * 0.25 + 0.25)
        k += 1
    for i in range(6):
        ys = -258.6 + i * 2.0
        R.panel(V, (xw_(ys), ys), (xw_(ys + 1.0), ys + 1.0), z + 1.35, z + 2.65, "int_ru_student_art", off=0.017,
                u0=(k % 4) * 0.25, u1=(k % 4) * 0.25 + 0.25)
        k += 1


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
        _acc_studio(V, C, z)
    # the ACC mural on the public face of the ACC's east wall (its inside face, between the door to ll_room_32 and
    # the IT office corner; the old spot faced into the sealed ll_room_33 and could not be seen)
    R.panel(V, (-445.66, -257.9), (-445.66, -261.9), z + 0.6, z + 4.6, "int_ru_mural_acc", off=0.0)
    RZ.kit_add(P, "LL", tag="ll_misc")


DRESSERS.extend([grand_ballroom, rion_ballroom, auditorium, gallery, senate_chamber, meeting_rooms, level4, hotel,
                 hotel_reception,
                 lower_level])


# ================================================================== fix round 2, design pass: circulation + south hall
# The LL / L2 / L3 circulation (1,114 / 3,902 / 2,440 m2 of reachable floor) read as long blank white walls over bare
# floor with only wood doors. Room-number plaques beside the room doors, framed UF prints and cork bulletin boards
# every ~5 m on the solid corridor walls (ru_os_g310_g320: framed art rows), navy lounge groups on rugs and benches
# in the wide L2 pre-function hall west of the atrium, benches against the core walls on LL / L2 / L3. The L1 south
# hall (the Bookstore link) gets benches, planters and the UF BOOKSTORE sign over the link doors.
DRESS_FLOORS = ("LL", "L2", "L3")
ART_SKIP = [("LL", (-446.2, -262.4, -445.1, -257.4))]       # the LL accent mural (lower_level)
SOLID_TYPES = {"meeting_room", "ballroom", "auditorium", "studio", "office", "chamber", "room", "restroom", "service",
               "elevator", "storage", "lounge", "hotel_room", "double_height"}     # (no glass storefront types)
PLAQUE_TYPES = {"meeting_room", "ballroom", "auditorium", "gallery", "studio", "office", "office_suite", "chamber",
                "room", "restroom"}


def _span_clear_of_doors(F, a, u, s0, s1, pad=0.35):
    """True when the stretch s0..s1 of the wall line a + u*s keeps pad metres clear of every plan door on it."""
    for d in F.doors:
        da, db = (d[0], d[1]), (d[2], d[3])
        dm = ((da[0] + db[0]) / 2, (da[1] + db[1]) / 2)
        # distance of the door's midpoint from the wall line
        rx, ry = dm[0] - a[0], dm[1] - a[1]
        if abs(rx * u[1] - ry * u[0]) > 0.35:
            continue
        t0 = (da[0] - a[0]) * u[0] + (da[1] - a[1]) * u[1]
        t1 = (db[0] - a[0]) * u[0] + (db[1] - a[1]) * u[1]
        lo, hi = min(t0, t1), max(t0, t1)
        if hi > s0 - pad and lo < s1 + pad:
            return False
    return True


def _corridor_at(F, p):
    """The corridor zone at p (the smallest zone there is a walkable corridor), else None."""
    cls, z = F.cls_at(p)
    return z if (cls == "W" and z is not None and z.type == "corridor") else None


def _face_off(F, c, nout, gap=0.04, default=None):
    """fix round 4 (technical blocking; the round-1 chevron lesson): the offset along nout from the point c (on a
    room polygon edge) to just proud (gap) of the BUILT wall face: the nearest parallel plan wall within 0.4 m, its
    face WALL_T / 2 (EXT_T / 2 on the facade) toward nout. The room polygons are not the wall centre-lines (up to
    several cm off), so a fixed WALL_T / 2 + 1.2 cm left decals coplanar with or behind the wall."""
    best = None
    for w in F.walls:
        a, b = (w[0], w[1]), (w[2], w[3])
        L = math.dist(a, b)
        if L < 0.3:
            continue
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        if abs(ux * nout[0] + uy * nout[1]) > 0.05:
            continue
        t_ = (c[0] - a[0]) * ux + (c[1] - a[1]) * uy
        if t_ < -0.05 or t_ > L + 0.05:
            continue
        d = (c[0] - a[0]) * nout[0] + (c[1] - a[1]) * nout[1]
        if abs(d) > 0.4:
            continue
        if best is None or abs(d) < abs(best):
            best = d
    if best is None:
        return default if default is not None else WALL_T / 2 + gap
    ext = F.cls_at((c[0] + nout[0] * 0.6, c[1] + nout[1] * 0.6))[0] == "O"
    return -best + (EXT_T if ext else WALL_T) / 2 + gap


def _corridor_art(RZ, F, P):
    """Plaques beside the room doors and art on the room walls that face a corridor. Walks the ROOMS' outlines
    (outward = right of the CCW edge), because many room blocks sit as islands inside the big corridor polygons."""
    V = P.visual
    z = F.z
    k_art = 0
    n_plq = 0
    off = WALL_T / 2 + 0.012
    for oz in F.zones:
        if oz.type not in SOLID_TYPES or oz.cls not in ("S", "W"):
            continue
        # -- room-number plaques beside the doors into rooms (0.15 x 0.3 m, latch side, 1.4-1.7 m)
        if oz.type in PLAQUE_TYPES:
            for a, b, mid, nin in _room_doors(F, oz):
                if _corridor_at(F, (mid[0] - nin[0] * 0.6, mid[1] - nin[1] * 0.6)) is None:
                    continue
                L = math.dist(a, b)
                u = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
                for end, sg in ((b, 1.0), (a, -1.0)):
                    c = (end[0] + u[0] * sg * 0.32, end[1] + u[1] * sg * 0.32)
                    if not oz.contains((c[0] + nin[0] * 0.45, c[1] + nin[1] * 0.45)) or \
                            _corridor_at(F, (c[0] - nin[0] * 0.6, c[1] - nin[1] * 0.6)) is None:
                        continue
                    if not _span_clear_of_doors(F, c, u, -0.12, 0.12, pad=0.05):
                        continue
                    p0 = (c[0] - u[0] * 0.075, c[1] - u[1] * 0.075)
                    p1 = (c[0] + u[0] * 0.075, c[1] + u[1] * 0.075)
                    # panel() faces right of p0 -> p1: flip so it faces the corridor (-nin)
                    if (p1[1] - p0[1]) * (-nin[0]) - (p1[0] - p0[0]) * (-nin[1]) < 0:
                        p0, p1 = p1, p0
                    R.panel(V, p0, p1, z + 1.4, z + 1.7, "int_ru_room_plaque", off=_face_off(F, c, (-nin[0], -nin[1])))
                    n_plq += 1
                    break
        # -- framed prints / bulletin boards every ~5 m on the room walls facing a corridor, clear of doors/corners
        for pa, pb in R.edges(oz.poly):
            L = math.dist(pa, pb)
            if L < 2.2:
                continue
            u = ((pb[0] - pa[0]) / L, (pb[1] - pa[1]) / L)
            nout = (u[1], -u[0])                       # CCW room: the corridor is on the right
            m = int((L - 1.6) / 5.0)
            for j in range(m + 1):
                s = L / 2 + (j - m / 2.0) * 5.0
                board = (k_art % 3 == 2)
                w = 1.2 if board else 0.75
                if s - w / 2 < 0.6 or s + w / 2 > L - 0.6:
                    continue
                c = (pa[0] + u[0] * s, pa[1] + u[1] * s)
                if any(f == F.id and bb_[0] <= c[0] <= bb_[2] and bb_[1] <= c[1] <= bb_[3] for f, bb_ in ART_SKIP):
                    continue
                ok = True
                for e in (-w / 2, 0.0, w / 2):
                    q = (pa[0] + u[0] * (s + e), pa[1] + u[1] * (s + e))
                    if _corridor_at(F, (q[0] + nout[0] * 0.6, q[1] + nout[1] * 0.6)) is None or \
                            F.zone_at((q[0] - nout[0] * 0.45, q[1] - nout[1] * 0.45)) is not oz:
                        ok = False
                        break
                if not ok or not _span_clear_of_doors(F, pa, u, s - w / 2, s + w / 2, pad=0.45):
                    continue
                p0 = (pa[0] + u[0] * (s - w / 2), pa[1] + u[1] * (s - w / 2))     # right of p0 -> p1 = nout
                p1 = (pa[0] + u[0] * (s + w / 2), pa[1] + u[1] * (s + w / 2))
                off_ = _face_off(F, c, nout)
                if board:
                    R.panel(V, p0, p1, z + 1.05, z + 1.95, "int_ru_bulletin", off=off_)
                else:
                    cell = k_art % 8
                    u0_ = (cell % 4) / 4.0
                    v0_ = 0.5 if cell < 4 else 0.0
                    R.panel(V, p0, p1, z + 1.3, z + 2.05, "int_ru_prints", off=off_, u0=u0_, u1=u0_ + 0.25, v0=v0_,
                            v1=v0_ + 0.5)
                k_art += 1
    return k_art, n_plq


def _bench(V, C, cx, cy, z, along_x=True, L=1.8, col=True):
    """A backless lobby bench: maple slat seat on two black steel frames (0.46 m), one low collision box."""
    hx, hy = (L / 2, 0.23) if along_x else (0.23, L / 2)
    V.box(cx - hx, cy - hy, z + 0.40, cx + hx, cy + hy, z + 0.46, "int_ru_maple_panel", faces="+x-x+y-y+z")
    for sg in (-1, 1):
        lx, ly = (cx + sg * (hx - 0.15), cy) if along_x else (cx, cy + sg * (hy - 0.15))
        bx, by = (0.03, hy - 0.03) if along_x else (hx - 0.03, 0.03)
        V.box(lx - bx, ly - by, z, lx + bx, ly + by, z + 0.40, "int_ru_black", faces="+x-x+y-y")
    if col:
        K.col_box(C, cx - hx, cy - hy, z, cx + hx, cy + hy, z + 0.46, K.COL_NOCAM)


def _planter(V, C, cx, cy, z, s=0.5, h=0.55):
    """A square charcoal planter with a leafy shrub (low collision: the planter only)."""
    V.box(cx - s, cy - s, z, cx + s, cy + s, z + h, "int_ru_wall_charcoal", faces="+x-x+y-y+z")
    V.box(cx - s * 0.8, cy - s * 0.8, z + h, cx + s * 0.8, cy + s * 0.8, z + h + 0.55, "leaves_oak2",
          faces="+x-x+y-y+z")
    V.box(cx - s * 0.5, cy - s * 0.5, z + h + 0.55, cx + s * 0.5, cy + s * 0.5, z + h + 0.95, "leaves_oak",
          faces="+x-x+y-y+z")
    K.col_box(C, cx - s, cy - s, z, cx + s, cy + s, z + h, K.COL_NOCAM)


def _lounge_group(RZ, V, C, fid, cx, cy, z, k, rot=0.0):
    """A navy lounge group on a rug (sofa, two club chairs, coffee table): one seat-height collision block."""
    rug = [(cx - 2.4, cy - 2.0), (cx + 2.4, cy - 2.0), (cx + 2.4, cy + 2.0), (cx - 2.4, cy + 2.0)]
    R.floor_poly(V, R.ccw(rug), z + 0.02, "int_ru_carpet_atrium", step=3.0)
    RZ.kit_add(R.sofa(2.0, "int_ru_fabric_navy"), fid, tag=f"pf_sofa_{k}", x=cx, y=cy - 1.35, z=z, facing=0.0)
    RZ.kit_add(R.coffee_table(1.1, 0.6, col=False), fid, tag=f"pf_table_{k}", x=cx, y=cy + 0.05, z=z, facing=90.0)
    for j, (dx, f) in enumerate(((-1.35, 90.0), (1.35, 270.0))):
        prop = R.lounge_chair("int_ru_fabric_plum" if j else "int_ru_fabric_navy", "int_ru_fabric_taupe", col=False)
        RZ.kit_add(prop, fid, tag=f"pf_chair_{k}_{j}", x=cx + dx, y=cy + 0.1, z=z, facing=f)
    K.col_box(C, cx - 1.8, cy - 1.4, z, cx + 1.8, cy + 0.55, z + 0.46, K.COL_NOCAM)


BOOKSTORE_DOOR = ((-443.2, -357.1), (-438.7, -357.2))      # the plan's 4.5 m link doors into the UF Bookstore


WAINSCOT_FLOORS = ("LL", "L2")
WAINSCOT_H = 0.94          # navy field; a 6 cm cherry rail cap on top (1.0 m, under the bulletin boards at 1.05)


def _built_wall_index(RZ):
    """fix round 5 (technical blocking 2): every BUILT vertical visual face so far (placed kit props), hashed on a
    1 m plan grid: (nx, ny, d, x0, x1, y0, y1, z0, z1). _corridor_wainscot measures the real wall face from it (the
    plan-wall estimate of _face_off left the band 0.04-0.43 u off some walls: angled runs, skirtings, other builds)."""
    H = {}
    for _t, _g, p in RZ.kit.items:
        for pl in p.visual.polys:
            pts = pl.pts
            if len(pts) < 3:
                continue
            nx = ny = nz = 0.0
            for i_ in range(len(pts)):
                a_, b_ = pts[i_], pts[(i_ + 1) % len(pts)]
                nx += (a_[1] - b_[1]) * (a_[2] + b_[2])
                ny += (a_[2] - b_[2]) * (a_[0] + b_[0])
                nz += (a_[0] - b_[0]) * (a_[1] + b_[1])
            L_ = math.sqrt(nx * nx + ny * ny + nz * nz)
            if L_ < 1e-6 or abs(nz) / L_ > 0.05:
                continue
            h_ = math.hypot(nx, ny)
            nx, ny = nx / h_, ny / h_
            xs, ys, zs = [q[0] for q in pts], [q[1] for q in pts], [q[2] for q in pts]
            e = (nx, ny, nx * pts[0][0] + ny * pts[0][1], min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))
            for i_ in range(int(math.floor(e[3])), int(math.floor(e[4])) + 1):
                for j_ in range(int(math.floor(e[5])), int(math.floor(e[6])) + 1):
                    H.setdefault((i_, j_), []).append(e)
    return H


def _built_face_t(H, q, nout, z0, z1, reach=0.4):
    """The largest offset t along nout (|t| <= reach) of a built face facing nout that covers q + t * nout over the
    height z0..z1 (None if there is none)."""
    best = None
    for e in H.get((int(math.floor(q[0])), int(math.floor(q[1]))), ()):
        nx, ny, d, x0, x1, y0, y1, ez0, ez1 = e
        dn = nx * nout[0] + ny * nout[1]
        if dn < 0.995 or ez1 < z0 + 0.01 or ez0 > z1 - 0.01:
            continue
        t_ = (d - nx * q[0] - ny * q[1]) / dn
        if abs(t_) > reach:
            continue
        px, py = q[0] + nout[0] * t_, q[1] + nout[1] * t_
        if x0 - 0.02 <= px <= x1 + 0.02 and y0 - 0.02 <= py <= y1 + 0.02:
            if best is None or t_ > best:
                best = t_
    return best


def _built_face_plane(HB, p0, p1, nout, z0, z1):
    """fix round 5: the plane (nx, ny, d) of the most proud built face facing nout that covers BOTH ends and the
    middle of p0 -> p1 (None if no single plane does)."""
    pick = None
    for q in (p0, ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2), p1):
        best = None
        for e in HB.get((int(math.floor(q[0])), int(math.floor(q[1]))), ()):
            nx, ny, d, x0, x1, y0, y1, ez0, ez1 = e
            dn = nx * nout[0] + ny * nout[1]
            if dn < 0.995 or ez1 < z0 + 0.01 or ez0 > z1 - 0.01:
                continue
            t_ = (d - nx * q[0] - ny * q[1]) / dn
            if abs(t_) > 0.4:
                continue
            px, py = q[0] + nout[0] * t_, q[1] + nout[1] * t_
            if x0 - 0.02 <= px <= x1 + 0.02 and y0 - 0.02 <= py <= y1 + 0.02 and (best is None or t_ > best[0]):
                best = (t_, (round(nx, 4), round(ny, 4), round(d, 3)))
        if best is None:
            return None
        if pick is None:
            pick = best[1]
        elif abs(best[1][0] - pick[0]) > 1e-3 or abs(best[1][1] - pick[1]) > 1e-3 or abs(best[1][2] - pick[2]) > 0.003:
            return None
    return pick


def _strip_shift(HB, a, b, z0, z1, gap=0.015, cap=0.08):
    """fix round 5 (technical blocking 2): how far (>= 0) a strip drawn at off=0 on the line a -> b (facing right)
    must move out to stand gap proud of every BUILT face behind it (faces up to cap off the line; a closer look than
    the plan-wall estimate, which left bands 0.1-0.4 u off the ballroom walls)."""
    L = math.dist(a, b)
    if L < 0.05:
        return 0.0
    dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    nrm = (dy, -dx)
    best = None
    n = max(2, int(L / 0.5) + 1)
    for k in range(n + 1):
        q = (a[0] + dx * L * k / n, a[1] + dy * L * k / n)
        t_ = _built_face_t(HB, q, nrm, z0, z1, reach=cap)
        if t_ is not None and (best is None or t_ > best):
            best = t_
    return 0.0 if best is None else max(0.0, best + gap)


def _corridor_wainscot(RZ, F, P):
    """fix round 4 (design pass, improvement 3; no photo of the LL corridor or the L2 pre-function hall, inferred, in
    the house palette): from 4-9 m behind Mario the 5.4 m white room blocks along the LL corridor and the L2
    pre-function hall read as blank slabs (int_ru_wall is near-flat). A navy wainscot to 0.94 m with a 6 cm cherry
    rail cap on the room walls that face a corridor gives scale and depth cues at the gameplay camera. Visual only,
    2.5 cm proud of the BUILT wall face (_face_off; the prints / boards / plaques sit at 4 cm and start at 1.05 m+),
    0.35 m clear of every plan door, only where a plan wall stands behind it (no band across an open zone edge)."""
    V = P.visual
    z = F.z
    n_runs, run_len = 0, 0.0
    step = 0.25
    HB = _built_wall_index(RZ)
    for oz in F.zones:
        if oz.type not in SOLID_TYPES or oz.cls not in ("S", "W"):
            continue
        for pa, pb in R.edges(oz.poly):
            L = math.dist(pa, pb)
            if L < 0.9:
                continue
            u = ((pb[0] - pa[0]) / L, (pb[1] - pa[1]) / L)
            nout = (u[1], -u[0])                       # CCW room: the corridor is on the right
            n = int((L - 0.3) / step)
            if n < 2:
                continue
            ss = [0.15 + (L - 0.3) * k / n for k in range(n + 1)]
            ok = []
            for sv in ss:
                q = (pa[0] + u[0] * sv, pa[1] + u[1] * sv)
                good = (_corridor_at(F, (q[0] + nout[0] * 0.6, q[1] + nout[1] * 0.6)) is not None and
                        F.zone_at((q[0] - nout[0] * 0.45, q[1] - nout[1] * 0.45)) is oz and
                        _span_clear_of_doors(F, pa, u, sv - 0.01, sv + 0.01, pad=0.35) and
                        _face_off(F, q, nout, gap=0.025, default=-99.0) != -99.0)
                ok.append(good)
            k = 0
            while k < len(ss):
                if not ok[k]:
                    k += 1
                    continue
                k0 = k
                while k + 1 < len(ss) and ok[k + 1]:
                    k += 1
                s0, s1 = ss[k0], ss[k]
                k += 1
                if s1 - s0 < 0.6:
                    continue
                c = (pa[0] + u[0] * (s0 + s1) / 2, pa[1] + u[1] * (s0 + s1) / 2)
                off_ = _face_off(F, c, nout, gap=0.025)
                # fix round 5 (technical blocking 2): measured on the BUILT faces at every sample of the run (not
                # only the plan-wall estimate at its centre): 2 cm proud of the most proud face anywhere along it
                tb = [_built_face_t(HB, (pa[0] + u[0] * sv, pa[1] + u[1] * sv), nout, z + 0.02, z + 1.0)
                      for sv in ss[k0:k] + [s1]]
                tb = [t_ for t_ in tb if t_ is not None]
                if tb:
                    off_ = max(off_, max(tb) + 0.02)
                p0 = (pa[0] + u[0] * s0, pa[1] + u[1] * s0)      # right of p0 -> p1 = nout (the corridor)
                p1 = (pa[0] + u[0] * s1, pa[1] + u[1] * s1)
                # ... and PARALLEL to that face (the room edge can be ~1-2 degrees off the built wall): the band's ends
                # are put 2 cm off the face plane itself when one face covers the whole run
                fe = _built_face_plane(HB, p0, p1, nout, z + 0.02, z + 1.0)
                if fe is not None:
                    for sv in ss[k0:k]:
                        q_ = (pa[0] + u[0] * sv, pa[1] + u[1] * sv)
                        tq = _built_face_t(HB, q_, nout, z + 0.02, z + 1.0)
                        dn_ = fe[0] * nout[0] + fe[1] * nout[1]
                        if tq is not None and (fe[2] - fe[0] * q_[0] - fe[1] * q_[1]) / dn_ < tq - 0.003:
                            fe = None           # a more proud face somewhere along the run: keep the max offset
                            break
                if fe is not None:
                    fnx, fny, fd = fe
                    p0 = (p0[0] + fnx * (fd + 0.02 - fnx * p0[0] - fny * p0[1]), p0[1] + fny * (fd + 0.02 - fnx * p0[0] - fny * p0[1]))
                    p1 = (p1[0] + fnx * (fd + 0.02 - fnx * p1[0] - fny * p1[1]), p1[1] + fny * (fd + 0.02 - fnx * p1[0] - fny * p1[1]))
                    off_ = 0.0
                R.panel(V, p0, p1, z + 0.02, z + WAINSCOT_H, "int_ru_wall_navy", off=off_, u1=round((s1 - s0) / 2.0, 3),
                        v1=0.46)       # texel density as the 2 m tile
                R.panel(V, p0, p1, z + WAINSCOT_H, z + 1.0, "int_ru_cherry", off=off_, u1=round((s1 - s0) / 1.2, 3),
                        v1=0.05)       # 6 cm of the 1.2 m tile (no squeezed grain)
                n_runs += 1
                run_len += s1 - s0
    return n_runs, round(run_len, 1)


def circulation_dress(RZ):
    stats = {}
    for fid in DRESS_FLOORS:
        F = RZ.floors[fid]
        P = R._p(f"circulation_{fid}")
        stats[fid] = _corridor_art(RZ, F, P)
        if fid in WAINSCOT_FLOORS:
            stats[fid + "_wainscot"] = _corridor_wainscot(RZ, F, P)
        V, C, z = P.visual, P.collision, F.z
        if fid == "L2":
            # the pre-function hall west of the atrium: a lounge group west of the blue elevators and one by the
            # atrium's west balcony; benches against the core block
            _lounge_group(RZ, V, C, fid, -458.6, -270.6, z, 0)
            _lounge_group(RZ, V, C, fid, -421.6, -281.2, z, 1)
            for bx in (-431.0, -425.0):
                _bench(V, C, bx, -266.05, z)
        elif fid == "L3":
            for bx in (-431.0, -426.0):
                _bench(V, C, bx, -266.05, z)
        elif fid == "LL":
            for bx in (-438.5, -432.5):
                _bench(V, C, bx, -266.05, z)
        RZ.kit_add(P, fid, tag=f"circulation_{fid}")
    RZ.stats["circulation_art"] = {f: {"art": a, "plaques": p} for f, (a, p) in stats.items()}
    # ---- L1 south hall (the Bookstore link; l1_corridor_08 south of y -338)
    F = RZ.floors["L1"]
    P = R._p("south_hall")
    V, C, z = P.visual, P.collision, F.z
    for (bx, by) in ((-434.5, -346.0), (-434.5, -346.7), (-423.5, -346.0), (-423.5, -346.7)):
        _bench(V, C, bx, by, z, col=False)
    for bx in (-434.5, -423.5):
        K.col_box(C, bx - 0.9, -346.93, z, bx + 0.9, -345.77, z + 0.46, K.COL_NOCAM)
    for (px, py) in ((-437.6, -342.0), (-420.4, -342.0), (-437.6, -351.2), (-420.4, -351.2), (-429.0, -351.2)):
        _planter(V, C, px, py, z)
    # the University of Florida Bookstore sign over the link doors, on a 0.6 m deep white sign ledge (collision top + underside: a
    # double jump, or a jump and a ledge grab, reaches the coins on it)
    (ax, ay), (bx_, by_) = BOOKSTORE_DOOR
    mx = (ax + bx_) / 2
    yw = -357.0                                 # the hall face of the south wall at the doors (EXT_T / 2 north)
    x0, x1 = ax - 0.5, bx_ + 0.5
    V.box(x0, yw, z + 2.95, x1, yw + 0.6, z + 3.1, "int_ru_white", faces="+x-x+y+z-z")
    K.col_box(C, x0, yw, z + 2.95, x1, yw + 0.6, z + 3.1, K.COL, bottom=True)
    # ru_bookstore_entrance: glowing white letters on a dark fascia band across the whole storefront
    # fix round 4 (technical blocking): 1.8 cm / 4 cm proud (0.6 / 1.2 cm rounded to the same game unit: z-fight)
    R.panel(V, (x1, yw), (x0, yw), z + 3.1, z + 5.0, "int_ru_black", off=0.018)
    R.panel(V, (mx + 1.8, yw), (mx - 1.8, yw), z + 3.15, z + 4.95, "int_ru_sign_bookstore", off=0.04, glow=True)
    for dx in (-1.6, 0.0, 1.6):
        EXTRA_PICKUPS.append({"kind": "coin", "name": f"bookstore ledge coin {dx:+.1f}", "pos": (mx + dx, yw + 0.3, z + 3.1)})
    RZ.kit_add(P, "L1", tag="south_hall")
    # a second jump reward on the Ground: coins on top of three of the arcade cabinets by the Esports storefront
    # (game_room: tops at 1.85 m, x -458.8; double-jump, or hop from the 1.55 m kiosk at y -292.5)
    for i in (0, 3, 6):
        EXTRA_PICKUPS.append({"kind": "coin", "name": f"arcade top coin {i}", "pos": (-458.8, -283.6 - i * 0.95, 1.85)})


DRESSERS.extend([circulation_dress])


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
        # matched to the photos (fidelity review r1): the lounge from its west end, the vault from under the L1
        # balcony's south edge, the vertical view from the L3 west-end balcony
        ("reitz_atrium_lounge", (-413.2, -271.0, 1.5), (-392.0, -271.3, 7.0), None, 62.0, "ru_atrium_enr_lounge.webp"),
        ("reitz_atrium_stairs", (-413.6, -271.0, 20.2), (-400.0, -271.2, 15.2), None, 95.0, "ru_atrium_enr_vertical.webp"),
        ("reitz_atrium_up", (-406.0, -274.5, 1.6), (-399.0, -268.5, 18.0), None, 76.0, "ru_atrium_hdr_flickr.jpg"),
        ("reitz_uf_letters", (-409.0, -272.5, 1.6), (-409.4, -264.5, 2.5), None, 58.0, "ru_atrium_uf_letters_flickr.jpg"),
        ("reitz_game_room_lanes", (-458.2, -301.2, 1.7), (-441.0, -306.4, 1.6), None, 60.0, "ru_gr_lanes_overview_2.jpg"),
        # fidelity-3 (round 2): behind and between the two white columns (y -305.0..-304.4, x -446.2 / -442.7) that
        # frame ru_gr_lane_screens
        ("reitz_bowling_lane", (-444.46, -301.9, 1.6), (-444.46, -327.0, 1.9), None, 58.0, "ru_gr_lane_screens.jpg"),
        ("reitz_billiards", (-458.6, -289.6, 1.6), (-440.0, -285.4, 1.5), None, 62.0, "ru_gr_billiards_room.jpg"),
        ("reitz_esports", (-461.2, -294.5, 1.7), (-463.0, -309.0, 3.0), None, 66.0, "ru_es_overview.jpg"),
        ("reitz_food_court", (-457.2, -314.2, 7.55), (-433.0, -310.5, 7.2), None, 54.0, "ru_food_court_counter_2023.jpeg"),
        ("reitz_food_court_burgers", (-426.4, -306.2, 7.6), (-429.4, -297.2, 8.3), None, 58.0, "ru_food_court_sonic_2025.jpg"),
        ("reitz_food_court_coffee", (-428.6, -305.2, 7.55), (-433.2, -305.2, 7.4), None, 55.0, "ru_starbucks_2017.jpg"),
        ("reitz_grand_ballroom", (-488.5, -250.6, 14.8), (-488.5, -275.0, 14.4), None, 62.0, "ru_os_grand_ballroom_1.jpg"),
        # fidelity-4 r2: from the north-west, behind the rows, looking at the stage + black drape on the far (south)
        # wall, the N-S beams converging to the right (ru_os_rion_ballroom); the old camera stood beside the stage
        ("reitz_rion_ballroom", (-451.6, -301.6, 20.4), (-437.5, -322.5, 19.0), None, 62.0, "ru_os_rion_ballroom.jpg"),
        ("reitz_auditorium", (-433.4, -251.5, 15.6), (-454.0, -251.5, 13.7), None, 58.0, "ru_os_auditorium_3.jpg"),
        ("reitz_senate_chamber", (-416.0, -259.4, 2.6), (-405.0, -246.0, 1.4), None, 66.0, "ru_os_chamber.jpg"),
        ("reitz_meeting_g330", (-361.4, -283.4, 1.7), (-373.8, -275.0, 1.3), None, 66.0, "ru_os_g330.jpg"),
        ("reitz_hotel_reception", (-450.7, -273.9, 1.7), (-456.4, -270.3, 1.7), None, 70.0, None),
        ("reitz_gallery", (-421.5, -259.8, 13.6), (-430.0, -250.0, 13.4), None, 62.0, "ru_the_gallery.jpg"),
        ("reitz_arredondo", (-453.0, -263.5, 25.6), (-424.0, -261.6, 25.4), None, 62.0, "ru_os_arredondo_cafe.jpg"),
        # fidelity-4 r2: from the south-east corner looking north-north-west: the royal-blue wall with the dresser + TV
        # on the left, the cherry headboard + nightstands + lamps ahead, the balcony glass on the right
        # (ru_hotel_room; _hotel_516). The old view had the blue wall head-on and the bed's bare foot.
        ("reitz_hotel_room", (-425.3, -273.45, 30.65), (-428.5, -268.8, 30.05), None, 72.0, "ru_hotel_room.jpg"),
        ("reitz_hotel_suite", (-445.25, -287.1, 30.6), (-440.0, -286.9, 30.2), None, 64.0, "ru_hotel_suite.jpg"),
        ("reitz_dance_studio", (-402.4, -279.0, -4.4), (-389.5, -270.0, -4.8), None, 62.0, "ru_os_dance_1.jpg"),
        ("reitz_acc_mural", (-452.5, -259.9, -4.4), (-445.7, -259.9, -3.8), None, 62.0, "ru_acc_entrance_mural.jpg"),
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
