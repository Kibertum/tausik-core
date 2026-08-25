---
slug: qa-task-update-notes-guard
title: "Guard the task_update(notes=…) journal-overwrite footgun"
status: done
epic: v15-polish
story: v15p-debt
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 40
defect_of: null
scope: "scripts/service_task.py (guard), scripts/project_parser_task.py (--notes-overwrite), scripts/project_cli_task.py (wire flag), docs/ru/cli.md (warning), tests/ (new guard test)"
scope_exclude: "scripts/project_backend.py (CRUD stays pure), MCP handler/tools schema (service guard protects all callers; MCP override is follow-up)"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T12:38:37Z"
---

## Goal

Stop task_update from silently clobbering a task's append-only journal. notes is a crash-safe log (task_log appends); a blind task_update(notes=…) overwrites the entire history (memory #160 footgun, undocumented per audit). Refuse to overwrite a non-empty journal unless the caller explicitly opts in (notes_overwrite), steer to task_log, and document the warning.

## Acceptance Criteria

AC-1: service_task.task_update refuses (ServiceError) when fields include notes AND the task already has non-empty notes, with a message steering to `task log` and mentioning the notes_overwrite escape. AC-2: passing notes_overwrite=true (popped, never reaches backend) allows the intentional overwrite. AC-3: setting notes on a task with EMPTY/NULL notes is allowed (no false positive — first note via update is fine). AC-4: CLI `task update` gains `--notes-overwrite` flag wired to notes_overwrite; docs/ru/cli.md documents the --notes warning. AC-5: new tests cover refuse / empty-notes-allowed / override-allowed. Negative: task_log append path unaffected (still appends, never blocked); other task_update fields (title/goal/scope) unaffected. AC-6: targeted tests green via .tausik/tausik.

## Plan

## Rollback

git checkout -- scripts/service_task.py scripts/project_parser_task.py scripts/project_cli_task.py docs/ru/cli.md tests/; pure additive guard, no migration/flag. Guard defaults to refuse — if it over-blocks, notes_overwrite=true is the immediate escape.

## Journal

- 2026-06-14T12:38:32Z [implementation] — AC verified: 1. ✓ task_update refuses notes= on non-empty journal -> ServiceError (test_overwrite_nonempty_journal_refused). 2. ✓ notes_overwrite=true allows replace, flag popped before backend (test_overwrite_allowed_with_flag). 3. ✓ notes on empty journal allowed, no false positive (test_notes_on_empty_journal_allowed). 4. ✓ CLI --notes-overwrite wired (project_parser_task.py + project_cli_task.py); docs/ru/cli.md documents the warning. 5. ✓ 5 new tests + task_log append unaffected + other fields unaffected. Negative: task_log append never blocked (test_task_log_append_unaffected), goal/title updates unaffected (test_other_fields_unaffected). Tests: 65 passed (notes_guard+tausik_service). Filesize: extracted guard to scripts/task_notes_guard.py (35L) -> service_task.py 399<400. ruff+mypy clean. Domain: a real footgun (memory #160) that silently destroyed crash-safe journal history is now fail-safe by default with an explicit, discoverable escape.
