"""HUB stage landmarks: The Hub (1950 student center) and Newell Hall (1910, renovated 2017).

Landmark module (contract: tools/campus/landmarks/_common.py). Geometry is in MAP METRES,
z up (x = east, y = north, origin = Century Tower), traced from the OSM footprints in
data/uf/campus.json, so each model sits exactly on the footprint it replaces:

  The Hub w150926632 4,200 m2, 2 storeys, 9.0 m budget 200 collision / 700 visual tris
  Newell Hall w150926630 973 m2, 3.5 storeys + roof budget 150 collision / 600 visual tris

build(ctx) returns, per landmark, one visual mesh (visual=True) and one closed low-poly
collision mesh (collision=True); each dict also carries "landmark": <slug>. UVs are in texture
repeats (the _common.project_uv convention), and windows and doors map one repeat each.

The Hub (Andrew Ferendino of Russell T. Pancoast & Assoc., 1950; renovated 2006-07)
  The NRHP nomination (08000551, Section 7) describes an International-Modern student center,
  "slightly V-shaped, with a wide, curving covered walkway across the main, north facade".
  It has three elements: a two-storey central block, a two-storey pavilion with a curved facade
  at the west end, and a one-storey rounded element at the east end. Other features:
    - flat roof with cast-concrete coping, red brick walls
    - horizontal window bands framed in cast concrete
    - a concrete awning on slender columns that follows the curve
    - a two-storey glass expanse at the main entry
    - on the south (Union Lawn) side, an open stair up to a second-floor balcony
    - service additions on the south-west
  Modelled as:
    - the two-storey block (9.0 m): the OSM outline clipped west, south and east
    - a one-storey ring around it: SW service wing and south balcony strip at 4.6 m, rounded
      east food-court wing at 5.2 m
    - the curving awning (top 3.3 m): it fills the 4 m strip along the north edge of the OSM
      outline and ends in the round knob in front of the east wing
  OSM entrance nodes give the main glass entry (-196.2, -51.9), the east-drum entry and the south
  door.

Newell Hall (William A. Edwards, 1910; RAMSA + SchenkelShultz renovation and addition, 2017)
  NRHP nomination 79000657 (1978), Section 7:
    - collegiate Gothic; brick with terra-cotta sills
    - a "crenellated parapet along roofline"
    - a terra-cotta first-floor belt and an arch over the main entry
    - 6/6 sash windows with transoms; three and a half storeys
    - a "hip roof accented by dormers on the north and south and by pavilions oriented
      north-south on both the east and west ends"
    - an arched entry centred in the east facade, "accented by a gable"
  The 2017 work added:
    - a west addition in running and stack-bond brick that mirrors the original composition
    - a glass connector between old and new
    - a low gabled cafe pavilion that opens onto the courtyard along Stadium Road
    - re-opened north doors
  OSM: building:levels 4, roof:colour red; entrance nodes on the east (main), north, south,
  connector and cafe.
  Modelled as:
    - east and west pavilions: parapet 14.0 m, hip roofs to 17.1 m, ridges N-S
    - central block: parapet 13.4 m, roof to 17.0 m, 2 dormers per side
    - merlons on the parapets; the east entry gable and stoop
    - addition: flat terraces at 12.4 m and a west-facing gable to 16.3 m
    - glass connector at 12.4 m
    - cafe pavilion: eave 4.2 m, ridge 7.2 m, glazed south gable

Traversal (SM64 moves)
  The Hub:
    - stage door (south, Union Lawn): glass double doors under a jump-through entrance canopy
      (3.6 m: double jump onto it, then hop onto the 4.6 m balcony deck); above it a raised entry
      bay (11.5 m) with the THE HUB name sign, the one bump in the flat silhouette (generator
      round 3: a readability addition, not a documented feature of the real building)
    - double-jump through the jump-through awning to stand on it (3.3 m)
    - hop to the east wing roof (5.2 m)
    - wall-kick or back-flip to the two-storey roof (9.0 m), which has rooftop units
    - or walk up the south stair to the balcony (4.6 m)
  Newell Hall:
    - the 3.6 m slots on either side of the glass connector are wall-kick chimneys up to the
      connector roof (12.4 m)
    - from there, single jumps reach the addition terraces and the pavilion parapets (14.0 m)
    - the cafe roof is reachable from the courtyard
  Collision is closed and low-poly. Thin awning posts, merlons and window/door frames are
  visual only.

Sources (reviewed)
  - NRHP registration form, The Hub (08000551), Sections 7-8 and floor plans:
https://npgallery.nps.gov/GetAsset/12600128-589f-4e72-af64-c41116a7bc9e
  - NRHP inventory form, Newell Hall (79000657), Section 7:
    https://npgallery.nps.gov/GetAsset/675bf049-7a6c-40ff-8293-14ea747148f9
  - Wikipedia: The Hub (Gainesville, Florida); Newell Hall (Gainesville, Florida)
  - SchenkelShultz project page: https://schenkelshultz.com/work/uf-newell-hall/
  - Spaces4Learning 2018-02:
    https://spaces4learning.com/articles/2018/02/01/university-of-florida.aspx
  - UF Archives building data (GSF, dates): https://www.uflib.ufl.edu/ufarch/bldgdata2.htm
  - OpenStreetMap ways 150926632 / 150926630 and their entrance nodes (data/uf/tiles/t6.osm)
"""
import math

try:  # the generator imports this module as part of the `landmarks` package
    from . import _common as _C
except Exception:  # pragma: no cover - standalone import
    _C = None

HUB_ID = "w150926632"
NEWELL_ID = "w150926630"

_PALETTE_NAMES = (
    "brick_red", "brick_dark", "limestone", "roof_tile_red", "roof_dark", "copper_green",
    "window_dark", "window_glass", "door_wood", "concrete", "metal_gray", "plaza_brick", "grass",
    "path", "water", "dark_trim", "white_trim", "rock", "bronze", "sign_the_hub",
)
_DEFAULT_TILE = {"window_glass": 3.0, "grass": 4.0, "path": 3.0, "water": 6.0, "rock": 3.0}
COLLISION_MAX_EDGE = 30.0   # longest collision floor edge (m); larger roof triangles are split

# ============================================================================ Newell Hall data
# Footprint parts snapped to the OSM way (all within 0.07 m; the building is axis-aligned).
N_PE = (-163.27, 20.54, -154.68, 40.17)      # east pavilion (1910)        x0, y0, x1, y1
N_C = (-179.30, 21.81, -163.27, 38.66)       # central block (1910)
N_PW = (-188.28, 20.46, -179.30, 40.09)      # west pavilion (1910)
N_K = (-191.90, 26.90, -188.28, 36.33)       # glass connector (2017)
N_CAFE = (-200.60, 12.07, -191.90, 20.60)    # cafe pavilion (2017)
N_ADD = [(-204.52, 20.60), (-191.90, 20.60), (-191.90, 39.86), (-200.14, 39.86),
         (-200.14, 36.22), (-206.38, 36.22), (-206.38, 24.28), (-204.52, 24.28)]  # addition, CCW
N_ADD_CORE = (-206.38, 24.28, -191.90, 36.22)  # gabled core of the addition (ridge E-W)
N_ADD_N = (-200.14, 36.22, -191.90, 39.86)     # flat roof terraces of the addition
N_ADD_S = (-204.52, 20.60, -191.90, 24.28)

N_PAR_P = 14.0        # pavilion parapet top
N_PAR_C = 13.4        # central block parapet top
N_PITCH = math.tan(math.radians(35.0))
N_RIDGE_C = 17.0
N_ADD_H = 12.4        # addition / connector roof
N_ADD_RIDGE = 16.3
N_CAFE_EAVE = 4.2
N_CAFE_RIDGE = 7.2
N_STOOP_H = 1.2       # raised-basement entry on the east facade
N_MAIN_DOOR_Y = 30.25  # OSM entrance=main node on the east facade
N_DOOR_X = -171.25     # OSM north/south entrance nodes of the central block
N_FLOORS = ((2.3, 4.6), (5.9, 8.2), (9.5, 11.8))   # window sill/head per storey (raised basement)

# ============================================================================ The Hub data
H_TOP = 9.0           # 2-storey block, top of the cast-concrete coping
H_LOW = 4.6           # 1-storey service wing / south balcony deck
H_EAST = 5.2          # rounded east food-court wing
H_CANOPY = (3.0, 3.3)  # awning underside / top
H_CANOPY_W = 4.0      # awning depth inside the OSM outline
H_BALCONY_W = 5.0     # south balcony depth (2nd storey set back)
H_MAIN_DOOR = (-196.15, -51.87)   # OSM entrance=main (two-storey glass entry)
H_SOUTH_DOOR = (-194.85, -84.65)  # OSM entrance (Union Lawn side, toward the Reitz Union)
H_EAST_DOOR = (-170.32, -44.96)   # OSM entrance=main of the east food-court drum


