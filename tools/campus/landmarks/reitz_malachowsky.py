"""REITZ UNION + ENGINEERING stage landmark: Malachowsky Hall for Data Science & Information Technology
(UF, opened 3 Nov 2023) and its entrance plaza, hand-modelled for GatorCampus 64.

Landmark module (contract: tools/campus/landmarks/_common.py). The single LANDMARKS entry carries
"stages": ["reitz_eng"], so only `build_stage.py reitz_eng` builds it. Geometry is in MAP METRES, z up
(x = east, y = north, origin = Century Tower), on the exact OSM footprint in data/uf/campus.json:

  Malachowsky Hall w1094502850 3,940 m2 roof 33.0 m budget 300 collision / 1200 visual tris
                     (stages.json reitz_eng landmark, "detailed", height 33 m)

build(ctx) returns three parts, all with "landmark": "malachowsky_hall": the visual mesh, a
visual-only "decal" paving part (plaza + atrium floor, moved under the collision floor by the
generator) and one low-poly collision mesh. Collision walls face out of the solids (into the
atrium inside it); every collision floor is flat or under 5 degrees.

WHAT THE SOURCES SAY (reviewed)
  - Bohlin Cywinski Jackson (design) with Walker Architects (Gainesville). Seven storeys, 263,440 sq ft,
    $150 M, opened 3 Nov 2023, across Museum Road from the Reitz Union (Wikipedia; UF HWCOE).
  - A compact, rectilinear seven-storey block built on a former 400-space parking lot; it went taller
    than planned so the rest of the site stays a public green (BCJ / The Plan; BCJ project page).
    North faces the new Campus Green, the south is approached from the Engineering district, the east
    has a secondary entrance (AIA Tri-State). The site slopes: the north and south entrances are on
    different levels (BCJ / The Plan; OSM: south doors level 0, north/east doors level 1).
  - Skin: ~1,500 prefabricated, custom-folded aluminium rainscreen panels (typical panel 6 x 7.5 ft =
    1.8 x 2.3 m) in three shapes, rotated and mirrored; "origami-like creases" give idiosyncratic
    trapezoidal / triangular electrochromic windows. Panels are denser on the south and west, more
    open on the north and east. Finish: a neutral silver PVDF (PPG Duranar / Kynar 500) with varying
    metallic flake, chosen against the Florida glare (AIA PA awards; Arkema; The Architect's
    Newspaper 2022-01 via search summary; BCJ / The Plan).
  - "A band of clear glass rises up the north side in a stepped form", drawing daylight into breakout
    areas at different levels (BCJ / The Plan); renderings show the rectilinear massing broken up by
    cantilevered glass volumes for the social spaces (The Architect's Newspaper caption, via search).
    Communal areas sit behind ceramic-fritted curtain wall (Arkema).
  - Inside: a seven-level "vertical commons" / atrium with a grand stair from the top tier to the
    ground-floor lobby and a building-length pedestrian boulevard (UF HWCOE; BCJ; Walker Architects);
    ground-floor makerspaces for robotics / VR / IoT; rooftop terraces; a 150-person forum with
    panoramic campus views (BCJ project page; AIA PA; Tradeline via search).
  - OSM: entrances north (w/ the N-S indoor corridor, node 11254215508), south x2, east (node
    11254215506), service and a west loading dock; the cafe "Beans n Bytes" in the NW corner; the
    plaza in front (north) is the paved forecourt where the two diagonal Campus Green walks meet the
    main door.

MODELLED AS
  - The OSM outline (24 nodes; 8 near-collinear nodes dropped, every OSM node stays within 1.4 cm of
    the modelled outline -> 16 walls), extruded to a flat roof at 33.0 m: ground floor 0-5.0 m, six
    upper floors of 4.6-5.0 m.
  - The folded skin on every wall above 5.0 m: a vertex grid with one row per floor (columns 3.66 m =
    two 6-ft panels on the north front, 7.32 m on the east; ~8 m columns and two-storey rows on the
    denser south and west) whose interior vertices are pushed 0, 0.3 or 0.6 m INTO the wall (three
    panel shapes), each cell split along one of its two diagonals (rotated / mirrored panels). Facets
    are silver (metal_gray) or light-flake silver (white_trim); triangular electrochromic windows
    (window_dark) are inset in ~65 % of the north/east cells and ~40 % of the south/west cells.
    Collision stays on the outer (OSM) plane.
  - Ground floor: clear glass lobby (north, east), tinted makerspace glass (south), metal + an overhead
    loading door (west). The east bump (OSM nodes 17-22) is a full-height clear-glass stair / forum
    tower.
  - THE STEPPED GLASS BAND: eleven cantilevered glass breakout boxes (3.0 m deep) stepping 2.33 m at a
    time across the north facade, from the entrance canopy (5.0 m) to the north-east roof corner
    (30.67 m), under one sloped white soffit. Over the 2.9 m deep OSM recess (nodes 12-15) the four
    middle boxes fill the recess back to its wall: deeper "terraces" there.
  - The entrance canopy: a folded (trapezoidal, 4-degree) cantilever over the main north door, 3.2 m
    at its west tip rising to 5.0 m where it meets the first glass box.
  - The vertical commons as a cheap interior: the north door opens into a 6 m wide passage and a
    26 x 17 m atrium, 32.2 m clear (glass walls with floor bands, skylight), with a 3.5 m deep L7
    "star ledge" at 28.0 m along its south wall and a server-room alcove at its west side. No stair
    inside: the atrium is the Remote Robotics Lab (game_design 7.2 act 2, a co-op crane ride).
  - Roof: a light membrane roof, the atrium skylight lantern (35.33 m), a mechanical penthouse with
    louvres (37.67 m, the top platform) and a raised rooftop terrace deck at the north-east.
  - The plaza: paved forecourt along the whole north facade with two pale bands continuing the
    diagonal Campus Green walks to the door, a raised planter (1.0 m) and a seat wall (0.45 m).
  Not modelled: the real grand stair (it would let a solo player bypass the co-op crane), the site
  slope (the campus is flat in this game), lettering (no sign texture), bike racks and furniture.

GAMEPLAY (SM64 default surfaces; rises <= 2.33 m, i.e. one running jump or a double jump)
  - "THE GLASS STAIR", plaza -> roof: planter (1.0) -> canopy west tip (3.2) -> walk up the canopy
    (5.0) -> 11 glass boxes, 7.33... 30.67 m (2.33 m rises, 5.3 m treads; four deeper recess
    terraces at 14.33-21.33) -> roof (33.0) -> skylight lantern (35.33) -> penthouse (37.67).
  - The atrium: the north door (6 x 3.6 m) -> passage -> atrium floor; the star ledge (28.0 m) is
    only reachable by a mission platform (spots: atrium_console, crane_start, star_ledge).
  - The server-room alcove (spot server_room_dock) is the Data Packet Relay finish (act 6); the
    canopy top (canopy_coin) was the Meal Swipe Tokens "Malachowsky canopy" coin (act 5) until the
    Course 2 fix round moved that token up to the 12 m glass box of the climb route
    (stage_points.reitz_token_spots).

Sources (reviewed)
  - UF Herbert Wertheim College of Engineering, Malachowsky Hall page:
https://www.eng.ufl.edu/about/new-buildings/malachowsky-hall-for-data-science-information-technology/
  - Bohlin Cywinski Jackson project page:
    https://www.bcj.com/projects/academic/university-of-florida-malachowsky-hall-for-data-science-information-technology/
  - BCJ, "University of Florida Malachowsky Hall featured in The Plan" (stepped north glass band, panel
    pattern by orientation, sloping site, former parking lot):
    https://www.bcj.com/news/university-of-florida-malachowsky-hall-featured-in-the-plan/
  - AIA Pennsylvania awards gallery (6' x 7.5' folded aluminium panel, vertical commons, forum):
    https://aiapa_awards.secure-platform.com/a/gallery/rounds/36/details/2743
  - AIA Tri-State awards gallery (orientation of the four elevations):
    https://aia_tri-state_awards.secure-platform.com/a/gallery/rounds/41/details/3132
  - Arkema Kynar 500 case study (aluminium plate, PVDF finish, fritted curtain wall):
    https://kynar500.arkema.com/en/media/case-studies/malachowsky-hall-university-of-florida/
  - The Architect's Newspaper, 2022-01 (neutral silver, 1.8 x 2.3 m panels, cantilevered glass
    volumes; page refused direct reading, details from search summaries):
    https://www.archpaper.com/2022/01/malachowsky-hall-deflects-florida-glare-with-aluminum-facade-and-electrochromatic-glazing/
  - Kawneer project page (trapezoidal facade, curtain wall, public green):
    https://www.kawneer.com/projects/education/uf-malachowsky-hall/
  - Wikipedia, "Malachowsky Hall for Data Science & Information Technology":
    https://en.wikipedia.org/wiki/Malachowsky_Hall_for_Data_Science_%26_Information_Technology
  - OpenStreetMap way 1094502850 (footprint), entrance nodes 11254215506/07/08, 13505680290,
    11254215510, loading dock 11254215505, indoor corridors 1471511654 / 1214700202, grass areas
    1471511671/72/73 and footways 1205038961/62, 1224007461 (plaza edges)
"""
import math
import os
import sys

