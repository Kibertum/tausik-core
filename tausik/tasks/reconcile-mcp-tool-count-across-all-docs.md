---
slug: reconcile-mcp-tool-count-across-all-docs
title: "Reconcile MCP tool count across all docs"
status: done
epic: null
story: null
complexity: null
role: tech-writer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "docs/en/mcp.md"
  - "docs/ru/mcp.md"
  - "docs/en/senar-compliance-matrix.md"
  - "docs/ru/senar-compliance-matrix.md"
  - "docs/README.md"
  - README.md
  - README.ru.md
  - AGENTS.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-07T20:15:28Z"
---

## Goal

Audit actual MCP tool count (project: tools.py+tools_extra.py, RAG: server.py), fix all references in README EN+RU, CLAUDE.md, docs/en/mcp.md, docs/ru/mcp.md, AGENTS.md, senar-compliance-matrix EN+RU to use one consistent number

## Acceptance Criteria

1. All docs reference 73 MCP tools (68 project + 5 RAG)
2. Zero inconsistencies across README, CLAUDE.md, docs, AGENTS.md
3. Negative: grep for '72 tool' or '72 инструмент' or '67 project' returns 0 matches (no stale counts remain)

## Plan

## Rollback

## Journal

- 2026-04-07T20:14:15Z [implementation] — AC verified: 1) All 17 references now say 73 (68+5) 2) grep for '72 tool|72 инструмент|67 project' = 0 results 3) Actual count confirmed: tools.py=54, tools_extra.py=14 (68 total project), RAG server.py=5 → 73
