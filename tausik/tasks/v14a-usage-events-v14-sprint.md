---
slug: v14a-usage-events-v14-sprint
title: "A1: записать v1.4 sprint usage events (estimate per task)"
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
completed_at: "2026-05-03T10:20:05Z"
---

## Goal

Заполнить usage_events для v14-* задач сессий #42-43 — model_id="claude-opus-4-7", tokens estimate, task_slug, session, cost. Цель: tausik metrics --cost даёт реальную картину бюджета v1.4 разработки.

## Acceptance Criteria

1. usage_events заполнен для всех v14-* done задач (~50-60 рядов).
2. model_id="claude-opus-4-7" (default Composer + сессия #43 модель).
3. tokens estimate per task: trivial=2000, light=8000, moderate=20000, substantial=50000, deep=120000 (input+output combined).
4. cost computed via llm_pricing config (Opus = $15/$75 per 1M).
5. tausik metrics --cost возвращает реальную таблицу (не "No usage data").
6. Negative: data явно labeled estimate в evidence (не реальный telemetry).
relevant_files: .tausik/tausik.db (через sqlite UPDATE)

## Plan

## Rollback

## Journal

- 2026-05-03T10:20:05Z [implementation] — AC verified: 1. ✓ 62 v14-* done задач — usage_events заполнены (input=3.4M, output=601K, total=4M tokens). 2. ✓ model_id=claude-opus-4-7 для всех. 3. ✓ tokens estimate per tier: trivial=2k/light=8k/moderate=20k/substantial=50k/deep=120k. 4. ✓ cost computed via Opus pricing (input $15/M, output $75/M) = $96.17. 5. ✓ tausik metrics --cost возвращает таблицу top tasks (no longer 'No usage data'). 6. ✓ Negative: source='manual' label указывает что это estimate, не реальный telemetry — в Phase B авто-запись через PostToolUse hook.
