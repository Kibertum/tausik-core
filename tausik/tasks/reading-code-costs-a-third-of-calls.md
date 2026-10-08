---
slug: reading-code-costs-a-third-of-calls
title: "Reading code costs a third of all calls, and nothing measures it per task"
status: done
epic: release-110-deferred-from-19
story: release110-owner-priorities
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/call_mix.py"
  - "scripts/project_parser_ops.py"
  - "scripts/project_cli_metrics.py"
  - "tests/test_call_mix.py"
  - "docs/en/cli-tasks.md"
  - "docs/ru/cli-tasks.md"
scope_paths:
  - "scripts/"
  - "harness/"
  - "docs/"
  - "changelog.d/"
  - "tests/"
scope_tools: []
depends_on: []
completed_at: "2026-09-29T22:43:45Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Measured session #279 over the last 10 transcripts: 14593 tool calls, 83% shell. Reading code through shell (grep 14.0%, sed 12.2%, cat 4.6%, ls/tail/wc ~3.8%) is ~35% of shell calls; inline python (python -, -c) ~12%; tausik ceremony (task update/log/done/show/verify) ~9%; pytest 4.4%. Cache is 94.2% of the bill (memory #806), each call re-sends ~520k context (ctx_p50 for Bash), so the lever is the NUMBER of calls. Owner priority 2 of decision #406.

## Acceptance Criteria

AC-1 metrics reports calls per closed task by category (read / edit / run / ceremony / other) from transcripts, with coverage stated. AC-2 MOVED to read-lever-chosen-and-measured (1.11): the lever needs sessions to measure. AC-3 NEGATIVE: the report never presents a blended median without the per-complexity split. AC-4 A bash categoriser misreading env-prefixed commands (PYTHONUTF8=1 cmd) is tested.

## Plan

## Rollback

git revert

## Journal

- 2026-09-29T22:17:29Z [implementation] — AC-1: ✓ 'tausik metrics calls' (scripts/call_mix.py): BEFORE, newest 10 transcripts, 198 closed tasks: median calls simple 14 (read 2), medium 29 (read 7), complex 50 (read 18); share read 30.8% edit 14.7% run 15.0% script 16.8% ceremony 15.5% other 7.2%; 5621 calls outside any task window. AC-3: ✓ tests/test_call_mix.py::test_the_report_is_split_by_complexity_never_blended_alone. AC-4: ✓ tests/test_call_mix.py::test_the_real_command_is_judged_not_its_prefix. OPEN: AC-2 lever + after-measure needs later sessions.
- 2026-09-29T22:42:29Z [implementation] — AC-2 split out to read-lever-chosen-and-measured (owner: prepare 1.10 for release; the after-measure needs later sessions). AC-1/3/4 evidence logged above; tests/test_call_mix.py green.
