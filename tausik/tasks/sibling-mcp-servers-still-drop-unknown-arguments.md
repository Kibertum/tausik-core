---
slug: sibling-mcp-servers-still-drop-unknown-arguments
title: "Два соседних MCP-сервера по-прежнему принимают необъявленный параметр молча"
status: planning
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: substantial
call_budget: 80
defect_of: mcp-server-drops-unknown-arguments-silently
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
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

## Plan

## Rollback

## Journal
