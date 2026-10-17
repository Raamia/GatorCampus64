"""Corina: big voluminous dark-brown curls past the shoulders with caramel ends,
curly bangs to the brows, navy t-shirt, thin silver chain necklace.

Hair = the shared long-hair shell (sgl_heads, window 60, face locks) with a lot of
volume and a rounder face, plus head_parts:
  - add_curly_bangs: her own fringe (the shared one is off): separate curl clumps with
    rounded tips that flip out, recessed notches between them, a short gap just left of
    centre where the forehead shows, and longer clumps at the sides (photos 1 and 4)
  - shape_chin: oval face, the jaw tapers to a softer, narrower chin
  - reshape_rings: hair radius at the cheeks/jaw per column (wide at the sides, shallow
    at the back, the jaw-side hair moved behind the jaw so profiles show no "beard")
  - add_shell_bumps: hair vertices pushed in/out in a checkerboard (lumpy relief)
  - add_curly_drape: an A-line drape of her own (the shared drape hugs the body) that
    continues the checkerboard, bulges then tucks in, ends in scalloped curl tips, with
    the caramel colour (role hair_tips = colors.hair_tips) on a zigzag boundary
  - move_floor: closes the underside of the hair above the neck (seen from below)
  - add_lumps: hanging curl clumps on the side silhouettes only (from the gameplay
    camera behind her, clumps on the back read as studs)
"""
import math

from mathutils import Vector

import sgl_body
import sgl_heads as H
import sgl_materials as smat
from sgl_heads import Geo, emit

