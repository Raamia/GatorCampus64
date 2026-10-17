"""Vignesh: short dark wavy-curly hair with volume on top, blue browline glasses
(blue top bar, thin silver lower rims), light stubble along the jaw and chin, huge
toothy grin. Red t-shirt with a white line-art graphic, jeans, white sneakers.

Head space is (l, f, u) = (character's left, forward, up); see sgl_heads.
Built against the reference photos in reference/friends/vignesh/ (photo3 = face,
photo2 = hair outline from the front, photo1 = outfit).

Only the documented hooks are used (HAIR_STYLE, ACCESSORIES, head_parts, head_roles,
post_build) plus sgl_heads' public helpers (ring_point, skull_surface,
surface_normal, THETAS, SEG, HEAD_CENTER, Geo, emit, BoneFrame) and the hair/face
vertex maps build_head leaves on the Geo (hair_vid / face_vid, as add_fringe uses).
"""
import math

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

import sgl_body
import sgl_heads as H
import sgl_materials as smat
from sgl_util import mix_hex

# ------------------------------------------------------------------ hair style
HAIR_STYLE = {
    "base": "short_wavy_curly",
    # the face window ends at 60 deg: the temple columns (60..90) are hair from ring 2
    # up (lowered to the ear top in _shape_hair), like the sideburns in photo2
    "window": 60, "face_bands": ("fan_bottom", 0, 1, 2),
    # base thickness; the dome itself is shaped per vertex by HAIR_OFF below
    "off": {"top": 0.17, "upper": 0.17, "side": 0.055, "back": 0.075},
    # ring 1 (the lowest hair, at the back) close to the head, so the hair tapers into
    # the nape instead of ending in a slab
    "ring_off": {1: 0.035},
    "hang": False,
    # long oval face with a high forehead (photo2: brow-to-hairline is about half of
    # eyes-to-chin): Daniel's tuned skull with a narrower jaw tapering to a lower,
    # more forward chin (photo3), and the crown raised for the high hairline (ring 3)
    "skull": [
        (0.00, 0.25, 0.34, 0.31, 0.07, 2.3),
        (0.36, 0.445, 0.50, 0.49, 0.03, 2.4),
        (0.68, 0.50, 0.48, 0.54, 0.00, 2.3),
        (0.93, 0.44, 0.39, 0.50, -0.02, 2.2),
        (1.06, 0.32, 0.26, 0.38, -0.03, 2.0),
    ],
    "bottom_pole": (0.0, 0.15, -0.16),
    "top_pole": (0.0, -0.03, 1.12),
    # eyes: 64 texels over 0.88 of the face width (a little larger than Daniel's, so
    # the eyes hold their own inside the frames); the grin wider than Daniel's
    "face_layout": {"eyes": (0.0, 0.545, 0.88, 0.40), "mouth": (0.0, 0.23, 0.46, 0.23)},
    "fringe": None, "drape": None, "locks": None,
    # outside the face window: temples and above the ears hair from ring 2, behind the
    # ears and at the back from ring 1 (HAIR_LOW then shapes these edges)
    "hair_bottom": {75: 2, 105: 2, 135: 1, 165: 1},
    "ears": {"theta": 96, "u": 0.48, "h": 0.25, "out": 0.11, "w": 0.08},
    "nose": {"u": 0.39, "half_width": 0.075, "bottom": -0.045, "tip": 0.07, "top": 0.09},
}

