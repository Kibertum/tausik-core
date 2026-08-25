---
slug: brain-db-schema
title: "Спроектировать Notion databases: decisions, web_cache, patterns, gotchas"
status: done
epic: shared-brain
story: brain-infra
complexity: medium
role: architect
stack: null
tier: null
call_budget: null
defect_of: null
scope: "references/brain-db-schema.md (новый design-doc, markdown)"
scope_exclude: "scripts/**, .tausik/**, .claude/** — эта задача design-only, никакого Python кода"
relevant_files:
  - "references/brain-db-schema.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-22T23:49:02Z"
---

## Goal

Спроектировать 4 databases с properties: decisions (title, context, decision, rationale, tags, date, source_project_hash), web_cache (url, query, content, fetched_at, ttl, domain), patterns (name, description, when_to_use, example, tags), gotchas (title, description, wrong_way, right_way, tags). source_project_hash — SHA256(project_name) для приватности идентификации без раскрытия имени.

## Acceptance Criteria

1) Создан design-doc `references/brain-db-schema.md` с полной спецификацией 4 Notion databases: decisions, web_cache, patterns, gotchas. 2) Для каждой базы перечислены все properties с Notion-типами (title/rich_text/select/multi_select/date/number/url/checkbox), обязательность, defaults. 3) Задокументирована формула `source_project_hash = SHA256(project_name)[:16]` и её privacy-назначение. 4) Для каждой базы приведён пример JSON-payload для `pages.create` API (полный, валидный, с реальным properties-object). 5) Описаны индексы/sort-приоритеты и поля для дельта-pull (`last_edited_time`). 6) Раздел Trade-offs: рассмотрены альтернативы (flat-bag vs многотабличное, tags vs categories), negative-сценарии (overflow в rich_text, rate-limit при массовом pull). 7) Negative scenario: что делать, если integration не имеет доступа к БД — документировано. 8) Evidence в task-logs: ссылка на коммит + короткая выжимка ключевых решений.

## Plan

## Rollback

## Journal

- 2026-04-22T23:43:01Z [implementation] — Старт design-работы. Подход: создать references/brain-db-schema.md, 4 базы (decisions, web_cache, patterns, gotchas) + общее определение privacy-hash. Сверюсь со стилем существующих references/*.md и project_backend.py memory schema как референс для полей patterns/gotchas.
- 2026-04-22T23:45:54Z [implementation] — Evidence AC-verify: references/brain-db-schema.md создан (315 строк). Покрытие AC: (1) файл есть; (2) все 4 базы с таблицей properties, Notion-типами и обязательностью; (3) формула SHA256(name)[:16] задокументирована в §2 Privacy; (4) JSON payload для каждой из 4 баз, валидный для POST /v1/pages; (5) §5 Delta-pull (last_edited_time asc, sync_state high-water mark) + §6 Pagination/rate-limit; (6) §7 Trade-offs с 7 решениями; (7) §8 Negative scenarios (8 сценариев, включая «integration без доступа → disable brain + fallback local-FTS»). §9 явно фиксирует out-of-scope для v1.
- 2026-04-22T23:46:15Z [implementation] — AC verified: 1. references/brain-db-schema.md создан (315 строк) ✓ 2. Все 4 базы (decisions/web_cache/patterns/gotchas) с таблицей properties: Notion-тип, обязательность, назначение ✓ 3. Формула source_project_hash = SHA256(project_name_canonical)[:16] задокументирована в §2 Privacy с rationale ✓ 4. JSON payload для pages.create приведён по каждой из 4 баз — валидные properties-objects ✓ 5. §5 фиксирует last_edited_time asc + sync_state high-water mark; §6 — throttle 350ms + 429-backoff ✓ 6. §7 Trade-offs: 7 решений с альтернативами (4 vs 1 база, multi_select vs relation, rich_text chunks vs child-blocks, hash vs plaintext, Content Hash, Confidence select, Generalizable checkbox) ✓ 7. §8 Negative scenarios: integration без доступа → disable + fallback local-FTS ✓ 8. Evidence: файл references/brain-db-schema.md + 3 decision-записи (#30 4-db split, #31 SHA256 privacy, #32 Content Hash dedup) ✓
