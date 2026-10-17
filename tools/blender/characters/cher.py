"""Cher: long straight black hair well past the shoulders, parted slightly to her
right with an open forehead and wispy face-framing layers; soft round face; blue
collared button-up shirt with rolled short sleeves, jeans, white sneakers.

Hair = the shared long-hair shell (sgl_heads, hang=True) with an arched side-part
hairline and a sleek, rounded crown, plus (head_parts):
  - a straight curtain of her own (cher_drape): from the back of the head down to the
    middle of the back, over the shoulders, and two front panels that fall in front
    of the shoulders down the chest; the bottom edge is cut into strand tips
  - face-framing layers (shared add_face_locks, tuned) over the window border
Everything is rigid on the head bone, kept clear of the torso (rest pose) by a
raycast against the body.

Outfit (ACCESSORIES "shirt_collar"): the shared collar/placket/buttons, a chest
pocket, and turned-up cuffs on the forearms that hide Mario's sleeve/forearm
junction (add_elbow_cuffs).

post_build: bleeds the face-texture ink colours into the neighbouring transparent
texels (no light halo around brows/lashes/lips on a shaded face) and reports the
head/curtain triangle counts.
"""
import math
import os

import bpy
from mathutils import Vector

import sgl_body
import sgl_heads as H
import sgl_materials as smat
from sgl_heads import Geo, emit

HAIR_STYLE = {
    "base": "long_straight_past_shoulders",
    "window": 60, "face_bands": ("fan_bottom", 0, 1, 2),
    # sleek straight hair, flat to the head on top (review: the first crown read as
    # a boxy helmet): thin hair on the crown and a crown that narrows and rounds off
    # above the temples (rings 3-4 and the top pole below the shared skull's)
    "off": {"top": 0.04, "upper": 0.04, "side": 0.06, "back": 0.075},
    "hang": True,
    # soft round face: fuller jaw/chin ring, cheeks a little wider and squarer
    "skull": [
        (0.10, 0.39, 0.39, 0.34, 0.06, 2.3),
        (0.42, 0.535, 0.50, 0.50, 0.03, 2.4),
        (0.74, 0.55, 0.48, 0.54, 0.00, 2.3),
        (0.98, 0.46, 0.38, 0.47, -0.02, 2.0),
        (1.115, 0.31, 0.23, 0.33, -0.03, 2.0),
    ],
    "top_pole": (0.0, -0.03, 1.17),
    "bottom_pole": (0.0, 0.11, -0.06),
    # mouth: same texel size as the eyes (0.45 / 32 = 0.90 / 64)
    "face_layout": {"mouth": (0.0, 0.26, 0.45, 0.225)},
    # side part at -15 (her right). Open, arched forehead: the hairline is high next
    # to the part and falls to the outer brow ends at the temples; the bigger sweep
    # (her left) comes in lower than the right side. Edge stays above the brows (u 0.72).
    "fringe": {"kind": "side_part", "offset": 0.045, "offset_mid": 0.07, "mid_at": 0.5,
               "edge": {-60: 0.74, -45: 0.755, -30: 0.86, -15: 0.955, 0: 0.91, 15: 0.855,
                        30: 0.80, 45: 0.75, 60: 0.74}},
    # wispy face-framing layers from the temples to the jaw
    "locks": {"theta_inner": 53, "theta_outer": 68, "theta_tip": 60, "u_top": 0.78, "u_mid": 0.40,
              "u_tip": 0.17, "offset_inner": 0.03, "offset_outer": 0.075},
    "drape": None,  # built in head_parts (cher_drape)
    "ears": False,
    "nose": {"u": 0.43, "half_width": 0.045, "bottom": -0.03, "tip": 0.036, "top": 0.055},
    # ---- Cher-only keys (read by head_parts)
    # curtain columns for her LEFT side and the back centre (mirrored to her right),
    # ordered around the back: (top, theta at the head, theta at the tips, tip height u,
    # inward taper, clearance from the torso). top "jaw": just outside the jaw at the
    # face-window border (ring 0); top "hair": on the ring-0 edge of the hair shell
    # (between its vertices if not a multiple of 30).
    #   jaw/60/90  front panel falling in front of the shoulder down the chest (tips
    #              0.07 lower than the first final build: her hair falls well past
    #              the chest in the photo)
    #   105        stops at the shoulder top: Mario's shoulders sit right under the
    #              head, so the side hair parts there (front panel / back curtain)
    #   135..180   down the back to mid-back, extra clearance at the tips (the head
    #              nods/turns against the torso in the idle and walk cycles)
    "cher_drape": {
        "cols": [
            ("jaw", 60, 30, -0.32, -0.10, 0.05),
            ("hair", 60, 42, -0.39, 0.10, 0.05),
            ("hair", 90, 60, -0.34, 0.14, 0.05),
            ("hair", 105, 106, 0.01, 0.0, 0.05),
            ("hair", 135, 138, -0.30, 0.10, 0.09),
            ("hair", 157.5, 159, -0.40, 0.18, 0.09),
            ("hair", 180, 180, -0.44, 0.20, 0.09),
        ],
        "jaw_off": 0.025,
        "mid_s": 0.45, "thickness": 0.06, "notch": 0.08, "min_notch": 0.045,
    },
}


