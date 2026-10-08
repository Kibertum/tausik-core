---
slug: test-dedupe-gate-measures-the-framework-not-the-project
title: "test_dedupe gate in a consumer project measures the framework's own tests"
status: done
epic: release-110-deferred-from-19
story: release110-owner-priorities
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/gate_test_dedupe.py"
  - "scripts/gate_project_root.py"
  - "tests/test_demo_caught_lie.py"
  - "changelog.d/test-dedupe-gate-measures-the-framework-not-the-project.md"
scope_paths:
  - "scripts/"
  - "tests/"
  - "changelog.d/"
scope_tools: []
depends_on: []
completed_at: "2026-09-29T21:38:53Z"
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

Found session #279: in tests/test_tausik_cli.py the temporary project (tmp_path, no tests/) ran task done --verify and the test_dedupe gate reported the TAUSIK repository's groups (tests/test_audit_stale_docs.py:85 ...) and its baseline 283. A consumer project's close is therefore refused by growth in the framework's test tree, and a framework test that adds a structurally similar test turns every consumer close red.

## Acceptance Criteria

AC-1 The gate measures the tests of the project being verified (its root), not of the installed framework. AC-2 NEGATIVE: a project with no tests/ gets NOT_APPLICABLE with a reason, not the framework's verdict. AC-3 A test runs the gate from a temp project while the framework baseline is exceeded and it stays green.

## Plan

## Rollback

git revert

## Journal

- 2026-09-29T21:38:11Z [implementation] — Fixed inside demo-of-a-caught-lie-as-first-touch (the demo exposed it): gate_test_dedupe._repo_root now resolves via gate_project_root.project_root(). AC-1: ✓ tests/test_demo_caught_lie.py::test_ruff_format_and_dedupe_measure_the_consumer_not_the_framework. AC-2: ✓ tests/test_demo_caught_lie.py::test_dedupe_in_a_consumer_measures_the_consumer_whatever_the_framework_owes (NOT ADOPTED, measured 0 groups — the gate's own not-applicable form). AC-3: ✓ same test: framework baseline irrelevant, consumer close stays green.
