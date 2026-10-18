"""Render template frames 0, 30, 60, then two synthetic limb bends (60 degrees).

Blender --python tools/likeness/render_poses.py -- <batch> <specimen ID>.
"""
from pathlib import Path
import sys

import bpy
import math
from mathutils import Quaternion, Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/blender"))
import sgl_preview as preview


def main():
    batch, code = sys.argv[sys.argv.index("--") + 1:]
    folder = Path(batch).resolve() / "models" / code
    bpy.ops.wm.open_mainfile(filepath=str(folder / f"{code}.blend"), load_ui=False)
    from sgl_blender import setup_fast64
    setup_fast64()
    body, arm = bpy.data.objects["Mario Mesh"], bpy.data.objects["Mario"]
    arm.animation_data.action = bpy.data.actions[preview.PREVIEW_ACTION]
    for obj in bpy.data.objects:
        obj.hide_render = obj is not body
    preview.swap_to_preview_materials(body)
    preview.BG = (.84, .86, .80)
    cam = preview.setup_scene(256)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 4
    scene.cycles.use_denoising = False
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    paths = []
    scene.frame_set(0)
    base = [b.matrix_basis.copy() for b in arm.pose.bones]
    for frame in (0, 30, 60, "bend-y", "bend-z"):
        if isinstance(frame, int):
            scene.frame_set(frame)
        else:
            arm.animation_data.action = None
            axis = (0, 1, 0) if frame == "bend-y" else (0, 0, 1)
            for bone, matrix in zip(arm.pose.bones, base):
                bone.matrix_basis = matrix
                if any(n in bone.name for n in ("Forearm", "Thigh Color", "Leg")):
                    bone.matrix_basis = matrix @ Quaternion(axis, math.radians(60)).to_matrix().to_4x4()
        bpy.context.view_layer.update()
        lo, hi = preview.frame_bbox(body, arm)
        cam.data.ortho_scale = max(hi - lo) * 1.15
        preview.aim(cam, (lo + hi) / 2, Vector((.65, -1, .12)), 10.)
        path = str(folder / f"pose-{frame}.png")
        preview.render_to(path)
        paths.append(path)
    preview.compose_grid(paths, str(folder / "poses.png"), cols=5)


if __name__ == "__main__":
    main()
