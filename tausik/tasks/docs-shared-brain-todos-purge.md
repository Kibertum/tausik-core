---
slug: docs-shared-brain-todos-purge
title: "Shared-brain.md purge stale TODOs — 14 shipped modules still labeled pending"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-15T13:24:40Z"
---

## Goal

shared-brain.md (EN+RU): удалить '## Still TODO (planning)' секцию (lines 289-291) — все 14 модулей shipped. Lines 252-253: убрать (pending) от brain-scrubbing и brain-classifier. Удалить '## Alternative: Outline (TODO)' пустую секцию line 279.

## Acceptance Criteria

(1) Все правки точечные согласно audit-findings. (2) pnpm build clean без новых dead links. (3) Diff чистый — содержание не утеряно. (4) Ошибка: не должно остаться текста с устаревшими версиями/командами/упоминаниями.

## Plan

## Rollback

## Journal

- 2026-05-15T13:24:40Z [implementation] — AC verified: правки сделаны, pnpm build clean 4.61s, без новых dead links.
