# Super Gatorlator 64: game flow contract

Status: flow spike + integration pass + review fix round (Oct 2026), coopdx v1.5.1. The hub (`castle_grounds`) and the real Swamp (`bob`) are built; The Swamp has 3 playable acts (§5.1), coins for its 100-coin star, Goombas, hearts and poles (§9). Nothing here has been run in the game yet: §10 is the test script.
This file is the contract for everything that moves a player between the hub and a stage: level slots, warp nodes, the hub doors, star ids, act order and how a stage must be built. Where it disagrees with `docs/game_design.md` §2.1, §2.3 and the act order of §7.1, **this file wins** (see §11).

Code that implements it:

| What | File |
|---|---|
| Stage table, warp node numbers, star helpers, course and act names, `sgl_act_is_soon` | `mods/sgl64/course.lua` |
| Level settings, camera, door behavior, door labels, hub NEXT hint, lives, draw distance, `/campus` | `mods/sgl64/levels.lua` |
| Mod header (`-- incompatible: romhack`), welcome popup, `/school` | `mods/sgl64/main.lua` |
| Mission framework (controller, leader, synced state, stars, Study Group `/join`, `/mission`, "coming soon" acts) | `mods/sgl64/sgl_mission.lua` |
| Mission HUD kit (`sgl_hud_blocked`: no mission UI under the character menu; markers stick to the screen edge as arrows when off screen; banners and prompts shrink to fit 4:3) | `mods/sgl64/sgl_hud.lua` |
| The Swamp's missions and every Swamp mission coordinate (`SWAMP_POINTS`) | `mods/sgl64/swamp_missions.lua` |
| Friend models (`/char`) and the character select menu | `mods/sgl64/characters.lua`, `mods/sgl64/charselect.lua` |
| Level generator: `--slot`, warp nodes, door objects, return spawns, level-script stars, music, water boxes (clipped to the play zone) | `tools/campus/build_stage.py` |
| Coins, hearts, 1-ups, Goombas and landmark poles of a stage (checked against the collision) | `tools/campus/stage_pickups.py` |
| Static check of the wiring (runs on every export) | `tools/blender/validate_level.py` (`check_flow_contract`) |
| Build reports with every door, spawn and node | `art/levels/hub/sgl_hub_build.json`, `art/levels/swamp/sgl_swamp_build.json` |
| Swamp anchor points measured on the built collision | `data/uf/swamp_points.json` |
| Offline checks of all of the above (no game) | `tools/luatest/run.sh` (§12) |

Units: 1 m = 100 game units. Game X = east, Y = up, Z = **south**. Game yaw: `0` faces +Z (south), `0x4000` faces +X (east), `0x8000` faces −Z (north), `0xC000` faces −X (west). Hub map metres convert as `X = (x + 45) * 100`, `Z = -(y - 98) * 100` (stages.json hub centre (−45, 98)).

---

## 1. The flow in one picture

```
new game / game over ──► hub (LEVEL_CASTLE_GROUNDS), MARIO_POS on the Plaza of the Americas
                              │
          walk into door i ───┤ id_bhvSglDoor: stage built? enough stars? (else a popup, door stays shut)
                              ▼
          vanilla warp: hub WARP_NODE(0x10+i) ──► stage level, area 1, node 0x0A
                              ▼
                      VANILLA ACT SELECT (course i acts)
                              ▼
                 stage, spawn 0x0A (spin-in), act k
     ┌────────────────────────┼─────────────────────────────┬─────────────────────────┐
  star (leave level)     death / fall / pause "Exit course"   pause "Exit to castle"   game over
  stage 0xF0             stage 0xF1                            exitCastle* node 0x0A    entryLevel
     ▼                        ▼                                    ▼                       ▼
  hub 0x20+i              hub 0x30+i                            hub Plaza 0x0A          hub Plaza (MARIO_POS)
  outside door i,         outside door i,                       (spin-in)               lives = 4
  course-complete screen  death exit (−1 life; none for Exit course)
```

Nothing warps "around" the engine: every step is a vanilla level-script warp node, so act select, the course-complete screen, life loss, coopdx instancing and star sharing all behave like Super Mario 64.

---

## 2. Level slots

Our levels **replace vanilla levels** through DynOS, as Star Road does. `mods/sgl64/levels/<slot>/` holds the Fast64 C export with the script `level_<slot>_entry`. coopdx compiles it into `levels/level_<slot>_entry.lvl` at launch, and that `.lvl` overrides the vanilla level of the same name. `level_is_vanilla_level(LEVEL_X)` returns `false` once ours is loaded, and that is how Lua knows a stage is built (`sgl_stage_ready`).

| Door | Stage | Slot folder | Level | Course | Stars to open | Hub building door | Status |
|---|---|---|---|---|---|---|---|
| hub | Central Campus | `castle_grounds` | `LEVEL_CASTLE_GROUNDS` (16) | none | 0 | (start) | built |
| 1 | The Swamp | `bob` | `LEVEL_BOB` (9) | `COURSE_BOB` 1 | 0 | University Auditorium | **built** (§9), acts 1-3 playable |
| 2 | Reitz Union & Engineering | `wf` | `LEVEL_WF` | `COURSE_WF` 2 | 2 | The Hub | reserved |
| 3 | Lake Alice | `jrb` | `LEVEL_JRB` | `COURSE_JRB` 3 | 8 | Newell Hall | reserved |
| 4 | Marston Science Library | `ccm` | `LEVEL_CCM` | `COURSE_CCM` 4 | 5 | Marston | reserved |
| 5 | Library West After Dark | `bbh` | `LEVEL_BBH` | `COURSE_BBH` 5 | 14 | Library West | reserved |
| 6 | Century Tower (interior) | `ttc` | `LEVEL_TTC` | `COURSE_TTC` 14 | 20 | Century Tower base (north) | reserved |

`sgl_test` stays a custom test level (`level_register`, `/campus test`). The old custom hub `sgl_hub` is retired. Its folder was moved to the macOS Trash, so it can be restored.

Global settings (`levels.lua`, at mod load):
- `gLevelValues.entryLevel = exitCastleLevel = LEVEL_CASTLE_GROUNDS`, `exitCastleArea = 1`, `exitCastleWarpNode = 0x0A`
- `gLevelValues.fixCollisionBugs = 1`
- `gServerSettings.skipIntro = 1`: the vanilla intro cutscene assumes Peach's castle grounds.
- `camera_set_romhack_override(RCO_ALL_EXCEPT_BOWSER)` and `camera_set_use_course_specific_settings(false)`, as Star Road does.
- No `HOOK_USE_ACT_SELECT` hook. Registering one replaces coopdx's default rule (act select for courses 1-15) for **every** level, so do not add one casually.
- `gServerSettings.stayInLevelAfterStar` is **not** forced. With the host default ("Leave level") a star sends the collector back to the hub. With "Stay in level" the group keeps playing and leaves through the pause menu.

