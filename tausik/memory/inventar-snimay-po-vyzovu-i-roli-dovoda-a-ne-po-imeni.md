---
slug: inventar-snimay-po-vyzovu-i-roli-dovoda-a-ne-po-imeni
title: "Инвентарь снимай по ВЫЗОВУ и роли довода, а не по имени переменной"
type: convention
tags: []
task: write-gate-resolves-a-script-path-against-the-wrong-directory
edges: []
---

В #205 инвентарь того же отождествления снимался grep по join(project_dir, expanded) и join(project_dir, path) — и пропустил четвёртое место, где переменная зовётся script. Пересъём по вызову дал 36 вхождений join(project_dir в scripts/hooks, из которых 35 приклеивают КОНСТАНТНЫЙ внутренний путь (.tausik/tausik.db и подобные) и потому верны, а внешний путь приклеивает РОВНО ОДНО. Различай в перечне константные внутренние пути и пришедшие извне: без этого единственный значимый случай тонет в трёх десятках безобидных.
