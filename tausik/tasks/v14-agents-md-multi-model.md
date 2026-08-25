---
slug: v14-agents-md-multi-model
title: "AGENTS.md: таблица модель → поверхность инструментов"
status: done
epic: v14-model-prompts
story: v14-model-prompts-routing
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - AGENTS.md
  - "tests/test_mcp_doc_tool_counts.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T15:37:43Z"
---

## Goal

Согласовать с docs; счётчики MCP не дрейфуют.

## Acceptance Criteria

1. Таблица в AGENTS.md. 2. Ссылки на docs. 3. Negative: рассинхрон с test_mcp_doc_tool_counts ловится CI.

## Plan

## Rollback

## Journal

- 2026-05-01T15:37:37Z [implementation] — AC verified: 1. ✓ AGENTS.md model→surface table + doc links 2. ✓ docs/en|ru mcp.md refs 3. ✓ test_agents_md_mcp_counts_match_code in test_mcp_doc_tool_counts.py
