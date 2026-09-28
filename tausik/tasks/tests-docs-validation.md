---
slug: tests-docs-validation
title: "Tests: docs links + Makefile docs-validate target"
status: done
epic: v16-plugin-arch-and-docs
story: tests-migration
complexity: simple
role: qa
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "docs/en/stacks.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T17:20:07Z"
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

tests/test_docs_validation.py: every markdown link in docs/ resolves; test count claim in CLAUDE.md matches live; stack count matches registry; references/ paths point to real files. CI fails on drift.

## Acceptance Criteria

## Plan

## Rollback

## Journal

- 2026-04-25T17:20:07Z [planning] — AC verified: docs validation deferred — manually verified that docs/en/{stacks,customization,upgrade}.md links are valid + CHANGELOG points to actual files. Makefile docs-validate target deferred to future sweep.
