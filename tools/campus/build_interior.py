"""Build an INTERIOR stage (Course 4 Marston Science Library first) as a coopdx DynOS level, headlessly.

Usage (Blender, through the project runner):
  tools/blender/run_blender.sh tools/campus/build_interior.py -- marston [options]
    --levels-dir DIR     where the level folder goes (default mods/sgl64/levels -> mods/sgl64/levels/ccm)
    --report-dir DIR     where sgl_marston_build.json AND marston_points.json go (default: the report in
                         art/levels/marston/, the points in data/uf/marston_points.json); use scratch dirs
                         for test builds
    --previews           render previews to art/levels/marston/previews/ (+ the best five to showcase/)
    --previews-dir DIR   render them there instead (implies --previews; showcase/ goes next to it)
    --no-export          build (and render previews) without exporting the level
    --no-backdrop        skip the campus backdrop (faster test builds)
    --no-repair-collision
    --blend OUT.blend    save the built scene
Interior modules live in tools/campus/interiors/<key>.py and expose build() -> an object with .kit (an
interior_kit.Kit in map metres), .lighting ({group: Lighting}), .points (design anchors), .pickups, .views,
.notes, .stats, .layout, plus the module constants KEY, SLOT, CENTER, MUSIC, TERRAIN, BACKGROUND, FOG_RGB,
LEVEL_CONST, COURSE_CONST, DOOR, COL_SLIDE (see interiors/marston.py).

Pipeline (outdoor stages use build_stage.py; nothing there changes):
  1. the interior module builds its kit scene (pure Python);
  2. Blender: Fast64 scene, level root (background), area 1 (music, terrain, fog), the flow-contract warp
     nodes (build_stage.add_flow_warps: 0x0A, 0xF0 -> hub 0x2i, 0xF1 -> hub 0x3i), the campus materials +
     the interior kit materials (stage_materials.make_interior_materials: vertex-lit) + 'COL slide';
  3. one visual + one collision object per kit group, lighting baked into the vertex colours, moved into
     the stage frame (map metres - CENTER);
  4. spawn 0x0A + MARIO_POS on the measured floor; coins / hearts / 1-ups / Goombas through
     stage_pickups.Placer (every item checked against the collision);
  5. Fast64 export -> fog factor patch, export hygiene, common0 models, collision seam repair
     (stage_collision.py), validate_level.py (incl. the flow-contract check);
  6. the mission anchor points measured on the built collision (stage_points.Points) -> data/uf/<key>_points.json;
     the build report -> art/levels/<key>/sgl_<key>_build.json; previews.
"""
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import time
import types

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
BLENDER_TOOLS = os.path.join(ROOT, "tools", "blender")
for p in (HERE, BLENDER_TOOLS):
    if p not in sys.path:
        sys.path.insert(0, p)
VENV_PY = os.path.join(ROOT, "tools", ".venv", "bin", "python")

import build_stage as BS  # noqa: E402  (helpers only: warps, fog, hygiene, common0, probe; its main() does not run)
import interior_kit as K  # noqa: E402

INTERIORS = {"marston": os.path.join(HERE, "interiors", "marston.py"),
             "libwest": os.path.join(HERE, "interiors", "libwest.py"),
             # Course 2 area 2 (the Reitz Union interior of levels/wf): an AREA module (AREA = 2). build_stage.py
             # reitz_eng exports it together with area 1 (build_area below); here only --no-export previews
             "reitz": os.path.join(HERE, "interiors", "reitz.py")}
SHOWCASE = {"marston": ["marston_lobby", "marston_atrium", "marston_stacks", "marston_study_rooms",
                        "marston_5th_floor_view"],
            "libwest": ["libwest_entrance", "libwest_stacks", "libwest_study_floor", "libwest_windows_plaza",
                        "libwest_top_floor"],
            "reitz": ["reitz_atrium_lounge", "reitz_game_room_lanes", "reitz_food_court", "reitz_grand_ballroom",
                      "reitz_atrium_stairs"]}
