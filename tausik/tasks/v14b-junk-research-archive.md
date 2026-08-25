---
slug: v14b-junk-research-archive
title: "B-junk-2: Research dump archive — move stale retrospectives to docs/_archive/"
status: done
epic: v14-polish-quality
story: v14-polish-b-quality
complexity: simple
role: developer
stack: python
tier: moderate
call_budget: 30
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-07T00:54:01Z"
---

## Goal

Re-scope from manual move (NOT READY: all files 3-6 days old, criteria >30) to automated audit script. Create scripts/audit_research_dump.py that surfaces candidates when they ripen — replaces the manual 2026-06-02 review with a cheap scan.

## Acceptance Criteria

1. New scripts/audit_research_dump.py with audit_research_dump(repo_root, min_age_days=30) -> dict — walks docs/{en,ru}/research/, filters files by age and absence of references in tests/, scripts/, CHANGELOG, README. 2. Returns {candidates, skipped_recent, skipped_referenced, scanned} — counts + per-candidate age_days. 3. CLI: tausik audit research [--min-age-days N] [--json] — prints human or JSON report. 4. tests/test_audit_research_dump.py: ≥6 cases — empty dir, recent file skipped, old + referenced skipped, old + unreferenced is candidate, age threshold boundary, JSON CLI mode. 5. docs/{en,ru}/cli.md mention the new audit subcommand. 6. CHANGELOG en+ru entry — explain re-scope from manual to automated. 7. ruff + mypy + pytest + filesize gates green.

## Plan

## Rollback

## Journal

- 2026-05-07T00:54:00Z [implementation] — AC verified (re-scoped from manual move to audit script): 1.✓ scripts/audit_research_dump.py with audit_research_dump(repo_root, min_age_days=30). 2.✓ Returns {candidates, skipped_recent, skipped_referenced, scanned}. 3.✓ tausik audit research [--min-age-days N] [--json] CLI; smoke shows 4 scanned, 0 candidates (all 4 files are 5 days old per task notes). 4.✓ tests/test_audit_research_dump.py 7 cases. 5.✓ docs/{en,ru}/cli.md updated with audit research entry. 6.✓ CHANGELOG en+ru entry explains re-scope. 7.✓ ruff/mypy/pytest/filesize green; constants.json regen; project_cli_ops.py split into project_cli_audit_extra.py to satisfy filesize gate.
