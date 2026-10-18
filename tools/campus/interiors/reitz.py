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
# iteration 7 (technical blocking): coopdx v1.5.1 with gLevelValues.fixCollisionBugs = 1 (levels.lua) pushes Mario
# off a wall's CLOSEST POINT on the ground (rounded corners), so a doorway narrower than his 100 u body is a wall:
# 0.8 / 0.9 m plan doors blocked (doorpass.py under lib_dx: 81 doors vanilla-only). Every open / entrance doorway
# keeps its rendered frame at plan width but its COLLISION opening is at least DOOR_COL_MIN (the jamb collision is
# cut back behind the rendered frame, symmetrically, clamped to the wall run).
DOOR_COL_MIN = 1.12
# iteration 7 (fidelity-1 improvement 4): collinear plan-wall joints whose two runs must not overlap (floor, point)
SEAM_JOINTS = [("G", (-416.8, -261.3))]          # the Senate Chamber vestibule: int_ru_wall | int_ru_wall_cream
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
# user-photo pass (B05, B06: the L1 north lobby at the stair head; user_05: the L3 north corridor beside the
# Gators tower): extra convex cedar slat ceiling bands, joined to the void bands in build_floor (downlights kept)
CEDAR_EXTRA = {"L1": [[(-396.0, -267.9), (-368.5, -267.9), (-368.5, -259.5), (-396.0, -259.5)],
                      # user-photo pass (user_06, user_07, user_08, user_09): the cedar soffit band along the core side
                      # of the L1 north corridor and the whole Orange-elevator passage ceiling
                      [(-459.0, -267.3), (-414.0, -267.3), (-414.0, -264.9), (-459.0, -264.9)],
                      [(-420.2, -277.5), (-417.8, -277.5), (-417.8, -266.5), (-420.2, -266.5)]],
               "L3": [[(-425.0, -266.7), (-392.0, -266.7), (-392.0, -262.4), (-425.0, -262.4)]]}
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
    "brands": "Food court storefronts: the vendors' plain names in the colours of the user's photos "
              "(STARBUCKS, PANDA, BABA'S PIZZA, HALAL SHACK, HOME OF THE GATORS / BOOKSTORE) with simple generic round "
              "badges; no reproduced logo artwork (no siren, swoosh or panda mark). Older slots keep generic signs.",
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
        if zid == "meeting_3310":
            # iteration 9 (fidelity-4 improvement 8; ru_os_3310): warm cream walls (photo ~174, 159, 139; the white
            # int_ru_wall baked a cool grey). Not 3305: its south wall's run end overlaps the l3_corridor_08 wall
            # face by 0.2 m in one plane at the T with its east wall, which only stays invisible while both are white
            s["wall"] = "int_ru_wall_warm"
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
            # user-photo pass (C14-C16): light maple strip floor (int_ru_maple baked a medium honey-orange)
            s.update(floor="int_ru_maple_pale", wall="int_ru_wall", clear=CLEAR["L3"] + 0.6, light="linear", spacing=3.6)
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
        # user-photo pass (user_04, user_01): a dark slate lay-in ceiling (the white one swallowed the LED rings)
        # photo pass round 2 (fidelity-ground 1; user_04, B15, B20): the slate tile baked near-black in every view;
        # the photos show a mid blue-grey to light grey 2 x 2 lay-in (the Esports Center keeps its black ceiling)
        s.update(floor="int_ru_plank", wall="int_ru_wall_navy", light="troffer", spacing=3.6, base="int_ru_black",
                 ceil="int_ru_tile_ceiling_mid")
    elif t == "esports":
        # ru_es_oelrich_9352: wood-look plank floor; near-black hex walls (ru_es_overview). User-photo pass (user_01,
        # B18): the floor is grey plank vinyl
        s.update(floor="int_ru_plank", wall="int_ru_hex", ceil="int_ru_black", light="esports", spacing=3.0)
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
        # iteration 9 (fidelity-4 improvement 5; ru_hotel_room, ru_hotel_suite): the guest rooms' own warm taupe
        # carpet (the navy diamond int_ru_carpet_hotel stays on the corridors)
        s.update(floor="int_ru_carpet_hotelroom", wall="int_ru_wall", accent="int_ru_wall_royal", light="lamp",
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
    if zid == RION_GALLERY:
        s.update(floor="int_ru_carpet_prefn", light="down", spacing=3.4)   # photo pass round 3 (C03, C12, C13)
    return s


# photo pass round 3 (C03, C12, C13, the fidelity-upper blocker): the Rion pre-function is ONE long
# carpeted gallery along the ballroom's north wall, entered at its east end through the ~2 m RION BALLROOM EAST
# double door (C03) and closed at its west end by a wall with the Bill Rion memorial case beside a door (C13). The
# plan splits it into the west patch and east bulge of l3_corridor_11 with the solid l3_room_10 strip (and the south
# strip of l3_room_107) between them. Here l3_room_10 becomes the whole gallery (one walkable zone, x -456.9..-425.0,
# y -297.1..-289.7), l3_room_107 loses its south strip, the partitions inside the gallery go, and three plan walls
# are added: its north wall between the two old patches, the east wall with the 2 m door, the west end wall with
# a 2 m door to the west corridor. The Rion's five narrow north doors in between stay closed (_closed_look).
RION_GALLERY = "l3_room_10"
RION_GALLERY_POLY = [(-456.9, -296.8), (-447.5, -296.9), (-432.7, -297.1), (-427.9, -297.2), (-425.0, -297.2),
                     (-425.1, -290.2), (-432.6, -290.1), (-448.5, -289.7), (-456.9, -289.6)]
RION_GALLERY_DROP = [(-432.7, -297.1, -432.7, -294.4), (-432.7, -294.4, -432.6, -290.1),
                     (-432.7, -294.4, -435.5, -294.4), (-435.5, -294.4, -435.4, -293.5),
                     (-435.4, -293.5, -437.2, -293.4), (-437.2, -293.4, -437.2, -294.3),
                     (-437.2, -294.3, -444.9, -294.2), (-444.9, -294.2, -444.9, -293.3),
                     (-444.9, -293.3, -446.6, -293.3), (-446.6, -293.3, -446.6, -294.2),
                     (-446.6, -294.2, -447.4, -294.2), (-448.6, -294.2, -448.5, -289.7),
                     (-447.4, -294.2, -448.6, -294.2), (-447.4, -294.2, -447.5, -296.9)]
RION_GALLERY_WALLS = [(-448.5, -289.7, -432.6, -290.1),          # north wall between the old patches
                      (-425.0, -297.2, -425.1, -290.2),          # east wall (RION BALLROOM EAST)
                      (-456.9, -289.6, -456.9, -296.8)]          # west end wall (memorial case + door)
RION_GALLERY_DOORS = [(-425.036, -294.7, -425.064, -292.7, 0),   # RION BALLROOM EAST: 2.0 m, centred on the beam
                      (-456.9, -296.45, -456.9, -294.45, 0)]     # west end: 2.0 m to the west corridor
RION_GALLERY_STRIP = [(-426.6, -282.8), (-424.9, -282.8), (-424.9, -281.8), (-432.5, -281.7), (-432.5, -277.4),
                      (-441.0, -277.4), (-441.1, -281.3), (-443.9, -281.2), (-443.9, -277.3), (-448.5, -277.3),
                      (-448.6, -285.6), (-456.8, -285.5), (-456.9, -289.6), (-448.5, -289.7), (-432.6, -290.1),
                      (-432.5, -282.7)]
SEAM_JOINTS += [("L3", (-448.5, -289.7)), ("L3", (-432.6, -290.1)), ("L3", (-425.1, -290.2)),
                ("L3", (-456.9, -289.6)), ("L3", (-456.9, -296.8))]


def _rion_gallery_plan(F):
    """Photo pass round 3: turn the L3 Rion pre-function into one gallery zone (see RION_GALLERY_POLY)."""
    gz, rz = F.zone(RION_GALLERY), F.zone("l3_room_107")
    if gz is None or rz is None:
        return
    gz.type, gz.name, gz.cls = "corridor", "Rion Ballroom pre-function", "W"
    for zn, poly in ((gz, RION_GALLERY_POLY), (rz, RION_GALLERY_STRIP)):
        zn.poly = R.ccw(list(poly))
        zn.bb = R.bbox(zn.poly)
        zn.area = abs(R.signed_area(zn.poly))

    def same(w, d):
        return (math.dist(w[:2], d[:2]) < 0.02 and math.dist(w[2:4], d[2:4]) < 0.02) or \
            (math.dist(w[:2], d[2:4]) < 0.02 and math.dist(w[2:4], d[:2]) < 0.02)
    F.walls = [w for w in F.walls if not any(same(w, d) for d in RION_GALLERY_DROP)] + list(RION_GALLERY_WALLS)
    F.doors = list(F.doors) + list(RION_GALLERY_DOORS)


# ================================================================== the build
class Reitz:
    def __init__(self, layout):
        self.layout = layout
        self.footprint = R.ccw([tuple(p) for p in layout["footprint"]["poly_m"]])
        self.floors = {f["id"]: Floor(f, self.footprint) for f in layout["floors"]}
        if "L3" in self.floors:
            _rion_gallery_plan(self.floors["L3"])       # photo pass round 3 (C03, C12, C13)
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
    if fid == "L1" and zid == "l1_corridor_08" and my < -337.5 and \
            ((abs(my + 357.2) < 0.6 and mx > -446.0) or abs(mx + 418.2) < 0.6):
        # user-photo pass (user_20): the south hall's south wall (the Bookstore front) and east wall are solid
        return None
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


def _entrance_door_pair(V, a, b, z0, leaf_h=2.45, top=GLASS_DOOR_H, glass="int_ru_glass_door"):
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
    # iteration 7 (fidelity-1 improvement 3): the OUTER bank (this call) takes the tinted int_ru_glass_door
    R.panel(V, a, b, z0, z0 + top, glass)
    R.panel(V, b, a, z0, z0 + top, glass)
    # iteration 7 (design improvement 5, a_north_arrive): the arrival camera looks through this bank and the
    # vestibule's inner bank for the first ~10 m and the two rows of 11 cm white stiles + standing pull bars read as
    # a fence. ru_ribbon_cutting_doors shows slim light-metal stiles: 11 -> 6 cm here (the inner bank keeps its own
    # leaves), and the pulls below lose their off-face standoffs (a slim bar 2.5 cm proud of the stile face instead)
    st, hl = 0.06, 0.035                    # stile width, half depth
    for k in range(n):
        s0, s1 = w * k / n, w * (k + 1) / n
        # the two end stiles start 4.5 cm in from the bay ends: the vestibule's steel frame members (+-4 cm round
        # the bay ends) have faces in the plane of the stile faces (a coplanar white / steel pair at the overlap)
        if k == 0:
            s0 += 0.045
        if k == n - 1:
            s1 -= 0.045
        for (u0, u1) in ((s0, s0 + st), (s1 - st, s1)):
            R.seg_box(V, at(u0), at(u1), hl, z0, z0 + leaf_h, "int_ru_white", faces="sideends", ao=0.95)
        R.seg_box(V, at(s0 + st), at(s1 - st), hl, z0, z0 + 0.26, "int_ru_white", faces="sidetop", ao=0.95)
        # fix iteration 6 (design improvement 6): the leaf head rail and the transom bar are the horizontal bars that
        # crossed Mario's torso in the arrival view: thinned 12 + 14 cm -> 5 + 6 cm (the wide stiles and the deep
        # bottom rail of ru_ribbon_cutting_doors stay)
        R.seg_box(V, at(s0 + st), at(s1 - st), hl, z0 + leaf_h - 0.05, z0 + leaf_h, "int_ru_white", faces="sidebot",
                  ao=0.95)
        # pull: a slim steel bar on both faces of the meeting stile (or the latch side), 4.5-6.5 cm off the glass
        # plane, i.e. 1 cm clear of the stile's 3.5 cm face (no coplanar or touching faces)
        sp = s1 - st * 0.5 if (k == 0 and n == 2) else s0 + st * 0.5
        px, py = at(sp)
        for sg in (-1, 1):
            q0 = (px + nx * sg * 0.055 - dx * 0.01, py + ny * sg * 0.055 - dy * 0.01)
            q1 = (px + nx * sg * 0.055 + dx * 0.01, py + ny * sg * 0.055 + dy * 0.01)
            R.seg_box(V, q0, q1, 0.01, z0 + 0.95, z0 + 1.85, "int_ru_steel", faces="sideendstopbot")
    # transom bar over the leaves, transom glass above (to the opening head)
    R.seg_box(V, at(0.0), at(w), 0.06, z0 + leaf_h, z0 + leaf_h + 0.06, "int_ru_white", faces="sidebot", ao=0.95)
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


# user-photo pass (Ground; B13, B17, user_03): floor inlays, each drawn in its own material at the floor's height
# and cut out of its zone's floor (no overlay, no z-fight): (zone id, (x0, y0, x1, y1), material, uv mode)
FLOOR_INLAYS = {"G": [
    # J. WAYNE REITZ UNION lettering just inside the hotel doors (B17), reading walking in eastward
    ("g_corridor_02", (-460.75, -272.2, -460.05, -267.3), "int_ru_inlay_reitz", "reitz"),
    # grey terrazzo runner rectangles down the Subway corridor (user_03)
    *[("g_corridor_02", (-445.6, yc_ - 1.2, -444.4, yc_ + 1.2), "int_ru_terrazzo_grey", "tile")
      for yc_ in (-262.3, -258.7, -255.1, -251.5, -247.9)],
    # the orange-elevator corridor's orange terrazzo runner with a grey side band (B13); photo pass round 2
    # (fidelity-ground 2a): the band is on the EAST side beside the elevators (as on L1), the orange field ~2/3 wide
    ("g_corridor_02", (-420.95, -276.0, -419.25, -245.4), "int_ru_terrazzo_orange", "tile"),
    ("g_corridor_02", (-419.25, -276.0, -418.85, -245.4), "int_ru_terrazzo_grey", "tile"),
], "L1": [
    # user-photo pass (user_07): the Orange-elevator passage's orange terrazzo runner, a grey band on the elevator side
    ("l1_corridor_08", (-419.95, -277.2, -418.35, -266.8), "int_ru_terrazzo_orange", "tile"),
    ("l1_corridor_08", (-418.35, -277.2, -418.05, -266.8), "int_ru_terrazzo_grey", "tile"),
    # user-photo pass (user_14-16): the CCC's stepped slate floor and the slate band along the CCC front
    ("l1_corridor_08", (-465.1, -268.6, -461.8, -258.4), "int_ru_slate_floor", "tile"),
    ("l1_corridor_08", (-461.8, -266.8, -460.6, -260.1), "int_ru_slate_floor", "tile"),
    ("l1_corridor_08", (-460.6, -265.0, -459.4, -261.9), "int_ru_slate_floor", "tile"),
    ("l1_corridor_08", (-463.2, -279.0, -460.6, -268.6), "int_ru_slate_floor", "tile"),
    # design + leftovers pass (user_06, C04, B05): the dark grey terrazzo inlay band down the north
    # corridor, 0.3 m wide, ~0.9 m in from the balcony line (west of the tower: the rail curves north east of it)
    ("l1_corridor_08", (-458.4, -265.62, -412.3, -265.32), "int_ru_terrazzo_dark", "tile"),
    # photo pass round 2 (user_12, user_13, user_17): the L1 west lounge's blue triangle-geometric carpet
    ("l1_corridor_08", (-457.2, -277.3, -450.6, -268.3), "int_ru_carpet_lounge", "tile"),   # round 3: muted navy/slate
], "L2": [
    # design + leftovers pass (user_06, C04, B05): the dark grey terrazzo inlay band down the north
    # corridor, 0.3 m wide, ~0.9 m in from the balcony line (west of the tower: the rail curves north east of it)
    ("l2_corridor_08", (-458.4, -265.62, -412.3, -265.32), "int_ru_terrazzo_dark", "tile"),
], "L3": [
    # user-photo pass (C12, C13): blue geometric carpet over the Rion pre-function bulge (terrazzo outside)
    # photo pass round 2: the medium-blue geometric carpet (the navy wavy int_ru_carpet_atrium read as water), and
    # carried over the west pre-function by the Rion's west doors
    # photo pass round 3: both patches are now the one l3_room_10 gallery zone, carpeted by its style
    # (int_ru_carpet_prefn), so their inlays went
    # design + leftovers pass (user_06, C04, B05): the dark grey terrazzo inlay band down the north
    # corridor, 0.3 m wide, ~0.9 m in from the balcony line (west of the tower: the rail curves north east of it)
    ("l3_corridor_11", (-453.0, -265.62, -412.3, -265.32), "int_ru_terrazzo_dark", "tile"),
]}


def _floor_inlays(F, zn):
    out = []
    for zid, (x0, y0, x1, y1), mat, mode in FLOOR_INLAYS.get(F.id, ()):
        if zid != zn.id:
            continue
        probe = [(x0 + 0.01, y0 + 0.01), (x1 - 0.01, y0 + 0.01), (x1 - 0.01, y1 - 0.01), (x0 + 0.01, y1 - 0.01),
                 ((x0 + x1) / 2, (y0 + y1) / 2)]
        if all(getattr(F.cls_at(p_)[1], "id", None) == zid for p_ in probe):
            out.append(((x0, y0, x1, y1), mat, mode))
    return out


def _draw_inlay(V, z, rect, mat, mode):
    x0, y0, x1, y1 = rect
    if mode == "reitz":
        # the 128 px line in two 64 px strips (rows 0-15 = v 0.5-1: the left half) laid along -y, letter tops to +x
        ym = (y0 + y1) / 2
        for ya, yb, v0, v1 in ((y1, ym, 0.5, 1.0), (ym, y0, 0.0, 0.5)):
            V.poly([(x0, ya, z), (x0, yb, z), (x1, yb, z), (x1, ya, z)], mat,
                   uvs=[(0.0, v0), (1.0, v0), (1.0, v1), (0.0, v1)], normal_hint=(0, 0, 1))
    else:
        R.floor_poly(V, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z, mat, step=FLOOR_STEP)


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
        inl_ = _floor_inlays(F, zn)
        R.floor_poly(V, zn.poly, z - 0.02, st["floor"], step=FLOOR_STEP,
                     cut=list(F.voids) + inner[zn.id] + [[(r_[0], r_[1]), (r_[2], r_[1]), (r_[2], r_[3]), (r_[0], r_[3])]
                                                         for r_, _m, _k in inl_])
        for r_, m_, k_ in inl_:
            _draw_inlay(V, z - 0.02, r_, m_, k_)
        floor_polys.append(R.offset_poly(R.clean(zn.poly, 0.12, 0.03), 0.06))
        zc = z + st["clear"]
        top_voids = voids_above if st["clear"] <= CLEAR[fid] + 0.01 else []
        if zn.type == "atrium_floor":
            continue
        tris = R.triangulate(zn.poly)
        cut = list(top_voids) + list(F.voids) + inner_ceil[zn.id]
        # fix iteration 6 (design improvement 7, collision budget): a room with a dropped lay-in ceiling has its
        # collision ceiling at ceil_h (below); the plain ceiling's collision cover at the clear height above it can
        # never be reached (Mario or the camera meet the dropped one first), so such a zone joins no ceiling group
        if not (CEIL_GROUP_SKIP_DROPPED and st.get("ceil_h")):
            zone_zc.append((zn, round(zc, 3)))
        # fix round 2 (blocking): the cedar soffit band under each balcony is ONE polygon (the void above offset by
        # 3.2 m, clipped to the zone), cut out of the tile ceiling: no per-piece material (sawtooth cedar slivers)
        cedar_ok = zn.type in ("corridor", "atrium_floor", "vestibule") and fid in ("G", "L1", "L2", "L3")
        bands = [R.ccw(R.convex_hull(R.offset_poly(v, 3.2))) for v in top_voids] if cedar_ok else []
        if cedar_ok:
            bands += [R.ccw(list(r_)) for r_ in CEDAR_EXTRA.get(fid, ())]
        for pc, mat in _band_pieces(R.subtract(R.grid_pieces(tris, CEIL_STEP), cut), bands, st["ceil"],
                                    WHITE_SOFFITS.get(fid, ())):
            V.poly([(x, y, zc) for x, y in reversed(R.ccw(pc))], mat, ao=0.95)
            if st.get("ceil_h"):
                V.poly([(x, y, z + st["ceil_h"]) for x, y in reversed(R.ccw(pc))], st["ceil"], ao=0.95)
        if st.get("ceil_h"):
            for t_ in R.triangulate(R.clean(zn.poly, 0.12, 0.03)):
                C.poly([(x, y, z + st["ceil_h"]) for x, y in reversed(R.ccw(t_))], K.COL)
        if not (CEIL_GROUP_SKIP_DROPPED and st.get("ceil_h")):
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
        # iteration 7 (fidelity-1 improvement 4): at a SEAM_JOINTS point two collinear plan walls meet end to end;
        # both used to run WALL_T / 2 past it, so their faces overlapped in a 0.2 m coplanar strip (two materials:
        # z-fight). There each ends exactly at the joint (faces abut, no overlap)
        ea = 0.0 if any(fs == F.id and math.dist(a, pj) < 0.02 for fs, pj in SEAM_JOINTS) else ext
        eb = 0.0 if any(fs == F.id and math.dist(b, pj) < 0.02 for fs, pj in SEAM_JOINTS) else ext
        a2 = (a[0] - dx * ea, a[1] - dy * ea)
        b2 = (b[0] + dx * eb, b[1] + dy * eb)
        runs = _side_samples(F, a, b, 0.35)
        doors = _door_cuts(F, a, b)
        L = math.dist(a2, b2)
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        if any(R.pip(mid, nw) for nw in F.no_walls):
            continue
        open_ww = any(R.pip(mid, ow) for ow in F.open_ww)
        n_before = len(runs_all)
        for s0, s1, (cl, zl), (cr, zr) in runs:
            if open_ww and cl == "W" and cr == "W":
                continue
            if cl == "W" and cr == "W" and zl is not None and zr is not None and frozenset((zl.id, zr.id)) in OPEN_PAIRS:
                continue
            if "W" not in (cl, cr) and "V" not in (cl, cr) and "O" not in (cl, cr):
                continue
            if "W" not in (cl, cr) and "V" not in (cl, cr) and cl == cr:
                continue
            r0 = 0.0 if s0 < 1e-6 else s0 + ea
            r1 = L if s1 > L0 - 1e-6 else s1 + ea
            pa = (a2[0] + dx * r0, a2[1] + dy * r0)
            pb = (a2[0] + dx * r1, a2[1] + dy * r1)
            RL = math.dist(pa, pb)
            dl = []
            for d0, d1, di, dext in doors:
                q0, q1 = d0 + ea - r0, d1 + ea - r0
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
            runs_all.append({"pa": pa, "pb": pb, "L": (cl, zl), "R": (cr, zr), "doors": dl, "accent": set(),
                             "r0": r0, "RL": RL, "col_spans": {}, "col_cuts": []})

    _door_col_plan(F, runs_all)
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
        _wall_run(RZ, F, V, C, CW, r["pa"], r["pb"], r["L"], r["R"], r["doors"], stats, r["accent"],
                  col_spans=r["col_spans"], col_cuts=r["col_cuts"])
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
    if F.id == "L3":
        # photo pass round 3 (C12): the Rion's five narrow north doors between the gallery's old patches are closed
        # honey leaves under the RION BALLROOM letters (they were walled by the solid l3_room_10 strip); the four
        # double doors at the gallery's ends stay open
        for i, d in enumerate(F.doors):
            m = ((d[0] + d[2]) / 2, (d[1] + d[3]) / 2)
            if -447.2 < m[0] < -432.9 and -297.4 < m[1] < -296.6:
                out.add(i)
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


def _in_entrance(ent, pa, pb, RL, d0, d1, min_w=0.9):
    """True when at least min_w of door interval d0..d1 on run pa -> pb lies within the entrance's a .. b span."""
    ux, uy = (pb[0] - pa[0]) / RL, (pb[1] - pa[1]) / RL
    sa = (ent["a"][0] - pa[0]) * ux + (ent["a"][1] - pa[1]) * uy
    sb = (ent["b"][0] - pa[0]) * ux + (ent["b"][1] - pa[1]) * uy
    lo, hi = max(d0, min(sa, sb)), min(d1, max(sa, sb))
    return hi - lo >= min(min_w, d1 - d0 - 1e-6)


def _door_col_span(d0, d1, lo, hi):
    """A doorway's collision interval: at least DOOR_COL_MIN wide, centred, shifted to stay within lo .. hi."""
    if d1 - d0 >= DOOR_COL_MIN:
        return d0, d1
    m = (d0 + d1) / 2
    c0, c1 = m - DOOR_COL_MIN / 2, m + DOOR_COL_MIN / 2
    if c0 < lo:
        c0, c1 = lo, lo + DOOR_COL_MIN
    if c1 > hi:
        c0, c1 = max(lo, hi - DOOR_COL_MIN), hi
    return min(c0, d0), max(c1, d1)


def _door_col_plan(F, runs_all):
    """iteration 7 (technical blocking; coopdx ground push, doorpass.py + lib_dx): every open / entrance doorway's
    COLLISION opening is widened to DOOR_COL_MIN along its wall line. The wall line is the chain of collinear runs
    that touch the door's run (the plan often splits one wall into several pieces); the opening stays 0.25 m inside
    the chain's ends (the walls that meet it there). The part beyond the door's own run is cut from the collinear
    neighbours' collision (r["col_cuts"]); the door's own run gets r["col_spans"][door index]."""
    for r in runs_all:
        r.setdefault("col_spans", {})
        r.setdefault("col_cuts", [])
    for r in runs_all:
        if not r["doors"]:
            continue
        pa, RL = r["pa"], r["RL"]
        u = ((r["pb"][0] - pa[0]) / RL, (r["pb"][1] - pa[1]) / RL)

        def T(p_):
            return (p_[0] - pa[0]) * u[0] + (p_[1] - pa[1]) * u[1]

        def off(p_):
            return abs((p_[0] - pa[0]) * u[1] - (p_[1] - pa[1]) * u[0])
        col = []
        for ro in runs_all:
            uo = ((ro["pb"][0] - ro["pa"][0]) / ro["RL"], (ro["pb"][1] - ro["pa"][1]) / ro["RL"])
            if abs(uo[0] * u[0] + uo[1] * u[1]) < 0.9998 or off(ro["pa"]) > 0.02 or off(ro["pb"]) > 0.02:
                continue
            t0, t1 = sorted((T(ro["pa"]), T(ro["pb"])))
            col.append((t0, t1, ro))
        for q0, q1, di, dext in r["doors"]:
            kind_ = _door_kind(F, pa, r["pb"], RL, r["L"], r["R"], q0, q1, di)
            if kind_ not in ("open", "entrance"):
                continue
            lo, hi = 0.0, RL
            grew = True
            while grew:
                grew = False
                for t0, t1, ro in col:
                    if t1 >= lo - 0.02 and t0 <= hi + 0.02 and (t0 < lo - 1e-6 or t1 > hi + 1e-6):
                        lo, hi = min(lo, t0), max(hi, t1)
                        grew = True
            c0, c1 = _door_col_span(q0, q1, min(q0, lo + 0.25), max(q1, hi - 0.25))
            r["col_spans"][di] = (c0, c1)
            hd_ = DOOR_H if kind_ == "open" else GLASS_DOOR_H
            for t0, t1, ro in col:
                if ro is r:
                    continue
                # the widened span in ro's own run coordinates
                p0 = (pa[0] + u[0] * c0, pa[1] + u[1] * c0)
                p1 = (pa[0] + u[0] * c1, pa[1] + u[1] * c1)
                uo = ((ro["pb"][0] - ro["pa"][0]) / ro["RL"], (ro["pb"][1] - ro["pa"][1]) / ro["RL"])
                s0_, s1_ = sorted(((p_[0] - ro["pa"][0]) * uo[0] + (p_[1] - ro["pa"][1]) * uo[1]) for p_ in (p0, p1))
                s0_, s1_ = max(0.0, s0_), min(ro["RL"], s1_)
                if s1_ - s0_ > 0.01:
                    ro["col_cuts"].append((s0_, s1_, hd_))


def _door_kind(F, pa, pb, RL, left, right, d0, d1, di):
    """What a plan door d0 .. d1 (run coordinates) on run pa -> pb becomes: 'open', 'entrance', 'closed',
    'closed_ext', 'glazed' or None (no walkable side). Shared by the run assembly (DOOR_COL_MIN spans) and _wall_run."""
    fid = F.id
    kinds = {left[0], right[0]}
    ent = entrance_at(fid, (pa[0] + (pb[0] - pa[0]) * d0 / RL, pa[1] + (pb[1] - pa[1]) * d0 / RL),
                      (pa[0] + (pb[0] - pa[0]) * d1 / RL, pa[1] + (pb[1] - pa[1]) * d1 / RL))
    mid = (pa[0] + (pb[0] - pa[0]) * (d0 + d1) / 2 / RL, pa[1] + (pb[1] - pa[1]) * (d0 + d1) / 2 / RL)
    open_ext = any(R.seg_point_dist(mid, (od[0], od[1]), (od[2], od[3])) < 0.6
                   for e in ENTRANCES if e["floor"] == fid for od in e.get("open_doors", ()))
    open_ext = open_ext or _terrace_door(fid, mid)
    if open_ext and ent is None:
        ent = True
    if kinds == {"W"} and di in _closed_look(F):
        return "closed"                                 # fidelity-4 r2: a meeting room's second door, closed
    if kinds == {"W"}:
        return "open"
    if "W" in kinds and ent is not None and isinstance(ent, dict) and not _in_entrance(ent, pa, pb, RL, d0, d1):
        # iteration 7 (technical improvement 6; terr.py): a plan door bay that lies mostly OUTSIDE its entrance's
        # warp strip (the South Terrace's west bay, x -389.5 .. -387.7 vs the strip from -388.2) is glazed: no
        # opening (the wall's curtain glass + collision fill it); Mario stood stuck in it, outside, unwarped
        return "glazed"
    if "W" in kinds and ent is not None:
        return "entrance"
    if "W" in kinds:
        return "closed_ext" if "O" in kinds else "closed"
    return None


def _wall_run(RZ, F, V, C, CW, pa, pb, left, right, doors, stats, accent=(), col_spans=None, col_cuts=()):
    fid, z = F.id, F.z
    RL = math.dist(pa, pb)
    if RL < 0.05:
        return
    # user-photo pass (B16): the Game Room entrance is an aluminium / glass double door with a glass transom: steel
    # jambs and returns, the GLASS_DOOR_H head (the leaves, pulls and transom: g_userphoto_ground())
    gr_entry = {getattr(left[1], "id", None), getattr(right[1], "id", None)} == {"game_room", "g_corridor_02"}
    stats["walls"] += 1
    sides = {"L": left, "R": right}
    ext_wall = "O" in (left[0], right[0])
    t = (EXT_T if ext_wall else WALL_T) / 2
    # door handling on this run
    holes = []          # (s0, s1, z0 rel, z1 rel) in run coordinates, for both faces
    col_holes = []      # the same doorways in collision (widened to DOOR_COL_MIN)
    door_recs = []
    for d0, d1, di, dext in doors:
        kind_ = _door_kind(F, pa, pb, RL, left, right, d0, d1, di)
        if kind_ in ("open", "entrance"):
            hd_ = DOOR_H if (kind_ == "open" and not gr_entry) else GLASS_DOOR_H
            holes.append((d0, d1, 0.0, hd_))
            c0_, c1_ = (col_spans or {}).get(di, (d0, d1))
            col_holes.append((max(0.0, c0_), min(RL, c1_), 0.0, hd_))
            door_recs.append((kind_, d0, d1))
            if kind_ == "open":
                stats["doors_open"] += 1
        elif kind_ in ("closed", "closed_ext"):
            door_recs.append((kind_, d0, d1))
            stats["doors_closed"] += 1
    # iteration 7: collision-only cuts from a neighbouring run's widened doorway (same plan wall, DOOR_COL_MIN)
    for c0_, c1_, hd_ in col_cuts:
        if c1_ - c0_ > 0.01:
            col_holes.append((c0_, c1_, 0.0, hd_))
    for side in ("L", "R"):
        cls, zn = sides[side]
        ocls, ozn = sides["R" if side == "L" else "L"]
        fa, fb, nrm = _side_pts(pa, pb, side, t)

        def S(s):
            return s if side == "R" else RL - s
        hs = [(min(S(h[0]), S(h[1])), max(S(h[0]), S(h[1])), z + h[2], z + h[3]) for h in holes]
        hs_col = [(min(S(h[0]), S(h[1])), max(S(h[0]), S(h[1])), z + h[2], z + h[3]) for h in col_holes]
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
            if zn.id == "g_corridor_02" and all(-447.5 <= p_[0] <= -442.6 and -273.5 <= p_[1] <= -266.3
                                                 for p_ in (pa, pb)):
                mat = "int_ru_wall_royal"           # user-photo pass (user_03, user_11): the Blue elevator lobby
            elif zn.id == "g_corridor_02" and all(-462.0 <= p_[0] <= -421.0 and -282.5 <= p_[1] <= -274.5
                                                   for p_ in (pa, pb)):
                mat = "int_ru_wall_cream"           # user-photo pass (B12): the Game Room / barbershop corridor
            elif ozn is not None and ozn.id in ("l1_room_07", "l2_room_02", "l3_room_108") and \
                    zn.type == "corridor" and abs(pa[1] - pb[1]) < 0.6 and \
                    all(-418.7 <= p_[0] <= -413.3 and (-275.5 <= p_[1] <= -274.6 or -267.2 <= p_[1] <= -266.4)
                        for p_ in (pa, pb)):
                # photo pass round 2 (atrium leftovers; C02, C06, user_05): the Gators tower's north / south faces
                # on the L1-L3 corridors are the same royal-blue cladding as its void face
                mat = "int_ru_wall_royal"
            hh = list(hs)
            if ozn is not None and ozn.id in ("food_court_servery", "l1_room_02"):
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
            col_face(CW, fa, fb, z, z + h, holes=[x for x in hs_col],
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
                    hd = DOOR_H if (kind == "open" and not gr_entry) else GLASS_DOOR_H
                    # jambs + head trim on this face
                    # aluminium frames at entrances and round the vestibules (ru_ribbon_cutting_doors), wood elsewhere
                    jm = "int_ru_steel" if (kind == "entrance" or "vestibule" in (zn.type, getattr(ozn, "type", None))
                                            or _meeting_door(fid, zn, ozn) or gr_entry) else "int_ru_wood_panel"
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
        hd = DOOR_H if (kind == "open" and not gr_entry) else GLASS_DOOR_H
        da = (pa[0] + (pb[0] - pa[0]) * d0 / RL, pa[1] + (pb[1] - pa[1]) * d0 / RL)
        db = (pa[0] + (pb[0] - pa[0]) * d1 / RL, pa[1] + (pb[1] - pa[1]) * d1 / RL)
        n = ((pb[1] - pa[1]) / RL, -(pb[0] - pa[0]) / RL)
        lw = left[1].style["clear"] if left[0] == "W" and left[1] and left[1].style else F.clear
        rw = right[1].style["clear"] if right[0] == "W" and right[1] and right[1].style else F.clear
        top = min(lw, rw)
        R.seg_box(V, da, db, t, z + hd, z + top, "int_ru_wall", faces="bot")
        c0_, c1_ = (col_spans or {}).get(next((di_ for e0_, e1_, di_, _x in doors if abs(e0_ - d0) < 1e-9
                                               and abs(e1_ - d1) < 1e-9), None), (d0, d1))
        ca_ = (pa[0] + (pb[0] - pa[0]) * c0_ / RL, pa[1] + (pb[1] - pa[1]) * c0_ / RL)
        cb_ = (pa[0] + (pb[0] - pa[0]) * c1_ / RL, pa[1] + (pb[1] - pa[1]) * c1_ / RL)
        C.poly([(ca_[0] - n[0] * t, ca_[1] - n[1] * t, z + hd), (cb_[0] - n[0] * t, cb_[1] - n[1] * t, z + hd),
                (cb_[0] + n[0] * t, cb_[1] + n[1] * t, z + hd), (ca_[0] + n[0] * t, ca_[1] + n[1] * t, z + hd)],
               K.COL, normal_hint=(0, 0, -1))
        # jamb faces (wall thickness) visual + collision
        for p, sgn, cp_ in ((da, 1, ca_), (db, -1, cb_)):
            q0 = (p[0] + n[0] * t, p[1] + n[1] * t)
            q1 = (p[0] - n[0] * t, p[1] - n[1] * t)
            k0_ = (cp_[0] + n[0] * t, cp_[1] + n[1] * t)          # the jamb's collision face (DOOR_COL_MIN)
            k1_ = (cp_[0] - n[0] * t, cp_[1] - n[1] * t)
            dir_ = ((pb[0] - pa[0]) / RL * sgn, (pb[1] - pa[1]) / RL * sgn)
            vest = "vestibule" in (getattr(left[1], "type", None), getattr(right[1], "type", None))
            # fidelity-4 r2: the meeting rooms' open doorways get painted returns (the wood returns read as door
            # leaves standing open into the L2 / L3 corridors)
            jret = "int_ru_wall" if _meeting_door(fid, left[1], right[1]) else \
                ("int_ru_wood_panel" if (kind == "open" and not vest and not gr_entry) else "int_ru_steel")
            # iteration 8 (technical improvement 4): a jamb return that lies on a cross wall's face (a door at a wall
            # junction, e.g. L2 door 77 at plan x -463.3) stands 1.2 cm into the opening: it was coplanar with that
            # face (wall x wood_panel, 1.82 m2 visible). Visual only; the collision jamb stays.
            if _jamb_on_cross_face(F, p, dir_):
                q0 = (q0[0] + dir_[0] * 0.012, q0[1] + dir_[1] * 0.012)
                q1 = (q1[0] + dir_[0] * 0.012, q1[1] + dir_[1] * 0.012)
            V.poly([(q0[0], q0[1], z), (q1[0], q1[1], z), (q1[0], q1[1], z + hd), (q0[0], q0[1], z + hd)],
                   jret,
                   normal_hint=(dir_[0], dir_[1], 0))
            C.poly([(k0_[0], k0_[1], z), (k1_[0], k1_[1], z), (k1_[0], k1_[1], z + hd), (k0_[0], k0_[1], z + hd)], K.COL,
                   normal_hint=(dir_[0], dir_[1], 0))
        if kind == "open":
            zl = left[1].style["floor"] if left[1] and left[1].style else "int_ru_terrazzo"
            threshold(V, C, da, db, n, z, 2 * t + 0.5, zl)


def _jamb_on_cross_face(F, p, d):
    """True when a plan wall perpendicular to the door's run (parallel to the jamb normal d's plane) has a face
    within 1 cm of the jamb point p and covers it along its length (iteration 8)."""
    for w in F.walls:
        a, b = (w[0], w[1]), (w[2], w[3])
        L = math.dist(a, b)
        if L < 0.05:
            continue
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        if abs(ux * d[0] + uy * d[1]) > 0.05:          # the cross wall runs across the jamb normal
            continue
        s_ = (p[0] - a[0]) * ux + (p[1] - a[1]) * uy
        if s_ < -0.16 or s_ > L + 0.16:
            continue
        off = abs((p[0] - a[0]) * uy - (p[1] - a[1]) * ux)
        if any(abs(off - h_) < 0.01 for h_ in (WALL_T / 2, EXT_T / 2)):
            return True
    return False


def _storefront_holes(fa, fb, z, near=0.5, h=None):
    """Openings in the corridor face of the servery wall where the SERVERY_FRONTS storefronts are."""
    h = FC_FRONT_H if h is None else h
    L = math.dist(fa, fb)
    if L < 0.2:
        return []
    dx, dy = (fb[0] - fa[0]) / L, (fb[1] - fa[1]) / L
    out = []
    for a, b, *_ in SERVERY_FRONTS + SERVERY2_FRONTS:
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
    if t in ("elevator", "elevator_car") or zn.type == "elevator_car":
        return "int_ru_door_elev"           # user-photo pass (user_11): the walkable Blue cars are stainless too           # brushed-steel sliding doors + call buttons (fidelity-4)
    if t == "hotel_room":
        return "int_ru_door_hotel"          # cherry guest-room door with a brass number plate (fidelity-4)
    if t in ("restroom", "service", "room", "elevator") and (ozn is None or not ozn.name.startswith("Stair")):
        return "int_ru_door" if t == "restroom" else "int_ru_door_steel" if t in ("service", "elevator") else "int_ru_door"
    if "career_connections_center" in (zn.id, getattr(ozn, "id", "")):
        return "int_ru_wall_navy"           # user-photo pass (user_14, user_16): the CCC doors are navy leaves
    if t in ("office", "office_suite", "retail", "dining_retail", "food_servery"):
        return "int_ru_door_glass" if t in ("office_suite", "retail", "dining_retail") else "int_ru_door"
    if "rion_ballroom" in (zn.id, getattr(ozn, "id", "")):
        return "int_ru_door"                # user-photo pass (C03, C12, C13): the Rion's doors are honey wood
    if zn.type == "ballroom" or (ozn is not None and ozn.type == "ballroom"):
        return "int_ru_door_walnut"
    if zn.fid in ("L2", "L3") and "meeting_room" in (zn.type, t):
        return "int_ru_door_meeting_honey"  # user-photo pass (C08): honey leaves (were walnut)        # fidelity-4 r2: walnut leaf, narrow vision lite, lever
    return "int_ru_door"


# (floor, plan point at the block's end, trim m). Iteration 9 tried ("L3", (-396.2, -265.8), 0.2) for technical
# improvement 5 and left it out: falls_fast found 4 new walk-off points at (7386, 1800, -2707) through the gap
RAIL_END_TRIM = []


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
    # user-photo pass (B05, B06): the L1 north curtain wall at the atrium stair head has BLACK mullions
    north_l1 = abs(z - Z["L1"]) < 0.01 and all(-259.8 <= p_[1] <= -257.6 and -393.6 <= p_[0] <= -368.0 for p_ in (a, b))
    # user-photo pass (B02): the food court's curtain wall (L1 south of the core) has black mullions too
    fc_l1 = abs(z - Z["L1"]) < 0.01 and (a[1] + b[1]) / 2 < -282.5 and (a[0] + b[0]) / 2 > -462.0
    mullions(V, ca, cb, z + sill, z + head, bay=bay, t=0.04,
             mat="int_ru_black" if (north_l1 or fc_l1) else "int_ru_steel",
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
               "int_ru_picket2", uvs=[(0, 0), (Lr / 1.1, 0), (Lr / 1.1, 1), (0, 1)], ao=1.0)
        R.seg_box(V, ra, rb, 0.04, z + RAIL_H, z + RAIL_H + 0.06, "int_ru_maple", faces="sidetop")
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
        # iteration 9 (technical improvement 5; rscan): hook to trim a thick block's end back (RAIL_END_TRIM; empty:
        # the L3 stub at plan (-396.2, -265.8) trimmed 0.2 m opened a walk-off, so it needs a rendered return instead)
        for fid_, tp_, tr_ in RAIL_END_TRIM:
            if fid_ != F.id or not segs:
                continue
            q0, q1, th = segs[0]
            if th and math.dist((a[0] + ux * q0, a[1] + uy * q0), tp_) < 0.35 and q1 - q0 > tr_ + 0.3:
                segs[0] = (q0 + tr_, q1, th)
            q0, q1, th = segs[-1]
            if th and math.dist((a[0] + ux * q1, a[1] + uy * q1), tp_) < 0.35 and q1 - q0 > tr_ + 0.3:
                segs[-1] = (q0, q1 - tr_, th)
        for q0, q1, thick in segs:
            if q1 - q0 < 0.02:
                continue
            ca_ = (a[0] + ux * q0 + nx * (0.03 if thick else -0.12), a[1] + uy * q0 + ny * (0.03 if thick else -0.12))
            cb_ = (a[0] + ux * q1 + nx * (0.03 if thick else -0.12), a[1] + uy * q1 + ny * (0.03 if thick else -0.12))
            R.col_seg(C, ca_, cb_, 0.3 if thick else 0.15, z, z + RAIL_H + 0.06, K.COL_NOCAM)
        # iteration 6 (technical improvement 9): where the 0.6 m block steps down to the 0.3 m one beside a flight,
        # its 0.3 m outboard end cap stood as an invisible wall over the flight's edge (rscan: three 0.34 m2 stubs
        # with no render within 20 u). Each step now carries a rendered picket return + steel cap on that face
        # (the balcony rail turning down the flight's side, as in ru_atrium_hdr_flickr).
        for (q0, q1, th0), (q2, q3, th1) in zip(segs, segs[1:]):
            if th0 == th1 or q1 - q0 < 0.02 or q3 - q2 < 0.02:
                continue
            qa_ = (a[0] + ux * q1 + nx * 0.035, a[1] + uy * q1 + ny * 0.035)
            qb_ = (a[0] + ux * q1 + nx * 0.325, a[1] + uy * q1 + ny * 0.325)
            V.poly([(qa_[0], qa_[1], z), (qb_[0], qb_[1], z), (qb_[0], qb_[1], z + RAIL_H), (qa_[0], qa_[1], z + RAIL_H)],
                   "int_ru_picket2", uvs=[(0, 0), (0.29 / 1.1, 0), (0.29 / 1.1, 1), (0, 1)], ao=1.0)
            R.seg_box(V, qa_, qb_, 0.035, z + RAIL_H, z + RAIL_H + 0.06, "int_ru_maple", faces="sidetop")
        # iteration 7 (technical improvement 3; rscan): where a run ENDS at a scissor-flight gap on a 0.6 m block, its
        # 0.6 m end cap was the last invisible stub (L2 NE head plan (-393.2, -265.5), L3 (-396.2, -265.9)): the rail
        # turns down the flight's side there too (picket return + steel cap from the rail line to the cap's outer edge)
        for q_e, th_, cut_ in ((segs[0][0], segs[0][2], r0 > 1e-3), (segs[-1][1], segs[-1][2], r1 < L - 1e-3)):
            if not (th_ and cut_):
                continue
            qa_ = (a[0] + ux * q_e - nx * 0.12, a[1] + uy * q_e - ny * 0.12)
            qb_ = (a[0] + ux * q_e + nx * 0.325, a[1] + uy * q_e + ny * 0.325)
            V.poly([(qa_[0], qa_[1], z), (qb_[0], qb_[1], z), (qb_[0], qb_[1], z + RAIL_H), (qa_[0], qa_[1], z + RAIL_H)],
                   "int_ru_picket2", uvs=[(0, 0), (0.445 / 1.1, 0), (0.445 / 1.1, 1), (0, 1)], ao=1.0)
            R.seg_box(V, qa_, qb_, 0.035, z + RAIL_H, z + RAIL_H + 0.06, "int_ru_maple", faces="sidetop")
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


def _wayfind_g_white(V, z, zc):
    """The white two-tier Ground sign (user_03, B17) across the corridor at y -264.6, x -446.9..-442.9: upper tier
    ATRIUM | MEETING ROOMS G310-G330 | SENATE CHAMBER + arrow (atrium east), lower tier, right-aligned on the south
    face, HOTEL RECEPTION + arrow (hotel west). Each face reads left to right with its own arrows."""
    yc, x0, x1 = -264.6, -446.9, -442.9
    tiers = ((x0, x1, z + 4.0, z + 4.35, ("int_ru_wayfind_G_w_a", "int_ru_wayfind_G_w_b"), 1),
             (-445.1, x1, z + 3.4, z + 3.75, ("int_ru_wayfind_G_w_c",), -1))
    for ta, tb, zb_, zt_, mats, east in tiers:
        V.box(ta, yc - 0.03, zb_ - 0.04, tb, yc + 0.03, zt_ + 0.04, "int_ru_white", faces="+x-x-z+z")
        for face in (-1, 1):                # -1: the south face (normal -y), +1: the north face
            # walking a -> b keeps the normal on the right: south face west -> east, north face east -> west
            if face < 0:
                ta_, tb_ = ta + 0.05, tb - 0.5         # text, then the arrow tile at the right (east) end
                arr = (tb - 0.45, tb - 0.05)
            else:
                ta_, tb_ = tb - 0.05, ta + 0.5         # text from the east, the arrow tile at the west end
                arr = (ta + 0.45, ta + 0.05)
            n = 2 * len(mats)
            for q_ in range(n):
                pa = (ta_ + (tb_ - ta_) * q_ / n, yc)
                pb = (ta_ + (tb_ - ta_) * (q_ + 1) / n, yc)
                R.panel(V, pa, pb, zb_, zt_, mats[q_ // 2], off=0.035, glow=True, v0=0.5 if q_ % 2 == 0 else 0.0,
                        v1=1.0 if q_ % 2 == 0 else 0.5)
            # the arrow points +u (toward b) unless mirrored: the target lies east (east=1) or west (east=-1)
            toward_b_east = face < 0
            mirror = (east > 0) != toward_b_east
            R.panel(V, (arr[0], yc), (arr[1], yc), zb_ + 0.0, zt_, "int_ru_arrow_navy", off=0.04,
                    u0=1.0 if mirror else 0.0, u1=0.0 if mirror else 1.0)
    R.seg_box(V, (x0 - 0.02, yc), (x1 + 0.02, yc), 0.045, z + 4.39, z + 4.43, "int_ru_steel", faces="sidetop")
    for xr in (x0 + 0.4, x1 - 0.4):
        V.box(xr - 0.012, yc - 0.012, z + 4.43, xr + 0.012, yc + 0.012, zc, "int_ru_steel", faces="+x-x+y-y")
    for xr in (-444.8, x1 - 0.3):
        V.box(xr - 0.01, yc - 0.01, z + 3.79, xr + 0.01, yc + 0.01, z + 3.96, "int_ru_steel", faces="+x-x+y-y")


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
        if fid == "L1":
            # user-photo pass (user_11): L1's sign is light grey with navy caps, at the Blue lobby mouth
            _wayfind_l1_grey(V, F.z, zc)
            RZ.kit_add(P, fid, tag=f"wayfind_{fid}")
            RZ.points.setdefault("wayfinding", {})[fid] = {"name": f"interior_wayfind_{fid}", "p": [xc, yc, F.z],
                                                           "kind": "ground"}     # (the point entry stays where it was)
            continue
        if fid == "G":
            # user-photo pass (user_03, B17): Ground's hanging sign is WHITE with dark caps and navy arrow tiles,
            # two tiers, at the head of the Subway corridor (the point entry stays where it was)
            _wayfind_g_white(V, F.z, zc)
            RZ.kit_add(P, fid, tag=f"wayfind_{fid}")
            RZ.points.setdefault("wayfinding", {})[fid] = {"name": f"interior_wayfind_{fid}", "p": [xc, yc, F.z],
                                                           "kind": "ground"}
            continue
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
    _trim_unreachable_collision(RZ)
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
    RZ.stats["goomba_spots"] = len(GOOMBA_SPOTS)
    _arm_goomba_placer()
    return RZ


HIGH_HALLS = ("grand_ballroom",)     # big double-height halls with no wall-kick shaft (the small 11.4 m rooms keep theirs)


def _sealed_at(F, q):
    """A plan point inside a sealed room that nothing brings Mario into (the elevator cars are S zones too, but the
    elevator warps land Mario in them, so they keep every face)."""
    c, zn = F.cls_at(q)
    return c == "S" and zn is not None and zn.type != "elevator"


def _segx(p1, p2, p3, p4):
    d1 = (p2[0] - p1[0]) * (p3[1] - p1[1]) - (p2[1] - p1[1]) * (p3[0] - p1[0])
    d2 = (p2[0] - p1[0]) * (p4[1] - p1[1]) - (p2[1] - p1[1]) * (p4[0] - p1[0])
    d3 = (p4[0] - p3[0]) * (p1[1] - p3[1]) - (p4[1] - p3[1]) * (p1[0] - p3[0])
    d4 = (p4[0] - p3[0]) * (p2[1] - p3[1]) - (p4[1] - p3[1]) * (p2[0] - p3[0])
    return d1 * d2 < 0.0 and d3 * d4 < 0.0


def _poly_sealed(F, pts2):
    """True when the plan polygon pts2 lies wholly in sealed rooms: its centroid and nudged corners are sealed, and
    no other zone or void (a W elevator car inside a sealed block, a corridor) overlaps it at all."""
    cx = sum(q[0] for q in pts2) / len(pts2)
    cy = sum(q[1] for q in pts2) / len(pts2)
    smp = [(cx, cy)] + [(q[0] + (cx - q[0]) * 0.1, q[1] + (cy - q[1]) * 0.1) for q in pts2]
    if not all(_sealed_at(F, q_) for q_ in smp):
        return False
    bx0, bx1 = min(q[0] for q in pts2), max(q[0] for q in pts2)
    by0, by1 = min(q[1] for q in pts2), max(q[1] for q in pts2)
    others = [zn.poly for zn in F.zones if not (zn.cls == "S" and zn.type != "elevator")] + list(F.voids)
    for op in others:
        if max(q[0] for q in op) < bx0 or min(q[0] for q in op) > bx1 or max(q[1] for q in op) < by0 or \
                min(q[1] for q in op) > by1:
            continue
        oc = (sum(q[0] for q in op) / len(op), sum(q[1] for q in op) / len(op))
        if any(R.pip(q, pts2) for q in op) or R.pip(oc, pts2) or any(R.pip(q, op) for q in pts2):
            return False
        for i in range(len(pts2)):
            for j in range(len(op)):
                if _segx(pts2[i - 1], pts2[i], op[j - 1], op[j]):
                    return False
    return True


def _trim_unreachable_collision(RZ):
    """iteration 9 (technical improvement 3: area 2 was 12,899 collision tris, 611 over the 12,288 soft line): the
    floor shells drop collision Mario can never touch: ceilings over sealed (S) rooms, ceilings 9 m or more above
    their floor (the double-height Grand Ballroom's 11.4 m ceiling: no jump from its 0.6 m stage reaches 7.5 m),
    walls with sealed rooms on both sides, and exact duplicate faces. Visual geometry is untouched."""
    def nz_(pts):
        a, b, c = pts[0], pts[1], pts[2]
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    stats = {"ceil_sealed": 0, "ceil_high": 0, "floor_sealed": 0, "wall_sealed": 0, "dup": 0}
    seen = {}
    for t, g, p in RZ.kit.items:
        if g not in RZ.floors:
            continue
        F = RZ.floors[g]
        keep = []
        sg_ = seen.setdefault(g, set())
        shell = t.startswith("shell_")
        for pl in p.collision.polys:
            pts = pl.pts
            n_t = len(pts) - 2
            key = (tuple(sorted((round(q[0], 3), round(q[1], 3), round(q[2], 3)) for q in pts)),
                   round(nz_(pts), 4), getattr(pl, "mat", None))
            if key in sg_:
                stats["dup"] += n_t
                continue
            sg_.add(key)
            if not shell:
                keep.append(pl)
                continue
            zs = [q[2] for q in pts]
            cx = sum(q[0] for q in pts) / len(pts)
            cy = sum(q[1] for q in pts) / len(pts)
            if max(zs) - min(zs) < 0.01:
                smp = [(cx, cy)] + [(q[0] + (cx - q[0]) * 0.1, q[1] + (cy - q[1]) * 0.1) for q in pts]
                if nz_(pts) < 0.0:
                    if zs[0] - F.z >= 9.0 and all((F.cls_at(q_)[1] is not None and F.cls_at(q_)[1].id in HIGH_HALLS)
                                                  for q_ in smp):
                        stats["ceil_high"] += n_t
                        continue
                    # (sealed-room ceilings / floors were tried and left out: the QA door sweep showed walks
                    # passing INTO several S rooms (G #23, #39, L1 #4, L2 #23, #27, #141, L3 #34, #35, L6 #38),
                    # which then found no floor)
            else:
                # a vertical face: both sides sealed at a quarter and three quarters of its length
                lo = min(range(len(pts)), key=lambda i: (pts[i][2], i))
                hz = [q for q in pts if abs(q[2] - zs[0]) < 0.01 or True]
                xs_ = sorted(set((round(q[0], 4), round(q[1], 4)) for q in hz))
                if len(xs_) >= 2:
                    e0 = min(xs_, key=lambda q: (q[0], q[1]))
                    e1 = max(xs_, key=lambda q: math.dist(q, e0))
                    L = math.dist(e0, e1)
                    if L > 0.05:
                        ux, uy = (e1[0] - e0[0]) / L, (e1[1] - e0[1]) / L
                        sealed = True
                        for f_ in (0.25, 0.5, 0.75):
                            mx, my = e0[0] + ux * L * f_, e0[1] + uy * L * f_
                            for sg in (-1.0, 1.0):
                                if F.cls_at((mx - uy * 0.4 * sg, my + ux * 0.4 * sg))[0] != "S":
                                    sealed = False
                        if sealed:
                            stats["wall_sealed"] += n_t
                            continue
            keep.append(pl)
        p.collision.polys[:] = keep
    RZ.stats["collision_trim"] = stats
    print("REITZ collision trim:", stats)


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
    {"kind": "1up", "name": "uf letters 1-up", "pos": (-411.33, -265.6, 2.6)},       # the letters stand on the floor (B09)
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
    # design + leftovers pass (fun): a coin trail up the royal-blue Gators elevator tower (user_05, B10,
    # C02, C06): a line along its glazed base on Ground (between the tower face x -413.85 and the lounge furniture),
    # then one line per balcony storey beside the tower, alternating north / south so the trail zigzags up the
    # scissor stairs; and a line down lane 7's approach over the foul line (between the ball returns: the white
    # columns between the lane pairs stand at y -305.0 .. -304.4, so an across-the-approach line hits them)
    {"kind": "coin_line", "name": "gators tower base coins", "pos": (-413.2, -271.0, 0.0), "facing": 0.0},
    {"kind": "coin_line", "name": "gators tower l1 coins", "pos": (-413.0, -265.7, 6.0), "facing": 90.0},
    {"kind": "coin_line", "name": "gators tower l2 coins", "pos": (-413.0, -276.1, 12.0), "facing": 90.0},
    {"kind": "coin_line", "name": "gators tower l3 coins", "pos": (-413.0, -265.7, 18.0), "facing": 90.0},
    {"kind": "coin_line", "name": "bowling approach coins", "pos": (-446.35, -309.4, 0.0), "facing": 0.0},
]
# fix round 4 (design pass, improvement 2): Goomba spots checked in the reachability flood (>= 2 m of open floor all
# round). build_interior.build_area (the area-module path, shared with other stages, not this module's to edit) has
# no "goomba" branch in its pickup loop, so kind "goomba" in PICKUPS would be dropped silently.
# iteration 7 (design improvement 1): placed through _arm_goomba_placer() (below), called at the end of build().
GOOMBA_SPOTS = [
    {"kind": "goomba", "name": "game room goomba 1", "pos": (-423.5, -304.5, 0.0), "facing": 0.0},
    {"kind": "goomba", "name": "game room goomba 2", "pos": (-424.5, -312.5, 0.0), "facing": 180.0},
    {"kind": "goomba", "name": "ll corridor goomba", "pos": (-407.5, -272.5, -6.0), "facing": 90.0},
]


def _arm_goomba_placer():
    """iteration 7 (design improvement 1: area 2 had no enemies, play was a coin walk). build_stage calls build() and
    then build_interior.build_area(), which makes this area's stage_pickups.Placer(S, probe) with S.key == KEY and runs
    the PICKUPS loop (coin / coin_line / coin_ring / heart / 1up only). A one-shot Placer subclass is armed here: when
    that Placer is made for this area it puts back the stock class and places GOOMBA_SPOTS with the stock
    Placer.goomba (floor probe on the area's own collision + 1.2 m head room; vanilla bhvGoomba / MODEL_GOOMBA, which
    the level loads with common0; one coin each when stomped). Any other Placer (area 1, another stage) is a plain
    Placer: the subclass checks S.key. Nothing in build_interior.py changes."""
    try:
        import stage_pickups as SP
    except Exception:                       # outside Blender (selftest): nothing to place
        return
    base = getattr(SP.Placer, "_sgl_base", SP.Placer)

    class _ReitzAreaPlacer(base):
        _sgl_base = base

        def __init__(self, S, probe):
            super().__init__(S, probe)
            if getattr(S, "key", None) == KEY:
                SP.Placer = base
                for it in GOOMBA_SPOTS:
                    self.goomba(it["name"], it["pos"], it.get("facing", 0.0))
    SP.Placer = _ReitzAreaPlacer
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
                # iteration 9 (fidelity-4 sweep): the rail + piers stop at the plan doors on this edge (L1 #19, #20,
                # #178, #181: the picket ran across the glass doors onto the walkway)
                for f0, f1 in _free_runs(F1, pa, pb, clear=0.1, min_len=0.3):
                    ra, rb = _sub(pa, pb, f0, f1)
                    Lr = f1 - f0
                    V.poly([(ra[0], ra[1], z), (rb[0], rb[1], z), (rb[0], rb[1], z + RAIL_H), (ra[0], ra[1], z + RAIL_H)],
                           "int_ru_picket", uvs=[(f0 / 1.1, 0), ((f0 + Lr) / 1.1, 0), ((f0 + Lr) / 1.1, 1), (f0 / 1.1, 1)])
            # canopy piers (fidelity pass 2): square white piers on the outer edge, <= 6.5 m apart, so the west
            # glass of the food court looks out on the covered walkway to the Bookstore
            if L > 3.0:
                n_p = int(math.ceil(L / 6.5))
                ux, uy = (pb[0] - pa[0]) / L, (pb[1] - pa[1]) / L
                inx, iny = -uy, ux              # left of pa -> pb on a CCW zone: into the walkway
                for k in range(n_p + 1):
                    if k == 0 and L < 6.0:
                        continue
                    if not _slot_clear(F1, pa, pb, L * k / n_p - 0.25, L * k / n_p + 0.25, 0.1):
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
    # iteration 9 (fidelity-4 blocking 1-3): no dressing face may stand inside a plan door opening (the slate band,
    # art boards and wall panels covered 27 doorways: invisible exits that Mario walked through)
    din = _decor_in_doors(M)
    print(f"   decor in door openings: {len(din)} faces"
          + (f" ({', '.join(sorted(set(f'{t}/{m}@{f}#{i}' for t, m, f, i in din))[:8])})" if din else ""))
    for t, m, f, i in din:
        probs.append((t, f"{m} stands in door {f}#{i}"))
    print("problems:", probs[:10] or "none")
    return probs



# ================================================================== the atrium (2016 wing): G lounge, voids L1-L3
# the plan's stair chevron (L1-L3 voids): tip, outer arm ends, inner tip (map m)
CHEVRON = {"tip": (-401.2, -271.3), "ne": (-395.6, -265.7), "se": (-397.3, -275.3), "inner": (-398.6, -271.3)}
STAIR_W = 1.8
LANDING_ALONG = 2.2
STAIR_STRINGER = 0.38                  # user-photo pass (user_02): deep white stringers (design pass 0.24)
LANDING_T = 0.30                       # ... landing slab thickness (user-photo pass; design pass 0.22)


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
        # iteration 6 (technical blocking): rail_outer_head - the SE flights' railings keep their void-side collision
        # face only over the top 0.4 m (the 14 cm two-faced rail threw Mario through itself at the L1 SE flight foot:
        # falls_fast 19 -> 0, spotfall_r L2 SE foot 1 -> 0). The NE flights keep the full closed rail: at the L2 NE
        # head the short outer face made the plug junction's 3-wall push worse (spotfall_r 1 -> 3)
        # iteration 7 (technical blocking): the outer face comes back wherever walkable floor lies beside the
        # flight's lower stretch (side walk-through, railside3.py): the Ground flight on both sides, the L2 flight on
        # its balcony side (+n). The L1 flight (void on both sides at its foot) stays inner-only + the 0.4 m head.
        roh_ = {"G": (None, None), "L1": 0.4, "L2": (0.4, None)}[lo]
        f1 = R.stair_flight(V, C, a_se, b_se, z0, zl, STAIR_W, stringer=STAIR_STRINGER, rail_outer_head=roh_,
                            rail_cap_foot=(lo in ("G", "L2")), rail_skirt=(1.9 if lo == "G" else None))
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
                   "int_ru_picket2", uvs=[(0, 0), (math.dist(ra, rb) / 1.1, 0), (math.dist(ra, rb) / 1.1, 1), (0, 1)])
            R.seg_box(V, ra, rb, 0.035, zl + RAIL_H, zl + RAIL_H + 0.06, "int_ru_maple", faces="sidetop")
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
               "int_ru_picket2", uvs=[(0, 0), (Lr / 1.1, 0), (Lr / 1.1, 1), (0, 1)])
        R.seg_box(V, ra, rb, 0.035, zl + RAIL_H, zl + RAIL_H + 0.06, "int_ru_maple", faces="sidetop")
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
        elif math.dist(a, b) > 1.0 and max(a[0], b[0]) < -413.5:
            # user-photo pass (user_05, B10, C09): the Gators elevator tower's royal-blue cladding rises through the
            # clerestory at the void's west end (was glass); its pilasters and the 'Gators' script: gators_tower()
            R.quad_wall(V, b, a, z0, z1, "int_ru_wall_royal", ao=0.95)
        elif math.dist(a, b) > 15.0 and _word_band(V, a, b, z0, z1):
            pass                    # user-photo pass (user_05, C09, C10): the giant BLUE / ORANGE word bands
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
        # iteration 7 (fidelity-1 improvement 5; ru_atrium_hdr_flickr): polished silver, not matte grey: the bright
        # int_ru_drum_panel, and a soft vertical highlight down the drum (per-facet shade 0.80 .. 1.0, peaking a little
        # north of mid-width where the photos catch the skylight)
        u_ = (my_ - ya_) / max(0.01, yb_ - ya_)
        ao_ = 0.80 + 0.20 * math.exp(-((u_ - 0.42) / 0.2) ** 2)
        V.poly([(pa[0], pa[1], z0), (pb[0], pb[1], z0), (pb[0], pb[1], zt), (pa[0], pa[1], zt)], "int_ru_drum_panel",
               normal_hint=(nh[0] / Lh, nh[1] / Lh, 0.0), ao=ao_)
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


