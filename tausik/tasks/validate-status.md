---
slug: validate-status
title: "Валидация status в task_list и других queries"
status: done
epic: frai-maturity
story: security
complexity: simple
role: developer
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
completed_at: "2026-03-14T11:45:45Z"
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

task_list(status) не валидирует значение — можно передать произвольную строку в SQL. Добавить whitelist валидацию для всех status-параметров.

## Acceptance Criteria

## Plan

## Rollback

## Journal