def _door(name, pos, facing, note, primary=False):
    d = {"name": name, "pos_m": tuple(round(c, 2) for c in pos), "facing_deg": round(facing % 360.0, 1),
         "note": note}
    if primary:
        d["primary"] = True
    return d


# Door markers: pos_m is on the outer wall plane at the door sill; facing_deg is the compass
# direction a player walking OUT of the door looks (0 = north, 90 = east). The Hub values come
# from _hub_door_markers() (the facade is offset from the OSM outline); tests check they match.
LANDMARKS = [
    {
        "slug": "the_hub",
        "name": "The Hub",
        "osm_ids": [HUB_ID],
        "center_m": (-218.7, -72.4),
        "doors": [
            _door("DOOR_the_hub_0", (-194.85, -84.65, 0.0), 144.1,
                  "south entrance on the Union Lawn side (OSM entrance node), the side that faces "
                  "the Reitz Union: suggested door to the Reitz + Engineering stage", primary=True),
            _door("DOOR_the_hub_1", (-194.05, -55.09, 0.0), 326.9,
                  "main two-storey glass entry under the curving north awning (OSM entrance=main)"),
            _door("DOOR_the_hub_2", (-170.32, -44.96, 0.0), 42.9,
                  "food-court entry in the rounded east wing (OSM entrance=main)"),
        ],
    },
    {
        "slug": "newell_hall",
        "name": "Newell Hall",
        "osm_ids": [NEWELL_ID],
        "center_m": (-181.0, 29.1),
        "doors": [
            _door("DOOR_newell_hall_0", (-206.38, 30.25, 0.0), 270.0,
                  "west gable door of the 2017 addition (mirrors the east entry): suggested stage "
                  "door, west side toward the stadium (stages.json); no real door here", primary=True),
            _door("DOOR_newell_hall_1", (-154.68, N_MAIN_DOOR_Y, N_STOOP_H), 90.0,
                  "historic arched main entry in the east facade, top of the stoop (OSM entrance=main)"),
            _door("DOOR_newell_hall_2", (-190.08, 26.90, 0.0), 180.0,
                  "student entry in the glass connector, inside the south wall-kick slot (OSM entrance)"),
        ],
    },
]


# ============================================================================ 2D geometry helpers
def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def _mul(a, s):
    return (a[0] * s, a[1] * s)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def _cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def _length(a):
    return math.hypot(a[0], a[1])


def _unit(a):
    L = _length(a) or 1.0
    return (a[0] / L, a[1] / L)


def _right(u):
    """Right-hand normal of a direction (= outward normal of a CCW footprint edge)."""
    return (u[1], -u[0])


def _lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def _signed_area(poly):
    s = 0.0
    for i in range(len(poly)):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % len(poly)]
        s += x0 * y1 - x1 * y0
    return s / 2.0


def _ccw(poly):
    return list(poly) if _signed_area(poly) >= 0 else list(reversed(poly))


def _rect(r):
    x0, y0, x1, y1 = r
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _centroid(poly):
    a = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        c = x1 * y2 - x2 * y1
        a += c
        cx += (x1 + x2) * c
        cy += (y1 + y2) * c
    return (cx / (3 * a), cy / (3 * a)) if abs(a) > 1e-9 else poly[0]


def _seg_dist(p, a, b):
    ab = _sub(b, a)
    L2 = _dot(ab, ab)
    if L2 < 1e-12:
        return _length(_sub(p, a))
    t = max(0.0, min(1.0, _dot(_sub(p, a), ab) / L2))
    return _length(_sub(p, _lerp(a, b, t)))


def _closest_on_chain(p, chain, closed=False):
    """(distance, point, segment index) of the closest point of a polyline to p."""
    best = None
    n = len(chain)
    for k in range(n if closed else n - 1):
        a, b = chain[k], chain[(k + 1) % n]
        ab = _sub(b, a)
        L2 = _dot(ab, ab) or 1e-12
        t = max(0.0, min(1.0, _dot(_sub(p, a), ab) / L2))
        q = _lerp(a, b, t)
        d = _length(_sub(p, q))
        if best is None or d < best[0]:
            best = (d, q, k)
    return best


def _bearing(v):
    """Compass bearing (0 = north/+y, 90 = east/+x) of a 2D direction."""
    return math.degrees(math.atan2(v[0], v[1])) % 360.0


def _dp(pts, tol):
    """Douglas-Peucker on an open polyline (keeps both ends)."""
    if len(pts) < 3:
        return list(pts)
    a, b = pts[0], pts[-1]
    dmax, imax = -1.0, 0
    for i in range(1, len(pts) - 1):
        d = _seg_dist(pts[i], a, b)
        if d > dmax:
            dmax, imax = d, i
    if dmax > tol:
        return _dp(pts[:imax + 1], tol)[:-1] + _dp(pts[imax:], tol)
    return [a, b]


def _dp_protected(chain, tol, keep):
    """Douglas-Peucker on an open chain, never removing indices in `keep` (and the ends)."""
    cut = sorted(set([0, len(chain) - 1] + [i for i in keep if 0 < i < len(chain) - 1]))
    out = []
    for i0, i1 in zip(cut, cut[1:]):
        out.extend(_dp(chain[i0:i1 + 1], tol)[:-1])
    out.append(chain[-1])
    return out


def _clean(poly, eps=0.02):
    """Drop duplicate points, spikes and collinear points (closed polygon)."""
    pts = [tuple(p) for p in poly]
    changed = True
    while changed and len(pts) >= 3:
        changed = False
        out = []
        for p in pts:
            if not out or _length(_sub(p, out[-1])) > eps:
                out.append(p)
        if len(out) > 1 and _length(_sub(out[0], out[-1])) <= eps:
            out.pop()
        pts = out
        n = len(pts)
        for i in range(n):
            a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
            ab, bc = _sub(b, a), _sub(c, b)
            lab, lbc = _length(ab), _length(bc)
            if lab < eps or lbc < eps or abs(_cross(ab, bc)) / max(lab, lbc) < eps * 0.5:
                pts.pop(i)
                changed = True
                break
    return pts


def _clean_chain(pts, min_seg=0.3):
    """Open chain: drop points that make the chain double back or that are closer than min_seg."""
    out = [pts[0]]
    for p in pts[1:]:
        if _length(_sub(p, out[-1])) < min_seg:
            continue
        while len(out) >= 2 and _dot(_sub(p, out[-1]), _sub(out[-1], out[-2])) < 0:
            out.pop()
        out.append(p)
    return out


def _halfplane(p0, p1, keep_pt):
    """Half-plane bounded by the line p0-p1, on the side of keep_pt: (origin, unit normal)."""
    d = _sub(p1, p0)
    n = (-d[1], d[0])
    if _dot(_sub(keep_pt, p0), n) < 0:
        n = (-n[0], -n[1])
    return (p0, _unit(n))


def _flip(hp):
    return (hp[0], (-hp[1][0], -hp[1][1]))


def _clip(poly, hps):
    """Sutherland-Hodgman clip of a simple polygon by half-planes [(origin, normal)] -> CCW."""
    out = list(poly)
    for p0, n in hps:
        src, out = out, []
        if not src:
            break
        for i in range(len(src)):
            a, b = src[i], src[(i + 1) % len(src)]
            da, db = _dot(_sub(a, p0), n), _dot(_sub(b, p0), n)
            if da >= -1e-9:
                out.append(a)
            if (da >= -1e-9) != (db >= -1e-9):
                out.append(_lerp(a, b, da / (da - db)))
        out = _clean(out)
    return _ccw(out) if len(out) >= 3 else []


def _point_in_poly(p, poly):
    x, y = p
    inside = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if (y0 > y) != (y1 > y):
            if x0 + (y - y0) * (x1 - x0) / (y1 - y0) > x:
                inside = not inside
    return inside


def _offset_polyline(pts, d):
    """Offset an open polyline by d to its LEFT (negative d = right), mitred joints."""
    out = []
    n = len(pts)
    for i in range(n):
        if i == 0 or i == n - 1:
            e = _unit(_sub(pts[1], pts[0])) if i == 0 else _unit(_sub(pts[i], pts[i - 1]))
            m, c = (-e[1], e[0]), 1.0
        else:
            e0 = _unit(_sub(pts[i], pts[i - 1]))
            e1 = _unit(_sub(pts[i + 1], pts[i]))
            n0, n1 = (-e0[1], e0[0]), (-e1[1], e1[0])
            m = _unit(_add(n0, n1))
            c = max(_dot(m, n0), 0.5)
        out.append(_add(pts[i], _mul(m, d / c)))
    return out


