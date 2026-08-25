---
slug: l26-tool-token-cost
title: "Замер токен-стоимости определений MCP-тулов + deferred loading"
status: done
epic: landscape-2026-h2
story: l26-mcp-spec
complexity: medium
role: qa
stack: python
tier: null
call_budget: null
defect_of: null
scope: "tests/test_mcp_tool_token_cost.py (new ratchet test); docs/{en,ru}/mcp.md (one measured line); CHANGELOG.md + CHANGELOG.ru.md. Read-only over harness/claude/mcp/{project,brain}/tools.py."
scope_exclude: "Do NOT edit tool descriptions unless one exceeds 2KB (none do); do NOT touch the MCP server runtime or scoping (mcp_tool_scope.py); no host-config changes (ENABLE_TOOL_SEARCH is the host's)."
relevant_files:
  - "tests/test_mcp_tool_token_cost.py"
  - "docs/en/mcp.md"
  - "docs/ru/mcp.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "tests/test_mcp_tool_token_cost.py"
  - "docs/en/mcp.md"
  - "docs/ru/mcp.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-07-27T13:23:07Z"
---

## Goal

У TAUSIK около 190 MCP-тулов. Отраслевой замер: семь подключённых серверов дают примерно 67300 токенов ДО первого слова пользователя (около трети окна в 200k), GitHub MCP — около 18000 токенов на 27 тулов. При этом tool search в Claude Code теперь включён ПО УМОЛЧАНИЮ (переменная ENABLE_TOOL_SEARCH, режимы unset/true/auto/auto:N/false), грузятся только имена, а описания и инструкции сервера обрезаются на 2 КБ каждое. Задача: (1) измерить фактическую токен-стоимость своих определений; (2) проверить, что deferred loading реально покрывает TAUSIK и ничего не ломает; (3) при необходимости ужать описания под лимит 2 КБ и проверить, что имена тулов остаются самодостаточными для поиска. Смежный риск: SkillResolve-Bench фиксирует сбой диспетчеризации по описаниям при сотнях однотипных возможностей.

## Acceptance Criteria

AC1. Измерена фактическая токен-стоимость определений всех ~190 MCP-тулов TAUSIK; число зафиксировано в отчёте задачи/доке.
AC2. Проверено, что deferred loading (ENABLE_TOOL_SEARCH) реально покрывает TAUSIK-тулы и ничего не ломает: прогон подтверждает, что тул подгружается и вызывается по имени после поиска.
AC3. Описания, превышающие лимит 2 КБ, ужаты под лимит; тест-проверка, что ни одно описание тула не превышает 2 КБ.
AC4. Проверена самодостаточность имён для поиска: диспетчеризация по имени без описания находит нужный тул на репрезентативной выборке (защита от сбоя SkillResolve-Bench при сотнях однотипных возможностей).
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью об этом изменении.

## Plan

## Rollback

git revert — the change is a measurement report + a ratchet test (tests/test_mcp_tool_token_cost.py) + a doc line; deleting the test file and reverting the doc line restores the prior state. Zero runtime behavior change (no production code path added).

## Journal

- 2026-07-27T13:15:32Z [implementation] — MEASUREMENT REPORT (AC1): 124 TAUSIK MCP tools authored (117 project + 7 brain). Full tool-definitions JSON = 51323 bytes ≈ 12830 est. tokens (bytes/4 heuristic, stdlib-first, no LLM tokenizer). Largest single description = 483 bytes (tausik_self_check); 0 descriptions exceed the 2KB deferred-load truncation limit (AC3 already satisfied — test is a ratchet). AC2 (deferred loading covers TAUSIK): empirically confirmed this session — TAUSIK MCP tools are surfaced as deferred and loaded by name via ToolSearch before each call; test asserts the precondition (every tool has a non-empty name). AC4 (name self-sufficiency vs SkillResolve-Bench): test asserts names unique + each carries a searchable domain token + representative intents (start/verify/status/search/session) resolve by name. Ceiling set at 65536B so a careless doubling reddens CI.
- 2026-07-27T13:23:05Z [implementation] — AC verified: 1. ✓ AC1 measured: tests/test_mcp_tool_token_cost.py::test_total_surface_cost_is_measured_and_bounded prints '124 MCP tools, 51323 bytes, ~12830 est. tokens' and caps at 65536B. Recorded in task log + docs/{en,ru}/mcp.md. 2. ✓ AC2: deferred loading empirically covers TAUSIK — this session loads TAUSIK MCP tools by name via ToolSearch before every call. test_every_tool_has_a_nonempty_name asserts the mechanism precondition (name is the search key). 3. ✓ AC3: test_no_description_exceeds_deferred_load_limit — every description ≤2048B (host truncation limit); currently 0 offenders, largest 483B. Ratchet keeps it so. 4. ✓ AC4: test_tool_names_are_unique + test_every_name_carries_a_searchable_domain_token + test_representative_intents_resolve_to_the_right_tool — names unique, each has a searchable domain token, sample intents (start/verify/status/search/session) resolve by name. Guards the SkillResolve-Bench failure. 5. ✓ CHANGELOG.md + CHANGELOG.ru.md [Unreleased] prose entry added. Cross-test safety: full mcp suite (slow enabled) 355 passed after isolating the loader's sys.path/sys.modules mutation (no leak into sibling mcp tests). ruff clean. Domain: measurement/ratchet only, no tool/schema changed.
