---
slug: kb-global-version-guard
title: "Версионный гард общей базы: требовать обновления фреймворка"
status: done
epic: shared-knowledge
story: kb-global
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/knowledge_db.py"
  - "scripts/service_knowledge_aggregates.py"
  - "tests/test_knowledge_version_guard.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/knowledge_db.py"
  - "scripts/service_knowledge_aggregates.py"
  - "tests/test_knowledge_version_guard.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-08-02T17:36:01Z"
---

## Goal

Разные проекты на одной машине работают с РАЗНЫМИ версиями TAUSIK, но с ОДНОЙ общей базой знаний. Если проект со старой версией видит базу новее своей схемы — он ОБЯЗАН потребовать от пользователя обновить фреймворк, с явным сообщением и указанием обеих версий. Тихая деградация до работы без общей базы ЗАПРЕЩЕНА: это противоречит принципу нулевой толерантности к тихим ошибкам. Пользователь должен узнать о рассинхроне сразу, а не обнаружить через неделю, что подсказки перестали приходить. Обратный случай (база старее кода) — штатная миграция общей базы.

## Acceptance Criteria

1. Проект со схемой старее общей базы завершается ГРОМКОЙ ошибкой с требованием обновить фреймворк и указанием ОБЕИХ версий (кода и базы); тест проверяет текст сообщения и наличие обеих версий.
2. Тихой деградации до работы без общей базы нет: при рассинхроне путь не продолжается молча.
3. Обратный случай (база старее кода) выполняет штатную миграцию общей базы, а не блокирует.
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью об этом изменении.

## Plan

## Rollback

git revert; гард снимается

## Journal

