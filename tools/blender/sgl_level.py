"""Scene-building helpers for coopdx (DynOS) custom levels made headlessly with Fast64.

Units and axes
  Blender metres, Z up, X = east, Y = north (the same frame as data/uf/campus.json,
  origin = Century Tower). Fast64's Blender-to-SM64 scale is 100, so 1 m = 100 SM64
  units (Mario is ~161 units = 1.6 m): geometry built in metres is true 1:1 in game.
  After export: SM64 X = east, SM64 Y = up, SM64 Z = south (= -Blender Y).
  Yaw: an empty with no rotation faces SM64 +Z (= Blender -Y, south); rotate it by
  180 deg about Z to face north.

Level hierarchy Fast64 expects (what make_level / make_area build)
  Level Root (empty)            background
    Area Root (empty, index 1)  music, terrain, camera, warp nodes
      meshes ...                F3D materials; collision type per material
      Object empties            OBJECT(model, x, y, z, rx, ry, rz, bparams, behaviour)
      Mario Start empty         MARIO_POS(...)
      Water Box empty           COL_WATER_BOX(...)

Only call these after sgl_blender.setup_fast64() (they use Fast64 properties).
"""
import math
import os

import bmesh
import bpy

from sgl_util import hex_to_srgb, srgb_to_linear, write_png

SM64_SCALE = 100.0  # Fast64 blender_to_sm64_scale: 1 Blender unit (1 m) = 100 SM64 units

# Behaviours whose OBJECT DynOS indexes as a warp spawn (src/game/area.c sWarpBhvSpawnTable).
# warp_to_level() needs one of these with bparam2 = 0x0A in the target area.
WARP_SPAWN_BEHAVIORS = (
    "bhvDoorWarp", "bhvStar", "bhvExitPodiumWarp", "bhvWarp", "bhvWarpPipe", "bhvFadingWarp",
    "bhvInstantActiveWarp", "bhvAirborneWarp", "bhvHardAirKnockBackWarp", "bhvSpinAirborneCircleWarp",
    "bhvDeathWarp", "bhvSpinAirborneWarp", "bhvFlyingWarp", "bhvSwimmingWarp", "bhvPaintingStarCollectWarp",
    "bhvPaintingDeathWarp", "bhvAirborneStarCollectWarp", "bhvAirborneDeathWarp", "bhvLaunchStarCollectWarp",
    "bhvLaunchDeathWarp",
)


# ------------------------------------------------------------------ scene
def new_empty_scene():
    """Start from an empty file (no template materials, so setup_fast64() has nothing
    to upgrade and cannot hit the template-upgrade segfault)."""
    bpy.ops.wm.read_homefile(use_empty=True)


def configure_scene():
    scene = bpy.context.scene
    scene.gameEditorMode = "SM64"
    sm64 = scene.fast64.sm64
    sm64.export_type = "C"
    sm64.blender_to_sm64_scale = SM64_SCALE
    scene.saveTextures = False  # inline u8 texture arrays: no #include/PNG paths for DynOS to resolve
    return scene


def _link(obj):
    if obj.name not in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.link(obj)


def _empty(name, sm64_type, location=(0, 0, 0), yaw_deg=0.0, display="PLAIN_AXES", size=1.0, parent=None):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = display
    obj.empty_display_size = size
    _link(obj)
    obj.location = location
    obj.rotation_euler = (0.0, 0.0, math.radians(yaw_deg))
    obj.sm64_obj_type = sm64_type
    if parent is not None:
        obj.parent = parent
    return obj


# ------------------------------------------------------------------ level / area roots
def make_level(name, background="OCEAN_SKY", background_color=None):
    """Level Root empty. background: a Fast64 enumBackground key (OCEAN_SKY, ABOVE_CLOUDS,
    GREEN_SKY, ...) or None with background_color=(r, g, b) 0..1 for a solid colour."""
    root = _empty(name, "Level Root")
    if background is None:
        root.useBackgroundColor = True
        root.backgroundColor = (*(background_color or (0.45, 0.65, 0.9)), 1.0)
    else:
        root.useBackgroundColor = False
        root.background = background
    return root


