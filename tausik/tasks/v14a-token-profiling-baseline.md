---
slug: v14a-token-profiling-baseline
title: "A4: token profiling baseline для /start /task /ship"
status: done
epic: v14-polish-critical
story: v14-polish-a-pre-push
complexity: null
role: qa
stack: python
tier: light
call_budget: 15
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-03T10:19:06Z"
---

## Goal

Измерить tokens на /start /task /ship. Записать baseline в docs/ru/research/tausik-1.4-token-baseline-2026-05-03.md. Использовать tausik metrics --cost (или manual estimate).

## Acceptance Criteria

1. Создан docs/ru/research/tausik-1.4-token-baseline-2026-05-03.md с baseline.
2. Документ имеет: methodology, текущие numbers для /start /task /ship (estimate), targets для оптимизации.
3. CLAUDE.md (post-bootstrap) size ≈ baseline (lines × ~3.5 tokens/line).
4. Memory Block re-injection size estimated.
5. Negative: нет реальных измерений — все numbers labeled estimate.
relevant_files: docs/ru/research/tausik-1.4-token-baseline-2026-05-03.md

## Plan

## Rollback

## Journal

- 2026-05-03T10:19:06Z [implementation] — AC verified: 1. ✓ docs/ru/research/tausik-1.4-token-baseline-2026-05-03.md создан. 2. ✓ Methodology + Estimate numbers + Targets + Measurement plan. 3. ✓ /start ~17k, /task ~900, /ship ~6k. 4. ✓ Memory Block ~30 lines = ~150 tokens. 5. ✓ Все numbers явно labeled 'estimate' — реальные measurements в Phase B через v14b-usage-events-auto-write.
