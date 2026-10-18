# Overnight progress

> **Historical snapshot:** the door thresholds and test instructions below describe that earlier build. Current built stages open with 0 stars; unbuilt stages remain coming soon. Follow `docs/development.md` for current testing instructions.

Everything below is installed in the game, compiles in coopdx and is committed to
[Raamia/gimmickfc](https://github.com/Raamia/gimmickfc).
Nothing has been played in the game yet. Your first session is the real test.

## Done overnight

| Piece | Status | Reviews |
|---|---|---|
| **Stage doors + act select** | The hub now replaces Mario's castle grounds. Walking into a building door opens SM64's real act select. Stars save, are shared, and send you back outside the door. | flow tests 217/217 |
| **Character select menu** | "CHOOSE YOUR GATOR!": the 10 friends' portraits pop up on first spawn and your pick is remembered. Reopen with L + START or `/char`. | |
| **Course 1: The Swamp** (Auditorium door, open from the start) | Ben Hill Griffin Stadium at true scale, with the O'Connell Center and Florida Gym. 3 missions: climb to the press-box roof, a stadium stair sprint race, and the co-op **Gator Chomp Chorus**. | technical 9/10, fun 6/10 (most points fixed) |
| **Course 2: Reitz + Engineering** (The Hub door, 2 stars) | The Reitz Union (enterable food court, climbable tower), Weil Hall and its clock tower, Malachowsky Hall. 3 missions, including the co-op **Remote Robotics Lab** (operators steer cranes that carry riders). | technical 8/10, fun 7/10 |
| **Character polish** | The light outline around eyes and mouths is gone, there are no sleeve shards at bent elbows, the wings are out of the big hair, Raami's temple gaps are closed, Cher's hair clips less, and Daniel's eyes are narrower and further apart. | all 10 re-validated |
| **Course 3: Lake Alice** (Newell door, **5 stars**) | The real lake basin with its 3 bog islands, wading shallows and swimmable water, lily pads, bald cypress, the two bat houses and the Baughman Center. 3 missions: **Boardwalk Welcome** (lily-pad hop to the observation deck), **Gator Hop** (ride 17 gator platforms across the deep hole), and the co-op **Bat Census at Dusk** (the lake turns to dusk while 2-4 of you count bats). | technical 8/10, fun 7/10 |

## Test it (about 15 minutes)

The full step-by-step script is in **README.md, "Testing"**. The short version:

1. Start sm64coopdx, **Host**, use an **unused save slot**, and enable only **Super Gatorlator 64**.
2. You spawn on the Plaza and the character menu opens. Pick yourself.
3. Walk ~80 m south to the **Auditorium** door (gold star above it) and walk in. You get the act select with **THE SWAMP**. Pick act 1 and climb to the press-box roof for the star.
4. Back on campus, play act 2 (the race, D-pad Down to the start box).
5. With 2 stars, **The Hub** door opens **Reitz + Engineering**. With 5, **Newell Hall's** east door opens **Lake Alice**.
6. With a friend: they get a "Study Group" popup when you enter a mission. D-pad Up or `/join` follows you. Try the co-op acts (Gator Chomp Chorus is act 3 of the Swamp).

Useful commands: `/campus where`, `/campus list`, `/mission`, `/join`, `/char`.

**Please tell me:** whether anything crashes or shows a `[SGL]` error in the console (the ` key), whether the race times feel fair, whether climbs are too hard or too easy, and how it runs.

## Decisions for you (none of them block anything)

1. **Daniel's eyes:** they're now narrower and further apart (closer to his photos), but a bit less expressive. Keep them, or go back to the previous version?
2. **Final Exam trivia:** the boss asks multiple-choice questions. Want to write campus in-jokes for it with your friends?
3. **Next stages:** the plan continues with Marston Library (5 stars), Library West After Dark (14), the Century Tower climb (20), then the Final Exam. Same order, or something else first?
4. **Cher's long hair:** it still clips a little in crouches and swimming. Fixing that fully needs hair that moves on its own (a bigger job).

## A change I made

**Lake Alice now opens at 5 stars instead of 8, and Marston moves from 5 to 8.** Each built course has two solo acts and one 2-player act, so a solo player can only reach 6 stars right now, and 8 was every star in the game with no slack. Marston isn't built yet, so swapping the two keeps the unlock curve rising. Tests and docs are updated. Tell me if you'd rather have it back at 8.

## Known rough edges

- **Untested in game:** mission feel values (race par times, climb heights, co-op timing windows) are untuned.
- **Hub:** fog color is a guess, and some generic rooftops can't be reached.
- **Lake Alice:** Jolly Roger Bay's slot brings its own music mixing, so the music shifts as you move around. The Baughman Center has no mission yet.
- **Doors:** Marston, Library West and Century Tower show "Coming soon".
- **Web version:** paused, as you chose.
