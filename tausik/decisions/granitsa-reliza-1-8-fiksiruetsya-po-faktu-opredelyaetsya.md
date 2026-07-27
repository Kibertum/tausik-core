---
slug: granitsa-reliza-1-8-fiksiruetsya-po-faktu-opredelyaetsya
task: null
date: "2026-07-20"
edges: []
---

## Decision

Граница релиза 1.8 фиксируется ПО ФАКТУ: определяется членством в эпике landscape-2026-h2, а НЕ числом «35» из #141. В 1.8 входят ВСЕ задачи landscape-2026-h2 (закрытые + planning/blocked), КРОМЕ помеченных тегами отсрочки [2.0]/[POST-1.4]/[DEFERRED] (v2-stale-mcp-reaping, v2-mcp-request-time-db-routing, v14b-followup-remeasure). НЕ входят: v2-global-mcp, vscode-extension, shared-knowledge/kb-*, km-knowledge-layer, brain-hardening. Объём ~51. Перебивает число 35 из #141; поправка #154 в силе.

## Rationale

Число 35 из #141 разошлось с фактом (~51), 5 сессий блокировало планирование. Владелец в #126 выбрал «зафиксировать по факту». Счётный лимит хрупок — дефекты заводятся догфудом каждую сессию (4 за #125); членство в эпике устойчиво. Теги отсрочки уже в заголовках — детерминированный критерий исключения.
