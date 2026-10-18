#!/bin/sh
# Offline checks for the mods/sgl64 Lua (no game needed):
#   1. luac -p on every mod Lua file (syntax; coopdx runs Lua 5.3-style code, keep 5.4/5.5-only
#      syntax such as <const>/<close>/global out of the mod)
#   2. check_api.lua: unknown functions/constants and wrong argument counts vs sm64coopdx v1.5.1
#   3. check_globals.lua: cross-file globals from the bytecode, in coopdx's load order (strcmp of the
#      file names): every read resolves, load-time reads only use earlier files, no shadowed coopdx
#      names, no global assigned by two files
#   4. test_missions.lua: multi-client simulation of the mission framework + Swamp missions (incl. the solo
#      Gator Chomp Chorus of swamp_chomp.lua played to its star, and the co-op path with 2 players)
#   5. test_flow.lua: the whole mod (every file) + the real level scripts of every built stage
#      (castle_grounds, bob, wf, jrb, ccm, bbh): doors, warp nodes, return spawns, act select, stars,
#      character select, Study Group
#   6. check_swamp_points.py: SWAMP_POINTS still match data/uf/swamp_points.json (the built Swamp)
#      (skipped when tools/.venv is missing)
#   7. test_reitz_missions.lua: course 2 (wf_reitz_missions.lua): the rooftop climb + window-washer lift,
#      the shared token hunt, the co-op robotics cranes (2-4 players), act select, levels/wf contract (incl. area 2,
#      the Reitz Union interior: entry node, exits, paired instant warps, elevator pads)
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
#  13. test_libwest_missions.lua: course 5 (uf_west_library_missions.lua): the all-nighter climb (stair barriers, rolling
#      ladders, sleepy Boos, the route marker), the coffee run (race, route, cups, stairwell Boos), the co-op quiet-hours
#      hide and seek (roles, counting, touch / lantern beam / line of sight, noise, sneezes, chime, out of the stacks,
#      infection, rotation, tallies), act select, levels/bbh contract once built
#  14. check_libwest_points.py: LIBWEST_POINTS vs data/uf/libwest_points.json or data/uf/libwest_layout.json (layout
#      sanity: walkable floor, columns, barriers on the doors, ladder decks, star humps, the arena, the coffee run's par),
#      and the built levels/bbh collision once it exists, incl. a walk through every door anchor and a
#      floor-crack scan (skipped when tools/.venv is missing)
#  15. test_qr.lua: sgl_qr.lua (vendored QR encoder) against known vectors (thonky.com HELLO WORLD 1-M codewords,
#      a pinned zbarimg-decoded 5-M matrix of the Gator Pass URL), QR structure, the HUD draw helper
#  16. test_login.lua: web platform mod side: guests.lua slots in characters.lua, charselect.lua paging,
#      sgl_login.lua (/login, /link, QR panel, login_cancel, verified marks + resend) against the real
#      sgl_bridge.lua with a simulated headless host, and a guests.lua rendered by server/bridge's
#      deploy.py (needs python3, or $PYTHON) loaded into characters.lua
#  17. test_bridge.lua: sgl_bridge.lua (hosted server bridge): JSON encoder / decoder, SGLEVT events (host prints,
#      client relay), inbox sequencing + routing, inert without a headless host
#  18. test_runs.lua: verified leaderboards (spec 10): the headless host's own timing of mission rounds and its
#      "run" event (solo, co-op with a pause, races GO -> finish, retries, dedupe, lost reports, offline inert),
#      the "leaderboard" inbox command and the leaderboard menu (live rows + age, scrolling, .sav fallback),
#      the solo outbox never written on a headless host
#  19. test_npc.lua: the roaming mascots (sgl_npc.lua): Albert and Alberta in the level of their spot, chat ->
#      outbox with the asker's live stats, /albert and /alberta, the bridge's replies relayed to everyone, the host's
#      synced moves (poofs, held while someone is near), their animations, timeouts
#  20. check_npc_ids.py: the NPCs of sgl_npc.lua match the personas in tools/npc_bridge/npcs.json
#  21. check_npc_spots.py: every mascot spot stands on flat, clear floor in the built level; routes keep exactly
#      one mascot on the hub
#  22. check_game_guide.py: tools/npc_bridge/game_guide.md covers every stage, door, star count and act of course.lua
#  24. test_rivals.lua: sgl_rivals.lua dresses every Goomba as a rival school's mascot (same on every client)
#  25. test_hud_sight.lua: sgl_hud_in_sight hides HUD labels drawn over the world (door labels, NPC name tags)
#      when a wall stands between the camera and the label
#  26. test_campus_npcs.lua: player-local campus crowd: shared budget, equal allocations, joins/leaves, twelve
#      players, headless exclusion, safe sidewalk movement, hard leash, camera-aware spawn and /crowd controls
#  27. tools/npcs/campus_routes.py --check: sgl_campus_npc_routes.lua matches the OSM footways + the built hub
#  23. tools/npc_bridge/test_*.py: the NPC chat bridge and the game guide (modfs protocol, routing, Gemini requests;
#      offline) and tools/actors/test_make_gators.py (the generated Albert and Alberta actors are valid and up to date)
# Usage: tools/luatest/run.sh            (exit status 0 = all good)
# Fixtures (regenerate only for a new coopdx version): coopdx_constants_v151.lua,
# coopdx_api_v151.lua, coopdx_structs_v151.lua (gen_coopdx_*.py, see their headers).
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
MOD="$HERE/../../mods/sgl64"
LUA="${LUA:-lua}"
LUAC="${LUAC:-luac}"
export LUAC

