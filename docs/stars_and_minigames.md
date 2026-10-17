# Super Gatorlator 64: Stars and Minigames

Every star in the game, as the mission code builds it today. The stage table and act names live in `mods/sgl64/course.lua`, and each stage's missions are in its own `*_missions.lua` file.

## How stars work

- **Doors:** the stage doors in the hub open at **0, 2, 5, 8, 11 and 14** total stars.
- **Stars per stage:** each stage has 7 stars, the 6 acts plus the 100-coin star.
  - Act *k* awards star id *k − 1*.
  - The 100-coin star is id 6.
- **What's built:** acts 1–3 in every built stage.
  - That's 15 missions plus five 100-coin stars, **20 stars** in all.
- **Coming soon:** acts 4–6 are named "COMING SOON". The stage loads as free roam with no mission and no star.
- **Act order:** the solo-able acts come first. Act select only offers the acts you already have stars for plus the next one.
- **Co-op:**
  - Stars are shared by everyone in the session.
  - When a friend starts a mission, everyone else gets a "join them" invite (the Study Group).
  - Co-op missions scale with the number of players.
- **Solo players:** every built stage gives a solo player 3 stars (acts 1–2 plus 100 coins). That's enough to open each next door with one star to spare.

---

## 1. The Swamp
**Door:** University Auditorium · **Opens at:** 0★ · **Level slot:** `bob` · **Code:** `swamp_missions.lua`

Ben Hill Griffin Stadium at true scale, plus the O'Connell Center and Florida Gym.

| # | Act | Type | Players |
|---|---|---|---|
| 1 | Kickoff - Climb the Skybox | Solo climb | 1+ |
| 2 | Stadium Stair Sprint | Race | 1+ |
| 3 | Gator Chomp Chorus - 2P | Co-op rhythm | 2–4 |

### Act 1: Kickoff - Climb the Skybox
- **Goal:** climb the West Skybox Tower to the press-box roof, **66 m** up.
- **Route:**
  1. Start at "CLIMB HERE" on the west rim.
  2. Climb the ledges.
  3. Cross the camera decks.
  4. Climb a **22.5 m pole** to the roof.
- **Pickups:** coins on every ledge and deck, and hearts at the rim, the Bull Gator Deck and deck 5.
- **Star:** the only star the level itself places, on the press-box roof. The mission just tracks the climb and the marker shows the route.

### Act 2: Stadium Stair Sprint
- **Course:** start in the north end zone, run up the east stands and around the rim, and finish on the South Ramp terrace.
  - There are **9 checkpoints**.
- **Times:** **par 1'10** earns the star. **Gold** is **0'45**.
- **Extras:** race music plays, and D-pad Down takes you back to the start box.

### Act 3: Gator Chomp Chorus - 2P
- **Players:** needs at least 2. One corner lights up per player (2–4).
- **Rounds:** 3 phrases. In each one:
  1. Stand on a lit end-zone corner button.
  2. Hold it while the crowd chants "GA… TOR…".
  3. Ground-pound on "**CHOMP!**".
- **Each new phrase** lights a different set of corners.

### Coming soon
- Visiting Mascot
- Tailgate Tokens
- Flyover!

---

## 2. Reitz Union + Engineering Quad
**Door:** The Hub · **Opens at:** 2★ · **Level slot:** `wf` · **Code:** `wf_reitz_missions.lua`

The Reitz Union is enterable: area 2 is the full 8-floor interior. Weil Hall, Malachowsky Hall and Gator Corner are also in this stage. The missions all run outside, in area 1.

| # | Act | Type | Players |
|---|---|---|---|
| 1 | Rooftop of the Reitz | Solo climb | 1+ |
| 2 | Meal Swipe Tokens | Collect 8 | 1+ (shared) |
| 3 | Remote Robotics Lab - 2P | Co-op cranes | 2+ |

