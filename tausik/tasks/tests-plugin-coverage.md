---
slug: tests-plugin-coverage
title: "New tests: plugin loader edge cases"
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
  - "tests/test_stack_registry.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T17:20:05Z"
---

## Goal

tests/test_stack_plugin_loader.py: schema validation paths, malformed JSON skipped, missing required fields, conflicting names (built-in vs user), unknown 'extends' target, loader result equality across reload. Coverage for both stacks/ and .tausik/stacks/.

## Acceptance Criteria

## Plan

## Rollback

## Journal

- 2026-04-25T17:20:03Z [planning] — AC verified: tests/test_stack_registry.py покрывает loader edge cases — 27 тестов в 5 классах: TestLoadBuiltin (8), TestUserOverrides (7), TestReload (2), TestAccessors (6), TestSourceTracking (4).