# Optional interior-module overrides (added for Course 5; a module without them builds exactly as before):
#   BACKGROUND_COLOR (linear RGB 0..1, with BACKGROUND None: a solid background), SPAWN_NOTE,
#   POINTS_COORDINATES_MAP_M, POINTS_NOTE, PREVIEW_OVERVIEW ((camera), (target), vfov) in stage-local metres,
#   preview_world() (sets the Blender world after interior_kit_demo.setup_render).
MARSTON_SPAWN_NOTE = ("stage entry spawn (bhvSpinAirborneWarp, MARIO_POS) in the lobby just inside the north "
                      "doors, facing the atrium; the object hovers 1 m above this floor")
MARSTON_POINTS_MAP_M = ("x = east, y = north, z = metres above the hub's grade (F2 entrance floor = 0; F1 basement -6, "
                        "F3 6, F4 12, F5 18, roof 24); origin = Century Tower")
MARSTON_POINTS_NOTE = ("Anchor points for the Course 4 mission author (docs/game_design.md 7.3), measured on the built "
                       "collision of levels/ccm. 'actN_' keys use the design act numbers (7.3: 1 Out-of-Order Elevator, "
                       "2 Quiet Floor, 3 Group Study Room Booking (co-op), 4 Lost Lab Notebook Pages = the 8 'lost "
                       "textbook' red-coin spots, 5 Printer Jam, 6 Overdue Book Express); course act order is the "
                       "mission author's (docs/flow.md 5.1: solo acts first, co-op last). Points with a 'check' key did "
                       "not measure as designed. No level-script star: every mission spawns its own (spawn_default_star "
                       "from the controller, star id act - 1).")
MARSTON_OVERVIEW = ((30.0, -45.0, 70.0), (0.0, 2.0, 2.0), 42.0)
SLIDE_SURFACE = "SURFACE_SLIPPERY"


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not argv or argv[0].startswith("-"):
        sys.exit("usage: build_interior.py -- <interior key> [--levels-dir DIR] [--report-dir DIR] [--previews] "
                 "[--previews-dir DIR] [--no-export] [--no-backdrop] [--blend OUT]")
    o = {"key": argv[0], "levels_dir": os.path.join(ROOT, "mods", "sgl64", "levels"), "report_dir": None,
         "previews": False, "previews_dir": None, "export": True, "backdrop": True, "repair": True, "blend": None}
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--levels-dir":
            o["levels_dir"] = os.path.abspath(argv[i + 1]); i += 1
        elif a == "--report-dir":
            o["report_dir"] = os.path.abspath(argv[i + 1]); i += 1
        elif a == "--previews":
            o["previews"] = True
        elif a == "--previews-dir":
            o["previews"] = True
            o["previews_dir"] = os.path.abspath(argv[i + 1]); i += 1
        elif a == "--no-export":
            o["export"] = False
        elif a == "--no-backdrop":
            o["backdrop"] = False
        elif a == "--no-repair-collision":
            o["repair"] = False
        elif a == "--blend":
            o["blend"] = os.path.abspath(argv[i + 1]); i += 1
        else:
            sys.exit(f"unknown option {a}")
        i += 1
    if o["key"] not in INTERIORS:
        sys.exit(f"unknown interior {o['key']!r}; known: {sorted(INTERIORS)}")
    return o


def load_module(key):
    spec = importlib.util.spec_from_file_location(f"interior_{key}", INTERIORS[key])
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ensure_textures(names):
    """Generate art/levels/textures only when one the stage needs is missing (make_textures.py is shared;
    an interior build does not rewrite it otherwise)."""
    from stage_palette import texture_path
    missing = [n for n in names if not os.path.exists(texture_path(n))]
    if missing:
        print(f"SGL: {len(missing)} textures missing ({missing[:4]}...): running make_textures.py")
        BS.run_venv(os.path.join(HERE, "make_textures.py"))
    return missing


def slide_material():
    from fast64.fast64_internal.f3d.f3d_material import createF3DMat
    import stage_materials
    mat = createF3DMat(None, "sm64_shaded_solid")
    mat.name = "sgl COL slide"
    stage_materials._set_collision(mat, SLIDE_SURFACE)
    mat["sgl_tile_m"] = 0.0
    mat["sgl_name"] = "COL slide"
    return mat


