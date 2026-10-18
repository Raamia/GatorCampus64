# Player-local campus crowd

Built on Pranav's campus NPC merge (#23). Previously every graphical client
simulated 40 students: 24 at landmarks and 16 around its player. Now the host
divides one budget among connected human players. Each client simulates only its
own share around its player. All 40 existing models remain available as a visual
library; no model or level rebuild is required.

## Suggested budgets

| Total budget | 1 player | 2 players | 4 players | 8 players | 12 players |
| --- | --- | --- | --- | --- | --- |
| 12 — light | 12 | 6 | 3 | 1 | 1 |
| **24 — default** | **12** | **12** | **6** | **3** | **2** |
| 36 — busier | 12 | 12 | 9 | 4 | 3 |

Every player receives `min(12, floor(budget / human_players))`. Remainders stay
unused so nobody gets preferential allocation. A budget below player count gives
everyone zero. The default reduces simulated crowd objects per client from 40
to at most 12; at twelve players it allows two each, 24 total instead of 480.
These are object counts, not measured frame-rate improvements. Actor asset
loading and memory are not reduced by the same ratio.

`SGL_CROWD_BUDGET` and `SGL_CROWD_PER_PLAYER` in
[`sgl_campus_npcs.lua`](../mods/sgl64/sgl_campus_npcs.lua) set the defaults.
The host can use `/crowd budget 12`, `/crowd budget 24`, or `/crowd budget 36`;
the accepted range is integer 0–40. Zero disables the crowd for everyone.
Changes last for the current session and reset when the mod reloads. On a
headless deployment, use the checked-in default unless a host-side command
interface is available; a connected player's command cannot change the budget.
`/crowd` reports local active count and allocation. `/crowd off|on` stays local.

## Allocation and behavior

- Active means connected human player; stationary players and stage visitors
  count. The headless host (global ID 0) does not. The ordinary graphical host
  does count. No AFK heuristic changes someone's allocation.
- Players with crowd disabled or without nearby safe paths reserve their share.
  Unused shares are not lent out, so changing areas or re-enabling scenery cannot
  increase the total beyond the allocation.
- The host publishes budget and global player IDs in one synchronized value,
  at most once per second and only when changed. Clients wait for membership
  before spawning and can reduce shares earlier if they see a newer roster.
  Allocations converge after roster propagation; this is a cosmetic budget,
  not a distributed reservation protocol during network delays.
- Students remain local scenery, not shared physical NPCs. Clients see different
  students even when standing together, and do not spawn other players' shares.
  Only the budget/roster is synchronized; there are no student-position packets.
- The hub uses its existing OSM sidewalk graph. The Swamp, Reitz exterior and
  interior, Lake Alice, Marston, and Library West use destination-specific paths
  generated from their built collision. Unmapped areas get no crowd. Albert,
  Alberta, mission NPCs and Gemini interactions remain outside this budget.
- Outdoors, students spawn 6–30 m away, steer home beyond 22 m, recycle out of
  view beyond 38 m, and are removed beyond 55 m. Interior distances are 2–12 m
  for spawning, 9 m for steering, 16 m for recycling and 24 m for removal.
  Spawn candidates must be within 1.2 m of the player's floor height.
- Level/area/act changes and abrupt horizontal or vertical teleports clear the
  previous crowd. Entering a new reachable indoor room also starts arrival
  recovery. Arrival waits ten frames for the destination to settle, then
  spawns at most two students per half second. During the first 100 frames,
  safe in-view candidates are permitted when there are no hidden ones; this
  prevents a stationary camera after a demo warp from suppressing every spawn.
  Ordinary replenishment after that window remains out of view.
- Spawn spacing prevents students appearing on top of one another. A small room
  or missing route can mean fewer students than the allocated share. Movement
  and recycling retain the shared budget; no new allocation is made per area.

## Indoor routing and teleport recovery

The previous implementation explicitly disabled the crowd outside hub area 1.
`/campus marston`, the map travel buttons and building doors enter other levels
or areas, so waiting or walking there could not restore those students. A strict
hidden-spawn filter could also leave a hub destination empty after a teleport.
The original tests covered changing coordinates within the hub but deliberately
expected no students in other levels; the new tests cover the real travel command.

[`area_routes.py`](../tools/npcs/area_routes.py) creates separate graphs for each
supported destination from exported `collision.inc.c` files and level objects.
It samples authored floor elevations, checks continuous floor support beneath
and beside each path, requires 0.75 m body clearance and 2 m headroom, and keeps
clear of static level objects. It excludes stairs, furniture tops, roof guesses,
and unsupported gaps. Graph edges never cross floors or walls. These are short
ambient stroll paths, not a building-wide navigation mesh.

On arrival and every half second indoors, up to eight collision rays find a
reachable nearby graph component on the player's floor. Students in a previous
unreachable component are retired, even when geographically close. A short
forward ray every six frames pauses walking for newly blocking doors or mission
props. Interior students do not push the player in narrow halls. Floors and room
clearance are validated against static geometry; this is not full dynamic
pathfinding or collision avoidance between students.

Elevators, stair travel and door warps repopulate the destination floor; students
do not traverse stairs/elevators themselves. Area changes are detected even when
an instant warp does not fire level initialization. Spatial buckets limit runtime
node searches to the player's neighborhood. Route construction happens offline;
the game caches adjacency and components per visited destination.

To rebuild/check after changing exported level geometry:

```sh
python3 -I tools/npcs/area_routes.py
python3 -I tools/npcs/area_routes.py --check
```

The generated file is `mods/sgl64/sgl_campus_npc_areas.lua` (about 1.2 MB of Lua
source across six destination areas). Commit it with geometry changes. Actor
assets are reused and do not need regeneration for this fix.

## Validation and merge handoff

Run `lua tools/luatest/test_campus_npcs.lua` for the multi-client regressions,
and `tools/luatest/run.sh` for mod syntax/API/load-order and gameplay coverage.
Tests exercise real sidewalk routes, solo/two/twelve-player budgets, ordinary
and dedicated hosts, late joins, disconnects, local toggles, stage/area changes,
teleports, unavailable paths, camera constraints, and host-only budget commands.
Follow-up regressions cover `/campus marston`, upstairs teleporting, map travel,
Reitz instant area changes, float coordinates, separate indoor rooms/floors,
arrival camera fallback, spawn spacing and dynamically blocking obstacles.

Teleport/interior follow-up: 165 crowd checks and three generator geometry
tests passed; the full `tools/luatest/run.sh` also completed successfully on
the final code and routes (the same five optional checks below were skipped).
An independent ray/triangle check of Marston collision confirmed
reachable route candidates at the command arrival (8 of the nearest 8) and the
upstairs test location (7 of 8).

Original budget validation: 112 crowd checks passed and `tools/luatest/run.sh`
completed successfully, including campus route validation and existing gameplay,
bridge and actor tests. The runner skipped five optional Python geometry checks
(Swamp/Reitz/Lake/Marston/Library West) because `tools/.venv` is absent.

Merge and deployment belong to the deployment owner. Ship the updated Lua to
the server and clients together, including both route files; older clients keep
their old crowd behavior. Before release, check a two-client hub session, then
use `/campus marston 1 me`, the map travel buttons, Reitz interior doors and an
upstairs teleport. Verify the crowd reappears on the correct floor, return to
the hub, join/leave, and toggle `/crowd off|on`. Check for conspicuous spawn
or removal, path clipping and animation quality on target machines; record
frame times if choosing between the suggested budgets. Offline simulation does
not establish visual quality or an FPS gain. No deployment is performed here.
