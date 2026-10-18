"""Build a UF campus stage (true 1:1 scale) as a coopdx DynOS level, headlessly.

Usage:
  tools/blender/run_blender.sh tools/campus/build_stage.py -- hub [options]
  tools/blender/run_blender.sh tools/campus/build_stage.py -- swamp --slot bob [options]
    --slot NAME          vanilla level slot to replace (docs/flow.md): castle_grounds (the hub), bob, wf,
                         jrb, ccm, bbh, ttc. Default: STAGE_SLOTS[<key>] (hub -> castle_grounds,
                         swamp -> bob, reitz_eng -> wf, lake_alice -> jrb). Writes
                         <levels-dir>/<slot>/ with script level_<slot>_entry: DynOS compiles it into
                         level_<slot>_entry.lvl, which replaces that vanilla level.
    --custom             old behaviour: a custom level sgl_<key> (level_register in levels.lua)
    --levels-dir DIR     where the level folder goes (default mods/sgl64/levels)
    --report-dir DIR     where sgl_<key>_build.json goes (default art/levels/<key>, or STAGE_SHORT_NAMES: reitz_eng ->
                         art/levels/reitz; e.g. scratch for test builds)
    --previews           render previews to art/levels/<key>/previews/ (STAGE_SHORT_NAMES) after exporting
    --previews-only      build + render previews, do not export
    --no-export          build only (with --blend to inspect it)
    --blend OUT.blend    save the built scene
    --work DIR           intermediate files (default: a temp dir)
    --strict-landmarks   a failing landmark module stops the build (default: warn + generic building)
    --no-landmarks       ignore tools/campus/landmarks/*.py (generic + fallback models only)
    --previews-dir DIR   render previews there instead of art/levels/<key>/previews/
    --repair-collision / --no-repair-collision
                         T-junction-split + weld the exported floors (stage_collision.py; default on
                         for REPAIR_COLLISION_STAGES = the hub and the swamp)
    --no-interior        skip the stage's extra interior areas (STAGE_INTERIOR_AREAS; reitz_eng: area 2, the
                         Reitz Union interior); area 1 keeps its door hookups (scratch verification builds)
The swamp and reitz_eng also write their mission anchor points (stage_points.py) to
data/uf/swamp_points.json / data/uf/reitz_points.json (next to the report for a --report-dir test build).
Course 3, lake_alice (slot jrb): its stage-specific parts (tree thinning, the observation deck + nest, pickups,
data/uf/lake_points.json, preview cameras) live in stage_lake.py.

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
OVERRIDE_FAR_M with set_override_far() while a player is in the hub or a stage, and the fog is fitted
to that (fog only starts at FOG_START_M, so Century Tower stays visible from the whole Plaza).
Level name: the slot (hub -> mods/sgl64/levels/castle_grounds/, level_castle_grounds_entry), or
sgl_<key> with --custom. Build report: art/levels/<key>/sgl_<key>_build.json.

Flow contract (docs/flow.md), written into the level script by add_flow_warps():
  hub (castle_grounds), area 1:
    0x0A  Plaza spawn (bhvSpinAirborneWarp; also MARIO_POS for a fresh start / game over)
    0x0B  Plaza death respawn (bhvDeathWarp)        0xF0 -> 0x0A, 0xF1 -> 0x0B (dying in the hub)
    0x10+i  door i -> LEVEL_<stage i>, area 1, node 0x0A   (id_bhvSglDoor object, bparams
            i << 24 | (0x10+i) << 16 | trigger half width dm << 8 | emblem height dm)
    0x20+i  return after a star            (bhvPaintingStarCollectWarp just outside door i)
    0x30+i  return after a death / "Exit course" (bhvPaintingDeathWarp, same spot)
    doors i: 1 Swamp = Auditorium, 2 Reitz = The Hub, 3 Lake Alice = Newell, 4 Marston,
             5 Library West, 6 Century Tower
  stage in slot s with door i, area 1:
    0x0A  entry spawn (bhvSpinAirborneWarp)   0xF0 -> CASTLE_GROUNDS 0x20+i   0xF1 -> CASTLE_GROUNDS 0x30+i
  extra areas (STAGE_INTERIOR_AREAS, additive): reitz_eng's area 2 = the Reitz Union interior
  (tools/campus/interiors/reitz.py via build_interior.build_area): its own 0x0A (debug), 0xF0 / 0xF1 as area 1,
  bhvFadingWarp elevator pads (0x40+); area 1 <-> 2 through INSTANT_WARPs on the landmark's door floors.
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
OVERRIDE_FAR_M = 1000.0      # projection far plane in the hub + stages: levels.lua SGL_FAR_UNITS
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
                 "sign": {"pos": (38.64, 137.42), "facing": 355.0, "lua": "SGL_HUB_SIGN_WELCOME"}},
         # The Swamp: the Courtyard of Champions just north of the stadium's north gatehouse (the
         # swamp_stadium module's suggested_stage_spawn), facing south at the Sunshine Seats, the north
         # gate tunnel straight ahead and the two helix ramp towers either side
         "swamp": {"pos": (-513.49, 272.98), "facing": 180.0},
         # Course 2, Reitz Union & Engineering: on the North Lawn's west walks, about 40 m north-east of the
         # Reitz Union, facing south-west at it (fun review fix round: the first shot is the landmark): the
         # glass east wing and the 27 m tower ahead, the north colonnade on the right, act 1's CLIMB HERE
         # (the ravine terrace at the south-west corner, behind the building) 16 degrees left of centre
         "reitz_eng": {"pos": (-398.0, -200.0), "facing": 214.0},
         # Course 3, Lake Alice: the bat-house field on the north shore (lake_alice_shore.py's landing zone,
         # spot spawn_field), the 2010 / 2017 bat barns behind, facing south-south-east over the observation
         # fence and Museum Road down the arrival vista (stage_lake.SPAWN_VISTA) to the north boardwalk inlet,
         # the west bog (the island nest) and the lily-pad line to the observation deck
         "lake_alice": {"pos": (-1893.0, -541.0), "facing": 150.0}}
# per-stage look (keys override FOG_COLOR_SRGB / BACKGROUND / MUSIC / terrain); the fog distances and
# the far plane are shared (levels.lua SGL_FAR_UNITS)
STAGE_LOOK = {
    # game-day afternoon: same blue sky, a touch warmer haze over the stands
    # its own music (fun review: the hub and the Swamp both played SEQ_LEVEL_GRASS); the act 2 race
    # switches to SEQ_LEVEL_SLIDE while racing (sgl_mission.lua)
    "swamp": {"fog_color": (188, 204, 224), "background": "OCEAN_SKY", "music": "SEQ_LEVEL_SNOW",
              "terrain": "TERRAIN_GRASS"},
    # Course 2: a hot Gainesville afternoon on the quad (a warmer, paler haze); its own music, Lethal Lava
    # Land / Shifting Sand Land's theme (adventurous, tall things to climb; the hub keeps GRASS, the
    # Swamp SNOW, races SLIDE)
    "reitz_eng": {"fog_color": (200, 206, 216), "background": "OCEAN_SKY", "music": "SEQ_LEVEL_HOT",
                  "terrain": "TERRAIN_GRASS"},
    # Course 3: a humid daytime over the water (a soft green-blue haze); Jolly Roger Bay / Dire Dire Docks'
    # water theme (the slot's own vanilla music). The act 4 dusk look is applied per act from Lua.
    "lake_alice": {"fog_color": (182, 206, 210), "background": "OCEAN_SKY", "music": "SEQ_LEVEL_WATER",
                   "terrain": "TERRAIN_GRASS"},
}
# level-script stars a stage build places itself (docs/flow.md 5: act k -> star id k - 1, ACT_k).
# "spot" = a landmark module spot (landmark_extras) or "pos": (map x, y, z hint); the star hovers
# STAR_UP_M above the ray-cast floor there. Mission stars that Lua spawns are not listed here.
STAGE_STARS = {
    # design 7.1 act 1 "Kickoff: Climb the Skybox": the star sits on the 66 m press box roof, at the end
    # of the module's climb route (rim -> tower ledges -> Bull Gator Deck -> camera decks -> roof)
    "swamp": [{"act": 1, "landmark": "stadium", "spot": "press_box_roof_star",
               "name": "Kickoff star (press box roof)"}],
    # Course 2 has no level-script star (integration decision, docs/flow.md §11): every Reitz mission
    # spawns its own star from its controller, act 1 ROOFTOP OF THE REITZ included (spawn_default_star at
    # reitz_points.json act1_rooftop.star_target, the penthouse roof 1.2 m up; wf_reitz_missions.lua
    # reitz_rooftop has no levelStar). To switch act 1 to a Swamp-style level-script star, add
    #   "reitz_eng": [{"act": 1, "landmark": "reitz_union", "spot": "roof_star",
    #                  "name": "Rooftop of the Reitz star (tower penthouse)"}],
    # rebuild, AND set levelStar = true on reitz_rooftop (tools/luatest test_flow / test_reitz_missions
    # fail on a mismatch either way).
}
STAR_UP_M = 1.2
# coins, hearts, 1-ups, Goombas and the landmark poles a stage places in its level script
# (stage_pickups.py; the report lists them under "pickups")
STAGE_PICKUPS = {"swamp": lambda m: m.swamp_pickups, "reitz_eng": lambda m: m.reitz_pickups,
                 "lake_alice": lambda m: __import__("stage_lake").lake_pickups,      # Course 3: stage_lake.py
                 "hub": lambda m: m.hub_pickups}                                     # the rival Goombas
# stages whose level script loads the common0 model group (MODEL_HEART, MODEL_GOOMBA, ...):
# JUMP_LINK(script_func_global_1) after MARIO(...), as every vanilla course does
STAGE_COMMON0_MODELS = {"swamp", "reitz_eng", "lake_alice", "hub"}   # hub: the rival Goombas (368e21f)
# stage key -> anchor point exporter (stage_points.py), run after the build: data/uf/<key>_points.json
STAGE_POINTS = {"swamp": lambda m: m.swamp_points, "reitz_eng": lambda m: m.reitz_points,
                "lake_alice": lambda m: __import__("stage_lake").lake_points}        # data/uf/lake_points.json
# post-export collision seam repair (stage_collision.py: T-junction split + vertex weld of the floors on
# the exported integer data, so rounded seams leave no find_floor NULL points = invisible walls or holes).
# On by default for these stages (the hub since the integration pass: its seams had ~21k crack points,
# mostly on roofs); --repair-collision / --no-repair-collision override
REPAIR_COLLISION_STAGES = {"swamp", "hub", "reitz_eng", "lake_alice"}
# short name of a stage whose stages.json key is long: its art folder (art/levels/<short>/: build report,
# previews) and its anchor points (data/uf/<short>_points.json); others use the key itself
STAGE_SHORT_NAMES = {"reitz_eng": "reitz", "lake_alice": "lake"}
# extra areas of a stage built from interior modules (tools/campus/interiors/<key>.py, an AREA module: AREA,
# CENTER = the stage centre, instant_warps(), WARP_MAT / WARP_SURFACE). Course 2: area 2 = the Reitz Union interior,
# entered through the landmark's real doors (landmarks/reitz_reitz_union.py puts the area-1 warp floors there).
# Stages not listed build exactly as before.
STAGE_INTERIOR_AREAS = {"reitz_eng": ["reitz"]}
TREE_BEHAVIOR = "bhvTree"            # vanilla climbable tree: SET_HITBOX(80, 500), pushes Mario away
LAMP_BEHAVIOR = "bhvPoleGrabbing"    # vanilla pole: hitbox height = bparam2 * 10 units

# ------------------------------------------------------------------ level slots + warp contract
# docs/flow.md. Stages replace vanilla levels (DynOS level_<slot>_entry.lvl, the Star Road way).
HUB_SLOT = "castle_grounds"
SLOT_LEVELS = {"castle_grounds": "LEVEL_CASTLE_GROUNDS", "bob": "LEVEL_BOB", "wf": "LEVEL_WF", "jrb": "LEVEL_JRB",
               "ccm": "LEVEL_CCM", "bbh": "LEVEL_BBH", "ttc": "LEVEL_TTC"}
SLOT_DOOR = {"bob": 1, "wf": 2, "jrb": 3, "ccm": 4, "bbh": 5, "ttc": 6}     # stage slot -> hub door index
# hub door index -> stage_landmarks.DOOR_DEFAULTS slug of the building door that leads there
HUB_DOORS = {1: "university_auditorium", 2: "the_hub", 3: "newell_hall", 4: "marston", 5: "library_west",
             6: "century_tower"}
# stages.json key -> default slot (interiors: future keys, same mapping)
STAGE_SLOTS = {"hub": HUB_SLOT, "swamp": "bob", "reitz_eng": "wf", "lake_alice": "jrb", "marston": "ccm",
               "library_west": "bbh", "century_tower": "ttc"}
NODE_SPAWN = 0x0A           # hub Plaza spawn / every stage's entry spawn (warp_to_level target)
NODE_HUB_DEATH = 0x0B       # hub: respawn after dying in the hub (0xF1)
NODE_DOOR = 0x10            # hub: WARP_NODE(0x10 + i) -> stage i, area 1, node 0x0A
NODE_STAR_RETURN = 0x20     # hub: spawn outside door i after a star (stage 0xF0)
NODE_DEATH_RETURN = 0x30    # hub: spawn outside door i after a death / pause "Exit course" (stage 0xF1)
DOOR_BEHAVIOR = "id_bhvSglDoor"                     # mods/sgl64/levels.lua (hook_behavior)
STAR_RETURN_BEHAVIOR = "bhvPaintingStarCollectWarp"  # ACT_EXIT_AIRBORNE: flies out backwards, course-done screen
DEATH_RETURN_BEHAVIOR = "bhvPaintingDeathWarp"      # ACT_DEATH_EXIT: flies out backwards, loses a life
RETURN_SPAWN_UP_M = 0.8      # return spawns hover this high (Mario is launched backwards ~3 m from there)
DOOR_EMBLEM_UP_M = 4.2       # door emblem (spinning star) height above the sill, lowered under porch roofs
DOOR_EMBLEM_OUT_M = 1.2      # ... and its distance in front of the door plane (levels.lua DOOR_EMBLEM_OUT)
DOOR_SIDE_MARGIN_M = 0.6     # door trigger half width = door width / 2 + this (levels.lua bparam3)


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
        sys.exit("usage: build_stage.py -- <stage_key> [--slot NAME | --custom] [--levels-dir DIR] [--previews] "
                 "[--no-export] [--blend OUT] [--work DIR] [--strict-landmarks]")
    opts = {"key": argv[0], "levels_dir": os.path.join(ROOT, "mods", "sgl64", "levels"), "previews": False,
            "export": True, "blend": None, "work": None, "strict": False, "landmarks": True,
            "previews_dir": None, "slot": None, "custom": False, "report_dir": None, "repair_collision": None,
            "interior": True}
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--slot":
            opts["slot"] = argv[i + 1].lower(); i += 1
        elif a == "--custom":
            opts["custom"] = True
        elif a == "--report-dir":
            opts["report_dir"] = os.path.abspath(argv[i + 1]); i += 1
        elif a == "--levels-dir":
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
        elif a == "--repair-collision":
            opts["repair_collision"] = True
        elif a == "--no-repair-collision":
            opts["repair_collision"] = False
        elif a == "--no-interior":
            opts["interior"] = False
        else:
            sys.exit(f"unknown option {a}")
        i += 1
    if opts["custom"]:
        if opts["slot"]:
            sys.exit("--slot and --custom exclude each other")
    else:
        opts["slot"] = opts["slot"] or STAGE_SLOTS.get(opts["key"])
        if opts["slot"] is None:
            sys.exit(f"stage {opts['key']!r} has no default slot (STAGE_SLOTS): pass --slot NAME or --custom")
        if opts["slot"] not in SLOT_LEVELS:
            sys.exit(f"unknown slot {opts['slot']!r}; known: {sorted(SLOT_LEVELS)}")
        if (opts["slot"] == HUB_SLOT) != (opts["key"] == "hub"):
            print(f"SGL WARNING: building stage {opts['key']!r} into slot {opts['slot']!r} "
                  f"(the hub slot is {HUB_SLOT!r}, which only the 'hub' stage should use)")
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

    def __init__(self, data, area, mats, tiles, key=None):
        self.root = ROOT
        self.key = key or data.get("stage", {}).get("key", "hub")   # stages.json key ("hub", "swamp", ...)
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
        self.ground_holes = []         # landmark "ground_holes_m" (stage coords), set by stage_ground.build

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

    def ceiling(self, x, y, z_from, reach=30.0):
        """Height of the first surface above (x, y, z_from) or None."""
        from mathutils import Vector
        if self.tree is None:
            return None
        hit = self.tree.ray_cast(Vector((x, y, z_from)), Vector((0, 0, 1)), reach)
        return None if hit[0] is None else hit[0].z

    def ray(self, x, y, z, dx, dy, reach):
        """Distance to the first surface along the horizontal direction (dx, dy) from (x, y, z), or
        None within reach."""
        from mathutils import Vector
        if self.tree is None:
            return None
        hit = self.tree.ray_cast(Vector((x, y, z)), Vector((dx, dy, 0.0)).normalized(), reach)
        return None if hit[0] is None else hit[3]

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


# ---- real ground relief (stage_terrain.py, USGS 3DEP): reitz_eng only, every other stage stays byte-identical
TERRAIN_DRAPE = {"Ground visual", "Ground collision", "Roads and paths visual", "Pond basins visual",
                 "Pond basins collision", "Pond water"}           # per-vertex drape
TERRAIN_LANDMARKS = ("reitz_malachowsky", "reitz_weil_eng_clocktower")   # whole-module z offset (centroid)
TERRAIN_SMALL_M = 12.0       # components smaller than this (trees, poles, props) ride the height at their centre


def apply_terrain(S, objs):
    """Drape the ground / road ribbons on stage_terrain.height_m and set everything else on it: generic buildings
    sink to the lowest terrain under their footprint (no gap on a slope), trees / props / dressing ride the height
    at their centre, the reitz_malachowsky / reitz_weil_eng_clocktower landmark parts get the height at their
    centroid. Runs before the collision probe that places objects, so spawn / stars / pickups land on it."""
    import bmesh
    import stage_terrain
    if not stage_terrain.has_terrain(S.key):
        return None
    hm = stage_terrain.height_m
    key, cx, cy = S.key, S.cx, S.cy
    T, OFF = stage_terrain.TILE, stage_terrain.TILE_OFF
    st = {"draped_objects": [], "draped_vertices": 0, "components_lifted": 0, "landmarks": {}, "max_m": 0.0,
          "min_m": 0.0}
    flat_cache = {}
    for o in objs:
        if o is None or o.type != "MESH":
            continue
        me = o.data
        lx, ly, lz = o.location
        bm = bmesh.new()
        bm.from_mesh(me)
        if o.name in TERRAIN_DRAPE:
            if o.name.startswith("Roads and paths visual") and bm.verts:
                # split the ribbons on the ground tile lines so they follow the tiled ground exactly on tile edges
                xs = [v.co.x for v in bm.verts]
                ys = [v.co.y for v in bm.verts]
                for axis, lo, hi in ((0, min(xs), max(xs)), (1, min(ys), max(ys))):
                    for k in range(math.floor((lo - OFF) / T), math.floor((hi - OFF) / T) + 1):
                        c = OFF + k * T
                        if not (lo < c < hi):
                            continue
                        geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
                        bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-4,
                                               plane_co=(c, 0, 0) if axis == 0 else (0, c, 0),
                                               plane_no=(1, 0, 0) if axis == 0 else (0, 1, 0))
            # cut the faces of sloped tiles on the tile diagonal (x - y = m * TILE): height_m is planar on each half
            by_diag = {}
            for f in bm.faces:
                c = f.calc_center_median()
                i, j = math.floor((c.x - OFF) / T), math.floor((c.y - OFF) / T)
                if (i, j) not in flat_cache:
                    flat_cache[(i, j)] = all(abs(hm(key, OFF + (i + a) * T + lx + cx, OFF + (j + b) * T + ly + cy)) < 1e-4
                                             for a in (0, 1) for b in (0, 1))
                if flat_cache[(i, j)]:
                    continue
                d = [v.co.x - v.co.y for v in f.verts]
                m = i - j
                if min(d) < m * T - 1e-3 and max(d) > m * T + 1e-3:
                    by_diag.setdefault(m, []).append(f)
            for m, faces in by_diag.items():
                edges = list({e for f in faces for e in f.edges})
                verts = list({v for f in faces for v in f.verts})
                bmesh.ops.bisect_plane(bm, geom=faces + edges + verts, dist=1e-4, plane_co=(m * T, 0, 0),
                                       plane_no=(1, -1, 0))
            st["diagonal_cuts"] = st.get("diagonal_cuts", 0) + sum(len(f) for f in by_diag.values())
            for v in bm.verts:
                h = hm(key, v.co.x + lx + cx, v.co.y + ly + cy)
                v.co.z += h
                st["max_m"], st["min_m"] = max(st["max_m"], h), min(st["min_m"], h)
            st["draped_objects"].append(o.name)
            st["draped_vertices"] += len(bm.verts)
        else:
            bm.verts.ensure_lookup_table()
            parent = list(range(len(bm.verts)))

            def find(i):
                while parent[i] != i:
                    parent[i] = parent[parent[i]]
                    i = parent[i]
                return i
            for e in bm.edges:
                a, b = find(e.verts[0].index), find(e.verts[1].index)
                if a != b:
                    parent[a] = b
            comps = {}
            for v in bm.verts:
                comps.setdefault(find(v.index), []).append(v)
            for vs in comps.values():
                x0 = min(v.co.x for v in vs)
                x1 = max(v.co.x for v in vs)
                y0 = min(v.co.y for v in vs)
                y1 = max(v.co.y for v in vs)
                if math.hypot(x1 - x0, y1 - y0) < TERRAIN_SMALL_M:
                    dz = hm(key, (x0 + x1) / 2 + lx + cx, (y0 + y1) / 2 + ly + cy)
                else:
                    dz = min(hm(key, v.co.x + lx + cx, v.co.y + ly + cy) for v in vs)
                if abs(dz) < 1e-4:
                    continue
                for v in vs:
                    v.co.z += dz
                st["components_lifted"] += 1
        bm.to_mesh(me)
        bm.free()
        me.update()
    groups = {}
    for o in S.landmark_objects:
        mod = str(o.get("sgl_landmark", ""))
        if o.type == "MESH" and any(m in mod for m in TERRAIN_LANDMARKS):
            groups.setdefault(mod, []).append(o)
    for mod, os_ in groups.items():
        pts = [(v.co.x + o.location.x, v.co.y + o.location.y) for o in os_ for v in o.data.vertices]
        if not pts:
            continue
        mx = (min(p[0] for p in pts) + max(p[0] for p in pts)) / 2
        my = (min(p[1] for p in pts) + max(p[1] for p in pts)) / 2
        dz = hm(key, mx + cx, my + cy)
        st["landmarks"][mod] = round(dz, 3)
        if abs(dz) < 1e-4:
            continue
        for o in os_:
            for v in o.data.vertices:
                v.co.z += dz
            o.data.update()
    st["max_m"], st["min_m"] = round(st["max_m"], 2), round(st["min_m"], 2)
    print(f"SGL: terrain (USGS 3DEP): drape {st['draped_objects']} ({st['draped_vertices']} verts, "
          f"{st['min_m']}..{st['max_m']} m), {st['components_lifted']} components set on it, landmarks {st['landmarks']}")
    return st


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


def add_flow_warps(L, area, slot):
    """WARP_NODEs of the flow contract (module docstring, docs/flow.md). slot None = custom level
    (old behaviour: exits name vanilla Castle Inside nodes, levels.lua redirects them to the hub).
    Returns the nodes for the build report."""
    nodes = []

    def node(wid, dest, dest_node, note):
        L.add_warp_node(area, wid, dest, 1, dest_node)
        nodes.append({"id": "0x%02X" % wid, "dest_level": dest, "dest_area": 1, "dest_node": "0x%02X" % dest_node,
                      "note": note})

    cg = SLOT_LEVELS[HUB_SLOT]
    if slot is None:
        node(NODE_SPAWN, "LEVEL_CASTLE", NODE_SPAWN, "spawn (warp_to_level target)")
        node(0xF0, "LEVEL_CASTLE", 0x32, "star exit (levels.lua redirects to the hub)")
        node(0xF1, "LEVEL_CASTLE", 0x64, "death exit (levels.lua redirects to the hub)")
    elif slot == HUB_SLOT:
        node(NODE_SPAWN, cg, NODE_SPAWN, "Plaza spawn (also exitCastleWarpNode, /campus hub)")
        node(NODE_HUB_DEATH, cg, NODE_HUB_DEATH, "Plaza death respawn")
        node(0xF0, cg, NODE_SPAWN, "hub success exit (unused) -> Plaza")
        node(0xF1, cg, NODE_HUB_DEATH, "death in the hub -> Plaza death respawn")
        for i in sorted(HUB_DOORS):
            st = next(s for s, d in SLOT_DOOR.items() if d == i)
            node(NODE_DOOR + i, SLOT_LEVELS[st], NODE_SPAWN, f"door {i} ({HUB_DOORS[i]}) -> {st} entry")
            node(NODE_STAR_RETURN + i, cg, NODE_STAR_RETURN + i, f"return after a star, outside door {i}")
            node(NODE_DEATH_RETURN + i, cg, NODE_DEATH_RETURN + i, f"return after a death / Exit course, door {i}")
    else:
        i = SLOT_DOOR[slot]
        node(NODE_SPAWN, SLOT_LEVELS[slot], NODE_SPAWN, "stage entry spawn")
        node(0xF0, cg, NODE_STAR_RETURN + i, f"star exit -> hub outside door {i}")
        node(0xF1, cg, NODE_DEATH_RETURN + i, f"death / Exit course -> hub outside door {i}")
    return nodes


def return_spawn_spot(probe, x, y, z, facing_deg, avoid):
    """Stage-local (x, y, floor z, clearance, forward m, side m) for door i's return spawns: on the door
    axis 2.5-6 m out, on a floor from 2 m below (a stoop's steps) to 0.5 m above the door sill, 1 m
    clear around, nothing in the way of the ~3.5 m backwards launch (bhvPainting* warps), and away
    from `avoid` [(x, y, r)] (signs)."""
    f = math.radians(facing_deg)
    nx, ny = math.sin(f), math.cos(f)
    tx, ty = -ny, nx
    best = None
    for a in (2.5, 3.0, 3.5, 4.0, 5.0, 6.0):
        for b in (0.0, 0.8, -0.8, 1.6, -1.6, 2.4, -2.4):
            px, py = x + nx * a + tx * b, y + ny * a + ty * b
            fz = probe.floor(px, py, z + 1.5)
            if fz is None or not (z - 2.0 <= fz <= z + 0.5):
                continue
            if any(math.dist((px, py), (ax, ay)) < r for ax, ay, r in avoid):
                continue
            cl = probe.clearance(px, py, fz + 0.6, 2.0)
            path = min((probe.ray(px, py, fz + h, nx, ny, 4.5) or 4.5) for h in (0.4, 1.2, 2.0))
            landing = [probe.floor(px + nx * d, py + ny * d, fz + 1.5) for d in (1.5, 3.0, 4.5)]
            land_ok = all(lz is not None and abs(lz - fz) < 1.2 for lz in landing)
            if cl >= 1.0 and path >= 4.4 and land_ok:
                return px, py, fz, cl, a, b
            score = min(cl, 1.0) + min(path, 4.5) / 4.5 + (1.0 if land_ok else 0.0)
            if best is None or score > best[0]:
                best = (score, (px, py, fz, cl, a, b))
    if best is not None:
        print(f"SGL WARNING: return spawn at door ({x:.1f}, {y:.1f}): no fully clear spot, using the best one "
              f"({best[1][4]} m out, {best[1][5]} m aside, clearance {best[1][3]:.1f} m)")
        return best[1]
    return None


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


def add_common0_models(level_dir):
    """JUMP_LINK(script_func_global_1) right after MARIO(...) in the level script: loads the vanilla
    common0 model group (MODEL_HEART, MODEL_GOOMBA, MODEL_PURPLE_SWITCH, ...) into the level pool, as every
    vanilla course does (DynOS knows script_func_global_1). Idempotent. -> True when the line is there."""
    path = os.path.join(level_dir, "script.c")
    src = open(path).read()
    line = "\tJUMP_LINK(script_func_global_1),"
    if line.strip() in src:
        return True
    marker = "MARIO(MODEL_MARIO, 0x00000001, bhvMario),"
    i = src.find(marker)
    if i < 0:
        print("SGL WARNING: script.c has no MARIO(...) line; common0 models not loaded")
        return False
    i += len(marker)
    open(path, "w").write(src[:i] + "\n" + line + src[i:])
    return True


def lua_far_units():
    """SGL_FAR_UNITS (formerly SGL_HUB_FAR_UNITS) from mods/sgl64/levels.lua (None if missing)."""
    import re
    try:
        src = open(os.path.join(ROOT, "mods", "sgl64", "levels.lua")).read()
    except OSError:
        return None
    m = re.search(r"SGL_(?:HUB_)?FAR_UNITS\s*=\s*(\d+)", src)
    return int(m.group(1)) if m and "set_override_far" in src else None


def main():
    opts = parse_args()
    key = opts["key"]
    slot = opts["slot"]                       # None = custom level (--custom)
    level = slot or f"sgl_{key}"              # level folder + level_<level>_entry
    is_hub = key == "hub"
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

    look = STAGE_LOOK.get(key, {})
    fog_rgb = tuple(look.get("fog_color", FOG_COLOR_SRGB))
    root = L.make_level(f"{level} Level Root", background=look.get("background", BACKGROUND))
    area = L.make_area(root, 1, music=look.get("music", MUSIC), terrain=look.get("terrain", "TERRAIN_GRASS"),
                       camera="CAMERA_MODE_FREE_ROAM", clip=(NEAR_CLIP, FAR_CLIP))
    area.fast64.sm64.area.set_fog = True
    lin = tuple(stage_materials._srgb_to_linear(c / 255.0) for c in fog_rgb)
    area.area_fog_color = (*lin, 1.0)
    area.area_fog_position = (990, 1000)  # placeholder, replaced by gsSPFogFactor after export
    fm, fo, _ = coop_fog_factor(FOG_START_M, FOG_END_M)

    # warp nodes (flow contract, docs/flow.md): vanilla-slot levels name LEVEL_CASTLE_GROUNDS / the
    # stage levels directly; a --custom level's exits name vanilla Castle Inside nodes (custom level
    # numbers only exist at runtime) and mods/sgl64/levels.lua redirects them to the hub.
    warp_nodes = add_flow_warps(L, area, slot)

    mats = stage_materials.make_materials()
    # extra interior areas (STAGE_INTERIOR_AREAS): their modules + the instant-warp floor materials the landmark's door
    # hookups use, and area 1's INSTANT_WARPs into them
    area_mods = []
    instant_out = []
    if key in STAGE_INTERIOR_AREAS and slot not in (None, HUB_SLOT):
        import build_interior as BI
        for mkey in STAGE_INTERIOR_AREAS[key]:
            amod = BI.load_area_module(mkey)
            area_mods.append(amod)
            mats.update(BI.warp_materials(amod))
            for idx, off in amod.instant_warps():
                L.add_instant_warp(area, idx, amod.AREA, off)
                instant_out.append({"index": idx, "surface": amod.WARP_SURFACE[idx], "to_area": amod.AREA,
                                    "offset_units": list(off)})
    tiles_ = stage_materials.tiles()
    for amod in area_mods:
        for nm in amod.WARP_MAT.values():
            tiles_[nm] = 0.0
    S = Stage(data, area, mats, tiles_, key=key)

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
    if is_hub:   # stage doors + their signs only exist in the hub
        stage_landmarks.doors(S)
    sp = SPAWN.get(key, {"pos": tuple(data["center"]), "facing": 0.0})
    if key not in SPAWN:
        print(f"SGL WARNING: no SPAWN entry for stage {key!r}: spawning at the window centre facing north")
    S.spawn = sp                                              # stage_pickups / stage_points use it
    keep_clear = [(sp["pos"][0], sp["pos"][1], 3.5)]          # map metres: no climbable tree here
    if "sign" in sp:
        keep_clear.append((sp["sign"]["pos"][0], sp["sign"]["pos"][1], 2.5))
    keep_clear += [(d["map_pos"][0], d["map_pos"][1], 7.0) for d in S.doors if d.get("sign")]
    import stage_dressing
    stage_dressing.reserve(S)                                 # trees off the stage dressing's spots (Course 2)
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
    terrain_st = apply_terrain(S, objs)
    if terrain_st is not None:
        S.stats["terrain"] = terrain_st
    uv_span = max(acc.max_uv_span for acc, _, _ in S.accs.values())
    for name, (acc, collision, render) in S.accs.items():
        if render and acc.max_uv_span > G.UV_SPAN_MAX + 1:
            print(f"SGL WARNING: {name}: a face spans {acc.max_uv_span:.1f} texture repeats "
                  f"({getattr(acc, 'max_uv_where', '')}; N64 limit ~{G.UV_SPAN_MAX:.0f} for 64 px textures)")
    # water boxes stop 2 m outside the play zone (a pond cut by the boundary keeps its basin, but its
    # COL_WATER_BOX no longer reaches far past the walls: technical review, hub Dairy / Gator Pond)
    water_out = []
    px0, py0, px1, py1 = S.play_local
    for (x0, y0, x1, y1, surf, bottom, name) in S.water_boxes:
        cx0, cy0, cx1, cy1 = max(x0, px0 - 2.0), max(y0, py0 - 2.0), min(x1, px1 + 2.0), min(y1, py1 + 2.0)
        if cx1 - cx0 < 0.5 or cy1 - cy0 < 0.5:
            print(f"SGL: water box {name} is outside the play zone; skipped")
            continue
        L.add_water_box(area, cx0, cy0, cx1, cy1, surface_z=surf, bottom_z=bottom)
        water_out.append({"name": name, "stage_m": [round(v, 2) for v in (cx0, cy0, cx1, cy1)], "surface_m": surf,
                          "clipped": (cx0, cy0, cx1, cy1) != (x0, y0, x1, y1)})

    # ---- objects: spawn, welcome sign, door signs (checked against the real collision)
    probe = CollisionProbe(objs + S.landmark_objects)
    sx, sy = S.T(sp["pos"])
    spawn_floor = probe.floor(sx, sy, 3.0)
    spawn_clear = probe.clearance(sx, sy, (spawn_floor or 0.0) + 0.6)
    if spawn_floor is None or abs(spawn_floor) > 0.5 or spawn_clear < 1.5:
        print(f"SGL WARNING: spawn at {sp['pos']}: floor {spawn_floor}, clearance {spawn_clear:.1f} m")
    L.add_spawn(area, (sx, sy, (spawn_floor or 0.0) + 1.0), yaw_deg=yaw_for_facing(sp["facing"]))
    spawn_objects = [{"node": "0x%02X" % NODE_SPAWN, "behavior": "bhvSpinAirborneWarp",
                      "game_units": [round(sx * 100), round(((spawn_floor or 0.0) + 1.0) * 100), round(-sy * 100)],
                      "facing_deg": sp["facing"], "note": "spawn + MARIO_POS"}]
    if slot == HUB_SLOT:
        # dying in the hub (0xF1): fall back onto the Plaza next to the spawn (vanilla death exit, -1 life)
        dx, dy = sx + 1.5, sy
        dz = probe.floor(dx, dy, 3.0)
        if dz is None or abs(dz - (spawn_floor or 0.0)) > 0.5:
            dx, dy, dz = sx, sy, spawn_floor or 0.0
        L.add_object(area, "Spawn 0B death", (dx, dy, dz + 1.0), "bhvDeathWarp", "MODEL_NONE",
                     "0x00%02X0000" % NODE_HUB_DEATH, yaw_for_facing(sp["facing"]))
        spawn_objects.append({"node": "0x%02X" % NODE_HUB_DEATH, "behavior": "bhvDeathWarp",
                              "game_units": [round(dx * 100), round((dz + 1.0) * 100), round(-dy * 100)],
                              "facing_deg": sp["facing"], "note": "death in the hub"})
    # ---- level-script stars of this stage (STAGE_STARS; docs/flow.md 5)
    stars_out = []
    for st in STAGE_STARS.get(key, []) if slot not in (None, HUB_SLOT) else []:
        act = int(st["act"])
        pos = st.get("pos")
        if pos is None:
            e = next((e for e in S.landmark_entries if e["slug"] == st.get("landmark")), None)
            pos = (e or {}).get("spots", {}).get(st.get("spot"))
        if pos is None:
            print(f"SGL WARNING: star act {act}: spot {st.get('landmark')}/{st.get('spot')} not found; star skipped")
            continue
        tx, ty = S.T(pos[:2])
        zh = float(pos[2]) if len(pos) > 2 else 0.0
        fz = probe.floor(tx, ty, zh + 1.5)
        if fz is None or abs(fz - zh) > 1.0:
            print(f"SGL WARNING: star act {act} ({st.get('name')}): floor {fz} at the design height {zh} m")
        z = (fz if fz is not None else zh) + STAR_UP_M
        bp = "0x%02X000000" % (act - 1)
        L.add_object(area, f"Star act {act}", (tx, ty, z), "bhvStar", "MODEL_STAR", bp, 0.0, acts=[act])
        stars_out.append({"act": act, "star_id": act - 1, "name": st.get("name"), "behavior": "bhvStar",
                          "bparams": bp, "acts": [act], "map_m": [round(pos[0], 2), round(pos[1], 2), round(z, 2)],
                          "game_units": [round(tx * 100), round(z * 100), round(-ty * 100)],
                          "floor_m": None if fz is None else round(fz, 2)})
    # ---- coins, hearts, 1-ups, Goombas, poles of this stage (stage_pickups.py)
    pickups_out = None
    if key in STAGE_PICKUPS and (slot not in (None, HUB_SLOT) or key == "hub"):
        import stage_pickups
        items, skipped = STAGE_PICKUPS[key](stage_pickups)(S, probe)
        for it in items:
            L.add_object(area, it["name"], it["stage"], it["behavior"], it["model"], it["bparams"],
                         yaw_for_facing(it["facing_deg"]), acts=it.get("acts"))
        pickups_out = stage_pickups.summary(items, skipped)
        S.stage_pickups = pickups_out
        print(f"SGL: {pickups_out['objects']} pickup / enemy / pole objects ({pickups_out['by_kind']}), "
              f"{pickups_out['coins_placed']} coins (+ Goombas: {pickups_out['coins_with_goombas']}), "
              f"{len(skipped)} skipped")
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
            "note": d.get("note"), "width_m": d.get("width_m")})

    # ---- hub stage doors (flow contract): the door trigger object + the two return spawns per door
    flow_doors = []
    if slot == HUB_SLOT:
        signs = [(dd["sign_map_m"][0] - S.cx, dd["sign_map_m"][1] - S.cy, 1.5) for dd in door_out
                 if dd.get("sign_map_m")]
        for i in sorted(HUB_DOORS):
            slug = HUB_DOORS[i]
            st = next(s for s, n in SLOT_DOOR.items() if n == i)
            d = next((dd for dd in S.doors if dd["slug"] == slug and dd.get("stage")), None)
            if d is None:
                print(f"SGL WARNING: hub door {i} ({slug}) not found: its door object is missing and its "
                      "return spawns fall back to the Plaza spawn")
                for base, bhv in ((NODE_STAR_RETURN, STAR_RETURN_BEHAVIOR), (NODE_DEATH_RETURN, DEATH_RETURN_BEHAVIOR)):
                    L.add_object(area, "Spawn %02X fallback" % (base + i), (sx, sy, (spawn_floor or 0.0) + 1.0), bhv,
                                 "MODEL_NONE", "0x00%02X0000" % (base + i), yaw_for_facing(sp["facing"]))
                flow_doors.append({"door": i, "slug": slug, "slot": st, "missing": True})
                continue
            x, y, z = d["map_pos"]
            lx, ly = x - S.cx, y - S.cy
            width = float(d.get("width_m") or 2.4)
            half_dm = max(12, min(30, int(round((width / 2 + DOOR_SIDE_MARGIN_M) * 10))))
            # emblem height: DOOR_EMBLEM_UP_M, or 0.7 m under a porch roof / canopy above the doorway
            f = math.radians(d["facing"])
            ex, ey = lx + math.sin(f) * DOOR_EMBLEM_OUT_M, ly + math.cos(f) * DOOR_EMBLEM_OUT_M
            ceil = probe.ceiling(ex, ey, z + 0.5)
            emblem = DOOR_EMBLEM_UP_M if ceil is None else max(2.4, min(DOOR_EMBLEM_UP_M, ceil - z - 0.7))
            emblem_dm = int(round(emblem * 10))
            bp = (i << 24) | ((NODE_DOOR + i) << 16) | (half_dm << 8) | emblem_dm
            yaw = yaw_for_facing(d["facing"])
            L.add_object(area, f"Door {i} {slug}", (lx, ly, z), DOOR_BEHAVIOR, "MODEL_NONE", "0x%08X" % bp, yaw)
            # return spawns face the door: bhvPainting* warps launch Mario backwards (away from the door);
            # the star exit turns him round to face away from it after the course-done screen
            spot = return_spawn_spot(probe, lx, ly, z, d["facing"], signs)
            if spot is None:
                print(f"SGL WARNING: door {i} ({slug}): no floor in front of the door for its return spawns; "
                      "placing them 3 m out at the sill height")
                f = math.radians(d["facing"])
                spot = (lx + math.sin(f) * 3.0, ly + math.cos(f) * 3.0, z, 0.0, 3.0, 0.0)
            rx, ry, rz, rcl, ra, rb = spot
            ryaw = yaw_for_facing((d["facing"] + 180.0) % 360.0)
            ret = []
            for base, bhv in ((NODE_STAR_RETURN, STAR_RETURN_BEHAVIOR), (NODE_DEATH_RETURN, DEATH_RETURN_BEHAVIOR)):
                L.add_object(area, "Spawn %02X door %d" % (base + i, i), (rx, ry, rz + RETURN_SPAWN_UP_M), bhv,
                             "MODEL_NONE", "0x00%02X0000" % (base + i), ryaw)
                ret.append({"node": "0x%02X" % (base + i), "behavior": bhv,
                            "game_units": [round(rx * 100), round((rz + RETURN_SPAWN_UP_M) * 100), round(-ry * 100)],
                            "game_yaw": int(round(math.radians(ryaw) / (2 * math.pi) * 65536)) & 0xFFFF})
                spawn_objects.append(dict(ret[-1], note=f"return outside door {i} ({slug})"))
            if DOOR_BEHAVIOR not in lua_names:
                lua_names.append(DOOR_BEHAVIOR)
            flow_doors.append({
                "door": i, "slug": slug, "slot": st, "stage_level": SLOT_LEVELS[st], "warp_node": "0x%02X" % (NODE_DOOR + i),
                "door_object": {"behavior": DOOR_BEHAVIOR, "bparams": "0x%08X" % bp,
                                "game_units": [round(lx * 100), round(z * 100), round(-ly * 100)],
                                "game_yaw": int(round(math.radians(yaw) / (2 * math.pi) * 65536)) & 0xFFFF,
                                "trigger_half_width_m": half_dm / 10, "emblem_up_m": emblem_dm / 10,
                                "ceiling_above_m": None if ceil is None else round(ceil - z, 2),
                                "map_m": [round(x, 2), round(y, 2), round(z, 2)],
                                "facing_deg": round(d["facing"], 1)},
                "return_spawns": ret, "return_spot": {"out_m": ra, "aside_m": rb, "clearance_m": round(rcl, 2),
                                                      "floor_m": round(rz, 2)},
                "stars_required_generator": d.get("stars"), "stage_label": d.get("stage")})

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
        "slot": slot, "level_script": f"level_{level}_entry",
        "warp_nodes": warp_nodes, "spawn_objects": spawn_objects, "flow_doors": flow_doors,
        "doors": door_out, "lua_globals_needed": lua_names,
        "landmark_extras": landmark_extras(S),
        "pole_objects": pole_out, "climb_routes": climb, "stars": stars_out,
        "fog": {"start_m": FOG_START_M, "end_m": FOG_END_M, "gsSPFogFactor": [fm, fo], "color_srgb": fog_rgb,
                "far_clip_units": FAR_CLIP, "override_far_units": int(OVERRIDE_FAR_M * 100),
                "lua_far_units": lua_far_units()},
        "water_boxes": water_out,
        "pickups": pickups_out,
        "stats": S.stats,
        "attribution": data["attribution"],
    }
    print(f"SGL: built {level}: {len(objs)} meshes, collision {report['collision_tris']} tris, "
          f"visual {report['visual_tris']} tris ({time.time() - t0:.1f}s)")
    for k in ("collision_by_object",):
        for n, c in sorted(report[k].items(), key=lambda t: -t[1]):
            print(f"   collision {c:6d}  {n}")

    # ---- extra interior areas (after area 1 is complete; one Fast64 export holds every area)
    area_reports, area_built = [], []
    if instant_out:
        report["instant_warps"] = instant_out
    if area_mods and opts["interior"]:
        import build_interior as BI
        for amod in area_mods:
            if getattr(amod, "TEXTURE_SCRIPT", None):
                run_venv(os.path.join(HERE, amod.TEXTURE_SCRIPT), "--textures")
            M2 = amod.build(backdrop=True)
            if "int_carpet" not in mats:
                # interior kit materials WITHOUT pinning the Fast64 world (area 1 exports exactly as before);
                # build_interior.patch_vertex_lit adds the G_LIGHTING clear to the area's vertex-lit lists
                mats.update(stage_materials.make_interior_materials(world_lighting_default=False))
            a2, objs2, probe2, rep2 = BI.build_area(L, root, amod, M2, mats, slot, SLOT_DOOR[slot], SLOT_LEVELS[slot])
            area_reports.append(rep2)
            area_built.append((amod, M2, objs2, probe2))
        report["interior_areas"] = area_reports
    elif area_mods:
        print("SGL: --no-interior: area 1 only (its door hookups stay; the INSTANT_WARPs lead to no area)")

    if opts["blend"]:
        os.makedirs(os.path.dirname(opts["blend"]), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=opts["blend"], copy=True)
        print(f"SGL: saved {opts['blend']}")

    art_dir = os.path.join(ROOT, "art", "levels", STAGE_SHORT_NAMES.get(key, key))
    report_dir = opts["report_dir"] or art_dir
    os.makedirs(report_dir, exist_ok=True)
    if opts["export"]:
        from export_level import export_level
        from validate_level import validate_level
        level_dir, _ = export_level(root.name, level, opts["levels_dir"], setup=False, validate=False)
        n_pos, n_col = patch_fog(level_dir, fm, fo, fog_rgb)
        if area_built:
            import build_interior as BI
            for amod, _, _, _ in area_built:
                n_vl = BI.patch_vertex_lit(level_dir, amod.AREA)
                for r in area_reports:
                    if r["area"] == amod.AREA:
                        r["vertex_lit_material_lists"] = n_vl
        hyg = export_hygiene(level_dir)
        # material geometry modes as differences from the engine state: without a Fast64 world every material
        # exported in full form and its revert cleared G_ZBUFFER, so objects drawn after the level (Mario,
        # NPCs, Goombas, signs) showed through trees and walls (tools/blender/fix_geometry_modes.py)
        from fix_geometry_modes import fix_level as fix_geometry_modes
        hyg["geometry_modes_rewritten"] = fix_geometry_modes(level_dir)
        if key in STAGE_COMMON0_MODELS:
            hyg["common0_jump_link"] = add_common0_models(level_dir)
        report["export_hygiene"] = hyg
        rc = opts["repair_collision"]
        if rc if rc is not None else key in REPAIR_COLLISION_STAGES:
            import glob as _glob
            import stage_collision
            report["collision_repair"] = {}
            for cpath in sorted(_glob.glob(os.path.join(level_dir, "area_*", "collision.inc.c"))):
                r = stage_collision.repair(cpath)
                report["collision_repair"][os.path.basename(os.path.dirname(cpath))] = r
                print(f"SGL: collision seam repair {os.path.relpath(cpath, level_dir)}: {r}")
        if hyg["max_abs_vertex"] > 32767:
            print(f"SGL WARNING: a vertex coordinate is {hyg['max_abs_vertex']} (> s16)")
        lf = lua_far_units()
        if lf != int(OVERRIDE_FAR_M * 100):
            print(f"SGL WARNING: levels.lua SGL_FAR_UNITS = {lf}, the fog is fitted to "
                  f"{int(OVERRIDE_FAR_M * 100)} (set_override_far)")
        rep = validate_level(level_dir)
        print(rep["text"])
        report["validation"] = {"errors": rep["errors"], "warnings": rep["warnings"],
                                "collision_tris": rep.get("collision_tris"), "render_tris": rep.get("render_tris"),
                                "lua_names": rep.get("lua_names"), "fog_patched": [n_pos, n_col]}
        report["level_dir"] = level_dir
        if rep["errors"]:
            json.dump(report, open(os.path.join(report_dir, f"sgl_{key}_build.json"), "w"), indent=1)
            raise RuntimeError(f"{len(rep['errors'])} validation error(s) in {level_dir}")
        print(f"SGL: exported {level_dir} (fog factor {fm}, {fo}; {n_pos} fog commands patched) "
              f"in {time.time() - t0:.1f}s")
    if opts["export"]:
        # one report per stage key (art/levels/hub/sgl_hub_build.json even though the level is castle_grounds)
        json.dump(report, open(os.path.join(report_dir, f"sgl_{key}_build.json"), "w"), indent=1)
    if key in STAGE_POINTS and (opts["export"] or opts["report_dir"]):
        # mission anchor points measured on the built collision (stage_points.py): data/uf/<key>_points.json,
        # or next to the report for a --report-dir test build
        import stage_points
        pts = STAGE_POINTS[key](stage_points)(
            S, probe,
            {"map_m": list(sp["pos"]), "facing_deg": sp["facing"], "game_units": report["spawn"]["game_units"]},
            stars_out, warp_nodes, level, slot)
        pts_path = os.path.join(report_dir if opts["report_dir"] else os.path.join(ROOT, "data", "uf"),
                                f"{STAGE_SHORT_NAMES.get(key, key)}_points.json")
        for amod, M2, objs2, probe2 in area_built:
            # additive: the interior area's anchors (measured on its own collision) under "interior_area_<N>"
            import build_interior as BI
            measured, flags = BI.measure_area_points(amod, M2, probe2)
            rep2 = next(r for r in area_reports if r["area"] == amod.AREA)
            pts[f"interior_area_{amod.AREA}"] = dict(
                {"note": getattr(amod, "POINTS_NOTE", ""), "coordinates": getattr(amod, "POINTS_COORDINATES_MAP_M", ""),
                 "area": amod.AREA, "spawn": rep2["spawn"], "warp_nodes": rep2["warp_nodes"],
                 "instant_warps": rep2["instant_warps"], "warp_strips": rep2["warp_strips"], "pads": rep2["pads"],
                 "pickups": rep2["pickups"], "checks": flags}, **measured)
            pts.setdefault("instant_warps_area_1", report.get("instant_warps", []))
        stage_points.write(pts_path, pts)
        print(f"SGL: wrote {pts_path} ({len(pts.get('checks', []))} point checks flagged)")
        for c in pts.get("checks", []):
            print(f"   points check: {c}")

    if opts["previews"]:
        for _, _, objs2, _ in area_built:          # the interior areas share area 1's frame: keep them out of its views
            for ob in objs2:
                ob.hide_render = True
                ob.hide_set(True)
        import stage_preview
        pv = opts["previews_dir"] or os.path.join(art_dir, "previews")
        paths = stage_preview.render_all(S, pv, fog=(FOG_START_M, FOG_END_M, fog_rgb),
                                         fog_params=coop_fog_factor(FOG_START_M, FOG_END_M),
                                         far_m=OVERRIDE_FAR_M)
        top = next((p for p in paths if p.endswith("_topdown.png")), None)
        if top:
            run_venv(os.path.join(HERE, "compare_map.py"), key, top, os.path.join(pv, f"{key}_map_compare.png"))
    if opts["export"] and not opts["report_dir"] and os.path.abspath(opts["levels_dir"]) == os.path.join(ROOT, "mods", "sgl64", "levels"):
        run_venv(os.path.join(ROOT, "tools", "npcs", "rebuild.py"))
    print(f"SGL: done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        print(f"SGL ERROR: {e}")
        sys.exit(1)
