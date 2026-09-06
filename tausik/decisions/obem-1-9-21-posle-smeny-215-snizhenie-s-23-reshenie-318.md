---
slug: obem-1-9-21-posle-smeny-215-snizhenie-s-23-reshenie-318
task: null
date: "2026-09-06"
edges: []
---

## Decision

ОБЪЁМ 1.9 = 21 ПОСЛЕ СМЕНЫ #215, снижение с 23 (решение #318). Пересчитано КОМАНДОЙ по шести историям: gates-declare-what-they-prevent 7 (6 planning + 1 BLOCKED), renar-debt-implemented-wrong 1, renar-contract-contour 5, evidence-primitives 4, test-evidence-not-test-volume 4, standards-drift-detection 0 (история ЗАКРЫТА ЦЕЛИКОМ). Точки: 35,38,37,39,42,40,42,43,39,34,32,28,32,31,29,25,23,21.

## Rationale

Закрыты our-evidence-speaks-only-our-own-schema (standards-drift 1→0, история закрылась автоматически) и adapt-dual-signature-implements-a-withdrawn-norm (renar-debt 2→1). Обе начинались с проверки премисы, и обе премисы оказались частично неверны: экспорт OTLP был сделан ещё в 1.8, а состояния client-ready в нашей машине не существует вовсе — работа в обоих случаях свелась к меньшему и точному приращению.
