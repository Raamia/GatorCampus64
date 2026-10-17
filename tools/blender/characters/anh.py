"""Anh: straight black mushroom cut with side-swept bangs, thick black rectangular
glasses, Argentina #10 home jersey (white with sky-blue stripes, black collar with a
sky-blue rim, three black stripes down each sleeve, black cuffs, black 10 on the back),
black shorts, white socks, white sneakers.

Josh (based_on anh) and Donald (based_on josh) inherit this module, so every piece
here is driven by the spec that is being built:
  - the glasses only when "glasses_thick_rectangular" is in build.accessories
  - jersey stripes / number / socks only when listed in build.accessories
  - every colour comes from spec["colors"] (with neutral fallbacks)
"""
import math

from mathutils import Vector

import sgl_body
import sgl_heads as H
import sgl_materials as smat
from sgl_body import _prism, _ring_hit, bone_bvh, dominant_groups, hit_from
from sgl_heads import BoneFrame, Geo, emit

GLASSES = "glasses_thick_rectangular"


def _accessories(spec):
    return spec.get("build", {}).get("accessories", [])


# ------------------------------------------------------------------ hair
# Head-space reminders (sgl_heads): l = character's left, f = forward, u = up; theta 0 =
# front, +90 = his left. Rings below are the skull; the eye band is ring 1 -> ring 2.
HAIR_STYLE = {
    "base": "straight_fringe_medium",
    # round, youthful face: full cheeks (ring 1) tapering to a small soft chin (photo 2):
    # a narrow jaw ring and the chin pole a little lower than the cheeks would give alone
    "skull": [
        (0.04, 0.30, 0.36, 0.33, 0.06, 2.2),
        (0.38, 0.50, 0.50, 0.50, 0.03, 2.3),
        (0.68, 0.515, 0.48, 0.54, 0.00, 2.3),
        (0.86, 0.465, 0.41, 0.50, -0.02, 2.2),
        (0.97, 0.345, 0.29, 0.39, -0.03, 2.0),
    ],
    "bottom_pole": (0.0, 0.12, -0.05),
    "top_pole": (0.0, -0.03, 1.07),
    # square texels (the artist's layout): 64 texels over 0.86 of the face; the mouth at the
    # same texel size (half the eye rect in both directions). Eye content centre u 0.572,
    # lips u 0.205: about 0.6 of the eye -> chin distance, as in photos 2/3
    "face_layout": {"eyes": (0.0, 0.565, 0.86, 0.43), "mouth": (0.0, 0.225, 0.43, 0.215)},
    "window": 90, "face_bands": ("fan_bottom", 0, 1, 2),
    # mushroom/bowl cut: a smooth dome with volume all round, the sides hanging straight
    "off": {"top": 0.12, "upper": 0.10, "side": 0.07, "back": 0.08},
    "ring_off": {2: 0.08},
    "hang": False,
    # side-swept bangs: a small parting just left of centre (+7.5, the only place the
    # forehead shows), the long sweep falls to his right; over the lenses the strand
    # tips end behind the brow bar of the glasses (u 0.65-0.68, just above the eye art at
    # 0.614), the temples hang lower into the side curtains. 15-degree steps (7.5 only at
    # the parting): the strand tips over the lenses are hidden by the brow bar, so finer
    # clumps there only cost triangles (about 55 per head)
    "fringe": {"kind": "full", "offset": 0.012, "offset_mid": 0.08, "mid_at": 0.5, "lo_ring": 1,
               "edge": {-90: 0.47, -75: 0.54, -60: 0.62,
                        # the long sweep over his right lens: strand tips behind the brow bar
                        -45: 0.655, -30: 0.67, -15: 0.68,
                        0: 0.71, 7.5: 0.745,  # the parting, just left of centre
                        15: 0.70, 30: 0.665, 45: 0.65,
                        60: 0.62, 75: 0.54, 90: 0.47}},
    # the side curtains of the bowl cut, in front of (and over) the ears, down to about
    # the bottom of the glasses at the front and the jaw at the tip (photos 1-3)
    "locks": {"theta_inner": 64, "theta_outer": 102, "theta_tip": 86, "u_top": 0.82, "u_mid": 0.46,
              "u_tip": 0.32, "offset_inner": 0.05, "offset_outer": 0.10},
    # the hair covers the ears (no ear geometry) and stops at ring 1 beside them (jaw
    # below is skin); behind them it reaches ring 0, the back of the head the nape
    "hair_bottom": {105: 1, 135: 0, 165: 0},
    "drape": None,
    "ears": False,
    # small, soft nose; its tip clearly below the bottom rim of the glasses (u 0.405), as in
    # photos 2/3 (bottom vertex u ~0.355, tip ~0.375)
    "nose": {"u": 0.385, "half_width": 0.075, "bottom": -0.03, "tip": 0.055, "top": 0.06},
}


