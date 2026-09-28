---
slug: audit-log
title: "Audit log — таблица событий"
status: done
epic: release-ready
story: p1-value
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
  - "scripts/project_backend.py"
  - "scripts/project_cli.py"
  - "scripts/project_parser.py"
  - "scripts/project.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-03-14T13:12:51Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Таблица events хранит кто/что/когда менял. Автоматические triggers на tasks/decisions

## Acceptance Criteria

1. Таблица events (entity_type, entity_id, action, actor, timestamp, details_json) | 2. Triggers на INSERT/UPDATE/DELETE tasks | 3. CLI: events list [--entity tasks] [--limit N] | 4. Тесты покрывают все trigger-ы

## Plan

## Rollback

## Journal
