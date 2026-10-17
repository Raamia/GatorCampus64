"""Alfred: short tight black curls piled high on top with tapered (faded) sides and nape,
thick straight brows (face art), big ears, a long straight nose; a sharp black suit with
notch lapels, a white collared shirt and a bright red tie with thin diagonal white stripes.

Only one reference photo (front, head and torso): the side and back of the hair are
inferred (curly volume all around the top, short faded hair behind the ears and at the nape).
"""
import math
import random

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

import sgl_heads as sh
import sgl_materials as smat
from sgl_body import bone_bvh, front_hit, radial_hit
from sgl_heads import BoneFrame, Geo, emit
from sgl_util import mix_hex

# ------------------------------------------------------------------ head / hair
# Head space (l, f, u). Skull = Daniel's oval face (the reviewed preset), with ring 2 a little
# higher (0.71) so the brow rows of the eye art (rows 6-9, u 0.638..0.687 with the eye rect
# below) sit well inside the eye band (band 1, ring 1 -> ring 2), and ring 0 narrower (0.26)
# for his long, narrow chin. The curly mass starts at ring 3 (the hairline, u 0.86); its
# volume per ring and direction is set in head_parts (_reshape_hair, HAIR_OFF): a wide,
# front-heavy mushroom of curls puffing out at the temples, with short tapered sides and nape.
HAIR_STYLE = {
    "window": 60,                       # columns at +-75 (temples) are hair from ring 2 up
    "face_bands": ("fan_bottom", 0, 1, 2),
    # base offsets (rings 2-4 and the top are reshaped per direction in head_parts)
    "off": {"top": 0.30, "upper": 0.18, "side": 0.0, "back": 0.0},
    "ring_off": {2: 0.05},
    "hang": False,
    "skull": [
        (0.00, 0.26, 0.36, 0.33, 0.06, 2.3),
        (0.36, 0.47, 0.50, 0.50, 0.03, 2.4),
        (0.71, 0.50, 0.48, 0.54, 0.00, 2.3),
        (0.86, 0.455, 0.41, 0.50, -0.02, 2.2),
        (0.97, 0.34, 0.29, 0.39, -0.03, 2.0),
    ],
    "bottom_pole": (0.0, 0.12, -0.13),
    "top_pole": (0.0, -0.03, 1.03),
    # eyes: Daniel's rect (the artist sized the art for it), 8% taller so the thick brows and
    # the eyes read a little bigger; the mouth a little lower (his lower face is long in the
    # photo), same horizontal texel size as the eyes
    "face_layout": {"eyes": (0.0, 0.565, 0.84, 0.39), "mouth": (0.0, 0.205, 0.42, 0.21)},
    # the curly mass comes down onto the forehead: a fringe flap from the crown edge (ring 3
    # hair) down to a softly scalloped hairline at u ~0.80 (a curl hangs lower just left of
    # centre, as in the photo), kept well above the brows (u 0.69); at +-60 it meets the
    # temple hair (column 75 is hair from ring 2 up)
    "fringe": {"kind": "full", "offset": 0.05, "lo_ring": 2,
               "edge": {-60: 0.75, -45: 0.795, -30: 0.815, -15: 0.80, 0: 0.79, 15: 0.78,
                        30: 0.815, 45: 0.80, 60: 0.755}},
    "locks": None,
    "drape": None,
    # temples (75): hair from ring 2 (u 0.71) up, like sideburns down to the ear tops;
    # behind the ears (105): from ring 1; back (135/165): from ring 0 (the nape), neck below.
    # Rings 0/1 have no offset: the tapered sides lie flat on the skull (seen from the front
    # they do not stick out beside the cheeks)
    "hair_bottom": {75: 2, 105: 1, 135: 0, 165: 0},
    # ears: built in head_parts (EAR), rounder and sticking out more than the stock wedge
    "ears": False,
    # long, prominent straight nose (photo1), narrower than Daniel's
    "nose": {"u": 0.385, "half_width": 0.066, "bottom": -0.045, "tip": 0.08, "top": 0.12},
}

# hair thickness per ring: (front, side, back) at 0 / 90 / 180 degrees, cosine-blended in
# between. Photo1: the curls puff out at the temples (forehead level, ring 3) to about 1.35x
# the face width and rise about 0.9-1.0x the brow-chin distance above the brows.
HAIR_OFF = {2: (0.055, 0.07, 0.035), 3: (0.165, 0.17, 0.10), 4: (0.20, 0.17, 0.15)}
TOP_HAIR = (0.0, 0.02, 1.19)   # the crown (a little forward of the skull's top pole)

