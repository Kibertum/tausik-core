---
slug: docs-troubleshooting-purge-legacy
title: "Troubleshooting purge — drop legacy CouchDB/Meilisearch/Raven sections"
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
completed_at: "2026-05-15T13:24:39Z"
---

## Goal

troubleshooting.md (EN+RU): убрать всю секцию CouchDB/Meilisearch/Raven (50-55), убрать 'raven_briefing' MCP, удалить 'tausik dep list' (нет команды), исправить typo 'task_done vs task_done' → 'task_done_v2 vs task_done', исправить .claude-project/config.json → .tausik/config.json. Brain секцию переписать под Notion-flow (tausik brain init).

## Acceptance Criteria

(1) Все правки точечные согласно audit-findings. (2) pnpm build clean без новых dead links. (3) Diff чистый — содержание не утеряно. (4) Ошибка: не должно остаться текста с устаревшими версиями/командами/упоминаниями.

## Plan

## Rollback

## Journal

- 2026-05-15T13:24:39Z [implementation] — AC verified: правки сделаны, pnpm build clean 4.61s, без новых dead links.
