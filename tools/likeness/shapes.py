"""Experimental geometry for the review batch, using the existing character rig.

Loaded by build_one.py only; production generation does not use this module.
"""
import copy
import math

import bpy
from mathutils import Vector

from catalog import BODY_PROFILES, FACE_PROFILES
import sgl_heads


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
    hair = spec["likeness_review"]["hair"]
    if hair not in ("waves", "curls", "coils"):
        return
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


def body_post_build(ctx):
    """Continuous rest-space silhouette study. The production skeleton is unchanged.

    Apply the same position-based transform to coincident seams. These initial
    shapes require animation review before use in the production generator.
    """
    spec = ctx["spec"]
    profile = spec["likeness_review"]
    shoulder, waist, hip, depth = BODY_PROFILES[profile["body"]]
    if profile["outfit"] == "hoodie":
        shoulder *= 1.035
        waist *= 1.07
        depth *= 1.04
    if profile["outfit"] == "overshirt":
        shoulder *= 1.045
        waist *= 1.13
        depth *= 1.055
    obj = bpy.data.objects["Mario Mesh"]
    frame = sgl_heads.BoneFrame(obj, bpy.data.objects["Mario"], "Torso")
    groups = {g.index: g.name for g in obj.vertex_groups}
    head_z = []
    for v in obj.data.vertices:
        if any(groups.get(g.group) == "Head DL" for g in v.groups):
            head_z.append(frame.from_local(v.co).z)
    top = min(head_z) if head_z else max(frame.from_local(v.co).z for v in obj.data.vertices)
    bottom = min(frame.from_local(v.co).z for v in obj.data.vertices)
    height = max(top - bottom, .01)
    changed = 0
    for v in obj.data.vertices:
        names = [groups.get(g.group, "") for g in v.groups]
        if any("Head" in n or "Wing" in n for n in names):
            continue
        p = frame.from_local(v.co)
        t = max(0., min(1., (p.z - bottom) / height))
        stops = [(0., hip), (.45, hip), (.65, waist), (.88, shoulder), (1., 1.)]
        scale = 1.
        for (a, av), (b, bv) in zip(stops, stops[1:]):
            if a <= t <= b:
                scale = av + (bv - av) * (t - a) / (b - a)
                break
        fade = min(1., max(0., (1. - t) / .12))
        p.x *= scale
        p.y *= 1 + (depth - 1) * fade
        v.co = frame.to_local(p)
        changed += 1
    obj.data.update()
    return {"profile": profile, "vertices": changed, "status": "review silhouette; animation fitting pending"}
