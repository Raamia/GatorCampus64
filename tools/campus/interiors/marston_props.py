"""Marston Science Library (Course 4): the photo-reference furniture and fixtures, built with the interior kit
(tools/campus/interior_kit.py). Pure Python; every builder returns a kit Prop in LOCAL coordinates (origin on the
floor under the piece, its front facing local +y; place with Prop.merge / Kit.add and a compass facing).

Each piece is modelled on the reference photos (reference/interiors/marston/index.json "n" numbers in brackets,
contact sheets in art/levels/marston/reference_sheets/), in the N64 style of the kit: few polygons, small tiling
textures (the int_ms_* materials of stage_palette.INTERIOR_MATERIALS) and the colour in the vertex shade (tints).
Collision is a few closed boxes per piece ('COL nocam': the camera passes through furniture), and only where Mario
should bump into something.

    tools/.venv/bin/python -I tools/campus/interiors/marston_props.py     (builds every piece, prints tri counts)
"""
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CAMPUS_TOOLS = os.path.dirname(HERE)
if CAMPUS_TOOLS not in sys.path:
    sys.path.insert(0, CAMPUS_TOOLS)

import interior_kit as K  # noqa: E402

NOCAM = K.COL_NOCAM

# ------------------------------------------------------------------ colours (vertex tints; textures are pale)
# sampled from the photos (99_materials_palette.png / materials_palette.json), lifted for the vertex shade
T_ORANGE_LEATHER = (0.80, 0.46, 0.18)     # F2 banquette seats, lounge chairs [#24 #25]
T_YELLOW_OTTOMAN = (0.95, 0.80, 0.24)     # F2 round ottomans [#24]
T_SALMON = (0.86, 0.58, 0.52)             # F1 hexagon ottomans, banquette seats [#38 #39 #69]
T_SAND = (0.94, 0.80, 0.58)               # F1 hexagon ottomans [#69]
T_OLIVE_BASE = (0.55, 0.55, 0.40)         # F1 banquette bases [#38]
T_BLUE_CUSHION = (0.36, 0.45, 0.50)       # F5 lounge-cube cushions [#100] (fix round 2 fidelity-4: dusty slate blue-grey;
                                          # the photos measure 64-74 / 82-90 / 86-94, 0.22/0.55/0.68 read saturated teal)
T_PLUM = (0.42, 0.31, 0.37)               # L308 chairs [#78] (fix round 2 fidelity-4: muted plum-grey, photo 92/68/78;
                                          # 0.46/0.26/0.36 read raspberry)
T_TAUPE = (0.62, 0.58, 0.54)              # F1 study-room shell chairs [#44]
T_GREY_STEEL = (0.74, 0.76, 0.80)         # grey steel shelving / frames (on int_metal / int_drywall)
T_LIGHT_STEEL = (0.92, 0.94, 0.96)
T_STEEL_BLUE = (0.60, 0.70, 0.82)         # F4 stack end panels [#84-#86]
T_CORAL = (0.82, 0.46, 0.40)              # F3 stack end panels [#83 #91]
T_TERRACOTTA = (0.70, 0.42, 0.34)         # F3-F5 column caps [#76 #100]
T_TEAL_WALL = (0.40, 0.66, 0.84)          # F2 accent walls [#24 #29]
T_TEAL_ROOM = (0.38, 0.50, 0.60)          # F1 study-room accent walls [#44 (80, 105, 124) at 0.89 of the white wall]
T_YELLOW_WALL = (1.00, 0.76, 0.12)        # F2 accent walls [#24 #25 #29]
T_PURPLE_WALL = (0.50, 0.38, 0.72)        # F1 accent walls [#36]
T_OLIVE_WALL = (0.70, 0.70, 0.46)         # F1 computer labs [#61 #63 #64]
T_GREY_WALL = (0.46, 0.48, 0.50)          # dark grey window walls F3-F5 [#76 #100]
T_LAMINATE_GREY = (0.84, 0.86, 0.88)      # service desk base [#23]
T_SOLID_SURFACE = (0.44, 0.46, 0.48)      # service desk top [#23]
T_BLACK = (0.30, 0.30, 0.32)
# fidelity-2 fix 2 (#61 #63): the computer labs' Sayls are light grey mesh on a light grey frame (lab-only; the
# Commons keeps the design review's mid-grey)
LAB_CHAIR = dict(mesh_tint=(0.90, 0.91, 0.94), frame_tint=(0.70, 0.71, 0.74), seat_tint=(0.86, 0.87, 0.90))


def _ngon(cx, cy, r, n, rot=0.0):
    return [(cx + r * math.cos(rot + 2 * math.pi * k / n), cy + r * math.sin(rot + 2 * math.pi * k / n)) for k in range(n)]


def prism(V, pts, z0, z1, mat, top=True, bottom=False, tint=None, glow=False, top_mat=None, ao=None):
    """Vertical prism over a CCW footprint (outward side walls, optional caps)."""
    pts = list(pts)
    if K._signed_area(pts) < 0:
        pts.reverse()
    kw = {"tint": tint, "glow": glow}
    if ao is not None:
        kw["ao"] = ao
    for a, b in zip(pts, pts[1:] + pts[:1]):
        V.wall(a, b, z0, z1, mat, **kw)
    if top:
        V.poly([(x, y, z1) for x, y in pts], top_mat or mat, **kw)
    if bottom:
        V.poly([(x, y, z0) for x, y in reversed(pts)], mat, **kw)


def col_prism(C, pts, z0, z1, bottom=False):
    pts = list(pts)
    if K._signed_area(pts) < 0:
        pts.reverse()
    K.col_prism(C, pts, z0, z1, NOCAM, bottom=bottom)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def arc(cx, cy, r, a0, a1, n):
    return [(cx + r * math.cos(a0 + (a1 - a0) * k / n), cy + r * math.sin(a0 + (a1 - a0) * k / n)) for k in range(n + 1)]


# ================================================================== seating
# iteration 4 (fidelity-4, #75 #76 #96 #99): the F3-F5 Sayls are near-black charcoal in the photos; the default mid
# grey (mesh 0.92) made them the lightest objects on those floors. marston.build_floor sets this per floor
# ({"mesh", "frame", "seat"} default tints, or None for the defaults below) while it builds F3-F5
SAYL_FLOOR = None


def sayl_chair(mesh_tint=None, frame_tint=None, seat_tint=None):
    """Grey task chair with a Y-shaped back (Herman Miller Sayl: nearly every task chair in the photos, #27 #28 #36
    #61 #76 #97): black five-star base and post, a charcoal seat, a light grey lattice back leaning back with the
    grey Y spine (stem from the seat, arms to the top corners) in front of and behind it. ~36 tris, visual only.
    The sitter faces +y (the back is at -y).
    fidelity-2 fix 2: frame_tint / seat_tint (optional) recolour the Y spine and the seat (the labs' light grey chairs,
    #61 #63); the defaults keep the Commons / F2 / F5 chairs as they were."""
    P = K.Prop("sayl_chair", col_closed=True)
    V = P.visual
    blk = T_BLACK
    fd = SAYL_FLOOR or {}
    V.poly([(-0.30, -0.035, 0.06), (0.30, -0.035, 0.06), (0.30, 0.035, 0.06), (-0.30, -0.035 + 0.07, 0.06)],
           "int_plastic", tint=blk)
    V.poly([(-0.035, -0.30, 0.06), (0.035, -0.30, 0.06), (0.035, 0.30, 0.06), (-0.035, 0.30, 0.06)], "int_plastic",
           tint=blk)
    V.box(-0.03, -0.03, 0.06, 0.03, 0.03, 0.40, "int_metal", faces="+x-x+y-y", tint=(0.42, 0.42, 0.44))
    V.box(-0.24, -0.22, 0.40, 0.24, 0.24, 0.47, "int_ms_felt", faces="+x-x+y-y+z",
          tint=seat_tint or fd.get("seat") or (0.78, 0.79, 0.82))
    # back: a tapered lattice panel leaning back (both faces)
    b0, b1 = (-0.21, -0.22, 0.52), (0.21, -0.22, 0.52)
    t0, t1 = (-0.25, -0.31, 1.02), (0.25, -0.31, 1.02)
    # design fix round 1: charcoal mesh (#36 #100); the light grey backs with the Y were the loudest graphic on F1/F2/F5
    # fix round 2 fidelity-1 (4243 commons_tables: chair p50 lum 31-67 render vs 62-111 photo): two steps lighter, a
    # mid grey (still well under the light grey 0.85 backs that design round 1 found loud)
    # design fix round 2 (p_f4_carrels, the gameplay camera; #97 mid-grey mesh): with the vertex shade the 0.66 mesh
    # still read near-black (texel mean 0.57 x 0.66 = 0.38 before lighting): now ~0.53 grey, the Y spine 0.1 darker
    tint = mesh_tint or fd.get("mesh") or (0.92, 0.92, 0.96)
    V.poly([b0, b1, t1, t0], "int_ms_mesh", tint=tint, normal_hint=(0, 1, 0))
    V.poly([t0, t1, b1, b0], "int_ms_mesh", tint=(tint[0] * 0.8, tint[1] * 0.8, tint[2] * 0.8), normal_hint=(0, -1, 0))

    def lerp(p, q, t):
        return tuple(p[i] + (q[i] - p[i]) * t for i in range(3))
    mid_b, mid_t = lerp(b0, b1, 0.5), lerp(t0, t1, 0.5)
    fork = lerp(mid_b, mid_t, 0.55)
    w = 0.028
    for off, nh in ((0.012, (0, 1, 0)), (-0.012, (0, -1, 0))):
        def o(p):
            return (p[0], p[1] + off, p[2])
        segs = [(lerp(mid_b, mid_t, -0.08), fork), (fork, lerp(t0, t1, 0.04)), (fork, lerp(t0, t1, 0.96))]
        for (p, q) in segs:
            dx, dz = q[0] - p[0], q[2] - p[2]
            L = math.hypot(dx, dz) or 1.0
            nx, nz = -dz / L * w, dx / L * w
            quad = [o((p[0] - nx, p[1], p[2] - nz)), o((p[0] + nx, p[1], p[2] + nz)),
                    o((q[0] + nx, q[1], q[2] + nz)), o((q[0] - nx, q[1], q[2] - nz))]
            # fidelity-1 (#37 4243): the Y spine is the chair's grey frame plastic, not black; black read as a stick
            # figure from the game camera, where the photos show uniformly grey chairs
            # design fix round 1: a dark grey Y, barely lighter than the charcoal mesh (as in #36 #100)
            # fix round 2 fidelity-1: lifted with the mesh (0.30 -> 0.38), a slightly darker grey frame on it
            V.poly(quad, "int_metal", tint=frame_tint or fd.get("frame") or (0.64, 0.64, 0.67), normal_hint=nh)
    return P


def _legs(V, pts, z0, z1, w=0.022, tint=(0.80, 0.80, 0.84)):
    """Thin chrome legs (two crossed double-sided strips each: reads round from every side)."""
    for (x, y) in pts:
        for (a, b) in (((x - w, y), (x + w, y)), ((x, y - w), (x, y + w))):
            V.wall(a, b, z0, z1, "int_metal", tint=tint)
            V.wall(b, a, z0, z1, "int_metal", tint=tint)


def caper_stool(h=0.76, tint=T_BLACK):
    """Black counter stool (Herman Miller Caper, #41 #45 #76): a perforated black shell seat and a low back on four
    splayed chrome legs with a foot ring. Visual only."""
    P = K.Prop("caper_stool", col_closed=True)
    V = P.visual
    V.box(-0.21, -0.20, h - 0.05, 0.21, 0.21, h, "int_plastic", faces="+x-x+y-y+z", tint=tint)
    back = [(-0.20, -0.20, h + 0.08), (0.20, -0.20, h + 0.08), (0.21, -0.25, h + 0.40), (-0.21, -0.25, h + 0.40)]
    V.poly(back, "int_ms_perf", tint=(0.30, 0.30, 0.32), normal_hint=(0, 1, 0))
    V.poly(list(reversed(back)), "int_ms_perf", tint=(0.24, 0.24, 0.26), normal_hint=(0, -1, 0))
    V.box(-0.02, -0.21, h, 0.02, -0.18, h + 0.10, "int_plastic", faces="+x-x+y-y", tint=tint)
    _legs(V, [(-0.19, -0.18), (0.19, -0.18), (0.19, 0.18), (-0.19, 0.18)], 0.0, h - 0.05)
    ring = [(-0.18, -0.17), (0.18, -0.17), (0.18, 0.17), (-0.18, 0.17)]
    for a_, b_ in zip(ring, ring[1:] + ring[:1]):
        V.wall(a_, b_, 0.28, 0.30, "int_metal", tint=(0.80, 0.80, 0.84))
        V.wall(b_, a_, 0.28, 0.30, "int_metal", tint=(0.80, 0.80, 0.84))
    return P


def guest_chair(fabric_tint=T_PLUM, h=0.46):
    """Stacking / nesting chair (L308 plum chairs on casters #78, L136 black Caper chairs #47 #49): an upholstered or
    plastic seat, a curved back, four chrome legs. Visual only."""
    P = K.Prop("guest_chair", col_closed=True)
    V = P.visual
    V.box(-0.23, -0.21, h - 0.05, 0.23, 0.23, h, "int_ms_leather", faces="+x-x+y-y+z", tint=fabric_tint)
    back = [(-0.22, -0.21, h + 0.12), (0.22, -0.21, h + 0.12), (0.23, -0.27, h + 0.46), (-0.23, -0.27, h + 0.46)]
    V.poly(back, "int_ms_leather", tint=fabric_tint, normal_hint=(0, 1, 0))
    dk = (fabric_tint[0] * 0.75, fabric_tint[1] * 0.75, fabric_tint[2] * 0.75)
    V.poly(list(reversed(back)), "int_ms_leather", tint=dk, normal_hint=(0, -1, 0))
    for sx in (-1, 1):
        V.wall((sx * 0.215, -0.21), (sx * 0.22, -0.26), h - 0.05, h + 0.30, "int_metal", tint=(0.8, 0.8, 0.84))
        V.wall((sx * 0.22, -0.26), (sx * 0.215, -0.21), h - 0.05, h + 0.30, "int_metal", tint=(0.8, 0.8, 0.84))
    _legs(V, [(-0.20, -0.18), (0.20, -0.18), (0.20, 0.20), (-0.20, 0.20)], 0.0, h - 0.05)
    return P


def tub_chair(tint=T_ORANGE_LEATHER, col=True):
    """Leather tub lounge chair (F2 lounge #24 #26; taupe shell chairs in the F1 study rooms #44): a low seat inside
    a wrap-around back and arms, on short metal feet. Collision: one block."""
    P = K.Prop("tub_chair", col_closed=True)
    V = P.visual
    dark = (tint[0] * 0.82, tint[1] * 0.82, tint[2] * 0.82)
    V.box(-0.38, -0.36, 0.08, 0.38, 0.36, 0.40, "int_ms_leather", faces="+x-x+y-y", tint=dark)
    V.box(-0.30, -0.24, 0.40, 0.30, 0.34, 0.46, "int_ms_leather", faces="+y+z", tint=tint)
    V.box(-0.42, -0.40, 0.40, 0.42, -0.24, 0.84, "int_ms_leather", faces="+x-x+y-y+z", tint=tint)
    for sx in (-1, 1):
        x0, x1 = (0.30, 0.42) if sx > 0 else (-0.42, -0.30)
        V.box(x0, -0.24, 0.40, x1, 0.34, 0.66, "int_ms_leather", faces="+x-x+y+z", tint=tint)
    for sx in (-1, 1):
        for sy in (-1, 1):
            V.box(sx * 0.30 - 0.02, sy * 0.28 - 0.02, 0.0, sx * 0.30 + 0.02, sy * 0.28 + 0.02, 0.08, "int_metal",
                  faces="+x-x+y-y")
    if col:
        K.col_box(P.collision, -0.42, -0.40, 0.0, 0.42, 0.36, 0.66, NOCAM)
    return P


def _splay_legs(V, feet, tops, w=0.016, tint=(0.80, 0.80, 0.84)):
    """Thin splayed steel legs: each a pair of crossed double-sided strips from a foot (x, y) on the floor to a top
    (x, y, z) under the seat."""
    for (fx, fy), (tx, ty, tz) in zip(feet, tops):
        for (ox, oy) in ((w, 0.0), (0.0, w)):
            q = [(fx - ox, fy - oy, 0.0), (fx + ox, fy + oy, 0.0), (tx + ox, ty + oy, tz), (tx - ox, ty - oy, tz)]
            V.poly(q, "int_metal", tint=tint)
            V.poly(list(reversed(q)), "int_metal", tint=tint)


def shell_chair(tint=T_TAUPE, col=True, col_box=(-0.34, -0.36, 0.0, 0.34, 0.32, 0.46)):
    """fidelity-1: the taupe metallic-leather shell lounge chair of the F1 study rooms (#44 #46): a one-piece shell
    (seat, raked back and low wings) on four thin splayed steel legs. Faces +y. Collision: one low block."""
    P = K.Prop("shell_chair", col_closed=True)
    V = P.visual
    out = (tint[0] * 0.92, tint[1] * 0.90, tint[2] * 0.88)
    dk = (tint[0] * 0.62, tint[1] * 0.62, tint[2] * 0.62)
    lt = (min(1.0, tint[0] * 1.12), min(1.0, tint[1] * 1.12), min(1.0, tint[2] * 1.12))
    # fix round 2 fidelity-1 (#44 vs room_L125 / room_L123): a BULKY padded tub shell, not thin planes (they read as
    # folded deck chairs): a 0.13 m seat cushion, and a 9 cm thick upholstered shell wrapped round it from wing tip to
    # wing tip, its top falling from 0.90 m at the back to 0.54 m at the wing ends and raked outward (~90 tris)
    zs, zb = 0.44, 0.31                                    # seat top / cushion bottom
    seat = [(-0.30, -0.20), (0.30, -0.20), (0.31, 0.17), (0.25, 0.31), (-0.25, 0.31), (-0.31, 0.17)]
    prism(V, seat, zb, zs, "int_ms_leather", tint=tint, top_mat="int_ms_leather")
    V.poly([(x, y, zb) for x, y in seat], "int_metal", tint=dk, normal_hint=(0, 0, -1))
    # the top of the cushion a shade lighter (it catches the ceiling light in #44)
    # iteration 4 (technical): 1.5 cm proud (the old 4 mm rounded onto the seat top in game units: z-fight)
    V.poly([(x * 0.86, y * 0.86 + 0.02, zs + 0.015) for x, y in seat], "int_ms_leather", tint=lt,
           normal_hint=(0, 0, 1))
    ox_, oy_, rx, ry, t = 0.0, -0.02, 0.40, 0.34, 0.09
    n = 8
    a0, a1 = math.radians(160.0), math.radians(380.0)
    ring = []
    for k in range(n + 1):
        a = a0 + (a1 - a0) * k / n
        c, s = math.cos(a), math.sin(a)
        f = (-s + 0.342) / 1.342                           # 0 at the wing tips, 1 at the middle of the back
        h = zs + 0.10 + 0.36 * f
        lean = 0.10 * f + 0.02
        ux, uy = c, s                                      # outward (radial) direction
        ob = (ox_ + rx * c, oy_ + ry * s, zb - 0.02)
        ot = (ox_ + (rx + lean) * c, oy_ + (ry + lean) * s, h)
        ib = (ox_ + (rx - t) * c, oy_ + (ry - t) * s, zs - 0.02)
        it = (ox_ + (rx - t + lean) * c, oy_ + (ry - t + lean) * s, h - 0.015)
        ring.append((ob, ot, ib, it, (ux, uy)))
    for k in range(n):
        (ob0, ot0, ib0, it0, u0), (ob1, ot1, ib1, it1, u1) = ring[k], ring[k + 1]
        um = ((u0[0] + u1[0]) / 2, (u0[1] + u1[1]) / 2)
        V.poly([ob0, ob1, ot1, ot0], "int_ms_leather", tint=out, normal_hint=(um[0], um[1], 0.0))
        V.poly([ib0, ib1, it1, it0], "int_ms_leather", tint=tint, normal_hint=(-um[0], -um[1], 0.0))
        V.poly([ot0, ot1, it1, it0], "int_ms_leather", tint=lt, normal_hint=(0, 0, 1))
    for j, sgn in ((0, -1.0), (n, 1.0)):                   # the rounded wing fronts
        ob, ot, ib, it, u = ring[j]
        tx, ty = -u[1] * sgn, u[0] * sgn                   # tangent pointing off the end of the arc
        V.poly([ob, ib, it, ot], "int_ms_leather", tint=tint, normal_hint=(tx, ty, 0.0))
    _splay_legs(V, [(-0.32, -0.30), (0.32, -0.30), (0.30, 0.30), (-0.30, 0.30)],
                [(-0.20, -0.14, zb), (0.20, -0.14, zb), (0.19, 0.18, zb), (-0.19, 0.18, zb)])
    if col:
        K.col_box(P.collision, *col_box, NOCAM)
    return P


