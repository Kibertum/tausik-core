"""Таблица, добавленная только миграцией, отсутствует у КАЖДОЙ новой установки.

НАЙДЕНО ПРОВЕРКОЙ ГОТОВНОСТИ К ВЫПУСКУ 1.9 (смена #239), на настоящей свежей
установке в пустой проект. `meta.schema_version` говорил 60, таблиц было 91, и
`test_red_history` среди них НЕ БЫЛО.

ПОЧЕМУ ТАК ВЫХОДИТ. `backend_init` на новой базе сначала штампует
`meta.schema_version = SCHEMA_VERSION`, а потом зовёт `run_migrations(conn,
SCHEMA_VERSION)` — то есть применяет только миграции ВЫШЕ текущей версии, а таких
нет ни одной. Значит все таблицы новой базы берутся из `CREATE TABLE` на свежем
пути, и миграция про них не знает.

ПОЧЕМУ ЭТО ХУЖЕ ОБЫЧНОГО ДЕФЕКТА: отказ ТИХИЙ по построению. `record_reds`
ловит `sqlite3.Error` и возвращает 0, потому что наблюдение не смеет ронять
прогон. У нового проекта красная история пишет в никуда, база честно говорит
«схема 60», и ни один гейт не возражает.

ЭТОТ ФАЙЛ ПРОВЕРЯЕТ СВОЙСТВО, А НЕ СЛУЧАЙ. Чинить одну таблицу значило бы ждать
следующую. Существующий `check_schema_migration_parity` сверяет НУМЕРАЦИЮ и
такого не видит.
"""

from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

from backend_migrations import MIGRATIONS  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/"]

#: `CREATE TABLE [IF NOT EXISTS] name` — в любом регистре и с любым отступом.
_CREATE_TABLE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[\"'`\[]?([A-Za-z_][A-Za-z0-9_]*)",
    re.IGNORECASE,
)

#: Таблицы, которые миграция создаёт ВРЕМЕННО ради перестройки и тут же
#: переименовывает. Их отсутствие в готовой базе — норма, а не пропажа: SQLite не
#: умеет ALTER для CHECK, поэтому таблицу пересобирают через копию.
#:
#: Суффикс версии (`usage_events_v58`, `artifact_edges_v59`) — здешний способ
#: называть такую копию, и он найден прогоном: без него охрана краснела на двух
#: законных перестройках и была бы выключена первой же.
_SCAFFOLDING = re.compile(r"(_new$|_old$|_tmp$|_v\d+$|^new_|^old_|^tmp_)")


#: `ALTER TABLE <таблица> ADD COLUMN <столбец>` — второй способ, которым миграция
#: меняет форму базы, и до v61 его никто не сверял со свежим путём. Проверка
#: таблиц его не видит по построению: таблица-то на месте, а столбца в ней нет.
_ADD_COLUMN = re.compile(
    r"ALTER\s+TABLE\s+[\"'`\[]?([A-Za-z_][A-Za-z0-9_]*)[\"'`\]]?\s+"
    r"ADD\s+(?:COLUMN\s+)?[\"'`\[]?([A-Za-z_][A-Za-z0-9_]*)",
    re.IGNORECASE,
)


