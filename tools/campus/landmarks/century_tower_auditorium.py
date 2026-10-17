"""Century Tower + University Auditorium: hand-modelled hub landmarks for Super Gatorlator 64.

Landmark module contract (see landmarks/_common.py): LANDMARKS + build(ctx). Geometry is authored
in MAP METRES, z up (x = east, y = north, origin = Century Tower centroid) on top of the exact OSM
footprints in data/uf/campus.json; the generator moves it into the stage frame.

CENTURY TOWER (OSM w150860043, 9.23 x 9.40 m, 47.9 m)
  Red-brick shaft with full-height corner piers and a recessed bay on each face (darker brick),
  limestone base course / string courses / alternating quoins, a pointed-arch door on the north
  face (stage door) and one on the west face ("FINAL EXAM" door), staggered stair lancets, a clock
  on every face (the design doc's progress meter), a belfry stage with two louvred lancets per
  face, a projecting limestone cornice, a parapet with four corner pinnacle turrets, and a steep
  copper-green pyramid with a finial (apex 47.9 m = published 157 ft).
  Climb: 18 limestone stations spiral clockwise up the outside (corner set-offs projecting 1.3 m
  and centred face ledges projecting 1.55 m, 2.2 m apart in height, 1.4 m apart horizontally):
  ground -> 0.9 m step -> 2.0 m NW corner block -> N door canopy (4.2 m) -> ... -> 39.4 m N ledge
  under the cornice -> double jump or ledge-grab onto the 0.65 m parapet (42.2 m) -> top deck
  (41.2 m), a ~1.6 m walkway ring around the pyramid (the finale's "top platform").
  A moving single jump (~2.9 m) or a double jump (~3.6 m) clears every step; no ledge is directly
  above another within 17 m, and none overhangs the doors, clocks or belfry lancets.

UNIVERSITY AUDITORIUM (OSM w154223635, 1922-24 Collegiate Gothic + 1977 additions, ridge 18 m)
  Read from the footprint and the OSM entrance nodes: a cruciform hall (N-S nave + E-W transept,
  42-degree red-tile roofs, ridges at 18 m, the transept gable ends hold the two big traceried
  windows), single-storey arcaded lobbies along the west and east fronts (doors at the OSM
  entrance nodes), flat-roofed 1977 corner blocks and stage block (9.0 m), and the 1977 north
  wing with a parapeted front gable, a big traceried window, corner turrets and the three-door
  polygonal porch facing the Plaza of the Americas (the hub's stage door).
  Traversal: stepped buttresses -> porch roof (5.2 m) and arcade roofs (5.2 m) -> transept
  buttress blocks (7.1 m) -> flat roofs (9.0 m); a stair buttress -> the walkable 33-degree
  north-wing roof (ridge 18 m). The steep hall roofs slide (Wing Cap territory).
  OSM building:part w863677836 (a 4.9 m "stone tower", 57.9 m) inside the hall is listed in
  osm_ids so the generator never builds it (no such tower exists; the 190 ft tower of the 1920s
  plan was never built).

Parts returned by build(): <slug> visual (visual only) and <slug> collision (collision only) for
each landmark. Collision is closed where Mario can reach it, walls face out of the solids, and no
collision face is larger than ~17 m. Budgets (stages.json hub landmarks): tower 450 col / 1600 vis,
auditorium 300 col / 1200 vis; build() prints the counts.

Reference used (cite): Wikipedia "Century Tower (University of Florida)" (157 ft / 48 m, modified
Collegiate Gothic after Canterbury's Bell Harry Tower, 61-bell carillon, 1953-56); Wikipedia
"University Auditorium (Gainesville, Florida)" (Edwards 1922-24, cruciform plan, hammerbeam roof,
large windows over the east and west transept balconies, 1977 McGinley additions with new
entrances/lobbies/stage dressing rooms); UF Archives page web.uflib.ufl.edu/ufarch/xauditorium.htm
(large arched windows with tracery, spires, unbuilt 190 ft tower); OSM ways 150860043, 154223635,
863677836 and entrance nodes 5626051050, 8064445591, 8064445593-8064445596.
"""
import math
import os
import sys

try:
    from landmarks import _common as C
except ImportError:  # imported as a top-level module: make the `landmarks` package importable
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from landmarks import _common as C

EPS = 1e-6

TOWER_ID = "w150860043"
AUD_ID = "w154223635"
AUD_PART_ID = "w863677836"

# campus.json footprints (used for LANDMARKS at import time; build() re-reads campus.json)
TOWER_FP = [(3.68, 3.78), (3.72, -5.63), (-5.51, -5.66), (-5.55, 3.73)]


# =================================================================== small geometry helpers
class Frame:
    """Local (u, v, z) -> map (x, y, z): origin + u * ex + v * ey, ey = ex rotated +90 degrees."""

    def __init__(self, origin=(0.0, 0.0), ex=(1.0, 0.0), z0=0.0):
        L = math.hypot(ex[0], ex[1])
        self.ex = (ex[0] / L, ex[1] / L)
        self.ey = (-self.ex[1], self.ex[0])
        self.o = (float(origin[0]), float(origin[1]))
        self.z0 = float(z0)

    def p(self, u, v, z=0.0):
        return (self.o[0] + u * self.ex[0] + v * self.ey[0],
                self.o[1] + u * self.ex[1] + v * self.ey[1], self.z0 + z)

    def d(self, du, dv, dz=0.0):
        return (du * self.ex[0] + dv * self.ey[0], du * self.ex[1] + dv * self.ey[1], dz)

    def bearing(self, du, dv):
        x, y, _ = self.d(du, dv)
        return math.degrees(math.atan2(x, y)) % 360.0


def poly(b, F, pts, mat, hint):
    """Polygon from local (u, v, z) points; `hint` = local direction the face should look at."""
    b.poly([F.p(*q) for q in pts], mat, normal_hint=F.d(*hint))


def box(b, F, u0, u1, v0, v1, z0, z1, mat, faces="tbnsew", mats=None):
    """Axis-aligned box in the frame; `faces` picks t(op) b(ottom) n(+v) s(-v) e(+u) w(-u)."""
    mats = mats or {}
    u0, u1 = sorted((u0, u1))
    v0, v1 = sorted((v0, v1))
    if "t" in faces:
        poly(b, F, [(u0, v0, z1), (u1, v0, z1), (u1, v1, z1), (u0, v1, z1)], mats.get("t", mat), (0, 0, 1))
    if "b" in faces:
        poly(b, F, [(u0, v0, z0), (u1, v0, z0), (u1, v1, z0), (u0, v1, z0)], mats.get("b", mat), (0, 0, -1))
    if "s" in faces:
        poly(b, F, [(u0, v0, z0), (u1, v0, z0), (u1, v0, z1), (u0, v0, z1)], mats.get("s", mat), (0, -1, 0))
    if "n" in faces:
        poly(b, F, [(u0, v1, z0), (u1, v1, z0), (u1, v1, z1), (u0, v1, z1)], mats.get("n", mat), (0, 1, 0))
    if "e" in faces:
        poly(b, F, [(u1, v0, z0), (u1, v1, z0), (u1, v1, z1), (u1, v0, z1)], mats.get("e", mat), (1, 0, 0))
    if "w" in faces:
        poly(b, F, [(u0, v0, z0), (u0, v1, z0), (u0, v1, z1), (u0, v0, z1)], mats.get("w", mat), (-1, 0, 0))


def pyramid(b, F, cu, cv, hu, hv, z0, z1, mat, apex=None):
    """Four-sided pyramid on the rectangle (cu +- hu, cv +- hv) at z0 with its apex at z1."""
    A = (cu, cv, z1) if apex is None else apex
    cs = [(cu - hu, cv - hv), (cu + hu, cv - hv), (cu + hu, cv + hv), (cu - hu, cv + hv)]
    for i in range(4):
        p, q = cs[i], cs[(i + 1) % 4]
        mu, mv = (p[0] + q[0]) / 2 - cu, (p[1] + q[1]) / 2 - cv
        poly(b, F, [(p[0], p[1], z0), (q[0], q[1], z0), A], mat, (mu, mv, 0.25 * (abs(mu) + abs(mv))))


def splits(a, b, max_len):
    n = max(1, int(math.ceil((b - a) / max_len - 1e-9)))
    return [a + (b - a) * i / n for i in range(n + 1)]


class Opening:
    """Wall opening in wall coordinates (t along the wall, z up): a rectangle t0..t1 x zb..zs
    topped by a two-centred pointed arch rising `rise` above the springing line zs."""

    def __init__(self, t0, t1, zb, zs, rise=0.0, segs=2):
        self.t0, self.t1, self.zb, self.zs, self.rise, self.segs = t0, t1, zb, zs, rise, segs
        w = t1 - t0
        if rise > EPS and rise <= w / 2 + 1e-4:
            raise ValueError("pointed arch needs rise > half the width")

    @property
    def apex(self):
        return self.zs + self.rise

    def chain(self, grow=0.0):
        """Upper outline from the left springing point to the right one, radii grown by `grow`."""
        t0, t1, zs = self.t0, self.t1, self.zs
        if self.rise <= EPS:
            return [(t0 - grow, zs + grow), (t1 + grow, zs + grow)]
        w = t1 - t0
        m = (t0 + t1) / 2
        r = (w * w / 4 + self.rise * self.rise) / w
        cr = t1 - r                 # centre of the right-hand arc (on the springing line)
        R = r + grow
        a_end = math.acos(max(-1.0, min(1.0, (m - cr) / R)))
        right = [(cr + R * math.cos(a_end * i / self.segs), zs + R * math.sin(a_end * i / self.segs))
                 for i in range(self.segs + 1)]          # right springing -> apex
        left = [(2 * m - t, z) for t, z in right]        # left springing -> apex (mirror)
        return left + right[::-1][1:]                    # left springing -> apex -> right springing

    def outline(self):
        """Counter-clockwise outline (seen from outside)."""
        pts = [(self.t0, self.zb), (self.t1, self.zb)] + list(reversed(self.chain()))
        out = []
        for p in pts:
            if not out or abs(p[0] - out[-1][0]) > 1e-5 or abs(p[1] - out[-1][1]) > 1e-5:
                out.append(p)
        if abs(out[0][0] - out[-1][0]) < 1e-5 and abs(out[0][1] - out[-1][1]) < 1e-5:
            out.pop()
        return out


