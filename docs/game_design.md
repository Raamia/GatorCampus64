# Super Gatorlator 64: Game Design

Status: design v1 (co-op mission track). Target: sm64coopdx v1.5.1, built as a Lua + DynOS mod in `mods/sgl64/`.
Every feature here uses APIs in the v1.5.1 Lua docs (`docs/lua/*.md` at tag `v1.5.1`) or patterns already used by the bundled mods (arena, hide-and-seek, star-road, sm74, day-night-cycle).

**Scope note:** this is the original co-op and environment design. The current solo gameplay proposal supersedes its interior assumptions: only the Reitz Union and Marston Science Library are enterable. Library West, Century Tower, and all other campus buildings are exterior-only in the solo campaign. Use `docs/singleplayer_campaign.md` for gameplay planning; do not implement conflicting interior concepts from this older design.

---

## 0. TL;DR

- **The pitch:** You and up to 15 friends (realistically 2-6) play as each other on the real University of Florida campus, built at true 1:1 scale. The center of campus is the "castle". Building doors lead into stages instead of paintings. Stars are shared by everyone. "The Final Exam" waits on top of Century Tower.
- **Structure:** This is a total conversion, built the proven romhack way that star-road and sm74 use: DynOS `.lvl` files replace vanilla level slots. The hub replaces Castle Grounds, the 6 stages replace courses 1-6, and the finale replaces Bowser in the Sky. We get the act-select screen, star bookkeeping, the 100-coin star, exit/death warps and pause "Exit Course" for free.
- **Content:**
  - 6 stages × (6 missions + 1 "Team 100" coin star) = 42 stars
  - 7 hub secret stars
  - 2 stars in the Smathers bonus slide
  - 1 optional star in the finale approach
  - **52 stars** in total. The Final Exam opens at **30 stars**.
