---
slug: zadacha-dobavlyayuschaya-testovyy-fayl-obyazana-prognat
title: "Задача, добавляющая ТЕСТОВЫЙ ФАЙЛ, обязана прогнать полную ленту: scoped verify его не видит"
type: convention
tags:
  - crosscutting
  - resolver
  - testing
  - verify
task: our-conformance-generator-cites-the-wrong-chapter
edges:
  - relation: relates_to
    target_type: memory
    target: novyy-modul-stav-pod-git-do-polnoy-lenty-hrapovik-vidimosti
---

Задача, ДОБАВЛЯЮЩАЯ тестовый файл, обязана прогнать ПОЛНУЮ ленту перед закрытием. Зелёный tausik verify --task этого не заменяет и не может: покрытие scoped-прогона вычисляется ИЗ relevant_files через рёбра резолвера (basename, импорты продуктовых модулей, объявленный CROSSCUTTING_SCOPE), а новый файл, который ничто не выбирает, в покрытие не попадает ПО ПОСТРОЕНИЮ.
ПОЙМАНО ЖИВЬЁМ В #199: verify --task дал зелёное на 14 из 423 файлов; полная лента дала 1 failed — tests/test_crosscutting_registry.py::TestInvisibleToEveryEdge::test_a_test_no_change_can_select_must_declare_or_be_baselined. Новый tests/test_renar_citations_resolve.py читает исходники как ДАННЫЕ и не импортирует ни одного продуктового модуля, поэтому невидим для всех рёбер.
ЧИНИТЬ ОБЪЯВЛЕНИЕМ, НЕ БАЗЛАЙНОМ: CROSSCUTTING_SCOPE = [...] с деревьями, которые тест реально стережёт. _INVISIBLE_BASELINE — для того, что объявить НЕЛЬЗЯ; если объявить можно, добавление в базлайн есть уклонение от храповика.
ПОЧЕМУ ЭТО НЕ КОСМЕТИКА: невидимый тест — не нейтральный факт, а гейт, который проходит каждый scoped-прогон, ни разу не выполнившись. Первый его настоящий отказ приходит на полной ленте и цепляется к ЧУЖОМУ изменению.
