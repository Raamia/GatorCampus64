"""HUB stage landmarks: Library West, Smathers Library (Library East), the Library Colonnade and
the Plaza of the Americas hardscape.

Landmark module (contract: tools/campus/landmarks/_common.py). Geometry is in MAP METRES, z up
(x = east, y = north, origin = Century Tower). Every footprint vertex below is copied from
data/uf/campus.json (verified at build time, see _verify_footprints) so each model sits exactly on
the OSM footprint it replaces.

  entry replaces (campus.json) budget col / vis built col / vis
  library_west r12122775/196848215 (+ /891179070, 250 / 900 167 / 945
                         the 0-area entrance sliver)
  library_colonnade w859953340 (building=roof, ref 1103) (generic canopy) 74 / 278
  smathers_library w154223625 300 / 1000 277 / 1127
  plaza_of_the_americas (area w264182367; no building) 120 / 900 86 / 630
  Library West + colonnade collision = 241 <= 250; plaza + colonnade visual = 908 ~ 900.
  Group total 604 collision tris (budget 670), 2980 visual (budget 2800, +6%: Smathers' gothic
  openings). build() prints the live numbers.

LIBRARY WEST (1967, "mid-century"; 2006 renovation + north addition by Long & Associates)
  - Original 6-floor block = the south part of the OSM outline (80 x 33.5 m, entrance recessed
    4.3 m in the middle of the plaza face). Roof 25.3 m, parapet 26.0 m (stages.json: 26 m).
    Plaza face: "opened up dramatically on the lower two floors" (R-BARC) -> two glazed floors
    between brick piers, the main entrance is a "two-story transparent glass wall" facing the
    Plaza (R-BARC) with the revolving door at OSM entrance node 4741830154 (38.91, 258.53).
    Floors 3-6: brick with continuous window bands under projecting concrete sun-shade eyebrows.
  - 2006 addition = the north part of the outline ("book box", 3 storeys, transparent north
    facade on University Ave): roof 15.0 m, flat, metal fascia; curved glass front (4 chords)
    between two brick stair towers; north doors at OSM entrance nodes (23.27, 316.3) and
    (54.46, 316.29) in the notches beside the curve; brick sides with a 2-storey window band.
  - Rooftop: mechanical penthouse (4 m) as a perch for the rooftop red coins.
LIBRARY COLONNADE (OSM w859953340, covered walk from 1967 between Library West and Smathers)
  - 2024-25 rebuild: the eastern section in front of Smathers was removed, the rest rebuilt
    "taller and narrower" with solar panels, brick benches, a Garden Terrace between colonnade and
    library (replacing the sabal palms) and another terrace along the Plaza edge; the bronze
    alligator "Focused Attention" (9 ft) sits in front of it on a limestone base facing the Plaza.
  - Modelled: slab 4.0-4.6 m (jump-through, no ceiling) over the 6 m walk x 19.1-85.1, the
    entrance canopy to the LW door and the east walk along LW; brick piers with collision at the
    ends / door, slender steel posts visual-only (stages.json canopy rule); 6 solar-panel rows.
SMATHERS LIBRARY (William A. Edwards, opened 1926; Guy Fulton addition after WWII; NRHP 1979)
  - Collegiate Gothic, red brick + cast-stone trim, red tile roofs (OSM roof:colour #B55549).
    West range on the Plaza (paired lancets of the reading room over ground-floor windows,
    buttresses), north range (gable ends with big lancets), entrance tower (roof 18.2, parapet
    18.9, two pinnacles) with the main door at OSM entrance node 4741830122 (126.95, 244.81)
    facing the Plaza, flat-roofed east stacks block (the post-war addition), stair turret on the
    east side, two-storey bay on the south gable end, side door at OSM node 10083724148.
  - Eaves 14.0 m, ridges 18.0 m (stages.json: 18 m), roof pitch 31-34 deg (< 38 deg: walkable);
    the west range's roof runs into the north range's with proper valleys.
PLAZA OF THE AMERICAS (Olmsted Jr. / Phillips 1925 layout; 2017 + 2025 renovations)
  - Concrete walks traced from the OSM footways (main SW-NE diagonal, SE diagonal, NW cross, the
    central N-S axis between Library West's door and the Auditorium, the two E-W cross walks),
    the paved central square with its six raised planters, benches at OSM bench nodes, the Garden
    Terrace planters and brick benches, the plaza-edge terrace in front of Smathers, the gator on
    its plinth, the Venetian Renaissance well-head (OSM node 5623470779) in the Smathers garden.
  - Trees are NOT modelled here (the generator places them from OSM points).

TRAVERSAL (vanilla SM64 moves at 1 m = 100 units; reach = jump peak + the 0.78 m floor snap)
  Library West: planter (0.75) -> colonnade roof (4.6, double jump / back-flip, or jump up
    through it from below) -> 9.0 m sun-shade band -> eyebrow ledges 12.6 / 16.2 / 19.8 / 23.4
    (3.6 m apart, double jump in place; the ledges are jump-through) -> parapet 26.0 -> roof 25.3
    -> penthouse 29.3. Drop to the addition roof (15.0) without fall damage (10.3 m < 11.5 m).
  Smathers: the stepped angle buttresses at both ends of the west (Plaza) face have 0.8 m deep
    set-offs at 3.6 / 7.2 / 10.8 m -> eave 14.0 -> tile roofs (ridge 18.0) -> entrance tower top
    (18.2/18.9) -> flat stacks roof (14.3/15.0) -> stair turret (16.4). The three shallow
    buttresses between the bays are 0.8 m deep with a limestone perch at 8.4 m.
  Plaza: everything up to 0.75 m (benches, planters, terraces, plinth) is a step-up (top-only
    collision, Mario walks onto it); the well-head (1.0 m) is a closed box.
  Collision notes: ledges, the colonnade slab and step-up props are deliberately top-only (one-way
    platforms); thin posts, mullions, pinnacles and window reveals are visual only; the gator has
    a top-only pad at 1.06 m (step-up from its 0.7 m plinth).
    Everything else is closed: walls 0..parapet, roof decks, 0.7 m parapet copings (step-up),
    gable triangles, roof slopes; no downward-facing (ceiling) triangles anywhere.

OUTPUT PARTS (build): <slug>.visual / <slug>.collision per entry, plus "plaza_americas.walks"
  (visual, decal=True, z_offset_m=0.03: walk ribbons + paving, draw as a decal/second ground layer).
  Every part carries "landmark": <slug>. Meshes are triangles only, flat, with a "UVMap" in texture
  repeats (projected per _common.project_uv, explicit 0..n UVs on window bands / openings so whole
  windows tile), every face < 11.5 repeats across.

Sources (reviewed):
  - R-BARC, University of Florida Library West:https://r-barc.com/work/university-of-florida-library-west
  - SchoolDesigns, UF Library West Addition/Renovation (Long & Associates, 05/2006, "completes the
    public urban edge", scale/texture of the Gothic neighbours):
    https://schooldesigns.com/Projects/university-of-florida-library-west-addition-renovation
  - Kawneer project page (6-storey building + 4-storey addition, curtain walls):
    https://www.kawneer.com/projects/leed/university-of-florida-library-west/
  - UF Libraries, Colonnade project (290 seats, brick benches, Garden Terrace, plaza-edge terrace,
    solar panels): https://www.uflib.ufl.edu/libcoll_colonnade.html
  - UF Libraries 2025-08-15, alligator "Focused Attention" on the new garden terrace, limestone
    base facing the Plaza: https://communications.uflib.ufl.edu/2025/08/15/longtime-library-donors-alligator-is-released-on-new-garden-terrace/
  - SOURCE (UF Libraries magazine) 2025 "Colonnade Reimagined" (phase 1 removed the eastern
    section; terraces replace sabal palms), via search summary: https://journals.flvc.org/source/article/view/138616
  - Independent Florida Alligator, colonnade "partially taken down and rebuilt taller and
    narrower": https://www.alligator.org/r/0c8baee5af
  - Wikipedia: Smathers Library (Gainesville, Florida); List of University of Florida buildings
    (Library West 1967 / 2006; Smathers 1927, Edwards + Fulton, 1950 renovation)
  - UF Archives, Smathers Library history: https://web.uflib.ufl.edu/ufarch/xsmathers.htm
  - Wikipedia: Plaza of the Americas (Gainesville, Florida) (Olmsted Jr. + Phillips 1925 plan,
    cement and brick crosswalks, 2017 renovation added seating)
  - OpenStreetMap (c) contributors, ODbL: ways 196848215, 891179070, 154223625, 859953340,
    264182367, the footways named below, bench / entrance / well-head nodes (data/uf/tiles/t6.osm)
  Facade details beyond these sources (window rhythm, buttress set-offs, eyebrow ledges, tower
  pinnacles) are stylised from general knowledge of UF Collegiate Gothic and 1960s campus
  modernism, sized for SM64 traversal.
"""
import math

try:  # the generator imports this module as part of the `landmarks` package
    from . import _common as _C
except Exception:  # pragma: no cover - standalone import
    try:
        from landmarks import _common as _C  # type: ignore
    except Exception:
        _C = None

SLUG = "library_west_smathers_plaza"

_PALETTE_NAMES = (
    "brick_red", "brick_dark", "limestone", "roof_tile_red", "roof_dark", "copper_green",
    "window_dark", "window_glass", "door_wood", "concrete", "metal_gray", "plaza_brick", "grass",
    "path", "water", "dark_trim", "white_trim", "rock", "bronze",
)
_FALLBACK_TILE = {"window_glass": 3.0, "grass": 4.0, "path": 3.0, "water": 6.0, "rock": 3.0}
_FALLBACK_COLOR = {
    "brick_red": "#A9533A", "brick_dark": "#7A3828", "limestone": "#D6C8A4", "roof_tile_red": "#B0532F",
    "roof_dark": "#4C4C52", "copper_green": "#5E9C88", "window_dark": "#2E3A48", "window_glass": "#6E94B4",
    "door_wood": "#6B4226", "concrete": "#B8B4AA", "metal_gray": "#8A8E92", "plaza_brick": "#A65A42",
    "grass": "#5F9A3F", "path": "#C6C0B2", "water": "#3C78B4", "dark_trim": "#3A3430",
    "white_trim": "#E6E2D8", "rock": "#8C8272",
}

LW_ID = "r12122775/196848215"
LW_SLIVER_ID = "r12122775/891179070"
COLONNADE_ID = "w859953340"
SMATHERS_ID = "w154223625"
PLAZA_AREA_ID = "w264182367"

# walkway ribbons drawn by this module (OSM way id, width m); the generator can skip these
RIBBON_WAYS = (
    ("w427929303", 3.2),   # main SW-NE diagonal (Little Hall corner -> Library West colonnade)
    ("w595211017", 2.8),   # SE diagonal + north spur of the central axis
    ("w436088983", 2.6),   # south diagonal (48,114) -> (95,148)
    ("w427929305", 2.4),   # NW cross, arm 1
    ("w586111820", 2.4),   # NW cross, arm 2
    ("w860122323", 2.8),   # central axis, west walk (x = 31)
    ("w606699058", 2.8),   # central axis, east walk (x = 48)
    ("w427929304", 3.0),   # E-W cross walk at y = 191
    ("w427929302", 2.6),   # E-W cross walk at y = 143
    ("w595211057", 2.0),   # central median cross walk y = 213
    ("w1005260344", 2.0),  # central median cross walk y = 232
)
# OSM ways / areas / nodes this module replaces in the plaza (informational for the generator)
REPLACED_WAYS = tuple(w for w, _ in RIBBON_WAYS) + (
    "w860122325",   # Smathers Walkway (covered) under the colonnade -> colonnade paving
    "w1105642064",  # curved path through the old palm bed -> Garden Terrace paving
    "w586114121",   # covered walk to the Library West door -> colonnade paving
    "w481256524",   # covered sidewalk along Library West's east side -> colonnade paving
)
REPLACED_AREAS = ("w595211018", "w595211010", "w595211012", "w595211013", "w595211014",
                  "w595211015", "w595211016")
