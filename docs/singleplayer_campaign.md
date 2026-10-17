# Single-player gameplay spec

**Status:** design proposal for review. This describes the intended complete game; it does not claim that every listed act is implemented. Co-op is out of scope for this pass.

## 1. Player promise

Play as a UF friend in a Super Mario 64 style campus adventure. Explore recognizable places, use the familiar movement kit to reach surprising routes, earn stars from short authored challenges, and climb Century Tower for the Final Exam. The whole campaign works offline with one player. An optional DeepSpace leaderboard adds asynchronous score chasing after the local game loop is fun; no account is needed to start or finish the game.

### Design rules

- **Movement is the toy:** running, triple jumps, wall kicks, backflips, swimming, shell surfing, and Wing Cap flight solve most problems.
- **Each course feels like its real place:** the stadium is broad and vertical, Lake Alice is open and watery, and the two libraries reward quiet navigation.
- **Teach, then test:** every act shows its mechanic safely before combining it with a more demanding route.
- **Failure costs time, not progress:** retries are unlimited; collected stars and unlocked doors stay saved.
- **No online dependency:** local save data is authoritative for the campaign. Account sync and leaderboard results are optional.

## 2. The gameplay loops

### Moment-to-moment loop: about 5–30 seconds

1. Read a landmark, route marker, enemy tell, or objective counter.
2. Choose a movement line: run-up, jump, wall kick, pole, lift, shell, or cap.
3. Make the jump or interact with the obstacle.
4. Recover from a miss using the nearest safe platform, checkpoint, or course entrance.
5. See clear feedback: a token counter changes, a route marker advances, an enemy reacts, or the objective updates.

Avoid long text during active play. Explanations appear before the challenge or in short HUD prompts.

### Mission loop: about 2–8 minutes

1. Choose an act from the course door's act-select screen.
2. Spawn at the act's start point. Show the title, one-line goal, and first landmark.
3. Start the official run clock when control is handed to the player.
4. Complete the objective. Show only the progress information needed for that act: route checkpoints, tokens, noise, remaining time, or boss phase.
5. Spawn the star at the goal. The clock stops when the player collects it.
6. Show a result card with mission time, retries, and local personal best. Save the star and result immediately.
7. Return to the hub outside the course door, or let the player replay the act from its act-select screen.

### Course loop: about 20–45 minutes

Each campus course has six authored acts and a 100-coin star. The acts vary the movement skill: climb, race, puzzle, boss, collection, and a course-specific movement challenge. The player can leave and return without losing stars. New doors appear as the total star count rises.

### Campaign loop: about 3–6 hours for the main route

Start in the Plaza of the Americas, clear enough stars to open the next building, visit all five campus courses, enter the Century Tower course, then collect 30 stars to open Finals Week Ascent and The Final Exam. Players who want more can finish the 52-star set and improve course records.

### Leaderboard loop: optional replay

1. The local results card always shows the personal best first.
2. If the player has opted in and sync is available, upload that completed run and fetch the mission's current record list.
3. Visit the in-game **Record Board** in the Plaza to inspect global mission times and the player's own rank.
4. Select a completed act at its course door, replay it, and try to improve the time.

The board compares a player only with runs of the same act. It does not award required stars, unlock routes, or interrupt gameplay with sign-in. Online entries are casual records unless a server-side validation system is added; local scores remain available offline.

## 3. Campaign flow and progression

### Opening ten minutes

1. The game opens on character select; choosing a character starts a new or existing save.
2. The player appears in the Plaza with Century Tower visible as the long-term goal.
3. A short movement route teaches a triple jump, a wall kick, and a safe return to the plaza. It does not demand precision or award a mandatory star.
4. The University Auditorium door points to The Swamp, the first open course.
5. The first act, **Kickoff – Climb the Skybox**, teaches the main promise: read the stadium, find a route, climb, collect a star.
6. The hub signpost points out the next star threshold and names the next campus building.

### Door order

Use the star gates already represented by the current hub: The Swamp opens at 0; Reitz at 2; Lake Alice at 5; Marston at 8; Library West at 11; Century Tower at 14. Finals Week Ascent opens at 30 stars. Keep these numbers visible at the locked door and on the hub map.

