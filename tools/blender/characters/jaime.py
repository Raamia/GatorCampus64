"""Jaime: big fluffy, messy, windswept medium-brown hair (fringe to the brows, wavy
volume flaring out at the temples), thick dark brows (in the eye texture), silver
over-ear headphones around his neck and a thin silver chain; white tee with a small
dark-red print, khaki shorts, white sneakers, braided leather bracelet.

Reference: reference/friends/jaime/ (photo1 = face, photo3 right = outfit).

Hair: the fluffy_windswept_medium preset only sets up the shell topology (face window,
hair_bottom, fringe); head_parts then re-places every hair vertex of the 12-column shell
from per-ring tables and cuts extra tuft/notch vertices into shell edges, so the outline
is a broad, convex mop (no crown-and-brim step) broken into clumps: stacked side tufts
flaring out above the brows, a jagged crown, flicks behind the ears and at the nape.

NOTE: this module uses sgl_heads/sgl_body internals beyond the documented hooks
(H.SEG/THETAS/ring_point/_wrap/_hair_dir/skull_surface/surface_normal, Geo.hair_vid,
the fringe's side ends welded to the shell (Geo.fringe_welded), SB._ring_hit/front_hit/
radial_hit/bone_bvh). _require() checks the ones whose change would silently break the
sculpt (a 12-column shell with 5 skull rings); a missed fringe weld prints an SGL WARNING.
"""
import math

from mathutils import Vector

import sgl_heads as H
import sgl_materials as smat
import sgl_body as SB
from sgl_util import mix_hex, shade_hex


def _require(g=None):
    """Fail loudly if the shared head builder no longer has the layout the tables
    below are written for."""
    problems = []
    if H.SEG != 12 or [round(t) for t in H.THETAS] != list(range(0, 360, 30)):
        problems.append(f"SEG={H.SEG} (tables assume 12 columns at 30 degrees)")
    if len(H.SKULL_RINGS) != 5:
        problems.append(f"{len(H.SKULL_RINGS)} skull rings (tables assume 5)")
    if g is not None and not hasattr(g, "hair_vid"):
        problems.append("Geo has no hair_vid")
    if problems:
        raise RuntimeError("characters/jaime.py: sgl_heads changed: " + "; ".join(problems))


# ------------------------------------------------------------------ hair
HAIR_STYLE = {
    # skin to 90 degrees: the cheeks show below the side tufts (photo 1); behind 90 degrees
    # the hair hangs over the (hidden) ears down to ring 1, the nape is covered
    "window": 90, "face_bands": ("fan_bottom", 0, 1, 2),
    "hair_bottom": {105: 1},
    # only a starting point: head_parts re-places every shell hair vertex (SHELL_OFF etc.)
    "off": {"top": 0.12, "upper": 0.13, "side": 0.10, "back": 0.10},
    "hang": False,
    # Daniel's oval skull and eye layout (the eye art was drawn for it: brow row 6 starts
    # at u 0.678, just under ring 2), with a broader jaw and a lower mouth and nose (his
    # midface is long: nose bottom ~0.47 and mouth ~0.7 of the brow-to-chin height)
    "skull": [
        (0.00, 0.33, 0.37, 0.33, 0.06, 2.3),
        (0.36, 0.48, 0.50, 0.50, 0.03, 2.4),
        (0.68, 0.50, 0.48, 0.54, 0.00, 2.3),
        (0.86, 0.455, 0.41, 0.50, -0.02, 2.2),
        (0.97, 0.34, 0.29, 0.39, -0.03, 2.0),
    ],
    "bottom_pole": (0.0, 0.13, -0.10),
    "top_pole": (0.0, -0.03, 1.03),
    "face_layout": {"eyes": (0.0, 0.565, 0.84, 0.36), "mouth": (0.0, 0.17, 0.42, 0.21)},
    # fringe of separate pointed clumps hanging from the crown to just above the brows
    # (lo_ring 2 keeps the tips above brow row 6), a slight bulge only (a thick ledge
    # read as a hat band), a small parting at the centre; at the temples (75..90) it
    # sweeps out into the lower side tufts (90 snaps to the tuft tip)
    "fringe": {"kind": "full", "offset": 0.075, "offset_mid": 0.13, "mid_at": 0.5,
               "edge": {-90: 0.69, -75: 0.79, -60: 0.72, -52.5: 0.77, -45: 0.705, -37.5: 0.76,
                        -30: 0.80, -22.5: 0.73, -15: 0.705, -7.5: 0.77, 0: 0.81, 7.5: 0.75,
                        15: 0.705, 22.5: 0.76, 30: 0.79, 37.5: 0.72, 45: 0.705, 52.5: 0.765,
                        60: 0.73, 75: 0.80, 90: 0.69}},
    "drape": None, "ears": False, "locks": None,
    "nose": {"u": 0.35, "half_width": 0.07, "bottom": -0.035, "tip": 0.05, "top": 0.065},
}


