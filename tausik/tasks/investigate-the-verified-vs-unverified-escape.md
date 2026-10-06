---
slug: investigate-the-verified-vs-unverified-escape
title: "Investigate the verified-vs-unverified escape paradox and risk-backtest AUC"
status: planning
epic: release-1-11-3
story: release1113-hygiene-calibration
complexity: null
role: qa
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

Explain why verified tasks escape defects more often than unverified ones (9.8% vs 1.5%) and whether the risk score discriminates at all (AUC 0.5364 = coin flip); land a fix or a recorded decision

## Acceptance Criteria

Written diagnosis with numbers from the tasks table (sample sizes, windows); either a fix (recalibrated risk score or changed verify policy) or a documented decision to keep as-is. Negative scenario: if the paradox is a small-sample artifact the conclusion names the sizes and the statistical test used, not a hand-wave.

## Plan

## Rollback

## Journal