# taper at the back (the default game camera looks at it): the nape band under ring 1 is
# hair mixed with HAIR_FADE_MIX skin; the band above it behind the ears and at the back
# (ring 1 -> ring 2, below the curls) is a lighter step of HAIR_TAPER_MIX
HAIR_FADE_MIX = 0.38
FADE_MAX_U = 0.38        # hair faces entirely below this height (the bands under ring 1) are the fade
HAIR_TAPER_MIX = 0.14
TAPER_MAX_U = 0.76       # hair faces entirely below this height ...
TAPER_MIN_THETA = 100.0  # ... and entirely behind this angle from the front are the taper

# curl clumps: (elevation from the head centre, count, azimuth offset, radius, height, back-arc limit)
_CURL_ROWS = [
    (90, 1, 0.0, 0.18, 0.06, None),
    (62, 5, 0.0, 0.185, 0.065, None),
    (34, 7, 25.7, 0.18, 0.065, None),
    (12, 3, 0.0, 0.16, 0.05, 135.0),     # lower back of the crown only (|azimuth| >= 135)
]
CURL_COLOUR_MIX = 0.07   # curl clumps: hair lifted toward a warm grey (their sheen in the photo)
# clump shape: a dome, not a peak. A base ring of CURL_SIDES points on the hair surface, a
# raised top ring of CURL_TOP points (CURL_TOP_R of the radius, CURL_TOP_H of the height,
# turned half a step), closed by a flat cap or, with CURL_APEX, a low apex. Smooth shading
# then reads as a round ringlet.
CURL_SIDES = 6
CURL_TOP = 3
CURL_TOP_R = 0.55
CURL_TOP_H = 0.85
CURL_APEX = False
CURL_RADIAL = 1.5      # weight of the radial direction in the dome's axis (see _lump)
CURL_MAX_DROP = 0.075   # base points never drop further than this below the clump's tangent plane


# ears (photo: big, sticking out, from eye level down to below the nose tip): a flap hinged
# on the skull at the front edge and swung out by "angle"; outline in (back, up) fractions
EAR = {"theta": 92.0, "u": 0.43, "h": 0.29, "w": 0.19, "angle": 48.0, "thick": 0.024}
_EAR_OUTLINE = [(0.0, 0.42), (0.30, 0.53), (0.74, 0.42), (1.0, 0.12), (0.92, -0.20), (0.58, -0.45), (0.14, -0.50)]


def _add_ears(g):
    up = Vector((0, 0, 1))
    for side in (-1, 1):
        t = EAR["theta"] * side
        uc = EAR["u"]
        p = sh.skull_surface(t, uc)
        n = sh.surface_normal(t, uc)
        n = Vector((n.x, n.y, 0)).normalized()
        back = up.cross(n) if up.cross(n).y < 0 else n.cross(up)
        a = math.radians(EAR["angle"])
        along = (back * math.cos(a) + n * math.sin(a)).normalized()
        flap_n = along.cross(up)
        if flap_n.y < 0:           # the front face looks forward and out
            flap_n = -flap_n
        root = p - n * 0.012
        front = [root + along * (x * EAR["w"]) + up * (y * EAR["h"]) for x, y in _EAR_OUTLINE]
        f_ids = [g.v(q) for q in front]
        b_ids = [g.v(q - flap_n * EAR["thick"]) for q in front]
        g.face(f_ids, "skin", flap_n)
        g.face(b_ids, "skin", -flap_n)
        # rim along the outer edge (the part seen from the side / behind)
        for k in range(1, len(front) - 2):
            mid = (front[k] + front[k + 1]) / 2
            g.face([f_ids[k], f_ids[k + 1], b_ids[k + 1], b_ids[k]], "skin", mid - (root + along * 0.4 * EAR["w"]))


def _hair_off(k, theta):
    front, side, back = HAIR_OFF[k]
    c = math.cos(math.radians(theta))
    w = abs(c) ** 0.8
    return side + ((front if c >= 0 else back) - side) * w


def _shell_ids(g):
    """The head builder's hair/face vertex maps {(ring, column): vertex id} (attributes
    sgl_heads.build_head sets on its Geo; add_fringe/add_drape use them the same way)."""
    hair, face = getattr(g, "hair_vid", None), getattr(g, "face_vid", None)
    if hair is None or face is None:
        raise RuntimeError("alfred: sgl_heads.build_head no longer provides Geo.hair_vid/face_vid; "
                           "update characters/alfred.py (_reshape_hair)")
    return hair, face