# ------------------------------------------------------------------ glasses (head geometry)
# Frame layout in eye-texture texels (square texels: eye rect width / 64), relative to the
# eye centre (texture x 15.0 / 49.0 continuous -> l = +-0.2656 x the eye rect width,
# u = rect centre + half a texel). The eye art is 18 x 7 texels; the lens opening keeps
# 3 texels of skin round it, so the black rim never touches the lashes.
FRAME = {
    # lens opening, in texels from the eye centre: the eye sits in the upper part of the
    # lens, a little toward the nose (photos 2/3), and the lens reaches the side hair;
    # the bottom rim (u 0.405) stays above the nose tip, as in the photos
    "inner_top": 6.5, "inner_bottom": 10.0, "inner_nasal": 12.0, "inner_temporal": 14.0,
    "rim_top": 3.0, "rim_side": 3.0, "rim_bottom": 2.4,   # thick frames, a heavier brow bar
    "chamfer": 2.0,      # outer corners cut by this many texels (rounded frames); not the
                         # nasal-top corner, where the bridge joins
    "offset": 0.045,     # front of the frame, forward of the skull at the same (l, u)
    "depth": 0.026,      # front-to-back thickness of the frame
    "bend_theta": 30.0,  # skull facet column the frame bends on: the nasal part hugs the face
    "temple_yaw": 20.0,  # the temporal part turns back only this much (degrees), so its end
                         # stands off the temple like real frames instead of wrapping like goggles
    "bridge_u": 7.5,     # bridge centre above the eye centre (texels): along the top rim
    "bridge_hh": 1.4,    # bridge half height (texels)
    "arm_r": 0.016,      # temple arm radius
}


def _theta_at(l, u):
    """Angle of the skull's front surface point at (l, u) (bisection; the skull is convex)."""
    lo, hi = -89.0, 89.0
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if H.skull_surface(mid, u).x < l:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _skull_front_f(l, u):
    """Forward (f) coordinate of the skull's front surface at (l, u)."""
    return H.skull_surface(_theta_at(l, u), u).y


def _box_faces(g, front, back, role, outward_hint):
    """Walls joining a closed front loop to its back loop (same length, same order)."""
    n = len(front)
    cen = sum((g.verts[i] for i in front), Vector()) / n
    for k in range(n):
        j = (k + 1) % n
        mid = (g.verts[front[k]] + g.verts[front[j]]) / 2
        g.face([front[k], front[j], back[j], back[k]], role, (mid - cen) + outward_hint)


def _frame_point(l, u, back=False):
    """Frame vertex at (l, u). The front view keeps the exact texel layout (only f is
    computed): out to the bend column the frame is a fixed distance forward of the skull,
    beyond it a flatter plane (temple_yaw), never closer to the skull than `offset`."""
    F = FRAME
    f = _skull_front_f(l, u) + F["offset"]
    l_bend = H.skull_surface(F["bend_theta"], u).x
    if abs(l) > l_bend:
        f_bend = _skull_front_f(math.copysign(l_bend, l), u) + F["offset"]
        f = max(f, f_bend - (abs(l) - l_bend) * math.tan(math.radians(F["temple_yaw"])))
    return Vector((l, f - (F["depth"] if back else 0.0), u))


