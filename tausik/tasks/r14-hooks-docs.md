---
slug: r14-hooks-docs
title: "Fix hooks.md vs scripts/hooks/pre-commit (mypy vs tausik gates)"
status: done
epic: rel-14-readiness
story: rel-14-audit-fixes
complexity: null
role: null
stack: null
tier: moderate
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T00:36:17Z"
---

## Goal

Release 1.4 readiness: r14-hooks-docs

## Acceptance Criteria

1. docs/en/hooks.md and docs/ru/hooks.md describe real pre-commit behaviour (mypy + RAG reindex), not 'scoped quality gates'. 2. Negative scenario: cmd.exe without Bash cannot run the script - explicit Windows caveat documented.

## Plan

## Rollback

## Journal

- 2026-05-01T00:36:16Z [implementation] — Rewrote 'Git pre-commit' section in docs/{en,ru}/hooks.md: replaces lying 'scoped quality gates' description with real behavior - mypy on scripts/ via pyproject.toml config (blocking) + optional incremental RAG reindex (warn-only, 5s cap). Mirrored to .claude/docs/{en,ru}/hooks.md.
- 2026-05-01T00:36:16Z [implementation] — Section now also explicitly disambiguates pre-commit from 'scoped quality gates': those run via tausik verify per the v1.4 Verify-First Contract.
- 2026-05-01T00:36:17Z [implementation] — AC verified: 1. Real pre-commit behaviour described in docs/{en,ru}/hooks.md ✓ (mypy + optional RAG reindex). 2. Windows caveat documented ✓ (Git Bash/WSL required, cmd.exe will fail). Mirror tests pass: 34/34 in test_med_findings_fix + test_doc_extract.