# user-photo pass (the user's own photos user_05, C09, C10): the giant glowing royal-blue BLUE (south) and
# orange ORANGE (north) words on white bands with grey stripe / echo graphics, in the clerestory zone right over the
# L3 balconies. The glazing quad is SPLIT (no overlay): band z0 .. CLERE_BAND_TOP, glass above it and along the rest.
# photo pass round 2 (fidelity-atrium 2, design 3; C09, C10, user_05): the words read small and floating between two
# glass panes: the white wall now spans the WHOLE void face (plain white either side of the graphic band), the band
# and the letters are 1.2x wider and taller (top 25.0: letters ~1.45 m), the glazing runs only above them
CLERE_WORDS = {"S": (-404.5, 14.4, "int_ru_band_blue", "int_ru_word_blue", 8.4),
               "N": (-405.15, 16.2, "int_ru_band_orange", "int_ru_word_orange", 11.7)}
CLERE_BAND_TOP = 25.0


def _word_band(V, a, b, z0, z1):
    side = "S" if max(a[1], b[1]) < -274.0 else ("N" if min(a[1], b[1]) > -268.0 else None)
    if side is None:
        return False
    xc, wb, band_mat, word_mat, ww = CLERE_WORDS[side]

    def at(x):                                  # the point of b -> a (void on its right) at map x
        t_ = (x - b[0]) / (a[0] - b[0])
        return (b[0] + (a[0] - b[0]) * t_, b[1] + (a[1] - b[1]) * t_)
    sgn = 1.0 if a[0] > b[0] else -1.0
    cuts = [b[0], xc - sgn * wb / 2, xc + sgn * wb / 2, a[0]]
    for i in range(3):
        p_, q_ = at(cuts[i]), at(cuts[i + 1])
        if math.dist(p_, q_) < 0.05:
            continue
        zg = CLERE_BAND_TOP
        if i == 1:
            R.panel(V, p_, q_, z0, CLERE_BAND_TOP, band_mat)
            R.panel(V, at(xc - sgn * ww / 2), at(xc + sgn * ww / 2), z0 + 0.05, CLERE_BAND_TOP - 0.1, word_mat,
                    off=0.08, glow=True)     # 8 cm proud channel letters: the edges are slanted (1-3 cm read as coplanar)
        else:
            R.quad_wall(V, p_, q_, z0, CLERE_BAND_TOP, "int_ru_white")
        R.quad_wall(V, p_, q_, zg, z1 - 0.2, "int_ru_glass")
        mullions(V, p_, q_, zg, z1 - 0.2, bay=1.6, mat="int_ru_slat_dark", t=0.06)
        R.quad_wall(V, p_, q_, z1 - 0.2, z1, "int_ru_slat_dark")
    return True


