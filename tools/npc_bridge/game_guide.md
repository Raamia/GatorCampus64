# Super Gatorlator 64: the NPC game guide

Albert and Alberta, the roaming mascot NPCs, answer game questions straight from this file: no AI call, instant, always right.
Anything this file can't answer (general knowledge, small talk) goes to Gemini instead.
tools/npc_bridge/guide.py reads it; tools/npc_bridge/test_guide.py and tools/luatest/check_game_guide.py check it.

## How to add or change an entry

Every entry is a `###` heading (a sample question) followed by these lines:

- `id:` a short unique name (letters, digits, dashes). Tests refer to it, so keep it once it exists.
- `npc:` (optional) only this NPC answers with the entry, e.g. `npc: albert` for "Who are you?".
- `ask:` comma-separated ways a player might ask, and keywords. More phrasings = better matching.
  The heading counts as one more phrasing.
- `answer:` what the NPC says, on one line. The first sentence or two (about 200 characters) go in the
  speech bubble; the whole answer goes to chat, so details can follow.

Live values, filled in from the game when the player asks:
`{player}` name, `{stars}` team stars, `{lives}`, `{coins}` (this visit), `{here}` where they are,
`{character}` their friend character, `{players}` players online, `{next_hint}` which door opens next and how
many more stars it needs, `{stage_stars}` stars per stage, `{stage_stars:KEY}` one stage
(KEY = swamp, reitz, alice, marston, libwest), `{albert_at}` / `{alberta_at}` where each mascot is right now.

Questions nobody could answer well land in tools/npc_bridge/unanswered.log: turn them into new entries here.

## Getting started

### What is Super Gatorlator 64?
id: about
ask: what is this game, what is super gatorlator, tell me about the game, what game is this, about this game, what is this, explain the game, whats the point of the game
answer: Super Gatorlator 64 is the real University of Florida campus, at true scale, inside Super Mario 64, with online co-op and your friends as playable characters. Explore campus, walk into building doors to enter stages, and collect stars to open more of them. Go Gators!

### What does the game have to offer?
id: offer
ask: what can i do, what is there to do, what does the game have, what features, what content, things to do, what does it offer, how much stuff is there, what modes
answer: Five stages behind real campus doors (The Swamp, Reitz Union & Engineering, Lake Alice, Marston Science Library and Library West After Dark), each with 3 missions plus a 100-coin star, so 20 stars so far. There are climbs, races, token hunts, stealth, co-op puzzles and hide and seek. You can also play as 10 of our friends and play online with your friends.

### Which stages are there?
id: stages
ask: list the stages, what stages are there, how many levels, which levels, what courses, all the stages, levels list, worlds in the game
answer: Five stages so far: 1 THE SWAMP (University Auditorium door, open from the start), 2 REITZ & ENGINEERING (The Hub, 2 stars), 3 LAKE ALICE (Newell Hall, 5 stars), 4 MARSTON LIBRARY (Marston Science Library, 8 stars) and 5 LIBRARY WEST AFTER DARK (Library West, 11 stars). CENTURY TOWER (14 stars) is coming soon.

### Where should I go next?
id: next
ask: where do i go, what do i do now, what next, where should i go, what should i do first, how do i start, im lost, help me, where to go next, next stage, what now, i dont know what to do
answer: {next_hint} Your stars: {stars}. In the hub, a NEXT panel and a gold marker point at the door you should try.

### What are stars and how do I get them?
id: stars-what
ask: what are stars, how do i get stars, how to earn stars, collect stars, what do stars do, why stars, star count
answer: Stars open the stage doors around campus. You earn one by finishing a mission (each stage has acts 1 to 3) or by collecting 100 coins in one visit to a stage. After the star dance you land back outside that stage's door with the star counted for everyone.

## Your stats

### How many stars do I have?
id: my-stars
ask: how many stars do i have, my stars, my star count, how many stars, how many stars do we have, total stars, how many stars have i got
answer: You have {stars} stars, {player}! {next_hint}

### How many stars do I have in each stage?
id: stage-stars
ask: stars per stage, stars in each stage, stars per level, which stars am i missing, stage progress, my progress, how far along am i, completion, what have i finished
answer: Stars per stage: {stage_stars}. Each stage has 3 mission stars and a 100-coin star.