### Act 1: Rooftop of the Reitz
- **Goal:** climb the Reitz Union from the ravine side.
- **Route:**
  1. Brick terraces.
  2. Sunshade awnings.
  3. The ballroom roof.
  4. The podium roof.
  5. The **window-washer lift**, a moving platform on the tower's west face. The cable pole and the tower's east ledges also work.
  6. The tower roof.
  7. The elevator penthouse, **28.8 m** up.
- **Star:** appears on the penthouse.

### Act 2: Meal Swipe Tokens
Find **8 meal-swipe tokens**:
1. Gator Corner patio
2. Engineering Plaza sculpture
3. Liberty Pond fountain
4. Bookstore awning
5. Ravine boardwalk
6. Weil Hall's roof ridge (**24 m**)
7. Malachowsky's glass stair (**12 m**)
8. Cooling-tower catwalk

- **Progress:** shared by everyone in the act.
- **Star:** pops out where the 8th token was found.

### Act 3: Remote Robotics Lab - 2P
- **Setting:** Malachowsky Hall's 7-storey atrium.
- **The crane:** one player stands on an **operator console** and steers a **crane platform** with the stick. The crane only moves while someone is on the console, so you can't do it alone.
- **Goal:** the riders go up through **5 sensor gates** to the star ledge, **28 m** up.
- **Getting through a gate:**
  1. A rider jumps and hits the gate's "**!**" sensor box, which hangs under the gate.
  2. That unlocks the gate.
  3. The operator steers the crane through its narrow gap. The gap moves every round.
- **Enemies:** circling Amps guard two floors.
- **Scaling:**
  - **2–3 players:** one crane. 1 rider must reach the ledge with 2 players, 2 riders with 3.
  - **4 players:** a second crane on the east lane, with its own console. 2 riders must reach the ledge.
  - **5+ players:** 3 riders must reach the ledge.
  - Each crane carries at most riders-needed ÷ cranes, rounded up.
- **Shortcut:** D-pad Down takes you into the lab from anywhere.

### Coming soon
- Weil Wind Tunnel
- Rogue Robot Roundup
- Data Packet Relay

---

## 3. Lake Alice
**Door:** Newell Hall · **Opens at:** 5★ · **Level slot:** `jrb` · **Code:** `uf_lake_missions.lua`

The real lake basin, with its islands, lily pads, cypress trees, the bat houses and the Baughman Center.

| # | Act | Type | Players |
|---|---|---|---|
| 1 | Boardwalk Welcome | Solo | 1+ |
| 2 | Gator Hop | Timed platforming | 1+ |
| 3 | Bat Census at Dusk - 2P | Co-op | 2–4 |

### Act 1: Boardwalk Welcome
- **Route:**
  1. Start at the bat-house field and cross Museum Road onto the north boardwalk.
  2. Wade onto the west bog.
  3. Hop **15 lily pads** out to the observation deck in the middle of the lake.
- **Hazards:** five Skeeters skate beside the pads, and two big gators lurk in the open water. The pads are the safe way across; swimmers get bitten.
- **Star:** on the far side of the deck.

### Act 2: Gator Hop
- **Goal:** start from the deck's big end pad. Hop **17 basking gators** across the deep hole to the gator nest on the small bog.
- **Timing:** the gators sink in a wave, **2.8 s up and 1.6 s under**. Every player sees the same timing.
- **Rules:**
  - Hop the gators in order. You may skip one.
  - Swimming straight to the nest doesn't count.
  - Two players on one gator sink it right away, so spread out in co-op.
- **Hazards:** three big gators patrol beside the line and snap at anyone in the water.

### Act 3: Bat Census at Dusk - 2P
- **Setting:** the act plays at dusk, and night falls during the count.
- **Posts:** 3 census posts, 67–136 m apart:
  - by the bat barns
  - in the Bat House Gardens
  - on the north boardwalk
- **Counting:** a post only counts bats while someone stands on it. Once **2 posts are staffed**, bats stream out of the barns for **90 s**.
- **Target:** **600 bats, plus 300 per extra player**, up to 1,500. One post alone can never make it.
- **Hazard:** Swoopers dive at the counters, one at a time, every **11 s**. A hit knocks you back without damage, and your count stops until you're back on your post.

