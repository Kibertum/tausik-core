---
slug: test-root-discovery-promises-a-depth-it-does-not-reach
title: "Обнаружение корней тестов не достаёт до services/api/tests, хотя докстринг это обещает"
status: done
epic: landscape-2026-h2
story: l26-silent-failures-in-shipped-commands
complexity: simple
role: backend
stack: null
tier: light
call_budget: null
defect_of: null
scope: null
scope_exclude: "harness/**, bootstrap/** — вопрос в гейтах scripts/"
relevant_files:
  - "scripts/gate_test_resolver.py"
  - "scripts/gate_ac_check.py"
  - "tests/test_gate_test_resolver.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/**"
  - "tests/*.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-08-12T18:45:27Z"
---

## Goal

Обещание в докстринге и поведение обнаружения совпадают: либо глубина достаёт до services/api/tests, либо обещание названо честно.

## Acceptance Criteria

1. Воспроизведение ДО правки зафиксировано: test_roots(<tmp>) на дереве с services/api/tests/test_x.py возвращает [], тогда как docstring _DISCOVERY_DEPTH (scripts/gate_test_resolver.py:119-121) прямо называет services/api/tests рабочим случаем. Ложное обещание завёл тот же коммит, что и саму глубину.
2. Раскладка services/api/tests обнаруживается ЛИБО докстринг и tests/consumer_layout.py:7 перестают её обещать. Выбор назван решением, а не умолчан.
3. НЕГАТИВНЫЙ: рост глубины не подцепляет чужие тесты — вендоренные каталоги, развёрнутые профили IDE и .tausik-lib по-прежнему пропускаются. Проверяется деревом, где чужой tests/ лежит внутри пропускаемого каталога.
4. НЕГАТИВНЫЙ: ближайший уровень по-прежнему побеждает — при наличии <root>/tests обнаружение не уходит вглубь.
5. gate_test_citation отличает «корней не нашлось» от «цитата не совпала»: сейчас _test_ref_exists возвращает False в обоих случаях, и честная цитата services/api/tests/test_x.py::test_y читается как выдуманная, а чек-лист блокирует закрытие без указания настоящей причины.

## Plan

## Rollback

git revert

## Journal

- 2026-08-12T18:45:26Z [implementation] — AC-1 (воспроизведение ДО правки): ✓ MANUAL: test_roots(<tmp>) на дереве с services/api/tests/test_x.py вернул [], тогда как докстринг _DISCOVERY_DEPTH называл services/api/tests рабочим случаем. Ложное обещание приехало тем же коммитом, что и сама глубина. Найдено адверсариальным ревью партии; проверено мной лично, а не принято на слово. AC-2 (раскладка обнаруживается либо обещание снимается): ✓ tests/test_gate_test_resolver.py::TestDiscoveryReachesTheDepthItPromises::test_a_three_segment_layout_is_found — выбрано сделать обещание ИСТИННЫМ, а не убрать его: раскладка типовая для монорепозитория. Предел поднят с 2 до 3 сегментов пути. AC-3 (НЕГАТИВНЫЙ: чужие тесты не подцепляются на новой глубине): ✓ ::test_a_vendored_tree_is_not_harvested_at_the_new_depth (node_modules, .venv, .tausik-lib) ✓ ::test_a_deployed_ide_profile_is_not_harvested — каталог профиля берётся ИЗ ide_utils.all_profile_dirs(), а не выбирается автором теста. AC-4 (НЕГАТИВНЫЙ: ближайший уровень побеждает): ✓ ::test_the_nearest_level_still_wins. AC-5 (гейт цитирования отличает «корней нет» от «цитата не совпала»): ✓ MANUAL: gate_ac_check._no_test_roots_hint() на дереве без корней возвращает текст, называющий настоящую причину и лекарство testing.roots; в этом репозитории (корни есть) возвращает пустую строку. Прежний отказ выглядел одинаково в обоих случаях, и совет «поправьте цитату» был неисполним. Обнаружено СВЕРХ критериев: настроенные корни возвращались с разделителем '/', а обнаруженные — с разделителем платформы; одна функция отдавала два написания в зависимости от происхождения корня. Приведено к normpath. ✓ ::test_four_segments_are_out_of_reach_and_that_is_stated — заодно закрепляет, что объявленная граница честна и что testing.roots работает как выход за неё. Domain: замер стоимости обхода — 1 мс на этом репозитории, 0.4 мс на пустом дереве; рост глубины не делает обнаружение дорогим. Полный прогон: 6996 passed, 24 skipped, 0 failed. ruff чист.
