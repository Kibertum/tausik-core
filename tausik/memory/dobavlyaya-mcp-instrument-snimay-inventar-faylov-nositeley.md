---
slug: dobavlyaya-mcp-instrument-snimay-inventar-faylov-nositeley
title: "Добавляя MCP-инструмент, снимай инвентарь ФАЙЛОВ-НОСИТЕЛЕЙ ЧИСЛА командой gen_doc_constants --check И grep по старому числу — охранник видит не все формы"
type: convention
tags:
  - counts
  - docs
  - drift
  - mcp
task: review-208-doc-counts-blind-and-update-guards
edges: []
---

#208: два инструмента изменили счёт 126 -> 128; --check назвал шесть файлов, а ревью нашло ещё три (docs/ru/architecture.md «**117 project + 7 brain = 124 инструмента**», заголовки senar-compliance-matrix «MCP coverage 124 tools», ячейки таблицы README «| 124 |»), потому что парный шаблон требовал «(», а шаблон жирного — число жирным токеном; ячейки таблицы без слова tools не накрывает никто и после починки. Правило: (1) grep -rn по СТАРОМУ числу во всех docs/README/AGENTS до и после правки, а не только --check; (2) формы, найденные grep'ом и не пойманные --check, добавлять в doc_drift_common с пробой «вернул старое — красный»; (3) эти файлы — несущие для оценки сложности (#523): задача «добавить два инструмента» тронула 13 файлов.