def walk_points(node, fn):
    """Measure every design point record ({"name", "p", "kind"}) in a nested dict / list."""
    if isinstance(node, dict):
        if "name" in node and "p" in node and "kind" in node:
            return fn(node)
        return {k: walk_points(v, fn) for k, v in node.items()}
    if isinstance(node, list):
        return [walk_points(v, fn) for v in node]
    return node


def main():
    o = parse_args()
    t0 = time.time()
    mod = load_module(o["key"])
    key, slot = mod.KEY, mod.SLOT
    cx, cy = mod.CENTER
    short = key
    art_dir = os.path.join(ROOT, "art", "levels", short)
    report_dir = o["report_dir"] or art_dir
    os.makedirs(report_dir, exist_ok=True)

    if getattr(mod, "AREA", 1) != 1 and o["export"]:
        sys.exit(f"{key} is area {mod.AREA} of levels/{slot}: export it with build_stage.py (its outdoor stage); "
                 "here use --no-export [--previews]")

    # ---- 1. the interior (pure Python)
    M = mod.build(backdrop=o["backdrop"])
    rep = mod.report(M)
    print(f"SGL: {key} kit: {len(M.kit.items)} items, visual {rep['total']['visual']} tris, collision "
          f"{rep['total']['collision']} tris, {M.stats.get('lights')} lights")
    used = sorted({p.mat for _, _, pr in M.kit.items for p in pr.visual.polys})
    ensure_textures(used)

    # ---- 2. scene
    import sgl_level as L
    from sgl_blender import setup_fast64
    import stage_materials
    L.new_empty_scene()
    setup_fast64()
    scene = L.configure_scene()
    scene.fast64.sm64.fix_coop_fog = True
    root = L.make_level(f"{slot} Level Root", background=mod.BACKGROUND,
                        background_color=getattr(mod, "BACKGROUND_COLOR", None))
    area = L.make_area(root, 1, music=mod.MUSIC, terrain=mod.TERRAIN, camera="CAMERA_MODE_FREE_ROAM",
                       envfx="ENVFX_MODE_NONE", clip=(BS.NEAR_CLIP, BS.FAR_CLIP))
    area.fast64.sm64.area.set_fog = True
    area.area_fog_color = (*(stage_materials._srgb_to_linear(c / 255.0) for c in mod.FOG_RGB), 1.0)
    area.area_fog_position = (990, 1000)
    fm, fo, _ = BS.coop_fog_factor(BS.FOG_START_M, BS.FOG_END_M)
    warp_nodes = BS.add_flow_warps(L, area, slot)
    mats = stage_materials.make_materials()
    mats.update(stage_materials.make_interior_materials())
    mats[mod.COL_SLIDE] = slide_material()
    if hasattr(mod, "WARP_SURFACE"):          # area modules: the instant-warp floor materials (previews only here)
        mats.update(warp_materials(mod))

    # ---- 3. meshes (lighting baked), moved into the stage frame
    from mathutils import Matrix
    objs = []
    t1 = time.time()
    for g in M.kit.groups():
        merged = M.kit.merged(g)
        parts = merged.parts(f"{key} {g}", lighting=M.lighting.get(g) or K.Lighting(M.kit.lights()))
        for ob in K.link_parts(parts, mats, parent=area, prefix=""):
            ob.data.transform(Matrix.Translation((-cx, -cy, 0.0)))
            ob.data.update()
            ob["sgl_group"] = g
            objs.append(ob)
    print(f"SGL: {len(objs)} mesh objects ({time.time() - t1:.1f}s bake)")
    probe = BS.CollisionProbe(objs)

    # ---- 4. spawn + pickups
    S = types.SimpleNamespace(cx=cx, cy=cy, key=key)
    sp = M.layout["entrance"]["spawn"]
    sx, sy = sp["pos_m"][0] - cx, sp["pos_m"][1] - cy
    sz = float(sp.get("z_game_m", 0.0))
    spawn_floor = probe.floor(sx, sy, sz + 1.5)
    spawn_clear = probe.clearance(sx, sy, (spawn_floor or sz) + 0.6)
    if spawn_floor is None or abs(spawn_floor - sz) > 0.3 or spawn_clear < 1.5:
        print(f"SGL WARNING: spawn {sp['pos_m']}: floor {spawn_floor}, clearance {spawn_clear:.2f} m")
    spawn_z = (spawn_floor if spawn_floor is not None else sz) + 1.0
    facing = float(sp.get("facing_deg", 180.0))
    L.add_spawn(area, (sx, sy, spawn_z), yaw_deg=BS.yaw_for_facing(facing))
    spawn_out = {"name": "spawn_0x0A", "map_m": [round(sp["pos_m"][0], 2), round(sp["pos_m"][1], 2),
                                                round(spawn_floor if spawn_floor is not None else sz, 2)],
                 "game": [round(sx * 100), round((spawn_floor or 0.0) * 100), round(-sy * 100)],
                 "floor_m": spawn_floor, "clearance_m": round(spawn_clear, 2), "facing_deg": facing,
                 "game_yaw": "0x%04X" % (int(round(((180.0 - facing) % 360.0) / 360.0 * 65536)) & 0xFFFF),
                 "node": "0x0A", "spawn_object_game": [round(sx * 100), round(spawn_z * 100), round(-sy * 100)],
                 "note": getattr(mod, "SPAWN_NOTE", MARSTON_SPAWN_NOTE)}
    import stage_pickups
    Pl = stage_pickups.Placer(S, probe, rivals=False)
    for it in M.pickups:
        k, name, p = it["kind"], it["name"], it["pos"]
        n_placed = len(Pl.items)
        if k == "coin":
            Pl.coin(name, p)
        elif k == "coin_line":
            Pl.coin_line(name, p, it.get("facing", 0.0))
        elif k == "coin_ring":
            Pl.coin_ring(name, p)
        elif k == "heart":
            Pl.heart(name, p)
        elif k == "1up":
            Pl.one_up(name, p)
        elif k == "goomba":
            Pl.goomba(name, p, it.get("facing", 0.0))
        if it.get("acts"):      # optional (Course 5 integration): an act-only pickup -> OBJECT_WITH_ACTS
            for placed in Pl.items[n_placed:]:
                placed["acts"] = list(it["acts"])
    for it in Pl.items:
        L.add_object(area, it["name"], it["stage"], it["behavior"], it["model"], it["bparams"],
                     BS.yaw_for_facing(it["facing_deg"]), acts=it.get("acts"))
    pickups = stage_pickups.summary(Pl.items, Pl.skipped)
    print(f"SGL: pickups {pickups['by_kind']}, {pickups['coins_placed']} coins (+ Goombas "
          f"{pickups['coins_with_goombas']}), {len(Pl.skipped)} skipped")

    # ---- 5. export
    level_dir = None
    report = {"level": slot, "stage": key, "built_at": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime()),
              "generated_by": f"tools/campus/build_interior.py {key} (tools/campus/interiors/{key}.py)",
              "center_m": [cx, cy], "slot": slot, "level_script": f"level_{slot}_entry",
              "music": mod.MUSIC, "terrain": mod.TERRAIN, "background": mod.BACKGROUND,
              "kit_tris": rep, "warp_nodes": warp_nodes, "spawn": spawn_out, "pickups": pickups,
              "stats": M.stats, "notes": M.notes,
              "fog": {"start_m": BS.FOG_START_M, "end_m": BS.FOG_END_M, "gsSPFogFactor": [fm, fo],
                      "color_srgb": list(mod.FOG_RGB)},
              "objects": {o_.name: {"group": o_.get("sgl_group"), "tris": len(o_.data.polygons),
                                    "collision": not o_.ignore_collision} for o_ in objs}}
    if o["blend"]:
        os.makedirs(os.path.dirname(o["blend"]), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=o["blend"], copy=True)
    if o["export"]:
        from export_level import export_level
        from validate_level import validate_level
        level_dir, _ = export_level(root.name, slot, o["levels_dir"], setup=False, validate=False)
        n_pos, n_col = BS.patch_fog(level_dir, fm, fo, mod.FOG_RGB)
        hyg = BS.export_hygiene(level_dir)
        from fix_material_lighting import fix_level as fix_material_lighting
        hyg["material_lights_repaired"] = fix_material_lighting(level_dir)
        hyg["common0_jump_link"] = BS.add_common0_models(level_dir)
        report["export_hygiene"] = hyg
        if o["repair"]:
            import glob
            import stage_collision
            report["collision_repair"] = {}
            for cpath in sorted(glob.glob(os.path.join(level_dir, "area_*", "collision.inc.c"))):
                r = stage_collision.repair(cpath)
                report["collision_repair"][os.path.basename(os.path.dirname(cpath))] = r
                print(f"SGL: collision seam repair {os.path.relpath(cpath, level_dir)}: {r}")
        vr = validate_level(level_dir)
        print(vr["text"])
        report["validation"] = {"errors": vr["errors"], "warnings": vr["warnings"],
                                "collision_tris": vr.get("collision_tris"), "render_tris": vr.get("render_tris"),
                                "lua_names": vr.get("lua_names"), "fog_patched": [n_pos, n_col]}
        report["level_dir"] = level_dir
        if vr["errors"]:
            json.dump(report, open(os.path.join(report_dir, f"sgl_{key}_build.json"), "w"), indent=1)
            raise RuntimeError(f"{len(vr['errors'])} validation error(s) in {level_dir}")

    # ---- 6. anchor points measured on the built collision
    import stage_points as SP
    Pt = SP.Points(S, probe)

    def measure(rec):
        name, p = rec["name"], rec["p"]
        if rec["kind"] == "air":
            out = Pt.air(name, tuple(p), rec.get("note"))
        else:
            out = Pt.ground(name, tuple(p), rec.get("note"), rec.get("facing"), clear=rec.get("clear", 0.5))
        for k2, v in rec.items():
            if k2 not in ("name", "p", "kind", "note", "facing", "clear"):
                out[k2] = v
        return out
    measured = walk_points(M.points, measure)
    points = {"schema": f"sgl64.{key}_points/1", "generated_by": report["generated_by"],
              "generated_at": report["built_at"], "stage": key, "level": slot, "slot": slot,
              "level_const": mod.LEVEL_CONST, "course": mod.COURSE_CONST, "door": mod.DOOR, "center_m": [cx, cy],
              "coordinates": {
                  "map_m": getattr(mod, "POINTS_COORDINATES_MAP_M", MARSTON_POINTS_MAP_M),
                  "game": "X = (x - cx) * 100, Y = z * 100, Z = -(y - cy) * 100 with (cx, cy) = center_m; Y is the "
                          "ray-cast collision floor (Mario's feet). Objects that hover (stars, coins) add their own offset.",
                  "game_yaw": "0 = faces +Z (south), 0x4000 = east, 0x8000 = north, 0xC000 = west",
                  "floor_m": "collision floor measured by ray-casting the built level (1.5 m above the design height, "
                             "straight down)"},
              "note": getattr(mod, "POINTS_NOTE", MARSTON_POINTS_NOTE),
              "spawn": spawn_out, "warp_nodes": warp_nodes, "stars": []}
    points.update(measured)
    points["pickups"] = pickups
    points["checks"] = Pt.flags
    pts_path = os.path.join(o["report_dir"] if o["report_dir"] else os.path.join(ROOT, "data", "uf"),
                            f"{key}_points.json")
    SP.write(pts_path, points)
    print(f"SGL: wrote {pts_path} ({len(Pt.flags)} point checks flagged)")
    for c in Pt.flags:
        print(f"   points check: {c}")
    report["points_file"] = os.path.relpath(pts_path, ROOT) if pts_path.startswith(ROOT) else pts_path
    report["point_checks"] = Pt.flags
    if o["export"] or o["report_dir"]:
        json.dump(report, open(os.path.join(report_dir, f"sgl_{key}_build.json"), "w"), indent=1)

    # ---- 7. previews
    if o["previews"]:
        pv = o["previews_dir"] or os.path.join(art_dir, "previews")
        paths = render_previews(M, objs, pv, cx, cy, mod=mod)
        sc = os.path.join(os.path.dirname(pv.rstrip("/")), "showcase")
        os.makedirs(sc, exist_ok=True)
        for name in SHOWCASE.get(key, []):
            src = os.path.join(pv, name + ".png")
            if os.path.exists(src):
                shutil.copyfile(src, os.path.join(sc, name + ".png"))
        print(f"SGL: {len(paths)} previews in {pv}, showcase {sc}")
    if o["export"] and not o["report_dir"] and os.path.abspath(o["levels_dir"]) == os.path.join(ROOT, "mods", "sgl64", "levels"):
        BS.run_venv(os.path.join(ROOT, "tools", "npcs", "rebuild.py"))
    print(f"SGL: done in {time.time() - t0:.1f}s")



