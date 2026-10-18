"""Generate the mini bull (a USF Bulls joke enemy) that replaces every Goomba, as a coopdx DynOS actor, without Blender.

The actor is named goomba_geo, so DynOS swaps it in for the vanilla Goomba model everywhere while the vanilla
Goomba behaviour stays: it wanders, charges Mario, gets squashed flat when you stomp it (or knocked out by a punch
or kick) and drops its coin. To keep the Goomba's own walk animation working, the geo copies the vanilla Goomba
skeleton exactly (actors/goomba/geo.inc.c in sm64coopdx: GEO_SCALE 0.25, then 7 animated parts: root, body, the
eyes switch (open / blinking, geo_switch_anim_state), and the two feet with their pivots).

  hooves     built in the feet's own local space, inside the vanilla feet's box, so they step like Goomba feet
  body, eyes designed in world space (Y up, facing +Z, feet on y = 0, Goomba scale 1: in game normal Goombas are
             x1.5) and mapped into their joints with the joint transforms at frame 0 of the Goomba walk (REST below,
             read once from the US ROM; the walk only sways the body a few degrees from there)

Look: a round dark-brown bull with USF gold horns, a green-and-gold headband, a tan muzzle with a gold nose ring,
angry eyebrows, black hooves and a tail tuft.
Writes mods/sgl64/actors/goomba/{model.inc.c, geo.inc.c, geo_header.h}.
Usage: python3 -I tools/actors/make_minibull.py [--out DIR]
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_gators as G  # noqa: E402  (Mesh, primitives, C output)

ROOT = G.ROOT
OUT = os.path.join(ROOT, "mods", "sgl64", "actors", "goomba")
NAME = "minibull"           # prefix of every display list / material (the geo itself is goomba_geo)

G.COLORS.update({
    "bull": (74, 46, 30),        # dark brown hide
    "bull_dark": (40, 26, 18),   # ears, tail tuft, eyebrows
    "muzzle": (205, 160, 120),   # tan snout
    "usf_green": (0, 103, 71),   # USF green
    "usf_gold": (207, 196, 147), # USF gold: horns, nose ring, headband trim
    "hoof": (25, 22, 22),
    "nostril": (60, 30, 30),
    "eye_white": (250, 250, 245),
    "pupil": (15, 15, 20),
})

# The vanilla Goomba skeleton: (name, parent, translation) in the order of the animation channels, and the walk's
# frame 0 (root translation; rotation x, y, z of each part, s16 angle units).
PARTS = [("root", None, (0, 0, 0)), ("body", "root", (0, 0, 0)), ("eyes", "body", (48, 0, 0)),
         ("foot_l_pivot", "body", (-60, -16, 45)), ("foot_l", "foot_l_pivot", (0, 0, 0)),
         ("foot_r_pivot", "body", (-60, -16, -45)), ("foot_r", "foot_r_pivot", (0, 0, 0))]
REST_TRANSLATION = (0, 90, 0)
REST = [(0, 16383, 0), (1564, -938, 16383), (-1773, 0, 0), (0, 0, -16383), (0, 0, -31619), (0, 0, -16383),
        (-32767, 29950, -5216)]
GEO_SCALE = 0.25


def rot_mat(rx, ry, rz, t):
    """The engine's mtxf_rotate_xyz_and_translate (row vectors), angles in s16 units."""
    r = lambda a: a * 2 * math.pi / 65536
    sx, cx, sy, cy, sz, cz = math.sin(r(rx)), math.cos(r(rx)), math.sin(r(ry)), math.cos(r(ry)), math.sin(r(rz)), math.cos(r(rz))
    return [[cy * cz, cy * sz, -sy, 0], [sx * sy * cz - cx * sz, sx * sy * sz + cx * cz, sx * cy, 0],
            [cx * sy * cz + sx * sz, cx * sy * sz - sx * cz, cx * cy, 0], [t[0], t[1], t[2], 1]]


def mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def rest_world():
    """Each part's world matrix at the walk's frame 0 (object scale 1)."""
    out = {}
    base = [[GEO_SCALE, 0, 0, 0], [0, GEO_SCALE, 0, 0], [0, 0, GEO_SCALE, 0], [0, 0, 0, 1]]
    for i, (name, parent, t) in enumerate(PARTS):
        if i == 0:
            t = tuple(a + b for a, b in zip(t, REST_TRANSLATION))
        out[name] = mul(rot_mat(*REST[i], t), out[parent] if parent else base)
    return out


def inverse(m):
    """Inverse of a uniformly scaled rotation + translation."""
    R = [row[:3] for row in m[:3]]
    t = m[3][:3]
    s2 = sum(x * x for x in R[0])
    Ri = [[R[j][i] / s2 for j in range(3)] for i in range(3)]
    ti = [-sum(t[k] * Ri[k][j] for k in range(3)) for j in range(3)]
    return [Ri[0] + [0], Ri[1] + [0], Ri[2] + [0], ti + [1]]


