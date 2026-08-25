---
slug: hotfix-skill-bundles-skip-must-not-change-test-cou
title: "Hotfix: skill_bundles skip must not change test_count (replace module-level skip with skipif)"
status: done
epic: null
story: null
complexity: null
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "tests/test_skill_bundles.py"
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-07T21:18:08Z"
---

## Goal

Previous hotfix used pytest.skip(allow_module_level=True) — this excludes tests from collection so pytest_test_count returns 3356 in CI (skills-official absent) vs 3378 in repo's constants.json → doc-constants drift check fails. Replace with @pytest.mark.skipif at module/class level that DOES preserve collection count, only skipping at run time. Fix yields identical test_count in both environments.

## Acceptance Criteria

AC-1: tests/test_skill_bundles.py — replace module-level pytest.skip(allow_module_level=True) with pytestmark = pytest.mark.skipif(not BUNDLES_PATH.exists(), ...) so collection still includes all tests; AC-2 (negative): if skills-official/bundles.json absent, all tests in file are reported as SKIPPED (not deselected/missing) and pytest --collect-only count remains 3378; AC-3: pytest --collect-only --override-ini="addopts=" yields 3378 locally regardless of whether skills-official/ exists; AC-4: doc-constants drift check `python scripts/gen_doc_constants.py --check` exits 0 in CI (verified by next push).

## Plan

## Rollback

## Journal

- 2026-05-07T21:18:02Z [implementation] — AC-1: ✓ Replaced module-level pytest.skip(allow_module_level=True) with pytestmark = pytest.mark.skipif at module top. AC-2: ✓ collection preserves all 22 tests in file regardless of skills-official presence (verified: pytest --collect-only --override-ini='addopts=' → 22 tests collected in test_skill_bundles.py). AC-3: ✓ full-suite collect-only returns exactly 3378 (matches constants.json). Local scoped run with skills-official present: 22/22 PASS, ruff green. AC-4 verifiable on next CI push.
