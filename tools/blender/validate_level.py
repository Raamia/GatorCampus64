"""Static check of a Fast64 level export against what coopdx v1.5.1's DynOS level compiler
accepts (pure Python, no Blender needed).

Usage: python3 tools/blender/validate_level.py <levels_dir>/<level_name>

DynOS (data/dynos_bin_lvl.cpp, dynos_bin_read.cpp, ...) reads every *.c file under
levels/<name>/, keeps declarations of known types, and compiles every LevelScript whose
name contains "_entry" into levels/level_<name>_entry.lvl. Checks here:
  - layout: script.c defines level_<name>_entry; only DynOS-readable declarations
    (no structs/functions/#define in *.c), no CUSTOM_CMD
  - every macro in level scripts / geo layouts / collision / display lists / macro
    objects is one the DynOS parser knows (tables below, from the v1.5.1 sources)
  - collision: surface types DynOS knows, COL_* counts match, vertices in s16 range,
    no COL_TRI with force surfaces; triangle budget (SURFACE_POOL_SIZE = 16384 incl.
    dynamic objects)
  - level script: every AREA has TERRAIN, a warp-spawn OBJECT with bparam2 = 0x0A
    (warp_to_level() target) and death/success warp nodes 0xF1/0xF0; MARIO_POS and
    CALL(0, lvl_init_or_update) present
  - names DynOS will resolve as Lua globals at level load (OBJECT_EXT_LUA_PARAMS) are
    listed, because a typo there only fails in game
Prints a report and exits non-zero on errors.
"""
import os
import re
import sys

