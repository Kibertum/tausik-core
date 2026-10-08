---
slug: r111-workflow-cost-audit
title: "1.11: remove the next measured workflow overhead"
status: done
epic: release-111-economy-draft
story: release111-context-and-workflow
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 35
defect_of: null
scope: "Existing call-mix/context workflow and skills; one measured improvement only."
scope_exclude: "Paid synthetic benchmarks, external publication, broad refactoring and weakened gates."
relevant_files:
  - "scripts/task_context_package.py"
  - "harness/skills/task/SKILL.md"
  - "tests/test_task_context_package.py"
  - "docs/ru/research/release111-economy-results.md"
  - "changelog.d/task-package-plan-111.md"
scope_paths:
  - ".tausik/planning/release-111"
  - "docs/ru/research/release111-economy-results.md"
  - "scripts/task_context_package.py"
  - "harness/skills/task/SKILL.md"
  - "tests/test_task_context_package.py"
  - "changelog.d/task-package-plan-111.md"
scope_tools: []
depends_on: []
completed_at: "2026-10-01T19:58:31Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Use existing Codex traces to rank repeated context and unnecessary model rounds, then implement only the highest-value bounded improvement.

## Acceptance Criteria

AC-1 Offline existing traces rank three concrete sources by bytes/rounds with unassigned work reported separately. AC-2 Choose one change with explicit stop budget and before/after behavior measurement. AC-3 No synthetic paid model runs, no full-history worker forks by default, and no weakening task/verify gates. AC-4 A negative regression protects necessary work; scoped verify passes.

## Plan

[{"step": "Rank three overhead sources from existing native traces without model replay", "done": true}, {"step": "Select and implement one bounded improvement with behavior regression coverage", "done": true}, {"step": "Measure before/after, verify and record limits", "done": true}]

## Rollback

Revert this task's bounded changes; preserve raw measurements and prior inconclusive verdict.

## Journal

- 2026-10-01T19:56:38Z [implementation] — Step1 measurement: 14 project Codex transcripts,39.3MB source. Outer outputs containing file reads:5,745,411B/338 calls/808 mentions; searches:4,830,158B/256/409; task show:662,784B/59/102. Categories overlap when batched; bytes are candidate upper bounds. Validation pytest outputs672,186B are necessary and excluded from overhead ranking. Separate attribution baseline:934 accepted-task rounds;1421 project responses unassigned. Selected clean task-show package improvement: completed task full16371B vs current package5052B. Stop budget: one producer field, one skill correction, one parametrized/behavior regression; no new API/model run/gate weakening.
- 2026-10-01T19:57:36Z [implementation] — Step2 done: one bounded change only. Task package now includes complete plan progress; task skill uses package mode for routine status and close-plan checks. Negative behavior regression preserves done=false as well as done=true. Focused:13 passed;ruff green.
- 2026-10-01T19:58:26Z [implementation] — AC verified: 1. ✓ Offline 14-transcript audit ranks file reads 5,745,411B, searches 4,830,158B, task-show 662,784B; 1421 unassigned responses reported separately from 934 accepted-task rounds. 2. ✓ Selected one change with stop budget 1 producer field + 1 skill + 1 regression. Frozen task: full 16,371B, package before 5,052B, after 5,490B (-66.5% vs full). 3. ✓ No synthetic model runs or workers; task/verify gates unchanged. Claim limited to payload reduction. 4. ✓ Regression preserves complete/incomplete plan status; 13 focused tests passed and scoped verify #3294 passed.
- 2026-10-01T19:58:26Z [implementation] — Step3: frozen fixture full16371B;package before5052B;after5490B with4/4 plan steps, -66.5% vs full. Domain: agent receives exact plan progress for real task. Negative: incomplete plan step remains done=false. Limit: payload only; accepted-task token/round savings unknown. Verify3294 green;no paid replay.