def coffee_disc(d=0.90, h=0.46, top="int_ms_maple", base_tint=T_LIGHT_STEEL, col=True):
    """fix round 2 fidelity-1 (#44 #46): the study rooms' low round coffee table: a thick maple disc (16 sides, a
    4 cm edge) on a short brushed-steel column and a round low foot plate. Collision: the disc's octagon prism."""
    P = K.Prop("coffee_disc", col_closed=True)
    V = P.visual
    r = d / 2
    disc = _ngon(0, 0, r, 16, math.pi / 16)
    prism(V, disc, h - 0.04, h, top)
    V.poly([(x, y, h - 0.04) for x, y in reversed(disc)], top, tint=(0.66, 0.66, 0.66))
    prism(V, _ngon(0, 0, 0.055, 8, math.pi / 8), 0.035, h - 0.04, "int_metal", top=False, tint=base_tint)
    prism(V, _ngon(0, 0, 0.26, 12, math.pi / 12), 0.005, 0.035, "int_metal", tint=base_tint)
    if col:
        col_prism(P.collision, _ngon(0, 0, r, 8, math.pi / 8), 0.0, h)
    P.anchor("top", 0.0, 0.0, h)
    return P


def recycle_bin(label=(0.24, 0.46, 0.80), w=0.46, d=0.40, h=0.98, col=True):
    """fix round 2 fidelity-1 (#69 4317, #39 4356): a brushed stainless recycling / waste receptacle beside the
    elevator-lobby stanchions: a tall box with a dark round-cornered opening in its slanted front head and a coloured
    stream label. Faces +y. Collision: one box."""
    P = K.Prop("recycle_bin", col_closed=True)
    V = P.visual
    st = (1.02, 1.03, 1.06)
    V.box(-w / 2, -d / 2, 0.0, w / 2, d / 2, h - 0.12, "int_metal", faces="+x-x+y-y", tint=st)
    # the head: the front leans back 6 cm, the top is flat
    yf, yb, z0 = d / 2, -d / 2, h - 0.12
    V.poly([(-w / 2, yf, z0), (w / 2, yf, z0), (w / 2, yf - 0.06, h), (-w / 2, yf - 0.06, h)], "int_metal", tint=st,
           normal_hint=(0, 1, 0.4))
    V.poly([(-w / 2, yb, h), (w / 2, yb, h), (w / 2, yf - 0.06, h), (-w / 2, yf - 0.06, h)], "int_metal",
           tint=(0.92, 0.93, 0.96), normal_hint=(0, 0, 1))
    for sx in (-1, 1):
        V.poly([(sx * w / 2, yb, z0), (sx * w / 2, yf, z0), (sx * w / 2, yf - 0.06, h), (sx * w / 2, yb, h)],
               "int_metal", tint=st, normal_hint=(sx, 0, 0))
    V.poly([(w / 2, yb, z0), (-w / 2, yb, z0), (-w / 2, yb, h), (w / 2, yb, h)], "int_metal", tint=st,
           normal_hint=(0, -1, 0))
    # the opening (dark) on the slanted head and the label strip under it
    V.poly([(-0.15, yf - 0.012 + 0.008, z0 + 0.025), (0.15, yf - 0.012 + 0.008, z0 + 0.025),
            (0.15, yf - 0.046 + 0.008, z0 + 0.095), (-0.15, yf - 0.046 + 0.008, z0 + 0.095)], "int_plastic",
           tint=(0.10, 0.10, 0.11), normal_hint=(0, 1, 0.4))
    V.poly(K.front_quad(-0.13, 0.13, yf + 0.006, z0 - 0.16, z0 - 0.06), "int_drywall", tint=label, ao=1.0)
    if col:
        K.col_box(P.collision, -w / 2, -d / 2, 0.0, w / 2, d / 2, h, NOCAM)
    return P


def slim_table(d=0.50, h=0.58, top="int_ms_maple"):
    """fidelity-1: a slim round maple side table on three thin splayed steel legs (#44). Visual only."""
    P = K.Prop("slim_table", col_closed=True)
    V = P.visual
    r = d / 2
    prism(V, _ngon(0, 0, r, 10), h - 0.03, h, top)
    V.poly([(x, y, h - 0.03) for x, y in reversed(_ngon(0, 0, r, 10))], top, tint=(0.7, 0.7, 0.7))
    feet = [(math.cos(a) * (r + 0.02), math.sin(a) * (r + 0.02)) for a in (0.3, 0.3 + 2.094, 0.3 + 4.189)]
    tops = [(math.cos(a) * r * 0.45, math.sin(a) * r * 0.45, h - 0.03) for a in (0.3, 0.3 + 2.094, 0.3 + 4.189)]
    _splay_legs(V, feet, tops, w=0.012)
    return P


def round_ottoman(r=0.42, h=0.42, tint=T_YELLOW_OTTOMAN, col=True):
    """Round upholstered ottoman on casters (the yellow ones in the F2 lounge, #24 #25): octagonal drum."""
    P = K.Prop("round_ottoman", col_closed=True)
    V = P.visual
    prism(V, _ngon(0, 0, r, 8, math.pi / 8), 0.05, h, "int_ms_leather", tint=tint)
    if col:
        col_prism(P.collision, _ngon(0, 0, r, 8, math.pi / 8), 0.0, h)
    return P


def hex_ottoman(r=0.55, h=0.45, tint=T_SALMON, col=True):
    """Hexagonal faux-leather ottoman on grey legs (F1 elevator lobby and MADE@UF front, #39 #69)."""
    P = K.Prop("hex_ottoman", col_closed=True)
    V = P.visual
    pts = _ngon(0, 0, r, 6, 0.0)
    prism(V, pts, h - 0.16, h, "int_ms_leather", tint=tint)
    for (x, y) in _ngon(0, 0, r * 0.78, 3, 0.3):
        V.box(x - 0.025, y - 0.025, 0.0, x + 0.025, y + 0.025, h - 0.16, "int_metal", faces="+x-x+y-y",
              tint=(0.62, 0.62, 0.64))
    if col:
        col_prism(P.collision, pts, 0.0, h)
    return P


def banquette_arc(r_in=1.15, depth=0.62, a0=200.0, a1=340.0, seat_tint=T_ORANGE_LEATHER, back_mat="int_ms_fab_dark",
                  back_tint=None, base_tint=None, seat_h=0.44, back_h=1.02, n=None, col=True):
    """Curved modular banquette (F2 lounge: orange-tan leather seats, charcoal patterned backs [#24 #25]; F1: salmon
    seats, olive base, multicolour backs [#38]). Local origin = the circle's centre; the seats face it. Angles in
    degrees, counter-clockwise from local +x. Collision: one block per segment (seat height) + the back."""
    P = K.Prop("banquette", col_closed=True)
    V, C = P.visual, P.collision
    n = n or max(2, int(round((a1 - a0) / 22.0)))
    A0, A1 = math.radians(a0), math.radians(a1)
    r_seat = r_in + depth - 0.14
    r_out = r_in + depth
    inner = arc(0, 0, r_in, A0, A1, n)
    mid = arc(0, 0, r_seat, A0, A1, n)
    outer = arc(0, 0, r_out, A0, A1, n)
    base_t = base_tint or (seat_tint[0] * 0.72, seat_tint[1] * 0.72, seat_tint[2] * 0.72)
    bt = back_tint or (1.0, 1.0, 1.0)
    for k in range(n):
        a, b = inner[k], inner[k + 1]
        ma, mb = mid[k], mid[k + 1]
        oa, ob = outer[k], outer[k + 1]
        # seat cushion: top + front; base below the cushion
        V.poly([(a[0], a[1], seat_h), (b[0], b[1], seat_h), (mb[0], mb[1], seat_h), (ma[0], ma[1], seat_h)],
               "int_ms_leather", tint=seat_tint, normal_hint=(0, 0, 1))
        V.poly([(b[0], b[1], 0.30), (a[0], a[1], 0.30), (a[0], a[1], seat_h), (b[0], b[1], seat_h)], "int_ms_leather",
               tint=seat_tint, normal_hint=(-(a[0] + b[0]), -(a[1] + b[1]), 0))
        V.poly([(b[0] * 1.03, b[1] * 1.03, 0.06), (a[0] * 1.03, a[1] * 1.03, 0.06), (a[0] * 1.03, a[1] * 1.03, 0.30),
                (b[0] * 1.03, b[1] * 1.03, 0.30)], "int_ms_leather", tint=base_t,
               normal_hint=(-(a[0] + b[0]), -(a[1] + b[1]), 0))
        # back: inner face, top, outer face
        V.poly([(mb[0], mb[1], seat_h), (ma[0], ma[1], seat_h), (ma[0], ma[1], back_h), (mb[0], mb[1], back_h)],
               back_mat, tint=bt, normal_hint=(-(ma[0] + mb[0]), -(ma[1] + mb[1]), 0))
        V.poly([(ma[0], ma[1], back_h), (oa[0], oa[1], back_h), (ob[0], ob[1], back_h), (mb[0], mb[1], back_h)],
               back_mat, tint=bt, normal_hint=(0, 0, 1))
        V.poly([(oa[0], oa[1], 0.06), (ob[0], ob[1], 0.06), (ob[0], ob[1], back_h), (oa[0], oa[1], back_h)], back_mat,
               tint=(bt[0] * 0.9, bt[1] * 0.9, bt[2] * 0.9), normal_hint=(oa[0] + ob[0], oa[1] + ob[1], 0))
        if col:
            col_prism(C, [a, b, mb, ma], 0.0, seat_h)
            col_prism(C, [ma, mb, ob, oa], 0.0, back_h)
    for end, (ia, oa) in (("a", (inner[0], outer[0])), ("b", (inner[-1], outer[-1]))):
        d = (oa[0] - ia[0], oa[1] - ia[1])
        p, q = (ia, oa) if end == "b" else (oa, ia)
        V.wall(p, q, 0.06, seat_h, "int_ms_leather", tint=base_t)
        mp = (ia[0] + d[0] * 0.77, ia[1] + d[1] * 0.77)
        V.wall(mp if end == "b" else oa, oa if end == "b" else mp, seat_h, back_h, back_mat, tint=bt)
    return P


def lounge_cube(fabric_tint=None, cushion_tint=T_BLUE_CUSHION, col=True):
    """Floor-5 lounge cube (2022, #100-#102): a square armchair in light grey geometric fabric with a blue seat
    cushion, on short grey legs. 0.8 x 0.8 m, seat 0.45 m, arms / back 0.75 m."""
    P = K.Prop("lounge_cube", col_closed=True)
    V = P.visual
    ft = fabric_tint or (1.0, 1.0, 1.0)
    V.box(-0.40, -0.40, 0.10, 0.40, 0.40, 0.36, "int_ms_fab_geo", faces="+x-x+y-y", tint=ft)
    V.box(-0.40, -0.40, 0.36, 0.40, -0.24, 0.76, "int_ms_fab_geo", faces="+x-x+y-y+z", tint=ft)
    for sx in (-1, 1):
        x0, x1 = (0.26, 0.40) if sx > 0 else (-0.40, -0.26)
        V.box(x0, -0.24, 0.36, x1, 0.40, 0.70, "int_ms_fab_geo", faces="+x-x+y+z", tint=ft)
    V.box(-0.26, -0.24, 0.36, 0.26, 0.40, 0.46, "int_ms_leather", faces="+y+z", tint=cushion_tint)
    for sx in (-1, 1):
        for sy in (-1, 1):
            V.box(sx * 0.36 - 0.025, sy * 0.36 - 0.025, 0.0, sx * 0.36 + 0.025, sy * 0.36 + 0.025, 0.10, "int_metal",
                  faces="+x-x+y-y", tint=(0.7, 0.7, 0.72))
    if col:
        K.col_box(P.collision, -0.40, -0.40, 0.0, 0.40, 0.40, 0.70, NOCAM)
    return P


def side_table_block(w=0.55, h=0.42, col=True):
    """Maple bench / side table on grey legs between the floor-5 lounge cubes (#100)."""
    P = K.Prop("side_block", col_closed=True)
    V = P.visual
    V.box(-w / 2, -w / 2, h - 0.08, w / 2, w / 2, h, "int_ms_maple", faces="+x-x+y-y+z")
    for sx in (-1, 1):
        for sy in (-1, 1):
            V.box(sx * (w / 2 - 0.05) - 0.02, sy * (w / 2 - 0.05) - 0.02, 0.0, sx * (w / 2 - 0.05) + 0.02,
                  sy * (w / 2 - 0.05) + 0.02, h - 0.08, "int_metal", faces="+x-x+y-y", tint=(0.7, 0.7, 0.72))
    if col:
        K.col_box(P.collision, -w / 2, -w / 2, 0.0, w / 2, w / 2, h, NOCAM)
    return P


def study_pod(w=1.5, d=1.2, h=1.40, col=True):
    """Dark grey felt high-back study pod (floor 5, 2022, #100): a U of tall panels round a maple desk that opens
    to local +y, with a chair."""
    P = K.Prop("study_pod", col_closed=True)
    V = P.visual
    t = 0.06
    V.box(-w / 2, -d / 2, 0.0, w / 2, -d / 2 + t, h, "int_ms_felt", faces="+x-x+y-y+z")
    for sx in (-1, 1):
        x0, x1 = (w / 2 - t, w / 2) if sx > 0 else (-w / 2, -w / 2 + t)
        V.box(x0, -d / 2 + t, 0.0, x1, d / 2, h, "int_ms_felt", faces="+x-x+y+z")
    V.box(-w / 2 + t, -d / 2 + t, 0.72, w / 2 - t, -d / 2 + 0.66, 0.76, "int_ms_maple", faces="+y+z-z")
    P.merge(sayl_chair(), 0.0, 0.05, 0.0, 180.0)
    if col:
        c = P.collision
        K.col_box(c, -w / 2, -d / 2, 0.0, w / 2, -d / 2 + 0.2, h, NOCAM)
        K.col_box(c, -w / 2, -d / 2 + 0.2, 0.0, -w / 2 + 0.2, d / 2, h, NOCAM)
        K.col_box(c, w / 2 - 0.2, -d / 2 + 0.2, 0.0, w / 2, d / 2, h, NOCAM)
    return P


def commons_pod(arm=1.25, h=1.35, col=True):
    """The 2014 commons study pod (#36): grey fabric panels with rounded tops in a cross on brushed aluminium posts
    (foot discs), a curved white desk in each of the four bays, a Sayl chair at each. Collision: the cross (thin
    panels thickened) + the four desks."""
    P = K.Prop("commons_pod", col_closed=True)
    V, C = P.visual, P.collision
    t = 0.05
    for (dx, dy) in ((1, 0), (0, 1), (-1, 0), (0, -1)):
        x0, x1 = sorted((0.0, dx * arm)) if dx else (-t, t)
        y0, y1 = sorted((0.0, dy * arm)) if dy else (-t, t)
        # iteration 4 (fidelity-1, #36 4212): the photo's pod panels are a light blue-grey (RGB ~116 / 120 / 147); the
        # (1.25, 1.27, 1.32) felt rendered a neutral 87-109 / 93-114 / 99-119
        V.box(x0, y0, 0.22, x1, y1, h - 0.08, "int_ms_felt", faces="+x-x+y-y+z", tint=(1.35, 1.38, 1.60))
        ex, ey = dx * arm, dy * arm
        # fidelity-1: posts 5 cm square (were 8 cm: their faces sat 1 cm off the 10 cm felt panel's, z-fighting)
        V.box(ex - 0.025, ey - 0.025, 0.0, ex + 0.025, ey + 0.025, h, "int_metal", faces="+x-x+y-y+z")
        V.poly([(ex + 0.16 * math.cos(a), ey + 0.16 * math.sin(a), 0.01) for a in
                [2 * math.pi * k / 6 for k in range(6)]], "int_metal")
    V.box(-0.035, -0.035, 0.0, 0.035, 0.035, h, "int_metal", faces="+x-x+y-y+z")
    for qx, qy in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
        # quarter-round white desk in the bay
        pts = [(qx * 0.06, qy * 0.06)] + [(qx * (0.06 + 0.95 * math.cos(a)), qy * (0.06 + 0.95 * math.sin(a)))
                                          for a in [math.pi / 2 * k / 4 for k in range(5)]]
        prism(V, pts, 0.71, 0.74, "int_drywall", tint=(0.95, 0.95, 0.96))
        V.box(qx * 0.75 - 0.02, qy * 0.75 - 0.02, 0.0, qx * 0.75 + 0.02, qy * 0.75 + 0.02, 0.71, "int_metal",
              faces="+x-x+y-y")
        P.merge(sayl_chair(), qx * 1.05, qy * 1.05, 0.0, math.degrees(math.atan2(-qx, -qy)) % 360.0)
        if col:
            col_prism(C, pts, 0.0, 0.74)
    if col:
        # the cross: one E-W block and two N-S blocks reaching 0.06 m into it (no coincident opposite faces: a
        # zero-thickness pair is a 'thin wall' an airborne player is thrown through)
        K.col_box(C, -arm, -0.12, 0.0, arm, 0.12, h, NOCAM)
        K.col_box(C, -0.12, -arm, 0.0, 0.12, 0.06, h, NOCAM)
        K.col_box(C, -0.12, -0.06, 0.0, 0.12, arm, h, NOCAM)
    return P


# ================================================================== tables
def cafe_chair(wood=(0.62, 0.44, 0.30), frame=(0.20, 0.20, 0.22)):
    """Design fix round 1: a cafe side chair for the Starbucks seating (it had Sayl task chairs): four thin black
    steel legs, a stained wood seat and a wood back with an open slot. ~34 tris, visual only. Sitter faces +y."""
    P = K.Prop("cafe_chair", col_closed=True)
    V = P.visual
    V.box(-0.21, -0.20, 0.42, 0.21, 0.21, 0.46, "int_ms_veneer", faces="+x-x+y-y+z", tint=wood)
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * 0.18, sy * 0.17
            V.box(x - 0.015, y - 0.015, 0.0, x + 0.015, y + 0.015, 0.42, "int_metal", faces="+x-x+y-y", tint=frame)
        # rear posts up to the back
        V.box(sx * 0.18 - 0.015, -0.19, 0.46, sx * 0.18 + 0.015, -0.16, 0.86, "int_metal", faces="+x-x+y-y", tint=frame)
    for z0, z1 in ((0.58, 0.64), (0.72, 0.86)):                 # two back rails (open slot between them)
        V.box(-0.20, -0.20, z0, 0.20, -0.17, z1, "int_ms_veneer", faces="+x-x+y-y+z", tint=wood)
    return P


