---
slug: fix-1-11-3-published-claims-spec-code-parity-21
title: "Fix 1.11.3 published claims: SPEC/code parity, 21.4x derivation, missing references"
status: planning
epic: null
story: null
complexity: null
role: tech-writer
stack: python
tier: null
call_budget: null
defect_of: r1112-pooled-verification-proof-and-rollout
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

Make the published 1.11.3 claims match the implementation: EN SPEC diverges from code and its RU mirror (member-status-drift, v75 columns, SS3), the 21.4x headline is not derivable from any published pair, the new pooled MCP tools and CLI flags are missing from the references, and stale 152/62KB figures survived the 149 edit.

## Acceptance Criteria

AC-1: EN SPEC matches code and RU mirror: member statuses in SS1, member-status-drift in SS4, v75 column named cohort_identity (not cohort_id/cohort_size), SS3 marked honestly if the fine-grained set stays unwired. AC-2: the 21.4x claim either carries a published derivation (which gate-execution counts produced it) or is replaced by the derivable 34x executions / 4.7x wall in all four surfaces (CHANGELOG en+ru, SPEC en+ru). AC-3: mcp.md en+ru gain tausik_verify_cohort/tausik_verify_hierarchy rows and story/epic done verify_handle args; cli-quality.md documents verify --tasks/--story/--epic; cli-tasks.md documents story/epic done --verify-handle; configuration.md documents memory_tail_by_relevance. AC-4: stale numbers corrected: main 149 count line, 58KB/14.8k surface-cost figure, 'memory archive --confirm' naming. AC-5 negative: no number published without its denominator; en/ru rows agree cell-for-cell (doc parity check green).

## Plan

## Rollback

## Journal