### How many lives do I have?
id: lives
ask: how many lives, my lives, lives left, extra lives, 1ups, game over, how do i get more lives
answer: You have {lives} lives, {player}. The hub refills you to 4 lives every time you're back on campus, and 1-ups hide all over the stages.

### How many coins do I have?
id: coins
ask: how many coins, my coins, coin count, coins do i have
answer: You have {coins} coins right now. Collect 100 coins in a single visit to a stage and its 100-coin star comes out.

### Where am I?
id: where
ask: where am i, what level am i in, what stage is this, my location, where are we, what place is this
answer: You're in {here}. Type /campus where for the exact level, area and act, and /campus hub to warp back to the Plaza.

### Which character am I playing?
id: my-character
ask: my character, which character am i, what character am i playing, which friend am i, who am i
answer: You're playing as {character}. Press L + START (Left Shift + Space on a keyboard) or type /char to pick someone else.

### Who is online?
id: players
ask: how many players, who is online, players online, how many people, is anyone else playing, my friends online
answer: There are {players} players online. Friends can join through Join on the main menu, and D-pad Up or /join takes you to their act.

### What are my stats?
id: my-stats
ask: my stats, show my stats, status, how am i doing, my status, player stats, give me my stats, stats
answer: {player}: {stars} stars, {lives} lives, {coins} coins, playing as {character}, now in {here}. Stars per stage: {stage_stars}. {next_hint}

## The hub (central campus)

### What is the hub?
id: hub
ask: what is the hub, central campus, the campus, plaza of the americas, where do i spawn, spawn, castle, starting area, home base
answer: The hub is UF's central campus, built from real map data at full size. You spawn on the Plaza of the Americas facing south toward the University Auditorium. Every stage is behind a real building door, and signposts by each door say how many stars it needs.

### Where are the stage doors?
id: doors
ask: where are the doors, door locations, which doors, how do i enter a stage, how to get into a level, building doors, entrances, find the doors
answer: University Auditorium (THE SWAMP, about 80 m south of the spawn, open from the start); The Hub's south entrance (REITZ & ENGINEERING, about 325 m south-west, 2 stars); Newell Hall's east entry (LAKE ALICE, about 225 m west-south-west, 5 stars); Marston's north wing door (MARSTON, about 230 m south-south-west, 8 stars); Library West's revolving door (about 115 m north, 11 stars).

### Why is this door locked?
id: locked-door
ask: door is locked, locked door, why cant i go in, cant enter, door wont open, red flames, see through star, it says locked, how to unlock a door, unlock
answer: A locked door shows a see-through star, red flames and "LOCKED - N stars". Walk in and it buzzes and says how many it needs. Collect more stars and it opens with a gold star and "Walk in!". {next_hint}

### What is Century Tower?
id: century-tower
ask: century tower, the tower, bell tower, tower door, 14 stars, carillon
answer: Century Tower is campus's famous bell tower, about 145 m south-south-west of the spawn, behind the Auditorium. Its stage is coming soon (it opens at 14 stars). For now its door shows "CENTURY TOWER / Coming soon" and buzzes.

### What are the Smathers and Final Exam doors?
id: future-doors
ask: smathers library, smathers stacks slide, final exam door, finals week ascent, 30 stars, secret door, other doors, bonus
answer: Two more signposts tease future content: the SMATHERS STACKS SLIDE at Smathers Library (3 stars) and the FINALS WEEK ASCENT behind the Final Exam Door (30 stars). Both are coming soon.

### What happens when I die?
id: death
ask: what happens when i die, i died, dying, lose a life, drown, fell, how do i not die, health
answer: Losing all your health (or drowning) throws you out of that stage's door with one life fewer. Back on campus the hub refills your lives to 4.

### What is a 100-coin star?
id: hundred-coins
ask: 100 coins, 100 coin star, hundred coins, coin star, collect 100 coins, red coins
answer: Every stage has a 100-coin star: collect 100 coins in one visit and it appears. There are plenty to find: about 142 in The Swamp, about 250 outside in Reitz & Engineering plus more inside the Reitz Union, about 176 at Lake Alice, about 190 in Marston and about 206 in Library West. Goombas drop a coin each too.

### What are the coming soon acts?
id: coming-soon
ask: coming soon, act 4, act 5, act 6, coming soon acts, free roam, explore mode, empty act, no mission
answer: Acts 4 to 6 of each stage are COMING SOON. You can enter them to explore freely (no mission, no star), which is great for sightseeing, coins and secrets. Pause and EXIT COURSE takes you back.