class Wall:
    """A vertical wall plane over the local segment a -> b (outside on the right of a -> b, i.e.
    a counter-clockwise footprint edge). Wall coordinates: t (0..L along a -> b, increasing to the
    viewer's right when seen from outside), z up, off (+ = outward)."""

    def __init__(self, F, a, b):
        self.F = F
        self.a = a
        dx, dy = b[0] - a[0], b[1] - a[1]
        self.L = math.hypot(dx, dy)
        self.dv = (dx / self.L, dy / self.L)
        self.n = (self.dv[1], -self.dv[0])

    def p(self, t, z, off=0.0):
        return self.F.p(self.a[0] + self.dv[0] * t + self.n[0] * off,
                        self.a[1] + self.dv[1] * t + self.n[1] * off, z)

    def hint(self, ht=0.0, hz=0.0, ho=1.0):
        return self.F.d(self.dv[0] * ht + self.n[0] * ho, self.dv[1] * ht + self.n[1] * ho, hz)

    def poly(self, b, pts_tz, mat, off=0.0, hint=(0.0, 0.0, 1.0)):
        b.poly([self.p(t, z, off) for t, z in pts_tz], mat, normal_hint=self.hint(*hint))

    def bearing(self):
        x, y, _ = self.F.d(self.n[0], self.n[1])
        return math.degrees(math.atan2(x, y)) % 360.0


def wall_surface(b, W, z0, top, mat, openings=(), max_w=12.0, t_range=None):
    """Fill the wall from z0 up to `top` (a height, or a profile [(t, z), ...] covering t_range)
    minus `openings` (each must either cover the whole band or have its arch head inside it)."""
    ta, tb = t_range or (0.0, W.L)
    prof = [(ta, top), (tb, top)] if isinstance(top, (int, float)) else list(top)

    def ztop(t):
        for (t1, z1), (t2, z2) in zip(prof, prof[1:]):
            if t1 - EPS <= t <= t2 + EPS:
                return z1 if t2 - t1 < EPS else z1 + (z2 - z1) * (t - t1) / (t2 - t1)
        return prof[0][1] if t < prof[0][0] else prof[-1][1]

    def inner(s0, s1):
        return [(t, z) for t, z in prof if s0 + 1e-4 < t < s1 - 1e-4]

    def strip(s0, s1):
        if s1 - s0 < 1e-4:
            return
        cuts = splits(s0, s1, max_w)
        for a0, a1 in zip(cuts, cuts[1:]):
            pts = [(a0, z0), (a1, z0), (a1, ztop(a1))] + list(reversed(inner(a0, a1))) + [(a0, ztop(a0))]
            W.poly(b, pts, mat)

    cur = ta
    for o in sorted(openings, key=lambda o: o.t0):
        zt = min(ztop(o.t0), ztop(o.t1))
        if o.zb >= zt - EPS or o.apex <= z0 + EPS or o.t1 <= ta or o.t0 >= tb:
            continue  # opening not in this band
        strip(cur, o.t0)
        if o.zb > z0 + EPS:
            W.poly(b, [(o.t0, z0), (o.t1, z0), (o.t1, o.zb), (o.t0, o.zb)], mat)
        if o.zs < zt - EPS:  # the head is in this band: fill above the arch
            ch = o.chain()
            if o.zs < z0 - EPS or any(z > ztop(t) + EPS for t, z in ch):
                raise ValueError("arch head crosses a band boundary")
            pts = ch + [(o.t1, ztop(o.t1))] + list(reversed(inner(o.t0, o.t1))) + [(o.t0, ztop(o.t0))]
            W.poly(b, pts, mat)
        cur = o.t1
    strip(cur, tb)


def recess(b, W, o, depth, back_mat, side_mat, skip_bottom=False):
    """Reveals + back panel of an opening cut `depth` into the wall."""
    out = o.outline()
    W.poly(b, out, back_mat, off=-depth)
    n = len(out)
    for i in range(n):
        p, q = out[i], out[(i + 1) % n]
        if skip_bottom and i == 0:
            continue
        et, ez = q[0] - p[0], q[1] - p[1]
        b.poly([W.p(p[0], p[1], 0.0), W.p(q[0], q[1], 0.0), W.p(q[0], q[1], -depth), W.p(p[0], p[1], -depth)],
               side_mat, normal_hint=W.hint(-ez, et, 0.0))


def arch_frame(b, W, o, g, mat, off=0.05, jambs=True):
    """Proud surround (hood mould + jambs) of width g around an opening."""
    c0, c1 = o.chain(0.0), o.chain(g)
    for i in range(len(c0) - 1):
        W.poly(b, [c0[i], c0[i + 1], c1[i + 1], c1[i]], mat, off=off)
    if jambs and o.zs > o.zb + EPS:
        W.poly(b, [(o.t0 - g, o.zb), (o.t0, o.zb), (o.t0, o.zs), (o.t0 - g, o.zs)], mat, off=off)
        W.poly(b, [(o.t1, o.zb), (o.t1 + g, o.zb), (o.t1 + g, o.zs), (o.t1, o.zs)], mat, off=off)


def decal(b, W, pts_tz, mat, off=0.04):
    W.poly(b, pts_tz, mat, off=off)


def coping(b, W, z, h=0.3, depth=0.3, mat="limestone", max_len=12.0):
    """Inner face + top of a parapet coping running along the whole wall (visual)."""
    cuts = splits(0.0, W.L, max_len)
    for ta, tb in zip(cuts, cuts[1:]):
        b.poly([W.p(ta, z, -depth), W.p(tb, z, -depth), W.p(tb, z + h, -depth), W.p(ta, z + h, -depth)], mat,
               normal_hint=W.hint(0, 0, -1))
        b.poly([W.p(ta, z + h, 0), W.p(tb, z + h, 0), W.p(tb, z + h, -depth), W.p(ta, z + h, -depth)], mat,
               normal_hint=(0, 0, 1))


def flat_rect(b, F, x0, x1, y0, y1, z, mat, max_len=12.0, up=True):
    xs, ys = splits(x0, x1, max_len), splits(y0, y1, max_len)
    for xa, xb in zip(xs, xs[1:]):
        for ya, yb in zip(ys, ys[1:]):
            poly(b, F, [(xa, ya, z), (xb, ya, z), (xb, yb, z), (xa, yb, z)], mat, (0, 0, 1 if up else -1))


def wall_disk(b, W, tc, zc, r, n, mat, off):
    W.poly(b, [(tc + r * math.cos(2 * math.pi * i / n), zc + r * math.sin(2 * math.pi * i / n))
               for i in range(n)], mat, off=off)


def gable_roof(b, F, x0, x1, y0, y1, ze, zr, along, mat, oh=0.0, thick=0.0, ends=(False, False),
               edge_mat="dark_trim", max_len=12.0, end_oh=0.0, soffit=False):
    """Gable roof over the frame rectangle x0..x1 x y0..y1 (u, v), ridge parallel to `along`
    ("x" = u or "y" = v), eaves at ze, ridge at zr. oh: eave overhang; thick > 0 adds fascia,
    soffits and (ends[i]) rake edges; end_oh extends the slopes past the ends whose ends[i] is True."""
    if along == "x":
        a0, a1, c0, c1 = x0, x1, y0, y1

        def m(a, c, z):
            return (a, c, z)
    else:
        a0, a1, c0, c1 = y0, y1, x0, x1

        def m(a, c, z):
            return (c, a, z)
    cm = (c0 + c1) / 2
    s = (zr - ze) / ((c1 - c0) / 2)
    zo = ze - oh * s
    ea0 = a0 - (end_oh if ends[0] else 0.0)
    ea1 = a1 + (end_oh if ends[1] else 0.0)
    cuts = splits(ea0, ea1, max_len)
    for side, ce in ((-1, c0 - oh), (1, c1 + oh)):
        for p, q in zip(cuts, cuts[1:]):
            pts = [m(p, ce, zo), m(q, ce, zo), m(q, cm, zr), m(p, cm, zr)]
            poly(b, F, pts, mat, m(0, side, 1.0))
            if thick > 0:
                poly(b, F, [m(p, ce, zo - thick), m(q, ce, zo - thick), m(q, ce, zo), m(p, ce, zo)],
                     edge_mat, m(0, side, 0))
                if oh > 0 and soffit:
                    cw = c0 if side < 0 else c1
                    poly(b, F, [m(p, ce, zo - thick), m(q, ce, zo - thick), m(q, cw, ze - thick), m(p, cw, ze - thick)],
                         edge_mat, m(0, -side, -1.0))
    if thick > 0:
        for i, (ae, on) in enumerate(((ea0, ends[0]), (ea1, ends[1]))):
            if not on:
                continue
            sgn = -1 if i == 0 else 1
            prof = [m(ae, c0 - oh, zo), m(ae, cm, zr), m(ae, c1 + oh, zo),
                    m(ae, c1 + oh, zo - thick), m(ae, cm, zr - thick), m(ae, c0 - oh, zo - thick)]
            poly(b, F, prof, edge_mat, m(sgn, 0, 0))
            if end_oh > 0:  # underside of the slopes beyond the gable wall
                aw = a0 if i == 0 else a1
                for ce in (c0 - oh, c1 + oh):
                    poly(b, F, [m(ae, ce, zo - thick), m(aw, ce, zo - thick), m(aw, cm, zr - thick),
                                m(ae, cm, zr - thick)], edge_mat, m(0, 0, -1.0))


