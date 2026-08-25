---
slug: srez-v1-5-polirovka-v15p-senar-v15s-edinstvennaya-ficha
task: null
date: "2026-06-13"
edges: []
---

## Decision

Срез v1.5 = полировка (v15p) + SENAR (v15s) + единственная фича v15mr-fable-tier-fix (P0). Snippet ×5, orchestrator, остальные model-routing (v15mr phase-matrix/surfaces/subagent-hints/telemetry) переносятся в 1.6.

## Rationale

v15mr-fable-tier-fix чинит ложный MODEL MISMATCH (P0-баг, бьёт по dogfood каждой сессии) — обязателен в 1.5. Snippet/orchestrator — крупные фичи без блокеров, безопасно отложить в 1.6, держит релиз 1.5 сфокусированным на качестве и стабильности (SENAR: верификация важнее скорости).
