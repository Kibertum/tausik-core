---
slug: sg-scope-exclusion
title: "Scope exclusion field + QG-0 warning"
status: done
epic: senar-v13-full
story: senar-gaps
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
completed_at: "2026-03-29T11:34:25Z"
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

Scope поддерживает inclusion и exclusion. QG-0 предупреждает если scope пустой.

## Acceptance Criteria

1. --scope-exclude в task update. 2. QG-0 предупреждает если scope пустой при complexity != simple. 3. scope_exclude в tasks (migration). 4. task show отображает оба. 5. MCP принимает scope_exclude. 6. Тесты.

## Plan

## Rollback

## Journal
