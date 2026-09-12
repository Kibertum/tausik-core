---
slug: ogranichit-parent-tree-pretenzii-done-zadach-usloviem
title: "Ограничить parent-tree претензии done-задач условием completed_at >= started_at верифицируемой задач"
type: dead_end
tags:
  - ownership
  - release-1.9
  - verify
task: ownership-projection-is-not-a-competing-claim
edges: []
---

Approach: Ограничить parent-tree претензии done-задач условием completed_at >= started_at верифицируемой задачи, чтобы старые закрытые задачи не создавали ambiguous
Reason: Замерено прототипом на реальной истории с 2026-09-10: для пяти задач 1.9 остаток undeclared не изменился (agents-skill-count-14 16→16), а для write-gate-is-blind-to-pathlib-writes вырос 42→43 — единственный уникальный владелец одного пути был старой done-задачей. Шум создают не done-задачи, а плоское объединение проекций с ACL-претензиями; ярусы решают это без временной границы.