def _reshape_hair(g):
    """Front-heavy curly volume: rings 2-4 of the hair shell pushed out by HAIR_OFF (thick
    over the forehead and on top, thinner toward the tapered back), the crown at TOP_HAIR.
    The fringe and the hairline strips share these vertices, so they follow. Rings 2+ are
    pushed straight away from the head centre (as sgl_heads does above the widest ring)."""
    hair, face = _shell_ids(g)
    for (k, i), vid in hair.items():
        if k == "top":
            g.verts[vid] = Vector(TOP_HAIR)
            continue
        if k not in HAIR_OFF or face.get((k, i)) == vid:
            continue
        theta = sh.THETAS[i]
        p = sh.ring_point(k, theta)
        d = p - sh.HEAD_CENTER
        g.verts[vid] = p + d.normalized() * _hair_off(k, theta)


def _hair_bvh(g, roles=("hair",)):
    """BVH of the head faces with these roles (None: every face, skin included)."""
    polys = [list(idx) for idx, role in g.faces if roles is None or role in roles]
    return BVHTree.FromPolygons([Vector(v) for v in g.verts], polys)


def _zip_rings(g, lo, hi, a_lo, a_hi, role, inner):
    """Triangles between two closed rings of vertex ids (angles a_lo / a_hi, increasing):
    walk both rings by angle, always advancing the one whose next vertex comes first."""
    n, m = len(lo), len(hi)
    i = j = 0
    while i < n or j < m:
        ni = a_lo[(i + 1) % n] + (2 * math.pi if i + 1 >= n else 0.0)
        nj = a_hi[(j + 1) % m] + (2 * math.pi if j + 1 >= m else 0.0)
        if j >= m or (i < n and ni <= nj):
            tri = [lo[i % n], lo[(i + 1) % n], hi[j % m]]
            i += 1
        else:
            tri = [lo[i % n], hi[(j + 1) % m], hi[j % m]]
            j += 1
        cen = sum((g.verts[t] for t in tri), Vector()) / 3
        g.face(tri, role, cen - inner)


def _lump(g, bvh, bvh_all, centre, dirv, r, h, spin=0.0, sink=0.012, role="hair"):
    """Round low dome sitting on the hair surface where the ray from outside along -dirv
    first hits it: a base ring of CURL_SIDES points (sunk a little into the shell), a top
    ring of CURL_TOP points turned half a step, then a flat cap or a low apex. Returns the hit."""
    loc, nor, _i, _d = bvh.ray_cast(centre + dirv * 3.0, -dirv, 3.0)
    if loc is None:
        return None
    if nor.dot(dirv) < 0:
        nor = -nor
    # orient the dome between the face normal and the radial direction: on the shell's
    # edges (the fringe's front corner) the face normal alone tips the dome into a spike
    nor = (nor + dirv * CURL_RADIAL).normalized()
    up = Vector((0, 0, 1)) if abs(nor.z) < 0.95 else Vector((0, 1, 0))
    t1 = nor.cross(up).normalized()
    t2 = nor.cross(t1).normalized()
    n, m = CURL_SIDES, CURL_TOP
    a_lo = [spin + 2 * math.pi * k / n for k in range(n)]
    a_hi = [spin + 2 * math.pi * (k + 0.5) / m for k in range(m)]
    def base_points(rad):
        pts = []
        for a in a_lo:
            p = loc + (t1 * math.cos(a) + t2 * math.sin(a)) * rad
            # onto the outer hair surface toward the head centre (follows the curvature;
            # a ray along -nor runs far down the side of a strongly curved bulge)
            d = (p - centre).normalized()
            # (bvh_all: a rim point past the fringe's edge lands on the forehead, not
            # through it on the back of the hair)
            hit = bvh_all.ray_cast(centre + d * 3.0, -d, 3.0)
            q = hit[0] if hit[0] is not None else p
            pts.append((q, (p - q).dot(nor)))
        return pts

    # on a strongly curved spot (the temple bulge) a smaller clump keeps its rim on the hair
    for _try in range(3):
        pts = base_points(r)
        if max(dr for _q, dr in pts) <= CURL_MAX_DROP:
            break
        r *= 0.82
    base = []
    for q, drop in pts:
        if drop > CURL_MAX_DROP:
            print(f"SGL alfred curl: rim point lifted ({drop:.3f} below the tangent plane) at "
                  f"{tuple(round(c, 2) for c in loc)}")
            q = q + nor * (drop - CURL_MAX_DROP)
        base.append(g.v(q - nor * sink))
    top = [g.v(loc + (t1 * math.cos(a) + t2 * math.sin(a)) * (r * CURL_TOP_R) + nor * (h * CURL_TOP_H))
           for a in a_hi]
    inner = loc - nor * 0.3
    _zip_rings(g, base, top, a_lo, a_hi, role, inner)
    if CURL_APEX:
        apex = g.v(loc + nor * h)
        for k in range(m):
            g.face([apex, top[k], top[(k + 1) % m]], role, nor)
    else:
        g.face(top, role, nor)
    return loc


