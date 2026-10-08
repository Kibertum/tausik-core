---
slug: mcp-rag-server-rename-for-mypy-scope
title: "Переименовать codebase-rag/server.py: коллизия имён держит пакет вне области mypy"
status: done
epic: release-110-deferred-from-19
story: release110-site-docs-and-hygiene
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 55
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "harness/claude/mcp/codebase-rag/rag_server.py"
  - "harness/claude/mcp/codebase-rag/server.py"
  - "harness/claude/mcp/codebase-rag/rag_handlers.py"
  - "harness/claude/mcp/codebase-rag/rag_tools.py"
  - "bootstrap/bootstrap_codex_mcp.py"
  - "bootstrap/bootstrap_kilo.py"
  - "bootstrap/bootstrap_opencode.py"
  - "bootstrap/bootstrap_generate.py"
  - "bootstrap/bootstrap_qwen.py"
  - "scripts/hooks/session_start.py"
  - pyproject.toml
  - "tests/test_mypy_clean.py"
  - "tests/test_rag_tool_surface_parity.py"
  - "tests/test_rag_reindex_hang.py"
  - "tests/test_bootstrap_qwen.py"
  - "tests/test_bootstrap_generate_mcp.py"
  - "tests/test_opencode_bootstrap.py"
scope_paths:
  - "harness/claude/mcp/codebase-rag/*"
  - "bootstrap/*.py"
  - "scripts/hooks/session_start.py"
  - "scripts/hooks/pre-commit"
  - "scripts/mcp_tool_counts.py"
  - pyproject.toml
  - "tests/*.py"
  - "docs/en/*.md"
  - "docs/ru/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T23:35:53Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#72"
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

- 2026-09-23T23:34:47Z [implementation] — AC1: ✓ measurement — harness/claude/mcp/codebase-rag/server.py renamed to rag_server.py; 'mypy scripts harness/claude/mcp/project harness/claude/mcp/codebase-rag' runs to the end: Success, no issues found in 471 source files (no Duplicate module).
- 2026-09-23T23:34:47Z [implementation] — AC2: ✓ tests/test_mypy_clean.py::test_declared_tree_is_mypy_clean — codebase-rag added to [tool.mypy] files, the collision comment rewritten to history; zero errors, and the two import-not-found of session #177 no longer occur, so no new override was needed.
- 2026-09-23T23:34:48Z [implementation] — AC3: ✓ tests/test_mypy_clean.py::test_declared_scope_covers_the_agent_facing_mcp_package — reads [tool.mypy] files through tomllib (not a grep, so a commented-out entry cannot count) and requires both MCP packages.
- 2026-09-23T23:34:48Z [implementation] — AC4: ✓ measurement — bootstrap_{codex_mcp,kilo,opencode,generate,qwen}.py, scripts/hooks/session_start.py (3 probes), scripts/hooks/pre-commit and docs/en/environment.md point at rag_server.py; after bootstrap.py --ide all, .mcp.json / .cursor/mcp.json / .qwen/settings.json name .../codebase-rag/rag_server.py and .claude/mcp/codebase-rag holds rag_server.py with no server.py; '.tausik/venv/Scripts/python.exe .claude/mcp/codebase-rag/rag_server.py --project . < /dev/null' exits rc=0 with 0 bytes of stderr.
- 2026-09-23T23:34:48Z [implementation] — AC5: ✓ measurement — negative: git grep over bootstrap scripts harness tests docs .github .gitlab-ci.yml finds no codebase-rag/server.py launch reference; the remaining mentions are CHANGELOG history, tausik/tasks projections and one docstring saying the module WAS split.
- 2026-09-23T23:34:48Z [implementation] — AC6: ✓ tests/test_rag_tool_surface_parity.py::test_server_keeps_its_entrypoint — negative, reads rag_server.py now and finds the __main__ guard.
- 2026-09-23T23:34:49Z [implementation] — AC7: ✓ measurement — 448+41 bootstrap/rag/mypy/session_start/host tests pass after fixing three fixtures that created codebase-rag/server.py (test_bootstrap_generate_mcp, test_bootstrap_qwen, test_opencode_bootstrap); ruff clean; CHANGELOG EN/RU with the re-run-bootstrap note. docs/ru/environment.md never had these rows (pair drift, task doc-language-pairs-have-drifted-and-three-are-unpaired).
