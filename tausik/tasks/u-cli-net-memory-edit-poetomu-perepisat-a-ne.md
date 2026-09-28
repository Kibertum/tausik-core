---
slug: u-cli-net-memory-edit-poetomu-perepisat-a-ne
title: "У CLI нет memory edit, поэтому «переписать, а не удалять» делается в обход"
status: planning
epic: release-110-deferred-from-19
story: release110-site-docs-and-hygiene
complexity: simple
role: null
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

Запись памяти правится командой, а не через ручную правку проекции и state import: доктрина проекта требует переписывать протухшую запись, а CLI предлагает только delete и supersede.

## Acceptance Criteria

1. tausik memory edit <id> меняет content и title, обновляет updated_at и перепроецирует файл. 2. Правка НЕ трогает created_at и id — это та же запись, а не новая. 3. НЕГАТИВНЫЙ: правка архивированной записи отказывает с внятным текстом, а не тихо оживляет её. 4. Замер: обход через проекцию плюс state import стоил 16 правок в смене #277 и трижды требовал повторного импорта.

## Plan

## Rollback

## Journal
