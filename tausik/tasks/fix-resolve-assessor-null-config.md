---
slug: fix-resolve-assessor-null-config
title: "Defect: resolve_assessor возвращает 'None' при null в config (str(None) coercion)"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: light
call_budget: 12
defect_of: fix-hardcode-assessor-identity
scope: "scripts/project_cli_renar.py (resolve_assessor coercion + cleanup), tests/test_renar_assessor_resolve.py (null-config test), tests/test_enum_single_source.py (collection-time hardening). НЕ трогать: формат манифеста, прочую логику."
scope_exclude: "renar_conformance.py, формат RENAR-CONFORMANCE.yaml"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T00:18:48Z"
---

## Goal

Ревью Батча 1 нашло HIGH-баг: resolve_assessor использует str(cfg.get('renar_default_assessor','')) — при JSON null ключ присутствует, get возвращает None, str(None)='None', .strip() truthy → assessor='None' (фиктивный человек в подписываемом манифесте, обходит fallback). Исправить coercion + покрыть тестом null-config. Заодно: хардненинг collection-time в test_enum_single_source (missing harness-файл не должен ронять весь модуль) и cleanup двойного if в resolve_assessor.

## Acceptance Criteria

1. resolve_assessor(None, {'renar_default_assessor': None}) возвращает FALLBACK_ASSESSOR (или git), НЕ строку 'None' — coercion через `cfg.get(key,'') or ''`. 2. Новый тест test_null_config_value_falls_through покрывает JSON-null ветку. 3. Root cause: get() с присутствующим null-ключом не подставляет default; str(None) даёт 'None' — задокументировано в коде/логе. 4. Negative: пустая строка, whitespace, None в config — все падают в git→fallback (не 'None', не ''). 5. test_enum_single_source: отсутствующий harness-файл даёт SKIP, а не collection-error всего модуля. 6. pytest зелёный, ruff чист.

## Plan

## Rollback

## Journal

- 2026-06-14T00:18:47Z [implementation] — AC-1: ✓ resolve_assessor(None,{key:None})→FALLBACK (coercion cfg.get(key) or '') — tested via tests/test_renar_assessor_resolve.py::test_null_config_value_falls_through. AC-2: ✓ +2 null-теста (fallback и git-ветка). AC-3: ✓ root cause (get с present-null не подставляет default; str(None)='None') в комментарии кода. AC-4: ✓ Negative: '', whitespace, None → git/fallback, не 'None'. AC-5: ✓ test_enum_single_source: _load возвращает None при отсутствии файла + @_NEED_MCP skipif → SKIP вместо collection-error. AC-6: ✓ pytest 14 passed, ruff clean, --check CLEAN. Domain: подписант манифеста никогда не фиктивный 'None'.
