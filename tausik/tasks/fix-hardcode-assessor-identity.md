---
slug: fix-hardcode-assessor-identity
title: "RENAR conformance: убрать hardcoded 'architect-andrey-y' дефолт assessor"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: light
call_budget: 15
defect_of: null
scope: "scripts/project_cli_renar.py (резолв assessor), scripts/project_parser.py (help-текст), tests/test_renar_assessor_resolve.py (новый). НЕ трогать: renar_conformance.py (генератор), формат манифеста."
scope_exclude: "scripts/renar_conformance.py, формат RENAR-CONFORMANCE.yaml, schema"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-13T23:53:33Z"
---

## Goal

Убрать персональную identity 'architect-andrey-y', захардкоженную как дефолт assessor в `tausik renar conformance`. Сейчас любой другой пользователь без явного --assessor подпишет RENAR-CONFORMANCE.yaml чужим именем. Заменить на цепочку резолва: --assessor (explicit) → config renar_default_assessor → git user.name → нейтральный generic fallback.

## Acceptance Criteria

1. Литерал 'architect-andrey-y' отсутствует в scripts/ (grep пустой, включая help-текст парсера). 2. Новая функция резолва assessor: explicit --assessor → config['renar_default_assessor'] → git config user.name → нейтральный fallback 'unknown-assessor'. 3. Help-текст --assessor в project_parser.py обновлён, без персонального имени. 4. Юнит-тест покрывает все 4 ветки резолва (explicit / config / git / fallback). 5. Негативный сценарий: при отсутствии config и недоступном git резолвится 'unknown-assessor', НЕ падает. 6. SECURITY (threat surface: identity пишется в подписываемый conformance-манифест → мисатрибуция): резолв детерминирован и явен, generic fallback виден в манифесте как 'unknown-assessor' (не выдаёт чужого человека за подписанта). 7. pytest зелёный, ruff чистый.

## Plan

## Rollback

## Journal

- 2026-06-13T23:53:28Z [implementation] — AC verified: 1.✓ литерал 'architect-andrey-y' удалён из всех .py-источников (grep clean, осталось только в docstring теста). 2.✓ resolve_assessor() цепочка explicit→config→git→fallback реализована. 3.✓ help-текст парсера обновлён. 4.✓ 7 юнит-тестов покрывают все ветки. 5.✓ негативный сценарий test_fallback_when_nothing_resolves + test_git_helper_never_raises (не падает). 6.✓ SECURITY: fallback 'unknown-assessor' виден в манифесте, не выдаёт чужого за подписанта. 7.✓ pytest 16 passed, ruff clean. Bootstrap синхронизировал .claude/.
