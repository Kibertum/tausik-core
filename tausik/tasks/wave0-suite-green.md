---
slug: wave0-suite-green
title: "Green the 3 red tests in the 1.8 working tree before committing the batch"
status: done
epic: null
story: null
complexity: simple
role: qa
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "tests/test_state_export.py"
  - "tests/test_state_import.py"
  - "tests/test_skills_maturity.py"
  - "docs/_generated/constants.json"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T12:14:20Z"
---

## Goal

The full suite has 3 real failures from the uncommitted 1.8 batch: (1) test_check_docs_hook exit-0 fails on constants.json drift (regen fixes); (2) test_hook_encoding flags test_state_export.py:513 + test_state_import.py:321 decoding subprocess output without encoding='utf-8' (real defect the meta-gate caught); (3) test_skills_maturity test_copy_roles_copies_all asserts 6==5 — hardcoded role count not updated for devops (fix by deriving from the actual count, not bumping 5→6). Make the suite green with zero warnings before Wave-0 commit.

## Acceptance Criteria

1. test_state_export.py:513 + test_state_import.py:321 subprocess.run calls pass encoding='utf-8' so test_hook_encoding meta-gate passes. 2. test_skills_maturity.py::test_copy_roles_copies_all derives expected role set from harness/roles/*.md (no hardcoded count/list) and passes with devops present. 3. constants.json regenerated so test_check_docs_hook exit-0 passes. 4. Full suite: python -m pytest tests/ -q → 0 failed, 0 warnings.

## Plan

## Rollback

## Journal

- 2026-07-26T12:14:19Z [implementation] — AC verified: 1. ✓ encoding='utf-8' added to subprocess.run in test_state_export.py:513 + test_state_import.py:321; test_hook_encoding meta-gate passes 2. ✓ test_skills_maturity.test_copy_roles_copies_all now derives expected_roles from harness/roles/*.md (no hardcoded 5/list); passes with devops 3. ✓ gen_doc_constants --write; --check matches; test_check_docs_hook exit-0 passes 4. ✓ Full suite (background b5cbsczu6): 5942 passed, 24 skipped, 0 failed, 0 warnings in 581s