The current tree allows players to skip optional acts. Each course has enough stars to move forward without perfect race times or hidden collectibles. Confirm the actual collectible count in a fresh save before tuning any gate.

### Star budget target

The larger design target is 52 stars:

- Six courses (five campus courses plus Century Tower), each with six act stars and one 100-coin star: 42.
- Plaza / campus secrets: 7.
- Smathers Stacks Slide: 2.
- Finals Week Ascent red-coin star: 1.
- **Total: 52.** The Final Exam's Grand Star is the ending reward; confirm during implementation whether it also increments the save's star counter.

This is the full-game target, not the current implemented count. First replace each course's currently co-op-only third act with its solo design and playtest acts 1–3 from a fresh save. Then add acts 4–6 in order so the act-select screen never depends on a missing earlier star.

## 4. Mission rules shared by every act

### Start and objective

- Start each act at a safe point with the camera aimed toward its first landmark.
- Show the objective in one sentence and identify the first route cue.
- A personal-best timer starts only when control begins. Briefing time and pause time do not count.
- Long acts use a visible midpoint checkpoint. Re-entering after a fall returns the player to the last checkpoint where practical.

### Failure and retry

- A fall or hit resets the player to a nearby safe point and removes a small number of carried coins, following familiar SM64 expectations.
- A timed challenge may continue after a hit if recovery is possible; otherwise it returns the player to the start and records a retry.
- Restarting an act is immediate and explicit. No lives or collected stars are consumed.
- Leaving a course returns to the hub and preserves saved stars, unlocked doors, and local bests.

### Scoring and records

- **Star condition:** one clear objective per act. Do not make leaderboard placement part of the star condition.
- **Official time:** act start to star collection, including time spent after retries. Restarting does not erase elapsed time in a leaderboard run; choosing “new run” at the act-select screen begins a fresh attempt.
- **Tie-break:** fewer retries, then earlier recorded time.
- **Stored result:** unique run ID, act ID, elapsed frames, retry count, date, and game version. Upload only when the player has opted in.
- **Local first:** save the local result before attempting any network operation. A sync error never blocks the result screen.

## 5. Campus course acts

Every act below is designed for one player. The list follows the six-act structure in `docs/game_design.md`; several later acts are proposed content, not claims about the current build.

### Course 1 — The Swamp / stadium

**Course identity:** stadium-scale traversal, crowd energy, big jumps, and one short precision rhythm challenge.

1. **Kickoff – Climb the Skybox** — The player begins at field level and follows coin lines to the stadium rim. Climb the concourse ramps and upper deck, use the pole to reach the press-box roof, and collect the star. Milestones name the rim, camera deck, and pole. A fall before the midpoint returns to the rim; after the midpoint it returns to the camera deck.
2. **Stadium Stair Sprint** — Race the water-boy NPC from the north end zone up the east stands, around the rim, and down to the South Ramp terrace. Nine checkpoints prevent cutting across walls. Target par is 70 seconds; a faster gold target is 45 seconds, to be tuned in playtests. The NPC gives a visible lead marker. The race is replayable even after its star is earned.
3. **Gator Chomp Chorus** — A single-player rhythm minigame on the end-zone pads. The scoreboard demonstrates a four-beat phrase; the player moves to the lit pad and ground-pounds on the “CHOMP” beat. Complete three phrases that add one beat or a pad change each time. A miss repeats the current phrase, not the whole act. Initial timing window target: ±0.2 seconds.
4. **The Visiting Mascot** — A slow, readable boss. The inflatable mascot bounces across midfield; its landing has a clear shadow and sound cue. After landing it is vulnerable for three seconds while three colored air valves are exposed. Ground-pound one exposed valve per cycle; three successful cycles deflate it. A hit knocks the player back but does not erase completed valve hits.
5. **Tailgate Tokens** — Find eight orange-and-blue pennant tokens across the tailgate lots, Gator Sportshop roof, gator-statue plinth, bleachers, South Ramp, arena entry, scoreboard, and tunnel. Coin trails hint at long jumps; the HUD identifies the nearest remaining token without showing its exact position. The star appears at the last token.
6. **Flyover!** — Take a Wing Cap from the scoreboard and fly through eight large banner rings above the stadium and Exactech Arena. Rings are grouped into two legs with a cap refresh between them. Missing a ring leaves the route recoverable; falling returns the player to the scoreboard. The final ring points to the star landing.
7. **Team 100** — Collect 100 coins around the stands, concessions, and tailgate lots. Red coins are not required for this star. A coin counter and a few coin trails make the route readable; the star appears at midfield.