def make_area(level_root, index=1, music="SEQ_LEVEL_GRASS", terrain="TERRAIN_GRASS",
              camera="CAMERA_MODE_FREE_ROAM", envfx="ENVFX_MODE_NONE", clip=(100, 30000), fov=45.0):
    """Area Root under level_root. clip = (near, far) in SM64 units; far is an s16 in
    GEO_CAMERA_FRUSTUM, so 32767 (~327 m) is the hard maximum view distance."""
    area = _empty(f"Area {index}", "Area Root", parent=level_root)
    area.areaIndex = index
    if music is None:
        area.noMusic = True
    elif music.startswith("SEQ_") and music in {i.identifier for i in bpy.types.Object.bl_rna.properties["musicSeqEnum"].enum_items}:
        area.musicSeqEnum = music
    else:
        area.musicSeqEnum = "Custom"
        area.music_seq = music
    area.terrainEnum = terrain
    area.camOption = camera
    area.envOption = envfx
    area.clipPlanes = clip
    area.fov = fov
    return area


def add_warp_node(area, warp_id, dest_level="LEVEL_CASTLE", dest_area=1, dest_node=0x0A,
                  checkpoint=False, painting=False):
    """WARP_NODE(id, destLevel, destArea, destNode, flags). dest_level must be a vanilla
    LEVEL_* constant: a custom level's number is only known at runtime (level_register),
    and coopdx v1.5.1 cannot resolve a Lua variable here (DynOS stores the token in the
    wrong word). Send players into custom levels from Lua (warp_to_level/warp_to_warpnode)."""
    wn = area.warpNodes.add()
    wn.warpType = "Painting" if painting else "Warp"
    wn.warpID = "0x%02X" % warp_id
    wn.destLevelEnum = "Custom"
    wn.destLevel = dest_level
    wn.destArea = "0x%02X" % dest_area
    wn.destNode = "0x%02X" % dest_node
    wn.warpFlagEnum = "WARP_CHECKPOINT" if checkpoint else "WARP_NO_CHECKPOINT"
    return wn


def add_instant_warp(area, index, dest_area, offset_units=(0, 0, 0)):
    """INSTANT_WARP(index, destArea, dx, dy, dz): seamless area change inside the SAME level,
    triggered by floors of type SURFACE_INSTANT_WARP_1B + index. Needs no level number."""
    wn = area.warpNodes.add()
    wn.warpType = "Instant"
    wn.warpID = "0x%02X" % index
    wn.destArea = "0x%02X" % dest_area
    wn.instantOffset = offset_units
    return wn


# ------------------------------------------------------------------ objects
def add_object(area, name, location, behavior, model="MODEL_NONE", bparams="0x00000000", yaw_deg=0.0,
               acts=None):
    """OBJECT(model, x, y, z, 0, yaw, 0, bparams, behavior). behavior / model / bparams may be
    vanilla symbols (bhvYellowCoin, MODEL_YELLOW_COIN) or the NAME of a Lua global of the
    mod (id_bhvSglFoo, E_MODEL_FOO, SGL_SIGN_BPARAM): DynOS turns any name it does not know
    into a Lua lookup at level load (OBJECT_EXT_LUA_PARAMS)."""
    obj = _empty(name, "Object", location, yaw_deg, display="SPHERE", size=0.5, parent=area)
    obj.sm64_model_enum = "Custom"
    obj.sm64_obj_model = model
    obj.sm64_behaviour_enum = "Custom"
    obj.sm64_obj_behaviour = behavior
    go = obj.fast64.sm64.game_object
    go.use_individual_params = False
    go.bparams = bparams
    if acts is not None:
        for i in range(1, 7):
            setattr(obj, f"sm64_obj_use_act{i}", i in acts)
    return obj


