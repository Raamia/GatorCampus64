"""Generate Albert the Alligator (the hub's NPC host) as a coopdx DynOS actor, without Blender.

The friend models come from Blender + Fast64 (tools/blender/), which needs a Blender install. Albert is an NPC
prop, not a player model, so a low-poly mesh built from primitives is enough: this script writes Fast64-style C
that DynOS compiles at launch into actors/albert_geo.bin (smlua_model_util_get_id("albert_geo")).

  mods/sgl64/actors/albert/model.inc.c   lights, materials (the lit solid-colour Fast64 pattern of the friend
                                          models), vertices, display lists
  mods/sgl64/actors/albert/geo.inc.c     albert_geo: shadow -> a skeleton of GEO_ANIMATED_PART joints (JOINTS:
                                          root, hips, torso, head, jaw, arms, tail, legs), animated by the
                                          keyframes of mods/sgl64/sgl_albert.lua
  mods/sgl64/actors/albert/geo_header.h  extern declarations

Units are game units (1 = 1 cm), +Y up, he faces +Z (an object's yaw 0). About 1.9 m tall.
Usage: python3 -I tools/actors/make_albert.py [--out DIR]
"""
import argparse
import math
import os

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(ROOT, "mods", "sgl64", "actors", "albert")
NAME = "albert"
MAX_LOAD = 32   # vertices per gsSPVertex load (F3DEX2 vertex buffer)

# Florida Gators palette + gator greens
COLORS = {
    "skin": (58, 140, 52),      # gator green
    "skin_dark": (34, 96, 36),  # scutes, brow, nostrils' rim
    "belly": (196, 214, 120),   # lower jaw / throat, pale yellow-green
    "jersey": (250, 70, 22),    # UF orange
    "blue": (0, 33, 165),       # UF blue: collar, sleeves, letters, shorts
    "white": (245, 245, 240),   # eyes, teeth, claws, shoe soles
    "black": (18, 18, 22),      # pupils, nostrils
    "mouth": (196, 60, 70),     # inside of the mouth
    "shoe": (250, 110, 30),     # orange sneakers
}


class Mesh:
    """Triangles grouped by material; each triangle carries its own face normal (flat shading)."""

    def __init__(self):
        self.tris = {}   # material -> [((v0, v1, v2), normal)]

    def tri(self, mat, a, b, c, inside=None):
        n = cross(sub(b, a), sub(c, a))
        if inside is not None:   # wind so the normal points away from the primitive's centre
            face = scale(add(add(a, b), c), 1 / 3)
            if dot(n, sub(face, inside)) < 0:
                b, c = c, b
                n = scale(n, -1)
        ln = math.sqrt(dot(n, n))
        if ln < 1e-9:
            return
        self.tris.setdefault(mat, []).append(((a, b, c), scale(n, 1 / ln)))

    def quad(self, mat, a, b, c, d, inside):
        self.tri(mat, a, b, c, inside)
        self.tri(mat, a, c, d, inside)

    def hexa(self, mat, p, center=None):
        """8 corners: p[0..3] bottom ring, p[4..7] top ring, same order (a deformed box)."""
        center = center or scale(sum_v(p), 1 / 8)
        for i in range(4):
            j = (i + 1) % 4
            self.quad(mat, p[i], p[j], p[j + 4], p[i + 4], center)
        self.quad(mat, p[0], p[1], p[2], p[3], center)
        self.quad(mat, p[4], p[5], p[6], p[7], center)

    def box(self, mat, x0, x1, y0, y1, z0, z1, xform=None):
        p = [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1),
             (x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)]
        if xform:
            p = [xform(v) for v in p]
        self.hexa(mat, p)

    def taper(self, mat, y0, y1, bot, top, xform=None):
        """A box tapered along Y: bot/top = (x0, x1, z0, z1) at y0 / y1."""
        (a0, a1, b0, b1), (c0, c1, d0, d1) = bot, top
        p = [(a0, y0, b0), (a1, y0, b0), (a1, y0, b1), (a0, y0, b1),
             (c0, y1, d0), (c1, y1, d0), (c1, y1, d1), (c0, y1, d1)]
        if xform:
            p = [xform(v) for v in p]
        self.hexa(mat, p)

    def zbar(self, mat, z0, z1, near, far, xform=None):
        """A box tapered along Z: near/far = (x0, x1, y0, y1) at z0 / z1."""
        (a0, a1, b0, b1), (c0, c1, d0, d1) = near, far
        p = [(a0, b0, z0), (a1, b0, z0), (c1, d0, z1), (c0, d0, z1),
             (a0, b1, z0), (a1, b1, z0), (c1, d1, z1), (c0, d1, z1)]
        if xform:
            p = [xform(v) for v in p]
        self.hexa(mat, p)

    def ball(self, mat, c, r, seg=8, rings=6, xform=None):
        """A low-poly UV sphere (r = (rx, ry, rz))."""
        pts = {}
        for i in range(rings + 1):
            th = math.pi * i / rings
            for j in range(seg):
                ph = 2 * math.pi * j / seg
                v = (c[0] + r[0] * math.sin(th) * math.cos(ph), c[1] + r[1] * math.cos(th),
                     c[2] + r[2] * math.sin(th) * math.sin(ph))
                pts[i, j] = xform(v) if xform else v
        center = xform(c) if xform else c
        for i in range(rings):
            for j in range(seg):
                k = (j + 1) % seg
                a, b, cc, d = pts[i, j], pts[i, k], pts[i + 1, k], pts[i + 1, j]
                if i == 0:
                    self.tri(mat, a, cc, d, center)
                elif i == rings - 1:
                    self.tri(mat, a, b, cc, center)
                else:
                    self.quad(mat, a, b, cc, d, center)

    def pyramid(self, mat, base, apex):
        """base = 4 corners (a quad), apex = tip."""
        center = scale(add(scale(sum_v(base), 0.25), apex), 0.5)
        for i in range(4):
            self.tri(mat, base[i], base[(i + 1) % 4], apex, center)
        self.quad(mat, base[0], base[1], base[2], base[3], center)