### Course 2 — Reitz Union + Engineering

**Course identity:** rooftops, lifts, engineering machinery, and short route-planning challenges.

1. **Rooftop of the Reitz** — Climb terraces and awnings, board the window-washer lift, and jump from its top to the roof. The lift stops at a safe intermediate balcony. The star is placed where the player can see the next course landmark.
2. **Meal Swipe Tokens** — Find eight golden tokens around Gator Corner, Engineering Plaza, Liberty Pond, the bookstore awning, the ravine boardwalk, Weil roof, Malachowsky stair, and cooling towers. Each token is reachable with standard moves; optional shells shorten travel but are not required.
3. **Remote Robotics Lab — solo trial** — Replace operator/rider play with one-player control. Three floor consoles select the crane's next fixed stop. Reach a console, choose a lit floor, then ride the crane through the atrium. Avoid hanging cable bundles and swinging sensor arms. The platform pauses at every landing so the player can dismount safely. The last stop reaches the star ledge.
4. **Weil Wind Tunnel** — Ground-pound the floor switch to start the vertical fan. The fan stays active long enough for one complete climb if the player follows the wind stream and lands on the maintenance ledges. A visible countdown warns before spin-down. The switch can be reactivated without restarting the act.
5. **Rogue Robot Roundup** — Five delivery robots flee across the North Lawn. Approach from ahead, grab one, and carry or throw it into the charging dock by Liberty Pond. A robot dropped outside the dock runs again after a short pause. Each docked robot stays counted; after five, the star appears on the dock.
6. **Data Packet Relay** — Carry a glowing data packet from Weil's server closet to Malachowsky's server room. It drops if Mario takes a hit; the timer continues. Two marked recovery points prevent a single mistake from wasting the run. Target par: 75 seconds, tuned after playtesting. The shortest route uses the North Lawn cannon, while the safer route uses the engineering walkways.
7. **Team 100** — Collect 100 coins through the food court, plazas, and engineering quad. Coins mark the main circuit; small groups reward exploring balconies and courtyards.

### Course 3 — Lake Alice

**Course identity:** water routes, timed platforms, wildlife, and shell movement.

1. **Boardwalk Welcome** — Follow the marsh boardwalk, cross a short lily-pad route, and reach the lake observation deck. The first pads are broad and stationary; later pads drift or bob. Water provides a safe recovery route, with a return ladder near the start.
2. **Gator Hop** — Cross the deep-water gap on basking gators. Each gator stays above water for three seconds and below for two. The first pair share a cycle; later pairs use offset timing. A large gator jaw gives a visible snap warning before it becomes hazardous. Falling returns the player to the last bank.
3. **Bat Census at Dusk — solo survey** — Follow three marked bat flights between the bat houses, gardens, and boardwalk. At each station, hold position long enough to record a passing wave; the HUD shows silhouettes captured and the next flight direction. Complete six waves before the dusk timer ends. A dive-bombing bat interrupts a reading but does not reset previous stations.
4. **Shell Surf Regatta** — Take a shell from the dock and pass through eight buoy checkpoints around the lake. Checkpoints are tall and forgiving; the route has one safe shoreline to recover a lost shell. Target par: 75 seconds. The timer stops at the final buoy; the star appears at the dock.
5. **Lost Hatchling** — Find the baby gator near Museum Road, pick it up, and return it to the nest island. Carrying reduces top speed and prevents attacking; throwing across short water gaps is allowed. A drop near shore makes the hatchling wait, while a drop in deep water returns it to the last safe bank.
6. **Lily Pad Red Coins** — Collect eight red coins on lily pads, bat-house roofs, garden trellis, cypress knees, and the boardwalk underside. A route preview shows a few landmark silhouettes, then the player chooses the order. The final coin spawns the star on the observation deck.
7. **Team 100** — Gather 100 coins along the boardwalk, island, gardens, and bat-house parking edge. Coins above water have safe platforms or ladders nearby so exploration does not become repeated swimming from the beginning.

### Course 4 — Marston Science Library

**Course identity:** vertical indoor traversal, quiet movement, and machinery puzzles.