def add_glasses(g, spec):
    """Thick black rectangular frames: per lens a front ring bent on the skull's 30-degree
    facet column (so it hugs the round face), outer walls for thickness, the walls of
    the lens opening, a bridge along the top rim and temple arms into the side hair."""
    ex, eu, ew, eh = H.FACE_LAYOUT["eyes"]
    tx = ew / 64.0
    ty = eh / 32.0
    uc = eu + 0.5 * ty  # eye content centre (row 15.5 of 32)
    F = FRAME
    o_top = uc + (F["inner_top"] + F["rim_top"]) * ty
    o_bot = uc - (F["inner_bottom"] + F["rim_bottom"]) * ty
    i_top = uc + F["inner_top"] * ty
    i_bot = uc - F["inner_bottom"] * ty
    for side in (-1, 1):
        lc = ex + side * 0.2656 * ew
        o_n = lc - side * (F["inner_nasal"] + F["rim_side"]) * tx
        o_t = lc + side * (F["inner_temporal"] + F["rim_side"]) * tx
        i_n, i_t = lc - side * F["inner_nasal"] * tx, lc + side * F["inner_temporal"] * tx

        def bend(u):
            return side * H.skull_surface(F["bend_theta"], u).x

        # inner loop: nose-top, bend-top, temple-top, temple-bottom, bend-bottom, nose-bottom;
        # the outer loop follows it with the temple and nose-bottom corners chamfered, each
        # outer vertex paired with the inner corner it is joined to on the front face
        cx, cy = side * F["chamfer"] * tx, F["chamfer"] * ty
        i2d = [(i_n, i_top), (bend(i_top), i_top), (i_t, i_top), (i_t, i_bot), (bend(i_bot), i_bot), (i_n, i_bot)]
        o2d = [((o_n, o_top), 0), ((bend(o_top), o_top), 1),
               ((o_t - cx, o_top), 2), ((o_t, o_top - cy), 2),
               ((o_t, o_bot + cy), 3), ((o_t - cx, o_bot), 3),
               ((bend(o_bot), o_bot), 4),
               ((o_n + cx, o_bot), 5), ((o_n, o_bot + cy), 5)]
        of = [g.v(_frame_point(l, u)) for (l, u), _k in o2d]
        ob = [g.v(_frame_point(l, u, True)) for (l, u), _k in o2d]
        inf = [g.v(_frame_point(l, u)) for l, u in i2d]
        ib = [g.v(_frame_point(l, u, True)) for l, u in i2d]
        fwd = Vector((side * 0.3, 1.0, 0.0))
        n_o = len(o2d)
        for a in range(n_o):
            b = (a + 1) % n_o
            ka, kb = o2d[a][1], o2d[b][1]
            if ka == kb:  # chamfer: a triangle to the inner corner
                g.face([of[a], of[b], inf[ka]], "glasses", fwd)
            else:
                g.face([of[a], of[b], inf[kb], inf[ka]], "glasses", fwd)
        _box_faces(g, of, ob, "glasses", Vector())
        cen = sum((g.verts[i] for i in inf), Vector()) / 6
        for k in range(6):
            j = (k + 1) % 6
            mid = (g.verts[inf[k]] + g.verts[inf[j]]) / 2
            g.face([inf[k], inf[j], ib[j], ib[k]], "glasses", cen - mid)
        # temple arm: from the back of the temple-top corner along the side of the head,
        # ending inside the side hair above the ear
        start = _frame_point(o_t - side * tx, o_top - F["rim_top"] * ty * 0.5, True)
        th_end, u_end = side * 100.0, uc + 0.07
        end = H.skull_surface(th_end, u_end) + H.surface_normal(th_end, u_end) * 0.02
        _prism(g, [start, end], F["arm_r"], "glasses", sides=3, cap_end=False)
    # bridge: a short bar along the top rim, its ends buried in both nasal rims
    bu = uc + F["bridge_u"] * ty
    bh = F["bridge_hh"] * ty
    lb = abs(ex + 0.2656 * ew - (F["inner_nasal"] + F["rim_side"] * 0.5) * tx)
    q = {}
    for name, l in (("r", -lb), ("l", lb)):
        q[name] = [g.v(_frame_point(l, bu + bh)), g.v(_frame_point(l, bu - bh)),
                   g.v(_frame_point(l, bu - bh, True)), g.v(_frame_point(l, bu + bh, True))]
    rf, lf = q["r"], q["l"]
    g.face([rf[0], lf[0], lf[1], rf[1]], "glasses", Vector((0, 1, 0)))
    g.face([rf[0], rf[3], lf[3], lf[0]], "glasses", Vector((0, 0, 1)))
    g.face([rf[1], lf[1], lf[2], rf[2]], "glasses", Vector((0, 0, -1)))


