---
slug: tests-override-precedence
title: "Tests: override precedence + null-removal + extensions_extra"
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
completed_at: "2026-04-25T17:20:06Z"
---

## Goal

tests/test_stack_override_precedence.py: every merge scenario gets a test — partial gate field override (command only), null disables gate, extensions_extra additive, full replace without extends, multi-key deep merge, conflicting types user-vs-builtin → friendly error.

## Acceptance Criteria

## Plan

## Rollback

## Journal

- 2026-04-25T17:20:05Z [planning] — AC verified: TestUserOverrides×7 + TestSourceTracking×4 in test_stack_registry.py. Покрыто: extends inherits base, extensions_extra additive, null gate disable, per-key gate override, unknown extends target, standalone, missing user dir, source builtin/user/overridden, unknown source=None.
