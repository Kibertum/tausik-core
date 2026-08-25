---
slug: v14-archive-done-tasks-spec
title: "Спека read-only архива done-задач старше N дней"
status: done
epic: v14-project-hygiene
story: v14-hygiene-policy
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "docs/en/task-archive-spec.md"
  - "docs/ru/task-archive-spec.md"
  - "docs/README.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T17:39:03Z"
---

## Goal

Параметры в config; активные задачи не затрагиваются.

## Acceptance Criteria

1. Документ спеки. 2. Параметры config. 3. Negative: active task никогда не архивируется.

## Plan

## Rollback

## Journal

- 2026-05-01T17:39:03Z [implementation] — AC verified: 1. Спеки docs/en и docs/ru/task-archive-spec.md + README #19. 2. Пример JSON task_archive в конфиге. 3. Negative: явный запрет архивации non-done статусов.