# Shell sculpt. Every hair vertex (ring k, column angle) is placed at
#   skull point + hair_dir * OFF + horizontal * SPREAD + up * LIFT  (+ TUFTS extras)
# with OFF/SPREAD/LIFT interpolated over |angle| (0 front, 180 back).
SHELL_OFF = {
    0: {90: 0.06, 120: 0.08, 150: 0.11, 180: 0.08},
    1: {90: 0.05, 120: 0.13, 150: 0.12, 180: 0.14},
    2: {90: 0.31, 120: 0.13, 150: 0.24, 180: 0.18},
    3: {0: 0.17, 30: 0.15, 60: 0.21, 90: 0.27, 120: 0.24, 150: 0.17, 180: 0.21},
    4: {0: 0.17, 30: 0.20, 60: 0.21, 90: 0.23, 120: 0.21, 150: 0.20, 180: 0.17},
}
SHELL_SPREAD = {
    4: {0: 0.0, 30: 0.03, 60: 0.06, 90: 0.08, 120: 0.06, 150: 0.03, 180: 0.0},
}
SHELL_LIFT = {
    0: {90: 0.0, 120: 0.04, 150: -0.05, 180: 0.02},
    1: {90: -0.03, 120: -0.02, 150: 0.02, 180: -0.02},
    2: {90: 0.06, 120: -0.04, 150: 0.05, 180: 0.0},
    3: {0: 0.04, 30: -0.02, 60: 0.03, 90: 0.04, 120: 0.0, 150: -0.03, 180: 0.03},
    4: {0: 0.02, 30: 0.05, 60: 0.06, 90: 0.07, 120: 0.06, 150: 0.04, 180: 0.0},
}
TOP_OFF = 0.27
# the crown whorl sits behind the top of the head, a little to his left: the crown tufts
# radiate forward from it (a centred apex made the crown read as an umbrella)
TOP_SHIFT = Vector((0.03, -0.13, 0.0))
# per-vertex extras (ring, signed column angle): (lift, extra offset); windswept, a bit
# bigger on his right (photo 3)
TUFTS = {
    (4, -90): (0.02, 0.01), (2, -90): (0.02, 0.02), (2, 90): (-0.01, -0.01),
}
# extra vertices cut into shell edges between two hair vertices (ring, |angle|) -> (ring,
# |angle|), mirrored to both sides: (t along the edge, horizontal push, lift). A negative
# push is a notch between two tufts.
EDGE_CUTS = {
    # side outline: three stacked tufts (crown shoulder, temple, brow-level tip) with
    # notches between them, so the side reads as clumps, not a brim
    ((2, 90), (3, 90)): (0.5, -0.09, 0.0),
    ((3, 90), (4, 90)): (0.5, -0.06, -0.01),
    # under the brow-level tip: the side hair tucks in before the sideburn (a hanging
    # lock, not a brim)
    ((1, 90), (2, 90)): (0.45, -0.05, 0.0),
    # behind the ear: notch between the temple tuft and the ear-level flick, the lower
    # edge of the side hair cut into two points (sideburn, flick), and the brow-level tip
    # split from the hair behind it
    ((1, 120), (2, 120)): (0.5, -0.04, 0.0),
    ((1, 90), (1, 120)): (0.5, -0.02, 0.07),
    ((2, 90), (2, 120)): (0.5, -0.04, 0.03),
    ((2, 150), (3, 150)): (0.5, -0.05, 0.0),
    # back: the ring-2 layer ends in points at 150/180 with notches between them
    ((2, 120), (2, 150)): (0.5, -0.04, 0.03),
    ((2, 150), (2, 180)): (0.5, -0.05, 0.04),
}
# crown tufts between the ring-4 columns: these ring-4 edges are cut at a raised point, so
# the crown outline is jagged (signed column-midpoint angle: (lift, extra offset))
CROWN_TUFTS = {15: (0.12, 0.05), 75: (0.10, 0.06), 135: (0.10, 0.05),
               -165: (0.09, 0.05), -105: (0.11, 0.06), -45: (0.13, 0.07)}


