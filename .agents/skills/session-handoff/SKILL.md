---
name: session-handoff
description: Create a compact continuation file for a fresh Claude Code session. Use after a major phase, before context reset, or when another agent will continue the work.
allowed-tools: Read, Glob, Grep, Bash, Write
---

# Session Handoff

Write `.agent-state/current-task.md`.

## Required sections

- Objective
- User constraints
- Decisions
- Relevant files
- Files changed
- Work completed
- Remaining work
- Commands run and summarized results
- Unresolved errors or risks
- Exact next action
- Suggested first command

## Rules

- Maximum 100 lines.
- Do not paste full logs or diffs.
- Preserve exact paths, command names, and error messages when unresolved.
- Do not claim validation passed unless it was run successfully.
- Never include secrets or environment values.