def head_parts(g, style, spec):
    """Front-heavy curly volume, protruding ears, round curl domes all over the top (a bumpy
    silhouette; slightly lighter than the hair, so they read as tight curls with a sheen) and
    the tapered back recoloured (fade at the nape, a lighter taper step above it)."""
    _reshape_hair(g)
    _add_ears(g)
    centre = sh.HEAD_CENTER
    bvh = _hair_bvh(g)
    bvh_all = _hair_bvh(g, None)
    rng = random.Random(11)
    for elev, count, az0, r, h, limit in _CURL_ROWS:
        for k in range(count):
            az = az0 + 360.0 * k / count + rng.uniform(-6, 6)
            if limit is not None:   # spread the row over the back arc only
                az = 180.0 + (k - (count - 1) / 2) * (360.0 - 2 * limit) / max(1, count - 1) + rng.uniform(-5, 5)
            el = elev + (rng.uniform(-4, 4) if elev < 90 else 0.0)
            t, e = math.radians(az), math.radians(el)
            d = Vector((math.sin(t) * math.cos(e), math.cos(t) * math.cos(e), math.sin(e)))
            _lump(g, bvh, bvh_all, centre, d, r * rng.uniform(0.9, 1.1), h * rng.uniform(0.85, 1.15),
                  spin=rng.uniform(0, 1.0), role="curl")
    # tapered back: the hair faces below ring 1 are the fade, the band above it behind the
    # ears and at the back (below the curls) the lighter taper step
    for n, (idx, role) in enumerate(g.faces):
        if role != "hair":
            continue
        if max(g.verts[i].z for i in idx) <= FADE_MAX_U:
            g.faces[n] = (idx, "hair_fade")
        elif HAIR_TAPER_MIX > 0 and max(g.verts[i].z for i in idx) <= TAPER_MAX_U and \
                min(abs(math.degrees(math.atan2(g.verts[i].x, g.verts[i].y))) for i in idx) >= TAPER_MIN_THETA:
            g.faces[n] = (idx, "hair_taper")


def head_roles(spec, mats):
    pal = mats["_palette"]
    fade = mix_hex(pal["hair"], pal["skin"], HAIR_FADE_MIX)
    curl = mix_hex(pal["hair"], "#8A7A74", CURL_COLOUR_MIX)
    taper = mix_hex(pal["hair"], pal["skin"], HAIR_TAPER_MIX)
    return {"hair_fade": smat.accessory_material(mats, "hair_fade", fade, base="Hair (HAIR)"),
            "hair_taper": smat.accessory_material(mats, "hair_taper", taper, base="Hair (HAIR)"),
            "curl": smat.accessory_material(mats, "hair_curl", curl, base="Hair (HAIR)")}


# ------------------------------------------------------------------ suit (Torso bone frame)
# Torso frame (l, f, u): the chin meets the chest at about u 0.33 (the head's fan sinks into
# the chest above that), the neck top is u 0.47, the belly is deepest at u 0.02 (f 0.417).
V_TOP = 0.37       # top of the shirt V (under the chin)
V_BOT = -0.09      # where the lapels meet (jacket button)
V_HALF = 0.165     # half width of the V at V_TOP


def _v_half(u):
    return V_HALF * (u - V_BOT) / (V_TOP - V_BOT)


def _on(bvh, l, u, off):
    loc, n = front_hit(bvh, l, u)
    if loc is None:
        return None
    return loc + n * off


def _need(p, what):
    if p is None:
        raise RuntimeError(f"alfred suit: torso surface not found for {what}")
    return p


