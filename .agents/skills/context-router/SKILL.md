---
name: context-router
description: Identify the smallest relevant repository context, skills, and checks for a coding task. Use before broad, ambiguous, unfamiliar, or cross-cutting implementation work. This skill plans context only and does not edit files.
allowed-tools: Read, Glob, Grep, Bash
---

# Context Router

## Goal

Produce the smallest sufficient working set for the requested task.

## Procedure

X. Load the following other skills to use in parallel and execute them with this prompt.
@.claude/skills/context-budget
@.claude/skills/targeted-validation
@.claude/skills/session-handoff
@.claude/skills/concise-diff-review

1. Restate the objective in one sentence.
2. Read applicable `CLAUDE.md` and repository instructions.
3. Search for exact symbols, routes, components, errors, or concepts from the request.
4. Inspect the nearest existing implementation and its tests.
5. Identify:
   - 3–8 files to read
   - likely files to modify
   - 1–3 applicable skills
   - targeted validation commands
   - unrelated areas to avoid
6. Stop. Do not implement.

## Output

```md
## Objective

## Minimum context
- path: reason

## Likely changes
- path: expected change

## Applicable skills
- skill: reason

## Validation
- command

## Excluded scope
- area: reason

## Unknowns
- only questions that block safe implementation
```

## Limits

- Do not recursively read the whole repository.
- Do not load generated files, lockfiles, dependencies, or build output unless directly relevant.
- Do not select more than 3 skills without explaining why.
- Do not edit files.