# ---- DynOS v1.5.1 symbol tables -------------------------------------------------
LVL_SYMBOLS = set("""
EXECUTE EXIT_AND_EXECUTE EXIT SLEEP SLEEP_BEFORE_EXIT JUMP JUMP_LINK RETURN JUMP_LINK_PUSH_ARG
JUMP_N_TIMES LOOP_BEGIN LOOP_UNTIL JUMP_IF SKIP_IF SKIP SKIP_NOP JUMP_AREA_EXT CALL CALL_LOOP SET_REG
PUSH_POOL POP_POOL FIXED_LOAD LOAD_RAW LOAD_MIO0 LOAD_YAY0 LOAD_MARIO_HEAD LOAD_MIO0_TEXTURE
LOAD_YAY0_TEXTURE INIT_LEVEL CLEAR_LEVEL ALLOC_LEVEL_POOL FREE_LEVEL_POOL AREA END_AREA
LOAD_MODEL_FROM_DL CMD23 MARIO INSTANT_WARP LOAD_AREA CMD2A MARIO_POS CMD2C CMD2D TERRAIN ROOMS
TERRAIN_TYPE NOP TRANSITION BLACKOUT GAMMA SET_BACKGROUND_MUSIC SET_MENU_MUSIC STOP_MUSIC
MACRO_OBJECTS CMD3A WHIRLPOOL GET_OR_SET ADV_DEMO CLEAR_DEMO_PTR SHOW_DIALOG OBJECT OBJECT_WITH_ACTS
LOAD_MODEL_FROM_GEO JUMP_AREA WARP_NODE PAINTING_WARP_NODE
""".split())
GEO_SYMBOLS = set("""
GEO_BRANCH_AND_LINK GEO_END GEO_BRANCH GEO_RETURN GEO_NODE_SCREEN_AREA GEO_NODE_ORTHO GEO_CAMERA_FRUSTUM
GEO_CAMERA_FRUSTUM_WITH_FUNC GEO_NODE_START GEO_ZBUFFER GEO_RENDER_RANGE GEO_CAMERA GEO_TRANSLATE_ROTATE
GEO_TRANSLATE_ROTATE_WITH_DL GEO_TRANSLATE GEO_TRANSLATE_WITH_DL GEO_ROTATE GEO_ROTATE_WITH_DL GEO_ROTATE_Y
GEO_ROTATE_Y_WITH_DL GEO_TRANSLATE_NODE GEO_TRANSLATE_NODE_WITH_DL GEO_ROTATION_NODE GEO_ROTATION_NODE_WITH_DL
GEO_ANIMATED_PART GEO_BILLBOARD_WITH_PARAMS GEO_BILLBOARD_WITH_PARAMS_AND_DL GEO_BILLBOARD GEO_DISPLAY_LIST
GEO_SHADOW GEO_RENDER_OBJ GEO_BACKGROUND_COLOR GEO_NOP_1A GEO_HELD_OBJECT GEO_SCALE GEO_SCALE_WITH_DL
GEO_SCALE_XYZ GEO_SCALE_XYZ_WITH_DL GEO_NOP_1E GEO_NOP_1F GEO_CULLING_RADIUS GEO_BONE GEO_BONE_WITH_SCALE
GEO_ASM GEO_SWITCH_CASE GEO_OPEN_NODE GEO_CLOSE_NODE GEO_BACKGROUND
""".split())
COL_SYMBOLS = set("""
COL_INIT COL_VERTEX_INIT COL_VERTEX COL_TRI_INIT COL_TRI COL_TRI_SPECIAL COL_TRI_STOP COL_END
COL_SPECIAL_INIT COL_WATER_BOX_INIT COL_WATER_BOX SPECIAL_OBJECT SPECIAL_OBJECT_WITH_YAW
SPECIAL_OBJECT_WITH_YAW_AND_PARAM
""".split())
MACRO_SYMBOLS = {"MACRO_OBJECT", "MACRO_OBJECT_WITH_BEH_PARAM", "MACRO_OBJECT_END"}
GFX_SYMBOLS = set("""
gsDPFullSync gsDPLoadBlock gsDPLoadSync gsDPLoadTLUTCmd gsDPLoadTLUT_pal16 gsDPLoadTLUT_pal256
gsDPLoadTextureBlock gsDPLoadTextureBlock_4b gsDPLoadTile gsDPNoOp gsDPNoOpTag gsDPPipeSync
gsDPPipelineMode gsDPSetAlphaCompare gsDPSetAlphaDither gsDPSetBlendColor gsDPSetColorDither
gsDPSetColorImage gsDPSetCombineKey gsDPSetCombineLERP gsDPSetCombineMode gsDPSetCycleType
gsDPSetDepthSource gsDPSetEnvColor gsDPSetEnvRGB gsDPSetFogColor gsDPSetPrimColor gsDPSetPrimDepth
gsDPSetRenderMode gsDPSetTextureConvert gsDPSetTextureDetail gsDPSetTextureFilter gsDPSetTextureImage
gsDPSetTextureLOD gsDPSetTextureLUT gsDPSetTexturePersp gsDPSetTile gsDPSetTileSize gsDPTileSync
gsMoveWd gsSP1Triangle gsSP2Triangles gsSPBranchList gsSPClearGeometryMode gsSPCopyLightEXT
gsSPCopyLightsPlayerPart gsSPCopyPlayerPartToColor gsSPCullDisplayList gsSPDisplayList
gsSPEndDisplayList gsSPFogFactor gsSPFogPosition gsSPFresnel gsSPGeometryMode gsSPGeometryModeSetFirst
gsSPLight gsSPLightColor gsSPLoadGeometryMode gsSPLoadState gsSPMatrix gsSPNoOp gsSPNumLights
gsSPSaveState gsSPSetGeometryMode gsSPSetLights0 gsSPSetLights1 gsSPSetOtherMode gsSPTexture
gsSPVertex gsSPVertexNonGlobal
""".split())
# data/dynos_bin_col.cpp DynOS_Col_ParseConstants (surface types usable in COL_TRI_INIT)
SURFACES = set("""
SURFACE_DEFAULT SURFACE_BURNING SURFACE_RAYCAST SURFACE_0004 SURFACE_HANGABLE SURFACE_SLOW
SURFACE_DEATH_PLANE SURFACE_CLOSE_CAMERA SURFACE_WATER SURFACE_FLOWING_WATER SURFACE_INTANGIBLE
SURFACE_VERY_SLIPPERY SURFACE_SLIPPERY SURFACE_NOT_SLIPPERY SURFACE_TTM_VINES SURFACE_MGR_MUSIC
SURFACE_INSTANT_WARP_1B SURFACE_INSTANT_WARP_1C SURFACE_INSTANT_WARP_1D SURFACE_INSTANT_WARP_1E
SURFACE_SHALLOW_QUICKSAND SURFACE_DEEP_QUICKSAND SURFACE_INSTANT_QUICKSAND SURFACE_DEEP_MOVING_QUICKSAND
SURFACE_SHALLOW_MOVING_QUICKSAND SURFACE_QUICKSAND SURFACE_MOVING_QUICKSAND SURFACE_WALL_MISC
SURFACE_NOISE_DEFAULT SURFACE_NOISE_SLIPPERY SURFACE_HORIZONTAL_WIND SURFACE_INSTANT_MOVING_QUICKSAND
SURFACE_ICE SURFACE_LOOK_UP_WARP SURFACE_HARD SURFACE_WARP SURFACE_TIMER_START SURFACE_TIMER_END
SURFACE_HARD_SLIPPERY SURFACE_HARD_VERY_SLIPPERY SURFACE_HARD_NOT_SLIPPERY SURFACE_VERTICAL_WIND
SURFACE_BOSS_FIGHT_CAMERA SURFACE_CAMERA_FREE_ROAM SURFACE_THI3_WALLKICK SURFACE_CAMERA_8_DIR
SURFACE_CAMERA_MIDDLE SURFACE_CAMERA_ROTATE_RIGHT SURFACE_CAMERA_ROTATE_LEFT SURFACE_CAMERA_BOUNDARY
SURFACE_NOISE_VERY_SLIPPERY_73 SURFACE_NOISE_VERY_SLIPPERY_74 SURFACE_NOISE_VERY_SLIPPERY
SURFACE_NO_CAM_COLLISION SURFACE_NO_CAM_COLLISION_77 SURFACE_NO_CAM_COL_VERY_SLIPPERY
SURFACE_NO_CAM_COL_SLIPPERY SURFACE_SWITCH SURFACE_VANISH_CAP_WALLS SURFACE_WOBBLING_WARP SURFACE_TRAPDOOR
""".split()) | {f"SURFACE_PAINTING_WOBBLE_{x:02X}" for x in range(0xA6, 0xD3)} \
    | {f"SURFACE_PAINTING_WARP_{x:02X}" for x in range(0xD3, 0xFD)} \
    | {"SURFACE_TTC_PAINTING_1", "SURFACE_TTC_PAINTING_2", "SURFACE_TTC_PAINTING_3"}
