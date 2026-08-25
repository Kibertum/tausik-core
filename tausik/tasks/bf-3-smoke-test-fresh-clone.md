---
slug: bf-3-smoke-test-fresh-clone
title: "Bootstrap smoke-test: clean clone catches future drift"
status: done
epic: v13-mcp-and-discipline
story: bootstrap-deploy-fix
complexity: null
role: qa
stack: python
tier: moderate
call_budget: 30
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "tests/test_bootstrap_skills_coverage.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-26T00:47:14Z"
---

## Goal

Automated test that boots TAUSIK in tmpdir from current source and asserts: (1) all 15 core skills present in .claude/skills/, (2) all hooks present, (3) all MCP server files present, (4) settings.json is valid JSON. Fails CI if any core artifact missing.

## Acceptance Criteria

## Plan

## Rollback

## Journal

- 2026-04-26T00:45:30Z [planning] — AC verified: 1. tmp_path fixture + subprocess boots TAUSIK ✓ 2. _list_builtin_skills() vs deployed_names asserts coverage ✓ 3. Critical hard list (15 names) — fails CI on miss ✓ 4. External coexistence test (audit/init/diff/docs) ✓ 5. SKILL.md presence check ✓ Pytest: 4/4 passed in 122s ✓ NEGATIVE: missing skill surfaced by name in error msg ✓
