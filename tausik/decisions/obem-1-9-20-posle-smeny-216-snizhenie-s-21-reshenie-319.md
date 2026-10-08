---
slug: obem-1-9-20-posle-smeny-216-snizhenie-s-21-reshenie-319
task: roadmap-artifact-predates-decision-256
date: "2026-09-06"
edges: []
---

## Decision

ОБЪЁМ 1.9 = 20 ПОСЛЕ СМЕНЫ #216, снижение с 21 (решение #319). Пересчитано КОМАНДОЙ по шести историям: gates-declare-what-they-prevent 7 (6 planning + 1 BLOCKED), renar-contract-contour 5, evidence-primitives 4, test-evidence-not-test-volume 4, renar-debt-implemented-wrong 0 (история ЗАКРЫТА ЦЕЛИКОМ), standards-drift-detection 0 (закрыта в #215). Точки: 35,38,37,39,42,40,42,43,39,34,32,28,32,31,29,25,23,21,20.

## Rationale

Закрыта roadmap-artifact-predates-decision-256 — последняя задача истории renar-debt-implemented-wrong, история закрылась автоматически. Из шести историй релиза две закрыты целиком, остаток лежит в четырёх.

ПЕРЕСЧЁТ СДЕЛАН ТЕМ ЖЕ КОДОМ, ЧТО ПОРОЖДАЕТ КАРТУ (release_roadmap.composition + _remaining), а не отдельным скриптом: у счёта релиза одна реализация, и цифра в решении не может разойтись с цифрой в ROADMAP.md — это то же самое число, а не два одинаковых.

Состав шести историй прочитан из решения #319 машиной, не введён рукой; устав — #256 через #294. Правило состава не менялось.