def add_spawn(area, location, yaw_deg=0.0, warp_id=0x0A, behavior="bhvSpinAirborneWarp", mario_start=True):
    """Spawn point: the warp-spawn OBJECT (bparam2 = warp_id) DynOS warps land on, plus
    MARIO_POS (Fast64 'Mario Start') for the level's default start."""
    spawn = add_object(area, "Spawn %02X" % warp_id, location, behavior, "MODEL_NONE",
                       "0x00%02X0000" % warp_id, yaw_deg)
    if mario_start:
        ms = _empty("Mario Start", "Mario Start", location, yaw_deg, parent=area)
        ms.sm64_obj_mario_start_area = "0x%02X" % area.areaIndex
    return spawn


def add_water_box(area, xmin, ymin, xmax, ymax, surface_z, bottom_z=None, toxic=False):
    """COL_WATER_BOX over [xmin, xmax] x [ymin, ymax] (metres) with the water surface at
    surface_z. SM64 water boxes are a surface height over an XZ rectangle: everything
    below surface_z inside the rectangle is water. Must not be rotated."""
    bottom_z = surface_z - 10.0 if bottom_z is None else bottom_z
    half_h = (surface_z - bottom_z) / 2.0
    box = _empty("Water Box", "Water Box", ((xmin + xmax) / 2, (ymin + ymax) / 2, bottom_z + half_h),
                 display="CUBE", size=1.0, parent=area)
    box.scale = ((xmax - xmin) / 2, (ymax - ymin) / 2, half_h)
    box.waterBoxType = "Toxic Haze" if toxic else "Water"
    return box


# ------------------------------------------------------------------ materials
def _f3d_mat(name, preset):
    from fast64.fast64_internal.f3d.f3d_material import createF3DMat
    mat = createF3DMat(None, preset)
    mat.name = name
    return mat


def _set_light(mat, hex_color):
    srgb = hex_to_srgb(hex_color)
    f = mat.f3d_mat
    if hasattr(f, "set_ambient_from_light"):
        f.set_ambient_from_light = False
    f.default_light_color = (*(srgb_to_linear(c) for c in srgb), 1.0)
    f.ambient_light_color = (*(srgb_to_linear(c * 0.5) for c in srgb), 1.0)
    mat.diffuse_color = (*(srgb_to_linear(c) for c in srgb), 1.0)


def _set_collision(mat, surface):
    mat.collision_all_options = True
    mat.collision_type = "Custom" if surface not in _collision_enum() else surface
    mat.collision_custom = surface
    if surface in _collision_simple_enum():
        mat.collision_type_simple = surface


def _collision_enum():
    return {i.identifier for i in bpy.types.Material.bl_rna.properties["collision_type"].enum_items}


def _collision_simple_enum():
    return {i.identifier for i in bpy.types.Material.bl_rna.properties["collision_type_simple"].enum_items}


def solid_material(name, hex_color, surface="SURFACE_DEFAULT"):
    """Vertex-lit solid colour (Fast64 preset sm64_shaded_solid)."""
    mat = _f3d_mat(name, "sm64_shaded_solid")
    _set_light(mat, hex_color)
    _set_collision(mat, surface)
    mat["sgl_tile_m"] = 0.0
    return mat


def textured_material(name, image, tile_m, surface="SURFACE_DEFAULT", tint="#FFFFFF"):
    """Lit, wrapping texture (sm64_shaded_texture); one texture repeat every tile_m metres
    (build_* helpers project UVs from that). image: a bpy image with power-of-two sides."""
    from sgl_materials import set_f3d_texture
    mat = _f3d_mat(name, "sm64_shaded_texture")
    set_f3d_texture(mat, image, clamp=False)
    _set_light(mat, tint)
    _set_collision(mat, surface)
    mat["sgl_tile_m"] = float(tile_m)
    return mat