def head_parts(g, style, spec):
    if GLASSES in _accessories(spec):
        add_glasses(g, spec)


def head_roles(spec, mats):
    if GLASSES not in _accessories(spec):
        return {}
    pal = mats["_palette"]
    return {"glasses": smat.accessory_material(mats, "glasses", pal.get("glasses", pal["hair"]))}


# ------------------------------------------------------------------ body helpers
def _plane_local(frame, p0, p1, p2):
    """Plane through three head/torso-space points, as (co, normal) in mesh-local space."""
    a, b, c = (frame.to_local(p) for p in (p0, p1, p2))
    n = (b - a).cross(c - a)
    return a, n.normalized()


def _centroid(obj, frame, poly):
    me = obj.data
    pts = [frame.from_local(me.vertices[i].co) for i in poly.vertices]
    return sum(pts, Vector()) / len(pts)


# face cutting / limb band helpers (first written here, now shared in sgl_body)
_cut_faces = sgl_body.cut_faces
_tri_count = sgl_body.tri_count
_limb_axis = sgl_body.limb_axis


def _recolour_limb_bands(obj, arm, group, bone_a, bone_b, bands):
    return sgl_body.recolour_limb_bands(obj, arm, group, bone_a, bone_b, bands, tag="anh")


# ------------------------------------------------------------------ jersey
# Stripe sectors around the torso axis (degrees from the front, + = his left). The cut
# planes are vertical planes through the axis, so each one also cuts the back at
# theta + 180: boundaries at +-14 / +-36 / +-62 give the same pattern behind. Front
# (photo 3): blue centre stripe, white, a blue stripe at each side; white under the arms.
STRIPE_EDGES = (14.0, 36.0, 62.0)
# only the visible walls of the torso are cut: not the cap under the head and not the
# part inside the shorts (keeps the triangle count down)
STRIPE_U = (-0.26, 0.42)
STRIPE_MAX_NU = 0.8
STRIPE_SNAP = 0.03  # a stripe edge may pass through a vertex this close instead of cutting a sliver
TORSO_F0 = 0.035  # torso axis (forward offset of the torso's centre, Torso frame)
# accessory pieces laid on the torso must not be raycast onto each other (the stripes are
# cut into the torso itself, so they stay in)
NOT_IN_TORSO_BVH = ("Top Trim (ACC)", "Jersey Gold (ACC)", "Jersey Number (ACC)")
SLEEVE = (0.50, 0.66)  # cuff band of the short sleeve, as fractions shoulder -> elbow
# the jersey cuts its own sleeve (cuff band + bare arm, add_jersey_stripes): no shared
# short-sleeve cut for Anh (sgl_body.short_sleeve_ends). Josh and Donald (plain tees, own
# modules) get the shared cut, which ends the sleeve at the same SLEEVE[1].
SHORT_SLEEVE_END = None
SOCK_TOP = 0.50        # sock top, as a fraction knee -> ankle


