---
slug: mcp-silence-prompts-32601
title: "MCP-серверы: отвечать на prompts/list и resources/list вместо -32601"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: "harness/claude/mcp/project/server.py, harness/claude/mcp/brain/server.py, harness/cursor/mcp/brain/server.py, tests/test_mcp_answers_prompts_list.py"
scope_exclude: "tools.py / handlers.py — набор инструментов не меняется; bootstrap-ветки IDE — отдельная задача opencode-ide-support"
relevant_files:
  - "harness/claude/mcp/project/server.py"
  - "harness/claude/mcp/brain/server.py"
  - "harness/claude/mcp/codebase-rag/server.py"
  - "harness/cursor/mcp/project/server.py"
  - "harness/cursor/mcp/brain/server.py"
  - "harness/cursor/mcp/codebase-rag/server.py"
  - "tests/test_mcp_answers_prompts_list.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-14T12:19:07Z"
---

## Goal

Убрать поток ошибок `MCP error -32601: Method not found failed to get prompts` в логах хостов, которые (как OpenCode) запрашивают prompts/list и resources/list безусловно, не глядя на объявленные capabilities. Сейчас серверы tausik-project и tausik-brain регистрируют только list_tools+call_tool, поэтому любой такой запрос отбивается как Method not found. Инструменты при этом работают, но пользователь читает лог и делает вывод «MCP TAUSIK не отвечает / сломан» — ложный диагноз, который увёл его в неверную сторону при разборе реального инцидента. Тихая ошибка наоборот: шумная НЕ-ошибка, маскирующая исправность.

## Acceptance Criteria

1. harness/claude/mcp/project/server.py и harness/claude/mcp/brain/server.py регистрируют @server.list_prompts() и @server.list_resources(), возвращающие пустой список — сервер отвечает на prompts/list и resources/list штатным пустым результатом вместо -32601. 2. То же для cursor-зеркала brain (harness/cursor/mcp/brain/server.py), если оно является отдельным исходником, а не генерируемой копией. 3. НЕГАТИВНЫЙ СЦЕНАРИЙ: тест tests/test_mcp_answers_prompts_list.py падает, если у сервера снова не окажется хендлера prompts/list или resources/list (проверять по фактической регистрации в request_handlers у mcp.server.Server, а не по grep исходника — grep не доказывает, что хендлер реально зарегистрирован). 4. Пустой список prompts не ломает существующую выдачу tools: list_tools по-прежнему возвращает полный набор TOOLS. 5. Gates зелёные: tausik verify --task mcp-silence-prompts-32601.

## Plan

## Rollback

git revert: изменения аддитивны (два новых хендлера), удаление возвращает прежнее поведение -32601 без потери функциональности инструментов.

## Journal

- 2026-07-14T12:19:07Z [implementation] — AC verified: 1. ✓ list_prompts/list_resources добавлены в harness/claude/mcp/{project,brain}/server.py. 2. ✓ РАСШИРЕНО против исходного AC: серверов оказалось шесть, а не два (claude|cursor × project|brain|codebase-rag). Починка только двух оставила бы остальные четыре сорить -32601 — поправлены все шесть. 3. ✓ НЕГАТИВНЫЙ СЦЕНАРИЙ: tests/test_mcp_answers_prompts_list.py, 10 passed. Список серверов не захардкожен (glob по harness/*/mcp/*/server.py) + test_servers_were_discovered страхует от вакуумного прохода на пустом glob. Регистрация проверяется по AST (декораторы на функциях), а не grep'ом: test_ast_guard_ignores_mentions_in_comments доказывает, что упоминание в комментарии/докстринге тест НЕ удовлетворяет. 4. ✓ test_decorator_pattern_really_registers_handlers: на живом mcp.server.Server до регистрации ListPromptsRequest/ListResourcesRequest отсутствуют в request_handlers, после — присутствуют. test_empty_prompts_do_not_suppress_the_tool_list: ListToolsRequest на месте, capabilities.{tools,prompts,resources} объявлены. 5. ✓ tausik verify --task mcp-silence-prompts-32601: passed=True, gates=[hadolint, pytest]. Domain: пустой список prompts семантически верен — TAUSIK действительно не экспортирует ни одного prompt/resource, только tools; хост получает честный пустой ответ вместо Method not found. ГРАНИЦА ЧЕСТНОСТИ: end-to-end (поднять сервер по stdio и дёрнуть prompts/list по JSON-RPC) не прогонялся — harness/-исходник не запускается напрямую, он рассчитан на разложенный bootstrap'ом .claude/. Проверено на уровне механизма SDK + структурного покрытия всех шести серверов; фактическую тишину в логе подтвердит перезапуск IDE после bootstrap.
