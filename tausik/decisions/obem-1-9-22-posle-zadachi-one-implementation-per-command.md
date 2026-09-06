---
slug: obem-1-9-22-posle-zadachi-one-implementation-per-command
task: one-implementation-per-command-mcp-over-cli
date: "2026-09-06"
edges: []
---

## Decision

ОБЪЁМ 1.9 = 22 ПОСЛЕ ЗАДАЧИ one-implementation-per-command-mcp-over-cli, РОСТ с 20 (решение #320). Пересчитано КОМАНДОЙ по шести историям: gates-declare-what-they-prevent 7 (6 planning + 1 BLOCKED), evidence-primitives 6, renar-contract-contour 5, test-evidence-not-test-volume 4, renar-debt-implemented-wrong 0, standards-drift-detection 0. Точки: 35,38,37,39,42,40,42,43,39,34,32,28,32,31,29,25,23,21,20,22.

## Rationale

ПРИЧИНА РОСТА ЦИФРАМИ: закрыта одна (20→19), заведено три (19→22). Все три в истории evidence-primitives, все три — ПО ЗАМЕРУ внутри работы.

(1) mcp-verify-is-a-second-command-not-a-second-rendering (complex): tausik_verify не рендеринг, который выносится, а вторая КОМАНДА — relevant_files, кэш, квитанция, одноразовый дескриптор, код выхода. Схлопывание есть перепроектирование пути, через который идёт закрытие по QG-2.

(2) mcp-metrics-answers-one-line-where-cli-prints-the-report (medium): MCP отдаёт одну строку там, где CLI печатает весь отчёт SENAR, а CLAUDE.md велит предпочитать MCP — основной читатель видит наименьшую часть.

(3) roadmap-freshness-fires-on-which-task-is-active (simple): дефект моей же прошлой смены — карта печатает остаток ПО СТАТУСАМ, поэтому старт любой задачи делает её устаревшей.

ОТВЕРГНУТО: втянуть verify и metrics в закрытую задачу — «объём не вырос» ценой наполовину сделанной перестройки пути закрытия.
