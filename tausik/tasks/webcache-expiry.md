---
slug: webcache-expiry
title: "Web-cache expiration и staleness warning"
status: done
epic: release-ready
story: p1-value
complexity: simple
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/project_cli_extra.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-03-14T13:16:11Z"
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

Записи старше N дней помечаются stale. search показывает возраст записи

## Acceptance Criteria

1. web_cache_search показывает возраст (3d ago, 2w ago) | 2. Записи >30d помечаются [stale] в выводе | 3. web-cache status показывает stale count | 4. TTL настраивается через config.json

## Plan

## Rollback

## Journal
