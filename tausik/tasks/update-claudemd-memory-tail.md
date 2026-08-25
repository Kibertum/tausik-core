---
slug: update-claudemd-memory-tail
title: "update_claudemd writes compact memory tail into Current State"
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
  - "scripts/project_cli_extra.py"
  - "scripts/service_knowledge_aggregates.py"
  - "tests/test_claudemd_drift.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-06T16:14:53Z"
---

## Goal

tausik update-claudemd appends compact memory tail (5 decisions + 5 conventions + 3 dead ends, one line each) into CLAUDE.md Current State so /start does not need a separate memory_block call.

## Acceptance Criteria

1) tausik update-claudemd writes a 'Memory tail' subsection inside Current State block with 5 decisions, 5 conventions, 3 dead ends (one line each); 2) section is bounded by markers so re-runs replace it idempotently; 3) when DB has no memory items, section is omitted (not empty); 4) tests cover happy path + empty-DB path; negative: 5) malformed CLAUDE.md (missing Current State markers) does not crash, falls back to existing behaviour

## Plan

## Rollback

## Journal

- 2026-05-06T16:11:46Z [implementation] — Implemented _build_memory_tail() helper in scripts/project_cli_extra.py — fetches 5 decisions + 5 conventions + 3 dead ends via svc.be.decision_list/memory_list, returns one-line-per-item markdown list. cmd_update_claudemd now appends memory tail subsection inside DYNAMIC block when non-empty. AC verified: 1) ✓ Memory tail subsection rendered as 'Decisions (N): - #id text', 'Conventions (N): - #id title', 'Dead ends (N): - #id title' (test_memory_tail_renders_decisions_conventions_deadends); 2) ✓ idempotent via existing DYNAMIC:START/END markers; 3) ✓ empty DB returns [] so subsection omitted (test_memory_tail_empty_db_returns_empty_list); 4) ✓ unit tests cover happy + empty paths + truncation + decisions-only (5 new tests); 5) ✓ db failure returns [] gracefully without crashing CLAUDE.md update (test_memory_tail_db_failure_returns_empty_no_crash). Live CLI in .claude/scripts/ runs stale code until A5 bootstrap; debug import from scripts/ confirms 17 lines memory tail produced. pytest 10/10 in test_claudemd_drift.py
