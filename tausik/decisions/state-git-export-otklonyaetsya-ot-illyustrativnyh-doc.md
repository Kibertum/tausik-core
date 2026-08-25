---
slug: state-git-export-otklonyaetsya-ot-illyustrativnyh-doc
task: state-git-export
date: "2026-07-25"
edges: []
---

## Decision

state-git-export отклоняется от иллюстративных doc-шаблонов ради полноты round-trip, спека приведена в соответствие: memory несёт `title` (NOT NULL, слаг из него необратим), decision несёт `edges` (валидный source_type в memory_edges), task-frontmatter несёт `scope/scope_exclude/scope_tools`. Грамматику тела (секции по фиксированному набору Goal→AC→Plan→Rollback→Journal, журнал = только последняя `## Journal`) держит state-git-import, экспорт `##` в прозе не экранирует.

## Rationale

AC-2 требует сериализовать КАЖДОЕ durable-поле; slug необратим, title/edges нельзя выкинуть лишь потому, что пример их не показал. Правило 2 «фиксированный порядок ключей — часть контракта» делает порядок нормативным, спека обязана совпадать с эмиттером байт-в-байт, иначе roundtrip-gate залочит расхождение. Экранировать `##` на экспорте — преждевременное сцепление с ненаписанным импортом и нечитаемый диф; грамматика — ответственность парсера (негативный сценарий 4).
