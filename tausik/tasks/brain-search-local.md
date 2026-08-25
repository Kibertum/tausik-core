---
slug: brain-search-local
title: "brain_search_local через FTS5 (быстрый offline search)"
status: done
epic: shared-brain
story: brain-local-fts
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/brain_search.py (новый), tests/test_brain_search.py (новый)"
scope_exclude: "MCP-tool registration (это brain-mcp-tools-read, отдельная задача). CLI-команды. Не трогать brain_schema/brain_sync/brain_config/brain_notion_client."
relevant_files:
  - "scripts/brain_search.py"
  - "tests/test_brain_search.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-23T04:31:20Z"
---

## Goal

MCP tool brain_search_local: запрос к FTS5 virtual tables с ранжированием bm25. Возвращает те же нормализованные результаты что brain_search, но без сети. Используется как быстрый путь.

## Acceptance Criteria

1) scripts/brain_search.py создан: search_local(conn, query, *, categories=None, limit=20, offset=0)→list[dict]; get_by_id(conn, category, notion_page_id)→dict|None. 2) Query sanitization: обрамление в двойные кавычки + escape внутренних " → "" (FTS5 phrase-query). Спец-символы (-, :, etc) не ломают парсер. 3) Ранжирование: ORDER BY bm25(fts_table) asc (меньше = релевантнее); score в результате = числовое значение bm25. 4) Snippet: SQL snippet() по основной текстовой колонке (context для decisions, content для web_cache, description для patterns/gotchas) с маркерами [...] и truncation 64 tokens. 5) Нормализованный dict: {category, notion_page_id, name, snippet, score, tags(list), stack(list), source_project_hash, last_edited_time, url?/date?/severity?/confidence? в зависимости от категории}. 6) categories=None → все 4 категории; явный список фильтрует; пустой query или пустой список категорий → []. 7) limit/offset применяются ПОСЛЕ sort-merge всех категорий (глобальный ранжир). 8) get_by_id: точный SELECT по notion_page_id, возвращает нормализованный dict или None. 9) tests/test_brain_search.py: пустой query → []; match во всех 4 категориях; фильтр categories; limit/offset; query со спец-символами («-» «"» «:») → работает, не падает; кириллица; get_by_id hit/miss; JSON-tags/stack десериализуются. 10) Gates: pytest + ruff зелёные, <400 строк.

## Plan

## Rollback

## Journal

- 2026-04-23T04:28:29Z [implementation] — AC verified: 1. scripts/brain_search.py (193 строки): sanitize_fts_query, search_local(conn, query, *, categories, limit, offset), get_by_id(conn, category, notion_page_id) ✓ 2. Query sanitization: пустой → ""; валидный → обрамление в "…"; внутренние " → "" (test_sanitize_* 4 теста, включая test_sanitize_neutralizes_dash_and_colon для "foo-bar:baz" → '"foo-bar:baz"') ✓ 3. Ранжирование: ORDER BY bm25(fts_table) ASC + результаты сортируются по score глобально (test_search_combines_categories_sorted_by_bm25) ✓ 4. Snippet: SQL snippet(fts, col_idx, '[', ']', '...', 32) — маркеры [ ] вокруг match (test_search_snippet_marks_match) ✓ 5. Нормализованный dict: category+notion_page_id+name+snippet+score(float)+tags(list)+stack(list)+source_project_hash+last_edited_time + категория-специфичные поля: decisions→date, web_cache→url/domain/fetched_at, patterns→date/confidence, gotchas→date/severity/evidence_url (test_search_finds_decision/_web_cache/_pattern/_gotcha) ✓ 6. Фильтры: categories=None → все 4 (test_search_combines_categories); явный список (test_search_categories_filter); пустой список → [] (test_search_with_empty_categories_returns_empty); неизвестная категория — игнорируется (test_search_unknown_category_ignored) ✓ 7. limit/offset после глобального sort-merge: 5 decisions → 2+2+1 страницы покрывают все 5 уникальных id (test_search_limit_and_offset); negative → ValueError (test_search_negative_limit_raises) ✓ 8. get_by_id: hit возвращает норм. dict с score=0.0, tags/stack парсятся; miss → None; неизвестная категория → ValueError ✓ 9. tests/test_brain_search.py — 24 теста, 24/24 за 1.35s. Регресс brain-suite 102/102 ✓ 10. Gates: ruff clean, filesize 193 < 400 ✓. Кириллица (test_search_cyrillic_works: "Использовать" → 1 hit). Спец-символы (-, ", :) не ломают парсер — 3 отдельных теста ✓
