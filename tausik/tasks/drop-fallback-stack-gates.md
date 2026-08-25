---
slug: drop-fallback-stack-gates
title: "Drop _FALLBACK_STACK_GATES hardcoded copy"
status: done
epic: v131-blind-review-fixes
story: arch-layering
complexity: simple
role: developer
stack: python
tier: light
call_budget: 15
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/default_gates.py"
  - "tests/test_v131_blind_review.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-27T12:11:42Z"
---

## Goal

default_gates._FALLBACK_STACK_GATES is 190-line hardcode that drifts from stacks/&lt;name&gt;/stack.json source. Replace with empty + log warning on registry load failure. Closes HIGH (Arch).

## Acceptance Criteria

1. default_gates._FALLBACK_STACK_GATES removed (190 LOC); 2. Registry load failure logs WARNING and returns empty dict; 3. Universal gates (filesize, tdd_order, ruff, mypy, bandit) remain hardcoded since they're not stack-scoped; 4. Test simulates registry import failure and asserts no silent stale gate set; 5. Negative: removing a gate from stacks/python/stack.json does NOT leave it active via fallback.

## Plan

## Rollback

## Journal

- 2026-04-27T12:11:41Z [implementation] — AC: 1.✓ _FALLBACK_STACK_GATES (190 LOC) удалён; default_gates.py упал с 290 до 101 строк; 2.✓ _build_stack_scoped_gates() возвращает {} + log WARNING при ImportError/любом сбое; 3.✓ Universal gates (filesize, ruff, mypy, bandit, tdd_order) остались — они в UNIVERSAL_GATES; 4.✓ Тест test_default_gates_no_fallback_on_registry_failure симулирует ImportError stack_registry и подтверждает пустой dict; 5.✓ Existing tests/test_gates.py + tests/test_qg2_gates.py + tests/test_v131_blind_review.py все зелёные (108 + 11); 6.✓ Negative — удаление gate из stacks/python/stack.json больше не оставит его активным через fallback.
