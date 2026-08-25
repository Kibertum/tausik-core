---
slug: schema-model-mismatch-nullable-on-upgrade
title: "tasks.model_mismatch: NOT NULL в свежей схеме, nullable на пути миграции"
status: done
epic: landscape-2026-h2
story: l26-arch-debt
complexity: complex
role: developer
stack: null
tier: light
call_budget: 25
defect_of: test-ddl-drift-verification-runs
scope: "scripts/backend_migrations_v43.py (новый — rebuild tasks, frozen DDL snapshot), scripts/backend_migrations.py (import + registry 43), scripts/backend_schema.py (SCHEMA_VERSION 42→43), tests/test_migration_v43_model_mismatch.py (новый), tests/test_schema_upgrade_parity.py (ратчеты + докстринг), CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "Порядок колонок memory (остаётся в _KNOWN_ORDER_DRIFT); backend_schema.py tasks DDL (канон не меняем, только версия); другие миграции; никакого live-Notion/внешнего эффекта"
relevant_files:
  - "scripts/backend_migrations_v43.py"
  - "scripts/backend_migrations.py"
  - "scripts/backend_schema.py"
  - "scripts/backend_migrations_postseed.py"
  - "tests/test_migration_v43_model_mismatch.py"
  - "tests/test_schema_upgrade_parity.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-27T10:42:37Z"
---

## Goal

НАЙДЕНО МЕХАНИЧЕСКИ в сессии #121 гейтом tests/test_schema_upgrade_parity.py (AC7 задачи test-ddl-drift-verification-runs), не рассуждением.

ЧТО. backend_schema.SCHEMA_SQL объявляет tasks.model_mismatch как INTEGER NOT NULL DEFAULT 0. Миграция, добавившая эту колонку, объявила её БЕЗ NOT NULL. Свежая БД: notnull=1. БД, доведённая с v1 миграциями: notnull=0.

ПОЧЕМУ ЭТО НЕ КОСМЕТИКА. Свежая схема — это БД, созданная один раз при инициализации. У всех живых проектов БД мигрированная, и там колонка ДОПУСКАЕТ NULL. Любой `WHERE model_mismatch = 0` в SQLite NULL-строку не вернёт, а `WHERE model_mismatch = 1` — тем более. То есть выборка «задачи без рассогласования модели» на обновлённой БД молча теряет строки, которых на CI (свежая схема) не бывает. Класс ровно тот же, ради которого написан гейт паритета фикстур: зелено там, где проверяют, неверно там, где работают.

ПОЧЕМУ ДЕФЕКТ НЕ ВЫСТРЕЛИЛ СЕГОДНЯ. Записи колонку всегда заполняют явно, поэтому NULL в ней пока не появляется. Это удача, а не защита: дефолт срабатывает только на INSERT, перечисляющих колонку; любой будущий путь записи, её пропускающий, даст NULL на обновлённых БД и 0 на свежих.

ЧТО СДЕЛАТЬ. Миграция-довыравниватель: на БД, где notnull=0, привести колонку к NOT NULL DEFAULT 0 (в SQLite это перестройка таблицы либо 12-шаговая процедура ALTER). Перед этим — UPDATE tasks SET model_mismatch = 0 WHERE model_mismatch IS NULL. После — убрать запись ('tasks','model_mismatch') из _KNOWN_CONSTRAINT_DRIFT в tests/test_schema_upgrade_parity.py; храповик test_known_constraint_drift_is_still_real сам упадёт на протухшей записи, если её забыть.

ГРАНИЦА. Расхождение ПОРЯДКА колонок (tasks, memory) сюда НЕ входит: оно неизбежно от ALTER TABLE ADD COLUMN, чинится только перестройкой таблиц и уже покрыто отдельным гейтом (позиционный INSERT в scripts/ запрещён механически).

## Acceptance Criteria

AC1. Миграция-довыравниватель приводит tasks.model_mismatch к INTEGER NOT NULL DEFAULT 0 на БД, где notnull=0; перед перестройкой выполняется UPDATE tasks SET model_mismatch=0 WHERE model_mismatch IS NULL (бэкфилл до NOT NULL).
AC2. НЕГАТИВНЫЙ ТЕСТ обязателен: на БД, доведённой миграциями с v1, после run_migrations PRAGMA table_info(tasks).model_mismatch notnull==1 (fails-then-passes).
AC3. Перестройка центральной таблицы tasks не теряет данных: count строк до/после равен, цепочка defect_of цела, входящие FK (decisions, memory) валидны (PRAGMA foreign_key_check пуст), fts_tasks пересобран и синхронен. INSERT выполняется с ЯВНЫМ списком 43 колонок, НЕ SELECT * (порядок на мигрированной БД иной от ALTER ADD COLUMN).
AC4. Все объекты на tasks воссозданы после перестройки: 6 индексов + 7 триггеров (3 FTS-триггера + 4 аудит-триггера).
AC5. Ратчеты обновлены: ('tasks','model_mismatch') убрана из _KNOWN_CONSTRAINT_DRIFT, 'tasks' убран из _KNOWN_ORDER_DRIFT (перестройка выровняла порядок колонок); test_known_constraint_drift_is_still_real и test_order_drift_is_confined_to_known_tables зелёные (ожидание order-drift = {'memory'}).
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью об этом изменении.

