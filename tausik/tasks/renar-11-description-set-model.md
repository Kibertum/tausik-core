---
slug: renar-11-description-set-model
title: "RENAR 1.1 комплект описания: снять status/version с BR/SR/SPEC/TC, set-version N.M, QG по объектам комплекта, automation.status из двух значений, адреса утверждений <id>#n"
status: planning
epic: v2-global-mcp
story: v2-renar-11-description-set
complexity: complex
role: architect
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
completed_at: null
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

Строки guide/12 RENAR 1.1 №1, 2, 4 (set-version), 11, 12, 13, 15, 17, 21, отложенные решением #382, внедрены: артефакты требований без поартефактного статуса, версия комплекта с записью версии, QG-0/1/2 по объектам комплекта, manifest set-version; блок renar-11-deltas манифеста больше не содержит этих строк в deferred.

## Acceptance Criteria

## Plan

## Rollback

миграция схемы с обратным скриптом; манифест регенерируется

## Journal
