---
slug: v2-mcp-request-time-db-routing
title: "[2.0] MCP: resolution БД spawn-time → request-time (пул коннектов по project-root)"
status: planning
epic: v2-global-mcp
story: v2gm-core
complexity: complex
role: architect
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
resolution: null
resolution_reason: null
tracker_refs:
  - "github#37"
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

Сделать один демон systemwide: сервер держит пул SQLite-коннектов по project-root, каждый tool-call несёт/выводит корень. Сейчас server.py пинит --project + os.chdir() один раз при спавне, db_path резолвится единожды — один сервер навсегда привязан к одному проекту. Исследование (tausik_systemwide_analysis.md) ошибочно считает resolution per-cwd; этот разрыв = ядро 2.0. Связано с decision #94.

## Acceptance Criteria

## Plan

## Rollback

## Journal
