"""Build and export the "sgl_test" proof-of-concept level (custom level pipeline check).

Usage:
  tools/blender/run_blender.sh tools/blender/build_test_level.py -- [--levels-dir DIR] [--blend OUT.blend]
  (run_blender.sh opens the character template first; this script starts from an empty
  file, so the template is never modified.)

Writes mods/sgl64/levels/sgl_test/ (Fast64 C export, DynOS layout); coopdx compiles it to
levels/level_sgl_test_entry.lvl at launch and mods/sgl64/levels.lua registers it.

Layout (metres, X east, Y north, Z up; 1 m = 100 SM64 units, true scale):
  200 x 200 m textured grass field (10 m cells), spawn at (0, -60) facing north,
  coin ring, a signpost, 1/2/3/4 m jump-test blocks, a 15 m ramp up to a 5 m deck,
  a slippery slide ramp, a 10 m tower with 1.25 m stairs and a goal marker on top,
  a 20 x 20 m sunken pool (4 m deep, water surface 0.6 m below ground),
  a death plane 60 m below everything.
"""
import math
import os
import sys
import time

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from sgl_util import PROJECT_ROOT  # noqa: E402

LEVEL_NAME = "sgl_test"
ROOT_NAME = "sgl_test Level Root"


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    levels_dir = os.path.join(PROJECT_ROOT, "mods", "sgl64", "levels")
    blend = None
    if "--levels-dir" in argv:
        levels_dir = os.path.abspath(argv[argv.index("--levels-dir") + 1])
    if "--blend" in argv:
        blend = os.path.abspath(argv[argv.index("--blend") + 1])
    return levels_dir, blend


