"""Approved, composable head geometry and skeleton-compatible body fitting."""
import copy
import math

import bpy
from mathutils import Vector

from sgl_appearance import BODY_PROFILES, FACE_PROFILES
import sgl_heads


def _interp(x, points):
    if x <= points[0][0]:
        return points[0][1] + x - points[0][0]
    if x >= points[-1][0]:
        return points[-1][1] + x - points[-1][0]
    for (a, av), (b, bv) in zip(points, points[1:]):
        if a <= x <= b:
            return av + (bv - av) * (x - a) / (b - a)


def _height(z, profile):
    oval = FACE_PROFILES["oval"]
    face = FACE_PROFILES[profile["face"]]
    return _interp(z, [(0., 0.), *zip(oval["heights"], face["heights"])])


def _hair_point(point, profile):
    """Fit the approved oval-head locks to the selected skull, independently of hair."""
    x, y, z = point
    oval = FACE_PROFILES["oval"]
    face = FACE_PROFILES[profile["face"]]
    widths = [(u, w / ow) for u, w, ow in zip(oval["heights"], face["widths"], oval["widths"])]
    clipped_z = max(widths[0][0], min(widths[-1][0], z))
    return Vector((x * _interp(clipped_z, widths), y, _height(z, profile)))


def head_style(profile):
    face = FACE_PROFILES[profile["face"]]
    style = copy.deepcopy(sgl_heads.HAIR_STYLES["short_wavy_curly"])
    style.update(window=180, face_bands=("fan_bottom", 0, 1, 2),
                 off={"top": 0.02, "upper": 0.018, "side": 0.015, "back": 0.015},
                 hang=False, fringe=None, drape=None, ears=True)
    # The rear half below the temples is exposed skin, rather than a hair helmet.
    style["hair_bottom"] = {t: 2 for t in (15, 45, 75, 105, 135, 165)}
    style["window"] = 90
    style["skull"] = [(u, w, rf, rb, f0, p) for u, w, p, (_, _, rf, rb, f0, _) in
                      zip(face["heights"], face["widths"], face["powers"], sgl_heads._DEFAULTS["SKULL_RINGS"])]
    style["bottom_pole"] = (0, 0.07, face["heights"][0] - 0.10)
    style["top_pole"] = (0, -0.03, face["heights"][-1] + 0.08)
    eye_u = (face["heights"][1] + face["heights"][2]) / 2
    mouth_u = (face["heights"][0] + face["heights"][1]) / 2
    style["face_layout"] = {"eyes": (0, eye_u, face["widths"][2] * 1.65, 0.38),
                            "mouth": (0, mouth_u, 0.33, 0.165)}
    style["nose"] = {"u": face["heights"][1] + 0.035, "half_width": face["nose"][0],
                     "tip": face["nose"][1], "top": 0.07, "bottom": -0.035}
    style["ears"] = {"theta": 94, "u": eye_u - 0.09, "h": 0.20, "out": 0.09, "w": 0.065}
    hair = profile["hair"]
    if hair == "sidepart":
        style["off"] = {"top": 0.11, "upper": 0.075, "side": 0.025, "back": 0.035}
        style["fringe"] = {"kind": "side_part", "offset": 0.035, "lo_ring": 1,
                           "edge": {-60: 0.82, -45: 0.88, -30: 0.97, -15: 0.89, 0: 0.80, 15: 0.75, 30: 0.73, 45: 0.77, 60: 0.82}}
    elif hair == "fringe":
        style["off"] = {"top": 0.12, "upper": 0.09, "side": 0.055, "back": 0.06}
        style["hair_bottom"] = {t: 1 for t in (75, 105, 135, 165)}
        style["fringe"] = {"kind": "full", "offset": 0.055, "lo_ring": 1,
                           "edge": {t: 0.66 + (0.018 if t % 30 else 0) for t in range(-60, 61, 15)}}
    elif hair in ("waves", "curls", "coils"):
        style["off"] = {"top": 0.08, "upper": 0.06, "side": 0.025, "back": 0.03}
        if hair == "coils":
            style["off"] = {"top": 0.14, "upper": 0.14, "side": 0.10, "back": 0.12}
            style["hair_bottom"] = {t: 1 for t in (75, 105, 135, 165)}
    elif hair in ("bob", "long"):
        long = copy.deepcopy(sgl_heads.HAIR_STYLES["long_straight_past_shoulders"])
        for key in ("off", "hang", "fringe", "drape", "locks", "window", "face_bands"):
            style[key] = long[key]
        style.pop("hair_bottom", None)
        if hair == "bob":
            style["locks"] = None
            style["drape"]["ends"] = {t: 0.12 + (0.025 if t in (60, 300) else 0) for t in range(60, 301, 30)}
            style["drape"]["flare"] = 0.045
    if profile["face"] != "oval":
        fringe = style.get("fringe")
        if fringe:
            fringe["edge"] = {angle: _height(z, profile) for angle, z in fringe["edge"].items()}
        locks = style.get("locks")
        if locks:
            for key in ("u_top", "u_mid", "u_tip"):
                locks[key] = _height(locks[key], profile)
    return style


