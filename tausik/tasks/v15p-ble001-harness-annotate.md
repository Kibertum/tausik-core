---
slug: v15p-ble001-harness-annotate
title: "[defect] BLE001: annotate harness/**/mcp blind-except too (ruff check . was red)"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: qa-enforce-ble001-blind-except
scope: "harness/{claude,cursor}/mcp/**/*.py (reasoned noqa via the annotation script), bootstrap re-run"
scope_exclude: "no ruff exclude/mask of harness; no logic change; no new CLI"
relevant_files:
  - "tests/test_ble001_enforced.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T19:48:39Z"
---

## Goal

Follow-up defect of qa-enforce-ble001-blind-except: enabling BLE001 globally left `ruff check .` red with 64 blind-except in harness/**/mcp (claude+cursor MCP source copies) — CI only lints scripts/tests/bootstrap so it stayed green, but a developer running `ruff check .` hits errors. Annotate the harness sites with the same reasoned # noqa so the WHOLE tree is clean under BLE001 (consistent strict enforcement), not just CI scope.

## Acceptance Criteria

AC1: all blind-except in harness/**/mcp annotated with reasoned # noqa: BLE001 (same category-accurate scheme). AC2: `ruff check .` (whole tree) is clean under BLE001 — not just the CI scope. AC3: mypy clean; comment-only (no behavior change). AC4: bootstrap re-run so .claude/mcp copies inherit the annotations. Negative: a NEW unannotated blind-except anywhere in the tree still fails `ruff check .` (rule remains enforcing, exclude not used to mask).

## Plan

## Rollback

git revert; comment-only annotations, no behavior.

## Journal

- 2026-06-14T19:48:10Z [implementation] — AC1: ✓ all 64 blind-except in harness/**/mcp (14 files, claude+cursor) annotated with reasoned # noqa: BLE001 (MCP-handler category). AC2: ✓ All checks passed! clean whole-tree under BLE001 (was 64 errors) — guarded by test_no_unannotated_blind_except_whole_tree (now uses '.'). AC3: ✓ mypy clean (208 files), comment-only. AC4: ✓ bootstrap re-run (harness→.claude/mcp inherit). Root cause (category: process): BLE001 enablement under-scoped to CI paths (scripts/tests/bootstrap) while All checks passed! traverses harness too. Prevention: guard test now checks the whole tree, not just CI scope. Negative: a new unannotated blind except anywhere fails All checks passed! (no exclude used to mask).
- 2026-06-14T19:48:38Z [implementation] — AC1: ✓ 64 blind-except in harness/**/mcp (14 files) reasoned-noqa'd. AC2: ✓ ruff check . clean whole-tree (was 64) — test_no_unannotated_blind_except_whole_tree uses '.'. AC3: ✓ mypy clean (208), comment-only. AC4: ✓ bootstrap re-run. Knowledge: memory #170 (CI-scope vs full-tree ruff). Root cause (category: process): BLE001 enablement under-scoped to CI paths. Prevention: whole-tree guard test. Negative: new unannotated blind except anywhere fails ruff check . (no exclude mask).
