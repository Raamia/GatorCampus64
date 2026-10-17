"""THE SWAMP stage landmarks: the Exactech Arena at the Stephen C. O'Connell Center ("the O'Dome")
and the Florida Gymnasium ("Alligator Alley"), hand-modelled for Super Gatorlator 64.

Landmark module (contract: tools/campus/landmarks/_common.py). Every LANDMARKS entry carries
"stages": ["swamp"], so only `build_stage.py swamp` builds it. Geometry is in MAP METRES, z up
(x = east, y = north, origin = Century Tower), on the exact OSM footprints in data/uf/campus.json:

  O'Connell Center w45719889 16,539 m2 crown 30.5 m budget 350 collision / 1200 visual tris
  Florida Gym w45719891 5,747 m2 tower 18.4 m budget 200 collision / 700 visual tris

build(ctx) returns, per landmark, one visual mesh and one closed low-poly collision mesh; each
part dict also carries "landmark": <slug>. Collision walls face out of the solids; every collision
floor Mario is meant to walk on is under 23 degrees, every slide face is over 41 degrees.

O'CONNELL CENTER (1980; Caudill Rowlett Scott + Moore, May & Harrington, structure Geiger-Berger)
  What the sources say:
    - It opened in 1980 under an air-supported PTFE-glass-fibre roof, with ~30,000 sq ft of fixed
      tensile roof around the perimeter. In 1998 the inflated roof gave way to a "conventional
      hard-shell dome". The 2016 rebuild ($64.5 M) added a grand entrance on the east side,
      between Gates 1 and 2, facing the stadium across Gale Lemerand Drive.
    - Height 30.5 m and membrane area 14,500 m2 (Structurae). Main arena 150,000 sq ft (Birdair).
    - OSM: colour white, roof:colour white; entrance nodes at the SW, SE and NE gates and three
      doors on the east curve.
  Modelled as:
    - The OSM outline (24 corners), with straight precast concrete walls on the W, N and S sides
      and chamfered gate corners. The 2016 lobby on the east is a circular arc (fitted to the 36 OSM
      nodes, R 68.2 m, 13 glass chords). Walls are 10.5 m: concrete with a dark concourse window
      band and a white cornice.
    - A flat perimeter roof ring at 10.5 m around the dome, 4-8 m wide. It widens into the
      ~20 m lobby roof on the east.
    - The dome: a rounded-square superellipse (exponent 2.15, 118 x 123 m, centred on the original
      1980 square west of the lobby; about 11,700 m2 in plan). It has three profile rings and a
      crown at 30.5 m. Faces are smooth-shaded white panels. Thin grey bands show the diagonal
      cable net of the 1980 air roof (the O'Dome's signature look). They are visual only.
  Gameplay (SM64 default surfaces slide above ~38 degrees):
    - "THE SLIDE": the outer skirt of the dome (10.5 -> 20.6 m) is a 45-47 degree band all
      round. Jumping off the cap anywhere makes a long slide down to the perimeter roof, whose
      wall is only 10.5 m high, so overshooting it does no fall damage.
    - "THE CLIMB", from the grand entrance (east, facing the stadium): ticket kiosk (2.6 m) ->
      entrance canopy (5.1 m) -> EXACTECH ARENA marquee box (7.8 m) -> lobby roof (10.5 m) ->
      a 5-step steel maintenance stair up the east skirt (2.02 m risers, 1.87 m treads) ->
      walkable 22-degree upper band -> 5-degree cap -> crown hatch (31.1 m). This is the race
      checkpoint / Flyover landmark.
    - The grand entrance has a walk-in entry niche (8 x 3 m, 4.6 m tall) under the canopy, used by
      the Tailgate Tokens "inside the Exactech Arena entry" coin.
  Not modelled: the natatorium/pool wing (separate OSM buildings, left to the generator), the
  interior, and lettering (the palette has no sign texture, so the marquee is a white panel with a
  dark band). The 10.5 m wall height and the dome's profile split are design choices for the
  slide; the sources give only the 30.5 m overall height.

FLORIDA GYMNASIUM (1947-49; Rudolph Weaver / Guy Fulton; NRHP UF Campus Historic District 2008)
  What the sources say:
    - UF PD&C character-defining features list: two-storey scale, rectangular massing, gable
      roof, central tower entrance with cast-stone surrounds on the central axis facing the
      street. Also English-bond brick, soldier courses over shallow arches at the east/west
      windows, cast-stone parapet cap and cornice line, and copper downspouts.
    - Semi-Gothic brick and limestone (UF HHP). 7,000 seats (Wikipedia); a 106 x 270 ft playing
      area (UF HHP), which fixes the hall as the long N-S volume of the footprint.
    - OSM: the entrance node is at the middle of the south facade (Stadium Road, addr 1864
      Stadium Rd). The footprint has a 15 m central pavilion on the south (and a matching one on
      the north).
  Modelled as:
    - a two-storey front block (9.6 m) with the central entrance tower (18.4 m, Tudor-arched cast
      stone entrance, lettering band, tall pointed window, corner pinnacles)
    - the gym hall (39.4 x 86.9 m): eaves 11.6 m, ridge 16.6 m (14-degree gable, walkable)
    - two-storey side wings and a north annex at 9.6 m, plus a north pavilion (12.4 m)
  No public height was found. The heights come from the "two-storey scale" plus the span of a
  7,000-seat hall (stages.json estimate 14 m; this model's ridge is 16.6 m and the tower 18.4 m).
  Gameplay:
    - a stepped brick buttress on the front block's east face (2.4 / 4.8 / 7.2 m) -> front roof
      (9.6) -> hop 2.0 m onto the hall roof -> walk up to the ridge (16.6), run its 87 m length
      -> jump the 0.8 m parapet onto the tower deck (17.6). The pinnacles (pyramids, slide)
      crown it.
    - the hall roof connects to the wing and annex roofs (9.6) for coin trails

OTHER SWAMP-WINDOW BUILDINGS (stages.json swamp landmarks)
  Not hand-modelled here. Heisman Plaza and the stadium parts belong with the stadium. The Bull Gator
  statue and the Gatorade birthplace marker are prop objects. Roberts' Stadium Club is a backdrop
  across University Ave. Van Fleet Hall, Emerson Alumni Hall, Murphree Hall and the Carse Swimming &
  Diving Complex are plain boxes that the generic extrusions already cover; the remaining collision
  headroom is better spent on the stadium.

Sources (reviewed)
  - Wikipedia, "O'Connell Center":https://en.wikipedia.org/wiki/O%27Connell_Center
  - Structurae, O'Connell Center (height 30.5 m, membrane 14,500 m2):
    https://structurae.net/en/structures/o-connell-center
  - Birdair project page (air-inflated PTFE roof 1980, ~30,000 sq ft fixed perimeter roof):
    https://www.birdair.com/?p=5644
  - TensiNet project 4801 (1998 replacement by a hard-shell dome):
    https://tensinet.com/index.php/projects-database/projects/4801
  - UF News 2014-06 (new main entrance on the east side between gates 1 and 2):
    https://archive.news.ufl.edu/articles/2014/06/oconnell-center-design-work-to-begin-soon-construction-slated-to-start-in-marc.html
  - Wikipedia, "Florida Gymnasium": https://en.wikipedia.org/wiki/Florida_Gymnasium
  - UF HHP, "Celebrating 75 Years at the Florida Gym": https://hhp.ufl.edu/?p=25598
  - UF PD&C historic campus, Florida Gymnasium character-defining features:
    https://facilities.ufl.edu/?p=7722
  - OpenStreetMap ways 45719889, 45719891, area 857776611, entrance nodes 4431930583,
    4431930914, 4431930913, 7997000209, 7997000822, 5955474635, 6257946046/7, 7997001073
"""
import math
import os
import sys

try:
    from landmarks import _common as C
except ImportError:  # imported as a top-level module: make the `landmarks` package importable
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from landmarks import _common as C

STAGES = ["swamp"]
EPS = 1e-6
VIS_MAX_LEN = 20.0   # split visual faces so a 2 m texture repeats <= ~10x across one face


# =================================================================== small helpers
def _cuts(t0, t1, max_len):
    n = max(1, int(math.ceil((t1 - t0) / max_len - 1e-9)))
    return [t0 + (t1 - t0) * i / n for i in range(n + 1)]