try:
    from landmarks import _common as C
except ImportError:  # imported as a top-level module: make the `landmarks` package importable
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from landmarks import _common as C

STAGES = ["reitz_eng"]
SLUG = "malachowsky_hall"
MAL_ID = "w1094502850"
EPS = 1e-6

# OSM footprint of w1094502850 exactly as in campus.json (clockwise, map metres); indices are used below
FP_OSM = [(-384.98, -554.99), (-409.89, -554.8), (-416.58, -554.76), (-416.55, -550.25), (-427.06, -550.17),
          (-452.86, -549.98), (-482.21, -549.76), (-482.05, -530.05), (-481.99, -520.02), (-485.7, -519.98),
          (-485.63, -511.0), (-452.33, -511.24), (-426.62, -511.44), (-426.65, -514.29), (-405.58, -514.45),
          (-405.55, -511.48), (-383.3, -511.64), (-383.32, -513.94), (-380.78, -513.95), (-378.78, -513.97),
          (-378.84, -522.74), (-380.94, -522.72), (-384.74, -522.7), (-384.83, -535.02)]
MERGE_TOL = 0.06          # drop OSM nodes closer than this to the line through their neighbours

# ---------------------------------------------------------------- heights (m above grade)
Z_BASE = -0.2             # walls start a little under the generator's ground layers
Z_L2 = 5.0                # ground floor 0-5.0 (lobby / makerspaces)
ROWS_FINE = (5.0, 9.6, 14.2, 18.8, 23.4, 28.0, 33.0)      # one skin row per floor (north, east)
ROWS_COARSE = (5.0, 14.2, 23.4, 33.0)                     # two-storey rows (south, west: denser panels)
Z_ROOF = 33.0
RISE = (Z_ROOF - Z_L2) / 12.0                             # 2.333 m per glass box
FOLD_DEPTHS = (0.0, 0.3, 0.6)                             # the three panel shapes (inward offsets)
COL_N, COL_E, COL_S = 3.66, 7.32, 8.2                     # skin column width (2 / 4 panels of 6 ft; south+west)

# ---------------------------------------------------------------- the stepped glass band (north)
BAND_D = 3.0              # cantilever depth in front of the facade
BAND_N = 11
BAND_BOT = (3.4, 26.0)    # soffit height at the west and east ends of the band
TREAD_EMBED = 0.15        # collision treads reach this far into the wall behind them
VIS_EMBED = 0.8           # visual band faces reach behind the deepest skin folds

# ---------------------------------------------------------------- entrance canopy (north door)
CAN_X0 = -468.0           # west tip (map x)
CAN_Z = (3.2, 5.0)        # top at the west tip / at the first glass box
CAN_V = (5.0, BAND_D)     # projection at the west tip / at the band
CAN_T = 0.35              # slab thickness
DOOR_W, DOOR_H = 6.0, 3.6

# ---------------------------------------------------------------- atrium (vertical commons) interior
ATR = (-466.0, -440.0, -534.0, -517.0)    # x0, x1, y0, y1
ATR_CEIL = 32.2
LEDGE_Z, LEDGE_D, LEDGE_T = 28.0, 3.5, 0.6
ALCOVE = (-470.5, -530.5, -521.5, 4.0)    # back x, y0, y1, height (server room, west side)
SLAB_BANDS = (5.0, 9.6, 14.2, 18.8, 23.4)

# ---------------------------------------------------------------- roof features
LANTERN = (-464.0, -442.0, -532.0, -519.0, Z_ROOF + RISE)          # atrium skylight monitor
PENTHOUSE = (-480.5, -467.0, -546.5, -516.5, Z_ROOF + 2 * RISE)     # mechanical penthouse
TERRACE = (-403.5, -386.5, -527.0, -514.8, Z_ROOF + 0.25)           # rooftop terrace deck

# ---------------------------------------------------------------- plaza (map metres)
PLANTER = (-475.0, -470.0, 0.8, 3.6, 1.0)     # x0, x1 (map), v0, v1 (in front of the facade), top
SEATWALL = (-441.5, -432.5, 3.6, 4.2, 0.45)
# paved forecourt along the north facade: OSM grass edges (w1471511672/73/71) and the facade
PLAZA_NORTH = [(-479.3, -505.75), (-462.8, -506.4), (-458.7, -505.9), (-445.2, -506.4), (-438.2, -506.9),
               (-383.3, -508.0)]
# pale bands that carry the two diagonal Campus Green walks (w1224007461, w1205038962) to the door
PLAZA_BANDS = [((-459.7, -507.9), (-454.3, -511.1)), ((-443.9, -508.3), (-450.3, -511.1))]


# =================================================================== small helpers
def _r(p, nd=2):
    return tuple(round(float(c), nd) for c in p)


