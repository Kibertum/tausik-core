---
slug: renar-drift-detektory-mappyatsya-na-tausik-model-task-tc
title: "RENAR drift-детекторы маппятся на TAUSIK-модель: task=TC, spec=requirement"
type: pattern
tags:
  - drift
  - gates
  - provenance
  - renar
task: v16r-drift-detectors
edges: []
---

У TAUSIK нет first-class TC-таблицы. RENAR §3.11 drift-7 (TC↔requirement provenance) реализован так: единица верификации = task (его acceptance_criteria = «TC»), требование = spec, связь = task_specs. drift-1 (schema) ре-валидирует specs+adapts по closed-lists (импорт констант из service_specs/service_adapts — single source) + cross-field инварианты, которые DB CHECK выразить не может (delta_n↔parent_adapt, signed↔dual-signature §7.5). Детекторы pure conn-based в scripts/renar_drift.py; warn-only gates (renar_drift_schema/provenance) + CLI `tausik drift`. Ключевое для FP: stale-verification scoped к active spec (deprecated после done — settled, не stale, иначе double-report с deprecated-requirement). _rows ловит OperationalError ТОЛЬКО 'no such table' (иначе syntax-ошибка маскируется под clean). Артефактные таблицы на собственной базе пусты → FP=0, детекторы forward-looking. Остальные 6 drift-классов не реализованы.