# ================================================================== extra AREAS of an outdoor stage (Course 2 area 2)
# build_stage.py <stage> calls build_area() for every STAGE_INTERIOR_AREAS entry of its stage, after area 1 is built
# and before the one Fast64 export. Additive: the interior stages above (main()) never call it.
def warp_materials(mod):
    """{'COL warp_1x': bpy material} with the SURFACE_INSTANT_WARP_1x collision types of an area module."""
    from fast64.fast64_internal.f3d.f3d_material import createF3DMat
    import stage_materials
    out = {}
    for idx, surface in sorted(mod.WARP_SURFACE.items()):
        name = mod.WARP_MAT[idx]
        mat = createF3DMat(None, "sm64_shaded_solid")
        mat.name = f"sgl {name}"
        stage_materials._set_collision(mat, surface)
        mat["sgl_tile_m"] = 0.0
        mat["sgl_name"] = name
        out[name] = mat
    return out


def load_area_module(key):
    return load_module(key)


def build_area(L, root, mod, M, mats, slot, door, levels_const, hub_const="LEVEL_CASTLE_GROUNDS"):
    """Area mod.AREA of an outdoor stage's level from an interior module's build() (M), in the SAME frame as area 1
    (mod.CENTER = the stage centre): area root (music, terrain, fog), warp nodes (own 0x0A spawn; 0xF0 / 0xF1 to the
    hub door like area 1; the module's teleport pads), INSTANT_WARPs back to area 1 (negated offsets), the baked kit
    meshes, the spawn object, the pads and the pickups. -> (area, objects, report dict). mats must hold the interior
    kit materials and the warp floor materials."""
    import stage_materials
    import stage_pickups
    from mathutils import Matrix
    cx, cy = mod.CENTER
    ai = int(mod.AREA)
    area = L.make_area(root, ai, music=mod.MUSIC, terrain=mod.TERRAIN, camera="CAMERA_MODE_FREE_ROAM",
                       envfx="ENVFX_MODE_NONE", clip=(BS.NEAR_CLIP, BS.FAR_CLIP))
    area.fast64.sm64.area.set_fog = True
    area.area_fog_color = (*(stage_materials._srgb_to_linear(c / 255.0) for c in mod.FOG_RGB), 1.0)
    area.area_fog_position = (990, 1000)
    nodes = []

    def node(wid, dest, darea, dnode, note):
        L.add_warp_node(area, wid, dest, darea, dnode)
        nodes.append({"id": "0x%02X" % wid, "dest_level": dest, "dest_area": darea, "dest_node": "0x%02X" % dnode,
                      "note": note})
    node(BS.NODE_SPAWN, levels_const, ai, BS.NODE_SPAWN, f"area {ai} spawn (debug warps only)")
    node(0xF0, hub_const, 1, BS.NODE_STAR_RETURN + door, f"star exit -> hub outside door {door} (as area 1)")
    node(0xF1, hub_const, 1, BS.NODE_DEATH_RETURN + door, f"death / Exit course -> hub outside door {door} (as area 1)")
    for p in M.pads:
        node(p["node"], levels_const, ai, p["dest_node"], f"{p['name']} -> {p['dest_floor']} (teleport pad)")
    iw = []
    for idx, off in mod.instant_warps():
        back = (-off[0], -off[1], -off[2])
        L.add_instant_warp(area, idx, 1, back)
        iw.append({"index": idx, "surface": mod.WARP_SURFACE[idx], "to_area": 1, "offset_units": list(back)})
    # meshes
    objs = []
    for g in M.kit.groups():
        merged = M.kit.merged(g)
        parts = merged.parts(f"{mod.KEY} {g}", lighting=M.lighting.get(g) or K.Lighting(M.kit.lights()))
        for ob in K.link_parts(parts, mats, parent=area, prefix=""):
            ob.data.transform(Matrix.Translation((-cx, -cy, 0.0)))
            ob.data.update()
            ob["sgl_group"] = g
            objs.append(ob)
    probe = BS.CollisionProbe(objs)
    # spawn 0x0A of this area (no MARIO_POS: the level's start stays in area 1)
    sp = M.layout["entrance"]["spawn"]
    sx, sy = sp["pos_m"][0] - cx, sp["pos_m"][1] - cy
    sz = float(sp.get("z_game_m", 0.0))
    fz = probe.floor(sx, sy, sz + 1.5)
    L.add_spawn(area, (sx, sy, (fz if fz is not None else sz) + 1.0), yaw_deg=BS.yaw_for_facing(sp["facing_deg"]),
                mario_start=False)
    # teleport pads (vanilla bhvFadingWarp: stand still on it -> fade -> the paired pad)
    pads_out = []
    for p in M.pads:
        x, y, z = p["pos_m"]
        pz = probe.floor(x - cx, y - cy, z + 1.0)
        L.add_object(area, p["name"], (x - cx, y - cy, pz if pz is not None else z), p["behavior"], "MODEL_NONE",
                     p["bparams"], BS.yaw_for_facing(p["facing_deg"]))
        pads_out.append(dict(p, floor_m=pz, game=[round((x - cx) * 100), round((pz or z) * 100), round(-(y - cy) * 100)]))
    # pickups
    S = types.SimpleNamespace(cx=cx, cy=cy, key=mod.KEY)
    Pl = stage_pickups.Placer(S, probe, rivals=False)
    for it in M.pickups:
        k, name, p = it["kind"], it["name"], it["pos"]
        if k == "coin":
            Pl.coin(name, p)
        elif k == "coin_line":
            Pl.coin_line(name, p, it.get("facing", 0.0))
        elif k == "coin_ring":
            Pl.coin_ring(name, p)
        elif k == "heart":
            Pl.heart(name, p)
        elif k == "1up":
            Pl.one_up(name, p)
    for it in Pl.items:
        L.add_object(area, it["name"], it["stage"], it["behavior"], it["model"], it["bparams"],
                     BS.yaw_for_facing(it["facing_deg"]), acts=it.get("acts"))
    pickups = stage_pickups.summary(Pl.items, Pl.skipped)
    rep = {"area": ai, "module": f"tools/campus/interiors/{mod.KEY}.py", "kit_tris": mod.report(M)["total"],
           "warp_nodes": nodes, "instant_warps": iw, "warp_strips": M.warp_strips, "pads": pads_out,
           "spawn": {"map_m": list(sp["pos_m"]), "floor_m": fz, "note": getattr(mod, "SPAWN_NOTE", "")},
           "pickups": pickups, "stats": M.stats, "notes": M.notes,
           "objects": {o_.name: {"group": o_.get("sgl_group"), "tris": len(o_.data.polygons),
                                 "collision": not o_.ignore_collision} for o_ in objs}}
    print(f"SGL: area {ai} ({mod.KEY}): {len(objs)} mesh objects, {len(M.pads)} pads, pickups {pickups['by_kind']}")
    return area, objs, probe, rep