# surface_has_force(): these need COL_TRI_SPECIAL (a force parameter)
FORCE_SURFACES = {"SURFACE_0004", "SURFACE_FLOWING_WATER", "SURFACE_DEEP_MOVING_QUICKSAND",
                  "SURFACE_SHALLOW_MOVING_QUICKSAND", "SURFACE_MOVING_QUICKSAND", "SURFACE_HORIZONTAL_WIND",
                  "SURFACE_INSTANT_MOVING_QUICKSAND"}
# src/game/area.c sWarpBhvSpawnTable: OBJECTs DynOS indexes as warp spawns
WARP_SPAWN_BEHAVIORS = {
    "bhvDoorWarp", "bhvStar", "bhvExitPodiumWarp", "bhvWarp", "bhvWarpPipe", "bhvFadingWarp",
    "bhvInstantActiveWarp", "bhvAirborneWarp", "bhvHardAirKnockBackWarp", "bhvSpinAirborneCircleWarp",
    "bhvDeathWarp", "bhvSpinAirborneWarp", "bhvFlyingWarp", "bhvSwimmingWarp", "bhvPaintingStarCollectWarp",
    "bhvPaintingDeathWarp", "bhvAirborneStarCollectWarp", "bhvAirborneDeathWarp", "bhvLaunchStarCollectWarp",
    "bhvLaunchDeathWarp"}
# declaration types DynOS_Read_Source understands (anything else is "Unknown type name")
DYNOS_TYPES = {"Lights0", "Lights1", "Light_t", "Ambient_t", "u8", "Texture", "Vtx", "Gfx", "GeoLayout",
               "Collision", "LevelScript", "MacroObject", "Trajectory", "Movtex", "MovtexQuadCollection",
               "BehaviorScript", "u64"}
DYNOS_IGNORED_WORDS = {"static", "const", "inline", "include", "ALIGNED8", "UNUSED", "struct"}

SURFACE_POOL_SIZE = 0x4000      # coopdx v1.5.1 static + dynamic collision triangles
LEVEL_COORD_LIMIT = 32767       # EXTENDED_BOUNDS_MODE 3 level boundary (s16 vertices)
MAX_MOD_SIZE = 35 * 1048576     # src/pc/mods/mods.h: a mod >= 35 MB of .lua/.bin/.lvl/... is disabled


SYMBOLS_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dynos_symbols_v1.5.1.json")
_NUM = re.compile(r"[-+]?(0[xX][0-9a-fA-F]+|\d+\.?\d*(?:[eE][-+]?\d+)?[fF]?|\.\d+[fF]?)$")
# macros whose args DynOS skips without parsing (lvl_symbol_noop_3)
NOOP_LVL = {"LOAD_RAW", "LOAD_MIO0", "LOAD_YAY0", "LOAD_MIO0_TEXTURE", "LOAD_YAY0_TEXTURE"}
# level commands whose args may name Lua globals of the mod (DynOS_Lua_RememberVariable)
LUA_OK_LVL = {"OBJECT", "OBJECT_WITH_ACTS", "SHOW_DIALOG", "LOAD_MODEL_FROM_GEO"}


def load_symbols():
    """DynOS name tables (dynos_symbols_v1.5.1.json, from gen_dynos_symbols.py), or None."""
    if not os.path.exists(SYMBOLS_JSON):
        return None
    import json
    with open(SYMBOLS_JSON) as f:
        d = json.load(f)
    common = set(d["builtin_functions"]) | set(d["builtin_names"]) | {"NULL", "TRUE", "FALSE"}
    return {
        "lvl": set(d["lvl_constants"]) | set(d["bhv_constants"]) | common,
        "geo": set(d["geo_constants"]) | common,
        "gfx": set(d["gfx_constants"]) | common,
        "col": set(d["col_constants"]),
        "macro": set(d["macro_constants"]),
    }


def unresolved_names(arg, known, decls):
    """Identifiers in one macro argument that DynOS cannot resolve (number, expression of
    constants, declared data, `name + offset`, lights `.a/.l`)."""
    a = arg.strip()
    if not a or _NUM.match(a) or a in known or a in decls:
        return []
    m = re.fullmatch(r"(\w+)\s*\+\s*(0x[0-9a-fA-F]+|\d+)", a)  # vtx_0 + 15
    if m and (m.group(1) in decls or m.group(1) in known):
        return []
    m = re.fullmatch(r"&?(\w+)\.(a|l)(\[0\])?", a)  # lights.a / lights.l[0]
    if m and m.group(1) in decls:
        return []
    bad = []
    for tok in re.findall(r"[A-Za-z_]\w*", a):
        if tok in known or tok in decls or re.fullmatch(r"0x[0-9a-fA-F]+", tok):
            continue
        bad.append(tok)
    return bad