def _polyline_length(pts):
    return sum(_length(_sub(b, a)) for a, b in zip(pts, pts[1:]))


def _point_along(pts, s):
    """(point, unit direction) at arc length s along an open polyline."""
    for k in range(len(pts) - 1):
        a, b = pts[k], pts[k + 1]
        L = _length(_sub(b, a))
        if s <= L or k == len(pts) - 2:
            t = min(max(s / L, 0.0), 1.0) if L > 0 else 0.0
            return _lerp(a, b, t), _unit(_sub(b, a))
        s -= L
    return pts[-1], _unit(_sub(pts[-1], pts[-2]))


def _tri_quality(a, b, c):
    area2 = abs(_cross(_sub(b, a), _sub(c, a)))
    s = _dot(_sub(b, a), _sub(b, a)) + _dot(_sub(c, b), _sub(c, b)) + _dot(_sub(a, c), _sub(a, c))
    return area2 / s if s > 0 else 0.0


def _triangulate(poly):
    """Ear clipping (best-shaped ear first) of a simple CCW polygon -> CCW index triples."""
    pts = list(poly)
    idx = list(range(len(pts)))
    tris = []

    def strictly_inside(p, a, b, c):
        return (_cross(_sub(b, a), _sub(p, a)) > 1e-9 and _cross(_sub(c, b), _sub(p, b)) > 1e-9
                and _cross(_sub(a, c), _sub(p, c)) > 1e-9)

    guard = 0
    while len(idx) > 3 and guard < 10000:
        guard += 1
        m = len(idx)
        best, bestq = None, -1.0
        for k in range(m):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % m]
            a, b, c = pts[i0], pts[i1], pts[i2]
            if _cross(_sub(b, a), _sub(c, b)) <= 1e-9:
                continue
            if any(strictly_inside(pts[j], a, b, c) for j in idx if j not in (i0, i1, i2)):
                continue
            q = _tri_quality(a, b, c)
            if q > bestq:
                best, bestq = k, q
        if best is None:  # only degenerate (collinear) corners left: drop one
            for k in range(m):
                i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % m]
                if abs(_cross(_sub(pts[i1], pts[i0]), _sub(pts[i2], pts[i1]))) <= 1e-6:
                    idx.pop(k)
                    break
            else:
                best = 0
            if best is None:
                continue
        m = len(idx)
        tris.append((idx[best - 1], idx[best], idx[(best + 1) % m]))
        idx.pop(best)
    if len(idx) == 3:
        a, b, c = (pts[i] for i in idx)
        if _cross(_sub(b, a), _sub(c, b)) > 1e-9:
            tris.append(tuple(idx))
    return tris


def _refine(verts, tris, max_len):
    """Conforming longest-edge bisection until every edge <= max_len (no T-junctions)."""
    verts = list(verts)
    tris = [tuple(t) for t in tris]
    for _ in range(400):
        best, bl = None, max_len
        for t in tris:
            for k in range(3):
                i, j = t[k], t[(k + 1) % 3]
                L = _length(_sub(verts[j], verts[i]))
                if L > bl + 1e-9:
                    best, bl = (i, j), L
        if best is None:
            break
        i, j = best
        verts.append(_lerp(verts[i], verts[j], 0.5))
        mi = len(verts) - 1
        new = []
        for t in tris:
            if i in t and j in t:
                while not ((t[0] == i and t[1] == j) or (t[0] == j and t[1] == i)):
                    t = (t[1], t[2], t[0])
                new.append((t[0], mi, t[2]))
                new.append((mi, t[1], t[2]))
            else:
                new.append(t)
        tris = new
    return verts, tris


# ============================================================================ mesh builder
def _newell(pts3):
    nx = ny = nz = 0.0
    for (x1, y1, z1), (x2, y2, z2) in zip(pts3, pts3[1:] + pts3[:1]):
        nx += (y1 - y2) * (z1 + z2)
        ny += (z1 - z2) * (x1 + x2)
        nz += (x1 - x2) * (y1 + y2)
    return (nx, ny, nz)


def _project_uv(pts3, tile_m):
    """Same convention as _common.project_uv: floors top-down, walls along the wall; repeats."""
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


class _MB:
    """Polygons with palette names -> one welded bpy mesh (UVs in texture repeats)."""

    def __init__(self, tiles):
        self.tiles = tiles
        self.polys = []  # (pts3, material, uvs or None)

    def poly(self, pts3, mat, uvs=None, want=None):
        """Add a planar convex polygon (n-gons are fanned). want = optional 3D direction the
        face normal must point along (the polygon is flipped if needed)."""
        if mat not in _PALETTE_NAMES:
            raise ValueError("unknown palette material %r" % (mat,))
        pts3 = [(float(p[0]), float(p[1]), float(p[2])) for p in pts3]
        if len(pts3) < 3:
            return
        n = _newell(pts3)
        if math.sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2]) < 1e-5:
            return  # degenerate
        if want is not None and n[0] * want[0] + n[1] * want[1] + n[2] * want[2] < 0:
            pts3.reverse()
            if uvs is not None:
                uvs = list(reversed(uvs))
        if len(pts3) > 4:
            for k in range(1, len(pts3) - 1):
                self.poly([pts3[0], pts3[k], pts3[k + 1]], mat,
                          None if uvs is None else [uvs[0], uvs[k], uvs[k + 1]])
            return
        self.polys.append((pts3, mat, uvs))

    def tri_count(self):
        return sum(len(p[0]) - 2 for p in self.polys)

    def build(self, name):
        import bpy
        slots, verts, vindex, faces, fmats, fuvs = [], [], {}, [], [], []
        for pts3, m, uvs in self.polys:
            idx = []
            for p in pts3:
                key = (round(p[0], 4), round(p[1], 4), round(p[2], 4))
                if key not in vindex:
                    vindex[key] = len(verts)
                    verts.append(p)
                idx.append(vindex[key])
            if len(set(idx)) < len(idx):
                continue
            if m not in slots:
                slots.append(m)
            faces.append(idx)
            fmats.append(slots.index(m))
            fuvs.append(uvs if uvs is not None else _project_uv(pts3, self.tiles.get(m, 2.0)))
        me = bpy.data.meshes.new(name)
        me.from_pydata(verts, [], faces)
        uv = me.uv_layers.new(name="UVMap")
        for poly, mi, uvs in zip(me.polygons, fmats, fuvs):
            poly.material_index = mi
            poly.use_smooth = False
            for li, (u, v) in zip(poly.loop_indices, uvs):
                uv.data[li].uv = (u, v)
        me.update()
        return me, slots


# ---------------------------------------------------------------------------- shape helpers
def _wall(mb, a, b, z0, z1, mat):
    """Vertical quad a->b (outward normal on the right of a->b, as for a CCW footprint)."""
    if z1 - z0 < 1e-4 or _length(_sub(b, a)) < 1e-4:
        return
    mb.poly([(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)], mat)


def _wall_prof(mb, a, b, prof, mat, off=0.04, uvs=None):
    """Polygon drawn on the wall a->b in wall coordinates (s along a->b, z), pushed `off` metres
    outward (decals: windows, doors). It always faces outward (right of a->b)."""
    u = _unit(_sub(b, a))
    n = _right(u)
    pts = [(a[0] + u[0] * s + n[0] * off, a[1] + u[1] * s + n[1] * off, z) for s, z in prof]
    mb.poly(pts, mat, uvs, want=(n[0], n[1], 0.0))


def _decal(mb, a, b, s0, s1, z0, z1, mat, off=0.04, reps=(1.0, 1.0)):
    _wall_prof(mb, a, b, [(s0, z0), (s1, z0), (s1, z1), (s0, z1)], mat, off,
               uvs=[(0.0, 0.0), (reps[0], 0.0), (reps[0], reps[1]), (0.0, reps[1])])


