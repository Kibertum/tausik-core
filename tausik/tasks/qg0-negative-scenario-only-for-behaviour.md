---
slug: qg0-negative-scenario-only-for-behaviour
title: "QG-0 demands a negative scenario from a task whose scope is only prose — the rule shipped this morning says it should not"
status: done
epic: release-19-renar-conformance
story: test-evidence-not-test-volume
complexity: simple
role: developer
stack: python
tier: light
call_budget: 15
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/gate_qg0_check.py"
  - "tests/test_qg0_prose_only_scope.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - ROADMAP.md
scope_paths:
  - "scripts/gate_qg0_check.py"
  - "tests/test_qg0_prose_only_scope.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - ROADMAP.md
scope_tools: []
depends_on: []
completed_at: "2026-09-14T14:01:58Z"
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

Session #264, first task after the rule landed: a logo/README task with scope_paths of images, Markdown and one test file was refused by QG-0 with 'AC has no negative scenario', while HARD_CONSTRAINTS now says work that changes only prose need not name one (decision #371). The rules file and the gate disagree — the exact 'said wider than done' defect 1.9 was built against. Fix: gate_qg0_check skips the negative-scenario refusal when the task declares scope_paths and every path is prose (.md/.txt/.rst, anything under docs/, and images .png/.jpg/.svg — an asset carries no behaviour either); an undeclared scope or any code path keeps the refusal. The refusal text stays byte-identical (tests/test_agent_quickstart.py pins it).

## Acceptance Criteria

AC-1: a task with scope_paths ['docs/assets/x.png', 'README.md', 'tests/test_x.py'] and an AC without a negative scenario passes QG-0. AC-2 (negative): the same AC with scope_paths ['scripts/x.py'] is still refused with 'AC has no negative scenario'; the same AC with NO scope_paths is still refused. AC-3: the refusal string is unchanged (tests/test_agent_quickstart.py green).

## Plan

## Rollback

git revert; one branch in gate_qg0_check

## Journal

- 2026-09-14T14:01:06Z [implementation] — AC-1 ✓ tests/test_qg0_prose_only_scope.py::test_a_prose_and_assets_scope_passes_without_a_negative_scenario. AC-2 ✓ (NEGATIVE) ::test_any_other_scope_is_still_refused[undeclared|code|prose-plus-code|tests-only] — four refusals kept. AC-3 ✓ tests/test_agent_quickstart.py green (refusal string pinned there, unchanged). Deployed via bootstrap --ide all.