# lapel faces a touch lighter than the jacket (the spec's black suit, #1C1B1F, is one dark
# silhouette at game size otherwise); 0 = same material as the jacket
LAPEL_LIFT = 0.10
LAPEL_SHEEN = "#A09EA8"
LAPEL_PEAK = (0.315, 0.265)   # (outer l, u) of the lapel peak just under the notch
U_HEM = -0.35                 # jacket hem (just above where the seat curves under)


def _lapel_outer(u):
    """Outer lapel edge below the peak: a slightly convex line from the peak to the button."""
    lp, up = LAPEL_PEAK
    return lp * max(0.0, (u - V_BOT) / (up - V_BOT)) ** 0.8


def add_suit_lapels_white_shirt_v(ctx):
    """Suit jacket front: a white shirt V between two notch lapels (raised and slanted
    toward the V so their edge catches the light), shirt collar points beside the tie knot,
    the jacket fronts parting below the button, a hem around the seat, white shirt cuffs."""
    obj, arm, mats = ctx["obj"], ctx["arm"], ctx["mats"]
    pal = mats["_palette"]
    bvh, frame = bone_bvh(obj, arm, "Torso", ["Torso", "Butt"])
    g = Geo()
    fwd = Vector((0, 1, 0))
    up = Vector((0, 0, 1))
    # ---- shirt plate: the V, tucked under the lapels and up under the chin. Rows 0.05 apart
    # and 0.012 off the surface: on the curved chest a coarser plate sinks into the torso
    rows = [0.43, 0.40, V_TOP, 0.32, 0.27, 0.22, 0.17, 0.12, 0.07, 0.02, -0.03, V_BOT - 0.01]
    plate = []
    for u in rows:
        hw = _v_half(min(u, V_TOP)) + 0.035
        plate.append([g.v(_need(_on(bvh, l, u, 0.012), "shirt")) for l in (-hw, 0.0, hw)])
    for r0, r1 in zip(plate, plate[1:]):
        for c in range(2):
            g.face([r0[c], r0[c + 1], r1[c + 1], r1[c]], "shirt", fwd)
    # ---- lapels: (u, outer l) rows; the inner edge is on the V line, the notch at u 0.285
    prof = [(V_TOP + 0.02, 0.275), (0.30, 0.29), (0.285, 0.225), LAPEL_PEAK[::-1]]
    prof += [(u, _lapel_outer(u)) for u in (0.21, 0.16, 0.105, 0.05, 0.0, -0.045)]
    for s in (-1, 1):
        ins, outs, ins_b, outs_b = [], [], [], []
        for u, lo in prof:
            li = _v_half(min(u, V_TOP))
            ins.append(g.v(_need(_on(bvh, s * li, u, 0.036), "lapel")))
            outs.append(g.v(_need(_on(bvh, s * lo, u, 0.016), "lapel")))
            ins_b.append(g.v(_need(_on(bvh, s * li, u, -0.004), "lapel")))
            outs_b.append(g.v(_need(_on(bvh, s * lo, u, -0.004), "lapel")))
        tip = g.v(_need(_on(bvh, 0.0, V_BOT, 0.026), "lapel tip"))
        tip_b = g.v(_need(_on(bvh, 0.0, V_BOT, -0.004), "lapel tip"))
        side = Vector((s, 0, 0))
        for k in range(len(prof) - 1):
            g.face([ins[k], outs[k], outs[k + 1], ins[k + 1]], "lapel", fwd + side * 0.3)
            g.face([ins[k], ins[k + 1], ins_b[k + 1], ins_b[k]], "top", fwd * 0.3 - side)
            g.face([outs[k], outs[k + 1], outs_b[k + 1], outs_b[k]], "top", fwd * 0.3 + side)
        g.face([ins[-1], outs[-1], tip], "lapel", fwd + side * 0.3)
        g.face([ins[-1], tip, tip_b, ins_b[-1]], "top", fwd * 0.3 - side)
        g.face([outs[-1], tip, tip_b, outs_b[-1]], "top", fwd * 0.3 + side - up * 0.5)
        # top of the collar part (seen from above, beside the chin)
        g.face([ins[0], outs[0], outs_b[0], ins_b[0]], "top", fwd * 0.2 + up)
    # ---- shirt collar points beside the knot
    for s in (-1, 1):
        pts = [(0.035, 0.335, 0.030), (0.135, 0.345, 0.030), (0.098, 0.215, 0.022), (0.04, 0.262, 0.024)]
        top = [g.v(_need(_on(bvh, s * l, u, off), "collar")) for l, u, off in pts]
        bot = [g.v(_need(_on(bvh, s * l, u, 0.004), "collar")) for l, u, _o in pts]
        g.face(top, "shirt", fwd)
        side = Vector((s, 0, 0))
        g.face([top[1], top[2], bot[2], bot[1]], "shirt", side + fwd * 0.3)
        g.face([top[2], top[3], bot[3], bot[2]], "shirt", -side * 0.5 - up)
    # ---- jacket fronts parting below the button: a raised edge curving out to the hem
    edge = [(0.0, V_BOT), (0.05, -0.15), (0.12, -0.215), (0.20, -0.265), (0.28, -0.305), (0.34, U_HEM + 0.005)]
    for s in (-1, 1):
        lip, wall = [], []
        for l, u in edge:
            loc, n = front_hit(bvh, s * l, u)
            _need(loc, "jacket front")
            lip.append(g.v(loc + n * 0.024))
            wall.append(g.v(loc - n * 0.004))
        # the open side is toward the centre line / below the curve
        for k in range(len(edge) - 1):
            mid = (g.verts[lip[k]] + g.verts[lip[k + 1]]) / 2
            out = Vector((-s, 0.0, -1.0)) if k else Vector((-s, 0.0, -0.3))
            g.face([lip[k], lip[k + 1], wall[k + 1], wall[k]], "top", out + fwd * 0.4)
            # sloped top of the lip back down onto the jacket panel
            back = [g.v(_need(_on(bvh, s * (l + 0.035), u + 0.03, -0.004), "jacket front"))
                    for l, u in (edge[k], edge[k + 1])]
            g.face([lip[k], lip[k + 1], back[1], back[0]], "top", fwd + up * 0.5 + Vector((s * 0.3, 0, 0)))
    # ---- jacket collar around the back of the neck (under the nape), the white shirt collar
    # showing as a thin band along its top edge; it runs into the lapels' collar parts
    arc = [62 + k * 236.0 / 10 for k in range(11)]
    cols = []
    for t in arc:
        b = (1 - math.cos(math.radians(t))) / 2          # 0 front .. 1 back
        u0 = 0.30 + 0.05 * (1 - b)
        lo, n_lo = radial_hit(bvh, t, u0)
        hi, n_hi = radial_hit(bvh, t, u0 + 0.07)
        if lo is None or hi is None:
            raise RuntimeError(f"alfred suit: neck not found at theta {t}")
        rad = Vector((hi.x, hi.y, 0)).normalized()
        top = hi + rad * 0.03
        cols.append([g.v(lo + n_lo * 0.004), g.v(top), g.v(top + up * 0.022 - rad * 0.006),
                     g.v(hi + up * 0.03 - rad * 0.02)])
    for a, b in zip(cols, cols[1:]):
        m = (g.verts[a[1]] + g.verts[b[1]]) / 2
        rad = Vector((m.x, m.y, 0)).normalized()
        g.face([a[0], b[0], b[1], a[1]], "top", rad + up * 0.2)
        g.face([a[1], b[1], b[2], a[2]], "shirt", rad + up * 0.3)
        g.face([a[2], b[2], b[3], a[3]], "shirt", up + rad * 0.3)
    roles = {"top": mats["top"],
             "lapel": mats["top"] if LAPEL_LIFT <= 0 else
             smat.accessory_material(mats, "lapel", mix_hex(pal["top"], LAPEL_SHEEN, LAPEL_LIFT)),
             "shirt": smat.accessory_material(mats, "shirt", pal.get("shirt", "#F4F2F6"))}
    tris = emit(g, obj, "Torso", frame, roles)
    tris += jacket_hem(ctx, bvh, frame)
    return tris