def transparent_material(name, hex_color, alpha=0.55, cull_back=False):
    """See-through solid colour on draw layer 5 (LAYER_TRANSPARENT) for water surfaces etc.
    Built from sm64_shaded_solid: colour = shade * prim, alpha = prim alpha (1-cycle, no
    fog, so it does not depend on area fog settings)."""
    mat = _f3d_mat(name, "sm64_shaded_solid")
    f = mat.f3d_mat
    f.draw_layer.sm64 = "5"
    for comb in (f.combiner1, f.combiner2):
        comb.A, comb.B, comb.C, comb.D = "SHADE", "0", "PRIMITIVE", "0"
        comb.A_alpha, comb.B_alpha, comb.C_alpha, comb.D_alpha = "0", "0", "0", "PRIMITIVE"
    f.set_prim = True
    srgb = hex_to_srgb(hex_color)
    _set_light(mat, "#FFFFFF")
    f.prim_color = (*(srgb_to_linear(c) for c in srgb), alpha)
    f.rdp_settings.g_cull_back = cull_back
    _set_collision(mat, "SURFACE_DEFAULT")
    mat["sgl_tile_m"] = 0.0
    return mat


def make_image(name, rows, out_png=None):
    """bpy image from rows (top to bottom) of (r, g, b, a) 0-255 tuples. Packed into the
    .blend; also written to out_png when given (handy for review)."""
    h, w = len(rows), len(rows[0])
    img = bpy.data.images.new(name, w, h, alpha=True)
    px = []
    for row in reversed(rows):  # Blender images are stored bottom row first
        for r, g, b, a in row:
            px.extend((r / 255.0, g / 255.0, b / 255.0, a / 255.0))
    img.pixels[:] = px
    if out_png:
        write_png(out_png, rows)
        img.filepath_raw = out_png
        img.file_format = "PNG"
    img.pack()
    return img


# ------------------------------------------------------------------ geometry
class MeshBuilder:
    """Collects polygons (unshared vertices, so every face keeps its own UVs) and builds one
    mesh object. UVs are planar projections in metres / material tile size, shifted per face
    so texture coordinates stay small (Vtx UVs are s16 10.5 fixed point)."""

    def __init__(self):
        self.polys = []  # (points, material)

    def poly(self, pts, mat, normal_hint=None):
        pts = [tuple(map(float, p)) for p in pts]
        if normal_hint is not None:
            n = _normal(pts)
            if sum(a * b for a, b in zip(n, normal_hint)) < 0:
                pts.reverse()
        self.polys.append((pts, mat))

    def box(self, xmin, ymin, zmin, xmax, ymax, zmax, mat, top=None, bottom=False):
        """Axis-aligned box, outward faces. top: optional material for the top face."""
        x0, y0, z0, x1, y1, z1 = xmin, ymin, zmin, xmax, ymax, zmax
        self.poly([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], top or mat, (0, 0, 1))
        if bottom:
            self.poly([(x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0)], mat, (0, 0, -1))
        self.poly([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], mat, (0, -1, 0))
        self.poly([(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)], mat, (0, 1, 0))
        self.poly([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], mat, (1, 0, 0))
        self.poly([(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)], mat, (-1, 0, 0))

    def ramp_north(self, xmin, xmax, y_low, y_high, z_base, z_top, mat):
        """Wedge rising from z_base at y_low to z_top at y_high (walk up heading north)."""
        x0, x1 = xmin, xmax
        self.poly([(x0, y_low, z_base), (x1, y_low, z_base), (x1, y_high, z_top), (x0, y_high, z_top)], mat, (0, -1, 1))
        self.poly([(x1, y_high, z_base), (x0, y_high, z_base), (x0, y_high, z_top), (x1, y_high, z_top)], mat, (0, 1, 0))
        self.poly([(x1, y_low, z_base), (x1, y_high, z_base), (x1, y_high, z_top)], mat, (1, 0, 0))
        self.poly([(x0, y_high, z_base), (x0, y_low, z_base), (x0, y_high, z_top)], mat, (-1, 0, 0))

    def grid(self, xmin, ymin, xmax, ymax, z, cell, mat, skip=None):
        """Flat ground of cell x cell squares; skip(cx, cy) -> True leaves a hole
        (cx, cy = lower-left corner of the cell)."""
        nx, ny = round((xmax - xmin) / cell), round((ymax - ymin) / cell)
        for i in range(nx):
            for j in range(ny):
                cx, cy = xmin + i * cell, ymin + j * cell
                if skip and skip(cx, cy):
                    continue
                self.poly([(cx, cy, z), (cx + cell, cy, z), (cx + cell, cy + cell, z), (cx, cy + cell, z)],
                          mat, (0, 0, 1))

    def build(self, name, parent=None, ignore_collision=False, ignore_render=False):
        mats = []
        for _, m in self.polys:
            if m not in mats:
                mats.append(m)
        me = bpy.data.meshes.new(name)
        bm = bmesh.new()
        uv = bm.loops.layers.uv.new("UVMap")
        for pts, m in self.polys:
            verts = [bm.verts.new(p) for p in pts]
            face = bm.faces.new(verts)
            face.material_index = mats.index(m)
            face.smooth = False
            tile = float(m.get("sgl_tile_m", 0.0)) if m is not None else 0.0
            for loop, (u, v) in zip(face.loops, _planar_uvs(pts, tile)):
                loop[uv].uv = (u, v)
        bm.to_mesh(me)
        bm.free()
        obj = bpy.data.objects.new(name, me)
        _link(obj)
        for m in mats:
            me.materials.append(m)
        from fast64.fast64_internal.f3d.f3d_material import addColorAttributesToModel
        addColorAttributesToModel(obj)
        obj.ignore_collision = ignore_collision
        obj.ignore_render = ignore_render
        if parent is not None:
            obj.parent = parent
        return obj