def add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def scale(a, k): return (a[0] * k, a[1] * k, a[2] * k)
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def sum_v(ps):
    s = (0, 0, 0)
    for p in ps:
        s = add(s, p)
    return s


def rot_x(deg, pivot):
    """Rotate about the X axis through pivot (positive = the front tips down)."""
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)

    def f(v):
        y, z = v[1] - pivot[1], v[2] - pivot[2]
        return (v[0], pivot[1] + y * ca - z * sa, pivot[2] + y * sa + z * ca)
    return f


def rot_z(deg, pivot):
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)

    def f(v):
        x, y = v[0] - pivot[0], v[1] - pivot[1]
        return (pivot[0] + x * ca - y * sa, pivot[1] + x * sa + y * ca, v[2])
    return f


# --------------------------------------------------------------------------------------------
# Albert
# --------------------------------------------------------------------------------------------
HEAD_Y = 136          # bottom of the skull


# The skeleton: GEO_ANIMATED_PART joints in depth-first order (= the order of the animation channels;
# mods/sgl64/sgl_albert.lua ALBERT_JOINTS must list the same names). pivot = the joint's world position at rest;
# every part's vertices are written relative to its own pivot.
JOINTS = [
    # name      parent   pivot (x, y, z)
    ("root",   None,    (0, 0, 0)),
    ("hips",   "root",  (0, 46, 0)),
    ("torso",  "hips",  (0, 66, 0)),
    ("head",   "torso", (0, 130, 0)),
    ("jaw",    "head",  (0, HEAD_Y + 5, 4)),
    ("arm_l",  "torso", (34, 118, 0)),     # his left = +X (he faces +Z)
    ("arm_r",  "torso", (-34, 118, 0)),
    ("tail",   "hips",  (0, 50, -14)),
    ("leg_l",  "root",  (17, 46, 0)),
    ("leg_r",  "root",  (-17, 46, 0)),
]
PIVOT = {name: pivot for name, _, pivot in JOINTS}


