"""Blender entry point for one catalog specimen; writes game export + GLB + posters."""
import json
import os
from pathlib import Path
import runpy
import sys

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path[:0] = [str(HERE), str(ROOT / "tools/blender")]

from catalog import entries, spec_for
import sgl_characters


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    code, destination = args[:2]
    integrated = "--integrated" in args[2:]
    destination = Path(destination).resolve()
    entry = next(e for e in entries() if e["id"] == code)
    spec = spec_for(entry)
    if integrated:
        from sgl_appearance import VERSION, resolve_spec
        spec["appearance"] = {"version": VERSION, **spec.pop("likeness_review")}
        spec = resolve_spec(spec)
    art = destination / "specs"
    out = destination / "models" / code
    extensions = destination / "extensions"
    (art / code).mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    extensions.mkdir(parents=True, exist_ok=True)
    (art / code / "character.json").write_text(json.dumps(spec, indent=2) + "\n")
    # The builder's existing per-character extension mechanism keeps experiments
    # isolated from the production catalog and the ten handcrafted characters.
    if not integrated:
        (extensions / f"{code}.py").write_text(
            "from shapes import head_style, add_hair_parts, body_post_build\n"
            f"HAIR_STYLE = head_style({entry['profile']!r})\n"
            "head_parts = add_hair_parts\npost_build = body_post_build\n")
        sgl_characters.CHAR_DIR = str(extensions)
    os.environ["SGL_ART_DIR"] = str(art)
    sys.argv = ["build_character.py", "--", code, "--art-dir", str(art),
                "--build-dir", str(out), "--actors-dir", str(destination / "actors"), "--no-preview"]
    runpy.run_path(str(ROOT / "tools/blender/build_character.py"), run_name="__main__")

    from sgl_browser_model import export_browser_model
    import sgl_preview as preview
    glb = export_browser_model(str(out / "model.glb"))
    arm = bpy.data.objects["Mario"]
    body = bpy.data.objects["Mario Mesh"]
    arm.animation_data.action = bpy.data.actions[preview.PREVIEW_ACTION]
    bpy.context.scene.frame_set(0)
    bpy.context.view_layer.update()
    lo, hi = preview.frame_bbox(body, arm)
    hlo, hhi = preview._group_center(body, "Head DL")
    center, head = (lo + hi) / 2, (hlo + hhi) / 2
    full_size = max(hi - lo)
    head_size = max(hhi - hlo)

    def target(v):
        return [round(v.x, 5), round(v.z, 5), round(-v.y, 5)]

    report = json.loads((out / "build_report.json").read_text())
    record = {**entry, "model": f"models/{code}/model.glb", "poster": f"models/{code}/poster.png",
              "front": f"models/{code}/front.png", "headTarget": target(head), "bodyTarget": target(center),
              "headRadius": round(head_size * 2.4, 5), "bodyRadius": round(full_size * 2.1, 5),
              "triangles": report["tris"]["Mario Mesh"], "validation": report["validation"]["ok"]}

    for obj in bpy.data.objects:
        obj.hide_render = obj is not body
    preview.swap_to_preview_materials(body)
    preview.BG = (.84, .86, .80)
    cam = preview.setup_scene(512)
    scene = bpy.context.scene
    # CPU Cycles avoids requiring a display, EGL, or a working GPU driver on SSH hosts.
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 8
    scene.cycles.use_denoising = False
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    closeup = entry["group"] in ("Faces", "Hair")
    cam.data.ortho_scale = (head_size * 1.28) if closeup else (full_size * 1.15)
    focus = head if closeup else center
    for name, direction in (("poster", Vector((.65, -1, .12))), ("front", Vector((0, -1, .04)))):
        preview.aim(cam, focus, direction, 10.)
        preview.render_to(str(out / f"{name}.png"))
    (out / "review.json").write_text(json.dumps(record, indent=2) + "\n")
    print("SGL_REVIEW_READY", code, glb, flush=True)


if __name__ == "__main__":
    main()
