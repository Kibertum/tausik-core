---
slug: pricing-guard-watches-routable-models-not-the-running-one
title: "Охрана цен смотрит на маршрутизируемые модели, а не на работающую: 36.5% живых токенов записаны по $0.00 при зелёном тесте"
status: planning
epic: release-19-renar-conformance
story: guarantees-are-not-claude-only
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 55
defect_of: telemetry-and-pricing-know-one-vendor-only
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

ЗАМЕР НА ЖИВОМ ДЕРЕВЕ (смена #225, .tausik/token_metrics.jsonl, 4777 строк за смены #220-#224): 1713 строк из 4777 (35.9%) и 1 133 486 токенов из 3 102 706 (36.5%) записаны с model=claude-opus-5, для которой в scripts/cost_pricing.py НЕТ ЦЕНЫ. Стоимость этих токенов записана как $0.00. `tausik metrics` печатает «Last session: #225 842,558 tokens, $0.0000, model=claude-opus-5» — уверенный ноль там, где ответ «неизвестно».

ЭТО НЕ ПРОБЕЛ ВЕНДОРА, А ДЫРА В СОБСТВЕННОЙ ОХРАНЕ. Механизм против ровно этого дефекта СУЩЕСТВУЕТ: cost_pricing.models_missing_pricing() + tests/test_cost_pricing.py заведены задачей cost-pricing-missing-opus-48 именно потому, что «таблица, которую надо обновлять по памяти, — это таблица, которая дрейфует». Охрана осталась зелёной, потому что она читает МАРШРУТИЗИРУЕМЫЕ идентификаторы (model_profiles / model_routing_matrix / service_delegate), а цена применяется к РАБОТАЮЩЕМУ идентификатору, который приходит из полезной нагрузки хоста и в этих таблицах не значится. Замер: model_profiles.DEFAULT_FAMILIES называет claude-opus-4-8 и claude-sonnet-4-6, то есть на поколение отстаёт от того, на чём проект реально работает; claude-opus-5 не упомянут ни в одном из трёх источников.

ЭТО ПРЯМО ПОДРЫВАЕТ ДВА ОБЕЩАНИЯ РЕЛИЗА 1.9. Заявление об экономии токенов не может опираться на счётчик, треть которого — тихий ноль; заявление о качестве «на любой модели» не может опираться на телеметрию, которая не знает даже текущую модель СВОЕГО ЖЕ вендора.

ЧТО ДЕЛАЕТСЯ: источником охраны становится НАБЛЮДЁННАЯ модель (та, что реально записана в телеметрию), а не только объявленная в таблицах маршрутизации. Неизвестная модель обязана давать ВИДИМОЕ «цена неизвестна» в metrics, а не ноль (решение #334: величина, которую нельзя измерить, даёт отсутствие, а не ноль).

ГРАНИЦА С telemetry-and-pricing-know-one-vendor-only (родитель): там — РАЗБОР ФОРМЫ полезной нагрузки и цены ДРУГИХ вендоров. Здесь — дыра в охране согласованности на СВОЁМ вендоре и подача «неизвестно» вместо нуля в metrics. Не сливать.

## Acceptance Criteria

## Plan

## Rollback

## Journal