# ------------------------------------------------------------------ hair
def _body_r():
    body = bpy.data.objects["Mario Mesh"]
    arm = bpy.data.objects["Mario"]
    return H.body_radius_fn(H.body_bvh_head_space(body, arm))


def _mirrored(cols):
    """Left-side + back-centre columns -> full list ordered around the back (60 .. 300)."""
    out = list(cols)
    for c in reversed(cols):
        if c[1] % 360 in (0, 180):
            continue
        out.append((c[0], 360 - c[1], 360 - c[2]) + tuple(c[3:]))
    return out


def _ring0_top(g, theta):
    """(outer vertex, position) on the ring-0 hair edge at theta (multiple of 15)."""
    a = (theta % 360) / 30.0
    i0 = math.floor(a + 1e-9)
    frac = a - i0
    v0 = g.hair_vid.get((0, i0 % H.SEG))
    if v0 is None:
        raise RuntimeError(f"cher_drape: no ring-0 hair vertex at theta {i0 * 30}")
    if frac < 1e-6:
        return v0, g.verts[v0]
    v1 = g.hair_vid[(0, (i0 + 1) % H.SEG)]
    p = g.verts[v0].lerp(g.verts[v1], frac)
    return g.v(p), p


def _jaw_top(g, theta, off, f0):
    p = H.ring_point(0, theta)
    d = Vector((p.x, p.y - f0, 0)).normalized()
    p = p + d * off
    return g.v(p), p


def _out(a, b, below):
    """Outward hint for a curtain quad: columns run in increasing theta (around the
    back), rows run down, so (next column - this column) x down points away from the
    head axis (and toward the front for a radial jaw->hair segment)."""
    return (b - a).cross(below)