## The Swamp (course 1, University Auditorium door, open from the start)

### How do I get into The Swamp?
id: swamp-door
ask: get into the swamp, swamp door, where is the swamp, university auditorium, auditorium door, course 1, stadium, ben hill griffin, first stage, first level
answer: Walk about 80 m south of the spawn to the University Auditorium's centre porch door (gold star, "THE SWAMP / Walk in!"). It's open from the start. Inside is Ben Hill Griffin Stadium.

### How do I do Kickoff - Climb the Skybox?
id: swamp-act1
ask: kickoff, climb the skybox, swamp act 1, skybox, climb the stadium, stadium roof, first star, swamp first mission
answer: Climb the stadium to its roof (66 m): through the north gate, west along the concourse, up the west stands to the rim (20 m), then the 11 orange ledges to the Bull Gator Deck (44 m), then the 10 orange camera decks or the tall pole onto the roof. The star waits on the roof; the orange marker shows the way.

### How do I do the Stadium Stair Sprint?
id: swamp-act2
ask: stadium stair sprint, stair sprint, swamp act 2, swamp race, race in the swamp, sprint
answer: It's a race. Press D-pad Down (End on a keyboard, or type /mission start) to warp to the start box, wait for 3-2-1-GO, then follow the blue CP markers to the South Ramp terrace. Finish under 1'10 for the star; under 0'45 is a GOLD TIME.

### How do I do Gator Chomp Chorus?
id: swamp-act3
ask: gator chomp chorus, chomp chorus, swamp act 3, swamp co op, chomp, buttons in the end zone, ground pound buttons
answer: It needs 2 to 4 players. Stand on the lit end-zone corner buttons (one each, the flames turn blue), wait for the HUD to count GA... TOR... CHOMP!, then all jump and ground-pound (Z) together within about 1.3 s. Do 3 phrases and the star flies to midfield. Pounding late means "Off the beat!" and a retry.

### Where can I drown in The Swamp?
id: swamp-pool
ask: florida pool, swimming pool, drown in the swamp, water in the swamp, pool
answer: The Florida Pool is east of the stadium. Drowning there throws you out of the Auditorium door with one life fewer.

## Reitz Union & Engineering (course 2, The Hub door, 2 stars)

### How do I get into Reitz & Engineering?
id: reitz-door
ask: reitz door, get into reitz, the hub door, reitz union, engineering, course 2, second stage, where is reitz, how to unlock reitz, 2 stars
answer: Walk about 325 m south-west of the Plaza to The Hub's south entrance. It opens at 2 stars (finish The Swamp's acts 1 and 2). You arrive on the Reitz Union's North Lawn.

### How do I do Rooftop of the Reitz?
id: reitz-act1
ask: rooftop of the reitz, reitz act 1, reitz roof, window washer lift, climb the reitz, penthouse
answer: Climb the Reitz Union from its south-west (ravine) corner: brick terraces, three copper awnings, the ballroom roof (13 m), the podium roof (17.6 m), then ride the checkered window-washer lift up the tower to the parapet (27 m). Drop onto the tower roof and land on top of the elevator penthouse (28.8 m) for the star.

### How do I do Meal Swipe Tokens?
id: reitz-act2
ask: meal swipe tokens, tokens, reitz act 2, red tokens, 8 tokens, find the tokens, where are the tokens, token hunt
answer: Find 8 big red tokens; the panel names the nearest. They're on the Gator Corner patio table, the steel sculpture on the Engineering Plaza, the Liberty Pond fountain float, the Bookstore's east awning, the ravine boardwalk, Weil Hall's 24 m roof ridge, Malachowsky's glass stair and the Weil Cooling Towers' roof. The star appears where you grab the 8th.

### How do I do the Remote Robotics Lab?
id: reitz-act3
ask: remote robotics lab, robotics, reitz act 3, crane, cranes, robotics lab, console
answer: It needs 2 to 4 players. Press D-pad Down to enter the Robotics Lab. One player drives the crane from the purple console, the other rides it. At each locked gate the rider jumps into the yellow "!" box, then the driver lines the crane up under the narrow gap. Five gates, then step onto the star ledge.

