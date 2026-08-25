---
slug: v15p-review-low-cleanup
title: "[P2] v1.5 review cleanup — remaining MEDIUM + valuable LOW findings"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/project_cli_aidd_validate.py, scripts/hooks/scope_write_gate.py, scripts/gate_command_runner.py, scripts/service_knowledge_aggregates.py, scripts/project_cli_task.py, scripts/backend_queries_fts.py, tests/*"
scope_exclude: "accepted-by-design LOW (pyproject double-parse, .env→security heuristic, autogen abort=skip, README errors=replace, _parse_claims last-wins) — noted, not changed"
relevant_files:
  - "scripts/project_cli_aidd_validate.py"
  - "scripts/hooks/scope_write_gate.py"
  - "scripts/gate_command_runner.py"
  - "scripts/service_knowledge_aggregates.py"
  - "scripts/project_cli_task.py"
  - "scripts/backend_queries_fts.py"
  - "tests/test_v15_review_cleanup.py"
  - "docs/_generated/constants.json"
  - README.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T22:20:17Z"
---

## Goal

Finish the v1.5 swarm-review backlog so nothing is left undone before release. Fix the 3 still-open MEDIUM findings (aidd validate _files_over silent 4000-file truncation → report unverifiable not ok; scope_write_gate._delegated_slugs swallows sqlite errors silently → stderr warn; gate_command_runner conflates spawn errors with honest non-zero → catch FileNotFoundError/PermissionError separately + log) plus the valuable LOW: delegated_missing_scope should treat parsed-empty '[]' scope_paths as missing (consistency with the QG-0 fix); build_memory_compact needs the same defensive guard as its sibling aggregates; project_cli_task help text must list the OW subcommands; fts_maybe_optimize must not persist a stale baseline when the post-optimize recount fails. Remaining LOW (perf double-parse, .env heuristic, abort=skip, README errors=replace, last-wins claim parse) are accepted-by-design — record as a note, do not churn.

## Acceptance Criteria

AC1: aidd validate _verify_max_filesize reports 'unverifiable' (not 'ok') when the file walk hit its cap before confirming no offender. AC2: scope_write_gate._delegated_slugs emits a stderr warning on sqlite error (instead of fully silent), keeping the legacy-empty fallback. AC3: gate_command_runner catches spawn errors (FileNotFoundError/PermissionError) distinctly with a logged WARNING, separate from an honest non-zero exit. AC4: delegated_missing_scope treats a parsed-empty scope_paths ('[]') as missing (delegated worker still flagged). AC5: build_memory_compact wraps its backend call in try/except → '' on error (parity with build_compact_memory_tail/build_memory_block). AC6: project_cli_task usage/help string lists delegate/undelegate/handoff/summary-back. AC7: fts_maybe_optimize does not write a stale baseline when the post-optimize recount raises. AC8: tests cover each; ruff+mypy clean; filesize<400. Negative: each error/edge path is asserted (truncation→unverifiable, recount-fail→baseline unchanged, empty scope→flagged).

## Plan

## Rollback

git revert; all fixes small/localized, no schema change.

## Journal

- 2026-06-14T22:20:00Z [implementation] — AC verified: 1. ✓ _files_over returns (offenders, truncated); _verify_max_filesize → 'unverifiable' on truncation — TestFilesOverTruncation (3). 2. ✓ _delegated_slugs warns to stderr on sqlite error, keeps legacy-empty. 3. ✓ gate_command_runner catches FileNotFoundError/PermissionError/NotADirectoryError distinctly + logs WARNING — TestGateSpawnError. 4. ✓ delegated_missing_scope treats '[]'/''/null as missing (_scope_empty) — TestDelegatedEmptyScope (3). 5. ✓ build_memory_compact try/except→'' parity — TestMemoryCompactGuard. 6. ✓ project_cli_task subcmds help lists delegate/undelegate/handoff/summary-back. 7. ✓ fts_maybe_optimize baseline = recount, else current+1 (never stale). 8. ✓ 51 tests green; full ruff+mypy clean (210); files<400. Accepted-by-design LOW + test-gaps → memory #172 (backlog). Root cause (category: other): review-surfaced edge/observability gaps from the initial v15 build; Prevention: fixed valuable ones + documented accepted ones.