# user-photo pass (user_05, B10, C02, C06, C09): the royal-blue clad 'Gators' glass elevator tower on the
# west void's west end (the plan block of the Orange elevators, x -418.4 .. -413.6, y -274.9 .. -266.7), Ground to the
# clerestory top. Visual only, on each storey's own void-side wall face (measured on the built area; the faces step a
# few cm between storeys): royal-blue pilasters 0.12 m deep, black-glass shaft bays 4 cm proud with thin white reveal
# lines (geometry, 3 cm in front of the glass; glass 6 cm proud: the faces are slanted), royal spandrel bands at the slabs, two lit glass cars, a glazed base
# with steel mullions on Ground and the orange 'Gators' script near the top.
GT_FACE = {"G": ((-413.9, -275.0), (-413.8, -266.7), 0.0, 5.4), "L1": ((-413.6, -275.3), (-413.5, -266.8), 5.4, 11.4),
           "L2": ((-413.5, -275.0), (-413.4, -266.5), 11.4, 17.4), "L3": ((-414.0, -275.2), (-413.9, -266.6), 17.4, 23.4),
           "top": ((-414.1, -275.1), (-414.0, -266.7), 23.4, ATRIUM_TOP)}
GT_PIL = ((-274.9, -274.2), (-271.1, -270.5), (-267.4, -266.7))
GT_BAYS = ((-274.2, -271.1), (-270.5, -267.4))
GT_CARS = {("L3", 0): (18.3, 21.0), ("L1", 1): (6.3, 9.0)}       # (storey, bay index 0 = south): car z range


def gators_tower(RZ):
    for fid, (fa, fb, z0, z1) in GT_FACE.items():
        P = K.Prop(f"gators_tower_{fid}")
        V = P.visual

        def wx(y, fa=fa, fb=fb):
            return fa[0] + (fb[0] - fa[0]) * (y - fa[1]) / (fb[1] - fa[1])
        for y0, y1 in GT_PIL:
            xa, xb = wx(y0) + 0.12, wx(y1) + 0.12
            R.quad_wall(V, (xa, y0), (xb, y1), z0, z1, "int_ru_wall_royal", ao=0.95)
            R.quad_wall(V, (xa - 0.14, y0), (xa, y0), z0, z1, "int_ru_wall_royal", ao=0.8)
            R.quad_wall(V, (xb, y1), (xb - 0.14, y1), z0, z1, "int_ru_wall_royal", ao=0.8)
            V.poly([(xa - 0.14, y0, z1), (xa, y0, z1), (xb, y1, z1), (xb - 0.14, y1, z1)], "int_ru_wall_royal",
                   normal_hint=(0, 0, 1))
        if fid == "top":
            # the 'Gators' script, mapped once on a 4.2 x 2.1 m card in front of the middle pilaster (glows)
            # (3 cm in front of the L3 storey's pilasters, whose face plane lies 10 cm east of the clerestory's)
            ya_, yb_ = -272.9, -268.7
            fl3a, fl3b = GT_FACE["L3"][0], GT_FACE["L3"][1]

            def wl3(y):
                return fl3a[0] + (fl3b[0] - fl3a[0]) * (y - fl3a[1]) / (fl3b[1] - fl3a[1])
            R.panel(V, (wl3(ya_) + 0.15, ya_), (wl3(yb_) + 0.15, yb_), 22.6, 24.7, "int_ru_sign_gators", glow=True)
            RZ.kit_add(P, "L3", tag="gators_tower_top")
            continue
        # royal spandrels at the slabs (z 6 / 12 / 18: -0.9 .. +0.3, in line with the balcony fascias), glass between
        spans = []
        for zs in (6.0, 12.0, 18.0):
            lo, hi = max(z0, zs - 0.9), min(z1, zs + 0.3)
            if hi - lo > 0.01:
                spans.append((lo, hi))
        zg0 = max([hi for lo, hi in spans if lo <= z0 + 0.01] + [z0])
        zg1 = min([lo for lo, hi in spans if hi >= z1 - 0.01] + [z1])
        for bi, (y0, y1) in enumerate(GT_BAYS):
            pa_, pb_ = (wx(y0), y0), (wx(y1), y1)
            for lo, hi in spans:
                R.panel(V, pa_, pb_, lo, hi, "int_ru_wall_royal", off=0.06, ao=0.95)
            R.panel(V, pa_, pb_, zg0, zg1, "int_ru_tower_glass", off=0.06)
            car = GT_CARS.get((fid, bi))
            if car:
                R.panel(V, pa_, pb_, car[0], car[1], "int_ru_tower_car", off=0.075, glow=True)
            if fid == "G":
                # glazed base: steel mullions every ~1.4 m and a transom at the door-head line
                n_ = max(1, int(round((y1 - y0) / 1.4)))
                for k in range(1, n_ + 1):
                    yk = y0 + (y1 - y0) * k / (n_ + 1)
                    R.panel(V, (wx(yk - 0.03), yk - 0.03), (wx(yk + 0.03), yk + 0.03), zg0, zg1, "int_ru_steel_bright",
                            off=0.09)
                R.panel(V, pa_, pb_, 2.95, 3.01, "int_ru_steel_bright", off=0.09)
            else:
                for f_ in (1.0 / 3.0, 2.0 / 3.0):
                    zr = zg0 + (zg1 - zg0) * f_
                    R.panel(V, pa_, pb_, zr - 0.015, zr + 0.015, "int_ru_white", off=0.09)
        RZ.kit_add(P, fid, tag=f"gators_tower_{fid}")


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
        inner = _inset_ortho(outer, 0.15)     # user-photo pass (B08, B09): royal triangle carpet, navy 0.15 m edge
        R.floor_poly(V, inner, z, "int_ru_carpet_tri_dk", step=3.0)    # photo pass round 2: ~25 % darker (B09)
        R.floor_poly(V, outer, z, "int_ru_fabric_navy", step=3.0, holes=(list(reversed(inner)),))
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
        if k < 6:
            # user-photo pass (B08, B09, B10, C01, user_02): rug 1 gets the photographed layout (below
            # stacking-chair rows facing the UF letters, a curving row of orange high-back swivels, charcoal sofas)
            k += 1
            continue
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
        # user-photo pass (B08, B09, C01, user_06): conversation groups of a charcoal leather sofa and club chairs with
        # grey seat and back, navy sides and maple arm caps (one orange high-back swivel on every other group)
        _put(R.lounge_sofa(2.25 if k % 3 == 1 else 1.75, mat="int_ru_leather_char", seat="int_ru_leather_char",
                           arm="int_ru_leather_char"), 0.0, -1.0, 0.0, f"lounge_sofa_{k}")
        left = R.lounge_chair("int_ru_fabric_navy", "int_ru_leather_grey", col=False, arm="int_ru_fabric_navy",
                              back="int_ru_leather_grey", cap="int_ru_maple")
        if k % 2 == 0:
            right = R.lounge_chair("int_ru_fabric_navy", "int_ru_leather_grey", col=False, arm="int_ru_fabric_navy",
                                   back="int_ru_leather_grey", cap="int_ru_maple")
        else:
            right = R.swivel_highback()
        _put(left, -0.5, 1.02, 180.0, f"lounge_chair_{k}_0")
        _put(right, 0.5, 1.02, 180.0, f"lounge_chair_{k}_1")
        k += 1
    # user-photo pass (B08, B09, B10, C01, user_02): rug 1, south from the UF letters: open terrazzo,
    # three rows of black stacking chairs facing the letters (the kit's own low no-cam box), a curving row of eight
    # orange high-back swivels with blue cushions (an arc through (-412.5, -272.6), (-408.0, -271.6), (-403.5, -272.6),
    # all facing its centre to the north), two runs of charcoal leather modular sofas (3 x 0.85 m) facing north.
    # Collision: 4 low no-cam boxes (was 6)
    RZ.kit_add(R.chair_rows(3, 8, kind="black"), "G", tag="lounge_rows", x=-409.4, y=-268.4, facing=0.0)
    arc_c, arc_r = (-408.0, -262.975), 8.625
    th = math.asin(4.5 / arc_r)
    for i in range(8):
        t_ = -th + 2.0 * th * i / 7.0
        RZ.kit_add(R.swivel_highback(), "G", tag=f"lounge_swivel_{i}", x=arc_c[0] + arc_r * math.sin(t_),
                   y=arc_c[1] - arc_r * math.cos(t_), facing=(-math.degrees(t_)) % 360.0)
    K.col_box(C, -412.9, -273.0, z, -403.1, -271.2, z + 0.48, K.COL_NOCAM)
    for i, xs_ in enumerate((-411.3, -404.7)):
        RZ.kit_add(R.lounge_sofa(2.55, mat="int_ru_leather_char", seat="int_ru_leather_char",
                                 arm="int_ru_leather_char"), "G", tag=f"lounge_char_sofa_{i}", x=xs_, y=-274.3, facing=0.0)
        K.col_box(C, xs_ - 1.3, -274.75, z, xs_ + 1.3, -273.85, z + 0.5, K.COL_NOCAM)
    # UF letters (facing south) on the gator-skin wall panel behind them
    # design + leftovers pass (B09, B10: the letters stand straight on the terrazzo, no blue plinth)
    RZ.kit_add(R.uf_letters(2.6, 0.7, base=False), "G", tag="uf_letters", x=-409.4, y=-265.6, facing=180.0)
    # fix round 4 (technical improvement): the gap between the letters' plinth and the 20 cm Senate Chamber wall is
    # filled (collision only, up to 2.2 m: below the letters' top, a reward spot): stepping off the plinth's back
    # pushed Mario through the thin wall
    # design + leftovers pass: with the plinth gone the fill is trimmed to the letters' own x extent (U west face
    # -411.525, F east face -407.275; 2.5 cm inside them), so its end faces stand flush with rendered letter faces
    K.col_box(P.collision, -411.50, -265.3, z, -407.30, -264.47, z + 2.2, K.COL_NOCAM)
    wall_a, wall_b = (-414.0, -264.36), (-404.6, -264.36)
    # fix round 4 (fidelity-1): the texture maps over 2 m (plates about 2x larger in world size)
    # fix round 5 (fidelity-1): the recipe now has 3 x 3 taupe plates on a cream network per tile, mapped over 1.0 m
    # (~0.33 m plates, the photo's ~0.3-0.4 m)
    # user-photo pass (B09): the grey-on-white skin panel starts at x -411.2 (the letters stay on it); west of it, three
    # tall orange values panels (4 cm off the wall) and a royal-blue column 0.3 m proud (0.3 m clear of plan door 6)
    wall_a = (-411.2, -264.36)
    R.panel(V, wall_a, wall_b, z, z + 5.3, "int_ru_gator_skin_grey", off=0.13, u0=0.0, u1=math.dist(wall_a, wall_b) / 1.0,
            v0=0.0, v1=5.3 / 1.0)
    for x0_ in (-412.95, -412.35, -411.75):
        R.panel(V, (x0_, -264.36), (x0_ + 0.52, -264.36), z + 0.2, z + 4.8, "int_ru_orange_uf", off=0.14)
        for zt_ in (z + 3.9, z + 4.15, z + 1.9, z + 2.15):          # white value captions (two per panel)
            R.panel(V, (x0_ + 0.07, -264.36), (x0_ + 0.45, -264.36), zt_, zt_ + 0.09, "int_ru_white", off=0.16)
    V.box(-413.6, -264.76, z, -413.0, -264.46, z + CLEAR["G"] - 0.02, "int_ru_wall_royal", faces="+x-x-y")
    K.col_box(C, -413.6, -264.76, z, -413.0, -264.46, z + CLEAR["G"], K.COL_NOCAM)
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
    # user-photo pass (B09): royal blue with orange ends, WELCOME TO THE REITZ UNION + the multilingual welcome,
    # lengthened to 5 % .. 60 % of the rail (about 10 m), two once-mapped halves side by side
    for (f0_, f1_), bm_ in (((0.05, 0.325), "int_ru_banner_welcome2"), ((0.325, 0.60), "int_ru_banner_welcome3")):
        ba = (ea[0] + (eb[0] - ea[0]) * f0_, ea[1] + (eb[1] - ea[1]) * f0_)
        bb = (ea[0] + (eb[0] - ea[0]) * f1_, ea[1] + (eb[1] - ea[1]) * f1_)
        R.panel(V, ba, bb, RZ.floors["L1"].z + 0.05, RZ.floors["L1"].z + 1.0, bm_, off=0.09)
    # 'SENATE CHAMBER' in grey dimensional letters on the white Senate wall west of the vestibule door (B09)
    R.panel(V, (-404.4, -264.36), (-401.4, -264.36), z + 2.55, z + 2.93, "int_ru_word_senate", off=0.115)
    # Swamp Boss gator head (plan object at (-397.3, -271.1)), under the stair landing; free library (plan)
    RZ.kit_add(R.gator_head(1.0), "G", tag="swamp_boss", x=-397.3, y=-271.1, facing=90.0)
    RZ.kit_add(R.free_library(4.6, 1.5), "G", tag="free_library", x=-386.1, y=-271.2, facing=270.0)
    # gator tracks: footprints along a winding steel strip from the South Terrace doors into the lounge
    # (on bare terrazzo: south of the second rug and its two lounge clusters; ru_floor_gator_tracks)
    base = [(-385.4, -285.4), (-388.6, -284.2), (-392.4, -283.4), (-394.0, -282.6), (-396.2, -280.4), (-399.5, -277.2)]
    _gator_tracks(V, base, z)
    orange_brew_front(V, P, z)
    cabo_front(V, C, z)
    RZ.kit_add(P, "G", tag="atrium_lounge")
    ob_cafe(RZ, z)
    RZ.points.setdefault("atrium", {})["lounge"] = {"name": "interior_atrium_lounge", "p": [-404.0, -271.0, 0.0],
                                                    "kind": "ground"}
    RZ.points["atrium"]["uf_letters_top"] = {"name": "interior_uf_letters_top", "p": [-411.33, -265.6, 2.6],
                                             "kind": "ground"}