def build_body(P):
    # sneakers (orange, white soles) and green legs
    for s, leg in ((1, "leg_l"), (-1, "leg_r")):
        m = P[leg]
        x = 17 * s
        m.box("white", x - 11, x + 11, 0, 4, -10, 22)
        m.box("shoe", x - 11, x + 11, 4, 13, -10, 22)
        m.box("skin", x - 8, x + 8, 13, 50, -7, 9)
    # blue shorts
    P["hips"].taper("blue", 42, 68, (-31, 31, -18, 18), (-29, 29, -18, 18))
    m = P["torso"]
    # orange jersey: a torso that widens to the shoulders, with a round tummy in front
    m.taper("jersey", 64, 126, (-30, 30, -19, 19), (-36, 36, -20, 20))
    m.ball("jersey", (0, 84, 6), (25, 18, 15))
    # blue collar and sleeve caps
    m.taper("blue", 122, 130, (-24, 24, -15, 15), (-18, 18, -12, 12))
    for s in (-1, 1):
        m.box("blue", 34 * s - 9, 34 * s + 9, 106, 126, -13, 13)
    # "UF" in blue block letters on the chest (z just in front of the jersey)
    z0, z1 = 20.5, 23
    for x0, x1, y0, y1 in ((-19, -15, 102, 121), (-9, -5, 102, 121), (-19, -5, 102, 106),   # U
                           (3, 7, 102, 121), (3, 18, 117, 121), (3, 14, 110, 114)):         # F
        m.box("blue", x0, x1, y0, y1, z0, z1)
    # neck
    m.taper("skin", 126, HEAD_Y + 4, (-16, 16, -13, 11), (-17, 17, -14, 12))
    # green arms hanging a little outward, white claws
    for s, arm in ((1, "arm_l"), (-1, "arm_r")):
        m = P[arm]
        tilt = rot_z(10 * s, (34 * s, 118, 0))
        m.box("skin", 34 * s - 7, 34 * s + 7, 78, 112, -7, 7, tilt)
        hand = tilt((34 * s, 72, 0))
        m.ball("skin", hand, (9, 8, 9))
        for k in (-1, 0, 1):
            cx, cz = hand[0] + 3 * k, hand[2] + 6
            m.pyramid("white", [(cx - 1.5, hand[1] - 4, cz), (cx + 1.5, hand[1] - 4, cz),
                                (cx + 1.5, hand[1] - 4, cz + 3), (cx - 1.5, hand[1] - 4, cz + 3)],
                      (cx, hand[1] - 10, cz + 2))
    # tail: a tapered green bar from the shorts down to the ground behind him, with dark scutes
    m = P["tail"]
    m.zbar("skin", -10, -90, (-14, 14, 38, 60), (-3, 3, 4, 12))
    for i in range(5):
        z = -24 - 13 * i
        y = 60 + (12 - 60) * ((-14 - z) / 76)   # the tail's top edge at z
        w = 9 - i * 1.4
        m.pyramid("skin_dark", [(-w / 2, y - 1, z - 4), (w / 2, y - 1, z - 4), (w / 2, y - 1, z + 4), (-w / 2, y - 1, z + 4)],
                  (0, y + 7 - i, z))


def build_head(m):
    y0 = HEAD_Y
    # skull: a wide rounded block
    m.taper("skin", y0, y0 + 30, (-25, 25, -20, 16), (-21, 21, -16, 12))
    m.ball("skin", (0, y0 + 26, -2), (21, 10, 16))
    # upper snout: long and flat, tapering to the nose, from the skull forward to z = 80
    m.zbar("skin", 10, 80, (-22, 22, y0 + 7, y0 + 25), (-15, 15, y0 + 9, y0 + 19))
    m.ball("skin", (0, y0 + 14, 79), (15, 6, 7))          # rounded nose tip
    # the red roof of the mouth (inside the lower jaw while it's closed, shows when he talks)
    m.box("mouth", -15, 15, y0 + 6.2, y0 + 7, 10, 70)
    # nostrils on top of the nose
    for s in (-1, 1):
        m.box("black", 6 * s - 2.5, 6 * s + 2.5, y0 + 19.6, y0 + 21.2, 70, 75)
    # brow ridges and big cartoon eyes on top of the head
    for s in (-1, 1):
        ex = 12 * s
        m.box("skin_dark", ex - 10, ex + 10, y0 + 33, y0 + 38, 2, 14)
        m.ball("white", (ex, y0 + 38, 11), (9, 10, 8))
        m.ball("black", (ex + 1.5 * s, y0 + 38, 18), (4, 5, 2.5))
    # dark scutes down the back of the head
    for i, z in enumerate((-8, -16)):
        m.pyramid("skin_dark", [(-5, y0 + 30 - 6 * i, z - 3), (5, y0 + 30 - 6 * i, z - 3),
                                (5, y0 + 30 - 6 * i, z + 3), (-5, y0 + 30 - 6 * i, z + 3)], (0, y0 + 37 - 6 * i, z))
    # upper teeth along both sides of the upper jaw (always visible, a classic grin)
    for s in (-1, 1):
        for k in range(6):
            z = 22 + 9 * k
            x = (20 - 6 * (z - 10) / 70) * s
            m.pyramid("white", [(x - 1.6, y0 + 8, z - 2), (x + 1.6, y0 + 8, z - 2), (x + 1.6, y0 + 8, z + 2),
                                (x - 1.6, y0 + 8, z + 2)], (x, y0 + 2.5, z))