def _normal(pts):
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = pts[0], pts[1], pts[2]
    ux, uy, uz = bx - ax, by - ay, bz - az
    vx, vy, vz = cx - ax, cy - ay, cz - az
    return (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)


def _planar_uvs(pts, tile):
    if tile <= 0:
        return [(0.0, 0.0)] * len(pts)
    nx, ny, nz = (abs(c) for c in _normal(pts))
    if nz >= nx and nz >= ny:
        uvs = [(p[0] / tile, p[1] / tile) for p in pts]  # floor / roof: top-down projection
    elif nx >= ny:
        uvs = [(p[1] / tile, p[2] / tile) for p in pts]  # east / west wall
    else:
        uvs = [(p[0] / tile, p[2] / tile) for p in pts]  # north / south wall
    du = math.floor(min(u for u, _ in uvs))
    dv = math.floor(min(v for _, v in uvs))
    return [(u - du, v - dv) for u, v in uvs]


def hierarchy(root):
    """root and all its descendants."""
    out = [root]
    for c in root.children:
        out.extend(hierarchy(c))
    return out


def tri_count(objs):
    n = 0
    for o in objs:
        if o.type == "MESH":
            o.data.calc_loop_triangles()
            n += len(o.data.loop_triangles)
    return n


def checker_rows(size, a_hex, b_hex, cells=4, noise=10, seed=1):
    """Two-colour checker with a little deterministic noise (procedural placeholder texture)."""
    import random
    rnd = random.Random(seed)
    a = tuple(int(a_hex.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    b = tuple(int(b_hex.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    step = size // cells
    rows = []
    for y in range(size):
        row = []
        for x in range(size):
            base = a if ((x // step) + (y // step)) % 2 == 0 else b
            d = rnd.randint(-noise, noise)
            row.append(tuple(max(0, min(255, c + d)) for c in base) + (255,))
        rows.append(row)
    return rows


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path