### Coming soon
- Shell Surf Regatta
- Lost Hatchling
- Lily Pad Red Coins

---

## 4. Marston Science Library
**Door:** Marston · **Opens at:** 8★ · **Level slot:** `ccm` · **Code:** `uf_marston_missions.lua`

An interior stage, upgraded from 118 reference photos.
- **Floors:** five, 6 m apart. F1 is the basement and F2 is the entrance floor.
- **Atrium:** 13 × 15 m, open from the F2 court up to a skylight.

| # | Act | Type | Players |
|---|---|---|---|
| 1 | Out-of-Order Elevator | Solo climb | 1+ |
| 2 | Shhh! Lost Textbooks | Stealth collect | 1+ (shared) |
| 3 | Study Room Booking - 2P | Co-op | 2–4 |

### Act 1: Out-of-Order Elevator
- **Setup:** the elevator is out of order, and the stair halls on floors 1–4 are "closed for renovation".
- **Route:**
  1. The grand stair from the F2 lobby to the F3 balcony.
  2. A **book-cart lift** on the atrium's east side, up to F4.
  3. Around the F4 balcony.
  4. A second lift on the west side, up to F5.
  5. The F5 north reading room.
- **Lifts:** they chain, so lift B waits at F4 for a rider from lift A. The lifts are also safe from the books.
- **Hazard:** flying overdue books swoop at anyone on the F3 and F4 balconies. Duck or punch them.
- **Shortcut:** wall-kick up the broken elevator shaft, which is open on F2–F5.
- **The basement is closed:** sliding down the F2 book chute sends you back to the lobby.
- **Star:** in the F5 reading room.

### Act 2: Shhh! Lost Textbooks
- **Goal:** find **8 lost textbooks** on the silent 5th floor while **3 Shushers** (Toad librarians) patrol.
- **Noise:**
  - Running, jumping, landing and punching are loud.
  - Tiptoeing is silent: tilt the stick a little, or hold L / Left Shift.
  - Crawling (Z) is silent.
- **Markers:** each Shusher's marker shows how loud you can be at your distance.
  - green: you can run
  - white: walk
  - red: tiptoe only
- **Getting caught:** a Shusher catches you by hearing you, seeing you right in front of it, or bumping into you. It sends you back to the stairwell, with **no damage**.
- **Progress:** found books stay found and are shared by everyone.
- **Co-op trick:** a Shusher that half-hears someone stops and turns to look. One friend can lure it while another sneaks past.
- **Star:** at the west window desk, still on the quiet floor.

### Act 3: Study Room Booking - 2P
- **Kiosks:** booking kiosks on different floors.
  - **2 players:** 1F + 5F
  - **3 players:** 1F + 4F + 5F
  - **4 players:** all four floors
- **The trick:** each kiosk's screen shows the **other** kiosks' booking codes, 1–3 punches each, so players have to call codes out to each other.
- **Goal:** book every lit kiosk **within 4 s** of the first one. That opens glass room **L129** on F1, with the star inside.
- **Getting there:** your first trip to a kiosk has to be on foot. After that, D-pad Down returns you to a kiosk you've reached.

### Coming soon
- Lost Lab Notebook Pages
- Printer Jam
- Overdue Book Express

---

## 5. Library West After Dark
**Door:** Library West · **Opens at:** 11★ · **Level slot:** `bbh` · **Code:** `uf_west_library_missions.lua`

A night-time interior.
- **Floors:** six, 6 m apart, with Century Tower glowing through the windows.
- **Base and roof:** a three-storey base whose roof is a walkable terrace around the tower's 4th floor.
- **F5:** staff only in every act.

| # | Act | Type | Players |
|---|---|---|---|
| 1 | All-Nighter | Solo climb | 1+ |
| 2 | Coffee Run | Race | 1+ |
| 3 | Quiet Hours Hide & Seek - 2P | Hide-and-seek | 2+ |

