---
slug: c1-mass-parametrize-razdelen-na-3-batch-a-po-size-buckets
task: v14c-mass-parametrize-batch-1
date: "2026-05-07"
edges: []
---

## Decision

C1 mass-parametrize разделён на 3 batch'а по size-buckets аудита: batch-1 (size ≥4, 34 групп), batch-2 (size=3, 33 групп), batch-3 (size=2, 145 групп — DEFERRED 1.4.1). Cross-file группы обрабатываются per-file (без перемещений тестов между модулями).

## Rationale

Original v14c-mass-parametrize-all single task 488 кандидатов нарушал SENAR Rule 9.2 (180-min session limit) — реалистично 5+ сессий. Split по size-buckets даёт ROI-aware прогрессию: batch-1 и batch-2 закроют ≥230 тестов в 1.4, batch-3 (2-test groups) — диминишинг return (false-positive risk: structural identity ≠ semantic identity для пар) перенесён. Per-file approach для cross-file групп предотвращает churn в test организации.
