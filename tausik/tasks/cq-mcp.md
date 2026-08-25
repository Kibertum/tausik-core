---
slug: cq-mcp
title: "cq MCP server: query before task, publish dead ends"
status: done
epic: frai-v27
story: cq-integration
complexity: complex
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
completed_at: "2026-03-29T11:58:03Z"
---

## Goal

MCP server для cq: query знаний перед задачей, publish dead ends и patterns после задачи

## Acceptance Criteria

1. MCP tool frai_cq_query: поиск по cq базе перед началом задачи. 2. MCP tool frai_cq_publish: публикация dead end или pattern в cq. 3. /go и /task автоматически делают cq query по теме задачи. 4. cq_config в .frai/config.json (endpoint, api_key, org_id). 5. Graceful degradation: если cq недоступен — warning, не блокировка. 6. Тесты с mock cq server.

## Plan

## Rollback

## Journal
