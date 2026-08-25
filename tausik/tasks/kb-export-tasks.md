---
slug: kb-export-tasks
title: "Выгрузка задач в текст репозитория"
status: done
epic: shared-knowledge
story: kb-git-sync
complexity: complex
role: architect
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: "Ничего. Карточка закрывается как ПОГЛОЩЁННАЯ эпиком team-state-in-git — собственной работы под этим слагом не выполняется, файлы не изменяются. Реализация лежит в scripts/state_export.py, scripts/state_serialize.py, scripts/state_import.py, scripts/gate_state_roundtrip.py и tests/test_state_export.py и уже прошла свои гейты под своими слагами."
relevant_files:
  - "scripts/state_export.py"
  - "scripts/state_serialize.py"
  - "scripts/state_import.py"
  - "scripts/gate_state_roundtrip.py"
  - "tests/test_state_export.py"
scope_paths:
  - "scripts/service_export.py"
scope_tools: []
depends_on: []
completed_at: "2026-07-28T19:37:27Z"
---

## Goal

Проектная БД остаётся ИСТИНОЙ, git — канал синхронизации. Начинаем с задач: slug уже уникален и мержится. Формат решает судьбу мержа: ОДИН ФАЙЛ НА СУЩНОСТЬ со стабильным порядком полей — тогда диффы минимальны и конфликт человекочитаем; один большой JSONL превращает мерж в мучение. Для задач предпочтителен markdown с фронтматтером: он читается в PR как спека, и это даёт главный побочный выигрыш — критерии приёмки начинают ревьюиться как код, вместо того чтобы быть запертыми в бинарнике. Выгружаем замысел: заголовок, цель, критерии, план, scope, rollback, статус, журнал. НЕ выгружаем доказательства (см. отдельный пункт в критериях).

## Acceptance Criteria