def _stripe_at(theta):
    a = abs(theta)
    a = min(a, 180.0 - a)  # back mirrors the front
    e1, e2, e3 = STRIPE_EDGES
    return a < e1 or e2 <= a < e3


def add_jersey_stripes(ctx):
    """Argentina home shirt: sky-blue vertical stripes cut into the white torso (centre
    stripe + one each side, front and back), black collar, short sleeves ending in a black
    cuff band, and (with colors.jersey_gold) two small gold badges on the chest."""
    obj, arm, mats, spec = ctx["obj"], ctx["arm"], ctx["mats"], ctx["spec"]
    pal = mats["_palette"]
    me = obj.data
    frame = BoneFrame(obj, arm, "Torso")
    before = _tri_count(obj)
    groups = dominant_groups(obj)
    ids = []
    for p, gname in zip(me.polygons, groups):
        if gname != "Torso":
            continue
        pts = [frame.from_local(me.vertices[i].co) for i in p.vertices]
        c = sum(pts, Vector()) / len(pts)
        nrm = (pts[1] - pts[0]).cross(pts[2] - pts[0])
        if STRIPE_U[0] <= c.z <= STRIPE_U[1] and nrm.length > 0 and abs(nrm.normalized().z) < STRIPE_MAX_NU:
            ids.append(p.index)
    planes = []
    for e in STRIPE_EDGES:
        for s in (-1, 1):
            t = math.radians(s * e)
            d = Vector((math.sin(t), math.cos(t), 0.0))
            p0 = Vector((0.0, TORSO_F0, 0.0))
            planes.append(_plane_local(frame, p0, p0 + Vector((0, 0, 1)), p0 + d))
    ids = _cut_faces(obj, ids, planes, snap=STRIPE_SNAP)
    stripe = smat.accessory_material(mats, "top_stripes", pal.get("top_stripes", pal["top_detail"]))
    si = smat.ensure_slot(obj, stripe)
    top_idx = smat.ensure_slot(obj, mats["top"])
    n = 0
    for i in ids:
        p = me.polygons[i]
        if p.material_index != top_idx:
            continue
        c = _centroid(obj, frame, p)
        theta = math.degrees(math.atan2(c.x, c.y - TORSO_F0))
        if _stripe_at(theta):
            p.material_index = si
            n += 1
    tris = _tri_count(obj) - before
    print(f"SGL anh: jersey stripes: {n} torso faces striped, +{tris} tris")
    trim = smat.accessory_material(mats, "top_trim", pal.get("top_trim", pal["top_detail"]))
    # short jersey sleeves: the sleeve ends in a black cuff band partway down the upper
    # arm, bare arm below it
    if spec.get("build", {}).get("sleeves", "long") == "short":
        for side in ("Left", "Right"):
            tris += _recolour_limb_bands(obj, arm, f"{side} Arm Color", f"{side} Arm Color", f"{side} Forearm",
                                         [(SLEEVE[0], SLEEVE[1], trim), (SLEEVE[1], 1.0, mats["skin"])])
    tris += add_collar(ctx, trim, stripe)
    tris += add_shoulder_stripes(ctx, trim)
    if pal.get("jersey_gold"):
        tris += add_badges(ctx, smat.accessory_material(mats, "jersey_gold", pal["jersey_gold"]))
    return tris


