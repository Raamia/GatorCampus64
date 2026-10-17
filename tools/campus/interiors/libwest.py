"""Course 5: LIBRARY WEST AFTER DARK, the Library West INTERIOR at night (slot bbh, LEVEL_BBH, hub door 5),
built from data/uf/libwest_layout.json (docs/libwest_layout.md) with the interior kit
(tools/campus/interior_kit.py) and the generic interior helpers of interiors/marston.py (walls, partitions,
slabs, low-poly furniture, the backdrop's tree / Century Tower / extrusion helpers; imported read-only).

Pure Python (no bpy): build() returns a LibWest object holding an interior_kit.Kit of the whole stage (map
metres, z up, campus.json origin), the per-group Lighting for the vertex-colour bake (night), the anchor points
the mission author needs (measured on the built collision by tools/campus/build_interior.py), the pickups plan,
the preview cameras and the build notes. tools/campus/build_interior.py turns it into the DynOS level
mods/sgl64/levels/bbh/ (docs/flow.md 3.2 / 7).

    tools/.venv/bin/python -I tools/campus/interiors/libwest.py --selftest     (geometry checks, no Blender)
    tools/blender/run_blender.sh tools/campus/build_interior.py -- libwest [--previews]

What is built (docs/libwest_layout.md has the research; every deviation from 1:1 is in NOTES)
  * The 1967 tower on its three-storey base: F1-F3 on the registered UF plan footprint (the OSM outline incl.
    the 2006 north wing and its curved glass front), F4-F6 on the floor-4 tower plate, the base roof around the
    tower as walkable night ROOF TERRACES at z 18, the tower's hipped tile roof at the eaves (z 36).
  * Floors 6.0 m apart (real ~4.2 m): 5.4 m clear for the SM64 camera; plan dimensions 1:1.
  * The LOBBY (F1, a separate pocket behind the locked revolving door: cafe, the unbranded coffee counter, the
    escalator foot) under the PLAZA HALL, an 11.4 m void behind the two-storey entrance glass (the design's
    "rotunda", Act 3's Big Boo arena), the F2 balcony over it.
  * Vertical circulation: the west and east stair halls (F1 -> F6, 30 deg switchbacks, turn landings against
    the glass with Plaza views), the NW and NE stair halls in the north wing (F1 -> F3 + a roof door onto the
    north terrace at z 18), two static escalators (F1 -> F2, "switched off after hours"), the main elevators
    (car A OUT OF ORDER with its doors open on every floor: a wall-kick shaft; car B closed), the east elevator
    and the ADA elevator (closed).
  * Stacks: the plans' call-number ranges (1.2 m deep, 1.5-3.0 m: the layout's 3.6 m rows are built 3.0 m as at
    Marston) with end-cap steps and book-cart bridges; F1's compact (mobile) shelving with floor rails.
  * Rooms: 10 glass group-study rooms on F2, F4's 416/417/401/405, F6's grad rooms, Rm 211, the electrical rooms
    (Act 4's breakers), the F5 staff break room; closed staff blocks, restrooms and offices are sealed.
  * NIGHT: vertex-colour light baked dim and warm (most troffers off), desk lamps with warm pools on every table,
    carrel and window desk (green banker's lamps on F6), cool blue light inside the glass, lit stair halls, red
    EXIT signs over the stair doors, glowing screens; outside a dark-blue night (solid background + fog), a
    low-poly campus backdrop with lit windows, Plaza lamps, stars, a moon and Century Tower floodlit.
  * Outside is never walkable: the backdrop has no collision, so every terrace edge is an SM64 out-of-bounds
    edge; the revolving door and the north doors are locked (leave through the pause menu).
Coordinates: map metres; game X = (x - cx) * 100, Y = z * 100, Z = -(y - cy) * 100 with (cx, cy) = CENTER.
"""
import importlib.util
import json
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))           # tools/campus/interiors
CAMPUS_TOOLS = os.path.dirname(HERE)                        # tools/campus
ROOT = os.path.abspath(os.path.join(CAMPUS_TOOLS, "..", ".."))
if CAMPUS_TOOLS not in sys.path:
    sys.path.insert(0, CAMPUS_TOOLS)

import interior_kit as K  # noqa: E402

# the generic helpers of the Marston module (read-only reuse; marston.py is not changed by this stage)
_spec = importlib.util.spec_from_file_location("interior_marston_helpers", os.path.join(HERE, "marston.py"))
MH = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(MH)

ccw, rect_poly, bbox, pip, in_rect, clip_rect = MH.ccw, MH.rect_poly, MH.bbox, MH.pip, MH.in_rect, MH.clip_rect
seg_point_dist, intervals_union, intervals_subtract = MH.seg_point_dist, MH.intervals_union, MH.intervals_subtract
split_line, edges, signed_area, Cells = MH.split_line, MH.edges, MH.signed_area, MH.Cells
thick_wall, thin_partition, box_prop, floor_box, poly_slab = (MH.thick_wall, MH.thin_partition, MH.box_prop,
                                                               MH.floor_box, MH.poly_slab)
col_seg_box = MH.col_seg_box

LAYOUT_PATH = os.path.join(ROOT, "data", "uf", "libwest_layout.json")
CAMPUS_PATH = os.path.join(ROOT, "data", "uf", "campus.json")

# ------------------------------------------------------------------ stage identity (docs/flow.md 2 / 3.2)
KEY = "libwest"
SLOT = "bbh"
LEVEL_CONST = "LEVEL_BBH"
COURSE_CONST = "COURSE_BBH"
DOOR = 5
CENTER = (38.9, 285.6)                  # stages.json interior_stages[library_west].center_m (layout center_m)

# ------------------------------------------------------------------ level look (what the BBH slot brings: NOTES)
MUSIC = "SEQ_LEVEL_SPOOKY"              # Big Boo's Haunt's theme; LEVEL_BBH's music dynamics (sDynBbh) only switch
                                        # on rooms 13 / 10: this level has no ROOMS (every floor is room 0), so the
                                        # full mix plays everywhere (coopdx v1.5.1 src/audio/external.c)
TERRAIN = "TERRAIN_SPOOKY"              # BBH's own: creaky wood footsteps; no gameplay effect (not TERRAIN_SLIDE)
BACKGROUND = None                       # solid night colour instead of a skybox (GEO_BACKGROUND_COLOR)
NIGHT_RGB = (16, 22, 48)
BACKGROUND_COLOR = tuple(K._srgb_to_linear(c / 255.0) for c in NIGHT_RGB)   # Fast64 gamma-corrects it back
FOG_RGB = NIGHT_RGB
COL_SLIDE = "COL slide"                 # build_interior makes the material (unused here)
SPAWN_NOTE = ("stage entry spawn (bhvSpinAirborneWarp, MARIO_POS) in the entrance vestibule just inside the "
              "locked revolving door, facing north up the escalators; the object hovers 1 m above this floor")
POINTS_COORDINATES_MAP_M = ("x = east, y = north, z = metres above the hub's grade (F1 lobby floor = 0; F2 6, F3 12, "
                            "F4 + roof terraces 18, F5 24, F6 30, tower eaves 36); origin = Century Tower")
POINTS_NOTE = ("Anchor points for the Course 5 mission author (docs/game_design.md 7.5), measured on the built "
               "collision of levels/bbh. 'actN_' keys use the design act numbers (7.5: 1 All-Nighter, 2 Quiet Hours "
               "Hide-and-Seek (co-op), 3 The Ghost of Finals Past, 4 Lights Out, 5 Coffee Run, 6 Re-shelve the "
               "Glowing Books); course act order is the mission author's (docs/flow.md 5.1: solo acts first, co-op "
               "last; suggested 1 = design 1, 2 = design 3, 3 = design 2). Points with a 'check' key did not measure "
               "as designed. No level-script star: every mission spawns its own (spawn_default_star from the "
               "controller, star id act - 1). Act-only devices (stair barriers, rolling ladders, Boos, breakers, the "
               "cup) are Lua objects: static level geometry cannot be act-masked.")
PREVIEW_OVERVIEW = ((34.0, -78.0, 92.0), (0.0, 6.0, 8.0), 42.0)     # stage-local camera, target, vfov

# ------------------------------------------------------------------ vertical frame (game metres)
# the course act of QUIET HOURS HIDE & SEEK - 2P (course.lua act names; uf_west_library_missions.lua
# LIBWEST_MISSION_ACTS.hideseek, design 7.5 act 2): Goombas in its arena are left out of it (plan_pickups);
# tools/luatest/test_libwest_missions.lua checks the built level script for it
HIDE_SEEK_ACT = 3

FLOORS = ("F1", "F2", "F3", "F4", "F5", "F6")
BASE_FLOORS = ("F1", "F2", "F3")
TOWER_FLOORS = ("F4", "F5", "F6")
Z = {"F1": 0.0, "F2": 6.0, "F3": 12.0, "F4": 18.0, "F5": 24.0, "F6": 30.0, "ROOF": 36.0}
STOREY = 6.0
SLAB = 0.6
CLEAR = STOREY - SLAB
WALL_T = 0.30
PARAPET_H = 1.1
DOOR_H = 2.6
ROOM_DOOR_W = 2.4
STUDY_DOOR_W = 2.0
THIN_COL_T = MH.THIN_COL_T
TALL_RANGE_H = 3.0
HIPPED_RIDGE = 5.0                      # tile roof ridge over the eaves (36 m)
BULKHEAD_TOP = Z["F4"] + CLEAR          # NW / NE stair-hall roof bulkheads (their roof slab 23.4 .. 24.0)

# per-floor accent (layout materials_and_light: plan key colours) as carpet tints, kept light so the navy carpet
# still reads at night; terrazzo (lobby, escalators, elevator lobbies) is the real mustard of recycled chips (S17)
CARPET_TINT = {"F1": (1.0, 0.90, 0.80), "F2": (0.96, 0.88, 1.0), "F3": (1.0, 0.88, 0.84),
               "F4": (0.88, 1.0, 0.88), "F5": (0.92, 0.92, 0.92), "F6": (0.86, 0.90, 1.0)}
ACCENT_TINT = {"F1": (1.0, 0.62, 0.36), "F2": (0.86, 0.56, 1.0), "F3": (1.0, 0.66, 0.52),
               "F4": (0.66, 0.92, 0.62), "F5": (0.75, 0.75, 0.75), "F6": (0.52, 0.62, 1.0)}
TERRAZZO = (1.0, 0.86, 0.54)

# night light (layout materials_and_light.vertex_colour_light, tuned on the previews)
WARM = (1.0, 0.80, 0.52)
GREEN_LAMP = (0.70, 1.0, 0.62)
GLASS_BLUE = (0.55, 0.66, 1.0)
EXIT_RED = (1.0, 0.18, 0.12)
SCREEN = (0.70, 0.85, 1.0)

# ------------------------------------------------------------------ circulation (map metres; layout vertical[])
HALLS = {"stair_w": (18.8, 258.5, 25.8, 268.5), "stair_e": (51.7, 258.5, 58.7, 268.5),
         "stair_nw": (15.0, 308.4, 22.6, 318.6), "stair_ne": (55.2, 308.4, 62.7, 318.5)}
HALL_LANE = {"stair_w": (3.15, 0.4), "stair_e": (3.15, 0.4), "stair_nw": (3.45, 0.4), "stair_ne": (3.4, 0.4)}
HALL_FIRST = {"stair_w": 266.1, "stair_e": 266.1, "stair_nw": 310.9, "stair_ne": 310.85}   # first riser line
HALL_LEVELS = {"stair_w": FLOORS, "stair_e": FLOORS, "stair_nw": ("F1", "F2", "F3", "F4"),
               "stair_ne": ("F1", "F2", "F3", "F4")}
# the main elevator bank (car A 28.6..31.7, car B 32.1..35.2) + fillers to x 35.6 (the escalator well's west side)
BANK = (28.6, 271.2, 35.6, 274.4)
CAR_A_X = (28.6, 31.7)
CAR_B_X = (32.1, 35.2)
# the east elevator (moved 1.6 m north by the layout) filled down to the east stair hall's north wall
EAST_ELEV = (55.0, 268.5, 58.7, 272.6)
EAST_CAR_Y = (269.0, 272.6)
ADA = (42.0, 271.2, 45.4, 274.2)        # ADA elevator 42.4..45.4 + a filler to the escalator well (F1-F2 only)
ESCALATOR = (35.6, 265.1, 42.0, 275.5)
ESC_LANES = ((35.6, 38.6), (39.0, 42.0))
VOID = (25.8, 258.5, 51.7, 271.2)       # the Plaza Hall (F2 slab hole), 11.4 m tall
ESC_WELL = (35.6, 271.2, 42.0, 275.5)   # F2 slab hole the escalators come up through
VOID_RAIL = [(45.4, 271.2), (51.7, 271.2), (51.7, 268.5)]
F5_CORRIDORS = [(25.8, 264.0), (51.7, 264.0), (51.7, 268.5), (28.6, 268.5), (28.6, 274.4), (52.4, 274.4),
                (52.4, 268.5), (55.0, 268.5), (55.0, 277.4), (11.8, 277.4), (11.8, 274.4), (25.8, 274.4)]
LOBBY_F1 = [(25.8, 258.5), (49.4, 258.5), (49.4, 271.2), (25.8, 271.2)]

NOTES = {
    "scale": "Plan (x, y) 1:1 to the registered UF floor plans (docs/libwest_layout.md 3); floors 6.0 m apart in the "
             "game (real ~4.2 m, estimate): 5.4 m clear for the SM64 camera.",
    "deviations": [
        "Floor-to-floor 6.0 m (real ~4.2 m): camera headroom over 2.3-3.0 m stacks; a floor is not one backflip.",
        "The Plaza Hall: a 25.9 x 12.7 m void over the lobby, 11.4 m tall, behind the real two-storey glass (the real "
        "2nd floor runs up to the glass): the design's 'rotunda' (Act 3 Big Boo) and the night showpiece.",
        "West / east stair halls 7.0 x 10.0 m (real ~3.2 x 7.2 m), NW / NE halls 7.6 x 10.2 m with a roof door onto "
        "the north terrace (only the tower boxes are on the plans); 30 deg switchbacks, 3.15-3.45 m lanes.",
        "Escalators: two static 30 deg ramps (switched off after hours), bottom 2.6 m further in for the spawn.",
        "Stacks 1.2 m deep with 3.2 m / 2.86 m aisles (real compact shelving ~0.6 m, no fixed aisles); the 3.6 m rows "
        "are built 3.0 m (a jump on top fits under the 5.4 m ceiling), end-cap steps, book-cart bridges.",
        "Doors 2.0-2.6 m wide, 2.6 m tall; glass partitions run floor to ceiling, so every room is sealed except "
        "its door gap (no door leaves are modelled in the gaps).",
        "The base roof (z 18) is walkable: west, north and east ROOF TERRACES with 1.1 m parapets, reached by the "
        "F4 terrace doors and the NW / NE stair-hall roof doors.",
        "Floor 5 (staff offices, no plan published) is closed except a corridor ring, the staff break room and the "
        "electrical room; its stair-hall doors are open gaps in the geometry (the layout's 'locked except Acts 4-5' "
        "needs act masks, which static geometry cannot have: the missions add Lua barriers).",
        "Floor 6 reuses floor 4's core; its plaza-face slots become one big view window (Act 1's star).",
        "The main elevators' car A is OUT OF ORDER with its doors open on every floor (a wall-kick shaft, as at "
        "Marston); car B, the east elevator and the ADA elevator are closed.",
        "The coffee counter is unbranded and narrower (x 42.0..51.7; the real Starbucks runs to x 58.3).",
        "Entrance: the revolving door and the north doors are locked after hours; nothing outside is walkable. The "
        "revolving door's drum is centred on the glass line (the layout's spot is 1 m inside it).",
        "The F3 electrical room's south wall moves 0.9 m north (y 267.6 -> 268.5) and the F5 breaker panel to the "
        "electrical room's east wall: the layout put them across the west stair hall's F3 door and in the F5 "
        "electrical room's doorway. Free columns within 2.2 m of a stair-hall door and in the north wing's stack "
        "aisles are left out.",
        "Rolling ladders, Boos, breakers, the coffee cup and the glowing books are mission devices (Lua), not "
        "level geometry; the electrical rooms, the break room and the hide-and-seek spots are in place for them.",
    ],
    "fix_round": [
        "Car A's F1 threshold: a 1.7 x 0.2 m floor (+ a metal sill) in the doorway. K.elevator's thresholds are the "
        "lintel tops of the storey below, so its lowest floor had none, and the BANK hole in the F1 slab left a 0.2 m "
        "strip with no floor (an SM64 invisible wall) that trapped anyone who dropped into the shaft.",
        "Finals-week clutter (visual only): open laptops glowing at about a third of the study seats (each a small "
        "cool light), energy-drink cans, and students asleep on the desks of about one table cluster in six.",
        "The far F3 range-top 1-up moved 1.5 m along its range: it shared the spot with the range top's coin.",
    ],
}


# ================================================================== the layout
def load_layout(path=LAYOUT_PATH):
    with open(path) as f:
        return json.load(f)


def floor_of(layout, fid):
    return next(f for f in layout["floors"] if f["id"] == fid)


def plate_outline(layout, fid):
    """The slab outline of a floor: the whole base for F1-F4 (F4 = tower + roof terraces), the tower above."""
    src = "F1" if fid in ("F1", "F2", "F3", "F4") else "F5"
    return ccw([tuple(p) for p in floor_of(layout, src)["outline_m"]])


def inner_outline(layout, fid):
    """The enclosed (heated) outline of a floor: the base for F1-F3, the tower for F4-F6."""
    return ccw([tuple(p) for p in floor_of(layout, fid)["outline_m"]])


def blocks(fid):
    """Rects that are holes in this floor's slab and built by their own builders (stair halls, shafts)."""
    out = [HALLS["stair_w"], HALLS["stair_e"], BANK, EAST_ELEV]
    if fid in ("F1", "F2", "F3", "F4"):
        out += [HALLS["stair_nw"], HALLS["stair_ne"]]
    if fid in ("F1", "F2"):
        out.append(ADA)
    return out


