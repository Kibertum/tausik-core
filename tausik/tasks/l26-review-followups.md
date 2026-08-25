---
slug: l26-review-followups
title: "Остальные находки adversarial-ревью: префикс бэкапов, null в cq, якорь LIKE"
status: done
epic: landscape-2026-h2
story: l26-hygiene
complexity: medium
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
  - "scripts/service_knowledge.py"
  - "tests/test_migrations.py"
  - "tests/test_memory_cq_rows.py"
scope_tools: []
depends_on: []
completed_at: "2026-07-18T11:25:11Z"
---

## Goal

Остаток находок adversarial-ревью коммитов 7f54093/8cf58cf/e0fa959 (три CRITICAL уже закрыты отдельным дефектом). HIGH-1 prune_db_backups: проверка name.startswith(base) без разделителя после базового имени — файл db.db2.bak.v1 проходит проверку для базы db.db, поэтому бэкапы РАЗНЫХ баз с общим префиксом попадают в один пул сортировки по номеру версии, и единственный настоящий бэкап целевой базы может быть выбран на удаление. HIGH-2 build_cq_row: unit.get(insight, {}) подставляет умолчание только когда ключ ОТСУТСТВУЕТ; при явном null в JSON (частая форма ответа) вызов .get на None даёт AttributeError, который гасится внешним except, а поскольку local.extend потребляет ГЕНЕРАТОР, один битый юнит молча обрывает всю оставшуюся пачку. Существующий тест проверяет только пустой словарь, то есть уже безопасный случай. MEDIUM-1 запрос выбора FTS-таблиц использует неякорный LIKE по всему DDL, поэтому обычная таблица, где эта фраза встречается в тексте, была бы ошибочно принята за FTS5-кандидата. MEDIUM-2 тест паритета версии схемы фактически вакуумный: гард срабатывает на импорте, поэтому рассинхрон обрушит сбор тестов раньше, чем тест сможет отработать.

## Acceptance Criteria

1. prune_db_backups сопоставляет имя ТОЧНО как base + суффикс версии, поэтому бэкапы другой базы с общим префиксом не попадают в пул. 2. build_cq_row устойчив к явному null в полях insight и evidence. 3. Один некорректный cq-юнит НЕ обрывает обработку остальных — обработка идёт поэлементно, а не одним генератором под общим except. 4. Запрос выбора FTS-таблиц якорится на форме объявления виртуальной таблицы. 5. Назначение теста паритета версии схемы уточнено, чтобы он не выглядел полноценной проверкой негатива. 6. НЕГАТИВНЫЙ КЕЙС: тест с двумя базами общего префикса доказывает, что настоящий бэкап целевой базы не удаляется. 7. НЕГАТИВНЫЙ КЕЙС: тест с явным null в полях cq-юнита падает на прежнем коде. 8. ruff чист; затронутые сьюты зелёные на 3.11 и 3.13.

## Plan

## Rollback

git revert; поведение возвращается к текущему

## Journal

- 2026-07-18T11:25:10Z [implementation] — AC-1: ✓ точное сопоставление имени base + суффикс версии с normcase вместо префикса — tests/test_migrations.py::TestDbBackupPruning::test_backups_of_a_prefix_sharing_database_are_untouched. AC-2: ✓ явный null в insight и evidence обрабатывается через or {} вместо .get-умолчания, которое применяется только при ОТСУТСТВУЮЩЕМ ключе — tests/test_memory_cq_rows.py::TestCqRowShape::test_explicit_nulls_do_not_raise. AC-3: ✓ обработка cq-юнитов поэлементная с try внутри цикла, один битый юнит не обрывает пачку. AC-4: ✓ запрос якорен на CREATE VIRTUAL TABLE, обычная таблица с этой фразой в тексте DDL больше не кандидат. AC-5: ✓ назначение теста паритета задокументировано как пин, а не негатив, с указанием на реальное негативное покрытие. AC-6: ✓ см. Negative. AC-7: ✓ см. Negative. AC-8: ✓ ruff чист, 36 passed на 3.11 И 3.13. Negative: бэкапы базы с общим префиксом не трогаются и собственный единственный снапшот не удаляется — tests/test_migrations.py::TestDbBackupPruning::test_backups_of_a_prefix_sharing_database_are_untouched; явные null в полях cq-юнита не роняют — tests/test_memory_cq_rows.py::TestCqRowShape::test_explicit_nulls_do_not_raise и ::test_null_confidence_does_not_raise. Domain: НАЙДЕН ДОПОЛНИТЕЛЬНЫЙ null-путь, которого не было в ревью — domain со значением null давал TypeError на join; его поймал мой же новый тест при первом прогоне, что подтверждает не вакуумность теста. Checklist: scope соблюдён, покрыты оба HIGH и оба MEDIUM из ревью, security surface нет, rollback = git revert.