### Act 1: All-Nighter
- **Goal:** climb from the lobby to the 6th floor's big window.
- **Setup:** the west and east stair halls are "closed for cleaning" below the 4th floor.
- **Route:**
  1. The stopped escalator.
  2. The 2nd-floor stacks. Rolling library ladders slide along the tall shelves; step up onto their tops.
  3. The NW or NE stair tower.
  4. Its roof door.
  5. Across the dark north roof terrace.
  6. The quiet 4th floor.
  7. A stair hall up to F6.
  8. The big window over the Plaza.
- **Sleepy Boos:**
  - They drift after you while your back is turned, and freeze while you face them.
  - A touch hurts and knocks you back.
  - A punch from close range sends one away for 15 s.
- **Shortcut:** wall-kick up the broken elevator shaft.
- **Star:** at the big window.

### Act 2: Coffee Run
- **Route:**
  1. Start at your desk in the F6 grad reading room.
  2. Run down a stair hall to F2.
  3. Go down the stopped escalator.
  4. Grab a cup at the lobby coffee counter.
  5. Bring it back up to your desk.
- **Times:** **par 1'00** earns the star. **Gold** is **0'45**.
- **With friends:** it's a race, with a results board and personal bests.
- **Hazard:** Boos haunt the stair landings. They knock you back without damage, which costs time.
- **Extras:** the HUD marker walks you through the route, and anyone carrying coffee wears the cup over their head.

### Act 3: Quiet Hours Hide & Seek - 2P
- **The seeker:** one player is the **night librarian**, drawn in metal with a lantern overhead. The role rotates each round.
  - 2 librarians with 5–8 players
  - 3 librarians with 9+
- **Hiding:** the librarian counts at the circulation desk with the screen dark for **25–30 s** while the hiders spread out.
- **Play area:**
  - **2 players:** F2 only
  - **3 players:** F2–F3
  - **4+ players:** F1–F3
- **Quiet hours:** **120 s** with 2 players, or 150 s by the design. A librarian finds a hider by touch, or by keeping the lantern beam on them for half a second.
  - The beam reaches 6 m, or 3 m if the hider crouches.
  - Shelves block it.
- **Found hiders** join the librarians.
- **Giveaways:**
  - Running, jumping or landing near a librarian shows a NOISE marker on the librarian's screen.
  - A hider who stays put for **45 s** sneezes, heard 20 m away.
  - Every **30 s** a chime tells the librarians which floor and side each hider is on.
  - Leaving the stacks for 4 s counts as being found.
- **Star:** every completed round with 2+ players puts the star on the circulation desk.
- **Results:** a board shows who survived, and each player keeps a running tally.

### Coming soon
- The Ghost of Finals Past
- Lights Out
- Re-shelve the Glowing Books

---

## 100-coin stars
Every built stage has a 100-coin star, star id 6.
- **Marston** places about 190 coins plus 5 Goombas, from the round-3 count. The other stages' counts aren't listed here.
- **The Reitz interior** (area 2) holds 84 coins inside, on top of the outdoor coins.

## Not built yet
- **Century Tower,** door 6 at 14★. Designed in `docs/game_design.md` section 7.6.
- **Bonus stages:** Smathers Stacks Slide and Finals Week Ascent. Designed in section 8.
- **Final Exam boss.** Designed in section 8.3.
- **Campus Secrets:** the castle secret-star slot has been renamed "CAMPUS SECRETS". No hub secret stars are listed here.
- **15 "COMING SOON" acts:** acts 4–6 of every stage, listed under each stage above.

## Handy commands
- `/campus <stage> <act> me`: jump straight into a stage and act, for example `/campus marston 2 me`.
- `/mission force`: runs a mission even if its stage check fails.
- **D-pad Down:**
  - races: back to the start box
  - Robotics Lab: into the lab
  - Study Room Booking: back to a kiosk you've reached
