"""v50 — закрытый перечень статусов ADAPT доводится до семи (§7.8.1).

Держится отдельным модулем, чтобы backend_migrations.py оставался под гейтом
размера. ``MIGRATION_V50`` — МАРКЕР ВЕРСИИ для реестра; настоящая работа идёт
охраняемым пост-шагом ``maybe_widen_adapt_statuses_v50`` (почему — ниже).

ЧТО БЫЛО НЕ ТАК, И РАСХОЖДЕНИЕ ШЛО В ОБЕ СТОРОНЫ. CHECK на ``adapts.status``
перечислял ТРИ значения — ``draft, signed, superseded`` — тогда как §7.8.1
стр.384 закрывает список на СЕМИ: ``draft | review | asked | answered |
approved | frozen | superseded``.

(1) ``signed`` — наше собственное значение, которого в закрытом перечне
стандарта нет. Мы завели свой статус в списке, объявленном закрытым.

(2) ``approved`` — значение, которого §13.3.3 стр.77 ТРЕБУЕТ для ветви
findings-present («ADAPT обязателен в статусе approved с подписью Архитектора»),
у нас ОТСУТСТВОВАЛО. Второе следствие тяжелее первого, и разница не
стилистическая: соответствие было недостижимо не по лени, а потому что
CHECK-ограничение БД ОТКЛОНИЛО БЫ запись. Требуемое состояние было
НЕДОСТИЖИМО, а не просто не достигнуто.

ПОЧЕМУ signed ОТОБРАЖАЕТСЯ В approved, А НЕ УДАЛЯЕТСЯ. Наш ``signed`` означал
«обе подписи собраны». Стандарт разводит два РАЗНЫХ факта: ``approved`` есть
СТАТУС, а подпись Архитектора — отдельное требование той же ветви, и живёт она
в ``adapt_signatures``. Наш ``signed`` их схлопывал. Перенос сохраняет смысл
записи («работа принята») и возвращает подпись на её собственное место;
удаление статуса потеряло бы факт приёмки.

ДВЕ КОЛОНКИ ADR-007, ДОБАВЛЯЕМЫЕ ТЕМ ЖЕ ШАГОМ. ``trigger_stage`` — поле,
которым ADR-007 различает несколько ADAPT одного ТЗ; без него кардинальность
0..N невыразима. ``supersession_rationale`` (ADR-007 стр.108) — обязательное
основание дезавуирования. Дезавуирование у нас было наполовину и потому опаснее
пустого места: статус ``superseded`` в перечне БЫЛ, ребро ``supersedes`` в
backend_schema.py БЫЛО, а сослаться на противоречащее требование было НЕГДЕ —
запись выходила синтаксически валидной и содержательно пустой, вырожденный
контроль по ADR-021 прямо в схеме данных. Правило «нет основания — нет
дезавуирования» живёт в ``backend_crud_adapts.adapt_set_status``, низшем
примитиве, который эту колонку пишет.

Обе колонки добавляются ЗДЕСЬ, а не отдельной миграцией, потому что перестройка
таблицы всё равно происходит: сделать её дважды было бы строго хуже — каждая
перестройка ``adapts`` есть операция с выключенными внешними ключами.

ПОЧЕМУ ПЕРЕСТРОЙКА, А НЕ ALTER. SQLite не умеет менять CHECK у существующей
колонки: ALTER TABLE переименовывает, добавляет и удаляет, но ограничение не
трогает. Единственный путь — создать таблицу новой формы, скопировать строки,
снести старую, переименовать. Тем же путём и по той же причине шли v24, v48
и v49.

ПОЧЕМУ ОХРАНЯЕМЫЙ ШАГ, А НЕ СПИСОК УТВЕРЖДЕНИЙ. Ровно та же причина, что у
v48/v49: tests/test_adapts.py::test_migration_v36_creates_tables_clean поднимает
МИНИМАЛЬНУЮ БД, объявляет её версией 35 и прогоняет миграции. Список утверждений
не умеет пропустить сам себя на частичной фикстуре; охраняемый шаг умеет.

УСЛОВИЕ ОХРАНЫ — ровно то состояние, которое чинится: таблица ``adapts``
существует И её CHECK ещё НЕ допускает ``approved``. Отсюда идемпотентность:
после перестройки допускает, и повторный вызов проваливается сквозь охрану.
Свежая БД, где ADAPTS_SQL сразу даёт семь, тоже проходит мимо.

ТРИГГЕРЫ. adapts_ai/ad/au висят на таблице и умирают вместе с ней при DROP,
поэтому снимаются ЯВНО до копирования и пересоздаются после переименования.

ЗДЕСЬ ИСПРАВЛЕНО УНАСЛЕДОВАННОЕ УТВЕРЖДЕНИЕ. Формулировка v49, перенесённая
сюда дословно, гласила: «без снятия копирующий INSERT породил бы второй
комплект записей в FTS». ЭТО НЕВЕРНО, и показала это мутация: копирующий
INSERT адресован НОВОЙ таблице ``adapts_v50``, а триггеры висят на ``adapts``
— на такой вставке они не срабатывают. Мутант, удаляющий три DROP TRIGGER,
ВЫЖИЛ при зелёном тесте на отсутствие дублей, и это правильный результат:
мутант эквивалентен. Снятие остаётся как явное объявление порядка, но своей
заявленной цены оно не имеет, и притворяться иначе — то же завышение, что
и завышенный докстринг файла тестов.

``fts_adapts`` — внешняя contentless-таблица, она переживает перестройку и НЕ
трогается: копия сохраняет ``id``, то есть rowid индекса остаются валидны.

ЧЕТЫРЕ ДОЧЕРНИЕ ТАБЛИЦЫ ссылаются на ``adapts(slug)``: adapt_interpretations,
adapt_findings, adapt_signatures, adapt_links. Они переживают DROP/RENAME при
выключенных внешних ключах, а целостность проверяется ``PRAGMA
foreign_key_check`` сразу после включения — как в v49.

РАСШИРЕНИЕ, А НЕ ОТКРЫТИЕ. Список остаётся ЗАКРЫТЫМ: CHECK на месте, и статус
вне перечня по-прежнему отклоняется базой — включая сам ``signed`` ПОСЛЕ
миграции. Обе стороны проверяются в tests/test_migrations_v50_adapt_statuses.py,
причём на МИГРИРОВАННОЙ схеме, а не только на свежей: по опыту v49 мутация,
заменившая CHECK на голое ``status TEXT NOT NULL``, пережила бы набор тестов,
идущий только по свежему пути.

ПОЧЕМУ НЕТ ОБРАТНОЙ МИГРАЦИИ. ``run_migrations`` односторонний по докстрингу.
Откат по данным безопасен ТОЛЬКО при отсутствии строк в статусах review, asked,
answered, frozen и approved; при их наличии обратная миграция обязана быть
решением о переносе, а не молчаливым сужением CHECK, который эти строки
отвергнет.
"""