# Hair thickness per shell vertex (ring, |theta|): a rounded dome as in photos 2/3.
# Close at the temples and above the ears (ring 2), widest at ring 3 (the dome's
# shoulder, wider than the temples), ring 4 pulled in so the top rounds over instead
# of ending in square corners. The front of ring 3 (the hairline ledge) stays thinner
# than the sides so the hair does not jut out over the forehead.
HAIR_OFF = {
    (2, 60): 0.05, (2, 90): 0.055, (2, 120): 0.06, (2, 150): 0.075, (2, 180): 0.08,
    (3, 0): 0.15, (3, 30): 0.16, (3, 60): 0.175, (3, 90): 0.205, (3, 120): 0.20, (3, 150): 0.185,
    (3, 180): 0.175,
    (4, 0): 0.15, (4, 30): 0.15, (4, 60): 0.155, (4, 90): 0.155, (4, 120): 0.155, (4, 150): 0.155,
    (4, 180): 0.155,
}
# Arched hairline (photos 2/3): the forehead is dome shaped, the hairline is highest in
# the middle and curves down at the temples into the sideburns instead of meeting
# them at a square corner. Border vertices (ring, |theta|) -> u on the skull (both the
# skin and the hair copy move).
HAIRLINE = {(3, 30): 0.915, (3, 60): 0.85}
# lowest hair border vertices (ring, |theta|) -> u: the temple hair slants down to the
# ear top in front of the ears (photo2), over the ear it sits on the ear top, the
# nape hairline at the back is a little below ring 1 (the hair there is thin, ring_off 1)
HAIR_LOW = {(2, 60): 0.69, (2, 90): 0.615, (2, 120): 0.63, (1, 150): 0.29, (1, 180): 0.27}
# Dome cap: the top fan (ring 4 -> pole, the widest flat area of the hair) is split by a
# 6-vertex ring at the even columns, placed DOME_T of the way from ring 4 to the pole
# and pushed DOME_BULGE outward, so the top rounds over in every view (+12 tris)
DOME_T = 0.5
DOME_BULGE = 0.04
DOME_CENTRE = Vector((0.0, -0.03, 0.75))

# Curl clumps on the hair: (theta, u on the skull, radius, height, droop[, sides]).
# Few, broad and low (a soft bump in the silhouette, not a spike); droop tips a clump
# forward/down (curls falling over the hairline). Only the hairline row, seen up close
# in front, is 5-sided; the rest are 4-sided.
CURLS = [
    # hairline, following the arch: high in the middle, lower toward the temples
    (-50, 0.875, 0.10, 0.045, 0.3), (-26, 0.915, 0.105, 0.045, 0.3), (-2, 0.93, 0.10, 0.045, 0.3),
    (22, 0.92, 0.105, 0.045, 0.3), (47, 0.88, 0.10, 0.045, 0.3),
    # temple corners: carry the arch down into the sideburns
    (-64, 0.79, 0.085, 0.045, 0.35, 4), (64, 0.79, 0.085, 0.045, 0.35, 4),
    # around the crown (the dome's shoulder); none on the top itself: the dome cap rounds
    # it, and any clump there stands up from the silhouette in front and side views
    (-150, 1.00, 0.125, 0.045, 0.0, 4), (-95, 0.99, 0.125, 0.045, 0.0, 4), (-38, 1.01, 0.125, 0.045, 0.0, 4),
    (20, 1.01, 0.125, 0.045, 0.0, 4), (80, 0.99, 0.125, 0.045, 0.0, 4), (135, 1.00, 0.125, 0.045, 0.0, 4),
    # sides above the ears, behind the ears, back
    (-112, 0.78, 0.095, 0.045, 0.0, 4), (110, 0.79, 0.095, 0.045, 0.0, 4),
    (-130, 0.50, 0.09, 0.04, 0.0, 4), (128, 0.52, 0.09, 0.04, 0.0, 4),
    (-168, 0.74, 0.11, 0.045, 0.0, 4), (165, 0.62, 0.11, 0.045, 0.0, 4),
]
CURL_SINK = 0.02   # base ring below the hair surface (the clump grows out of the shell)

# ------------------------------------------------------------------ glasses
# heights follow the eye art rows on the eyes rect above (0.0125 per row from u 0.745):
# brows rows 6-7 (u 0.645-0.67), the bar slot rows 8-11 (0.595-0.645), top lash row 12
# (from 0.595), crease row 19 (0.495). The bar fills the slot so the brows sit right on
# it as in photo3; it sits close to the face (gap_front) so that the game camera, which
# looks down, shifts it only a little onto the lashes
GLASSES = {
    "l_in": 0.085,         # inner lens edge (next to the bridge)
    "l_out": 0.40,         # outer lens edge / hinge
    "bar_bottom": 0.599,
    "bar_top_in": 0.642,
    "bar_top_out": 0.645,
    "lens_bottom": 0.415,  # tall lenses as in photo3 (the rims cross the middle of the nose)
    "gap_front": 0.036,    # frame front in front of the face
    "gap_back": 0.010,
    "rim_w": 0.018,
    "bridge": (0.608, 0.634),
    # temple arm: (theta, u, offset from the skull) points behind the hinge; just over
    # the temple hair and the ear top, as close as they can be (fists in hand-to-face
    # animations)
    "arm": ((78, 0.628, 0.072), (104, 0.605, 0.064)),
}

