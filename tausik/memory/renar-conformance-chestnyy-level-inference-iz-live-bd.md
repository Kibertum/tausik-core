---
slug: renar-conformance-chestnyy-level-inference-iz-live-bd
title: "RENAR conformance: честный level-inference из live-БД (machinery vs data clauses)"
type: pattern
tags:
  - conformance
  - honesty
  - maturity
  - renar
task: v16r-conformance-yaml
edges: []
---

`tausik renar conformance` (renar_conformance.py) генерирует RENAR-CONFORMANCE.yaml §14.4.2, вычисляя уровень из live-БД, не декларативно. Ключевые принципы честности (из ревью): (1) §14.4.3 — нарушение ЛЮБОЙ mandatory clause → pre_adoption=true + level=null (паттерн kai, аудит §0.2.3); (2) machinery-vs-data split клауз: capability-клаузы (closed-lists, V1-V6, QG, schema-hook=drift-1) confirmed по наличию машинерии; data-клаузы (adapt-per-tz) — только при артефактах; (3) §14.3.5 tc-pos-neg = CONDITIONAL (vacuous-true когда нет TC, НЕ путать с gate_negative_scenario=QG-0 на тексте AC); (4) tz_immutable требует status='signed' (draft≠immutable §12.5.1); (5) level-signals честные False где нет enforcement (knowledge_graph row-existence≠primacy); (6) --write читает existing manifest-version→инкремент+atomic os.replace (§14.4.1 immutability, не reset-to-1). На собственной базе TAUSIK честно = pre_adoption (0 ADAPT). [[v16r-drift-detectors-pattern]] (drift-1 = schema-validation-hook сигнал RENAR-3).
