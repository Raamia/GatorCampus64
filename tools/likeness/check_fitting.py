"""Blender checks for composable heads and body fitting on the real template rig.

Run after an integrated f01 build, with Blender --python-exit-code 1 --python
tools/likeness/check_fitting.py -- dist/likeness-integrated.
This exercises the template example animation, not the game's animation library.
"""
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import sys

import bpy
from mathutils import Quaternion

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/blender"))
from sgl_appearance import BODY_PROFILES, FACE_PROFILES, HAIR_PROFILES, OUTFITS
import sgl_heads
from sgl_likeness import fit_body
from sgl_preview import PREVIEW_ACTION


def coordinates(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    result = [v.co.copy() for v in mesh.vertices]
    evaluated.to_mesh_clear()
    assert all(math.isfinite(c) for v in result for c in v)
    return result


def main():
    batch = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    os.environ["SGL_ART_DIR"] = str(batch / "specs")
    bpy.ops.wm.open_mainfile(filepath=str(batch / "models/f01/f01.blend"), load_ui=False)
    obj, arm = bpy.data.objects["Mario Mesh"], bpy.data.objects["Mario"]
    spec = json.loads((batch / "specs/f01/character.json").read_text())
    catalog_before = copy.deepcopy((FACE_PROFILES, sgl_heads.HAIR_STYLES))
    bvh = sgl_heads.body_bvh_head_space(obj, arm)
    heads = {}
    for face in FACE_PROFILES:
        for hair in HAIR_PROFILES:
            spec["appearance"].update(face=face, hair=hair)
            geo = sgl_heads.build_full_head(spec, bvh)
            assert geo.tri_count() > 0
            assert all(math.isfinite(c) for v in geo.verts for c in v)
            digest = hashlib.sha256(repr([tuple(v) for v in geo.verts]).encode()).hexdigest()
            assert digest not in [r["digest"] for r in heads.values()]
            heads[f"{face}/{hair}"] = {"triangles": geo.tri_count(), "digest": digest}
    assert catalog_before == (FACE_PROFILES, sgl_heads.HAIR_STYLES), "head builder mutated shared presets"

    original = [v.co.copy() for v in obj.data.vertices]
    bones = [(b.name, tuple(b.head_local), tuple(b.tail_local), tuple(map(tuple, b.matrix_local)))
             for b in arm.data.bones]
    names = {g.index: g.name for g in obj.vertex_groups}
    untouched = {v.index for v in obj.data.vertices if any(
        any(part in names[g.group] for part in ("Head", "Wing", "Hand", "Shoe")) for g in v.groups)}
    # Independently find coincident vertices with different weights, so the
    # deformation's own reported protection mask cannot hide a missed seam.
    shared = {}
    for vertex in obj.data.vertices:
        key = tuple(round(c, 5) for c in vertex.co)
        weights = tuple(sorted((g.group, round(g.weight, 5)) for g in vertex.groups))
        shared.setdefault(key, []).append((vertex.index, weights))
    untouched.update(index for group in shared.values() if len({w for _, w in group}) > 1
                     for index, _ in group)
    arm.animation_data.action = bpy.data.actions[PREVIEW_ACTION]
    poses = []
    for frame in range(90):
        bpy.context.scene.frame_set(frame)
        poses.append((f"example:{frame}", [b.matrix_basis.copy() for b in arm.pose.bones]))
    # Stress the limb pivots around each local axis from the standing pose.
    bpy.context.scene.frame_set(0)
    base = [b.matrix_basis.copy() for b in arm.pose.bones]
    for axis in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
        for angle in (-60, 60, 110):
            matrices = [m.copy() for m in base]
            for i, bone in enumerate(arm.pose.bones):
                if any(n in bone.name for n in ("Forearm", "Thigh Color", "Leg")):
                    matrices[i] = matrices[i] @ Quaternion(axis, math.radians(angle)).to_matrix().to_4x4()
            poses.append((f"joint-sweep:{axis}:{angle}", matrices))
    arm.animation_data.action = None

    def pose(matrices):
        for bone, matrix in zip(arm.pose.bones, matrices):
            bone.matrix_basis = matrix
        bpy.context.view_layer.update()

    baseline = []
    for _, matrices in poses:
        pose(matrices)
        baseline.append(coordinates(obj))
    assert any(max((a - b).length for a, b in zip(baseline[0], frame)) > .01
               for frame in baseline[1:90]), "template animation did not move the mesh"
    results = {}
    for body in BODY_PROFILES:
        for outfit in OUTFITS:
            for v, co in zip(obj.data.vertices, original):
                v.co = co
            result = fit_body(obj, arm, {"body": body, "outfit": outfit})
            protected = set(result.pop("protected_joint_vertices")) | untouched
            assert all((obj.data.vertices[i].co - original[i]).length < 1e-6 for i in protected)
            if body != "neutral" or outfit in ("hoodie", "overshirt"):
                assert result["changed_vertices"] > 0
            worst = 0.
            for (label, matrices), reference in zip(poses, baseline):
                pose(matrices)
                current = coordinates(obj)
                error = max((current[i] - reference[i]).length for i in protected)
                assert error < 1e-5, (body, outfit, label, error)
                worst = max(worst, error)
            results[f"{body}/{outfit}"] = {**result, "protected_vertices": len(protected),
                                            "max_animated_boundary_delta": worst}
    assert bones == [(b.name, tuple(b.head_local), tuple(b.tail_local), tuple(map(tuple, b.matrix_local)))
                     for b in arm.data.bones]
    report = {"heads": heads, "body_fits": results, "poses_per_body": len(poses),
              "scope": "Finite geometry, distinct heads, unchanged rig and protected boundaries; not a game clipping test"}
    (batch / "fitting_checks.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"FITTING_OK {len(heads)} heads, {len(results)} body/outfit fits, {len(poses)} poses each", flush=True)


if __name__ == "__main__":
    main()