def jacket_hem(ctx, bvh, frame_t):
    """Hem of the jacket around the sides and back of the seat (rigid on the Butt bone):
    a short flared band whose dark underside separates jacket and trousers."""
    obj, arm, mats = ctx["obj"], ctx["arm"], ctx["mats"]
    frame_b = BoneFrame(obj, arm, "Butt")
    g = Geo()
    up = Vector((0, 0, 1))
    thetas = [72 + k * 216.0 / 12 for k in range(13)]   # 72 .. 288 through the back
    cols = []
    for t in thetas:
        hi, n_hi = radial_hit(bvh, t, U_HEM + 0.075)
        lo, n_lo = radial_hit(bvh, t, U_HEM)
        if hi is None or lo is None:
            print(f"SGL WARNING: alfred jacket hem: body not found at theta {t}")
            return 0
        rad = Vector((lo.x, lo.y, 0)).normalized()
        cols.append([hi + n_hi * 0.004, lo + rad * 0.032 - up * 0.01, lo + up * 0.012 - rad * 0.004])
    ids = [[g.v(frame_b.from_local(frame_t.to_local(p))) for p in c] for c in cols]
    for k in range(len(cols) - 1):
        a, b = ids[k], ids[k + 1]
        rad = Vector((cols[k][1].x + cols[k + 1][1].x, cols[k][1].y + cols[k + 1][1].y, 0)).normalized()
        g.face([a[0], b[0], b[1], a[1]], "top", rad + up * 0.3)
        g.face([a[1], b[1], b[2], a[2]], "top", rad * 0.3 - up)
    return emit(g, obj, "Butt", frame_b, {"top": mats["top"]})