def strip_comments(text):
    return re.sub(r"//[^\n]*|/\*.*?\*/", "", text, flags=re.S)


def declarations(text):
    """Yield (type, name, body) of top-level `TYPE name[...] = { body };` declarations, and
    ('?', line, '') for any other top-level statement DynOS would choke on."""
    lines = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#include") or s.startswith("extern "):
            continue
        lines.append(line)
    text = "\n".join(lines)
    for stmt in re.split(r";", text):
        s = stmt.strip()
        if not s:
            continue
        m = re.match(r"((?:\w+\s+)*?)(\w+)\s*\*?\s*(\w+)\s*(\[[^\]]*\])*\s*=\s*(.*)$", s, re.S)
        if m:
            words = m.group(1).split()
            yield (m.group(2), m.group(3), m.group(5), words)
        else:
            yield ("?", s.splitlines()[0][:80], "", [])


def macros(body):
    """Top-level NAME(args) entries of an initializer body, as (name, [args])."""
    out = []
    i, n = 0, len(body)
    while i < n:
        m = re.compile(r"\s*,?\s*([A-Za-z_]\w*)\s*\(").match(body, i)
        if not m:
            i += 1
            continue
        name = m.group(1)
        j = m.end()
        depth, start = 1, j
        while j < n and depth:
            if body[j] == "(":
                depth += 1
            elif body[j] == ")":
                depth -= 1
            j += 1
        args = split_args(body[start:j - 1])
        out.append((name, args))
        i = j
    return out


def split_args(s):
    args, depth, cur = [], 0, ""
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            args.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        args.append(cur.strip())
    return args


def to_int(s):
    s = s.strip()
    try:
        return int(s, 0)
    except ValueError:
        return None