---

## 3. Warp nodes

All nodes are in **area 1**.

### 3.1 Hub (`castle_grounds`)

| Node | WARP_NODE destination | Spawn object (bparam2 = node) | Used by |
|---|---|---|---|
| `0x0A` | CASTLE_GROUNDS 1 `0x0A` | `bhvSpinAirborneWarp` + `MARIO_POS`, Plaza (8320, 100, −4440), compass 190° (faces the Auditorium) | `warp_to_level(LEVEL_CASTLE_GROUNDS, 1, 0)`, pause "Exit to castle", `/campus hub` |
| `0x0B` | CASTLE_GROUNDS 1 `0x0B` | `bhvDeathWarp`, Plaza (8470, 100, −4440) | dying **in the hub** (hub `0xF1` → `0x0B`) |
| `0xF0` | CASTLE_GROUNDS 1 `0x0A` | (none) | unused hub success exit |
| `0xF1` | CASTLE_GROUNDS 1 `0x0B` | (none) | death in the hub |
| `0x10 + i` | stage i's level, 1, `0x0A` | (none: the door object `id_bhvSglDoor` carries `0x10 + i` in bparam2) | door i |
| `0x20 + i` | CASTLE_GROUNDS 1 `0x20 + i` | `bhvPaintingStarCollectWarp` outside door i | stage i `0xF0` (after a star) |
| `0x30 + i` | CASTLE_GROUNDS 1 `0x30 + i` | `bhvPaintingDeathWarp` outside door i (same spot) | stage i `0xF1` (death, fall, pause "Exit course") |

So for The Swamp: hub `0x11` → BOB `0x0A`; BOB `0xF0` → hub `0x21`; BOB `0xF1` → hub `0x31`.

### 3.2 Every stage (slot s, door i)

| Node | WARP_NODE destination | Spawn object |
|---|---|---|
| `0x0A` | own level, 1, `0x0A` | `bhvSpinAirborneWarp` with bparams `0x000A0000` (+ `MARIO_POS`) |
| `0xF0` | `LEVEL_CASTLE_GROUNDS`, 1, `0x20 + i` | (none) |
| `0xF1` | `LEVEL_CASTLE_GROUNDS`, 1, `0x30 + i` | (none) |

No `0xF3`. Falling onto a `SURFACE_DEATH_PLANE` without a `0xF3` node uses `0xF1` (death return, −1 life, or game over at 0 lives). Extra areas, instant warps and pipes inside a stage are the stage's own business. They must not reuse `0x0A`/`0xF0`/`0xF1`.

---

## 4. Hub doors

### 4.1 Positions

Door positions come from the landmark modules' `doors` (`stage_landmarks.DOOR_DEFAULTS` picks which one). They sit on the facade (collision) plane at the sill. "Facing" is the compass direction a player walking out of the door looks (0 = north).

| i | Building door | Map m (x, y, z) | Facing | Door object, game units (X, Y, Z) | Yaw | Trigger half width | Return spawns `0x2i`/`0x3i`, game units | Return yaw |
|---|---|---|---|---|---|---|---|---|
| 1 | University Auditorium (centre porch door) | (38.50, 62.85, 0.0) | 1.5° N | (8350, 0, 3515) | 0x7EEF | 1.6 m | (8357, 80, 3265): 2.5 m out | 0xFEEF |
| 2 | The Hub (south entrance) | (−194.85, −84.65, 0.0) | 144.1° SE | (−14985, 0, 18265) | 0x1987 | 1.8 m | (−14838, 80, 18468): 2.5 m out | 0x9987 |
| 3 | Newell Hall (east entry, top of stoop) | (−154.68, 30.25, 1.2) | 90° E | (−10968, 120, 6775) | 0x4000 | 1.8 m | (−10668, 80, 6775): 3 m out, on the ground | 0xC000 |
| 4 | Marston (north wing main door) | (−58.50, −69.00, 0.0) | 0° N | (−1350, 0, 16700) | 0x8000 | 1.8 m | (−1350, 80, 16450): 2.5 m out | 0x0000 |
| 5 | Library West (revolving door) | (38.91, 258.43, 0.0) | 180° S | (8391, 0, −16043) | 0x0000 | 1.8 m | (8391, 80, −15793): 2.5 m out | 0x8000 |
| 6 | Century Tower (north bay) | (−0.93, 3.31, 0.0) | 359.8° N | (4407, 0, 9469) | 0x8024 | 1.6 m | (4406, 80, 9219): 2.5 m out | 0x0024 |

The Smathers (bonus slide, 3★) and FINAL EXAM (30★) doors keep their signposts but have no slot or door object yet.

**Return spawn yaw faces the door** (the contract text says "facing away"; this is deliberate). `bhvPainting*` spawns launch Mario backwards (forward speed −32), so an object facing the door sends him out and away from it. He is drawn facing away while flying. After the course-complete screen the star exit turns him round for good (`handle_save_menu`: `faceAngle += 0x8000`). Net effect: he ends up about 5.5 m out from the door, facing away from it, as the contract intends. The generator checks that the 4.5 m launch path is clear and has floor (`return_spawn_spot`). These spots are outside the door trigger (1.5 m), so arriving never re-enters a door.

### 4.2 The door object `id_bhvSglDoor` (`levels.lua`)

Placed by the generator in the hub level script:

```
OBJECT(MODEL_NONE, X, Y, Z, 0, yawDeg, 0, (i << 24) | ((0x10 + i) << 16) | (halfWidth_dm << 8) | emblem_dm, id_bhvSglDoor)
   e.g. door 1: 0x0111102A = door 1, node 0x11, half width 1.6 m, emblem 4.2 m up
```

- **bparam1**: door index i (= `SGL_STAGES[].door` in `course.lua`).
- **bparam2**: the hub warp node `0x10 + i`. The vanilla warp reads it from `m.usedObj`.
- **bparam3**: trigger half width in 10 cm units (door width / 2 + 0.6 m).
- **bparam4**: emblem height in 10 cm units. It is 4.2 m, lowered to 0.7 m under any porch roof or canopy above the doorway (The Hub 2.9 m, Library West 3.9 m, Century Tower 3.0 m).

Each client runs its own copy (no sync), and only the local player is checked. Every frame:

