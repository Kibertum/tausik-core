---
slug: senar-v13-core
title: "SENAR v1.3 Core — rename Essential, cost metrics, ADR, session 180min"
status: done
epic: frai-v24
story: senar-v13-upgrade
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-03-26T14:27:31Z"
---

## Goal

Frai соответствует SENAR v1.3 Core: Cost per Task + Cost Predictability в metrics, ADR метрика, session limit 180 мин, checklist расширен до 23 пунктов

## Acceptance Criteria

1. frai metrics показывает Cost per Task (по complexity). 2. frai metrics показывает Cost Predictability (actual/planned). 3. ADR метрика считается: adversarial findings / L3-reviewed tasks. 4. Session limit обновлён до 180 мин (SENAR v1.3 рекомендация). 5. CLAUDE.md и docs обновлены — Essential заменён на Core. 6. /review skill расширен до 23 пунктов checklist. 7. Тесты покрывают новые метрики.

## Plan

[{"step": "backend_queries: Cost per Task \u043f\u043e complexity (simple/medium/complex)", "done": true}, {"step": "backend_queries: Cost Predictability (actual_cost/planned_cost)", "done": true}, {"step": "backend_queries: ADR \u043c\u0435\u0442\u0440\u0438\u043a\u0430 (adversarial findings / L3 tasks)", "done": true}, {"step": "project_cli: \u043e\u0431\u043d\u043e\u0432\u0438\u0442\u044c frai metrics \u0434\u043b\u044f \u043e\u0442\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u0438\u044f \u043d\u043e\u0432\u044b\u0445 \u043c\u0435\u0442\u0440\u0438\u043a", "done": true}, {"step": "Session limit: \u043e\u0431\u043d\u043e\u0432\u0438\u0442\u044c 120\u2192180 \u043c\u0438\u043d \u0432 service + CLAUDE.md", "done": true}, {"step": "Docs: Essential\u2192Core \u043f\u0435\u0440\u0435\u0438\u043c\u0435\u043d\u043e\u0432\u0430\u043d\u0438\u0435 \u043f\u043e \u0432\u0441\u0435\u043c\u0443 \u043f\u0440\u043e\u0435\u043a\u0442\u0443", "done": true}, {"step": "review skill: \u0440\u0430\u0441\u0448\u0438\u0440\u0438\u0442\u044c checklist \u0434\u043e 23 \u043f\u0443\u043d\u043a\u0442\u043e\u0432 (SENAR v1.3)", "done": true}, {"step": "\u0422\u0435\u0441\u0442\u044b \u0434\u043b\u044f \u043d\u043e\u0432\u044b\u0445 \u043c\u0435\u0442\u0440\u0438\u043a", "done": true}]

## Rollback

## Journal