def apply(v, m):
    return tuple(v[0] * m[0][j] + v[1] * m[1][j] + v[2] * m[2][j] + m[3][j] for j in range(3))


def to_local(mesh, world_to_local):
    """A copy of a world-space mesh in a joint's local space (positions and normals)."""
    out = G.Mesh()
    rot = [row[:3] for row in world_to_local[:3]]
    for mat, tris in mesh.tris.items():
        for (a, b, c), n in tris:
            nn = tuple(sum(n[k] * rot[k][j] for k in range(3)) for j in range(3))
            ln = math.sqrt(sum(x * x for x in nn)) or 1
            out.tris.setdefault(mat, []).append(
                ((apply(a, world_to_local), apply(b, world_to_local), apply(c, world_to_local)),
                 tuple(x / ln for x in nn)))
    return out


# --------------------------------------------------------------------------------------------
# the mini bull, world space at Goomba scale 1 (about 0.55 m tall; normal Goombas are drawn x1.5)
# --------------------------------------------------------------------------------------------
def build_body(m):
    # round body/head blob with a slightly flat bottom
    m.ball("bull", (0, 30, 0), (25, 21, 23), seg=10, rings=7)
    m.ball("bull", (0, 18, -2), (21, 9, 19), seg=10, rings=5)
    # tan muzzle out front, nostrils, gold nose ring
    m.ball("muzzle", (0, 24, 18), (15, 10, 9), seg=10, rings=6)
    for s in (-1, 1):
        m.ball("nostril", (5 * s, 26, 26.5), (2.4, 2.4, 1.2), seg=6, rings=4)
    m.box("usf_gold", -5, 5, 15.5, 17.5, 25, 27)
    m.box("usf_gold", -5, -3.5, 15.5, 20, 25, 27)
    m.box("usf_gold", 3.5, 5, 15.5, 20, 25, 27)
    # USF green headband with gold trim across the forehead
    m.taper("usf_green", 40, 45, (-24, 24, -18, 16), (-22, 22, -16, 14))
    m.taper("usf_gold", 45, 46.5, (-22, 22, -16, 14), (-21.5, 21.5, -15.5, 13.5))
    # gold horns sweeping out and up, ears below them
    for s in (-1, 1):
        base = [(16 * s, 42, -4), (24 * s, 42, -4), (24 * s, 42, 6), (16 * s, 42, 6)]
        mid = (34 * s, 50, 1)
        m.pyramid("usf_gold", base, mid)
        m.pyramid("usf_gold", [(30 * s, 47, -2), (35 * s, 47, -2), (35 * s, 47, 4), (30 * s, 47, 4)], (38 * s, 60, 2))
        m.ball("bull_dark", (25 * s, 34, -2), (6, 3, 4), seg=6, rings=4)
        # angry eyebrows slanting down toward the snout
        m.box("bull_dark", 4 * s - 3, 4 * s + 3, 37, 39.5, 18, 21, G.rot_z(18 * s, (9 * s, 38, 0)))
        m.box("bull_dark", 9 * s - 5, 9 * s + 5, 37.5, 40, 17, 20, G.rot_z(-22 * s, (9 * s, 38, 0)))
    # tail tuft at the back
    m.box("bull", -1.5, 1.5, 22, 30, -26, -22, G.rot_x(-30, (0, 26, -24)))
    m.ball("bull_dark", (0, 19, -28), (3, 4, 3), seg=6, rings=4)


def build_eyes(m, blink):
    """Two angry eyes on the face, above the muzzle (blink: brown lids closed over them)."""
    for s in (-1, 1):
        c = (9 * s, 33, 18.5)
        if blink:
            m.ball("bull", c, (5.5, 1.6, 2.5), seg=8, rings=4)
            m.box("bull_dark", c[0] - 5, c[0] + 5, c[1] - 0.6, c[1] + 0.6, c[2] + 1.8, c[2] + 2.6)
        else:
            m.ball("eye_white", c, (5.5, 6.5, 2.8), seg=8, rings=5)
            m.ball("pupil", (c[0] - 1.2 * s, c[1] - 0.5, c[2] + 2.4), (2.4, 3.2, 1.0), seg=6, rings=4)


def build_hoof(m):
    """A black hoof in a foot's LOCAL space (inside the vanilla Goomba foot's box: x -30..90 toward the toe,
    y -17..14, z -37..51), with a gold sole stripe."""
    m.ball("hoof", (22, -4, 7), (34, 13, 26), seg=8, rings=5)
    m.box("usf_gold", 44, 54, -10, 6, -14, 28)    # a gold band around the front of the hoof
    m.box("bull", -30, -6, -7, 7, -4, 18)         # a stubby leg stump into the body


