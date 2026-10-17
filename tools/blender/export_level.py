# Export a Fast64 level (Level Root empty + Area Roots) as a coopdx DynOS level, headlessly.
#
# coopdx (DynOS) compiles mods/<mod>/levels/<name>/ (C sources with a script.c) into
# mods/<mod>/levels/level_<name>_entry.lvl when the game starts, and a Lua
# level_register("level_<name>_entry", ...) makes it a warpable level.
#
# Usage (any .blend that contains a Level Root):
#   tools/blender/run_blender.sh <file.blend> tools/blender/export_level.py -- <level_root> <level_name> [<levels_dir>]
#   <levels_dir> defaults to mods/sgl64/levels. Writes <levels_dir>/<level_name>/ and validates it.
# Other scripts: `from export_level import export_level` (see build_test_level.py).
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sgl_blender import setup_fast64  # noqa: E402
from sgl_util import PROJECT_ROOT  # noqa: E402

DEFAULT_LEVELS_DIR = os.path.join(PROJECT_ROOT, "mods", "sgl64", "levels")

# Files Fast64 writes for decomp builds that DynOS cannot parse (C structs / functions).
# DynOS reads EVERY *.c under levels/<name>/, so they are removed after export.
NON_DYNOS_FILES = ("camera_trigger.inc.c", "puppycam_trigger.inc.c", "texscroll.inc.c")


def speed_up_collision_export():
    """Fast64 looks every collision vertex up with a linear scan (O(n^2)); a campus-sized
    area (10k+ vertices) then takes minutes. Swap in a dict-backed lookup with the same
    results (first index of an equal position)."""
    from fast64.fast64_internal.sm64 import sm64_collision as col
    if getattr(col, "_sgl_fast_vert_index", False):
        return
    cache = {}

    def collision_vert_index(vert, vert_array):
        key = id(vert_array)
        entry = cache.get(key)
        if entry is None or entry[0] is not vert_array or entry[2] > len(vert_array):
            entry = [vert_array, {}, 0]
            cache.clear()
            cache[key] = entry
        lookup = entry[1]
        for i in range(entry[2], len(vert_array)):
            lookup.setdefault(vert_array[i].position, i)
        entry[2] = len(vert_array)
        return lookup.get(tuple(vert))

    col.collisionVertIndex = collision_vert_index
    col._sgl_fast_vert_index = True


def export_level(level_root_name, level_name, levels_dir=DEFAULT_LEVELS_DIR, setup=True, validate=True):
    """Export the Level Root `level_root_name` to <levels_dir>/<level_name>/.
    Returns (level_dir, validation report). Raises RuntimeError on failure."""
    if not level_name.replace("_", "").isalnum() or level_name != level_name.lower():
        raise RuntimeError(f"level name {level_name!r}: use lower_snake_case (it becomes level_{level_name}_entry)")
    levels_dir = os.path.abspath(levels_dir)
    os.makedirs(levels_dir, exist_ok=True)
    if setup:
        setup_fast64()
    speed_up_collision_export()

    scene = bpy.context.scene
    scene.gameEditorMode = "SM64"
    sm64 = scene.fast64.sm64
    sm64.export_type = "C"
    scene.saveTextures = False  # inline textures: DynOS cannot follow #include'd PNGs
    props = sm64.combined_export
    props.non_decomp_level = True  # "Custom Export Path": no decomp headers/tables are touched
    props.custom_level_path = levels_dir
    props.custom_level_name = level_name
    props.delete_all_lvls = True  # drop a stale level_<name>_entry.lvl next to the sources

    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    root = bpy.data.objects.get(level_root_name)
    if root is None or root.type != "EMPTY" or root.sm64_obj_type != "Level Root":
        raise RuntimeError(f"{level_root_name!r} is not a Level Root empty")
    for o in bpy.context.selected_objects:
        o.select_set(False)
    root.select_set(True)
    bpy.context.view_layer.objects.active = root

    # Fast64 "Export Hidden Geometry" unhides through bpy.ops.object.hide_view_clear(),
    # whose poll fails without a 3D view (--background). Unhide directly instead.
    hidden = [o for o in bpy.context.view_layer.objects if o.hide_get()]
    for o in hidden:
        o.hide_set(False)
    export_hidden = scene.exportHiddenGeometry
    scene.exportHiddenGeometry = False
    try:
        result = bpy.ops.object.sm64_export_level()
    finally:
        scene.exportHiddenGeometry = export_hidden
        for o in hidden:
            o.hide_set(True)
    level_dir = os.path.join(levels_dir, level_name)
    if result != {"FINISHED"} or not os.path.isfile(os.path.join(level_dir, "script.c")):
        raise RuntimeError(f"Fast64 level export failed: {result}")

    for fname in NON_DYNOS_FILES:
        path = os.path.join(level_dir, fname)
        if os.path.exists(path):
            os.remove(path)

    report = None
    if validate:
        from validate_level import validate_level
        report = validate_level(level_dir)
        print(report["text"])
        if report["errors"]:
            raise RuntimeError(f"{len(report['errors'])} validation error(s) in {level_dir}")
    print(f"EXPORT_LEVEL_RESULT {result} -> {level_dir}")
    return level_dir, report


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(argv) not in (2, 3):
        sys.exit("usage: -- <level_root> <level_name> [<levels_dir>]")
    try:
        export_level(*argv)
    except RuntimeError as e:
        print(e)
        sys.exit(1)