def build_jaw(m):
    """The lower jaw (pale belly green) + the mouth's red inside; the jaw joint opens it."""
    y0 = HEAD_Y
    m.zbar("belly", 4, 76, (-20, 20, y0 - 2, y0 + 7), (-13, 13, y0 + 2, y0 + 8.5))
    m.box("mouth", -15, 15, y0 + 7, y0 + 8, 10, 70)
    # lower teeth
    for s in (-1, 1):
        for k in range(5):
            z = 26 + 10 * k
            x = (17 - 5 * (z - 4) / 72) * s
            m.pyramid("white", [(x - 1.5, y0 + 7, z - 2), (x + 1.5, y0 + 7, z - 2), (x + 1.5, y0 + 7, z + 2),
                                (x - 1.5, y0 + 7, z + 2)], (x, y0 + 12, z))


def build_parts():
    """-> {joint name: Mesh in world coordinates at rest}."""
    P = {name: Mesh() for name, _, _ in JOINTS}
    build_body(P)
    build_head(P["head"])
    build_jaw(P["jaw"])
    return P


# --------------------------------------------------------------------------------------------
# C output (Fast64 conventions, as in mods/sgl64/actors/<friend>/model.inc.c)
# --------------------------------------------------------------------------------------------
def b8(v):
    return "0x%02X" % (int(round(v)) & 0xFF)


def normal_bytes(n):
    return [max(-127, min(127, int(round(c * 127)))) for c in n]


