---
slug: doc-constants-drift-resync
title: "docs/_generated/constants.json is out of sync with its generator — check_docs real-repo test red"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: null
tier: trivial
call_budget: 10
defect_of: null
scope: "docs/_generated/constants.json (generated)"
scope_exclude: "any source constant definitions — the JSON must follow them"
relevant_files:
  - "docs/_generated/constants.json"
  - README.md
  - README.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-25T06:45:24Z"
---

## Goal

The full suite fails on test_check_docs_hook.py::TestRealRepoSync::test_exit_0_when_in_sync: docs/_generated/constants.json does not match what scripts/gen_doc_constants.py --write produces. The file was already modified before session #137 and the handoff flagged doc-constants-drift-is-a-trap. Regenerate it from source, confirm the only delta is legitimately-changed constants (not hand edits), and get the real-repo sync test green so the batch can commit clean.

## Acceptance Criteria

1. docs/_generated/constants.json equals the output of `python scripts/gen_doc_constants.py --write` (byte-identical, deterministic). 2. The diff vs HEAD is inspected and every changed constant traces to a real source change (no stray/hand-edited values). 3. Negative/guard: test_check_docs_hook.py::TestRealRepoSync::test_exit_0_when_in_sync passes (the hook exits 0 on the synced repo). 4. No source .py constant is edited to force the match — the JSON follows the source, never the reverse.

## Plan

## Rollback

## Journal

- 2026-07-25T06:45:08Z [implementation] — Ran scripts/gen_doc_constants.py --write. Sole constants.json delta vs HEAD: test_count 5913->5982 (tests added in #135-136 + session-137 regression tests). Generator also refreshed the test-count badge/references in README.md + README.ru.md (5913->5982) — cross-file refs it owns; both were already M. No source .py constant touched (AC-4). test_check_docs_hook.py::TestRealRepoSync::test_exit_0_when_in_sync now PASSES (was the sole full-suite failure). Generator prints 'matches repository constants'.
- 2026-07-25T06:45:22Z [implementation] — AC verified: 1. ✓ gen_doc_constants.py --write prints 'OK constants.json matches repository constants' — file equals generator output 2. ✓ git diff shows the ONLY constants.json change is test_count 5913->5982; README delta is the same value in the badge/refs — all trace to added tests, no hand edits 3. ✓ Negative/guard: tests/test_check_docs_hook.py::TestRealRepoSync::test_exit_0_when_in_sync — 1 passed (was the sole full-suite failure) 4. ✓ no source .py constant edited — only the generated JSON + generator-owned README cross-refs changed
