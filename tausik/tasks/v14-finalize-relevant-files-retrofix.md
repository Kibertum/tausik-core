---
slug: v14-finalize-relevant-files-retrofix
title: "Retrofix done-задач закрытых без relevant_files (Phase C методологический долг)"
status: done
epic: null
story: null
complexity: null
role: qa
stack: python
tier: moderate
call_budget: 30
defect_of: null
scope: ".tausik/tausik.db через MCP task_update / sqlite UPDATE; задачи в Composer batch v14-* done без relevant_files"
scope_exclude: "любые .py файлы, docs/, tests/, agents/, bootstrap/, scripts/ — это data-fix"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-02T21:54:03Z"
---

## Goal

~7-10 done-задач из Composer batch (v14-bootstrap-context-tier, v14-pricing-table-config, v14-doctor-auto-verify-hint и т.д.) закрыты с WARN: scoped gates SKIPPED — pytest gate реально не отрабатывал. Composer retro (D-A) принял для 1.4 как есть, но мы оставляем себе аудиторский долг. Найти все done-задачи без relevant_files, добавить через task_update (поле notes или relevant_files напрямую если поле есть) — чтобы аудит был воспроизводим. Это методологический фикс, не code change.

## Acceptance Criteria

1. 9 done v14-* задач из Composer batch получают корректный relevant_files в DB через task_update: v14-agents-trim-redundancy, v14-artifact-search-ranking, v14-bootstrap-context-tier, v14-conftest-verify-first-comment, v14-docs-verify-glossary, v14-doctor-auto-verify-hint, v14-pricing-table-config, v14-status-json-compact, v14-usage-events-schema.
2. relevant_files определяется по сопоставлению с CHANGELOG.md секциями + git log.
3. SQL query «SELECT slug FROM tasks WHERE slug LIKE 'v14-%' AND status='done' AND (relevant_files IS NULL OR relevant_files IN ('[]',''))» возвращает только 4 строки: 3 finalize-* (БД/docs only — корректно) + 1 strategic-review (research-only — корректно). 9 Composer-задач исчезают из списка.
4. Notes этих 9 задач НЕ изменяются (ретро-фикс касается только relevant_files).
5. Negative: задачи с уже непустым relevant_files (27 штук) не трогаются.
6. Negative: задачи finalize-* и strategic-review (legitimate empty) остаются с пустым relevant_files — это ожидаемо.
relevant_files: .tausik/tausik.db (через MCP task_update; SQL не нужен напрямую если task_update поддерживает relevant_files)

## Plan

## Rollback

## Journal

- 2026-05-02T21:53:59Z [implementation] — AC verified: 1. ✓ 9 v14-* done задач retrofix'нуты с корректным relevant_files (mapping по CHANGELOG секциям + uncommitted state). 2. ✓ Файлы определены через сопоставление с CHANGELOG.md секциями 'Added — Epic v14-*' и tests/. 3. ✓ SQL post-check: empty count = 4 (вместо 13 до retrofix), точно: v14-strategic-review-10-1-4, v14-finalize-changelog-header, v14-finalize-rename-v15-epic, v14-finalize-doctor-drift-sync — все legitimate (research/БД-only). 4. ✓ Notes 9 retrofix'нутых задач не тронуты — только relevant_files поле обновлено через одиночный UPDATE. 5. ✓ 27 ранее заполненных задач не тронуты (UPDATE filtered by relevant_files IN [empty]). 6. ✓ Negative: finalize-* и strategic-review остаются empty (legitimate). data-migration выполнена через sqlite UPDATE как одноразовый retro-fix; runtime flow по-прежнему MCP-only.
