---
slug: otchet-pole-ustarelo-bez-migratsii-vremya-pravki-berem-iz
title: "Отчёт «поле устарело» без миграции: время правки берём из события в events, а не из новой колонки"
type: pattern
tags:
  - events
  - hierarchy
  - staleness
task: epic-and-story-descriptions-cannot-be-updated
edges: []
---

epic/story update (#208): нужно было «сколько задач добавлено после последней правки описания», а у epics/stories нет updated_at. Вместо колонки (миграция v50, откат, экспорт) — событие description_updated в append-only events при правке описания; отчёт = COUNT задач с created_at > MAX(events.created_at) или created_at группы, если событий нет. Границы: считаются только СОЗДАНИЯ (перенос задачи между историями не бьёт created_at — сказано в докстринге); правка заголовка события не пишет — иначе счётчик обнулялся бы переименованием. Отчёт печатается числом в list и намеренно не гейт: done проходит при любом stale, и это закреплено тестом.
