---
slug: edit-write-v-scripts-zapuskaet-ruff-format-na-ves-fayl-u
title: "Edit/Write в scripts/ запускает ruff format на ВЕСЬ файл — у файла на пределе 500 строк это ломает filesize"
type: gotcha
tags:
  - "ruff,formatter,filesize,editing"
task: annotated-crosscutting-scope-reads-as-undeclared
edges: []
---

Смена #267: правка четырёх строк в scripts/gate_test_resolver.py инструментом Edit — PostToolUse-хук прогнал ruff format по всему файлу, переформатировал старые длинные строки, файл вырос с 500 до 502 и получил чужой дифф на 31 строку. Файл на пределе filesize и с несформатированным наследием править не Edit, а скриптом-файлом из scratchpad (git show HEAD:path + точечные замены), потом ruff check; проверять git diff --stat.