def build():
    import sgl_level as L

    L.configure_scene()
    root = L.make_level(ROOT_NAME, background="OCEAN_SKY")
    area = L.make_area(root, 1, music="SEQ_LEVEL_GRASS", terrain="TERRAIN_GRASS",
                       camera="CAMERA_MODE_FREE_ROAM", clip=(100, 30000))

    # Warp nodes. 0x0A = spawn (warp_to_level target). 0xF0 / 0xF1 = success / death exits;
    # they must name a vanilla level (custom level numbers only exist at runtime), so they
    # point at Castle Inside's Bob-omb painting exits (what Fast64's own template uses).
    # levels.lua turns those exits into a warp back into SGL levels.
    L.add_warp_node(area, 0x0A, "LEVEL_CASTLE", 1, 0x0A)
    L.add_warp_node(area, 0xF0, "LEVEL_CASTLE", 1, 0x32)
    L.add_warp_node(area, 0xF1, "LEVEL_CASTLE", 1, 0x64)

    # ---- materials
    tex_dir = L.ensure_dir(os.path.join(PROJECT_ROOT, "art", "levels", "sgl_test"))
    grass_img = L.make_image("sgl_grass_32", L.checker_rows(32, "#4E9A3A", "#5BAA44", cells=2, noise=9),
                             os.path.join(tex_dir, "grass_32.png"))
    grass = L.textured_material("Grass (tex)", grass_img, tile_m=4.0, surface="SURFACE_DEFAULT")
    concrete = L.solid_material("Concrete", "#BDB8AE")
    brick = L.solid_material("UF Brick", "#A24A32")          # the campus' collegiate-gothic brick
    orange = L.solid_material("Gator Orange", "#FA4616")      # UF orange
    blue = L.solid_material("Gator Blue", "#0021A5")          # UF blue
    ice = L.solid_material("Slide (very slippery)", "#9FD3F0", surface="SURFACE_VERY_SLIPPERY")
    tile = L.solid_material("Pool Tile", "#5FA8C6")
    water_vis = L.transparent_material("Water Surface", "#2E7FD8", alpha=0.55)
    death = L.solid_material("Death Plane", "#000000", surface="SURFACE_DEATH_PLANE")

    pool = (40.0, 20.0, 60.0, 40.0)  # xmin, ymin, xmax, ymax (two 10 m grid cells each way)

    # ---- ground (holes where the pool is)
    g = L.MeshBuilder()
    g.grid(-100, -100, 100, 100, 0.0, 10.0, grass,
           skip=lambda cx, cy: pool[0] <= cx < pool[2] and pool[1] <= cy < pool[3])
    g.build("Ground", parent=area)

    # ---- props
    p = L.MeshBuilder()
    # jump-test blocks 3x3 m, 1/2/3/4 m tall, west of spawn
    for i, h in enumerate((1.0, 2.0, 3.0, 4.0)):
        x0 = -40.0 + i * 6.0
        p.box(x0, -45.0, 0.0, x0 + 3.0, -42.0, h, concrete, top=orange if i % 2 else blue)
    # ramp: 6 m wide, rises 5 m over 15 m heading north, onto a 6 x 6 m deck 5 m high
    p.ramp_north(-30.0, -24.0, -20.0, -5.0, 0.0, 5.0, concrete)
    p.box(-30.0, -5.0, 0.0, -24.0, 1.0, 5.0, concrete, top=orange)
    # slide: very slippery ramp from 8 m high down to the ground heading south
    p.ramp_north(-60.0, -54.0, 0.0, 30.0, 0.0, 8.0, ice)
    p.box(-60.0, 30.0, 0.0, -54.0, 34.0, 8.0, concrete, top=blue)
    for j in range(6):  # stairs up the north side of the slide deck, 8/7 m per step
        p.box(-60.0, 34.0 + 2.0 * j, 0.0, -54.0, 36.0 + 2.0 * j, 8.0 * (6 - j) / 7.0, concrete, top=blue)
    # tower: 6 x 6 m, 10 m tall, with 7 steps of 1.25 m (2 m deep) up its south side (8th hop = roof)
    tx0, ty0 = 10.0, 30.0
    p.box(tx0, ty0, 0.0, tx0 + 6.0, ty0 + 6.0, 10.0, brick, top=orange)
    for k in range(1, 8):
        y1 = ty0 - (7 - k) * 2.0
        p.box(tx0 + 1.5, y1 - 2.0, 0.0, tx0 + 4.5, y1, k * 1.25, brick, top=concrete)
    # a low wall to wall-kick against, east of the tower
    p.box(24.0, 30.0, 0.0, 25.0, 45.0, 6.0, brick)
    p.build("Props", parent=area)

    # ---- pool basin (floor 4 m down, walls face inward) + see-through water surface
    b = L.MeshBuilder()
    x0, y0, x1, y1 = pool
    b.poly([(x0, y0, -4.0), (x1, y0, -4.0), (x1, y1, -4.0), (x0, y1, -4.0)], tile, (0, 0, 1))
    b.poly([(x0, y0, -4.0), (x0, y1, -4.0), (x0, y1, 0.0), (x0, y0, 0.0)], tile, (1, 0, 0))
    b.poly([(x1, y1, -4.0), (x1, y0, -4.0), (x1, y0, 0.0), (x1, y1, 0.0)], tile, (-1, 0, 0))
    b.poly([(x1, y0, -4.0), (x0, y0, -4.0), (x0, y0, 0.0), (x1, y0, 0.0)], tile, (0, 1, 0))
    b.poly([(x0, y1, -4.0), (x1, y1, -4.0), (x1, y1, 0.0), (x0, y1, 0.0)], tile, (0, -1, 0))
    b.build("Pool Basin", parent=area)
    w = L.MeshBuilder()
    w.poly([(x0, y0, -0.6), (x1, y0, -0.6), (x1, y1, -0.6), (x0, y1, -0.6)], water_vis, (0, 0, 1))
    w.build("Pool Water (visual)", parent=area, ignore_collision=True)
    L.add_water_box(area, x0, y0, x1, y1, surface_z=-0.6, bottom_z=-5.0)

    # ---- death plane (collision only), 60 m below the field, wider than the field
    d = L.MeshBuilder()
    d.poly([(-160, -160, -60), (160, -160, -60), (160, 160, -60), (-160, 160, -60)], death, (0, 0, 1))
    d.build("Death Plane (collision only)", parent=area, ignore_render=True)

    # ---- objects
    L.add_spawn(area, (0.0, -60.0, 1.0), yaw_deg=180.0)  # bhvSpinAirborneWarp, bparams 0x000A0000
    for i in range(8):
        a = 2 * math.pi * i / 8
        L.add_object(area, f"Coin {i}", (4.0 * math.cos(a), -35.0 + 4.0 * math.sin(a), 0.5),
                     "bhvYellowCoin", "MODEL_YELLOW_COIN")
    # signpost: dialog id comes from a Lua global (levels.lua allocates the dialog)
    L.add_object(area, "Sign", (4.0, -52.0, 0.0), "bhvMessagePanel", "MODEL_WOODEN_SIGNPOST",
                 bparams="SGL_TEST_SIGN_BPARAM", yaw_deg=180.0)
    # goal marker on top of the tower: a Lua behaviour defined in levels.lua
    L.add_object(area, "Tower Goal", (tx0 + 3.0, ty0 + 3.0, 10.5), "id_bhvSglTestGoal", "MODEL_NONE")
    return root


def main():
    levels_dir, blend = parse_args()
    t0 = time.time()
    import sgl_level as L
    from sgl_blender import setup_fast64
    L.new_empty_scene()
    setup_fast64()
    root = build()
    meshes = [o for o in L.hierarchy(root) if o.type == "MESH"]
    print(f"SGL: built {LEVEL_NAME}: {len(meshes)} meshes, {L.tri_count(meshes)} triangles")
    if blend:
        os.makedirs(os.path.dirname(blend), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=blend, copy=True)
        print(f"SGL: saved {blend}")
    from export_level import export_level
    level_dir, report = export_level(root.name, LEVEL_NAME, levels_dir, setup=False)
    print(f"SGL: exported {level_dir} in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        print(e)
        sys.exit(1)
