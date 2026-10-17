"""Raami: a big cloud of tight black curls (wider than the head) with curls falling
over the forehead to his thick brows, long face and nose, slate blue crewneck
sweatshirt with a ribbed collar, black pants, white sneakers.

Hair = the shared shell (big offsets, lumpy, side hair dropped to the ear tops and
pulled in, back hairline raised to the nape, flatter top) + the shared fringe flap
(bulging, down to just above the brows, tucked in at the temples) + low-poly curl
clumps (blunt 5/4-sided pyramids whose base corners are dropped onto the hair surface,
in a curl colour a little lighter and warmer than the hair, derived from colors.hair):
laid on the hair surface by raycasts, a row right on the crown/fringe crease (so the
fringe does not read as a beret brim), a few over the fringe, and round curls hanging below the fringe edge at irregular heights
(one lock dips over the inner end of his right brow, as in photo 2), over the ear tops
(closed) and at the nape. Head about 461 tris (Daniel 314); the whole body stays below
Daniel's 1293.

Also: crewneck sweatshirt (ribbed collar + hip-length body with a ribbed hem) when
outfit.top says crewneck, and the wing-cap wings moved out of the curls (post_build:
the wing BONES move with the wing vertices, so the flap hinge stays at the wing root).

Shared helpers this module relies on are checked up front (_require) so a refactor of
sgl_heads / sgl_body fails with a clear message instead of a silent wrong build.
"""
import math

from mathutils import Vector
from mathutils.bvhtree import BVHTree

import sgl_body
import sgl_heads as H
import sgl_materials as smat
from sgl_util import mix_hex

# ------------------------------------------------------------------ head + hair style
HAIR_STYLE = {
    "base": "tight_curls_voluminous_with_curly_fringe",
    "window": 90, "face_bands": ("fan_bottom", 0, 1, 2),
    "off": {"top": 0.28, "upper": 0.27, "side": 0.25, "back": 0.25},
    "ring_off": {0: 0.17, 1: 0.21},
    "hang": False,
    # long oval face, narrow jaw, long chin; ring 2 (u 0.72) sits just above the brows
    # (texture rows 5-8 = u 0.69-0.64 with the eye rect below), so the whole brow band
    # is on the eye material
    "skull": [
        (-0.04, 0.34, 0.35, 0.33, 0.07, 2.8),
        (0.36, 0.45, 0.50, 0.50, 0.03, 2.4),
        (0.72, 0.50, 0.48, 0.54, 0.00, 2.3),
        (0.90, 0.46, 0.41, 0.50, -0.02, 2.2),
        (1.02, 0.34, 0.29, 0.39, -0.03, 2.0),
    ],
    "bottom_pole": (0.0, 0.12, -0.13),
    "top_pole": (0.0, -0.03, 1.08),
    # eyes: square texels, 64 texels over 0.86; row 5 (brow top) at u 0.693, iris
    # centre (row 15.5) at u 0.552, eye bottom (row 20) at u 0.478
    # mouth: wide (content 26/32 of 0.48 = 0.39, about the pupil distance), lip line u 0.20
    "face_layout": {"eyes": (0.0, 0.545, 0.86, 0.43), "mouth": (0.0, 0.20, 0.48, 0.24)},
    # the flap edge is a little uneven (lower on his left of centre, higher at his right
    # temple); the curls hanging below it (FRINGE_TIPS) make the visible ragged edge
    "fringe": {"kind": "full", "offset": 0.08, "offset_mid": 0.26, "mid_at": 0.55, "lo_ring": 1,
               "edge": {-90: 0.56, -60: 0.675, -30: 0.745, 0: 0.765, 30: 0.75, 60: 0.65, 90: 0.56}},
    # beside the ears the hair starts at ring 2 (the ear stays visible below the curls
    # hanging over its top); the back of the head is covered down to ring 0 (nape)
    "hair_bottom": {105: 2, 135: 0, 165: 0},
    "drape": None, "locks": None,
    "ears": {"theta": 97, "u": 0.45, "h": 0.22, "out": 0.11, "w": 0.08},
    # long straight nose: bridge from between the eyes (u 0.495), wings and tip low (u 0.34)
    "nose": {"u": 0.345, "half_width": 0.07, "bottom": -0.035, "tip": 0.068, "top": 0.15},
}

