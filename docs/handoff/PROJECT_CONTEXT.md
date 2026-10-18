# Project context

Super Gatorlator 64 is a native sm64coopdx v1.5.1 UF campus mod, with a React companion site and hosted account/run services. It is not a browser game.

## Source map
- `mods/sgl64/course.lua`: canonical stages, acts, star IDs and warp contract.
- `levels.lua`: hub doors and self/party travel; `/campus swamp 3 me` launches Chomp solo.
- `sgl_mission.lua`: elected round controller, shared state and rewards.
- `wf_reitz_missions.lua`: rooftop, tokens and crane; operator camera.
- `sgl_deepspace.lua`: native BOARDS/MAP, travel and leaderboard cache/outbox.
- `sgl_controls.lua`: cursor toggle, keyboard 0 and `/mouse`.
- `sgl_hud.lua`, `sgl_status_hud.lua`: native drawing and UF HUD assets.
- `sgl_login.lua`, `sgl_bridge.lua`: Gator Pass/device flow and hosted events.
- Lua files load alphabetically in a mod environment; `_G` differs from `_ENV`. Guard late globals and use the offline checker.
- `tools/campus`, `tools/actors`, `tools/blender`: generated campus, actors and character exports.

## Website
`companion/app` uses React, TypeScript, Vite, DeepSpace and Cloudflare Workers.
Read its AGENTS.md and local DeepSpace skill first.
`SiteHeader.tsx` is shared across public and app routes; `Navigation.tsx` adds account controls.
`src/data/mission-catalog.json` drives board and leaderboard entries.
Public `pages/index.tsx` must prerender without authenticated hooks/window access.
App pages live under `src/pages/(app)`; preserve `studyFetch` integration.
Read DESIGN.md and existing styles before UI changes.
Seven curated missions now include `swamp_chorus`, The Swamp act 3.
Solo Chomp: watch four pads, repeat ground-pound sequences, grade A+–C.
Co-op Chomp is a distinct shared rhythm mode; solo grades are not verified timed records.
Detailed guide remains on Play. No separate minigame category on the board.

## Accepted UX
Shared navy/gold header, gold G, readable navigation, cream cards and orange accents.
Remove squads, manual timing forms, player-reported wording, bonus crest decoration,
placeholder building drawings, duplicate campus maps and labels covering map buildings.
Keep OSM attribution. Only Reitz and Marston are advertised enterable interiors;
map imagery is campus context, not proof every road/building is playable.
Native BOARDS and MAP buttons should be compact and mirrored; modal fonts readable.
Co-op completion should reward participating players and teleport them out together.

## Services
`server/api`: FastAPI/Postgres, Gator Pass, jobs, guest slots, events and runs.
`server/worker`: vision/Blender guest-character pipeline and object storage outputs.
`server/bridge`: headless game stdout SGLEVT to API, atomic ModFS inbox, guest deployment.
Hosted runs are server timed; offline native bridge uploads a local outbox after game exit.
DeepSpace authentication and Auth0 Gator Pass are different; account linking is incomplete.
`server/web` is a separate activation/gallery frontend, not the companion app.

## Branches and deployment
Main baseline: the earlier change. Raami branch the earlier change includes solo Chomp at the earlier change.
branch review, fix/crane-camera-team-rewards at the earlier change, remains conflicting for teammate review.
It includes disabling stretched crane shadows, explicit crane camera vectors/FOV,
UF result textures and idempotent participant rewards with delayed group exit.
Offline Lua suite passed there; live camera/rendering acceptance remains unverified.
Local installed mod contains those fixes; main source does not yet include them.
No deployment was performed for this handoff. Follow docs/operations.md for releases.
Never copy .env, credentials, ROM, player photos, saves or production state into context.
See README.md, docs/flow.md, docs/operations.md and docs/web_platform_spec.md for details.
Older docs can contain stale squad/URL/runtime claims; source and actual deployment win.
