---
slug: mcp-win-tests
title: "MCP integration tests для Windows"
status: done
epic: improvements-v2
story: testing-dx
complexity: medium
role: qa
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
completed_at: "2026-03-19T09:44:48Z"
---

## Goal

Написать integration tests для MCP серверов покрывающие Windows-специфичные баги

## Acceptance Criteria

Написаны тесты покрывающие: subprocess hang, async context manager, path resolution. Все проходят на Windows.

## Plan

[{"step": "\u041e\u043f\u0440\u0435\u0434\u0435\u043b\u0438\u0442\u044c Windows-\u0441\u043f\u0435\u0446\u0438\u0444\u0438\u0447\u043d\u044b\u0435 \u0441\u0446\u0435\u043d\u0430\u0440\u0438\u0438 \u0438\u0437 \u0430\u043d\u0430\u043b\u0438\u0437\u0430 \u0431\u0430\u0433\u043e\u0432", "done": true}, {"step": "\u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c pytest \u0442\u0435\u0441\u0442\u044b \u0434\u043b\u044f MCP \u0441\u0435\u0440\u0432\u0435\u0440\u043e\u0432 (subprocess, async, paths)", "done": true}, {"step": "\u0423\u0431\u0435\u0434\u0438\u0442\u044c\u0441\u044f \u0447\u0442\u043e \u0442\u0435\u0441\u0442\u044b \u043f\u0440\u043e\u0445\u043e\u0434\u044f\u0442 \u043d\u0430 Windows", "done": true}]

## Rollback

## Journal
