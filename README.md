# Super Gatorlator 64

Our school in Super Mario 64, with online co-op and playable versions of our friends. Built as mods for [sm64coopdx](https://github.com/coop-deluxe/sm64coopdx).

## Setup (macOS)

1. Download `sm64coopdx_macOS_ARM.zip` from the [sm64coopdx releases page](https://github.com/coop-deluxe/sm64coopdx/releases) and unzip `sm64coopdx.app` into this folder.
2. Launch it once and drag your own **US** Super Mario 64 ROM (`.z64`) onto the window. ROMs are not included in this repo.
3. Install our mods:
   ```bash
   ./install-mods.sh
   ```
4. Restart the game, choose **Host**, open **Mods**, enable **Super Gatorlator 64**, and start the game.

## Layout

- `mods/sgl64/` holds the main mod: Lua scripts, friend models (`actors/`), portraits (`textures/`) and levels (`levels/castle_grounds` = the hub, `levels/bob` = The Swamp, `levels/wf` = Reitz Union & Engineering, `levels/jrb` = Lake Alice, `levels/sgl_test`). Each stage's missions are in their own file (`swamp_missions.lua`, `wf_reitz_missions.lua`, `uf_lake_missions.lua`).
- `docs/flow.md` is the level-flow contract (doors, warp nodes, stars, act order, load order); `docs/game_design.md` is the full design.
- `tools/campus/` builds the stages from campus data (`stage_pickups.py`: the coins, hearts, 1-ups, Goombas and poles of a stage); `tools/luatest/` checks the Lua offline.
- `install-mods.sh` copies `mods/` into the game's mods folder.

## Testing

Quick check: in game, type `/school` in chat. It should reply with "Super Gatorlator 64 is working!"

The full script below is also in `docs/flow.md` §10, where each step names the part of the level-flow contract it proves.

### Before the game (offline, about 1 minute)

```bash
tools/luatest/run.sh            # ends with "== all luatest checks passed"
tools/.venv/bin/python -I tools/blender/validate_level.py mods/sgl64/levels/castle_grounds   # 0 error(s)
tools/.venv/bin/python -I tools/blender/validate_level.py mods/sgl64/levels/bob              # 0 error(s)
tools/.venv/bin/python -I tools/blender/validate_level.py mods/sgl64/levels/wf               # 0 error(s)
tools/.venv/bin/python -I tools/blender/validate_level.py mods/sgl64/levels/jrb              # 0 error(s)
./install-mods.sh
```

Then start sm64coopdx → **Host** → an **unused save slot** (0 stars) → Mods: enable only **Super Gatorlator 64** → keep **Stay in Level After Star: Leave Level** → Host. The first launch compiles the levels (a few seconds). To see the first-time character menu again, delete `~/Library/Application Support/sm64coopdx/sav/sgl64.sav` (it stores your pick and your race best).

### Single player

1. **Spawn**: you land standing on the Plaza of the Americas facing south, with the University Auditorium ahead and no Peach intro (a fresh start has no spin-in; `/campus hub` and Pause → Exit to castle spin you in). The popup "Welcome to Super Gatorlator 64, <you>!" appears. The console shows no `[SGL]` errors.
2. **Character select** (first time only, about 1 s after landing): "CHOOSE YOUR GATOR!" with 10 cards, and nothing else drawn over it. Move with the D-pad, stick or arrow keys and pick with A (keyboard L). The menu says "HERE WE GO, <NAME>!", closes, and your model changes. L + START (keyboard Left Shift + Space), `/char` or Pause → Mods → "Choose your friend" reopens it; B or START closes it.
3. **Where to go**: about 1.5 s after the menu closes, the popup "Walk into the University Auditorium door to enter THE SWAMP!" and, for 20 s, a "NEXT: THE SWAMP" panel with a gold marker over the door (an arrow on the screen edge if the door is behind you).
4. `/campus list` shows `hub(castle_grounds)=ours, swamp(bob, door 1, 0*)=ours, reitz(wf, door 2, 2*)=ours, alice(jrb, door 3, 8*)=ours`, every other stage `vanilla`, and `stars 0, lives 4`.
5. **A shut door**: walk about 115 m north to Library West. Above its door are a see-through spinning star and red flames, with the label "LIBRARY WEST AFTER DARK / Coming soon". Walking into it gives "… is coming soon (opens at 14 stars)" and a buzz, and you stay put. Marston's and Century Tower's doors look the same. The Hub's and Newell Hall's doors look alike but say LOCKED: they open at 2 and 5 stars (see "Reitz & Engineering" and "Lake Alice" below).
6. **The Swamp door**: walk about 80 m south of the spawn to the Auditorium's centre porch door: gold star, no flames, "THE SWAMP / Walk in!". Walk in. Mario vanishes, the star fade plays, and the act select shows THE SWAMP with only act 1 "KICKOFF - CLIMB THE SKYBOX". Press A.
7. **Act 1**: you spin in on the Courtyard of Champions facing the stadium's north gate, with new music, a coin line to the gate and two Goombas in the way. The banner reads "THE SWAMP - ACT 1 / KICKOFF - CLIMB THE SKYBOX". The left panel shows "You 0 m team best 0 m goal 66 m" and 3 milestones, then shrinks to the height line. An orange "CLIMB HERE" marker points at the west rim. `/campus where` gives `level 9 area 1 act 1` and about `campus map: -513.5 m east, 273.0 m north`. `/mission` gives `… active, round 1, players 1/1, leader <you>`. If the panel says "Mission offline here", send the console line.
8. **Climb**: through the north gate, west along the concourse (coin lines), up the west stands to the west rim (20 m, a heart). The marker says "LEDGES": climb the 11 orange ledges (a coin on each) to the Bull Gator Deck (44 m, a heart). The marker says "CAMERA DECKS / POLE": hop up the 10 orange camera decks (coins, a heart half way) or climb the tall pole beside them and jump off its top onto the roof (66 m). Toasts appear at 20 m and 44 m, then "STAR!" on the roof. The star has been sitting on the roof all along. Grab it: after the star dance you fly out of the Auditorium door, see the course-complete screen, and end up outside it with **1 star**.
9. **Act 2, STADIUM STAIR SPRINT** (the act select now offers it):
   - Press **D-pad Down** (keyboard: `/mission start`) to teleport into the start box in the north end zone, or walk there. A 3-2-1 countdown runs (you are frozen), then GO!, the race music and a timer.
   - Follow the blue CP markers: NE corner → east field wall → east stands → east rim (coins, a Goomba) → round the south-east rim (another Goomba) → South Ramp terrace (FINISH).
   - Under 1'10: the star drops onto the terrace; grab it for **2 stars**. Under 0'45: "GOLD TIME!". Over 1'10: TRY AGAIN; D-pad Down takes you back to the box. Note whether par and gold feel fair.
10. **Act 3 alone**: the act select offers "GATOR CHOMP CHORUS - 2P". Alone online, the prompt says "This act needs 2 players - you are the only one online". Pause → EXIT COURSE puts you outside the Auditorium with no life lost.
11. **A coming-soon act**: `/campus swamp 4 me`. The banner reads "COMING SOON - MASCOT / No mission here yet - explore! …" and the panel stays up for 20 s. There is no star. Pause → EXIT COURSE returns you to the Auditorium.
12. **100 coins**: there are 142 coins in The Swamp (plus one per Goomba). Collecting 100 in one visit brings out the 100-coin star.
13. **Exits and lives**: Pause → EXIT TO CASTLE takes you to the Plaza. Drowning in the Florida Pool (east of the stadium) throws you out of the Auditorium door with −1 life, and the hub refills lives to 4.
14. **Remembered pick**: quit and host again. No menu opens, a "Playing as <X>" popup appears, and you have your friend's model.

### With a friend

1. The friend joins and spawns on the Plaza, and their character menu opens if they have never picked. Each of you sees the other as the picked friend. In the menu (L + START), your friend's card shows their name tag and yours says YOU.
2. **Invite**: the host enters the Auditorium (act 1). The friend gets the popup "<Host> started THE SWAMP act 1 … D-pad Up or /join to follow!" and a 10 s prompt. They press D-pad Up (keyboard: type `/join`, or Pause → Mods → "Join my study group") and land in the same act; you see each other. `/mission` gives `players 2/2, leader <Host>`.
3. **Shared star, leaving together**: whoever grabs the roof star leaves with the course-complete screen. The other sees the star vanish and "Star collected by <name>", plus the prompt "<name> got the star! D-pad Up: back to campus together". D-pad Up lands them outside the Auditorium too (no life lost). Both counters go up.
4. **Co-op act 3**: get both of you into act 3 (the act select once you have 2 Swamp stars, or `/campus swamp 3` from the host).
   - After 3 s, two end-zone corner buttons light up with red flames: north-west and south-east (3 or 4 corners light up with 3 or 4 players). Stand on one each: the flame turns blue.
   - The HUD counts "GA..." and "TOR...", then "CHOMP!": both of you jump and ground-pound (Z) on your button within about 1.3 s.
   - "CHOMP! Phrase 1/3": the other two corners light up; run there (47 m) and do it again, then once more on the first pair. After the third phrase the star flies from the south scoreboard to midfield.
   - Pounding late or stepping off during the count: "Off the beat!" and that phrase starts again. Leaving the act shows "Paused: waiting for enough players".
5. **Race together** (act 2): with both of you in the start box the countdown starts at once. If only one of you is in, a 10 s lobby wait runs first. The results board lists both times. If one of you leaves mid-race, the results come at once.
6. **Leader hand-off**: in act 1 or 2 the host types `/campus hub me`. The mission keeps running for the friend, and `/mission` names them as leader.
7. **Only the host moves everyone**: the friend's `/campus swamp 2` moves only the friend ("Only the host moves everyone; warping just you.").
8. **Late join**: a third player who joins mid-game types `/join <host name>` to land in your act.
9. With an invite showing, open the character menu: the prompt is hidden, and D-pad Up moves the cursor instead of joining.

### Reitz & Engineering (course 2, The Hub door, 2 stars)

1. **Locked**: with fewer than 2 stars, walk about 325 m south-west of the Plaza to The Hub's south entrance. It shows a see-through star, red flames and "REITZ & ENGINEERING / LOCKED - 2 stars (you have N)"; walking in gives "Locked! … needs 2 stars" and a buzz.
2. **Hint**: with The Swamp's acts 1 and 2 done and nobody else online, every hub arrival shows "NEXT: REITZ & ENGINEERING / THE HUB door - walk in!" with a marker (The Swamp's act 3 needs a friend). The first hub visit of a session also says "Walk into The Hub door to enter REITZ & ENGINEERING!".
3. **Open**: with 2 stars the door has a gold star and "Walk in!". Walk in: the act select shows REITZ & ENGINEERING with act 1 "ROOFTOP OF THE REITZ".
4. **Arrival**: you spin in on the North Lawn about 40 m north-east of the Reitz Union, facing south-west at it: the glass east wing with its diamond pattern on the left, the brick tower in the middle, the north colonnade. New music (the Lethal Lava Land theme), a coin line ahead and a Koopa shell to your left. The banner reads "REITZ & ENGINEERING - ACT 1 / ROOFTOP OF THE REITZ" and an orange "CLIMB HERE" marker points a little left, round the building. `/campus where` gives `level 24 area 1 act 1` and about `campus map: -398 m east, -200 m north`.
5. **Act 1 climb**: on the ravine side (the Reitz Union's south-west corner): brick terraces (1.5 / 3 / 4.5 m) → three copper awnings (6.7 / 8.9 / 11.1 m) → ballroom roof (13.2 m, toast, a Bob-omb) → podium roof (17.6 m, a heart and a Goomba). A checkered **window-washer lift** shuttles up the tower's west face (about 2 s wait, 5 s ride): ride it to the parapet (27 m) and **step** east onto it (the deck stops 10 cm from the parapet: no jump needed), drop onto the tower roof (another Bob-omb), climb onto the elevator penthouse (28.8 m): "STAR!" and the star drops in. A jump beside the penthouse does not count; you have to land on its roof. The cable pole beside the lift and the ledges on the tower's east face also work. Grab it: you fly out of The Hub's door with the course-complete screen. Check the lift carries you smoothly, also right after a friend joins.
6. **Act 2, MEAL SWIPE TOKENS**: 8 big red tokens; the panel names the nearest and its distance. They are on the Gator Corner patio table (far west), the steel sculpture on the Engineering Plaza (4 m: triple jump, or the two blue step plates on its west column), the Liberty Pond fountain float (swim), the Bookstore's east awning (3 m), the ravine boardwalk, **Weil Hall's 24 m roof ridge** (climb the copper downspout in its east courtyard, then the roof stair), **Malachowsky's glass stair** (the 12 m glass box; run up from the planter and the canopy) and the Weil Cooling Towers' roof (10 m, ledges on the east face; louvred walls and two fans on the roof). Coin lines mark the long walks between them, and the three Koopa shells (North Lawn, Engineering Plaza, Reitz Union Drive) let you surf across. The star pops out right where you find the 8th token. Check every token can be reached and none has a yellow coin inside it. To replay, `/mission reset`: the next round's star appears too (up to 8 stars per visit, then the panel asks you to re-enter the act).
7. **Act 3 alone**: "This act needs 2 players". The panel says "D-pad Down: into the Robotics Lab": press it (or `/mission start`) and you land in Malachowsky's atrium by the consoles. Pause → EXIT COURSE puts you outside The Hub with no life lost.
8. **Look around** (any act; `/campus reitz 4 me` is a coming-soon free-roam act): Malachowsky Hall's glass stair (planter → canopy → 11 glass boxes → roof 33 m → penthouse 37.7 m, a 1-up; a coin ring on the rooftop terrace), its atrium through the north door, Weil Hall's roof run (copper downspout in its east courtyard → steel roof stair → the 24 m ridge → tower deck, a 1-up), the coins on top of the Reitz north colonnade, the Reitz food court (South Terrace), the ravine boardwalk, the wind-tunnel vent by the cooling towers and the robot dock by Liberty Pond. 100 coins (there are 254 plus 8 Goombas; 249 in act 2) bring out course 2's 100-coin star. Drowning in Liberty Pond throws you out of The Hub's door with −1 life.
9. **With friends, act 3 REMOTE ROBOTICS LAB - 2P** (`/campus reitz 3` from the host; D-pad Down takes anyone into the lab):
   - One player stands on the lit purple console: the flame turns blue and the panel says "You drive crane 1: stick moves it, B lets go" (B no longer punches). A second player stepping onto the same console waits ("Console 1: <name> is driving") until the driver steps off. A small side view of the lane appears on the right: grey bars, red locked gaps, yellow "!" boxes, the blue crane, green riders, red Amps.
   - The other player boards the checkered crane. Stick up raises it until **gate 1 (locked)** stops it 2.8 m under the bar: "Gate 1 is locked: rider, jump into the ! box". The driver moves the crane under the yellow "!" box (gold "! BOX" marker), the rider walks to it on the deck and jumps into it: "Sensor hit! Gate 1 is open", the box and the red flames in the gap vanish. Then the driver lines the crane up under the narrow gap (orange "GAP" marker, ±0.5 m) and goes up to the next gate. Five gates; the gaps sit at different places every round, never at a wall. The circling Amps are at the rider's height while the crane waits under gates 3 and 5: jump them or park away from the middle.
   - At the top, step south onto the star ledge: the star rises from the floor to the ledge.
   - 3 players: 2 riders needed, both may ride. 4 players: the east console drives crane 2, 2 riders are needed and a crane lifts **one** rider ("Too heavy! Crane 1 lifts 1 rider"), so use both cranes (or make two trips). Note the crane speed, the steering, the "!" box and gap sizes, and whether the rider jitters.
10. **Shared acts**: in act 1 both of you see the lift at the same height; in act 2 the token count is shared ("<friend> found the … token!").

### Lake Alice (course 3, Newell Hall door, 5 stars)

Playing alone you can only get 6 stars so far (both stages' acts 1-2 and their 100-coin stars; the two act 3s need a friend), so play the co-op acts first or jump in with `/campus alice <act>` from the host.

1. **Locked**: with fewer than 5 stars, walk about 225 m west-south-west of the Plaza to Newell Hall's east entry (at the top of a short stoop). It shows a see-through star, red flames and "LAKE ALICE / LOCKED - 5 stars (you have N)"; walking in gives "Locked! … needs 5 stars" and a buzz.
2. **Hint and open door**: with 5 stars, the first hub visit says "Walk into the Newell Hall door to enter LAKE ALICE!" and a "NEXT: LAKE ALICE" panel points at the door. The door has a gold star and "Walk in!"; walk in and the act select shows LAKE ALICE with act 1 "BOARDWALK WELCOME".
3. **Arrival**: you spin in on the bat-house field with the two bat barns behind you (a white one and a brown one, on legs behind black fences) and, ahead, Museum Road and a view down to the lake: the north boardwalk, the west bog, a line of lily pads and a pavilion on a deck in the middle. The music is Jolly Roger Bay's. The banner reads "LAKE ALICE - ACT 1 / BOARDWALK WELCOME", an orange "BOARDWALK" marker shows the way, five Skeeters skate on the water and two big gators (shark stand-ins) cruise beside the middle of the pad line. `/campus where` gives `level 12 area 1 act 1` and about `campus map: -1893 m east, -541 m north`.
4. **Act 1**: cross the road onto the north boardwalk, wade onto the west bog (a gator statue suns itself on it), then hop the 15 lily pads (the marker says "PAD k"; a coin floats over each but pad 5; the gaps get wider). If you fall in around pads 3-6 or 9-13, a lurking gator comes for you ("CHOMP! A gator - back onto the lily pads!", one wedge, knocked back): swim to a pad and press A at the surface to jump back on; on a pad you are safe. From the last, big pad jump onto the deck: "STAR!", and the star arcs in from over the water to the deck's far side, past the pavilion (it no longer flies through the roof). Grab it: you fly out of the Newell Hall door with the course-complete screen. Also check that swimming next to the deck does not count, that you can climb onto the deck from the water, and that the pavilion roof (double jump) has a 1-up.
5. **Act 2, GATOR HOP**: press **D-pad Down** (keyboard: `/mission start`) to land on the deck. Hop onto the big pad, then along 17 basking gators (shark stand-ins, sized so their backs are the platforms) heading north. Each one sinks for about a second in a wave, so time your hops; the marker says "GATOR k". Fall in anywhere past the second gator and a big gator chases and bites you ("CHOMP!", one wedge, knocked back); on a gator's back you are safe. After the last gator, step onto the small bog with the nest: the star drops in beside the nest mound. Swimming straight to the bog does not count ("hop ALL the gators"). Note whether the stand-in gators look right (the shark's back should be level with what you stand on) and whether the timing feels fair.
6. **Act 3 alone**: "This act needs 2 players", and the lake turns to dusk (orange light, purple sky). Pause → EXIT COURSE puts you outside Newell Hall in daylight, with no life lost.
7. **With friends, act 3 BAT CENSUS AT DUSK - 2P** (`/campus alice 3` from the host):
   - The panel says "Bats to count: 900 - staff 2+ census posts!" and red POST markers show the three posts (by the bat barns, in the Bat House Gardens, on the north boardwalk). D-pad Down puts you on a free one.
   - With two posts staffed: a 3-2-1 countdown, "BATS OUT!", spooky music, bats streaming out of both barns **over your own post** (each player sees the swarm pass over theirs), and a Swooper diving at each counter every ~11 s for the whole count, one at a time (each vanishes in a puff after its pass). A Swooper hit costs no health; it knocks you back, and your post stops counting until you are back on it. The panel shows each post's share ("Bat barns - counting   +312").
   - About 900 bats in about 70 s while the sky turns to night: the star flies out of the white barn onto the barns' post.
   - Both of you on one post: the count starts after 60 s anyway and falls short ("Not this time"), then a new round starts. With 3 or 4 players the target is 1200 or 1500.
   - Leaving the act brings the daylight back at once.
8. **Look around** (any act; `/campus alice 4 me` is a coming-soon free-roam act): spot the six basking alligators (statues on the two bogs and at the waterline round the lake; you can stand on their backs); swim anywhere in the lake (you never pop out of the water inside its shore) and dive into a deep hole (coin rings; a 1-up at the bottom of the deepest, south of the small bog); climb a bat-cam pole onto a barn roof (the brown barn's side box has a 1-up); climb a Museum Road street light or a cypress trunk; walk the Baughman Center's footbridge and climb porch → vestibule → aisle roofs (the steep copper roof slides you off); visit the east overlook. The water music thins out south of the deck and on high roofs (that is Jolly Roger Bay's own music behaviour): say if it bothers you. 100 coins (176 in the level, plus 5 Goombas) bring out course 3's 100-coin star. Losing all your health throws you out of the Newell Hall door with −1 life.
9. **Shared acts**: in act 1 the panel shows the team best ("Lily pads: you k/15   team best n/15"); in act 2, two players on one gator sink it at once ("Too heavy!") on both screens.

Shortcuts: `/campus swamp 1|2|3 [me]`, `/campus reitz 1|2|3 [me]`, `/campus alice 1|2|3 [me]`, `/campus hub`, `/campus where`, `/mission`, `/mission reset`, `/mission start`, `/join [name]`.

## Campus data

The UF campus stages are generated from [OpenStreetMap](https://www.openstreetmap.org/) data.
Map data © OpenStreetMap contributors, available under the
[Open Database License (ODbL)](https://www.openstreetmap.org/copyright).
`tools/campus/osm_extract.py` turns the raw tiles (see `data/uf/SOURCE.txt`) into `data/uf/campus.json`.
