# Shared helpers for running Fast64 headlessly (blender --background).
import addon_utils
import bpy


def setup_fast64():
    """Enable Fast64 and run the upgrade steps it normally runs from a load_post
    handler. In --background mode the add-on is enabled after the .blend loads, so
    without this, old-format data in the template (e.g. Custom geo command macros)
    is not migrated and exports as empty CUSTOM_CMD() lines."""
    mod = addon_utils.enable("fast64", default_set=True)
    if not mod:
        raise RuntimeError("Fast64 add-on failed to load")

    scene = bpy.context.scene
    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    mod.game_data.update(scene.gameEditorMode)
    settings = scene.fast64.settings
    strip_old_scene_properties_outputs()
    if bpy.app.version >= (4, 2, 0):
        if any(mat.is_f3d for mat in bpy.data.materials) and not settings.internal_fixed_4_2:
            mod.upgrade_f3d_version_all_meshes()
        settings.internal_fixed_4_2 = True
    mod.upgrade_changed_props()
    migrate_legacy_custom_geo_cmds()
    if any(mat.is_f3d and mat.mat_ver < mod.F3D_MAT_CUR_VERSION for mat in bpy.data.materials):
        bpy.ops.dialog.upgrade_f3d_materials("EXEC_DEFAULT")
    try:
        mod.resync_scene_props()
    except KeyError as e:
        # Re-opened build files (art/<id>/build/<id>.blend) keep only the Fast64 library
        # node groups that were in use when saved, so this viewport-preview-only resync
        # can miss e.g. "GeometryNormal_ViewSpace". Exporting does not need it.
        print(f"SGL: skipped Fast64 preview resync ({e})")
    return mod


def strip_old_scene_properties_outputs():
    """Fast64's createOrUpdateSceneProperties() upgrades an old "SceneProperties" node group
    by removing its outputs while iterating group.interface.items_tree, which reads freed
    memory: the intermittent segfault on macOS (about 1 in 14 loads) and a crash on every
    load on Linux. Remove those outputs here first, one at a time with a fresh lookup each
    time, so Fast64's loop finds nothing to remove. Fast64 then rebuilds the outputs."""
    if bpy.app.version < (4, 0, 0):
        return
    group = bpy.data.node_groups.get("SceneProperties")
    if group is None or group.get("version", -1) >= 2:  # Fast64's SCENE_PROPERTIES_VERSION
        return
    while True:
        item = next((i for i in group.interface.items_tree
                     if i.item_type == "SOCKET" and i.in_out == "OUTPUT"), None)
        if item is None:
            break
        group.interface.remove(item)


def migrate_legacy_custom_geo_cmds():
    """The coopdx template stores custom geo commands (geo_mario_set_player_colors,
    geo_mirror_mario_backface_culling) as raw bone["fast64"]["sm64"]["custom_geo_cmd_macro"
    / "custom_geo_cmd_args"], a layout Fast64's own upgrade misses. Move them into the
    current custom command properties so they export as e.g.
    GEO_ASM(LAYER_OPAQUE + 3, geo_mario_set_player_colors)."""
    migrated = 0
    for obj in bpy.data.objects:
        if obj.type != "ARMATURE":
            continue
        for bone in obj.data.bones:
            raw = bone.get("fast64")
            raw = raw.get("sm64") if raw is not None else None
            if raw is None or "custom_geo_cmd_macro" not in raw:
                continue
            custom = bone.fast64.sm64.custom
            custom.str_cmd = raw["custom_geo_cmd_macro"]
            custom.args.clear()
            arg = custom.args.add()
            arg.name = "args"
            arg.arg_type = "PARAMETER"
            arg.parameter = raw.get("custom_geo_cmd_args", "")
            custom.version = 1
            bone.geo_cmd = "Custom"
            del raw["custom_geo_cmd_macro"]
            if "custom_geo_cmd_args" in raw:
                del raw["custom_geo_cmd_args"]
            migrated += 1
    print(f"SGL: migrated {migrated} legacy custom geo commands")
    return migrated
