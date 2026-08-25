---
slug: real-migrations
title: "Реальные schema migrations (не заглушки)"
status: done
epic: release-ready
story: p0-blockers
complexity: medium
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/backend_schema.py"
  - "tests/test_migrations.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-03-14T13:07:32Z"
---

## Goal

MIGRATIONS dict содержит рабочие ALTER TABLE. upgrade() корректно мигрирует v1→v3

## Acceptance Criteria

1. Migration v2 добавляет claimed_by | 2. Migration v3 содержит реальный DDL | 3. Тест: v1 БД → upgrade() → schema v3 | 4. Откат невозможен — задокументировано

## Plan

## Rollback

## Journal