def flat(b, F, pts2, z, mat, up=True):
    poly(b, F, [(u, v, z) for u, v in pts2], mat, (0, 0, 1 if up else -1))


# =================================================================== CENTURY TOWER
T_PIER = 1.5          # corner pier width along each face
T_BAY = 0.45          # bay recess depth
T_SHAFT = 40.4        # top of the shaft (cornice starts)
T_DECK = 41.2         # top deck floor
T_PARAPET = 42.2      # parapet / coping top
T_PAR_W = 0.65        # parapet thickness (>= 0.6 so ledge-grab finds the parapet top, not the deck)
T_CORNICE = 0.15      # visual cornice projection
T_APEX = 47.1         # pyramid apex (finial to 47.9)
T_HEIGHT = 47.9
T_PYR = 2.35          # pyramid half size (leaves a ~1.6 m walkway)
T_TURRET = 1.3        # pinnacle turret size
LEDGE_HALF = 1.5      # face ledge half length
LEDGE_OUT = 1.1       # face ledge projection beyond the pier faces (1.55 m from the bay wall)
LEDGE_T = 0.5         # ledge slab thickness
CORBEL = 0.7          # visual corbel depth under face ledges
CORNER_IN = 1.75      # corner platform reach back along the faces
CORNER_OUT = 1.3      # corner platform projection beyond the pier faces (Mario keeps 0.5 m off walls)
ST_Z0, ST_DZ, ST_N = 2.0, 2.2, 18
ST_ORDER = ("NW", "N", "NE", "E", "SE", "S", "SW", "W")
CORNER_SIGNS = {"NW": (-1, 1), "NE": (1, 1), "SE": (1, -1), "SW": (-1, -1)}
FACE_AXIS = {"N": (0, 1), "S": (0, -1), "E": (1, 0), "W": (-1, 0)}
T_CLOCK_Z, T_CLOCK_R, T_CLOCK_PANEL = 28.1, 1.4, 1.8
T_BELFRY = (31.8, 37.4, 0.9, 1.65, 2.75)   # zb, zs, rise, |t| inner, |t| outer
T_DOOR = (1.0, 2.2, 1.2)                    # half width, springing, rise
T_BANDS = ((0.0, 0.6), (15.0, 15.4), (31.0, 31.6))
T_LANCET_Z = (6.0, 11.0, 16.0, 21.0)


def _tower_layout(fp, z0=0.0):
    pts = C.ccw([tuple(p) for p in fp])
    sw = min(pts, key=lambda p: p[0] + p[1])
    ne = max(pts, key=lambda p: p[0] + p[1])
    se = max(pts, key=lambda p: p[0] - p[1])
    nw = min(pts, key=lambda p: p[0] - p[1])
    e1 = (se[0] - sw[0], se[1] - sw[1])
    e2 = (ne[0] - nw[0], ne[1] - nw[1])
    width = (math.hypot(*e1) + math.hypot(*e2)) / 2
    depth = (math.dist(nw, sw) + math.dist(ne, se)) / 2
    cx = sum(p[0] for p in pts) / 4
    cy = sum(p[1] for p in pts) / 4
    F = Frame((cx, cy), (e1[0] + e2[0], e1[1] + e2[1]), z0)
    HU, HV = width / 2, depth / 2
    stations = [(ST_ORDER[k % 8], round(ST_Z0 + ST_DZ * k, 3)) for k in range(ST_N)]
    route = []
    for where, z in stations:
        if where in CORNER_SIGNS:
            su, sv = CORNER_SIGNS[where]
            u, v = su * (HU + CORNER_OUT / 2 - 0.2), sv * (HV + CORNER_OUT / 2 - 0.2)
        else:
            au, av = FACE_AXIS[where]
            u, v = au * (HU + LEDGE_OUT / 2), av * (HV + LEDGE_OUT / 2)
        route.append(tuple(round(c, 2) for c in F.p(u, v, z)))
    doors = [
        {"name": "DOOR_century_tower_1", "pos_m": tuple(round(c, 2) for c in F.p(0.0, HV - T_BAY, 0.0)),
         "facing_deg": round(F.bearing(0, 1), 1), "width_m": 2 * T_DOOR[0], "height_m": T_DOOR[1] + T_DOOR[2],
         "primary": True, "target": "Course 6 Century Tower interior (20 stars)",
         "note": "north face, in the recessed bay; visual door leaf sits 0.35 m behind pos_m"},
        {"name": "DOOR_century_tower_2", "pos_m": tuple(round(c, 2) for c in F.p(-(HU - T_BAY), 0.0, 0.0)),
         "facing_deg": round(F.bearing(-1, 0), 1), "width_m": 2 * T_DOOR[0], "height_m": T_DOOR[1] + T_DOOR[2],
         "target": "FINAL EXAM door -> Finals Week Ascent (30 stars)",
         "note": "west face, in the recessed bay; visual door leaf sits 0.35 m behind pos_m"},
    ]
    spots = {
        "top_deck_north": tuple(round(c, 2) for c in F.p(0.0, (HV - T_PAR_W + T_PYR) / 2, T_DECK)),
        "top_deck_south": tuple(round(c, 2) for c in F.p(0.0, -(HV - T_PAR_W + T_PYR) / 2, T_DECK)),
        "top_deck_east": tuple(round(c, 2) for c in F.p((HU - T_PAR_W + T_PYR) / 2, 0.0, T_DECK)),
        "top_deck_west": tuple(round(c, 2) for c in F.p(-(HU - T_PAR_W + T_PYR) / 2, 0.0, T_DECK)),
        "pyramid_apex": tuple(round(c, 2) for c in F.p(0.0, 0.0, T_HEIGHT)),
        "clock_north_center": tuple(round(c, 2) for c in F.p(0.0, HV - T_BAY + 0.12, T_CLOCK_Z)),
    }
    return {"F": F, "HU": HU, "HV": HV, "stations": stations, "route": route, "doors": doors,
            "spots": spots, "center": (cx, cy)}


def _tower_outline(HU, HV):
    P, B = T_PIER, T_BAY
    return [(-HU, -HV), (-HU + P, -HV), (-HU + P, -HV + B), (HU - P, -HV + B), (HU - P, -HV), (HU, -HV),
            (HU, -HV + P), (HU - B, -HV + P), (HU - B, HV - P), (HU, HV - P), (HU, HV),
            (HU - P, HV), (HU - P, HV - B), (-HU + P, HV - B), (-HU + P, HV), (-HU, HV),
            (-HU, HV - P), (-HU + B, HV - P), (-HU + B, -HV + P), (-HU, -HV + P)]


BAY_EDGES = {2: "S", 7: "E", 12: "N", 17: "W"}  # outline edge index -> face


def _ledge_box(HU, HV, face, z):
    """Face ledge box (u0, u1, v0, v1, z0, z1, wall_side) in tower-local coords."""
    au, av = FACE_AXIS[face]
    if au == 0:
        v_in, v_out = av * (HV - T_BAY), av * (HV + LEDGE_OUT)
        return (-LEDGE_HALF, LEDGE_HALF, min(v_in, v_out), max(v_in, v_out), z - LEDGE_T, z,
                "s" if av > 0 else "n")
    u_in, u_out = au * (HU - T_BAY), au * (HU + LEDGE_OUT)
    return (min(u_in, u_out), max(u_in, u_out), -LEDGE_HALF, LEDGE_HALF, z - LEDGE_T, z, "w" if au > 0 else "e")


def _corner_box(HU, HV, corner, z0, z1, out=CORNER_OUT, inn=CORNER_IN):
    su, sv = CORNER_SIGNS[corner]
    return (su * (HU - inn), su * (HU + out), sv * (HV - inn), sv * (HV + out), z0, z1)