def _clump(g, center, radius, stretch=(1, 1, 1)):
    """Small faceted rounded lock, embedded into the scalp shell."""
    center = Vector(center)
    rings = []
    for lat in (-60, -20, 20, 60):
        a = math.radians(lat)
        rings.append([g.v(center + Vector((math.cos(math.radians(t)) * math.cos(a) * radius * stretch[0],
                                         math.sin(math.radians(t)) * math.cos(a) * radius * stretch[1],
                                         math.sin(a) * radius * stretch[2]))) for t in range(0, 360, 60)])
    for row_a, row_b in zip(rings, rings[1:]):
        for i in range(6):
            ids = [row_a[i], row_a[(i + 1) % 6], row_b[(i + 1) % 6], row_b[i]]
            g.face(ids, "hair", sum((g.verts[k] for k in ids), Vector()) / 4 - center)
    g.face(rings[0], "hair", Vector((0, 0, -1)))
    g.face(rings[-1], "hair", Vector((0, 0, 1)))


def add_hair_parts(g, style, spec):
    profile = spec["appearance"]
    hair = profile["hair"]
    if hair not in ("waves", "curls", "coils"):
        return
    first_vertex = len(g.verts)
    if hair == "waves":
        for i, (x, y, z) in enumerate(((-.29, .27, 1.03), (0, .32, 1.08), (.29, .25, 1.05),
                                      (-.25, -.05, 1.19), (.07, -.04, 1.24), (.31, -.07, 1.14), (0, -.28, 1.12))):
            _clump(g, (x, y, z), .16, (1.15, .82, .65))
    else:
        radius = .125 if hair == "curls" else .16
        for row, (z, r, count) in enumerate(((1.25, .12, 5), (1.14, .34, 9), (.96, .47, 12))):
            for i in range(count):
                a = 2 * math.pi * (i + row * .35) / count
                _clump(g, (math.cos(a) * r, math.sin(a) * r - .025, z), radius,
                       (1, 1, 1 + .10 * math.sin(i * 2)))
        if hair == "coils":
            for i in range(11):
                a = math.radians(60 + i * 24)
                _clump(g, (math.sin(a) * .54, math.cos(a) * .52, .75), .14)
    if profile["face"] != "oval":
        for index in range(first_vertex, len(g.verts)):
            g.verts[index] = _hair_point(g.verts[index], profile)


def fit_body(obj, arm, profile):
    """Fit cross-sections in each bone's rest frame, keeping the original joint caps.

    A global mesh stretch moves vertices away from their unchanged skeletal pivots.
    Here joint planes, shared seam vertices, hands, feet, head and wings stay fixed.
    Garments are added afterward against the fitted body surface.
    """
    shoulder, waist, hip, depth = BODY_PROFILES[profile["body"]]
    if profile["outfit"] == "hoodie":
        shoulder *= 1.035
        waist *= 1.07
        depth *= 1.04
    elif profile["outfit"] == "overshirt":
        shoulder *= 1.045
        waist *= 1.13
        depth *= 1.055
    names = {g.index: g.name for g in obj.vertex_groups}
    dominant = {v.index: names[max(v.groups, key=lambda g: g.weight).group] for v in obj.data.vertices if v.groups}
    body_groups = {n for n in dominant.values() if not any(k in n for k in ("Head", "Wing", "Hand", "Shoe"))}
    all_groups = set(dominant.values())
    seams = {}
    for v in obj.data.vertices:
        key = tuple(round(float(c), 5) for c in v.co)
        seams.setdefault(key, []).append(v.index)
    protected = {i for indices in seams.values() if len({dominant.get(i) for i in indices}) > 1 for i in indices}
    frames = {n: sgl_heads.BoneFrame(obj, arm, n) for n in body_groups}
    joints = {n: [0.] for n in body_groups}
    # Only the nearest weighted ancestor owns this joint; switch/rotation helper
    # bones do not introduce fake caps within a limb.
    to_mesh = obj.matrix_world.inverted() @ arm.matrix_world
    for name in all_groups:
        if "Wing" in name or name not in arm.data.bones:
            continue
        bone = arm.data.bones[name]
        parent = bone.parent
        while parent and parent.name not in all_groups:
            parent = parent.parent
        if parent and parent.name in frames:
            joints[parent.name].append(frames[parent.name].from_local(to_mesh @ bone.head_local).z)
    changed = 0
    max_delta = 0.
    for v in obj.data.vertices:
        name = dominant.get(v.index)
        if name not in frames or v.index in protected:
            continue
        frame = frames[name]
        p = frame.from_local(v.co)
        distance = min(abs(p.z - z) for z in joints[name])
        if distance <= .025:
            protected.add(v.index)
            continue
        blend = min(1., (distance - .025) / .10)
        blend = blend * blend * (3 - 2 * blend)
        if name == "Torso":
            height = max(joints[name]) or .4
            t = max(0., min(1., p.z / height))
            width = waist + (shoulder - waist) * t
        elif name == "Butt":
            width = hip
        elif "Thigh" in name or "Leg" in name:
            width = (hip + depth) / 2
        else:
            width = (shoulder + depth) / 2
        before = v.co.copy()
        p.x *= 1 + (width - 1) * blend
        p.y *= 1 + (depth - 1) * blend
        v.co = frame.to_local(p)
        delta = (v.co - before).length
        changed += delta > 1e-6
        max_delta = max(max_delta, delta)
    obj.data.update()
    return {"body": profile["body"], "outfit": profile["outfit"], "changed_vertices": changed,
            "protected_joint_vertices": sorted(protected), "max_displacement": max_delta,
            "method": "bone-local cross-section fit with fixed joint caps"}
