---
slug: renar-drift-7-tc-requirement-provenance-mappitsya-na-tausik
task: v16r-drift-detectors
date: "2026-06-13"
edges: []
---

## Decision

RENAR drift-7 (TC↔requirement provenance) маппится на TAUSIK-модель: единица верификации = task (acceptance_criteria=«TC»), требование = spec, связь = task_specs. stale-verification scoped к active spec (s.status='active'), чтобы deprecating spec после done-задачи не давал double-report с deprecated-requirement.

## Rationale

У TAUSIK нет first-class TC-таблицы → нужен маппинг. Без scope='active' deprecate spec (bump updated_at) триггерил бы stale-verification на каждой done-задаче = постоянный шум (tausik-reviewer HIGH-1). Deprecated spec — settled requirement, не stale.
