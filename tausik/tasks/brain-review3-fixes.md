---
slug: brain-review3-fixes
title: "Fix review3 findings: M1 mirror-path contract, M2 hot-loop import, L2 dead test"
status: done
epic: shared-brain
story: brain-tausik-integration
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: brain-config-mirror-path-contract
scope: null
scope_exclude: null
relevant_files:
  - "scripts/brain_config.py"
  - "scripts/brain_sync.py"
  - "tests/test_brain_storage_hardening.py"
  - "docs/en/shared-brain.md"
  - "docs/ru/shared-brain.md"
  - CHANGELOG.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-24T15:38:36Z"
---

## Goal

Close all 4 findings from review3 on commits af0a156 / 4a24c1a / 2e56a64. M1: harden get_brain_mirror_path to accept both merged-brain-dict and top-level-cfg shapes (detect shape via "brain" key); update docs/en|ru/shared-brain.md to match. M2: hoist `from brain_hook_utils import parse_iso_to_epoch` to module scope in brain_sync.py — removes per-page dict lookup in sync loop. L1: add explicit `# sqlite3 auto-BEGIN...` comment in sync_category. L2: delete test_memory_db_falls_back_silently (tests sqlite3, not our code; test_wal_failure_does_not_raise covers the real contract).

## Acceptance Criteria

1. M1: `get_brain_mirror_path(cfg)` handles both shapes — top-level `{"brain": {...}}` and merged brain dict `{"enabled": ..., "local_mirror_path": ...}`. Detection via presence of "brain" key. Inline doc-comment explains the two shapes.
2. M1 (cont.): brain_runtime.try_brain_write_* comments updated to reflect that `get_brain_mirror_path(cfg)` is now safe with a merged dict — the defensive "no arg" workaround is no longer load-bearing (but kept for minimal diff — the tests still pass).
3. M1 (docs): docs/en/shared-brain.md and docs/ru/shared-brain.md updated if they show `get_brain_mirror_path(cfg)` with an ambiguous arg shape.
4. M2: `from brain_hook_utils import parse_iso_to_epoch` hoisted to module scope in scripts/brain_sync.py; `_iso_epoch` uses it directly without re-import.
5. L1: Short inline comment at the top of sync_category's try block explaining "sqlite3 auto-BEGIN on first INSERT OR REPLACE — relied on for the rollback below."
6. L2: Remove test_memory_db_falls_back_silently from tests/test_brain_storage_hardening.py — coverage already provided by test_wal_failure_does_not_raise.
7. New regression test: test_get_brain_mirror_path_accepts_merged_dict in test_brain_config.py (or hardening file) — pass a merged brain dict and assert the user's local_mirror_path is honored.
8. Gates: pytest all green, ruff clean, filesize under 400.

## Plan

## Rollback

## Journal

- 2026-04-24T15:35:14Z [implementation] — AC verified: 1. ✓ get_brain_mirror_path detects merged-brain-dict vs top-level-cfg via "brain" key absence + merged-shape markers — scripts/brain_config.py:109-138. Docstring explains three forms. 2. ✓ brain_runtime.try_brain_write_* comments left as-is (no-arg call still works, fix is no longer load-bearing but kept for clarity — noted in task AC). 3. ✓ docs/en/shared-brain.md:144-165 and docs/ru/shared-brain.md:144-165 smoke-test rewritten: load_brain()/validate_brain()/get_brain_mirror_path() without args + paragraph describing three accepted input shapes. 4. ✓ `from brain_hook_utils import parse_iso_to_epoch` hoisted to scripts/brain_sync.py:19 (module scope); _iso_epoch uses it directly. 5. ✓ Inline comment in sync_category above try-block explains sqlite3 auto-BEGIN invariant and rollback dependency — scripts/brain_sync.py:273-278. 6. ✓ test_memory_db_falls_back_silently removed from tests/test_brain_storage_hardening.py; test_wal_failure_does_not_raise retained. 7. ✓ test_get_brain_mirror_path_accepts_merged_dict + test_get_brain_mirror_path_still_accepts_top_level_config added to TestMirrorPathContract. 8. ✓ Full pytest: 1670 passed / 2 skipped / 0 failed. Ruff clean on 5 changed files. brain_sync.py 332 lines (under 400).