# ------------------------------------------------------------------ stubble
# upper edge of the stubble (u) at the shell's column boundaries (|theta|): the chin
# below the lower lip, rising along the jaw toward the ear
STUBBLE_TOP = {0: 0.115, 30: 0.125, 60: 0.165, 90: 0.215, 120: 0.25}
STUBBLE_MIX = 0.6   # colors.stubble mixed into the skin colour (light stubble that reads)


def _wrap(theta):
    return (theta + 180.0) % 360.0 - 180.0


def _accessories(spec):
    return set(spec.get("build", {}).get("accessories", []))


def _has_vertex_maps(g, what):
    if hasattr(g, "hair_vid") and hasattr(g, "face_vid"):
        return True
    print(f"SGL WARNING: vignesh {what}: head Geo has no hair_vid/face_vid maps, skipped")
    return False


# ------------------------------------------------------------------ hair shaping
def _shape_hair(g):
    """Dome (HAIR_OFF), arched hairline (HAIRLINE), lowered border (HAIR_LOW)."""
    if not _has_vertex_maps(g, "hair shaping"):
        return
    for i, theta in enumerate(H.THETAS):
        a = round(abs(_wrap(theta)))
        for ring in (2, 3, 4):
            hv = g.hair_vid.get((ring, i))
            fv = g.face_vid.get((ring, i))
            if hv is None or hv == fv:
                continue
            u_new = HAIRLINE.get((ring, a))
            off = HAIR_OFF.get((ring, a))
            if u_new is None and off is None:
                continue
            p = H.ring_point(ring, theta) if u_new is None else H.skull_surface(theta, u_new)
            if u_new is not None and fv is not None:
                g.verts[fv] = p.copy()
            if off is None:
                off = (g.verts[hv] - H.ring_point(ring, theta)).length
            g.verts[hv] = p + (p - H.HEAD_CENTER).normalized() * off
        for ring in (1, 2):
            low = HAIR_LOW.get((ring, a))
            hv = g.hair_vid.get((ring, i))
            if low is None or hv is None or hv == g.face_vid.get((ring, i)):
                continue
            p = g.verts[hv]
            g.verts[hv] = Vector((p.x, p.y, low))


def add_dome_cap(g):
    if not _has_vertex_maps(g, "dome cap"):
        return 0
    top = g.hair_vid.get(("top", 0))
    r4 = [g.hair_vid.get((4, i)) for i in range(H.SEG)]
    fan = [n for n, (idx, _role) in enumerate(g.faces) if top in idx]
    if top is None or None in r4 or len(fan) != H.SEG or H.SEG % 2:
        print("SGL WARNING: vignesh dome cap: top fan not found, skipped")
        return 0
    for n in reversed(fan):
        g.faces.pop(n)
    pt = g.verts[top]
    mid = {}
    for i in range(0, H.SEG, 2):
        m = g.verts[r4[i]].lerp(pt, DOME_T)
        mid[i] = g.v(m + (m - DOME_CENTRE).normalized() * DOME_BULGE)
    for i in range(0, H.SEG, 2):
        j = (i + 2) % H.SEG
        a, b, c, ma, mc = r4[i], r4[i + 1], r4[j], mid[i], mid[j]
        for tri in ((ma, a, b), (ma, b, mc), (mc, b, c), (ma, mc, top)):
            centroid = sum((g.verts[x] for x in tri), Vector()) / 3
            g.face(list(tri), "hair", centroid - DOME_CENTRE)
    return len(mid)


