---
slug: reliz-1-11-3-opublikovan-s-zamerennoy-a-ne-obeschannoy
task: null
date: "2026-10-08"
edges: []
---

## Decision

Релиз 1.11.3 опубликован с замеренной, а не обещанной экономикой: verification-цикл закрыт refusal-веткой (savings не заявляются), а Kilo-линия завершена permission-политикой на границе деплоя; GitHub main ведётся snapshot-коммитами дерева тега (решение #422), не слиянием истории.

## Rationale

Владелец приказал в чате: замеры AC-1..AC-3 естественно, без синтетики, релиз по этим числам; публикация GitLab merge + GitHub release. Snapshot-паттерн подтверждён прецедентом v1.11.2 (68b43c46).
