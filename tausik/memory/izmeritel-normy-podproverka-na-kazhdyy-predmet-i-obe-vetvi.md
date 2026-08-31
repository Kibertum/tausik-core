---
slug: izmeritel-normy-podproverka-na-kazhdyy-predmet-i-obe-vetvi
title: "Измеритель нормы: подпроверка на каждый предмет, и ОБЕ ветви контроля"
type: pattern
tags:
  - conformance
  - measurer
  - mutation
  - renar
task: mandatory-clause-13-3-3-is-checked-by-counting-artifacts
edges:
  - relation: relates_to
    target_type: memory
    target: chinya-vyrozhdennyy-izmeritel-menyay-sostoyanie-testa-a-ne
  - relation: relates_to
    target_type: memory
    target: test-artefakta-ne-proveryaet-generator-nuzhny-dva-testa
---

Измеритель обязательного положения обязан иметь именованную подпроверку на КАЖДЫЙ перечислимый предмет нормы, и у каждой — ОБЕ ветви контроля. Счётчик «артефакт есть» под нормой, требующей СВОЙСТВ артефакта, не наблюдает ни одного из них: §13.3.3 требовал выпущенной AR, статуса approved при находках, подписи Архитектора и происхождения SPEC, а мерился как adapts > 0 — и был зелёным при всех четырёх нарушенных сразу. Красный контроль (нарушение краснеет) НЕДОСТАТОЧЕН: без зелёного (допустимое состояние зеленеет) оценщик, всегда возвращающий false, неотличим от работающего, и ремонт становится той же вырожденностью лицом в другую сторону. Приём, который это дал дёшево: разделить ЧТЕНИЕ субстрата (collect_state -> dataclass фактов) и ЧИСТЫЙ ОЦЕНЩИК (evaluate(state)). Тогда зелёная ветвь выражается на состоянии, которого схема физически не допускает (adapts.status не имеет approved, у specs нет колонки source), а читатель отдельно проверяется на настоящей БД там, где схема допускает.
