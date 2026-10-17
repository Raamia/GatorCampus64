"""Interior kit demo: a sample two-level library room (32 x 22 m, 8.4 m tall: a double-height lobby and a
mezzanine at 4.2 m) with every tools/campus/interior_kit.py prop, lighting baked into vertex colours, and
preview renders.

Usage (Blender, headless):
  tools/blender/run_blender.sh tools/campus/interior_kit_demo.py -- [--out DIR] [--export LEVELS_DIR]
                                                                   [--blend OUT.blend] [--no-lineup]
    --out DIR          previews + kit_demo.json (default art/levels/marston)
    --export DIR       also export the room as the custom test level sgl_kit_demo into DIR with the real
                       Fast64 materials (stage_materials.make_interior_materials) and run validate_level on
                       it. Use a scratch directory, never mods/sgl64/levels.
    --no-lineup        skip the per-prop contact sheet (kit_props.png)
Writes:
  kit_overview.png / kit_overview_nw.png   dollhouse views (back-face culling removes the near walls)
  kit_topdown.png                          orthographic plan
  kit_lobby / kit_cafe / kit_lounge / kit_stacks / kit_mezzanine / kit_stairs / kit_atrium .png
                                           gameplay-camera views (~6 m behind a 1.6 m Mario stand-in)
  kit_collision.png                        collision only: grey = COL default, orange = COL nocam,
                                           green = COL notslip (stairs), magenta = COL hangable
  kit_props.png                            every builder alone, with its visual / collision triangles
  kit_textures.png                         the int_* texture sheet (make_textures.py --interior-sheet)
  kit_demo.json                            per-prop triangle counts, anchors, headroom / floor checks
Map metres, z up; the room's south-west floor corner is (0, 0, 0).
"""
import json
import math
import os
import subprocess
import sys
import tempfile
import time

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
for p in (HERE, os.path.join(ROOT, "tools", "blender")):
    if p not in sys.path:
        sys.path.insert(0, p)
VENV_PY = os.path.join(ROOT, "tools", ".venv", "bin", "python")

import interior_kit as K  # noqa: E402

W, D, H = 32.0, 22.0, 8.4        # room
MZ, MT = 4.2, 0.30               # mezzanine floor height, slab thickness
SB = (28.4, 14.0)                # switchback origin (first riser of flight 1)
ATRIUM = (12.0, 14.0, 20.0, 20.0)
ELEV_HOLE = (0.2, 15.3, 2.6, 17.7)


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    o = {"out": os.path.join(ROOT, "art", "levels", "marston"), "export": None, "blend": None, "lineup": True}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--out":
            o["out"] = os.path.abspath(argv[i + 1]); i += 1
        elif a == "--export":
            o["export"] = os.path.abspath(argv[i + 1]); i += 1
        elif a == "--blend":
            o["blend"] = os.path.abspath(argv[i + 1]); i += 1
        elif a == "--no-lineup":
            o["lineup"] = False
        else:
            sys.exit(f"unknown option {a}")
        i += 1
    if o["export"] and os.path.abspath(o["export"]).startswith(os.path.join(ROOT, "mods")):
        sys.exit("--export must point at a scratch directory, not into mods/")
    return o


def lights_rect(kit, x0, y0, x1, y1, z, spacing, holes=(), tag="lights", drop=0.0, radius=7.0, group="main"):
    """Troffers on a grid over a rectangle at ceiling height z, skipping holes (atria, stair wells)."""
    P = K.Prop("light_set")
    nx = max(1, int(round((x1 - x0) / spacing)))
    ny = max(1, int(round((y1 - y0) / spacing)))
    for i in range(nx):
        for j in range(ny):
            x = x0 + (i + 0.5) * (x1 - x0) / nx
            y = y0 + (j + 0.5) * (y1 - y0) / ny
            if any(h[0] - 0.4 < x < h[2] + 0.4 and h[1] - 0.7 < y < h[3] + 0.7 for h in holes):
                continue
            P.merge(K.ceiling_light(drop=drop, radius=radius), x, y, z)
    kit.add(P, tag=tag, group=group)


