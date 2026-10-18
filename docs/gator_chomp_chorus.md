# Gator Chomp Chorus (The Swamp, act 3)

The act runs one of two games:

- **Alone: the solo rhythm game** in `mods/sgl64/swamp_chomp.lua`. Four pads (small purple switches) stand in a row in the middle of the north end zone, 3.5 m apart. Their positions come from `SWAMP_POINTS` (the NW/NE corner buttons) in `swamp_missions.lua`, and they sit well away from the corner buttons.
- **2+ players: the co-op chorus**, unchanged from before. Each player holds a lit end-zone corner, the crowd counts GA... TOR..., then everyone ground-pounds on CHOMP!, for 3 phrases (`sgl_mission_kind_buttons`, POUND mode).

Both games give the same star (id 2). The solo game succeeds through the normal mission path (`SUCCESS`), and the star drops from the south scoreboard to midfield once. If a second player arrives mid-game, the co-op chorus takes over.

## How to play (solo)

1. **Intro.** The screen says "Watch the pads, then repeat: jump + ground-pound (Z) on the lit pad". A `CHOMP PADS` marker points at the row.
2. **WATCH.** The pads play a phrase on a steady beat. Each one lights an orange flame and makes its own sound: Bubba chomp, big pound, box break, red coin. Pounds don't count during playback.
3. **READY... SET...** Two ticks follow. A pound on a pad now counts as **TOO EARLY**.
4. **YOUR TURN / GO!** The pads show small blue flames. Jump and press Z on each pad in the same order. A correct pad squishes, flashes a big blue flame and plays its sound. You have 2.5 s for each pad, counted from GO! or from your last hit. Pounding off the pads is ignored, so you can reposition.
5. **Feedback.** You see **NICE!** on success. **WRONG PAD**, **TOO EARLY** or **TOO LATE** replays the same phrase. There are no lives, only a miss count.
6. The phrases are a practice note, then rounds of 2, 3 and 4 notes. When all of them are done you get **GATOR GREAT!**, a grade by misses (0 = A+, 1 = A, 2-3 = B, more = C) and a cheer. Albert does the Gator Chomp at his `swamp_chorus` post, and the star spawns. **Press B to play again**: the pads rotate and no second star is given.

## Demo

- Host: `/campus swamp 3 me`, or walk into the Swamp door and pick **GATOR CHOMP CHORUS** in the act select.
- Alone, the game starts at once. The bottom prompt reads "Solo Gator Chomp - a study buddy makes it the co-op chorus".
- To show co-op, have a friend join (D-pad Up on the Study Group invite). The game switches to the corner-button chorus.
- `/mission reset` restarts the act.

## Tuning (`SGL_CHOMP` in swamp_chomp.lua)

| key | default | meaning |
|---|---|---|
| `beat` | 24 frames (0.8 s) | one played note |
| `litFrames` | 16 | how long a played pad stays lit |
| `countFrames` | 20 | each of READY... / SET... |
| `noteTime` | 75 (2.5 s) | time allowed to land the next pound (a jump + Z is about 1 s) |
| `feedbackFrames` | 45 | NICE! / WRONG PAD on screen |
| `introFrames` | 120 | intro line |
| `padRadius` | 200 | xz hit radius of a pad (game units) |
| `padScale` | 1.0 | purple switch scale (the corner buttons are 1.5) |
| `phrases` | `{2}, {1,3}, {4,2,3}, {1,4,2,3}` | practice, then the rounds (pads 1-4 west to east) |
| `sounds` | 4 vanilla `SOUND_*` | one per pad |

The pad row's position is in `swamp_missions.lua`: the act 3 `sgl_swamp_chomp_kind(..., pads)` call, at the midpoint of the NW and NE corners plus 4.5 m toward the goal line.

## Tests

`tools/luatest/test_missions.lua` has the test "act 3 solo". It plays a WRONG PAD, a TOO EARLY and then every phrase to GATOR GREAT!, and checks for exactly one star, the B replay, and that 2 players still get the co-op chorus. Run it with `tools/luatest/run.sh`.

## Not done yet

There is no custom music or audio (vanilla sounds only), no free-play kiosk, no best score in mod storage, and no camera scripting. Solo state is kept locally on the lone player's client, which is the leader. A solo win doesn't report a verified leaderboard run.