def _arch_door(mb, a, b, sc, w, z0, zs, zp, mat, frame=None, fw=0.35, off=0.04):
    """Pointed-arch door (pentagon) centred at s = sc on wall a->b, optional frame ring."""
    h = w / 2.0
    inner = [(sc - h, z0), (sc + h, z0), (sc + h, zs), (sc, zp), (sc - h, zs)]
    _wall_prof(mb, a, b, inner, mat, off, uvs=[(0, 0), (1, 0), (1, 0.85), (0.5, 1), (0, 0.85)])
    if frame:
        H = h + fw
        outer = [(sc - H, z0), (sc + H, z0), (sc + H, zs + fw * 0.4), (sc, zp + fw), (sc - H, zs + fw * 0.4)]
        for k in (1, 2, 3, 4):  # right jamb, right arch, left arch, left jamb (open at the sill)
            k2 = (k + 1) % 5
            _wall_prof(mb, a, b, [inner[k], outer[k], outer[k2], inner[k2]], frame, off)


def _cap(mb, poly, z, mat, up=True, max_edge=None):
    """Horizontal polygon (CCW footprint) at height z, facing up (or down)."""
    tris = _triangulate(poly)
    verts = list(poly)
    if max_edge:
        verts, tris = _refine(verts, tris, max_edge)
    for t in tris:
        pts = [(verts[i][0], verts[i][1], z) for i in t]
        mb.poly(pts if up else list(reversed(pts)), mat)


def _box(mb, x0, y0, z0, x1, y1, z1, mat, faces="nsewt", top=None):
    f = {
        "s": [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)],
        "n": [(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)],
        "e": [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)],
        "w": [(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)],
        "t": [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
        "b": [(x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0)],
    }
    for k in faces:
        mb.poly(f[k], (top or mat) if k == "t" else mat)


def _hip_roof(mb, rect, ze, tan_p, mat):
    """Hip roof on an axis-aligned rectangle, ridge along the long side."""
    x0, y0, x1, y1 = rect
    W, D = x1 - x0, y1 - y0
    if D >= W:  # ridge N-S
        h = W / 2.0
        zr = ze + h * tan_p
        xc = (x0 + x1) / 2.0
        mb.poly([(x1, y0, ze), (x1, y1, ze), (xc, y1 - h, zr), (xc, y0 + h, zr)], mat)
        mb.poly([(x0, y1, ze), (x0, y0, ze), (xc, y0 + h, zr), (xc, y1 - h, zr)], mat)
        mb.poly([(x0, y0, ze), (x1, y0, ze), (xc, y0 + h, zr)], mat)
        mb.poly([(x1, y1, ze), (x0, y1, ze), (xc, y1 - h, zr)], mat)
    else:  # ridge E-W
        h = D / 2.0
        zr = ze + h * tan_p
        yc = (y0 + y1) / 2.0
        mb.poly([(x0, y0, ze), (x1, y0, ze), (x1 - h, yc, zr), (x0 + h, yc, zr)], mat)
        mb.poly([(x1, y1, ze), (x0, y1, ze), (x0 + h, yc, zr), (x1 - h, yc, zr)], mat)
        mb.poly([(x1, y0, ze), (x1, y1, ze), (x1 - h, yc, zr)], mat)
        mb.poly([(x0, y1, ze), (x0, y0, ze), (x0 + h, yc, zr)], mat)
    return zr


def _gable_roof(mb, rect, ze, zr, axis, mat, end0=None, end1=None):
    """Gable roof; axis 'x' = ridge E-W (gable ends west=end0 / east=end1),
    axis 'y' = ridge N-S (gable ends south=end0 / north=end1). end* = wall material or None."""
    x0, y0, x1, y1 = rect
    if axis == "x":
        yc = (y0 + y1) / 2.0
        mb.poly([(x0, y0, ze), (x1, y0, ze), (x1, yc, zr), (x0, yc, zr)], mat)
        mb.poly([(x1, y1, ze), (x0, y1, ze), (x0, yc, zr), (x1, yc, zr)], mat)
        if end0:
            mb.poly([(x0, y1, ze), (x0, y0, ze), (x0, yc, zr)], end0)
        if end1:
            mb.poly([(x1, y0, ze), (x1, y1, ze), (x1, yc, zr)], end1)
    else:
        xc = (x0 + x1) / 2.0
        mb.poly([(x1, y0, ze), (x1, y1, ze), (xc, y1, zr), (xc, y0, zr)], mat)
        mb.poly([(x0, y1, ze), (x0, y0, ze), (xc, y0, zr), (xc, y1, zr)], mat)
        if end0:
            mb.poly([(x0, y0, ze), (x1, y0, ze), (xc, y0, zr)], end0)
        if end1:
            mb.poly([(x1, y1, ze), (x0, y1, ze), (xc, y1, zr)], end1)


# ---------------------------------------------------------------------------- massing parts
class _Part:
    def __init__(self, name, poly, top, bands, z0=0.0):
        self.name = name
        self.poly = _ccw(poly)
        self.top = top          # wall top (eave / coping), absolute z
        self.bands = bands      # callable(a, b, edge_len) -> [(z_top_rel, material), ...]
        self.z0 = z0            # ground z


def _wall_spans(parts, i):
    """Exposed wall spans of parts[i]: [(a, b, z_bottom, edge_index)]. An edge that touches a
    neighbouring part only shows above that part's wall top (hidden walls are culled)."""
    part = parts[i]
    poly = part.poly
    n = len(poly)
    spans = []
    for k in range(n):
        a, b = poly[k], poly[(k + 1) % n]
        e = _sub(b, a)
        L = _length(e)
        if L < 1e-3:
            continue
        u = (e[0] / L, e[1] / L)
        ts = {0.0, 1.0}
        for j, q in enumerate(parts):
            if j == i:
                continue
            for p in q.poly:
                w = _sub(p, a)
                t = _dot(w, u) / L
                if abs(_cross(u, w)) < 0.03 and 1e-4 < t < 1 - 1e-4:
                    ts.add(t)
        ts = sorted(ts)
        nout = _right(u)
        for t0, t1 in zip(ts, ts[1:]):
            if (t1 - t0) * L < 0.02:
                continue
            probe = _add(_lerp(a, b, (t0 + t1) / 2.0), _mul(nout, 0.12))
            bottom = part.z0
            for j, q in enumerate(parts):
                if j != i and _point_in_poly(probe, q.poly):
                    bottom = max(bottom, q.top)
            if bottom < part.top - 1e-3:
                spans.append((_lerp(a, b, t0), _lerp(a, b, t1), bottom, k))
    return spans


def _band_walls(mb, a, b, zb, zt, bands, base):
    """Wall from zb to zt split into material bands [(z_top_rel, mat)] (equal ones merged)."""
    out = []
    z = base
    for ztop, mat in bands:
        z0, z1 = max(z, zb), min(base + ztop, zt)
        if z1 - z0 > 1e-3:
            if out and out[-1][2] == mat and abs(out[-1][1] - z0) < 1e-6:
                out[-1] = (out[-1][0], z1, mat)
            else:
                out.append((z0, z1, mat))
        z = base + ztop
    if out and out[-1][1] < zt - 1e-3:  # bands shorter than the wall: stretch the last one
        out[-1] = (out[-1][0], zt, out[-1][2])
    for z0, z1, mat in out:
        _wall(mb, a, b, z0, z1, mat)


def _main_mat(bands):
    """Collision material of a banded wall: its brick if it has any, else the tallest band."""
    mats = [m for _, m in bands]
    for m in ("brick_red", "brick_dark"):
        if m in mats:
            return m
    best, prev, bh = bands[0][1], 0.0, -1.0
    for ztop, mat in bands:
        if ztop - prev > bh:
            best, bh = mat, ztop - prev
        prev = ztop
    return best


def _emit_walls(vis, col, parts, col_max=40.0):
    """Banded visual walls + collision walls (one quad per span; a wall touches the same
    collision cells however it is split, so only extreme lengths are split)."""
    for i, p in enumerate(parts):
        for a, b, zb, k in _wall_spans(parts, i):
            ea, eb = p.poly[k], p.poly[(k + 1) % len(p.poly)]
            bands = p.bands(ea, eb, _length(_sub(eb, ea)))
            _band_walls(vis, a, b, zb, p.top, bands, p.z0)
            L = _length(_sub(b, a))
            nseg = max(1, int(math.ceil(L / col_max - 1e-9)))
            for s in range(nseg):
                _wall(col, _lerp(a, b, s / nseg), _lerp(a, b, (s + 1) / nseg), zb, p.top, _main_mat(bands))


