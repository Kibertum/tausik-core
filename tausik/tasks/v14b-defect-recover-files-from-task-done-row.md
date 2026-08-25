---
slug: v14b-defect-recover-files-from-task-done-row
title: "DEFECT: lookup_relevant_files_from_recent_verify picks task-done filesize rows, not verify rows"
status: done
epic: null
story: null
complexity: null
role: developer
stack: python
tier: light
call_budget: 15
defect_of: v14b-parametrize-top4
scope: "scripts/verify_recent_lookup.py, tests/test_verify_recent_lookup.py (или добавить в существующий)"
scope_exclude: "scripts/service_*.py, scripts/project_*.py, docs/, agents/"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-03T11:18:09Z"
---

## Goal

Fix verify_recent_lookup.lookup_relevant_files_from_recent_verify to filter by trigger=verify only. Currently picks the most recent ANY exit-zero verification_runs row (ORDER BY id DESC), which can be a task-done filesize PASS row containing relevant_files in its command. This causes task_done to recover an inaccurate file list, compute a different files_hash than verify-time, and miss the cache — re-triggering "no fresh verify run" failure even after a real verify --task PASS. Discovered during v14b-parametrize-top4 closure: verify recorded files=, then lookup_relevant_files_from_recent_verify returned ['tests/test_brain_scrubbing.py','tests/test_hooks.py'] from task-done row 368 (filesize=PASS) instead of the verify row 367 (pytest=PASS, files=). Fix: add WHERE command LIKE 'trigger=verify|%' to the SQL in verify_recent_lookup.lookup_relevant_files_from_recent_verify; covered by regression test.

## Acceptance Criteria

1. scripts/verify_recent_lookup.py: lookup_relevant_files_from_recent_verify SQL дополнен `AND command LIKE 'trigger=verify|%'` — фильтрует только verify-trigger строки.
2. tests/test_verify_recent_lookup.py: новый regression test покрывает сценарий — таблица verification_runs содержит свежие task-done filesize-row (с files в command) И verify-row (без files); recovery возвращает None (потому что verify row имеет empty files), НЕ берёт files из task-done row.
3. Pytest: scoped tests/test_verify_recent_lookup.py зелёный + полный suite не сломан (2591+1 ожидается).
4. Negative scenario: если задача имеет ТОЛЬКО task-done строки (нет verify), recovery возвращает None (не угадывает из task-done command). Test покрывает.
5. Lint: ruff All checks passed.

## Plan

[{"step": "\u041d\u0430\u0439\u0442\u0438 existing test file \u0434\u043b\u044f verify_recent_lookup (\u0438\u043b\u0438 \u0440\u0435\u0448\u0438\u0442\u044c \u043f\u0440\u043e new file)", "done": true}, {"step": "\u0418\u0441\u043f\u0440\u0430\u0432\u0438\u0442\u044c SQL \u0432 verify_recent_lookup.lookup_relevant_files_from_recent_verify", "done": true}, {"step": "\u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c regression test (verify row + task-done row \u2192 recovery \u0432\u043e\u0437\u0432\u0440\u0430\u0449\u0430\u0435\u0442 None)", "done": true}, {"step": "Pytest scoped \u0437\u0435\u043b\u0451\u043d\u044b\u0439", "done": true}, {"step": "Pytest \u043f\u043e\u043b\u043d\u044b\u0439 suite \u0431\u0435\u0437 \u0440\u0435\u0433\u0440\u0435\u0441\u0441\u0438\u0439", "done": true}, {"step": "Ruff", "done": true}, {"step": "verify --task + task done", "done": true}]

## Rollback

## Journal

- 2026-05-03T11:07:08Z [planning] — Repro confirmed via direct trace: 1. verify --task v14b-parametrize-top4 (no relevant_files in task DB) → records row 367 (trigger=verify, files=, summary=pytest=PASS). 2. task done v14b-parametrize-top4 (any args) → calls lookup_relevant_files_from_recent_verify which ORDER BY id DESC LIMIT 1 returns row 368 (trigger=task-done, files=tests/...,tests/..., summary=filesize=PASS) — NOT the verify row. 3. Recovered files compute hash da2b7..., verify row 367 was hashed at 35f9503... → cache MISS → "no fresh verify run". Workaround used in v14b-parametrize-top4: pre-set tasks.relevant_files via raw SQL, re-run verify (now uses correct files), task done with matching --relevant-files. Root cause: scripts/verify_recent_lookup.py:134-144 SQL has no WHERE filter on `command LIKE 'trigger=verify|%'`. Only filters by task_slug + exit_code=0. Fix one-liner: add the LIKE filter. Add regression test covering the scenario (task-done filesize row + verify row both fresh; recovery must pick verify).
- 2026-05-03T11:18:09Z [implementation] — AC verified: 1) scripts/verify_recent_lookup.py:lookup_relevant_files_from_recent_verify SQL дополнен AND command LIKE 'trigger=verify|%' — фильтрует только verify-trigger rows. 2) tests/test_verify_first_contract.py: 2 новых regression теста — test_recovery_ignores_task_done_filesize_rows (verify row пустой + новее task-done row с files в command → recovery возвращает None, не ['tests/test_a.py']) и test_recovery_picks_older_verify_over_newer_task_done (verify со src/foo.py + новее task-done со src/bar.py,src/baz.py → recovery возвращает ['src/foo.py']). 3) Pytest scoped: test_verify_first_contract.py 21 passed (было 19, +2). 4) Полный pytest: 2593 passed, 7 skipped в 8m06s (baseline 2591, +2 регрессии). 5) Negative: test_lookup_helper_unit уже покрывает кейс отсутствия verify rows. 6) Ruff: All checks passed.
