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
- Stage visitors, players with crowd disabled, and players far from sidewalks
  reserve their share. Unused shares are not lent out, so returning to the hub
  or re-enabling scenery cannot increase the total beyond the allocation.
- The host publishes budget and global player IDs in one synchronized value,
  at most once per second and only when changed. Clients wait for membership
  before spawning and can reduce shares earlier if they see a newer roster.
  Allocations converge after roster propagation; this is a cosmetic budget,
  not a distributed reservation protocol during network delays.
- Students remain local scenery, not shared physical NPCs. Clients see different
  students even when standing together, and do not spawn other players' shares.
  Only the budget/roster is synchronized; there are no student-position packets.
- The existing validated sidewalk graph covers hub area 1 only. Other stages
  and hub areas get no ambient crowd. Albert, Alberta, mission NPCs, and Gemini
  interactions are outside this budget and retain their existing behavior.
- Students spawn at safe sidewalk nodes 6–30 m away and within 5 m vertically.
  They turn toward the player beyond a 22 m leash, recycle off camera beyond
  38 m, and are removed beyond 55 m or 8 m vertically even if on camera.
  Distance checks are staggered every half second, so the hard limit allows a
  small movement overshoot between checks. Teleporting cannot leave a permanent
  crowd running elsewhere on the map.
- Spawning attempts at most two students each half second. No nearby or hidden
  path means fewer students, with automatic retry. Recycling never falls back
  to an in-view node. Retained students keep walking when allocations change.

## Validation and merge handoff

Run `lua tools/luatest/test_campus_npcs.lua` for the multi-client regressions,
and `tools/luatest/run.sh` for mod syntax/API/load-order and gameplay coverage.
Tests exercise real sidewalk routes, solo/two/twelve-player budgets, ordinary
and dedicated hosts, late joins, disconnects, local toggles, stage/area changes,
teleports, unavailable paths, camera constraints, and host-only budget commands.

Validation: 112 crowd checks passed and `tools/luatest/run.sh`
completed successfully, including campus route validation and existing gameplay,
bridge and actor tests. The runner skipped five optional Python geometry checks
(Swamp/Reitz/Lake/Marston/Library West) because `tools/.venv` is absent.

Merge and deployment belong to the deployment owner. Ship the updated Lua to
the server and clients together; older clients retain their original 40-object
behavior. Before release, check a two-client hub session, walk from the Plaza to
Library West, join/leave, and toggle `/crowd off|on`. Check for conspicuous spawn
or removal, path clipping and animation quality on target machines; record
frame times if choosing between the suggested budgets. Offline simulation does
not establish visual quality or an FPS gain. No deployment is performed here.