# ============================================================================ The Hub
def _hub_parts(pts):
    """Massing of The Hub from the raw OSM ring (campus.json order: clockwise, 88 points)."""
    P = [tuple(p) for p in pts]
    if len(P) != 88:
        raise ValueError("The Hub footprint changed in campus.json (expected 88 points, got %d)" % len(P))
    # facade line = the walkway's outer edge (pts 3..28, smoothed) pushed H_CANOPY_W inward
    edge = _dp(P[3:29], 0.5)
    inner = _clean_chain(_offset_polyline(edge, -H_CANOPY_W)[1:])  # building is on the right
    facade = [P[3]] + inner + [P[42]]
    e1 = facade[-2]                                           # east end of the 2-storey block
    # rest of the outline: drum (42-55), south-east additions, south facade, SW service wing
    keep = [i - 42 for i in (55, 68, 69, 77, 82, 83, 84, 85)]
    rest = _dp_protected(P[42:86], 0.5, keep)
    base = _clean(_ccw([P[0]] + facade + rest[1:]))          # drops the 0.7 m jogs at 1-2 / 86-87
    outer = _dp(P[3:42], 0.3)                                 # awning edge + round knob
    canopy = _clean(_ccw(outer + [P[42]] + list(reversed(facade[1:-1]))))

    inside = (-220.0, -70.0)
    hw = _halfplane(P[85], P[84], inside)                     # keep = east of the SW wing
    s_dir = _unit(_sub(P[69], P[77]))
    s_in = (-s_dir[1], s_dir[0])
    if _dot(s_in, _sub(inside, P[77])) < 0:
        s_in = (-s_in[0], -s_in[1])
    s0 = _add(P[77], _mul(s_in, H_BALCONY_W))
    hs = _halfplane(s0, _add(s0, s_dir), inside)              # keep = north of the balcony strip
    he = _halfplane(e1, P[68], inside)                        # keep = west of the east wing
    return {
        "up": _clip(base, [hw, hs, he]),
        "south": _clip(base, [hw, _flip(hs), he]),
        "west": _clip(base, [_flip(hw)]),
        "east": _clip(base, [hw, _flip(he)]),
        "base": base, "canopy": canopy, "outer": outer, "facade": facade,
        "drum": [P[k] for k in range(42, 56)], "P": P,
    }


def _hub_door_markers(g):
    """[(name, (x, y), facing_deg)] for the LANDMARKS entry (wall plane points)."""
    out = []
    for name, src, chain_keys in (("DOOR_the_hub_0", H_SOUTH_DOOR, ("south",)),
                                  ("DOOR_the_hub_1", H_MAIN_DOOR, ("up",)),
                                  ("DOOR_the_hub_2", H_EAST_DOOR, ("east",))):
        best = None
        for key in chain_keys:
            poly = g[key]
            d, q, k = _closest_on_chain(src, poly, closed=True)
            if best is None or d < best[0]:
                a, b = poly[k], poly[(k + 1) % len(poly)]
                best = (d, q, _right(_unit(_sub(b, a))))
        out.append((name, best[1], _bearing(best[2])))
    return out


def _hub_build(ctx, tiles):
    g = _hub_parts(_building(ctx, HUB_ID)["pts"])
    gz = float(ctx["ground_z"](-218.7, -72.4)) if ctx.get("ground_z") else 0.0
    vis, col = _MB(tiles), _MB(tiles)
    main_door = _closest_on_chain(H_MAIN_DOOR, g["facade"])[1]
    drum = g["drum"]

    def on_drum(p):
        return _closest_on_chain(p, drum)[0] < 0.6

    def up_bands(a, b, L):
        if _seg_dist(main_door, a, b) < 0.5 and L > 2.0:     # two-storey glass entry
            return [(0.3, "white_trim"), (8.4, "window_glass"), (9.0, "white_trim")]
        if L < 3.5:
            return [(8.6, "brick_red"), (9.0, "white_trim")]
        return [(1.0, "brick_red"), (3.0, "window_glass"), (3.4, "white_trim"), (5.6, "brick_red"),
                (7.2, "window_glass"), (7.6, "white_trim"), (8.6, "brick_red"), (9.0, "white_trim")]

    def south_bands(a, b, L):
        if L < 3.5:
            return [(4.2, "brick_red"), (4.6, "white_trim")]
        return [(1.0, "brick_red"), (3.0, "window_glass"), (3.4, "white_trim"), (4.2, "brick_red"),
                (4.6, "white_trim")]

    def west_bands(a, b, L):  # service wing: plain brick
        return [(4.2, "brick_red"), (4.6, "white_trim")]

    def east_bands(a, b, L):
        if on_drum(a) and on_drum(b):  # rounded food-court storefront
            return [(0.6, "brick_red"), (3.6, "window_glass"), (4.0, "white_trim"), (4.8, "brick_red"),
                    (5.2, "white_trim")]
        if L < 3.5:
            return [(4.8, "brick_red"), (5.2, "white_trim")]
        return [(1.0, "brick_red"), (3.0, "window_glass"), (3.4, "white_trim"), (4.8, "brick_red"),
                (5.2, "white_trim")]

    parts = [
        _Part("up", g["up"], gz + H_TOP, up_bands, gz),
        _Part("south", g["south"], gz + H_LOW, south_bands, gz),
        _Part("west", g["west"], gz + H_LOW, west_bands, gz),
        _Part("east", g["east"], gz + H_EAST, east_bands, gz),
    ]
    _emit_walls(vis, col, parts)
    roof_mat = {"up": "roof_dark", "south": "concrete", "west": "roof_dark", "east": "roof_dark"}
    for p in parts:
        _cap(vis, p.poly, p.top, roof_mat[p.name])
        _cap(col, p.poly, p.top, roof_mat[p.name], max_edge=COLLISION_MAX_EDGE)

    # ---- curving awning on slender posts. Collision: top only = a jump-through platform.
    z0c, z1c = gz + H_CANOPY[0], gz + H_CANOPY[1]
    can = g["canopy"]
    _cap(vis, can, z1c, "concrete")
    _cap(vis, can, z0c, "white_trim", up=False)
    _cap(col, can, z1c, "concrete", max_edge=COLLISION_MAX_EDGE)
    facade_set = set(g["facade"])
    for k in range(len(can)):
        a, b = can[k], can[(k + 1) % len(can)]
        if a in facade_set and b in facade_set:
            continue  # inner edge sits against the building
        _wall(vis, a, b, z0c, z1c, "white_trim")
    walk = g["outer"]
    total = _polyline_length(walk)
    npost = max(2, int(round(total / 10.0)))
    for k in range(npost):
        p, d = _point_along(walk, (k + 0.5) * total / npost)
        c = _add(p, _mul(_right(d), 0.6))  # walkway runs west -> east: building on the right
        r = 0.15
        _box(vis, c[0] - r, c[1] - r, gz, c[0] + r, c[1] + r, z0c, "metal_gray", faces="nsew")

    # ---- open stair up to the south balcony (visual steps over a collision ramp)
    south = parts[1].poly
    P = g["P"]
    d, _, k = _closest_on_chain(_lerp(P[72], P[73], 0.5), south, closed=True)
    _hub_stair(vis, col, south[k], south[(k + 1) % len(south)], gz, H_LOW)

    # ---- rooftop mechanical units on the 2-storey roof (stepping stones; the big one is solid)
    up_poly = parts[0].poly
    ux, uy = _centroid(up_poly)
    for (ox, oy, w, dd, h, solid) in ((-8.0, 3.0, 5.0, 3.5, 1.8, True), (10.0, -3.0, 3.0, 3.0, 1.2, False)):
        x, y = ux + ox, uy + oy
        if all(_point_in_poly(c, up_poly) for c in ((x - w, y - dd), (x + w, y + dd), (x - w, y + dd), (x + w, y - dd))):
            _box(vis, x - w / 2, y - dd / 2, gz + H_TOP, x + w / 2, y + dd / 2, gz + H_TOP + h, "metal_gray")
            if solid:
                _box(col, x - w / 2, y - dd / 2, gz + H_TOP, x + w / 2, y + dd / 2, gz + H_TOP + h, "metal_gray")

    # ---- glass double doors (design doc 3.4: glass buildings get glass doors) so the doors read
    for name, pos, facing in _hub_door_markers(g):
        key = {"DOOR_the_hub_0": "south", "DOOR_the_hub_1": "up", "DOOR_the_hub_2": "east"}[name]
        if name == "DOOR_the_hub_1":
            continue  # the glass entry band already reads as the main entry
        poly = g[key]
        _, q, kk = _closest_on_chain(pos, poly, closed=True)
        a, b = poly[kk], poly[(kk + 1) % len(poly)]
        L = _length(_sub(b, a))
        s = min(max(_dot(_sub(q, a), _unit(_sub(b, a))), 1.6), L - 1.6)
        _glass_doors(vis, a, b, s, gz)
        if name == "DOOR_the_hub_0":
            _hub_stage_entry(vis, col, a, b, s, parts[0].poly, gz)
    return vis, col