- 2026-08-02T17:35:26Z [implementation] — ЧЕК-ЛИСТ ВЕРИФИКАЦИИ (SENAR Rule 5) — поимённые ссылки. AC-1 (громкий отказ с ОБЕИМИ версиями): ✓ tests/test_knowledge_version_guard.py::TestANewerStoreIsRefused::test_opening_raises_and_names_both_versions ✓ tests/test_knowledge_version_guard.py::TestANewerStoreIsRefused::test_the_message_says_nothing_was_touched ✓ tests/test_knowledge_version_guard.py::TestANewerStoreIsRefused::test_a_far_newer_store_is_refused_too AC-2 (нет тихой деградации): ✓ tests/test_knowledge_version_guard.py::TestNoSilentDegradation::test_a_shared_write_does_not_fall_back_to_the_project ✓ tests/test_knowledge_version_guard.py::TestNoSilentDegradation::test_a_shared_read_does_not_quietly_return_nothing ✓ tests/test_knowledge_version_guard.py::TestNoSilentDegradation::test_the_guard_is_not_swallowed_by_the_read_path_error_handling ✓ tests/test_knowledge_version_guard.py::TestTheBlockReportsSkewWithoutTakingTheSessionDown::test_the_block_still_renders_and_names_the_skew ✓ tests/test_knowledge_version_guard.py::TestTheBlockReportsSkewWithoutTakingTheSessionDown::test_the_compact_tail_behaves_the_same AC-3 (обратный случай мигрирует, а не блокирует): ✓ tests/test_knowledge_version_guard.py::TestAnOlderStoreIsNotAnError::test_an_older_store_opens_and_is_brought_up_to_date ✓ tests/test_knowledge_version_guard.py::TestAnOlderStoreIsNotAnError::test_a_store_at_this_exact_version_is_untouched_and_usable СВЕРХ AC — целостность чужой базы при отказе (найдено мной, дефект внесён на шаге 1): ✓ tests/test_knowledge_version_guard.py::TestTheStoreSurvivesTheRefusal::test_the_version_stamp_is_not_written_down ✓ tests/test_knowledge_version_guard.py::TestTheStoreSurvivesTheRefusal::test_existing_rows_are_still_there ПРОБЫ ФАЛЬСИФИЦИРУЕМОСТИ — РУЧНЫЕ ПРОГОНЫ, обратимыми правками scripts/knowledge_db.py: ✓ проба (а): условие гарда заменено на if False -> «8 failed, 2 passed» ✓ проба (б): гард переставлен ПОСЛЕ init_knowledge_schema (порядок нарушен) -> «8 failed, 2 passed», включая test_the_version_stamp_is_not_written_down; доказывает, что гарантию несёт именно ПОРЯДОК, а не наличие проверки ✓ восстановление -> «12 passed» ПРОВЕРКА ЗАПУСКОМ, определившая архитектуру: прогнал build_memory_block против базы с user_version=99 и увидел ServiceError вместо блока. То есть фатальный гард ронял старт сессии и обновление CLAUDE.md во ВСЕХ проектах машины из-за более новой базы в ОДНОМ. Это и привело к разведению по типу действия — проверка запуском, а не чтением кода. Полный набор: «6642 passed, 24 skipped, 140 deselected in 935.48s», 0 failed, 0 errors. ruff check All checks passed, ruff format already formatted, mypy Success: no issues found in 297 source files. bootstrap --ide all прогнан.
- 2026-08-02T17:35:58Z [implementation] — AC verified (поимённые ссылки на тесты — в журнале задачи): 1. ✓ ГРОМКИЙ ОТКАЗ С ОБЕИМИ ВЕРСИЯМИ. Проект, встретивший базу схемы НОВЕЕ своей, поднимает ServiceError; сообщение называет версию базы, версию кода, что сделать («Update TAUSIK in this project») и что НИЧЕГО не было тронуто. Последнее — не вежливость: читатель обязан понять, в опасности ли его данные, прежде чем решать. Проверено на +1 и на +99, то есть это не проверка на единицу разницы. 2. ✓ ТИХОЙ ДЕГРАДАЦИИ НЕТ, И ГРАНИЦА ФАТАЛЬНОСТИ ПРОВЕДЕНА ЯВНО. Запись в общую базу и поиск по ней отказывают прямо — человек попросил общее хранилище и заслуживает прямого ответа. Блок знаний ОТРИСОВЫВАЕТ отказ, но сессию не роняет. Основание — ПРОВЕРКА ЗАПУСКОМ, а не чтение: прогнав build_memory_block против базы с user_version=99, я получил исключение вместо блока, то есть более новая база в ОДНОМ проекте перестала бы давать стартовать сессию во ВСЕХ остальных. Это наказание не тех людей за рассинхрон, которого они не создавали, и ни один критерий такого не просил. Разведение записано в коде с обоснованием. 3. ✓ ОБРАТНЫЙ СЛУЧАЙ МИГРИРУЕТ. База старее кода открывается, поднимается до текущей версии и СОХРАНЯЕТ записи (тест требует ненулевого счёта после миграции — иначе «миграция» могла бы означать потерю). База ровно текущей версии не трогается и остаётся пригодной для поиска. CHANGELOG.md и зеркало CHANGELOG.ru.md — прозаическая запись. ДЕФЕКТ, ВНЕСЁННЫЙ МНОЙ НА ШАГЕ 1 И НАЙДЕННЫЙ ЗДЕСЬ: init_knowledge_schema проставляет PRAGMA user_version БЕЗУСЛОВНО. Значит старый фреймворк, открыв более новую базу, переписал бы отметку ВНИЗ — и уничтожил бы свидетельство рассинхрона не только для себя, а для ВСЕХ проектов машины: следующий заглянувший не увидел бы расхождения вовсе. Гарантию несёт ПОРЯДОК: гард стоит ДО штампа. Закреплено тестом на неизменность отметки после отказа и доказано пробой — перестановка двух строк роняет восемь тестов. ПРОБЫ ФАЛЬСИФИЦИРУЕМОСТИ, ПОТЕСТОВО: (а) условие гарда снято -> 8 failed из 12; (б) гард переставлен ПОСЛЕ инициализации схемы -> 8 failed, включая тест на неизменность отметки. Вторая проба ценнее первой: она доказывает, что работает не наличие проверки, а её МЕСТО. После восстановления 12 passed. Negative: негативные ветви проверены явно — отказ на +1 и +99, отсутствие записи штампа при отказе, сохранность существующих строк при отказе, отсутствие отката на проектную базу при записи, отсутствие тихого пустого результата при чтении, непроглатывание гарда обработчиком ошибок пути чтения (там ловятся sqlite3.Error и OSError, а ServiceError обязан пройти насквозь). Domain: осмысленно вне тестов. Сценарий не гипотетический: несколько проектов на одной машине на разных версиях фреймворка — обычный режим работы, а общий файл знаний у них ровно один. Отметка версии читается через PRAGMA user_version, который переживает копирование файла между машинами и не стоит ни таблицы, ни строки; он был проставлен на шаге 1 именно под эту задачу. Полный pytest: 6642 passed, 24 skipped, 0 failed, 0 errors (935s). ruff check — All checks passed. ruff format — already formatted. mypy — Success: no issues found in 297 source files. bootstrap --ide all прогнан, drift отсутствует.
