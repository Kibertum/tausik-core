---
slug: mcp-rag-server-rename-for-mypy-scope
title: "Переименовать codebase-rag/server.py: коллизия имён держит пакет вне области mypy"
status: planning
epic: arch-debt-post-18
story: adp18-module-boundaries
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 55
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Замерено в задаче mcp-rag-server-module-split, а не предположено. Комментарий в pyproject.toml обещал, что разрез модуля введёт harness/claude/mcp/codebase-rag в область mypy. Разрез выполнен (server.py 562 -> 134, добавлены rag_tools.py и rag_handlers.py), а коллизия ОСТАЛАСЬ: прогон `mypy scripts harness/claude/mcp/project harness/claude/mcp/codebase-rag` по-прежнему обрывается на «Duplicate module named "server" (also at harness/claude/mcp/project/server.py)» и не проверяет НИЧЕГО. Причина в имени файла, а не в его размере. Обычные обходы неприменимы: каталог codebase-rag содержит дефис, поэтому не может быть Python-пакетом — отпадают и __init__.py, и --explicit-package-bases. При проверке в одиночку пакет почти чист: `mypy harness/claude/mcp/codebase-rag` даёт 2 ошибки, обе import-not-found для модулей (project_backend, tausik_utils), которые доезжают через sys.path в рантайме — тот же класс, что уже закрыт override'ами для соседей. Настоящий разблокиратор — переименование файла (например rag_server.py), и оно затрагивает .mcp.json, шаблоны bootstrap, доки EN+RU и развёрнутые профили пяти IDE, поэтому вынесено отдельной задачей, а не пришито к разрезу. Комментарий в pyproject.toml уже исправлен, чтобы не утверждать ложное, и указывает на эту задачу.

## Acceptance Criteria

AC1. Файл harness/claude/mcp/codebase-rag/server.py переименован так, что коллизия имён снята (имя не совпадает с harness/claude/mcp/project/server.py). Прогон `mypy scripts harness/claude/mcp/project harness/claude/mcp/codebase-rag` доходит до конца и НЕ обрывается на Duplicate module.
AC2. harness/claude/mcp/codebase-rag добавлен в [tool.mypy] files в pyproject.toml, комментарий про коллизию удалён (он перестал описывать реальность), и repo-wide прогон mypy чист — ноль ошибок. Две известные import-not-found (project_backend, tausik_utils) закрыты override'ами по образцу уже существующих для соседних модулей, а не игнорированием файла целиком.
AC3. Тест, проверяющий область mypy, читает её ИЗ КОНФИГА и требует наличия обоих MCP-пакетов (конвенция #344): расширить tests/test_mypy_clean.py::test_declared_scope_covers_the_agent_facing_mcp_package либо добавить парный тест.
AC4. Все точки запуска переставлены на новое имя и это доказано прогоном, а не поиском: .mcp.json, шаблоны bootstrap (bootstrap_*.py), .claude/.cursor/.qwen/.kilo/.opencode профили после bootstrap.py --ide all, докиs EN+RU. Сервер стартует по новому пути: `python <новый путь> --project .` завершается кодом 0 с пустым stderr.
AC5. НЕГАТИВНЫЙ: не осталось НИ ОДНОЙ ссылки на старый путь codebase-rag/server.py — проверяется grep по репозиторию, включая доки и шаблоны; иначе у части IDE сервер молча перестанет подниматься.
AC6. НЕГАТИВНЫЙ: тест tests/test_rag_tool_surface_parity.py::test_server_keeps_its_entrypoint продолжает проходить на переименованном файле (точка входа `if __name__ == "__main__"` не теряется при переносе — она уже терялась однажды при разрезе).
AC7. Гейты зелёные: ruff, mypy, pytest, filesize, bootstrap_drift. CHANGELOG.md + CHANGELOG.ru.md обновлены прозаической записью.

## Plan

## Rollback

git revert коммита задачи. Переименование файла и правки конфигов обратимы одним откатом; схема БД и данные не затрагиваются. Проверка отката: `python harness/claude/mcp/codebase-rag/server.py --project .` снова работает по старому пути, mypy возвращается к прежней области.

## Journal
