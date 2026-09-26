---
slug: mcp-tools-list-caching-conflicts-with-scope-hiding
title: "Кэшируемый tools/list против скрытия инструментов по scope: клиент покажет поверхность, которой уже нет"
status: done
epic: release-110-deferred-from-19
story: release110-open-defects
complexity: medium
role: backend
stack: null
tier: moderate
call_budget: 40
defect_of: null
scope: null
scope_exclude: "requirements.txt — апгрейд mcp SDK отдельной задачей, когда выйдет stable"
relevant_files:
  - "harness/claude/mcp/project/server.py"
  - "scripts/mcp_tool_scope.py"
  - "tests/test_mcp_list_cache_hint.py"
  - "tests/test_mcp_integration.py"
scope_paths:
  - "harness/**"
  - "scripts/*.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-24T08:27:34Z"
resolution: null
resolution_reason: null
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

- 2026-09-24T08:24:28Z [implementation] — AC1 source: modelcontextprotocol.io/specification/2026-07-28/changelog. Removed: initialize/notifications/initialized handshake (SEP-2575), Mcp-Session-Id + protocol sessions (SEP-2567, 'list endpoints no longer vary per-connection'), ping, logging/setLevel, roots/list_changed, SSE resumability. Required: server/discover MUST (SEP-2575), resultType on all results (SEP-2322), ttlMs+cacheScope on tools/prompts/resources list via CacheableResult (SEP-2549). Deprecated: Roots, Sampling, Logging (SEP-2577), HTTP+SSE (SEP-2596), DCR; window >= 12 months (SEP-2596).
- 2026-09-24T08:24:29Z [implementation] — AC2: nothing breaks today: SDK 1.27 speaks 2025-11-25 and earlier; clients MUST treat a result without resultType as complete (SEP-2322); server/discover is a STDIO compat probe, an unknown method is a -32601 the client falls back on; Roots/Sampling/Logging unused - held by tests/test_mcp_no_deprecated_primitives.py (memory #255).
- 2026-09-24T08:26:50Z [implementation] — Mutation: server returned the bare list (no hint) -> tests/test_mcp_list_cache_hint.py::test_a_scope_change_mid_session_is_never_served_from_a_cache red; restored.
- 2026-09-24T08:26:51Z [implementation] — AC-1: ✓ official changelog enumerated in the log above (SEP-2567/2575/2322/2549/2577/2596)
- 2026-09-24T08:26:51Z [implementation] — AC-2: ✓ tests/test_mcp_no_deprecated_primitives.py holds 'no deprecated primitives'; resultType absent = complete per SEP-2322
- 2026-09-24T08:26:51Z [implementation] — Root cause: scope hiding (mcp-scope-tools-exposure) made tools/list state-dependent before MCP 2026-07-28 added client-side caching; nothing told the client not to cache it.
- 2026-09-24T08:26:52Z [implementation] — AC-3: ✓ tests/test_mcp_list_cache_hint.py::test_a_scope_change_mid_session_is_never_served_from_a_cache asserts ttlMs 0 + cacheScope private; decision recorded
- 2026-09-24T08:26:52Z [implementation] — AC-4: ✓ tests/test_mcp_integration.py::TestMCPServerStartup::test_server_starts_and_accepts_initialize now sends mcp.types.LATEST_PROTOCOL_VERSION (pin 2024-11-05 removed)
- 2026-09-24T08:26:52Z [implementation] — AC-5: ✓ tests/test_mcp_list_cache_hint.py::test_a_scope_change_mid_session_is_never_served_from_a_cache — scope changed between two tools/list in one real stdio session: list narrower, neither cacheable
- 2026-09-24T08:26:53Z [implementation] — AC-6: ✓ requirements.txt untouched, mcp stays 1.27.0 (git diff requirements.txt empty)
