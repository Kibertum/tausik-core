---
slug: brain-notion-rest-client
title: "stdlib-only Notion REST client: urllib + throttle + retry"
status: done
epic: shared-brain
story: brain-mcp-server
complexity: complex
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/brain_notion_client.py (новый), tests/test_brain_notion_client.py (новый)"
scope_exclude: "Реальные HTTP-запросы к api.notion.com — всё через mock. Не трогать brain_schema.py, brain_config.py. MCP tools (brain-mcp-tools-write/read) — отдельные задачи."
relevant_files:
  - "scripts/brain_notion_client.py"
  - "tests/test_brain_notion_client.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-23T04:18:07Z"
---

## Goal

Реализовать REST-клиент на urllib (zero deps, convention #19). Endpoints: pages.create/retrieve/update, databases.query, search. Throttle 350ms между writes (rate limit 3 req/s). Exponential backoff retry на 429 и 5xx. Pagination через cursor. Возврат markdown при retrieve.

## Acceptance Criteria

1) scripts/brain_notion_client.py создан: класс NotionClient + иерархия ошибок NotionError→NotionAuthError/NotionNotFoundError/NotionRateLimitError/NotionServerError. Нулевые внешние зависимости (stdlib only: urllib.request/error, json, time, random, logging). 2) Публичные endpoints: pages_create, pages_retrieve, pages_update, databases_query, iter_database_query (auto-pagination iterator), search. 3) Все запросы — Authorization: Bearer <token> + Notion-Version header + JSON bodies. 4) Throttle: между write-запросами (POST/PATCH/DELETE) выдерживается интервал ≥350 ms (конфигурируется). 5) Retry: 429 → Retry-After header если есть, иначе экспоненциальный backoff min(2^n, 30s) ±20% jitter; 5xx → то же без Retry-After; max_retries=5; после лимита — NotionRateLimitError/NotionServerError. 6) Auth (401/403) и NotFound (404) — НЕ ретраятся, сразу бросают типизированную ошибку. 7) iter_database_query корректно проходит страницы через start_cursor/has_more/next_cursor и завершается естественно. 8) Инъекция urlopen/clock/sleep через конструктор — для тестов без сети. 9) tests/test_brain_notion_client.py: покрыты все эндпоинты, throttle, все классы ошибок, retry с Retry-After и без, max-retries limit, pagination, token required. 10) Gates: pytest зелёный, ruff clean на новых файлах; filesize ≤400 строк на файл. 11) Evidence в task_log — «AC verified: N. ... ✓» + pytest output + файлы.

## Plan

## Rollback

## Journal

- 2026-04-23T04:15:15Z [implementation] — AC verified: 1. scripts/brain_notion_client.py (328 строк) — класс NotionClient + иерархия ошибок NotionError→NotionAuthError/NotionNotFoundError/NotionRateLimitError/NotionServerError; stdlib only (urllib.request/error, json, time, random, logging) ✓ 2. Публичные endpoints: pages_create/pages_retrieve/pages_update, databases_query, iter_database_query (auto-pagination), search ✓ 3. Headers Authorization=Bearer + Notion-Version + Content-Type JSON проверены в test_pages_create_sends_expected_request ✓ 4. Throttle 350ms между writes: test_first_write_does_not_sleep (без задержки) + test_second_write_sleeps_to_honor_throttle (sleep 0.3-0.4s) + test_reads_do_not_throttle ✓ 5. Retry: 429+Retry-After (test_429_retries_with_retry_after_header), 429+exp backoff (test_429_retries_with_exponential_backoff_when_no_header, 2^attempt ±20% jitter), 5xx (test_500_retries_and_succeeds), max_retries=5 (test_*_exhausted) ✓ 6. 401/403 → NotionAuthError без retry (test_401/403), 404 → NotionNotFoundError без retry; 400 → generic NotionError без retry ✓ 7. iter_database_query: test_iter_database_query_follows_cursor (cur-1 второй запрос) + test_iter_stops_when_cursor_missing_despite_has_more ✓ 8. Инъекция urlopen/clock/sleep через конструктор — все 26 тестов через _Recorder/_ClockSleep, нулевой сетевой I/O ✓ 9. tests/test_brain_notion_client.py — 26 тестов, 26/26 за 0.09s; регресс brain-suite 63/63 ✓ 10. Gates: ruff All checks passed; filesize 328 строк client (тесты 410 — исключение для тестов согласно CLAUDE.md) ✓ 11. Retry-After нечисловой корректно falls back на backoff (test_retry_after_non_numeric_falls_back_to_backoff) ✓