### Can I go inside the Reitz Union?
id: reitz-interior
ask: inside the reitz union, reitz interior, reitz union inside, elevators in the reitz, game room, bowling, food court, ballroom
answer: Yes! Four real doors lead inside: the North Entrance, the South Terrace doors, the old FOOD COURT door and the Ground north door. Inside are eight real floors: the atrium with its giant UF letters, the Game Room with bowling and billiards, the Esports Center, the food court, ballrooms and hotel floors. In the Blue elevators, stand in the north-west car to go up and the north-east car to go down.

### Where are the secrets in Reitz & Engineering?
id: reitz-secrets
ask: reitz secrets, reitz 1up, 1 up in reitz, malachowsky, weil hall, secrets in reitz
answer: Climb Malachowsky Hall's glass stair to its penthouse (a 1-up), run Weil Hall's roof to the tower deck (another 1-up), and inside the Reitz Union check the top of the UF letters, the Swamp Boss gator head under the stair, the pool tables and the arcade cabinets.

## Lake Alice (course 3, Newell Hall door, 5 stars)

### How do I get into Lake Alice?
id: alice-door
ask: lake alice door, get into lake alice, newell hall, course 3, third stage, where is lake alice, how to unlock lake alice, 5 stars
answer: Walk about 225 m west-south-west of the Plaza to Newell Hall's east entry, at the top of a short stoop. It opens at 5 stars. You arrive on the bat-house field above the lake.

### How do I do Boardwalk Welcome?
id: alice-act1
ask: boardwalk welcome, lake alice act 1, lily pads, lily pad route, lake act 1, pavilion, deck
answer: Cross Museum Road onto the north boardwalk, wade onto the west bog, then hop the 15 lily pads (the gaps get wider). From the last big pad jump onto the deck in the middle of the lake for the star. Fall in near pads 3-6 or 9-13 and a gator comes for you: swim to a pad and press A at the surface to climb back on.

### How do I do Gator Hop?
id: alice-act2
ask: gator hop, lake alice act 2, sinking gators, hop the gators, gator backs, nest
answer: Press D-pad Down to start on the deck, hop onto the big pad, then along 17 basking gators heading north. Each one sinks for about a second in a wave, so time your hops. After the last gator, step onto the small bog with the nest and the star drops in. Swimming straight there doesn't count.

### How do I do the Bat Census?
id: alice-act3
ask: bat census, bat census at dusk, lake alice act 3, bats, census posts, swooper
answer: It needs 2 to 4 players. Staff at least two of the three census posts (press D-pad Down to warp to a free one). Bats stream out of the barns at dusk and each post counts its share; Swoopers dive at you, so stay on your post. Count about 900 bats (1200 with 3 players, 1500 with 4) in about 70 s and the star flies out of the white barn.

