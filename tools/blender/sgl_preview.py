"""Preview renders for built characters (run AFTER saving/exporting: it swaps
materials and poses the rig, and the caller must not save afterwards).

The F3D materials are replaced by emission materials that emulate how coopdx
(gfx_pc.c) shades them, so the previews show the in-game look:
  - vertex shading in sRGB space: colour = ambient + diffuse * max(0, N.L) with the
    material's own Lights1 colours and the light direction (0x28, 0x28, 0x28) given in
    EYE space, i.e. light from camera right + up + toward the viewer (it follows the
    camera in every view, as in game)
  - face materials, combiner (TEXEL0 - SHADE) * TEXEL0_ALPHA + SHADE: the texel is shown
    UNLIT where alpha = 1 and the shaded skin elsewhere
  - textures are sampled bilinearly with clamping, and the UVs are scaled by
    texture size / exported tile size (gsDPSetTileSize), which is what coopdx does:
    a tile that does not match the texture shows up squeezed/stretched here too.
"""
import json
import math
import os

import bpy
import numpy as np
from mathutils import Vector

PREVIEW_ACTION = "In-Game Example (DO NOT EXPORT WITH THIS)"
BG = (0.42, 0.44, 0.47)  # neutral grey-blue, sRGB-ish
# wing-cap wings only render while wearing the wing cap (geo_switch_mario_cap_on_off)
HIDDEN_IN_PREVIEW = ("Wing Base", "Wing Tip", "Metal Wing Base (METAL)", "Metal Wing Tip (METAL)")
LIGHT_DIR_EYE = Vector((1.0, 1.0, 1.0)).normalized()  # camera space: x right, y up, z toward viewer
METAL_SRGB = (0.62, 0.63, 0.66)


def _lin_to_srgb(c):
    return c * 12.92 if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def _f3d_info(mat):
    f = getattr(mat, "f3d_mat", None)
    if f is None or not getattr(mat, "is_f3d", False):
        return (0.8, 0.8, 0.8), (0.4, 0.4, 0.4), None, False, (1.0, 1.0)
    col = tuple(_lin_to_srgb(c) for c in f.default_light_color[:3])
    amb = tuple(_lin_to_srgb(c) for c in f.ambient_light_color[:3])
    img = None
    try:
        if f.tex0.tex_set and f.tex0.tex is not None:
            img = f.tex0.tex
    except Exception:
        img = None
    comb = f.combiner1
    texel_unlit = img is not None and comb.A == "TEXEL0" and comb.B == "SHADE" and comb.C == "TEXEL0_ALPHA"
    scale = (1.0, 1.0)
    if img is not None and img.size[0] > 0:
        t = f.tex0
        scale = (img.size[0] / (round(t.S.high - t.S.low) + 1), img.size[1] / (round(t.T.high - t.T.low) + 1))
        if scale != (1.0, 1.0):
            print(f"SGL PREVIEW WARNING: {mat.name}: tile {round(t.S.high) + 1}x{round(t.T.high) + 1} does not "
                  f"match texture {img.size[0]}x{img.size[1]} (rendered as coopdx would)")
    return col, amb, img, texel_unlit, scale


_LIGHT_NODES = []  # (material name, node name) of every light-direction input, see set_light_dir()


def set_light_dir(cam):
    """Point the preview light along eye-space (1, 1, 1) of `cam` (camera object: local
    +x right, +y up, +z toward the viewer), in world space, in every preview material."""
    bpy.context.view_layer.update()  # matrix_world is stale right after aim()
    d = (cam.matrix_world.to_3x3() @ LIGHT_DIR_EYE).normalized()
    for mname, nname in _LIGHT_NODES:
        m = bpy.data.materials.get(mname)
        if m is not None:
            m.node_tree.nodes[nname].inputs[1].default_value = d


