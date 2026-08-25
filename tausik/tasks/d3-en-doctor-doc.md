---
slug: d3-en-doctor-doc
title: "docs/en/doctor.md NEW"
status: done
epic: docs-overhaul-v13
story: docs-en-new-features
complexity: null
role: tech-writer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "docs/en/doctor.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-26T16:18:40Z"
---

## Goal

docs/en/doctor.md NEW: health check categories exit codes

## Acceptance Criteria

1. docs/en/doctor.md created; 2. Documents 4 health groups (venv, DB, MCP, skills); 3. Covers drift detection; 4. Shows CLI usage (.tausik/tausik doctor) + MCP tausik_doctor; 5. Negative: doesn't claim doctor auto-fixes (it diagnoses only)

## Plan

## Rollback

## Journal

- 2026-04-26T16:18:40Z [implementation] — AC verified: 1.✓ docs/en/doctor.md created with sample output captured from real `tausik doctor` invocation; 2.✓ 4 health groups documented (venv, DB, MCP, skills) plus drift, config, gates, session; 3.✓ Drift detection covered with fix command (bootstrap --refresh); 4.✓ CLI usage `.tausik/tausik doctor` and MCP `tausik_doctor` both shown; 5.✓ negative — explicit "Doctor does NOT auto-fix" section, exit code semantics shown.
