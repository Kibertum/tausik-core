---
slug: v14b-followup-subagent-remeasure-quant
title: "Quantitative sub-agent token remeasure (≥10 sessions accumulated)"
status: planning
epic: landscape-2026-h2
story: l26-provable
complexity: medium
role: qa
stack: python
tier: moderate
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
completed_at: null
---

## Goal

After ≥10 real sessions with sub-agents enabled accumulate in token_metrics.jsonl post-1.4.0 release, run `tausik metrics tokens`, compute input-token reduction % vs pre-sub-agent baseline.json, record Gate B FINAL decision via tausik_decide. If reduction ≥15%: confirm KEEP. If <15%: prepare 1.4.x revert (.claude/agents/*.md removal + /review revert to inline) per the original Gate B rollback recipe.

## Acceptance Criteria

AC1. После накопления ≥10 реальных сессий с sub-agents в token_metrics.jsonl (post-1.4.0) выполнен `tausik metrics tokens`; сокращение input-токенов относительно baseline.json посчитано и зафиксировано числом.
AC2. Финальное решение Gate B зафиксировано через tausik decide: KEEP при сокращении ≥15%, иначе — курс на откат 1.4.x.
AC3. Ветка <15%: подготовлен рецепт отката по исходному Gate B rollback recipe — удаление .claude/agents/*.md + возврат /review к inline.
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью об этом изменении.

## Plan

## Rollback

## Journal