CLOUD_CENTER = Vector((0.0, -0.04, 0.80))
# lumpy shell: hair vertex offset scaled by these in a checker pattern
LUMP = (0.86, 1.10)

# curl clumps on the hair surface, cast toward CLOUD_CENTER:
# (azimuth deg (0 front, 90 his left), elevation deg, radius)
SURFACE_CLUMPS = (
    [(10.0, 86.0, 0.15)]
    + [(a, 62.0, 0.15) for a in (0, 60, 120, 180, 240, 300)]
    + [(a, 36.0, 0.16 if 140 < a < 220 else 0.15) for a in (32, 75, 118, 160, 200, 242, 285, 328)]
    + [(a, 12.0, 0.17 if 120 < a < 240 else 0.15) for a in (62, 98, 135, 180, 225, 262, 298)]
    # the back is what the game camera sees most: bigger, denser curls there
    + [(a, -6.0, 0.16) for a in (157, 203)] + [(180.0, -24.0, 0.16)]
)
# clumps at the sides near brim level read as sideways spikes in the front view:
# their axis is tilted down and they are a little flatter
SIDE_TILT = (45.0, 135.0, 25.0, 0.55, 0.8)  # |az| range, max elevation, downward tilt, height scale
# a row of curls right on the crease where the fringe flap meets the crown (ring 3):
# (theta, radius); placed on the lumpy ring-3 hair line itself
CREASE_CLUMPS = [(-62.0, 0.13), (-37.0, 0.14), (-12.0, 0.14), (13.0, 0.14), (38.0, 0.14), (62.0, 0.13)]
# curls over the forehead, cast along the skull normal at (theta, u): (theta, u, radius, droop)
FRINGE_CLUMPS = [(t, 0.83, 0.115, 0.35) for t in (-24.0, 0.0, 25.0)]
# round curls hanging below the hair edge, facing out (a pentagon outline, not a spike):
# (theta, u of the lowest point, radius, distance of the centre out from the skull).
# Irregular heights, as in photo 2: most stop at the brow top (u 0.693) or a little above,
# the lock at -12 dips over the inner end of his right brow (rows 5-7 of the brow, the
# lower edge stays visible), the outer ones hang down the temples
FRINGE_TIPS = [(-63.0, 0.60, 0.08, 0.07), (-46.0, 0.705, 0.075, 0.075), (-30.0, 0.68, 0.085, 0.08),
               (-12.0, 0.648, 0.09, 0.085), (14.0, 0.685, 0.08, 0.08),
               (32.0, 0.712, 0.08, 0.075), (49.0, 0.67, 0.075, 0.075), (64.0, 0.60, 0.08, 0.07)]
# over the tops of the ears (ear 0.34..0.56, its top third covered), behind the ears and
# at the nape (the raised back hairline, see NAPE_LIFT): mirrored to both sides
HANG_CLUMPS = [(102.0, 0.51, 0.10, 0.16),
               (124.0, 0.27, 0.10, 0.17), (163.0, 0.05, 0.11, 0.15)]
