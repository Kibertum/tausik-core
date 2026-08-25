---
slug: consumer-stack-gate-map
title: "project_config.STACK_GATE_MAP computed from registry"
status: done
epic: v16-plugin-arch-and-docs
story: refactor-consumers
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/project_config.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T17:04:49Z"
---

## Goal

_build_stack_gate_map() reads from registry.gates_for(stack) for each stack instead of iterating DEFAULT_GATES. auto_enable_gates_for_stacks unchanged in API. Tests pass.

## Acceptance Criteria

1. STACK_GATE_MAP в project_config.py вычисляется из DEFAULT_GATES (который сам уже registry-derived после consumer-default-gates).
2. _build_stack_gate_map() итерирует DEFAULT_GATES.items() и читает gate.stacks → корректный stack→gates mapping без изменений в project_config.
3. STACK_GATE_MAP['python'] = ['pytest'] (как раньше).
4. STACK_GATE_MAP['typescript'] содержит tsc, eslint, js-test.
5. STACK_GATE_MAP['terraform'] = ['terraform-validate'].
6. auto_enable_gates_for_stacks() работает без изменений.
7. pytest tests/test_gates.py + test_stack_registry: 0 регрессий.
8. **Negative scenario:** registry недоступен → DEFAULT_GATES fallback на _FALLBACK_STACK_GATES → STACK_GATE_MAP корректно построен из fallback. Уже покрыто defensive код в default_gates.py.

## Plan

## Rollback

## Journal

- 2026-04-25T17:03:44Z [implementation] — AC verified: 1. ✓ STACK_GATE_MAP вычисляется из DEFAULT_GATES (registry-derived after consumer-default-gates). 2. ✓ _build_stack_gate_map в project_config.py не изменён — итерирует DEFAULT_GATES.items() и читает gate.stacks. 3. ✓ python→[pytest]. 4. ✓ typescript→[eslint,js-test,tsc]. 5. ✓ terraform→[terraform-validate]. 6. ✓ auto_enable_gates_for_stacks(cfg,['python'])→['pytest'] — без изменений. 7. ✓ pytest 307 passed (no regression). 8. ✓ Negative scenario: DEFAULT_GATES fallback покрывает случай → STACK_GATE_MAP корректно строится из fallback (defensive код в default_gates.py).
