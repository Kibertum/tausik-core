---
slug: v42-slug-race-and-silent-backfill
title: "Дефекты v42-миграции: гонка в next_slug, тихий сбой backfill, f-string SQL"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 40
defect_of: state-git-stable-ids
scope: "scripts/slug_util.py (retry + allowlist), scripts/backend_crud.py (insert-with-retry), scripts/backend_migrations_v42_backfill.py (error signal), scripts/backend_migrations_postseed.py (если нужно поднять сигнал), tests/test_state_stable_ids.py + новый tests/test_v42_slug_race.py"
scope_exclude: "детерминизм backfill (проверен, не трогаем); транслитерация не-русской кириллицы (осознанное ограничение); state-git-export"
relevant_files:
  - "scripts/slug_util.py"
  - "scripts/backend_crud.py"
  - "scripts/backend_crud_knowledge.py"
  - "scripts/project_backend.py"
  - "scripts/backend_migrations_v42_backfill.py"
  - "tests/test_v42_slug_race.py"
  - "tests/test_state_stable_ids.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-25T11:46:01Z"
---

## Goal

Ревью state-git-stable-ids нашло: (1) КРИТ — next_slug читает набор слагов и вставляет отдельным стейтментом (TOCTOU); при check_same_thread=False два конкурентных decision_add/memory_add с одинаковым базовым слагом дают либо IntegrityError-падение (если UNIQUE-индекс есть), либо тихий дубль (если backfill не отработал). Я ввёл это чтение-перед-записью в этой миграции. (2) HIGH — maybe_backfill_v42 ловит sqlite3.Error, только logger.warning, флаг не ставит, вызывающий отбрасывает результат -> тихий сбой повторяется на каждом открытии БД вечно (нарушает 'нулевую толерантность к тихим ошибкам'). (3) LOW — имя таблицы интерполируется f-строкой в SQL (сейчас безопасно, литералы, но без allowlist). Исправить: UNIQUE-индекс становится источником истины (insert + retry на IntegrityError), backfill сигналит громко (ERROR + meta-флаг ошибки, виден doctor), next_slug получает allowlist таблиц.

## Acceptance Criteria

1. Гонка устранена: слаг-выделение race-safe — при коллизии UNIQUE-индекса вставка ПОВТОРЯЕТСЯ с пере-вычисленным слагом (bounded retry), а не падает и не молча дублирует. Тест: смоделировать коллизию (вставить слаг между вычислением и записью) -> итог две РАЗНЫЕ строки с разными слагами, без исключения наружу. 2. UNIQUE-индекс — источник истины: тест, что при существующем индексе попытка вставить дубль ловится и разрешается ретраем. 3. Тихий сбой backfill устранён: при sqlite3.Error backfill логирует ERROR и пишет meta-флаг 'v42_slugs_backfill_error' с сообщением; повторный успешный прогон флаг ошибки СНИМАЕТ. НЕГАТИВ: смоделировать ошибку в backfill -> флаг ошибки выставлен, не проглочен молча. 4. f-string SQL: next_slug отвергает таблицу вне allowlist {'decisions','memory'} явной ошибкой (ValueError), а не строит произвольный SQL. НЕГАТИВ: next_slug(q,'evil; DROP',...) -> ValueError. 5. Регрессия: 18 тестов test_state_stable_ids + backend-набор зелёные; backend_crud и backend_schema остаются <400 строк. 6. Полный scoped verify зелёный.

## Plan

## Rollback

git revert коммита. Изменения локализованы в slug allocation + backfill error-signal; схема/данные не трогаются (кроме нового meta-ключа ошибки, безвредного). UNIQUE-индекс и уже проставленные слаги неизменны.

## Journal

- 2026-07-25T11:45:33Z [implementation] — AC verified (run #1319): AC-1 гонка: insert_with_slug ретраит на IntegrityError — test_a_raced_insert_retries_with_the_next_suffix (attempts==['todo','todo-2'], две разные строки, без исключения наружу). tests/test_v42_slug_race.py. AC-2 UNIQUE=источник истины: тот же тест + test_exhausted_retries_reraise_loudly (исчерпание ретраев -> IntegrityError наружу, не тихо). AC-3 тихий сбой устранён: backfill логирует ERROR + пишет meta 'v42_slugs_backfill_error'; test_a_failed_backfill_records_a_queryable_error_marker (флаг успеха НЕ выставлен), test_recovery_clears_the_error_marker (успех снимает маркер). НЕГАТИВ: смоделирован дубль-слаг -> CREATE UNIQUE INDEX падает -> маркер выставлен. AC-4 allowlist: next_slug отвергает таблицу вне {decisions,memory} ValueError — test_next_slug_rejects_an_unknown_table. НЕГАТИВ покрыт. AC-5 регрессия: 26 тестов (race+stable-ids) + 787 backend-набор зелёные; backend_crud 316<400, backend_crud_knowledge 127<400 (вынесен KnowledgeCrudMixin). AC-6: verify #1319 exit=0. Domain: под конкурентными писателями (check_same_thread=False) идентичность слагов больше не ломается — либо ретрай разводит их, либо громкая ошибка; сбойная миграция идентичности видна, а не тихо повторяется вечно. CHANGELOG EN+RU. Defect_of state-git-stable-ids.
- 2026-07-25T11:45:51Z [implementation] — Root cause (race-condition): slug-выделение в state-git-stable-ids ввело чтение набора занятых слагов и вставку отдельным стейтментом, не сделав UNIQUE-индекс атомарным арбитром — на соединении check_same_thread=False два писателя проходят окно между read и insert. Сопутствующее (missing-validation): backfill глотал sqlite3.Error без сигнала, а имя таблицы шло в SQL f-строкой без allowlist. Prevention: при наличии UNIQUE-констрейнта он и есть источник истины — insert + retry на IntegrityError, а не check-then-insert; любой best-effort путь, глотающий исключение, обязан оставлять громкий запрашиваемый след (ERROR + meta-маркер); имя таблицы в интерполируемом SQL — всегда allowlist.
- 2026-07-25T11:46:00Z [implementation] — AC verified (run #1319). Race fixed via insert_with_slug retry (UNIQUE index = source of truth); backfill loud (ERROR + queryable v42_slugs_backfill_error marker, cleared on recovery); next_slug table allowlist. 26 race/stable-ids tests + 787 backend green; KnowledgeCrudMixin extracted (backend_crud 316<400). Root cause logged (race-condition). CHANGELOG EN+RU.
