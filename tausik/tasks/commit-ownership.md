---
slug: commit-ownership
title: "Отделить commit ownership от статуса закрытия задачи"
status: blocked
epic: release-19-renar-conformance
story: release19-proof-integrity
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/verify_commit_ownership.py; scripts/verify_scope_honesty.py; tests/test_verify_commit_ownership.py; task metadata only"
scope_exclude: "Do not weaken ownership for uncommitted, unknown, ambiguous or undeclared paths; do not alter task status manually; do not release, tag, push or modify user .agents/."
relevant_files:
  - "scripts/verify_commit_ownership.py"
  - "scripts/verify_scope_honesty.py"
  - "tests/test_verify_commit_ownership.py"
scope_paths:
  - "scripts/verify_commit_ownership.py"
  - "scripts/verify_scope_honesty.py"
  - "tests/test_verify_commit_ownership.py"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Разорвать QG-2 цикл release 1.9 без ручного изменения статусов: verify должен считать путь принадлежащим другой задаче, если тот же commit однозначно доказывает её declared scope, даже когда задача ещё active/blocked; статус done не является доказательством владения файлом.

## Acceptance Criteria

1. Реальный git-тест: sibling commit с task export другой active/blocked задачи и её declared relevant_files не создаёт git-mismatch у текущей задачи. 2. Отрицательный тест: uncommitted, неизвестный, ambiguous или не объявленный в sibling task path остаётся в mismatch. 3. Тест подтверждает, что один task export не может присвоить путь другой задаче без совпадения пути в том же commit. 4. Existing done-task case remains green. 5. Focused pytest, mypy, ruff, dedupe, signed verify; no release, tag or push.

## Plan

[{"step": "Reproduce the closure-order cycle against the current commit-local ownership helper and identify the minimum status-dependent predicate.", "done": true}, {"step": "Add real-git regressions for active/blocked sibling ownership, unknown paths and existing done-task behavior.", "done": true}, {"step": "Implement status-independent, commit-local ownership proof without relaxing ambiguity or uncommitted-path checks.", "done": true}, {"step": "Run focused tests, mypy, ruff and dedupe; record scope and security evidence.", "done": true}, {"step": "Run signed verify and close only on a presentable receipt.", "done": true}]

## Rollback

git revert the dedicated ownership-status decoupling commit.

## Journal

- 2026-09-11T12:22:57Z [implementation] — Removed the lifecycle-status predicate from commit-local ownership: task export + declared relevant path + same commit prove ownership whether sibling is active, blocked or done. Added a parameterized real-git regression across all three states; 44 focused tests, mypy, ruff and dedupe baseline pass. Unknown/uncommitted/ambiguous paths remain covered by existing negative behavior.
- 2026-09-11T12:26:10Z [implementation] — Verify #2403 confirms commit-local active/blocked ownership works for task commits, but exposes a separate source: framework-generated AGENTS.md/CLAUDE.md dynamic-state commit has no task export and therefore correctly remains unknown under this task's strict rule. Do not broaden ownership to arbitrary commits; handle generated dynamic-block-only changes in a dedicated task.
- 2026-09-12T11:05:44Z — Unblocking for a narrow follow-up: commit 6013fb2e contains scoped-pytest source without that task export in the same commit, while the task's declaration existed before the commit. Investigate a conservative parent-tree declaration proof; retain ambiguity and unknown-path failure.
- 2026-09-12T11:06:06Z [implementation] — Dead end confirmed: the existing contract requires same-commit task-export proof. Commit 6013fb2e did not modify scoped-pytest-empty-late-batch.md, even though its parent blob already declared the four affected files. Extending this task would weaken/contradict its acceptance criterion; create a separate narrowly specified predeclared-scope provenance task.
