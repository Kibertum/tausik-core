---
slug: novyy-modul-stav-pod-git-do-polnoy-lenty-hrapovik-vidimosti
title: "Новый модуль ставь под git ДО полной ленты: храповик видимости считает только ОТСЛЕЖИВАЕМЫЕ исходники"
type: convention
tags:
  - gates
  - git
  - tests
  - visibility-ratchet
task: no-degeneracy-measure-for-our-own-mandatory-controls
edges: []
---

Замерено в #197 дважды за смену. test_crosscutting_registry::TestInvisibleToEveryEdge::test_a_test_no_change_can_select_must_declare_or_be_baselined валит новый тест-файл с формулировкой «no change to any tracked source file would ever select these tests». Ключевое слово — TRACKED: пока `scripts/<новый>.py` лежит untracked, ребро «тест -> продуктовый модуль» для храповика не существует.

**Почему заметно не сразу:** tests/test_config_policy.py в той же смене ПРОШЁЛ при untracked scripts/config_policy.py — он импортирует ещё project_config и config_trust, оба отслеживаемые, и висел на них. Упал только tests/test_gate_degeneracy.py, который импортирует РОВНО один новый модуль. То есть отказ зависит от того, сколько чужих импортов случайно оказалось в файле, и на маленьком аккуратном тесте срабатывает, а на большом — нет.

**Как применять:** `git add` нового модуля и нового теста сразу после создания, ДО первого прогона полной ленты. Починка — именно git add, а НЕ внесение файла в baseline: baseline здесь скрыл бы настоящую невидимость. Связано: [[hrapovik-vidimosti-schitaet-ryobra-rezolvera-sam]].