def _glass_doors(mb, a, b, s, gz, w=2.6, h=2.8):
    """Aluminium-framed glass double doors on wall a->b centred at s (decals, visual only)."""
    hw = w / 2.0
    _decal(mb, a, b, s - hw - 0.18, s + hw + 0.18, gz, gz + h + 0.18, "metal_gray", off=0.05)
    _decal(mb, a, b, s - hw, s - 0.05, gz + 0.03, gz + h, "window_glass", off=0.07, reps=(0.45, 0.9))
    _decal(mb, a, b, s + 0.05, s + hw, gz + 0.03, gz + h, "window_glass", off=0.07, reps=(0.45, 0.9))
    for s0, s1 in ((s - hw + 0.15, s - 0.2), (s + 0.2, s + hw - 0.15)):   # push bars
        _decal(mb, a, b, s0, s1, gz + 1.0, gz + 1.1, "dark_trim", off=0.09)


def _quad_out(a, u, n, s0, s1, d0, d1, z):
    """Horizontal quad in front of a wall (s along u, d out along n), CCW from above."""
    def P(ss, dd):
        return (a[0] + u[0] * ss + n[0] * dd, a[1] + u[1] * ss + n[1] * dd, z)
    return [P(s0, d0), P(s1, d0), P(s1, d1), P(s0, d1)]


def _hub_stage_entry(vis, col, a, b, s, up_poly, gz):
    """The stage door on the Union Lawn side: a concrete entrance canopy (jump-through, top 3.6 m:
    a double jump lands on it, then hop onto the 4.6 m balcony deck), and above it on the
    two-storey block a raised entry bay (to 11.5 m: the one bump in The Hub's flat silhouette) with
    a glass strip and the white-on-blue THE HUB name sign facing the lawn. The real 2006-07
    renovation signage is not documented in the sources above; the bay and sign are a game
    readability addition so the stage door's building is recognisable from across the lawn."""
    u = _unit(_sub(b, a))
    n = _right(u)
    up = (0.0, 0.0, 1.0)
    # canopy 5.2 m x 2.4 m, 0.35 m thick
    z0, z1 = gz + 3.25, gz + 3.6
    top = _quad_out(a, u, n, s - 2.6, s + 2.6, 0.0, 2.4, z1)
    bot = _quad_out(a, u, n, s - 2.6, s + 2.6, 0.0, 2.4, z0)
    vis.poly(top, "concrete", want=up)
    vis.poly(bot, "white_trim", want=(0.0, 0.0, -1.0))
    for i, j in ((1, 2), (2, 3), (3, 0)):
        vis.poly([bot[i], bot[j], top[j], top[i]], "white_trim",
                 want=((bot[i][0] + bot[j][0]) / 2 - (a[0] + u[0] * s), (bot[i][1] + bot[j][1]) / 2
                       - (a[1] + u[1] * s), 0.0))
    col.poly(top, "concrete", want=up)
    for k in (-1, 1):   # two slim posts at the outer corners
        c = _add(_add(a, _mul(u, s + k * 2.35)), _mul(n, 2.15))
        _box(vis, c[0] - 0.1, c[1] - 0.1, gz, c[0] + 0.1, c[1] + 0.1, z0, "metal_gray", faces="nsew")
    # raised entry bay on the two-storey block's wall behind the balcony
    door_pt = _add(a, _mul(u, s))
    probe = _sub(door_pt, _mul(n, H_BALCONY_W + 0.5))
    _, q, k = _closest_on_chain(probe, up_poly, closed=True)
    a2, b2 = up_poly[k], up_poly[(k + 1) % len(up_poly)]
    u2 = _unit(_sub(b2, a2))
    n2 = _right(u2)
    if _dot(n2, n) < 0.7:      # not the wall facing the lawn: no bay
        return
    L2 = _length(_sub(b2, a2))
    s2 = _dot(_sub(q, a2), u2)
    hw = min(3.5, L2 / 2.0 - 0.5)
    if hw < 2.0:
        return
    s2 = min(max(s2, hw + 0.3), L2 - hw - 0.3)
    zb, zt = gz + H_LOW, gz + 11.5
    out, back = 0.4, 1.6
    f0 = _add(a2, _add(_mul(u2, s2 - hw), _mul(n2, out)))
    f1 = _add(a2, _add(_mul(u2, s2 + hw), _mul(n2, out)))
    r0 = _add(a2, _add(_mul(u2, s2 - hw), _mul(n2, -back)))
    r1 = _add(a2, _add(_mul(u2, s2 + hw), _mul(n2, -back)))
    for mb in (vis, col):
        m = "brick_red"
        _wall(mb, f0, f1, zb, zt, m)                       # front (faces the lawn)
        _wall(mb, f1, r1, zb if mb is vis else zb, zt, m)  # east / west sides
        _wall(mb, r0, f0, zb, zt, m)
        _wall(mb, r1, r0, gz + H_TOP, zt, m)               # back, above the 9 m roof
        mb.poly([(f0[0], f0[1], zt), (f1[0], f1[1], zt), (r1[0], r1[1], zt), (r0[0], r0[1], zt)],
                "white_trim" if mb is vis else "concrete", want=up)
    # coping band, glass strip and the name sign on the bay front (decals)
    _decal(vis, f0, f1, 0.0, 2 * hw, zt - 0.4, zt + 0.02, "white_trim", off=0.03)
    _decal(vis, f0, f1, 0.5, 2 * hw - 0.5, zb + 0.3, zb + 1.9, "window_glass", off=0.04, reps=(2.0, 1.0))
    sw = min(6.0, 2 * hw - 0.6)
    _decal(vis, f0, f1, hw - sw / 2, hw + sw / 2, zb + 2.3, zb + 2.3 + sw / 2, "sign_the_hub", off=0.05)


def _hub_stair(vis, col, a, b, gz, height):
    """Straight stair outside the CCW wall edge a->b, rising from near b toward a, ending at the
    deck height (the deck is the roof behind that wall)."""
    L = _length(_sub(a, b))
    d = _unit(_sub(a, b))                    # climbing direction
    out = _right(_unit(_sub(b, a)))          # away from the building
    steps, width = 8, 2.0
    run = min(8.0, L - 1.0)
    s_foot = max(0.3, L - run - 0.7)

    def P(s, w):
        return _add(_add(b, _mul(d, s_foot + s)), _mul(out, w))

    def v(s, w, z):
        p = P(s, w)
        return (p[0], p[1], z)

    zt = gz + height
    rise, tr = height / steps, run / steps
    up = (0.0, 0.0, 1.0)
    back = (-d[0], -d[1], 0.0)
    fwd = (d[0], d[1], 0.0)
    side = (out[0], out[1], 0.0)
    for k in range(steps):
        z0, z1 = gz + rise * k, gz + rise * (k + 1)
        s0, s1 = tr * k, tr * (k + 1)
        vis.poly([v(s0, 0, z0), v(s0, width, z0), v(s0, width, z1), v(s0, 0, z1)], "concrete", want=back)
        vis.poly([v(s0, 0, z1), v(s0, width, z1), v(s1, width, z1), v(s1, 0, z1)], "concrete", want=up)
    # outer side: the stepped profile (s, z), triangulated, on the plane w = width
    prof = [(0.0, 0.0), (run, 0.0)]
    for k in range(steps, 0, -1):
        prof += [(tr * k, rise * k), (tr * (k - 1), rise * k)]
    prof = _clean(prof)
    for t in _triangulate(_ccw(prof)):
        vis.poly([v(prof[i][0], width, gz + prof[i][1]) for i in t], "white_trim", want=side)
    vis.poly([v(run, 0, gz), v(run, width, gz), v(run, width, zt), v(run, 0, zt)], "white_trim", want=fwd)
    # collision: ramp, outer cheek, top end wall
    col.poly([v(0, 0, gz), v(0, width, gz), v(run, width, zt), v(run, 0, zt)], "concrete", want=up)
    col.poly([v(0, width, gz), v(run, width, gz), v(run, width, zt)], "concrete", want=side)
    col.poly([v(run, 0, gz), v(run, width, gz), v(run, width, zt), v(run, 0, zt)], "concrete", want=fwd)


# ============================================================================ Newell Hall
def _orig_bands(par):
    def f(a, b, L):
        if L < 2.0:
            return [(par - 0.4, "brick_red"), (par, "limestone")]
        return [(1.5, "brick_dark"), (1.8, "limestone"), (par - 0.4, "brick_red"), (par, "limestone")]
    return f


