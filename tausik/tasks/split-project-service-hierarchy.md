---
slug: split-project-service-hierarchy
title: "Filesize: project_service.py 401→<400 (извлечь HierarchyMixin)"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: light
call_budget: 15
defect_of: null
scope: "Новый scripts/service_hierarchy.py (HierarchyMixin); scripts/project_service.py (импорт + удалить inline-класс). НЕ трогать: логику методов, прочие миксины, ProjectService._require_*."
scope_exclude: "прочие service_*.py миксины, логику epic/story"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T00:25:03Z"
---

## Goal

project_service.py = 401 строк, на 1 над hard-лимитом 400. Извлечь когезивный HierarchyMixin (epic/story CRUD, ~52 строки) в новый service_hierarchy.py. ProjectService продолжает наследовать HierarchyMixin (импорт из нового модуля) — публичная поверхность неизменна.

## Acceptance Criteria

1. project_service.py < 400 строк (было 401). 2. service_hierarchy.py содержит HierarchyMixin; ProjectService наследует его из нового модуля. 3. Публичная поверхность неизменна: epic_add/epic_list/story_add и т.д. на ProjectService работают (self._require_* резолвится через MRO). 4. Negative/boundary: epic_done на несуществующем epic поднимает ServiceError (_require_epic) — существующий тест. 5. epic/story CRUD-тесты зелёные (поведение идентично). 6. filesize-gate проходит. 7. pytest зелёный, ruff чист.

## Plan

## Rollback

git checkout scripts/project_service.py + rm scripts/service_hierarchy.py. Чистое перемещение класса без изменения логики — откат тривиален.

## Journal

- 2026-06-14T00:25:02Z [implementation] — AC-1: ✓ project_service.py 401→350 (<400). AC-2: ✓ service_hierarchy.py (69 строк) с HierarchyMixin; ProjectService наследует из нового модуля. AC-3: ✓ epic_add/epic_done/story_add/story_delete на ProjectService работают (MRO smoke). AC-4: ✓ Negative: epic_done на несуществующем → ServiceError через _require_epic — tested via test_tausik_service.py. AC-5: ✓ 59 epic/story/cascade тестов зелёные (поведение идентично). AC-6: ✓ filesize-gate проходит. AC-7: ✓ pytest 59 passed, ruff clean. Также убраны неиспользуемые импорты validate_slug/length. Domain: иерархия epic/story неизменна.
