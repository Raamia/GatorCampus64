"""F3D materials for the campus stages (inside Blender, after sgl_blender.setup_fast64()).

Every visual material is a Fast64 *fog* material (sm64_fog_shaded_texture[_cutout|_transparent])
that uses the Area's fog, so the whole stage fades into the sky before the ~327 m camera far clip.
"""
import bpy

from stage_palette import MATERIALS, texture_path

PRESET = {"opaque": "sm64_fog_shaded_texture", "cutout": "sm64_fog_shaded_texture_cutout",
          "water": "sm64_fog_shaded_texture_transparent"}


def _srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _hex(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def _set_light(mat, srgb, ambient_k=0.5):
    f = mat.f3d_mat
    # Fog presets may omit light commands. Never inherit an actor's lights:
    # visible actors (and therefore the inherited tint) change with the camera.
    f.set_lights = True
    if hasattr(f, "set_ambient_from_light"):
        f.set_ambient_from_light = False
    f.default_light_color = (*(_srgb_to_linear(c) for c in srgb), 1.0)
    f.ambient_light_color = (*(_srgb_to_linear(c * ambient_k) for c in srgb), 1.0)


def _set_collision(mat, surface):
    mat.collision_all_options = True
    enum = {i.identifier for i in bpy.types.Material.bl_rna.properties["collision_type"].enum_items}
    mat.collision_type = surface if surface in enum else "Custom"
    mat.collision_custom = surface
    simple = {i.identifier for i in bpy.types.Material.bl_rna.properties["collision_type_simple"].enum_items}
    if surface in simple:
        mat.collision_type_simple = surface


def make_materials(light_hex="#FFFFFF", ambient_k=0.55):
    """-> {name: bpy material} for every stage_palette material + 'COL default' / 'COL nocam'."""
    from fast64.fast64_internal.f3d.f3d_material import createF3DMat
    from sgl_materials import set_f3d_texture
    out = {}
    for name, m in MATERIALS.items():
        mat = createF3DMat(None, PRESET[m["kind"]])
        mat.name = f"sgl {name}"
        img = bpy.data.images.load(texture_path(name), check_existing=True)
        img.name = m["tex"]
        set_f3d_texture(mat, img, clamp=False)
        f = mat.f3d_mat
        f.use_global_fog = True
        f.set_fog = True
        if m["kind"] == "cutout":
            f.set_env = True
            f.env_color = (1.0, 1.0, 1.0, 1.0)
            f.rdp_settings.g_cull_back = False
        if m["kind"] == "water":
            f.set_prim = True
            f.prim_color = (1.0, 1.0, 1.0, float(m.get("alpha", 0.7)))
            f.rdp_settings.g_cull_back = False
        _set_light(mat, _hex(light_hex), ambient_k)
        mat.diffuse_color = (*(_srgb_to_linear(c) for c in _hex(m["color"])), 1.0)
        _set_collision(mat, "SURFACE_DEFAULT")
        mat["sgl_tile_m"] = float(m["tile_m"])
        mat["sgl_name"] = name
        out[name] = mat
    for key, surface in (("COL default", "SURFACE_DEFAULT"), ("COL nocam", "SURFACE_NO_CAM_COLLISION")):
        mat = createF3DMat(None, "sm64_shaded_solid")
        mat.name = f"sgl {key}"
        _set_light(mat, (0.8, 0.2, 0.8))
        _set_collision(mat, surface)
        mat["sgl_tile_m"] = 0.0
        mat["sgl_name"] = key
        out[key] = mat
    return out


def tiles():
    t = {name: float(m["tile_m"]) for name, m in MATERIALS.items()}
    t["COL default"] = 0.0
    t["COL nocam"] = 0.0
    return t


# ------------------------------------------------------------------ interior kit (opt-in)
# Interior stages (tools/campus/interior_kit.py) add these to the stage's material dict:
#     mats = make_materials(); mats.update(make_interior_materials())
#     tiles = tiles(); tiles.update(interior_tiles())
# make_materials() / tiles() above are unchanged, so outdoor stage builds stay byte-identical.
# Vertex-lit materials ("lit": "vertex" in stage_palette.INTERIOR_MATERIALS, the default) use the same
# fog presets with G_LIGHTING off: Fast64 then exports the mesh's "Col" colour attribute as the vertex
# shade (TEXEL0 * SHADE), which is where interior_kit bakes its ambient / AO / ceiling-light lighting.
INTERIOR_COLLISION = {
    "COL notslip": "SURFACE_NOT_SLIPPERY",   # stair ramps and steep-ish decks: never slide
    "COL hangable": "SURFACE_HANGABLE",      # undersides Mario can hang from and shimmy along (light ring)
}


def make_interior_materials(lit=None, light_hex="#FFFFFF", ambient_k=0.55, world_lighting_default=True):
    """-> {name: bpy material} for every stage_palette.INTERIOR_MATERIALS entry ('sgl int_*') plus
    'COL notslip' and 'COL hangable'. lit: None = each entry's "lit" ("vertex"), or force "vertex" /
    "normal" for all (normal = lit like the campus materials, light_hex / ambient_k as make_materials).

    world_lighting_default: Fast64 writes each material's geometry mode as the difference from the scene
    world's rdp_defaults and reverts it afterwards, but every exported display list ends by turning
    G_LIGHTING back ON (the SM64 engine state between display lists). In these headless scenes the world
    default has G_LIGHTING off (outdoor materials all set it themselves), so a vertex-lit material would
    emit nothing and be drawn LIT whenever it comes first in a display list. True (default) pins the
    scene's Fast64 world and sets its default G_LIGHTING on: vertex-lit materials then emit
    gsSPClearGeometryMode(G_LIGHTING) and restore it in their revert, and normal-lit materials rely on
    the engine default. Only interior builds call this, so outdoor builds are unchanged."""
    from fast64.fast64_internal.f3d.f3d_material import createF3DMat
    from sgl_materials import set_f3d_texture
    from stage_palette import INTERIOR_MATERIALS
    if world_lighting_default:
        from fast64.fast64_internal.utility import create_or_get_world
        scene = bpy.context.scene
        world = create_or_get_world(scene)
        if scene.world is None:
            scene.world = world
        world.rdp_defaults.g_lighting = True
    out = {}
    for name, m in INTERIOR_MATERIALS.items():
        mode = lit or m.get("lit", "vertex")
        mat = createF3DMat(None, PRESET[m["kind"]])
        mat.name = f"sgl {name}"
        img = bpy.data.images.load(texture_path(name), check_existing=True)
        img.name = m["tex"]
        set_f3d_texture(mat, img, clamp=False)
        f = mat.f3d_mat
        f.use_global_fog = True
        f.set_fog = True
        if m["kind"] == "cutout":
            f.set_env = True
            f.env_color = (1.0, 1.0, 1.0, 1.0)
            f.rdp_settings.g_cull_back = False
        if m["kind"] == "water":
            f.set_prim = True
            f.prim_color = (1.0, 1.0, 1.0, float(m.get("alpha", 0.7)))
            f.rdp_settings.g_cull_back = False
        if mode == "vertex":
            f.rdp_settings.g_lighting = False      # shade = the "Col" vertex colours
            if hasattr(f, "set_lights"):
                f.set_lights = False
        else:
            _set_light(mat, _hex(light_hex), ambient_k)
        mat.diffuse_color = (*(_srgb_to_linear(c) for c in _hex(m["color"])), 1.0)
        _set_collision(mat, "SURFACE_DEFAULT")
        mat["sgl_tile_m"] = float(m["tile_m"])
        mat["sgl_name"] = name
        mat["sgl_lit"] = mode
        out[name] = mat
    for key, surface in INTERIOR_COLLISION.items():
        mat = createF3DMat(None, "sm64_shaded_solid")
        mat.name = f"sgl {key}"
        _set_light(mat, (0.8, 0.2, 0.8))
        _set_collision(mat, surface)
        mat["sgl_tile_m"] = 0.0
        mat["sgl_name"] = key
        out[key] = mat
    return out


def interior_tiles():
    """tile_m of the interior kit materials (+ the two interior COL materials), for Stage.tiles."""
    from stage_palette import INTERIOR_MATERIALS
    t = {name: float(m["tile_m"]) for name, m in INTERIOR_MATERIALS.items()}
    for key in INTERIOR_COLLISION:
        t[key] = 0.0
    return t
