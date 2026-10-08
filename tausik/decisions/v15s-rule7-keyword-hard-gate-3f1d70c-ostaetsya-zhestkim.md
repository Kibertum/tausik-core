---
slug: v15s-rule7-keyword-hard-gate-3f1d70c-ostaetsya-zhestkim
task: v15s-rule7-rootcause-hardgate
date: "2026-06-13"
edges: []
---

## Decision

v15s-rule7: keyword hard-gate (3f1d70c) остаётся жёстким полом; structured-часть = парсер root-cause (closed-list категория + prevention) + метрика root_cause_coverage + advisory-nudge на отсутствие структуры. НЕ делаем structured хардом (сломало бы существующие defect-close с keyword-only).

## Rationale

Апгрейд keyword->structured как hard сломает закрытие старых defect-задач с keyword-only root cause (регрессия flow). Ценность structured — в распознавании и метрике покрытия, а не в ужесточении блокировки поверх уже работающего keyword-гейта. SENAR: не ломать рабочий путь ради строгости.
