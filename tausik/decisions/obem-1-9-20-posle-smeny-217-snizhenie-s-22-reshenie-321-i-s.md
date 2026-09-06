---
slug: obem-1-9-20-posle-smeny-217-snizhenie-s-22-reshenie-321-i-s
task: mcp-metrics-answers-one-line-where-cli-prints-the-report
date: "2026-09-06"
edges: []
---

## Decision

ОБЪЁМ 1.9 = 20 ПОСЛЕ СМЕНЫ #217, снижение с 22 (решение #321) и с 20 на входе смены. Пересчитано КОМАНДОЙ по шести историям: gates-declare-what-they-prevent 7 (1 BLOCKED), renar-contract-contour 5, evidence-primitives 4, test-evidence-not-test-volume 4, renar-debt-implemented-wrong 0, standards-drift-detection 0. Точки: 35,38,37,39,42,40,42,43,39,34,32,28,32,31,29,25,23,21,20,22,20.

## Rationale

Смена #217 закрыла ТРИ задачи и завела три: одна из заведённых закрыта в ту же смену. Итог: вход 20, заведено 3 (→23 по ходу), закрыто 3 (one-implementation-per-command-mcp-over-cli, roadmap-freshness-fires-on-which-task-is-active, mcp-metrics-answers-one-line-where-cli-prints-the-report) → 20.

ОБЪЁМ НЕ СДВИНУЛСЯ, НО СОДЕРЖАНИЕ СМЕНИЛОСЬ: три задачи ушли, две новые остались в остатке (mcp-verify..., mcp-task-show принадлежит другому эпику). Обе — не догадки: инвентарь по AST дал 17 вторых реализаций, 15 схлопнуто, две объявлены с причиной.

ЧИСТЫЙ ЭФФЕКТ ДЛЯ РЕЛИЗА: храповик вторых реализаций теперь машинный и сжимающийся — паритет MCP и CLI перестал быть предметом чтения кода. Это ровно то, ради чего #256 назвал 1.9 рефакторингом ядра доказательства.
