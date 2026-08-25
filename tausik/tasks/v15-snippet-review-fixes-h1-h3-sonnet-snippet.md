---
slug: v15-snippet-review-fixes-h1-h3-sonnet-snippet
title: "v15-snippet-review-fixes: H1/H3 + тест-баг из Sonnet-ревью snippet-эпика"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "harness/claude/mcp/project/handlers.py, harness/cursor/mcp/project/handlers.py, scripts/project_cli_snippet.py, tests/test_snippet_mcp_search.py, tests/test_snippet_brain_extract.py, README.md, docs/_generated/constants.json"
scope_exclude: null
relevant_files:
  - "harness/claude/mcp/project/handlers.py"
  - "harness/cursor/mcp/project/handlers.py"
  - "scripts/project_cli_snippet.py"
  - "tests/test_snippet_mcp_search.py"
  - "tests/test_snippet_brain_extract.py"
  - README.md
  - "docs/_generated/constants.json"
scope_paths:
  - "harness/claude/mcp/project/handlers.py"
  - "harness/cursor/mcp/project/handlers.py"
  - "scripts/project_cli_snippet.py"
  - "tests/*"
  - README.md
  - "docs/_generated/constants.json"
scope_tools: []
depends_on: []
completed_at: "2026-06-14T16:06:45Z"
---

## Goal

Исправить находки Sonnet-ревью v15-snippet-system: H1 — безопасная коэрция limit в MCP _do_snippet_search (нечисловой limit не валит tool, оба mirror'а claude+cursor); H3 — обернуть open_brain_deps/store_record в try/except в _cmd_snippet_extract (дружелюбное сообщение вместо traceback); test-bug — заменить всегда-истинный assert '== [] or True' на реальную проверку отсутствия исключения. H2 — не баг (format_store_result уже различает статусы).

## Acceptance Criteria

1. _do_snippet_search безопасно коэрсит limit: нечисловой/мусорный limit ("many", None, "") -> дефолт 20 без исключения; идентично в harness/claude и harness/cursor. 2. _cmd_snippet_extract оборачивает open_brain_deps()+store_record() в try/except -> печатает 'Brain error: ...' в stderr и return, без traceback. 3. Тест-багфикс: test_fts_operator_chars_do_not_raise проверяет реально (result — list, исключение не всплывает), без 'or True'. 4. Негативный/ошибочный ввод: limit='many' -> envelope count берётся из дефолта без краша (тест); open_brain_deps бросает -> сообщение, не traceback (тест). 5. pytest зелёный; claude/cursor handlers байт-в-байт идентичны.

## Plan

## Rollback

git revert — точечные правки в 2 mirror handlers + project_cli_snippet.py + 1 тест

## Journal

- 2026-06-14T16:06:45Z [implementation] — AC verified: 1. ✓ _do_snippet_search safe limit coercion (bool/int/float/numeric-str -> int, else default 20) in claude+cursor mirrors — tests/test_snippet_mcp_search.py::test_handler_non_numeric_limit_does_not_crash (many/''/None/True/'12abc' all -> count=1) 2. ✓ _cmd_snippet_extract wraps open_brain_deps()+store_record() in try/except -> 'Brain error: ...' to stderr, return — tests/test_snippet_brain_extract.py::test_open_brain_deps_raises_friendly_message 3. ✓ test_fts_operator_chars_do_not_raise rewritten: result=search(...); assert isinstance(result,list) — no more always-true 'or True' 4. ✓ Negative: junk limit -> default no crash (test above); open_brain_deps raises -> message not traceback (test above) 5. ✓ pytest 21 snippet tests green; verify gate (mypy+pytest) pass; claude/cursor handlers.py byte-identical (cp + diff); doc-constants 4172 in sync. H2 confirmed non-issue: brain_store_format.format_store_result already prefixes every failure status distinctly
