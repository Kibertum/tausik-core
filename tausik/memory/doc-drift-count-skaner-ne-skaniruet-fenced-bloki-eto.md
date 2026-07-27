---
slug: doc-drift-count-skaner-ne-skaniruet-fenced-bloki-eto
title: "Doc-drift/count сканер НЕ сканирует fenced-блоки — это защита, не баг"
type: convention
tags:
  - doc-drift
  - false-positives
  - regex
  - scanner-design
task: doc-drift-split-and-regex
edges: []
---

Сканеры doc-drift (doc_drift_scanners/common) намеренно вырезают ```fenced-блоки перед матчингом счётчиков/версий (_strip_fenced_blocks). Числа в примерах кода иллюстративны ('add 5 tests where one parametrized covers', 'pytest ... # все тесты (4101)'). Если увидел устаревшее число ВНУТРИ fence и хочется «починить сканер, чтобы он его ловил» — НЕ делай: это вернёт весь класс ложных срабатываний, ради которого fence-strip и существует. Устаревший литерал в fence чини как ЛИТЕРАЛ вручную, сканер не трогай. Реальные пробелы сканера ищи в НЕ-fenced прозе (пример: '21 real-time hooks' в буллете README — прилагательное между числом и существительным обходило adjacency-anchored regex).