def _hash(*k):
    h = 2166136261
    for v in k:
        h = ((h ^ (int(v) & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
        h ^= h >> 13
        h = (h * 0x5BD1E995) & 0xFFFFFFFF
        h ^= h >> 15
    return h


def _line_dev(p, a, c):
    dx, dy = c[0] - a[0], c[1] - a[1]
    L = math.hypot(dx, dy)
    return abs((p[0] - a[0]) * dy - (p[1] - a[1]) * dx) / max(L, EPS)


def _merge(pts, tol):
    """Drop nodes that lie within tol of the line through their neighbours (repeat until stable)."""
    pts = list(pts)
    changed = True
    while changed and len(pts) > 4:
        changed = False
        for i in range(len(pts)):
            a, p, c = pts[i - 1], pts[i], pts[(i + 1) % len(pts)]
            if _line_dev(p, a, c) < tol:
                del pts[i]
                changed = True
                break
    return pts


def _inside(pt, poly):
    x, y = pt
    c = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            if x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                c = not c
    return c


def _clip_x(poly, x0, x1):
    """Sutherland-Hodgman clip of a polygon [(x, y), ...] to the slab x0 <= x <= x1."""
    def clip(pts, keep, cross):
        out = []
        for i in range(len(pts)):
            p, q = pts[i - 1], pts[i]
            if keep(q):
                if not keep(p):
                    out.append(cross(p, q))
                out.append(q)
            elif keep(p):
                out.append(cross(p, q))
        return out

    def at(xc):
        return lambda p, q: (xc, p[1] + (q[1] - p[1]) * (xc - p[0]) / (q[0] - p[0]))
    pts = clip(list(poly), lambda p: p[0] >= x0, at(x0))
    pts = clip(pts, lambda p: p[0] <= x1, at(x1)) if pts else pts
    out = []
    for p in pts:
        if not out or math.dist(p, out[-1]) > 1e-4:
            out.append(p)
    if len(out) > 1 and math.dist(out[0], out[-1]) < 1e-4:
        out.pop()
    return out


class Edge:
    """Vertical wall plane over the footprint edge a -> c (counter-clockwise footprint: outside on
    the right). Wall coordinates: t (0..L along a -> c), z up, off (+ = outward)."""

    def __init__(self, a, c):
        self.a = (float(a[0]), float(a[1]))
        self.c = (float(c[0]), float(c[1]))
        dx, dy = self.c[0] - self.a[0], self.c[1] - self.a[1]
        self.L = math.hypot(dx, dy)
        self.d = (dx / self.L, dy / self.L)
        self.n = (self.d[1], -self.d[0])

    def p(self, t, z, off=0.0):
        return (self.a[0] + self.d[0] * t + self.n[0] * off,
                self.a[1] + self.d[1] * t + self.n[1] * off, z)

    def hint(self, s=1.0):
        return (s * self.n[0], s * self.n[1], 0.0)

    def quad(self, b, t0, t1, z0, z1, mat, off=0.0, uv_tile=None, max_rep=None):
        """Wall quad t0..t1 x z0..z1. max_rep (visual only): cut it into pieces that span at most
        that many texture repeats along the wall (the N64 / _common.py limit is ~12)."""
        if t1 - t0 < 1e-4 or z1 - z0 < 1e-4:
            return
        if max_rep:
            tu = uv_tile[0] if uv_tile else C.PALETTE[mat]["tile_m"]
            n = max(1, int(math.ceil((t1 - t0) / (tu * max_rep) - 1e-9)))
            if n > 1:
                for k in range(n):
                    self.quad(b, t0 + (t1 - t0) * k / n, t0 + (t1 - t0) * (k + 1) / n, z0, z1, mat, off, uv_tile)
                return
        pts = [self.p(t0, z0, off), self.p(t1, z0, off), self.p(t1, z1, off), self.p(t0, z1, off)]
        uvs = None
        if uv_tile:
            tu, tv = uv_tile
            u0, u1 = t0 / tu, t1 / tu
            v0, v1 = (z0 - Z_BASE) / tv, (z1 - Z_BASE) / tv
            du, dv = math.floor(u0), math.floor(v0)
            uvs = [(u0 - du, v0 - dv), (u1 - du, v0 - dv), (u1 - du, v1 - dv), (u0 - du, v1 - dv)]
        b.poly(pts, mat, uvs=uvs, normal_hint=self.hint())

    def bearing(self):
        return math.degrees(math.atan2(self.n[0], self.n[1])) % 360.0


class Frame:
    """Local frame of the north facade: t east along the line from OSM node 10 to node 16, v outward
    (north), z up."""

    def __init__(self, a, c):
        dx, dy = c[0] - a[0], c[1] - a[1]
        L = math.hypot(dx, dy)
        self.o = a
        self.u = (dx / L, dy / L)
        self.n = (-self.u[1], self.u[0])
        self.L = L

    def p(self, t, v, z=0.0):
        return (self.o[0] + self.u[0] * t + self.n[0] * v, self.o[1] + self.u[1] * t + self.n[1] * v, z)

    def tv(self, x, y):
        dx, dy = x - self.o[0], y - self.o[1]
        return (dx * self.u[0] + dy * self.u[1], dx * self.n[0] + dy * self.n[1])

    def t_of_x(self, x):
        """t of the point on the frame's base line (v = 0) with map x."""
        return (x - self.o[0]) / self.u[0]


def _flat(b, pts2, z, mat, up=True, uv_tile=None):
    pts3 = [(x, y, z) for x, y in pts2]
    uvs = C.project_uv(pts3, uv_tile, normal=(0, 0, 1)) if uv_tile else None
    b.poly(pts3, mat, uvs=uvs, normal_hint=(0, 0, 1 if up else -1))


def _box(b, x0, x1, y0, y1, z0, z1, mat, faces="tnsew", mats=None, uv_tiles=None):
    """Axis-aligned box in map metres; `faces` picks t(op) b(ottom) n s e w."""
    mats = mats or {}
    uv_tiles = uv_tiles or {}
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    q = {
        "t": ([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], (0, 0, 1)),
        "b": ([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)], (0, 0, -1)),
        "s": ([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], (0, -1, 0)),
        "n": ([(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], (0, 1, 0)),
        "e": ([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], (1, 0, 0)),
        "w": ([(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)], (-1, 0, 0)),
    }
    for f in faces:
        pts, h = q[f]
        m = mats.get(f, mat)
        tile = uv_tiles.get(f)
        if isinstance(tile, tuple):
            uvs = _wall_uvs(pts, h, tile)          # (m per repeat along the face, m per repeat up)
        else:
            uvs = C.project_uv(pts, tile, normal=h) if tile else None
        b.poly(pts, m, uvs=uvs, normal_hint=h)


def _ibox_walls(b, x0, x1, y0, y1, z0, z1, mat, sides="nsew", uv_tile=None):
    """Inward-facing walls of an axis-aligned room (normals point into the room)."""
    walls = {
        "s": ([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], (0, 1, 0)),
        "n": ([(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], (0, -1, 0)),
        "w": ([(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)], (1, 0, 0)),
        "e": ([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], (-1, 0, 0)),
    }
    for s in sides:
        pts, h = walls[s]
        uvs = _wall_uvs(pts, h, uv_tile) if uv_tile else None
        b.poly(pts, mat, uvs=uvs, normal_hint=h)


def _wall_uvs(pts, normal, tile):
    """UVs for a vertical face: u along the face (tile[0] m per repeat), v = z (tile[1] m)."""
    L = math.hypot(normal[0], normal[1]) or 1.0
    hx, hy = -normal[1] / L, normal[0] / L
    tu, tv = tile
    uvs = [((p[0] * hx + p[1] * hy) / tu, (p[2] - Z_BASE) / tv) for p in pts]
    du = math.floor(min(u for u, _ in uvs))
    dv = math.floor(min(v for _, v in uvs))
    return [(u - du, v - dv) for u, v in uvs]


def _tri_normal(a, b, c):
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    n = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
    L = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2) or 1.0
    return (n[0] / L, n[1] / L, n[2] / L)


# =================================================================== layout (pure Python)
OUTLINE = C.ccw(_merge(FP_OSM, MERGE_TOL))           # 17 corners, counter-clockwise
_P = {i: FP_OSM[i] for i in range(len(FP_OSM))}
NF = Frame(_P[10], _P[16])                           # north facade frame


def _side_of(E):
    b = E.bearing()
    if b < 45 or b >= 315:
        return "N"
    if b < 135:
        return "E"
    if b < 225:
        return "S"
    return "W"


def _edges():
    """Footprint walls (counter-clockwise) with side, skin columns and ground-floor treatment."""
    out = []
    n = len(OUTLINE)
    for i in range(n):
        a, c = OUTLINE[i], OUTLINE[(i + 1) % n]
        E = Edge(a, c)
        side = _side_of(E)
        mid = ((a[0] + c[0]) / 2, (a[1] + c[1]) / 2)
        recess_side = side in ("E", "W") and mid[1] > -515.0 and -428.0 < mid[0] < -404.0
        east_tower = -381.5 < max(a[0], c[0]) and -523.0 < mid[1] < -513.5   # OSM nodes 17-22 bump
        E.side = "N" if recess_side else side
        E.kind = "flat" if (recess_side or E.L < 4.0) else ("glass" if east_tower else "skin")
        width = {"N": COL_N, "E": COL_E}.get(E.side, COL_S)
        E.ncols = max(1, int(round(E.L / width)))
        E.rows = ROWS_FINE if E.side in ("N", "E") else ROWS_COARSE
        E.north_main = side == "N" and abs(a[0] - _P[12][0]) < 0.1 and abs(c[0] - _P[10][0]) < 0.1
        out.append(E)
    return out


EDGES = _edges()

# north facade frame coordinates of the key nodes
T_DOOR = NF.tv(*_P[11])[0]
T_R0 = (NF.tv(*_P[12])[0] + NF.tv(*_P[13])[0]) / 2          # recess west side
T_R1 = (NF.tv(*_P[14])[0] + NF.tv(*_P[15])[0]) / 2          # recess east side
V_RECESS = (NF.tv(*_P[13])[1] + NF.tv(*_P[14])[1]) / 2      # recess back wall (about -2.94)
T_END = NF.L                                                # NE corner (node 16)
_W_STEP = (T_R1 - T_R0) / 4.0
BAND_T = [T_R0 - 3 * _W_STEP + k * _W_STEP for k in range(BAND_N)] + [T_END]     # 12 boundaries
BAND_Z = [Z_L2 + RISE * (k + 1) for k in range(BAND_N)]                      # tread tops
CAN_T0, CAN_T1 = NF.t_of_x(CAN_X0), BAND_T[0]


def _band_bottom(t):
    return BAND_BOT[0] + (BAND_BOT[1] - BAND_BOT[0]) * (t - BAND_T[0]) / (BAND_T[-1] - BAND_T[0])


def _band_back(k):
    """Back of glass box k (v): the recess back wall for the four boxes inside the OSM recess."""
    tm = (BAND_T[k] + BAND_T[k + 1]) / 2
    return V_RECESS if T_R0 < tm < T_R1 else 0.0


def _canopy_z(t):
    return CAN_Z[0] + (CAN_Z[1] - CAN_Z[0]) * (t - CAN_T0) / (CAN_T1 - CAN_T0)


def _canopy_v(t):
    return CAN_V[0] + (CAN_V[1] - CAN_V[0]) * (t - CAN_T0) / (CAN_T1 - CAN_T0)


def _facade_y(x):
    """y of the north facade (OSM edge 10 -> 12) at map x."""
    (x0, y0), (x1, y1) = _P[10], _P[12]
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def _layout():
    """Spots, climb route, markers, doors (map metres; z = metres above grade)."""
    def nfp(t, v, z):
        return _r(NF.p(t, v, z))
    ax0, ax1, ay0, ay1 = ATR
    acx = (ax0 + ax1) / 2
    pt0, pt1 = NF.t_of_x(PLANTER[0]), NF.t_of_x(PLANTER[1])
    steps = []
    for k in range(BAND_N):
        tm = (BAND_T[k] + BAND_T[k + 1]) / 2
        steps.append(nfp(tm, (_band_back(k) + BAND_D) / 2, BAND_Z[k]))
    lx0, lx1, ly0, ly1, lz = LANTERN
    px0, px1, py0, py1, pz = PENTHOUSE
    tx0, tx1, ty0, ty1, tz = TERRACE
    route = [("plaza", nfp((pt0 + pt1) / 2 - 4.0, 2.2, 0.0)),
             ("planter", nfp((pt0 + pt1) / 2, (PLANTER[2] + PLANTER[3]) / 2, PLANTER[4])),
             ("canopy_tip", nfp(CAN_T0 + 1.2, 2.2, _canopy_z(CAN_T0 + 1.2))),
             ("canopy_top", nfp(CAN_T1 - 0.8, 1.5, _canopy_z(CAN_T1 - 0.8)))]
    route += [(f"glass_box_{k + 1}", steps[k]) for k in range(BAND_N)]
    route += [("roof_ne", _r((-387.0, -514.0, Z_ROOF))), ("lantern", _r(((lx0 + lx1) / 2, (ly0 + ly1) / 2, lz))),
              ("penthouse", _r(((px0 + px1) / 2, (py0 + py1) / 2, pz)))]
    spots = {
        "plaza_center": nfp(T_DOOR, 3.6, 0.0),
        "north_entrance": nfp(T_DOOR, 1.2, 0.0),
        "planter_top": route[1][1],
        "seat_wall": nfp(NF.t_of_x((SEATWALL[0] + SEATWALL[1]) / 2), (SEATWALL[2] + SEATWALL[3]) / 2, SEATWALL[4]),
        "canopy_tip": route[2][1],
        "canopy_coin": nfp(T_DOOR, 2.0, _canopy_z(T_DOOR)),
        "canopy_top": route[3][1],
        "recess_terrace": nfp((BAND_T[4] + BAND_T[5]) / 2, V_RECESS + 1.2, BAND_Z[4]),
        "recess_floor": nfp((T_R0 + T_R1) / 2, V_RECESS + 1.0, 0.0),
        "glass_box_top": steps[-1],
        "roof_ne": route[-3][1],
        "roof_center": _r((-432.0, -540.0, Z_ROOF)),
        "rooftop_terrace": _r(((tx0 + tx1) / 2, (ty0 + ty1) / 2, tz)),
        "lantern_top": route[-2][1],
        "penthouse_top": route[-1][1],
        "atrium_floor": _r((acx, (ay0 + ay1) / 2, 0.0)),
        "atrium_entry": _r((-452.33, ay1 - 1.5, 0.0)),
        "atrium_console": _r((-460.0, ay1 - 2.5, 0.0)),
        "crane_start": _r((acx, (ay0 + ay1) / 2 + 1.0, 0.0)),
        "star_ledge": _r((acx, ay0 + LEDGE_D / 2, LEDGE_Z)),
        "server_room_dock": _r(((ALCOVE[0] + ax0) / 2, (ALCOVE[1] + ALCOVE[2]) / 2, 0.0)),
        "south_entrance": _r((-452.86, -551.5, 0.0)),
        "east_entrance": _r((-383.3, -535.0, 0.0)),
        "loading_dock": _r((-483.6, -530.05, 0.0)),
    }
    for k, p in enumerate(steps):
        spots[f"glass_box_{k + 1}"] = p
    doors = [
        {"name": "DOOR_malachowsky_hall_1", "pos_m": _r((_P[11][0], _P[11][1], 0.0)),
         "facing_deg": round(Edge(_P[11], _P[10]).bearing(), 1), "width_m": DOOR_W, "height_m": DOOR_H,
         "note": "main north entrance (OSM 11254215508) under the folded canopy; an open 6 m passage into the "
                 "atrium (Remote Robotics Lab); not a stage door"},
        {"name": "DOOR_malachowsky_hall_2", "pos_m": _r((_P[5][0], _P[5][1], 0.0)), "facing_deg": 180.0,
         "width_m": 3.0, "height_m": 3.0, "note": "south entrance, level 0 (OSM 11254215507); visual glass doors"},
        {"name": "DOOR_malachowsky_hall_3", "pos_m": _r((_P[4][0], _P[4][1], 0.0)), "facing_deg": 180.0,
         "width_m": 2.4, "height_m": 3.0, "note": "south-east entrance (OSM 13505680290); visual glass doors"},
        {"name": "DOOR_malachowsky_hall_4", "pos_m": _r((_P[23][0], _P[23][1], 0.0)), "facing_deg": 90.0,
         "width_m": 3.0, "height_m": 3.0, "note": "east (secondary) entrance, level 1 (OSM 11254215506); visual"},
        {"name": "DOOR_malachowsky_hall_5", "pos_m": _r((_P[7][0], _P[7][1], 0.0)), "facing_deg": 270.0,
         "width_m": 4.0, "height_m": 4.2, "note": "west loading dock overhead door (OSM 11254215505); visual"},
        {"name": "DOOR_malachowsky_hall_6", "pos_m": _r((_P[1][0], _P[1][1], 0.0)), "facing_deg": 180.0,
         "width_m": 2.0, "height_m": 2.8, "note": "service door (OSM 11254215510); visual"},
    ]
    markers = {
        "atrium_box_m": {"x": [ax0, ax1], "y": [ay0, ay1], "z": [0.0, ATR_CEIL],
                         "note": "clear interior of the vertical commons; the generator ground (z = 0) is its floor"},
        "star_ledge_m": {"x": [ax0, ax1], "y": [ay0, ay0 + LEDGE_D], "z": LEDGE_Z,
                         "note": "L7 ledge along the atrium's south wall, underside at 27.4 m"},
        "atrium_passage_m": {"x": [-452.33 - DOOR_W / 2, -452.33 + DOOR_W / 2], "y": [ay1, round(_facade_y(-452.33), 2)],
                             "z": [0.0, DOOR_H]},
        "server_room_m": {"x": [ALCOVE[0], ax0], "y": [ALCOVE[1], ALCOVE[2]], "z": [0.0, ALCOVE[3]]},
        "glass_stair_m": [{"box": k + 1, "t0_m": _r(NF.p(BAND_T[k], 0.0, BAND_Z[k])),
                           "t1_m": _r(NF.p(BAND_T[k + 1], 0.0, BAND_Z[k])), "depth_m": round(BAND_D - _band_back(k), 2),
                           "top_z_m": round(BAND_Z[k], 2)} for k in range(BAND_N)],
        "levels_m": {"ground_floor_top": Z_L2, "floors": list(ROWS_FINE[:-1]), "roof": Z_ROOF,
                     "lantern": LANTERN[4], "penthouse": PENTHOUSE[4], "rooftop_terrace": TERRACE[4],
                     "canopy": list(CAN_Z), "planter": PLANTER[4], "seat_wall": SEATWALL[4]},
        "note": "map metres (x east, y north, z above grade); the building is flat-sited (real site slopes south)",
    }
    top = {"z_m": PENTHOUSE[4], "center_m": _r(((px0 + px1) / 2, (py0 + py1) / 2)),
           "half_m": _r(((px1 - px0) / 2, (py1 - py0) / 2)),
           "note": "mechanical penthouse roof, the highest point of the stage; reached from the 35.33 m skylight "
                   "lantern (3 m gap, 2.33 m rise), which is reached from the 33 m roof"}
    return {"spots": spots, "route": route, "doors": doors, "markers": markers, "top": top}


# =================================================================== geometry
def _skin(vis, E, seed, win_frac):
    """Folded aluminium skin over wall E above the ground floor (visual)."""
    rows = E.rows
    nr = len(rows) - 1
    nc = E.ncols
    ts = [E.L * i / nc for i in range(nc + 1)]

    def dep(i, j):
        if i in (0, nc) or j in (0, nr):
            return 0.0
        return FOLD_DEPTHS[_hash(seed, i, j) % 3]
    P = {(i, j): E.p(ts[i], rows[j], -dep(i, j)) for i in range(nc + 1) for j in range(nr + 1)}
    for j in range(nr):
        for i in range(nc):
            a, b, c, d = P[(i, j)], P[(i + 1, j)], P[(i + 1, j + 1)], P[(i, j + 1)]
            tris = [(a, b, c), (a, c, d)] if _hash(seed, i, j, 1) & 1 else [(a, b, d), (b, c, d)]
            for k, tri in enumerate(tris):
                mat = "white_trim" if _hash(seed, i, j, 2 + k) % 100 < 28 else "metal_gray"
                vis.poly(list(tri), mat, normal_hint=E.hint())
            if (_hash(seed, i, j, 7) % 1000) / 1000.0 < win_frac:
                tri = tris[_hash(seed, i, j, 8) & 1]
                nrm = _tri_normal(*tri)
                if nrm[0] * E.n[0] + nrm[1] * E.n[1] < 0:
                    nrm = (-nrm[0], -nrm[1], -nrm[2])
                cx = sum(p[0] for p in tri) / 3
                cy = sum(p[1] for p in tri) / 3
                cz = sum(p[2] for p in tri) / 3
                s = 0.56
                w = [(cx + (p[0] - cx) * s + nrm[0] * 0.05, cy + (p[1] - cy) * s + nrm[1] * 0.05,
                      cz + (p[2] - cz) * s + nrm[2] * 0.05) for p in tri]
                vis.poly(w, "window_dark", uvs=C.project_uv(w, 1.6, normal=nrm), normal_hint=nrm)


def _ground_floor(vis, E):
    """Ground-floor wall (visual), 0..5 m; the main north edge leaves the door opening."""
    mat, tile = {"N": ("window_glass", (3.0, 5.2)), "E": ("window_glass", (3.0, 5.2)),
                 "S": ("window_dark", (2.6, 2.6)), "W": ("metal_gray", (2.0, 2.0))}[E.side]
    if E.kind == "glass":
        return
    if E.north_main:
        # this edge runs west (node 12 -> node 10): t of the door centre (node 11) from node 12
        tdc = math.dist(E.a, _P[11])
        d0, d1 = tdc - DOOR_W / 2, tdc + DOOR_W / 2
        E.quad(vis, 0.0, d0, Z_BASE, Z_L2, mat, uv_tile=tile, max_rep=11)
        E.quad(vis, d1, E.L, Z_BASE, Z_L2, mat, uv_tile=tile, max_rep=11)
        E.quad(vis, d0, d1, DOOR_H, Z_L2, "white_trim")
        # door frame: thin dark jambs and a header just proud of the opening
        for t0, t1 in ((d0 - 0.25, d0), (d1, d1 + 0.25)):
            E.quad(vis, t0, t1, Z_BASE, DOOR_H + 0.25, "dark_trim", off=0.04)
        E.quad(vis, d0 - 0.25, d1 + 0.25, DOOR_H, DOOR_H + 0.25, "dark_trim", off=0.04)
        return
    E.quad(vis, 0.0, E.L, Z_BASE, Z_L2, mat, uv_tile=tile, max_rep=11)


def _shell(vis, col):
    """Outer walls (collision + visual skin), the roof, the coping."""
    for idx, E in enumerate(EDGES):
        # ---- collision: full-height outer plane (the north main edge leaves the door opening)
        if E.north_main:
            tdc = math.dist(E.a, _P[11])
            d0, d1 = tdc - DOOR_W / 2, tdc + DOOR_W / 2
            E.quad(col, 0.0, d0, Z_BASE, Z_ROOF, "metal_gray")
            E.quad(col, d1, E.L, Z_BASE, Z_ROOF, "metal_gray")
            E.quad(col, d0, d1, DOOR_H, Z_ROOF, "metal_gray")
        else:
            E.quad(col, 0.0, E.L, Z_BASE, Z_ROOF, "window_glass" if E.kind == "glass" else "metal_gray")
        # ---- visual
        if E.kind == "glass":
            # east stair / forum tower: clear curtain wall, one texture repeat per floor
            E.quad(vis, 0.0, E.L, Z_BASE, Z_ROOF, "window_glass", uv_tile=(3.0, 4.6))
            continue
        _ground_floor(vis, E)
        if E.kind == "flat":
            E.quad(vis, 0.0, E.L, Z_L2, Z_ROOF, "metal_gray", uv_tile=(2.0, 3.0))
        else:
            frac = 0.65 if E.side in ("N", "E") else 0.4
            _skin(vis, E, 101 + 17 * idx, frac)
        if E.side in ("N", "E"):
            E.quad(vis, 0.0, E.L, Z_ROOF - 0.45, Z_ROOF, "white_trim", off=0.03, uv_tile=(4.0, 2.0), max_rep=11)
        # slab line between the glass ground floor and the folded skin
        E.quad(vis, 0.0, E.L, Z_L2 - 0.35, Z_L2, "white_trim", off=0.03, uv_tile=(4.0, 2.0), max_rep=11)
    # ---- roof: one collision polygon, three visual slabs (texture repeats)
    col.poly([(x, y, Z_ROOF) for x, y in OUTLINE], "concrete", normal_hint=(0, 0, 1))
    xs = [p[0] for p in OUTLINE]
    cuts = [min(xs) - 1, -451.5, -417.3, max(xs) + 1]
    for x0, x1 in zip(cuts, cuts[1:]):
        piece = _clip_x(OUTLINE, x0, x1)
        if len(piece) >= 3:
            _flat(vis, C.ccw(piece), Z_ROOF, "concrete", uv_tile=4.0)


def _door_panels(vis):
    """Visual entrance panels on the south, east and west walls."""
    for E in EDGES:
        for node, w, h, mat in ((5, 3.0, 3.0, "window_glass"), (4, 2.4, 3.0, "window_glass"),
                                (23, 3.0, 3.0, "window_glass"), (7, 4.0, 4.2, "metal_gray"),
                                (1, 2.0, 2.8, "dark_trim")):
            p = _P[node]
            # the door node lies on this edge?
            t = (p[0] - E.a[0]) * E.d[0] + (p[1] - E.a[1]) * E.d[1]
            off = (p[0] - E.a[0]) * E.n[0] + (p[1] - E.a[1]) * E.n[1]
            if -0.01 <= t <= E.L + 0.01 and abs(off) < 0.08:
                t0, t1 = max(0.3, t - w / 2), min(E.L - 0.3, t + w / 2)
                E.quad(vis, t0 - 0.3, t1 + 0.3, Z_BASE, h + 0.3, "dark_trim", off=0.05)
                E.quad(vis, t0, t1, Z_BASE, h, mat, off=0.08, uv_tile=(w / 2 if mat != "metal_gray" else 1.0,
                                                                          h + 0.2 if mat != "metal_gray" else 0.5))


def _band(vis, col):
    """The stepped glass band: eleven cantilevered glass boxes on the north facade."""
    def P(t, v, z):
        return NF.p(t, v, z)
    hint_n = (NF.n[0], NF.n[1], 0.0)
    hint_e = (NF.u[0], NF.u[1], 0.0)
    hint_w = (-NF.u[0], -NF.u[1], 0.0)
    for k in range(BAND_N):
        t0, t1, z = BAND_T[k], BAND_T[k + 1], BAND_Z[k]
        vb = _band_back(k)
        b0, b1 = _band_bottom(t0), _band_bottom(t1)
        # tread (terrace deck)
        col.poly([P(t0, vb - TREAD_EMBED, z), P(t1, vb - TREAD_EMBED, z), P(t1, BAND_D, z), P(t0, BAND_D, z)],
                 "concrete", normal_hint=(0, 0, 1))
        vis.poly([P(t0, vb - VIS_EMBED, z), P(t1, vb - VIS_EMBED, z), P(t1, BAND_D, z), P(t0, BAND_D, z)],
                 "concrete", normal_hint=(0, 0, 1))
        # front glass (north face): from the sloped soffit up to the tread
        front = [P(t0, BAND_D, b0), P(t1, BAND_D, b1), P(t1, BAND_D, z), P(t0, BAND_D, z)]
        col.poly(front, "window_glass", normal_hint=hint_n)
        vis.poly(front, "window_glass", normal_hint=hint_n)
        vis.poly([P(t0, BAND_D + 0.03, z - 0.45), P(t1, BAND_D + 0.03, z - 0.45), P(t1, BAND_D + 0.03, z),
                  P(t0, BAND_D + 0.03, z)], "white_trim", normal_hint=hint_n)
        # riser (west face of box k above box k-1, or the band's west end)
        zlo = BAND_Z[k - 1] if k > 0 else b0
        vr = max(vb, _band_back(k - 1)) if k > 0 else vb
        col.poly([P(t0, vr - TREAD_EMBED, zlo), P(t0, BAND_D, zlo), P(t0, BAND_D, z), P(t0, vr - TREAD_EMBED, z)],
                 "window_glass", normal_hint=hint_w)
        vis.poly([P(t0, vr - VIS_EMBED, zlo), P(t0, BAND_D, zlo), P(t0, BAND_D, z), P(t0, vr - VIS_EMBED, z)],
                 "window_glass", normal_hint=hint_w)
        # white slab edge on the riser top
        vis.poly([P(t0 - 0.03, vr - VIS_EMBED, z - 0.45), P(t0 - 0.03, BAND_D, z - 0.45), P(t0 - 0.03, BAND_D, z),
                  P(t0 - 0.03, vr - VIS_EMBED, z)], "white_trim", normal_hint=hint_w)
    # east end (flush with the NE corner)
    tE, bE, zE = BAND_T[-1], _band_bottom(BAND_T[-1]), BAND_Z[-1]
    for b, emb in ((col, TREAD_EMBED), (vis, VIS_EMBED)):
        b.poly([P(tE, -emb, bE), P(tE, -emb, zE), P(tE, BAND_D, zE), P(tE, BAND_D, bE)], "window_glass",
               normal_hint=hint_e)
    # soffit: one sloped plane, three pieces (back edge follows the recess)
    pieces = [(BAND_T[0], T_R0, 0.0), (T_R0, T_R1, V_RECESS), (T_R1, BAND_T[-1], 0.0)]
    for t0, t1, vb in pieces:
        b0, b1 = _band_bottom(t0), _band_bottom(t1)
        for b, emb in ((col, TREAD_EMBED), (vis, VIS_EMBED)):
            b.poly([P(t0, vb - emb, b0), P(t0, BAND_D, b0), P(t1, BAND_D, b1), P(t1, vb - emb, b1)],
                   "white_trim", normal_hint=(0, 0, -1))
    # vertical white mullion fins on the front at every box joint (visual)
    for k in range(1, BAND_N):
        t = BAND_T[k]
        vis.poly([P(t - 0.18, BAND_D + 0.05, _band_bottom(t)), P(t + 0.18, BAND_D + 0.05, _band_bottom(t)),
                  P(t + 0.18, BAND_D + 0.05, BAND_Z[k - 1]), P(t - 0.18, BAND_D + 0.05, BAND_Z[k - 1])],
                 "white_trim", normal_hint=hint_n)


def _canopy(vis, col):
    """Folded entrance canopy over the north door (cantilevered from the facade)."""
    t0, t1 = CAN_T0, CAN_T1
    z0, z1 = _canopy_z(t0), _canopy_z(t1)
    v0, v1 = _canopy_v(t0), _canopy_v(t1)
    vb = -TREAD_EMBED
    P = NF.p
    top = [P(t0, vb, z0), P(t1, vb, z1), P(t1, v1, z1), P(t0, v0, z0)]
    bot = [P(t0, vb, z0 - CAN_T), P(t0, v0, z0 - CAN_T), P(t1, v1, z1 - CAN_T), P(t1, vb, z1 - CAN_T)]
    fdx, fdy = P(t1, v1)[0] - P(t0, v0)[0], P(t1, v1)[1] - P(t0, v0)[1]
    front_hint = (fdy, -fdx, 0.0) if (fdy * NF.n[0] - fdx * NF.n[1]) > 0 else (-fdy, fdx, 0.0)
    front = [P(t0, v0, z0 - CAN_T), P(t1, v1, z1 - CAN_T), P(t1, v1, z1), P(t0, v0, z0)]
    west = [P(t0, vb, z0 - CAN_T), P(t0, v0, z0 - CAN_T), P(t0, v0, z0), P(t0, vb, z0)]
    hint_w = (-NF.u[0], -NF.u[1], 0.0)
    col.poly(top, "concrete", normal_hint=(0, 0, 1))
    for b in (col, vis):
        b.poly(bot, "white_trim", normal_hint=(0, 0, -1), uvs=C.project_uv(bot, 4.0, normal=(0, 0, 1)) if b is vis else None)
        b.poly(front, "metal_gray", normal_hint=front_hint, uvs=_wall_uvs(front, front_hint, (4.0, 2.0)) if b is vis else None)
        b.poly(west, "metal_gray", normal_hint=hint_w)
    # visual top: facets folded along a valley crease 0.12 m BELOW the collision plane (origami look;
    # no visual surface above the floor Mario stands on, so his shadow is never hidden)
    fold = -0.12
    c0, c1 = P(t0, v0 * 0.45, z0 + fold), P(t1, v1 * 0.45, z1 + fold)
    for tri, mat in (((top[0], top[1], c1), "white_trim"), ((top[0], c1, c0), "white_trim"),
                     ((c0, c1, top[2]), "metal_gray"), ((c0, top[2], top[3]), "metal_gray")):
        vis.poly(list(tri), mat, uvs=C.project_uv(list(tri), 4.0, normal=(0, 0, 1)), normal_hint=(0, 0, 1))


def _atrium(vis, col):
    """Passage + atrium (vertical commons) + server alcove + star ledge: inward-facing interior."""
    ax0, ax1, ay0, ay1 = ATR
    dx0, dx1 = _P[11][0] - DOOR_W / 2, _P[11][0] + DOOR_W / 2
    yf0, yf1 = _facade_y(dx0), _facade_y(dx1)
    glass, core = (3.0, 4.6), (4.0, 4.6)
    for b, vis_pass in ((col, False), (vis, True)):
        mat_w = "window_glass"                     # north / south: offices and labs behind glass
        mat_c = "white_trim" if vis_pass else "metal_gray"     # east / west: solid stair + lift cores
        # north wall (faces south) with the passage opening
        for x0, x1, z0 in ((ax0, dx0, Z_BASE), (dx1, ax1, Z_BASE), (dx0, dx1, DOOR_H)):
            pts = [(x0, ay1, z0), (x1, ay1, z0), (x1, ay1, ATR_CEIL), (x0, ay1, ATR_CEIL)]
            b.poly(pts, mat_w, uvs=_wall_uvs(pts, (0, -1, 0), glass) if vis_pass else None, normal_hint=(0, -1, 0))
        # south and east walls
        _ibox_walls(b, ax0, ax1, ay0, ay1, Z_BASE, ATR_CEIL, mat_w, sides="s", uv_tile=glass if vis_pass else None)
        _ibox_walls(b, ax0, ax1, ay0, ay1, Z_BASE, ATR_CEIL, mat_c, sides="e", uv_tile=core if vis_pass else None)
        # west wall with the server-room alcove opening
        bx, by0, by1, bh = ALCOVE
        for y0, y1, z0 in ((ay0, by0, Z_BASE), (by1, ay1, Z_BASE), (by0, by1, bh)):
            pts = [(ax0, y0, z0), (ax0, y1, z0), (ax0, y1, ATR_CEIL), (ax0, y0, ATR_CEIL)]
            b.poly(pts, mat_c, uvs=_wall_uvs(pts, (1, 0, 0), core) if vis_pass else None, normal_hint=(1, 0, 0))
        # ceiling (skylight)
        b.poly([(ax0, ay0, ATR_CEIL), (ax1, ay0, ATR_CEIL), (ax1, ay1, ATR_CEIL), (ax0, ay1, ATR_CEIL)],
               "window_glass", normal_hint=(0, 0, -1),
               uvs=C.project_uv([(ax0, ay0, 0), (ax1, ay0, 0), (ax1, ay1, 0), (ax0, ay1, 0)], 3.0, normal=(0, 0, 1))
               if vis_pass else None)
        # passage (door -> atrium)
        b.poly([(dx0, ay1, Z_BASE), (dx0, yf0, Z_BASE), (dx0, yf0, DOOR_H), (dx0, ay1, DOOR_H)],
               "concrete", normal_hint=(1, 0, 0))
        b.poly([(dx1, yf1, Z_BASE), (dx1, ay1, Z_BASE), (dx1, ay1, DOOR_H), (dx1, yf1, DOOR_H)],
               "concrete", normal_hint=(-1, 0, 0))
        b.poly([(dx0, ay1, DOOR_H), (dx1, ay1, DOOR_H), (dx1, yf1, DOOR_H), (dx0, yf0, DOOR_H)],
               "white_trim", normal_hint=(0, 0, -1))
        # server alcove
        b.poly([(bx, by0, Z_BASE), (bx, by1, Z_BASE), (bx, by1, bh), (bx, by0, bh)],
               "window_dark" if vis_pass else "metal_gray", normal_hint=(1, 0, 0),
               uvs=_wall_uvs([(bx, by0, Z_BASE), (bx, by1, Z_BASE), (bx, by1, bh), (bx, by0, bh)], (1, 0, 0),
                             (1.5, 2.1)) if vis_pass else None)
        b.poly([(bx, by0, Z_BASE), (ax0, by0, Z_BASE), (ax0, by0, bh), (bx, by0, bh)], "metal_gray",
               normal_hint=(0, 1, 0))
        b.poly([(ax0, by1, Z_BASE), (bx, by1, Z_BASE), (bx, by1, bh), (ax0, by1, bh)], "metal_gray",
               normal_hint=(0, -1, 0))
        b.poly([(bx, by0, bh), (ax0, by0, bh), (ax0, by1, bh), (bx, by1, bh)], "dark_trim", normal_hint=(0, 0, -1))
        # L7 star ledge along the south wall
        ly1 = ay0 + LEDGE_D
        lt = [(ax0, ay0 - TREAD_EMBED, LEDGE_Z), (ax1, ay0 - TREAD_EMBED, LEDGE_Z), (ax1, ly1, LEDGE_Z), (ax0, ly1, LEDGE_Z)]
        lf = [(ax0, ly1, LEDGE_Z - LEDGE_T), (ax1, ly1, LEDGE_Z - LEDGE_T), (ax1, ly1, LEDGE_Z), (ax0, ly1, LEDGE_Z)]
        lb = [(ax0, ay0 - TREAD_EMBED, LEDGE_Z - LEDGE_T), (ax0, ly1, LEDGE_Z - LEDGE_T),
              (ax1, ly1, LEDGE_Z - LEDGE_T), (ax1, ay0 - TREAD_EMBED, LEDGE_Z - LEDGE_T)]
        b.poly(lt, "concrete", normal_hint=(0, 0, 1), uvs=C.project_uv(lt, 3.0, normal=(0, 0, 1)) if vis_pass else None)
        b.poly(lf, "white_trim", normal_hint=(0, 1, 0), uvs=_wall_uvs(lf, (0, 1, 0), (4.0, 2.0)) if vis_pass else None)
        b.poly(lb, "white_trim", normal_hint=(0, 0, -1), uvs=C.project_uv(lb, 4.0, normal=(0, 0, 1)) if vis_pass else None)
    # visual: white slab bands at every floor on the four atrium walls, server racks
    for z in SLAB_BANDS:
        z0, z1 = z - 0.5, z
        for pts, h in (([(ax0, ay1 - 0.03, z0), (ax1, ay1 - 0.03, z0), (ax1, ay1 - 0.03, z1), (ax0, ay1 - 0.03, z1)], (0, -1, 0)),
                       ([(ax0, ay0 + 0.03, z0), (ax1, ay0 + 0.03, z0), (ax1, ay0 + 0.03, z1), (ax0, ay0 + 0.03, z1)], (0, 1, 0)),
                       ([(ax0 + 0.03, ay0, z0), (ax0 + 0.03, ay1, z0), (ax0 + 0.03, ay1, z1), (ax0 + 0.03, ay0, z1)], (1, 0, 0)),
                       ([(ax1 - 0.03, ay0, z0), (ax1 - 0.03, ay1, z0), (ax1 - 0.03, ay1, z1), (ax1 - 0.03, ay0, z1)], (-1, 0, 0))):
            vis.poly(pts, "white_trim" if h[0] == 0 else "metal_gray", normal_hint=h, uvs=_wall_uvs(pts, h, (4.0, 2.0)))
    bx, by0, by1, bh = ALCOVE
    for k in range(3):
        y0 = by0 + 0.6 + k * 2.75
        vis.poly([(bx + 0.05, y0, 0.0), (bx + 0.05, y0 + 2.2, 0.0), (bx + 0.05, y0 + 2.2, 2.6), (bx + 0.05, y0, 2.6)],
                 "dark_trim", normal_hint=(1, 0, 0))
        vis.poly([(bx + 0.08, y0 + 0.25, 0.3), (bx + 0.08, y0 + 1.95, 0.3), (bx + 0.08, y0 + 1.95, 2.4),
                  (bx + 0.08, y0 + 0.25, 2.4)], "window_dark",
                 uvs=[(0, 0), (1, 0), (1, 1.5), (0, 1.5)], normal_hint=(1, 0, 0))


def _roof_features(vis, col):
    lx0, lx1, ly0, ly1, lz = LANTERN
    px0, px1, py0, py1, pz = PENTHOUSE
    tx0, tx1, ty0, ty1, tz = TERRACE
    # skylight lantern: glass top, glass clerestory sides on a white curb
    _box(col, lx0, lx1, ly0, ly1, Z_ROOF - 0.3, lz, "window_glass", faces="tnsew")
    _box(vis, lx0, lx1, ly0, ly1, Z_ROOF - 0.3, lz, "window_glass", faces="tnsew", uv_tiles={"t": 3.0})
    for f in "nsew":
        _box(vis, lx0 - 0.05, lx1 + 0.05, ly0 - 0.05, ly1 + 0.05, Z_ROOF - 0.3, Z_ROOF + 0.5, "white_trim", faces=f,
             uv_tiles={f: (4.0, 2.0)})
    # mechanical penthouse with louvres (metal) and a dark roof
    _box(col, px0, px1, py0, py1, Z_ROOF - 0.3, pz, "metal_gray", faces="tnsew")
    _box(vis, px0, px1, py0, py1, Z_ROOF - 0.3, pz, "metal_gray", faces="nsew",
         uv_tiles={f: (4.0, 1.2) for f in "nsew"})
    _box(vis, px0, px1, py0, py1, Z_ROOF - 0.3, pz, "roof_dark", faces="t", uv_tiles={"t": 3.0})
    for f in "nsew":
        _box(vis, px0 - 0.06, px1 + 0.06, py0 - 0.06, py1 + 0.06, pz - 0.5, pz, "white_trim", faces=f,
             uv_tiles={f: (4.0, 2.0)})
    # rooftop terrace deck (raised 0.25 m: Mario steps up, so only its top collides)
    _flat(col, [(tx0, ty0), (tx1, ty0), (tx1, ty1), (tx0, ty1)], tz, "concrete")
    _box(vis, tx0, tx1, ty0, ty1, Z_ROOF - 0.1, tz, "concrete", faces="nsew")
    _flat(vis, [(tx0, ty0), (tx1, ty0), (tx1, ty1), (tx0, ty1)], tz, "path", uv_tile=3.0)


def _plaza(vis, col, dec):
    """Raised planter, seat wall, paving (decal) of the entrance forecourt."""
    t0, t1 = NF.t_of_x(PLANTER[0]), NF.t_of_x(PLANTER[1])
    v0, v1, ztop = PLANTER[2], PLANTER[3], PLANTER[4]
    P = NF.p
    corners = [P(t0, v0), P(t1, v0), P(t1, v1), P(t0, v1)]
    hints = [(-NF.n[0], -NF.n[1], 0), (NF.u[0], NF.u[1], 0), (NF.n[0], NF.n[1], 0), (-NF.u[0], -NF.u[1], 0)]
    for i in range(4):
        a, c = corners[i], corners[(i + 1) % 4]
        q = [(a[0], a[1], Z_BASE), (c[0], c[1], Z_BASE), (c[0], c[1], ztop), (a[0], a[1], ztop)]
        col.poly(q, "concrete", normal_hint=hints[i])
        vis.poly(q, "concrete", normal_hint=hints[i])
    # planted top (visual exactly on the collision plane: nothing above a floor hides Mario's shadow)
    col.poly([(x, y, ztop) for x, y, _ in corners], "grass", normal_hint=(0, 0, 1))
    vis.poly([(x, y, ztop) for x, y, _ in corners], "grass", normal_hint=(0, 0, 1))
    # seat wall (0.45 m: Mario walks up it, so only its top collides)
    s0, s1 = NF.t_of_x(SEATWALL[0]), NF.t_of_x(SEATWALL[1])
    w0, w1, zs = SEATWALL[2], SEATWALL[3], SEATWALL[4]
    sc = [P(s0, w0), P(s1, w0), P(s1, w1), P(s0, w1)]
    col.poly([(x, y, zs) for x, y, _ in sc], "concrete", normal_hint=(0, 0, 1))
    vis.poly([(x, y, zs) for x, y, _ in sc], "white_trim", normal_hint=(0, 0, 1))
    for i in range(4):
        a, c = sc[i], sc[(i + 1) % 4]
        vis.poly([(a[0], a[1], Z_BASE), (c[0], c[1], Z_BASE), (c[0], c[1], zs), (a[0], a[1], zs)], "concrete",
                 normal_hint=hints[i])
    # ---- paving (decal part): forecourt + the strip along the facade, cut into ~32 m pieces
    south = [(x, _facade_y(x)) for x, _ in (PLAZA_NORTH[0],)]
    poly = list(PLAZA_NORTH) + [(_P[16][0], _P[16][1]), (_P[15][0], _P[15][1]), (_P[14][0], _P[14][1]),
                                (_P[13][0], _P[13][1]), (_P[12][0], _P[12][1])] + south
    poly = C.ccw(poly)
    for x0, x1 in ((-480.0, -447.0), (-447.0, -415.0), (-415.0, -383.0)):
        piece = _clip_x(poly, x0, x1)
        if len(piece) >= 3:
            _flat(dec, C.ccw(piece), 0.0, "path", uv_tile=3.0)
    for a, c in PLAZA_BANDS:
        dx, dy = c[0] - a[0], c[1] - a[1]
        L = math.hypot(dx, dy)
        nx, ny = -dy / L * 0.6, dx / L * 0.6
        q = [(a[0] + nx, a[1] + ny), (c[0] + nx, c[1] + ny), (c[0] - nx, c[1] - ny), (a[0] - nx, a[1] - ny)]
        _flat(dec, C.ccw(q), 0.004, "white_trim", uv_tile=2.0)
    # atrium + passage + server alcove floor (polished concrete)
    ax0, ax1, ay0, ay1 = ATR
    dx0, dx1 = _P[11][0] - DOOR_W / 2, _P[11][0] + DOOR_W / 2
    _flat(dec, [(ax0, ay0), (ax1, ay0), (ax1, ay1), (ax0, ay1)], 0.0, "concrete", uv_tile=3.0)
    _flat(dec, [(dx0, ay1), (dx1, ay1), (dx1, _facade_y(dx1)), (dx0, _facade_y(dx0))], 0.0, "concrete", uv_tile=3.0)
    bx, by0, by1, _bh = ALCOVE
    _flat(dec, [(bx, by0), (ax0, by0), (ax0, by1), (bx, by1)], 0.0, "dark_trim", uv_tile=2.0)


# =================================================================== contract
_L = _layout()

LANDMARKS = [
    {
        "slug": SLUG,
        "name": "Malachowsky Hall for Data Science & Information Technology",
        "osm_ids": [MAL_ID],
        "stages": list(STAGES),
        "center_m": _r(C.centroid(C.ccw(FP_OSM))),
        "height_m": Z_ROOF,
        "doors": _L["doors"],
        "spots": _L["spots"],
        "climb_route_m": [p for _, p in _L["route"]],
        "top_platform": _L["top"],
        "markers": _L["markers"],
    },
]


def _check_footprint(ctx):
    try:
        fp = C.building(ctx, MAL_ID)["pts"]
    except KeyError:
        print(f"reitz_malachowsky: WARNING {MAL_ID} not in campus.json")
        return
    if len(fp) != len(FP_OSM) or any(math.dist(p, q) > 0.05 for p, q in zip(fp, FP_OSM)):
        print("reitz_malachowsky: WARNING Malachowsky Hall footprint changed in campus.json; the model uses "
              "the copy in FP_OSM")


def build(ctx):
    """-> [{"name", "mesh", "material_slots", "collision", "visual", "landmark"("decal")},...] (map metres)."""
    key = ctx.get("stage_key")
    if key is not None and key not in STAGES:
        return []
    _check_footprint(ctx)
    vis, col, dec = C.Builder(), C.Builder(), C.Builder()
    _shell(vis, col)
    _door_panels(vis)
    _band(vis, col)
    _canopy(vis, col)
    _atrium(vis, col)
    _roof_features(vis, col)
    _plaza(vis, col, dec)
    parts = []
    for name, b, collision, visual, extra in ((f"{SLUG} visual", vis, False, True, {}),
                                              (f"{SLUG} paving", dec, False, True, {"decal": True}),
                                              (f"{SLUG} collision", col, True, False, {})):
        me, slots = b.build(name)
        p = C.part(name, me, slots, collision=collision, visual=visual)
        p["landmark"] = SLUG
        p.update(extra)
        parts.append(p)
    print(f"reitz_malachowsky: {SLUG}: visual {vis.tri_count()} + paving {dec.tri_count()} tris, "
          f"collision {col.tri_count()} tris (budget 1200 / 300)")
    return parts