# the shared fringe flap bulges by offset_mid at every edge column; at the temples
# (|theta| 90, in front of the ears) that middle row stood 0.26 off the skull, further
# out than the side hair, and showed as thin blades beside the head (front and back
# views). {|theta|: middle-row offset} there
FLAP_SIDE_MID = {90.0: 0.13}
# flatter, rounder top (the shell's top-pole vertex sat as a peak above the crown curls)
TOP_DROP = 0.07
# the back hair's lowest ring (ring 0, the jaw line) is raised to the nape, more behind
# the ears (the hairline curves up around them): {|theta|: lift}
NAPE_LIFT = {120.0: 0.30, 150.0: 0.16, 180.0: 0.12}
# the side hair (ring 2 beside and behind the ears) hangs lower than the brow line,
# so the cloud's outline curves down to the tops of the ears. The dropped vertex is
# also pulled in (lump < 1, no checker): at full offset it was the outermost, lowest
# point of the cloud from the front, a sharp sideways wedge above the ear.
# {|theta|: (drop, out, lump)}
SIDE_DROP = {90.0: (0.11, 0.0, 0.72), 120.0: (0.09, 0.0, 0.88)}
# curl colour = the (lifted) spec hair colour mixed a little toward a warm brown: low
# contrast up close (no "bark chips"), still a visible curly texture at game size
CURL_TOWARD, CURL_MIX = "#6A5444", 0.08
# apex height / base radius: blunt = rounder; clumps on the silhouette of a view show
# their triangular profile, so they stay low (0.42 / 0.6 read as spikes in profile)
CLUMP_HEIGHT = 0.38
HANG_HEIGHT = 0.5
FRINGE_TOP_RING = 3  # sgl_heads.add_fringe fans the flap from this ring (the crease)

# ------------------------------------------------------------------ shared-code guard
_NEEDS = {
    H: ("SEG", "THETAS", "SKULL_RINGS", "ring_point", "skull_surface", "surface_normal", "BoneFrame", "Geo",
        "emit"),
    sgl_body: ("bone_bvh", "radial_hit", "hoodie_hem"),
    smat: ("accessory_material", "build_palette"),
}


def _require(g=None):
    """Fail loudly if a shared helper this module relies on was renamed or removed."""
    missing = [f"{m.__name__}.{n}" for m, names in _NEEDS.items() for n in names if not hasattr(m, n)]
    if g is not None:
        missing += [f"Geo.{a} (set by sgl_heads.build_head)" for a in ("verts", "faces", "hair_vid", "face_vid")
                    if not hasattr(g, a)]
        if hasattr(g, "hair_vid") and not any(k == FRINGE_TOP_RING for (k, _i) in g.hair_vid):
            missing.append(f"hair ring {FRINGE_TOP_RING} in Geo.hair_vid (the fringe crease ring)")
    if missing:
        raise RuntimeError("characters/raami.py relies on shared code that changed: " + ", ".join(missing)
                           + " -- update raami.py to the new API")


def _wrap(theta):
    return (theta + 180.0) % 360.0 - 180.0


def _frame(n):
    n = n.normalized()
    up = Vector((0.0, 0.0, 1.0))
    t1 = up - n * up.dot(n)
    if t1.length < 1e-4:
        t1 = Vector((1.0, 0.0, 0.0)) - n * n.x
    t1.normalize()
    return n, t1, n.cross(t1).normalized()


def clump(g, c, n, r, h, k=5, sink=0.35, spin=0.0, role="curl", closed=False, bvh=None):
    """Blunt k-sided pyramid (k tris): base ring of radius r around c, sunk r*sink
    below the surface along n, apex h out along n. Smooth normals make it read as a
    rounded curl clump (bright centre, darker rim). closed: also a base polygon (k-2
    tris) for clumps that hang free of the hair, whose open base would otherwise show
    as see-through blades from behind (backface culling). bvh (the hair surface):
    each base corner is dropped onto it (a little below), so on strongly curved hair
    (the crease, the fringe front) the base does not stand off the surface as a flap
    that shows as a thin blade on the silhouette."""
    n, t1, t2 = _frame(n)
    base = []
    for j in range(k):
        a = spin + 2.0 * math.pi * j / k
        q = c + (t1 * math.cos(a) + t2 * math.sin(a)) * r - n * (r * sink)
        if bvh is not None:
            hit, _nor = _cast(bvh, q + n * (r * 1.2), -n, r * 2.6)
            if hit is not None:
                q = hit - n * (r * 0.12)
        base.append(g.v(q))
    apex = g.v(c + n * h)
    below = c - n * r
    for j in range(k):
        a_, b_ = base[j], base[(j + 1) % k]
        mid = (g.verts[a_] + g.verts[b_] + g.verts[apex]) / 3.0
        g.face([a_, b_, apex], role, mid - below)
    if closed:
        g.face(base, role, -n)
        return k + k - 2
    return k


