---
slug: r14-task-gate-secure
title: "task_gate.py: SQLite direct + fail-secure mode flag (close fail-open loophole)"
status: done
epic: rel-14-readiness
story: rel-14-audit-fixes
complexity: medium
role: null
stack: null
tier: moderate
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T00:26:35Z"
---

## Goal

Release 1.4 readiness: r14-task-gate-secure

## Acceptance Criteria

1. task_gate.py reads .tausik/tausik.db directly via sqlite3 SELECT instead of subprocess + 5s timeout - faster, no subprocess flake. 2. New TAUSIK_HOOK_FAIL_SECURE=1 env var: when set, any DB error (corrupt, locked) blocks Write/Edit instead of fail-open. 3. Default behavior unchanged - DB error → allow (fail-open) when fail-secure not set. 4. Negative scenario - TAUSIK_HOOK_FAIL_SECURE=1 + DB unreadable → exit 2 with clear stderr message. 5. .tausik/ marker missing still allows (not a tausik project, hook is no-op).

## Plan

## Rollback

## Journal

- 2026-05-01T00:26:35Z [implementation] — AC verified: 1. SQLite SELECT replaces subprocess ✓ (test_no_subprocess_left_in_hook_source). 2. fail_secure flag added ✓ (test_fail_secure_blocks_on_db_error). 3. Default fail-open preserved ✓ (test_fail_open_default_on_db_error). 4. Negative scenario - TAUSIK_HOOK_FAIL_SECURE=1 + corrupt DB → exit 2 with stderr ✓. 5. Non-tausik project still no-op ✓ (test_no_tausik_dir_allows).
- 2026-05-01T00:26:35Z [implementation] — Rewrote scripts/hooks/task_gate.py: subprocess.run + 5s timeout → direct sqlite3 SELECT (sub-millisecond). TAUSIK_HOOK_FAIL_SECURE=1 env var added — when set, DB errors block instead of fail-open. 7 tests cover all paths.
