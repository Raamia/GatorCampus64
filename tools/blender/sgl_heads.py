"""Procedural low-poly heads (skull + hair + face) and head replacement in every
head-bearing mesh of the coopdx Mario template.

Head space: (l, f, u) = (character's left, forward, up), origin at the head
pivot bone (Head DL / the variant's bone). In bone-local coordinates of the
template's head bones that is (x, y, z) = (u, f, l), so one geometry can be
placed into every head mesh through each bone's matrix.

The head is ONE shell of rings x SEG columns. Faces inside the "face window"
are skin (eye / mouth materials on the eye and mouth bands, planar UVs), every
other face is hair and its vertices are pushed outward (hair volume). Vertices
on the window border are split and joined by strips, which read as the hair's
thickness at the hairline. Styles add a fringe flap over the forehead, a drape
of long hair below the head, ears and a nose.
"""
import math

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

import sgl_characters
import sgl_materials as smat

SEG = 12
THETAS = [i * 360.0 / SEG for i in range(SEG)]  # 0 = front, 90 = character's left, 180 = back

# u, rx (half width), rf (front depth), rb (back depth), f0 (forward shift), superellipse power
SKULL_RINGS = [
    (0.16, 0.34, 0.37, 0.34, 0.05, 2.1),
    (0.42, 0.52, 0.50, 0.50, 0.03, 2.3),
    (0.74, 0.55, 0.48, 0.54, 0.00, 2.3),
    (0.98, 0.49, 0.39, 0.50, -0.02, 2.2),
    (1.13, 0.34, 0.25, 0.36, -0.03, 2.0),
]
BOTTOM_POLE = Vector((0.0, 0.07, 0.05))
TOP_POLE = Vector((0.0, -0.03, 1.21))
WIDEST_RING = 2
HEAD_CENTER = Vector((0.0, 0.0, 0.62))
BANDS = ["fan_bottom", 0, 1, 2, 3, "fan_top"]  # band k spans ring k -> ring k+1
BAND_ROLE = {"fan_bottom": "skin", 0: "mouth", 1: "eyes", 2: "skin", 3: "skin", "fan_top": "skin"}

# Texture rectangles in head space: (l centre, u centre, width, height)
FACE_LAYOUT = {
    "eyes": (0.0, 0.565, 0.90, 0.45),  # 64x32 texture, square texels
    "mouth": (0.0, 0.30, 0.30, 0.15),  # 32x16 texture
    "textured_half_angle": 62.0,        # eye/mouth material only on front columns
}