def _newell_build(ctx, tiles):
    gz = float(ctx["ground_z"](-181.0, 29.1)) if ctx.get("ground_z") else 0.0
    vis, col = _MB(tiles), _MB(tiles)

    def add_bands(a, b, L):   # 2017 addition: dark plinth, brick, cast-stone coping
        return [(0.9, "brick_dark"), (N_ADD_H - 0.4, "brick_red"), (N_ADD_H, "limestone")]

    def k_bands(a, b, L):     # glass connector
        return [(N_ADD_H - 0.5, "window_glass"), (N_ADD_H, "metal_gray")]

    def cafe_bands(a, b, L):  # cafe pavilion: storefront glass between brick plinth and eave
        return [(0.5, "brick_dark"), (3.6, "window_glass"), (N_CAFE_EAVE, "brick_red")]

    parts = [
        _Part("pe", _rect(N_PE), gz + N_PAR_P, _orig_bands(N_PAR_P), gz),
        _Part("c", _rect(N_C), gz + N_PAR_C, _orig_bands(N_PAR_C), gz),
        _Part("pw", _rect(N_PW), gz + N_PAR_P, _orig_bands(N_PAR_P), gz),
        _Part("k", _rect(N_K), gz + N_ADD_H, k_bands, gz),
        _Part("add", N_ADD, gz + N_ADD_H, add_bands, gz),
        _Part("cafe", _rect(N_CAFE), gz + N_CAFE_EAVE, cafe_bands, gz),
    ]
    _emit_walls(vis, col, parts)

    # ---- roofs (visual and collision share these simple planes)
    for mb in (vis, col):
        is_vis = mb is vis
        # central block: E-W roof running into both pavilion roofs (cross-gable valleys)
        xa = (N_PW[0] + N_PW[2]) / 2.0
        xb = (N_PE[0] + N_PE[2]) / 2.0
        _gable_roof(mb, (xa, N_C[1], xb, N_C[3]), gz + N_PAR_C, gz + N_RIDGE_C, "x", "roof_tile_red")
        _hip_roof(mb, N_PE, gz + N_PAR_P, N_PITCH, "roof_tile_red")
        _hip_roof(mb, N_PW, gz + N_PAR_P, N_PITCH, "roof_tile_red")
        # addition: gabled core (its west gable end = the new west facade), flat terraces N + S
        _gable_roof(mb, N_ADD_CORE, gz + N_ADD_H, gz + N_ADD_RIDGE, "x", "roof_tile_red",
                    end0="brick_red", end1="brick_red")
        _cap(mb, _rect(N_ADD_N), gz + N_ADD_H, "concrete")
        _cap(mb, _rect(N_ADD_S), gz + N_ADD_H, "concrete")
        _cap(mb, _rect(N_K), gz + N_ADD_H, "metal_gray")
        # cafe pavilion: low gable, ridge N-S, glazed gable end toward the courtyard (south)
        _gable_roof(mb, N_CAFE, gz + N_CAFE_EAVE, gz + N_CAFE_RIDGE, "y", "roof_tile_red",
                    end0="window_glass" if is_vis else "brick_red")
        _newell_dormers(mb, gz, is_vis)

    _newell_merlons(vis, gz)

    # ---- windows (6/6 sash + transom) on the 1910 building, one texture repeat each
    W = 1.3
    x0c, y0c, x1c, y1c = N_C
    pe, pw = N_PE, N_PW
    fl = N_FLOORS
    win = [
        # (wall a, wall b (CCW, outside on the right), s centres, storeys)
        ((x1c, y1c), (x0c, y1c), [2.0, 5.2, 10.8, 14.0], fl),             # central, north
        ((x1c, y1c), (x0c, y1c), [x1c - N_DOOR_X], fl[1:]),               # above the north door
        ((x0c, y0c), (x1c, y0c), [2.0, 5.2, 10.8, 14.0], fl),             # central, south
        ((x0c, y0c), (x1c, y0c), [N_DOOR_X - x0c], fl[1:]),               # above the south door
        ((pe[2], pe[3]), (pe[0], pe[3]), [2.3, 6.3], fl),                  # east pavilion N
        ((pe[0], pe[1]), (pe[2], pe[1]), [2.3, 6.3], fl),                  # east pavilion S
        ((pe[2], pe[1]), (pe[2], pe[3]), [2.4, 5.8, 13.6, 17.2], fl),      # east facade
        ((pe[2], pe[1]), (pe[2], pe[3]), [N_MAIN_DOOR_Y - pe[1]], fl[1:]),  # above the main entry
        ((pw[2], pw[3]), (pw[0], pw[3]), [2.4, 6.6], fl),                  # west pavilion N
        ((pw[0], pw[1]), (pw[2], pw[1]), [2.4, 6.6], fl),                  # west pavilion S
    ]
    for a, b, scs, storeys in win:
        for sc in scs:
            for z0, z1 in storeys:
                _decal(vis, a, b, sc - W / 2, sc + W / 2, gz + z0, gz + z1, "window_dark")

    # ---- east main entry: gable over the pointed-arch door, limestone surround, stoop
    ea, eb = (pe[2], pe[1]), (pe[2], pe[3])
    sc = N_MAIN_DOOR_Y - pe[1]
    _arch_door(vis, ea, eb, sc, 2.2, gz + N_STOOP_H, gz + N_STOOP_H + 2.6, gz + N_STOOP_H + 3.4,
               "door_wood", frame="limestone")
    for mb in (vis, col):  # solid: Mario can stand on its rakes
        _newell_gable(mb, ea, eb, sc, 6.0, gz + N_PAR_P, gz + N_PAR_P + 2.6, 0.6)
    _newell_stoop(vis, col, gz)

    # ---- other doors: re-opened north/south doors, the addition's west door, connector, cafe
    _arch_door(vis, (x1c, y1c), (x0c, y1c), x1c - N_DOOR_X, 2.0, gz, gz + 2.6, gz + 3.3, "door_wood")
    _arch_door(vis, (x0c, y0c), (x1c, y0c), N_DOOR_X - x0c, 2.0, gz, gz + 2.6, gz + 3.3, "door_wood")
    wa, wb = (-206.38, 36.22), (-206.38, 24.28)      # west facade of the addition (walk south)
    wsc = 36.22 - 30.25
    _arch_door(vis, wa, wb, wsc, 2.4, gz, gz + 2.8, gz + 3.7, "door_wood", frame="limestone")
    for s in (wsc - 3.4, wsc + 3.4):                  # tall stair-hall windows flanking it
        _decal(vis, wa, wb, s - 0.8, s + 0.8, gz + 1.4, gz + 10.6, "window_glass", reps=(1.0, 3.0))
    _newell_gable_trim(vis, gz)
    an_a, an_b = (-191.90, 39.86), (-200.14, 39.86)  # addition, north face
    for s in (2.0, 6.2):
        _decal(vis, an_a, an_b, s - 0.8, s + 0.8, gz + 1.4, gz + 10.6, "window_glass", reps=(1.0, 3.0))
    as_a, as_b = (-204.52, 20.60), (-191.90, 20.60)  # addition, south face (cafe below the east part)
    _decal(vis, as_a, as_b, 1.16, 2.76, gz + 1.4, gz + 10.6, "window_glass", reps=(1.0, 3.0))
    for s in (6.6, 10.4):
        _decal(vis, as_a, as_b, s - 0.8, s + 0.8, gz + 5.2, gz + 10.6, "window_glass", reps=(1.0, 2.0))
    k_s = -190.08 - N_K[0]                            # OSM connector entrance node
    _decal(vis, (N_K[0], N_K[1]), (N_K[2], N_K[1]), k_s - 1.0, k_s + 1.0, gz, gz + 2.8, "door_wood", off=0.05)
    c_s = -196.42 - N_CAFE[0]                         # OSM cafe entrance node
    _decal(vis, (N_CAFE[0], N_CAFE[1]), (N_CAFE[2], N_CAFE[1]), c_s - 1.1, c_s + 1.1, gz, gz + 2.8,
           "door_wood", off=0.05)
    return vis, col


