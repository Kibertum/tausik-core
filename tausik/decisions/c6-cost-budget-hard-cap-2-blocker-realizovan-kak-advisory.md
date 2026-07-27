---
slug: c6-cost-budget-hard-cap-2-blocker-realizovan-kak-advisory
task: v14c-token-budget-task
date: "2026-05-07"
edges: []
---

## Decision

C6 cost-budget hard cap (2× BLOCKER) реализован как advisory stderr message, не как физический block инструмента.

## Rationale

Claude Code PostToolUse hooks не могут физически остановить агента — они только пишут в stderr. Агент видит сообщение следующим turn'ом и обязан остановиться сам. Это soft refuse pattern, аналогичный SENAR session capacity gate (тоже advisory). Для 2× BLOCKER формулировка 'stop and re-plan or `tausik task update --cost-budget`' даёт actionable next step. Throttle 30s per (slug, level) предотвращает спам если агент игнорирует.
