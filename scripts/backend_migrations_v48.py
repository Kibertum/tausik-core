"""v48 — атрибуция расхода ключуется ЗАДАЧЕЙ, а не сессией
(usage-attribution-is-keyed-by-task-not-session, лента Б релиза 1.9).

Держится отдельным модулем, чтобы backend_migrations.py оставался под гейтом
размера. ``MIGRATION_V48`` — маркер версии для реестра; настоящая работа делается
охраняемым пост-шагом ``maybe_rebuild_usage_events_v48`` (почему — ниже).

ЧТО БЫЛО НЕ ТАК. ``usage_events`` объявляла ``session_id INTEGER NOT NULL`` и
``task_slug TEXT`` — то есть СЕССИЮ обязательной, а ЗАДАЧУ опциональной. Это
ровно наоборот от того, что таблица существует измерять: цель атрибуции — та
самая задача, которая несёт ``cost_actual_usd``, ``tokens_actual``,
``started_model_id``. Сессия же — производный отчёт о пробеге активности, со
своей логикой разрывов (gap-based, ≥10 мин). NOT NULL здесь никто не выбирал
сознательно; он приехал из v23, где таблица задумывалась ЖУРНАЛОМ СЕССИИ, и
пережил появление per-tool атрибуции версией позже, в v24.

ЦЕНА ЭТОГО NOT NULL ИЗМЕРЕНА. Хуку ``scripts/hooks/posttool_usage.py`` некуда
было положить событие без открытой сессии, и он дропал его ЦЕЛИКОМ —
`if session_id is None: return 0` — при том, что ``task_slug`` в этот момент уже
был известен строкой выше. Работа без открытой сессии записывала НОЛЬ, а не
ошибку, и вместе с телеметрией молча отказывали ещё четыре механизма,
перечисленные в docs/ru/sessions.md: token-метрики, пиннинг модели, каденция
аудита и срез brain «за эту сессию» — последний опаснее всех, потому что он не
пуст, а НЕВЕРЕН и выдаёт себя за сессионный.

ПОЧЕМУ ПЕРЕСТРОЙКА, А НЕ ALTER. SQLite не умеет снимать NOT NULL с существующей
колонки: ALTER TABLE переименовывает, добавляет и удаляет, но не ослабляет
ограничение. Единственный путь — создать таблицу новой формы, скопировать
строки, снести старую, переименовать. Тем же путём и по той же причине шла v24
на этой же таблице (там ослабляли CHECK на ``source``).

ПОЧЕМУ ОХРАНЯЕМЫЙ ПОСТ-ШАГ, А НЕ ПРОСТОЙ СПИСОК SQL — ЗАМЕР, А НЕ ОСТОРОЖНОСТЬ.
Первая редакция была именно списком, дословно по образцу v24, и уронила два
теста: test_adapts.py::test_migration_v36_creates_tables_clean и
test_reasoning_steps.py::test_migration_v32_creates_table_triggers_clean — оба
падали на `no such table: usage_events`. Причина не в них: такой тест поднимает
МИНИМАЛЬНУЮ БД и запускает миграции с версии 32 или 36, чтобы проверить ОДНУ
конкретную миграцию. v23, создающая usage_events, при этом не выполняется
никогда, и слепой `DROP TABLE usage_events` в конце цепочки роняет весь прогон.
v24 этого не встречала лишь потому, что в 2024-м таких фикстур ещё не было.
Список утверждений не умеет пропустить сам себя; охраняемый шаг умеет — тот же
приём, что у v42_backfill и v43, и по той же причине.

УСЛОВИЕ ОХРАНЫ — ровно то состояние, которое чинится: таблица существует И её
``session_id`` до сих пор NOT NULL. Отсюда идемпотентность: после перестройки
notnull=0, и повторный вызов проваливается сквозь охрану. Свежая БД, где
SCHEMA_SQL уже даёт правильную форму, тоже проходит мимо.

ПОЧЕМУ FK СТАЛ ``ON DELETE SET NULL``, А НЕ ОСТАЛСЯ ``CASCADE``. Каскад был
согласован со старым смыслом: событие принадлежит сессии, без сессии
бессмысленно. При новом смысле это прямая потеря измерения — удаление сессии
стирало бы расход, атрибутированный ЗАДАЧЕ, которая жива и чей
``cost_actual_usd`` из этих строк и складывается. SET NULL сохраняет событие и
честно говорит, что сессионного контекста у него больше нет; это та же форма,
что у соседнего ``task_slug``, и теперь обе ссылки необязательны симметрично.

ПОЧЕМУ НЕТ ОБРАТНОЙ МИГРАЦИИ. ``run_migrations`` односторонний по своему
докстрингу, и это не оплошность конкретно здесь. Откат по данным не нужен: код
v47 всегда вставлял ``session_id`` не-NULL и ни одно его чтение не полагается на
NOT NULL, поэтому ослабленная таблица его не ломает. Откат кода — ``git revert``
плюс одна ручная строка ``UPDATE meta SET value='47' WHERE key='schema_version'``,
потому что ``backend_init`` отказывает при db_ver > SCHEMA_VERSION. Строки с NULL
``session_id`` при этом остаются и читаются штатно.

ЧТО НЕ ВХОДИТ СЮДА. Событие, у которого нет НИ задачи, НИ сессии, по-прежнему
имеет право существовать — но не имеет права исчезать молча. Видимость ему даёт
не схема, а отчёт: явная корзина «вне задачи»
(``backend_queries_usage.usage_events_unattributed_rollup`` и
``project_cli_metrics``). Схема лишь перестаёт мешать такую строку записать.
"""

from __future__ import annotations

import logging
import sqlite3