def _interp(table, a):
    keys = sorted(table)
    if a <= keys[0]:
        return table[keys[0]]
    if a >= keys[-1]:
        return table[keys[-1]]
    for k0, k1 in zip(keys, keys[1:]):
        if k0 <= a <= k1:
            return table[k0] + (table[k1] - table[k0]) * (a - k0) / (k1 - k0)


def _horiz(p):
    d = Vector((p.x, p.y, 0.0))
    return d.normalized() if d.length > 1e-6 else Vector((0, 0, 0))


def shell_point(k, theta):
    if k == "top":
        return H.TOP_POLE + TOP_SHIFT + Vector((0, 0, TOP_OFF))
    p = H.ring_point(k, theta)
    a = abs(H._wrap(theta))
    lift = _interp(SHELL_LIFT[k], a) if k in SHELL_LIFT else 0.0
    off = _interp(SHELL_OFF[k], a)
    spread = _interp(SHELL_SPREAD[k], a) if k in SHELL_SPREAD else 0.0
    dl, do = TUFTS.get((k, round(H._wrap(theta))), (0.0, 0.0))
    return p + H._hair_dir(k, p) * (off + do) + _horiz(p) * spread + Vector((0, 0, lift + dl))


# ------------------------------------------------------------------ shell surgery
def _cut_edge(g, a, b, p):
    """New vertex at p inserted into the a-b edge of every face that has it (so the
    mesh stays closed: no T-junction). Returns the new vertex id, or None."""
    m = None
    for n, (idx, role) in enumerate(g.faces):
        L = len(idx)
        for k in range(L):
            if {idx[k], idx[(k + 1) % L]} == {a, b}:
                if m is None:
                    m = g.v(p)
                g.faces[n] = (list(idx[:k + 1]) + [m] + list(idx[k + 1:]), role)
                break
    return m


def _newell(pts):
    n = Vector()
    for x, y in zip(pts, pts[1:] + pts[:1]):
        n += x.cross(y)
    return n


def _triangulate(g, idx, prefer=()):
    """Fan triangulation of a polygon, keeping its winding. Roots in `prefer` (the cut
    vertices: tufts fan out from their tip) are tried first; a root is valid when every
    fan triangle faces the same way as the polygon."""
    P = g.verts
    nrm = _newell([P[i] for i in idx])
    best, best_q = None, -1.0
    roots = sorted(range(len(idx)), key=lambda r: idx[r] not in prefer)
    for r in roots:
        order = list(idx[r:]) + list(idx[:r])
        tris = [(order[0], order[k], order[k + 1]) for k in range(1, len(order) - 1)]
        q = 1e9
        for t in tris:
            tn = (P[t[1]] - P[t[0]]).cross(P[t[2]] - P[t[0]])
            per = sum(((P[t[i]] - P[t[(i + 1) % 3]]).length for i in range(3)))
            q = min(q, tn.dot(nrm.normalized()) / max(per * per, 1e-9))
        if q > 1e-4 and idx[r] in prefer:
            return tris
        if q > best_q:
            best, best_q = tris, q
    return best


def _triangulate_all(g, prefer):
    out = []
    for idx, role in g.faces:
        if len(idx) <= 4 and not any(i in prefer for i in idx):
            out.append((idx, role))
            continue
        if len(idx) == 3:
            out.append((idx, role))
            continue
        for t in _triangulate(g, idx, prefer):
            out.append((list(t), role))
    g.faces = out


def _vid(g, k, theta):
    return g.hair_vid.get((k, round((theta % 360) / 30.0) % 12))