from __future__ import annotations

import logging
import sqlite3

# Маркер версии: реестру нужен ключ 50 для импортного гейта паритета
# (check_schema_migration_parity), а сама перестройка не может жить в списке
# утверждений — она обязана уметь пропустить себя на частичной БД.
MIGRATION_V50: list[str] = []

_log = logging.getLogger("tausik.migrations")

# Колонки adapts В СТАРОЙ (до-v50) форме. Используются для ОБЕИХ сторон
# копирующего INSERT, чтобы значения ложились по ИМЕНИ, а не по позиции. Две
# новые колонки в списке отсутствуют намеренно: у источника их нет, и в приёмнике
# они останутся NULL.
_OLD_ADAPT_COLUMNS = (
    "id, slug, title, tz_ref, status, parent_adapt, delta_n, created_at, updated_at"
)

# Замороженный снимок канонического DDL adapts на момент v50 — обязан совпадать
# с блоком adapts в backend_schema_adapts.ADAPTS_SQL. Дублирование намеренно:
# миграция есть ИСТОРИЧЕСКИЙ снимок, и читать из неё живую константу нельзя —
# колонка, добавленная в v51+, молча изменила бы то, что строит v50.
_CREATE_ADAPTS_NEW = """
CREATE TABLE adapts_v50 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    tz_ref TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN
        ('draft', 'review', 'asked', 'answered', 'approved', 'frozen',
         'superseded')),
    parent_adapt TEXT REFERENCES adapts(slug) ON DELETE SET NULL,
    delta_n INTEGER NOT NULL DEFAULT 0,
    trigger_stage TEXT,
    supersession_rationale TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

# Дословно из backend_schema_adapts: DROP TABLE уносит их вместе с таблицей.
_TRIGGERS = (
    """CREATE TRIGGER IF NOT EXISTS adapts_ai AFTER INSERT ON adapts BEGIN
        INSERT INTO fts_adapts(rowid, slug, title, tz_ref)
        VALUES (new.id, new.slug, new.title, new.tz_ref);
    END""",
    """CREATE TRIGGER IF NOT EXISTS adapts_ad AFTER DELETE ON adapts BEGIN
        INSERT INTO fts_adapts(fts_adapts, rowid, slug, title, tz_ref)
        VALUES ('delete', old.id, old.slug, old.title, old.tz_ref);
    END""",
    """CREATE TRIGGER IF NOT EXISTS adapts_au AFTER UPDATE ON adapts BEGIN
        INSERT INTO fts_adapts(fts_adapts, rowid, slug, title, tz_ref)
        VALUES ('delete', old.id, old.slug, old.title, old.tz_ref);
        INSERT INTO fts_adapts(rowid, slug, title, tz_ref)
        VALUES (new.id, new.slug, new.title, new.tz_ref);
    END""",
)

_INDEXES = ("CREATE INDEX IF NOT EXISTS idx_adapts_parent ON adapts(parent_adapt)",)


def _needs_rebuild(conn: sqlite3.Connection) -> bool:
    """True только когда adapts существует и её CHECK ещё не допускает 'approved'.

    Пропускает (False):
      * таблицы нет вовсе — частичная фикстура, стартовавшая с версии выше 36 и
        потому никогда не выполнявшая миграцию, которая эту таблицу создаёт;
      * CHECK уже содержит approved — свежая БД или повторный вызов
        (идемпотентность);
      * не хватает какой-либо старой канонической колонки — синтетическая
        фикстура, поднявшая минимальный adapts ради другой проверки: копирующий
        INSERT на ней бы упал.
    """
    try:
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='adapts'"
        ).fetchone()
    except sqlite3.Error:
        return False
    if not row or not row[0]:
        return False
    ddl = str(row[0])
    if "CHECK(status IN" not in ddl:
        # Схема без CHECK на статусе — не та форма, которую этот шаг чинит.
        return False
    if "'approved'" in ddl:
        return False
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(adapts)")}
    except sqlite3.Error:
        return False
    expected = {c.strip() for c in _OLD_ADAPT_COLUMNS.split(",")}
    return expected.issubset(cols)


def maybe_widen_adapt_statuses_v50(conn: sqlite3.Connection) -> int:
    """Перестроить adapts, доведя закрытый CHECK на status до семи значений §7.8.1.

    Переносит строки ``signed`` в ``approved`` тем же копирующим INSERT: новый
    CHECK отверг бы ``signed``, поэтому отображение обязано произойти ВНУТРИ
    копии, а не отдельным UPDATE после неё.

    Идемпотентна и самоохраняема: no-op, пока CHECK уже содержит approved.
    Возвращает 1, если перестройка выполнена, 0 — если пропущена. Обращение с
    foreign_keys повторяет раннер миграций (PRAGMA off вокруг DROP/RENAME,
    foreign_key_check после): PRAGMA обязана стоять ВНЕ транзакции, поэтому
    вызывающий должен быть в autocommit — как и все вызывающие run_migrations.
    """
    if not _needs_rebuild(conn):
        return 0

    # Отображение статуса живёт ВНУТРИ копирующего SELECT: новый CHECK отвергает
    # 'signed', поэтому вставить как есть и поправить потом невозможно.
    copy_columns = (
        "id, slug, title, tz_ref, "
        "CASE WHEN status='signed' THEN 'approved' ELSE status END, "
        "parent_adapt, delta_n, created_at, updated_at"
    )

    statements = [
        # Снимаются ДО копии ради явного порядка. Дублирования в fts_adapts они
        # бы НЕ вызвали — копия идёт в adapts_v50, а висят они на adapts;
        # проверено мутацией (см. докстринг модуля).
        "DROP TRIGGER IF EXISTS adapts_ai",
        "DROP TRIGGER IF EXISTS adapts_ad",
        "DROP TRIGGER IF EXISTS adapts_au",
        _CREATE_ADAPTS_NEW,
        # Копия по ЯВНЫМ именам колонок (никогда SELECT *): порядок колонок у
        # мигрированной таблицы может отличаться от канонического.
        f"INSERT INTO adapts_v50 ({_OLD_ADAPT_COLUMNS}) SELECT {copy_columns} FROM adapts",
        "DROP TABLE adapts",
        "ALTER TABLE adapts_v50 RENAME TO adapts",
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
        raise RuntimeError(f"v50 adapts rebuild broke FK integrity: {violations}")
    _log.info("v50: rebuilt adapts — the closed status list now carries the standard's seven")
    return 1