def validate_level(level_dir):
    level_dir = os.path.abspath(level_dir)
    name = os.path.basename(level_dir.rstrip("/"))
    errors, warnings, info = [], [], []
    entry = f"level_{name}_entry"

    if not os.path.isfile(os.path.join(level_dir, "script.c")):
        errors.append(f"missing {level_dir}/script.c (DynOS only compiles folders with a script.c)")
        return _finish(name, errors, warnings, info)

    decls = {}  # name -> (type, body, file)
    c_files = []
    for root, _, files in os.walk(level_dir):
        for f in sorted(files):
            if not f.endswith(".c"):
                continue
            path = os.path.join(root, f)
            rel = os.path.relpath(path, level_dir)
            c_files.append(rel)
            raw = open(path, encoding="utf-8", errors="replace").read()
            if "CUSTOM_CMD" in raw:
                errors.append(f"{rel}: contains CUSTOM_CMD (an un-migrated Fast64 custom command)")
            n_zclear = len(re.findall(r"gsSPClearGeometryMode\([^)]*\bG_ZBUFFER\b", raw))
            if n_zclear:
                errors.append(f"{rel}: {n_zclear} display list(s) clear G_ZBUFFER, so every object drawn after the "
                              f"level shows through walls (run tools/blender/fix_geometry_modes.py on the level)")
            text = strip_comments(raw)
            for line in text.splitlines():
                s = line.strip()
                if s.startswith("#") and not s.startswith("#include"):
                    errors.append(f"{rel}: preprocessor line DynOS does not understand: {s[:60]}")
            for typ, dname, body, words in declarations(text):
                if typ == "?":
                    errors.append(f"{rel}: statement DynOS cannot parse: {dname}")
                    continue
                if typ not in DYNOS_TYPES:
                    errors.append(f"{rel}: declaration type {typ!r} ({dname}) is unknown to DynOS")
                    continue
                if dname in decls:
                    errors.append(f"{rel}: {dname} declared twice")
                decls[dname] = (typ, body, rel)
    info.append(f"C files read by DynOS: {', '.join(c_files)}")

    by_type = {}
    for dname, (typ, body, rel) in decls.items():
        by_type.setdefault(typ, []).append(dname)

    if entry not in decls or decls[entry][0] != "LevelScript":
        errors.append(f"script.c must define `const LevelScript {entry}[]` (folder name = level name)")
    others = [d for d in by_type.get("LevelScript", []) if "_entry" in d and d != entry]
    if others:
        warnings.append(f"extra *_entry level scripts become their own .lvl files: {others}")

    lua_names = set()
    # ---- level scripts
    areas = {}
    cur_area = None
    script_cmds = []
    for d in by_type.get("LevelScript", []):
        for mname, args in macros(decls[d][1]):
            if mname not in LVL_SYMBOLS:
                errors.append(f"{d}: level script command {mname} is not supported by DynOS")
            script_cmds.append((d, mname, args))
    loaded_models = set(GLOBAL_MODELS)
    for d, mname, args in script_cmds:
        if mname == "JUMP_LINK" and args and args[0].strip() in MODEL_GROUP_SCRIPTS:
            loaded_models |= MODEL_GROUP_SCRIPTS[args[0].strip()]
            info.append(f"model group {args[0].strip()} loaded ({len(MODEL_GROUP_SCRIPTS[args[0].strip()])} models)")
        if mname == "AREA":
            cur_area = to_int(args[0])
            areas[cur_area] = {"geo": args[1], "terrain": None, "warps": {}, "spawns": {}, "objects": 0,
                               "object_list": []}
            if args[1] not in decls:
                errors.append(f"AREA({args[0]}): geo layout {args[1]} not found")
        elif mname == "END_AREA":
            cur_area = None
        elif cur_area is not None and mname == "TERRAIN":
            areas[cur_area]["terrain"] = args[0]
            if args[0] not in decls:
                errors.append(f"area {cur_area}: collision {args[0]} not found")
        elif cur_area is not None and mname in ("WARP_NODE", "PAINTING_WARP_NODE"):
            wid = to_int(args[0])
            areas[cur_area]["warps"][wid] = args[1:]
            if not args[1].startswith("LEVEL_") and to_int(args[1]) is None:
                errors.append(f"area {cur_area}: {mname}({args[0]}) dest level {args[1]} is a Lua name; "
                              "coopdx v1.5.1 does not resolve it at runtime - use a LEVEL_* constant + Lua warps")
        elif cur_area is not None and mname in ("OBJECT", "OBJECT_WITH_ACTS"):
            areas[cur_area]["objects"] += 1
            model, bparam, bhv = args[0], args[7], args[8]
            areas[cur_area]["object_list"].append({"cmd": mname, "model": model, "bhv": bhv, "bparam": bparam,
                                                   "pos": args[1:4], "yaw": args[5],
                                                   "acts": args[9] if len(args) > 9 else "ALL"})
            for a in (model, bhv, bparam):
                if not _known_symbol(a):
                    lua_names.add(a)
            if bhv in WARP_SPAWN_BEHAVIORS:
                bp = to_int(bparam)
                if bp is not None:
                    areas[cur_area]["spawns"][(bp >> 16) & 0xFF] = (bhv, args[1:4])
            if model.startswith("MODEL_") and model != "MODEL_NONE" and model not in loaded_models:
                warnings.append(f"area {cur_area}: {model} is not a globally loaded model; it only shows if this "
                                "level loads it (or use the Lua E_MODEL_* name, loaded on demand)")
        elif mname == "SHOW_DIALOG":
            for a in args:
                if not _known_symbol(a):
                    lua_names.add(a)
    cmd_names = [c[1] for c in script_cmds]
    if "MARIO_POS" not in cmd_names:
        errors.append("no MARIO_POS (add a Fast64 'Mario Start' empty)")
    if not any(c[1] == "CALL" and c[2][1:] == ["lvl_init_or_update"] for c in script_cmds):
        errors.append("no CALL(0, lvl_init_or_update) (DynOS warps detect level init by it)")
    if not areas:
        errors.append("level script has no AREA")
    for idx, a in sorted(areas.items()):
        if a["terrain"] is None:
            errors.append(f"area {idx}: no TERRAIN (collision)")
        if 0x0A not in a["spawns"]:
            msg = (f"area {idx}: no warp-spawn OBJECT with bparam2 0x0A "
                   "(warp_to_level(level, %d, act) needs it; e.g. bhvSpinAirborneWarp, bparams 0x000A0000)" % idx)
            (errors if idx == 1 else warnings).append(msg)
        for wid in (0x0A, 0xF0, 0xF1):
            if wid not in a["warps"]:
                (errors if wid == 0xF1 else warnings).append(
                    f"area {idx}: no WARP_NODE 0x{wid:02X}" + (" (death warp; without it a death sends "
                                                              "everyone to gLevelValues.entryLevel)" if wid == 0xF1 else ""))
        info.append(f"area {idx}: geo {a['geo']}, collision {a['terrain']}, {a['objects']} objects, "
                    f"warp nodes {sorted('0x%02X' % w for w in a['warps'])}, "
                    f"spawn warps {sorted('0x%02X' % w for w in a['spawns'])}")
    # ---- Super Gatorlator 64 flow contract (docs/flow.md) for vanilla-slot level folders
    check_flow_contract(name, areas, errors, warnings, info)

    # ---- geo layouts
    for d in by_type.get("GeoLayout", []):
        for mname, args in macros(decls[d][1]):
            if mname not in GEO_SYMBOLS:
                errors.append(f"{d}: geo command {mname} is not supported by DynOS")
            if mname == "GEO_CAMERA_FRUSTUM_WITH_FUNC":
                far = to_int(args[2])
                info.append(f"{d}: camera fov {args[0]}, near {args[1]}, far {args[2]} units"
                            + (f" (~{far / 100:.0f} m)" if far else ""))

    # ---- collision
    area_tris = []
    total_tris = 0
    for d in by_type.get("Collision", []):
        cmds = macros(decls[d][1])
        n_vert = n_tri = 0
        declared_v = declared_t = None
        surf = None
        water = 0
        cur_surfaces = {}
        for mname, args in cmds:
            if mname not in COL_SYMBOLS:
                errors.append(f"{d}: collision command {mname} is not supported by DynOS")
                continue
            if mname == "COL_VERTEX_INIT":
                declared_v = to_int(args[0])
            elif mname == "COL_VERTEX":
                n_vert += 1
                for a in args:
                    v = to_int(a)
                    if v is None or abs(v) > LEVEL_COORD_LIMIT:
                        errors.append(f"{d}: vertex coordinate {a} outside s16 / level bounds")
            elif mname == "COL_TRI_INIT":
                surf = args[0]
                declared_t = to_int(args[1])
                cur_surfaces[surf] = cur_surfaces.get(surf, 0) + (declared_t or 0)
                if surf not in SURFACES and to_int(surf) is None:
                    errors.append(f"{d}: surface type {surf} unknown to DynOS")
            elif mname in ("COL_TRI", "COL_TRI_SPECIAL"):
                n_tri += 1
                if mname == "COL_TRI" and surf in FORCE_SURFACES:
                    errors.append(f"{d}: {surf} needs COL_TRI_SPECIAL (force parameter)")
                for a in args[:3]:
                    v = to_int(a)
                    if v is None or (declared_v is not None and not 0 <= v < declared_v):
                        errors.append(f"{d}: triangle vertex index {a} out of range")
            elif mname == "COL_WATER_BOX":
                water += 1
        if declared_v is not None and declared_v != n_vert:
            errors.append(f"{d}: COL_VERTEX_INIT({declared_v}) but {n_vert} vertices")
        if not cmds or cmds[-1][0] != "COL_END":
            errors.append(f"{d}: does not end with COL_END()")
        total_tris += n_tri
        area_tris.append(n_tri)
        info.append(f"{d}: {n_vert} vertices, {n_tri} triangles, {water} water boxes, surfaces "
                    + ", ".join(f"{k}={v}" for k, v in cur_surfaces.items()))
    # the pool holds the CURRENT area's static triangles (load_area_terrain clears it on every area change), so the
    # budget applies per area; a one-area level checks its total exactly as before
    pool_tris = max(area_tris) if area_tris else 0
    if pool_tris > SURFACE_POOL_SIZE * 0.75:
        (errors if pool_tris > SURFACE_POOL_SIZE else warnings).append(
            f"{pool_tris} static collision triangles"
            + (f" in the largest area ({total_tris} in {len(area_tris)} areas)" if len(area_tris) > 1 else "")
            + f" vs SURFACE_POOL_SIZE {SURFACE_POOL_SIZE} (objects need room too; keep levels well under ~12k)")

    # ---- display lists / macro objects
    gfx_tris = 0
    for d in by_type.get("Gfx", []):
        for mname, args in macros(decls[d][1]):
            if mname not in GFX_SYMBOLS:
                errors.append(f"{d}: display list command {mname} is not supported by DynOS")
            elif mname == "gsSP1Triangle":
                gfx_tris += 1
            elif mname == "gsSP2Triangles":
                gfx_tris += 2
    for d in by_type.get("MacroObject", []):
        for mname, args in macros(decls[d][1]):
            if mname not in MACRO_SYMBOLS:
                errors.append(f"{d}: macro object command {mname} is not supported by DynOS")
    # ---- every macro argument resolvable by DynOS (else: "Unknown ... arg" at compile time)
    syms = load_symbols()
    if syms is None:
        warnings.append(f"{SYMBOLS_JSON} missing: macro arguments not checked")
    else:
        checked = 0
        for typ, dom in (("LevelScript", "lvl"), ("GeoLayout", "geo"), ("Gfx", "gfx"), ("Collision", "col"),
                         ("MacroObject", "macro")):
            for d in by_type.get(typ, []):
                for mname, args in macros(decls[d][1]):
                    if dom == "lvl" and mname in NOOP_LVL:
                        continue
                    for k, a in enumerate(args):
                        checked += 1
                        known = syms[dom]
                        if mname == "gsDPSetCombineLERP":
                            pre = "G_ACMUX_" if (k % 8) >= 4 else "G_CCMUX_"
                            if pre + a.strip() in known:
                                continue
                        bad = unresolved_names(a, known, decls)
                        if not bad:
                            continue
                        if dom == "lvl" and mname in LUA_OK_LVL:
                            continue  # Lua global (listed above)
                        if dom == "lvl" and mname in ("WARP_NODE", "PAINTING_WARP_NODE") and k == 1:
                            continue  # reported above
                        errors.append(f"{d}: {mname} argument {a!r}: DynOS cannot resolve {', '.join(bad)}")
        info.append(f"{checked} macro arguments checked against the DynOS v1.5.1 symbol tables")
    vtx = sum(len(re.findall(r"\{\s*\{\s*\{", decls[d][1])) for d in by_type.get("Vtx", []))
    tex_bytes = sum(len(re.findall(r"0x[0-9a-fA-F]{2}\b", decls[d][1])) for d in by_type.get("u8", []))
    info.append(f"render: {gfx_tris} triangles, {vtx} vertices, {len(by_type.get('Gfx', []))} display lists, "
                f"{len(by_type.get('u8', []))} textures ({tex_bytes / 1024:.1f} KiB raw)")
    if lua_names:
        info.append("resolved as Lua globals of the mod at level load (must exist, or the object is skipped): "
                    + ", ".join(sorted(lua_names)))
        check_lua_globals(level_dir, lua_names, warnings, info)
    return _finish(name, errors, warnings, info, lua_names=sorted(lua_names), collision_tris=total_tris,
                   render_tris=gfx_tris)