def add_cher_drape(g, style):
    cfg = style["cher_drape"]
    body_r = _body_r()
    th = cfg["thickness"]
    mid_s = cfg["mid_s"]
    f0 = H.SKULL_RINGS[0][4]
    cols = []
    for kind, t_top, t_end, u_end, taper, clear in _mirrored(cfg["cols"]):
        if kind == "jaw":
            top, ptop = _jaw_top(g, t_top, cfg.get("jaw_off", 0.02), f0)
        else:
            top, ptop = _ring0_top(g, t_top)
        r_top = Vector((ptop.x, ptop.y - f0, 0)).length
        u_top = ptop.z
        outer, inner, dirs = [top], [], []
        for n, s in enumerate((0.0, mid_s, 1.0)):
            t = math.radians(t_top + (t_end - t_top) * s)
            d = Vector((math.sin(t), math.cos(t), 0.0))
            u = u_top + (u_end - u_top) * s
            r = r_top - taper * (s ** 0.7)
            if n > 0:
                rb = body_r(math.degrees(t), u, f0)
                if rb is not None:
                    r = max(r, rb + clear + th)
                outer.append(g.v(Vector((0, f0, u)) + d * r))
            u_in = u + 0.04 if n == 0 else u
            inner.append(g.v(Vector((0, f0, u_in)) + d * (r - th)))
            dirs.append(d)
        cols.append((t_top, dirs, outer, inner))

    V = g.verts
    down = Vector((0, 0, -1))
    notch = cfg.get("notch", 0.0)
    for (ta, da, oa, ia), (tb, db, ob, ib) in zip(cols, cols[1:]):
        o0 = _out(V[oa[0]], V[ob[0]], down)
        o1 = _out(V[oa[1]], V[ob[1]], down)
        g.face([oa[0], ob[0], ob[1], oa[1]], "hair", o0)
        g.face([ia[0], ib[0], ib[1], ia[1]], "hair", -o0)
        # strand tips: the bottom edge rises between two column tips (not on the short
        # pieces over the shoulders, where the notch would be a sliver: 4 tris saved)
        om_p = (V[oa[2]] + V[ob[2]]) / 2
        im_p = (V[ia[2]] + V[ib[2]]) / 2
        rise = min(notch, 0.45 * (min(V[oa[1]].z, V[ob[1]].z) - om_p.z))
        if rise < cfg.get("min_notch", 0.0):
            g.face([oa[1], ob[1], ob[2], oa[2]], "hair", o1)
            g.face([ia[1], ib[1], ib[2], ia[2]], "hair", -o1)
            g.face([oa[2], ob[2], ib[2], ia[2]], "hair", down + o1.normalized() * 0.3)
            continue
        om = g.v(om_p + Vector((0, 0, rise)))
        im = g.v(im_p + Vector((0, 0, rise)))
        for x, y, z in ((oa[1], ob[1], om), (oa[1], om, oa[2]), (ob[1], ob[2], om)):
            g.face([x, y, z], "hair", o1)
        for x, y, z in ((ia[1], ib[1], im), (ia[1], im, ia[2]), (ib[1], ib[2], im)):
            g.face([x, y, z], "hair", -o1)
        on = o1.normalized() * 0.3
        g.face([oa[2], om, im, ia[2]], "hair", down + on)
        g.face([om, ob[2], ib[2], im], "hair", down + on)
    # close the two front ends of the curtain
    for (t, d, o, i), (t2, d2, o2, i2) in ((cols[0], cols[1]), (cols[-1], cols[-2])):
        for n in range(2):
            away = (V[o[n]] + V[o[n + 1]]) / 2 - (V[o2[n]] + V[o2[n + 1]]) / 2
            g.face([o[n], o[n + 1], i[n + 1], i[n]], "hair", away)


def straighten_fringe_ends(g, style):
    """The fringe's convex middle row (offset_mid) also bulges at the two edge columns
    that snap to the face-window border (+-60), so the flap's side edge bows out past
    the straight hair edge next to it and a sliver of forehead skin shows through from
    the side. Move those two middle-row vertices onto the straight shell edge."""
    fr = style.get("fringe") or {}
    mid_off = fr.get("offset_mid")
    if mid_off is None:
        return 0
    lo_ring, top_ring = fr.get("lo_ring", 2), 3
    u_lo, u_hi = H.SKULL_RINGS[lo_ring][0], H.SKULL_RINGS[top_ring][0]
    moved = 0
    for t, u_edge in fr["edge"].items():
        i = round((t % 360) / 30.0) % H.SEG
        if abs(H.THETAS[i] - (t % 360)) > 1e-6:
            continue
        u_e = max(u_lo + 0.005, min(u_hi - 0.02, u_edge))
        if not (u_e <= u_lo + 0.02 and (lo_ring, i) in g.hair_vid and (lo_ring, i) in g.face_vid):
            continue  # not snapped to the border
        u_m = u_e + (u_hi - u_e) * fr.get("mid_at", 0.45)
        p = H.skull_surface(t, u_m) + H.surface_normal(t, u_m) * mid_off
        vi = next((k for k, q in enumerate(g.verts) if (q - p).length < 1e-6), None)
        if vi is None:
            continue
        a, b = g.verts[g.hair_vid[(lo_ring, i)]], g.verts[g.hair_vid[(top_ring, i)]]
        g.verts[vi] = a.lerp(b, (p.z - a.z) / (b.z - a.z))
        moved += 1
    return moved


HEAD_STATS = {}


