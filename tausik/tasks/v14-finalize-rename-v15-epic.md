---
slug: v14-finalize-rename-v15-epic
title: "Переименовать v15-task-done-reliability эпик и его задачи в v14-*"
status: done
epic: null
story: null
complexity: null
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: ".tausik/tausik.db (через MCP epic_add, story_add, task_add, task_delete, story_delete, epic_delete)"
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-02T21:45:22Z"
---

## Goal

Эпик v15-task-done-reliability был создан другим агентом, но по факту это часть v1.4 follow-up reliability. Содержит 3 истории (v15-runtime-safety, v15-cache-coherence, v15-defense-in-depth) и 5 planning задач. Переименовать всё в v14-* prefix для аудитопригодности через delete+recreate (slug — primary key, прямой rename невозможен). Цель: все 5 задач после ренейма имеют v14-* slug и сохранённые goal.

## Acceptance Criteria

1. Эпик v14-task-done-reliability создан, 3 истории (v14-runtime-safety, v14-cache-coherence, v14-defense-in-depth) созданы внутри.
2. 5 задач v14-verify-pipeline-envelope-timeout, v14-doctor-autoverify-banner, v14-task-done-relevant-files-fallback, v14-verify-hang-regression-test, v14-hook-matcher-narrow созданы с правильными story_slug и сохранёнными goal.
3. Старые v15-* (5 задач + 3 истории + 1 эпик) удалены через каскад epic_delete.
4. tausik epic_list показывает v14-task-done-reliability и НЕ показывает v15-task-done-reliability.
5. tausik task_list --epic v14-task-done-reliability возвращает 5 задач со статусом planning.
relevant_files: [нет — это БД-операции через MCP]

## Plan

## Rollback

## Journal

- 2026-05-02T21:44:59Z [implementation] — AC verified: 1. ✓ Epic v14-task-done-reliability создан (epic_add подтвердил) 2. ✓ 3 истории созданы: v14-runtime-safety, v14-cache-coherence, v14-defense-in-depth (story_add x3 подтвердил) 3. ✓ 5 задач созданы с правильными story_slug и goal перенесён из v15-* (task_add x5 подтвердил) 4. ✓ epic_delete v15-task-done-reliability каскадно удалил 3 v15-* истории и 5 v15-* задач 5. ✓ tausik_task_list --epic v14-task-done-reliability возвращает 5 задач со статусом planning: - v14-verify-pipeline-envelope-timeout (story v14-runtime-safety) - v14-doctor-autoverify-banner (story v14-runtime-safety) - v14-task-done-relevant-files-fallback (story v14-cache-coherence) - v14-verify-hang-regression-test (story v14-defense-in-depth) - v14-hook-matcher-narrow (story v14-defense-in-depth) 6. ✓ tausik_task_list --status planning не содержит v15-* slug relevant_files: [] (БД-only операция через MCP, code untouched)
- 2026-05-02T21:45:11Z [implementation] — AC verified (verify cache hit pre-check): 1. ✓ Epic v14-task-done-reliability создан 2. ✓ 3 истории созданы: v14-runtime-safety, v14-cache-coherence, v14-defense-in-depth 3. ✓ 5 задач v14-* созданы с правильными story_slug, goal перенесён из v15-* 4. ✓ epic_delete v15-task-done-reliability каскадно удалил 3 истории + 5 задач 5. ✓ task_list --epic v14-task-done-reliability возвращает 5 planning задач 6. ✓ task_list --status planning не содержит v15-* slug verify run: passed=True trigger=verify gates=['pytest'] (scoped to []=skip) relevant_files: [] (DB-only операция через MCP)
