---
slug: consumer-gate-dispatch
title: "gate_stack_dispatch._EXT_TO_STACKS computed"
status: done
epic: v16-plugin-arch-and-docs
story: refactor-consumers
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/gate_stack_dispatch.py"
scope_exclude: "scripts/stack_registry.py, остальные consumers"
relevant_files:
  - "scripts/gate_stack_dispatch.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T17:01:34Z"
---

## Goal

Replace hardcoded _EXT_TO_STACKS dict with on-demand computation from registry.extensions_for(stack). _FILENAME_TO_STACKS + _PATH_HINTS stay (those are heuristics, not stack-owned data — they remain in dispatch module). infer_stacks_from_files / gate_applies_to / skipped_result keep public API.

## Acceptance Criteria

1. scripts/gate_stack_dispatch.py: _EXT_TO_STACKS, _FILENAME_TO_STACKS, _PATH_HINTS вычисляются из registry (default_registry().extensions_for/filenames_for/path_hints_for) для каждого stack.
2. infer_stacks_from_files сохраняет API/семантику.
3. Hardcoded fallback оставлен на случай import error.
4. Тесты test_gates.py + test_iac_bootstrap_detection.py: 0 регрессий.
5. .py → {python, fastapi, django, flask}; .ts → 6+ стэков (typescript, react, next, vue, nuxt, svelte); .blade.php → blade+laravel+php (или хотя бы blade — проверим как registry это представляет).
6. **Negative scenario:** registry import error → fallback на хардкод-индекс, gate_applies_to работает без падения.
7. Filesize: gate_stack_dispatch.py под 400 строк.

## Plan

## Rollback

## Journal

- 2026-04-25T17:01:33Z [implementation] — AC verified: 1. ✓ _EXT_TO_STACKS/_FILENAME_TO_STACKS/_PATH_HINTS вычисляются через _build_dispatch_tables() из registry. 2. ✓ infer_stacks_from_files API/семантика идентична: foo.py → {django,fastapi,flask,python}; foo.blade.php → {blade,laravel,php}. 3. ✓ Hardcoded _FALLBACK_* оставлены. 4. ✓ pytest 307 passed (test_gates+iac+stack_registry+skills_maturity), 0 регрессий. 5. ✓ Compound extension .blade.php → union с .php стэками сохранена через post-build trick. 6. ✓ Negative scenario: try/except → fallback на hardcoded tables. 7. ✓ Filesize: gate_stack_dispatch.py 177 строк <400.
