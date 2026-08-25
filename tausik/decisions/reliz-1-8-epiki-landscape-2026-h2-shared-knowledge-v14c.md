---
slug: reliz-1-8-epiki-landscape-2026-h2-shared-knowledge-v14c
task: null
date: "2026-07-22"
edges: []
---

## Decision

Релиз 1.8 = эпики {landscape-2026-h2, shared-knowledge} + v14c-visual-cost-dashboard + v14c-skill-web-catalog. v2-global-mcp (breaking) → мажор 2.0, вне 1.8. Notion НЕ удаляется — опциональный двусторонний sync поверх локального KB. Финальный гейт: doc-swarm (kb-docs-map → l26-narrative-honesty → kb-docs-swarm → kb-docs-consistency). CHANGELOG непрерывно. Supersedes #156.

## Rationale

Пользователь: один большой 1.8, не откладывать функционал. Но breaking по semver = 2.0, а усиление+вывод Notion противоречивы. Развязка: вся НЕ-breaking функциональность (landscape hardening + KB-фича) в 1.8; breaking global-install — заголовок 2.0; Notion живёт опцией и синхронизируется с локальным KB. brain-hardening reliability/semantic-search/capture-ux влиты в KB-трек; в 2.0 уезжает только Outline-спайк.