def _hair_bvh(g):
    polys = [list(idx) for idx, role in g.faces if role == "hair"]
    return BVHTree.FromPolygons([Vector(v) for v in g.verts], polys)


def add_curls(g, bvh):
    centre = Vector((0.0, 0.0, 0.6))
    up = Vector((0, 0, 1))
    n_ok = 0
    for k, (theta, u, r, h, droop, *rest) in enumerate(CURLS):
        loc = None
        for du in (0.0, 0.01, 0.02, 0.03, 0.045, 0.06):
            target = H.skull_surface(theta, u + du) + H.surface_normal(theta, u + du) * 0.06
            d = (target - centre).normalized()
            loc, nor, _i, _dist = bvh.ray_cast(centre, d, 3.0)
            if loc is not None:
                break
        if loc is None:
            print(f"SGL WARNING: vignesh curl {theta}/{u}: hair surface not found")
            continue
        if nor.dot(d) < 0:
            nor = -nor
        n = (nor * 0.6 + d * 0.4).normalized()
        t1 = n.cross(up)
        if t1.length < 1e-4:
            t1 = Vector((1, 0, 0))
        t1.normalize()
        t2 = n.cross(t1).normalized()
        m = rest[0] if rest else 5
        phase = (k * 0.7) % (2 * math.pi / m)
        ring = [g.v(loc + (t1 * math.cos(phase + 2 * math.pi * j / m) + t2 * math.sin(phase + 2 * math.pi * j / m)) * r
                    - n * CURL_SINK) for j in range(m)]
        fwd = Vector((math.sin(math.radians(theta)), math.cos(math.radians(theta)), 0))
        apex = g.v(loc + n * h + (fwd * 0.5 - up * 0.8) * (droop * h))
        for j in range(m):
            a, b = ring[j], ring[(j + 1) % m]
            mid = (g.verts[a] + g.verts[b]) / 2
            g.face([a, b, apex], "hair", (mid - loc) + n * 0.3)
        n_ok += 1
    return n_ok


# ------------------------------------------------------------------ glasses
def theta_for_l(l, u):
    """Angle on the skull (front half) whose surface point at height u has this l."""
    lo, hi = -89.9, 89.9
    for _ in range(40):
        mid = (lo + hi) / 2
        if H.skull_surface(mid, u).x < l:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def face_point(l, u, gap):
    """Point `gap` in front of the face at (l, u) (pushed between the surface normal
    and straight forward)."""
    t = theta_for_l(l, u)
    p = H.skull_surface(t, u)
    n = H.surface_normal(t, u)
    d = (n * 0.5 + Vector((0, 1, 0)) * 0.5).normalized()
    return p + d * gap


