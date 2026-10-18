"""Generate the rival-school mascots that replace the Goombas, as coopdx DynOS actors, without Blender.

UF's rivals sneak around campus as joke enemies: the USF Bull, the UCF Knight, the Georgia Bulldog, the Tennessee
hound, the Miami ibis, the LSU tiger and FSU's horse Renegade. The bull is named goomba_geo, so DynOS swaps it in
for every Goomba by default; the others (rival_<id>_geo) are swapped onto individual Goombas by
mods/sgl64/sgl_rivals.lua. The vanilla Goomba behaviour stays for all of them: they wander, charge Mario, get
squashed flat when you stomp them (or knocked out by a punch or kick) and drop a coin. To keep the Goomba's own
walk animation working, every geo copies the vanilla Goomba skeleton exactly (actors/goomba/geo.inc.c in sm64coopdx: GEO_SCALE 0.25, then 7 animated parts: root, body, the
eyes switch (open / blinking, geo_switch_anim_state), and the two feet with their pivots).

  hooves     built in the feet's own local space, inside the vanilla feet's box, so they step like Goomba feet
  body, eyes designed in world space (Y up, facing +Z, feet on y = 0, Goomba scale 1: in game normal Goombas are
             x1.5) and mapped into their joints with the joint transforms at frame 0 of the Goomba walk (REST below,
             read once from the US ROM; the walk only sways the body a few degrees from there)

Every rival shares the round Goomba-sized body, angry eyes (with a blink) and feet on the Goomba feet; RIVALS gives
each its colours, feet and head features (build_<id>).
Writes mods/sgl64/actors/goomba/ (the bull) and mods/sgl64/actors/rival_<id>/ ({model.inc.c, geo.inc.c, geo_header.h}).
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
    # Georgia Bulldogs
    "dog_white": (238, 236, 230), "uga_red": (186, 12, 47), "uga_black": (20, 20, 20), "nose": (25, 22, 22),
    # Tennessee (Smokey, the bluetick hound)
    "ut_orange": (255, 130, 0), "hound_white": (245, 243, 236), "hound_tan": (196, 150, 104),
    # Miami (Sebastian the ibis)
    "ibis_white": (246, 246, 240), "um_orange": (244, 115, 33), "um_green": (0, 80, 48),
    # LSU tiger
    "tiger": (232, 132, 38), "stripe": (30, 22, 20), "lsu_purple": (70, 29, 124), "lsu_gold": (253, 208, 35),
    "tiger_white": (245, 240, 230),
    # FSU (Renegade, the Appaloosa horse)
    "horse": (122, 74, 52), "fsu_garnet": (120, 47, 64), "fsu_gold": (206, 184, 136), "mane": (40, 28, 22),
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


def build_knight(m):
    """UCF Knights: black armour, a steel helmet with a visor slit round the eyes, a gold plume and gold trim."""
    blob(m, "ucf_black")
    # the helmet: a steel dome over the top half and a face plate under the eyes
    m.ball("steel", (0, 36, 0), (26, 17, 24), seg=10, rings=6)
    m.taper("steel", 14, 29, (-18, 18, 12, 22), (-21, 21, 14, 23))
    m.box("steel_dark", -20, 20, 27.5, 29, 20, 24)          # the visor's lower rim
    for k in range(-2, 3):                                   # breathing holes
        m.box("ucf_black", 4 * k - 0.8, 4 * k + 0.8, 18, 25, 22.6, 23.6)
    m.box("ucf_gold", -1.5, 1.5, 38, 52, 20, 24)             # the helmet's centre ridge
    # gold plume sweeping back from the crest
    for i in range(5):
        z, y = 2 - 7 * i, 52 + 3 * i - 0.8 * i * i
        m.ball("ucf_gold", (0, y, z), (4 - 0.4 * i, 5, 5), seg=6, rings=4)
    brows(m, "steel_dark")


def build_bulldog(m):
    """Georgia Bulldogs: a white bulldog with droopy jowls, an underbite, a red-and-black sweater, spiked collar."""
    blob(m, "dog_white")
    for s in (-1, 1):
        m.ball("dog_white", (8 * s, 22, 18), (10, 8, 8), seg=8, rings=5)       # jowls
        m.ball("hound_tan", (22 * s, 42, -2), (6, 5, 3), seg=6, rings=4)     # ears
        m.pyramid("dog_white", [(2 * s, 19, 22), (4 * s, 19, 22), (4 * s, 19, 24), (2 * s, 19, 24)], (3 * s, 25, 24))  # fangs
    m.ball("nose", (0, 28, 25), (5, 3.5, 3), seg=8, rings=4)
    scarf(m, "uga_red", "uga_black")
    m.taper("uga_black", 22.5, 25, (-23.8, 23.8, -21.8, 19.8), (-24, 24, -21.5, 20.5))  # collar
    for k in range(-3, 4):                                                # silver studs
        m.pyramid("steel", [(6 * k - 1.5, 23, 20), (6 * k + 1.5, 23, 20), (6 * k + 1.5, 24.5, 20),
                            (6 * k - 1.5, 24.5, 20)], (6 * k, 23.7, 23.5))
    brows(m, "uga_black")


def build_hound(m):
    """Tennessee: Smokey the bluetick hound, white with orange ears, a tan muzzle and an orange-and-white collar."""
    blob(m, "hound_white")
    m.ball("hound_tan", (0, 24, 18), (13, 9, 9), seg=10, rings=6)
    m.ball("nose", (0, 28, 26), (4.5, 3.5, 2.5), seg=8, rings=4)
    for s in (-1, 1):
        # long floppy ears hanging down the sides
        m.ball("ut_orange", (25 * s, 30, 0), (4, 13, 8), seg=6, rings=5)
        for k in range(3):   # bluetick spots
            m.ball("ucf_black", ((10 + 6 * k) * s, 40 - 3 * k, -10 + 5 * k), (2.5, 2.5, 1.5), seg=6, rings=3)
    scarf(m, "ut_orange", "hound_white")
    brows(m, "hound_tan")


def build_ibis(m):
    """Miami: Sebastian the ibis, white with a long curved orange beak, a green crest and an orange-and-green scarf."""
    blob(m, "ibis_white")
    # the beak: two tapered segments curving down
    m.zbar("um_orange", 18, 34, (-5, 5, 24, 31), (-3.5, 3.5, 22, 28))
    m.zbar("um_orange", 34, 46, (-3.5, 3.5, 22, 28), (-1.5, 1.5, 15, 19))
    # a spiky green crest of feathers
    for k, (x, z) in enumerate(((0, -2), (-6, -6), (6, -6), (0, -10))):
        m.pyramid("um_green", [(x - 3, 47, z - 3), (x + 3, 47, z - 3), (x + 3, 47, z + 3), (x - 3, 47, z + 3)],
                  (x * 1.4, 60 - 2 * k, z - 6))
    scarf(m, "um_green", "um_orange")
    brows(m, "um_green")


def build_tiger(m):
    """LSU: an orange tiger with black stripes, a white muzzle, round ears and a purple-and-gold headband."""
    blob(m, "tiger")
    m.ball("tiger_white", (0, 23, 17), (14, 9, 9), seg=10, rings=6)
    m.ball("nose", (0, 27, 25), (4, 3, 2.5), seg=8, rings=4)
    for s in (-1, 1):
        m.ball("tiger", (18 * s, 46, -2), (6, 6, 3), seg=8, rings=4)
        m.ball("tiger_white", (18 * s, 46, -0.5), (3.5, 3.5, 2), seg=6, rings=4)
        for k in range(3):   # stripes on the cheeks and sides
            y = 34 - 6 * k
            m.box("stripe", 22 * s - 2, 25 * s + 2 if s > 0 else 22 * s + 2, y, y + 2, -6, 8, G.rot_z(-14 * s, (23 * s, y, 0)))
    for k in range(3):       # stripes on top of the head
        m.box("stripe", -1.5 + 0 * k, 1.5, 49, 51.5, -12 + 8 * k, -8 + 8 * k)
    headband(m, "lsu_purple", "lsu_gold", y=36)
    brows(m, "stripe")


def build_horse(m):
    """FSU: Renegade, the Appaloosa horse, with a long muzzle, pointed ears, a dark mane and a garnet-and-gold band."""
    blob(m, "horse")
    m.zbar("horse", 10, 40, (-12, 12, 13, 31), (-8, 8, 14, 25))
    m.ball("hound_tan", (0, 19.5, 40), (8.5, 6, 3.5), seg=8, rings=5)
    m.box("mane", -6, 6, 13.5, 15, 22, 40)                  # the mouth line
    for s in (-1, 1):
        m.ball("nostril", (4 * s, 21, 43.2), (1.8, 2.2, 1.0), seg=6, rings=4)
        m.pyramid("horse", [(10 * s, 46, -4), (16 * s, 46, -4), (16 * s, 46, 3), (10 * s, 46, 3)], (14 * s, 60, -1))
        for k in range(3):   # appaloosa spots on the back
            m.ball("hound_white", ((8 + 7 * k) * s, 26 + 4 * k, -18 + 2 * k), (3, 3, 2), seg=6, rings=3)
    for k in range(6):       # the mane down the back of the head
        m.box("mane", -2.5, 2.5, 50 - 4 * k, 55 - 4 * k, -6 - 4 * k, -1 - 4 * k)
    headband(m, "fsu_garnet", "fsu_gold", y=38)
    brows(m, "mane")


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
        m.box("usf_gold" if col == "hoof" else "fsu_gold", 44, 54, -10, 6, -14, 28)
    elif style == "bird":
        m.box(col, -30, -6, -5, 5, 2, 12)                     # the shin
        for z in (-14, 7, 28):                                # three toes
            m.box(col, -6, 60, -10, -2, z - 4, z + 4)
    elif style == "boot":
        m.ball(col, (20, -4, 7), (36, 14, 27), seg=8, rings=5)
        m.box("ucf_gold", 46, 56, -10, 8, -16, 30)
    else:   # paw
        m.ball(col, (18, -4, 7), (32, 13, 26), seg=8, rings=5)
        for z in (-8, 7, 22):
            m.ball("nose", (48, -6, z), (4, 5, 5), seg=6, rings=3)
    m.box(col, -30, -6, -7, 7, -4, 18)                        # a stubby leg into the body


# id -> geo / folder, body colour (for the blink lids), feet, features
RIVALS = {
    "usf": {"geo": "goomba_geo", "folder": "goomba", "school": "USF Bulls", "lid": "bull", "foot": ("hoof", "hoof"),
            "build": build_bull},
    "ucf": {"school": "UCF Knights", "lid": "steel", "foot": ("boot", "steel"), "build": build_knight},
    "uga": {"school": "Georgia Bulldogs", "lid": "dog_white", "foot": ("paw", "dog_white"), "build": build_bulldog},
    "tenn": {"school": "Tennessee Volunteers", "lid": "hound_white", "foot": ("paw", "hound_white"), "build": build_hound},
    "miami": {"school": "Miami Hurricanes", "lid": "ibis_white", "foot": ("bird", "um_orange"), "build": build_ibis},
    "lsu": {"school": "LSU Tigers", "lid": "tiger", "foot": ("paw", "tiger"), "build": build_tiger},
    "fsu": {"school": "Florida State Seminoles", "lid": "horse", "foot": ("hoof", "mane"), "build": build_horse},
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
