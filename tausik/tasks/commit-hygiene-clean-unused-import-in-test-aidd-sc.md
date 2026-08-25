---
slug: commit-hygiene-clean-unused-import-in-test-aidd-sc
title: "Commit hygiene: clean unused import in test_aidd_scaffold to unblock commit gate"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-06T10:34:42Z"
---

## Goal

Remove unused `import pytest` from tests/test_aidd_scaffold.py (ruff F401 blocker) so the v1.4-polish bundle commit can pass commit gates and land 4 closed tasks (active-time + stdin-hang + t13-prompt-caching-docs + aidd-scaffold).

## Acceptance Criteria

1. tests/test_aidd_scaffold.py no longer has `import pytest` line. 2. ruff check on the file passes (no F401). 3. 14 existing tests in test_aidd_scaffold.py still pass (pytest still importable transitively via fixtures). 4. gate_runner commit on the staged set no longer reports the F401 ruff failure. 5. Negative: if a test in the file actually USES `pytest.raises` / `pytest.fixture` / etc., the import must NOT be removed — re-add and adjust scope. (Current file inspection shows no such usage; this AC enforces verification before deletion.)

## Plan

## Rollback

## Journal

- 2026-05-06T10:34:25Z [implementation] — AC verified: 1. ✓ `import pytest` removed from tests/test_aidd_scaffold.py and tests/test_validate_prompt_caching.py (scope expanded mid-task — second F401 surfaced after first was fixed). 2. ✓ `python -m ruff check` on both files: "All checks passed!". 3. ✓ Tests pass: test_aidd_scaffold 14/14 in 0.18s; test_validate_prompt_caching 11/11 in 0.19s. 4. ✓ `gate_runner commit` — ruff now [PASS]; F401 no longer in failure list. 5. ✓ Negative AC: grep `pytest\.` in both files returned No matches found before deletion — no fixture/raises/parametrize usage that would have required keeping the import.
