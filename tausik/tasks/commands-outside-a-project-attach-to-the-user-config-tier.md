---
slug: commands-outside-a-project-attach-to-the-user-config-tier
title: "Команды вне проекта молча цепляются к пользовательскому тиру ~/.tausik вместо отказа"
status: done
epic: landscape-2026-h2
story: l26-silent-failures-in-shipped-commands
complexity: medium
role: backend
stack: null
tier: moderate
call_budget: null
defect_of: null
scope: null
scope_exclude: "harness/** — дефект в CLI-слое; миграции схемы БД"
relevant_files:
  - "scripts/project_config.py"
  - "scripts/project.py"
  - "tests/test_the_home_tier_is_not_a_project.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/**"
  - "tests/*.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-08-12T17:47:42Z"
---

## Goal

Восходящий поиск проекта знает границу: пользовательский тир ~/.tausik — это конфигурация, а не проект, и за проект он выдан быть не может.

## Acceptance Criteria

1. find_tausik_dir не принимает ~/.tausik за корень проекта. Причина: config_trust сам заводит ~/.tausik как ПОЛЬЗОВАТЕЛЬСКИЙ тир конфигурации, а восходящий поиск отличить его от проекта не умеет. На Windows любой pytest tmp_path лежит под C:\Users\<u>, поэтому подъём на 8 уровней всегда доходит до дома.
2. Отказ, который уже описан тестом, снова наступает: tests/test_knowledge_origin.py::TestAWriteThatCannotAttributeItselfFails — оба теста зелёные без правки самих тестов. Сейчас они красные на любой машине, где пользовательский тир существует, то есть на штатной установке.
3. НЕГАТИВНЫЙ: настоящий проект, лежащий В ДОМАШНЕМ каталоге (~/work/proj/.tausik), продолжает находиться. Граница проводится по РАВЕНСТВУ дому, а не по вхождению в него, иначе лечение отрезает законный случай.
4. НЕГАТИВНЫЙ: TAUSIK_DIR, указывающий на ~/.tausik явно, продолжает работать. Явное указание — это решение пользователя, и запрет относится к УГАДЫВАНИЮ, а не к выбору.
5. Команда чтения (status) вне любого проекта говорит «нет проекта здесь», а не показывает пустую сводку. Пустая сводка неотличима от сводки настоящего пустого проекта.

## Plan

## Rollback

git revert коммита

## Journal

- 2026-08-12T17:31:55Z [implementation] — Правил оказалось три, а не одно. (1) ~/.tausik за проект не выдаётся. (2) Подъём ОСТАНАВЛИВАЕТСЯ на доме: без остановки запрет на сам тир просто перешагивался и усыновлялось первое, что найдётся выше. (3) Команда, не являющаяся init, при отсутствии проекта отказывает вслух: SQLiteBackend разворачивает каталог и схему по факту подключения, поэтому tausik status в произвольном каталоге ЗАВОДИЛ там .tausik/tausik.db и печатал «Tasks: 0/0 done» — побочный эффект оставался на диске. Проверка поставлена на уровне команды, а не в бэкенде: бэкенду создание нужно. Две версии правки отвергнуты прогоном, обе записаны в докстрингах. Первая сравнивала пути КАК СТРОКИ: подъём приходит от TMP в коротком имени 8.3 (C:\Users\[вычеркнуто: local-path]), expanduser отдаёт длинное — написания разные, каталог один. Вопрос о ТОЖДЕСТВЕ решается realpath. Вторая выводила адрес тира из config_trust.user_config_path ради единственного источника истины — под pytest переопределение уводит тир на выброшенный путь, и дом снова становился «проектом»: переопределение переносит ФАЙЛ, а не ДОМАШНИЙ КАТАЛОГ. Итог: 80 тестов graph+origin зелёные, хеш ~/.tausik/tausik.db после прогона не меняется, 9 новых тестов в test_the_home_tier_is_not_a_project.py.
- 2026-08-12T17:47:41Z [implementation] — AC-1 (~/.tausik не принимается за корень проекта): ✓ tests/test_the_home_tier_is_not_a_project.py::test_the_home_tier_is_not_offered_as_a_project. Добавлено сверх критерия: подъём ОСТАНАВЛИВАЕТСЯ на доме — без остановки запрет на сам тир перешагивался и усыновлялся первый .tausik выше дома, в каталогах, общих для всех учётных записей ✓ ::test_the_walk_does_not_climb_above_home. AC-2 (описанный тестом отказ снова наступает, тесты не правились): ✓ tests/test_knowledge_origin.py::TestAWriteThatCannotAttributeItselfFails — оба теста зелёные, файл теста не изменён (git diff пуст). AC-3 (НЕГАТИВНЫЙ: проект внутри дома находится): ✓ ::test_a_real_project_inside_home_is_still_found — граница по равенству каталогу тира, а не по вхождению в дом. AC-4 (НЕГАТИВНЫЙ: явный TAUSIK_DIR на тир работает): ✓ ::test_an_explicit_pointer_at_the_tier_is_obeyed. AC-5 (status вне проекта говорит «нет проекта»): ✓ ::test_a_read_command_outside_a_project_is_refused ✓ ::test_the_cli_refuses_outside_a_project_and_leaves_nothing_behind — сквозная проверка живым запуском, потому что внутренний контракт может быть верен, а точка входа его не звать; именно так дефект и жил. Обнаружено и закрыто СВЕРХ критериев: SQLiteBackend разворачивает каталог и схему по факту подключения, поэтому команда ЧТЕНИЯ заводила .tausik/tausik.db там, где её набрали, и печатала «Tasks: 0/0 done» — побочный эффект оставался на диске. Проверка поставлена на уровне команды (assert_project_exists), а не в бэкенде: бэкенду создание нужно для init. Тождество каталога решается realpath, а не сравнением написаний ✓ ::test_identity_is_resolved_not_spelled. НЕГАТИВНЫЕ на право создавать: ✓ ::test_init_is_the_one_command_allowed_to_create ✓ ::test_a_command_inside_a_project_is_not_refused. Полный прогон: 6985 passed, 24 skipped, 0 failed (было 6971 passed, 5 failed). Хеш ~/.tausik/tausik.db до и после прогона совпадает — набор тестов больше не пишет в базу разработчика. ruff чист. Две отвергнутые версии правки записаны в докстрингах, а не умолчаны.