def _r(p, nd=2):
    return tuple(round(float(c), nd) for c in p)


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

    def quad(self, b, t0, t1, z0, z1, mat, off=0.0, max_len=None):
        if t1 - t0 < 1e-4 or z1 - z0 < 1e-4:
            return
        cuts = [t0, t1] if not max_len else _cuts(t0, t1, max_len)
        for ta, tb in zip(cuts, cuts[1:]):
            b.poly([self.p(ta, z0, off), self.p(tb, z0, off), self.p(tb, z1, off), self.p(ta, z1, off)], mat,
                   normal_hint=(self.n[0], self.n[1], 0.0))

    def poly(self, b, pts_tz, mat, off=0.0, inward=False):
        s = -1.0 if inward else 1.0
        b.poly([self.p(t, z, off) for t, z in pts_tz], mat, normal_hint=(s * self.n[0], s * self.n[1], 0.0))

    def bearing(self):
        return math.degrees(math.atan2(self.n[0], self.n[1])) % 360.0


def _box(b, x0, x1, y0, y1, z0, z1, mat, faces="tnsew", mats=None):
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
        b.poly(pts, mats.get(f, mat), normal_hint=h)


def _pyramid(b, x0, x1, y0, y1, z0, z1, mat):
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    cs = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    for i in range(4):
        p, q = cs[i], cs[(i + 1) % 4]
        mx, my = (p[0] + q[0]) / 2 - cx, (p[1] + q[1]) / 2 - cy
        b.poly([(p[0], p[1], z0), (q[0], q[1], z0), (cx, cy, z1)], mat, normal_hint=(mx, my, 0.5 * (abs(mx) + abs(my))))


def _flat(b, pts2, z, mat, up=True, uv_tile=None):
    pts3 = [(x, y, z) for x, y in pts2]
    uvs = None
    if uv_tile:
        uvs = C.project_uv(pts3, uv_tile, normal=(0, 0, 1))
    b.poly(pts3, mat, uvs=uvs, normal_hint=(0, 0, 1 if up else -1))


def _rect_grid(b, x0, x1, y0, y1, z, mat, max_len=VIS_MAX_LEN, up=True):
    xs, ys = _cuts(x0, x1, max_len), _cuts(y0, y1, max_len)
    for xa, xb in zip(xs, xs[1:]):
        for ya, yb in zip(ys, ys[1:]):
            _flat(b, [(xa, ya), (xb, ya), (xb, yb), (xa, yb)], z, mat, up)


def _subdivide_loop(pts, max_len):
    out = []
    n = len(pts)
    for i in range(n):
        a, c = pts[i], pts[(i + 1) % n]
        L = math.dist(a, c)
        k = max(1, int(math.ceil(L / max_len - 1e-9)))
        for j in range(k):
            out.append((a[0] + (c[0] - a[0]) * j / k, a[1] + (c[1] - a[1]) * j / k))
    return out


def _annulus(b, outer, inner, z, mat, uv_tile=None):
    """Flat roof between two closed loops (outer around inner), triangulated with a hole."""
    from mathutils.geometry import tessellate_polygon
    o3 = [(x, y, z) for x, y in outer]
    i3 = [(x, y, z) for x, y in inner]
    allp = o3 + i3
    for tri in tessellate_polygon([o3, i3]):
        pts = [allp[k] for k in tri]
        uvs = C.project_uv(pts, uv_tile, normal=(0, 0, 1)) if uv_tile else None
        b.poly(pts, mat, uvs=uvs, normal_hint=(0, 0, 1))


def _zipper(b, outer, inner, z, mat, center, uv_tile):
    """Flat ring between two loops that are star-shaped around `center` (both counter-clockwise):
    triangles zipped by angle, so no triangle is longer than the loops' own spacing. Falls back to
    _annulus if a triangle comes out flipped."""
    def prep(L):
        a = [math.atan2(p[1] - center[1], p[0] - center[0]) % (2 * math.pi) for p in L]
        k = min(range(len(L)), key=lambda i: a[i])
        L2, a2 = L[k:] + L[:k], a[k:] + a[:k]
        un = [a2[0]]
        for v in a2[1:]:
            while v < un[-1]:
                v += 2 * math.pi
            un.append(v)
        return L2 + [L2[0]], un + [un[0] + 2 * math.pi]
    O, ao = prep(list(outer))
    I, ai = prep(list(inner))
    tris = []
    i = j = 0
    while i < len(O) - 1 or j < len(I) - 1:
        t_o = (O[i], O[i + 1], I[j]) if i < len(O) - 1 else None
        t_i = (O[i], I[j + 1], I[j]) if j < len(I) - 1 else None
        use_o = t_i is None or (t_o is not None and ao[i + 1] <= ai[j + 1])
        # prefer the angle order, but never emit a flipped triangle when the other choice is fine
        if use_o and t_i is not None and C.signed_area(list(t_o)) <= 1e-6 < C.signed_area(list(t_i)):
            use_o = False
        elif not use_o and t_o is not None and C.signed_area(list(t_i)) <= 1e-6 < C.signed_area(list(t_o)):
            use_o = True
        if use_o:
            tris.append(t_o)
            i += 1
        else:
            tris.append(t_i)
            j += 1
    if any(C.signed_area(list(t)) <= 1e-6 for t in tris):
        print("swamp_oconnell_gym: zipper ring fell back to tessellation")
        _annulus(b, outer, inner, z, mat, uv_tile)
        return
    for t in tris:
        pts = [(x, y, z) for x, y in t]
        b.poly(pts, mat, uvs=C.project_uv(pts, uv_tile, normal=(0, 0, 1)), normal_hint=(0, 0, 1))


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


def _seg_dist(p, a, c):
    dx, dy = c[0] - a[0], c[1] - a[1]
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 < EPS else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


# =================================================================== O'CONNELL CENTER
OC_ID = "w45719889"
OC_COURT_AREA = "w857776611"       # indoor court (layer -1) inside the footprint
# east facade: circle fitted to OSM nodes 21..56 of w45719889 (rms 0.12 m), arc -66 .. +66 deg
OC_ARC_C, OC_ARC_R = (-747.24, 68.28), 68.16
OC_ARC_DEG = (-66.0, -55.0, -45.0, -35.0, -25.0, -15.0, -5.0, 5.0, 15.0, 25.0, 35.0, 45.0, 55.0, 66.0)
# the rest of the outline, simplified from the OSM nodes (counter-clockwise, starting at the NW
# chamfer and running south down the west wall); small gate kiosks and stair bumps are dropped
OC_PRE = [(-825.0, 99.5), (-825.6, 38.2), (-794.3, 11.7), (-797.2, -1.6), (-723.4, -1.3), (-723.0, 3.5)]
OC_POST = [(-726.5, 129.0), (-737.6, 137.1), (-780.8, 137.25), (-792.5, 125.9)]
OC_DC = (-758.6, 67.85)            # dome centre (centre of the original 1980 square)
OC_A, OC_B, OC_EXP, OC_SEG = 59.0, 61.5, 2.15, 24
OC_Z = 10.5                        # perimeter wall / ring roof
OC_RINGS = ((1.0, 10.5), (0.84, 20.6), (0.55, 27.5))   # (scale, z): skirt 45-47 deg, band ~21 deg
OC_CROWN = 30.5                    # Structurae height
OC_NICHE_W, OC_NICHE_D, OC_NICHE_H = 8.0, 3.0, 4.6
OC_CANOPY = (4.5, 8.0, 4.6, 5.1)    # projection, half width, bottom, top
OC_MARQUEE = (1.5, 5.0, 7.8)       # projection, half width, top
OC_KIOSK_TOP = 2.6
OC_STEP_N, OC_STEP_W = 5, 3.2
OC_HATCH = (2.0, 31.1)             # half size, top
OC_BANDS = ((0.0, 6.4, "concrete"), (6.4, 8.2, "window_dark"), (8.2, 9.7, "concrete"), (9.7, OC_Z, "white_trim"))


def _se(theta, s=1.0):
    c, sn = math.cos(theta), math.sin(theta)
    e = 2.0 / OC_EXP
    return (OC_DC[0] + s * OC_A * math.copysign(abs(c) ** e, c),
            OC_DC[1] + s * OC_B * math.copysign(abs(sn) ** e, sn))


