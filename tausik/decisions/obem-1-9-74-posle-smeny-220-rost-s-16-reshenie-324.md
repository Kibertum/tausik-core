---
slug: obem-1-9-74-posle-smeny-220-rost-s-16-reshenie-324
task: null
date: "2026-09-06"
edges: []
---

## Decision

ОБЪЁМ 1.9 = 74 ПОСЛЕ СМЕНЫ #220, РОСТ с 16 (решение #324). Владелец отменил узкое чтение решения #256 по ОБЪЁМУ (по существу ядро доказательства RENAR остаётся частью 1.9, но не единственной). Возвращены три группы, пересчитано КОМАНДОЙ по task_list на каждую историю/эпик: (1) 4 доп. истории эпика release-19-renar-conformance вне «шести историй» — guarantees-are-not-claude-only(12), knowledge-records-what-failed-19(8), proof-and-positioning-outward(7) = 27; (2) весь эпик release-19-agent-effectiveness, 5 историй = 25; (3) история agent-output-discipline (6 задач: response-contract-*, output-economy-mode-is-shipped-but-off, no-byte-cap-rule, mcp-tool-surface-costs-44kb, response-contract-adherence-is-never-measured, output-discipline-reaches-the-agent-once) — сегодня в эпике landscape-2026-h2, переносится под 1.9. Итого 16+27+25+6=74.

## Rationale

Доклад сессии #220 назвал объём 16 по шести историям decision #319-#324. Владелец спросил, куда делось «многое», включая оптимизацию вывода. Разбор (task_list по эпикам/историям, roadmap --include_done=false) показал: решение #256 от 25.08 сузило 1.9 до ядра доказательства RENAR, из-за чего agent-effectiveness (журнал/контекст/задача-единица) и agent-output-discipline (форма ответа, экономия вывода) перестали считаться в объёме, хотя не закрыты и остаются под ярлыком 1.9 (эпик release-19-agent-effectiveness активен). Владелец выбрал вернуть все три группы.
