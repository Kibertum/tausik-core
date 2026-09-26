---
slug: root-skill-count-14
title: "Синхронизировать корневой каталог навыков с 14 core навыками"
status: done
epic: release-19-agent-effectiveness
story: release19-effective-context
complexity: simple
role: tech-writer
stack: python
tier: null
call_budget: null
defect_of: docs-generated-constants-19-drift
scope: "Edit only root README.md and README.ru.md core-skill count cells, with focused existing check-docs proof; update generated task/story state."
scope_exclude: "Do not alter generated constants, skills, bootstrap behavior, release/tag/push or user-owned .agents/."
relevant_files:
  - README.md
  - README.ru.md
  - "tests/test_check_docs_hook.py"
scope_paths:
  - README.md
  - README.ru.md
  - "tests/test_check_docs_hook.py"
  - "tausik/tasks/root-skill-count-14.md"
  - "tausik/tasks/docs-generated-constants-19-drift.md"
  - "tausik/stories/release19-effective-context.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-12T12:19:25Z"
resolution: null
resolution_reason: null
---

## Goal

Устранить EN/RU README дрейф: после добавления /i-have-adhd корневой каталог всё ещё говорит о 13 core навыках, из-за чего check_docs не может подтвердить сгенерированные константы.

## Acceptance Criteria

AC-1: all root README catalog cells use the computed 14-core count in EN and RU. AC-2: no official/conditional-skill count or host claim is changed. AC-3: negative boundary: check_docs still rejects a stale 13-core declaration. AC-4: focused check-docs test and signed verify pass.

## Plan

[{"step": "Locate every root README count cell rejected by check_docs and confirm the canonical value.", "done": true}, {"step": "Update only the stale EN/RU core-skill catalog cells.", "done": true}, {"step": "Run focused check-docs proof and signed verify; then unblock the generated-constants task.", "done": true}]

## Rollback

Revert the two documentation lines if the canonical computed count changes.

## Journal

- 2026-09-12T10:23:49Z [implementation] — Canonical generated constant is skills_core_count=14. Located the stale root README catalog cells named by check_docs; next step is an EN/RU mirror-only update.
- 2026-09-12T10:24:28Z [implementation] — Updated exactly the six EN/RU root catalog cells from 13 to the generated canonical 14; no official/conditional count or host claim changed. Focused real-repo check-docs proof now passes.
- 2026-09-12T10:24:39Z [implementation] — README.md and README.ru.md cells are corrected, but focused check_docs now exposes a separate stale static count in AGENTS.md:100 ('13 core skills'). That onboarding contract lies outside this task's declared root-README scope; it must be fixed separately rather than silently widening the task.
- 2026-09-12T12:18:20Z [implementation] — Unblocked: the separate AGENTS.md static count is fixed and closed (agents-skill-count-14, commit 6013fb2e); relevant_files declared now (they were never declared, which is why README.md/README.ru.md could not be attributed to this task in sibling receipts).
- 2026-09-12T12:18:21Z [implementation] — AC verified: AC-1 ✓ grep shows all six EN/RU root catalog cells (README.md:141,154-158; README.ru.md:140,153-157) read 14 core, no 13 remains. AC-2 ✓ official count (20) and host claims in the same rows unchanged (git diff of 6013fb2e touched only the core cells). AC-3 ✓ TestDriftDetected::test_drifted_json_returns_1 rejects a stale declaration. AC-4 ✓ tests/test_check_docs_hook.py 6/6 incl. TestRealRepoSync; signed verify below. Domain: the README catalog now equals what bootstrap deploys (14 core + brain conditional).
- 2026-09-12T12:19:13Z [implementation] — Root cause (documentation): the six hand-maintained root catalog cells (EN+RU) were not updated when the /i-have-adhd skill raised the deployed core count to 14 in 4720e8e0; the generated constants caught it only in the full lane. Prevention: check_docs real-repo test now guards the cells against constants.json; the skill-adding task's closure must regenerate constants and touch the catalog rows named in this task.
