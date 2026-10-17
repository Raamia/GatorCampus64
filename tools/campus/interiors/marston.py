"""Course 4: the Marston Science Library INTERIOR (slot ccm, LEVEL_CCM, hub door 4), built from
data/uf/marston_layout.json with the interior kit (tools/campus/interior_kit.py).

Pure Python (no bpy): build() returns a Marston object holding an interior_kit.Kit of the whole stage
(map metres, z up, campus.json origin), the per-group Lighting for the vertex-colour bake, the anchor
points the mission author needs (measured on the built collision by tools/campus/build_interior.py), the
pickups plan, the preview cameras and the build notes. tools/campus/build_interior.py turns it into the
DynOS level mods/sgl64/levels/ccm/ (docs/flow.md 3.2 / 7).

    tools/.venv/bin/python -I tools/campus/interiors/marston.py --selftest     (geometry checks, no Blender)

What is built (docs/marston_layout.md has the research; every deviation from 1:1 is listed in NOTES)
  * Five floors on their real plan footprints (the registered UF floor plans, 1:1 in x / y): F1 basement
    (z -6, the Collaboration Commons: 21 glass group-study rooms, makerspace, labs, the book-sorting room,
    the north lab's walk-in vent duct), F2 entrance floor (z 0: north porch + vestibule + lobby, service
    desk, Starbucks, atrium court, computer lab, sci-fi stacks, group rooms 201D-H), F3 (z 6: periodicals,
    theses, classroom L308, wellness room, data room, the fish tank), F4 (z 12, the QUIET floor: A-QC /
    QC-Z stacks, quiet carrels, east + south terraces), F5 (z 18, the SILENT floor: north / west reading
    rooms with the view windows, upper terraces), and the roof deck (z 24) with the atrium skylight and the
    two brick towers (29.7 m).
  * Floors are 6.0 m apart in the game (real ~4.2 m): 5.4 m of clear height for the SM64 camera
    (interior_kit.CAMERA_CEILING_M = 5.0). Plan dimensions stay 1:1.
  * Vertical circulation: the NE and SW stair halls (wide 30 deg switchbacks, F1 -> roof / F1 -> F5), the
    west core (steep 35 deg secondary stair + two elevators: elevator 1 is OUT OF ORDER with its doors open
    on F2-F5, a wall-kick shaft; elevator 2 is closed), the freight elevator (closed), the atrium
    (13.2 x 14.8 m, F2 floor -> skylight at 24 m) with its grand stair F2 -> F3, and the book-return chute
    (a slide from the F2 vestibule nook down to the F1 sorting room).
  * Stacks are kit bookshelves (1.2 m deep, 2.3 m tall as the layout; the layout's 3.6 m "tall" ranges are
    built 3.0 m: TALL_RANGE_H) with 1.07 m end-cap steps (and a 2.29 m middle step on the tall ranges), so every
    range top is reachable by single jumps. Book-cart bridges (2.3 m) cross the aisles between neighbouring
    ranges at their climbing ends, so the range tops of a row join up into one route; the camera passes through
    stacks, bridges, glass and furniture ('COL nocam').
  * Windows are real glass (the OCEAN_SKY skybox and a low-poly campus backdrop show through): the north
    porch storefront, the court glass, ribbon windows, the 5th floor's view windows toward Century Tower.
    The backdrop is the OSM campus around Marston (ground, walks, roads, trees, the buildings extruded from
    campus.json at their real heights, Century Tower, the glass court roof, the 'French Fries').
  * Outside is never walkable: the backdrop has no collision, so every porch / terrace / roof edge is an
    SM64 out-of-bounds edge (no floor beyond it), which stops Mario like a wall.
  * Photo-reference passes (reference/interiors/marston/index.json, 118 photos; contact sheets in
    art/levels/marston/reference_sheets/): every space that is photographed is furnished and finished as the photos
    show it (interiors/marston_props.py has the pieces; '#n' in the comments = the photo). Floors 2-5 keep the 1987
    coffered ceiling (shallow four-facet pyramids on dark ribs, a lay-in light / grille / downlight in one facet),
    floor 1 and the rooms the 2014 flat 2' tile; walls, columns (copper / terracotta cap bands), carpets, accent
    walls, furniture families (Sayl chairs, maple benching with frosted dividers, perforated 2022 carrels, lounge
    cubes, pods, banquettes, hexagon ottomans), signs and the window views (Century Tower's crown, the Auditorium's
    gable, the plaza oaks) follow the photos. Unphotographed spaces (atrium, stair halls, upper-floor elevator
    lobbies) stay as inferred in docs/marston_layout.md. Deviations: NOTES.
Coordinates: map metres; game X = (x - cx) * 100, Y = z * 100, Z = -(y - cy) * 100 with (cx, cy) = CENTER.
"""
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
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import interior_kit as K  # noqa: E402
import marston_props as MP  # noqa: E402  (the photo-reference furniture / fixtures, interiors/marston_props.py)

LAYOUT_PATH = os.path.join(ROOT, "data", "uf", "marston_layout.json")
CAMPUS_PATH = os.path.join(ROOT, "data", "uf", "campus.json")

# ------------------------------------------------------------------ stage identity (docs/flow.md 2 / 3.2)
KEY = "marston"
SLOT = "ccm"
LEVEL_CONST = "LEVEL_CCM"
COURSE_CONST = "COURSE_CCM"
DOOR = 4
CENTER = (-59.6, -98.9)                 # stages.json interior_stages[marston_interior].center_m

# ------------------------------------------------------------------ level look
MUSIC = "SEQ_LEVEL_INSIDE_CASTLE"       # Peach's castle interior theme: calm, indoor; not CCM's snow theme
TERRAIN = "TERRAIN_STONE"               # not TERRAIN_SNOW: no shivering idle, no snow footsteps
BACKGROUND = "OCEAN_SKY"
FOG_RGB = (182, 204, 228)

# ------------------------------------------------------------------ vertical frame (game metres)
FLOORS = ("F1", "F2", "F3", "F4", "F5")
Z = {"F1": -6.0, "F2": 0.0, "F3": 6.0, "F4": 12.0, "F5": 18.0, "ROOF": 24.0}
STOREY = 6.0                            # game floor-to-floor (real ~4.2 m: docs/marston_layout.md 4)
SLAB = 0.6                              # slab thickness: clear height 5.4 m
CLEAR = STOREY - SLAB
TOWER_TOP = 29.7                        # NE / SW brick towers
TOWER_ROOF_T = 0.6
WALL_T = 0.30                           # exterior wall: the plan line is the INSIDE face
PARAPET_H = 1.1                         # terraces
ROOF_PARAPET_H = 1.0
DOOR_H = 2.6                            # door / gap head height (real 2.13 m doors; co-op + camera)
STUDY_DOOR_W = 1.8                      # glass study-room door gaps (real 0.91 m doors)
ROOM_DOOR_W = 2.4                       # other rooms
GLASS_T = 0.10
PART_T = 0.20                           # solid partitions
# collision thickness of the thin things (fix round): an AIRBORNE Mario is pushed to the front of every wall
# plane within 50 units (coopdx v1.5.1 keeps the vanilla push in the air), so a two-faced wall thinner than the
# distance he moves in a quarter step (a 48 u/f long jump or dive: 12) throws him through it, into the next
# room (glass room L129: act 3's lock) or over a balcony railing. 0.24 m needs over 96 u/f.
THIN_COL_T = 0.24
# stacks (fix round): the layout's 3.6 m ranges left 1.8 m under the 5.4 m ceiling (a jump on top rose 0.2 m: walk-only
# dead ends); at 3.0 m a jump rises 0.8 m and a long jump reaches the next range. Bridges: BRIDGE_* below.
TALL_RANGE_H = 3.0
BRIDGE_T = 0.08                         # book-cart bridge plank thickness (top at the range tops' 2.3 m)
BRIDGE_ON = 0.15                        # how far a bridge rests on each range top (overlapping decks at the seams)
COL_SLIDE = "COL slide"                 # SURFACE_SLIPPERY (the book chute); build_interior makes the material

CARPET_TINT = {"F1": (0.80, 0.97, 0.78), "F2": (1.0, 0.93, 0.86), "F3": (1.0, 0.86, 0.84),
               "F4": (0.86, 0.94, 1.0), "F5": (0.93, 0.86, 1.0)}
ACCENT_TINT = {"F1": (0.66, 0.92, 0.42), "F2": (1.0, 1.0, 1.0), "F3": (1.0, 0.74, 0.68),
               "F4": (0.62, 0.80, 1.0), "F5": (0.80, 0.64, 1.0)}

# ------------------------------------------------------------------ photo-reference pass (reference/interiors/marston)
# What each floor looks like in the photos (#n = reference/interiors/marston/index.json "n"):
#   F1 (2014 Collaboration Commons, Brame Heck): flat white 2 x 2 tile ceiling with linear LED slots, aluminium ring
#      pendants (purple / blue / olive inside), translucent blue wave ribbons over the elevator lobby, white columns,
#      red-brick core walls, purple / yellow / olive accent walls, navy-purple multi-stripe carpet [#36-#43, #61-#64, #69]
#   F2-F5 (1987 shell): the coffered ceiling (10 ft inverted pyramids with lay-in lights / diffusers / downlights),
#      white columns with a cap band (copper veneer on F2, terracotta on F3-F5), charcoal-brown linear carpet, black
#      ribbon windows at desk height [#23-#30, #76, #84, #97-#104]
#   F2: teal-blue and golden-yellow accent walls, the copper-banded soffit and lantern over the lounge [#24-#29]
#   F3: coral stack end panels; F4: steel-blue end panels [#83-#93]; F4-F5: dark grey window walls (2022) [#97 #100]
FLOOR_CARPET = {"F1": ("int_ms_carpet_f1", None), "F2": ("int_ms_carpet", None), "F3": ("int_ms_carpet", (0.97, 0.97, 0.98)),
                "F4": ("int_ms_carpet", (0.96, 0.95, 0.94)), "F5": ("int_ms_carpet", (1.0, 0.98, 0.96))}
COLUMN_CAP = {"F1": None, "F2": ("int_ms_veneer", None), "F3": ("int_ms_wall", MP.T_TERRACOTTA),
              "F4": ("int_ms_wall", MP.T_TERRACOTTA), "F5": ("int_ms_wall", MP.T_TERRACOTTA)}
COLUMN_CAP_H = 0.85                     # real ~0.5 m band in a ~2.9 m room; scaled with the 5.4 m game ceiling
COLUMN_W = 0.70
WINDOW_WALL_TINT = {"F2": None, "F3": (0.80, 0.81, 0.82), "F4": MP.T_GREY_WALL, "F5": MP.T_GREY_WALL}
WINDOW_BAY = 1.25                       # ribbon-window mullion spacing (real ~1.1-1.3 m, #76 #104)
WINDOW_FRAME = "int_plastic"            # black anodised frames
COFFER = 3.048                          # the 1987 coffers: a 10 ft grid, three per 30 ft module bay
COFFER_DEPTH = 0.42                     # recessed into the 0.6 m slab: visual only, the collision ceiling stays flat
COFFER_ORIGIN = (-33.54, -125.0)        # the module grid's SE corner (docs/marston_layout.md 3)
BRICK_UV = {"int_ms_brick": (0.84, 0.54)}
STOREFRONT_HEAD = 3.9                   # the north storefront's glass head (the copper cladding above, #1)   # anisotropic tiles (u along the wall, v up): modular brick 0.21 x 0.0675 m

# photo pass 2: window bands the photos show differently from the layout (sill, head in metres above the floor)
WINDOW_OVERRIDES = {
    "f1_lightwell_w": (0.10, 3.40),     # full-height black-mullion glazing to the light well (#54 #57)
}
# rooms the photos show with solid (painted) walls although the layout calls them glass: L136 (#47 #49 beige walls,
# a door with a vision slot), classroom L308 (#78 white walls, wood door with a vision slot), the data room (#77)
SOLID_ROOMS = {"L136", "L308", "data_room"}
T_BEIGE_WALL = (0.98, 0.92, 0.78)

# ------------------------------------------------------------------ vertical circulation (map metres)
NE_HALL = [(-39.6, -79.0), (-39.6, -67.4), (-50.9, -67.4), (-52.6, -69.0), (-52.6, -79.0)]
NE_RECT = (-52.6, -79.0, -39.6, -67.4)
SW_RECT = (-90.82, -118.95, -79.46, -107.8)
SW_RECT_F1 = (-90.82, -118.95, -80.2, -107.8)
CORE_RECT = (-77.8, -90.6, -69.7, -83.2)
ELEV1_X = (-76.6, -73.9)                # out of order: open doors F2-F5, wall-kick shaft
ELEV2_X = (-73.5, -70.8)
ELEV_Y = (-90.6, -88.2)
FREIGHT_RECT = (-76.8, -115.9, -73.8, -112.9)
ATRIUM = (-65.0, -107.8, -51.83, -93.0)
STAIR_LANDING = (-65.0, -107.8, -61.5, -104.9)      # top landing of the grand stair (part of F3)
GRAND_STAIR_X = (-65.0, -61.5)
ATRIUM_PILLARS = [(-60.97, -97.57), (-60.97, -106.71)]
CHANDELIER = {"pos": (-58.4, -100.4), "top_z": 15.0, "radius": 2.0, "ring_w": 0.8}
SKYLIGHT_RIDGE = 3.0
PORCH = (-71.0, -75.5, -52.6, -69.0)
ARENA = [(-80.2, -115.4), (-56.0, -115.4), (-56.0, -96.8), (-80.2, -96.8)]     # Act 5 Printer Jam (F1)
# book-return chute: hatch in the F2 nook west of the vestibule -> slide -> F1 sorting room
CHUTE_HATCH = (-71.0, -78.0, -69.8, -76.4)
# z_top -2.0 (integration pass; was -1.25): where the slide passes under the F2 slab (the hatch's west edge, x -71.0)
# its surface must be more than 1.6 m under the slab's underside (-0.6), or SM64's ground step stops Mario there
# (floorHeight + 160 >= ceilHeight). At -1.25 it was 1.26 m: Mario stuck in the hatch pit. Now 1.91 m (24 deg slide,
# still slippery: SURFACE_SLIPPERY slides from 20 deg).
CHUTE = {"y": (-78.0, -76.4), "x_top": -69.85, "z_top": -2.0, "x_bottom": -78.8, "z_bottom": -6.0}
# walk-in vent duct along the F1 north lab's west wall: floor -3.4, ceiling -1.4
DUCT = {"x": (-83.1, -81.1), "y": (-74.3, -55.0), "z0": -3.4, "z1": -1.4, "t": 0.15}
SORTING_DOOR = ((-69.7, -80.6), (-69.7, -78.2))     # F1 sorting room door (east wall, see NOTES)
SBUX_LOBBY_DOOR = ((-79.1, -91.4), (-79.1, -89.0))  # Starbucks entry -> core lobby (gameplay)

NOTES = {
    "scale": "Plan (x, y) 1:1 to the registered UF floor plans (docs/marston_layout.md 3); floors 6.0 m apart "
             "in the game (real ~4.2 m, estimate): 5.4 m clear for the SM64 camera.",
    "deviations": [
        "Floor-to-floor 6.0 m (real ~4.2 m): camera headroom over 2.3-3.6 m stacks; one backflip no longer "
        "clears a floor.",
        "Atrium 13.2 x 14.8 m from the F2 court to a roof skylight (real: one 9.14 m cell over F2-F3), with a "
        "grand stair F2 -> F3 on its west edge (drawn by the architect in 1987, never built).",
        "Stacks 1.2 m deep with ~3.4 m aisles (real ~0.6 m / ~1 m), 2.3 m and 3.0 m tall (the layout's 3.6 m "
        "ranges capped: room to jump on top under the 5.4 m ceiling), end-cap steps, book-cart bridges across "
        "the aisles at the climbing ends.",
        "Doors 1.8-2.6 m wide, 2.6 m tall (real 0.91 x 2.13 m); glass partitions run floor to ceiling, so "
        "every glass room is sealed except its door gap (no doors are modelled in the gaps).",
        "NE / SW towers are whole stair halls (6.15 / 5.25 m lanes, 30 deg); the core stair is 35 deg with "
        "2.2 m lanes; the tower restrooms are dropped.",
        "Terraces (z 12, 18) and the roof deck (z 24) are walkable; the roof is reached by the NE stair hall.",
        "Book-return chute, vent duct, chandelier ring, out-of-order elevator shaft, booking kiosks: game "
        "devices (docs/game_design.md 7.3).",
        "The F1 sorting-room door is on the room's east wall (the layout's south door would open onto the "
        "core stair's lowest flight); the Starbucks entry also opens east toward the elevator lobby.",
        "Window bands are taller than the real ribbons (sill 1.0, head 3.6 m) so the campus reads through them.",
        "Makerspace (photo pass 2, #50-#60): black-framed glass front on the elevator lobby with a 2.4 m door gap "
        "(real: one door leaf), red brick on the Commons side with a 4.8 m opening (the layout's Act 5 arena "
        "access; real: solid), full-height light-well glazing on the west (#54 #57).",
        "Floor-1 west Commons (the layout's Act 5 'Printer Jam' arena, an unbuilt 'coming soon' act) is furnished "
        "like the rest of the Commons, as photographed (#36 #39 #40); a future act 5 must clear or use it.",
        "Walls between two rooms are white drywall; only the open-floor side of a glass room is glass (#38 #44). "
        "L136, L308 and the data room have painted walls (#47 #49 #77 #78) although the layout calls them glass.",
        "Two of the four F2 exhibit cases stand in the entrance lobby (real: 2 x 2 there); the game lobby is "
        "narrower (the west core takes its west half), so two are left out.",
        "Ceiling heights stay 5.4 m (camera), so the coffers (real 10 ft squares, kept 1:1) read flatter than in "
        "the photos and the F1 ring pendants hang 0.75 m down from a 5.4 m ceiling (real ~2.9 m).",
        "Backdrop: the live oaks between Marston and Century Tower are placed on a jittered grid (positions "
        "inferred; the photos #99 #104 show an unbroken canopy that OSM does not map).",
        "Fix round 5: the two F1 emergency exits (plan S2: west wall by the core, north end of the North Lab) are "
        "opaque painted-steel door pairs with push bars and EXIT ONLY placards and an EXIT sign over each "
        "(unphotographed: the usual type, inferred). The below-grade areaways they open onto are not built.",
        "Fix round 5: two steel cabinets flank the book chute's outlet in the F1 sorting room (game device), so the "
        "low end of the chute's rails is solid from the room side.",
        "Open door leaves (study rooms, L308, the data room) and chairs are visual only: players pass through them "
        "(the door gaps stay clear for co-op traffic). Tables, desks, carrels, counters and shelving have collision.",
        "Porch: its open north and west sides are invisible walls (camera passes) up to the F4 slab, so nobody steps "
        "off into the plaza (the basement runs under it).",
    ],
    # photo pass 2 corrections to docs/marston_layout.md (sourced by reference/interiors/marston/index.json)
    "sourced_now": [
        "Starbucks' interior door from the library is real (Alligator 2015: court doors by day, interior doors after "
        "sundown and on weekends), not a gameplay invention.",
        "The floor-1 elevator lobby has two stainless cars in a red brick wall (#69): the two-car core is confirmed "
        "for that floor.",
        "Floor 2 accent colours are teal-blue and golden yellow (#24 #29), not UF orange; floor 3 stack ends are "
        "coral (#83 #91), floor 4's steel blue (#84-#86).",
    ],
}


# ================================================================== 2D helpers (map metres)
def signed_area(p):
    a = 0.0
    for (x1, y1), (x2, y2) in zip(p, p[1:] + p[:1]):
        a += x1 * y2 - x2 * y1
    return a / 2.0


def ccw(p):
    p = [(float(x), float(y)) for x, y in p]
    return p if signed_area(p) >= 0 else list(reversed(p))


def rect_poly(r):
    x0, y0, x1, y1 = r
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def bbox(p):
    xs, ys = [q[0] for q in p], [q[1] for q in p]
    return (min(xs), min(ys), max(xs), max(ys))


def pip(pt, poly):
    """Point in polygon (even-odd)."""
    x, y = pt
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y):
            xc = xi + (y - yi) * (xj - xi) / (yj - yi)
            if x < xc:
                inside = not inside
        j = i
    return inside


def in_rect(pt, r, m=0.0):
    return r[0] - m < pt[0] < r[2] + m and r[1] - m < pt[1] < r[3] + m


def clip_rect(poly, x0, y0, x1, y1):
    """Sutherland-Hodgman: the part of `poly` inside the rectangle (the rectangle is the convex clipper)."""
    def clip(pts, inside, inter):
        out = []
        for i in range(len(pts)):
            cur, prev = pts[i], pts[i - 1]
            ci, pv = inside(cur), inside(prev)
            if ci:
                if not pv:
                    out.append(inter(prev, cur))
                out.append(cur)
            elif pv:
                out.append(inter(prev, cur))
        return out

    def ix(xv):
        return lambda a, b: (xv, a[1] + (b[1] - a[1]) * (xv - a[0]) / (b[0] - a[0]))

    def iy(yv):
        return lambda a, b: (a[0] + (b[0] - a[0]) * (yv - a[1]) / (b[1] - a[1]), yv)
    pts = list(poly)
    for inside, inter in ((lambda p: p[0] >= x0, ix(x0)), (lambda p: p[0] <= x1, ix(x1)),
                          (lambda p: p[1] >= y0, iy(y0)), (lambda p: p[1] <= y1, iy(y1))):
        if not pts:
            return []
        pts = clip(pts, inside, inter)
    out = []
    for p in pts:
        if not out or math.dist(p, out[-1]) > 1e-6:
            out.append(p)
    if len(out) > 1 and math.dist(out[0], out[-1]) < 1e-6:
        out.pop()
    return out


def seg_point_dist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    if L2 < 1e-12:
        return math.dist(p, a)
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def intervals_union(iv):
    out = []
    for a, b in sorted(iv):
        if out and a <= out[-1][1] + 1e-6:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(a, b) for a, b in out]


def intervals_subtract(iv, cut):
    out = list(iv)
    for c0, c1 in cut:
        nxt = []
        for a, b in out:
            if c1 <= a + 1e-6 or c0 >= b - 1e-6:
                nxt.append((a, b))
                continue
            if c0 > a + 1e-6:
                nxt.append((a, c0))
            if c1 < b - 1e-6:
                nxt.append((c1, b))
        out = nxt
    return [(a, b) for a, b in out if b - a > 0.05]


def split_line(a, b, step, extra=()):
    """Sorted cut positions a..b: the extra cuts inside, then every gap longer than step split evenly."""
    xs = sorted({round(a, 4), round(b, 4)} | {round(e, 4) for e in extra if a + 1e-4 < e < b - 1e-4})
    out = [xs[0]]
    for v in xs[1:]:
        gap = v - out[-1]
        if step and gap > step + 1e-6:
            k = int(math.ceil(gap / step - 1e-9))
            base = out[-1]
            for i in range(1, k):
                out.append(round(base + gap * i / k, 4))
        out.append(v)
    return out


def edges(poly):
    return list(zip(poly, poly[1:] + poly[:1]))


def offset_poly(poly, d):
    """Offset a CCW polygon outward by d (mitred corners)."""
    n = len(poly)
    lines = []
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        L = math.dist(a, b) or 1.0
        nx, ny = (b[1] - a[1]) / L, -(b[0] - a[0]) / L
        lines.append(((a[0] + nx * d, a[1] + ny * d), (b[0] + nx * d, b[1] + ny * d)))
    out = []
    for i in range(n):
        (p1, p2), (p3, p4) = lines[i - 1], lines[i]
        d1 = (p2[0] - p1[0], p2[1] - p1[1])
        d2 = (p4[0] - p3[0], p4[1] - p3[1])
        den = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(den) < 1e-9:
            out.append(p3)
            continue
        t = ((p3[0] - p1[0]) * d2[1] - (p3[1] - p1[1]) * d2[0]) / den
        out.append((p1[0] + d1[0] * t, p1[1] + d1[1] * t))
    return out


def wall_tint(level):
    """Stair-hall wall tint: a pastel of the floor's accent colour."""
    a = ACCENT_TINT.get(level, (1.0, 1.0, 1.0))
    return tuple(0.55 + 0.45 * c for c in a)


# ================================================================== geometry builders
def wall_ao(z, zf=0.0, ceil=CLEAR, s=None, L=None):
    k = 1.0 - 0.30 * max(0.0, 1.0 - (z - zf) / 0.9)
    k *= 1.0 - 0.10 * max(0.0, 1.0 - (ceil - z) / 0.8)
    if s is not None and L is not None:
        k *= 1.0 - 0.12 * max(0.0, 1.0 - min(s, L - s) / 0.9)
    return k


class Cells:
    """Rectilinear cell grid over cover polygons with rectangular holes; merge() joins equal cells."""

    def __init__(self, xs, ys):
        self.xs, self.ys = xs, ys
        self.attr = {}
        self.piece = {}

    @classmethod
    def build(cls, cover, holes, xs, ys, attr_fn):
        c = cls(xs, ys)
        boxes = [(poly, bbox(poly)) for poly in cover]
        for i in range(len(xs) - 1):
            for j in range(len(ys) - 1):
                x0, x1, y0, y1 = xs[i], xs[i + 1], ys[j], ys[j + 1]
                ra = (x1 - x0) * (y1 - y0)
                if ra < 1e-8:
                    continue
                best, bp = 0.0, None
                for poly, bx in boxes:
                    if x1 <= bx[0] + 1e-9 or x0 >= bx[2] - 1e-9 or y1 <= bx[1] + 1e-9 or y0 >= bx[3] - 1e-9:
                        continue
                    pc = clip_rect(poly, x0, y0, x1, y1)
                    if len(pc) < 3:
                        continue
                    f = abs(signed_area(pc)) / ra
                    if f > best:
                        best, bp = f, pc
                    if f > 0.999:
                        break
                if best < 0.02:
                    continue
                if best > 0.999:
                    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                else:
                    cx = sum(p[0] for p in bp) / len(bp)
                    cy = sum(p[1] for p in bp) / len(bp)
                if any(in_rect((cx, cy), h) for h in holes):
                    continue
                a = attr_fn(cx, cy)
                if a is None:
                    continue
                c.attr[(i, j)] = a
                if best <= 0.999:
                    c.piece[(i, j)] = ccw(bp)
        return c

    def merge(self, max_w, max_h):
        """-> [(x0, y0, x1, y1, attr)] full cells joined greedily, [(polygon, attr)] partial cells."""
        done = set()
        rects, parts = [], []
        nx, ny = len(self.xs) - 1, len(self.ys) - 1
        for j in range(ny):
            for i in range(nx):
                k = (i, j)
                if k in done or k not in self.attr:
                    continue
                a = self.attr[k]
                if k in self.piece:
                    parts.append((self.piece[k], a))
                    done.add(k)
                    continue
                i2 = i
                while (i2 + 1 < nx and (i2 + 1, j) not in done and self.attr.get((i2 + 1, j)) == a
                       and (i2 + 1, j) not in self.piece and self.xs[i2 + 2] - self.xs[i] <= max_w + 1e-6):
                    i2 += 1
                j2 = j
                while j2 + 1 < ny and self.ys[j2 + 2] - self.ys[j] <= max_h + 1e-6:
                    row = [(ii, j2 + 1) for ii in range(i, i2 + 1)]
                    if all(r not in done and self.attr.get(r) == a and r not in self.piece for r in row):
                        j2 += 1
                    else:
                        break
                for ii in range(i, i2 + 1):
                    for jj in range(j, j2 + 1):
                        done.add((ii, jj))
                rects.append((self.xs[i], self.ys[j], self.xs[i2 + 1], self.ys[j2 + 1], a))
        return rects, parts


def add_raw_poly(km, pts, mat, normal_hint=None):
    """A collision polygon with a material the kit does not know (COL slide): appended directly."""
    pts = [(float(p[0]), float(p[1]), float(p[2])) for p in pts]
    if normal_hint is not None and K._dot(K.newell(pts), normal_hint) < 0:
        pts.reverse()
    km.polys.append(K.Poly(pts, mat, None, [1.0] * len(pts), None, False))


def thick_wall(V, C, a, b, z0, z1, t=WALL_T, in_mat="int_drywall", out_mat=None, openings=(), col_in=True,
               col_out=False, base=True, vis_step=3.0, col_step=10.24, in_tint=None, cam=True, ceil=CLEAR,
               out_step=6.0, frame="int_metal", in_face=True, bay=1.6, sill_ledge=False):
    """Wall from a to b (local z0..z1): the inner face ON the line a-b facing LEFT of a->b (inside a CCW
    room), the outer face t to the right. out_mat: None (no outer face) or f(s, z) -> material / None.
    openings: [{"s0", "s1", "z0", "z1", "kind": door|window|locked|dark}] (s along a->b): door = hole
    (collision too); window = glass pane (collision closed); locked = a closed glass door; dark = an
    opaque dark pane (a closed room seen from outside); steel = a closed, opaque steel exit-door pair (fix round 5:
    the F1 emergency exits, whose glass showed the void below grade).
    col_out: a bool, or f(s) -> bool (fix round 5: the outer collision face only where the outside is reachable,
    decided along the wall instead of from three samples)."""
    L = math.dist(a, b)
    if L < 0.05:
        return
    col_out_fn = col_out if callable(col_out) else None
    if col_out_fn is not None:
        col_out = any(col_out_fn(s) for s in [k * 0.125 for k in range(int(L / 0.125) + 1)])
    dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    nox, noy = dy, -dx

    def at(s):
        return (a[0] + dx * s, a[1] + dy * s)

    def out(s):
        return (a[0] + dx * s + nox * t, a[1] + dy * s + noy * t)

    def mid(s, f=0.5):
        return (a[0] + dx * s + nox * t * f, a[1] + dy * s + noy * t * f)
    ops = [dict(o, s0=max(0.0, o["s0"]), s1=min(L, o["s1"])) for o in openings if o["s1"] - o["s0"] > 0.05]
    holes = [o for o in ops if o["kind"] == "door"]
    cm = K.COL if cam else K.COL_NOCAM
    if in_face and in_mat:
        us = split_line(0.0, L, vis_step, [v for o in ops for v in (o["s0"], o["s1"])])
        zs = split_line(z0, z1, vis_step, ([z0 + 0.10] if base else []) + [v for o in ops for v in (o["z0"], o["z1"])])
        for i in range(len(us) - 1):
            for j in range(len(zs) - 1):
                s0, s1, za, zb = us[i], us[i + 1], zs[j], zs[j + 1]
                sm, zm = (s0 + s1) / 2, (za + zb) / 2
                if any(o["s0"] < sm < o["s1"] and o["z0"] < zm < o["z1"] for o in ops):
                    continue
                m = "int_plastic" if (base and zb <= z0 + 0.1001) else in_mat
                ao = [wall_ao(za, z0, ceil, s1, L), wall_ao(za, z0, ceil, s0, L), wall_ao(zb, z0, ceil, s0, L),
                      wall_ao(zb, z0, ceil, s1, L)]
                V.wall(at(s1), at(s0), za, zb, m, ao=ao, tint=in_tint if m == in_mat else None)
    if out_mat is not None:
        cuts = [v for o in ops for v in (o["s0"], o["s1"])]
        prev, s = None, 0.125
        zmid = (z0 + z1) / 2
        while s < L:
            m = out_mat(s, zmid)
            if prev is not None and m != prev:
                cuts.append(s - 0.125)
            prev = m
            s += 0.25
        uo = split_line(0.0, L, out_step, cuts)
        zo = split_line(z0, z1, out_step, [v for o in ops for v in (o["z0"], o["z1"])])
        for i in range(len(uo) - 1):
            for j in range(len(zo) - 1):
                s0, s1, za, zb = uo[i], uo[i + 1], zo[j], zo[j + 1]
                sm, zm = (s0 + s1) / 2, (za + zb) / 2
                if any(o["s0"] < sm < o["s1"] and o["z0"] < zm < o["z1"] for o in ops):
                    continue
                m = out_mat(sm, zm)
                if m:
                    V.wall(out(s0), out(s1), za, zb, m, ao=1.0)
    ft = (0.55, 0.55, 0.58) if frame == "int_plastic" else None
    for o in ops:
        s0, s1, oz0, oz1 = o["s0"], o["s1"], o["z0"], o["z1"]
        V.wall(out(s0), at(s0), oz0, oz1, frame, ao=0.85, tint=ft)
        V.wall(at(s1), out(s1), oz0, oz1, frame, ao=0.85, tint=ft)
        if oz1 < z1 - 1e-3:
            V.poly([(*at(s0), oz1), (*at(s1), oz1), (*out(s1), oz1), (*out(s0), oz1)], frame, ao=0.8,
                   normal_hint=(0, 0, -1), tint=ft)
        if oz0 > z0 + 1e-3:
            V.poly([(*at(s0), oz0), (*out(s0), oz0), (*out(s1), oz0), (*at(s1), oz0)], frame,
                   normal_hint=(0, 0, 1), tint=ft)
        kind = o["kind"]
        if kind == "steel":
            # a painted steel door pair recessed 0.09 m (push bars, EXIT ONLY placards: int_ms_exit_door), its back
            # face too, so no view through the opening reaches what lies behind the wall
            fi = min(0.3, 0.09 / t) if t > 0 else 0.3
            V.wall(mid(s1, fi), mid(s0, fi), oz0, oz1, "int_ms_exit_door", uvs=K.ONCE, ao=1.0)
            V.wall(mid(s0, fi), mid(s1, fi), oz0, oz1, "int_metal", ao=0.8, tint=(0.42, 0.45, 0.50))
            continue
        if kind in ("window", "locked", "dark"):
            span = s1 - s0
            n_bays = max(1, int(round(span / bay)))
            for k in range(n_bays):
                b0, b1 = s0 + span * k / n_bays, s0 + span * (k + 1) / n_bays
                if kind == "dark":
                    V.wall(mid(b0, 0.7), mid(b1, 0.7), oz0, oz1, "window_dark", ao=1.0)
                else:
                    V.wall(mid(b0), mid(b1), oz0, oz1, "int_glass", ao=1.0)
                if k:
                    p = mid(b0)
                    mw = 0.045 if frame == "int_plastic" else 0.04       # (Library West's int_metal frames: as before)
                    V.box(p[0] - mw, p[1] - mw, oz0, p[0] + mw, p[1] + mw, oz1, frame, faces="+x-x+y-y",
                          tint=(0.55, 0.55, 0.58) if frame == "int_plastic" else None)
            if sill_ledge and kind == "window" and oz0 > z0 + 0.3:
                # the deep interior sill of the ribbon windows (#76 #99 #104): a white ledge 0.22 m into the room
                ia, ib = (a[0] + dx * s0 - nox * 0.22, a[1] + dy * s0 - noy * 0.22), \
                    (a[0] + dx * s1 - nox * 0.22, a[1] + dy * s1 - noy * 0.22)
                V.poly([(*at(s0), oz0), (*at(s1), oz0), (*ib, oz0), (*ia, oz0)], "int_ms_wall", ao=1.0,
                       normal_hint=(0, 0, 1), tint=(0.96, 0.96, 0.96))
                V.wall(ia, ib, oz0 - 0.05, oz0, "int_ms_wall", ao=0.9, tint=(0.9, 0.9, 0.9))
            if kind == "locked":
                for sx in (s0 + 0.08, s1 - 0.08, s0 + span / 2):
                    p = mid(sx)
                    V.box(p[0] - 0.05, p[1] - 0.05, oz0, p[0] + 0.05, p[1] + 0.05, oz1, frame, faces="+x-x+y-y")
                for sx in (s0 + span * 0.44, s0 + span * 0.56):
                    p = mid(sx)
                    V.box(p[0] - 0.12, p[1] - 0.12, oz0 + 1.0, p[0] + 0.12, p[1] + 0.12, oz0 + 1.06, frame,
                          faces="+x-x+y-y+z-z")
    if col_in or col_out:
        trans = []
        if col_out_fn is not None:
            ss = [k * 0.125 for k in range(int(L / 0.125) + 1)]
            trans = [(p + q) / 2 for p, q in zip(ss, ss[1:]) if col_out_fn(p) != col_out_fn(q)]
        cu = split_line(0.0, L, col_step, [v for o in holes for v in (o["s0"], o["s1"])] + trans)
        cz = split_line(z0, z1, 0.0, [v for o in holes for v in (o["z0"], o["z1"])])
        for i in range(len(cu) - 1):
            for j in range(len(cz) - 1):
                s0, s1, za, zb = cu[i], cu[i + 1], cz[j], cz[j + 1]
                sm, zm = (s0 + s1) / 2, (za + zb) / 2
                if any(o["s0"] < sm < o["s1"] and o["z0"] < zm < o["z1"] for o in holes):
                    continue
                if col_in:
                    C.wall(at(s1), at(s0), za, zb, cm)
                if col_out and (col_out_fn is None or col_out_fn(sm)):
                    C.wall(out(s0), out(s1), za, zb, cm)
        for o in holes:
            C.wall(out(o["s0"]), at(o["s0"]), o["z0"], o["z1"], cm)
            C.wall(at(o["s1"]), out(o["s1"]), o["z0"], o["z1"], cm)
            if o["z1"] < z1 - 1e-3:
                C.poly([(*at(o["s0"]), o["z1"]), (*at(o["s1"]), o["z1"]), (*out(o["s1"]), o["z1"]),
                        (*out(o["s0"]), o["z1"])], cm, normal_hint=(0, 0, -1))