# models loaded by level_main_scripts_entry (permanent pool): usable from any level script
GLOBAL_MODELS = set("""
MODEL_MARIO MODEL_SMOKE MODEL_SPARKLES MODEL_BUBBLE MODEL_SMALL_WATER_SPLASH MODEL_IDLE_WATER_WAVE
MODEL_WATER_SPLASH MODEL_WAVE_TRAIL MODEL_YELLOW_COIN MODEL_STAR MODEL_TRANSPARENT_STAR
MODEL_WOODEN_SIGNPOST MODEL_WHITE_PARTICLE_SMALL MODEL_RED_FLAME MODEL_BLUE_FLAME MODEL_BURN_SMOKE
MODEL_LEAVES MODEL_PURPLE_MARBLE MODEL_FISH MODEL_FISH_SHADOW MODEL_SPARKLES_ANIMATION MODEL_SAND_DUST
MODEL_BUTTERFLY MODEL_BURN_SMOKE_UNUSED MODEL_PEBBLE MODEL_MIST MODEL_WHITE_PUFF MODEL_WHITE_PARTICLE_DL
MODEL_WHITE_PARTICLE MODEL_YELLOW_COIN_NO_SHADOW MODEL_BLUE_COIN MODEL_BLUE_COIN_NO_SHADOW
MODEL_MARIOS_WINGED_METAL_CAP MODEL_MARIOS_METAL_CAP MODEL_MARIOS_WING_CAP MODEL_MARIOS_CAP
MODEL_BOWSER_KEY_CUTSCENE MODEL_BOWSER_KEY MODEL_RED_FLAME_SHADOW MODEL_1UP MODEL_RED_COIN
MODEL_RED_COIN_NO_SHADOW MODEL_NUMBER MODEL_EXPLOSION MODEL_DIRT_ANIMATION MODEL_CARTOON_STAR
""".split())