# The three black stripes over each shoulder (photos 2/3: the most visible trim), on
# the sleeves from the shoulder seam down to the cuff band. (Their short run over the
# top of the torso is not modelled: Mario's head covers the torso top in every view.)
# Rows at these fractions shoulder -> cuff band of the white sleeve; stripes centred on
# these angles round the rest-pose upper arm (0 = its front, 90 = its outer side). In
# Mario's in-game poses the arm is raised sideways and rest angles 30-70 face up/out (the
# top of the sleeve, checked on the In-Game Example pose): where the stripes run on a
# real jersey with the arm out, and what the game camera (behind, above) sees.
STRIPE3_SLEEVE_ROWS = (0.03, 0.35, 0.67, 0.98)
STRIPE3_SLEEVE_PHI = (30.0, 50.0, 70.0)
STRIPE3_SLEEVE_HW = 6.0   # degrees
STRIPE3_LIFT = 0.01


def add_shoulder_stripes(ctx, mat):
    obj, arm = ctx["obj"], ctx["arm"]
    frame = BoneFrame(obj, arm, "Torso")
    tris = 0
    max_lift = 0.0
    for side_name, s in (("Left", 1), ("Right", -1)):
        grp = f"{side_name} Arm Color"
        if grp not in obj.vertex_groups:
            continue
        abvh, _f = bone_bvh(obj, arm, "Torso", [grp])
        a_loc, b_loc = (frame.from_local(p) for p in _limb_axis(obj, arm, grp, f"{side_name} Forearm"))
        axis = b_loc - a_loc
        if axis.length < 1e-6:
            continue
        axis.normalize()
        me = obj.data
        gi = obj.vertex_groups[grp].index
        proj = [(frame.from_local(v.co) - a_loc).dot(axis) for v in me.vertices
                if any(x.group == gi and x.weight > 0.4 for x in v.groups)]
        lo, hi = min(proj), max(proj)
        s0 = lo + (hi - lo) * SLEEVE[0]  # the cuff band starts here
        # radial frame round the arm axis: front (f) and outer (s * l) directions
        fwd = Vector((0, 1, 0))
        fwd = (fwd - axis * fwd.dot(axis)).normalized()
        out = axis.cross(fwd) if axis.cross(fwd).x * s > 0 else -axis.cross(fwd)
        def surf(phi, frac):
            """Sleeve surface point at (angle, fraction shoulder -> cuff) and the radial
            direction it was cast along (None if missed)."""
            t = math.radians(phi)
            d = fwd * math.cos(t) + out * math.sin(t)
            c = a_loc + axis * (lo + (s0 - lo) * frac)
            loc, _nor = hit_from(abvh, c + d * 1.0, -d)
            return loc, d

        rows = STRIPE3_SLEEVE_ROWS
        g = Geo()
        for phi_c in STRIPE3_SLEEVE_PHI:
            phis = (phi_c - STRIPE3_SLEEVE_HW, phi_c, phi_c + STRIPE3_SLEEVE_HW)
            pts = {(phi, k): surf(phi, fr_) for phi in phis for k, fr_ in enumerate(rows)}
            if any(loc is None for loc, _d in pts.values()):
                print(f"SGL WARNING: anh shoulder stripes: sleeve surface not found ({grp}, {phi_c})")
                continue
            # the sleeve bulges between the rows: lift each row so that the flat stripe
            # segments stay STRIPE3_LIFT above the surface along their whole length
            lift = [STRIPE3_LIFT] * len(rows)
            for k in range(len(rows) - 1):
                need = 0.0
                for phi in phis:
                    pa, pb = pts[(phi, k)][0], pts[(phi, k + 1)][0]
                    for t in (0.2, 0.4, 0.6, 0.8):
                        loc, d = surf(phi, rows[k] + (rows[k + 1] - rows[k]) * t)
                        if loc is not None:
                            need = max(need, (loc - pa.lerp(pb, t)).dot(d))
                lift[k] = max(lift[k], STRIPE3_LIFT + need)
                lift[k + 1] = max(lift[k + 1], STRIPE3_LIFT + need)
            max_lift = max(max_lift, *lift)
            e0, e1 = ([g.v(pts[(phi, k)][0] + pts[(phi, k)][1] * lift[k]) for k in range(len(rows))]
                      for phi in (phis[0], phis[2]))
            dmid = pts[(phi_c, 1)][1]
            for k in range(len(rows) - 1):
                g.face([e0[k], e0[k + 1], e1[k + 1], e1[k]], "stripe3", dmid)
        tris += emit(g, obj, grp, frame, {"stripe3": mat})
    print(f"SGL anh: shoulder stripes +{tris} tris (max lift {max_lift:.3f})")
    return tris


