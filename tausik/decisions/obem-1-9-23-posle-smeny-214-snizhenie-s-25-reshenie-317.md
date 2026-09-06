---
slug: obem-1-9-23-posle-smeny-214-snizhenie-s-25-reshenie-317
task: null
date: "2026-09-06"
edges: []
---

## Decision

ОБЪЁМ 1.9 = 23 ПОСЛЕ СМЕНЫ #214, снижение с 25 (решение #317). Пересчитано КОМАНДОЙ по шести историям: gates-declare-what-they-prevent 7 (6 planning + 1 BLOCKED), renar-debt-implemented-wrong 2, renar-contract-contour 5, evidence-primitives 4, test-evidence-not-test-volume 4, standards-drift-detection 1. Точки: 35,38,37,39,42,40,42,43,39,34,32,28,32,31,29,25,23.

## Rationale

Закрыты три задачи из объёма: adapt-category-list-lives-in-three-literal-copies (renar-debt 3→2), nothing-detects-that-the-standard-moved-under-us (standards-drift 2→1) и check-parser-is-blind-to-sql-comments-and-basis-discloses-less (дефект по внешнему L3 #40, заведён в renar-debt и закрыт в ту же смену — объём не изменил). Смена закрыта по остатку ёмкости: 61 вызов при medium-задачах с бюджетом 60 — начинать значило упереться в гейт посреди работы.
