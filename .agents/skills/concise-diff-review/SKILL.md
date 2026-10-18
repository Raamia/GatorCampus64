---
name: concise-diff-review
description: Review the current Git diff for blocking correctness, security, compatibility, performance, and test issues without restating the patch. Use before commit or handoff.
allowed-tools: Read, Glob, Grep, Bash
---

# Concise Diff Review

## Read

- Applicable repository instructions
- `git diff --stat`
- Changed files only
- Nearby contracts and tests only when necessary

## Return

### Blocking
Maximum 5 findings.

### Probable defects
Maximum 5 findings.

### Missing validation
Only high-value commands.

Each finding must include:
- file and line
- failure mode
- minimal correction

## Do not

- Praise the patch.
- Summarize every file.
- Suggest unrelated refactors.
- Repeat code already visible.
- Report stylistic preferences as defects.