1. Задачи выгружаются в текст репозитория как ОДИН ФАЙЛ НА ЗАДАЧУ (markdown с фронтматтером) со стабильным порядком полей; диффы минимальны и человекочитаемы.
2. Выгружается замысел: заголовок, цель, критерии, план, scope, rollback, статус, журнал. Доказательства (гейты/receipt/подписи) НЕ выгружаются.
3. Идентификация файла по slug; повторная выгрузка без изменений в БД не порождает диффа.
4. НЕГАТИВ (добавлен ревизией revise-kb-export-tasks-superseded в сессии #153: карточка писалась до QG-0-гейта негативного сценария и его не имела; поставленная работа его закрывает, поэтому критерий дописан, а не проигнорирован). Порча и потеря видны, а не проглатываются: сущность без стабильного слага отвергает экспорт с подсказкой про миграцию вместо генерации эфемерного слага; CRLF-пересохранение файла --check считает дрейфом, а не чистым деревом; каждое удаление файла при реконсиляции печатается; висячее ребро памяти отбрасывается с предупреждением.
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью об этом изменении.

## Plan

## Rollback

git revert; выгруженные файлы удаляются, проектная БД не затронута

## Journal

- 2026-07-28T19:28:33Z [planning] — ЗАКРЫТА КАК ПОГЛОЩЁННАЯ, БЕЗ СОБСТВЕННОЙ РАБОТЫ. Ревизия revise-kb-export-tasks-superseded (сессия #153) сверила все три содержательных критерия этой карточки с фактическим деревом и назвала артефакт для КАЖДОГО. Поглотивший эпик — team-state-in-git (state-git-spec, state-git-stable-ids, state-git-export, state-git-import, gate_state_roundtrip), закрыт в этом же релизе 1.8. Критерий 1 (файл на задачу, стабильный порядок полей) → scripts/state_export.py::_task_doc + scripts/state_serialize.py; tests/test_state_export.py::test_fixed_frontmatter_key_order_for_task, ::test_export_is_deterministic_across_two_builds, ::test_shuffled_row_order_yields_identical_bytes. Критерий 2 (выгружается замысел, доказательства НЕ выгружаются) → тело файла ровно Goal/AC/Plan/Rollback/Journal; state_serialize.ENTITY_DIRS не содержит таблиц доказательств вовсе; tests/test_state_export.py::test_all_durable_fields_serialized_runtime_excluded. Критерий 3 (идентификация по slug, повторная выгрузка без диффа) → tests/test_state_export.py::test_layout_paths_use_slugs, ::test_export_idempotent_write_then_check_clean, ::test_slugless_decision_refuses_with_migration_hint. Критерий CHANGELOG → CHANGELOG.ru.md:1681 + зеркало EN. ПОЧЕМУ БЕЗ QG-2. Гейт закрытия проверяет работу, выполненную ПОД ЭТИМ слагом; здесь работа выполнена под чужими слагами и уже прошла свои гейты. Статус выставлен явно (task update --status done), а не проведён через task done — след намеренно видим: закрытие без собственного прогона обязано быть отличимо от закрытия с прогоном. Доказательства — в журнале ревизии revise-kb-export-tasks-superseded. УСТАРЕВШАЯ ПОДСКАЗКА, для истории: scope_paths карточки называл scripts/service_export.py — такого файла нет, реализация легла в scripts/state_export.py.
- 2026-07-28T19:37:24Z [implementation] — AC-1: ✓ tests/test_state_export.py::test_fixed_frontmatter_key_order_for_task, tests/test_state_export.py::test_export_is_deterministic_across_two_builds, tests/test_state_export.py::test_shuffled_row_order_yields_identical_bytes, tests/test_state_export.py::test_lf_only_and_single_trailing_newline — один файл на задачу с фиксированным порядком из 17 ключей фронтматтера, байтовый детерминизм не зависит ни от повторного построения, ни от порядка строк в БД. AC-2: ✓ tests/test_state_export.py::test_all_durable_fields_serialized_runtime_excluded — durable-поля (план, критерии, rollback, scope, scope_tools, бюджет, тир) обязаны присутствовать, рантайм-телеметрия (risk_score, attempts, claimed_by, started_at) обязана отсутствовать. Структурная часть: state_serialize.ENTITY_DIRS = (epics, stories, tasks, decisions, memory) — таблиц доказательств в проекции нет вовсе, а не отфильтрованы. AC-3: ✓ tests/test_state_export.py::test_export_idempotent_write_then_check_clean, tests/test_state_export.py::test_layout_paths_use_slugs — запись, затем check_tree пуст, затем повторная запись не меняет ни байта; путь файла строится из слага. AC-4 (негатив): ✓ tests/test_state_export.py::test_slugless_decision_refuses_with_migration_hint, tests/test_state_export.py::test_check_tree_detects_crlf_corruption, tests/test_state_export.py::test_write_tree_reports_deleted_paths_not_silently, tests/test_state_export.py::test_dangling_edge_dropped_with_warning_not_silently. AC-5 (CHANGELOG): ✓ CHANGELOG.ru.md:1681 «Состояние проекта экспортируется в git-native дерево» + парная запись в CHANGELOG.md. Новой записи эта карточка не добавляет — изменение уже описано поглотившей работой, поэтому закрытие идёт с --no-changelog. СПОСОБ ЗАКРЫТИЯ И ЕГО ЧЕСТНОСТЬ. Закрывается с --no-file-changes: под этим слагом не изменён ни один файл, и это проверяет git, а не моё слово. Объявленная область — файлы реализации, которые уже закоммичены. Критерий 4 ДОПИСАН ревизией (карточка не имела негативного сценария и не проходила QG-0); дописан, а не обойдён, и поставленная работа его закрывает четырьмя тестами. Оговорка на будущее: критерий 3 говорит о детерминизме экспортёра и выполнен, но на СВЕЖЕМ КЛОНЕ под Windows дерево всё равно разъедется — .gitattributes не закрепляет tausik/ на LF. Это слой ниже карточки, заведён отдельно как tausik-tree-gitattributes-lf и обязан быть закрыт до тега v1.8.0.
- 2026-07-28T19:37:43Z [done] — Domain: результат осмыслен вне тестов, проверено на живом репозитории в этой же сессии, а не на фикстурах. `tausik state export` отработал по реальной БД и записал 2095 файлов. Заявленный смысл карточки — «критерии приёмки начинают ревьюиться как код, вместо того чтобы быть запертыми в бинарнике» — подтверждён употреблением: вся ревизия revise-kb-export-tasks-superseded читала карточки kb-export-tasks и kb-brain-deprecate ИМЕННО из tausik/tasks/*.md, а не из БД, и построчной сверки критериев с артефактами хватило для вердикта. То есть выгруженный файл фактически сработал как спека для человека и агента. Проверка отрицанием, тоже на живых данных: чтение проекции обнаружило в ней то, чего в БД быть не должно, — обрывки синтаксиса вызова инструмента в 64 файлах (заведено как tool-call-syntax-leaks-into-entity-text). Дефект существовал в БД и был невидим, пока состояние жило в бинарнике; читаемая проекция сделала его заметным с первого взгляда. Это подтверждает не только корректность формата, но и его заявленную ценность.