## Plan

## Rollback

Миграции необратимы by design (нет down-скриптов). Откат ДО деплоя: git revert коммита — убирает backend_migrations_v43.py, снимает регистрацию 43, возвращает SCHEMA_VERSION=42, восстанавливает ратчеты. БД, уже поднятые до v43, откатывать НЕ нужно: rebuild только ужесточает model_mismatch до NOT NULL DEFAULT 0 (данные не теряются, backfill NULL→0 семантически корректен — код всегда писал 0/1). Восстановление из бэкапа .tausik/tausik.db только если rebuild повредил бы данные — но AC3 (count/FK/fts паритет) это исключает тестом перед мержем. FK-off только на время rebuild (раннер), foreign_key_check после — гарантия целостности.

## Journal

- 2026-07-20T23:37:52Z [planning] — СЕКВЕНСИРОВАНИЕ (сессия #126, не начата осознанно): фикс требует ПЕРЕСТРОЙКИ таблицы tasks (SQLite не умеет ALTER ADD NOT NULL) — это самая опасная миграция (центральная таблица, ~43 колонки, self-FK defect_of, ссылки от task_logs.task_slug). Прецедент есть (backend_migrations_legacy.py rebuild tasks_new; раннер гейтит FK-off). ВНИМАНИЕ: INSERT обязан быть с ЯВНЫМ списком колонок (не SELECT *), т.к. порядок колонок на мигрированной БД отличается от baseline (ALTER ADD COLUMN аппендит) — позиционный INSERT разложит данные в НЕ ТЕ колонки. Перестройка ПОБОЧНО выровняет и порядок колонок → проверить, не протухнет ли ratchet порядка в test_schema_upgrade_parity (обновить, если да). После — убрать ('tasks','model_mismatch') из _KNOWN_CONSTRAINT_DRIFT (иначе test_known_constraint_drift_is_still_real упадёт). Мой column no_file_changes_declared (v41) уже NOT NULL на ОБОИХ путях — этого дефекта не имеет. Дефект не горит (записи всегда заполняют колонку явно). Достойно L3 из-за риска данных.
- 2026-07-21T08:31:24Z [planning] — КАРТА ВЗРЫВНОГО РАДИУСА (разведка сессии #127, до старта — для будущего фокус-прохода). Оценка исправлена simple→complex. Объекты на tasks, которые перестройка ОБЯЗАНА воссоздать (DROP TABLE tasks удалит все триггеры на ней): - 6 индексов: idx_tasks_story_id, idx_tasks_status, idx_tasks_slug (backend_schema.py:373-375), idx_tasks_archived_at (migrations:232), idx_tasks_started_model, idx_tasks_model_mismatch (migrations:319-320). - 3 FTS-триггера: tasks_ai/tasks_ad/tasks_au (backend_schema.py:283-294) → зеркало fts_tasks (fts5, backend_schema.py:260). Виртуальная таблица fts_tasks НЕ дропается, но её контент keyed by rowid=tasks.id → id колонки КОПИРОВАТЬ явно, иначе fts разъедется. После перестройки прогнать INSERT INTO fts_tasks(fts_tasks) VALUES('rebuild') либо пересобрать через delete+reinsert. - 4 аудит-триггера: tasks_audit_insert/status/claim/delete (backend_schema.py:347-363). FK: self-FK defect_of→tasks(slug); входящие task_slug→tasks(slug) ON DELETE SET NULL от decisions, memory (и историч. web_cache/plans, дропнуты в v9). RENAME сохраняет имя tasks и все slug → входящие FK остаются валидны при полном копировании строк. Раннер гейтит PRAGMA foreign_keys=OFF на время перестройки (прецедент backend_migrations_legacy.py). ЛОВУШКА ДУБЛИРОВАНИЯ СХЕМЫ: рукописный CREATE TABLE tasks_new = копия 43-колоночной схемы = анти-паттерн #249/#270. Решить: (а) вынести канонический tasks-DDL в единый источник, из которого читают и SCHEMA_SQL, и миграция; либо (б) принять разовое дублирование в миграции как исторический снимок (миграции по природе — снимки; но тогда пометить и обосновать). Предпочтителен (а), если не раздувает. ПЛАН v42: 1. UPDATE tasks SET model_mismatch=0 WHERE model_mismatch IS NULL (бэкфилл до NOT NULL). 2. PRAGMA foreign_keys=OFF (раннер). 3. CREATE TABLE tasks_new (полная канонная схема, model_mismatch INTEGER NOT NULL DEFAULT 0, порядок колонок = канон). 4. INSERT INTO tasks_new (<43 колонки ЯВНО>) SELECT <те же 43 ЯВНО> FROM tasks — НЕ SELECT * (порядок на мигрированной БД иной от ALTER ADD). 5. DROP TABLE tasks; ALTER TABLE tasks_new RENAME TO tasks. 6. Воссоздать 6 индексов + 7 триггеров. 7. Пересобрать fts_tasks. 8. PRAGMA foreign_key_check. ПОСЛЕ: убрать ('tasks','model_mismatch') из _KNOWN_CONSTRAINT_DRIFT (test_schema_upgrade_parity.py:51) — иначе test_known_constraint_drift_is_still_real упадёт на протухшей записи. Перестройка ПОБОЧНО выровняет порядок колонок tasks → убрать 'tasks' из _KNOWN_ORDER_DRIFT (там же:56) и проверить test_order_drift_is_confined_to_known_tables (ожидание станет {'memory'}). НЕГАТИВНЫЙ ТЕСТ обязателен: на мигрированной с v1 БД после run_migrations проверить PRAGMA table_info(tasks).model_mismatch notnull==1 И что строки/FK/fts сохранились (count до/после, defect_of-цепочка цела). L3 внешним ревьюером (separation of duties) из-за риска данных на центральной таблице.
- 2026-07-27T10:42:33Z [implementation] — AC1 (миграция-довыравниватель + бэкфилл): backend_migrations_v43.maybe_rebuild_tasks_v43 приводит tasks.model_mismatch к NOT NULL DEFAULT 0; UPDATE ... WHERE model_mismatch IS NULL перед перестройкой. test_null_value_is_backfilled_to_zero, test_model_mismatch_is_not_null_after_v43. ЖИВАЯ БД: notnull=1, 0 NULL строк. | AC2 (негативный тест на мигрированной с v1 БД): test_migration_v43_model_mismatch строит DB до v42, инъецирует NULL, применяет v43 -> notnull==1 (fails-then-passes подтверждён red-фазой). | AC3 (данные/FK/fts): count 2==2 до/после, defect_of self-FK цел, incoming FK decisions->tasks резолвится, PRAGMA foreign_key_check пуст, fts_tasks пересобран. INSERT с ЯВНЫМИ 43 колонками (не SELECT *). ЖИВАЯ БД: 1173 задачи сохранены, 0 FK violations. | AC4 (объекты): 6 индексов + 7 триггеров пересозданы verbatim; test_all_six_indexes_recreated, test_all_seven_triggers_recreated, test_audit_trigger_fires_after_rebuild. ЖИВАЯ БД: 6 idx, 7 trg, fts 3 hits. | AC5 (ратчеты): _KNOWN_CONSTRAINT_DRIFT пуст, _KNOWN_ORDER_DRIFT={memory}; test_known_constraint_drift_is_still_real + test_order_drift_is_confined_to_known_tables зелёные; +test_rebuilt_tasks_ddl_matches_including_constraints (закрыл L3-medium: гейт теперь ловит CHECK/FK/UNIQUE дрейф). | Полный pytest: 6140 passed / 0 failed (1 teardown-race от конкурентного bootstrap, проходит изолированно). CHANGELOG EN+RU. | L3: review #3 external-reviewer на claude-sonnet-5 (separation of duties, Opus author) APPROVE 0 critical/high/medium. Domain: миграция выполнена на реальной 1173-строчной БД с авто-бэкапом .bak.v42, целостность подтверждена.
- 2026-07-27T10:43:03Z [done] — Root cause (integration-mismatch): миграция v33 добавила model_mismatch через ALTER ADD COLUMN без NOT NULL (SQLite запрещает NOT NULL на ADD COLUMN), а CREATE TABLE baseline объявил NOT NULL — свежая и мигрированная схемы разошлись по строгости колонки, NULL молча терялся в WHERE model_mismatch=0/1. Prevention: гейт паритета фикстур (test_schema_upgrade_parity) теперь сравнивает не только (name,type,notnull,default), но и полный нормализованный DDL (CHECK/FK/UNIQUE) fresh vs migrated — любой будущий дрейф ограничений центральной таблицы краснит гейт. Domain: исправлено перестройкой tasks на реальной 1173-строчной БД с авто-бэкапом, целостность (count/FK/fts/defect_of) подтверждена до/после.
