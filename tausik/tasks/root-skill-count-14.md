---
slug: root-skill-count-14
title: "Синхронизировать корневой каталог навыков с 14 core навыками"
status: blocked
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
relevant_files: []
scope_paths:
  - README.md
  - README.ru.md
  - "tests/test_check_docs_hook.py"
  - "tausik/tasks/root-skill-count-14.md"
  - "tausik/tasks/docs-generated-constants-19-drift.md"
  - "tausik/stories/release19-effective-context.md"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Устранить EN/RU README дрейф: после добавления /i-have-adhd корневой каталог всё ещё говорит о 13 core навыках, из-за чего check_docs не может подтвердить сгенерированные константы.

## Acceptance Criteria

AC-1: all root README catalog cells use the computed 14-core count in EN and RU. AC-2: no official/conditional-skill count or host claim is changed. AC-3: negative boundary: check_docs still rejects a stale 13-core declaration. AC-4: focused check-docs test and signed verify pass.

## Plan

[{"step": "Locate every root README count cell rejected by check_docs and confirm the canonical value.", "done": true}, {"step": "Update only the stale EN/RU core-skill catalog cells.", "done": true}, {"step": "Run focused check-docs proof and signed verify; then unblock the generated-constants task.", "done": false}]

## Rollback

Revert the two documentation lines if the canonical computed count changes.

## Journal

- 2026-09-12T10:23:49Z [implementation] — Canonical generated constant is skills_core_count=14. Located the stale root README catalog cells named by check_docs; next step is an EN/RU mirror-only update.
- 2026-09-12T10:24:28Z [implementation] — Updated exactly the six EN/RU root catalog cells from 13 to the generated canonical 14; no official/conditional count or host claim changed. Focused real-repo check-docs proof now passes.
- 2026-09-12T10:24:39Z [implementation] — README.md and README.ru.md cells are corrected, but focused check_docs now exposes a separate stale static count in AGENTS.md:100 ('13 core skills'). That onboarding contract lies outside this task's declared root-README scope; it must be fixed separately rather than silently widening the task.