# 17 sabal palms of the old Library West entrance bed, removed in the 2025 Garden Terrace work
REMOVED_POINTS = tuple("n92917807%02d" % i for i in range(85, 100)) + ("n9291780800", "n9291780801")


def _door(name, pos, facing, primary, note, opening=None, recess=0.0):
    d = {"name": name, "pos_m": tuple(pos), "facing_deg": float(facing), "primary": primary, "note": note}
    if opening:
        d["opening_m"] = tuple(opening)
    if recess:
        d["recess_m"] = recess
    return d


LANDMARKS = [
    {
        "slug": "library_west",
        "name": "Library West",
        "osm_ids": [LW_ID, LW_SLIVER_ID],
        "center_m": (38.9, 285.6),
        "height_m": 26.0,
        "doors": [
            # pos = the recessed door plane (glass wall plane y = 258.43 at x = 38.91, recess 0.35 m)
            _door("DOOR_library_west_1", (38.91, 258.78, 0.0), 180.0, True,
                  "Main revolving door (OSM 4741830154) in the two-storey glass wall, under the "
                  "colonnade's entrance canopy -> 'Library West After Dark'", (4.4, 3.2), 0.35),
            _door("DOOR_library_west_2", (23.27, 316.30, 0.0), 0.0, False,
                  "North door (OSM 10117492280) in the notch west of the curved glass front"),
            _door("DOOR_library_west_3", (54.46, 316.29, 0.0), 0.0, False,
                  "North door (OSM 10117492278) in the notch east of the curved glass front"),
        ],
    },
    {
        "slug": "library_colonnade",
        "name": "Library Colonnade",
        "osm_ids": [COLONNADE_ID],
        "center_m": (52.0, 247.0),
        "height_m": 4.6,
        "budget_note": "no own stages.json entry: collision counted in library_west's 250, "
                       "visual in plaza_of_the_americas' 900",
        "doors": [],
    },
    {
        "slug": "smathers_library",
        "name": "Smathers Library",
        "osm_ids": [SMATHERS_ID],
        "center_m": (145.4, 232.8),
        "height_m": 18.0,
        "doors": [
            _door("DOOR_smathers_library_1", (127.55, 244.81, 0.0), 270.0, True,
                  "Main entrance (OSM 4741830122) in the west face of the entrance tower, facing "
                  "the Plaza -> 'Smathers Stacks Slide'", (2.6, 4.0), 0.6),
            _door("DOOR_smathers_library_2", (161.59, 253.63, 0.0), 180.0, False,
                  "Side door (OSM 10083724148) on the north range, facing the east courtyard",
                  (2.0, 3.5)),
        ],
    },
    {
        "slug": "plaza_of_the_americas",
        "name": "Plaza of the Americas (hardscape)",
        "osm_ids": [],
        "osm_area_ids": [PLAZA_AREA_ID],
        "center_m": (51.8, 182.6),
        "replaces_ways": list(REPLACED_WAYS),
        "replaces_areas": list(REPLACED_AREAS),
        "removes_points": list(REMOVED_POINTS),
        "doors": [],
        "notes": "Walk ribbons are visual-only decals at z = +0.03 m (ground collision is the "
                 "generator's); skip the listed OSM ways/areas to avoid double paths and the "
                 "listed palm nodes (removed 2025, they would stand in the Garden Terrace).",
    },
]

# ============================================================================ small vector helpers


def _tile(m):
    if _C is not None and m in _C.PALETTE:
        return float(_C.PALETTE[m]["tile_m"])
    return _FALLBACK_TILE.get(m, 2.0)


def _newell(pts):
    nx = ny = nz = 0.0
    for (x1, y1, z1), (x2, y2, z2) in zip(pts, pts[1:] + pts[:1]):
        nx += (y1 - y2) * (z1 + z2)
        ny += (z1 - z2) * (x1 + x2)
        nz += (x1 - x2) * (y1 + y2)
    return (nx, ny, nz)


def _project_uv(pts3, tile_m):
    """Same convention as _common.project_uv: floors top-down, walls along the wall; repeats."""
    if _C is not None:
        return _C.project_uv(pts3, tile_m)
    nx, ny, nz = _newell(pts3)
    t = max(tile_m, 1e-6)
    if abs(nz) >= max(abs(nx), abs(ny)) * 1.0001:
        uvs = [(p[0] / t, p[1] / t) for p in pts3]
    else:
        L = math.hypot(nx, ny) or 1.0
        hx, hy = -ny / L, nx / L
        uvs = [((p[0] * hx + p[1] * hy) / t, p[2] / t) for p in pts3]
    du = math.floor(min(u for u, _ in uvs))
    dv = math.floor(min(v for _, v in uvs))
    return [(u - du, v - dv) for u, v in uvs]


def _signed_area(poly):
    a = 0.0
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        a += x1 * y2 - x2 * y1
    return a / 2.0


def _ccw(poly):
    poly = [tuple(p) for p in poly]
    return poly if _signed_area(poly) > 0 else list(reversed(poly))


