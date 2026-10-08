---
slug: sibling-mcp-servers-still-drop-unknown-arguments
title: "Два соседних MCP-сервера по-прежнему принимают необъявленный параметр молча"
status: done
epic: release-110-deferred-from-19
story: release110-open-defects
complexity: medium
role: developer
stack: python
tier: substantial
call_budget: 80
defect_of: mcp-server-drops-unknown-arguments-silently
scope: null
scope_exclude: null
relevant_files:
  - "scripts/mcp_arguments.py"
  - "harness/claude/mcp/project/server.py"
  - "harness/claude/mcp/codebase-rag/rag_server.py"
  - "tests/test_mcp_unknown_arguments.py"
  - "tests/test_rag_server_refuses_unknown_arguments.py"
scope_paths:
  - "scripts/mcp_arguments.py"
  - "harness/claude/mcp/project/server.py"
  - "harness/claude/mcp/codebase-rag/rag_server.py"
  - "tests/*.py"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T23:40:47Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#141"
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

НАЙДЕНО ПОПУТНО в mcp-server-drops-unknown-arguments-silently, замер сессии #182. Тот дефект чинился в tausik-project и там закрыт. Но серверов у нас ТРИ, и у двух других сверки аргументов нет вовсе:

1. harness/claude/mcp/brain/server.py:87 — call_tool сразу зовёт handle_tool(name, arguments). 12 инструментов. Хуже соседа вдвойне: в его ответе об ошибке нет и usage-подсказки — она есть только у project (_usage_hint). Агент, ошибшийся именем параметра у brain, не получает ни отказа, ни намёка.
2. harness/claude/mcp/codebase-rag/server.py:102 — call_tool зовёт call_tool_sync(name, arguments, project_dir) через wait_for. Схемы отдаёт rag_tools.tool_definitions().

ЦЕНА ТА ЖЕ И УЖЕ ИЗВЕСТНА: у project опечатка в имени параметра выглядела как успех и породила семь задач без истории, невидимых для roadmap. Здесь тот же механизм и та же тишина, разница только в том, что цену ещё не предъявили.

ЧТО СДЕЛАТЬ: перенести устройство, а не переписать его. В project это declared_arguments (единственный разворот схемы) + reject_unknown_arguments (ValueError с именем лишнего ключа и близким объявленным) + _error_reply (одна форма отказа), страж стоит в call_tool ДО обработчика и вне его try. Вопрос, который задача обязана задать ДО кода: живёт ли это общим модулем на три сервера или копией в каждом. Копия в трёх местах — ровно тот второй перечень имён, который AC4 исходной задачи запрещал внутри одного сервера.

ЧТО НЕ ДЕЛАТЬ: не расширять на проверку типов и диапазонов объявленных значений — граница дефекта та же, что у исходной задачи, и она измерена.

ЗАМЕР, КОТОРЫЙ НАДО ПОВТОРИТЬ ЗДЕСЬ ДО ПРАВКИ: у project разбор AST показал ноль обработчиков, читающих ключ вне своей схемы (119 из 119). Для brain и codebase-rag это НЕ проверено, а без этого сверка со схемой может сломать законный вызов.

## Acceptance Criteria

1. Measured before the change: the brain server no longer exists (removed with the Notion transport), so codebase-rag is the one sibling left; every key its handlers read from arguments is declared by its schema (no legitimate call can be refused). 2. The guard lives ONCE, in scripts/mcp_arguments.py (declared_arguments, usage_hint, error_reply, reject_unknown_arguments); the project server imports it instead of defining it, and the rag server calls it before its handler, outside the handler's try. 3. NEGATIVE: a call to a rag tool with an undeclared argument (e.g. search_code with 'qurey') is refused with the name, the nearest declared name and the usage line — and a correct call still reaches the handler. 4. NEGATIVE: the project server's behaviour is unchanged — its existing unknown-argument tests stay green; the rule accepts both dict schemas and mcp Tool objects.

## Plan

## Rollback

git revert; the guard moves back into the project server

## Journal

- 2026-09-23T23:40:06Z [implementation] — AC-1: ✓ measurement — harness/claude/mcp has project and codebase-rag only (brain removed with the Notion transport); every key the rag handlers read from arguments (query, limit, scope, mode, max_seconds, older_than_days, ttl_hours, url, content) is declared by rag_tools.tool_definitions(), so the guard cannot refuse a legitimate call.
- 2026-09-23T23:40:06Z [implementation] — AC-2: ✓ tests/test_mcp_unknown_arguments.py::test_no_server_keeps_its_own_copy_of_the_guard and tests/test_mcp_unknown_arguments.py::test_the_usage_line_and_the_guard_read_the_same_unfolding — scripts/mcp_arguments.py holds declared_arguments/usage_hint/error_reply/reject_unknown_arguments; both servers import it; the rag call_tool checks before the handler and outside its try.
- 2026-09-23T23:40:06Z [implementation] — Root cause: the argument guard was written inside harness/claude/mcp/project/server.py only; the rag server's call_tool handed arguments straight to call_tool_sync, and its schemas do not set additionalProperties:false, so the MCP SDK's own validation (which does enforce 'required') let an extra key through.
- 2026-09-23T23:40:07Z [implementation] — AC-3: ✓ tests/test_rag_server_refuses_unknown_arguments.py::test_an_undeclared_argument_is_refused_by_name and tests/test_rag_server_refuses_unknown_arguments.py::test_a_declared_call_still_reaches_the_handler — negative, real stdio JSON-RPC against the real server process; mutation (guard call replaced by pass) turned the refusal test red: 1 failed, 1 passed; restored.
- 2026-09-23T23:40:07Z [implementation] — AC-4: ✓ tests/test_mcp_unknown_arguments.py::test_the_live_case_that_created_the_orphans_is_now_refused — negative, project server unchanged: 193 tests across test_mcp_project_server, test_mcp_unknown_arguments, test_self_correcting_cli and the rag suites pass; mypy clean over 472 files; the shared helper reads dict schemas and mcp Tool objects alike.
- 2026-09-23T23:40:32Z [implementation] — NO-DEAD-END: the two red runs were the test's own first draft (SDK 'required' check answered before the guard; stdin EOF shut the server before the handler replied), corrected in the test, not a wrong approach to the fix.
