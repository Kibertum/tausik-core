---
slug: memory-layers
title: "Memory layer: local vs shared separation, cq fallback"
status: done
epic: frai-v27
story: memory-rethink
complexity: medium
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
completed_at: "2026-03-29T11:59:15Z"
---

## Goal

Разделить memory на local (project-specific) и shared (cross-project через cq). Local остаётся в SQLite, shared запрашивается из cq.

## Acceptance Criteria

1. memory_search ищет local, потом cq (если настроен). 2. memory add --shared публикует в cq + local. 3. dead-end предлагает publish в cq. 4. /start загружает cq entries по стеку. 5. Если cq недоступен — не блокирует, только local results. 6. Тесты.

## Plan

## Rollback

## Journal