SHIRT_CUFFS = True
CUFF_WHITE_U = 0.0   # cuff faces nearer the fist than this (hand bone frame) are the shirt cuff


def shirt_cuffs(ctx):
    """The sleeve cuffs (Mario's glove cuffs, made sleeve-coloured by sgl_body.sleeve_cuffs)
    become white shirt cuffs peeking out of the jacket sleeves, in every hand mesh (not the
    metal ones: rebuild_metal runs after post_build). Returns the number of faces recoloured."""
    if not SHIRT_CUFFS:
        return 0
    mats = ctx["mats"]
    shirt = smat.accessory_material(mats, "shirt", mats["_palette"].get("shirt", "#F4F2F6"))
    top = mats["top"]
    n = 0
    for o in bpy.data.objects:
        if o.type != "MESH" or o.parent is None or o.parent.type != "ARMATURE" or o.name.startswith("Metal"):
            continue
        if top.name not in [m.name for m in o.data.materials if m]:
            continue
        arm = o.parent
        me = o.data
        ti = [i for i, m in enumerate(me.materials) if m == top]
        hand = [g.index for g in o.vertex_groups if "Hand" in g.name and g.name in arm.data.bones]
        if not hand:
            continue
        vs = {v.index for v in me.vertices if any(gg.group in hand and gg.weight > 0.4 for gg in v.groups)}
        faces = [p for p in me.polygons if p.material_index in ti and all(i in vs for i in p.vertices)]
        if not faces:
            continue
        si = smat.ensure_slot(o, shirt)
        frames = {g.index: BoneFrame(o, arm, g.name) for g in o.vertex_groups if g.index in hand}
        for p in faces:
            # the hand group this face belongs to (Mario Mesh has both hands)
            gi = max(hand, key=lambda h: sum(1 for i in p.vertices
                                             for gg in me.vertices[i].groups if gg.group == h and gg.weight > 0.4))
            fr = frames[gi]
            u = sum(fr.from_local(me.vertices[i].co).z for i in p.vertices) / len(p.vertices)
            if u > CUFF_WHITE_U:
                p.material_index = si
                n += 1
        smat.compact_material_slots(o)
    print(f"SGL alfred: {n} cuff faces -> shirt")
    return n


TIE_STRIPES = 7            # thin white "/" stripes on the blade (left edge heights below)
TIE_STRIPE_U0 = -0.03      # lowest stripe starts here on the blade's right-hand (-l) edge
TIE_STRIPE_STEP = 0.04
TIE_STRIPE_SLOPE = 1.28    # du / dl: tan(52 deg), the stripe angle measured on photo1
TIE_STRIPE_TH = 0.0125     # vertical thickness (about 0.008 across the stripe)


def _tie_half(u):
    """Half width of the tie blade at height u (0.255 under the knot .. -0.035)."""
    pts = [(0.255, 0.026), (0.17, 0.032), (0.08, 0.038), (0.0, 0.043), (-0.035, 0.043)]
    if u >= pts[0][0]:
        return pts[0][1]
    for (u0, w0), (u1, w1) in zip(pts, pts[1:]):
        if u1 <= u <= u0:
            return w0 + (w1 - w0) * (u0 - u) / (u0 - u1)
    return pts[-1][1]