def round_table(d=1.07, h=0.76, top="int_ms_maple", base_tint=T_BLACK, chairs=4, stools=False, col=True, rot=0.0,
                chair=None):
    """Round maple table on a pedestal (F1 commons #36-#41, F2 #24 #27, study rooms #44 #46), with task chairs (or
    counter stools when h > 0.9) round it."""
    P = K.Prop("round_table", col_closed=True)
    V = P.visual
    r = d / 2
    # fix round 2 fidelity-1 (4243 matched view commons_tables): the near tables read as decagons in the foreground
    # where the photo's are round; the top is now 16-sided (visual only, the collision keeps its octagon)
    disc = _ngon(0, 0, r, 16, math.pi / 16)
    prism(V, disc, h - 0.035, h, top)
    V.poly([(x, y, h - 0.035) for x, y in reversed(disc)], top, tint=(0.7, 0.7, 0.7))
    V.box(-0.05, -0.05, 0.03, 0.05, 0.05, h - 0.035, "int_plastic", faces="+x-x+y-y", tint=base_tint)
    V.poly([(x, y, 0.03) for x, y in _ngon(0, 0, 0.30, 6)], "int_plastic", tint=base_tint)
    for k in range(chairs):
        a = rot + 2 * math.pi * (k + 0.5) / chairs
        cx, cy = math.cos(a) * (r + 0.22), math.sin(a) * (r + 0.22)
        face = math.degrees(math.atan2(-cx, -cy)) % 360.0
        P.merge(caper_stool(0.76) if stools else (chair() if chair else sayl_chair()), cx, cy, 0.0, face)
    if col:
        col_prism(P.collision, _ngon(0, 0, r, 8), 0.0, h)
    P.anchor("top", 0.0, 0.0, h)
    return P


def rect_table(L=1.83, W=0.91, h=0.76, top="int_ms_maple", legs="panel", chairs_per_side=2, chair=None,
               ends_round=False, col=True, seat_sides=(1, -1)):
    """Rectangular (optionally race-track) maple table: panel ends (training / reading tables #47 #76) or four legs;
    task chairs on the long sides. Collision: one block."""
    P = K.Prop("rect_table", col_closed=True)
    V = P.visual
    hl, hw = L / 2, W / 2
    if ends_round:
        pts = [(-hl + hw, -hw)] + [(hl - hw + hw * math.cos(a), hw * math.sin(a))
                                   for a in [-math.pi / 2 + math.pi * k / 4 for k in range(5)]]
        pts += [(-hl + hw + hw * math.cos(a), hw * math.sin(a)) for a in [math.pi / 2 + math.pi * k / 4 for k in range(1, 5)]]
        prism(V, pts, h - 0.04, h, top)
        V.poly([(x, y, h - 0.04) for x, y in reversed(pts)], top, tint=(0.7, 0.7, 0.7))
    else:
        V.box(-hl, -hw, h - 0.04, hl, hw, h, top, faces=K.BOX_ALL)
    if legs == "panel":
        for sx in (-1, 1):
            x = sx * (hl - (hw if ends_round else 0.0) - 0.15)
            V.box(x - 0.03, -hw + 0.12, 0.0, x + 0.03, hw - 0.12, h - 0.04, top, faces="+x-x+y-y", tint=(0.86, 0.86, 0.86))
    else:
        for sx in (-1, 1):
            for sy in (-1, 1):
                x, y = sx * (hl - 0.08), sy * (hw - 0.08)
                V.box(x - 0.025, y - 0.025, 0.0, x + 0.025, y + 0.025, h - 0.04, "int_metal", faces="+x-x+y-y",
                      tint=(0.72, 0.72, 0.74))
    mk = chair or sayl_chair
    for i in range(chairs_per_side):
        x = -hl + (i + 0.5) * L / chairs_per_side
        for sgn in seat_sides:
            P.merge(mk(), x, sgn * (hw + 0.24), 0.0, 180.0 if sgn > 0 else 0.0)
    if col:
        K.col_box(P.collision, -hl, -hw, 0.0, hl, hw, h, NOCAM)
    P.anchor("top", 0.0, 0.0, h)
    return P