def add_glasses(g):
    G = GLASSES
    up = Vector((0, 0, 1))
    for s in (-1, 1):
        stations = [G["l_in"], 0.245, G["l_out"]]
        prof = []
        for k, l in enumerate(stations):
            a = k / (len(stations) - 1)
            ub = G["bar_bottom"]
            ut = G["bar_top_in"] + (G["bar_top_out"] - G["bar_top_in"]) * a
            ft = face_point(s * l, ut, G["gap_front"])
            fb = face_point(s * l, ub, G["gap_front"])
            bt = face_point(s * l, ut, G["gap_back"])
            bb = face_point(s * l, ub, G["gap_back"])
            prof.append([g.v(ft), g.v(fb), g.v(bb), g.v(bt)])
        for p0, p1 in zip(prof, prof[1:]):
            fwd = (g.verts[p0[0]] + g.verts[p1[0]]) / 2 - (g.verts[p0[3]] + g.verts[p1[3]]) / 2
            g.face([p0[0], p1[0], p1[1], p0[1]], "glasses", fwd)          # front
            g.face([p0[3], p1[3], p1[0], p0[0]], "glasses", up)           # top
            g.face([p0[1], p1[1], p1[2], p0[2]], "glasses", -up)          # bottom
        g.face(prof[-1], "glasses", Vector((s, -0.2, 0)))                 # outer end
        g.face(prof[0], "glasses", Vector((-s, 0, 0)))                    # inner end
        # lower rim: thin silver wire from the bar's outer end round the lens bottom
        lb = G["lens_bottom"]
        lo, li = G["l_out"] - 0.012, G["l_in"] + 0.006
        path = [(lo, G["bar_bottom"] + 0.004), (lo + 0.002, lb + 0.035), (lo - 0.035, lb),
                (li + 0.035, lb), (li, lb + 0.03), (li, G["bar_bottom"] + 0.004)]
        pts = [face_point(s * l, u, G["gap_front"] - 0.01) for l, u in path]
        w = G["rim_w"] / 2
        left, right = [], []
        for k, p in enumerate(pts):
            d = (pts[min(k + 1, len(pts) - 1)] - pts[max(k - 1, 0)]).normalized()
            side = d.cross(Vector((0, 1, 0))).normalized()
            left.append(g.v(p + side * w))
            right.append(g.v(p - side * w))
        for k in range(len(pts) - 1):
            g.face([left[k], left[k + 1], right[k + 1], right[k]], "rims", Vector((0, 1, 0)))
        # temple arm: from the hinge back over the side hair to above the ear
        hinge_t, hinge_b = prof[-1][3], prof[-1][2]
        tops, bots, ins = [hinge_t], [hinge_b], [None]
        for theta, u, off in G["arm"]:
            p = H.skull_surface(s * theta, u)
            n = H.surface_normal(s * theta, u)
            n = Vector((n.x, n.y, 0)).normalized()
            tops.append(g.v(p + n * off + up * 0.013))
            bots.append(g.v(p + n * off - up * 0.013))
            ins.append(g.v(p + n * (off - 0.022) + up * 0.013))
        for k in range(len(tops) - 1):
            mid = (g.verts[tops[k]] + g.verts[tops[k + 1]]) / 2
            out = Vector((mid.x, mid.y * 0.3, 0))
            g.face([tops[k], tops[k + 1], bots[k + 1], bots[k]], "glasses", out)
            if ins[k] is not None:
                g.face([ins[k], ins[k + 1], tops[k + 1], tops[k]], "glasses", up)
            else:
                g.face([tops[k], ins[k + 1], tops[k + 1]], "glasses", up)
    # bridge
    b0, b1 = G["bridge"]
    q = []
    for l in (-G["l_in"], G["l_in"]):
        q.append([g.v(face_point(l, b1, G["gap_front"] - 0.008)), g.v(face_point(l, b0, G["gap_front"] - 0.008)),
                  g.v(face_point(l, b0, G["gap_back"])), g.v(face_point(l, b1, G["gap_back"]))])
    a, b = q
    g.face([a[0], b[0], b[1], a[1]], "glasses", Vector((0, 1, 0)))
    g.face([a[3], b[3], b[0], a[0]], "glasses", up)
    g.face([a[1], b[1], b[2], a[2]], "glasses", -up)


# ------------------------------------------------------------------ stubble
def _find_face(g, vids):
    key = set(vids)
    for n, (idx, _role) in enumerate(g.faces):
        if set(idx) == key:
            return n
    return None


