---
slug: override-deep-merge
title: "Deep-merge override semantics + null-removal"
status: done
epic: v16-plugin-arch-and-docs
story: user-customization
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/stack_registry.py (verification only — already implemented in stack-registry-loader)"
scope_exclude: "other files"
relevant_files:
  - "scripts/stack_registry.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T17:12:26Z"
---

## Goal

Implement deep-merge between user stack.json and built-in. Rules: dict deep-merge field-by-field; null in user means remove built-in key (e.g. gates.ruff: null disables ruff); arrays replace by default but extensions_extra adds; lists in detect REPLACE (user wants different signatures). Cover edge cases: missing 'extends', referenced unknown built-in, conflicting field types user-vs-builtin.

## Acceptance Criteria

1. StackRegistry._deep_merge реализует rules: extensions_extra additive, gates per-key override + null disable, detect/filenames/path_hints/version/guide_path replace.
2. extends: 'builtin:NAME' — inherits from base.
3. Покрыто тестами TestUserOverrides (7 tests) + TestSourceTracking (4 tests).
4. **Negative scenario:** unknown extends target → log + skip + error в self.errors (test_unknown_extends_target_recorded_and_skipped).
5. pytest tests/test_stack_registry.py 27 pass.

## Plan

## Rollback

## Journal

- 2026-04-25T17:12:23Z [implementation] — AC verified: 1. ✓ _deep_merge implemented в stack_registry.py: extensions_extra additive, gates per-key override + null disable, detect/filenames/path_hints/guide_path/version replace. 2. ✓ extends: 'builtin:NAME' — _extends_target() парсит, _resolve() merges. 3. ✓ TestUserOverrides×7 + TestSourceTracking×4 pass. 4. ✓ Negative: test_unknown_extends_target_recorded_and_skipped → user decl skipped + error в self.errors. 5. ✓ pytest tests/test_stack_registry.py: 27 passed.
