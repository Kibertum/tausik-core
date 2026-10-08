---
slug: split-the-three-registry-surfaces-over-the-line
title: "Split the three registry surfaces over the line cap"
status: planning
epic: null
story: null
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

backend_schema.py (514), project_parser.py (521) and backend_migrations.py (502) crossed the 500-line filesize cap and were exempted in gates.json with this task named as the retainer. Split each along its natural seam (DDL per domain / parser per command family / migration registry stays one line per version) so the exemptions can be removed.

## Acceptance Criteria

1) All three files back under 500 lines with the gates.json exempt_files entries removed. 2) Parity gates (check_schema_migration_parity, ddl parity, parser wiring) stay green. 3) NEGATIVE: no behavior change — full default lane green.

## Plan

## Rollback

## Journal