1. **State.** "coming soon" if `level_is_vanilla_level(stage level)` (stage not built). Otherwise "locked" if `sgl_total_stars() < stars`, else "open". `sgl_total_stars()` = `save_file_get_total_star_count(file, COURSE_MIN-1, COURSE_MAX-1)`: all courses plus castle secret stars, shared by everyone.
2. **Looks.**
   - The object is lifted to the emblem spot and spins: a gold star when open, a see-through star when locked or coming soon.
   - Two red flames (`E_MODEL_RED_FLAME`, non-synced child objects, no damage) flank every door that will not open.
   - Within 25 m, a floating label shows the stage name and `Walk in!` / `LOCKED - N stars (you have M)` / `Coming soon`.
   - The door's signpost text is rewritten on every hub visit, so it says whether the stage is built.
3. **Trigger.** Mario is in the doorway when he is up to 1.5 m in front of the door plane (to 3 m behind it, for recessed bays) and within the half width, with feet 1.5 m below to 3.5 m above the sill. He must also face into the door (within 79°), be in a normal action (not intangible, cutscene or automatic, e.g. not mid-spawn or bubbled), be alive and be area-synced. Then:
   - **open**: exactly what vanilla `interact_warp` does: `m.interactObj = m.usedObj = door`, `SOUND_MENU_ENTER_HOLE`, `set_mario_action(m, ACT_DISAPPEARED, (WARP_OP_WARP_OBJECT << 16) + 2)`. Two frames later `level_trigger_warp` takes node `0x10 + i` from `usedObj`, the star-shaped fade plays, and the level change to a course runs `lvl_set_current_level`. That function returns 1 for courses 1-15, which brings up **the vanilla act select**.
   - **locked / coming soon**: one popup (and a buzz) per approach. Step 4.5 m away to see it again.

---

## 5. Stars and acts

| Star | Save slot | Star id (`bparam1 = id << 24`) |
|---|---|---|
| Act k (1..6) mission star of stage i | stage i's course | **k − 1** (`sgl_mission_star_id(k)`) |
| 100-coin star | stage i's course | **6** (vanilla: spawns automatically at 100 coins, `SGL_STAR_ID_100_COINS`) |
| Hub secrets (later) | castle secret stars (course −1) | 0-6 |

coopdx shares every collection (`packet_collect_star`) and saves it in the host's slot. Only the player who touches the star does the star dance and leaves; everyone else in the act stays, sees the star vanish, and the mission panel says "Star collected by <name>". They get a 10 s prompt "<name> got the star! D-pad Up: back to campus together": D-pad Up takes the pause menu's EXIT COURSE (`level_trigger_warp(m, WARP_OP_EXIT)`: the stage's `0xF1` → outside the stage's hub door, no life lost), so the group does not get split by the host's "Leave level" setting.

The round ends (DONE) on the collector's "got" event from **any** live state, not only after SUCCESS: a level-script star (act 1) can be grabbed before the leader's tick has seen anyone on the roof. A `levelStar` mission also ends when its star object vanishes on the leader's client (collected elsewhere), even if the event is lost.

### 5.1 Act order: playable acts first, no gaps

The vanilla act select (`star_select.c`) lets you pick **every act you already have the star of, plus the first act you do not have**. So act k only appears once acts 1..k−1 are all collected. A stage whose act 2 has no star would stop every player at act 2 for good. Hence:

