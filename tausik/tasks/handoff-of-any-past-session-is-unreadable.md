---
slug: handoff-of-any-past-session-is-unreadable
title: "Хэндофф любой сессии, кроме последней, не читается ни CLI, ни MCP"
status: planning
epic: release-19-renar-conformance
story: github-primary-gitlab-mirror
complexity: simple
role: backend
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/project_cli*.py"
  - "scripts/mcp_*.py"
  - "tests/*.py"
  - "docs/ru/cli.md"
  - "docs/en/cli.md"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

ЗАМЕР, сессия #181: session last-handoff отдаёт ТОЛЬКО свежайший хэндофф; команды session show <id> нет; session list печатает summary, но не handoff; events по entity=session несут только tool_use. Следствие измерено на живом случае: таблица разбора PR #5 была записана в хэндофф сессии #179, инструкция владельца гласила «заново не разбирать», и достать её пришлось ИЗ ТРАНСКРИПТА IDE, то есть из-за пределов фреймворка. Фреймворк, обещающий непрерывность контекста между сессиями, теряет её на глубине один. Правило AC: чтение хэндоффа по номеру сессии обязано быть в CLI и в MCP (MCP-first), и обязано быть закреплено тестом, который краснеет на сегодняшнем дереве.

## Acceptance Criteria

## Plan

## Rollback

git revert коммита; команда аддитивна, существующий last-handoff не меняется

## Journal
