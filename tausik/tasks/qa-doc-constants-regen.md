---
slug: qa-doc-constants-regen
title: "Fix RED suite: regenerate stale docs/_generated/constants.json (test_count drift)"
status: done
epic: v15-polish
story: v15p-debt
complexity: simple
role: qa
stack: python
tier: trivial
call_budget: 10
defect_of: null
scope: "docs/_generated/constants.json (regenerated) + README.md test-count badges/bold (same generated-count consumer)"
scope_exclude: "scripts/*, tests/* (no source/test edits)"
relevant_files:
  - "docs/_generated/constants.json"
  - README.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T12:20:01Z"
---

## Goal

Restore green test suite by regenerating the stale generated constants artifact. The committed docs/_generated/constants.json has test_count=4062 but live=4083, causing 2 deterministic failures (test_gen_doc_constants + check_docs_hook RealRepoSync). Generated-artifact drift, not a code regression.

## Acceptance Criteria

AC-1: python scripts/gen_doc_constants.py regenerates docs/_generated/constants.json with test_count matching live (4083). AC-2: tests/test_gen_doc_constants.py::test_constants_json_file_matches_live passes. AC-3: tests/test_check_docs_hook.py::TestRealRepoSync::test_exit_0_when_in_sync passes (incl. README cross-file count sync). Negative: no scripts/*.py or tests/*.py file modified (only generated json + README counts); git diff confirms.

## Plan

## Rollback

## Journal

- 2026-06-14T12:19:42Z [implementation] — Regenerated docs/_generated/constants.json via gen_doc_constants.py (test_count 4062→4083). check_docs cross-file check also flagged README.md badges/bold (4062→4083 at L10,111,184) — same generated-count drift, synced via sed. Scope widened from json-only to include README.md (a doc consumer of the count, NOT source/test — scope_exclude respected). tests/test_gen_doc_constants.py + tests/test_check_docs_hook.py: 42 passed. NOTE: if this session adds tests, re-run gen_doc_constants.py before commit to re-sync.
- 2026-06-14T12:20:01Z [implementation] — AC verified: 1. ✓ gen_doc_constants.py wrote constants.json test_count 4062→4083 (git diff confirms single-line change) 2. ✓ tests/test_gen_doc_constants.py::test_constants_json_file_matches_live PASS (was FAIL) 3. ✓ tests/test_check_docs_hook.py::TestRealRepoSync::test_exit_0_when_in_sync PASS after README cross-file count sync; 42 passed in test_gen_doc_constants+test_check_docs_hook 4. ✓ Negative: git status shows only docs/_generated/constants.json + README.md modified (plus pre-existing CLAUDE.md); zero scripts/*.py or tests/*.py touched
