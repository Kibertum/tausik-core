---
slug: v34-backfill-return-0-not-partial-count-after-mid-
title: "v34 backfill: return 0 (not partial count) after mid-loop rollback"
status: done
epic: null
story: null
complexity: null
role: developer
stack: python
tier: null
call_budget: null
defect_of: test-v34-hashchain-backfill
scope: "scripts/backend_migrations_v34.py, tests/test_v34_hashchain_backfill.py"
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T09:30:54Z"
---

## Goal

Adversarial reviewer found: maybe_backfill_v34 (backend_migrations_v34.py:81) returns the accumulated 'sealed' counter even when a mid-loop sqlite3.Error triggers rollback — so the caller sees N 'sealed' rows when 0 were actually committed (DB is correct via rollback, but the return value lies, and the v34 test suite has no rollback-path test). Fix: return 0 on any rollback path; add a test that injects an error mid-backfill and asserts return==0, meta flag unset, stored links unchanged.

## Acceptance Criteria

1. maybe_backfill_v34 returns 0 (not the partial 'sealed' count) when a sqlite3.Error mid-loop triggers rollback. 2. Negative/boundary: after rollback the meta flag v34_backfilled stays UNSET (a later run retries) and stored entry_hash/prev_hash are unchanged (no partial seal persisted). 3. Happy path unchanged: a fully successful backfill still returns the true sealed count and sets the flag. 4. New test injects a mid-loop failure (monkeypatch events_chain.entry_hash to raise after the first row) and asserts return==0, flag is None, stored links unchanged. 5. pytest + ruff + mypy clean, bootstrap re-run.

## Plan

## Rollback

git revert — one-line return change + one test

## Journal

- 2026-06-14T09:30:32Z [implementation] — Root cause (category=correctness): maybe_backfill_v34 accumulated 'sealed' across the loop and had a single `return sealed` after the try/except, so the except (rollback) path fell through to it and returned the partial in-loop count — even though rollback committed nothing. DB stayed correct (rollback) but the return value lied. Fix: explicit `return 0` inside the except after rollback. Prevention: a function that mutates inside a transaction must return a committed-count, not an in-progress counter; the rollback path needs its own return.
- 2026-06-14T09:30:39Z [implementation] — AC verified: AC-1: ✓ returns 0 on mid-loop sqlite3.Error rollback — tested via tests/test_v34_hashchain_backfill.py::test_midloop_error_rolls_back_and_returns_zero. AC-2: ✓ Negative/boundary: after rollback meta flag is None and both rows' stored links stay (None,None) — same test asserts _meta_flag is None and _stored_links unchanged. AC-3: ✓ happy path unchanged — test_seals_unsealed_chain_from_genesis (3 sealed, flag set) + 6 other v34 tests green. AC-4: ✓ test injects failure via monkeypatch events_chain.entry_hash raising on 2nd row. AC-5: ✓ 7 v34 tests pass, ruff + mypy clean (198 files), bootstrap re-run. Domain: rollback genuinely undoes the first row's partial UPDATE (asserted via stored links), so the return-0 matches the real committed state.
