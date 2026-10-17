"""Build a friend character from the coopdx Mario template ("template surgery").

Usage (headless, project-local Fast64):
  BLENDER_USER_SCRIPTS=<repo>/tools/blender-scripts <Blender> --background --factory-startup \
      --python-exit-code 1 --python tools/blender/build_character.py -- <character_id> [--no-export] [--no-preview]
      [--build-dir DIR]   (write the .blend/textures/previews somewhere else, e.g. for test builds)
      [--actors-dir DIR]  (export somewhere other than mods/sgl64/actors/, e.g. for test builds)
      [--art-dir DIR]     (read <DIR>/<id>/character.json (+ textures/) instead of art/<id>/;
                           same as SGL_ART_DIR=DIR, used by the web worker's per-job builds)
  tools/blender/run_blender.sh wraps this command and retries when Blender crashes
  (Fast64's material upgrade segfaults on roughly 1 in 14 template loads).

Driven entirely by art/<id>/character.json. Steps:
  1. open the template (read-only; never saved over) and run setup_fast64()
  2. face textures: final art > candidate set > generated placeholder, skin keyed to alpha
  3. recolour materials, remap the outfit on the body, add outfit accessories
  4. replace every head (main, 7 cap-on + 8 capless eye variants) with the procedural
     head/hair, run the character module's post_build, move the wing-cap wings
     (WING_SHIFT), rebuild the metal body/head from the finished geometry
  5. save art/<id>/build/<id>.blend, export mods/sgl64/actors/<id>/, validate
  6. render previews to art/<id>/build/previews/ (after saving; never saved)
"""
import json
import os
import sys
import time

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from sgl_util import TEMPLATE_BLEND, actors_dir, build_dir, load_spec  # noqa: E402


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not argv:
        sys.exit("usage: -- <character_id> [--no-export] [--no-preview] [--build-dir DIR] [--actors-dir DIR] "
                 "[--art-dir DIR]")
    out = actors = None
    if "--art-dir" in argv:  # read by sgl_util.art_dir (load_spec, face textures)
        os.environ["SGL_ART_DIR"] = os.path.abspath(argv[argv.index("--art-dir") + 1])
    if "--build-dir" in argv:
        out = os.path.abspath(argv[argv.index("--build-dir") + 1])
    if "--actors-dir" in argv:
        actors = os.path.abspath(argv[argv.index("--actors-dir") + 1])
    return argv[0], "--no-export" not in argv, "--no-preview" not in argv, out, actors


def open_template():
    cur = os.path.abspath(bpy.data.filepath) if bpy.data.filepath else ""
    if cur != os.path.abspath(TEMPLATE_BLEND):
        bpy.ops.wm.open_mainfile(filepath=TEMPLATE_BLEND, load_ui=False)


def keep_fast64_node_groups():
    """Fast64 LINKS its node groups from f3d_material_library.blend once per scene
    (scene["f3d_lib_dir"]). A linked group nothing uses is not written to the .blend
    (a fake user does not keep linked data), e.g. GeometryNormal_ViewSpace while the
    lighting uses the world-space variant, and Fast64 never re-links it, so its preview
    resync fails when the build file is reopened. A small local holder group with a
    fake user references every linked Fast64 group so all of them are saved."""
    holder = bpy.data.node_groups.get("SGL keep Fast64 groups")
    if holder is None:
        holder = bpy.data.node_groups.new("SGL keep Fast64 groups", "ShaderNodeTree")
    holder.use_fake_user = True
    have = {n.node_tree.name for n in holder.nodes if n.type == "GROUP" and n.node_tree}
    for ng in list(bpy.data.node_groups):
        if ng.library is None or ng.name in have or ng.bl_idname != "ShaderNodeTree":
            continue
        node = holder.nodes.new("ShaderNodeGroup")
        node.node_tree = ng
    return holder


def rigged_meshes():
    return [o for o in bpy.data.objects if o.type == "MESH" and o.parent is not None and o.parent.type == "ARMATURE"]


def loose_verts(obj):
    """Vertices no edge or face uses (Fast64 skips them, but they are build debris)."""
    used = {i for e in obj.data.edges for i in e.vertices}
    return len(obj.data.vertices) - len(used)


def mesh_tris(name):
    o = bpy.data.objects[name]
    o.data.calc_loop_triangles()
    return len(o.data.loop_triangles)