def col_seg_box(C, p, q, th, z0, z1, mat, bottom=False, top=True):
    """Closed collision block around segment p-q (half thickness th), z0..z1."""
    L = math.dist(p, q)
    if L < 1e-4:
        return
    dx, dy = (q[0] - p[0]) / L, (q[1] - p[1]) / L
    nx, ny = -dy, dx
    foot = ccw([(p[0] + nx * th, p[1] + ny * th), (q[0] + nx * th, q[1] + ny * th),
                (q[0] - nx * th, q[1] - ny * th), (p[0] - nx * th, p[1] - ny * th)])
    C.prism(foot, z0, z1, mat, top=mat if top else None, bottom=mat if bottom else None)


def thin_partition(V, C, a, b, z0, z1, kind="glass", doors=(), post_every=2.6, frame="int_metal",
                   solid_mat="int_drywall", tint=None, transom=DOOR_H):
    """Interior partition along a-b from z0 to z1 (the ceiling). kind "glass": a translucent pane in a
    metal frame ('COL nocam' slab, the camera passes); "solid": a drywall wall PART_T thick ('COL default').
    doors: [(s0, s1, head_z)] gaps (collision gap too)."""
    L = math.dist(a, b)
    if L < 0.05:
        return
    dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    nx, ny = -dy, dx
    th = (GLASS_T if kind == "glass" else PART_T) / 2.0

    def at(s, side=0.0):
        return (a[0] + dx * s + nx * side, a[1] + dy * s + ny * side)
    gaps = [(max(0.0, d0), min(L, d1), h) for d0, d1, h in doors if min(L, d1) - max(0.0, d0) > 0.05]
    spans = intervals_subtract([(0.0, L)], [(g0, g1) for g0, g1, _ in gaps])
    if kind == "staff_open":
        # the service desk's open back (#23): the staff room shows over the counter under a copper-veneer bulkhead;
        # the collision stays a full-height wall (the staff room is closed)
        zb = 2.75
        for s0, s1 in spans:
            V.wall(at(s1, th), at(s0, th), zb, z1, "int_ms_veneer", ao=0.95)
            V.wall(at(s0, -th), at(s1, -th), zb, z1, "int_ms_veneer", ao=0.95)
            V.poly([(*at(s0, th), zb), (*at(s1, th), zb), (*at(s1, -th), zb), (*at(s0, -th), zb)], "int_ms_wall",
                   normal_hint=(0, 0, -1), tint=(0.9, 0.9, 0.9))
            col_seg_box(C, at(s0), at(s1), max(th, THIN_COL_T / 2.0), z0, z1, K.COL, top=False)
        return
    cm = K.COL_NOCAM if kind == "glass" else K.COL
    for s0, s1 in spans:
        if kind == "glass":
            V.wall(at(s0), at(s1), z0 + 0.10, z1, "int_glass", ao=1.0)
            V.wall(at(s1, th), at(s0, th), z0, z0 + 0.10, frame)
            V.wall(at(s0, -th), at(s1, -th), z0, z0 + 0.10, frame)
            V.poly([(*at(s0, th), z0 + 0.1), (*at(s0, -th), z0 + 0.1), (*at(s1, -th), z0 + 0.1),
                    (*at(s1, th), z0 + 0.1)], frame, normal_hint=(0, 0, 1))
            n = max(1, int(math.ceil((s1 - s0) / post_every)))
            for k in range(n + 1):
                p = at(s0 + (s1 - s0) * k / n)
                V.box(p[0] - 0.035, p[1] - 0.035, z0, p[0] + 0.035, p[1] + 0.035, z1, frame, faces="+x-x+y-y")
            if transom < z1 - 0.2:
                V.wall(at(s1, th), at(s0, th), transom - 0.05, transom + 0.05, frame)
                V.wall(at(s0, -th), at(s1, -th), transom - 0.05, transom + 0.05, frame)
        else:
            zz = split_line(z0, z1, 3.0, [z0 + 0.1])
            uu = split_line(s0, s1, 3.0)
            for i in range(len(uu) - 1):
                for j in range(len(zz) - 1):
                    u0, u1, za, zb = uu[i], uu[i + 1], zz[j], zz[j + 1]
                    m = "int_plastic" if zb <= z0 + 0.1001 else solid_mat
                    ao = [wall_ao(za, z0), wall_ao(za, z0), wall_ao(zb, z0), wall_ao(zb, z0)]
                    V.wall(at(u1, th), at(u0, th), za, zb, m, ao=ao, tint=tint if m == solid_mat else None)
                    V.wall(at(u0, -th), at(u1, -th), za, zb, m, ao=ao, tint=tint if m == solid_mat else None)
            for s, sgn in ((s0, -1), (s1, 1)):                                  # end faces (door jambs)
                if 0.01 < s < L - 0.01:
                    p, q = at(s, -th * sgn), at(s, th * sgn)
                    V.wall(p, q, z0, z1, solid_mat, ao=0.85, tint=tint)
        col_seg_box(C, at(s0), at(s1), max(th, THIN_COL_T / 2.0), z0, z1, cm, top=False)
    for g0, g1, head in gaps:
        if head < z1 - 0.05:
            if kind == "glass":
                V.wall(at(g0), at(g1), head, z1, "int_glass", ao=1.0)
                V.wall(at(g1, th), at(g0, th), head - 0.06, head, frame)
                V.wall(at(g0, -th), at(g1, -th), head - 0.06, head, frame)
                V.poly([(*at(g0, th), head - 0.06), (*at(g1, th), head - 0.06), (*at(g1, -th), head - 0.06),
                        (*at(g0, -th), head - 0.06)], frame, normal_hint=(0, 0, -1))
            else:
                V.wall(at(g1, th), at(g0, th), head, z1, solid_mat, ao=0.9, tint=tint)
                V.wall(at(g0, -th), at(g1, -th), head, z1, solid_mat, ao=0.9, tint=tint)
                V.poly([(*at(g0, th), head), (*at(g1, th), head), (*at(g1, -th), head), (*at(g0, -th), head)],
                       "int_wood_dark", normal_hint=(0, 0, -1))
            col_seg_box(C, at(g0), at(g1), max(th, THIN_COL_T / 2.0), head, z1, cm, bottom=True, top=False)
        for s in (g0, g1):
            p = at(s)
            V.box(p[0] - 0.06, p[1] - 0.06, z0, p[0] + 0.06, p[1] + 0.06, head,
                  frame if kind == "glass" else "int_wood_dark", faces="+x-x+y-y")


def slab(V, C, cover, holes, top_fn, top_col, bot_fn, bot_col, edge_holes=(), lines=((), ()), vis=3.0,
         col=10.24, thickness=SLAB, edge_mat="int_drywall"):
    """Floor slab at local z 0 (top) / -thickness (bottom) over the union of `cover` polygons minus `holes`
    (rects). top_fn / bot_fn(x, y) -> (material, tint) or None; top_col / bot_col(x, y) -> bool.
    edge_holes: holes whose sides get a fascia (visual + collision)."""
    allp = [p for poly in cover for p in poly]
    bx = bbox(allp)
    ex = [p[0] for p in allp] + [h[i] for h in holes for i in (0, 2)] + list(lines[0])
    ey = [p[1] for p in allp] + [h[i] for h in holes for i in (1, 3)] + list(lines[1])
    xs, ys = split_line(bx[0], bx[2], vis, ex), split_line(bx[1], bx[3], vis, ey)
    xc, yc = split_line(bx[0], bx[2], col, ex), split_line(bx[1], bx[3], col, ey)
    if top_fn is not None:
        rects, parts = Cells.build(cover, holes, xs, ys, top_fn).merge(vis, vis)
        for x0, y0, x1, y1, (m, tint) in rects:
            V.poly([(x0, y0, 0.0), (x1, y0, 0.0), (x1, y1, 0.0), (x0, y1, 0.0)], m, ao=1.0, tint=tint)
        for poly, (m, tint) in parts:
            V.poly([(x, y, 0.0) for x, y in poly], m, ao=1.0, tint=tint)
    if bot_fn is not None:
        rects, parts = Cells.build(cover, holes, xs, ys, bot_fn).merge(vis, vis)
        for x0, y0, x1, y1, (m, tint) in rects:
            V.poly([(x0, y0, -thickness), (x0, y1, -thickness), (x1, y1, -thickness), (x1, y0, -thickness)], m,
                   ao=0.92, tint=tint)
        for poly, (m, tint) in parts:
            V.poly([(x, y, -thickness) for x, y in reversed(poly)], m, ao=0.92, tint=tint)
    if top_col is not None:
        rects, parts = Cells.build(cover, holes, xc, yc, lambda x, y: True if top_col(x, y) else None).merge(col, col)
        for x0, y0, x1, y1, _ in rects:
            C.poly([(x0, y0, 0.0), (x1, y0, 0.0), (x1, y1, 0.0), (x0, y1, 0.0)], K.COL)
        for poly, _ in parts:
            C.poly([(x, y, 0.0) for x, y in poly], K.COL)
    if bot_col is not None:
        rects, parts = Cells.build(cover, holes, xc, yc, lambda x, y: True if bot_col(x, y) else None).merge(col, col)
        for x0, y0, x1, y1, _ in rects:
            C.poly([(x0, y0, -thickness), (x0, y1, -thickness), (x1, y1, -thickness), (x1, y0, -thickness)], K.COL)
        for poly, _ in parts:
            C.poly([(x, y, -thickness) for x, y in reversed(poly)], K.COL)

    def solid(x, y):
        return any(pip((x, y), poly) for poly in cover) and not any(in_rect((x, y), h) for h in holes)
    for h in edge_holes:
        x0, y0, x1, y1 = h
        sides = [((x1, y0), (x0, y0), (0.0, -0.05)), ((x0, y1), (x1, y1), (0.0, 0.05)),
                 ((x0, y0), (x0, y1), (-0.05, 0.0)), ((x1, y1), (x1, y0), (0.05, 0.0))]
        for a, b, (ox, oy) in sides:
            L = math.dist(a, b)
            cuts = split_line(0.0, L, 3.0)
            for s0, s1 in zip(cuts, cuts[1:]):
                pa = (a[0] + (b[0] - a[0]) * s0 / L, a[1] + (b[1] - a[1]) * s0 / L)
                pb = (a[0] + (b[0] - a[0]) * s1 / L, a[1] + (b[1] - a[1]) * s1 / L)
                mx, my = (pa[0] + pb[0]) / 2 + ox, (pa[1] + pb[1]) / 2 + oy
                if not solid(mx, my):
                    continue
                # wall(p, q) faces right of p->q: the sides above run so that the face looks INTO THE HOLE
                # (fix round: this was wall(pb, pa), facing into the slab. An airborne Mario is pushed to a
                # wall's front side within 50 units, so a player dropping through the chute hatch was popped
                # back out onto F2, and the drywall strip was back-face culled from the hole / atrium side)
                V.wall(pa, pb, -thickness, 0.0, edge_mat, ao=0.9)
                C.wall(pa, pb, -thickness, 0.0, K.COL)


def box_prop(kind, x0, y0, z0, x1, y1, z1, mat, top=None, col=True, cam=False, faces=None, tint=None, glow=False):
    P = K.Prop(kind, col_closed=True)
    P.visual.box(x0, y0, z0, x1, y1, z1, mat, faces=faces, mats={"+z": top} if top else None, tint=tint, glow=glow)
    if col:
        K.col_box(P.collision, x0, y0, z0, x1, y1, z1, K.COL if cam else K.COL_NOCAM, bottom=z0 > 1e-6)
    return P


def single_box_collision(P, boxes, cam=False):
    """Replace a prop's collision with simple blocks (budget: carrels, computer rows, desks)."""
    P.collision = K.KitMesh(auto_ao=False)
    for (x0, y0, z0, x1, y1, z1) in boxes:
        K.col_box(P.collision, x0, y0, z0, x1, y1, z1, K.COL if cam else K.COL_NOCAM, bottom=z0 > 1e-6)
    return P


def ms_column(fid, h=CLEAR, size=COLUMN_W):
    """A module column as photographed: square, white / cream paint, a black base, and a cap band at the ceiling
    (copper veneer on F2 #24 #30, terracotta paint on F3-F5 #76 #100; none in the 2014 basement #36). Collision as
    the kit column (the full square prism, 'COL default')."""
    P = K.Prop("column", size=size, height=h)
    r = size / 2.0
    pts = [(-r, -r), (r, -r), (r, r), (-r, r)]
    V = P.visual
    V.prism(pts, 0.0, 0.10, "int_plastic")
    cap = COLUMN_CAP.get(fid)
    top = h - (COLUMN_CAP_H if cap else 0.0)
    V.prism([(x * 0.995, y * 0.995) for x, y in pts], 0.10, top, "int_ms_wall", tint=(1.0, 1.0, 0.99))
    if cap:
        mat, tint = cap
        V.prism([(x * 1.03, y * 1.03) for x, y in pts], top, h, mat, tint=tint, ao=1.0)
    K.col_prism(P.collision, pts, 0.0, h, K.COL)
    return P


def staff_counter_edge(M, fid, a, b):
    """Is the partition piece a-b the back of the F2 service desk (the edge of the staff region along the counter)?"""
    if fid != "F2":
        return False
    desk = next((pr for pr in floor_of(M.layout, "F2")["props"] if pr["id"] == "desk_counter"), None)
    if desk is None:
        return False
    poly = [tuple(q) for q in desk["poly_m"]]
    m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    if min(seg_point_dist(m, p, q) for p, q in edges(poly)) > 1.0:
        return False
    return staff_view(M, fid, m[0] + 0.3 * (b[1] - a[1]) / max(1e-6, math.dist(a, b)),
                      m[1] - 0.3 * (b[0] - a[0]) / max(1e-6, math.dist(a, b))) or \
        staff_view(M, fid, m[0] - 0.3 * (b[1] - a[1]) / max(1e-6, math.dist(a, b)),
                   m[1] + 0.3 * (b[0] - a[0]) / max(1e-6, math.dist(a, b)))


def staff_view(M, fid, x, y):
    """The staff area behind the F2 service desk, seen through the open counter (#23): floor + ceiling drawn."""
    if fid != "F2":
        return False
    r = M.region_at(fid, x, y)
    return r is not None and r["id"] == "service_desk"


def ext_wall_tint(M, fid, a, b, has_win):
    """Interior paint of an exterior wall run: the F2 golden-yellow window wall east of the atrium (#24 #25 #29), the
    grey window walls of F3-F5 (#76; dark grey after the 2022 refit on F4-F5, #97 #100), the olive end walls of the
    F1 computer labs (#61 #63), white elsewhere."""
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    if fid == "F2" and abs(a[0] - b[0]) < 0.05 and a[0] > -34.0 and -106.0 < my < -96.0:
        return MP.T_YELLOW_WALL
    if fid == "F2" and abs(a[1] - b[1]) < 0.05 and my < -124.5 and -46.0 < mx < -33.0:
        return MP.T_YELLOW_WALL
    if fid == "F1":
        if abs(a[1] - b[1]) < 0.05 and my > -53.0:
            return MP.T_OLIVE_WALL                         # North Lab end wall
        if abs(a[1] - b[1]) < 0.05 and abs(my + 115.9) < 0.1 and mx < -71.0:
            return MP.T_OLIVE_WALL                         # South Lab end wall
        if abs(a[1] - b[1]) < 0.05 and my < -124.5 and -71.3 < mx < -60.7:
            return T_BEIGE_WALL                            # L136 (#47)
        return None
    if has_win:
        return WINDOW_WALL_TINT.get(fid)
    return None


def partition_tint(M, fid, a, b):
    """Accent paint of solid interior partitions: F2 teal-blue round the staff offices east of the lounge (#24 #27
    #28), F1 purple at the NE restrooms (#36) and golden yellow on the commons face of the north staff room (#37)."""
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    for side in (0.3, -0.3):
        if abs(a[1] - b[1]) < 0.05:
            px, py = mx, my + side
        else:
            px, py = mx + side, my
        r = M.region_at(fid, px, py)
        if r is None:
            continue
        if fid == "F2" and r["id"] == "staff_se":
            return MP.T_TEAL_WALL
        if fid == "F1" and r["id"] in ("wc_f1_mens", "wc_f1"):
            return MP.T_PURPLE_WALL
        if fid == "F1" and r["id"] == "sorting_room" and abs(a[1] - b[1]) < 0.05:
            return MP.T_YELLOW_WALL
        if fid == "F1" and r["id"] == "L136":
            return T_BEIGE_WALL                            # L136's cream walls (#47 #49)
    return None


# ================================================================== the layout
def load_layout(path=LAYOUT_PATH):
    with open(path) as f:
        return json.load(f)


def floor_of(layout, fid):
    return next(f for f in layout["floors"] if f["id"] == fid)


def outline(layout, fid):
    return ccw([tuple(p) for p in floor_of(layout, fid)["outline_m"]])


def long_axis(poly):
    """(centre x, y, length, width, facing): facing 90 = the long axis runs N-S (local +x -> south)."""
    x0, y0, x1, y1 = bbox(poly)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w, h = x1 - x0, y1 - y0
    if h >= w:
        return cx, cy, h, w, 90.0
    return cx, cy, w, h, 0.0


def facing_from(a, b):
    """Compass bearing a -> b (0 = north, 90 = east)."""
    return math.degrees(math.atan2(b[0] - a[0], b[1] - a[1])) % 360.0


def tower_polys(fid):
    out = [("ne_hall", rect_poly(NE_RECT)), ("sw_hall", rect_poly(SW_RECT if fid != "F1" else SW_RECT_F1)),
           ("core", rect_poly(CORE_RECT))]
    return out


class Marston:
    """The built interior: kit, lighting per group, design anchor points, pickups plan, previews, notes."""

    def __init__(self, layout):
        self.layout = layout
        self.kit = K.Kit()
        self.points = {}
        self.pickups = []
        self.views = []
        self.notes = json.loads(json.dumps(NOTES))
        self.doors = {fid: [] for fid in FLOORS}
        self.regions = {}
        self.outlines = {fid: outline(layout, fid) for fid in FLOORS}
        self.daylight = []
        self.stack_tops = []
        self.props = {fid: [] for fid in FLOORS}      # footprints [(poly, kind, id, height)]
        self.anchors = {}
        self.tags = set()
        self.lighting = {}
        self.stats = {}
        self.coffers = {}                             # {fid: {(i, j): cell}}: the 1987 ceiling coffers over each floor
        self.dressing = []                            # free-standing furniture queued by dress() (place_dressing)

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
        return pip((x, y), self.outlines[fid])

    def region_at(self, fid, x, y):
        for r in self.regions[fid]:
            if pip((x, y), r["poly"]):
                return r
        return None

    def in_tower(self, fid, x, y, m=0.0):
        return any(in_rect((x, y), bbox(p), m) for _, p in tower_polys(fid))

    def zone_at(self, fid, x, y):
        for z in floor_of(self.layout, fid)["zones"]:
            if pip((x, y), [tuple(p) for p in z["poly_m"]]):
                return z
        return None

    def solid_at(self, fid, x, y):
        r = self.region_at(fid, x, y)
        return r is not None and r["kind"] == "solid"


# ================================================================== regions + doors
def regions_of(M, fid):
    """Enclosed regions of a floor: [{id, poly, kind (glass|wall|solid), walkable, type}]. Zone coordinates
    are snapped to the outline / towers (0.45 m) and to each other (0.25 m) so partitions meet cleanly."""
    f = floor_of(M.layout, fid)
    ol = M.outlines[fid]
    refx = sorted({p[0] for p in ol} | {v for _, p in tower_polys(fid) for v in (bbox(p)[0], bbox(p)[2])})
    refy = sorted({p[1] for p in ol} | {v for _, p in tower_polys(fid) for v in (bbox(p)[1], bbox(p)[3])})

    def snap(v, refs, tol):
        best = None
        for r in refs:
            if abs(v - r) <= tol and (best is None or abs(v - r) < abs(v - best)):
                best = r
        return v if best is None else best
    out = []
    for z in f["zones"]:
        enc, typ, walk = z.get("enclosure", "open"), z["type"], z.get("walkable", True)
        if typ in ("porch", "porch_void", "terrace", "atrium_void", "roof_deck") or z["id"] == "service_desk":
            continue
        if enc in ("open", "railing", "parapet", "glass_partial"):
            continue
        poly = [(snap(x, refx, 0.45), snap(y, refy, 0.45)) for x, y in z["poly_m"]]
        kind = "glass" if enc.startswith("glass") else ("wall" if walk else "solid")
        if z["id"] in SOLID_ROOMS:
            kind = "wall"
        out.append({"id": z["id"], "poly": ccw(poly), "type": typ, "walkable": walk, "name": z.get("name", z["id"]),
                    "kind": kind})
    vals_x = sorted({p[0] for r in out for p in r["poly"]})
    vals_y = sorted({p[1] for r in out for p in r["poly"]})

    def cluster(vals, refs):
        rep = {}
        for v in vals:
            s = snap(v, refs, 0.25)
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


def _free_point(M, fid, x, y, own=None):
    if not M.inside(fid, x, y) or M.in_tower(fid, x, y, 0.1):
        return False
    if fid != "F2" and fid != "F1" and in_rect((x, y), ATRIUM, 0.3):
        return False
    r = M.region_at(fid, x, y)
    if r is not None and r is not own:
        return False
    for poly, kind, pid, h in M.props[fid]:
        if pip((x, y), poly):
            return False
    return True


def plan_doors(M):
    """Door gaps of every enclosed walkable region: the layout's interior openings, a few gameplay doors and
    an automatic door on the room side with the longest free run (outside point on the open floor)."""
    L = M.layout
    explicit = {"F2": [("vestibule", ((-69.2, -78.8), (-65.2, -78.8)), 3.0),
                       ("starbucks", ((-73.9, -104.6), (-73.9, -107.0)), DOOR_H),
                       ("sbux_entry", SBUX_LOBBY_DOOR, DOOR_H)],
                "F1": [("sorting_room", SORTING_DOOR, DOOR_H),
                       # the Act 3 star room: its only free side is 1.8 m between L128 and L130
                       ("L129", ((-37.5, -120.5), (-37.5, -118.9)), DOOR_H)]}
    for fid in FLOORS:
        cent = (CENTER[0], CENTER[1])
        for r in M.regions[fid]:
            if r["kind"] == "solid":
                continue
            given = [e for e in explicit.get(fid, []) if e[0] == r["id"]]
            if r["id"] == "sbux_entry":
                pass
            elif given:
                for _, (a, b), h in given:
                    M.doors[fid].append(_door_rec(fid, r, *snap_door_to_edge(r, a, b), h))
                continue
            if r["type"] == "cafe" and r["id"] == "starbucks":
                continue
            for _, (a, b), h in given:
                M.doors[fid].append(_door_rec(fid, r, *snap_door_to_edge(r, a, b), h))
            if given:
                continue
            want = STUDY_DOOR_W if r["type"] == "group_study" else ROOM_DOOR_W
            best = None
            for p, q in edges(r["poly"]):
                Ls = math.dist(p, q)
                if Ls < 1.4:
                    continue
                dx, dy = (q[0] - p[0]) / Ls, (q[1] - p[1]) / Ls
                ox, oy = dy, -dx                                  # outward (right of a CCW edge)
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
            M.doors[fid].append(_door_rec(fid, r, best[1], best[2], DOOR_H))


def snap_door_to_edge(r, a, b):
    """Move an explicit door segment onto the nearest parallel edge of its (snapped) room polygon."""
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    horiz = abs(a[1] - b[1]) < 1e-6
    best = None
    for p, q in edges(r["poly"]):
        if horiz != (abs(p[1] - q[1]) < 1e-6):
            continue
        d = abs(p[1] - my) if horiz else abs(p[0] - mx)
        lo, hi = (sorted((p[0], q[0])) if horiz else sorted((p[1], q[1])))
        along = mx if horiz else my
        if not (lo - 0.5 <= along <= hi + 0.5):
            continue
        if best is None or d < best[0]:
            best = (d, p[1] if horiz else p[0])
    if best is None or best[0] > 0.6:
        return a, b
    v = best[1]
    return ((a[0], v), (b[0], v)) if horiz else ((v, a[1]), (v, b[1]))


def _door_rec(fid, r, a, b, head):
    a, b = (round(a[0], 3), round(a[1], 3)), (round(b[0], 3), round(b[1], 3))
    c = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    # outward = away from the room: test a point 0.5 m to each side
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L, dx / L
    side = (c[0] + nx * 0.5, c[1] + ny * 0.5)
    if pip(side, r["poly"]):
        nx, ny = -nx, -ny
    return {"floor": fid, "room": r["id"], "room_name": r["name"], "type": r["type"], "a": a, "b": b, "centre": c,
            "width": round(L, 2), "head": head, "facing": round(math.degrees(math.atan2(nx, ny)) % 360.0, 1)}


# ================================================================== partitions
def build_partitions(M, fid, P):
    """Interior walls between enclosed regions and the open floor (glass or drywall), with the door gaps.
    Pieces on the floor outline (exterior walls) and on a tower (stair halls, core) are left to those."""
    regions = M.regions[fid]
    ol = M.outlines[fid]
    buckets = {}
    diag = []
    for r in regions:
        for p, q in edges(r["poly"]):
            if abs(p[1] - q[1]) < 1e-3:
                buckets.setdefault(("h", round(p[1], 3)), []).append((min(p[0], q[0]), max(p[0], q[0])))
            elif abs(p[0] - q[0]) < 1e-3:
                buckets.setdefault(("v", round(p[0], 3)), []).append((min(p[1], q[1]), max(p[1], q[1])))
            else:
                diag.append((p, q))
    blockers = list(edges(ol)) + [e for _, poly in tower_polys(fid) for e in edges(poly)]
    n_glass = n_solid = 0
    for (ax, v), ivs in buckets.items():
        ivs = intervals_union(ivs)
        cut = []
        for p, q in blockers:
            if ax == "h" and abs(p[1] - q[1]) < 1e-3 and abs(p[1] - v) < 0.08:
                cut.append((min(p[0], q[0]), max(p[0], q[0])))
            if ax == "v" and abs(p[0] - q[0]) < 1e-3 and abs(p[0] - v) < 0.08:
                cut.append((min(p[1], q[1]), max(p[1], q[1])))
        ivs = intervals_subtract(ivs, cut)
        if fid == "F1" and ax == "h" and abs(v - DUCT["y"][0]) < 0.05:          # under / around the vent duct
            ivs = intervals_subtract(ivs, [(DUCT["x"][0] - 0.1, DUCT["x"][1] + 0.05)])
        for s0, s1 in ivs:
            # split the piece where the regions on either side change
            cuts = split_line(s0, s1, 0.25)
            pieces = []
            for u0, u1 in zip(cuts, cuts[1:]):
                um = (u0 + u1) / 2
                pa, pb = ((um, v + 0.15), (um, v - 0.15)) if ax == "h" else ((v + 0.15, um), (v - 0.15, um))
                ra, rb = M.region_at(fid, *pa), M.region_at(fid, *pb)
                if ra is rb or (ra is None and rb is None):
                    k = None
                elif ra is not None and rb is not None and ra["type"] == rb["type"] == "cafe":
                    k = None
                elif ra is not None and rb is not None:
                    k = "solid"         # photo pass 2: rooms share white drywall; only the open-floor side is glass (#38)
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
                kk = k
                if k == "solid" and staff_counter_edge(M, fid, a, b):
                    kk = "staff_open"
                thin_partition(P.visual, P.collision, (a[0], a[1]), (b[0], b[1]), 0.0, CLEAR, kk, doors,
                               solid_mat="int_ms_wall", tint=partition_tint(M, fid, a, b) if k == "solid" else None,
                               frame="int_plastic" if fid == "F2" else "int_metal")
                if k == "glass":
                    n_glass += 1
                else:
                    n_solid += 1
    for p, q in diag:
        thin_partition(P.visual, P.collision, p, q, 0.0, CLEAR,
                       "staff_open" if staff_counter_edge(M, fid, p, q) else "solid")
    M.stats.setdefault("partitions", {})[fid] = {"glass": n_glass, "solid": n_solid}


# ================================================================== props
def range_prop(L, W, h, seed, steps=True):
    """A stack range L long (local x), W deep, h tall with a climbing end at local -x: a 1.07 m end cap
    (and a 2.29 m step section on ranges over 2.6 m). -> (prop, [(x0, x1, top_z)] walkable tops)."""
    P = K.Prop("range", col_closed=True)
    cap = 0.9
    tops = []
    if not steps or L < 3.0:
        P.merge(K.bookshelf(L, h, W, seed=seed))
        tops.append((-L / 2, L / 2, h))
        return P, tops
    if h > 2.6:
        main_l = L - 2 * cap
        P.merge(K.bookshelf(main_l, h, W, seed=seed), cap, 0.0, 0.0)
        P.merge(K.bookshelf(cap, K.REAL["stack_full_h"], W, end_caps=("-x",), step_len=cap, seed=seed + 1),
                -L / 2 + 1.5 * cap, 0.0, 0.0)
        tops += [(-L / 2 + 2 * cap, L / 2, h), (-L / 2 + cap, -L / 2 + 2 * cap, K.REAL["stack_full_h"]),
                 (-L / 2, -L / 2 + cap, K.REAL["stack_counter_h"])]
    else:
        P.merge(K.bookshelf(L - cap, h, W, end_caps=("-x",), step_len=cap, seed=seed), cap / 2, 0.0, 0.0)
        tops += [(-L / 2 + cap, L / 2, h), (-L / 2, -L / 2 + cap, K.REAL["stack_counter_h"])]
    return P, tops


def lp_chair(fabric="int_fabric_blue", frame="int_metal"):
    """Low-poly chair (22 tris, visual only): seat block, back, a front skirt. The sitter faces +y."""
    P = K.Prop("chair", col_closed=True)
    V = P.visual
    V.box(-0.23, -0.24, 0.38, 0.23, 0.24, 0.46, fabric, faces="+x-x+y-y+z")
    V.box(-0.23, -0.25, 0.46, 0.23, -0.20, 0.88, fabric, faces="+x-x+y-y+z")
    V.box(-0.21, -0.20, 0.0, 0.21, 0.20, 0.38, frame, faces="+x-x", tint=(0.8, 0.8, 0.82))
    return P


def lp_table(length=1.83, width=0.91, chairs_per_side=2, seat="int_fabric_blue", h=K.REAL["table_h"], col=True):
    """Low-poly study table (top + two pedestal ends) with low-poly chairs; collision: one block."""
    P = K.Prop("table", col_closed=True)
    V = P.visual
    hl, hw = length / 2, width / 2
    V.box(-hl, -hw, h - 0.04, hl, hw, h, "int_wood", faces=K.BOX_ALL)
    for sx in (-1, 1):
        x = sx * (hl - 0.12)
        V.box(x - 0.03, -hw + 0.1, 0.0, x + 0.03, hw - 0.1, h - 0.04, "int_metal", faces="+x-x+y-y")
    for i in range(chairs_per_side):
        x = -hl + (i + 0.5) * length / chairs_per_side
        for sgn, f in ((1, 180.0), (-1, 0.0)):
            P.merge(lp_chair(seat), x, sgn * (hw + 0.24), 0.0, f)
    if col:
        K.col_box(P.collision, -hl, -hw, 0.0, hl, hw, h, K.COL_NOCAM)
    P.anchor("top", 0.0, 0.0, h)
    return P


def lp_carrels(n, w=0.95, depth=0.76, panel="int_fabric_blue", h=K.REAL["table_h"], ph=K.REAL["carrel_panel_h"]):
    """A row of n study carrels (low poly): shared desk, back panel, dividers, a book strip, chairs on +y.
    Collision: the desk block + the back panel."""
    P = K.Prop("carrels", col_closed=True)
    V = P.visual
    L = n * w
    hl, hd = L / 2, depth / 2
    V.box(-hl, -hd, h - 0.03, hl, hd, h, "int_wood", faces="+x-x+y-y+z")
    V.box(-hl, -hd, 0.0, hl, -hd + 0.05, ph, panel, faces="+x-x+y-y+z", mats={"+z": "int_metal"})
    for i in range(n + 1):
        x = -hl + i * w
        V.box(x - 0.02, -hd + 0.05, h, x + 0.02, hd - 0.1, ph, panel, faces="+x-x+z")
        V.box(x - 0.02, -hd + 0.05, 0.0, x + 0.02, hd, h - 0.03, panel, faces="+x-x")
    V.poly(K.front_quad(-hl + 0.03, hl - 0.03, -hd + 0.051, ph - 0.36, ph - 0.06), "int_books",
           uvs=K.uv_rect(0.0, 0.0, (L - 0.06) / 2.0, 0.375))
    for i in range(n):
        P.merge(lp_chair("int_fabric_blue" if i % 2 else "int_fabric_orange"), -hl + (i + 0.5) * w, hd + 0.25, 0.0,
                180.0)
    K.col_box(P.collision, -hl, -hd, 0.0, hl, hd, h, K.COL_NOCAM)
    K.col_box(P.collision, -hl, -hd, h, hl, -hd + 0.05, ph, K.COL_NOCAM, bottom=True)
    return P


def lp_carrels_double(n, w, width, panel="int_fabric_blue", h=K.REAL["table_h"], top_h=1.30, hutch=0.6):
    """Back-to-back carrels across a `width` deep row (the layout's 1.4-1.6 m rows): desks on both sides of a
    central hutch `hutch` wide and `top_h` tall (books on both faces, a walkable top: the act 2 'carrel top'),
    dividers, chairs. Collision: the two desk blocks + the hutch block."""
    P = K.Prop("carrels2", col_closed=True)
    V = P.visual
    L = n * w
    hl, hw, hh = L / 2, width / 2, hutch / 2
    V.box(-hl, -hh, 0.0, hl, hh, top_h, panel, faces="+x-x+z", mats={"+z": "int_wood"})
    for sgn in (1, -1):
        y0, y1 = (hh, hw) if sgn > 0 else (-hw, -hh)
        V.box(-hl, y0, h - 0.03, hl, y1, h, "int_wood", faces="+x-x+y-y+z" if sgn > 0 else "+x-x+y-y+z")
        quad = K.front_quad if sgn > 0 else K.back_quad
        yb = sgn * hh
        V.poly(quad(-hl + 0.03, hl - 0.03, yb, h + 0.05, top_h - 0.05), "int_books",
               uvs=K.uv_rect(0.0, 0.0, (L - 0.06) / 2.0, 0.5))
        for i in range(n + 1):
            x = -hl + i * w
            V.box(x - 0.02, min(y0, y1), 0.0, x + 0.02, max(y0, y1), top_h if i in (0, n) else h + 0.45, panel,
                  faces="+x-x+z+y-y")
        for i in range(n):
            P.merge(lp_chair("int_fabric_blue" if (i + (sgn > 0)) % 2 else "int_fabric_orange"),
                    -hl + (i + 0.5) * w, sgn * (hw + 0.25), 0.0, 180.0 if sgn > 0 else 0.0)
        K.col_box(P.collision, -hl, min(y0, y1), 0.0, hl, max(y0, y1), h, K.COL_NOCAM)
    K.col_box(P.collision, -hl, -hh, 0.0, hl, hh, top_h, K.COL_NOCAM)
    P.anchor("hutch_top", 0.0, 0.0, top_h)
    return P


