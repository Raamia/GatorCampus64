"""Generate the rival-school mascots that replace the Goombas, as coopdx DynOS actors, without Blender.

UF's rivals sneak around campus as joke enemies: USF Bulls and FSU Seminoles replace the Goombas, and UCF Knight
ghosts replace the Boos of Library West. The bull is named goomba_geo, so DynOS swaps it in for every Goomba by
default; the Seminole (rival_fsu_geo) is swapped onto individual Goombas by mods/sgl64/sgl_rivals.lua, and the
Knight ghost (knight_ghost_geo, no skeleton: the Boo's geo with geo_update_layer_transparency, so it fades like a
Boo) is used by the Library West missions in place of the Boo model. The vanilla Goomba behaviour stays for all of them: they wander, charge Mario, get
squashed flat when you stomp them (or knocked out by a punch or kick) and drop a coin. To keep the Goomba's own
walk animation working, every geo copies the vanilla Goomba skeleton exactly (actors/goomba/geo.inc.c in sm64coopdx: GEO_SCALE 0.25, then 7 animated parts: root, body, the
eyes switch (open / blinking, geo_switch_anim_state), and the two feet with their pivots).

  hooves     built in the feet's own local space, inside the vanilla feet's box, so they step like Goomba feet
  body, eyes designed in world space (Y up, facing +Z, feet on y = 0, Goomba scale 1: in game normal Goombas are
             x1.5) and mapped into their joints with the joint transforms at frame 0 of the Goomba walk (REST below,
             read once from the US ROM; the walk only sways the body a few degrees from there)

Every rival shares the round Goomba-sized body, angry eyes (with a blink) and feet on the Goomba feet; RIVALS gives
each its colours, feet and head features (build_<id>).
Writes mods/sgl64/actors/goomba/ (the bull), mods/sgl64/actors/rival_fsu/ and mods/sgl64/actors/knight_ghost/
({model.inc.c, geo.inc.c, geo_header.h}).
Usage: python3 -I tools/actors/make_rivals.py [--out DIR]
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_gators as G  # noqa: E402  (Mesh, primitives, C output)

ROOT = G.ROOT
OUT = os.path.join(ROOT, "mods", "sgl64", "actors")

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
    # UCF Knights
    "steel": (178, 182, 190), "steel_dark": (90, 94, 102), "ucf_black": (28, 28, 30), "ucf_gold": (255, 201, 4),
    # FSU Seminoles: garnet and gold
    "fsu_garnet": (120, 47, 64), "fsu_gold": (206, 184, 136), "fsu_dark": (70, 26, 36),
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
# the rivals, world space at Goomba scale 1 (about 0.55 m tall; normal Goombas are drawn x1.5): a round body/head
# blob centred at (0, 30, 0), the face toward +Z (z ~ 22), eyes at (+-9, 33, 18.5)
# --------------------------------------------------------------------------------------------
def blob(m, col):
    m.ball(col, (0, 30, 0), (25, 21, 23), seg=10, rings=7)
    m.ball(col, (0, 18, -2), (21, 9, 19), seg=10, rings=5)


def headband(m, band, trim, y=40):
    m.taper(band, y, y + 5, (-24, 24, -18, 16), (-22, 22, -16, 14))
    m.taper(trim, y + 5, y + 6.5, (-22, 22, -16, 14), (-21.5, 21.5, -15.5, 13.5))


def scarf(m, band, trim):
    """A band round the bottom of the body (a sweater / collar)."""
    m.taper(band, 15, 21, (-20.5, 20.5, -19, 17), (-23.5, 23.5, -21.5, 19.5))
    m.taper(trim, 21, 22.5, (-23.5, 23.5, -21.5, 19.5), (-23.8, 23.8, -21.8, 19.8))


def brows(m, col):
    for s in (-1, 1):
        m.box(col, 4 * s - 3, 4 * s + 3, 37, 39.5, 18, 21, G.rot_z(18 * s, (9 * s, 38, 0)))
        m.box(col, 9 * s - 5, 9 * s + 5, 37.5, 40, 17, 20, G.rot_z(-22 * s, (9 * s, 38, 0)))


def build_bull(m):
    """USF: a dark-brown bull, gold horns, green-and-gold headband, tan muzzle with a gold nose ring."""
    blob(m, "bull")
    m.ball("muzzle", (0, 24, 18), (15, 10, 9), seg=10, rings=6)
    for s in (-1, 1):
        m.ball("nostril", (5 * s, 26, 26.5), (2.4, 2.4, 1.2), seg=6, rings=4)
    m.box("usf_gold", -5, 5, 15.5, 17.5, 25, 27)
    m.box("usf_gold", -5, -3.5, 15.5, 20, 25, 27)
    m.box("usf_gold", 3.5, 5, 15.5, 20, 25, 27)
    headband(m, "usf_green", "usf_gold")
    for s in (-1, 1):
        m.pyramid("usf_gold", [(16 * s, 42, -4), (24 * s, 42, -4), (24 * s, 42, 6), (16 * s, 42, 6)], (34 * s, 50, 1))
        m.pyramid("usf_gold", [(30 * s, 47, -2), (35 * s, 47, -2), (35 * s, 47, 4), (30 * s, 47, 4)], (38 * s, 60, 2))
        m.ball("bull_dark", (25 * s, 34, -2), (6, 3, 4), seg=6, rings=4)
    brows(m, "bull_dark")
    m.box("bull", -1.5, 1.5, 22, 30, -26, -22, G.rot_x(-30, (0, 26, -24)))
    m.ball("bull_dark", (0, 19, -28), (3, 4, 3), seg=6, rings=4)


def build_seminole(m):
    """FSU Seminoles: a garnet rival crowned with a big gold spear-tip crest (after the spear logo), a garnet-and-gold
    headband and gold eyebrows. (On purpose no Native American imagery: the spear and the colours carry it.)"""
    blob(m, "fsu_garnet")
    headband(m, "fsu_gold", "fsu_dark", y=38)
    # the spear tip: a tall flattened diamond on top of the head, with two barbs and a garnet centre line
    tip = [(-9, 47, -3), (0, 47, -6), (9, 47, -3), (0, 47, 3)]
    m.pyramid("fsu_gold", tip, (0, 78, -1.5))
    m.pyramid("fsu_gold", [(-9, 47, -3), (0, 47, 3), (9, 47, -3), (0, 47, -6)], (0, 41, -1.5))
    for s in (-1, 1):
        m.pyramid("fsu_gold", [(4 * s, 52, -4), (4 * s, 52, 1), (4 * s, 57, 1), (4 * s, 57, -4)], (15 * s, 47, -1.5))
    m.box("fsu_dark", -1, 1, 50, 72, 1.6, 2.6)
    # a short gold spear shaft through the headband at the back
    m.box("fsu_gold", -2, 2, 30, 48, -16, -12)
    # a gold grin
    m.box("fsu_gold", -7, 7, 21, 23, 21.5, 23.5)
    for k in (-1, 1):
        m.box("fsu_gold", 7 * k - 1, 7 * k + 1, 22, 26, 21.2, 23.2)
    brows(m, "fsu_gold")


def build_knight_ghost(m):
    """UCF Knights, as a ghost (the Boos' stand-in): a floating steel helmet with a visor, glowing eyes in the slit,
    a gold plume and a wispy black tail, centred like the Boo (origin in the middle, facing +Z, ~1.6 m wide)."""
    m.ball("steel", (0, 8, 0), (62, 54, 58), seg=12, rings=8)
    m.taper("steel", -46, -6, (-46, 46, 30, 52), (-54, 54, 34, 58))           # face plate
    m.box("ucf_black", -48, 48, 4, 20, 50, 60)                               # the visor slit
    for s in (-1, 1):
        m.ball("eye_white", (20 * s, 12, 61), (11, 6, 2), seg=8, rings=4)      # glowing eyes in the slit
        m.ball("pupil", (18 * s, 11.5, 62.8), (4, 4.5, 1), seg=6, rings=4)
    for k in range(-3, 4):                                                   # breathing holes
        m.box("ucf_black", 10 * k - 2, 10 * k + 2, -36, -14, 54, 58)
    m.box("ucf_gold", -4, 4, 20, 64, 46, 56)                                 # centre ridge
    m.taper("ucf_gold", -50, -44, (-50, 50, -46, 40), (-48, 48, -44, 38))    # gold rim
    for i in range(6):                                                       # plume sweeping back
        z, y = 6 - 18 * i, 66 + 10 * i - 2.4 * i * i
        m.ball("ucf_gold", (0, y, z), (10 - i, 13, 13), seg=8, rings=4)
    # the ghostly tail curling down and back, and two little wisp arms
    m.zbar("ucf_black", -30, -70, (-34, 34, -60, -20), (-14, 14, -96, -70))
    m.zbar("ucf_black", -70, -100, (-14, 14, -96, -70), (-3, 3, -112, -102))
    for s in (-1, 1):
        m.zbar("ucf_black", 0, 26, (40 * s - 10, 40 * s + 10, -40, -24), (54 * s - 4, 54 * s + 4, -34, -28))


def eyes(m, lid, blink):
    for s in (-1, 1):
        c = (9 * s, 33, 18.5)
        if blink:
            m.ball(lid, c, (5.5, 1.6, 2.5), seg=8, rings=4)
            m.box("pupil", c[0] - 5, c[0] + 5, c[1] - 0.6, c[1] + 0.6, c[2] + 1.8, c[2] + 2.6)
        else:
            m.ball("eye_white", c, (5.5, 6.5, 2.8), seg=8, rings=5)
            m.ball("pupil", (c[0] - 1.2 * s, c[1] - 0.5, c[2] + 2.4), (2.4, 3.2, 1.0), seg=6, rings=4)


def foot(m, style, col):
    """A foot in a foot joint's LOCAL space (inside the vanilla Goomba foot's box: x -30..90 toward the toe,
    y -17..14, z -37..51)."""
    if style == "hoof":
        m.ball(col, (22, -4, 7), (34, 13, 26), seg=8, rings=5)
        m.box("usf_gold", 44, 54, -10, 6, -14, 28)
    else:   # boot
        m.ball(col, (20, -4, 7), (36, 14, 27), seg=8, rings=5)
        m.box("fsu_gold", 46, 56, -10, 8, -16, 30)
    m.box(col, -30, -6, -7, 7, -4, 18)                        # a stubby leg into the body


# id -> geo / folder, body colour (for the blink lids), feet, features
RIVALS = {
    "usf": {"geo": "goomba_geo", "folder": "goomba", "school": "USF Bulls", "lid": "bull", "foot": ("hoof", "hoof"),
            "build": build_bull},
    "fsu": {"school": "Florida State Seminoles", "lid": "fsu_garnet", "foot": ("boot", "fsu_garnet"),
            "build": build_seminole},
}
for _rid, _r in RIVALS.items():
    _r.setdefault("geo", "rival_%s_geo" % _rid)
    _r.setdefault("folder", "rival_%s" % _rid)
    _r["prefix"] = "rival_%s" % _rid


def build_parts(rid="usf"):
    r = RIVALS[rid]
    W = rest_world()
    parts = {}
    body = G.Mesh()
    r["build"](body)
    parts["body"] = to_local(body, inverse(W["body"]))
    for blink in (False, True):
        e = G.Mesh()
        eyes(e, r["lid"], blink)
        parts["eyes_blink" if blink else "eyes"] = to_local(e, inverse(W["eyes"]))
    for f in ("foot_l", "foot_r"):
        h = G.Mesh()
        foot(h, *r["foot"])
        parts[f] = h
    return parts


def geo_layout(geo, tops):
    t = lambda n: tops[n]
    return ("// GENERATED by tools/actors/make_rivals.py. Do not edit; edit the script and re-run it.\n"
            "// The vanilla Goomba skeleton (sm64coopdx actors/goomba/geo.inc.c) with a rival mascot's display lists.\n\n"
            "const GeoLayout %s[] = {\n"
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
            "};\n") % (geo, t("body"), t("eyes"), t("eyes_blink"), t("foot_l"), t("foot_r"))


def build(rid="usf"):
    """-> (model.inc.c, geo.inc.c, geo_header.h, triangle count) of one rival."""
    r = RIVALS[rid]
    parts = build_parts(rid)
    vtx, dls, used = [], [], set()
    tops = {name: G.emit_mesh(r["prefix"], mesh, name, vtx, dls, used) for name, mesh in parts.items()}
    model = "// GENERATED by tools/actors/make_rivals.py. Do not edit; edit the script and re-run it.\n\n"
    model += "\n".join(G.materials(r["prefix"], used)) + "\n" + "\n".join(vtx) + "\n" + "\n".join(dls)
    header = ["extern const GeoLayout %s[];" % r["geo"]]
    for mat in sorted(used):
        header += ["extern Lights1 %s_%s_lights;" % (r["prefix"], mat), "extern Gfx mat_%s_%s[];" % (r["prefix"], mat),
                   "extern Gfx mat_revert_%s_%s[];" % (r["prefix"], mat)]
    header += ["extern " + chunk.split(" = ")[0] + ";" for chunk in vtx + dls]
    ntris = sum(len(t) for mesh in parts.values() for t in mesh.tris.values())
    return model, geo_layout(r["geo"], tops), "\n".join(header) + "\n", ntris


GHOST = {"geo": "knight_ghost_geo", "folder": "knight_ghost", "prefix": "knight_ghost"}


def build_ghost():
    """-> (model.inc.c, geo.inc.c, geo_header.h, triangle count) of the Knight ghost: one display list drawn opaque
    or see-through by the Boo's transparency switch (oOpacity), exactly like boo_geo."""
    mesh = G.Mesh()
    build_knight_ghost(mesh)
    vtx, dls, used = [], [], set()
    top = G.emit_mesh(GHOST["prefix"], mesh, "body", vtx, dls, used)
    model = "// GENERATED by tools/actors/make_rivals.py. Do not edit; edit the script and re-run it.\n\n"
    model += "\n".join(G.materials(GHOST["prefix"], used)) + "\n" + "\n".join(vtx) + "\n" + "\n".join(dls)
    geo = ("// GENERATED by tools/actors/make_rivals.py. Do not edit; edit the script and re-run it.\n"
           "// boo_geo's layout (sm64coopdx actors/boo/geo.inc.c): the layer switch follows the object's oOpacity.\n\n"
           "const GeoLayout %s[] = {\n"
           "\tGEO_SHADOW(SHADOW_CIRCLE_4_VERTS, 0x96, 70),\n"
           "\tGEO_OPEN_NODE(),\n"
           "\t\tGEO_ASM(0, geo_update_layer_transparency),\n"
           "\t\tGEO_SWITCH_CASE(2, geo_switch_anim_state),\n"
           "\t\tGEO_OPEN_NODE(),\n"
           "\t\t\tGEO_DISPLAY_LIST(LAYER_OPAQUE, %s),\n"
           "\t\t\tGEO_DISPLAY_LIST(LAYER_TRANSPARENT, %s),\n"
           "\t\tGEO_CLOSE_NODE(),\n"
           "\tGEO_CLOSE_NODE(),\n"
           "\tGEO_END(),\n"
           "};\n") % (GHOST["geo"], top, top)
    header = ["extern const GeoLayout %s[];" % GHOST["geo"]]
    for mat in sorted(used):
        header += ["extern Lights1 %s_%s_lights;" % (GHOST["prefix"], mat), "extern Gfx mat_%s_%s[];" % (GHOST["prefix"], mat),
                   "extern Gfx mat_revert_%s_%s[];" % (GHOST["prefix"], mat)]
    header += ["extern " + chunk.split(" = ")[0] + ";" for chunk in vtx + dls]
    return model, geo, "\n".join(header) + "\n", sum(len(t) for t in mesh.tris.values())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=OUT, help="actors folder (default mods/sgl64/actors)")
    args = ap.parse_args(argv)
    for rid, r in RIVALS.items():
        model, geo, header, ntris = build(rid)
        folder = os.path.join(args.out, r["folder"])
        os.makedirs(folder, exist_ok=True)
        for fname, text in (("model.inc.c", model), ("geo.inc.c", geo), ("geo_header.h", header)):
            with open(os.path.join(folder, fname), "w") as f:
                f.write(text)
        print("make_rivals: %-6s %-24s %4d triangles -> %s (%s)" % (rid, r["school"], ntris,
                                                                 os.path.relpath(folder, ROOT), r["geo"]))
    model, geo, header, ntris = build_ghost()
    folder = os.path.join(args.out, GHOST["folder"])
    os.makedirs(folder, exist_ok=True)
    for fname, text in (("model.inc.c", model), ("geo.inc.c", geo), ("geo_header.h", header)):
        with open(os.path.join(folder, fname), "w") as f:
            f.write(text)
    print("make_rivals: ghost  UCF Knights (Boo)        %4d triangles -> %s (%s)" % (
        ntris, os.path.relpath(folder, ROOT), GHOST["geo"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
