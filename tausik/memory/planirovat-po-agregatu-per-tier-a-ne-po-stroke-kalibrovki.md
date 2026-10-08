---
slug: planirovat-po-agregatu-per-tier-a-ne-po-stroke-kalibrovki
title: "Планировать по агрегату per-tier, а не по строке калибровки на окне n=10"
type: convention
tags:
  - calibration
  - metrics
  - planning
task: null
edges: []
---

Строка Calibration в status считается на окне n=10 и НЕПРИГОДНА для планирования: 11 августа она за один день показала и calibrated 1.06, и overestimating 0.63. Планировать надо по блоку Per-tier в metrics, который считает по популяции: на 502 закрытиях с тиром actual/budget = 0.63, причём чем крупнее задача, тем сильнее перекос в ПЕРЕоценку (substantial 0.49, deep 0.33). Ловушка в том, что волатильная строка стоит на видном месте в status и выглядит авторитетнее агрегата, спрятанного в metrics. Народное «бюджеты занижены вдвое-втрое» — это отдельные случаи, а не популяция.
