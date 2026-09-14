---
slug: two-slow-lane-tests-are-red-only-in-ci
title: "Two slow-lane tests are red only in CI: one asserts a shared-store artefact of the author's machine, one flushes a closed stdin on Linux"
status: done
epic: release-19-agent-effectiveness
story: verification-off-the-critical-path
complexity: simple
role: developer
stack: python
tier: light
call_budget: 15
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "tests/test_consumer_first_close.py"
  - "tests/test_mcp_integration.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - ROADMAP.md
scope_paths:
  - "tests/test_consumer_first_close.py"
  - "tests/test_mcp_integration.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - ROADMAP.md
scope_tools: []
depends_on: []
completed_at: "2026-09-14T01:38:16Z"
---

## Goal

The published full lane (GitLab #7719, tests-full, `pytest -m ''`) is red on two slow-marked tests that are green on every developer machine: (1) tests/test_consumer_first_close.py::test_блок_состояния_отрисован_bootstrap_ом asserts "Memory tail" in a FRESH consumer project's CLAUDE.md — the heading is rendered only when the tail has content, and on a developer machine the content is the shared knowledge store (~/.tausik-knowledge), which CI does not have; the test asserted an artefact of the author's machine, not the rendered block; (2) tests/test_mcp_integration.py::TestMCPServerStartup::test_server_starts_and_accepts_initialize closes proc.stdin and then calls proc.communicate(), which on Linux (CPython 3.12 subprocess._communicate) flushes stdin first and raises ValueError on the closed file; Windows takes the thread path and never flushes. Neither is a product defect; both are tests that say something false about where they run. Fix the two tests to assert what they mean: the dynamic block's own lines (## Current State, Tasks: 0/0 done) and a communicate(input=...) without a manual close.

## Acceptance Criteria

AC-1: both tests pass with -m '' locally AND in the published GitLab full lane on the pushed commit (the CI run is the evidence — the tests were already green here). AC-2 (negative): the consumer test no longer names 'Memory tail'; it asserts the lines the block renders in an empty project (## Current State, Tasks: 0/0 done), so a machine with a shared store cannot make it pass for the wrong reason. AC-3: the MCP startup test sends the initialize message through communicate(input=...) with no manual stdin close.

## Plan

## Rollback

git revert; two test files, no product code

## Journal

- 2026-09-14T01:34:32Z [implementation] — AC-2 ✓ consumer test asserts '## Current State' and 'Tasks: 0/0 done' (no 'Memory tail'); AC-3 ✓ MCP startup test uses proc.communicate(init_msg + newline, timeout=5) with no manual close; both green locally with -m '' (6 passed). AC-1: the CI half is the pushed commit's tests-full job — evidence comes from the pipeline, not from a local full lane.
- 2026-09-14T01:38:13Z [implementation] — Third fix in the same file while verifying: TestMCPNewToolHandlers::test_task_list_csv_status_schema_pattern did a bare 'from tools import TOOLS' and relied on a sibling test having inserted the MCP dir on the same xdist worker — red in the two-file scoped run (ImportError: cannot import name TOOLS from tools, unknown location), green in the full lane by ordering luck; it now inserts the path like every sibling. Scoped verify with TAUSIK_VERIFY_FULL=1 (slow marker included, two files): ruff PASS, pytest PASS, run #2660.
