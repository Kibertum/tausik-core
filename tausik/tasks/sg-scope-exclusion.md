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
---

## Goal

Scope поддерживает inclusion и exclusion. QG-0 предупреждает если scope пустой.

## Acceptance Criteria

1. --scope-exclude в task update. 2. QG-0 предупреждает если scope пустой при complexity != simple. 3. scope_exclude в tasks (migration). 4. task show отображает оба. 5. MCP принимает scope_exclude. 6. Тесты.

## Plan

## Rollback

## Journal