# model groups a level script can load with JUMP_LINK(<script>) (vanilla levels/scripts.c; DynOS knows the
# script_func_global_* names). common0 = script_func_global_1 (every vanilla course links it).
MODEL_GROUP_SCRIPTS = {
    "script_func_global_1": set("""
MODEL_BLUE_COIN_SWITCH MODEL_AMP MODEL_PURPLE_SWITCH MODEL_CHECKERBOARD_PLATFORM MODEL_BREAKABLE_BOX
MODEL_BREAKABLE_BOX_SMALL MODEL_EXCLAMATION_BOX_OUTLINE MODEL_EXCLAMATION_BOX MODEL_GOOMBA MODEL_EXCLAMATION_POINT
MODEL_KOOPA_SHELL MODEL_METAL_BOX MODEL_METAL_BOX_DL MODEL_BLACK_BOBOMB MODEL_BOBOMB_BUDDY MODEL_DL_CANNON_LID
MODEL_BOWLING_BALL MODEL_CANNON_BARREL MODEL_CANNON_BASE MODEL_HEART MODEL_FLYGUY MODEL_CHUCKYA
MODEL_TRAJECTORY_MARKER_BALL
""".split()),
}


# ---- Super Gatorlator 64 flow contract (docs/flow.md, tools/campus/build_stage.py) ----------------
FLOW_HUB = "castle_grounds"
FLOW_SLOT_LEVEL = {"castle_grounds": "LEVEL_CASTLE_GROUNDS", "bob": "LEVEL_BOB", "wf": "LEVEL_WF",
                   "jrb": "LEVEL_JRB", "ccm": "LEVEL_CCM", "bbh": "LEVEL_BBH", "ttc": "LEVEL_TTC"}
FLOW_SLOT_DOOR = {"bob": 1, "wf": 2, "jrb": 3, "ccm": 4, "bbh": 5, "ttc": 6}
FLOW_DOOR_BEHAVIOR = "id_bhvSglDoor"
FLOW_STAR_RETURN = {"bhvPaintingStarCollectWarp", "bhvAirborneStarCollectWarp", "bhvLaunchStarCollectWarp"}
FLOW_DEATH_RETURN = {"bhvPaintingDeathWarp", "bhvAirborneDeathWarp", "bhvLaunchDeathWarp", "bhvDeathWarp"}


def _warp_dest(a, wid):
    """(destLevel, destArea, destNode) of WARP_NODE wid in area dict a, or None."""
    w = a["warps"].get(wid)
    if w is None or len(w) < 3:
        return None
    return w[0].strip(), to_int(w[1]), to_int(w[2])


