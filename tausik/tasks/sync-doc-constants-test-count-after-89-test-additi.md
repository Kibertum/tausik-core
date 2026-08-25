---
slug: sync-doc-constants-test-count-after-89-test-additi
title: "sync doc constants test-count after #89 test additions"
status: done
epic: null
story: null
complexity: null
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "docs/_generated/constants.json (and any doc embedding the test count)"
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T10:02:18Z"
---

## Goal

Adding test_v34_hashchain_backfill.py and test_ac_parser_inline.py in #89 increased the live test count, so docs/_generated/constants.json (which pins the count) drifted — test_gen_doc_constants::test_constants_json_file_matches_live and test_check_docs_hook::test_exit_0_when_in_sync now fail. Regenerate constants.json from live via `tausik doc constants` so both doc-sync tests pass; include the regenerated artifact in the #89 commit.

## Acceptance Criteria

1. docs/_generated/constants.json regenerated from live via `tausik doc constants` (test count reflects the two new #89 test files). 2. test_gen_doc_constants::test_constants_json_file_matches_live passes. 3. test_check_docs_hook::TestRealRepoSync::test_exit_0_when_in_sync passes (any doc embedding the count is in sync). 4. Negative/boundary: `tausik doc constants --check` reports CLEAN (no residual drift); no unintended fields changed in constants.json beyond the count. 5. Full pytest green, no new ruff/mypy issues.

## Plan

## Rollback

git checkout docs/_generated/constants.json

## Journal

- 2026-06-14T10:02:10Z [implementation] — AC verified: 1. ✓ constants.json regenerated via `tausik doc constants` (test_count 4037->4062) — git diff shows only test_count changed. 2. ✓ test_gen_doc_constants::test_constants_json_file_matches_live passes. 3. ✓ test_check_docs_hook::test_exit_0_when_in_sync passes; README.md count synced 4037->4062 in 3 places (badge+bold+prose). 4. ✓ Negative: `tausik doc constants --check` reports CLEAN, no residual cross-file drift; diff confirms only test_count field changed in constants.json. 5. ✓ 42 doc-sync tests pass; no ruff/mypy touched (data/doc only). Domain: the pinned count now matches the live collected test count after adding test_v34 + test_ac_parser_inline.