def demo_room():
    """The sample room. Returns (kit, notes)."""
    kit = K.Kit()
    REAL = K.REAL
    # ---------------------------------------------------------------- shell, floors, mezzanine
    openings = [
        {"wall": "s", "at": 16.0, "w": 3.0, "h": 3.2, "kind": "gap"},                 # entry
        {"wall": "s", "at": 6.0, "w": 6.0, "z0": 1.2, "h": 2.4, "kind": "window"},
        {"wall": "s", "at": 26.0, "w": 6.0, "z0": 1.2, "h": 2.4, "kind": "window"},
        {"wall": "s", "at": 6.0, "w": 6.0, "z0": 5.0, "h": 2.4, "kind": "window"},
        {"wall": "s", "at": 26.0, "w": 6.0, "z0": 5.0, "h": 2.4, "kind": "window"},
        {"wall": "e", "at": 6.0, "w": 8.0, "z0": 0.9, "h": 6.0, "kind": "glass"},      # skybox shows through
        {"wall": "n", "at": 16.0, "w": 20.0, "z0": 0.9, "h": 2.1, "kind": "window"},
        {"wall": "n", "at": 16.0, "w": 20.0, "z0": MZ + 0.9, "h": 2.4, "kind": "window"},
    ]
    kit.add(K.room_shell(W, D, H, floor_on=False, openings=openings, wall_mats={"w": "int_wall_blue"}),
            tag="shell", group="shell")
    floor_kw = dict(bottom=None, edge=None, col_bottom=False, col_edges=False, thickness=0.05)
    kit.add(K.slab(W, 12.0, top="int_floor_tile", ao_sides="esw", **floor_kw), tag="lobby_floor", group="shell")
    kit.add(K.slab(W, D - 12.0, top="int_carpet", ao_sides="new", **floor_kw), 0.0, 12.0, 0.0, tag="stacks_floor",
            group="shell")
    sb = K.switchback_stair(MZ, 1.5)
    hx0, hy0, hx1, hy1 = sb.info["hole"]
    stair_hole = (SB[0] + hx0, SB[1] + hy0, SB[0] + hx1, SB[1] + hy1)
    holes = [ATRIUM, stair_hole, ELEV_HOLE]
    kit.add(K.slab(W, D - 12.0, MT, holes=[(h[0], h[1] - 12.0, h[2], h[3] - 12.0) for h in holes], ao_sides="new"),
            0.0, 12.0, MZ, tag="mezzanine", group="shell")
    for x in (6.0, 26.0):
        kit.add(K.column(0.6, MZ - MT), x, 12.4, 0.0, tag=f"column_{x:g}")
    # ---------------------------------------------------------------- circulation
    gs = K.straight_stair(MZ, 2.4, landing_depth=1.5, top_lip_visual=False)
    gy = 12.0 - gs.info["run"] - 0.01
    kit.add(gs, 16.0, gy, 0.0, 0.0, tag="grand_stair")
    kit.add(sb, SB[0], SB[1], 0.0, 0.0, tag="switchback")
    kit.add(K.elevator((0.0, MZ), 2.4, 2.4, top=H, out_of_order=(0, 1)), 2.6, 16.5, 0.0, 90.0, tag="elevator")
    rz = MZ
    kit.add(K.railing([(0.3, 12.06, rz), (14.7, 12.06, rz)], infill="glass"), tag="rail_mezz_w")
    kit.add(K.railing([(17.3, 12.06, rz), (31.7, 12.06, rz)], infill="glass"), tag="rail_mezz_e")
    a = ATRIUM
    kit.add(K.railing([(a[0] - 0.06, a[1] - 0.06, rz), (a[2] + 0.06, a[1] - 0.06, rz), (a[2] + 0.06, a[3] + 0.06, rz),
                       (a[0] - 0.06, a[3] + 0.06, rz), (a[0] - 0.06, a[1] - 0.06, rz)]), tag="rail_atrium")
    s0, s1, s2, s3 = stair_hole
    kit.add(K.railing([(SB[0] + 0.02, s1 - 0.06, rz), (s0 - 0.06, s1 - 0.06, rz), (s0 - 0.06, s3 + 0.06, rz),
                       (s2 + 0.06, s3 + 0.06, rz), (s2 + 0.06, s1 - 0.06, rz)]), tag="rail_stairwell")
    # ---------------------------------------------------------------- lobby (double height)
    kit.add(K.help_desk(3.6, hang_z=2.8, hang_top=H), 8.5, 6.5, 0.0, 180.0, tag="help_desk")
    kit.add(K.cafe_counter(4.8), 1.6, 6.0, 0.0, 90.0, tag="cafe")
    kit.add(K.kiosk(), 12.5, 2.5, 0.0, 180.0, tag="kiosk_lobby")
    kit.add(K.couch(2.2), 25.0, 1.9, 0.0, 0.0, tag="couch")
    for i, (x, y, f) in enumerate(((22.4, 5.0, 30.0), (25.4, 6.3, 0.0), (28.6, 4.8, 320.0))):
        kit.add(K.beanbag(fabric=("int_fabric_orange", "int_fabric_green", "int_fabric_blue")[i]), x, y, 0.0, f,
                tag=f"beanbag_{i}")
    kit.add(K.poster(which=0, z=1.4), 11.0, 0.0, 0.0, 0.0, tag="poster_dna")
    kit.add(K.poster(which=1, z=1.4), 21.0, 0.0, 0.0, 0.0, tag="poster_read")
    kit.add(K.sign("int_sign_marston", 2.4, 1.2, 3.6), 16.0, 0.0, 0.0, 0.0, tag="sign_marston")
    kit.add(K.floor_sign("up", 0.45, 1.5, mount="post"), 13.9, 3.4, 0.0, 180.0, tag="sign_up")
    kit.add(K.floor_sign("1", 0.45, 1.5, mount="post"), 25.8, 13.3, 0.0, 180.0, tag="sign_floor1")
    # ---------------------------------------------------------------- ground floor under the mezzanine
    kit.add(K.stack_range(3, 5 * REAL["stack_section_w"], K.AISLE_M,
                          heights=(REAL["stack_counter_h"], REAL["stack_mid_h"], REAL["stack_full_h"]),
                          end_caps=[("+x",)], seed=3), 6.6, 13.9, 0.0, 0.0, tag="stacks_ground")
    kit.add(K.kick_stool(), 10.3, 15.2, 0.0, tag="kick_stool")
    kit.add(K.book_cart(), 11.0, 13.1, 0.0, 90.0, tag="book_cart")
    kit.add(K.study_table(), 14.2, 16.2, 0.0, 90.0, tag="table_atrium_a")
    kit.add(K.study_table(), 17.8, 18.0, 0.0, 90.0, tag="table_atrium_b")
    kit.add(K.computer_row(3, double=True), 23.0, 16.6, 0.0, 0.0, tag="computers")
    kit.add(K.carrel_row(4), 23.0, 21.6, 0.0, 180.0, tag="carrels")
    kit.add(K.kiosk(), 20.6, 13.0, 0.0, 180.0, tag="kiosk_ground")
    # ---------------------------------------------------------------- mezzanine (z = 4.2)
    # full-height glass room (walls meet the 8.4 m ceiling): sealed for the co-op act, no roof to stand on
    kit.add(K.study_room(4.0, 3.6, H - MZ, roof=False), 5.0, 20.1, MZ, 180.0, tag="study_room")
    kit.add(K.stack_range(2, 4 * REAL["stack_section_w"], K.AISLE_M, seed=7), 23.5, 15.9, MZ, 0.0, tag="stacks_mezz")
    kit.add(K.bookshelf(4 * REAL["stack_section_w"], double=False, depth=0.36, seed=11), 23.5, 21.75, MZ, 180.0,
            tag="wall_shelf")
    kit.add(K.study_table(), 9.0, 16.4, MZ, 90.0, tag="table_mezz")
    kit.add(K.beanbag(), 14.5, 21.0, MZ, 10.0, tag="beanbag_mezz_a")
    kit.add(K.beanbag(fabric="int_fabric_blue"), 17.0, 21.2, MZ, 200.0, tag="beanbag_mezz_b")
    kit.add(K.whiteboard(2.0, 1.1, 0.9), 0.0, 14.0, MZ, 90.0, tag="whiteboard_mezz")
    kit.add(K.sign("int_sign_quiet", 1.2, 0.6, 2.4, mount="hanging", hang_top=H - MZ), 23.5, 13.4, MZ, 180.0,
            tag="sign_quiet")
    kit.add(K.floor_sign("2", 0.45, 1.6), 0.0, 12.5, MZ, 90.0, tag="sign_floor2")
    kit.add(K.kiosk(), 10.6, 20.6, MZ, 180.0, tag="kiosk_mezz")
    # ---------------------------------------------------------------- lights
    ring_r = 2.8
    kit.add(K.light_ring(ring_r, drop=2.0), 16.0, 17.0, H - 0.18 - 2.0, tag="light_ring")
    lights_rect(kit, 0.0, 0.0, W, 12.0, H, 4.0, tag="lights_lobby", drop=2.4, radius=9.5)
    lights_rect(kit, 0.0, 12.0, W, D, MZ - MT, 3.6, holes=holes, tag="lights_ground", radius=6.5)
    lights_rect(kit, 0.0, 12.0, W, D, H, 3.6, holes=[ATRIUM], tag="lights_mezz", radius=7.0)
    notes = {"room_m": [W, D, H], "mezzanine_z": MZ, "grand_stair_start_y": round(gy, 3),
             "stair_hole": [round(v, 3) for v in stair_hole], "atrium": list(ATRIUM)}
    return kit, notes


