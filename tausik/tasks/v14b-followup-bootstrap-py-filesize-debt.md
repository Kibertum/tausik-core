---
slug: v14b-followup-bootstrap-py-filesize-debt
title: "Split bootstrap/bootstrap.py — 529 lines over filesize gate"
status: done
epic: v14b-start-token-economy
story: phase-a-quick-wins
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "bootstrap/bootstrap.py"
  - "bootstrap/bootstrap_modes.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-06T16:36:02Z"
---

## Goal

Reduce bootstrap/bootstrap.py to under 400 lines by extracting logical groups (CLI parsing, vendor sync, IDE detection, etc.) into dedicated bootstrap_*.py modules following the existing pattern (e.g. bootstrap_vendor.py, bootstrap_generate.py).

## Acceptance Criteria

1) bootstrap/bootstrap.py < 400 lines; 2) extracted modules each < 400 lines; 3) all existing bootstrap tests stay green (no regression in tests/test_bootstrap*.py); 4) running bootstrap against this project succeeds end-to-end (smoke test); negative: 5) public CLI surface (python bootstrap/bootstrap.py --update / --init) is unchanged — same flags, same exit codes

## Plan

## Rollback

## Journal

- 2026-05-06T16:35:59Z [implementation] — Extracted argparse build_parser() + run_dry_run() + run_refresh_mode() + run_post_bootstrap() + load_bootstrap_config() helpers into bootstrap/bootstrap_modes.py. bootstrap.py imports from new module and dispatches; main() body shrunk from ~350 to ~180 lines. AC verified: 1) ✓ bootstrap/bootstrap.py = 361 lines (was 530, gate limit 400); 2) ✓ bootstrap_modes.py = 253 lines (under 400); 3) ✓ bootstrap test suite green: 19/19 in test_bootstrap_dryrun + test_bootstrap_real + test_bootstrap_non_destructive + test_bootstrap_frontmatter + test_bootstrap_skills_coverage + test_bootstrap_model_profile; 4) ✓ smoke test: python bootstrap/bootstrap.py --update completes end-to-end (Skills 13, Scripts 110, MCP 3, References 6 copied); python bootstrap/bootstrap.py --dry-run shows expected output; 5) ✓ full pytest 2841 passed / 7 skipped / 0 failures in 113.29s (no regression). Public CLI surface unchanged (argparse moved to bootstrap_modes.build_parser, all flags identical).
