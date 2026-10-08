---
slug: schetchik-ac-dokazatelstv-ischet-simvol-a-ne-slovo-ac1-pass
title: "Счётчик AC-доказательств ищет символ ✓, а не слово: «AC1 pass» даёт предупреждение «0 have explicit evidence markers»"
type: gotcha
tags:
  - evidence
  - qg2
  - task-done
task: nothing-checks-completeness-of-a-spec-body
edges: []
---

Замерено в #197 на закрытии nothing-checks-completeness-of-a-spec-body: `task done --evidence` с шестью подробными строками вида «AC1 pass — ...» получил «WARNING: 6 AC criteria, but only 0 have explicit evidence markers (✓)». Доказательства были, счётчик их не увидел.

**Почему:** детектор считает МАРКЕР ✓, а не смысл строки. Формулировка «AC1 pass», «AC1 выполнен», «AC1 ok» для него неотличима от отсутствия доказательства, и наоборот — одна галочка без текста засчитается.

**Как применять:** пиши «AC1 ✓ — <чем доказано>», а не «AC1 pass — ...». Дешевле поставить символ, чем объяснять на ревью, почему закрытие с полным разбором каждого критерия помечено нулём. Предупреждение НЕ блокирует закрытие, поэтому легко проехать мимо: task done завершается успешно, строка уезжает в конец вывода за списком гейтов. Альтернатива без ручных галочек — `--evidence-json` с полем status на каждый критерий.