def _oc_layout():
    arc = [(OC_ARC_C[0] + OC_ARC_R * math.cos(math.radians(d)), OC_ARC_C[1] + OC_ARC_R * math.sin(math.radians(d)))
           for d in OC_ARC_DEG]
    outline = [tuple(p) for p in OC_PRE] + arc + [tuple(p) for p in OC_POST]
    n_pre = len(OC_PRE)
    kinds = ["glass" if n_pre <= i < n_pre + len(arc) - 1 else "concrete" for i in range(len(outline))]
    mid = n_pre + OC_ARC_DEG.index(-5.0)         # central chord (-5 .. +5 deg): grand entrance
    gate_se = n_pre + OC_ARC_DEG.index(-55.0)    # chord containing the SE gate door (-50 deg)
    gate_ne = n_pre + OC_ARC_DEG.index(45.0)     # chord containing the NE gate door (+50 deg)
    gate_sw = 1                                  # B -> D chamfer (SW gate, OSM door node)
    gate_nw = len(outline) - 1                   # K -> A chamfer (NW gate)
    # dome loops: half-segment offset so a planar face is centred on due east (the stair)
    loops = []
    for s, z in OC_RINGS:
        loops.append([(*_se(2 * math.pi * (i + 0.5) / OC_SEG, s), z) for i in range(OC_SEG)])
    # grand entrance geometry (central chord is vertical: x = xf, y = yc +- half)
    xf = (outline[mid][0] + outline[mid + 1][0]) / 2
    yc = (outline[mid][1] + outline[mid + 1][1]) / 2
    # east skirt face (between the vertices at -7.5 / +7.5 deg): x of the base and top chords
    xb = _se(math.radians(7.5), OC_RINGS[0][0])[0]
    xt = _se(math.radians(7.5), OC_RINGS[1][0])[0]
    z_b, z_t = OC_RINGS[0][1], OC_RINGS[1][1]
    rise = (z_t - z_b) / OC_STEP_N
    run = (xb - xt) / OC_STEP_N

    def x_slope(z):
        return xb - (z - z_b) * (xb - xt) / (z_t - z_b)

    steps = []
    for k in range(1, OC_STEP_N + 1):
        zk = z_b + rise * k
        steps.append({"x0": x_slope(zk) - 0.5, "x1": x_slope(zk) + run, "z0": z_b + rise * (k - 1), "z1": zk})
    dy = OC_DC[1]
    hs = OC_STEP_W / 2
    can_p, can_h, can_z0, can_z1 = OC_CANOPY
    mq_p, mq_h, mq_z = OC_MARQUEE
    kiosk = (xf + 0.35, xf + 3.15, yc - 11.8, yc - 9.1)
    route = [
        ("kiosk_top", ((kiosk[0] + kiosk[1]) / 2, (kiosk[2] + kiosk[3]) / 2, OC_KIOSK_TOP)),
        ("canopy_top", (xf + can_p - 1.2, yc - can_h + 1.5, can_z1)),
        ("marquee_top", (xf + mq_p / 2, yc - 2.5, mq_z)),
        ("lobby_roof", (xf - 4.0, yc - 2.0, OC_Z)),
        ("stair_foot", (xb + 1.5, dy, OC_Z)),
    ]
    for k, s_ in enumerate(steps, 1):
        route.append((f"stair_step_{k}", ((s_["x1"] + max(s_["x1"] - run, s_["x0"])) / 2, dy, s_["z1"])))
    x3 = _se(math.radians(7.5), OC_RINGS[2][0])[0]
    route += [("upper_band", (xt - 9.0, dy, OC_RINGS[1][1] + 9.0 * (OC_RINGS[2][1] - OC_RINGS[1][1]) / (xt - x3))),
              ("crown_hatch", (OC_DC[0], OC_DC[1], OC_HATCH[1]))]
    doors = [
        {"name": "DOOR_oconnell_center_1", "pos_m": _r((xf - OC_NICHE_D, yc, 0.0)), "facing_deg": 90.0,
         "width_m": 6.0, "height_m": OC_NICHE_H, "recess_m": OC_NICHE_D,
         "note": "2016 grand entrance (OSM entrance nodes 6257946046, 7997001073, 6257946047), glass doors at "
                 "the back of the 8 x 3 m walk-in niche under the canopy; not a stage door"},
    ]
    for name, i, tf in (("DOOR_oconnell_center_2", gate_sw, 0.6), ("DOOR_oconnell_center_3", gate_se, 0.5),
                        ("DOOR_oconnell_center_4", gate_ne, 0.5), ("DOOR_oconnell_center_5", gate_nw, 0.5)):
        E = Edge(outline[i], outline[(i + 1) % len(outline)])
        doors.append({"name": name, "pos_m": _r((*E.xy(E.L * tf), 0.0)), "facing_deg": round(E.bearing(), 1),
                      "width_m": 6.0, "height_m": 3.0, "note": "gate doors (visual panel on the wall); not a stage door"})
    gate_t = {gate_sw: 0.6, gate_se: 0.5, gate_ne: 0.5, gate_nw: 0.5}
    zb1 = OC_RINGS[1][1]
    spots = {
        "crown_hatch": _r((OC_DC[0], OC_DC[1], OC_HATCH[1])),
        "dome_cap_north": _r((OC_DC[0], OC_DC[1] + 25.0, OC_RINGS[2][1] + 2.0)),
        "dome_cap_south": _r((OC_DC[0], OC_DC[1] - 25.0, OC_RINGS[2][1] + 2.0)),
        "dome_cap_west": _r((OC_DC[0] - 24.0, OC_DC[1], OC_RINGS[2][1] + 2.1)),
        "slide_top_north": _r((OC_DC[0], OC_DC[1] + OC_B * 0.84 - 0.6, zb1)),
        "slide_top_south": _r((OC_DC[0], OC_DC[1] - OC_B * 0.84 + 0.6, zb1)),
        "slide_top_west": _r((OC_DC[0] - OC_A * 0.84 + 0.6, OC_DC[1], zb1)),
        "ring_roof_north": _r((OC_DC[0], 133.3, OC_Z)),
        "ring_roof_south": _r((OC_DC[0], 2.4, OC_Z)),
        "ring_roof_west": _r((-821.5, OC_DC[1], OC_Z)),
        "lobby_roof": _r((xf - 9.0, yc, OC_Z)),
        "entry_niche": _r((xf - OC_NICHE_D / 2, yc, 0.0)),
        "canopy_top": _r((xf + can_p / 2, yc + can_h - 1.5, can_z1)),
        "kiosk_top": route[0][1],
        "marquee_top": route[2][1],
    }
    return {"outline": outline, "kinds": kinds, "mid": mid, "gate_t": gate_t, "loops": loops, "xf": xf, "yc": yc,
            "steps": steps, "xb": xb, "xt": xt, "kiosk": kiosk, "route": route, "doors": doors,
            "spots": spots, "stair_y": (dy - hs, dy + hs)}


def _surface_z(tris, x, y):
    """Height of the triangulated surface at (x, y) (None outside)."""
    for (ax, ay, az), (bx, by, bz), (cx, cy, cz) in tris:
        d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(d) < 1e-12:
            continue
        l1 = ((by - cy) * (x - cx) + (cx - bx) * (y - cy)) / d
        l2 = ((cy - ay) * (x - cx) + (ax - cx) * (y - cy)) / d
        l3 = 1 - l1 - l2
        if l1 >= -1e-7 and l2 >= -1e-7 and l3 >= -1e-7:
            return l1 * az + l2 * bz + l3 * cz
    return None


def _seg_params(p, q, a, c):
    """Parameter t on p->q where it crosses segment a->c (or None)."""
    rx, ry = q[0] - p[0], q[1] - p[1]
    sx, sy = c[0] - a[0], c[1] - a[1]
    den = rx * sy - ry * sx
    if abs(den) < 1e-12:
        return None
    t = ((a[0] - p[0]) * sy - (a[1] - p[1]) * sx) / den
    u = ((a[0] - p[0]) * ry - (a[1] - p[1]) * rx) / den
    if -1e-9 <= t <= 1 + 1e-9 and -1e-9 <= u <= 1 + 1e-9:
        return t
    return None


def _cable(b, tris, edges2, base_loop, p, q, width, lift, mat, tol=0.04):
    """A thin band lying `lift` above the dome surface along the plan line p -> q (clipped to the
    dome base): vertices at every crossing with a surface edge, merged where the surface is flat
    enough (never dipping more than `tol` under the facets)."""
    ts = {0.0, 1.0}
    for a, c in edges2:
        t = _seg_params(p, q, a, c)
        if t is not None:
            ts.add(min(1.0, max(0.0, t)))
    ts_sorted = []
    for t in sorted(ts):
        if not ts_sorted or t - ts_sorted[-1] > 2e-4:
            ts_sorted.append(t)
    ts = ts_sorted
    L = math.dist(p, q)
    ux, uy = (q[0] - p[0]) / L, (q[1] - p[1]) / L
    nx, ny = -uy * width / 2, ux * width / 2
    pts = []
    for t in ts:
        x, y = p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t
        if not _inside((x, y), base_loop):
            continue
        za = _surface_z(tris, x + nx, y + ny)
        zb = _surface_z(tris, x - nx, y - ny)
        zc = _surface_z(tris, x, y)
        if za is None or zb is None or zc is None:
            continue
        pts.append((t, x, y, za, zb, zc))
    if len(pts) < 2:
        return
    # greedy merge: keep a vertex only if dropping it would put the band under the surface
    keep = [pts[0]]
    i = 0
    while i < len(pts) - 1:
        j = i + 1
        while j + 1 < len(pts):
            ok = True
            a_, c_ = pts[i], pts[j + 1]
            for k in range(i + 1, j + 1):
                m = pts[k]
                f = (m[0] - a_[0]) / (c_[0] - a_[0])
                for idx in (3, 4, 5):
                    zl = a_[idx] + (c_[idx] - a_[idx]) * f
                    if zl < m[idx] - tol:
                        ok = False
            if not ok:
                break
            j += 1
        keep.append(pts[j])
        i = j
    for a_, c_ in zip(keep, keep[1:]):
        quad = [(a_[1] + nx, a_[2] + ny, a_[3] + lift), (a_[1] - nx, a_[2] - ny, a_[4] + lift),
                (c_[1] - nx, c_[2] - ny, c_[4] + lift), (c_[1] + nx, c_[2] + ny, c_[3] + lift)]
        b.poly(quad, mat, uvs=[(0, 0), (0.25, 0), (0.25, 1), (0, 1)], normal_hint=(0, 0, 1))


