#!/bin/sh
# Offline checks for the mods/sgl64 Lua (no game needed):
#   1. luac -p on every mod Lua file (syntax; coopdx runs Lua 5.3-style code, keep 5.4/5.5-only
#      syntax such as <const>/<close>/global out of the mod)
#   2. check_api.lua: unknown functions/constants and wrong argument counts vs sm64coopdx v1.5.1
#   3. check_globals.lua: cross-file globals from the bytecode, in coopdx's load order (strcmp of the
#      file names): every read resolves, load-time reads only use earlier files, no shadowed coopdx
#      names, no global assigned by two files
#   4. test_missions.lua: multi-client simulation of the mission framework + Swamp missions
#   5. test_flow.lua: the whole mod (every file) + the real levels/castle_grounds and levels/bob
#      scripts: doors, warp nodes, return spawns, act select, stars, character select, Study Group
#   6. check_swamp_points.py: SWAMP_POINTS still match data/uf/swamp_points.json (the built Swamp)
#      (skipped when tools/.venv is missing)
#   7. test_reitz_missions.lua: course 2 (wf_reitz_missions.lua): the rooftop climb + window-washer lift,
#      the shared token hunt, the co-op robotics cranes (2-4 players), act select, levels/wf contract
#   8. check_reitz_points.py: REITZ_POINTS vs data/uf/reitz_points.json, and every anchor / crane lane /
#      console against the built levels/wf collision (skipped when tools/.venv is missing)
#   9. test_lake_missions.lua: course 3 (uf_lake_missions.lua): the lily-pad route, the sinking gator line +
#      big gators, the co-op bat census (2-4 players) and its dusk lighting, act select, levels/jrb contract
#  10. check_lake_points.py: LAKE_POINTS vs data/uf/lake_points.json or the lake landmark modules, lake
#      depth / clearance of the gators, and the built levels/jrb collision + water boxes once it exists
#      (skipped when tools/.venv is missing)
#  11. test_marston_missions.lua: course 4 (uf_marston_missions.lua): the atrium climb (stair barriers, book-cart lifts,
#      flying books), the silent floor's textbooks + Shusher patrols (noise, sight, pauses, lures), the co-op study
#      room booking (2-4 kiosks, 4 s window, count-in), act select, levels/ccm contract once built
#  12. check_marston_points.py: MARSTON_POINTS vs data/uf/marston_points.json or data/uf/marston_layout.json (layout
#      sanity: walkable floor, patrol clearance, lifts in the void, kiosk reach), and the built levels/ccm collision
#      once it exists (skipped when tools/.venv is missing)
# Usage: tools/luatest/run.sh            (exit status 0 = all good)
# Fixtures (regenerate only for a new coopdx version): coopdx_constants_v151.lua,
# coopdx_api_v151.lua, coopdx_structs_v151.lua (gen_coopdx_*.py, see their headers).
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
MOD="$HERE/../../mods/sgl64"
LUA="${LUA:-lua}"
LUAC="${LUAC:-luac}"
export LUAC

echo "== luac -p"
for f in "$MOD"/*.lua; do
    "$LUAC" -p "$f"
    echo "ok $(basename "$f")"
done
if grep -nE '<const>|<close>|^[[:space:]]*global[[:space:]]' "$MOD"/*.lua; then
    echo "Lua 5.4/5.5-only syntax found (coopdx is Lua 5.3-style)"; exit 1
fi

echo "== check_api (sm64coopdx v1.5.1)"
"$LUA" "$HERE/check_api.lua" "$MOD"/*.lua

echo "== check_globals (cross-file, load order)"
"$LUA" "$HERE/check_globals.lua" "$MOD"

echo "== test_missions"
"$LUA" "$HERE/test_missions.lua"

echo "== test_flow (whole mod + level scripts)"
"$LUA" "$HERE/test_flow.lua"

echo "== test_reitz_missions (course 2: Reitz Union & Engineering)"
"$LUA" "$HERE/test_reitz_missions.lua"

echo "== test_lake_missions (course 3: Lake Alice)"
"$LUA" "$HERE/test_lake_missions.lua"

echo "== test_marston_missions (course 4: Marston Science Library)"
"$LUA" "$HERE/test_marston_missions.lua"

PY="$HERE/../.venv/bin/python"
if [ -x "$PY" ]; then
    echo "== check_swamp_points"
    out="$("$PY" -I "$HERE/check_swamp_points.py")" || { echo "$out"; exit 1; }
    echo "$out"
    echo "== check_reitz_points"
    out="$("$PY" -I "$HERE/check_reitz_points.py")" || { echo "$out"; exit 1; }
    echo "$out"
    echo "== check_lake_points"
    out="$("$PY" -I "$HERE/check_lake_points.py")" || { echo "$out"; exit 1; }
    echo "$out"
    echo "== check_marston_points"
    out="$("$PY" -I "$HERE/check_marston_points.py")" || { echo "$out"; exit 1; }
    echo "$out"
else
    echo "== check_swamp_points / check_reitz_points / check_lake_points / check_marston_points skipped (no tools/.venv)"
fi
echo "== all luatest checks passed"
