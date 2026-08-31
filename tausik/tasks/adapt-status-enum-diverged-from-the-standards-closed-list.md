---
slug: adapt-status-enum-diverged-from-the-standards-closed-list
title: "Закрытый перечень статусов ADAPT разошёлся со стандартом в обе стороны: лишний signed есть, обязательного approved нет"
status: planning
epic: release-19-renar-conformance
story: renar-debt-implemented-wrong
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 80
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on:
  - our-conformance-claim-rests-on-a-mode-the-standard-removed
completed_at: null
---

## Goal

НАЙДЕНО В #198 ПРИ ВЫНЕСЕНИИ ВЕРДИКТА ПО ADR-007. Единственное структурное несоответствие из шести: чинится не процессом, а миграцией схемы.

СТАНДАРТ, §7.8.1 стр.384 (цитата сверена машиной): «status: draft | review | asked | answered | approved | frozen | superseded» — семь значений, список закрытый.
МЫ, scripts/backend_schema_adapts.py:20: CHECK на ТРИ — «('draft', 'signed', 'superseded')».

ДВА СЛЕДСТВИЯ, ВТОРОЕ ТЯЖЕЛЕЕ.
(1) `signed` — значение, которого в закрытом перечне стандарта НЕТ. Мы завели собственный статус в списке, объявленном закрытым.
(2) `approved` — значение, которое §13.3.3 ТРЕБУЕТ для ветви findings-present («ADAPT обязателен в статусе `approved` с подписью Архитектора»), у нас ОТСУТСТВУЕТ. Наш ADAPT не может достичь требуемого статуса не по лени, а потому что CHECK-ограничение БД отклонит запись. Соответствие недостижимо без миграции.

СМЕЖНОЕ, ИЗ ТОГО ЖЕ ВЕРДИКТА, НЕ РАЗРЕЗАТЬ.
— `trigger-stage`, которым ADR-007 различает несколько ADAPT одного ТЗ, в схеме ОТСУТСТВУЕТ (негативная проверка прошла). Кардинальность 0..N мы формально не нарушаем при одном ADAPT, но выразить её не умеем.
— Дезавуирование наполовину есть и потому опаснее пустого места: статус `superseded` в enum ЕСТЬ, ребро `supersedes` в backend_schema.py:146 ЕСТЬ, а обязательного `supersession-rationale` (ADR-007 стр.108) НЕТ. Дезавуировать механически можно, сослаться на противоречащее требование — нельзя. Запись будет синтаксически валидной и содержательно пустой: вырожденный контроль по ADR-021, только в схеме данных.
— Точки контроля `adapt-supersession` (§10.11.1 стр.485) и обещанного самим ADR-007 гейта check-adapt-supersession у нас нет: висячая ссылка source.adapt на superseded ADAPT ничем не ловится.

ОГОВОРКА О ПОРЯДКЕ РАБОТ. Миграция enum осмысленна только вместе с решением по our-conformance-claim-rests-on-a-mode-the-standard-removed: если заявка о соответствии снимается, приводить схему к чужому закрытому списку — работа без адресата. Зависимость ставится в БД.

## Acceptance Criteria

## Plan

## Rollback

## Journal
