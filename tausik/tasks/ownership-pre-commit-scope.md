---
slug: ownership-pre-commit-scope
title: "Доказать ownership по pre-commit объявленной scope"
status: active
epic: release-19-renar-conformance
story: release19-proof-integrity
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "Change only committed task-ownership provenance extraction in scripts/verify_commit_ownership.py and its real-git behavioral tests; document the parent-tree declaration boundary if externally observable."
scope_exclude: "Do not trust current worktree declarations, alter dynamic-block semantics, weaken ambiguity or uncommitted-change handling, rewrite git history, release, tag, push or touch user-owned .agents/."
relevant_files:
  - "scripts/verify_commit_ownership.py"
  - "tests/test_verify_commit_ownership.py"
scope_paths:
  - "scripts/verify_commit_ownership.py"
  - "tests/test_verify_commit_ownership.py"
  - "docs/en/receipts.md"
  - "docs/ru/receipts.md"
  - "tausik/tasks/ownership-pre-commit-scope.md"
  - "tausik/stories/release19-proof-integrity.md"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Разрешить verify исключать committed path только когда ровно одна чужая task export уже существовала в parent commit, была active/blocked/done до commit и объявляла именно этот путь; сохранить fail-closed для отсутствующей, изменённой-в-том-же-commit, неоднозначной и uncommitted декларации.

## Acceptance Criteria

AC-1: real-git test proves one pre-existing sibling declaration owns a later committed matching path. AC-2: two pre-existing sibling declarations for same path remain undeclared. AC-3: missing parent declaration and uncommitted path remain undeclared. AC-4: current same-commit and dynamic-only proofs remain green. AC-5: focused pytest, ruff, mypy, dedupe and signed verify pass.

## Plan

[{"step": "Add strict parent-commit declaration candidate extraction and preserve same-commit ownership.", "done": true}, {"step": "Add real-git behavioral tests for unique predeclared, ambiguous, missing and uncommitted cases.", "done": true}, {"step": "Run focused pytest, ruff, mypy and dedupe; then signed verify.", "done": false}]

## Rollback

Revert the dedicated ownership-provenance commit.

## Journal

- 2026-09-12T11:08:24Z [implementation] — Steps 1–2 done: added immutable parent-tree declaration proof via git grep candidate lookup plus parsed exact relevant_files validation; real-git tests cover unique active owner, ambiguity, planning, missing declaration, existing same-commit and uncommitted negatives.
