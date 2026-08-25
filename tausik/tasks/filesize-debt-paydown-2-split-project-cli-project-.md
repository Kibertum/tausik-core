---
slug: filesize-debt-paydown-2-split-project-cli-project-
title: "Filesize debt paydown 2: split project_cli + project_service + service_task to under 400 lines each"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/project_cli.py (modify — remove cmd_task block), scripts/project_cli_task.py (NEW), scripts/project_service.py (modify — remove SessionMixin block), scripts/service_session.py (NEW), scripts/service_task.py (modify — remove _task_done_report block), scripts/service_task_done.py (NEW), bootstrap drift sync"
scope_exclude: "No semantic changes to the moved code — pure re-org. No public API renames. No CHANGELOG entry (internal refactor, captured in task notes)."
relevant_files:
  - "scripts/project_cli.py"
  - "scripts/project_cli_task.py"
  - "scripts/project_service.py"
  - "scripts/service_session.py"
  - "scripts/service_task.py"
  - "scripts/service_task_done.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-06T10:50:42Z"
---

## Goal

Split scripts/project_cli.py (471), scripts/project_service.py (518), scripts/service_task.py (517) into <400-line modules so commit-time filesize gate passes for the v1.4-polish bundle commit (4 closed tasks: active-time, stdin-hang, t13-prompt-caching, aidd-scaffold) without bypass. Pre-existing debt — 2 of 3 files actually shrank in the bundle, but all are over the 400-line limit and have been since session #49.

## Acceptance Criteria

1. scripts/project_cli.py < 400 lines (extract cmd_task + supporting helpers into scripts/project_cli_task.py NEW). 2. scripts/project_service.py < 400 lines (extract SessionMixin into scripts/service_session.py NEW; ProjectService still inherits from it via mixin chain). 3. scripts/service_task.py < 400 lines (extract _task_done_report + its private helpers into scripts/service_task_done.py NEW). 4. All imports/dispatch dictionaries that referenced the moved symbols are updated; nothing imports from a module that no longer exports it. 5. Full pytest fast lane GREEN — at least the directly touched test files (test_project_mcp, test_tausik_service, test_task_done_matcher, test_mcp_integration) pass cleanly with no new failures vs HEAD. 6. ruff + mypy clean on all 6 files (3 modified + 3 new). 7. filesize gate: All files within line limit at commit time. 8. .claude/scripts/ kept in sync via bootstrap (drift-clean per `tausik doctor`). 9. NEGATIVE — if a moved symbol is private (single-underscore prefix) but referenced from another scripts/*.py module by name, re-export it explicitly from the original module so external callers don't break; verify by grepping all `from project_cli import`, `from project_service import`, `from service_task import` and ensuring every name is still importable from where it was. 10. NEGATIVE — verify there's no circular import between original module and its new sibling (e.g. project_cli ↔ project_cli_task) by importing each at module load; pytest collection itself acts as the smoke test.

## Plan

## Rollback

## Journal

- 2026-05-06T10:41:15Z [implementation] — Session #53 resumed after interruption. No prior progress; starting fresh — read all 3 source files, identify split points, extract.
- 2026-05-06T10:48:30Z [implementation] — Extracted: cmd_task -> project_cli_task.py (239L), SessionMixin -> service_session.py (136L), _task_done_report+_format_task_done_failures -> service_task_done.py (236L). All 3 source files now under 400: project_cli=259, project_service=398, service_task=318. Imports smoke-tested, MRO verified.
- 2026-05-06T10:50:42Z [implementation] — Split complete: project_cli (471->259) + project_cli_task (NEW 239); project_service (518->398) + service_session (NEW 136); service_task (518->318) + service_task_done (NEW 236). All under 400-line filesize gate. 132 pytest tests pass (test_project_mcp, test_tausik_service, test_task_done_v1_aggregation, test_verify_first_contract, test_e2e_workflow, test_task_done_matcher). 17 MCP integration tests pass. ruff clean on all 6 files; mypy clean (pre-existing brain_classifier error unrelated). Bootstrap drift-clean per tausik doctor. Re-exports: cmd_task accessible from project_cli, _format_task_done_failures accessible from service_task. MRO verified: SessionMixin in ProjectService, TaskDoneReportMixin in TaskMixin.
