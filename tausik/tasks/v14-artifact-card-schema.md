---
slug: v14-artifact-card-schema
title: "JSON/schema карточки артефакта"
status: done
epic: v14-brain-snippets
story: v14-brain-snippets-model
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/brain_artifact_card.py"
  - "scripts/brain_config.py"
  - "scripts/brain_mcp_write.py"
  - "tests/test_brain_mcp_write.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T11:32:20Z"
---

## Goal

Валидируемая структура карточки для API/MCP и локального зеркала.

## Acceptance Criteria

1. JSON Schema или эквивалент в репозитории. 2. Валидация обязательных полей. 3. Negative: пустой scope вызывает ошибку валидации.

## Plan

## Rollback

## Journal

- 2026-05-01T11:32:14Z [implementation] — AC verified: 1. ✓ JSON Schema agents/schemas/brain-artifact-card.schema.json. 2. ✓ brain_artifact_card + store_record валидация scope; strippped до Notion. 3. ✓ пустой scope → card_schema_blocked; strict require_artifact_scope. pytest tests/test_brain_mcp_write.py.
