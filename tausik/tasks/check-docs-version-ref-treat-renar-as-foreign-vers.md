---
slug: check-docs-version-ref-treat-renar-as-foreign-vers
title: "check_docs version-ref: treat RENAR as foreign version (false-positive on renar.tech v1.0-draft in CLAUDE.md memory-tail)"
status: done
epic: null
story: null
complexity: null
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/doc_drift_scanners.py (_FOREIGN_VERSION_PREFIXES), tests for doc_drift_scanners"
scope_exclude: null
relevant_files:
  - "scripts/doc_drift_scanners.py"
  - "tests/test_gen_doc_constants.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-13T23:30:38Z"
---

## Goal

scan_version_refs flags 'v1.0' inside 'renar.tech v1.0-draft' (CLAUDE.md auto-gen memory-tail decision #103) as TAUSIK-version drift, blocking all commits. RENAR is a sibling spec versioning independently — exactly the foreign-version case already handled for SENAR/Python/OWASP. Add RENAR/renar to _FOREIGN_VERSION_PREFIXES + regression test.

## Acceptance Criteria

1. _FOREIGN_VERSION_PREFIXES includes RENAR + renar so 'renar.tech v1.0-draft' / 'RENAR v1.0' refs are skipped. 2. NEGATIVE: a genuine TAUSIK vX.Y drift (e.g. 'v1.0' with no foreign prefix) is STILL flagged. 3. Regression test asserts scan_version_refs does not flag the renar.tech memory-tail line. 4. test_check_docs_hook::test_exit_0_when_in_sync passes on live repo. 5. All gates green.

## Plan

## Rollback

git revert; single-line tuple addition + one test, fully additive

## Journal

- 2026-06-13T23:30:17Z [implementation] — Fix: added RENAR+renar to _FOREIGN_VERSION_PREFIXES (24-char lookbehind catches 'renar.tech ' before v1.0). Tests: test_scan_version_refs_skips_renar_foreign (positive: renar.tech v1.0-draft + RENAR v1.0 not flagged), test_scan_version_refs_still_flags_native_drift_near_renar (NEGATIVE: bare v1.0 w/o foreign prefix still drifts). check_docs hook test now green (42 passed). ruff+mypy clean. Trivial 1-line tuple change → self-reviewed, no subagent.
- 2026-06-13T23:30:37Z [implementation] — AC verified: 1.✓ RENAR/renar in _FOREIGN_VERSION_PREFIXES (doc_drift_scanners.py:128). 2.✓ NEGATIVE bare v1.0 still flagged: tests/test_gen_doc_constants.py::test_scan_version_refs_still_flags_native_drift_near_renar. 3.✓ regression: ::test_scan_version_refs_skips_renar_foreign. 4.✓ tests/test_check_docs_hook.py::TestRealRepoSync::test_exit_0_when_in_sync passes (42 passed). 5.✓ ruff+mypy clean, verify run #750 pytest PASS.
