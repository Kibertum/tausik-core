---
slug: v1-5-0-finaliziruem-i-relizim-seychas-ves-otlozhennyy-obem
task: v15p-release-150
date: "2026-06-13"
edges: []
---

## Decision

v1.5.0 финализируем и релизим сейчас; весь отложенный объём (snippet/orchestrator/v15mr/v16r-RENAR/brainh) — последовательный 1.x-трек ПОСЛЕ 1.5; gmcp-* остаётся 2.0 (decision #94 в силе). CHANGELOG не пре-анонсирует невыпущенное (роадмап в task DB + TODO.md).

## Rationale

Пользователь сначала просил «всё в 1.5», но gmcp = архитектура 2.0 (request-time DB routing/standalone) — склейка 1.5=2.0 ломает версионную семантику и обрушает готовый polish-релиз в 2-3 недели стройки. Согласовали: релиз 1.5 не задерживаем, ничего не теряем (всё трекнуто), мажорный gmcp честно остаётся 2.0.