- **Co-op:** Every stage has one mission that needs 2-4 players. Every stage has a friendly race or competitive mode. Hide-and-seek is a Library West mission and also a free-play hub mode. You can still reach the 30-star finale solo (46 stars don't need a partner).
- **Smallest fun slice (build first):**
  1. Character select menu
  2. A mini hub (Plaza of the Americas + Century Tower + one door)
  3. The Swamp with 3 missions, one of them co-op ("Gator Chomp Chorus")

  See section 10.

---

## 1. Engine facts that shape the design

### 1.1 Scale (1 unit = 1 cm, Mario ≈ 161 units ≈ 1.6 m)

Mario's vanilla physics at true scale (jump peak ≈ v²/8, since gravity is 4 units/frame²):

| Move | Peak height | Real-world meaning |
|---|---|---|
| Single jump (42-50 u/f) | 2.2-3.1 m | over a car, onto a planter |
| Double jump (52-60 u/f) | 3.4-4.5 m | about one building floor |
| Triple jump / backflip / side flip / wall kick (62-69 u/f) | 4.8-6.0 m | 1.5 floors |
| Run speed (32 u/f × 30 fps) | 9.6 m/s | crosses the Plaza of the Americas (156 m) in ~16 s |
| Fall damage | falls > 11.5 m (1150 u) | a 3-4 floor drop hurts |

Consequences:

- **Facades need ledges every ~3 m** (window sills, balconies, awnings) to be climbable.
- **5-8 storey roofs (18-30 m) need a route:** stairs, ramps, moving lifts, cannons, vertical wind or a Wing Cap. Real buildings in the data:
  - Reitz Union: 8 levels
  - Malachowsky Hall: 7 levels
  - Stadium West Skybox Tower: **66 m**
  - Century Tower: **47.9 m**
- **Pacing:**
  - Hub cross-walks are 20-40 s (Plaza → Century Tower ≈ 190 m ≈ 20 s; Tower → The Hub ≈ 225 m).
  - Add fast travel (bus stops, cannons, shells).
  - Size races at 200-450 m (30-60 s).
- **Stadium risers** (~40-50 cm steps): model them as visual steps over smooth **ramp collision**, so walking up the stands feels good.
- **Render/collision budget:**
  - Level bounds are ±327 m, so every stage must fit in a 654 m square.
  - Collision cap is 16,384 triangles including dynamic objects: buildings get box collision, and detail stays visual only.
  - Turn on `gBehaviorValues.InfiniteRenderDistance = 1` and use `set_override_far(...)` / a large `GEO_CAMERA_FRUSTUM` far plane for the outdoor stages.

### 1.2 Co-op rules of coopdx we design around

- **Instances:** Players only see each other and share objects when they are in the same **level + area + act**. coopdx's collect-star packet checks `currCourseNum/currActNum/currLevelNum/currAreaIndex`. So every co-op mission needs the group in the same act. We add a "Study Group" invite system (§6.11).
- **Stars are shared automatically.** `network_send_collect_star` broadcasts every collection, and every client calls `save_file_collect_star_or_key`. Progress lives in the **host's save slot** (sent to joiners).
- **Star spawning is local and driven by synced state.** The coop pattern (vanilla red-coin star, star-road's hidden star) is: synced state reaches "done", then each client's controller object spawns the star itself (`spawn_default_star` / `spawn_red_coin_cutscene_star` / `spawn_no_exit_star`, which read the star id from the calling object's `oBehParams >> 24`). coopdx matches the collection by position across clients.
- **Object ownership:** `network_init_object(o, true, …)` (standard sync) is owned by the **nearest player in the area** (`sync_object_should_own`). Use it for physics objects that players push or carry. Use `network_init_object(o, false, fields)` + `network_send_object(o, true)` for mission controllers written by our own "instance leader" (§6.1).
- **The host may not be in the stage.** Mission logic must never assume the host is present. Authority belongs to the instance leader.
- **`gServerSettings` desyncs if changed later:** set it only at mod-load top level (same on all clients).
- **Mod download cap:** joiners download the mod; `MAX_MOD_SIZE` is **35 MB** (`src/pc/mods/mods.h`). Ship precompiled `.bin/.lvl/.tex` like the bundled mods do, not Fast64 `.c` sources.

---

## 2. How the game maps onto coopdx

### 2.1 Level slots

| Course # | Our stage | Replaces (DynOS file) | Hub door | Stars to open | Real-world anchor (campus.json, m) |
|---|---|---|---|---|---|
| hub | **Central Campus** (Plaza of the Americas ↔ Century Tower ↔ Turlington) | `level_castle_grounds_entry.lvl` | (spawn) | 0 | origin ≈ (-40, 90); Plaza (61,181), Tower (0,0) |
| 1 | **The Swamp** (stadium district, gameday) | `level_bob_entry.lvl` | University Auditorium | 0 | stadium relation centered (-534,134), 224×280 m |
| 2 | **Reitz Union & Engineering Quad** | `level_wf_entry.lvl` | The Hub | 2 | Reitz (-441,-289), Weil (-497,-56), Malachowsky (-432,-532) |
| 3 | **Marston Science Library** (interior) | `level_jrb_entry.lvl` | Marston | 5 | 57×57 m, 5 levels |
| 4 | **Lake Alice** | `level_ccm_entry.lvl` | Newell Hall | 8 | bat houses (-1882..-1908, -510); lake center ≈ (-1750,-633)* |
| 5 | **Library West After Dark** (interior) | `level_bbh_entry.lvl` | Library West | 14 | 80×65 m, 5 levels |
| 6 | **Century Tower** (interior, "bigger on the inside") | `level_hmc_entry.lvl` | Century Tower base | 20 | 9×9 m, 47.9 m tall |
| bonus | **Smathers Stacks Slide** | `level_pss_entry.lvl` (COURSE_PSS) | Smathers Library | 3 | — |
| finale A | **Finals Week Ascent** | `level_bits_entry.lvl` | "Final Exam" door at Century Tower | 30 | — |
| finale B | **The Final Exam** (boss arena above the tower) | `level_bowser_3_entry.lvl` | pipe at end of finale A | — | — |

\* The Lake Alice water polygon is **missing** from `campus.json`. `osm_extract.py` only keeps `building` relations, and the lake is a multipolygon relation. Wikipedia's coordinates (29.6431, -82.3614) put the lake center at ≈(-1750,-633) m, next to the bat houses. That is **not** the (-1136,-771) conservation-area figure. See §11.

Why these slots:

- **BBH** already holds the Boo/Big Boo star logic, which fits a haunted late-night Library West.
- **CCM** holds `RacingPenguinTrajectory` and the Tuxie's-mother logic, which we can reuse for Lake Alice races and the "return the hatchling" mission.
- **BOB** holds Koopa-the-Quick's `KoopaBobTrajectory` for the stadium race.

The other slots are unused.

### 2.2 Global settings (top level of a new `a-sgl-constants.lua` / `sgl-levels.lua`)

```lua
gLevelValues.entryLevel        = LEVEL_CASTLE_GROUNDS   -- spawn in the hub
gLevelValues.exitCastleLevel   = LEVEL_CASTLE_GROUNDS   -- pause > Exit Course returns to the hub
gLevelValues.exitCastleArea    = 1
gLevelValues.exitCastleWarpNode = 0x0A                  -- Plaza of the Americas spawn
gLevelValues.fixCollisionBugs  = 1
gBehaviorValues.InfiniteRenderDistance = 1
gServerSettings.skipIntro = 1
gServerSettings.stayInLevelAfterStar = STAR_STAY_IN_LEVEL  -- groups stay together after a star (host can override, see §3.5)
camera_set_romhack_override(RCO_ALL_EXCEPT_BOWSER)
camera_set_use_course_specific_settings(false)
smlua_text_utils_course_acts_replace(COURSE_BOB, " 1 THE SWAMP", "KICKOFF: CLIMB THE SKYBOX", ...)  -- per course
smlua_text_utils_castle_secret_stars_replace("   CAMPUS SECRETS")
```

`main.lua` needs `-- incompatible: romhack` in its header once the level replacements ship (a shared file, so the lead does this; see §11).

### 2.3 Warp nodes (convention for the level-building tracks)

- **Hub (Castle Grounds, area 1):**
  - `0x0A` = Plaza spawn.
  - For stage *n*: `0x2n` = success/exit return (in front of that stage's door), `0x3n` = death return.
  - Door warp objects (`bhvDoorWarp`, 2nd behParam byte = node id) use `WARP_NODE(0x0n, LEVEL_<stage>, 1, 0x0A, …)`.
- **Each stage:**
  - `0x0A` = entry spawn.
  - `WARP_NODE(0xF0, LEVEL_CASTLE_GROUNDS, 1, 0x2n)`, `WARP_NODE(0xF1, …, 0x3n)`, `WARP_NODE(0xF3, …, 0x2n)`.
  - The return nodes get `bhvPaintingStarCollectWarp` / `bhvPaintingDeathWarp` spawn objects in the hub, the way the custom-level example and star-road do it.

### 2.4 Star bookkeeping

| Where | Save slot | Bits |
|---|---|---|
| Stage *n*, act *a* | course *n* | star index *a−1* (0-5) |
| Stage "Team 100" | course *n* | index 6 |
| Hub secrets | castle secret stars (course −1, max **7**) | 0-6 |
| Smathers slide | COURSE_PSS | 0-1 |
| Finals Week Ascent red coins (optional) | COURSE_BITS | 0 |

Doors check the shared total `gMarioStates[0].numStars`. coopdx refreshes it for every player on each collect.

### 2.5 New files (nothing existing gets edited)

`mods/sgl64/` loads every `.lua` alphabetically into one shared environment. The arena mod uses an `aa-` prefix to load first.

- `a-sgl-constants.lua`: slot mapping, star thresholds, packet ids, custom object fields (`define_custom_obj_fields`)
- `charselect.lua`: character select menu (§4). Loads after `characters.lua`.
- `sgl-levels.lua`: text, `gLevelValues`/`gBehaviorValues`, door locks, `HOOK_USE_ACT_SELECT`
- `sgl-party.lua`: instance/leader helpers, Study Group invites, regroup
- `sgl-mission.lua`: mission controller behavior, state machine, star spawn, Team 100 coin pot
- `sgl-hud.lua`: banners, timers, objective markers, results board
- `sgl-race.lua`, `sgl-hideseek.lua`: reusable game modes
- `sgl-stage-swamp.lua`, `sgl-stage-reitz.lua`, `sgl-stage-marston.lua`, `sgl-stage-alice.lua`, `sgl-stage-libwest.lua`, `sgl-stage-tower.lua`, `sgl-hub.lua`, `sgl-final-exam.lua`
- `textures/portrait_<id>.png`: 10 portraits (§4); `sound/` holds samples and music

---

## 3. Session flow (the game flow, start to finish)

```
Host launches coopdx ─► Host: picks save slot, enables ONLY "Super Gatorlator 64", opens lobby
Friends ─► Join (CoopNet lobby w/ password, or direct IP) ─► mod auto-downloads (<35 MB)
   │
   ▼
Spawn in hub (Plaza of the Americas) ─► Character Select overlay (first time; else auto-applies saved pick)
   │
   ▼
Explore hub ─► hub secrets, bus stops, free-play hide-and-seek, Gator Chomp emote
   │
   ▼
Walk into a building door ─► locked? popup "Marston opens at 5★ (you have 3★)"
   │ unlocked
   ▼
Act select ("Syllabus") ─► pick an act; coopdx shows which friends are in which act
   │                       └─► everyone else in the hub gets a "Study Group" invite → D-pad Up joins the same act
   ▼
Mission (HUD banner + objective) ─► star spawns ─► star shared to everyone's count
   │      └─ group stays in the stage (stay-in-level) or exits to the door it came from
   ▼
Star thresholds open new doors (2/5/8/14/20) ─► Century Tower bells ring at 30★
   ▼
Finals Week Ascent ─► The Final Exam (boss) ─► Grand Star ─► "Graduation" credits with the 10 friends
   ▼
Post-game: 52★ "Summa Cum Laude" (nametag title + confetti), hub free play, race records
```

### 3.1 Lobby / join

- **Host:**
  1. Host → choose a save slot (this slot **is** the group's shared progress).
  2. Mods: enable only Super Gatorlator 64. It is a romhack-class mod, and the gamemode mods (Arena, Hide and Seek) are incompatible.
  3. Recommended settings: Player Interactions = Solid; Bubble on death = On (teammates pop you back); Stay in level after star = Stay.
- **Friends:** Join → lobby → password. coopdx sends the mod files, then the host's save.
- **Join presence:** when a friend joins, `HOOK_ON_PLAYER_CONNECTED` shows a popup ("Corina joined the study group!"). The Century Tower carillon chimes (`audio_sample_play`).
- **Location display:** `network_player_set_override_location(np, "The Swamp · Gator Chomp Chorus")` makes the player list show which stage and mission each friend is in.

### 3.2 Character select

On first spawn, an overlay opens when there is no saved pick (§4). After that, `mod_storage_load("friend")` re-applies the saved pick automatically. A hint shows: "D-pad Down: change friend".

### 3.3 Hub arrival

Spawn at the center of the Plaza of the Americas, facing south toward Century Tower. Library West's doors are behind you.

- **First time ever (host's save has 0★):** a 10-second "campus tour" camera pans from the Plaza to the tower. The Auditorium door pulses with a "Start here" marker.
- **HUD:** a corner widget shows the next unlock, e.g. "Next: The Hub opens at 2★".

### 3.4 Doors → act select → Study Group

- **Doors** are `bhvDoorWarp` objects with building-specific door models (glass double doors, the Auditorium's arched doors, the Century Tower base door).
- **Locks:** `HOOK_ALLOW_INTERACT` returns `false` for `INTERACT_WARP_DOOR` while `numStars <` the threshold. It also shows a `djui_popup_create` with the requirement. The door model gets a padlock decal.
- **Act select:** the vanilla screen ("Syllabus"). Act names come from `smlua_text_utils_course_acts_replace`. Co-op-required acts end in `(2P+)`. `HOOK_USE_ACT_SELECT` returns true for courses 1-6.
- **Study Group invite:** the first player to enter a stage act sends a reliable `PKT_PARTY` packet {level, act, missionName}.
  - Players in the hub (or idle elsewhere) get a 10 s prompt: "Raami opened THE SWAMP · Act 3 GATOR CHOMP CHORUS (2P+). D-pad Up to join".
  - Accepting calls `warp_to_level(level, 1, act)`, which skips act select.
  - The pause-menu button "Join my study group" (`hook_mod_menu_button`) and the chat command `/join <name>` do the same.

### 3.5 Missions → stars

- **Mission start:** a banner ("ACT 3 · GATOR CHOMP CHORUS"), a one-line objective and, for co-op acts, a "Players here: 1/2 needed" panel that holds the mission until enough friends arrive.
- **Star collected:** the shared count goes up, and every client shows "Daniel got a star! (13★)". Bells chime in the hub.
- **Default "Stay in level":** the group keeps playing the same act or opens the pause menu. Leaving through the door returns you to that stage's door in the hub (`0x2n`).

### 3.6 Unlock thresholds

| Stars | Unlocks |
|---|---|
| 0 | The Swamp (Auditorium door) |
| 2 | Reitz Union & Engineering (The Hub door) |
| 3 | Smathers Stacks Slide (bonus) |
| 5 | Marston Science Library |
| 8 | Lake Alice (Newell Hall). Newell was the agricultural experiment station building, so bugs → bats. |
| 12 | Hub TA star #1 (Toad-style NPC) |
| 14 | Library West After Dark |
| 20 | Century Tower interior. Wing Cap box appears in the hub (needed for the rooftop red coins). |
| 25 | Hub TA star #2 |
| 30 | **The Final Exam** (bells ring, the hub sky shifts to "finals week" night) |
| 52 | "Summa Cum Laude" title + graduation confetti in the hub |

Math check:

- There are 6 co-op-required missions, so a solo player can earn 46 stars. 30 is reachable solo; co-op makes it much faster.
- A 2-hour session with 3-4 friends should earn roughly 15-20 stars.
- The finale is about a 3-session arc.

### 3.7 Finale and graduation

- At 30★, a star-door-style "FINAL EXAM" door at the Century Tower base opens into **Finals Week Ascent** (§8.2), then a pipe to **The Final Exam** boss (§8.3).
- **Grand Star:** a "Graduation" sequence plays: fireworks over the hub, then a HUD credits roll with the 10 friends' portraits and names, plus "Map data © OpenStreetMap contributors (ODbL)".

### 3.8 Post-game

- **Persists on each client (`mod_storage`):** race records, hide-and-seek wins.
- **Hub free play:** hide-and-seek and the Plaza Dash stay open.

---

## 4. Character select menu (10 friends, portraits, synced)

**Data**
- Friend roster comes from `characters.lua`. The model swap and sync already work there through `gPlayerSyncTable[i].friend`, an index into `FRIENDS`.
- Proposal: `characters.lua` exposes `_G.sglFriends = FRIENDS` (one line). Without that, `charselect.lua` must duplicate the ordered id list (fragile).
- `charselect.lua` only writes `gPlayerSyncTable[0].friend`.

**Portraits**
- Source: `art/<id>/build/previews/head.png` (all 10 exist, 768×768).
- Downscale to 64×64 (macOS `sips`, no install) → `mods/sgl64/textures/portrait_<id>.png`.
- Draw with `get_texture_info("portrait_<id>")` + `djui_hud_render_texture`.
- The custom-hud-texture example ships both `.png` and `.tex`. Ship the `.tex` too if the PNG does not load on clients.

**Layout (`djui_hud_set_resolution(RESOLUTION_N64)`, 320×240 virtual)**
- Title bar: "WHO ARE YOU TODAY?" in orange-on-blue. No UF logos.
- A 5×2 grid of 52×52 portrait cards with the name below each.
- Focused card: scaled 1.15× with a gold border and a slow bob.
- Under each card: small colored dots (`network_get_player_text_color_string`) for every connected player who picked that friend, so you can see "Anh is being Daniel".
- Right/bottom strip: the focused friend's name, tagline (from `art/<id>/character.json` signature traits, e.g. "big voluminous curls") and "A: Pick  B: Back  START: Random".
- **Live preview:** while the cursor moves, your **own in-world model** swaps locally (`obj_set_model_extended` on `gMarioStates[0].marioObj`). The camera is held with `camera_freeze()` facing you. This is local only until you confirm.

**Input**
- D-pad or stick with auto-repeat; A to confirm; B to close (only if you already have a pick); START for random.
- Mouse: `djui_hud_get_mouse_x/y`, `djui_hud_get_mouse_buttons_pressed`, `djui_hud_set_mouse_locked(false)` while open.
- While open, `HOOK_BEFORE_MARIO_UPDATE` zeroes the local `m.controller.buttonPressed/buttonDown/stickX/stickY`, and `hud_hide()` hides the vanilla HUD.

**Sync and rules**
- Confirm sets `gPlayerSyncTable[0].friend = index`, which syncs to everyone. Also `mod_storage_save("friend", id)`.
- Duplicates are allowed by default (two people can both be Raami). A host-only mod-menu checkbox "One friend per player" (`hook_mod_menu_checkbox` → `gGlobalSyncTable.uniqueFriends`) greys out taken cards.
- Race resolution: `hook_on_sync_table_change` on each player's `friend`. If two players hold the same pick, the lower `globalIndex` keeps it and the other gets a popup and the reopened menu.
- `HOOK_ON_PLAYER_DISCONNECTED` frees picks automatically, since sync entries reset.

**Ways to open it**
- First spawn
- `/char` with no args (the existing command keeps working)
- Pause → mod menu "Change friend" (`hook_mod_menu_button`)
- D-pad Down while standing in the hub
- A "Gator ID card kiosk" object in the Plaza

**Difficulty:** S/M. Pure Lua + 10 PNGs. **Build this first.**

---

## 5. The Hub: Central Campus (replaces Castle Grounds)

**Footprint** (origin ≈ (-40,90) m, which fits ±327 m):

| Place | Center (m) |
|---|---|
| Library West | (38,287) |
| Smathers | (143,227) |
| Plaza of the Americas | (61,181), 156×134 m |
| Criser | (160,155) |
| Griffin-Floyd | (-45,143) |
| Century Tower | (0,0) |
| University Auditorium | (37,22) |
| Turlington | (-77,35) |
| Newell | (-180,26) |
| The Hub | (-213,-74) |
| Marston | (-62,-96) |
| Music Bldg | (39,-66) |
| Dairy Pond | (-121,-162) |
| Gator Pond | (195,-65) |

**Role:** Peach's castle grounds. You can reach everything on foot. The tower is the landmark you see from everywhere, and the stage doors are the building entrances.

**What's there**

- **Stage doors:** Auditorium (Swamp), The Hub (Reitz/Engineering), Marston, Newell (Lake Alice), Library West, Century Tower, Smathers (slide). Each has a plaque: stage name, stars required, and stars earned there (`save_file_get_star_flags`).
- **Century Tower clock = progress meter:**
  - The hour hand points at total stars / 52.
  - The carillon plays a short chime on every star (`audio_sample_load/play`, triggered from `hook_on_sync_table_change` or the star-count change).
  - Century Tower is a real memorial (UF centennial and alumni lost in the World Wars). Keep the tower base calm and respectful: no enemies, and the boss fight happens in a separate sky arena.
- **Fast travel:** 4 campus bus stops (original livery, not RTS branding) at the Plaza, Turlington, Newell/The Hub, and Marston. Stand on one and press B: fade (`play_transition`) and teleport (`obj_set_pos`/`m.pos`) to the next stop. Local only, nothing to sync. **S**.
- **Gator Chomp emote** (anywhere): D-pad Left plays the chomp arm animation (a custom action via `hook_mario_action`, optional custom animation via `smlua_anim_util_register_animation`). Everyone sees it because actions sync. It is a social toy and also the input for the Swamp co-op mission. **S**.
- **Free-play hide-and-seek** (host toggle in the mod menu): seekers vs hiders inside the Plaza + Library West/Smathers exteriors. Uses `sgl-hideseek.lua` (§6.7). No star. Wins are recorded locally.
- **Plaza Dash** (any time): a start arch at the Plaza runs a loop around the Plaza, past Smathers, through the Criser arcade and back. It tracks every player's time (§6.6). Records are kept locally.

**Hub secret stars** (castle secret stars; vanilla allows exactly 7 bits):

1. **The Bold Squirrel (S/M).** A Plaza squirrel stole a granola bar. Chase and dive-catch it.
   - Implementation: a custom rigid-model behavior that flees the nearest player (`nearest_mario_state_to_object`) along hop arcs and is "caught" on dive or punch contact (`obj_check_if_collided_with_object`). Then the controller spawns the star.
   - Sync: standard sync (the nearest player owns it).
   - Co-op: two players can corner it much faster.
   - Fallback: vanilla `bhvMips` with `gBehaviorValues.trajectories.MipsTrajectory` set to a custom path, presented as an "escaped lab bunny". It uses the vanilla rabbit model, so no reskin is needed.
2. **Turlington Tabling Gauntlet (M).** Cross Turlington Plaza from the Turlington steps to Newell without getting flyered.
   - Cheerful original "tabler" NPCs with clipboards step into your path. A touch makes a flyer stick to your HUD and causes a 1.5 s stun (`set_mario_action(m, ACT_HARD_BACKWARD_GROUND_KB, 0)`).
   - Arrive with fewer than 3 flyers and the star spawns at the finish.
   - Co-op: tablers lock onto the nearest player, so friends can decoy.
   - Sync: tablers use standard sync; the flyer count is local; reaching the finish sends a packet that tells the leader to set the controller to done.
3. **Five Bell Notes (S).** Five floating bell-note pickups hidden on campus (on top of the Auditorium arches, on the Gator Pond island, inside the Criser arcade, on the Library West entrance canopy, at the Music Building courtyard). Vanilla `bhvHiddenStarTrigger` + `bhvHiddenStar` with a note model swap. coopdx already syncs it.
4. **Rooftop Red Coins (M).** 8 red coins on the Library West, Smathers, Criser and Auditorium rooftops. Needs the Wing Cap box that appears at 20★ (`bhvExclamationBox`, Wing Cap param, spawned by Lua when `numStars >= 20`) or a cannon on the Plaza. Vanilla `bhvRedCoin` + `bhvHiddenRedCoinStar`.
5. **Plaza Dash par time (S).** Finish the Plaza Dash under par. The first friend to do it spawns the star at the arch.
6. **TA Office Hours #1 (S).** A Toad-style NPC TA in the Auditorium portico gives a star at 12★ (`bhvToadMessage` + `gBehaviorValues.ToadStar1Requirement = 12`; dialog via `smlua_text_utils_dialog_replace`). Model: a simple original NPC, or keep the Toad model.
7. **TA Office Hours #2 (S).** In the Marston entry plaza at 25★ (`ToadStar2Requirement = 25`).

---

## 6. Mission framework (shared tech every mission uses)

### 6.1 Instance and leader

```lua
-- same on every client; never assumes the host is present
function sgl_instance_key(np) return np.currLevelNum .. ":" .. np.currAreaIndex .. ":" .. np.currActNum end
function sgl_instance_players()       -- local indices of connected players in my instance
function sgl_is_leader()              -- true if I have the smallest globalIndex among them
```

- The leader runs the authoritative tick (`HOOK_UPDATE`). When it leaves, the next-smallest index takes over seamlessly, because state lives in synced objects.
- "Players here" is `#sgl_instance_players()` (counts only `currAreaSyncValid` players). It drives co-op gating and HP scaling.

### 6.2 Mission controller object

- **Hooking:** `id_bhvSglMission = hook_behavior(nil, OBJ_LIST_DEFAULT, true, init, loop, "bhvSglMission")`. DynOS level scripts reference Lua behaviors by name, the way the arena levels use `id_bhvArenaKoth`.
- **Placement:** `OBJECT_WITH_ACTS(MODEL_NONE, x,y,z, 0,0,0, (starId<<24)|(missionId<<16), id_bhvSglMission, ACT_n)`.
- **Fields:** `define_custom_obj_fields({ oSglState='u32', oSglProgress='u32', oSglTimer='u32', oSglFlags='u32', oSglAux='u32' })`, then `network_init_object(o, false, {'oSglState','oSglProgress','oSglTimer','oSglFlags','oSglAux'})`.
- **Writes:** only the leader changes fields, then calls `network_send_object(o, true)` on each **state change**. Timers sync at 1 Hz in seconds, like hide-and-seek's `displayTimer`.
- **States:** `WAITING_FOR_PLAYERS → INTRO → ACTIVE → SUCCESS → DONE` (or `FAILED → INTRO`).
- **Star:** on `SUCCESS`, **every client** spawns the star once from inside the loop (`spawn_default_star(x,y,z)` or `spawn_red_coin_cutscene_star`), then sets a local "spawned" flag. If the star is already collected (`save_file_get_star_flags(...) & (1<<starId)`), spawn a transparent "already got it" star (vanilla behavior) so replays still work.
- **Stale state:** if a client enters and finds itself alone in the instance with a non-`WAITING` state, it resets the controller.

### 6.3 Events (packets)

- `network_send(true, { id = PKT_X, ik = instanceKey, ... })`, received via `HOOK_ON_PACKET_RECEIVE`. Receivers ignore other instances, and only the leader applies authoritative effects.
- Reliable sends are only for discrete events (hits, button presses, finish times, phase changes).
- Continuous data (operator stick values, boss position) goes unreliable at 10-15 Hz.

### 6.4 Per-player sync fields (`gPlayerSyncTable[i]`)

| Field | Meaning |
|---|---|
| `friend` | existing character pick |
| `role` | 0 none, 1 seeker, 2 hider, 3 operator … |
| `ready` | race start box |
| `chomp` | last beat index hit |
| `raceFrames` | finish time |

Keep `gGlobalSyncTable` for session-wide things only: `uniqueFriends`, `hubHideSeek`, `hubHnsState`, `hubHnsTimer`.

### 6.5 HUD kit (`sgl-hud.lua`)

- Mission banner, objective counter, timer, "Players here x/N needed" panel, results board.
- Objective markers: `djui_hud_world_pos_to_screen_pos` + a small arrow texture.
- Everything is drawn in `HOOK_ON_HUD_RENDER` at `RESOLUTION_N64` (same style as `main.lua` and hide-and-seek).

### 6.6 Race module (`sgl-race.lua`, for all friendly races)

1. **Start box:** a `mario_is_within_rectangle` area sets `ready`. The leader starts when all players in the instance are ready, or 10 s after the first is ready.
2. **Start:** a reliable `PKT_RACE_GO` carries a 3-2-1 countdown that every client renders. Players in the box are held (input zeroed) until GO.
3. **Track:** checkpoints are custom invisible trigger objects in order (no sync). Local timing goes into `raceFrames`, plus a reliable `PKT_RACE_FINISH`.
4. **Star rule:** the star spawns at the finish for the first finisher if they beat par, or for whoever beats the NPC (Koopa-the-Quick races). Stars are shared anyway, so the race is for bragging rights.
5. **Records:** `play_race_fanfare()`, a results board, and personal bests in `mod_storage_save`.

### 6.7 Hide-and-seek module (`sgl-hideseek.lua`)

- Adapted from the bundled `hide-and-seek.lua`: round state machine, random seeker pick, seekers drawn metal (`m.marioBodyState.modelState |= MODEL_STATE_METAL`), touch-tag via `HOOK_ON_INTERACT` with `INTERACT_PLAYER`.
- Differences from the bundled mod:
  - The leader runs it, not the server.
  - It is scoped to one instance, keyed by a controller object.
  - Rounds are 150 s.
- `HOOK_ALLOW_PVP_ATTACK` returns `false` everywhere except seeker→hider during a round, so the rest of the game stays friendly.
- This needs player interactions of at least Solid. Set `gServerSettings.playerInteractions` at mod load, or show a host warning if it is "None".

### 6.8 Co-op gating

- Each mission declares `minPlayers` / `maxPlayers`.
- Below `minPlayers`, the controller stays in `WAITING_FOR_PLAYERS`, and the HUD says "Needs a study buddy: 1/2. Invite a friend (pause > Invite)".
- Requirements and HP scale with players here, e.g. `targets = base + perPlayer * (n-1)`.

### 6.9 Team 100 (7th star in every stage)

- `HOOK_ON_INTERACT` on `INTERACT_COIN` sends the coin value to the leader, which adds it to the controller's `oSglProgress`. At 100 the star spawns.
- This avoids depending on whether coopdx coin counts are per-player.
- Set `gLevelValues.coinsRequiredForCoinStar = 999` in our courses so the vanilla per-player coin star doesn't double up.

### 6.10 Reskin policy (important for art cost)

- **Rigid vanilla actors can be reskinned cheaply:** swap the model with `obj_set_model_extended` in `HOOK_OBJECT_SET_MODEL`, or in a non-replacing `hook_behavior(id_bhvX, list, false, init)`. Examples: red coins, Bullet Bills, shockwave rings, boxes, platforms, Thwomps.
- **Animated vanilla actors** (King Bob-omb, Bubba, penguins, Mips, Bowser…) need a replacement model rigged to **that actor's skeleton** (like our friends use the Mario rig). That is L art. Prefer one of:
  - (a) keep the vanilla model when it fits: Swoopers *are* bats, Skeeters are water striders, Boos fit the haunted library, cheep-cheeps are fish;
  - (b) write our own Lua behaviors with simple rigid models animated in code (`obj_scale_xyz`, bobbing, two-part jaws).
- **No real people** other than the 10 friends. No UF logos, no Albert/Alberta likeness, no brand names. Use original "gator statue" stand-ins. Real places are fine.

### 6.11 Party / Study Group (`sgl-party.lua`)

- **Invite:** `HOOK_ON_LEVEL_INIT` into a course act sends a reliable `PKT_PARTY {level, act, mission, gi}`. Recipients outside that instance get a 10 s prompt; D-pad Up runs `warp_to_level(level, 1, act)` after checking the door lock locally.
- **Regroup:** `hook_mod_menu_button("Join my study group")` warps to the instance with the most friends.
- **Location:** `network_player_set_override_location` shows mission names in the player list.

---

## 7. Stages and missions

Format per mission: **Goal · Co-op · Reuses · Lua · Sync · Difficulty**.
Difficulty: **S** ≈ ≤1 day of Lua on vanilla objects; **M** ≈ 2-4 days with a small custom behavior; **L** ≈ a week or more, or needs custom anims/boss/art. "+art" marks a notable modelling cost beyond the stage itself.

### 7.1 Course 1: The Swamp (gameday) · door: University Auditorium · 0★

**Real geography** (campus.json; level origin ≈ (-540,150) m):

| Feature | Location / size |
|---|---|
| Stadium (building relation) | centered (-534,134), 224×280 m |
| West Skybox Tower | 66 m |
| Bull Gator Deck | 52 m |
| Sunshine Seats | 46 m |
| South Ramp | 12 m |
| Field | (-514,122) |
| Exactech Arena | (-754,67) |
| Florida Gym | (-383,58) |
| Stadium Lawn | (-490,288) |
| Courtyard of Champions | (-513,279) |
| Tailgating lots | north |
| Bronze-gator statue spots | (-608,-3), (-585,386): use original gator statues |

**Look:** a game-day afternoon: orange-and-blue crowds (billboard sprites), confetti, a giant scoreboard. Music: an upbeat fight-song-style original track (`smlua_audio_utils_replace_sequence` or `audio_stream_load`).

1. **Kickoff: Climb the Skybox** (Act 1)
   - **Goal:** reach the roof of the 66 m West Skybox Tower. Route: field → tunnel → concourse ramps → upper deck → catwalks → light-tower ladder (pole). An usher NPC (`bhvBobombBuddyOpensCannon`) opens an end-zone cannon that shortcuts to the upper deck.
   - **Co-op:** any count. Whoever reaches the usher first opens the cannon for everyone (save flag).
   - **Reuses:** cannon (`bhvCannonClosed`), poles, Goombas as "rowdy rival fans" (vanilla model), Bob-omb Buddy dialog.
   - **Lua:** text only (`smlua_text_utils_dialog_replace`); star placed in the level script.
   - **Sync:** vanilla.
   - **S**
2. **The Visiting Mascot** (Act 2)
   - **Goal:** a giant inflatable rival mascot (an original goofy bird, rigid model) bounces around midfield squashing players. When it lands it wobbles for 3 s with its 3 air valves exposed at its feet; ground-pound a valve to deflate it a notch.
   - **Co-op:** valves needed = 3 + (players−1). Valves on different sides let several players hit in one wobble window.
   - **Reuses:** shockwave on landing (`spawn_non_sync_object(id_bhvBowserShockWave, …)`), mist particles.
   - **Lua:**
     - custom `hook_behavior` boss with collision (`obj.collisionData = smlua_collision_util_get(...)`, `load_object_collision_model()`)
     - valve detection via `cur_obj_is_mario_ground_pounding_platform` on child valve objects
     - `obj_scale_xyz` squash-and-stretch; `spawn_default_star` on defeat
   - **Sync:** leader-driven boss (`network_init_object(o,false,{pos,action,hp})`, 10 Hz unreliable position + reliable state); valve hits by packet.
   - **M** (+art: one rigid model)
3. **Gator Chomp Chorus (2P+)** (Act 3, **co-op required**)
   - **Goal:** in the student section, 2-4 "spirit pads" face the giant scoreboard. A beat bar scrolls on the HUD. On every CHOMP beat, everyone on a pad does the Gator Chomp (B → chomp action) within ±0.2 s. Land 8 good phrases in a row (a miss costs 2) and the scoreboard drops the star.
   - **Co-op:** pads active = players here (2-4). One player can't fill two pads.
   - **Reuses:** crowd sound samples; the chomp emote from §5.
   - **Lua:**
     - `hook_mario_action(ACT_SGL_CHOMP, …)` + optional `smlua_anim_util_register_animation`
     - the leader sends a reliable `PKT_PHRASE {n}`; each client starts its local beat clock on receipt (no clock sync needed)
     - timing is judged **locally** (no latency penalty) and the result goes to the leader via a reliable `PKT_CHOMP {phrase, ok}`
     - HUD beat bar via `djui_hud_render_rect`
   - **Sync:** controller `oSglProgress` = streak.
   - **M**
4. **Tailgate Tokens** (Act 4)
   - **Goal:** 8 red coins reskinned as orange/blue pennant tokens. Locations: tailgate canopies on the north lots, the Gator Sportshop roof, the original gator-statue plinth, under the bleachers, on top of the South Ramp, inside the Exactech Arena entry, on the scoreboard, in the tunnel. Star in the end zone.
   - **Co-op:** split up.
   - **Reuses:** `bhvRedCoin`, `bhvHiddenRedCoinStar`.
   - **Lua:** model swap via `hook_behavior(id_bhvRedCoin, OBJ_LIST_LEVEL, false, init_setmodel)` when in this level.
   - **Sync:** vanilla.
   - **S**
5. **Stadium Stair Sprint** (Act 5, friendly race)
   - **Goal:** race "Speedy", an original water-boy NPC, from the north end zone up through the stands to the top row of the south upper deck (~300 m with climbing).
   - **Co-op:** with 2+ players it's also a player race with a results board. The NPC still sets the star condition.
   - **Reuses:** Koopa-the-Quick (`bhvKoopa`, `KOOPA_BP_KOOPA_THE_QUICK_BOB`). Path: `gBehaviorValues.trajectories.KoopaBobTrajectory = get_trajectory("swamp_race_path")` (sm74 pattern).
   - **Lua:** race module (§6.6) for the player board; NPC model swap optional (keep the vanilla Koopa model, since animation reskins are L).
   - **Sync:** vanilla KtQ + race packets.
   - **M**
6. **Flyover!** (Act 6)
   - **Goal:** a Wing Cap box on top of the scoreboard. Fly through 8 banner rings floating over the stadium and the Exactech Arena roof before the cap runs out.
   - **Co-op:** rings are shared. Any player lighting a ring lights it for all, so friends can split the route.
   - **Reuses:** `bhvExclamationBox` (Wing Cap), ring models.
   - **Lua:** custom ring trigger behavior (distance test to a local player → reliable packet to leader → `oSglFlags` bitmask).
   - **Sync:** controller bitmask.
   - **S/M**
7. **Team 100** (7th): shared coin pot (§6.9). Coins in the concessions, stands and lots. **S**

### 7.2 Course 2: Reitz Union & Engineering Quad · door: The Hub · 2★

**Real geography** (origin ≈ (-500,-280) m):

| Feature | Location / size |
|---|---|
| J. Wayne Reitz Union | (-441,-289), 163×95 m, 8 levels |
| Reitz Union North Lawn | (-305,-167), 423×181 m |
| Weil Hall | (-497,-56), 6 levels |
| Weil cooling towers | (-506,-136) |
| Engineering Plaza | (-589,-70) |
| Malachowsky Hall | (-432,-532), 7 levels |
| Liberty Pond | (-369,-335) |
| Reitz Ravine Woods | (-597,-361) |
| Graham Pond | (-745,-393) |
| Gator Corner Dining | (-664,-86) |

1. **Rooftop of the Reitz** (Act 1)
   - **Goal:** climb the Reitz Union: ravine-side terraces → awnings → a window-washer lift (moving platform on a track) → roof star.
   - **Reuses:** `bhvPlatformOnTrack` (or a custom lift), poles, Goombas/Bob-ombs as hazards.
   - **Lua:** none beyond text.
   - **Sync:** vanilla.
   - **S**
2. **Remote Robotics Lab (2P)** (Act 2, **co-op required**)
   - **Goal:** in Malachowsky's atrium, one player stands on the operator console and steers a crane platform with their stick. The rider stands on the platform and is carried up through a 7-storey maze of hanging cable bundles and swinging sensor arms to the star ledge. The platform only moves while someone is on the console. Swap roles anytime.
   - **Co-op:** a solo player can't be both. 3-4 players: a second crane plus extra riders.
   - **Reuses:** none (new).
   - **Lua:**
     - console occupancy by distance test
     - the operator's client sends a reliable `{op=gi}` once, then unreliable `{sx,sy}` at 15 Hz
     - **every client integrates the same velocity from those stick packets** (deterministic, so the rider doesn't jitter) and does `load_object_collision_model()` each frame
     - the leader sends a corrective position every 2 s
   - **Sync:** custom packets + controller.
   - **M** (risk: rider jitter. Fallback: discrete "lift to next floor" button presses.)
3. **Weil Wind Tunnel** (Act 3)
   - **Goal:** turn on the aerospace wind tunnel (big floor button), then ride its vertical airflow up past the Weil cooling towers to a star above the roof.
   - **Co-op:** someone must keep standing on the button or the fan spins down after 10 s. Solo works if you're fast; it's easier with a friend.
   - **Reuses:** `SURFACE_VERTICAL_WIND` collision (the vanilla `ACT_VERTICAL_WIND`) in a toggled collision object; purple-switch-style button.
   - **Lua:** button state → controller flag → swap the wind object on or off.
   - **Sync:** controller.
   - **S/M**
4. **Rogue Robot Roundup** (Act 4)
   - **Goal:** five runaway sidewalk delivery robots (original design) flee across the North Lawn. Pick each one up (grab like a Bob-omb) and drop it on the charging dock by Liberty Pond. A dropped robot runs again after 4 s.
   - **Co-op:** more players means you can pass robots (throw them to a teammate) and corner them.
   - **Reuses:** grabbable object pattern.
   - **Lua:** custom behavior with `oInteractType = INTERACT_GRABBABLE` and `oHeldState` handling (HELD_FREE/HELD/THROWN/DROPPED), flee AI, dock trigger.
   - **Sync:** standard sync (coopdx gives ownership to the holder, then the nearest player); dock count in the controller.
   - **M** (+art: rigid robot)
5. **Meal Swipe Tokens** (Act 5)
   - **Goal:** 8 red coins as golden tokens: Gator Corner patio, the Engineering Plaza sculpture, the Liberty Pond fountain, the Reitz bookstore awning, the ravine boardwalk, Weil's courtyard, the Malachowsky canopy, the cooling-tower catwalk.
   - **Reuses:** red coins.
   - **S**
6. **Data Packet Relay** (Act 6, friendly race / relay)
   - **Goal:** carry a glowing data packet (holdable) from the Weil server closet to Malachowsky's server room (~480 m) in 75 s. It drops if you're hit, and the timer keeps running.
   - **Co-op:** with 2+, the packet can be thrown between players stationed along the route, which beats the clock easily. Solo is possible with the North Lawn cannon shortcut.
   - **Reuses:** holdable object, cannon.
   - **Lua:** race module timer + holdable behavior.
   - **Sync:** standard sync packet object + controller timer.
   - **M**
7. **Team 100** (7th). **S**

### 7.3 Course 3: Marston Science Library (interior) · door: Marston · 5★

**Real footprint:** 57×57 m, 5 levels. Build it 1:1: floors ~4 m (400 u), so a backflip clears one floor. A central atrium/stairwell connects the floors. Book stacks are both platforms and cover. Science-lab flavor; the makerspace is fictionalized.

1. **Out-of-Order Elevator** (Act 1)
   - **Goal:** the elevator is "out of order". Climb the atrium via moving book carts, shelf tops and a wall-kick stairwell shaft to the 5th-floor reading-room star.
   - **Reuses:** moving platforms, wall kicks, Thwomp-style "falling encyclopedia" crushers (rigid reskin of `bhvThwomp`).
   - **Lua:** model swap.
   - **S/M**
2. **Quiet Floor** (Act 2)
   - **Goal:** stealth. On the silent floor, original "Shusher" robots patrol. Running, jumping or landing hard makes noise (check `m.action` flags / `m.forwardVel > 20`; tiptoe-speed walking is quiet). A Shusher that hears you within its radius sends you back to the stairwell. Reach the far window desk.
   - **Co-op:** noise is per-player, so friends can lure Shushers away (they turn toward the loudest noise).
   - **Lua:** custom patrol behavior; noise computed locally for the local Mario and reported to the leader by packet.
   - **Sync:** standard sync patrols.
   - **M**
3. **Group Study Room Booking (2P+)** (Act 3, **co-op required**)
   - **Goal:** the booking system needs every member at once. 2-4 reservation kiosks sit on different floors (count = players here, minimum 2). All must be activated (punch) within 4 s of each other to unlock the glass group-study room holding the star.
   - **Co-op:** kiosks are ≥2 floors apart, so one player can't hit two in 4 s.
   - **Lua:** the leader timestamps kiosk packets on receipt; within the window → success → glass door object removed.
   - **Sync:** controller.
   - **M**
4. **Lost Lab Notebook Pages** (Act 4)
   - **Goal:** 8 red coins as notebook pages in the stacks, the makerspace, the vent duct, the atrium light fixture, and the book-return chute.
   - **S**
5. **Printer Jam** (Act 5, mini-boss)
   - **Goal:** a giant malfunctioning 3D-printer gantry in the makerspace. Two print heads slam down. After a slam a head is stuck for 3 s: ground-pound its glowing reset button. Each head needs 3 resets.
   - **Co-op:** two heads in parallel; needs scale with players.
   - **Lua:** two custom collision objects + button children (`cur_obj_is_mario_ground_pounding_platform`), shockwave on slam, `spawn_default_star` on defeat.
   - **Sync:** leader-driven.
   - **M** (+art: rigid gantry)
6. **Overdue Book Express** (Act 6)
   - **Goal:** carry an overdue book (holdable) from the 5th floor to the lobby return slot in 45 s.
   - **Co-op:** throw it down the atrium to a friend waiting below.
   - **Lua:** holdable + timer + return-slot trigger.
   - **S/M**
7. **Team 100** (7th). **S**

### 7.4 Course 4: Lake Alice · door: Newell Hall · 8★

**Real geography** (origin ≈ (-1760,-600) m, pending the lake polygon):

| Feature | Location / size |
|---|---|
| Lake | center ≈ (-1750,-633) |
| 3 bat houses | (-1882,-510), (-1895,-511), (-1908,-502), 9 m tall, 6-7 m wide |
| Bat House Gardens | (-1839,-479) |
| Field & Fork gardens | (-1879,-543) |
| Bat House parking | (-2002,-597) |
| Bogs | (-1807,-606), (-1652,-496) |
| Museum Road | along the north shore |

Marsh boardwalk, lily pads, Spanish moss trees. Lake Alice's gators are hazards in an original cartoon style.

1. **Boardwalk Welcome** (Act 1)
   - **Goal:** cross the marsh boardwalk and the lily-pad shallows to the observation deck at the lake center. Skeeters (water striders, vanilla) and cheep-cheeps on the way.
   - **Reuses:** vanilla Skeeter/Cheep-cheep; floating lily pads (`bhvWdwSquareFloatingPlatform` / `bhvJrbFloatingPlatform` with a lily-pad model swap, or rigid custom).
   - **S**
2. **Gator Hop** (Act 2)
   - **Goal:** basking gators form a path to the island nest. They sink in a rhythm (back above water 3 s, under 2 s). Falling in near a "big gator" (rigid two-part jaw, original design) means it snaps and you take damage.
   - **Co-op:** gators sink faster when two players stand on one, so spread out.
   - **Lua:** custom collision platforms on a cycle (`oTimer` phase from the controller's synced `oSglTimer`, so all clients agree), jaw-snap hazard.
   - **M** (+art: rigid gator)
3. **Shell Surf Regatta** (Act 3, friendly race)
   - **Goal:** grab a Koopa shell at the dock and surf a buoy course around the lake through 8 checkpoint buoys. Beat par 75 s for the star; with friends it's a race.
   - **Reuses:** `bhvKoopaShell` (shell boxes respawn: `gBehaviorValues.RespawnShellBoxes = 1`).
   - **Lua:** race module.
   - **M**
4. **Bat Census at Dusk (2P+)** (Act 4, **co-op required**)
   - **Setup:** this act runs at dusk (lighting set locally per act: `set_lighting_color`, `set_fog_color`, `set_override_skybox`, or the day-night-cycle API if that mod is on). Swoopers (vanilla bats!) stream out of the 3 bat houses for 90 s.
   - **Goal:** three census stations (clipboard posts by the houses, the gardens and the boardwalk) count bats only while occupied. Reach the target count (600 + 300 per extra player). Swoopers dive at counters, and a hit knocks you off your station.
   - **Co-op:** the target is impossible with only one station staffed.
   - **Lua:** the leader samples player positions at 2 Hz (same instance, so it sees everyone) and adds to `oSglProgress`; Swooper spawns are local and cosmetic; dive attackers are vanilla.
   - **Sync:** controller.
   - **M**
5. **Lost Hatchling** (Act 5)
   - **Goal:** a baby gator wandered onto Museum Road. Carry it (holdable, rigid cute model) back to its mother at the island nest. The mother is static and waves her tail in code.
   - **Co-op:** pass it across the water by throwing.
   - **Reuses:** holdable pattern from 7.2-4; the vanilla Tuxie logic is an alternative if we keep penguin models (off-theme).
   - **S/M**
6. **Lily Pad Red Coins** (Act 6)
   - **Goal:** 8 red coins on lily pads, bat-house roofs, the garden trellis, a cypress knee, and the boardwalk underside.
   - **S**
7. **Team 100** (7th). **S**

### 7.5 Course 5: Library West After Dark (interior) · door: Library West · 14★

**Real footprint:** 80×65 m, 5 levels. Late-night finals vibe: desk lamps, a first-floor coffee counter (unbranded), and sleepy-ghost Boos (vanilla Boo model fits). BBH slot, so Big Boo logic and star positions (`gLevelValues.starPositions.GhostHuntBooStarPos`, `BalconyBooStarPos`) work with `vec3f_set`, like sm74.

1. **All-Nighter** (Act 1)
   - **Goal:** climb from the lobby to the top-floor reading room past Boos and sliding book ladders. The star is at the big window.
   - **Reuses:** Boos, moving platforms.
   - **S**
2. **Quiet Hours Hide-and-Seek (2P+)** (Act 2, **co-op/competitive required**)
   - **Goal:** one seeker ("night librarian", drawn metal, carries a flashlight point light) vs hiders in the stacks. 150 s round. After any completed round with 2+ players, the star appears at the circulation desk. Winners get a results board and a mod_storage tally.
   - **Lua:** `sgl-hideseek.lua` (§6.7); seeker light via `le_add_light` + `le_set_light_pos` each frame (local per client, following the seeker's Mario).
   - **Sync:** `gPlayerSyncTable[i].role`, controller state/timer.
   - **M**
3. **The Ghost of Finals Past** (Act 3)
   - **Goal:** defeat the small Boos haunting each floor, then Big Boo appears in the rotunda; ground-pound it 3 times.
   - **Reuses:** vanilla ghost hunt (`bhvGhostHuntBoo` + `bhvGhostHuntBigBoo`).
   - **Lua:** star position override only.
   - **S**
4. **Lights Out** (Act 4)
   - **Goal:** the power's out. Everything is dark (`le_set_mode(LE_MODE_AFFECT_ALL_SHADED_AND_COLORED)`, `le_set_ambient_color(20,20,30)`). Each player carries a point light (`le_add_light` attached to every connected Mario in the instance, drawn locally). Find and ground-pound 3 breakers on 3 floors to restore power.
   - **Co-op:** more players means more light. Breakers can be done in parallel.
   - **Sync:** breakers in the controller bitmask.
   - **M** (risk: vertex lighting needs subdivided floors; see §11)
5. **Coffee Run** (Act 5, friendly race)
   - **Goal:** start on the 5th floor, grab a coffee cup at the 1st-floor counter and bring it back up. Beat par 60 s; with friends it's a race. Boos block the stairwells.
   - **Lua:** race module + a pickup-and-return checkpoint.
   - **M**
6. **Re-shelve the Glowing Books** (Act 6)
   - **Goal:** 8 red coins as glowing books.
   - **S**
7. **Team 100** (7th). **S**

### 7.6 Course 6: Century Tower (interior) · door: tower base · 20★

The real tower is 9×9 m and 47.9 m tall: too small to hold 6 missions at 1:1. The interior is a **"bigger on the inside"** clockwork shaft (≈30×30 m, 60 m tall), and the **exterior stays 1:1** in the hub. This is a deliberate exception that needs user sign-off. TTC-style objects fit: `bhvTTCRotatingSolid`, `bhvTTCPendulum`, treadmills, moving bars, Thwomps, Amps. Their speed is controlled with `set_ttc_speed_setting(TTC_SPEED_*)`.

1. **Up the Bell Tower** (Act 1)
   - **Goal:** classic vertical climb through cogs, pendulums and treadmills to the bell chamber star.
   - **Reuses:** TTC objects.
   - **S/M**
2. **Carillon Concert (2P+)** (Act 2, **co-op required**)
   - **Goal:** 8 bells hang on 4 levels of the bell chamber. A melody plays once with bells lighting up. Then the players must ground-pound the bells in order, ≤2.5 s per note. Three songs of increasing length → star.
   - **Co-op:** consecutive notes jump between levels 6-8 m apart, so one player can't make it in time. Players split levels.
   - **Lua:**
     - bell objects with `cur_obj_is_mario_ground_pounding_platform` → reliable `PKT_BELL {bell, song, note}` → leader validates the sequence and timing on receipt
     - bell sounds via `audio_sample_play` (custom samples)
     - the demo melody is driven by the controller state
   - **Sync:** controller.
   - **M/L**
3. **Clockwork Red Coins** (Act 3)
   - **Goal:** 8 red coins in the gears.
   - **S**
4. **Race to the Top** (Act 4, friendly race)
   - **Goal:** players race from the base to the top bell. Par 90 s for solo.
   - **Lua:** race module.
   - **M**
5. **Stop the Clock** (Act 5)
   - **Goal:** a pressure plate at the base freezes every mechanism while held (`set_ttc_speed_setting(TTC_SPEED_STOPPED)`); off means the mechanisms run fast. The star is behind a gear wall that's only passable while frozen.
   - **Co-op:** one holds, the others climb. Solo: the plate freezes for 12 s after a ground pound (harder).
   - **Lua:** controller flag; every client sets the TTC speed from it.
   - **S/M**
6. **Ring the Outside Bells** (Act 6)
   - **Goal:** take the Wing Cap from the top window, fly around the tower exterior and hit 4 exterior bells.
   - **Lua:** ring/bell trigger pattern from 7.1-6.
   - **S/M**
7. **Team 100** (7th). **S**

---

## 8. Bonus stages and the finale

### 8.1 Smathers Stacks Slide (COURSE_PSS) · door: Smathers Library · 3★

- **Layout:** a winding slide down through the old library's stacks and map-room cabinets (PSS-style; no act select, since PSS is a bonus course).
- **Stars:** star 1 for finishing; star 2 for finishing under 21 s (`gLevelValues.pssSlideStarTime`, `pssSlideStarIndex`). Vanilla logic.
- **S** (art: one slide)

### 8.2 Finals Week Ascent (BITS slot) · door: "FINAL EXAM" at the tower base · 30★

- **Layout:** a night-time obstacle climb up an impossible spiral of giant textbooks and blue books above campus. The real hub lights glow far below (skybox).
- **Obstacles:** Bullet Bills reskinned as flying red pens (rigid model, cheap), Thwomps as falling textbooks, Amps as static shocks, rotating rulers (rotating platforms).
- **Ending:** a pipe → The Final Exam.
- **Optional star:** 8 red coins (COURSE_BITS).
- **S** code / **L** art

### 8.3 Boss: The Final Exam (BOWSER_3 slot)

**Arena:** "the exam hall in the sky": a circular floating platform (radius ≈ 25 m) above Century Tower's top. Around it:
- 4 answer pads (A-D)
- 6 "pop-quiz bombs" at the rim (Bowser-style mines; vanilla `bhvBowserBomb` can be placed and reused)
- a lower safety ring with springs back up, so falls aren't instant deaths

Bubble death is on.

**Boss design (original):** a hulking, floating blue-book exam. It has a bubble-sheet face, pages that flap like wings, orbiting #2 pencils, and a ticking clock on its spine. It's built from rigid parts animated in code (no skeleton needed).

- **Phase 1: Multiple Choice.**
  - A HUD question with 4 answers and a 10 s timer. Questions are silly campus trivia and in-jokes the friends can write, stored in a Lua table.
  - The pads for wrong answers sink at zero (they are collision objects lowered on all clients from controller state) and drop players to the lower ring.
  - If ≥1 player is on the right pad, the Exam is "stumped": it crashes down and opens 3 answer bubbles on its back for 4 s. Ground-pound them.
  - Hits needed: 3 + ⌊(n−1)/2⌋.
- **Phase 2: Pop Quiz Barrage.**
  - It circles and rains pencils (falling projectiles with shadow markers) and slams out shockwave rings (`id_bhvBowserShockWave`).
  - Eraser bombs (holdable, rigid model) spawn at the rim. Throw them when it swoops low.
  - Co-op: one player baits the swoop and another throws.
- **Phase 3: Essay Question.**
  - The arena tilts slowly (one big rotating collision object). The Exam writes long lines of "essay" text that sweep across the arena like Bowser's fire rings (jump them).
  - Ground-pound the 4 "citation" pillars in the order the HUD shows. Each pillar lights for everyone. Players can split them.
  - After the 4th, the Exam crumples into paper confetti and drops the **Grand Star** (`id_bhvGrandStar` spawned by every client from controller state; same spawn pattern).

**Lua and sync:**
- One controller + boss object, leader-authoritative:
  - `network_init_object(o,false,{phase,hp,action,pos…})`
  - 10 Hz unreliable position updates, reliable phase/hit events
- Player hits reach the leader by packet (`HOOK_ON_ATTACK_OBJECT` / ground-pound detection on child weak-point objects).
- Music via `smlua_audio_utils_replace_sequence` for the boss sequence.
- Death: `HOOK_ON_DEATH` → bubble or respawn at the arena edge; never kick the group out.

**Difficulty:** **L** (code ~1-2 weeks; art: rigid parts plus the arena).

**Ending:** Grand Star → our own "Graduation" sequence instead of vanilla credits:
- fade to the hub at night with fireworks (spawned particles)
- the cast lineup (`art/cast_lineup.png`) and per-friend portrait cards in a HUD credits roll
- OSM attribution
- back to free play

**M**

---

## 9. Star budget

| Source | Stars | Co-op-required |
|---|---|---|
| 6 stages × 6 missions | 36 | 6 |
| 6 × Team 100 | 6 | 0 |
| Hub secrets | 7 | 0 |
| Smathers slide | 2 | 0 |
| Finals Week Ascent red coins (optional) | 1 | 0 |
| **Total** | **52** | **6** |

Every stage has at least one friendly race or competitive mode:

| Stage | Race / competitive mission |
|---|---|
| The Swamp | Stair Sprint |
| Reitz & Engineering | Data Packet Relay |
| Lake Alice | Shell Surf Regatta |
| Library West | Coffee Run, Hide-and-Seek |
| Century Tower | Race to the Top |
| Hub | Plaza Dash, free-play Hide-and-Seek |

Marston's Quiet Floor stealth doubles as a "who gets caught" competition.

---

## 10. Build order (smallest fun slice first)

Each slice ends with an in-game test with 2+ real players. The lead runs the game.

**Slice A: "First Door" (the first playable evening)**
1. `charselect.lua` + 10 portraits. **S/M.**
   Test: 2 players pick friends, see each other's models, and the pick persists after rejoin.
2. Framework: `a-sgl-constants.lua`, `sgl-levels.lua` (text, entry/exit, door locks), `sgl-party.lua` (instance/leader, invites), `sgl-mission.lua` (controller, star spawn, Team 100), `sgl-hud.lua`. **M.**
3. Hub v0 (Castle Grounds replacement): Plaza of the Americas, Century Tower exterior, the Auditorium door, box stand-ins for other buildings, spawn node `0x0A`, return nodes `0x21/0x31`. **M** (art).
4. The Swamp v0 (BOB replacement): stadium bowl with ramp collision, field, West Skybox Tower, cannon.
   Acts 1 (Kickoff), 4 (Tailgate Tokens) and **3 (Gator Chomp Chorus, co-op)**. **M/L** (art) + S/M (code).
5. `main.lua` gets `-- incompatible: romhack` (lead).
6. Ship precompiled `.lvl/.bin` only; check mod size < 35 MB.

**Acceptance:** 2-4 friends join → pick friends → spawn on the Plaza → walk into the Auditorium → act select → the invite brings everyone into Act 3 → chomp together → star → everyone's count reads 1★ → back on the Plaza.

**Slice B: "Gameday + Hub"**
- Swamp acts 2, 5, 6 + Team 100. Race module.
- Hub v1: all door shells with locks and plaques, bus stops, Five Bell Notes, Bold Squirrel, Plaza Dash, chomp emote, TA #1.
- Reitz & Engineering stage with Acts 1, 3, 5 first, then 2 (Remote Robotics), 4 and 6.

**Slice C: "Libraries"** (interiors are small and collision-cheap, so faster to build)
- Marston (all acts).
- Library West (all acts) with `sgl-hideseek.lua` (also enables hub free-play hide-and-seek) and Lights Out.
- Smathers slide.

**Slice D: "Lake Alice"**
- Fix the lake data first (§11).
- Then the stage, dusk lighting, shells, Bat Census.

**Slice E: "Finals"**
- Century Tower interior.
- Finals Week Ascent.
- The Final Exam boss.
- Graduation ending.
- Hub TA #2, rooftop red coins and the Wing Cap at 20★.

**Slice F: Polish**
- Music (custom `.m64` sequences via `smlua_audio_utils_replace_sequence`, or `audio_stream_load`) and dialog writing.
- Balance pass.
- Web build parity: same mod, light on packets, small textures.

---

## 11. Risks, open questions, and proposals for the lead

1. **Lake Alice is missing from the data.** `tools/campus/osm_extract.py` only turns `building` relations into polygons. Water and leisure multipolygons (Lake Alice, likely others) are dropped.
   - The lake center is ≈(-1750,-633) m (from its published coordinates), ~600 m west of the (-1136,-771) "conservation area" figure. The bat houses at (-1882..-1908,-510) confirm the lake is on the west side.
   - Proposal: extend the extractor to emit `natural=water` / `leisure` relation outers into `areas` (no downloads; the tiles are already local).
2. **Reskinning animated vanilla enemies is expensive** (skeleton-matched models). Only rigid actors are reskinned; everything else uses vanilla models that fit, or our own rigid-model behaviors (§6.10).
3. **Mod size cap:** 35 MB per mod for joiners. 1:1 levels with textures must be optimized. Ship compiled `.lvl/.bin/.tex` only (`install-mods.sh` currently copies everything; a "package" step should strip `.c/.h` sources).
4. **Shared files that need small edits** (lead's call):
   - `main.lua` header: add `-- incompatible: romhack` once the level replacements land.
   - `characters.lua`: expose `FRIENDS` (e.g. `_G.sglFriends = FRIENDS`) so `charselect.lua` reads the same ordered list.
5. **Act instancing:** friends in different acts can't see each other. The Study Group invite + regroup button (§6.11) are essential, not polish.
6. **Coin counting in co-op is unverified** (per-player or shared). Team 100 sidesteps it with a leader-summed pot. Check in-game that `INTERACT_COIN` fires once per coin per collector.
7. **Server settings:** Solid interactions (needed for touch-tag), stay-in-level and bubble death are set at mod load. `gServerSettings` desyncs if changed later. Confirm that overriding host choices is acceptable; otherwise show a warning.
8. **1:1 scale feel:** traversal times (§1.1) need bus stops, cannons and shells. Verify riser and step collision feel in Slice A. The draw distance on the outdoor stages needs `InfiniteRenderDistance` + far-plane/fog tuning.
9. **Lighting engine (Lights Out, hide-and-seek flashlight):** vertex lighting needs reasonably dense floor and wall vertices. Large 1:1 quads will look flat, so subdivide interior floors to ~2 m.
10. **Century Tower interior is not 1:1** ("bigger on the inside"). Confirm the user is happy with this exception. Also keep the real tower (a memorial) respectful: the fight is in a separate sky arena.
11. **Remote Robotics Lab:** the rider on a platform owned by a remote client may jitter. Mitigation is deterministic integration from stick packets, with a "floor buttons" fallback.
12. **Web port:** everything here is plain Lua plus DynOS assets. Keep reliable packets event-only, and avoid large audio streams if the web build's audio is limited.
13. **Content sensitivity:**
    - no real people beyond the friends
    - no UF logos or mascot likenesses (Albert/Alberta statues become original gator statues)
    - no brand names (the Gatorade marker, the coffee chain)
    - Baughman Center (a reflection space on the lake) is backdrop only

---

## Appendix A: Lua API cheat sheet used in this doc (v1.5.1)

- **Hooks:**
  - `hook_event`: `HOOK_UPDATE`, `HOOK_MARIO_UPDATE`, `HOOK_BEFORE_MARIO_UPDATE`, `HOOK_ON_HUD_RENDER`, `HOOK_ON_LEVEL_INIT`, `HOOK_ON_WARP`, `HOOK_BEFORE_WARP`, `HOOK_ON_SYNC_VALID`, `HOOK_ON_PLAYER_CONNECTED/DISCONNECTED`, `HOOK_ON_PACKET_RECEIVE`, `HOOK_ALLOW_INTERACT`, `HOOK_ON_INTERACT`, `HOOK_ALLOW_PVP_ATTACK`, `HOOK_ON_PVP_ATTACK`, `HOOK_ON_ATTACK_OBJECT`, `HOOK_USE_ACT_SELECT`, `HOOK_ON_DEATH`, `HOOK_ON_PAUSE_EXIT`, `HOOK_OBJECT_SET_MODEL`, `HOOK_GET_STAR_COLLECTION_DIALOG`, `HOOK_ON_NAMETAGS_RENDER`
  - also `hook_behavior`, `hook_mario_action`, `hook_on_sync_table_change`, `hook_chat_command`, `hook_mod_menu_button/checkbox`
- **Sync:** `gGlobalSyncTable`, `gPlayerSyncTable[i]`, `network_init_object`, `network_send_object`, `network_send`, `network_send_to`, `spawn_sync_object`, `spawn_non_sync_object`, `define_custom_obj_fields`, `network_is_server`, `network_player_connected_count`, `network_player_from_global_index`, `network_get_player_text_color_string`, `network_player_set_description`, `network_player_set_override_location`
- **Stars / save:** `spawn_default_star`, `spawn_red_coin_cutscene_star`, `spawn_no_exit_star`, `save_file_get_total_star_count`, `save_file_get_star_flags`, `gLevelValues.starPositions` + `vec3f_set`, `gLevelValues.coinsRequiredForCoinStar`, `gBehaviorValues.ToadStar1/2Requirement`, `MipsStar1/2Requirement`
- **Levels / warps:** DynOS `.lvl` replacement, `warp_to_level`, `warp_to_warpnode`, `level_trigger_warp`, `gLevelValues.entryLevel/exitCastle*`, `smlua_text_utils_course_acts_replace`, `smlua_text_utils_castle_secret_stars_replace`, `smlua_text_utils_secret_star_replace`, `smlua_text_utils_dialog_replace`, `act_select_hud_hide`
- **Objects:** `obj_set_model_extended`, `smlua_model_util_get_id`, `smlua_collision_util_get`, `load_object_collision_model`, `cur_obj_is_mario_ground_pounding_platform`, `cur_obj_is_any_player_on_platform`, `obj_check_if_collided_with_object`, `nearest_mario_state_to_object`, `obj_scale_xyz`, `get_trajectory`, `gBehaviorValues.trajectories.*`, `set_ttc_speed_setting`
- **HUD / UI:** `djui_hud_set_resolution`, `djui_hud_print_text`, `djui_hud_render_rect`, `djui_hud_render_texture`, `get_texture_info`, `djui_hud_world_pos_to_screen_pos`, `djui_hud_get_mouse_x/y`, `djui_hud_get_mouse_buttons_pressed`, `djui_hud_set_mouse_locked`, `djui_popup_create`, `hud_hide/hud_show`, `mod_storage_save/load`
- **Look / sound:** `set_lighting_color`, `set_fog_color`, `set_override_skybox`, `set_override_far`, `le_set_mode`, `le_set_ambient_color`, `le_add_light`, `le_set_light_pos`, `le_remove_light`, `smlua_audio_utils_replace_sequence`, `audio_stream_load/play`, `audio_sample_load/play`, `play_race_fanfare`, `camera_set_romhack_override`, `camera_freeze`

## Appendix B: Coordinate convention for level builders

Level units = centimetres. Convert from `campus.json` (meters, x = east, y = north) with stage origin (ox, oy):

- `X = (x − ox) * 100`
- `Z = −(y − oy) * 100` (SM64 +Z points south)
- `Y = height * 100`

Keep every stage within ±32,767 units, i.e. ±327 m of its origin.
