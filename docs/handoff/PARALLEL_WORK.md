# Two terminals

## Primary agent
Checkout: `/path/to/gimmickfc`
Branch: `fix/gator-chomp-catalog`; preview: 127.0.0.1:5181.
Owns the current catalog correction and handoff.

## Second Codex agent
Checkout: `/path/to/gimmickfc-worktree`
Branch: `codex/parallel-work`; latest primary website and HUD changes are merged here.
The branch also preserves the second agent’s HUD spacing and power-meter work in a WIP commit.
Compare commit history before assuming this branch is identical to the primary checkout.
Start:

```sh
cd /path/to/gimmickfc-worktree
codex
```

First prompt:
“Read AGENTS.md and .agent-state/current-task.md, then docs/handoff/PARALLEL_WORK.md.
Check git status. I will assign your task. Establish file ownership before editing;
preserve the other agent's changes and use your own branch.”

If a website task needs a preview, install dependencies in this checkout if absent,
then run `npx deepspace dev start --host 127.0.0.1 --port 5182` from companion/app.
Do not stop the primary preview on 5181.

## Coordination
Assign separate files or subsystems. Commit only owned changes; exchange commit IDs
and review diffs before cherry-picking. Never reset/clean another checkout.
Both checkouts share the same installed game directory:
`~/Library/Application Support/sm64coopdx/mods/sgl64`.
Only one designated operator runs install-mods.sh, restarts the game or deploys.
Do not install main over pending game fixes without checking the installed version.
Never run two writers against the same saves, bridge inbox, server or database.
branch review merge conflicts are reserved for the teammate, as the user requested.