# ------------------------------------------------------------------ hair styles
# long_straight_past_shoulders (Cher) and straight_fringe_medium (Daniel) have been
# built and reviewed; the other presets are first guesses so every character spec
# builds, refine when they are made. Optional per-style keys:
#   skull / bottom_pole / top_pole / face_layout  head shape + texture rects (configure())
#   ring_off {ring: offset}                       hair thickness per skull ring
#   hair_bottom {column angle: band}              outside the face window, the lowest
#                                                 hair band of that column (skin below)
#   fringe.lo_ring / offset_mid / mid_at          how low the fringe may reach; convex
#                                                 middle row of the fringe flap
#   fringe.weld_ends (default True)               flap sides welded to the side hair
#                                                 (weld_fringe_ends)
#   ears {theta, u, h, out, w}                    ear wedge placement
#   nose {u, half_width, bottom, tip, top}        nose size/placement (add_nose)
_LONG = {
    "window": 60, "face_bands": ("fan_bottom", 0, 1, 2),
    "off": {"top": 0.08, "upper": 0.075, "side": 0.06, "back": 0.075},
    "hang": True,
    "fringe": None, "drape": None, "ears": False,
}
HAIR_STYLES = {
    "long_straight_past_shoulders": dict(_LONG, **{
        # side part at -15 deg (her right); the big sweep falls to her left
        "fringe": {"kind": "side_part", "offset": 0.05,
                   "edge": {-60: 0.75, -45: 0.775, -30: 0.845, -15: 0.935, 0: 0.80, 15: 0.765,
                            30: 0.752, 45: 0.75, 60: 0.75}},
        "drape": {"ends": {60: 0.02, 90: 0.03, 120: -0.20, 150: -0.44, 180: -0.52, 210: -0.40,
                           240: -0.24, 270: 0.05, 300: 0.0},
                  "thickness": 0.07, "clearance": 0.05, "flare": 0.02, "notch": 0.09},
        # wispy face-framing layers
        "locks": {"theta_inner": 50, "theta_outer": 64, "theta_tip": 56, "u_top": 0.76, "u_mid": 0.40,
                  "u_tip": 0.03, "offset_inner": 0.035, "offset_outer": 0.06},
    }),
    "long_curly_voluminous_with_curly_bangs": dict(_LONG, **{  # untested
        "off": {"top": 0.13, "upper": 0.12, "side": 0.12, "back": 0.12},
        "fringe": {"kind": "full", "offset": 0.07,
                   "edge": {t: 0.74 + 0.02 * (abs(t) // 15 % 2) for t in range(-60, 61, 15)}},
        "drape": {"ends": {60: -0.02, 90: -0.05, 120: -0.25, 150: -0.40, 180: -0.45, 210: -0.40,
                           240: -0.25, 270: -0.05, 300: -0.02},
                  "thickness": 0.10, "clearance": 0.05, "flare": 0.08},
    }),
    "straight_fringe_medium": {  # Daniel (built and reviewed against his photos, 2 rounds)
        # heavy straight fringe down to the brows, thick straight hair with volume on
        # top, sides hanging over the tops of the ears, nape covered
        "window": 90, "face_bands": ("fan_bottom", 0, 1, 2),
        "off": {"top": 0.11, "upper": 0.10, "side": 0.055, "back": 0.075},
        "ring_off": {2: 0.065},  # temples flare a little (thick straight hair)
        "hang": False,
        # oval face (taller than wide): narrow cheeks/temples, rounded chin a little lower
        "skull": [
            (0.00, 0.29, 0.36, 0.33, 0.06, 2.3),
            (0.36, 0.47, 0.50, 0.50, 0.03, 2.4),
            (0.68, 0.50, 0.48, 0.54, 0.00, 2.3),
            (0.86, 0.455, 0.41, 0.50, -0.02, 2.2),
            (0.97, 0.34, 0.29, 0.39, -0.03, 2.0),
        ],
        "bottom_pole": (0.0, 0.12, -0.12),
        "top_pole": (0.0, -0.03, 1.03),
        # eyes: 64 texels across about 0.86 of the face width (the artist's 1:1 sizing);
        # the rect is 15% shorter than square texels so the eyes read as a narrow squint.
        # mouth: same horizontal texel size as the eyes (0.42 / 32 = 0.84 / 64)
        "face_layout": {"eyes": (0.0, 0.565, 0.84, 0.36), "mouth": (0.0, 0.23, 0.42, 0.21)},
        # heavy, nearly straight lower edge just above the eye art (u 0.61), broken into
        # broad clumps by a few notches (+-45, +-22.5) and the parting just to his right of
        # centre (-7.5); the clump tips at +-30 overlap the top texel row of the eyes,
        # the temples hang lower
        # weld_ends False: his reviewed head geometry stays exactly as built (the cast
        # polish may change only his face textures). Seen straight from the side a thin
        # slit of temple skin still shows where each flap end meets the side hair (the
        # gap weld_fringe_ends closes for the others); welding it would change his head
        "fringe": {"kind": "full", "offset": 0.035, "offset_mid": 0.115, "mid_at": 0.5, "lo_ring": 1,
                   "weld_ends": False,
                   "edge": {-90: 0.52, -82.5: 0.55, -75: 0.535, -67.5: 0.585, -60: 0.62, -52.5: 0.615,
                            -45: 0.66, -37.5: 0.62, -30: 0.605, -22.5: 0.66, -15: 0.62,
                            -7.5: 0.69,  # the parting
                            0: 0.62, 7.5: 0.62, 15: 0.62, 22.5: 0.66, 30: 0.605, 37.5: 0.62,
                            45: 0.66, 52.5: 0.615, 60: 0.62, 67.5: 0.58, 75: 0.535, 82.5: 0.55, 90: 0.52}},
        # side hair hanging in front of the tops of the ears
        "locks": {"theta_inner": 74, "theta_outer": 104, "theta_tip": 92, "u_top": 0.78, "u_mid": 0.53,
                  "u_tip": 0.43, "offset_inner": 0.035, "offset_outer": 0.10},
        # beside and behind the ears the hair stops at ring 1 (u 0.36), the jaw below
        # is skin; only the back of the head is covered down to the nape
        "hair_bottom": {105: 1},
        # no drape: the back of the shell already reaches the nape (ring 0) and a
        # hanging curtain only collides with the hood bunched behind the neck
        "drape": None,
        "ears": {"theta": 96, "u": 0.395, "h": 0.22, "out": 0.12, "w": 0.08},
        # broad, flat nose (about 15% of the face width)
        "nose": {"u": 0.40, "half_width": 0.08, "bottom": -0.035, "tip": 0.04, "top": 0.06},
    },
    "straight_mushroom_cut_side_swept_bangs": {  # untested (Anh, Josh, Donald)
        "window": 60, "face_bands": ("fan_bottom", 0, 1, 2),
        "off": {"top": 0.08, "upper": 0.08, "side": 0.06, "back": 0.07},
        "hang": True,
        "fringe": {"kind": "side_part", "offset": 0.055,
                   "edge": {-60: 0.74, -45: 0.75, -30: 0.77, -15: 0.80, 0: 0.79, 15: 0.77, 30: 0.75,
                            45: 0.74, 60: 0.74}},
        "drape": {"ends": {120: 0.10, 150: 0.06, 180: 0.05, 210: 0.06, 240: 0.10},
                  "thickness": 0.06, "clearance": 0.04, "flare": 0.0},
        "ears": False,
    },
    "short_curly_top_faded_sides": {  # untested (Alfred)
        "window": 90, "face_bands": ("fan_bottom", 0, 1, 2),
        "off": {"top": 0.14, "upper": 0.11, "side": 0.025, "back": 0.03},
        "hang": False, "fringe": None, "drape": None, "ears": True,
    },
    "fluffy_windswept_medium": {  # untested (Jaime)
        "window": 75, "face_bands": ("fan_bottom", 0, 1, 2),
        "off": {"top": 0.13, "upper": 0.13, "side": 0.11, "back": 0.10},
        "hang": False,
        "fringe": {"kind": "full", "offset": 0.08,
                   "edge": {t: 0.76 + (0.03 if t % 30 else 0.0) for t in range(-60, 61, 15)}},
        "drape": None, "ears": False,
    },
    "tight_curls_voluminous_with_curly_fringe": {  # untested (Raami)
        "window": 75, "face_bands": ("fan_bottom", 0, 1, 2),
        "off": {"top": 0.17, "upper": 0.16, "side": 0.14, "back": 0.13},
        "hang": False,
        "fringe": {"kind": "full", "offset": 0.10,
                   "edge": {t: 0.75 + (0.025 if t % 30 else 0.0) for t in range(-60, 61, 15)}},
        "drape": None, "ears": False,
    },
    "short_wavy_curly": {  # untested (Vignesh)
        "window": 90, "face_bands": ("fan_bottom", 0, 1, 2),
        "off": {"top": 0.10, "upper": 0.08, "side": 0.04, "back": 0.05},
        "hang": False, "fringe": None, "drape": None, "ears": True,
    },
}
DEFAULT_STYLE = "short_wavy_curly"


_DEFAULTS = {"SKULL_RINGS": list(SKULL_RINGS), "BOTTOM_POLE": BOTTOM_POLE.copy(), "TOP_POLE": TOP_POLE.copy(),
             "FACE_LAYOUT": dict(FACE_LAYOUT)}


def configure(style):
    """Apply a style's optional head-shape overrides (module globals; one character
    is built per process): "skull" (ring list, same layout as SKULL_RINGS),
    "bottom_pole"/"top_pole" (l, f, u) and "face_layout" (merged into FACE_LAYOUT)."""
    global SKULL_RINGS, BOTTOM_POLE, TOP_POLE, FACE_LAYOUT
    SKULL_RINGS = [tuple(r) for r in style.get("skull", _DEFAULTS["SKULL_RINGS"])]
    if len(SKULL_RINGS) != len(_DEFAULTS["SKULL_RINGS"]):
        raise ValueError("skull override must keep the ring count (band roles depend on it)")
    BOTTOM_POLE = Vector(style.get("bottom_pole", _DEFAULTS["BOTTOM_POLE"]))
    TOP_POLE = Vector(style.get("top_pole", _DEFAULTS["TOP_POLE"]))
    FACE_LAYOUT = dict(_DEFAULTS["FACE_LAYOUT"], **style.get("face_layout", {}))


def hair_style(spec):
    if "appearance" in spec:
        from sgl_appearance import validate
        from sgl_likeness import head_style
        profile = validate(spec["appearance"])
        return f"appearance_v{profile['version']}:{profile['face']}/{profile['hair']}", head_style(profile)
    custom = sgl_characters.get(spec, "HAIR_STYLE")
    name = (custom or {}).get("base") or spec.get("build", {}).get("hair_style", DEFAULT_STYLE)
    if name not in HAIR_STYLES:
        if custom is None:
            print(f"SGL WARNING: hair_style {name!r} has no preset yet, using {DEFAULT_STYLE!r}")
        name = DEFAULT_STYLE
    style = HAIR_STYLES[name]
    if custom:
        style = dict(style, **{k: v for k, v in custom.items() if k != "base"})
        name = f"{name} + characters/{sgl_characters.load(spec).__name__.removeprefix('sgl_char_')}.py"
    return name, style


# ------------------------------------------------------------------ skull
def ring_point(k, theta):
    u, rx, rf, rb, f0, p = SKULL_RINGS[k]
    t = math.radians(theta)
    s, c = math.sin(t), math.cos(t)
    e = 2.0 / p
    l = rx * math.copysign(abs(s) ** e, s)
    f = f0 + (rf if c >= 0 else rb) * math.copysign(abs(c) ** e, c)
    return Vector((l, f, u))


def _wrap(theta):
    return (theta + 180.0) % 360.0 - 180.0


def skull_surface(theta, u):
    """Point on the faceted skull (bilinear inside the band quad)."""
    theta = theta % 360.0
    i0 = int(theta // (360.0 / SEG)) % SEG
    i1 = (i0 + 1) % SEG
    a = (theta - THETAS[i0]) / (360.0 / SEG)
    us = [r[0] for r in SKULL_RINGS]
    if u <= us[0]:
        lo, hi = None, 0
    elif u >= us[-1]:
        lo, hi = len(us) - 1, None
    else:
        lo = max(k for k in range(len(us)) if us[k] <= u)
        hi = lo + 1

    def pt(k, i):
        if k is None:
            return BOTTOM_POLE if hi == 0 else TOP_POLE
        return ring_point(k, THETAS[i])

    ulo = BOTTOM_POLE.z if lo is None else us[lo]
    uhi = TOP_POLE.z if hi is None else us[hi]
    b = 0.0 if uhi == ulo else (u - ulo) / (uhi - ulo)
    p_lo = pt(lo, i0).lerp(pt(lo, i1), a)
    p_hi = pt(hi, i0).lerp(pt(hi, i1), a)
    return p_lo.lerp(p_hi, b)


def surface_normal(theta, u, d=2.0, du=0.02):
    p = skull_surface(theta, u)
    t = skull_surface(theta + d, u) - skull_surface(theta - d, u)
    v = skull_surface(theta, u + du) - skull_surface(theta, u - du)
    n = t.cross(v)
    if n.dot(p - HEAD_CENTER) < 0:
        n = -n
    return n.normalized()


# ------------------------------------------------------------------ geometry container
class Geo:
    def __init__(self):
        self.verts = []
        self.faces = []  # (indices, role)

    def v(self, p):
        self.verts.append(Vector(p))
        return len(self.verts) - 1

    def face(self, idx, role, outward):
        idx = [i for n, i in enumerate(idx) if i != idx[n - 1]] if len(idx) > 3 else list(idx)
        # drop duplicates by position too
        uniq = []
        for i in idx:
            if all((self.verts[i] - self.verts[j]).length > 1e-6 for j in uniq):
                uniq.append(i)
        if len(uniq) < 3:
            return
        pts = [self.verts[i] for i in uniq]
        n = Vector()
        for a, b in zip(pts, pts[1:] + pts[:1]):
            n += a.cross(b)
        # (l, f, u) is LEFT-handed relative to Blender's mesh space (the mapping
        # to bone space is a reflection), so a face is outward-facing in the
        # mesh when its head-space winding normal points AGAINST `outward`.
        if n.dot(outward) > 0:
            uniq.reverse()
        self.faces.append((uniq, role))

    def tri_count(self):
        return sum(len(f) - 2 for f, _ in self.faces)


def _hair_dir(k, p):
    """Direction to push a skull vertex outward for hair volume."""
    if k is not None and k < WIDEST_RING:
        d = Vector((p.x, p.y - SKULL_RINGS[k][4], 0.0))
    else:
        d = p - HEAD_CENTER
    return d.normalized() if d.length > 1e-6 else Vector((0, 0, 1))


def _offset(style, k, theta):
    o = style["off"]
    if k in style.get("ring_off", {}):
        return style["ring_off"][k]
    if k == "top" or k == len(SKULL_RINGS) - 1:
        return o["top"]
    if k > WIDEST_RING:
        return o["upper"]
    return o["side"] if math.cos(math.radians(theta)) >= 0 else o["back"]


def hair_point(style, k, theta):
    if k == "top":
        return TOP_POLE + Vector((0, 0, style["off"]["top"]))
    p = ring_point(k, theta)
    off = _offset(style, k, theta)
    d = _hair_dir(k, p)
    q = p + d * off
    if style.get("hang") and k < WIDEST_RING:
        # long hair falls straight from the widest ring instead of following the jaw
        w = ring_point(WIDEST_RING, theta)
        wd = _hair_dir(WIDEST_RING, w)
        hang = w + wd * _offset(style, WIDEST_RING, theta)
        r_hang = Vector((hang.x, hang.y - SKULL_RINGS[k][4], 0)).length
        cur = Vector((q.x, q.y - SKULL_RINGS[k][4], 0))
        if cur.length < r_hang:
            q = Vector((0, SKULL_RINGS[k][4], q.z)) + cur.normalized() * r_hang
    return q


def build_head(style, face_window_roles=True):
    """Return Geo with roles: skin, hair, eyes, mouth."""
    g = Geo()
    nr = len(SKULL_RINGS)
    window = style["window"]
    face_bands = set(style["face_bands"])
    tex_half = FACE_LAYOUT["textured_half_angle"]

    # shell faces as corner keys: (ring index | 'bot' | 'top', column)
    shell = []
    for i in range(SEG):
        j = (i + 1) % SEG
        tc = THETAS[i] + 180.0 / SEG
        shell.append(("fan_bottom", [("bot", 0), (0, j), (0, i)], tc))
        for k in range(nr - 1):
            shell.append((k, [(k, i), (k, j), (k + 1, j), (k + 1, i)], tc))
        shell.append(("fan_top", [(nr - 1, i), (nr - 1, j), ("top", 0)], tc))

    # optional per-column lowest hair band outside the face window, keyed by the
    # column's |angle| (e.g. {105: 1}: beside/behind the ear the hair stops at ring 1
    # and the jaw below is skin); unlisted columns are hair all the way down
    band_order = ["fan_bottom"] + list(range(nr - 1)) + ["fan_top"]
    hair_bottom = {abs(_wrap(float(t))): b for t, b in style.get("hair_bottom", {}).items()}

    def region(band, tc):
        a = abs(_wrap(tc))
        if a < window:
            return "face" if band in face_bands else "hair"
        lowest = next((b for t, b in hair_bottom.items() if abs(t - a) < 1e-3), "fan_bottom")
        return "hair" if band_order.index(band) >= band_order.index(lowest) else "face"

    corner_regions = {}
    for band, corners, tc in shell:
        r = region(band, tc)
        for c in corners:
            corner_regions.setdefault(c, set()).add(r)

    def skin_pos(c):
        k, i = c
        if k == "bot":
            return BOTTOM_POLE
        if k == "top":
            return TOP_POLE
        return ring_point(k, THETAS[i])

    def hair_pos(c):
        k, i = c
        if k == "bot":
            return BOTTOM_POLE
        return hair_point(style, k, THETAS[i])

    vid = {}
    for c, regs in corner_regions.items():
        if "face" in regs:
            vid[(c, "face")] = g.v(skin_pos(c))
        if "hair" in regs:
            hp = hair_pos(c)
            if "face" in regs and (hp - g.verts[vid[(c, "face")]]).length < 1e-6:
                vid[(c, "hair")] = vid[(c, "face")]
            else:
                vid[(c, "hair")] = g.v(hp)

    edge_faces = {}
    for band, corners, tc in shell:
        r = region(band, tc)
        idx = [vid[(c, r)] for c in corners]
        if r == "hair":
            role = "hair"
        else:
            role = BAND_ROLE[band]
            if role in ("eyes", "mouth") and abs(_wrap(tc)) > tex_half:
                role = "skin"
        centroid = sum((g.verts[i] for i in idx), Vector()) / len(idx)
        g.face(idx, role, centroid - HEAD_CENTER)
        for a, b in zip(corners, corners[1:] + corners[:1]):
            key = tuple(sorted([a, b], key=str))
            edge_faces.setdefault(key, []).append((r, centroid))

    # strips along face/hair borders (hair thickness at the hairline)
    for (a, b), lst in edge_faces.items():
        regs = {r for r, _ in lst}
        if regs != {"face", "hair"}:
            continue
        face_centroid = next(c for r, c in lst if r == "face")
        quad = [vid[(a, "face")], vid[(b, "face")], vid[(b, "hair")], vid[(a, "hair")]]
        mid = (g.verts[vid[(a, "face")]] + g.verts[vid[(b, "face")]]) / 2
        g.face(quad, "hair", face_centroid - mid)

    g.hair_vid = {c: vid[(c, "hair")] for (c, r) in vid if r == "hair"}
    g.face_vid = {c: vid[(c, "face")] for (c, r) in vid if r == "face"}
    return g


def add_fringe(g, style):
    fr = style.get("fringe")
    if not fr:
        return
    edge = dict(sorted(fr["edge"].items()))
    off = fr["offset"]
    top_ring = 3  # forehead top ring (u = 0.98)
    lo_ring = fr.get("lo_ring", 2)  # the edge may not go below this ring (1: down to the brows)
    thetas = sorted(edge)
    u_lo = SKULL_RINGS[lo_ring][0]
    u_hi = SKULL_RINGS[top_ring][0]

    def top_vertex(t):
        i = round((t % 360) / (360.0 / SEG)) % SEG
        if abs(THETAS[i] - (t % 360)) > 1e-6:
            return None
        return g.hair_vid.get((top_ring, i))

    # optional middle row: the fringe bulges out like the crown above it, then tucks
    # in toward the brows (a convex profile instead of a flat flap hanging off ring 3)
    mid_off = fr.get("offset_mid")
    mids = {}
    if mid_off is not None:
        for t in thetas:
            u_e = max(u_lo + 0.005, min(u_hi - 0.02, edge[t]))
            u_m = u_e + (u_hi - u_e) * fr.get("mid_at", 0.45)
            mids[t] = g.v(skull_surface(t, u_m) + surface_normal(t, u_m) * mid_off)
    low = {}
    tuck = {}
    for t in thetas:
        u = max(u_lo + 0.005, min(u_hi - 0.02, edge[t]))
        i = round((t % 360) / (360.0 / SEG)) % SEG
        on_grid = abs(THETAS[i] - (t % 360)) < 1e-6
        if on_grid and u <= u_lo + 0.02 and (lo_ring, i) in g.hair_vid and (lo_ring, i) in g.face_vid:
            # snap to the hair border vertex so the flap meets the side hair exactly
            low[t] = g.hair_vid[(lo_ring, i)]
            tuck[t] = g.face_vid[(lo_ring, i)]
            continue
        p = skull_surface(t, u)
        n = surface_normal(t, u)
        low[t] = g.v(p + n * off)
        tuck[t] = g.v(p - n * 0.006)
    g.fringe_welded = {}
    if mids and fr.get("weld_ends", True):
        weld_fringe_ends(g, fr, thetas, mids, low, lo_ring, top_ring)
    # flap faces: per 30-degree shell column, fan from the two top corners
    step = 360.0 / SEG
    col_starts = sorted({math.floor((t + 1e-6) / step) * step for t in thetas if t < max(thetas) - 1e-6})
    for c0 in col_starts:
        c1 = c0 + step
        ta, tb = top_vertex(c0), top_vertex(c1)
        if ta is None or tb is None:
            continue
        lows = [(mids or low)[t] for t in thetas if c0 - 1e-6 <= t <= c1 + 1e-6]
        centroid = sum((g.verts[i] for i in lows + [ta, tb]), Vector()) / (len(lows) + 2)
        out = centroid - HEAD_CENTER
        mid = len(lows) // 2
        for x, y in zip(lows[:mid], lows[1:mid + 1]):
            g.face([ta, x, y], "hair", out)
        g.face([ta, lows[mid], tb], "hair", out)
        for x, y in zip(lows[mid:], lows[mid + 1:]):
            g.face([tb, x, y], "hair", out)
    if mids:
        for a, b in zip(thetas, thetas[1:]):
            ca = (g.verts[mids[a]] + g.verts[mids[b]] + g.verts[low[a]] + g.verts[low[b]]) / 4
            g.face([mids[a], mids[b], low[b], low[a]], "hair", ca - HEAD_CENTER)
    # tuck strip: the visible underside of the fringe
    for a, b in zip(thetas, thetas[1:]):
        quad = [low[a], low[b], tuck[b], tuck[a]]
        g.face(quad, "hair", Vector((0, 0.35, -1.0)))


def weld_fringe_ends(g, fr, thetas, mids, low, lo_ring, top_ring):
    """Close the flap's sides. With a middle row (offset_mid), the first and last
    middle-row vertices bulge out by offset_mid like the rest, while the side hair next to
    them (the shell's hair border at that column) runs along the skull: a slot opens
    between the flap's side edge and the side hair at each temple, and the forehead skin
    (or the flap's inside) shows through it from the side. The end middle vertex is
    welded to the shell instead, so the flap's side edge IS the side hair's border edge:
      - edge snapped to the border (its low vertex is the lo_ring hair vertex): the middle
        vertex becomes the ring-2 hair vertex when the flap reaches below ring 2 (lo_ring
        1), else the low vertex itself (the flap side then runs straight down the shell
        edge ring 3 -> ring 2)
      - edge hanging free below ring 2 (not snapped, e.g. over the temple in front of the
        ear): the middle vertex becomes the ring-2 hair vertex and the flap's lower part
        hangs from the side hair's corner
    Only window-border columns qualify (the column must have a ring-2 hair vertex). The
    welded vertices are recorded in g.fringe_welded {theta: vertex}. fringe.weld_ends =
    False keeps the free-standing ends."""
    u2 = SKULL_RINGS[2][0]
    u_lo = SKULL_RINGS[lo_ring][0]
    u_hi = SKULL_RINGS[top_ring][0]
    for t in sorted({thetas[0], thetas[-1]}):
        i = round((t % 360) / (360.0 / SEG)) % SEG
        if abs(THETAS[i] - (t % 360)) > 1e-6 or (top_ring, i) not in g.hair_vid:
            continue
        h2 = g.hair_vid.get((2, i))
        if h2 is None or g.face_vid.get((2, i)) is None:
            continue  # not a window-border column
        u_e = max(u_lo + 0.005, min(u_hi - 0.02, fr["edge"][t]))
        snapped = low[t] == g.hair_vid.get((lo_ring, i))
        if snapped and lo_ring >= 2:
            mids[t] = low[t]
        elif u_e < u2:
            mids[t] = h2
        else:
            continue
        g.fringe_welded[t] = mids[t]


def body_radius_fn(body_bvh):
    """r(theta, u): horizontal distance from the head axis to the body surface
    (rest pose, head space), or None."""
    def r(theta, u, f0=0.0):
        if body_bvh is None:
            return None
        t = math.radians(theta)
        d = Vector((math.sin(t), math.cos(t), 0.0))
        axis = Vector((0, f0, u))
        hit = body_bvh.ray_cast(axis + d * 2.0, -d, 2.0)
        if hit[0] is None:
            return None
        return (hit[0] - axis).length
    return r


def add_drape(g, style, body_r):
    dr = style.get("drape")
    if not dr:
        return
    ends = dict(sorted(((t % 360), u) for t, u in dr["ends"].items()))
    # order columns around the back: from the front-left (60) through 180 to 300
    order = sorted(ends, key=lambda t: t if t >= 0 else t + 360)
    th = dr["thickness"]
    clear = dr["clearance"]
    flare = dr.get("flare", 0.0)
    top_ring = 0
    cols = []
    for t in order:
        i = round(t / (360.0 / SEG)) % SEG
        top = g.hair_vid.get((top_ring, i))
        if top is None:
            continue
        ptop = g.verts[top]
        f0 = SKULL_RINGS[top_ring][4]
        radial = Vector((ptop.x, ptop.y - f0, 0))
        r_top = radial.length
        d = radial.normalized()
        u_top = ptop.z
        u_end = ends[t]
        rows_u = [u_top, (u_top + u_end) / 2, u_end]
        outer = [top]
        inner = []
        for n, u in enumerate(rows_u):
            # the drape's own shape: straight down from the shell (flare 0), widening
            # toward the tips (flare > 0) or tapering in (flare < 0). The body is only a
            # floor: the inner side never comes closer than `clearance` to the torso
            # (rest pose). (Clamping the shape TO the body cancelled any flare, so the
            # drape hugged the back and shoulders and clipped as soon as the head turned.)
            r_out = r_top + flare * (n / 2)
            rb = body_r(t, u, f0) if n > 0 else None
            if rb is not None:
                r_out = max(r_out, rb + clear + th)
            p_out = Vector((0, f0, u)) + d * r_out
            if n > 0:
                outer.append(g.v(p_out))
            r_in = r_out - th
            u_in = u + 0.04 if n == 0 else u
            inner.append(g.v(Vector((0, f0, u_in)) + d * r_in))
        cols.append((t, d, outer, inner))
    notch = dr.get("notch", 0.0)
    for (ta, da, oa, ia), (tb, db, ob, ib) in zip(cols, cols[1:]):
        mid_dir = (da + db).normalized()
        g.face([oa[0], ob[0], ob[1], oa[1]], "hair", mid_dir)
        g.face([ia[0], ib[0], ib[1], ia[1]], "hair", -mid_dir)
        if notch <= 0:
            g.face([oa[1], ob[1], ob[2], oa[2]], "hair", mid_dir)
            g.face([ia[1], ib[1], ib[2], ia[2]], "hair", -mid_dir)
            g.face([oa[2], ob[2], ib[2], ia[2]], "hair", Vector((0, 0, -1)))
            continue
        # notch between the two strand tips: the bottom edge rises midway
        om_p = (g.verts[oa[2]] + g.verts[ob[2]]) / 2
        im_p = (g.verts[ia[2]] + g.verts[ib[2]]) / 2
        rise = min(notch, 0.45 * (min(g.verts[oa[1]].z, g.verts[ob[1]].z) - om_p.z))
        om = g.v(om_p + Vector((0, 0, rise)))
        im = g.v(im_p + Vector((0, 0, rise)))
        for x, y, z in ((oa[1], ob[1], om), (oa[1], om, oa[2]), (ob[1], ob[2], om)):
            g.face([x, y, z], "hair", mid_dir)
        for x, y, z in ((ia[1], ib[1], im), (ia[1], im, ia[2]), (ib[1], ib[2], im)):
            g.face([x, y, z], "hair", -mid_dir)
        g.face([oa[2], om, im, ia[2]], "hair", Vector((0, 0, -1)) + (da - mid_dir))
        g.face([om, ob[2], ib[2], im], "hair", Vector((0, 0, -1)) + (db - mid_dir))
    # close the two ends of the drape
    for (t, d, o, i), (t2, d2, o2, i2) in ((cols[0], cols[1]), (cols[-1], cols[-2])):
        away = (d - d2).normalized()
        for n in range(2):
            g.face([o[n], o[n + 1], i[n + 1], i[n]], "hair", away)


def add_face_locks(g, style):
    """Tapered locks hanging in front of the face-window border (both sides)."""
    lk = style.get("locks")
    if not lk:
        return
    for side in (-1, 1):
        th_in = side * lk["theta_inner"]
        th_out = side * lk["theta_outer"]
        th_tip = side * lk["theta_tip"]
        rows = []
        for u in (lk["u_top"], lk["u_mid"]):
            pi = skull_surface(th_in, u) + surface_normal(th_in, u) * lk["offset_inner"]
            po = skull_surface(th_out, u) + surface_normal(th_out, u) * lk["offset_outer"]
            si = skull_surface(th_in, u) - surface_normal(th_in, u) * 0.006
            rows.append((g.v(pi), g.v(po), g.v(si)))
        ut = lk["u_tip"]
        tip = g.v(skull_surface(th_tip, max(ut, SKULL_RINGS[0][0])) * Vector((1, 1, 0)) + Vector((0, 0, ut))
                  + surface_normal(th_tip, max(ut, SKULL_RINGS[0][0])) * lk["offset_outer"])
        tip_in = g.v(skull_surface(th_tip, max(ut, SKULL_RINGS[0][0])) * Vector((0.97, 0.97, 0))
                     + Vector((0, 0, ut + 0.02)))
        (a0, b0, s0), (a1, b1, s1) = rows
        out = skull_surface(side * 0.5 * (lk["theta_inner"] + lk["theta_outer"]), 0.5)
        out = Vector((out.x, out.y + 0.25, 0))
        g.face([a0, b0, b1, a1], "hair", out)
        g.face([a1, b1, tip], "hair", out)
        # thickness along the inner (face-side) edge, tucked into the skull
        toward_face = Vector((-side, 0.6, 0))
        g.face([a0, a1, s1, s0], "hair", toward_face)
        g.face([a1, tip, tip_in, s1], "hair", toward_face + Vector((0, 0, -0.5)))


def add_nose(g, cfg=None):
    """Small 4-triangle nose on the face front. cfg (style "nose"): u (centre height),
    half_width, bottom (bottom vertex below the base), tip (protrusion), top (bridge
    height above the base)."""
    cfg = cfg if isinstance(cfg, dict) else {}
    u0 = cfg.get("u", 0.435)
    hw = cfg.get("half_width", 0.04)
    p = skull_surface(0.0, u0)
    n = surface_normal(0.0, u0)
    base = p - n * 0.01
    tip = p + n * cfg.get("tip", 0.045) + Vector((0, 0, -0.01))
    a = g.v(base + Vector((-hw, 0, 0.012)))
    b = g.v(base + Vector((hw, 0, 0.012)))
    c = g.v(base + Vector((0, 0, cfg.get("bottom", -0.03))))
    t = g.v(tip)
    top = g.v(base + Vector((0, 0, cfg.get("top", 0.06))))
    out = Vector((0, 1, 0))
    g.face([a, top, t], "skin", out + Vector((-0.5, 0, 0.3)))
    g.face([top, b, t], "skin", out + Vector((0.5, 0, 0.3)))
    g.face([a, t, c], "skin", out + Vector((-0.5, 0, -0.5)))
    g.face([t, b, c], "skin", out + Vector((0.5, 0, -0.5)))


def add_ears(g, cfg=None):
    """Ears as small closed wedges (front, back, rim on separate vertices) so they
    are visible from every side with backface culling. cfg: dict with theta (deg
    from the front), u (centre height), h (height), out (protrusion), w (depth)."""
    cfg = cfg if isinstance(cfg, dict) else {}
    th0 = cfg.get("theta", 90.0)
    uc = cfg.get("u", 0.50)
    h = cfg.get("h", 0.17)
    out = cfg.get("out", 0.085)
    w = cfg.get("w", 0.06)
    for side in (-1, 1):
        t = th0 * side
        p = skull_surface(t, uc)
        n = surface_normal(t, uc)
        n = Vector((n.x, n.y, 0)).normalized()
        back = Vector((0, -1, 0))
        up = Vector((0, 0, 1))
        # base on the skull (slightly sunk), outer rim tilted backward
        base_top = p - n * 0.01 + up * (h * 0.5)
        base_bot = p - n * 0.01 - up * (h * 0.45)
        out_top = p + n * out + back * (w * 0.8) + up * (h * 0.40)
        out_bot = p + n * (out * 0.85) + back * (w * 0.6) - up * (h * 0.30)
        thick = back * 0.025
        f_ids = [g.v(q) for q in (base_top, out_top, out_bot, base_bot)]
        b_ids = [g.v(q + thick) for q in (base_top, out_top, out_bot, base_bot)]
        front_dir = n * 0.4 + Vector((0, 1, 0))
        g.face(f_ids, "skin", front_dir)
        g.face(b_ids, "skin", -front_dir)
        # rim (top, outer, bottom edges)
        for a, b, d in ((0, 1, up + n * 0.3), (1, 2, n), (2, 3, -up + n * 0.3)):
            g.face([f_ids[a], f_ids[b], b_ids[b], b_ids[a]], "skin", d)


def build_full_head(spec, body_bvh=None):
    name, style = hair_style(spec)
    configure(style)
    g = build_head(style)
    add_fringe(g, style)
    add_drape(g, style, body_radius_fn(body_bvh))
    add_face_locks(g, style)
    add_nose(g, style.get("nose"))
    if style.get("ears"):
        add_ears(g, style.get("ears"))
    if "appearance" in spec:
        from sgl_likeness import add_hair_parts
        add_hair_parts(g, style, spec)
    head_parts = sgl_characters.get(spec, "head_parts")
    if head_parts:
        head_parts(g, style, spec)
    g.style_name = name
    return g


# ------------------------------------------------------------------ placement
class BoneFrame:
    """Maps head/torso space (l, f, u) to an object's mesh-local coordinates
    through a template bone (bone-local axes are x = up, y = front, z = left)."""

    def __init__(self, obj, arm, bone_name):
        b = arm.data.bones[bone_name]
        self.M = obj.matrix_world.inverted() @ arm.matrix_world @ b.matrix_local
        self.Minv = self.M.inverted()

    def to_local(self, p):
        return self.M @ Vector((p[2], p[1], p[0]))

    def from_local(self, co):
        q = self.Minv @ Vector(co)
        return Vector((q[2], q[1], q[0]))


def remove_group_geometry(obj, group_name):
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    deform = bm.verts.layers.deform.verify()
    gi = obj.vertex_groups[group_name].index
    doomed = [v for v in bm.verts if v[deform].get(gi, 0.0) > 0.4]
    bmesh.ops.delete(bm, geom=doomed, context="VERTS")
    bm.to_mesh(me)
    bm.free()
    return len(doomed)


def emit(geo, obj, group_name, frame, role_mats):
    """Append geo to obj, rigidly weighted to group_name, with planar face UVs."""
    me = obj.data
    slot = {role: smat.ensure_slot(obj, m) for role, m in role_mats.items()}
    bm = bmesh.new()
    bm.from_mesh(me)
    deform = bm.verts.layers.deform.verify()
    uvl = bm.loops.layers.uv.active or bm.loops.layers.uv.new("UVMap")
    gi = obj.vertex_groups[group_name].index
    # only vertices some face uses: helper points (raycast bases, unused rows) would
    # otherwise end up as loose vertices in the mesh
    used = {i for idx, _r in geo.faces for i in idx}
    bv = {}
    for i, p in enumerate(geo.verts):
        if i not in used:
            continue
        v = bm.verts.new(frame.to_local(p))
        v[deform][gi] = 1.0
        bv[i] = v
    rects = {k: FACE_LAYOUT[k] for k in ("eyes", "mouth")}
    dropped = []
    for idx, role in geo.faces:
        try:
            f = bm.faces.new([bv[i] for i in idx])
        except ValueError:
            # bmesh refuses a face whose vertex set already has a face (e.g. a
            # back face built from the same vertices): never lose geometry silently
            dropped.append((tuple(idx), role))
            continue
        f.material_index = slot[role]
        f.smooth = True
        rect = rects.get(role)
        for loop, i in zip(f.loops, idx):
            if rect is None:
                loop[uvl].uv = (0.5, 0.5)
            else:
                lc, uc, w, h = rect
                p = geo.verts[i]
                loop[uvl].uv = ((p.x - (lc - w / 2)) / w, (p.z - (uc - h / 2)) / h)
    bm.to_mesh(me)
    bm.free()
    if dropped:
        raise RuntimeError(f"emit into {obj.name}/{group_name}: {len(dropped)} faces could not be created "
                           f"(duplicate vertex sets): {dropped[:4]}")
    return geo.tri_count()


def find_eye_state(obj):
    for m in obj.data.materials:
        if m is None:
            continue
        for state, name in smat.EYE_MATERIALS.items():
            if m.name == name:
                return state
    return None


def head_targets():
    """(object, armature, group/bone) for every non-metal head mesh in the template."""
    out = [(bpy.data.objects["Mario Mesh"], bpy.data.objects["Mario"], "Head DL")]
    for o in bpy.data.objects:
        if o.type != "MESH" or o.parent is None or o.parent.type != "ARMATURE":
            continue
        name = o.name
        if (name.startswith("Head ") or name.startswith("Capless Head")) and name.endswith(" Mesh"):
            groups = [g.name for g in o.vertex_groups]
            if len(groups) != 1:
                raise RuntimeError(f"{name}: expected one vertex group, found {groups}")
            out.append((o, o.parent, groups[0]))
    return out


def body_bvh_head_space(body_obj, arm, frame_bone="Head DL", groups=("Torso", "Butt")):
    """BVH of the body's torso/butt faces in head space (rest pose)."""
    frame = BoneFrame(body_obj, arm, frame_bone)
    me = body_obj.data
    gidx = {body_obj.vertex_groups[n].index for n in groups if n in body_obj.vertex_groups}
    keep = set()
    for v in me.vertices:
        for gg in v.groups:
            if gg.group in gidx and gg.weight > 0.4:
                keep.add(v.index)
    verts = [frame.from_local(v.co) for v in me.vertices]
    polys = [list(p.vertices) for p in me.polygons if all(i in keep for i in p.vertices)]
    if not polys:
        return None
    return BVHTree.FromPolygons(verts, polys)


def replace_heads(spec, mats, body_bvh=None):
    """Replace the head in Mario Mesh and all head variant meshes. Returns stats."""
    geo = build_full_head(spec, body_bvh)
    stats = {"style": geo.style_name, "tris": geo.tri_count(), "meshes": []}
    head_roles = sgl_characters.get(spec, "head_roles")
    extra_roles = head_roles(spec, mats) if head_roles else {}
    for obj, arm, group in head_targets():
        state = find_eye_state(obj) or "open"
        roles = {"skin": mats["skin"], "hair": mats["hair"], "eyes": mats["eyes_" + state],
                 "mouth": mats["mouth"], **extra_roles}
        removed = remove_group_geometry(obj, group)
        emit(geo, obj, group, BoneFrame(obj, arm, group), roles)
        smat.compact_material_slots(obj)
        stats["meshes"].append((obj.name, state, removed))
    return stats