1. **Out-of-Order Elevator** — Climb the central atrium by riding moving book carts, jumping across shelf tops, and wall-kicking in the stairwell shaft. Falling from the upper floors returns the player to the nearest lower landing. The route marker highlights the next floor, not every jump.
2. **Shhh! Lost Textbooks** — Search the quiet floor for eight misplaced books while avoiding Shusher robots. Walking and crouching are quiet; running, hard landings, and ground pounds raise a noise meter. At high noise a nearby Shusher investigates. Being caught returns Mario to the stairwell and leaves already found books in place.
3. **Study Room Route — solo puzzle** — A kiosk flashes a three-symbol floor sequence, then hides it. Visit the rooms in order and press each booking panel. Later rounds add one symbol and an alternate stair route. A mistake resets only the current sequence. The glass study room opens when the sequence is complete; the star is inside.
4. **Lost Lab Notebook Pages** — Find eight pages in the stacks, makerspace, vent duct, atrium light, and return chute. Each page has a brief paper-flutter sound, and the HUD points to the nearest uncollected page only when the player asks for a hint.
5. **Printer Jam** — A two-head 3D printer swings its print heads over a marked floor. After each slam, one reset button glows for three seconds. Ground-pound it, avoid the next swing, then repeat until both heads are reset three times. Each head has its own clear sound and color, and progress persists through a hit.
6. **Overdue Book Express** — Pick up an overdue book on the fifth floor and deliver it to the lobby return slot within 45 seconds. Carrying it limits running speed but leaves jumps available. The atrium has safe drop ledges and a chute shortcut; a hit drops the book without resetting the timer. Reaching the slot completes the act.
7. **Team 100** — Collect 100 coins through the stacks, atrium, and makerspace. Use the same quiet/noise rule only in the Shusher area so the coin hunt remains a movement challenge, not a stealth repetition.

### Course 5 — Library West After Dark

**Course identity:** nighttime atmosphere, vertical indoor movement, ghosts, stealth, and light puzzles.

1. **All-Nighter** — Climb from the lobby to the top-floor reading room using book ladders, balconies, and stairwells. Boos patrol predictable paths. Looking directly at a Boo makes it harmless; punching removes it briefly. A ladder at each floor gives a safe return route.
2. **Coffee Run** — Start on the fifth floor, pick up a coffee cup at the lobby counter, and carry it back to the top reading room. Boos block some stairwells; the cup slows Mario but does not remove jumps. Target par: 60 seconds. If hit, the cup drops and can be picked up again; the clock keeps running.
3. **Quiet Hours Patrol — solo stealth** — Avoid an AI night librarian and collect three library cards from the stacks before reaching the circulation desk. The librarian follows a visible patrol path and reacts to line of sight and loud landings. Book alcoves break sight. If spotted, the player is escorted to the lobby; collected cards remain, so the route can be completed on another attempt.
4. **The Ghost of Finals Past** — Clear one small Boo from each floor, then bait Big Boo into turning around and ground-pound it three times. A successful hit requires facing away from the player; the tell is a short spin and sound cue. Damage does not reset cleared floors.
5. **Lights Out** — The library begins dark, with a small local light around Mario. Find and ground-pound three breaker switches on different floors. Each breaker restores one section of lights and reveals the route to the next floor. A fall returns to the last powered landing; completed breakers stay on.
6. **Re-shelve the Glowing Books** — Find eight glowing books that have escaped their shelves. Coins and colored shelf labels suggest each floor. The player can collect them in any order; the last one appears at the lobby return desk.
7. **Team 100** — Collect 100 coins through the lobby, stacks, and reading floors. Boos remain hazards but are slower than in the timed Coffee Run. Desk lamps and window light keep the paths readable.

### Course 6 — Century Tower

**Course identity:** an original clockwork climb inside a tower whose real exterior remains campus-scale. The interior is intentionally larger than the real footprint to support platforming.

