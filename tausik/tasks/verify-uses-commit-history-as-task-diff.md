---
slug: verify-uses-commit-history-as-task-diff
title: "Verify считает коммиты других задач изменениями активной задачи"
status: blocked
epic: release-19-renar-conformance
story: release19-proof-integrity
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: write-gate-is-blind-to-pathlib-writes
scope: "scripts/ verification/cache provenance path; focused tests and, if externally observable, verification documentation."
scope_exclude: "Не менять semantics ACL pathlib-задачи, не переписывать историю Git, не ослаблять git-mismatch для неизвестного происхождения, не выполнять release/push/tag."
relevant_files:
  - "scripts/verify_commit_ownership.py"
  - "scripts/verify_scope_honesty.py"
  - "tests/test_verify_commit_ownership.py"
  - "tests/test_verify_scope_honesty.py"
  - "docs/en/receipts.md"
  - "docs/ru/receipts.md"
scope_paths:
  - "scripts/verify_commit_ownership.py"
  - "scripts/verify_scope_honesty.py"
  - "tests/test_verify_commit_ownership.py"
  - "tests/test_verify_scope_honesty.py"
  - "docs/en/receipts.md"
  - "docs/ru/receipts.md"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Квитанция verify должна сравнивать declared relevant_files только с изменениями, относимыми к проверяемой задаче, и не делать корректную узкую задачу красной из-за отдельно спланированного и закоммиченного изменения после её started_at.

## Acceptance Criteria

AC-1: после отдельного коммита несвязанной задачи verify ранее начатой задачи с полным собственным declared scope не получает git-mismatch только из-за этого коммита. AC-2: незакоммичённое или относимое к задаче изменение вне declared relevant_files по-прежнему даёт git-mismatch с именами путей. AC-3: алгоритм происхождения diff и его граница документированы; он не скрывает изменения без подтверждённого task ownership. AC-4: регрессия покрыта поведенческими тестами на реальном пути verify/cache, включая отрицательный случай. AC-5: scoped pytest, ruff и dedupe-аудит проходят.

## Plan

[{"step": "Reproduce the false git-mismatch with two separately-scoped tasks/commits and trace the current verify provenance boundary.", "done": true}, {"step": "Choose and record a conservative ownership source that excludes only changes proven to belong to another task.", "done": true}, {"step": "Implement the verifier/cache provenance correction without weakening mismatch detection for unknown changes.", "done": true}, {"step": "Add focused behavioral regression tests for the cross-task committed case and the undeclared-change negative case.", "done": true}, {"step": "Run scoped tests, ruff, dedupe audit and tausik_verify; log AC evidence.", "done": false}]

## Rollback

git revert of the dedicated commit restores the prior strict history-based verifier behavior.

## Journal

- 2026-09-10T12:24:53Z [implementation] — Шаг 1: причина подтверждена в scripts/verify_git_diff.py: changed_files_since объединяет git log --since=<started_at> с git diff HEAD без происхождения. Коммит 52097532 содержит завершённые Codex-задачи и активную pathlib-задачу, поэтому последняя ложно видит чужие пути. Важно: одной временной метки недостаточно для ownership.
- 2026-09-10T12:28:44Z [implementation] — Шаги 2–4: выбран и реализован консервативный commit-local ownership. Вычитаются только пути, которые тот же commit однозначно связывает с переходом другого task export в done и его committed relevant_files; uncommitted, malformed и ambiguous paths остаются. Добавлены real-git регрессии: sibling completion не краснит subject, staged undeclared path всё ещё краснит.
- 2026-09-10T12:30:45Z [implementation] — Шаг 5: MCP verify #2391: ruff PASS, но pytest FAIL из-за scope selector: для изменённых verify-модулей выбрано 78 тестовых файлов и gate не завершился за свой лимит. Это не исправлять повышением timeout: причина и требуемое доказательство принадлежат существующей release-задаче verify-certifies-a-run-that-touched-no-test-of-the-subject.
- 2026-09-10T13:14:50Z [implementation] — Focused real-git regressions: 42 passed; ruff, mypy and dedupe baseline passed. A fresh-source verify was launched but its stdout transport detached while the process continued; its result cannot be used as evidence, so the confirmed project.py→pytest process tree was terminated. Need a persistent/captured verification invocation after MCP/runtime refresh; no certificate or closure attempted.