def benching(L=4.8, W=1.5, h=0.76, top="int_ms_maple", seats_per_side=None, divider=True, col=True,
             chairs=True, stools=False):
    """Benching desk (F1 commons #36 #40, F2 #27 #28, labs #64): a long double-sided maple (or white) top on slim
    legs, a frosted-glass divider down the middle on a white power rail, task chairs both sides."""
    P = K.Prop("benching", col_closed=True)
    V = P.visual
    hl, hw = L / 2, W / 2
    V.box(-hl, -hw, h - 0.035, hl, hw, h, top, faces=K.BOX_ALL)
    n_leg = max(2, int(round(L / 1.6)) + 1)
    for i in range(n_leg):
        x = -hl + 0.1 + (L - 0.2) * i / (n_leg - 1)
        V.box(x - 0.025, -hw + 0.08, 0.0, x + 0.025, hw - 0.08, 0.05, "int_metal", faces="+x-x+y-y+z",
              tint=(0.8, 0.8, 0.82))
        V.box(x - 0.025, -0.03, 0.05, x + 0.025, 0.03, h - 0.035, "int_metal", faces="+x-x+y-y", tint=(0.8, 0.8, 0.82))
    if divider:
        V.box(-hl + 0.05, -0.04, h, hl - 0.05, 0.04, h + 0.07, "int_drywall", faces="+x-x+y-y+z", tint=(1.0, 1.0, 1.0))
        # fidelity-2 fix 2 (#36 #40 #64): pale frosted divider glass (the streaky blue int_glass read cyan)
        V.box(-hl + 0.1, -0.012, h + 0.07, hl - 0.1, 0.012, h + 0.40, "int_ms_glass_frost", faces="+y-y")
    n = seats_per_side or max(1, int(L // 0.8))
    if chairs:
        for i in range(n):
            x = -hl + (i + 0.5) * L / n
            for sgn in (1, -1):
                P.merge(caper_stool(0.76) if stools else sayl_chair(), x, sgn * (hw + 0.22), 0.0,
                        180.0 if sgn > 0 else 0.0)
    if col:
        K.col_box(P.collision, -hl, -hw, 0.0, hl, hw, h + 0.4 if divider else h, NOCAM)
    P.anchor("top", 0.0, 0.0, h)
    return P


def bar_table(L=2.4, W=0.75, h=1.05, stools_per_side=3, col=True, sides=(1, -1)):
    """Counter-height maple bar table with black stools (F1 #38 #41) or the F3 window bar (#76). sides: the local
    y sides that get stools (fidelity-4: (-1,) for the F4 window bar, stools on the room side only)."""
    P = K.Prop("bar_table", col_closed=True)
    V = P.visual
    hl, hw = L / 2, W / 2
    V.box(-hl, -hw, h - 0.04, hl, hw, h, "int_ms_maple", faces=K.BOX_ALL)
    for sx in (-1, 1):
        x = sx * (hl - 0.1)
        V.box(x - 0.04, -hw + 0.06, 0.0, x + 0.04, hw - 0.06, h - 0.04, "int_ms_maple", faces="+x-x+y-y",
              tint=(0.9, 0.9, 0.9))
    for i in range(stools_per_side):
        x = -hl + (i + 0.5) * L / stools_per_side
        for sgn in sides:
            P.merge(caper_stool(0.76), x, sgn * (hw + 0.18), 0.0, 180.0 if sgn > 0 else 0.0)
    if col:
        K.col_box(P.collision, -hl, -hw, 0.0, hl, hw, h, NOCAM)
    return P


def guitar_pick_table(L=4.2, W=1.45, h=0.76, seats=10, col=True):
    """The floor-3 14-person 'guitar-pick' table (2018 refit, #76): a long race-track maple top, wider at one end,
    on two panel bases, task chairs all round."""
    P = K.Prop("pick_table", col_closed=True)
    V = P.visual
    hl = L / 2
    pts = []
    for k in range(7):                          # wide rounded end at +x
        a = -math.pi / 2 + math.pi * k / 6
        pts.append((hl - W / 2 + W / 2 * math.cos(a), W / 2 * math.sin(a)))
    w2 = W * 0.36                               # narrow rounded end at -x
    for k in range(7):
        a = math.pi / 2 + math.pi * k / 6
        pts.append((-hl + w2 + w2 * math.cos(a), w2 * math.sin(a)))
    prism(V, pts, h - 0.06, h, "int_ms_maple")
    V.poly([(x, y, h - 0.06) for x, y in reversed(pts)], "int_ms_maple", tint=(0.7, 0.7, 0.7))
    for x in (-hl * 0.45, hl * 0.45):
        # fidelity-4 (#76): solid maple end panels nearly the table's width (they were 0.44 m posts)
        half = W / 2 * (0.36 + 0.64 * (x + hl) / L) - 0.14
        V.box(x - 0.05, -half, 0.0, x + 0.05, half, h - 0.06, "int_ms_maple", faces="+x-x+y-y", tint=(0.92, 0.9, 0.86))
    for i in range(seats // 2):
        x = -hl + 0.55 + (L - 1.1) * (i + 0.5) / (seats // 2)
        half = W / 2 * (0.36 + 0.64 * (x + hl) / L)
        for sgn in (1, -1):
            P.merge(sayl_chair(), x, sgn * (half + 0.24), 0.0, 180.0 if sgn > 0 else 0.0)
    if col:
        col_prism(P.collision, pts[::2] if len(pts) > 12 else pts, 0.0, h)
    P.anchor("top", 0.0, 0.0, h)
    return P


# ================================================================== carrels, computers
def perf_carrels(n=3, w=1.2, depth=0.75, desk_h=0.74, panel_h=1.30, double=False, monitors=False, col=True,
                 shelf=True, panel_mat="int_ms_perf", curved=True, tall_dividers=False, alt_shelf=False):
    """The 2022 perforated-panel carrels (floors 4-5 #97 #98 #101) and the floor-3 computer carrels (#65 #66): light
    grey perforated end / back panels on aluminium edges, a curved maple worksurface, an overhead shelf, Sayl
    chairs on +y. double: back to back (a centre spine panel_h tall; the top is a walkable 'carrel top').
    Collision: the desk block(s) + the spine / back panel."""
    P = K.Prop("perf_carrels", col_closed=True)
    V, C = P.visual, P.collision
    L = n * w
    hl = L / 2
    spine = 0.08
    sides = (1, -1) if double else (1,)
    for sgn in sides:
        yb = sgn * spine / 2 if double else -depth / 2
        yf = yb + sgn * depth if double else depth / 2
        lo, hi = min(yb, yf), max(yb, yf)
        for i in range(n):
            x0 = -hl + i * w
            # worksurface: a rectangle with a curved bite (the user's side)
            if curved:
                bite = [(x0 + 0.08 + (w - 0.16) * k / 4, yf - sgn * 0.12 * math.sin(math.pi * k / 4)) for k in range(5)]
                pts = [(x0, yb), (x0 + w, yb), (x0 + w, yf)] + list(reversed(bite)) + [(x0, yf)]
                if sgn < 0:
                    pts = [(x, -y if False else y) for x, y in pts]
                prism(V, pts, desk_h - 0.03, desk_h, "int_ms_maple")
            else:
                V.box(x0, lo, desk_h - 0.03, x0 + w, hi, desk_h, "int_ms_maple", faces=K.BOX_ALL)
            if monitors:
                P.merge(K.monitor(screen_w=0.6, screen_h=0.36), x0 + w / 2, yb + sgn * 0.22, desk_h, 0.0 if sgn > 0 else 180.0)
            P.merge(sayl_chair(), x0 + w / 2, yf + sgn * 0.20, 0.0, 180.0 if sgn > 0 else 0.0)
        for i in range(n + 1):                      # end / divider panels (aluminium edged)
            x = -hl + i * w
            # fix round 5: the panel stops at its aluminium edge and the edge is clearly wider (0.08 vs 0.04 m): the
            # 0.06 / 0.05 m boxes overlapped and their faces rounded onto the same planes (z-fighting, 18 m2)
            ph = panel_h if (i in (0, n) or tall_dividers) else desk_h + 0.45
            V.box(x - 0.02, lo if sgn > 0 else lo + 0.04, 0.0, x + 0.02, hi - 0.04 if sgn > 0 else hi, ph, panel_mat,
                  faces="+x-x-y+z" if sgn > 0 else "+x-x+y+z")
            V.box(x - 0.04, hi - 0.04 if sgn > 0 else lo, 0.0, x + 0.04, hi if sgn > 0 else lo + 0.04,
                  ph, "int_metal", faces="+x-x+y-y+z", tint=(0.86, 0.86, 0.88))
        if shelf and not double:
            V.box(-hl + 0.03, yb, panel_h - 0.30, hl - 0.03, yb + 0.30, panel_h - 0.27, "int_metal", faces="+y+z-z",
                  tint=T_LIGHT_STEEL)
        if alt_shelf and double:
            # fidelity-4 (#97 #98): a perforated overhead shelf on the spine over every other carrel
            for i in range(0, n, 2):
                x0 = -hl + i * w
                y0, y1 = (yb, yb + 0.30) if sgn > 0 else (yb - 0.30, yb)
                V.box(x0 + 0.05, y0, panel_h - 0.36, x0 + w - 0.05, y1, panel_h - 0.32, "int_ms_perf",
                      faces="+y+z-z" if sgn > 0 else "-y+z-z", tint=(0.92, 0.92, 0.94))
        if col:
            K.col_box(C, -hl, lo, 0.0, hl, hi, desk_h, NOCAM)
    yb0, yb1 = (-spine / 2, spine / 2) if double else (-depth / 2, -depth / 2 + 0.05)
    V.box(-hl, yb0, 0.0, hl, yb1, panel_h, panel_mat, faces="+x-x+y-y+z", mats={"+z": "int_metal"})
    if col:
        K.col_box(C, -hl, yb0 - (0.25 if double else 0.0), desk_h if double else 0.0, hl,
                  yb1 + (0.25 if double else 0.0), panel_h, NOCAM, bottom=double)
    if double:
        P.anchor("spine_top", 0.0, 0.0, panel_h)
    return P


def lab_cubicles(n=4, w=1.0, depth=0.78, desk_h=0.74, double=True, col=True, chair=None, band=True):
    """Floor-1 computer-lab rows (North / South Lab #61-#63): maple desks, grey fabric screens with an aluminium cap
    and a frosted-glass top band, monitors and towers, Sayl chairs. double: two facing rows on one spine.
    fidelity-2 fix 2 (#61 #63 #64): the top band is pale white-grey frosted glass (int_ms_glass_frost; the streaky
    blue int_glass read as a cyan stripe on every row) and the chairs are the labs' light grey Sayls (LAB_CHAIR)
    unless `chair` (sayl_chair kwargs) says otherwise. band=False (the North Lab, #61 #62: grey fabric screens only):
    no glass band, the fabric spine and the seat dividers run up to the band's old foot + 0.14 under the aluminium cap."""
    P = K.Prop("lab_cubicles", col_closed=True)
    V, C = P.visual, P.collision
    L = n * w
    hl = L / 2
    sides = (1, -1) if double else (1,)
    for sgn in sides:
        y0, y1 = sorted((sgn * 0.04, sgn * (depth + 0.04)))
        V.box(-hl, y0, desk_h - 0.03, hl, y1, desk_h, "int_ms_maple", faces=K.BOX_ALL)
        for i in range(n):
            cx = -hl + (i + 0.5) * w
            # fidelity-2 (#61 #63): large monitors with the blue desktop wallpaper
            P.merge(ms_monitor(), cx, sgn * 0.26, desk_h, 0.0 if sgn > 0 else 180.0)
            V.box(cx + 0.22, sgn * 0.12 - 0.09, desk_h, cx + 0.40, sgn * 0.12 + 0.09, desk_h + 0.38, "int_plastic",
                  faces="+x-x+y-y+z", tint=T_BLACK)
            P.merge(sayl_chair(**(LAB_CHAIR if chair is None else chair)), cx, sgn * (depth + 0.28), 0.0,
                    180.0 if sgn > 0 else 0.0)
        for i in range(n + 1):
            x = -hl + i * w
            V.box(x - 0.025, y0, 0.0, x + 0.025, y1, desk_h + 0.5, "int_ms_felt", faces="+x-x+y-y+z",
                  tint=(1.35, 1.38, 1.42))
        if col:
            K.col_box(C, -hl, y0, 0.0, hl, y1, desk_h, NOCAM)
    sp = 0.30 if band else 0.44                     # the fabric spine's top above the desk
    V.box(-hl, -0.04, 0.0, hl, 0.04, desk_h + sp, "int_ms_felt", faces="+x-x+y-y", tint=(1.35, 1.38, 1.42))
    V.box(-hl, -0.04, desk_h + sp, hl, 0.04, desk_h + sp + 0.04, "int_metal", faces="+x-x+y-y+z")
    if band:
        V.box(-hl, -0.015, desk_h + 0.34, hl, 0.015, desk_h + 0.62, "int_ms_glass_frost", faces="+y-y")
    if col:
        K.col_box(C, -hl, -0.04, 0.0, hl, 0.04, desk_h + (0.62 if band else sp + 0.04), NOCAM)
    return P


def white_benching_120(arms=3, arm_l=1.5, h=0.74, col=True, chair=None, monitors=False):
    """The basement lab's white 120-degree benching with frosted dividers (#64): `arms` desks round a hub.
    iteration 4: chair = sayl_chair kwargs (the lab's light grey LAB_CHAIR), monitors = a monitor on each desk."""
    P = K.Prop("bench120", col_closed=True)
    V = P.visual
    for k in range(arms):
        a = 2 * math.pi * k / arms
        ca, sa = math.cos(a), math.sin(a)

        def rot(x, y):
            return (x * ca - y * sa, x * sa + y * ca)
        pts = [rot(0.15, -0.38), rot(arm_l, -0.38), rot(arm_l, 0.38), rot(0.15, 0.38)]
        prism(V, pts, h - 0.03, h, "int_drywall", tint=(1.0, 1.0, 1.0))
        p, q = rot(0.2, 0.40), rot(arm_l, 0.40)
        V.wall(p, q, h, h + 0.36, "int_ms_glass_frost")         # fidelity-2 fix 2: frosted (#64), not blue
        V.wall(q, p, h, h + 0.36, "int_ms_glass_frost")
        lx, ly = rot(arm_l - 0.1, 0.0)
        V.box(lx - 0.03, ly - 0.03, 0.0, lx + 0.03, ly + 0.03, h - 0.03, "int_metal", faces="+x-x+y-y")
        cx, cy = rot(arm_l * 0.6, -0.62)
        P.merge(sayl_chair(**(chair or {})), cx, cy, 0.0, (math.degrees(-a)) % 360.0)
        if monitors:
            mx, my = rot(arm_l * 0.6, 0.12)
            P.merge(K.monitor(screen_w=0.56, screen_h=0.36), mx, my, h, (math.degrees(-a) + 180.0) % 360.0)
        if col:
            col_prism(P.collision, pts, 0.0, h)
    return P


def computer_bench(n=6, w=0.9, depth=0.75, h=0.74, double=True, col=True, top="int_drywall"):
    """The floor-2 computer area (#30): long white-laminate benches with monitors back to back, Sayl chairs."""
    P = K.Prop("computer_bench", col_closed=True)
    V = P.visual
    L = n * w
    hl = L / 2
    sides = (1, -1) if double else (1,)
    for sgn in sides:
        y0, y1 = sorted((sgn * 0.02, sgn * (depth + 0.02))) if double else (-depth / 2, depth / 2)
        V.box(-hl, y0, h - 0.03, hl, y1, h, top, faces=K.BOX_ALL, tint=(1.0, 1.0, 1.0))
        for i in range(n):
            cx = -hl + (i + 0.5) * w
            yb = sgn * 0.22 if double else -depth / 2 + 0.2
            P.merge(K.monitor(screen_w=0.56, screen_h=0.36), cx, yb, h, 0.0 if sgn > 0 else 180.0)
            yc = sgn * (depth + 0.26) if double else depth / 2 + 0.26
            P.merge(sayl_chair(), cx, yc, 0.0, 180.0 if sgn > 0 else 0.0)
        for i in range(int(L // 1.8) + 1):
            x = -hl + 0.1 + (L - 0.2) * i / max(1, int(L // 1.8))
            V.box(x - 0.02, y0 + 0.05, 0.0, x + 0.02, y1 - 0.05, h - 0.03, "int_metal", faces="+x-x+y-y")
        if col:
            K.col_box(P.collision, -hl, y0, 0.0, hl, y1, h, NOCAM)
    return P


# ================================================================== shelving
def range_unit(L, W, h, books="int_ms_stacks", end_tint=T_STEEL_BLUE, shelf_tint=T_LIGHT_STEEL, rows=None,
               seed=0, double=True, labels=True):
    """A steel library range (the 7-shelf double-faced ranges of #84-#93): light grey uprights and shelves, the
    floor's painted end panels (steel blue on 4, coral on 3) slightly proud of the range with a white label holder,
    a base kick and a cap. Visual only (the caller adds collision)."""
    P = K.Prop("range_unit", col_closed=True)
    V = P.visual
    rng = random.Random(seed)
    hl, hd = L / 2.0, W / 2.0
    et = 0.04
    base_h, cap = 0.10, 0.03
    for sx in (-1, 1):                                     # end panels
        x0, x1 = (hl - et, hl) if sx > 0 else (-hl, -hl + et)
        V.box(x0, -hd - 0.02, 0.0, x1, hd + 0.02, h + 0.02, "int_drywall", faces=("+x" if sx > 0 else "-x") + "+y-y+z",
              tint=end_tint)
        # design fix round 1: one slim label strip near the top of the panel (#83-#86); the two 0.24 m squares at
        # 62-70 % read as pairs of eyes on every aisle end. labels: True (both ends), False, or "+x" / "-x"
        if labels is True or labels == ("+x" if sx > 0 else "-x"):
            xl = x1 + 0.005 if sx > 0 else x0 - 0.005
            zc = h * 0.88
            pl = [(xl, -0.15, zc - 0.04), (xl, 0.15, zc - 0.04), (xl, 0.15, zc + 0.04), (xl, -0.15, zc + 0.04)]
            if sx < 0:
                pl.reverse()
            V.poly(pl, "int_drywall", tint=(1.0, 1.0, 1.0), normal_hint=(sx, 0, 0))
    V.box(-hl + et, -hd, h - cap, hl - et, hd, h, "int_drywall", faces="+z+y-y", tint=shelf_tint)
    V.box(-hl + et, -hd + 0.03, 0.0, hl - et, hd - 0.03, base_h, "int_drywall", faces="+y-y", tint=(0.62, 0.64, 0.66))
    zone = h - cap - base_h
    nrows = rows or max(1, int(round(zone / 0.31)))
    nsec = max(1, int(round(L / K.REAL["stack_section_w"])))
    sw = (L - 2 * et) / nsec
    for sgn in ((1, -1) if double else (1,)):
        y = sgn * (hd - 0.03)
        for k in range(nsec):
            x0 = -hl + et + k * sw
            u0 = rng.randrange(8) / 8.0
            quad = K.front_quad if sgn > 0 else K.back_quad
            V.poly(quad(x0, x0 + sw, y, base_h, h - cap), books, uvs=K.uv_rect(u0, 0.0, u0 + sw / 2.0, nrows / 2.0))
            if k:
                yu = sgn * (hd - 0.012)
                V.poly([(x0 - 0.02, yu, base_h), (x0 + 0.02, yu, base_h), (x0 + 0.02, yu, h - cap), (x0 - 0.02, yu, h - cap)],
                       "int_drywall", tint=shelf_tint, normal_hint=(0, sgn, 0))
    return P


def low_shelf(L=1.4, W=0.9, h=1.15, sign=None, books="int_ms_stacks", seed=0, col=True):
    """Grey steel double-faced low display shelf with a maple top (Collection Highlights #24 #31, New Books #32),
    a white sign panel on the +x end (sign: an int_ms_sign_* material). Collision: one block."""
    P = K.Prop("low_shelf", col_closed=True)
    V = P.visual
    hl, hw = L / 2, W / 2
    g = (0.70, 0.72, 0.76)
    V.box(-hl, -hw, 0.0, hl, hw, h - 0.04, "int_drywall", faces="+x-x", tint=g)
    V.box(-hl, -hw, h - 0.04, hl, hw, h, "int_ms_maple", faces=K.BOX_ALL)
    rng = random.Random(seed)
    for sgn in (1, -1):
        y = sgn * hw
        quad = K.front_quad if sgn > 0 else K.back_quad
        V.poly(quad(-hl + 0.03, hl - 0.03, y * 0.98, 0.08, h - 0.06), books,
               uvs=K.uv_rect(rng.randrange(8) / 8.0, 0.0, rng.randrange(8) / 8.0 + (L - 0.06) / 2.0, 1.5),
               tint=(0.9, 0.9, 0.92))
        for k in range(1, 3):                              # grey steel shelf boards
            z = 0.08 + (h - 0.14) * k / 3
            # iteration 4 (fidelity-4): the board's front face stands 6 mm proud of the book quad (it was coplanar with
            # it: a z-fighting strip along every board, coplanar_report)
            V.box(-hl + 0.03, y * 0.98 - (0.03 if sgn > 0 else 0.006), z - 0.02, hl - 0.03,
                  y * 0.98 + (0.006 if sgn > 0 else 0.03), z, "int_drywall", faces="+y-y+z", tint=g)
        V.box(-hl, y - (0.03 if sgn > 0 else 0), 0.0, -hl + 0.04, y + (0 if sgn > 0 else 0.03), h - 0.04, "int_drywall",
              faces="+x-x+y-y", tint=g)
        V.box(hl - 0.04, y - (0.03 if sgn > 0 else 0), 0.0, hl, y + (0 if sgn > 0 else 0.03), h - 0.04, "int_drywall",
              faces="+x-x+y-y", tint=g)
    if sign:
        x = hl + 0.006
        pts = [(x, -hw + 0.08, 0.40), (x, hw - 0.08, 0.40), (x, hw - 0.08, h - 0.12), (x, -hw + 0.08, h - 0.12)]
        V.poly(pts, sign, uvs=K.ONCE, normal_hint=(1, 0, 0))
    for k in range(3):                                     # face-out books standing on the top (#31 #32)
        bx = -hl + (k + 0.5) * L / 3
        tint = [(0.42, 0.52, 0.78), (0.86, 0.70, 0.40), (0.40, 0.62, 0.52)][k]
        V.poly([(bx - 0.10, 0.01, h), (bx + 0.10, 0.01, h), (bx + 0.10, -0.04, h + 0.27), (bx - 0.10, -0.04, h + 0.27)],
               "int_ms_leather", tint=tint, normal_hint=(0, 1, 0.2))
        V.poly([(bx + 0.10, -0.01, h), (bx - 0.10, -0.01, h), (bx - 0.10, -0.06, h + 0.27), (bx + 0.10, -0.06, h + 0.27)],
               "int_ms_leather", tint=(tint[0] * 0.7, tint[1] * 0.7, tint[2] * 0.7), normal_hint=(0, -1, 0.2))
    if col:
        K.col_box(P.collision, -hl, -hw, 0.0, hl, hw, h, NOCAM)
    P.anchor("top", 0.0, 0.0, h)
    return P


def compact_shelving(n=5, L=4.5, depth=0.9, h=2.2, col=True):
    """Beige movable compact-shelving ranges with hand-crank end panels (#25 #30 on floor 2): closed, so only the
    end panels and the faces of the end ranges show. Local: the ranges run along y (n side by side along x)."""
    P = K.Prop("compact", col_closed=True)
    V = P.visual
    W = n * depth
    for i in range(n):
        x0 = -W / 2 + i * depth
        V.box(x0 + 0.01, -L / 2, 0.0, x0 + depth - 0.01, L / 2, h, "int_drywall",
              faces="+y-y+z" + ("-x" if i == 0 else "") + ("+x" if i == n - 1 else ""),
              tint=(0.90, 0.86, 0.76), mats={"-x": "int_ms_stacks", "+x": "int_ms_stacks"},
              uvs={"-x": K.uv_rect(0, 0, L / 2, 3.5), "+x": K.uv_rect(0, 0, L / 2, 3.5)})
        for sy in (-1, 1):                                 # crank wheel
            yy = sy * (L / 2 + 0.005)
            c = [(x0 + depth / 2 + 0.12 * math.cos(a), yy, 1.1 + 0.12 * math.sin(a)) for a in
                 [2 * math.pi * k / 6 for k in range(6)]]
            V.poly(c if sy > 0 else list(reversed(c)), "int_metal", normal_hint=(0, sy, 0))
    if col:
        K.col_box(P.collision, -W / 2, -L / 2, 0.0, W / 2, L / 2, h, NOCAM)
    return P


def microfiche_cabinet(w=1.0, d=0.7, h=1.35, col=True):
    """Grey steel multi-drawer microform cabinet (#94)."""
    P = K.Prop("microform", col_closed=True)
    V = P.visual
    V.box(-w / 2, -d / 2, 0.0, w / 2, d / 2, h, "int_metal", faces="+x-x+y-y+z", tint=(0.86, 0.88, 0.9))
    for k in range(5):
        z = 0.12 + k * (h - 0.2) / 5
        V.box(-w / 2 + 0.04, d / 2, z, w / 2 - 0.04, d / 2 + 0.01, z + (h - 0.2) / 5 - 0.03, "int_metal",
              faces="+y+z-z", tint=(0.95, 0.96, 0.98))
        V.box(-0.12, d / 2 + 0.01, z + 0.12, 0.12, d / 2 + 0.03, z + 0.16, "int_metal", faces="+y+z", tint=(1.1, 1.1, 1.1))
    if col:
        K.col_box(P.collision, -w / 2, -d / 2, 0.0, w / 2, d / 2, h, NOCAM)
    return P


# ================================================================== lights and ceilings
def coffer(s, depth=0.42, apex=0.0, kind="light", tint=None, ribs="sw", turn=0, lay_w=0.61):
    """One 1987 ceiling coffer (floors 2-5, #23 #28 #76 #84 #100): a shallow inverted pyramid, s x s m, of four
    triangular greige facets meeting at a point `depth` m above the grid plane (apex > 0: a flat apex square
    instead), dark metal ribs on the grid lines (`ribs`: which edges, 's' 'w' 'n' 'e'; neighbours share an edge so
    each draws its south and west ones), and in one facet (`turn` 0-3 picks which) a 2' x 2' lay-in light
    ('light'), a return-air grille ('diffuser') or a round downlight ('can'), set into the slope as in #28 and #100.
    Local origin = the coffer's centre on the grid plane (place it at the ceiling height); faces look down."""
    P = K.Prop("coffer", col_closed=True)
    V = P.visual
    h = s / 2
    bot = [(-h, -h, 0.0), (h, -h, 0.0), (h, h, 0.0), (-h, h, 0.0)]          # S W -> S E -> N E -> N W
    a = apex / 2
    top = [(-a, -a, depth), (a, -a, depth), (a, a, depth), (-a, a, depth)]
    ft = {0: 1.0, 1: 0.92, 2: 0.84, 3: 0.95}          # facet tints (S E N W): the photos' light / shadow sides
    for k in range(4):
        b0, b1 = bot[k], bot[(k + 1) % 4]
        t0, t1 = top[k], top[(k + 1) % 4]
        tt = ft[k] if tint is None else ft[k] * tint
        pts = [b0, t0, b1] if apex <= 0.0 else [b0, t0, t1, b1]
        V.poly(pts, "int_ms_coffer", ao=[1.0] + [0.9] * (len(pts) - 2) + [1.0], tint=(tt, tt, tt * 0.98),
               normal_hint=(0, 0, -1))
    if apex > 0.0:
        V.poly([(x, y, depth) for x, y, _ in reversed(top)], "int_ms_coffer", normal_hint=(0, 0, -1),
               tint=(0.82, 0.82, 0.80))
    # the fixture in facet `turn` (k: 0 south, 1 east, 2 north, 3 west), a rectangle in the facet plane
    k = turn % 4
    b0, b1 = bot[k], bot[(k + 1) % 4]
    bm = ((b0[0] + b1[0]) / 2, (b0[1] + b1[1]) / 2, 0.0)
    ex, ey = (b1[0] - b0[0]) / s, (b1[1] - b0[1]) / s
    up = (-bm[0], -bm[1], depth)                       # base midpoint -> apex
    slant = math.sqrt(up[0] ** 2 + up[1] ** 2 + up[2] ** 2)
    nx, ny, nz = K._unit(_cross((ex, ey, 0.0), up))
    if nz > 0:
        nx, ny, nz = -nx, -ny, -nz

    def fq(w, f0, f1, off=0.025):                       # fix round 5: 2.5 cm off the facet (1.2 cm rounded onto it)
        out = []
        for (sx, f) in ((-1, f0), (1, f0), (1, f1), (-1, f1)):
            out.append((bm[0] + ex * sx * w / 2 + up[0] * f + nx * off, bm[1] + ey * sx * w / 2 + up[1] * f + ny * off,
                        up[2] * f + nz * off))
        return out
    f0 = 0.16
    f1 = f0 + 0.61 / slant
    if kind == "light":
        # fidelity-3: lay_w 1.22 = a 2' x 4' lay-in troffer along the facet's base (#23 #29 f3_computers_2020): two
        # 2' x 2' lens panels side by side
        if lay_w > 0.9:
            for sgn in (-1, 1):
                q = fq(lay_w / 2, f0, f1)
                sh = (ex * sgn * lay_w / 4, ey * sgn * lay_w / 4)
                V.poly([(x + sh[0], y + sh[1], z) for x, y, z in q], "int_ms_lay_in", uvs=[(0, 0), (1, 0), (1, 1), (0, 1)],
                       glow=True, tint=(1.0, 1.0, 0.97), normal_hint=(0, 0, -1))
        else:
            V.poly(fq(lay_w, f0, f1), "int_ms_lay_in", uvs=[(0, 0), (1, 0), (1, 1), (0, 1)], glow=True,
                   tint=(1.0, 1.0, 0.97), normal_hint=(0, 0, -1))
        c = fq(0.0, (f0 + f1) / 2, (f0 + f1) / 2)[0]
        P.lights.append(K.Light((c[0], c[1], c[2] - 0.6), radius=6.5, strength=0.30))
    elif kind == "diffuser":
        V.poly(fq(0.61, f0, f0 + 0.40 / slant), "int_ms_diffuser", uvs=[(0, 0), (1, 0), (1, 1), (0, 1)],
               normal_hint=(0, 0, -1), tint=(0.92, 0.92, 0.92))
    elif kind == "can":
        c = fq(0.0, 0.42, 0.42)[0]
        ring = [(c[0] + 0.11 * math.cos(t), c[1] + 0.11 * math.sin(t), c[2] - 0.004) for t in
                [2 * math.pi * j / 6 for j in range(6)]]
        V.poly(list(reversed(ring)), "int_ms_led", glow=True, tint=(1.0, 0.98, 0.92), normal_hint=(0, 0, -1))
        P.lights.append(K.Light((c[0], c[1], c[2] - 0.8), radius=5.0, strength=0.18))
    # ribs on the grid lines (0.05 m dark T-bars just below the facets' lower edges)
    rw, rz = 0.035, -0.008
    edges = {"s": ((-h, -h), (h, -h)), "e": ((h, -h), (h, h)), "n": ((-h, h), (h, h)), "w": ((-h, -h), (-h, h))}
    for e in ribs:
        (x0, y0), (x1, y1) = edges[e]
        if y0 == y1:
            q = [(x0 - rw, y0 - rw, rz), (x0 - rw, y0 + rw, rz), (x1 + rw, y0 + rw, rz), (x1 + rw, y0 - rw, rz)]
        else:
            q = [(x0 - rw, y0 - rw, rz), (x0 - rw, y1 + rw, rz), (x0 + rw, y1 + rw, rz), (x0 + rw, y0 - rw, rz)]
        V.poly(q, "int_plastic", tint=(0.62, 0.60, 0.58), ao=1.0, normal_hint=(0, 0, -1))
    return P


def ring_pendant(r=2.2, band=0.42, drop=0.75, inner=(0.55, 0.38, 0.78), n=16, cables=3, phase=0.3):
    """The floor-1 aluminium ring pendant (2014, #36-#41 #61): a brushed outer band, a painted / lit inner face
    (purple, blue or olive) and a white diffuser underneath, hung `drop` m below the ceiling on cables. Local origin
    = the centre on the CEILING plane (place it at the ceiling height). Visual only; adds an uplight-ish Light."""
    P = K.Prop("ring_pendant", col_closed=True)
    V = P.visual
    z1 = -drop
    z0 = z1 - band
    ro, ri = r, r - 0.10
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        o0, o1 = (ro * math.cos(a0), ro * math.sin(a0)), (ro * math.cos(a1), ro * math.sin(a1))
        i0, i1 = (ri * math.cos(a0), ri * math.sin(a0)), (ri * math.cos(a1), ri * math.sin(a1))
        V.wall(o0, o1, z0, z1, "int_metal", tint=(1.0, 1.0, 1.02), ao=1.0)                 # outer (faces out)
        V.wall(i1, i0, z0, z1, "int_drywall", tint=inner, glow=True)                        # inner (faces in)
        V.poly([(o0[0], o0[1], z0), (i0[0], i0[1], z0), (i1[0], i1[1], z0), (o1[0], o1[1], z0)], "int_ms_led",
               glow=True, tint=(0.96, 0.96, 0.96), normal_hint=(0, 0, -1))                  # underside lens
        # design fix round 2: the game camera (Lakitu ~3.6 m, just above the band) sees mostly the TOP face, so the
        # plain metal top read as a grey tray and the purple / blue / olive only as a thin far-side line (#36 #37).
        # A readability cheat (the real top is never seen): the top is the inner colour, lit, inside a 2.5 cm
        # aluminium lip that keeps the outer edge metal.
        rm = ro - 0.025
        m0, m1 = (rm * math.cos(a0), rm * math.sin(a0)), (rm * math.cos(a1), rm * math.sin(a1))
        V.poly([(o1[0], o1[1], z1), (m1[0], m1[1], z1), (m0[0], m0[1], z1), (o0[0], o0[1], z1)], "int_metal",
               normal_hint=(0, 0, 1))
        V.poly([(m1[0], m1[1], z1), (i1[0], i1[1], z1), (i0[0], i0[1], z1), (m0[0], m0[1], z1)], "int_drywall",
               tint=inner, glow=True, normal_hint=(0, 0, 1))
    for k in range(cables):
        a = 2 * math.pi * k / cables + phase
        x, y = (ro - 0.05) * math.cos(a), (ro - 0.05) * math.sin(a)
        V.box(x - 0.006, y - 0.006, z1, x + 0.006, y + 0.006, 0.0, "int_metal", faces="+x-x+y-y")
    P.lights.append(K.Light((0.0, 0.0, z0 - 0.5), radius=7.0, strength=0.26, color=(1.0, 0.98, 0.96)))
    # design fix round 1: plus a warm pool on the floor under each ring (a landmark in the evenly lit commons)
    P.lights.append(K.Light((0.0, 0.0, z0 - 2.0), radius=4.2, strength=0.24, color=(1.0, 0.86, 0.66)))
    return P


def wave_ribbon(L=9.0, w=0.95, amp=0.35, waves=2.0, drop=0.55, n=16, tint=(0.70, 0.72, 1.0), edge=False, phase=0.0,
                mat="int_glass", tilt=0.0):
    """Undulating translucent blue ceiling ribbon over the floor-1 elevator lobby (#37 #39 #69): a strip along
    local x, its height a sine wave. Origin = the strip's centre line start on the CEILING plane. Visual only.
    fidelity-1: edge=True adds the white edge trim (a 3.5 cm white upstand on both long edges, #69 #39); phase shifts
    the wave (in cycles); mat = the panel material (int_ms_glass_clear: the pale, unstreaked acrylic of #69).
    fix round 2: tilt = the cross-section's roll in degrees (+: the +y edge higher). The low edge stays at the
    untilted height and the other edge rises by w * tan(tilt), so a camera at the ribbons' own height (the game
    camera) sees a broad face instead of a thin strand (#69 #39: broad overlapping panels)."""
    P = K.Prop("wave_ribbon", col_closed=True)
    V = P.visual
    tr = math.tan(math.radians(tilt))

    def lift(y):                                    # the roll: 0 on the low edge
        return tr * (y + w / 2) if tr >= 0 else tr * (y - w / 2)
    for k in range(n):
        x0, x1 = L * k / n, L * (k + 1) / n
        z0 = -drop - amp * (0.5 + 0.5 * math.sin(2 * math.pi * (waves * k / n + phase)))
        z1 = -drop - amp * (0.5 + 0.5 * math.sin(2 * math.pi * (waves * (k + 1) / n + phase)))
        if edge:
            for sy in (-1, 1):
                e0, e1 = (x0, sy * w / 2), (x1, sy * w / 2)
                for a_, b_ in ((e0, e1), (e1, e0)):
                    za = z0 if a_ is e0 else z1
                    zb = z1 if a_ is e0 else z0
                    zl = lift(sy * w / 2)
                    V.poly([(a_[0], a_[1], za + zl - 0.01), (b_[0], b_[1], zb + zl - 0.01),
                            (b_[0], b_[1], zb + zl + 0.025), (a_[0], a_[1], za + zl + 0.025)], "int_drywall",
                           glow=True, tint=(0.92, 0.95, 1.0))
        lo, hi = lift(-w / 2), lift(w / 2)
        q = [(x0, -w / 2, z0 + lo), (x1, -w / 2, z1 + lo), (x1, w / 2, z1 + hi), (x0, w / 2, z0 + hi)]
        V.poly(q, mat, glow=True, tint=tint, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)], normal_hint=(0, 0, -1))
        V.poly(list(reversed(q)), mat, glow=True, tint=(tint[0] * 0.9, tint[1] * 0.9, tint[2]),
               uvs=[(0, 1), (1, 1), (1, 0), (0, 0)], normal_hint=(0, 0, 1))
    for x in (0.4, L - 0.4):
        # fix round 2: the cable stops on the panel (it ran down to the wave's lowest point wherever it hung)
        zc = -drop - amp * (0.5 + 0.5 * math.sin(2 * math.pi * (waves * x / L + phase))) + lift(0.0)
        V.box(x - 0.006, -0.006, zc, x + 0.006, 0.006, 0.0, "int_metal", faces="+x-x+y-y")
    return P


def led_strip(L, w=0.10):
    """A linear LED slot light flush with the floor-1 tile ceiling (#36 #40 #61): local x along the strip, origin at
    its centre on the ceiling plane. Glows; the caller adds Lights."""
    P = K.Prop("led_strip", col_closed=True)
    P.visual.poly([(-L / 2, -w / 2, -0.012), (-L / 2, w / 2, -0.012), (L / 2, w / 2, -0.012), (L / 2, -w / 2, -0.012)],
                  "int_ms_led", uvs=[(0, 0), (0, 1), (1, 1), (1, 0)], glow=True, tint=(0.98, 0.99, 1.0))
    return P


def soffit_lantern(s=5.6, band=0.5, drop=1.2, corner=0.7, closed=False, top_copper=False):
    """The suspended square 'lantern' of the floor-2 lounge (#24 #25 #26): a grey square frame lit white underneath,
    copper-veneer boxes on its corners and mid-sides, green LED downlights. Local origin = its centre on the CEILING
    plane it hangs from; it hangs `drop` m below it. Visual only.
    closed (iteration 4, fidelity-3, #24 #25): from below the photographed lantern is CLOSED, a white ceiling inside
    the band with a glowing cove strip round its edge: one down-facing white panel at the band top plus the strip
    (both one-sided, so a camera above it, e.g. on the F3 balcony or the walkable frame top, sees through).
    top_copper (iteration 4, design r3 #5): the frame's walkable top in the copper veneer with a ring of green LED
    dots, so the secret reads from the F3 balcony (a readability cheat: the real top is never seen; was grey drywall)."""
    P = K.Prop("lantern", col_closed=True)
    V = P.visual
    h = s / 2
    t = 0.45                       # frame width
    z1 = -drop
    z0 = z1 - band
    outer = [(-h, -h), (h, -h), (h, h), (-h, h)]
    inner = [(-h + t, -h + t), (h - t, -h + t), (h - t, h - t), (-h + t, h - t)]
    for k in range(4):
        a, b = outer[k], outer[(k + 1) % 4]
        V.wall(a, b, z0, z1, "int_drywall", tint=(0.64, 0.66, 0.66))
        ia, ib = inner[k], inner[(k + 1) % 4]
        V.wall(ib, ia, z0, z1, "int_drywall", tint=(0.92, 0.92, 0.92), glow=True)
        V.poly([(a[0], a[1], z0), (ia[0], ia[1], z0), (ib[0], ib[1], z0), (b[0], b[1], z0)], "int_ms_led", glow=True,
               tint=(0.98, 0.98, 0.96), normal_hint=(0, 0, -1))
        if top_copper:
            V.poly([(b[0], b[1], z1), (ib[0], ib[1], z1), (ia[0], ia[1], z1), (a[0], a[1], z1)], "int_ms_copper",
                   normal_hint=(0, 0, 1), tint=(1.08, 1.04, 1.0))
        else:
            V.poly([(b[0], b[1], z1), (ib[0], ib[1], z1), (ia[0], ia[1], z1), (a[0], a[1], z1)], "int_drywall",
                   normal_hint=(0, 0, 1), tint=(0.7, 0.7, 0.7))
    for (x, y) in [(-h, -h), (h, -h), (h, h), (-h, h), (0, -h), (h, 0), (0, h), (-h, 0)]:
        c = corner * (1.0 if abs(x) == abs(y) else 0.8)
        V.box(x - c / 2, y - c / 2, z0 - 0.08, x + c / 2, y + c / 2, z1 + 0.10, "int_ms_copper", faces=K.BOX_ALL)
    for (x, y) in [(-h * 0.5, -h), (h * 0.5, -h), (h, -h * 0.5), (h, h * 0.5), (h * 0.5, h), (-h * 0.5, h), (-h, h * 0.5),
                   (-h, -h * 0.5)]:
        V.poly([(x + 0.1 * math.cos(a), y + 0.1 * math.sin(a), z0 - 0.002) for a in
                [2 * math.pi * k / 6 for k in range(6)]][::-1], "int_ms_led", glow=True, tint=(0.55, 1.0, 0.35),
               normal_hint=(0, 0, -1))
    for (x, y) in [(-h + 0.2, -h + 0.2), (h - 0.2, -h + 0.2), (h - 0.2, h - 0.2), (-h + 0.2, h - 0.2)]:
        V.box(x - 0.008, y - 0.008, z1, x + 0.008, y + 0.008, 0.0, "int_metal", faces="+x-x+y-y")
    if top_copper:
        # green LED dots along the frame's centre line between the copper boxes, 6 mm proud of the top (no z-fight)
        m = h - t / 2
        for (x, y) in [(-m * 0.5, -m), (m * 0.5, -m), (m, -m * 0.5), (m, m * 0.5), (m * 0.5, m), (-m * 0.5, m),
                       (-m, m * 0.5), (-m, -m * 0.5)]:
            V.poly([(x + 0.11 * math.cos(a), y + 0.11 * math.sin(a), z1 + 0.006) for a in
                    [2 * math.pi * k / 6 for k in range(6)]], "int_ms_led", glow=True, tint=(0.55, 1.0, 0.35),
                   normal_hint=(0, 0, 1))
    if closed:
        hi, hs = h - t, h - t - 0.16          # the inner edge of the frame; the cove strip's inner edge
        V.poly([(-hs, -hs, z1), (-hs, hs, z1), (hs, hs, z1), (hs, -hs, z1)], "int_ms_wall", tint=(0.97, 0.97, 0.96),
               glow=True, normal_hint=(0, 0, -1))
        ring_o = [(-hi, -hi), (hi, -hi), (hi, hi), (-hi, hi)]
        ring_i = [(-hs, -hs), (hs, -hs), (hs, hs), (-hs, hs)]
        for k in range(4):
            a, b = ring_o[k], ring_o[(k + 1) % 4]
            ia, ib = ring_i[k], ring_i[(k + 1) % 4]
            V.poly([(a[0], a[1], z1), (ia[0], ia[1], z1), (ib[0], ib[1], z1), (b[0], b[1], z1)], "int_ms_led",
                   glow=True, tint=(1.0, 0.98, 0.92), normal_hint=(0, 0, -1))
    P.lights.append(K.Light((0.0, 0.0, z0 - 0.8), radius=8.0, strength=0.30))
    return P


def service_ring_sign(r=1.75, band=0.46, z=3.3, repeats=4, n_per=6, hang_top=None):
    """The suspended yellow 'Service Desk' ring (#23): a cylindrical band, the int_ms_sign_service texture reading
    SERVICE DESK all round (outside) and plain yellow inside, on two rods. Local origin = the ring's centre on the
    floor; hang_top = the ceiling height."""
    P = K.Prop("ring_sign", col_closed=True)
    V = P.visual
    # one repeat = SERVICE (41 px) + gap (9 px) + DESK (23 px) + gap (9 px) = 82 px of the 64 px-wide texture halves
    pieces = [("top", 0, 41), (None, 0, 9), ("bot", 0, 23), (None, 0, 9)]
    tot = sum(p[2] for p in pieces)
    circ = 2 * math.pi * r
    per = circ / repeats
    z0, z1 = z, z + band
    ang = 0.0
    for _ in range(repeats):
        for half, _, px in pieces:
            span = per * px / tot
            m = max(1, int(round(n_per * px / tot)) + 1)
            for k in range(m):
                a0 = (ang + span * k / m) / r
                a1 = (ang + span * (k + 1) / m) / r
                p0, p1 = (r * math.cos(a0), r * math.sin(a0)), (r * math.cos(a1), r * math.sin(a1))
                if half is None:
                    uv = [(0.95, 0.52), (1.0, 0.52), (1.0, 0.98), (0.95, 0.98)]
                else:
                    u0, u1 = (1.0 + px * k / m) / 64.0, (1.0 + px * (k + 1) / m) / 64.0
                    v0, v1 = (0.5, 1.0) if half == "top" else (0.0, 0.5)
                    uv = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
                # outside face: wall(p0, p1) (CCW travel; kit walls face the right of a -> b = outward), the text
                # running with the angle so it reads left to right from outside (the photo pass had it on the
                # inner face, read mirrored through the ring); plain yellow inside
                V.wall(p0, p1, z0, z1, "int_ms_sign_service", uvs=uv, glow=True, tint=(1.0, 0.98, 0.92))
                V.wall(p1, p0, z0, z1, "int_ms_sign_service", uvs=[(0.97, 0.53)] * 2 + [(0.98, 0.97)] * 2,
                       tint=(0.9, 0.85, 0.7))
            ang += span
    top = hang_top if hang_top is not None else z1 + 1.0
    for a in (0.6, 0.6 + math.pi):
        x, y = r * math.cos(a), r * math.sin(a)
        V.box(x - 0.008, y - 0.008, z1, x + 0.008, y + 0.008, top, "int_metal", faces="+x-x+y-y")
    return P


def exit_sign(z=2.4, hang_top=None, mount="wall"):
    """Red EXIT sign (#24 #47 #69)."""
    return K.sign("int_ms_exit", 0.36, 0.20, z, mount=mount, glow=True, hang_top=hang_top)


# ================================================================== room fixtures
def gis_display_wall(w=3.3, h=1.7, z=0.85, cols=3, rows=2, bezel=0.025):
    """fix round 2 (#48): the L136 tiled visualization wall, LIT: a cols x rows grid of thin-bezel displays showing
    one bright GIS aerial image across the whole grid (int_ms_gis_map mapped once over it). Local: on the wall plane
    y = 0, facing +y; bottom at z (a standing user reaches it, #48). The black back panel shows as the 2.5 cm bezels."""
    P = K.Prop("gis_wall", col_closed=True)
    P.visual.box(-w / 2 - bezel, 0.0, z - bezel, w / 2 + bezel, 0.07, z + h + bezel, "int_plastic", faces="+x-x+z-z+y",
                 tint=T_BLACK)
    cw, rh = w / cols, h / rows
    for i in range(cols):
        for j in range(rows):
            xa, xb = -w / 2 + i * cw + bezel / 2, -w / 2 + (i + 1) * cw - bezel / 2
            za, zb = z + j * rh + bezel / 2, z + (j + 1) * rh - bezel / 2
            uv = K.uv_rect((w / 2 - xb) / w, (za - z) / h, (w / 2 - xa) / w, (zb - z) / h)
            P.visual.poly(K.front_quad(xa, xb, 0.09, za, zb), "int_ms_gis_map", uvs=uv, glow=True)
    P.lights.append(K.Light((0.0, 0.7, z + h / 2), radius=2.6, strength=0.14, color=(0.85, 0.95, 0.85)))
    return P


def wall_tv(w=1.3, h=0.75, z=1.35, plate=False):
    """Wall-mounted flat TV (study rooms #44 #45, L308 #78). Local: on the wall plane y = 0, facing +y.
    fidelity-1: plate=True adds the white wall input plate (#44 #45) to the right of the screen, lower down."""
    P = K.Prop("wall_tv", col_closed=True)
    P.visual.box(-w / 2, 0.0, z, w / 2, 0.06, z + h, "int_plastic", faces="+x-x+z-z", tint=T_BLACK)
    P.visual.poly(K.front_quad(-w / 2, w / 2, 0.061, z, z + h), "int_ms_tv", uvs=K.ONCE)
    if plate:
        P.visual.box(w / 2 + 0.22, 0.0, z - 0.05, w / 2 + 0.34, 0.015, z + 0.10, "int_plastic", faces="+y+x-x+z-z",
                     tint=(0.96, 0.96, 0.95))
        P.visual.poly(K.front_quad(w / 2 + 0.25, w / 2 + 0.31, 0.016, z + 0.0, z + 0.05), "int_plastic", tint=T_BLACK)
    return P


def projection_screen(w=2.6, h=1.6, z=1.1):
    """Pull-down projection screen showing the UF slide (L136 #47). On the wall plane y = 0, facing +y."""
    P = K.Prop("projection_screen", col_closed=True)
    V = P.visual
    V.box(-w / 2 - 0.05, 0.0, z + h, w / 2 + 0.05, 0.12, z + h + 0.12, "int_drywall", faces="+y-z+z+x-x",
          tint=(0.9, 0.9, 0.9))
    V.poly(K.front_quad(-w / 2, w / 2, 0.05, z, z + h), "int_ms_projector", uvs=K.ONCE, glow=True, tint=(0.92, 0.92, 0.95))
    return P


def fish_tank(L=1.8, W=0.6, h=1.45, stand=0.78):
    """The 150-gallon planted tank across from the floor-3 elevators (#79 #80): black stand, planted water seen
    through both long faces (int_ms_aquarium), glass ends, a black hood, the club's plaque. Collision: one block
    (its lid is a red-coin spot)."""
    P = K.Prop("fish_tank", col_closed=True)
    V = P.visual
    hl, hw = L / 2, W / 2
    V.box(-hl, -hw, 0.0, hl, hw, stand, "int_plastic", faces="+x-x+y-y", tint=(0.42, 0.42, 0.44))
    # fidelity-4 (#79 #80): a planted tank in depth instead of a flat card: the planted back (int_ms_aquarium) on
    # the centre plane, layered plant fronds, black rock and driftwood in front of it, a few large rainbowfish,
    # behind clear glass faces
    zb, zt = stand + 0.02, h - 0.10
    rng = random.Random(79)
    for sgn in (1, -1):
        quad = K.front_quad if sgn > 0 else K.back_quad
        # fix round 2 fidelity-4 (f3_fish_tank_2023, _plaque_2025: a dark, dense planted tank, the plaque photo
        # averages lum ~28; the render read pale cyan-green 86/116/111): a dimmer back, darker water on the glass,
        # darker gravel, black rock and deep-green fronds
        V.poly(quad(-hl + 0.02, hl - 0.02, sgn * 0.02, zb, zt), "int_ms_aquarium", uvs=K.ONCE, glow=True,
               tint=(0.72, 0.78, 0.74))
        V.poly(quad(-hl + 0.01, hl - 0.01, sgn * hw, stand, h - 0.10), "int_glass", tint=(0.42, 0.54, 0.50))
        V.poly([(-hl + 0.02, 0.0, zb), (hl - 0.02, 0.0, zb), (hl - 0.02, sgn * (hw - 0.02), zb),
                (-hl + 0.02, sgn * (hw - 0.02), zb)][::sgn], "int_ms_carpet", tint=(0.44, 0.40, 0.32),
               normal_hint=(0, 0, 1))
        # black rock: low heptagonal lumps
        for rx, rr, rh in ((-hl * 0.55, 0.16, 0.18), (hl * 0.15, 0.13, 0.12), (hl * 0.7, 0.11, 0.22)):
            prism(V, _ngon(rx, sgn * 0.16, rr, 6, rng.uniform(0, 1)), zb, zb + rh, "int_plastic",
                  tint=(0.17, 0.17, 0.18))
        # driftwood: two slanted branches
        for x0, x1, z1 in ((-hl * 0.35, -hl * 0.05, zt - 0.12), (hl * 0.25, hl * 0.6, zt - 0.2)):
            y = sgn * 0.09
            for dy in (-0.02, 0.02):
                V.poly([(x0 - 0.03, y + dy, zb), (x0 + 0.03, y + dy, zb), (x1 + 0.02, y + dy, z1),
                        (x1 - 0.02, y + dy, z1)][::(1 if sgn * dy > 0 else -1)], "bark", tint=(0.55, 0.42, 0.30))
        # plant fronds in two layers (two-sided blades, three greens)
        # (lit by the tank hood: glow, bright greens)
        for layer, yy in ((0, 0.07), (1, 0.20)):
            nk = 11 if layer == 0 else 8
            for k in range(nk):
                x = -hl + 0.12 + (L - 0.24) * (k + rng.uniform(0.1, 0.9)) / nk
                hh = rng.uniform(0.25, 0.62) * (1.0 if layer == 0 else 0.55) * (zt - zb)
                g = rng.choice(((0.28, 0.54, 0.22), (0.38, 0.62, 0.24), (0.20, 0.44, 0.18)))
                lean = rng.uniform(-0.10, 0.10)
                for dw in (-0.09, 0.0, 0.09):
                    tri = [(x - 0.08, sgn * yy, zb), (x + 0.08, sgn * yy, zb),
                           (x + lean + dw, sgn * yy, zb + hh * (1.0 if dw == 0.0 else 0.75))]
                    V.poly(tri, "leaves_oak2", tint=g, glow=True)
                    V.poly(tri[::-1], "leaves_oak2", tint=g, glow=True)
        # rainbowfish (big: 0.16-0.2 m). fix round 2 fidelity-4: the photos' fish are mostly orange-red and yellow
        # deep-bodied rainbowfish (the flat blue diamonds read wrong): two orange-red with yellow-orange tails and one
        # blue-and-yellow, each a taller rounded hexagon body
        for fx, fz, fl, bc, tc in ((-hl * 0.45, zb + 0.42, 0.18, (1.15, 0.42, 0.16), (1.15, 0.78, 0.22)),
                                   (hl * 0.2, zb + 0.30, 0.20, (1.10, 0.36, 0.14), (1.15, 0.70, 0.20)),
                                   (hl * 0.6, zb + 0.5, 0.16, (0.40, 0.62, 1.10), (1.15, 0.86, 0.25))):
            y = sgn * 0.26
            d = 1 if rng.random() < 0.5 else -1
            body = [(fx - d * fl / 2, y, fz), (fx - d * fl * 0.18, y, fz - fl * 0.30), (fx + d * fl * 0.24, y, fz - fl * 0.24),
                    (fx + d * fl / 2, y, fz), (fx + d * fl * 0.24, y, fz + fl * 0.26), (fx - d * fl * 0.18, y, fz + fl * 0.34)]
            tail = [(fx - d * fl / 2, y, fz), (fx - d * fl * 0.78, y, fz - fl * 0.18), (fx - d * fl * 0.78, y, fz + fl * 0.18)]
            for poly, c in ((body, bc), (tail, tc)):
                V.poly(poly, "int_ms_wall", tint=c, glow=True)
                V.poly(poly[::-1], "int_ms_wall", tint=c, glow=True)
    for sx in (-1, 1):
        x = sx * hl
        V.poly([(x, -hw, stand), (x, hw, stand), (x, hw, h - 0.1), (x, -hw, h - 0.1)] if sx > 0 else
               [(x, hw, stand), (x, -hw, stand), (x, -hw, h - 0.1), (x, hw, h - 0.1)], "int_ms_aquarium",
               uvs=[(0.0, 0.0), (0.3, 0.0), (0.3, 1.0), (0.0, 1.0)], glow=True, tint=(0.46, 0.52, 0.50))
    V.box(-hl - 0.01, -hw - 0.01, h - 0.10, hl + 0.01, hw + 0.01, h, "int_plastic", faces=K.BOX_ALL, tint=(0.4, 0.4, 0.42))
    # the club's engraved acrylic plaque on the glass (#80): frosted white, so it reads in front of the clear glass
    V.box(hl * 0.35, hw + 0.006, stand + 0.04, hl * 0.85, hw + 0.016, stand + 0.20, "int_metal", faces="+y",
          tint=(1.15, 1.15, 1.15))
    # fix round 2 fidelity-4 (#80): its engraved lettering, a few dark lines 4 mm proud of the frosted face (a title
    # line, then three shorter text lines)
    xa, xb = hl * 0.35, hl * 0.85
    for k, (u0, u1, zc, th) in enumerate(((0.12, 0.88, 0.165, 0.014), (0.10, 0.90, 0.130, 0.008),
                                          (0.10, 0.78, 0.105, 0.008), (0.10, 0.62, 0.080, 0.008))):
        V.poly(K.front_quad(xa + (xb - xa) * u0, xa + (xb - xa) * u1, hw + 0.020, stand + zc - th / 2,
                            stand + zc + th / 2), "int_plastic", tint=(0.30, 0.31, 0.33), ao=1.0)
    K.col_box(P.collision, -hl, -hw, 0.0, hl, hw, h, NOCAM)
    P.anchor("lid", 0.0, 0.0, h)
    return P


def vending_machine(w=1.0, d=0.85, h=1.85):
    """Purple supply vending machine (#73). Collision: one block."""
    P = K.Prop("vending", col_closed=True)
    V = P.visual
    V.box(-w / 2, -d / 2, 0.0, w / 2, d / 2, h, "int_drywall", faces="+x-x-y+z", tint=(0.44, 0.34, 0.66))
    V.poly(K.front_quad(-w / 2, w / 2, d / 2, 0.0, h), "int_ms_vending", uvs=K.ONCE, glow=True, tint=(0.95, 0.95, 0.98))
    K.col_box(P.collision, -w / 2, -d / 2, 0.0, w / 2, d / 2, h, NOCAM)
    return P


def drinking_fountain_pair(stainless=False):
    """Bi-level drinking fountains (#69). On the wall plane y = 0, facing +y. Visual only.
    fix round 2 fidelity-1 (#69 4317): white enamel bodies (the photo's fountain on the lobby's west wall is white,
    the stainless boxes did not read), a recessed stainless basin and bubbler on top, a white back plate.
    iteration 4 (fidelity-1, #69 4317): stainless=True gives the F1 lobby unit its brushed stainless bodies (bright
    int_metal, lighter than the old stainless boxes) on a stainless back plate; the default keeps the F2 pair white."""
    P = K.Prop("fountains", col_closed=True)
    V = P.visual
    wh = (0.97, 0.97, 0.96)
    bmat, btint = ("int_metal", (1.08, 1.10, 1.14)) if stainless else ("int_drywall", wh)
    V.poly(K.front_quad(-0.62, 0.62, 0.006, 0.70, 1.30), bmat,
           tint=(1.0, 1.02, 1.06) if stainless else (0.93, 0.93, 0.92), ao=1.0)
    for x, z in ((-0.35, 0.80), (0.35, 0.95)):
        V.box(x - 0.24, 0.006, z, x + 0.24, 0.42, z + 0.20, bmat, faces="+x-x+y-z", tint=btint)
        V.poly([(x - 0.24, 0.006, z + 0.20), (x + 0.24, 0.006, z + 0.20), (x + 0.24, 0.42, z + 0.20),
                (x - 0.24, 0.42, z + 0.20)], bmat, tint=btint, normal_hint=(0, 0, 1))
        V.poly([(x - 0.17, 0.08, z + 0.21), (x + 0.17, 0.08, z + 0.21), (x + 0.17, 0.36, z + 0.21),
                (x - 0.17, 0.36, z + 0.21)], "int_metal", tint=(0.82, 0.84, 0.88), normal_hint=(0, 0, 1))
        V.box(x - 0.02, 0.14, z + 0.21, x + 0.02, 0.18, z + 0.26, "int_metal", faces="+x-x+y-y+z",
              tint=(1.0, 1.0, 1.04))
    # iteration 4 (technical): a NO_CAM block round the bodies (no back face: it stands on the wall plane)
    P.collision.box(-0.62, 0.0, 0.0, 0.62, 0.42, 1.15, NOCAM, faces="+x-x+y+z")
    return P


def stanchion(z=0.95):
    """Black queue stanchion post (#23, #69). Visual only."""
    P = K.Prop("stanchion", col_closed=True)
    V = P.visual
    V.poly([(x, y, 0.02) for x, y in _ngon(0, 0, 0.17, 6)], "int_plastic", tint=T_BLACK)
    V.box(-0.03, -0.03, 0.02, 0.03, 0.03, z, "int_plastic", faces="+x-x+y-y+z", tint=T_BLACK)
    return P


def security_gate(h=1.55, d=0.62):
    """White arched security-gate pedestal at the entrance (#23). Collision: a slim block."""
    P = K.Prop("security_gate", col_closed=True)
    V = P.visual
    V.box(-0.06, -d / 2, 0.0, 0.06, d / 2, h - 0.25, "int_drywall", faces="+x-x+y-y", tint=(1.0, 1.0, 1.0))
    top = arc(0, h - 0.25, d / 2, 0.0, math.pi, 6)
    pts = [(-0.06, y, z) for y, z in top]
    for sx in (-1, 1):
        x = sx * 0.06
        pl = [(x, y, z) for y, z in top] + [(x, -d / 2, h - 0.25)]
        V.poly(pl if sx > 0 else list(reversed(pl)), "int_drywall", tint=(1.0, 1.0, 1.0), normal_hint=(sx, 0, 0))
    for k in range(len(top) - 1):
        (y0, z0), (y1, z1) = top[k], top[k + 1]
        V.poly([(-0.06, y0, z0), (0.06, y0, z0), (0.06, y1, z1), (-0.06, y1, z1)], "int_drywall",
               normal_hint=(0, (y0 + y1) / 2, (z0 + z1) / 2 - (h - 0.25)))
    for k in range(3):                                   # the arched window ribs (dark lines)
        z = 0.5 + k * 0.28
        V.box(-0.065, -d / 2 + 0.1, z, 0.065, d / 2 - 0.1, z + 0.04, "int_plastic", faces="+x-x", tint=(0.55, 0.55, 0.58))
    del pts
    K.col_box(P.collision, -0.08, -d / 2, 0.0, 0.08, d / 2, h, NOCAM)
    return P


def news_box():
    """Orange newspaper box at the north entrance (#1). Collision: one block."""
    P = K.Prop("news_box", col_closed=True)
    V = P.visual
    V.box(-0.25, -0.22, 0.0, 0.25, 0.22, 1.05, "int_drywall", faces="+x-x+y-y+z", tint=(0.98, 0.42, 0.16))
    # design fix round 2: window and label 1.2 cm proud of the front (1-2 mm off it they z-fought: 0.11 m2)
    V.poly(K.front_quad(-0.18, 0.18, 0.232, 0.62, 0.92), "int_glass", tint=(0.6, 0.6, 0.6))
    V.poly(K.front_quad(-0.2, 0.2, 0.232, 0.18, 0.40), "int_drywall", tint=(1.0, 1.0, 1.0))
    K.col_box(P.collision, -0.25, -0.22, 0.0, 0.25, 0.22, 1.05, NOCAM)
    return P


def potted_plant(h=0.55, r=0.32):
    """Pothos in a pot (on the F2 banquette end tables, #24 #26). Visual only."""
    P = K.Prop("plant", col_closed=True)
    V = P.visual
    prism(V, _ngon(0, 0, 0.16, 6), 0.0, 0.22, "int_plastic", tint=(0.3, 0.3, 0.3))
    for k in range(5):
        a = 2 * math.pi * k / 5
        cx, cy = math.cos(a) * r * 0.5, math.sin(a) * r * 0.5
        prism(V, _ngon(cx, cy, r * 0.55, 5, a), 0.18, h * (0.75 + 0.25 * (k % 2)), "leaves_oak", top=True)
    return P


def floor_plant(h=1.55, pot_r=0.22, pot_h=0.48, seed=0):
    """fix round 2 fidelity-4: a tall potted floor plant (rubber plant / fiddle-leaf type) in a charcoal planter, beside
    the F3 fish tank so the tank reads as a feature (cu_fishctx). Collision: the pot only (a low NOCAM block)."""
    P = K.Prop("floor_plant", col_closed=True)
    V = P.visual
    rng = random.Random(1300 + seed)
    prism(V, _ngon(0, 0, pot_r, 8, 0.2), 0.0, pot_h, "int_plastic", tint=(0.24, 0.24, 0.26))
    prism(V, _ngon(0, 0, pot_r * 0.86, 8, 0.2), pot_h - 0.04, pot_h - 0.02, "int_ms_carpet", tint=(0.34, 0.28, 0.22))
    V.box(-0.02, -0.02, pot_h - 0.04, 0.02, 0.02, h * 0.82, "bark", faces="+x-x+y-y", tint=(0.50, 0.40, 0.30))
    # four leaf clusters up the stem, alternating sides, the top one largest
    for k, (zc, r) in enumerate(((pot_h + 0.22, 0.22), (pot_h + 0.46, 0.26), (h - 0.48, 0.28), (h - 0.24, 0.30))):
        a = rng.uniform(0, math.pi) + k * 1.9
        cx, cy = math.cos(a) * 0.07, math.sin(a) * 0.07
        prism(V, _ngon(cx, cy, r, 5, a), zc - 0.12, min(h, zc + 0.14), "leaves_oak", top=True,
              tint=(0.62, 0.78, 0.56))
    K.col_box(P.collision, -pot_r, -pot_r, 0.0, pot_r, pot_r, pot_h, NOCAM)
    return P


def _obox(V, p0, d, n, a0, a1, b0, b1, z0, z1, mat, tint=None, faces="abnfdu"):
    """An oriented box: a along the unit plan vector d, b along n (n = d turned left), from plan point p0."""
    def P(a, b, z):
        return (p0[0] + d[0] * a + n[0] * b, p0[1] + d[1] * a + n[1] * b, z)
    q = {"f": ([P(a0, b1, z0), P(a1, b1, z0), P(a1, b1, z1), P(a0, b1, z1)], (n[0], n[1], 0)),
         "n": ([P(a0, b0, z0), P(a1, b0, z0), P(a1, b0, z1), P(a0, b0, z1)], (-n[0], -n[1], 0)),
         "a": ([P(a0, b0, z0), P(a0, b1, z0), P(a0, b1, z1), P(a0, b0, z1)], (-d[0], -d[1], 0)),
         "b": ([P(a1, b0, z0), P(a1, b1, z0), P(a1, b1, z1), P(a1, b0, z1)], (d[0], d[1], 0)),
         "u": ([P(a0, b0, z1), P(a1, b0, z1), P(a1, b1, z1), P(a0, b1, z1)], (0, 0, 1)),
         "d": ([P(a0, b0, z0), P(a1, b0, z0), P(a1, b1, z0), P(a0, b1, z0)], (0, 0, -1))}
    for k in faces:
        pts, nh = q[k]
        V.poly(pts, mat, tint=tint, normal_hint=nh)


def storefront_leaf(V, hinge, d, w=1.15, h=2.5, t=0.05, glass="int_ms_glass_clear"):
    """fix round 2 fidelity-4: an open black-anodised storefront glass leaf (the F4 / F5 terrace doors), drawn into
    the KitMesh V from its hinge (plan point) along the unit plan vector d: stiles, a top rail, a deep bottom rail,
    clear glass both ways and a push bar on each face. Visual only."""
    n = (-d[1], d[0])
    blk = (0.16, 0.16, 0.17)
    st, tr, br = 0.07, 0.09, 0.24
    _obox(V, hinge, d, n, 0.0, st, -t / 2, t / 2, 0.0, h, "int_plastic", blk)
    _obox(V, hinge, d, n, w - st, w, -t / 2, t / 2, 0.0, h, "int_plastic", blk)
    _obox(V, hinge, d, n, st, w - st, -t / 2, t / 2, h - tr, h, "int_plastic", blk, faces="fnud")
    _obox(V, hinge, d, n, st, w - st, -t / 2, t / 2, 0.0, br, "int_plastic", blk, faces="fnu")
    gp = [(hinge[0] + d[0] * a, hinge[1] + d[1] * a) for a in (st, w - st)]
    for sg in (1, -1):
        pts = [(gp[0][0], gp[0][1], br), (gp[1][0], gp[1][1], br), (gp[1][0], gp[1][1], h - tr),
               (gp[0][0], gp[0][1], h - tr)]
        V.poly(pts, glass, ao=1.0, normal_hint=(n[0] * sg, n[1] * sg, 0))
        b0, b1 = sorted((sg * t / 2, sg * (t / 2 + 0.035)))
        _obox(V, hinge, d, n, st + 0.05, w - st - 0.05, b0, b1, 0.98, 1.03, "int_metal", (0.80, 0.82, 0.86),
              faces="fud" if sg > 0 else "nud")


def whiteboard_easel(w=1.2, h=1.6):
    """Mobile double-sided whiteboard on a frame (F2 #27). Collision: a slim block."""
    P = K.Prop("mobile_whiteboard", col_closed=True)
    V = P.visual
    V.poly(K.front_quad(-w / 2, w / 2, 0.02, 0.55, 0.55 + h * 0.62), "int_whiteboard", uvs=K.ONCE)
    V.poly(K.back_quad(-w / 2, w / 2, -0.02, 0.55, 0.55 + h * 0.62), "int_whiteboard", uvs=K.ONCE)
    for sx in (-1, 1):
        x = sx * (w / 2 + 0.03)
        V.box(x - 0.025, -0.025, 0.0, x + 0.025, 0.025, h, "int_metal", faces="+x-x+y-y+z")
        V.box(x - 0.025, -0.3, 0.0, x + 0.025, 0.3, 0.05, "int_metal", faces="+x-x+y-y+z")
    K.col_box(P.collision, -w / 2 - 0.06, -0.06, 0.0, w / 2 + 0.06, 0.06, h, NOCAM)
    return P


def easel_sign():
    """Black easel with a poster (F2 lounge #26). Visual only."""
    P = K.Prop("easel", col_closed=True)
    V = P.visual
    for x in (-0.25, 0.25):
        V.box(x - 0.015, -0.2, 0.0, x + 0.015, -0.17, 1.6, "int_plastic", faces="+x-x+y-y", tint=T_BLACK)
    V.box(-0.015, 0.15, 0.0, 0.015, 0.18, 1.5, "int_plastic", faces="+x-x+y-y", tint=T_BLACK)
    V.poly(K.front_quad(-0.3, 0.3, -0.16, 0.85, 1.6), "int_posters", uvs=K.uv_rect(0.0, 0.5, 0.25, 1.0))
    return P


def exhibit_case(L=1.2, W=0.6, h=1.1):
    """Cherry-wood exhibit case with a glass top box (F2 lounge #26). Collision: one block."""
    P = K.Prop("exhibit_case", col_closed=True)
    V = P.visual
    hl, hw = L / 2, W / 2
    V.box(-hl, -hw, 0.0, hl, hw, h - 0.3, "int_ms_veneer", faces="+x-x+y-y+z")
    V.box(-hl + 0.03, -hw + 0.03, h - 0.3, hl - 0.03, hw - 0.03, h, "int_glass", faces="+x-x+y-y+z", tint=(1.1, 1.1, 1.1))
    for k in range(3):
        x = -hl + (k + 0.5) * L / 3
        V.box(x - 0.12, -0.10, h - 0.3, x + 0.12, 0.10, h - 0.26, "int_ms_leather", faces="+z+y-y+x-x",
              tint=[(0.85, 0.8, 0.6), (0.4, 0.55, 0.8), (0.75, 0.4, 0.3)][k])
    K.col_box(P.collision, -hl, -hw, 0.0, hl, hw, h, NOCAM)
    return P


def butcher_island(L=2.4, W=1.2, h=0.92, stools=True):
    """Makerspace butcher-block island with grey storage bins underneath (#53 #54 #60). Collision: one block."""
    P = K.Prop("maker_island", col_closed=True)
    V = P.visual
    hl, hw = L / 2, W / 2
    V.box(-hl, -hw, h - 0.06, hl, hw, h, "int_ms_butcher", faces=K.BOX_ALL)
    V.box(-hl + 0.05, -hw + 0.05, 0.08, hl - 0.05, hw - 0.05, h - 0.06, "int_metal", faces="+x-x+y-y",
          tint=(0.66, 0.68, 0.72))
    for sgn in (1, -1):                                  # the bin shelves (#54 #59), both long faces
        yy = sgn * (hw - 0.04)
        quad = K.front_quad if sgn > 0 else K.back_quad
        V.poly(quad(-hl + 0.08, hl - 0.08, yy + sgn * 0.004, 0.10, h - 0.10), "int_ms_bins",
               uvs=K.ONCE if sgn > 0 else [(1, 0), (0, 0), (0, 1), (1, 1)])
    if stools:
        for k in range(2):
            x = -hl * 0.5 + k * hl
            P.merge(sayl_chair(), x, hw + 0.30, 0.0, 180.0)
    K.col_box(P.collision, -hl, -hw, 0.0, hl, hw, h, NOCAM)
    P.anchor("top", 0.0, 0.0, h)
    return P


def pegboard_wall(L=2.4, h=1.4, z=0.95):
    """Makerspace pegboard tool wall (#53 #58): on the wall plane y = 0, facing +y, with a work counter below."""
    P = K.Prop("pegboard", col_closed=True)
    V = P.visual
    V.poly(K.front_quad(-L / 2, L / 2, 0.02, z, z + h), "int_ms_pegboard", uvs=K.uv_rect(0, 0, L, h))
    V.box(-L / 2, 0.0, 0.88, L / 2, 0.65, 0.92, "int_ms_butcher", faces="+y+z+x-x")
    V.box(-L / 2, 0.0, 0.0, L / 2, 0.6, 0.88, "int_metal", faces="+y+x-x", tint=(0.36, 0.36, 0.38))
    K.col_box(P.collision, -L / 2, 0.0, 0.0, L / 2, 0.65, 0.92, NOCAM)
    return P


def printer_station(w=1.2, d=0.8, h=1.15):
    """Large multifunction printer / scanner (F2 #28, the print stations). Collision: one block."""
    P = K.Prop("printer_station", col_closed=True)
    V = P.visual
    V.box(-w / 2, -d / 2, 0.0, w / 2, d / 2, h, "int_drywall", faces="+x-x+y-y+z", tint=(0.86, 0.87, 0.88))
    V.box(-w / 2, -d / 2, h - 0.25, w / 2, d / 2 + 0.05, h - 0.18, "int_plastic", faces="+y+z", tint=(0.4, 0.4, 0.42))
    V.poly(K.front_quad(0.15, 0.45, d / 2 + 0.002, h - 0.15, h - 0.02), "int_monitor", uvs=K.ONCE, glow=True)
    K.col_box(P.collision, -w / 2, -d / 2, 0.0, w / 2, d / 2, h, NOCAM)
    return P


def door_leaf(w=0.95, h=2.13, mat="int_ms_veneer", vision=True, open_deg=0.0, tint=None):
    """A wood-veneer door leaf (study rooms #36 #38, data room #77, L308 #78), hinge at local x = 0, closed along
    +x, swung open by open_deg (positive = toward +y). Visual only (door gaps stay open for co-op traffic)."""
    P = K.Prop("door_leaf", col_closed=True)
    V = P.visual
    a = math.radians(open_deg)
    ux, uy = math.cos(a), math.sin(a)
    t = 0.045
    nx, ny = -uy * t / 2, ux * t / 2
    p0, p1 = (nx, ny), (ux * w + nx, uy * w + ny)
    q0, q1 = (-nx, -ny), (ux * w - nx, uy * w - ny)
    V.wall(q0, q1, 0.0, h, mat, tint=tint)
    V.wall(p1, p0, 0.0, h, mat, tint=tint)
    V.wall(q1, p1, 0.0, h, mat, tint=tuple(0.8 * c for c in (tint or (1.0, 1.0, 1.0))))
    V.poly([(*q0, h), (*q1, h), (*p1, h), (*p0, h)], mat, normal_hint=(0, 0, 1), tint=tint)
    if vision:
        f0, f1 = 0.62, 0.78
        for sgn in (1, -1):
            # fix round 5: 1.5 cm proud of the leaf (1 mm rounded onto the veneer's plane in the export: z-fighting)
            k = 1.0 + 0.015 / (t / 2)
            o = (nx * sgn * k, ny * sgn * k)
            a0 = (ux * w * f0 + o[0], uy * w * f0 + o[1])
            a1 = (ux * w * f1 + o[0], uy * w * f1 + o[1])
            V.wall(a1, a0, 1.0, 1.85, "int_glass", tint=(0.8, 0.85, 0.9)) if sgn > 0 else \
                V.wall(a0, a1, 1.0, 1.85, "int_glass", tint=(0.8, 0.85, 0.9))
    hx, hy = ux * (w - 0.08), uy * (w - 0.08)
    V.box(hx - 0.03, hy - 0.06, 1.0, hx + 0.03, hy + 0.06, 1.08, "int_metal", faces="+x-x+y-y+z")
    return P


def name_plaque(row, atlas="int_ms_names", w=0.9, h=0.13, z=2.75):
    """Study-room name plaque (#36 #38: 'Carson', 'Heisenberg') from the int_ms_names atlas row 0-3. On the wall
    plane y = 0, facing +y."""
    v1 = 1.0 - row * 0.25
    return K.sign(atlas, w, h, z, mount="wall", uvs=K.uv_rect(0.0, v1 - 0.25, 1.0, v1))


def bulk_name(mat, row, w=1.28, h=0.32, z=3.12):
    """fidelity-1: a study-room name lettered on the F1 bulkhead (#38 #36): one 64 x 16 row (row 0 = top) of a
    two-name cut-out texture (int_ms_bnames_*), a single quad on the wall plane y = 0 facing +y, centred at height z."""
    P = K.Prop("bulk_name", col_closed=True)
    v0 = 0.5 if row == 0 else 0.0
    P.visual.poly(K.front_quad(-w / 2, w / 2, 0.0, z - h / 2, z + h / 2), mat, uvs=K.uv_rect(0.0, v0, 1.0, v0 + 0.5),
                  ao=1.0)
    return P


# ================================================================== check
# ================================================================== photo pass 2 (more pieces from the photos)
def bentply_chair(shell=(0.60, 0.40, 0.25), cushion=(0.80, 0.81, 0.83)):
    """Bent-plywood lounge chair on four thin steel legs (the F1 lounge by the glass rooms #38): a mid walnut shell
    (seat + back in one curve) with a light grey cushion. Visual only; the sitter faces +y.
    iteration 4 (fidelity-1, #38 4272): light grey seats (were white) and a lighter shell (was (0.42, 0.26, 0.16):
    from behind its 0.8-shaded back read near-black in lounge_c); the back's outer face is shaded 0.9, not 0.8."""
    P = K.Prop("bentply_chair", col_closed=True)
    V = P.visual
    V.box(-0.30, -0.26, 0.36, 0.30, 0.26, 0.40, "int_ms_veneer", faces="+x-x+y-y-z", tint=shell)
    V.box(-0.27, -0.22, 0.40, 0.27, 0.24, 0.45, "int_ms_leather", faces="+x-x+y+z", tint=cushion)
    back = [(-0.30, -0.26, 0.40), (0.30, -0.26, 0.40), (0.33, -0.40, 0.86), (-0.33, -0.40, 0.86)]
    V.poly(back, "int_ms_veneer", tint=shell, normal_hint=(0, 1, 0.3))
    V.poly(list(reversed(back)), "int_ms_veneer", tint=(shell[0] * 0.9, shell[1] * 0.9, shell[2] * 0.9),
           normal_hint=(0, -1, -0.3))
    V.poly([(-0.27, -0.25, 0.46), (0.27, -0.25, 0.46), (0.29, -0.36, 0.80), (-0.29, -0.36, 0.80)], "int_ms_leather",
           tint=cushion, normal_hint=(0, 1, 0.3))
    for sx in (-1, 1):
        for sy in (-1, 1):
            a, b = (sx * 0.24, sy * 0.20), (sx * 0.30, sy * 0.28)
            V.wall(a, b, 0.0, 0.36, "int_metal", tint=(0.7, 0.7, 0.72))
            V.wall(b, a, 0.0, 0.36, "int_metal", tint=(0.7, 0.7, 0.72))
    return P


def lectern(w=1.1, d=0.6, h=0.95):
    """Teaching lectern (L136 #47): a black laminate cabinet on casters with a dual-monitor arm. Collision: a block."""
    P = K.Prop("lectern", col_closed=True)
    V = P.visual
    V.box(-w / 2, -d / 2, 0.08, w / 2, d / 2, h, "int_plastic", faces=K.BOX_ALL, tint=T_BLACK)
    V.box(-w / 2 + 0.05, -d / 2 - 0.01, 0.20, w / 2 - 0.05, -d / 2, h - 0.12, "int_ms_veneer", faces="-y",
          tint=(0.55, 0.40, 0.28))
    V.box(-0.03, -0.06, h, 0.03, 0.0, h + 0.36, "int_metal", faces="+x-x+y-y")
    for sx in (-1, 1):
        P.merge(K.monitor(screen_w=0.52, screen_h=0.32), sx * 0.29, -0.02, h + 0.04, 180.0)
    K.col_box(P.collision, -w / 2, -d / 2, 0.0, w / 2, d / 2, h, NOCAM)
    return P


def training_table(L=1.83, W=0.6, h=0.74, chairs=2, chair_tint=None, base="tleg"):
    """Flip-top training table on two grey T-legs with casters (L136 #47 #49, L308 #78): a maple top, chairs on the
    +y side (Caper stacking chairs, black). base="pedestal" (fidelity-4, L308 #78): two chunky grey pedestal
    columns on wide flat feet. Collision: one block (the top)."""
    P = K.Prop("training_table", col_closed=True)
    V = P.visual
    hl, hw = L / 2, W / 2
    V.box(-hl, -hw, h - 0.035, hl, hw, h, "int_ms_maple", faces=K.BOX_ALL)
    V.box(-hl + 0.1, -hw + 0.02, h - 0.10, hl - 0.1, -hw + 0.04, h - 0.035, "int_metal", faces="+y-y",
          tint=(0.62, 0.63, 0.66))
    for sx in (-1, 1):
        x = sx * (hl - (0.22 if base == "pedestal" else 0.12))
        if base == "pedestal":
            V.box(x - 0.08, -0.15, 0.05, x + 0.08, 0.15, h - 0.035, "int_metal", faces="+x-x+y-y",
                  tint=(0.58, 0.59, 0.62))
            V.box(x - 0.11, -hw + 0.05, 0.0, x + 0.11, hw - 0.05, 0.05, "int_metal", faces="+x-x+y-y+z",
                  tint=(0.50, 0.51, 0.54))
            continue
        V.box(x - 0.03, -0.03, 0.06, x + 0.03, 0.03, h - 0.035, "int_metal", faces="+x-x+y-y",
              tint=(0.62, 0.63, 0.66))
        V.box(x - 0.03, -hw + 0.04, 0.03, x + 0.03, hw - 0.04, 0.07, "int_metal", faces="+x-x+y-y+z",
              tint=(0.62, 0.63, 0.66))
    for i in range(chairs):
        cx = -hl + (i + 0.5) * L / chairs
        P.merge(guest_chair(chair_tint or (0.30, 0.31, 0.34)), cx, hw + 0.30, 0.0, 180.0)
    K.col_box(P.collision, -hl, -hw, 0.0, hl, hw, h, NOCAM)
    P.anchor("top", 0.0, 0.0, h)
    return P


def crochet_jellyfish(drop=1.6, r=0.32, tint=(0.86, 0.88, 0.94)):
    """The crocheted jellyfish hanging in the makerspace (#53 #54): a dome with long tentacle strands, hung from the
    ceiling plane (local origin = the hanging point ON the ceiling; it hangs below). Visual only."""
    P = K.Prop("jellyfish", col_closed=True)
    V = P.visual
    zt = -drop + 1.0
    ring = [(r * math.cos(2 * math.pi * k / 6), r * math.sin(2 * math.pi * k / 6)) for k in range(6)]
    for a, b in zip(ring, ring[1:] + ring[:1]):
        V.poly([(a[0], a[1], zt - 0.25), (b[0], b[1], zt - 0.25), (0.0, 0.0, zt)], "int_ms_fab_multi", tint=tint,
               normal_hint=(a[0] + b[0], a[1] + b[1], 0.5))
        V.poly([(a[0] * 0.7, a[1] * 0.7, -drop), (b[0] * 0.7, b[1] * 0.7, -drop), (b[0], b[1], zt - 0.25),
                (a[0], a[1], zt - 0.25)], "int_ms_fab_multi", tint=(tint[0] * 0.9, tint[1] * 0.9, tint[2]),
               normal_hint=(a[0] + b[0], a[1] + b[1], 0.0))
    V.box(-0.006, -0.006, zt, 0.006, 0.006, 0.0, "int_metal", faces="+x-x+y-y")
    return P


def glass_sign(mat, w, h, z, glow=True):
    """A cut-out sign hung just behind a glass front (the MARSTON MAKERSPACE neon #51 #52): local plane y = 0,
    facing +y, both faces (seen through the glass from either side). Visual only."""
    P = K.Prop("glass_sign", col_closed=True)
    P.visual.poly(K.front_quad(-w / 2, w / 2, 0.0, z, z + h), mat, uvs=K.ONCE, glow=glow)
    P.visual.poly(K.back_quad(-w / 2, w / 2, -0.004, z, z + h), mat, uvs=[(1, 0), (0, 0), (0, 1), (1, 1)], glow=glow)
    return P


def wire_shelving(L=1.2, d=0.46, h=1.85, seed=0, col=True, bins=False):
    """Chrome wire shelving with cardboard boxes, bins and binders (the staff / tool-lending room behind the service
    desk #23, the makerspace #53): four posts, five wire shelves, a mix of boxes on them. Local front = +y.
    bins (iteration 4, fidelity-3, #23): the tool-lending bay: rows of red and orange plastic bins instead."""
    P = K.Prop("wire_shelving", col_closed=True)
    V = P.visual
    rng = random.Random(seed)
    hl, hd = L / 2, d / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (hl - 0.02), sy * (hd - 0.02)
            V.box(x - 0.012, y - 0.012, 0.0, x + 0.012, y + 0.012, h, "int_metal", faces="+x-x+y-y",
                  tint=(1.1, 1.1, 1.12))
    for k in range(5):
        z = 0.15 + (h - 0.2) * k / 4
        V.box(-hl, -hd, z - 0.015, hl, hd, z, "int_metal", faces="+z-z+y-y", tint=(1.0, 1.0, 1.0))
        if k == 4:
            continue
        x = -hl + 0.04
        while x < hl - 0.2:
            w = rng.uniform(0.18, 0.42)
            hh = rng.uniform(0.12, (h - 0.2) / 4 - 0.06)
            kind = rng.random()
            if bins:
                w = 0.36
                hh = min((h - 0.2) / 4 - 0.07, 0.30)
                tint = rng.choice([(1.0, 0.24, 0.14), (1.0, 0.24, 0.14), (1.0, 0.50, 0.12)])
                V.box(x, -hd + 0.03, z, min(hl - 0.03, x + w), hd - 0.05, z + hh, "int_ms_wall", faces="+x-x+y+z",
                      tint=tint)
                x += w + 0.03
                continue
            if kind < 0.55:
                mat, tint = "int_wood", (0.95, 0.80, 0.58)                        # cardboard
            elif kind < 0.8:
                mat, tint = "int_ms_wall", rng.choice([(1.0, 1.0, 1.0), (0.55, 0.72, 1.0), (1.0, 0.45, 0.32)])
            else:
                mat, tint = "int_ms_leather", rng.choice([(0.3, 0.4, 0.75), (0.75, 0.3, 0.25), (0.25, 0.25, 0.28)])
            V.box(x, -hd + 0.03, z, min(hl - 0.03, x + w), hd - 0.05, z + hh, mat, faces="+x-x+y+z", tint=tint)
            x += w + rng.uniform(0.02, 0.08)
    if col:
        K.col_box(P.collision, -hl, -hd, 0.0, hl, hd, h, NOCAM)
    return P


def tool_case(w=0.5, d=0.36, h=0.42, tint=(0.95, 0.28, 0.14)):
    """A red hard tool / equipment case (the lending kits on the staff-room floor, #23). Visual only."""
    P = K.Prop("tool_case", col_closed=True)
    V = P.visual
    V.box(-w / 2, -d / 2, 0.0, w / 2, d / 2, h, "int_ms_wall", faces="+x-x+y-y+z", tint=tint)
    V.box(-0.08, -d / 2 - 0.02, h - 0.12, 0.08, -d / 2, h - 0.06, "int_plastic", faces="-y+z", tint=T_BLACK)
    return P


# ================================================================== fidelity-2: the makerspace and the F1 labs
T_STEEL_FRAME = (0.62, 0.64, 0.68)       # the islands' grey steel frames [#54 #56]
T_WIRE_BLACK = (0.28, 0.28, 0.30)        # black wire shelving [#53]


def ms_monitor(screen_w=0.60, screen_h=0.37, z=0.12, dark=False):
    """fidelity-2 (#61 #63 #64): a large lab monitor showing the blue desktop wallpaper (int_ms_monitor; the kit's
    int_monitor window read as an error dialog from the game camera). Base centre at the desk surface, the screen
    faces +y and glows. Visual only.
    iteration 4 (fidelity-4, #76 the data consultation room): dark=True is a monitor that is off: the glossy black
    int_ms_tv screen (faint diagonal sheen), not lit."""
    P = K.Prop("ms_monitor", col_closed=True)
    V = P.visual
    hw = screen_w / 2.0
    scr = "int_ms_tv" if dark else "int_ms_monitor"
    V.box(-0.12, -0.1, 0.0, 0.12, 0.08, 0.015, "int_plastic", faces="+x-x+y-y+z", tint=T_BLACK)
    V.box(-0.03, -0.06, 0.015, 0.03, -0.03, z + 0.08, "int_plastic", faces="+x-x+y-y", tint=T_BLACK)
    V.box(-hw, -0.03, z, hw, 0.0, z + screen_h, "int_plastic", faces=K.BOX_ALL, mats={"+y": scr},
          uvs={"+y": K.ONCE}, tint=T_BLACK)
    for p in V.polys[-6:]:
        if p.mat == scr:
            p.glow = not dark
            p.tint = None
    return P


def maker_island2(L=1.9, W=1.2, h=0.92, chairs_per_side=2):
    """fidelity-2 (#53 #54 #56): a butcher-block island on a grey steel frame, open bin shelves under the top on both
    long faces, Sayl chairs on both long sides. Local: long axis x. Collision: one block (stand-on top)."""
    P = K.Prop("maker_island", col_closed=True)
    V = P.visual
    hl, hw = L / 2, W / 2
    V.box(-hl, -hw, h - 0.06, hl, hw, h, "int_ms_butcher", faces=K.BOX_ALL)
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (hl - 0.07), sy * (hw - 0.07)
            V.box(x - 0.03, y - 0.03, 0.0, x + 0.03, y + 0.03, h - 0.06, "int_metal", faces="+x-x+y-y",
                  tint=T_STEEL_FRAME)
    V.box(-hl + 0.05, -hw + 0.08, 0.10, hl - 0.05, hw - 0.08, h - 0.06, "int_metal", faces="+x-x+z",
          tint=(0.44, 0.45, 0.48))
    if W >= 1.0:                                         # work on the top (#53 #54): a bin, a tool case, a part
        rng = random.Random(int(L * 100 + W * 10))
        for k, (u, v) in enumerate(((-0.45, 0.25), (0.35, -0.20), (0.05, 0.30))):
            w_, d_, h_ = ((0.36, 0.26, 0.12), (0.30, 0.20, 0.10), (0.14, 0.14, 0.08))[k]
            tint = (T_BLACK, (0.86, 0.30, 0.16), rng.choice(((0.25, 0.55, 0.95), (0.96, 0.82, 0.25))))[k]
            V.box(u - w_ / 2, v - d_ / 2, h, u + w_ / 2, v + d_ / 2, h + h_, "int_ms_wall", faces="+x-x+y-y+z",
                  tint=tint)
    for sgn in (1, -1):                                  # the bin shelves (#54 #59), both long faces
        yy = sgn * (hw - 0.08)
        quad = K.front_quad if sgn > 0 else K.back_quad
        V.poly(quad(-hl + 0.10, hl - 0.10, yy, 0.12, h - 0.10), "int_ms_bins",
               uvs=K.ONCE if sgn > 0 else [(1, 0), (0, 0), (0, 1), (1, 1)])
        for k in range(chairs_per_side):
            x = -hl + (k + 0.5) * L / chairs_per_side
            P.merge(sayl_chair(), x, sgn * (hw + 0.30), 0.0, 180.0 if sgn > 0 else 0.0)
    K.col_box(P.collision, -hl, -hw, 0.0, hl, hw, h, NOCAM)
    P.anchor("top", 0.0, 0.0, h)
    return P


def printer_rack(L=1.2, d=0.5, h=1.85, printers=5, seed=0, col=True):
    """fidelity-2 (#53 #54): black wire shelving along the inside of the makerspace glass with ~0.45 m desktop 3D
    printers on it (dark frames, lit open fronts, a part on the bed), filament boxes on the top shelf. Local front
    = +y."""
    P = K.Prop("printer_rack", col_closed=True)
    V = P.visual
    rng = random.Random(seed)
    hl, hd = L / 2, d / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (hl - 0.02), sy * (hd - 0.02)
            V.box(x - 0.014, y - 0.014, 0.0, x + 0.014, y + 0.014, h, "int_metal", faces="+x-x+y-y",
                  tint=T_WIRE_BLACK)
    shelves = (0.12, 0.68, 1.24, h - 0.02)
    for z in shelves:
        V.box(-hl, -hd, z - 0.02, hl, hd, z, "int_metal", faces="+z-z+y-y", tint=T_WIRE_BLACK)
    slots = [(1, 0), (1, 1), (2, 0), (2, 1), (0, 0), (0, 1)][:printers]
    pw, pd, ph = 0.45, 0.42, 0.45
    for (si, k) in slots:
        z = shelves[si]
        px = -hl + 0.06 + pw / 2 + k * (L - 0.12 - pw)
        x0, x1, y0, y1 = px - pw / 2, px + pw / 2, -pd / 2, pd / 2
        V.box(x0, y0, z, x1, y1, z + ph, "int_plastic", faces="+x-x-y+z", tint=(0.20, 0.20, 0.22))
        V.poly(K.front_quad(x0 + 0.03, x1 - 0.03, y1 - 0.05, z + 0.04, z + ph - 0.05), "int_ms_wall", glow=True,
               tint=(1.0, 0.95, 0.84))
        for (u0, u1, w0, w1) in ((x0, x1, z, z + 0.04), (x0, x1, z + ph - 0.05, z + ph), (x0, x0 + 0.03, z, z + ph),
                                 (x1 - 0.03, x1, z, z + ph)):
            V.poly(K.front_quad(u0, u1, y1, w0, w1), "int_plastic", tint=(0.16, 0.16, 0.18))
        c = rng.choice(((0.95, 0.45, 0.15), (0.25, 0.55, 0.95), (0.95, 0.85, 0.25), (0.9, 0.25, 0.3)))
        V.box(px - 0.06, -0.05, z + 0.04, px + 0.06, 0.07, z + 0.14, "int_ms_wall", faces="+x-x+y+z", tint=c)
        V.box(px - 0.08, -0.12, z + ph, px + 0.08, 0.04, z + ph + 0.07, "int_ms_wall", faces="+x-x+y-y+z", tint=c)
    for (si, k) in [(s, kk) for s in range(3) for kk in range(2) if (s, kk) not in slots] + [(3, 0), (3, 1)]:
        z = shelves[si]
        x = -hl + 0.06 + k * L / 2
        V.box(x, -hd + 0.04, z, x + L / 2 - 0.12, hd - 0.06, z + rng.uniform(0.16, 0.30), "int_wood",
              faces="+x-x+y-y+z", tint=(0.95, 0.80, 0.58))
    if col:
        K.col_box(P.collision, -hl, -hd, 0.0, hl, hd, h, NOCAM)
    return P


def spool_wall(L=2.4, z0=1.0, z1=2.3, seed=0):
    """fidelity-2 (#60): the wall of coloured thread spools and ribbon rolls on pegs above the long sewing table.
    On the wall plane y = 0, facing +y. Visual only."""
    P = K.Prop("spool_wall", col_closed=True)
    V = P.visual
    rng = random.Random(seed)
    V.poly(K.front_quad(-L / 2, L / 2, 0.012, z0, z1), "int_ms_pegboard", uvs=K.uv_rect(0, 0, L, z1 - z0))
    cols = ((0.86, 0.20, 0.20), (0.95, 0.55, 0.15), (0.95, 0.85, 0.22), (0.30, 0.70, 0.35), (0.25, 0.50, 0.88),
            (0.55, 0.35, 0.78), (0.96, 0.62, 0.72), (1.0, 1.0, 1.0), (0.22, 0.22, 0.24), (0.40, 0.80, 0.80))
    rows = int((z1 - z0 - 0.06) / 0.16)
    for r in range(rows):
        z = z0 + 0.05 + r * 0.16
        x = -L / 2 + 0.06
        while x < L / 2 - 0.12:
            w = rng.choice((0.05, 0.05, 0.06, 0.10))
            hh = 0.08 if w < 0.08 else 0.06
            V.box(x, 0.012, z, x + w, 0.075, z + hh, "int_ms_wall", faces="+y+z", tint=rng.choice(cols))
            x += w + 0.03
    return P


def sewing_machine(tint=(0.97, 0.97, 0.95)):
    """fidelity-2 (#54 #60): a white domestic sewing machine (~0.42 x 0.18 x 0.30 m) on a bench. Visual only."""
    P = K.Prop("sewing_machine", col_closed=True)
    V = P.visual
    V.box(-0.21, -0.09, 0.0, 0.21, 0.09, 0.08, "int_ms_wall", faces="+x-x+y-y+z", tint=tint)
    V.box(0.11, -0.08, 0.08, 0.20, 0.08, 0.20, "int_ms_wall", faces="+x-x+y-y", tint=tint)
    V.box(-0.19, -0.08, 0.20, 0.20, 0.08, 0.30, "int_ms_wall", faces="+x-x+y-y+z-z", tint=tint)
    V.box(-0.19, -0.02, 0.10, -0.16, 0.02, 0.20, "int_metal", faces="+x-x+y-y", tint=(0.7, 0.7, 0.72))
    V.box(0.12, 0.08, 0.20, 0.19, 0.095, 0.27, "int_plastic", faces="+y", tint=(0.86, 0.24, 0.20))
    return P


def hex_pinboards(r=0.17, z=1.20):
    """fidelity-2 (#51 right): the honeycomb cluster of hexagon pinboards on the brick pier outside the makerspace
    (white, pale blue, yellow and sky blue, a few pinned papers). On the wall plane y = 0, facing +y. Visual only."""
    P = K.Prop("hex_pinboards", col_closed=True)
    V = P.visual
    dx = r * math.sqrt(3.0)
    cells = ((0, 0, (0.96, 0.96, 0.94)), (1, 0, (0.62, 0.78, 0.96)), (0, 1, (0.98, 0.84, 0.30)),
             (1, 1, (0.96, 0.96, 0.94)), (0, 2, (0.62, 0.78, 0.96)), (1, 2, (0.98, 0.84, 0.30)),
             (0, 3, (0.96, 0.96, 0.94)), (1, 3, (0.45, 0.66, 0.92)), (0, 4, (0.98, 0.84, 0.30)))
    for (i, j, tint) in cells:
        cx = (i - 0.5) * dx + (0.5 * dx if j % 2 else 0.0) - 0.25 * dx
        cz = z + j * 1.5 * r
        pts = [(cx + r * math.cos(a), 0.02, cz + r * math.sin(a)) for a in
               [math.radians(30 + 60 * k) for k in range(6)]][::-1]
        V.poly(pts, "int_ms_wall", tint=tint, normal_hint=(0, 1, 0))
        if (i + j) % 3 == 0:
            V.poly(K.front_quad(cx - 0.06, cx + 0.05, 0.024, cz - 0.07, cz + 0.06), "int_ms_wall",
                   tint=(1.0, 1.0, 1.0))
    return P


def wall_clock(r=0.18, z=2.95):
    """A round black-rimmed wall clock (#51 the makerspace pier, #69): on the wall plane y = 0, facing +y. Visual
    only."""
    P = K.Prop("wall_clock", col_closed=True)
    V = P.visual
    for rr, yo, mat, tint in ((r, 0.02, "int_plastic", T_BLACK), (r - 0.03, 0.026, "int_ms_wall", (1.0, 1.0, 1.0))):
        V.poly([(rr * math.cos(a), yo, z + rr * math.sin(a)) for a in
                [2 * math.pi * k / 12 for k in range(12)]][::-1], mat, tint=tint, normal_hint=(0, 1, 0))
    for (u0, u1, z0, z1) in ((-0.008, 0.008, z, z + r * 0.62), (-0.008, r * 0.45, z - 0.008, z + 0.008)):
        V.poly(K.front_quad(u0, u1, 0.032, z0, z1), "int_plastic", tint=T_BLACK)
    return P


def string_lights(L=8.0, z=3.25, sag=0.14, spans=4, knots=None):
    """fidelity-2 (#51): warm string lights draped along the storefront head: a dark cord in shallow swags with a
    glowing bulb every ~0.3 m, both faces. Local: along x from -L/2 to L/2 in the plane y = 0. Visual only.
    fidelity-2 fix 2 (#51 #52): knots = local x of the points where the cord is tied up at z (the mullions); the cord
    hangs in a catenary swag between each pair (sag scaled with the span, `sag` for a 1.75 m bay), so the swags read
    bay by bay as in the photos (without knots: `spans` equal swags, as before)."""
    P = K.Prop("string_lights", col_closed=True)
    V = P.visual
    n = max(2, int(L / 0.3))
    if knots:
        ks = sorted(set([-L / 2] + [k for k in knots if -L / 2 < k < L / 2] + [L / 2]))

        def zc(x):
            for a, b in zip(ks, ks[1:]):
                if a - 1e-6 <= x <= b + 1e-6:
                    span = b - a
                    t = (x - a) / span if span > 1e-6 else 0.0
                    c = 2.2                                   # catenary shape: cosh, normalised to 0 at the ends
                    d = (math.cosh(c * (2 * t - 1)) - math.cosh(c)) / (math.cosh(c) - 1.0)
                    return z + sag * min(1.6, span / 1.75) * d
            return z
        xs = sorted(set([-L / 2 + k * L / n for k in range(n + 1)] + ks))
        bulbs = set(round(-L / 2 + k * L / n, 6) for k in range(1, n))
    else:
        def zc(x):
            t = ((x + L / 2) / (L / spans)) % 1.0
            return z - sag * 4.0 * t * (1.0 - t)
        xs = [-L / 2 + k * L / n for k in range(n + 1)]
        bulbs = set(round(x, 6) for x in xs[1:-1])
    px, pz = xs[0], zc(xs[0])
    for k, x in enumerate(xs[1:], 1):
        zz = zc(x) if (k < len(xs) - 1 or knots) else z
        V.poly([(px, 0.0, pz), (x, 0.0, zz), (x, 0.0, zz + 0.014), (px, 0.0, pz + 0.014)], "int_plastic",
               tint=T_BLACK, normal_hint=(0, -1, 0))
        V.poly([(px, 0.0, pz + 0.014), (x, 0.0, zz + 0.014), (x, 0.0, zz), (px, 0.0, pz)], "int_plastic",
               tint=T_BLACK, normal_hint=(0, 1, 0))
        if round(x, 6) in bulbs:
            for q in (K.front_quad(x - 0.035, x + 0.035, 0.004, zz - 0.10, zz - 0.02),
                      K.back_quad(x - 0.035, x + 0.035, -0.004, zz - 0.10, zz - 0.02)):
                V.poly(q, "int_ms_wall", glow=True, tint=(1.0, 0.84, 0.50))
        px, pz = x, zz
    return P


def glider_chair(tint=(0.86, 0.74, 0.50), wood=(0.80, 0.58, 0.34), col=False):
    """fidelity-2 fix 2 (#75, wellness room): the tan upholstered nursing glider: a cushioned seat and a tall padded
    back leaning back between WOODEN arms on front and rear posts, on a wooden glider base (two runners and a cross
    rail). The sitter faces +y. ~70 tris; collision (optional) one block."""
    P = K.Prop("glider_chair", col_closed=True)
    V = P.visual
    dark = tuple(c * 0.84 for c in tint)
    for sx in (-1, 1):
        V.box(sx * 0.30 - 0.03, -0.36, 0.0, sx * 0.30 + 0.03, 0.34, 0.06, "int_ms_maple", faces="+x-x+y-y+z", tint=wood)
    V.box(-0.27, -0.04, 0.06, 0.27, 0.04, 0.16, "int_ms_maple", faces="+y-y+z", tint=wood)
    V.box(-0.26, -0.30, 0.16, 0.26, 0.32, 0.40, "int_ms_leather", faces="+x-x+y-y", tint=dark)
    V.box(-0.26, -0.26, 0.40, 0.26, 0.34, 0.51, "int_ms_leather", faces="+x-x+y+z", tint=tint)
    # the tall padded back (0.10 thick), leaning back
    f = [(-0.26, -0.24, 0.50), (0.26, -0.24, 0.50), (0.26, -0.38, 1.10), (-0.26, -0.38, 1.10)]
    r = [(x, y - 0.10, z) for x, y, z in f]
    V.poly(f, "int_ms_leather", tint=tint, normal_hint=(0, 1, 0.2))
    V.poly(list(reversed(r)), "int_ms_leather", tint=dark, normal_hint=(0, -1, 0))
    V.poly([f[3], f[2], r[2], r[3]], "int_ms_leather", tint=tint, normal_hint=(0, 0, 1))
    for i0, i1, sx in ((0, 3, -1), (1, 2, 1)):
        V.poly([f[i0], f[i1], r[i1], r[i0]], "int_ms_leather", tint=dark, normal_hint=(sx, 0, 0))
    # the arms (#75): upholstered side panels under a wooden arm rail, the wood running down the front post
    for sx in (-1, 1):
        x0, x1 = (0.27, 0.35) if sx > 0 else (-0.35, -0.27)
        V.box(x0, -0.34, 0.62, x1, 0.38, 0.67, "int_ms_maple", faces="+x-x+y-y+z-z", tint=wood)
        V.box(x0 + 0.01, 0.27, 0.06, x1 - 0.01, 0.34, 0.62, "int_ms_maple", faces="+x-x+y-y", tint=wood)
        V.box(x0 + 0.005, -0.32, 0.16, x1 - 0.005, 0.27, 0.62, "int_ms_leather", faces="+x-x-y", tint=tint)
    if col:
        K.col_box(P.collision, -0.35, -0.42, 0.0, 0.35, 0.38, 0.67, NOCAM)
    return P


def x_side_table(r=0.24, h=0.56, top=(0.97, 0.97, 0.96), leg=(0.26, 0.24, 0.24)):
    """fidelity-2 fix 2 (#75, wellness room): a round side table, a white top on two crossed dark X frames (each a
    pair of slanted bars crossing mid-height). Visual only."""
    P = K.Prop("x_side_table", col_closed=True)
    V = P.visual
    prism(V, _ngon(0.0, 0.0, r, 12), h - 0.03, h, "int_drywall", tint=top)
    w = 0.016
    for ang in (math.radians(45.0), math.radians(135.0)):
        ca, sa = math.cos(ang), math.sin(ang)
        for (u0, u1) in ((-0.82 * r, 0.82 * r), (0.82 * r, -0.82 * r)):
            du, dz = u1 - u0, h - 0.03
            L = math.hypot(du, dz)
            nu, nz = -dz / L * w, du / L * w
            q = [((u0 - nu) * ca, (u0 - nu) * sa, 0.0 - nz), ((u0 + nu) * ca, (u0 + nu) * sa, 0.0 + nz),
                 ((u1 + nu) * ca, (u1 + nu) * sa, dz + nz), ((u1 - nu) * ca, (u1 - nu) * sa, dz - nz)]
            q = [(x, y, max(0.0, min(h - 0.03, z))) for x, y, z in q]
            V.poly(q, "int_metal", tint=leg)
            V.poly(list(reversed(q)), "int_metal", tint=leg)
    return P


def sink_counter(L=1.5, D=0.60, h=0.91, col=True, ada=False):
    """fidelity-2 fix 2 (#73 #74, wellness room): the white sink counter: a white solid-surface top with an inset
    stainless sink and a gooseneck faucet on a white base cabinet (door joints, small pulls, a dark recessed toe kick),
    a white paper-towel dispenser and a soap dispenser on the wall above. Local: the wall face is y = 0, the counter
    stands in front (+y), x along the wall. Collision: the counter block ('nocam')."""
    P = K.Prop("sink_counter", col_closed=True)
    V = P.visual
    hl = L / 2
    white = (0.95, 0.95, 0.94)
    if ada:
        # iteration 4 (fidelity-2, #74 f3_wellness_room_sink): the wall-hung ADA counter: a 0.17 m white apron under
        # the top and open knee space below (the wall shows through), a small white pipe shroud under the bowl
        V.box(-hl, D - 0.05, h - 0.21, hl, D - 0.01, h - 0.04, "int_drywall", faces="+y-y+x-x-z", tint=white)
        V.box(-hl, 0.0, h - 0.21, -hl + 0.03, D - 0.05, h - 0.04, "int_drywall", faces="+x-x-z", tint=white)
        V.box(hl - 0.03, 0.0, h - 0.21, hl, D - 0.05, h - 0.04, "int_drywall", faces="+x-x-z", tint=white)
        V.box(-0.16, 0.0, h - 0.48, 0.16, 0.20, h - 0.21, "int_drywall", faces="+y+x-x-z", tint=(0.90, 0.90, 0.89))
    else:
        V.box(-hl + 0.02, 0.0, 0.0, hl - 0.02, D - 0.09, 0.10, "int_plastic", faces="+y+x-x", tint=(0.32, 0.32, 0.34))
        V.box(-hl + 0.02, 0.0, 0.10, hl - 0.02, D - 0.03, h - 0.04, "int_drywall", faces="+y+x-x-z", tint=white)
        nd = max(2, int(round(L / 0.5)))
        for k in range(1, nd):
            x = -hl + 0.02 + (L - 0.04) * k / nd
            V.poly(K.front_quad(x - 0.005, x + 0.005, D - 0.028, 0.14, h - 0.08), "int_plastic",
                   tint=(0.62, 0.62, 0.64))
        for k in range(nd):
            x = -hl + 0.02 + (L - 0.04) * (k + 0.5) / nd + (0.12 if k % 2 == 0 else -0.12)
            V.box(x - 0.012, D - 0.03, h - 0.22, x + 0.012, D - 0.01, h - 0.12, "int_metal", faces="+y+x-x+z-z")
    V.box(-hl, 0.0, h - 0.04, hl, D, h, "int_drywall", faces="+x-x+y+z-z", tint=(0.99, 0.99, 0.98))
    V.poly([(-0.24, 0.14, h + 0.006), (0.24, 0.14, h + 0.006), (0.24, 0.46, h + 0.006), (-0.24, 0.46, h + 0.006)],
           "int_metal", tint=(0.70, 0.72, 0.76))
    V.poly([(-0.20, 0.18, h + 0.008), (0.20, 0.18, h + 0.008), (0.20, 0.42, h + 0.008), (-0.20, 0.42, h + 0.008)],
           "int_metal", tint=(0.52, 0.54, 0.58))
    V.box(-0.018, 0.04, h, 0.018, 0.08, h + 0.30, "int_metal", faces="+x-x+y-y")
    V.box(-0.015, 0.04, h + 0.26, 0.015, 0.24, h + 0.30, "int_metal", faces="+x-x+y-y+z-z")
    # (#74: a dark navy paper-towel dispenser and a blue soap dispenser beside it)
    V.box(0.18, 0.0, 1.30, 0.50, 0.11, 1.72, "int_plastic", faces="+x-x+y+z-z", tint=(0.20, 0.23, 0.32))
    V.poly(K.front_quad(0.22, 0.46, 0.111, 1.33, 1.37), "int_plastic", tint=(0.10, 0.11, 0.14))
    V.box(-0.50, 0.0, 1.14, -0.36, 0.09, 1.40, "int_plastic", faces="+x-x+y+z-z", tint=(0.22, 0.42, 0.84))
    V.poly(K.front_quad(-0.46, -0.40, 0.091, 1.20, 1.26), "int_plastic", tint=(0.92, 0.94, 0.96))
    if col:
        K.col_box(P.collision, -hl, 0.0, 0.0, hl, D, h, NOCAM)
    return P


def all_props():
    return {
        "sayl_chair": sayl_chair(), "caper_stool": caper_stool(), "guest_chair": guest_chair(), "tub_chair": tub_chair(),
        "round_ottoman": round_ottoman(), "hex_ottoman": hex_ottoman(), "banquette_arc": banquette_arc(),
        "lounge_cube": lounge_cube(), "side_block": side_table_block(), "study_pod": study_pod(),
        "round_table": round_table(), "rect_table": rect_table(), "benching": benching(), "bar_table": bar_table(),
        "guitar_pick": guitar_pick_table(), "perf_carrels": perf_carrels(), "perf_carrels2": perf_carrels(double=True),
        "lab_cubicles": lab_cubicles(), "bench120": white_benching_120(), "computer_bench": computer_bench(),
        "range_unit": range_unit(4.0, 1.2, 2.3), "low_shelf": low_shelf(sign="int_ms_sign_highlights"),
        "compact": compact_shelving(), "microform": microfiche_cabinet(), "coffer": coffer(3.05),
        "ring_pendant": ring_pendant(), "wave_ribbon": wave_ribbon(), "led_strip": led_strip(6.0),
        "lantern": soffit_lantern(), "ring_sign": service_ring_sign(), "exit": exit_sign(), "wall_tv": wall_tv(),
        "projection": projection_screen(), "fish_tank": fish_tank(), "vending": vending_machine(),
        "fountains": drinking_fountain_pair(), "stanchion": stanchion(), "security_gate": security_gate(),
        "news_box": news_box(), "plant": potted_plant(), "mobile_wb": whiteboard_easel(), "easel": easel_sign(),
        "exhibit": exhibit_case(), "island": butcher_island(), "pegboard": pegboard_wall(),
        "printer_station": printer_station(), "door_leaf": door_leaf(open_deg=80), "plaque": name_plaque(1),
    }


if __name__ == "__main__":
    bad = 0
    for k, p in all_props().items():
        t = p.tris()
        mats = sorted({q.mat for q in p.visual.polys})
        unknown = [m for m in mats if not K.known_material(m)]
        iss = K.collision_issues(p.collision, base_z=0.0) if p.collision.polys else []
        print(f"{k:16s} visual {t['visual']:4d} collision {t['collision']:3d}  {'UNKNOWN ' + str(unknown) if unknown else ''}"
              f"{' COL ' + str(iss[:2]) if iss else ''}")
        bad += bool(unknown) + bool(iss)
    sys.exit(1 if bad else 0)