def _build_oconnell(ctx):
    lay = _oc_layout()
    gz = ctx["ground_z"](*OC_DC)
    vis, col = C.Builder(), C.Builder()
    outline, kinds, mid = lay["outline"], lay["kinds"], lay["mid"]
    n = len(outline)
    xf, yc = lay["xf"], lay["yc"]
    nw, nd, nh = OC_NICHE_W, OC_NICHE_D, OC_NICHE_H

    # ---------------------------------------------------------------- perimeter walls
    for i in range(n):
        E = Edge(outline[i], outline[(i + 1) % n], gz)
        if i == mid:
            t0 = E.L / 2 - nw / 2
            t1 = E.L / 2 + nw / 2
            # collision: wall either side of the niche, lintel above it, niche box
            E.quad(col, 0.0, t0, 0.0, OC_Z, "concrete")
            E.quad(col, t1, E.L, 0.0, OC_Z, "concrete")
            E.quad(col, t0, t1, nh, OC_Z, "concrete")
            B = Edge(E.p(t0, 0, -nd)[:2], E.p(t1, 0, -nd)[:2], gz)       # niche back (doors)
            B.quad(col, 0.0, B.L, 0.0, nh, "window_glass")
            S1 = Edge(E.p(t0, 0, 0)[:2], E.p(t0, 0, -nd)[:2], gz)        # niche south side, faces north
            S2 = Edge(E.p(t1, 0, -nd)[:2], E.p(t1, 0, 0)[:2], gz)        # niche north side, faces south
            for S in (S1, S2):
                S.quad(col, 0.0, S.L, 0.0, nh, "concrete")
                S.quad(vis, 0.0, S.L, 0.0, nh, "concrete")
            ceil = [E.p(t0, nh, 0), E.p(t1, nh, 0), E.p(t1, nh, -nd), E.p(t0, nh, -nd)]
            col.poly(ceil, "metal_gray", normal_hint=(0, 0, -1))
            vis.poly(ceil, "metal_gray", normal_hint=(0, 0, -1))
            # visual: glass either side, glass doors at the back, transom band and glass above
            for a_, c_ in ((0.0, t0), (t1, E.L)):
                E.quad(vis, a_, c_, 0.0, 4.6, "window_glass")
            E.quad(vis, 0.0, E.L, 4.6, 5.0, "metal_gray")
            E.quad(vis, 0.0, E.L, 5.0, 9.6, "window_glass")
            E.quad(vis, 0.0, E.L, 9.6, OC_Z, "metal_gray")
            B.quad(vis, 0.0, B.L, 0.0, 3.0, "window_glass")
            B.quad(vis, 0.0, B.L, 3.0, nh, "metal_gray")
            for tm in (B.L / 3, 2 * B.L / 3):   # door mullions
                B.quad(vis, tm - 0.08, tm + 0.08, 0.0, 3.0, "dark_trim", off=0.04)
            continue
        E.quad(col, 0.0, E.L, 0.0, OC_Z, "concrete")
        if kinds[i] == "glass":
            E.quad(vis, 0.0, E.L, 0.0, 4.6, "window_glass")
            E.quad(vis, 0.0, E.L, 4.6, 5.0, "metal_gray")
            E.quad(vis, 0.0, E.L, 5.0, 9.6, "window_glass")
            E.quad(vis, 0.0, E.L, 9.6, OC_Z, "metal_gray")
        else:
            for z0, z1, m in OC_BANDS:
                E.quad(vis, 0.0, E.L, z0, z1, m, max_len=VIS_MAX_LEN)
            # precast fins at the corners of the long walls (visual)
            if E.L > 30.0:
                for tf in _cuts(0.0, E.L, 15.0)[1:-1]:
                    E.quad(vis, tf - 0.35, tf + 0.35, 0.0, 9.7, "white_trim", off=0.12)
        if i in lay["gate_t"]:
            tg = E.L * lay["gate_t"][i]
            E.quad(vis, tg - 3.0, tg + 3.0, 0.0, 3.0, "window_dark", off=0.06)
            E.quad(vis, tg - 3.6, tg + 3.6, 3.3, 4.2, "dark_trim", off=0.06)

    # ---------------------------------------------------------------- perimeter roof ring
    base = [(x, y) for x, y, _ in lay["loops"][0]]
    _annulus(col, outline, base, gz + OC_Z, "metal_gray")
    _zipper(vis, _subdivide_loop(outline, 10.0), base, gz + OC_Z, "metal_gray", OC_DC, 4.0)

    # ---------------------------------------------------------------- dome
    loops = [[(x, y, z + gz) for x, y, z in L] for L in lay["loops"]]
    apex = (OC_DC[0], OC_DC[1], gz + OC_CROWN)
    dome_tris = []
    for k in range(len(loops) - 1):
        A, Bl = loops[k], loops[k + 1]
        for i in range(OC_SEG):
            j = (i + 1) % OC_SEG
            quad = [A[i], A[j], Bl[j], Bl[i]]
            dome_tris += [(A[i], A[j], Bl[j]), (A[i], Bl[j], Bl[i])]
            col.poly(quad, "white_trim", normal_hint=(0, 0, 1))
            vis.poly(quad, "white_trim", uvs=C.project_uv(quad, 4.0), normal_hint=(0, 0, 1), smooth=True)
    last = loops[-1]
    for i in range(OC_SEG):
        j = (i + 1) % OC_SEG
        tri = [last[i], last[j], apex]
        dome_tris.append(tuple(tri))
        col.poly(tri, "white_trim", normal_hint=(0, 0, 1))
        vis.poly(tri, "white_trim", uvs=C.project_uv(tri, 4.0), normal_hint=(0, 0, 1), smooth=True)
    # cable net of the 1980 air roof: two diagonal families (visual only)
    edges2 = []
    for L in loops:
        for i in range(OC_SEG):
            edges2.append((L[i][:2], L[(i + 1) % OC_SEG][:2]))
    for k in range(len(loops) - 1):
        for i in range(OC_SEG):
            edges2.append((loops[k][i][:2], loops[k + 1][i][:2]))
    for i in range(OC_SEG):
        edges2.append((last[i][:2], apex[:2]))
    base_loop = [(x, y) for x, y, _ in loops[0]]
    R = 75.0
    for sgn in (1.0, -1.0):
        for c in (-60.0, -30.0, 0.0, 30.0, 60.0):
            # lines (x - cx) - sgn (y - cy) = c, i.e. direction (1, sgn)/sqrt2, offset c/sqrt2 across
            ox, oy = c / 2.0, -sgn * c / 2.0
            ux, uy = 1 / math.sqrt(2), sgn / math.sqrt(2)
            p = (OC_DC[0] + ox - ux * R, OC_DC[1] + oy - uy * R)
            q = (OC_DC[0] + ox + ux * R, OC_DC[1] + oy + uy * R)
            _cable(vis, dome_tris, edges2, base_loop, p, q, 0.55, 0.12, "metal_gray")
    # crown hatch (checkpoint)
    hs, ht = OC_HATCH
    for bld in (vis, col):
        _box(bld, OC_DC[0] - hs, OC_DC[0] + hs, OC_DC[1] - hs, OC_DC[1] + hs, gz + OC_CROWN - 0.5, gz + ht,
             "metal_gray", faces="tnsew", mats={"t": "white_trim"})

    # ---------------------------------------------------------------- east stair up the skirt
    y0, y1 = lay["stair_y"]
    for s_ in lay["steps"]:
        for bld in (vis, col):
            _box(bld, s_["x0"], s_["x1"], y0, y1, gz + s_["z0"], gz + s_["z1"], "metal_gray", faces="tens")
    # handrails: one sloped bar per side, 1.0 m above the step noses (visual only, both faces)
    s_a, s_b = lay["steps"][0], lay["steps"][-1]
    for yy, sg in ((y0 + 0.05, -1), (y1 - 0.05, 1)):
        rail = [(s_a["x1"], yy, gz + s_a["z1"] + 0.85), (s_b["x1"] - 1.0, yy, gz + s_b["z1"] + 0.85),
                (s_b["x1"] - 1.0, yy, gz + s_b["z1"] + 1.0), (s_a["x1"], yy, gz + s_a["z1"] + 1.0)]
        uv = [(0, 0), (6, 0), (6, 0.1), (0, 0.1)]
        vis.poly(rail, "dark_trim", uvs=uv, normal_hint=(0, sg, 0))
        vis.poly(rail, "dark_trim", uvs=uv, normal_hint=(0, -sg, 0))

    # ---------------------------------------------------------------- grand entrance props
    can_p, can_h, can_z0, can_z1 = OC_CANOPY
    for bld in (vis, col):
        _box(bld, xf - 0.4, xf + can_p, yc - can_h, yc + can_h, gz + can_z0, gz + can_z1, "metal_gray",
             faces="tbens", mats={"t": "white_trim"})
    mq_p, mq_h, mq_z = OC_MARQUEE
    for bld in (vis, col):
        _box(bld, xf - 0.3, xf + mq_p, yc - mq_h, yc + mq_h, gz + can_z1, gz + mq_z, "dark_trim",
             faces="tens", mats={"t": "metal_gray"})
    # marquee face: a white sign panel with a dark lettering band (no sign texture in the palette)
    _box(vis, xf + mq_p, xf + mq_p + 0.05, yc - mq_h + 0.3, yc + mq_h - 0.3, gz + can_z1 + 0.3, gz + mq_z - 0.3,
         "white_trim", faces="e")
    _box(vis, xf + mq_p, xf + mq_p + 0.09, yc - mq_h + 0.9, yc + mq_h - 0.9, gz + can_z1 + 1.05, gz + mq_z - 1.05,
         "dark_trim", faces="e")
    kx0, kx1, ky0, ky1 = lay["kiosk"]
    for bld in (vis, col):
        _box(bld, kx0, kx1, ky0, ky1, gz, gz + OC_KIOSK_TOP, "concrete", faces="tnsew", mats={"t": "metal_gray"})
    _box(vis, kx1, kx1 + 0.04, ky0 + 0.4, ky1 - 0.4, gz + 1.0, gz + 2.0, "window_dark", faces="e")
    return vis, col, lay


