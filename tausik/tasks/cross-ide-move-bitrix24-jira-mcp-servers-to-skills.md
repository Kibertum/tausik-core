---
slug: cross-ide-move-bitrix24-jira-mcp-servers-to-skills
title: "Cross-IDE: move bitrix24/jira MCP servers to skills repo"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "agents/claude/mcp/bitrix24/, agents/claude/mcp/jira/, agents/cursor/mcp/bitrix24/, agents/cursor/mcp/jira/, bootstrap/bootstrap.py"
scope_exclude: "scripts/, tests/, agents/*/mcp/project/"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-07T11:52:39Z"
---

## Goal

Перенести bitrix24 и jira MCP серверы из agents/claude/mcp/ в skills-official/ рядом со скиллами. Удалить из core. Обновить bootstrap_copy для нового расположения.

## Acceptance Criteria

1. bitrix24/ и jira/ MCP серверы удалены из agents/claude/mcp/ и agents/cursor/mcp/. 2. Bootstrap не ломается без этих серверов. 3. Тесты проходят. 4. Ошибка: bootstrap не падает если MCP серверы отсутствуют в agents/.

## Plan

## Rollback

## Journal

- 2026-04-07T11:51:31Z [implementation] — AC verified: 1. bitrix24/ и jira/ отсутствуют в agents/claude/mcp/ и agents/cursor/mcp/ — удалены ранее ✓ 2. Bootstrap не ссылается на bitrix24/jira (grep: 0 matches in bootstrap/) ✓ 3. 833 tests pass ✓ 4. Bootstrap не падает — MCP серверы отсутствуют без ошибок ✓
