---
slug: stack-registry-tests
title: "Unit tests for StackRegistry"
status: done
epic: v16-plugin-arch-and-docs
story: plugin-foundation
complexity: medium
role: qa
stack: python
tier: null
call_budget: null
defect_of: null
scope: "tests/test_stack_registry.py (NEW)"
scope_exclude: "scripts/* (тестируем существующее), other tests (только новый файл)"
relevant_files:
  - "tests/test_stack_registry.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T16:39:54Z"
---

## Goal

Comprehensive unit tests for stack_registry: malformed JSON skipped with warning, conflicting names (built-in vs user), empty dir, missing schema, deep-merge correctness (partial gate override, null removal, extensions_extra additive), unknown 'extends' target → error, multiple users layered. Cover all error paths.

## Acceptance Criteria

1. tests/test_stack_registry.py создан, минимум 12 кейсов покрывают: empty dir, missing dir, malformed JSON skipped + error captured, schema-invalid skipped + error captured, valid built-in load, duplicate name, hidden/_underscore-prefixed dirs ignored, deep-merge: gates per-key override + null disable + extensions_extra additive + base extensions preserved, unknown extends target → error, multiple users layered, reload() resets state, default_registry singleton.
2. Используем pytest tmp_path для всех файловых фикстур.
3. Импорты не требуют bootstrap (тесты идут от scripts/ через sys.path).
4. Проходят: pytest tests/test_stack_registry.py -v → 12+ pass, 0 fail.
5. test_gates.py не сломан (регрессия): pytest tests/test_gates.py -q → 84 pass.
6. Filesize: test_stack_registry.py — exempt от 400 limit (tests/ in _FILESIZE_EXEMPT_DIRS).

## Plan

## Rollback

## Journal

- 2026-04-25T16:39:51Z [implementation] — AC verified: 1. ✓ tests/test_stack_registry.py — 23 кейса в 4 классах: TestLoadBuiltin (missing/empty/valid/malformed/schema-invalid/hidden/loose-files/duplicate, 8), TestUserOverrides (extends/extensions_extra/null-disable/per-key-override/unknown-target/standalone/missing-dir, 7), TestReload (reload/cache-invalidation, 2), TestAccessors (unknown/filenames+path_hints/gates-null/gates-fresh-dict/guide-default/guide-custom, 6). 2. ✓ tmp_path для всех файловых фикстур. 3. ✓ sys.path.insert(0, scripts) — без bootstrap. 4. ✓ pytest tests/test_stack_registry.py -v: 23 passed in 0.25s. 5. ✓ pytest tests/test_gates.py -q: 84 passed (no regression). 6. ✓ Filesize: tests/ exempt от 400-limit.