HAIR_STYLE = {
    "window": 60, "face_bands": ("fan_bottom", 0, 1, 2),
    "off": {"top": 0.13, "upper": 0.16, "side": 0.20, "back": 0.17},
    # rounder face than the default skull (full cheeks, soft chin) and a lower crown, so
    # the hair above the bangs is about as tall as the face (photo 1), not a tall helmet
    "skull": [
        (0.12, 0.43, 0.38, 0.34, 0.06, 2.5),
        (0.42, 0.55, 0.50, 0.50, 0.03, 2.4),
        (0.74, 0.555, 0.48, 0.54, 0.00, 2.3),
        (0.95, 0.48, 0.39, 0.50, -0.02, 2.2),
        (1.07, 0.33, 0.26, 0.36, -0.03, 2.0),
    ],
    "bottom_pole": (0.0, 0.16, 0.01),
    "top_pole": (0.0, -0.03, 1.14),
    "ring_off": {0: 0.50, 1: 0.30},   # re-placed by "ring_radius" below
    "hang": True,
    "face_layout": {"eyes": (0.0, 0.57, 0.86, 0.37), "mouth": (0.0, 0.255, 0.44, 0.22)},
    "fringe": None,  # built in head_parts (curly bangs)
    # curly bangs (photos 1 and 4): separate clumps, (centre angle, half width deg, tip u),
    # her right is negative. The brows (eye texture rows 6-9, u 0.645-0.686) span about
    # 12-41 deg each side: the middle clumps stop at their top, the long side clumps hang
    # outside the brow tails; a short gap just to her left of centre shows the forehead.
    "bangs": {
        "span": 60, "end_u": 0.66, "notch_u": 0.77, "shoulder": 0.72, "shoulder_du": 0.015,
        "clumps": [(-49, 9, 0.64), (-28, 10, 0.69), (-9, 8, 0.70), (17, 10, 0.69), (43, 11, 0.655)],
        "gap": (3.0, 0.85),
        "offset": 0.075, "offset_mid": 0.13, "mid_u": 0.865,
        # kind: (extra mid-row offset, extra edge offset, edge lift): clumps bulge and
        # their tips flip out and up (curls), notches and the gap recess toward the skull
        # (the two ends sit on the side hair's border, see add_curly_bangs)
        "extra": {"tip": (0.05, 0.04, 0.012), "shoulder": (0.03, 0.02, 0.0),
                  "notch": (-0.005, -0.015, 0.0), "gap": (-0.045, -0.045, 0.0)},
    },
    "drape": None,  # built in head_parts (curly_drape)
    # curls framing the face: from the temples (end of the bangs) down over the outer
    # cheeks to the jaw, as in photos 1 and 4
    "locks": {"theta_inner": 50, "theta_outer": 68, "theta_tip": 58, "u_top": 0.70, "u_mid": 0.40,
              "u_tip": 0.17, "offset_inner": 0.04, "offset_outer": 0.10},
    "nose": {"u": 0.42, "half_width": 0.05, "bottom": -0.03, "tip": 0.045, "top": 0.06},
    # ---- Corina-only keys (read by head_parts)
    # horizontal radius of the hair at ring 1 (cheeks) and ring 0 (jaw) per |column angle|:
    # widest at the sides, less deep at the back (the side view stays a head, not a cape);
    # ring 0 at the back is just deep enough for the crouch (see curly_drape min_r)
    "ring_radius": {1: {60: 0.64, 90: 0.80, 120: 0.78, 150: 0.70, 180: 0.66},
                    0: {60: 0.62, 90: 0.86, 120: 0.82, 150: 0.73, 180: 0.73}},
    # the hair beside the jaw sits further back than the face-window border (60 deg), so
    # in profile the front drape hangs behind the jaw instead of reading as a beard
    "ring_angle": {1: {60: 66.0}, 0: {60: 78.0}},
    # (the back, |angle| >= back_from, gets deeper relief instead of curl clumps)
    "bumps": {"out": 0.05, "in": 0.03, "rings": (1, 2, 3, 4),
              "back_from": 120, "back_out": 0.08, "back_in": 0.04},
    "curly_drape": {
        "cols": (60, 90, 120, 150, 180, 210, 240, 270, 300),
        # the back ends stop above the waist so the gameplay camera (behind her) still
        # sees some navy shirt below the caramel ends; the hair stays past the shoulders
        "ends": {60: -0.16, 90: -0.38, 120: -0.30, 150: -0.39, 180: -0.33, 210: -0.39, 240: -0.30,
                 270: -0.38, 300: -0.16},
        "rows": (0.0, 0.33, 0.64, 1.0),
        # radius added to the top radius at each row: bulges, then the curl ends tuck in
        "flare": (0.0, 0.10, 0.12, 0.06), "thickness": 0.09, "notch": 0.12,
        # gap between the inner side and the (rest pose) torso
        "clearance": 0.05,
        # crouching (and other bent-over moves) swings the upper back up to 0.76 from
        # the head axis behind the head (measured over the CROUCHING animation): the
        # back columns' outer surface stays outside that (no inward curl bump there)
        "min_r": {150: 0.81, 180: 0.82, 210: 0.81},
        # caramel ends: every segment from row 2 down, and the row-1 segment of every other
        # column gap (a ragged colour boundary, single curls lighter than others)
        "tips_from_row": 2, "tips_alt_row": 1,
    },
    # hanging curl clumps on the side silhouettes: (column angle, height u, half width,
    # half height, rise); mirrored to -angle unless the angle is 0 or 180. Each is a
    # 4-sided pyramid whose base hugs the hair and whose apex droops toward the bottom.
    # None on the crown or the back: seen from the gameplay camera they read as studs
    "lumps": [
        (55, 1.17, 0.17, 0.19, 0.08), (95, 0.98, 0.15, 0.20, 0.08),
        (90, 0.62, 0.15, 0.21, 0.08), (95, 0.22, 0.15, 0.21, 0.07),
    ],
    "lump_droop": 0.45, "lump_sides": 4,
    # oval face: ring-0 face vertices per |angle|: (width scale, du, df); the jaw tapers
    # from the full cheeks to a softer, narrower chin
    "chin": {0: (1.0, -0.065, 0.0), 30: (0.90, -0.035, 0.0), 60: (0.88, 0.03, 0.0)},
}


# ------------------------------------------------------------------ hair
# (local copies of two small sgl_heads helpers, so this module does not depend on the
# shared module's private functions)
def _wrap(theta):
    return (theta + 180.0) % 360.0 - 180.0