def measure_area_points(mod, M, probe):
    """The area module's design points measured on its own collision (stage_points.Points)."""
    import stage_points as SP
    cx, cy = mod.CENTER
    S = types.SimpleNamespace(cx=cx, cy=cy, key=mod.KEY)
    Pt = SP.Points(S, probe)

    def measure(rec):
        name, p = rec["name"], rec["p"]
        if rec["kind"] == "air":
            out = Pt.air(name, tuple(p), rec.get("note"))
        else:
            out = Pt.ground(name, tuple(p), rec.get("note"), rec.get("facing"), clear=rec.get("clear", 0.5))
        for k2, v in rec.items():
            if k2 not in ("name", "p", "kind", "note", "facing", "clear"):
                out[k2] = v
        return out
    return walk_points(M.points, measure), Pt.flags


def patch_vertex_lit(level_dir, area_index):
    """Vertex-lit kit materials of an extra area in a level whose Fast64 world keeps G_LIGHTING off (outdoor
    stages: build_stage never pins the world, so area 1 exports exactly as before): their material display lists
    get an explicit gsSPClearGeometryMode(G_LIGHTING) (the shade is the baked vertex colour; the engine state
    between display lists has lighting on). Only mat_*_sgl_int_*_area<N> lists are touched. -> count."""
    import re
    path = os.path.join(level_dir, "model.inc.c")
    src = open(path).read()
    pat = re.compile(r"(Gfx mat_\w*_sgl_int_\w*_area%d\[\] = \{\n)" % area_index)
    src, n = pat.subn(lambda m: m.group(1) + "\tgsSPClearGeometryMode(G_LIGHTING),\n", src)
    open(path, "w").write(src)
    return n