def _columns_added_by_migrations() -> set[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    for statements in MIGRATIONS.values():
        for statement in statements:
            for table, column in _ADD_COLUMN.findall(statement or ""):
                if not _SCAFFOLDING.search(table):
                    found.add((table, column))
    return found


def _fresh_columns(tmp_path: Path) -> dict[str, set[str]]:
    """Столбцы НАСТОЯЩЕЙ новой базы, поднятой обычным путём."""
    path = tmp_path / "fresh_cols.db"
    backend = SQLiteBackend(str(path))
    backend.close()
    conn = sqlite3.connect(str(path))
    try:
        out: dict[str, set[str]] = {}
        for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'"):
            out[str(name)] = {
                str(row[1]) for row in conn.execute(f"PRAGMA table_info('{name}')")
            }
        return out
    finally:
        conn.close()


def _tables_created_by_migrations() -> set[str]:
    found: set[str] = set()
    for statements in MIGRATIONS.values():
        for statement in statements:
            for name in _CREATE_TABLE.findall(statement or ""):
                if not _SCAFFOLDING.search(name):
                    found.add(name)
    return found


def _fresh_tables(tmp_path: Path) -> set[str]:
    """Таблицы НАСТОЯЩЕЙ новой базы, поднятой обычным путём."""
    path = tmp_path / "fresh.db"
    backend = SQLiteBackend(str(path))
    backend.close()
    conn = sqlite3.connect(str(path))
    try:
        return {
            str(row[0]) for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    finally:
        conn.close()


class TestСвежаяУстановкаИмеетВсёТоЖе:
    def test_каждая_таблица_миграций_есть_на_свежей_базе(self, tmp_path):
        migrated = _tables_created_by_migrations()
        fresh = _fresh_tables(tmp_path)
        missing = sorted(migrated - fresh)
        assert not missing, (
            "эти таблицы создаются миграцией и отсутствуют у новой установки, "
            "то есть работают только там, где база обновлялась: "
            f"{missing}. Новая база НЕ прогоняет миграций — добавь CREATE TABLE "
            "на свежий путь (образец: backend_schema_gate_runs.GATE_RUNS_SQL)"
        )

    def test_разбор_миграций_действительно_что_то_находит(self):
        """Предпосылка. Пустое множество прошло бы проверку выше молча, и это
        был бы самый тихий способ её отключить."""
        found = _tables_created_by_migrations()
        assert len(found) > 10, f"разбор миграций нашёл только {len(found)} таблиц"
        assert "test_red_history" in found, "таблица v60 перестала находиться разбором"

    def test_свежий_путь_и_миграция_дают_одинаковую_ФОРМУ(self, tmp_path):
        """Совпадения ИМЕНИ мало: два определения могут разойтись столбцами.

        Миграция заморожена навсегда (конвенция #646), а определение на свежем
        пути живёт. База, обновлённая год назад, и база, поднятая сегодня,
        обязаны нести одну и ту же таблицу — иначе код, работающий на одной,
        падает на другой, и виновата будет не он.
        """
        fresh_db = tmp_path / "fresh.db"
        backend = SQLiteBackend(str(fresh_db))
        backend.close()

        migrated_db = tmp_path / "migrated.db"
        conn = sqlite3.connect(str(migrated_db))
        for statement in MIGRATIONS[60]:
            conn.execute(statement)
        conn.commit()

        def columns(connection):
            return [
                (row[1], row[2], row[3], row[5])
                for row in connection.execute("PRAGMA table_info(test_red_history)")
            ]

        fresh_conn = sqlite3.connect(str(fresh_db))
        try:
            assert columns(fresh_conn) == columns(conn) != [], (
                "свежий путь и миграция создают РАЗНУЮ таблицу под одним именем"
            )
        finally:
            fresh_conn.close()
            conn.close()



class TestСтолбецИзМиграцииЕстьИНаСвежемПути:
    """Вторая половина той же дыры, и она была открыта.

    Проверка выше сверяет ТАБЛИЦЫ. Столбец, добавленный `ALTER TABLE ... ADD
    COLUMN`, она пропускает по построению: таблица на месте, а поля в ней нет.
    Найдено при добавлении v61 (`tasks.tracker_refs`) — то есть охрана,
    написанная в смене #240 против ровно этого класса, свою же следующую
    миграцию бы не поймала.
    """

    def test_каждый_столбец_миграций_есть_на_свежей_базе(self, tmp_path):
        fresh = _fresh_columns(tmp_path)
        missing = sorted(
            f"{table}.{column}"
            for table, column in _columns_added_by_migrations()
            # Таблицы, которой на свежей базе нет вовсе, касается проверка выше;
            # спрашивать с неё ещё и столбцы значило бы сообщить одну пропажу
            # дважды и разными словами.
            if table in fresh and column not in fresh[table]
        )
        assert not missing, (
            "эти столбцы добавляет миграция, и на новой установке их НЕТ — код, "
            "работающий на обновлённой базе, падает на свежей: "
            f"{missing}. Новая база НЕ прогоняет миграций — добавь столбец в "
            "определение таблицы в backend_schema.py"
        )

    def test_разбор_действительно_находит_столбцы(self):
        """Предпосылка. Пустое множество прошло бы молча."""
        found = _columns_added_by_migrations()
        assert len(found) > 5, f"разбор нашёл только {len(found)} столбцов"
        assert ("tasks", "tracker_refs") in found, "столбец v61 не находится разбором"
        assert ("tasks", "scope") in found, "столбец v12 не находится разбором"

    def test_выдуманный_столбец_ловится(self, tmp_path, monkeypatch):
        """Отрицательная половина: миграция объявляет столбец, которого на
        свежем пути нет, и охрана обязана его назвать.

        Подмена — той же формы, что у соседнего теста про выдуманную таблицу:
        MIGRATIONS правится в модуле И в глобальном имени этого файла, потому
        что разбор читает второе.
        """
        import backend_migrations
        from backend_schema import SCHEMA_VERSION

        patched = dict(backend_migrations.MIGRATIONS)
        patched[SCHEMA_VERSION - 1] = [
            *patched.get(SCHEMA_VERSION - 1, []),
            "ALTER TABLE tasks ADD COLUMN nobody_added_me TEXT",
        ]
        monkeypatch.setattr(backend_migrations, "MIGRATIONS", patched)
        monkeypatch.setitem(globals(), "MIGRATIONS", patched)

        assert ("tasks", "nobody_added_me") in _columns_added_by_migrations()
        fresh = _fresh_columns(tmp_path)
        assert "nobody_added_me" not in fresh["tasks"], (
            "свежая база всё же завела столбец — тогда дефекта, ради которого "
            "написан этот класс, не существует"
        )
        with pytest.raises(AssertionError, match="nobody_added_me"):
            self.test_каждый_столбец_миграций_есть_на_свежей_базе(tmp_path)


class TestОхранаУмеетКраснеть:
    """Проверка, которая не может отказать, не охраняет ничего."""

    def test_выдуманная_таблица_миграции_ловится(self, tmp_path, monkeypatch):
        """Подмешивается миграция, создающая таблицу, которой на свежем пути нет.

        НОМЕР ВЗЯТ НЕ ВЫШЕ ТЕКУЩЕЙ ВЕРСИИ, и это существо дефекта. Первая
        редакция взяла 9999 и провалилась: `run_migrations` применяет всё СТРОГО
        ВЫШЕ штампа, поэтому такая миграция на свежей базе исполняется и таблица
        появляется. Тихо отсутствуют ровно те таблицы, чья миграция НЕ ВЫШЕ
        `SCHEMA_VERSION`, — то есть каждая уже выпущенная.
        """
        import backend_migrations
        from backend_schema import SCHEMA_VERSION

        patched = dict(backend_migrations.MIGRATIONS)
        patched[SCHEMA_VERSION - 1] = [
            *patched.get(SCHEMA_VERSION - 1, []),
            "CREATE TABLE IF NOT EXISTS nobody_created_me (x TEXT)",
        ]
        monkeypatch.setattr(backend_migrations, "MIGRATIONS", patched)
        monkeypatch.setitem(globals(), "MIGRATIONS", patched)

        assert "nobody_created_me" in _tables_created_by_migrations()
        assert "nobody_created_me" not in _fresh_tables(tmp_path), (
            "свежая база всё же создала таблицу — тогда дефекта, ради которого "
            "написан этот файл, не существует"
        )

    @pytest.mark.parametrize(
        "name",
        [
            pytest.param("artifacts_new", id="suffix_new"),
            pytest.param("old_tasks", id="prefix_old"),
            pytest.param("tmp_edges", id="prefix_tmp"),
        ],
    )
    def test_строительные_леса_перестройки_не_считаются_пропажей(self, name):
        """SQLite не умеет ALTER для CHECK, поэтому таблицу пересобирают через
        копию с временным именем. Считать её пропажей значило бы краснеть на
        каждой такой миграции — и охрану выключили бы первой же."""
        assert _SCAFFOLDING.search(name)