def _newell_dormers(mb, gz, visual):
    """Two gabled dormers on each long slope of the central roof (NRHP: dormers N and S)."""
    slope = (N_RIDGE_C - N_PAR_C) / ((N_C[3] - N_C[1]) / 2.0)
    zf_e, zf_r = gz + 15.3, gz + 16.0      # dormer eave / ridge
    front_mat = "limestone" if visual else "brick_red"
    for xc in (-175.3, -167.3):
        x0, x1 = xc - 0.9, xc + 0.9
        for side in (1, -1):              # +1 north slope, -1 south slope
            eave_y = N_C[3] if side == 1 else N_C[1]
            yf = eave_y - side * 1.2      # dormer front plane
            zb = gz + N_PAR_C + 1.2 * slope
            ye = eave_y - side * (zf_e - gz - N_PAR_C) / slope   # dormer eave meets the roof
            yr = eave_y - side * (zf_r - gz - N_PAR_C) / slope   # dormer ridge meets the roof
            out = (0.0, float(side), 0.0)
            mb.poly([(x0, yf, zb), (x1, yf, zb), (x1, yf, zf_e), (x0, yf, zf_e)], front_mat, want=out)
            mb.poly([(x0, yf, zf_e), (x1, yf, zf_e), (xc, yf, zf_r)], front_mat, want=out)
            if visual:
                a, b = ((x1, yf), (x0, yf)) if side == 1 else ((x0, yf), (x1, yf))
                _decal(mb, a, b, 0.4, 1.4, zb + 0.15, zf_e - 0.1, "window_dark", off=0.03)
            for xs, sgn in ((x0, -1.0), (x1, 1.0)):
                mb.poly([(xs, yf, zb), (xs, yf, zf_e), (xs, ye, zf_e)], "roof_tile_red" if visual else "brick_red",
                        want=(sgn, 0.0, 0.0))
                mb.poly([(xs, yf, zf_e), (xc, yf, zf_r), (xc, yr, zf_r), (xs, ye, zf_e)], "roof_tile_red",
                        want=(0.0, 0.0, 1.0))


def _newell_merlons(mb, gz):
    """Crenellated parapet (NRHP): merlons (front, back, top) standing on the parapet coping.
    Visual only; spaced so the gaps show the red roof behind them."""
    mw, mh, mt = 1.1, 0.8, 0.4
    pe, pw, c = N_PE, N_PW, N_C
    par_p, par_c = gz + N_PAR_P, gz + N_PAR_C
    runs = [  # (a, b (outside on the right), z, s centres)
        ((pe[2], pe[1]), (pe[2], pe[3]), par_p, [1.3, 4.0, 15.6, 18.3]),     # east facade
        ((pe[0], pe[1]), (pe[2], pe[1]), par_p, [1.3, 7.3]),                 # east pavilion S
        ((pe[2], pe[3]), (pe[0], pe[3]), par_p, [1.3, 7.3]),                 # east pavilion N
        ((pw[0], pw[1]), (pw[2], pw[1]), par_p, [1.3, 7.7]),                 # west pavilion S
        ((pw[2], pw[3]), (pw[0], pw[3]), par_p, [1.3, 7.7]),                 # west pavilion N
        ((c[0], c[1]), (c[2], c[1]), par_c, [3.6, 8.0, 12.4]),               # central S
        ((c[2], c[3]), (c[0], c[3]), par_c, [3.6, 8.0, 12.4]),               # central N
    ]
    for a, b, z, scs in runs:
        u = _unit(_sub(b, a))
        n = _right(u)
        for s in scs:
            p0, p1 = _add(a, _mul(u, s - mw / 2)), _add(a, _mul(u, s + mw / 2))
            q0, q1 = _add(p0, _mul(n, -mt)), _add(p1, _mul(n, -mt))
            mb.poly([(p0[0], p0[1], z), (p1[0], p1[1], z), (p1[0], p1[1], z + mh), (p0[0], p0[1], z + mh)],
                    "brick_red", want=(n[0], n[1], 0.0))
            mb.poly([(q1[0], q1[1], z), (q0[0], q0[1], z), (q0[0], q0[1], z + mh), (q1[0], q1[1], z + mh)],
                    "brick_red", want=(-n[0], -n[1], 0.0))
            mb.poly([(p0[0], p0[1], z + mh), (p1[0], p1[1], z + mh), (q1[0], q1[1], z + mh),
                     (q0[0], q0[1], z + mh)], "limestone", want=(0.0, 0.0, 1.0))


def _newell_gable(mb, a, b, sc, w, z0, zp, t):
    """Pointed brick gable rising from the parapet over the east entry (front, back, coping)."""
    u = _unit(_sub(b, a))
    n = _right(u)
    h = w / 2.0
    pa, pb, pc = _add(a, _mul(u, sc - h)), _add(a, _mul(u, sc + h)), _add(a, _mul(u, sc))
    ia, ib, ic = (_add(p, _mul(n, -t)) for p in (pa, pb, pc))
    mb.poly([(pa[0], pa[1], z0), (pb[0], pb[1], z0), (pc[0], pc[1], zp)], "brick_red", want=(n[0], n[1], 0.0))
    mb.poly([(ia[0], ia[1], z0), (ib[0], ib[1], z0), (ic[0], ic[1], zp)], "brick_red", want=(-n[0], -n[1], 0.0))
    mb.poly([(pb[0], pb[1], z0), (ib[0], ib[1], z0), (ic[0], ic[1], zp), (pc[0], pc[1], zp)], "limestone",
            want=(0.0, 0.0, 1.0))
    mb.poly([(ia[0], ia[1], z0), (pa[0], pa[1], z0), (pc[0], pc[1], zp), (ic[0], ic[1], zp)], "limestone",
            want=(0.0, 0.0, 1.0))


def _newell_gable_trim(mb, gz):
    """Cast-stone coping band along the rakes of the addition's west gable."""
    x = N_ADD_CORE[0] - 0.04
    y0, y1 = N_ADD_CORE[1], N_ADD_CORE[3]
    yc = (y0 + y1) / 2.0
    ze, zr, t = gz + N_ADD_H, gz + N_ADD_RIDGE, 0.45
    for ya, yb, za, zb in ((y1, yc, ze, zr), (yc, y0, zr, ze)):
        mb.poly([(x, ya, za - t), (x, yb, zb - t), (x, yb, zb), (x, ya, za)], "limestone", want=(-1.0, 0.0, 0.0))


def _newell_stoop(vis, col, gz):
    """Raised-basement entry: landing + two steps in front of the east door; ramp collision."""
    x0 = N_PE[2]
    y0, y1 = N_MAIN_DOOR_Y - 2.0, N_MAIN_DOOR_Y + 2.0
    h = N_STOOP_H
    xs = [x0, x0 + 1.6, x0 + 2.2, x0 + 2.8]
    for k, z in enumerate((h, h * 2 / 3, h / 3)):
        _box(vis, xs[k], y0, gz, xs[k + 1], y1, gz + z, "limestone", faces="nset")
    xl, xr = x0 + 1.0, xs[-1]
    up = (0.0, 0.0, 1.0)
    col.poly([(x0, y0, gz + h), (xl, y0, gz + h), (xl, y1, gz + h), (x0, y1, gz + h)], "limestone", want=up)
    col.poly([(xl, y0, gz + h), (xr, y0, gz), (xr, y1, gz), (xl, y1, gz + h)], "limestone", want=up)
    col.poly([(x0, y0, gz), (xr, y0, gz), (xl, y0, gz + h), (x0, y0, gz + h)], "limestone", want=(0, -1, 0))
    col.poly([(xr, y1, gz), (x0, y1, gz), (x0, y1, gz + h), (xl, y1, gz + h)], "limestone", want=(0, 1, 0))


# ============================================================================ entry point
def _building(ctx, osm_id):
    bs = ctx.get("buildings")
    if bs is not None and osm_id in bs:
        return bs[osm_id]
    for b in ctx["campus"]["buildings"]:
        if b["id"] == osm_id:
            return b
    raise KeyError(osm_id)


def _tiles(ctx):
    pal = ctx.get("palette") or (_C.PALETTE if _C is not None else None) or {}
    tiles = {}
    for name in _PALETTE_NAMES:
        entry = pal.get(name)
        t = entry.get("tile_m") if isinstance(entry, dict) else None
        tiles[name] = float(t) if t else _DEFAULT_TILE.get(name, 2.0)
    return tiles


def build_polys(ctx):
    """Pure-Python part of build(): {slug: (visual builder, collision builder)}."""
    tiles = _tiles(ctx)
    return {"the_hub": _hub_build(ctx, tiles), "newell_hall": _newell_build(ctx, tiles)}


def build(ctx):
    names = {"the_hub": "The Hub", "newell_hall": "Newell Hall"}
    out = []
    for slug, (vis, col) in build_polys(ctx).items():
        for mb, kind in ((vis, "visual"), (col, "collision")):
            name = "%s %s" % (names[slug], kind)
            me, slots = mb.build(name)
            out.append({"name": name, "mesh": me, "material_slots": slots,
                        "collision": kind == "collision", "visual": kind == "visual", "landmark": slug})
    return out