def _shade_node(nt, col, amb, mat_name):
    """Node output: N64 vertex shade (linear, for emission) for light colour col / ambient amb (sRGB)."""
    N, L = nt.nodes, nt.links
    geo = N.new("ShaderNodeNewGeometry")
    dot = N.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    L.new(geo.outputs["Normal"], dot.inputs[0])
    dot.inputs[1].default_value = LIGHT_DIR_EYE
    _LIGHT_NODES.append((mat_name, dot.name))
    mx = N.new("ShaderNodeMath")
    mx.operation = "MAXIMUM"
    L.new(dot.outputs["Value"], mx.inputs[0])
    mx.inputs[1].default_value = 0.0
    sc = N.new("ShaderNodeVectorMath")
    sc.operation = "SCALE"
    sc.inputs[0].default_value = col
    L.new(mx.outputs[0], sc.inputs["Scale"])
    add = N.new("ShaderNodeVectorMath")
    add.operation = "ADD"
    L.new(sc.outputs[0], add.inputs[0])
    add.inputs[1].default_value = amb
    mn = N.new("ShaderNodeVectorMath")
    mn.operation = "MINIMUM"
    L.new(add.outputs[0], mn.inputs[0])
    mn.inputs[1].default_value = (1.0, 1.0, 1.0)
    gam = N.new("ShaderNodeGamma")  # sRGB -> linear (approx.) for the emission output
    L.new(mn.outputs[0], gam.inputs["Color"])
    gam.inputs["Gamma"].default_value = 2.2
    return gam.outputs[0]