def check_flow_contract(name, areas, errors, warnings, info):
    """Warp wiring of the hub (castle_grounds) and the stage slots (bob, wf, jrb, ccm, bbh, ttc).
    Only runs for those folder names; other levels (sgl_test, ...) are not affected."""
    if name not in FLOW_SLOT_LEVEL or 1 not in areas:
        return
    a = areas[1]
    cg = FLOW_SLOT_LEVEL[FLOW_HUB]
    bad = []

    def expect(wid, level, node):
        got = _warp_dest(a, wid)
        if got != (level, 1, node):
            bad.append(f"WARP_NODE(0x{wid:02X}) must lead to {level} area 1 node 0x{node:02X}, found {got}")

    if name == FLOW_HUB:
        for i in sorted(FLOW_SLOT_DOOR.values()):
            slot = next(s for s, d in FLOW_SLOT_DOOR.items() if d == i)
            expect(0x10 + i, FLOW_SLOT_LEVEL[slot], 0x0A)
            for base, bhvs, what in ((0x20, FLOW_STAR_RETURN, "star return"), (0x30, FLOW_DEATH_RETURN, "death return")):
                wid = base + i
                if wid not in a["warps"]:
                    bad.append(f"no WARP_NODE(0x{wid:02X}) ({what} of door {i})")
                sp = a["spawns"].get(wid)
                if sp is None:
                    bad.append(f"no spawn object with bparam2 0x{wid:02X} ({what} of door {i})")
                elif sp[0] not in bhvs:
                    warnings.append(f"flow: spawn 0x{wid:02X} uses {sp[0]} (expected one of {sorted(bhvs)})")
            doors = [o for o in a["object_list"] if o["bhv"] == FLOW_DOOR_BEHAVIOR
                     and to_int(o["bparam"]) is not None and (to_int(o["bparam"]) >> 16) & 0xFF == 0x10 + i]
            if len(doors) != 1:
                bad.append(f"expected 1 {FLOW_DOOR_BEHAVIOR} object with bparam2 0x{0x10 + i:02X} (door {i}), "
                           f"found {len(doors)}")
            elif (to_int(doors[0]["bparam"]) >> 24) & 0xFF != i:
                bad.append(f"door object 0x{0x10 + i:02X}: bparam1 must be the door index {i}")
        if 0x0A not in a["spawns"]:
            bad.append("no Plaza spawn 0x0A")
        info.append(f"flow contract (hub): doors 1-{max(FLOW_SLOT_DOOR.values())} -> "
                    + ", ".join(f"0x{0x10 + i:02X}->{_warp_dest(a, 0x10 + i)}" for i in sorted(FLOW_SLOT_DOOR.values())))
    else:
        i = FLOW_SLOT_DOOR[name]
        expect(0x0A, FLOW_SLOT_LEVEL[name], 0x0A)
        expect(0xF0, cg, 0x20 + i)
        expect(0xF1, cg, 0x30 + i)
        stars = [o for o in a["object_list"] if o["bhv"] == "bhvStar"]
        info.append(f"flow contract (stage {name}, door {i}): 0xF0->{_warp_dest(a, 0xF0)}, "
                    f"0xF1->{_warp_dest(a, 0xF1)}; level-script stars: "
                    + (", ".join(f"id {(to_int(o['bparam']) or 0) >> 24} acts {o['acts']}" for o in stars) or "none"))
    for b in bad:
        errors.append("flow: " + b)


def check_lua_globals(level_dir, lua_names, warnings, info):
    """Warn about Lua names the level script uses that no .lua file of the mod assigns (a typo there
    only shows up in game: DynOS skips the object). The mod root is two folders above the level."""
    import glob
    mod_root = os.path.dirname(os.path.dirname(os.path.abspath(level_dir)))
    files = glob.glob(os.path.join(mod_root, "*.lua"))
    if not files:
        return
    src = "\n".join(open(f, encoding="utf-8", errors="replace").read() for f in files)
    missing = []
    for n in sorted(lua_names):
        tok = n.strip()
        if not re.fullmatch(r"[A-Za-z_]\w*", tok):
            continue
        if not re.search(r"(^|[^\w.])" + re.escape(tok) + r"\s*=[^=]", src, re.M):
            missing.append(tok)
    if missing:
        warnings.append(f"Lua globals not assigned in {os.path.basename(mod_root)}/*.lua: {', '.join(missing)}")
    else:
        info.append(f"all {len(lua_names)} Lua names are assigned in {os.path.basename(mod_root)}/*.lua")


def _known_symbol(a):
    """True when DynOS resolves `a` itself (number, vanilla constant/behaviour, expression)."""
    a = a.strip()
    if to_int(a) is not None:
        return True
    if re.fullmatch(r"[\w\s|<>()+\-*&x]+", a) and re.search(r"[|<>()+\-*&]", a):
        return all(_known_symbol(t) for t in re.findall(r"[A-Za-z_]\w*", a) if not t.startswith("0x"))
    return bool(re.match(r"(MODEL_|bhv|DIALOG_|LEVEL_|SEQ_|TERRAIN_|WARP_|NULL$|TRUE$|FALSE$)", a)) \
        and not a.startswith("bhvSgl")


def _finish(name, errors, warnings, info, **extra):
    lines = [f"validate_level {name}: {len(errors)} error(s), {len(warnings)} warning(s)"]
    lines += [f"  ERROR {e}" for e in errors]
    lines += [f"  WARN  {w}" for w in warnings]
    lines += [f"  info  {i}" for i in info]
    return {"name": name, "errors": errors, "warnings": warnings, "info": info, "text": "\n".join(lines), **extra}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python3 validate_level.py <levels_dir>/<level_name>")
    rep = validate_level(sys.argv[1])
    print(rep["text"])
    sys.exit(1 if rep["errors"] else 0)
