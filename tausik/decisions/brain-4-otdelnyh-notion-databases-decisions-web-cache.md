---
slug: brain-4-otdelnyh-notion-databases-decisions-web-cache
task: brain-db-schema
date: "2026-04-22"
edges: []
---

## Decision

Brain: 4 отдельных Notion databases (decisions, web_cache, patterns, gotchas), не единая flat с discriminator

## Rationale

Разная семантика полей (у gotchas есть Wrong/Right Way, у web_cache нет) → flat теряет нативные Notion filters/views. 4 курсора в pull-sync — единичная стоимость в клиенте, а UX-выигрыш постоянный.
