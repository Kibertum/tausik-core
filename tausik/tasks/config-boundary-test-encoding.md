---
slug: config-boundary-test-encoding
title: "test_config_module_boundary subprocess reads use parent locale encoding — add encoding=utf-8"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: trivial
call_budget: 6
defect_of: project-config-god-module-split
scope: "tests/test_config_module_boundary.py only"
scope_exclude: null
relevant_files:
  - "tests/test_config_module_boundary.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T14:04:05Z"
---

## Goal

Full-suite guard test_hook_encoding::test_no_test_reads_a_subprocess_in_the_parents_encoding flags test_config_module_boundary.py:50 and :61 — the two subprocess.run(..., text=True) calls decode child output in the parent's locale encoding (cp1252 on Windows) instead of utf-8, making them dependent on pytest launch flags. Add encoding='utf-8' to both, matching the project convention (hook-stderr-encoding-locale-dependent).

## Acceptance Criteria

1. Both subprocess.run calls in tests/test_config_module_boundary.py (test_project_config_imports_without_db_layer, test_service_factory_still_requires_db_layer) pass encoding='utf-8'. 2. test_hook_encoding::test_no_test_reads_a_subprocess_in_the_parents_encoding passes (offenders list empty for this file). 3. The boundary tests still pass (edge-broken proof intact). NEGATIVE: 4. Guard is green regardless of pytest launch flags / parent locale — the tests no longer depend on ambient encoding.

## Plan

## Rollback

git revert — trivial 2-line test change.

## Journal

- 2026-07-26T14:03:27Z [implementation] — Root cause (other/convention-miss): the new boundary test's subprocess.run calls used text=True without encoding='utf-8', so they decoded child output in the parent's locale codepage (cp1252 on Windows) — violating the project convention that subprocess reads must pin utf-8 (hook-stderr-encoding-locale-dependent). Missed because the scoped verify for #34 didn't run test_hook_encoding (the AST guard lives in a different file than the code under test); only the full suite catches cross-file guard tests. Prevention: when adding a test that shells out, pin encoding='utf-8'; and run the full suite (not just scoped) before considering a task with new subprocess-spawning tests fully closed.
- 2026-07-26T14:04:03Z [implementation] — AC verified: 1. ✓ both subprocess.run calls in test_config_module_boundary.py now pass encoding='utf-8' 2. ✓ test_hook_encoding::test_no_test_reads_a_subprocess_in_the_parents_encoding passes (offenders empty) 3. ✓ boundary tests still pass (6 passed incl edge-broken proof) 4. ✓ encoding pinned utf-8 → independent of pytest launch flags / parent locale
