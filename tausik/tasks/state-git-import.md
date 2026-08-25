---
slug: state-git-import
title: "Импорт git-native файлы → БД: идемпотентная пересборка рабочего кэша (tausik sync)"
status: done
epic: team-state-in-git
story: state-in-branch-mvp
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 120
defect_of: null
scope: "scripts/state_import.py (новый парсер+applier), scripts/state_parse.py (frontmatter+body парсер, если нужен для <400), scripts/project_cli_state.py (подкоманда import/sync), scripts/project_parser_state.py (CLI), tests/test_state_import.py + расширить tests/test_state_export.py round-trip пином"
scope_exclude: "state_export.py и state_serialize.py (сериализатор — готов, не менять кроме возможного re-use чистых хелперов чтения); схема БД/миграции (импорт использует существующий backend CRUD, не меняет схему); удаление сущностей (mirror-режим отложен — только add/update)"
relevant_files:
  - "scripts/state_import.py"
  - "scripts/state_parse.py"
  - "scripts/project_cli_state.py"
  - "tests/test_state_import.py"
scope_paths:
  - "scripts/state_import.py"
  - "scripts/state_parse.py"
  - "scripts/project_cli_state.py"
  - "scripts/project_parser_state.py"
  - "scripts/project.py"
  - "tests/test_state_import.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-07-25T17:45:02Z"
---

## Goal

Обратная сторона round-trip: дерево файлов (канонический источник правды) → пересобрать/обновить БД-кэш. Это то, что инженер запускает после git pull / git checkout, чтобы БД отражала стейт ветки.

Требования: (1) ОБРАТНОСТЬ round-trip: import(export(БД)) даёт БД, эквивалентную исходной (те же сущности, поля, связи, граф памяти). Пин тестом на реальном стейте. (2) Идемпотентность: повторный импорт без изменений файлов не трогает БД. (3) Дельта, а не полная перезапись, где возможно: изменился один файл → обновляется одна сущность (для скорости и чтобы не сбивать локальные несинхронизированные записи без нужды). (4) Явная политика на конфликт БД↔файлы: если локальная БД разошлась с файлами (незакоммиченная локальная правка vs пришедшая из pull) — что побеждает и как об этом сказано пользователю (git — источник правды, но молча терять локальную работу нельзя). (5) FTS переиндексируется. CLI: `tausik state import` / `tausik sync`.

## Acceptance Criteria

1. ОБРАТНОСТЬ round-trip: на реальном стейте import(export(БД)) даёт БД, эквивалентную исходной по множеству сущностей (tasks, task_logs, epics, stories, decisions, memory, memory_edges), их durable-полям и графу рёбер. Пин-тест: экспорт живой БД → чистая БД → импорт → сравнение множеств/полей/рёбер эквивалентно (слаги как ключи, порядок неважен). 2. ИДЕМПОТЕНТНОСТЬ: повторный импорт без изменений файлов не выполняет ни одного write в БД (проверяется счётчиком мутаций/хэшем строк). 3. ДЕЛЬТА: изменён один файл → обновляется ровно одна сущность; неизменённые файлы не трогают свои строки (по сравнению нормализованного распарсенного файла с текущей проекцией строки, не по mtime). 4. ПОЛИТИКА КОНФЛИКТА (git — источник правды, но без тихой потери): файлы побеждают по умолчанию, НО каждая перезапись локально-расходящейся строки печатается явно (что перезаписано, слаг); `--dry-run` показывает план изменений (added/updated/conflicts) без записи; ничего не удаляется молча (инкрементальный импорт НЕ удаляет сущности, которых нет в дереве — чтобы checkout одной ветки не стёр невлитое из другой). 5. FTS реиндексируется после импорта (search видит новые/изменённые сущности). 6. НЕГАТИВ битый файл: невалидный YAML-frontmatter или отсутствие обязательного slug → импорт ОТВЕРГАЕТ с ошибкой, называющей файл и проблему, и НЕ пишет частичные данные в БД (транзакционность: либо весь файл-батч применён, либо откат). 7. НЕГАТИВ грамматика тела: секции задачи восстанавливаются по фиксированному упорядоченному набору заголовков (Goal→AC→Plan→Rollback→Journal), журнал = только последняя ## Journal (негативный сценарий 4 спеки team-state-in-git.md) — тело с `## Journal` внутри Plan не подделывает журнал. 8. CLI `tausik state import` (алиас `tausik sync`) с `--dry-run`; читает дерево из tausik/. 9. Полный scoped verify зелёный.

## Plan

## Rollback

Импорт пишет в БД-кэш (пересобираемый), не в git-источник. Откат: git revert коммита кода + пересобрать БД из дерева повторным импортом или из .bak. Транзакционность батча (пункт 6) не оставляет частичного состояния. Не трогает сериализатор, схему, миграции. `--dry-run` для безопасной проверки до записи.

