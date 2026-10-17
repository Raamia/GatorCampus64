# Super Gatorlator 64

**The University of Florida campus as a co-op Super Mario 64 game, with our friends as playable characters.**

Super Gatorlator 64 is a total-conversion mod for [sm64coopdx](https://github.com/coop-deluxe/sm64coopdx), the open-source PC port of Super Mario 64 with online co-op. It keeps Mario's original movement, physics and animations, and replaces the world and the cast: real UF buildings rebuilt at true 1:1 scale from OpenStreetMap data, and 10 real friends turned into low-poly N64-style characters from their photos.

> **Status:** everything below is built, verified offline, and compiles in the game. It has not been fully play-tested yet.

---

## What's in the game

### The cast: 10 playable friends

Each friend was built from 1–4 photos into an N64-style character that keeps every one of Mario's moves (triple jump, wall kick, ground pound, swimming, wing cap, metal cap).

- **Hand-drawn pixel-art faces:** 8 eye states (open, blinking, looking around, knocked out) plus a mouth.
- **Signature looks:** each friend's hairstyle, outfit and accessories, like glasses, headphones, a soccer jersey or a suit and tie.
- **Character select menu:** "CHOOSE YOUR GATOR!" with portraits, synced online so everyone sees each other as the right friend.

### The campus: a hub and 5 stages

| Stage | Door in the hub | Unlocks at | What it is |
|---|---|---|---|
| **Hub: Plaza of the Americas** | — | start | Century Tower (climbable, 47.9 m), the Auditorium, Library West, Smathers, Turlington and "The Potato", Marston, The Hub, Newell |
| **1. The Swamp** | University Auditorium | 0 ★ | Ben Hill Griffin Stadium at true scale, the O'Connell Center, Florida Gym |
| **2. Reitz Union + Engineering** | The Hub | 2 ★ | The Reitz Union (enterable food court, climbable tower), Weil Hall, Malachowsky Hall, Gator Corner |
| **3. Lake Alice** | Newell Hall | 5 ★ | The real lake basin with its islands, lily pads, cypress, the bat houses, the Baughman Center |
| **4. Marston Science Library** | Marston | 8 ★ | A 5-floor interior from UF floor plans: stacks, glass study rooms, quiet and silent floors |
| **5. Library West After Dark** | Library West | 11 ★ | A night-time 6-floor interior with Century Tower glowing through the windows |

Walk into a building's door to get SM64's real act select screen. Stars are shared by the whole group, save between sessions, and unlock the next doors.

### 15 missions: two solo and one co-op per stage

| Stage | Missions |
|---|---|
| The Swamp | Climb to the press-box roof · Stadium stair sprint race · **Gator Chomp Chorus** (co-op ground-pound rhythm on the end-zone corners) |
| Reitz + Engineering | Rooftop of the Reitz (window-washer lift) · Meal Swipe Tokens hunt · **Remote Robotics Lab** (operators steer cranes that carry riders) |
| Lake Alice | Lily-pad hop to the deck · Gator Hop across the deep hole · **Bat Census at Dusk** (the lake turns to dusk) |
| Marston | Out-of-Order Elevator climb · Shhh! Lost Textbooks (stealth past librarians) · **Group Study Room Booking** |
| Library West | All-Nighter climb · a second solo act · **Quiet Hours Hide & Seek** (nametags hidden) |

**Co-op features:**
- **Study Group invites:** when a friend starts a mission, everyone else gets a "join them" popup.
- **Co-op scaling:** team missions adapt to 2–4 players.
- **Shared progress:** shared stars, shared mission state, and a host-only group warp.

---

## How it works

### Architecture

```
sm64coopdx (prebuilt, unmodified engine)
└── mods/sgl64/ ← everything we made is a mod
    ├── *.lua mission framework, missions, HUD, doors, character select
    ├── actors/<friend>/ character models (Fast64 C export → compiled at launch)
    ├── levels/castle_grounds/ the hub (replaces Mario's castle grounds)
    ├── levels/bob, wf, jrb, ccm, bbh/ the 5 stages (replace vanilla course slots)
    └── textures/ character portraits
```

- **No engine changes.** The game is plain sm64coopdx. DynOS, its runtime asset compiler, turns our exported C into models and levels when the game launches.
- **Level slots.** The hub replaces Mario's castle grounds, and each stage replaces a vanilla course slot. That gives us SM64's own act select, star saving and "exit course" behavior for free (the same approach as the Star Road romhack).
- **Lua mission framework.** It runs a controller per act and elects a leader among the players in that act. It also syncs mission state, spawns stars, draws the HUD, and handles races and hide-and-seek.

### Pipeline 1: photos → playable characters

1. **Spec:** colors sampled from the photos, plus outfit, hairstyle and accessories (`art/<id>/character.json`).
2. **Face art:** an agent draws the 8 eye states and a mouth as pixel art in a shared style. For the first character, three artists competed and three judges picked the winner.
3. **3D model, by "template surgery":** headless Blender scripts start from the official coopdx Mario template, which keeps the rig and all animations. They recolor the body, remap the overalls into the friend's outfit, generate a new head and hairstyle, add accessories, and replace all 18 head variants (every eye state, cap on and off, metal).
4. **Export:** Fast64 (a Blender add-on for SM64) writes C, which DynOS compiles in game.
5. **Validation:** an export validator, plus rendered previews compared against the photos by reviewer agents.

### Pipeline 2: OpenStreetMap → true-scale stages

1. **Campus data:** about 24 MB of OSM data for UF main campus, giving 2,251 building footprints with heights, plus paths, roads, water and trees.
2. **Stage planning:** the coopdx level limit is about 650 m across at Mario scale, so the campus is split into 600 m stage windows. Each window gets a collision budget and simplification rules.
3. **Procedural generator:** ground, paths, every building extruded to its real footprint and height with N64-style brick and roof textures, trees, fog and boundary walls.
4. **Hand-modeled landmarks:** 11 Python modules for Century Tower, the stadium, the Reitz Union, Malachowsky and others, built to a shared contract so they drop into any stage.
5. **Interiors:** floor plans researched from UF Libraries pages, then built with a reusable interior kit (climbable bookshelf stacks, study rooms, stairs, elevators).
6. **Validation:** a static validator checks every level against the coopdx v1.5.1 level parser, plus collision crack scans.

### Testing without playing

Every change is checked offline before anyone launches the game:
- **`tools/luatest/`** is a multi-client simulation of the coopdx Lua API. It covers 2,921 checks across the flow (doors, warps, act select, stars) and every mission, including deliberate "mutation" breakages to prove the tests catch bugs.
- **`validate_level.py`** checks every exported level against the coopdx v1.5.1 parser's symbol tables.
- **`luac`** syntax-checks all Lua.

---

## By the numbers

| | |
|---|---|
| Playable characters | 10 |
| Stages | hub + 5 (3 outdoor, 2 interior) |
| Missions | 15 (10 solo, 5 co-op) |
| Mod Lua | 12 files, ~10,900 lines |
| Build tools (Python) | ~43,800 lines |
| Offline tests | ~18,700 lines, 2,921 checks |
| Hand-modeled landmarks | 11 modules |
| N64-style textures | 83, all generated procedurally |
| OSM buildings | 2,251 |
| Mod size toward coopdx's 35 MB limit | 8.2 MB |

---

## How it was built

It was built with **Claude Code, using parallel multi-agent workflows**. Each piece followed the same pattern: research, then build, then **independent reviewers** (technical, likeness, fun), then a fix round. Typically 5–10 agents ran per stage, and several stages built at the same time. What kept it on track:
- **Contracts between agents:** a written level-flow contract (`docs/flow.md`) and a landmark module interface, so parallel work fit together.
- **Adversarial reviews:** reviewers caught real bugs before any play test. Examples include faces rendering with the wrong texture tile size, a book chute whose walls faced the wrong way, an elevator shaft that trapped players, and hide-and-seek nametags that showed through walls.
- **Offline verification:** validators and the Lua simulation stood in for play-testing, since agents can't see the game screen.

---

## Known gaps

- **Not fully play-tested.** Mission tuning (race times, climb difficulty, co-op timing) still needs real players.
- **Century Tower interior** and the **"Final Exam" boss** are designed (`docs/game_design.md`) but not built.
- **Web browser version:** feasibility researched but paused. A WebAssembly port of coopdx with WebRTC co-op exists as prior art.
- **Smaller issues:** long hair is rigid on the head bone, and most building heights are estimated because OSM lacks them.

---

## If you build something like this at a UF hackathon

### Scope it down

We had about 36 hours of heavily parallelized agent time. For a 24–36 hour hackathon, a strong demo would be:
- **The hub only:** Plaza of the Americas and Century Tower, generated from OSM.
- **2–3 friend characters.**
- **One stage with one co-op mission.**

The OSM-to-level pipeline is the most impressive part per hour spent. Characters take longer than you'd expect.

### Check the IP rules first

Super Mario 64 is Nintendo's. This project only works for people who own their own ROM, and it's kept in a private repo. Before entering a hackathon:
- Read the rules on third-party IP and public demos.
- Never distribute a ROM or Nintendo assets.
- **Consider an original engine** (Godot, Unity or three.js with your own character controller). The OSM-to-3D campus pipeline, the photo-to-character idea and the co-op mission design all carry over, and the result is fully yours to show publicly.

### Pitfalls we hit

- **Level size:** about 650 m at Mario scale, so a 3 km campus has to be split into stages.
- **Draw distance and fog:** these need deliberate tuning at true scale.
- **Act order:** act select only offers acts you have stars for, plus the next one. Missions must be acts 1..N with no gaps, or the game soft-locks.
- **Load order:** coopdx loads mod Lua files alphabetically, so file names matter.
- **Wall direction:** wall faces must point the right way. Airborne players get pushed out of walls they're near.
- **Stars per player:** count how many stars a solo player can actually earn before setting door requirements.

### Credits to keep

- Map data © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors (ODbL), which requires attribution.
- [sm64coopdx](https://github.com/coop-deluxe/sm64coopdx), the [coopdx character template](https://github.com/coop-deluxe/character-template), [Fast64](https://github.com/Fast-64/fast64) and [Fast64-Gart](https://github.com/ManIsCat2/Fast64-Gart).
