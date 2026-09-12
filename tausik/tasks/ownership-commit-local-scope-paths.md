---
slug: ownership-commit-local-scope-paths
title: "Доказать ownership commit-local scope_paths"
status: active
epic: release-19-renar-conformance
story: release19-proof-integrity
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "Change only commit-local ownership extraction and its real-git behavioral tests."
scope_exclude: "Do not trust current worktree scope, loosen ambiguity handling, alter dynamic-state semantics, rewrite history, release, tag, push or touch user .agents/."
relevant_files:
  - "scripts/verify_commit_ownership.py"
  - "tests/test_verify_commit_ownership.py"
scope_paths:
  - "scripts/verify_commit_ownership.py"
  - "tests/test_verify_commit_ownership.py"
  - "tausik/tasks/ownership-commit-local-scope-paths.md"
  - "tausik/stories/release19-proof-integrity.md"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Разрешить verify исключать committed path, когда ровно одна чужая task export в том же immutable commit объявляет этот путь через scope_paths (включая безопасный glob); не доверять current worktree и сохранить fail-closed для отсутствия, неоднозначности и path вне scope.

## Acceptance Criteria

AC-1: real-git test proves same-commit unique scope_paths glob owns matching path. AC-2 (negative): two matching scope_paths exports remain undeclared. AC-3 (negative): a path outside scope_paths and an uncommitted path remain undeclared. AC-4: existing relevant_files and parent-tree proofs remain green. AC-5: focused pytest, ruff, mypy, dedupe and signed verify pass.

## Plan

[{"step": "Add a commit-local scope_paths matcher that remains exact and fail-closed.", "done": false}, {"step": "Add real-git positive and negative ownership regressions.", "done": false}, {"step": "Run focused checks and signed verify.", "done": false}]

## Rollback

Revert the dedicated ownership-provenance commit.

## Journal
