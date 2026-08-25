---
slug: sync-doc-test-count-constants-3933-3960
title: "Sync doc test-count constants 3933->3960"
status: done
epic: null
story: null
complexity: null
role: tech-writer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-13T22:31:14Z"
---

## Goal

gen_doc_constants regenerated test_count 3933->3960 (25 tests from session #86 never synced + 2 from fix-drift1-delta-crash); README badge/bold/prose and constants.json must match or check_docs hook test fails (test_check_docs_hook::test_exit_0_when_in_sync). Doc-only sync.

## Acceptance Criteria

1. constants.json test_count=3960. 2. README.md all 4 occurrences of 3933 -> 3960 (badge label+url, bold, prose). 3. NEGATIVE: check_docs hook test passes — test_check_docs_hook.py::TestRealRepoSync::test_exit_0_when_in_sync green (was failing on drift). 4. No source/test behavior change.

## Plan

## Rollback

## Journal

- 2026-06-13T22:31:04Z [implementation] — AC verified: 1.✓ constants.json test_count=3960 (gen_doc_constants.py). 2.✓ README 3933->3960 all 4 occurrences (badge label+url, bold line111, prose line184); '3933 left: 0'. 3.✓ NEGATIVE tests/test_check_docs_hook.py::TestRealRepoSync::test_exit_0_when_in_sync now passes (was failing on cross-file drift). 4.✓ doc-only, no source/test logic touched.
- 2026-06-13T22:31:14Z [implementation] — AC verified: 1.✓ constants.json test_count=3960 (gen_doc_constants.py). 2.✓ README 3933->3960 all 4 occurrences; '3933 left: 0'. 3.✓ NEGATIVE test_check_docs_hook::test_exit_0_when_in_sync passes (was failing on drift). 4.✓ doc-only.
