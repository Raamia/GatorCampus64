"""Preview renders of a built campus stage (run after export: materials are swapped).

Emulates what coopdx shows: texel x vertex shade (ambient + light . normal, light from the camera's
upper right, in sRGB space), bilinear repeating textures, the exact coopdx fog curve (fog factor =
(A - C / depth) * fm + fo, see build_stage.coop_fog_factor) mixed toward the fog colour, a sky
gradient for the skybox, and the camera far clip (the hub's set_override_far value).
"""
import math
import os

import bpy
from mathutils import Vector

LIGHT_EYE = Vector((1.0, 1.0, 1.0)).normalized()


def _lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _preview_mat(src, fog_params, fog_rgb):
    name = "PV " + src.name
    pm = bpy.data.materials.get(name)
    if pm:
        return pm
    f = src.f3d_mat
    img = f.tex0.tex if f.tex0.tex_set else None
    amb = tuple(f.ambient_light_color[:3])
    dif = tuple(f.default_light_color[:3])
    kind = "opaque"
    if f.draw_layer.sm64 == "4":
        kind = "cutout"
    elif f.draw_layer.sm64 == "5":
        kind = "water"
    pm = bpy.data.materials.new(name)
    pm.use_nodes = True
    nt = pm.node_tree
    N, Lk = nt.nodes, nt.links
    for n in list(N):
        N.remove(n)
    out = N.new("ShaderNodeOutputMaterial")
    emit = N.new("ShaderNodeEmission")
    # --- shade = min(1, amb + dif * max(0, n . L)) in sRGB, per channel (lights are linear in Fast64)
    geo = N.new("ShaderNodeNewGeometry")
    dot = N.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    dot.name = "light_dot"
    Lk.new(geo.outputs["Normal"], dot.inputs[0])
    mx = N.new("ShaderNodeMath")
    mx.operation = "MAXIMUM"
    mx.inputs[1].default_value = 0.0
    Lk.new(dot.outputs["Value"], mx.inputs[0])
    srgb = lambda c: c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055  # noqa: E731
    dif_s = tuple(srgb(c) for c in dif)
    amb_s = tuple(srgb(c) for c in amb)
    sc = N.new("ShaderNodeVectorMath")
    sc.operation = "SCALE"
    sc.inputs[0].default_value = dif_s
    Lk.new(mx.outputs[0], sc.inputs["Scale"])
    add = N.new("ShaderNodeVectorMath")
    add.operation = "ADD"
    add.inputs[1].default_value = amb_s
    Lk.new(sc.outputs[0], add.inputs[0])
    mn = N.new("ShaderNodeVectorMath")
    mn.operation = "MINIMUM"
    mn.inputs[1].default_value = (1, 1, 1)
    Lk.new(add.outputs[0], mn.inputs[0])
    # texel (sRGB) * shade
    tex_alpha = None
    if img is not None:
        tex = N.new("ShaderNodeTexImage")
        tex.image = img
        tex.interpolation = "Linear"
        tex.extension = "REPEAT"
        uv = N.new("ShaderNodeUVMap")
        Lk.new(uv.outputs["UV"], tex.inputs["Vector"])
        gam = N.new("ShaderNodeGamma")  # linear -> sRGB-ish
        gam.inputs["Gamma"].default_value = 1 / 2.2
        Lk.new(tex.outputs["Color"], gam.inputs["Color"])
        mul = N.new("ShaderNodeVectorMath")
        mul.operation = "MULTIPLY"
        Lk.new(gam.outputs[0], mul.inputs[0])
        Lk.new(mn.outputs[0], mul.inputs[1])
        col_s = mul.outputs[0]
        tex_alpha = tex.outputs["Alpha"]
    else:
        col_s = mn.outputs[0]
    # --- fog: depth (m) -> units -> fz = A - C/d -> f = clamp((fz*fm + fo)/255)
    fm, fo, (A, C) = fog_params
    cam = N.new("ShaderNodeCameraData")
    d_units = N.new("ShaderNodeMath")
    d_units.operation = "MULTIPLY"
    d_units.inputs[1].default_value = 100.0
    Lk.new(cam.outputs["View Z Depth"], d_units.inputs[0])
    inv = N.new("ShaderNodeMath")
    inv.operation = "DIVIDE"
    inv.inputs[0].default_value = C
    Lk.new(d_units.outputs[0], inv.inputs[1])
    fz = N.new("ShaderNodeMath")
    fz.operation = "SUBTRACT"
    fz.inputs[0].default_value = A
    Lk.new(inv.outputs[0], fz.inputs[1])
    lin = N.new("ShaderNodeMath")
    lin.operation = "MULTIPLY_ADD"
    lin.inputs[1].default_value = fm / 255.0
    lin.inputs[2].default_value = fo / 255.0
    lin.use_clamp = True
    Lk.new(fz.outputs[0], lin.inputs[0])
    en = N.new("ShaderNodeMath")
    en.operation = "MULTIPLY"
    en.name = "fog_enable"
    en.inputs[1].default_value = 1.0
    Lk.new(lin.outputs[0], en.inputs[0])
    mix = N.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    Lk.new(en.outputs[0], mix.inputs["Factor"])
    Lk.new(col_s, mix.inputs[6])
    mix.inputs[7].default_value = (*fog_rgb, 1.0)
    to_lin = N.new("ShaderNodeGamma")
    to_lin.inputs["Gamma"].default_value = 2.2
    Lk.new(mix.outputs[2], to_lin.inputs["Color"])
    Lk.new(to_lin.outputs[0], emit.inputs["Color"])
    if kind == "opaque" or tex_alpha is None and kind != "water":
        Lk.new(emit.outputs[0], out.inputs["Surface"])
    else:
        tr = N.new("ShaderNodeBsdfTransparent")
        ms = N.new("ShaderNodeMixShader")
        if kind == "cutout":
            rnd = N.new("ShaderNodeMath")
            rnd.operation = "GREATER_THAN"
            rnd.inputs[1].default_value = 0.5
            Lk.new(tex_alpha, rnd.inputs[0])
            Lk.new(rnd.outputs[0], ms.inputs[0])
        else:
            ms.inputs[0].default_value = float(f.prim_color[3])
        Lk.new(tr.outputs[0], ms.inputs[1])
        Lk.new(emit.outputs[0], ms.inputs[2])
        Lk.new(ms.outputs[0], out.inputs["Surface"])
        try:
            pm.surface_render_method = "DITHERED" if kind == "cutout" else "BLENDED"
        except Exception:  # noqa: BLE001
            pm.blend_method = "CLIP" if kind == "cutout" else "BLEND"
    return pm