def lp_computers(n, seat_w=0.9, depth=0.8, double=False, h=K.REAL["table_h"]):
    """Computer workstations (low poly): desk, monitors (kit), keyboards, chairs; collision: the desk."""
    P = K.Prop("computers", col_closed=True)
    V = P.visual
    L = n * seat_w
    hl = L / 2
    y0, y1 = (-depth, depth) if double else (-depth / 2, depth / 2)
    V.box(-hl, y0, h - 0.04, hl, y1, h, "int_wood", faces=K.BOX_ALL)
    V.box(-hl, y0 + 0.03, 0.05, hl, y1 - 0.03, h - 0.04, "int_plastic", faces="+x-x+y-y", tint=(0.9, 0.9, 0.9))
    for sgn in ((1, -1) if double else (1,)):
        for i in range(n):
            cx = -hl + (i + 0.5) * seat_w
            yb = sgn * (0.12 if double else -depth / 2 + 0.2)
            P.merge(K.monitor(), cx, yb, h, 0.0 if sgn > 0 else 180.0)
            ys = sgn * ((depth if double else depth / 2) + 0.26)
            P.merge(lp_chair("int_fabric_blue" if i % 2 else "int_fabric_orange"), cx, ys, 0.0, 180.0 if sgn > 0 else 0.0)
    K.col_box(P.collision, -hl, y0, 0.0, hl, y1, h, K.COL_NOCAM)
    return P