def head_parts(g, style, spec):
    """Sculpt the generated shell: every hair vertex re-placed from the tables above,
    tuft/notch vertices cut into the crown ring and the side outline, then the cut
    polygons re-triangulated; the upward faces of the big side/back crown tufts get the
    highlight colour."""
    _require(g)
    for c, vid in g.hair_vid.items():
        k, i = c
        if k == "bot":
            continue
        g.verts[vid] = shell_point(k, H.THETAS[i] if k != "top" else 0.0)
    cuts = set()
    tips = set()   # the big crown tufts: their faces get the highlight colour
    # crown tufts: the ring-4 edges listed in CROWN_TUFTS cut at a raised, pushed-out point
    for i in range(12):
        a, b = _vid(g, 4, i * 30), _vid(g, 4, i * 30 + 30)
        tm = round(H._wrap(i * 30 + 15))
        if tm not in CROWN_TUFTS:
            continue   # smooth there: a tuft on every edge read as a pinwheel from above
        lift, off = CROWN_TUFTS[tm]
        p = (g.verts[a] + g.verts[b]) / 2
        m = _cut_edge(g, a, b, p + (p - H.HEAD_CENTER).normalized() * off + Vector((0, 0, lift)))
        if m is not None:
            cuts.add(m)
            if lift >= HIGHLIGHT["min_lift"] and abs(tm) >= HIGHLIGHT["min_angle"]:
                tips.add(m)
    # side outline tufts/notches (mirrored), welding the fringe's side vertex at +-90
    edges = []
    for ((k1, t1), (k2, t2)), val in EDGE_CUTS.items():
        for s in (-1, 1):
            edges.append(((k1, s * t1), (k2, s * t2), val))
    # the fringe's side ends at +-90 are welded to the shell by the shared builder
    # (sgl_heads.weld_fringe_ends: the flap side runs down the shell edge ring 3 -> ring
    # 2), so the side notch cut into that edge below also cuts the flap's side edge and
    # the fringe stays closed against the side tufts
    welded = getattr(g, "fringe_welded", {})
    if style.get("fringe") and style["fringe"].get("offset_mid") is not None and set(welded) != {-90, 90}:
        print("SGL WARNING: jaime hair: fringe side ends not welded to the shell:", sorted(welded))
    for (k1, t1), (k2, t2), (t, push, lift) in edges:
        a, b = _vid(g, k1, t1), _vid(g, k2, t2)
        if a is None or b is None:
            print("SGL WARNING: jaime hair: no shell edge", (k1, t1), (k2, t2))
            continue
        p = g.verts[a].lerp(g.verts[b], t)
        m = _cut_edge(g, a, b, p + _horiz(p) * push + Vector((0, 0, lift)))
        if m is None:
            print("SGL WARNING: jaime hair: edge not in any face", (k1, t1), (k2, t2))
            continue
        cuts.add(m)
    _triangulate_all(g, cuts)
    _highlight(g, tips)


# ------------------------------------------------------------------ highlight
# "mix": how far from the hair colour toward the spec's hair_highlight (1 = exact; full
# strength flashed as light spikes on top of the head). Only side/back tufts (|angle| >=
# min_angle): light tufts above the forehead read as two horns from the front.
HIGHLIGHT = {"min_lift": 0.09, "min_up": 0.25, "mix": 0.6, "min_angle": 60}


def _highlight(g, tips):
    """Sun-lightened tips (photo 1 is backlit, photo 3 shows lighter ends): the upward
    faces of the big crown tufts below the crown rim get the spec's hair_highlight
    colour (not the top-fan faces: light wedges meeting at the whorl read as an umbrella)."""
    apex = g.hair_vid.get(("top", 0))
    out = []
    for idx, role in g.faces:
        if role == "hair" and apex not in idx and any(i in tips for i in idx):
            n = -_newell([g.verts[i] for i in idx])  # head-space winding normals point inward (Geo.face)
            if n.length > 1e-9 and n.normalized().z > HIGHLIGHT["min_up"]:
                role = "hair_hi"
        out.append((idx, role))
    g.faces = out


def head_roles(spec, mats):
    pal = mats["_palette"]
    hi = mix_hex(pal["hair"], pal.get("hair_highlight") or shade_hex(pal["hair"], 1.4), HIGHLIGHT["mix"])
    return {"hair_hi": smat.accessory_material(mats, "hair_highlight", hi, base="Hair (HAIR)")}


# ------------------------------------------------------------------ accessories
def _torso(ctx, groups=("Torso",)):
    return SB.bone_bvh(ctx["obj"], ctx["arm"], "Torso", list(groups))