def _hair_dir(k, p):
    """Outward direction of hair volume at a shell vertex of ring k (as sgl_heads)."""
    if k < H.WIDEST_RING:
        d = Vector((p.x, p.y - H.SKULL_RINGS[k][4], 0.0))
    else:
        d = p - H.HEAD_CENTER
    return d.normalized() if d.length > 1e-6 else Vector((0, 0, 1))


def _bump_sign(k, i):
    return 1 if (k + i) % 2 == 0 else -1


def _own_hair_verts(g, ring):
    """{column: vertex} of a ring's hair vertices that are not shared with the face."""
    return {i: vi for (k, i), vi in g.hair_vid.items() if k == ring and g.face_vid.get((k, i)) != vi}


def reshape_rings(g, style):
    for ring, table in style["ring_radius"].items():
        f0 = H.SKULL_RINGS[ring][4]
        keys = sorted(table)
        for i, vi in _own_hair_verts(g, ring).items():
            a = abs(_wrap(H.THETAS[i]))
            a = min(max(a, keys[0]), keys[-1])
            lo = max(k for k in keys if k <= a)
            hi = min(k for k in keys if k >= a)
            r = table[lo] if hi == lo else table[lo] + (table[hi] - table[lo]) * (a - lo) / (hi - lo)
            p = g.verts[vi]
            d = Vector((p.x, p.y - f0, 0)).normalized()
            ang = style.get("ring_angle", {}).get(ring, {}).get(round(abs(_wrap(H.THETAS[i]))))
            if ang is not None:
                a_ = math.radians(math.copysign(ang, d.x))
                d = Vector((math.sin(a_), math.cos(a_), 0))
            g.verts[vi] = Vector((0, f0, p.z)) + d * r


def add_shell_bumps(g, style):
    b = style["bumps"]
    for ring in b["rings"]:
        for i, vi in _own_hair_verts(g, ring).items():
            p = g.verts[vi]
            s = _bump_sign(ring, i)
            back = abs(_wrap(H.THETAS[i])) >= b.get("back_from", 999)
            out, inn = (b["back_out"], b["back_in"]) if back else (b["out"], b["in"])
            g.verts[vi] = p + _hair_dir(ring, p) * (out if s > 0 else -inn)


def _body_r():
    import bpy
    body = bpy.data.objects.get("Mario Mesh")
    arm = bpy.data.objects.get("Mario")
    if body is None or arm is None:
        return lambda t, u, f0=0.0: None
    return H.body_radius_fn(H.body_bvh_head_space(body, arm))


