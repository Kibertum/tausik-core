---
slug: consumer-default-gates
title: "default_gates split: universal inline + stack-scoped from registry"
status: done
epic: v16-plugin-arch-and-docs
story: refactor-consumers
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/default_gates.py"
scope_exclude: "scripts/project_config.py (без изменений), scripts/stack_registry.py"
relevant_files:
  - "scripts/default_gates.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T17:03:00Z"
---

## Goal

scripts/default_gates.py keeps only universal gates (filesize, tdd_order — gates without 'stacks' field). Stack-scoped gates removed from this file (now live in stacks/<name>/stack.json). load_gates() in project_config merges DEFAULT_GATES (universal) + registry-derived stack gates + user overrides. Backwards-compat preserved (existing get_gates_for_trigger callers see same keys).

## Acceptance Criteria

1. scripts/default_gates.py: DEFAULT_GATES = UNIVERSAL_GATES (filesize, tdd_order, ruff, mypy, bandit — gates без stacks-фильтра) ∪ registry-derived stack-scoped gates.
2. UNIVERSAL_GATES — hardcoded dict в default_gates.py.
3. _build_stack_scoped_gates() итерирует registry.all_stacks() + registry.gates_for(name), собирает union (одна gate-name может появиться в нескольких stacks — последнее wins или первое; зафиксировать поведение).
4. DEFAULT_GATES["pytest"]["stacks"] = ["python","fastapi","django","flask"] (как в registry/python).
5. DEFAULT_GATES["tsc"]["stacks"] = ["typescript","react","next","vue","nuxt","svelte"] (из registry/typescript).
6. project_config.load_gates() работает без изменений.
7. pytest tests/test_gates.py + test_stack_registry + test_iac + test_skills_maturity: 0 регрессий.
8. **Negative scenario:** registry import error → DEFAULT_GATES = UNIVERSAL_GATES + hardcoded fallback (текущий полный hardcoded словарь). Module не падает.
9. Filesize: default_gates.py под 400 строк.

## Plan

## Rollback

## Journal

- 2026-04-25T17:03:00Z [implementation] — AC verified: 1. ✓ DEFAULT_GATES=UNIVERSAL_GATES(5)∪_build_stack_scoped_gates(20)=25 total. 2. ✓ UNIVERSAL_GATES = filesize, tdd_order, ruff, mypy, bandit. 3. ✓ _build_stack_scoped_gates итерирует registry.all_stacks() в sorted order, first-wins для дубликатов имён. 4. ✓ pytest.stacks=[python,fastapi,django,flask] (из registry/python). 5. ✓ tsc.stacks=[typescript,react,next,vue,nuxt,svelte] (из registry/typescript). 6. ✓ project_config.load_gates без изменений. 7. ✓ pytest 307 passed, 0 регрессий. 8. ✓ Negative scenario: try/except → fallback на UNIVERSAL_GATES + _FALLBACK_STACK_GATES (полный hardcoded). 9. ✓ default_gates.py 292 строки <400.
