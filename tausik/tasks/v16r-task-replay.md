---
slug: v16r-task-replay
title: "[P1] tausik task replay — реконструкция таймлайна задачи"
status: done
epic: v16-renar-core
story: v16r-trace
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "scripts/backend_queries.py (verification_runs_for_task query); scripts/service_replay.py (NEW ReplayMixin); scripts/service_task.py (mix ReplayMixin into TaskMixin); scripts/project_parser_task.py + scripts/project_cli_task.py (replay subcommand); MCP handlers + tool registration (tausik_task_replay); tests/test_task_replay.py (NEW); docs/{en,ru}/reasoning-trace.md + cli.md + mcp.md; harness/skills/reason/SKILL.md (replay gotcha wording). Re-bootstrap."
scope_exclude: "No DB migration (all 5 tables already exist). No changes to verify/task_done gate logic. Do NOT edit .claude/.cursor/.qwen by hand. No .pen. Reuse existing events_list/task_logs/reasoning_step_list — do not duplicate queries."
relevant_files:
  - "scripts/service_replay.py"
  - "scripts/backend_crud_reasoning.py"
  - "scripts/service_task.py"
  - "scripts/project_parser_task.py"
  - "scripts/project_cli_task.py"
  - "tests/test_task_replay.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-13T15:52:59Z"
---

## Goal

Блокер №3 RENAR-релиза: команда `task replay <slug>` собирает хронологию из task_logs + events + reasoning_steps + verification_runs + receipts (v15-receipt-*) в единый читаемый таймлайн (markdown). AC: replay выводит полную хронологию с источниками; работает на исторических задачах без reasoning_steps (graceful); экспорт в файл.

## Acceptance Criteria

1. `tausik task replay <slug>` prints a single chronological markdown timeline merging task_logs + reasoning_steps + events + verification_runs (incl. receipt signed/run-id from receipt_json), each entry tagged with its SOURCE and ISO timestamp, sorted ascending; header carries task slug/title/status/goal, footer carries per-source counts. 2. GRACEFUL/NEGATIVE: replay on a historical task with ZERO reasoning_steps (and/or zero verification_runs) does NOT crash — absent sources render as an explicit empty marker, not an error; a non-existent slug raises a friendly ServiceError (no traceback). 3. `--output FILE` writes the markdown to a file (confirmation message); without it, stdout. 4. MCP `tausik_task_replay` parity; ruff+mypy+gen_doc_constants --check green; new tests cover chronology+graceful-empty+file-export; re-bootstrap regenerates mirrors; docs (reasoning-trace replay wording flipped to live, cli.md+mcp.md entries) updated.

## Plan

[{"step": "backend_queries.py: add verification_runs_for_task(slug) returning runs (scope/command/exit_code/summary/ran_at/duration_ms/receipt_json) ordered by ran_at", "done": true}, {"step": "service_replay.py: new ReplayMixin.task_replay(slug, output=None) \u2014 gather 5 sources, merge-sort by timestamp, render markdown (header+timeline+per-source footer, receipt signature), graceful empty, optional file write", "done": true}, {"step": "Wire ReplayMixin into TaskMixin (service_task.py)", "done": true}, {"step": "CLI: replay subcommand in project_parser_task.py + dispatch in project_cli_task.py (--output)", "done": true}, {"step": "MCP tausik_task_replay handler + registration", "done": true}, {"step": "tests/test_task_replay.py: chronology+sources, graceful-empty (zero reasoning/verification), file export, bad-slug error", "done": true}, {"step": "Docs: flip reasoning-trace replay wording to live (en/ru) + cli.md/mcp.md entries + SKILL.md gotcha; re-bootstrap; ruff/mypy/constants --check", "done": true}, {"step": "Review (tausik-reviewer) + verify (CLI) + task done + commit", "done": true}]

## Rollback

Pure additive (new backend query, new mixin file, new CLI subcommand, new MCP tool, new test, doc edits) — git revert the commit and re-bootstrap. No migration to undo.

## Journal

- 2026-06-13T15:43:00Z [implementation] — Steps 2-7 done: ReplayMixin (service_replay.py) merges 4 sources by ISO-ts with robust parse; verification_runs_for_task query; wired into TaskMixin; CLI `task replay [--output]`; MCP tausik_task_replay (claude+cursor harness tools+handlers); 7 tests (chronology/verdict+receipt/graceful-zero/empty-render/bad-slug/file-export/parser) all green. Docs: reasoning-trace replay flipped to live (en/ru), cli.md+mcp.md entries, SKILL.md gotcha. Constants regen (mcp 105->106, project 98->99, rag 112->113, test 3846->3853); fixed cross-file counts in README/README.ru/AGENTS/architecture/docs-README/mcp.md; gen_doc_constants --check GREEN; 876 targeted tests passed; ruff+mypy GREEN; re-bootstrap (165 scripts, 14 skills).
- 2026-06-13T15:50:11Z [implementation] — Step 8: tausik-reviewer on code diff — 3 high/7 med/low. Applied: (high) output-path guard rejecting writes into .claude/.cursor/.qwen memory dirs (open bypasses pretool hook); (med) SQL ORDER BY datetime(ran_at); (med) exit_code None→INCOMPLETE defensive branch; (med) route reasoning_steps+events through service layer (self.reasoning_steps/self.events_list) not be.*; (low) isinstance guard on _ts_sort_key. Added tests: events-source wiring (events:2) + protected-memory-path refusal → 8 pass. Declined: event n=1000 cap (unrealistic per-task), backtick-escape (commands have none), _ins in tests (codebase norm). test_count 3853→3854; README badges bumped; constants --check GREEN. CLI verify PASS receipt #719.
- 2026-06-13T15:51:56Z [implementation] — AC1: tausik task replay <slug> prints chronological md timeline merging task_logs+reasoning_steps+events+verification_runs (receipt signed/key via receipt_json), each entry SOURCE+ISO-ts, ascending; header slug/title/status/goal, footer per-source counts. Verified by test_replay_merges_and_sorts_all_sources + live dogfood on v16r-reason-skill (11 entries, receipts shown). AC2 GRACEFUL/NEGATIVE: test_replay_graceful_zero_reasoning_and_verification (zero reasoning+verify, no crash, '0 (none)'); test_replay_bad_slug_raises (ServiceError, no traceback); test_render_empty_timeline_marker. AC3: test_replay_writes_to_file (--output) + test_replay_refuses_protected_memory_path. AC4: MCP tausik_task_replay claude+cursor parity (test_mcp_doc_tool_counts green); ruff+mypy GREEN; FULL suite 3726 passed/8 skip/0 fail; gen_doc_constants --check GREEN (mcp 105->106, project 98->99, test 3853->3854); re-bootstrap mirrors; docs reasoning-trace/cli/mcp updated. CLI verify PASS receipt #719.
- 2026-06-13T15:52:58Z [implementation] — AC1: replay merges 4 sources chronologically with SOURCE+ISO-ts, receipt key, header+footer — test_replay_merges_and_sorts_all_sources + live dogfood (11 entries). AC2 GRACEFUL/NEGATIVE: zero-reasoning+verify no crash (test_replay_graceful_*), bad slug→ServiceError, empty-render marker. AC3: --output file + protected-memory-path refusal. AC4: MCP claude+cursor parity (mcp_doc tests), ruff+mypy GREEN, FULL suite 3726 passed/8 skip/0 fail, constants --check GREEN, re-bootstrap, docs updated. Backend query relocated to backend_crud_reasoning.py to respect filesize gate. CLI verify PASS.
