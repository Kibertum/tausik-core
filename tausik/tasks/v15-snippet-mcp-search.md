---
slug: v15-snippet-mcp-search
title: "[1.5] MCP tausik_snippet_search — semantic поиск по snippets"
status: done
epic: v15-snippet-system
story: v15-snippet-foundation
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/snippet_storage.py, harness/claude/mcp/project/tools.py, harness/claude/mcp/project/handlers.py, harness/cursor/mcp/project/tools.py, harness/cursor/mcp/project/handlers.py, tests/*, README.md, docs/_generated/constants.json"
scope_exclude: "scripts/project_cli_snippet.py (CLI detect unchanged), scripts/snippet_detect.py, .claude/ .cursor/ (bootstrap-generated)"
relevant_files:
  - "scripts/snippet_storage.py"
  - "harness/claude/mcp/project/tools.py"
  - "harness/claude/mcp/project/handlers.py"
  - "harness/cursor/mcp/project/tools.py"
  - "harness/cursor/mcp/project/handlers.py"
  - "tests/test_snippet_mcp_search.py"
  - README.md
  - README.ru.md
  - AGENTS.md
  - "docs/README.md"
  - "docs/en/mcp.md"
  - "docs/ru/mcp.md"
  - "docs/en/architecture.md"
  - "docs/ru/agent-contract.md"
  - "docs/en/senar-compliance-matrix.md"
  - "docs/ru/senar-compliance-matrix.md"
  - "docs/_generated/constants.json"
scope_paths:
  - "scripts/snippet_storage.py"
  - "harness/claude/mcp/project/tools.py"
  - "harness/claude/mcp/project/handlers.py"
  - "harness/cursor/mcp/project/tools.py"
  - "harness/cursor/mcp/project/handlers.py"
  - "tests/*"
  - README.md
  - README.ru.md
  - AGENTS.md
  - "docs/README.md"
  - "docs/en/mcp.md"
  - "docs/ru/mcp.md"
  - "docs/en/architecture.md"
  - "docs/ru/agent-contract.md"
  - "docs/en/senar-compliance-matrix.md"
  - "docs/ru/senar-compliance-matrix.md"
  - "docs/_generated/constants.json"
scope_tools: []
depends_on: []
completed_at: "2026-06-14T15:53:23Z"
---

## Goal

MCP tool tausik_snippet_search(query, language?, limit?) для агента — поиск переиспользуемых сниппетов из snippets table. FTS5 запрос + ranking (line count, occurrences, recency). Возвращает: code, source_file:line, language, occurrences. Регистрация в harness/{claude,cursor}/mcp/project/tools.py. Tests: FTS5 query, ranking, language filter, JSON envelope. Это (4/5) v15 — surface для агента над таблицей из v15-snippet-table.

## Acceptance Criteria

1. snippet_storage.search_snippets_ranked(conn, query, language?, limit?) — FTS5 MATCH + composite ranking (occurrences=fts_rank DESC, line_count DESC, recency DESC); опциональный точный language-фильтр; clamp limit [1,200]. 2. MCP tool tausik_snippet_search(query, language?, limit?) зарегистрирован в harness/claude и harness/cursor (tools.py + handlers.py), возвращает JSON envelope {query, language, count, results:[{code, source(file:lines), language, occurrences, line_count, taxonomy_kind}]}. 3. Негативный кейс (ошибочный/пустой ввод): пустой/whitespace query -> [] и envelope count=0 БЕЗ ошибки; неизвестный language -> пустой results без ошибки; FTS-операторы в query не валят запрос (phrase-quote). 4. pytest: FTS query, ranking-порядок, language-фильтр, JSON-envelope, негатив; bootstrap mirror .claude в синхроне.

## Plan

## Rollback

git revert — additive (новая storage-функция + MCP tool); удаление tausik_snippet_search из tools.py/handlers.py обоих mirror'ов возвращает прежнее поведение, схема БД не меняется

## Journal

- 2026-06-14T15:53:23Z [implementation] — AC verified: 1. ✓ snippet_storage.search_snippets_ranked(conn,query,language?,limit?): FTS5 MATCH + ORDER BY occurrences(fts_rank) DESC, line_count DESC, created_at DESC, id ASC; language filter; limit clamp [1,200] — tests/test_snippet_mcp_search.py::TestRankedSearch (ranked_by_occurrences_desc, language_filter, limit_clamped) 2. ✓ tausik_snippet_search registered in harness/claude + harness/cursor (tools.py schema + handlers.py _do_snippet_search, mirrors byte-identical); JSON envelope {query,language,count,results:[{code,source,language,occurrences,line_count,taxonomy_kind}]} — TestMcpTool::test_tool_registered_in_tools_list + test_handler_returns_json_envelope 3. ✓ Negative: empty/whitespace query -> [] count=0 no error (test_empty_query_returns_empty + test_handler_empty_query_no_error); unknown language -> [] (test_unknown_language_yields_empty); FTS operator chars phrase-quoted, no raise (test_fts_operator_chars_do_not_raise) 4. ✓ pytest tests/test_snippet_mcp_search.py 11 passed; bootstrap synced .claude MCP mirror; doc counts reconciled (124 MCP main / 117 project / 131 with-rag) across README/AGENTS/mcp.md/architecture/agent-contract/senar + test_count 4162 — test_mcp_doc_tool_counts + gen_doc_constants --check green