def add_collar(ctx, trim, rim=None):
    """Round black jersey collar: a low band around the base of the neck, dipping into
    a shallow V at the front; its top edge (the inner rim, rim material) is sky blue on
    the real shirt."""
    obj, arm = ctx["obj"], ctx["arm"]
    bvh, frame = bone_bvh(obj, arm, "Torso", ["Torso"])
    g = Geo()
    cols = 10
    up = Vector((0, 0, 1))
    low, top, top_in = [], [], []
    for k in range(cols):
        t = 360.0 * k / cols
        c = math.cos(math.radians(t))
        front = max(0.0, c)
        u_b = 0.43 - 0.05 * front ** 3      # small V at the front
        loc, n = _ring_hit(bvh, t, u_b, TORSO_F0)
        if loc is None:
            print(f"SGL WARNING: anh collar: torso not found at theta {t}")
            return 0
        hgt = 0.045
        low.append(g.v(loc + n * 0.012 - up * 0.01))
        top.append(g.v(loc + n * 0.0 + up * hgt - n * 0.02))
        top_in.append(g.v(loc + up * hgt - n * 0.035))
    for k in range(cols):
        j = (k + 1) % cols
        mid = (g.verts[low[k]] + g.verts[low[j]]) / 2
        rad = Vector((mid.x, mid.y - TORSO_F0, 0)).normalized()
        g.face([low[k], low[j], top[j], top[k]], "trim", rad + up * 0.3)
        g.face([top[k], top[j], top_in[j], top_in[k]], "rim", up)  # the inside is under the jaw
    return emit(g, obj, "Torso", frame, {"trim": trim, "rim": rim or trim})


def _decal(g, bvh, outline, origin_f, direction, lift):
    """Vertices of a flat outline (list of (l, u)) laid onto the torso surface by
    raycasts along `direction` from f = origin_f, lifted `lift` along the surface normal.
    None if a ray misses."""
    ids = []
    for l, u in outline:
        loc, nor = hit_from(bvh, Vector((l, origin_f, u)), direction)
        if loc is None:
            return None
        ids.append(g.v(loc + nor * lift))
    return ids


def add_badges(ctx, gold):
    """Simplified gold crests: the federation shield on his left chest and the
    champions badge on the centre stripe."""
    obj, arm = ctx["obj"], ctx["arm"]
    bvh, frame = bone_bvh(obj, arm, "Torso", ["Torso"], exclude_materials=NOT_IN_TORSO_BVH)
    g = Geo()
    fwd = Vector((0, 1, 0))
    shields = [
        (0.20, 0.25, 0.042, 0.052),     # AFA crest, his left chest
        (0.0, 0.215, 0.034, 0.046),     # champions badge, centre stripe
    ]
    for lc, uc, hw, hh in shields:
        outline = [(lc - hw, uc + hh), (lc + hw, uc + hh), (lc + hw, uc - hh * 0.2), (lc, uc - hh),
                   (lc - hw, uc - hh * 0.2)]
        # fan round a raycast centre so the shield follows the curved chest
        ids = _decal(g, bvh, outline + [(lc, uc)], 2.0, Vector((0, -1, 0)), 0.012)
        if ids:
            ring, c = ids[:-1], ids[-1]
            for k in range(len(ring)):
                g.face([ring[k], ring[(k + 1) % len(ring)], c], "gold", fwd)
    return emit(g, obj, "Torso", frame, {"gold": gold})


