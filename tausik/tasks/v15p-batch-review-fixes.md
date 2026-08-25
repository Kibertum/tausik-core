---
slug: v15p-batch-review-fixes
title: "[P2] Batch-review hardening — fts_maybe_optimize + claudemd_writer edge-cases"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/backend_queries.py, scripts/claudemd_writer.py, tests/test_fts_maybe_optimize.py, tests/test_update_claudemd_agents.py"
scope_exclude: "no behavior change to the happy path; no new public API"
relevant_files:
  - "scripts/backend_queries.py"
  - "scripts/backend_queries_fts.py"
  - "scripts/claudemd_writer.py"
  - "tests/test_fts_maybe_optimize.py"
  - "tests/test_update_claudemd_agents.py"
  - README.md
  - "docs/_generated/constants.json"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T18:03:44Z"
---

## Goal

Apply adversarial batch-review (separate model) findings on the two just-landed simple tasks: (fts) handle negative events-delta by re-baselining instead of looping, make baseline write best-effort, document the migration-bypass limitation; (claudemd) anchor END marker after START to avoid multi-pair/out-of-order corruption, wrap file read in OSError handling, drop the cwd-relative AGENTS.md fallback that could corrupt an unrelated file under MCP cwd, coerce dry_run to bool.

## Acceptance Criteria

AC1: fts_maybe_optimize — negative delta re-baselines and returns optimized=False (no loop-fire); baseline write best-effort (never propagates); migration-bypass caveat documented in docstring. AC2: claudemd_writer.apply_dynamic_section — END located after START via index(end,start); file read wrapped in OSError→error tuple; out-of-order/multi-pair no longer corrupts the doc. AC3: resolve_sibling_targets only considers an AGENTS.md sibling of the primary path (no bare cwd-relative candidate that could hit an unrelated file under MCP cwd). AC4: regression tests for each fix; ruff+mypy clean; filesize<400.

## Plan

## Rollback

git revert; pure defensive hardening of two functions, no schema/state change.

## Journal

- 2026-06-14T18:03:27Z [implementation] — Applied batch-review (sonnet) findings. fts: negative-delta re-baselines (vacuum/DB-replace) without loop-firing; _set_fts_baseline best-effort (write failure swallowed); migration-bypass caveat in docstring. claudemd_writer: END located via find(END, after START) — body-text/multi-pair markers no longer mis-slice; open() wrapped OSError→error tuple; resolve_sibling_targets drops bare cwd-relative AGENTS.md fallback (MCP-cwd corruption risk) → sibling-of-primary only; dry_run coerced to bool. Extracted FTS maintenance to backend_queries_fts.BackendQueriesFtsMixin (backend_queries.py 406→341, cap). +5 regression tests. 80 tests green, ruff+mypy clean.
- 2026-06-14T18:03:43Z [implementation] — AC1: ✓ fts — negative delta re-baselines + returns optimized=False (test_negative_delta_rebaselines_without_firing); _set_fts_baseline best-effort; migration caveat in docstring. AC2: ✓ claudemd — END via find(END, after START) so prose/multi markers don't corrupt (test_end_marker_in_prose_before_section_not_corrupted); read wrapped OSError→error tuple (test_missing_file_returns_error_tuple). AC3: ✓ resolve_sibling_targets sibling-of-primary only, no cwd fallback (test_does_not_pick_cwd_agents_md_for_other_dir_primary). AC4: ✓ +5 regression tests (16 in the two files, 80 incl backend smoke); ruff+mypy clean; backend_queries.py 341<400 via BackendQueriesFtsMixin extraction, claudemd_writer 75, backend_queries_fts 88. Negative: events-count failure → optimized=False not crash; marker-less file → skip notice; absent file → error tuple not traceback.