def _tn(a, b):
    """Unit tangent a->b, outward normal (right-hand side), length."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy)
    t = (dx / L, dy / L)
    return t, (t[1], -t[0]), L


def _P(a, t, n, u, w, z):
    return (a[0] + t[0] * u + n[0] * w, a[1] + t[1] * u + n[1] * w, z)


def _inset(ring, d):
    """Offset a CCW ring inward by d (mitred, clamped)."""
    out = []
    k = len(ring)
    for i in range(k):
        p0, p1, p2 = ring[i - 1], ring[i], ring[(i + 1) % k]
        t1, _, _ = _tn(p0, p1)
        t2, _, _ = _tn(p1, p2)
        n1 = (-t1[1], t1[0])  # left = inward for CCW
        n2 = (-t2[1], t2[0])
        mx, my = n1[0] + n2[0], n1[1] + n2[1]
        ml = math.hypot(mx, my)
        if ml < 1e-6:
            mx, my, ml = n1[0], n1[1], 1.0
        mx, my = mx / ml, my / ml
        cosv = mx * n1[0] + my * n1[1]
        s = d / max(cosv, 0.35)
        out.append((p1[0] + mx * s, p1[1] + my * s))
    return out


def _clip_plane(pts, axis, k, keep_le):
    """Sutherland-Hodgman clip of a 3D polygon against dot(p, axis) <= k (or >= k)."""
    def side(p):
        v = p[0] * axis[0] + p[1] * axis[1] + p[2] * axis[2] - k
        return v if keep_le else -v
    out = []
    n = len(pts)
    for i in range(n):
        p, q = pts[i], pts[(i + 1) % n]
        sp, sq = side(p), side(q)
        if sp <= 0:
            out.append(p)
        if (sp < 0 < sq) or (sq < 0 < sp):
            t = sp / (sp - sq)
            out.append(tuple(p[j] + (q[j] - p[j]) * t for j in range(3)))
    return out


def _proj2(pts):
    """2D projection of a planar 3D polygon that keeps its winding: CCW in 2D iff the polygon
    faces +axis (returns points, sign of the dropped normal axis)."""
    n = _newell(pts)
    ax = max(range(3), key=lambda i: abs(n[i]))
    if ax == 2:
        P = [(p[0], p[1]) for p in pts]
    elif ax == 0:
        P = [(p[1], p[2]) for p in pts]
    else:
        P = [(p[2], p[0]) for p in pts]
    return P, (1.0 if n[ax] > 0 else -1.0)


def _cross2(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _earclip(P):
    """Ear clipping of a simple (or weakly simple) CCW 2D polygon -> CCW index triples."""
    idx = list(range(len(P)))
    tris = []
    guard = 0
    while len(idx) > 3 and guard < 20000:
        guard += 1
        m = len(idx)
        found = None
        for k in range(m):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % m]
            a, b, c = P[i0], P[i1], P[i2]
            if _cross2(a, b, c) <= 1e-9:
                continue
            ok = True
            for j in idx:
                if j in (i0, i1, i2):
                    continue
                q = P[j]
                if q == a or q == b or q == c:
                    continue
                if _cross2(a, b, q) > 1e-9 and _cross2(b, c, q) > 1e-9 and _cross2(c, a, q) > 1e-9:
                    ok = False
                    break
            if ok:
                found = k
                break
        if found is None:  # only collinear / reflex corners left: drop the flattest vertex
            k = min(range(m), key=lambda k: abs(_cross2(P[idx[k - 1]], P[idx[k]], P[idx[(k + 1) % m]])))
            idx.pop(k)
            continue
        tris.append((idx[found - 1], idx[found], idx[(found + 1) % m]))
        idx.pop(found)
    if len(idx) == 3 and _cross2(P[idx[0]], P[idx[1]], P[idx[2]]) > 1e-9:
        tris.append(tuple(idx))
    return tris


def _triangulate(pts):
    """Planar 3D polygon (any shape, consistent winding) -> index triples with the same facing."""
    if len(pts) == 3:
        return [(0, 1, 2)]
    P, sgn = _proj2(pts)
    if sgn > 0:
        return _earclip(P)
    k = len(P)
    rev = [P[k - 1 - i] for i in range(k)]
    return [tuple(k - 1 - i for i in reversed(t)) for t in _earclip(rev)]


def _is_convex(pts):
    P, sgn = _proj2(pts)
    k = len(P)
    for i in range(k):
        if sgn * _cross2(P[i - 1], P[i], P[(i + 1) % k]) < -1e-9:
            return False
    return True


def _split_grid(pts, axes_cells):
    """Split a planar 3D polygon into equal slabs along each axis so no piece is wider than
    cell: axes_cells = [(axis, cell)]. Concave polygons are triangulated first (clipping a
    concave polygon would leave overlapping bridges)."""
    need = False
    for axis, cell in axes_cells:
        vals = [p[0] * axis[0] + p[1] * axis[1] + p[2] * axis[2] for p in pts]
        need = need or (max(vals) - min(vals) > cell)
    if not need:
        return [pts]
    pieces = [pts] if _is_convex(pts) else [[pts[i] for i in t] for t in _triangulate(pts)]
    for axis, cell in axes_cells:
        nxt = []
        for poly in pieces:
            vals = [p[0] * axis[0] + p[1] * axis[1] + p[2] * axis[2] for p in poly]
            lo, hi = min(vals), max(vals)
            if hi - lo <= cell:
                nxt.append(poly)
                continue
            k = math.ceil((hi - lo) / cell)
            cuts = [lo + (hi - lo) * i / k for i in range(1, k)]
            rest = poly
            for c in cuts:
                left = _clip_plane(rest, axis, c, True)
                rest = _clip_plane(rest, axis, c, False)
                if len(left) >= 3:
                    nxt.append(left)
                if len(rest) < 3:
                    break
            if len(rest) >= 3:
                nxt.append(rest)
        pieces = nxt
    return pieces


def _split_for_tiles(pts, tile):
    """Keep each visual face under ~10 texture repeats across (contract: < ~12)."""
    nx, ny, nz = _newell(pts)
    cell = 11.0 * tile
    if abs(nz) >= max(abs(nx), abs(ny)) * 1.0001:
        axes = [((1.0, 0.0, 0.0), cell), ((0.0, 1.0, 0.0), cell)]
    else:
        L = math.hypot(nx, ny) or 1.0
        axes = [((-ny / L, nx / L, 0.0), cell), ((0.0, 0.0, 1.0), cell)]
    return _split_grid(pts, axes)


# ============================================================================ mesh builder
class _Mesh:
    """Polygons with palette material names -> one triangulated bpy mesh."""

    def __init__(self, name, visual=True):
        self.name = name
        self.visual = visual
        self.polys = []  # (pts3, material, uvs or None)

    def poly(self, pts, mat, hint=None, uvs=None):
        if mat not in _PALETTE_NAMES:
            raise ValueError("unknown palette material %r" % (mat,))
        pts = [(float(p[0]), float(p[1]), float(p[2])) for p in pts]
        if uvs is not None:
            uvs = [tuple(map(float, uv)) for uv in uvs]
        keep = []
        for i, p in enumerate(pts):
            if keep and max(abs(p[j] - pts[keep[-1]][j]) for j in range(3)) < 1e-5:
                continue
            keep.append(i)
        if len(keep) > 1 and max(abs(pts[keep[0]][j] - pts[keep[-1]][j]) for j in range(3)) < 1e-5:
            keep.pop()
        if len(keep) < 3:
            return
        pts = [pts[i] for i in keep]
        if uvs is not None:
            uvs = [uvs[i] for i in keep]
        n = _newell(pts)
        if math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2) < 1e-7:
            return
        if hint is not None and n[0] * hint[0] + n[1] * hint[1] + n[2] * hint[2] < 0:
            pts.reverse()
            if uvs is not None:
                uvs.reverse()
        self.polys.append((pts, mat, uvs))

    # ---------------------------------------------------------------- primitives
    def wall(self, a, b, z0, z1, mat, off=0.0, uvs=None):
        """Vertical quad a->b (outward normal on the right of a->b, i.e. CCW footprints)."""
        if z1 - z0 < 1e-4:
            return
        t, n, _ = _tn(a, b)
        pa = (a[0] + n[0] * off, a[1] + n[1] * off)
        pb = (b[0] + n[0] * off, b[1] + n[1] * off)
        self.poly([(pa[0], pa[1], z0), (pb[0], pb[1], z0), (pb[0], pb[1], z1), (pa[0], pa[1], z1)],
                  mat, (n[0], n[1], 0.0), uvs)

    def flat(self, ring, z, mat, up=True):
        self.poly([(q[0], q[1], z) for q in ring], mat, (0.0, 0.0, 1.0 if up else -1.0))

    def flat_split(self, ring, z, mat, cell=20.0, up=True):
        """Flat polygon split on a world grid (collision floors: no triangle wider than ~cell)."""
        pts = [(x, y, z) for x, y in _ccw(ring)]
        for piece in _split_grid(pts, [((1.0, 0.0, 0.0), cell), ((0.0, 1.0, 0.0), cell)]):
            self.poly(piece, mat, (0.0, 0.0, 1.0 if up else -1.0))

    def rect(self, x0, y0, x1, y1, z, mat, up=True):
        self.flat([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z, mat, up)

    def prism_walls(self, ring, z0, z1, mat, skip=()):
        ring = _ccw(ring)
        for i, (a, b) in enumerate(zip(ring, ring[1:] + ring[:1])):
            if i not in skip:
                self.wall(a, b, z0, z1, mat)

    def box(self, x0, y0, z0, x1, y1, z1, mat, top=None, bottom=None, sides=True):
        ring = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        if sides:
            self.prism_walls(ring, z0, z1, mat)
        if top:
            self.flat(ring, z1, top)
        if bottom:
            self.flat(ring, z0, bottom, up=False)

    def obox(self, cx, cy, ang_deg, L, W, z0, z1, mat, top=None, bottom=None, sides=True):
        """Box of length L along heading ang_deg (map angle, CCW from east), width W."""
        c, s = math.cos(math.radians(ang_deg)), math.sin(math.radians(ang_deg))
        ring = []
        for u, w in ((-L / 2, -W / 2), (L / 2, -W / 2), (L / 2, W / 2), (-L / 2, W / 2)):
            ring.append((cx + c * u - s * w, cy + s * u + c * w))
        if sides:
            self.prism_walls(ring, z0, z1, mat)
        if top:
            self.flat(ring, z1, top)
        if bottom:
            self.flat(ring, z0, bottom, up=False)
        return ring

    def ledge(self, a, b, ztop, depth, thick, mat, ends=(True, True), bottom=True, top_mat=None):
        """Projecting slab along wall a->b (visual): top, front, bottom, ends."""
        t, n, L = _tn(a, b)
        zb = ztop - thick
        a1 = (a[0] + n[0] * depth, a[1] + n[1] * depth)
        b1 = (b[0] + n[0] * depth, b[1] + n[1] * depth)
        self.poly([(a[0], a[1], ztop), (b[0], b[1], ztop), (b1[0], b1[1], ztop), (a1[0], a1[1], ztop)],
                  top_mat or mat, (0, 0, 1))
        self.wall(a1, b1, zb, ztop, mat)
        if bottom:
            self.poly([(a[0], a[1], zb), (a1[0], a1[1], zb), (b1[0], b1[1], zb), (b[0], b[1], zb)],
                      mat, (0, 0, -1))
        if ends[0]:
            self.wall(a, a1, zb, ztop, mat)
        if ends[1]:
            self.wall(b1, b, zb, ztop, mat)

    def ledge_top(self, a, b, ztop, depth, mat):
        """Collision: top face of a projecting ledge only (jump-through from below)."""
        t, n, L = _tn(a, b)
        a1 = (a[0] + n[0] * depth, a[1] + n[1] * depth)
        b1 = (b[0] + n[0] * depth, b[1] + n[1] * depth)
        self.poly([(a[0], a[1], ztop), (b[0], b[1], ztop), (b1[0], b1[1], ztop), (a1[0], a1[1], ztop)],
                  mat, (0, 0, 1))

    def fin(self, a, b, u, width, depth, z0, z1, mat, top=None):
        """Vertical pier / mullion standing on wall a->b at distance u (front + 2 sides [+ top])."""
        t, n, _ = _tn(a, b)
        u0, u1 = u - width / 2, u + width / 2
        p0, p1 = _P(a, t, n, u0, 0, 0), _P(a, t, n, u1, 0, 0)
        q0, q1 = _P(a, t, n, u0, depth, 0), _P(a, t, n, u1, depth, 0)
        self.wall(q0, q1, z0, z1, mat)
        self.wall(p0, q0, z0, z1, mat)
        self.wall(q1, p1, z0, z1, mat)
        if top:
            self.flat([p0, p1, q1, q0], z1, top)

    def rows(self, a, b, rows, zlo=None, zhi=None, off=0.0):
        """Horizontal bands on wall a->b; window bands get explicit UVs (whole windows)."""
        t, n, L = _tn(a, b)
        for lo, hi, mat in rows:
            if zlo is not None:
                lo = max(lo, zlo)
            if zhi is not None:
                hi = min(hi, zhi)
            if hi - lo < 1e-3:
                continue
            if mat == "window_dark":
                bay = L / max(1, round(L / 2.0))
                nv = max(1, round((hi - lo) / 2.4))
                npc = max(1, math.ceil(L / (10.5 * bay)))
                for k in range(npc):
                    u0, u1 = L * k / npc, L * (k + 1) / npc
                    pa = _P(a, t, n, u0, off, 0)
                    pb = _P(a, t, n, u1, off, 0)
                    self.poly([(pa[0], pa[1], lo), (pb[0], pb[1], lo), (pb[0], pb[1], hi), (pa[0], pa[1], hi)],
                              mat, (n[0], n[1], 0), [(u0 / bay, 0), (u1 / bay, 0), (u1 / bay, nv), (u0 / bay, nv)])
            else:
                pa = _P(a, t, n, 0, off, 0)
                pb = _P(a, t, n, L, off, 0)
                self.wall((pa[0], pa[1]), (pb[0], pb[1]), lo, hi, mat)

    def facade(self, a, b, z0, z1, wall_mat, openings, reveal_mat="limestone"):
        """Wall a->b from z0 to z1 with openings (dicts from _op). Openings sharing a column
        must have the same (u0, u1). Pointed arches: 'apex' > 0 raises the head to a point."""
        t, n, L = _tn(a, b)
        cols = {}
        for o in openings:
            cols.setdefault((round(o["u0"], 4), round(o["u1"], 4)), []).append(o)
        keys = sorted(cols)

        def P(u, v, w=0.0):
            return _P(a, t, n, u, w, v)

        def quad(u0, u1, v0, v1):
            if u1 - u0 > 1e-4 and v1 - v0 > 1e-4:
                self.poly([P(u0, v0), P(u1, v0), P(u1, v1), P(u0, v1)], wall_mat, (n[0], n[1], 0))

        cur = 0.0
        for (u0, u1) in keys:
            if u0 > cur + 1e-4:
                quad(cur, u0, z0, z1)
            um = (u0 + u1) / 2
            vb, apex_prev = z0, 0.0
            for o in sorted(cols[(u0, u1)], key=lambda o: o["v0"]):
                self._piece(P, n, u0, u1, um, vb, apex_prev, o["v0"], wall_mat)
                self._opening(P, n, o, reveal_mat)
                vb, apex_prev = o["v1"], o["apex"]
            self._piece(P, n, u0, u1, um, vb, apex_prev, z1, wall_mat)
            cur = u1
        if cur < L - 1e-4:
            quad(cur, L, z0, z1)

    def _piece(self, P, n, u0, u1, um, vb, apex, top, mat):
        if apex > 0:
            if top - (vb + apex) < 1e-4:
                return
            self.poly([P(u0, vb), P(um, vb + apex), P(u1, vb), P(u1, top), P(u0, top)], mat, (n[0], n[1], 0))
        elif top - vb > 1e-4:
            self.poly([P(u0, vb), P(u1, vb), P(u1, top), P(u0, top)], mat, (n[0], n[1], 0))

    def _opening(self, P, n, o, reveal_mat):
        u0, u1, v0, v1, apex, d = o["u0"], o["u1"], o["v0"], o["v1"], o["apex"], o["depth"]
        um = (u0 + u1) / 2
        out = [(u0, v0), (u1, v0), (u1, v1)] + ([(um, v1 + apex)] if apex > 0 else []) + [(u0, v1)]
        uvs = None
        if o["mat"] in ("window_dark", "window_glass"):
            hv = (v1 + apex - v0)
            reps_v = max(1, round(hv / 2.6))
            reps_u = max(1, round((u1 - u0) / 1.6))
            uvs = [((u - u0) / (u1 - u0) * reps_u, (v - v0) / hv * reps_v) for u, v in out]
        self.poly([P(u, v, -d) for u, v in out], o["mat"], (n[0], n[1], 0), uvs)
        if d > 0:
            cu = sum(u for u, _ in out) / len(out)
            cv = sum(v for _, v in out) / len(out)
            for (pu, pv), (qu, qv) in zip(out, out[1:] + out[:1]):
                mu, mv = (pu + qu) / 2, (pv + qv) / 2
                c3, m3 = P(cu, cv), P(mu, mv)
                hint = (c3[0] - m3[0], c3[1] - m3[1], c3[2] - m3[2])
                self.poly([P(pu, pv), P(qu, qv), P(qu, qv, -d), P(pu, pv, -d)], reveal_mat, hint)

    def pyramid(self, cx, cy, z0, half, h, mat):
        c = [(cx - half, cy - half), (cx + half, cy - half), (cx + half, cy + half), (cx - half, cy + half)]
        apex = (cx, cy, z0 + h)
        for p, q in zip(c, c[1:] + c[:1]):
            mx, my = (p[0] + q[0]) / 2 - cx, (p[1] + q[1]) / 2 - cy
            self.poly([(p[0], p[1], z0), (q[0], q[1], z0), apex], mat, (mx, my, half))

    def ribbon(self, pts2, w, z, mat):
        """Mitred flat strip along a polyline (walkway decal)."""
        if len(pts2) < 2:
            return
        h = w / 2.0
        offs = []
        k = len(pts2)
        for i in range(k):
            if i == 0:
                t, _, _ = _tn(pts2[0], pts2[1])
                m, s = (-t[1], t[0]), h
            elif i == k - 1:
                t, _, _ = _tn(pts2[-2], pts2[-1])
                m, s = (-t[1], t[0]), h
            else:
                t1, _, _ = _tn(pts2[i - 1], pts2[i])
                t2, _, _ = _tn(pts2[i], pts2[i + 1])
                l1, l2 = (-t1[1], t1[0]), (-t2[1], t2[0])
                mx, my = l1[0] + l2[0], l1[1] + l2[1]
                ml = math.hypot(mx, my) or 1.0
                m = (mx / ml, my / ml)
                s = h / max(m[0] * l1[0] + m[1] * l1[1], 0.5)
            offs.append((m, s))
        for i in range(k - 1):
            (m0, s0), (m1, s1) = offs[i], offs[i + 1]
            p0, p1 = pts2[i], pts2[i + 1]
            L0 = (p0[0] + m0[0] * s0, p0[1] + m0[1] * s0)
            R0 = (p0[0] - m0[0] * s0, p0[1] - m0[1] * s0)
            L1 = (p1[0] + m1[0] * s1, p1[1] + m1[1] * s1)
            R1 = (p1[0] - m1[0] * s1, p1[1] - m1[1] * s1)
            self.poly([(R0[0], R0[1], z), (R1[0], R1[1], z), (L1[0], L1[1], z), (L0[0], L0[1], z)], mat, (0, 0, 1))

    # ---------------------------------------------------------------- output
    def triangles(self):
        """-> [(3 points, material, 3 uvs)]: tile-split, ear-clipped, degenerate-free."""
        out = []
        for pts, m, uvs in self.polys:
            if self.visual and uvs is None:
                pieces = [(piece, _project_uv(piece, _tile(m))) for piece in _split_for_tiles(pts, _tile(m))
                          if len(piece) >= 3]
            else:
                pieces = [(pts, uvs if uvs is not None else _project_uv(pts, _tile(m)))]
            for piece, puv in pieces:
                for t in _triangulate(piece):
                    a, b, c = (piece[i] for i in t)
                    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
                    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
                    area = 0.5 * math.sqrt((uy * vz - uz * vy) ** 2 + (uz * vx - ux * vz) ** 2 + (ux * vy - uy * vx) ** 2)
                    if area < 2e-4:
                        continue
                    out.append(((a, b, c), m, tuple(puv[i] for i in t)))
        return out

    def tri_count(self):
        return len(self.triangles())

    def build(self):
        """-> (bpy mesh, material_slots, triangle count). Triangles only, flat, UVs in repeats."""
        import bmesh
        import bpy
        tris = self.triangles()
        slots = []
        for _, m, _ in tris:
            if m not in slots:
                slots.append(m)
        bm = bmesh.new()
        uvl = bm.loops.layers.uv.new("UVMap")
        for pts, m, uvs in tris:
            try:
                f = bm.faces.new([bm.verts.new(p) for p in pts])
            except ValueError:
                continue
            f.material_index = slots.index(m)
            f.smooth = False
            for loop, (u, v) in zip(f.loops, uvs):
                loop[uvl].uv = (u, v)
        me = bpy.data.meshes.new(self.name)
        bm.to_mesh(me)
        bm.free()
        me.update()
        return me, slots, len(me.polygons)


def _op(u0, u1, v0, v1, mat="window_dark", apex=0.0, depth=0.0):
    return {"u0": float(u0), "u1": float(u1), "v0": float(v0), "v1": float(v1), "mat": mat,
            "apex": float(apex), "depth": float(depth)}


def _col(uc, w):
    return uc - w / 2.0, uc + w / 2.0


# ============================================================================ data checks
def _verify_footprints(ctx, log):
    """Every hard-coded OSM vertex must match campus.json within 0.05 m."""
    want = {
        LW_ID: LW_S + LW_N_CW,
        SMATHERS_ID: SM_RING_CW,
        COLONNADE_ID: [(19.11, 248.68), (78.73, 248.49), (85.11, 273.76), (123.24, 248.26), (19.03, 241.09)],
    }
    blds = {}
    try:
        for b in ctx["campus"]["buildings"]:
            if b["id"] in want:
                blds[b["id"]] = b["pts"]
    except Exception:
        log.append("WARN campus.json buildings not available; footprints not verified")
        return
    for bid, pts in want.items():
        src = blds.get(bid)
        if not src:
            log.append("WARN %s not in campus.json" % bid)
            continue
        worst = 0.0
        for p in pts:
            d = min(math.hypot(p[0] - q[0], p[1] - q[1]) for q in src)
            worst = max(worst, d)
        if worst > 0.05:
            log.append("WARN %s: hard-coded vertex %.2f m away from campus.json" % (bid, worst))


def _way_pts(ctx, wid):
    try:
        for w in ctx["campus"]["ways"]:
            if w["id"] == wid:
                return [tuple(p) for p in w["pts"]]
    except Exception:
        pass
    return None


def _area_pts(ctx, aid):
    try:
        for a in ctx["campus"]["areas"]:
            if a["id"] == aid:
                return [tuple(p) for p in a["pts"]]
    except Exception:
        pass
    return None


def _points(ctx, pred):
    out = []
    try:
        for p in ctx["campus"]["points"]:
            if pred(p["tags"]):
                out.append((p["id"], tuple(p["pt"])))
    except Exception:
        pass
    return out


# ============================================================================ LIBRARY WEST
# south (1967) block, CCW: SW, S1 -> R1 (recess west side) -> S2 (entrance glass, recessed)
#   -> R2 -> S3 -> E -> N -> W
LW_S = [(-1.31, 254.17), (19.16, 254.29), (19.34, 258.55), (58.33, 258.32), (58.41, 254.17),
        (78.76, 254.08), (78.79, 287.58), (-0.96, 287.6)]
# north (2006) addition, OSM (clockwise) order from (16.1, 287.56) to (61.44, 287.53)
LW_N_CW = [(16.1, 287.56), (16.19, 295.93), (6.14, 295.88), (6.07, 302.33), (4.81, 302.43), (4.78, 309.37),
           (6.04, 309.32), (6.06, 315.74), (15.01, 315.83), (15.02, 318.57), (22.59, 318.62), (22.6, 316.29),
           (23.93, 316.3), (23.93, 318.85), (28.43, 319.53), (31.71, 319.89), (35.39, 320.06), (39.17, 320.07),
           (42.35, 319.93), (46.35, 319.63), (49.84, 319.27), (53.71, 318.75), (53.71, 316.3), (55.2, 316.28),
           (55.22, 318.49), (62.66, 318.54), (62.73, 315.81), (72.05, 315.75), (71.95, 309.54), (73.09, 309.54),
           (73.04, 302.28), (71.76, 302.35), (71.66, 295.43), (61.62, 295.78), (61.44, 287.53)]
LW_N_COL_DROP = {(28.43, 319.53), (35.39, 320.06), (42.35, 319.93), (49.84, 319.27)}  # curve -> 4 chords
LW_N_COL_DROP2 = {(31.71, 319.89), (46.35, 319.63)}  # collision walls: curve -> 2 chords (<= 0.4 m)
LW_N_ROOF_COL = [  # roof collision of the addition as a few convex-ish pieces (CCW, inside the walls)
    [(16.1, 287.56), (61.44, 287.53), (61.62, 295.78), (16.19, 295.93)],
    [(6.14, 295.88), (16.19, 295.93), (61.62, 295.78), (71.66, 295.43), (72.05, 315.78), (6.06, 315.78)],
    [(4.78, 302.4), (6.1, 302.4), (6.1, 309.35), (4.78, 309.37)],
    [(71.9, 302.33), (73.04, 302.28), (73.09, 309.54), (71.9, 309.54)],
    [(15.01, 315.78), (22.6, 315.78), (22.59, 318.62), (15.02, 318.57)],
    [(22.6, 315.78), (55.2, 315.78), (55.2, 316.28), (53.71, 316.3), (53.71, 318.75),
     (39.17, 320.07), (23.93, 318.85), (23.93, 316.3), (22.6, 316.29)],
    [(55.2, 315.78), (62.73, 315.78), (62.66, 318.54), (55.22, 318.49)],
]
LW_N_ROOF_CURVE_VIS = [(22.6, 315.78), (55.2, 315.78), (55.2, 316.28), (53.71, 316.3), (53.71, 318.75),
                       (46.35, 319.63), (39.17, 320.07), (31.71, 319.89), (23.93, 318.85), (23.93, 316.3),
                       (22.6, 316.29)]

LW_BAND = 9.0                          # top of the sun-shade band over the glazed base
LW_EYEBROWS = (12.6, 16.2, 19.8, 23.4)  # ledge tops, 3.6 m apart (standing double jump reach 4.2)
LW_ROOF, LW_TOP = 25.3, 26.0           # roof deck, parapet coping (0.7 m: a step-up)
LW_ADD_TOP = 15.0                      # 2006 addition roof (flat, flush fascia)
LW_DOOR = (38.91, 258.53)              # OSM main entrance node


def _lw_upper_rows():
    rows, prev = [], LW_BAND
    for e in LW_EYEBROWS:  # brick spandrel, 1.8 m window band, brick head behind each eyebrow
        rows += [(prev, prev + 1.25, "brick_red"), (prev + 1.25, e - 0.55, "window_dark")]
        prev = e - 0.55
    rows += [(prev, LW_TOP - 0.3, "brick_red"), (LW_TOP - 0.3, LW_TOP, "limestone")]
    return rows


_LW_SIDE_BASE = [(0.0, 1.3, "brick_dark"), (1.3, 4.1, "window_dark"), (4.1, 5.9, "brick_red"),
                 (5.9, 8.3, "window_dark"), (8.3, LW_BAND, "concrete")]
_LW_SOUTH_BASE = [(0.0, 0.45, "brick_dark"), (0.45, 4.6, "window_glass"), (4.6, 5.4, "concrete"),
                  (5.4, 8.4, "window_glass"), (8.4, LW_BAND, "concrete")]


def _build_library_west(ctx, V, C, log):
    S = LW_S
    S1, R1, S2, R2, S3, E, N, W = [(S[i], S[(i + 1) % 8]) for i in range(8)]
    upper = _lw_upper_rows()

    # ---- plaza (south) faces: glazed base between brick piers, banded upper floors, ledges
    for (a, b), ends in ((S1, (True, False)), (S3, (False, True))):
        V.rows(a, b, _LW_SOUTH_BASE + upper)
        _, _, L = _tn(a, b)
        nb = max(2, round(L / 6.5))
        for k in range(nb + 1):
            u = 0.45 + (L - 0.9) * k / nb
            V.fin(a, b, u, 0.9, 0.25, 0.0, LW_BAND - 0.6, "brick_red")
        V.ledge(a, b, LW_BAND, 1.2, 0.6, "concrete", ends=ends)
        for e in LW_EYEBROWS:
            V.ledge(a, b, e, 0.9, 0.3, "concrete", ends=ends)
        C.wall(a, b, 0.0, LW_TOP, "brick_red")
        C.ledge_top(a, b, LW_BAND, 1.2, "concrete")
        for e in LW_EYEBROWS:
            C.ledge_top(a, b, e, 0.9, "concrete")

    # entrance glass wall: two storeys of glass, door void at the OSM main entrance node
    a, b = S2
    t, n, L = _tn(a, b)
    ud = (LW_DOOR[0] - a[0]) * t[0] + (LW_DOOR[1] - a[1]) * t[1]
    V.facade(a, b, 0.0, LW_BAND, "window_glass",
             [_op(ud - 2.2, ud + 2.2, 0.0, 3.2, "dark_trim", depth=0.35)], reveal_mat="metal_gray")
    V.rows(a, b, upper)
    for k in range(1, 6):
        u = L * k / 6
        if abs(u - ud) > 3.0:
            V.fin(a, b, u, 0.25, 0.3, 0.0, LW_BAND - 0.6, "dark_trim")
    V.ledge(a, b, LW_BAND, 1.2, 0.6, "concrete", ends=(False, False))
    for e in LW_EYEBROWS:
        V.ledge(a, b, e, 0.9, 0.3, "concrete", ends=(False, False))
    C.wall(a, b, 0.0, LW_TOP, "window_glass")
    C.ledge_top(a, b, LW_BAND, 1.2, "concrete")
    for e in LW_EYEBROWS:
        C.ledge_top(a, b, e, 0.9, "concrete")

    # recess side walls, east, west and north faces
    recess = [(0.0, 0.45, "brick_dark"), (0.45, 8.4, "window_glass"), (8.4, LW_BAND, "concrete"),
              (LW_BAND, LW_TOP - 0.3, "brick_red"), (LW_TOP - 0.3, LW_TOP, "limestone")]
    for a, b in (R1, R2):
        V.rows(a, b, recess)
        C.wall(a, b, 0.0, LW_TOP, "brick_red")
    for a, b in (E, W):
        V.rows(a, b, _LW_SIDE_BASE + upper)
        C.wall(a, b, 0.0, LW_TOP, "brick_red")
    na, nb_ = N
    n1, n2 = (61.44, 287.53), (16.1, 287.56)  # the addition covers N between these up to 15 m
    V.rows(na, n1, _LW_SIDE_BASE + upper)
    V.rows(n1, n2, _LW_SIDE_BASE + upper, zlo=LW_ADD_TOP)
    V.rows(n2, nb_, _LW_SIDE_BASE + upper)
    C.wall(na, nb_, 0.0, LW_TOP, "brick_red")

    # roof: deck, parapet (0.7 m coping = step-up), rooftop penthouse
    inner = _inset(S, 0.5)
    for p, q in zip(inner, inner[1:] + inner[:1]):
        V.wall(q, p, LW_ROOF, LW_TOP, "concrete")
    for i in range(8):
        o0, o1, i0, i1 = S[i], S[(i + 1) % 8], inner[i], inner[(i + 1) % 8]
        V.poly([(o0[0], o0[1], LW_TOP), (o1[0], o1[1], LW_TOP), (i1[0], i1[1], LW_TOP), (i0[0], i0[1], LW_TOP)],
               "limestone", (0, 0, 1))
        C.poly([(o0[0], o0[1], LW_TOP), (o1[0], o1[1], LW_TOP), (i1[0], i1[1], LW_TOP), (i0[0], i0[1], LW_TOP)],
               "limestone", (0, 0, 1))
    # roof deck collision as three convex pieces (west wing, middle over the recess, east wing)
    w0, w1, w2, w3, w4, w5, w6, w7 = inner

    def on_north(x):  # point on the inner north edge w6 -> w7 at x
        return (x, w6[1] + (w7[1] - w6[1]) * (w6[0] - x) / (w6[0] - w7[0]))
    for piece in ([w0, w1, w2, on_north(w2[0]), w7], [w2, w3, on_north(w3[0]), on_north(w2[0])],
                  [w3, w4, w5, w6, on_north(w3[0])]):
        V.flat(piece, LW_ROOF, "roof_dark")
        C.flat_split(piece, LW_ROOF, "roof_dark", cell=22.0)
    ph = (31.0, 269.0, LW_ROOF, 46.0, 280.0, LW_ROOF + 4.0)  # x0, y0, z0, x1, y1, z1
    V.box(*ph, "brick_red", top="roof_dark")
    V.ledge((ph[0], ph[1]), (ph[3], ph[1]), ph[5], 0.25, 0.4, "limestone", bottom=False)
    C.box(*ph, "brick_red", top="roof_dark")

    # ---- 2006 north addition
    ring = list(reversed(LW_N_CW))  # CCW; the closing edge (16.1,287.56)->(61.44,287.53) is shared
    curtain = [(0.0, 0.4, "dark_trim"), (0.4, 4.7, "window_glass"), (4.7, 5.3, "dark_trim"),
               (5.3, 14.4, "window_glass"), (14.4, LW_ADD_TOP, "metal_gray")]
    brick = [(0.0, 5.6, "brick_red"), (5.6, 13.2, "window_dark"), (13.2, 14.4, "brick_red"),
             (14.4, LW_ADD_TOP, "metal_gray")]  # brick base, two-storey reading-room glazing
    plain = [(0.0, 14.4, "brick_red"), (14.4, LW_ADD_TOP, "metal_gray")]
    tiny = [(0.0, LW_ADD_TOP, "brick_red")]
    ring = [p for p in ring if p not in LW_N_COL_DROP]
    for i in range(len(ring) - 1):
        a, b = ring[i], ring[i + 1]
        t, n, L = _tn(a, b)
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        tower = 15.0 < mx < 22.7 or 55.1 < mx < 62.8
        if n[1] > 0.5 and my > 316.0 and tower and L > 5.0:
            # brick stair towers flanking the curved glass front: tall slot window
            V.facade(a, b, 0.0, 14.4, "brick_red", [_op(L / 2 - 0.8, L / 2 + 0.8, 1.0, 13.4, depth=0.3)])
            V.rows(a, b, [(14.4, LW_ADD_TOP, "limestone")])
        elif n[1] > 0.5 and my > 315.5:
            V.rows(a, b, curtain)
        elif L < 1.6:
            V.rows(a, b, tiny)
        elif L < 3.0:
            V.rows(a, b, plain)
        else:
            V.rows(a, b, brick)
    for piece in LW_N_ROOF_COL[:5] + [LW_N_ROOF_CURVE_VIS] + LW_N_ROOF_COL[6:]:
        V.flat(piece, LW_ADD_TOP, "roof_dark")
    cring = [p for p in ring if p not in LW_N_COL_DROP2]
    for i in range(len(cring) - 1):
        C.wall(cring[i], cring[i + 1], 0.0, LW_ADD_TOP, "brick_red")
    for piece in LW_N_ROOF_COL:
        C.flat(piece, LW_ADD_TOP, "roof_dark")


# ============================================================================ COLONNADE
CO_Y0, CO_Y1 = 241.4, 247.6           # main walk (6.2 m wide)
CO_X0, CO_X1 = 19.1, 85.1
CO_CON = (35.0, 42.4, 258.4)          # entrance canopy to the Library West door (x0, x1, y1)
CO_EAST = (78.85, 85.1, 273.7)        # covered walk along Library West's east side (x0, x1, y1)
CO_Z0, CO_Z1 = 4.0, 4.6
CO_RECTS = [(19.1, 241.4, 35.0, 247.6), (35.0, 241.4, 42.4, 247.6), (42.4, 241.4, 60.0, 247.6),
            (60.0, 241.4, 78.85, 247.6), (78.85, 241.4, 85.1, 247.6), (35.0, 247.6, 42.4, 258.4),
            (78.85, 247.6, 85.1, 273.7)]
CO_OUTLINE = [(19.1, 241.4), (85.1, 241.4), (85.1, 273.7), (78.85, 273.7), (78.85, 247.6), (42.4, 247.6),
              (42.4, 258.4), (35.0, 258.4), (35.0, 247.6), (19.1, 247.6)]
CO_PIERS = [(19.55, 241.85), (35.45, 241.85), (41.95, 241.85), (35.45, 257.85), (41.95, 257.85),
            (84.65, 241.85)]
CO_POSTS = [(27.5, 241.75), (50.6, 241.75), (59.0, 241.75), (67.6, 241.75), (76.2, 241.75),
            (19.45, 247.25), (27.5, 247.25), (35.25, 247.25), (42.15, 247.25), (53.0, 247.25), (65.6, 247.25),
            (78.7, 247.25), (84.75, 256.4), (84.75, 265.0), (84.75, 273.35)]


def _build_colonnade(ctx, V, C, log):
    for x0, y0, x1, y1 in CO_RECTS:
        V.rect(x0, y0, x1, y1, CO_Z1, "roof_dark")
        V.rect(x0, y0, x1, y1, CO_Z0, "concrete", up=False)
        C.rect(x0, y0, x1, y1, CO_Z1, "roof_dark")  # jump-through (no ceiling)
    ring = _ccw(CO_OUTLINE)
    for a, b in zip(ring, ring[1:] + ring[:1]):
        V.wall(a, b, CO_Z0, CO_Z1, "limestone")
    for x, y in CO_PIERS:
        V.box(x - 0.45, y - 0.45, 0.0, x + 0.45, y + 0.45, CO_Z0, "brick_red")
        C.box(x - 0.45, y - 0.45, 0.0, x + 0.45, y + 0.45, CO_Z0, "brick_red")
    for x, y in CO_POSTS:
        V.box(x - 0.15, y - 0.15, 0.0, x + 0.15, y + 0.15, CO_Z0, "metal_gray")
    # solar panel rows on the roof (south-facing, 7 deg): walkable tops
    for x0 in (20.0, 31.2, 43.0, 54.2, 65.4, 76.6):
        x1 = x0 + 8.0
        lo, hi = CO_Z1 + 0.05, CO_Z1 + 0.65
        ya, yb = 242.1, 246.9
        top = [(x0, ya, lo), (x1, ya, lo), (x1, yb, hi), (x0, yb, hi)]
        V.poly(top, "window_dark", (0, -0.12, 1), [(0, 0), (4, 0), (4, 2), (0, 2)])
        V.poly([(x1, yb, CO_Z1), (x0, yb, CO_Z1), (x0, yb, hi), (x1, yb, hi)], "metal_gray", (0, 1, 0))
        V.poly([(x0, ya, CO_Z1), (x0, yb, CO_Z1), (x0, yb, hi), (x0, ya, lo)], "metal_gray", (-1, 0, 0))
        V.poly([(x1, ya, CO_Z1), (x1, ya, lo), (x1, yb, hi), (x1, yb, CO_Z1)], "metal_gray", (1, 0, 0))
        C.poly(top, "metal_gray", (0, -0.12, 1))


# ============================================================================ SMATHERS LIBRARY
SM_RING_CW = [(153.52, 205.63), (165.72, 205.61), (165.72, 203.01), (169.82, 203.0), (169.81, 195.72),
              (165.68, 195.73), (165.67, 192.7), (144.73, 192.76), (144.73, 191.95), (141.51, 191.96),
              (141.5, 188.86), (138.96, 188.87), (132.71, 188.88), (132.72, 192.1), (129.45, 192.11),
              (129.46, 197.33), (129.46, 200.01), (129.57, 239.23), (126.94, 239.23), (126.94, 240.98),
              (126.95, 244.81), (126.96, 248.28), (125.15, 248.28), (125.16, 253.49), (112.83, 253.5),
              (112.85, 266.67), (173.31, 266.58), (173.29, 253.62), (161.59, 253.64), (154.56, 253.65),
              (154.55, 245.24), (166.8, 245.22), (166.76, 215.48), (148.89, 215.5), (148.89, 210.34),
              (153.53, 210.33)]
SM_EAVE, SM_RIDGE = 14.0, 18.0
SM_W = (129.5, 141.51, 192.1)          # west range: eave x, east x, south gable y
SM_RIDGE_X = 135.5
SM_N = (112.84, 173.3, 253.55, 266.62)  # north range: x0, x1, south eave y, north eave y
SM_RIDGE_Y = 260.08
SM_TOWER = [(126.94, 239.23), (129.57, 239.23), (129.5, 253.55), (125.16, 253.49), (125.15, 248.28),
            (126.96, 248.28)]
SM_TOWER_ROOF, SM_TOWER_TOP = 18.2, 18.9
SM_E = [(141.51, 191.96), (144.73, 191.95), (144.73, 192.76), (165.67, 192.7), (165.68, 195.73),
        (165.72, 203.01), (165.72, 205.61), (153.52, 205.63), (153.53, 210.33), (148.89, 210.34),
        (148.89, 215.5), (166.76, 215.48), (166.8, 245.22), (154.55, 245.24), (154.56, 253.55),
        (141.51, 253.55)]
SM_E_ROOF, SM_E_TOP = 14.3, 15.0
SM_T = [(165.68, 195.73), (169.81, 195.72), (169.82, 203.0), (165.72, 203.01)]
SM_T_TOP = 16.4
SM_B = [(132.72, 192.1), (132.71, 188.88), (141.5, 188.86), (141.51, 191.96)]
SM_B_ROOF, SM_B_TOP = 8.0, 8.7
SM_DOOR = (126.95, 244.81)
SM_SIDE_DOOR = (161.59, 253.63)


def _rake(V, a, b, z_eave, z_ridge, u_ridge):
    """Stone coping on the two rakes of a gable wall a->b (outward right)."""
    t, n, L = _tn(a, b)
    for u0, u1, z0, z1 in ((0.0, u_ridge, z_eave, z_ridge), (u_ridge, L, z_ridge, z_eave)):
        o0, o1 = _P(a, t, n, u0, 0.15, 0), _P(a, t, n, u1, 0.15, 0)
        i0, i1 = _P(a, t, n, u0, -0.45, 0), _P(a, t, n, u1, -0.45, 0)
        V.poly([(o0[0], o0[1], z0 + 0.3), (o1[0], o1[1], z1 + 0.3), (i1[0], i1[1], z1 + 0.3),
                (i0[0], i0[1], z0 + 0.3)], "limestone", (0, 0, 1))
        V.poly([(o0[0], o0[1], z0), (o1[0], o1[1], z1), (o1[0], o1[1], z1 + 0.3), (o0[0], o0[1], z0 + 0.3)],
               "limestone", (n[0], n[1], 0))


def _gable(V, C, a, b, z_eave, z_ridge):
    t, n, L = _tn(a, b)
    m = (L / 2.0)
    tri = [(a[0], a[1], z_eave), (b[0], b[1], z_eave), _P(a, t, n, m, 0, z_ridge)]
    V.poly(tri, "brick_red", (n[0], n[1], 0))
    C.poly(tri, "brick_red", (n[0], n[1], 0))
    _rake(V, a, b, z_eave, z_ridge, m)


def _stepped_buttress(V, C, a, b, uc, width, tiers, collide_tops=None):
    """Buttress on wall a->b at u = uc: tiers = [(z0, z1, depth)], limestone set-off tops.
    collide_tops: tier indices whose top gets collision (default: all)."""
    t, n, _ = _tn(a, b)
    u0, u1 = uc - width / 2, uc + width / 2
    for k, (z0, z1, d) in enumerate(tiers):
        p0, p1 = _P(a, t, n, u0, 0, 0), _P(a, t, n, u1, 0, 0)
        q0, q1 = _P(a, t, n, u0, d, 0), _P(a, t, n, u1, d, 0)
        for M in (V, C):
            M.wall(q0, q1, z0, z1, "brick_red")
            M.wall(p0, q0, z0, z1, "brick_red")
            M.wall(q1, p1, z0, z1, "brick_red")
        top = [p0, p1, q1, q0]
        V.flat(top, z1, "limestone")
        if collide_tops is None or k in collide_tops:
            C.flat(top, z1, "limestone")


def _gothic_bay_cols(L, bays, pair=True, ground=True, lancet=(5.0, 10.8, 1.5), depth=0.4, w=1.7, gap=1.0,
                     ground_v=(1.0, 3.3)):
    """Openings for evenly spaced bays: one or two lancets (+ ground windows) per bay."""
    ops = []
    for c in bays:
        cols = [(c - gap / 2 - w, c - gap / 2), (c + gap / 2, c + gap / 2 + w)] if pair else [_col(c, w)]
        for u0, u1 in cols:
            if ground:
                ops.append(_op(u0, u1, ground_v[0], ground_v[1]))
            ops.append(_op(u0, u1, lancet[0], lancet[1], apex=lancet[2], depth=depth))
    return ops


def _build_smathers(ctx, V, C, log):
    wx, wx1, wy0 = SM_W
    nx0, nx1, ny0, ny1 = SM_N

    # ---- west range, Plaza face: buttressed reading-room lancets
    a, b = (129.57, 239.23), (129.45, 192.11)
    t, n, L = _tn(a, b)
    bays = [7.39, 18.17, 28.95, 39.73]
    V.facade(a, b, 0.0, SM_EAVE, "brick_red", _gothic_bay_cols(L, bays))
    V.ledge(a, b, SM_EAVE, 0.35, 0.45, "limestone", bottom=True)
    C.wall(a, b, 0.0, SM_EAVE, "brick_red")
    big = [(0.0, 3.6, 2.4), (3.6, 7.2, 1.6), (7.2, 10.8, 0.8)]
    for uc in (1.2, L - 1.2):
        _stepped_buttress(V, C, a, b, uc, 1.6, big)
    for uc in (12.78, 23.56, 34.34):  # shallow: one 0.8 m deep tier, limestone perch at 8.4
        _stepped_buttress(V, C, a, b, uc, 1.2, [(0.0, 8.4, 0.8)])

    # ---- west range, south gable end (two-storey bay in front of its east part)
    a1, b1 = (129.45, 192.11), (132.72, 192.1)
    V.facade(a1, b1, 0.0, SM_EAVE, "brick_red", [_op(0.85, 2.4, 1.0, 3.3), _op(0.85, 2.4, 5.0, 10.8, apex=1.2)])
    a2, b2 = (132.72, 192.1), (141.51, 192.08)
    _, _, L2 = _tn(a2, b2)
    V.facade(a2, b2, SM_B_TOP, SM_EAVE, "brick_red",
             [_op(L2 / 2 - 1.3, L2 / 2 + 1.3, 9.3, 12.2, apex=1.2, depth=0.4)])
    C.wall(a1, b2, 0.0, SM_EAVE, "brick_red")
    _gable(V, C, (wx - 0.05, wy0), (wx1, wy0), SM_EAVE, SM_RIDGE)

    # ---- roofs (red tile), west range ridge N-S meets the north range in valleys
    ry = SM_RIDGE_Y
    west_slope = [(wx, wy0, SM_EAVE), (SM_RIDGE_X, wy0, SM_RIDGE), (SM_RIDGE_X, ry, SM_RIDGE), (wx, ny0, SM_EAVE)]
    east_slope = [(wx1, wy0, SM_EAVE), (wx1, ny0, SM_EAVE), (SM_RIDGE_X, ry, SM_RIDGE), (SM_RIDGE_X, wy0, SM_RIDGE)]
    north_slope = [(nx0, ny1, SM_EAVE), (nx0, ry, SM_RIDGE), (nx1, ry, SM_RIDGE), (nx1, ny1, SM_EAVE)]
    south_slope = [(nx0, ny0, SM_EAVE), (wx, ny0, SM_EAVE), (SM_RIDGE_X, ry, SM_RIDGE), (wx1, ny0, SM_EAVE),
                   (nx1, ny0, SM_EAVE), (nx1, ry, SM_RIDGE), (nx0, ry, SM_RIDGE)]
    for poly, hint in ((west_slope, (-1, 0, 1.5)), (east_slope, (1, 0, 1.5)), (north_slope, (0, 1, 1.6)),
                       (south_slope, (0, -1, 1.6))):
        V.poly(poly, "roof_tile_red", hint)
        for piece in _split_grid(poly, [((1.0, 0.0, 0.0), 21.0), ((0.0, 1.0, 0.0), 21.0)]):
            C.poly(piece, "roof_tile_red", hint)

    # ---- north range
    a, b = (173.31, 266.58), (112.85, 266.67)  # north face
    t, n, L = _tn(a, b)
    bays = [L * (k + 0.5) / 7 for k in range(7)]
    V.facade(a, b, 0.0, SM_EAVE, "brick_red",
             _gothic_bay_cols(L, bays, pair=False, ground=False, lancet=(3.0, 10.6, 1.1), depth=0.0, w=1.8))
    C.wall(a, b, 0.0, SM_EAVE, "brick_red")
    # west gable end (faces Library West / the colonnade)
    a, b = (112.85, 266.67), (112.83, 253.5)
    t, n, L = _tn(a, b)
    V.facade(a, b, 0.0, SM_EAVE, "brick_red",
             [_op(L / 2 - 1.2, L / 2 + 1.2, 1.0, 3.3), _op(L / 2 - 1.2, L / 2 + 1.2, 4.8, 11.2, apex=1.8, depth=0.4),
              _op(1.6, 2.8, 5.4, 9.4, apex=0.6), _op(L - 2.8, L - 1.6, 5.4, 9.4, apex=0.6)])
    C.wall(a, b, 0.0, SM_EAVE, "brick_red")
    _gable(V, C, (nx0, ny1), (nx0, ny0), SM_EAVE, SM_RIDGE)
    # east gable end
    a, b = (173.29, 253.62), (173.31, 266.58)
    t, n, L = _tn(a, b)
    V.facade(a, b, 0.0, SM_EAVE, "brick_red",
             [_op(L / 2 - 1.2, L / 2 + 1.2, 1.0, 3.3), _op(L / 2 - 1.2, L / 2 + 1.2, 4.8, 11.2, apex=1.8)])
    C.wall(a, b, 0.0, SM_EAVE, "brick_red")
    _gable(V, C, (nx1, ny0), (nx1, ny1), SM_EAVE, SM_RIDGE)
    # south face, west of the tower
    a, b = (112.83, 253.5), (125.16, 253.49)
    V.facade(a, b, 0.0, SM_EAVE, "brick_red",
             _gothic_bay_cols(12.33, [3.3, 9.0], pair=False, lancet=(5.0, 10.6, 1.1), depth=0.0, w=1.8))
    C.wall(a, b, 0.0, SM_EAVE, "brick_red")
    # south face on the east courtyard, side door at the OSM entrance node
    a, b = (154.56, 253.65), (173.29, 253.62)
    t, n, L = _tn(a, b)
    ud = SM_SIDE_DOOR[0] - a[0]
    ops = [_op(ud - 1.0, ud + 1.0, 0.0, 2.9, "door_wood", apex=0.6),
           _op(ud - 1.0, ud + 1.0, 5.0, 10.6, apex=1.1)]
    for uc in (2.9, 14.4):
        ops += [_op(uc - 0.9, uc + 0.9, 1.0, 3.3), _op(uc - 0.9, uc + 0.9, 5.0, 10.6, apex=1.1)]
    V.facade(a, b, 0.0, SM_EAVE, "brick_red", ops)
    C.wall(a, b, 0.0, SM_EAVE, "brick_red")

    # ---- entrance tower (main door to the Plaza) + its stair block
    tw = SM_TOWER
    a, b = tw[5], tw[0]  # west face (entrance), north -> south
    t, n, L = _tn(a, b)
    ud = a[1] - SM_DOOR[1]
    dc = _col(ud, 2.6)
    V.facade(a, b, 0.0, SM_TOWER_TOP, "brick_red",
             [_op(dc[0], dc[1], 0.0, 3.2, "dark_trim", apex=0.8, depth=0.6),
              _op(dc[0], dc[1], 5.4, 11.2, apex=1.4, depth=0.4),
              _op(dc[0], dc[1], 13.8, 15.6, apex=0.5),
              _op(6.3, 7.7, 1.2, 3.2), _op(6.3, 7.7, 5.8, 10.6, apex=0.7)])
    V.ledge(a, b, 4.6, 0.3, 0.35, "limestone")
    V.ledge(a, b, 13.0, 0.3, 0.35, "limestone")
    V.ledge(a, b, 16.8, 0.3, 0.35, "limestone")
    V.facade(tw[0], tw[1], 0.0, SM_TOWER_TOP, "brick_red", [_op(0.6, 2.0, 6.0, 8.6, apex=0.5),
                                                            _op(0.6, 2.0, 10.6, 12.8, apex=0.5)])
    V.facade(tw[3], tw[4], 0.0, SM_TOWER_TOP, "brick_red", [_op(1.9, 3.3, 1.2, 3.0), _op(1.9, 3.3, 6.0, 8.4, apex=0.6),
                                                            _op(1.9, 3.3, 10.6, 13.0, apex=0.6)])
    V.wall(tw[4], tw[5], 0.0, SM_TOWER_TOP, "brick_red")
    V.wall(tw[1], tw[2], SM_EAVE, SM_TOWER_TOP, "brick_red")
    V.wall(tw[2], tw[3], SM_EAVE, SM_TOWER_TOP, "brick_red")
    C.prism_walls(tw, 0.0, SM_TOWER_TOP, "brick_red")
    _parapet_roof(V, C, tw, SM_TOWER_ROOF, SM_TOWER_TOP, 0.45)
    for i in (0, 5):  # pinnacles on the two Plaza-side corners
        p, pprev, pnext = tw[i], tw[i - 1], tw[(i + 1) % len(tw)]
        ti, _, _ = _tn(pprev, p)
        to, _, _ = _tn(p, pnext)
        cx, cy = p[0] - ti[0] * 0.35 + to[0] * 0.35, p[1] - ti[1] * 0.35 + to[1] * 0.35
        V.pyramid(cx, cy, SM_TOWER_TOP, 0.4, 1.9, "limestone")

    # ---- east stacks block (flat roof, parapet)
    e = SM_E
    k = len(e)
    erows = [(0.0, 2.6, "brick_red"), (2.6, 5.4, "window_dark"), (5.4, 8.6, "brick_red"),
             (8.6, 11.4, "window_dark"), (11.4, SM_E_TOP, "brick_red")]
    eplain = [(0.0, 8.6, "brick_red"), (8.6, 11.4, "window_dark"), (11.4, SM_E_TOP, "brick_red")]
    for i in range(k):
        a, b = e[i], e[(i + 1) % k]
        _, _, L = _tn(a, b)
        if i == 4:      # behind the stair turret
            C.wall(a, b, 0.0, SM_E_TOP, "brick_red")
            continue
        if i in (14, 15):  # against the north range / west range roofs
            V.rows(a, b, [(SM_EAVE, SM_E_TOP - 0.3, "brick_red"), (SM_E_TOP - 0.3, SM_E_TOP, "limestone")])
        else:
            V.rows(a, b, erows if L > 12.0 else eplain)
        C.wall(a, b, 0.0, SM_E_TOP, "brick_red")
    _parapet_roof(V, C, e, SM_E_ROOF, SM_E_TOP, 0.45)

    # ---- stair turret on the east side
    tt = SM_T
    for i in range(4):
        a, b = tt[i], tt[(i + 1) % 4]
        _, _, L = _tn(a, b)
        if i == 3:
            V.rows(a, b, [(SM_E_TOP, SM_T_TOP, "brick_red")])
        else:
            V.facade(a, b, 0.0, SM_T_TOP, "brick_red",
                     [_op(L / 2 - 0.4, L / 2 + 0.4, 3.0, 6.0), _op(L / 2 - 0.4, L / 2 + 0.4, 10.0, 13.6)])
    V.flat(tt, SM_T_TOP, "roof_dark")
    C.prism_walls(tt, 0.0, SM_T_TOP, "brick_red")
    C.flat(tt, SM_T_TOP, "roof_dark")
    for p in tt[1:3]:  # east corners
        cx = p[0] + (0.4 if p[0] < 167 else -0.4)
        cy = p[1] + (0.4 if p[1] < 199 else -0.4)
        V.pyramid(cx, cy, SM_T_TOP, 0.4, 1.4, "limestone")

    # ---- two-storey bay on the south gable
    bb = SM_B
    a, b = bb[1], bb[2]  # south face
    _, _, L = _tn(a, b)
    V.facade(a, b, 0.0, SM_B_TOP, "brick_red",
             [_op(L / 2 - 1.4, L / 2 + 1.4, 1.4, 6.4, apex=1.0),
              _op(0.9, 1.9, 1.4, 5.4, apex=0.5), _op(L - 1.9, L - 0.9, 1.4, 5.4, apex=0.5)])
    for a, b in ((bb[0], bb[1]), (bb[2], bb[3])):
        V.facade(a, b, 0.0, SM_B_TOP, "brick_red", [_op(1.0, 2.2, 4.0, 6.8, apex=0.5)])
    for i in range(3):
        C.wall(bb[i], bb[i + 1], 0.0, SM_B_TOP, "brick_red")
    _parapet_roof(V, C, bb, SM_B_ROOF, SM_B_TOP, 0.4)


def _parapet_roof(V, C, ring, z_roof, z_top, d):
    """Flat roof deck with a parapet whose coping is a step-up (z_top - z_roof <= 0.75)."""
    ring = _ccw(ring)
    inner = _inset(ring, d)
    k = len(ring)
    V.flat(inner, z_roof, "roof_dark")
    C.flat_split(inner, z_roof, "roof_dark", cell=22.0)
    for i in range(k):
        o0, o1, i0, i1 = ring[i], ring[(i + 1) % k], inner[i], inner[(i + 1) % k]
        V.wall(i1, i0, z_roof, z_top, "brick_red")
        cop = [(o0[0], o0[1], z_top), (o1[0], o1[1], z_top), (i1[0], i1[1], z_top), (i0[0], i0[1], z_top)]
        V.poly(cop, "limestone", (0, 0, 1))
        C.poly(cop, "limestone", (0, 0, 1))


# ============================================================================ PLAZA HARDSCAPE
PATH_Z = 0.03
PLAZA_CLIP = (-17.0, 113.0, 139.0, 241.4)   # ribbons stop at the colonnade paving
TERRACE_PAVING = [  # colonnade walk, Garden Terrace, east walk (rectangles, x0 y0 x1 y1)
    (19.1, 241.4, 85.1, 247.6), (19.2, 247.6, 58.4, 254.2), (19.3, 254.2, 58.35, 258.4),
    (58.4, 247.6, 78.8, 254.1), (78.8, 247.6, 85.1, 273.7)]
GARDEN_PLANTERS = ((20.6, 33.4), (44.0, 57.0))  # x ranges of the two Garden Terrace planters
EDGE_TERRACE = (89.0, 241.6, 121.5, 247.4, 0.45)
GATOR = (38.8, 238.3)                 # plinth 2.0 x 3.4 m, centred on the Library West axis
WELL_HEAD = (116.5, 220.6)


def _clip_polyline(pts, box):
    """Clip a polyline to an axis-aligned box -> list of polylines."""
    x0, y0, x1, y1 = box
    out, cur = [], []

    def inside(p):
        return x0 <= p[0] <= x1 and y0 <= p[1] <= y1

    for p, q in zip(pts, pts[1:]):
        # Liang-Barsky
        dx, dy = q[0] - p[0], q[1] - p[1]
        t0, t1 = 0.0, 1.0
        ok = True
        for pp, qq in ((-dx, p[0] - x0), (dx, x1 - p[0]), (-dy, p[1] - y0), (dy, y1 - p[1])):
            if abs(pp) < 1e-12:
                if qq < 0:
                    ok = False
                    break
            else:
                r = qq / pp
                if pp < 0:
                    t0 = max(t0, r)
                else:
                    t1 = min(t1, r)
        if not ok or t0 > t1:
            if len(cur) >= 2:
                out.append(cur)
            cur = []
            continue
        a = (p[0] + dx * t0, p[1] + dy * t0)
        b = (p[0] + dx * t1, p[1] + dy * t1)
        if cur and math.hypot(cur[-1][0] - a[0], cur[-1][1] - a[1]) < 1e-6:
            cur.append(b)
        else:
            if len(cur) >= 2:
                out.append(cur)
            cur = [a, b]
        if not inside(q):
            if len(cur) >= 2:
                out.append(cur)
            cur = []
    if len(cur) >= 2:
        out.append(cur)
    return out


def _bench(V, C, x, y, ang, z0=0.0, length=1.8, depth=0.55, h=0.45, mat="concrete", top="door_wood"):
    V.obox(x, y, ang, length, depth, z0, z0 + h, mat, top=top)
    ring = C.obox(x, y, ang, length, depth, z0, z0 + h, mat, sides=False)
    C.flat(ring, z0 + h, top)


def _gator(V, C, cx, cy, z0, heading_deg):
    """Low-poly bronze alligator (2.7 m), facing heading_deg (map angle)."""
    c, s = math.cos(math.radians(heading_deg)), math.sin(math.radians(heading_deg))

    def W(x, y, z):
        return (cx + c * x - s * y, cy + s * x + c * y, z0 + z)

    secs = [(-1.45, 0.04, 0.10, 0.15), (-0.95, 0.14, 0.07, 0.26), (-0.45, 0.30, 0.08, 0.36),
            (0.15, 0.34, 0.08, 0.38), (0.55, 0.22, 0.10, 0.31), (0.85, 0.20, 0.08, 0.30), (1.25, 0.10, 0.08, 0.19)]
    g = "bronze"   # dark statue bronze (palette entry added by the generator, round 3)
    for (xa, wa, ba, ta), (xb, wb, bb, tb) in zip(secs, secs[1:]):
        V.poly([W(xa, -wa, ta), W(xb, -wb, tb), W(xb, wb, tb), W(xa, wa, ta)], g, (0, 0, 1))
        V.poly([W(xa, wa, ba), W(xa, wa, ta), W(xb, wb, tb), W(xb, wb, bb)], g, (-s, c, 0))
        V.poly([W(xa, -wa, ba), W(xb, -wb, bb), W(xb, -wb, tb), W(xa, -wa, ta)], g, (s, -c, 0))
    x, w, b_, t_ = secs[0]
    V.poly([W(x, -w, b_), W(x, -w, t_), W(x, w, t_), W(x, w, b_)], g, (-c, -s, 0))
    x, w, b_, t_ = secs[-1]
    V.poly([W(x, w, b_), W(x, w, t_), W(x, -w, t_), W(x, -w, b_)], g, (c, s, 0))
    for lx, ly in ((0.35, 0.36), (0.35, -0.36), (-0.4, 0.38), (-0.4, -0.38)):
        p = W(lx, ly, 0.0)
        V.obox(p[0], p[1], heading_deg + (25 if lx > 0 else -25) * (1 if ly > 0 else -1), 0.24, 0.16,
               z0, z0 + 0.13, g, top=g)
    for ey in (0.11, -0.11):
        p = W(0.78, ey, 0.0)
        V.obox(p[0], p[1], heading_deg, 0.1, 0.08, z0 + 0.28, z0 + 0.35, "white_trim", top="white_trim")
    ring = [W(-0.6, -0.3, 0), W(0.9, -0.3, 0), W(0.9, 0.3, 0), W(-0.6, 0.3, 0)]
    C.flat([(p[0], p[1]) for p in ring], z0 + 0.36, "bronze")


def _nearest_dir(ctx, p, cache):
    """Direction (deg) of the nearest footway segment to p (for bench orientation)."""
    if "segs" not in cache:
        segs = []
        try:
            for w in ctx["campus"]["ways"]:
                if w["tags"].get("highway") in ("footway", "cycleway", "path", "pedestrian"):
                    pts = w["pts"]
                    for q, r in zip(pts, pts[1:]):
                        if -30 < q[0] < 150 and 100 < q[1] < 260:
                            segs.append((tuple(q), tuple(r)))
        except Exception:
            pass
        cache["segs"] = segs
    best, bd = 0.0, 1e9
    for q, r in cache["segs"]:
        dx, dy = r[0] - q[0], r[1] - q[1]
        L2 = dx * dx + dy * dy
        if L2 < 1e-6:
            continue
        tt = max(0.0, min(1.0, ((p[0] - q[0]) * dx + (p[1] - q[1]) * dy) / L2))
        d = math.hypot(q[0] + dx * tt - p[0], q[1] + dy * tt - p[1])
        if d < bd:
            bd, best = d, math.degrees(math.atan2(dy, dx))
    return best


def _build_plaza(ctx, V, C, P, log):
    # ---- walks (decal ribbons) from the OSM footways
    drawn = 0
    for wid, w in RIBBON_WAYS:
        pts = _way_pts(ctx, wid)
        if not pts:
            log.append("WARN plaza way %s missing in campus.json" % wid)
            continue
        for seg in _clip_polyline(pts, PLAZA_CLIP):
            P.ribbon(seg, w, PATH_Z, "path")
            drawn += 1
    # central square paving (OSM area w595211018) and the colonnade / Garden Terrace paving
    sq = _area_pts(ctx, "w595211018")
    if sq:
        P.flat(_ccw(sq), PATH_Z + 0.005, "concrete")
    for x0, y0, x1, y1 in TERRACE_PAVING:
        P.rect(x0, y0, x1, y1, PATH_Z, "concrete")

    # ---- the six raised planters of the central square (OSM gardens), 0.6 m: step-up
    for aid in ("w595211010", "w595211012", "w595211013", "w595211014", "w595211015", "w595211016"):
        pts = _area_pts(ctx, aid)
        if not pts:
            continue
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        if x0 < 40:
            x0 = max(x0, 32.6)
        else:
            x1 = min(x1, 45.4)
        V.box(x0, y0, 0.0, x1, y1, 0.6, "brick_red", top="grass")
        C.rect(x0, y0, x1, y1, 0.6, "grass")

    # ---- benches at the OSM bench nodes (backless SM64 benches, step-up)
    benches = _points(ctx, lambda t: t.get("amenity") == "bench")
    clip = (-15.0, 116.0, 96.0, 239.0)
    benches = [(i, p) for i, p in benches if clip[0] <= p[0] <= clip[2] and clip[1] <= p[1] <= clip[3]]
    benches.sort(key=lambda ip: ip[0])
    keep = []
    for i, p in benches:  # thin the dense rows: keep benches >= 6 m apart, max 20
        if len(keep) < 20 and all(math.hypot(p[0] - q[0], p[1] - q[1]) >= 6.0 for _, q in keep):
            keep.append((i, p))
    cache = {}
    for _, p in keep:
        _bench(V, C, p[0], p[1], _nearest_dir(ctx, p, cache))

    # ---- Garden Terrace (Library West front): two-step planters with brick seats
    for x0, x1 in GARDEN_PLANTERS:
        V.box(x0, 249.4, 0.0, x1, 250.2, 0.45, "brick_red", top="limestone")
        V.box(x0, 250.2, 0.0, x1, 256.0, 0.75, "brick_red", top="grass")
        C.rect(x0, 249.4, x1, 250.2, 0.45, "limestone")
        C.rect(x0, 250.2, x1, 256.0, 0.75, "grass")
    for x0, x1 in ((21.0, 33.0), (44.0, 56.0), (60.0, 76.0)):  # brick benches under the colonnade
        V.box(x0, 246.2, 0.0, x1, 246.8, 0.45, "brick_red", top="limestone")
        C.rect(x0, 246.2, x1, 246.8, 0.45, "limestone")

    # ---- plaza-edge terrace where the colonnade's eastern section stood (in front of Smathers)
    x0, y0, x1, y1, h = EDGE_TERRACE
    V.box(x0, y0, 0.0, x1, y1, h, "brick_red", top="concrete")
    C.rect(x0, y0, x1, y1, h, "concrete")
    for bx0, bx1 in ((92.0, 100.0), (110.0, 118.0)):
        V.box(bx0, 246.5, h, bx1, 247.1, h + 0.45, "brick_red", top="limestone")
        C.rect(bx0, 246.5, bx1, 247.1, h + 0.45, "limestone")

    # ---- "Focused Attention": bronze gator on a limestone plinth facing the Plaza
    gx, gy = GATOR
    V.box(gx - 1.0, gy - 1.7, 0.0, gx + 1.0, gy + 1.7, 0.7, "limestone", top="limestone")
    C.rect(gx - 1.0, gy - 1.7, gx + 1.0, gy + 1.7, 0.7, "limestone")
    _gator(V, C, gx, gy + 0.1, 0.7, -90.0)  # snout south, toward the Plaza
    # ---- Venetian Renaissance well-head (1965 gift), Smathers garden
    wx, wy = WELL_HEAD
    ring = [(wx + 0.8 * math.cos(math.radians(22.5 + 45 * i)), wy + 0.8 * math.sin(math.radians(22.5 + 45 * i)))
            for i in range(8)]
    for a, b in zip(ring, ring[1:] + ring[:1]):
        V.wall(a, b, 0.0, 1.0, "limestone")
    V.flat(ring, 1.0, "limestone")
    C.box(wx - 0.75, wy - 0.75, 0.0, wx + 0.75, wy + 0.75, 1.0, "limestone", top="limestone")
    log.append("plaza: %d walk ribbons, %d benches" % (drawn, len(keep)))


# ============================================================================ entry point
def build(ctx):
    """-> list of parts (contract in _common.py). Prints a budget report."""
    log = []
    _verify_footprints(ctx, log)
    parts = []
    report = {}

    def emit(slug, M, collision, visual, extra=None):
        me, slots, ntri = M.build()
        d = {"name": M.name, "mesh": me, "material_slots": slots, "collision": collision, "visual": visual,
             "landmark": slug}
        if extra:
            d.update(extra)
        parts.append(d)
        key = "col" if collision else "vis"
        report.setdefault(slug, {"col": 0, "vis": 0})[key] += ntri

    lwV, lwC = _Mesh("library_west.visual"), _Mesh("library_west.collision", visual=False)
    _build_library_west(ctx, lwV, lwC, log)
    coV, coC = _Mesh("library_colonnade.visual"), _Mesh("library_colonnade.collision", visual=False)
    _build_colonnade(ctx, coV, coC, log)
    smV, smC = _Mesh("smathers_library.visual"), _Mesh("smathers_library.collision", visual=False)
    _build_smathers(ctx, smV, smC, log)
    plV, plC = _Mesh("plaza_americas.visual"), _Mesh("plaza_americas.collision", visual=False)
    plP = _Mesh("plaza_americas.walks")
    _build_plaza(ctx, plV, plC, plP, log)

    emit("library_west", lwV, False, True)
    emit("library_west", lwC, True, False)
    emit("library_colonnade", coV, False, True)
    emit("library_colonnade", coC, True, False)
    emit("smathers_library", smV, False, True)
    emit("smathers_library", smC, True, False)
    emit("plaza_of_the_americas", plV, False, True)
    emit("plaza_of_the_americas", plP, False, True, {"decal": True, "z_offset_m": PATH_Z})
    emit("plaza_of_the_americas", plC, True, False)

    budget = {}
    try:
        for lm in ctx["stage"]["landmarks"]:
            budget[lm["name"]] = (lm.get("collision_tris"), lm.get("visual_tris"))
    except Exception:
        pass
    names = {"library_west": "Library West", "smathers_library": "Smathers Library",
             "plaza_of_the_americas": "Plaza of the Americas"}
    print("[%s] triangle report (built / stages.json budget):" % SLUG)
    for slug in ("library_west", "library_colonnade", "smathers_library", "plaza_of_the_americas"):
        r = report.get(slug, {"col": 0, "vis": 0})
        bc, bv = budget.get(names.get(slug, ""), (None, None))
        print("  %-22s collision %4d / %-5s visual %5d / %s" % (slug, r["col"], bc, r["vis"], bv))
    lw, co, pl = report["library_west"], report["library_colonnade"], report["plaza_of_the_americas"]
    print("  library_west + colonnade collision %d / 250;  plaza + colonnade visual %d / 900"
          % (lw["col"] + co["col"], pl["vis"] + co["vis"]))
    for line in log:
        print("  " + line)
    return parts
