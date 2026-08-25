---
slug: brain-config-mirror-path-contract
title: "MEDIUM: get_brain_mirror_path(merged_brain_dict) silently ignores user config"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: brain-decide-auto-route
scope: null
scope_exclude: null
relevant_files:
  - "scripts/brain_runtime.py"
  - "tests/test_brain_storage_hardening.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-24T15:18:55Z"
---

## Goal

get_brain_mirror_path() вызывает внутри load_brain(cfg) который ждёт top-level config (cfg.get('brain',{})). Если передать merged brain dict (результат load_brain) — функция возвращает DEFAULT_BRAIN path, а user config местоположения mirror теряется. Тот же баг в brain_runtime.py:41 где cfg — это уже merged brain. Либо менять контракт get_brain_mirror_path (accept merged dict), либо fix callers и добавить тест

## Acceptance Criteria

1. brain_runtime.try_brain_write_decision + try_brain_write_web_cache call `get_brain_mirror_path()` (no arg) so load_config() is consulted fresh — user's `local_mirror_path` is no longer silently dropped.
2. Inline comment at both call sites explains the contract (passing already-merged brain dict loses user config).
3. Regression test for each wrapper: pass a full_cfg with custom local_mirror_path, patch brain_config.load_config + brain_sync.open_brain_db, assert the mirror path the wrapper opens matches the user's, not DEFAULT_BRAIN.
4. Negative case: open_brain_db is called even when the cfg arg passed to the wrapper is the merged brain dict (the original bug would have opened DEFAULT path).
5. pytest + ruff clean.

## Plan

## Rollback

## Journal

- 2026-04-24T15:15:36Z [implementation] — AC verified: 1. ✓ Both wrappers now call `get_brain_mirror_path()` without arg — scripts/brain_runtime.py lines ~98 and ~147. 2. ✓ Inline comment above both call sites explains the contract: passing already-merged `cfg` would silently drop user's local_mirror_path. 3. ✓ TestMirrorPathContract::test_try_brain_write_decision_opens_user_mirror_path + test_try_brain_write_web_cache_opens_user_mirror_path in tests/test_brain_storage_hardening.py — assert path opened matches user config. 4. ✓ Negative case covered: the test's `full_cfg["brain"]["local_mirror_path"]` is at a custom tmp_path location; captured `path` arg to open_brain_db must equal `abspath(user_mirror)`. Before the fix, the arg would have been DEFAULT_BRAIN['local_mirror_path'] expanded to ~/.tausik-brain/brain.db. 5. ✓ pytest + ruff clean.