def head_parts(g, style, spec):
    fr = style.get("fringe") or {}
    moved = straighten_fringe_ends(g, style)
    if fr.get("offset_mid") is not None and moved == 0:
        # the shared add_fringe changed (or the edge no longer snaps at +-60): the
        # temple skin sliver this fix hides would be back
        print("SGL WARNING: cher straighten_fringe_ends moved no vertices; check the temples "
              "(head_side preview) for a sliver of forehead skin beside the fringe")
    n0 = g.tri_count()
    add_cher_drape(g, style)
    HEAD_STATS.update({"fringe_end_vertices_straightened": moved, "curtain_tris": g.tri_count() - n0,
                       "head_tris": g.tri_count()})
    print(f"SGL cher head: {HEAD_STATS}")


# ------------------------------------------------------------------ outfit
def add_chest_pocket(ctx):
    """Patch pocket on her left chest (photo 1): shirt colour, raised a little off the
    shirt, with a darker hem band along its top and darker side walls; same torso
    surface sampling as the shared collar."""
    obj, arm, mats = ctx["obj"], ctx["arm"], ctx["mats"]
    bvh, frame = sgl_body.bone_bvh(obj, arm, "Torso", ["Torso"])
    u_top = None
    for k in range(60):
        u = 0.30 + k * 0.004
        loc, _n = sgl_body.front_hit(bvh, 0.0, u)
        if loc is not None:
            u_top = u
    if u_top is None:
        print("SGL WARNING: cher pocket: torso surface not found")
        return 0
    cfg = POCKET
    g = Geo()

    def on(l, u, off):
        loc, n = sgl_body.front_hit(bvh, l, u)
        return None if loc is None else loc + n * off

    l0, l1 = cfg["l"]
    u0, u1 = u_top - cfg["u"][0], u_top - cfg["u"][1]
    uh = u0 - cfg["hem"]
    corners = [(l0, u0), (l1, u0), (l1, uh), (l0, uh)]
    body_pts = [(l0, uh), (l1, uh), (l1, u1 + cfg["point"]), ((l0 + l1) / 2, u1), (l0, u1 + cfg["point"])]
    hem = [on(l, u, cfg["raise"]) for l, u in corners]
    pk = [on(l, u, cfg["raise"]) for l, u in body_pts]
    if any(q is None for q in hem + pk):
        print("SGL WARNING: cher pocket: torso surface not found")
        return 0
    out = Vector((0, 1, 0))
    g.face([g.v(q) for q in hem], "pocket_hem", out)
    ids = [g.v(q) for q in pk]
    g.face(ids, "pocket", out)
    # side walls down to the shirt so the raised edge reads from an angle
    base = [g.v(on(l, u, -0.004)) for l, u in body_pts]
    cen = sum((g.verts[i] for i in ids), Vector()) / len(ids)
    for a in range(len(ids)):
        b = (a + 1) % len(ids)
        if a == 0:
            continue  # top edge sits under the hem
        mid = (g.verts[ids[a]] + g.verts[ids[b]]) / 2
        g.face([ids[a], ids[b], base[b], base[a]], "pocket_hem", (mid - cen) + out * 0.3)
    return emit(g, obj, "Torso", frame, {"pocket": mats["top"], "pocket_hem": mats["top_detail"]})