def add_curly_drape(g, style):
    dr = style["curly_drape"]
    b = style["bumps"]
    body_r = _body_r()
    f0 = H.SKULL_RINGS[0][4]
    th, clear = dr["thickness"], dr["clearance"]
    rows = dr["rows"]
    cols = []
    for t in dr["cols"]:
        i = round((t % 360) / (360.0 / H.SEG)) % H.SEG
        top = g.hair_vid.get((0, i))
        if top is None:
            raise RuntimeError(f"corina drape: no ring-0 hair vertex at column {t}")
        ptop = g.verts[top]
        radial = Vector((ptop.x, ptop.y - f0, 0))
        r_top = radial.length
        d = radial.normalized()
        u_top = ptop.z
        u_end = dr["ends"][t]
        outer, inner = [top], []
        for j, s in enumerate(rows):
            u = u_top + (u_end - u_top) * s
            r = r_top + dr["flare"][j]
            if 0 < j < len(rows) - 1:
                r += b["out"] if _bump_sign(-j, i) > 0 else -b["in"]
            rb = body_r(t, u, f0) if j > 0 else None
            if rb is not None:
                r = max(r, rb + clear + th)
            if j > 0:
                r = max(r, dr.get("min_r", {}).get(t, 0.0))
                outer.append(g.v(Vector((0, f0, u)) + d * r))
            if j in (0, len(rows) // 2, len(rows) - 1):
                u_in = u + 0.04 if j == 0 else u
                inner.append(g.v(Vector((0, f0, u_in)) + d * (r - th)))
        cols.append((t, d, outer, inner))
    tips_from = dr["tips_from_row"]
    notch = dr["notch"]

    alt = dr.get("tips_alt_row")

    def role(seg, gap):
        if seg >= tips_from or (seg == alt and gap % 2 == 0):
            return "hair_tips"
        return "hair"

    down = Vector((0, 0, -1))
    for gap, ((ta, da, oa, ia), (tb, db, ob, ib)) in enumerate(zip(cols, cols[1:])):
        md = (da + db).normalized()
        n = len(oa)
        for j in range(n - 2):
            if j == alt:
                # colour boundary zigzags: the segment is split along a diagonal that
                # alternates per gap, its lower triangle is caramel (curl ends)
                if gap % 2 == 0:
                    g.face([oa[j], ob[j], ob[j + 1]], "hair", md)
                    g.face([oa[j], ob[j + 1], oa[j + 1]], "hair_tips", md)
                else:
                    g.face([oa[j], ob[j], oa[j + 1]], "hair", md)
                    g.face([ob[j], ob[j + 1], oa[j + 1]], "hair_tips", md)
                continue
            g.face([oa[j], ob[j], ob[j + 1], oa[j + 1]], role(j, gap), md)
        # scalloped curl ends: the bottom edge rises between two column tips
        om_p = (g.verts[oa[-1]] + g.verts[ob[-1]]) / 2
        rise = min(notch, 0.5 * (min(g.verts[oa[-2]].z, g.verts[ob[-2]].z) - om_p.z))
        om = g.v(om_p + Vector((0, 0, rise)))
        for x, y, z in ((oa[-2], ob[-2], om), (oa[-2], om, oa[-1]), (ob[-2], ob[-1], om)):
            g.face([x, y, z], role(n - 2, gap), md)
        # inner side (seen from the front through the gap beside the neck); its bottom
        # edge is straight, the underside rises from it into the scallop
        for j in range(len(ia) - 1):
            g.face([ia[j], ib[j], ib[j + 1], ia[j + 1]], "hair" if j == 0 else "hair_tips", -md)
        g.face([oa[-1], om, ia[-1]], "hair_tips", down + (da - md) - md * 0.3)
        g.face([om, ib[-1], ia[-1]], "hair_tips", down - md * 0.3)
        g.face([om, ob[-1], ib[-1]], "hair_tips", down + (db - md) - md * 0.3)
    # close both ends of the drape (outer rows 0..3 against inner rows 0, mid, end)
    for (t, d, o, i), (t2, d2, o2, i2) in ((cols[0], cols[1]), (cols[-1], cols[-2])):
        away = (d - d2).normalized()
        g.face([o[0], o[1], i[1], i[0]], "hair", away)
        g.face([o[1], o[2], i[1]], "hair", away)
        g.face([o[2], o[3], i[2], i[1]], "hair_tips", away)


def _bang_points(bg):
    """Edge points (theta, u, kind) of the curly bangs, from her right (-) to her left (+):
    each clump is shoulder / tip / shoulder, a notch (or the forehead gap) between two
    clumps, and the two ends on the face-window border."""
    pts = [(-bg["span"], bg["end_u"], "end")]
    clumps = bg["clumps"]
    gap = bg.get("gap")
    for n, (c, hw, tip) in enumerate(clumps):
        if n:
            pc, phw, _ = clumps[n - 1]
            if gap and pc < gap[0] < c:
                pts.append((gap[0], gap[1], "gap"))
            else:
                pts.append((0.5 * (pc + phw + c - hw), bg["notch_u"], "notch"))
        sh, du = bg["shoulder"], bg["shoulder_du"]
        pts += [(c - hw * sh, tip + du, "shoulder"), (c, tip, "tip"), (c + hw * sh, tip + du, "shoulder")]
    pts.append((bg["span"], bg["end_u"], "end"))
    thetas = [p[0] for p in pts]
    if thetas != sorted(thetas) or len(set(thetas)) != len(thetas):
        raise ValueError(f"corina bangs: clump edge points overlap or are out of order: {thetas}")
    return pts


def add_curly_bangs(g, style):
    """Curly bangs over the forehead (replaces the shared fringe, same build: a flap from
    the ring-3 hairline over a convex middle row down to the edge, with a tucked
    underside). The edge is a row of curl clumps: over each clump the middle row bulges
    and the tip flips out and up; notches and the forehead gap recess toward the skull."""
    bg = style["bangs"]
    pts = _bang_points(bg)
    top_ring = 3
    step = 360.0 / H.SEG
    mids, lows, tucks = [], [], []
    for t, u_e, kind in pts:
        if kind == "end":
            # the ends join the side hair: the middle row ends on the ring-2 hair vertex of
            # the window border and the edge on the border line below it, so no wedge opens
            # between the bangs and the side hair (the forehead showed through it)
            i = round((t % 360) / step) % H.SEG
            h1, h2 = g.hair_vid.get((1, i)), g.hair_vid.get((2, i))
            if h1 is None or h2 is None or h1 == g.face_vid.get((1, i)):
                raise RuntimeError(f"corina bangs: no side-hair border vertices at {t} deg")
            p1, p2 = g.verts[h1], g.verts[h2]
            mids.append(h2)
            lows.append(g.v(p1.lerp(p2, (u_e - p1.z) / (p2.z - p1.z))))
            tucks.append(g.v(H.skull_surface(t, u_e) - H.surface_normal(t, u_e) * 0.006))
            continue
        em, el, lift = bg["extra"][kind]
        # the middle row runs at one height (only the depth varies per clump): a middle
        # row that zigzags in height with the edge folds the fan triangles above it, and
        # a folded triangle shows its culled back as a sliver of forehead
        u_m = max(bg["mid_u"], u_e + 0.03)
        mids.append(g.v(H.skull_surface(t, u_m) + H.surface_normal(t, u_m) * (bg["offset_mid"] + em)))
        p, n = H.skull_surface(t, u_e), H.surface_normal(t, u_e)
        lows.append(g.v(p + n * (bg["offset"] + el) + Vector((0, 0, lift))))
        tucks.append(g.v(p - n * 0.006))
    # hairline corners: the ring-3 hair vertices of the face-window columns
    corners = []
    for t in range(-bg["span"], bg["span"] + 1, int(step)):
        vi = g.hair_vid.get((top_ring, round((t % 360) / step) % H.SEG))
        if vi is None:
            raise RuntimeError(f"corina bangs: no ring-{top_ring} hair vertex at {t} deg")
        corners.append((t, vi))

    def out(idx):
        return sum((g.verts[i] for i in idx), Vector()) / len(idx) - H.HEAD_CENTER

    def tri(idx):
        g.face(idx, "hair", out(idx))

    # flap: every middle-row segment fans to its nearest hairline corner; where the
    # nearest corner changes, a triangle bridges the two corners over the shared vertex
    thetas = [p[0] for p in pts]
    prev = None
    for j in range(len(pts) - 1):
        k = min(range(len(corners)), key=lambda c: abs(corners[c][0] - 0.5 * (thetas[j] + thetas[j + 1])))
        if prev is not None:
            for kk in range(prev, k):
                tri([corners[kk][1], corners[kk + 1][1], mids[j]])
        tri([corners[k][1], mids[j], mids[j + 1]])
        prev = k
    if prev != len(corners) - 1 or min(range(len(corners)), key=lambda c: abs(corners[c][0] - thetas[0])) != 0:
        raise RuntimeError("corina bangs: the flap does not span every hairline corner")
    for j in range(len(pts) - 1):
        quad = [mids[j], mids[j + 1], lows[j + 1], lows[j]]
        g.face(quad, "hair", out(quad))
        # tuck strip: the visible underside of the bangs
        g.face([lows[j], lows[j + 1], tucks[j + 1], tucks[j]], "hair", Vector((0, 0.35, -1.0)))


def shape_chin(g, style):
    """Oval face: move the ring-0 face vertices (the jaw line) per |angle| (the chin
    point under them is the style's bottom_pole)."""
    moved = 0
    for (k, i), vi in g.face_vid.items():
        if k != 0:
            continue
        cfg = style["chin"].get(round(abs(_wrap(H.THETAS[i]))))
        if cfg is None:
            continue
        sl, du, df = cfg
        p = g.verts[vi]
        if g.hair_vid.get((k, i)) == vi:
            raise RuntimeError(f"corina chin: ring-0 vertex {i} is shared with the hair")
        g.verts[vi] = Vector((p.x * sl, p.y + df, p.z + du))
        moved += 1
    if moved != len(style["chin"]) * 2 - (1 if 0 in style["chin"] else 0):
        raise RuntimeError(f"corina chin: moved {moved} jaw vertices, expected one per configured angle and side")


def add_lumps(g, style):
    """Curl clumps: low pyramids (lump_sides) sitting on the hair surface (found by
    raycasting the hair built so far), apex drooping like a hanging curl."""
    from mathutils.bvhtree import BVHTree
    polys = [idx for idx, role in g.faces if role in ("hair", "hair_tips")]
    bvh = BVHTree.FromPolygons(g.verts, polys)
    tips_u = style["curly_drape"].get("tips_u", -0.05)
    lumps = []
    for lump in style["lumps"]:
        t, u, w, hh, rise = lump[:5]
        # optional per lump: sides, droop (else lump_sides / lump_droop)
        sides = lump[5] if len(lump) > 5 else style.get("lump_sides", 5)
        droop = lump[6] if len(lump) > 6 else style.get("lump_droop", 0.25)
        lumps.append((t, u, w, hh, rise, sides, droop))
        if t % 180:
            lumps.append((-t, u, w, hh, rise, sides, droop))
    for t, u, w, hh, rise, sides, droop in lumps:
        a = math.radians(t)
        d = Vector((math.sin(a), math.cos(a), 0))
        if u > 1.12:  # crown: cast from above-outside toward the head centre
            o = H.HEAD_CENTER + (d * 0.6 + Vector((0, 0, u - H.HEAD_CENTER.z))).normalized() * 3.0
        else:
            o = Vector((0, 0, u)) + d * 3.0
        target = Vector((0, 0, min(u, 1.0))) if u <= 1.12 else H.HEAD_CENTER
        loc, nor, _i, _dist = bvh.ray_cast(o, (target - o).normalized(), 6.0)
        if loc is None:
            raise RuntimeError(f"corina lump at {t}/{u} missed the hair")
        if nor.dot(o - loc) < 0:
            nor = -nor
        up = Vector((0, 0, 1))
        t1 = up.cross(nor)
        t1 = t1.normalized() if t1.length > 1e-4 else Vector((1, 0, 0))
        t2 = nor.cross(t1).normalized()  # "up" along the surface
        sink = 0.03
        base = []
        for j in range(sides):
            ang = math.pi / 2 + 2 * math.pi * j / sides
            bp = loc + t1 * (math.cos(ang) * w) + t2 * (math.sin(ang) * hh)
            # conform the base corner to the (curved) hair surface, then sink it, so no
            # corner floats above a convex crown and shows as a sliver on the silhouette
            hit = bvh.ray_cast(bp + nor * 0.4, -nor, 0.8)[0]
            base.append(g.v((hit if hit is not None else bp) - nor * sink))
        apex = g.v(loc + nor * rise - t2 * (droop * hh))
        role = "hair_tips" if loc.z < tips_u else "hair"
        for j in range(sides):
            a_, b_ = base[j], base[(j + 1) % sides]
            mid = (g.verts[a_] + g.verts[b_]) / 2
            g.face([a_, b_, apex], role, (mid - loc) + nor * 0.5)


def move_floor(g, style):
    """The shell closes the hair columns with a fan from ring 0 to the bottom pole (the
    chin); with ring 0 pushed far out that fan slopes into the jaw. Re-fan the hair
    columns to a point inside the head above the neck instead, and close the two gaps
    beside the jaw (border strip -> new fan)."""
    bot = g.face_vid.get(("bot", 0))
    if bot is None:
        raise RuntimeError("corina floor: no chin pole vertex")
    ring0_hair = set(_own_hair_verts(g, 0).values())
    centre = g.v(Vector(style.get("floor_centre", (0.0, -0.02, 0.10))))
    keep = []
    refanned = 0
    for idx, role in g.faces:
        if role == "hair" and bot in idx and len(idx) == 3 and all(v in ring0_hair for v in idx if v != bot):
            others = [v for v in idx if v != bot]
            keep.append(([centre] + others, role))
            refanned += 1
            continue
        keep.append((idx, role))
    down = Vector((0, 0, -1))
    border = 0
    for (k, i), vi in g.hair_vid.items():
        if k == 0 and (k, i) in g.face_vid and g.face_vid[(k, i)] != vi:   # window border column
            keep.append(([bot, vi, centre], "hair"))
            border += 1
    if refanned == 0 or border != 2:
        raise RuntimeError(f"corina floor: re-fanned {refanned} hair floor faces, {border} border columns "
                           "(expected some and 2): the shell layout changed")
    # re-orient: Geo.face sorts winding from an outward vector, so rebuild through it
    g.faces[:] = []
    for idx, role in keep:
        if centre in idx:
            g.face(idx, role, down)
        else:
            g.faces.append((idx, role))


def head_parts(g, style, spec):
    counts = [("shell+nose+locks", g.tri_count())]
    shape_chin(g, style)
    reshape_rings(g, style)
    add_shell_bumps(g, style)
    add_curly_bangs(g, style)  # after the shell is final: its ends sit on the side hair
    counts.append(("bangs", g.tri_count()))
    add_curly_drape(g, style)
    counts.append(("drape", g.tri_count()))
    move_floor(g, style)
    counts.append(("floor", g.tri_count()))
    add_lumps(g, style)
    counts.append(("lumps", g.tri_count()))
    print("SGL corina head tris:", counts)


def head_roles(spec, mats):
    return {"hair_tips": smat.accessory_material(mats, "hair_tips", spec["colors"]["hair_tips"],
                                                 base="Hair (HAIR)")}


# ------------------------------------------------------------------ necklace
CHAIN = "#AEB3BA"  # silver; lit it renders near white, shaded mid grey


def add_thin_chain_necklace(ctx):
    """Thin silver chain: a flat strip lying on the torso around the base of the neck,
    dipping into a U on the chest, with a small diamond pendant at the front."""
    obj, arm, mats = ctx["obj"], ctx["arm"], ctx["mats"]
    pal = mats["_palette"]
    bvh, frame = sgl_body.bone_bvh(obj, arm, "Torso", ["Torso"])
    g = Geo()
    n = 20
    width, lift = 0.022, 0.012
    rows = []
    for k in range(n):
        t = math.radians(360.0 * k / n)
        c = math.cos(t)
        front = max(0.0, c) ** 1.6
        u = 0.36 - 0.14 * front + 0.03 * (1 - c) / 2
        d = Vector((math.sin(t), c, 0))
        loc, nor = sgl_body.hit_from(bvh, d * 2.0 + Vector((0, 0, u)), -d)
        if loc is None:
            raise RuntimeError(f"corina necklace: torso not found at theta {math.degrees(t):.0f}")
        rows.append((loc, nor))
    ids = []
    for k, (loc, nor) in enumerate(rows):
        tang = (rows[(k + 1) % n][0] - rows[k - 1][0]).normalized()
        side = tang.cross(nor).normalized()
        p = loc + nor * lift
        ids.append((g.v(p + side * width / 2), g.v(p - side * width / 2), nor))
    for k in range(n):
        a, b = ids[k], ids[(k + 1) % n]
        g.face([a[0], a[1], b[1], b[0]], "chain", (a[2] + b[2]).normalized())
    loc, nor = sgl_body.front_hit(bvh, 0.0, 0.36 - 0.14 - 0.035)
    if loc is not None:
        p = loc + nor * (lift + 0.004)
        s = 0.022
        q = [g.v(p + Vector((0, 0, s))), g.v(p + Vector((s * 0.8, 0, 0))), g.v(p + Vector((0, 0, -s * 1.2))),
             g.v(p + Vector((-s * 0.8, 0, 0)))]
        g.face(q, "chain", nor)
    roles = {"chain": smat.accessory_material(mats, "chain", pal.get("chain", CHAIN))}
    return emit(g, obj, "Torso", frame, roles)


ACCESSORIES = {"thin_chain_necklace": add_thin_chain_necklace}