def main():
    char_id, do_export, do_preview, out_override, actors_override = parse_args()
    t0 = time.time()
    spec = load_spec(char_id)
    open_template()

    from sgl_blender import setup_fast64
    setup_fast64()
    loose_before = {o.name: loose_verts(o) for o in rigged_meshes()}

    import sgl_body
    import sgl_heads
    import sgl_materials
    import sgl_textures

    out_build = out_override or build_dir(char_id)  # --build-dir: test builds outside art/
    os.makedirs(out_build, exist_ok=True)
    report = {"id": char_id, "name": spec.get("name", char_id)}

    # 1. textures
    tex = sgl_textures.process_face_textures(char_id, spec, out_build)
    imgs = sgl_textures.load_images(char_id, tex["files"])
    report["face_textures"] = {"source": tex["source"], "kind": tex["kind"], "crease_mode": tex["crease_mode"],
                               "crease_texels": tex["creases"]}

    # 2. materials
    mats = sgl_materials.setup_materials(spec)
    for state, fname in sgl_textures.EYE_FILES.items():
        sgl_materials.set_f3d_texture(mats["eyes_" + state], imgs[fname], clamp=True)
    sgl_materials.set_f3d_texture(mats["mouth"], imgs[sgl_textures.MOUTH_FILE], clamp=True)
    face_mats = [mats["eyes_" + s] for s in sgl_textures.EYE_FILES] + [mats["mouth"]]
    report["face_tiles"] = {m.name: sgl_materials.check_f3d_texture(m)[:4] for m in face_mats}
    report["palette"] = {k: v for k, v in mats["_palette"].items()}

    # 3. body (before heads: the drape uses the torso surface for clearance)
    report["body"] = sgl_body.build_body(spec, mats)
    body = bpy.data.objects["Mario Mesh"]
    arm = bpy.data.objects["Mario"]
    bvh = sgl_heads.body_bvh_head_space(body, arm)

    # 4. heads + metal
    hs = sgl_heads.replace_heads(spec, mats, bvh)
    report["heads"] = {"style": hs["style"], "tris_per_head": hs["tris"],
                       "meshes": [f"{n} ({s})" for n, s, _r in hs["meshes"]]}
    import sgl_characters
    post_build = sgl_characters.get(spec, "post_build")
    if post_build:
        report["post_build"] = post_build({"spec": spec, "mats": mats, "report": report})
    wing_shift = sgl_characters.get(spec, "WING_SHIFT")
    if wing_shift is not None:  # wing-cap wings moved out of big hair (sgl_body.move_wings)
        report["wings"] = sgl_body.move_wings(wing_shift)
    for o in bpy.data.objects:
        if o.type == "MESH" and o.parent is not None and o.parent.type == "ARMATURE":
            sgl_materials.compact_material_slots(o)
    sgl_body.rebuild_metal(mats)

    # leftover check in the meshes that get exported
    bad = []
    for o in bpy.data.objects:
        if o.type != "MESH" or o.parent is None or o.parent.type != "ARMATURE":
            continue
        for m in o.data.materials:
            if m and m.name in sgl_materials.REMOVED_MATERIALS:
                bad.append((o.name, m.name))
    if bad:
        raise RuntimeError(f"leftover Mario materials: {bad}")
    loose = {o.name: loose_verts(o) for o in rigged_meshes()}
    loose = {n: k for n, k in loose.items() if k > loose_before.get(n, 0)}
    if loose:
        raise RuntimeError(f"loose vertices added by the build: {loose}")
    report["loose_vertices_added"] = 0

    report["tris"] = {n: mesh_tris(n) for n in ("Mario Mesh", "Capless Head Mesh", "Metal Mario Mesh",
                                                 "Metal Capless Head Mesh", "Head Closed Mesh")}
    sgl_body.set_action(arm, sgl_body.REST_ACTION)

    # 5. save + export + validate
    bpy.context.preferences.filepaths.save_version = 0  # no .blend1 backups (disk space)
    # Fast64's shader node groups can be orphans at save time; Blender would drop them
    # and setup_fast64() on the saved file then fails (missing "GeometryNormal_ViewSpace").
    for ng in bpy.data.node_groups:
        ng.use_fake_user = True
    keep_fast64_node_groups()
    blend_path = os.path.join(out_build, f"{char_id}.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path, compress=True, copy=False)
    report["blend"] = blend_path
    print("SGL saved", blend_path)
    if do_export:
        from export_character import export_character
        for m in face_mats:  # the exported tile must match each face texture (see set_f3d_texture)
            sgl_materials.check_f3d_texture(m)
        out_dir = export_character("Mario", char_id, actors_override or actors_dir(), setup=False)
        import validate_export
        vrep, _ = validate_export.validate(out_dir, char_id)
        report["export"] = out_dir
        report["validation"] = vrep
        print("SGL validation", "OK" if vrep["ok"] else "FAILED", vrep["errors"])
        bpy.ops.wm.save_as_mainfile(filepath=blend_path, compress=True, copy=False)

    # 6. previews (never saved)
    if do_preview:
        import sgl_preview
        eye_imgs = [(state, imgs[f]) for state, f in sgl_textures.EYE_FILES.items()]
        files = sgl_preview.render_character(os.path.join(out_build, "previews"), eye_materials=eye_imgs)
        report["previews"] = files

    report["seconds"] = round(time.time() - t0, 1)
    with open(os.path.join(out_build, "build_report.json"), "w") as f:
        json.dump(report, f, indent=2, default=str)
    print("SGL_BUILD_REPORT", json.dumps(report, default=str))
    if do_export and not report["validation"]["ok"]:
        sys.exit(1)


main()
