---
slug: preserve-dynamic-state-across-governance-refresh
title: "Preserve dynamic state across governance refresh"
status: done
epic: null
story: null
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: "Generated governance rule refresh and same-profile bootstrap regressions."
scope_exclude: "State generation semantics outside bootstrap and unrelated host adapters."
relevant_files:
  - "bootstrap/bootstrap_governance.py"
  - "tests/test_rules_generator_warning_parity.py"
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-04T13:41:08Z"
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

Preserve authoritative populated DYNAMIC state when refreshing pristine generated host rules.

## Acceptance Criteria

AC-1: Repeated full-profile bootstrap preserves the existing populated DYNAMIC body while refreshing pristine generated static content. AC-2 negative: customized and legacy files remain untouched, and an empty regenerated block cannot erase populated state. AC-3: focused tests pass.

## Plan

## Rollback

Revert DYNAMIC body preservation during pristine refresh.

## Journal

- 2026-10-04T13:40:47Z [implementation] — AC-1: pristine static refresh now merges the existing DYNAMIC interior into the newly stamped generated body. AC-2: ✓ tests/test_rules_generator_warning_parity.py::TestGeneratedRulesOwnership verifies populated state survives while new generated state is discarded; existing custom and legacy preservation tests remain green. AC-3: ✓ 11 focused tests passed. Domain: repeating a full-profile bootstrap cannot erase the current session/task state block.
- 2026-10-04T13:41:05Z [implementation] — AC-1: ✓ bootstrap/bootstrap_governance.py preserves the existing DYNAMIC body during pristine static refresh. AC-2: ✓ ownership tests prove populated state survives and customized/legacy rules remain protected. AC-3: ✓ verify #3504 passed 11 tests, 0 failed; 8 gates passed, hadolint skipped as not applicable. Domain: repeated full-profile bootstrap retains live governance state.