def _build_tower(ctx, fp):
    gz = ctx["ground_z"]
    lay0 = _tower_layout(fp)
    cx, cy = lay0["center"]
    lay = _tower_layout(fp, gz(cx, cy))
    F, HU, HV, stations = lay["F"], lay["HU"], lay["HV"], lay["stations"]
    vis, col = C.Builder(), C.Builder()
    outline = _tower_outline(HU, HV)

    # ---- climbing stations ------------------------------------------------------------
    face_ledges = {f: [] for f in FACE_AXIS}     # face -> [ledge tops]
    corner_tops = {c: [] for c in CORNER_SIGNS}
    for k, (where, z) in enumerate(stations):
        (corner_tops if where in CORNER_SIGNS else face_ledges)[where].append((k, z))

    # ---- shaft collision (20-sided prism) --------------------------------------------
    for i in range(len(outline)):
        a, bb = outline[i], outline[(i + 1) % len(outline)]
        W = Wall(F, a, bb)
        W.poly(col, [(0, 0.0), (W.L, 0.0), (W.L, T_SHAFT), (0, T_SHAFT)], "brick_red")  # cells are XZ-only

    # ---- shaft visual -----------------------------------------------------------------
    bz, bs, brise, bt_in, bt_out = T_BELFRY
    dh, ds, drise = T_DOOR
    rows = [(0.0, 0.6, "limestone"), (0.6, 15.0, None), (15.0, 15.4, "limestone"), (15.4, 31.0, None),
            (31.0, 31.6, "limestone"), (31.6, T_SHAFT, None)]
    face_walls = {}
    for i in range(len(outline)):
        a, bb = outline[i], outline[(i + 1) % len(outline)]
        W = Wall(F, a, bb)
        face = BAY_EDGES.get(i)
        base_mat = "brick_dark" if face else "brick_red"
        ops = []
        if face:
            face_walls[face] = W
            tc = W.L / 2
            ops += [Opening(tc - bt_out, tc - bt_in, bz, bs, brise, 2), Opening(tc + bt_in, tc + bt_out, bz, bs, brise, 2)]
            if face in ("N", "W"):
                ops.append(Opening(tc - dh, tc + dh, 0.0, ds, drise, 2))
        for z0, z1, m in rows:
            wall_surface(vis, W, z0, z1, m or base_mat, ops)

    for face, W in face_walls.items():
        tc = W.L / 2
        # belfry: louvred lancets
        for t0, t1 in ((tc - bt_out, tc - bt_in), (tc + bt_in, tc + bt_out)):
            o = Opening(t0, t1, bz, bs, brise, 2)
            recess(vis, W, o, 0.5, "window_dark", "limestone")
            arch_frame(vis, W, o, 0.2, "limestone", off=0.05, jambs=False)
            for j in range(4):
                zl = bz + 1.0 + 1.15 * j
                decal(vis, W, [(t0, zl), (t1, zl), (t1, zl + 0.28), (t0, zl + 0.28)], "dark_trim", off=-0.3)
        # doors
        if face in ("N", "W"):
            o = Opening(tc - dh, tc + dh, 0.0, ds, drise, 2)
            recess(vis, W, o, 0.35, "door_wood", "limestone", skip_bottom=True)
            arch_frame(vis, W, o, 0.25, "limestone", off=0.06)
            if face == "N":  # memorial plaque beside the stage door
                decal(vis, W, [(tc + 1.55, 1.3), (tc + 2.45, 1.3), (tc + 2.45, 1.9), (tc + 1.55, 1.9)], "dark_trim", 0.05)
        # clock (all four faces)
        decal(vis, W, [(tc - T_CLOCK_PANEL, T_CLOCK_Z - T_CLOCK_PANEL), (tc + T_CLOCK_PANEL, T_CLOCK_Z - T_CLOCK_PANEL),
                       (tc + T_CLOCK_PANEL, T_CLOCK_Z + T_CLOCK_PANEL), (tc - T_CLOCK_PANEL, T_CLOCK_Z + T_CLOCK_PANEL)],
              "limestone", 0.05)
        wall_disk(vis, W, tc, T_CLOCK_Z, T_CLOCK_R, 12, "white_trim", 0.09)
        for ang, ln, wd in ((150.0, 0.75, 0.10), (60.0, 1.15, 0.07)):   # ~10:10
            ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
            pa = (-sa * wd, ca * wd)
            decal(vis, W, [(tc - pa[0], T_CLOCK_Z - pa[1]), (tc + ca * ln - pa[0], T_CLOCK_Z + sa * ln - pa[1]),
                           (tc + ca * ln + pa[0], T_CLOCK_Z + sa * ln + pa[1]), (tc + pa[0], T_CLOCK_Z + pa[1])],
                  "dark_trim", 0.12)
        # staggered stair lancets, skipping ledges / door / bands
        busy = [(z - LEDGE_T - CORBEL - 0.2, z + 0.3) for _, z in face_ledges[face]]
        busy += [(zb0 - 0.2, zb1 + 0.2) for zb0, zb1 in T_BANDS]
        if face in ("N", "W"):
            busy.append((0.0, ds + drise + 0.6))
        for zl in T_LANCET_Z:
            if any(zl - 0.3 < hi and zl + 2.85 > lo for lo, hi in busy):
                continue
            o = Opening(tc - 0.35, tc + 0.35, zl, zl + 2.0, 0.55, 1)
            decal(vis, W, o.outline(), "window_dark", 0.05)
            decal(vis, W, [(tc - 0.5, zl - 0.18), (tc + 0.5, zl - 0.18), (tc + 0.5, zl), (tc - 0.5, zl)], "limestone", 0.07)

    # quoins on the four outer corners (alternating long/short)
    busy_c = {c: [(z - LEDGE_T - 0.3, z + 0.3) for _, z in corner_tops[c]] for c in CORNER_SIGNS}
    busy_c["NW"].append((0.0, 2.4))
    for c in ("NE", "SE", "SW"):
        busy_c[c].append((0.0, 1.0))
    for c, (su, sv) in CORNER_SIGNS.items():
        for i in range(20):
            z0q = 1.0 + 2.0 * i
            z1q = z0q + 0.6
            if z1q > T_SHAFT - 0.4:
                break
            if any(z0q < hi and z1q > lo for lo, hi in busy_c[c] + [(a - 0.1, b + 0.1) for a, b in T_BANDS]):
                continue
            la, lb = (0.9, 0.5) if i % 2 == 0 else (0.5, 0.9)
            o = 0.04
            # face with normal (su, 0): spans v from sv*(HV - la) to sv*(HV + o)
            va, vb = sorted((sv * (HV - la), sv * (HV + o)))
            poly(vis, F, [(su * (HU + o), va, z0q), (su * (HU + o), vb, z0q), (su * (HU + o), vb, z1q),
                          (su * (HU + o), va, z1q)], "limestone", (su, 0, 0))
            ua, ub = sorted((su * (HU - lb), su * (HU + o)))
            poly(vis, F, [(ua, sv * (HV + o), z0q), (ub, sv * (HV + o), z0q), (ub, sv * (HV + o), z1q),
                          (ua, sv * (HV + o), z1q)], "limestone", (0, sv, 0))

    # ---- base blocks + climbing stations ------------------------------------------------
    for c in ("NE", "SE", "SW"):
        u0, u1, v0, v1, _, _ = _corner_box(HU, HV, c, 0, 0, out=0.5)
        box(vis, F, u0, u1, v0, v1, 0.0, 0.7, "limestone", faces="tnsew")
        box(col, F, u0, u1, v0, v1, 0.0, 0.7, "limestone", faces="tnsew")
    u0, u1, v0, v1, _, _ = _corner_box(HU, HV, "NW", 0, 0, out=2.5)   # first step
    box(vis, F, u0, u1, v0, v1, 0.0, 0.9, "limestone", faces="tnsew")
    box(col, F, u0, u1, v0, v1, 0.0, 0.9, "limestone", faces="tnsew")
    for k, (where, z) in enumerate(stations):
        if where in CORNER_SIGNS:
            u0, u1, v0, v1, z0, z1 = _corner_box(HU, HV, where, z - LEDGE_T, z)
            if k == 0:
                z0 = 0.0
            faces = "tnsew" if k == 0 else "tbnsew"
            box(vis, F, u0, u1, v0, v1, z0, z1, "limestone", faces=faces)
            box(col, F, u0, u1, v0, v1, z0, z1, "limestone", faces=faces)
        else:
            u0, u1, v0, v1, z0, z1, wall_side = _ledge_box(HU, HV, where, z)
            faces = "tbnsew".replace(wall_side, "")
            box(col, F, u0, u1, v0, v1, z0, z1, "limestone", faces=faces)
            W = face_walls[where]
            tc = W.L / 2
            lo_feat = z0 - CORBEL
            clash = (where in ("N", "W") and lo_feat < ds + drise + 0.3) or \
                    (lo_feat < T_CLOCK_Z + T_CLOCK_PANEL + 0.05 and z0 > T_CLOCK_Z - T_CLOCK_PANEL)
            box(vis, F, u0, u1, v0, v1, z0, z1, "limestone", faces=faces.replace("b", "") if not clash else faces)
            if not clash:  # corbelled underside: slope from the front bottom edge back to the wall
                d_front = (T_BAY + LEDGE_OUT)
                pf =[W.p(tc - LEDGE_HALF, z0, d_front), W.p(tc + LEDGE_HALF, z0, d_front),
                      W.p(tc + LEDGE_HALF, z0 - CORBEL, 0.0), W.p(tc - LEDGE_HALF, z0 - CORBEL, 0.0)]
                vis.poly(pf, "limestone", normal_hint=W.hint(0, -1.0, 1.0))
                for sgn in (-1, 1):
                    tri = [W.p(tc + sgn * LEDGE_HALF, z0, 0.0), W.p(tc + sgn * LEDGE_HALF, z0, d_front),
                           W.p(tc + sgn * LEDGE_HALF, z0 - CORBEL, 0.0)]
                    vis.poly(tri, "limestone", normal_hint=W.hint(sgn, 0, 0))

    # ---- cornice, parapet, deck, turrets, pyramid ---------------------------------------
    sq = [(-HU, -HV), (HU, -HV), (HU, HV), (-HU, HV)]
    k = T_CORNICE
    sqc = [(-HU - k, -HV - k), (HU + k, -HV - k), (HU + k, HV + k), (-HU - k, HV + k)]
    pi = T_PAR_W
    sqi = [(-HU + pi, -HV + pi), (HU - pi, -HV + pi), (HU - pi, HV - pi), (-HU + pi, HV - pi)]
    # visual cornice (40.4 - 41.0, projecting), parapet (41.0 - 42.0) + coping (42.0 - 42.2)
    for i in range(4):
        a, bb = sqc[i], sqc[(i + 1) % 4]
        Wc = Wall(F, a, bb)
        Wc.poly(vis, [(0, T_SHAFT), (Wc.L, T_SHAFT), (Wc.L, 41.0), (0, 41.0)], "limestone")
        a, bb = sq[i], sq[(i + 1) % 4]
        Wp = Wall(F, a, bb)
        Wp.poly(vis, [(0, 41.0), (Wp.L, 41.0), (Wp.L, 42.0), (0, 42.0)], "brick_red")
        Wp.poly(vis, [(0, 42.0), (Wp.L, 42.0), (Wp.L, T_PARAPET), (0, T_PARAPET)], "limestone")
        # cornice top ledge (41.0) and parapet top ring (42.2)
        poly(vis, F, [(*sqc[i], 41.0), (*sqc[(i + 1) % 4], 41.0), (*sq[(i + 1) % 4], 41.0), (*sq[i], 41.0)],
             "limestone", (0, 0, 1))
        for bld in (vis, col):
            poly(bld, F, [(*sq[i], T_PARAPET), (*sq[(i + 1) % 4], T_PARAPET), (*sqi[(i + 1) % 4], T_PARAPET),
                          (*sqi[i], T_PARAPET)], "limestone", (0, 0, 1))
            # parapet inner face (looks toward the tower axis)
            a, bb = sqi[i], sqi[(i + 1) % 4]
            mu, mv = -(a[0] + bb[0]) / 2, -(a[1] + bb[1]) / 2
            poly(bld, F, [(a[0], a[1], T_DECK), (bb[0], bb[1], T_DECK), (bb[0], bb[1], T_PARAPET),
                          (a[0], a[1], T_PARAPET)], "brick_red", (mu, mv, 0))
        # collision outer face of the top block (flush with the piers)
        Wp.poly(col, [(0, T_SHAFT), (Wp.L, T_SHAFT), (Wp.L, T_PARAPET), (0, T_PARAPET)], "limestone")
    # cornice underside (visual: from the 20-gon out to the projecting square)
    P, B = T_PIER, T_BAY
    for pts in (
        [(HU + k, HV + k), (-HU - k, HV + k), (-HU, HV), (-HU + P, HV), (-HU + P, HV - B), (HU - P, HV - B),
         (HU - P, HV), (HU, HV)],
        [(-HU - k, -HV - k), (HU + k, -HV - k), (HU, -HV), (HU - P, -HV), (HU - P, -HV + B), (-HU + P, -HV + B),
         (-HU + P, -HV), (-HU, -HV)],
        [(HU + k, -HV - k), (HU + k, HV + k), (HU, HV), (HU, HV - P), (HU - B, HV - P), (HU - B, -HV + P),
         (HU, -HV + P), (HU, -HV)],
        [(-HU - k, HV + k), (-HU - k, -HV - k), (-HU, -HV), (-HU, -HV + P), (-HU + B, -HV + P), (-HU + B, HV - P),
         (-HU, HV - P), (-HU, HV)],
    ):
        poly(vis, F, [(u, v, T_SHAFT) for u, v in pts], "limestone", (0, 0, -1))
    # collision: ceilings over the four bays under the top block
    for u0, u1, v0, v1 in ((-HU + P, HU - P, HV - B, HV), (-HU + P, HU - P, -HV, -HV + B),
                           (HU - B, HU, -HV + P, HV - P), (-HU, -HU + B, -HV + P, HV - P)):
        poly(col, F, [(u0, v0, T_SHAFT), (u1, v0, T_SHAFT), (u1, v1, T_SHAFT), (u0, v1, T_SHAFT)], "limestone",
             (0, 0, -1))
    # deck
    for bld in (vis, col):
        flat(bld, F, sqi, T_DECK, "roof_dark")
    # corner pinnacle turrets
    for c, (su, sv) in CORNER_SIGNS.items():
        u0, u1 = sorted((su * (HU - T_TURRET), su * (HU + 0.05)))
        v0, v1 = sorted((sv * (HV - T_TURRET), sv * (HV + 0.05)))
        cu, cv = (u0 + u1) / 2, (v0 + v1) / 2
        box(vis, F, u0, u1, v0, v1, 41.0, 43.6, "brick_red", faces="nsew")
        box(vis, F, u0, u1, v0, v1, 43.6, 44.0, "limestone", faces="nsew")
        pyramid(vis, F, cu, cv, (u1 - u0) / 2 + 0.08, (v1 - v0) / 2 + 0.08, 44.0, 46.0, "limestone")
        box(col, F, u0, u1, v0, v1, T_DECK, 44.0, "brick_red", faces="nsew")
        pyramid(col, F, cu, cv, (u1 - u0) / 2, (v1 - v0) / 2, 44.0, 46.0, "limestone")
    # pyramid roof + plinth + finial
    for bld in (vis, col):
        box(bld, F, -T_PYR, T_PYR, -T_PYR, T_PYR, T_DECK, T_DECK + 0.4, "limestone", faces="nsew")
    pyramid(vis, F, 0.0, 0.0, T_PYR, T_PYR, T_DECK + 0.4, T_APEX, "copper_green")
    pyramid(col, F, 0.0, 0.0, T_PYR, T_PYR, T_DECK + 0.4, T_APEX, "copper_green")
    pyramid(vis, F, 0.0, 0.0, 0.18, 0.18, T_APEX - 0.15, T_HEIGHT, "metal_gray")
    return vis, col, lay