# ------------------------------------------------------------------ scene + render helpers
def _flat_mat(name, rgb):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*(K._srgb_to_linear(c) for c in rgb), 1.0)
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def _box_obj(name, boxes, coll):
    import bmesh
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    mats = []
    for (x0, y0, z0), (x1, y1, z1), mat in boxes:
        r = bmesh.ops.create_cube(bm, size=1.0)
        vs = r["verts"]
        bmesh.ops.scale(bm, vec=(x1 - x0, y1 - y0, z1 - z0), verts=vs)
        bmesh.ops.translate(bm, vec=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), verts=vs)
        if mat not in mats:
            mats.append(mat)
        for f in {f for v in vs for f in v.link_faces}:
            f.material_index = mats.index(mat)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def mario_standin(coll, x, y, z, facing):
    """1.6 m Mario-sized figure (preview only): red cap / shirt, blue overalls, facing compass `facing`."""
    red, blue, skin = _flat_mat("PV mario red", (0.86, 0.1, 0.1)), _flat_mat("PV mario blue", (0.15, 0.25, 0.8)), \
        _flat_mat("PV mario skin", (0.98, 0.8, 0.62))
    ob = _box_obj("PV Mario", [((-0.22, -0.14, 0.0), (0.22, 0.14, 0.75), blue),
                                ((-0.25, -0.16, 0.75), (0.25, 0.16, 1.2), red),
                                ((-0.17, -0.15, 1.2), (0.17, 0.17, 1.5), skin),
                                ((-0.19, -0.17, 1.45), (0.19, 0.25, 1.6), red)], coll)
    ob.location = (x, y, z)
    ob.rotation_euler = (0.0, 0.0, -math.radians(facing))
    return ob


