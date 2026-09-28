---
slug: fix-n1-roadmap
title: "Исправить N+1 запрос в roadmap"
status: done
epic: frai-maturity
story: schema-integrity
complexity: medium
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
completed_at: "2026-03-14T11:53:09Z"
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

roadmap_data() делает 511 отдельных запросов. Переписать на JOIN или batch-загрузку. Должен быть 1-3 запроса.

## Acceptance Criteria

## Plan

## Rollback

## Journal
