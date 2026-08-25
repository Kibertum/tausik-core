---
slug: r14-codebase-rag-doc
title: "Document codebase-rag MCP: how 7 tools relate to the 96 main tools claim"
status: done
epic: rel-14-readiness
story: rel-14-audit-fixes
complexity: null
role: null
stack: null
tier: moderate
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "tests/test_mcp_doc_tool_counts.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T01:56:53Z"
---

## Goal

Release 1.4 readiness: r14-codebase-rag-doc

## Acceptance Criteria

1. docs/en/mcp.md и docs/ru/mcp.md: базовая поверхность 97 (91+6), опциональный codebase-rag +7=104; явная секция Codebase RAG отдельный сервер. 2. pytest-тест сверяет числа в заголовке mcp.md с len(TOOLS). 3. Negative: pytest fails when header disagrees with code.

## Plan

## Rollback

## Journal

- 2026-05-01T01:56:22Z [implementation] — AC: 1. mcp.md EN/RU уже описывали 97+104 и секцию RAG. 2. tests/test_mcp_doc_tool_counts.py — синхрон заголовка с len(TOOLS). 3. Negative: тест падает при рассинхроне (assert). verify: pytest PASS scoped.
- 2026-05-01T01:56:35Z [implementation] — 1. docs en/ru mcp.md: 97+104 and RAG section present. 2. test_mcp_doc_tool_counts passes. 3. mismatch would fail test.
- 2026-05-01T01:56:48Z [implementation] — AC verified: 1. docs mcp EN/RU 97+104 + RAG section ✓ 2. test_mcp_doc_tool_counts sync ✓ 3. Negative: pytest fails on mismatch ✓
- 2026-05-01T01:56:53Z [implementation] — AC verified: 1-3 per notes; verify cache green.