# =================================================================== UNIVERSITY AUDITORIUM
# Key lines from the OSM footprint (map metres)
A_SW, A_SE, A_NE, A_NW = (25.04, -18.26), (50.68, -18.27), (50.68, -12.01), (25.05, -12.31)
XW_ARC, XW, XNW, XNE, XE, XE_ARC = 23.09, 25.05, 30.27, 45.70, 50.68, 52.75
Y_BS_W, Y_BS_E = -12.31, -12.01           # B south line (west / east)
Y_BN_W, Y_BN_E = 15.87, 15.78             # B north line (west / east)
TY0, TY1 = -7.7, 7.7                      # transept arm
NAVE_W = ((30.47, 40.10), (30.25, 17.40))  # nave west wall (CCW direction: southward)
NAVE_E = ((45.68, 17.56), (45.81, 39.68))  # nave east wall (northward)
CHAMF_W = ((30.25, 17.40), (28.77, 15.86))
CHAMF_E = ((47.94, 15.78), (45.68, 17.56))
D_PTS = [(28.27, 40.12), (48.14, 39.67), (48.24, 56.21), (28.43, 56.08)]   # north wing (CCW)
PORCH = [(33.63, 56.02), (43.28, 56.24), (43.30, 59.78), (40.67, 62.80), (36.33, 62.91), (33.67, 60.31)]  # CCW
Z_EAVE, Z_RIDGE = 11.0, 18.0              # hall eaves / ridges
Z_FLAT = 9.0                              # 1977 flat roofs (corner blocks + stage block)
Z_ARC = 5.2                               # arcaded lobbies along the west/east fronts
Z_PORCH = 5.2                             # porch roof (walls + coping to 5.5)
Z_D_EAVE, Z_D_RIDGE = 11.5, 18.0          # north wing
COPING = 0.3


def _aud_layout():
    door_w = Wall(Frame(), PORCH[3], PORCH[4])
    tc = door_w.L / 2
    pos = door_w.p(tc, 0.0)
    doors = [{"name": "DOOR_university_auditorium_1", "pos_m": (round(pos[0], 2), round(pos[1], 2), 0.0),
              "facing_deg": round(door_w.bearing(), 1), "width_m": 2.0, "height_m": 3.8, "primary": True,
              "target": "Course 1 The Swamp (0 stars, 'Start here')",
              "note": "centre door of the three-door porch facing the Plaza of the Americas (OSM entrance "
                      "node 8064445595); the NW/NE porch doors are decorative; visual door leaf 0.5 m behind pos_m"}]
    spots = {
        "porch_roof": (38.4, 59.4, Z_PORCH),
        "west_arcade_roof": (24.07, 1.8, Z_ARC),
        "east_arcade_roof": (51.7, 1.8, Z_ARC),
        "south_flat_roof": (38.0, -15.2, Z_FLAT),
        "nw_flat_roof": (27.6, 11.8, Z_FLAT),
        "ne_flat_roof": (48.2, 11.7, Z_FLAT),
        "north_wing_ridge": (38.27, 48.0, Z_D_RIDGE),
        "ta_portico_npc": (38.4, 61.6, 0.0),
    }
    return {"doors": doors, "spots": spots}


def _profile_gable(L, t_eave0, t_eave1, z_low, z_eave, z_ridge, t_ridge=None):
    """Wall top profile: z_low up to t_eave0, eave + gable between, z_low after t_eave1."""
    tr = (t_eave0 + t_eave1) / 2 if t_ridge is None else t_ridge
    prof = []
    if t_eave0 > EPS:
        prof += [(0.0, z_low), (t_eave0, z_low)]
    prof += [(t_eave0, z_eave), (tr, z_ridge), (t_eave1, z_eave)]
    if t_eave1 < L - EPS:
        prof += [(t_eave1, z_low), (L, z_low)]
    return prof