def _hair_bvh(g):
    polys = [list(idx) for idx, role in g.faces if role == "hair"]
    return BVHTree.FromPolygons([Vector(v) for v in g.verts], polys)


def _cast(bvh, origin, d, dist):
    d = d.normalized()
    loc, nor, _i, _dd = bvh.ray_cast(origin, d, dist)
    if loc is None:
        return None, None
    if nor.dot(d) > 0:
        nor = -nor
    return loc, nor


def _sph(az, el):
    a, e = math.radians(az), math.radians(el)
    return Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))


def lump_shell(g):
    face_ids = set(g.face_vid.values())
    for (k, i), vi in g.hair_vid.items():
        if vi in face_ids or not isinstance(k, int):
            continue
        s = H.ring_point(k, H.THETAS[i])
        side = SIDE_DROP.get(abs(_wrap(H.THETAS[i]))) if k == 2 else None
        lump = side[2] if side else LUMP[(k + i) % 2]
        g.verts[vi] = s + (g.verts[vi] - s) * lump
    top = g.hair_vid.get(("top", 0))
    if top is not None and top not in face_ids:
        g.verts[top].z -= TOP_DROP
    for i, th in enumerate(H.THETAS):
        drop = SIDE_DROP.get(abs(_wrap(th)))
        vi = g.hair_vid.get((2, i))
        if drop and vi is not None and vi not in face_ids:
            p = g.verts[vi]
            out = Vector((p.x, p.y, 0.0)).normalized()
            g.verts[vi] = p + out * drop[1] - Vector((0.0, 0.0, drop[0]))
    # raise the back hairline (hair edge AND the skin edge under it, so the strip between
    # them stays a short underside instead of a wall reaching down to the jaw)
    for i, th in enumerate(H.THETAS):
        lift = NAPE_LIFT.get(abs(_wrap(th)), 0.0)
        if not lift:
            continue
        for vi in {g.hair_vid.get((0, i)), g.face_vid.get((0, i))} - {None}:
            g.verts[vi].z += lift


def tuck_flap_sides(g, style):
    """Pull the fringe flap's middle-row vertices at the temples in (FLAP_SIDE_MID).
    They are found by position: sgl_heads.add_fringe puts them at
    skull_surface(t, u_m) + surface_normal(t, u_m) * offset_mid."""
    fr = style.get("fringe") or {}
    mid_off = fr.get("offset_mid")
    if mid_off is None:
        return 0
    edge = fr["edge"]
    u_lo = H.SKULL_RINGS[fr.get("lo_ring", 2)][0]
    u_hi = H.SKULL_RINGS[FRINGE_TOP_RING][0]
    moved = 0
    for t_abs, off in FLAP_SIDE_MID.items():
        for t in (t_abs, -t_abs):
            if t not in edge:
                continue
            u_e = max(u_lo + 0.005, min(u_hi - 0.02, edge[t]))
            u_m = u_e + (u_hi - u_e) * fr.get("mid_at", 0.45)
            p, n = H.skull_surface(t, u_m), H.surface_normal(t, u_m)
            want = p + n * mid_off
            hits = [i for i, v in enumerate(g.verts) if (v - want).length < 1e-5]
            if len(hits) != 1:
                raise RuntimeError(f"raami tuck_flap_sides: fringe middle vertex at theta {t} not found "
                                   f"({len(hits)} matches) - did sgl_heads.add_fringe change?")
            g.verts[hits[0]] = p + n * off
            moved += 1
    return moved