# block "10": glyphs in (l, u) on the back; seen from behind the viewer's left is the
# character's left (+l), so the "1" sits at +l and the "0" at -l
NUMBER = {"u_lo": 0.02, "u_hi": 0.31, "digit_w": 0.135, "gap": 0.045, "stroke": 0.042}


def add_jersey_number(ctx):
    obj, arm, mats = ctx["obj"], ctx["arm"], ctx["mats"]
    pal = mats["_palette"]
    bvh, frame = bone_bvh(obj, arm, "Torso", ["Torso"], exclude_materials=NOT_IN_TORSO_BVH)
    mat = smat.accessory_material(mats, "jersey_number", pal.get("jersey_number", pal.get("top_trim", pal["top_detail"])))
    g = Geo()
    N = NUMBER
    lo, hi, w, gap, s = N["u_lo"], N["u_hi"], N["digit_w"], N["gap"], N["stroke"]
    back = Vector((0, -1, 0))

    def decal(outline):
        ids = _decal(g, bvh, outline, -2.0, Vector((0, 1, 0)), 0.012)
        if ids:
            g.face(ids, "num", back)
        return ids

    def strip(l0, l1, us):
        """Vertical bar l0..l1 over the heights us (quads following the surface)."""
        a = _decal(g, bvh, [(l0, u) for u in us], -2.0, Vector((0, 1, 0)), 0.012)
        b = _decal(g, bvh, [(l1, u) for u in us], -2.0, Vector((0, 1, 0)), 0.012)
        if a is None or b is None:
            return
        for k in range(len(us) - 1):
            g.face([a[k], b[k], b[k + 1], a[k + 1]], "num", back)

    third = (hi - lo) / 3
    # "1": a bar a little right of its cell centre (viewer's view) and a flag at the top
    # pointing to the viewer's left (+l)
    bw = s * 1.15
    b0 = gap / 2 + w / 2 - bw / 2 - 0.012
    strip(b0, b0 + bw, [lo, lo + third, lo + 2 * third, hi])
    decal([(b0 + bw, hi), (b0 + bw + 0.055, hi - 0.06), (b0 + bw + 0.055, hi - 0.06 - s * 0.9),
           (b0 + bw, hi - s * 1.1)])
    # "0": rectangular ring with chamfered outer corners, cell -(gap/2 + w) .. -gap/2
    l_out, l_in = -(gap / 2 + w), -gap / 2
    c = s * 0.6
    mids = [lo + s, lo + third, lo + 2 * third, hi - s]
    strip(l_in - s, l_in, mids)
    strip(l_out, l_out + s, mids)
    decal([(l_out, hi - s), (l_in, hi - s), (l_in - c, hi), (l_out + c, hi)])
    decal([(l_out + c, lo), (l_in - c, lo), (l_in, lo + s), (l_out, lo + s)])
    return emit(g, obj, "Torso", frame, {"num": mat})


# ------------------------------------------------------------------ socks
def add_white_socks(ctx):
    """Crew socks: the lower part of each shin (Leg) in the socks colour."""
    obj, arm, mats = ctx["obj"], ctx["arm"], ctx["mats"]
    pal = mats["_palette"]
    mat = smat.accessory_material(mats, "socks", pal.get("socks", pal["shoes"]))
    tris = 0
    for side, shoe in (("Left", "Left Shoe"), ("Right", "Right Shoe")):
        tris += _recolour_limb_bands(obj, arm, f"{side} Leg", f"{side} Leg", shoe, [(SOCK_TOP, 1.0, mat)])
    return tris


def _glasses_on_head(ctx):
    return 0  # built as head geometry in head_parts (every head variant)


ACCESSORIES = {
    GLASSES: _glasses_on_head,
    "jersey_stripes": add_jersey_stripes,
    "jersey_number_10_back": add_jersey_number,
    "white_socks": add_white_socks,
}