echo "== material lighting regression tests"
python3 -m unittest discover -s "$HERE/../blender" -p test_material_lighting.py
echo "== exported material lighting"
python3 "$HERE/../blender/fix_material_lighting.py" --check "$MOD"/levels/*/

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

echo "== test_free_roam"
"$LUA" "$HERE/test_free_roam.lua"

echo "== test_flow (whole mod + level scripts)"
"$LUA" "$HERE/test_flow.lua"

echo "== test_reitz_missions (course 2: Reitz Union & Engineering)"
"$LUA" "$HERE/test_reitz_missions.lua"

echo "== test_lake_missions (course 3: Lake Alice)"
"$LUA" "$HERE/test_lake_missions.lua"

echo "== test_marston_missions (course 4: Marston Science Library)"
"$LUA" "$HERE/test_marston_missions.lua"

echo "== test_libwest_missions (course 5: Library West After Dark)"
"$LUA" "$HERE/test_libwest_missions.lua"

echo "== test_qr (sgl_qr.lua: QR encoder known vectors)"
"$LUA" "$HERE/test_qr.lua"

echo "== test_login (guest slots, character select pages, Gator Pass login)"
"$LUA" "$HERE/test_login.lua"
echo "== test_bridge (sgl_bridge.lua: events, inbox)"
"$LUA" "$HERE/test_bridge.lua"
echo "== test_runs (verified runs, leaderboard command + menu)"
"$LUA" "$HERE/test_runs.lua"

PY="$HERE/../.venv/bin/python"
if [ ! -x "$PY" ]; then PY="$(command -v python3)"; fi
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
    echo "== check_libwest_points"
    out="$("$PY" -I "$HERE/check_libwest_points.py")" || { echo "$out"; exit 1; }
    echo "$out"
else
    echo "== check_swamp_points / check_reitz_points / check_lake_points / check_marston_points / check_libwest_points skipped (no tools/.venv)"
fi
echo "== test_npc (roaming mascots Albert and Alberta)"
"$LUA" "$HERE/test_npc.lua"
echo "== test_rivals (rival mascots replace the Goombas)"
"$LUA" "$HERE/test_rivals.lua"
echo "== test_hud_sight (door labels and NPC name tags hidden behind walls)"
"$LUA" "$HERE/test_hud_sight.lua"
echo "== test_minimap (floor selection, markers, privacy, and visibility)"
"$LUA" "$HERE/test_minimap.lua"
python3 -I "$HERE/check_minimap_textures.py"
python3 -I "$HERE/check_hub_materials.py"
echo "== live NPC geometry"
"$LUA" "$HERE/test_npc_geometry.lua"
echo "== test_campus_npcs (students walking the hub's sidewalks)"
"$LUA" "$HERE/test_campus_npcs.lua"
echo "== map-derived NPC data --check"
python3 -I "$HERE/../npcs/rebuild.py" --check
echo "== indoor crowd geometry tests"
python3 -m unittest discover -s "$HERE/../npcs" -p 'test_*.py'
echo "== check_npc_ids"
python3 -I "$HERE/check_npc_ids.py"
echo "== check_npc_spots"
python3 -I "$HERE/check_npc_spots.py"
echo "== check_game_guide"
python3 -I "$HERE/check_game_guide.py"
echo "== npc_bridge tests"
out="$(python3 -m unittest discover -s "$HERE/../npc_bridge" 2>&1)" || { echo "$out"; exit 1; }
echo "$out" | tail -1
echo "== generated mascot, pickup, Gator Crest and ride gator actor tests"
out="$(python3 -m unittest discover -s "$HERE/../actors" 2>&1)" || { echo "$out"; exit 1; }
echo "$out" | tail -1
echo "== all luatest checks passed"
