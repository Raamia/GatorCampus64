# Single-player gameplay spec

**Status:** design proposal for review. This describes the intended complete game; it does not claim that every listed act is implemented. Co-op is out of scope for this pass.

## 1. Player promise

Play as a UF friend in a Super Mario 64 style campus adventure. Explore recognizable places, use the familiar movement kit to reach surprising routes, earn stars from short authored challenges, and climb Century Tower for the Final Exam. The whole campaign works offline with one player. An optional DeepSpace leaderboard adds asynchronous score chasing after the local game loop is fun; no account is needed to start or finish the game.

### Design rules

- **Movement is the toy:** running, triple jumps, wall kicks, backflips, swimming, shell surfing, and Wing Cap flight solve most problems.
- **Each course fits the accessible space:** only the Reitz Union and Marston Science Library have enterable interiors. The stadium, Lake Alice, Library West, and Century Tower are exterior-only stages; nearby buildings are scenery and traversal surfaces, never doors into interiors.
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

Start in the Plaza of the Americas, clear enough stars to open the next building, visit all five campus courses, climb Century Tower on the outside, then collect 30 stars to open Finals Week Ascent and The Final Exam. Players who want more can finish the 52-star set and improve course records.

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
3. **Engineering Crane Trial — solo minigame** — Play in the outdoor Engineering Plaza, with the nearby halls as scenery only. Three ground consoles select the crane's next fixed stop. Reach a console, choose a lit height, then ride the outdoor demo crane through hanging cable bundles and swinging sensor arms. The platform pauses at every landing so the player can dismount safely. The last stop reaches the star platform.
4. **Weil Wind Tunnel** — Use an outdoor wind-test rig beside Weil Hall; do not enter Weil. Ground-pound its floor switch to start the vertical fan. The fan stays active long enough for one complete climb if the player follows the wind stream and lands on maintenance ledges. A visible countdown warns before spin-down. The switch can be reactivated without restarting the act.
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

**Course identity:** an exterior night course around Library West. The building has no enterable floors; play takes place on its walks, gardens, facade ledges, roof edge, and nearby plaza.

1. **All-Nighter** — Climb the outside of Library West from the front walk to the roof edge using facade ledges, awnings, lamp posts, and a maintenance lift. Boos patrol the walkways and roof perimeter. Looking directly at a Boo makes it harmless; punching removes it briefly. Checkpoints at the courtyard and roof access prevent a long repeat after a fall.
2. **Coffee Run** — Pick up a coffee from an outdoor cart on the Plaza and carry it around Library West to a marked study table on the far terrace. Boos and narrow exterior routes force the player to choose between a short exposed path and a longer sheltered path. Target par: 60 seconds. If hit, the cup drops and can be picked up again; the clock keeps running.
3. **Quiet Hours Patrol — solo stealth** — Avoid an AI night librarian and collect three library cards from exterior notice boards, benches, and a book-return kiosk before reaching the outdoor drop slot. The librarian patrols the paths around the building and reacts to line of sight and loud landings. Trees, statues, and facade recesses break sight. If spotted, the player is escorted to the front walk; collected cards remain.
4. **The Ghost of Finals Past** — Clear small Boos from three outdoor landmarks, then bait Big Boo into turning around and ground-pound it three times on the roof terrace. A successful hit requires facing away from the player; the tell is a short spin and sound cue. Damage does not reset cleared landmarks.
5. **Lights Out** — The exterior path lights go dark, with a small local light around Mario. Find and activate three outdoor breaker boxes around the Library West walk and garden. Each breaker restores one section of path lighting and reveals the next route. A fall returns to the last lit checkpoint; completed breakers stay on.
6. **Re-shelve the Glowing Books** — Find eight glowing book props scattered around the exterior: entry steps, benches, garden edges, facade ledges, and roof access. Coins and window silhouettes hint at each area. Collect them in any order; the last appears beside the outdoor book-return slot.
7. **Team 100** — Collect 100 coins around the front walk, garden, exterior ledges, and roof perimeter. Boos remain hazards but move slower than in the timed Coffee Run. Path lights and window glow keep the route readable.

### Course 6 — Century Tower exterior

**Course identity:** an exterior-only ascent around the real 47.9 m tower. Do not add an enterable tower room or a larger interior. Build a safe platforming route from visible facade details, adjacent maintenance platforms, and the surrounding plaza.

