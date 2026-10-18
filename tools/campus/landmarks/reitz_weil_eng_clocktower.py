"""REITZ UNION + ENGINEERING QUAD stage landmarks: Joseph Weil Hall (the "Engineering Industries
Building"), the Engineering Clock Tower and the Engineering Plaza / Weil courtyard, hand-modelled
for Super Gatorlator 64.

Landmark module (contract: tools/campus/landmarks/_common.py). Every LANDMARKS entry carries
"stages": ["reitz_eng"], so only `build_stage.py reitz_eng` (slot wf) builds it; the Swamp window
also contains Weil Hall but keeps its generic backdrop extrusion. Geometry is in MAP METRES, z up
(x = east, y = north, origin = Century Tower), on the OSM footprints of data/uf/campus.json:

  Weil Hall w445808709 3,484 m2 tower deck 25.6 m budget 300 collision / 1000 visual
  Engineering Clock Tower w481256532 12 m2 apex 8.0 m budget 60 collision / 300 visual
  Engineering Plaza area w857648949 (+ seating w857648945, bike parking w435957942) - no budget
  Built (headless test): Weil 297 collision / 927 visual, clock tower 20 / 210, plaza
  72 / 400; the module total (389 collision) stays under the generator's module check (1.1 x 360).
build(ctx) returns per landmark one visual mesh and one closed low-poly collision mesh (+ flat
"decal" paving parts); each part dict carries "landmark": <slug>. Collision walls face out of the
solids; walkable floors are flat or <= 20 degrees (dormer roofs 18, front steps 19.8), every tiled
roof slope is a slide (54-60 degrees).

WEIL HALL (Guy Fulton, Collegiate Gothic, built in phases 1947-1951; NRHP 08000547, 2008)
  What the sources say (NRHP nomination, sections 7-8; UF building directory; OSM):
    - "four and a half story masonry building" with "a rectangular footprint with a strong east-west
      axis"; red brick in English cross bond; "steeply pitched roof with intersecting gables...
      covered in flat terra cotta tiles"; stone quoins and ornament on the east, north and west
      facades. UF counts 6 levels (158,558 GSF, 473 rooms): the site slopes, so the lower floor is
      half below the entrance and the fifth floor is in the roof (dormers).
    - North (main) elevation: "short, projecting wings at each end, and three flat, gable walls in
      the middle"; "shed-roofed dormers are set in the north roof between the front gables"; stone
      water table, a masonry belt course above the top-floor windows and a parapet coping.
    - "The gable adjacent to the main entrance incorporates a polygonal bay with a parapet of
      checkerboard diagonal bricks and quatrefoil stone panels"; "Steps rise a half level from
      Stadium Road to the main entrance"; "A tower feature... highlight[s] the main entrance. A
      Gothic arch... leads to the recessed set of double wood doors. ENGINEERING INDUSTRIES... is
      set in raised cast stone lettering above the arch." The west-end entrance repeats this detail.
    - "A separate entrance to the lower floor... near the center of the front elevation" under a
      framed Gothic arch; "Three gables project from the south elevation... service area and
      loading bay"; "Later additions to the east end of the building extend to the south, forming
      an L" (the floor plans label a small COURTYARD beside it).
    - The west elevation is set back from Gale Lemerand Drive, "forming a small plaza used to
      display a structural steel sculpture and the workings of an antique clock enclosed in a small
      brick structure"; "oak-shaded plaza on the west side".
    - OSM entrances: main (-458.47, -40.32) with 4 m steps north to Stadium Road, lower-floor door
      (-495.81, -38.06), west door (-559.98, -47.36), east door (-435.32, -49.08), service doors
      south. OSM roof:colour #BA4A00, building:levels 6.
  Modelled as (OSM outline, 38 edges, every vertex within 0.17 m of the OSM way):
    - Main range (M) 19 m deep along Stadium Road, walls 13.6 m (three storeys over the half-sunk
      lower floor) with a 0.7 m stone-coped parapet and a 1 m box gutter behind it; 54-degree
      terra-cotta roof to a flat 1 m ridge at 24.0 m (stages.json 24 m). Its west end is a big
      gable facing the clock-tower plaza, over a two-storey entrance bay with a balcony on top.
    - Projecting north wings: the west wing (WN, 13.2 m) and the entrance wing (PW, 12.9 m) with
      60-degree gables facing Stadium Road; PW carries the polygonal bay (OSM chamfers).
    - Three flush front gables (cross roofs, apex 19.4 m) and four shed dormers between them.
    - The entrance tower (6.1 x 9.2 m) beside PW over the main door: Gothic arch, lettering band,
      stone-coped parapet; deck 25.6 m (1.6 m over the ridge).
    - East range (E) with a hipped east end (ridge 22.4 m); the later south addition (SA, flat
      roofs at 13.6 m and 9.6 m over the auditorium) round the small east COURTYARD; the south
      projections (SP) as a flat 13.6 m service roof.
    - Windows come from the generator's facade textures (facade_gothic: paired lancets with cast
      stone surrounds, 4 m floors from the 1.2 m water table; facade_brick on the later addition).
  Gameplay (SM64 surfaces slide above ~38 degrees):
    - THE ROOF RUN: copper downspouts are climbable poles (markers["poles"], bhvPoleGrabbing) to the
      13.6 m roofs: courtyard -> SA roof -> south box gutter -> a 6-step steel roof-access stair
      (1.73 m risers) -> the flat ridge (24 m, 98 m long, T-junctions to both north wings) -> jump
      1.6 m through the west crenel onto the tower deck (25.6 m, the summit). The east range ridge
      (22.4 m) reaches the deck through the east crenel (3.2 m: double jump).
    - Sliding off any slope lands in a parapet-guarded box gutter (13.6 m), never off the roof;
      the shed dormers (16.6-17.5 m) are perches in the north gutter bays.
    - Ground level: the main stoop (1.8 m) and its walk-in arch, the lower-floor arch niche
      ("server closet" spot), the west entrance bay balcony (9.2 m, its own downspout), the east
      courtyard (Weil's courtyard red coin), and an HVAC box stepping from the 9.6 m to the 13.6 m
      addition roof.
  Not modelled: interiors, the 2018 east addition's glass details, south-elevation gables (flat
  service roof instead), the stair tower to Reed Lab (part of the addition roof), lettering text
  (no sign texture: stone band with a dark strip).

ENGINEERING CLOCK TOWER (Tau Beta Pi / College of Engineering; faces completed Oct 2025)
  Sources: OSM w481256532 (height 8 m, brick, clock tower, 3.4 x 3.4 m); UF News 2025-11 (four
  faces: Gator Chomp north, Log10 south, Wandering Dial east, Binary west; "stands in the courtyard
  in front of Weil Hall"); uftbp.com clock tower page (Wandering Hour Dial faces Weil Hall); the
  MAE article photo (glass-walled ground stage with brick corner piers and a glass door, brick
  shaft with louvred vents, round faces in brick rings, cross-gabled red tile roof with white
  gable trim). Modelled to that photo: glass stage to 2.9 m, brick band, shaft, faces centred at
  6.2 m, eaves 5.7 m, cross-gable apex 8.0 m. Collision: a solid block with the cross-gable roof.

ENGINEERING PLAZA / WEIL COURTYARD
  OSM: area "Engineering Plaza" (leisure=common, w857648949) with an outdoor seating area and a
  30-stand bike parking cut out of its north-east side; the orange 4 m structural steel artwork of
  the Civil & Coastal Engineering department (n4339659046); a hand-crank solar information
  terminal (n4027014576, 2 m). The generator would draw the plaza as lawn (no surface tag): this
  module paves it (plaza_brick, as in the 2025 photo) together with the courtyard triangle round
  the clock tower (between the diagonal walk, the E-W walk and the N-S walk), and adds the steel
  sculpture (walkable top girder at 4.0 m: triple-jump red-coin perch, or the two step plates on
  its west column, 1.6 / 2.9 m; columns orange, girder, plates and brace blue since its Dec 2025
  repaint in UF orange and blue), two tables, the solar kiosk (2 m step), bike racks, two live oaks
  and two sabal palms ("oak-shaded plaza", palms in the 2025 photo).

Sources (reviewed)
  - NRHP registration form, Engineering Industries Building (Weil Hall), 2008:
https://npgallery.nps.gov/pdfhost/docs/NRHP/Text/08000547.pdf
  - Wikipedia, "Weil Hall": https://en.wikipedia.org/wiki/Weil_Hall
  - UF News, "Original steel teaching sculpture gets a facelift" (Dec 2025, orange and blue):
    https://news.ufl.edu/2025/12/original-steel-teaching-sculpture-gets-a-facelift/
  - UF HWCOE building directory, Joseph Weil Hall (6 floors, 158,558 GSF, 473 rooms, 1950):
    https://www.eng.ufl.edu/facilities/hwcoe-buildings-information/hwcoe-building-directory/name/joseph-weil-hall
  - Photo "Dsg UF Campus Skyline From Stadium 20050507" (north facade: front gables, shed dormers):
    https://commons.wikimedia.org/wiki/File:Dsg_UF_Campus_Skyline_From_Stadium_20050507.jpg
  - UF News, "Time for a change atop the Weil Hall clock tower" (2025-11):
    https://news.ufl.edu/2025/11/uf-engineering-clock-tower
  - UF MAE, same story with the tower photo (2025-12-05):
    https://mae.ufl.edu/2025/12/05/time-for-a-change-atop-the-weil-hall-clock-tower/
  - UF Tau Beta Pi, clock tower page: https://www.uftbp.com/page.php?p=clockTower
  - OpenStreetMap ways 445808709, 481256532, 857648949, 857648945, 435957942, 857655067; nodes
    7996089874, 4431589370, 4431566458, 4431589371, 4431579534, 4431589366, 7996089872,
    7996089869, 4339659052, 4339659046, 4027014576
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
EPS = 1e-6
VIS_MAX = 20.0          # split visual faces so a 2 m texture repeats <= 10x across one face


# =================================================================== materials
def _material_table():
    """Palette names plus the generator's materials (stage_palette: facade textures, steps, trees),
    which build_stage.py also knows (S.mats); palette-only fallbacks if it cannot be imported."""
    table = {k: dict(v) for k, v in C.PALETTE.items()}
    try:
        import stage_palette as _sp   # tools/campus is on sys.path inside the generator
        for k, v in _sp.MATERIALS.items():
            table.setdefault(k, dict(v))
    except Exception:  # noqa: BLE001
        pass
    return table


MATS = _material_table()
_ROLE_PREFS = {
    "facade": ("facade_gothic", "brick_red"),     # paired lancets + cast stone surrounds, 4 m bays
    "facade_add": ("facade_brick", "brick_red"),  # the later south addition
    "facade_blank": ("facade_service", "brick_red"),
    "steps": ("steps", "limestone"),
    "flat": ("roof_gravel", "roof_dark"),
    "orange": ("banner_orange", "roof_tile_red"),
    "oak": ("leaves_oak", "copper_green"),
    "oak2": ("leaves_oak2", "copper_green"),
    "bark": ("bark", "door_wood"),
    "frond": ("palm_frond", "copper_green"),
    "palm": ("palm_trunk", "door_wood"),
}


def R(role):
    """Material name for a role (first available of the preferences)."""
    for n in _ROLE_PREFS[role]:
        if n in MATS:
            return n
    raise KeyError(role)


def _tile(m):
    return float(MATS[m].get("tile_m", 2.0))


SOLID_ORANGE_V = 0.62   # banner_orange texel row inside the solid orange area (as the stadium uses)


# =================================================================== builder (palette + generator mats)
class Bld:
    """Polygon collector like _common.Builder, accepting generator materials too."""

    def __init__(self):
        self.polys = []

    def poly(self, pts3, material, uvs=None, normal_hint=None, smooth=False):
        if material not in MATS:
            raise ValueError(f"unknown material {material!r}")
        pts3 = [tuple(float(c) for c in p) for p in pts3]
        if uvs is not None:
            uvs = [tuple(u) for u in uvs]
        # drop repeated consecutive vertices
        keep = [i for i in range(len(pts3)) if math.dist(pts3[i], pts3[i - 1]) > 1e-5]
        pts3 = [pts3[i] for i in keep]
        if uvs is not None:
            uvs = [uvs[i] for i in keep]
        if len(pts3) < 3:
            return
        n = C.face_normal(pts3)
        if math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2) < 1e-7:
            return
        if normal_hint is not None and n[0] * normal_hint[0] + n[1] * normal_hint[1] + n[2] * normal_hint[2] < 0:
            pts3.reverse()
            if uvs is not None:
                uvs.reverse()
        self.polys.append((pts3, material, uvs, smooth))

    def tri_count(self):
        return sum(len(p[0]) - 2 for p in self.polys)

    def build(self, name):
        import bmesh
        import bpy
        slots = []
        for _, m, _, _ in self.polys:
            if m not in slots:
                slots.append(m)
        me = bpy.data.meshes.new(name)
        bm = bmesh.new()
        uvl = bm.loops.layers.uv.new("UVMap")
        for pts3, m, uvs, smooth in self.polys:
            try:
                face = bm.faces.new([bm.verts.new(p) for p in pts3])
            except ValueError:
                continue
            face.material_index = slots.index(m)
            face.smooth = smooth
            if uvs is None:
                uvs = C.project_uv(pts3, _tile(m))
            for loop, (u, v) in zip(face.loops, uvs):
                loop[uvl].uv = (u, v)
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
        bm.to_mesh(me)
        bm.free()
        return me, slots


# =================================================================== geometry helpers
def _cuts(t0, t1, max_len):
    n = max(1, int(math.ceil((t1 - t0) / max_len - 1e-9)))
    return [t0 + (t1 - t0) * i / n for i in range(n + 1)]


def _r(p, nd=2):
    return tuple(round(float(c), nd) for c in p)


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(a):
    L = math.sqrt(_dot(a, a)) or 1.0
    return (a[0] / L, a[1] / L, a[2] / L)


def _lerp3(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


class Edge:
    """Vertical wall plane over the footprint edge a -> c (counter-clockwise footprint: outside on
    the right). Wall coordinates: t (0..L along a -> c), z up, off (+ = outward)."""

    def __init__(self, a, c, z0=0.0):
        self.a = (float(a[0]), float(a[1]))
        self.c = (float(c[0]), float(c[1]))
        dx, dy = self.c[0] - self.a[0], self.c[1] - self.a[1]
        self.L = math.hypot(dx, dy)
        self.d = (dx / self.L, dy / self.L)
        self.n = (self.d[1], -self.d[0])
        self.z0 = float(z0)

    def p(self, t, z, off=0.0):
        return (self.a[0] + self.d[0] * t + self.n[0] * off,
                self.a[1] + self.d[1] * t + self.n[1] * off, self.z0 + z)

    def xy(self, t, off=0.0):
        return self.p(t, 0.0, off)[:2]

    def hint(self, inward=False):
        s = -1.0 if inward else 1.0
        return (s * self.n[0], s * self.n[1], 0.0)

    def quad(self, b, t0, t1, z0, z1, mat, off=0.0, max_len=None, inward=False, uvs=None):
        if t1 - t0 < 1e-4 or z1 - z0 < 1e-4:
            return
        cuts = [t0, t1] if not max_len else _cuts(t0, t1, max_len)
        for ta, tb in zip(cuts, cuts[1:]):
            b.poly([self.p(ta, z0, off), self.p(tb, z0, off), self.p(tb, z1, off), self.p(ta, z1, off)], mat,
                   uvs=uvs, normal_hint=self.hint(inward))

    def poly(self, b, pts_tz, mat, off=0.0, inward=False, uvs=None):
        pts_tz = [(float(t), float(z)) for t, z in pts_tz]
        if len(pts_tz) <= 4:
            b.poly([self.p(t, z, off) for t, z in pts_tz], mat, uvs=uvs, normal_hint=self.hint(inward))
            return
        # concave outlines (arch openings): ear-clipped here, not left to Blender's n-gon fill
        uvmap = dict(zip(pts_tz, uvs)) if uvs is not None else None
        for tri in _ear_clip(pts_tz):
            b.poly([self.p(t, z, off) for t, z in tri], mat, uvs=[uvmap[q] for q in tri] if uvmap else None,
                   normal_hint=self.hint(inward))

    def bearing(self):
        return math.degrees(math.atan2(self.n[0], self.n[1])) % 360.0


def facade(b, E, t0, t1, z0, z1, m, bay=3.8, zref=1.2, fh=4.0, off=0.0, max_bays=5, nb=None):
    """Wall with a facade texture (one window bay x one floor per repeat): u in whole bays over the
    full edge length, v = (z - zref) / floor height; split every <= max_bays bays."""
    if t1 - t0 < 1e-4 or z1 - z0 < 1e-4:
        return
    nb = nb or max(1, int(round(E.L / bay)))
    per = E.L / nb
    for ta, tb in zip(_cuts(t0, t1, per * max_bays), _cuts(t0, t1, per * max_bays)[1:]):
        uvs = [(ta / per, (z0 - zref) / fh), (tb / per, (z0 - zref) / fh), (tb / per, (z1 - zref) / fh),
               (ta / per, (z1 - zref) / fh)]
        b.poly([E.p(ta, z0, off), E.p(tb, z0, off), E.p(tb, z1, off), E.p(ta, z1, off)], m, uvs=uvs,
               normal_hint=E.hint())


def decal(b, E, tc, w, z0, z1, m, off=0.04, u=1.0, v=1.0):
    """A flat panel (window, door, sign) centred at t = tc on the wall, explicit 0..u x 0..v UVs."""
    pts = [E.p(tc - w / 2, z0, off), E.p(tc + w / 2, z0, off), E.p(tc + w / 2, z1, off), E.p(tc - w / 2, z1, off)]
    b.poly(pts, m, uvs=[(0, 0), (u, 0), (u, v), (0, v)], normal_hint=E.hint())


def plane_quad(b, p0, p1, p2, p3, m, split=VIS_MAX, tile=None, hint=(0, 0, 1), uv=True):
    """Planar quad p0 p1 p2 p3 with p0->p1 and p3->p2 parallel (an eave and a ridge / cap edge).
    Split along p0->p1 into pieces <= split m. UVs: u along p0->p1, v across (up the slope)."""
    L = math.dist(p0, p1)
    n = max(1, int(math.ceil(L / split - 1e-9))) if split else 1
    tl = tile or _tile(m)
    ud = _norm(_sub(p1, p0))
    nrm = _norm(C.face_normal([p0, p1, p2]))
    vd = _cross(nrm, ud)
    if _dot(vd, _sub(p3, p0)) < 0:
        vd = (-vd[0], -vd[1], -vd[2])
    for i in range(n):
        f0, f1 = i / n, (i + 1) / n
        q = [_lerp3(p0, p1, f0), _lerp3(p0, p1, f1), _lerp3(p3, p2, f1), _lerp3(p3, p2, f0)]
        uvs = [(_dot(_sub(p, p0), ud) / tl, _dot(_sub(p, p0), vd) / tl) for p in q] if uv else None
        b.poly(q, m, uvs=uvs, normal_hint=hint)


def _ear_clip(pts2):
    """Triangles (counter-clockwise) of a simple polygon (any winding), by ear clipping."""
    pts = C.ccw([tuple(p) for p in pts2])
    idx = list(range(len(pts)))
    tris = []

    def area2(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    def inside(p, a, b, c):
        return area2(a, b, p) >= -1e-9 and area2(b, c, p) >= -1e-9 and area2(c, a, p) >= -1e-9
    guard = 0
    while len(idx) > 3 and guard < 1000:
        guard += 1
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            a, b, c = pts[i0], pts[i1], pts[i2]
            if area2(a, b, c) <= 1e-9:
                continue
            if any(inside(pts[j], a, b, c) for j in idx if j not in (i0, i1, i2)
                   and pts[j] not in (a, b, c)):
                continue
            tris.append((a, b, c))
            idx.pop(k)
            break
        else:
            break
    if len(idx) == 3:
        tris.append(tuple(pts[i] for i in idx))
    return tris


def flat(b, pts2, z, m, up=True, tile=None):
    """Flat polygon at height z (concave ones are ear-clipped here, every piece faces up / down)."""
    pts2 = [tuple(p) for p in pts2]
    convex = len(pts2) <= 4 and all(
        ((pts2[(i + 1) % len(pts2)][0] - pts2[i][0]) * (pts2[(i + 2) % len(pts2)][1] - pts2[(i + 1) % len(pts2)][1])
         - (pts2[(i + 1) % len(pts2)][1] - pts2[i][1]) * (pts2[(i + 2) % len(pts2)][0] - pts2[(i + 1) % len(pts2)][0]))
        * (1 if C.signed_area(pts2) > 0 else -1) >= -1e-9 for i in range(len(pts2)))
    pieces = [pts2] if convex else _ear_clip(pts2)
    for pc in pieces:
        pts3 = [(x, y, z) for x, y in pc]
        uvs = C.project_uv(pts3, tile or _tile(m), normal=(0, 0, 1))
        b.poly(pts3, m, uvs=uvs, normal_hint=(0, 0, 1 if up else -1))


def box(b, x0, x1, y0, y1, z0, z1, m, faces="tnsew", mats=None):
    """Axis-aligned box in map metres; `faces` picks t(op) b(ottom) n s e w."""
    mats = mats or {}
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
        mm = mats.get(f, m)
        uvs = None
        if mm in ("banner_orange",):
            uvs = [(0.1, SOLID_ORANGE_V), (0.9, SOLID_ORANGE_V), (0.9, SOLID_ORANGE_V), (0.1, SOLID_ORANGE_V)]
        b.poly(pts, mm, uvs=uvs, normal_hint=h)


def obox(b, cx, cy, ang, hx, hy, z0, z1, m, faces="tsenw", uv_solid=False):
    """Oriented box: centre, yaw (radians, local x axis), half sizes. faces: t + side order s e n w."""
    ca, sa = math.cos(ang), math.sin(ang)

    def P(u, v, z):
        return (cx + ca * u - sa * v, cy + sa * u + ca * v, z)
    cs = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
    sol = [(0.1, SOLID_ORANGE_V), (0.9, SOLID_ORANGE_V), (0.9, SOLID_ORANGE_V), (0.1, SOLID_ORANGE_V)]
    if "t" in faces:
        b.poly([P(u, v, z1) for u, v in cs], m, uvs=sol if uv_solid else None, normal_hint=(0, 0, 1))
    side_names = "senw"
    for k in range(4):
        if side_names[k] not in faces:
            continue
        (u0, v0), (u1, v1) = cs[k], cs[(k + 1) % 4]
        mx, my = (u0 + u1) / 2, (v0 + v1) / 2
        hint = (ca * mx - sa * my, sa * mx + ca * my, 0)
        b.poly([P(u0, v0, z0), P(u1, v1, z0), P(u1, v1, z1), P(u0, v0, z1)], m, uvs=sol if uv_solid else None,
               normal_hint=hint)


def _arch_chain(t0, t1, zs, rise, segs=2):
    """Two-centred pointed arch from (t0, zs) over the apex to (t1, zs)."""
    w = t1 - t0
    m = (t0 + t1) / 2
    r = (w * w / 4 + rise * rise) / w
    cr = t1 - r
    a_end = math.acos(max(-1.0, min(1.0, (m - cr) / r)))
    right = [(cr + r * math.cos(a_end * i / segs), zs + r * math.sin(a_end * i / segs)) for i in range(segs + 1)]
    left = [(2 * m - t, z) for t, z in right]
    return left + right[::-1][1:]


def _gothic_door(vis, col, E, tc, w, z_sill, zs, rise, depth, top_z, lettering=True, surround=0.4,
                 col_recess=True, col_floor=True):
    """Recessed Gothic-arch doorway in wall E (visual: arch hole, reveals, door leaf, cast-stone
    surround and lettering band; collision: a rectangular walk-in recess, if col_recess).
    Visual covers t in [o0 - surround, o1 + surround], z in [z_sill, top_z]; the caller draws the
    wall outside that span. Returns (o0, o1, zt): the opening and its collision top."""
    o0, o1 = tc - w / 2, tc + w / 2
    chain = _arch_chain(o0, o1, zs, rise)
    apex = zs + rise
    g = surround
    ch2 = _arch_chain(o0 - g, o1 + g, zs, rise + g * 0.9)
    # visual: wall above the surround up to top_z (brick), door leaf at the back, reveals
    E.poly(vis, ch2 + [(o1 + g, top_z), (o0 - g, top_z)], "brick_red")
    E.poly(vis, [(o0, z_sill), (o1, z_sill)] + list(reversed(chain)), "door_wood", off=-depth)
    outline = [(o0, z_sill)] + chain + [(o1, z_sill)]
    for (ta, za), (tb, zb) in zip(outline, outline[1:]):
        quad = [E.p(ta, za, 0.0), E.p(tb, zb, 0.0), E.p(tb, zb, -depth), E.p(ta, za, -depth)]
        et, ez = tb - ta, zb - za
        hint_t, hint_z = ez, -et
        vis.poly(quad, "limestone", normal_hint=(E.d[0] * hint_t, E.d[1] * hint_t, hint_z))
    # recess floor (visual + collision; at ground level the generator's ground is the floor)
    fl = [E.p(o0, z_sill, 0.15), E.p(o1, z_sill, 0.15), E.p(o1, z_sill, -depth), E.p(o0, z_sill, -depth)]
    if z_sill > 0.05:
        vis.poly(fl, "limestone", normal_hint=(0, 0, 1))
        if col_recess and col_floor:
            col.poly(fl, "limestone", normal_hint=(0, 0, 1))
    # cast stone surround (proud) and hood
    for (ta, za), (tb, zb), (tc_, zc_), (td, zd) in zip(chain, chain[1:], ch2[1:], ch2):
        E.poly(vis, [(ta, za), (tb, zb), (tc_, zc_), (td, zd)], "limestone")
    E.quad(vis, o0 - g, o0, z_sill, zs, "limestone")
    E.quad(vis, o1, o1 + g, z_sill, zs, "limestone")
    # door mullion
    E.quad(vis, tc - 0.06, tc + 0.06, z_sill, zs, "dark_trim", off=-depth + 0.04)
    if lettering:   # ENGINEERING INDUSTRIES (raised cast stone lettering): stone band + dark strip
        zl = apex + g + 0.35
        E.quad(vis, tc - 2.6, tc + 2.6, zl, zl + 0.75, "limestone", off=0.05)
        E.quad(vis, tc - 2.3, tc + 2.3, zl + 0.24, zl + 0.5, "dark_trim", off=0.08)
    # collision: rectangular recess (back, sides) - the opening up to the springing line + rise/2
    zt = zs + rise * 0.55
    if col_recess:
        E.quad(col, o0, o1, z_sill, zt, "door_wood", off=-depth)
        S1 = Edge(E.xy(o0, 0.0), E.xy(o0, -depth), E.z0)     # left reveal, faces +t (into the opening)
        S2 = Edge(E.xy(o1, -depth), E.xy(o1, 0.0), E.z0)
        for S in (S1, S2):
            S.quad(col, 0.0, S.L, max(0.0, z_sill - 0.01), zt, "limestone")
    return (o0, o1, zt)


# =================================================================== WEIL HALL: dimensions
WEIL_ID = "w445808709"
Z_WT = 1.2            # stone water table: origin of the 4 m facade floors
Z_EAVE = 13.6         # wall top / box gutter floor / flat roofs of the addition
Z_PAR = 14.3          # parapet coping
PAR_T = 0.45          # parapet thickness
GUT = 1.45            # box gutter inner edge (roof slopes start here), from the wall face
CAP = 0.5             # half width of the flat ridge caps
Z_RIDGE = 24.0        # stages.json landmark height (6 levels)
Z_STOOP = 1.8         # "steps rise a half level from Stadium Road to the main entrance"
GUT_OV = 0.15         # collision overlap of gutter floors under the slopes / into flat roofs

# main range M (E-W ridge), x from the west gable to the tower
M_XW, M_YN, M_YS = -560.0, -38.06, -57.1
M_YR = (M_YN + M_YS) / 2                     # -47.58
M_SLOPE = (Z_RIDGE - Z_EAVE) / ((M_YN - GUT) - (M_YR + CAP))    # 1.374 (54 deg)
# east range E (E-W ridge, hipped east end)
E_XE, E_YN = -435.3, -40.4
E_YR = (E_YN + M_YS) / 2                     # -48.75
E_Z_RIDGE = Z_EAVE + M_SLOPE * ((E_YN - GUT) - (E_YR + CAP))    # 22.39
E_X_HIP = E_XE - GUT - ((E_YN - GUT) - (E_YR + CAP))            # east end of the E ridge cap
# entrance tower
T_X0, T_X1, T_Y0, T_Y1 = -461.55, -455.45, -49.6, -40.4
T_DECK, T_TOP, T_PAR = 25.6, 26.4, 0.4
T_GAP_W = (-48.4, -46.76)    # west crenel (M ridge cap y -48.08 .. -47.08)
T_GAP_E = (-49.2, -47.9)     # east crenel (E ridge cap y -49.25 .. -48.25)
# projecting north wings (N-S ridges to the main ridge)
PW_X0, PW_X1, PW_YN = -474.45, -461.55, -31.9
PW_XR = (PW_X0 + PW_X1) / 2
PW_SLOPE = (Z_RIDGE - Z_EAVE) / ((PW_X1 - PW_X0) / 2 - CAP)   # 1.748 (60 deg)
WN_X0, WN_X1, WN_YN = -560.0, -546.85, -31.8
WN_XR = (WN_X0 + WN_X1) / 2
WN_SLOPE = (Z_RIDGE - Z_EAVE) / ((WN_X1 - WN_X0) / 2 - CAP)   # 1.712 (60 deg)
# polygonal bay on PW's north gable (OSM chamfers)
BAY = [(-464.75, -31.9), (-466.0, -30.5), (-470.0, -30.5), (-471.4, -31.9)]
Z_BAY = 14.4
# three flush front gables in the north facade, shed dormers between them
FG_X = (-530.55, -510.65, -490.75)
FG_HALF, FG_SLOPE = 3.6, 1.6
FG_APEX = Z_EAVE + FG_HALF * FG_SLOPE                            # 19.36
FG_PAR_HALF = FG_HALF - (Z_PAR - Z_EAVE) / FG_SLOPE             # 3.16: where the cross roof clears the parapet
FG_YV = (M_YN - GUT) - (FG_APEX - Z_EAVE) / M_SLOPE             # cross ridge meets the main slope
DORM_X = (-540.5, -520.6, -500.7, -480.8)
DORM_HALF, DORM_H, DORM_PITCH = 4.0, 3.0, math.tan(math.radians(18.0))
DORM_D = DORM_H / (M_SLOPE - DORM_PITCH)                         # 2.86 m deep
# addition and service roofs
Z_SAE = 9.6
# flat roofs as overlapping rectangles (x0, x1, y0, y1) covering the polygons below (concave
# n-gons can triangulate into flipped pieces); the north edges reach 0.4 m into the box gutter
SP_RECTS = [(-560.0, -540.77, -69.17, M_YS + 0.4), (-540.82, -532.65, -63.32, M_YS + 0.4),
            (-532.7, -522.35, -65.38, M_YS + 0.4)]
SAW_RECTS = [(-471.6, -456.6, -79.3, M_YS + 0.4), (-468.2, -461.8, -82.9, -79.25), (-456.65, -454.65, -61.15, M_YS + 0.4)]
SAE_RECTS = [(-456.6, -441.3, -79.3, -63.9), (-441.35, -440.85, -79.3, -65.15), (-440.9, -438.8, -77.9, -65.15)]
HVAC = (-455.6, -452.6, -70.0, -67.0, Z_SAE + 2.0)
COURTYARD = [(-454.65, -63.9), (-435.3, -63.9), (-435.3, M_YS), (-454.65, M_YS)]
# main entrance stoop + steps (OSM steps w857655067, 4 m wide, north to y -34.9)
ST_X = (-460.6, -456.4)
ST_Y_STOOP = -38.2
ST_Y_FOOT = -33.2
# west entrance bay (two-storey bay with a balcony off the upper floor)
WB_X0, WB_Y0, WB_Y1, WB_Z, WB_PAR_Z, WB_PAR_T = -561.8, -51.0, -43.7, 9.2, 10.1, 0.3
# lower-floor (lab) entrance niche, centre of the front elevation
LAB_X, LAB_W, LAB_H, LAB_D = -495.81, 2.4, 3.4, 1.4
# roof-access stair on the south slope of M (6 steps of 1.73 m)
RS_X = (-469.6, -467.2)
RS_N = 6

# outline: (name, a, c, wall top, kind) counter-clockwise, every vertex within 0.17 m of OSM w445808709
OUTLINE = [
    ("sa_w", (-471.6, M_YS), (-471.6, -79.3), Z_EAVE, "sa"),
    ("sa_s1", (-471.6, -79.3), (-468.2, -79.3), Z_EAVE, "sa"),
    ("st_w", (-468.2, -79.3), (-468.2, -82.9), Z_EAVE, "sa"),
    ("st_s", (-468.2, -82.9), (-461.8, -82.9), Z_EAVE, "sa"),
    ("st_e", (-461.8, -82.9), (-461.8, -79.3), Z_EAVE, "sa"),
    ("sa_s2", (-461.8, -79.3), (-456.6, -79.3), Z_EAVE, "sa"),
    ("sae_s", (-456.6, -79.3), (-440.85, -79.3), Z_SAE, "sae"),
    ("sae_j1", (-440.85, -79.3), (-440.85, -77.9), Z_SAE, "sae"),
    ("sae_j2", (-440.85, -77.9), (-438.8, -77.9), Z_SAE, "sae"),
    ("sae_e", (-438.8, -77.9), (-438.8, -65.15), Z_SAE, "sae"),
    ("sae_j3", (-438.8, -65.15), (-441.3, -65.15), Z_SAE, "sae"),
    ("sae_j4", (-441.3, -65.15), (-441.3, -63.9), Z_SAE, "sae"),
    ("sae_n", (-441.3, -63.9), (-456.6, -63.9), Z_SAE, "sae"),
    ("sa_e1", (-456.6, -63.9), (-456.6, -61.15), Z_EAVE, "sa"),
    ("sa_e2", (-456.6, -61.15), (-454.65, -61.15), Z_EAVE, "sa"),
    ("sa_e3", (-454.65, -61.15), (-454.65, M_YS), Z_EAVE, "sa"),
    ("e_s", (-454.65, M_YS), (E_XE, M_YS), Z_PAR, "main"),
    ("e_e", (E_XE, M_YS), (E_XE, E_YN), Z_PAR, "main"),
    ("e_n", (E_XE, E_YN), (T_X1, E_YN), Z_PAR, "main"),
    ("t_n", (T_X1, E_YN), (T_X0, E_YN), T_TOP, "tower"),
    ("pw_e", (PW_X1, E_YN), (PW_X1, PW_YN), Z_EAVE, "eave"),
    ("pw_n1", (PW_X1, PW_YN), BAY[0], Z_EAVE, "gable"),
    ("bay_1", BAY[0], BAY[1], Z_BAY, "bay"),
    ("bay_2", BAY[1], BAY[2], Z_BAY, "bay"),
    ("bay_3", BAY[2], BAY[3], Z_BAY, "bay"),
    ("pw_n2", BAY[3], (PW_X0, PW_YN), Z_EAVE, "gable"),
    ("pw_w", (PW_X0, PW_YN), (PW_X0, M_YN), Z_EAVE, "eave"),
    ("m_n", (PW_X0, M_YN), (WN_X1, M_YN), Z_PAR, "main"),
    ("wn_e", (WN_X1, M_YN), (WN_X1, WN_YN), Z_EAVE, "eave"),
    ("wn_n", (WN_X1, WN_YN), (WN_X0, WN_YN), Z_EAVE, "gable"),
    ("w_w", (WN_X0, WN_YN), (M_XW, -69.17), Z_EAVE, "west"),
    ("sp_s1", (-560.0, -69.17), (-540.77, -69.17), Z_EAVE, "sp"),
    ("sp_j1", (-540.77, -69.17), (-540.77, -63.32), Z_EAVE, "sp"),
    ("sp_j2", (-540.77, -63.32), (-532.7, -63.32), Z_EAVE, "sp"),
    ("sp_j3", (-532.7, -63.32), (-532.7, -65.38), Z_EAVE, "sp"),
    ("sp_s2", (-532.7, -65.38), (-522.35, -65.38), Z_EAVE, "sp"),
    ("sp_e", (-522.35, -65.38), (-522.35, M_YS), Z_EAVE, "sp"),
    ("m_s", (-522.35, M_YS), (-471.6, M_YS), Z_PAR, "main"),
]
# OSM reference vertices (checked against campus.json: a moved footprint prints a warning)
WEIL_REF = [(-471.64, -57.01), (-560.0, -69.17), (-559.93, -31.78), (-435.23, -40.48), (-466.01, -30.47),
            (-461.78, -82.87)]


def _roof_steps():
    """The 6 treads of the roof-access stair: (y0, y1, z_top) from the south gutter to the ridge."""
    y_foot = M_YS + GUT
    y_top = M_YR - CAP
    run = (y_top - y_foot) / RS_N
    rise = (Z_RIDGE - Z_EAVE) / RS_N
    return [(y_foot + run * (k - 1), y_foot + run * k, Z_EAVE + rise * k) for k in range(1, RS_N + 1)], rise


def _weil_layout():
    xc_rs = (RS_X[0] + RS_X[1]) / 2
    steps, rise = _roof_steps()
    tcx, tcy = (T_X0 + T_X1) / 2, (T_Y0 + T_Y1) / 2
    poles = [
        {"name": "weil_downspout_courtyard", "base_m": (-454.2, -57.55, 0.0), "height_m": 14.8,
         "note": "east courtyard NW corner: handstand ~13.8 m, jump west onto the addition roof (13.6) or "
                 "north over the 14.3 m parapet into the east range's south gutter"},
        {"name": "weil_downspout_courtyard_low", "base_m": (-456.15, -63.45, 0.0), "height_m": 10.8,
         "note": "east courtyard SW corner: onto the auditorium roof (9.6 m), then the HVAC box (11.6) "
                 "and the 13.6 m addition roof"},
        {"name": "weil_downspout_north_west", "base_m": (WN_X1 + 0.45, M_YN + 0.4, 0.0), "height_m": 14.8,
         "note": "inside corner of the west wing and the north facade: north box gutter, bay 1"},
        {"name": "weil_downspout_north_east", "base_m": (PW_X0 - 0.45, M_YN + 0.4, 0.0), "height_m": 14.8,
         "note": "inside corner of the entrance wing and the north facade: north box gutter, bay 4"},
        {"name": "weil_downspout_west", "base_m": (M_XW - 0.4, -58.2, 0.0), "height_m": 14.8,
         "note": "west facade by the plaza: onto the flat south service roof (13.6 m)"},
        {"name": "weil_downspout_west_bay", "base_m": (M_XW - 0.45, WB_Y1 + 0.45, 0.0), "height_m": 10.4,
         "note": "north inside corner of the west entrance bay: onto the balcony (9.2 m)"},
        {"name": "weil_downspout_service", "base_m": (-522.35 + 0.45, M_YS - 0.45, 0.0), "height_m": 14.8,
         "note": "service court, inside corner of the south projections and the main range: south gutter"},
    ]
    route = [
        ("courtyard", (-445.0, -60.5, 0.0)),
        ("downspout_top", (-454.2, -57.55, 13.8)),
        ("addition_roof", (-463.0, -62.0, Z_EAVE)),
        ("stair_foot", (xc_rs, M_YS + 1.0, Z_EAVE)),
    ]
    for k, (y0, y1, z) in enumerate(steps, 1):
        route.append((f"roof_stair_{k}", (xc_rs, (y0 + y1) / 2, z)))
    route += [("ridge_at_tower", (T_X0 - 1.2, M_YR, Z_RIDGE)), ("tower_deck", (tcx, -45.0, T_DECK))]
    doors = [
        {"name": "DOOR_weil_hall_1", "pos_m": _r((-458.47, E_YN - 1.2, Z_STOOP)), "facing_deg": 0.0,
         "width_m": 2.4, "height_m": 4.2, "recess_m": 1.2,
         "note": "main entrance in the tower (OSM 7996089874): Gothic arch, double wood doors, ENGINEERING "
                 "INDUSTRIES band; on the 1.8 m stoop up the steps from Stadium Road; not a stage door"},
        {"name": "DOOR_weil_hall_2", "pos_m": _r((WB_X0 + 0.6, -47.36, 0.0)), "facing_deg": 270.0,
         "width_m": 2.4, "height_m": 3.6, "recess_m": 0.6,
         "note": "west entrance (OSM 4431566458) under the west gable, facing the clock tower plaza"},
        {"name": "DOOR_weil_hall_3", "pos_m": _r((LAB_X, M_YN - LAB_D, 0.0)), "facing_deg": 0.0,
         "width_m": LAB_W, "height_m": 3.0, "recess_m": LAB_D,
         "note": "lower-floor laboratory entrance (OSM 4431589370), framed Gothic arch; walk-in niche = "
                 "the 'Weil server closet' spot"},
        {"name": "DOOR_weil_hall_4", "pos_m": _r((E_XE, -49.08, 0.0)), "facing_deg": 90.0, "width_m": 2.0,
         "height_m": 2.6, "note": "east entrance (OSM 4431589371); visual panel"},
        {"name": "DOOR_weil_hall_5", "pos_m": _r((-520.18, M_YS, 0.0)), "facing_deg": 180.0, "width_m": 2.0,
         "height_m": 2.6, "note": "service court door (OSM 4431579534); visual panel"},
        {"name": "DOOR_weil_hall_6", "pos_m": _r((-471.6, -58.15, 0.0)), "facing_deg": 270.0, "width_m": 2.0,
         "height_m": 2.6, "note": "south addition west door (OSM 4431589366); visual panel"},
        {"name": "DOOR_weil_hall_7", "pos_m": _r((-438.8, -71.54, 0.0)), "facing_deg": 90.0, "width_m": 2.0,
         "height_m": 2.6, "note": "south addition east door (OSM 7996089872); visual panel"},
        {"name": "DOOR_weil_hall_8", "pos_m": _r((-468.2, -81.16, 0.0)), "facing_deg": 270.0, "width_m": 1.8,
         "height_m": 2.6, "note": "stair tower west door (OSM 7996089869), toward Reed Laboratory; visual panel"},
        {"name": "DOOR_weil_hall_9", "pos_m": _r((-461.8, -80.98, 0.0)), "facing_deg": 90.0, "width_m": 1.8,
         "height_m": 2.6, "note": "stair tower east door (OSM 4339659052); visual panel"},
    ]
    dz = M_YN - GUT - DORM_D / 2
    spots = {
        "tower_deck": _r((tcx, -45.0, T_DECK)),
        "tower_deck_north": _r((tcx, T_Y1 - 1.2, T_DECK)),
        "ridge_at_tower": _r((T_X0 - 1.2, M_YR, Z_RIDGE)),
        "ridge_mid": _r((-510.0, M_YR, Z_RIDGE)),
        "ridge_west_gable": _r((M_XW + 1.0, M_YR, Z_RIDGE)),
        "ridge_wn_north": _r((WN_XR, WN_YN - 1.0, Z_RIDGE)),
        "ridge_pw_north": _r((PW_XR, PW_YN - 1.0, Z_RIDGE)),
        "ridge_east": _r((E_X_HIP - 1.0, E_YR, E_Z_RIDGE)),
        "roof_stair_foot": _r((xc_rs, M_YS + 1.0, Z_EAVE)),
        "roof_stair_top": _r((xc_rs, (steps[-1][0] + steps[-1][1]) / 2, Z_RIDGE)),
        "south_gutter_mid": _r((-497.0, M_YS + 0.95, Z_EAVE)),
        "south_service_roof": _r((-541.0, -61.0, Z_EAVE)),
        "addition_roof": _r((-464.0, -68.0, Z_EAVE)),
        "auditorium_roof": _r((-447.0, -72.0, Z_SAE)),
        "hvac_top": _r(((HVAC[0] + HVAC[1]) / 2, (HVAC[2] + HVAC[3]) / 2, HVAC[4])),
        "east_gutter": _r((E_XE - 0.95, -48.75, Z_EAVE)),
        "north_gutter_bay_1": _r((DORM_X[0], M_YN - 0.95, Z_EAVE)),
        "north_gutter_bay_2": _r((DORM_X[1], M_YN - 0.95, Z_EAVE)),
        "north_gutter_bay_3": _r((DORM_X[2], M_YN - 0.95, Z_EAVE)),
        "north_gutter_bay_4": _r((DORM_X[3], M_YN - 0.95, Z_EAVE)),
        "courtyard": _r((-445.0, -60.5, 0.0)),
        "balcony": _r(((WB_X0 + M_XW) / 2 - 0.15, -47.36, WB_Z)),
        "main_stoop": _r((-458.5, E_YN + 1.1, Z_STOOP)),
        "main_entrance_recess": _r((-458.5, E_YN - 0.7, Z_STOOP)),
        "server_closet": _r((LAB_X, M_YN - LAB_D / 2, 0.0)),
        "west_entrance": _r((WB_X0 - 2.0, -47.36, 0.0)),
        "polygonal_bay_top": _r((-468.0, -31.2, Z_BAY)),
        "front_steps_foot": _r((-458.5, ST_Y_FOOT + 1.0, 0.0)),
        "north_lawn_front": _r((-510.0, -32.0, 0.0)),
        "service_court": _r((-500.0, -62.0, 0.0)),
    }
    for k, x in enumerate(DORM_X, 1):
        spots[f"dormer_roof_{k}"] = _r((x, dz, DORM_H + Z_EAVE + DORM_PITCH * DORM_D / 2))
    for q in poles:
        q["base_m"] = _r(q["base_m"])
    return {"route": route, "doors": doors, "spots": spots, "poles": poles, "steps": steps, "rise": rise}


# =================================================================== WEIL HALL: build
def _wall_visual(vis, E, kind, top, name):
    """Banded visual wall of one outline edge (the special parts are drawn by the caller)."""
    if kind == "main":
        facade(vis, E, 0.0, E.L, 0.0, Z_EAVE, R("facade"))
        E.quad(vis, 0.0, E.L, Z_EAVE, Z_PAR, "limestone", max_len=VIS_MAX)
    elif kind in ("eave", "gable", "sp"):
        if E.L > 2.5:
            facade(vis, E, 0.0, E.L, 0.0, Z_EAVE - 0.4, R("facade"))
        else:
            E.quad(vis, 0.0, E.L, 0.0, Z_EAVE - 0.4, "brick_red")
        E.quad(vis, 0.0, E.L, Z_EAVE - 0.4, Z_EAVE, "limestone", max_len=VIS_MAX)
    elif kind == "sa":
        if E.L > 2.5:
            facade(vis, E, 0.0, E.L, 0.0, Z_EAVE - 0.4, R("facade_add"), bay=3.4)
        else:
            E.quad(vis, 0.0, E.L, 0.0, Z_EAVE - 0.4, "brick_red")
        E.quad(vis, 0.0, E.L, Z_EAVE - 0.4, Z_EAVE, "limestone", max_len=VIS_MAX)
    elif kind == "sae":
        if E.L > 4.0:
            facade(vis, E, 0.0, E.L, 0.0, Z_SAE - 0.4, R("facade_blank"), bay=5.0)
        else:
            E.quad(vis, 0.0, E.L, 0.0, Z_SAE - 0.4, "brick_red")
        E.quad(vis, 0.0, E.L, Z_SAE - 0.4, Z_SAE, "limestone", max_len=VIS_MAX)


def _gable(vis, col, E, prof_col, t_ap0, t_ap1, foot0, foot1, z_ap, cope=0.32, window=True, col_on=True,
           kneelers=True):
    """Gable wall above the eave on edge plane E. prof_col: collision profile [(t, z)] (base at the
    eave, top = the roof surface). Visual: brick gable to the roof line + proud cast-stone coping
    strips (top face on the flat cap), kneelers, attic window; t_ap0..t_ap1 = flat ridge cap;
    foot0/foot1 = rake feet."""
    if col_on:
        E.poly(col, prof_col, "brick_red")
    top = [(foot0, Z_EAVE), (t_ap0, z_ap), (t_ap1, z_ap), (foot1, Z_EAVE)]
    E.poly(vis, top, "brick_red")
    # coping: strips along the two rakes and the cap, from roof line to roof line + cope
    for k, ((ta, za), (tb, zb)) in enumerate(zip(top, top[1:])):
        E.poly(vis, [(ta, za - 0.05), (tb, zb - 0.05), (tb, zb + cope), (ta, za + cope)], "limestone", off=0.05)
        if k == 1:      # flat cap: top face (the rakes show their proud face only)
            vis.poly([E.p(ta, za + cope, 0.05), E.p(tb, zb + cope, 0.05), E.p(tb, zb + cope, -0.5),
                      E.p(ta, za + cope, -0.5)], "limestone", normal_hint=(0, 0, 1))
    # kneelers (the rake coping "terminating in stepped parapets") at the rake feet
    if kneelers:
        for tf, s in ((foot0, 1), (foot1, -1)):
            t0, t1 = sorted((tf - s * 0.15, tf + s * 0.75))
            E.quad(vis, t0, t1, Z_EAVE - 0.05, Z_EAVE + 0.75, "limestone", off=0.06)
            vis.poly([E.p(t0, Z_EAVE + 0.75, 0.06), E.p(t1, Z_EAVE + 0.75, 0.06), E.p(t1, Z_EAVE + 0.75, -0.6),
                      E.p(t0, Z_EAVE + 0.75, -0.6)], "limestone", normal_hint=(0, 0, 1))
    if window:      # attic window: one facade bay (paired lancets in cast stone) scaled into the gable
        tm = (t_ap0 + t_ap1) / 2
        w = min(3.6, (t_ap0 - foot0) * 0.9)
        decal(vis, E, tm, w, Z_EAVE + 1.0, Z_EAVE + 1.0 + w, R("facade"), off=0.03)


def _build_weil(ctx):
    lay = _weil_layout()
    gz = ctx["ground_z"](-500.0, -50.0)
    vis, col = Bld(), Bld()
    edges = {name: (Edge(a, c, gz), top, kind) for name, a, c, top, kind in OUTLINE}

    # ---------------------------------------------------------------- outline walls
    for name, a, c, top, kind in OUTLINE:
        E = edges[name][0]
        if name == "t_n":
            continue                                   # tower north face: below
        if name == "m_n":
            # collision: wall split round the lower-floor niche
            tl = abs(LAB_X - PW_X0)                     # t of the niche centre (edge runs west)
            o0, o1 = tl - LAB_W / 2, tl + LAB_W / 2
            E.quad(col, 0.0, o0, 0.0, top, "brick_red")
            E.quad(col, o1, E.L, 0.0, top, "brick_red")
            E.quad(col, o0, o1, LAB_H, top, "brick_red")
            continue
        E.quad(col, 0.0, E.L, 0.0, top, "brick_red")
        if kind in ("bay", "west"):
            continue
        _wall_visual(vis, E, kind, top, name)
    # internal wall: the 13.6 m addition above the 9.6 m auditorium roof (faces east)
    Ei = Edge((-456.6, -79.3), (-456.6, -63.9), gz)
    Ei.quad(col, 0.0, Ei.L, Z_SAE - 0.2, Z_EAVE, "brick_red")
    facade(vis, Ei, 0.0, Ei.L, Z_SAE, Z_EAVE - 0.4, R("facade_add"), bay=3.4)
    Ei.quad(vis, 0.0, Ei.L, Z_EAVE - 0.4, Z_EAVE, "limestone")

    # ---------------------------------------------------------------- north facade (M): niche, plinth
    En = edges["m_n"][0]
    tl = abs(LAB_X - PW_X0)
    o0, o1 = tl - LAB_W / 2, tl + LAB_W / 2
    facade(vis, En, 0.0, o0, 0.0, Z_EAVE, R("facade"), nb=19)
    facade(vis, En, o1, En.L, 0.0, Z_EAVE, R("facade"), nb=19)
    # parapet band only between the front gables (the gable walls rise from the eave there)
    xs_b = [PW_X0] + [v for xg in sorted(FG_X, reverse=True) for v in (xg + FG_HALF - 0.05, xg - FG_HALF + 0.05)] \
        + [WN_X1]
    for xa, xb in zip(xs_b[0::2], xs_b[1::2]):
        En.quad(vis, abs(xa - PW_X0), abs(xb - PW_X0), Z_EAVE, Z_PAR, "limestone", max_len=VIS_MAX)
    # stone water table along the visible north face
    En.quad(vis, 0.0, o0 - 0.45, 0.95, Z_WT, "limestone", off=0.06, max_len=VIS_MAX)
    En.quad(vis, o1 + 0.45, En.L, 0.95, Z_WT, "limestone", off=0.06, max_len=VIS_MAX)
    # lower-floor niche: framed Gothic arch, bas-relief panel (civil engineer's tools) above
    chain = _arch_chain(o0, o1, 2.4, 1.0)
    En.poly(vis, chain + [(o1, Z_EAVE), (o0, Z_EAVE)], R("facade"),
            uvs=[(t / (En.L / 19), (z - Z_WT) / 4.0) for t, z in chain + [(o1, Z_EAVE), (o0, Z_EAVE)]])
    En.poly(vis, [(o0, 0.0), (o1, 0.0)] + list(reversed(chain)), "door_wood", off=-LAB_D)
    outline_n = [(o0, 0.0)] + chain + [(o1, 0.0)]
    for (ta, za), (tb, zb) in zip(outline_n, outline_n[1:]):
        q = [En.p(ta, za, 0.0), En.p(tb, zb, 0.0), En.p(tb, zb, -LAB_D), En.p(ta, za, -LAB_D)]
        et, ez = tb - ta, zb - za
        vis.poly(q, "limestone", normal_hint=(En.d[0] * ez, En.d[1] * ez, -et))
    chain2 = _arch_chain(o0 - 0.4, o1 + 0.4, 2.4, 1.36)
    for (ta, za), (tb, zb), (tc_, zc_), (td, zd) in zip(chain, chain[1:], chain2[1:], chain2):
        En.poly(vis, [(ta, za), (tb, zb), (tc_, zc_), (td, zd)], "limestone", off=0.05)
    En.quad(vis, o0 - 0.4, o0, 0.0, 2.4, "limestone", off=0.05)
    En.quad(vis, o1, o1 + 0.4, 0.0, 2.4, "limestone", off=0.05)
    En.quad(vis, tl - 1.5, tl + 1.5, 4.2, 5.0, "limestone", off=0.06)       # bas-relief panel
    En.quad(vis, tl - 1.2, tl + 1.2, 4.4, 4.8, "bronze", off=0.08)
    # niche collision (back, sides)
    En.quad(col, o0, o1, 0.0, LAB_H, "door_wood", off=-LAB_D)
    for S in (Edge(En.xy(o0, 0.0), En.xy(o0, -LAB_D), gz), Edge(En.xy(o1, -LAB_D), En.xy(o1, 0.0), gz)):
        S.quad(col, 0.0, S.L, 0.0, LAB_H, "limestone")
        S.quad(vis, 0.0, S.L, 0.0, 2.4, "limestone")
    vis.poly([En.p(o0, LAB_H, 0.0), En.p(o1, LAB_H, 0.0), En.p(o1, LAB_H, -LAB_D), En.p(o0, LAB_H, -LAB_D)],
             "limestone", normal_hint=(0, 0, -1))

    # ---------------------------------------------------------------- west facade (x = -560)
    Ew = edges["w_w"][0]                       # t = 0 at y -31.8, runs south
    t_m0, t_m1 = abs(M_YN - WN_YN), abs(M_YS - WN_YN)     # M's north / south wall lines: t 6.26, 25.3
    facade(vis, Ew, 0.0, Ew.L, 0.0, Z_EAVE - 0.4, R("facade"), bay=3.8)
    Ew.quad(vis, 0.0, Ew.L, Z_EAVE - 0.4, Z_EAVE, "limestone", max_len=VIS_MAX)
    # the west gable of M (collision: up to the roof surface; visual: coping, kneelers, windows)
    tg0, tg1 = t_m0 + GUT, t_m1 - GUT
    tc0, tc1 = abs(M_YR - CAP - WN_YN), abs(M_YR + CAP - WN_YN)
    tc0, tc1 = sorted((tc0, tc1))
    _gable(vis, col, Ew, [(tg0, Z_EAVE), (tg1, Z_EAVE), (tc1, Z_RIDGE), (tc0, Z_RIDGE)], tc0, tc1, tg0, tg1,
           Z_RIDGE, window=False, kneelers=False)
    tmid = (tc0 + tc1) / 2
    decal(vis, Ew, tmid, 4.0, 15.0, 19.0, R("facade"), off=0.03)          # attic lancets
    decal(vis, Ew, tmid, 1.2, 20.4, 21.6, "limestone", off=0.04)          # quatrefoil panel
    # quoins at the west corners
    for t0, t1 in ((0.0, 0.6), (Ew.L - 0.6, Ew.L)):
        Ew.quad(vis, t0, t1, 0.0, Z_EAVE - 0.4, "limestone", off=0.03)

    # ---------------------------------------------------------------- west entrance bay + balcony
    Wb_w = Edge((WB_X0, WB_Y1), (WB_X0, WB_Y0), gz)        # faces west, t = 0 at the north end
    Wb_n = Edge((M_XW, WB_Y1), (WB_X0, WB_Y1), gz)         # faces north
    Wb_s = Edge((WB_X0, WB_Y0), (M_XW, WB_Y0), gz)         # faces south
    for E in (Wb_w, Wb_n, Wb_s):
        E.quad(col, 0.0, E.L, 0.0, WB_PAR_Z, "brick_red")
    tdc = abs(-47.36 - WB_Y1)
    # (the bay's door recess is visual only: its collision wall stays flat)
    ao0, ao1, _ = _gothic_door(vis, col, Wb_w, tdc, 2.4, 0.0, 2.9, 1.2, 0.6, WB_Z, lettering=True,
                               col_recess=False)
    facade(vis, Wb_w, 0.0, ao0 - 0.4, 0.0, WB_Z, R("facade"), nb=2)
    facade(vis, Wb_w, ao1 + 0.4, Wb_w.L, 0.0, WB_Z, R("facade"), nb=2)
    for E in (Wb_n, Wb_s):
        E.quad(vis, 0.0, E.L, 0.0, WB_Z, "brick_red")
    for E in (Wb_w, Wb_n, Wb_s):                            # balustrade outer faces
        E.quad(vis, 0.0, E.L, WB_Z, WB_PAR_Z, "limestone")
    # balcony floor, balustrade inner faces + tops (collision + visual)
    xi = WB_X0 + WB_PAR_T
    yi0, yi1 = WB_Y0 + WB_PAR_T, WB_Y1 - WB_PAR_T
    for bld in (vis, col):
        flat(bld, [(xi - 0.05, yi0 - 0.05), (M_XW + 0.2, yi0 - 0.05), (M_XW + 0.2, yi1 + 0.05), (xi - 0.05, yi1 + 0.05)],
             gz + WB_Z, "limestone")
        flat(bld, [(WB_X0, WB_Y0), (xi, yi0), (xi, yi1), (WB_X0, WB_Y1)], gz + WB_PAR_Z, "limestone")
        Edge((xi, yi0), (xi, yi1), gz).quad(bld, 0.0, yi1 - yi0, WB_Z, WB_PAR_Z, "limestone", inward=True)
    for bld in (vis,):
        flat(bld, [(xi, WB_Y1), (WB_X0, WB_Y1), (xi, yi1)], gz + WB_PAR_Z, "limestone")
        flat(bld, [(WB_X0, WB_Y0), (xi, WB_Y0), (xi, yi0)], gz + WB_PAR_Z, "limestone")
        flat(bld, [(xi, yi1), (M_XW, yi1), (M_XW, WB_Y1), (xi, WB_Y1)], gz + WB_PAR_Z, "limestone")
        flat(bld, [(xi, WB_Y0), (M_XW, WB_Y0), (M_XW, yi0), (xi, yi0)], gz + WB_PAR_Z, "limestone")
        Edge((M_XW, yi1), (xi, yi1), gz).quad(bld, 0.0, M_XW - xi, WB_Z, WB_PAR_Z, "limestone")
        Edge((xi, yi0), (M_XW, yi0), gz).quad(bld, 0.0, M_XW - xi, WB_Z, WB_PAR_Z, "limestone")
    # balcony door (upper floor) on the facade behind
    decal(vis, Ew, tdc + abs(WB_Y1 - WN_YN), 1.6, WB_Z, WB_Z + 2.6, "door_wood", off=0.03)

    # ---------------------------------------------------------------- polygonal bay (PW north)
    for nm in ("bay_1", "bay_2", "bay_3"):
        E = edges[nm][0]
        if nm == "bay_2":
            facade(vis, E, 0.0, E.L, 0.0, Z_EAVE, R("facade"), nb=1)
            # parapet: checkerboard diagonal brick band with quatrefoil stone panels
            E.quad(vis, 0.0, E.L, Z_EAVE, Z_BAY, "brick_dark")
            for tq in (E.L * 0.25, E.L * 0.75):
                decal(vis, E, tq, 0.5, Z_EAVE + 0.15, Z_EAVE + 0.65, "limestone", off=0.04)
        else:
            uvs = [(0.27, -0.3), (0.73, -0.3), (0.73, (Z_EAVE - Z_WT) / 4.0), (0.27, (Z_EAVE - Z_WT) / 4.0)]
            E.quad(vis, 0.0, E.L, 0.0, Z_EAVE, R("facade"), uvs=uvs)
            E.quad(vis, 0.0, E.L, Z_EAVE, Z_BAY, "brick_dark")
    for bld in (vis, col):
        flat(bld, BAY[::-1] if C.signed_area(BAY) < 0 else BAY, gz + Z_BAY, "limestone")

    # ---------------------------------------------------------------- tower
    Et = Edge((T_X1, E_YN), (T_X0, E_YN), gz)               # north face, t = 0 at the east corner
    tdoor = abs(-458.47 - T_X1)                  # OSM main entrance node
    a0, a1, zt = _gothic_door(vis, col, Et, tdoor, 2.6, Z_STOOP, 4.6, 1.5, 1.2, Z_EAVE, col_floor=False)
    # collision north face round the recess
    Et.quad(col, 0.0, a0, 0.0, T_TOP, "brick_red")
    Et.quad(col, a1, Et.L, 0.0, T_TOP, "brick_red")
    Et.quad(col, a0, a1, zt, T_TOP, "brick_red")
    # visual north face
    for z0_, z1_ in ((0.0, Z_EAVE), (Z_EAVE, T_DECK - 0.4)):
        Et.quad(vis, 0.0, a0 - 0.4, z0_, z1_, "brick_red")
        Et.quad(vis, a1 + 0.4, Et.L, z0_, z1_, "brick_red")
    Et.quad(vis, a0 - 0.4, a1 + 0.4, 0.0, Z_STOOP, "brick_red")
    Et.quad(vis, a0 - 0.4, a1 + 0.4, Z_EAVE, T_DECK - 0.4, "brick_red")
    decal(vis, Et, Et.L / 2, 1.8, 8.6, 12.6, "window_dark", off=0.06, u=1.6, v=2.0)      # tall stair window
    decal(vis, Et, Et.L / 2, 2.3, 8.3, 12.9, "limestone", off=0.04)
    tow_faces = [Et,
                 Edge((T_X0, E_YN), (T_X0, T_Y0), gz),       # west, faces west
                 Edge((T_X0, T_Y0), (T_X1, T_Y0), gz),       # south
                 Edge((T_X1, T_Y0), (T_X1, E_YN), gz)]       # east
    for k, E in enumerate(tow_faces):
        if k > 0:
            E.quad(vis, 0.0, E.L, Z_EAVE, T_DECK - 0.4, "brick_red")
        if k == 0:          # belfry lancet pair on the street face (the others rise only 2-4 m over the roofs)
            decal(vis, E, E.L / 2, 4.0, 18.4, 22.4, R("facade"), off=0.03)
        E.quad(vis, 0.0, E.L, T_DECK - 0.4, T_DECK, "limestone")
        # quoins
        for z0_, z1_ in (((0.0, Z_EAVE), (Z_EAVE, T_DECK - 0.4)) if k == 0 else ((Z_EAVE, T_DECK - 0.4),)):
            E.quad(vis, 0.0, 0.55, z0_, z1_, "limestone", off=0.03)
            E.quad(vis, E.L - 0.55, E.L, z0_, z1_, "limestone", off=0.03)
    # west / south / east faces (collision), with the crenels
    Etw, Ets, Ete = tow_faces[1], tow_faces[2], tow_faces[3]
    Etw.quad(col, 0.0, Etw.L, Z_EAVE, T_DECK, "brick_red")
    Ets.quad(col, 0.0, Ets.L, Z_EAVE, T_TOP, "brick_red")
    Ete.quad(col, 0.0, Ete.L, Z_EAVE, T_DECK, "brick_red")
    # parapet segments: (outer edge, t0, t1) with inner faces + tops
    gw0, gw1 = abs(T_GAP_W[1] - E_YN), abs(T_GAP_W[0] - E_YN)          # on the west face (t from north)
    ge0, ge1 = abs(T_GAP_E[0] - T_Y0), abs(T_GAP_E[1] - T_Y0)          # on the east face (t from south)
    segs = [(Et, 0.0, Et.L), (Etw, 0.0, gw0), (Etw, gw1, Etw.L), (Ets, 0.0, Ets.L), (Ete, ge1, Ete.L)]
    Ete.quad(vis, 0.0, ge0, T_DECK, T_TOP, "brick_red")
    for E, t0, t1 in segs:
        if E is not Ets and E is not Et:
            E.quad(col, t0, t1, T_DECK, T_TOP, "brick_red")
        for bld in (vis, col):
            E.quad(bld, t0, t1, T_DECK, T_TOP, "brick_red", off=-T_PAR, inward=True)
        for bld in (vis, col):
            bld.poly([E.p(t0, T_TOP, 0.0), E.p(t1, T_TOP, 0.0), E.p(t1, T_TOP, -T_PAR), E.p(t0, T_TOP, -T_PAR)],
                     "limestone", normal_hint=(0, 0, 1))
        E.quad(vis, t0, t1, T_DECK, T_TOP, "brick_red")
    for E, t in ((Etw, gw0), (Etw, gw1), (Ete, ge1)):            # crenel cheeks (visual)
        S = Edge(E.xy(t, 0.0), E.xy(t, -T_PAR), gz)
        S.quad(vis, 0.0, S.L, T_DECK, T_TOP, "brick_red")
        S2 = Edge(E.xy(t, -T_PAR), E.xy(t, 0.0), gz)
        S2.quad(vis, 0.0, S2.L, T_DECK, T_TOP, "brick_red")
    # deck: the whole tower top in collision (the crenels need no separate sills; the parapet stands
    # on it), the inner rectangle + crenel sills visually
    flat(col, [(T_X0, T_Y0), (T_X1, T_Y0), (T_X1, T_Y1), (T_X0, T_Y1)], gz + T_DECK, "roof_dark")
    flat(vis, [(T_X0 + T_PAR, T_Y0 + T_PAR), (T_X1 - T_PAR, T_Y0 + T_PAR), (T_X1 - T_PAR, T_Y1 - T_PAR),
               (T_X0 + T_PAR, T_Y1 - T_PAR)], gz + T_DECK, "roof_dark")
    flat(vis, [(T_X0, T_GAP_W[0]), (T_X0 + T_PAR, T_GAP_W[0]), (T_X0 + T_PAR, T_GAP_W[1]), (T_X0, T_GAP_W[1])],
         gz + T_DECK, "limestone")
    flat(vis, [(T_X1 - T_PAR, T_GAP_E[0]), (T_X1, T_GAP_E[0]), (T_X1, T_GAP_E[1]), (T_X1 - T_PAR, T_GAP_E[1])],
         gz + T_DECK, "limestone")

    # ---------------------------------------------------------------- main stoop + steps
    sx0, sx1 = ST_X
    flat(vis, [(sx0, E_YN), (sx1, E_YN), (sx1, ST_Y_STOOP), (sx0, ST_Y_STOOP)], gz + Z_STOOP, "limestone")
    # collision: one slab from the steps into the door recess (its parts inside the wall are hidden)
    flat(col, [(sx0, E_YN - 1.25), (sx1, E_YN - 1.25), (sx1, ST_Y_STOOP), (sx0, ST_Y_STOOP)], gz + Z_STOOP, "limestone")
    ramp = [(sx0, ST_Y_STOOP, gz + Z_STOOP), (sx1, ST_Y_STOOP, gz + Z_STOOP), (sx1, ST_Y_FOOT, gz), (sx0, ST_Y_FOOT, gz)]
    col.poly(ramp, "limestone", normal_hint=(0, 0, 1))
    n_steps = 10
    vis.poly(ramp, R("steps"), uvs=[(0, n_steps / 2.0), (4.2, n_steps / 2.0), (4.2, 0), (0, 0)], normal_hint=(0, 0, 1))
    for x, sg in ((sx0, -1), (sx1, 1)):
        side = [(x, E_YN, gz), (x, ST_Y_FOOT, gz), (x, ST_Y_STOOP, gz + Z_STOOP), (x, E_YN, gz + Z_STOOP)]
        col.poly(side, "brick_red", normal_hint=(sg, 0, 0))
        vis.poly(side, "limestone", normal_hint=(sg, 0, 0))

    # ---------------------------------------------------------------- gables of the north wings
    Ewn = edges["wn_n"][0]          # t = 0 at the east corner (x -546.85), runs west
    _gable(vis, col, Ewn, [(0.0, Z_EAVE), (Ewn.L, Z_EAVE), (Ewn.L / 2 + CAP, Z_RIDGE), (Ewn.L / 2 - CAP, Z_RIDGE)],
           Ewn.L / 2 - CAP, Ewn.L / 2 + CAP, 0.0, Ewn.L, Z_RIDGE)
    for t0, t1 in ((0.0, 0.6), (Ewn.L - 0.6, Ewn.L)):
        Ewn.quad(vis, t0, t1, 0.0, Z_EAVE - 0.4, "limestone", off=0.03)
    Epw = Edge((PW_X1, PW_YN), (PW_X0, PW_YN), gz)
    _gable(vis, col, Epw, [(0.0, Z_EAVE), (Epw.L, Z_EAVE), (Epw.L / 2 + CAP, Z_RIDGE), (Epw.L / 2 - CAP, Z_RIDGE)],
           Epw.L / 2 - CAP, Epw.L / 2 + CAP, 0.0, Epw.L, Z_RIDGE)
    for nm, t0, t1 in (("pw_n1", 0.0, 0.6), ("pw_n2", None, None), ("pw_e", None, None), ("pw_w", 0.0, 0.6),
                       ("wn_e", None, None)):
        E = edges[nm][0]
        if t0 is None:
            t0, t1 = E.L - 0.6, E.L
        E.quad(vis, t0, t1, 0.0, Z_EAVE - 0.4, "limestone", off=0.03)
    Ee = edges["e_n"][0]
    Ee.quad(vis, 0.0, 0.6, 0.0, Z_EAVE, "limestone", off=0.03)
    Eee = edges["e_e"][0]
    Eee.quad(vis, Eee.L - 0.6, Eee.L, 0.0, Z_EAVE, "limestone", off=0.03)
    Eee_door = abs(-49.08 - M_YS)
    decal(vis, Eee, Eee_door, 2.0, 0.0, 2.6, "door_wood", off=0.05)
    decal(vis, Eee, Eee_door, 2.6, 2.6, 3.0, "limestone", off=0.05)

    # ---------------------------------------------------------------- main roofs
    rs = "roof_tile_red"
    yNg, ySg = M_YN - GUT, M_YS + GUT                  # gutter inner edges (slope feet)
    yNc, ySc = M_YR + CAP, M_YR - CAP                  # cap edges
    # M north slope (to the tower's west face, + overlap into the tower)
    for bld, ov in ((vis, 0.0), (col, 0.45)):
        plane_quad(bld, (M_XW, yNg, gz + Z_EAVE), (T_X0 + ov, yNg, gz + Z_EAVE), (T_X0 + ov, yNc, gz + Z_RIDGE),
                   (M_XW, yNc, gz + Z_RIDGE), rs, split=VIS_MAX if bld is vis else None, uv=bld is vis)
        plane_quad(bld, (T_X1, ySg, gz + Z_EAVE), (M_XW, ySg, gz + Z_EAVE), (M_XW, ySc, gz + Z_RIDGE),
                   (T_X1, ySc, gz + Z_RIDGE), rs, split=VIS_MAX if bld is vis else None, uv=bld is vis)
        # flat ridge cap
        plane_quad(bld, (M_XW, ySc, gz + Z_RIDGE), (T_X0 + ov, ySc, gz + Z_RIDGE), (T_X0 + ov, yNc, gz + Z_RIDGE),
                   (M_XW, yNc, gz + Z_RIDGE), rs if bld is col else "roof_tile_red", split=VIS_MAX if bld is vis else None,
                   uv=bld is vis, tile=2.0)
    # E range: north / south slopes, hip, cap (overlapping 0.45 m into the tower in collision)
    eNg, eSg = E_YN - GUT, M_YS + GUT
    eNc, eSc = E_YR + CAP, E_YR - CAP
    xg_e = E_XE - GUT
    for bld, ov in ((vis, 0.0), (col, 0.45)):
        xw = T_X1 - ov
        plane_quad(bld, (xw, eNg, gz + Z_EAVE), (xg_e, eNg, gz + Z_EAVE), (E_X_HIP, eNc, gz + E_Z_RIDGE),
                   (xw, eNc, gz + E_Z_RIDGE), rs, split=VIS_MAX if bld is vis else None, uv=bld is vis, hint=(0, 1, 1))
        plane_quad(bld, (xg_e, eSg, gz + Z_EAVE), (xw, eSg, gz + Z_EAVE), (xw, eSc, gz + E_Z_RIDGE),
                   (E_X_HIP, eSc, gz + E_Z_RIDGE), rs, split=VIS_MAX if bld is vis else None, uv=bld is vis,
                   hint=(0, -1, 1))
        plane_quad(bld, (xg_e, eNg, gz + Z_EAVE), (xg_e, eSg, gz + Z_EAVE), (E_X_HIP, eSc, gz + E_Z_RIDGE),
                   (E_X_HIP, eNc, gz + E_Z_RIDGE), rs, split=None, uv=bld is vis, hint=(1, 0, 1))
        plane_quad(bld, (xw, eSc, gz + E_Z_RIDGE), (E_X_HIP, eSc, gz + E_Z_RIDGE), (E_X_HIP, eNc, gz + E_Z_RIDGE),
                   (xw, eNc, gz + E_Z_RIDGE), rs, split=None, uv=bld is vis, tile=2.0)
    # north wings (N-S ridges to the main ridge, overlapping M's cap)
    for x0, x1, xr, yn, sl in ((WN_X0, WN_X1, WN_XR, WN_YN, WN_SLOPE), (PW_X0, PW_X1, PW_XR, PW_YN, PW_SLOPE)):
        ys = M_YR
        for bld in (vis, col):
            uvb = bld is vis
            plane_quad(bld, (x0, ys, gz + Z_EAVE), (x0, yn, gz + Z_EAVE), (xr - CAP, yn, gz + Z_RIDGE),
                       (xr - CAP, ys, gz + Z_RIDGE), rs, split=None, uv=uvb, hint=(-1, 0, 1))
            plane_quad(bld, (x1, yn, gz + Z_EAVE), (x1, ys, gz + Z_EAVE), (xr + CAP, ys, gz + Z_RIDGE),
                       (xr + CAP, yn, gz + Z_RIDGE), rs, split=None, uv=uvb, hint=(1, 0, 1))
            plane_quad(bld, (xr - CAP, ys, gz + Z_RIDGE), (xr + CAP, ys, gz + Z_RIDGE), (xr + CAP, yn, gz + Z_RIDGE),
                       (xr - CAP, yn, gz + Z_RIDGE), rs, split=None, uv=uvb, tile=2.0)
    # front gables: gable wall (flush, above the parapet) + cross roof
    for xg in FG_X:
        tri_c = [(xg + FG_PAR_HALF, M_YN, gz + Z_PAR), (xg, M_YN, gz + FG_APEX), (xg - FG_PAR_HALF, M_YN, gz + Z_PAR)]
        col.poly(tri_c, "brick_red", normal_hint=(0, 1, 0))
        vis.poly([(xg + FG_HALF - 0.05, M_YN, gz + Z_EAVE), (xg, M_YN, gz + FG_APEX), (xg - FG_HALF + 0.05, M_YN, gz + Z_EAVE)],
                 "brick_red", normal_hint=(0, 1, 0))
        Eg = Edge((xg + FG_HALF, M_YN), (xg - FG_HALF, M_YN), gz)
        top = [(0.0, Z_EAVE), (FG_HALF, FG_APEX), (2 * FG_HALF, Z_EAVE)]
        for (ta, za), (tb, zb) in zip(top, top[1:]):
            Eg.poly(vis, [(ta, za - 0.05), (tb, zb - 0.05), (tb, zb + 0.3), (ta, za + 0.3)], "limestone", off=0.05)
            vis.poly([Eg.p(ta, za + 0.3, 0.05), Eg.p(tb, zb + 0.3, 0.05), Eg.p(tb, zb + 0.3, -0.45),
                      Eg.p(ta, za + 0.3, -0.45)], "limestone", normal_hint=(0, 0, 1))
        decal(vis, Eg, FG_HALF, 1.6, Z_PAR + 0.3, Z_PAR + 2.6, "window_dark", off=0.04, u=1.0, v=1.0)
        decal(vis, Eg, FG_HALF, 2.0, Z_PAR + 0.1, Z_PAR + 2.8, "limestone", off=0.02)
        for bld in (vis, col):
            uvb = bld is vis
            plane_quad(bld, (xg - FG_HALF, M_YN, gz + Z_EAVE), (xg - FG_HALF, yNg, gz + Z_EAVE), (xg, FG_YV, gz + FG_APEX),
                       (xg, M_YN, gz + FG_APEX), rs, split=None, uv=uvb, hint=(-1, 0, 1))
            plane_quad(bld, (xg + FG_HALF, yNg, gz + Z_EAVE), (xg + FG_HALF, M_YN, gz + Z_EAVE), (xg, M_YN, gz + FG_APEX),
                       (xg, FG_YV, gz + FG_APEX), rs, split=None, uv=uvb, hint=(1, 0, 1))
    # shed dormers between the gables
    for xd in DORM_X:
        x0, x1 = xd - DORM_HALF, xd + DORM_HALF
        yf, yb = yNg, yNg - DORM_D
        zf, zb = Z_EAVE + DORM_H, Z_EAVE + DORM_H + DORM_PITCH * DORM_D
        for bld in (vis, col):
            bld.poly([(x0, yf, gz + Z_EAVE), (x1, yf, gz + Z_EAVE), (x1, yf, gz + zf), (x0, yf, gz + zf)], "brick_red",
                     normal_hint=(0, 1, 0))
            plane_quad(bld, (x1, yf + (0.35 if bld is vis else 0.0), gz + zf - (0.11 if bld is vis else 0.0)),
                       (x0, yf + (0.35 if bld is vis else 0.0), gz + zf - (0.11 if bld is vis else 0.0)),
                       (x0, yb, gz + zb), (x1, yb, gz + zb), rs, split=None, uv=bld is vis)
        for x, sg in ((x0, -1), (x1, 1)):
            vis.poly([(x, yf, gz + Z_EAVE), (x, yf, gz + zf), (x, yb, gz + zb)], "brick_red", normal_hint=(sg, 0, 0))
        decal(vis, Edge((x1, yf), (x0, yf), gz), DORM_HALF, 2 * DORM_HALF - 1.6, Z_EAVE + 0.7, Z_EAVE + 2.5,
              "window_dark", off=0.04, u=(2 * DORM_HALF - 1.6) / 1.2, v=1.0)
        vis.poly([(x0, yf + 0.36, gz + zf - 0.11), (x1, yf + 0.36, gz + zf - 0.11), (x1, yf + 0.36, gz + zf - 0.35),
                  (x0, yf + 0.36, gz + zf - 0.35)], "white_trim", uvs=[(0, 0), (4, 0), (4, 0.12), (0, 0.12)],
                 normal_hint=(0, 1, 0))

    # ---------------------------------------------------------------- box gutters + parapets
    gm = "metal_gray"
    # north gutter (M), south gutter (M + E, over the flat roofs), E north + east gutters
    gut_n = [(WN_X1 - GUT_OV, M_YN - PAR_T + 0.02), (PW_X0 + GUT_OV, M_YN - PAR_T + 0.02),
             (PW_X0 + GUT_OV, yNg - GUT_OV), (WN_X1 - GUT_OV, yNg - GUT_OV)]
    gut_s = [(M_XW, ySg + GUT_OV), (E_XE - PAR_T + 0.02, ySg + GUT_OV), (E_XE - PAR_T + 0.02, M_YS + PAR_T - 0.02),
             (M_XW, M_YS + PAR_T - 0.02)]
    gut_en = [(T_X1 - GUT_OV, E_YN - PAR_T + 0.02), (E_XE - PAR_T + 0.02, E_YN - PAR_T + 0.02),
              (E_XE - PAR_T + 0.02, eNg - GUT_OV), (T_X1 - GUT_OV, eNg - GUT_OV)]
    gut_ee = [(E_XE - PAR_T + 0.02, eNg), (E_XE - PAR_T + 0.02, eSg), (xg_e - GUT_OV, eSg), (xg_e - GUT_OV, eNg)]
    for poly in (gut_n, gut_s, gut_en, gut_ee):
        for bld in (vis, col):
            if bld is vis:
                xs = [p[0] for p in poly]
                ys = [p[1] for p in poly]
                x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
                if x1 - x0 > y1 - y0:
                    for xa, xb in zip(_cuts(x0, x1, VIS_MAX), _cuts(x0, x1, VIS_MAX)[1:]):
                        flat(vis, [(xa, y0), (xb, y0), (xb, y1), (xa, y1)], gz + Z_EAVE, gm)
                else:
                    flat(vis, poly, gz + Z_EAVE, gm)
            else:
                flat(col, poly, gz + Z_EAVE, gm)
    # parapet runs: inner faces + coping tops (walls' outer faces are the outline quads)
    runs = []
    bnds = [WN_X1] + [v for xg in FG_X for v in (xg - FG_PAR_HALF, xg + FG_PAR_HALF)] + [PW_X0]
    for xa, xb in zip(bnds[0::2], bnds[1::2]):
        runs.append(([(xa, M_YN), (xb, M_YN)], "vis", (False, False)))                        # north, visual pieces
    runs.append(([(WN_X1, M_YN), (PW_X0, M_YN)], "col", (False, False)))                     # north, one collision run
    runs.append(([(-522.35, M_YS), (-471.6, M_YS)], None, (True, True)))                      # M south
    runs.append(([(-454.65, M_YS), (E_XE, M_YS), (E_XE, E_YN), (T_X1, E_YN)], None, (True, False)))   # E U-run
    for pts, only, ends in runs:
        # inset polyline to the building side (found per run by testing the outline)
        inset = _inset_polyline(pts, PAR_T)
        for (p, q), (pi, qi) in zip(zip(pts, pts[1:]), zip(inset, inset[1:])):
            mid_out = ((p[0] + q[0]) / 2 - (pi[0] + qi[0]) / 2, (p[1] + q[1]) / 2 - (pi[1] + qi[1]) / 2)
            hint_in = (-mid_out[0], -mid_out[1], 0)
            for bld in ((vis,) if only == "vis" else (col,) if only == "col" else (vis, col)):
                n = max(1, int(math.ceil(math.dist(p, q) / VIS_MAX - 1e-9))) if bld is vis else 1
                for k in range(n):
                    f0, f1 = k / n, (k + 1) / n
                    a = (p[0] + (q[0] - p[0]) * f0, p[1] + (q[1] - p[1]) * f0)
                    b_ = (p[0] + (q[0] - p[0]) * f1, p[1] + (q[1] - p[1]) * f1)
                    ai = (pi[0] + (qi[0] - pi[0]) * f0, pi[1] + (qi[1] - pi[1]) * f0)
                    bi = (pi[0] + (qi[0] - pi[0]) * f1, pi[1] + (qi[1] - pi[1]) * f1)
                    bld.poly([(ai[0], ai[1], gz + Z_EAVE), (bi[0], bi[1], gz + Z_EAVE), (bi[0], bi[1], gz + Z_PAR),
                              (ai[0], ai[1], gz + Z_PAR)], "brick_red", normal_hint=hint_in)
                    bld.poly([(a[0], a[1], gz + Z_PAR), (b_[0], b_[1], gz + Z_PAR), (bi[0], bi[1], gz + Z_PAR),
                              (ai[0], ai[1], gz + Z_PAR)], "limestone", normal_hint=(0, 0, 1))
        for k, use in zip((0, -1), ends):
            if not use:
                continue
            p, pi = pts[k], inset[k]
            q = pts[1] if k == 0 else pts[-2]
            dirv = (p[0] - q[0], p[1] - q[1])
            face = [(p[0], p[1], gz + Z_EAVE), (pi[0], pi[1], gz + Z_EAVE), (pi[0], pi[1], gz + Z_PAR), (p[0], p[1], gz + Z_PAR)]
            vis.poly(face, "brick_red", normal_hint=(dirv[0], dirv[1], 0))

    # ---------------------------------------------------------------- flat roofs (13.6 / 9.6)
    for rects, z in ((SP_RECTS, Z_EAVE), (SAW_RECTS, Z_EAVE), (SAE_RECTS, Z_SAE)):
        for x0, x1, y0, y1 in rects:
            flat(col, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], gz + z, "roof_dark")
            for xa, xb in zip(_cuts(x0, x1, 16.0), _cuts(x0, x1, 16.0)[1:]):
                for ya, yb in zip(_cuts(y0, y1, 16.0), _cuts(y0, y1, 16.0)[1:]):
                    flat(vis, [(xa, ya), (xb, ya), (xb, yb), (xa, yb)], gz + z, R("flat"), tile=4.0)
    # HVAC unit on the auditorium roof (step to the 13.6 m roof)
    hx0, hx1, hy0, hy1, hz = HVAC
    box(col, hx0, hx1, hy0, hy1, gz + Z_SAE, gz + hz, "metal_gray", faces="tnsew")
    box(vis, hx0, hx1, hy0, hy1, gz + Z_SAE, gz + hz, "metal_gray", faces="tnsew")
    vis.poly([((hx0 + hx1) / 2 - 0.9, (hy0 + hy1) / 2 - 0.9, gz + hz + 0.02), ((hx0 + hx1) / 2 + 0.9, (hy0 + hy1) / 2 - 0.9, gz + hz + 0.02),
              ((hx0 + hx1) / 2 + 0.9, (hy0 + hy1) / 2 + 0.9, gz + hz + 0.02), ((hx0 + hx1) / 2 - 0.9, (hy0 + hy1) / 2 + 0.9, gz + hz + 0.02)],
             "window_dark", uvs=[(0, 0), (1, 0), (1, 1), (0, 1)], normal_hint=(0, 0, 1))

    # ---------------------------------------------------------------- roof-access stair (south slope)
    steps, rise = lay["steps"], lay["rise"]
    rx0, rx1 = RS_X
    for k, (y0, y1, zt_) in enumerate(steps):
        zb_ = zt_ - rise
        for bld in (vis, col):
            bld.poly([(rx0, y0, gz + zt_), (rx1, y0, gz + zt_), (rx1, y1 + 0.05, gz + zt_), (rx0, y1 + 0.05, gz + zt_)],
                     "metal_gray", normal_hint=(0, 0, 1))
            bld.poly([(rx0, y0, gz + zb_ - 0.05), (rx1, y0, gz + zb_ - 0.05), (rx1, y0, gz + zt_), (rx0, y0, gz + zt_)],
                     "metal_gray", normal_hint=(0, -1, 0))
        for x, sg in ((rx0, -1), (rx1, 1)):
            vis.poly([(x, y0, gz + zb_), (x, y1, gz + zt_), (x, y0, gz + zt_)], "metal_gray", normal_hint=(sg, 0, 0))
    # handrails (visual)
    (ya, _, za), (_, yb, zb_) = steps[0], steps[-1]
    for x in (rx0 + 0.05, rx1 - 0.05):
        rail = [(x, ya, gz + za + 0.85), (x, yb, gz + zb_ + 0.85), (x, yb, gz + zb_ + 1.0), (x, ya, gz + za + 1.0)]
        vis.poly(rail, "dark_trim", uvs=[(0, 0), (6, 0), (6, 0.1), (0, 0.1)], normal_hint=(1, 0, 0))
        vis.poly(rail, "dark_trim", uvs=[(0, 0), (6, 0), (6, 0.1), (0, 0.1)], normal_hint=(-1, 0, 0))

    # ---------------------------------------------------------------- copper downspouts (pole objects)
    for p in lay["poles"]:
        x, y, z = p["base_m"]
        top = Z_EAVE if p["height_m"] > 12 else p["height_m"] - 1.1
        # the two faces turned away from the walls (the pipe stands in an inside corner or on a wall)
        hx = 0.09
        ol = [a for _, a, _, _, _ in OUTLINE] if not (WB_Y0 < y < WB_Y1 + 1.0 and x < M_XW) else \
            [(M_XW, WN_YN), (WB_X0, WN_YN), (WB_X0, WB_Y1), (M_XW, WB_Y1), (M_XW, -69.17), (-500.0, -69.17), (-500.0, WN_YN)]
        fx = "e" if _inside((x - 1.0, y), ol) else "w" if _inside((x + 1.0, y), ol) else "ew"
        fy = "n" if _inside((x, y - 1.0), ol) else "s" if _inside((x, y + 1.0), ol) else "ns"
        box(vis, x - hx, x + hx, y - hx, y + hx, gz, gz + top, "copper_green", faces=fx + fy)
        box(vis, x - 0.2, x + 0.2, y - 0.2, y + 0.2, gz + top - 0.45, gz + top, "copper_green", faces=fx + fy)
    # ---------------------------------------------------------------- door panels (minor doors)
    for nm, tpos, w in (("m_s", abs(-520.18 - (-522.35)) + 0.0, 2.0), ("sa_w", abs(-58.15 - M_YS), 2.0),
                        ("sae_e", abs(-71.54 - (-77.9)), 2.0), ("st_w", abs(-81.16 - (-79.3)), 1.8),
                        ("st_e", abs(-80.98 - (-82.9)), 1.8)):
        E = edges[nm][0]
        tp = min(max(tpos, w / 2 + 0.3), E.L - w / 2 - 0.3)
        decal(vis, E, tp, w, 0.0, 2.6, "door_wood", off=0.05)
        decal(vis, E, tp, w + 0.6, 2.6, 3.0, "limestone", off=0.05)
    return vis, col, lay


def _inset_polyline(pts, d):
    """Offset an open polyline by d toward the building (the side is found per run by testing a
    point 1 m to the right of the first segment against the outline); corners are mitred."""
    out_poly = [a for _, a, _, _, _ in OUTLINE]
    (ax, ay), (bx, by) = pts[0], pts[1]
    L = math.hypot(bx - ax, by - ay)
    rx, ry = (by - ay) / L, -(bx - ax) / L          # right-hand normal
    mx, my = (ax + bx) / 2, (ay + by) / 2
    side = 1.0 if _inside((mx + rx * 1.0, my + ry * 1.0), out_poly) else -1.0
    off_lines = []
    for p, q in zip(pts, pts[1:]):
        L = math.hypot(q[0] - p[0], q[1] - p[1])
        nx, ny = side * (q[1] - p[1]) / L, side * -(q[0] - p[0]) / L
        off_lines.append(((p[0] + nx * d, p[1] + ny * d), (q[0] + nx * d, q[1] + ny * d)))
    res = [off_lines[0][0]]
    for (p1, q1), (p2, q2) in zip(off_lines, off_lines[1:]):
        res.append(_line_x(p1, q1, p2, q2) or q1)
    res.append(off_lines[-1][1])
    return res


def _line_x(p1, q1, p2, q2):
    d1 = (q1[0] - p1[0], q1[1] - p1[1])
    d2 = (q2[0] - p2[0], q2[1] - p2[1])
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-9:
        return None
    t = ((p2[0] - p1[0]) * d2[1] - (p2[1] - p1[1]) * d2[0]) / den
    return (p1[0] + d1[0] * t, p1[1] + d1[1] * t)


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


def _flat_split(vis, poly, z, m, cell=16.0):
    """Visual flat roof: the polygon clipped to a grid of cells (keeps UV spans small)."""
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    for xa, xb in zip(_cuts(x0, x1, cell), _cuts(x0, x1, cell)[1:]):
        for ya, yb in zip(_cuts(y0, y1, cell), _cuts(y0, y1, cell)[1:]):
            piece = _clip_rect(poly, xa, ya, xb, yb)
            if len(piece) >= 3 and abs(C.signed_area(piece)) > 1e-3:
                flat(vis, piece, z, m)


def _clip_rect(poly, x0, y0, x1, y1):
    """Sutherland-Hodgman clip of a polygon to an axis-aligned rectangle (counter-clockwise out)."""
    def clip(pts, inside, inter):
        out = []
        for i in range(len(pts)):
            cur, prev = pts[i], pts[i - 1]
            if inside(cur):
                if not inside(prev):
                    out.append(inter(prev, cur))
                out.append(cur)
            elif inside(prev):
                out.append(inter(prev, cur))
        return out

    def ix(a, b, x):
        t = (x - a[0]) / (b[0] - a[0])
        return (x, a[1] + (b[1] - a[1]) * t)

    def iy(a, b, y):
        t = (y - a[1]) / (b[1] - a[1])
        return (a[0] + (b[0] - a[0]) * t, y)
    pts = C.ccw(list(poly))
    for inside, inter in ((lambda p: p[0] >= x0 - 1e-9, lambda a, b: ix(a, b, x0)),
                          (lambda p: p[0] <= x1 + 1e-9, lambda a, b: ix(a, b, x1)),
                          (lambda p: p[1] >= y0 - 1e-9, lambda a, b: iy(a, b, y0)),
                          (lambda p: p[1] <= y1 + 1e-9, lambda a, b: iy(a, b, y1))):
        if not pts:
            break
        pts = clip(pts, inside, inter)
    return pts


# =================================================================== ENGINEERING CLOCK TOWER
CT_ID = "w481256532"
CT_C = (-577.745, -46.29)
CT_H = 1.70                     # half size (OSM 3.38 x 3.43 m)
CT_Z_GLASS, CT_Z_BAND, CT_Z_EAVE, CT_Z_APEX = 2.9, 3.3, 5.7, 8.0
CT_CLOCK_Z, CT_CLOCK_R = 6.2, 0.62
CT_FACES = {"north": "Gator Chomp", "south": "Log10 Clock", "east": "Wandering Hour Dial", "west": "Binary Clock"}


def _ct_layout():
    cx, cy = CT_C
    doors = [{"name": "DOOR_engineering_clock_tower_1", "pos_m": _r((cx, cy - CT_H, 0.0)), "facing_deg": 180.0,
              "width_m": 1.0, "height_m": 2.4,
              "note": "glass door on the south (Log10) face into the clock-works room; visual only"}]
    spots = {
        "clock_tower_south": _r((cx, cy - CT_H - 1.6, 0.0)),
        "clock_tower_east": _r((cx + CT_H + 1.5, cy, 0.0)),
        "clock_tower_north": _r((cx, cy + CT_H + 1.5, 0.0)),
        "clock_tower_apex": _r((cx, cy, CT_Z_APEX)),
    }
    return {"doors": doors, "spots": spots}


def _clock_face(vis, E, tc, zc, r, kind):
    """Round clock face (8-gon) in a brick ring, 2 hands; a distinct dial per face."""
    def ring(rad, off):
        return [E.p(tc + rad * math.cos(2 * math.pi * (k + 0.5) / 8), zc + rad * math.sin(2 * math.pi * (k + 0.5) / 8),
                    off) for k in range(8)]
    vis.poly(ring(r + 0.18, 0.04), "brick_dark", normal_hint=E.hint())
    dial = "white_trim" if kind != "west" else "window_dark"
    uvs = None if dial == "white_trim" else [(0.5 + 0.5 * math.cos(2 * math.pi * (k + 0.5) / 8),
                                               0.5 + 0.5 * math.sin(2 * math.pi * (k + 0.5) / 8)) for k in range(8)]
    vis.poly(ring(r, 0.07), dial, uvs=uvs, normal_hint=E.hint())
    hand_m = "dark_trim" if kind != "west" else "white_trim"
    if kind == "north":     # Gator Chomp: two gator jaws (orange / dark wedges)
        E.poly(vis, [(tc - 0.45, zc - 0.05), (tc + 0.45, zc + 0.1), (tc + 0.45, zc + 0.3)], R("orange"), off=0.1)
        E.poly(vis, [(tc - 0.45, zc - 0.15), (tc + 0.45, zc - 0.35), (tc + 0.45, zc - 0.12)], "copper_green", off=0.1)
        return
    E.quad(vis, tc - 0.03, tc + 0.03, zc, zc + r * 0.8, hand_m, off=0.1)
    E.poly(vis, [(tc, zc - 0.03), (tc + r * 0.55, zc - 0.03 - r * 0.2), (tc + r * 0.55, zc + 0.03 - r * 0.2), (tc, zc + 0.03)],
           hand_m, off=0.1)


def _build_clock_tower(ctx):
    cx, cy = CT_C
    gz = ctx["ground_z"](cx, cy)
    vis, col = Bld(), Bld()
    h = CT_H
    corners = [(cx - h, cy - h), (cx + h, cy - h), (cx + h, cy + h), (cx - h, cy + h)]
    faces = []
    names = ("south", "east", "north", "west")
    for k in range(4):
        E = Edge(corners[k], corners[(k + 1) % 4], gz)
        faces.append((names[k], E))
    pier = 0.5
    for nm, E in faces:
        # collision: solid shaft to the eave + gable wall to the apex
        E.quad(col, 0.0, E.L, 0.0, CT_Z_EAVE, "brick_red")
        E.poly(col, [(0.0, CT_Z_EAVE), (E.L, CT_Z_EAVE), (E.L / 2, CT_Z_APEX)], "brick_red")
        # visual: plinth, glass stage between brick piers, band, shaft, gable
        E.quad(vis, 0.0, E.L, 0.0, 0.35, "brick_dark")
        E.quad(vis, 0.0, pier, 0.35, CT_Z_GLASS, "brick_red")
        E.quad(vis, E.L - pier, E.L, 0.35, CT_Z_GLASS, "brick_red")
        if nm == "south":   # glass door + side light
            E.quad(vis, pier, E.L / 2 - 0.55, 0.35, CT_Z_GLASS, "window_glass", off=-0.08,
                   uvs=[(0, 0), (0.5, 0), (0.5, 1), (0, 1)])
            E.quad(vis, E.L / 2 - 0.55, E.L / 2 + 0.55, 0.0, 2.45, "window_glass", off=-0.08,
                   uvs=[(0, 0), (0.4, 0), (0.4, 1), (0, 1)])
            E.quad(vis, E.L / 2 - 0.55, E.L / 2 + 0.55, 2.45, CT_Z_GLASS, "metal_gray", off=-0.08)
            E.quad(vis, E.L / 2 + 0.55, E.L - pier, 0.35, CT_Z_GLASS, "window_glass", off=-0.08,
                   uvs=[(0, 0), (0.5, 0), (0.5, 1), (0, 1)])
        else:
            E.quad(vis, pier, E.L - pier, 0.35, CT_Z_GLASS, "window_glass", off=-0.08,
                   uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
        for t0, t1 in ((pier, pier), (E.L - pier, E.L - pier)):     # reveal faces of the piers
            S = Edge(E.xy(t0, 0.0), E.xy(t0, -0.08), gz) if t0 < E.L / 2 else Edge(E.xy(t0, -0.08), E.xy(t0, 0.0), gz)
            S.quad(vis, 0.0, S.L, 0.35, CT_Z_GLASS, "brick_red")
        E.quad(vis, pier, E.L - pier, CT_Z_GLASS - 0.05, CT_Z_GLASS, "metal_gray", off=-0.07)
        E.quad(vis, 0.0, E.L, CT_Z_GLASS, CT_Z_BAND, "brick_dark", off=0.05)
        vis.poly([E.p(0.0, CT_Z_BAND, 0.05), E.p(E.L, CT_Z_BAND, 0.05), E.p(E.L, CT_Z_BAND, 0.0), E.p(0.0, CT_Z_BAND, 0.0)],
                 "brick_dark", normal_hint=(0, 0, 1))
        E.quad(vis, 0.0, E.L, CT_Z_BAND, CT_Z_EAVE, "brick_red")
        E.poly(vis, [(0.0, CT_Z_EAVE), (E.L, CT_Z_EAVE), (E.L / 2, CT_Z_APEX)], "brick_red")
        decal(vis, E, E.L / 2, 0.55, 3.75, 4.15, "white_trim", off=0.04)           # louvre vent
        E.quad(vis, E.L / 2 - 0.2, E.L / 2 + 0.2, 3.85, 3.9, "dark_trim", off=0.06)
        E.quad(vis, E.L / 2 - 0.2, E.L / 2 + 0.2, 4.0, 4.05, "dark_trim", off=0.06)
        _clock_face(vis, E, E.L / 2, CT_CLOCK_Z, CT_CLOCK_R, nm)
        # white gable trim (barge boards)
        for (ta, za), (tb, zb) in (((-0.12, CT_Z_EAVE - 0.08), (E.L / 2, CT_Z_APEX)), ((E.L / 2, CT_Z_APEX), (E.L + 0.12, CT_Z_EAVE - 0.08))):
            E.poly(vis, [(ta, za - 0.22), (tb, zb - 0.22), (tb, zb + 0.06), (ta, za + 0.06)], "white_trim", off=0.12,
                   uvs=[(0, 0), (2, 0), (2, 0.15), (0, 0.15)])
    # cross-gable roof: 8 facets, each from an eave corner to the apex over the face's mid ridge
    apex = (cx, cy, gz + CT_Z_APEX)
    ov = 0.22
    cz = gz + CT_Z_EAVE - ov * (CT_Z_APEX - CT_Z_EAVE) / h * 0.5
    for k in range(4):
        a = corners[k]
        b_ = corners[(k + 1) % 4]
        mid = ((a[0] + b_[0]) / 2, (a[1] + b_[1]) / 2)
        out = (mid[0] - cx, mid[1] - cy)
        Lo = math.hypot(*out)
        ox, oy = out[0] / Lo, out[1] / Lo
        ridge_end = (mid[0] + ox * ov, mid[1] + oy * ov, gz + CT_Z_APEX - 0.02)
        for corner in (a, b_):
            cvec = (corner[0] - cx, corner[1] - cy)
            cl = math.hypot(*cvec)
            cpt = (corner[0] + cvec[0] / cl * ov * 1.414, corner[1] + cvec[1] / cl * ov * 1.414, cz)
            tri = [cpt, ridge_end, apex]
            nh = (ox + cvec[0] / cl, oy + cvec[1] / cl, 1.2)
            vis.poly(tri, "roof_tile_red", normal_hint=nh)
            col.poly([(corner[0], corner[1], gz + CT_Z_EAVE), (mid[0], mid[1], gz + CT_Z_APEX), apex], "roof_tile_red",
                     normal_hint=nh)
    # ridge finial
    box(vis, cx - 0.12, cx + 0.12, cy - 0.12, cy + 0.12, gz + CT_Z_APEX - 0.1, gz + CT_Z_APEX + 0.45, "white_trim",
        faces="tnsew")
    return vis, col, _ct_layout()


# =================================================================== ENGINEERING PLAZA / COURTYARD
PLAZA_AREA = "w857648949"
PLAZA_SEATING = "w857648945"
PLAZA_BIKES = "w435957942"
# paved outline: the plaza polygon with its seating / bike-parking notches filled, plus the courtyard
# triangle round the clock tower (diagonal walk, E-W walk and N-S walk centre lines), CCW
PAVING = [(-607.7, -64.91), (-608.48, -88.57), (-606.63, -88.64), (-571.49, -89.13), (-569.81, -89.23),
          (-569.85, -70.9), (-569.79, -58.09), (-569.0, -58.09), (-568.22, -50.07), (-565.83, -47.3),
          (-565.76, -33.97), (-589.15, -49.73)]
SCULPT_C, SCULPT_ANG = (-585.97, -70.69), math.radians(-35.0)
SOLAR_C = (-570.33, -51.33)
TABLES = [(-577.2, -53.4), (-574.0, -56.2)]
BIKE_RAILS = [((-578.6, -61.6), (-570.6, -61.6)), ((-578.6, -66.6), (-570.6, -66.6))]
OAKS = [(-597.5, -79.5, 6.0), (-594.0, -60.5, 5.0)]
PALMS = [(-582.4, -47.4, 8.4), (-573.3, -44.6, 7.6)]


def _plaza_layout():
    ca, sa = math.cos(SCULPT_ANG), math.sin(SCULPT_ANG)
    spots = {
        "sculpture_top": _r((SCULPT_C[0], SCULPT_C[1], 4.0)),
        "sculpture_base": _r((SCULPT_C[0] - sa * 2.2, SCULPT_C[1] + ca * 2.2, 0.0)),
        "solar_kiosk_top": _r((SOLAR_C[0], SOLAR_C[1], 2.0)),
        "plaza_center": _r((-591.0, -76.0, 0.0)),
        "seating_table": _r((TABLES[0][0], TABLES[0][1], 0.76)),
        "bike_racks": _r((-574.6, -64.1, 0.0)),
        "courtyard_walk": _r((-570.0, -42.0, 0.0)),
    }
    return {"spots": spots}


def _oak(vis, col, x, y, R_, ht, key):
    from math import cos, sin, pi
    tr = 0.38
    sides = 5
    pts = [(x + cos(2 * pi * i / sides + 0.3) * tr, y + sin(2 * pi * i / sides + 0.3) * tr) for i in range(sides)]
    for i in range(sides):
        j = (i + 1) % sides
        q = [(pts[i][0], pts[i][1], 0.0), (pts[j][0], pts[j][1], 0.0), (pts[j][0], pts[j][1], ht + 0.6),
             (pts[i][0], pts[i][1], ht + 0.6)]
        mx, my = (pts[i][0] + pts[j][0]) / 2 - x, (pts[i][1] + pts[j][1]) / 2 - y
        vis.poly(q, R("bark"), normal_hint=(mx, my, 0))
    box(col, x - 0.3, x + 0.3, y - 0.3, y + 0.3, 0.0, ht, "door_wood", faces="nsew")
    H = R_ * 1.0
    rings = []
    for k, (rr, zz, rot) in enumerate(((0.55, 0.0, 0.0), (1.0, 0.35, 0.3), (0.72, 0.78, 0.6))):
        ring_ = []
        for i in range(8):
            a = rot + 2 * pi * i / 8
            jit = 1.0 + 0.12 * math.sin(i * 2.3 + k + x)
            ring_.append((x + cos(a) * R_ * rr * jit, y + sin(a) * R_ * rr * jit, ht + zz * H))
        rings.append(ring_)
    m = R("oak") if key % 2 == 0 else R("oak2")
    bottom, top = (x, y, ht - 0.2), (x, y, ht + H)
    r0 = rings[0]
    for i in range(8):
        vis.poly([bottom, r0[(i + 1) % 8], r0[i]], m, normal_hint=(0, 0, -1))
    for lo, hi in zip(rings, rings[1:]):
        for i in range(8):
            j = (i + 1) % 8
            mx, my = (lo[i][0] + lo[j][0]) / 2 - x, (lo[i][1] + lo[j][1]) / 2 - y
            vis.poly([lo[i], lo[j], hi[j], hi[i]], m, normal_hint=(mx, my, 0.3))
    r1 = rings[-1]
    for i in range(8):
        vis.poly([r1[i], r1[(i + 1) % 8], top], m, normal_hint=(0, 0, 1))


def _palm(vis, col, x, y, ht, key):
    from math import cos, sin, pi
    lean = (0.25 * math.sin(key * 1.7), 0.25 * math.cos(key * 1.3))
    sides = 5
    tr = 0.24
    p0 = [(x + cos(2 * pi * i / sides) * tr, y + sin(2 * pi * i / sides) * tr) for i in range(sides)]
    for i in range(sides):
        j = (i + 1) % sides
        q = [(p0[i][0], p0[i][1], 0.0), (p0[j][0], p0[j][1], 0.0), (p0[j][0] + lean[0], p0[j][1] + lean[1], ht),
             (p0[i][0] + lean[0], p0[i][1] + lean[1], ht)]
        mx, my = (p0[i][0] + p0[j][0]) / 2 - x, (p0[i][1] + p0[j][1]) / 2 - y
        vis.poly(q, R("palm"), normal_hint=(mx, my, 0))
    # (no trunk collider: the module's collision total stays inside the Weil + clock tower budgets)
    tx, ty, tz = x + lean[0], y + lean[1], ht
    for i in range(7):
        a = key + 2 * pi * i / 7
        ca, sa = cos(a), sin(a)
        L = 3.2
        droop = 0.8 + 0.4 * math.sin(i * 1.9 + key)
        base = (tx, ty, tz + 0.2)
        tip = (tx + ca * L, ty + sa * L, tz - droop)
        ml = (tx + ca * L * 0.55 - sa * 0.55, ty + sa * L * 0.55 + ca * 0.55, tz + 0.25)
        mr = (tx + ca * L * 0.55 + sa * 0.55, ty + sa * L * 0.55 - ca * 0.55, tz + 0.25)
        vis.poly([base, mr, tip, ml], R("frond"), normal_hint=(0, 0, 1))
        vis.poly([base, ml, tip, mr], R("frond"), normal_hint=(0, 0, -1))


def _bike_beam(vis, a, b, width, material):
    """A slim, double-sided low-poly bicycle frame tube between two 3D points."""
    dx, dz = b[0] - a[0], b[2] - a[2]
    length = math.hypot(dx, dz) or 1.0
    px, pz = -dz / length * width, dx / length * width
    uv = [(0.1, 0.62)] * 4 if material in ("banner_orange", "banner_blue") else None
    for side in (-1, 1):
        y = side * 0.035
        q = [(a[0] + px, a[1] + y, a[2] + pz), (b[0] + px, b[1] + y, b[2] + pz),
             (b[0] - px, b[1] + y, b[2] - pz), (a[0] - px, a[1] + y, a[2] - pz)]
        vis.poly(q, material, uvs=uv, normal_hint=(0.0, side, 0.0))


def _bicycle(vis, x, y, frame):
    """A parked campus bike: paired polygon wheels, visible spokes and a painted frame."""
    wheel_z, wheel_r, wheel_w = 0.34, 0.32, 0.035
    wheel_xs = (x - 0.52, x + 0.52)
    for wx in wheel_xs:
        for side in (-1, 1):
            yy = y + side * wheel_w
            for k in range(12):
                a0, a1 = math.tau * k / 12, math.tau * (k + 1) / 12
                outer0 = (wx + wheel_r * math.cos(a0), yy, wheel_z + wheel_r * math.sin(a0))
                outer1 = (wx + wheel_r * math.cos(a1), yy, wheel_z + wheel_r * math.sin(a1))
                inner1 = (wx + (wheel_r - 0.055) * math.cos(a1), yy, wheel_z + (wheel_r - 0.055) * math.sin(a1))
                inner0 = (wx + (wheel_r - 0.055) * math.cos(a0), yy, wheel_z + (wheel_r - 0.055) * math.sin(a0))
                vis.poly([outer0, outer1, inner1, inner0], "dark_trim", normal_hint=(0.0, side, 0.0))
            # Four spokes make the wheels read clearly at game scale.
            for k in range(4):
                a = math.tau * k / 4
                rim = (wx + (wheel_r - 0.055) * math.cos(a), yy, wheel_z + (wheel_r - 0.055) * math.sin(a))
                hub = (wx, yy, wheel_z)
                _bike_beam(vis, hub, rim, 0.009, "metal_gray")
        # Tire sidewall gives the thin wheel a little depth when viewed obliquely.
        for k in range(12):
            a0, a1 = math.tau * k / 12, math.tau * (k + 1) / 12
            p0 = (wx + wheel_r * math.cos(a0), y - wheel_w, wheel_z + wheel_r * math.sin(a0))
            p1 = (wx + wheel_r * math.cos(a1), y - wheel_w, wheel_z + wheel_r * math.sin(a1))
            p2 = (p1[0], y + wheel_w, p1[2])
            p3 = (p0[0], y + wheel_w, p0[2])
            vis.poly([p0, p1, p2, p3], "dark_trim")
    rear, front = (wheel_xs[0], y, wheel_z), (wheel_xs[1], y, wheel_z)
    crank = (x - 0.02, y, 0.36)
    seat = (x - 0.18, y, 0.70)
    head = (x + 0.30, y, 0.66)
    for a, b in ((rear, crank), (crank, seat), (seat, head), (head, crank), (crank, front), (seat, rear)):
        _bike_beam(vis, a, b, 0.025, frame)
    box(vis, x - 0.40, x - 0.05, y - 0.07, y + 0.07, 0.70, 0.75, "dark_trim", faces="tnsew")
    box(vis, x + 0.26, x + 0.44, y - 0.16, y + 0.16, 0.78, 0.83, "metal_gray", faces="tnsew")
    _bike_beam(vis, (x + 0.30, y, 0.66), (x + 0.40, y, 0.79), 0.025, "metal_gray")


def _build_plaza(ctx):
    vis, col, pave = Bld(), Bld(), Bld()
    # paving (decal: the generator moves it 1.5 cm under the collision floor)
    _flat_split(pave, PAVING, 0.0, "plaza_brick", cell=18.0)
    ca, sa = math.cos(SCULPT_ANG), math.sin(SCULPT_ANG)
    sx, sy = SCULPT_C
    pad = [(sx + ca * u - sa * v, sy + sa * u + ca * v) for u, v in ((-2.2, -1.0), (2.2, -1.0), (2.2, 1.0), (-2.2, 1.0))]
    pave.poly([(x, y, 0.004) for x, y in pad], "concrete", normal_hint=(0, 0, 1))
    # structural steel sculpture, repainted UF orange and blue in Dec 2025 (UF News): two orange wide-flange
    # columns, a blue top girder and knee brace, and two blue step plates on the west column's south face
    # (1.6 / 2.9 m: a jungle-gym way up to the 4 m girder besides the triple jump)
    orng = R("orange")
    solid = orng == "banner_orange"
    blue = "banner_blue" if "banner_blue" in MATS else orng
    for u in (-1.35, 1.35):
        cxp, cyp = sx + ca * u, sy + sa * u
        obox(vis, cxp, cyp, SCULPT_ANG, 0.17, 0.17, 0.0, 3.6, orng, faces="senw", uv_solid=solid)
        obox(col, cxp, cyp, SCULPT_ANG, 0.17, 0.17, 0.0, 3.6, orng, faces="senw")   # tops: under the girder
        obox(vis, cxp, cyp, SCULPT_ANG, 0.3, 0.3, 0.0, 0.15, "metal_gray", faces="tsenw")
    obox(vis, sx, sy, SCULPT_ANG, 1.9, 0.22, 3.6, 4.0, blue, faces="tsenw", uv_solid=solid)
    obox(col, sx, sy, SCULPT_ANG, 1.9, 0.22, 3.6, 4.0, blue, faces="tsenw")
    vis.poly([(sx + ca * u - sa * v, sy + sa * u + ca * v, z) for u, v, z in ((-1.9, -0.22, 3.6), (1.9, -0.22, 3.6),
                                                                             (1.9, 0.22, 3.6), (-1.9, 0.22, 3.6))],
             blue, uvs=[(0.1, SOLID_ORANGE_V)] * 4 if solid else None, normal_hint=(0, 0, -1))
    # step plates (collision: the top only, so they stay inside the module budget): local u along the girder,
    # v across it (south = -v)
    for pu, pz in ((-1.35, 1.6), (-0.75, 2.9)):
        px_, py_ = sx + ca * pu - sa * (-0.52), sy + sa * pu + ca * (-0.52)
        obox(vis, px_, py_, SCULPT_ANG, 0.3, 0.35, pz - 0.12, pz, blue, faces="tsenw", uv_solid=solid)
        obox(col, px_, py_, SCULPT_ANG, 0.3, 0.35, pz - 0.12, pz, blue, faces="t")   # jump-through: 2 tris each
        vis.poly([(px_ + ca * u - sa * v, py_ + sa * u + ca * v, pz - 0.12) for u, v in ((-0.3, -0.35), (0.3, -0.35),
                                                                                       (0.3, 0.35), (-0.3, 0.35))],
                 blue, uvs=[(0.1, SOLID_ORANGE_V)] * 4 if solid else None, normal_hint=(0, 0, -1))
    # knee brace (visual): from the left column at 1.4 m to the girder at 1.0 m from the right column
    for side in (-0.06, 0.06):
        p = [(sx + ca * u - sa * side, sy + sa * u + ca * side, z) for u, z in ((-1.2, 1.3), (-1.2, 1.6), (0.5, 3.6), (0.2, 3.6))]
        vis.poly(p, blue, uvs=[(0.1, SOLID_ORANGE_V)] * 4 if solid else None,
                 normal_hint=(-sa * (1 if side > 0 else -1), ca * (1 if side > 0 else -1), 0))
    # solar crank information terminal (2 m): post + tilted panel
    kx, ky = SOLAR_C
    box(vis, kx - 0.2, kx + 0.2, ky - 0.15, ky + 0.15, 0.0, 1.6, "metal_gray", faces="nsew")
    box(vis, kx - 0.32, kx + 0.32, ky - 0.25, ky + 0.25, 0.9, 1.3, orng, faces="nsew" if not solid else "nsew")
    vis.poly([(kx - 0.7, ky - 0.45, 1.75), (kx + 0.7, ky - 0.45, 1.75), (kx + 0.7, ky + 0.45, 2.05), (kx - 0.7, ky + 0.45, 2.05)],
             "window_dark", uvs=[(0, 0), (1.4, 0), (1.4, 0.9), (0, 0.9)], normal_hint=(0, -0.3, 1))
    vis.poly([(kx - 0.7, ky - 0.45, 1.70), (kx + 0.7, ky - 0.45, 1.70), (kx + 0.7, ky + 0.45, 2.0), (kx - 0.7, ky + 0.45, 2.0)],
             "metal_gray", normal_hint=(0, 0.3, -1))
    box(col, kx - 0.7, kx + 0.7, ky - 0.45, ky + 0.45, 0.0, 2.0, "metal_gray", faces="tnsew")
    # tables (round-ish: octagon top on a pedestal)
    for tx_, ty_ in TABLES:
        top = [(tx_ + 0.6 * math.cos(math.pi * (k + 0.5) / 4), ty_ + 0.6 * math.sin(math.pi * (k + 0.5) / 4)) for k in range(8)]
        vis.poly([(x, y, 0.76) for x, y in top], "concrete", normal_hint=(0, 0, 1))
        for k in range(8):
            a, b_ = top[k], top[(k + 1) % 8]
            vis.poly([(a[0], a[1], 0.7), (b_[0], b_[1], 0.7), (b_[0], b_[1], 0.76), (a[0], a[1], 0.76)], "concrete",
                     normal_hint=((a[0] + b_[0]) / 2 - tx_, (a[1] + b_[1]) / 2 - ty_, 0))
        box(vis, tx_ - 0.12, tx_ + 0.12, ty_ - 0.12, ty_ + 0.12, 0.0, 0.7, "concrete", faces="nsew")
        box(col, tx_ - 0.45, tx_ + 0.45, ty_ - 0.45, ty_ + 0.45, 0.0, 0.76, "concrete", faces="tnsew")
    # bike racks (visual: a row of hoops as one rail + legs)
    for (ax, ay), (bx, by) in BIKE_RAILS:
        vis.poly([(ax, ay, 0.8), (bx, by, 0.8), (bx, by, 0.9), (ax, ay, 0.9)], "metal_gray", normal_hint=(0, -1, 0))
        vis.poly([(ax, ay, 0.8), (bx, by, 0.8), (bx, by, 0.9), (ax, ay, 0.9)], "metal_gray", normal_hint=(0, 1, 0))
        for k in range(9):
            xh = ax + (bx - ax) * k / 8
            vis.poly([(xh - 0.03, ay, 0.0), (xh + 0.03, ay, 0.0), (xh + 0.03, ay, 0.85), (xh - 0.03, ay, 0.85)],
                     "metal_gray", normal_hint=(0, -1, 0))
    # The existing racks read as empty rails from the plaza. Park four simple campus bikes at them.
    for bx, by, frame in ((-576.6, -62.25, "banner_orange"), (-572.5, -62.25, "banner_blue"),
                          (-576.6, -67.25, "banner_blue"), (-572.5, -67.25, "banner_orange")):
        _bicycle(vis, bx, by, frame)
    for k, (x, y, R_) in enumerate(OAKS):
        _oak(vis, col, x, y, R_, 5.0 + 0.4 * k, k)
    for k, (x, y, ht) in enumerate(PALMS):
        _palm(vis, col, x, y, ht, k + 1)
    return vis, col, pave, _plaza_layout()


# =================================================================== contract
_WL = _weil_layout()
_CL = _ct_layout()
_PL = _plaza_layout()


def _centroid_osm(pts):
    return _r(C.centroid(C.ccw(pts)))


LANDMARKS = [
    {
        "slug": "weil_hall",
        "name": "Joseph Weil Hall (Engineering Industries Building)",
        "osm_ids": [WEIL_ID],
        "replaces_ways": ["w857655067"],            # the main entrance steps (modelled with the stoop)
        "stages": list(STAGES),
        "center_m": (-496.56, -52.71),              # OSM footprint centroid
        "height_m": T_TOP,
        "doors": _WL["doors"],
        "spots": _WL["spots"],
        "climb_route_m": [p for _, p in _WL["route"]],
        "top_platform": {"z_m": T_DECK, "center_m": _r(((T_X0 + T_X1) / 2, (T_Y0 + T_Y1) / 2)),
                         "half_m": (round((T_X1 - T_X0) / 2 - T_PAR, 2), round((T_Y1 - T_Y0) / 2 - T_PAR, 2)),
                         "note": "entrance tower deck inside a 0.8 m parapet with crenels W (to the 24 m ridge, "
                                 "1.6 m up) and E (to the 22.4 m east ridge, 3.2 m up)"},
        "markers": {"poles": _WL["poles"],
                    "roof_run_m": [p for _, p in _WL["route"]]},
    },
    {
        "slug": "engineering_clock_tower",
        "name": "Engineering Clock Tower",
        "osm_ids": [CT_ID],
        "stages": list(STAGES),
        "center_m": CT_C,
        "height_m": CT_Z_APEX,
        "doors": _CL["doors"],
        "spots": _CL["spots"],
        "faces": CT_FACES,
    },
    {
        "slug": "engineering_plaza",
        "name": "Engineering Plaza and Weil courtyard",
        "osm_ids": [],
        "osm_area_ids": [PLAZA_AREA],
        "replaces_areas": [PLAZA_AREA, PLAZA_SEATING, PLAZA_BIKES],
        "stages": list(STAGES),
        "center_m": (-589.5, -68.5),
        "spots": _PL["spots"],
    },
]


def _check_footprint(ctx, osm_id, ref_pts, label, tol=0.15):
    try:
        fp = C.footprint(ctx, osm_id)
    except KeyError:
        print(f"reitz_weil_eng_clocktower: WARNING {label} ({osm_id}) not in campus.json")
        return
    if not all(any(math.dist(p, q) < tol for q in fp) for p in ref_pts):
        print(f"reitz_weil_eng_clocktower: WARNING {label} footprint changed in campus.json")


def build(ctx):
    """-> [{"name", "mesh", "material_slots", "collision", "visual", "landmark"[, "decal"]}, ...]
    (map metres, z up)."""
    if "ground_z" not in ctx:
        ctx = dict(ctx, ground_z=lambda x, y: 0.0)
    key = ctx.get("stage_key")
    if key is not None and key not in STAGES:
        return []
    _check_footprint(ctx, WEIL_ID, WEIL_REF, "Weil Hall")
    _check_footprint(ctx, CT_ID, [(-576.07, -48.01), (-579.43, -44.57)], "Engineering Clock Tower")
    parts = []

    def add(slug, nm, b, collision, visual, decal_=False):
        if not b.polys:
            return
        me, slots = b.build(f"{slug} {nm}")
        p = C.part(f"{slug} {nm}", me, slots, collision=collision, visual=visual)
        p["landmark"] = slug
        if decal_:
            p["decal"] = True
        parts.append(p)

    w_vis, w_col, _ = _build_weil(ctx)
    # Weil's courtyard paving (decal)
    w_pave = Bld()
    _flat_split(w_pave, COURTYARD, 0.0, "plaza_brick", cell=18.0)
    add("weil_hall", "visual", w_vis, False, True)
    add("weil_hall", "collision", w_col, True, False)
    add("weil_hall", "courtyard paving", w_pave, False, True, decal_=True)
    c_vis, c_col, _ = _build_clock_tower(ctx)
    add("engineering_clock_tower", "visual", c_vis, False, True)
    add("engineering_clock_tower", "collision", c_col, True, False)
    p_vis, p_col, p_pave, _ = _build_plaza(ctx)
    add("engineering_plaza", "paving", p_pave, False, True, decal_=True)
    add("engineering_plaza", "visual", p_vis, False, True)
    add("engineering_plaza", "collision", p_col, True, False)
    for slug, v, c in (("weil_hall", w_vis, w_col), ("engineering_clock_tower", c_vis, c_col),
                       ("engineering_plaza", p_vis, p_col)):
        print(f"reitz_weil_eng_clocktower: {slug}: visual {v.tri_count()} tris, collision {c.tri_count()} tris")
    return parts