def _rake_coping(b, W, t_e0, t_e1, z_e, z_r, mat="limestone", up=0.35, thick=0.4):
    """Parapet coping along a gable's two rakes (visual): outer band, top and inner face."""
    tr = (t_e0 + t_e1) / 2
    for (ta, za), (tb, zb_) in (((t_e0, z_e), (tr, z_r)), ((tr, z_r), (t_e1, z_e))):
        W.poly(b, [(ta, za), (tb, zb_), (tb, zb_ + up), (ta, za + up)], mat, off=0.0)
        top = [W.p(ta, za + up, 0.0), W.p(tb, zb_ + up, 0.0), W.p(tb, zb_ + up, -thick), W.p(ta, za + up, -thick)]
        b.poly(top, mat, normal_hint=(0, 0, 1))
        back = [W.p(ta, za - 0.3, -thick), W.p(tb, zb_ - 0.3, -thick), W.p(tb, zb_ + up, -thick), W.p(ta, za + up, -thick)]
        b.poly(back, mat, normal_hint=W.hint(0, 0, -1.0))


def _stepped(b, F, x0, x1, y0, y1, tiers, toward, mat="limestone"):
    """Stepped buttress against a wall. tiers: [(depth, top_z)] outermost first; `toward` is the
    outward direction ('w', 'e', 'n', 's') - depth is measured from the wall line x0/x1/y0/y1."""
    for depth, ztop in tiers:
        if toward == "w":
            u0, u1, v0, v1, faces = x1 - depth, x1, y0, y1, "tnsw"
        elif toward == "e":
            u0, u1, v0, v1, faces = x0, x0 + depth, y0, y1, "tnse"
        elif toward == "n":
            u0, u1, v0, v1, faces = x0, x1, y0, y0 + depth, "tnew"
        else:
            u0, u1, v0, v1, faces = x0, x1, y1 - depth, y1, "tsew"
        box(b, F, u0, u1, v0, v1, 0.0, ztop, mat, faces=faces)


