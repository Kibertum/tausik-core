---
slug: ownership-commit-local-scope-paths
title: "Доказать ownership commit-local scope_paths"
status: done
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
completed_at: "2026-09-12T12:09:16Z"
resolution: null
resolution_reason: null
---

## Goal

Разрешить verify исключать committed path, когда ровно одна чужая task export в том же immutable commit объявляет этот путь через scope_paths (включая безопасный glob); не доверять current worktree и сохранить fail-closed для отсутствия, неоднозначности и path вне scope.

## Acceptance Criteria

AC-1: real-git test proves same-commit unique scope_paths glob owns matching path. AC-2 (negative): two matching scope_paths exports remain undeclared. AC-3 (negative): a path outside scope_paths and an uncommitted path remain undeclared. AC-4: existing relevant_files and parent-tree proofs remain green. AC-5: focused pytest, ruff, mypy, dedupe and signed verify pass.

## Plan

[{"step": "Add a commit-local scope_paths matcher that remains exact and fail-closed.", "done": true}, {"step": "Add real-git positive and negative ownership regressions.", "done": true}, {"step": "Run focused checks and signed verify.", "done": true}]

## Rollback

Revert the dedicated ownership-provenance commit.

## Journal

- 2026-09-12T12:08:52Z [implementation] — AC verified: AC-1 ✓ test_same_commit_scope_path_glob_owns_matching_state_file (real git, unique glob owner). AC-2 ✓ test_two_sibling_exports_in_one_commit_remain_ambiguous[two-acl-globs] added now: two matching scope_paths exports keep foreign.py undeclared (plus relevant-files-versus-acl-glob). AC-3 ✓ test_same_commit_scope_path_without_active_matching_owner_stays_undeclared[active-foreign.py] (outside scope) and test_uncommitted_undeclared_path_still_reddens_after_sibling_commit (uncommitted). AC-4 ✓ relevant_files and parent-tree proofs: test_committed_sibling_scope_is_not_charged_to_active_task[3], test_predeclared_active_sibling_scope_owns_later_commit green. AC-5 ✓ 22/22 focused, ruff, mypy (commit hook: 453 files OK), dedupe 322 unchanged, signed verify below. Domain: measured on the real backlog commit e2f55369 the glob ACL of normalize is the sole same-commit owner of moved state; the residue that remains is code from export-less commits, visible in the receipt.
