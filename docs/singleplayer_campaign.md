# Single-player campaign

## Goal

Make Super Gatorlator 64 a complete single-player game. Every required course, star, unlock, and ending must work with one local player and no network connection. Co-op is out of scope for this pass and can be added later.

## Core loop

1. Explore the Plaza of the Americas hub and find the next open campus building.
2. Enter a course and choose an act from the familiar SM64 act-select screen.
3. Complete a clear movement or exploration challenge and collect its star.
4. Return to the hub, see which doors opened, and pick the next challenge.
5. Collect enough stars to reach the Century Tower finale.

The moment-to-moment play stays focused on Mario movement: running, long jumps, wall kicks, swimming, shell surfing, and careful landings. Missions should introduce one memorable obstacle, teach it safely, then combine it with a harder route near the star.

## Campaign order

| Course | Unlock | Main solo acts | Course identity |
|---|---:|---|---|
| The Swamp / stadium | Start | Kickoff: Climb the Skybox; Stadium Stair Sprint; Tailgate Tokens | Big outdoor climbs, a friendly race, and stadium exploration |
| Reitz Union + Engineering | 2 stars | Rooftop of the Reitz; Meal Swipe Tokens; Remote Robotics Lab solo route | Lifts, courtyards, rooftops, and a compact platforming puzzle |
| Lake Alice | 5 stars | Boardwalk Welcome; Gator Hop; Bat Census solo route | Water, timed lily pads, and a dusk exploration challenge |
| Marston Science Library | 8 stars | Out-of-Order Elevator; Lost Textbooks; Study Room Booking solo route | Vertical indoor platforming, stealth, and a route-planning puzzle |
| Library West After Dark | 11 stars | All-Nighter; Coffee Run; Quiet Hours solo route | Nighttime climbing, a timed delivery, and hide-from-the-librarian play |
| Century Tower + Final Exam | 30 stars | Finals Week Ascent; The Final Exam | The campaign finale and graduation ending |

The existing ten solo missions remain the campaign backbone. Replace the five currently co-op-only acts with solo-designed missions for this pass:

- **Stadium Rhythm Challenge:** hit a ground-pound beat sequence across one connected set of pads.
- **Robotics Lab Trial:** steer a self-running crane through a platforming route using floor controls.
- **Bat Census at Dusk:** follow bat waves between three stations and record them before the timer ends.
- **Study Room Route:** activate kiosks across multiple floors in a timed route, with a short reset on mistakes.
- **Quiet Hours Patrol:** evade a predictable librarian route, collect three library cards, and reach the circulation desk.

## Star economy

The current door thresholds (2, 5, 8, and 11 stars) work once the five replacement solo acts are built. Make the full 30-star finale reachable without grinding:

- 15 course mission stars: three reliable, authored stars per campus course.
- 15 optional course stars: token hunts, races, 100-coin stars, and secret routes.
- Hub and tower challenge stars add replay goals and a buffer for players who skip difficult challenges.

The exact final count can stay at the existing 52-star target. Before tuning the finale gate, verify the number of stars that are actually collectible in the built levels, not just listed in the design. Every required door should be reachable through more than one path, and no single race should be mandatory.

## Difficulty and replay

- The first star in each course is a guided introduction with visible landmarks and a forgiving fall recovery.
- The second introduces a timing, hazard, or navigation skill.
- The third combines those skills and rewards exploration.
- Optional stars add tighter times, harder routes, red-coin searches, and 100-coin challenges.
- Personal bests and completion times are stored locally. A failed attempt never erases a collected star.

## Leaderboard loop

The leaderboard is an optional replay feature, not a campaign gate:

1. After a mission star is collected, show a results card with completion time, retries, and local personal best.
2. Save the result locally immediately, whether or not the player is signed in or online.
3. If the player opts in to account sync, submit the result to DeepSpace and show its current rank when available.
4. Put a **Record Board** in the Plaza hub. It shows the top times for each mission and the player's own best, with a filter for friends or global entries if those scopes are available.
5. Let the player replay any completed act directly from its course door to beat a personal best or leaderboard time.

Use separate categories for each mission so a short course is not compared against a long one. Keep the posted metric simple: fastest valid completion time, with retries as a tie-breaker. Store a run ID, mission ID, duration, retry count, and game version; don't upload email or other personal profile fields. Treat the board as casual unless the game adds server-side validation against cheated times. A leaderboard position never grants a required star or blocks an unlock.

## Ending

At 30 stars, the Century Tower opens for Finals Week Ascent. Reach the bell chamber, enter the exam arena, defeat the original campus-themed boss, collect the Grand Star, and return to the Plaza for a short graduation scene featuring the playable friends. The credits should acknowledge the team and OpenStreetMap contributors.

## DeepSpace and sign-in

DeepSpace supports optional account-linked records and a leaderboard for completed runs; it does not need multiplayer for that. The native game must save stars and personal bests locally first. A separate sync layer can upload opted-in results when available, while the game remains fully playable offline. Never gate stars, doors, or the ending on DeepSpace or OAuth sign-in.

Because this project is an sm64coopdx Lua mod, the Lua code should not be treated as a web or mobile SDK client. The game needs a native bridge or local helper to send results to DeepSpace. Auth0 sign-in should only be added after the game has a safe token handoff from that bridge; no client secret or long-lived bearer token belongs in the mod. OAuth is for optional identity and saved online records, not for starting a single-player session.

## Ship order

1. Verify the ten existing solo missions from a fresh save.
2. Replace the five co-op-only acts with solo-designed missions and test them.
3. Confirm the 11-star Library West gate and 30-star finale can be reached from a one-player save.
4. Add the finale and graduation sequence.
5. Add the local Record Board and personal-best results cards.
6. Add optional DeepSpace leaderboard sync after the local campaign loop is stable.