1. **Up the Bell Tower** — Climb the outside of the tower using narrow ledges, poles, and temporary maintenance platforms. Safe terraces sit before every major jump. The goal is a marked summit platform; no door or interior room is entered.
2. **Carillon Concert — solo memory game** — Listen to and watch a short bell melody, then ground-pound exterior chime panels in the same order. Three rounds increase from four to six to eight notes. The panels are placed on adjacent terraces connected by safe jumps. A wrong panel repeats the current melody.
3. **Tower Ring Red Coins** — Collect eight red coins on facade ledges, maintenance platforms, and the plaza monuments below. The route alternates between high and low terraces; a coin trail marks a safe descent back toward the tower base.
4. **Race to the Top** — A solo time trial from the base to the summit platform. Follow six exterior checkpoints through the same route used by the climb act. Target par: 90 seconds. The run is scored only by the official clock, not by a network ghost.
5. **Stop the Clock** — Ground-pound an exterior maintenance switch to pause the moving lifts and rotating platforms for 12 seconds. Climb to the next terrace and hit a second switch to renew the window. The star appears on the upper platform after the final switch; the challenge is route planning under a timer.
6. **Ring the Outside Bells** — Take the Wing Cap from a base-level box and fly around the tower to hit four large exterior bells. Each bell makes a distinct sound and lights up. A cap refresh on a halfway terrace makes the route forgiving; missing a bell returns Mario to the launch platform.
7. **Team 100** — Collect 100 coins on the surrounding plaza, exterior platforms, and tower terraces. Coin trails signal safe timing windows without forcing a single path.

## 6. Hub and bonus activities

### Plaza of the Americas

The hub is a playable place, not a menu. It contains the course doors, visible exterior route up Century Tower, character pick, progress map, and the in-game Record Board. Add seven secret stars for optional movement challenges on plazas, paths, and building exteriors: rooftop routes, hidden coin rings, a fountain jump, and a short landmark circuit. No secret enters an interior other than Reitz or Marston. Each secret gets a clue on the campus map after the player has explored nearby.

### Smathers Stacks Slide

A short bonus course entered from Smathers Library. Slide through a winding stack-and-map-room route. Earn one star by finishing; earn a second by finishing under the target time. The second star is a replay reward, never required for the next door.

### Finals Week Ascent and The Final Exam

At 30 stars, a door at the Century Tower base opens to a night-time exterior ascent above the campus. Jump across oversized textbooks, avoid flying red pens and falling books, and reach a separate exam arena in the sky. The boss has three readable phases: dodge a moving desk, ground-pound exposed answer buttons, then return a flying blue book to the right shelf. A wrong shelf resets only that phase. Defeating the boss triggers the Grand Star and graduation ending. The approach's eight red coins award one optional star. The arena is a separate course space, not a tower or campus building interior.

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

## 9. SwampHacks track fit