1. **Up the Bell Tower** — Climb through gears, pendulums, treadmills, and moving bars to the bell chamber. Safe ledges sit before every major obstacle. The star is on the bell platform.
2. **Carillon Concert — solo memory game** — Listen to and watch a short bell melody, then ground-pound bells in the same order. Three rounds increase from four to six to eight notes. A wrong bell repeats the current melody; it does not reset the whole act. Bells are arranged so the longest route is still reachable with ordinary jumps.
3. **Clockwork Red Coins** — Collect eight red coins on rotating gears, pendulum platforms, and the inside rim of the shaft. A gear stops briefly when Mario lands on its center, creating a safe decision point.
4. **Race to the Top** — A solo time trial from the base to the top bell. Follow six checkpoints through the same route used by the climb act. Target par: 90 seconds. The run is scored only by the official clock, not by a network ghost.
5. **Stop the Clock** — Ground-pound the base pressure plate to freeze the machinery for 12 seconds. Climb through the now-still gears and reach the star behind the gear wall before motion resumes. Multiple plates on higher landings renew the window; the challenge is route planning under a timer.
6. **Ring the Outside Bells** — Take the Wing Cap from the top window and fly around the tower exterior to hit four large bells. Each bell makes a distinct sound and lights up. A cap refresh at the halfway point makes the route forgiving; missing a bell returns Mario to the launch ledge.
7. **Team 100** — Collect 100 coins on the gears and bell landings. Coin trails signal safe timing windows without forcing a single path.

## 6. Hub and bonus activities

### Plaza of the Americas

The hub is a playable place, not a menu. It contains the course doors, visible Century Tower goal, character pick, progress map, and the in-game Record Board. Add seven secret stars for optional movement challenges: rooftop routes, hidden coin rings, a fountain jump, and a short landmark circuit. Each secret gets a clue on the campus map after the player has explored nearby.

### Smathers Stacks Slide

A short bonus course entered from Smathers Library. Slide through a winding stack-and-map-room route. Earn one star by finishing; earn a second by finishing under the target time. The second star is a replay reward, never required for the next door.

### Finals Week Ascent and The Final Exam

At 30 stars, a door at Century Tower opens to a night-time climb above the campus. Jump across oversized textbooks, avoid flying red pens and falling books, and reach the exam arena. The boss has three readable phases: dodge a moving desk, ground-pound exposed answer buttons, then return a flying blue book to the right shelf. A wrong shelf resets only that phase. Defeating the boss triggers the Grand Star and graduation ending. The approach's eight red coins award one optional star.

## 7. The in-game Record Board

### What the player sees

- One row per act: act name, best time, rank, and whether the result is local or synced.
- Filters: course, all courses, and personal bests.
- A selected row shows top times and the player's own position even if it is outside the top list.
- The player can hide public display name or use a chosen in-game name. Email is never shown.

### What gets recorded

Record one entry for each completed attempt: act ID, duration in frames, retry count, completion date, game version, and a random run ID. The local game save is the source for stars and the local best. DeepSpace receives only opted-in score entries. The board sorts fastest time first, then fewer retries; it never compares different acts.

### How DeepSpace fits

DeepSpace is the asynchronous records service. It does not host the single-player world or need real-time players. An optional account lets the player sync a name and submit or read scores. The game must continue when logged out, offline, or when sync fails. The current SM64CoopDX Lua mod does not itself provide a documented DeepSpace client, so implementation needs a native bridge or local helper before the board can be connected. Do not place client secrets or long-lived bearer tokens in Lua.

## 8. Difficulty and accessibility

- Put a safe landing or recovery route near every required precision jump.
- Give each hazard a visible tell before it can hit the player.
- Keep mission goals short; a long course can have a midpoint checkpoint.
- Show optional hints on request. Hints identify the next landmark or remaining collectible, not the full route.
- Avoid color-only signals: pair color with shape, label, sound, or animation.
- Do not require leaderboard performance, one-life runs, or a perfect streak for a star.
- Keep act replay reachable from the door after collecting its star.

## 9. Suggested build order

1. Lock the solo mission rules, official timer behavior, and result-card fields.
2. Make all currently playable acts completable by one player; replace the five co-op-only mechanics with the solo versions above.
3. Add remaining acts in course order so vanilla act-select progression never hits a missing star.
4. Add Team 100 stars, hub secrets, and the Smathers slide; verify the star budget from a fresh save.
5. Build Century Tower and test the 14-star course gate.
6. Build the 30-star finale and graduation sequence.
7. Add the local Record Board and personal-best display.
8. Connect optional DeepSpace result sync only after the offline loop and records work locally.