- **Playable acts are numbered 1..n with no gap**, solo-able acts first (a co-op act can't hold up a solo player behind it).
- Acts with nothing in them yet are named **`COMING SOON - …`** in `course.lua`. `sgl_act_is_soon(stage, k)` is true for them (or for a stage without act names). They load the stage as free roam with no star. A banner and panel say so on arrival ("No mission here yet - explore! Pause > EXIT COURSE goes back."), and they send no Study Group invite. Pause → EXIT COURSE (stage `0xF1`, no life lost) or `/campus hub` leaves. Nothing soft-locks: the worst case is an act with no star, which is always exitable.
- When a mission lands, rename its act in `course.lua` (the mission `title` must equal the act name; `tools/luatest` checks it) and keep the playable block contiguous. Renumber acts if needed: nothing else depends on the number except the star id (k − 1).

**The Swamp (course 1)**:

| Act | Name (act select) | What | Star | Players |
|---|---|---|---|---|
| 1 | KICKOFF - CLIMB THE SKYBOX | `swamp_skybox` (reach): climb the West Skybox Tower to the press box roof, 66 m. The marker walks the route (CLIMB HERE at the west rim → LEDGES → CAMERA DECKS / POLE → PRESS BOX ROOF); coins on every ledge and deck, 3 hearts, a 22.5 m pole from the Bull Gator Deck to the roof | **level-script** `bhvStar` id 0, `ACT_1`, on the roof (−3828, 6720, 3648) | 1+ |
| 2 | STADIUM STAIR SPRINT | `swamp_sprint` (race): north end zone → east stands → rim → South Ramp terrace, 9 checkpoints, par 1'10, gold 0'45; race music while racing; D-pad Down / `/mission start` = back to the start box; 2 Goombas and coin lines on the rim run | spawned, id 1, onto the South Ramp terrace | 1+ |
| 3 | GATOR CHOMP CHORUS - 2P | `swamp_chorus` (buttons, POUND mode): 3 phrases. In each, hold the lit end-zone corners while the crowd counts GA... TOR..., then everyone ground-pounds on CHOMP! (1.3 s window). The next phrase lights other corners (2 players: NW + SE, NE + SW, NW + SE) | spawned, id 2, from the south scoreboard to midfield | **2-4** |
| 4 | COMING SOON - MASCOT | design §7.1 act 2 "The Visiting Mascot" | none yet | |
| 5 | COMING SOON - TAILGATE | design §7.1 act 4 "Tailgate Tokens" | none yet | |
| 6 | COMING SOON - FLYOVER! | design §7.1 act 6 "Flyover!" | none yet | |

(`data/uf/swamp_points.json` keeps the design numbering in its `actN_` keys: design 5 is course act 2.)

Act names use the act-select **menu font**: A-Z, 0-9, space and `' . , - & ! ?` only. No lower case, colon, parentheses or plus, which is why "(2P+)" became "- 2P". Courses 2, 3, 4, 5 and 14 have their names set; their acts get names when the stages arrive (until then every act of theirs counts as "coming soon").

### 5.2 Placing or spawning a star

**In the level script** (static star, `build_stage.py` `STAGE_STARS`):
```
OBJECT_WITH_ACTS(MODEL_STAR, x, y, z, 0, 0, 0, (k - 1) << 24, bhvStar, ACT_k)
-- Fast64 / sgl_level.py: L.add_object(area, "Star act k", (x, y, z), "bhvStar", "MODEL_STAR",
--                                     bparams="0x0%d000000" % (k - 1), acts=[k])
```
**From a mission** (`sgl_mission.lua`, design doc §6.2):
- The framework spawns one controller object (`id_bhvSglMission`) per act visit on every client, from Lua; a level script may also place one with `OBJECT_WITH_ACTS(MODEL_NONE, ..., (k-1) << 24 | missionNum << 16, id_bhvSglMission, ACT_k)` and it is adopted.
- When the synced state reaches SUCCESS, **every client** calls `spawn_default_star(x, y, z)` from inside that object's loop. It reads the id from the calling object's `oBehParams >> 24`, coopdx de-duplicates it per bparams and sends `PACKET_SPAWN_STAR`, so exactly one star appears. Never call it from `HOOK_UPDATE`.
- A mission whose act also has a level-script star sets `levelStar = true` (Swamp act 1): it tracks the goal and never spawns a second star; if the level has no such star it falls back to spawning one (console warning). Any other mission spawns its star and its act must **not** have a level-script `bhvStar` (console warning; `tools/luatest/test_flow.lua` fails).
- After the dance the collector leaves through the stage's `0xF0` and lands outside the stage's door (`0x2i`) with the course-complete screen. There is nothing to wire in the mission.

Helpers in `course.lua`: `SGL_STAGES`, `sgl_stage_by_level(gNetworkPlayers[0].currLevelNum)`, `sgl_stage_by_course`, `sgl_stage_by_key`, `sgl_stage_by_door`, `sgl_mission_star_id`, `sgl_act_name`, `sgl_act_is_soon`, `sgl_stage_ready`, `sgl_total_stars`, `sgl_stage_star_flags`. The act number is `gNetworkPlayers[0].currActNum` (players only see each other in the same level + area + act).

## 6. Returning to the hub

| Event | Path | Lands | Lives |
|---|---|---|---|
| Star collected (host setting "Leave level", the default) | star dance → `WARP_OP_STAR_EXIT` → stage `0xF0` | hub `0x2i`, outside door i, course-complete screen | unchanged |
| Death (health, drowning, death plane) | stage `0xF1` | hub `0x3i`, outside door i, death exit | −1 (game over at 0) |
| Pause → EXIT COURSE | `WARP_OP_EXIT` → stage `0xF1` | hub `0x3i`, outside door i, death-exit animation | not lost |
| D-pad Up after a friend's star ("back to campus together", 10 s) | the same `WARP_OP_EXIT` (`level_trigger_warp`) | hub `0x3i`, outside door i | not lost |
| Pause → EXIT TO CASTLE | `exitCastleLevel/Area/WarpNode` | hub `0x0A`, Plaza, spin-in | unchanged |
| Game over | `gLevelValues.entryLevel` | hub `MARIO_POS`, Plaza | reset to 4 |
| Death in the hub | hub `0xF1` → `0x0B` | Plaza, death exit | refilled at once (hub) |

Lives (`levels.lua`, the Star Road idea of no harsh game overs): every session starts with at least `SGL_LIVES = 4`. While you are in the hub, lives are kept topped up to 4; the top-up runs once any death exit has landed and taken its life. A game over can therefore only happen after losing 4 lives inside one stage visit, and it just returns you to the Plaza. With the host's "bubble on death" setting, a player who dies while teammates are nearby becomes a bubble instead (coopdx), and none of the death paths above run.

Draw distance: in the hub and in every built stage, `set_override_far(SGL_FAR_UNITS = 100000)` (1000 m). `build_stage.py` fits the fog to exactly that (fog 200 m → 1000 m).

---

## 7. How a stage build must look (Swamp builder checklist)

1. Build with the generator into the slot:
   ```
   tools/blender/run_blender.sh tools/campus/build_stage.py -- swamp --slot bob
   ```
   (`--slot` defaults from `STAGE_SLOTS`: swamp → bob, reitz_eng → wf, lake_alice → jrb.) This writes `mods/sgl64/levels/bob/` with `level_bob_entry` (plus `data/uf/swamp_points.json` and `art/levels/swamp/`). `--levels-dir DIR --report-dir DIR` send a test build to scratch instead.
2. The generator writes the stage's warp nodes (§3.2) itself. Add a spawn for the stage to `SPAWN` in `build_stage.py`, e.g. `"swamp": {"pos": (x_m, y_m), "facing": deg}` in map metres. Without it the stage spawns at the window centre facing north, with a warning.
3. Landmark modules for the stage list it: `"stages": ["swamp"]` (`_common.py` contract; a missing key means `["hub"]`). Modules with no entry for the stage are skipped, and mixed modules drop the other entries' parts. Geometry stays in **map metres**. `ctx["stage_key"]` and `ctx["stage"]` describe the stage being built.
4. The export must pass `validate_level.py`, which now also runs `check_flow_contract`: `0x0A` spawn, `0xF0 → LEVEL_CASTLE_GROUNDS 0x2i`, `0xF1 → 0x3i`, and the `bhvStar`s it found with their acts. It also warns when a Lua name used by the level script (signs, `id_bhv…`) is not assigned in any `mods/sgl64/*.lua`.
5. Everything must fit in s16 (±327.67 m from the stage centre). The generator now skips trees within 10.5 m of that limit and only builds the hub props in the hub.
6. Area 1 holds the outdoor stage. More areas are fine (`INSTANT_WARP` or extra warp nodes); keep `0x0A`/`0xF0`/`0xF1` as above.
7. Stars and mission objects: see §5. Level-script objects that should only exist in one act use `OBJECT_WITH_ACTS(…, ACT_k)` (`L.add_object(..., acts=[k])`). `OBJECT` means all acts. Coins, hearts, 1-ups, enemies and landmark poles go in `tools/campus/stage_pickups.py` (`STAGE_PICKUPS[<stage>]`; every item is checked against the collision and skipped with a warning if it does not fit); a stage that uses common0 models (`MODEL_HEART`, `MODEL_GOOMBA`, …) is listed in `STAGE_COMMON0_MODELS` so its script gets `JUMP_LINK(script_func_global_1)`. Give a stage at least ~120 coins so its 100-coin star (id 6) is reachable.
8. Add the stage's map centre to `SGL_MAP_CENTERS` in `levels.lua` (stages.json `center_m`) so `/campus where` prints campus map coordinates there (The Swamp: `{ -580, 160 }`, done).
9. Missions: register them in a `<stage>_missions.lua` (§5.1, §5.2), keep every coordinate in one table checked against the stage's `data/uf/<stage>_points.json`, and run `tools/luatest/run.sh`.

The **hub** is built with `build_stage.py -- hub` (slot `castle_grounds`). It writes the six door objects, the 12 return spawns, `0x0A`/`0x0B` and all hub nodes. Rebuild it after changing any landmark door: positions are re-derived every build, and the build report lists them under `flow_doors`. The seam repair is on for the hub as well since the integration pass (`REPAIR_COLLISION_STAGES`): it closed about 90 % of the hub's crack points (almost all on roofs); the rest are small modelling gaps between separate slabs.

---

## 8. Test commands (`/campus`, `levels.lua`)

| Command | Effect |
|---|---|
| `/campus where` | level / area / act, position in game units and metres; campus map metres in the hub |
| `/campus list` | which slots are ours vs vanilla, door, stars to open; your stars and lives |
| `/campus hub` or `/campus back` | everyone to the Plaza (act 0, like every normal hub arrival) |
| `/campus test` | everyone to sgl_test |
| `/campus swamp [act]` | everyone straight into The Swamp act (default 1), skipping the door and act select |
| any of the above + `me` | only you |

Only the **host** (or a moderator) moves everyone. Anyone else's `/campus …` moves only themselves (with a chat note), and clients ignore a `"warp"` packet that does not come from the server (`NPT_SERVER`) or a moderator, so a stray command cannot drag the group past the door locks and the act select.

Other stage keys: `reitz`, `alice`, `marston`, `libwest`, `tower`. They are refused until that slot is built.

---

## 9. The Swamp build (`levels/bob`)

Built by `build_stage.py -- swamp` (slot `bob`) from the stages.json swamp window (centre (−580, 160) m): OSM ground, roads, 83 buildings, 260 trees and 4 pools, the stadium (Ben Hill Griffin, sunk bowl, field at −10 m, rim at 20 m, West Skybox Tower 66 m) and the O'Connell Center / Florida Gym modules, game-day dressing, and invisible walls at the 520 m play zone. Report: `art/levels/swamp/sgl_swamp_build.json`; previews: `art/levels/swamp/`.

- **Spawn `0x0A`**: Courtyard of Champions, north of the stadium's north gatehouse, (6651, 100, −11298), facing south at the gate (map (−513.5, 273.0)).
- **Exits**: `0xF0 → hub 0x21`, `0xF1 → hub 0x31` (Auditorium door).
- **Level-script star**: act 1 only, id 0, on the press box roof at (−3828, 6720, 3648).
- **Mission anchors**: `data/uf/swamp_points.json` (every point re-measured on the built collision). `SWAMP_POINTS` in `swamp_missions.lua` copies the ones the missions use; `tools/luatest/check_swamp_points.py` fails on drift > 0.5 m. Every probe, button, checkpoint and star target sits on the built floor (checked with SM64's `find_floor` rules on `area_1/collision.inc.c`).
- **Collision**: 7,188 triangles after the post-export seam repair (`stage_collision.py`: T-junction split, weld, split again), which removes the integer-rounding cracks where floors meet (invisible walls or holes). The 5 cm modelling gaps at the tops of the two north helix ramps (22 m) are closed since the fix round: the bridges' collision decks now overlap the helix landing (0.4 m) and the vomitory floor (0.9 m) (`swamp_stadium.py` `bridge(col_ext=…)`). Crack scan: 1,940 points at 22 sites → 125 points at 20 sites, none larger than a few cm.
- **Pickups** (`stage_pickups.py`, every one checked against the collision): **142 coins** (+7 from Goombas; the vanilla 100-coin star, id 6, is reachable): one coin over each of the 21 ledges and camera decks of the act 1 climb, coin lines on the sprint's rim run, the concourse, the field apron and in front of the spawn, a ring at midfield and on the gatehouse roof, lines on both video-board tops. 4 recovery hearts (west rim, Bull Gator Deck, camera deck 5, South Ramp terrace), 3 1-ups (light frame top 71 m, Exactech Arena crown, Florida Gym tower deck), 7 Goombas (concourse, Courtyard of Champions, 2 on the sprint's rim run). The level script loads the common0 model group (`JUMP_LINK(script_func_global_1)`, for `MODEL_HEART` / `MODEL_GOOMBA`); `validate_level.py` knows it.
- **Poles** (the stadium module's `markers["poles"]`, `bhvPoleGrabbing`): both goalposts, a 22.5 m pole from the Bull Gator Deck to the press box roof (an alternative to the 10 camera-deck hops), the south board leg (24.2 m) and three hanging poles on the east light masts.
- **Look**: own music (`SEQ_LEVEL_SNOW`; the hub keeps `SEQ_LEVEL_GRASS`, the act 2 race plays `SEQ_LEVEL_SLIDE`). The bowl is solid colour blocks (blue lower bowl, orange upper bowl and Sunshine Seats; risers in the banner's darker hem shade, treads in the main colour) instead of blue/grey/orange stripes every 0.5 m; the camera decks are orange like the ledges.
- **Death return** (`0xF1`, −1 life): lose all health, e.g. drown in the Florida Pool (east of the stadium) or take two falls from the press box roof (a fall over 30 m costs 4 of 8 health wedges with the cap on). Pause → EXIT COURSE takes the same exit without losing a life. Coins heal one wedge each, hearts heal fully.

---

## 10. In-game test script (lead)

The same script, without the contract notes, is in `README.md` → Testing. Each step names what it proves.

### 10.0 Before the game (offline, about 1 minute)

```
tools/luatest/run.sh            # ends with "== all luatest checks passed" (§12)
tools/.venv/bin/python -I tools/blender/validate_level.py mods/sgl64/levels/castle_grounds   # 0 error(s), 0 warning(s)
tools/.venv/bin/python -I tools/blender/validate_level.py mods/sgl64/levels/bob              # 0 error(s), 0 warning(s)
./install-mods.sh               # rsync --delete: stale compiled .lvl files of changed levels go away
```

Start sm64coopdx → **Host** → an **unused save slot** (0 stars) → Mods: only **Super Gatorlator 64** (`incompatible: romhack`) → keep **Stay in Level After Star: Leave Level** → Host. The first launch compiles `castle_grounds`, `bob` and `sgl_test` (a few seconds). To see the first-time character menu again, delete `~/Library/Application Support/sm64coopdx/sav/sgl64.sav` (it stores the pick and the race best).

### 10.1 Single player

1. **Spawn** (`entryLevel`, hub `MARIO_POS`): you land **standing** on the Plaza of the Americas facing south, the University Auditorium ahead, no Peach intro. (A fresh start uses `MARIO_POS` with no warp, so there is no spin-in; the spin-in only plays for `/campus hub` and Pause → Exit to castle, which use node `0x0A`.) Popup "Welcome to Super Gatorlator 64, <you>!". No `[SGL]` errors in the console, and no "loaded" banner at the top of the screen (removed). If chat says "The campus hub did not load", DynOS did not compile `levels/castle_grounds`.
2. **Character select** (`charselect.lua`, first time only, about 1 s after landing): "CHOOSE YOUR GATOR!" with 10 portrait cards. The vanilla HUD, the door labels and the hub's NEXT panel are hidden under it (`sgl_hud_blocked`). Move with the D-pad, stick or arrow keys and pick with A (keyboard L). The title flashes "HERE WE GO, <NAME>!", the menu closes and your model changes. L + START (keyboard Left Shift + Space), `/char` or Pause → Mods → "Choose your friend" reopens it; B or START closes it.
3. **Hub hint** (`levels.lua`): about 1.5 s after the menu closes, the popup "University of Florida / Walk into the University Auditorium door to enter THE SWAMP!" and, for 20 s, a left panel "NEXT: THE SWAMP / UNIVERSITY AUDITORIUM door - walk in!" with a gold marker over the door (an arrow on the screen edge when the door is behind you). Every later hub arrival shows the NEXT panel again (the next stage with an unstarred act).
4. `/campus list` → `hub(castle_grounds)=ours, swamp(bob, door 1, 0*)=ours`, every other stage `vanilla`, then `stars 0, lives 4`.
5. **A shut door** (§4.2 "coming soon"): walk about 115 m north to Library West. Above its door: a see-through spinning star, red flames on both sides, the label "LIBRARY WEST AFTER DARK / Coming soon". Walk into it: popup "… is coming soon (opens at 14 stars)" + buzz, and you stay in the hub. Every door except the Auditorium's looks like this.
6. **The Swamp door** (hub `0x11` → BOB `0x0A`, vanilla act select): walk about 80 m south of the spawn to the Auditorium's centre porch door: gold star, no flames, label "THE SWAMP / Walk in!". Walk in: Mario vanishes, star fade, then the **act select** shows course "THE SWAMP" with only act 1 "KICKOFF - CLIMB THE SKYBOX". Press A.
7. **Act 1 arrival** (BOB `0x0A`): spin-in on the Courtyard of Champions facing the stadium's north gate. New music (Cool Cool Mountain's theme). A coin line leads to the gate and two Goombas wander between you and it. Banner "THE SWAMP - ACT 1 / KICKOFF - CLIMB THE SKYBOX"; left panel "You 0 m team best 0 m goal 66 m" with three milestones, which shrinks to the height line after ~5 s; an orange "CLIMB HERE" marker (an edge arrow when off screen). `/campus where` → `level 9 area 1 act 1 …` and about `campus map: -513.5 m east, 273.0 m north …`. `/mission` → `KICKOFF - CLIMB THE SKYBOX (swamp_skybox act 1): active, round 1, players 1/1, leader <you>`. A panel saying "Mission offline here" means the geometry probes failed: send the console line.
8. **Climb + level-script star** (§5.1, `0xF0` → hub `0x21`): through the north gate onto the concourse (coin lines lead west), round to the West Skybox Tower, up the west stands to the west rim (20 m, a heart there). The marker switches to "LEDGES": climb the 11 orange ledges of the tower's south bay (a coin over each) to the Bull Gator Deck (44 m, a heart); the marker switches to "CAMERA DECKS / POLE": either hop up the 10 orange camera decks (coins, a heart on deck 5) or climb the 22.5 m pole next to them and jump off its top; from the first deck on the marker says "PRESS BOX ROOF". Toasts "West rim reached! (20 m)" and "Bull Gator Deck reached! (44 m)" (the panel opens up for 5 s each time); on the roof "STAR!" and "Done! Grab the star!". The star has been on the roof all along (there is no second one). Grab it: star dance, you fly out of the Auditorium door, course-complete screen "THE SWAMP / KICKOFF - CLIMB THE SKYBOX", and you end up outside the Auditorium. Stars: 1.
9. **Act 2, the race**: walk into the Auditorium door again. The act select now offers acts 1 and 2 "STADIUM STAIR SPRINT"; pick 2. Panel "Stand in the start box: north end zone" and a START marker; press **D-pad Down** (keyboard: `/mission start`) to teleport into the box. In the box: 3, 2, 1 (you are frozen), GO!, race fanfare, the **race music** (Koopa the Quick's), timer top right. Follow the blue CP markers: NE field corner → east field wall → east cross-aisle → east stands → east rim (coin lines, a Goomba on the walkway) → east rim south end → south-east rim (another Goomba) → south rim → South Ramp terrace (FINISH, a heart). The level music comes back at the finish. Under 1'10"00: "Finish! … - under par!" (under 0'45: "GOLD TIME!"), the star flies from the south scoreboard onto the terrace and the results board shows "Par 1'10   Gold 0'45"; grab it → 2 stars. Over par: "TRY AGAIN" and a new round; D-pad Down puts you back in the box (no 174 m walk). Note whether 1'10 and 0'45 feel fair (tune `par` / `gold` in `swamp_missions.lua`).
10. **Act 3 alone** (co-op gate): act select offers act 3 "GATOR CHOMP CHORUS - 2P". Enter alone with nobody else online: "This act needs 2 players - you are the only one online / Invite a friend to the game, or Pause > EXIT COURSE to go back". Pause → **EXIT COURSE**: you land outside the Auditorium (`0xF1` → `0x31`, death-exit animation, no life lost).
11. **A coming-soon act** (§5.1): `/campus swamp 4 me`. Banner "THE SWAMP - ACT 4 / COMING SOON - MASCOT / No mission here yet - explore! Pause > EXIT COURSE goes back."; panel "ACT 4: COMING SOON" for 20 s; no star, no invite to others. Pause → EXIT COURSE returns you outside the Auditorium. The act select shows act 4 only after act 3's star.
12. **100 coins**: in any act, collect 100 coins (there are 142, plus one per stomped Goomba; the climb, the concourse and the rim run alone have ~90): the vanilla 100-coin star (id 6) appears; grabbing it counts as a star of THE SWAMP.
13. **Exits and lives**: in any act, Pause → **EXIT TO CASTLE** → Plaza spin-in (`exitCastleWarpNode 0x0A`). Die once (drown in the Florida Pool east of the stadium): Mario is thrown out of the Auditorium door (`0x31`), −1 life, and the hub tops lives back up to 4.
14. **Remembered pick**: quit and host again: no menu; popup "Playing as <X>. L + START or /char to switch."; your friend's model; the NEXT panel ~1.5 s after landing.

### 10.2 With a friend (2 players; 3-4 for the bigger chorus)

1. **Join**: the friend joins and lands on the Plaza (act 0, same hub instance); their character select opens if their machine has no saved pick. Each sees the other as the picked friend. In the menu (L + START) the card of the other player's friend carries their name tag in their shirt colour; yours says YOU.
2. **Study Group invite** (`sgl_mission.lua`): the host walks into the Auditorium and starts act 1. The friend gets a popup "<Host> started THE SWAMP act 1: KICKOFF - CLIMB THE SKYBOX. D-pad Up or /join to follow!" and a 10 s prompt "D-pad Up: join <Host>". The friend presses D-pad Up (keyboard: type `/join` or Pause → Mods → "Join my study group"; the D-pad has no default key) and lands in the same act; you see each other. `/mission` on either → `players 2/2, leader <Host>` (smallest global index). The player list shows "THE SWAMP - Act 1: KICKOFF - CLIMB THE SKYBOX" and "Central Campus".
3. **A shared star, leaving together**: one of you grabs the roof star and leaves with the course-complete screen. The other sees the star vanish, the panel "Star collected by <name>" (no "Grab the star" or STAR marker left over, even if the grab came before the roof was reached on the leader's screen), and the prompt "<name> got the star! D-pad Up: back to campus together". D-pad Up takes the EXIT COURSE path: outside the Auditorium (`0x31`), no life lost. Both star counters go up by 1.
4. **Co-op act 3** (POUND mode): get both into act 3 (act select once the save has acts 1-2, or `/campus swamp 3` from the host, which moves everyone). After "Get ready…" (3 s) two end-zone corner buttons light up: north-west and south-east, with red flames (3 or 4 corners with 3 or 4 players). Each player stands on one: the flame turns blue and the switch squishes. Both held: the HUD counts "GA..." (1 s), "TOR..." (1 s), then "CHOMP!" + "POUND IT! (jump + Z)": both jump and ground-pound on their button within 1.3 s. Then "CHOMP! Phrase 1/3 - new corners are lit!": the north-east and south-west corners light up (47 m runs), then north-west + south-east again. After the third phrase the star flies from the south scoreboard to midfield. Pounding late, or stepping off during the count: "Off the beat!" and that phrase starts over (no fail). A player leaving the act gives "Paused: waiting for enough players".
5. **Race together** (act 2): both in the start box → countdown at once (one player in the box starts a 10 s lobby countdown). The results board lists both times. If one of you gives up and leaves the act, the results come at once; if one stays but never finishes, they come 45 s after the first finish.
6. **Leader hand-off**: in act 1 or 2 the host leaves (`/campus hub me`); the mission keeps running under the friend (`/mission` names the new leader). In act 3 it pauses until a second player is back.
7. **`/campus` is the host's**: the friend types `/campus swamp 2`: only the friend moves, with "Only the host moves everyone; warping just you."
8. **Late join**: a third player joins while you are in the Swamp: `/join <host name>` warps them straight into your act (the door's star lock still applies).
9. **Menu vs invite**: with an invite showing, open the character menu: the prompt is hidden and D-pad Up moves the cursor, it does not join.

Shortcuts for retesting: `/campus swamp 1|2|3 [me]`, `/campus hub`, `/campus where`, `/mission`, `/mission reset`, `/mission start`, `/mission list`, `/join [name]`.

---

## 11. Deviations and notes

- **Slot mapping vs game_design.md §2.1**: Marston is CCM (course 4) and Lake Alice JRB (course 3), not the reverse. The Century Tower interior is TTC (course 14), not HMC. Door stars follow the contract: Reitz 2, Marston 5, Lake Alice 8, Library West 14, Century Tower 20.
- **Return spawn yaw** faces the door (§4.1). It is the painting-warp convention, and the player still ends up outside the door facing away.
- **Extra hub nodes** beyond the contract: `0x0B` (Plaza death respawn) with hub `0xF1 → 0x0B` and `0xF0 → 0x0A`, so dying in the hub (drowning in a pond, for example) plays the vanilla death exit on the Plaza. The validator also wants every area to have `0xF1`.
- `exitCastleWarpNode = 0x0A` (Plaza spin-in). A return spawn would play the course-complete screen (`0x2i`) or cost a life (`0x3i`) after "Exit to castle".
- Design-doc act names with "(2P+)" are written "- 2P" (menu font).
- `/campus hub` uses act 0 (the old custom hub used act 1). Normal arrivals in the hub are act 0, and coopdx instances by act.
- Door visuals (flame scale 5, emblem sizes, label placement) are tuned from vanilla model sizes, not yet seen in game. Tweak the `DOOR_*` constants at the top of the door section in `levels.lua`.
- **Swamp act order vs game_design.md §7.1** (integration pass): the three built missions are acts 1-3 (Kickoff, Stair Sprint, Chomp Chorus); design acts 2, 4 and 6 are "COMING SOON" acts 4-6 until they are built (§5.1). With the design order (missions on 1, 3 and 5) the vanilla act select would never have offered act 3 or 5.
- **Act 1's star is a level-script star** (as design §7.1 asks) and the mission only tracks the climb (`levelStar = true`); acts 2 and 3 spawn theirs from the mission controller.
- **`data/uf/swamp_points.json` keeps the design act numbers** in its `actN_` keys (its notes give the mapping).
- **Collision seam repair** now runs split → weld → split (it used to weld first, which opened new cracks where it collapsed sliver triangles) and is on for the hub too; both levels were rebuilt with it (only `area_1/collision.inc.c` changed).
- **HUD layering**: hooks run in file load order, so `charselect.lua`'s menu is drawn first; every other HUD hook of the mod returns early while it is open (`sgl_hud_blocked`).
- **Review fix round** (all offline-checked, §12):
  - the "got" event ends a round from any live state and names the collector; a `levelStar` mission also ends when its star vanishes; the other players get the 10 s "back to campus together" prompt (§5, §6);
  - act 3 is a rhythm co-op test now (POUND mode, 3 phrases with moving corners) instead of a 3 s hold;
  - the act 2 race: no stall when a racer leaves (min(racers, players here)), results 45 s after the first finish at the latest, 4 s results, D-pad Down / `/mission start` back to the start box, gold time 0'45, race music;
  - act 1: route markers, compact panel; every marker shows as an edge arrow when off screen;
  - `/campus` moves everyone only for the host or a moderator (§8);
  - the hub door hint waits until the character menu is closed, plus a NEXT panel and marker;
  - the "Super Gatorlator 64 loaded" banner is gone;
  - level content (coins, hearts, 1-ups, Goombas, poles, music, bowl colours, orange camera decks, helix seams) through the generator (§9); the hub's two pond water boxes are clipped to the play zone (they reached 41 m and 19 m past the boundary walls); both levels rebuilt.
- **Not done in the fix round** (left for later, see the integration report): a live 3D preview in the character menu (needs in-game camera framing), crowd billboards / flags / crowd sound in the stands, hurdles or a shortcut on the race's rim run (2 Goombas stand in for them), the usher cannon shortcut of design §7.1, anything for a 5th+ player in act 3.
- Untested in game: everything above was checked offline (validator, `luac -p`, `tools/luatest`: bytecode global check, multi-client simulation of the whole mod against coopdx v1.5.1's real constants, bindings and struct fields, with the real level scripts). The lead's run of §10 is the real test.

---

## 12. Lua files: load order, hooks, shared globals

coopdx loads a mod's top-level `.lua` files in **strcmp order of the file names** (`mod.c` `mod_set_loading_order`) into one per-mod environment whose `__index` is the real `_G` (`smlua.c`). `_G.name = v` therefore lands in the real global table (shared with other mods); a bare global lands in the mod's environment. Both are visible to every file of the mod once assigned.

| # | File | Provides to other files | Uses from other files | Hooks / commands |
|---|---|---|---|---|
| 1 | `characters.lua` | `_G.sglFriends`, `_G.sglSetFriend` | `_G.sglOpenCharSelect`, `_G.sglOnFriendSet` (runtime, optional) | `MARIO_UPDATE` (model swap), `ON_SYNC_VALID`, `/char` |
| 2 | `charselect.lua` | `_G.sglOnFriendSet`, `_G.sglOpenCharSelect`, `_G.sglCharSelectIsOpen` | `_G.sglFriends`, `_G.sglSetFriend` (with fallbacks) | `BEFORE_MARIO_UPDATE` (eats the pad while open; L + START), `UPDATE`, `ON_SYNC_VALID`, `ON_WARP`, `ON_HUD_RENDER` (menu), mod menu "Choose your friend" |
| 3 | `course.lua` | `SGL_*` constants, `SGL_STAGES`, `sgl_stage_*`, `sgl_act_*`, `sgl_mission_star_id`, `sgl_total_stars`, `sgl_stage_star_flags` | | course and act names (at load) |
| 4 | `levels.lua` | `id_bhvSglDoor`, `id_bhvSglDoorFx`, `id_bhvSglTestGoal`, `SGL_HUB_SIGN_*`, `SGL_TEST_SIGN_BPARAM` (level scripts), `SGL_LEVELS`, `SGL_LIVES`, `SGL_FAR_UNITS`, `SGL_MAP_CENTERS`, `SGL_HUB_HINT_*`, `sgl_next_stage` | `course.lua` (at load), `sgl_hud.lua` (runtime) | `BEFORE_WARP`, `ON_LEVEL_INIT`, `ON_PACKET_RECEIVE` (`sgl = "warp"`, host / moderator only), `UPDATE` (far plane, hub hint), `MARIO_UPDATE` (lives), `ON_HUD_RENDER` (door labels, hub NEXT panel), `/campus` |
| 5 | `main.lua` | | | `ON_LEVEL_INIT` (welcome popup), `/school` |
| 6 | `sgl_hud.lua` | `SGL_HUD_*` colours, `sgl_hud_*` widgets (incl. `sgl_hud_fit`, `sgl_hud_edge_point`), `sgl_hud_blocked` | `_G.sglCharSelectIsOpen` (optional) | `UPDATE` (toast ages), `ON_HUD_RENDER` (toasts) |
| 7 | `sgl_mission.lua` | `SGL_MS_*`, `sgl_mission_*`, `sgl_party_*`, `sgl_exit_*`, `sgl_soon_act`, `sgl_is_pound_action`, `id_bhvSglMission`, `id_bhvSglMissionFx`, `id_bhvSglButton` | `course.lua`, `sgl_hud.lua` | `UPDATE` (controller spawner, coming-soon notice, invites, leave-together offer, player list), `ON_INTERACT` (star collected), `BEFORE_MARIO_UPDATE` (race countdown freeze), `MARIO_UPDATE` (D-pad Up: leave together / join; D-pad Down: back to the start), `ON_SYNC_VALID` (invite), `ON_PACKET_RECEIVE` (`sgl = "m"`, `"party"`), `ON_HUD_RENDER` (mission, coming soon, invite, leave together), `/mission`, `/join`, mod menu "Join my study group" |
| 8 | `swamp_missions.lua` | `SWAMP_POINTS`, `SWAMP_MISSION_ACTS` | `sgl_mission.lua` (at load) | (registers 3 missions) |

How the hooks share the frame:
- **HUD**: hooks of one mod run in registration order, i.e. file order, so the character menu (file 2) is drawn first. Every other HUD hook (door labels, hub NEXT panel, toasts, mission panel, coming-soon notice, invite and leave-together prompts) returns early while the game is paused or the menu is open (`sgl_hud_blocked()` in `sgl_hud.lua`). The hub hint also waits until the menu has been closed for 1.5 s before it starts.
- **Input**: `charselect.lua` clears the controller while its menu is open (Mario stands still, START does not pause, D-pad Up does not accept an invite or leave, D-pad Down does not teleport). The race countdown clears it too. Both only clear input, so the order does not matter. D-pad Up prefers "leave together" over an invite when both are up.
- **Packets** are told apart by their `sgl` field: `"warp"` (levels.lua, `/campus`), `"m"` (mission events) and `"party"` (Study Group invites, sgl_mission.lua).
- Chat commands (`/char`, `/campus`, `/school`, `/mission`, `/join`), mod menu buttons and behaviour names are unique; the simulator refuses duplicates.
- First spawn popups: the main.lua welcome and charselect's "Playing as …" (only with a saved pick) at once; the levels.lua door hint after the character menu (if any) is closed.

**Offline checks** (`tools/luatest/run.sh`, needs `lua`/`luac`; Python parts use `tools/.venv`):
1. `luac -p` on every file, and no Lua 5.4+-only syntax.
2. `check_api.lua`: every coopdx call exists in v1.5.1 with a valid argument count; every constant exists.
3. `check_globals.lua`: from the bytecode (`luac -l`), every global read resolves, load-time reads only use files earlier in the load order, no mod global shadows a coopdx name, no global is assigned by two files.
4. `test_missions.lua`: multi-client simulation of the framework and the Swamp missions (incl. the fix round: the pound chorus and its misses, a friend grabbing the level star before the leader saw the roof, the star vanishing without an event, leaving together through BOB `0xF1`, route markers and the compact panel, race dropouts / grace / teleport / music / gold, edge markers).
5. `test_flow.lua`: the whole mod (every file, strict globals) plus the real `levels/castle_grounds` and `levels/bob` scripts: door contract for all six doors, warp nodes and return spawns, the vanilla act select rule against the act names / missions / level-script stars, the single-player loop (door hint only after the menu), coming-soon acts, two players with invites, the pound chorus, leaving together and host-only `/campus`, the character menu over the other HUDs.
6. `check_swamp_points.py`: `SWAMP_POINTS` vs `data/uf/swamp_points.json`.