def add_stubble(g, style):
    """Band 0 of the front and side columns is split along STUBBLE_TOP; the part below
    and the chin fan become the "stubble" skin material."""
    if not _has_vertex_maps(g, "stubble"):
        return 0
    rings = style.get("skull") or H.SKULL_RINGS
    u0, u1 = rings[0][0], rings[1][0]
    split = {}

    def split_vertex(i):
        if i in split:
            return split[i]
        ut = STUBBLE_TOP.get(round(abs(_wrap(H.THETAS[i]))))
        a = g.face_vid.get((0, i))
        b = g.face_vid.get((1, i))
        if ut is None or a is None or b is None:
            split[i] = None
        elif ut >= u1 - 1e-6:
            split[i] = b
        else:
            split[i] = g.v(g.verts[a].lerp(g.verts[b], (ut - u0) / (u1 - u0)))
        return split[i]

    changed = 0
    bot = g.face_vid.get(("bot", 0))
    for i in range(H.SEG):
        j = (i + 1) % H.SEG
        tc = abs(_wrap(H.THETAS[i] + 180.0 / H.SEG))
        if tc > 110:
            continue
        # chin underside (fan to the bottom pole)
        fi = _find_face(g, [bot, g.face_vid.get((0, i)), g.face_vid.get((0, j))])
        if fi is not None:
            g.faces[fi] = (g.faces[fi][0], "stubble")
            changed += 1
        # band 0: the lower part becomes stubble, the upper part keeps its role
        quad = [g.face_vid.get((0, i)), g.face_vid.get((0, j)), g.face_vid.get((1, j)), g.face_vid.get((1, i))]
        if None in quad:
            continue
        fi = _find_face(g, quad)
        si, sj = split_vertex(i), split_vertex(j)
        if fi is None or si is None or sj is None:
            continue
        _idx, role = g.faces.pop(fi)
        a_i, a_j, b_j, b_i = quad
        out = sum((g.verts[x] for x in quad), Vector()) / 4 - H.HEAD_CENTER
        g.face([a_i, a_j, sj, si], "stubble", out)
        g.face([si, sj, b_j, b_i], role, out)
        changed += 1
    # no T-junctions: a neighbouring face that still spans the whole ring 0 -> ring 1
    # edge of a split column (behind the jaw, where the stubble ends) gets the split
    # vertex too, so the shell stays closed (no hairline crack along that edge)
    for i, si in split.items():
        a, b = g.face_vid.get((0, i)), g.face_vid.get((1, i))
        if si is None or si == b:
            continue
        for n, (idx, role) in enumerate(g.faces):
            if si in idx:
                continue
            for k in range(len(idx)):
                if {idx[k], idx[(k + 1) % len(idx)]} == {a, b}:
                    g.faces[n] = (idx[:k + 1] + [si] + idx[k + 1:], role)
                    break
    return changed


# ------------------------------------------------------------------ shirt graphic
# White line-art crayfish on the front of the tee (photo1): two long antennae rising
# toward the chest, a carapace with a big open claw on each side, a segmented tail
# running down toward the hem, a fan at its end. Diagonal like the print: the head and
# antennae lean toward his right (negative l), the tail ends near the middle of the
# hem. The shirt front spans about l -0.36..0.44, u -0.20 (hem, middle)..0.46 (neck)
# in the torso frame. Strokes are polylines in the creature's own frame (a along the
# body, head positive; b across it, his left positive), turned by GRAPHIC_TILT and
# placed at GRAPHIC_CENTRE (torso l, u of the carapace centre).
GRAPHIC_CENTRE = (-0.07, 0.11)
GRAPHIC_TILT = 22.0
GRAPHIC_STROKES = [
    [(0.055, 0.0), (0.03, 0.04), (-0.03, 0.04), (-0.055, 0.0), (-0.03, -0.04), (0.03, -0.04),
     (0.055, 0.0)],                                                    # carapace
    [(0.05, 0.015), (0.12, 0.04), (0.195, 0.055)],                     # antennae
    [(0.05, -0.015), (0.12, -0.04), (0.195, -0.055)],
    [(0.025, 0.04), (0.04, 0.11)], [(0.10, 0.10), (0.04, 0.11), (0.08, 0.155)],      # claws:
    [(0.025, -0.04), (0.04, -0.11)], [(0.10, -0.10), (0.04, -0.11), (0.08, -0.155)],  # arm, pincer
    [(-0.055, 0.0), (-0.095, 0.0), (-0.135, 0.0)],                     # tail
    [(-0.08, 0.03), (-0.08, -0.03)], [(-0.112, 0.028), (-0.112, -0.028)],
    [(-0.135, 0.0), (-0.165, 0.038), (-0.18, 0.0), (-0.165, -0.038), (-0.135, 0.0)],  # tail fan
    [(-0.005, 0.04), (-0.025, 0.085)], [(-0.035, 0.035), (-0.065, 0.075)],            # legs
    [(-0.005, -0.04), (-0.025, -0.085)], [(-0.035, -0.035), (-0.065, -0.075)],
]
GRAPHIC_W = 0.022
GRAPHIC_LIFT = 0.015   # >= 1.5 game units in front of the shirt (export rounds to integers)


