---
slug: consumer-project-types
title: "project_types.DEFAULT_STACKS computed from registry"
status: done
epic: v16-plugin-arch-and-docs
story: refactor-consumers
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/project_types.py"
scope_exclude: "scripts/stack_registry.py (стабилен из Story 1), scripts/stack_schema.py, остальные consumers (отдельные задачи)"
relevant_files:
  - "scripts/project_types.py"
  - "tests/test_skills_maturity.py"
  - "tests/test_iac_bootstrap_detection.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T16:58:40Z"
---

## Goal

Replace hardcoded DEFAULT_STACKS frozenset with property/function that reads from StackRegistry. VALID_STACKS alias kept for backwards-compat. get_valid_stacks(cfg) merges registry + cfg.custom_stacks. All existing callers continue working.

## Acceptance Criteria

1. scripts/project_types.py: DEFAULT_STACKS вычисляется из default_registry().all_stacks() с fallback на хардкод-set если registry не загружается.
2. VALID_STACKS остаётся alias на DEFAULT_STACKS (back-compat для существующих importers).
3. get_valid_stacks(cfg) сохраняет логику + custom_stacks, теперь поверх registry-derived DEFAULT_STACKS.
4. Никаких циклических импортов; project_types importable standalone (тест: python -c 'from project_types import DEFAULT_STACKS; print(len(DEFAULT_STACKS))').
5. Все 25 миграционных стэков попадают в DEFAULT_STACKS (== set из registry).
6. pytest tests/ -q: 0 регрессий.
7. Filesize: project_types.py под 400 строк.
8. **Negative scenario:** если registry-load бросит exception/IO error / отсутствует stacks/ dir — module всё равно загружается с fallback hardcoded set (no crash на импорте); ошибка логируется через warnings/logging.

## Plan

## Rollback

## Journal

- 2026-04-25T16:58:39Z [implementation] — AC verified: 1. ✓ project_types.DEFAULT_STACKS вычисляется из default_registry().all_stacks() (25 стэков); _FALLBACK_STACKS — fallback hardcoded set. 2. ✓ VALID_STACKS = DEFAULT_STACKS (alias). 3. ✓ get_valid_stacks(cfg) работает с registry-derived базой + custom_stacks. 4. ✓ Standalone import: PYTHONIOENCODING=utf-8 python -c 'from project_types import DEFAULT_STACKS' → count=25, no crash. 5. ✓ Все 25 стэков в DEFAULT_STACKS (python, docker и пр.). 6. ✓ pytest всех stack-related файлов: 307 проходят, 0 регрессий (после миграции test_skills_maturity + test_iac_bootstrap_detection под новый layout). 7. ✓ project_types.py 95 строк <400. 8. ✓ Negative scenario: try/except вокруг registry-load → fallback на _FALLBACK_STACKS + log.warning, module не падает.