### What else is at Lake Alice?
id: alice-secrets
ask: lake alice secrets, basking alligators, alligator statues, bat barn, 1 up at lake alice, deep hole, baughman center, footbridge
answer: Spot the six basking alligator statues (you can stand on their backs), dive into the deep holes (coin rings, and a 1-up at the bottom of the deepest, south of the small bog), climb a bat-cam pole onto a barn roof (a 1-up in the brown barn's side box) and walk the Baughman Center's footbridge.

## Marston Science Library (course 4, Marston door, 8 stars)

### How do I get into Marston?
id: marston-door
ask: marston door, get into marston, marston science library, course 4, fourth stage, where is marston, how to unlock marston, 8 stars, library
answer: Walk about 230 m south-south-west of the Plaza to Marston's north wing door. It opens at 8 stars. Inside is the real five-floor library; you start in the lobby by the HELP DESK.

### How do I do Out-of-Order Elevator?
id: marston-act1
ask: out of order elevator, marston act 1, book cart lift, atrium climb, flying books, reading room, marston first
answer: The stairs are closed for renovation, so climb the grand stair to the 3rd-floor balcony, ride the checkered book-cart lift on the atrium's east side up to the 4th, hop onto the book cart that carries you across the atrium, and ride the west lift to the 5th floor. Walk into the north reading room for the star. Crouch (Z) or punch to deal with flying books.

### How do I do Shhh! Lost Textbooks?
id: marston-act2
ask: shhh lost textbooks, lost textbooks, marston act 2, textbooks, librarians, sneak, quiet floor, shushers, stealth
answer: Press D-pad Down to start at the 5th-floor stairwell. Find 8 flat brown textbooks without being heard: tiptoe (tilt the stick a little, or hold Left Shift on a keyboard) or crawl (Z). Each librarian's marker says how loud you may be: green RUN, white WALK, red TIPTOE. Get caught and it's back to the stairwell. The star rises at the west window desk.

### How do I do Study Room Booking?
id: marston-act3
ask: study room booking, marston act 3, kiosks, booking code, study room, l129, punch the kiosk
answer: It needs 2 to 4 players. Each of you goes to a lit booking kiosk; your kiosk shows your friend's code, never your own, so tell each other ("yours is 2!"). When you're all at a kiosk the HUD counts 3-2-1-PUNCH: punch your kiosk your code's number of times, all within 4 s, and room L129 unlocks with the star inside.

### What else is in Marston?
id: marston-secrets
ask: marston secrets, book chute, chandelier, marston roof, 1 up in marston, basement, fish tank
answer: Ride the book chute down to the basement and jump into the vent duct (a 1-up), climb the north-east stair hall to the roof and the tower top (a 1-up), drop from the 5th floor onto the atrium chandelier ring (another 1-up), and climb the bookshelf ranges across the book-cart bridges.

## Library West After Dark (course 5, Library West door, 11 stars)

### How do I get into Library West?
id: libwest-door
ask: library west door, get into library west, library west after dark, course 5, fifth stage, where is library west, how to unlock library west, 11 stars, revolving door
answer: Walk about 115 m north of the Plaza to Library West's revolving door. It opens at 11 stars. Inside it's night: six floors of stacks, desk lamps and sleepy Boos.

### How do I do the All-Nighter?
id: libwest-act1
ask: all nighter, all-nighter, library west act 1, big window, ladders, boos, rolling ladders
answer: Ride the escalator to the 2nd floor, climb the rolling library ladders onto the north stacks, take a north stair tower up to its roof door, cross the roof terrace, go in through the 4th floor's north door and up a stair hall to the 6th floor's big window for the star. Face a Boo to freeze it; touching one costs a wedge.

### How do I do the Coffee Run?
id: libwest-act2
ask: coffee run, library west act 2, coffee, race in library west, get coffee, coffee counter
answer: It's a race. Press D-pad Down to go to your 6th-floor desk, then after 3-2-1-GO run down to the 2nd floor, down the escalator to the coffee counter (a green cup appears over your head), and back up to your desk. Under 1'00 earns the star; under 0'45 is a GOLD TIME. Shortcut: hop the 2nd-floor balcony rail into the lobby (no damage).

### How do I do Quiet Hours Hide & Seek?
id: libwest-act3
ask: quiet hours hide and seek, hide and seek, library west act 3, night librarian, hide, seek, lantern
answer: It needs 2 or more players. One player is the night librarian and counts down while everyone else hides in the stacks. Then the librarian hunts for 120 s with a lantern beam; touch a hider or keep them in the beam to find them, and found hiders become librarians. The results board names the winner and the star lands on the circulation desk.

### What else is in Library West?
id: libwest-secrets
ask: library west secrets, roof terrace, 1 up in library west, elevator shaft, sleeping students, electrical room
answer: Check the roof terraces at 18 m (a 1-up on the north-east stair tower's roof), the 5th floor's staff corridor (a 1-up in the electrical room), the 6th floor's big window with Century Tower and the moon, and the open elevator shaft. It's finals week, so look for the students asleep on their desks.

## Controls

### What are the controls?
id: controls
ask: controls, keyboard controls, what are the keys, how do i play, buttons, key bindings, which keys, keyboard
answer: Default keyboard: WASD moves, L jumps (A), comma punches (B), K crouches or ground-pounds (Z), Space is START (pause), Left Shift is L, Right Shift is R, the arrow keys turn the camera and Enter opens chat. The D-pad is Home (up), End (down), Delete (left) and Page Down (right). A controller works too.

### How do I jump?
id: jump
ask: how do i jump, jump button, jump key, double jump, triple jump, long jump, wall kick
answer: Jump is A, which is the L key on a keyboard. Jump again as you land for a double and then a triple jump; crouch (K) while running and jump for a long jump; jump into a wall and jump again to wall-kick.

### How do I punch or ground-pound?
id: punch
ask: how do i punch, attack, punch button, kick, ground pound, how to ground pound, crouch, crawl, dive
answer: Punch is B (the comma key). Z (the K key) crouches; press it in the air to ground-pound, and hold it while moving to crawl. Ground-pounds matter in Gator Chomp Chorus.

### What does L + START do?
id: l-start
ask: l + start, l and start, l plus start, press l + start, how to press l + start, left shift space, character menu, open the menu, choose your gator
answer: L + START opens the "CHOOSE YOUR GATOR!" character menu. On a keyboard that's Left Shift + Space. Move with the arrow keys or stick, pick with A (the L key), and close with B or START. Typing /char does the same.

### How do I use the D-pad on a keyboard?
id: dpad
ask: d pad, dpad, d-pad up, d-pad down, home key, end key, d pad on keyboard
answer: On a keyboard the D-pad is Home (up), End (down), Delete (left) and Page Down (right). D-pad Up joins your friends' act, and D-pad Down warps you to a mission's start in races and many co-op acts.

### How do I move the camera?
id: camera
ask: camera, move the camera, rotate camera, camera controls, c buttons, look around
answer: The arrow keys are the C buttons: left and right turn the camera, and up and down zoom it. Indoors the camera sits closer and lower automatically.

### How do I chat?
id: chat
ask: how do i chat, open chat, type a message, talk to people, chat key, send a message
answer: Press Enter, type, and press Enter again. Near an NPC, whatever you type goes to them too. Lines starting with / are commands.

### Can I change the controls?
id: rebind
ask: change controls, rebind keys, remap, change keys, use a controller, gamepad, controller support
answer: Yes: on the main menu go to Options, then Controls, to rebind any key. Controllers work out of the box.

## Commands

### What chat commands are there?
id: commands
ask: commands, chat commands, slash commands, what commands, list of commands, help commands, cheats
answer: /albert and /alberta (ask the mascots anything, from anywhere), /leaderboard (the campus leaderboards), /char (pick your friend), /join (go to your friends' act), /mission (mission status; /mission start and /mission reset), /campus (where, list, hub, or warp to a stage act) and /school (check the mod is running).

### How do I warp to a stage?
id: warp
ask: warp, teleport, campus command, go to a stage, shortcut, skip, campus hub, go back to the plaza, return to spawn, get to the plaza
answer: Type /campus followed by a stage and act, like /campus marston 1, or /campus hub to go back to the Plaza. Stages: swamp, reitz, alice, marston, libwest. The host's /campus moves everyone; add "me" (like /campus swamp 2 me) to move only yourself. Pause and Exit to Castle also returns you to the Plaza.

### What does /mission do?
id: mission-cmd
ask: mission command, /mission, mission start, mission reset, mission status, restart mission, retry
answer: /mission shows the current mission's state, round, players and leader. /mission start does what D-pad Down does (warp to the start), and /mission reset starts a fresh round.

## Characters

### Who can I play as?
id: characters
ask: characters, who can i play as, playable characters, friends, change character, switch character, pick a character, skins, models, 10 friends
answer: You can play as 10 of our friends: Daniel, Corina, Raami, Anh, Josh, Donald, Jaime, Alfred, Vignesh and Cher. Press L + START (Left Shift + Space) or type /char to open the menu, or /char <name> to pick directly. Your pick is remembered next time, and everyone sees you as your friend.

## Playing with friends

### How do I play with friends?
id: multiplayer
ask: play with friends, multiplayer, co op, coop, online, invite friends, host, join a game, how do friends join, play together
answer: One player chooses Host (with Super Gatorlator 64 enabled under Mods) and the others choose Join and connect to them. Explore campus together; stars count for everyone.

### How do I join my friends' mission?
id: join-act
ask: join my friends, study group, follow my friend, join their act, d pad up, /join, go to my friend, invite
answer: When a friend starts an act you get a popup: press D-pad Up (Home on a keyboard) or type /join to land in the same act. Late? /join <their name> works too. Pause, Mods, "Join my study group" does the same.

### Which missions need 2 players?
id: two-player
ask: 2 player missions, needs 2 players, co op missions, act 3, two players, multiplayer missions, i cant do act 3, only one player, need a friend
answer: Every stage's act 3 needs 2 to 4 players: Gator Chomp Chorus (Swamp), Remote Robotics Lab (Reitz), Bat Census at Dusk (Lake Alice), Study Room Booking (Marston) and Quiet Hours Hide & Seek (Library West). Alone, the act tells you it needs 2 players and you can exit with no life lost.

### Do stars count for everyone?
id: shared-stars
ask: shared stars, do stars count for everyone, who gets the star, friend got the star, star collected by, leave together
answer: Yes, stars count for the whole team. When a friend grabs the star you see "Star collected by <name>" and can press D-pad Up to head back to campus together with no life lost.

## Times and records

### Is there a leaderboard?
id: leaderboard
ask: leaderboard, leaderboards, high scores, rankings, best times, records, who is the best, scoreboard, top players, campus leaderboards, boards
answer: Yes! Open the CAMPUS LEADERBOARDS with R + START (Right Shift + Space on a keyboard), the on-screen BOARDS button, or /leaderboard. There are boards for the Reitz rooftop, the Marston climb, the Stadium Stair Sprint and the Skybox Climb. Races also show a results board with everyone's times, and the game saves your personal best.

### What are the race par and gold times?
id: race-times
ask: par time, gold time, race times, how fast, race par, time to beat, personal best, pb
answer: Stadium Stair Sprint (Swamp act 2): par 1'10, gold 0'45. Coffee Run (Library West act 2): par 1'00, gold 0'45. Beat par for the star; gold is for bragging rights. Your personal best is saved.

## The mascots (Albert and Alberta)

### Who are you?
id: who-albert
npc: albert
ask: who are you, who is albert, are you a gator, mascot, albert the alligator, whats your name, your name, introduce yourself
answer: I'm Albert the Alligator, UF's official mascot and one of your two hosts, with Alberta! We roam campus and the stages to help you out. Ask me anything about the game. CHOMP CHOMP!

### Who are you, Alberta?
id: who-alberta
npc: alberta
ask: who are you, who is alberta, are you a gator, mascot, alberta the alligator, whats your name, your name, introduce yourself
answer: I'm Alberta the Alligator, UF's official mascot alongside Albert and one of your two hosts! I roam the libraries, Lake Alice and the Plaza to help you out. Ask me anything about the game. Go Gators!

### Who can I talk to?
id: npcs
ask: other npcs, who else can i talk to, npcs, characters to talk to, who are the mascots, mascots, albert and alberta, who is alberta, who is albert, guides, helpers
answer: Albert and Alberta, UF's two alligator mascots, are your guides. One of them is always on the Plaza by the spawn, and the other visits a stage, popping up near where you arrive. They move every few minutes, with a puff of smoke. Walk up to one and type, or ask from anywhere with /albert or /alberta.

### Where is Albert?
id: where-albert
ask: where is albert, wheres albert, find albert, albert location, where did albert go, where can i find albert
answer: Albert is {albert_at} right now. He moves every few minutes, but you can always ask him from anywhere with /albert followed by your question.

### Where is Alberta?
id: where-alberta
ask: where is alberta, wheres alberta, find alberta, alberta location, where did alberta go, where can i find alberta
answer: Alberta is {alberta_at} right now. She moves every few minutes, but you can always ask her from anywhere with /alberta followed by your question.

### Where are you, Albert?
id: where-am-i-albert
npc: albert
ask: where are you, where are you now, where are you right now, where will you be, where do you go
answer: Right now I'm {albert_at}! I hop around campus every few minutes. When I'm away, Alberta is on the Plaza, and you can ask me from anywhere with /albert.

### Where are you, Alberta?
id: where-am-i-alberta
npc: alberta
ask: where are you, where are you now, where are you right now, where will you be, where do you go
answer: Right now I'm {alberta_at}! I move around every few minutes. When I'm away, Albert is on the Plaza, and you can ask me from anywhere with /alberta.

### How do I talk to Albert or Alberta?
id: talk-npc
ask: how do i talk to you, talk to npc, how to talk, talk prompt, speak to albert, speak to alberta, ask a question, ask from anywhere
answer: Walk up until "TALK TO ..." shows at the bottom of the screen, press Enter, type your question and press Enter. The answer appears in a speech bubble and in chat for everyone. From anywhere else, type /albert or /alberta followed by your question.

## About the campus

### Is this the real UF campus?
id: real-campus
ask: is this real, real campus, real buildings, true scale, openstreetmap, map data, how big is the campus, is campus accurate
answer: Yes! The campus is built from OpenStreetMap data at true 1:1 scale, so every building is real and full size. The interiors (Reitz Union, Marston, Library West) follow the real floor plans.

### Who made this game?
id: credits
ask: who made this, who made the game, developers, credits, who built this, creators
answer: Super Gatorlator 64 is a fan project by a group of UF friends, built as mods for sm64coopdx (the co-op Super Mario 64 PC port). The playable characters are the friends who made it. Map data (c) OpenStreetMap contributors.
