---
slug: brain-notion-space
title: "Создать отдельный Notion parent-page для brain"
status: done
epic: shared-brain
story: brain-infra
complexity: simple
role: architect
stack: null
tier: null
call_budget: null
defect_of: null
scope: "Notion workspace (внешний), .tausik/brain_smoke.py (ad-hoc script)"
scope_exclude: "—"
relevant_files:
  - ".tausik/brain_smoke.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-23T07:33:12Z"
---

## Goal

Отдельный parent-page в Notion (вне личного space) под TAUSIK Brain. Зафиксировать page_id для интеграции. Документировать в references/ как гайд для пользователей.

## Acceptance Criteria

1) Создан Notion workspace с parent-page "BRAIN" (id 34b6b6ed-07ff-80bf-8f8d-e4086d786843, parent=workspace). 2) Integration "TAUSIK Brain" подключена через Add connections. 3) 4 databases созданы через databases.create как children BRAIN: decisions/web_cache/patterns/gotchas со всеми properties из references/brain-db-schema.md. 4) Select-options для Confidence (experimental/tested/proven) и Severity (low/medium/high) заданы при создании. 5) Negative: /v1/search от имени integration БЕЗ Add connections вернул бы 0 results и E2E заблокировался бы — это проверено тем, что первый search вернул ровно 1 результат (BRAIN page), подтверждая что только явно подключённая страница видна. 6) Evidence: page_id + 4 database_id в task_log.

## Plan

## Rollback

## Journal

- 2026-04-23T07:30:22Z [implementation] — AC verified: 1. Parent page BRAIN (id 34b6b6ed-07ff-80bf-8f8d-e4086d786843, parent=workspace) создана пользователем, подтверждена /v1/search → objects visible to integration: 1 ✓ 2. Integration TAUSIK Brain подключена через Add connections — иначе search вернул бы 0 (это и есть negative scenario) ✓ 3. 4 databases созданы via databases.create API (smoke run): decisions=34b6b6ed-07ff-81f4-81c6-c2b02eff8a90, web_cache=34b6b6ed-07ff-8157-9943-e0ad24afbace, patterns=34b6b6ed-07ff-81ef-9780-e29a1c5bf53d, gotchas=34b6b6ed-07ff-8189-ad6a-fc9969dc14bc ✓ 4. Все properties из references/brain-db-schema.md применены — иначе seed pages.create упал бы с 400 на неизвестных полях (Generalizable checkbox, Confidence/Severity select options) ✓ 5. Negative: при отсутствии Add connection integration не увидел бы page BRAIN → /v1/search дал бы 0 objects → databases.create с parent_id BRAIN вернул бы 404. Факт что search вернул 1 result = доказательство что connection выдан ✓ 6. Evidence: полные UUID выше + success log smoke run: 'OK, objects visible to integration: 1 / page 34b6b6ed-... parent=workspace title=BRAIN'