## Journal

- 2026-07-25T17:30:07Z [implementation] — ПАУЗА по запросу пользователя (переключение на продуктовое исследование cubest/onyx). Прогресс: QG-0 доведён (AC+scope+rollback+негативы, решение по политике конфликта: git-файлы источник правды, дельта, перезапись не молча, --dry-run). Готов и протестирован state_parse.py — формальная инверсия эмиттера (unescape_dq, parse_scalar, split_file, parse_frontmatter с block-list + edge-mapping, parse_sections по фиксированному упорядоченному набору заголовков, parse_journal). Round-trip парсера подтверждён вручную: кириллица+двоеточие в title, int call_budget, null, списки, edges, journal-строки (с фазой и без) восстанавливаются точно. НЕ начато: state_import.py (applier — читать дерево, дельта-upsert по слагу в FK-порядке epics→stories→tasks→decisions→memory→edges, task_logs append по (created_at,message,phase), транзакционность батча с откатом на ParseError, FTS rebuild через INSERT INTO <fts>(<fts>) VALUES('rebuild') см. backend_init.py:187, begin_tx/commit/rollback есть на backend), CLI import/sync подкоманда, round-trip пин-тест import(export(БД))≈БД. Возобновить отсюда со свежим контекстом.
- 2026-07-25T17:44:44Z [implementation] — Реализация завершена. state_parse.py (171, инверсия эмиттера: unescape_dq, parse_scalar, split_file, parse_frontmatter с block-list+edge-mapping, parse_sections по фиксированному упорядоченному набору заголовков, parse_journal) + state_import.py (345, read_tree/parse_tree с whole-batch abort, column-mappers, _Applier дельта-upsert по слагу, journal как МУЛЬТИМНОЖЕСТВО, edges reconstruct, FTS rebuild, транзакция + defer_foreign_keys). CLI: state import + алиас sync, --dry-run. Negative: битый файл → ParseError до любой записи (test_malformed_file_aborts_whole_batch); ## Journal в прозе Plan не подделывает журнал (test_body_heading_in_prose_does_not_forge_journal). Domain: round-trip ПИН на ЖИВОЙ БД — ре-экспорт импортированной БД байт-идентичен на всех 1956 файлах (added=1956, journal=1662, edges=3), 2-й импорт идемпотентен (0 изменений); git-wins с отчётом перезаписи; FTS ищет импортированное. Две ловушки найдены пином и закрыты (memory #311): defer_foreign_keys для самоссылочного defect_of, Counter-семантика журнала для дублей. 42 теста (11 import+31 export) PASS, ruff чист, filesize под cap, scoped verify PASS, bootstrap redeploy --ide all.
- 2026-07-25T17:45:00Z [implementation] — AC verified: 1. ✓ ОБРАТНОСТЬ round-trip: test_state_import.py::test_round_trip_reexport_is_byte_identical (ре-экспорт импортированной БД == исходное дерево); ЖИВОЙ пин: export 1953-сущностной БД → import в свежую → re-export байт-идентичен на всех 1956 файлах 2. ✓ ИДЕМПОТЕНТНОСТЬ: ::test_import_is_idempotent (2-й импорт added/updated/journal/edges все пустые); живой 2-й импорт 0 изменений 3. ✓ ДЕЛЬТА: ::test_delta_only_changed_entity_written (правка одного файла → updated==['epics/team-state'], added==[]) 4. ✓ ПОЛИТИКА КОНФЛИКТА git-wins-не-молча: ::test_git_wins_but_reports_overwrite (локальная правка БД → import перезаписывает значением файла И репортит tasks/exp в updated); ::test_dry_run_writes_nothing (--dry-run план без записи); удаление не делается (инкрементальный) 5. ✓ FTS реиндекс: ::test_fts_reindexed_after_import (memory_search находит импортированную запись) 6. ✓ НЕГАТИВ битый файл: ::test_malformed_file_aborts_whole_batch (ParseError, транзакция откатана, 0 строк в БД) + parse-фаза отделена от apply 7. ✓ НЕГАТИВ грамматика тела: ::test_body_heading_in_prose_does_not_forge_journal (## Journal в Plan остаётся в Plan, реальный журнал не подделан); ::test_duplicate_journal_lines_roundtrip_as_multiset (мультимножество) 8. ✓ CLI state import + sync: ::test_cli_state_import_roundtrip (subprocess: wipe DB → import из дерева → 1 task восстановлена); parser state import/sync с --dry-run 9. ✓ Scoped verify: pytest PASS (42 теста: 11 import + 31 export), ruff чист, filesize под cap; bootstrap redeploy --ide all
