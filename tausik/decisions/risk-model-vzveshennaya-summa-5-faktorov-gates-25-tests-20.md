---
slug: risk-model-vzveshennaya-summa-5-faktorov-gates-25-tests-20
task: v15-risk-model
date: "2026-06-12"
edges: []
---

## Decision

Risk-модель: взвешенная сумма 5 факторов (gates .25, tests .20, AC-evidence .20, security .20, churn .15), пороги 0.33/0.66, missing factor = консервативный 1.0 + defaulted-список

## Rationale

Сумма а не max: риск компаундируется из независимых слабостей. Веса априорные до накопления риск-строк в БД для калибровки. Fail-visible: неизмеренный фактор не должен выглядеть безопаснее измеренного-плохого.
