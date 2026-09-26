---
slug: a-task-cannot-be-closed-as-obsolete
title: "A task cannot be closed as obsolete or won't-do: the lifecycle has done, blocked and delete, and nothing for a finding that time resolved"
status: done
epic: release-110-deferred-from-19
story: release110-open-defects
complexity: complex
role: architect
stack: python
tier: moderate
call_budget: 40
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/task_obsolete.py"
  - "scripts/backend_migrations_v67.py"
  - "scripts/backend_migrations.py"
  - "scripts/backend_schema.py"
  - "scripts/project_backend.py"
  - "scripts/project_parser_task.py"
  - "scripts/project_cli_task.py"
  - "scripts/mcp_cli_only.py"
  - "scripts/backend_queries_metrics.py"
  - "scripts/backend_tier_metrics.py"
  - "scripts/backend_defect_escape.py"
  - "scripts/root_cause.py"
  - "scripts/renar_drift.py"
  - "scripts/status_view.py"
  - "scripts/tausik_utils.py"
  - "scripts/claudemd_state.py"
  - "tests/test_task_obsolete.py"
scope_paths:
  - "scripts/*.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-24T06:05:53Z"
resolution: null
resolution_reason: null
---

## Goal

Session #265: the owner asked to close four obsolete tasks. The lifecycle offered three exits and none fit: task done demands per-criterion ✓ evidence (a FAIL line blocks, 'not exercised' is not recognised), task delete erases the record and its journal, and leaving them open lies to the roadmap. The honest closure took writing acceptance criteria after the fact for two tasks that reality had satisfied, and a hard delete for a duplicate. Add a fourth exit — obsolete / won't do — that keeps the record, requires a reason, stops counting the task as open in the map, and is reported apart from done (a closed finding is not a shipped one).

## Acceptance Criteria

1. `tausik task obsolete <slug> --reason "<why>"` closes a task in planning, active or blocked WITHOUT per-criterion evidence and WITHOUT QG-2: the record stays (status done, completed_at set, journal kept), the reason is required (refused under 10 characters) and stored in tasks.resolution_reason, and tasks.resolution = 'obsolete' (schema v67, CHECK closed list).
2. A closed finding is not a shipped one: FPSR, DER, cycle and lead time, tier calibration, defect escape and root-cause coverage exclude obsolete tasks; the status line and CLAUDE.md state report them apart ("N done, M obsolete").
3. NEGATIVE: an obsolete close is refused on a task already done, and with an empty or placeholder reason; the metrics of a project are byte-identical before and after an obsolete close of a task that would have counted.
4. NEGATIVE: it stays CLI-only for 1.10 and is declared so in mcp_cli_only.CLI_ONLY with its reason; the ProjectService/SQLiteBackend public surface does not grow (class_surface baseline unchanged).
5. The two stale tasks found in session #269 (the-suite-cost-is-per-test-overhead-not-a-slow-tail, record-direct-edit-is-a-dead-duplicate-of-the-live-path) are closed with it, as the live proof.

## Plan

## Rollback

git revert; a status value and its readers

## Journal

- 2026-09-24T05:58:09Z [implementation] — AC-1: ✓ tests/test_task_obsolete.py::test_a_planning_task_closes_as_obsolete_and_keeps_its_record — scripts/task_obsolete.close_obsolete + CLI 'task obsolete <slug> --reason'; status done, completed_at, journal line 'OBSOLETE (was planning): <reason>', tasks.resolution='obsolete' (v67, CHECK closed list), resolution_reason stored; no QG-2 run.
- 2026-09-24T05:58:09Z [implementation] — AC-2: ✓ tests/test_task_obsolete.py::test_delivery_metrics_do_not_move and tests/test_task_obsolete.py::test_the_status_line_and_claude_md_report_it_apart — FPSR/DER/cycle/lead/per-tier/calibration/defect-escape/root-cause/RENAR-drift SQL filter resolution IS NULL; status counts carry an 'obsolete' key; CLAUDE.md state prints 'N/T done, M obsolete'; completion_pct counts obsolete as completed.
- 2026-09-24T05:58:09Z [implementation] — AC-3: ✓ tests/test_task_obsolete.py::test_a_close_without_a_checkable_reason_is_refused and tests/test_task_obsolete.py::test_a_task_already_done_is_not_marked_obsolete — negative; the metrics test gives the obsolete task attempts=1, a start and a tier, and 10 delivery keys stay identical; mutation (FPSR filter removed) -> 1 failed, 7 passed; restored.
- 2026-09-24T05:58:10Z [implementation] — AC-4: ✓ tests/test_mcp_cli_only.py::test_a_listed_command_is_not_an_mcp_tool — 'task obsolete' registered CLI-only with its reason (decision #390); close_obsolete is a module function, class_surface baseline (SQLiteBackend 169, ProjectService 148) untouched; 520 schema/migration/metrics/status/doc-coverage/class-surface tests pass.
- 2026-09-24T05:58:10Z [implementation] — AC-5: ✓ measurement — live: task obsolete closed the-suite-cost-is-per-test-overhead-not-a-slow-tail and record-direct-edit-is-a-dead-duplicate-of-the-live-path; a second obsolete on the latter was refused 'already closed (obsolete)'; status now reads 'Tasks: 1580/1699 done, 2 obsolete'. Live DB migrated to v67 via bootstrap + CLI (the CLI runs the deployed .claude/scripts copy).
