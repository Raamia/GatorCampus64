# Inspect a coopdx character .blend headlessly: objects, armature hierarchy,
# Fast64 geo commands, materials, textures and triangle counts.
# Usage: blender --background <file.blend> --python inspect_template.py
import bpy
import addon_utils

mod = addon_utils.enable("fast64", default_set=True, persistent=True)
print("FAST64_ENABLED", bool(mod))

scene = bpy.context.scene
print("SCENE", scene.name, "gameEditorMode=", getattr(scene, "gameEditorMode", None))

print("\n== OBJECTS ==")
for ob in bpy.data.objects:
    tris = ""
    if ob.type == "MESH":
        me = ob.data
        me.calc_loop_triangles()
        tris = f" tris={len(me.loop_triangles)} verts={len(me.vertices)} mats={[m.name for m in me.materials if m]}"
    print(f"{ob.type:9s} {ob.name!r} parent={ob.parent.name if ob.parent else None!r} "
          f"parent_bone={ob.parent_bone!r} hide={ob.hide_get() if ob.name in bpy.context.view_layer.objects else 'n/a'}{tris}")

print("\n== ARMATURES ==")
for arm in [o for o in bpy.data.objects if o.type == "ARMATURE"]:
    print("ARMATURE", arm.name)
    def walk(bone, depth):
        cmd = getattr(bone, "geo_cmd", None)
        extra = ""
        for attr in ("func_param", "geo_func", "switch_func", "draw_layer"):
            if hasattr(bone, attr):
                extra += f" {attr}={getattr(bone, attr)!r}"
        print("  " * depth + f"- {bone.name!r} geo_cmd={cmd!r}{extra}")
        for child in bone.children:
            walk(child, depth + 1)
    for b in arm.data.bones:
        if b.parent is None:
            walk(b, 1)

print("\n== MATERIALS ==")
for m in bpy.data.materials:
    f3d = getattr(m, "f3d_mat", None)
    info = ""
    if f3d is not None:
        try:
            t0 = f3d.tex0.tex
            info += f" tex0={t0.name if t0 else None}"
            if t0:
                info += f" size={tuple(t0.size)} fmt={f3d.tex0.tex_format}"
        except Exception as e:
            info += f" (tex0 err {e})"
        for attr in ("coop_player_part", "player_part", "coop_part"):
            if hasattr(f3d, attr):
                info += f" {attr}={getattr(f3d, attr)!r}"
    print(f"MAT {m.name!r} is_f3d={getattr(m, 'is_f3d', None)} users={m.users}{info}")

print("\n== IMAGES ==")
for img in bpy.data.images:
    print(f"IMG {img.name!r} size={tuple(img.size)} file={img.filepath!r} packed={bool(img.packed_file)}")

print("\n== FAST64 SCENE SETTINGS ==")
try:
    sm64 = scene.fast64.sm64
    print("export_type", sm64.export_type)
    ce = sm64.combined_export
    for attr in dir(ce):
        if attr.startswith(("export", "custom", "object_name", "level", "non_decomp", "header")) and not attr.startswith("__"):
            try:
                print("  ce.", attr, "=", getattr(ce, attr))
            except Exception:
                pass
except Exception as e:
    print("fast64 settings error:", e)
print("INSPECT_DONE")
