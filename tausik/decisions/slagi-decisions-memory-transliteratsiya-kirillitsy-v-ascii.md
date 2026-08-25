---
slug: slagi-decisions-memory-transliteratsiya-kirillitsy-v-ascii
task: state-git-stable-ids
date: "2026-07-25"
edges: []
---

## Decision

Слаги decisions/memory — транслитерация кириллицы в ASCII-латиницу, не Unicode и не только-id. Спека team-state-in-git.md делегировала стабилизацию слага сюда; данные русские, чистый ASCII-fold обнулил бы их в id-fallback. Транслитерация даёт переносимые, git-дружественные, читаемые tausik/<kind>/<slug>.md, одинаковые на любой машине. Таблица транслитерации и порядок дедупа (id ASC, суффикс -2/-3) ЗАМОРОЖЕНЫ: правка переслагивает историю и ломает байт-идентичный round-trip.

## Rationale
