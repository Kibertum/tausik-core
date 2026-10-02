---
slug: shrink-ruff-format-ratchet-after-ci-isolation
title: "Shrink ruff format ratchet after CI isolation"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "One legacy ratchet entry"
scope_exclude: "Other gates and tests"
relevant_files:
  - "tausik/gates.json"
  - "tests/test_gate_ruff_format.py"
scope_paths:
  - "tausik/gates.json"
  - "tausik/tasks/shrink-ruff-format-ratchet-after-ci-isolation.md"
scope_tools: []
depends_on: []
completed_at: "2026-10-02T17:05:43Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: gpt-6-astra
started_model_version: null
done_model_id: gpt-6-astra
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Remove the now-formatted skill CLI test from the legacy ruff-format exception list.

## Acceptance Criteria

1. tests/test_skill_cli_help.py is absent from the ruff-format legacy list. 2. The ruff-format ratchet test passes. Negative: no other exception or gate setting changes.

## Plan

## Rollback

git revert the ratchet commit

## Journal

- 2026-10-02T17:05:39Z [implementation] — AC verified: AC-1: ✓ tausik/gates.json no longer lists tests/test_skill_cli_help.py. AC-2: ✓ tests/test_gate_ruff_format.py passed 6/6 and verify #3407 passed 30 selected nodes. Negative: the diff removes exactly one list entry and changes no gate setting.