def _cup(g, centre, axis, radius, shell, cushion, sides=8):
    """Headphone ear cup around `centre` (the shell/cushion seam): a silver shell with a
    bevelled outer face, on a slightly wider dark cushion whose front rim shows as a
    dark ring around the shell (what makes it read as an ear cup from the front)."""
    axis = axis.normalized()
    a = Vector((0, 0, 1)).cross(axis)
    a = a.normalized() if a.length > 1e-4 else axis.orthogonal().normalized()
    b = axis.cross(a).normalized()

    def ring(off, rad):
        return [g.v(centre + axis * off + (a * math.cos(2 * math.pi * (k + 0.5) / sides)
                                           + b * math.sin(2 * math.pi * (k + 0.5) / sides)) * rad)
                for k in range(sides)]

    front = ring(shell, radius * 0.86)
    shell_back = ring(0.0, radius * 0.94)
    cush_front = ring(0.0, radius * 1.04)
    cush_back = ring(-cushion, radius * 0.96)
    g.face(front, "headphones", axis)
    g.face(cush_back, "headphones_shadow", -axis)

    def band(r0, r1, role, tilt):
        for k in range(sides):
            j = (k + 1) % sides
            mid = (g.verts[r0[k]] + g.verts[r0[j]]) / 2 - centre
            g.face([r0[k], r0[j], r1[j], r1[k]], role, mid - axis * mid.dot(axis) + axis * tilt)

    band(front, shell_back, "headphones", 0.3)
    band(shell_back, cush_front, "headphones_shadow", 1.0)
    band(cush_front, cush_back, "headphones_shadow", 0.0)
    top = centre + b * radius * 0.9 - axis * cushion * 0.5
    return top


def add_headphones_around_neck(ctx):
    """Over-ear headphones worn around the neck (photos 2 and 3): two big round cups
    resting high on the collarbones either side of the chin, outer shells turned
    forward and outward, and the headband (wide yokes) rising from the top of each cup
    along the side of the neck and round the back (hidden under the hair there). Rigid
    on the Torso bone, so the chin dips between the cups in head-down poses."""
    obj, arm, mats = ctx["obj"], ctx["arm"], ctx["mats"]
    pal = mats["_palette"]
    bvh, frame = _torso(ctx)
    g = H.Geo()
    up = Vector((0, 0, 1))
    fwd = Vector((0, 1, 0))
    tops = {}
    for side in (-1, 1):
        loc, n = SB._ring_hit(bvh, CUP["theta"] * side, CUP["u"])
        if loc is None:
            print("SGL WARNING: headphones: torso not found")
            return 0
        axis = (n * CUP["out"] + fwd * CUP["fwd"] + up * CUP["up"]).normalized()
        c = loc + n * CUP["gap"] + axis * CUP["cushion"]
        tops[side] = (_cup(g, c, axis, CUP["r"], CUP["shell"], CUP["cushion"], CUP.get("sides", 8)), n)
    # headband: cup top -> up the side of the neck -> round the back -> other cup top
    pts = [tops[-1]]
    for t, u, push in BAND:
        loc, n = SB._ring_hit(bvh, t, u)
        if loc is None:
            print("SGL WARNING: headphones: band path not found at", t, u)
            return 0
        pts.append((loc + n * push, n))
    pts.append(tops[1])
    hw, ht = BAND_HW, BAND_HT
    up_s, dn_s, iup, idn = [], [], [], []
    for p, n in pts:
        up_s.append(g.v(p + up * hw + n * ht))
        dn_s.append(g.v(p - up * hw + n * ht))
        iup.append(g.v(p + up * hw - n * ht))
        idn.append(g.v(p - up * hw - n * ht))
    for k in range(len(pts) - 1):
        n = (pts[k][1] + pts[k + 1][1]).normalized()
        g.face([up_s[k], up_s[k + 1], dn_s[k + 1], dn_s[k]], "headphones", n)
        g.face([iup[k], iup[k + 1], idn[k + 1], idn[k]], "headphones_shadow", -n)
        g.face([up_s[k], up_s[k + 1], iup[k + 1], iup[k]], "headphones", up)
        g.face([dn_s[k], dn_s[k + 1], idn[k + 1], idn[k]], "headphones_shadow", -up)
    # SM64 lighting (ambient 0.5 + diffuse N.L) washes light colours out to white on lit
    # faces, the same white as the T-shirt: the silver is darkened a little so the cups
    # still read as grey metal/plastic against the shirt
    roles = {"headphones": smat.accessory_material(mats, "headphones",
                                                   shade_hex(pal.get("headphones", "#D6D2CB"), HP_SHADE)),
             "headphones_shadow": smat.accessory_material(
                 mats, "headphones_shadow", shade_hex(pal.get("headphones_shadow", "#A8A39A"), HP_SHADE))}
    return H.emit(g, obj, "Torso", frame, roles)


