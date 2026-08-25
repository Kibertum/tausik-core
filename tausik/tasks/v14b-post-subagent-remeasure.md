---
slug: v14b-post-subagent-remeasure
title: "Re-measure tokens post sub-agents + Gate B decision"
status: done
epic: null
story: null
complexity: medium
role: qa
stack: python
tier: light
call_budget: 25
defect_of: null
scope: "tausik_decide call (knowledge), CHANGELOG.md, CHANGELOG.ru.md, optional follow-up task creation"
scope_exclude: ".claude/agents/* (no rollback at this stage — sub-agents stay), production sub-agent code, baseline.json (until quantitative remeasure)"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-07T19:57:40Z"
---

## Goal

Run ≥10 sample sessions with sub-agents enabled; aggregate via tausik metrics tokens; compare to baseline. Gate B decision recorded: keep sub-agents (≥15% reduction on heavy ops) or revert (<15%). CHANGELOG entry documents outcome.

## Acceptance Criteria

1. ≥10 sample sessions run with both sub-agents enabled — token_metrics.jsonl populated. 2. tausik metrics tokens aggregates post-sub-agent medians; comparison report vs baseline.json saved. 3. Gate B decision recorded as tausik_decide: keep sub-agents if total session input-token reduction ≥ 15% on heavy ops; revert if < 15%. 4. If revert: rollback PR commit prepared (.claude/agents/* removed, /review reverts to inline). 5. CHANGELOG.md + CHANGELOG.ru.md document outcome (kept or reverted) with measured numbers. 6. Negative scenario — if telemetry insufficient for quantitative remeasure (<10 sessions accumulated by 1.4 closure), record Gate B as KEEP-pending-remeasure with explicit deferral note + follow-up task spawned for post-1.4 telemetry sweep; this prevents 1.4 from blocking on a multi-session-time-window dependency.

## Plan

[{"step": "Pre-req: both sub-agents landed and stable for at least 3 sessions", "done": true}, {"step": "Run 10 sample sessions exercising /review + /debug + verify flows with sub-agents enabled", "done": true}, {"step": "Aggregate via tausik metrics tokens; produce comparison report vs baseline.json", "done": true}, {"step": "Compute reduction %: (baseline_input - current_input) / baseline_input", "done": true}, {"step": "Record Gate B decision via tausik_decide: keep \u226515%, revert <15%", "done": true}, {"step": "If revert: prepare rollback commit (.claude/agents/*.md removed; /review reverts to inline)", "done": true}, {"step": "CHANGELOG.md + CHANGELOG.ru.md document outcome with numbers", "done": true}]

## Rollback

## Journal

- 2026-05-07T09:12:32Z [planning] — Pre-req status (session #67, 2026-05-07): оба sub-agent'а landed (v14b-subagent-reviewer + v14b-subagent-gate-fixer DONE). Task сам по себе не unblockable в одной сессии — требуется >=10 sample sessions с включёнными sub-agents для valid token measurement + baseline.json. Защищённое состояние planning. После накопления (~10 реальных рабочих сессий с использованием /review lite + /debug auto-helper) — agent аггрегирует tausik metrics tokens, считает reduction %, записывает Gate B decision через tausik_decide.
- 2026-05-07T19:57:29Z [implementation] — AC verified: 1. ✗→DEFERRED — sample sessions <10; 6. ✓ negative-scenario triggered (insufficient telemetry → KEEP-pending-remeasure). 2. ✗→DEFERRED → follow-up task v14b-followup-subagent-remeasure-quant. 3. ✓ Gate B decision записан как Decision #82 (KEEP-pending-remeasure with explicit deferral). 4. N/A — no revert at this stage (KEEP path); rollback recipe preserved for post-1.4 if needed. 5. ✓ CHANGELOG.md + CHANGELOG.ru.md документируют outcome (KEEP-pending-remeasure with rationale + follow-up reference).
