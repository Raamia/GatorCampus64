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
