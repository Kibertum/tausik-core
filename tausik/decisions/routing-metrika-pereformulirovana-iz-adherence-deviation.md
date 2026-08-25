---
slug: routing-metrika-pereformulirovana-iz-adherence-deviation
task: routing-adherence-metric-measures-nothing
date: "2026-07-26"
edges: []
---

## Decision

Routing-метрика переформулирована из 'adherence/deviation' (нарушение) в 'recommendation fit' (калибровка): reframe, а не suppress-rows или count-only-switchable

## Rationale

Routing Adherence 1.6% при n=10909, sonnet->opus 10739 — метрика сообщала о нарушении правила в 98.4% случаев, то есть измеряла НЕВЫПОЛНИМОСТЬ правила, не нарушение. Claude Code не переключает модель программно (bootstrap WORKFLOW), модель фиксирована на сессию выбором пользователя. Из 3 опций задачи выбран reframe (option 2): (1) suppress-rows когда actual==session-model потерял бы почти все данные (одномодельные сессии — большинство); (2) count-only-switchable невозможно определить per-row; (3) reframe сохраняет калибровочные данные (совпадает ли рекомендация матрицы с тем, что реально запускают) и убирает ложную коннотацию провала дисциплины. Данные (record/aggregate) не тронуты — только презентация + докстринг: 'Model Recommendation Fit' + пояснение что выбор модели per-session/вручную.