def oriented_axis(poly):
    """(centre x, y, length, width, facing) of a (possibly diagonal) 4-point prop polygon: local +x runs along its
    longest edge (facing = that edge's compass bearing - 90)."""
    pts = list(poly)
    e = [(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]
    a, b = max(e, key=lambda q: math.dist(*q))
    short = min(math.dist(*q) for q in e)
    cx, cy = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
    bearing = math.degrees(math.atan2(b[0] - a[0], b[1] - a[1]))
    return cx, cy, math.dist(a, b), short, (bearing - 90.0) % 360.0


def axis_aligned(poly):
    return len({round(p[0], 3) for p in poly}) == 2 and len({round(p[1], 3) for p in poly}) == 2


def long_axis(poly):
    x0, y0, x1, y1 = bbox(poly)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w, h = x1 - x0, y1 - y0
    if h >= w:
        return cx, cy, h, w, 90.0
    return cx, cy, w, h, 0.0


class LibWest:
    """The built interior: kit, lighting per group, design anchor points, pickups plan, previews, notes."""

    def __init__(self, layout):
        self.layout = layout
        self.kit = K.Kit()
        self.points = {}
        self.pickups = []
        self.views = []
        self.notes = json.loads(json.dumps(NOTES))
        self.doors = {fid: [] for fid in FLOORS}
        self.locked = {fid: [] for fid in FLOORS}
        self.regions = {}
        self.plates = {fid: plate_outline(layout, fid) for fid in FLOORS}
        self.inners = {fid: inner_outline(layout, fid) for fid in FLOORS}
        self.base = self.inners["F1"]
        self.tower = self.inners["F4"]
        self.glass_lights = []
        self.stack_tops = []
        self.stack_axes = {}                         # stack top name -> its range's long axis (unit map x, y)
        self.props = {fid: [] for fid in FLOORS}      # footprints [(poly, kind, id, height)]
        self.anchors = {}
        self.tags = set()
        self.lighting = {}
        self.stats = {}
        self.lamps = []                              # (fid, x, y, z) desk lamp spots (stats)

    def add(self, prop, x=0.0, y=0.0, z=0.0, facing=0.0, tag=None, group="main"):
        base = tag or prop.kind
        t, n = base, 1
        while t in self.tags:
            n += 1
            t = f"{base}_{n}"
        self.tags.add(t)
        return self.kit.add(prop, x, y, z, facing, tag=t, group=group)

    def anchor(self, name, x, y, z, facing=0.0, **extra):
        self.anchors[name] = dict(pos=(round(x, 3), round(y, 3), round(z, 3)), facing=round(facing % 360.0, 1), **extra)

    # --- floor queries (map metres)
    def inside(self, fid, x, y):
        return pip((x, y), self.inners[fid])

    def on_plate(self, fid, x, y):
        return pip((x, y), self.plates[fid])

    def in_block(self, fid, x, y, m=0.0):
        return any(in_rect((x, y), r, m) for r in blocks(fid))

    def region_at(self, fid, x, y):
        for r in self.regions.get(fid, ()):
            if pip((x, y), r["poly"]):
                return r
        if fid == "F5" and self.inside(fid, x, y) and not self.in_block(fid, x, y):
            return F5_DEFAULT                                  # the closed staff offices (default zone)
        return None

    def solid_at(self, fid, x, y):
        r = self.region_at(fid, x, y)
        return r is not None and r["kind"] == "solid"

    def zone_at(self, fid, x, y):
        for z in floor_of(self.layout, fid)["zones"]:
            if pip((x, y), [tuple(p) for p in z["poly_m"]]):
                return z
        return None

    def walkable(self, fid, x, y):
        """Floor Mario can stand on at (x, y) on floor fid (terraces included on F4)."""
        if not self.on_plate(fid, x, y) or self.in_block(fid, x, y):
            return False
        if fid == "F2" and (in_rect((x, y), VOID) or in_rect((x, y), ESC_WELL)):
            return False
        return not self.solid_at(fid, x, y)

    def terrace(self, fid, x, y):
        return fid == "F4" and self.on_plate(fid, x, y) and not self.inside(fid, x, y)


F5_DEFAULT = {"id": "f5_offices", "poly": [], "type": "staff", "walkable": False, "name": "Staff offices",
              "kind": "solid", "no_door": True}


# ================================================================== regions + doors
def snap_refs(M, fid):
    pts = list(M.inners[fid])
    xs = {p[0] for p in pts} | {v for r in blocks(fid) for v in (r[0], r[2])}
    ys = {p[1] for p in pts} | {v for r in blocks(fid) for v in (r[1], r[3])}
    return sorted(xs), sorted(ys)


def _snap(v, refs, tol):
    best = None
    for r in refs:
        if abs(v - r) <= tol and (best is None or abs(v - r) < abs(v - best)):
            best = r
    return v if best is None else best


def regions_of(M, fid):
    """Enclosed regions of a floor: [{id, poly, kind (glass|wall|solid), walkable, type, no_door}] snapped to
    the outline / blocks (0.45 m) and to each other (0.25 m), plus the synthetic F1 lobby and F5 corridor ring."""
    f = floor_of(M.layout, fid)
    refx, refy = snap_refs(M, fid)
    out = []
    for z in f["zones"]:
        enc, typ, walk = z.get("enclosure", "open"), z["type"], z.get("walkable", True)
        if typ in ("terrace", "atrium_void", "roof_tile") or enc in ("open", "railing", "parapet", "glass_partial"):
            continue
        poly = [(_snap(x, refx, 0.45), _snap(y, refy, 0.45)) for x, y in z["poly_m"]]
        if z["id"] == "f3_electrical":
            poly = [(x, max(y, 268.5)) for x, y in poly]   # clear of the west stair hall's F3 door (NOTES)
        out.append({"id": z["id"], "poly": ccw(poly), "type": typ, "walkable": walk, "name": z.get("label") or z["id"],
                    "kind": "glass" if enc.startswith("glass") else ("wall" if walk else "solid"),
                    "door_facing": z.get("door_facing_deg"), "no_door": False})
    if fid == "F1":
        out.append({"id": "lobby", "poly": ccw(LOBBY_F1), "type": "lobby", "walkable": True, "name": "Lobby",
                    "kind": "wall", "no_door": True})
    if fid == "F5":
        out.append({"id": "f5_corridors", "poly": ccw(F5_CORRIDORS), "type": "open_floor", "walkable": True,
                    "name": "Staff corridor", "kind": "wall", "no_door": True})
    vals_x = sorted({p[0] for r in out for p in r["poly"]})
    vals_y = sorted({p[1] for r in out for p in r["poly"]})

    def cluster(vals, refs):
        rep = {}
        for v in vals:
            s = _snap(v, refs, 0.25)
            if s != v:
                rep[v] = s
                continue
            for k in sorted(set(rep.values())):
                if abs(v - k) <= 0.25:
                    rep[v] = k
                    break
            else:
                rep[v] = v
        return rep
    rx, ry = cluster(vals_x, refx), cluster(vals_y, refy)
    for r in out:
        r["poly"] = ccw([(rx.get(x, x), ry.get(y, y)) for x, y in r["poly"]])
    return out


def _door_rec(fid, r, a, b, head, kind="gap", oid=None):
    a, b = (round(a[0], 3), round(a[1], 3)), (round(b[0], 3), round(b[1], 3))
    c = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L, dx / L
    side = (c[0] + nx * 0.5, c[1] + ny * 0.5)
    if r is not None and pip(side, r["poly"]):
        nx, ny = -nx, -ny
    return {"floor": fid, "room": r["id"] if r else None, "room_name": r["name"] if r else None,
            "type": r["type"] if r else None, "a": a, "b": b, "centre": c, "width": round(L, 2), "head": head,
            "facing": round(math.degrees(math.atan2(nx, ny)) % 360.0, 1), "kind": kind, "id": oid}


def _region_with_edge(M, fid, a, b, tol=0.35):
    """The region one of whose edges carries the segment a-b (snapped onto that edge), or (None, a, b)."""
    horiz = abs(a[1] - b[1]) < 1e-6
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    best = None
    for r in M.regions[fid]:
        for p, q in edges(r["poly"]):
            if horiz != (abs(p[1] - q[1]) < 1e-6):
                continue
            if horiz:
                d = abs(p[1] - my)
                lo, hi = sorted((p[0], q[0]))
                along = mx
            else:
                d = abs(p[0] - mx)
                lo, hi = sorted((p[1], q[1]))
                along = my
            if d > tol or not (lo - 0.05 <= along <= hi + 0.05):
                continue
            if best is None or d < best[0]:
                best = (d, r, p[1] if horiz else p[0])
    if best is None:
        return None, a, b
    _, r, v = best
    return (r, (a[0], v), (b[0], v)) if horiz else (r, (v, a[1]), (v, b[1]))


def _free_point(M, fid, x, y, own=None):
    if not M.inside(fid, x, y) or M.in_block(fid, x, y, 0.1):
        return False
    if fid == "F2" and (in_rect((x, y), VOID, 0.3) or in_rect((x, y), ESC_WELL, 0.3)):
        return False
    r = M.region_at(fid, x, y)
    if r is not None and r is not own:
        return False
    for poly, kind, pid, h in M.props[fid]:
        if pip((x, y), poly):
            return False
    return True


def plan_doors(M):
    """Door gaps of every enclosed walkable region: the layout's room openings (door / door_open = a gap,
    door_locked = a closed door decal), then an automatic door for a walkable room the layout gives none."""
    for fid in FLOORS:
        f = floor_of(M.layout, fid)
        given = set()
        for o in f.get("openings", []):
            a, b = tuple(o["a_m"]), tuple(o["b_m"])
            if seg_point_dist(a, *_outline_edge_near(M, fid, a)) < 0.2 and \
                    seg_point_dist(b, *_outline_edge_near(M, fid, b)) < 0.2:
                continue                                   # an exterior opening (exterior walls build it)
            if "ada" in o["id"]:
                continue                                   # the ADA elevator's doors (decals on its block)
            r, a2, b2 = _region_with_edge(M, fid, a, b)
            if r is None:
                if o["type"] != "door_open":               # an open side of an open zone (Neuharth): nothing
                    M.notes.setdefault("unplaced_openings", []).append(f"{fid} {o['id']}")
                continue
            given.add(r["id"])
            if o["type"] == "door_locked":
                M.locked[fid].append(_door_rec(fid, r, a2, b2, DOOR_H, "locked", o["id"]))
            else:
                M.doors[fid].append(_door_rec(fid, r, a2, b2, DOOR_H, "gap", o["id"]))
        cent = CENTER
        for r in M.regions[fid]:
            if r["kind"] == "solid" or r.get("no_door") or r["id"] in given:
                continue
            want = STUDY_DOOR_W if r["type"] == "group_study" else ROOM_DOOR_W
            best = None
            for p, q in edges(r["poly"]):
                Ls = math.dist(p, q)
                if Ls < 1.4:
                    continue
                dx, dy = (q[0] - p[0]) / Ls, (q[1] - p[1]) / Ls
                ox, oy = dy, -dx
                run, runs = [], []
                s = 0.25
                while s <= Ls - 0.25 + 1e-6:
                    x, y = p[0] + dx * s + ox * 0.7, p[1] + dy * s + oy * 0.7
                    x2, y2 = p[0] + dx * s + ox * 1.6, p[1] + dy * s + oy * 1.6
                    if _free_point(M, fid, x, y) and _free_point(M, fid, x2, y2):
                        run.append(s)
                    else:
                        if run:
                            runs.append((run[0], run[-1]))
                        run = []
                    s += 0.1
                if run:
                    runs.append((run[0], run[-1]))
                for r0, r1 in runs:
                    ln = r1 - r0
                    if ln < 1.3:
                        continue
                    mx, my = p[0] + dx * (r0 + r1) / 2, p[1] + dy * (r0 + r1) / 2
                    toward = math.hypot(cent[0] - mx, cent[1] - my) or 1.0
                    score = min(ln, 4.0) + 1.5 * ((cent[0] - mx) * ox + (cent[1] - my) * oy) / toward
                    if best is None or score > best[0]:
                        w = min(want, ln - 0.1)
                        c = (r0 + r1) / 2
                        best = (score, (p[0] + dx * (c - w / 2), p[1] + dy * (c - w / 2)),
                                (p[0] + dx * (c + w / 2), p[1] + dy * (c + w / 2)))
            if best is None:
                M.notes.setdefault("sealed_rooms", []).append(f"{fid} {r['id']}")
                continue
            M.doors[fid].append(_door_rec(fid, r, best[1], best[2], DOOR_H, "gap", f"auto_{r['id']}"))


def _outline_edge_near(M, fid, p):
    best = None
    for a, b in edges(M.inners[fid]):
        d = seg_point_dist(p, a, b)
        if best is None or d < best[0]:
            best = (d, a, b)
    return best[1], best[2]


# ================================================================== partitions
def build_partitions(M, fid, P):
    """Interior walls between enclosed regions and the open floor (glass or drywall) with the door gaps; the
    pieces on the outline and on stair halls / shafts are left to those. A wall between two closed (solid)
    regions is not built (nobody sees it)."""
    regions = M.regions[fid]
    buckets, diag = {}, []
    for r in regions:
        for p, q in edges(r["poly"]):
            if abs(p[1] - q[1]) < 1e-3:
                buckets.setdefault(("h", round(p[1], 3)), []).append((min(p[0], q[0]), max(p[0], q[0])))
            elif abs(p[0] - q[0]) < 1e-3:
                buckets.setdefault(("v", round(p[0], 3)), []).append((min(p[1], q[1]), max(p[1], q[1])))
            else:
                diag.append((p, q))
    rects = list(blocks(fid)) + ([ESCALATOR] if fid == "F1" else [])
    blockers = list(edges(M.inners[fid])) + [e for r in rects for e in edges(rect_poly(r))]
    if fid == "F1":
        blockers.append(((ESCALATOR[0], 271.2), (ESCALATOR[2], 271.2)))     # the escalators pass the lobby line
    n_glass = n_solid = 0
    for (ax, v), ivs in sorted(buckets.items()):
        ivs = intervals_union(ivs)
        cut = []
        for p, q in blockers:
            if ax == "h" and abs(p[1] - q[1]) < 1e-3 and abs(p[1] - v) < 0.08:
                cut.append((min(p[0], q[0]), max(p[0], q[0])))
            if ax == "v" and abs(p[0] - q[0]) < 1e-3 and abs(p[0] - v) < 0.08:
                cut.append((min(p[1], q[1]), max(p[1], q[1])))
        ivs = intervals_subtract(ivs, cut)
        for s0, s1 in ivs:
            cuts = split_line(s0, s1, 0.25)
            pieces = []
            for u0, u1 in zip(cuts, cuts[1:]):
                um = (u0 + u1) / 2
                pa, pb = ((um, v + 0.15), (um, v - 0.15)) if ax == "h" else ((v + 0.15, um), (v - 0.15, um))
                ra, rb = M.region_at(fid, *pa), M.region_at(fid, *pb)
                outa = not M.inside(fid, *pa) or M.in_block(fid, *pa)
                outb = not M.inside(fid, *pb) or M.in_block(fid, *pb)
                if ra is rb or (ra is None and rb is None) or outa or outb:
                    k = None
                elif ra is not None and rb is not None and ra["kind"] == rb["kind"] == "solid":
                    k = None
                elif any(r is not None and r["kind"] in ("solid", "wall") for r in (ra, rb)):
                    k = "solid"
                else:
                    k = "glass"
                if pieces and pieces[-1][2] == k:
                    pieces[-1][1] = u1
                else:
                    pieces.append([u0, u1, k])
            for u0, u1, k in pieces:
                if k is None or u1 - u0 < 0.1:
                    continue
                a = (u0, v) if ax == "h" else (v, u0)
                b = (u1, v) if ax == "h" else (v, u1)
                doors = []
                for d in M.doors[fid]:
                    (dax, day), (dbx, dby) = d["a"], d["b"]
                    if ax == "h" and abs(day - v) < 0.08 and abs(dby - v) < 0.08:
                        d0, d1 = sorted((dax, dbx))
                    elif ax == "v" and abs(dax - v) < 0.08 and abs(dbx - v) < 0.08:
                        d0, d1 = sorted((day, dby))
                    else:
                        continue
                    if d1 <= u0 or d0 >= u1:
                        continue
                    doors.append((d0 - u0, d1 - u0, d["head"]))
                thin_partition(P.visual, P.collision, a, b, 0.0, CLEAR, k, doors, solid_mat="int_drywall")
                if k == "glass":
                    n_glass += 1
                else:
                    n_solid += 1
    for p, q in diag:
        thin_partition(P.visual, P.collision, p, q, 0.0, CLEAR, "solid")
    # locked doors: a closed door leaf on both faces of the partition (visual only)
    for d in M.locked[fid]:
        locked_door_decal(P, d)
    M.stats.setdefault("partitions", {})[fid] = {"glass": n_glass, "solid": n_solid}


def locked_door_decal(P, d):
    a, b = d["a"], d["b"]
    L = math.dist(a, b)
    if L < 0.3:
        return
    dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    nx, ny = -dy, dx
    for sgn in (1, -1):
        o = sgn * 0.13
        pa = (a[0] + nx * o, a[1] + ny * o)
        pb = (b[0] + nx * o, b[1] + ny * o)
        hint = (nx * sgn, ny * sgn, 0.0)
        P.visual.poly([(pa[0], pa[1], 0.0), (pb[0], pb[1], 0.0), (pb[0], pb[1], 2.2), (pa[0], pa[1], 2.2)],
                      "int_wood_dark", normal_hint=hint, ao=0.9)
        hx, hy = pa[0] + dx * L * 0.85 + nx * sgn * 0.02, pa[1] + dy * L * 0.85 + ny * sgn * 0.02
        P.visual.box(hx - 0.04, hy - 0.04, 1.0, hx + 0.04, hy + 0.04, 1.08, "int_metal", faces="+x-x+y-y+z")


# ================================================================== small night props
def desk_lamp(color=WARM, shade_tint=None, light=True, radius=3.2, strength=0.55):
    """Desk / banker's lamp (base centre origin on the desk top): base, stem, a glowing shade. Adds a Light."""
    P = K.Prop("desk_lamp", col_closed=True)
    V = P.visual
    V.box(-0.08, -0.06, 0.0, 0.08, 0.06, 0.03, "int_metal", faces="+z", tint=(0.55, 0.5, 0.4))
    V.box(-0.012, -0.012, 0.03, 0.012, 0.012, 0.36, "int_metal", faces="+x-y", tint=(0.6, 0.55, 0.45))
    st = shade_tint or tuple(min(1.0, c * 1.0) for c in color)
    V.box(-0.16, -0.08, 0.34, 0.16, 0.08, 0.44, "int_light", faces=K.BOX_ALL, tint=st, glow=True)
    if light:
        P.lights.append(K.Light((0.0, 0.0, 0.55), radius=radius, strength=strength, color=color))
    return P


def laptop(light=True):
    """An open laptop left on a desk at 3 a.m. (origin: the desk top under its middle; the user sits at -y):
    a dark base and a tilted lid whose screen glows toward the user, with a small cool light. Visual only."""
    P = K.Prop("laptop", col_closed=True)
    V = P.visual
    V.box(-0.17, -0.12, 0.0, 0.17, 0.12, 0.02, "int_plastic", faces="+z+y-y+x-x", tint=(0.55, 0.56, 0.6))
    a, b = (0.12, 0.02), (0.19, 0.25)                 # the lid: hinge (y, z) -> top edge, tilted back
    V.poly([(0.16, a[0], a[1]), (-0.16, a[0], a[1]), (-0.16, b[0], b[1]), (0.16, b[0], b[1])], "int_plastic",
           tint=(0.5, 0.5, 0.55), normal_hint=(0, 1, 0.3))
    V.poly([(-0.15, a[0] - 0.004, a[1] + 0.01), (0.15, a[0] - 0.004, a[1] + 0.01), (0.15, b[0] - 0.004, b[1] - 0.01),
            (-0.15, b[0] - 0.004, b[1] - 0.01)], "int_monitor", uvs=K.ONCE, glow=True, tint=SCREEN,
           normal_hint=(0, -1, 0.3))
    if light:
        P.lights.append(K.Light((0.0, -0.3, 0.35), radius=1.5, strength=0.14, color=SCREEN))
    return P


def drink_can(tint):
    """An energy-drink can (0.066 x 0.066 x 0.12 m) on a desk top. Visual only."""
    P = K.Prop("drink_can", col_closed=True)
    P.visual.box(-0.033, -0.033, 0.0, 0.033, 0.033, 0.12, "int_plastic", faces="+x-x+y-y+z", tint=tint)
    return P


def sleeping_student(fabric, hood=(1.0, 1.0, 1.0)):
    """A finals-week all-nighter asleep on the desk (origin: the table edge under the student's middle, the table
    running toward +y, its top at table_h; the chair behind at -y): hips on the chair, a hunched hoodie, arms
    folded on the table, the head down on them. Low poly, vertex-coloured, visual only (no collision)."""
    P = K.Prop("sleeping_student", col_closed=True)
    V = P.visual
    th, sh = K.REAL["table_h"], K.REAL["seat_h"]
    skin, hair = (0.92, 0.74, 0.6), (0.3, 0.24, 0.2)
    V.box(-0.17, -0.5, sh, 0.17, -0.2, sh + 0.18, "int_fabric_blue", faces="+z+x-x+y-y", tint=(0.55, 0.6, 0.75))
    V.box(-0.2, -0.36, sh + 0.16, 0.2, -0.06, th + 0.24, fabric, faces="+z+x-x-y", tint=hood)        # hoodie
    V.box(-0.26, -0.08, th, 0.26, 0.2, th + 0.11, fabric, faces="+z+x-x+y-y", tint=hood)             # folded arms
    V.box(-0.11, -0.04, th + 0.11, 0.11, 0.2, th + 0.3, "int_drywall", faces="+x-x+y-y", tint=skin)  # head
    V.box(-0.115, -0.07, th + 0.2, 0.115, 0.21, th + 0.32, "int_plastic", faces="+z+x-x-y+y", tint=hair)
    return P


CAN_TINTS = ((0.35, 0.9, 0.4), (0.3, 0.55, 1.0), (1.0, 0.85, 0.3), (0.95, 0.35, 0.35))


def table_with_lamps(L, W, seat="int_fabric_blue", lamp_color=WARM, shade=None, rng=None, finals=True):
    """The layout's table_cluster as low-poly study tables (Marston's lp_table) with desk lamps. finals: the
    finals-week clutter of a 3 a.m. library (fix round: the fun review's "it reads closed, not after dark"):
    open laptops glowing at about a third of the seats, energy-drink cans, and on about a sixth of the clusters a student
    asleep on the desk. Placed by a fixed rule of the cluster's size and the seat (the lamp rng is untouched)."""
    P = K.Prop("table_cluster", col_closed=True)
    n = max(1, int(L // 2.1))
    rows = 2 if W >= 3.4 else 1
    key = int(round(L * 10)) + int(round(W * 10))
    for i in range(n):
        x = -L / 2 + (i + 0.5) * L / n
        for r in range(rows):
            y = 0.0 if rows == 1 else (-W / 4 if r == 0 else W / 4)
            tl = min(1.83, L / n - 0.2)
            P.merge(MH.lp_table(tl, 0.91, chairs_per_side=2, seat=seat), x, y, 0.0, 0.0)
            on = rng is None or rng.random() < 0.85
            lamp_sx = 1 if (i + r) % 2 else -1
            P.merge(desk_lamp(lamp_color, shade, light=on), x + (tl / 2 - 0.3) * lamp_sx, y,
                    K.REAL["table_h"], 0.0)
            if not finals:
                continue
            asleep = i == 0 and r == 0 and key % 3 == 1
            for k in range(2):                                 # lp_table's chairs: 2 a side
                sx = -tl / 2 + (k + 0.5) * tl / 2
                if abs(sx - (tl / 2 - 0.3) * lamp_sx) < 0.36:
                    sx = (tl / 2 - 0.3 - 0.36) * lamp_sx       # clear of the lamp (laptop 0.17 + shade 0.16)
                for side, f in ((-1, 0.0), (1, 180.0)):        # the user sits at y = side * (0.455 + ...)
                    s = (i * 4 + r * 8 + k * 2 + (side > 0)) + key
                    if asleep and side < 0 and sx * lamp_sx < 0:   # the seat at the far end from the lamp
                        P.merge(sleeping_student(("int_fabric_orange", "int_fabric_green", "int_fabric_blue")[key % 3]),
                                x + sx, y - 0.455, 0.0, 0.0)
                        continue
                    if s % 3 == 0:
                        P.merge(laptop(), x + sx, y + side * 0.2, K.REAL["table_h"], f)
                    if s % 4 == 1:
                        P.merge(drink_can(CAN_TINTS[s % len(CAN_TINTS)]), x + sx + 0.24, y + side * 0.3,
                                K.REAL["table_h"], 0.0)
    return P


def pendant(drop, radius=0.32, color=WARM):
    """A globe pendant lamp hanging `drop` m from the ceiling (origin = the ceiling point)."""
    P = K.Prop("pendant", col_closed=True)
    V = P.visual
    V.box(-0.01, -0.01, -drop + radius, 0.01, 0.01, 0.0, "int_metal", faces="+x-x+y-y", tint=(0.4, 0.4, 0.4))
    n = 8
    zc = -drop
    pts = [(radius * math.cos(2 * math.pi * k / n), radius * math.sin(2 * math.pi * k / n)) for k in range(n)]
    for k in range(n):
        a, b = pts[k], pts[(k + 1) % n]
        V.poly([(a[0], a[1], zc - radius * 0.7), (b[0], b[1], zc - radius * 0.7), (b[0], b[1], zc + radius * 0.7),
                (a[0], a[1], zc + radius * 0.7)], "int_light", glow=True, tint=color,
               normal_hint=((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 0.0))
    V.poly([(x, y, zc - radius * 0.7) for x, y in reversed(pts)], "int_light", glow=True, tint=color)
    P.lights.append(K.Light((0.0, 0.0, zc - 0.6), radius=6.5, strength=0.42, color=color))
    return P


def exit_sign():
    """Red EXIT sign over a door (local: the wall plane y = 0, faces +y), glowing, with a small red light."""
    P = K.Prop("exit_sign", col_closed=True)
    P.visual.box(-0.32, 0.0, 0.0, 0.32, 0.08, 0.2, "int_light", faces="+y+x-x+z-z", tint=EXIT_RED, glow=True)
    P.visual.box(-0.22, 0.081, 0.06, 0.22, 0.082, 0.14, "int_light", faces="+y", tint=(1.0, 0.72, 0.66), glow=True)
    P.lights.append(K.Light((0.0, 0.6, -0.3), radius=2.6, strength=0.22, color=EXIT_RED))
    return P


def troffer(on, radius=7.0, strength=0.24):
    """A 2' x 4' troffer: lit (glowing + a Light) or switched off for the night (dark panel)."""
    P = K.Prop("troffer", col_closed=True)
    z = -0.012
    if on:
        P.visual.poly([(-0.3, -0.6, z), (-0.3, 0.6, z), (0.3, 0.6, z), (0.3, -0.6, z)], "int_light",
                      uvs=[(0, 0), (0, 1), (1, 1), (1, 0)], glow=True, tint=(0.92, 0.9, 0.82))
        P.lights.append(K.Light((0.0, 0.0, -0.5), radius=radius, strength=strength, color=(1.0, 0.95, 0.85)))
    else:
        P.visual.poly([(-0.3, -0.6, z), (-0.3, 0.6, z), (0.3, 0.6, z), (0.3, -0.6, z)], "int_light",
                      uvs=[(0, 0), (0, 1), (1, 1), (1, 0)], tint=(0.55, 0.57, 0.62))
    return P


def screen_prop(w, h, z0, tint=SCREEN, frame="int_plastic", depth=0.06, mat="int_monitor"):
    """A wall screen (local wall plane y = 0, faces +y): frame + glowing panel."""
    P = K.Prop("screen", col_closed=True)
    P.visual.box(-w / 2, 0.0, z0, w / 2, depth, z0 + h, frame, faces="+y+x-x+z-z")
    P.visual.poly(K.front_quad(-w / 2 + 0.05, w / 2 - 0.05, depth + 0.002, z0 + 0.05, z0 + h - 0.05), mat,
                  uvs=K.ONCE, glow=True, tint=tint)
    P.lights.append(K.Light((0.0, 1.0, z0 + h / 2), radius=4.0, strength=0.22, color=tint))
    return P


def range_prop_lw(L, W, h, seed, mobile=False):
    """Marston's range (end cap steps toward local -x) + compact-shelving floor rails for mobile ranges."""
    P, tops = MH.range_prop(L, W, h, seed)
    if mobile:
        for sy in (-W / 2 - 0.12, W / 2 + 0.12):
            P.visual.box(-L / 2 - 0.3, sy - 0.03, 0.0, L / 2 + 0.3, sy + 0.03, 0.012, "int_metal", faces="+z+y-y",
                         tint=(0.6, 0.6, 0.62))
        P.visual.box(L / 2 + 0.02, -0.18, 0.95, L / 2 + 0.06, 0.18, 1.15, "int_metal", faces="+x+y-y+z",
                     tint=(0.75, 0.75, 0.78))          # the crank wheel hub at the aisle end
    return P, tops


def revolving_door(r=1.6, h=3.0):
    """The locked revolving door: a glass drum with a metal canopy and four wings (closed collision)."""
    P = K.Prop("revolving_door", col_closed=True)
    V, C = P.visual, P.collision
    n = 12
    pts = [(r * math.cos(2 * math.pi * (k + 0.5) / n), r * math.sin(2 * math.pi * (k + 0.5) / n)) for k in range(n)]
    for k in range(n):
        a, b = pts[k], pts[(k + 1) % n]
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        if abs(mid[0]) < r * 0.55:                    # the two open sides (the drum's mouths) stay open visually
            continue
        V.wall(a, b, 0.0, h, "int_glass", ao=1.0)
        V.wall(b, a, 0.0, h, "int_glass", ao=1.0)
    V.prism(pts, h, h + 0.35, "int_metal", top="int_metal", bottom="int_metal", tint=(0.6, 0.62, 0.66))
    for k in range(4):
        a = math.radians(20 + 90 * k)
        V.box(-0.03, 0.0, 0.02, 0.03, r - 0.05, h - 0.05, "int_glass", faces="+x-x", ao=1.0)
        V.polys[-2:] = [K.Poly([(p[0] * math.cos(a) - p[1] * math.sin(a), p[0] * math.sin(a) + p[1] * math.cos(a), p[2])
                                for p in q.pts], q.mat, q.uvs, q.ao, q.tint, q.glow) for q in V.polys[-2:]]
    V.box(-0.06, -0.06, 0.0, 0.06, 0.06, h, "int_metal", faces="+x-x+y-y")
    K.col_prism(C, pts, 0.0, h + 0.35, K.COL_NOCAM)
    return P


def security_gates(x0, x1, y, h=1.0, lanes=3):
    """Exit / security gate pedestals across the top of the escalators (walk-through lanes, glass flaps open)."""
    P = K.Prop("security_gates", col_closed=True)
    n = lanes + 1
    for i in range(n):
        x = x0 + 0.15 + (x1 - x0 - 0.3) * i / (n - 1)
        P.visual.box(x - 0.12, y - 0.35, 0.0, x + 0.12, y + 0.35, h, "int_metal", faces="+x-x+y-y+z",
                     tint=(0.7, 0.72, 0.76))
        P.visual.box(x - 0.13, y - 0.36, h - 0.06, x + 0.13, y + 0.36, h - 0.04, "int_light", faces="+x-x+y-y+z",
                     tint=(0.3, 0.9, 0.45), glow=True)
        K.col_box(P.collision, x - 0.12, y - 0.35, 0.0, x + 0.12, y + 0.35, h, K.COL_NOCAM)
    return P


def bike_desk():
    """Fitness bike desk (local: centred, faces +y): a frame, a seat and a small desk with a lamp."""
    P = K.Prop("bike_desk", col_closed=True)
    V = P.visual
    V.box(-0.25, -0.55, 0.0, 0.25, 0.55, 0.06, "int_plastic", faces=K.BOX_ALL[:5])
    V.box(-0.05, -0.35, 0.06, 0.05, -0.25, 0.85, "int_metal", faces="+x-x+y-y")
    V.box(-0.15, -0.45, 0.85, 0.15, -0.2, 0.92, "int_fabric_blue", faces=K.BOX_ALL[:5])
    V.box(-0.4, 0.15, 0.95, 0.4, 0.6, 1.0, "int_wood", faces=K.BOX_ALL)
    V.box(-0.04, 0.3, 0.06, 0.04, 0.4, 0.95, "int_metal", faces="+x-x+y-y")
    K.col_box(P.collision, -0.4, -0.55, 0.0, 0.4, 0.6, 1.0, K.COL_NOCAM)
    P.merge(desk_lamp(light=False), 0.25, 0.45, 1.0, 0.0)
    return P


def lockers(L, W, h):
    P = K.Prop("lockers", col_closed=True)
    V = P.visual
    V.box(-L / 2, -W / 2, 0.0, L / 2, W / 2, h, "int_metal", faces=K.BOX_ALL[:5], tint=(0.55, 0.62, 0.78))
    n = max(1, int(L / 0.4))
    for i in range(n + 1):
        x = -L / 2 + i * L / n
        V.box(x - 0.01, W / 2, 0.05, x + 0.01, W / 2 + 0.01, h - 0.05, "int_plastic", faces="+y")
    K.col_box(P.collision, -L / 2, -W / 2, 0.0, L / 2, W / 2, h, K.COL_NOCAM)
    P.anchor("top", 0.0, 0.0, h)
    return P


def rooftop_unit(L, W, h):
    P = K.Prop("rooftop_unit", col_closed=True)
    V = P.visual
    V.box(-L / 2, -W / 2, 0.0, L / 2, W / 2, h, "metal_gray", faces=K.BOX_ALL[:4], mats={"+z": "int_metal"})
    V.poly([(-L / 2, -W / 2, h), (L / 2, -W / 2, h), (L / 2, W / 2, h), (-L / 2, W / 2, h)], "int_metal")
    for sx in (-L / 4, L / 4):
        V.poly([(sx - 0.6, -0.6, h + 0.01), (sx + 0.6, -0.6, h + 0.01), (sx + 0.6, 0.6, h + 0.01),
                (sx - 0.6, 0.6, h + 0.01)], "int_rail_bars", uvs=[(0, 0), (1.2, 0), (1.2, 1.2), (0, 1.2)])
    V.box(-L / 2 + 0.2, W / 2, 0.4, -L / 2 + 0.5, W / 2 + 0.02, 0.5, "int_light", faces="+y", glow=True,
          tint=(0.2, 1.0, 0.3))
    K.col_box(P.collision, -L / 2, -W / 2, 0.0, L / 2, W / 2, h, K.COL)
    P.anchor("top", 0.0, 0.0, h)
    return P


def small_box(kind, w, d, h, mat, top=None, tint=None, glow_face=None, col=True):
    P = K.Prop(kind, col_closed=True)
    P.visual.box(-w / 2, -d / 2, 0.0, w / 2, d / 2, h, mat, faces=K.BOX_ALL[:5], mats={"+z": top} if top else None,
                 tint=tint)
    if glow_face:
        P.visual.poly(K.front_quad(-w / 2 + 0.06, w / 2 - 0.06, d / 2 + 0.003, h * 0.55, h - 0.08), "int_monitor",
                      uvs=K.ONCE, glow=True, tint=glow_face)
    if col:
        K.col_box(P.collision, -w / 2, -d / 2, 0.0, w / 2, d / 2, h, K.COL_NOCAM)
    return P


def breaker_panel():
    """A grey electrical panel on a wall (local: wall plane y = 0, faces +y) with a red status light."""
    P = K.Prop("breaker_panel", col_closed=True)
    P.visual.box(-0.45, 0.0, 0.6, 0.45, 0.18, 2.0, "int_metal", faces="+y+x-x+z-z", tint=(0.62, 0.64, 0.66))
    for k in range(4):
        z = 0.85 + k * 0.28
        P.visual.box(-0.35, 0.18, z, 0.35, 0.19, z + 0.16, "int_plastic", faces="+y", tint=(0.35, 0.35, 0.38))
    P.visual.box(0.28, 0.19, 1.85, 0.36, 0.2, 1.93, "int_light", faces="+y", tint=(1.0, 0.2, 0.15), glow=True)
    K.col_box(P.collision, -0.45, 0.0, 0.6, 0.45, 0.18, 2.0, K.COL_NOCAM, bottom=True)
    return P


def sloped_block(V, C, x0, x1, profile, mat="int_metal", top_mat=None, col_mat=K.COL, tint=None):
    """A block between x0 and x1 whose top follows profile [(y, z)] (y increasing), bottom at z = 0: escalator
    dividers. Closed collision (no bottom)."""
    tm = top_mat or mat
    ys = [p[0] for p in profile]
    for (ya, za), (yb, zb) in zip(profile, profile[1:]):
        V.poly([(x0, ya, za), (x1, ya, za), (x1, yb, zb), (x0, yb, zb)], tm, normal_hint=(0, 0, 1), tint=tint)
        C.poly([(x0, ya, za), (x1, ya, za), (x1, yb, zb), (x0, yb, zb)], col_mat, normal_hint=(0, 0, 1))
    for x, sx in ((x0, -1), (x1, 1)):
        side = [(x, ys[0], 0.0), (x, ys[-1], 0.0)] + [(x, y, z) for y, z in reversed(profile)]
        V.poly(side, mat, normal_hint=(sx, 0, 0), tint=tint)
        C.poly(side, col_mat, normal_hint=(sx, 0, 0))
    for (y, z), sy in ((profile[0], -1), (profile[-1], 1)):
        q = [(x0, y, 0.0), (x1, y, 0.0), (x1, y, z), (x0, y, z)]
        V.poly(q, mat, normal_hint=(0, sy, 0), tint=tint)
        C.poly(q, col_mat, normal_hint=(0, sy, 0))


# ================================================================== floors
def finish(M, fid, x, y):
    """Floor material (material, tint) at map (x, y) on floor fid, or None (closed / outside)."""
    if M.terrace(fid, x, y):
        return ("concrete", (0.86, 0.86, 0.9))
    if not M.walkable(fid, x, y):
        return None
    if fid == "F1" and pip((x, y), LOBBY_F1):
        if in_rect((x, y), (25.8, 258.5, 35.6, 271.2)):
            return ("int_wood", (0.92, 0.80, 0.66))          # cafe
        return ("int_floor_tile", TERRAZZO)
    z = M.zone_at(fid, x, y)
    typ = z["type"] if z else "open_floor"
    zid = z["id"] if z else ""
    if typ in ("lobby", "vestibule") or zid == "f2_balcony":
        return ("int_floor_tile", TERRAZZO)
    if fid == "F5":
        return ("int_floor_tile", (0.78, 0.78, 0.8))
    if typ == "cafe":
        return ("int_wood", (0.9, 0.78, 0.62))
    if typ == "group_study":
        return ("int_carpet_accent", ACCENT_TINT[fid])
    if typ in ("reading_room", "staff_lounge"):
        t = CARPET_TINT[fid]
        return ("int_carpet", (t[0], t[1] * 0.9, t[2] * 0.85))
    if typ in ("electrical_room", "studio"):
        return ("int_stone", (0.8, 0.8, 0.82))
    if typ in ("classroom", "computer_lab"):
        t = CARPET_TINT[fid]
        return ("int_carpet", (t[0] * 0.95, t[1] * 0.95, t[2]))
    # elevator lobbies: terrazzo in front of the main bank (every floor)
    if 28.0 <= x <= 36.2 and 274.4 <= y <= 277.4:
        return ("int_floor_tile", TERRAZZO)
    return ("int_carpet", CARPET_TINT[fid])


def window_openings(M, fid, a, b, s_keep):
    """Openings of the outline edge a->b (CCW): the layout windows and doors on it (s along a->b)."""
    f = floor_of(M.layout, fid)
    L = math.dist(a, b)
    dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    ops, doors = [], []
    for o in f.get("openings", []):
        pa, pb = tuple(o["a_m"]), tuple(o["b_m"])
        if seg_point_dist(pa, a, b) > 0.15 or seg_point_dist(pb, a, b) > 0.15:
            continue
        s0 = (pa[0] - a[0]) * dx + (pa[1] - a[1]) * dy
        s1 = (pb[0] - a[0]) * dx + (pb[1] - a[1]) * dy
        s0, s1 = sorted((s0, s1))
        kind = "locked" if o["type"] == "door_locked" and not o.get("revolving") else "door"
        h = 3.0 if o.get("revolving") else DOOR_H                 # the drum (a prop) closes the revolving door
        if o.get("revolving"):
            s0, s1 = s0 - 0.2, s1 + 0.2
        doors.append({"s0": s0, "s1": s1, "z0": 0.0, "z1": h, "kind": kind, "id": o["id"]})
    for w in f.get("windows", []):
        pa, pb = tuple(w["a_m"]), tuple(w["b_m"])
        wd = (pb[0] - pa[0], pb[1] - pa[1])
        wl = math.hypot(*wd) or 1.0
        cross = (wd[0] * dy - wd[1] * dx) / wl
        kind = w.get("kind", "ribbon")
        tall = kind in ("storefront", "curtain_wall", "view")
        sill = float(w["sill_m"])
        head = min(float(w["head_m"]), CLEAR - (0.05 if tall else 0.25))
        if abs(cross) < 0.05:
            dline = abs((pa[0] - a[0]) * (-dy) + (pa[1] - a[1]) * dx)
            if dline > 0.35:
                continue
            s0 = (pa[0] - a[0]) * dx + (pa[1] - a[1]) * dy
            s1 = (pb[0] - a[0]) * dx + (pb[1] - a[1]) * dy
            s0, s1 = sorted((s0, s1))
            s0, s1 = max(s0, 0.2), min(s1, L - 0.2)
            if s1 - s0 > 0.6:
                ops.append({"s0": s0, "s1": s1, "z0": sill, "z1": head, "kind": "window", "id": w["id"], "wk": kind})
        else:
            bx = bbox([pa, pb])
            if in_rect(a, bx, 0.35) and in_rect(b, bx, 0.35) and L > 0.9:
                ops.append({"s0": 0.2, "s1": L - 0.2, "z0": sill, "z1": head, "kind": "window", "id": w["id"],
                            "wk": kind})
    out = []
    for o in ops:
        for k0, k1 in s_keep:
            for s0, s1 in intervals_subtract([(max(o["s0"], k0 + 0.2), min(o["s1"], k1 - 0.2))],
                                             [(d["s0"] - 0.3, d["s1"] + 0.3) for d in doors]):
                if s1 - s0 <= 0.6:
                    continue
                if o["wk"] in ("slot", "slot_band"):
                    # the tower's narrow window slots between brick piers (2005 photo, S23)
                    n = max(1, int((s1 - s0 + 0.7) // 1.6))
                    span = (s1 - s0 - (n - 1) * 0.7) / n
                    for i in range(n):
                        a0 = s0 + i * (span + 0.7)
                        out.append(dict(o, s0=a0, s1=a0 + span))
                else:
                    out.append(dict(o, s0=s0, s1=s1))
    for d in doors:
        if any(k0 - 0.05 <= d["s0"] and d["s1"] <= k1 + 0.05 for k0, k1 in s_keep):
            out.append(d)
    return out


def _keep_runs(test, Ls, step=0.05):
    keep, run, s = [], None, 0.0
    while s <= Ls + 1e-6:
        ok = test(s)
        if ok and run is None:
            run = s
        if not ok and run is not None:
            keep.append((run, s))
            run = None
        s += step
    if run is not None:
        keep.append((run, Ls))
    return [(k0, k1) for k0, k1 in keep if k1 - k0 > 0.1]


def build_floor(M, fid):
    """One floor in its local frame (z 0 = the floor top, placed at Z[fid], group fid): the slab under it, the
    outline walls with windows / doors, the F4 terrace parapets, partitions, props, columns, lights, signs."""
    L = M.layout
    z = Z[fid]
    P = K.Prop(f"floor_{fid}", col_closed=False)
    V, C = P.visual, P.collision
    ol = M.inners[fid]
    idx = FLOORS.index(fid)
    below = FLOORS[idx - 1] if idx > 0 else None
    # ---------------- slab (this floor's floor; its bottom is the ceiling of the floor below)
    cover = [M.plates[fid]]
    holes = list(blocks(fid))
    edge_holes = []
    if fid == "F2":
        holes += [VOID, ESC_WELL]
        edge_holes.append(VOID)
    zone_lines = ([p[0] for zz in floor_of(L, fid)["zones"] for p in zz["poly_m"]] + [25.8, 35.6, 49.4, 42.0],
                  [p[1] for zz in floor_of(L, fid)["zones"] for p in zz["poly_m"]] + [271.2, 274.4, 277.4])

    def top_fn(x, y):
        return finish(M, fid, x, y)

    def top_col(x, y):
        return M.walkable(fid, x, y)

    def bot_fn(x, y):
        if below is None:
            return None
        if M.on_plate(below, x, y) and M.solid_at(below, x, y):
            return None
        return ("int_ceiling", (0.92, 0.92, 0.95))

    bot_col = (lambda x, y: True) if below else None
    # visual: cut at every zone line (floor finishes); collision: one floor over the whole plate minus the holes
    # (cells cut only by the holes and the outline, so the floor stays big; a floor under a sealed room is harmless)
    MH.slab(V, C, cover, holes, top_fn, None, bot_fn if below else None, None, edge_holes, zone_lines)
    MH.slab(V, C, cover, holes, None, (lambda x, y: True), None, bot_col, (), ((), ()))
    # ---------------- outline walls + facade
    n_ext = 0
    for a, b in edges(ol):
        Ls = math.dist(a, b)
        dx, dy = (b[0] - a[0]) / Ls, (b[1] - a[1]) / Ls
        ix, iy = -dy, dx

        def ok(s, a=a, dx=dx, dy=dy, ix=ix, iy=iy):
            pi = (a[0] + dx * s + ix * 0.25, a[1] + dy * s + iy * 0.25)
            po = (a[0] + dx * s - ix * 0.45, a[1] + dy * s - iy * 0.45)
            return not M.in_block(fid, *pi) and not M.in_block(fid, *po)
        keep = _keep_runs(ok, Ls)
        if not keep:
            continue
        ops = window_openings(M, fid, a, b, keep)
        for o in ops:
            if o["kind"] == "window":
                sm = (o["s0"] + o["s1"]) / 2
                pi = (a[0] + dx * sm + ix * 0.8, a[1] + dy * sm + iy * 0.8)
                if M.solid_at(fid, *pi):
                    o["kind"] = "dark"
                else:
                    M.glass_lights.append((fid, a, b, o["s0"], o["s1"], o["z0"], o["z1"]))
        # split the kept runs where the floor above is a void (the Plaza Hall glass runs on up to 6.0)
        pieces = []
        for k0, k1 in keep:
            cuts = [k0, k1]
            for s in split_line(k0, k1, 0.0, [(v - a[0]) / dx if abs(dx) > 0.5 else (v - a[1]) / dy
                                                for v in ((VOID[0], VOID[2]) if abs(dx) > 0.5 else (VOID[1], VOID[3]))]):
                if k0 < s < k1:
                    cuts.append(s)
            cuts = sorted(set(round(c, 4) for c in cuts))
            for s0, s1 in zip(cuts, cuts[1:]):
                sm = (s0 + s1) / 2
                pm = (a[0] + dx * sm + ix * 0.3, a[1] + dy * sm + iy * 0.3)
                tall = fid == "F1" and in_rect(pm, VOID)
                pieces.append((s0, s1, tall))
        for k0, k1, tall in pieces:
            pa = (a[0] + dx * k0, a[1] + dy * k0)
            pb = (a[0] + dx * k1, a[1] + dy * k1)
            sub = [dict(o, s0=max(o["s0"], k0) - k0, s1=min(o["s1"], k1) - k0) for o in ops
                   if o["s1"] > k0 + 0.3 and o["s0"] < k1 - 0.3]
            mid = ((pa[0] + pb[0]) / 2 - ix * 0.6, (pa[1] + pb[1]) / 2 - iy * 0.6)
            col_out = M.terrace(fid, *mid)
            outer = (lambda s_, z_: "brick_red")
            top = STOREY if tall else CLEAR
            thick_wall(V, C, pa, pb, 0.0, top, in_mat="int_drywall", out_mat=outer, openings=sub, col_in=True,
                       col_out=col_out, ceil=top)
            n_ext += 1
            qa = (pa[0] - ix * WALL_T, pa[1] - iy * WALL_T)
            qb = (pb[0] - ix * WALL_T, pb[1] - iy * WALL_T)
            if not tall:
                V.wall(qa, qb, CLEAR, STOREY, "dark_trim" if fid not in TOWER_FLOORS else "concrete", ao=1.0)
                if col_out:
                    C.wall(qa, qb, CLEAR, STOREY, K.COL)
    # ---------------- F4: the roof terraces' parapets on the base outline (where the tower does not stand)
    if fid == "F4":
        n_par = 0
        for a, b in edges(M.base):
            Ls = math.dist(a, b)
            dx, dy = (b[0] - a[0]) / Ls, (b[1] - a[1]) / Ls
            ix, iy = -dy, dx

            def okp(s, a=a, dx=dx, dy=dy, ix=ix, iy=iy):
                pi = (a[0] + dx * s + ix * 0.3, a[1] + dy * s + iy * 0.3)
                po = (a[0] + dx * s - ix * 0.45, a[1] + dy * s - iy * 0.45)
                return M.terrace(fid, *pi) and not M.in_block(fid, *pi, 0.05) and not M.in_block(fid, *po)
            for k0, k1 in _keep_runs(okp, Ls):
                if k1 - k0 < 0.2:
                    continue
                pa = (a[0] + dx * k0, a[1] + dy * k0)
                pb = (a[0] + dx * k1, a[1] + dy * k1)
                thick_wall(V, C, pa, pb, 0.0, PARAPET_H, t=WALL_T, in_mat="brick_red",
                           out_mat=lambda s2, z2: "brick_red", col_in=True, col_out=False, base=False, ceil=99.0)
                qa = (pa[0] - ix * WALL_T, pa[1] - iy * WALL_T)
                qb = (pb[0] - ix * WALL_T, pb[1] - iy * WALL_T)
                cap = [(*pa, PARAPET_H), (*pb, PARAPET_H), (*qb, PARAPET_H), (*qa, PARAPET_H)]
                V.poly(cap, "concrete", ao=1.0, normal_hint=(0, 0, 1))
                C.poly(cap, K.COL, normal_hint=(0, 0, 1))
                n_par += 1
        M.stats["parapet_runs"] = n_par
    # ---------------- partitions, props, columns
    build_partitions(M, fid, P)
    place_layout_props(M, fid, P, z)
    extras_for_floor(M, fid, P, z)
    n_col = 0
    for (x, y) in floor_of(L, fid).get("columns_m", []):
        if not M.inside(fid, x, y) or M.in_block(fid, x, y, 0.6) or M.solid_at(fid, x, y):
            continue
        if any(pip((x, y), poly) or any(math.dist((x, y), q) < 0.7 for q in poly) for poly, *_ in M.props[fid]):
            continue
        r = M.region_at(fid, x, y)
        if r is not None and r["id"] not in ("lobby", "f5_corridors"):
            continue
        if fid in BASE_FLOORS and y > 296.0:
            continue                       # not in the north wing's 2.86 m stack aisles (camera, hide-and-seek)
        if any(math.dist((x, y), ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)) < 2.2
               for hid in HALLS if fid in HALL_LEVELS[hid] for a, b, _h, _k in hall_doors(hid, fid)):
            continue                       # nothing in front of a stair-hall door
        if fid == "F2" and (in_rect((x, y), VOID, 0.5) or in_rect((x, y), ESC_WELL, 0.5)):
            continue
        h = 2 * STOREY - SLAB if (fid == "F1" and in_rect((x, y), VOID)) else CLEAR
        cp = K.Prop("column", col_closed=False)
        cp.visual.box(-0.35, -0.35, 0.0, 0.35, 0.35, h, "int_drywall", faces="+x-x+y-y", tint=(0.95, 0.93, 0.9))
        cp.visual.box(-0.37, -0.37, 0.0, 0.37, 0.37, 0.1, "int_plastic", faces="+x-x+y-y+z")
        cp.collision.box(-0.35, -0.35, 0.0, 0.35, 0.35, h, K.COL_NOCAM, faces="+x-x+y-y")   # floor to ceiling
        P.merge(cp, x, y, 0.0, 0.0)
        n_col += 1
    M.stats.setdefault("columns", {})[fid] = n_col
    build_lights(M, fid, P)
    M.add(P, 0.0, 0.0, z, 0.0, tag=f"floor_{fid}", group=fid)
    M.stats.setdefault("exterior_wall_runs", {})[fid] = n_ext


def build_lights(M, fid, P):
    """Troffers on the 7.64 x 8.1 m module grid (two per bay), mostly switched off for the night: every third
    one stays on, plus every fixture over the main aisles and the elevator lobby."""
    gx = [4.16, 11.8, 19.44, 27.08, 34.72, 42.36, 50.0, 57.64, 65.3, 72.94]
    gy = [254.4, 258.5, 266.6, 274.7, 282.8, 287.6, 291.6, 296.3, 301.0, 305.4, 309.8, 314.2, 318.6]
    xs = [(gx[i] + gx[i + 1]) / 2 + d for i in range(len(gx) - 1) for d in (-1.9, 1.9)]
    ys = [(gy[i] + gy[i + 1]) / 2 for i in range(len(gy) - 1)]
    n_on = n_off = 0
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            if not M.inside(fid, x, y) or M.in_block(fid, x, y, 0.6) or M.solid_at(fid, x, y):
                continue
            if fid == "F2" and (in_rect((x, y), VOID, 0.4) or in_rect((x, y), ESC_WELL, 0.4)):
                continue
            if fid == "F1" and in_rect((x, y), VOID, 0.2):
                continue                                  # the Plaza Hall's ceiling is the F3 slab (pendants)
            on = (i + 2 * j) % 3 == 0 or (fid == "F5" and M.walkable(fid, x, y))
            P.merge(troffer(on, strength=0.24 if fid != "F5" else 0.3), x, y, CLEAR, 90.0 if (i % 2) else 0.0)
            n_on += on
            n_off += not on
    M.stats.setdefault("troffers", {})[fid] = {"on": n_on, "off": n_off}


# ================================================================== props
def register_footprints(M):
    """Prop footprints per floor, known before the doors are planned (no door opens into a range or counter)."""
    for fid in FLOORS:
        f = floor_of(M.layout, fid)
        for pr in f["props"]:
            if "poly_m" in pr:
                hh = float(pr.get("height_m", 1.0))
                M.props[fid].append((ccw([tuple(p) for p in pr["poly_m"]]), pr["type"], pr["id"],
                                     min(hh, TALL_RANGE_H) if pr["type"] == "range" else hh))
            elif "pos_m" in pr and pr["type"] not in ("wall_sign",):
                x, y = pr["pos_m"]
                sw, sd = pr.get("size_m", [0.9, 0.7])
                M.props[fid].append((rect_poly((x - sw / 2, y - sd / 2, x + sw / 2, y + sd / 2)), pr["type"], pr["id"],
                                     float(pr.get("height_m", 1.2))))


def place_layout_props(M, fid, P, z):
    """Every layout prop of a floor, as kit props merged into the floor prop P (local z 0 = floor)."""
    f = floor_of(M.layout, fid)
    seed = {"F1": 1100, "F2": 1200, "F3": 1300, "F4": 1400, "F5": 1500, "F6": 1600}[fid]
    rng = random.Random(seed)
    cent = (38.9, 300.0)
    ranges = []
    lamp_color, shade = (GREEN_LAMP, (0.35, 0.85, 0.45)) if fid == "F6" else (WARM, None)
    for pr in f["props"]:
        typ, pid = pr["type"], pr["id"]
        poly = ccw([tuple(p) for p in pr["poly_m"]]) if "poly_m" in pr else None
        h = float(pr.get("height_m", 1.0))
        seed += 7
        if poly is not None:
            cx, cy, Lg, Wd, fac = long_axis(poly) if axis_aligned(poly) else oriented_axis(poly)
        if typ == "range":
            h = min(h, TALL_RANGE_H)
            ends = [(cx + math.sin(math.radians(fac + 90)) * Lg / 2, cy + math.cos(math.radians(fac + 90)) * Lg / 2),
                    (cx - math.sin(math.radians(fac + 90)) * Lg / 2, cy - math.cos(math.radians(fac + 90)) * Lg / 2)]
            near_neg = math.dist(ends[1], cent) <= math.dist(ends[0], cent)
            face = fac if near_neg else (fac + 180.0) % 360.0
            rp, tops = range_prop_lw(Lg, Wd, h, seed, mobile=bool(pr.get("mobile")))
            P.merge(rp, cx, cy, 0.0, face)
            sx, sy = math.sin(math.radians(face + 90)), math.cos(math.radians(face + 90))
            ranges.append({"id": pid, "c": (cx, cy), "L": Lg, "W": Wd, "u": (sx, sy), "tops": tops})
            for k, (x0, x1, tz) in enumerate(tops):
                xm = (x0 + x1) / 2
                M.stack_axes[f"{fid.lower()}_{pid}" + ("" if k == 0 else f"_step{k}")] = (sx, sy)
                M.stack_tops.append({"name": f"{fid.lower()}_{pid}" + ("" if k == 0 else f"_step{k}"),
                                     "floor": fid, "pos": (cx + sx * xm, cy + sy * xm, z + tz),
                                     "length_m": round(x1 - x0, 2), "height_m": round(tz, 2),
                                     "label": pr.get("label"), "main": k == 0, "layout_h": pr.get("height_m"),
                                     "range": pid})
        elif typ == "shelf_low":
            P.merge(K.bookshelf(Lg, h, Wd, seed=seed, double=Wd > 0.9), cx, cy, 0.0, fac)
            M.anchor(f"shelf_top_{pid}", cx, cy, z + h, fac, floor=fid)
        elif typ == "counter":
            if pid == "coffee_counter":
                cx -= 0.15                                 # its back clear of the back-bar partition (x 49.4)
                P.merge(K.cafe_counter(Lg, Wd, height=h, stools=4, menu=False), cx, cy, 0.0, 270.0)
                M.anchor("coffee_counter_top", cx, cy + 0.6, z + h, 270.0, floor=fid)        # the layout's 1.1 m
                M.anchor("coffee_customer_side", cx - 1.4, cy + 0.6, z, 90.0, floor=fid)
            else:
                P.merge(MH.counter_prop(poly, h), 0.0, 0.0, 0.0, 0.0)
                M.anchor(f"counter_{pid}", cx, cy, z + h, fac, floor=fid)
                if pid == "circ_counter":
                    for k in range(4):
                        P.merge(K.monitor(), cx - 5.4 + k * 3.6, cy + 0.15, h, 180.0)
                    P.merge(desk_lamp(), cx + 6.6, cy, h, 0.0)
                    P.merge(desk_lamp(), cx - 6.6, cy, h, 0.0)
                    P.merge(K.sign("int_sign_help", 2.0, 1.0, 3.4, mount="hanging", hang_top=CLEAR), cx, cy - 0.6,
                            0.0, 180.0)
                elif pid in ("reading_counter_w", "reading_counter_e"):
                    for k in range(3):
                        P.merge(desk_lamp(lamp_color, shade), cx - Lg / 3 + k * Lg / 3, cy, h, 0.0)
                elif pid == "research_desk":
                    P.merge(K.monitor(), cx, cy + 0.2, h, 180.0)
                    P.merge(desk_lamp(), cx + 0.7, cy, h, 0.0)
                elif pid == "lounge_counter":
                    P.merge(small_box("coffee_maker", 0.35, 0.3, 0.45, "int_plastic", tint=(0.3, 0.3, 0.32),
                                      col=False), cx - 0.9, cy, h, 0.0)
                    P.merge(desk_lamp(WARM, light=True), cx + 0.8, cy, h, 0.0)
        elif typ == "table_cluster":
            P.merge(table_with_lamps(Lg, Wd, "int_fabric_" + ("orange", "blue", "green")[seed % 3], lamp_color, shade,
                                     rng), cx, cy, 0.0, fac)
            M.lamps.append((fid, cx, cy, z))
        elif typ == "computer_row":
            n = max(1, int(Lg // 0.9))
            dbl = Wd >= 1.6
            cp = MH.lp_computers(n, Lg / n, 0.8, double=dbl)
            for i in range(n):
                cp.lights.append(K.Light((-Lg / 2 + (i + 0.5) * Lg / n, 0.6, 1.1), radius=2.4, strength=0.2,
                                         color=SCREEN))
            P.merge(cp, cx, cy, 0.0, fac)
            if pid == "bloomberg_terminal":
                M.anchor("bloomberg_terminal", cx, cy - 0.9, z, 0.0, floor=fid)
        elif typ == "carrel_row":
            n = max(1, int(Lg // 0.95))
            pnl = "int_fabric_" + ("blue", "green")[seed % 2]
            if Wd >= 1.35:
                cr = MH.lp_carrels_double(n, Lg / n, Wd, panel=pnl, top_h=min(h, 1.6))
                for i in range(n):
                    for sgn in (1, -1):
                        cr.merge(desk_lamp(lamp_color, shade, light=(i % 2 == 0)), -Lg / 2 + (i + 0.5) * Lg / n,
                                 sgn * 0.48, K.REAL["table_h"], 0.0)
                P.merge(cr, cx, cy, 0.0, fac)
                M.anchor(f"carrel_top_{fid}_{pid}", cx, cy, z + min(h, 1.6), fac, floor=fid)
            else:
                cr = MH.lp_carrels(n, Lg / n, panel=pnl, ph=min(h, 1.6) if h > 1.0 else K.REAL["carrel_panel_h"])
                for i in range(n):
                    cr.merge(desk_lamp(lamp_color, shade, light=(i % 2 == 0)), -Lg / 2 + (i + 0.5) * Lg / n, -0.1,
                             K.REAL["table_h"], 0.0)
                # face the carrels so the sitter backs onto the open floor (the panel on the wall side)
                face = fac
                if fac == 90.0:
                    face = 90.0 if cx < 38.9 else 270.0
                elif cy > 270.0:
                    face = 180.0                          # the grad desks face the north windows (chairs south)
                P.merge(cr, cx, cy, 0.0, face)
        elif typ == "window_desk":
            dr = MH.desk_row(Lg, min(Wd, 0.9), monitors=False)
            n = max(1, int(Lg // 2.4))
            for i in range(n):
                dr.merge(desk_lamp(lamp_color, shade, light=(i % 2 == 0)), -Lg / 2 + (i + 0.5) * Lg / n, -0.1,
                         K.REAL["table_h"], 0.0)
            # chairs on the room side: north desks face the window (chairs south), south desks chairs north
            P.merge(dr, cx, cy, 0.0, 180.0 if cy > 270.0 else 0.0)
        elif typ == "printer":
            x, y = pr["pos_m"]
            P.merge(small_box("printer", 1.0, 0.7, 1.1, "int_plastic", top="int_metal", tint=(0.85, 0.85, 0.85),
                              glow_face=(0.5, 1.0, 0.6)), x, y, 0.0, float(pr.get("facing_deg", 0.0)))
        elif typ == "scanner":
            x, y = pr["pos_m"]
            P.merge(small_box("scanner", 0.9, 0.6, 1.0, "int_plastic", top="int_glass", tint=(0.8, 0.8, 0.82),
                              glow_face=SCREEN), x, y, 0.0, float(pr.get("facing_deg", 0.0)))
        elif typ == "self_checkout":
            x, y = pr["pos_m"]
            kp = K.kiosk()
            kp.lights.append(K.Light((0.0, 0.5, 1.2), radius=2.5, strength=0.22, color=SCREEN))
            P.merge(kp, x, y, 0.0, float(pr.get("facing_deg", 180.0)))
            f_ = float(pr.get("facing_deg", 180.0))
            M.anchor("self_checkout", x + math.sin(math.radians(f_)) * 0.8, y + math.cos(math.radians(f_)) * 0.8, z,
                     (f_ + 180.0) % 360.0, floor=fid)
        elif typ == "vending_machine":
            x, y = pr["pos_m"]
            sw, sd = pr.get("size_m", [1.0, 0.8])
            vm = MH.vending(sw, sd, h)
            vm.lights.append(K.Light((0.0, sd / 2 + 0.8, 1.2), radius=3.0, strength=0.3, color=(0.85, 0.92, 1.0)))
            P.merge(vm, x, y, 0.0, float(pr.get("facing_deg", 180.0)))
        elif typ == "drinking_fountain":
            x, y = pr["pos_m"]
            P.merge(box_prop("fountain", -0.3, 0.0, 0.7, 0.3, 0.4, 1.0, "int_metal", col=False), x, y, 0.0,
                    float(pr.get("facing_deg", 0.0)))
        elif typ == "revolving_door":
            x, y = pr["pos_m"]
            P.merge(revolving_door(), x, 258.65, 0.0, 0.0)          # centred on the glass line (the wall's gap)
            M.anchor("revolving_door", x, 258.65, z, 180.0, floor=fid)
        elif typ == "security_gates":
            P.merge(security_gates(bbox(poly)[0], bbox(poly)[2], cy), 0.0, 0.0, 0.0, 0.0)
        elif typ == "bike_desk":
            face = 90.0 if cx < 38.9 else 270.0
            P.merge(bike_desk(), cx, cy, 0.0, face)
        elif typ == "wudu_station":
            x, y = pr["pos_m"]
            ws = small_box("wudu_station", 2.4, 0.6, 0.9, "int_stone", top="int_metal", tint=(0.9, 0.9, 0.92))
            ws.visual.box(-1.2, -0.3, 0.0, 1.2, -0.25, 1.9, "int_floor_tile", faces="+y", tint=(0.8, 0.9, 0.95))
            P.merge(ws, x, y, 0.0, float(pr.get("facing_deg", 180.0)))
        elif typ == "partition":
            fw = box_prop("feature_wall", -Lg / 2, -0.15, 0.0, Lg / 2, 0.15, h, "int_wall_blue", top="int_metal",
                          cam=False)
            P.merge(fw, cx, cy, 0.0, fac)
        elif typ == "tv_wall":
            x0, y0, x1, y1 = bbox(poly)
            P.merge(screen_prop(y1 - y0 - 0.2, 1.4, 1.0, tint=(0.75, 0.9, 1.0)), x1 - 0.01, (y0 + y1) / 2, 0.0, 270.0)
            M.anchor("news_tv", x0 - 0.8, (y0 + y1) / 2, z, 90.0, floor=fid)
        elif typ == "lockers":
            P.merge(lockers(Lg, Wd, h), cx, cy, 0.0, 180.0 if cy > 270.0 else 0.0)
            M.anchor(f"lockers_top_{pid}", cx, cy, z + h, 0.0, floor=fid)
        elif typ == "sofa":
            face = {"lounge_seating_1": 0.0, "lounge_seating_2": 180.0, "lounge_seating_3": 90.0}.get(pid, fac)
            P.merge(K.couch(Lg, fabric="int_fabric_green" if fid == "F6" else "int_fabric_blue"), cx, cy, 0.0, face)
            sx_, sy_ = (cx + Lg / 2 + 0.45, cy) if fac == 0.0 else (cx, cy + Lg / 2 + 0.45)
            P.merge(small_box("side_table", 0.5, 0.5, 0.55, "int_wood_dark", top="int_wood"), sx_, sy_, 0.0, 0.0)
            P.merge(desk_lamp(lamp_color, shade), sx_, sy_, 0.55, 0.0)
        elif typ == "rooftop_unit":
            P.merge(rooftop_unit(Lg, Wd, h), cx, cy, 0.0, 0.0)
            M.anchor(f"roof_unit_{pid}", cx, cy, z + h, 0.0, floor=fid)
        elif typ == "breaker_panel":
            x, y = pr["pos_m"]
            f_ = float(pr.get("facing_deg", 180.0))
            if pid == "breaker_panel_3":
                x, y, f_ = HALLS["stair_e"][0] - WALL_T - 0.01, 261.4, 270.0   # off the door wall (layout: in it)
            P.merge(breaker_panel(), x, y, 0.0, f_)
            M.anchor(f"breaker_panel_{pid}", x, y, z, f_, floor=fid)
        elif typ == "wall_sign":
            x, y = pr["pos_m"]
            f_ = float(pr.get("facing_deg", 0.0))
            x, y = x + math.sin(math.radians(f_)) * 0.12, y + math.cos(math.radians(f_)) * 0.12
            if pid == "results_board":
                P.merge(K.whiteboard(2.4, 1.2, 1.0), x, y, 0.0, f_)
                P.merge(screen_prop(1.2, 0.5, 2.35, tint=(1.0, 0.85, 0.4)), x, y, 0.0, f_)
                M.anchor("results_board", x, y, z, f_, floor=fid)
            elif pid == "aed_first_aid":
                P.merge(small_box("aed", 0.5, 0.2, 0.6, "int_plastic", tint=(0.9, 0.2, 0.15), col=False), x, y,
                        1.2, f_)
            elif pid == "coffee_menu":
                pass                                      # built on the back-bar wall (extras)
            else:
                P.merge(K.sign("int_sign_quiet", 1.2, 0.6, 1.6), x, y, 0.0, f_)
        else:
            M.notes.setdefault("unplaced_props", []).append(f"{fid} {pid} ({typ})")
    if fid in ("F2", "F3"):                            # F1's compact shelving needs no bridges (2.3 m tops only)
        # no book-cart bridge on a range that carries a rolling-ladder track (act 1, Lua platforms that slide along
        # its face: a plank across that aisle would sit in the ladder's travel box)
        ladders = {t["range"] for t in M.layout["missions"]["design_act1_all_nighter"]["book_ladder_tracks"]
                   if t["floor"] == fid}
        keep = [r for r in ranges if r["id"] not in ladders]
        MH.range_bridges(M, fid, P, z, keep)
        M.stats.setdefault("bridges_skipped_for_ladders", {})[fid] = sorted(ladders)


def extras_for_floor(M, fid, P, z):
    """Signs, lamps, study-room furniture and the other non-layout dressing of one floor."""
    # group study rooms: a table with a lamp and a whiteboard opposite the door, a sign over the door
    for r in M.regions[fid]:
        if r["type"] != "group_study":
            continue
        d = next((d for d in M.doors[fid] if d["room"] == r["id"]), None)
        x0, y0, x1, y1 = bbox(r["poly"])
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if d is not None:
            f = math.radians(d["facing"])
            fx, fy = math.sin(f), math.cos(f)
            half = abs(fx) * (x1 - x0) / 2 + abs(fy) * (y1 - y0) / 2
            P.merge(K.whiteboard(min(2.4, (abs(fy) * (x1 - x0) + abs(fx) * (y1 - y0)) - 0.8), 1.2, 0.9),
                    cx - fx * (half - 0.12), cy - fy * (half - 0.12), 0.0, d["facing"])
            dcx, dcy = d["centre"]
            P.merge(K.sign("int_sign_study", 1.2, 0.6, DOOR_H + 0.25, mount="wall"), dcx + fx * 0.06, dcy + fy * 0.06,
                    0.0, d["facing"])
            along_x = abs(fy) > abs(fx)
        else:
            fx = fy = 0.0
            along_x = (x1 - x0) >= (y1 - y0)
        if min(x1 - x0, y1 - y0) < 2.3:
            continue
        span = (x1 - x0) if along_x else (y1 - y0)
        P.merge(MH.lp_table(min(1.83, span - 1.4), 0.91, 2 if span >= 3.6 else 1, seat="int_fabric_green"),
                cx - fx * 0.3, cy - fy * 0.3, 0.0, 0.0 if along_x else 90.0)
        P.merge(desk_lamp(GREEN_LAMP if fid == "F6" else WARM), cx - fx * 0.3 + (0.5 if along_x else 0.0),
                cy - fy * 0.3 + (0.0 if along_x else 0.5), K.REAL["table_h"], 0.0)
    # EXIT signs over every stair-hall door that opens onto this floor (on the floor side of the wall)
    for hid, rect in HALLS.items():
        if fid not in HALL_LEVELS[hid]:
            continue
        for (a, b, head, key) in hall_doors(hid, fid):
            cxd, cyd = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            out = _hall_door_out(rect, a, b)
            px, py = cxd + out[0] * (WALL_T + 0.01), cyd + out[1] * (WALL_T + 0.01)
            face = math.degrees(math.atan2(out[0], out[1])) % 360.0
            if not M.on_plate(fid, px + out[0] * 0.5, py + out[1] * 0.5):
                continue
            P.merge(exit_sign(), px, py, head + 0.15, face)
    if fid == "F1":
        # coffee bar: the menu board and a back-bar shelf on the partition at x 49.4, under-counter glow
        P.merge(screen_prop(3.2, 1.2, 2.3, tint=(1.0, 0.82, 0.5), mat="int_sign_cafe"), 49.29, 265.4, 0.0, 270.0)
        for y in (261.5, 264.5, 267.5):
            M.kit.light(K.Light((48.0, y, 1.3), radius=4.0, strength=0.45, color=WARM))
        # cafe pendants hanging from the Plaza Hall ceiling (the F3 slab bottom, z 11.4)
        for (x, y) in ((29.0, 261.0), (33.3, 261.0), (30.2, 264.8), (33.3, 268.1), (29.2, 269.3), (44.3, 261.0),
                       (44.3, 265.0)):
            P.merge(pendant(8.4 if x < 40 else 8.0), x, y, 2 * STOREY - SLAB, 0.0)
        # the glass wall at night: cool light from the Plaza lamps along the glass, high up in the hall too
        for x in (28.5, 33.5, 38.9, 44.0, 49.0):
            for zz in (2.0, 8.5):
                M.kit.light(K.Light((x, 259.6, zz), radius=6.0, strength=0.26, color=GLASS_BLUE))
        P.merge(K.sign("int_sign_cafe", 2.0, 1.0, 3.2, mount="hanging", hang_top=2 * STOREY - SLAB), 30.7, 265.0,
                0.0, 180.0)
        P.merge(K.floor_sign("up", 0.7, 2.6, mount="post"), 37.1, 264.2, 0.0, 180.0)
        P.merge(K.floor_sign("1", 0.8, 3.6), 38.9, 270.9, 0.0, 180.0)
        # escalator foot lighting
        M.kit.light(K.Light((38.8, 266.0, 1.2), radius=5.0, strength=0.3, color=(1.0, 0.9, 0.75)))
    if fid == "F2":
        P.merge(K.floor_sign("2", 0.7, 3.6, mount="hanging", hang_top=CLEAR), 38.8, 278.6, 0.0, 180.0)
        P.merge(K.sign("int_sign_study", 1.6, 0.8, 3.2, mount="hanging", hang_top=CLEAR), 14.0, 266.6, 0.0, 90.0)
        P.merge(K.sign("int_sign_quiet", 1.6, 0.8, 3.2, mount="hanging", hang_top=CLEAR), 4.0, 262.0, 0.0, 90.0)
        P.merge(K.book_cart(seed=31), 27.0, 296.8, 0.0, 0.0)
        P.merge(K.book_cart(seed=32), 49.8, 304.6, 0.0, 90.0)
    if fid == "F3":
        P.merge(K.sign("int_sign_quiet", 1.6, 0.8, 3.2, mount="hanging", hang_top=CLEAR), 38.8, 296.6, 0.0, 180.0)
        P.merge(K.book_cart(seed=41), 49.2, 299.6, 0.0, 0.0)
        P.merge(K.couch(2.2, fabric="int_fabric_blue"), 74.6, 264.0, 0.0, 270.0)
    if fid == "F4":
        for x, y, f in ((26.0, 276.4, 180.0), (44.0, 262.0, 0.0), (14.0, 270.8, 90.0)):
            P.merge(K.sign("int_sign_quiet", 1.6, 0.8, 3.2, mount="hanging", hang_top=CLEAR), x, y, 0.0, f)
        # moonlight over the roof terraces (cool, wide, high: it also falls on the tower's walls)
        for (x, y) in ((4.5, 262.0), (4.5, 280.0), (73.0, 262.0), (73.0, 280.0), (14.0, 300.0), (30.0, 306.0),
                       (47.0, 306.0), (64.0, 300.0), (38.8, 292.0)):
            M.kit.light(K.Light((x, y, z + 7.0), radius=15.0, strength=0.30, color=(0.62, 0.72, 1.0)))
        # the terraces at night: wall packs over the terrace doors and a few on the parapets (moonlit decks)
        # two stepped rooftop units against the NE stair hall's bulkhead (1.6 / 3.2 m): its roof (6 m) holds a 1-up
        for k, (ax0, ax1, hh) in enumerate(((51.4, 53.0, 1.6), (53.0, 54.85, 3.2))):
            P.merge(rooftop_unit(ax1 - ax0, 2.6, hh), (ax0 + ax1) / 2, 310.3, 0.0, 0.0)
            M.anchor(f"roof_unit_ne_step{k + 1}", (ax0 + ax1) / 2, 310.3, z + hh, 0.0, floor=fid)
        for (x, y, f) in ((11.3, 263.2, 270.0), (38.8, 283.3, 0.0), (11.3, 277.0, 270.0), (65.8, 276.0, 90.0)):
            fx, fy = math.sin(math.radians(f)), math.cos(math.radians(f))
            P.visual.box(x - 0.2, y - 0.2, 3.2, x + 0.2, y + 0.2, 3.45, "int_light", faces=K.BOX_ALL,
                         tint=(1.0, 0.85, 0.6), glow=True)
            M.kit.light(K.Light((x + fx * 1.2, y + fy * 1.2, z + 2.6), radius=7.5, strength=0.32, color=(1.0, 0.85, 0.6)))
    if fid == "F5":
        P.merge(K.sign("int_sign_out_of_order", 1.2, 0.6, 3.0, mount="hanging", hang_top=CLEAR), 38.8, 266.2, 0.0,
                180.0)
    if fid == "F6":
        P.merge(K.sign("int_sign_quiet", 1.6, 0.8, 3.4, mount="hanging", hang_top=CLEAR), 38.9, 266.8, 0.0, 180.0)
        # the big window: blue moon / Plaza light along the glass
        for x in (24.0, 31.0, 38.9, 46.0, 53.0):
            M.kit.light(K.Light((x, 259.5, z + 2.4), radius=6.5, strength=0.24, color=GLASS_BLUE))


# ================================================================== stair halls
def hall_doors(hid, fid):
    """[(a, b, head, key)] door gaps of a stair hall on a floor (layout vertical[].game.doors; the F5 'locked'
    doors stay open gaps: the missions lock them with Lua barriers, static geometry cannot be act-masked)."""
    v = next(v for v in LAYOUT_CACHE["vertical"] if v["id"] == hid)
    out = []
    for key, (a, b, _f) in v["game"]["doors"].items():
        lvl = key.split("_")[0]
        if lvl == fid:
            out.append((tuple(a), tuple(b), DOOR_H, key))
    return out


def _hall_door_out(rect, a, b):
    x0, y0, x1, y1 = rect
    cx, cy = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    if abs(a[1] - b[1]) < 1e-6:
        return (0.0, -1.0) if abs(cy - y0) < abs(cy - y1) else (0.0, 1.0)
    return (-1.0, 0.0) if abs(cx - x0) < abs(cx - x1) else (1.0, 0.0)


LAYOUT_CACHE = {}


def hall_band_walls(M, V, C, rect, lvl, z0, z1, doors, windows, tint=None):
    """The four walls of a stair hall for one level band (map x, y; local z): inner faces on the rect, the outer
    face (drywall where a floor is outside, brick outdoors, none against another block) and its collision where
    someone can stand outside (a floor or a terrace). doors [(a, b, head)], windows [(edge 's'|'n'|'w'|'e', z0, z1)]."""
    x0, y0, x1, y1 = rect
    sides = {"s": ((x0, y0), (x1, y0)), "e": ((x1, y0), (x1, y1)), "n": ((x1, y1), (x0, y1)), "w": ((x0, y1), (x0, y0))}
    # thick_wall's inner face looks LEFT of a->b: walking the rect counter-clockwise keeps the inside on the left
    fid = lvl if lvl in FLOORS else None
    for key, (a, b) in sides.items():
        Ls = math.dist(a, b)
        dx, dy = (b[0] - a[0]) / Ls, (b[1] - a[1]) / Ls
        ox, oy = dy, -dx                                   # outward (right of a -> b)
        ops = []
        for (pa, pb, head) in doors:
            if seg_point_dist(pa, a, b) > 0.1 or seg_point_dist(pb, a, b) > 0.1:
                continue
            s0 = (pa[0] - a[0]) * dx + (pa[1] - a[1]) * dy
            s1 = (pb[0] - a[0]) * dx + (pb[1] - a[1]) * dy
            s0, s1 = sorted((s0, s1))
            ops.append({"s0": s0, "s1": s1, "z0": z0, "z1": z0 + head, "kind": "door"})
        for (wk, wz0, wz1) in windows:
            if wk == key:
                ops.append({"s0": 0.45, "s1": Ls - 0.45, "z0": z0 + wz0, "z1": z0 + wz1, "kind": "window"})

        def where(s, a=a, dx=dx, dy=dy, ox=ox, oy=oy):
            px, py = a[0] + dx * s + ox * 0.7, a[1] + dy * s + oy * 0.7
            if fid is None:
                return "out"
            if M.in_block(fid, px, py):
                return "block"
            if M.inside(fid, px, py):
                return "floor"
            if M.terrace(fid, px, py):
                return "terrace"
            return "out"

        def outer(s, zz):
            w = where(s)
            if w == "block":
                return None
            if w == "floor":
                return "int_drywall"
            return "brick_red"
        col_out = any(where(s) in ("floor", "terrace") for s in (Ls * 0.15, Ls * 0.5, Ls * 0.85))
        thick_wall(V, C, a, b, z0, z1, t=WALL_T, in_mat="int_drywall", out_mat=outer, openings=ops, col_in=True,
                   col_out=col_out, in_tint=tint, ceil=z1)


def build_hall(M, hid):
    """A stair hall: switchbacks of two 3 m flights per storey (30 deg, 'COL notslip'), floor landings at the doors,
    turn landings at the far end (against the Plaza glass for the west / east halls), walls per level band with the
    doors, EXIT signs, lights; the NW / NE halls end in a roof landing with a door onto the north terrace under a
    bulkhead."""
    P = K.Prop(hid, col_closed=False)
    V, C = P.visual, P.collision
    rect = HALLS[hid]
    x0, y0, x1, y1 = rect
    lane, gap = HALL_LANE[hid]
    first = HALL_FIRST[hid]
    south_rise = hid in ("stair_w", "stair_e")            # flights rise south (turn landing on the glass)
    facing = 180.0 if south_rise else 0.0
    xm = (x0 + x1) / 2
    levels = HALL_LEVELS[hid]
    top_lvl = levels[-1]
    tint = (0.92, 0.94, 1.0)
    for lvl in levels:
        zb = Z[lvl]
        band_top = zb + STOREY if not (hid in ("stair_nw", "stair_ne") and lvl == "F4") else BULKHEAD_TOP
        doors = [(a, b, h) for a, b, h, _k in hall_doors(hid, lvl)]
        windows = []
        if south_rise:
            windows = [("s", 0.6, 5.6)] if lvl in ("F1", "F2") else [("s", 1.0, 5.2)]
        elif lvl in ("F1", "F2", "F3"):
            windows = [("n", 1.0, 5.0)]                   # the tower box's north slot onto University Avenue
        hall_band_walls(M, V, C, rect, lvl, zb, band_top, doors, windows, tint=tint)
        # floor landing at the doors
        if lvl == "F1":
            floor_box(V, C, rect, zb, "int_stone", bottom=False, edge=False, tint=(0.85, 0.85, 0.88))
        elif south_rise:
            floor_box(V, C, (x0, first, x1, y1), zb, "int_stair")
        else:
            floor_box(V, C, (x0, y0, x1, first), zb, "int_stair")
        if lvl != top_lvl:
            sb = K.switchback_stair(STOREY, lane, gap, landing_depth=1e-7, solid_first=(lvl == "F1"))
            P.merge(sb, xm, first, zb, facing)
            run = sb.info["hole"][3]
            if south_rise:
                y_turn = first - run
                poly_slab(V, C, rect_poly((x0, y0, x1, y_turn)), zb + STOREY / 2)
                tz = (x0 + x1) / 2, (y0 + y_turn) / 2
            else:
                y_turn = first + run
                poly_slab(V, C, rect_poly((x0, y_turn, x1, y1)), zb + STOREY / 2)
                tz = (x0 + x1) / 2, (y_turn + y1) / 2
            M.anchor(f"{hid}_{lvl}_turn", tz[0], tz[1], zb + STOREY / 2, facing, floor=lvl)
            P.merge(K.ceiling_light(radius=8.0, strength=0.32), xm, tz[1], zb + STOREY / 2 + CLEAR - 0.1, 90.0)
        # landing light + floor number on the landing's end wall
        ly = (first + y1) / 2 if south_rise else (y0 + first) / 2
        P.merge(K.ceiling_light(radius=8.0, strength=0.36), xm, ly, zb + CLEAR - 0.05 if lvl != top_lvl or
                hid in ("stair_w", "stair_e") else zb + CLEAR - 0.05, 0.0)
        num = str(FLOORS.index(lvl) + 1) if not (hid in ("stair_nw", "stair_ne") and lvl == "F4") else "up"
        if south_rise:
            P.merge(K.floor_sign(num, 0.7, 2.2), xm, y1 - 0.02, zb, 180.0)
        else:
            P.merge(K.floor_sign(num, 0.7, 2.2), xm, y0 + 0.02, zb, 0.0)
        M.anchor(f"{hid}_{lvl}_landing", xm, ly, zb, facing, floor=lvl)
        for (a, b, h, key) in hall_doors(hid, lvl):
            out = _hall_door_out(rect, a, b)
            c = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            M.anchor(f"{hid}_door_{key}", c[0] + out[0] * 0.9, c[1] + out[1] * 0.9, zb,
                     math.degrees(math.atan2(-out[0], -out[1])) % 360.0, floor=lvl, a_m=list(a), b_m=list(b),
                     inside=[round(c[0] - out[0] * 0.9, 3), round(c[1] - out[1] * 0.9, 3)])
    # caps: the west / east halls end under the roof slab (z 35.4); the NW / NE halls under their bulkhead roof
    if hid in ("stair_nw", "stair_ne"):
        zt = BULKHEAD_TOP
        out = (x0 - WALL_T, y0 - WALL_T, x1 + WALL_T, y1 + WALL_T)
        floor_box(V, C, out, zt + SLAB, "roof_gravel", thickness=SLAB, col=True, bottom=True, edge=True)
        M.anchor(f"{hid}_bulkhead_top", xm, (y0 + y1) / 2, zt + SLAB, 0.0, floor="F4")
    M.add(P, 0.0, 0.0, 0.0, 0.0, tag=hid, group="halls")


# ================================================================== elevators, escalators
def elevator_decal(V, x, y, z, facing, label=None):
    """A closed elevator door (int_elevator) with its frame and a floor indicator on a wall face (map position,
    compass facing of the face)."""
    f = math.radians(facing)
    fx, fy = math.sin(f), math.cos(f)
    rx, ry = math.cos(f), -math.sin(f)                     # to the right of the face (as seen from the front)

    def P_(u, d):
        return (x + rx * u + fx * d, y + ry * u + fy * d)
    hw = 0.85
    pa, pb = P_(hw, 0.012), P_(-hw, 0.012)
    V.poly([(pa[0], pa[1], z), (pb[0], pb[1], z), (pb[0], pb[1], z + 2.5), (pa[0], pa[1], z + 2.5)], "int_elevator",
           uvs=K.ONCE, ao=1.0, normal_hint=(fx, fy, 0.0))
    for u0, u1, za, zb in ((-hw - 0.08, -hw, z, z + 2.58), (hw, hw + 0.08, z, z + 2.58), (-hw, hw, z + 2.5, z + 2.58)):
        qa, qb = P_(u1, 0.03), P_(u0, 0.03)
        V.poly([(qa[0], qa[1], za), (qb[0], qb[1], za), (qb[0], qb[1], zb), (qa[0], qa[1], zb)], "int_metal",
               ao=0.95, normal_hint=(fx, fy, 0.0))
    if label is not None:
        cell = K.FLOOR_SIGN_CELLS.get(label, -1)
        if cell >= 0:
            u0, v0 = (cell % 4) / 4.0, 0.5 if cell < 4 else 0.0
            qa, qb = P_(0.16, 0.02), P_(-0.16, 0.02)
            V.poly([(qa[0], qa[1], z + 2.68), (qb[0], qb[1], z + 2.68), (qb[0], qb[1], z + 3.0),
                    (qa[0], qa[1], z + 3.0)], "int_sign_floors", uvs=K.uv_rect(u0, v0, u0 + 0.25, v0 + 0.5),
                   glow=True, normal_hint=(fx, fy, 0.0))
    qa, qb = P_(hw + 0.37, 0.02), P_(hw + 0.25, 0.02)
    V.poly([(qa[0], qa[1], z + 1.0), (qb[0], qb[1], z + 1.0), (qb[0], qb[1], z + 1.12), (qa[0], qa[1], z + 1.12)],
           "int_plastic", glow=True, tint=(1.0, 0.55, 0.2), normal_hint=(fx, fy, 0.0))


def build_elevators(M):
    P = K.Prop("elevators", col_closed=False)
    V, C = P.visual, P.collision
    top = Z["F6"] + CLEAR
    floors = tuple(Z[f] for f in FLOORS)
    # car A: OUT OF ORDER, doors open on every floor (wall-kick shaft F1 -> F6)
    wa = CAR_A_X[1] - CAR_A_X[0]
    ea = K.elevator(floors=floors, width=wa, depth=BANK[3] - BANK[1], door_w=1.7, door_h=2.5, top=top,
                    open_floors=tuple(range(6)), out_of_order=tuple(range(6)), labels=["1", "2", "3", "4", "5", "6"],
                    hollow=True)
    ax = (CAR_A_X[0] + CAR_A_X[1]) / 2
    P.merge(ea, ax, BANK[3], 0.0, 0.0)
    # car A's F1 THRESHOLD (fix round): K.elevator's door thresholds on floor k are the top of the lintel box of floor
    # k - 1 (y -wall_t..0 in front of the pit floor); its lowest floor has no lintel below, and blocks() cuts the whole
    # BANK out of every slab, so the F1 doorway had a 0.2 m out-of-bounds strip (an invisible wall: SM64 treats a step
    # with no floor as a wall) between the stacks floor and the pit, and a player who dropped into the shaft was stuck
    # at its bottom. A threshold plate (visual) + floor (collision, overlapping both neighbours by 2 cm) at z 0.
    hd_a, wt_a = 1.7 / 2, 0.20                        # the door_w above / K.elevator's wall_t
    V.poly([(ax - hd_a, BANK[3] - wt_a, 0.0), (ax + hd_a, BANK[3] - wt_a, 0.0), (ax + hd_a, BANK[3], 0.0),
            (ax - hd_a, BANK[3], 0.0)], "int_metal", ao=0.9, normal_hint=(0, 0, 1))
    C.poly([(ax - hd_a - 0.02, BANK[3] - wt_a - 0.02, 0.0), (ax + hd_a + 0.02, BANK[3] - wt_a - 0.02, 0.0),
            (ax + hd_a + 0.02, BANK[3] + 0.02, 0.0), (ax - hd_a - 0.02, BANK[3] + 0.02, 0.0)], K.COL,
           normal_hint=(0, 0, 1))
    # car B: closed
    wb = CAR_B_X[1] - CAR_B_X[0]
    eb = K.elevator(floors=floors, width=wb, depth=BANK[3] - BANK[1], top=top, out_of_order=(), hollow=False,
                    labels=["1", "2", "3", "4", "5", "6"])
    P.merge(eb, (CAR_B_X[0] + CAR_B_X[1]) / 2, BANK[3], 0.0, 0.0)
    for fx0, fx1 in ((CAR_A_X[1], CAR_B_X[0]), (CAR_B_X[1], BANK[2])):
        P.visual.box(fx0, BANK[1], 0.0, fx1, BANK[3], top, "int_drywall", faces="+y-y+z", tint=(0.86, 0.84, 0.8))
        K.col_box(C, fx0 + 0.01, BANK[1] + 0.01, 0.0, fx1 - 0.01, BANK[3] - 0.01, top, K.COL)
    # the bank's south face over the Plaza Hall (stone cladding seen from the lobby and the void)
    for lvl in FLOORS:
        zb = Z[lvl]
        M.anchor(f"elevator_a_door_{lvl}", ax, BANK[3] + 0.7, zb, 180.0, floor=lvl, open=True)
        P.merge(K.sign("int_sign_out_of_order", 0.8, 0.4, 1.0, mount="post"), CAR_A_X[0] - 0.4, BANK[3] + 0.6, zb, 0.0)
    M.anchor("elevator_a_shaft_bottom", ax, (BANK[1] + BANK[3]) / 2, 0.0, 0.0, floor="F1",
             shaft_inner_m=[round(wa - 0.4, 2), round(BANK[3] - BANK[1] - 0.4, 2)], top_z=top - 0.3)
    # east elevator: closed block; doors west on F2-F6, east on F1
    ex0, ey0, ex1, ey1 = EAST_ELEV
    P.visual.box(ex0, ey0, 0.0, ex1, ey1, top, "int_drywall", faces="+x-x+y-y", tint=(0.86, 0.84, 0.8))
    K.col_box(C, ex0, ey0 + 0.01, 0.0, ex1, ey1, top, K.COL)
    ecy = (EAST_CAR_Y[0] + EAST_CAR_Y[1]) / 2 + 0.2
    for i, lvl in enumerate(FLOORS):
        if lvl == "F1":
            elevator_decal(V, ex1, ecy, Z[lvl], 90.0, "1")
        else:
            elevator_decal(V, ex0, ecy, Z[lvl], 270.0, str(i + 1))
    # ADA elevator (F1 lobby door south, F2 door north) + the filler to the escalator well; F1-F2 only
    dx0, dy0, dx1, dy1 = ADA
    zt = 2 * STOREY - SLAB
    P.visual.box(dx0, dy0, 0.0, dx1, dy1, zt, "int_drywall", faces="+x-x+y-y", tint=(0.86, 0.84, 0.8))
    K.col_box(C, dx0, dy0, 0.0, dx1, dy1, zt, K.COL)
    elevator_decal(V, 43.9, dy0, 0.0, 180.0, "1")
    elevator_decal(V, 43.9, dy1, Z["F2"], 0.0, "2")
    M.anchor("ada_elevator_F1", 43.9, dy0 - 0.8, 0.0, 0.0, floor="F1")
    M.anchor("ada_elevator_F2", 43.9, dy1 + 0.8, Z["F2"], 180.0, floor="F2")
    M.add(P, 0.0, 0.0, 0.0, 0.0, tag="elevators", group="halls")


def build_escalators(M):
    """Two static escalators (30 deg ramps, 'COL notslip'), glass balustrades, a divider; F1 lobby -> F2."""
    P = K.Prop("escalators", col_closed=False)
    V, C = P.visual, P.collision
    rise = STOREY
    n, r, t = K.stair_steps(rise)
    Y1 = (n - 1) * t
    y_first = ESCALATOR[3] - Y1
    for (lx0, lx1) in ESC_LANES:
        fl = K.stair_flight(rise, lx1 - lx0, lip=0.35, lip_visual=False, solid=True, tread_mat="int_stair",
                            side_mat="int_metal")
        P.merge(fl, (lx0 + lx1) / 2, y_first, 0.0, 0.0)
    ys, ye = y_first - t / 2, ESCALATOR[3]
    prof = [(ys, 1.0), (ye, rise + 1.0), (ye + 0.35, rise + 1.0)]
    sloped_block(V, C, ESC_LANES[0][1], ESC_LANES[1][0], prof, mat="int_metal", top_mat="int_plastic",
                 tint=(0.8, 0.82, 0.86))
    for x in (ESCALATOR[0] + 0.06, ESCALATOR[2] - 0.06):
        P.merge(K.railing([(x, ys, 0.0), (x, ye, rise), (x, ye + 0.3, rise)], height=1.0, infill="glass",
                          rail_mat="int_plastic", col_t=THIN_COL_T), 0.0, 0.0, 0.0, 0.0)
    for (lx0, lx1) in ESC_LANES:
        M.kit.light(K.Light(((lx0 + lx1) / 2, (ys + ye) / 2, rise / 2 + 1.5), radius=5.0, strength=0.2,
                            color=(1.0, 0.92, 0.8)))
    M.anchor("escalator_bottom", 38.8, ys - 0.9, 0.0, 0.0, floor="F1")
    M.anchor("escalator_top", 38.8, ESCALATOR[3] + 1.2, Z["F2"], 0.0, floor="F2")
    M.notes["escalators"] = {"first_riser_y": round(y_first, 2), "run_m": round(Y1, 2), "risers": n,
                             "ramp_deg": round(math.degrees(math.atan2(rise, (n - 0.5) * t)), 1)}
    M.add(P, 0.0, 0.0, 0.0, 0.0, tag="escalators", group="F1")


def build_plaza_hall(M):
    """The F2 balcony railing round the void, the free column and the lobby's partitions are elsewhere; here: the
    railing (glass, 1.0 m, 0.24 m collision) and the balcony iMac row's light."""
    P = K.Prop("plaza_hall", col_closed=False)
    e = 0.06
    pts = [(VOID_RAIL[0][0], VOID_RAIL[0][1] + e), (VOID_RAIL[1][0] + e, VOID_RAIL[1][1] + e),
           (VOID_RAIL[2][0] + e, VOID_RAIL[2][1])]
    P.merge(K.railing([(x, y, 0.0) for x, y in pts], height=1.0, infill="glass", post_every=2.5, col_t=THIN_COL_T),
            0.0, 0.0, Z["F2"], 0.0)
    M.anchor("plaza_hall_centre", 38.8, 263.5, 0.0, 0.0, floor="F1")
    M.anchor("balcony_rail", 48.6, 271.9, Z["F2"], 180.0, floor="F2")
    M.add(P, 0.0, 0.0, 0.0, 0.0, tag="plaza_hall", group="F2")


# ================================================================== roof
def build_roof(M):
    """The roof slab over the tower (z 36: F6's ceiling below) and the hipped red-tile roof (visual + a closed
    collision skin; out of reach)."""
    z = Z["ROOF"]
    P = K.Prop("roof", col_closed=False)
    V, C = P.visual, P.collision
    tw = M.tower

    def bot_fn(x, y):
        return None if M.solid_at("F6", x, y) else ("int_ceiling", (0.92, 0.92, 0.95))
    MH.slab(V, C, [tw], [], lambda x, y: ("roof_gravel", None), lambda x, y: True, bot_fn, lambda x, y: True, [])
    # eave fascia
    out = MH.offset_poly(tw, WALL_T)
    for a, b in edges(out):
        V.wall(a, b, 0.0, 0.5, "white_trim", ao=1.0)
    # hipped roof over the main block (11.8..65.3 x 258.5..280.7), ridge HIPPED_RIDGE above the eaves
    x0, y0, x1, y1 = 11.5, 258.2, 65.6, 281.0
    hw = (y1 - y0) / 2
    r0, r1 = x0 + hw, x1 - hw
    H = HIPPED_RIDGE
    yc = (y0 + y1) / 2
    faces = [[(x0, y0, 0.5), (x1, y0, 0.5), (r1, yc, H), (r0, yc, H)],
             [(x1, y1, 0.5), (x0, y1, 0.5), (r0, yc, H), (r1, yc, H)],
             [(x0, y1, 0.5), (x0, y0, 0.5), (r0, yc, H)],
             [(x1, y0, 0.5), (x1, y1, 0.5), (r1, yc, H)]]
    for f in faces:
        if K.newell(f)[2] < 0:
            f.reverse()
        V.poly(f, "roof_tile_red", ao=1.0)
        C.poly(f, K.COL)
    M.anchor("roof_ridge", (r0 + r1) / 2, yc, z + H, 0.0, floor="ROOF")
    M.add(P, 0.0, 0.0, z, 0.0, tag="roof", group="roof")


# ================================================================== backdrop (no collision)
BACKDROP_R = 165.0
SOUTH_REACH = 296.0                    # the strip south to Century Tower (289 m) and the Auditorium (269 m)
SKIP_BUILDINGS = {"r12122775/196848215", "r12122775/891179070", "w863677836", "w150860043"}


def build_backdrop(M, campus=None):
    """The campus around Library West at night, visual only: ground (lawn / paving / parking), walks and roads,
    trees, buildings extruded from campus.json with lit windows, Plaza lamps, the colonnade, Century Tower lit,
    a moon and stars."""
    if campus is None:
        with open(CAMPUS_PATH) as f:
            campus = json.load(f)
    cx, cy = CENTER
    P = K.Prop("backdrop", col_closed=False)
    V = P.visual
    R = BACKDROP_R
    foot = M.base
    rng = random.Random(55)

    def in_area(x, y, m=0.0):
        if abs(x - cx) < R - m and abs(y - cy) < R - m:
            return True
        return abs(x - cx) < 120.0 - m and cy - SOUTH_REACH + m < y < cy

    def near(pts, m=-10.0):
        return any(in_area(x, y, m) for x, y in pts)
    areas = []
    for a in campus["areas"]:
        tg = a["tags"]
        if not near(a["pts"]):
            continue
        if tg.get("natural") == "water":
            areas.append((ccw([tuple(p) for p in a["pts"]]), ("pond_water", (0.5, 0.55, 0.8))))
        elif tg.get("amenity") == "parking":
            areas.append((ccw([tuple(p) for p in a["pts"]]), ("parking", None)))
        elif tg.get("highway") == "pedestrian" or tg.get("place") == "square":
            areas.append((ccw([tuple(p) for p in a["pts"]]), ("plaza_brick", None)))

    def ground(x, y):
        for poly, m in areas:
            if pip((x, y), poly):
                return m
        return ("lawn", None)
    gx = split_line(cx - R, cx + R, 8.0)
    gy = split_line(cy - SOUTH_REACH, cy + R, 8.0)
    cells = Cells.build([rect_poly((cx - R, cy - SOUTH_REACH, cx + R, cy + R))], [], gx, gy,
                        lambda x, y: None if (pip((x, y), foot) or not in_area(x, y)) else ground(x, y))
    rects, parts = cells.merge(24.0, 24.0)
    for x0, y0, x1, y1, (m, t) in rects:
        V.poly([(x0, y0, -0.05), (x1, y0, -0.05), (x1, y1, -0.05), (x0, y1, -0.05)], m, ao=1.0, tint=t)
    for poly, (m, t) in parts:
        V.poly([(x, y, -0.05) for x, y in poly], m, ao=1.0, tint=t)
    # walks and roads; street / Plaza lamps along them
    widths = {"footway": 2.4, "path": 2.0, "pedestrian": 4.0, "cycleway": 2.4, "service": 5.0, "unclassified": 6.5,
              "residential": 6.5, "tertiary": 7.5, "secondary": 9.0, "primary": 10.0, "steps": 2.4}
    n_ways = n_lamps = 0
    lamp_spots = []
    for w in campus["ways"]:
        hw = w["tags"].get("highway")
        if hw not in widths or not near(w["pts"], 0.0):
            continue
        mat = "asphalt" if hw in ("service", "unclassified", "residential", "tertiary", "secondary", "primary") \
            else "sidewalk"
        zz = -0.035 if mat == "sidewalk" else -0.04
        half = widths[hw] / 2
        pts = w["pts"]
        acc = 0.0
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            if not (in_area(ax, ay) and in_area(bx, by)):
                continue
            L = math.hypot(bx - ax, by - ay)
            if L < 0.3:
                continue
            mx, my = (ax + bx) / 2, (ay + by) / 2
            if pip((mx, my), foot):
                continue
            nx, ny = -(by - ay) / L * half, (bx - ax) / L * half
            ext = min(half, 1.0)
            ux, uy = (bx - ax) / L * ext, (by - ay) / L * ext
            q = [(ax - ux + nx, ay - uy + ny, zz), (ax - ux - nx, ay - uy - ny, zz), (bx + ux - nx, by + uy - ny, zz),
                 (bx + ux + nx, by + uy + ny, zz)]
            V.poly(q, mat, ao=1.0, normal_hint=(0, 0, 1))
            n_ways += 1
            # lamps every ~22 m along walks and streets within the near ring
            acc += L
            while acc > 22.0:
                acc -= 22.0
                t_ = max(0.0, min(1.0, 1.0 - acc / L))
                lx, ly = ax + (bx - ax) * t_ + nx / half * (half + 0.8), ay + (by - ay) * t_ + ny / half * (half + 0.8)
                if math.dist((lx, ly), (cx, cy)) < 150 and not pip((lx, ly), foot) and \
                        all(math.dist((lx, ly), q2) > 9.0 for q2 in lamp_spots):
                    lamp_spots.append((lx, ly))
    for (lx, ly) in lamp_spots:
        street_lamp(V, lx, ly)
        n_lamps += 1
    M.stats["backdrop_lamp_spots"] = lamp_spots
    # trees (dark live oaks; palms as oaks too at this distance)
    n_trees = 0
    for p in campus["points"]:
        if p["tags"].get("natural") != "tree":
            continue
        x, y = p["pt"]
        if not in_area(x, y, 12.0):
            continue
        if pip((x, y), foot) or any(seg_point_dist((x, y), a_, b_) < 12.0 for a_, b_ in edges(foot)):
            continue                                       # no canopy against the glass (the Garden Terrace)
        MH.tree(V, x, y, rng.uniform(0.85, 1.2), rng)
        n_trees += 1
    # buildings, with a scatter of lit windows
    n_b = 0
    for b in campus["buildings"]:
        if b["id"] in SKIP_BUILDINGS:
            continue
        tg = b.get("tags", {})
        if tg.get("building") in ("roof", None):
            continue
        pts = ccw([tuple(q) for q in b["pts"]])
        bx = bbox(pts)
        if not all(in_area(x, y, -2.0) for x, y in ((bx[0], bx[1]), (bx[2], bx[3]), (bx[0], bx[3]), (bx[2], bx[1]))):
            continue
        h = float(b.get("height") or 8.0)
        name = tg.get("name") or ""
        facade = "facade_gothic" if name in ("Smathers Library", "University Auditorium", "Anderson Hall",
                                             "Peabody Hall", "Keene-Flint Hall") else \
            ("facade_brick" if h < 14 else "facade_band")
        extrude_lw(V, pts, h, facade, "roof_dark")
        lit_windows(V, pts, h, rng, warm_share=0.35 if name != "Smathers Library" else 0.2)
        n_b += 1
    # the Library Colonnade (scaled x1.43 to the game's taller ground floor) and its garden terrace
    col_h = 4.6 * 1.43
    V.box(19.1, 241.4, col_h - 0.4, 85.1, 247.6, col_h, "concrete", faces=K.BOX_ALL, tint=(0.75, 0.75, 0.8))
    V.box(35.0, 247.6, col_h - 0.4, 42.4, 258.0, col_h, "concrete", faces=K.BOX_ALL, tint=(0.75, 0.75, 0.8))
    for x in (19.6, 27.5, 35.4, 42.0, 50.6, 59.0, 67.6, 76.2, 84.6):
        V.box(x - 0.25, 241.6, 0.0, x + 0.25, 242.1, col_h - 0.4, "brick_red", faces="+x-x+y-y")
    for y in (250.0, 255.0):
        for x in (35.3, 42.1):
            V.box(x - 0.2, y - 0.2, 0.0, x + 0.2, y + 0.2, col_h - 0.4, "brick_red", faces="+x-x+y-y")
    for (xa, xb) in ((20.6, 33.4), (44.0, 57.0)):
        V.box(xa, 249.4, 0.0, xb, 256.0, 0.75, "brick_red", faces="+x-x+y-y")
        V.box(xa + 0.2, 249.6, 0.74, xb - 0.2, 255.8, 0.95, "leaves_oak", faces="+z")
    for x in (24.0, 31.0, 46.0, 53.0):                   # canopy downlights onto the terrace
        V.box(x - 0.3, 244.2, col_h - 0.42, x + 0.3, 244.8, col_h - 0.4, "int_light", faces="-z", glow=True,
              tint=(1.0, 0.86, 0.6))
    V.box(38.4, 236.8, 0.0, 39.2, 239.8, 0.7, "limestone", faces="+x-x+y-y+z")      # the bronze gator's plinth
    V.box(38.5, 237.0, 0.7, 39.1, 239.6, 1.15, "bronze", faces="+x-x+y-y+z")
    # Century Tower, floodlit (the backdrop Lighting gets floodlights at its base)
    ct = next((b for b in campus["buildings"] if b["id"] == "w150860043"), None)
    if ct:
        MH.century_tower(V, ccw([tuple(q) for q in ct["pts"]]))
        cb = bbox(ct["pts"])
        tcx, tcy = (cb[0] + cb[2]) / 2, (cb[1] + cb[3]) / 2
        w = min(cb[2] - cb[0], cb[3] - cb[1]) / 2
        for a, b in edges([(tcx - w, tcy - w), (tcx + w, tcy - w), (tcx + w, tcy + w), (tcx - w, tcy + w)]):
            L = math.dist(a, b)
            ddx, ddy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            nx, ny = ddy, -ddx
            mcx, mcy = (a[0] + b[0]) / 2 + nx * 0.06, (a[1] + b[1]) / 2 + ny * 0.06
            ring = [(mcx + ddx * 1.4 * math.cos(2 * math.pi * k / 12), mcy + ddy * 1.4 * math.cos(2 * math.pi * k / 12),
                     35.8 + 1.4 * math.sin(2 * math.pi * k / 12)) for k in range(12)]
            V.poly(ring, "white_trim", glow=True, tint=(1.0, 0.95, 0.75), normal_hint=(nx, ny, 0))
            for k in range(3):
                s0, s1 = L * (k + 0.3) / 3, L * (k + 0.7) / 3
                pa = (a[0] + ddx * s0 + nx * 0.05, a[1] + ddy * s0 + ny * 0.05)
                pb = (a[0] + ddx * s1 + nx * 0.05, a[1] + ddy * s1 + ny * 0.05)
                V.wall(pa, pb, 39.0, 40.6, "int_light", glow=True, tint=(1.0, 0.8, 0.45))
        M.stats["century_tower"] = [round(tcx, 2), round(tcy, 2)]
    # sky: a moon and stars on a dome (inside s16: radius 285 m around the stage centre)
    moon_b, moon_e, Rm = math.radians(172.0), math.radians(24.0), 280.0
    mx, my, mz = cx + Rm * math.cos(moon_e) * math.sin(moon_b), cy + Rm * math.cos(moon_e) * math.cos(moon_b), \
        Rm * math.sin(moon_e)
    disc(V, (mx, my, mz), (cx, cy, 30.0), 7.0, (0.95, 0.95, 0.85))
    srng = random.Random(9)
    n_stars = 0
    while n_stars < 160:
        b = srng.uniform(0, 2 * math.pi)
        e = math.radians(srng.uniform(12.0, 78.0))
        Rs = 285.0
        sx, sy, sz = cx + Rs * math.cos(e) * math.sin(b), cy + Rs * math.cos(e) * math.cos(b), Rs * math.sin(e)
        if abs(sx - cx) > 300 or abs(sy - cy) > 300:
            continue
        br = srng.uniform(0.55, 1.0)
        disc(V, (sx, sy, sz), (cx, cy, 30.0), srng.uniform(0.35, 0.7), (br, br, min(1.0, br * 1.05)), n=4)
        n_stars += 1
    M.stats["backdrop"] = {"buildings": n_b, "trees": n_trees, "way_segments": n_ways, "lamps": n_lamps,
                           "ground_rects": len(rects), "stars": n_stars}
    M.add(P, 0.0, 0.0, 0.0, 0.0, tag="backdrop", group="backdrop")


def extrude_lw(V, pts, h, wall, roof, cell=24.0):
    """A backdrop building (Marston's extrude, but the flat roof is always cut into cells: no face spans more
    than the UV limit)."""
    for a, b in edges(pts):
        L = math.dist(a, b)
        if L < 0.2:
            continue
        cuts = split_line(0.0, L, 20.0)
        zs = split_line(0.0, h, 20.0)
        for s0, s1 in zip(cuts, cuts[1:]):
            pa = (a[0] + (b[0] - a[0]) * s0 / L, a[1] + (b[1] - a[1]) * s0 / L)
            pb = (a[0] + (b[0] - a[0]) * s1 / L, a[1] + (b[1] - a[1]) * s1 / L)
            for za, zb in zip(zs, zs[1:]):
                V.wall(pa, pb, za, zb, wall, ao=1.0)
    bx = bbox(pts)
    for x0, x1 in zip(split_line(bx[0], bx[2], cell), split_line(bx[0], bx[2], cell)[1:]):
        for y0, y1 in zip(split_line(bx[1], bx[3], cell), split_line(bx[1], bx[3], cell)[1:]):
            pc = clip_rect(pts, x0, y0, x1, y1)
            if len(pc) >= 3 and abs(signed_area(pc)) > 1e-4:
                V.poly([(x, y, h) for x, y in ccw(pc)], roof, ao=1.0)


def disc(V, c, toward, r, col, n=10):
    """A flat glowing disc at c facing `toward` (moon, stars)."""
    d = (toward[0] - c[0], toward[1] - c[1], toward[2] - c[2])
    L = math.sqrt(sum(v * v for v in d)) or 1.0
    nrm = (d[0] / L, d[1] / L, d[2] / L)
    ref = (0.0, 0.0, 1.0) if abs(nrm[2]) < 0.9 else (1.0, 0.0, 0.0)
    u = (nrm[1] * ref[2] - nrm[2] * ref[1], nrm[2] * ref[0] - nrm[0] * ref[2], nrm[0] * ref[1] - nrm[1] * ref[0])
    ul = math.sqrt(sum(v * v for v in u))
    u = tuple(v / ul for v in u)
    w = (nrm[1] * u[2] - nrm[2] * u[1], nrm[2] * u[0] - nrm[0] * u[2], nrm[0] * u[1] - nrm[1] * u[0])
    pts = [tuple(c[i] + r * (math.cos(2 * math.pi * k / n) * u[i] + math.sin(2 * math.pi * k / n) * w[i])
                 for i in range(3)) for k in range(n)]
    V.poly(pts, "int_light", glow=True, tint=col, normal_hint=nrm)


def street_lamp(V, x, y, h=4.2):
    V.box(x - 0.06, y - 0.06, 0.0, x + 0.06, y + 0.06, h, "metal_gray", faces="+x-x+y-y", ao=1.0,
          tint=(0.5, 0.5, 0.55))
    V.box(x - 0.22, y - 0.22, h, x + 0.22, y + 0.22, h + 0.45, "int_light", faces=K.BOX_ALL, glow=True,
          tint=(1.0, 0.86, 0.58))


def lit_windows(V, pts, h, rng, warm_share=0.3):
    """Scatter lit window quads over a backdrop building's walls (warm lit rooms, some cool, most dark)."""
    floors = max(1, int(h // 3.6))
    for a, b in edges(pts):
        L = math.dist(a, b)
        if L < 4.0:
            continue
        dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx, ny = dy, -dx
        nwin = int(L // 3.2)
        for fl in range(floors):
            z0 = 1.0 + fl * 3.6
            for i in range(nwin):
                if rng.random() > warm_share:
                    continue
                s = (i + 0.5) * L / nwin
                pa = (a[0] + dx * (s - 0.6) + nx * 0.04, a[1] + dy * (s - 0.6) + ny * 0.04)
                pb = (a[0] + dx * (s + 0.6) + nx * 0.04, a[1] + dy * (s + 0.6) + ny * 0.04)
                col = (1.0, 0.82, 0.5) if rng.random() < 0.8 else (0.7, 0.85, 1.0)
                V.wall(pa, pb, z0, z0 + 1.5, "int_light", glow=True, tint=col)


# ================================================================== pickups, points, views
def plan_pickups(M):
    """Coins (> 120 so the 100-coin star is reachable), hearts, 1-ups, Goombas: map (x, y, design floor z).
    Placed (and checked against the collision) by build_interior.py with stage_pickups.Placer."""
    red = [tuple(r["pos_m"]) for r in M.layout["missions"]["design_act6_glowing_books"]["red_coins"]]
    out = []

    def add(kind, name, x, y, z, facing=0.0):
        if kind in ("coin", "coin_line", "coin_ring") and any(math.dist((x, y), r) < 2.5 for r in red):
            M.notes.setdefault("coins_dropped_for_red_coins", []).append(name)
            return
        out.append({"kind": kind, "name": name, "pos": (round(x, 3), round(y, 3), round(z, 3)), "facing": facing})
    z1, z2, z3, z4, z5, z6 = (Z[k] for k in FLOORS)
    # F1 lobby: the vestibule, up the escalators (6 + 6 coins on the steps), the cafe and the coffee bar
    add("coin_line", "F1 cafe", 31.6, 263.0, z1, 90.0)
    add("coin_line", "F1 coffee bar", 47.0, 264.0, z1, 0.0)
    n, r, t = K.stair_steps(STOREY)
    y_first = ESCALATOR[3] - (n - 1) * t
    for k in range(5):
        tt = (k + 0.5) / 5
        y = y_first + tt * (ESCALATOR[3] - y_first)
        for lx in (37.1, 40.5):
            add("coin", f"F1 escalator coin {k + 1} x{lx}", lx, y, z1 + tt * STOREY)
    # F1 study floor: compact stacks aisles, Judaica, east stacks, the middle band
    add("coin_line", "F1 compact aisle north", 38.75, 305.4, z1, 0.0)
    add("coin_line", "F1 compact aisle south", 38.75, 296.9, z1, 90.0)
    add("coin_line", "F1 Judaica aisle", 17.8, 304.4, z1, 0.0)
    add("coin_line", "F1 curve bay", 38.8, 317.6, z1, 90.0)
    add("coin_line", "F1 east stacks", 66.0, 260.2, z1, 90.0)
    add("coin_line", "F1 west stacks", 8.6, 275.0, z1, 0.0)
    add("coin_line", "F1 middle band", 38.8, 279.0, z1, 90.0)
    add("coin_ring", "F1 HV stacks", 50.4, 270.4, z1)
    # F2: arrival hall, the study-room corridor, stacks, balcony
    add("coin_ring", "F2 arrival hall", 38.8, 280.3, z2)
    for k, x in enumerate((13.5, 15.2, 16.9)):
        add("coin", f"F2 study room corridor {k + 1}", x, 267.1, z2)
    add("coin_line", "F2 west wing", 10.4, 272.0, z2, 0.0)
    add("coin_line", "F2 balcony", 49.6, 273.9, z2, 90.0)
    add("coin_line", "F2 stacks aisle west", 28.3, 305.4, z2, 0.0)
    add("coin_line", "F2 stacks aisle east", 49.2, 305.4, z2, 0.0)
    add("coin_line", "F2 curve bay", 38.8, 317.6, z2, 90.0)
    add("coin_line", "F2 east windows", 70.2, 305.0, z2, 0.0)
    # F3: the open study floor, Neuharth, periodicals
    add("coin_line", "F3 south study", 38.8, 263.2, z3, 90.0)
    add("coin_ring", "F3 open floor", 7.6, 271.0, z3)
    add("coin_line", "F3 Neuharth", 70.0, 264.0, z3, 90.0)
    add("coin_line", "F3 east tables", 76.0, 278.0, z3, 0.0)
    add("coin_line", "F3 periodicals aisle", 38.75, 305.4, z3, 0.0)
    add("coin_line", "F3 microforms aisle", 59.67, 303.0, z3, 0.0)
    add("coin_line", "F3 west tables", 6.0, 271.0, z3, 0.0)
    # range tops (F2 / F3 3.0 m rows): one coin on every main top
    for st in M.stack_tops:
        if st["main"] and st["floor"] in ("F2", "F3") and st["height_m"] >= 2.9:
            add("coin", f"{st['floor']} range top {st['name']}", st["pos"][0], st["pos"][1], st["pos"][2])
    # F4 quiet floor + the roof terraces at night
    add("coin_line", "F4 north window desks", 35.0, 280.6, z4, 90.0)
    add("coin_line", "F4 south band", 38.8, 261.0, z4, 90.0)
    add("coin_ring", "F4 north terrace", 39.0, 304.0, z4)
    add("coin_line", "F4 north terrace east", 56.0, 292.0, z4, 90.0)
    add("coin_line", "F4 north terrace west", 21.0, 291.0, z4, 90.0)
    add("coin_line", "F4 west terrace", 4.5, 270.0, z4, 0.0)
    add("coin_line", "F4 east terrace", 72.0, 270.0, z4, 0.0)
    # F5 corridor, F6 reading room and lounge
    add("coin_line", "F5 corridor", 38.8, 276.0, z5, 90.0)
    add("coin_line", "F6 reading room", 38.9, 265.6, z6, 90.0)
    add("coin_line", "F6 grad desks", 35.0, 280.4, z6, 90.0)
    add("coin_line", "F6 lounge", 15.2, 266.5, z6, 0.0)
    # stair halls: a coin on every turn landing
    for k, v in sorted(M.anchors.items()):
        if k.endswith("_turn") and k.startswith("stair_"):
            add("coin", f"turn landing {k}", v["pos"][0], v["pos"][1], v["pos"][2])
    # hearts, 1-ups, Goombas
    out.append({"kind": "heart", "name": "heart F1 lobby", "pos": (30.8, 266.7, z1)})
    out.append({"kind": "heart", "name": "heart F2 stacks", "pos": (38.75, 309.8, z2)})
    out.append({"kind": "heart", "name": "heart F4 north terrace", "pos": (22.0, 300.0, z4)})
    out.append({"kind": "heart", "name": "heart F6 lounge", "pos": (15.2, 270.8, z6)})
    out.append({"kind": "1up", "name": "1-up F5 electrical room", "pos": (45.0, 261.5, z5)})
    out.append({"kind": "1up", "name": "1-up NE bulkhead roof", "pos": M.anchors["stair_ne_bulkhead_top"]["pos"]})
    tall = [s for s in M.stack_tops if s["floor"] == "F3" and s["main"] and s["height_m"] >= 2.9]
    if tall:
        far = max(tall, key=lambda s: s["pos"][1])
        # (fix round) not on the range top's coin (every main top has one at its centre): 1.5 m along the range
        ux, uy = M.stack_axes.get(far["name"], (1.0, 0.0))
        off = max(0.0, min(1.5, far["length_m"] / 2 - 0.5))
        out.append({"kind": "1up", "name": f"1-up F3 range top {far['name']}",
                    "pos": (round(far["pos"][0] + ux * off, 3), round(far["pos"][1] + uy * off, 3), far["pos"][2])})
    # (integration) a Goomba inside the hide-and-seek arena (the layout's design act 2 polygon on its floors) is left
    # out of that course act (OBJECT_WITH_ACTS): it would chase the hiders who keep still. Every other act keeps it.
    arena = M.layout["missions"]["design_act2_quiet_hours_hide_and_seek"]["arena"]
    for name, x, y, z in (("goomba F1 compact stacks", 38.75, 309.8, z1), ("goomba F1 east stacks", 66.0, 269.0, z1),
                          ("goomba F2 stacks", 59.67, 301.0, z2), ("goomba F3 periodicals", 28.3, 309.8, z3)):
        it = {"kind": "goomba", "name": name, "pos": (x, y, z), "facing": 90.0}
        if any(abs(z - Z[f]) < 0.1 for f in arena["floors"]) and pip((x, y), arena["poly_m"]):
            it["acts"] = [a for a in range(1, 7) if a != HIDE_SEEK_ACT]
            M.notes.setdefault("goombas_not_in_hide_and_seek", []).append(name)
        out.append(it)
    M.pickups = out


def plan_points(M):
    """Design anchor points for the mission author (docs/game_design.md 7.5), grouped as the points file is;
    build_interior.py re-measures each on the built collision."""
    L = M.layout["missions"]
    pts = {}

    def g(name, p, note=None, facing=None, kind="ground", **extra):
        d = {"name": name, "p": tuple(p), "kind": kind}
        if note:
            d["note"] = note
        if facing is not None:
            d["facing"] = facing
        d.update(extra)
        return d

    def lp(rec, z_off=0.0):
        """layout point -> (x, y, floor z)"""
        return (rec["pos_m"][0], rec["pos_m"][1], Z[rec["floor"]] + z_off)

    def door_pt(key, note=None):
        a = M.anchors[key]
        return g(key, a["pos"], note=note, facing=a["facing"], clear=0.5, a_m=a.get("a_m"), b_m=a.get("b_m"),
                 inside_m=a.get("inside"))
    a1 = L["design_act1_all_nighter"]
    pts["act1_all_nighter"] = {
        "start": g("act1_start", lp(a1["start"]), facing=0.0, note="= the spawn (vestibule, facing the escalators)"),
        "star_target": g("act1_star_target", lp(a1["star"]), clear=0.3,
                         note="F6 big window over the Plaza (Century Tower lit, 188 deg); hover the star ~1.6 m up"),
        "route": [g(f"act1_route_{k}", lp(r), note=r.get("note"), clear=0.3) for k, r in enumerate(a1["route"])],
        "boos": [g(f"act1_boo_{k}", lp(b), note=b.get("note"), clear=0.5) for k, b in enumerate(a1["boos"])],
        "book_ladder_tracks": [g(f"act1_ladder_{t['floor']}_{k}", (*t["a_m"], Z[t["floor"]]), clear=0.25,
                                 end_m=list(t["b_m"]), range=t["range"],
                                 note="rolling library ladder along the south face of a 3.0 m range (a Lua "
                                      "platform; its top step at 2.2 m)")
                               for k, t in enumerate(a1["book_ladder_tracks"])],
        "closed_for_cleaning_doors": [door_pt(f"{h}_door_{f}", "act 1: a Lua barrier here ('CLOSED FOR CLEANING')")
                                      for h in ("stair_w", "stair_e") for f in ("F1", "F2", "F3")
                                      if f"{h}_door_{f}" in M.anchors],
        "staff_only_doors_f5": [door_pt(f"{h}_door_F5_locked", "the F5 staff floor's stair door: an open gap in the "
                                        "geometry; lock it with a Lua barrier except in acts 4-5")
                                for h in ("stair_w", "stair_e")],
    }
    a2 = L["design_act2_quiet_hours_hide_and_seek"]
    extra_spots = [("F1", (7.4, 314.5), "F1 NW window corner behind the bike desks"),
                   ("F1", (64.0, 313.0), "F1 behind the short GV-HD range by the NE stair"),
                   ("F2", (10.6, 313.8), "F2 behind the short manga-row end (NW corner)"),
                   ("F2", (26.0, 317.2), "F2 curved glass bay, west end"),
                   ("F2", (5.4, 305.9), "F2 west window bay"),
                   ("F3", (70.2, 312.0), "F3 east window seats behind the microforms"),
                   ("F3", (26.8, 317.4), "F3 curved glass bay, west end"),
                   ("F3", (49.2, 309.8), "F3 aisle between periodicals and microforms")]
    a2 = json.loads(json.dumps(a2))
    for s_ in a2["hiding_spots"]:
        if s_["note"].startswith("F3 neck"):
            s_["pos_m"] = [38.75, 292.5]                   # behind the neck's free column (layout: on it)
    pts["act2_quiet_hours_hide_and_seek"] = {
        "players": a2["players"], "round_s": a2["round_s"],
        "arena": {"floors": a2["arena"]["floors"], "poly_m": a2["arena"]["poly_m"], "note": a2["arena"]["note"]},
        "seeker_start": g("act2_seeker_start", lp(a2["seeker_start"]), facing=0.0, clear=0.5,
                          note="the night librarian counts at the circulation desk (facing the counter)"),
        "hider_release": g("act2_hider_release", lp(a2["hider_release"]), facing=0.0, clear=0.5,
                           note=a2["hider_release"].get("note")),
        "hider_release_east": g("act2_hider_release_east", (49.6, 288.6, Z["F2"]), facing=0.0, clear=0.5,
                                note="the east corridor into the stacks (x 48.0..51.2)"),
        "star_target": g("act2_star_target", (38.0, 283.9, Z["F2"] + 1.2), clear=0.0,
                         note="on the circulation desk counter (top 1.2 m): the star appears here (design)"),
        "results_board": g("act2_results_board", M.anchors["results_board"]["pos"],
                           facing=M.anchors["results_board"]["facing"], clear=0.0,
                           note="whiteboard + a lit header screen on the desk enclosure's west face"),
        "hiding_spots": [g(f"act2_hide_{k}", lp(s), note=s.get("note"), clear=0.3)
                         for k, s in enumerate(a2["hiding_spots"])] +
                        [g(f"act2_hide_{k + len(a2['hiding_spots'])}", (x, y, Z[fl]), note=note, clear=0.3)
                         for k, (fl, (x, y), note) in enumerate(extra_spots)],
        "stair_links": [door_pt(f"{h}_door_{f}") for h in ("stair_nw", "stair_ne") for f in ("F1", "F2", "F3")],
        "seeker_light": a2["seeker_light"],
    }
    a3 = L["design_act3_ghost_of_finals_past"]
    pts["act3_ghost_of_finals_past"] = {
        "boos": {k: g(f"act3_boo_{k}", lp(b), note=b.get("note"), clear=0.5) for k, b in a3["boos"].items()},
        "big_boo_arena": {"poly_m": a3["big_boo_arena"]["poly_m"], "z_floor": 0.0,
                          "z_ceiling": 2 * STOREY - SLAB, "note": "the Plaza Hall (the design's 'rotunda'); the cafe "
                          "tables stay (static geometry has no act masks): a low obstacle course under Big Boo"},
        "big_boo_spawn": g("act3_big_boo_spawn", lp(a3["big_boo_spawn"], 3.0), kind="air",
                           note="3 m over the coffee bar floor"),
        "star_ghost_hunt": g("act3_star_GhostHuntBooStarPos", lp(a3["star_GhostHuntBooStarPos"]), clear=0.3,
                             note="gLevelValues.starPositions.GhostHuntBooStarPos = this game point + 1.6 m up "
                                  "(vec3f_set, game units)"),
        "star_balcony": g("act3_star_BalconyBooStarPos", lp(a3["star_BalconyBooStarPos"]), clear=0.3,
                          note="optional BalconyBooStarPos: the F2 balcony over the Plaza Hall (+1.4 m)"),
    }
    a4 = L["design_act4_lights_out"]
    pts["act4_lights_out"] = {
        "breakers": {k: g(f"act4_breaker_{k}", lp(b), note=b.get("note"), clear=0.5) for k, b in a4["breakers"].items()},
        "breaker_panels": [g(k, v["pos"], facing=v["facing"], clear=0.0) for k, v in sorted(M.anchors.items())
                           if k.startswith("breaker_panel_")],
        "electrical_room_doors": [{"floor": d["floor"], "room": d["room"],
                                   "door": g(f"act4_door_{d['room']}", (*d["centre"], Z[d["floor"]]),
                                             facing=d["facing"], clear=0.15)}
                                  for fl in FLOORS for d in M.doors[fl] if d["type"] == "electrical_room"],
        "star_target": g("act4_star_target", lp(a4["star"]), clear=0.3,
                         note="the Neuharth Reading Room, in front of the news TV; hover ~1.2 m"),
        "lighting": a4["lighting"],
    }
    a5 = L["design_act5_coffee_run"]
    pts["act5_coffee_run"] = {
        "start": g("act5_start", lp(a5["start"]), facing=0.0, clear=0.5, note=a5["start"].get("note")),
        "cup": g("act5_cup", (*M.anchors["coffee_counter_top"]["pos"][:2], M.anchors["coffee_counter_top"]["pos"][2]),
                 clear=0.0, note="on the coffee counter (top 1.1 m)"),
        "goal": g("act5_goal", (27.9, 263.1, Z["F5"] + 1.0), clear=0.0,
                  note="the break room counter's coffee maker (counter top 1.0 m)"),
        "par_s": a5["par_s"],
        "boo_blocks": [g(f"act5_boo_block_{k}", M.anchors[f"{b['stair']}_{lvl}_turn"]["pos"], clear=0.5,
                         note=f"{b['stair']} {b['landing']}")
                       for k, b in enumerate(a5["boo_blocks"])
                       for lvl in [FLOORS[int(round(b["z_game_m"] - 3.0)) // 6]]],
        "route": a5["route"],
    }
    a6 = L["design_act6_glowing_books"]
    reds = []
    for k, r in enumerate(a6["red_coins"]):
        x, y = r["pos_m"]
        note = r.get("note", "")
        p = (x, y, Z[r["floor"]])
        best = None
        for st in M.stack_tops:                       # a book on a range / shelf / unit top: snap to that top
            if st["floor"] == r["floor"] and math.dist((x, y), st["pos"][:2]) < 1.6 and \
                    (best is None or math.dist((x, y), st["pos"][:2]) < math.dist((x, y), best["pos"][:2])):
                best = st
        if best is not None and ("range" in note or "Judaica" in note):
            p = (x, best["pos"][1], best["pos"][2])
        elif "Recreational" in note:
            p = (x, y, M.anchors["shelf_top_rra_shelf"]["pos"][2])
        elif "newspaper" in note:
            p = (x, y, M.anchors["shelf_top_newspaper_racks"]["pos"][2])
        elif "Reading Nook" in note:
            p = (x, y, M.anchors["shelf_top_nook_shelf"]["pos"][2])
        elif "rooftop unit" in note:
            p = M.anchors["roof_unit_rooftop_unit_1"]["pos"]
        elif "lockers" in note:
            p = (x, M.anchors["lockers_top_lockers_f6"]["pos"][1], M.anchors["lockers_top_lockers_f6"]["pos"][2])
        reds.append(g(f"act6_red_{k + 1}", p, note=note, clear=0.0, float_m=0.6))
    pts["act6_glowing_books"] = {"red_coins": reds}
    pts["stack_tops"] = [g(s["name"], s["pos"], note=s.get("label"), length_m=s["length_m"], height_m=s["height_m"],
                           main=s["main"], clear=0.3) for s in M.stack_tops]
    pts["group_study_rooms"] = [
        {"room": d["room"], "floor": d["floor"], "name": d["room_name"], "door_a_m": list(d["a"]), "door_b_m": list(d["b"]),
         "door_width_m": d["width"], "door_head_m": d["head"], "facing_deg": d["facing"],
         "door": g(f"room_{d['room']}_door", (*d["centre"], Z[d["floor"]]), facing=d["facing"], clear=0.15),
         "inside": g(f"room_{d['room']}_inside", _inside_point(d), facing=(d["facing"] + 180) % 360, clear=0.35)}
        for fl in FLOORS for d in M.doors[fl] if d["type"] == "group_study"]
    pts["rooms"] = [{"room": d["room"], "floor": d["floor"], "type": d["type"], "name": d["room_name"],
                     "door": g(f"room_{d['room']}_door", (*d["centre"], Z[d["floor"]]), facing=d["facing"],
                               clear=0.15)}
                    for fl in FLOORS for d in M.doors[fl] if d["type"] != "group_study"]
    pts["locked_doors"] = [{"floor": d["floor"], "room": d["room"], "id": d["id"], "a_m": list(d["a"]),
                            "b_m": list(d["b"])} for fl in FLOORS for d in M.locked[fl]]
    pts["circulation"] = [g(k, v["pos"], facing=v["facing"], clear=0.5)
                          for k, v in sorted(M.anchors.items())
                          if k.startswith(("stair_", "escalator", "ada_elevator", "elevator_a_door"))
                          and not k.endswith("bulkhead_top")]
    pts["elevator_a_shaft"] = g("elevator_a_shaft_bottom", M.anchors["elevator_a_shaft_bottom"]["pos"], clear=0.3,
                                note="car A (OUT OF ORDER): an open wall-kick shaft F1 -> F6 ceiling, inner "
                                     + str(M.anchors["elevator_a_shaft_bottom"]["shaft_inner_m"]) + " m")
    pts["landmarks"] = [g(k, v["pos"], facing=v["facing"], clear=0.0)
                        for k, v in sorted(M.anchors.items())
                        if k in ("plaza_hall_centre", "balcony_rail", "coffee_counter_top", "coffee_customer_side",
                                 "news_tv", "self_checkout", "bloomberg_terminal", "counter_circ_counter",
                                 "counter_research_desk", "stair_nw_bulkhead_top", "stair_ne_bulkhead_top")
                        or k.startswith("roof_unit_") or k.startswith("lockers_top_")]
    pts["terraces"] = [g("terrace_w", (4.5, 270.0, Z["F4"]), clear=0.5), g("terrace_n", (39.0, 300.0, Z["F4"]), clear=0.5),
                       g("terrace_e", (72.0, 270.0, Z["F4"]), clear=0.5),
                       g("terrace_door_w", (10.6, 263.2, Z["F4"]), facing=270.0, clear=0.5),
                       g("terrace_door_n", (38.8, 284.2, Z["F4"]), facing=0.0, clear=0.5)]
    pts["views"] = [g("view_f6_big_window", (38.9, 260.6, Z["F6"]), facing=188.0, clear=0.3,
                      note="Century Tower lit, 289 m at 188 deg, over the Plaza of the Americas"),
                    g("view_stair_w_turn_landing", M.anchors["stair_w_F2_turn"]["pos"], facing=180.0, clear=0.3,
                      note="a turn landing against the glass: the Plaza at night")]
    M.points = pts


def _inside_point(d):
    f = math.radians(d["facing"])
    x, y = d["centre"]
    return (x - math.sin(f) * 0.9, y - math.cos(f) * 0.9, Z[d["floor"]])


def plan_views(M):
    """Preview cameras: (name, location, target, Mario stand-in (x, y, z, facing) or None, vfov)."""
    sp = M.layout["entrance"]["spawn"]["pos_m"]
    M.views = [
        ("libwest_entrance", (38.9, 259.4, 2.4), (38.8, 276.0, 5.0), (sp[0], sp[1], 0.0, 0.0), 60.0),
        ("libwest_plaza_hall", (50.6, 273.6, 9.0), (33.0, 260.5, 3.0), None, 62.0),
        ("libwest_lobby_glass", (38.8, 274.0, 8.4), (38.8, 230.0, 2.0), (30.8, 266.7, 0.0, 180.0), 64.0),
        ("libwest_stacks", (17.8, 296.6, 8.4), (17.8, 314.0, 7.2), (17.8, 301.4, 6.0, 0.0), 56.0),
        ("libwest_stacks_f1", (38.75, 297.0, 2.6), (38.75, 315.0, 1.6), (38.75, 301.0, 0.0, 0.0), 58.0),
        ("libwest_study_floor", (27.6, 268.0, 15.4), (52.0, 259.6, 12.4), (33.2, 263.4, 12.0, 115.0), 62.0),
        ("libwest_neuharth", (62.0, 266.4, 14.6), (78.6, 260.0, 13.2), (72.0, 262.0, 12.0, 90.0), 56.0),
        ("libwest_windows_plaza", (38.9, 266.8, 32.6), (38.4, 200.0, 29.0), (38.9, 260.5, 30.0, 180.0), 58.0),
        ("libwest_top_floor", (27.4, 267.2, 33.2), (51.0, 261.5, 30.6), (32.0, 266.2, 30.0, 110.0), 62.0),
        ("libwest_quiet_floor", (14.0, 279.4, 20.6), (46.0, 278.0, 18.6), (24.0, 279.0, 18.0, 90.0), 56.0),
        ("libwest_north_terrace", (30.0, 306.0, 21.4), (40.0, 283.0, 24.0), (36.0, 298.0, 18.0, 180.0), 60.0),
        ("libwest_west_terrace", (2.0, 284.0, 20.6), (10.0, 258.0, 19.4), (4.0, 272.0, 18.0, 180.0), 58.0),
        ("libwest_stair_landing", (22.3, 265.0, 12.6), (22.3, 250.0, 9.4), (22.3, 260.0, 9.0, 180.0), 62.0),
        ("libwest_study_rooms", (6.4, 267.0, 8.6), (16.0, 262.0, 6.8), (10.4, 267.0, 6.0, 90.0), 58.0),
        ("libwest_f5_corridor", (13.0, 275.9, 26.4), (54.0, 275.9, 24.6), (20.0, 275.9, 24.0, 90.0), 56.0),
        ("libwest_coffee_bar", (40.0, 262.0, 2.8), (49.0, 268.0, 1.6), (46.0, 266.0, 0.0, 90.0), 56.0),
    ]


# ================================================================== lighting (per group)
def lighting(M):
    """interior_kit.Lighting per kit group (the night bake): a dim warm interior (most troffers off), desk lamps,
    lit stair halls, cool blue light just inside every glass band, moonlit terraces, a dark-blue backdrop with
    floodlights on Century Tower."""
    lights = M.kit.lights()
    for fid, a, b, s0, s1, oz0, oz1 in M.glass_lights:
        L = math.dist(a, b)
        dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        ix, iy = -dy, dx
        n = max(1, int(round((s1 - s0) / 4.0)))
        for k in range(n):
            s = s0 + (s1 - s0) * (k + 0.5) / n
            lights.append(K.Light((a[0] + dx * s + ix * 1.2, a[1] + dy * s + iy * 1.2, Z[fid] + (oz0 + oz1) / 2),
                                  radius=4.5, strength=0.16, color=GLASS_BLUE))
    night = dict(sky=(0.46, 0.43, 0.41), ground=(0.25, 0.25, 0.29), key=(0.3, -0.4, 0.8), key_strength=0.05)
    out = {g: K.Lighting(lights, **night) for g in ("F1", "F2", "F3", "F4", "F5", "F6", "halls")}
    out["halls"] = K.Lighting(lights, sky=(0.52, 0.52, 0.55), ground=(0.33, 0.33, 0.37), key_strength=0.05)
    out["F5"] = K.Lighting(lights, sky=(0.40, 0.40, 0.44), ground=(0.23, 0.23, 0.27), key_strength=0.04)
    out["roof"] = K.Lighting(lights, sky=(0.44, 0.48, 0.62), ground=(0.3, 0.32, 0.4), key=(0.4, -0.6, 0.7),
                             key_strength=0.12)
    flood = []
    ct = M.stats.get("century_tower")
    if ct:
        for dxy in ((-7, -7), (7, -7), (7, 7), (-7, 7)):
            flood.append(K.Light((ct[0] + dxy[0], ct[1] + dxy[1], 2.0), radius=40.0, strength=0.9,
                                 color=(1.0, 0.88, 0.65)))
    for (lx, ly) in M.stats.get("backdrop_lamp_spots", []):
        flood.append(K.Light((lx, ly, 3.6), radius=9.0, strength=0.35, color=(1.0, 0.85, 0.55)))
    flood.append(K.Light((38.8, 252.0, 4.0), radius=14.0, strength=0.35, color=(1.0, 0.86, 0.6)))   # the glass wall
    out["backdrop"] = K.Lighting(flood, sky=(0.17, 0.20, 0.32), ground=(0.10, 0.11, 0.18), key=(0.4, -0.6, 0.7),
                                 key_strength=0.10)
    M.lighting = out
    M.stats["lights"] = len(lights)
    return out


# ================================================================== the build
def build(layout=None, campus=None, backdrop=True):
    """-> LibWest: the whole stage as an interior_kit.Kit (groups F1..F6, halls, roof, backdrop)."""
    layout = layout or load_layout()
    LAYOUT_CACHE.clear()
    LAYOUT_CACHE.update(layout)
    M = LibWest(layout)
    for fid in FLOORS:
        M.regions[fid] = regions_of(M, fid)
    register_footprints(M)
    plan_doors(M)
    for fid in FLOORS:
        build_floor(M, fid)
    build_roof(M)
    for hid in HALLS:
        build_hall(M, hid)
    build_elevators(M)
    build_escalators(M)
    build_plaza_hall(M)
    if backdrop:
        build_backdrop(M, campus)
    MH.fix_uv_spans(M)
    moonlit_exterior(M)
    plan_pickups(M)
    plan_points(M)
    plan_views(M)
    lighting(M)
    return M


EXTERIOR_MATS = {"brick_red", "brick_dark", "dark_trim", "roof_gravel", "roof_tile_red", "white_trim", "metal_gray",
                 "concrete"}


def moonlit_exterior(M, k=0.82, tint=(0.76, 0.82, 1.0)):
    """The building's outside faces (brick, trims, roofs, the terrace pavers and parapets) share their floor's
    interior bake; scale them down and toward blue so the outside reads as moonlight. Interior surfaces use the
    int_* materials, so the material alone tells them apart."""
    n = 0
    for _, g, pr in M.kit.items:
        if g == "backdrop":
            continue
        for p in pr.visual.polys:
            if p.mat in EXTERIOR_MATS and not p.glow:
                p.ao = [a * k for a in p.ao]
                t0 = p.tint or (1.0, 1.0, 1.0)
                p.tint = tuple(a * b for a, b in zip(t0, tint))
                n += 1
    M.stats["moonlit_faces"] = n


def report(M):
    return MH.report(M)


def preview_world():
    """Blender (previews only): a dark-blue night world instead of interior_kit_demo's day sky."""
    import bpy
    w = bpy.context.scene.world
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (*BACKGROUND_COLOR, 1.0)
    nt.links.new(bg.outputs[0], out.inputs[0])


# ================================================================== checks (pure Python)
def selftest(verbose=True):
    errors = []
    M = build(backdrop=True)
    rep = report(M)
    if verbose:
        print(json.dumps(rep, indent=1))
        print("doors:", {k: len(v) for k, v in M.doors.items()}, "locked:", {k: len(v) for k, v in M.locked.items()},
              "sealed:", M.notes.get("sealed_rooms"), "unplaced openings:", M.notes.get("unplaced_openings"))
        print("stats:", json.dumps({k: v for k, v in M.stats.items() if k != "backdrop_lamp_spots"}))
        print("unplaced props:", M.notes.get("unplaced_props"))
        print("pickups:", len(M.pickups), "coins planned:",
              sum({"coin": 1, "coin_line": 5, "coin_ring": 8}.get(p["kind"], 0) for p in M.pickups))
    col = rep["total"]["collision"]
    if col > 12000:
        errors.append(f"collision {col} tris (budget ~7000-11000)")
    for poly in (p for _, _, pr in M.kit.items for p in pr.visual.polys):
        if not K.known_material(poly.mat):
            errors.append(f"unknown material {poly.mat}")
            break
    for _, _, pr in M.kit.items:
        for poly in pr.collision.polys:
            if poly.mat not in K.COL_NAMES + (COL_SLIDE,):
                errors.append(f"{pr.kind}: collision material {poly.mat}")
                break
    worst = 0.0
    for _, _, pr in M.kit.items:
        for poly in pr.visual.polys + pr.collision.polys:
            for x, y, z in poly.pts:
                worst = max(worst, abs(x - CENTER[0]), abs(y - CENTER[1]), abs(z))
    if worst > 320.0:
        errors.append(f"a vertex is {worst:.1f} m from the centre")
    issues = []
    for _, _, pr in M.kit.items:
        issues += K.uv_span_issues(pr.visual)
    if issues:
        errors.append(f"{len(issues)} faces exceed the UV span: {issues[:3]}")
    # the spawn stands on the lobby floor with room around it
    sp = M.layout["entrance"]["spawn"]["pos_m"]
    if not M.walkable("F1", *sp):
        errors.append("spawn not on walkable F1 floor")
    if verbose:
        print(f"max |coord| from centre: {worst:.1f} m; selftest:", "OK" if not errors else errors)
    return errors


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(1 if selftest() else 0)
    print(__doc__)
