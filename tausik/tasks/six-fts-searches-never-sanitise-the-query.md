---
slug: six-fts-searches-never-sanitise-the-query
title: "Шесть поисков по FTS отказывают на обычном запросе с дефисом"
status: done
epic: release-110-deferred-from-19
story: release110-open-defects
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 35
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/backend_crud_actz.py"
  - "scripts/backend_crud_adapts.py"
  - "scripts/backend_crud_at.py"
  - "scripts/backend_crud_specs.py"
  - "tests/test_fts_searches_sanitise_the_query.py"
  - "tausik/gates.json"
scope_paths:
  - "scripts/*.py"
  - "tests/*.py"
  - "tausik/gates.json"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-28T13:45:56Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

НАЙДЕНО ПРИ ПОЧИНКЕ memory-search-crashes-on-two-word-queries, смена #277. Санитайзер _sanitize_fts5 живёт в backend_queries и вызывается ровно из трёх мест. Ещё ШЕСТЬ вызовов FTS MATCH не санируют запрос вообще: backend_crud_actz.py:259, backend_crud_adapts.py:239, backend_crud_at.py:63, backend_crud_specs.py:145, memory_relevance.py:182, snippet_storage.py:124 и :157.

ЗАМЕРЕНО через живой CLI: `spec search foo-bar`, `at search foo-bar`, `adapt search foo-bar`, `actz search foo-bar` дают «Error: Invalid search query 'foo-bar': no such column: bar». Это НЕ трейсбек — отказ перехвачен и назван, поэтому severity ниже родительского дефекта. Но обычный запрос с дефисом, точкой или решёткой («release-1.10», «tausik.tech», «github#124») отвергается, а именно так в этом проекте и пишут имена.

СЛЕДСТВИЕ, КОТОРОЕ СТОИТ ДОРОЖЕ САМОГО ОТКАЗА: сообщение «no such column: bar» толкает агента думать, что он перепутал синтаксис, и пробовать ещё раз в другой форме. Один оборот измерен как ~482k токенов cache_read.

ЧТО ПРОВЕРИТЬ ПЕРВЫМ, а не чинить сразу: одинаково ли шесть мест заслуживают санитайзера. memory_relevance строит запрос САМ из ключевых слов задачи, а не из пользовательского ввода — там источник доверенный, и санитайзер может быть лишним; snippet_storage принимает ввод. Различие определяет, одна это правка или две.

## Acceptance Criteria

AC-1 ПРОВЕРИТЬ ПЕРВЫМ, а не чинить: у каждого из семи мест назван ИСТОЧНИК запроса и то, санируется ли он уже. Постановка называла шесть мест без санитайзера; проверить поимённо. AC-2 Место, принимающее пользовательский ввод и НЕ санирующее его, получает санитайзер — тот же, что у трёх работающих поисков, а не второй его вариант. AC-3 Замер живым CLI до и после: spec search, at search, adapt search, actz search на запросе с дефисом. До — отказ с текстом про несуществующую колонку; после — результат или честный пустой. AC-4 НЕГАТИВ: место, где запрос строит САМ код из доверенных ключевых слов и уже квотирует термы, не получает второго слоя — двойное экранирование сломало бы поиск, который сейчас работает. AC-5 НЕГАТИВ: запрос, который не находит ничего, возвращает пустой список, а не ошибку; и запрос из одних спецсимволов не превращается в поиск по всему. AC-6 Тест на каждое исправленное место: дефис, точка и решётка в запросе.

## Plan

## Rollback

git revert коммита: четыре поиска возвращаются к отказу на дефисе. Санитайзер общий и уже работает у трёх поисков, поэтому откат не оставляет полусостояния.

## Journal

- 2026-09-28T13:31:16Z [implementation] — AC-1 проверено поимённо, и постановка неверна для двух мест из семи. memory_relevance:182 строит запрос САМ из ключевых слов и уже чистит термы через _FTS5_TOKEN_SPECIAL_RE, затем квотирует — второй слой сломал бы работающий поиск. snippet_storage:124 и :157 уже зовут _fts_quote на вводе. Без санитайзера ровно ЧЕТЫРЕ места: backend_crud_actz, adapts, at, specs — и именно их четыре CLI-команды и роняет. AC-3 замер ДО: все четыре дают «Invalid search query 'foo-bar': no such column: bar».
- 2026-09-28T13:34:16Z [implementation] — Мой же негативный тест нашёл ВТОРОЙ дефект: запрос из одних операторов санируется в пустую строку, а пустой MATCH сам есть syntax error в FTS5 — то есть четыре поиска обменяли бы одну ошибку на другую. Добавлена та же охрана, что у трёх работающих поисков: пустой результат санитайзера даёт [], а не запрос. Пустой список честен, а match-all был бы хуже прежнего отказа. AC-3 замер ПОСЛЕ: все четыре команды отвечают «No matching …» на foo-bar, release-1.10, github#124 и tausik.tech.
- 2026-09-28T13:38:05Z [implementation] — Четыре существующих теста требовали ServiceError на несбалансированной кавычке. Это обещание было верным, ПОКА запрос уходил в FTS5 сырым — оно не давало утечь трейсбеку. Теперь санировать нечего отказывать: несбалансированная кавычка есть пунктуация, а имена в проекте полны пунктуации. Контракт переписан с ПРИЧИНОЙ, а не флипом ожидания, и исходный замысел соблюдён полнее: вызывающий получает ответ вместо урока о синтаксисе.
- 2026-09-28T13:41:09Z [implementation] — AC verified: AC-1 ✓ семь мест разобраны поимённо, два уже безопасны и остались нетронутыми, без санитайзера ровно четыре. AC-2 ✓ четыре места зовут ТОТ ЖЕ _sanitize_fts5, что и три работающих поиска; проверяется тестом по исходнику метода. AC-3 ✓ замер живым CLI до и после в журнале: было «no such column: bar», стало «No matching …» на foo-bar, release-1.10, github#124, tausik.tech. AC-4 ✓ негатив: memory_relevance и snippet_storage проверены тестом на ОТСУТСТВИЕ второго слоя — двойное экранирование сломало бы работающий поиск. AC-5 ✓ негатив: запрос из одних операторов даёт [], а не match-all и не ошибку; найден моим же тестом как второй дефект. AC-6 ✓ тест на дефис, точку, решётку и несбалансированную кавычку для каждого из четырёх поисков. Root cause: санитайзер жил в одном модуле, а четыре поиска в других и звали MATCH напрямую. Domain: поиск по именам, как их пишут в этом проекте. Negative: AC-4 и AC-5 закреплены. NO-DEAD-END.
- 2026-09-28T13:44:29Z [implementation] — EVIDENCE: default 11949 passed / 30 skipped / 0 failed; ruff чистый; дедуп 283/671, ровно база; список legacy-формата сократился на четыре файла — те, что правка отформатировала по делу.
