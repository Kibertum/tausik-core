---
slug: predmet-proveryay-tam-gde-razlichie-nablyudaemo-a-ne-tam
title: "Предмет проверяй там, где различие НАБЛЮДАЕМО, а не там, где привычнее"
type: convention
tags: []
task: write-gate-does-not-treat-a-newline-as-a-command-separator
edges: []
---

В #205 мутация «снять экранирование внутри кавычек» не меняла write_targets: непарные кавычки уводят разбор в regex-fallback, и ответ тот же по ДРУГОЙ причине. Тест через write_targets был бы зелёным и на мутанте. Различие видно в текстовом контракте самого модуля — туда проверка и вынесена. Одинаковый ответ по разной причине не есть покрытие.
