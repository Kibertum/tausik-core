---
slug: v133-impl
title: "Implement v1.3.3 brain init anti-hallucination guards"
status: done
epic: v133-anti-hallucination
story: brain-init-guards
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-28T10:06:38Z"
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

Refactor brain_init wizard to detect existing canonical BRAIN databases via workspace search, add --join-existing and --force-create flags, update SKILL.md and docs to enforce one-set-per-workspace architecture

## Acceptance Criteria

## Plan

## Rollback

## Journal

- 2026-04-28T10:06:37Z [planning] — Shipped commit 8d9fe76. 16 new tests, 2270 total pass. SKILL.md ARCHITECTURE block + docs Common Mistakes section.
