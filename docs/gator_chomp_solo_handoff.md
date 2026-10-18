# Handoff: solo Gator Chomp Chorus demo

> **Status:** this is the original brief for the solo Gator Chomp Chorus. It has since been built: see `mods/sgl64/swamp_chomp.lua` and `docs/gator_chomp_chorus.md`.

## Goal

Build one polished, self-contained single-player mini-game that works well in a demo. A player should understand it quickly, play through a complete challenge, and see a satisfying result. The feature does not need a full campaign, leaderboard, online service, or long-term progression to be demo-ready.

## The game in one sentence

At The Swamp stadium, watch a short rhythm pattern on glowing pads, then run to the matching pads and ground-pound on the beat to perform the Gator Chomp.

## Where it happens

Use **The Swamp stadium field**, at the existing end-zone button setup used by Swamp Act 3. The existing coordinates are in `SWAMP_POINTS` in `mods/sgl64/swamp_missions.lua`; the current four buttons are at the field’s far corners. Those corners are too far apart for a quick solo rhythm sequence, so make a compact four-pad arrangement in **one end zone** for this mini-game. Put the player’s start spot and the scoreboard-facing camera nearby. Keep the rest of the stadium visible as the backdrop.

Choose the exact pad positions against the built collision. Leave enough room around each pad for Mario to land and move between them without colliding with scenery. If the multiplayer act must remain available, retain its existing four-corner layout and give the solo variant its own compact pad positions.

## Player flow

1. **Start:** Place Mario beside the pads. Show one instruction: “Watch the pads. Repeat the beat: move, jump, and ground-pound.” Include the game’s actual keyboard/controller binding in the prompt.
2. **Practice:** Light one pad and play its sound. Let the player try one forgiving input. Give immediate “NICE!” feedback; a miss explains the ground-pound input and lets the player retry.
3. **Main phrase:** Show and play a pattern. The player repeats it. Each note is one pad plus a beat; accept a ground-pound on the selected pad within a forgiving timing window.
4. **Build mastery:** Add notes or vary the pattern across additional rounds. Keep the same visual grammar so the challenge grows without introducing unclear rules. Tune the number and length of rounds for the best game feel; there is no target run duration.
5. **Payoff:** The scoreboard flashes the result, the crowd reacts, and Mario or a nearby mascot performs a Gator Chomp. Show a simple grade and “Play again” prompt. The demo should show a complete, satisfying mini-game loop.

A player who misses should recover quickly without restarting the entire act. Do not truncate a phrase or skip the result just to meet a runtime target.

## Core rules

- The game is single-player and starts without waiting for another player.
- The player watches each phrase before repeating it. Pad color, a distinct sound, and a beat pulse all identify the next note.
- During playback, inputs do not count. During the response, the active phrase and current beat are easy to see.
- To score a note, Mario must be on or above its pad and land a ground-pound inside the timing window. Reuse the existing `ACT_GROUND_POUND` / `ACT_GROUND_POUND_LAND` detection where practical.
- A wrong pad or early/late pound gives immediate feedback and retries the current phrase. It does not remove a life, health, star, or previously completed phrase.
- Award a clear result: for example, **GATOR GREAT** for completing the challenge, with a score or small grade based on accuracy. Do not make perfection necessary to finish.
- Keep the challenge local and deterministic. No network connection or account is needed.

## Presentation polish

- Make the four pads visually distinct but consistent with the orange-and-blue stadium palette. Use a different light pulse for “watch,” “your turn,” and “correct.”
- Give each pad a short, recognizable musical hit. Keep sound and visual timing aligned; the sound should still make the beat understandable if the player is not looking directly at the scoreboard.
- Put the pattern on the stadium scoreboard or a large HUD panel. Show a short countdown before the response and a clear beat marker during it.
- Celebrate each correct note, phrase completion, and final result with punchy sound and animation. Use the Gator Chomp animation as the payoff if it can be triggered cleanly.
- Keep HUD copy brief. Always tell the player which action to use and whether a miss was caused by the pad or timing.
- Keep the camera framed on Mario and the pad cluster. Avoid forcing a long cross-field run or hiding the target pads behind the HUD.
- Make the opening start automatically after a short intro, or let the player begin with one obvious input. Avoid relying on chat commands during the demo.

## Current implementation to build on

- `mods/sgl64/swamp_missions.lua` registers the existing **Act 3: GATOR CHOMP CHORUS - 2P** and defines its four end-zone button coordinates. Today it requires at least two players and asks them to hold different distant corners while they pound on “CHOMP!”.
- `mods/sgl64/sgl_mission.lua` contains `sgl_mission_kind_buttons`, button visuals, player-on-button checks, chant timing, ground-pound detection, HUD markers, and failure feedback. It assumes a set of simultaneously occupied pads; it does **not** currently implement a solo watch-and-repeat sequence.
- `mods/sgl64/course.lua` names Swamp Act 3 and currently labels it as two-player-only.
- `tools/luatest/test_missions.lua` covers the current multiplayer chorus behavior. If that act is changed or shared logic is refactored, preserve the intended multiplayer behavior or deliberately update the act’s contract and related coverage.
- `docs/singleplayer_campaign.md` lines 117–120 already describe a proposed solo rhythm variant: watch a phrase, move to the lit pad, and ground-pound on “CHOMP!”. It is design guidance, not proof that the solo behavior exists.
- `README.md` lines 93–101 describes the current experience and says Act 3 needs two players.

## Suggested implementation shape

Treat the solo sequence as a small state machine rather than trying to force it into the existing “all lit pads occupied at once” rules:

1. `INTRO`: show one short instruction and the control prompt.
2. `PLAYBACK`: flash and sound each pad in the phrase at a steady, readable tempo.
3. `INPUT`: accept one pad plus ground-pound per beat; advance the note index on a correct hit.
4. `FEEDBACK`: show a brief correct/miss response, then resume the same phrase or advance.
5. `SUCCESS`: show score/grade, play the celebration, and offer replay.

Keep sequence data explicit and easy to tune, such as a list of pad indices per round, beat duration, and timing window. Use a compact pad cluster, and start with a forgiving window (around 350–450 ms on either side of the target); tune it by playing on keyboard and controller. Do not assume the existing one-second co-op chant timing feels right for a solo pattern game.

Decide before implementation whether Act 3 becomes solo-only or whether the co-op chorus remains selectable. The shortest route for a single-player demo is to let solo players start the mini-game immediately. If co-op must stay, keep its behavior and make the solo version a separate mode or act entry rather than silently changing the current multiplayer rules.

## Demo-ready checklist

- A first-time player can start without setup, another player, chat commands, or reading a long explanation.
- The game clearly distinguishes watching the pattern from repeating it.
- Every note has synchronized visual and audio cues, and a correct input gets immediate feedback.
- The pads are reachable and camera-visible; no sequence requires a cross-field sprint.
- A miss can be understood and retried immediately, with no life or progress loss.
- A complete run reaches a celebratory result without relying on a full course or campaign.
- Replay starts cleanly and resets the sequence, score, and visuals.
- The final result and celebration display once, without awarding multiple stars or replaying the star cutscene on every note.
- The decision about the existing co-op Act 3 is reflected consistently in the act name, player-count rules, NPC post text, README, and mission coverage.

## Out of scope for this demo

Full solo campaign progression, online score submission, global leaderboards, multiple venues, unlock trees, and a large collection of songs. Add those only after the core round is fun and readable on its own.