def build_parts():
    W = rest_world()
    parts = {}
    body = G.Mesh()
    build_body(body)
    parts["body"] = to_local(body, inverse(W["body"]))
    for blink in (False, True):
        e = G.Mesh()
        build_eyes(e, blink)
        parts["eyes_blink" if blink else "eyes"] = to_local(e, inverse(W["eyes"]))
    for foot in ("foot_l", "foot_r"):
        h = G.Mesh()
        build_hoof(h)
        parts[foot] = h
    return parts


def geo_layout(tops):
    t = lambda n: tops[n]
    return ("// GENERATED by tools/actors/make_minibull.py. Do not edit; edit the script and re-run it.\n"
            "// The vanilla Goomba skeleton (sm64coopdx actors/goomba/geo.inc.c) with mini bull display lists.\n\n"
            "const GeoLayout goomba_geo[] = {\n"
            "\tGEO_SHADOW(SHADOW_CIRCLE_4_VERTS, 0x96, 100),\n"
            "\tGEO_OPEN_NODE(),\n"
            "\t\tGEO_SCALE(0x00, 16384),\n"
            "\t\tGEO_OPEN_NODE(),\n"
            "\t\t\tGEO_ANIMATED_PART(LAYER_OPAQUE, 0, 0, 0, NULL),\n"
            "\t\t\tGEO_OPEN_NODE(),\n"
            "\t\t\t\tGEO_ANIMATED_PART(LAYER_OPAQUE, 0, 0, 0, %s),\n"
            "\t\t\t\tGEO_OPEN_NODE(),\n"
            "\t\t\t\t\tGEO_SWITCH_CASE(2, geo_switch_anim_state),\n"
            "\t\t\t\t\tGEO_OPEN_NODE(),\n"
            "\t\t\t\t\t\tGEO_ANIMATED_PART(LAYER_OPAQUE, 48, 0, 0, %s),\n"
            "\t\t\t\t\t\tGEO_ANIMATED_PART(LAYER_OPAQUE, 48, 0, 0, %s),\n"
            "\t\t\t\t\tGEO_CLOSE_NODE(),\n"
            "\t\t\t\t\tGEO_ANIMATED_PART(LAYER_OPAQUE, -60, -16, 45, NULL),\n"
            "\t\t\t\t\tGEO_OPEN_NODE(),\n"
            "\t\t\t\t\t\tGEO_ANIMATED_PART(LAYER_OPAQUE, 0, 0, 0, %s),\n"
            "\t\t\t\t\tGEO_CLOSE_NODE(),\n"
            "\t\t\t\t\tGEO_ANIMATED_PART(LAYER_OPAQUE, -60, -16, -45, NULL),\n"
            "\t\t\t\t\tGEO_OPEN_NODE(),\n"
            "\t\t\t\t\t\tGEO_ANIMATED_PART(LAYER_OPAQUE, 0, 0, 0, %s),\n"
            "\t\t\t\t\tGEO_CLOSE_NODE(),\n"
            "\t\t\t\tGEO_CLOSE_NODE(),\n"
            "\t\t\tGEO_CLOSE_NODE(),\n"
            "\t\tGEO_CLOSE_NODE(),\n"
            "\tGEO_CLOSE_NODE(),\n"
            "\tGEO_END(),\n"
            "};\n") % (t("body"), t("eyes"), t("eyes_blink"), t("foot_l"), t("foot_r"))


def build():
    """-> (model.inc.c, geo.inc.c, geo_header.h, triangle count)."""
    parts = build_parts()
    vtx, dls, used = [], [], set()
    tops = {name: G.emit_mesh(NAME, mesh, name, vtx, dls, used) for name, mesh in parts.items()}
    model = "// GENERATED by tools/actors/make_minibull.py. Do not edit; edit the script and re-run it.\n\n"
    model += "\n".join(G.materials(NAME, used)) + "\n" + "\n".join(vtx) + "\n" + "\n".join(dls)
    header = ["extern const GeoLayout goomba_geo[];"]
    for mat in sorted(used):
        header += ["extern Lights1 %s_%s_lights;" % (NAME, mat), "extern Gfx mat_%s_%s[];" % (NAME, mat),
                   "extern Gfx mat_revert_%s_%s[];" % (NAME, mat)]
    header += ["extern " + chunk.split(" = ")[0] + ";" for chunk in vtx + dls]
    ntris = sum(len(t) for mesh in parts.values() for t in mesh.tris.values())
    return model, geo_layout(tops), "\n".join(header) + "\n", ntris


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=OUT, help="actor folder (default mods/sgl64/actors/goomba)")
    args = ap.parse_args(argv)
    model, geo, header, ntris = build()
    os.makedirs(args.out, exist_ok=True)
    for fname, text in (("model.inc.c", model), ("geo.inc.c", geo), ("geo_header.h", header)):
        with open(os.path.join(args.out, fname), "w") as f:
            f.write(text)
    print("make_minibull: %d triangles -> %s (goomba_geo)" % (ntris, os.path.relpath(args.out, ROOT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
