"""v49 — закрытый перечень типов SPEC доводится до одиннадцати (ADR-013).

Держится отдельным модулем, чтобы backend_migrations.py оставался под гейтом
размера. ``MIGRATION_V49`` — МАРКЕР ВЕРСИИ для реестра; настоящая работа идёт
охраняемым пост-шагом ``maybe_widen_spec_types_v49`` (почему — ниже).

ЧТО БЫЛО НЕ ТАК. CHECK на ``specs.type`` перечислял ДЕВЯТЬ значений, тогда как
§8.3 стандарта закрывает список на ОДИННАДЦАТИ: ADR-013 добавил ``SPEC-TEST``
(тестовые стенды и данные) и ``SPEC-DOC`` (поставляемая документация). Довод
стандарта механический: §10.5.4 инвалидирует ``verified`` при ЛЮБОМ инкременте
версии артефакта, поэтому привязка TC к стенду через SPEC-OPS обрушивала бы в
``approved`` ВСЕ TC на этом SPEC-OPS при правке процедуры деплоя, к стенду
отношения не имеющей. Отдельный тип делает инвалидацию точной.

ЦЕНА НЕДОСТАЧИ БЫЛА НЕ КОСМЕТИЧЕСКОЙ. ADR-023 дополнил §8.4.1 положением
«Полнота охвата» со словами «во всех ОДИННАДЦАТИ типах». Норму про одиннадцать
невозможно исполнить в системе, знающей девять: для двух типов у нас не было и
предмета исполнения.

ПОЧЕМУ ПЕРЕСТРОЙКА, А НЕ ALTER. SQLite не умеет менять CHECK у существующей
колонки: ALTER TABLE переименовывает, добавляет и удаляет, но ограничение не
трогает. Единственный путь — создать таблицу новой формы, скопировать строки,
снести старую, переименовать. Тем же путём и по той же причине шли v24 и v48.

ПОЧЕМУ ОХРАНЯЕМЫЙ ШАГ, А НЕ СПИСОК УТВЕРЖДЕНИЙ. Ровно та же причина, что у v48,
и найдена она тем же способом — полной лентой, а не рассуждением.
tests/test_adapts.py::test_migration_v36_creates_tables_clean поднимает
МИНИМАЛЬНУЮ БД, объявляет её версией 35 и прогоняет миграции, чтобы проверить
ОДНУ конкретную. v35, создающая ``specs``, при этом не выполняется никогда, и
слепой ``DROP TABLE specs`` в конце цепочки роняет весь прогон на
``no such table: specs``. Список утверждений не умеет пропустить сам себя;
охраняемый шаг умеет — тот же приём, что у v42_backfill, v43 и v48.

УСЛОВИЕ ОХРАНЫ — ровно то состояние, которое чинится: таблица ``specs``
существует И её CHECK ещё НЕ допускает ``TEST``. Отсюда идемпотентность: после
перестройки допускает, и повторный вызов проваливается сквозь охрану. Свежая
БД, где SCHEMA_SQL сразу даёт одиннадцать, тоже проходит мимо.

ПОРЯДОК ВАЖЕН. Триггеры specs_ai/specs_ad/specs_au висят на таблице и умирают
вместе с ней при DROP TABLE specs, поэтому пересоздаются ПОСЛЕ переименования.
Снятие ДО копии оставлено ради ЯВНОГО ПОРЯДКА и корректности НЕ покупает:
копирующий INSERT адресован ``specs_v49``, а триггеры висят на ``specs``, и на
такой вставке они не срабатывают. Прежняя редакция утверждала здесь обратное —
что без снятия появился бы второй комплект записей в FTS. Утверждение НЕВЕРНО и
опровергнуто МУТАЦИЕЙ: удаление всех трёх ``DROP TRIGGER`` оставляет
tests/test_migrations_v49_spec_types.py зелёным. Оно же было скопировано в v50
дословно и там исправлено — неверное объяснение переживает верный код и
тиражируется копированием. ``fts_specs`` — внешняя contentless-таблица, она
переживает перестройку и НЕ трогается: копия сохраняет ``id``, то есть rowid
индекса остаются валидны.

РАСШИРЕНИЕ, А НЕ ОТКРЫТИЕ. Список остаётся ЗАКРЫТЫМ: CHECK на месте, и тип вне
перечня по-прежнему отклоняется базой. Обе стороны проверяются в
tests/test_migrations_v49_spec_types.py, причём на МИГРИРОВАННОЙ схеме, а не
только на свежей — мутация, заменившая CHECK на голое ``type TEXT NOT NULL``,
пережила первый набор тестов именно потому, что они шли по свежему пути.

ПОЧЕМУ НЕТ ОБРАТНОЙ МИГРАЦИИ. ``run_migrations`` односторонний по докстрингу.
Откат по данным безопасен ТОЛЬКО при отсутствии строк типов TEST и DOC — при их
наличии обратная миграция обязана быть решением о переносе, а не молчаливым
сужением CHECK, который эти строки отвергнет.
"""

from __future__ import annotations

import logging
import sqlite3

# Маркер версии: реестру нужен ключ 49 для импортного гейта паритета
# (check_schema_migration_parity), а сама перестройка не может жить в списке
# утверждений — она обязана уметь пропустить себя на частичной БД.
MIGRATION_V49: list[str] = []

