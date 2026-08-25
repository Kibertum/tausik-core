---
slug: v153-release-bump
title: "[chore] Release 1.5.3 — version bump + CHANGELOG for Windows fixes"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: light
call_budget: 12
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-15T10:19:08Z"
---

## Goal

Cut the 1.5.3 patch release for the two Windows defect fixes (cmd-wrapper unconditional exit + RAG reserved-name walk abort). Bump version 1.5.2→1.5.3 in pyproject.toml + tausik_version.py, add [1.5.3] sections to CHANGELOG.md + CHANGELOG.ru.md, re-bootstrap, keep gen_doc_constants --check green, then commit and push for user internal testing.

## Acceptance Criteria

AC1: pyproject.toml + scripts/tausik_version.py both read 1.5.3. AC2: CHANGELOG.md and CHANGELOG.ru.md each have a [1.5.3] — 2026-06-15 section describing both Windows fixes (cmd-wrapper, RAG reserved-name). AC3: bootstrap re-run; gen_doc_constants --check green; ruff+mypy clean. Negative: no version reference left at 1.5.2 in source-of-truth files; Unreleased section reset to placeholder.

## Plan

## Rollback

## Journal

- 2026-06-15T10:19:07Z [implementation] — AC verified: 1. ✓ pyproject.toml + scripts/tausik_version.py = 1.5.3; fresh CLI reports 1.5.3; no 1.5.2 left in source-of-truth (grep clean) 2. ✓ CHANGELOG.md + CHANGELOG.ru.md each have [1.5.3] — 2026-06-15 with both Windows fixes (cmd-wrapper regression + RAG reserved-name walk abort) 3. ✓ bootstrap rc=0; gen_doc_constants --check OK (constants.json regenerated to 1.5.3); ruff All checks passed; mypy Success 210 files; doc tests 44 passed
