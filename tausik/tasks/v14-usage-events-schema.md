---
slug: v14-usage-events-schema
title: "Таблица usage_events или расширение events для токенов"
status: done
epic: v14-cost-telemetry
story: v14-cost-schema
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: "scripts/backend_schema.py scripts/backend_migrations.py scripts/backend_queries.py scripts/project_service.py tests/test_metrics_session_usage.py"
scope_exclude: null
relevant_files:
  - "scripts/backend_schema.py"
  - "scripts/backend_migrations.py"
  - "tests/test_metrics_session_usage.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T10:51:09Z"
---

## Goal

Миграция + минимальный CRUD/insert путь.

## Acceptance Criteria

1. Миграция backend_schema. 2. Запись события из сервиса или заглушки. 3. Negative: отрицательные токены отклоняются.

## Plan

## Rollback

## Journal

- 2026-05-01T10:51:09Z [implementation] — AC verified: 1. ✓ usage_events в backend_schema + v23 migrations. 2. ✓ session_usage_record пишет session_record событие. 3. ✓ Negative: metrics_record_session отклоняет отрицательные токены/cost. AC-3: ✓ tested via tests/test_metrics_session_usage.py tests/test_migrations.py.
