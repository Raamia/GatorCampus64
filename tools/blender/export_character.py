# Export a coopdx character armature to C with Fast64, headlessly.
# coopdx (DynOS) compiles the exported folder into <actor>_geo.bin when the mod loads.
#
# Usage:
#   blender --background <file.blend> --python export_character.py -- <armature> <actor_name> <actors_dir>
# Example:
#   ... -- Mario daniel /path/to/mods/sgl64/actors   ->  actors/daniel/{geo.inc.c, model.inc.c}
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sgl_blender import setup_fast64  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
if len(argv) != 3:
    sys.exit("usage: -- <armature> <actor_name> <actors_dir>")
armature_name, actor_name, actors_dir = argv
actors_dir = os.path.abspath(actors_dir)
os.makedirs(actors_dir, exist_ok=True)

setup_fast64()

scene = bpy.context.scene
scene.gameEditorMode = "SM64"
scene.fast64.sm64.export_type = "C"
scene.saveTextures = False  # inline texture arrays: no #include paths for DynOS to resolve

ce = scene.fast64.sm64.combined_export
ce.export_header_type = "Custom"
ce.custom_export_path = actors_dir
ce.object_name = actor_name
ce.delete_all_bins = False

if bpy.context.mode != "OBJECT":
    bpy.ops.object.mode_set(mode="OBJECT")

armature = bpy.data.objects.get(armature_name)
if armature is None or armature.type != "ARMATURE":
    sys.exit(f"armature {armature_name!r} not found")
bpy.context.view_layer.objects.active = armature

result = bpy.ops.object.sm64_export_geolayout_armature(export_obj=armature_name)
out_dir = os.path.join(actors_dir, actor_name)
files = sorted(os.listdir(out_dir)) if os.path.isdir(out_dir) else []
print(f"EXPORT_RESULT {result} -> {out_dir} files={files}")
if result != {"FINISHED"} or "geo.inc.c" not in files:
    sys.exit(1)
