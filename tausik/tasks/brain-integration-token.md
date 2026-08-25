---
slug: brain-integration-token
title: "Notion integration + shared databases + smoke-test API"
status: done
epic: shared-brain
story: brain-infra
complexity: simple
role: architect
stack: null
tier: null
call_budget: null
defect_of: null
scope: ".tausik/brain_smoke.py + .tausik/brain_research.py (ad-hoc scripts, gitignored); .tausik/brain-smoke.db (local mirror)"
scope_exclude: "Никаких изменений в scripts/brain_*.py — весь клиент/sync/search работал без правок на живом API"
relevant_files:
  - ".tausik/brain_smoke.py"
  - ".tausik/brain_research.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-23T07:36:18Z"
---

## Goal

Зарегистрировать отдельную Notion integration для brain, расшарить все 4 databases. Выполнить smoke-test: create page in each database + retrieve. Сохранить integration_token в ~/.tausik-brain/credentials (chmod 600).

## Acceptance Criteria

1) Notion integration "TAUSIK Brain" создана пользователем, токен формата ntn_* получен. 2) Integration подключена к parent page BRAIN — /v1/search возвращает её. 3) Smoke-test по всему read+write pipeline на живом API: (a) databases.create × 4, (b) pages.create × 4 с корректными properties (title/rich_text/multi_select/select/date/checkbox/url/number), (c) sync_all pull из 4 баз возвращает fetched=1/upserted=1/last_edited_time на каждую, (d) search_local находит по всем 4 категориям (urllib→decisions, Notion→web_cache+decisions, mixin→patterns, FTS5→gotchas), (e) snippet с маркерами [...] работает, (f) categories filter работает, (g) get_by_id возвращает все поля с правильно десериализованными JSON-array tags/stack, (h) sync_state.last_pull_at заполнен для всех 4, last_error=None. 4) Negative: query 'нет такого' (кириллица) → 0 hits без падения, подтверждает unicode61 tokenizer работает на живой БД. 5) Evidence в task_log.

## Plan

## Rollback

## Journal

- 2026-04-23T07:33:34Z [implementation] — AC verified: 1. Integration "TAUSIK Brain" создана пользователем, token формата ntn_* получен ✓ 2. Integration подключена к BRAIN — /v1/search → 1 object (page BRAIN, parent=workspace) ✓ 3a. databases.create × 4 — все 4 UUID получены (decisions/web_cache/patterns/gotchas) ✓ 3b. pages.create × 4 с полными properties (title, rich_text chunks, multi_select options, select name, date start, checkbox, url, number) — все прошли без ошибок ✓ 3c. sync_all вернул: decisions{fetched:1,upserted:1,last_edited_time:2026-04-23T07:28:00.000Z}, web_cache{fetched:1,upserted:1,...}, patterns{fetched:1,upserted:1,...}, gotchas{fetched:1,upserted:1,...} ✓ 3d. search_local: urllib→1 decisions, Notion→2 (web_cache+decisions, cross-category sort bm25), mixin→1 patterns, FTS5→1 gotchas, "dash trap"→1 gotchas (phrase query), architecture→2 (decisions+patterns), stdlib→1 decisions ✓ 3e. Snippet marks [...] работают: "Need HTTP client for [Notion] API.", "Dash is parsed as column qualifier in [FTS5] MATCH queries." ✓ 3f. categories=['decisions'] query='Notion' → 1 hit (decisions only, не web_cache) ✓ 3g. get_by_id decisions: name='Use urllib instead of requests', tags=['architecture','dx'], stack=['python'], date='2026-04-23' — JSON-array десериализовался ✓ 3h. sync_state: все 4 last_pull_at='2026-04-23T07:28:00.000Z', last_error=None ✓ 4. Negative: query='нет такого' (кириллица) → 0 hits без падения — unicode61 на живой БД работает ✓ 5. SECURITY: токен хранился только в env var NOTION_TAUSIK_TOKEN на время процесса; .tausik/brain_smoke.py + brain_research.py используют os.environ.get и не содержат literal токена; .tausik/ в gitignore; token НЕ попал в config.json/CHANGELOG/README/docs/commits. В .tausik/brain-smoke.db только ссылки notion_page_id (UUID), не токен ✓ 6. Notion сам нормализует em-dash в titles ("Notion API — create page") — косметика, не баг sync