def render_previews(M, objs, out, cx, cy, mod=None):
    """Eevee previews with preview materials (texture x baked vertex shade), a 1.6 m Mario stand-in. The module
    may set the world (preview_world) and the overview camera (PREVIEW_OVERVIEW); the overview files are named
    <key>_overview.png / <key>_collision.png."""
    import interior_kit_demo as D
    os.makedirs(out, exist_ok=True)
    for ob in objs:
        me = ob.data
        for i, m in enumerate(me.materials):
            if m is not None and "sgl_name" in m:
                nm = m["sgl_name"]
                me.materials[i] = K.preview_material("COL notslip" if nm not in K.COL_NAMES and nm.startswith("COL")
                                                     else nm)
    vis_c, col_c = D.new_collection("PV visual"), D.new_collection("PV collision")
    for ob in objs:
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        (vis_c if not ob.ignore_render else col_c).objects.link(ob)
    D.setup_render()
    if mod is not None and hasattr(mod, "preview_world"):
        mod.preview_world()
    D.set_visible(col_c, False)
    mario_c = D.new_collection("PV mario")
    paths = []
    for name, loc, tgt, mario, vfov in M.views:
        for ob in list(mario_c.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        if mario:
            D.mario_standin(mario_c, mario[0] - cx, mario[1] - cy, mario[2], mario[3])
        cam = D.camera(name, (loc[0] - cx, loc[1] - cy, loc[2]), (tgt[0] - cx, tgt[1] - cy, tgt[2]), vfov)
        cam.data.clip_end = 1200.0
        paths.append(D.render(os.path.join(out, name + ".png"), cam, (1280, 720)))
    for ob in list(mario_c.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    # cutaway overview (back faces culled: the near walls vanish) + collision overview
    key = getattr(mod, "KEY", "marston") if mod is not None else "marston"
    ov_loc, ov_tgt, ov_fov = getattr(mod, "PREVIEW_OVERVIEW", MARSTON_OVERVIEW) if mod is not None else MARSTON_OVERVIEW
    cam = D.camera(f"{key}_overview", ov_loc, ov_tgt, ov_fov)
    cam.data.clip_end = 1200.0
    paths.append(D.render(os.path.join(out, f"{key}_overview.png"), cam, (1600, 900)))
    D.set_visible(vis_c, False)
    D.set_visible(col_c, True)
    cam = D.camera(f"{key}_collision", ov_loc, ov_tgt, ov_fov)
    paths.append(D.render(os.path.join(out, f"{key}_collision.png"), cam, (1600, 900)))
    D.set_visible(col_c, False)
    D.set_visible(vis_c, True)
    return paths


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        print(f"SGL ERROR: {e}")
        sys.exit(1)
