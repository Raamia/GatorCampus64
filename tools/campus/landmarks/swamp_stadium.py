"""Ben Hill Griffin Stadium ("The Swamp"): hand-modelled hero landmark of the Swamp stage.

Landmark module contract (landmarks/_common.py): LANDMARKS + build(ctx). Geometry is authored in a
local stadium frame and returned in MAP METRES, z up (x = east, y = north, origin = Century Tower):
local (u, v) = (across the field to the east, along the field to the north), origin = the field
centre (-514.28, 122.98), long axis bearing 0.3 degrees (fitted to OSM w119378491). Built only into
the "swamp" stage ("stages": ["swamp"]).

SOURCES (heights; see the report for links)
  - OSM relation 1640985 / outer way 45719890 (footprint), field w119378491 (height=-10), building:part
    ways (tier outlines + mapper heights: lower stands 24, west skybox tower 52-66 "7 levels", Bull
    Gator Deck 44-52, Sunshine Seats 24-46, video boards 46-56 S / 48-58 N), light masts (n8001637276..,
    height 38, three freestanding behind the east stands).
  - Wikipedia "Ben Hill Griffin Stadium" / StadiumDB: built in a sinkhole, ~30-32 rows below the
    surrounding grade -> field 10 m below grade (= OSM -10).
  - Thornton Tomasetti (2026 renovation): the new suite frames are ~84 ft (25.6 m) high "rising from
    ground level to the top of the existing seating bowl, then extending higher" -> the east / south
    bowl tops out a bit under 25.6 m above grade (the OSM 24-44 m "upper deck" on the east is not
    supported by any source; modelled as one deep bowl).
  - D.H. Griffin (2003 press box tower renovation): a 7-storey west press box / skybox tower.
  - floridagators.com / sportsvideo.org 2009: Daktronics boards 136 x 30 ft (south) and 71 x 24 ft
    (north) "atop the upper deck of both end zones" (the OSM board parts are 42 m / 22 m wide).
  - NCAA field: 160 x 360 ft, end zones 10 yd, crossbar 10 ft, uprights 18 ft 6 in apart, 30 ft tall.

MODEL (gameplay simplification; all heights relative to the surrounding grade, z = 0)
  Field -10 m (68 x 124 m turf ring, NCAA field painted, "THE SWAMP" end zones, goalposts, pylons),
  1.2 m padded field wall. LOWER BOWL (360 deg): 18 chunky steps (0.49 x 0.9 m) up to a 2.5 m
  cross-aisle AT GRADE (z 0, gates arrive here), then steps 0.5 x 0.91 m. The steps are visual; the
  collision is one ramp per band through the step nosings (28.5 / 28.7 deg: run up, jump normally;
  visual treads are never above the collision, so Mario's shadow stays visible). EAST, SOUTH, WEST:
  the bowl continues to a 20 m rim walkway (40 steps above the aisle) with a 1 m parapet (outer wall
  21 m). NORTH: the bowl stops at a 7 m promenade under the Sunshine Seats (an upper deck: 22 m front
  walkway, 26 steps 0.6 x 0.92 m = 33 deg, rim 37.6 m) with the Touchdown Terrace glass wall below.
  NE / NW corners are open (as in OSM): corner plazas at grade with stairs to the promenade and steel
  bridges from the east / west rim to the Sunshine front walkway, so the 20-22 m level is one loop.
  WEST: the press box / skybox tower (OSM footprint, 66 m roof): glass suites over the rim, the Bull
  Gator Deck terrace at 44 m (8.9 m cantilever), the press box (52-66 m) and four light frames on the
  roof (71 m). SOUTH: the South Ramp block (OSM width, terrace at 20 m = rim) with one long exterior
  ramp from grade, and the 41.5 x 9.1 m video board on two legs (46.5-55.6 m) with a ledge ladder up
  the east leg, a catwalk (44 m) and service ledges on its back. NORTH: the 21.6 x 7.3 m board on
  the Sunshine rim (40.5-47.8 m: lower than OSM's 48-58 because the deck is), two helix ramps (OSM
  circles, grade -> 22 m) into vomitories under the Sunshine Seats, the north gatehouse, the loading
  block (NW) and the Gator Sportshop (NE). EAST: three 38 m light masts with catwalks.
  Tunnels (portals cut through the steps, hood platforms over the mouths): south field tunnel
  (field -> grade at the South Ramp), gates at grade into the cross-aisle (E x2, SE, SW, W "Heisman"
  gate through the tower, N gatehouse, NE / NW corners) and the two Sunshine vomitories (22 m).

GAMEPLAY (game_design.md section 7.1 + lead brief; positions in LANDMARKS[0]["spots"] / "markers")
  Act 1 Kickoff: rim (20) -> 11 ledges on the tower's south bay (2 m apart) -> Bull Gator Deck (44)
  -> 10 camera decks (2 m apart) -> press box roof (66) -> light frames (71). climb_route_m lists it.
  Act 2 mascot: the open field. Act 3 spirit pads: north cross-aisle facing the south board.
  End-zone corner buttons: the four end-line corners (field level, nothing else there). Field goal:
  uprights at both end lines (collision posts + crossbar), tee spots on the 20 / 30 yd lines.
  Races: the apron loop around the field and the stair sprint (north end zone -> east stands -> south
  terrace). Act 6: Wing Cap box on top of the south board (reachable without Lua: terrace -> 11 leg
  ledges -> catwalk -> 5 back ledges -> top, markers["scoreboard_climb_m"]); rings over the bowl.
  Poles (Lua bhvPoleGrabbing objects; all <= 25.5 m): markers["poles"].

GENERATOR NOTES (also in the build report)
  "ground_holes_m": the field sits 10 m below the generator's z = 0 collision ground, so the ground
  (collision AND every visual ground layer) must be cut out inside these rings (the bowl at the
  cross-aisle's outer edge + the south field tunnel's slot), like the pond holes. Inside them this
  module provides every floor.
  Materials: palette names from _common.PALETTE plus generator materials (stage_palette: banner_orange,
  banner_blue, facade_brick, facade_band, facade_glass, road_paint, ground_grass, lawn, sidewalk, ...)
  when stage_palette is importable (it is inside the generator); otherwise palette fallbacks.

Parts: "stadium visual" (visual), "stadium field" (visual, field paint below the field collision
floor), "stadium collision" (collision only), all with "landmark": "stadium". Budgets (stages.json
swamp landmark r1640985/45719890): 2600 collision / 9000 visual triangles; build() prints the counts
(this version: ~1700 collision / ~6700 visual).
Map data (c) OpenStreetMap contributors, ODbL 1.0.
"""
import math
import os
import sys

try:
    from landmarks import _common as C
except ImportError:  # imported as a top-level module: make the `landmarks` package importable
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from landmarks import _common as C

SLUG = "stadium"           # parts "stadium visual" / "stadium field" / "stadium collision"
STADIUM_ID = "r1640985/45719890"
# OSM building:part ways inside the relation (the generator skips parts anyway; listed so the build
# report shows what this module stands for)
PART_IDS = ["w857073724", "w857073737", "w857391715", "w857391718", "w858341222", "w858341223",
            "w858341224", "w858341225", "w858341226", "w858341227", "w858341228", "w858341232",
            "w858341236", "w858341237", "w858371792", "w858371793", "w859154006", "w859154007"]
FIELD_AREA_ID = "w119378491"
# OSM areas inside the bowl (drawn by this module, below grade): the pitch, the south field-level apron,
# four bleacher strips at the south field edge
INNER_AREA_IDS = ["w119378491", "w858341244", "w858341238", "w858341239", "w858341240", "w858341241"]
# hedges at the south field edge (would float at z 0 over the sunken field) and a short wall in the
# NW open corner (where the corner stairs are)
INNER_WAY_IDS = ["w1349061689", "w1349061690", "w858476067"]

EPS = 1e-6

# =================================================================== frame
CX, CY = -514.28, 122.98          # field centre (map metres)
BEARING_DEG = 0.3                 # long axis bearing (north = 0)
_B = math.radians(BEARING_DEG)
EX = (math.cos(_B), -math.sin(_B))   # local +u (east) in map coordinates
EY = (math.sin(_B), math.cos(_B))    # local +v (north)


def to_map(u, v):
    return (CX + u * EX[0] + v * EY[0], CY + u * EX[1] + v * EY[1])


def to_local(x, y):
    dx, dy = x - CX, y - CY
    return (dx * EX[0] + dy * EX[1], dx * EY[0] + dy * EY[1])


def bearing_of(du, dv):
    """Compass bearing (map) of a local direction."""
    x = du * EX[0] + dv * EY[0]
    y = du * EX[1] + dv * EY[1]
    return round(math.degrees(math.atan2(x, y)) % 360.0, 1)


# =================================================================== dimensions (metres)
A0, B0, R0 = 33.6, 62.1, 12.0     # field ring half sizes (OSM pitch 67.2 x 124.3) + corner radius
Z_FIELD = -10.0
Z_WALLTOP = -8.8                  # 1.2 m padded field wall
# lower band L1: field wall -> cross-aisle at grade
L1_N, L1_T = 18, 0.9
L1_R = (0.0 - Z_WALLTOP) / L1_N   # 0.489 m
D_AISLE0 = L1_N * L1_T            # 16.2: last L1 riser = front edge of the cross-aisle
D_AISLE1 = 18.7                   # back edge of the flat cross-aisle = ground hole edge
# main band (L2 + upper horseshoe): cross-aisle -> rim
H_N, H_R = 40, 0.5
D_RIM0 = 55.2                     # last riser = front of the rim walkway
H_T = (D_RIM0 - D_AISLE1) / H_N   # 0.9125 m (28.7 deg)
Z_RIM = H_N * H_R                 # 20.0
D_RIM1, D_OUT = 57.7, 58.3        # parapet inner / outer face (outer wall)
Z_PARAPET = Z_RIM + 1.0
# north: the bowl stops at the promenade (7 m) under the Sunshine Seats
N_LOW = 14
Z_PROM = N_LOW * H_R              # 7.0
D_PROM0 = D_AISLE1 + N_LOW * H_T  # 31.475
D_PROM1 = D_PROM0 + 3.0           # 34.475: Touchdown Terrace wall / corner retaining wall
# Sunshine Seats (north upper deck)
D_SUN_F = 17.0                    # front fascia
D_SUN0 = 19.5                     # front walkway back edge = first riser
Z_SUN = 22.0
SUN_N, SUN_R = 26, 0.6
D_SUN_RIM0 = 43.5
SUN_T = (D_SUN_RIM0 - D_SUN0) / SUN_N   # 0.923 m (33 deg: walkable, a steep-jump slope)
Z_SUN_TOP = Z_SUN + SUN_N * SUN_R       # 37.6
D_SUN_RIM1, D_SUN_OUT = 46.0, 46.6      # back wall = OSM Sunshine outer edge (v 108.7)
Z_SUN_SOFFIT = 20.5
# west tower
Z_BGD = 44.0                      # Bull Gator Deck floor
U_BGD = -83.0                     # BGD front edge (OSM -82.5)
V_BGD = 45.0                      # BGD / press box cantilever half length
Z_PB0, Z_ROOF = 52.0, 66.0        # press box / skybox
U_PB = -86.0                      # press box front (OSM -85.6)
# south block (South Ramp) + video boards
V_SBLOCK = -124.4                 # south face of the South Ramp block (ramp in front to -128.4)
V_SRAMP = -128.4
U_SBLOCK = 53.5                   # OSM South Ramp (w858341236) half width
SB = {"w": 41.5, "h": 9.1, "z0": 46.5, "v0": -116.0, "v1": -119.5}    # south board (136 x 30 ft)
NB = {"w": 21.6, "h": 7.3, "z0": 40.5, "v0": 106.2, "v1": 108.7}      # north board (71 x 24 ft)
# NCAA field
FOP_HW = 24.384                   # half width (160 ft)
GOAL_V = 45.72                    # goal lines (50 yd)
END_V = 54.864                    # end lines (60 yd)
YD5 = 4.572
CROSSBAR_Z = Z_FIELD + 3.048
UPRIGHT_HALF = 2.82 + 0.1         # 18 ft 6 in inside + half post
UPRIGHT_TOP = CROSSBAR_Z + 9.144
# tunnels
GATE_W, GATE_H, SLAB = 2.5, 4.0, 0.5      # half width, clear height, hood slab
WALL_T = 0.6

# segments of a 12-vertex ring (corner arcs as two 45-degree chords), counter-clockwise
SEGS = ["NEa", "NEb", "N", "NWa", "NWb", "W", "SWa", "SWb", "S", "SEa", "SEb", "E"]
SI = {n: i for i, n in enumerate(SEGS)}
CORNERS = [((A0 - R0), (B0 - R0), 0.0), (-(A0 - R0), (B0 - R0), 90.0),
           (-(A0 - R0), -(B0 - R0), 180.0), ((A0 - R0), -(B0 - R0), 270.0)]
H_SEGS = ("E", "SEa", "SEb", "S", "SWa", "SWb", "W")     # bowl rises to the 20 m rim
N_SEGS = ("NEa", "NEb", "N", "NWa", "NWb")               # bowl stops at the 7 m promenade
SUN_SEGS = ("NEb", "N", "NWa")                           # Sunshine Seats + Touchdown Terrace
OPEN_SEGS = ("NEa", "NWb")                               # open corners
TERRACE_SEGS = ("SWb", "S", "SEa")                       # rim merges with the South Ramp terrace


# =================================================================== materials
def _material_table():
    table = {k: dict(v) for k, v in C.PALETTE.items()}
    try:
        import stage_palette as _sp   # generator materials (merged into the generator's S.mats)
        for k, v in _sp.MATERIALS.items():
            table.setdefault(k, dict(v))
    except Exception:  # noqa: BLE001 - palette-only fallbacks
        pass
    return table


MATS = _material_table()
ROLE_PREFS = {
    "turf": ("grass",), "turf2": ("lawn", "grass"), "apron": ("ground_grass", "grass"),
    "line": ("white_trim",), "orange": ("banner_orange", "roof_tile_red"),
    "blue": ("banner_blue", "window_dark"), "tread": ("metal_gray",),
    "riser_lo": ("banner_blue", "window_dark"), "riser_hi": ("banner_orange", "roof_tile_red"),
    "concrete": ("concrete",), "brick": ("facade_brick", "brick_red"), "band": ("facade_band", "brick_red"),
    "brick_plain": ("brick_red",), "glass": ("facade_glass", "window_glass"), "window": ("window_glass",),
    "dark": ("dark_trim",), "screen": ("window_dark",), "metal": ("metal_gray",), "white": ("white_trim",),
    "roof": ("roof_gravel", "roof_dark"), "goalpost": ("road_paint", "limestone"),
    "paving": ("sidewalk", "concrete"), "service": ("facade_service", "brick_red"),
    "deck": ("plaza_brick", "concrete"),
}
SOLID_V = {"banner_orange": 0.62, "banner_blue": 0.62}   # texel row inside the solid colour area
SOLID_HEM_V = 0.984     # the banner textures' darker hem rows (75 %; make_textures.tx_banner): bowl risers
UV_SPAN = 11.0          # max texture repeats across one face (contract: keep under ~12)


def mat(role):
    for n in ROLE_PREFS[role]:
        if n in MATS:
            return n
    raise KeyError(role)


def tile_of(m):
    return float(MATS[m].get("tile_m", 2.0))


# =================================================================== geometry collector
def newell(pts):
    nx = ny = nz = 0.0
    for (x1, y1, z1), (x2, y2, z2) in zip(pts, pts[1:] + pts[:1]):
        nx += (y1 - y2) * (z1 + z2)
        ny += (z1 - z2) * (x1 + x2)
        nz += (x1 - x2) * (y1 + y2)
    return (nx, ny, nz)


