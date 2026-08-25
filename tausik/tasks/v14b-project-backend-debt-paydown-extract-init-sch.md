---
slug: v14b-project-backend-debt-paydown-extract-init-sch
title: "v14b-project-backend-debt-paydown: extract _init_schema to backend_init.py"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/project_backend.py (изъять _init_schema body), scripts/backend_init.py (новый, init_schema free function), CHANGELOG.{md,ru.md}."
scope_exclude: "backend_crud.py, backend_queries.py, backend_graph.py, backend_migrations.py, backend_schema.py — не трогаем (schema модуль остаётся источником SCHEMA_SQL/FTS_SQL/INDEXES_SQL constant'ов; init_schema их потребляет)."
relevant_files:
  - "scripts/project_backend.py"
  - "scripts/backend_init.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-06T19:13:12Z"
---

## Goal

scripts/project_backend.py 403 строки (3 over). Извлекаем 67-строчный метод _init_schema (DDL bootstrap + version migration + FTS rebuild) в новый scripts/backend_init.py как free function init_schema(conn). project_backend.py упадёт до ~336 строк.

## Acceptance Criteria

1. scripts/backend_init.py создан, содержит free function init_schema(conn: sqlite3.Connection) -> None (полная DDL/migration логика).
2. scripts/project_backend.py < 350 строк (было 403, ожидаем ~336).
3. SQLiteBackend.__init__ вызывает init_schema(self._conn) вместо self._init_schema(); метод _init_schema удалён или сделан тонким wrapper.
4. Поведение init schema эквивалентно: тот же путь skip-DDL-если-up-to-date, тот же backup перед migration, тот же FTS rebuild после migration.
5. Full pytest 2889+ passed, 0 регрессий (включая backend-tests).
6. Negative case: попытка инициализации БД с schema_version > SCHEMA_VERSION (newer DB) поднимает RuntimeError с понятным сообщением — поведение сохранено.
7. Ruff + mypy clean.
8. Bootstrap → .claude/scripts/{project_backend.py, backend_init.py} оба синхронизированы.
9. CHANGELOG.md + CHANGELOG.ru.md: запись под Unreleased v1.4.0 polish Phase B Changed (continuing the filesize-debt-paydown thread).

## Plan

## Rollback

## Journal

- 2026-05-06T19:12:55Z [implementation] — Implementation done: backend_init.py (NEW, 96 строк) с init_schema(conn) free function. project_backend.py 403→327. SQLiteBackend.__init__ вызывает init_schema(self._conn) вместо self._init_schema(). Метод _init_schema удалён, других caller'ов не было. shutil + run_migrations импорты переехали в backend_init. Ruff + mypy clean. Full pytest 2889 passed (0 регрессий, включая backend-tests, init-tests, version-guard).
- 2026-05-06T19:13:12Z [implementation] — AC verified: 1. ✓ scripts/backend_init.py создан с init_schema(conn) free function (96 строк). 2. ✓ scripts/project_backend.py 327 строк (было 403, требование <350). 3. ✓ SQLiteBackend.__init__ вызывает init_schema(self._conn); метод _init_schema удалён полностью. 4. ✓ Поведение эквивалентно: skip-DDL-если-up-to-date, backup перед migration, FTS rebuild — full pytest covers init paths. 5. ✓ Full pytest 2889 passed, 7 skipped, 120 deselected (was 2889 baseline, 0 регрессий). 6. ✓ Negative case покрыт: RuntimeError на db_ver > SCHEMA_VERSION сохранён в init_schema, тот же текст сообщения. 7. ✓ Ruff + mypy clean. 8. ✓ Bootstrap синхронизировал .claude/scripts/{project_backend.py, backend_init.py}. 9. ✓ CHANGELOG.md/ru.md entry под Unreleased v1.4.0 polish Phase B Changed (продолжение filesize-debt-paydown thread).