def add_elbow_cuffs(ctx):
    """Rolled short sleeves. Mario's upper arm ("<side> Arm Color", the sleeve) is a
    short stub whose end overlaps the top of the forearm: with short sleeves the
    skin forearm pokes out through the sleeve end as a jagged skin notch with a
    blue hook (and the shared rolled_cuffs, on the upper arm, are buried in that
    same intersection). Here the turned-up cuff band sits on the FOREARM, just
    below the sleeve end and a little wider than both, so it hides the
    sleeve/forearm junction in every pose and moves with the forearm; the
    forearm's top cap (inside the sleeve, it shows when the elbow bends) becomes
    shirt colour so nothing skin-coloured shows above the cuff."""
    obj, arm, mats = ctx["obj"], ctx["arm"], ctx["mats"]
    me = obj.data
    cfg = CUFF
    tris = recol = 0
    top = smat.ensure_slot(obj, mats["top"])
    tucked = 0
    for side in sgl_body.ARMS:
        grp = f"{side} Forearm"
        if grp not in obj.vertex_groups or grp not in arm.data.bones:
            print(f"SGL WARNING: cher cuffs: no {grp}")
            continue
        # the sleeve's end cap reaches past the elbow (into the cuff's height) and is
        # wider there than the forearm: pull it in so it stays inside the cuff band
        upper = f"{side} Arm Color"
        if upper in obj.vertex_groups and upper in arm.data.bones:
            ufr = sgl_body.BoneFrame(obj, arm, upper)
            ui = obj.vertex_groups[upper].index
            for v in me.vertices:
                if any(gg.group == ui and gg.weight > 0.4 for gg in v.groups):
                    q = ufr.from_local(v.co)
                    if q.z > cfg["sleeve_end_u"]:
                        k = cfg["sleeve_end_k"]
                        v.co = ufr.to_local(Vector((q.x * k, q.y * k, q.z)))
                        tucked += 1
        bvh, frame = sgl_body.bone_bvh(obj, arm, grp, [grp])
        gi = obj.vertex_groups[grp].index
        vs = {v.index for v in me.vertices if any(gg.group == gi and gg.weight > 0.4 for gg in v.groups)}
        for poly in me.polygons:
            if all(i in vs for i in poly.vertices) and \
                    all(frame.from_local(me.vertices[i].co).z < cfg["cap_u"] for i in poly.vertices):
                poly.material_index = top
                recol += 1
        g = Geo()
        n = cfg["sides"]
        half = math.radians(180.0 / n)
        # the forearm's cross-sections over the cuff's height (dense radial samples);
        # every cuff edge is placed outside their support line, so no forearm
        # corner pokes through the band between two cuff vertices
        u0, u1 = cfg["u"]
        pts = []
        for m in range(5):
            for k in range(48):
                loc, _nor = sgl_body.radial_hit(bvh, 7.5 * k, u0 + (u1 - u0) * m / 4)
                if loc is not None:
                    pts.append(Vector((loc.x, loc.y)))
        if len(pts) < 200:
            print(f"SGL WARNING: cher cuffs: {grp} surface not found")
            continue

        def support(t):
            d = Vector((math.sin(t), math.cos(t)))
            return max(q.dot(d) for q in pts)
        rings = []
        for u, push in ((u0, cfg["push"][0]), (u1, cfg["push"][1])):
            ring, lip = [], []
            for k in range(n):
                t = 2 * math.pi * (k + 0.5) / n
                d = Vector((math.sin(t), math.cos(t), 0.0))
                r = max(support(t - half), support(t + half)) / math.cos(half)
                ring.append(g.v(d * (r + push) + Vector((0, 0, u))))
                # the lip turns in to just inside the forearm: no gap into the cuff
                lip.append(g.v(d * (r * cfg["lip"]) + Vector((0, 0, u))))
            rings.append((ring, lip))
        if len(rings) != 2:
            print(f"SGL WARNING: cher cuffs: {grp} surface not found")
            continue
        (hi, lip_hi), (lo, lip_lo) = rings  # hi = toward the elbow (sleeve), lo = toward the hand
        for k in range(n):
            j = (k + 1) % n
            mid = (g.verts[lo[k]] + g.verts[lo[j]]) / 2
            out = Vector((mid.x, mid.y, 0))
            g.face([hi[k], hi[j], lo[j], lo[k]], "cuff", out)
            g.face([lo[k], lo[j], lip_lo[j], lip_lo[k]], "cuff", Vector((0, 0, 1)) + out * 0.2)
            g.face([hi[j], hi[k], lip_hi[k], lip_hi[j]], "cuff", Vector((0, 0, -1)) + out * 0.2)
        tris += emit(g, obj, grp, frame, {"cuff": mats["top_detail"]})
    return {"tris": tris, "forearm_cap_faces_recoloured": recol, "sleeve_end_vertices_tucked": tucked}