HP_SHADE = 0.86
# cup placement (Torso frame): raycast angle/height, gap off the surface, axis mix
# (outward / forward / up), radius, shell and cushion depth, sides. Swept over every
# animation (overlapping triangle pairs): higher or more lateral cups clip the jaw and
# the shoulders much more often; this is the highest placement that keeps idle, walk
# and run free of contact.
CUP = {"theta": 48, "u": 0.20, "gap": 0.0, "out": 1.0, "fwd": 0.45, "up": 0.3,
       "r": 0.155, "shell": 0.05, "cushion": 0.045, "sides": 10}
# headband path between the cups (theta, u, offset from the torso surface), from his
# right side round the back of the neck (under the hair) to his left
BAND = [(-72, 0.37, 0.04), (-95, 0.40, 0.035), (-125, 0.42, 0.03), (-155, 0.43, 0.03), (180, 0.435, 0.03),
        (155, 0.43, 0.03), (125, 0.42, 0.03), (95, 0.40, 0.035), (72, 0.37, 0.04)]
BAND_HW, BAND_HT = 0.042, 0.02   # yoke/headband half height and half thickness


def add_thin_chain_necklace(ctx):
    """Thin silver chain: a narrow ribbon hanging in a V from the sides of the neck to a
    small diamond pendant on the upper chest, between the headphone cups. Its silver is
    darkened like the headphones' so it shows as a grey line on the white T-shirt."""
    obj, arm, mats = ctx["obj"], ctx["arm"], ctx["mats"]
    pal = mats["_palette"]
    bvh, frame = _torso(ctx)
    g = H.Geo()
    w = 0.012
    # V from the sides of the neck down to a small pendant on the upper chest
    pts = []
    for l, u in ((-0.15, 0.36), (-0.12, 0.27), (-0.075, 0.17), (-0.03, 0.10), (0.0, 0.085),
                 (0.03, 0.10), (0.075, 0.17), (0.12, 0.27), (0.15, 0.36)):
        loc, n = SB.front_hit(bvh, l, u)
        if loc is None:
            print("SGL WARNING: chain: torso not found")
            return 0
        pts.append((loc + n * 0.012, n))
    left, right = [], []
    for k, (p, n) in enumerate(pts):
        nxt = pts[min(k + 1, len(pts) - 1)][0] - pts[max(k - 1, 0)][0]
        side = nxt.cross(n).normalized()
        left.append(g.v(p + side * w))
        right.append(g.v(p - side * w))
    for k in range(len(pts) - 1):
        n = (pts[k][1] + pts[k + 1][1]).normalized()
        g.face([left[k], left[k + 1], right[k + 1], right[k]], "chain", n)
    # pendant: small diamond below the lowest point
    loc, n = SB.front_hit(bvh, 0.0, 0.05)
    if loc is not None:
        c = loc + n * 0.02
        s = 0.03
        q = [g.v(c + Vector((0, 0, s))), g.v(c + Vector((s * 0.8, 0, 0))), g.v(c - Vector((0, 0, s))),
             g.v(c - Vector((s * 0.8, 0, 0)))]
        g.face(q, "chain", n)
    roles = {"chain": smat.accessory_material(mats, "chain", shade_hex(pal.get("chain", "#C8CCD0"), HP_SHADE))}
    return H.emit(g, obj, "Torso", frame, roles)


ACCESSORIES = {
    "headphones_around_neck": add_headphones_around_neck,
    "thin_chain_necklace": add_thin_chain_necklace,
}


# ------------------------------------------------------------------ outfit details
# not in build.accessories, but part of his outfit (spec "outfit" + photo 3)
LOGO = {"l": 0.20, "u": 0.02, "hw": 0.075, "hh": 0.03}   # small print on his left chest
# dark braided leather on his left wrist; colour from the spec (colors.bracelet), this is the fallback
BRACELET = {"colour": "#3B2B24", "at": 0.72, "h": 0.022, "push": 0.03}
TEE_HEM = 0.62   # pelvis faces above this fraction of the pelvis height become T-shirt


