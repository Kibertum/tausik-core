---
slug: v14-agents-test-discipline
title: "AGENTS.md: короткий чеклист дисциплины тестов агента"
status: done
epic: v14-test-philosophy
story: v14-test-agent-rules
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
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T17:23:11Z"
---

## Goal

Исключения для security-sensitive путей.

## Acceptance Criteria

1. Блок в AGENTS.md. 2. Ссылка на docs. 3. Negative: security paths не попадают под «не пиши тесты».

## Plan

## Rollback

## Journal

- 2026-05-01T17:23:06Z [implementation] — AC verified: 1. Секция «Testing discipline (agents)» в AGENTS.md с чеклистом. 2. Ссылка на docs/en и docs/ru testing-principles в тексте и в таблице Documentation Map. 3. Negative: для hooks/auth/billing явно сказано — не освобождение от тестов, а более строгая дисциплина.