def table_cluster(L, W, seat="int_fabric_blue"):
    P = K.Prop("table_cluster", col_closed=True)
    n = max(1, int(L // 2.1))
    rows = 2 if W >= 3.4 else 1
    for i in range(n):
        x = -L / 2 + (i + 0.5) * L / n
        for r in range(rows):
            y = 0.0 if rows == 1 else (-W / 4 if r == 0 else W / 4)
            P.merge(lp_table(min(1.83, L / n - 0.2), 0.91, chairs_per_side=2, seat=seat), x, y, 0.0, 0.0)
    return P


def desk_row(L, D, h=0.76, chairs=True, seat="int_fabric_blue", monitors=False):
    """A long counter desk (window desks): wood top on panels, chairs on the +y side."""
    P = K.Prop("desk_row", col_closed=True)
    V = P.visual
    V.box(-L / 2, -D / 2, h - 0.04, L / 2, D / 2, h, "int_wood", faces=K.BOX_ALL)
    V.box(-L / 2, -D / 2, 0.0, L / 2, -D / 2 + 0.04, h - 0.04, "int_wood_dark", faces="+y-y")
    n = max(1, int(L // 1.2))
    for i in range(n + 1):
        x = -L / 2 + i * L / n
        V.box(x - 0.02, -D / 2, 0.0, x + 0.02, D / 2, h - 0.04, "int_metal", faces="+x-x+y")
    for i in range(n):
        x = -L / 2 + (i + 0.5) * L / n
        if chairs:
            P.merge(lp_chair(seat), x, D / 2 + 0.25, 0.0, 180.0)
        if monitors:
            P.merge(K.monitor(), x, -D / 2 + 0.2, h, 0.0)
    K.col_box(P.collision, -L / 2, -D / 2, 0.0, L / 2, D / 2, h, K.COL_NOCAM)
    return P


def display_case(L, W, h):
    P = K.Prop("display_case", col_closed=True)
    hb = max(0.5, h - 0.4)
    P.visual.box(-L / 2, -W / 2, 0.0, L / 2, W / 2, hb, "int_wood_dark", mats={"+z": "int_wood"})
    P.visual.box(-L / 2 + 0.03, -W / 2 + 0.03, hb, L / 2 - 0.03, W / 2 - 0.03, h - 0.02, "int_glass",
                 faces="+x-x+y-y", ao=1.0)
    P.visual.box(-L / 2, -W / 2, h - 0.02, L / 2, W / 2, h, "int_metal", faces=K.BOX_ALL)
    rng = random.Random(int(L * 100 + W * 10))
    for k in range(3):
        x = -L / 2 + (k + 0.5) * L / 3
        tint = [(0.95, 0.55, 0.25), (0.3, 0.55, 0.9), (0.4, 0.8, 0.45)][rng.randrange(3)]
        P.visual.box(x - 0.12, -0.08, hb, x + 0.12, 0.08, hb + 0.28, "int_plastic", faces="+x-x+y-y+z", tint=tint,
                     glow=False)
    K.col_box(P.collision, -L / 2, -W / 2, 0.0, L / 2, W / 2, h, K.COL_NOCAM)
    return P


def aquarium(L, W, h):
    """The 150-gallon fish tank (F3, across from the elevators): cabinet, glass tank, fish, lid."""
    P = K.Prop("aquarium", col_closed=True)
    V = P.visual
    hb = 0.8
    V.box(-L / 2, -W / 2, 0.0, L / 2, W / 2, hb, "int_wood_dark", faces="+x-x+y-y+z")
    V.box(-L / 2 + 0.03, -W / 2 + 0.03, hb, L / 2 - 0.03, W / 2 - 0.03, hb + 0.06, "int_stone", faces="+z",
          tint=(0.95, 0.85, 0.6))
    V.box(-L / 2, -W / 2, hb, L / 2, W / 2, h - 0.05, "int_glass", faces="+x-x+y-y", ao=1.0, tint=(0.6, 0.85, 1.0))
    V.box(-L / 2 + 0.05, -W / 2 + 0.05, hb + 0.06, L / 2 - 0.05, W / 2 - 0.05, h - 0.12, "int_wall_blue",
          faces="+x-x+y-y", glow=True, tint=(0.35, 0.65, 0.85))
    rng = random.Random(150)
    for k in range(9):
        x = rng.uniform(-L / 2 + 0.2, L / 2 - 0.2)
        z = rng.uniform(hb + 0.15, h - 0.25)
        c = [(1.0, 0.55, 0.15), (0.95, 0.85, 0.2), (0.35, 0.6, 1.0), (1.0, 0.35, 0.3)][k % 4]
        for sy in (W / 2 - 0.07, -W / 2 + 0.07):
            V.box(x - 0.07, sy - 0.005, z - 0.03, x + 0.07, sy + 0.005, z + 0.03, "int_plastic", faces="+y-y",
                  glow=True, tint=c)
    V.box(-L / 2, -W / 2, h - 0.05, L / 2, W / 2, h, "int_plastic", faces=K.BOX_ALL)
    K.col_box(P.collision, -L / 2, -W / 2, 0.0, L / 2, W / 2, h, K.COL_NOCAM)
    P.anchor("lid", 0.0, 0.0, h)
    return P


def printer_3d(L, W, h):
    P = K.Prop("printer_3d", col_closed=True)
    V = P.visual
    V.box(-L / 2, -W / 2, 0.0, L / 2, W / 2, 0.75, "int_wood", faces="+x-x+y-y+z")
    for k in range(2):
        x = -L / 2 + (k + 0.5) * L / 2
        V.box(x - 0.45, -0.45, 0.75, x + 0.45, 0.45, h, "int_metal", faces="+x-x+y-y+z")
        V.poly(K.front_quad(x - 0.35, x + 0.35, 0.452, 0.85, h - 0.08), "int_plastic", glow=True, tint=(0.3, 0.9, 1.0))
    K.col_box(P.collision, -L / 2, -W / 2, 0.0, L / 2, W / 2, h, K.COL_NOCAM)
    return P


def vending(L, W, h):
    P = K.Prop("vending", col_closed=True)
    P.visual.box(-L / 2, -W / 2, 0.0, L / 2, W / 2, h, "int_plastic", faces="+x-x+y-y+z", tint=(0.9, 0.3, 0.25))
    P.visual.poly(K.front_quad(-L / 2 + 0.08, L / 2 - 0.3, W / 2 + 0.005, 0.5, h - 0.15), "int_glass", glow=True,
                  tint=(0.9, 0.95, 1.0))
    K.col_box(P.collision, -L / 2, -W / 2, 0.0, L / 2, W / 2, h, K.COL_NOCAM)
    return P


def vis_wall(L, h):
    P = K.Prop("vis_wall", col_closed=True)
    n = max(1, int(round(L / 1.5)))
    for i in range(n):
        x0 = -L / 2 + i * L / n
        for j in range(2):
            z0 = 0.6 + j * (h - 0.6) / 2
            P.visual.poly(K.front_quad(x0 + 0.02, x0 + L / n - 0.02, 0.06, z0 + 0.02, z0 + (h - 0.6) / 2 - 0.02),
                          "int_monitor", uvs=K.ONCE, glow=True)
    P.visual.box(-L / 2, 0.0, 0.55, L / 2, 0.05, h + 0.05, "int_plastic", faces="+y+x-x+z")
    return P


def counter_prop(poly, h=1.1):
    """Service-desk counter from the layout polygon (any shape): wood front, stone top."""
    P = K.Prop("counter", col_closed=True)
    pts = ccw(poly)
    P.visual.prism(pts, 0.0, h - 0.05, "int_wood_dark", top=None)
    P.visual.prism(pts, h - 0.05, h, "int_stone", top="int_stone")
    K.col_prism(P.collision, pts, 0.0, h, K.COL_NOCAM)
    return P


RANGE_STYLE = {   # (books, end-panel tint): the collections as photographed
    "Periodicals": ("int_ms_bound", MP.T_CORAL),            # F3 bound journals, coral end panels [#83 #87 #88]
    "Theses": ("int_ms_theses", MP.T_CORAL),                # F3 dark-green theses [#89 #90 #93]
    "A-QC": ("int_ms_stacks", MP.T_STEEL_BLUE),             # F4 general collection, steel-blue ends [#84-#86]
    "QC-Z": ("int_ms_stacks", MP.T_STEEL_BLUE),
    "Oversize": ("int_ms_stacks", MP.T_STEEL_BLUE),
    "Science Fiction": ("int_ms_stacks", (0.72, 0.74, 0.78)),   # F2 grey cantilever shelving [#82]
    "Course Reserves": ("int_books", (0.86, 0.66, 0.42)),       # maple-veneer reserve shelving [#33]
}


def range_prop_ms(L, W, h, seed, label=None, steps=True):
    """range_prop with the photographed look: 7-shelf light-grey steel sections and the floor's painted end panels
    (RANGE_STYLE). The climbing steps keep range_prop's exact boxes (a counter-height 1.07 m section at the climbing
    end, and a 2.29 m section on the 3.0 m ranges), built as lower steel sections. -> (prop, walkable tops)."""
    books, end_tint = RANGE_STYLE.get(label or "", ("int_ms_stacks", MP.T_STEEL_BLUE))
    P = K.Prop("range", col_closed=True)
    cap = 0.9
    tops = []
    C = P.collision

    def section(x0, x1, hh, rows=None, sd=0):
        P.merge(MP.range_unit(x1 - x0, W, hh, books=books, end_tint=end_tint, rows=rows, seed=seed + sd),
                (x0 + x1) / 2, 0.0, 0.0)
        K.col_box(C, x0, -W / 2, 0.0, x1, W / 2, hh, K.COL_NOCAM)
    if not steps or L < 3.0:
        section(-L / 2, L / 2, h)
        tops.append((-L / 2, L / 2, h))
        return P, tops
    if h > 2.6:
        section(-L / 2 + 2 * cap, L / 2, h, rows=9)
        section(-L / 2 + cap, -L / 2 + 2 * cap, K.REAL["stack_full_h"], rows=7, sd=1)
        section(-L / 2, -L / 2 + cap, K.REAL["stack_counter_h"], rows=3, sd=2)
        tops += [(-L / 2 + 2 * cap, L / 2, h), (-L / 2 + cap, -L / 2 + 2 * cap, K.REAL["stack_full_h"]),
                 (-L / 2, -L / 2 + cap, K.REAL["stack_counter_h"])]
    else:
        section(-L / 2 + cap, L / 2, h, rows=7)
        section(-L / 2, -L / 2 + cap, K.REAL["stack_counter_h"], rows=3, sd=2)
        tops += [(-L / 2 + cap, L / 2, h), (-L / 2, -L / 2 + cap, K.REAL["stack_counter_h"])]
    return P, tops


def ms_table_cluster(L, W, kind="rect", seed=0):
    """table_cluster's layout (the same table centres and sizes, so tops and book spots stay put) in the photographed
    furniture: maple tables with Sayl chairs ('rect'), race-track tables ('round_end')."""
    P = K.Prop("table_cluster", col_closed=True)
    n = max(1, int(L // 2.1))
    rows = 2 if W >= 3.4 else 1
    for i in range(n):
        x = -L / 2 + (i + 0.5) * L / n
        for r in range(rows):
            y = 0.0 if rows == 1 else (-W / 4 if r == 0 else W / 4)
            P.merge(MP.rect_table(min(1.83, L / n - 0.2), 0.91, chairs_per_side=2, ends_round=(kind == "round_end")),
                    x, y, 0.0, 0.0)
    return P


def service_desk_prop(poly, h=1.1):
    """The L-shaped service desk (#23): light-grey laminate front with a toe kick, a dark speckled solid-surface
    transaction top slightly proud of it, the lower work surface behind it. Collision: the footprint prism (as
    counter_prop)."""
    P = K.Prop("counter", col_closed=True)
    pts = ccw(poly)
    V = P.visual
    V.prism(pts, 0.0, 0.10, "int_plastic", top=None, tint=(0.62, 0.62, 0.64))
    V.prism([(x, y) for x, y in pts], 0.10, h - 0.06, "int_ms_wall", top=None, tint=MP.T_LAMINATE_GREY)
    big = offset_poly(pts, 0.05)
    V.prism(big, h - 0.06, h, "int_stone", top="int_stone", tint=MP.T_SOLID_SURFACE)
    K.col_prism(P.collision, pts, 0.0, h, K.COL_NOCAM)
    return P


def place_layout_props(M, fid, P, z):
    """Every layout prop of a floor, as kit props merged into the floor prop P (local z 0 = floor), in the look of
    the reference photos (positions, footprints and stand-on heights are the layout's)."""
    f = floor_of(M.layout, fid)
    seed = {"F1": 100, "F2": 200, "F3": 300, "F4": 400, "F5": 500}[fid]
    cent = (-60.0, -99.0)
    ranges = []
    for pr in f["props"]:
        typ, pid = pr["type"], pr["id"]
        if pid in PROP_MOVES and PROP_MOVES[pid] is None:
            continue
        poly = ccw(prop_poly(pr)) if "poly_m" in pr else None
        h = float(pr.get("height_m", 1.0))
        if typ == "range":
            h = min(h, TALL_RANGE_H)
        seed += 7
        if poly is not None:
            cx, cy, Lg, Wd, fac = long_axis(poly)
        if typ == "range":
            # climbing end toward the floor's centre (the main aisle)
            ends = [(cx + math.sin(math.radians(fac + 90)) * Lg / 2, cy + math.cos(math.radians(fac + 90)) * Lg / 2),
                    (cx - math.sin(math.radians(fac + 90)) * Lg / 2, cy - math.cos(math.radians(fac + 90)) * Lg / 2)]
            # local -x end = map end opposite to the +x direction (+x -> compass fac + 90)
            near_neg = math.dist(ends[1], cent) <= math.dist(ends[0], cent)
            face = fac if near_neg else (fac + 180.0) % 360.0
            rp, tops = range_prop_ms(Lg, Wd, h, seed, label=pr.get("label"))
            P.merge(rp, cx, cy, 0.0, face)
            sx, sy = math.sin(math.radians(face + 90)), math.cos(math.radians(face + 90))
            ranges.append({"id": pid, "c": (cx, cy), "L": Lg, "W": Wd, "u": (sx, sy), "tops": tops})
            for k, (x0, x1, tz) in enumerate(tops):
                xm = (x0 + x1) / 2
                M.stack_tops.append({"name": f"{fid.lower()}_{pid}" + ("" if k == 0 else f"_step{k}"),
                                     "floor": fid, "pos": (cx + sx * xm, cy + sy * xm, z + tz),
                                     "length_m": round(x1 - x0, 2), "height_m": round(tz, 2),
                                     "label": pr.get("label"), "main": k == 0})
        elif typ == "shelf_low":
            # F2 Collection Highlights / New Books (#24 #31 #32): grey steel display units with the white end-panel
            # signs, two per layout footprint (the rest of the footprint is lounge floor); F1 Maker Collection
            sign = {"highlights": "int_ms_sign_highlights", "new_books": "int_ms_sign_newbooks"}.get(pid)
            if fid == "F2" and sign:
                # two double-faced units at the north end of the footprint, long side E-W, the white sign panel
                # on the end toward the lobby / grand stair (highlights) or the east floor (new books) (#24 #31 #32)
                for k in range(2):
                    yy = cy + Lg / 2 - 0.65 - k * 1.55
                    P.merge(MP.low_shelf(1.5, 1.0, 1.15, sign=sign, seed=seed + k), cx, yy, 0.0,
                            180.0 if pid == "highlights" else 0.0)
            elif pid == "maker_collection":
                P.merge(MP.low_shelf(Lg, Wd, 1.2, seed=seed), cx, cy, 0.0, 0.0)
            else:
                P.merge(MP.low_shelf(Lg, min(Wd, 1.0), h, seed=seed), cx, cy, 0.0, fac)
        elif typ == "display_case":
            if fid == "F2":
                P.merge(MP.exhibit_case(Lg, Wd, 1.1), cx, cy, 0.0, fac)        # cherry cases (#26), in the lobby
            else:
                n = max(1, int(Lg // 1.05))                        # F3: grey microform cabinets (#94)
                for k in range(n):
                    P.merge(MP.microfiche_cabinet(1.0, min(Wd, 0.8), 1.35), cx,
                            cy - Lg / 2 + (k + 0.5) * Lg / n, 0.0, 90.0)
        elif typ == "counter":
            if pid == "sbux_counter":
                P.merge(cafe_counter_ms(Lg, Wd), cx, cy, 0.0, 270.0)
                M.anchor("cafe_counter_top", cx, cy, z + K.REAL["counter_h"], 270.0, floor=fid)
                M.anchor("cafe_customer_side", cx - 1.6, cy, z, 90.0, floor=fid)
            else:
                P.merge(service_desk_prop(poly, h), 0.0, 0.0, 0.0, 0.0)
                for mx, my, f_ in ((-62.0, -90.5, 225.0), (-59.6, -91.75, 180.0), (-55.6, -90.6, 135.0)):
                    P.merge(K.monitor(), mx, my, h, f_)
                P.merge(MP.service_ring_sign(1.75, 0.46, 3.55, hang_top=CLEAR), -60.4, -91.2, 0.0, 0.0)
                M.anchor("service_desk_counter", -58.7, -92.0, z + h, 180.0, floor=fid)
                M.anchor("service_desk_patron", -58.7, -93.6, z, 0.0, floor=fid)
        elif typ == "table_cluster":
            # photo pass 2: the west Commons (the layout's Act 5 arena) is furnished like the rest (#36 #39 #40)
            if fid == "F2" and pid.startswith("east_tables"):
                # long maple benching with frosted-glass dividers (#28), one per cluster footprint
                P.merge(MP.benching(min(Lg, 5.6), 1.5, seats_per_side=6), cx, cy, 0.0, fac)
            elif fid == "F2" and pid.startswith("sbux_tables"):
                for k in range(2):
                    P.merge(MP.round_table(0.76, chairs=2, rot=0.4), cx - Lg / 4 + k * Lg / 2, cy, 0.0, 0.0)
            elif fid == "F3" and pid.startswith("east_tables3"):
                # the 2018 guitar-pick tables (#76): one long rounded table per cluster
                P.merge(MP.guitar_pick_table(min(Lg, 4.6), 1.45, seats=8), cx, cy, 0.0, fac)
            elif fid == "F5" and pid == "reading_tables_n_3":
                # photo pass 2: the 2022 silent floor (#100-#102): perforated carrels back to back, Sayl chairs
                nn = max(1, int(Lg // 1.25))
                P.merge(MP.perf_carrels(nn, Lg / nn, (Wd - 0.08) / 2, panel_h=1.30, double=True), cx, cy, 0.0, fac)
            elif fid == "F5" and pid == "reading_tables_n_4":
                # ... and a lounge row (#100 #102): dark grey felt pods at the ends, the grey geometric lounge cubes
                # with blue cushions and maple side blocks between them, facing the north windows
                for xx in (cx - Lg / 2 + 0.8, cx + Lg / 2 - 0.8):
                    P.merge(MP.study_pod(1.5, 1.2, 1.40), xx, cy, 0.0, 0.0)
                x = cx - Lg / 2 + 2.2
                k = 0
                while x < cx + Lg / 2 - 1.9:
                    if k % 3 == 2:
                        P.merge(MP.side_table_block(0.55, 0.42), x - 0.15, cy, 0.0, 0.0)
                        x += 0.7
                    else:
                        P.merge(MP.lounge_cube(), x, cy, 0.0, 0.0 if k % 2 == 0 else 20.0)
                        x += 0.95
                    k += 1
            elif fid == "F1" and pid in ("commons_tables_05", "commons_tables_09"):
                P.merge(MP.commons_pod(1.2), cx, cy, 0.0, 45.0)          # #36: the pods mid-floor
            elif fid == "F1":
                P.merge(MP.benching(min(Lg, 4.8), 1.5, seats_per_side=5), cx, cy, 0.0, fac)
            else:
                P.merge(ms_table_cluster(Lg, Wd), cx, cy, 0.0, fac)
        elif typ == "computer_row":
            n = max(1, int(Lg // 0.9))
            if fid == "F2":
                # white-laminate computer benches back to back (#30): two double rows across the computer area
                nb = max(1, int(Lg // 0.95))
                for yy in (-109.9, -113.0):
                    P.merge(MP.computer_bench(nb, Lg / nb, 0.72, double=True), cx, yy, 0.0, fac)
            else:
                # perforated-panel computer carrels (#65 #66 #67), the chairs on the open side of the row
                nn = max(1, int(Lg // 1.2))
                face = fac
                ux, uy = math.sin(math.radians(fac)), math.cos(math.radians(fac))
                ahead = (cx + ux * (Wd / 2 + 0.8), cy + uy * (Wd / 2 + 0.8))
                if not M.inside(fid, *ahead) or M.in_tower(fid, *ahead) or M.region_at(fid, *ahead) is not None:
                    face = (fac + 180.0) % 360.0
                P.merge(MP.perf_carrels(nn, Lg / nn, min(Wd, 0.85), monitors=True, shelf=False, curved=False),
                        cx, cy, 0.0, face)
        elif typ == "carrel_row":
            n = max(1, int(Lg // 1.2))
            if Wd >= 1.35:
                # the 2022 perforated carrels back to back (#97 #98 #101): the spine top (1.30 m) is walkable
                P.merge(MP.perf_carrels(n, Lg / n, (Wd - 0.08) / 2, panel_h=1.30, double=True), cx, cy, 0.0, fac)
                M.anchor(f"carrel_top_{fid}_{pid}", cx, cy, z + 1.30, fac, floor=fid)
            else:
                P.merge(MP.perf_carrels(n, Lg / n, Wd), cx, cy, 0.0, fac)
        elif typ == "window_desk":
            dr = window_counter(Lg, min(Wd, 0.9))
            # chairs on the room side, away from the window (north desks -> chairs south; west -> east)
            P.merge(dr, cx, cy, 0.0, 180.0 if fac == 0.0 else 90.0)
        elif typ == "aquarium":
            P.merge(MP.fish_tank(Lg, max(Wd, 0.6), h), cx, cy, 0.0, 0.0)
            M.anchor("fish_tank_lid", cx, cy, z + h, 0.0, floor=fid)
        elif typ == "printer_3d":
            P.merge(printer_bench(Lg, Wd, h), cx, cy, 0.0, fac)
        elif typ == "workbench":
            P.merge(MP.butcher_island(Lg, Wd, h, stools=False), cx, cy, 0.0, 0.0 if Lg >= Wd else 90.0)
        elif typ == "visualization_wall":
            pass        # photo pass 2: the 2014 wall (#48) is gone; L136 has twin projection screens (#47, conference_l136)
        elif typ == "vending_machine":
            x, y = pr["pos_m"]
            sw, sd = pr.get("size_m", [1.0, 0.8])
            P.merge(MP.vending_machine(sw, sd, h), x, y, 0.0, float(pr.get("facing_deg", 180.0)))
        elif typ == "pier":
            P.merge(box_prop("pier", -Lg / 2, -Wd / 2, 0.0, Lg / 2, Wd / 2, 11.4, "int_ms_brick", cam=True), cx, cy, 0.0, 0.0)
        elif typ == "book_return_slot":
            x, y = pr["pos_m"]
            P.merge(box_prop("return_slot", -0.4, 0.0, 0.75, 0.4, 0.06, 1.25, "int_metal", col=False), x, y, 0.0, 90.0)
            P.merge(box_prop("return_slot_mouth", -0.3, 0.061, 0.98, 0.3, 0.07, 1.05, "int_plastic", col=False),
                    x, y, 0.0, 90.0)
            M.anchor("book_return_slot", x + 0.3, y, z, 90.0, floor=fid)
        elif typ == "printer":
            x, y = pr["pos_m"]
            P.merge(MP.printer_station(1.0, 0.7, 1.1), x, y, 0.0, 0.0)
        elif typ == "drinking_fountain":
            x, y = pr["pos_m"]
            P.merge(MP.drinking_fountain_pair(), x, y, 0.0, float(pr.get("facing_deg", 0.0)))
        elif typ == "wall_sign":
            pass
        elif typ in ("book_return", "duct", "skylight"):
            pass                                                    # outside / built elsewhere
        else:
            M.notes.setdefault("unplaced_props", []).append(f"{fid} {pid} ({typ})")
    range_bridges(M, fid, P, z, ranges)


def window_counter(L, D, h=0.76):
    """A window counter / bar (F5 north view windows, the west window desk; #76 #104): a long maple top on white
    panel legs with task chairs on the room side (+y). Collision: one block (its top is a book spot in act 2)."""
    P = K.Prop("window_counter", col_closed=True)
    V = P.visual
    V.box(-L / 2, -D / 2, h - 0.04, L / 2, D / 2, h, "int_ms_maple", faces=K.BOX_ALL)
    V.box(-L / 2, -D / 2, 0.0, L / 2, -D / 2 + 0.04, h - 0.04, "int_ms_wall", faces="+y-y", tint=(0.9, 0.9, 0.9))
    n = max(1, int(L // 1.0))
    for i in range(n + 1):
        x = -L / 2 + i * L / n
        V.box(x - 0.02, -D / 2, 0.0, x + 0.02, D / 2, h - 0.04, "int_ms_wall", faces="+x-x+y", tint=(0.9, 0.9, 0.9))
    for i in range(n):
        P.merge(MP.sayl_chair(), -L / 2 + (i + 0.5) * L / n, D / 2 + 0.25, 0.0, 180.0)
    K.col_box(P.collision, -L / 2, -D / 2, 0.0, L / 2, D / 2, h, K.COL_NOCAM)
    return P


def printer_bench(L, W, h):
    """Makerspace 3D printers (#53 #54): enclosed printers on a butcher-block bench, blue-lit print chambers."""
    P = K.Prop("printer_3d", col_closed=True)
    V = P.visual
    V.box(-L / 2, -W / 2, 0.70, L / 2, W / 2, 0.76, "int_ms_butcher", faces=K.BOX_ALL)
    V.box(-L / 2 + 0.05, -W / 2 + 0.05, 0.0, L / 2 - 0.05, W / 2 - 0.05, 0.70, "int_metal", faces="+x-x+y-y",
          tint=(0.6, 0.62, 0.66))
    for k in range(2):
        x = -L / 2 + (k + 0.5) * L / 2
        V.box(x - 0.42, -0.40, 0.76, x + 0.42, 0.40, h, "int_plastic", faces="+x-x+y-y+z", tint=(0.36, 0.36, 0.38))
        V.poly(K.front_quad(x - 0.32, x + 0.32, 0.402, 0.84, h - 0.08), "int_glass", glow=True, tint=(0.55, 0.85, 1.0))
    K.col_box(P.collision, -L / 2, -W / 2, 0.0, L / 2, W / 2, h, K.COL_NOCAM)
    return P


def cafe_counter_ms(L, D, h=K.REAL["counter_h"]):
    """The Marston cafe counter (#35): vertical wood-slat front, a light quartz top, a pastry case, the espresso
    machine and the order-pickup end. Local: x along the counter, the customer side +y. Collision: one block."""
    P = K.Prop("cafe_counter", col_closed=True)
    V = P.visual
    hl, hd = L / 2, D / 2
    V.box(-hl, -hd, 0.0, hl, hd, h - 0.05, "int_ms_slats", faces="+x-x+y-y")
    V.box(-hl - 0.03, -hd - 0.03, h - 0.05, hl + 0.03, hd + 0.04, h, "int_stone", faces=K.BOX_ALL, tint=(1.0, 0.98, 0.95))
    V.box(-hl + 0.4, -hd + 0.1, h, -hl + 2.2, hd - 0.05, h + 0.45, "int_glass", faces="+x-x+y-y+z", tint=(1.1, 1.1, 1.1))
    for k in range(4):
        V.box(-hl + 0.55 + k * 0.42, -0.12, h + 0.05, -hl + 0.85 + k * 0.42, 0.12, h + 0.14, "int_ms_leather",
              faces="+x-x+y-y+z", tint=[(0.8, 0.6, 0.3), (0.55, 0.35, 0.2), (0.9, 0.8, 0.6), (0.7, 0.45, 0.25)][k])
    V.box(0.6, -hd + 0.05, h, 1.4, hd - 0.15, h + 0.5, "int_metal", faces="+x-x+y-y+z", tint=(0.8, 0.8, 0.82))
    V.box(hl - 1.2, -hd + 0.05, h, hl - 0.3, hd - 0.1, h + 0.06, "int_metal", faces="+y+z", tint=(0.7, 0.7, 0.72))
    K.col_box(P.collision, -hl, -hd, 0.0, hl, hd, h, K.COL_NOCAM)
    P.anchor("top", 0.0, 0.0, h)
    return P


def range_bridges(M, fid, P, z, ranges):
    """Book-cart bridges (fix round): a plank across the aisle between two neighbouring parallel ranges whose
    climbing ends line up, over the section next to the end cap (a short range's 2.3 m top / a tall range's
    2.29 m step), so the tops of a row are one walkable route (step up from a 2.29 m step onto a 3.0 m top).
    Only between tops of the same height (+-5 cm) and across 2-4 m aisles; aisle headroom under a plank 2.2 m."""
    cap = 0.9
    n = 0

    def section(r):
        """centre (map), top height of the second 0.9 m section from the climbing end (local -x)"""
        s = -r["L"] / 2 + 1.5 * cap
        tz = next((t for x0, x1, t in r["tops"] if x0 - 1e-6 <= s <= x1 + 1e-6), None)
        return (r["c"][0] + r["u"][0] * s, r["c"][1] + r["u"][1] * s), tz
    for i, a in enumerate(ranges):
        if a["L"] < 3.0:
            continue
        pa, ta = section(a)
        best = None
        for b in ranges[i + 1:]:
            if b["L"] < 3.0 or a["u"][0] * b["u"][0] + a["u"][1] * b["u"][1] < 0.999:
                continue
            pb, tb = section(b)
            if ta is None or tb is None or abs(ta - tb) > 0.05:
                continue
            dx, dy = pb[0] - pa[0], pb[1] - pa[1]
            along = dx * a["u"][0] + dy * a["u"][1]
            lat = abs(dx * a["u"][1] - dy * a["u"][0])
            gap = lat - (a["W"] + b["W"]) / 2
            if abs(along) > 0.3 or not (2.0 <= gap <= 4.0):
                continue
            if best is None or gap < best[0]:
                best = (gap, b, pb, tb)
        if best is None:
            continue
        gap, b, pb, tb = best
        top = max(ta, tb)
        # axis-aligned in this layout (ranges run N-S or E-W)
        if abs(a["u"][0]) < 1e-6:                    # ranges along y: the bridge spans x
            xs = sorted((pa[0], pb[0]))
            x0, x1 = xs[0] + a["W"] / 2 - BRIDGE_ON, xs[1] - b["W"] / 2 + BRIDGE_ON
            y0, y1 = pa[1] - (cap - 0.1) / 2, pa[1] + (cap - 0.1) / 2
        elif abs(a["u"][1]) < 1e-6:                  # ranges along x: the bridge spans y
            ys = sorted((pa[1], pb[1]))
            y0, y1 = ys[0] + a["W"] / 2 - BRIDGE_ON, ys[1] - b["W"] / 2 + BRIDGE_ON
            x0, x1 = pa[0] - (cap - 0.1) / 2, pa[0] + (cap - 0.1) / 2
        else:
            continue
        top += 0.01                                  # 1 cm over the tops: no z-fighting where it rests on them
        P.merge(box_prop("book_bridge", x0, y0, top - BRIDGE_T, x1, y1, top, "int_metal", top="int_wood_dark",
                         faces="+x-x+y-y+z-z"), 0.0, 0.0, 0.0, 0.0)
        M.anchor(f"bridge_{fid.lower()}_{a['id']}_{b['id']}", (x0 + x1) / 2, (y0 + y1) / 2, z + top, 0.0, floor=fid)
        n += 1
    M.stats.setdefault("range_bridges", {})[fid] = n


# photo pass 2: layout props moved to where the photos show them (map polygons)
PROP_MOVES = {
    # the exhibit cases stand in the entrance lobby on the real plan (S3); the layout had moved them to the atrium's
    # south edge, where the lounge's S-banquettes now are (#24 #25). The game lobby is narrower (the core takes its
    # west half), so two cases stand along its east side and two are left out (NOTES)
    "exhibit_1": [(-65.85, -81.7), (-65.15, -81.7), (-65.15, -80.3), (-65.85, -80.3)],
    "exhibit_2": [(-65.85, -88.6), (-65.15, -88.6), (-65.15, -87.2), (-65.85, -87.2)],
    "exhibit_3": None,
    "exhibit_4": None,
    # Collection Highlights / New Books: two display units each (#31 #32) at the north of the layout's footprints, the
    # south of the court is the lounge
    "highlights": [(-60.0, -101.3), (-57.3, -101.3), (-57.3, -97.8), (-60.0, -97.8)],
    "new_books": [(-55.4, -101.3), (-52.6, -101.3), (-52.6, -97.7), (-55.4, -97.7)],
    # maker books on a low display shelf inside the makerspace glass (#51), not in the elevator lobby (#69 has none)
    "maker_collection": [(-79.5, -97.55), (-77.3, -97.55), (-77.3, -97.05), (-79.5, -97.05)],
}


def prop_poly(pr):
    return [tuple(p) for p in PROP_MOVES.get(pr["id"], pr["poly_m"])]


def register_footprints(M):
    """Prop footprints per floor (layout props + kiosks + gameplay furniture), known before the doors are
    planned so no door opens into a range or a counter."""
    for fid in FLOORS:
        f = floor_of(M.layout, fid)
        for pr in f["props"]:
            if pr["id"] in PROP_MOVES and PROP_MOVES[pr["id"]] is None:
                continue
            if pr["id"] in PROP_MOVES:
                M.props[fid].append((ccw(prop_poly(pr)), pr["type"], pr["id"], 1.2))
            elif "poly_m" in pr:
                hh = float(pr.get("height_m", 1.0))
                M.props[fid].append((ccw([tuple(p) for p in pr["poly_m"]]), pr["type"], pr["id"],
                                     min(hh, TALL_RANGE_H) if pr["type"] == "range" else hh))
            elif pr["type"] == "vending_machine":
                x, y = pr["pos_m"]
                sw, sd = pr.get("size_m", [1.0, 0.8])
                M.props[fid].append((rect_poly((x - sw / 2, y - sd / 2, x + sw / 2, y + sd / 2)), pr["type"], pr["id"],
                                     float(pr.get("height_m", 1.9))))
        for kid, k in M.layout["missions"]["design_act3_group_study_room_booking"]["kiosks"].items():
            if k["floor"] == fid:                     # keep the kiosk spots free of doors / furniture
                x, y = k["pos_m"]
                M.props[fid].append((rect_poly((x - 0.4, y - 0.4, x + 0.4, y + 0.4)), "kiosk_spot", kid, 0.0))
        if fid == "F4":
            M.props[fid].append((rect_poly((-45.9, -105.4, -45.1, -104.6)), "kiosk_spot", "K3_f4", 0.0))
    M.props["F1"].append((rect_poly((-83.0, -76.1, -81.2, -74.7)), "sorting_table", "sorting_table", 1.2))


# ================================================================== floors
def finish(M, fid, x, y):
    """Floor material (material, tint) at map (x, y) on floor fid, or None (closed / outside)."""
    if M.solid_at(fid, x, y):
        return FLOOR_CARPET[fid] if staff_view(M, fid, x, y) else None
    z = M.zone_at(fid, x, y)
    typ = z["type"] if z else "open_floor"
    # photo pass: carpet everywhere people sit (the entrance lobby too, #23), walk-off matting in the vestibule,
    # light-blue vinyl in the makerspace (#54), wood-look plank in the cafe and the wellness room (#74, inferred for
    # the cafe), dark linear carpet in the F1 study rooms (#44 #45), grey carpet in the classrooms (#47 #78)
    if typ == "vestibule":
        return ("int_ms_mat", None)
    if typ == "sorting_room":
        return ("int_floor_tile", None)
    if typ in ("cafe", "wellness"):
        return ("int_ms_plank", None)
    if typ == "makerspace":
        return ("int_ms_vinyl", None)
    if typ == "group_study":
        return ("int_ms_carpet", (0.92, 0.92, 0.94))
    if typ in ("conference", "classroom", "data_room"):
        return ("int_ms_carpet", (1.0, 1.04, 1.10))
    return FLOOR_CARPET[fid]


def window_openings(M, fid, a, b, s_keep):
    """Openings of the outline edge a->b (CCW): the layout windows and doors on it (s along a->b)."""
    f = floor_of(M.layout, fid)
    L = math.dist(a, b)
    dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    ops = []
    doors = []
    for o in f.get("openings", []):
        pa, pb = tuple(o["a_m"]), tuple(o["b_m"])
        if seg_point_dist(pa, a, b) > 0.15 or seg_point_dist(pb, a, b) > 0.15:
            continue
        s0 = (pa[0] - a[0]) * dx + (pa[1] - a[1]) * dy
        s1 = (pb[0] - a[0]) * dx + (pb[1] - a[1]) * dy
        s0, s1 = sorted((s0, s1))
        kind = "locked" if o["type"] == "door_locked" else "door"
        if kind == "locked" and fid == "F1":
            # fix round 5: the basement's emergency exits (S2) open onto below-grade areaways the stage does not build;
            # as glass they showed the void. Built as the usual opaque steel exit pair instead (inferred: unphotographed)
            kind = "steel"
        if o["id"] == "f1_sorting_door":
            continue
        h = 3.0 if o["type"] == "entrance" else DOOR_H
        doors.append({"s0": s0, "s1": s1, "z0": 0.0, "z1": h, "kind": kind, "id": o["id"]})
        if o["type"] == "entrance":                # glass transom over the doors (the OPEN 24 HOURS neon, #3 #4)
            ops.append({"s0": s0, "s1": s1, "z0": h + 0.08, "z1": STOREFRONT_HEAD, "kind": "window", "id": "transom"})
    for w in f.get("windows", []):
        pa, pb = tuple(w["a_m"]), tuple(w["b_m"])
        wd = (pb[0] - pa[0], pb[1] - pa[1])
        wl = math.hypot(*wd) or 1.0
        cross = (wd[0] * dy - wd[1] * dx) / wl
        sill, head = float(w["sill_m"]), min(float(w["head_m"]), CLEAR - 0.25)
        if w["id"] in WINDOW_OVERRIDES:
            sill, head = WINDOW_OVERRIDES[w["id"]]
        if w["id"] == "f2_storefront_n":
            head = STOREFRONT_HEAD                 # the black storefront under the copper cladding (#1 #2 #3)
        if abs(cross) < 0.05 and seg_point_dist(a, pa, pb) < 0.35 or abs(cross) < 0.05 and \
                seg_point_dist(pa, a, b) < 0.35 and seg_point_dist(pb, a, b) < 60:
            # parallel and on the same line
            dline = abs((pa[0] - a[0]) * (-dy) + (pa[1] - a[1]) * dx)
            if dline > 0.35:
                continue
            s0 = (pa[0] - a[0]) * dx + (pa[1] - a[1]) * dy
            s1 = (pb[0] - a[0]) * dx + (pb[1] - a[1]) * dy
            s0, s1 = sorted((s0, s1))
            s0, s1 = max(s0, 0.25), min(s1, L - 0.25)
            if s1 - s0 > 0.6:
                ops.append({"s0": s0, "s1": s1, "z0": sill, "z1": head, "kind": "window", "id": w["id"]})
        else:
            bx = bbox([pa, pb])
            if (in_rect(a, bx, 0.35) and in_rect(b, bx, 0.35)) and L < 6.0:
                if L > 0.9:
                    ops.append({"s0": 0.25, "s1": L - 0.25, "z0": sill, "z1": head, "kind": "window", "id": w["id"]})
    # doors win over windows; keep only inside the kept (non-tower) parts
    out = []
    for o in [o for o in ops if o.get("id") == "transom"]:
        out.append(o)
    ops = [o for o in ops if o.get("id") != "transom"]
    for o in ops:
        for k0, k1 in s_keep:
            for s0, s1 in intervals_subtract([(max(o["s0"], k0 + 0.2), min(o["s1"], k1 - 0.2))],
                                             [(d["s0"] - 0.3, d["s1"] + 0.3) for d in doors]):
                if s1 - s0 > 0.6:
                    out.append(dict(o, s0=s0, s1=s1))
    for d in doors:
        if any(k0 - 0.05 <= d["s0"] and d["s1"] <= k1 + 0.05 for k0, k1 in s_keep):
            out.append(d)
    return out


def build_floor(M, fid):
    """One floor in its local frame (z 0 = the floor top, placed at Z[fid], group fid): the slab under it,
    the outline walls with windows / doors and the facade, partitions, props, columns, lights, signs."""
    L = M.layout
    z = Z[fid]
    P = K.Prop(f"floor_{fid}", col_closed=False)
    V, C = P.visual, P.collision
    ol = M.outlines[fid]
    idx = FLOORS.index(fid)
    below = FLOORS[idx - 1] if idx > 0 else None
    ob = M.outlines[below] if below else None
    # ---------------- slab (this floor's floor; its bottom is the ceiling of the floor below)
    cover = [ol]
    if fid == "F2":
        cover += [rect_poly(PORCH), M.outlines["F1"]]
    elif ob is not None:
        cover.append(ob)
    # fix round 2: the basement's SW hall is SW_RECT_F1 (its east wall on the F1 outline, x -80.2); cutting the
    # upper floors' SW_RECT out of F1 left a 0.74 m strip with no floor between the hall and the Commons
    holes = [NE_RECT, SW_RECT_F1 if fid == "F1" else SW_RECT, CORE_RECT]
    edge_holes = []
    if fid == "F2":
        holes.append(CHUTE_HATCH)
        edge_holes.append(CHUTE_HATCH)
    if fid == "F3":
        h1 = (STAIR_LANDING[2], ATRIUM[1], ATRIUM[2], ATRIUM[3])
        h2 = (ATRIUM[0], STAIR_LANDING[3], STAIR_LANDING[2], ATRIUM[3])
        holes += [h1, h2]
        edge_holes += [h1, h2]
    elif fid in ("F4", "F5"):
        holes.append(ATRIUM)
        edge_holes.append(ATRIUM)
    zone_lines = ([p[0] for zz in floor_of(L, fid)["zones"] for p in zz["poly_m"]],
                  [p[1] for zz in floor_of(L, fid)["zones"] for p in zz["poly_m"]])
    if below:
        cl = coffer_lines(M, below)
        zone_lines = (zone_lines[0] + cl[0], zone_lines[1] + cl[1])

    def top_fn(x, y):
        if M.inside(fid, x, y):
            return finish(M, fid, x, y)
        if fid == "F2" and in_rect((x, y), PORCH):
            return ("int_stone", (0.86, 0.84, 0.8))
        if fid in ("F4", "F5") and ob is not None and pip((x, y), ob):
            return ("int_stone", (0.80, 0.80, 0.78))            # terrace pavers
        return None

    def top_col(x, y):
        if M.inside(fid, x, y):
            return not M.solid_at(fid, x, y)
        if fid == "F2":
            return True                                         # porch + the plaza / court over the basement
        return fid in ("F4", "F5") and ob is not None and pip((x, y), ob)

    def bot_fn(x, y):
        if below is None:
            return None
        if pip((x, y), ob):
            if in_coffer(M, below, x, y):
                return None                                     # the coffer grid (build_lights of the floor below)
            if M.solid_at(below, x, y):
                return ("int_ms_tile", None) if staff_view(M, below, x, y) else None
            # photo pass 2: the 2014 basement and the rooms have flat white 2' tile (#36 #47 #54 #78); the open
            # floors 2-5 keep the coffers' smooth paint on the flat soffits round them (#28 #76 #100)
            if below == "F1" or M.region_at(below, x, y) is not None:
                return ("int_ms_tile", None)
            return ("int_ms_coffer", (0.97, 0.97, 0.96))
        if fid == "F4" and in_rect((x, y), PORCH):
            return ("int_ms_copper", (0.92, 0.92, 0.92))         # the copper-clad porch soffit (#1 #3)
        return ("concrete", None)                               # porch / arcade soffit

    bot_col = (lambda x, y: below is not None) if below else None
    slab(V, C, cover, holes, top_fn, top_col, bot_fn if below else None, bot_col, edge_holes, zone_lines)
    # ---------------- outline walls + facade
    regions = M.regions[fid]
    n_ext = 0
    for a, b in edges(ol):
        Ls = math.dist(a, b)
        dx, dy = (b[0] - a[0]) / Ls, (b[1] - a[1]) / Ls
        ix, iy = -dy, dx
        keep, run = [], None
        s = 0.0
        while s <= Ls + 1e-6:
            pi = (a[0] + dx * s + ix * 0.25, a[1] + dy * s + iy * 0.25)
            po = (a[0] + dx * s - ix * 0.45, a[1] + dy * s - iy * 0.45)
            ok = not M.in_tower(fid, *pi) and not M.in_tower(fid, *po)
            if ok and run is None:
                run = s
            if not ok and run is not None:
                keep.append((run, s))
                run = None
            s += 0.05
        if run is not None:
            keep.append((run, Ls))
        keep = [(k0, k1) for k0, k1 in keep if k1 - k0 > 0.1]
        if not keep:
            continue
        ops = window_openings(M, fid, a, b, keep)
        # dark panes where the inside is a closed room
        for o in ops:
            if o["kind"] == "window":
                sm = (o["s0"] + o["s1"]) / 2
                pi = (a[0] + dx * sm + ix * 0.8, a[1] + dy * sm + iy * 0.8)
                if M.solid_at(fid, *pi):
                    o["kind"] = "dark"
                else:
                    M.daylight.append((fid, a, b, o["s0"], o["s1"], o["z0"], o["z1"]))
        for k0, k1 in keep:
            pa = (a[0] + dx * k0, a[1] + dy * k0)
            pb = (a[0] + dx * k1, a[1] + dy * k1)
            sub = [dict(o, s0=o["s0"] - k0, s1=o["s1"] - k0) for o in ops
                   if o["s0"] >= k0 - 1e-6 and o["s1"] <= k1 + 1e-6]
            mid = ((pa[0] + pb[0]) / 2 - ix * 0.6, (pa[1] + pb[1]) / 2 - iy * 0.6)
            col_out = (fid in ("F2", "F3") and in_rect(mid, PORCH)) or \
                (fid in ("F4", "F5") and ob is not None and pip(mid, ob))
            outer = None if fid == "F1" else (lambda s_, z_: "brick_red")
            if fid in ("F2", "F3") and abs(pa[1] - PORCH[1]) < 0.05 and abs(pb[1] - PORCH[1]) < 0.05:
                # the porch face is clad in weathered copper above the storefront (#1 #3)
                # below the copper the storefront is continuous black-anodised framing between the glass (#1 #2),
                # brick only on the west pier (the last 0.6 m)
                outer = (lambda s_, z_: "int_ms_copper") if fid == "F3" else \
                    (lambda s_, z_, pa=pa, pb=pb: "int_ms_copper" if z_ > STOREFRONT_HEAD - 0.05 else
                     ("brick_red" if pa[0] + (pb[0] - pa[0]) * s_ / math.dist(pa, pb) < -70.4 else "int_plastic"))
            has_win = any(o["kind"] in ("window", "dark") for o in sub)
            thick_wall(V, C, pa, pb, 0.0, CLEAR, in_mat="int_ms_wall", out_mat=outer, openings=sub, col_in=True,
                       col_out=col_out, in_tint=ext_wall_tint(M, fid, pa, pb, has_win), frame=WINDOW_FRAME,
                       bay=WINDOW_BAY, sill_ledge=fid != "F1")
            n_ext += 1
            if fid != "F1":
                # fascia band over the next slab's edge (dark trim), up to the next floor's top
                qa = (pa[0] - ix * WALL_T, pa[1] - iy * WALL_T)
                qb = (pb[0] - ix * WALL_T, pb[1] - iy * WALL_T)
                V.wall(qa, qb, CLEAR, STOREY, "dark_trim", ao=1.0)
                if col_out:
                    C.wall(qa, qb, CLEAR, STOREY, K.COL)
                # overhang fascia under this floor (porch / arcade) where the floor below does not continue
                if ob is not None and fid != "F2":
                    pbel = ((pa[0] + pb[0]) / 2 + ix * 0.4, (pa[1] + pb[1]) / 2 + iy * 0.4)
                    if not pip(pbel, ob):
                        V.wall(qa, qb, -SLAB, 0.0, "dark_trim", ao=1.0)
    # ---------------- the porch's open sides: invisible walls up to the F4 slab (the basement runs under the
    # plaza and the court, so stepping off would fall through the plaza instead of stopping at an OOB edge)
    if fid == "F2":
        px0, py0, px1, py1 = PORCH
        for a, b in (((px1, py1), (px0, py1)), ((px0, py1), (px0, py0))):
            for z0_, z1_ in ((0.0, 5.7), (5.7, Z["F4"] - Z["F2"] - SLAB)):
                # facing IN (onto the porch) only (fix round): the pair wall(a, b) + wall(b, a) collapsed into the
                # outward face in the exporter's remove_doubles, which a grounded player walking out skips
                C.wall(b, a, z0_, z1_, K.COL_NOCAM)
    # ---------------- terrace parapets (the edges of the floor below that this floor does not cover)
    if fid in ("F4", "F5"):
        n_par = 0
        for a, b in edges(ob):
            Ls = math.dist(a, b)
            dx, dy = (b[0] - a[0]) / Ls, (b[1] - a[1]) / Ls
            ix, iy = -dy, dx
            keep, run, s_ = [], None, 0.0
            while s_ <= Ls + 1e-6:
                pi = (a[0] + dx * s_ + ix * 0.3, a[1] + dy * s_ + iy * 0.3)
                ok = pip(pi, ob) and not M.inside(fid, *pi) and not M.in_tower(fid, *pi, 0.05)
                if ok and run is None:
                    run = s_
                if not ok and run is not None:
                    keep.append((run, s_))
                    run = None
                s_ += 0.05
            if run is not None:
                keep.append((run, Ls))
            for k0, k1 in keep:
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
        M.stats.setdefault("parapet_runs", {})[fid] = n_par
    # ---------------- partitions, props, columns
    build_partitions(M, fid, P)
    place_layout_props(M, fid, P, z)
    extras_for_floor(M, fid, P, z)
    for (x, y) in floor_of(L, fid).get("columns_m", []):
        if not M.inside(fid, x, y) or M.in_tower(fid, x, y, 0.6) or M.solid_at(fid, x, y):
            continue
        if fid != "F1" and in_rect((x, y), ATRIUM, 0.5):
            continue
        if any(pip((x, y), poly) or any(math.dist((x, y), q) < 0.7 for q in poly) for poly, *_ in M.props[fid]):
            continue
        if M.region_at(fid, x, y) is not None:
            continue
        P.merge(ms_column(fid), x, y, 0.0, 0.0)
    # ---------------- ceiling lights (on this floor's ceiling, local z CLEAR)
    build_lights(M, fid, P)
    M.add(P, 0.0, 0.0, z, 0.0, tag=f"floor_{fid}", group=fid)
    M.stats.setdefault("exterior_wall_runs", {})[fid] = n_ext


def coffer_cells(M, fid):
    """The 1987 ceiling coffers over floor fid (F2-F5): {(i, j): (x0, y0, x1, y1)}, 10 ft squares on the 30 ft module
    grid (three per bay), every cell wholly over the open floor: not over a room, a tower or the core, the atrium void,
    the porch or outside. The flat slab underside fills the rest (partial cells at the walls, rooms)."""
    if fid == "F1":
        return {}
    ox, oy = COFFER_ORIGIN
    x0b, y0b, x1b, y1b = bbox(M.outlines[fid])
    out = {}
    for i in range(int(math.floor((x0b - ox) / COFFER)), int(math.ceil((x1b - ox) / COFFER)) + 1):
        for j in range(int(math.floor((y0b - oy) / COFFER)), int(math.ceil((y1b - oy) / COFFER)) + 1):
            x0, y0 = ox + i * COFFER, oy + j * COFFER
            x1, y1 = x0 + COFFER, y0 + COFFER
            ax0, ay0, ax1, ay1 = ATRIUM
            if x0 < ax1 + 0.05 and x1 > ax0 - 0.05 and y0 < ay1 + 0.05 and y1 > ay0 - 0.05:
                continue
            m = 0.12
            probe = [(x0 + m, y0 + m), (x1 - m, y0 + m), (x1 - m, y1 - m), (x0 + m, y1 - m), ((x0 + x1) / 2, (y0 + y1) / 2),
                     ((x0 + x1) / 2, y0 + m), ((x0 + x1) / 2, y1 - m), (x0 + m, (y0 + y1) / 2), (x1 - m, (y0 + y1) / 2)]
            if all(M.inside(fid, *p) and not M.in_tower(fid, *p, WALL_T + 0.05) and M.region_at(fid, *p) is None
                   for p in probe):
                out[(i, j)] = (x0, y0, x1, y1)
    return out


def in_coffer(M, fid, x, y):
    if fid not in M.coffers:
        return False
    ox, oy = COFFER_ORIGIN
    return (int(math.floor((x - ox) / COFFER)), int(math.floor((y - oy) / COFFER))) in M.coffers[fid]


def coffer_lines(M, fid):
    """Grid lines of floor fid's coffers (for the slab cell grids, so the flat underside meets them exactly)."""
    cells = M.coffers.get(fid) or {}
    xs = sorted({v for c in cells.values() for v in (c[0], c[2])})
    ys = sorted({v for c in cells.values() for v in (c[1], c[3])})
    return xs, ys


def louver_troffer(length=1.2, width=0.6, radius=6.0, strength=0.30):
    """2' x 4' parabolic egg-crate troffer (the classrooms and rooms, #47 #78): glowing, adds a Light."""
    P = K.Prop("troffer", col_closed=True)
    hw, hl = width / 2.0, length / 2.0
    P.visual.poly([(-hl, -hw, -0.012), (-hl, hw, -0.012), (hl, hw, -0.012), (hl, -hw, -0.012)], "int_ms_louver",
                  uvs=[(0, 0), (0, 1), (1, 1), (1, 0)], glow=True, tint=(0.97, 0.97, 0.95))
    P.lights.append(K.Light((0.0, 0.0, -0.6), radius=radius, strength=strength))
    return P


def build_lights(M, fid, P):
    """Ceiling fixtures (local z CLEAR = the ceiling): F2-F5 the coffer grid (a lay-in light in every other coffer,
    diffusers and downlights in the rest, #23 #84 #100), troffers in the rooms; F1 the 2014 ceiling (f1_ceiling)."""
    n = 0
    if fid == "F1":
        n = f1_ceiling(M, P)
    else:
        cells = M.coffers[fid]
        for (i, j), (x0, y0, x1, y1) in sorted(cells.items()):
            if (i + j) % 2 == 0:
                kind = "light"
                n += 1
            else:
                kind = "diffuser" if (i % 3 == 0) else "can"
            # ribs: every coffer draws its south and west grid lines, plus north / east on the grid's edge
            ribs = "sw" + ("n" if (i, j + 1) not in cells else "") + ("e" if (i + 1, j) not in cells else "")
            P.merge(MP.coffer(COFFER, COFFER_DEPTH, kind=kind, ribs=ribs, turn=(i * 3 + j * 2) % 4),
                    (x0 + x1) / 2, (y0 + y1) / 2, CLEAR, 0.0)
        M.stats.setdefault("coffers", {})[fid] = len(M.coffers[fid])
    # rooms: flat 2 x 4 tile ceilings with troffers on a ~2.4 m grid
    for r in M.regions[fid]:
        if r["kind"] == "solid":
            continue
        x0, y0, x1, y1 = bbox(r["poly"])
        nx_, ny_ = max(1, int(round((x1 - x0) / 2.6))), max(1, int(round((y1 - y0) / 2.6)))
        for a in range(nx_):
            for b in range(ny_):
                x, y = x0 + (x1 - x0) * (a + 0.5) / nx_, y0 + (y1 - y0) * (b + 0.5) / ny_
                if not pip((x, y), r["poly"]):
                    continue
                if r["type"] == "group_study":
                    P.merge(louver_troffer(0.62, 0.62, 5.0, 0.30), x, y, CLEAR, 0.0)
                else:
                    P.merge(louver_troffer(), x, y, CLEAR, 90.0 if (x1 - x0) < (y1 - y0) else 0.0)
                n += 1
    M.stats.setdefault("ceiling_lights", {})[fid] = n


F1_RINGS = [  # (x, y, radius, inner colour): the 2014 ring pendants (#36 purple, #37 #41 blue, #61 #64 olive)
    (-56.40, -83.85, 2.3, (0.56, 0.38, 0.80)),
    (-47.25, -93.00, 2.0, (0.30, 0.52, 0.86)),
    (-47.25, -111.30, 2.3, (0.56, 0.38, 0.80)),
    (-65.55, -84.80, 1.8, (0.30, 0.52, 0.86)),
    (-56.40, -102.15, 2.3, (0.56, 0.38, 0.80)),
    (-78.40, -63.40, 2.2, (0.62, 0.62, 0.36)),      # North Computer Lab (olive inside, #61)
    (-75.70, -111.30, 1.9, (0.62, 0.62, 0.36)),     # South Computer Lab
]


def f1_ceiling(M, P):
    """Floor 1 (2014): linear LED slots in the flat tile ceiling (rows E-W, 3.05 m apart, staggered runs, #36 #40),
    the aluminium ring pendants (F1_RINGS) and the translucent blue wave ribbons over the elevator lobby (#69).
    Returns the number of light fixtures."""
    n = 0
    ox, oy = COFFER_ORIGIN

    def clear(x, y):
        return M.inside("F1", x, y) and not M.in_tower("F1", x, y, WALL_T + 0.2) and M.region_at("F1", x, y) is None \
            and not in_rect((x, y), (DUCT["x"][0] - 0.2, DUCT["y"][0] - 0.2, DUCT["x"][1] + 0.2, DUCT["y"][1] + 0.2))
    x0b, y0b, x1b, y1b = bbox(M.outlines["F1"])
    j = 0
    y = oy + COFFER / 2
    while y < y1b:
        if y > y0b:
            # runs of 6.1 m with 1.5 m gaps, staggered row to row
            x = ox - (j % 2) * 3.0 - 0.75
            while x - 6.1 > x0b:
                xa, xb = x - 6.1, x
                pts = [(xa + (xb - xa) * k / 8, y) for k in range(9)]
                if all(clear(*p) for p in pts) and not any(math.hypot(px - rx, y - ry) < rr + 0.4
                                                               for rx, ry, rr, _ in F1_RINGS for px in (xa, (xa + xb) / 2, xb)):
                    P.merge(MP.led_strip(6.1), (xa + xb) / 2, y, CLEAR, 0.0)
                    for k in range(2):
                        P.lights.append(K.Light((xa + 1.5 + 3.05 * k, y, CLEAR - 0.8), radius=6.5, strength=0.22,
                                                color=(0.96, 0.98, 1.0)))
                    n += 1
                x -= 7.6
            j += 1
        y += COFFER
    for (x, y, r, inner) in F1_RINGS:
        P.merge(MP.ring_pendant(r, inner=inner), x, y, CLEAR, 0.0)
        n += 1
    # the wave ribbons over the elevator lobby (south of the core, #69; the 'wavy blue ceiling panels' of #37 #39)
    for k, (yy, xs) in enumerate(((-91.9, -79.6), (-93.5, -80.4), (-95.1, -79.0))):
        P.merge(MP.wave_ribbon(L=9.2, w=0.9, amp=0.38, waves=1.5, drop=0.55 + 0.12 * k), xs, yy, CLEAR, 0.0)
    return n


def extras_for_floor(M, fid, P, z):
    """Fixed dressing of one floor merged into the floor prop (signs, wall fixtures, the study rooms' insides, the
    kiosk anchors) plus the free-standing furniture queued with dress() (placed by place_dressing() once the pickups
    are planned). Everything follows the reference photos (#n in the comments)."""
    kiosks = M.layout["missions"]["design_act3_group_study_room_booking"]["kiosks"]
    for kid, k in kiosks.items():
        if k["floor"] != fid:
            continue
        x, y = k["pos_m"]
        face = {"K1": 0.0, "K2": 180.0, "K3": 0.0, "K4": 90.0}[kid]
        # no kiosk geometry: uf_marston_missions.lua spawns the kiosks (Lua bodies) for act 3
        f = math.radians(face)
        M.anchor(f"kiosk_{kid}", x, y, z, face, floor=fid, punch=(round(x + math.sin(f) * 0.62, 3),
                                                                  round(y + math.cos(f) * 0.62, 3)))
    study_rooms(M, fid, P)
    if fid == "F1":
        dress_f1(M, P, z)
    elif fid == "F2":
        dress_f2(M, P, z)
    elif fid == "F3":
        dress_f3(M, P, z)
    elif fid == "F4":
        dress_f4(M, P, z)
    elif fid == "F5":
        dress_f5(M, P, z)
    exit_signs(M, fid, P)


def study_rooms(M, fid, P):
    """The glass group-study rooms (#36 #38 #44-#46): a dark name plaque over the door outside (scientists' names,
    #38 'Heisenberg', #36 'Carson', 'Franklin'), a wood door leaf standing open inside, a wall TV opposite the
    door, and either a round table with two taupe shell chairs (#44 #46) or a counter-height table with stools
    (#45); a teal accent wall in every third room (#44 #46)."""
    k = 0
    for r in M.regions[fid]:
        if r["type"] != "group_study":
            continue
        d = next((d for d in M.doors[fid] if d["room"] == r["id"]), None)
        x0, y0, x1, y1 = bbox(r["poly"])
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if d is None:
            continue
        f = math.radians(d["facing"])
        fx, fy = math.sin(f), math.cos(f)                  # outward (door facing)
        dcx, dcy = d["centre"]
        if fid == "F1":
            atlas = "int_ms_names" if k % 8 < 4 else "int_ms_names_b"
            P.merge(MP.name_plaque(k % 4, atlas, 0.95, 0.15, DOOR_H + 0.25), dcx + fx * 0.06, dcy + fy * 0.06, 0.0,
                    d["facing"])
        # the wall opposite the door: TV; the door leaf swung open against the inside of the door wall
        half = abs(fx) * (x1 - x0) / 2 + abs(fy) * (y1 - y0) / 2
        span = abs(fy) * (x1 - x0) + abs(fx) * (y1 - y0)
        P.merge(MP.wall_tv(min(1.4, span - 1.2), 0.78, 1.3), cx - fx * (half - 0.03), cy - fy * (half - 0.03), 0.0,
                d["facing"])
        (ax, ay), (bx, by) = d["a"], d["b"]
        hinge = (ax - fx * 0.05, ay - fy * 0.05)
        along = math.degrees(math.atan2(bx - ax, by - ay))
        P.merge(MP.door_leaf(0.92, DOOR_H - 0.3, open_deg=-95.0), hinge[0], hinge[1], 0.0, (along - 90.0) % 360.0)
        if r["id"] == "L129":                              # the act 3 star room: chairs in the corners only
            for (qx, qy) in ((x0 + 0.6, y0 + 0.6), (x1 - 0.6, y0 + 0.6)):
                P.merge(MP.tub_chair(MP.T_TAUPE), qx, qy, 0.0, facing_from((qx, qy), (cx, cy)))
            k += 1
            continue
        if min(x1 - x0, y1 - y0) >= 2.6:
            if k % 2 == 0:
                P.merge(MP.round_table(0.76, chairs=0), cx - fx * 0.3, cy - fy * 0.3, 0.0, 0.0)
                for sgn in (1, -1):
                    px, py = cx - fx * 0.3 + fy * sgn * 0.95, cy - fy * 0.3 - fx * sgn * 0.95
                    P.merge(MP.tub_chair(MP.T_TAUPE, col=False), px, py, 0.0, facing_from((px, py), (cx, cy)))
            else:
                along_x = abs(fy) > abs(fx)
                P.merge(MP.rect_table(min(1.9, span - 1.4), 0.9, 1.05, chairs_per_side=2,
                                      chair=lambda: MP.caper_stool(0.76), ends_round=True),
                        cx - fx * 0.3, cy - fy * 0.3, 0.0, 0.0 if along_x else 90.0)
        if k % 3 == 0:                                     # teal accent wall (a side wall)
            sx, sy = (cx + fy * (abs(fx) * 0 + (x1 - x0) / 2 - 0.02), cy) if abs(fy) > abs(fx) else \
                (cx, cy + fx * ((y1 - y0) / 2 - 0.02))
            L = (y1 - y0) if abs(fy) > abs(fx) else (x1 - x0)
            face = 270.0 if abs(fy) > abs(fx) else 180.0
            if abs(fy) > abs(fx) and fy < 0:
                face = 90.0
            accent = K.Prop("accent", col_closed=True)
            accent.visual.wall((L / 2 - 0.1, 0.012), (-L / 2 + 0.1, 0.012), 0.1, CLEAR - 0.05, "int_ms_wall",
                               tint=MP.T_TEAL_WALL)
            P.merge(accent, sx, sy, 0.0, face)
        k += 1


def exit_signs(M, fid, P):
    """Red EXIT signs over the stair / core doors (#24 #47 #69 #76)."""
    # fix round 5: the tower / core door signs sat inside their 0.3 m walls (y -79.2 between the faces at -79.0 and
    # -79.3, x -69.5 between -69.7 and -69.4), hidden by the walls' outer faces: now on the outer faces
    ne, core = (-51.0, -79.31, 180.0), (-69.39, -85.2, 90.0)
    spots = {"F1": [ne, core, (-80.19, -86.1, 90.0), (-75.65, -52.51, 180.0)],   # + the two steel exits
             "F2": [ne, core, (-67.2, -79.0, 180.0)],
             "F3": [ne, core],
             "F4": [ne, core],
             "F5": [core]}
    for x, y, f in spots.get(fid, []):
        P.merge(MP.exit_sign(DOOR_H + 0.35), x, y, 0.0, f)


def dress(M, fid, prop, x, y, facing=0.0, note=None, keep=0.0):
    """Queue a free-standing piece (map x, y on floor fid); place_dressing() places it after the pickups are planned,
    unless its collision would crowd a coin formation, a heart / Goomba, a kiosk, a door or another anchor."""
    M.dressing.append({"floor": fid, "prop": prop, "pos": (x, y), "facing": facing, "note": note or prop.kind,
                       "keep": keep})


def prop_rect(prop, x, y, facing):
    """Plan footprint (x0, y0, x1, y1) of a prop placed at map (x, y) with a compass facing: every visual or
    collision face between 3 cm and 2.4 m above its floor (lights and signs overhead do not count)."""
    pl = prop.placed(x, y, 0.0, facing)
    xs, ys = [], []
    for p in pl.visual.polys + pl.collision.polys:
        zs = [q[2] for q in p.pts]
        if max(zs) < 0.03 or min(zs) > 2.4:
            continue
        xs += [q[0] for q in p.pts]
        ys += [q[1] for q in p.pts]
    if not xs:
        return (x, y, x, y)
    return (min(xs), min(ys), max(xs), max(ys))


def _rects_hit(a, b, m=0.0):
    return a[0] < b[2] + m and b[0] < a[2] + m and a[1] < b[3] + m and b[1] < a[3] + m


def furnish(M, fid, prop, x, y, facing=0.0, room=None, margin=0.30, note=None):
    """Photo pass 2: queue a free-standing piece (dress()) only where it fits: its whole footprint on this floor's
    open floor (or inside room `room` = a region id), off the stair halls / core / atrium void / grand stair, clear
    of the module columns, the layout props and every piece queued before it by `margin`. Returns True if queued,
    else notes it in M.notes['furnish_skipped'] (the plan check drawing shows those)."""
    r = prop_rect(prop, x, y, facing)
    why = None
    nx_, ny_ = max(2, int((r[2] - r[0]) / 0.5) + 2), max(2, int((r[3] - r[1]) / 0.5) + 2)
    for i in range(nx_):
        for j in range(ny_):
            px_ = r[0] + (r[2] - r[0]) * i / (nx_ - 1)
            py_ = r[1] + (r[3] - r[1]) * j / (ny_ - 1)
            if not M.inside(fid, px_, py_) or M.in_tower(fid, px_, py_, 0.25):
                why = "outside / stair hall"
                break
            reg = M.region_at(fid, px_, py_)
            if (reg["id"] if reg else None) != room:
                why = f"room {reg['id'] if reg else 'open floor'}"
                break
        if why:
            break
    if not why and fid != "F1":
        a = ATRIUM
        if fid == "F2":
            a = (GRAND_STAIR_X[0], ATRIUM[1], GRAND_STAIR_X[1] + 0.4, ATRIUM[3])     # the grand stair
        if _rects_hit(r, a, 0.3):
            why = "atrium / grand stair"
    if not why:
        for (cx, cy) in floor_of(M.layout, fid).get("columns_m", []):
            if _rects_hit(r, (cx - 0.35, cy - 0.35, cx + 0.35, cy + 0.35), margin):
                why = f"column {cx, cy}"
                break
    if not why:
        for poly, kind, pid, h in M.props[fid]:
            if _rects_hit(r, bbox(poly), margin):
                why = f"prop {pid}"
                break
    if not why:
        for it in M.dressing:
            if it["floor"] == fid and _rects_hit(r, it.get("rect") or prop_rect(it["prop"], it["pos"][0], it["pos"][1],
                                                                                 it["facing"]), margin):
                why = f"dressing {it['note']}"
                break
    if why:
        M.notes.setdefault("furnish_skipped", []).append(f"{fid} {note or prop.kind} at ({x:.1f}, {y:.1f}) ({why})")
        return False
    dress(M, fid, prop, x, y, facing, note=note)
    M.dressing[-1]["rect"] = r
    return True


def dress_f1(M, P, z):
    """Floor 1, the 2014 Collaboration Commons (#36-#43, #61-#64, #69), furnished as densely as the photos show (700+
    seats): commons pods, benching rows with frosted dividers, round maple tables under the ring pendants, the salmon
    / olive S-banquettes and bent-plywood chairs by the glass rooms, counter-height bar tables with black stools, the
    hexagon ottomans of the elevator lobby, the two computer labs' rows, the makerspace (brick walls, black-framed
    glass front with the yellow neon, butcher-block islands, pegboard, 3D printers) and conference room L136 (twin
    screens, training tables, lectern, chair rail). Photo pass 2 furnishes the layout's Act 5 arena too (the real
    west Commons is full of tables, #36 #39 #40); see NOTES."""
    # sorting room (gameplay, staff look) + the duct step
    for k, x in enumerate((-79.6, -76.6)):
        P.merge(K.bookshelf(2.7, K.REAL["stack_mid_h"], 0.45, double=False, seed=900 + k, books=("int_ms_stacks",),
                            carcass="int_shelf_steel", end_panel="int_shelf_steel"), x + 1.35, -74.6, 0.0, 180.0)
    P.merge(box_prop("sorting_table", -0.9, -0.7, 0.0, 0.9, 0.7, 1.2, "int_metal", top="int_ms_butcher"),
            -82.1, -75.4, 0.0, 0.0)
    M.anchor("duct_step_sorting_table", -82.1, -75.4, z + 1.2, 0.0, floor="F1")
    P.merge(K.book_cart(seed=3), -75.0, -81.0, 0.0, 90.0)
    P.merge(K.book_cart(seed=4), -72.5, -81.6, 0.0, 70.0)
    P.merge(K.whiteboard(2.4, 1.2, 0.9), -83.05, -64.0, 0.0, 90.0)
    # the commons help desk (printing help, S1) beside the makerspace
    P.merge(K.help_desk(2.0, return_len=0.0, hang_z=2.9, hang_top=CLEAR), -70.3, -98.8, 0.0, 90.0)
    # elevator lobby (#69): hexagon ottomans (salmon + sand, nested), stainless bins, stanchions, the directory
    # a honeycomb cluster as photographed (#39 #69): flat-topped hexagons nose to tail, salmon and sand
    hx, hy = -77.7, -94.35
    for (u, v, tint) in ((0, 0, MP.T_SALMON), (1, 1, MP.T_SALMON), (2, 0, MP.T_SAND), (3, 1, MP.T_SALMON),
                         (1, -1, MP.T_SAND), (2, -2, MP.T_SALMON), (4, 0, MP.T_SAND)):
        dress(M, "F1", MP.hex_ottoman(0.55, 0.45, tint), hx + u * 0.855, hy + v * 0.494, 0.0)
    P.merge(K.sign("int_ms_directory", 0.55, 0.75, 1.35, mount="wall"), -73.7, -90.6, 0.0, 180.0)
    P.merge(MP.drinking_fountain_pair(), -80.2, -92.6, 0.0, 90.0)
    for x in (-71.2, -70.6):
        P.merge(MP.stanchion(), x, -91.8, 0.0, 0.0)
    makerspace(M, P)
    south_lab(M)
    conference_l136(M, P)

    def bench(x, y, L=4.8, f=0.0, n=5):
        furnish(M, "F1", MP.benching(L, 1.5, seats_per_side=n), x, y, f, note="benching")

    def rtab(x, y, rot=0.3):
        furnish(M, "F1", MP.round_table(1.07, chairs=4, rot=rot), x, y, 0.0, note="round_table")

    def pod(x, y, f=0.0):
        furnish(M, "F1", MP.commons_pod(1.2), x, y, f, note="commons_pod")
    # north strip under L115-L117 (#40): benching rows
    for y in (-70.4, -73.6):
        bench(-66.6, y)
    # commons centre (#36 #37 #40): pods, round tables under the rings, benching rows
    pod(-65.5, -79.0)
    for (x, y) in ((-66.0, -83.0), (-64.2, -86.4), (-58.8, -83.4), (-53.4, -82.9)):
        rtab(x, y)
    bench(-66.0, -91.6)
    rtab(-49.4, -91.6)
    # east, by the glass rooms (#38 #41): S-banquettes round ottoman tables, bent-plywood chairs, bar tables
    furnish(M, "F1", MP.banquette_arc(1.0, 0.62, 95.0, 265.0, MP.T_SALMON, "int_ms_fab_multi", None, MP.T_OLIVE_BASE),
            -40.9, -100.0, 0.0, note="banquette")
    dress(M, "F1", MP.round_table(0.9, h=0.42, chairs=0), -40.9, -100.0, 0.0, note="lounge_table")
    furnish(M, "F1", MP.banquette_arc(1.0, 0.62, 275.0, 445.0, MP.T_SALMON, "int_ms_fab_multi", None, MP.T_OLIVE_BASE),
            -44.6, -103.4, 0.0, note="banquette")
    dress(M, "F1", MP.round_table(0.9, h=0.42, chairs=0), -44.6, -103.4, 0.0, note="lounge_table")
    for (x, y, f) in ((-45.0, -99.4, 120.0), (-40.6, -104.2, 300.0), (-46.6, -100.8, 90.0)):
        furnish(M, "F1", MP.bentply_chair(), x, y, f, note="bentply_chair", margin=0.15)
    for y in (-109.4, -112.2):
        furnish(M, "F1", MP.bar_table(2.4, 0.75, 1.05, 3), -43.2, y, 0.0, note="bar_table")
    # south band above the study rooms L130-L135 (#40)
    for x in (-56.4, -47.4):
        bench(x, -116.6, 4.2, 0.0, 4)
    # the west Commons (the layout's Act 5 arena; its table clusters are benching rows like the others): round tables
    # between the rows (#39 #40 #36)
    for (x, y) in ((-67.4, -100.2), (-67.4, -108.2), (-59.0, -108.4), (-52.6, -100.2)):
        rtab(x, y, 0.5)
    # North Computer Lab (#61 #62): two blocks of double rows each side of the aisle (the coin line runs down it)
    for y in (-57.6, -61.2, -64.8, -68.4):
        dress(M, "F1", MP.lab_cubicles(3, 1.0, 0.76, double=True), -79.35, y, 0.0)
        dress(M, "F1", MP.lab_cubicles(2, 1.0, 0.76, double=True), -75.15, y, 0.0)


def south_lab(M):
    """The South Computer Lab (#63, 30 PCs): grey-screen double rows with maple desks and Sayl chairs, the olive end
    wall (ext_wall_tint) and its olive ring pendant (F1_RINGS)."""
    for y in (-108.6, -111.6):
        for x in (-77.4, -73.8):
            furnish(M, "F1", MP.lab_cubicles(3, 1.0, 0.76, double=True), x, y, 0.0, note="lab_cubicles", margin=0.2)
    for x in (-77.4, -73.8):
        furnish(M, "F1", MP.lab_cubicles(3, 1.0, 0.76, double=False), x, -115.7, 0.0, note="lab_cubicles",
                margin=0.05)


def makerspace(M, P):
    """The Marston Makerspace (former MADE@UF L100; #50-#60): the black-framed glass front on the elevator lobby with
    the yellow MARSTON MAKERSPACE neon behind it, red brick on the Commons side with a TV and the pegboard tool wall,
    butcher-block islands with bin shelves, crocheted jellyfish hanging from the 2' tile ceiling. The 3D printers and
    the sewing bench are layout props; the west wall is the light-well glazing (#54)."""
    x0, y0, x1, y1 = -80.2, -106.8, -71.3, -96.8
    # the black-framed glass storefront faces north onto the elevator lobby and its hexagon ottomans (#39 #51 #69:
    # the ottomans sit between the elevators and the glass), a 2.4 m gap for the door (real: one leaf, co-op)
    for (xa, xb) in ((x0 + 0.3, -77.6), (-75.2, x1)):
        thin_partition(P.visual, P.collision, (xa, y1), (xb, y1), 0.0, CLEAR, "glass", frame="int_plastic",
                       post_every=1.2)
    P.merge(MP.glass_sign("int_ms_neon_maker", 1.7, 0.85, 1.55), -73.4, y1 - 0.12, 0.0, 0.0)
    # red brick east wall toward the Commons help desk (#53 #55 #56: brick inside), open in the middle (the arena)
    for (ya, yb) in ((y1, -99.2), (-104.0, y0)):
        thin_partition(P.visual, P.collision, (x1, ya), (x1, yb), 0.0, CLEAR, "solid", solid_mat="int_ms_brick")
    P.merge(MP.wall_tv(1.4, 0.80, 1.7), x1 - PART_T / 2, -105.4, 0.0, 270.0)
    # pegboard tool wall on the brick (#53 #58)
    P.merge(MP.pegboard_wall(2.0, 1.4, 0.95), x1 - PART_T / 2, -98.1, 0.0, 270.0)
    # islands (#54): two butcher-block islands with bin shelves and Sayl chairs
    for y in (-99.6, -102.6):
        furnish(M, "F1", MP.butcher_island(2.4, 1.2, 0.92, stools=True), -74.0, y, 0.0, note="maker_island",
                margin=0.2)
    for (x, y) in ((-75.6, -100.9), (-72.9, -104.2), (-77.9, -103.0)):
        P.merge(MP.crochet_jellyfish(1.7 if x > -75 else 1.4), x, y, CLEAR, 0.0)
    M.notes.setdefault("photo_pass_2", []).append(
        "F1 makerspace: black-framed glass front on the north (the elevator lobby side, #39 #51 #69) with a 2.4 m "
        "door gap (real: one leaf), the neon inside the glass, brick east wall with a 4.8 m opening to the Commons, "
        "islands, pegboard, jellyfish (#50-#60)")


def chair_rail(V, poly, z=0.88, h=0.08, mat="int_ms_veneer", tint=(0.86, 0.66, 0.42), skip=()):
    """A wood chair rail round the inside of a rectangular room (L136 #47, #49): a strip 1 cm off each wall."""
    pts = ccw(poly)
    for a, b in edges(pts):
        L = math.dist(a, b)
        if L < 0.3:
            continue
        dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx, ny = -dy, dx                                      # inward (left of CCW)
        aa = (a[0] + nx * 0.012 + dx * 0.05, a[1] + ny * 0.012 + dy * 0.05)
        bb = (b[0] + nx * 0.012 - dx * 0.05, b[1] + ny * 0.012 - dy * 0.05)
        V.wall(bb, aa, z, z + h, mat, tint=tint, ao=1.0)


def conference_l136(M, P):
    """L136, the conference / meeting room (#47 2023, #49 2019; the 2014 visualization wall #48 is gone): two ceiling
    projectors and screens showing the UF slide on the west wall, a lectern with dual monitors, rows of maple
    training tables on grey T-legs with black Caper chairs facing the screens, a whiteboard wall, the wood chair rail,
    beige walls."""
    r = next((r for r in M.regions["F1"] if r["id"] == "L136"), None)
    if r is None:
        return
    x0, y0, x1, y1 = bbox(r["poly"])
    for y in (y0 + 2.9, y0 + 6.7):
        P.merge(MP.projection_screen(2.6, 1.5, 1.05), x0 + 0.02, y, 0.0, 90.0)
        P.merge(box_prop("projector", -0.25, -0.22, -0.32, 0.25, 0.22, -0.12, "int_ms_wall", col=False,
                         tint=(0.95, 0.95, 0.95)), x0 + 4.4, y, CLEAR, 90.0)
        P.merge(box_prop("projector_rod", -0.02, -0.02, -0.12, 0.02, 0.02, 0.0, "int_metal", col=False),
                x0 + 4.4, y, CLEAR, 0.0)
    P.merge(K.whiteboard(3.6, 1.2, 0.9), (x0 + x1) / 2 + 1.0, y0 + 0.02, 0.0, 0.0)
    chair_rail(P.visual, r["poly"])
    furnish(M, "F1", MP.lectern(), x0 + 1.2, y1 - 1.3, 90.0, room="L136", note="lectern", margin=0.1)
    for x in (x0 + 3.3, x0 + 5.7, x0 + 8.1):
        for y in (y0 + 1.6, y0 + 3.6, y0 + 5.9, y0 + 7.9):
            furnish(M, "F1", MP.training_table(1.83, 0.6, 0.74, chairs=2), x, y, 90.0, room="L136",
                    note="training_table", margin=0.08)


def dress_f2(M, P, z):
    """Floor 2, the entrance floor (#23-#35): security gates, the service-desk queue and the staff / tool-lending room
    behind the desk, the lounge under the copper soffit lantern (S-curved orange-leather banquettes round yellow
    ottomans, tub chairs, the Collection Highlights / New Books shelves), long maple benching with frosted dividers,
    round cafe tables, mobile whiteboards, the printers by the teal wall with the How-to-Print poster, the computer
    area with its compact shelving, white benching by the sci-fi stacks, the lobby's exhibit cases, Starbucks."""
    # entrance (#23): white arched security gates inside the vestibule doors, queue stanchions at the desk
    for x in (-69.0, -67.2, -65.4):
        P.merge(MP.security_gate(1.55, 0.62), x, -79.75, 0.0, 0.0)
    for x, y in ((-63.0, -93.2), (-61.6, -94.0), (-60.0, -94.0)):
        P.merge(MP.stanchion(), x, y, 0.0, 0.0)
    belt = K.Prop("belt", col_closed=True)
    for (a, b) in (((-63.0, -93.2), (-61.6, -94.0)), ((-61.6, -94.0), (-60.0, -94.0))):
        belt.visual.wall(a, b, 0.84, 0.90, "int_plastic", tint=MP.T_BLACK)
        belt.visual.wall(b, a, 0.84, 0.90, "int_plastic", tint=MP.T_BLACK)
    P.merge(belt, 0.0, 0.0, 0.0, 0.0)
    staff_area(M, P)
    # the lounge in the atrium court (#24 #25 #26): two orange-tan / charcoal banquettes in an S round yellow
    # ottomans, orange tub chairs, cherry end tables with pothos, the easel
    furnish(M, "F2", MP.banquette_arc(1.15, 0.62, 180.0, 360.0, MP.T_ORANGE_LEATHER, "int_ms_fab_dark"), -58.6,
            -104.0, 0.0, note="banquette", margin=0.05)
    dress(M, "F2", MP.round_ottoman(0.42, 0.42, MP.T_YELLOW_OTTOMAN), -58.6, -104.3, 0.0, note="ottoman")
    furnish(M, "F2", MP.banquette_arc(1.15, 0.62, 0.0, 180.0, MP.T_ORANGE_LEATHER, "int_ms_fab_dark"), -54.9,
            -104.6, 0.0, note="banquette", margin=0.05)
    dress(M, "F2", MP.round_ottoman(0.42, 0.42, MP.T_YELLOW_OTTOMAN), -54.9, -104.3, 0.0, note="ottoman")
    furnish(M, "F2", MP.tub_chair(MP.T_ORANGE_LEATHER), -53.6, -106.9, 300.0, note="tub_chair", margin=0.1)
    for (x, y) in ((-60.2, -106.6), (-52.6, -102.6)):
        tbl = box_prop("end_table", -0.22, -0.22, 0.0, 0.22, 0.22, 0.62, "int_ms_veneer", top="int_ms_veneer")
        tbl.merge(MP.potted_plant(0.6), 0.0, 0.0, 0.62)
        furnish(M, "F2", tbl, x, y, 0.0, note="end_table", margin=0.05)
    P.merge(MP.easel_sign(), -60.8, -101.2, 0.0, 90.0)
    # east floor (#27 #28 #29): round cafe tables by the windows, mobile whiteboards, the printers by the teal wall
    for (x, y) in ((-40.4, -97.2), (-40.4, -101.0), (-36.4, -99.2), (-36.6, -103.2)):
        furnish(M, "F2", MP.round_table(1.07, chairs=4, rot=0.2), x, y, 0.0, note="round_table")
    for (x, y, f) in ((-43.6, -98.8, 90.0), (-51.0, -98.6, 270.0), (-39.0, -104.6, 0.0)):
        furnish(M, "F2", MP.whiteboard_easel(1.3, 1.7), x, y, f, note="mobile_whiteboard", margin=0.1)
    poster = K.Prop("print_poster", col_closed=True)
    poster.visual.poly(K.front_quad(-0.65, 0.65, 0.006, 1.6, 2.22), "int_ms_print_poster", uvs=K.ONCE, ao=1.0)
    P.merge(poster, -42.6, -105.7 + PART_T / 2, 0.0, 0.0)       # over the layout's printer (#28)
    # NE hall: orange tub chairs, the hanging RESTROOMS signs toward the NE stair hall (#27 #33)
    for (x, y, f) in ((-50.2, -85.6, 0.0), (-48.4, -85.6, 0.0), (-45.6, -85.6, 0.0), (-43.8, -85.6, 0.0)):
        dress(M, "F2", MP.tub_chair(MP.T_ORANGE_LEATHER), x, y, f)
    P.merge(K.sign("int_ms_sign_rest", 1.4, 0.7, 3.4, mount="hanging", hang_top=CLEAR), -50.0, -89.0, 0.0, 180.0)
    P.merge(K.sign("int_ms_sign_rest", 1.4, 0.7, 3.4, mount="hanging", hang_top=CLEAR), -44.0, -104.0, 0.0, 0.0)
    # computer area (#30): beige compact shelving behind the white computer benches (layout computer row)
    dress(M, "F2", MP.compact_shelving(5, 4.4, 0.9, 2.2), -55.6, -113.6, 0.0)
    # by the science fiction stacks (#27): round tables and white benching
    for y in (-119.0, -122.6):
        furnish(M, "F2", MP.round_table(1.07, chairs=4, rot=0.5), -57.9, y, 0.0, note="round_table")
    for x in (-52.4, -48.6):
        furnish(M, "F2", MP.benching(4.8, 1.4, top="int_ms_wall", seats_per_side=5), x, -120.9, 90.0,
                note="white_benching")
    # Starbucks (#34 #35)
    starbucks_front(M, P)


def staff_area(M, P):
    """The staff / tool-lending room behind the service desk, as seen over the counter (#23): a white back wall
    (free-standing, with collision) carrying the MARSTON logo panel and a clock, chrome wire shelving with boxes and
    bins in front of it, red equipment cases on the floor, a work desk with a monitor, troffers; and the copper-
    veneer bulkhead running over the desk behind the yellow ring."""
    yb = -84.6
    thin_partition(P.visual, P.collision, (-63.4, yb), (-53.6, yb), 0.0, CLEAR, "solid",
                   doors=[(7.2, 8.6, DOOR_H)])
    P.merge(K.sign("int_ms_logo", 1.6, 0.8, 1.9, mount="wall"), -57.6, yb - PART_T / 2, 0.0, 180.0)
    clock = K.Prop("clock", col_closed=True)
    clock.visual.poly([(0.22 * math.cos(a), 0.012, 2.45 + 0.22 * math.sin(a)) for a in
                       [2 * math.pi * k / 8 for k in range(8)]][::-1], "int_ms_wall", tint=(1.0, 1.0, 1.0),
                      normal_hint=(0, 1, 0))
    clock.visual.poly([(0.25 * math.cos(a), 0.008, 2.45 + 0.25 * math.sin(a)) for a in
                       [2 * math.pi * k / 8 for k in range(8)]][::-1], "int_plastic", tint=MP.T_BLACK,
                      normal_hint=(0, 1, 0))
    P.merge(clock, -61.0, yb - PART_T / 2, 0.0, 180.0)
    # fix round 5: the third unit stood across the back wall's door (x -56.2 .. -54.8) and the fourth overhung its jamb
    for k, x in enumerate((-62.6, -61.2, -59.8, -54.2)):
        P.merge(MP.wire_shelving(1.2, 0.46, 1.85, seed=700 + k), x, yb - PART_T / 2 - 0.25, 0.0, 180.0)
    for k in range(4):
        P.merge(MP.tool_case(), -56.0 + k * 0.62, -86.4, 0.0, 0.0 if k % 2 else 10.0)
    # fix round 5: with collision (it stands where the staff room is reachable; it was walk-through)
    P.merge(box_prop("staff_desk", -1.0, -0.4, 0.0, 1.0, 0.4, 0.76, "int_plastic", top="int_ms_maple", col=True),
            -59.0, -86.6, 0.0, 0.0)
    P.merge(K.monitor(), -59.0, -86.8, 0.76, 180.0)
    # the copper bulkhead over the desk (#23 #24): veneer box on the ceiling along the counter's back
    P.merge(box_prop("bulkhead", -63.6, -90.9, CLEAR - 1.1, -52.2, -89.9, CLEAR, "int_ms_veneer", col=False),
            0.0, 0.0, 0.0, 0.0)


def starbucks_front(M, P):
    """The cafe as seen from the library (#34: the green round decal on the interior glass by the door) and inside
    (#35: vertical wood slats, a rust wall, the green Order Status screen, a quartz pickup counter)."""
    dec = K.Prop("decal", col_closed=True)
    dec.visual.poly(K.front_quad(-0.75, 0.75, 0.0, 1.2, 2.7), "int_ms_cafe_decal", uvs=K.ONCE)
    for (x, y, f) in ((-73.84, -102.4, 90.0), (-73.96, -102.4, 270.0), (-79.04, -92.6, 90.0), (-79.16, -92.6, 270.0)):
        P.merge(dec, x, y, 0.0, f)
    wall = K.Prop("menu_wall", col_closed=True)
    V = wall.visual
    V.box(-2.4, -0.10, 0.0, 2.4, 0.10, 3.0, "int_ms_slats", faces="+y-y+x-x+z")
    V.box(0.9, 0.101, 0.0, 2.4, 0.115, 3.0, "int_ms_wall", faces="+y", tint=(0.46, 0.20, 0.08))     # rust panel
    V.poly(K.front_quad(1.15, 2.15, 0.12, 1.45, 2.85), "int_ms_order", uvs=K.ONCE, glow=True)
    V.box(-2.4, -0.4, 3.0, 2.4, 0.4, 3.2, "int_ms_veneer", faces="+y-y+x-x-z")
    K.col_box(wall.collision, -2.4, -0.10, 0.0, 2.4, 0.10, 3.0, K.COL_NOCAM)
    P.merge(wall, -77.6, -94.3, 0.0, 180.0)


def dress_f3(M, P, z):
    """Floor 3 (#76-#83): the window bars along the east windows, classroom L308 (three wall displays, plum chairs),
    the data consultation room (big monitors), the wellness room, book carts."""
    for yc in (-89.9, -95.6, -104.6, -110.6, -116.6, -122.2):
        dress(M, "F3", MP.bar_table(3.6, 0.62, 1.05, 3), -34.15, yc, 90.0)
    # L308 (#78): three big displays on the west wall (on its inner face), rows of maple training tables on grey
    # T-legs with plum chairs on casters, all facing the displays (the chairs on the east side of each table)
    xin = -80.2 + PART_T / 2 + 0.01
    for y, w in ((-99.4, 1.45), (-102.2, 1.45), (-105.3, 1.95)):
        P.merge(MP.wall_tv(w, w * 0.56, 1.4), xin, y, 0.0, 90.0)
    for x in (-77.9, -75.3, -72.7):
        for y in (-99.0, -100.9, -103.6, -105.5):
            furnish(M, "F3", MP.training_table(1.83, 0.62, 0.74, chairs=2, chair_tint=MP.T_PLUM), x, y, 90.0,
                    room="L308", note="training_table", margin=0.0)
    # data consultation room (#77): a maple desk with two big monitors on the south wall (the core stair opens into
    # the room from the west, so the north side stays clear)
    d = MP.rect_table(1.2, 0.7, 0.74, chairs_per_side=1, seat_sides=(1,), legs="legs")
    d.merge(K.monitor(screen_w=0.7, screen_h=0.42), 0.0, -0.12, 0.74, 0.0)
    dress(M, "F3", d, -68.85, -87.55, 0.0, note="data_desk")
    # wellness room (#74 #75): glider chair, side table, rug, sink counter
    P.merge(MP.tub_chair((0.86, 0.74, 0.50), col=False), -79.2, -96.4, 0.0, 135.0)
    rug = K.Prop("rug", col_closed=True)
    rug.visual.poly([(-0.9, -0.6, 0.01), (0.9, -0.6, 0.01), (0.9, 0.6, 0.01), (-0.9, 0.6, 0.01)], "int_ms_carpet_f1",
                    tint=(0.6, 0.7, 1.15))
    P.merge(rug, -78.4, -95.8, 0.0, 0.0)
    P.merge(K.book_cart(seed=11), -56.0, -84.0, 0.0, 0.0)


def dress_f4(M, P, z):
    """Floor 4, the quiet floor (#84-#86 #97-#99): signs, kick stools, book carts (the stacks, carrels and computers
    are layout props)."""
    for x, y, f in ((-52.2, -78.6, 180.0), (-66.0, -96.4, 0.0), (-55.0, -116.4, 0.0)):
        P.merge(K.sign("int_sign_quiet", 1.6, 0.8, 3.2, mount="hanging", hang_top=CLEAR), x, y, 0.0, f)
    for x, y in ((-61.0, -86.0), (-56.4, -112.0), (-70.0, -104.0)):
        P.merge(K.kick_stool(), x, y, 0.0, 0.0)
    P.merge(K.book_cart(seed=21), -56.4, -80.4, 0.0, 0.0)
    P.merge(K.book_cart(seed=22), -70.1, -110.2, 0.0, 90.0)


def dress_f5(M, P, z):
    """Floor 5, the silent floor (#100-#104): a lounge group of the grey geometric cubes with blue cushions, a maple
    side block and a dark grey study pod in the north room's east strip (clear of the Shushers' patrols)."""
    for x, y, f in ((-55.0, -78.0, 90.0), (-80.0, -92.4, 0.0)):
        P.merge(K.sign("int_sign_quiet", 1.6, 0.8, 3.2, mount="hanging", hang_top=CLEAR), x, y, 0.0, f)
    for y in (-81.0, -83.6):
        dress(M, "F5", MP.lounge_cube(), -53.5, y, 270.0)
    dress(M, "F5", MP.side_table_block(0.55, 0.42), -53.5, -82.3, 0.0)
    dress(M, "F5", MP.study_pod(1.5, 1.2, 1.40), -53.4, -87.4, 270.0)


def keepout_points(M):
    """{fid: [(x, y, r)]}: spots free-standing dressing keeps its collision clear of: every planned coin (formations
    point by point), heart, 1-up and Goomba, the kiosks and their punch spots, every door and stair-hall door, the
    spawn / act starts, the F5 textbooks, star spots and the Shushers' patrol lines."""
    out = {f: [] for f in FLOORS}

    def fl(zz):
        for f in FLOORS:
            if abs(zz - Z[f]) < 1.0:
                return f
        return None
    for it in M.pickups:
        k, (x, y, zz) = it["kind"], it["pos"]
        f = fl(zz)
        if f is None:
            continue
        if k == "coin_line":
            a = math.radians(it.get("facing", 0.0))
            for i in range(5):
                out[f].append((x + math.sin(a) * 1.6 * (i - 2), y + math.cos(a) * 1.6 * (i - 2), 0.8))
        elif k == "coin_ring":
            out[f].append((x, y, 0.8))
            for i in range(8):
                out[f].append((x + 3.0 * math.sin(i * math.pi / 4), y + 3.0 * math.cos(i * math.pi / 4), 0.8))
        elif k == "goomba":
            out[f].append((x, y, 1.6))
        else:
            out[f].append((x, y, 0.9))
    kio = M.layout["missions"]["design_act3_group_study_room_booking"]["kiosks"]
    stand = {"K1": (0.0, 2.2), "K2": (0.0, -2.2), "K3": (-2.2, 0.0), "K4": (2.2, 0.0)}
    for kid, k in kio.items():
        x, y = k["pos_m"]
        out[k["floor"]] += [(x, y, 0.9), (x + stand[kid][0], y + stand[kid][1], 1.1)]
    out["F4"] += [(-45.5, -105.0, 0.9), (-47.7, -105.0, 1.1)]
    for fid in FLOORS:
        for d in M.doors[fid]:
            c = d["centre"]
            f = math.radians(d["facing"])
            out[fid] += [(c[0], c[1], d["width"] / 2 + 0.6), (c[0] + math.sin(f) * 1.2, c[1] + math.cos(f) * 1.2, 1.2)]
        out[fid] += [(-51.0, -80.2, 1.6), (-68.4, -85.2, 1.6), (-75.25, -91.8, 1.3), (-72.15, -91.8, 1.3)]
    out["F2"] += [(-67.5, -83.8, 1.6), (-67.5, -86.0, 1.3), (-63.25, -94.0, 1.6), (-67.2, -79.6, 1.4)]
    for b in M.layout["missions"]["design_act2_quiet_floor"].get("shusher_patrols", []):
        pts = b["loop_m"]
        for (ax, ay), (bx, by) in zip(pts, pts[1:] + pts[:1]):
            n = max(1, int(math.dist((ax, ay), (bx, by)) // 0.8))
            for i in range(n + 1):
                out["F5"].append((ax + (bx - ax) * i / n, ay + (by - ay) * i / n, 1.0))
    out["F5"] += [(-54.0, -77.5, 1.4), (-87.2, -99.0, 1.2), (-62.5, -73.0, 1.0), (-55.0, -91.6, 1.0),
                  (-73.75, -91.8, 1.0), (-78.75, -104.5, 1.0), (-47.0, -100.0, 1.0)]
    out["F1"] += [(-35.5, -121.9, 1.0), (-40.0, -112.0, 1.2)]
    return out


def place_dressing(M):
    """Place the queued free-standing furniture (dress()) as one kit item per floor, skipping any piece whose
    collision (0.05-2.4 m above its floor) comes within a keep-out circle (keepout_points)."""
    keep = keepout_points(M)
    groups = {}
    for it in M.dressing:
        fid = it["floor"]
        pl = it["prop"].placed(it["pos"][0], it["pos"][1], 0.0, it["facing"])
        bad = None
        for poly in pl.collision.polys:
            zs = [p[2] for p in poly.pts]
            if max(zs) < 0.05 or min(zs) > 2.4:
                continue
            x0, y0 = min(p[0] for p in poly.pts), min(p[1] for p in poly.pts)
            x1, y1 = max(p[0] for p in poly.pts), max(p[1] for p in poly.pts)
            for (kx, ky, kr) in keep[fid]:
                dx = max(x0 - kx, 0.0, kx - x1)
                dy = max(y0 - ky, 0.0, ky - y1)
                if dx * dx + dy * dy < kr * kr:
                    bad = (kx, ky)
                    break
            if bad:
                break
        if not bad and (not M.inside(fid, *it["pos"]) and not (fid == "F2" and in_rect(it["pos"], PORCH))):
            bad = ("outside",)
        if not bad and M.in_tower(fid, *it["pos"], 0.3):
            bad = ("stair hall / core",)
        if bad:
            M.notes.setdefault("dressing_skipped", []).append(f"{fid} {it['note']} at {tuple(round(v, 2) for v in it['pos'])}"
                                                             f" (near {tuple(round(v, 2) if isinstance(v, float) else v for v in bad)})")
            continue
        D = groups.setdefault(fid, K.Prop(f"dress_{fid}", col_closed=False))
        D.visual.polys.extend(pl.visual.polys)
        D.collision.polys.extend(pl.collision.polys)
        D.lights.extend(pl.lights)
    for fid, D in groups.items():
        M.add(D, 0.0, 0.0, Z[fid], 0.0, tag=f"dress_{fid}", group=fid)
    M.stats["dressing"] = {f: sum(1 for it in M.dressing if it["floor"] == f) for f in FLOORS}
    M.stats["dressing_skipped"] = len(M.notes.get("dressing_skipped", []))


# ================================================================== roof
def build_roof(M):
    z = Z["ROOF"]
    P = K.Prop("roof", col_closed=False)
    V, C = P.visual, P.collision
    o5 = M.outlines["F5"]
    holes = [NE_RECT, SW_RECT, CORE_RECT, ATRIUM]

    def top_fn(x, y):
        return ("roof_gravel", None)

    def bot_fn(x, y):
        if in_coffer(M, "F5", x, y):
            return None
        return None if M.solid_at("F5", x, y) else ("int_ms_tile", None)
    slab(V, C, [o5], holes, top_fn, lambda x, y: True, bot_fn, lambda x, y: True, [ATRIUM], lines=coffer_lines(M, "F5"))
    # parapet + the F5 facade continues to the parapet top
    for a, b in edges(o5):
        Ls = math.dist(a, b)
        dx, dy = (b[0] - a[0]) / Ls, (b[1] - a[1]) / Ls
        ix, iy = -dy, dx
        keep, run, s = [], None, 0.0
        while s <= Ls + 1e-6:
            pi = (a[0] + dx * s + ix * 0.25, a[1] + dy * s + iy * 0.25)
            ok = not M.in_tower("F5", *pi) and not in_rect(pi, ATRIUM)
            if ok and run is None:
                run = s
            if not ok and run is not None:
                keep.append((run, s))
                run = None
            s += 0.05
        if run is not None:
            keep.append((run, Ls))
        for k0, k1 in keep:
            if k1 - k0 < 0.1:
                continue
            pa = (a[0] + dx * k0, a[1] + dy * k0)
            pb = (a[0] + dx * k1, a[1] + dy * k1)
            thick_wall(V, C, pa, pb, 0.0, ROOF_PARAPET_H, t=WALL_T, in_mat="brick_red",
                       out_mat=lambda s_, z_: "brick_red", col_in=True, col_out=False, base=False, ceil=99.0)
            qa = (pa[0] - ix * WALL_T, pa[1] - iy * WALL_T)
            qb = (pb[0] - ix * WALL_T, pb[1] - iy * WALL_T)
            V.poly([(*pa, ROOF_PARAPET_H), (*pb, ROOF_PARAPET_H), (*qb, ROOF_PARAPET_H), (*qa, ROOF_PARAPET_H)],
                   "concrete", normal_hint=(0, 0, 1))
            C.poly([(*pa, ROOF_PARAPET_H), (*pb, ROOF_PARAPET_H), (*qb, ROOF_PARAPET_H), (*qa, ROOF_PARAPET_H)],
                   K.COL, normal_hint=(0, 0, 1))
    # skylight: a hipped glass roof over the atrium (walkable, 24 deg)
    x0, y0, x1, y1 = ATRIUM
    cx = (x0 + x1) / 2
    hw = (x1 - x0) / 2
    r0, r1 = y0 + hw, y1 - hw
    H = SKYLIGHT_RIDGE
    faces = [[(x0, y0, 0), (cx, r0, H), (cx, r1, H), (x0, y1, 0)],          # west
             [(x1, y1, 0), (cx, r1, H), (cx, r0, H), (x1, y0, 0)],          # east
             [(x1, y0, 0), (cx, r0, H), (x0, y0, 0)],                       # south
             [(x0, y1, 0), (cx, r1, H), (x1, y1, 0)]]                       # north
    for f in faces:
        n = K.newell(f)
        if n[2] < 0:
            f.reverse()
        V.poly(f, "int_glass", ao=1.0)
        C.poly(f, K.COL)
    # ribs
    for t in (0.25, 0.5, 0.75):
        y = y0 + (y1 - y0) * t
        zr = H if r0 <= y <= r1 else H * (1 - abs(y - (r0 if y < r0 else r1)) / hw)
        for xa, xb in ((x0, cx), (cx, x1)):
            V.box(min(xa, xb), y - 0.04, 0.0, max(xa, xb), y + 0.04, 0.0 + 0.06, "int_metal", faces="+z")
    V.box(cx - 0.06, r0, H - 0.05, cx + 0.06, r1, H + 0.06, "int_metal", faces="+x-x+z")
    # core penthouse (elevator machine room) 24 -> 27, walkable
    cx0, cy0, cx1, cy1 = CORE_RECT
    P.merge(box_prop("penthouse", cx0, cy0, 0.0, cx1, cy1, 3.0, "brick_red", top="concrete", cam=True), 0, 0, 0, 0)
    # rooftop plant: AC units / ducts stepping up 1.4 m at a time to the two towers (24 -> 28.2 -> 29.7 / 30.2)
    steps = {"ne": [(-58.8, -74.2, -56.8, -71.0, 1.4), (-56.8, -74.2, -54.8, -71.0, 2.8), (-54.8, -74.2, -52.95, -71.0, 4.2)],
             "sw": [(-86.4, -107.45, -84.4, -104.4, 1.4), (-84.4, -107.45, -82.4, -104.4, 2.8),
                    (-82.4, -107.45, -80.4, -104.4, 4.2)]}
    for tw, boxes in steps.items():
        for k, (ax0, ay0, ax1, ay1, h) in enumerate(boxes):
            P.merge(box_prop("ac_unit", ax0, ay0, 0.0, ax1, ay1, h, "metal_gray", top="int_metal", cam=True), 0, 0, 0, 0)
            M.anchor(f"roof_{tw}_step{k + 1}", (ax0 + ax1) / 2, (ay0 + ay1) / 2, z + h, 0.0, floor="ROOF")
    M.add(P, 0.0, 0.0, z, 0.0, tag="roof", group="roof")


# ================================================================== stair halls, core
def tower_band_walls(M, V, C, edge_list, z0, z1, level, doors, in_mat="int_ms_wall", tint=None):
    """Walls of a tower (stair hall / core) for one level band (map x, y; local z of the band).
    The outer face is brick where the outside is outdoors at that level, drywall where it is the floor,
    none underground. doors: [((ax, ay), (bx, by), head)]. edge_list: the CCW edges (a, b) to build."""
    for a, b in edge_list:
        Ls = math.dist(a, b)
        dx, dy = (b[0] - a[0]) / Ls, (b[1] - a[1]) / Ls
        ox, oy = dy, -dx
        ops = []
        for (pa, pb, head) in doors:
            if seg_point_dist(pa, a, b) > 0.1 or seg_point_dist(pb, a, b) > 0.1:
                continue
            s0 = (pa[0] - a[0]) * dx + (pa[1] - a[1]) * dy
            s1 = (pb[0] - a[0]) * dx + (pb[1] - a[1]) * dy
            s0, s1 = sorted((s0, s1))
            ops.append({"s0": s0, "s1": s1, "z0": z0, "z1": z0 + head, "kind": "door"})

        def outer(s, zz, a=a, dx=dx, dy=dy, ox=ox, oy=oy):
            # fix round 2: F1 faces too, wherever the basement floor is outside the tower (they were left
            # out on F1, so the stair halls and the core were see-through from the Commons and the North Lab
            # behind full-height collision); only the earth side of a basement wall stays faceless
            px, py = a[0] + dx * s + ox * 0.7, a[1] + dy * s + oy * 0.7
            if level in FLOORS and M.inside(level, px, py):
                if M.in_tower(level, px, py):
                    return None
                return "int_ms_brick"
            if level == "F1":
                return None
            return "brick_red"

        def need_out(s, a=a, dx=dx, dy=dy, ox=ox, oy=oy):
            px, py = a[0] + dx * s + ox * 0.7, a[1] + dy * s + oy * 0.7
            if level == "F1":
                return M.inside("F1", px, py)
            if level in FLOORS:
                if M.inside(level, px, py):
                    return not M.in_tower(level, px, py)
                return (level == "F2" and in_rect((px, py), PORCH)) or level in ("F4", "F5", "ROOF")
            return True
        # fix round 5: decided along the wall (three samples missed the 2.5 m of the F2 cafe's south wall at the SW
        # hall's north-east end, so its brick face had no collision and a grounded player walked through it)
        thick_wall(V, C, a, b, z0, z1, t=WALL_T, in_mat=in_mat, out_mat=outer, openings=ops, col_in=True,
                   col_out=need_out, in_tint=tint, ceil=z1)


STAIR_EDGE_INSET = 0.02                 # fix round 5: landing / floor-box edges behind the stair flights' top lips


def floor_box(V, C, rect, z, mat="int_stone", thickness=0.3, tint=None, col=True, bottom=True, edge=True,
              edge_inset=0.0):
    """edge_inset (fix round 5, Marston's stair halls): the edge faces set back into the box, so a stair flight's top
    lip on the same line covers them instead of z-fighting with them."""
    x0, y0, x1, y1 = rect
    V.poly([(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)], mat, ao=1.0, tint=tint)
    if bottom:
        V.poly([(x0, y0, z - thickness), (x0, y1, z - thickness), (x1, y1, z - thickness), (x1, y0, z - thickness)],
               "int_ceiling", ao=0.9)
    if edge:
        e = edge_inset
        for a, b in edges([(x0 + e, y0 + e), (x1 - e, y0 + e), (x1 - e, y1 - e), (x0 + e, y1 - e)]):
            V.wall(a, b, z - thickness, z, "int_drywall", ao=0.9)
    if col:
        K.col_box(C, x0, y0, z - thickness, x1, y1, z, K.COL, bottom=bottom)


def poly_slab(V, C, poly, z, thickness=0.25, top="int_stair", tint=None, edge_inset=0.0):
    """A landing / platform slab over a (convex or rectilinear) polygon, top at z. edge_inset: as floor_box."""
    poly = ccw(poly)
    V.poly([(x, y, z) for x, y in poly], top, ao=1.0, tint=tint)
    V.poly([(x, y, z - thickness) for x, y in reversed(poly)], "int_ceiling", ao=0.9)
    for a, b in edges(offset_poly(poly, -edge_inset) if edge_inset else poly):
        V.wall(a, b, z - thickness, z, "int_drywall", ao=0.9)
    K.col_prism(C, poly, z - thickness, z, K.COL, bottom=True)


def build_ne_hall(M):
    """NE stair hall (tower): F1 -> roof landing (z 24), switchbacks of 2 x 3 m flights per storey."""
    P = K.Prop("ne_hall", col_closed=False)
    V, C = P.visual, P.collision
    x0, y0, x1, y1 = NE_RECT
    lane, gap = 6.15, 0.6
    xm = (x0 + x1) / 2
    first = -76.3
    doors_by = {lvl: [((-52.3, -79.0), (-49.7, -79.0), DOOR_H)] for lvl in ("F1", "F2", "F3", "F4")}
    doors_by["F5"] = [((-52.6, -78.7), (-52.6, -76.3), DOOR_H), ((-46.0, -79.0), (-43.6, -79.0), DOOR_H)]
    doors_by["ROOF"] = [((-52.6, -78.7), (-52.6, -76.3), DOOR_H)]
    for lvl in ("F1", "F2", "F3", "F4", "F5", "ROOF"):
        zb = Z[lvl]
        top = zb + STOREY if lvl != "ROOF" else TOWER_TOP - TOWER_ROOF_T
        tower_band_walls(M, V, C, edges(ccw(NE_HALL)), zb, top, lvl, doors_by[lvl], tint=wall_tint(lvl))
        if lvl == "F1":
            floor_box(V, C, NE_RECT, zb, "int_stone", bottom=False, edge=False)
        else:
            floor_box(V, C, (x0, y0, x1, first), zb, "int_stair", edge_inset=STAIR_EDGE_INSET)
        if lvl != "ROOF":
            sb = K.switchback_stair(STOREY, lane, gap, landing_depth=1e-7, solid_first=(lvl == "F1"))
            P.merge(sb, xm, first, zb, 0.0)
            y_turn = first + sb.info["hole"][3]
            poly_slab(V, C, clip_rect(ccw(NE_HALL), x0, y_turn, x1, y1), zb + STOREY / 2, edge_inset=STAIR_EDGE_INSET)
            # floor number on the landing wall
            P.merge(K.floor_sign(str(FLOORS.index(lvl) + 1), 0.7, 2.2), -45.0, -78.98, zb, 0.0)
            P.merge(K.ceiling_light(radius=8.0, strength=0.4), xm, -77.6, zb + 5.3, 0.0)
            P.merge(K.ceiling_light(radius=8.0, strength=0.35), xm, -69.9, zb + 3.0 + 5.3, 90.0)
            M.anchor(f"ne_stair_{lvl}_landing", xm - 3.1, -77.6, zb, 180.0, floor=lvl)
            M.anchor(f"ne_stair_{lvl}_turn", xm, -69.9, zb + 3.0, 0.0, floor=lvl)
    M.anchor("ne_stair_ROOF_landing", xm - 3.1, -77.6, Z["ROOF"], 270.0, floor="ROOF")
    # tower top
    tz = TOWER_TOP
    hall = ccw(NE_HALL)
    out = offset_poly(hall, WALL_T)
    V.poly([(x, y, tz - TOWER_ROOF_T) for x, y in reversed(hall)], "int_ms_tile", ao=0.9)
    C.poly([(x, y, tz - TOWER_ROOF_T) for x, y in reversed(hall)], K.COL)
    for c, d in edges(out):
        V.wall(c, d, tz - TOWER_ROOF_T, tz, "dark_trim", ao=1.0)
        C.wall(c, d, tz - TOWER_ROOF_T, tz, K.COL)
    V.poly([(x, y, tz) for x, y in out], "roof_gravel", ao=1.0)
    C.poly([(x, y, tz) for x, y in out], K.COL)
    M.anchor("ne_tower_top", xm, -73.0, tz, 0.0, floor="ROOF")
    M.add(P, 0.0, 0.0, 0.0, 0.0, tag="ne_hall", group="towers")


def build_sw_hall(M):
    """SW stair hall (tower): F1 -> F5, flights east-west; a solid brick tower above F5 to 29.7 m."""
    P = K.Prop("sw_hall", col_closed=False)
    V, C = P.visual, P.collision
    x0, y0, x1, y1 = SW_RECT
    lane, gap = 5.25, 0.55
    ym = (y0 + y1) / 2
    first = -82.2
    doors_by = {"F1": [((-80.2, -110.4), (-80.2, -112.8), DOOR_H)],
                "F2": [((-79.46, -108.4), (-79.46, -110.6), DOOR_H)],
                "F3": [((-79.46, -109.6), (-79.46, -112.0), DOOR_H)],
                "F4": [((-82.0, -107.8), (-80.0, -107.8), DOOR_H)],
                "F5": [((-82.0, -107.8), (-80.0, -107.8), DOOR_H)]}
    for lvl in FLOORS:
        zb = Z[lvl]
        rect = SW_RECT_F1 if lvl == "F1" else SW_RECT
        tower_band_walls(M, V, C, edges(rect_poly(rect)), zb, zb + (STOREY if lvl != "F5" else CLEAR), lvl,
                         doors_by[lvl], tint=wall_tint(lvl))
        if lvl == "F1":
            floor_box(V, C, SW_RECT_F1, zb, "int_stone", bottom=False, edge=False)
        else:
            floor_box(V, C, (first, y0, x1, y1), zb, "int_stair", edge_inset=STAIR_EDGE_INSET)
        if lvl != "F5":
            sb = K.switchback_stair(STOREY, lane, gap, landing_depth=1e-7, solid_first=(lvl == "F1"))
            P.merge(sb, first, ym, zb, 270.0)
            x_turn = first - sb.info["hole"][3]
            poly_slab(V, C, rect_poly((x0, y0, x_turn, y1)), zb + STOREY / 2, edge_inset=STAIR_EDGE_INSET)
            P.merge(K.ceiling_light(radius=8.0, strength=0.35), -87.9 - 1.0, ym, zb + 3.0 + 5.3, 0.0)
            M.anchor(f"sw_stair_{lvl}_turn", -89.0, ym, zb + 3.0, 270.0, floor=lvl)
        P.merge(K.floor_sign(str(FLOORS.index(lvl) + 1), 0.7, 2.2), -82.0 + 0.6, y0 + 0.02, zb, 0.0)
        P.merge(K.ceiling_light(radius=8.0, strength=0.4), -81.0, ym, zb + 5.3, 90.0)
        M.anchor(f"sw_stair_{lvl}_landing", -81.0, ym, zb, 90.0, floor=lvl)
    # fix round 2: over the F1 strip between the basement hall's east wall (x -80.2, 0.3 thick) and the upper
    # halls' wall line (x -79.46) the F2 slab is cut by SW_RECT: close it with the basement's tile ceiling at the
    # F2 slab's underside (the F2 hall floor box above is thinner), so the Commons ceiling runs on to the hall wall
    sx0, sx1, sy0, sy1 = SW_RECT_F1[2] + WALL_T, SW_RECT[2], -115.9, SW_RECT[3]
    V.poly([(sx0, sy0, Z["F2"] - SLAB), (sx0, sy1, Z["F2"] - SLAB), (sx1, sy1, Z["F2"] - SLAB),
            (sx1, sy0, Z["F2"] - SLAB)], "int_ms_tile", ao=0.95)
    # ceiling of the hall at F5 + solid tower 24 -> 29.7
    floor_box(V, C, SW_RECT, Z["ROOF"], "roof_gravel", thickness=SLAB, col=True, bottom=True, edge=False)
    sw = rect_poly(SW_RECT)
    out = rect_poly((x0 - WALL_T, y0 - WALL_T, x1 + WALL_T, y1 + WALL_T))
    for (c, d) in edges(out):
        for za, zb2 in ((Z["ROOF"], 27.0), (27.0, TOWER_TOP)):
            V.wall(c, d, za, zb2, "brick_red", ao=1.0)
        V.wall(c, d, TOWER_TOP, TOWER_TOP + 0.5, "dark_trim", ao=1.0)
    K.col_box(C, x0 - WALL_T, y0 - WALL_T, Z["ROOF"], x1 + WALL_T, y1 + WALL_T, TOWER_TOP + 0.5, K.COL)
    V.poly([(x, y, TOWER_TOP + 0.5) for x, y in out], "roof_gravel", ao=1.0)
    M.anchor("sw_tower_top", (x0 + x1) / 2, ym, TOWER_TOP + 0.5, 0.0, floor="ROOF")
    del out
    M.add(P, 0.0, 0.0, 0.0, 0.0, tag="sw_hall", group="towers")
    del sw


def build_core(M):
    """West core: the steep secondary stair (north part), elevator 1 (OUT OF ORDER, doors open F2-F5:
    a wall-kick shaft from the F2 floor to the F5 ceiling), elevator 2 (closed), fillers."""
    P = K.Prop("core", col_closed=False)
    V, C = P.visual, P.collision
    x0, y0, x1, y1 = CORE_RECT
    sy0 = -88.0
    # walls around the stair part (north, west, east incl. the door) per level; the south side is the
    # elevator block (its own walls)
    stair_poly = [(x0, sy0), (x1, sy0), (x1, y1), (x0, y1)]
    for lvl in FLOORS:
        zb = Z[lvl]
        top = zb + (STOREY if lvl != "F5" else CLEAR)
        doors = [((-69.7, -86.4), (-69.7, -84.0), DOOR_H)]
        # build only the north, east and west edges of the stair part (the south edge is the elevator wall)
        tower_band_walls(M, V, C, [e for e in edges(ccw(stair_poly)) if not (abs(e[0][1] - sy0) < 1e-6 and
                                                                              abs(e[1][1] - sy0) < 1e-6)],
                         zb, top, lvl, doors, tint=wall_tint(lvl))
        # the stair-side face of the elevator block
        thick_wall(V, C, (x0, sy0), (x1, sy0), zb, top, t=0.2, in_mat="int_ms_wall", out_mat=None, col_in=True,
                   ceil=top)
        if lvl == "F1":
            floor_box(V, C, (x0, sy0, x1, y1), zb, "int_stone", bottom=False, edge=False)
        else:
            floor_box(V, C, (-71.9, sy0, x1, y1), zb, "int_stair", edge_inset=STAIR_EDGE_INSET)
        if lvl != "F5":
            sb = K.switchback_stair(STOREY, 2.2, 0.4, landing_depth=1e-7, max_deg=35.0, solid_first=(lvl == "F1"))
            P.merge(sb, -71.9, (sy0 + y1) / 2, zb, 270.0)
            poly_slab(V, C, rect_poly((x0, sy0, -71.9 - sb.info["hole"][3], y1)), zb + STOREY / 2,
                      edge_inset=STAIR_EDGE_INSET)
        P.merge(K.ceiling_light(radius=6.0, strength=0.38), -70.8, -85.6, zb + (5.3 if lvl != "F5" else 5.3), 0.0)
        M.anchor(f"core_stair_{lvl}_landing", -70.8, -85.6, zb, 90.0, floor=lvl)
    floor_box(V, C, (x0, sy0, x1, y1), Z["ROOF"] - 0.0, "roof_gravel", thickness=SLAB, col=True, bottom=True,
              edge=False)
    # elevators (fronts at y -90.6, facing south)
    ew = ELEV1_X[1] - ELEV1_X[0]
    e1 = K.elevator(floors=(0.0, 6.0, 12.0, 18.0), width=ew, depth=2.4, door_w=1.7, door_h=2.5,
                    top=Z["F5"] + CLEAR, open_floors=(0, 1, 2, 3), out_of_order=(0, 1, 2, 3),
                    labels=["2", "3", "4", "5"], hollow=True, front_mat="int_ms_brick", wall_mat="int_ms_wall")
    P.merge(e1, (ELEV1_X[0] + ELEV1_X[1]) / 2, ELEV_Y[0], 0.0, 180.0)
    e2 = K.elevator(floors=(-6.0, 0.0, 6.0, 12.0, 18.0), width=ELEV2_X[1] - ELEV2_X[0], depth=2.4,
                    top=Z["F5"] + CLEAR, out_of_order=(), hollow=False, front_mat="int_ms_brick",
                    wall_mat="int_ms_wall")
    P.merge(e2, (ELEV2_X[0] + ELEV2_X[1]) / 2, ELEV_Y[0], 0.0, 180.0)
    # elevator 1 below F2: a closed door on F1 in a filler block
    P.merge(box_prop("elev1_f1", ELEV1_X[0], ELEV_Y[0], Z["F1"], ELEV1_X[1], ELEV_Y[1], 0.0, "int_ms_brick", cam=True),
            0, 0, 0, 0)
    ex = (ELEV1_X[0] + ELEV1_X[1]) / 2
    P.visual.poly([(ex + 0.75, ELEV_Y[0] - 0.02, Z["F1"]), (ex - 0.75, ELEV_Y[0] - 0.02, Z["F1"]),
                   (ex - 0.75, ELEV_Y[0] - 0.02, Z["F1"] + 2.4), (ex + 0.75, ELEV_Y[0] - 0.02, Z["F1"] + 2.4)],
                  "int_elevator", uvs=[(1, 0), (0, 0), (0, 1), (1, 1)], ao=1.0, normal_hint=(0, -1, 0))
    # fillers between / beside the elevators (solid, full height)
    for fx0, fx1 in ((x0, ELEV1_X[0]), (ELEV1_X[1], ELEV2_X[0]), (ELEV2_X[1], x1)):
        # the elevator wall is red brick with light mortar (#69 F1; the core brick of #37), on every floor.
        # fix round 5: the fillers stop at the elevator block's back (y -88.2) instead of running into the stair side's
        # painted 0.2 m wall: their brick back face lay exactly on the paint (z-fighting over 78 m2, F1-F5) and their
        # collision back face doubled the wall's
        P.merge(box_prop("core_filler", fx0, ELEV_Y[0], Z["F1"], fx1, ELEV_Y[1], Z["ROOF"], "int_ms_brick",
                         col=False, faces="+x-x-y"), 0, 0, 0, 0)
        C.box(fx0, ELEV_Y[0], Z["F1"], fx1, ELEV_Y[1], Z["ROOF"], K.COL, faces="+x-x-y")
    # fix round 5: the inner face of elevator 1's front wall (the kit draws its lobby face only), so the wall-kick
    # shaft is closed round its open doors when seen from inside (it showed the lobby through the wall)
    ecx, ehw, ehd, ewt = (ELEV1_X[0] + ELEV1_X[1]) / 2, (ELEV1_X[1] - ELEV1_X[0]) / 2, 1.7 / 2, 0.20
    yi = ELEV_Y[0] + ewt
    shaft_top = Z["F5"] + CLEAR - 0.3
    for k, zf in enumerate((0.0, 6.0, 12.0, 18.0)):
        z1f = min(zf + STOREY, shaft_top)
        for xa, xb_, za, zb_ in ((ecx + ehw - ewt, ecx + ehd, zf, z1f), (ecx - ehd, ecx - ehw + ewt, zf, z1f),
                                 (ecx + ehd, ecx - ehd, zf + 2.5, z1f)):
            V.wall((xa, yi), (xb_, yi), za, zb_, "int_metal", ao=0.8, tint=(0.42, 0.42, 0.45))
    # fix round 5: the roof deck over the elevator block (y -90.6 .. -88.0); the fillers' tops stood at the deck, the
    # elevators' at the F5 ceiling (0.6 m pits) and a 0.2 m crack ran along the stair side
    zr = Z["ROOF"]
    cap = [(x0, ELEV_Y[0], zr), (x1, ELEV_Y[0], zr), (x1, sy0, zr), (x0, sy0, zr)]
    V.poly(cap, "roof_gravel", ao=1.0, normal_hint=(0, 0, 1))
    C.poly(cap, K.COL, normal_hint=(0, 0, 1))
    for lvl in FLOORS:
        zb = Z[lvl]
        xs = (ELEV1_X[0] + ELEV1_X[1]) / 2
        M.anchor(f"elevator1_door_{lvl}", xs, ELEV_Y[0] - 0.6, zb, 180.0, floor=lvl, open=lvl != "F1")
    M.anchor("elevator1_shaft_bottom", (ELEV1_X[0] + ELEV1_X[1]) / 2, (ELEV_Y[0] + ELEV_Y[1]) / 2, 0.0, 0.0,
             floor="F2", shaft_inner_m=[round(ew - 0.4, 2), 2.0], top_z=Z["F5"] + CLEAR - 0.3)
    M.anchor("elevator2_door_F2", (ELEV2_X[0] + ELEV2_X[1]) / 2, ELEV_Y[0] - 0.6, 0.0, 180.0, floor="F2")
    for lvl in ("F2", "F3", "F4", "F5"):
        P.merge(K.sign("int_sign_out_of_order", 0.8, 0.4, 1.0, mount="post"), ELEV1_X[0] - 0.35, ELEV_Y[0] - 0.7,
                Z[lvl], 180.0)
    # freight elevator (closed shaft, doors on the north face)
    fr = FREIGHT_RECT
    fe = K.elevator(floors=(-6.0, 0.0, 6.0, 12.0), width=fr[2] - fr[0], depth=fr[3] - fr[1], top=Z["F4"] + CLEAR,
                    out_of_order=(), hollow=False, front_mat="int_ms_brick", wall_mat="int_ms_wall")
    P.merge(fe, (fr[0] + fr[2]) / 2, fr[3], 0.0, 0.0)
    M.add(P, 0.0, 0.0, 0.0, 0.0, tag="core", group="towers")


# ================================================================== atrium
def build_atrium(M):
    P = K.Prop("atrium", col_closed=False)
    V, C = P.visual, P.collision
    x0, y0, x1, y1 = ATRIUM
    # grand stair F2 -> F3 on the west edge (rising south), last nosing at the F3 landing's north edge
    w = GRAND_STAIR_X[1] - GRAND_STAIR_X[0]
    fl = K.stair_flight(STOREY, w, lip=0.35, lip_visual=False, solid=True, rails=("l", "r"),
                        rail_kw={"infill": "glass", "col_t": THIN_COL_T})
    run = fl.info["top_nosing_y"]
    y_first = STAIR_LANDING[3] + run
    P.merge(fl, (GRAND_STAIR_X[0] + GRAND_STAIR_X[1]) / 2, y_first, 0.0, 180.0)
    # fix round 5: the flight's collision lip runs 0.35 m on under the landing at full height, so its back stood 0.35 m
    # in front of the visible end: under the landing (F2) that was an invisible wall. Its faces now show there
    yl, ye = STAIR_LANDING[3] - 0.35, STAIR_LANDING[3]
    zt_ = Z["F3"] - SLAB
    V.wall((GRAND_STAIR_X[0], yl), (GRAND_STAIR_X[1], yl), 0.0, zt_, "int_drywall", ao=[0.8, 0.8, 1.0, 1.0])
    V.wall((GRAND_STAIR_X[1], yl), (GRAND_STAIR_X[1], ye), 0.0, zt_, "int_drywall", ao=0.9)
    V.wall((GRAND_STAIR_X[0], ye), (GRAND_STAIR_X[0], yl), 0.0, zt_, "int_drywall", ao=0.9)
    M.anchor("grand_stair_bottom", (GRAND_STAIR_X[0] + GRAND_STAIR_X[1]) / 2, y_first + 1.0, 0.0, 180.0, floor="F2")
    M.anchor("grand_stair_top", (GRAND_STAIR_X[0] + GRAND_STAIR_X[1]) / 2, STAIR_LANDING[3] - 1.2, Z["F3"], 180.0,
             floor="F3")
    M.notes["grand_stair"] = {"first_riser_y": round(y_first, 2), "run_m": round(run, 2),
                              "ramp_deg": round(fl.info["ramp_deg"], 1), "risers": fl.info["risers"]}
    # pillars (the two free module columns), F2 floor -> skylight: white, a cap band under every floor's ceiling
    # (copper veneer at F2, terracotta above: the columns of #24 #76 #100)
    for (px, py) in ATRIUM_PILLARS:
        pv = K.Prop("pillar", col_closed=True)
        r = 0.4
        pts = [(-r, -r), (r, -r), (r, r), (-r, r)]
        pv.visual.prism(pts, 0.0, 0.1, "int_plastic")
        zc = 0.1
        for lvl in ("F2", "F3", "F4", "F5"):
            top = Z[lvl] + CLEAR
            mat, tint = COLUMN_CAP[lvl]
            pv.visual.prism(pts, zc, top - COLUMN_CAP_H, "int_ms_wall", tint=(1.0, 1.0, 0.99))
            pv.visual.prism([(x * 1.03, y * 1.03) for x, y in pts], top - COLUMN_CAP_H, top, mat, tint=tint, ao=1.0)
            pv.visual.prism(pts, top, Z[lvl] + STOREY, "int_ms_wall", tint=(0.92, 0.92, 0.92))
            zc = Z[lvl] + STOREY
        K.col_box(pv.collision, -r, -r, 0.0, r, r, Z["ROOF"], K.COL)
        P.merge(pv, px, py, 0.0, 0.0)
    # the copper-veneer bulkhead round the opening in the F3 slab, seen from the F2 lounge, green LED downlights in
    # its underside (#24 #25 #26; read as the base of the real two-storey atrium), and the square lantern
    zb, zt = Z["F2"] + CLEAR - 0.70, Z["F2"] + CLEAR
    w = 0.9
    strips = [(x0 - w, y1, x1 + w, y1 + w), (x1, y0 - w, x1 + w, y1), (STAIR_LANDING[2], y0 - w, x1, y0),
              (x0 - w, STAIR_LANDING[3], x0, y1)]
    for (a0, b0, a1, b1) in strips:
        P.visual.box(a0, b0, zb, a1, b1, zt, "int_ms_veneer", faces="+x-x+y-y", ao=1.0)
        P.visual.poly([(a0, b0, zb), (a0, b1, zb), (a1, b1, zb), (a1, b0, zb)], "int_ms_wall", tint=(0.86, 0.86, 0.86),
                      normal_hint=(0, 0, -1))
        L_ = max(a1 - a0, b1 - b0)
        n = max(1, int(L_ // 1.8))
        for k in range(n):
            t = (k + 0.5) / n
            gx, gy = (a0 + (a1 - a0) * t, (b0 + b1) / 2) if (a1 - a0) > (b1 - b0) else ((a0 + a1) / 2, b0 + (b1 - b0) * t)
            P.visual.poly([(gx + 0.09 * math.cos(a), gy + 0.09 * math.sin(a), zb - 0.005) for a in
                           [2 * math.pi * j / 6 for j in range(6)]][::-1], "int_ms_led", glow=True,
                          tint=(0.55, 1.0, 0.35), normal_hint=(0, 0, -1))
    lan = MP.soffit_lantern(5.6, 0.5, 0.6, 0.7)
    lcx, lcy = (x0 + x1) / 2 + 0.2, (y0 + y1) / 2
    P.merge(lan, lcx, lcy, zt, 0.0)
    for (qx, qy) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        cxq, cyq = lcx + qx * 2.6, lcy + qy * 2.6
        P.visual.box(cxq - 0.008, cyq - 0.008, zt, cxq + 0.008, cyq + 0.008, Z["ROOF"], "int_metal", faces="+x-x+y-y")
    # railings round the void: F3 (around the stair landing), F4, F5 (north + west: E / S are the glass)
    rz = 0.0
    e = 0.06
    paths = {"F3": [(x0 - e, STAIR_LANDING[3]), (x0 - e, y1 + e), (x1 + e, y1 + e), (x1 + e, y0 - e),
                    (STAIR_LANDING[2] - e, y0 - e), (STAIR_LANDING[2] - e, STAIR_LANDING[3])],
             "F4": [(x0 - e, y0 - e), (x0 - e, y1 + e), (x1 + e, y1 + e), (x1 + e, y0 - e), (x0 - e, y0 - e)],
             "F5": [(x1, y1 + e), (x0 - e, y1 + e), (x0 - e, y0)]}
    for lvl, pts in paths.items():
        P.merge(K.railing([(x, y, rz) for x, y in pts], height=1.0, infill="glass", post_every=2.5,
                          col_t=THIN_COL_T), 0.0, 0.0, Z[lvl], 0.0)
    # chandelier ring (walkable top, hangable underside), cables to the skylight
    cx, cy = CHANDELIER["pos"]
    ring = K.light_ring(CHANDELIER["radius"], CHANDELIER["ring_w"], 0.18, drop=Z["ROOF"] - CHANDELIER["top_z"],
                        strength=0.5)
    P.merge(ring, cx, cy, CHANDELIER["top_z"] - 0.18, 0.0)
    M.anchor("chandelier_top", cx + CHANDELIER["radius"], cy, CHANDELIER["top_z"], 0.0, floor="F4")
    M.anchor("chandelier_centre", cx, cy, CHANDELIER["top_z"], 0.0, floor="F4")
    # daylight down the void
    for zl, r, s in ((22.0, 16.0, 0.30), (15.0, 13.0, 0.22), (8.0, 13.0, 0.2), (3.0, 11.0, 0.18)):
        M.kit.light(K.Light(((x0 + x1) / 2, (y0 + y1) / 2, zl), radius=r, strength=s, color=(1.0, 0.99, 0.95)))
    M.anchor("atrium_court_centre", -56.6, -100.4, 0.0, 0.0, floor="F2")
    M.add(P, 0.0, 0.0, 0.0, 0.0, tag="atrium", group="atrium")


# ================================================================== chute + duct
def build_chute_and_duct(M):
    P = K.Prop("chute_duct", col_closed=False)
    V, C = P.visual, P.collision
    ya, yb = CHUTE["y"]
    xt, zt, xb, zbt = CHUTE["x_top"], CHUTE["z_top"], CHUTE["x_bottom"], CHUTE["z_bottom"]
    T = 0.15
    rail = 0.7
    # slide surface (visual metal, collision COL slide), sides, underside, top end wall
    V.poly([(xt, ya, zt), (xt, yb, zt), (xb, yb, zbt), (xb, ya, zbt)], "int_metal", ao=1.0, normal_hint=(0, 0, 1),
           tint=(0.9, 0.95, 1.0))
    add_raw_poly(C, [(xt, ya, zt), (xt, yb, zt), (xb, yb, zbt), (xb, ya, zbt)], COL_SLIDE, normal_hint=(0, 0, 1))
    V.poly([(xt, ya, zt - T), (xb, ya, zbt - T), (xb, yb, zbt - T), (xt, yb, zt - T)], "int_metal", ao=0.7,
           normal_hint=(0, 0, -1))
    C.poly([(xt, ya, zt - T), (xb, ya, zbt - T), (xb, yb, zbt - T), (xt, yb, zt - T)], K.COL, normal_hint=(0, 0, -1))
    # side rails. Collision: the INNER face only (fix round). Two coincident faces collapse into one in the
    # exporter's remove_doubles (the outward one had survived, so a rider steering sideways slid through it),
    # and a wall thinner than Mario's 50-unit radius throws an airborne Mario through to its far side anyway.
    # Inward-facing, a sliding rider is held in the chute; a player beside it on F1 can only be nudged onto it.
    for y, sgn in ((ya, -1), (yb, 1)):
        side = [(xt, y, zt - T), (xb, y, max(zbt - T, -6.0)), (xb, y, zbt + rail), (xt, y, zt + rail)]
        V.poly(side, "int_metal", ao=0.9, normal_hint=(0, sgn, 0))
        V.poly(side, "int_metal", ao=0.9, normal_hint=(0, -sgn, 0))
        C.poly(side, K.COL_NOCAM, normal_hint=(0, -sgn, 0))
    V.poly([(xt, ya, zt - T), (xt, yb, zt - T), (xt, yb, Z["F2"] - SLAB), (xt, ya, Z["F2"] - SLAB)], "int_metal",
           normal_hint=(-1, 0, 0), ao=0.8)
    C.poly([(xt, ya, zt - T), (xt, yb, zt - T), (xt, yb, Z["F2"] - SLAB), (xt, ya, Z["F2"] - SLAB)], K.COL,
           normal_hint=(-1, 0, 0))
    # fix round 5: the rails' outer faces have no collision (see above), so near the outlet, where they are low, a
    # player on the F1 floor walked through them into the chute. Two steel cabinets now flank the outlet (the book
    # bins' bay) up to the rails' height 1.8 m up the slope; beyond that the chute's underside is under 1.6 m above
    # the floor and its ceiling keeps a grounded player out. Closed collision except the face on the rail (no
    # doubled walls), 'COL default'.
    hx = 1.8
    cab_top = zt + rail + (xb + hx - xt) * (zbt - zt) / (xb - xt) + 0.05
    for y0c, y1c, open_face in ((ya - 0.55, ya, "+y"), (yb, yb + 0.55, "-y")):
        faces = "".join(f for f in ("+x", "-x", "+y", "-y", "+z") if f != open_face)
        V.box(xb, y0c, Z["F1"], xb + hx, y1c, cab_top, "int_metal", faces=faces, tint=(0.72, 0.74, 0.78))
        C.box(xb, y0c, Z["F1"], xb + hx, y1c, cab_top, K.COL, faces=faces)
        yc, sg = (y1c, 1) if open_face == "+y" else (y0c, -1)      # the face over the rail, toward the chute
        r0, r1 = zt + rail + (xb - xt) * (zbt - zt) / (xb - xt), zt + rail + (xb + hx - xt) * (zbt - zt) / (xb - xt)
        over = [(xb, yc, r0), (xb + hx, yc, r1), (xb + hx, yc, cab_top), (xb, yc, cab_top)]
        V.poly(over, "int_metal", ao=0.9, tint=(0.72, 0.74, 0.78), normal_hint=(0, sg, 0))
        C.poly(over, K.COL, normal_hint=(0, sg, 0))
    # hatch shaft (F2 slab hole down to the slide): its north / south sides close the gap from the rail tops up to
    # the slab's underside (collision facing in, so a player dropping through the hatch is kept over the slide);
    # the east side is the chute's end wall above, and the west side stays open (the slide runs on under the slab)
    hx0, hy0, hx1, hy1 = CHUTE_HATCH
    slope = (zbt - zt) / (xb - xt)

    def rail_top(x):
        return zt + rail + (x - xt) * slope
    for y, sgn in ((hy0, -1), (hy1, 1)):
        shaft = [(hx0, y, rail_top(hx0)), (xt, y, rail_top(xt)), (xt, y, Z["F2"] - SLAB), (hx0, y, Z["F2"] - SLAB)]
        V.poly(shaft, "int_metal", ao=0.7, normal_hint=(0, -sgn, 0))
        V.poly(shaft, "int_metal", ao=0.8, normal_hint=(0, sgn, 0))
        C.poly(shaft, K.COL_NOCAM, normal_hint=(0, -sgn, 0))
    # book pile at the bottom + run-out mat
    for i, (bx, by, s) in enumerate(((-79.4, -77.6, 0.5), (-79.9, -76.8, 0.4), (-79.2, -76.6, 0.35))):
        V.box(bx - s, by - s * 0.6, -6.0, bx + s, by + s * 0.6, -6.0 + s * 0.7, "int_books", faces="+x-x+y-y+z",
              uvs=None, tint=(0.95, 0.85, 0.75))
    M.anchor("chute_top", (hx0 + hx1) / 2, (hy0 + hy1) / 2, Z["F2"], 270.0, floor="F2", note="hatch in the F2 floor")
    M.anchor("chute_mid", (xt + xb) / 2, (ya + yb) / 2, (zt + zbt) / 2, 270.0, floor="F1")
    M.anchor("chute_bottom", xb - 0.8, (ya + yb) / 2, Z["F1"], 270.0, floor="F1")
    # vent duct (F1 north lab, west wall): walk-in metal duct, open at the south end
    dx0, dx1 = DUCT["x"]
    dy0, dy1 = DUCT["y"]
    z0, z1, t = DUCT["z0"], DUCT["z1"], DUCT["t"]
    xi0, xi1 = dx0, dx1 - t
    # inner floor / ceiling / east wall / north end
    for (yy0, yy1) in zip(split_line(dy0, dy1, 3.0), split_line(dy0, dy1, 3.0)[1:]):
        V.poly([(xi0, yy0, z0), (xi1, yy0, z0), (xi1, yy1, z0), (xi0, yy1, z0)], "int_metal", ao=1.0,
               tint=(0.7, 0.72, 0.75))
        V.poly([(xi0, yy0, z1), (xi0, yy1, z1), (xi1, yy1, z1), (xi1, yy0, z1)], "int_metal", ao=0.8,
               tint=(0.6, 0.62, 0.66))
        V.wall((xi1, yy1), (xi1, yy0), z0, z1, "int_metal", ao=0.85, tint=(0.66, 0.68, 0.72))
        V.poly([(xi0, yy0, z0 - 0.2), (xi0, yy1, z0 - 0.2), (dx1, yy1, z0 - 0.2), (dx1, yy0, z0 - 0.2)], "int_metal",
               ao=0.7)
        V.wall((dx1, yy0), (dx1, yy1), z0 - 0.2, z1 + 0.2, "int_metal", ao=0.95)
        V.poly([(xi0, yy0, z1 + 0.2), (dx1, yy0, z1 + 0.2), (dx1, yy1, z1 + 0.2), (xi0, yy1, z1 + 0.2)], "int_metal",
               ao=0.8)
    V.wall((xi0, dy1), (xi1, dy1), z0, z1, "int_rail_bars", uvs=[(0, 0), (2, 0), (2, 2), (0, 2)])
    V.wall((xi1, dy0), (dx1, dy0), z0 - 0.2, z1 + 0.2, "int_metal")
    V.poly([(xi0, dy0, z0 - 0.2), (xi1, dy0, z0 - 0.2), (xi1, dy0, z0), (xi0, dy0, z0)], "int_metal",
           normal_hint=(0, -1, 0))
    V.poly([(xi0, dy0, z1), (xi1, dy0, z1), (xi1, dy0, z1 + 0.2), (xi0, dy0, z1 + 0.2)], "int_metal",
           normal_hint=(0, -1, 0))
    K.col_box(C, xi0, dy0, z0 - 0.2, dx1, dy1, z0, K.COL, bottom=True)
    K.col_box(C, xi0, dy0, z1, dx1, dy1, z1 + 0.2, K.COL, bottom=True)
    K.col_box(C, xi1, dy0, z0, dx1, dy1, z1, K.COL, bottom=True)
    K.col_box(C, xi0, dy1 - 0.1, z0, xi1, dy1, z1, K.COL, bottom=True)
    M.anchor("duct_mouth", (xi0 + xi1) / 2, dy0 + 0.6, z0, 0.0, floor="F1")
    M.anchor("duct_mid", (xi0 + xi1) / 2, (dy0 + dy1) / 2, z0, 0.0, floor="F1")
    M.anchor("duct_end", (xi0 + xi1) / 2, dy1 - 0.8, z0, 0.0, floor="F1")
    M.add(P, 0.0, 0.0, 0.0, 0.0, tag="chute_duct", group="F1")


# ================================================================== the north porch (photo pass)
def build_porch(M):
    """The north entrance under the two-storey porch (#1-#4): the copper-clad box projecting over the storefront
    east of the doors (its underside lit by a surface light), the OPEN 24 HOURS neon in the transom, '444 NEWELL
    DRIVE' on the glass beside the doors, the orange news box at the brick pier, red brick bands in the exposed-
    aggregate paving. The storefront itself and the copper above it are the F2 / F3 outline walls."""
    P = K.Prop("porch", col_closed=False)
    V, C = P.visual, P.collision
    y_wall = PORCH[1]                                       # -75.5: the storefront line
    yo = y_wall + WALL_T                                    # its outer face
    # the copper box over the east storefront (#1, left)
    # fix round 5: the box ends at the NE hall's outer wall face (x -52.9): run to -52.6 its east face lay on the
    # hall's painted inner face (z-fighting inside the stair hall) and its collision doubled the hall wall's
    bx0, bx1, by0, by1, bz0, bz1 = -64.6, NE_RECT[0] - WALL_T, yo, yo + 2.6, 3.9, 6.0
    V.box(bx0, by0, bz0, bx1, by1, bz1, "int_ms_copper", faces="-x+y+z-z", tint=(0.95, 0.95, 0.95))
    C.box(bx0, by0, bz0, bx1, by1, bz1, K.COL, faces="-x+y-y+z-z")         # the hall wall closes its east end
    for x in (-61.5, -56.5):
        V.poly([(x + 0.22 * math.cos(a), by0 + 1.3 + 0.12 * math.sin(a), bz0 - 0.01) for a in
                [2 * math.pi * k / 6 for k in range(6)]][::-1], "int_ms_led", glow=True, normal_hint=(0, 0, -1))
        P.lights.append(K.Light((x, by0 + 1.3, bz0 - 0.6), radius=5.0, strength=0.25))
    # OPEN 24 HOURS (blue / yellow neon, cut-out) behind the transom glass of the doors
    dx0, dx1 = -69.2, -65.2
    cx = (dx0 + dx1) / 2 + 0.8
    yn = y_wall + WALL_T / 2 - 0.05
    # fix round 2: front_quad + ONCE (upright as seen from the porch; the quad's V ran top-down: OPEN read under HOURS)
    V.poly(K.front_quad(cx - 0.42, cx + 0.42, yn, 3.12, 3.84), "int_ms_neon_open", uvs=K.ONCE, glow=True,
           normal_hint=(0, 1, 0))
    # 444 / NEWELL DRIVE in white vinyl on the glass west of the doors (#1)
    yg = y_wall + WALL_T / 2 + 0.02
    V.poly(K.front_quad(-70.85, -69.6, yg, 1.75, 2.4), "int_ms_glass_444", uvs=K.ONCE, normal_hint=(0, 1, 0))
    # the news box by the west pier
    P.merge(MP.news_box(), -70.55, yo + 0.45, 0.0, 0.0)
    # brick bands in the paving (#1 #2): along the storefront and out from the doors
    for (x0, y0, x1, y1) in ((-71.0, yo + 0.55, -52.6, yo + 0.95), (-67.45, yo + 0.95, -67.05, -69.0),
                             (-58.6, yo + 0.95, -58.2, -69.0)):
        V.poly([(x0, y0, 0.006), (x1, y0, 0.006), (x1, y1, 0.006), (x0, y1, 0.006)], "int_ms_brick", ao=1.0,
               tint=(0.92, 0.9, 0.9))
    M.add(P, 0.0, 0.0, Z["F2"], 0.0, tag="porch_dressing", group="F2")


def brick_uvs(M):
    """Anisotropic UVs for the face brick (BRICK_UV: u along the wall, v up), so a 64 x 32 texture of 4 x 8 bricks
    gives modular 0.21 x 0.0675 m bricks; floors (paving bands) use u for both."""
    for _, _, pr in M.kit.items:
        for p in pr.visual.polys:
            sc = BRICK_UV.get(p.mat)
            if sc is None or p.uvs is not None:
                continue
            nx, ny, nz = K.newell(p.pts)
            if abs(nz) >= max(abs(nx), abs(ny)):
                uvs = [(q[0] / sc[0], q[1] / sc[0]) for q in p.pts]
            else:
                L = math.hypot(nx, ny) or 1.0
                hx, hy = -ny / L, nx / L
                uvs = [((q[0] * hx + q[1] * hy) / sc[0], q[2] / sc[1]) for q in p.pts]
            du = math.floor(min(u for u, _ in uvs))
            dv = math.floor(min(v for _, v in uvs))
            p.uvs = [(u - du, v - dv) for u, v in uvs]


# ================================================================== backdrop (no collision)
BACKDROP_R = 170.0
SKIP_BUILDINGS = {"w150860048", "w859919297", "w863677836", "w150860043"}


def build_backdrop(M, campus=None):
    """The campus around Marston, visual only: ground (lawn / paving / parking / Dairy Pond), walks and
    roads, trees, buildings extruded from campus.json, Century Tower, the court's glass roof, CSE."""
    if campus is None:
        with open(CAMPUS_PATH) as f:
            campus = json.load(f)
    cx, cy = CENTER
    P = K.Prop("backdrop", col_closed=False)
    V = P.visual
    R = BACKDROP_R
    foot = M.outlines["F2"]

    def near(pts, r=R + 10):
        return any(abs(x - cx) < r and abs(y - cy) < r for x, y in pts)
    areas = []
    for a in campus["areas"]:
        tg = a["tags"]
        if not near(a["pts"]):
            continue
        if tg.get("natural") == "water":
            areas.append((ccw([tuple(p) for p in a["pts"]]), ("pond_water", None)))
        elif tg.get("amenity") == "parking":
            areas.append((ccw([tuple(p) for p in a["pts"]]), ("parking", None)))
        elif tg.get("highway") == "pedestrian" or tg.get("place") == "square":
            areas.append((ccw([tuple(p) for p in a["pts"]]), ("plaza_brick", None)))
    areas.append((ccw([(-75.0, -69.0), (-48.0, -69.0), (-48.0, -58.0), (-75.0, -58.0)]), ("plaza_brick", None)))
    areas.insert(0, (ccw([tuple(q) for q in M.layout["footprint"]["court_roof_poly_m"]]), ("plaza_brick", None)))

    def ground(x, y):
        for poly, m in areas:
            if pip((x, y), poly):
                return m
        return ("lawn", None)
    gx = split_line(cx - R, cx + R, 8.0)
    gy = split_line(cy - R, cy + R, 8.0)
    cells = Cells.build([rect_poly((cx - R, cy - R, cx + R, cy + R))], [], gx, gy,
                        lambda x, y: None if pip((x, y), foot) or in_rect((x, y), PORCH) else ground(x, y))
    rects, parts = cells.merge(24.0, 24.0)
    for x0, y0, x1, y1, (m, t) in rects:
        V.poly([(x0, y0, -0.05), (x1, y0, -0.05), (x1, y1, -0.05), (x0, y1, -0.05)], m, ao=1.0)
        if m == "pond_water":
            # fix round 5: Dairy Pond's bed under the translucent water (the skybox showed through it from the F4 / F5
            # west and south windows); 4 m wider than the water, under the lawn, so no grazing view passes its edge
            e = 4.0
            V.poly([(x0 - e, y0 - e, -0.35), (x1 + e, y0 - e, -0.35), (x1 + e, y1 + e, -0.35), (x0 - e, y1 + e, -0.35)],
                   "pond_bed", ao=0.8)
    # walks and roads
    widths = {"footway": 2.4, "path": 2.0, "pedestrian": 4.0, "cycleway": 2.4, "service": 5.0, "unclassified": 6.5,
              "residential": 6.5, "tertiary": 7.5, "steps": 2.4}
    n_ways = 0
    for w in campus["ways"]:
        hw = w["tags"].get("highway")
        if hw not in widths or not near(w["pts"], R):
            continue
        mat = "asphalt" if hw in ("service", "unclassified", "residential", "tertiary") else "sidewalk"
        zz = -0.035 if mat == "sidewalk" else -0.04
        half = widths[hw] / 2
        pts = w["pts"]
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            if not (abs(ax - cx) < R and abs(ay - cy) < R and abs(bx - cx) < R and abs(by - cy) < R):
                continue
            L = math.hypot(bx - ax, by - ay)
            if L < 0.3:
                continue
            mx, my = (ax + bx) / 2, (ay + by) / 2
            if pip((mx, my), foot) or in_rect((mx, my), PORCH):
                continue
            nx, ny = -(by - ay) / L * half, (bx - ax) / L * half
            ext = min(half, 1.0)
            ux, uy = (bx - ax) / L * ext, (by - ay) / L * ext
            q = [(ax - ux + nx, ay - uy + ny, zz), (ax - ux - nx, ay - uy - ny, zz), (bx + ux - nx, by + uy - ny, zz),
                 (bx + ux + nx, by + uy + ny, zz)]
            V.poly(q, mat, ao=1.0, normal_hint=(0, 0, 1))
            n_ways += 1
    # trees
    rng = random.Random(7)
    n_trees = 0
    for p in campus["points"]:
        if p["tags"].get("natural") != "tree":
            continue
        x, y = p["pt"]
        if abs(x - cx) > R - 15 or abs(y - cy) > R - 15:
            continue
        s = rng.uniform(0.85, 1.25)
        # photo pass 2: the whole canopy (radius 3.9 s) stays 0.8 m off the building (one poked through the F3 wall)
        if pip((x, y), foot) or in_rect((x, y), PORCH, 3.0) or \
                min(seg_point_dist((x, y), a, b) for a, b in edges(foot)) < 3.9 * s + 0.8:
            continue
        tree(V, x, y, s, rng)
        n_trees += 1
    n_trees += plaza_oaks(V, campus, foot, random.Random(31))
    # buildings
    n_b = 0
    for b in campus["buildings"]:
        if b["id"] in SKIP_BUILDINGS:
            continue
        pts = ccw([tuple(q) for q in b["pts"]])
        bx = bbox(pts)
        bc = ((bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2)
        if math.dist(bc, (cx, cy)) > R + 20 or b.get("tags", {}).get("building") in ("roof", None):
            continue
        h = float(b.get("height") or 8.0)
        facade = "facade_brick" if h < 14 else "facade_band"
        if b["id"] == "w150860044":
            facade = "brick_red"
        if b["id"] == "w154223635":
            auditorium(V, pts)
            n_b += 1
            continue
        extrude(V, pts, h, facade, "roof_gravel")
        n_b += 1
    # Century Tower (w150860043): shaft, belfry, roof
    ct = next((b for b in campus["buildings"] if b["id"] == "w150860043"), None)
    if ct:
        century_tower_photo(V, ccw([tuple(q) for q in ct["pts"]]))
    # the court's glass roof (OSM w859919297, min_height 10) + its steel grid
    court = ccw([tuple(q) for q in M.layout["footprint"]["court_roof_poly_m"]])
    rz = 12.0
    V.poly([(x, y, rz) for x, y in court], "int_glass", ao=1.0)
    cb = bbox(court)
    for gxv in split_line(cb[0], cb[2], 3.0)[1:-1]:
        seg = clip_rect(court, gxv - 0.05, cb[1], gxv + 0.05, cb[3])
        if len(seg) >= 3:
            b2 = bbox(seg)
            V.box(b2[0], b2[1], rz - 0.25, b2[2], b2[3], rz, "metal_gray", faces="+x-x-z")
    for (px, py) in court[::3]:
        V.box(px - 0.15, py - 0.15, 0.0, px + 0.15, py + 0.15, rz, "metal_gray", faces="+x-x+y-y")
    # 'Alachua' (John Henry, 1987): the yellow 'French Fries' beams at the court's south-west mouth
    fx, fy = -98.0, -95.5
    for k, (ang, tilt, hgt) in enumerate(((10, 12, 9.75), (70, -15, 8.6), (140, 20, 9.2), (220, -8, 7.8),
                                          (300, 14, 9.0))):
        a = math.radians(ang)
        bx0, by0 = fx + math.cos(a) * 1.2, fy + math.sin(a) * 1.2
        lean = math.radians(tilt)
        topx, topy = bx0 + math.sin(lean) * hgt * math.cos(a), by0 + math.sin(lean) * hgt * math.sin(a)
        beam(V, (bx0, by0, 0.0), (topx, topy, hgt * math.cos(lean)), 0.35, "road_paint")
    # entry plaza planters (the hub module's two brick planters)
    for (px, py) in ((-53.5, -64.2), (-63.5, -64.2)):
        V.box(px - 2.4, py - 1.2, 0.0, px + 2.4, py + 1.2, 0.9, "brick_red", faces="+x-x+y-y")
        V.box(px - 2.3, py - 1.1, 0.88, px + 2.3, py + 1.1, 1.1, "leaves_oak", faces="+x-x+y-y+z")
    # the west arcade piers under F3 (F2 is recessed to x -82 there)
    for py in (-88.4, -93.0, -97.6, -102.2, -106.0):
        V.box(-89.3, py - 0.35, 0.0, -88.6, py + 0.35, Z["F3"] - SLAB, "brick_dark", faces="+x-x+y-y")
    M.stats["backdrop"] = {"buildings": n_b, "trees": n_trees, "way_segments": n_ways, "ground_rects": len(rects)}
    M.add(P, 0.0, 0.0, 0.0, 0.0, tag="backdrop", group="backdrop")


def extrude(V, pts, h, wall, roof):
    """A backdrop building: walls (split for UV spans) + a flat roof."""
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
    if (bx[2] - bx[0]) > 40 or (bx[3] - bx[1]) > 40:
        xs = split_line(bx[0], bx[2], 30.0)
        ys = split_line(bx[1], bx[3], 30.0)
        for x0, x1 in zip(xs, xs[1:]):
            for y0, y1 in zip(ys, ys[1:]):
                pc = clip_rect(pts, x0, y0, x1, y1)
                if len(pc) >= 3:
                    V.poly([(x, y, h) for x, y in ccw(pc)], roof, ao=1.0)
    else:
        V.poly([(x, y, h) for x, y in pts], roof, ao=1.0)


def beam(V, a, b, r, mat):
    """Square beam from a to b (3D), visual only."""
    d = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    L = math.sqrt(sum(c * c for c in d)) or 1.0
    u = (d[0] / L, d[1] / L, d[2] / L)
    ref = (0.0, 0.0, 1.0) if abs(u[2]) < 0.9 else (1.0, 0.0, 0.0)
    s = (u[1] * ref[2] - u[2] * ref[1], u[2] * ref[0] - u[0] * ref[2], u[0] * ref[1] - u[1] * ref[0])
    sl = math.sqrt(sum(c * c for c in s))
    s = tuple(c / sl * r for c in s)
    t = (u[1] * s[2] - u[2] * s[1], u[2] * s[0] - u[0] * s[2], u[0] * s[1] - u[1] * s[0])
    tl = math.sqrt(sum(c * c for c in t)) or 1.0
    t = tuple(c / tl * r for c in t)
    corners = [(s[0] + t[0], s[1] + t[1], s[2] + t[2]), (-s[0] + t[0], -s[1] + t[1], -s[2] + t[2]),
               (-s[0] - t[0], -s[1] - t[1], -s[2] - t[2]), (s[0] - t[0], s[1] - t[1], s[2] - t[2])]
    for i in range(4):
        c0, c1 = corners[i], corners[(i + 1) % 4]
        q = [(a[0] + c0[0], a[1] + c0[1], a[2] + c0[2]), (a[0] + c1[0], a[1] + c1[1], a[2] + c1[2]),
             (b[0] + c1[0], b[1] + c1[1], b[2] + c1[2]), (b[0] + c0[0], b[1] + c0[1], b[2] + c0[2])]
        mc = ((c0[0] + c1[0]) / 2, (c0[1] + c1[1]) / 2, (c0[2] + c1[2]) / 2)
        V.poly(q, mat, ao=1.0, normal_hint=mc)
    V.poly([(b[0] + c[0], b[1] + c[1], b[2] + c[2]) for c in corners], mat, ao=1.0, normal_hint=u)


def tree(V, x, y, s, rng):
    """A low-poly live oak: trunk + two octagonal canopy tiers + a cap."""
    tr = 0.22 * s
    V.box(x - tr, y - tr, 0.0, x + tr, y + tr, 3.2 * s, "bark", faces="+x-x+y-y", ao=1.0)
    n = 7
    rot = rng.uniform(0, math.pi)
    tiers = [(2.8 * s, 3.9 * s, 3.0 * s), (5.0 * s, 3.0 * s, 7.0 * s)]
    prev = None
    for z0, r, z1 in tiers:
        lo = [(x + r * math.cos(rot + 2 * math.pi * k / n), y + r * math.sin(rot + 2 * math.pi * k / n)) for k in range(n)]
        hi = [(x + r * 0.62 * math.cos(rot + 2 * math.pi * (k + 0.5) / n),
               y + r * 0.62 * math.sin(rot + 2 * math.pi * (k + 0.5) / n)) for k in range(n)]
        for k in range(n):
            k2 = (k + 1) % n
            V.poly([(lo[k][0], lo[k][1], z0), (lo[k2][0], lo[k2][1], z0), (hi[k][0], hi[k][1], z1)],
                   "leaves_oak", ao=1.0, normal_hint=((lo[k][0] + lo[k2][0]) / 2 - x, (lo[k][1] + lo[k2][1]) / 2 - y, 0.4))
            V.poly([(lo[k2][0], lo[k2][1], z0), (hi[k2][0], hi[k2][1], z1), (hi[k][0], hi[k][1], z1)],
                   "leaves_oak2", ao=1.0, normal_hint=(hi[k][0] - x, hi[k][1] - y, 0.6))
        V.poly([(px, py, z0) for px, py in reversed(lo)], "leaves_oak2", ao=1.0)
        prev = hi
    V.poly([(px, py, tiers[-1][2]) for px, py in prev], "leaves_oak", ao=1.0)


def century_tower(V, pts):
    """Century Tower (1953, 47.9 m): brick shaft, limestone bands, clock faces, open belfry, roof."""
    bx = bbox(pts)
    cx, cy = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2
    w = min(bx[2] - bx[0], bx[3] - bx[1]) / 2
    sq = [(cx - w, cy - w), (cx + w, cy - w), (cx + w, cy + w), (cx - w, cy + w)]
    for a, b in edges(sq):
        for za, zb, m in ((0.0, 3.0, "limestone"), (3.0, 15.0, "brick_red"), (15.0, 27.0, "brick_red"),
                          (27.0, 33.0, "brick_red"), (33.0, 33.8, "limestone"), (37.8, 38.6, "limestone"),
                          (38.6, 41.0, "brick_red"), (41.0, 41.8, "limestone")):
            V.wall(a, b, za, zb, m, ao=1.0)
        # clock band 33.8-37.8: a limestone face with a dark clock disc
        V.wall(a, b, 33.8, 37.8, "limestone", ao=1.0)
        L = math.dist(a, b)
        dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx, ny = dy, -dx
        mcx, mcy = (a[0] + b[0]) / 2 + nx * 0.03, (a[1] + b[1]) / 2 + ny * 0.03
        n = 12
        ring = [(mcx + dx * 1.5 * math.cos(2 * math.pi * k / n), mcy + dy * 1.5 * math.cos(2 * math.pi * k / n),
                 35.8 + 1.5 * math.sin(2 * math.pi * k / n)) for k in range(n)]
        V.poly(ring, "white_trim", ao=1.0, normal_hint=(nx, ny, 0))
        V.poly([(mcx + nx * 0.02, mcy + ny * 0.02, 35.8), (mcx + nx * 0.02 + dx * 0.08, mcy + ny * 0.02 + dy * 0.08, 35.8),
                (mcx + nx * 0.02 + dx * 0.08, mcy + ny * 0.02 + dy * 0.08, 37.0), (mcx + nx * 0.02, mcy + ny * 0.02, 37.0)],
               "dark_trim", ao=1.0, normal_hint=(nx, ny, 0))
        # belfry openings 38.6-41.0 (dark arch panes)
        for k in range(3):
            s0 = L * (k + 0.25) / 3
            s1 = L * (k + 0.75) / 3
            pa = (a[0] + dx * s0 + nx * 0.02, a[1] + dy * s0 + ny * 0.02)
            pb = (a[0] + dx * s1 + nx * 0.02, a[1] + dy * s1 + ny * 0.02)
            V.wall(pa, pb, 38.8, 40.8, "window_dark", ao=1.0)
    # roof: a steep pyramid to 47.9 m
    for a, b in edges(sq):
        V.poly([(a[0], a[1], 41.8), (b[0], b[1], 41.8), (cx, cy, 47.9)], "roof_dark", ao=1.0,
               normal_hint=((a[0] + b[0]) / 2 - cx, (a[1] + b[1]) / 2 - cy, 0.5))


def century_tower_photo(V, pts):
    """Century Tower (1953, 47.9 m; the view from floors 4-5, #99 #104): a brick shaft on a cast-stone base, the clock
    stage under a cast-stone band, then the open belfry (two tall lancets per face between stone corner piers) and the
    crown: a tracery stage, a crenellated parapet and four corner pinnacles (no roof). Visual only."""
    bx = bbox(pts)
    cx, cy = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2
    w = min(bx[2] - bx[0], bx[3] - bx[1]) / 2

    def square(r):
        return [(cx - r, cy - r), (cx + r, cy - r), (cx + r, cy + r), (cx - r, cy + r)]
    sq = square(w)
    for a, b in edges(sq):
        L = math.dist(a, b)
        dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx, ny = dy, -dx
        for za, zb, m in ((0.0, 2.6, "limestone"), (2.6, 31.0, "brick_red"), (31.0, 31.7, "limestone"),
                          (31.7, 35.4, "brick_red"), (35.4, 36.2, "limestone")):
            V.wall(a, b, za, zb, m, ao=1.0)
        # stone quoins up the shaft corners (#104)
        for s0, s1 in ((0.0, 0.45), (L - 0.45, L)):
            pa = (a[0] + dx * s0 + nx * 0.03, a[1] + dy * s0 + ny * 0.03)
            pb = (a[0] + dx * s1 + nx * 0.03, a[1] + dy * s1 + ny * 0.03)
            V.wall(pa, pb, 2.6, 31.0, "limestone", ao=1.0, tint=(0.92, 0.9, 0.86))
        # the clock faces (31.7-35.4)
        mcx, mcy = (a[0] + b[0]) / 2 + nx * 0.04, (a[1] + b[1]) / 2 + ny * 0.04
        ring = [(mcx + dx * 1.45 * math.cos(2 * math.pi * k / 12), mcy + dy * 1.45 * math.cos(2 * math.pi * k / 12),
                 33.55 + 1.45 * math.sin(2 * math.pi * k / 12)) for k in range(12)]
        V.poly(ring, "white_trim", ao=1.0, normal_hint=(nx, ny, 0))
        V.poly([(mcx + nx * 0.02, mcy + ny * 0.02, 33.55), (mcx + nx * 0.02 + dx * 0.09, mcy + ny * 0.02 + dy * 0.09, 33.55),
                (mcx + nx * 0.02 + dx * 0.09, mcy + ny * 0.02 + dy * 0.09, 34.7), (mcx + nx * 0.02, mcy + ny * 0.02, 34.7)],
               "dark_trim", ao=1.0, normal_hint=(nx, ny, 0))
        # belfry 36.2-42.6: stone piers at the corners and between two tall lancets (dark openings, pointed heads)
        V.wall(a, b, 36.2, 36.9, "limestone", ao=1.0)
        V.wall(a, b, 41.6, 42.6, "limestone", ao=1.0)
        for k in range(2):
            s0, s1 = L * (0.16 + 0.39 * k), L * (0.45 + 0.39 * k)
            pa, pb = (a[0] + dx * s0, a[1] + dy * s0), (a[0] + dx * s1, a[1] + dy * s1)
            V.wall(pa, pb, 36.9, 40.6, "window_dark", ao=1.0)
            pm = ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)
            V.poly([(pa[0], pa[1], 40.6), (pb[0], pb[1], 40.6), (pm[0], pm[1], 41.6)], "window_dark", ao=1.0,
                   normal_hint=(nx, ny, 0))
            V.poly([(pa[0], pa[1], 40.6), (pm[0], pm[1], 41.6), (a[0] + dx * (s0 - L * 0.04), a[1] + dy * (s0 - L * 0.04),
                                                                41.6)], "limestone", ao=1.0, normal_hint=(nx, ny, 0))
        for s0, s1 in ((0.0, L * 0.16), (L * 0.45, L * 0.55), (L * 0.84, L)):
            pa, pb = (a[0] + dx * s0, a[1] + dy * s0), (a[0] + dx * s1, a[1] + dy * s1)
            V.wall(pa, pb, 36.9, 41.6, "limestone", ao=1.0)
    # the crown: a stone tracery stage set in 0.3 m, a crenellated parapet, four pinnacles
    sq2 = square(w - 0.3)
    V.poly([(x, y, 42.6) for x, y in sq], "limestone", ao=1.0)
    for a, b in edges(sq2):
        V.wall(a, b, 42.6, 45.2, "limestone", ao=1.0, tint=(0.95, 0.93, 0.9))
        L = math.dist(a, b)
        dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx, ny = dy, -dx
        for k in range(4):
            s0, s1 = L * (0.12 + 0.2 * k), L * (0.2 + 0.2 * k)
            V.wall((a[0] + dx * s0 + nx * 0.02, a[1] + dy * s0 + ny * 0.02),
                   (a[0] + dx * s1 + nx * 0.02, a[1] + dy * s1 + ny * 0.02), 43.0, 44.8, "window_dark", ao=1.0)
        for k in range(5):                                       # merlons
            s0, s1 = L * (0.04 + 0.2 * k), L * (0.13 + 0.2 * k)
            pa, pb = (a[0] + dx * s0, a[1] + dy * s0), (a[0] + dx * s1, a[1] + dy * s1)
            V.wall(pa, pb, 45.2, 46.0, "limestone", ao=1.0)
    for (px, py) in sq2:
        V.box(px - 0.45, py - 0.45, 42.6, px + 0.45, py + 0.45, 46.4, "limestone", faces="+x-x+y-y", ao=1.0)
        for a, b in edges(square(0.45)):
            ax, ay = a[0] - cx + px, a[1] - cy + py
            bx_, by_ = b[0] - cx + px, b[1] - cy + py
            V.poly([(ax, ay, 46.4), (bx_, by_, 46.4), (px, py, 47.9)], "limestone", ao=1.0,
                   normal_hint=((ax + bx_) / 2 - px, (ay + by_) / 2 - py, 0.5))
    V.poly([(x, y, 45.15) for x, y in sq2], "roof_gravel", ao=1.0)


def auditorium(V, pts):
    """University Auditorium (1922, Gothic; #104 behind the tower): its OSM footprint as a cast-stone / brick Gothic
    facade to the eaves and the steep red-tile gable over the main hall (running N-S)."""
    extrude(V, pts, 11.5, "facade_gothic", "roof_gravel")
    x0, y0, x1, y1 = 30.3, 17.4, 45.7, 56.1
    zr, ze = 20.5, 11.5
    xm = (x0 + x1) / 2
    V.poly([(x1, y0, ze), (x1, y1, ze), (xm, y1, zr), (xm, y0, zr)], "roof_tile_red", ao=1.0, normal_hint=(1, 0, 1))
    V.poly([(x0, y1, ze), (x0, y0, ze), (xm, y0, zr), (xm, y1, zr)], "roof_tile_red", ao=1.0, normal_hint=(-1, 0, 1))
    V.poly([(x0, y0, ze), (x1, y0, ze), (xm, y0, zr)], "facade_gothic", ao=1.0, normal_hint=(0, -1, 0))
    V.poly([(x1, y1, ze), (x0, y1, ze), (xm, y1, zr)], "facade_gothic", ao=1.0, normal_hint=(0, 1, 0))


def plaza_oaks(V, campus, foot, rng):
    """The live oaks between Marston and Century Tower (#99 #104 show an unbroken canopy north of the library; OSM maps
    only a few of them): mature oaks over the lawn north of the building, clear of the walks, the
    buildings, the entry plaza and the tower. Inferred positions. Returns the count."""
    blds = [ccw([tuple(q) for q in b["pts"]]) for b in campus["buildings"]]
    segs = []
    for w_ in campus["ways"]:
        if w_["tags"].get("highway") is None:
            continue
        pts_ = w_["pts"]
        for p, q in zip(pts_, pts_[1:]):
            if -100 < p[0] < 20 and -70 < p[1] < 10:
                segs.append((tuple(p), tuple(q)))
    n = 0
    y = -60.0
    while y < 2.0:
        x = -92.0
        while x < 16.0:
            px, py = x + rng.uniform(-3.5, 3.5), y + rng.uniform(-3.5, 3.5)
            sc = rng.uniform(1.5, 2.1)                 # mature live oaks: 11-15 m tall, 12-16 m across
            r = 3.9 * sc
            ok = math.dist((px, py), (-0.9, -0.95)) > 12.0
            ok = ok and not (-76.0 < px < -46.0 and py < -55.0)              # the entry plaza + planters
            ok = ok and min((seg_point_dist((px, py), a, b) for a, b in edges(foot)), default=99) > r + 2.0
            ok = ok and not any(pip((px, py), b) or min(seg_point_dist((px, py), a, c) for a, c in edges(b)) < r * 0.6
                                for b in blds if bbox(b)[0] - 10 < px < bbox(b)[2] + 10 and bbox(b)[1] - 10 < py < bbox(b)[3] + 10)
            ok = ok and all(seg_point_dist((px, py), a, b) > 3.0 for a, b in segs)
            if ok:
                tree(V, px, py, sc, rng)
                n += 1
            x += 11.5
        y += 11.5
    return n


# ================================================================== pickups, points, views
def plan_pickups(M):
    """Coins (> 120 so the 100-coin star is reachable), hearts, 1-ups, Goombas: map (x, y, design floor z).
    Placed (and checked against the collision) by build_interior.py with stage_pickups.Placer."""
    red = [tuple(r["pos_m"]) for r in M.layout["missions"]["design_act4_lost_lab_notebook_pages"]["red_coins"]]
    out = []

    def add(kind, name, x, y, z, facing=0.0):
        if kind in ("coin", "coin_line", "coin_ring") and any(math.dist((x, y), r) < 2.5 for r in red):
            return
        out.append({"kind": kind, "name": name, "pos": (round(x, 3), round(y, 3), round(z, 3)), "facing": facing})
    z1, z2, z3, z4, z5, zr = (Z[k] for k in ("F1", "F2", "F3", "F4", "F5", "ROOF"))
    # F2: lobby -> atrium, the court, the grand stair, cafe, sci-fi aisle, east hall
    add("coin_line", "F2 lobby to the atrium", -67.4, -88.6, z2, 180.0)
    add("coin_line", "F2 atrium court", -56.4, -98.6, z2, 0.0)
    gs = M.anchors.get("grand_stair_bottom", {"pos": (-63.25, -95.5, 0.0)})["pos"]
    for k in range(6):
        t = (k + 0.5) / 6
        y = gs[1] - 1.0 - t * (gs[1] - 1.0 - STAIR_LANDING[3])
        add("coin", f"F2 grand stair coin {k + 1}", -63.25, y, z2 + t * STOREY)
    add("coin_line", "F2 Starbucks", -78.9, -99.0, z2, 0.0)
    add("coin_line", "F2 science fiction aisle", -60.1, -121.0, z2, 0.0)
    add("coin_line", "F2 NE hall", -47.6, -82.6, z2, 90.0)
    add("coin_line", "F2 east tables", -46.8, -97.7, z2, 90.0)
    # F1: commons rings, study-room rows, makerspace, duct, sorting room
    add("coin_ring", "F1 commons ring north", -56.4, -88.0, z1)
    add("coin_ring", "F1 commons ring south", -53.8, -108.0, z1)
    add("coin_line", "F1 east study rooms", -39.2, -104.0, z1, 0.0)
    add("coin_line", "F1 south study rooms", -50.0, -118.8, z1, 90.0)
    add("coin_line", "F1 north lab", -77.0, -63.0, z1, 0.0)
    add("coin_line", "F1 makerspace", -74.6, -101.4, z1, 0.0)
    add("coin_line", "F1 west commons", -68.8, -99.0, z1, 0.0)
    for k, y in enumerate((-70.0, -62.0, -58.0)):
        add("coin", f"F1 vent duct coin {k + 1}", -82.1, y, DUCT["z0"])
    add("coin_line", "F1 sorting room", -75.0, -76.4, z1, 90.0)
    # F3: periodicals aisles + range tops, the balcony, theses, east tables
    add("coin_line", "F3 north periodicals aisle", -56.4, -88.8, z3, 0.0)
    add("coin_line", "F3 south periodicals aisle", -56.4, -114.9, z3, 0.0)     # clear of the book-cart bridge (-112.45)
    add("coin_line", "F3 atrium balcony east", -50.5, -100.0, z3, 0.0)
    add("coin_line", "F3 east tables", -37.8, -99.0, z3, 90.0)
    add("coin_line", "F3 elevator lobby", -75.0, -92.6, z3, 90.0)
    for st in M.stack_tops:
        if st["main"] and st["floor"] in ("F3", "F4"):
            add("coin", f"{st['floor']} range top {st['name']}", st["pos"][0], st["pos"][1], st["pos"][2])
    # F4: quiet floor aisles, terraces
    add("coin_line", "F4 quiet study aisle", -48.6, -99.0, z4, 0.0)
    add("coin_line", "F4 west reading tables", -84.5, -98.0, z4, 0.0)
    add("coin_line", "F4 east terrace", -38.0, -106.0, z4, 0.0)
    add("coin_line", "F4 east terrace south", -38.0, -119.0, z4, 0.0)
    add("coin_line", "F4 south terrace", -60.0, -120.4, z4, 90.0)
    # F5: reading rooms, terraces, window desks
    add("coin_line", "F5 north reading room", -61.0, -80.6, z5, 90.0)
    add("coin_line", "F5 north windows", -61.5, -71.2, z5, 90.0)
    add("coin_line", "F5 west reading room", -78.5, -101.0, z5, 0.0)
    add("coin_line", "F5 east terrace", -47.2, -92.0, z5, 0.0)
    add("coin_line", "F5 south terrace", -66.0, -112.0, z5, 90.0)
    # roof
    add("coin_ring", "roof ring", -61.0, -82.0, zr)
    add("coin_line", "roof west", -84.0, -96.0, zr, 0.0)
    # stair halls: a coin on every turn landing
    for k, v in sorted(M.anchors.items()):
        if k.endswith("_turn") and (k.startswith("ne_stair") or k.startswith("sw_stair")):
            add("coin", f"turn landing {k}", v["pos"][0], v["pos"][1], v["pos"][2])
    # hearts, 1-ups, Goombas
    out.append({"kind": "heart", "name": "heart F1 commons", "pos": (-60.0, -92.0, z1)})
    out.append({"kind": "heart", "name": "heart F3 west balcony", "pos": (-67.0, -100.0, z3)})
    out.append({"kind": "heart", "name": "heart F5 north reading room", "pos": (-57.0, -91.0, z5)})
    out.append({"kind": "heart", "name": "heart roof", "pos": (-70.0, -79.0, zr)})
    ne = M.anchors["ne_tower_top"]["pos"]
    out.append({"kind": "1up", "name": "1-up NE tower top", "pos": ne})
    ch = M.anchors["chandelier_top"]["pos"]
    out.append({"kind": "1up", "name": "1-up chandelier ring", "pos": (ch[0] - 2 * CHANDELIER["radius"], ch[1], ch[2])})
    de = M.anchors["duct_end"]["pos"]
    out.append({"kind": "1up", "name": "1-up vent duct end", "pos": de})
    for name, x, y, z in (("goomba F1 commons", -58.0, -100.0, z1), ("goomba F1 east", -44.0, -94.0, z1),
                          ("goomba F3 north aisle", -56.4, -88.0, z3), ("goomba F4 QC-Z aisle", -70.1, -102.0, z4)):
        out.append({"kind": "goomba", "name": name, "pos": (x, y, z), "facing": 90.0})
    M.pickups = out


def plan_points(M):
    """Design anchor points for the mission author (docs/game_design.md 7.3), grouped as the points file
    is; build_interior.py re-measures each on the built collision."""
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

    def zf(fl):
        return Z[fl]
    a1 = L["design_act1_out_of_order_elevator"]
    pts["act1_out_of_order_elevator"] = {
        "start": g("act1_start", (*a1["start"]["pos_m"], zf("F2")), facing=180.0),
        "star_target": g("act1_star_target", (*a1["star"]["pos_m"], zf("F5")), clear=0.25,
                         note="between the north reading tables by the view windows; hover the star ~1.2 m up"),
        "elevator_doors": [g(f"act1_elevator1_door_{lvl}", M.anchors[f"elevator1_door_{lvl}"]["pos"], facing=180.0)
                           for lvl in ("F2", "F3", "F4", "F5")],
        "shaft": g("act1_shaft_bottom", M.anchors["elevator1_shaft_bottom"]["pos"],
                   note="inside elevator 1 (out of order): wall-kick shaft to the F5 door; inner size "
                        + str(M.anchors["elevator1_shaft_bottom"]["shaft_inner_m"])),
        "chandelier_top": g("act1_chandelier_top", M.anchors["chandelier_top"]["pos"]),
        "book_cart_tracks": [g(f"act1_cart_track_{t['floor']}_{k}",
                               ((-60.9, t["a_m"][1]) if t["floor"] == "F2" else tuple(t["a_m"])) + (zf(t["floor"]),),
                               kind="air" if t["floor"] != "F2" else "ground",
                               end=list(t["b_m"]) if t["floor"] != "F2" else [-52.8, t["b_m"][1]],
                               note=(t.get("note") or "") + (" (starts east of the grand stair)" if t["floor"] == "F2"
                                                             else ""))
                             for k, t in enumerate(a1["book_cart_tracks"])],
        "encyclopedias": [g(f"act1_encyclopedia_{e['floor']}", ((-60.97, -90.9) if e["floor"] == "F3" else
                                                                 (-60.97, e["pos_m"][1])) + (zf(e["floor"]),),
                            note=(e.get("note") or "") + " (on the aisle centre line, clear of the module column)")
                          for e in a1["falling_encyclopedias"]],
        "renovation_barriers": [g(f"act1_barrier_{k}", M.anchors[k]["pos"]) for k in
                                ("ne_stair_F2_landing", "sw_stair_F2_landing", "core_stair_F2_landing")],
    }
    a2 = L["design_act2_quiet_floor"]
    pts["act2_quiet_floor"] = {
        "start": g("act2_start", (*a2["start"]["pos_m"], zf("F5")), facing=270.0),
        "goal_window_desk": g("act2_goal", (*a2["goal"]["pos_m"], zf("F5")), facing=270.0),
        "shusher_patrols": [{"name": f"act2_patrol_{k}", "note": p.get("note"),
                             "points": [g(f"act2_patrol_{k}_{i}", (*q, zf("F5"))) for i, q in enumerate(p["loop_m"])]}
                            for k, p in enumerate(a2["shusher_patrols"])],
        "librarian_patrol_f4": {"name": "f4_librarian_patrol", "note": "the QUIET floor (F4) loop: A-QC aisle -> "
                                "quiet study -> QC-Z south aisle -> west reading tables",
                                "points": [g(f"f4_patrol_{i}", (x, y, zf("F4"))) for i, (x, y) in enumerate(
                                    ((-61.0, -82.0), (-47.2, -82.0), (-47.2, -110.5), (-65.5, -112.2),
                                     (-75.0, -108.0), (-80.5, -95.0), (-66.0, -92.0)))]},
        "sent_back_to": g("act2_sent_back", (*a2["sent_back_to"]["pos_m"], zf("F5"))),
    }
    a3 = L["design_act3_group_study_room_booking"]
    star_room = next((d for d in M.doors["F1"] if d["room"] == a3["star_room"]), None)
    pts["act3_group_study_room_booking"] = {
        "kiosks": dict({k: g(f"act3_kiosk_{k}", M.anchors[f"kiosk_{k}"]["pos"], clear=0.6,
                             note="kiosk spot (layout); the act 3 mission spawns the kiosk itself (no level geometry)")
                        for k in ("K1", "K2", "K3", "K4")},
                       K3_f4=g("act3_kiosk_K3_f4", (-45.5, -105.0, zf("F4")), clear=0.6,
                               note="K3 as uf_marston_missions.lua places it (4th-floor quiet study, between carrel "
                                    "rows 4 and 5): the layout's F3 K3 is too close to K2 for the 4 s window")),
        "use_order_by_players": a3["use_order_by_players"],
        "star_room": a3["star_room"],
        "star_room_door": None if star_room is None else {
            "a_m": list(star_room["a"]), "b_m": list(star_room["b"]), "width_m": star_room["width"],
            "head_m": star_room["head"], "facing_deg": star_room["facing"],
            "centre": g("act3_star_room_door", (*star_room["centre"], zf("F1")), facing=star_room["facing"])},
        "star_target": g("act3_star_target", (*a3["star"]["pos_m"], zf("F1")),
                         note="inside glass room L129; hover the star ~1.2 m up"),
    }
    a4 = L["design_act4_lost_lab_notebook_pages"]
    reds = []
    for k, r in enumerate(a4["red_coins"]):
        x, y = r["pos_m"]
        note = r.get("note", "")
        p = (x, y, r["z_game_m"] - 0.5)
        if "chute" in note:
            p = M.anchors["chute_mid"]["pos"]
        elif "duct" in note:
            p = (M.anchors["duct_mid"]["pos"][0], y, DUCT["z0"])
        elif "chandelier" in note:
            p = M.anchors["chandelier_top"]["pos"]
        elif "fish tank" in note:
            p = M.anchors["fish_tank_lid"]["pos"]
        elif "Starbucks" in note:
            p = M.anchors["cafe_counter_top"]["pos"]
        elif "A-QC" in note:
            top = next(s for s in M.stack_tops if s["name"].endswith("aqc_02"))
            p = top["pos"]
        elif "3D-printer" in note:
            p = (x, y, Z["F1"] + 1.2)
        reds.append(g(f"act4_red_{k + 1}", p, note=note, kind="air" if r.get("over_void") or "chute" in note else "ground",
                      float_m=0.6))
    pts["act4_lost_lab_notebook_pages"] = {"red_coins": reds}
    a5 = L["design_act5_printer_jam"]
    ar = a5["arena_poly_m"]
    pts["act5_printer_jam"] = {
        "arena_poly_m": ar, "floor_z": Z["F1"],
        "centre": g("act5_arena_centre", ((ar[0][0] + ar[1][0]) / 2, (ar[0][1] + ar[2][1]) / 2, zf("F1"))),
        "heads_start": [g(f"act5_head_{k}", (*h, zf("F1"))) for k, h in enumerate(a5["gantry"]["heads_start_m"])],
        "gantry_rail_z": Z["F1"] + 4.6,
        "note": "the arena floor is clear: the commons tables inside it are not built (static level geometry "
                "cannot be act-masked); columns at the module grid points stay as cover",
        "tables_left_out": M.notes.get("left_out_for_the_act5_arena", []),
    }
    a6 = L["design_act6_overdue_book_express"]
    pts["act6_overdue_book_express"] = {
        "book": g("act6_book", (*a6["book"]["pos_m"], zf("F5") + K.REAL["table_h"]), clear=0.2,
                  note="on a north reading-room table (table top 0.76 m)"),
        "return_slot": g("act6_return_slot", (-68.5, -77.2, zf("F2")), facing=270.0, clear=0.4,
                         slot_m=list(M.anchors["book_return_slot"]["pos"]),
                         note="stand here (vestibule) facing the slot in the west glass wall (slot 1.0 m up)"),
        "throw_line_f5": g("act6_throw_rail_f5", (-58.4, -92.4, zf("F5")), clear=0.2,
                           note="at the F5 north atrium railing; the F2 court is 18 m below"),
        "catch_f2": g("act6_catch_f2", (-58.4, -97.0, zf("F2"))),
    }
    pts["stack_tops"] = [g(s["name"], s["pos"], note=s.get("label"), length_m=s["length_m"], height_m=s["height_m"],
                           main=s["main"], clear=0.4) for s in M.stack_tops]
    pts["group_study_rooms"] = [
        {"room": d["room"], "floor": d["floor"], "name": d["room_name"], "door_a_m": list(d["a"]), "door_b_m": list(d["b"]),
         "door_width_m": d["width"], "door_head_m": d["head"], "facing_deg": d["facing"],
         "door": g(f"room_{d['room']}_door", (*d["centre"], Z[d["floor"]]), facing=d["facing"]),
         "inside": g(f"room_{d['room']}_inside", _inside_point(M, d), facing=(d["facing"] + 180) % 360, clear=0.45)}
        for fl in FLOORS for d in M.doors[fl] if d["type"] == "group_study"]
    pts["rooms"] = [{"room": d["room"], "floor": d["floor"], "type": d["type"], "name": d["room_name"],
                     "door": g(f"room_{d['room']}_door", (*d["centre"], Z[d["floor"]]), facing=d["facing"])}
                    for fl in FLOORS for d in M.doors[fl] if d["type"] != "group_study"]
    pts["service_desk"] = {"counter": g("service_desk_counter", M.anchors["service_desk_counter"]["pos"]),
                           "patron": g("service_desk_patron", M.anchors["service_desk_patron"]["pos"], facing=0.0)}
    pts["cafe"] = {"counter_top": g("cafe_counter_top", M.anchors["cafe_counter_top"]["pos"]),
                   "customer": g("cafe_customer", M.anchors["cafe_customer_side"]["pos"], facing=90.0)}
    pts["circulation"] = [g(k, v["pos"], facing=v["facing"], clear=0.5,
                            kind="air" if k in ("chute_top", "chute_mid") else "ground")
                          for k, v in sorted(M.anchors.items())
                          if k.startswith(("ne_stair", "sw_stair", "core_stair", "grand_stair", "chute", "duct"))]
    pts["landmarks"] = [g(k, v["pos"], facing=v["facing"], clear=0.3, kind="air" if k == "chandelier_centre" else "ground")
                        for k, v in sorted(M.anchors.items())
                        if k in ("atrium_court_centre", "fish_tank_lid", "ne_tower_top", "sw_tower_top",
                                 "duct_step_sorting_table", "chandelier_centre") or k.startswith("roof_")]
    pts["terraces"] = [g("terrace_e4", (-38.0, -106.0, Z["F4"])), g("terrace_s4", (-57.0, -120.5, Z["F4"])),
                       g("terrace_e5", (-47.2, -97.0, Z["F5"])), g("terrace_s5", (-66.0, -111.8, Z["F5"])),
                       g("roof_deck", (-62.0, -82.0, Z["ROOF"])), g("porch", (-62.0, -72.2, Z["F2"]))]
    pts["views"] = [g("view_f5_north_window", (-62.5, -70.0 - 1.4, Z["F5"]), facing=31.0,
                      note="Century Tower 114 m NNE through the 5th floor view windows")]
    M.points = pts


def _inside_point(M, d):
    f = math.radians(d["facing"])
    x, y = d["centre"]
    return (x - math.sin(f) * 0.8, y - math.cos(f) * 0.8, Z[d["floor"]])


def plan_views(M):
    """Preview cameras: (name, location, target, Mario stand-in (x, y, z, facing) or None, vfov)."""
    sp = M.layout["entrance"]["spawn"]["pos_m"]
    M.views = [
        ("marston_lobby", (-67.6, -79.6, 2.9), (-60.0, -99.0, 2.4), (sp[0], sp[1], 0.0, 180.0), 52.0),
        ("marston_atrium", (-66.4, -94.0, 2.0), (-56.0, -101.0, 14.0), (-63.25, -97.0, 0.0, 180.0), 60.0),
        ("marston_atrium_down", (-54.0, -94.4, 19.6), (-58.4, -102.0, 0.0), None, 60.0),
        ("marston_stacks", (-56.4, -79.6, 15.6), (-56.4, -92.0, 13.6), (-56.4, -84.0, 12.0, 180.0), 50.0),
        ("marston_quiet_floor", (-44.5, -80.6, 15.4), (-48.0, -100.0, 13.0), (-47.2, -86.0, 12.0, 180.0), 50.0),
        ("marston_study_rooms", (-49.0, -103.0, -3.3), (-36.0, -115.0, -4.8), (-41.0, -110.0, -6.0, 135.0), 52.0),
        ("marston_commons", (-66.6, -88.6, -2.6), (-46.0, -110.0, -5.0), (-60.0, -95.6, -6.0, 135.0), 55.0),
        ("marston_5th_floor_view", (-62.5, -76.4, 20.4), (-30.0, -20.0, 22.0), (-62.5, -71.4, 18.0, 31.0), 55.0),
        ("marston_west_reading", (-66.0, -99.0, 21.2), (-86.0, -101.0, 19.0), (-70.0, -100.0, 18.0, 270.0), 52.0),
        ("marston_porch", (-62.0, -62.0, 2.6), (-63.0, -80.0, 2.2), (-67.2, -72.5, 0.0, 180.0), 55.0),
        ("marston_cafe", (-74.6, -93.8, 2.6), (-79.0, -104.0, 1.0), (-77.0, -99.0, 0.0, 200.0), 52.0),
        ("marston_ne_stairs", (-50.6, -77.8, 15.2), (-46.0, -68.0, 13.0), (-49.5, -74.0, 12.6, 0.0), 58.0),
        ("marston_terrace", (-36.0, -122.0, 14.6), (-55.0, -100.0, 18.0), (-38.0, -112.0, 12.0, 330.0), 55.0),
        ("marston_roof", (-78.0, -104.5, 27.4), (-50.0, -78.0, 24.5), (-70.0, -96.0, 24.0, 45.0), 58.0),
        ("marston_makerspace", (-64.0, -97.5, -3.2), (-78.5, -103.0, -5.2), (-70.0, -100.0, -6.0, 250.0), 55.0),
        ("marston_chute", (-73.2, -80.8, -3.4), (-79.0, -77.0, -5.0), None, 60.0),
        # photo pass 2: the photographed viewpoints (reference/interiors/marston '#n')
        ("marston_service_desk", (-63.8, -96.8, 1.55), (-57.5, -89.5, 2.0), None, 52.0),            # #23
        ("marston_f2_benching", (-42.0, -93.2, 1.6), (-56.0, -95.6, 1.2), None, 52.0),              # #28
        ("marston_elevator_lobby_f1", (-79.6, -96.2, -4.5), (-72.5, -90.6, -4.4), None, 52.0),      # #69
        ("marston_commons_lounge", (-48.6, -108.6, -4.5), (-38.0, -98.5, -4.7), None, 52.0),        # #38
        ("marston_north_lab", (-78.4, -73.6, -4.1), (-78.4, -55.0, -5.2), None, 52.0),              # #61
        ("marston_l136", (-61.4, -116.2, -4.3), (-71.2, -121.6, -4.8), None, 56.0),                 # #47
        ("marston_l308", (-71.6, -106.9, 7.7), (-80.2, -99.0, 6.9), None, 54.0),                    # #78
        ("marston_f5_lounge", (-56.0, -88.4, 19.6), (-66.0, -72.0, 19.0), None, 52.0),              # #102
        ("marston_starbucks", (-79.2, -99.0, 1.6), (-76.4, -94.3, 1.9), None, 52.0),                # #35
    ]


# ================================================================== lighting (per group)
def lighting(M):
    """interior_kit.Lighting per kit group (the bake): warm interior floors, a cool basement, daylight
    outdoors; every group sees all lights (troffers, stair halls, the chandelier, the atrium daylight)
    plus a daylight point light inside every window band."""
    lights = M.kit.lights()
    for fid, a, b, s0, s1, oz0, oz1 in M.daylight:
        L = math.dist(a, b)
        dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        ix, iy = -dy, dx
        n = max(1, int(round((s1 - s0) / 3.0)))
        for k in range(n):
            s = s0 + (s1 - s0) * (k + 0.5) / n
            lights.append(K.Light((a[0] + dx * s + ix * 1.4, a[1] + dy * s + iy * 1.4, Z[fid] + (oz0 + oz1) / 2),
                                  radius=5.5, strength=0.22, color=(0.92, 0.97, 1.0)))
    # photo pass 2: brighter ambient (the photos' white ceilings read ~0.8; the old bake left them ~0.55 grey)
    warm = dict(sky=(0.78, 0.76, 0.72), ground=(0.60, 0.58, 0.55), key_strength=0.10)
    out = {g: K.Lighting(lights, **warm) for g in ("F2", "F3", "F4", "F5", "atrium", "towers")}
    out["F1"] = K.Lighting(lights, sky=(0.74, 0.77, 0.80), ground=(0.64, 0.66, 0.70), key_strength=0.10)
    out["roof"] = K.Lighting(lights, sky=(0.92, 0.92, 0.94), ground=(0.68, 0.68, 0.70), key_strength=0.22)
    out["backdrop"] = K.Lighting([], sky=(0.95, 0.95, 0.96), ground=(0.70, 0.70, 0.70), key_strength=0.22)
    M.lighting = out
    M.stats["lights"] = len(lights)
    return out


# ================================================================== the build
def build(layout=None, campus=None, backdrop=True):
    """-> Marston: the whole stage as an interior_kit.Kit (groups F1..F5, roof, towers, atrium, backdrop)."""
    layout = layout or load_layout()
    M = Marston(layout)
    for fid in FLOORS:
        M.regions[fid] = regions_of(M, fid)
    for fid in FLOORS:
        M.coffers[fid] = coffer_cells(M, fid)
    register_footprints(M)
    plan_doors(M)
    for fid in FLOORS:
        build_floor(M, fid)
    build_roof(M)
    build_ne_hall(M)
    build_sw_hall(M)
    build_core(M)
    build_atrium(M)
    build_chute_and_duct(M)
    build_light_well(M)
    build_porch(M)
    if backdrop:
        build_backdrop(M, campus)
    plan_pickups(M)
    place_dressing(M)
    clean_collision(M)
    marston_finishes(M)
    brick_uvs(M)
    fix_uv_spans(M)
    coplanar_report(M, gap=0.004)        # fix round 5: z-fighting guard (stats["coplanar_overlap"])
    plan_points(M)
    plan_views(M)
    lighting(M)
    return M


# photo pass 2: the generic kit / helper finishes swapped for Marston's own after the build (the helpers keep the kit
# defaults because interiors/libwest.py reuses them and must build exactly as before)
FINISH_SWAP = {"int_drywall": "int_ms_wall", "int_ceiling": "int_ms_tile"}


def marston_finishes(M):
    """Swap the generic wall paint / ceiling tile on every Marston face for the photographed ones (FINISH_SWAP)."""
    n = 0
    for _, _, pr in M.kit.items:
        for p in pr.visual.polys:
            m = FINISH_SWAP.get(p.mat)
            if m:
                p.mat = m
                n += 1
    M.stats["finish_swaps"] = n


def clean_collision(M, eps=0.004):
    """Fix round 5: drop the collision wall faces that lie on another wall face's plane, inside it.
      (a) back to back (opposite normals): a face covered by opposite faces of a bigger total area is the back of a
          prop / box set flush against a wall (or a shaft wall's end against the front wall pieces); its front is
          inside that wall. In the air the walls push the vanilla way (each push from the same start position, so
          they add up), and such a hidden back face threw a jumping player through the wall in front of it (the F2
          vestibule wall: +84 units into the void behind). Equal pairs stay (a zero-thickness divider needs both
          faces on the ground).
      (b) same facing: a duplicate inside a bigger (or equal) face pushes an airborne player twice. A 'COL default'
          face is not dropped for a 'COL nocam' one (the camera would pass); the count of those is kept in stats."""
    by_plane = {}
    for ii, (_, _, pr) in enumerate(M.kit.items):
        for pi_, p in enumerate(pr.collision.polys):
            if p.mat not in (K.COL, K.COL_NOCAM, "COL notslip", "COL hangable"):
                continue
            n = K.unit_normal(p.pts)
            if abs(n[2]) > 0.01 or math.hypot(n[0], n[1]) < 0.99:
                continue
            nx, ny = n[0], n[1]
            sg = 1 if (nx > 1e-6 or (abs(nx) <= 1e-6 and ny > 0)) else -1
            cx_, cy_ = nx * sg, ny * sg
            d = cx_ * p.pts[0][0] + cy_ * p.pts[0][1]
            uz = [(-cy_ * q[0] + cx_ * q[1], q[2]) for q in p.pts]
            area = abs(signed_area(uz))
            box = bbox(uz)
            rect = len(p.pts) == 4 and abs((box[2] - box[0]) * (box[3] - box[1]) - area) < 1e-4
            key = (round(cx_, 3), round(cy_, 3), round(d / eps))
            by_plane.setdefault(key, []).append({"id": (ii, pi_), "sg": sg, "box": box, "area": area, "rect": rect,
                                                 "mat": p.mat, "uz": uz})

    def inside(b, q, e=eps):
        return b[0] - e <= q[0] <= b[2] + e and b[1] - e <= q[1] <= b[3] + e

    def overlaps(a, b):
        return a[0] < b[2] - eps and b[0] < a[2] - eps and a[1] < b[3] - eps and b[1] < a[3] - eps
    drop = set()
    kept_mixed = n_back = n_dup = 0
    for lst in by_plane.values():
        if len(lst) < 2:
            continue
        for a in sorted(lst, key=lambda f: f["area"]):
            if a["id"] in drop:
                continue
            opp = [b for b in lst if b["sg"] != a["sg"] and b["rect"] and b["id"] not in drop and
                   overlaps(a["box"], b["box"])]
            if opp and sum(b["area"] for b in opp) > a["area"] + 1e-4:
                bx = a["box"]
                samples = [(bx[0] + (bx[2] - bx[0]) * (i + 0.5) / 6, bx[1] + (bx[3] - bx[1]) * (j + 0.5) / 6)
                           for i in range(6) for j in range(6)]
                samples = [q for q in samples if pip(q, a["uz"])] + [(u + (0.002 if u < (bx[0] + bx[2]) / 2 else -0.002),
                                                                      z + (0.002 if z < (bx[1] + bx[3]) / 2 else -0.002))
                                                                     for u, z in a["uz"]]
                if all(any(inside(b["box"], q) for b in opp) for q in samples):
                    drop.add(a["id"])
                    n_back += 1
                    continue
            for b in lst:
                if b["id"] == a["id"] or b["id"] in drop or not b["rect"] or b["sg"] != a["sg"]:
                    continue
                ba, bb = a["box"], b["box"]
                if not (inside(bb, (ba[0], ba[1])) and inside(bb, (ba[2], ba[3]))):
                    continue
                if a["mat"] == K.COL and b["mat"] == K.COL_NOCAM:
                    kept_mixed += 1
                    continue
                if b["area"] > a["area"] + 1e-4 or (abs(b["area"] - a["area"]) <= 1e-4 and a["id"] > b["id"]):
                    drop.add(a["id"])
                    n_dup += 1
                    break
    for ii, (_, _, pr) in enumerate(M.kit.items):
        if any(k[0] == ii for k in drop):
            pr.collision.polys = [p for pi_, p in enumerate(pr.collision.polys) if (ii, pi_) not in drop]
    M.stats["collision_clean"] = {"back_to_back_dropped": n_back, "doubled_dropped": n_dup,
                                  "default_inside_nocam_kept": kept_mixed}


def coplanar_report(M, gap=0.004, top=8):
    """Fix round 5 check: visual faces of different materials that lie on one plane (within `gap` m: one export unit
    after rounding) facing the same way and overlap z-fight in game. -> {"m2": total overlap, "pairs": n,
    "worst": [(m2, materials, centre)]} over the stage (the backdrop excluded). Overlap areas are sampled (6 x 6)."""
    polys = []
    for _, g, pr in M.kit.items:
        if g == "backdrop":
            continue
        for p in pr.visual.polys:
            n = K.unit_normal(p.pts)
            if K._len(n) < 0.5:
                continue
            ax = max(range(3), key=lambda k: abs(n[k]))
            a, b = [k for k in range(3) if k != ax]
            q = [(v[a], v[b]) for v in p.pts]
            polys.append((n, sum(n[k] * p.pts[0][k] for k in range(3)), ax, q, bbox(q), p.mat, p.pts))
    buckets = {}
    for i, (n, d, ax, q, bx, mat, pts) in enumerate(polys):
        buckets.setdefault((round(n[0], 2), round(n[1], 2), round(n[2], 2), round(d / gap)), []).append(i)
    found = []
    seen = set()
    for key, lst in buckets.items():
        cand = list(lst)
        for dk in (-1, 1):
            cand += buckets.get((key[0], key[1], key[2], key[3] + dk), [])
        cand.sort(key=lambda i: polys[i][4][0])
        for x, i in enumerate(cand):
            if i not in lst:
                continue
            bi = polys[i][4]
            for j in cand[x + 1:]:
                bj = polys[j][4]
                if bj[0] >= bi[2]:
                    break
                if (min(i, j), max(i, j)) in seen or polys[i][5] == polys[j][5]:
                    continue
                if abs(polys[i][1] - polys[j][1]) > gap or bj[1] >= bi[3] or bi[1] >= bj[3]:
                    continue
                seen.add((min(i, j), max(i, j)))
                s, o = (i, j) if abs(signed_area(polys[i][3])) <= abs(signed_area(polys[j][3])) else (j, i)
                qs, bs = polys[s][3], polys[s][4]
                pts_ = [(bs[0] + (bs[2] - bs[0]) * (u + 0.5) / 6, bs[1] + (bs[3] - bs[1]) * (v + 0.5) / 6)
                        for u in range(6) for v in range(6)]
                pts_ = [pt for pt in pts_ if pip(pt, qs)]
                if not pts_:
                    continue
                hit = sum(1 for pt in pts_ if pip(pt, polys[o][3]))
                ar = abs(signed_area(qs)) * hit / len(pts_) / max(1e-6, abs(polys[s][0][polys[s][2]]))
                if ar > 0.01:
                    c = tuple(round(sum(v[k] for v in polys[s][6]) / len(polys[s][6]), 1) for k in range(3))
                    found.append((ar, tuple(sorted((polys[i][5], polys[j][5]))), c))
    found.sort(reverse=True)
    rep = {"m2": round(sum(f[0] for f in found), 2), "pairs": len(found),
           "worst": [(round(f[0], 2), f[1], f[2]) for f in found[:top]]}
    M.stats["coplanar_overlap"] = rep
    return rep


UV_LIMIT = 10.0          # max texture repeats across a face (interior_kit.UV_SPAN_MAX 12 with margin)


def _poly_uvs(p):
    return p.uvs or K.project_uv(p.pts, K.palette_entry(p.mat)["tile_m"], K.newell(p.pts))


def _span(uvs):
    return max(max(u for u, _ in uvs) - min(u for u, _ in uvs), max(v for _, v in uvs) - min(v for _, v in uvs))


def _split_poly(p, axis, cut):
    """Split a convex polygon by the plane coordinate[axis] = cut -> two Polys (explicit UVs, AO interpolated)."""
    uvs = p.uvs
    lo, hi = [], []
    n = len(p.pts)
    for i in range(n):
        a, b = p.pts[i], p.pts[(i + 1) % n]
        ua = uvs[i] if uvs else None
        ub = uvs[(i + 1) % n] if uvs else None
        aa, ab = p.ao[i], p.ao[(i + 1) % n]
        da, db = a[axis] - cut, b[axis] - cut
        (lo if da <= 0 else hi).append((a, ua, aa))
        if (da < 0 < db) or (db < 0 < da):
            t = da / (da - db)
            q = tuple(a[k] + (b[k] - a[k]) * t for k in range(3))
            uq = None if ua is None else (ua[0] + (ub[0] - ua[0]) * t, ua[1] + (ub[1] - ua[1]) * t)
            aq = aa + (ab - aa) * t
            lo.append((q, uq, aq))
            hi.append((q, uq, aq))
    out = []
    for part in (lo, hi):
        if len(part) < 3:
            continue
        pts = [v[0] for v in part]
        if K._len(K.newell(pts)) < 1e-8:
            continue
        pu = None
        if uvs:
            pu = [v[1] for v in part]
            du = math.floor(min(u for u, _ in pu))
            dv = math.floor(min(v for _, v in pu))
            pu = [(u - du, v - dv) for u, v in pu]
        out.append(K.Poly(pts, p.mat, pu, [v[2] for v in part], p.tint, p.glow))
    return out


def fix_uv_spans(M, limit=UV_LIMIT):
    """Split every visual face whose texture span exceeds `limit` repeats (long rails, fascias, landings,
    tall pillars, long desks, road ribbons) along its longest extent until it fits; also shifts explicit
    UVs by whole repeats so N64 texture coordinates stay small."""
    n_split = 0
    for _, _, pr in M.kit.items:
        out = []
        stack = list(pr.visual.polys)
        while stack:
            p = stack.pop()
            if _span(_poly_uvs(p)) <= limit or len(p.pts) > 12:
                if p.uvs:
                    du = math.floor(min(u for u, _ in p.uvs))
                    dv = math.floor(min(v for _, v in p.uvs))
                    if du or dv:
                        p = K.Poly(p.pts, p.mat, [(u - du, v - dv) for u, v in p.uvs], p.ao, p.tint, p.glow)
                out.append(p)
                continue
            ext = [max(v[k] for v in p.pts) - min(v[k] for v in p.pts) for k in range(3)]
            axis = max(range(3), key=lambda k: ext[k])
            cut = (max(v[axis] for v in p.pts) + min(v[axis] for v in p.pts)) / 2
            parts = _split_poly(p, axis, cut)
            if len(parts) < 2:
                out.append(p)
                continue
            n_split += 1
            stack.extend(parts)
        pr.visual.polys = out
    M.stats["uv_splits"] = n_split


def build_light_well(M):
    """The basement's west windows look into a sunken planted light well (under the F2 Starbucks slab):
    a planter bed, a concrete back wall and end walls and a glowing daylight slot at the top. Visual only.
    Fix round 2: the back wall faces the glass (it faced away: the skybox showed through the windows), the well
    stops at the SW stair hall's north wall (it ran 7 m into the hall, through its stair), and both ends are
    closed, so no view through the glazing reaches the void."""
    P = K.Prop("light_well", col_closed=True)
    V = P.visual
    x0, x1 = -82.3, SW_RECT_F1[2] - WALL_T                 # back wall .. the F1 west wall's outer face (-80.5)
    y0, y1 = SW_RECT_F1[3] + WALL_T, -97.3                 # the SW hall's north wall (outer face) .. past the glass
    z0, ztop = Z["F1"], Z["F2"] - SLAB
    V.box(x0, y0, z0, x1, y1, z0 + 1.2, "int_stone", faces="+z+x", tint=(0.8, 0.78, 0.72))
    V.poly([(x0, y0, z0 + 1.21), (x1, y0, z0 + 1.21), (x1, y1, z0 + 1.21), (x0, y1, z0 + 1.21)], "leaves_oak", ao=1.0)
    n = 4
    for k in range(n):
        y = y0 + (k + 0.5) * (y1 - y0) / n
        V.box(x0 + 0.3, y - 0.5, z0 + 1.2, x0 + 1.1, y + 0.5, z0 + 2.4 + 0.3 * (k % 2), "leaves_oak2",
              faces="+x-x+y-y+z", ao=1.0)
    V.wall((x0, y0), (x0, y1), z0, ztop, "concrete", ao=1.0)          # back wall, facing east (the glass)
    V.wall((x1, y0), (x0, y0), z0, ztop, "concrete", ao=0.9)          # south end, facing north
    V.wall((x0, y1), (x1, y1), z0, ztop, "concrete", ao=0.9)          # north end, facing south
    V.poly([(x0, y0, ztop - 0.05), (x0, y1, ztop - 0.05), (x1, y1, ztop - 0.05), (x1, y0, ztop - 0.05)],
           "int_light", uvs=[(0, 0), (0, 4), (1, 4), (1, 0)], glow=True, tint=(0.92, 0.97, 1.0))
    M.add(P, 0.0, 0.0, 0.0, 0.0, tag="light_well", group="F1")


# ================================================================== checks (pure Python)
def report(M):
    rep = M.kit.report()
    by_group = {}
    for it in rep["items"]:
        g = by_group.setdefault(it["group"], {"visual": 0, "collision": 0})
        g["visual"] += it["visual"]
        g["collision"] += it["collision"]
    return {"total": rep["total"], "by_group": by_group}


def selftest(verbose=True):
    errors = []
    M = build(backdrop=True)
    rep = report(M)
    if verbose:
        print(json.dumps(rep, indent=1))
        print("doors:", {k: len(v) for k, v in M.doors.items()}, "sealed:", M.notes.get("sealed_rooms"))
        print("stats:", json.dumps(M.stats))
        print("unplaced:", M.notes.get("unplaced_props"))
    col = rep["total"]["collision"]
    if col > 16000:
        errors.append(f"collision {col} tris (budget: <= ~20k per area; this stage aims under 16k)")
    for poly in (p for _, _, pr in M.kit.items for p in pr.visual.polys):
        if not K.known_material(poly.mat):
            errors.append(f"unknown material {poly.mat}")
            break
    for _, _, pr in M.kit.items:
        for poly in pr.collision.polys:
            if poly.mat not in K.COL_NAMES + (COL_SLIDE,):
                errors.append(f"{pr.kind}: collision material {poly.mat}")
                break
    # every coordinate inside s16 after the centre shift
    worst = 0.0
    for _, _, pr in M.kit.items:
        for poly in pr.visual.polys + pr.collision.polys:
            for x, y, z in poly.pts:
                worst = max(worst, abs(x - CENTER[0]), abs(y - CENTER[1]), abs(z))
    if worst > 300.0:
        errors.append(f"a vertex is {worst:.1f} m from the centre")
    issues = []
    for _, _, pr in M.kit.items:
        issues += K.uv_span_issues(pr.visual)
    if issues:
        errors.append(f"{len(issues)} faces exceed the UV span: {issues[:3]}")
    # fix round 5: coplanar same-facing faces of different materials (z-fighting). Small props keep a few dm2 here and
    # there (frames, posts); a whole wall's worth (round 5 had 78 m2 of brick on paint) fails the test
    cop = M.stats.get("coplanar_overlap", {})
    if cop.get("m2", 0.0) > 15.0:
        errors.append(f"{cop['m2']} m2 of coplanar faces of different materials (z-fighting), e.g. {cop['worst'][:3]}")
    if verbose:
        print(f"max |coord| from centre: {worst:.1f} m; selftest:", "OK" if not errors else errors)
    return errors


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(1 if selftest() else 0)
    print(__doc__)
