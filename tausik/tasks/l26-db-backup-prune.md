---
slug: l26-db-backup-prune
title: "Прунинг .db.bak.* и стрей-каталоги в корне"
status: done
epic: landscape-2026-h2
story: l26-hygiene
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/backend_init.py"
  - "tests/test_migrations.py"
scope_tools: []
depends_on: []
completed_at: "2026-07-18T11:00:51Z"
---

## Goal

backend_init.py:80-89 создаёт .tausik/tausik.db.bak.v<N> на каждую миграцию и НИКОГДА не подчищает — накопилось 10 штук (.bak.v27..v36) около 150 МБ при живой БД 24 МБ. Нужен keep-last-N (предложение: 3) с удалением старших. Отдельно: в корне репозитория лежат пустые нетрекаемые каталоги false/ и lf/ — остаток от неудачного шелл-редиректа; удалить. Фреймворк, который поставляет hygiene-CLI, не должен мусорить в собственном дереве.

## Acceptance Criteria

1. После миграции остаются только последние N бэкапов .db.bak.v<N> (по умолчанию 3), старшие удаляются. 2. Порядок определяется по НОМЕРУ версии из имени, а не по строковой сортировке — иначе v9 окажется старше v10. 3. Прунинг best-effort: при ОШИБКЕ удаления (файл занят, права) миграция НЕ падает, ошибка логируется предупреждением. 4. Негативный кейс: при ОТСУТСТВУЮЩЕЙ директории или пустом наборе бэкапов функция не бросает исключение. 5. Тест на прунинг: создать фейковые бэкапы v1..v12, после прунинга остаются ровно 3 старшие по номеру. 6. Разово удалить пустые стрей-каталоги false и lf из корня репозитория. 7. ruff чист; сьюта миграций зелёная на 3.11 и 3.13.

## Plan

## Rollback

git revert; бэкапы снова копятся без ограничения

## Journal

- 2026-07-18T11:00:50Z [implementation] — AC-1: ✓ prune_db_backups оставляет последние keep=3 — tests/test_migrations.py::TestDbBackupPruning::test_keeps_only_the_newest_by_version_number. AC-2: ✓ порядок численный, не лексический — tests/test_migrations.py::TestDbBackupPruning::test_ordering_is_numeric_not_lexical (лексически v9 идёт после v10, строковая сортировка удалила бы новейшие). AC-3: ✓ best-effort, ошибка удаления логируется предупреждением и не прерывает миграцию; вызов помещён ПОСЛЕ успешной миграции, чтобы упавший прогон сохранил все снапшоты для отката. AC-4: ✓ отсутствующая директория не бросает — tests/test_migrations.py::TestDbBackupPruning::test_missing_directory_does_not_raise. AC-5: ✓ прунинг v1..v12 оставляет ровно 3 старшие; посторонние файлы не трогаются — tests/test_migrations.py::TestDbBackupPruning::test_unrelated_files_are_untouched. AC-6: ✓ пустые каталоги false и lf удалены из корня. AC-7: ✓ ruff чист, сьюта миграций 26 passed на 3.11 И 3.13. Negative: отсутствующая директория и набор меньше keep обрабатываются без исключения — tests/test_migrations.py::TestDbBackupPruning::test_missing_directory_does_not_raise и ::test_no_op_when_at_or_below_keep. Domain: применено к живым данным (догфудинг) — удалено 7 бэкапов v27-v33, оставлены v34-v36, каталог .tausik уменьшился 615 МБ -> 529 МБ. Разбор остатка показал, что 244 МБ это легитимный venv, а 191 МБ token_metrics.jsonl адресуется следующей задачей — скрытого мусора больше нет. Checklist: scope соблюдён (backend_init.py + test_migrations.py), покрыты порядок/границы/негатив/посторонние файлы, security surface нет, rollback = git revert (удалённые бэкапы невосстановимы, но это устаревшие снапшоты схемы v27-v33 при текущей v37).