def _set_view_params(cam, fog_on):
    bpy.context.view_layer.update()
    ldir = (cam.matrix_world.to_3x3() @ LIGHT_EYE).normalized()
    for m in bpy.data.materials:
        if not m.name.startswith("PV ") or not m.node_tree:
            continue
        n = m.node_tree.nodes.get("light_dot")
        if n:
            n.inputs[1].default_value = ldir
        e = m.node_tree.nodes.get("fog_enable")
        if e:
            e.inputs[1].default_value = 1.0 if fog_on else 0.0


def _world(fog_rgb):
    scene = bpy.context.scene
    w = bpy.data.worlds.new("SGL preview sky")
    scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (*(_lin(c) for c in fog_rgb), 1)
    ramp.color_ramp.elements[1].position = 0.45
    ramp.color_ramp.elements[1].color = (_lin(0.33), _lin(0.55), _lin(0.86), 1)
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs[0], out.inputs[0])


def _camera(name, loc, target, ortho=None, vfov=45.0, far_m=327.67):
    data = bpy.data.cameras.new(name)
    cam = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = loc
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
        data.clip_start = 1.0
        data.clip_end = 2000.0
    else:
        data.sensor_fit = "VERTICAL"
        data.angle_y = math.radians(vfov)
        data.clip_start = 0.3
        data.clip_end = far_m
    return cam


