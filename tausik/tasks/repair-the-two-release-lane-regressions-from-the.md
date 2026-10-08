---
slug: repair-the-two-release-lane-regressions-from-the
title: "Repair the two release-lane regressions from the kilo-zai branch"
status: done
epic: null
story: null
complexity: null
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "tausik/gates.json"
  - "tests/test_host_gate_plugins.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-06T20:50:21Z"
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

The full default lane on the 1.11.2 release commit fails two gate-hygiene tests introduced by this branch: the ruff-format legacy list still names tests/test_session_model_id.py that 7c25c154 already formatted, and tests/test_host_gate_plugins.py from e4279117 walks harness plugin trees without a CROSSCUTTING_SCOPE declaration. Repair both so the release ships a green lane.

## Acceptance Criteria

1) tests/test_gate_ruff_format.py::test_the_legacy_list_only_shrinks passes with tests/test_session_model_id.py removed from tausik/gates.json. 2) tests/test_crosscutting_registry.py::TestCrosscuttingVisibility::test_new_tree_iterator_must_declare_or_optout passes with CROSSCUTTING_SCOPE declared in tests/test_host_gate_plugins.py covering the trees it actually walks. 3) Negative: the full default lane reports zero failed, with passed, skipped and deselected denominators stated.

## Plan

## Rollback

## Journal

- 2026-10-06T20:50:17Z [implementation] — AC-1: check test_the_legacy_list_only_shrinks green after removing the stale entry (71 to 70) from tausik/gates.json. AC-2: check test_new_tree_iterator_must_declare_or_optout green with CROSSCUTTING_SCOPE = harness declared in test_host_gate_plugins. AC-3: check negative proven: full default lane 12910 passed 37 skipped 143 deselected zero failed; slow lane 143 passed 12947 deselected.
- 2026-10-06T20:50:35Z [done] — AC-1: check tests/test_gate_ruff_format.py::test_the_legacy_list_only_shrinks. AC-2: check tests/test_crosscutting_registry.py::TestCrosscuttingVisibility::test_new_tree_iterator_must_declare_or_optout. AC-3: check full lane pytest tests -q and slow lane pytest -m slow -q, denominators in prior log.
