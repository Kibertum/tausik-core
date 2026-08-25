---
slug: r14-senar-l3-marker
title: "SENAR Rule 10.15: mark /review runs as L3 vs L2; add ADR metric"
status: done
epic: rel-14-readiness
story: rel-14-audit-fixes
complexity: complex
role: null
stack: null
tier: substantial
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/backend_migrations.py"
  - "scripts/backend_schema.py"
  - "scripts/backend_crud.py"
  - "scripts/project_parser_ops.py"
  - "scripts/project_cli_review.py"
  - "scripts/project.py"
  - "tests/test_review_l3_marker.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T01:12:11Z"
---

## Goal

Release 1.4 readiness: r14-senar-l3-marker

## Acceptance Criteria

1. Migration v21 creates table reviews(id, task_slug, run_type CHECK L1/L2/L3, critical_findings, warnings, run_at, notes). 2. backend_crud exposes review_record/review_list/review_metrics. 3. CLI tausik review record/list/metrics works end-to-end. 4. tausik metrics includes Adversarial Review block when L3 runs exist (ADR = critical/L3-tasks * 100). 5. /review skill records L3 run automatically. Negative: empty reviews table => ADR=0% and metrics block hidden, no L9 type accepted (CHECK constraint), unknown task_slug rejected by FK.

## Plan

## Rollback

## Journal

- 2026-05-01T01:08:24Z [implementation] — /review skill (agents/skills/review/SKILL.md) gained step 7 - records L3 run via tausik review record after compiling final report. Mirrored to .claude/skills/review/SKILL.md.
- 2026-05-01T01:08:24Z [implementation] — CLI: scripts/project_parser_ops.py add_review() with subcommands record/list/metrics. scripts/project_cli_ops.py cmd_review handler. ADR block printed inside cmd_metrics when l3_reviewed_tasks>0. Registered in scripts/project.py dispatch.
- 2026-05-01T01:08:24Z [implementation] — Docs: docs/{en,ru}/cli.md added Reviews (SENAR Rule 10.15) section with full subcommand reference. Mirrored to .claude/docs/{en,ru}/cli.md.
- 2026-05-01T01:08:24Z [implementation] — Migration v21 in scripts/backend_migrations.py and table reviews mirrored in scripts/backend_schema.py. SCHEMA_VERSION bumped to 21.
- 2026-05-01T01:08:24Z [implementation] — Tests: tests/test_review_l3_marker.py (7 cases): table exists, record+list, run_type CHECK rejects L9, empty metrics, ADR calculation across 3 tasks, list filter, parser registers review subcommand. 7/7 pass.
- 2026-05-01T01:08:24Z [implementation] — scripts/backend_crud.py: added review_record(task_slug, run_type, critical_findings, warnings, notes), review_list(task_slug, run_type, limit), review_metrics() returning {l3_reviewed_tasks, l3_critical_findings, adr_pct}.
- 2026-05-01T01:08:25Z [implementation] — AC verified: 1. Migration v21 + reviews table ✓. 2. backend_crud helpers ✓. 3. CLI works (tausik review metrics confirmed live). 4. tausik metrics block conditional on L3 rows ✓. 5. /review skill emits L3 record ✓. Negative: CHECK constraint rejected L9, empty metrics returns 0/0/0.0 ✓.