def setup_render():
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
    w = bpy.data.worlds.new("KIT sky")
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
    ramp.color_ramp.elements[0].color = (*(K._srgb_to_linear(c / 255.0) for c in (176, 200, 226)), 1.0)
    ramp.color_ramp.elements[1].position = 0.45
    ramp.color_ramp.elements[1].color = (*(K._srgb_to_linear(c) for c in (0.33, 0.55, 0.86)), 1.0)
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs[0], out.inputs[0])


def camera(name, loc, target, vfov=45.0, ortho=None):
    from mathutils import Vector
    data = bpy.data.cameras.new(name)
    cam = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
        data.clip_start, data.clip_end = 0.5, 500.0
    else:
        data.sensor_fit = "VERTICAL"
        data.angle_y = math.radians(vfov)
        data.clip_start, data.clip_end = 0.1, 400.0
    return cam


def render(path, cam, res=(1280, 720)):
    scene = bpy.context.scene
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("KIT_PREVIEW", path)
    return path


def new_collection(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c


def set_visible(coll, on):
    coll.hide_render = not on
    coll.hide_viewport = not on


# ------------------------------------------------------------------ checks against the built collision
def collision_probe(objs):
    from mathutils.bvhtree import BVHTree
    verts, polys = [], []
    for o in objs:
        mw = o.matrix_world
        base = len(verts)
        verts.extend(mw @ v.co for v in o.data.vertices)
        polys.extend([base + i for i in p.vertices] for p in o.data.polygons)
    return BVHTree.FromPolygons(verts, polys)


def anchor_checks(tree, anchors):
    """Headroom over walkable anchors (tops, seats, roofs, landings, stair tops) and a floor under every
    standing anchor (door gaps, punch spots, stair ends)."""
    from mathutils import Vector
    out = []
    for name, (x, y, z, f) in sorted(anchors.items()):
        key = name.split(".")[-1]
        rec = {"anchor": name, "pos_m": [round(x, 2), round(y, 2), round(z, 2)], "facing_deg": round(f, 1)}
        if any(k in key for k in ("top", "roof", "landing", "seat", "step", "bottom", "punch", "door", "outside",
                                  "inside", "staff", "patron", "barista", "centre")):
            hit = tree.ray_cast(Vector((x, y, z + 0.05)), Vector((0, 0, 1)), 50.0)
            head = None if hit[0] is None else hit[0].z - z
            fl = tree.ray_cast(Vector((x, y, z + 0.5)), Vector((0, 0, -1)), 3.0)
            floor = None if fl[0] is None else fl[0].z
            rec.update(headroom_m=None if head is None else round(head, 2),
                       floor_m=None if floor is None else round(floor, 2))
            if head is not None and head < K.MARIO_HEIGHT_M:
                rec["warning"] = f"only {head:.2f} m headroom (< {K.MARIO_HEIGHT_M} m)"
            if floor is None or abs(floor - z) > 0.35:
                rec.setdefault("warning", f"floor {floor} not at the anchor height {z:.2f}")
        out.append(rec)
    return out


# ------------------------------------------------------------------ main
def main():
    o = parse_args()
    t0 = time.time()
    os.makedirs(o["out"], exist_ok=True)
    # textures (both sets; the interior sheet goes next to the previews)
    r = subprocess.run([VENV_PY, "-I", os.path.join(HERE, "make_textures.py"), "--interior-sheet",
                        os.path.join(o["out"], "kit_textures.png")], capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode:
        print(r.stderr)
        raise SystemExit("make_textures.py failed")

    import sgl_level as L
    L.new_empty_scene()
    kit, notes = demo_room()
    rep = kit.report()
    print(f"KIT demo room: {len(kit.items)} props, visual {rep['total']['visual']} tris, "
          f"collision {rep['total']['collision']} tris, {len(kit.lights())} lights")
    lighting = K.Lighting(kit.lights())
    parts = kit.parts("kit_demo", lighting=lighting)

    level_dir = None
    if o["export"]:
        from sgl_blender import setup_fast64
        import stage_materials
        setup_fast64()
        scene = L.configure_scene()
        scene.fast64.sm64.fix_coop_fog = True
        root = L.make_level("sgl_kit_demo Level Root", background="OCEAN_SKY")
        area = L.make_area(root, 1, music="SEQ_LEVEL_INSIDE_CASTLE", terrain="TERRAIN_STONE",
                           camera="CAMERA_MODE_FREE_ROAM", clip=(100, 32767))
        area.fast64.sm64.area.set_fog = True
        area.area_fog_color = (*(K._srgb_to_linear(c / 255.0) for c in (176, 200, 226)), 1.0)
        area.area_fog_position = (990, 1000)
        L.add_warp_node(area, 0x0A, "LEVEL_CASTLE", 1, 0x0A)
        L.add_warp_node(area, 0xF0, "LEVEL_CASTLE", 1, 0x32)
        L.add_warp_node(area, 0xF1, "LEVEL_CASTLE", 1, 0x64)
        L.add_spawn(area, (16.0, 2.5, 1.0), yaw_deg=180.0)
        mats = stage_materials.make_materials()
        mats.update(stage_materials.make_interior_materials())
        objs = K.link_parts(parts, mats, parent=area)
        from export_level import export_level
        level_dir, vrep = export_level(root.name, "sgl_kit_demo", o["export"], setup=False, validate=True)
        src = open(os.path.join(level_dir, "model.inc.c")).read()
        export_info = {"level_dir": level_dir, "errors": vrep["errors"], "warnings": vrep["warnings"],
                       "clear_lighting_cmds": src.count("G_LIGHTING"),
                       "vertices": src.count("{{{"), "collision_tris": vrep.get("collision_tris"),
                       "render_tris": vrep.get("render_tris")}
        print("KIT export:", json.dumps(export_info))
        # previews: swap the Fast64 materials for preview ones
        for ob in objs:
            me = ob.data
            for i, m in enumerate(me.materials):
                if m is not None and "sgl_name" in m:
                    me.materials[i] = K.preview_material(m["sgl_name"])
    else:
        export_info = None
        names = {s for p in parts for s in p["material_slots"]}
        objs = K.link_parts(parts, {n: K.preview_material(n) for n in names})

    vis_c, col_c = new_collection("KIT visual"), new_collection("KIT collision")
    for ob in objs:
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        (vis_c if ob["sgl_kit_visual"] else col_c).objects.link(ob)
    tree = collision_probe([ob for ob in objs if not ob["sgl_kit_visual"]])
    checks = anchor_checks(tree, kit.anchors())
    warn = [c for c in checks if "warning" in c]
    for c in warn:
        print(f"KIT check {c['anchor']}: {c['warning']}")

    setup_render()
    set_visible(col_c, False)
    mario_c = new_collection("KIT mario")
    out = o["out"]
    views = [
        ("kit_overview", (47.0, -17.0, 31.0), (15.0, 10.0, 1.0), None, 40.0, (1600, 900)),
        ("kit_overview_nw", (-15.0, 40.0, 25.0), (16.0, 9.0, 0.5), None, 40.0, (1600, 900)),
        ("kit_lobby", (16.0, 0.35, 2.6), (16.0, 12.0, 1.6), (16.0, 2.9, 0.0, 0.0), 45.0, (1280, 720)),
        ("kit_cafe", (10.8, 2.6, 3.0), (2.0, 6.5, 1.2), (5.2, 5.4, 0.0, 280.0), 45.0, (1280, 720)),
        ("kit_lounge", (19.0, 10.2, 3.2), (27.0, 3.5, 1.0), (23.6, 7.6, 0.0, 120.0), 45.0, (1280, 720)),
        ("kit_stacks", (15.4, 15.1, 2.7), (5.0, 16.0, 1.3), (10.4, 15.1, 0.0, 270.0), 45.0, (1280, 720)),
        ("kit_mezzanine", (13.6, 12.6, 7.7), (5.0, 19.2, 5.2), (8.4, 16.9, MZ, 300.0), 45.0, (1280, 720)),
        ("kit_stairs", (24.9, 21.2, 7.6), (28.6, 15.4, 2.0), (29.2, 13.0, MZ, 180.0), 45.0, (1280, 720)),
        ("kit_atrium", (16.0, 12.6, 1.5), (16.0, 17.5, 7.0), None, 50.0, (1280, 720)),
    ]
    paths = []
    for name, loc, tgt, mario, vfov, res in views:
        for ob in list(mario_c.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        if mario:
            mario_standin(mario_c, *mario)
        paths.append(render(os.path.join(out, name + ".png"), camera(name, loc, tgt, vfov), res))
    for ob in list(mario_c.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    cam = camera("kit_topdown", (W / 2, D / 2, 60.0), (W / 2, D / 2, 0.0), ortho=34.0)
    cam.rotation_euler = (0.0, 0.0, 0.0)
    paths.append(render(os.path.join(out, "kit_topdown.png"), cam, (1600, 1100)))
    set_visible(vis_c, False)
    set_visible(col_c, True)
    paths.append(render(os.path.join(out, "kit_collision.png"),
                        camera("kit_collision", (47.0, -17.0, 31.0), (15.0, 10.0, 1.0), 40.0), (1600, 900)))
    set_visible(col_c, False)

    lineup = []
    if o["lineup"]:
        tmp = tempfile.mkdtemp(prefix="kit_props_")
        line_c = new_collection("KIT lineup")
        floor_mat = K.preview_material("int_floor_tile")
        for label, P in K.all_props().items():
            for ob in list(line_c.objects):
                bpy.data.objects.remove(ob, do_unlink=True)
            pp = P.parts(f"lineup {label}")
            names = {s for p in pp for s in p["material_slots"]}
            obs = K.link_parts(pp, {n: K.preview_material(n) for n in names}, collection=line_c)
            for ob in obs:
                if not ob["sgl_kit_visual"]:
                    ob.hide_render = True
            (x0, y0, z0), (x1, y1, z1) = P.visual.bounds()
            cx, cy, cz = (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2
            size = max(x1 - x0, y1 - y0, z1 - z0, 1.0)
            ceiling_prop = label in ("ceiling_light", "light_grid")
            if not ceiling_prop:                 # a floor tile under it (ceiling props are seen from below)
                fl = _box_obj("PV floor", [((x0 - size, y0 - size, min(z0, 0.0) - 0.02),
                                           (x1 + size, y1 + size, min(z0, 0.0) - 0.001), floor_mat)], line_c)
                fl.data.uv_layers.new(name="UVMap")
                col_attr = fl.data.color_attributes.new("Col", "FLOAT_COLOR", "CORNER")
                for d in col_attr.data:
                    d.color = (0.6, 0.6, 0.6, 1.0)
            d = 1.35 * size + 1.0
            if ceiling_prop:
                loc = (cx + 0.6 * d, cy + 0.8 * d, cz - 0.9 * d)
            elif label in ("room_shell",):
                loc = (cx - 0.55 * d, cy - 0.75 * d, cz + 0.6 * d)
            else:
                loc = (cx + 0.55 * d, cy + 0.85 * d, cz + 0.55 * d)
            path = os.path.join(tmp, f"{label}.png")
            render(path, camera(f"lineup {label}", loc, (cx, cy, cz), 40.0), (400, 300))
            lineup.append({"label": label, "path": path, **P.tris()})
        for ob in list(line_c.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        sheet = os.path.join(out, "kit_props.png")
        code = ("import json,sys\nfrom PIL import Image, ImageDraw\n"
                "items=json.loads(sys.argv[1]); out=sys.argv[2]; cols=6; cw,ch=400,330\n"
                "rows=(len(items)+cols-1)//cols\n"
                "sh=Image.new('RGB',(cols*cw,rows*ch),(36,36,40)); d=ImageDraw.Draw(sh)\n"
                "for i,it in enumerate(items):\n"
                "  r,c=divmod(i,cols); im=Image.open(it['path']).convert('RGB'); sh.paste(im,(c*cw,r*ch))\n"
                "  d.text((c*cw+6,r*ch+304),f\"{it['label']}  vis {it['visual']}  col {it['collision']}\","
                "fill=(235,235,235))\n"
                "sh.save(out)\n")
        rr = subprocess.run([VENV_PY, "-I", "-c", code, json.dumps(lineup), sheet], capture_output=True, text=True)
        if rr.returncode:
            print(rr.stderr)
        else:
            paths.append(sheet)
            print("KIT_PREVIEW", sheet)
    report = {
        "generated_by": "tools/campus/interior_kit_demo.py", "built_at": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime()),
        "notes": notes, "totals": rep["total"], "lights": len(kit.lights()),
        "props": rep["items"], "anchor_checks": checks, "warnings": [c["anchor"] + ": " + c["warning"] for c in warn],
        "lineup": [{k: v for k, v in it.items() if k != "path"} for it in lineup],
        "export": export_info, "previews": [os.path.relpath(p, ROOT) for p in paths],
    }
    json.dump(report, open(os.path.join(out, "kit_demo.json"), "w"), indent=1)
    if o["blend"]:
        bpy.ops.wm.save_as_mainfile(filepath=o["blend"], copy=True)
    print(f"KIT demo done in {time.time() - t0:.1f}s: {len(paths)} previews, {len(warn)} anchor warnings")


if __name__ == "__main__":
    main()
