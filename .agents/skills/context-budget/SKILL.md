---
name: context-budget
description: Reduce context waste during long Claude Code sessions by preserving decisions and active state while removing completed exploration. Use after major phases, repeated tool output, or before compaction or a fresh session.
allowed-tools: Read, Glob, Grep
---

# Context Budget

## Procedure

1. State the current objective in one sentence.
2. Preserve:
   - user constraints
   - architecture decisions
   - files read
   - files changed
   - commands and summarized results
   - unresolved errors
   - validation already completed
   - exact next action
3. Mark as disposable:
   - repeated explanations
   - obsolete plans
   - completed discovery
   - raw logs already summarized
   - rejected hypotheses
4. Recommend one action:
   - continue
   - compact
   - create handoff and start fresh

## Output

Keep the result below 80 lines.

Never remove unresolved security, correctness, migration, or data-loss concerns.
