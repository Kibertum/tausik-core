---
slug: v14c-visual-cost-dashboard-zakryt-kak-won-t-do-plotly-dash
task: v14c-visual-cost-dashboard
date: "2026-07-22"
edges: []
---

## Decision

v14c-visual-cost-dashboard ЗАКРЫТ как won't-do: Plotly/Dash-дашборд НЕ реализуется — противоречит stdlib-принципу проекта (CLAUDE.md: Python 3.11+ stdlib) и прецеденту dead-end #27 (отказ от ChromaDB ради stdlib). Потребность уже покрыта работающей текстовой tausik metrics --cost (AC3).

## Rationale

Отложена 3 релиза (решения #153/#141). Тяжёлая внешняя зависимость (Plotly/Dash) ради визуальной альтернативы уже работающему tausik metrics --cost не оправдана: (1) ломает заявленный stdlib-стек, (2) прецедент #27 уже отверг внешнюю тяжёлую зависимость (ChromaDB) по тем же соображениям, (3) текстовый cost-вывод функционально закрывает задачу наблюдаемости стоимости. Opt-in-extras путь тоже отклонён: даже изолированная зависимость тянет CI/поддержку ради дубля существующей функции. Честнее закрыть, чем держать вечно-deferred.
