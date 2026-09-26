---
slug: six-fts-searches-never-sanitise-the-query
title: "Шесть поисков по FTS отказывают на обычном запросе с дефисом"
status: planning
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
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
resolution: null
resolution_reason: null
---

## Goal

НАЙДЕНО ПРИ ПОЧИНКЕ memory-search-crashes-on-two-word-queries, смена #277. Санитайзер _sanitize_fts5 живёт в backend_queries и вызывается ровно из трёх мест. Ещё ШЕСТЬ вызовов FTS MATCH не санируют запрос вообще: backend_crud_actz.py:259, backend_crud_adapts.py:239, backend_crud_at.py:63, backend_crud_specs.py:145, memory_relevance.py:182, snippet_storage.py:124 и :157.

ЗАМЕРЕНО через живой CLI: `spec search foo-bar`, `at search foo-bar`, `adapt search foo-bar`, `actz search foo-bar` дают «Error: Invalid search query 'foo-bar': no such column: bar». Это НЕ трейсбек — отказ перехвачен и назван, поэтому severity ниже родительского дефекта. Но обычный запрос с дефисом, точкой или решёткой («release-1.10», «tausik.tech», «github#124») отвергается, а именно так в этом проекте и пишут имена.

СЛЕДСТВИЕ, КОТОРОЕ СТОИТ ДОРОЖЕ САМОГО ОТКАЗА: сообщение «no such column: bar» толкает агента думать, что он перепутал синтаксис, и пробовать ещё раз в другой форме. Один оборот измерен как ~482k токенов cache_read.

ЧТО ПРОВЕРИТЬ ПЕРВЫМ, а не чинить сразу: одинаково ли шесть мест заслуживают санитайзера. memory_relevance строит запрос САМ из ключевых слов задачи, а не из пользовательского ввода — там источник доверенный, и санитайзер может быть лишним; snippet_storage принимает ввод. Различие определяет, одна это правка или две.

## Acceptance Criteria

## Plan

## Rollback

## Journal