def render_all(S, out_dir, fog, fog_params, views=None, far_m=327.67):
    os.makedirs(out_dir, exist_ok=True)
    start, end, rgb8 = fog
    fog_rgb = tuple(c / 255.0 for c in rgb8)
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    try:
        scene.eevee.taa_render_samples = 8
    except Exception:  # noqa: BLE001
        pass
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.render.film_transparent = False
    _world(fog_rgb)
    _standins(S)
    for o in scene.objects:
        if o.type != "MESH":
            continue
        if getattr(o, "ignore_render", False):
            o.hide_render = True
            continue
        me = o.data
        for i, m in enumerate(me.materials):
            if m is not None and getattr(m, "is_f3d", False):
                me.materials[i] = _preview_mat(m, fog_params, fog_rgb)
    T = S.T
    H = S.data["extent_half_m"]
    if views is None:
        views = default_views(S)
    paths = []
    for v in views:
        if v.get("ortho"):
            cam = _camera(v["name"], (0, 0, 600), (0, 0, 0), ortho=v["ortho"])
            cam.rotation_euler = (0, 0, 0)
            scene.render.resolution_x = scene.render.resolution_y = v.get("px", 1600)
        else:
            (x, y, z), (tx, ty, tz) = v["cam"], v["target"]
            cam = _camera(v["name"], (*T((x, y)), z), (*T((tx, ty)), tz), vfov=v.get("vfov", 45.0), far_m=far_m)
            scene.render.resolution_x, scene.render.resolution_y = v.get("res", (1280, 720))
        scene.camera = cam
        _set_view_params(cam, v.get("fog", True))
        path = os.path.join(out_dir, v["name"] + ".png")
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print("SGL_PREVIEW", path)
        paths.append(path)
    return paths


def _standins(S):
    """Preview-only boxes for the level's objects (they are not meshes): wooden signposts, and a
    1.6 m Mario-sized figure at the spawn point for scale."""
    import bmesh
    from mathutils import Matrix
    made = []
    for o in list(bpy.context.scene.objects):
        if o.type != "EMPTY" or getattr(o, "sm64_obj_type", "") != "Object":
            continue
        model = getattr(o, "sm64_obj_model", "")
        loc = o.matrix_world.translation.copy()
        yaw = o.matrix_world.to_euler().z
        if model == "MODEL_WOODEN_SIGNPOST":
            boxes = [((-0.07, -0.07, 0.0), (0.07, 0.07, 0.8), "door_wood"),
                     ((-0.5, -0.05, 0.6), (0.5, 0.05, 1.3), "door_wood")]
        elif o.name.startswith("Spawn"):
            loc.z -= 1.0                              # spawn objects sit 1 m above the floor
            boxes = [((-0.28, -0.22, 0.0), (0.28, 0.22, 0.8), "window_glass"),
                     ((-0.3, -0.25, 0.8), (0.3, 0.25, 1.6), "door_marker")]
        else:
            continue
        bm = bmesh.new()
        mats = []
        for (x0, y0, z0), (x1, y1, z1), m in boxes:
            r = bmesh.ops.create_cube(bm, size=1.0)
            vs = r["verts"]
            bmesh.ops.scale(bm, vec=(x1 - x0, y1 - y0, z1 - z0), verts=vs)
            bmesh.ops.translate(bm, vec=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), verts=vs)
            if m not in mats:
                mats.append(m)
            for f in {f for v in vs for f in v.link_faces}:
                f.material_index = mats.index(m)
        me = bpy.data.meshes.new("PV standin " + o.name)
        bm.to_mesh(me)
        bm.free()
        for m in mats:
            me.materials.append(S.mats[m])
        me.uv_layers.new(name="UVMap")
        ob = bpy.data.objects.new("PV standin " + o.name, me)
        bpy.context.scene.collection.objects.link(ob)
        ob.matrix_world = Matrix.Translation(loc) @ Matrix.Rotation(yaw, 4, "Z")
        made.append(ob)
    return made


def default_views(S):
    H = S.data["extent_half_m"]
    return [
        {"name": "hub_topdown", "ortho": 2 * H, "fog": False, "px": 1600},
        # where Lakitu starts: 9 m behind Mario at the spawn, looking the way he faces (190 deg)
        {"name": "hub_spawn_view", "cam": (39.8, 151.3, 3.6), "target": (14.0, 6.0, 12.0), "vfov": 50.0},
        {"name": "hub_plaza_to_library_west", "cam": (38.2, 132.0, 2.2), "target": (38.9, 285.6, 9.0)},
        {"name": "hub_century_tower_auditorium", "cam": (-21.0, 56.0, 2.2), "target": (14.0, 4.0, 15.0)},
        {"name": "hub_turlington_marston", "cam": (8.0, -38.0, 2.2), "target": (-60.0, -33.0, 8.0)},
        {"name": "hub_birdseye", "cam": (150.0, -150.0, 120.0), "target": (-30.0, 120.0, 0.0), "vfov": 50.0},
        {"name": "hub_edge_check", "cam": (-270.0, 320.0, 2.2), "target": (-420.0, 470.0, 6.0)},
    ] + landmark_views()