def add_shirt(ctx):
    """Her blue button-up: the shared collar/placket/buttons, a patch pocket on her
    left chest and turned-up cuffs on the rolled short sleeves (add_elbow_cuffs)."""
    out = {"collar": sgl_body.add_shirt_collar(ctx), "pocket": add_chest_pocket(ctx)}
    if SHIRT.get("cuffs"):
        out["cuffs"] = add_elbow_cuffs(ctx)
    return out


# torso frame (l = her left, u up from the torso bone): pocket box below the torso top
POCKET = {"l": (0.075, 0.235), "u": (0.25, 0.39), "hem": 0.035, "point": 0.025, "raise": 0.014}
SHIRT = {"cuffs": True}  # the spec's rolled sleeves (add_elbow_cuffs)
# CUFF, forearm frame (u from the elbow toward the hand, bone length 0.2): the band
# spans u, an octagon fitted around the forearm's cross-section and pushed out by
# push (top, bottom); lip: its inner edges (x the fitted octagon, just inside the
# forearm); cap_u: forearm faces entirely above it (inside the sleeve) become shirt
# colour; sleeve_end_u / _k: upper-arm vertices past sleeve_end_u (its own bone
# frame, length 0.22) are pulled toward the arm axis by k, into the cuff
CUFF = {"sides": 8, "u": (-0.025, 0.07), "push": (0.016, 0.012), "lip": 0.86, "cap_u": 0.0,
        "sleeve_end_u": 0.25, "sleeve_end_k": 0.72}
ACCESSORIES = {"shirt_collar": add_shirt}


# ------------------------------------------------------------------ face texture edges
FACE_TEXTURES = ("eyes_open", "eyes_half", "eyes_closed", "eyes_left", "eyes_right", "eyes_up",
                 "eyes_down", "eyes_dead", "mouth_grin")


def bleed_face_edges(char_id):
    """The keyed face textures keep the skin RGB in their alpha-0 texels. With
    bilinear filtering and the face combiner (TEXEL0 - SHADE) * TEXEL0_ALPHA + SHADE,
    that skin RGB is mixed into the edge of every brow/lash/lip and draws a light
    peach halo around them wherever the face is shaded darker than the skin (side
    and 3/4 views). Give each transparent texel next to an opaque one the mean colour
    of its opaque neighbours instead (alpha stays 0, so the alpha mask and the clamp
    edges are unchanged): the filtered edge then fades from the ink to the shaded
    skin. Done on the loaded images (what Fast64 exports) and their processed PNGs."""
    import numpy as np
    from sgl_util import write_png
    out = {}
    for name in FACE_TEXTURES:
        img = bpy.data.images.get(f"{char_id}_{name}")
        if img is None:
            print(f"SGL WARNING: cher bleed: image {char_id}_{name} not found")
            continue
        w, h = img.size
        a = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
        op = a[..., 3] > 0.5
        acc = np.zeros((h, w, 3), np.float32)
        cnt = np.zeros((h, w), np.float32)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                sh_op = np.zeros_like(op)
                sh_rgb = np.zeros_like(acc)
                ys = slice(max(dy, 0), h + min(dy, 0))
                yd = slice(max(-dy, 0), h + min(-dy, 0))
                xs = slice(max(dx, 0), w + min(dx, 0))
                xd = slice(max(-dx, 0), w + min(-dx, 0))
                sh_op[yd, xd] = op[ys, xs]
                sh_rgb[yd, xd] = a[ys, xs, :3]
                acc += sh_rgb * sh_op[..., None]
                cnt += sh_op
        edge = ~op & (cnt > 0)
        a[edge, :3] = acc[edge] / cnt[edge][:, None]
        a[~op, 3] = 0.0
        img.pixels[:] = a.ravel()
        img.update()
        img.pack()  # a modified image packs its current pixels
        path = bpy.path.abspath(img.filepath)
        if path and os.path.isfile(path):
            q = np.clip(np.round(np.flipud(a) * 255), 0, 255).astype(np.uint8)
            write_png(path, [[tuple(int(v) for v in px) for px in row] for row in q])
        out[name] = int(edge.sum())
    return out


def post_build(ctx):
    rep = {"head": dict(HEAD_STATS)}
    rep["face_edge_bleed_texels"] = bleed_face_edges(ctx["spec"]["id"])
    return rep

