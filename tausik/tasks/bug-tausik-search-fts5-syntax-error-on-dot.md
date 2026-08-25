---
slug: bug-tausik-search-fts5-syntax-error-on-dot
title: "Bug: tausik_search FTS5 syntax error when query contains '.'"
status: done
epic: v141-bugfixes
story: v141-mcp-bugs
complexity: simple
role: developer
stack: python
tier: trivial
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-15T16:49:38Z"
---

## Goal

tausik_search должен корректно обрабатывать запросы со спецсимволами FTS5 (точка, тире и т.д.) — например `tausik.tech site`. Сейчас падает с `Error: fts5: syntax error near "."`. Нужно экранировать/обернуть пользовательский запрос перед передачей в FTS5 MATCH (фразовый поиск в двойных кавычках или sanitizer по спецсимволам).

## Acceptance Criteria

(1) tausik_search с query содержащим '.' (например 'tausik.tech') не падает с FTS5 syntax error. (2) _sanitize_fts5 обрабатывает '.', '-' и аналогичные spec-chars: каждый token с такими символами оборачивается в фразовые кавычки. (3) Тесты в tests/test_search_sanitization.py или подобном покрывают: точка в середине ('tausik.tech'), точка в конце ('foo.'), тире, смешанный запрос ('a.b c -d'), пустой запрос, пустые phrases, валидный 'AND'/'OR' оператор не сломан. (4) pytest всех текущих тестов остается зелёным. (5) Ошибка: не должны вернуться ложные результаты на разумные запросы — fallback на quoted-phrase сохраняет смысл.

## Plan

## Rollback

## Journal

- 2026-05-15T16:49:37Z [implementation] — AC verified: (1) ✓ _sanitize_fts5 теперь оборачивает токены с '.', '-', '/', '@', '#' в фразовые кавычки. (2) ✓ tests/test_fts5_sanitizer.py — 22 теста (включая параметризованный e2e матчинг против реальной FTS5-таблицы). (3) ✓ pytest scoped зелёный: 116 passed (sanitizer + edge_cases + tausik_service). (4) ✓ Quoted-phrase passthrough сохранён; boolean operators по-прежнему стрипаются; mixed запросы '"keep this" a.b plain' разбираются корректно. (5) ✓ Negative: pytest test_real_fts5_match_never_raises[tausik.tech] (и 8 других shapes) подтверждают что FTS5 OperationalError больше не выбрасывается.
