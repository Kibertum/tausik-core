---
slug: r14-claudemd-drift
title: "CLAUDE.md / AGENTS.md drift detection in tausik doctor + suggested update-claudemd"
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
completed_at: "2026-05-01T00:56:43Z"
---

## Goal

Release 1.4 readiness: r14-claudemd-drift

## Acceptance Criteria

1. tausik doctor warns when CLAUDE.md static H2 sections drift from build_full_body output (hash-comparable per section). 2. tausik update-claudemd accepts --dry-run that prints unified diff and exits 1 on drift. 3. cli.md (en+ru) document the new flag. 4. Negative scenarios: missing CLAUDE.md returns None (warn 'could not compare', not crash); user customizations beyond template additions are ignored (only template sections are checked).

## Plan

## Rollback

## Journal

- 2026-05-01T00:56:42Z [implementation] — Implemented project_cli_doctor._check_claudemd_drift: splits CLAUDE.md by H2 headings, compares each static section to bootstrap_templates.build_full_body output. Skips DYNAMIC block, '## Current State', and project-name-bearing '## Project:' heading so drift count = real template diff.
- 2026-05-01T00:56:43Z [implementation] — AC verified: 1. doctor section-level drift check works ✓ (smoke tested: shows 11 drifted sections in this repo where CLAUDE.md is intentionally customised). 2. --dry-run flag exists and exits 1 on drift ✓. 3. cli.md en+ru documented ✓. 4. Negative scenarios - missing file returns None, customisations not flagged ✓ (test_drift_returns_none_when_claudemd_missing + _split() ignores unknown headings).
- 2026-05-01T00:56:43Z [implementation] — Tests: tests/test_claudemd_drift.py adds 5 cases - zero drift on freshly generated, drift detected when section edited, None when CLAUDE.md missing, --dry-run flag in parser, subprocess dry-run exits 1. 5/5 pass.
- 2026-05-01T00:56:43Z [implementation] — tausik doctor now reports 'CLAUDE.md drift: N section(s) differ — run: tausik update-claudemd --dry-run'. tausik update-claudemd --dry-run added: difflib.unified_diff against the would-write content, exit 1 on diff, exit 0 on identity. parser registers the flag in project_parser.py:319.
