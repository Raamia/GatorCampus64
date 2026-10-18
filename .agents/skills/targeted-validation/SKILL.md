---
name: targeted-validation
description: Select the narrowest reliable validation commands from changed files and repository scripts. Use after implementation and before running an expensive full suite.
allowed-tools: Read, Glob, Grep, Bash
---

# Targeted Validation

## Safety

By default, plan and print commands. Execute only when the user or current workflow explicitly requests execution.

## Procedure

1. Read `git diff --name-only` and `git status --short`.
2. Map changed paths to packages and nearby tests.
3. Prefer repository-defined scripts.
4. Order checks:
   1. syntax or formatting for changed files
   2. nearest unit tests
   3. package typecheck
   4. package lint
   5. integration tests when contracts changed
   6. full suite only when risk warrants it
5. Explain why each command is required.

## Limits

- Do not install dependencies.
- Do not start watch mode.
- Do not run deployment commands.
- Do not run a full monorepo suite when package-scoped checks are sufficient.
