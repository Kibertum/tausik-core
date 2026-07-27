---
slug: gate-integrity-tests
title: "Behavioral tests for gate_test_citation.py + gate_tdd_order.py"
status: planning
epic: null
story: null
complexity: medium
role: qa
stack: null
tier: moderate
call_budget: 45
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
completed_at: null
---

## Goal

Close the highest process-integrity coverage hole: gate_test_citation.py (Rule 5, anti-fabrication — decides whether a claimed test citation resolves to a real test) and gate_tdd_order.py (72L) are registered but have zero behavioral tests. Add tests that would catch a regression accepting a citation to a non-existent test / an inverted TDD-order verdict.

## Acceptance Criteria

## Plan

## Rollback

## Journal
