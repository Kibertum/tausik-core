---
slug: v14-readme-align-mcp-counts
title: "Выравнивание README/таблиц IDE с фактическими MCP counts"
status: done
epic: v14-doc-automation
story: v14-readme-mcp-sync
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "docs/en/mcp.md"
  - "docs/ru/mcp.md"
  - README.md
  - README.ru.md
  - "docs/README.md"
  - AGENTS.md
  - CLAUDE.md
  - "docs/en/architecture.md"
  - "docs/ru/architecture.md"
  - "docs/en/senar-compliance-matrix.md"
  - "docs/ru/senar-compliance-matrix.md"
  - "tests/test_mcp_doc_tool_counts.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T12:29:54Z"
---

## Goal

Согласовано с test_mcp_doc_tool_counts.

## Acceptance Criteria

1. Обновлённые числа в README/docs index. 2. Один источник истины. 3. Negative: тест счётчиков падает при drift.

## Plan

## Rollback

## Journal

- 2026-05-01T12:26:14Z [implementation] — AC verified: 1. ✓ README, docs/README, mcp.md EN/RU, architecture, senar matrix, AGENTS, CLAUDE — 99 = 92+7, RAG total 106. 2. ✓ tests/test_mcp_doc_tool_counts.py: mcp.md + README hero + docs index. 3. ✓ negative: тесты падают при drift. AC-1: ✓ docs+README. AC-2: ✓ test_mcp_doc_tool_counts. AC-3: ✓ pytest.