def add_red_tie(ctx):
    """Red tie: a raised knot under the chin and a blade widening to a pointed tip,
    with thin diagonal white stripes ("/" seen from the front, as in the photo)."""
    obj, arm, mats = ctx["obj"], ctx["arm"], ctx["mats"]
    pal = mats["_palette"]
    bvh, frame = bone_bvh(obj, arm, "Torso", ["Torso", "Butt"])
    g = Geo()
    fwd = Vector((0, 1, 0))
    up = Vector((0, 0, 1))
    # ---- knot
    kt, kb = 0.318, 0.255
    knot = [(-0.038, kt), (0.038, kt), (0.027, kb), (-0.027, kb)]
    ktop = [g.v(_need(_on(bvh, l, u, 0.046), "knot")) for l, u in knot]
    kbot = [g.v(_need(_on(bvh, l, u, 0.004), "knot")) for l, u in knot]
    g.face(ktop, "tie", fwd)
    for a, d in ((0, up), (1, Vector((1, 0, 0))), (2, -up), (3, Vector((-1, 0, 0)))):
        b = (a + 1) % 4
        g.face([ktop[a], ktop[b], kbot[b], kbot[a]], "tie", d + fwd * 0.3)
    # ---- blade
    us = [kb, 0.17, 0.08, 0.0, -0.035]
    lift = 0.03
    L, R, Lb, Rb = [], [], [], []
    for u in us:
        hw = _tie_half(u)
        L.append(g.v(_need(_on(bvh, -hw, u, lift), "tie")))
        R.append(g.v(_need(_on(bvh, hw, u, lift), "tie")))
        Lb.append(g.v(_need(_on(bvh, -hw, u, 0.006), "tie")))
        Rb.append(g.v(_need(_on(bvh, hw, u, 0.006), "tie")))
    tip_u = -0.075
    tip = g.v(_need(_on(bvh, 0.0, tip_u, lift), "tie tip"))
    tip_b = g.v(_need(_on(bvh, 0.0, tip_u, 0.006), "tie tip"))
    for k in range(len(us) - 1):
        g.face([L[k], R[k], R[k + 1], L[k + 1]], "tie", fwd)
        g.face([L[k], L[k + 1], Lb[k + 1], Lb[k]], "tie", Vector((-1, 0.3, 0)))
        g.face([R[k], R[k + 1], Rb[k + 1], Rb[k]], "tie", Vector((1, 0.3, 0)))
    g.face([L[-1], R[-1], tip], "tie", fwd)
    g.face([L[-1], tip, tip_b, Lb[-1]], "tie", Vector((-1, 0.3, -1)))
    g.face([R[-1], tip, tip_b, Rb[-1]], "tie", Vector((1, 0.3, -1)))
    # ---- stripes: thin "/" bands across the blade, rising toward the character's left (+l)
    # at about 52 degrees as in the photo; the top ones are cut off along the knot
    ucap = kb - 0.004
    for k in range(TIE_STRIPES):
        u0 = TIE_STRIPE_U0 + k * TIE_STRIPE_STEP
        hwa = _tie_half(u0) * 0.97
        u1 = u0
        for _ in range(3):              # where the stripe's lower line meets the right edge
            u1 = u0 + TIE_STRIPE_SLOPE * (hwa + _tie_half(u1) * 0.97)
        hwb = _tie_half(u1) * 0.97
        th = TIE_STRIPE_TH
        if u0 + th >= ucap:
            continue
        if u1 + th <= ucap:
            poly = [(-hwa, u0), (hwb, u1), (hwb, u1 + th), (-hwa, u0 + th)]
        elif u1 <= ucap:
            # only the upper line reaches the knot
            poly = [(-hwa, u0), (hwb, u1), (hwb, ucap), (-hwa + (ucap - u0 - th) / TIE_STRIPE_SLOPE, ucap),
                    (-hwa, u0 + th)]
        else:
            poly = [(-hwa, u0), (-hwa + (ucap - u0) / TIE_STRIPE_SLOPE, ucap),
                    (-hwa + (ucap - u0 - th) / TIE_STRIPE_SLOPE, ucap), (-hwa, u0 + th)]
        pts = [_on(bvh, l, u, lift + 0.005) for l, u in poly]
        if any(p is None for p in pts):
            continue
        g.face([g.v(p) for p in pts], "tie_pattern", fwd)
    roles = {"tie": smat.accessory_material(mats, "tie", pal.get("tie", "#E0303A")),
             "tie_pattern": smat.accessory_material(mats, "tie_pattern", pal.get("tie_pattern", "#F4F2F6"))}
    return emit(g, obj, "Torso", frame, roles)


def post_build(ctx):
    """Whole-model passes after the body, accessories and heads are built."""
    return {"shirt_cuff_faces": shirt_cuffs(ctx)}


ACCESSORIES = {
    "suit_lapels_white_shirt_v": add_suit_lapels_white_shirt_v,
    "red_tie": add_red_tie,
}