# =================================================================== FLORIDA GYMNASIUM
GYM_ID = "w45719891"
G_FRONT = (-407.1, -359.8, 5.5, 17.1)
G_TOWER = (-390.7, -375.75, 4.55, 17.1)
G_HALL = (-402.7, -363.3, 17.1, 104.0)
G_WWING = [(-415.4, 50.8), (-407.05, 50.8), (-407.05, 47.1), (-402.7, 47.1), (-402.7, 104.0), (-415.4, 104.0)]
G_EWING = [(-363.3, 47.2), (-359.75, 47.2), (-359.75, 50.6), (-350.4, 50.6), (-350.4, 104.0), (-363.3, 104.0)]
G_ANNEX = (-406.9, -358.7, 104.0, 112.2)
G_NPAV = (-390.35, -375.5, 104.0, 113.2)
G_Z_LOW, G_Z_EAVE, G_Z_RIDGE = 9.6, 11.6, 16.6
G_Z_DECK, G_Z_TOWER, G_Z_PAV = 17.6, 18.4, 12.4
G_PAR = 0.45                       # tower parapet thickness
G_PIN = (1.1, 19.5, 20.9)          # pinnacle size, box top, pyramid apex
G_BUTTRESS = ((3.6, 2.4), (2.4, 4.8), (1.2, 7.2))     # (depth from the wall, top) outermost first
G_BUTTRESS_Y = (8.0, 14.6)
G_BANDS = ((0.0, 0.8, "limestone"), (0.8, 8.8, "brick_red"), (8.8, G_Z_LOW, "limestone"))


def _gym_layout():
    tx0, tx1, ty0, ty1 = G_TOWER
    tcx = (tx0 + tx1) / 2
    xr = (G_HALL[0] + G_HALL[1]) / 2
    fx1 = G_FRONT[1]
    route = [("buttress_1", (fx1 + 3.0, 11.3, G_BUTTRESS[0][1])), ("buttress_2", (fx1 + 1.8, 11.3, G_BUTTRESS[1][1])),
             ("buttress_3", (fx1 + 0.6, 11.3, G_BUTTRESS[2][1])), ("front_roof", (fx1 - 2.0, 14.0, G_Z_LOW)),
             ("hall_roof_se", (G_HALL[1] - 1.5, 19.0, G_Z_EAVE + 1.5 * (G_Z_RIDGE - G_Z_EAVE) / (xr - G_HALL[0]))),
             ("ridge_south", (xr, 19.0, G_Z_RIDGE)), ("tower_deck", (tcx, (ty0 + ty1) / 2, G_Z_DECK))]
    doors = [
        {"name": "DOOR_florida_gym_1", "pos_m": _r((tcx, ty0, 0.0)), "facing_deg": 180.0, "width_m": 4.0,
         "height_m": 6.0, "note": "main entrance in the central tower on Stadium Road (OSM entrance node "
                                  "4431930583); visual door leaf 0.8 m behind pos_m; not a stage door"},
        {"name": "DOOR_florida_gym_2", "pos_m": (-363.3, 19.25, 0.0), "facing_deg": 90.0, "width_m": 2.0,
         "height_m": 2.6, "note": "east door of the hall (OSM 4431930914); visual panel; not a stage door"},
        {"name": "DOOR_florida_gym_3", "pos_m": (-415.4, 63.27, 0.0), "facing_deg": 270.0, "width_m": 2.0,
         "height_m": 2.6, "note": "west wing door toward the stadium bridge (OSM 4431930913); visual panel"},
    ]
    spots = {
        "tower_deck": _r((tcx, (ty0 + ty1) / 2, G_Z_DECK)),
        "ridge_south": _r((xr, 19.0, G_Z_RIDGE)),
        "ridge_middle": _r((xr, 60.5, G_Z_RIDGE)),
        "ridge_north": _r((xr, 102.0, G_Z_RIDGE)),
        "front_roof_west": _r((-401.0, 11.3, G_Z_LOW)),
        "front_roof_east": _r((-366.0, 11.3, G_Z_LOW)),
        "west_wing_roof": _r((-409.0, 77.0, G_Z_LOW)),
        "east_wing_roof": _r((-356.8, 77.0, G_Z_LOW)),
        "north_annex_roof": _r((-398.0, 108.1, G_Z_LOW)),
        "north_pavilion_roof": _r(((G_NPAV[0] + G_NPAV[1]) / 2, 108.6, G_Z_PAV)),
        "entrance_steps": _r((tcx, ty0 - 2.0, 0.0)),
    }
    return {"route": route, "doors": doors, "spots": spots, "tcx": tcx, "xr": xr}


def _arch_chain(t0, t1, zs, rise, segs=3):
    """Two-centred pointed arch from (t0, zs) over the apex to (t1, zs)."""
    w = t1 - t0
    m = (t0 + t1) / 2
    r = (w * w / 4 + rise * rise) / w
    cr = t1 - r
    a_end = math.acos(max(-1.0, min(1.0, (m - cr) / r)))
    right = [(cr + r * math.cos(a_end * i / segs), zs + r * math.sin(a_end * i / segs)) for i in range(segs + 1)]
    left = [(2 * m - t, z) for t, z in right]
    return left + right[::-1][1:]