def emit_mesh(mesh, part, out_vtx, out_dl, used_mats, pivot=(0, 0, 0)):
    """Vertex arrays + triangle lists of one part (vertices relative to pivot); returns its display list name."""
    top = "%s_%s_mesh_layer_1" % (NAME, part)
    body = []
    for mat in sorted(mesh.tris):
        tris = mesh.tris[mat]
        used_mats.add(mat)
        body.append("\tgsSPDisplayList(mat_%s_%s)," % (NAME, mat))
        for c0 in range(0, len(tris), MAX_LOAD // 3):
            chunk = tris[c0:c0 + MAX_LOAD // 3]
            vname = "%s_%s_vtx_%d" % (top, mat, c0 // (MAX_LOAD // 3))
            tname = "%s_%s_tri_%d" % (top, mat, c0 // (MAX_LOAD // 3))
            lines = ["Vtx %s[%d] = {" % (vname, 3 * len(chunk))]
            for (a, b, c), n in chunk:
                nb = normal_bytes(n)
                for v in (a, b, c):
                    lines.append("\t{{{%d, %d, %d}, 0, {-16, -16}, {%s, %s, %s, 0xFF}}}," % (
                        int(round(v[0] - pivot[0])), int(round(v[1] - pivot[1])), int(round(v[2] - pivot[2])),
                        b8(nb[0]), b8(nb[1]), b8(nb[2])))
            lines.append("};\n")
            out_vtx.append("\n".join(lines))
            tl = ["Gfx %s[] = {" % tname, "\tgsSPVertex(%s + 0, %d, 0)," % (vname, 3 * len(chunk))]
            for i in range(len(chunk)):
                tl.append("\tgsSP1Triangle(%d, %d, %d, 0)," % (3 * i, 3 * i + 1, 3 * i + 2))
            tl.append("\tgsSPEndDisplayList(),\n};\n")
            out_dl.append("\n".join(tl))
            body.append("\tgsSPDisplayList(%s)," % tname)
        body.append("\tgsSPDisplayList(mat_revert_%s_%s)," % (NAME, mat))
    body.append("\tgsSPEndDisplayList(),")
    out_dl.append("Gfx %s[] = {\n%s\n};\n" % (top, "\n".join(body)))
    return top


def materials(used):
    out = []
    for mat in sorted(used):
        r, g, b = COLORS[mat]
        out.append("Lights1 %s_%s_lights = gdSPDefLights1(\n\t%s, %s, %s,\n\t%s, %s, %s, 0x28, 0x28, 0x28);\n" % (
            NAME, mat, b8(r * 0.5), b8(g * 0.5), b8(b * 0.5), b8(r), b8(g), b8(b)))
    for mat in sorted(used):
        out.append("Gfx mat_%s_%s[] = {\n"
                   "\tgsSPSetLights1(%s_%s_lights),\n"
                   "\tgsDPPipeSync(),\n"
                   "\tgsDPSetCombineLERP(0, 0, 0, SHADE, 0, 0, 0, ENVIRONMENT, 0, 0, 0, SHADE, 0, 0, 0, ENVIRONMENT),\n"
                   "\tgsDPSetAlphaDither(G_AD_NOISE),\n"
                   "\tgsSPTexture(65535, 65535, 0, 0, 1),\n"
                   "\tgsSPEndDisplayList(),\n};\n" % (NAME, mat, NAME, mat))
        out.append("Gfx mat_revert_%s_%s[] = {\n"
                   "\tgsDPPipeSync(),\n"
                   "\tgsDPSetAlphaDither(G_AD_DISABLE),\n"
                   "\tgsSPEndDisplayList(),\n};\n" % (NAME, mat))
    return out


def geo_layout(tops):
    """albert_geo: the joints as nested GEO_ANIMATED_PARTs (translation = offset from the parent's pivot)."""
    children = {}
    for name, parent, _ in JOINTS:
        children.setdefault(parent, []).append(name)
    lines = []

    def part(name, depth):
        parent = next(p for n, p, _ in JOINTS if n == name)
        px, py, pz = PIVOT[name]
        ox, oy, oz = (0, 0, 0) if parent is None else PIVOT[parent]
        tab = "\t" * depth
        lines.append("%sGEO_ANIMATED_PART(LAYER_OPAQUE, %d, %d, %d, %s)," % (
            tab, px - ox, py - oy, pz - oz, tops.get(name) or "NULL"))
        kids = children.get(name, [])
        if kids:
            lines.append(tab + "GEO_OPEN_NODE(),")
            for k in kids:
                part(k, depth + 1)
            lines.append(tab + "GEO_CLOSE_NODE(),")
    part("root", 3)
    return ("// GENERATED by tools/actors/make_albert.py. Do not edit; edit the script and re-run it.\n\n"
            "const GeoLayout %s_geo[] = {\n"
            "\tGEO_NODE_START(),\n"
            "\tGEO_OPEN_NODE(),\n"
            "\t\tGEO_SHADOW(0, 150, 90),\n"
            "\t\tGEO_OPEN_NODE(),\n"
            "%s\n"
            "\t\tGEO_CLOSE_NODE(),\n"
            "\tGEO_CLOSE_NODE(),\n"
            "\tGEO_END(),\n"
            "};\n") % (NAME, "\n".join(lines))


def build():
    """-> (model.inc.c text, geo.inc.c text, geo_header.h text, triangle count)."""
    parts = build_parts()
    vtx, dls, used = [], [], set()
    tops = {name: emit_mesh(parts[name], name, vtx, dls, used, PIVOT[name])
            for name, _, _ in JOINTS if parts[name].tris}
    model = "// GENERATED by tools/actors/make_albert.py. Do not edit; edit the script and re-run it.\n\n"
    model += "\n".join(materials(used)) + "\n" + "\n".join(vtx) + "\n" + "\n".join(dls)
    geo = geo_layout(tops)
    header = ["extern const GeoLayout %s_geo[];" % NAME]
    for mat in sorted(used):
        header += ["extern Lights1 %s_%s_lights;" % (NAME, mat), "extern Gfx mat_%s_%s[];" % (NAME, mat),
                   "extern Gfx mat_revert_%s_%s[];" % (NAME, mat)]
    for chunk in vtx:
        header.append("extern " + chunk.split(" = ")[0] + ";")
    for d in dls:
        header.append("extern " + d.split(" = ")[0] + ";")
    ntris = sum(len(t) for mesh in parts.values() for t in mesh.tris.values())
    return model, geo, "\n".join(header) + "\n", ntris


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=OUT, help="actor folder (default mods/sgl64/actors/albert)")
    args = ap.parse_args(argv)
    model, geo, header, ntris = build()
    os.makedirs(args.out, exist_ok=True)
    for name, text in (("model.inc.c", model), ("geo.inc.c", geo), ("geo_header.h", header)):
        with open(os.path.join(args.out, name), "w") as f:
            f.write(text)
    print("make_albert: %d triangles -> %s" % (ntris, os.path.relpath(args.out, ROOT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