class Geo:
    """Polygons in LOCAL stadium coordinates (u, v, z) with a material name and UVs."""

    def __init__(self, name):
        self.name = name
        self.polys = []

    def add(self, pts, m, uvs=None, hint=None):
        pts = [tuple(float(c) for c in p) for p in pts]
        # drop repeated points
        clean, cuv = [], []
        for i, p in enumerate(pts):
            if clean and max(abs(p[k] - clean[-1][k]) for k in range(3)) < 1e-5:
                continue
            clean.append(p)
            if uvs is not None:
                cuv.append(uvs[i])
        if len(clean) > 2 and max(abs(clean[0][k] - clean[-1][k]) for k in range(3)) < 1e-5:
            clean.pop()
            if uvs is not None:
                cuv.pop()
        if len(clean) < 3:
            return
        n = newell(clean)
        if math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2) < 1e-7:
            return
        if hint is not None and n[0] * hint[0] + n[1] * hint[1] + n[2] * hint[2] < 0:
            clean.reverse()
            if uvs is not None:
                cuv.reverse()
        if m not in MATS:
            raise ValueError(f"unknown material {m!r}")
        self.polys.append((clean, m, cuv if uvs is not None else None))

    def tris(self):
        return sum(len(p[0]) - 2 for p in self.polys)

    # ---------------------------------------------------------- shapes
    def quad(self, p0, p1, p2, p3, m, hint, uvs=None, mode=None):
        pts = [p0, p1, p2, p3]
        self.add(pts, m, uvs if uvs is not None else auto_uv(pts, m, hint, mode), hint)

    def poly(self, pts, m, hint, mode=None):
        self.add(pts, m, auto_uv(pts, m, hint, mode), hint)

    def wall(self, a, b, z0, z1, m, out, mode=None, tile=None):
        """Vertical quad over the 2D segment a -> b, facing the 2D direction `out` (long walls are
        split so a tiled facade keeps its scale under the UV span limit)."""
        hint = (out[0], out[1], 0.0)
        t = tile or tile_of(m)
        L = math.dist(a, b)
        n = 1
        if mode not in ("stretch", "solid") and self.name != "collision":
            n = max(1, math.ceil(L / (t * (UV_SPAN - 1))))
        for k in range(n):
            pa = (a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n)
            pb = (a[0] + (b[0] - a[0]) * (k + 1) / n, a[1] + (b[1] - a[1]) * (k + 1) / n)
            pts = [(pa[0], pa[1], z0), (pb[0], pb[1], z0), (pb[0], pb[1], z1), (pa[0], pa[1], z1)]
            self.add(pts, m, auto_uv(pts, m, hint, mode, tile), hint)

    def flat(self, pts2, z, m, up=True, mode=None, tile=None):
        pts = [(p[0], p[1], z) for p in pts2]
        hint = (0.0, 0.0, 1.0 if up else -1.0)
        self.add(pts, m, auto_uv(pts, m, hint, mode, tile), hint)

    def box(self, u0, u1, v0, v1, z0, z1, m, faces="tbnsew", mats=None, mode=None):
        mats = mats or {}
        u0, u1 = sorted((u0, u1))
        v0, v1 = sorted((v0, v1))
        r = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
        if "t" in faces:
            self.flat(r, z1, mats.get("t", m), True, mode)
        if "b" in faces:
            self.flat(r, z0, mats.get("b", m), False, mode)
        if "s" in faces:
            self.wall((u0, v0), (u1, v0), z0, z1, mats.get("s", m), (0, -1), mode)
        if "n" in faces:
            self.wall((u0, v1), (u1, v1), z0, z1, mats.get("n", m), (0, 1), mode)
        if "e" in faces:
            self.wall((u1, v0), (u1, v1), z0, z1, mats.get("e", m), (1, 0), mode)
        if "w" in faces:
            self.wall((u0, v0), (u0, v1), z0, z1, mats.get("w", m), (-1, 0), mode)

    def prism(self, pts2, z0, z1, m, top=None, bottom=None, mode=None, tile=None):
        pts2 = C.ccw(list(pts2))
        for a, b in zip(pts2, pts2[1:] + pts2[:1]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            self.wall(a, b, z0, z1, m, (dy, -dx), mode, tile)
        if top:
            self.flat(pts2, z1, top, True)
        if bottom:
            self.flat(pts2, z0, bottom, False)


def auto_uv(pts, m, hint, mode=None, tile=None):
    """UVs in texture repeats. Floors: top-down. Walls: along the wall / height. mode "solid": a
    constant texel row (banner textures -> solid orange / blue). mode "stretch": walls with the
    texture stretched along (one repeat per 10 m) and one repeat over the face height."""
    t = tile or tile_of(m)
    n = hint if hint is not None else newell(pts)
    if abs(n[2]) >= max(abs(n[0]), abs(n[1])) * 1.0001:
        uvs = [(p[0] / t, p[1] / t) for p in pts]
    else:
        L = math.hypot(n[0], n[1]) or 1.0
        hx, hy = -n[1] / L, n[0] / L
        if mode == "stretch":
            zs = [p[2] for p in pts]
            z0, z1 = min(zs), max(zs)
            uvs = [((p[0] * hx + p[1] * hy) / 10.0, (p[2] - z0) / max(z1 - z0, 1e-6)) for p in pts]
        else:
            uvs = [((p[0] * hx + p[1] * hy) / t, p[2] / t) for p in pts]
    if mode == "solid":
        v = SOLID_V.get(m)
        if v is not None:
            uvs = [(u / 4.0, v) for u, _ in uvs]
    span = max(max(u for u, _ in uvs) - min(u for u, _ in uvs), max(v for _, v in uvs) - min(v for _, v in uvs))
    if span > UV_SPAN:
        k = UV_SPAN / span
        uvs = [(u * k, v * k) for u, v in uvs]
    du = math.floor(min(u for u, _ in uvs))
    dv = math.floor(min(v for _, v in uvs))
    return [(u - du, v - dv) for u, v in uvs]


# =================================================================== rings / segments
def ring(d):
    pts = []
    for cx, cy, a0 in CORNERS:
        for k in range(3):
            a = math.radians(a0 + 45.0 * k)
            pts.append((cx + (R0 + d) * math.cos(a), cy + (R0 + d) * math.sin(a)))
    return pts


def seg(i, d):
    """(p0, p1, mid, t, n, half) of segment i of the ring at offset d (n = outward normal)."""
    r = ring(d)
    p0, p1 = r[i], r[(i + 1) % 12]
    L = math.dist(p0, p1)
    t = ((p1[0] - p0[0]) / L, (p1[1] - p0[1]) / L)
    n = (t[1], -t[0])
    mid = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
    return p0, p1, mid, t, n, L / 2


def spt(i, d, s, z=None):
    """Point on segment i at offset d, along-coordinate s (from the segment midpoint)."""
    _, _, mid, t, _, _ = seg(i, d)
    p = (mid[0] + t[0] * s, mid[1] + t[1] * s)
    return p if z is None else (p[0], p[1], z)


def seg_normal(i):
    return seg(i, 0.0)[4]


def seg_dir(i):
    return seg(i, 0.0)[3]


def half(i, d):
    return seg(i, d)[5]


# =================================================================== portals (tunnels / gates)
class Portal:
    """A tunnel through a step band: mouth at d0 (band start), straight along the segment normal to
    d_exit. Rows below the hood are cut over |s - sc| < w (w = inner half width + wall)."""

    def __init__(self, name, segname, sc, d0, d_exit, floor0, floor1, height, band, w_in=GATE_W,
                 kind="gate", exit_wall=True):
        self.name, self.seg, self.i, self.sc = name, segname, SI[segname], sc
        self.d0, self.d_exit = d0, d_exit
        self.floor0, self.floor1 = floor0, floor1      # floor z at d0 / d_exit
        self.height, self.w_in, self.w = height, w_in, w_in + WALL_T
        self.kind, self.exit_wall = kind, exit_wall
        D0, Z0, n, t, r = band
        # hood: first row J whose tread clears the tunnel ceiling + slab
        J = None
        for j in range(1, n + 1):
            dj = D0 + j * t
            zj = Z0 + j * r
            if zj >= self.floor_at(dj) + height + SLAB - 1e-6:
                J = j
                break
        if J is None:
            raise ValueError(f"portal {name}: band too low")
        self.J, self.z_h, self.d_h = J, Z0 + J * r, D0 + J * t

    def floor_at(self, d):
        if abs(self.d_exit - self.d0) < EPS:
            return self.floor0
        k = (d - self.d0) / (self.d_exit - self.d0)
        return self.floor0 + (self.floor1 - self.floor0) * max(0.0, min(1.0, k))

    def ceil_at(self, d):
        return self.floor_at(d) + self.height


def cut_intervals(i, portals, row=None, d=None):
    """s-intervals of segment i cut by portals (for a row index of the portal's band, or for a
    plan offset d inside the hood)."""
    out = []
    for p in portals:
        if p.i != i:
            continue
        if row is not None and row > p.J:
            continue
        out.append((p.sc - p.w, p.sc + p.w))
    return sorted(out)


def pieces(lo, hi, cuts):
    """[lo, hi] minus the cut intervals -> list of (a, b)."""
    out = []
    a = lo
    for c0, c1 in cuts:
        if c1 <= a or c0 >= hi:
            continue
        if c0 > a + 1e-4:
            out.append((a, c0))
        a = max(a, c1)
    if hi > a + 1e-4:
        out.append((a, hi))
    return out


# =================================================================== bowl (steps, ramps, landings)
def band_rows(vis, col, segs, D0, Z0, n, t, r, portals, riser_role, tread_role, riser_hi=None,
              z_split=None, tread0=True, tread0_z=None):
    """Visual steps + collision ramp over the segments. Riser j (1..n) at D0 + j t from Z0 + (j-1) r
    to Z0 + j r; tread j (0..n-1) from D0 + j t to D0 + (j+1) t at Z0 + j r (tread 0 = lower landing).
    The ramp runs through the nosings (D0, Z0) -> (D0 + n t, Z0 + n r)."""
    my_portals = [p for p in portals if p.seg in segs and abs(p.d0 - D0) < 1e-3]
    for sname in segs:
        i = SI[sname]
        nrm = seg_normal(i)
        inward = (-nrm[0], -nrm[1], 0.0)
        for j in range(0, n):
            if j == 0 and not tread0:
                continue
            da, db = D0 + j * t, D0 + (j + 1) * t
            z = Z0 + j * r
            if j == 0 and tread0_z is not None:
                z = tread0_z
            # treads below the hood (j < J) are cut; tread J continues the hood top
            cuts = cut_intervals(i, my_portals, row=j + 1)
            ha, hb = half(i, da), half(i, db)
            if tread_role == "riser":    # solid colour blocks: the tread takes its riser's colour
                trole = riser_hi if (riser_hi and z_split is not None and z >= z_split - 1e-6) else riser_role
            else:
                trole = tread_role
            tm = mat(trole)
            for a, b in pieces(-max(ha, hb), max(ha, hb), cuts):
                a0, b0 = max(a, -ha), min(b, ha)
                a1, b1 = max(a, -hb), min(b, hb)
                if b0 - a0 < 1e-3 and b1 - a1 < 1e-3:
                    continue
                pts = [spt(i, da, a0, z), spt(i, da, b0, z), spt(i, db, b1, z), spt(i, db, a1, z)]
                uvs = [(a0 / 10.0, 0.0), (b0 / 10.0, 0.0), (b1 / 10.0, 1.0), (a1 / 10.0, 1.0)]
                if tm in SOLID_V:
                    uvs = [(u, SOLID_V[tm]) for u, _ in uvs]
                vis.quad(*pts, tm, (0, 0, 1), uvs=_shift(uvs))
        for j in range(1, n + 1):
            d = D0 + j * t
            z0, z1 = Z0 + (j - 1) * r, Z0 + j * r
            if j == 1 and tread0_z is not None:
                z0 = tread0_z
            role = riser_role
            if riser_hi and z_split is not None and z0 >= z_split - 1e-6:
                role = riser_hi
            rm = mat(role)
            h = half(i, d)
            for a, b in pieces(-h, h, cut_intervals(i, my_portals, row=j)):
                pts = [spt(i, d, a, z0), spt(i, d, b, z0), spt(i, d, b, z1), spt(i, d, a, z1)]
                uvs = [(a / 10.0, 0.0), (b / 10.0, 0.0), (b / 10.0, 1.0), (a / 10.0, 1.0)]
                if rm in SOLID_V:     # the banner's darker hem colour, not its striped border on every 0.5 m
                    uvs = [(u, SOLID_HEM_V) for u, _ in uvs]    # riser: steps read as rows of one colour
                vis.quad(*pts, rm, inward, uvs=_shift(uvs))
        # ---- collision ramp (nosing line)
        D1, Z1 = D0 + n * t, Z0 + n * r
        h0, h1 = half(i, D0), half(i, D1)
        cuts = cut_intervals(i, my_portals, row=0)
        cm = mat("concrete")
        up = (inward[0] * 0.0, 0.0, 1.0)
        for a, b in pieces(-max(h0, h1), max(h0, h1), cuts):
            a0, b0 = max(a, -h0), min(b, h0)
            a1, b1 = max(a, -h1), min(b, h1)
            col.quad(spt(i, D0, a0, Z0), spt(i, D0, b0, Z0), spt(i, D1, b1, Z1), spt(i, D1, a1, Z1), cm, up)
        for p in my_portals:
            if p.i != i:
                continue
            a, b = p.sc - p.w, p.sc + p.w
            # ramp above the hood
            col.quad(spt(i, p.d_h, a, p.z_h), spt(i, p.d_h, b, p.z_h), spt(i, D1, b, Z1), spt(i, D1, a, Z1), cm, up)


def _shift(uvs):
    du = math.floor(min(u for u, _ in uvs))
    dv = math.floor(min(v for _, v in uvs))
    return [(u - du, v - dv) for u, v in uvs]


def s_at_u(i, d, u):
    """Along-coordinate on segment i (ring offset d) where the local u coordinate equals u."""
    _, _, mid, t, _, _ = seg(i, d)
    return (u - mid[0]) / t[0]


def block_side(i, d, inside):
    """s-range of the SWb / SEa chord at offset d that lies over the South Ramp block (|u| <= U_SBLOCK,
    inside=True) or beyond it (inside=False)."""
    h = half(i, d)
    s0 = s_at_u(i, d, -U_SBLOCK if SEGS[i] == "SWb" else U_SBLOCK)
    s0 = max(-h, min(h, s0))
    toward_s = SEGS[i] == "SWb"       # SWb runs from SW1 (outer end) to SW2 (south side): block part is s > s0
    if inside:
        return (s0, h) if toward_s else (-h, s0)
    return (-h, s0) if toward_s else (s0, h)


def landing(vis, col, segs, d0, d1, z, vis_role="concrete", vz=None, portals=(), col_on=True, vis_on=True,
            cut_d=None, srange=None):
    """Flat ring band d0..d1 at z over segments (visual at vz, default z). srange(i, d) -> (lo, hi)
    optionally limits the along-range of a segment."""
    for sname in segs:
        i = SI[sname]
        h0, h1 = half(i, d0), half(i, d1)
        cuts = []
        for p in portals:
            if p.i == i and (cut_d is None or cut_d(p)):
                cuts.append((p.sc - p.w_in, p.sc + p.w_in))
        cuts.sort()
        lo0, hi0 = srange(i, d0) if srange else (-h0, h0)
        lo1, hi1 = srange(i, d1) if srange else (-h1, h1)
        for a, b in pieces(-max(h0, h1), max(h0, h1), cuts):
            a0, b0 = max(a, lo0), min(b, hi0)
            a1, b1 = max(a, lo1), min(b, hi1)
            if b0 - a0 < 1e-3 and b1 - a1 < 1e-3:
                continue
            if vis_on:
                pts = [spt(i, d0, a0, z if vz is None else vz), spt(i, d0, b0, z if vz is None else vz),
                       spt(i, d1, b1, z if vz is None else vz), spt(i, d1, a1, z if vz is None else vz)]
                vis.quad(*pts, mat(vis_role), (0, 0, 1))
            if col_on:
                col.quad(spt(i, d0, a0, z), spt(i, d0, b0, z), spt(i, d1, b1, z), spt(i, d1, a1, z),
                         mat("concrete"), (0, 0, 1))


def ring_wall(vis, col, segs, d, z0, z1, role, facing_out, portals=(), mode=None, col_on=True, vis_on=True,
              tile=None, srange=None):
    """Vertical ring wall z0..z1 at offset d over segments, with tunnel openings (portals passed in:
    the opening spans floor..ceiling of the portal at d; only parts overlapping z0..z1 are cut)."""
    for sname in segs:
        i = SI[sname]
        nrm = seg_normal(i)
        out = nrm if facing_out else (-nrm[0], -nrm[1])
        h = half(i, d)
        lo_s, hi_s = srange(i, d) if srange else (-h, h)
        ops = []
        for p in portals:
            if p.i != i:
                continue
            f, c = p.floor_at(d), p.ceil_at(d)
            if c <= z0 + 1e-4 or f >= z1 - 1e-4:
                continue
            ops.append((p, f, c))
        cuts = sorted((p.sc - p.w_in, p.sc + p.w_in) for p, _, _ in ops)
        pieces_z = [(a, b, z0, z1) for a, b in pieces(lo_s, hi_s, cuts)]
        for p, f, c in ops:
            a, b = p.sc - p.w_in, p.sc + p.w_in
            if f > z0 + 1e-4:
                pieces_z.append((a, b, z0, f))
            if c < z1 - 1e-4:
                pieces_z.append((a, b, c, z1))
        for a, b, za, zb in pieces_z:
            pa, pb = spt(i, d, a), spt(i, d, b)
            if vis_on:
                vis.wall(pa, pb, za, zb, mat(role), out, mode, tile)
            if col_on:
                col.wall(pa, pb, za, zb, mat("concrete"), out)


# =================================================================== portal geometry
def portal_geometry(vis, col, p, band, paving=True):
    """Hood (platform over the mouth), lintel, jambs, tunnel walls, ceiling, floor."""
    D0, Z0, n, t, r = band
    i = p.i
    nrm = seg_normal(i)
    tdir = seg_dir(i)
    inward = (-nrm[0], -nrm[1], 0.0)
    cm = mat("concrete")
    a, b = p.sc - p.w, p.sc + p.w
    ai, bi = p.sc - p.w_in, p.sc + p.w_in
    zc0 = p.ceil_at(p.d0)
    # hood top (flat, continues tread J back to the mouth)
    for g, role in ((vis, "concrete"), (col, "concrete")):
        g.quad(spt(i, p.d0, a, p.z_h), spt(i, p.d0, b, p.z_h), spt(i, p.d_h, b, p.z_h), spt(i, p.d_h, a, p.z_h),
               mat(role) if g is vis else cm, (0, 0, 1))
    # lintel over the opening + jambs (mouth face, looking at the field)
    vis.quad(spt(i, p.d0, ai, zc0), spt(i, p.d0, bi, zc0), spt(i, p.d0, bi, p.z_h), spt(i, p.d0, ai, p.z_h),
             mat("orange"), inward, mode="solid")
    col.quad(spt(i, p.d0, ai, zc0), spt(i, p.d0, bi, zc0), spt(i, p.d0, bi, p.z_h), spt(i, p.d0, ai, p.z_h),
             cm, inward)
    f0 = p.floor_at(p.d0)
    for (s0, s1) in ((a, ai), (bi, b)):
        vis.quad(spt(i, p.d0, s0, f0), spt(i, p.d0, s1, f0), spt(i, p.d0, s1, p.z_h), spt(i, p.d0, s0, p.z_h),
                 mat("blue"), inward, mode="solid")
        col.quad(spt(i, p.d0, s0, f0), spt(i, p.d0, s1, f0), spt(i, p.d0, s1, p.z_h), spt(i, p.d0, s0, p.z_h),
                 cm, inward)
    # hood side faces (toward the rows): from below the step line up to the hood top
    for s, sgn in ((a, -1.0), (b, 1.0)):
        side = (tdir[0] * sgn, tdir[1] * sgn, 0.0)
        z_lo_h = p.z_h - r
        pts = [spt(i, p.d0, s, Z0), spt(i, p.d_h, s, z_lo_h), spt(i, p.d_h, s, p.z_h), spt(i, p.d0, s, p.z_h)]
        vis.add(pts, cm, auto_uv(pts, cm, side), side)
        cp = [spt(i, p.d0, s, Z0), spt(i, p.d_h, s, p.z_h), spt(i, p.d0, s, p.z_h)]
        col.add(cp, cm, None, side)
    # tunnel walls (inner faces), ceiling, floor
    dm = mat("dark")
    for s, sgn in ((ai, 1.0), (bi, -1.0)):
        face = (tdir[0] * sgn, tdir[1] * sgn, 0.0)
        pts = [spt(i, p.d0, s, p.floor_at(p.d0)), spt(i, p.d_exit, s, p.floor_at(p.d_exit)),
               spt(i, p.d_exit, s, p.ceil_at(p.d_exit)), spt(i, p.d0, s, p.ceil_at(p.d0))]
        vis.add(pts, cm, auto_uv(pts, cm, face), face)
        col.add(pts, cm, None, face)
        # orange stripe along the wall at 1.0-1.4 m
        sp = [spt(i, p.d0, s, p.floor_at(p.d0) + 1.0), spt(i, p.d_exit, s, p.floor_at(p.d_exit) + 1.0),
              spt(i, p.d_exit, s, p.floor_at(p.d_exit) + 1.4), spt(i, p.d0, s, p.floor_at(p.d0) + 1.4)]
        off = (tdir[0] * sgn * 0.03, tdir[1] * sgn * 0.03)
        sp = [(q[0] + off[0], q[1] + off[1], q[2]) for q in sp]
        vis.add(sp, mat("orange"), auto_uv(sp, mat("orange"), face, "solid"), face)
    cpts = [spt(i, p.d0, ai, p.ceil_at(p.d0)), spt(i, p.d0, bi, p.ceil_at(p.d0)),
            spt(i, p.d_exit, bi, p.ceil_at(p.d_exit)), spt(i, p.d_exit, ai, p.ceil_at(p.d_exit))]
    vis.add(cpts, dm, auto_uv(cpts, dm, (0, 0, -1)), (0, 0, -1))
    col.add(cpts, cm, None, (0, 0, -1))
    if paving:
        fz0, fz1 = p.floor_at(p.d0), p.floor_at(p.d_exit)
        sloped = abs(fz1 - fz0) > 1e-3
        vz0 = fz0 if sloped else fz0 - 0.015
        vz1 = fz1 if sloped else fz1 - 0.015
        fpts = [spt(i, p.d0, ai, vz0), spt(i, p.d0, bi, vz0), spt(i, p.d_exit, bi, vz1), spt(i, p.d_exit, ai, vz1)]
        pm = mat("paving")
        vis.add(fpts, pm, auto_uv(fpts, pm, (0, 0, 1)), (0, 0, 1))
        if sloped or fz0 > 0.5:
            col.add([spt(i, p.d0, ai, fz0), spt(i, p.d0, bi, fz0), spt(i, p.d_exit, bi, fz1),
                     spt(i, p.d_exit, ai, fz1)], cm, None, (0, 0, 1))


# =================================================================== text (original block letters)
FONT = {
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
    "W": ["#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"],
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "M": ["#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"],
    "P": ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
}


def glyph_rects(ch):
    rows = FONT[ch]
    runs = []
    for y, row in enumerate(rows):
        x = 0
        while x < 5:
            if row[x] == "#":
                x1 = x
                while x1 + 1 < 5 and row[x1 + 1] == "#":
                    x1 += 1
                runs.append([x, x1, y, y])
                x = x1 + 1
            else:
                x += 1
    merged = []
    for r in runs:
        for m in merged:
            if m[0] == r[0] and m[1] == r[1] and m[3] == r[2] - 1:
                m[3] = r[2]
                break
        else:
            merged.append(r)
    return merged   # [x0, x1, y0 (top row), y1]


def text_rects(text):
    """Block letters as rectangles in pixel units: (x0, y0, x1, y1), y up, width, height 7."""
    out = []
    x = 0
    for ch in text:
        if ch == " ":
            x += 4
            continue
        for x0, x1, y0, y1 in glyph_rects(ch):
            out.append((x + x0, 6 - y1, x + x1 + 1, 7 - y0))
        x += 6
    return out, x - 1


def place_text(g, text, origin, right, up, px, m, normal, mode="solid"):
    """Letters on a plane: origin = lower-left corner (local u, v, z), right / up unit vectors."""
    rects, _ = text_rects(text)
    for x0, y0, x1, y1 in rects:
        def P(x, y):
            return (origin[0] + right[0] * x * px + up[0] * y * px,
                    origin[1] + right[1] * x * px + up[1] * y * px,
                    origin[2] + right[2] * x * px + up[2] * y * px)
        pts = [P(x0, y0), P(x1, y0), P(x1, y1), P(x0, y1)]
        g.add(pts, m, [(0.1, SOLID_V.get(m, 0.5))] * 4 if mode == "solid" else auto_uv(pts, m, normal), normal)


def text_width(text, px):
    return text_rects(text)[1] * px


# =================================================================== components
def build_field(fld, col):
    """Turf, NCAA paint, end zones, midfield mark (visual, under the -10 m collision floor)."""
    rg = ring(0.0)
    col.add([(p[0], p[1], Z_FIELD) for p in rg], mat("concrete"), None, (0, 0, 1))
    # base turf: the field ring clipped to 20 m cells (keeps UV spans small)
    tm = mat("apron")
    for gx in range(-2, 2):
        for gy in range(-4, 4):
            cell = clip_poly(rg, gx * 20.0, gy * 20.0, (gx + 1) * 20.0, (gy + 1) * 20.0)
            if len(cell) >= 3:
                fld.flat(cell, Z_FIELD - 0.07, tm)
    # field of play: 5-yard mowing bands
    t1, t2 = mat("turf"), mat("turf2")
    for k in range(-10, 10):
        v0, v1 = k * YD5, (k + 1) * YD5
        fld.flat([(-FOP_HW, v0), (FOP_HW, v0), (FOP_HW, v1), (-FOP_HW, v1)], Z_FIELD - 0.06, t1 if k % 2 else t2)
    # end zones (solid blue) with orange letters
    bm, om = mat("blue"), mat("orange")
    for sgn in (1, -1):
        v0, v1 = sorted((sgn * GOAL_V, sgn * END_V))
        fld.add([(-FOP_HW, v0, Z_FIELD - 0.06), (FOP_HW, v0, Z_FIELD - 0.06), (FOP_HW, v1, Z_FIELD - 0.06),
                 (-FOP_HW, v1, Z_FIELD - 0.06)], bm, [(0, 0.62), (4, 0.62), (4, 0.62), (0, 0.62)], (0, 0, 1))
        px = 0.85
        w = text_width("THE SWAMP", px)
        hgt = 7 * px
        vc = sgn * (GOAL_V + END_V) / 2
        if sgn > 0:
            origin = (-w / 2, vc - hgt / 2, Z_FIELD - 0.02)
            place_text(fld, "THE SWAMP", origin, (1, 0, 0), (0, 1, 0), px, om, (0, 0, 1))
        else:
            origin = (w / 2, vc + hgt / 2, Z_FIELD - 0.02)
            place_text(fld, "THE SWAMP", origin, (-1, 0, 0), (0, -1, 0), px, om, (0, 0, 1))
    # lines: sidelines / end lines (1 m border), yard lines every 5 yd, goal lines
    lm = mat("line")
    zl = Z_FIELD - 0.05
    fld.flat([(-FOP_HW - 1.0, -END_V - 1.0), (-FOP_HW, -END_V - 1.0), (-FOP_HW, END_V + 1.0),
              (-FOP_HW - 1.0, END_V + 1.0)], zl, lm)
    fld.flat([(FOP_HW, -END_V - 1.0), (FOP_HW + 1.0, -END_V - 1.0), (FOP_HW + 1.0, END_V + 1.0),
              (FOP_HW, END_V + 1.0)], zl, lm)
    for sgn in (1, -1):
        v0, v1 = sorted((sgn * END_V, sgn * (END_V + 1.0)))
        fld.flat([(-FOP_HW, v0), (FOP_HW, v0), (FOP_HW, v1), (-FOP_HW, v1)], zl, lm)
    for k in range(-10, 11):
        v = k * YD5
        hw = 0.15 if abs(k) == 10 else 0.1
        fld.flat([(-FOP_HW, v - hw), (FOP_HW, v - hw), (FOP_HW, v + hw), (-FOP_HW, v + hw)], zl + 0.01, lm)
    # hash marks (every 5 yd, at the college hash distance 60 ft = 18.29 m apart -> +-9.14 m)
    for k in range(-9, 10):
        v = k * YD5
        for u in (-9.14, 9.14):
            fld.flat([(u - 0.6, v - 0.1), (u + 0.6, v - 0.1), (u + 0.6, v + 0.1), (u - 0.6, v + 0.1)], zl + 0.01, lm)
    # midfield mark: an original orange disc with a blue ring (no team logo)
    nseg = 16
    outer = [(6.0 * math.cos(2 * math.pi * k / nseg), 6.0 * math.sin(2 * math.pi * k / nseg)) for k in range(nseg)]
    inner = [(4.6 * math.cos(2 * math.pi * k / nseg), 4.6 * math.sin(2 * math.pi * k / nseg)) for k in range(nseg)]
    for k in range(nseg):
        a, b = outer[k], outer[(k + 1) % nseg]
        c, d = inner[(k + 1) % nseg], inner[k]
        fld.add([(a[0], a[1], zl + 0.02), (b[0], b[1], zl + 0.02), (c[0], c[1], zl + 0.02), (d[0], d[1], zl + 0.02)],
                bm, [(0, 0.62)] * 4, (0, 0, 1))
    fld.add([(p[0], p[1], zl + 0.02) for p in inner], om, [(0, 0.62)] * nseg, (0, 0, 1))


def clip_poly(poly, x0, y0, x1, y1):
    def clip(pts, inside, inter):
        out = []
        for k in range(len(pts)):
            a, b = pts[k - 1], pts[k]
            ia, ib = inside(a), inside(b)
            if ib:
                if not ia:
                    out.append(inter(a, b))
                out.append(b)
            elif ia:
                out.append(inter(a, b))
        return out

    def ix(xc):
        return lambda a, b: (xc, a[1] + (b[1] - a[1]) * (xc - a[0]) / (b[0] - a[0]))

    def iy(yc):
        return lambda a, b: (a[0] + (b[0] - a[0]) * (yc - a[1]) / (b[1] - a[1]), yc)
    pts = list(poly)
    for inside, inter in ((lambda p: p[0] >= x0, ix(x0)), (lambda p: p[0] <= x1, ix(x1)),
                          (lambda p: p[1] >= y0, iy(y0)), (lambda p: p[1] <= y1, iy(y1))):
        if not pts:
            break
        pts = clip(pts, inside, inter)
    return pts


def build_field_wall(vis, col, portals):
    """1.2 m padded wall around the field (blue with an orange stripe), white cap."""
    fp = [p for p in portals if abs(p.d0) < 1e-6]
    for sname in SEGS:
        i = SI[sname]
        h = half(i, 0.0)
        cuts = sorted((p.sc - p.w, p.sc + p.w) for p in fp if p.i == i)
        nrm = seg_normal(i)
        inward = (-nrm[0], -nrm[1])
        for a, b in pieces(-h, h, cuts):
            pa, pb = spt(i, 0.0, a), spt(i, 0.0, b)
            pts = [(pa[0], pa[1], Z_FIELD - 0.1), (pb[0], pb[1], Z_FIELD - 0.1), (pb[0], pb[1], Z_WALLTOP),
                   (pa[0], pa[1], Z_WALLTOP)]
            vis.add(pts, mat("blue"), [(a / 10, 0), (b / 10, 0), (b / 10, 1), (a / 10, 1)], (inward[0], inward[1], 0))
            col.wall(pa, pb, Z_FIELD, Z_WALLTOP, mat("concrete"), inward)


def build_bowl(vis, col, portals):
    L1 = (0.0, Z_WALLTOP, L1_N, L1_T, L1_R)
    band_rows(vis, col, SEGS, *L1, portals, "riser_lo", "riser", tread0=True)
    # cross-aisle at grade (inside the ground hole: own collision; visual just under the floor)
    landing(vis, col, SEGS, D_AISLE0, D_AISLE1, 0.0, "paving", vz=-0.015)
    # main band: H segments to the rim, N segments to the promenade
    band_rows(vis, col, H_SEGS, D_AISLE1, 0.0, H_N, H_T, H_R, portals, "riser_lo", "riser",
              riser_hi="riser_hi", z_split=Z_PROM, tread0=True, tread0_z=-0.015)
    band_rows(vis, col, N_SEGS, D_AISLE1, 0.0, N_LOW, H_T, H_R, portals, "riser_lo", "riser",
              tread0=True, tread0_z=-0.015)
    # rim walkway + parapet (not where the rim opens onto the South Ramp terrace)
    rim_par = [s for s in H_SEGS if s not in TERRACE_SEGS and s != "W"]
    part = ["SWb", "SEa"]                        # chords partly over the South Ramp block

    def over(i, d):
        return block_side(i, d, True)

    def beyond(i, d):
        return block_side(i, d, False)
    landing(vis, col, [s for s in H_SEGS if s != "S"], D_RIM0, D_RIM1, Z_RIM, "concrete")
    landing(vis, col, ["S"], D_RIM0, D_OUT, Z_RIM, "concrete")
    landing(vis, col, part, D_RIM1, D_OUT, Z_RIM, "concrete", srange=over)
    landing(vis, col, ["W"], D_RIM1, D_OUT, Z_RIM, "concrete")
    ring_wall(vis, col, rim_par, D_RIM1, Z_RIM, Z_PARAPET, "concrete", facing_out=False)
    landing(vis, col, rim_par, D_RIM1, D_OUT, Z_PARAPET, "white")
    ring_wall(vis, col, part, D_RIM1, Z_RIM, Z_PARAPET, "concrete", facing_out=False, srange=beyond)
    landing(vis, col, part, D_RIM1, D_OUT, Z_PARAPET, "white", srange=beyond)
    # outer wall of the bowl (E / SE / SW and the chord ends beyond the South Ramp block): brick plinth,
    # window band, orange crown
    gate_exits = [p for p in portals if abs(p.d_exit - D_OUT) < 1e-6]
    for segs_, sr in ((["E", "SEb", "SWa"], None), (part, beyond)):
        ring_wall(vis, col, segs_, D_OUT, 0.0, Z_PARAPET, "brick", facing_out=True, portals=gate_exits,
                  vis_on=False, srange=sr)
        ring_wall(vis, _Null(), segs_, D_OUT, 0.0, 4.0, "brick_plain", True, gate_exits, col_on=False, srange=sr)
        ring_wall(vis, _Null(), segs_, D_OUT, 4.0, 16.0, "brick", True, gate_exits, col_on=False, tile=4.0, srange=sr)
        ring_wall(vis, _Null(), segs_, D_OUT, 16.0, 19.6, "riser_hi", True, gate_exits, col_on=False, mode="stretch",
                  srange=sr)
        ring_wall(vis, _Null(), segs_, D_OUT, 19.6, Z_PARAPET, "white", True, gate_exits, col_on=False, srange=sr)
    # orange / blue banners on the east outer wall
    i = SI["E"]
    for k, sc in enumerate((-44.0, -20.0, -8.0, 8.0, 20.0, 44.0)):
        role = "riser_hi" if k % 2 == 0 else "riser_lo"
        q0, q1 = spt(i, D_OUT + 0.06, sc - 1.5), spt(i, D_OUT + 0.06, sc + 1.5)
        vis.add([(q0[0], q0[1], 5.0), (q1[0], q1[1], 5.0), (q1[0], q1[1], 15.0), (q0[0], q0[1], 15.0)],
                mat(role), [(0, 0.05), (1, 0.05), (1, 0.95), (0, 0.95)], (1, 0, 0))
    # north: promenade (7 m), corner retaining walls, Touchdown Terrace wall
    landing(vis, col, N_SEGS, D_PROM0, D_PROM1, Z_PROM, "concrete")
    ring_wall(vis, col, OPEN_SEGS, D_PROM1, 0.0, Z_PROM + 1.1, "brick_plain", facing_out=True,
              portals=[p for p in portals if abs(p.d_exit - D_PROM1) < 1e-6], tile=2.0)
    landing(vis, _Null(), OPEN_SEGS, D_PROM1, D_PROM1 + 0.3, Z_PROM + 1.1, "white", col_on=False)
    ring_wall(vis, col, SUN_SEGS, D_PROM1, Z_PROM, Z_SUN_SOFFIT, "concrete", facing_out=False, vis_on=False)
    ring_wall(vis, _Null(), SUN_SEGS, D_PROM1, Z_PROM, 10.0, "concrete", False, col_on=False)
    ring_wall(vis, _Null(), SUN_SEGS, D_PROM1, 10.0, 18.0, "glass", False, col_on=False, tile=4.0)
    ring_wall(vis, _Null(), SUN_SEGS, D_PROM1, 18.0, Z_SUN_SOFFIT, "concrete", False, col_on=False)


class _Null:
    """Sink for geometry we do not want (e.g. visual-only walls passed to a collision slot)."""

    def __getattr__(self, name):
        return lambda *a, **k: None


def build_end_walls(vis, col):
    """End walls of the east / west rows above the promenade (open NE / NW corners) and of the
    Sunshine Seats + north block (45 / 135 degree radial planes)."""
    cm = mat("concrete")
    for sgn in (1, -1):        # east (NE corner) / west (NW corner)
        u_of = lambda d: sgn * (A0 + d)   # noqa: E731
        vin = B0 - R0 - 0.5     # inner face (rows side)
        vout = B0 - R0          # outer face (corner plaza)
        prof_top = [(D_PROM0, Z_PROM + 1.0), (D_RIM0, Z_RIM + 1.0), (D_OUT, Z_PARAPET)]
        # outer face polygon (d, z)
        outer = [(D_PROM0, Z_PROM), (D_PROM1, Z_PROM), (D_PROM1, 0.0), (D_OUT, 0.0), (D_OUT, Z_PARAPET),
                 (D_RIM1, Z_PARAPET), (D_RIM1, Z_RIM), (D_RIM0, Z_RIM), (D_RIM0, Z_PARAPET),
                 (D_PROM0, Z_PROM + 1.0)]
        pts = [(u_of(d), vout, z) for d, z in outer]
        vis.add(pts, mat("brick_plain"), auto_uv(pts, mat("brick_plain"), (0, 1, 0)), (0, 1, 0))
        col.add(pts, cm, None, (0, 1, 0))
        inner = [(D_PROM0, Z_PROM), (D_PROM0 + H_T, Z_PROM), (D_RIM0, Z_RIM - H_R), (D_RIM0, Z_PARAPET),
                 (D_PROM0, Z_PROM + 1.0)]
        pts = [(u_of(d), vin, z) for d, z in inner]
        vis.add(pts, cm, auto_uv(pts, cm, (0, -1, 0)), (0, -1, 0))
        col.add(pts, cm, None, (0, -1, 0))
        # top strip (sloped) of the 0.5 m thick wall
        for (d0, z0), (d1, z1) in ((prof_top[0], prof_top[1]), ((D_RIM1, Z_PARAPET), (D_OUT, Z_PARAPET))):
            tp = [(u_of(d0), vin, z0), (u_of(d1), vin, z1), (u_of(d1), vout, z1), (u_of(d0), vout, z0)]
            vis.add(tp, mat("white"), auto_uv(tp, mat("white"), (0, 0, 1)), (0, 0, 1))
            col.add(tp, cm, None, (0, 0, 1))
    # Sunshine / north block end walls on the 45 and 135 degree radial lines
    for cx, cy, ang in ((A0 - R0, B0 - R0, 45.0), (-(A0 - R0), B0 - R0, 135.0)):
        a = math.radians(ang)
        rad = (math.cos(a), math.sin(a))
        # normal pointing into the open corner (away from the Sunshine side)
        side = (math.sin(a), -math.cos(a)) if ang < 90 else (-math.sin(a), math.cos(a))
        side_in = (-side[0], -side[1])

        def P(d, z, off=0.0):
            return (cx + rad[0] * (R0 + d) + side_in[0] * off, cy + rad[1] * (R0 + d) + side_in[1] * off, z)
        prof = [(D_SUN_F, Z_SUN_SOFFIT), (D_PROM1, Z_SUN_SOFFIT), (D_PROM1, 0.0), (D_SUN_OUT, 0.0),
                (D_SUN_OUT, Z_SUN_TOP + 1.0), (D_SUN_RIM0, Z_SUN_TOP + 1.0), (D_SUN0, Z_SUN + 1.0),
                (D_SUN0, Z_SUN), (D_SUN_F, Z_SUN)]
        pts = [P(d, z) for d, z in prof]
        hint = (side[0], side[1], 0.0)
        vis.add(pts, mat("brick_plain"), auto_uv(pts, mat("brick_plain"), hint), hint)
        col.add(pts, cm, None, hint)
        pin = [P(d, z, 0.5) for d, z in prof]
        hin = (side_in[0], side_in[1], 0.0)
        vis.add(pin, cm, auto_uv(pin, cm, hin), hin)
        col.add(pin, cm, None, hin)
        for (d0, z0), (d1, z1) in (((D_SUN0, Z_SUN + 1.0), (D_SUN_RIM0, Z_SUN_TOP + 1.0)),
                                   ((D_SUN_RIM0, Z_SUN_TOP + 1.0), (D_SUN_OUT, Z_SUN_TOP + 1.0))):
            tp = [P(d0, z0), P(d1, z1), P(d1, z1, 0.5), P(d0, z0, 0.5)]
            vis.add(tp, mat("white"), auto_uv(tp, mat("white"), (0, 0, 1)), (0, 0, 1))
            col.add(tp, cm, None, (0, 0, 1))


def build_sunshine(vis, col, portals):
    """North upper deck: front walkway (22 m), 26 steps, rim, back wall, soffit, fascia."""
    band = (D_SUN0, Z_SUN, SUN_N, SUN_T, SUN_R)
    landing(vis, col, SUN_SEGS, D_SUN_F, D_SUN0, Z_SUN, "concrete")
    band_rows(vis, col, SUN_SEGS, *band, portals, "riser_hi", "riser", tread0=True, tread0_z=None)
    landing(vis, col, SUN_SEGS, D_SUN_RIM0, D_SUN_RIM1, Z_SUN_TOP, "concrete")
    # front railing (fascia) + soffit
    ring_wall(vis, col, SUN_SEGS, D_SUN_F, Z_SUN, Z_SUN + 1.1, "metal", facing_out=True, col_on=True)
    ring_wall(vis, _Null(), SUN_SEGS, D_SUN_F, Z_SUN_SOFFIT, Z_SUN, "riser_lo", False, col_on=False, mode="stretch")
    ring_wall(vis, _Null(), SUN_SEGS, D_SUN_F, Z_SUN, Z_SUN + 1.1, "riser_hi", False, col_on=False, mode="stretch")
    for sname in SUN_SEGS:
        i = SI[sname]
        h0, h1 = half(i, D_SUN_F), half(i, D_PROM1)
        pts = [spt(i, D_SUN_F, -h0, Z_SUN_SOFFIT), spt(i, D_SUN_F, h0, Z_SUN_SOFFIT),
               spt(i, D_PROM1, h1, Z_SUN_SOFFIT), spt(i, D_PROM1, -h1, Z_SUN_SOFFIT)]
        vis.add(pts, mat("concrete"), auto_uv(pts, mat("concrete"), (0, 0, -1)), (0, 0, -1))
    # rim parapet + back wall (helix vomitories open in it)
    exits = [p for p in portals if abs(p.d_exit - D_SUN_OUT) < 1e-6]
    ring_wall(vis, col, SUN_SEGS, D_SUN_RIM1, Z_SUN_TOP, Z_SUN_TOP + 1.0, "concrete", facing_out=False)
    landing(vis, col, SUN_SEGS, D_SUN_RIM1, D_SUN_OUT, Z_SUN_TOP + 1.0, "white")
    ring_wall(vis, col, SUN_SEGS, D_SUN_OUT, 0.0, Z_SUN_TOP + 1.0, "brick", facing_out=True, portals=exits,
              vis_on=False)
    ring_wall(vis, _Null(), SUN_SEGS, D_SUN_OUT, 0.0, 4.0, "brick_plain", True, exits, col_on=False)
    ring_wall(vis, _Null(), SUN_SEGS, D_SUN_OUT, 4.0, 20.0, "brick", True, exits, col_on=False, tile=4.0)
    ring_wall(vis, _Null(), SUN_SEGS, D_SUN_OUT, 20.0, 32.0, "band", True, exits, col_on=False, tile=4.0)
    ring_wall(vis, _Null(), SUN_SEGS, D_SUN_OUT, 32.0, 36.4, "riser_hi", True, exits, col_on=False, mode="stretch")
    ring_wall(vis, _Null(), SUN_SEGS, D_SUN_OUT, 36.4, Z_SUN_TOP + 1.0, "white", True, exits, col_on=False)
    # "THE SWAMP" on the north face (courtyard side), above the gatehouse
    i = SI["N"]
    px = 0.75
    w = text_width("THE SWAMP", px)
    o = spt(i, D_SUN_OUT + 0.05, -w / 2, 24.0)     # N side runs east -> west: s = -w/2 is u = +w/2
    place_text(vis, "THE SWAMP", o, (-1, 0, 0), (0, 0, 1), px, mat("orange"), (0, 1, 0))


def build_corner_access(vis, col):
    """Open NE / NW corners: stairs from the corner plaza to the promenade; bridges from the east /
    west rim to the Sunshine front walkway."""
    cm = mat("concrete")
    for sname in OPEN_SEGS:
        i = SI[sname]
        nrm = seg_normal(i)
        h = half(i, D_PROM1)
        # which end touches the H rows (angle 0 / 180): NEa starts at the E side (s = -h), NWb ends at
        # the W side (s = +h)
        e = -1.0 if sname == "NEa" else 1.0
        d0, d1 = D_PROM1, D_PROM1 + 3.0
        s_top, s_land = e * (h - 3.5), e * h
        s_bot = -e * (h - 4.0)
        # stair ramp (grade at s_bot -> 7 m at s_top), landing s_top..s_land
        rp = [spt(i, d0, s_bot, 0.0), spt(i, d1, s_bot, 0.0), spt(i, d1, s_top, Z_PROM), spt(i, d0, s_top, Z_PROM)]
        vis.add(rp, mat("paving"), auto_uv(rp, mat("paving"), (0, 0, 1)), (0, 0, 1))
        col.add(rp, cm, None, (0, 0, 1))
        lp = [spt(i, d0, s_top, Z_PROM), spt(i, d1, s_top, Z_PROM), spt(i, d1, s_land, Z_PROM),
              spt(i, d0, s_land, Z_PROM)]
        vis.add(lp, mat("paving"), auto_uv(lp, mat("paving"), (0, 0, 1)), (0, 0, 1))
        col.add(lp, cm, None, (0, 0, 1))
        out = (nrm[0], nrm[1], 0.0)
        side = [spt(i, d1, s_bot, 0.0), spt(i, d1, s_land, 0.0), spt(i, d1, s_land, Z_PROM), spt(i, d1, s_top, Z_PROM)]
        vis.add(side, mat("brick_plain"), auto_uv(side, mat("brick_plain"), out), out)
        col.add(side, cm, None, out)
        # railing on the outer edge
        rr = [spt(i, d1 - 0.1, s_bot, 0.0), spt(i, d1 - 0.1, s_top, Z_PROM), spt(i, d1 - 0.1, s_land, Z_PROM),
              spt(i, d1 - 0.1, s_land, Z_PROM + 1.1), spt(i, d1 - 0.1, s_top, Z_PROM + 1.1),
              spt(i, d1 - 0.1, s_bot, 1.1)]
        inw = (-nrm[0], -nrm[1], 0.0)
        vis.add(rr, mat("metal"), auto_uv(rr, mat("metal"), inw), inw)
        col.add(rr, cm, None, inw)
        # promenade railing (inner face of the retaining wall top) with an opening onto the landing
        lo_s, hi_s = sorted((s_top, s_land))
        for a, b in pieces(-h, h, [(lo_s, hi_s)]):
            pa, pb = spt(i, D_PROM1, a), spt(i, D_PROM1, b)
            vis.wall(pa, pb, Z_PROM, Z_PROM + 1.1, mat("metal"), (-nrm[0], -nrm[1]))
            col.wall(pa, pb, Z_PROM, Z_PROM + 1.1, cm, (-nrm[0], -nrm[1]))
            qa, qb = spt(i, D_PROM1 + 0.3, a), spt(i, D_PROM1 + 0.3, b)
            vis.add([(pa[0], pa[1], Z_PROM + 1.1), (pb[0], pb[1], Z_PROM + 1.1), (qb[0], qb[1], Z_PROM + 1.1),
                     (qa[0], qa[1], Z_PROM + 1.1)], mat("white"), None, (0, 0, 1))
    # bridges (20 m rim -> 22 m Sunshine walkway)
    for sgn in (1, -1):
        u_rim = sgn * (A0 + (D_RIM0 + D_RIM1) / 2)
        v_end = B0 - R0
        a = math.radians(45.0 if sgn > 0 else 135.0)
        cx, cy = sgn * (A0 - R0), B0 - R0
        dmid = (D_SUN_F + D_SUN0) / 2
        tgt = (cx + math.cos(a) * (R0 + dmid), cy + math.sin(a) * (R0 + dmid))
        p0 = (u_rim, v_end - 3.0, Z_RIM)
        p1 = (u_rim, v_end + 6.0, Z_RIM + 0.2)
        # end 0.6 m past the 45 / 135 degree line, on the walkway
        p2 = (tgt[0] - sgn * 0.6 * math.sin(a), tgt[1] + 0.6 * math.cos(a) * sgn, Z_SUN)
        bridge(vis, col, [p0, p1, p2], 1.25)


def bridge(vis, col, path, hw, col_ext=(0.0, 0.0)):
    """Walkway along a polyline (x, y, z) with railings, a slab underside and two columns.
    col_ext = (start, end): the COLLISION deck reaches this far past the first / last point, so it
    overlaps the floor it meets (a flat end that stops on a curved or offset edge leaves a few-cm
    crack Mario can drop through); the visual deck and the railings keep the exact ends."""
    cm = mat("concrete")
    nseg = len(path) - 1
    for k, ((x0, y0, z0), (x1, y1, z1)) in enumerate(zip(path, path[1:])):
        L = math.hypot(x1 - x0, y1 - y0)
        t = ((x1 - x0) / L, (y1 - y0) / L)
        n = (-t[1], t[0])
        A = (x0 + n[0] * hw, y0 + n[1] * hw)
        B = (x0 - n[0] * hw, y0 - n[1] * hw)
        Cc = (x1 - n[0] * hw, y1 - n[1] * hw)
        D = (x1 + n[0] * hw, y1 + n[1] * hw)
        top = [(A[0], A[1], z0), (B[0], B[1], z0), (Cc[0], Cc[1], z1), (D[0], D[1], z1)]
        vis.add(top, mat("metal"), auto_uv(top, mat("metal"), (0, 0, 1)), (0, 0, 1))
        e0 = col_ext[0] if k == 0 else 0.0
        e1 = col_ext[1] if k == nseg - 1 else 0.0
        if e0 or e1:
            top = [(A[0] - t[0] * e0, A[1] - t[1] * e0, z0), (B[0] - t[0] * e0, B[1] - t[1] * e0, z0),
                   (Cc[0] + t[0] * e1, Cc[1] + t[1] * e1, z1), (D[0] + t[0] * e1, D[1] + t[1] * e1, z1)]
        col.add(top, cm, None, (0, 0, 1))
        bot = [(p[0], p[1], p[2] - 0.6) for p in top]
        vis.add(bot, mat("dark"), auto_uv(bot, mat("dark"), (0, 0, -1)), (0, 0, -1))
        for (p, q, nn) in ((A, D, n), (B, Cc, (-n[0], -n[1]))):
            side = [(p[0], p[1], (z0 if p in (A, B) else z1) - 0.6), (q[0], q[1], z1 - 0.6), (q[0], q[1], z1 + 1.1),
                    (p[0], p[1], z0 + 1.1)]
            h = (nn[0], nn[1], 0.0)
            vis.add(side, mat("riser_hi"), auto_uv(side, mat("riser_hi"), h, "stretch"), h)
            inner = [(p[0], p[1], z0), (q[0], q[1], z1), (q[0], q[1], z1 + 1.1), (p[0], p[1], z0 + 1.1)]
            hi = (-nn[0], -nn[1], 0.0)
            vis.add(inner, mat("metal"), auto_uv(inner, mat("metal"), hi), hi)
            col.add(inner, cm, None, hi)
    # columns under the middle of each span
    for (x0, y0, z0), (x1, y1, z1) in zip(path, path[1:]):
        if math.hypot(x1 - x0, y1 - y0) < 20:
            continue
        mx, my, mz = (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2
        vis.box(mx - 0.5, mx + 0.5, my - 0.5, my + 0.5, 0.0, mz - 0.6, mat("concrete"), faces="nsew")
        col.box(mx - 0.5, mx + 0.5, my - 0.5, my + 0.5, 0.0, mz - 0.6, mat("concrete"), faces="nsew")


def build_helix(vis, col, center, top_dir_deg, name):
    """Helix ramp tower: grade -> 22 m in 1.5 turns (r 8..14), solid core, outer parapet, a top
    landing facing top_dir_deg (local angle) with an opening for the bridge."""
    cm = mat("concrete")
    cx, cy = center
    r_in, r_out = 8.0, 14.0
    z_top = Z_SUN
    turns = 1.5
    nseg = 18
    a_top = math.radians(top_dir_deg) - math.radians(15.0)
    a_bot = a_top - turns * 2 * math.pi
    pts_in, pts_out = [], []
    for k in range(nseg + 1):
        a = a_bot + (a_top - a_bot) * k / nseg
        z = z_top * k / nseg
        pts_in.append((cx + r_in * math.cos(a), cy + r_in * math.sin(a), z))
        pts_out.append((cx + r_out * math.cos(a), cy + r_out * math.sin(a), z))
    for k in range(nseg):
        a0i, a1i, a0o, a1o = pts_in[k], pts_in[k + 1], pts_out[k], pts_out[k + 1]
        for tri in ((a0i, a0o, a1o), (a0i, a1o, a1i)):
            vis.add(list(tri), mat("paving"), auto_uv(list(tri), mat("paving"), (0, 0, 1)), (0, 0, 1))
            col.add(list(tri), cm, None, (0, 0, 1))
        for tri in ((a0i, a0o, a1o), (a0i, a1o, a1i)):
            b = [(p[0], p[1], p[2] - 0.6) for p in tri]
            vis.add(b, mat("concrete"), auto_uv(b, mat("concrete"), (0, 0, -1)), (0, 0, -1))
        # outer parapet (inner face + outer face) and the slab edge
        o = (math.cos((math.atan2(a0o[1] - cy, a0o[0] - cx) + math.atan2(a1o[1] - cy, a1o[0] - cx)) / 2), 0)
        mid = ((a0o[0] + a1o[0]) / 2 - cx, (a0o[1] + a1o[1]) / 2 - cy)
        out = (mid[0], mid[1], 0.0)
        inn = (-mid[0], -mid[1], 0.0)
        par_in = [a0o, a1o, (a1o[0], a1o[1], a1o[2] + 1.1), (a0o[0], a0o[1], a0o[2] + 1.1)]
        vis.add(par_in, mat("concrete"), auto_uv(par_in, mat("concrete"), inn), inn)
        col.add(par_in, cm, None, inn)
        par_out = [(a0o[0], a0o[1], a0o[2] - 0.6), (a1o[0], a1o[1], a1o[2] - 0.6), (a1o[0], a1o[1], a1o[2] + 1.1),
                   (a0o[0], a0o[1], a0o[2] + 1.1)]
        vis.add(par_out, mat("riser_lo"), auto_uv(par_out, mat("riser_lo"), out, "stretch"), out)
        _ = o
    # top landing sector (flat at 22 m) from a_top to a_top + 30 deg
    land = [(cx, cy)]
    for k in range(4):
        a = a_top + math.radians(30.0) * k / 3
        land.append((cx + r_out * math.cos(a), cy + r_out * math.sin(a)))
    lp_out = land[1:]
    lp = [(cx + r_in * math.cos(a_top), cy + r_in * math.sin(a_top))] + lp_out + \
        [(cx + r_in * math.cos(a_top + math.radians(30)), cy + r_in * math.sin(a_top + math.radians(30)))]
    vis.flat(lp, z_top, mat("paving"))
    col.flat(lp, z_top, cm)
    vis.flat(lp, z_top - 0.6, mat("concrete"), up=False)
    # core cylinder
    ncore = 12
    core = [(cx + r_in * math.cos(2 * math.pi * k / ncore), cy + r_in * math.sin(2 * math.pi * k / ncore))
            for k in range(ncore)]
    vis.prism(core, 0.0, z_top + 4.0, mat("brick_plain"), top=mat("roof"))
    col.prism(core, 0.0, z_top + 4.0, cm, top=cm)
    # orange band on the core top
    for k in range(ncore):
        a, b = core[k], core[(k + 1) % ncore]
        mid = ((a[0] + b[0]) / 2 - cx, (a[1] + b[1]) / 2 - cy)
        vis.add([(a[0] + mid[0] * 0.003, a[1] + mid[1] * 0.003, z_top + 2.2),
                 (b[0] + mid[0] * 0.003, b[1] + mid[1] * 0.003, z_top + 2.2),
                 (b[0] + mid[0] * 0.003, b[1] + mid[1] * 0.003, z_top + 3.4),
                 (a[0] + mid[0] * 0.003, a[1] + mid[1] * 0.003, z_top + 3.4)], mat("orange"),
                [(0, 0.62)] * 4, (mid[0], mid[1], 0))
    return {"name": name, "center": center, "top": (cx + 11 * math.cos(a_top + math.radians(15)),
                                                    cy + 11 * math.sin(a_top + math.radians(15)), z_top),
            "bottom": (pts_in[0][0] * 0.5 + pts_out[0][0] * 0.5, pts_in[0][1] * 0.5 + pts_out[0][1] * 0.5, 0.0)}


def build_south(vis, col, portals):
    """South Ramp block (terrace at the rim height, merging with the south rim walkway) and one long
    exterior ramp from grade (east end) to the terrace (west end) along its south face. The field
    tunnel (portal_geometry) runs under the block and exits through the ramp's outer face."""
    cm = mat("concrete")
    r = ring(D_OUT)
    sw2, se0 = r[SI["S"]], r[SI["SEa"]]
    iw, ie = SI["SWb"], SI["SEa"]
    sw1 = spt(iw, D_OUT, s_at_u(iw, D_OUT, -U_SBLOCK))     # chord points above the block's ends
    se1 = spt(ie, D_OUT, s_at_u(ie, D_OUT, U_SBLOCK))
    plan = [sw1, sw2, se0, se1, (U_SBLOCK, V_SBLOCK), (-U_SBLOCK, V_SBLOCK)]
    vis.flat(plan, Z_RIM, mat("concrete"))
    col.flat(plan, Z_RIM, cm)
    ft = [p for p in portals if p.kind == "field"][0]
    tw = ft.w_in
    v0, v1 = V_SRAMP, V_SBLOCK
    ue, uw = U_SBLOCK, -U_SBLOCK
    u_land = uw + 5.0                       # the ramp reaches the terrace height here

    def zr(u):
        return max(0.0, min(Z_RIM, Z_RIM * (ue - u) / (ue - u_land)))
    # south face of the block above the ramp (a triangle) + orange crown
    u19 = ue - (ue - u_land) * (Z_RIM - 1.0) / Z_RIM
    tri = [(ue, v1, 0.0), (ue, v1, Z_RIM - 1.0), (u19, v1, Z_RIM - 1.0)]
    vis.add(tri, mat("band"), auto_uv(tri, mat("band"), (0, -1, 0), None, 4.0), (0, -1, 0))
    crown = [(ue, v1, Z_RIM - 1.0), (u19, v1, Z_RIM - 1.0), (u_land, v1, Z_RIM), (ue, v1, Z_RIM)]
    vis.add(crown, mat("riser_hi"), auto_uv(crown, mat("riser_hi"), (0, -1, 0), "stretch"), (0, -1, 0))
    col.add([(ue, v1, 0.0), (ue, v1, Z_RIM + 1.0), (u_land, v1, Z_RIM + 1.0), (u_land, v1, Z_RIM)], cm, None,
            (0, -1, 0))
    # east / west end faces of the block
    for sgn in (1, -1):
        a = (sgn * U_SBLOCK, V_SBLOCK)
        b = se1 if sgn > 0 else sw1
        out = (sgn, 0)
        vis.wall(a, b, 0.0, Z_RIM - 1.0, mat("band"), out, tile=4.0)
        vis.wall(a, b, Z_RIM - 1.0, Z_RIM, mat("riser_hi"), out, "stretch")
        col.wall(a, b, 0.0, Z_RIM, cm, out)
    # terrace parapet (east, west, south; the south one opens where the ramp arrives)
    edges = [(se1, (U_SBLOCK, V_SBLOCK), (1, 0)), ((-U_SBLOCK, V_SBLOCK), sw1, (-1, 0)),
             ((U_SBLOCK, V_SBLOCK), (u_land, V_SBLOCK), (0, -1))]
    for a, b, out in edges:
        a2 = (a[0] - out[0] * 0.4, a[1] - out[1] * 0.4)
        b2 = (b[0] - out[0] * 0.4, b[1] - out[1] * 0.4)
        inw = (-out[0], -out[1])
        vis.wall(a2, b2, Z_RIM, Z_RIM + 1.0, mat("concrete"), inw)
        col.wall(a2, b2, Z_RIM, Z_RIM + 1.0, cm, inw)
        vis.add([(a2[0], a2[1], Z_RIM + 1.0), (b2[0], b2[1], Z_RIM + 1.0), (b[0], b[1], Z_RIM + 1.0),
                 (a[0], a[1], Z_RIM + 1.0)], mat("white"), None, (0, 0, 1))
        if out != (0, -1):
            vis.wall(a, b, Z_RIM, Z_RIM + 1.0, mat("white"), out)
    # the ramp (4 m wide), top landing, outer face with the field tunnel exit, parapet, west end
    top = [(ue, v0, 0.0), (ue, v1, 0.0), (u_land, v1, Z_RIM), (u_land, v0, Z_RIM)]
    vis.add(top, mat("paving"), auto_uv(top, mat("paving"), (0, 0, 1)), (0, 0, 1))
    col.add(top, cm, None, (0, 0, 1))
    land = [(u_land, v0), (u_land, v1), (uw, v1), (uw, v0)]
    vis.flat(land, Z_RIM, mat("paving"))
    col.flat(land, Z_RIM, cm)
    ztun = ft.ceil_at(ft.d_exit)
    side_pts = [(ue, v0, 0.0), (tw, v0, 0.0), (tw, v0, ztun), (-tw, v0, ztun), (-tw, v0, 0.0), (uw, v0, 0.0),
                (uw, v0, Z_RIM), (u_land, v0, Z_RIM)]
    vis.add(side_pts, mat("brick_plain"), auto_uv(side_pts, mat("brick_plain"), (0, -1, 0)), (0, -1, 0))
    col.add(side_pts, cm, None, (0, -1, 0))
    par = [(ue, v0, 0.0), (u_land, v0, Z_RIM), (uw, v0, Z_RIM), (uw, v0, Z_RIM + 1.1),
           (u_land, v0, Z_RIM + 1.1), (ue, v0, 1.1)]
    pout = [(q[0], q[1] - 0.02, q[2]) for q in par]
    vis.add(pout, mat("riser_lo"), auto_uv(pout, mat("riser_lo"), (0, -1, 0), "stretch"), (0, -1, 0))
    pin = [(q[0], q[1] + 0.25, q[2]) for q in par]
    vis.add(pin, mat("metal"), auto_uv(pin, mat("metal"), (0, 1, 0)), (0, 1, 0))
    col.add(pin, cm, None, (0, 1, 0))
    wend = [(uw, v0, 0.0), (uw, v1, 0.0), (uw, v1, Z_RIM), (uw, v0, Z_RIM)]
    vis.add(wend, mat("brick_plain"), auto_uv(wend, mat("brick_plain"), (-1, 0, 0)), (-1, 0, 0))
    col.add(wend, cm, None, (-1, 0, 0))
    # "THE SWAMP" on the block's south face above the ramp
    px = 0.9
    place_text(vis, "THE SWAMP", (-2.3, V_SBLOCK - 0.05, 12.6), (1, 0, 0), (0, 0, 1), px, mat("orange"),
               (0, -1, 0))
    return plan


def build_boards(vis, col):
    """South (41.5 x 9.1 m) and north (21.6 x 7.3 m) video boards: framed dark screens with original
    "THE SWAMP" lettering, legs, a catwalk and service ledges behind the south board."""
    cm = mat("concrete")
    out = {}
    for name, bd, face_sgn, base_z in (("south", SB, 1.0, Z_RIM), ("north", NB, -1.0, Z_SUN_TOP)):
        hw = bd["w"] / 2
        vf = max(bd["v0"], bd["v1"]) if face_sgn > 0 else min(bd["v0"], bd["v1"])
        vb = min(bd["v0"], bd["v1"]) if face_sgn > 0 else max(bd["v0"], bd["v1"])
        z0, z1 = bd["z0"], bd["z0"] + bd["h"]
        vlo, vhi = sorted((vf, vb))
        # box
        vis.box(-hw, hw, vlo, vhi, z0, z1, mat("dark"), faces="tbew" + ("s" if face_sgn > 0 else "n"))
        col.box(-hw, hw, vlo, vhi, z0, z1, cm)
        # face: blue frame, dark screen, orange strip, letters
        fz = vf + face_sgn * 0.02
        nf = (0.0, face_sgn, 0.0)
        frame = [(-hw, fz, z0), (hw, fz, z0), (hw, fz, z1), (-hw, fz, z1)]
        vis.add(frame, mat("blue"), [(0, 0.62), (1, 0.62), (1, 0.62), (0, 0.62)], nf)
        b = 0.6
        fz2 = vf + face_sgn * 0.04
        scr = [(-hw + b, fz2, z0 + 1.6), (hw - b, fz2, z0 + 1.6), (hw - b, fz2, z1 - b), (-hw + b, fz2, z1 - b)]
        vis.add(scr, mat("screen"), auto_uv(scr, mat("screen"), nf), nf)
        strip = [(-hw + b, fz2, z0 + b), (hw - b, fz2, z0 + b), (hw - b, fz2, z0 + 1.3), (-hw + b, fz2, z0 + 1.3)]
        vis.add(strip, mat("orange"), [(0, 0.62)] * 4, nf)
        px = (bd["w"] - 4 * b) / text_rects("THE SWAMP")[1]
        px = min(px, (bd["h"] - 2.6) / 7.0)
        tw = text_width("THE SWAMP", px)
        fz3 = vf + face_sgn * 0.06
        zc = (z0 + 1.6 + z1 - b) / 2 - 3.5 * px
        if face_sgn > 0:
            place_text(vis, "THE SWAMP", (tw / 2, fz3, zc), (-1, 0, 0), (0, 0, 1), px, mat("orange"), nf)
        else:
            place_text(vis, "THE SWAMP", (-tw / 2, fz3, zc), (1, 0, 0), (0, 0, 1), px, mat("orange"), nf)
        # legs
        legs_u = (-hw * 0.65, hw * 0.65)
        vleg = vb - face_sgn * 1.0 if face_sgn > 0 else (vf + vb) / 2
        for lu in legs_u:
            vis.box(lu - 0.75, lu + 0.75, vleg - 0.75, vleg + 0.75, base_z, z0, mat("metal"), faces="nsew")
            col.box(lu - 0.75, lu + 0.75, vleg - 0.75, vleg + 0.75, base_z, z0, cm, faces="nsew")
        out[name] = {"top": (0.0, (vf + vb) / 2, z1), "legs": [(lu, vleg) for lu in legs_u], "base_z": base_z,
                     "z0": z0, "z1": z1, "v_back": vb}
    # south board: catwalk (44 m) behind, 5 service ledges on the back face (46..54 m)
    s = out["south"]
    vb = s["v_back"]
    vis.box(-16.0, 16.0, vb - 3.0, vb, 43.6, 44.0, mat("metal"))
    col.box(-16.0, 16.0, vb - 3.0, vb, 43.6, 44.0, cm, faces="tnsew")
    ledges = []
    for k, z in enumerate((46.0, 48.0, 50.0, 52.0, 54.0)):
        u0 = -3.0 if k % 2 == 0 else 1.0
        vis.box(u0, u0 + 2.0, vb - 1.4, vb, z - 0.3, z, mat("orange"), faces="tbsew", mode="solid")
        col.box(u0, u0 + 2.0, vb - 1.4, vb, z - 0.3, z, cm, faces="tsew")
        ledges.append((u0 + 1.0, vb - 0.7, z))
    s["catwalk"] = (0.0, vb - 1.5, 44.0)
    s["ledges"] = ledges
    # ladder of 11 ledges up the east leg (22..42 m, 2 m apart) from the South Ramp terrace to the
    # catwalk: the board top (Wing Cap box) is reachable without a Lua pole
    lu, lv = s["legs"][1]
    rungs = []
    for k in range(11):
        z = Z_RIM + 2.0 * (k + 1)
        u0 = lu - 2.6 if k % 2 == 0 else lu + 0.2
        v1 = lv - 0.75
        vis.box(u0, u0 + 2.4, v1 - 1.4, v1, z - 0.3, z, mat("orange"), faces="tbnsew", mode="solid")
        col.box(u0, u0 + 2.4, v1 - 1.4, v1, z - 0.3, z, cm, faces="tsew")
        rungs.append((u0 + 1.2, v1 - 0.7, z))
    s["ladder"] = rungs
    return out


def build_goalposts(vis, col):
    gm = mat("goalpost")
    cm = mat("concrete")
    out = []
    for sgn in (1, -1):
        ve = sgn * END_V
        vp = sgn * (END_V + 1.8)
        # base post + gooseneck arm
        vis.box(-0.2, 0.2, vp - 0.2, vp + 0.2, Z_FIELD, CROSSBAR_Z + 0.15, gm, faces="tnsew")
        col.box(-0.2, 0.2, vp - 0.2, vp + 0.2, Z_FIELD, CROSSBAR_Z + 0.15, cm, faces="nsew")
        lo, hi = sorted((ve, vp))
        vis.box(-0.15, 0.15, lo, hi, CROSSBAR_Z - 0.15, CROSSBAR_Z + 0.15, gm, faces="tbew")
        # crossbar (standable, 0.35 m deep) and uprights
        vis.box(-UPRIGHT_HALF - 0.1, UPRIGHT_HALF + 0.1, ve - 0.175, ve + 0.175, CROSSBAR_Z - 0.175,
                CROSSBAR_Z + 0.175, gm)
        col.box(-UPRIGHT_HALF - 0.1, UPRIGHT_HALF + 0.1, ve - 0.175, ve + 0.175, CROSSBAR_Z - 0.175,
                CROSSBAR_Z + 0.175, cm, faces="tbnsew")
        for us in (-1, 1):
            uc = us * UPRIGHT_HALF
            vis.box(uc - 0.1, uc + 0.1, ve - 0.1, ve + 0.1, CROSSBAR_Z + 0.175, UPRIGHT_TOP, gm, faces="tnsew")
            col.box(uc - 0.1, uc + 0.1, ve - 0.1, ve + 0.1, CROSSBAR_Z + 0.175, UPRIGHT_TOP, cm, faces="nsew")
            # orange wind ribbon at the top
            vis.box(uc - 0.11, uc + 0.11, ve - 0.11, ve + 0.11, UPRIGHT_TOP - 1.2, UPRIGHT_TOP - 0.4,
                    mat("orange"), faces="nsew", mode="solid")
        # base pad
        vis.box(-0.6, 0.6, vp - 0.6, vp + 0.6, Z_FIELD, Z_FIELD + 1.8, mat("blue"), faces="tnsew", mode="solid")
        col.box(-0.6, 0.6, vp - 0.6, vp + 0.6, Z_FIELD, Z_FIELD + 1.8, cm, faces="tnsew")
        out.append({"end": "north" if sgn > 0 else "south", "crossbar_center": (0.0, ve, CROSSBAR_Z),
                    "upright_tops": [(-UPRIGHT_HALF, ve, UPRIGHT_TOP), (UPRIGHT_HALF, ve, UPRIGHT_TOP)],
                    "base_post": (0.0, vp, Z_FIELD)})
    # pylons (orange, 8)
    for vv in (GOAL_V, END_V, -GOAL_V, -END_V):
        for uu in (-FOP_HW, FOP_HW):
            sv = 1 if vv > 0 else -1
            su = 1 if uu > 0 else -1
            vis.box(uu, uu + su * 0.1, vv, vv + sv * 0.1, Z_FIELD, Z_FIELD + 0.45, mat("orange"), faces="tnsew",
                    mode="solid")
    return out


def build_light_masts(vis, col):
    """Three 38 m light masts behind the east stands (OSM n582413844, n8001637276, n8001637277)."""
    cm = mat("concrete")
    osm = [(-422.9, 80.4), (-423.4, 123.5), (-423.0, 166.4)]
    out = []
    u_m = A0 + D_OUT + 2.0
    for x, y in osm:
        _, v = to_local(x, y)
        vis.box(u_m - 0.6, u_m + 0.6, v - 0.6, v + 0.6, 0.0, 38.0, mat("metal"), faces="tnsew")
        col.box(u_m - 0.6, u_m + 0.6, v - 0.6, v + 0.6, 0.0, 38.0, cm, faces="tnsew")
        # light bank (facing the field) and catwalk
        ub0, ub1 = u_m - 1.5, u_m - 0.6
        vis.box(ub0, ub1, v - 4.5, v + 4.5, 33.5, 38.0, mat("dark"), faces="tbnse")
        vis.add([(ub0 - 0.02, v - 4.2, 33.8), (ub0 - 0.02, v + 4.2, 33.8), (ub0 - 0.02, v + 4.2, 37.7),
                 (ub0 - 0.02, v - 4.2, 37.7)], mat("white"), None, (-1, 0, 0))
        col.box(ub0, ub1, v - 4.5, v + 4.5, 33.5, 38.0, cm)
        vis.box(ub0 - 1.2, ub0, v - 4.5, v + 4.5, 32.8, 33.1, mat("metal"))
        col.box(ub0 - 1.2, ub0, v - 4.5, v + 4.5, 32.8, 33.1, cm, faces="tnsew")
        out.append({"mast": (u_m, v), "catwalk": (ub0 - 0.6, v, 33.1), "bank_top": (ub0 + 0.45, v, 38.0)})
    return out


# =================================================================== west tower (press box)
TOWER_PLAN = [(-91.9, -50.1), (-98.2, -86.8), (-105.6, -68.9), (-114.8, -46.8), (-115.0, -28.8),
              (-119.0, -28.8), (-119.0, 33.1), (-115.0, 33.1), (-114.6, 49.3), (-110.0, 60.8),
              (-98.3, 88.7), (-91.9, 50.1)]
PAVILION = (-133.0, -119.0, 11.0, 30.0, 10.0)


def build_tower(vis, col, portals):
    cm = mat("concrete")
    plan = C.ccw(TOWER_PLAN)
    u_e = -(A0 + D_OUT)                      # east face (field side) = -91.9
    wgate = [p for p in portals if p.name == "gate_W"][0]
    # west / end facades (all edges but the east one): 0..66
    _, p1_, q0_, q1_, ph_ = PAVILION
    fac = []
    for a, b in zip(plan, plan[1:] + plan[:1]):
        if abs(a[0] - u_e) < 0.05 and abs(b[0] - u_e) < 0.05:
            continue
        if abs(a[0] - p1_) < 0.05 and abs(b[0] - p1_) < 0.05:
            # the stretch behind the pavilion starts at the pavilion roof
            lo_, hi_ = sorted((a[1], b[1]))
            sgn_ = 1 if b[1] > a[1] else -1
            cuts_ = [(lo_, q0_, 0.0), (q0_, q1_, ph_), (q1_, hi_, 0.0)]
            for c0, c1, zb_ in (cuts_ if sgn_ > 0 else cuts_[::-1]):
                if c1 - c0 > 0.05:
                    pa_ = (p1_, c0 if sgn_ > 0 else c1)
                    pb_ = (p1_, c1 if sgn_ > 0 else c0)
                    fac.append((pa_, pb_, zb_))
            continue
        fac.append((a, b, 0.0))
    for a, b, zb in fac:
        dx, dy = b[0] - a[0], b[1] - a[1]
        out = (dy, -dx)
        L = math.hypot(dx, dy)
        out = (out[0] / L, out[1] / L)
        if zb < 6.0:
            vis.wall(a, b, zb, 6.0, mat("brick_plain"), out)
        vis.wall(a, b, max(zb, 6.0), 40.0, mat("brick"), out, tile=4.0)
        vis.wall(a, b, 40.0, 44.0, mat("riser_hi"), out, "stretch")
        vis.wall(a, b, 44.0, Z_PB0, mat("band"), out, tile=4.0)
        vis.wall(a, b, Z_PB0, Z_ROOF - 1.0, mat("glass"), out, tile=4.0)
        vis.wall(a, b, Z_ROOF - 1.0, Z_ROOF + 1.0, mat("white"), out)
        col.wall(a, b, zb, Z_ROOF + 1.0, cm, out)
    # west facade dressing: dark arches at street level, orange / blue banners, block letters
    uw_ = PAVILION[1] - 0.06
    for k, vc in enumerate((-24.0, -14.0, -4.0, 6.0, 16.0, 26.0)):
        role = "riser_hi" if k % 2 == 0 else "riser_lo"
        vis.add([(uw_, vc + 1.5, 14.0), (uw_, vc - 1.5, 14.0), (uw_, vc - 1.5, 32.0), (uw_, vc + 1.5, 32.0)],
                mat(role), [(0, 0.05), (1, 0.05), (1, 0.95), (0, 0.95)], (-1, 0, 0))
    for (a, b) in ((( -114.8, -46.8), (-115.0, -28.8)), ((-115.0, 33.1), (-114.6, 49.3))):
        L = math.dist(a, b)
        dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        o = (dy, -dx)
        for k in range(int(L // 6.0)):
            c0 = 1.5 + k * 6.0
            p0 = (a[0] + dx * c0 + o[0] * 0.05, a[1] + dy * c0 + o[1] * 0.05)
            p1 = (a[0] + dx * (c0 + 3.0) + o[0] * 0.05, a[1] + dy * (c0 + 3.0) + o[1] * 0.05)
            vis.add([(p0[0], p0[1], 0.0), (p1[0], p1[1], 0.0), (p1[0], p1[1], 4.5), (p0[0], p0[1], 4.5)],
                    mat("dark"), None, (o[0], o[1], 0.0))
    pxw = 0.9
    tww = text_width("THE SWAMP", pxw)
    place_text(vis, "THE SWAMP", (PAVILION[1] - 0.08, 2.0 + tww / 2, 55.5), (0, -1, 0), (0, 0, 1), pxw,
               mat("orange"), (-1, 0, 0))
    # east face over the rim: suites (20..43), BGD lounge (44..52); press box cantilever above
    vs, vn = -(B0 - R0), (B0 - R0)
    e0, e1 = (u_e, vs), (u_e, vn)
    vis.wall(e0, e1, Z_RIM, 23.0, mat("concrete"), (1, 0))
    vis.wall(e0, e1, 23.0, 43.0, mat("glass"), (1, 0), tile=4.0)
    vis.wall(e0, e1, 43.0, Z_PB0, mat("glass"), (1, 0), tile=4.0)
    col.wall(e0, e1, Z_RIM, Z_PB0, cm, (1, 0))
    for vv0, vv1 in ((vs, -V_BGD), (V_BGD, vn)):
        vis.wall((u_e, vv0), (u_e, vv1), Z_PB0, Z_ROOF - 1.0, mat("glass"), (1, 0), tile=4.0)
        vis.wall((u_e, vv0), (u_e, vv1), Z_ROOF - 1.0, Z_ROOF + 1.0, mat("white"), (1, 0))
        col.wall((u_e, vv0), (u_e, vv1), Z_PB0, Z_ROOF + 1.0, cm, (1, 0))
    # balcony bands on the suites (visual only, 0.4 m) every 4 m
    for z in (27.0, 31.0, 35.0, 39.0):
        vis.box(u_e, u_e + 0.4, -V_BGD, V_BGD, z - 0.3, z, mat("white"), faces="tbe")
    # Bull Gator Deck: floor slab, front glass railing, end railings (south end open at the face
    # for the ledge climb)
    vis.box(U_BGD, u_e, -V_BGD, V_BGD, Z_BGD - 1.0, Z_BGD, mat("concrete"), faces="bnse",
            mats={"e": mat("riser_hi")}, mode=None)
    vis.flat([(U_BGD, -V_BGD), (u_e, -V_BGD), (u_e, V_BGD), (U_BGD, V_BGD)], Z_BGD, mat("deck"))
    col.box(U_BGD, u_e, -V_BGD, V_BGD, Z_BGD - 1.0, Z_BGD, cm, faces="tbnse")
    vis.wall((U_BGD, -V_BGD), (U_BGD, V_BGD), Z_BGD, Z_BGD + 1.1, mat("window"), (-1, 0))
    vis.wall((U_BGD + 0.05, -V_BGD), (U_BGD + 0.05, V_BGD), Z_BGD, Z_BGD + 1.1, mat("window"), (1, 0))
    col.wall((U_BGD, -V_BGD), (U_BGD, V_BGD), Z_BGD, Z_BGD + 1.1, cm, (-1, 0))
    for vv, open_gap in ((V_BGD, False), (-V_BGD, True)):
        sgn = 1 if vv > 0 else -1
        u_end = u_e + 3.5 if open_gap else u_e
        a, b = (U_BGD, vv), (u_end, vv)
        vis.wall(a, b, Z_BGD, Z_BGD + 1.1, mat("window"), (0, sgn))
        vis.wall(b, a, Z_BGD, Z_BGD + 1.1, mat("window"), (0, -sgn))
        col.wall(a, b, Z_BGD, Z_BGD + 1.1, cm, (0, -sgn))
    # press box cantilever (52..66) over the BGD
    pb = (U_PB, u_e, -V_BGD, V_BGD)
    vis.wall((U_PB, -V_BGD), (U_PB, V_BGD), Z_PB0, Z_PB0 + 1.0, mat("white"), (1, 0))
    vis.wall((U_PB, -V_BGD), (U_PB, V_BGD), Z_PB0 + 1.0, 59.0, mat("glass"), (1, 0), tile=4.0)
    vis.wall((U_PB, -V_BGD), (U_PB, V_BGD), 59.0, 60.0, mat("riser_hi"), (1, 0), "stretch")
    vis.wall((U_PB, -V_BGD), (U_PB, V_BGD), 60.0, Z_ROOF - 1.0, mat("glass"), (1, 0), tile=4.0)
    vis.wall((U_PB, -V_BGD), (U_PB, V_BGD), Z_ROOF - 1.0, Z_ROOF + 1.0, mat("white"), (1, 0))
    col.wall((U_PB, -V_BGD), (U_PB, V_BGD), Z_PB0, Z_ROOF + 1.0, cm, (1, 0))
    for vv in (-V_BGD, V_BGD):
        sgn = 1 if vv > 0 else -1
        vis.wall((U_PB, vv), (u_e, vv), Z_PB0, Z_ROOF + 1.0, mat("glass"), (0, sgn), tile=4.0)
        col.wall((U_PB, vv), (u_e, vv), Z_PB0, Z_ROOF + 1.0, cm, (0, sgn))
    vis.flat([(U_PB, -V_BGD), (u_e, -V_BGD), (u_e, V_BGD), (U_PB, V_BGD)], Z_PB0, mat("dark"), up=False)
    col.flat([(U_PB, -V_BGD), (u_e, -V_BGD), (u_e, V_BGD), (U_PB, V_BGD)], Z_PB0, cm, up=False)
    # "THE SWAMP" on the press box front band (59..60 m is too thin: letters on the glass 60.3..65)
    px = 0.65
    tw = text_width("THE SWAMP", px)
    place_text(vis, "THE SWAMP", (U_PB + 0.05, -tw / 2, 60.4), (0, 1, 0), (0, 0, 1), px, mat("orange"), (1, 0, 0))
    # roof (66) incl. the cantilever, parapet (gap over the camera deck stack)
    roof_plan = C.ccw(plan)
    vis.flat(roof_plan, Z_ROOF, mat("roof"))
    col.flat(roof_plan, Z_ROOF, cm)
    vis.flat([(U_PB, -V_BGD), (u_e, -V_BGD), (u_e, V_BGD), (U_PB, V_BGD)], Z_ROOF, mat("roof"))
    col.flat([(U_PB, -V_BGD), (u_e, -V_BGD), (u_e, V_BGD), (U_PB, V_BGD)], Z_ROOF, cm)
    # parapet inner faces (roof edge), skip the deck stack gap at the front (v -2..2)
    edges = []
    for a, b in zip(roof_plan, roof_plan[1:] + roof_plan[:1]):
        if abs(a[0] - u_e) < 0.05 and abs(b[0] - u_e) < 0.05:
            # east edge: replaced by the cantilever front + the two short end pieces
            continue
        edges.append((a, b))
    lo, hi = sorted((vs, vn))
    edges += [((u_e, vs), (u_e, -V_BGD)),
              ((u_e, V_BGD), (u_e, vn)), ((U_PB, -V_BGD), (U_PB, -2.5)), ((U_PB, 2.5), (U_PB, V_BGD)),
              ((u_e, -V_BGD), (U_PB, -V_BGD)), ((U_PB, V_BGD), (u_e, V_BGD))]
    for a, b in edges:
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        if L < 0.1:
            continue
        # inward normal: toward the roof centre
        nx, ny = -dy / L, dx / L
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        if (nx * (-105.0 - mx) + ny * (0.0 - my)) < 0:
            nx, ny = -nx, -ny
        col.wall(a, b, Z_ROOF, Z_ROOF + 1.0, cm, (nx, ny))
        vis.wall(a, b, Z_ROOF, Z_ROOF + 1.0, mat("concrete"), (nx, ny))
    # light frames on the roof front (field side), 66 -> 71 m
    lights = []
    for vc in (-36.0, -12.0, 12.0, 36.0):
        vis.box(U_PB - 3.5, U_PB - 1.5, vc - 4.0, vc + 4.0, Z_ROOF, Z_ROOF + 5.0, mat("dark"), faces="tnsw")
        vis.add([(U_PB - 1.48, vc - 3.8, Z_ROOF + 1.2), (U_PB - 1.48, vc + 3.8, Z_ROOF + 1.2),
                 (U_PB - 1.48, vc + 3.8, Z_ROOF + 4.8), (U_PB - 1.48, vc - 3.8, Z_ROOF + 4.8)], mat("white"),
                None, (1, 0, 0))
        vis.wall((U_PB - 1.5, vc - 4.0), (U_PB - 1.5, vc + 4.0), Z_ROOF, Z_ROOF + 1.2, mat("dark"), (1, 0))
        col.box(U_PB - 3.5, U_PB - 1.5, vc - 4.0, vc + 4.0, Z_ROOF, Z_ROOF + 5.0, cm, faces="tnsew")
        lights.append((U_PB - 2.5, vc, Z_ROOF + 5.0))
    # climb: 11 ledges (22..42 m) on the south bay of the east face, then 10 camera decks (46..64 m)
    ledges = []
    for k in range(11):
        z = Z_RIM + 2.0 * (k + 1)
        v0 = -47.4 if k % 2 == 0 else -49.6
        vis.box(u_e, u_e + 1.4, v0, v0 + 2.0, z - 0.4, z, mat("orange"), faces="tbnse", mode="solid")
        col.box(u_e, u_e + 1.4, v0, v0 + 2.0, z - 0.4, z, cm, faces="tnse")
        ledges.append((u_e + 0.7, v0 + 1.0, z))
    decks = []
    for k in range(10):
        z = Z_BGD + 2.0 * (k + 1)
        v0 = -2.2 if k % 2 == 0 else 0.2
        u0, u1 = U_BGD - 0.5, U_PB
        # orange like the ledges (fun review: grey decks vanished against the glass of the tower)
        vis.box(u1, u0, v0, v0 + 2.0, z - 0.3, z, mat("orange"), faces="tbnsew" if z < Z_PB0 else "tbnse",
                mode="solid")
        col.box(u1, u0, v0, v0 + 2.0, z - 0.3, z, cm, faces="tnsew" if z < Z_PB0 else "tnse")
        if z < Z_PB0:   # camera stand legs (visual)
            vis.box(u1 + 0.2, u1 + 0.4, v0 + 0.8, v0 + 1.2, Z_BGD, z - 0.3, mat("dark"), faces="nsew")
        decks.append(((u0 + u1) / 2, v0 + 1.0, z))
    # pavilion (Heisman entrance) with the W gate through it
    p0, p1, q0, q1, ph = PAVILION
    pav = [(p0, q0), (p1, q0), (p1, q1), (p0, q1)]
    a_g, b_g = wgate.sc, wgate.w_in
    vg0, vg1 = -(wgate.sc) - wgate.w_in, -(wgate.sc) + wgate.w_in
    vis.wall((p0, q0), (p1, q0), 0.0, ph, mat("brick_plain"), (0, -1))
    vis.wall((p1, q1), (p0, q1), 0.0, ph, mat("brick_plain"), (0, 1))
    col.wall((p0, q0), (p1, q0), 0.0, ph, cm, (0, -1))
    col.wall((p1, q1), (p0, q1), 0.0, ph, cm, (0, 1))
    for (va, vb_) in ((q0, vg0), (vg1, q1)):
        vis.wall((p0, va), (p0, vb_), 0.0, ph - 2.0, mat("brick_plain"), (-1, 0))
        col.wall((p0, va), (p0, vb_), 0.0, ph, cm, (-1, 0))
    vis.wall((p0, vg0), (p0, vg1), GATE_H, ph - 2.0, mat("brick_plain"), (-1, 0))
    col.wall((p0, vg0), (p0, vg1), GATE_H, ph, cm, (-1, 0))
    vis.wall((p0, q0), (p0, q1), ph - 2.0, ph, mat("riser_hi"), (-1, 0), "stretch")
    vis.flat(pav, ph, mat("roof"))
    col.flat(pav, ph, cm)
    _ = (a_g, b_g, pb, lo, hi)
    return {"ledges": ledges, "decks": decks, "lights": lights}


def build_outbuildings(vis, col):
    """North gatehouse, NW loading block, NE Gator Sportshop (OSM outer-ring pieces)."""
    cm = mat("concrete")
    # gatehouse: four piers + roof slab over the north gate (v 108.7 -> 126)
    v0, v1 = B0 + D_SUN_OUT, 126.0
    for u0 in (-13.6, -6.0, 4.4, 12.0):
        vis.box(u0, u0 + 1.6, v1 - 1.6, v1, 0.0, 10.0, mat("brick_plain"), faces="nsew")
        col.box(u0, u0 + 1.6, v1 - 1.6, v1, 0.0, 10.0, cm, faces="nsew")
    vis.box(-13.6, 13.6, v0, v1, 10.0, 11.2, mat("concrete"), faces="tbnew", mats={"n": mat("riser_hi")})
    col.box(-13.6, 13.6, v0, v1, 10.0, 11.2, cm, faces="tbnew")
    # NW loading block (OSM outer zigzag), 6 m
    nw = [to_local(*to_map(u, v)) for u, v in
          [(-58.9, 97.1), (-54.4, 104.3), (-62.0, 112.1), (-61.8, 121.7), (-59.8, 123.5), (-67.4, 131.2),
           (-81.0, 117.5), (-69.0, 105.5), (-74.6, 100.0), (-67.6, 92.0)]]
    vis.prism(nw, 0.0, 6.0, mat("service"), top=mat("roof"), tile=4.0)
    col.prism(nw, 0.0, 6.0, cm, top=cm)
    # NE Gator Sportshop (OSM w858341228, 5 m), clipped clear of the Sunshine back wall
    ne = [(70.5, 93.5), (58.6, 105.2), (62.2, 108.7), (61.3, 109.6), (63.4, 111.5), (63.5, 123.1),
          (61.2, 125.2), (67.5, 131.2), (80.3, 117.4), (73.9, 111.3), (79.9, 105.1), (73.1, 98.3), (75.3, 96.1)]
    vis.prism(ne, 0.0, 5.0, mat("band"), top=mat("roof"), tile=4.0)
    col.prism(ne, 0.0, 5.0, cm, top=cm)
    return {"gatehouse_roof": (0.0, (v0 + v1) / 2, 11.2)}


# =================================================================== layout (portals, spots)
def make_portals():
    P = []
    L1 = (0.0, Z_WALLTOP, L1_N, L1_T, L1_R)
    HB = (D_AISLE1, 0.0, H_N, H_T, H_R)
    NB_ = (D_AISLE1, 0.0, N_LOW, H_T, H_R)
    SUNB = (D_SUN0, Z_SUN, SUN_N, SUN_T, SUN_R)
    d_field_exit = -V_SRAMP - B0      # 66.3
    P.append(Portal("field_tunnel", "S", 0.0, 0.0, d_field_exit, Z_FIELD, 0.0, 4.5, L1, w_in=3.0, kind="field"))
    for name, sname, sc in (("gate_E_south", "E", -30.0), ("gate_E_north", "E", 30.0),
                            ("gate_SE", "SEb", 0.0), ("gate_SW", "SWa", 0.0)):
        P.append(Portal(name, sname, sc, D_AISLE1, D_OUT, 0.0, 0.0, GATE_H, HB))
    # west "Heisman" gate through the tower to the pavilion front (u -133); W segment s = -v
    P.append(Portal("gate_W", "W", -26.5, D_AISLE1, -PAVILION[0] - A0, 0.0, 0.0, GATE_H, HB))
    P.append(Portal("gate_N", "N", 0.0, D_AISLE1, D_SUN_OUT, 0.0, 0.0, GATE_H, NB_))
    P.append(Portal("gate_NE", "NEa", 0.0, D_AISLE1, D_PROM1, 0.0, 0.0, GATE_H, NB_))
    P.append(Portal("gate_NW", "NWb", 0.0, D_AISLE1, D_PROM1, 0.0, 0.0, GATE_H, NB_))
    # Sunshine vomitories (22 m) toward the helix towers
    for name, sname, hc in (("vom_NE", "NEb", HELIX_NE), ("vom_NW", "NWa", HELIX_NW)):
        i = SI[sname]
        _, _, mid, t, _, _ = seg(i, D_SUN_OUT)
        sc = (hc[0] - mid[0]) * t[0] + (hc[1] - mid[1]) * t[1]
        # keep the whole tunnel on this chord (the chord is shortest at the mouth)
        lim = half(i, D_SUN0) - (GATE_W + WALL_T) - 0.3
        sc = max(-lim, min(lim, sc))
        P.append(Portal(name, sname, sc, D_SUN0, D_SUN_OUT, Z_SUN, Z_SUN, GATE_H, SUNB, kind="vomitory"))
    return P


# OSM circles (outer ring of r1640985): the two helix ramp towers north of the Sunshine Seats
HELIX_NE = (37.8, 122.8)
HELIX_NW = (-37.8, 122.8)


def portal_band(p):
    if p.kind == "field":
        return (0.0, Z_WALLTOP, L1_N, L1_T, L1_R)
    if p.kind == "vomitory":
        return (D_SUN0, Z_SUN, SUN_N, SUN_T, SUN_R)
    if p.seg in N_SEGS:
        return (D_AISLE1, 0.0, N_LOW, H_T, H_R)
    return (D_AISLE1, 0.0, H_N, H_T, H_R)


def ground_hole(portals):
    """Ring at the cross-aisle's outer edge + the south field tunnel slot (local, CCW)."""
    r = ring(D_AISLE1)
    ft = [p for p in portals if p.kind == "field"][0]
    w = ft.w
    i = SI["S"]
    # insert the slot into the S side (from SW2 to SE0 going east along v = -(B0 + D_AISLE1))
    out = []
    for k, p in enumerate(r):
        out.append(p)
        if k == SI["S"]:
            vy = p[1]
            out += [(-w, vy), (-w, V_SRAMP), (w, V_SRAMP), (w, vy)]
    _ = i
    return out


def helix_portal_bridge(vis, col, portals):
    """Short bridges from the helix top landings to the vomitory openings in the Sunshine back wall."""
    out = []
    for p, hc in ((next(q for q in portals if q.name == "vom_NE"), HELIX_NE),
                  (next(q for q in portals if q.name == "vom_NW"), HELIX_NW)):
        i = p.i
        n = seg_normal(i)
        a = spt(i, D_SUN_OUT, p.sc)
        # helix top direction = toward the portal (from the helix centre)
        ang = math.degrees(math.atan2(a[1] - hc[1], a[0] - hc[0]))
        out.append((p, hc, ang))
        r_out = 14.0
        q = (hc[0] + r_out * math.cos(math.radians(ang)), hc[1] + r_out * math.sin(math.radians(ang)))
        # the collision deck overlaps the helix landing (whose outer edge is a chord, up to 5 cm inside
        # q) by 0.4 m and the vomitory floor by 0.9 m (the bridge meets the vomitory's exit edge at ~13
        # degrees, so its square end must pass that edge at both corners): no seams at 22 m (integration
        # crack scan: map (-549, 232), (-547, 227), (-480, 227), (-478, 232))
        bridge(vis, col, [(q[0], q[1], Z_SUN), (a[0] + n[0] * 0.05, a[1] + n[1] * 0.05, Z_SUN)], p.w_in - 0.2,
               col_ext=(0.4, 0.9))
    return out


# =================================================================== assembly
def generate():
    """Build every polygon (local frame). -> dict with Geo collectors and layout data."""
    vis, fld, col = Geo("visual"), Geo("field"), Geo("collision")
    portals = make_portals()
    build_field(fld, col)
    build_field_wall(vis, col, portals)
    build_bowl(vis, col, portals)
    build_end_walls(vis, col)
    build_sunshine(vis, col, portals)
    for p in portals:
        portal_geometry(vis, col, p, portal_band(p))
    build_corner_access(vis, col)
    hx = []
    for p, hc, ang in helix_portal_bridge(vis, col, portals):
        hx.append(build_helix(vis, col, hc, ang, "helix_" + p.name[-2:]))
    south_plan = build_south(vis, col, portals)
    boards = build_boards(vis, col)
    goals = build_goalposts(vis, col)
    masts = build_light_masts(vis, col)
    tower = build_tower(vis, col, portals)
    outb = build_outbuildings(vis, col)
    return {"vis": vis, "field": fld, "col": col, "portals": portals, "helices": hx, "boards": boards,
            "goals": goals, "masts": masts, "tower": tower, "out": outb, "south_plan": south_plan}


def _m3(p):
    x, y = to_map(p[0], p[1])
    return (round(x, 2), round(y, 2), round(p[2], 2))


def _m2(p):
    x, y = to_map(p[0], p[1])
    return (round(x, 2), round(y, 2))


def layout_extras(G):
    """Spots / markers / climb route in MAP metres (z = height above grade)."""
    portals, boards, tower, goals, masts = G["portals"], G["boards"], G["tower"], G["goals"], G["masts"]
    zf = Z_FIELD
    spots = {
        "field_center": _m3((0.0, 0.0, zf)),
        "midfield_mascot_arena": _m3((0.0, 0.0, zf)),
        "endzone_button_NW": _m3((-FOP_HW + 1.0, END_V - 1.0, zf)),
        "endzone_button_NE": _m3((FOP_HW - 1.0, END_V - 1.0, zf)),
        "endzone_button_SW": _m3((-FOP_HW + 1.0, -END_V + 1.0, zf)),
        "endzone_button_SE": _m3((FOP_HW - 1.0, -END_V + 1.0, zf)),
        "fg_crossbar_north": _m3((0.0, END_V, CROSSBAR_Z)),
        "fg_crossbar_south": _m3((0.0, -END_V, CROSSBAR_Z)),
        "fg_tee_north_20yd": _m3((0.0, GOAL_V - 18.288, zf)),
        "fg_tee_north_30yd": _m3((0.0, GOAL_V - 27.432, zf)),
        "fg_tee_south_20yd": _m3((0.0, -GOAL_V + 18.288, zf)),
        "usher_npc": _m3((7.0, -B0 + 2.5, zf)),
        "cannon_north_endzone": _m3((-14.0, (GOAL_V + END_V) / 2, zf)),
        "spirit_pad_1": _m3((-13.0, B0 + (D_AISLE0 + D_AISLE1) / 2, 0.0)),
        "spirit_pad_2": _m3((-6.5, B0 + (D_AISLE0 + D_AISLE1) / 2, 0.0)),
        "spirit_pad_3": _m3((6.5, B0 + (D_AISLE0 + D_AISLE1) / 2, 0.0)),
        "spirit_pad_4": _m3((13.0, B0 + (D_AISLE0 + D_AISLE1) / 2, 0.0)),
        "south_board_top": _m3(boards["south"]["top"]),
        "wing_cap_box": _m3((0.0, boards["south"]["top"][1], boards["south"]["top"][2] + 1.5)),
        "south_board_catwalk": _m3(boards["south"]["catwalk"]),
        "north_board_top": _m3(boards["north"]["top"]),
        "south_ramp_terrace": _m3((0.0, -(B0 + D_OUT) - 2.0, Z_RIM)),
        "south_ramp_bottom": _m3((U_SBLOCK - 2.0, (V_SBLOCK + V_SRAMP) / 2, 0.0)),
        "field_tunnel_mid": _m3((0.0, -B0 - 33.0, -10.0 + 33.0 * 10.0 / 66.3)),
        "field_tunnel_exit": _m3((0.0, V_SRAMP - 2.0, 0.0)),
        "under_sunshine_promenade": _m3((0.0, B0 + (D_PROM0 + D_PROM1) / 2, Z_PROM)),
        "sunshine_front_walkway": _m3((0.0, B0 + (D_SUN_F + D_SUN0) / 2, Z_SUN)),
        "sunshine_top_row": _m3((0.0, B0 + D_SUN_RIM0 + 1.0, Z_SUN_TOP)),
        "east_rim": _m3((A0 + (D_RIM0 + D_RIM1) / 2, 0.0, Z_RIM)),
        "west_rim": _m3((-(A0 + (D_RIM0 + D_RIM1) / 2), -47.0, Z_RIM)),
        "bull_gator_deck": _m3(((U_BGD - (A0 + D_OUT)) / 2, 0.0, Z_BGD)),
        "press_box_roof_star": _m3((-104.0, 0.0, Z_ROOF)),
        "light_frame_top": _m3(tower["lights"][1]),
        "helix_NE_top": _m3(G["helices"][0]["top"]),
        "helix_NW_top": _m3(G["helices"][1]["top"]),
        "helix_NE_bottom": _m3(G["helices"][0]["bottom"]),
        "helix_NW_bottom": _m3(G["helices"][1]["bottom"]),
        "north_courtyard": _m3((0.0, 140.0, 0.0)),
        "suggested_stage_spawn": _m3((0.0, 150.0, 0.0)),
        "gatehouse_roof": _m3(G["out"]["gatehouse_roof"]),
        "east_light_catwalk_center": _m3(masts[1]["catwalk"]),
    }
    for g in goals:
        spots[f"goalpost_{g['end']}_base"] = _m3(g["base_post"])
    for p in portals:
        spots[f"tunnel_{p.name}_mouth"] = _m3(spt(p.i, p.d0 + 0.5, p.sc, p.floor_at(p.d0)))
        spots[f"tunnel_{p.name}_exit"] = _m3(spt(p.i, p.d_exit + 1.5, p.sc, p.floor_at(p.d_exit)))
    climb = [_m3((-(A0 + D_RIM0 + 1.0), -48.5, Z_RIM))]
    climb += [_m3(p) for p in tower["ledges"]]
    climb.append(_m3(((U_BGD - (A0 + D_OUT)) / 2, -42.0, Z_BGD)))
    climb += [_m3(p) for p in tower["decks"]]
    climb.append(_m3((-90.0, 0.0, Z_ROOF)))
    climb.append(_m3(tower["lights"][1]))
    board_climb = [_m3((boards["south"]["legs"][1][0], boards["south"]["legs"][1][1] - 3.0, Z_RIM))]
    board_climb += [_m3(p) for p in boards["south"]["ladder"]]
    board_climb.append(_m3(boards["south"]["catwalk"]))
    board_climb += [_m3(p) for p in boards["south"]["ledges"]]
    board_climb.append(_m3(boards["south"]["top"]))
    # race loop on the apron (field level, 3.5 m outside the sidelines / end lines)
    lu, lv = FOP_HW + 4.2, END_V + 3.6
    loop = [(lu, -lv + 4), (lu, lv - 4), (lu - 4, lv), (-lu + 4, lv), (-lu, lv - 4), (-lu, -lv + 4),
            (-lu + 4, -lv), (lu - 4, -lv)]
    race_loop = [_m3((u, v, zf)) for u, v in loop]
    # stair sprint: north end zone -> NE field corner -> diagonally up the east stands -> east rim ->
    # SE rim -> south ramp terrace
    sprint = [(0.0, 50.0, zf), (28.0, 58.0, zf), (A0 + 1.0, 40.0, Z_WALLTOP), (A0 + D_AISLE0 + 1.0, 30.0, 0.0),
              (A0 + 36.0, 15.0, 9.5), (A0 + D_RIM0 + 1.0, 0.0, Z_RIM), (A0 + D_RIM0 + 1.0, -45.0, Z_RIM)]
    se = ring(D_RIM0 + 1.25)
    sprint += [(se[SI["SEb"]][0], se[SI["SEb"]][1], Z_RIM), (se[SI["SEa"]][0], se[SI["SEa"]][1], Z_RIM),
               (0.0, -(B0 + D_RIM0 + 4.0), Z_RIM)]
    sprint_m = [_m3(p) for p in sprint]
    rings = [(0.0, 0.0, 35.0), (0.0, -60.0, 40.0), (40.0, -95.0, 45.0), (80.0, -20.0, 42.0),
             (70.0, 60.0, 45.0), (0.0, 100.0, 55.0), (-70.0, 60.0, 72.0), (-80.0, -40.0, 60.0)]
    poles = [
        {"name": "goalpost_north", "base_m": _m3(goals[0]["base_post"]), "height_m": 3.0},
        {"name": "goalpost_south", "base_m": _m3(goals[1]["base_post"]), "height_m": 3.0},
        {"name": "bgd_to_press_box_roof", "base_m": _m3((U_BGD - 1.0, 5.5, Z_BGD)), "height_m": 22.5},
        {"name": "south_board_leg", "base_m": _m3((boards["south"]["legs"][0][0] + 1.2, boards["south"]["legs"][0][1],
                                                    Z_RIM)), "height_m": 24.2},
    ]
    for k, m in enumerate(masts):
        poles.append({"name": f"east_light_mast_{k + 1}",
                      "base_m": _m3((A0 + D_OUT + 0.4, m["mast"][1] + 1.6, Z_PARAPET)), "height_m": 12.0})
    gates = []
    for p in portals:
        nrm = seg_normal(p.i)
        gates.append({"name": p.name, "kind": p.kind, "mouth_m": _m3(spt(p.i, p.d0, p.sc, p.floor_at(p.d0))),
                      "exit_m": _m3(spt(p.i, p.d_exit, p.sc, p.floor_at(p.d_exit))),
                      "width_m": 2 * p.w_in, "clear_height_m": p.height,
                      "exit_facing_deg": bearing_of(nrm[0], nrm[1])})
    markers = {
        "scoreboard_climb_m": board_climb,
        "race_loop_m": race_loop,
        "stair_sprint_m": sprint_m,
        "flyover_rings_m": [_m3(p) for p in rings],
        "poles": poles,
        "gates": gates,
        "levels_m": {"field": Z_FIELD, "field_wall_top": Z_WALLTOP, "cross_aisle": 0.0, "promenade": Z_PROM,
                     "rim": Z_RIM, "sunshine_walkway": Z_SUN, "sunshine_top_row": Z_SUN_TOP, "bull_gator_deck": Z_BGD,
                     "press_box_roof": Z_ROOF, "light_frames_top": Z_ROOF + 5.0,
                     "south_board": [SB["z0"], SB["z0"] + SB["h"]], "north_board": [NB["z0"], NB["z0"] + NB["h"]]},
        "note": "positions in map metres (x east, y north, z = metres above grade); the field is 10 m below grade",
    }
    top_platform = {"z_m": Z_ROOF, "center_m": _m2((-104.0, 0.0)),
                    "note": "press box / skybox roof (whole west tower), 1 m parapet with a gap over the camera "
                            "deck stack; four light frames (top 71 m) along the field edge"}
    return spots, markers, climb, top_platform


def _layout_cache():
    if not hasattr(_layout_cache, "G"):
        _layout_cache.G = generate()
    return _layout_cache.G


_G0 = _layout_cache()
_SPOTS, _MARKERS, _CLIMB, _TOP = layout_extras(_G0)
_HOLE = [[_m2(p) for p in C.ccw(ground_hole(_G0["portals"]))]]

LANDMARKS = [
    {
        "slug": SLUG,
        "name": "Ben Hill Griffin Stadium (The Swamp)",
        "stages": ["swamp"],
        "osm_ids": [STADIUM_ID] + PART_IDS,
        "center_m": _m2((0.0, 0.0)),
        "height_m": Z_ROOF,
        "doors": [],
        "replaces_areas": INNER_AREA_IDS,
        "replaces_ways": INNER_WAY_IDS,
        "ground_holes_m": _HOLE,
        "spots": _SPOTS,
        "markers": _MARKERS,
        "climb_route_m": _CLIMB,
        "top_platform": _TOP,
    },
]


def build(ctx):
    """-> [{"name", "mesh", "material_slots", "collision", "visual", "landmark"}, ...] (map metres)."""
    if ctx.get("stage_key") not in (None, "swamp"):
        return []
    G = generate()
    parts = []
    for key, pname, collision, visual in (("vis", f"{SLUG} visual", False, True),
                                          ("field", f"{SLUG} field", False, True),
                                          ("col", f"{SLUG} collision", True, False)):
        g = G[key]
        me, slots = to_mesh(g, pname)
        parts.append({"name": pname, "mesh": me, "material_slots": slots, "collision": collision,
                      "visual": visual, "landmark": SLUG})
    nv = G["vis"].tris() + G["field"].tris()
    print(f"stadium (swamp_stadium.py): visual {nv} tris (bowl+structures {G['vis'].tris()}, "
          f"field {G['field'].tris()}), "
          f"collision {G['col'].tris()} tris (budget 9000 / 2600)")
    return parts


def triangulate(pts):
    """Ear clipping of a simple planar polygon (3D points) -> list of index triples (same winding)."""
    n = len(pts)
    if n <= 3:
        return [tuple(range(n))]
    nx, ny, nz = newell(pts)
    ax = max(range(3), key=lambda k: abs((nx, ny, nz)[k]))
    i0, i1 = [(1, 2), (2, 0), (0, 1)][ax]
    sgn = 1.0 if (nx, ny, nz)[ax] > 0 else -1.0
    P = [(p[i0], p[i1] * sgn) for p in pts]

    def area2(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    def in_tri(p, a, b, c):
        d1, d2, d3 = area2(a, b, p), area2(b, c, p), area2(c, a, p)
        return d1 >= -1e-9 and d2 >= -1e-9 and d3 >= -1e-9
    idx = list(range(n))
    out = []
    guard = 0
    while len(idx) > 3 and guard < 10000:
        guard += 1
        m = len(idx)
        for k in range(m):
            ia, ib, ic = idx[k - 1], idx[k], idx[(k + 1) % m]
            a, b, c = P[ia], P[ib], P[ic]
            if area2(a, b, c) <= 1e-9:
                continue
            if any(in_tri(P[j], a, b, c) for j in idx if j not in (ia, ib, ic)
                   and P[j] not in (a, b, c)):
                continue
            out.append((ia, ib, ic))
            idx.pop(k)
            break
        else:
            # degenerate remainder: fan it
            for k in range(1, len(idx) - 1):
                out.append((idx[0], idx[k], idx[k + 1]))
            return out
    out.append(tuple(idx))
    return out


def to_mesh(g, name):
    """Geo (local) -> bpy mesh in map metres with a UV layer (collision meshes get dummy UVs)."""
    import bmesh
    import bpy
    slots = []
    for _, m, _ in g.polys:
        if m not in slots:
            slots.append(m)
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    cache = {}

    def vert(p):
        x, y = to_map(p[0], p[1])
        key = (round(x, 4), round(y, 4), round(p[2], 4))
        v = cache.get(key)
        if v is None:
            v = bm.verts.new((x, y, p[2]))
            cache[key] = v
        return v
    for pts, m, uvs in g.polys:
        if uvs is None:
            uvs = auto_uv(pts, m, None)
        for tri in triangulate(pts):
            fp = [pts[k] for k in tri]
            fu = [uvs[k] for k in tri]
            try:
                f = bm.faces.new([vert(p) for p in fp])
            except ValueError:
                # duplicate face (same vertex set): build it from fresh vertices
                try:
                    f = bm.faces.new([bm.verts.new((*to_map(p[0], p[1]), p[2])) for p in fp])
                except ValueError:
                    continue
            f.material_index = slots.index(m)
            for loop, (u, v) in zip(f.loops, fu):
                loop[uvl].uv = (u, v)
    bm.to_mesh(me)
    bm.free()
    return me, slots