def _build_auditorium(ctx, fp):
    gz = ctx["ground_z"]
    F = Frame((0.0, 0.0), (1.0, 0.0), gz(38.0, 22.0))
    vis, col = C.Builder(), C.Builder()

    def wall(a, b_):
        return Wall(F, a, b_)

    def brick_wall(W, z_top, bld):
        """Visual wall: limestone base course, brick, limestone coping row."""
        for r0, r1, m in ((0.0, 0.6, "limestone"), (0.6, z_top - COPING, "brick_red"), (z_top - COPING, z_top, "limestone")):
            wall_surface(bld, W, r0, r1, m)

    # ------------------------------------------------------------ A: 1977 stage block (flat 9.0)
    for a, b_ in ((A_NW, A_SW), (A_SW, A_SE), (A_SE, A_NE)):
        W = wall(a, b_)
        brick_wall(W, Z_FLAT + COPING, vis)
        wall_surface(col, W, 0.0, Z_FLAT, "brick_red", max_w=17.0)
        coping(vis, W, Z_FLAT)
        # windows: dark rectangles
        n = int(W.L // 6.5)       # south face only (the short west/east ends stay blank)
        for i in range(n):
            tc = W.L * (i + 0.5) / n
            for zb in (5.4,):
                decal(vis, W, [(tc - 0.7, zb), (tc + 0.7, zb), (tc + 0.7, zb + 1.9), (tc - 0.7, zb + 1.9)], "window_dark")
    # flat roofs at 9.0: stage block (2 pieces) + SW / SE corner blocks
    xm = (A_SW[0] + A_SE[0]) / 2
    flat_pieces = [
        [A_SW, (xm, -18.265), (xm, Y_BS_W), A_NW],
        [(xm, -18.265), A_SE, (A_NE[0], Y_BS_W), (xm, Y_BS_W)],
        [(XW, Y_BS_W), (XNW, Y_BS_W), (XNW, TY0), (XW, TY0)],
        [(XNE, Y_BS_W), (XE, Y_BS_W), (XE, TY0), (XNE, TY0)],
        [(XW, TY1), (XNW, TY1), CHAMF_W[0], CHAMF_W[1], (XW, Y_BN_W)],            # NW block
        [(XNE, TY1), (XE, TY1), (XE, Y_BN_E), CHAMF_E[0], CHAMF_E[1]],            # NE block
    ]
    for pts in flat_pieces:
        for bld in (vis, col):
            flat(bld, F, pts, Z_FLAT, "roof_dark")

    # ------------------------------------------------------------ B: transept front walls (W, E)
    # west wall (x = 25.05) walking south (outside = west); east wall (x = 50.68) walking north
    Ww = wall((XW, Y_BN_W), (XW, Y_BS_W))
    We = wall((XE, Y_BS_E), (XE, Y_BN_E))
    for W, y_from in ((Ww, Y_BN_W), (We, Y_BS_E)):
        sgn = -1 if W is Ww else 1          # t grows southward on the west wall, northward on the east
        te0 = abs(TY1 - y_from) if W is Ww else abs(TY0 - y_from)
        te1 = abs(TY0 - y_from) if W is Ww else abs(TY1 - y_from)
        prof_c = _profile_gable(W.L, te0, te1, Z_FLAT, Z_EAVE, Z_RIDGE)
        prof_v = _profile_gable(W.L, te0, te1, Z_FLAT + COPING, Z_EAVE + 0.35, Z_RIDGE + 0.35)
        # big traceried transept window, centred on the transept
        tcw = (te0 + te1) / 2
        win = Opening(tcw - 3.5, tcw + 3.5, 5.9, 12.0, 3.6, 2)
        wall_surface(col, W, Z_ARC, prof_c, "brick_red", max_w=17.0)
        wall_surface(vis, W, Z_ARC, prof_v, "brick_red", [win])
        recess(vis, W, win, 0.6, "window_dark", "limestone")
        arch_frame(vis, W, win, 0.35, "limestone", off=0.05, jambs=False)
        decal(vis, W, [(tcw - 3.7, 5.65), (tcw + 3.7, 5.65), (tcw + 3.7, 5.9), (tcw - 3.7, 5.9)], "limestone", 0.06)
        for tm in (tcw - 1.17, tcw + 1.17):   # mullions
            decal(vis, W, [(tm - 0.11, 5.9), (tm + 0.11, 5.9), (tm + 0.11, 13.4), (tm - 0.11, 13.4)], "limestone", -0.3)
        decal(vis, W, [(tcw - 3.5, 9.4), (tcw + 3.5, 9.4), (tcw + 3.5, 9.65), (tcw - 3.5, 9.65)], "limestone", -0.3)
        wall_disk(vis, W, tcw, 13.9, 0.8, 8, "limestone", -0.28)
        _rake_coping(vis, W, te0, te1, Z_EAVE + 0.35, Z_RIDGE + 0.35)
        # one small lancet on each corner block above the arcade roof
        for ta, tb in ((0.0, te0), (te1, W.L)):
            tl = (ta + tb) / 2
            decal(vis, W, Opening(tl - 0.45, tl + 0.45, 6.0, 7.7, 0.6, 1).outline(), "window_dark", 0.05)
        # coping inner face over the corner blocks
        for ta, tb in ((0.0, te0), (te1, W.L)):
            vis.poly([W.p(ta, Z_FLAT, -0.3), W.p(tb, Z_FLAT, -0.3), W.p(tb, Z_FLAT + COPING, -0.3),
                      W.p(ta, Z_FLAT + COPING, -0.3)], "limestone", normal_hint=W.hint(0, 0, -1))
        # transept corner buttresses (stepping blocks 5.2 -> 7.1) + corbelled pinnacles above
        for te in (te0, te1):
            y = W.p(te, 0)[1]
            if W is Ww:
                x0b, x1b, xp0, xp1 = XW - 0.9, XW, XW - 0.6, XW
            else:
                x0b, x1b, xp0, xp1 = XE, XE + 0.9, XE, XE + 0.6
            fc = "tnsw" if W is Ww else "tnse"
            for bld in (vis, col):
                box(bld, F, x0b, x1b, y - 0.7, y + 0.7, Z_ARC, 7.1, "limestone", faces=fc)
            fp_ = "nsw" if W is Ww else "nse"
            box(vis, F, xp0, xp1, y - 0.35, y + 0.35, 9.3, 18.9, "brick_red", faces=fp_ + "b")
            pyramid(vis, F, (xp0 + xp1) / 2, y, 0.38, 0.38, 18.9, 20.6, "limestone")

    # ------------------------------------------------------------ arcaded lobbies (W, E)
    arcs = [((XW_ARC, Y_BS_W), (XW, Y_BS_W), (XW, Y_BN_W), (23.10, Y_BN_W), "w"),
            ((XE, Y_BS_E), (52.73, Y_BS_E), (52.76, Y_BN_E), (XE, Y_BN_E), "e")]
    for p_sw, p_se, p_ne, p_nw, side in arcs:
        if side == "w":
            Wo = wall(p_nw, (XW_ARC, Y_BS_W))       # outer face, outside = west
            ends = [wall((XW_ARC, Y_BS_W), p_se), wall(p_ne, p_nw)]
            door_y = -0.34
        else:
            Wo = wall(p_se, p_ne)                   # outer face, outside = east
            ends = [wall(p_sw, p_se), wall(p_ne, p_nw)]
            door_y = -3.5
        # five-ish bays spaced from the real entrance (OSM entrance node), which gets a door arch
        td = abs(Wo.p(0, 0)[1] - door_y)
        sp = Wo.L / 5
        ops_vis = []
        for kb in range(-6, 7):
            tl = td + kb * sp
            if not 1.8 <= tl <= Wo.L - 1.8:
                continue
            if kb == 0:
                ops_vis.append((Opening(tl - 1.2, tl + 1.2, 0.0, 2.6, 1.5, 2), "door_wood"))
            else:
                ops_vis.append((Opening(tl - 1.5, tl + 1.5, 0.9, 3.2, 1.7, 1), "window_dark"))
        cut = [o for o, m in ops_vis if m == "door_wood"]
        for r0, r1, m in ((0.0, 0.6, "limestone"), (0.6, Z_ARC, "brick_red"), (Z_ARC, Z_ARC + COPING, "limestone")):
            wall_surface(vis, Wo, r0, r1, m, cut)
        for o, m in ops_vis:
            if m == "door_wood":
                recess(vis, Wo, o, 0.4, m, "limestone", skip_bottom=True)
            else:
                decal(vis, Wo, o.outline(), m, 0.04)
            arch_frame(vis, Wo, o, 0.22, "limestone", off=0.06, jambs=False)
        wall_surface(col, Wo, 0.0, Z_ARC, "brick_red", max_w=15.0)
        for We_ in ends:
            for r0, r1, m in ((0.0, 0.6, "limestone"), (0.6, Z_ARC, "brick_red"), (Z_ARC, Z_ARC + COPING, "limestone")):
                wall_surface(vis, We_, r0, r1, m)
            wall_surface(col, We_, 0.0, Z_ARC, "brick_red")
        ys = splits(min(p_sw[1], p_se[1]), max(p_ne[1], p_nw[1]), 15.0)
        for ya, yb in zip(ys, ys[1:]):
            for bld in (vis, col):
                flat(bld, F, [(p_sw[0], ya), (p_se[0], ya), (p_se[0], yb), (p_sw[0], yb)], Z_ARC, "roof_dark")
        for W in [Wo] + ends:
            coping(vis, W, Z_ARC)
        # stepped end buttress at the north end (ground -> 1.8 -> 3.5 -> arcade roof 5.2)
        if side == "w":
            for bld in (vis, col):
                _stepped(bld, F, XW_ARC, XW, Y_BN_W, Y_BN_W, [(2.4, 1.8), (1.2, 3.5)], "n")

    # ------------------------------------------------------------ B north walls (corner blocks)
    for a, b_ in ((CHAMF_W[0], CHAMF_W[1]), (CHAMF_W[1], (XW, Y_BN_W)), ((XE, Y_BN_E), CHAMF_E[0]), CHAMF_E):
        W = wall(a, b_)
        brick_wall(W, Z_FLAT + COPING, vis)
        wall_surface(col, W, 0.0, Z_FLAT, "brick_red")
        coping(vis, W, Z_FLAT)
        if W.L > 3.0:
            tl = W.L / 2
            for zb in (2.0, 5.6):
                o = Opening(tl - 0.6, tl + 0.6, zb, zb + 1.8, 0.75, 1)
                decal(vis, W, o.outline(), "window_dark", 0.05)

    # ------------------------------------------------------------ hall walls above the flat roofs
    seg = [
        # transept arm side walls (9.0 -> 11.0), outside = north / south
        ((XNW, TY1), (XW, TY1)), ((XE, TY1), (XNE, TY1)),
        ((XW, TY0), (XNW, TY0)), ((XNE, TY0), (XE, TY0)),
        # nave side walls over the corner blocks, outside = west / east
        ((XNW, CHAMF_W[0][1]), (XNW, TY1)), ((XNW, TY0), (XNW, Y_BS_W)),
        ((XNE, TY1), (XNE, CHAMF_E[1][1])), ((XNE, Y_BS_W), (XNE, TY0)),
    ]
    for a, b_ in seg:
        W = wall(a, b_)
        wall_surface(col, W, Z_FLAT, Z_EAVE, "brick_red")
        wall_surface(vis, W, Z_FLAT, Z_EAVE - 0.4, "brick_red")
        wall_surface(vis, W, Z_EAVE - 0.4, Z_EAVE, "limestone")
    # nave south gable (over the stage block), outside = south
    Wg = wall((XNW, Y_BS_W), (XNE, Y_BS_W))
    wall_surface(col, Wg, Z_FLAT, _profile_gable(Wg.L, 0.0, Wg.L, Z_FLAT, Z_EAVE, Z_RIDGE), "brick_red")
    wall_surface(vis, Wg, Z_FLAT, _profile_gable(Wg.L, 0.0, Wg.L, Z_FLAT, Z_EAVE + 0.35, Z_RIDGE + 0.35), "brick_red")
    _rake_coping(vis, Wg, 0.0, Wg.L, Z_EAVE + 0.35, Z_RIDGE + 0.35)
    o = Opening(Wg.L / 2 - 1.2, Wg.L / 2 + 1.2, 11.6, 14.0, 1.4, 2)
    decal(vis, Wg, o.outline(), "window_dark", 0.05)
    arch_frame(vis, Wg, o, 0.2, "limestone", off=0.07, jambs=False)

    # ------------------------------------------------------------ nave (C) side walls + buttresses
    nave_bays = [20.1, 25.7, 31.3, 36.9]
    buttress_y = [22.9, 28.5, 34.1]
    for (a, b_), outside in ((NAVE_W, "w"), (NAVE_E, "e")):
        W = wall(a, b_)
        rows = [(0.0, 0.6, "limestone"), (0.6, Z_EAVE - 0.4, None), (Z_EAVE - 0.4, Z_EAVE, "limestone")]
        for r0, r1, m in rows:
            wall_surface(vis, W, r0, r1, m or "brick_red")
        wall_surface(col, W, 0.0, Z_EAVE, "brick_red", max_w=17.0)
        for yb in nave_bays:
            # t of this y along the wall
            t = (yb - a[1]) / (b_[1] - a[1]) * W.L
            o = Opening(t - 1.0, t + 1.0, 3.2, 8.0, 1.3, 1)
            decal(vis, W, o.outline(), "window_dark", 0.05)
        for yb in buttress_y:
            t = (yb - a[1]) / (b_[1] - a[1]) * W.L
            xw = W.p(t, 0)[0]
            if outside == "w":
                u0, u1 = xw - 1.0, xw
                fcol, fvis = "nsw", "nsw"
            else:
                u0, u1 = xw, xw + 1.0
                fcol, fvis = "nse", "nse"
            box(col, F, u0, u1, yb - 0.5, yb + 0.5, 0.0, 8.0, "brick_red", faces=fcol)
            box(vis, F, u0, u1, yb - 0.5, yb + 0.5, 0.0, 7.4, "brick_red", faces=fvis)
            # weathered (sloped) limestone cap 7.4 -> 8.6 against the wall
            far = u0 if outside == "w" else u1
            near = u1 if outside == "w" else u0
            sgn = -1 if outside == "w" else 1
            for yy, s in ((yb - 0.5, -1), (yb + 0.5, 1)):
                poly(vis, F, [(far, yy, 7.4), (near, yy, 7.4), (near, yy, 8.6)], "limestone", (0, s, 0))
            poly(vis, F, [(far, yb - 0.5, 7.4), (far, yb + 0.5, 7.4), (near, yb + 0.5, 8.6), (near, yb - 0.5, 8.6)],
                 "limestone", (sgn, 0, 1))

    # ------------------------------------------------------------ hall roofs
    x_mid = (XNW + XNE) / 2
    gable_roof(col, F, XNW, XNE, Y_BS_W, 39.9, Z_EAVE, Z_RIDGE, "y", "roof_tile_red", max_len=17.5)
    gable_roof(col, F, XW, XE, TY0, TY1, Z_EAVE, Z_RIDGE, "x", "roof_tile_red", max_len=13.0)
    gable_roof(vis, F, XNW, XNE, Y_BS_W, 39.9, Z_EAVE, Z_RIDGE, "y", "roof_tile_red", oh=0.4, thick=0.25,
               max_len=17.5)
    gable_roof(vis, F, XW, XE, TY0, TY1, Z_EAVE, Z_RIDGE, "x", "roof_tile_red", oh=0.4, thick=0.25, max_len=17.5)
    # ridge caps
    flat_rect(vis, F, x_mid - 0.18, x_mid + 0.18, Y_BS_W, 39.9, Z_RIDGE + 0.02, "roof_dark", max_len=17.5)
    flat_rect(vis, F, XW, XE, -0.18, 0.18, Z_RIDGE + 0.03, "roof_dark", max_len=17.5)

    # ------------------------------------------------------------ D: 1977 north wing
    dW = wall(D_PTS[3], D_PTS[0])      # west side, walking south
    dE = wall(D_PTS[1], D_PTS[2])      # east side, walking north
    dS = wall(D_PTS[0], D_PTS[1])      # south side, walking east
    dN = wall(D_PTS[2], D_PTS[3])      # north facade, walking west
    for W in (dW, dE):
        for r0, r1, m in ((0.0, 0.6, "limestone"), (0.6, Z_D_EAVE - 0.4, None), (Z_D_EAVE - 0.4, Z_D_EAVE, "limestone")):
            wall_surface(vis, W, r0, r1, m or "brick_red")
        wall_surface(col, W, 0.0, Z_D_EAVE, "brick_red", max_w=17.0)
        for tl in (W.L * 0.3, W.L * 0.7):
            for zb in (2.4, 7.0):
                o = Opening(tl - 0.8, tl + 0.8, zb, zb + 2.2, 0.95, 1)
                decal(vis, W, o.outline(), "window_dark", 0.05)
    prof_s = _profile_gable(dS.L, 0.0, dS.L, 0.0, Z_D_EAVE, Z_D_RIDGE)
    wall_surface(col, dS, 0.0, prof_s, "brick_red", max_w=17.0)
    wall_surface(vis, dS, 0.0, prof_s, "brick_red")
    prof_nc = _profile_gable(dN.L, 0.0, dN.L, 0.0, Z_D_EAVE, Z_D_RIDGE)
    prof_nv = _profile_gable(dN.L, 0.0, dN.L, 0.0, Z_D_EAVE + 0.45, Z_D_RIDGE + 0.45)
    tcn = dN.L / 2
    fwin = Opening(tcn - 3.0, tcn + 3.0, 6.1, 12.0, 3.4, 2)
    wall_surface(col, dN, 0.0, prof_nc, "brick_red", max_w=17.0)
    wall_surface(vis, dN, 0.0, 0.6, "limestone")
    wall_surface(vis, dN, 0.6, prof_nv, "brick_red", [fwin])
    recess(vis, dN, fwin, 0.6, "window_dark", "limestone")
    arch_frame(vis, dN, fwin, 0.35, "limestone", off=0.05, jambs=False)
    for tm in (tcn - 1.0, tcn + 1.0):
        decal(vis, dN, [(tm - 0.11, 6.1), (tm + 0.11, 6.1), (tm + 0.11, 13.2), (tm - 0.11, 13.2)], "limestone", -0.3)
    decal(vis, dN, [(tcn - 3.0, 9.6), (tcn + 3.0, 9.6), (tcn + 3.0, 9.85), (tcn - 3.0, 9.85)], "limestone", -0.3)
    wall_disk(vis, dN, tcn, 13.7, 0.75, 8, "limestone", -0.28)
    _rake_coping(vis, dN, 0.0, dN.L, Z_D_EAVE + 0.45, Z_D_RIDGE + 0.45)
    # cross finial on the front gable (front + back faces)
    zc = Z_D_RIDGE + 0.45 + 0.35
    for off, hint in ((0.0, (0, 0, 1)), (-0.4, (0, 0, -1))):
        dN.poly(vis, [(tcn - 0.12, zc), (tcn + 0.12, zc), (tcn + 0.12, zc + 1.5), (tcn - 0.12, zc + 1.5)],
                "limestone", off=off, hint=hint)
        dN.poly(vis, [(tcn - 0.45, zc + 0.9), (tcn + 0.45, zc + 0.9), (tcn + 0.45, zc + 1.15), (tcn - 0.45, zc + 1.15)],
                "limestone", off=off, hint=hint)
    # north wing roof (33 deg: walkable)
    dx0, dx1 = (D_PTS[0][0] + D_PTS[3][0]) / 2, (D_PTS[1][0] + D_PTS[2][0]) / 2
    dy0, dy1 = (D_PTS[0][1] + D_PTS[1][1]) / 2, (D_PTS[2][1] + D_PTS[3][1]) / 2
    gable_roof(col, F, dx0, dx1, dy0, dy1, Z_D_EAVE, Z_D_RIDGE, "y", "roof_tile_red", max_len=17.0)
    gable_roof(vis, F, dx0, dx1, dy0, dy1, Z_D_EAVE, Z_D_RIDGE, "y", "roof_tile_red", oh=0.4, thick=0.25,
               max_len=17.5)
    xmd = (dx0 + dx1) / 2
    poly(vis, F, [(xmd - 0.18, dy0, Z_D_RIDGE + 0.02), (xmd + 0.18, dy0, Z_D_RIDGE + 0.02),
                  (xmd + 0.18, dy1, Z_D_RIDGE + 0.02), (xmd - 0.18, dy1, Z_D_RIDGE + 0.02)], "roof_dark", (0, 0, 1))
    # facade corner turrets (visual + collision walls)
    for (xc, yc) in (D_PTS[3], D_PTS[2]):
        u0, u1, v0, v1 = xc - 0.75, xc + 0.75, yc - 1.1, yc + 0.4
        box(vis, F, u0, u1, v0, v1, 0.0, 19.6, "brick_red", faces="nsew")
        pyramid(vis, F, xc, (v0 + v1) / 2, 0.85, 0.85, 19.6, 22.4, "limestone")
        box(col, F, u0, u1, v0, v1, 0.0, 19.6, "brick_red", faces="nsew")
    # stair buttress on the west wall (ground -> 2.3 -> 4.6 -> 6.9 -> 9.2 -> eave 11.5, 1.2 m treads)
    xw_d = dW.p(dW.L * 0.5, 0)[0]
    for bld in (vis, col):
        _stepped(bld, F, xw_d, xw_d, 46.6, 48.6, [(4.8, 2.3), (3.6, 4.6), (2.4, 6.9), (1.2, 9.2)], "w")

    # ------------------------------------------------------------ porch (three doors, flat roof)
    pw = [Wall(F, PORCH[i], PORCH[(i + 1) % len(PORCH)]) for i in range(len(PORCH))]
    for i, W in enumerate(pw):
        if i == 0:
            continue   # against the north wing
        ops = []
        if i in (2, 3, 4):   # NE diagonal, north (stage door), NW diagonal
            tc = W.L / 2
            ops.append(Opening(tc - 1.0, tc + 1.0, 0.0, 2.6, 1.2, 2))
        for r0, r1, m in ((0.0, 0.5, "limestone"), (0.5, Z_PORCH, "brick_red"), (Z_PORCH, Z_PORCH + COPING, "limestone")):
            wall_surface(vis, W, r0, r1, m, ops)
        for o in ops:
            recess(vis, W, o, 0.5, "door_wood", "limestone", skip_bottom=True)
            arch_frame(vis, W, o, 0.25, "limestone", off=0.06, jambs=False)
        wall_surface(col, W, 0.0, Z_PORCH, "brick_red")
        coping(vis, W, Z_PORCH)
    for bld in (vis, col):
        flat(bld, F, PORCH, Z_PORCH, "roof_dark")
    for (xc, yc) in PORCH[3:5]:
        box(vis, F, xc - 0.3, xc + 0.3, yc - 0.3, yc + 0.3, Z_PORCH + COPING, 6.4, "limestone", faces="nsew")
        pyramid(vis, F, xc, yc, 0.36, 0.36, 6.4, 7.5, "limestone")
    # stepped buttress against the porch's west side (ground -> 1.8 -> 3.6 -> roof 5.2, 1.2 m treads)
    for bld in (vis, col):
        _stepped(bld, F, 33.65, 33.65, 57.0, 59.0, [(2.4, 1.8), (1.2, 3.6)], "w")
    return vis, col


# =================================================================== contract
_TL = _tower_layout(TOWER_FP)
_AL = _aud_layout()

LANDMARKS = [
    {
        "slug": "century_tower",
        "name": "Century Tower",
        "osm_ids": [TOWER_ID],
        "center_m": tuple(round(c, 2) for c in _TL["center"]),
        "height_m": T_HEIGHT,
        "doors": _TL["doors"],
        "spots": _TL["spots"],
        "climb_route_m": _TL["route"],
        "top_platform": {"z_m": T_DECK, "ring_inner_half_m": T_PYR, "ring_outer_half_m": round(_TL["HU"] - T_PAR_W, 2),
                         "note": "~1.6 m walkway inside the 0.65 m parapet around the pyramid; parapet top 42.2 m"},
    },
    {
        "slug": "university_auditorium",
        "name": "University Auditorium",
        "osm_ids": [AUD_ID, AUD_PART_ID],
        "center_m": (37.9, 22.3),
        "height_m": Z_RIDGE,
        "doors": _AL["doors"],
        "spots": _AL["spots"],
    },
]


def build(ctx):
    """-> [{"name", "mesh", "material_slots", "collision", "visual"}, ...] (map metres, z up)."""
    if "ground_z" not in ctx:
        ctx = dict(ctx, ground_z=lambda x, y: 0.0)
    t_fp = C.footprint(ctx, TOWER_ID)
    a_fp = C.footprint(ctx, AUD_ID)
    lay = _tower_layout(t_fp)
    if max(math.dist(p, q) for p, q in zip(sorted(C.ccw(TOWER_FP)), sorted(t_fp))) > 0.05:
        print("century_tower_auditorium: WARNING Century Tower footprint changed in campus.json")
    LANDMARKS[0].update(center_m=tuple(round(c, 2) for c in lay["center"]), doors=lay["doors"],
                        spots=lay["spots"], climb_route_m=lay["route"])
    ref = C.ccw([(50.68, -12.01), (50.68, -18.27), (25.04, -18.26), (25.05, -12.31), (23.09, -12.31)])
    if not all(any(math.dist(p, q) < 0.05 for q in a_fp) for p in ref):
        print("century_tower_auditorium: WARNING University Auditorium footprint changed in campus.json")

    parts = []
    t_vis, t_col, _ = _build_tower(ctx, t_fp)
    a_vis, a_col = _build_auditorium(ctx, a_fp)
    for slug, vis, col in (("century_tower", t_vis, t_col), ("university_auditorium", a_vis, a_col)):
        me, slots = vis.build(f"{slug} visual")
        parts.append(C.part(f"{slug} visual", me, slots, collision=False, visual=True))
        me, slots = col.build(f"{slug} collision")
        parts.append(C.part(f"{slug} collision", me, slots, collision=True, visual=False))
        print(f"century_tower_auditorium: {slug}: visual {vis.tri_count()} tris, collision {col.tri_count()} tris")
    return parts