def _gator_tracks(V, base, z, dz_line=0.002, dz_print=0.004):
    """Gator tracks (ru_floor_gator_tracks; user-photo pass B05, B06: three-claw prints): footprints alternating
    beside a thin polished S-curve strip along the base polyline. Decals dz above the floor."""
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
        V.poly([(pa[0] + ta[1] * hw, pa[1] - ta[0] * hw, z + dz_line), (pb[0] + tb[1] * hw, pb[1] - tb[0] * hw, z + dz_line),
                (pb[0] - tb[1] * hw, pb[1] + tb[0] * hw, z + dz_line), (pa[0] - ta[1] * hw, pa[1] + ta[0] * hw, z + dz_line)],
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
        # user-photo pass (B05, B06): a three-claw print (int_ru_gator_claw), 0.45 m along the walk x 0.25 m, toes ahead
        pts = []
        for (u, v) in ((-0.225, -0.125), (0.225, -0.125), (0.225, 0.125), (-0.225, 0.125)):
            pts.append((px + u * math.cos(ang) - v * math.sin(ang), py + u * math.sin(ang) + v * math.cos(ang), z + dz_print))
        V.poly(pts, "int_ru_gator_claw", uvs=[(0, 0), (0, 1), (1, 1), (1, 0)], normal_hint=(0, 0, 1))


# fix round 5 (fidelity-1, ru_atrium_enr_lounge right third): the lounge's south side (the slanted SW facade's inner
# face, (-396.93, -282.72) -> (-406.18, -291.77), facing the lounge) was a blank cream wall ~13 m long. The photo
# shows the Orange & Brew front there: a low white ledge, tall glazed bays with dark bronze mullions ~1.2 m apart, warm
# lit interiors with posters behind, a transom bar under the white wall / soffit. Visual only, on the wall's room side:
# panels 5 cm off the wall (no coplanar faces; 3 cm read as coplanar to the origin-offset z-fight scan on the slanted
# run), mullions / transom / ledge cap 6.5-21.5 cm off it (inside Mario's 24 cm foot wall radius: the wall's own
# collision is unchanged, nothing new to stand on or snag).
OB_FRONT = [((-396.93, -282.72), (-402.68, -288.06), 0.2, 0.2, 2),     # (a, b, inset at a, inset at b, door bay)
            ((-402.54, -287.92), (-406.18, -291.77), 0.4, 0.2, None)]


# fix iteration 6 (design improvement 3; ob_in_ne / ob_in_w / ob_from_lounge): the Orange & Brew zone (cafe_bar,
# 379 m2, open to the lounge and the lounge -> Game Room link) was a bare cream-and-terrazzo hall in front of its own
# storefront. No interior photo exists, so it is furnished from the house kit as the cafe's seating hall: high-top
# tables with stools along the storefront (skipping the glass door bay), two navy booths behind them, a service
# counter on the plan's own object at the south tip (object_6c0207; menu boards on the facade behind it, a coin line
# on its top and a 1-up behind it as a small find), and two score TVs on the west wall. A ~3 m route from the lounge
# (x -410, y -279.5) to the Game Room door (x -425, y -293.1) stays clear (OB_ROUTE, checked by the selftest).
OB_ROUTE = [(-410.0, -279.5), (-416.5, -292.5), (-425.3, -293.1)]
OB_SEAT_A, OB_SEAT_B = (-396.93, -282.72), (-406.18, -291.77)       # the storefront line (orange_brew_front)
OB_HIGHTOPS = [(0.9, 2.3), (5.6, 2.3), (8.3, 2.3), (11.0, 2.3)]      # (s along the front, offset into the hall)
OB_BOOTHS = [(6.9, 4.4), (10.1, 4.2)]
# iteration 7 (technical improvement 9): the front's west run sits 4 cm north of the plan line (y -296.76): at -296.80
# it lay in the plane of the O&B / Game Room partition's far face (vanilla push dragged a run along it into the
# counter body or through the partition)
OB_COUNTER = [(-413.29, -300.58), (-417.70, -296.76), (-420.64, -296.76)]   # front face line (hall side), plan object


def _ob_at(s_, o_):
    a, b = OB_SEAT_A, OB_SEAT_B
    L = math.dist(a, b)
    d = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
    n = (d[1], -d[0])                                   # right of a -> b: into the hall
    return (a[0] + d[0] * s_ + n[0] * o_, a[1] + d[1] * s_ + n[1] * o_)


def ob_cafe(RZ, z):
    F = RZ.floors["G"]
    HB = _built_wall_index(RZ)
    P = R._p("ob_cafe")
    V, C = P.visual, P.collision
    # high-top tables (1.05 m) with two bar stools each; one collision box per table (no camera collision)
    for k, (s_, o_) in enumerate(OB_HIGHTOPS):
        x, y = _ob_at(s_, o_)
        # a solid octagonal pedestal (r 0.3) under the round top: the collision box (+-0.3) stays within 12 cm of a
        # rendered face (a box round the thin-pole version read as an invisible wall to the QA scan)
        # iteration 7 (fidelity-1 improvement 6): the r 0.3 black pedestal read as a bin with a lid; a slim steel post
        # (r 0.13) on a dark foot disc (r 0.27, 3 cm), the collision box +-0.15 round the post (every point of it within
        # 9 cm of the post: no invisible wall; Mario's 50 u radius keeps him 0.65 m off the post, outside the top)
        R.cyl(V, x, y, 0.42, z + 1.0, z + 1.05, "int_ru_maple_panel", n=8, top=True, bottom=True)
        R.cyl(V, x, y, 0.13, z + 0.03, z + 1.0, "int_ru_steel", n=8, top=False, bottom=False)
        R.cyl(V, x, y, 0.27, z, z + 0.03, "int_ru_black", n=8, top=True, bottom=False)
        K.col_box(C, x - 0.15, y - 0.15, z, x + 0.15, y + 0.15, z + 1.05, K.COL_NOCAM)
        for j in (0, 1):
            a_ = math.radians(45.0 + 180.0 * j + 90.0 * (k % 2))
            sx, sy = x + 0.72 * math.cos(a_), y + 0.72 * math.sin(a_)
            R.cyl(V, sx, sy, 0.2, z + 0.7, z + 0.76, "int_ru_leather_orange", n=8, top=True, bottom=True)
            R.cyl(V, sx, sy, 0.03, z, z + 0.7, "int_ru_steel", n=6, top=False, bottom=False)
            R.cyl(V, sx, sy, 0.17, z + 0.26, z + 0.29, "int_ru_steel", n=8, top=True, bottom=True)
    # navy curved booths (the Game Room kit), their open side toward the storefront
    a, b = OB_SEAT_A, OB_SEAT_B
    face_ = (math.degrees(math.atan2(b[0] - a[0], b[1] - a[1])) + 90.0) % 360.0
    for k, (s_, o_) in enumerate(OB_BOOTHS):
        x, y = _ob_at(s_, o_)
        RZ.kit_add(R.booth(2.4), "G", tag=f"ob_booth_{k}", x=x, y=y, z=z, facing=face_)
    # service counter on the plan object (front + return), maple top; the staff side behind it stays open floor.
    # Two convex quads that share the mitred corner edge (no overlapping coplanar tops); the ends sit in the walls.
    D_, H_ = 0.78, 1.06
    f0, f1, f2 = OB_COUNTER
    us = []
    for pa_, pb_ in ((f0, f1), (f1, f2)):
        L_ = math.dist(pa_, pb_)
        us.append(((pb_[0] - pa_[0]) / L_, (pb_[1] - pa_[1]) / L_))
    nbk = [(-u_[1], u_[0]) for u_ in us]                 # left of the front line: into the object (staff side)
    b0 = (f0[0] + nbk[0][0] * D_, f0[1] + nbk[0][1] * D_)
    b2 = (f2[0] + nbk[1][0] * D_, f2[1] + nbk[1][1] * D_)
    # mitre: intersect the two back lines
    pa_, da_ = b0, us[0]
    pb_, db_ = b2, us[1]
    den = da_[0] * db_[1] - da_[1] * db_[0]
    t_m = ((pb_[0] - pa_[0]) * db_[1] - (pb_[1] - pa_[1]) * db_[0]) / den
    b1 = (pa_[0] + da_[0] * t_m, pa_[1] + da_[1] * t_m)
    for (fa_, fb_, ba_, bb_) in ((f0, f1, b0, b1), (f1, f2, b1, b2)):
        R.panel(V, fa_, fb_, z, z + 0.08, "int_ru_black")                        # kick
        R.panel(V, fa_, fb_, z + 0.08, z + H_ - 0.06, "int_ru_counter_navy")
        R.panel(V, fa_, fb_, z + H_ - 0.06, z + H_, "int_ru_maple_panel")
        R.panel(V, bb_, ba_, z, z + H_, "int_ru_counter_navy")
        V.poly([(fa_[0], fa_[1], z + H_), (fb_[0], fb_[1], z + H_), (bb_[0], bb_[1], z + H_), (ba_[0], ba_[1], z + H_)],
               "int_ru_maple_panel", normal_hint=(0, 0, 1))
        C.poly([(fa_[0], fa_[1], z + H_), (fb_[0], fb_[1], z + H_), (bb_[0], bb_[1], z + H_), (ba_[0], ba_[1], z + H_)],
               K.COL_NOCAM, normal_hint=(0, 0, 1))
        for (qa, qb) in ((fa_, fb_), (bb_, ba_)):
            nx_, ny_ = qb[1] - qa[1], -(qb[0] - qa[0])
            C.poly([(qa[0], qa[1], z), (qb[0], qb[1], z), (qb[0], qb[1], z + H_), (qa[0], qa[1], z + H_)], K.COL_NOCAM,
                   normal_hint=(nx_, ny_, 0))
    # menu boards on the facade behind the counter (5 cm proud of the built face), a back counter under them
    fa, fb = (-406.0, -291.8), (-416.1, -304.0)
    Lf = math.dist(fa, fb)
    d = ((fb[0] - fa[0]) / Lf, (fb[1] - fa[1]) / Lf)
    nr = (d[1], -d[0])
    for k, (s0, s1) in enumerate(((9.2, 10.4), (10.6, 11.8), (12.0, 13.2))):
        q = (fa[0] + d[0] * (s0 + s1) / 2, fa[1] + d[1] * (s0 + s1) / 2)
        t_ = _built_face_t(HB, q, nr, z + 1.7, z + 2.6)
        if t_ is None:
            continue
        p0 = (fa[0] + d[0] * s0, fa[1] + d[1] * s0)
        p1 = (fa[0] + d[0] * s1, fa[1] + d[1] * s1)
        R.panel(V, p0, p1, z + 1.75, z + 2.45, "int_ru_menu" if k != 1 else "int_ru_menu_blue", off=t_ + 0.05,
                glow=True)
    # 2 score TVs on the west wall (x -418.1, y -282.3 .. -290.0), facing the hall
    for k, yc in enumerate((-284.6, -288.0)):
        q = (-417.97, yc)                                   # in the face's own 1 m hash cell (x -418)
        t_ = _built_face_t(HB, q, (1.0, 0.0), z + 2.0, z + 2.8)
        if t_ is None:
            continue
        R.panel(V, (q[0], yc - 0.75), (q[0], yc + 0.75), z + 2.0, z + 2.85, "int_ru_score_tv", off=t_ + 0.05, glow=True)
        V.box(q[0] + t_ + 0.01, yc - 0.8, z + 1.96, q[0] + t_ + 0.03, yc + 0.8, z + 2.89, "int_ru_black",
              faces="+x+y-y+z-z")             # the bezel's face 2 cm behind the screen (no coplanar pair)
    # a stand-up bar ledge under the TVs along the same wall (1.05 m, maple top, navy front), 4 bar stools
    t_ = _built_face_t(HB, (-417.97, -285.9), (1.0, 0.0), z + 0.1, z + 1.0)
    if t_ is not None:
        xf = -417.97 + t_ + 0.01         # the face runs ~0.8 deg off the axis: the box is within +-5 cm of it
        y0_, y1_ = -289.4, -282.45
        V.box(xf, y0_, z, xf + 0.4, y1_, z + 1.0, "int_ru_counter_navy", faces="+x-y+y")
        V.box(xf, y0_ - 0.03, z + 1.0, xf + 0.45, y1_, z + 1.05, "int_ru_maple_panel", faces="+x-y+y+z-z")
        K.col_box(C, xf, y0_ - 0.03, z, xf + 0.45, y1_, z + 1.05, K.COL_NOCAM)
        for yy in (-283.6, -285.4, -287.2, -289.0):
            sx = xf + 0.95
            R.cyl(V, sx, yy, 0.2, z + 0.7, z + 0.76, "int_ru_leather_orange", n=8, top=True, bottom=True)
            R.cyl(V, sx, yy, 0.03, z, z + 0.7, "int_ru_steel", n=6, top=False, bottom=False)
            R.cyl(V, sx, yy, 0.17, z + 0.26, z + 0.29, "int_ru_steel", n=8, top=True, bottom=True)
    # iteration 7 (design improvement 4, ob_from_lounge / ob_in_w): the lounge half of the hall (its NE part, open
    # along y -277.8 to g_corridor_02 / the atrium) was bare terrazzo. Two more high-tops of the same kit (maple top,
    # steel post, orange stools set east-west, not into the walk) 1.6 m in from that open edge at x -401.5 / -405.5:
    # they mark the cafe's edge, stay >= 1.7 m off the walk from the lounge corner (-398, -279) SW to the Game Room
    # door, >= 3.4 m off OB_ROUTE's start (-410, -279.5) and >= 4 m off the storefront row. A coin on the far one
    # (a hop-up). A double-faced ORANGE & BREW sign hangs over the hall's NE corner (x -399; 2.9-3.62 m, over
    # Mario's head and 3 m north of the walk line; steel rods to the 5.4 m tile ceiling) for wayfinding from the
    # lounge (east face) and from the cafe (west face). Visual only apart from the two table boxes (NO_CAM).
    for k, x in enumerate((-401.5, -405.5)):
        y = -279.4
        R.cyl(V, x, y, 0.42, z + 1.0, z + 1.05, "int_ru_maple_panel", n=8, top=True, bottom=True)
        R.cyl(V, x, y, 0.13, z + 0.03, z + 1.0, "int_ru_steel", n=8, top=False, bottom=False)
        R.cyl(V, x, y, 0.27, z, z + 0.03, "int_ru_black", n=8, top=True, bottom=False)
        K.col_box(C, x - 0.15, y - 0.15, z, x + 0.15, y + 0.15, z + 1.05, K.COL_NOCAM)
        for sx_ in (-0.72, 0.72):
            R.cyl(V, x + sx_, y, 0.2, z + 0.7, z + 0.76, "int_ru_leather_orange", n=8, top=True, bottom=True)
            R.cyl(V, x + sx_, y, 0.03, z, z + 0.7, "int_ru_steel", n=6, top=False, bottom=False)
            R.cyl(V, x + sx_, y, 0.17, z + 0.26, z + 0.29, "int_ru_steel", n=8, top=True, bottom=True)
        if k == 1:
            EXTRA_PICKUPS.append({"kind": "coin", "name": "orange and brew north high-top coin", "pos": (x, y, z + 1.05)})
    xb, yb0, yb1 = -399.0, -279.8, -278.3
    # the sign's black edge frame (no +-x faces), the sign on both faces 0.5 cm outside it, two rods to the ceiling
    V.box(xb - 0.02, yb0 - 0.05, z + 2.85, xb + 0.02, yb1 + 0.05, z + 3.67, "int_ru_black", faces="+y-y+z-z")
    # user-photo pass (B10, B11): the cafe is CABO Mexican Grill (glowing orange letters on the black frame)
    R.panel(V, (xb, yb0), (xb, yb1), z + 3.08, z + 3.44, "int_ru_word_cabo", off=0.025, glow=True)
    R.panel(V, (xb, yb1), (xb, yb0), z + 3.08, z + 3.44, "int_ru_word_cabo", off=0.025, glow=True)
    for yr in (yb0 + 0.15, yb1 - 0.15):
        V.box(xb - 0.012, yr - 0.012, z + 3.67, xb + 0.012, yr + 0.012, z + CLEAR["G"], "int_ru_steel", faces="+x-x+y-y")
    for (s_, o_) in OB_HIGHTOPS[1:3]:
        x, y = _ob_at(s_, o_)
        P.lights.append(K.Light((x, y, z + 2.6), radius=3.0, strength=0.2, color=(1.0, 0.78, 0.5)))
    RZ.kit_add(P, "G", tag="ob_cafe")
    for k, t_ in enumerate((0.22, 0.5, 0.78)):                 # coins along the counter top (a hop-up)
        m_ = (f0[0] + (f1[0] - f0[0]) * t_ + nbk[0][0] * 0.39, f0[1] + (f1[1] - f0[1]) * t_ + nbk[0][1] * 0.39)
        EXTRA_PICKUPS.append({"kind": "coin", "name": f"orange and brew counter coin {k}", "pos": (m_[0], m_[1], z + H_)})
    EXTRA_PICKUPS.append({"kind": "1up", "name": "orange and brew behind the counter", "pos": (-417.4, -299.6, z)})


# user-photo pass (B10, B11, C17: the plan agrees): the CABO Mexican Grill window wall facing the lounge on
# the cafe zone's north line y -277.80 (it was left open; the Orange & Brew look on the slanted SW facade was
# inferred). A white knee wall, a honey-wood sill, clear glass with black mullions every 1.25 m and a transom at 3.0 m,
# a white bulkhead to the 5.4 m ceiling, big glowing orange CABO letters and MEXICAN GRILL in white on the glass, potted
# snake plants along the knee wall. Door: plan door 1 in the plan wall just west of it (x -410.9 .. -409.2, 1.7 m).
# Collision: a 0.2 m wall from x -408.4 to -396.8. The slanted facade's storefront stays as the cafe's inside back wall (re-branded CABO).
CABO_Y = -277.80
CABO_X = (-408.4, -396.8)       # the plan wall with door 1 (x -410.9 .. -409.2, honey-wood leaves) stands west of x -408.4


def cabo_front(V, C, z):
    y, (x0, x1) = CABO_Y, CABO_X
    for xa, xb in ((x0, x1),):
        V.box(xa, y - 0.1, z, xb, y + 0.1, z + 0.9, "int_ru_white", faces="+y-y")
        V.box(xa, y - 0.15, z + 0.9, xb, y + 0.15, z + 0.96, "int_ru_maple", faces="+y-y+z-z")
        R.quad_wall(V, (xa, y), (xb, y), z + 0.96, z + 3.0, "int_ru_glass")           # faces the cafe (-y)
        R.quad_wall(V, (xb, y), (xa, y), z + 0.96, z + 3.0, "int_ru_glass")           # faces the lounge (+y)
        n_ = max(1, int(round((xb - xa) / 1.25)))
        for k in range(n_ + 1):
            xm = min(max(xa + (xb - xa) * k / n_, xa + 0.03), xb - 0.03)
            V.box(xm - 0.03, y - 0.04, z + 0.96, xm + 0.03, y + 0.04, z + 3.0, "int_ru_black", faces="+x-x+y-y")
            if k < n_:       # white panel joints on the knee wall, 1 cm proud (lounge side)
                pass
        for xe in (xa, xb):
            pass
    # end faces of the knee wall + sill at the door jambs and the free east end
    for xe, sg in ((x1, 1),):
        R.quad_wall(V, (xe, y - 0.1 * sg), (xe, y + 0.1 * sg), z, z + 0.9, "int_ru_white", ao=0.9)
        R.quad_wall(V, (xe, y - 0.15 * sg), (xe, y + 0.15 * sg), z + 0.9, z + 0.96, "int_ru_maple")
    # transom bar over the whole run, white bulkhead to the ceiling
    V.box(x0, y - 0.06, z + 3.0, x1, y + 0.06, z + 3.08, "int_ru_black", faces="+y-y-z+x")
    V.box(x0, y - 0.1, z + 3.08, x1, y + 0.1, z + CLEAR["G"] - 0.02, "int_ru_white", faces="+y-y-z+x")
    # CABO letters (3.2 x 0.9 m) and MEXICAN GRILL (2.4 x 0.3 m) on the lounge side, 2 cm in front of the mullions
    R.panel(V, (-402.4, y), (-405.6, y), z + 1.5, z + 2.4, "int_ru_word_cabo", off=0.06, glow=True)
    R.panel(V, (-402.8, y), (-405.2, y), z + 1.15, z + 1.45, "int_ru_word_mexgrill", off=0.06, glow=True)
    # potted snake plants against the knee wall (visual: inside Mario's wall radius of the glass wall)
    for px in (-411.45, -403.5, -397.4):
        py = y + 0.33
        V.box(px - 0.2, py - 0.2, z, px + 0.2, py + 0.2, z + 0.45, "int_ru_wall_charcoal", faces="+x-x+y-y+z")
        for ang in (25.0, 115.0):
            a_ = math.radians(ang)
            ca, sa = math.cos(a_) * 0.3, math.sin(a_) * 0.3
            for sg in (1, -1):
                V.poly([(px - ca * sg, py - sa * sg, z + 0.45), (px + ca * sg, py + sa * sg, z + 0.45),
                        (px + ca * sg, py + sa * sg, z + 1.35), (px - ca * sg, py - sa * sg, z + 1.35)],
                       "int_ru_snake_plant", uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    # collision: the glazed wall east of the plan wall (floor to ceiling)
    R.col_seg(C, (x0, y), (x1, y), 0.1, z, z + CLEAR["G"], K.COL)


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
        # iteration 7 (fidelity-1 improvement 2; right third of ru_atrium_enr_lounge): the bays run up to a WHITE
        # BULKHEAD with a cove LED line on its lower edge (it was ~2.4 m of blank cream wall up to the 5.4 m tile
        # ceiling); the sign moves onto the bulkhead. Visual only (inside Mario's 50 u wall radius). Front face 31 cm off
        # the wall line, LED face 1 cm behind it, sign 1.5 cm proud of it, no face on another (z-fight rule)
        zb_, zt_ = z + 3.2, z + CLEAR["G"] - 0.02
        s0_, s1_ = -ia, L2 + ib                          # the whole run: the two bulkheads meet at the corner
        R.quad_wall(V, at(s0_, 0.31), at(s1_, 0.31), zb_, zt_, "int_ru_white", ao=0.95)
        R.quad_wall(V, at(s0_, 0.07), at(s0_, 0.31), zb_, zt_, "int_ru_white", ao=0.9)
        R.quad_wall(V, at(s1_, 0.31), at(s1_, 0.07), zb_, zt_, "int_ru_white", ao=0.9)
        V.poly([(*at(s0_, 0.07), zb_), (*at(s1_, 0.07), zb_), (*at(s1_, 0.31), zb_), (*at(s0_, 0.31), zb_)],
               "int_ru_white", normal_hint=(0, 0, -1), ao=0.85)
        R.panel(V, at(s0_ + 0.03, 0.0), at(s1_ - 0.03, 0.0), zb_ - 0.035, zb_, "int_ru_led", off=0.30, glow=True)
        V.poly([(*at(s0_ + 0.03, 0.27), zb_ - 0.035), (*at(s1_ - 0.03, 0.27), zb_ - 0.035),
                (*at(s1_ - 0.03, 0.30), zb_ - 0.035), (*at(s0_ + 0.03, 0.30), zb_ - 0.035)], "int_ru_led",
               normal_hint=(0, 0, -1), glow=True)
        if door is not None:
            c0 = (door + 0.5) * w
            R.panel(V, at(c0 - 1.6, 0.0), at(c0 + 1.6, 0.0), z + 3.65, z + 4.55, "int_ru_word_cabo", off=0.325,
                    glow=True)          # user-photo pass: re-branded CABO (B10, B11)
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
    # iteration 7 (fidelity-1 improvement 7; no photo, inferred): an orange UF band round the navy front and two staff
    # screens on the top (it read as a bare navy counter); the top now covers the whole counter (kit fix)
    RZ.kit_add(R.info_desk(3.12, d=0.7, front="int_ru_wall_navy", stripe="int_ru_orange_uf", monitors=2), "L1",
               tag="info_desk", x=-397.75, y=-261.0, z=z,
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


DRESSERS.extend([atrium_stairs, atrium_top, gators_tower, atrium_lounge, level1_extras, rail_plugs, east_end_offices])


# user-photo pass (B05, B06, C01, user_02): the L1 north lobby at the top of the atrium stairs and the
# orange accent wall behind the L2 stair heads. Four white rocking chairs in front of the north curtain wall (facing
# into the lobby), the navy three-claw gator tracks along a thin stainless S-curve from the north doors toward the
# stair head, and orange paint on the L2 back wall (2 cm off, door-subtracted). Collision: one low no-cam box under
# the rocking chairs (keeps 2.3 m to the vestibule doors).
ROCKERS = (-392.2, -390.6, -389.0, -387.4)
ROCKER_Y = -260.35
L1_TRACKS = [(-381.0, -262.0), (-384.6, -263.6), (-388.6, -264.4), (-392.4, -264.2), (-394.4, -264.6)]
ORANGE_WALLS = {}     # user-photo pass (C04): the L2 span x -403.5..-390.6 is the Student Engagement glass front;
                      # the orange is the curved corridor wall west of it (upper_userphoto_more)


def north_lobby(RZ):
    F = RZ.floors["L1"]
    z = F.z
    P = K.Prop("l1_north_lobby")
    V, C = P.visual, P.collision
    for i, x in enumerate(ROCKERS):
        RZ.kit_add(R.rocking_chair(), "L1", tag=f"rocking_chair_{i}", x=x, y=ROCKER_Y, z=z, facing=180.0)
    K.col_box(C, -392.6, -260.8, z, -387.0, -259.6, z + 0.45, K.COL_NOCAM)
    _gator_tracks(V, L1_TRACKS, z, dz_line=0.006, dz_print=0.012)
    RZ.kit_add(P, "L1", tag="l1_north_lobby")
    # C09: wood 'Student Body Presidents' plaques and two SG composites on the L3 south back wall under the BLUE word
    # (the straight run facing the void, face y -280.2, x -407.8 .. -402.0; 2 cm off, clear of plan doors)
    F3 = RZ.floors["L3"]
    P3 = K.Prop("sg_presidents_wall")
    wa, wb = (-402.0, -280.2), (-407.8, -280.2)          # a -> b: the right normal faces the void (+y)
    runs = _free_runs(F3, wa, wb)

    def _free(s0, s1):
        return any(r0 <= s0 and s1 <= r1 for r0, r1 in runs)
    for k in range(8):
        s0 = 0.82 + k * 0.54
        if _free(s0, s0 + 0.42):
            pa_, pb_ = _sub(wa, wb, s0, s0 + 0.42)
            R.panel(P3.visual, pa_, pb_, F3.z + 1.2, F3.z + 1.8, "int_ru_wood_panel", off=0.02)
            R.panel(P3.visual, _sub(wa, wb, s0 + 0.08, s0 + 0.34)[0], _sub(wa, wb, s0 + 0.08, s0 + 0.34)[1],
                    F3.z + 1.62, F3.z + 1.7, "int_ru_steel_bright", off=0.05)
    for s0 in (0.6, 4.1):
        if _free(s0, s0 + 1.1):
            pa_, pb_ = _sub(wa, wb, s0, s0 + 1.1)
            R.panel(P3.visual, pa_, pb_, F3.z + 2.0, F3.z + 2.75, "int_ru_photos", off=0.02)
    RZ.kit_add(P3, "L3", tag="sg_presidents_wall")
    for fid, segs in ORANGE_WALLS.items():
        Fw = RZ.floors[fid]
        Pw = K.Prop(f"orange_wall_{fid}")
        for a, b in segs:
            _wall_strip_d(Fw, Pw.visual, a, b, Fw.z + 0.1, Fw.z + CLEAR[fid], "int_ru_orange", off=0.02)
        RZ.kit_add(Pw, fid, tag=f"orange_wall_{fid}")


DRESSERS.extend([north_lobby])


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
    # iteration 6 (technical improvement 2c): notched round the door's terrazzo threshold strip (x -425.35..-424.65,
    # y -294.0..-292.2), which it overlapped coplanar (0.3 m2 z-fight)
    for carpet2 in ([(-440.6, -297.2), (-425.35, -297.2), (-425.35, -290.0), (-440.6, -290.0)],
                    [(-425.35, -297.2), (-425.1, -297.2), (-425.1, -294.0), (-425.35, -294.0)],
                    [(-425.35, -292.2), (-425.1, -292.2), (-425.1, -290.0), (-425.35, -290.0)]):
        R.floor_poly(V, R.ccw(carpet2), z, "int_ru_carpet_billiards", step=4.5)
    k = 0
    # (fix round 2: shifted 1 m east, the arcade + esports bar stand along the storefront west of them)
    for ty, xs in ((-285.3, (-455.0, -450.3, -445.6, -440.9)), (-290.8, (-455.0, -450.3, -445.6)),
                   (-295.0, (-455.0, -450.3, -445.6))):
        for tx in xs:
            if k >= 9:
                break
            # user-photo pass (B20): one table has a white painted base
            RZ.kit_add(R.billiard_table(base="int_ru_white" if k == 3 else "int_ru_espresso"), "G", tag=f"pool_{k}",
                       x=tx, y=ty, facing=0.0)
            if k in (0, 5, 8):          # design pass: a coin on three of the tables' felt (jump up)
                EXTRA_PICKUPS.append({"kind": "coin", "name": f"billiards table {k} coin", "pos": (tx, ty, z + 0.79)})
            # photo pass round 2 (design 6; user_04, B20): the ring frames are the room's dominant ceiling feature:
            # 0.2 m bars, 0.1 m deep, a stronger light (they read as thin white lines at the gameplay camera)
            RZ.kit_add(R.led_frame(3.9, 2.5, z + 3.5, t=0.2, h=0.1, strength=0.42), "G", tag=f"pool_led_{k}", x=tx,
                       y=ty, facing=0.0)
            k += 1
    RZ.kit_add(R.billiard_table(3.57, 1.78), "G", tag="snooker", x=-437.2, y=-294.6, facing=0.0)
    RZ.kit_add(R.led_frame(4.4, 2.8, z + 3.5, t=0.2, h=0.1, strength=0.42), "G", tag="snooker_led", x=-437.2, y=-294.6,
               facing=0.0)
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
        # user-photo pass (B15): Gamepod Classic cabinets (black, rainbow side band, blue screens)
        RZ.kit_add(R.arcade_cabinet("int_ru_arcade_gamepod", (0.55, 0.75, 1.0)), "G", tag=f"arcade_{i}", x=xs_ + 0.5,
                   y=-283.6 - i * 0.95, facing=90.0)
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
    # user-photo pass (user_01, B15, B18): the long white GATOR ESPORTS CENTER letters on a black band over the
    # glass, and above them a continuous glowing blue LED gator-scale frieze (it replaces the row of 9 TVs), on both
    # faces of the storefront (plan line (-459.5, -309.1) -> (-459.3, -282.1): faces at +-0.1 of it)
    def _sfx(y_):
        return -459.5 + 0.2 * (y_ + 309.1) / 27.0
    R.panel(V, (_sfx(-298.6) + 0.1, -298.6), (_sfx(-289.2) + 0.1, -289.2), z + 2.98, z + 3.52, "int_ru_black",
            off=0.08)
    _esports_sign(V, (_sfx(-298.4) + 0.1, -298.4), (_sfx(-289.4) + 0.1, -289.4), z + 3.04, z + 3.46, off=0.1)
    nq_ = 9
    for q_ in range(nq_):
        ya_ = -308.8 + (26.4 * q_) / nq_
        yb_ = -308.8 + (26.4 * (q_ + 1)) / nq_
        R.panel(V, (_sfx(ya_) + 0.1, ya_), (_sfx(yb_) + 0.1, yb_), z + 3.55, z + 4.55, "int_ru_scale_led", off=0.1,
                glow=True, u0=(ya_ + 308.8) / 2.0, u1=(yb_ + 308.8) / 2.0)
    for q_ in range(nq_):
        ya_ = -282.4 - (26.0 * q_) / nq_
        yb_ = -282.4 - (26.0 * (q_ + 1)) / nq_
        R.panel(V, (_sfx(ya_) - 0.1, ya_), (_sfx(yb_) - 0.1, yb_), z + 3.55, z + 4.55, "int_ru_scale_led", off=0.04,
                glow=True, u0=(282.4 + ya_) / -2.0, u1=(282.4 + yb_) / -2.0)
    P.lights.append(K.Light((-457.5, -292.0, z + 4.0), radius=7.0, strength=0.3, color=(0.45, 0.5, 1.0)))
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
    # (user-photo pass, user_01: the three ottomans here gave way to the racing-sim bay, g_userphoto_ground())
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
    # photo pass round 2 (fidelity-ground 4; B18 looks south: the west side is a continuous run of stations under a
    # long black band with big white GATOR ESPORTS CENTER letters): a second 6-seat row north of the first (plan
    # wall (-465.8, -277.0) -> (-466.1, -309.0)), the band 0.18 / 0.2 m off the plan line (in front of the hex neon)
    def _ewx(y_):
        return -465.8 + 0.3 * (y_ + 277.0) / 32.0
    RZ.kit_add(R.esports_row(6, double=False), "G", tag="es_row_west_n", x=_ewx(-288.6), y=-288.6, facing=90.0)
    R.panel(V, (_ewx(-296.9), -296.9), (_ewx(-287.3), -287.3), z + 2.96, z + 3.58, "int_ru_black", off=0.18)
    _esports_sign(V, (_ewx(-296.7), -296.7), (_ewx(-287.5), -287.5), z + 3.03, z + 3.51, off=0.2)
    # B19: the arena end glows orange / red as well as blue
    for oy_ in (-306.0, -301.0):
        P.lights.append(K.Light((-462.6, oy_, z + 1.4), radius=5.0, strength=0.22, color=(1.0, 0.5, 0.18)))
    # user-photo pass (B18): grey / navy leather ottomans along the walkway (the red bench), one collision block
    for k_ in range(8):
        oy_ = -284.8 - k_ * 1.4
        V.box(-460.1, oy_ - 0.25, z, -459.6, oy_ + 0.25, z + 0.42,
              "int_ru_leather_grey" if k_ % 2 == 0 else "int_ru_leather_navy", faces="+x-x+y-y+z")
    K.col_box(C, -460.1, -296.0, z, -459.5, -284.0, z + 0.45, K.COL_NOCAM)
    # co-op screens at the north end (ru_es_oelrich_9003) with two gaming pods under clear dome canopies facing
    # them (B18, B19): a black recliner, a clear hemisphere, a blue LED strip on the base; one block each
    for i, yy in enumerate((-280.0, -283.0)):
        R.panel(V, (-465.6, yy - 0.9), (-465.6, yy + 0.9), z + 1.1, z + 2.1, "int_ru_game_screen", off=0.1, glow=True)
        cx_ = -463.1
        V.box(cx_ - 0.6, yy - 0.42, z, cx_ + 0.6, yy + 0.42, z + 0.12, "int_ru_black", faces="+x-x+y-y+z")
        V.box(cx_ - 0.6, yy - 0.43, z + 0.04, cx_ + 0.6, yy + 0.43, z + 0.08, "int_ru_led", faces="+y-y", glow=True,
              tint=(0.3, 0.45, 1.0))
        V.box(cx_ - 0.45, yy - 0.35, z + 0.12, cx_ + 0.25, yy + 0.35, z + 0.5, "int_ru_leather_char",
              faces="+x-x+y-y+z")
        V.poly([(cx_ + 0.25, yy - 0.35, z + 0.5), (cx_ + 0.25, yy + 0.35, z + 0.5), (cx_ + 0.48, yy + 0.35, z + 1.0),
                (cx_ + 0.48, yy - 0.35, z + 1.0)], "int_ru_leather_char", normal_hint=(-1, 0, 0.5))
        V.poly([(cx_ + 0.27, yy - 0.35, z + 0.12), (cx_ + 0.5, yy - 0.35, z + 0.99), (cx_ + 0.5, yy + 0.35, z + 0.99),
                (cx_ + 0.27, yy + 0.35, z + 0.12)], "int_ru_black", normal_hint=(1, 0, 0))
        rings_ = [(0.75, z + 0.55), (0.65, z + 0.93), (0.38, z + 1.2), (0.05, z + 1.3)]
        for (ra, za), (rb, zb) in zip(rings_, rings_[1:]):
            for k in range(8):
                a0_, a1_ = 2 * math.pi * k / 8, 2 * math.pi * (k + 1) / 8
                V.poly([(cx_ + ra * math.cos(a0_), yy + ra * math.sin(a0_), za),
                        (cx_ + ra * math.cos(a1_), yy + ra * math.sin(a1_), za),
                        (cx_ + rb * math.cos(a1_), yy + rb * math.sin(a1_), zb),
                        (cx_ + rb * math.cos(a0_), yy + rb * math.sin(a0_), zb)], "int_ru_glass_clear",
                       normal_hint=(math.cos((a0_ + a1_) / 2), math.sin((a0_ + a1_) / 2), 0.4))
        K.col_box(C, cx_ - 0.75, yy - 0.75, z, cx_ + 0.75, yy + 0.75, z + 1.3, K.COL_NOCAM)
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
        # user-photo pass (B18, B19): the storefront-side clusters gave way to the LED scale frieze (game_room());
        # the west-wall clusters glow electric blue, orange south of y -296 (the arena end)
        if k % 2 == 1:
            R.panel(V, (-465.85, yy - 1.2), (-465.85, yy + 1.2), z + 2.0, z + 3.8, "int_ru_hex_neon", off=0.02, glow=True,
                    tint=(1.0, 0.5, 0.15) if yy < -296 else (0.3, 0.35, 1.0))
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
                        (dx_ + ra * math.cos(a0_), dy_ + ra * math.sin(a0_), za)], "int_ru_glass_clear")
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


# ---------------------------------------------------------------- user-photo pass: Ground rooms and corridors
def _seg_pt(a, b, s):
    L = math.dist(a, b)
    return (a[0] + (b[0] - a[0]) * s / L, a[1] + (b[1] - a[1]) * s / L)


def _bay_front(F, V, a, b, z0, z1, mat, bay=1.2, off=0.115, mull="int_ru_steel", s_lo=0.0, s_hi=None):
    """A glazed storefront decal on the plan wall line a -> b (facing right of it; off from the line, so 0.115 is
    1.5 cm proud of a partition face): the plan doors on the line cut out (DOOR_CLEAR off each jamb), each free run
    split into ~bay panels of the once-mapped bay texture under a glass sheen layer, mullions at the bay joints."""
    L = math.dist(a, b)
    nx, ny = (b[1] - a[1]) / L, -(b[0] - a[0]) / L
    s_hi = L if s_hi is None else s_hi
    for r0, r1 in _free_runs(F, a, b, s_lo=s_lo, s_hi=s_hi, min_len=0.3):
        n = max(1, int(round((r1 - r0) / bay)))
        for k in range(n):
            p0, p1 = _seg_pt(a, b, r0 + (r1 - r0) * k / n), _seg_pt(a, b, r0 + (r1 - r0) * (k + 1) / n)
            R.panel(V, p0, p1, z0, z1, mat, off=off)
            R.panel(V, p0, p1, z0, z1, "int_ru_glass", off=off + 0.012)
        for k in range(n + 1):
            p = _seg_pt(a, b, r0 + (r1 - r0) * k / n)
            c = (p[0] + nx * (off + 0.03), p[1] + ny * (off + 0.03))
            V.box(c[0] - 0.03, c[1] - 0.03, z0, c[0] + 0.03, c[1] + 0.03, z1, mull, faces="+x-x+y-y")


def _pin_pull(V, x, y, z):
    """A bowling-pin door pull (B16): white 6-gon body, neck with a red ring, head."""
    R.cyl(V, x, y, 0.035, z + 0.86, z + 0.90, "int_ru_white", n=6, top=False)
    R.cyl(V, x, y, 0.05, z + 0.90, z + 1.12, "int_ru_white", n=6, top=False)
    R.cyl(V, x, y, 0.028, z + 1.12, z + 1.19, "int_ru_white", n=6, top=False)
    R.cyl(V, x, y, 0.031, z + 1.13, z + 1.16, "int_ru_red", n=6, top=False)
    R.cyl(V, x, y, 0.038, z + 1.19, z + 1.30, "int_ru_white", n=6, top=True)


def g_userphoto_ground(RZ):
    """User-photo pass (the user's own photos user_01, user_03, user_04, B12-B20): the Ground floor's
    missing identity pieces: the Game Room's glass entrance (bowling-pin pulls, GAME ROOM transom), the barbershop
    storefront + pole + striped sign, the royal-blue door niche, the orange-elevator corridor package (LED coves,
    B&W photo frieze, royal G directory, TV, round lights), the SUBWAY portal + glazed side wall, the billiards'
    black columns with TVs, the racing-sim bay with its partition, the ARENA line."""
    F = RZ.floors["G"]
    z = F.z
    P = K.Prop("g_userphoto_ground")
    V, C = P.visual, P.collision
    # -- Game Room entrance (B16): glass leaves held open into the Game Room, steel stiles, bowling-pin pulls,
    #    a glass transom with GAME ROOM cut-out letters on both faces
    for xl_ in (-446.5, -445.0):
        y0_, y1_ = -281.56, -282.40
        R.panel(V, (xl_, y0_), (xl_, y1_), z + 0.02, z + 2.45, "int_ru_glass_clear", off=0.0)
        R.panel(V, (xl_, y1_), (xl_, y0_), z + 0.02, z + 2.45, "int_ru_glass_clear", off=0.0)
        V.box(xl_ - 0.02, y1_, z, xl_ + 0.02, y1_ + 0.05, z + 2.45, "int_ru_steel", faces="+x-x+y-y+z")
        V.box(xl_ - 0.02, y0_ - 0.05, z, xl_ + 0.02, y0_, z + 2.45, "int_ru_steel", faces="+x-x-y+z")
        V.box(xl_ - 0.02, y1_ + 0.05, z + 2.38, xl_ + 0.02, y0_ - 0.05, z + 2.45, "int_ru_steel", faces="+x-x+z-z")
        V.box(xl_ - 0.02, y1_ + 0.05, z, xl_ + 0.02, y0_ - 0.05, z + 0.12, "int_ru_steel", faces="+x-x+z")
        for sx_ in (-1, 1):
            px_ = xl_ + sx_ * 0.07
            _pin_pull(V, px_, -282.2, z)
            for zz_ in (z + 0.98, z + 1.22):
                V.box(min(xl_, px_), -282.21, zz_, max(xl_, px_), -282.19, zz_ + 0.02, "int_ru_steel",
                      faces="+y-y+z-z")
    R.panel(V, (-446.6, -281.4), (-444.9, -281.4), z + 2.45, z + 3.0, "int_ru_glass_clear", off=0.004)
    R.panel(V, (-444.9, -281.4), (-446.6, -281.4), z + 2.45, z + 3.0, "int_ru_glass_clear", off=0.004)
    R.panel(V, (-445.05, -281.4), (-446.45, -281.4), z + 2.56, z + 2.9, "int_ru_sign_gr_transom", off=0.02, glow=True)
    R.panel(V, (-446.45, -281.4), (-445.05, -281.4), z + 2.56, z + 2.9, "int_ru_sign_gr_transom", off=0.02, glow=True)
    V.box(-446.6, -281.43, z + 2.42, -444.9, -281.37, z + 2.47, "int_ru_steel", faces="+y-y-z+z")
    # photo pass round 2 (fidelity-ground 8; B16): the portrait GAME ROOM HOURS screen on the cream corridor wall
    # right (west) of the doors: a black bezel 1.5 cm proud of the face (y -281.3), the screen 2 cm in front of it
    V.box(-447.86, -281.30, z + 1.11, -447.24, -281.285, z + 2.19, "int_ru_black", faces="+y+x-x+z-z")
    R.panel(V, (-447.28, -281.4), (-447.82, -281.4), z + 1.15, z + 2.15, "int_ru_hours_screen", off=0.135, glow=True)
    # -- barbershop (B12, B14): glazed aluminium storefront on the corridor face, striped sign, lit barber pole
    ba, bb = (-432.3, -277.5), (-437.3, -277.4)             # plan wall; right of a -> b = +y (the corridor)
    _bay_front(F, V, ba, bb, z + 0.15, z + 2.8, "int_ru_office_bay", bay=1.2, off=0.115)
    R.seg_box(V, (ba[0] + 0.003, ba[1] + 0.145), (bb[0] - 0.003, bb[1] + 0.145), 0.03, z + 2.8, z + 2.88, "int_ru_steel",
              faces="sidetop")
    # photo pass round 2 (fidelity-ground 3; B14 looks west: pole, door, glazing, then the sign): the lit pole stands
    # at the storefront's EAST end (plan wall y -277.5 there: face ~-277.4), the striped BARBERSHOP sign is a
    # double-faced blade projecting 0.9 m into the corridor just west of the storefront (visual, z 2.45+ overhead)
    px_, py_ = -431.95, -277.25
    for k in range(8):
        a0_, a1_ = 2 * math.pi * k / 8, 2 * math.pi * (k + 1) / 8
        V.poly([(px_ + 0.09 * math.cos(a0_), py_ + 0.09 * math.sin(a0_), z + 1.75),
                (px_ + 0.09 * math.cos(a1_), py_ + 0.09 * math.sin(a1_), z + 1.75),
                (px_ + 0.09 * math.cos(a1_), py_ + 0.09 * math.sin(a1_), z + 2.55),
                (px_ + 0.09 * math.cos(a0_), py_ + 0.09 * math.sin(a0_), z + 2.55)], "int_ru_barber_pole",
               uvs=[(k / 8, 0.0), ((k + 1) / 8, 0.0), ((k + 1) / 8, 1.0), (k / 8, 1.0)], glow=True,
               normal_hint=(math.cos((a0_ + a1_) / 2), math.sin((a0_ + a1_) / 2), 0.0))
    R.cyl(V, px_, py_, 0.11, z + 1.68, z + 1.75, "int_ru_steel_bright", n=8, top=False, bottom=True)
    R.cyl(V, px_, py_, 0.11, z + 2.55, z + 2.65, "int_ru_steel_bright", n=8, top=True)
    V.box(px_ - 0.04, py_ - 0.15, z + 2.0, px_ + 0.04, py_ - 0.09, z + 2.3, "int_ru_steel", faces="+x-x+z-z-y")
    bx_, by0_, by1_ = -437.7, -277.28, -276.38
    V.box(bx_ - 0.03, by0_, z + 2.42, bx_ + 0.03, by1_ + 0.03, z + 2.45, "int_ru_steel", faces="+x-x+y-z+z")
    V.box(bx_ - 0.03, by0_, z + 2.92, bx_ + 0.03, by1_ + 0.03, z + 2.95, "int_ru_steel", faces="+x-x+y-z+z")
    V.box(bx_ - 0.012, by1_, z + 2.45, bx_ + 0.012, by1_ + 0.03, z + 2.92, "int_ru_steel", faces="+y")
    R.panel(V, (bx_ + 0.012, by0_), (bx_ + 0.012, by1_), z + 2.45, z + 2.92, "int_ru_sign_barber_blade", off=0.0)
    R.panel(V, (bx_ - 0.012, by1_), (bx_ - 0.012, by0_), z + 2.45, z + 2.92, "int_ru_sign_barber_blade", off=0.0)
    # -- royal-blue door niche (B12): jambs + header round the closed door x -442.5..-441.6 (corridor face y -277.3)
    for (xa_, xb_, za_, zb_) in ((-442.85, -442.52, 0.0, 2.8), (-441.58, -441.25, 0.0, 2.8), (-442.52, -441.58, 2.42, 2.8)):
        R.panel(V, (xb_, -277.3), (xa_, -277.3), z + za_ + (0.1 if za_ == 0.0 else 0.0), z + zb_, "int_ru_wall_royal",
                off=0.015)
    # -- orange-elevator corridor (B13): warm LED coves high on both walls, B&W photo frieze, royal G directory, TV,
    #    round surface lights in the soffit
    west = [((-421.3, -274.9), (-421.2, -266.7)), ((-421.2, -263.9), (-421.1, -254.3)), ((-421.1, -254.3), (-421.1, -249.8))]
    # (the east wall's elevator bank, y -273.4..-268.1, keeps its floor-number panels clear: no frieze / cove there)
    east = [((-418.2, -266.8), (-418.2, -268.1)), ((-418.3, -273.4), (-418.3, -274.9)),
            ((-418.1, -244.6), (-418.3, -259.8)), ((-418.3, -259.8), (-418.3, -263.1))]
    for a_, b_ in west + east:
        L_ = math.dist(a_, b_)
        a2, b2 = _seg_pt(a_, b_, 0.05), _seg_pt(a_, b_, L_ - 0.05)
        _wall_strip(V, a2, b2, z + 3.05, z + 3.6, "int_ru_photo_bw", off=0.115)
        nx_, ny_ = (b_[1] - a_[1]) / L_, -(b_[0] - a_[0]) / L_
        R.seg_box(V, (a2[0] + nx_ * 0.13, a2[1] + ny_ * 0.13), (b2[0] + nx_ * 0.13, b2[1] + ny_ * 0.13), 0.03,
                  z + 3.72, z + 3.77, "int_ru_white", faces="sidetop")
        V.poly([(a2[0] + nx_ * 0.1, a2[1] + ny_ * 0.1, z + 3.72), (b2[0] + nx_ * 0.1, b2[1] + ny_ * 0.1, z + 3.72),
                (b2[0] + nx_ * 0.16, b2[1] + ny_ * 0.16, z + 3.72), (a2[0] + nx_ * 0.16, a2[1] + ny_ * 0.16, z + 3.72)],
               "int_ru_led", glow=True, tint=(1.0, 0.93, 0.8), normal_hint=(0, 0, -1))
    def _wx(y_):
        return -421.3 + 0.1 * (y_ + 274.9) / 8.2
    # photo pass round 2 (fidelity-ground 2b; B13): the royal G directory is on the EAST wall, just north of the
    # elevator bank (plan wall x -418.2, y -268.1..-266.8; the bank's floor-number panels stay clear)
    R.panel(V, (-418.2, -267.05), (-418.2, -267.95), z + 1.0, z + 2.6, "int_ru_dir_G", off=0.12, glow=True)
    V.box(_wx(-268.6) + 0.1, -268.6, z + 1.72, _wx(-268.6) + 0.16, -267.4, z + 2.48, "int_ru_black", faces="+x+y-y+z-z")
    R.panel(V, (_wx(-268.55) + 0.172, -268.55), (_wx(-267.45) + 0.172, -267.45), z + 1.76, z + 2.44,
            "int_ru_game_screen", off=0.0, glow=True)
    zs = z + GN_SOFFIT
    for yy in (-246.6, -250.2, -253.8, -257.4, -261.0):
        R.cyl(V, -419.75, yy, 0.24, zs - 0.05, zs, "int_ru_white", n=8, top=False, bottom=False)
        V.poly([(-419.75 + 0.22 * math.cos(2 * math.pi * k / 8), yy + 0.22 * math.sin(2 * math.pi * k / 8), zs - 0.052)
                for k in reversed(range(8))], "int_ru_led", glow=True, tint=(1.0, 0.96, 0.88), normal_hint=(0, 0, -1))
    P.lights.append(K.Light((-419.75, -272.0, z + 3.5), radius=5.0, strength=0.22, color=LIGHT_WARM))
    # white surrounds round the two orange-elevator doors (B13), outside their steel frames, 2 cm proud
    for xf_, yn_, ys_ in ((-418.4, -271.7, -272.6), (-418.348, -269.0, -269.8)):
        for y0_, y1_ in ((yn_ + 0.18, yn_ + 0.06), (ys_ - 0.06, ys_ - 0.18)):
            R.panel(V, (xf_, y0_), (xf_, y1_), z + 0.1, z + 2.55, "int_ru_white", off=0.02)
        R.panel(V, (xf_, yn_ + 0.18), (xf_, ys_ - 0.18), z + 2.42, z + 2.55, "int_ru_white", off=0.02)
    # -- SUBWAY (user_03): green portal + SUBWAY letters on the SE chamfer, a green-framed glazed side wall
    sa, sb = (-449.4, -262.5), (-447.4, -261.0)
    Ls = math.dist(sa, sb)
    for s0_, s1_ in ((0.0, 0.35), (Ls - 0.35, Ls)):
        R.panel(V, _seg_pt(sa, sb, s0_), _seg_pt(sa, sb, s1_), z + 0.0, z + 3.0, "int_ru_subway_green", off=0.13)
    R.panel(V, sa, sb, z + 3.0, z + 3.9, "int_ru_subway_green", off=0.13)
    R.panel(V, _seg_pt(sa, sb, 0.12), _seg_pt(sa, sb, Ls - 0.12), z + 3.2, z + 3.75, "int_ru_sign_subway", off=0.15,
            glow=True)
    _bay_front(F, V, sa, sb, z + 0.0, z + 3.0, "int_ru_cafe_bay", bay=0.6, off=0.115, mull="int_ru_subway_green",
               s_lo=0.35, s_hi=Ls - 0.35)
    wa, wb = (-447.4, -261.0), (-447.2, -245.9)
    _bay_front(F, V, wa, wb, z + 0.6, z + 2.9, "int_ru_cafe_bay", bay=1.5, off=0.115, mull="int_ru_subway_green")
    for r0, r1 in _free_runs(F, wa, wb, min_len=0.3):
        R.panel(V, _seg_pt(wa, wb, r0), _seg_pt(wa, wb, r1), z + 0.1, z + 0.6, "int_ru_subway_green", off=0.115)
        R.panel(V, _seg_pt(wa, wb, r0), _seg_pt(wa, wb, r1), z + 2.9, z + 3.05, "int_ru_subway_green", off=0.115)
    # -- billiards (user_04, B20): black square columns with portrait TVs, landscape TVs on the north wall
    for cx_ in (-452.65, -443.25):
        cy_ = -288.05
        V.box(cx_ - 0.3, cy_ - 0.3, z, cx_ + 0.3, cy_ + 0.3, z + CLEAR["G"], "int_ru_black", faces="+x-x+y-y")
        K.col_box(C, cx_ - 0.3, cy_ - 0.3, z, cx_ + 0.3, cy_ + 0.3, z + CLEAR["G"], K.COL_NOCAM)
        R.panel(V, (cx_ + 0.25, cy_ + 0.3), (cx_ - 0.25, cy_ + 0.3), z + 1.8, z + 2.7, "int_ru_game_screen", off=0.02,
                glow=True)
        R.panel(V, (cx_ - 0.25, cy_ - 0.3), (cx_ + 0.25, cy_ - 0.3), z + 1.8, z + 2.7, "int_ru_game_screen", off=0.02,
                glow=True)
    for tx_ in (-457.6, -450.0, -441.5):
        yw_ = -282.2 if tx_ > -448.0 else -282.2 - 0.1 * (tx_ + 448.0) / 11.3
        V.box(tx_ - 0.68, yw_ - 0.16, z + 2.47, tx_ + 0.68, yw_ - 0.1, z + 3.28, "int_ru_black", faces="-y+x-x+z-z")
        R.panel(V, (tx_ - 0.65, yw_ - 0.16), (tx_ + 0.65, yw_ - 0.16), z + 2.5, z + 3.25, "int_ru_game_screen",
                off=0.012, glow=True)
    # -- racing-sim bay (user_01): three rigs facing west in the plank strip, a low black partition with a blue LED
    #    hex band (north face) and a steel top rail; one collision block for the bay
    for ry_ in (-298.45, -299.3, -300.15):
        V.box(-459.05, ry_ - 0.33, z, -457.35, ry_ + 0.33, z + 0.1, "int_ru_black", faces="+x-x+y-y+z")
        V.box(-457.95, ry_ - 0.24, z + 0.1, -457.4, ry_ + 0.24, z + 0.42, "int_ru_leather_grey", faces="+x-x+y-y+z")
        V.poly([(-457.55, ry_ - 0.24, z + 0.42), (-457.55, ry_ + 0.24, z + 0.42), (-457.38, ry_ + 0.24, z + 1.15),
                (-457.38, ry_ - 0.24, z + 1.15)], "int_ru_leather_grey", normal_hint=(-1, 0, 0.3))
        V.poly([(-457.33, ry_ - 0.24, z + 0.42), (-457.33, ry_ + 0.24, z + 0.42), (-457.2, ry_ + 0.24, z + 1.15),
                (-457.2, ry_ - 0.24, z + 1.15)], "int_ru_black", normal_hint=(1, 0, -0.2))
        V.box(-458.6, ry_ - 0.03, z + 0.1, -458.5, ry_ + 0.03, z + 0.82, "int_ru_black", faces="+x-x+y-y")
        R.cyl(V, -458.62, ry_, 0.16, z + 0.8, z + 0.84, "int_ru_black", n=6, top=True, bottom=True)
        R.panel(V, (-458.95, ry_ - 0.3), (-458.95, ry_ + 0.3), z + 0.85, z + 1.17, "int_ru_game_screen", off=0.0,
                glow=True)
        V.box(-459.02, ry_ - 0.3, z + 0.82, -458.97, ry_ + 0.3, z + 1.2, "int_ru_black", faces="-x+z-z+y-y")
    R.seg_box(V, (-459.2, -300.76), (-456.7, -300.76), 0.06, z, z + 1.15, "int_ru_black")
    R.panel(V, (-456.75, -300.70), (-459.15, -300.70), z + 0.7, z + 1.1, "int_ru_hex_neon", off=0.01, glow=True,
            tint=(0.3, 0.35, 1.0))
    R.seg_box(V, (-459.2, -300.76), (-456.7, -300.76), 0.035, z + 1.15, z + 1.19, "int_ru_steel_bright",
              faces="sidetop")
    K.col_box(C, -459.2, -300.82, z, -456.7, -298.05, z + 1.15, K.COL_NOCAM)
    # -- Market / NOSH SPOT (user_03): a glazed cooler front on the SW chamfer and the west face, a black fascia with
    #    NOSH SPOT, a round navy MARKET blade projecting from the chamfer's north end
    ma, mb = (-442.8, -260.6), (-440.8, -262.6)            # right of a -> b = SW, the corridor head
    Lm = math.dist(ma, mb)
    _bay_front(F, V, ma, mb, z + 0.0, z + 3.0, "int_ru_cafe_bay", bay=0.7, off=0.115, mull="int_ru_black")
    R.panel(V, ma, mb, z + 3.0, z + 3.6, "int_ru_black", off=0.13)
    R.panel(V, _seg_pt(ma, mb, 0.2), _seg_pt(ma, mb, Lm - 0.2), z + 3.08, z + 3.52, "int_ru_sign_nosh", off=0.15,
            glow=True)
    va_, vb_ = (-442.8, -252.2), (-442.8, -260.6)            # the Market's west face (right = -x)
    _bay_front(F, V, va_, vb_, z + 0.0, z + 3.0, "int_ru_cafe_bay", bay=1.4, off=0.115, mull="int_ru_black")
    R.panel(V, va_, vb_, z + 3.0, z + 3.3, "int_ru_black", off=0.13)
    bx_, by_ = -443.0 - 0.32, -260.75                        # the blade: a two-faced 8-gon disc, 0.5 m out
    V.box(-443.1, by_ - 0.02, z + 3.5, -442.9, by_ + 0.02, z + 3.56, "int_ru_steel", faces="+y-y+z-z-x")
    for sgn in (1, -1):
        ring = [(bx_ - 0.33 * math.cos(2 * math.pi * k / 8 + math.pi / 8) * sgn,
                 z + 3.2 + 0.33 * math.sin(2 * math.pi * k / 8 + math.pi / 8)) for k in range(8)]
        V.poly([(x_, by_ + 0.012 * sgn, zz_) for x_, zz_ in ring], "int_ru_sign_market",
               uvs=[(0.5 + 0.5 * math.cos(2 * math.pi * k / 8 + math.pi / 8), 0.5 + 0.5 * math.sin(2 * math.pi * k / 8 + math.pi / 8))
                    for k in range(8)], normal_hint=(0, sgn, 0))
    # two honey-wood bin cubes with black slot tops against the Market glass (user_03), one block
    for by2_ in (-259.3, -258.6):
        V.box(-443.52, by2_ - 0.27, z, -442.98, by2_ + 0.27, z + 1.0, "int_ru_maple_panel", faces="+x-x+y-y")
        V.box(-443.52, by2_ - 0.27, z + 1.0, -442.98, by2_ + 0.27, z + 1.03, "int_ru_black", faces="+x-x+y-y+z")
    K.col_box(C, -443.52, -259.57, z, -442.98, -258.33, z + 1.03, K.COL_NOCAM)
    # -- Esports arena (B19): an orange ARENA line under the end-wall GATOR ESPORTS CENTER bulkhead
    R.panel(V, (-461.3, -308.45), (-463.9, -308.45), z + 3.0, z + 3.32, "int_ru_sign_arena", off=0.02, glow=True)
    RZ.kit_add(P, "G", tag="g_userphoto_ground")


DRESSERS.append(g_userphoto_ground)


# ================================================================== Level 1: food court
SERVERY_FRONTS = [   # (wall points a -> b on the servery outline, generic sign, back-wall paint, side paint, style)
    # placed by the layout's food_vendors pins (props_extra L1: mvf_pins + osm_pins; generic signs, no brands)
    # fidelity-2: slot 0 is the photographed one (ru_food_court_counter_2023: the empty former counter by the lime
    # wall + sky-blue post: pale-blue siding, white top, a plain cream fascia, no sign); the red wok counter moved
    # one slot east and the pizza slot gave way to it
    # user-photo pass (user_19): slots 0 + 1 are ONE wide Panda front (deep red, lattice-tile counter base, the
    # stainless kitchen left, the honey-plank serving line right); slot 2 is the light-wood counter with the round
    # red badge (MVF: Shake Smart); Halal Shack and Starbucks moved to l1_room_02 (SERVERY2_FRONTS)
    ((-447.9, -310.6), (-453.1, -310.4), None, "int_ru_paint_cranberry", "int_ru_paint_cranberry", "panda_k"),     # Panda (u19)
    ((-441.0, -312.0), (-446.5, -310.9), None, "int_ru_wood_tan", "int_ru_paint_cranberry", "panda"),         # Panda (u19)
    ((-435.5, -309.8), (-440.0, -312.1), None, "int_ru_wood_tan", "int_ru_wood_tan", "smart"),            # Shake Smart
    ((-433.2, -303.0), (-433.2, -307.4), "int_ru_vend_taco", "int_ru_paint_sky", "int_ru_paint_lime", "tacos"),  # Mi Apa
    ((-433.2, -298.9), (-433.2, -302.2), "int_ru_vend_mac", "int_ru_paint_lime", "int_ru_paint_sky", "mac"),  # Mac Shack
    ((-424.9, -297.2), (-432.0, -297.15), "int_ru_vend_burger", "int_ru_fc_tile", "int_ru_white", "burger"),  # Sonic
    ((-424.3, -291.6), (-424.3, -296.6), "int_ru_vend_smoothie", "int_ru_paint_lime", "int_ru_paint_sky", "shakes"),
    ((-424.3, -286.6), (-424.3, -290.8), None, "int_ru_wall_cream", "int_ru_wall_cream", "closed"),    # (2023 look)
]
# user-photo pass (user_18, user_20, B01, B03): the storefronts on l1_room_02's corridor faces (MVF pins: Starbucks
# on the north face, Baba's Pizza on the east face, Halal Shack on the angled SE face)
SERVERY2_FRONTS = [
    ((-441.1, -328.4), (-448.5, -328.4), None, "int_ru_cafe_shelves", "int_ru_slat_walnut", "sbux"),
    # photo pass round 2 (fidelity-foodcourt 1, 5; B01, user_20): Baba's and Halal Shack open onto a lit white
    # kitchen (styles' "kitchen" line); brick / honey wood stay on the counters, knee wall, piers and sides
    ((-439.8, -334.1), (-439.9, -339.4), None, "int_ru_white", "int_ru_brick_rustic", "pizza"),
    ((-440.6, -340.9), (-443.6, -347.4), None, "int_ru_white", "int_ru_wood_tan", "halal2"),
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
    # ==== user-photo pass: the user's own food court photos
    "closed": {"counter": "int_ru_counter_front", "top": "int_ru_white", "fascia": "int_ru_wall_cream", "open_h": 2.7,
               "no_menu": True, "kitchen": True},
    "panda_k": {"counter": "int_ru_tile_lattice", "top": "int_ru_black", "side": "int_ru_paint_cranberry",
                "fascia": "int_ru_paint_cranberry", "open_h": 2.8, "no_menu": True, "kitchen": True, "hood": False,
                "left_panel": ("int_ru_paint_cranberry", 0.5), "right_panel": ("int_ru_paint_cranberry", 0.5)},
    "panda": {"counter": "int_ru_tile_lattice", "top": "int_ru_black", "side": "int_ru_paint_cranberry",
              "fascia": "int_ru_paint_cranberry", "open_h": 2.8, "hood": False, "menu": "int_ru_menu_screen", "menu_n": 3,
              "menu_w": 3.3, "menu_z": (2.2, 2.6), "letters": "int_ru_vletters_panda", "letters_w": 1.8,
              "letters_h": 0.5, "letters_x": 0.3,
              "left_panel": ("int_ru_paint_cranberry", 0.5), "right_panel": ("int_ru_paint_cranberry", 0.5),
              "decals": (("int_ru_badge_red", 2.05, 1.35, 2.85, 3.55, 0.125, True),)},
    "smart": {"counter": "int_ru_wood_tan", "top": "int_ru_black", "side": "int_ru_wood_tan", "fascia": "int_ru_white",
              "open_h": 2.8, "hood": False, "menu": "int_ru_menu_screen", "menu_n": 3, "menu_z": (2.0, 2.5),
              "letters": "int_ru_vletters_smart", "letters_w": 2.6, "letters_h": 0.36, "letters_x": -0.4,
              "decals": (("int_ru_badge_red", 1.65, 1.0, 2.88, 3.53, 0.125, True),)},
    "sbux": {"counter": "int_ru_slat_dark", "top": "int_ru_black", "side": "int_ru_slat_walnut",
             "back_counter": "int_ru_slat_dark", "menu": "int_ru_chalkboard", "menu_glow": False, "menu_w": 3.4,
             "menu_z": (2.05, 2.7), "hood": False, "coffee_bar": True, "fascia": "int_ru_black", "open_h": 2.9,
             "letters": "int_ru_vletters_sbux", "letters_w": 3.0, "letters_h": 0.38, "letters_x": 0.6,
             "left_panel": ("int_ru_slat_walnut", 0.5), "right_panel": ("int_ru_slat_walnut", 0.5),
             "decals": (("int_ru_badge_green", 3.0, 2.3, 2.92, 3.52, 0.125, True),), "light": 0.45},
    "pizza": {"counter": "int_ru_brick_rustic", "top": "int_ru_black", "side": "int_ru_brick_rustic",
              "fascia": "int_ru_black", "open_h": 2.8, "hood": False, "no_menu": True, "kitchen": True,
              "left_panel": ("int_ru_brick_rustic", 0.4), "right_panel": ("int_ru_brick_rustic", 0.4),
              "pendants": (-0.88, 0.88),
              "decals": (("int_ru_vletters_babas", 2.0, -2.0, 0.25, 0.85, 0.67, False),
                         ("int_ru_badge_babas", -1.6, -2.6, 2.58, 3.55, 0.13, True),     # BABA'S / PIZZA (B01)
                         ("int_ru_menu_screen", 1.45, 0.45, 2.95, 3.45, 0.12, True),
                         ("int_ru_menu_screen", 0.35, -0.65, 2.95, 3.45, 0.12, True),
                         ("int_ru_menu_screen", -0.75, -1.45, 2.95, 3.45, 0.12, True))},
    "halal2": {"counter": "int_ru_wood_tan", "top": "int_ru_black", "side": "int_ru_wood_tan", "fascia": "int_ru_white",
               "open_h": 2.8, "hood": False, "kitchen": True, "menu": "int_ru_menu_screen", "menu_n": 3, "menu_z": (2.0, 2.55),
               "letters": "int_ru_vletters_halal2", "letters_w": 3.4, "letters_h": 0.36,
               "decals": (("int_ru_badge_gold", 2.75, 2.05, 2.85, 3.55, 0.125, True),)},
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


# user-photo pass (user_19, user_20, B01): queue lanes for Panda, Halal Shack and Baba's Pizza
FC_STANCHIONS2 = (((-452.6, -312.6), (-452.6, -313.0), (-447.0, -313.4), (-442.0, -314.2)),
                  ((-437.9, -340.6), (-440.7, -346.8), (-442.4, -350.4)),
                  ((-437.7, -334.6), (-437.7, -336.7), (-437.7, -338.8)))


def _fc_stanchions(V, z, pts=None):
    """Visual only (Mario walks through the belts: no thin invisible-looking collision walls in the queue)."""
    FC_STANCHIONS = pts or globals()["FC_STANCHIONS"]
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
    # user-photo pass (user_19): a dark warm-grey speckled queue band (the tan / brown diamond checker is gone)
    R.floor_poly(V, ring_in + list(reversed(outer)), z, "int_ru_fc_queue", step=FLOOR_STEP)
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
        # user-photo pass (user_19): Panda's deep red wraps the SW corner (it was the 2023 lime wall + sky post)
        _wall_strip(V, sw_a, cut, z + 0.12, zs, "int_ru_paint_cranberry", off=0.03)
        _wall_strip(V, cut, sw_b, z + 0.12, zs, "int_ru_paint_cranberry", off=0.06)
    # ... and the 1.4 m jog between the two Panda slots
    _wall_strip(V, (-447.85, -310.9), (-446.55, -310.9), z + 0.12, zs, "int_ru_paint_cranberry", off=0.13)
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
    # user-photo pass: the l1_room_02 storefronts (Starbucks, Baba's Pizza, Halal Shack); visual openings only (the
    # corridor face keeps its collision, like the servery's)
    r02 = F.zone("l1_room_02").poly
    for i, (a, b, sign, back, side, sty) in enumerate(SERVERY2_FRONTS):
        w = math.dist(a, b)
        cxm, cym = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        nx, ny = (b[1] - a[1]) / w, -(b[0] - a[0]) / w
        if R.pip((cxm + nx * 0.5, cym + ny * 0.5), r02):
            nx, ny = -nx, -ny
        facing = math.degrees(math.atan2(nx, ny)) % 360.0
        RZ.kit_add(R.storefront(w, sign, back, side, h=FC_FRONT_H, style=VENDOR_STYLES.get(sty)), "L1",
                   tag=f"storefront2_{i}", x=cxm, y=cym, z=z, facing=facing)
    _fc_stanchions(V, z)
    for pts_ in FC_STANCHIONS2:
        _fc_stanchions(V, z, pts_)
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
            # user-photo pass (user_18, B03): the pairs right in front of the new Starbucks / Baba's fronts give way
            # to the round mauve tables and the queues
            if (yy == -326.5 and xx in (-445.0, -439.0)) or (yy == -330.0 and xx <= -439.0):
                continue
            # photo pass round 2 (fidelity-foodcourt 2; B03): in front of Starbucks every table is a round mauve
            # laminate top (same positions and merged collision block as the pairs)
            mauve = yy in (-323.0, -326.5) and xx <= -439.0
            for sgn in (-1, 1):
                if mauve:
                    RZ.kit_add(_nocol(R.cafe_table_set(chair_mat="int_ru_uf_blue", frame="int_ru_maple_light",
                                                       top="int_ru_laminate_mauve", round_top=True)), "L1",
                               tag=f"fc_table_{k}", x=xx + sgn * 1.0, y=yy, z=z, facing=45.0)
                else:
                    RZ.kit_add(_nocol(R.cafe_table_set(chair_mat="int_ru_uf_blue", frame="int_ru_maple_light")), "L1",
                               tag=f"fc_table_{k}", x=xx + sgn * 1.0, y=yy, z=z, facing=0.0)
                k += 1
            K.col_box(C, xx - 1.375, yy - 0.375, z, xx + 1.375, yy + 0.375, z + 0.75, K.COL_NOCAM)
    for (xx, yy) in ((-420.0, -300.0), (-417.5, -306.0), (-420.0, -312.0), (-416.0, -292.5), (-414.6, -299.4)):
        RZ.kit_add(R.cafe_table_set(chair_mat="int_ru_uf_blue", frame="int_ru_maple_light"), "L1", tag=f"fc_table_{k}",
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
        # user-photo pass (B02 'big white square column', user_18 TVs on them): the south row is 0.8 m square
        hw = 0.4 if cy < -320.0 else 0.3
        V.box(cx - hw, cy - hw, z, cx + hw, cy + hw, z + F.clear, "int_ru_white", faces="+x-x+y-y")
        K.col_box(C, cx - hw, cy - hw, z, cx + hw, cy + hw, z + F.clear, K.COL)
        if cy < -320.0:
            V.box(cx - 0.62, cy + hw, z + 2.73, cx + 0.62, cy + hw + 0.06, z + 3.47, "int_ru_black", faces="+y+x-x-z+z")
            R.panel(V, (cx + 0.58, cy + hw + 0.06), (cx - 0.58, cy + hw + 0.06), z + 2.77, z + 3.43, "int_ru_score_tv",
                    off=0.015, glow=True)
    _fc_fidelity2(RZ, F, P, serv, fc, band, cols_, k, soffit_polys)
    # FOOD COURT sign over the queue ring (east)
    R.panel(V, (-424.0, -287.5), (-424.0, -283.0), z + 4.75, z + 5.35, "int_ru_sign_foodcourt", off=0.0, glow=True)
    RZ.kit_add(P, "L1", tag="food_court_misc")
    RZ.points.setdefault("food_court", {})["center"] = {"name": "interior_food_court_center", "p": [-438.0, -318.0, z],
                                                         "kind": "ground"}


DRESSERS.extend([food_court])


def _fc_downlights(V, P, s_in, zs, depth):
    """Two staggered rows of small glowing downlights under a curved soffit band (as food_court's)."""
    for frac, start in ((0.62, 0.6), (0.25, 1.4)):
        mid = _offset_open(s_in, depth * frac)
        acc, nxt, k = 0.0, start, (0 if frac > 0.5 else 2)
        for a, b in zip(mid, mid[1:]):
            L = math.dist(a, b)
            while acc + L >= nxt:
                t = (nxt - acc) / L
                mx, my = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
                V.poly([(mx - 0.1, my - 0.1, zs - 0.01), (mx - 0.1, my + 0.1, zs - 0.01),
                        (mx + 0.1, my + 0.1, zs - 0.01), (mx + 0.1, my - 0.1, zs - 0.01)], "int_ru_led", glow=True)
                if k % 4 == 1 and frac > 0.5:
                    P.lights.append(K.Light((mx, my, zs - 0.4), radius=4.5, strength=0.22, color=LIGHT_WARM))
                k += 1
                nxt += 1.6
            acc += L


def food_court_user(RZ):
    """User-photo pass (the user's own food court photos user_18, user_19, user_20, B01-B03): the
    Starbucks stepped soffit, the COFFEA ARABICA chalk mural with taupe club chairs and round mauve tables, the
    curved white soffit over Baba's Pizza + Halal Shack (gold blade sign, honey-plank wall), the UF Bookstore front
    (orange fascia, blue LED HOME OF THE GATORS / BOOKSTORE, rolling grilles, the Nike window with the #0 / #7
    mannequins), the south hall's royal-blue wainscot + orange bulkhead, grey vinyl floors, ORDER HERE kiosks."""
    F = RZ.floors["L1"]
    z = F.z
    P = K.Prop("food_court_user")
    V, C = P.visual, P.collision
    zs = z + FC_SOFFIT_Z
    ztop = z + CLEAR["L1"] - 0.01
    # ---- Starbucks: stepped white soffits (user_18, B03) in front of the storefront on l1_room_02's north face
    V.box(-451.65, -328.25, z + 3.55, -441.0, -326.2, ztop, "int_ru_soffit", faces="-z+y+x", ao=0.95)
    V.box(-451.65, -329.62, z + 3.55, -448.65, -328.25, ztop, "int_ru_soffit", faces="-z", ao=0.95)
    V.box(-451.65, -326.2, z + 4.1, -441.0, -324.6, ztop, "int_ru_soffit", faces="-z+y+x", ao=0.95)
    for k in range(7):
        x_ = -450.6 + k * 1.6
        V.poly([(x_ - 0.1, -327.3, z + 3.54), (x_ - 0.1, -327.1, z + 3.54), (x_ + 0.1, -327.1, z + 3.54),
                (x_ + 0.1, -327.3, z + 3.54)], "int_ru_led", glow=True)
        if k % 3 == 1:
            P.lights.append(K.Light((x_, -327.0, z + 3.1), radius=4.0, strength=0.2, color=LIGHT_WARM))
    # a black linear slot diffuser under the upper step, parallel to the storefront
    V.poly([(-449.5, -325.43, z + 4.09), (-449.5, -325.37, z + 4.09), (-443.5, -325.37, z + 4.09),
            (-443.5, -325.43, z + 4.09)], "int_ru_black")
    # ---- COFFEA ARABICA chalk mural on the recessed face + dark wood returns (user_18)
    off_m = _face_off(F, (-450.15, -329.8), (0.0, 1.0), gap=0.02)
    R.panel(V, (-448.63, -329.8), (-451.67, -329.8), z + 0.12, z + 3.5, "int_ru_mural_coffea", off=off_m)
    _wall_strip(V, (-448.5, -328.4), (-448.5, -329.8), z + 0.12, z + 3.5, "int_ru_slat_dark",
                off=_face_off(F, (-448.5, -329.1), (-1.0, 0.0), gap=0.02))
    _wall_strip(V, (-451.8, -329.8), (-451.75, -326.5), z + 0.12, z + 3.5, "int_ru_slat_dark",
                off=_face_off(F, (-451.77, -328.2), (1.0, 0.0), gap=0.02))
    for j, xx in enumerate((-451.15, -450.15, -449.15)):
        RZ.kit_add(R.lounge_chair(mat="int_ru_fabric_taupe", seat="int_ru_fabric_taupe", col=False), "L1",
                   tag=f"fc_coffea_chair_{j}", x=xx, y=-329.05, z=z, facing=0.0)
    K.col_box(C, -451.55, -329.5, z, -448.75, -328.65, z + 0.6, K.COL_NOCAM)
    # ---- round mauve laminate tables with the maple / royal-blue chairs (B03)
    for j, xx in enumerate((-450.0, -446.6, -443.2)):
        RZ.kit_add(R.cafe_table_set(chair_mat="int_ru_uf_blue", frame="int_ru_maple_light", top="int_ru_laminate_mauve",
                                    round_top=True), "L1", tag=f"fc_mauve_{j}", x=xx, y=-325.0, z=z, facing=45.0)
    # ---- curved white soffit over Baba's Pizza + Halal Shack (B01, user_20), l1_room_02's corridor faces (CCW)
    path = [(-448.0, -348.9), (-444.3, -348.9), (-439.9, -339.4), (-439.8, -334.1), (-441.1, -334.1), (-441.1, -329.6)]
    outer = _offset_open(path, FC_RING_DEPTH)
    R.floor_poly(V, path + list(reversed(outer)), zs, "int_ru_soffit", step=FLOOR_STEP, down=True, ao=0.95)
    for a, b in zip(outer, outer[1:]):
        R.quad_wall(V, a, b, zs, zs + 0.7, "int_ru_soffit", ao=0.9)
    R.quad_wall(V, path[0], outer[0], zs, zs + 0.7, "int_ru_soffit", ao=0.9)
    R.quad_wall(V, outer[-1], path[-1], zs, zs + 0.7, "int_ru_soffit", ao=0.9)
    _fc_downlights(V, P, path, zs, FC_RING_DEPTH)
    # Halal Shack: honey planks on the east 4 m of the room's south face + the round gold blade sign at the corner
    _wall_strip(V, (-448.3, -348.85), (-444.45, -348.9), z + 0.12, zs - 0.01, "int_ru_wood_tan",
                off=_face_off(F, (-446.3, -348.87), (0.0, -1.0), gap=0.02))
    bc, bd = (-443.44, -350.25), (-0.51, 0.86)
    ba, bb = (bc[0] - bd[0] * 0.45, bc[1] - bd[1] * 0.45), (bc[0] + bd[0] * 0.45, bc[1] + bd[1] * 0.45)
    # photo pass round 2 (fidelity-foodcourt 5): plain HALAL / SHACK on the gold disc (it showed a generic icon)
    R.panel(V, ba, bb, z + 2.6, z + 3.5, "int_ru_badge_halal", off=0.012, glow=True)
    R.panel(V, bb, ba, z + 2.6, z + 3.5, "int_ru_badge_halal", off=0.012, glow=True)
    # Baba's (B01): a lit glass pizza case on the counter top (z +1.06; the counter runs 0.72 m out of the plan line
    # x ~-439.85): warm-lit trays under clear glass, visual only (the corridor face keeps its collision)
    V.box(-439.72, -338.45, z + 1.06, -439.28, -335.05, z + 1.12, "int_ru_led", faces="+x-x+y-y+z", glow=True,
          tint=(1.0, 0.72, 0.42))
    V.box(-439.74, -338.5, z + 1.06, -439.24, -335.0, z + 1.46, "int_ru_glass_clear", faces="+x+y-y+z")
    V.box(bc[0] - 0.01, bc[1] - 0.01, z + 3.5, bc[0] + 0.01, bc[1] + 0.01, zs - 0.005, "int_ru_black", faces="+x-x+y-y")
    # ---- UF Bookstore front on the south hall's south wall (user_20). The decals follow the exterior wall's plan
    # line (three plan walls; the built face is EXT_T / 2 north of it) and split at its kinks (no _face_off: its
    # start-point distance drifts on a sloped wall)
    SW = [(-446.6, -357.1), (-427.8, -357.3), (-425.2, -357.3), (-418.3, -357.4)]

    def wy(x):
        for (ax, ay), (bx, by) in zip(SW, SW[1:]):
            if ax - 1e-6 <= x <= bx + 1e-6:
                return ay + (by - ay) * (x - ax) / (bx - ax)
        return SW[0][1] if x < SW[0][0] else SW[-1][1]

    def sp(x, gap):
        return (x, wy(x) + EXT_T / 2 + gap)

    def south_panel(xa, xb, z0, z1, mat, gap, glow=False, u0=0.0, u1=1.0, v1=1.0):
        """A panel on the south wall from xa (east, the viewer's left) to xb (west), split at the plan kinks."""
        cuts = [xa] + [kx for kx, _ in SW if xb < kx < xa][::-1] + [xb]
        for s0, s1 in zip(cuts, cuts[1:]):
            ua = u0 + (u1 - u0) * (xa - s0) / (xa - xb)
            ub = u0 + (u1 - u0) * (xa - s1) / (xa - xb)
            R.panel(V, sp(s0, gap), sp(s1, gap), z0, z1, mat, glow=glow, u0=ua, u1=ub, v1=v1)
    south_panel(-419.1, -443.6, z + 3.2, z + 4.1, "int_ru_orange", 0.03)
    south_panel(-420.5, -426.6, z + 3.3, z + 4.0, "int_ru_sign_bk_gators", 0.06, glow=True)
    south_panel(-427.05, -428.15, z + 3.1, z + 4.2, "int_ru_badge_gator", 0.06, glow=True)
    south_panel(-428.9, -434.6, z + 3.3, z + 4.0, "int_ru_sign_bk_store", 0.06, glow=True)
    for (gx0, gx1) in ((-419.8, -426.6), (-428.8, -434.6)):
        south_panel(gx0, gx1, z + 0.02, z + 3.1, "int_ru_black", 0.02)
        south_panel(gx0, gx1, z + 0.02, z + 3.1, "int_ru_grille", 0.07, u1=abs(gx1 - gx0) / 0.6, v1=3.08 / 0.6)
        south_panel(gx0 - 0.02, gx1 + 0.02, z + 3.1, z + 3.2, "int_ru_steel", 0.08)
    south_panel(-430.6, -432.8, z + 0.9, z + 2.4, "int_ru_video_wall", 0.04, glow=True)
    south_panel(-427.4, -428.0, z + 1.2, z + 2.1, "int_ru_bulletin", 0.02)
    # the Nike window: a lit white back panel and two football mannequins (#0 white, #7 royal blue); no swoosh
    south_panel(-435.0, -437.6, z + 0.3, z + 3.0, "int_ru_white", 0.02, glow=True)
    yb = sp(-436.3, 0.0)[1] + 0.45
    for xm, body, u0, u1 in ((-435.7, "int_ru_white", 0.0, 0.5), (-436.9, "int_ru_uf_blue", 0.5, 1.0)):
        for lx in (-0.12, 0.12):
            V.box(xm + lx - 0.07, yb - 0.08, z, xm + lx + 0.07, yb + 0.08, z + 0.9, "int_ru_white", faces="+x-x+y-y")
        V.box(xm - 0.24, yb - 0.14, z + 0.9, xm + 0.24, yb + 0.14, z + 1.5, body, faces="+x-x+y-y+z")
        for ax in (-0.31, 0.31):
            V.box(xm + ax - 0.07, yb - 0.07, z + 0.98, xm + ax + 0.07, yb + 0.07, z + 1.46, body, faces="+x-x+y-y-z")
        R.panel(V, (xm + 0.2, yb + 0.14), (xm - 0.2, yb + 0.14), z + 1.0, z + 1.42, "int_ru_jersey", off=0.015,
                u0=u0, u1=u1)
        V.box(xm - 0.13, yb - 0.13, z + 1.5, xm + 0.13, yb + 0.15, z + 1.82, body, faces="+x-x+y-y+z")
        # collision hugs each mannequin (a block reaching past the render reads as an invisible wall)
        K.col_box(C, xm - 0.36, yb - 0.15, z, xm + 0.36, yb + 0.16, z + 1.82, K.COL)
    # a red-orange banner pilaster west of the window
    south_panel(-437.8, -438.4, z + 0.4, z + 3.1, "int_ru_red", 0.03)
    # ---- the south hall's east wall (user_20, B02): royal-blue wainscot + UF-orange bulkhead, a blue directory
    # (one straight exterior plan wall (-418.3, -357.4) -> (-418.1, -338.1); the built face is EXT_T / 2 west of it)
    xe = lambda y: -418.3 + 0.2 * (y + 357.4) / 19.3
    _wall_strip_d(F, V, (xe(-338.2), -338.2), (xe(-357.2), -357.2), z + 0.005, z + 0.5, "int_ru_wall_royal",
                  off=EXT_T / 2 + 0.02)
    fx0 = xe(-357.2) - EXT_T / 2                       # the face's west-most point (south end)
    V.box(fx0 - 0.6, -357.2, z + 3.6, xe(-338.2) - EXT_T / 2 + 0.05, -338.2, z + 4.5, "int_ru_orange", faces="-x+y",
          ao=0.95)
    V.box(fx0 - 0.6, -357.2, z + 3.6, xe(-338.2) - EXT_T / 2 + 0.05, -338.2, z + 3.61, "int_ru_white", faces="-z",
          ao=0.95)
    for vy in (-341.5, -347.5, -353.5):      # round vent discs on the bulkhead face, 1.5 cm proud
        R.panel(V, (fx0 - 0.6, vy + 0.22), (fx0 - 0.6, vy - 0.22), z + 3.83, z + 4.27, "int_ru_badge_black", off=0.015)
    R.panel(V, (xe(-355.3), -355.3), (xe(-355.9), -355.9), z + 1.0, z + 2.2, "int_ru_wayfind_L1",
            off=EXT_T / 2 + 0.03, glow=True)
    # ---- grey vinyl (user_20, B02) in the south hall and the passage north of it, 1 cm over the fc tile
    vin = [(-454.1, -357.0), (-418.3, -357.4), (-418.1, -338.1), (-431.1, -338.0), (-431.1, -331.1), (-441.1, -331.1),
           (-441.1, -334.1), (-439.8, -334.1), (-439.9, -339.4), (-444.3, -348.9), (-454.1, -348.8)]
    R.floor_poly(V, vin, z, "int_ru_vinyl_grey", step=FLOOR_STEP)
    # ---- ORDER HERE kiosks (B02) facing the Panda queue
    for kx in (-436.6, -435.8, -435.0):
        V.box(kx - 0.225, -316.175, z, kx + 0.225, -315.825, z + 1.05, "int_ru_wall_royal", faces="+x-x+y-y+z")
        V.box(kx - 0.25, -316.08, z + 1.05, kx + 0.25, -316.0, z + 1.8, "int_ru_wall_royal", faces="+x-x+y-y+z")
        R.panel(V, (kx + 0.22, -316.0), (kx - 0.22, -316.0), z + 1.12, z + 1.74, "int_ru_menu_blue", off=0.012, glow=True)
        R.panel(V, (kx + 0.21, -315.825), (kx - 0.21, -315.825), z + 0.84, z + 0.9, "int_ru_order_here", off=0.012,
                glow=True)
    K.col_box(C, -436.85, -316.2, z, -434.75, -315.8, z + 1.8, K.COL)
    RZ.kit_add(P, "L1", tag="food_court_user")


DRESSERS.extend([food_court_user])

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
            if -452.5 < x < -440.0 and -330.5 < y < -323.8:      # user-photo pass: under the Starbucks soffit
                continue
            # user-photo pass (user_18-20, B02): square 2 x 2 lay-in troffers; every 7th cell a square return grille
            vent = (n_tr % 7 == 3)
            x0, x1, y0, y1 = x - 0.3, x + 0.3, y - 0.3, y + 0.3
            V.poly([(x0, y0, zc), (x0, y1, zc), (x1, y1, zc), (x1, y0, zc)],
                   "int_ru_vent_sq" if vent else "int_ru_troffer_sq",
                   uvs=[(0, 0), (0, 1), (1, 1), (1, 0)], glow=not vent)
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
                RZ.kit_add(_nocol(R.cafe_table_set(chair_mat="int_ru_uf_blue", frame="int_ru_maple_light")), "L1",
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


# iteration 9 (fidelity-4 blocking 1-3, one root cause): decorative wall dressing laid along whole room edges (the
# Grand Ballroom slate band + pilasters, the Gallery art boards, the Rion Ballroom panels, ...) covered doorways.
# Every edge-run dressing call asks these helpers for the door spans on its line and keeps DOOR_CLEAR off each jamb.
DOOR_CLEAR = 0.3


# plan doors that are listed in the layout data but not built (no opening, nothing behind): dressing may cross them
DOOR_NOT_BUILT = {("L1", 196)}       # the free-standing walkway glass pair removed in fidelity-2 (build_backdrop)


def _door_spans(F, a, b, clear=DOOR_CLEAR, tol=0.5):
    """Merged [(s0, s1)] along a -> b (0..L) covered by a plan door on (or within tol of, parallel to) that line,
    each widened by clear on both sides."""
    L = math.dist(a, b)
    if L < 0.05:
        return []
    dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    nx, ny = dy, -dx
    raw = []
    for di, d in enumerate(F.doors):
        p, q = (d[0], d[1]), (d[2], d[3])
        if math.dist(p, q) < 0.3 or (F.id, di) in DOOR_NOT_BUILT:
            continue
        cp = (p[0] - a[0]) * nx + (p[1] - a[1]) * ny
        cq = (q[0] - a[0]) * nx + (q[1] - a[1]) * ny
        if abs(cp) > tol or abs(cq) > tol:
            continue
        s0 = (p[0] - a[0]) * dx + (p[1] - a[1]) * dy
        s1 = (q[0] - a[0]) * dx + (q[1] - a[1]) * dy
        s0, s1 = min(s0, s1) - clear, max(s0, s1) + clear
        if s1 < 0.0 or s0 > L:
            continue
        raw.append((max(0.0, s0), min(L, s1)))
    raw.sort()
    out = []
    for s0, s1 in raw:
        if out and s0 <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], s1))
        else:
            out.append((s0, s1))
    return out


def _free_runs(F, a, b, clear=DOOR_CLEAR, s_lo=0.0, s_hi=None, min_len=0.05):
    """The complement of _door_spans inside [s_lo, s_hi] (default the whole edge): [(s0, s1)]."""
    L = math.dist(a, b)
    s_hi = L if s_hi is None else s_hi
    out, cur = [], s_lo
    for d0, d1 in _door_spans(F, a, b, clear):
        if d1 <= cur:
            continue
        if d0 >= s_hi:
            break
        if d0 - cur >= min_len:
            out.append((cur, d0))
        cur = max(cur, d1)
    if s_hi - cur >= min_len:
        out.append((cur, s_hi))
    return out


def _slot_clear(F, a, b, s0, s1, clear=DOOR_CLEAR):
    """True when [s0, s1] along a -> b stays clear of every plan door on that line (plus clear)."""
    return all(s1 <= d0 or s0 >= d1 for d0, d1 in _door_spans(F, a, b, clear))


def _sub(a, b, s0, s1):
    """The piece [s0, s1] of segment a -> b."""
    L = math.dist(a, b)
    dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    return (a[0] + dx * s0, a[1] + dy * s0), (a[0] + dx * s1, a[1] + dy * s1)


def _wall_strip_d(F, V, a, b, z0, z1, mat, off=0.02, clear=DOOR_CLEAR, min_len=0.05, **kw):
    """_wall_strip with the plan doors on its line cut out (the strip stops clear off each jamb). Returns the runs."""
    runs = _free_runs(F, a, b, clear, min_len=min_len)
    for s0, s1 in runs:
        pa, pb = _sub(a, b, s0, s1)
        _wall_strip(V, pa, pb, z0, z1, mat, off=off, **kw)
    return runs


# the dressing materials that must never stand inside a plan door opening (selftest _decor_in_doors)
DECOR_MATS = ("int_ru_wall_slate", "int_ru_art", "int_ru_acoustic", "int_ru_wood_panel", "int_ru_wall_navy",
              "int_ru_white", "int_ru_drape", "int_ru_drape_gold", "int_ru_proj_screen", "int_ru_led", "int_ru_black",
              "int_ru_counter_navy", "int_ru_mirror", "int_ru_paint_lime", "int_ru_paint_sky", "int_ru_picket",
              "int_ru_art_gal_a", "int_ru_art_gal_b",    # iteration 9: the Gallery's discrete pieces
              # user-photo pass (L1-L3 corridors + Rion): the timeline wall, oils, CCC desk / screen, Rion panels
              "int_ru_timeline", "int_ru_oils", "int_ru_marble", "int_ru_ccc_screen", "int_ru_wall_cream",
              "int_ru_fabric_taupe", "int_ru_office_bay", "int_ru_photo_bw", "int_ru_stone_grey")


def _decor_in_doors(M, mats=DECOR_MATS, clear_along=0.12, half_depth=0.32, zlo=0.3, zhi=2.2):
    """[(prop tag, material, floor, door index)] for every rendered face of a dressing prop (not the floor shells,
    which build the doors themselves) that stands inside a plan door opening's volume: within half_depth of the door
    line, inside its width less clear_along at each jamb, between zlo and zhi above the floor (the face is clipped
    to the door's width first, so a long strip that only passes the door is caught too)."""
    doors = []
    grid = {}
    for fid, F in M.floors.items():
        for i, d in enumerate(F.doors):
            a, b = (d[0], d[1]), (d[2], d[3])
            L = math.dist(a, b)
            if L < 0.3 or (fid, i) in DOOR_NOT_BUILT:
                continue
            k = len(doors)
            doors.append((fid, i, a, b, L, F.z))
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            grid.setdefault((int(mx // 4), int(my // 4)), []).append(k)
    out = []
    for t, g, p in M.kit.items:
        if t.startswith("shell_"):
            continue
        for poly in p.visual.polys:
            if poly.mat not in mats:
                continue
            pts = poly.pts
            xs, ys = [q[0] for q in pts], [q[1] for q in pts]
            cand = set()
            for gx in range(int(min(xs) // 4) - 1, int(max(xs) // 4) + 2):
                for gy in range(int(min(ys) // 4) - 1, int(max(ys) // 4) + 2):
                    cand.update(grid.get((gx, gy), ()))
            for k in cand:
                fid, i, a, b, L, z = doors[k]
                dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
                nx, ny = dy, -dx
                loc = [((q[0] - a[0]) * dx + (q[1] - a[1]) * dy, (q[0] - a[0]) * nx + (q[1] - a[1]) * ny, q[2])
                       for q in pts]
                for lim, sg in ((clear_along, 1.0), (L - clear_along, -1.0)):
                    nl = []
                    for j in range(len(loc)):
                        p0, p1 = loc[j - 1], loc[j]
                        i0, i1 = sg * (p0[0] - lim) >= 0.0, sg * (p1[0] - lim) >= 0.0
                        if i0 != i1:
                            t_ = (lim - p0[0]) / (p1[0] - p0[0])
                            nl.append(tuple(p0[c] + (p1[c] - p0[c]) * t_ for c in range(3)))
                        if i1:
                            nl.append(p1)
                    loc = nl
                    if not loc:
                        break
                if len(loc) < 3 or max(abs(q[1]) for q in loc) > half_depth:
                    continue
                o_al = max(q[0] for q in loc) - min(q[0] for q in loc)
                o_z = min(max(q[2] for q in loc), z + zhi) - max(min(q[2] for q in loc), z + zlo)
                if o_al > 0.12 and o_z > 0.12:
                    out.append((t, poly.mat, fid, i))
    return out


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

    def pil(a, dx, dy, nx, ny, sk, ztop, zb=None):
        px, py = a[0] + dx * sk, a[1] + dy * sk
        q0, q1 = (px - dx * 0.3, py - dy * 0.3), (px + dx * 0.3, py + dy * 0.3)
        R.seg_box(V, (q0[0] + nx * 0.12, q0[1] + ny * 0.12), (q1[0] + nx * 0.12, q1[1] + ny * 0.12), 0.12,
                  z + 0.1 if zb is None else zb, ztop, "int_ru_white", faces="sideends" if zb is None else "sideends_bot")

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
        # iteration 9 (fidelity-4 blocking 1): the slate band stops 0.3 m off each door jamb (it ran 18 cm in front
        # of all 10 walk-through perimeter doors: no exits visible from inside, Mario walked through the slate)
        _wall_strip_d(F, V, a, b, z + 0.1, z + 3.3, "int_ru_wall_slate", off=0.0, min_len=0.25)
        _wall_strip(V, a, b, z + 3.3, z + 3.4, "int_ru_white", off=0.01)
        if L > 20.0 and not east and mid_y < y0 + 1.0:
            # the stage's black pipe-and-drape (ru_os_grand_ballroom_2), 11 m centred behind the stage, in front of
            # the pilasters, clear of the backstage doors
            sc_ = ((x0 + x1) / 2 - a[0]) * dx + (y0 - a[1]) * dy
            for f0, f1 in _free_runs(F, a, b, s_lo=max(0.0, sc_ - 5.5), s_hi=min(L, sc_ + 5.5), min_len=0.3):
                pa_, pb_ = _sub(a, b, f0, f1)
                _wall_strip(V, pa_, pb_, z + 0.02, z + 3.0, "int_ru_drape", off=0.27)
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
                # iteration 9: a pilaster over a doorway starts above the band (the upper-wall rhythm stays)
                pil(a, dx, dy, nx, ny, sk, ztop,
                    zb=None if _slot_clear(F, a, b, sk - 0.3, sk + 0.3, 0.15) else z + 3.4)
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
    # iteration 9 (fidelity-4 sweep; technical doorpass8 L2 #133 / #134): the stage stood 0.1 m off the two
    # backstage doors (blocked under coopdx) and its drape hung across them and door 54. The stage is 2.2 m deep with
    # a 1.3 m passage behind it; the pipe-and-drape is hung on the wall, split around the doors (south-wall loop above)
    RZ.kit_add(R.stage_platform(9.0, 2.2, h=0.6, drape=False), "L2", tag="gb_stage", x=cxs, y=y0 + 2.5, z=z,
               facing=0.0)
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
    # user-photo pass (C07, C14-C16, the Rion confirmed by the user): light grey wall panels with cream
    # vertical reveals every 1.2 m and tall white speaker slots every 6 m (were dark-slate strips on white), a taupe
    # fabric panel on the east end wall, a dark clerestory band high on the west wall; the lit white lip stays
    for a, b in _room_inside_edges(zn, 0.11):
        L = math.dist(a, b)
        dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx, ny = dy, -dx
        _wall_strip_d(F, V, a, b, z + 0.1, zc - 0.7, "int_ru_wall_greige", off=0.02)
        k = 1
        while k * 1.2 < L - 0.3:
            sk = k * 1.2
            if _slot_clear(F, a, b, sk - 0.04, sk + 0.04):
                p0, p1 = _sub(a, b, sk - 0.04, sk + 0.04)
                _wall_strip(V, p0, p1, z + 0.1, zc - 0.7, "int_ru_wall_cream", off=0.035)
            k += 1
        if L > 12.0:
            m = 0
            while 6.0 * m + 3.0 < L - 1.0:
                sk = 6.0 * m + 3.0
                if _slot_clear(F, a, b, sk - 0.16, sk + 0.16):
                    p0, p1 = _sub(a, b, sk - 0.16, sk + 0.16)
                    _wall_strip(V, p0, p1, z + 2.7, z + 5.1, "int_ru_white", off=0.035)
                m += 1
        mx_, my_ = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        if abs(dx) < 0.05 and mx_ > (x0 + x1) / 2:          # the east end wall: taupe fabric panel
            s0_ = min(max(0.0, (-308.0 - a[1]) / dy), L) if dy else 0.0      # photo pass r2: smaller (c15)
            s1_ = min(max(0.0, (-318.0 - a[1]) / dy), L) if dy else 0.0
            s0_, s1_ = min(s0_, s1_), max(s0_, s1_)
            if s1_ - s0_ > 1.0:
                for r0, r1 in _free_runs(F, a, b, DOOR_CLEAR, s_lo=s0_, s_hi=s1_):
                    p0, p1 = _sub(a, b, r0, r1)
                    _wall_strip(V, p0, p1, z + 0.9, z + 3.9, "int_ru_fabric_taupe", off=0.06)
        if abs(dy) < 0.05 and my_ > (y0 + y1) / 2:          # photo pass r2: the long north wall (C15)
            _wall_strip(V, a, b, z + 4.6, z + 5.3, "int_ru_glass_smoke", off=0.05)
        # light cove along the top of every wall: a white lip with a glowing strip under it, washing the wall
        _wall_strip(V, a, b, zc - 0.62, zc - 0.5, "int_ru_led", off=0.05, glow=True)
        _wall_strip(V, a, b, zc - 0.5, zc - 0.02, "int_ru_white", off=0.06)
        # user-photo pass (C14): a lit EXIT sign over every door, inside
        for d0, d1 in _door_spans(F, a, b, clear=0.0):
            pa, pb = _sub(a, b, max(0.0, (d0 + d1) / 2 - 0.2), min(L, (d0 + d1) / 2 + 0.2))
            _wall_strip(V, pa, pb, z + 2.78, z + 2.98, "int_ru_exit", off=0.05, glow=True)
        for k in range(max(1, int(L / 7.0))):
            sk = L * (k + 0.5) / max(1, int(L / 7.0))
            P.lights.append(K.Light((a[0] + dx * sk + nx * 0.6, a[1] + dy * sk + ny * 0.6, zc - 1.2), radius=5.0,
                                    strength=0.14, color=LIGHT_WARM))
    # user-photo pass (C14-C16): the ceiling is long suspended light coves (lit edges, a row of downlights) between
    # dark cherry slat bands. Photo pass round 2: the coves run EAST-WEST, parallel to the screen wall (horizontal
    # across C14, converging sideways in C07, along the view in C15; were 8 north-south coves), 6 across the 27.5 m
    # depth, and their undersides are a warm bright cream (unlit glow; they baked charcoal, C14 measures ~187/161/141)
    nm = 6
    pitch = (y1 - y0) / nm
    cw = pitch - 1.45                       # cove width; a ~1.45 m cherry slat band between two coves
    cx0, cx1 = x0 + 1.5, x1 - 1.5
    nd = max(1, int((cx1 - cx0) / 2.45))
    for k in range(nm):
        cy = y0 + pitch * (k + 0.5)
        ya_, yb_ = cy - cw / 2, cy + cw / 2
        V.box(cx0, ya_, zc - 0.62, cx1, yb_, zc - 0.5, "int_ru_white", faces="+x-x+y-y")
        V.box(cx0, ya_, zc - 0.62, cx1, yb_, zc - 0.5, "int_ru_wall_cream", faces="-z", glow=True,
              tint=(0.86, 0.79, 0.72))
        for ey in (ya_, yb_ - 0.06):
            V.box(cx0, ey, zc - 0.64, cx1, ey + 0.06, zc - 0.62, "int_ru_led", faces="-z+x-x+y-y", glow=True)
        for j in range(nd):
            dx_ = cx0 + (cx1 - cx0) * (j + 0.5) / nd
            for dy_ in (cy - cw / 4, cy + cw / 4):
                V.poly([(dx_ - 0.11, dy_ - 0.11, zc - 0.645), (dx_ - 0.11, dy_ + 0.11, zc - 0.645),
                        (dx_ + 0.11, dy_ + 0.11, zc - 0.645), (dx_ + 0.11, dy_ - 0.11, zc - 0.645)], "int_ru_led",
                       glow=True, normal_hint=(0, 0, -1))
        for q in range(3):
            P.lights.append(K.Light((cx0 + (cx1 - cx0) * (q + 0.5) / 3, cy, zc - 1.5), radius=9.0, strength=0.22,
                                    color=LIGHT_WARM))
        if k > 0:
            # photo pass round 3 (C15): a darker brown band about a quarter of the cove width, centred in the gap
            # (was the whole 1.45 m gap in the redder int_ru_cherry)
            gm_ = ya_ - (pitch - cw) / 2
            by0, by1 = gm_ - 0.4, gm_ + 0.4
            V.poly([(cx0, by0, zc - 0.04), (cx0, by1, zc - 0.04), (cx1, by1, zc - 0.04), (cx1, by0, zc - 0.04)],
                   "int_ru_mahogany", normal_hint=(0, 0, -1))
    # user-photo pass (C07, C14): set for SwampHacks - two big projection screens on the south wall, a wood podium,
    # 7 rows of 6 white folding tables with black banquet chairs facing the screens (was a stage, a 4 m drape and
    # 12 x 30 theatre rows); one low NO_CAM block per half row
    ys_ = y0 + 0.11
    # the south wall is slightly skewed (y -324.0 at the west end, -324.3 at the east): the screens follow the
    # zone's south edge, inset like the wall panels
    sw = min(zip(zn.poly, zn.poly[1:] + zn.poly[:1]), key=lambda e: e[0][1] + e[1][1])
    (ex0, ey0), (ex1, ey1) = sw

    def south_y(x_):
        return ey0 + (ey1 - ey0) * (x_ - ex0) / (ex1 - ex0) + 0.11
    for sx in (-445.3, -435.8):            # photo pass round 3 (C14): ~3 m apart at the wall centre (were -447.3 / -433.8)
        if not _slot_clear(F, (x1, ys_), (x0, ys_), x1 - (sx + 3.3), x1 - (sx - 3.3), clear=0.1):
            continue
        R.panel(V, (sx + 3.28, south_y(sx + 3.28)), (sx - 3.28, south_y(sx - 3.28)), z + 1.58, z + 5.34, "int_ru_black",
                off=0.05)               # (raised to just under the wall cove's LED strip at zc - 0.62)
        R.panel(V, (sx + 3.2, south_y(sx + 3.2)), (sx - 3.2, south_y(sx - 3.2)), z + 1.66, z + 5.26, "int_ru_proj_screen",
                off=0.065, glow=True)
    RZ.kit_add(R.podium(), "L3", tag="rion_podium", x=-440.55, y=y0 + 1.7, z=z, facing=0.0)
    TX = (-452.5, -448.3, -444.1, -437.0, -432.8, -428.6)
    # photo pass round 2 (C07, C14): the same 42 tables grouped as SwampHacks hack clusters - three rows of two
    # tables pushed back to back with chairs on both sides, and one single front-facing row at the back (the last
    # row stays 0.7 m clear of the 'rion ballroom coins' line, y -300.5)
    rows = []
    for p_ in range(3):
        rows += [(2 * p_, -319.6 + 4.6 * p_, 0.0), (2 * p_ + 1, -319.6 + 4.6 * p_ + 0.75, 180.0)]
    rows.append((6, -305.0, 180.0))
    for r, ty, fa in rows:
        if ty < y0 + 3.0 or ty > y1 - 1.5:
            continue
        for i, tx in enumerate(TX):
            RZ.kit_add(_nocol(R.folding_table(L=1.8, W=0.75, top="int_ru_white", chairs=2, chair_mat="int_ru_black")),
                       "L3", tag=f"rion_table_{r}_{i}", x=tx, y=ty, z=z, facing=fa)
        if fa == 0.0:
            continue                     # one NO_CAM block per half cluster, added with its north table
        ys0 = ty - 0.75 - 0.375 if r % 2 == 1 else ty - 0.375
        for half in (TX[:3], TX[3:]):
            K.col_box(C, min(half) - 0.9, ys0, z, max(half) + 0.9, ty + 0.375, z + 0.74, K.COL_NOCAM)
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


AUD_BACK_STRIP = 1.35     # iteration 8: the back strip (Gallery door + stair) depth behind the top row, m
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
                # iteration 6 (technical improvement 2a): 1.5 cm off the wall (at 0.005 it lay 0.05-0.48 u off wall_aud
                # on the angled short walls beside the screen and z-fought); the door leaves moved out to 0.19 to match
                # iteration 9 (technical improvement 1): the strip stands 2 cm proud of the BUILT (rounded, ~0.7 deg
                # slanted) wall_aud face, measured, not 1.5 cm off the plan line (it cut into the face: 1.85 m2 of
                # z-fight at (-454.5, -248.2)); fidelity-4 sweep: strip + block stop at the plan door on the wall
                # (151 / 153 were covered), whose leaves the block's exit door now frames
                sh_ = _strip_shift(_built_wall_index(RZ), a, b, z + 0.1, zc - 0.3, gap=0.02, cap=0.1)
                _wall_strip_d(F, V, a, b, z + 0.1, zc - 0.3, "int_ru_wood_panel", off=max(0.015, sh_), clear=0.05)
                pd_ = _door_spans(F, a, b, clear=0.0)
                if L > 2.4:
                    # the honey-wood block: proud of the wall, an exit door + EXIT sign on its outer half
                    nx, ny = dy, -dx
                    for f0, f1 in _free_runs(F, a, b, clear=0.05, min_len=0.1):
                        pa_, pb_ = _sub(a, b, f0, f1)
                        R.panel(V, pa_, pb_, z + 0.1, z + 3.4, "int_ru_wood_panel", off=0.12)
                    side = 0.72 if (a[1] + b[1]) / 2 > (y0 + y1) / 2 else 0.28
                    sc = L * side
                    if pd_:
                        sc = (pd_[0][0] + pd_[0][1]) / 2           # the exit door on the plan door
                    # fix round 5 (fidelity-4 blocking): the leaves stand 0.17 off the wall line (8 cm proud of the
                    # block): at 0.13 the north leaf lay 0.5 mm off the next short wall's wood strip and z-fought
                    da = (a[0] + dx * (sc - 0.5) + nx * 0.19, a[1] + dy * (sc - 0.5) + ny * 0.19)
                    db = (a[0] + dx * (sc + 0.5) + nx * 0.19, a[1] + dy * (sc + 0.5) + ny * 0.19)
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
                # iteration 8 (technical improvement 4): 8 cm off the edge line (at 0.03 the strips lay 0-0.25 u off
                # the slightly slanted wall_aud face once their ends were rounded to whole units, and z-fought; at 0.05
                # some still sat only 1.3-1.9 u proud)
                _wall_strip(V, (q_[0] - dx * 0.13, q_[1] - dy * 0.13), (q_[0] + dx * 0.13, q_[1] + dy * 0.13),
                            z + 0.1, zc - 0.6, "int_ru_wood_panel", off=0.08)
    # raked seating: rows step up 0.18 m toward the east; continuous rows (no centre aisle), side aisles >= 1.2 m,
    # each row as wide as the room allows at its depth (the north-east corner is cut on the diagonal)
    nrows = 11
    # iteration 8 (technical blocking): the back strip behind the top row (the Gallery door's landing and the stair
    # foot) is 1.35 m from the zone edge = 1.25 m clear of the wall face (was 1.0 / 0.9 m: under coopdx's ground push
    # the 90 u turn between the rake back face and the door's jamb stub stopped every walk in from the Gallery;
    # DOOR_COL_MIN is 1.12 m). The rows are 2.7 cm shallower each.
    row_d = (x1 - x0 - 5.0 - AUD_BACK_STRIP) / nrows
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
    kb = 0
    for a, b in _room_inside_edges(zn, 0.12):
        L = math.dist(a, b)
        if L < 3.5:
            continue
        dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        m = 0.8
        # iteration 9 (fidelity-4 blocking 2 + improvement 9): discrete large boards (ru_os_gallery: 3-4 big pieces
        # per wall, not one continuous strip), split around every doorway with 0.3 m clear of each jamb (the strip
        # hung across doors 62, 63, 66, 75 and 119; Mario walked through the paintings)
        for f0, f1 in _free_runs(F, a, b, s_lo=m, s_hi=L - m, min_len=1.2):
            nb = max(1, int(round((f1 - f0 + 0.6) / 3.4)))
            w = (f1 - f0 - 0.6 * (nb - 1)) / nb
            for j in range(nb):
                g0 = f0 + j * (w + 0.6)
                pa, pb = _sub(a, b, g0, g0 + w)
                # iteration 9 (fidelity-4 improvement 9; ru_the_gallery): one large piece per board, alternating
                # the big blue canvas and the multicolour / photo-grid / landscape board (was the generic int_ru_art
                # row of small squares, repeated)
                R.panel(V, pa, pb, z + 1.1, z + 2.7, ("int_ru_art_gal_a", "int_ru_art_gal_b")[kb % 2], off=0.02)
                kb += 1
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
    closets_done = False      # iteration 9 (fidelity-4 improvement 4; ru_os_matthews_3 / _4): ONE closet wall
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
        if L > 6.0 and gaps and not closets_done:
            # the long wall with the wood door: two white double closets right beside it (ru_os_matthews_3); the
            # other long wall keeps only its framed photo groups (ru_os_matthews_4; both walls had closets)
            closets_done = True
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
    # iteration 9 (fidelity-4 improvement 2; ru_hotel_suite: plain white wall there): the zone-less 0.6 x 2.7 m
    # plan notch (x -440.5..-439.8, y -284.6..-281.9, a chase between the suite and room 520) is lined as a facade,
    # so its three faces showed ribbon windows onto brick. Plain white panels 2 cm in front of each built wall face
    # cover the window band (visual only; the glass collision 15 cm behind stays the wall)
    for pa_, pb_ in (((-440.65, -281.8), (-440.65, -284.7)),          # west face (the bedroom side)
                     ((-439.7, -281.75), (-440.6, -281.75))):         # north face (the bedroom's east strip)
        R.panel(V, pa_, pb_, z + 0.86, z + 3.24, "int_ru_wall", off=0.02)
    # south face (seen from the sitting room past the partition end): full height above the base and 6 cm longer
    # at its west end, so no brick shows in the crack at the partition end either
    R.panel(V, (-440.682, -284.722), (-439.826, -284.864), z + 0.12, zc - 0.02, "int_ru_wall", off=0.02)
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
    # iteration 9 (fidelity-4 sweep): the east drape is drawn back into the corner, clear of the balcony slider
    # (plan door L5 #22, x -441.1 .. -440.3; the drape hung across it and Mario walked through the cloth)
    _pleats(V, -440.25, xb - 0.03, yw, z + 0.02, z + 3.0, "int_ru_drape_gold", 2)
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
    # iteration 8 (technical improvement 1): 1.35 m (was 1.8 m from by0 + 1.15): its north-east corner stood 71 u
    # from the corridor door's east jamb, too tight to walk in under coopdx's push; now it clears the 1.12 x 1.0 m
    # swath inside the door
    yd0, yd1 = by0 + 1.05, by0 + 2.4
    V.box(bx1, yd0, z, bx1 + 0.55, yd1, z + 0.86, "int_ru_cherry", faces="+x+y-y+z")
    K.col_box(C, bx1, yd0, z, bx1 + 0.55, yd1, z + 0.86, K.COL_NOCAM)
    for k in range(1, 3):
        # iteration 8: the drawer reveals 1.5 cm proud of the dresser front (at 0.5 cm they z-fought with it)
        R.panel(V, (bx1 + 0.565, yd0 + 0.02), (bx1 + 0.565, yd1 - 0.02), z + 0.28 * k, z + 0.28 * k + 0.02,
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
    # user-photo pass (B17, the user's own photo): the reception faces WEST into the hotel-entrance lobby (the plan
    # prop + POI say so; the desk stood inside the sealed room, so the lobby saw a blank white wall). The room keeps
    # only its royal sign wall; the desk, the navy wall and the gold pendant are on the lobby side of x ~ -456.6.
    R.panel(V, (wx(-273.6), -273.6), (wx(-267.3), -267.3), z + 0.10, z + 3.8, "int_ru_wall_royal", off=0.012)
    R.panel(V, (wx(-271.65), -271.65), (wx(-269.25), -269.25), z + 2.3, z + 3.5, "int_ru_sign_hotel", off=0.03,
            glow=True)
    RZ.kit_add(P, "G", tag="hotel_reception")
    P = K.Prop("hotel_reception_lobby")
    V, C = P.visual, P.collision

    def lx(y):              # the lobby face of the room's west wall (plan line (-456.5, -266.8) -> (-456.6, -274.5))
        return -456.5 + (-456.6 + 456.5) * (y + 266.8) / (-274.5 + 266.8) - WALL_T / 2
    # navy wall behind the desk (faces -x) with the lit hotel sign
    R.panel(V, (lx(-267.0), -267.0), (lx(-273.9), -273.9), z + 0.10, z + 3.9, "int_ru_wall_navy", off=0.012)
    R.panel(V, (lx(-269.2), -269.2), (lx(-271.6), -271.6), z + 2.3, z + 3.5, "int_ru_sign_hotel", off=0.03,
            glow=True)
    # red-brown wood counter (int_ru_cherry), black kick, black granite top with a 5 cm overhang
    fx0, fx1, cy0, cy1 = -458.45, -457.75, -272.6, -268.2
    V.box(fx0, cy0, z + 0.12, fx1, cy1, z + 1.05, "int_ru_cherry", faces="+x-x+y-y")
    V.box(fx0 + 0.05, cy0 + 0.05, z, fx1 - 0.05, cy1 - 0.05, z + 0.12, "int_ru_black", faces="+x-x+y-y")
    V.box(fx0 - 0.05, cy0 - 0.05, z + 1.05, fx1 + 0.05, cy1 + 0.05, z + 1.10, "int_ru_granite_black",
          faces="+x-x+y-y+z-z")
    R.panel(V, (fx0, cy1 - 0.1), (fx0, cy0 + 0.1), z + 0.84, z + 0.92, "int_ru_black", off=0.012)
    K.col_box(C, fx0 - 0.05, cy0 - 0.05, z, fx1 + 0.05, cy1 + 0.05, z + 1.10, K.COL_NOCAM)
    # two monitors on the staff side (backs to the lobby)
    for my_ in (-271.3, -269.5):
        V.box(fx1 + 0.05, my_ - 0.26, z + 1.10, fx1 + 0.09, my_ + 0.26, z + 1.44, "int_ru_black",
              faces="+x-x+y-y+z")
        R.panel(V, (fx1 + 0.10, my_ - 0.24), (fx1 + 0.10, my_ + 0.24), z + 1.12, z + 1.42, "int_ru_game_screen",
                off=0.0, glow=True)
    # ONE gold geometric pendant (an 8-sided bipyramid) on a black rod, warm light
    zc = z + CLEAR["G"]
    px, py, rr = -458.1, -270.4, 0.32
    V.box(px - 0.012, py - 0.012, z + 3.45, px + 0.012, py + 0.012, zc, "int_ru_black", faces="+x-x+y-y")
    ring = [(px + rr * math.cos(2 * math.pi * k / 8 + math.pi / 8), py + rr * math.sin(2 * math.pi * k / 8 + math.pi / 8))
            for k in range(8)]
    for k in range(8):
        a_, b_ = ring[k], ring[(k + 1) % 8]
        V.poly([(a_[0], a_[1], z + 3.1), (b_[0], b_[1], z + 3.1), (px, py, z + 3.45)], "int_ru_brass",
               normal_hint=(a_[0] + b_[0] - 2 * px, a_[1] + b_[1] - 2 * py, 0.5))
        V.poly([(b_[0], b_[1], z + 3.1), (a_[0], a_[1], z + 3.1), (px, py, z + 2.75)], "int_ru_brass",
               normal_hint=(a_[0] + b_[0] - 2 * px, a_[1] + b_[1] - 2 * py, -0.5), tint=(1.15, 1.05, 0.85))
    P.lights.append(K.Light((px, py, z + 2.8), radius=4.0, strength=0.32, color=LIGHT_WARM))
    # lobby furniture (B17): two grey club chairs facing in from the doors' sides, a lit vending kiosk
    RZ.kit_add(R.lounge_chair("int_ru_leather_grey", "int_ru_leather_grey", col=False), "G", tag="hotel_lobby_chair_0",
               x=-461.55, y=-274.0, facing=90.0)
    RZ.kit_add(R.lounge_chair("int_ru_leather_grey", "int_ru_leather_grey", col=False), "G", tag="hotel_lobby_chair_1",
               x=-461.55, y=-265.4, facing=90.0)
    V.box(-458.7, -276.88, z, -457.7, -276.08, z + 1.9, "int_ru_black", faces="+x-x+y-y+z")
    R.panel(V, (-457.78, -276.08), (-458.62, -276.08), z + 0.35, z + 1.8, "int_ru_game_screen", off=0.01, glow=True)
    K.col_box(C, -458.7, -276.88, z, -457.7, -276.08, z + 1.9, K.COL_NOCAM)
    RZ.kit_add(P, "G", tag="hotel_reception_lobby")


# fix iteration 6 (design improvement 5): the student-art band repeated its 4 designs in strict ABCD order; 8 variants
# (each design plain or mirrored) in a scrambled order with no design repeated next to itself
ACC_ART_ORDER = [(0, 0), (2, 1), (1, 0), (3, 1), (2, 0), (0, 1), (3, 0), (1, 1), (0, 0), (3, 1), (1, 1), (2, 0),
                 (0, 1), (2, 1), (3, 0), (1, 0), (3, 1), (0, 0)]


def _acc_art_u(k):
    q, m = ACC_ART_ORDER[k % len(ACC_ART_ORDER)]
    return (q * 0.25 + 0.25, q * 0.25) if m else (q * 0.25, q * 0.25 + 0.25)


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
                u0=_acc_art_u(k)[0], u1=_acc_art_u(k)[1])
        k += 1
    for xw, yn in ((-447.4, -264.2), (-447.4, -265.9), (-447.2, -249.9), (-447.2, -251.6)):
        R.panel(V, (xw, yn), (xw, yn - 1.0), z + 1.35, z + 2.65, "int_ru_student_art", off=0.017,
                u0=_acc_art_u(k)[0], u1=_acc_art_u(k)[1])
        k += 1
    for i in range(6):
        ys = -258.6 + i * 2.0
        R.panel(V, (xw_(ys), ys), (xw_(ys + 1.0), ys + 1.0), z + 1.35, z + 2.65, "int_ru_student_art", off=0.017,
                u0=_acc_art_u(k)[0], u1=_acc_art_u(k)[1])
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
        # fix iteration 6 (design improvement 5; ru_acc_studio: a room full of light-wood tables with mustard-yellow
        # chairs): maple tops and yellow chairs, and three more tables (the open north half and the SE grid gap)
        for k, (xx, yy) in enumerate(((-455.0, -250.0), (-451.0, -250.0), (-455.0, -256.0), (-451.0, -256.0),
                                      (-455.0, -262.0), (-455.0, -247.1), (-451.0, -247.1), (-451.0, -262.0))):
            RZ.kit_add(R.folding_table(2.0, 1.0, top="int_ru_maple_panel", chairs=2, chair_mat="int_ru_fabric_mustard"),
                       "LL", tag=f"acc_table_{k}", x=xx, y=yy, z=z, facing=0.0)
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
ART_SKIP = [("LL", (-446.2, -262.4, -445.1, -257.4)),
            ("L3", (-457.5, -298.0, -424.0, -289.0)), ("L2", (-457.0, -305.0, -424.0, -300.0))]   # user-photo pass (C08, C12)
                  # the LL accent mural (lower_level)
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


WAINSCOT_FLOORS = ("LL",)          # user-photo pass (C08): the L2 meeting corridor walls are plain white
CEIL_GROUP_SKIP_DROPPED = True   # fix iteration 6 (design 7): no clear-height collision cover over a dropped ceiling
WAINSCOT_CORE = True      # fix iteration 6 (design 4): also band the core / stair side of the hall (see _corridor_wainscot)
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
    # (pa, pb, room zone or None): right of pa -> pb is the corridor side. Pass 1: the corridor-facing edges of the
    # solid rooms. Pass 2 (fix iteration 6, design improvement 4: the halls read lopsided, banded on the room side and
    # bare white on the facing core / stair / office-suite side): the corridor zones' own edges whose far side is a
    # solid block that pass 1 does not band (no zone = the core, or a solid non-room type), walked so the corridor is
    # on the right. The far-side test keeps the two passes apart (no doubled band on one wall).
    cands = []
    for oz in F.zones:
        if oz.type in SOLID_TYPES and oz.cls in ("S", "W"):
            cands.extend((pa, pb, oz) for pa, pb in R.edges(oz.poly))
    def _touches_void(cz):
        # iteration 7 (fidelity-1 regression): a corridor zone that holds / touches an atrium void is a BALCONY (the
        # L2 atrium balcony, l2_corridor_08): its back walls stay white / glazed (ru_atrium_enr_vertical)
        for vp in F.voids:
            if any(R.pip(p_, cz.poly) for p_ in vp) or any(R.pip(p_, vp) for p_ in cz.poly):
                return True
            if any(R.seg_point_dist(p_, a_, b_) < 0.3 for p_ in vp for a_, b_ in R.edges(cz.poly)):
                return True
        return False
    bays_ = [(a_, b_) for a_, b_ in EAST_END_OFFICES.get(F.id, ())]

    def _office_bay(q_):
        # ... and never across the glazed east office bays (int_ru_office_bay panels)
        return any(R.seg_point_dist(q_, a_, b_) < 0.6 for a_, b_ in bays_)
    for cz in F.zones:
        if WAINSCOT_CORE and cz.type == "corridor" and cz.cls == "W" and not _touches_void(cz):
            ccw_ = R.signed_area(cz.poly) > 0
            cands.extend(((pb, pa) if ccw_ else (pa, pb)) + (None,) for pa, pb in R.edges(cz.poly))
            # ... and the outer side of a corridor's edge when that side is another corridor (a big corridor polygon
            # need not follow the wall it shares with a small one: the smaller zone wins there)
            cands.extend(((pa, pb) if ccw_ else (pb, pa)) + (None,) for pa, pb in R.edges(cz.poly))
    placed = []                                  # (p0, p1, nout) of the bands so far: no band twice on one face

    def _dup(p0, p1, nv):
        L1 = math.dist(p0, p1)
        if L1 < 1e-6:
            return True
        ux_, uy_ = (p1[0] - p0[0]) / L1, (p1[1] - p0[1]) / L1
        for a0, a1, na in placed:
            if na[0] * nv[0] + na[1] * nv[1] < 0.99:
                continue
            if max(abs((a[0] - p0[0]) * nv[0] + (a[1] - p0[1]) * nv[1]) for a in (a0, a1)) > 0.12:
                continue
            ta, tb = sorted(((a[0] - p0[0]) * ux_ + (a[1] - p0[1]) * uy_) for a in (a0, a1))
            if min(tb, L1) - max(ta, 0.0) > 0.05:
                return True
        return False

    def _far_core(p_):
        cls_, zf_ = F.cls_at(p_)
        # a walled corridor-to-corridor edge counts too (the L2 pre-function hall's south wall backs onto the
        # restroom lobby corridor): each corridor bands its own face of the wall (no shared plane)
        return cls_ == "O" or (zf_ is not None and ((cls_ == "S" and zf_.type not in SOLID_TYPES) or
                                                    (cls_ == "W" and zf_.type == "corridor")))
    for pa, pb, oz in cands:
        if True:
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
                qb = (q[0] - nout[0] * 0.45, q[1] - nout[1] * 0.45)
                good = (not _office_bay(q) and
                        _corridor_at(F, (q[0] + nout[0] * 0.6, q[1] + nout[1] * 0.6)) is not None and
                        (F.zone_at(qb) is oz if oz is not None else _far_core(qb)) and
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
                if _dup(p0, p1, nout):
                    continue
                placed.append((p0, p1, nout))
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
    # user-photo pass (user_20): no planters in the south hall (removed; frees collision for the new fronts)
    # the University of Florida Bookstore sign over the link doors, on a 0.6 m deep white sign ledge (collision top + underside: a
    # double jump, or a jump and a ledge grab, reaches the coins on it)
    (ax, ay), (bx_, by_) = BOOKSTORE_DOOR
    mx = (ax + bx_) / 2
    yw = -357.0                                 # the hall face of the south wall at the doors (EXT_T / 2 north)
    x0, x1 = ax - 0.5, bx_ + 0.5
    V.box(x0, yw, z + 2.95, x1, yw + 0.6, z + 3.1, "int_ru_white", faces="+x-x+y+z-z")
    K.col_box(C, x0, yw, z + 2.95, x1, yw + 0.6, z + 3.1, K.COL, bottom=True)
    # user-photo pass (user_20): the dark fascia + white BOOKSTORE letters are replaced by the UF-orange Bookstore
    # front (food_court_user: orange fascia, blue LED letters, grilles, the Nike window)
    # iteration 6 (technical improvement 9): 0.52 m out on the 0.6 m ledge (at 0.3 the west coin sat within 0.5 m of
    # the slightly skewed south wall face: coins.py 'in wall')
    for dx in (-1.6, 0.0, 1.6):
        EXTRA_PICKUPS.append({"kind": "coin", "name": f"bookstore ledge coin {dx:+.1f}", "pos": (mx + dx, yw + 0.52, z + 3.1)})
    RZ.kit_add(P, "L1", tag="south_hall")
    # a second jump reward on the Ground: coins on top of three of the arcade cabinets by the Esports storefront
    # (game_room: tops at 1.85 m, x -458.8; double-jump, or hop from the 1.55 m kiosk at y -292.5)
    for i in (0, 3, 6):
        EXTRA_PICKUPS.append({"kind": "coin", "name": f"arcade top coin {i}", "pos": (-458.8, -283.6 - i * 0.95, 1.85)})


DRESSERS.extend([circulation_dress])


# ================================================================== user-photo pass: L1-L3 corridors + Rion
# The user's own photos (user_06-user_17, C03, C04, C07, C08, C11-C16; reference/interiors/reitz/user_reference)
# the Career Connections Center reception at the west end of the L1 north corridor, the UF Student Union history
# timeline wall round the core's north-east corner, the Orange-elevator passage sign, the north corridor's club
# chairs and oils, the GatorWell glass front, the Blue elevator lobby sign, the Rion pre-function letters.
def _hang_sign(V, xc, yc, z, zc, tiers):
    """A light-grey two-face hanging sign across x at yc (user_07, user_11): tiers [(w, zb, zt, mats, arrow)], mats
    the packed line textures (2 strips each), arrow None / 'up' / 'west' (navy arrow tile at the line start)."""
    for w, zb_, zt_, mats, arrow in tiers:
        x0, x1 = xc - w / 2, xc + w / 2
        V.box(x0, yc - 0.03, zb_ - 0.04, x1, yc + 0.03, zt_ + 0.04, "int_ru_white", faces="+x-x-z+z")
        for face in (1, -1):        # +1: the north face (a east -> b west); -1: the south face (a west -> b east)
            ta_, tb_ = (x1 - 0.05, x0 + 0.05) if face > 0 else (x0 + 0.05, x1 - 0.05)
            if arrow:
                arr = (ta_, ta_ - face * 0.4)
                ta_ = ta_ - face * 0.45
            n = 2 * len(mats)
            for q_ in range(n):
                pa = (ta_ + (tb_ - ta_) * q_ / n, yc)
                pb = (ta_ + (tb_ - ta_) * (q_ + 1) / n, yc)
                R.panel(V, pa, pb, zb_, zt_, mats[q_ // 2], off=0.035, glow=True, v0=0.5 if q_ % 2 == 0 else 0.0,
                        v1=1.0 if q_ % 2 == 0 else 0.5)
            if arrow == "up":
                ya = yc + face * 0.04
                pa, pb = (arr[0], ya), (arr[1], ya)
                V.poly([(pb[0], ya, zb_), (pa[0], ya, zb_), (pa[0], ya, zt_), (pb[0], ya, zt_)], "int_ru_arrow_navy",
                       uvs=[(0.0, 1.0), (0.0, 0.0), (1.0, 0.0), (1.0, 1.0)], normal_hint=(0, face, 0))
            elif arrow == "west":
                mirror = face < 0          # the tile points +u (toward b): b is west on the north face
                R.panel(V, (arr[0], yc), (arr[1], yc), zb_, zt_, "int_ru_arrow_navy", off=0.04,
                        u0=1.0 if mirror else 0.0, u1=0.0 if mirror else 1.0)
    top = max(t_[2] for t_ in tiers)
    wmax = max(t_[0] for t_ in tiers)
    for xr in (xc - wmax / 2 + 0.3, xc + wmax / 2 - 0.3):
        V.box(xr - 0.012, yc - 0.012, top + 0.04, xr + 0.012, yc + 0.012, zc, "int_ru_steel", faces="+x-x+y-y")


def _wayfind_l1_grey(V, z, zc):
    """L1 Blue elevator lobby sign at the lobby mouth (user_11): light grey, navy caps, two tiers."""
    _hang_sign(V, -444.9, -266.9, z, zc, [(3.6, z + 3.95, z + 4.25, ("int_ru_hang_blue_a", "int_ru_hang_blue_b"), None),
                                         (3.6, z + 3.5, z + 3.8, ("int_ru_hang_blue_c", "int_ru_hang_blue_d"), None)])


CCC_FACE = -465.13      # the CCC honey feature wall's east face (user_14): x -465.25..-465.13, y -267.8..-259.0
L1_CHAIR_GROUPS = [((-438.3, -437.3, -434.3, -433.3), (-435.8,)), ((-454.2, -453.2, -450.2, -449.2), (-451.7,)),
                   ((-426.5, -425.5, -424.5), (-423.5,))]
L1_CHAIR_Y = -261.45


def l1_userphoto_corridors(RZ):
    F = RZ.floors["L1"]
    z = F.z
    HB = _built_wall_index(RZ)
    P = K.Prop("l1_userphoto_corr")
    V, C = P.visual, P.collision

    def dec(a, b, z0, z1, mat, gap=0.02, **kw):
        off = _strip_shift(HB, a, b, z0, z1, gap=gap, cap=0.35) or gap
        R.panel(V, a, b, z0, z1, mat, off=off, **kw)
        return off

    def zc_at(p):
        zn_ = F.cls_at(p)[1]
        return z + (zn_.style["clear"] if zn_ is not None and zn_.style else F.clear)

    # -- (1) Career Connections Center reception (user_14, user_15; the blue screen at the corridor end in user_06,
    # user_08, C02, C06): a honey wood feature wall closing the jagged pockets of l1_room_11's east face, the blue
    # CAREER CONNECTIONS CENTER video wall on the north corridor axis, a white marble desk on a maple plinth, a marble
    # podium, a dark slat cloud with LED lines and two white ring lights (the CCC itself stays sealed)
    V.box(CCC_FACE - 0.12, -267.8, z, CCC_FACE, -259.0, z + 4.2, "int_ru_wood_panel", faces="+x+y-y+z")
    K.col_box(C, CCC_FACE - 0.12, -267.8, z, CCC_FACE, -259.0, z + 4.2, K.COL)
    R.panel(V, (CCC_FACE, -265.25), (CCC_FACE, -261.65), z + 1.35, z + 3.45, "int_ru_black", off=0.015)
    R.panel(V, (CCC_FACE, -265.15), (CCC_FACE, -261.75), z + 1.45, z + 3.35, "int_ru_ccc_screen", off=0.03, glow=True)
    V.box(-463.72, -265.22, z, -462.83, -261.68, z + 0.15, "int_ru_maple_panel", faces="+x-x+y-y+z")
    V.box(-463.65, -265.15, z + 0.15, -462.9, -261.75, z + 1.07, "int_ru_marble", faces="+x-x+y-y+z")
    K.col_box(C, -463.72, -265.22, z, -462.83, -261.68, z + 1.07, K.COL)
    V.box(-463.25, -267.3, z, -462.55, -266.7, z + 1.15, "int_ru_marble", faces="+x-x+y-y+z")
    K.col_box(C, -463.25, -267.3, z, -462.55, -266.7, z + 1.15, K.COL)
    V.box(-465.08, -268.4, z + 4.3, -459.4, -258.6, z + 4.42, "int_ru_slat_cloud", faces="-z+x-x+y-y", glow=True,
          tint=(0.92, 0.88, 0.84))       # photo pass round 3 (user_14, user_15): medium walnut (baked near-black)
    for yl in (-266.0, -263.45, -260.9):
        V.box(-464.9, yl - 0.03, z + 4.28, -459.6, yl + 0.03, z + 4.3, "int_ru_led", faces="-z+y-y", glow=True)
    for rx in (-463.27, -461.2):
        xa, xb, ya, yb = rx - 0.5, rx + 0.5, -265.05, -261.85
        for bx0, by0, bx1, by1 in ((xa, ya, xb, ya + 0.06), (xa, yb - 0.06, xb, yb), (xa, ya + 0.06, xa + 0.06, yb - 0.06),
                                   (xb - 0.06, ya + 0.06, xb, yb - 0.06)):
            V.box(bx0, by0, z + 3.66, bx1, by1, z + 3.74, "int_ru_led", faces="+x-x+y-y-z", glow=True)
    P.lights.append(K.Light((-462.6, -263.45, z + 3.4), radius=6.5, strength=0.2, color=LIGHT_WARM))

    # -- (2) UF Student Union history & timeline wall (user_07, user_08) round the core's north-east corner: grey
    # stone base, the orange / royal / navy / white timeline field, the orange header with its title, a B&W photo
    # frieze on top. North run faces north, east run (room_06, the Orange passage's west wall) faces east.
    for (a, b, head) in (((-420.2, -266.65), (-433.4, -266.5), "int_ru_timeline_head"),
                         ((-420.0, -275.0), (-420.0, -266.75), "int_ru_timeline_head2")):
        L = math.dist(a, b)
        dec(a, b, z + 0.0, z + 0.35, "int_ru_stone_grey", u1=L / 1.5, v1=0.35 / 1.5)
        dec(a, b, z + 0.35, z + 2.35, "int_ru_timeline", u1=L / 2.4)
        hoff = dec(a, b, z + 2.35, z + 2.75, "int_ru_orange_uf", u1=L / 2.0, v1=0.2)
        dec(a, b, z + 2.75, z + 3.45, "int_ru_photo_bw", u1=round(L / 1.4))
        s0 = (L - 3.2) / 2
        ha, hb = _sub(a, b, s0, s0 + 3.2)
        R.panel(V, ha, hb, z + 2.37, z + 2.73, head, off=hoff + 0.02)     # 2 cm in front of its own band

    # -- (3) the Orange-elevator passage: hanging sign at its mouth (user_07; the runner and cedar are FLOOR_INLAYS
    # and CEDAR_EXTRA)
    _hang_sign(V, -419.0, -265.9, z, zc_at((-419.0, -265.9)),
               [(3.4, z + 3.9, z + 4.2, ("int_ru_hang_pass_a", "int_ru_hang_pass_b"), "up"),
                (1.8, z + 3.45, z + 3.75, ("int_ru_hang_pass_c",), "west")])

    # -- (4) north corridor (user_06, user_08, user_10, C11): navy / grey club chairs with maple arm caps, backs to
    # the north wall, maple cube side tables, dark landscape oils over each group
    wa, wb = (-470.0, -260.8), (-410.0, -260.8)
    for gi, (xs_, ts_) in enumerate(L1_CHAIR_GROUPS):
        lo, hi = min(xs_ + ts_) - 0.5, max(xs_ + ts_) + 0.5
        if not _slot_clear(F, wa, wb, lo - wa[0], hi - wa[0], clear=0.4):
            continue
        for i, cx in enumerate(xs_):
            # photo pass round 3 (u06, u08, c11): navy upholstered arms with thin maple caps (the all-maple arms
            # read as tan cubes)
            RZ.kit_add(R.lounge_chair("int_ru_fabric_navy", "int_ru_leather_grey", arm="int_ru_fabric_navy",
                                      cap="int_ru_maple_panel", col=False),
                       "L1", tag=f"l1n_chair_{gi}_{i}", x=cx, y=L1_CHAIR_Y, z=z, facing=180.0)
        for tx in ts_:
            V.box(tx - 0.25, L1_CHAIR_Y - 0.25, z, tx + 0.25, L1_CHAIR_Y + 0.25, z + 0.5, "int_ru_maple_panel",
                  faces="+x-x+y-y+z")
        K.col_box(C, lo + 0.05, L1_CHAIR_Y - 0.43, z, hi - 0.05, L1_CHAIR_Y + 0.4, z + 0.46, K.COL_NOCAM)
        for k, (oa, ob) in enumerate(((lo + 0.3, lo + 1.2), (hi - 1.2, hi - 0.3))):
            off = _strip_shift(HB, (oa, -260.8), (ob, -260.8), z + 1.45, z + 2.15, gap=0.02, cap=0.35)
            if off:                          # only on a measured wall face (the north wall steps in and out)
                R.panel(V, (oa, -260.8), (ob, -260.8), z + 1.45, z + 2.15, "int_ru_oils", off=off, u0=0.5 * k,
                        u1=0.5 * k + 0.5)

    # -- (5) GatorWell glass storefront (user_10): four 1.15 m aluminium / glass bays on the south face, an orange
    # GatorWell decal on bays 3-4
    a, b = (-447.0, -260.8), (-442.4, -260.8)
    off0 = _strip_shift(HB, a, b, z + 0.1, z + 2.8, gap=0.03, cap=0.35) or 0.13
    L = math.dist(a, b)
    d = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
    n = (d[1], -d[0])

    def at(s_, off):
        return (a[0] + d[0] * s_ + n[0] * off, a[1] + d[1] * s_ + n[1] * off)
    nb = 4
    w = L / nb
    for i in range(nb):
        R.panel(V, at(i * w, 0.0), at((i + 1) * w, 0.0), z + 0.1, z + 2.75, "int_ru_office_bay", off=off0,
                u0=0.0 if i % 2 == 0 else 1.0, u1=1.0 if i % 2 == 0 else 0.0)
    for i in range(nb + 1):
        s_ = min(max(i * w, 0.035), L - 0.035)
        R.seg_box(V, at(s_, off0 + 0.005), at(s_, off0 + 0.08), 0.035, z + 0.1, z + 2.74, "int_ru_steel",
                  faces="sideends_top")
    R.seg_box(V, at(0.0, off0 + 0.0425), at(L, off0 + 0.0425), 0.0375, z + 2.75, z + 2.85, "int_ru_steel",
              faces="sideends_top_bot")
    R.panel(V, at(2 * w + 0.12, 0.0), at(L - 0.12, 0.0), z + 1.5, z + 1.8, "int_ru_sign_gatorwell", off=off0 + 0.012)
    RZ.kit_add(P, "L1", tag="l1_userphoto_corr")

    # -- (6) L3 Rion pre-function gallery (photo pass round 3; C03, C12, C13): one carpeted gallery (_rion_gallery_plan)
    # with RION BALLROOM letters over the Rion's double doors, a coffered ceiling (white soffits along both long
    # walls, white cross ribs) with the dark-wood beam strip and two linear lights down its length, a honey-front
    # counter on the north wall (C12 left, C13 right), the Bill Rion memorial case on the west end wall beside the
    # west door (C13), and RION BALLROOM EAST (C03): a 2 m double door, honey leaves held open into the corridor,
    # the letters over it and an EXIT sign inside
    F3 = RZ.floors["L3"]
    z3 = F3.z
    zn3 = F3.cls_at((-440.0, -293.6))[1]
    if zn3 is not None and zn3.id == RION_GALLERY:
        zc3 = z3 + (zn3.style["clear"] if zn3.style else F3.clear)
        P3 = K.Prop("l3_rion_prefunction")
        V3, C3 = P3.visual, P3.collision
        for a, b in (((-426.0, -297.05), (-430.6, -297.05)), ((-450.0, -296.9), (-454.6, -296.9))):
            off = _strip_shift(HB, a, b, z3 + 2.95, z3 + 3.4, gap=0.02, cap=0.35)
            if off:
                R.panel(V3, a, b, z3 + 2.95, z3 + 3.4, "int_ru_sign_rion", off=off)
        # coffers: soffit pieces whose wall-side edge stays inside each wall run (no gap, no poke into the Rion)
        zs = zc3 - 0.45
        for x0, x1, yw in ((-456.85, -448.6, -296.85), (-448.6, -432.7, -297.0), (-432.7, -427.9, -297.15),
                           (-427.9, -425.05, -297.2)):
            V3.box(x0, yw, zs, x1, -296.0, zc3, "int_ru_white", faces="-z+y")
        for x0, x1, yw in ((-456.85, -448.5, -289.65), (-448.5, -440.55, -289.8), (-440.55, -432.6, -290.0),
                           (-432.6, -425.05, -290.15)):
            V3.box(x0, -290.95, zs, x1, yw, zc3, "int_ru_white", faces="-z-y")
        for xr in (-451.6, -446.0, -440.4, -434.8, -429.2):
            V3.box(xr - 0.15, -296.0, zc3 - 0.25, xr + 0.15, -290.95, zc3, "int_ru_white", faces="-z+x-x")
        V3.box(-456.85, -293.95, zc3 - 0.35, -425.05, -293.35, zc3, "int_ru_mahogany", faces="-z+y-y")
        for yl in (-291.6, -295.7):
            V3.box(-456.6, yl - 0.05, zc3 - 0.03, -425.3, yl + 0.05, zc3 - 0.01, "int_ru_led", faces="-z+y-y+x-x",
                   glow=True)
        # the wood-front counter on the north wall (C12, C13): honey front, white top, solid
        cx0, cx1, cyw, cyf, ch = -455.4, -447.6, -289.68, -290.45, 0.95
        V3.box(cx0, cyf, z3, cx1, cyw, z3 + ch - 0.04, "int_ru_maple_panel", faces="-y+x-x")
        V3.box(cx0 - 0.03, cyf - 0.04, z3 + ch - 0.04, cx1 + 0.03, cyw, z3 + ch, "int_ru_white", faces="+z-y+x-x")
        K.col_box(C3, cx0 - 0.03, cyf - 0.04, z3, cx1 + 0.03, cyw, z3 + ch, K.COL)
        # the William E. (Bill) Rion memorial case on the west end wall, north of the west door (C13)
        a, b = (-456.9, -293.45), (-456.9, -291.75)
        t_ = _strip_shift(HB, a, b, z3 + 0.1, z3 + 2.1, gap=0.0, cap=0.35)
        if t_:
            fx = -456.9 + t_ + 0.005
            V3.box(fx, -293.45, z3, fx + 0.3, -291.75, z3 + 2.1, "int_ru_maple_panel", faces="+x+y-y+z")
            V3.poly([(fx + 0.315, -293.3, z3 + 0.35), (fx + 0.315, -291.9, z3 + 0.35),
                     (fx + 0.315, -291.9, z3 + 1.95), (fx + 0.315, -293.3, z3 + 1.95)], "int_ru_rion_case",
                    uvs=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)], normal_hint=(1, 0, 0))
            R.panel(V3, (fx + 0.335, -293.35), (fx + 0.335, -291.85), z3 + 0.3, z3 + 2.0, "int_ru_glass_faint",
                    off=0.0)
            K.col_box(C3, fx, -293.45, z3, fx + 0.34, -291.75, z3 + 2.1, K.COL_NOCAM)
        # EXIT signs over both gallery doors (C03: the lit EXIT at the far end), on the gallery side
        def ewx(y_):                # the east wall's centre line (-425.0, -297.2) -> (-425.1, -290.2)
            return -425.0 - 0.1 * (y_ + 297.2) / 7.0
        for a, b in (((-456.9, -295.75), (-456.9, -295.15)), ((ewx(-293.4), -293.4), (ewx(-294.0), -294.0))):
            off = _strip_shift(HB, a, b, z3 + 2.68, z3 + 2.9, gap=0.012, cap=0.35)
            if off:
                R.panel(V3, a, b, z3 + 2.68, z3 + 2.9, "int_ru_exit", off=off, glow=True)
        # RION BALLROOM EAST over the east door (corridor side) and its honey leaves held open into the corridor
        a, b = (ewx(-295.55), -295.55), (ewx(-291.85), -291.85)
        off = _strip_shift(HB, a, b, z3 + 2.76, z3 + 3.08, gap=0.012, cap=0.35)
        if off:
            R.panel(V3, a, b, z3 + 2.76, z3 + 3.08, "int_ru_sign_rion_east", off=off)
        for y0, y1 in ((-294.78, -294.72), (-292.68, -292.62)):
            V3.box(-424.93, y0, z3 + 0.02, -423.98, y1, z3 + 2.5, "int_ru_door", faces="+y-y+x+z")
            K.col_box(C3, -424.93, y0, z3, -423.98, y1, z3 + 2.5, K.COL_NOCAM)
        P3.lights.append(K.Light((-449.0, -293.6, zc3 - 1.0), radius=7.0, strength=0.12, color=LIGHT_WARM))
        P3.lights.append(K.Light((-433.0, -293.6, zc3 - 1.0), radius=7.0, strength=0.12, color=LIGHT_WARM))
        RZ.kit_add(P3, "L3", tag="l3_rion_prefunction")


def _glass_front(V, HB, a, b, z, nb, head=2.75, frit=False):
    """An aluminium / glass office front (user_10, C04) on the built wall face behind a -> b (facing right of a -> b):
    nb office-bay panels, steel mullions and a head; None (nothing built) when no single built face is found."""
    off0 = _strip_shift(HB, a, b, z + 0.1, z + head, gap=0.03, cap=0.35)
    if not off0:
        return None
    L = math.dist(a, b)
    d = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
    n = (d[1], -d[0])

    def at(s_, off):
        return (a[0] + d[0] * s_ + n[0] * off, a[1] + d[1] * s_ + n[1] * off)
    w = L / nb
    for i in range(nb):
        R.panel(V, at(i * w, 0.0), at((i + 1) * w, 0.0), z + 0.1, z + head, "int_ru_office_bay", off=off0,
                u0=0.0 if i % 2 == 0 else 1.0, u1=1.0 if i % 2 == 0 else 0.0)
    for i in range(nb + 1):
        s_ = min(max(i * w, 0.035), L - 0.035)
        R.seg_box(V, at(s_, off0 + 0.005), at(s_, off0 + 0.08), 0.035, z + 0.1, z + head - 0.01, "int_ru_steel",
                  faces="sideends_top")
    R.seg_box(V, at(0.0, off0 + 0.0425), at(L, off0 + 0.0425), 0.0375, z + head, z + head + 0.1, "int_ru_steel",
              faces="sideends_top_bot")
    if frit:
        for i in range(nb):
            R.panel(V, at(i * w + 0.04, 0.0), at((i + 1) * w - 0.04, 0.0), z + 0.95, z + 1.3, "int_ru_frit",
                    off=off0 + 0.01, u1=(w - 0.08) / 1.2)
    return off0


def upper_userphoto_more(RZ):
    """User-photo pass, second batch: the restroom-passage fountain niche (user_09), the CCC word wall (user_16),
    the Student Engagement glass front (C04) and the MEETING ROOMS 2315-2365 sign (C08)."""
    HB = _built_wall_index(RZ)
    F = RZ.floors["L1"]
    z = F.z
    P = K.Prop("l1_userphoto_more")
    V, C = P.visual, P.collision
    # restroom-passage fountain niche (user_09): a royal-blue niche panel with a white head lip on the accessible
    # bathroom's north face, a bi-level steel fountain with a bottle filler above the high bowl
    t_ = _built_face_t(HB, (-437.3, -266.75), (0.0, 1.0), z + 0.2, z + 2.4, reach=0.45)
    if t_ is not None and _slot_clear(F, (-440.0, -266.5), (-430.0, -266.5), 1.7, 3.6, clear=0.3):
        fy = -266.75 + t_
        V.box(-438.0, fy, z + 0.1, -436.6, fy + 0.02, z + 2.45, "int_ru_wall_royal", faces="+y+x-x")
        V.box(-438.05, fy, z + 2.45, -436.55, fy + 0.06, z + 2.51, "int_ru_white", faces="+y-z+z+x-x")
        # photo pass r2 (user_09): white side lips, so the blue panel reads as a niche behind a white surround
        for lx_ in (-438.07, -436.58):
            V.box(lx_, fy, z + 0.1, lx_ + 0.05, fy + 0.06, z + 2.45, "int_ru_white", faces="+y+x-x")
        # slimmer bowls (were 0.3 m tall boxes that read as grey crates): a thin bowl and a narrow apron under it
        for (x0_, x1_, h_) in ((-437.85, -437.3, 0.86), (-437.25, -436.7, 1.0)):
            V.box(x0_, fy + 0.02, z + h_ - 0.12, x1_, fy + 0.4, z + h_, "int_ru_steel", faces="+y+x-x+z-z")
            V.box(x0_ + 0.14, fy + 0.02, z + h_ - 0.42, x1_ - 0.14, fy + 0.16, z + h_ - 0.12, "int_ru_steel",
                  faces="+y+x-x-z")
            V.box(x0_ + 0.1, fy + 0.1, z + h_ + 0.012, x1_ - 0.1, fy + 0.34, z + h_ + 0.013, "int_ru_black", faces="+z")
        V.box(-437.15, fy + 0.02, z + 1.3, -436.8, fy + 0.12, z + 2.1, "int_ru_steel", faces="+y+x-x+z-z")
        K.col_box(C, -438.0, fy, z, -436.6, fy + 0.47, z + 1.0, K.COL_NOCAM)
        # photo pass round 3 (user_09): the projecting blue restroom-pictogram flag sign over the niche (two faces)
        V.box(-437.33, fy + 0.02, z + 2.9, -437.27, fy + 0.7, z + 2.94, "int_ru_steel", faces="+x-x+y+z-z")
        R.panel(V, (-437.3, fy + 0.08), (-437.3, fy + 0.66), z + 2.56, z + 2.88, "int_ru_sign_restroom_blade", off=0.022)
        R.panel(V, (-437.3, fy + 0.66), (-437.3, fy + 0.08), z + 2.56, z + 2.88, "int_ru_sign_restroom_blade", off=0.022)
        V.box(-437.32, fy + 0.07, z + 2.55, -437.28, fy + 0.67, z + 2.89, "int_ru_wall_royal", faces="+y-z+z")
    # the CCC cut-out word wall (user_15, user_16, user_17) on the CCC face x -463.2, facing east. Photo pass round 3
    # (user_16): ONE tall honey panel of dense small cut-out lettering (was two boards of giant words) south of a
    # shallow lounge alcove: honey wood lining with warm LED coves, a wall TV, a walnut slat cloud over it and four
    # teal tub chairs round a small table, kept within 1.7 m of the face (the lane to the south walkway glass doors
    # at x -462.4..-459.1 stays 4 m wide)
    for ya, yb in ((-280.95, -277.65),):
        a, b = (-463.25, ya), (-463.25, yb)
        if not _slot_clear(F, (-463.25, -285.0), (-463.25, -265.0), ya + 285.0, yb + 285.0, clear=0.3):
            continue
        off = _strip_shift(HB, a, b, z + 0.1, z + 3.4, gap=0.02, cap=0.35)
        if not off:
            continue
        R.panel(V, a, b, z + 0.1, z + 3.4, "int_ru_maple_panel", off=off)
        a2, b2 = _sub(a, b, 0.1, math.dist(a, b) - 0.1)
        R.panel(V, a2, b2, z + 1.75, z + 3.3, "int_ru_word_wall_dense_a", off=off + 0.015)
        R.panel(V, a2, b2, z + 0.2, z + 1.75, "int_ru_word_wall_dense_b", off=off + 0.015)
    a, b = (-463.25, -277.35), (-463.25, -272.95)
    off = _strip_shift(HB, a, b, z + 0.1, z + 3.4, gap=0.02, cap=0.35)
    if off and _slot_clear(F, (-463.25, -285.0), (-463.25, -265.0), -277.35 + 285.0, -272.95 + 285.0, clear=0.3):
        fx = -463.25 + off
        R.panel(V, a, b, z + 0.1, z + 3.4, "int_ru_wood_panel", off=off, u1=4.4 / 1.2)
        for zl in (z + 2.05, z + 3.32):          # warm LED cove lines across the honey lining
            V.box(fx, -277.3, zl, fx + 0.06, -273.0, zl + 0.04, "int_ru_led", faces="+x-z+z+y-y", glow=True)
        R.panel(V, (-463.25, -276.9), (-463.25, -275.75), z + 1.15, z + 1.85, "int_ru_black", off=off + 0.02)
        R.panel(V, (-463.25, -276.85), (-463.25, -275.8), z + 1.2, z + 1.8, "int_ru_ccc_screen", off=off + 0.035,
                glow=True)
        V.box(fx, -277.35, z + 3.4, -460.4, -272.95, z + 3.52, "int_ru_slat_cloud", faces="-z+x+y-y", glow=True,
              tint=(0.92, 0.88, 0.84))
        tx_, ty_ = -461.7, -275.0
        R.cyl(V, tx_, ty_, 0.32, z + 0.52, z + 0.56, "int_ru_white", n=10)
        R.cyl(V, tx_, ty_, 0.05, z, z + 0.52, "int_ru_black", n=6, top=False)
        for j, (dx_, dy_, f_) in enumerate(((-0.75, -0.75, 45.0), (-0.75, 0.75, 135.0), (0.75, -0.75, 315.0),
                                            (0.75, 0.75, 225.0))):
            RZ.kit_add(R.lounge_chair("int_ru_fabric_teal", swivel=True, col=False), "L1", tag=f"ccc_tub_{j}",
                       x=tx_ + dx_, y=ty_ + dy_, z=z, facing=f_)
        # one seat-height NO_CAM block over the whole cluster (collision budget; as the lounge groups)
        K.col_box(C, tx_ - 1.17, ty_ - 1.17, z, tx_ + 1.17, ty_ + 1.17, z + 0.48, K.COL_NOCAM)
        P.lights.append(K.Light((-461.6, -275.0, z + 2.8), radius=4.0, strength=0.14, color=LIGHT_WARM))
    # lime-green reveals on the navy CCC door at the back of its recess (user_14): the recess side walls (plan
    # y -267.9 and -270.4) are lime for 0.6 m out from the door plane (x -468.1)
    if F.cls_at((-467.7, -269.1))[0] == "W":
        R.panel(V, (-468.0, -267.9), (-467.4, -267.9), z + 0.1, z + 2.7, "int_ru_paint_lime", off=0.112)
        R.panel(V, (-467.4, -270.4), (-468.0, -270.4), z + 0.1, z + 2.7, "int_ru_paint_lime", off=0.112)
    RZ.kit_add(P, "L1", tag="l1_userphoto_more")
    # L2: Student Engagement glass front (C04) and the meeting-room corridor sign (C08)
    F2 = RZ.floors["L2"]
    z2 = F2.z
    P2 = K.Prop("l2_userphoto")
    V2 = P2.visual
    # (the line sits 5 cm off the plan wall: _built_face_t only looks in the 1 m cell of each sample point)
    for a, b, nb in (((-403.3, -262.05), (-399.7, -262.05), 3), ((-397.4, -262.05), (-390.8, -262.05), 6)):
        _glass_front(V2, HB, a, b, z2, nb, frit=True)
    # the curved orange corridor wall west of the Student Engagement front (C04), facing the corridor
    for w_ in F2.walls:
        a, b = (w_[0], w_[1]), (w_[2], w_[3])
        if not all(-411.0 <= q[0] <= -403.3 and -263.8 <= q[1] <= -262.0 for q in (a, b)) or math.dist(a, b) < 0.3:
            continue
        L_ = math.dist(a, b)
        m_ = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        nrm = ((b[1] - a[1]) / L_, -(b[0] - a[0]) / L_)
        if F2.cls_at((m_[0] + nrm[0] * 0.4, m_[1] + nrm[1] * 0.4))[0] != "W":
            a, b = b, a
        off = _strip_shift(HB, a, b, z2 + 0.1, z2 + 3.6, gap=0.02, cap=0.35)
        if off:
            _wall_strip_d(F2, V2, a, b, z2 + 0.1, z2 + 3.6, "int_ru_orange", off=off)
    xs, yc = -424.2, -302.4
    zn2 = F2.cls_at((xs, yc))[1]
    zc2 = z2 + (zn2.style["clear"] if zn2 is not None and zn2.style else F2.clear)
    ya, yb, zb_, zt_ = yc - 1.0, yc + 1.0, z2 + 3.3, z2 + 3.6
    V2.box(xs - 0.03, ya, zb_ - 0.04, xs + 0.03, yb, zt_ + 0.04, "int_ru_white", faces="+y-y-z+z")
    for pa, pb in (((xs, ya), (xs, yb)), ((xs, yb), (xs, ya))):
        m_ = _sub(pa, pb, 0.05, 1.0)
        m2 = _sub(pa, pb, 1.0, 1.95)
        R.panel(V2, m_[0], m_[1], zb_, zt_, "int_ru_hang_meet", off=0.035, glow=True, v0=0.5, v1=1.0)
        R.panel(V2, m2[0], m2[1], zb_, zt_, "int_ru_hang_meet", off=0.035, glow=True, v0=0.0, v1=0.5)
    for yr in (ya + 0.3, yb - 0.3):
        V2.box(xs - 0.012, yr - 0.012, zt_ + 0.04, xs + 0.012, yr + 0.012, zc2, "int_ru_steel", faces="+x-x+y-y")
    # the 2315-2330 fronts on the meeting corridor (C08): dark-tinted glass bays with steel mullions and grey
    # operable-partition stacks on the room-division lines, clear of every plan door (and its plaque) by 0.8 m
    a, b = (-456.0, -301.05), (-424.9, -301.05)
    for r0, r1 in _free_runs(F2, a, b, 0.8, min_len=1.0):
        pa, pb = _sub(a, b, r0, r1)
        off = _strip_shift(HB, pa, pb, z2 + 0.15, z2 + 3.0, gap=0.03, cap=0.35)
        if not off:
            continue
        nb_ = max(1, int(round((r1 - r0) / 1.2)))
        w_ = (r1 - r0) / nb_
        for i in range(nb_):
            q0, q1 = _sub(a, b, r0 + i * w_, r0 + (i + 1) * w_)
            R.panel(V2, q0, q1, z2 + 0.15, z2 + 2.75, "int_ru_glass_tint_dk", off=off)
        for i in range(nb_ + 1):
            sx = a[0] + min(max(r0 + i * w_, r0 + 0.03), r1 - 0.03)
            V2.box(sx - 0.03, -301.05 - off - 0.06, z2 + 0.15, sx + 0.03, -301.05 - off, z2 + 2.74, "int_ru_black",
                   faces="-y+x-x+z")
        V2.box(pa[0], -301.05 - off - 0.06, z2 + 2.75, pb[0], -301.05 - off, z2 + 2.83, "int_ru_black",
               faces="-y+x-x+z-z")
        # photo pass round 3 (C08): a transom bar across every bay (the fronts read as blackboards)
        V2.box(pa[0] + 0.03, -301.05 - off - 0.05, z2 + 2.08, pb[0] - 0.03, -301.05 - off, z2 + 2.13, "int_ru_black",
               faces="-y+z-z")
        for dxl in (-432.5, -440.15, -447.95):
            if pa[0] + 0.7 <= dxl <= pb[0] - 0.7:
                q0, q1 = (dxl - 0.6, -301.05), (dxl + 0.6, -301.05)
                R.panel(V2, q0, q1, z2 + 0.02, z2 + 3.0, "int_ru_partition", off=off + 0.075, u1=1.0, v1=2.5)
    RZ.kit_add(P2, "L2", tag="l2_userphoto")


DRESSERS.extend([l1_userphoto_corridors, upper_userphoto_more])


def _char_group(RZ, fid, tag, cx, cy, z):
    """photo pass r2 (user_12, user_13, user_17): a charcoal lounge group on the blue carpet (a sofa facing north, a
    low table, two charcoal club chairs facing it); one seat-height NO_CAM block."""
    RZ.kit_add(R.sofa(2.0, "int_ru_leather_char"), fid, tag=f"{tag}_sofa", x=cx, y=cy - 1.35, z=z, facing=0.0)
    RZ.kit_add(R.coffee_table(1.1, 0.6, col=False, mat="int_ru_black", top="int_ru_maple_panel"), fid,
               tag=f"{tag}_table", x=cx, y=cy + 0.05, z=z, facing=90.0)
    for j, (dx, f) in enumerate(((-1.35, 90.0), (1.35, 270.0))):
        prop = R.lounge_chair("int_ru_leather_char", "int_ru_fabric_char", col=False)
        RZ.kit_add(prop, fid, tag=f"{tag}_chair_{j}", x=cx + dx, y=cy + 0.1, z=z, facing=f)


def upper_userphoto_r2(RZ):
    """Photo pass round 2: the L1 west lounge east of the CCC word wall (user_12, user_13, user_17) and
    the Blue elevator lobby's navy upper walls and end doors (user_11)."""
    HB = _built_wall_index(RZ)
    F = RZ.floors["L1"]
    z = F.z
    P = K.Prop("l1_userphoto_r2")
    V, C = P.visual, P.collision

    def zc_at(p):
        zn_ = F.cls_at(p)[1]
        return z + (zn_.style["clear"] if zn_ is not None and zn_.style else F.clear)

    # -- (1) L1 west lounge (user_12, user_17: the open floor between the CCC word wall x -463.25 and the Blue
    # elevator block x -450.4, south of the north corridor). Blue triangle-geometric carpet on the east half (the
    # walk from the north corridor to the walkway glass doors and the south passage stays terrazzo), two white square
    # columns on the carpet's west edge, two charcoal lounge groups clear of the east-west walk to the Blue lobby
    # (y -273.4..-278.3), a white / silver gator sculpture on a low navy base, a lit honey-wood glass display case on
    # the elevator block, and red / orange / blue framed prints on the restroom block's north wall
    lx0, lx1, ly0, ly1 = -457.2, -450.6, -281.0, -268.3
    if all(F.cls_at(q)[0] == "W" for q in ((lx0, ly0), (lx1, ly0), (lx0, ly1), (lx1, ly1), ((lx0 + lx1) / 2, -275.0))):
        # (the carpet itself is a FLOOR_INLAYS rectangle: cut into the terrazzo, no decal)
        zc = zc_at((-454.0, -275.0))
        # photo pass round 3 (fidelity-upper r2, user_13): the south column, the second group and the prints were in
        # the pocket behind the cross wall at y -277.3 (x -455.2..-450.4); all now stand north of it
        for cy_ in (-270.4, -275.6):
            V.box(-457.28, cy_ - 0.28, z, -456.72, cy_ + 0.28, zc, "int_ru_white", faces="+x-x+y-y")
            K.col_box(C, -457.28, cy_ - 0.28, z, -456.72, cy_ + 0.28, zc, K.COL)
        for k, cy_ in enumerate((-271.4, -275.5)):
            _char_group(RZ, "L1", f"l1w_lounge_{k}", -453.7, cy_, z)
            K.col_box(C, -455.5, cy_ - 1.37, z, -451.9, cy_ + 0.55, z + 0.46, K.COL_NOCAM)   # sofa back to chair fronts
        # the gator sculpture (user_13): a low navy base, a white / silver low-poly gator (body, head, tail, legs)
        gx0, gx1, gy = -453.6, -451.6, -268.95
        V.box(gx0, gy - 0.3, z, gx1, gy + 0.3, z + 0.32, "int_ru_wall_navy", faces="+x-x+y-y+z")
        K.col_box(C, gx0, gy - 0.3, z, gx1, gy + 0.3, z + 0.32, K.COL_NOCAM)
        zb = z + 0.32
        V.box(gx0 + 0.55, gy - 0.16, zb + 0.08, gx0 + 1.3, gy + 0.16, zb + 0.34, "int_ru_steel_bright",
              faces="+x-x+y-y+z")
        V.box(gx0 + 1.3, gy - 0.12, zb + 0.1, gx0 + 1.62, gy + 0.12, zb + 0.3, "int_ru_steel_bright",
              faces="+x-x+y-y+z")
        V.box(gx0 + 1.62, gy - 0.08, zb + 0.1, gx0 + 1.92, gy + 0.08, zb + 0.22, "int_ru_white", faces="+x+y-y+z")
        V.box(gx0 + 0.1, gy - 0.09, zb + 0.06, gx0 + 0.55, gy + 0.09, zb + 0.24, "int_ru_steel_bright",
              faces="-x+y-y+z")
        for lxx in (gx0 + 0.65, gx0 + 1.15):
            for sg in (-1, 1):
                V.box(lxx, gy + sg * 0.16 - (0.08 if sg > 0 else 0.0), zb, lxx + 0.1, gy + sg * 0.16 +
                      (0.0 if sg > 0 else 0.08), zb + 0.1, "int_ru_white", faces="+x-x+y-y")
        # the lit display case on the elevator block's west face (user_12)
        t_ = _built_face_t(HB, (-450.4, -272.0), (-1.0, 0.0), z + 0.2, z + 2.2, reach=0.45)
        if t_ is not None:
            fx = -450.4 - t_
            V.box(fx - 0.5, -272.7, z, fx - 0.005, -271.1, z + 0.75, "int_ru_maple_panel", faces="-x+y-y+z")
            R.panel(V, (fx - 0.5, -272.65), (fx - 0.5, -271.15), z + 0.78, z + 1.95, "int_ru_glass_faint", off=0.0)
            V.box(fx - 0.47, -272.6, z + 1.0, fx - 0.03, -271.2, z + 1.02, "int_ru_glass_clear", faces="+z")
            V.box(fx - 0.5, -272.7, z + 1.95, fx - 0.005, -271.1, z + 2.05, "int_ru_maple_panel", faces="-x+y-y+z-z")
            V.box(fx - 0.45, -272.55, z + 1.9, fx - 0.05, -271.25, z + 1.93, "int_ru_led", faces="-z", glow=True)
            K.col_box(C, fx - 0.5, -272.7, z, fx, -271.1, z + 2.05, K.COL_NOCAM)
            P.lights.append(K.Light((fx - 0.8, -271.9, z + 1.6), radius=2.5, strength=0.12, color=LIGHT_WARM))
        # photo pass round 3 (user_13, left): a wall TV on the elevator block's west face, south of the case
        a, b = (-450.4, -274.15), (-450.4, -275.65)        # going south: the panel faces west, into the lounge
        off = _strip_shift(HB, a, b, z + 1.3, z + 2.15, gap=0.02, cap=0.35)
        if off:
            R.panel(V, a, b, z + 1.3, z + 2.15, "int_ru_black", off=off)
            a2, b2 = _sub(a, b, 0.05, 1.45)
            R.panel(V, a2, b2, z + 1.35, z + 2.1, "int_ru_tv_hotel", off=off + 0.012, glow=True)
        # framed prints on the restroom block's north wall (user_13)
        for k, (pa_x, pb_x) in enumerate(((-453.85, -454.85), (-452.3, -453.3), (-450.75, -451.75))):
            a, b = (pa_x, -277.33), (pb_x, -277.33)        # going west: the panels face north, into the lounge
            off = _strip_shift(HB, a, b, z + 1.35, z + 2.35, gap=0.02, cap=0.35)
            if off:
                R.panel(V, a, b, z + 1.35, z + 2.35, "int_ru_black", off=off)
                a2, b2 = _sub(a, b, 0.06, 1.04)
                R.panel(V, a2, b2, z + 1.41, z + 2.29, "int_ru_prints", off=off + 0.012, u0=k / 3.0,
                        u1=(k + 1) / 3.0)
        for q in ((-453.7, -271.0), (-453.7, -275.5)):
            P.lights.append(K.Light((q[0], q[1], zc - 0.9), radius=5.5, strength=0.12, color=LIGHT_WARM))

    # -- (2) Blue elevator lobby (user_11; x -446.9..-442.9, y -274.0..-266.9): navy upper walls on both elevator
    # walls from the door heads to the ceiling (under the head the band runs between the openings), a light in the
    # lobby, and honey-wood double doors with a sign on the servery's north wall at the far end
    zcl = zc_at((-444.9, -270.5))
    for a, b in (((-446.9, -274.0), (-446.9, -266.9)), ((-442.9, -266.9), (-442.9, -274.0))):
        off = _strip_shift(HB, a, b, z + 2.7, min(zcl - 0.05, z + 3.6), gap=0.02, cap=0.35)
        if not off:
            continue
        L = math.dist(a, b)
        R.panel(V, a, b, z + 2.66, zcl - 0.03, "int_ru_wall_lobby_navy", off=off, u1=L / 2.0,
                v1=(zcl - z - 2.69) / 2.0)
        for r0, r1 in _free_runs(F, a, b, 0.12, min_len=0.1):
            pa, pb = _sub(a, b, r0, r1)
            off2 = _strip_shift(HB, pa, pb, z + 2.42, z + 2.64, gap=0.02, cap=0.35)
            if off2:
                R.panel(V, pa, pb, z + 2.42, z + 2.66, "int_ru_wall_lobby_navy", off=off2, u1=(r1 - r0) / 2.0,
                        v1=0.12)
    P.lights.append(K.Light((-444.9, -270.5, zcl - 1.0), radius=5.0, strength=0.14, color=LIGHT_WARM))
    a, b = (-443.6, -277.4), (-446.2, -277.4)          # faces north (right of a -> b, going west)
    off = _strip_shift(HB, a, b, z + 0.05, z + 2.6, gap=0.02, cap=0.35)
    if off:
        R.panel(V, a, b, z + 0.0, z + 2.5, "int_ru_wood_panel", off=off, u1=1.0, v1=1.0)
        for i in range(2):
            q0, q1 = _sub(a, b, 0.08 + i * 1.22, 0.08 + (i + 1) * 1.22)
            R.panel(V, q0, q1, z + 0.0, z + 2.42, "int_ru_door_meeting_honey", off=off + 0.012,
                    u0=0.0 if i == 0 else 1.0, u1=1.0 if i == 0 else 0.0)
        R.panel(V, (-444.3, -277.4), (-445.5, -277.4), z + 2.62, z + 2.92, "int_ru_exit", off=off + 0.012, glow=True)
    RZ.kit_add(P, "L1", tag="l1_userphoto_r2")

    # -- (3) L3 west Rion pre-function: folded into the one gallery of l1_userphoto_corridors (6) in photo pass
    # round 3 (its beam strip, linear lights and the west RION BALLROOM letters now run the gallery's length)

    # -- (4) L1 north corridor (user_06, C11): the royal-blue Admin recess on the north wall, about a third of the
    # way down from the Orange passage (back wall round the Admin door, both side walls; door openings kept clear)
    P4 = K.Prop("l1_admin_recess")
    V4 = P4.visual
    zcr = zc_at((-430.6, -261.0))
    for a, b in (((-431.6, -259.7), (-429.6, -259.7)), ((-431.6, -260.8), (-431.6, -259.7)),
                 ((-429.6, -259.7), (-429.6, -260.8))):
        off = _strip_shift(HB, a, b, z + 0.12, zcr - 0.05, gap=0.02, cap=0.3)
        if off is None or off == 0.0 and math.dist(a, b) < 0.05:
            continue
        _wall_strip_d(F, V4, a, b, z + 0.12, zcr - 0.05, "int_ru_wall_royal", off=off or 0.02, clear=0.1)
        for d0, d1 in _door_spans(F, a, b, clear=0.1):
            pa, pb = _sub(a, b, max(0.0, d0), min(math.dist(a, b), d1))
            _wall_strip(V4, pa, pb, z + 2.66, zcr - 0.05, "int_ru_wall_royal", off=off or 0.02)
    RZ.kit_add(P4, "L1", tag="l1_admin_recess")

    # -- (5) CCC reception (user_14): the round blue CCC logo disc on the honey wall, left of the video wall
    P5 = K.Prop("l1_ccc_disc")
    V5 = P5.visual
    cy5, cz5, r5 = -266.6, z + 2.45, 0.55
    ring = [(cy5 + r5 * math.cos(math.pi * (k + 0.5) / 4), cz5 + r5 * math.sin(math.pi * (k + 0.5) / 4))
            for k in range(8)]
    V5.poly([(CCC_FACE + 0.02, yy, zz) for yy, zz in ring], "int_ru_wall_royal", normal_hint=(1, 0, 0))
    ring2 = [(cy5 + 0.6 * r5 * math.cos(math.pi * (k + 0.5) / 4), cz5 + 0.6 * r5 * math.sin(math.pi * (k + 0.5) / 4))
             for k in range(8)]
    V5.poly([(CCC_FACE + 0.035, yy, zz) for yy, zz in ring2], "int_ru_white", normal_hint=(1, 0, 0))
    ring3 = [(cy5 + 0.45 * r5 * math.cos(math.pi * (k + 0.5) / 4), cz5 + 0.45 * r5 * math.sin(math.pi * (k + 0.5) / 4))
             for k in range(8)]
    V5.poly([(CCC_FACE + 0.05, yy, zz) for yy, zz in ring3], "int_ru_wall_royal", normal_hint=(1, 0, 0))
    RZ.kit_add(P5, "L1", tag="l1_ccc_disc")

    # -- (6) L2 meeting corridor (C08): the stainless bi-level fountain on the south wall near the east mouth, on
    # the straight face west of the angled run by the 2340 door
    F2 = RZ.floors["L2"]
    z2 = F2.z
    t_ = _built_face_t(HB, (-431.7, -304.2), (0.0, 1.0), z2 + 0.2, z2 + 2.2, reach=0.45)
    if t_ is not None and _slot_clear(F2, (-434.0, -304.4), (-424.0, -304.4), 1.6, 3.0, clear=0.6):
        P6 = K.Prop("l2_fountain_2340")
        V6 = P6.visual
        fy = -304.2 + t_ + 0.015          # (the straight face is skewed ~1 cm over the fountain's width)
        for (x0_, x1_, h_) in ((-432.25, -431.7, 0.86), (-431.65, -431.1, 1.0)):
            V6.box(x0_, fy + 0.02, z2 + h_ - 0.3, x1_, fy + 0.45, z2 + h_, "int_ru_steel", faces="+y+x-x+z-z")
            V6.box(x0_ + 0.1, fy + 0.12, z2 + h_ + 0.012, x1_ - 0.1, fy + 0.38, z2 + h_ + 0.013, "int_ru_black",
                   faces="+z")
        V6.box(-431.6, fy + 0.02, z2 + 1.25, -431.15, fy + 0.15, z2 + 2.1, "int_ru_steel", faces="+y+x-x+z-z")
        K.col_box(P6.collision, -432.3, fy, z2, -431.05, fy + 0.45, z2 + 1.0, K.COL_NOCAM)
        RZ.kit_add(P6, "L2", tag="l2_fountain_2340")


DRESSERS.append(upper_userphoto_r2)


# iteration 8 (technical improvement 10): a wall face with no back face where a straight walk from walkable floor
# crosses it under coopdx's ground push (it skips a wall facing away from the move; vanilla's plane push is
# two-sided): l3_corridor_11 at plan (-440.2, -273.5) gets the same quad facing the other way (collision only).
# Game-unit vertices of the exported face, plan normal. The second one (ll_room_13 / ll_corridor_04 at
# (-403.2, -260.2), the x 6690..6700 wall) was tried and left out: its back face, which ends 35 u from LL door 23,
# blocked that door from ll_corridor_04 under dx151 (doorpass8 6/9 -> 0/9).
ONEWAY_BACKFACES = [
    # (1 u in front of the face: a back face on the very same 4 vertices is merged away as a duplicate face)
    # iteration 9 (technical improvement 2): 15 u in front (z -1955), not 1 u: the exporter welded the 1 u face onto
    # the original (a two-sided wall with no thickness) and a jump from l3_corridor_11 under the vanilla summed air
    # push still went through 75/84 times
    ("L3", ((3020, 1800, -1955), (2940, 1800, -1955), (2940, 2340, -1955), (3020, 2340, -1955)), (0.0, -1.0)),
]


def oneway_backfaces(RZ):
    for fid, quad, nrm in ONEWAY_BACKFACES:
        P = K.Prop(f"oneway_back_{fid}")
        q = [(gx / 100.0 - 470.0, -gz / 100.0 - 293.0, gy / 100.0) for gx, gy, gz in quad]
        P.collision.poly(q, K.COL, normal_hint=(nrm[0], nrm[1], 0.0))
        RZ.kit_add(P, fid, tag=f"oneway_back_{fid}")


DRESSERS.extend([oneway_backfaces])


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
