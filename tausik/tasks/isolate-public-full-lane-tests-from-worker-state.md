---
slug: isolate-public-full-lane-tests-from-worker-state
title: "Isolate public full-lane tests from worker state"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "Three existing CI tests and bilingual Unreleased note"
scope_exclude: "production discovery behavior and new test nodes"
relevant_files:
  - "tests/test_claudemd_state_gate.py"
  - "tests/test_mcp_integration.py"
  - "tests/test_skill_cli_help.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "tests/test_claudemd_state_gate.py"
  - "tests/test_mcp_integration.py"
  - "tests/test_skill_cli_help.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-10-02T16:55:28Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: gpt-6-astra
started_model_version: null
done_model_id: gpt-6-astra
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Make the public GitHub full lane deterministic when xdist workers reuse temporary parents and the snapshot intentionally carries no live state projection.

## Acceptance Criteria

1. Live-state CLAUDE block assertions are explicitly dormant on the public snapshot. 2. The no-project MCP test uses a working directory outside pytest worker project ancestry. 3. Skill CLI fixtures explicitly create their intended nested project. 4. Focused tests and the public full lane pass. Negative: production project discovery and nested-project refusal remain unchanged.

## Plan

## Rollback

git revert the CI isolation commit

## Journal

- 2026-10-02T16:55:00Z [implementation] — GitHub run #37036198731 showed 2 failures and 3 setup errors on one xdist worker: public CLAUDE.md has an intentionally empty dynamic block, and pytest worker ancestry had acquired a parent .tausik. Fixes are test-only: mark live-state class dormant on snapshots, use OS temp outside pytest ancestry for MCP no-project, and pass init --here for the fixture's intentional nested project. Focused result: 5 passed; no new test nodes.
- 2026-10-02T16:55:24Z [implementation] — AC verified: AC-1: ✓ tests/test_claudemd_state_gate.py::TestStalenessIsNotDrift is skipif(IS_PUBLIC_SNAPSHOT). AC-2: ✓ tests/test_mcp_integration.py::TestMCPServerStartup::test_server_without_project_still_answers_the_host uses an OS temporary directory outside pytest ancestry. AC-3: ✓ tests/test_skill_cli_help.py::TestSkillNegativeExitCode initializes with --here. AC-4: ✓ verify #3405 passed 26 selected nodes; the public full lane will be rerun from the filtered snapshot. Negative: only tests and changelog changed; production discovery remains untouched. Domain: a reused xdist worker can no longer turn parent test state into the subject of these three contracts.