# Маркер версии: реестру нужен ключ 48 для импортного гейта паритета
# (check_schema_migration_parity), а сама перестройка не может жить в списке
# утверждений — она обязана уметь пропустить себя на частичной БД (см. докстринг).
MIGRATION_V48: list[str] = []

_log = logging.getLogger("tausik.migrations")

# Колонки usage_events в каноническом (свежесхемном) порядке. Используются для
# ОБЕИХ сторон копирующего INSERT, чтобы значения ложились по ИМЕНИ, а не по
# позиции: физический порядок у мигрированной таблицы может отличаться, и
# позиционная копия разложила бы данные не по тем колонкам.
_USAGE_COLUMNS = (
    "id, session_id, task_slug, model_id, tokens_input, tokens_output, "
    "tokens_total, cost_usd, tool_calls, source, recorded_at, tool_name"
)

# Замороженный снимок канонического DDL usage_events на момент v48 — обязан
# совпадать с блоком usage_events в backend_schema.SCHEMA_SQL. Дублирование
# ГЕЙТИРОВАНО, а не оставлено на честное слово: миграция есть ИСТОРИЧЕСКИЙ
# снимок, и читать из неё живую константу нельзя (колонка, добавленная в v49+,
# молча изменила бы то, что строит v48, и разошлась бы с её же явным INSERT).
# Расхождение красит tests/test_schema_upgrade_parity.py — и набор колонок, и
# полный нормализованный CREATE, который единственный видит CHECK и FK.
_CREATE_USAGE_EVENTS_NEW = """
CREATE TABLE usage_events_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES sessions(id) ON DELETE SET NULL,
    task_slug TEXT REFERENCES tasks(slug) ON DELETE SET NULL,
    model_id TEXT,
    tokens_input INTEGER NOT NULL CHECK(tokens_input >= 0),
    tokens_output INTEGER NOT NULL CHECK(tokens_output >= 0),
    tokens_total INTEGER NOT NULL CHECK(tokens_total >= 0),
    cost_usd REAL NOT NULL DEFAULT 0 CHECK(cost_usd >= 0),
    tool_calls INTEGER NOT NULL DEFAULT 0 CHECK(tool_calls >= 0),
    source TEXT NOT NULL CHECK(source IN ('session_record', 'manual', 'posttool')),
    recorded_at TEXT NOT NULL,
    tool_name TEXT
)
"""

# Дословно из backend_schema_indexes.INDEXES_SQL + миграции v24. DROP TABLE
# уносит индексы вместе с таблицей, поэтому все три пересоздаются здесь.
_INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_usage_events_session ON usage_events(session_id, recorded_at)",
    "CREATE INDEX IF NOT EXISTS idx_usage_events_task ON usage_events(task_slug, recorded_at)",
    "CREATE INDEX IF NOT EXISTS idx_usage_events_tool ON usage_events(tool_name, recorded_at)",
)


def _needs_rebuild(conn: sqlite3.Connection) -> bool:
    """True только когда usage_events существует и её session_id всё ещё NOT NULL.

    Пропускает (False):
      * таблицы нет вовсе — частичная фикстура, стартовавшая с версии выше 23 и
        потому никогда не выполнявшая миграцию, которая эту таблицу создаёт;
      * session_id уже nullable — свежая БД или повторный вызов (идемпотентность);
      * не хватает какой-либо канонической колонки — синтетическая фикстура,
        поднявшая минимальный usage_events ради другой проверки: копирующий
        INSERT на ней бы упал. У настоящей обновлённой БД набор полон, и это
        пиньтся test_schema_upgrade_parity.
    """
    try:
        cols = {r[1]: r for r in conn.execute("PRAGMA table_info(usage_events)")}
    except sqlite3.Error:
        return False
    if not cols:
        return False
    sid = cols.get("session_id")
    if sid is None or int(sid[3]) != 1:  # r[3] — флаг notnull; 1 == NOT NULL
        return False
    expected = {c.strip() for c in _USAGE_COLUMNS.split(",")}
    return expected.issubset(cols)


def maybe_rebuild_usage_events_v48(conn: sqlite3.Connection) -> int:
    """Перестроить usage_events, сняв NOT NULL с session_id и сменив FK на SET NULL.

    Идемпотентна и самоохраняема: no-op, пока колонка не окажется NOT NULL.
    Возвращает 1, если перестройка выполнена, 0 — если пропущена. Обращение с
    foreign_keys повторяет раннер миграций (PRAGMA off вокруг DROP/RENAME,
    foreign_key_check после): PRAGMA обязана стоять ВНЕ транзакции, поэтому
    вызывающий должен быть в autocommit — как и все вызывающие run_migrations.
    """
    if not _needs_rebuild(conn):
        return 0

    statements = [
        _CREATE_USAGE_EVENTS_NEW,
        # Копия по ЯВНЫМ именам колонок (никогда SELECT *): порядок колонок у
        # мигрированной таблицы может отличаться от канонического.
        f"INSERT INTO usage_events_new ({_USAGE_COLUMNS}) "
        f"SELECT {_USAGE_COLUMNS} FROM usage_events",
        "DROP TABLE usage_events",
        "ALTER TABLE usage_events_new RENAME TO usage_events",
        *_INDEXES,
    ]

    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute("BEGIN")
    try:
        for stmt in statements:
            conn.execute(stmt)
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        conn.execute("PRAGMA foreign_keys=ON")
        raise
    conn.execute("PRAGMA foreign_keys=ON")
    violations = conn.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise RuntimeError(f"v48 usage_events rebuild broke FK integrity: {violations}")
    _log.info("v48: rebuilt usage_events — session_id is now optional, FK is ON DELETE SET NULL")
    return 1