_log = logging.getLogger("tausik.migrations")

# Колонки specs в каноническом (свежесхемном) порядке. Используются для ОБЕИХ
# сторон копирующего INSERT, чтобы значения ложились по ИМЕНИ, а не по позиции.
_SPEC_COLUMNS = "id, slug, type, title, content_ref, version, status, created_at, updated_at"

# Замороженный снимок канонического DDL specs на момент v49 — обязан совпадать
# с блоком specs в backend_schema_specs.SPECS_SQL. Дублирование намеренно:
# миграция есть ИСТОРИЧЕСКИЙ снимок, и читать из неё живую константу нельзя —
# колонка, добавленная в v50+, молча изменила бы то, что строит v49.
_CREATE_SPECS_NEW = """
CREATE TABLE specs_v49 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL CHECK(type IN
        ('ARCH', 'API', 'DATA', 'INT', 'PROC', 'UI', 'AI', 'SEC', 'OPS',
         'TEST', 'DOC')),
    title TEXT NOT NULL,
    content_ref TEXT,
    version TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN
        ('draft', 'active', 'deprecated')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

# Дословно из backend_migrations_v35: DROP TABLE уносит их вместе с таблицей.
_TRIGGERS = (
    """CREATE TRIGGER IF NOT EXISTS specs_ai AFTER INSERT ON specs BEGIN
        INSERT INTO fts_specs(rowid, slug, title, content_ref)
        VALUES (new.id, new.slug, new.title, new.content_ref);
    END""",
    """CREATE TRIGGER IF NOT EXISTS specs_ad AFTER DELETE ON specs BEGIN
        INSERT INTO fts_specs(fts_specs, rowid, slug, title, content_ref)
        VALUES ('delete', old.id, old.slug, old.title, old.content_ref);
    END""",
    """CREATE TRIGGER IF NOT EXISTS specs_au AFTER UPDATE ON specs BEGIN
        INSERT INTO fts_specs(fts_specs, rowid, slug, title, content_ref)
        VALUES ('delete', old.id, old.slug, old.title, old.content_ref);
        INSERT INTO fts_specs(rowid, slug, title, content_ref)
        VALUES (new.id, new.slug, new.title, new.content_ref);
    END""",
)

_INDEXES = ("CREATE INDEX IF NOT EXISTS idx_specs_type ON specs(type)",)


def _needs_rebuild(conn: sqlite3.Connection) -> bool:
    """True только когда specs существует и её CHECK ещё не допускает 'TEST'.

    Пропускает (False):
      * таблицы нет вовсе — частичная фикстура, стартовавшая с версии выше 35 и
        потому никогда не выполнявшая миграцию, которая эту таблицу создаёт;
      * CHECK уже содержит TEST — свежая БД или повторный вызов
        (идемпотентность);
      * не хватает какой-либо канонической колонки — синтетическая фикстура,
        поднявшая минимальный specs ради другой проверки: копирующий INSERT на
        ней бы упал.
    """
    try:
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='specs'"
        ).fetchone()
    except sqlite3.Error:
        return False
    if not row or not row[0]:
        return False
    ddl = str(row[0])
    if "CHECK(type IN" not in ddl:
        # Схема без CHECK на типе — не та форма, которую этот шаг чинит.
        return False
    if "'TEST'" in ddl:
        return False
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(specs)")}
    except sqlite3.Error:
        return False
    expected = {c.strip() for c in _SPEC_COLUMNS.split(",")}
    return expected.issubset(cols)


def maybe_widen_spec_types_v49(conn: sqlite3.Connection) -> int:
    """Перестроить specs, доведя закрытый CHECK на type до одиннадцати типов.

    Идемпотентна и самоохраняема: no-op, пока CHECK уже не содержит TEST.
    Возвращает 1, если перестройка выполнена, 0 — если пропущена. Обращение с
    foreign_keys повторяет раннер миграций (PRAGMA off вокруг DROP/RENAME,
    foreign_key_check после): PRAGMA обязана стоять ВНЕ транзакции, поэтому
    вызывающий должен быть в autocommit — как и все вызывающие run_migrations.
    """
    if not _needs_rebuild(conn):
        return 0

    statements = [
        # Снятие ради ЯВНОГО ПОРЯДКА, а не ради корректности: копия адресована
        # specs_v49, триггеры висят на specs и на такой вставке НЕ срабатывают.
        # Умирают они всё равно — вместе с таблицей, удаляемой ниже.
        "DROP TRIGGER IF EXISTS specs_ai",
        "DROP TRIGGER IF EXISTS specs_ad",
        "DROP TRIGGER IF EXISTS specs_au",
        _CREATE_SPECS_NEW,
        # Копия по ЯВНЫМ именам колонок (никогда SELECT *): порядок колонок у
        # мигрированной таблицы может отличаться от канонического.
        f"INSERT INTO specs_v49 ({_SPEC_COLUMNS}) SELECT {_SPEC_COLUMNS} FROM specs",
        "DROP TABLE specs",
        "ALTER TABLE specs_v49 RENAME TO specs",
        *_INDEXES,
        *_TRIGGERS,
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
        raise RuntimeError(f"v49 specs rebuild broke FK integrity: {violations}")
    _log.info("v49: rebuilt specs — the closed type list now carries the standard's eleven")
    return 1