def add_shirt_graphic():
    obj, arm = bpy.data.objects["Mario Mesh"], bpy.data.objects["Mario"]
    bvh, frame = sgl_body.bone_bvh(obj, arm, "Torso", ["Torso"])
    g = H.Geo()
    cx, cu = GRAPHIC_CENTRE
    t = math.radians(GRAPHIC_TILT)
    da = (-math.sin(t), math.cos(t))   # head direction in (l, u): up, toward his right
    db = (math.cos(t), math.sin(t))    # across the body, toward his left
    w = GRAPHIC_W / 2
    for stroke in GRAPHIC_STROKES:
        pts = [(cx + a * da[0] + b * db[0], cu + a * da[1] + b * db[1]) for a, b in stroke]
        left, right = [], []
        for k, (l, u) in enumerate(pts):
            a = pts[max(k - 1, 0)]
            b = pts[min(k + 1, len(pts) - 1)]
            dl, du = b[0] - a[0], b[1] - a[1]
            norm = math.hypot(dl, du)
            sl, su = -du / norm * w, dl / norm * w   # perpendicular in the (l, u) plane
            hits = [sgl_body.front_hit(bvh, l + sl, u + su), sgl_body.front_hit(bvh, l - sl, u - su)]
            if any(loc is None for loc, _n in hits):
                left = None
                break
            left.append(g.v(hits[0][0] + hits[0][1] * GRAPHIC_LIFT))
            right.append(g.v(hits[1][0] + hits[1][1] * GRAPHIC_LIFT))
        if left is None:
            print(f"SGL WARNING: vignesh shirt graphic: stroke off the torso {stroke}")
            continue
        for k in range(len(pts) - 1):
            g.face([left[k], left[k + 1], right[k + 1], right[k]], "top_detail", Vector((0, 1, 0)))
    return g, frame


# ------------------------------------------------------------------ hooks
def head_parts(g, style, spec):
    acc = _accessories(spec)
    _shape_hair(g)
    add_dome_cap(g)
    add_curls(g, _hair_bvh(g))
    if "stubble" in acc:
        add_stubble(g, style)
    if "glasses_browline_blue" in acc:
        add_glasses(g)


def head_roles(spec, mats):
    acc = _accessories(spec)
    c = spec["colors"]
    roles = {}
    if "glasses_browline_blue" in acc:
        roles["glasses"] = smat.accessory_material(mats, "glasses_top", c["glasses_top"])
        roles["rims"] = smat.accessory_material(mats, "glasses_rim", c["glasses_rim"])
    if "stubble" in acc:
        roles["stubble"] = smat.accessory_material(mats, "stubble", mix_hex(c["skin"], c["stubble"], STUBBLE_MIX),
                                                   base="Skin (SKIN)")
    return roles


# Short sleeves: the shared cut (sgl_body.short_sleeve_ends, sleeve end at 0.66 of the
# upper arm, everything past it skin) builds the sleeve end. His own first fix (the upper
# arm's end cap recoloured to skin past bone-frame u 0.25, the sleeve's last ring flared
# 1.22x) left red slivers poking through the bare forearm at extreme elbow bends (61 f38,
# star dance CD f36); a longer shared sleeve (0.75, 0.82) still shows them, 0.66 does not.


def post_build(ctx):
    spec, mats = ctx["spec"], ctx["mats"]
    obj = bpy.data.objects["Mario Mesh"]
    out = {}
    if spec["colors"].get("top_detail") and "graphic" in spec.get("outfit", {}).get("top", ""):
        g, frame = add_shirt_graphic()
        out["shirt_graphic_tris"] = H.emit(g, obj, "Torso", frame, {"top_detail": mats["top_detail"]})
    smat.compact_material_slots(obj)
    return out


def _in_head(name):
    def fn(ctx):
        return f"head geometry (characters/vignesh.py head_parts, every head variant): {name}"
    return fn


ACCESSORIES = {
    "glasses_browline_blue": _in_head("blue browline bar, silver lower rims, temples"),
    "stubble": _in_head("darker jaw/chin band"),
}
