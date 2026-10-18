# Current task

## Objective
Prepare context for a second Codex terminal and integrate Gator Chomp into the regular website mission catalog.

## User constraints
- Gator Chomp belongs in mission selection and leaderboard tabs, not a separate minigame section.
- Preserve previous website cleanup and consistent shared header.
- Teammate handles merge conflicts; do not merge branch review.
- No branch requirements on mission cards; setup details belong on Play.

## Decisions
- Verified location is The Swamp, act 3, mission id `swamp_chorus`, not Reitz.
- Catalog has seven curated missions, not all native campaign missions.
- Solo Chomp awards a grade; do not promise a verified solo time.
- Second agent uses a separate worktree/branch and port 5182.

## Relevant files
- `companion/app/src/data/mission-catalog.json`
- `companion/app/src/pages/(app)/home.tsx`
- `companion/app/src/pages/(app)/leaderboard.tsx`
- `docs/handoff/PROJECT_CONTEXT.md`
- `docs/handoff/PARALLEL_WORK.md`

## Files changed
- Website catalog, mission list, counts, leaderboard caption and setup guide title.
- Root AGENTS.md, this snapshot, docs/handoff and five.agents skills.

## Work completed
- Added Chomp to ordinary missions; removed separate guide from landing and board.
- Kept detailed instructions on Play; preserved teammate studyFetch integration.
- Created sibling worktree `gimmickfc-codex` on `codex/parallel-work`; merged latest `fix/gator-chomp-catalog` changes into it.
- Imported router and four companion skills from Raamia/my-claude-skills commit 341567a6debbdc240159677d34e1f5fe304a17dc.

## Remaining work
- User assigns a distinct task to the second agent.
- The second checkout includes WIP HUD edits (commits the earlier change and the earlier change); local Lua test suite has not been run.
- Live hosted verification of crane camera, shadows and shared mission completion.
- Teammate resolves branch review conflicts and integrates game fixes.

## Commands run and summarized results
- Git status/worktree inspections; main baseline the earlier change.
- Website TypeScript, 44 tests, ESLint and production build passed; no deployment.
- Previous game branch the earlier change passed tools/luatest/run.sh; no new game tests required for this catalog edit.

## Unresolved errors or risks
- branch review:https://github.com/Raamia/gimmickfc/pull/13 is conflicting.
- Current primary branch fix/gator-chomp-catalog is based on main; excludes branch review.
- Installed local mod includes the earlier change game fixes plus the recent map text, HUD spacing/power-meter and badge-removal changes; restart the game to load them.
- Raami branch the earlier change contains solo Chomp implementation; main lacks swamp_chomp.lua.
- Local installation does not update a hosted server or prove rendering acceptance.

## Exact next action
Read the handoff and accept a task with explicit file ownership before modifying code.

## Suggested first command
`git status --short --branch`