def _tex_node(nt, img, scale):
    N, L = nt.nodes, nt.links
    tex = N.new("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = "Linear"  # N64 / coopdx bilinear filtering
    tex.extension = "EXTEND"       # G_TX_CLAMP
    if scale != (1.0, 1.0):
        uv = N.new("ShaderNodeTexCoord")
        sep = N.new("ShaderNodeSeparateXYZ")
        L.new(uv.outputs["UV"], sep.inputs[0])
        mu = N.new("ShaderNodeMath")
        mu.operation = "MULTIPLY"
        L.new(sep.outputs[0], mu.inputs[0])
        mu.inputs[1].default_value = scale[0]
        # v' = 1 - (1 - v) * kt   (N64 T runs top-down, Blender V bottom-up)
        mv = N.new("ShaderNodeMath")
        mv.operation = "MULTIPLY_ADD"
        L.new(sep.outputs[1], mv.inputs[0])
        mv.inputs[1].default_value = scale[1]
        mv.inputs[2].default_value = 1.0 - scale[1]
        comb = N.new("ShaderNodeCombineXYZ")
        L.new(mu.outputs[0], comb.inputs[0])
        L.new(mv.outputs[0], comb.inputs[1])
        L.new(comb.outputs[0], tex.inputs["Vector"])
    return tex


def preview_material(mat):
    name = "PREVIEW " + mat.name
    pm = bpy.data.materials.get(name)
    if pm is not None:
        return pm
    pm = bpy.data.materials.new(name)
    pm.use_nodes = True
    nt = pm.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    pm.use_backface_culling = True
    if mat.name in HIDDEN_IN_PREVIEW:
        nt.links.new(nt.nodes.new("ShaderNodeBsdfTransparent").outputs[0], out.inputs["Surface"])
        return pm
    col, amb, img, texel_unlit, scale = _f3d_info(mat)
    is_metal = "METAL" in mat.name.upper()
    if is_metal:
        col, amb, img = METAL_SRGB, tuple(c * 0.5 for c in METAL_SRGB), None
    shade = _shade_node(nt, col, amb, pm.name)
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Strength"].default_value = 1.0
    shader = emit.outputs[0]
    if img is None:
        nt.links.new(shade, emit.inputs["Color"])
    else:
        tex = _tex_node(nt, img, scale)
        mix = nt.nodes.new("ShaderNodeMixRGB")
        if texel_unlit:
            # (TEXEL0 - SHADE) * TEXEL0_ALPHA + SHADE
            nt.links.new(tex.outputs["Alpha"], mix.inputs[0])
            nt.links.new(shade, mix.inputs[1])
            nt.links.new(tex.outputs["Color"], mix.inputs[2])
            nt.links.new(mix.outputs[0], emit.inputs["Color"])
        else:
            # plain textured (wings): texture * shade, alpha clip
            mix.blend_type = "MULTIPLY"
            mix.inputs[0].default_value = 1.0
            nt.links.new(tex.outputs["Color"], mix.inputs[1])
            nt.links.new(shade, mix.inputs[2])
            nt.links.new(mix.outputs[0], emit.inputs["Color"])
            transp = nt.nodes.new("ShaderNodeBsdfTransparent")
            m2 = nt.nodes.new("ShaderNodeMixShader")
            nt.links.new(tex.outputs["Alpha"], m2.inputs[0])
            nt.links.new(transp.outputs[0], m2.inputs[1])
            nt.links.new(emit.outputs[0], m2.inputs[2])
            shader = m2.outputs[0]
    nt.links.new(shader, out.inputs["Surface"])
    return pm


def swap_to_preview_materials(obj):
    for slot in obj.material_slots:
        if slot.material is not None and not slot.material.name.startswith("PREVIEW "):
            slot.link = "OBJECT"
            slot.material = preview_material(obj.data.materials[slot.slot_index] or slot.material)


def _eval_bbox(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in objs:
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        mw = o.matrix_world
        pts.extend(mw @ v.co for v in me.vertices)
        ev.to_mesh_clear()
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def frame_bbox(obj, arm):
    """World bbox of the posed mesh for framing the standard previews. The wing-cap wings
    are hidden in the previews but still set the top and back of the frame; a character
    module's WING_SHIFT moves them (sgl_body.move_wings records each wing's parent bone
    and armature-space move in obj["sgl_wing_shift"]), so their vertices are counted
    where the template has them: the preview scale stays that of every other character
    instead of shrinking the body whenever the wings move out of big hair."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    mw = obj.matrix_world
    pts = [mw @ v.co for v in me.vertices]
    ev.to_mesh_clear()
    try:
        moves = json.loads(obj.get("sgl_wing_shift", "{}"))
    except (TypeError, ValueError):
        moves = {}
    for group, mv in moves.items():
        vg = obj.vertex_groups.get(group)
        pb = arm.pose.bones.get(mv.get("parent", ""))
        if vg is None or pb is None:
            continue
        # every bone of the wing chain moved by delta in rest pose: the posed wing
        # moves by the parent bone's deform (rotation part) applied to delta
        deform = pb.matrix @ pb.bone.matrix_local.inverted()
        off = (arm.matrix_world.to_3x3() @ deform.to_3x3()) @ Vector(mv["delta"])
        for v in obj.data.vertices:
            if any(g.group == vg.index and g.weight > 0.4 for g in v.groups):
                pts[v.index] = pts[v.index] - off
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def _group_center(obj, group_name):
    dg = bpy.context.evaluated_depsgraph_get()
    gi = obj.vertex_groups[group_name].index
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    src = obj.data
    pts = []
    for v, v2 in zip(src.vertices, me.vertices):
        for g in v.groups:
            if g.group == gi and g.weight > 0.5:
                pts.append(obj.matrix_world @ v2.co)
    ev.to_mesh_clear()
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def setup_scene(size):
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    try:
        scene.eevee.taa_render_samples = 16
    except Exception:
        pass
    scene.render.resolution_x = size
    scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    world = scene.world or bpy.data.worlds.new("Preview World")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg is None:
        bg = world.node_tree.nodes.new("ShaderNodeBackground")
        world.node_tree.links.new(bg.outputs[0], world.node_tree.nodes.new("ShaderNodeOutputWorld").inputs[0])
    lin = tuple(((c + 0.055) / 1.055) ** 2.4 for c in BG)
    bg.inputs[0].default_value = (*lin, 1.0)
    bg.inputs[1].default_value = 1.0
    cam_data = bpy.data.cameras.new("Preview Cam")
    cam_data.type = "ORTHO"
    cam = bpy.data.objects.new("Preview Cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    return cam


def aim(obj, target, direction, dist):
    obj.location = target + direction.normalized() * dist
    obj.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()


def render_to(path):
    set_light_dir(bpy.context.scene.camera)
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("SGL_PREVIEW", path)


def compose_grid(paths, out_path, cols, labels=None):
    imgs = []
    for p in paths:
        im = bpy.data.images.load(p, check_existing=False)
        w, h = im.size
        arr = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
        imgs.append(arr)
        bpy.data.images.remove(im)
    h, w = imgs[0].shape[:2]
    rows = (len(imgs) + cols - 1) // cols
    pad = 6
    sheet = np.ones(((h + pad) * rows + pad, (w + pad) * cols + pad, 4), dtype=np.float32) * 0.15
    sheet[..., 3] = 1.0
    for i, arr in enumerate(imgs):
        r, c = divmod(i, cols)
        # numpy image rows are bottom-to-top (Blender), so place from the bottom
        y0 = (rows - 1 - r) * (h + pad) + pad
        x0 = c * (w + pad) + pad
        sheet[y0:y0 + h, x0:x0 + w] = arr
    H, W = sheet.shape[:2]
    out = bpy.data.images.new("sheet", W, H, alpha=True)
    out.pixels = sheet.ravel()
    out.filepath_raw = out_path
    out.file_format = "PNG"
    out.save()
    bpy.data.images.remove(out)
    for p in paths:
        try:
            os.remove(p)
        except OSError:
            pass
    print("SGL_PREVIEW", out_path)


def render_character(out_dir, armature="Mario", mesh="Mario Mesh", size=768, eye_materials=None,
                     extra_states=None, prefix=""):
    """Render front/back/left/three_quarter/head previews of the posed character.
    eye_materials: optional list of (label, image) to render an eye-state sheet
    by swapping the open-eye texture."""
    os.makedirs(out_dir, exist_ok=True)
    arm = bpy.data.objects[armature]
    body = bpy.data.objects[mesh]
    act = bpy.data.actions.get(PREVIEW_ACTION)
    if act is not None:
        if arm.animation_data is None:
            arm.animation_data_create()
        arm.animation_data.action = act
    bpy.context.scene.frame_set(0)

    for o in bpy.data.objects:
        o.hide_render = o is not body
    swap_to_preview_materials(body)

    cam = setup_scene(size)
    lo, hi = frame_bbox(body, arm)
    center = (lo + hi) / 2
    height = hi.z - lo.z
    cam.data.ortho_scale = max(height, hi.x - lo.x, hi.y - lo.y) * 1.12
    dist = 10.0

    files = {}
    views = {
        "front": Vector((0, -1, 0.08)),
        "back": Vector((0, 1, 0.08)),
        "left": Vector((1, 0, 0.08)),
        "three_quarter": Vector((0.75, -1, 0.25)),
    }
    for name, d in views.items():
        aim(cam, center, d, dist)
        p = os.path.join(out_dir, f"{prefix}{name}.png")
        render_to(p)
        files[name] = p

    # head close-up
    hlo, hhi = _group_center(body, "Head DL")
    hc = (hlo + hhi) / 2
    hsize = max(hhi.x - hlo.x, hhi.y - hlo.y, hhi.z - hlo.z)
    cam.data.ortho_scale = hsize * 1.25
    aim(cam, hc, Vector((0.35, -1, 0.12)), dist)
    p = os.path.join(out_dir, f"{prefix}head.png")
    render_to(p)
    files["head"] = p
    aim(cam, hc, Vector((1, -0.25, 0.05)), dist)
    p = os.path.join(out_dir, f"{prefix}head_side.png")
    render_to(p)
    files["head_side"] = p

    if eye_materials:
        open_prev = None
        for slot in body.material_slots:
            if slot.material and slot.material.name == "PREVIEW Open Eyes (SKIN)":
                open_prev = slot.material
        tex_node = None
        if open_prev is not None:
            for n in open_prev.node_tree.nodes:
                if n.type == "TEX_IMAGE":
                    tex_node = n
        if tex_node is not None:
            orig = tex_node.image
            s = bpy.context.scene
            s.render.resolution_x = s.render.resolution_y = size // 2
            aim(cam, hc, Vector((0, -1, 0.05)), dist)
            cam.data.ortho_scale = hsize * 1.1
            tiles = []
            for label, img in eye_materials:
                tex_node.image = img
                p = os.path.join(out_dir, f"_eye_{label}.png")
                render_to(p)
                tiles.append(p)
            tex_node.image = orig
            s.render.resolution_x = s.render.resolution_y = size
            sheet = os.path.join(out_dir, f"{prefix}eye_states.png")
            compose_grid(tiles, sheet, cols=4)
            files["eye_states"] = sheet
    return files
