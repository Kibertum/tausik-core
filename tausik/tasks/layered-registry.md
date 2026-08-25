---
slug: layered-registry
title: "Layered registry — built-in + .tausik/stacks/ user overrides"
status: done
epic: v16-plugin-arch-and-docs
story: user-customization
complexity: complex
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/stack_registry.py, tests/test_stack_registry.py"
scope_exclude: "consumers (Story 3 закрыта), bootstrap/*, stacks/*"
relevant_files:
  - "scripts/stack_registry.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T17:12:01Z"
---

## Goal

StackRegistry.load_user(.tausik/stacks/) layer composes on top of built-in. User stack with 'extends': 'builtin:NAME' deep-merges; without 'extends' is full replace; new name is new stack. Loader records source per stack ('builtin' | 'user' | 'overridden'). Caller can query is_user_overridden(name).

## Acceptance Criteria

1. StackRegistry tracks source per stack: 'builtin' | 'user' | 'overridden'.
2. is_user_overridden(name) -> bool метод.
3. source_for(name) -> str | None метод.
4. После load_builtin + load_user: stack который есть только в builtin → source='builtin'; только в user → 'user'; в обоих → 'overridden'.
5. test_stack_registry.py покрывает source tracking + is_user_overridden.
6. **Negative scenario:** unknown stack → source_for=None, is_user_overridden=False (no crash).
7. Filesize: stack_registry.py остаётся под 400 строк.

## Plan

## Rollback

## Journal

- 2026-04-25T17:11:58Z [implementation] — AC verified: 1. ✓ source_for(name) → 'builtin'|'user'|'overridden'|None. 2. ✓ is_user_overridden(name) → bool. 3. ✓ source_for/is_user_overridden реализованы в StackRegistry. 4. ✓ Тесты: builtin-only→builtin, user-only→user, both→overridden — 3 кейса. 5. ✓ TestSourceTracking — 4 кейса pass. 6. ✓ Negative: unknown stack → source_for=None, is_user_overridden=False. 7. ✓ stack_registry.py 318 строк <400.