def _gym_windows(b, E, t0, t1, rows, w, h, gap=None, soldier=True):
    """Evenly spaced window decals along t0..t1 of the wall E; rows = sill heights."""
    span = t1 - t0
    n = max(1, int(span // (gap or (w + 2.2))))
    step = span / n
    for zr in rows:
        for k in range(n):
            tc = t0 + step * (k + 0.5)
            E.quad(b, tc - w / 2, tc + w / 2, zr, zr + h, "window_dark", off=0.04)
            if soldier:
                E.quad(b, tc - w / 2 - 0.15, tc + w / 2 + 0.15, zr + h, zr + h + 0.35, "brick_dark", off=0.04)


def _build_gym(ctx):
    lay = _gym_layout()
    fx0, fx1, fy0, fy1 = G_FRONT
    tx0, tx1, ty0, ty1 = G_TOWER
    hx0, hx1, hy0, hy1 = G_HALL
    ax0, ax1, ay0, ay1 = G_ANNEX
    px0, px1, py0, py1 = G_NPAV
    gz = ctx["ground_z"](lay["xr"], 55.0)
    vis, col = C.Builder(), C.Builder()
    xr = lay["xr"]
    half = (hx1 - hx0) / 2
    slope = (G_Z_RIDGE - G_Z_EAVE) / half

    def rake(x):
        return G_Z_RIDGE - abs(x - xr) * slope

    def banded(E, t0, t1):
        """limestone base course, brick, cast-stone cornice + parapet cap (two-storey blocks)"""
        for z0, z1, m in G_BANDS:
            E.quad(vis, t0, t1, z0, z1, m, max_len=VIS_MAX_LEN)

    # ---------------------------------------------------------------- front block (9.6 m)
    sW = Edge((fx0, fy0), (tx0, fy0), gz)          # south facade west of the tower
    sE = Edge((tx1, fy0), (fx1, fy0), gz)
    eF = Edge((fx1, fy0), (fx1, fy1), gz)
    wF = Edge((fx0, fy1), (fx0, fy0), gz)
    nW = Edge((hx0, fy1), (fx0, fy1), gz)          # exposed north strips
    nE = Edge((fx1, fy1), (hx1, fy1), gz)
    for E in (sW, sE, eF, wF, nW, nE):
        E.quad(col, 0.0, E.L, 0.0, G_Z_LOW, "brick_red")
        banded(E, 0.0, E.L)
    for x0_, x1_ in ((fx0, tx0), (tx1, fx1)):
        for bld in (vis, col):
            _flat(bld, [(x0_, fy0), (x1_, fy0), (x1_, fy1), (x0_, fy1)], gz + G_Z_LOW, "roof_dark")
    for E in (sW, sE):
        _gym_windows(vis, E, 0.6, E.L - 0.6, (1.5,), 1.6, 2.4)
        _gym_windows(vis, E, 0.6, E.L - 0.6, (5.6,), 1.6, 2.4, soldier=False)
    _gym_windows(vis, wF, 0.5, wF.L - 0.5, (1.5, 5.6), 1.6, 2.4, gap=6.0, soldier=False)   # east face: buttress
    # copper downspouts at the front corners
    for E, t in ((sW, 0.35), (sE, sE.L - 0.35)):
        E.quad(vis, t - 0.12, t + 0.12, 0.0, 8.8, "copper_green", off=0.1)

    # ---------------------------------------------------------------- entrance tower (18.4 m)
    tS = Edge((tx0, ty0), (tx1, ty0), gz)
    tE = Edge((tx1, ty0), (tx1, ty1), gz)
    tW = Edge((tx0, ty1), (tx0, ty0), gz)
    tN = Edge((tx1, ty1), (tx0, ty1), gz)
    for E in (tS, tE, tW):
        E.quad(col, 0.0, E.L, 0.0, G_Z_TOWER, "brick_red")
    tN.quad(col, 0.0, tN.L, G_Z_LOW, G_Z_TOWER, "brick_red")
    # south face with the arched entrance
    W = tS.L
    tc = W / 2
    o0, o1, zs, rise = tc - 2.0, tc + 2.0, 4.4, 2.3
    chain = _arch_chain(o0, o1, zs, rise)
    tS.quad(vis, 0.0, o0, 0.0, 0.8, "limestone")
    tS.quad(vis, o1, W, 0.0, 0.8, "limestone")
    tS.quad(vis, 0.0, o0, 0.8, 16.6, "brick_red")
    tS.quad(vis, o1, W, 0.8, 16.6, "brick_red")
    tS.poly(vis, chain + [(o1, 16.6), (o0, 16.6)], "brick_red")
    # recess: door leaf 0.8 m back, limestone reveals
    tS.poly(vis, [(o0, 0.0), (o1, 0.0)] + list(reversed(chain)), "door_wood", off=-0.8)
    outline = [(o0, 0.0)] + chain + [(o1, 0.0)]
    for (ta, za), (tb, zb) in zip(outline, outline[1:]):
        quad = [tS.p(ta, za, 0.0), tS.p(tb, zb, 0.0), tS.p(tb, zb, -0.8), tS.p(ta, za, -0.8)]
        et, ez = tb - ta, zb - za
        # reveal faces point into the opening (toward its axis)
        hint_t, hint_z = ez, -et
        vis.poly(quad, "limestone", normal_hint=(tS.d[0] * hint_t, tS.d[1] * hint_t, hint_z))
    # cast-stone surround (proud 0.06) and hood
    grow = 0.45
    ch2 = _arch_chain(o0 - grow, o1 + grow, zs, rise + grow * 0.9)
    for (ta, za), (tb, zb), (tc_, zc_), (td, zd) in zip(chain, chain[1:], ch2[1:], ch2):
        tS.poly(vis, [(ta, za), (tb, zb), (tc_, zc_), (td, zd)], "limestone", off=0.06)
    tS.quad(vis, o0 - grow, o0, 0.0, zs, "limestone", off=0.06)
    tS.quad(vis, o1, o1 + grow, 0.0, zs, "limestone", off=0.06)
    # lettering band FLORIDA GYMNASIUM (limestone panel with a dark incised strip)
    tS.quad(vis, tc - 4.6, tc + 4.6, 7.4, 8.6, "limestone", off=0.05)
    tS.quad(vis, tc - 4.1, tc + 4.1, 7.75, 8.25, "dark_trim", off=0.08)
    # tall pointed window with a limestone surround
    win = [(tc - 1.4, 9.4), (tc + 1.4, 9.4)] + list(reversed(_arch_chain(tc - 1.4, tc + 1.4, 14.0, 1.6, 2)))
    sur = [(tc - 1.8, 9.0), (tc + 1.8, 9.0)] + list(reversed(_arch_chain(tc - 1.8, tc + 1.8, 14.0, 2.0, 2)))
    tS.poly(vis, sur, "limestone", off=0.05)
    tS.poly(vis, win, "window_dark", off=0.08)
    tS.quad(vis, tc - 0.06, tc + 0.06, 9.4, 15.0, "limestone", off=0.1)
    # corner pilasters (cast stone quoin strips)
    for t0_ in (0.0, W - 0.7):
        tS.quad(vis, t0_, t0_ + 0.7, 0.8, 16.6, "limestone", off=0.05)
    # side faces: full height where they stand proud of the front block, above it elsewhere
    for E in (tE, tW):
        t_proud = fy0 - ty0
        if E is tE:
            E.quad(vis, 0.0, t_proud, 0.0, 0.8, "limestone")
            E.quad(vis, 0.0, t_proud, 0.8, G_Z_LOW, "brick_red")
            E.quad(vis, 0.0, E.L, G_Z_LOW, 16.6, "brick_red")
        else:
            E.quad(vis, E.L - t_proud, E.L, 0.0, 0.8, "limestone")
            E.quad(vis, E.L - t_proud, E.L, 0.8, G_Z_LOW, "brick_red")
            E.quad(vis, 0.0, E.L, G_Z_LOW, 16.6, "brick_red")
        tm = E.L / 2
        win_s = [(tm - 0.9, 11.0), (tm + 0.9, 11.0)] + list(reversed(_arch_chain(tm - 0.9, tm + 0.9, 14.2, 1.1, 2)))
        E.poly(vis, win_s, "window_dark", off=0.05)
    # north face above the hall roof (two triangles meeting at the ridge)
    tr = tx1 - xr   # t of the ridge on tN (t runs west)
    tN.poly(vis, [(0.0, rake(tx1)), (tr, 16.6), (0.0, 16.6)], "brick_red")
    tN.poly(vis, [(tr, 16.6), (tN.L, rake(tx0)), (tN.L, 16.6)], "brick_red")
    # cornice, parapet, cap on all four faces
    for E in (tS, tE, tW, tN):
        E.quad(vis, 0.0, E.L, 16.6, G_Z_DECK, "limestone")
        E.quad(vis, 0.0, E.L, G_Z_DECK, G_Z_TOWER - 0.2, "brick_red")
        E.quad(vis, 0.0, E.L, G_Z_TOWER - 0.2, G_Z_TOWER, "limestone")
    # deck, parapet inner faces and cap (visual + collision)
    ix0, ix1, iy0, iy1 = tx0 + G_PAR, tx1 - G_PAR, ty0 + G_PAR, ty1 - G_PAR
    inner = [(ix0, iy0), (ix1, iy0), (ix1, iy1), (ix0, iy1)]
    outer = [(tx0, ty0), (tx1, ty0), (tx1, ty1), (tx0, ty1)]
    for bld in (vis, col):
        _flat(bld, inner, gz + G_Z_DECK, "roof_dark")
        for i in range(4):
            a, c = inner[i], inner[(i + 1) % 4]
            mx, my = (a[0] + c[0]) / 2 - (ix0 + ix1) / 2, (a[1] + c[1]) / 2 - (iy0 + iy1) / 2
            bld.poly([(a[0], a[1], gz + G_Z_DECK), (c[0], c[1], gz + G_Z_DECK), (c[0], c[1], gz + G_Z_TOWER),
                      (a[0], a[1], gz + G_Z_TOWER)], "brick_red", normal_hint=(-mx, -my, 0))
            oa, oc = outer[i], outer[(i + 1) % 4]
            bld.poly([(oa[0], oa[1], gz + G_Z_TOWER), (oc[0], oc[1], gz + G_Z_TOWER), (c[0], c[1], gz + G_Z_TOWER),
                      (a[0], a[1], gz + G_Z_TOWER)], "limestone", normal_hint=(0, 0, 1))
    # corner pinnacles (box + pyramid; the pyramids slide)
    ps, pz, pa = G_PIN
    for cx_, cy_ in ((tx0, ty0), (tx1, ty0), (tx1, ty1), (tx0, ty1)):
        sx = 1 if cx_ == tx0 else -1
        sy = 1 if cy_ == ty0 else -1
        x0_, x1_ = sorted((cx_, cx_ + sx * ps))
        y0_, y1_ = sorted((cy_, cy_ + sy * ps))
        for bld in (vis, col):
            _box(bld, x0_, x1_, y0_, y1_, gz + G_Z_TOWER, gz + pz, "limestone", faces="nsew")
            _pyramid(bld, x0_ - (0.08 if bld is vis else 0), x1_ + (0.08 if bld is vis else 0),
                     y0_ - (0.08 if bld is vis else 0), y1_ + (0.08 if bld is vis else 0), gz + pz, gz + pa,
                     "limestone")

    # ---------------------------------------------------------------- the hall (gable N-S)
    hE = Edge((hx1, hy0), (hx1, hy1), gz)
    hW = Edge((hx0, hy1), (hx0, hy0), gz)
    for E in (hE, hW):
        E.quad(col, 0.0, E.L, 0.0, G_Z_EAVE, "brick_red")
    y_wing = 47.15   # wings start here (north of it the hall walls show only above 9.6)
    for E in (hE, hW):
        if E is hE:
            ta, tb = 0.0, y_wing - hy0          # exposed full height from the front block to the wing
        else:
            ta, tb = hy1 - y_wing, E.L
        E.quad(vis, ta, tb, 0.0, 0.8, "limestone", max_len=VIS_MAX_LEN)
        E.quad(vis, ta, tb, 0.8, G_Z_EAVE - 0.8, "brick_red", max_len=VIS_MAX_LEN)
        lo, hi = (tb, E.L) if E is hE else (0.0, ta)
        E.quad(vis, lo, hi, G_Z_LOW, G_Z_EAVE - 0.8, "brick_red", max_len=VIS_MAX_LEN)
        E.quad(vis, 0.0, E.L, G_Z_EAVE - 0.8, G_Z_EAVE, "limestone", max_len=VIS_MAX_LEN)
        # tall gym windows with soldier courses over shallow arches (UF PD&C feature list)
        _gym_windows(vis, E, ta + 1.5, tb - 1.5, (2.2,), 2.4, 6.6, gap=7.5)
        # clerestory row above the wing roofs
        _gym_windows(vis, E, lo + 2.0, hi - 2.0, (9.85,), 1.6, 0.85, gap=11.0, soldier=False)
        # copper downspouts
        for t in (ta + 0.3, tb - 0.3):
            E.quad(vis, t - 0.12, t + 0.12, 0.0, G_Z_EAVE - 0.8, "copper_green", off=0.1)
    # gable walls above the low roofs (south: either side of the tower; north: full)
    gS_W = Edge((hx0, hy0), (tx0, hy0), gz)      # faces south, t runs east to the tower
    gS_E = Edge((tx1, hy0), (hx1, hy0), gz)      # faces south, t runs east from the tower
    for bld in (col, vis):
        gS_W.poly(bld, [(0.0, G_Z_LOW), (gS_W.L, G_Z_LOW), (gS_W.L, rake(tx0)), (0.0, G_Z_EAVE)], "brick_red")
        gS_E.poly(bld, [(0.0, G_Z_LOW), (gS_E.L, G_Z_LOW), (gS_E.L, G_Z_EAVE), (0.0, rake(tx1))], "brick_red")
    gN = Edge((hx1, hy1), (hx0, hy1), gz)          # faces north, t runs west
    gprof = [(0.0, G_Z_LOW), (gN.L, G_Z_LOW), (gN.L, G_Z_EAVE), (gN.L / 2, G_Z_RIDGE), (0.0, G_Z_EAVE)]
    gN.poly(col, gprof, "brick_red")
    gN.poly(vis, [(0.0, G_Z_LOW), (gN.L / 2, G_Z_LOW), (gN.L / 2, G_Z_RIDGE), (0.0, G_Z_EAVE)], "brick_red")
    gN.poly(vis, [(gN.L / 2, G_Z_LOW), (gN.L, G_Z_LOW), (gN.L, G_Z_EAVE), (gN.L / 2, G_Z_RIDGE)], "brick_red")
    # gable vent (round-headed louvre) on the north gable, above the pavilion
    tv = gN.L / 2
    gN.poly(vis, [(tv - 1.0, 12.8), (tv + 1.0, 12.8)] + list(reversed(_arch_chain(tv - 1.0, tv + 1.0, 13.9, 1.2, 2))),
            "window_dark", off=0.05)
    # rake copings (cast stone, visual): south pieces and north gable
    for E, pts in ((gS_W, [(0.0, G_Z_EAVE), (gS_W.L, rake(tx0))]), (gS_E, [(0.0, rake(tx1)), (gS_E.L, G_Z_EAVE)]),
                   (gN, [(0.0, G_Z_EAVE), (gN.L / 2, G_Z_RIDGE), (gN.L, G_Z_EAVE)])):
        for (ta, za), (tb, zb) in zip(pts, pts[1:]):
            E.poly(vis, [(ta, za - 0.35), (tb, zb - 0.35), (tb, zb + 0.3), (ta, za + 0.3)], "limestone", off=0.06)
            vis.poly([E.p(ta, za + 0.3, 0.06), E.p(tb, zb + 0.3, 0.06), E.p(tb, zb + 0.3, -0.4), E.p(ta, za + 0.3, -0.4)],
                     "limestone", normal_hint=(0, 0, 1))
    # roof: two 14-degree slopes, split along the length
    ys = _cuts(hy0, hy1, 30.0)
    for ya, yb in zip(ys, ys[1:]):
        for side in (-1, 1):
            xe = hx0 if side < 0 else hx1
            pts = [(xe, ya, gz + G_Z_EAVE), (xe, yb, gz + G_Z_EAVE), (xr, yb, gz + G_Z_RIDGE), (xr, ya, gz + G_Z_RIDGE)]
            if side > 0:
                pts = [pts[1], pts[0], pts[3], pts[2]]
            col.poly(pts, "roof_dark", normal_hint=(side, 0, 3))
            for yc_, yd_ in zip(_cuts(ya, yb, VIS_MAX_LEN), _cuts(ya, yb, VIS_MAX_LEN)[1:]):
                q = [(xe, yc_, gz + G_Z_EAVE), (xe, yd_, gz + G_Z_EAVE), (xr, yd_, gz + G_Z_RIDGE),
                     (xr, yc_, gz + G_Z_RIDGE)]
                vis.poly(q, "roof_dark", normal_hint=(side, 0, 3))
    # ridge cap and eave fascias (visual)
    ruv = [(0, 0), (0.15, 0), (0.15, 4.0), (0, 4.0)]
    vis.poly([(xr - 0.3, hy0, gz + G_Z_RIDGE - 0.07), (xr, hy0, gz + G_Z_RIDGE + 0.1), (xr, hy1, gz + G_Z_RIDGE + 0.1),
              (xr - 0.3, hy1, gz + G_Z_RIDGE - 0.07)], "metal_gray", uvs=ruv, normal_hint=(-1, 0, 3))
    vis.poly([(xr, hy0, gz + G_Z_RIDGE + 0.1), (xr + 0.3, hy0, gz + G_Z_RIDGE - 0.07),
              (xr + 0.3, hy1, gz + G_Z_RIDGE - 0.07), (xr, hy1, gz + G_Z_RIDGE + 0.1)], "metal_gray", uvs=ruv,
             normal_hint=(1, 0, 3))

    # ---------------------------------------------------------------- side wings + north annex (9.6 m)
    for wing in (G_WWING, G_EWING):
        nwp = len(wing)
        for i in range(nwp):
            a, c = wing[i], wing[(i + 1) % nwp]
            if abs(a[0] - c[0]) < 1e-6 and abs(a[0] - (hx0 if wing is G_WWING else hx1)) < 1e-6:
                continue   # hall side
            E = Edge(a, c, gz)
            E.quad(col, 0.0, E.L, 0.0, G_Z_LOW, "brick_red")
            banded(E, 0.0, E.L)
            if E.L > 30.0:   # paired 12-light sliders, one decal per pair
                _gym_windows(vis, E, 1.0, E.L - 1.0, (1.4, 5.5), 3.0, 2.3, gap=7.4, soldier=False)
            elif E.L > 12.0:
                _gym_windows(vis, E, 1.5, E.L - 1.5, (5.5,), 1.5, 2.3, gap=4.6, soldier=False)
        col.poly([(x, y, gz + G_Z_LOW) for x, y in wing], "roof_dark", normal_hint=(0, 0, 1))
        # visual roof as rectangles (the L-shaped polygon would span too many texture repeats)
        if wing is G_WWING:
            rects = ((-415.4, -402.7, 50.8, 104.0), (-407.05, -402.7, 47.1, 50.8))
        else:
            rects = ((-363.3, -350.4, 50.6, 104.0), (-363.3, -359.75, 47.2, 50.6))
        for x0_, x1_, y0_, y1_ in rects:
            _rect_grid(vis, x0_, x1_, y0_, y1_, gz + G_Z_LOW, "roof_dark")
    # west wing door + east hall door (visual panels)
    Ew = Edge(G_WWING[5], G_WWING[0], gz)
    tdw = Ew.L - (63.27 - G_WWING[0][1])
    Ew.quad(vis, tdw - 1.0, tdw + 1.0, 0.0, 2.6, "door_wood", off=0.05)
    Ew.quad(vis, tdw - 1.3, tdw + 1.3, 2.6, 3.0, "limestone", off=0.05)
    hE.quad(vis, 19.25 - hy0 - 1.0, 19.25 - hy0 + 1.0, 0.0, 2.6, "door_wood", off=0.05)
    hE.quad(vis, 19.25 - hy0 - 1.3, 19.25 - hy0 + 1.3, 2.6, 3.0, "limestone", off=0.05)
    # north annex
    aN_E = Edge((ax1, ay1), (px1, ay1), gz)
    aN_W = Edge((px0, ay1), (ax0, ay1), gz)
    aE = Edge((ax1, ay0), (ax1, ay1), gz)
    aW = Edge((ax0, ay1), (ax0, ay0), gz)
    for E in (aN_E, aN_W, aE, aW):
        E.quad(col, 0.0, E.L, 0.0, G_Z_LOW, "brick_red")
        banded(E, 0.0, E.L)
    for E in (aN_E, aN_W):
        _gym_windows(vis, E, 0.8, E.L - 0.8, (1.4, 5.5), 1.6, 2.3, gap=5.4, soldier=False)
    for x0_, x1_ in ((ax0, px0), (px1, ax1)):
        for bld in (vis, col):
            _flat(bld, [(x0_, ay0), (x1_, ay0), (x1_, ay1), (x0_, ay1)], gz + G_Z_LOW, "roof_dark")
    # north pavilion (12.4 m) with an entrance
    pN = Edge((px1, py1), (px0, py1), gz)
    pE = Edge((px1, py0), (px1, py1), gz)
    pW = Edge((px0, py1), (px0, py0), gz)
    for E in (pN, pE, pW):
        E.quad(col, 0.0, E.L, 0.0, G_Z_PAV, "brick_red")
        E.quad(vis, 0.0, E.L, 0.0, 0.8, "limestone")
        E.quad(vis, 0.0, E.L, 0.8, G_Z_PAV - 0.7, "brick_red")
        E.quad(vis, 0.0, E.L, G_Z_PAV - 0.7, G_Z_PAV, "limestone")
    for bld in (vis, col):
        _flat(bld, [(px0, py0), (px1, py0), (px1, py1), (px0, py1)], gz + G_Z_PAV, "roof_dark")
    tp = pN.L / 2
    pN.poly(vis, [(tp - 1.6, 0.0), (tp + 1.6, 0.0)] + list(reversed(_arch_chain(tp - 1.6, tp + 1.6, 3.4, 1.9, 2))),
            "door_wood", off=0.05)
    pN.poly(vis, [(tp - 1.2, 5.6), (tp + 1.2, 5.6)] + list(reversed(_arch_chain(tp - 1.2, tp + 1.2, 9.4, 1.4, 2))),
            "window_dark", off=0.05)

    # ---------------------------------------------------------------- stepped buttress (climb)
    by0, by1 = G_BUTTRESS_Y
    for d, ztop in G_BUTTRESS:
        for bld in (vis, col):
            _box(bld, fx1 - 0.3, fx1 + d, by0, by1, gz, gz + ztop, "brick_red", faces="tnse",
                 mats={"t": "limestone"})
    return vis, col, lay


# =================================================================== contract
_OL = _oc_layout()
_GL = _gym_layout()

LANDMARKS = [
    {
        "slug": "oconnell_center",
        "name": "Exactech Arena at the Stephen C. O'Connell Center",
        "osm_ids": [OC_ID],
        "replaces_areas": [OC_COURT_AREA],
        "stages": list(STAGES),
        "center_m": (-753.96, 67.24),       # OSM footprint centroid
        "height_m": OC_CROWN,
        "doors": _OL["doors"],
        "spots": _OL["spots"],
        "climb_route_m": [p for _, p in _OL["route"]],
        "top_platform": {"z_m": OC_HATCH[1], "center_m": _r(OC_DC), "half_m": OC_HATCH[0],
                         "note": "crown hatch on the 5-degree dome cap (cap walkable out to ~27 m radius); "
                                 "the 45-47 degree skirt below 20.6 m slides back to the 10.5 m perimeter roof"},
    },
    {
        "slug": "florida_gym",
        "name": "Florida Gymnasium (Alligator Alley)",
        "osm_ids": [GYM_ID],
        "stages": list(STAGES),
        "center_m": (-383.02, 62.75),       # OSM footprint centroid
        "height_m": G_Z_TOWER,
        "doors": _GL["doors"],
        "spots": _GL["spots"],
        "climb_route_m": [p for _, p in _GL["route"]],
        "top_platform": {"z_m": G_Z_DECK, "center_m": _GL["spots"]["tower_deck"][:2],
                         "note": "14.1 x 11.6 m tower deck inside a 0.8 m parapet; the hall ridge (16.6 m) "
                                 "meets the tower's north face"},
    },
]


def _check_footprint(ctx, osm_id, ref_pts, label):
    try:
        fp = C.footprint(ctx, osm_id)
    except KeyError:
        print(f"swamp_oconnell_gym: WARNING {label} ({osm_id}) not in campus.json")
        return
    if not all(any(math.dist(p, q) < 0.05 for q in fp) for p in ref_pts):
        print(f"swamp_oconnell_gym: WARNING {label} footprint changed in campus.json")


def build(ctx):
    """-> [{"name", "mesh", "material_slots", "collision", "visual", "landmark"}, ...] (map metres, z up)."""
    if "ground_z" not in ctx:
        ctx = dict(ctx, ground_z=lambda x, y: 0.0)
    key = ctx.get("stage_key")
    if key is not None and key not in STAGES:
        return []
    _check_footprint(ctx, OC_ID, [(-719.64, 5.9), (-679.36, 67.87), (-737.62, 137.12), (-825.74, 39.31)],
                     "O'Connell Center")
    _check_footprint(ctx, GYM_ID, [(-383.09, 4.61), (-415.89, 50.79), (-350.25, 103.63), (-406.85, 112.26)],
                     "Florida Gym")
    parts = []
    o_vis, o_col, _ = _build_oconnell(ctx)
    g_vis, g_col, _ = _build_gym(ctx)
    for slug, vis, col in (("oconnell_center", o_vis, o_col), ("florida_gym", g_vis, g_col)):
        me, slots = vis.build(f"{slug} visual")
        p = C.part(f"{slug} visual", me, slots, collision=False, visual=True)
        p["landmark"] = slug
        parts.append(p)
        me, slots = col.build(f"{slug} collision")
        p = C.part(f"{slug} collision", me, slots, collision=True, visual=False)
        p["landmark"] = slug
        parts.append(p)
        print(f"swamp_oconnell_gym: {slug}: visual {vis.tri_count()} tris, collision {col.tri_count()} tris")
    return parts