SwampHacks XII's current Devpost page lists DeepSpace, Gemini API, Auth0, Vultr, Solana, Tiger Data, GoDaddy Registry, AI/ML, Entertainment & Creative Technology, UI/UX, Best First Timers, and other challenges. The strongest fit for this native solo game is the game itself plus **DeepSpace + Gemini**. Auth0 is a possible third track if the team can implement account linking cleanly. The event's DeepSpace rules require working functionality, a clear explanation of which features judges should inspect, and a live demo or testable build with safe access instructions. [SwampHacks XII challenge list and rules](https://swamphacks-xii.devpost.com/)

**Recommended targets:** Entertainment & Creative Technology, Best Use of DeepSpace, and Best Use of Gemini API. Add Best Use of Auth0 only if the native sign-in bridge works end to end. Best Use of AI/ML is an additional possibility if the Gemini guide is a central, demonstrated feature rather than a small bonus.

### Recommended: Entertainment & Creative Technology

The game itself is the entry: a real campus turned into an SM64-style platforming campaign, with original characters, exterior exploration, movement challenges, and a complete single-player ending. Show a working route through a course and one distinctive minigame. This track needs no extra service integration; it rewards a polished, enjoyable demo.

### Recommended: DeepSpace — score service and optional account sync

Use DeepSpace for a real **single-player records service**:

- Save one best-time record per player and act, with retry count and game version.
- Show the top times and the signed-in player's own position on the in-game Plaza Record Board.
- Sync personal bests between sessions; store pending local results while offline and submit them after reconnection.
- Demonstrate a result created by the game appearing in the board, and explain the collection, permissions, and query that power it.

This fits DeepSpace's collections/records model; real-time multiplayer is unnecessary. The sponsor challenge specifically says a logo or mention is insufficient and asks for working use, an explanation, and a testable demo. [DeepSpace challenge requirements](https://swamphacks-xii.devpost.com/), [DeepSpace data storage](https://docs.deep.space/guides/data-storage)

### Recommended: Gemini API — the Gator Guide NPC

Make Gemini the player's **context-aware campus guide**, not a generic chatbot. The player can ask for a hint from a guide NPC during an unranked exploration run. Give the guide only verified game facts: current course and act, remaining tokens, last checkpoint, and authored route landmarks. Gemini returns a short structured hint such as `hintText`, `landmarkId`, and `assisted`; the game validates the landmark against an allowlist before displaying it.

Use Gemini for one meaningful capability: select and phrase the best next hint from the real mission state. It should not invent map locations, change a mission, control physics, or decide whether a star is awarded. Keep authored hints as the offline fallback. Google's structured-output mode supports schema-constrained JSON, and function calling can let the model request an allowed game-state lookup. Validate all returned values. [Gemini structured outputs](https://ai.google.dev/gemini-api/docs/structured-output), [Gemini function calling](https://ai.google.dev/gemini-api/docs/tools)

For fair time comparisons, either disable Gator Guide use during a ranked run or mark it **assisted** and show assisted times in a separate board category. This makes the AI visible in the demo while preserving a meaningful fastest-time board.

### Optional: Auth0 — secure account linking

Auth0 fits the **optional online record account**: sign in once to attach a display name and sync personal bests. Do not make login necessary for play. Keep one identity source; DeepSpace's built-in auth and Auth0 can overlap, so don't ask players to create two accounts. If targeting the Auth0 prize, use Auth0 as the sign-in authority and have the service verify its access token before accepting a score.

Since the game is a desktop native app, use Authorization Code with PKCE through the operating system browser and a carefully handled redirect. The native game must not contain a client secret. Auth0 documents PKCE for public native clients; the sponsor page calls out social sign-in, MFA, and passwordless options. An Auth0 identity does not automatically become a DeepSpace user: a trusted service would need to verify the Auth0 token, map its subject to a game profile, and write/read that player's records. This custom mapping is extra integration work; if it is too much for the demo, use DeepSpace auth alone and skip the Auth0 track. [Auth0 native application security](https://auth0.com/docs/get-started/applications/confidential-and-public-applications), [Auth0 native redirect guidance](https://auth0.com/docs/secure/security-guidance/measures-against-application-impersonation), [Auth0 challenge](https://swamphacks-xii.devpost/)

### Integration constraint: the game needs a bridge

The game is an sm64coopdx Lua mod, not a React Native/Expo app. DeepSpace's documented native SDK targets Expo, so it cannot simply be imported into this game's Lua. Keep gameplay native by adding a small local bridge: the mod writes completed runs to its local ModFS outbox; the bridge handles account linking, sends scores to a DeepSpace Worker, and returns leaderboard rows or a short Gemini hint. The bridge and Worker must keep service credentials off the mod and off the client. Until that bridge exists, the current browser dashboard prototype is not an in-game DeepSpace integration. [DeepSpace mobile client docs](https://docs.deep.space/guides/mobile-apps)

### Lower priority or poor fit

- **Best Use of AI/ML:** possible only if the Gator Guide is a central, technically demonstrated AI feature. Treat Gemini as the specific API entry; don't add an unrelated model pipeline just to claim this broader track. The current challenge asks for technical depth and AI/ML to be central. [AI/ML challenge requirements](https://swamphacks-xii.devpost.com/)
- **Easy on the Eyes / UI/UX:** good secondary fit if the hub map, pause/HUD, hints, and results board are polished and accessible. It does not require another backend.
- **Best First Timers:** applies only if at least half the team members meet the event's first-hackathon eligibility rule.
- **DEV Writing Challenge:** a low-cost post-event add-on: publish a substantive build story about the campus world, solo mission design, native bridge, or grounded AI guide. It is separate from the playable game's feature set.
- **Vultr:** skip for now. DeepSpace already supplies the backend this game needs; adding a second cloud host only makes sense if a concrete workload outgrows it.
- **Tiger Data:** skip unless the project genuinely needs time-series analytics across a much larger set of play sessions. A leaderboard is a small records table, which DeepSpace already covers.
- **Solana, GoDaddy Registry, Nessie, Roblox Studio, and hardware:** poor fit for this offline-first campus platformer. Blockchain scores, a finance API, another game engine, or physical hardware would add work without improving this game.

### Demo path for judges

1. Launch the native game without an account and complete a short mission.
2. Show the local result card and local personal best.
3. Ask the Gator Guide for a hint in a separate unranked attempt; show that its answer uses current mission state and a verified landmark.
4. Opt into account linking, submit a score, and open the in-game Record Board to see it.
5. Turn off the network or sign out and show that the campaign and locally saved progress still work.

The judge instructions should say exactly which mission, NPC, sign-in action, and Record Board to inspect, and must not contain secrets.

## 10. Suggested build order

1. Lock the solo mission rules, official timer behavior, and result-card fields.
2. Replace the five co-op-only acts with the solo mechanics above and playtest acts 1–3.
3. Add remaining acts in course order so vanilla act-select progression never hits a missing earlier star.
4. Add Team 100 stars, hub secrets, and the Smathers slide; verify the star budget from a fresh save.
5. Build the exterior Century Tower course and test the 14-star gate.
6. Build the 30-star finale and graduation sequence.
7. Add the local Record Board and personal-best display.
8. Add a native bridge, then connect optional DeepSpace records and Gemini hints.
9. Add Auth0 only if the team is deliberately entering that challenge and has time to test native PKCE.