def _crease_point(g, theta):
    """Point on the (lumpy) crease line where the fringe flap meets the crown: the
    ring-3 hair vertices, interpolated between columns."""
    step = 360.0 / H.SEG
    t = theta % 360.0
    i0 = int(t // step) % H.SEG
    i1 = (i0 + 1) % H.SEG
    a = (t - H.THETAS[i0]) / step
    p0 = g.verts[g.hair_vid[(FRINGE_TOP_RING, i0)]]
    p1 = g.verts[g.hair_vid[(FRINGE_TOP_RING, i1)]]
    return p0.lerp(p1, a)


def _jit(*key):
    """Deterministic pseudo-random value in [-1, 1] (no RNG state: every build is identical)."""
    x = math.sin(sum((n + 1) * 12.9898 * k for n, k in enumerate(key)) + 78.233) * 43758.5453
    return 2.0 * (x - math.floor(x)) - 1.0


def head_parts(g, style, spec):
    _require(g)
    lump_shell(g)
    tuck_flap_sides(g, style)
    bvh = _hair_bvh(g)
    tris = {"surface": 0, "crease": 0, "fringe": 0, "tips": 0, "hang": 0}
    # curl clumps all over the hair cloud
    a_lo, a_hi, el_max, tilt, h_scale = SIDE_TILT
    for az, el, r in SURFACE_CLUMPS:
        az += 6.0 * _jit(az, el)
        el += 4.0 * _jit(el, az)
        d = _sph(az, el)
        loc, nor = _cast(bvh, CLOUD_CENTER + d * 3.0, -d, 2.75)
        if loc is None or (loc - CLOUD_CENTER).length < 0.35:
            continue
        nn = (nor + d).normalized()
        h = r * CLUMP_HEIGHT
        if a_lo < abs(_wrap(az)) < a_hi and el < el_max:
            nn = (nn + Vector((0.0, 0.0, -tilt))).normalized()
            h *= h_scale
        # low on the back/sides (mostly seen at a distance): 4 sides instead of 5
        tris["surface"] += clump(g, loc, nn, r, h, k=4 if el < 0 else 5, sink=0.3,
                                 spin=math.radians(az * 0.37 + el), bvh=bvh)
    # curls right on the crown/fringe crease (breaks the "beret brim" line)
    for t, r in CREASE_CLUMPS:
        p = _crease_point(g, t)
        d = (p - CLOUD_CENTER).normalized()
        loc, nor = _cast(bvh, CLOUD_CENTER + d * 3.0, -d, 2.75)
        if loc is None:
            loc, nor = p, d
        axis = (nor + d).normalized()
        tris["crease"] += clump(g, loc, axis, r, r * (CLUMP_HEIGHT - 0.02), k=4 if abs(t) > 55 else 5,
                                sink=0.35, spin=math.radians(18 + t * 1.7), bvh=bvh)
    # curls falling over the forehead (forward and down)
    for t, u, r, droop in FRINGE_CLUMPS:
        p = H.skull_surface(t, u)
        n = H.surface_normal(t, u)
        loc, nor = _cast(bvh, p + n * 1.5, -n, 1.5)
        if loc is None:
            continue
        axis = (nor + Vector((0.0, 0.0, -droop))).normalized()
        tris["fringe"] += clump(g, loc, axis, r, r * (CLUMP_HEIGHT + 0.08), sink=0.4, spin=math.radians(36 + t), bvh=bvh)
    # round curls hanging below the fringe edge and the side/back hair edge
    blobs = [("tips", t, u, r, dist, 0.35) for t, u, r, dist in FRINGE_TIPS]
    blobs += [("hang", side * t, u, r, dist, 0.45) for side in (-1, 1) for t, u, r, dist in HANG_CLUMPS]
    for kind, t, u_low, r, dist, droop in blobs:
        u_c = u_low + r * 0.95
        p = H.skull_surface(t, u_c)
        n = H.surface_normal(t, u_c)
        if abs(t) > 65:   # sides/back: push out horizontally
            n = Vector((n.x, n.y, 0.0)).normalized()
        axis = n + Vector((0.0, 0.0, -droop))
        if 65 < abs(t) < 110:  # temples / ear tops: turned a little forward so they read round from the front
            axis += Vector((0.0, 0.45, 0.0))
        axis.normalize()
        # the hanging side curls are closed (their open base showed as blades from
        # behind); the nape ones (4-sided) face down/out and are seen from outside only
        tris[kind] += clump(g, p + n * dist, axis, r, r * HANG_HEIGHT, k=4 if abs(t) > 130 else 5, sink=0.25,
                            spin=math.radians(90 + t), closed=(kind == "hang" and abs(t) < 130))
    g.raami_clump_tris = dict(tris, total=sum(tris.values()))
    print(f"SGL raami head_parts: curl-clump tris {g.raami_clump_tris}, head total {g.tri_count()}")


def curl_colour(spec, mats=None):
    pal = (mats or {}).get("_palette") or smat.build_palette(spec)
    return mix_hex(pal["hair"], CURL_TOWARD, CURL_MIX)


def head_roles(spec, mats):
    _require()
    return {"curl": smat.accessory_material(mats, "hair_curl", curl_colour(spec, mats), base="Hair (HAIR)")}


# ------------------------------------------------------------------ outfit
def add_crew_collar(ctx):
    """Ribbed crew neck: a thick band around the base of the neck (top_detail), a
    little higher at the back, with a closed top rim and an inner wall."""
    obj, arm, mats = ctx["obj"], ctx["arm"], ctx["mats"]
    bvh, frame = sgl_body.bone_bvh(obj, arm, "Torso", ["Torso"])
    g = H.Geo()
    # the head pivot sits at torso u 0.41 and the neck stub above it is inside the head:
    # the collar rings the base of the neck just below the jaw (higher at the back)
    u_front, u_back = 0.30, 0.335
    cols = 12
    up = Vector((0.0, 0.0, 1.0))
    rings = []
    for j in range(cols):
        t = 360.0 * j / cols
        back = (1 - math.cos(math.radians(t))) / 2
        u = u_front + (u_back - u_front) * back
        loc, _n = sgl_body.radial_hit(bvh, t, u)
        if loc is None:
            print(f"SGL WARNING: crew_collar: torso not found at theta {t}")
            return 0
        n = Vector((loc.x, loc.y, 0.0)).normalized()  # outward, horizontal
        lo = loc + n * 0.012 - up * 0.02
        out = loc + n * 0.035 + up * 0.03
        top = loc - n * 0.005 + up * 0.075
        inner = loc - n * 0.04 + up * 0.065
        rings.append([g.v(q) for q in (lo, out, top, inner)])
    for j in range(cols):
        a, b = rings[j], rings[(j + 1) % cols]
        mid = sum((g.verts[i] for i in a + b), Vector()) / 8
        rad = Vector((mid.x, mid.y, 0.0)).normalized()
        g.face([a[0], b[0], b[1], a[1]], "top_detail", rad - up * 0.3)
        g.face([a[1], b[1], b[2], a[2]], "top_detail", rad + up * 0.5)
        g.face([a[2], b[2], b[3], a[3]], "top_detail", up)
    return H.emit(g, obj, "Torso", frame, {"top_detail": mats["top_detail"]})


def add_sweatshirt(ctx):
    """Crewneck sweatshirt: ribbed collar + hip-length body with a ribbed hem (the
    pelvis faces recoloured by sgl_body.hoodie_hem). Returns the collar's tris."""
    _require()
    tris = add_crew_collar(ctx)
    sgl_body.hoodie_hem(ctx)
    return tris


ACCESSORIES = {"crewneck_sweatshirt": add_sweatshirt}


def wears_crewneck(spec):
    top = str(spec.get("outfit", {}).get("top", "")).lower()
    return "crewneck" in top or "crew neck" in top or "crew-neck" in top


# ------------------------------------------------------------------ wing-cap wings
# The wings (Mario Mesh groups Left/Right Wing DL) sit at the sides of Mario's cap; here
# their roots would be buried in the curls, so they move out to the hair surface. The
# wing bones move by the same amount, so in the export the wing vertices stay where
# the template has them relative to their bone (root edge on the bone's X axis) and
# geo_mario_rotate_wing_cap_wings still flaps them about their root; only the
# GEO_TRANSLATE_ROTATE offset of the wing node changes.
WING_SHIFT = Vector((0.22, -0.02, 0.06))  # head space (l, f, u), mirrored for the right wing
WING_SIDES = (("Left", 1.0), ("Right", -1.0))
WING_ARMATURES = ("Mario", "Metal Mario")  # the metal body is rebuilt from Mario Mesh later


def _wing_bones(side):
    return (f"{side} Wing", f"0 {side} Wing Rotation Function", f"1 {side} Wing Rotation", f"{side} Wing DL")


def _translate_bones(arm, moves):
    """Translate edit bones {name: armature-space vector}. Needs edit mode."""
    import bpy
    if not moves:
        return 0
    vl = bpy.context.view_layer
    prev = vl.objects.active
    hidden, hide_vp = arm.hide_get(), arm.hide_viewport
    arm.hide_viewport = False
    arm.hide_set(False)
    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    vl.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    try:
        eb = arm.data.edit_bones
        for name, d in moves.items():
            eb[name].translate(d)
    finally:
        bpy.ops.object.mode_set(mode="OBJECT")
        arm.hide_viewport = hide_vp
        arm.hide_set(hidden)
        vl.objects.active = prev
    return len(moves)


def move_wings():
    import bpy
    obj, arm = bpy.data.objects["Mario Mesh"], bpy.data.objects["Mario"]
    frame = H.BoneFrame(obj, arm, "Head DL")
    moved = 0
    shifts = {}
    for side, sgn in WING_SIDES:
        vg = obj.vertex_groups.get(f"{side} Wing DL")
        if vg is None:
            continue
        shift = Vector((WING_SHIFT.x * sgn, WING_SHIFT.y, WING_SHIFT.z))
        shifts[side] = shift
        for v in obj.data.vertices:
            if any(g.group == vg.index and g.weight > 0.4 for g in v.groups):
                v.co = frame.to_local(frame.from_local(v.co) + shift)
                moved += 1
    bones = {}
    for arm_name in WING_ARMATURES:
        a = bpy.data.objects.get(arm_name)
        if a is None or a.type != "ARMATURE" or "Head DL" not in a.data.bones:
            continue
        head3 = a.data.bones["Head DL"].matrix_local.to_3x3()  # bone-local axes = (u, f, l)
        moves = {}
        for side, s in shifts.items():
            d = head3 @ Vector((s.z, s.y, s.x))
            moves.update({n: d for n in _wing_bones(side) if n in a.data.bones})
        bones[arm_name] = _translate_bones(a, moves)
    if moved and bones.get("Mario", 0) != 8:
        raise RuntimeError(f"raami move_wings: moved {moved} wing vertices but bones {bones} (expected 8 per armature)")
    return {"vertices": moved, "bones": bones}


def post_build(ctx):
    import bpy
    _require()
    spec = ctx["spec"]
    out = {"wings_moved": move_wings()}
    # the sweatshirt is the outfit itself (the spec lists no accessories); if the spec
    # ever lists "crewneck_sweatshirt", ACCESSORIES above builds it instead
    if wears_crewneck(spec) and "crewneck_sweatshirt" not in spec.get("build", {}).get("accessories", []):
        bctx = {"obj": bpy.data.objects["Mario Mesh"], "arm": bpy.data.objects["Mario"],
                "mats": ctx["mats"], "spec": spec}
        out["crewneck_sweatshirt_collar_tris"] = add_sweatshirt(bctx)
    out["curl_colour"] = curl_colour(spec, ctx["mats"])
    return out
