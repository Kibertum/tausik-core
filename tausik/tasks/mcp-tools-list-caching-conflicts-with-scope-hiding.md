---
slug: mcp-tools-list-caching-conflicts-with-scope-hiding
title: "Кэшируемый tools/list против скрытия инструментов по scope: клиент покажет поверхность, которой уже нет"
status: planning
epic: landscape-2026-h2
story: l26-narrative
complexity: medium
role: backend
stack: null
tier: moderate
call_budget: 40
defect_of: null
scope: null
scope_exclude: "requirements.txt — апгрейд mcp SDK отдельной задачей, когда выйдет stable"
relevant_files: []
scope_paths:
  - "harness/**"
  - "scripts/*.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Состав tools/list и правила его кэширования согласованы: клиент не может показать поверхность инструментов, которая уже сменилась, и ни одна деградация из-за этого не проходит молча.

## Acceptance Criteria

1. Ревизия MCP 2026-07-28 разобрана по официальному changelog, а не по пересказу: перечислено, что удалено (initialize/initialized, Mcp-Session-Id), что стало обязательным (server/discover, resultType, ttlMs+cacheScope в tools/list) и что депрекировано (Roots, Sampling, Logging, HTTP+SSE, окно 12 месяцев).
2. Названо, что у нас НЕ ломается сегодня и почему: клиент обязан трактовать ответ без resultType как complete, server/discover определён как compat-probe для stdio, Roots/Sampling/Logging мы не используем. Вывод «ничего не горит» подтверждён проверкой, а не надеждой.
3. Конфликт закрыт по существу: на tools/list отдаётся ttlMs=0 (или минимальный) и cacheScope=private, ЛИБО динамическое скрытие инструментов по scope_tools снимается. Выбор зафиксирован tausik decide с причиной, а не оставлен в коде молча.
4. Пин protocolVersion 2024-11-05 в tests/test_mcp_integration.py:119 либо обновлён, либо ЯВНО помечен как тест легаси-пути; молчаливое превращение основного теста в легаси ЗАПРЕЩЕНО.
5. НЕГАТИВНЫЙ сценарий: тест доказывает, что при смене scope активной задачи клиент НЕ может получить устаревший список — либо потому что кэш запрещён, либо потому что список больше не зависит от scope. Утверждение проверяется прогоном, а не чтением конфига.
6. НЕГАТИВНЫЙ сценарий: апгрейд SDK линейки 2026-07-28 в этой задаче НЕ выполняется — SDK в бете, окно деприкации 12 месяцев. Прыжок на бету считается выходом за область.

## Plan

## Rollback

git revert коммита; ttlMs возвращается к прежнему значению, решение о скрытии отменяется отдельной записью

## Journal
