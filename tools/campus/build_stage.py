"""Build a UF campus stage (true 1:1 scale) as a coopdx DynOS level, headlessly.

Usage:
  tools/blender/run_blender.sh tools/campus/build_stage.py -- hub [options]
    --levels-dir DIR     where the level folder goes (default mods/sgl64/levels)
    --previews           render previews to art/levels/<key>/previews/ after exporting
    --previews-only      build + render previews, do not export
    --no-export          build only (with --blend to inspect it)
    --blend OUT.blend    save the built scene
    --work DIR           intermediate files (default: a temp dir)
    --strict-landmarks   a failing landmark module stops the build (default: warn + generic building)
    --no-landmarks       ignore tools/campus/landmarks/*.py (generic + fallback models only)
    --previews-dir DIR   render previews there instead of art/levels/<key>/previews/

Pipeline
  1. tools/.venv/bin/python -I tools/campus/make_textures.py   -> art/levels/textures/*.png
  2. tools/.venv/bin/python -I tools/campus/stage_data.py <key> -> <work>/<key>_data.json
     (stages.json window + campus.json + raw OSM tiles: buildings, areas, roads, paths, trees, ponds)
  3. Blender: landmark modules (tools/campus/landmarks/*.py) -> ground -> buildings (+ climb routes)
     -> fallback tower + props -> door markers -> trees (+ climbable plaza oaks) + tree line ->
     boundary walls -> meshes -> set dressing (checked against the real collision) -> spawn, signs,
     climbable tree / lamp-post pole objects -> Fast64 export (tools/blender/export_level.py) -> fog
     patch + export hygiene -> validate_level.py
Draw distance: the GEO far clip is the s16 maximum (327 m); mods/sgl64/levels.lua raises it to
OVERRIDE_FAR_M with set_override_far() while a player is in the hub, and the fog is fitted to that
(fog only starts at FOG_START_M, so Century Tower stays visible from the whole Plaza).
Level name: sgl_<key> (hub -> mods/sgl64/levels/sgl_hub/, level_sgl_hub_entry).
Map data (c) OpenStreetMap contributors, ODbL 1.0.
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
BLENDER_TOOLS = os.path.join(ROOT, "tools", "blender")
for p in (HERE, BLENDER_TOOLS):
    if p not in sys.path:
        sys.path.insert(0, p)
VENV_PY = os.path.join(ROOT, "tools", ".venv", "bin", "python")

# ------------------------------------------------------------------ stage look + engine settings
FAR_CLIP = 32767             # GEO_CAMERA_FRUSTUM far (s16 max, ~327 m): the "vanilla far" coopdx uses
NEAR_CLIP = 100              #   for its fog depth remap (gfx_pc.c G_MW_FOG)
OVERRIDE_FAR_M = 1000.0      # projection far plane while in the hub: levels.lua SGL_HUB_FAR_UNITS
FOG_START_M = 200.0          # fog starts here (the tower is ~8 % fogged at 213 m, ~30 % at 262 m) ...
FOG_END_M = 1000.0           # ... and is full at the far plane (the farthest stage edge is ~800 m)
FOG_COLOR_SRGB = (176, 200, 226)
BACKGROUND = "OCEAN_SKY"     # blue sky with clouds (the skybox the test level uses)
MUSIC = "SEQ_LEVEL_GRASS"
BOUNDARY_WALL_TOP = 80.0     # m, above Century Tower (47.9 m)
BOUNDARY_WALL_BOTTOM = -6.0  # m, below the pond beds (-2.2 m): no swimming under the boundary
# design doc 3.3: spawn on the Plaza facing south toward Century Tower (Auditorium porch + flag in
# front of it), Library West behind you; the welcome sign is 5 m ahead, a little to the left
SPAWN = {"hub": {"pos": (38.2, 142.4), "facing": 190.0,
                 "sign": {"pos": (38.64, 137.42), "facing": 355.0, "lua": "SGL_HUB_SIGN_WELCOME"}}}
TREE_BEHAVIOR = "bhvTree"            # vanilla climbable tree: SET_HITBOX(80, 500), pushes Mario away
LAMP_BEHAVIOR = "bhvPoleGrabbing"    # vanilla pole: hitbox height = bparam2 * 10 units


def coop_fog_factor(start_m, end_m, near=NEAR_CLIP, far=FAR_CLIP, proj_far=OVERRIDE_FAR_M * 100):
    """gsSPFogFactor(fm, fo) so coopdx v1.5.1 fog is 0 at start_m and full at end_m (view depth).
    coopdx projects with near = min(near, 5) and far = set_override_far() (else the GEO far), but
    rescales fog depth to emulate the vanilla near plane with the GEO near / far (gfx_pc.c
    G_MW_FOG: sDepthZSub/Mult/Add use gProjectionVanilla{Near,Far}Value = the GEO node's values),
    so fog = (A - C/d) * fm + fo with:"""
    n2 = 5.0
    pf = float(proj_far or far)
    a = (pf + n2) / (pf - n2)
    b = 2 * n2 * pf / (pf - n2)
    k = (far - n2) / (far - near)
    A = a * k
    C = (b + near) * k - 2 * n2 + near
    fz0, fz1 = A - C / (start_m * 100), A - C / (end_m * 100)
    fm = 256.0 / (fz1 - fz0)
    fo = -fz0 * fm
    if not (-32768 <= fm <= 32767 and -32768 <= fo <= 32767):
        raise ValueError(f"fog range {start_m}..{end_m} m does not fit s16 (fm {fm:.0f}, fo {fo:.0f})")
    return int(round(fm)), int(round(fo)), (A, C)


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not argv or argv[0].startswith("-"):
        sys.exit("usage: build_stage.py -- <stage_key> [--levels-dir DIR] [--previews] [--no-export] "
                 "[--blend OUT] [--work DIR] [--strict-landmarks]")
    opts = {"key": argv[0], "levels_dir": os.path.join(ROOT, "mods", "sgl64", "levels"), "previews": False,
            "export": True, "blend": None, "work": None, "strict": False, "landmarks": True,
            "previews_dir": None}
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--levels-dir":
            opts["levels_dir"] = os.path.abspath(argv[i + 1]); i += 1
        elif a == "--previews":
            opts["previews"] = True
        elif a == "--previews-only":
            opts["previews"] = True
            opts["export"] = False
        elif a == "--no-export":
            opts["export"] = False
        elif a == "--blend":
            opts["blend"] = os.path.abspath(argv[i + 1]); i += 1
        elif a == "--work":
            opts["work"] = os.path.abspath(argv[i + 1]); i += 1
        elif a == "--strict-landmarks":
            opts["strict"] = True
        elif a == "--no-landmarks":
            opts["landmarks"] = False
        elif a == "--previews-dir":
            opts["previews_dir"] = os.path.abspath(argv[i + 1]); i += 1
        else:
            sys.exit(f"unknown option {a}")
        i += 1
    return opts


def run_venv(*args):
    if not os.path.exists(VENV_PY):
        raise RuntimeError(f"{VENV_PY} missing (the tools venv with Pillow)")
    r = subprocess.run([VENV_PY, "-I", *args], capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    if r.returncode:
        sys.stderr.write(r.stderr)
        raise RuntimeError(f"{os.path.basename(args[0])} failed ({r.returncode})")


class Stage:
    """Build context shared by the stage_* modules."""

    def __init__(self, data, area, mats, tiles):
        self.root = ROOT
        self.data = data
        self.area = area
        self.mats = mats
        self.tiles = tiles
        self.cx, self.cy = data["center"]
        H = data["extent_half_m"]
        self.ext_local = (-H, -H, H, H)
        px0, py0, px1, py1 = data["play"]
        self.play_local = (px0 - self.cx, py0 - self.cy, px1 - self.cx, py1 - self.cy)
        m = 2.0  # collision ground: the play zone + 2 m (nothing outside the boundary walls is reachable)
        cb = [self.play_local[0] - m, self.play_local[1] - m, self.play_local[2] + m, self.play_local[3] + m]
        for w in data["water"]:  # the collision ground must contain whole ponds (holes)
            x0, y0, x1, y1 = w["bbox"]
            x0, y0, x1, y1 = x0 - self.cx, y0 - self.cy, x1 - self.cx, y1 - self.cy
            if not (x1 < cb[0] or x0 > cb[2] or y1 < cb[1] or y0 > cb[3]):
                cb = [min(cb[0], x0 - 1), min(cb[1], y0 - 1), max(cb[2], x1 + 1), max(cb[3], y1 + 1)]
        cb = [max(cb[0], -H), max(cb[1], -H), min(cb[2], H), min(cb[3], H)]
        self.col_bounds = tuple(cb)
        self.accs = {}
        self.water_boxes = []
        self.stats = {}
        self.replaced_ids = set()      # osm ids built by landmark modules
        self.fallback_ids = set()      # osm ids built by the generator's own fallback models
        self.replaced_ways = set()     # OSM ways (roads / paths / barriers) a landmark module draws itself
        self.replaced_areas = set()    # OSM areas a landmark module draws itself
        self.removed_points = set()    # OSM nodes (trees, props) a landmark module removes
        self.landmark_entries = []
        self.landmark_objects = []
        self.landmark_report = []
        self.doors = []

    def T(self, p):
        return (p[0] - self.cx, p[1] - self.cy)

    def acc(self, name, collision=True, render=True):
        import stage_geom as G
        if name not in self.accs:
            self.accs[name] = (G.MeshAcc(name, self.tiles), collision, render)
        return self.accs[name][0]


def boundary_walls(S):
    """Invisible walls around the play zone (inward facing, ~20 m segments). They do not block the
    camera (SURFACE_NO_CAM_COLLISION)."""
    acc = S.acc("Boundary walls", render=False)
    x0, y0, x1, y1 = S.play_local
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    for a, b in zip(corners, corners[1:] + corners[:1]):
        n = math.ceil(math.dist(a, b) / 20.48)
        for k in range(n):
            p0 = (a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n)
            p1 = (a[0] + (b[0] - a[0]) * (k + 1) / n, a[1] + (b[1] - a[1]) * (k + 1) / n)
            acc.wall(p1, p0, BOUNDARY_WALL_BOTTOM, BOUNDARY_WALL_TOP, "COL nocam")  # normal points inward


def yaw_for_facing(facing_deg):
    """Blender empty Z rotation for an object that faces compass direction facing_deg."""
    return (180.0 - facing_deg) % 360.0


def lua_sign_name(slug):
    return "SGL_HUB_SIGN_" + slug.upper()


class CollisionProbe:
    """Ray queries against every collision mesh of the stage (stage metres)."""

    def __init__(self, objs):
        from mathutils.bvhtree import BVHTree
        verts, polys = [], []
        for o in objs:
            if o.type != "MESH" or getattr(o, "ignore_collision", False):
                continue
            mw = o.matrix_world
            base = len(verts)
            verts.extend(mw @ v.co for v in o.data.vertices)
            polys.extend([base + i for i in p.vertices] for p in o.data.polygons)
        self.tree = BVHTree.FromPolygons(verts, polys) if polys else None

    def floor(self, x, y, z_from):
        """Height of the first surface below (x, y, z_from) or None."""
        from mathutils import Vector
        if self.tree is None:
            return None
        hit = self.tree.ray_cast(Vector((x, y, z_from)), Vector((0, 0, -1)), 200.0)
        return None if hit[0] is None else hit[0].z

    def inside(self, x, y, z):
        """True when (x, y, z) is inside a closed collision volume: a ray up hits a surface from its
        back (an up-facing roof seen from below), or most horizontal rays hit wall backs."""
        from mathutils import Vector
        if self.tree is None:
            return False
        up = self.tree.ray_cast(Vector((x, y, z)), Vector((0, 0, 1)), 200.0)
        if up[0] is not None and up[1].z > 0.2:
            return True
        backs = hits = 0
        for k in range(8):
            a = k * math.pi / 4
            d = Vector((math.cos(a), math.sin(a), 0))
            h = self.tree.ray_cast(Vector((x, y, z)), d, 120.0)
            if h[0] is not None:
                hits += 1
                backs += h[1].dot(d) > 0.05
        return hits >= 4 and backs * 2 > hits

    def clearance(self, x, y, z, reach=3.0):
        """Shortest horizontal distance to a surface at height z (8 directions, up to reach)."""
        from mathutils import Vector
        best = reach
        for k in range(8):
            a = k * math.pi / 4
            hit = self.tree.ray_cast(Vector((x, y, z)), Vector((math.cos(a), math.sin(a), 0)), reach)
            if hit[0] is not None:
                best = min(best, hit[3])
        return best


def landmark_extras(S):
    """Gameplay hints the landmark modules export besides the contract (climb routes, top platforms,
    spots, markers), passed through to the build report for star / object placement later."""
    out = {}
    for e in S.landmark_entries:
        extra = {k: e[k] for k in ("spots", "climb_route_m", "top_platform", "markers", "height_m")
                 if k in e}
        if extra:
            out[e["slug"]] = extra
    return out


def place_on_ground(probe, x, y, z_ref, candidates):
    """First candidate (dx, dy) offset whose floor is within 1.5 m of z_ref and that has 0.9 m of
    room around it. Returns (x, y, z, clearance, index)."""
    best = None
    for i, (dx, dy) in enumerate(candidates):
        px, py = x + dx, y + dy
        fz = probe.floor(px, py, z_ref + 1.5)
        if fz is None or abs(fz - z_ref) > 1.5:
            continue
        cl = probe.clearance(px, py, fz + 0.6)
        if cl >= 0.9:
            return px, py, fz, cl, i
        if best is None or cl > best[3]:
            best = (px, py, fz, cl, i)
    return best or (x + candidates[0][0], y + candidates[0][1], z_ref, 0.0, 0)


def patch_fog(level_dir, fm, fo, color):
    """Fast64 writes gsSPFogPosition(min, max) (integer permille); replace it with the exact
    gsSPFogFactor and the sRGB fog colour."""
    import re
    path = os.path.join(level_dir, "model.inc.c")
    src = open(path).read()
    n_pos = len(re.findall(r"gsSPFogPosition\(\s*-?\d+\s*,\s*-?\d+\s*\)", src))
    src = re.sub(r"gsSPFogPosition\(\s*-?\d+\s*,\s*-?\d+\s*\)", f"gsSPFogFactor({fm}, {fo})", src)
    src, n_col = re.subn(r"gsDPSetFogColor\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)",
                         "gsDPSetFogColor(%d, %d, %d, 255)" % tuple(color), src)
    open(path, "w").write(src)
    return n_pos, n_col


def export_hygiene(level_dir):
    """Deterministic, diffable exports: Fast64 writes geometry-mode flags in a varying order and a
    trailing space after some script commands. Sort the OR-ed flags (same value) and strip trailing
    whitespace. Also returns the largest |vertex coordinate| (s16 hygiene check)."""
    import re
    path = os.path.join(level_dir, "model.inc.c")
    src = open(path).read()

    def sort_flags(m):
        flags = sorted(f.strip() for f in m.group(2).split("|"))
        return f"{m.group(1)}({' | '.join(flags)})"
    src, n_set = re.subn(r"(gsSP(?:Set|Clear)GeometryMode)\(([^()]*)\)", sort_flags, src)

    def sort_two(m):
        a = " | ".join(sorted(f.strip() for f in m.group(1).split("|")))
        b = " | ".join(sorted(f.strip() for f in m.group(2).split("|")))
        return f"gsSPGeometryMode({a}, {b})"
    src, n_two = re.subn(r"gsSPGeometryMode\(([^(),]*),\s*([^(),]*)\)", sort_two, src)
    open(path, "w").write(src)
    vmax = 0
    for m in re.finditer(r"\{\{\{\s*(-?\d+),\s*(-?\d+),\s*(-?\d+)\s*\}", src):
        vmax = max(vmax, abs(int(m.group(1))), abs(int(m.group(2))), abs(int(m.group(3))))
    stripped = 0
    for fn in ("script.c", "geo.inc.c", "header.inc.h", "leveldata.inc.c"):
        fp = os.path.join(level_dir, fn)
        if not os.path.exists(fp):
            continue
        lines = open(fp).read().split("\n")
        new = [ln.rstrip() for ln in lines]
        stripped += sum(1 for a, b in zip(lines, new) if a != b)
        open(fp, "w").write("\n".join(new))
    return {"geometry_mode_lines_sorted": n_set + n_two, "trailing_ws_lines": stripped, "max_abs_vertex": vmax}


def lua_far_units():
    """SGL_HUB_FAR_UNITS from mods/sgl64/levels.lua (None if missing)."""
    import re
    try:
        src = open(os.path.join(ROOT, "mods", "sgl64", "levels.lua")).read()
    except OSError:
        return None
    m = re.search(r"SGL_HUB_FAR_UNITS\s*=\s*(\d+)", src)
    return int(m.group(1)) if m and "set_override_far" in src else None


def main():
    opts = parse_args()
    key = opts["key"]
    level = f"sgl_{key}"
    t0 = time.time()
    work = opts["work"] or tempfile.mkdtemp(prefix=f"sgl_{key}_")
    os.makedirs(work, exist_ok=True)

    # ---- 1-2: textures + stage data (tools venv: Pillow / planner)
    run_venv(os.path.join(HERE, "make_textures.py"))
    data_path = os.path.join(work, f"{key}_data.json")
    run_venv(os.path.join(HERE, "stage_data.py"), key, data_path)
    data = json.load(open(data_path))

    # ---- 3: scene
    import sgl_level as L
    from sgl_blender import setup_fast64
    import stage_buildings
    import stage_geom as G
    import stage_ground
    import stage_landmarks
    import stage_materials
    import stage_nature

    L.new_empty_scene()
    setup_fast64()
    scene = L.configure_scene()
    scene.fast64.sm64.fix_coop_fog = True

    root = L.make_level(f"{level} Level Root", background=BACKGROUND)
    area = L.make_area(root, 1, music=MUSIC, terrain="TERRAIN_GRASS", camera="CAMERA_MODE_FREE_ROAM",
                       clip=(NEAR_CLIP, FAR_CLIP))
    area.fast64.sm64.area.set_fog = True
    lin = tuple(stage_materials._srgb_to_linear(c / 255.0) for c in FOG_COLOR_SRGB)
    area.area_fog_color = (*lin, 1.0)
    area.area_fog_position = (990, 1000)  # placeholder, replaced by gsSPFogFactor after export
    fm, fo, _ = coop_fog_factor(FOG_START_M, FOG_END_M)

    # warp nodes: 0x0A spawn; 0xF0/0xF1 success/death exits must name a vanilla level (custom level
    # numbers only exist at runtime); mods/sgl64/levels.lua turns them into a warp back to the hub.
    L.add_warp_node(area, 0x0A, "LEVEL_CASTLE", 1, 0x0A)
    L.add_warp_node(area, 0xF0, "LEVEL_CASTLE", 1, 0x32)
    L.add_warp_node(area, 0xF1, "LEVEL_CASTLE", 1, 0x64)

    mats = stage_materials.make_materials()
    S = Stage(data, area, mats, stage_materials.tiles())

    if opts["landmarks"]:
        stage_landmarks.load_modules(S, strict=opts["strict"])
        stage_landmarks.resolve_conflicts(S)
    stage_ground.build(S)
    tower = next((b for b in data["buildings"] if b["id"] == "w150860043"), None)
    if tower and "w150860043" not in S.replaced_ids:
        S.stats["century_tower"] = stage_landmarks.century_tower(S, tower)
        S.fallback_ids.add("w150860043")
    stage_buildings.build(S)
    stage_landmarks.props(S)
    stage_landmarks.doors(S)
    sp = SPAWN.get(key, {"pos": tuple(data["center"]), "facing": 0.0})
    keep_clear = [(sp["pos"][0], sp["pos"][1], 3.5)]          # map metres: no climbable tree here
    if "sign" in sp:
        keep_clear.append((sp["sign"]["pos"][0], sp["sign"]["pos"][1], 2.5))
    keep_clear += [(d["map_pos"][0], d["map_pos"][1], 7.0) for d in S.doors if d.get("sign")]
    stage_nature.build(S, keep_clear)
    boundary_walls(S)

    # ---- meshes
    objs = []
    built = set()

    def build_accs():
        for name, (acc, collision, render) in S.accs.items():
            if name in built:
                continue
            built.add(name)
            o = acc.build(mats, parent=area, collision=collision, render=render)
            if o is not None:
                objs.append(o)
    build_accs()
    # ---- set dressing, checked against the real collision (then built like the rest)
    import stage_dressing
    probe = CollisionProbe(objs + S.landmark_objects)
    avoid = [(x - S.cx, y - S.cy, r) for x, y, r in keep_clear[:2]]
    avoid += [(t["stage"][0], t["stage"][1], 1.6) for t in S.pole_trees]
    lamp_poles = stage_dressing.build(S, probe, avoid)
    build_accs()
    uv_span = max(acc.max_uv_span for acc, _, _ in S.accs.values())
    for name, (acc, collision, render) in S.accs.items():
        if render and acc.max_uv_span > G.UV_SPAN_MAX + 1:
            print(f"SGL WARNING: {name}: a face spans {acc.max_uv_span:.1f} texture repeats "
                  f"({getattr(acc, 'max_uv_where', '')}; N64 limit ~{G.UV_SPAN_MAX:.0f} for 64 px textures)")
    for (x0, y0, x1, y1, surf, bottom, name) in S.water_boxes:
        L.add_water_box(area, x0, y0, x1, y1, surface_z=surf, bottom_z=bottom)

    # ---- objects: spawn, welcome sign, door signs (checked against the real collision)
    probe = CollisionProbe(objs + S.landmark_objects)
    sx, sy = S.T(sp["pos"])
    spawn_floor = probe.floor(sx, sy, 3.0)
    spawn_clear = probe.clearance(sx, sy, (spawn_floor or 0.0) + 0.6)
    if spawn_floor is None or abs(spawn_floor) > 0.5 or spawn_clear < 1.5:
        print(f"SGL WARNING: spawn at {sp['pos']}: floor {spawn_floor}, clearance {spawn_clear:.1f} m")
    L.add_spawn(area, (sx, sy, (spawn_floor or 0.0) + 1.0), yaw_deg=yaw_for_facing(sp["facing"]))
    lua_names = []
    if "sign" in sp:
        gx, gy = S.T(sp["sign"]["pos"])
        gx, gy, gz, _, _ = place_on_ground(probe, gx, gy, 0.0, [(0, 0), (1.5, 0), (-1.5, 0), (0, 1.5)])
        L.add_object(area, "Sign welcome", (gx, gy, gz), "bhvMessagePanel", "MODEL_WOODEN_SIGNPOST",
                     bparams=sp["sign"]["lua"], yaw_deg=yaw_for_facing(sp["sign"]["facing"]))
        lua_names.append(sp["sign"]["lua"])
    door_out = []
    for d in S.doors:
        x, y, z = d["map_pos"]
        f = math.radians(d["facing"])
        nx, ny = math.sin(f), math.cos(f)
        tx, ty = -ny, nx
        # sign in front of the door, off to one side, facing the same way as the door
        lname = lua_sign_name(d["slug"]) if d.get("sign", True) else None
        sgx = sgy = None
        if lname:
            cands = [(nx * a + tx * b, ny * a + ty * b) for a, b in
                     ((3.0, 2.6), (3.0, -2.6), (4.5, 3.2), (4.5, -3.2), (6.0, 0.0), (6.0, 4.0), (6.0, -4.0))]
            px, py, pz, pcl, ci = place_on_ground(probe, x - S.cx, y - S.cy, z, cands)
            if pcl < 0.9:
                print(f"SGL WARNING: sign for {d['slug']}: only {pcl:.1f} m clearance")
            sgx, sgy = px + S.cx, py + S.cy
            L.add_object(area, f"Sign {d['slug']}", (px, py, pz), "bhvMessagePanel",
                         "MODEL_WOODEN_SIGNPOST", bparams=lname, yaw_deg=yaw_for_facing(d["facing"]))
            lua_names.append(lname)
        ename = d["name"] if str(d.get("name", "")).startswith("DOOR_") else f"DOOR_{d['slug']}"
        e = bpy.data.objects.new(ename, None)
        scene.collection.objects.link(e)
        e.location = (x - S.cx, y - S.cy, z)
        e.rotation_euler = (0, 0, math.radians(yaw_for_facing(d["facing"])))
        door_out.append({
            "slug": d["slug"], "name": e.name, "label": d.get("label"), "building_osm_id": d["osm_id"],
            "stage": d["stage"], "stars_required": d["stars"], "map_m": [round(x, 2), round(y, 2), round(z, 2)],
            "facing_deg": round(d["facing"], 1),
            "game_units": [round((x - S.cx) * 100), round(z * 100), round(-(y - S.cy) * 100)],
            "game_yaw": int(round(math.radians(yaw_for_facing(d["facing"])) / (2 * math.pi) * 65536)) & 0xFFFF,
            "sign_lua_bparam": lname, "sign_map_m": [round(sgx, 2), round(sgy, 2)] if lname else None,
            "source": d["source"], "marker_drawn": d["marker"], "module_primary": d.get("module_primary"),
            "note": d.get("note")})

    # ---- climbable trees (bhvTree) and lamp posts (bhvPoleGrabbing): MODEL_NONE pole objects on
    # visual-only trunks / posts; the pole hitbox pushes Mario out like a trunk collider
    pole_out = []
    for i, t in enumerate(S.pole_trees):
        x, y = t["stage"]
        fz = probe.floor(x, y, 3.0)
        cl = probe.clearance(x, y, (fz or 0.0) + 0.6, 2.0)
        if fz is None or abs(fz) > 0.3:
            print(f"SGL WARNING: climbable tree {t['id']}: floor {fz}")
        if cl < 1.2:
            print(f"SGL WARNING: climbable tree {t['id']}: collision {cl:.2f} m from the trunk")
        L.add_object(area, f"Tree {i:02d} {t['id']}", (x, y, fz or 0.0), TREE_BEHAVIOR, "MODEL_NONE")
        pole_out.append({"kind": "tree", "osm_id": t["id"], "map_m": [round(x + S.cx, 2), round(y + S.cy, 2)],
                         "floor_m": round(fz or 0.0, 2), "clearance_m": round(cl, 2), "pole_m": 5.0,
                         "behavior": TREE_BEHAVIOR})
    for p in lamp_poles:
        x, y = p["stage"]
        fz = probe.floor(x, y, 3.0) or 0.0
        tenth = int(round(p["height_m"] * 10))
        L.add_object(area, p["name"], (x, y, fz), LAMP_BEHAVIOR, "MODEL_NONE", bparams="0x00%02X0000" % tenth)
        pole_out.append({"kind": "lamp", "map_m": [round(x + S.cx, 2), round(y + S.cy, 2)], "floor_m": round(fz, 2),
                         "pole_m": tenth / 10, "behavior": LAMP_BEHAVIOR, "bparams": "0x00%02X0000" % tenth})
    climb = {b["name"] or b["id"]: b["climb_route"] for b in S.stats.get("buildings", []) if b.get("climb_route")}

    # ---- report
    def count(filter_fn):
        return sum(G.tris_of(o) for o in objs + S.landmark_objects if filter_fn(o))
    coll = {o.name: G.tris_of(o) for o in objs + S.landmark_objects if not o.ignore_collision}
    vis = {o.name: G.tris_of(o) for o in objs + S.landmark_objects if not o.ignore_render}
    report = {
        "level": level, "stage": key, "built_at": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime()),
        "center_m": data["center"], "window_m": data["window"], "play_m": data["play"],
        "extent_half_m": data["extent_half_m"],
        "collision_tris": sum(coll.values()), "visual_tris": sum(vis.values()),
        "collision_by_object": coll, "visual_by_object": vis,
        "landmark_modules": S.landmark_report, "replaced_osm_ids": sorted(S.replaced_ids),
        "replaced_ways": sorted(S.replaced_ways), "replaced_areas": sorted(S.replaced_areas),
        "removed_points": sorted(S.removed_points),
        "spawn": {"map_m": list(sp["pos"]), "game_units": [round(sx * 100), round(((spawn_floor or 0) + 1) * 100),
                                                             round(-sy * 100)],
                  "facing_deg": sp["facing"], "floor_m": spawn_floor, "clearance_m": round(spawn_clear, 2)},
        "doors": door_out, "lua_globals_needed": lua_names,
        "landmark_extras": landmark_extras(S),
        "pole_objects": pole_out, "climb_routes": climb,
        "fog": {"start_m": FOG_START_M, "end_m": FOG_END_M, "gsSPFogFactor": [fm, fo], "color_srgb": FOG_COLOR_SRGB,
                "far_clip_units": FAR_CLIP, "override_far_units": int(OVERRIDE_FAR_M * 100),
                "lua_far_units": lua_far_units()},
        "water_boxes": [{"name": w[6], "stage_m": [round(v, 2) for v in w[:4]], "surface_m": w[4]}
                        for w in S.water_boxes],
        "stats": S.stats,
        "attribution": data["attribution"],
    }
    print(f"SGL: built {level}: {len(objs)} meshes, collision {report['collision_tris']} tris, "
          f"visual {report['visual_tris']} tris ({time.time() - t0:.1f}s)")
    for k in ("collision_by_object",):
        for n, c in sorted(report[k].items(), key=lambda t: -t[1]):
            print(f"   collision {c:6d}  {n}")

    if opts["blend"]:
        os.makedirs(os.path.dirname(opts["blend"]), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=opts["blend"], copy=True)
        print(f"SGL: saved {opts['blend']}")

    art_dir = os.path.join(ROOT, "art", "levels", key)
    os.makedirs(art_dir, exist_ok=True)
    if opts["export"]:
        from export_level import export_level
        from validate_level import validate_level
        level_dir, _ = export_level(root.name, level, opts["levels_dir"], setup=False, validate=False)
        n_pos, n_col = patch_fog(level_dir, fm, fo, FOG_COLOR_SRGB)
        hyg = export_hygiene(level_dir)
        report["export_hygiene"] = hyg
        if hyg["max_abs_vertex"] > 32767:
            print(f"SGL WARNING: a vertex coordinate is {hyg['max_abs_vertex']} (> s16)")
        lf = lua_far_units()
        if lf != int(OVERRIDE_FAR_M * 100):
            print(f"SGL WARNING: levels.lua SGL_HUB_FAR_UNITS = {lf}, the fog is fitted to "
                  f"{int(OVERRIDE_FAR_M * 100)} (set_override_far)")
        rep = validate_level(level_dir)
        print(rep["text"])
        report["validation"] = {"errors": rep["errors"], "warnings": rep["warnings"],
                                "collision_tris": rep.get("collision_tris"), "render_tris": rep.get("render_tris"),
                                "lua_names": rep.get("lua_names"), "fog_patched": [n_pos, n_col]}
        report["level_dir"] = level_dir
        if rep["errors"]:
            json.dump(report, open(os.path.join(art_dir, f"{level}_build.json"), "w"), indent=1)
            raise RuntimeError(f"{len(rep['errors'])} validation error(s) in {level_dir}")
        print(f"SGL: exported {level_dir} (fog factor {fm}, {fo}; {n_pos} fog commands patched) "
              f"in {time.time() - t0:.1f}s")
    if opts["export"]:
        json.dump(report, open(os.path.join(art_dir, f"{level}_build.json"), "w"), indent=1)

    if opts["previews"]:
        import stage_preview
        pv = opts["previews_dir"] or os.path.join(art_dir, "previews")
        paths = stage_preview.render_all(S, pv, fog=(FOG_START_M, FOG_END_M, FOG_COLOR_SRGB),
                                         fog_params=coop_fog_factor(FOG_START_M, FOG_END_M),
                                         far_m=OVERRIDE_FAR_M)
        top = next((p for p in paths if p.endswith("_topdown.png")), None)
        if top:
            run_venv(os.path.join(HERE, "compare_map.py"), key, top, os.path.join(pv, f"{key}_map_compare.png"))
    print(f"SGL: done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        print(f"SGL ERROR: {e}")
        sys.exit(1)