def landmark_views():
    """Close views of every hand-modelled landmark from where a player walks up to it (camera about
    where Lakitu sits: 10-15 m behind Mario, 3-5 m up)."""
    return [
        {"name": "hub_lm_library_west", "cam": (38.9, 214.0, 4.0), "target": (38.9, 262.0, 11.0), "vfov": 55.0},
        {"name": "hub_lm_smathers", "cam": (98.0, 238.0, 2.0), "target": (128.0, 243.0, 8.0), "vfov": 60.0},
        {"name": "hub_lm_plaza_garden_terrace", "cam": (60.0, 228.0, 2.0), "target": (38.8, 246.0, 3.0),
         "vfov": 60.0},
        {"name": "hub_lm_century_tower", "cam": (-0.9, 44.0, 2.5), "target": (-0.9, 0.0, 20.0), "vfov": 62.0},
        {"name": "hub_lm_century_tower_top", "cam": (20.0, 20.0, 44.0), "target": (-0.9, -0.9, 38.0),
         "vfov": 55.0},
        {"name": "hub_lm_auditorium", "cam": (28.0, 100.0, 4.0), "target": (38.5, 50.0, 8.0), "vfov": 55.0},
        {"name": "hub_lm_auditorium_porch_door", "cam": (40.5, 76.0, 3.0), "target": (38.5, 62.0, 3.0),
         "vfov": 55.0},
        {"name": "hub_lm_century_tower_final_exam_door", "cam": (-20.0, 3.0, 2.5), "target": (-4.0, -1.0, 4.0),
         "vfov": 60.0},
        {"name": "hub_lm_turlington_potato", "cam": (-18.0, 44.0, 4.0), "target": (-52.0, 28.0, 5.0),
         "vfov": 55.0},
        {"name": "hub_lm_marston", "cam": (-50.0, -38.0, 4.0), "target": (-60.0, -75.0, 10.0), "vfov": 55.0},
        {"name": "hub_lm_the_hub", "cam": (-180.0, -103.0, 4.0), "target": (-198.0, -78.0, 5.0), "vfov": 60.0},
        {"name": "hub_lm_newell_east", "cam": (-128.0, 24.0, 4.0), "target": (-168.0, 30.0, 9.0), "vfov": 55.0},
        {"name": "hub_lm_newell_west_door", "cam": (-228.0, 34.0, 4.0), "target": (-205.0, 30.0, 6.0),
         "vfov": 55.0},
        {"name": "hub_lm_the_hub_far", "cam": (-140.0, -150.0, 6.0), "target": (-200.0, -80.0, 8.0), "vfov": 50.0},
        {"name": "hub_lm_bronze_gator", "cam": (43.5, 232.5, 2.4), "target": (38.8, 238.3, 1.0), "vfov": 50.0},
        {"name": "hub_lm_the_hub_entry", "cam": (-186.0, -96.0, 2.4), "target": (-195.5, -83.5, 4.0), "vfov": 60.0},
        # generator round 3: climb routes, plaza trees, set dressing, fog reach
        {"name": "hub_climb_criser", "cam": (128.0, 172.0, 4.0), "target": (148.0, 172.0, 8.0), "vfov": 60.0},
        {"name": "hub_climb_peabody", "cam": (92.0, 142.0, 3.0), "target": (112.0, 142.0, 7.0), "vfov": 60.0},
        {"name": "hub_climb_griffin_floyd", "cam": (-15.0, 145.0, 3.0), "target": (-37.0, 145.0, 7.0), "vfov": 60.0},
        {"name": "hub_plaza_trees", "cam": (60.0, 160.0, 3.5), "target": (80.0, 200.0, 4.0), "vfov": 60.0},
        {"name": "hub_dressing_auditorium_lawn", "cam": (38.0, 104.0, 3.0), "target": (38.0, 70.0, 3.0), "vfov": 60.0},
        {"name": "hub_dressing_turlington_plaza", "cam": (-40.0, -25.0, 4.0), "target": (-80.0, 10.0, 2.0),
         "vfov": 60.0},
        {"name": "hub_tower_from_smathers_door", "cam": (126.0, 236.0, 3.0), "target": (0.0, 0.0, 30.0), "vfov": 45.0},
    ]
