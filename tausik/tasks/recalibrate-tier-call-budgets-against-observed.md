---
slug: recalibrate-tier-call-budgets-against-observed
title: "Recalibrate tier call budgets against observed actuals"
status: planning
epic: release-1-11-3
story: release1113-hygiene-calibration
complexity: null
role: architect
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: null
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Make tier call budgets match measured actuals so budgets constrain work instead of decorating it (substantial budget 105.1 vs actual 53.3; median actual/budget 0.04)

## Acceptance Criteria

New budgets derived from measured percentiles per tier with the derivation shown; a check keeps budgets within a stated factor of rolling actuals. Negative scenario: budgets must not drop below p50 actuals — a budget that blocks legitimate work fails the check.

## Plan

## Rollback

## Journal