def _tee_over_hips(obj, arm, mats):
    """The loose T-shirt hangs over the top of the shorts: the upper pelvis (Butt) faces
    become top colour, which also straightens Mario's ragged belt line."""
    me = obj.data
    groups = SB.dominant_groups(obj)
    frame = H.BoneFrame(obj, arm, "Torso")
    butt = [p for p, g in zip(me.polygons, groups) if g == "Butt"]
    if not butt:
        return 0
    zs = {p.index: sum(frame.from_local(me.vertices[i].co).z for i in p.vertices) / len(p.vertices) for p in butt}
    lo, hi = min(zs.values()), max(zs.values())
    ti = smat.ensure_slot(obj, mats["top"])
    n = 0
    for p in butt:
        if zs[p.index] > lo + (hi - lo) * TEE_HEM:
            p.material_index = ti
            n += 1
    return n


def _chest_logo(obj, arm, mats):
    """Small dark-red print on his left chest: a word mark over a thinner line (the
    "NEVER / THE RESORT" print of photo 3). Each bar is split into columns laid on the
    curved chest so it does not sink into the surface."""
    bvh, frame = SB.bone_bvh(obj, arm, "Torso", ["Torso"])
    g = H.Geo()
    l0, u0, hw, hh = LOGO["l"], LOGO["u"], LOGO["hw"], LOGO["hh"]
    cols = 3
    for (la, ub, lb, ut) in ((l0 - hw, u0, l0 + hw, u0 + hh), (l0 - hw * 0.8, u0 - hh * 0.9, l0 + hw * 0.8, u0 - hh * 0.35)):
        top, bot = [], []
        for c in range(cols + 1):
            l = la + (lb - la) * c / cols
            for u, row in ((ut, top), (ub, bot)):
                loc, n = SB.front_hit(bvh, l, u)
                if loc is None:
                    return 0
                row.append(g.v(loc + n * 0.014))
        for c in range(cols):
            g.face([top[c], top[c + 1], bot[c + 1], bot[c]], "top_detail", Vector((0, 1, 0)))
    return H.emit(g, obj, "Torso", frame, {"top_detail": mats["top_detail"]})


def _bracelet(obj, arm, mats):
    """Dark braided leather bracelet: an 8-sided band near his left wrist (photo 3),
    rigid on the Left Forearm bone."""
    grp = "Left Forearm"
    bvh, frame = SB.bone_bvh(obj, arm, grp, [grp])
    hand = arm.data.bones.get("Left Hand")
    b = arm.data.bones[grp]
    length = (hand.head_local - b.head_local).length if hand else 0.28
    g = H.Geo()
    sides = 8
    rings = []
    for u in (length * BRACELET["at"] - BRACELET["h"], length * BRACELET["at"] + BRACELET["h"]):
        ring = []
        for k in range(sides):
            loc, _n = SB.radial_hit(bvh, 360.0 * k / sides, u)
            if loc is None:
                print("SGL WARNING: bracelet: forearm surface not found")
                return 0
            rad = Vector((loc.x, loc.y, 0)).normalized()
            ring.append(g.v(loc + rad * BRACELET["push"]))
        rings.append(ring)
    lo, hi = rings
    for k in range(sides):
        j = (k + 1) % sides
        mid = (g.verts[lo[k]] + g.verts[lo[j]]) / 2
        g.face([lo[k], lo[j], hi[j], hi[k]], "bracelet", Vector((mid.x, mid.y, 0)))
    role = smat.accessory_material(mats, "bracelet", mats["_palette"].get("bracelet", BRACELET["colour"]))
    return H.emit(g, obj, grp, frame, {"bracelet": role})


# wing-cap wings: Mario's wing roots sit inside the big side tufts and the crown; they
# move out and up to the hair surface (applied by build_character, sgl_body.move_wings)
WING_SHIFT = (0.22, -0.02, 0.08)  # head space (l, f, u), mirrored for the right wing


def post_build(ctx):
    """Outfit details on the finished body (before the metal body is rebuilt from it)."""
    import bpy
    obj, arm, mats = bpy.data.objects["Mario Mesh"], bpy.data.objects["Mario"], ctx["mats"]
    SB.set_action(arm, SB.REST_ACTION)
    return {"tee_over_hips_faces": _tee_over_hips(obj, arm, mats),
            "chest_logo_tris": _chest_logo(obj, arm, mats),
            "bracelet_tris": _bracelet(obj, arm, mats)}
