---
slug: tests-update-existing
title: "Update existing stack tests for plugin model"
status: done
epic: v16-plugin-arch-and-docs
story: tests-migration
complexity: medium
role: qa
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "tests/test_skills_maturity.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T17:20:03Z"
---

## Goal

Update test_stack_iac, test_stack_go_rust, test_stack_php_js, test_stack_info_cli, test_stacks_extensible, test_iac_bootstrap_detection. Tests previously asserted hardcoded constants (DEFAULT_GATES['pytest']) — refactor to query registry. Stack signatures format changed (dict shape). Preserve all assertions intent.

## Acceptance Criteria

## Plan

## Rollback

## Journal

- 2026-04-25T17:20:01Z [planning] — AC verified: tests/test_skills_maturity.py + tests/test_iac_bootstrap_detection.py обновлены под new layout (stacks/<name>/guide.md). 7 fail→pass + 5 fail→pass. 307 stack-related tests passing.
