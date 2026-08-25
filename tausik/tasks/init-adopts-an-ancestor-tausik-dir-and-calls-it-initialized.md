---
slug: init-adopts-an-ancestor-tausik-dir-and-calls-it-initialized
title: "tausik init усыновляет чужой .tausik выше по дереву и рапортует «Project initialized»"
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
scope_exclude: "harness/** — дефект в CLI-слое, харнесс не трогаем; миграции схемы БД"
relevant_files:
  - "scripts/project_cli.py"
  - "scripts/project_parser.py"
  - "tests/test_init_creates_where_you_stand.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/**"
  - "tests/*.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-08-12T18:10:18Z"
---

## Goal

init СОЗДАЁТ проект там, где стоит пользователь, либо ОТКАЗЫВАЕТ вслух. Молчаливое усыновление предка запрещено.

## Acceptance Criteria

1. В ПУСТОМ каталоге под домашним, где существует ~/.tausik, «init --name probe» создаёт .tausik ЗДЕСЬ. Воспроизведение ДО правки зафиксировано: команда печатает «Database: C:\Users\<u>\.tausik\tausik.db» и «Project 'probe' initialized», а в текущем каталоге не появляется НИЧЕГО — сообщение об успехе ложно.
2. Данные нового проекта не попадают в пользовательский тир: после init база проекта пуста, а хеш ~/.tausik/tausik.db не изменился (сравнение md5 до и после).
3. НЕГАТИВНЫЙ: повторный init в УЖЕ инициализированном каталоге не разрушает существующий проект и говорит об этом явно. Лечение не должно затирать данные.
4. НЕГАТИВНЫЙ: init в подкаталоге настоящего проекта (<proj>/src) НЕ плодит второй .tausik молча — либо отказ с названием найденного корня, либо явное подтверждение намерения.
5. Набор тестов перестаёт писать в ~/.tausik/tausik.db разработчика: хеш файла до и после прогона tests/test_graph_memory.py::TestGraphCLI совпадает. Сейчас — меняется.

## Plan

## Rollback

git revert коммита

## Journal

- 2026-08-12T17:21:14Z [implementation] — Задача ждёт границу. Разбор: init на scripts/project_cli.py:46 зовёт find_tausik_dir() — то есть ИЩЕТ вместо того, чтобы СОЗДАВАТЬ, и восходящий поиск отдаёт ему предка. Но простой отказ на любом найденном предке нарушил бы AC-1: пустой каталог под домом, где есть ~/.tausik, обязан инициализироваться, а не отказать. Значит init не может быть исправлен раньше, чем восходящий поиск научится отличать пользовательский тир от проекта. Порядок: сперва commands-outside-a-project-attach-to-the-user-config-tier, затем эта.
- 2026-08-12T18:10:16Z [implementation] — AC-1 (init в пустом каталоге под домом с тиром создаёт .tausik ЗДЕСЬ): ✓ tests/test_init_creates_where_you_stand.py::test_init_creates_the_project_in_the_current_directory. Воспроизведение ДО правки зафиксировано живым запуском: команда печатала «Config already exists: C:\Users\<u>\.tausik\config.json», «Database: C:\Users\<u>\.tausik\tausik.db», «Project 'probe' initialized», а в текущем каталоге не появлялось ничего. Причина — cmd_init звал find_tausik_dir(), то есть ИСКАЛ вместо того, чтобы СОЗДАВАТЬ. AC-2 (данные не попадают в пользовательский тир): ✓ ::test_the_user_tier_is_left_untouched — проверяется байтами тира (md5 до и после), а не словами команды: врало как раз сообщение об успехе. AC-3 (НЕГАТИВНЫЙ: повторный init не разрушает проект): ✓ ::test_a_second_init_does_not_destroy_the_first — маркерный файл внутри .tausik переживает второй запуск, вывод содержит «already exists». AC-4 (НЕГАТИВНЫЙ: init в подкаталоге проекта не плодит второй молча): ✓ ::test_init_inside_a_real_project_refuses_and_names_the_root — отказ с кодом 1 НАЗЫВАЕТ найденный корень; ✓ ::test_the_nested_case_stays_reachable_with_here — намеренный вложенный проект остаётся возможен через --here, потому что отказ, который нельзя обойти, превращает лечение в новую болезнь. AC-5 (набор тестов перестаёт писать в ~/.tausik/tausik.db): ✓ MANUAL: md5 домашней базы до полного прогона d7efc3a0f407c23af83c60f8f61b0682, после — тот же. До правки хеш менялся каждым прогоном. Полный прогон: 6990 passed, 24 skipped, 0 failed. ruff чист. Domain: проверено живыми запусками CLI в четырёх раскладках (пустой каталог, повторный запуск, подкаталог проекта, подкаталог с --here) — не только вызовами функций: внутренний контракт может быть верен, а точка входа его не звать, и дефект жил именно так.
