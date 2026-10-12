"""Потребитель, обновляющийся с 1.8.0, прогоняет ШЕСТНАДЦАТЬ миграций разом.

Тег v1.8.0 нёс `SCHEMA_VERSION = 44`; сейчас 60. То есть чужой проект, стоящий
на прошлом релизе, при первом открытии базы применяет v45..v60 подряд, на СВОИХ
данных, за один запуск.

ЧТО ПРОВЕРЯЛОСЬ ДО ЭТОГО ФАЙЛА И ЧЕГО НЕ ХВАТАЛО:

  `test_migrations.py::test_v1_to_latest` гоняет всю цепочку — но на базе с ДВУМЯ
  задачами. Она отвечает на вопрос «выполняются ли операторы», и не отвечает на
  вопрос «что происходит с данными, когда их много».

  Смена #239 прогнала v57 -> v60 на настоящей базе 78 МБ и получила 0.5 с и ноль
  потерь. Это три миграции из шестнадцати.

  Промежуток v44 -> v57 на объёме не проверял никто.

ПОЧЕМУ ОБЪЁМ ЗДЕСЬ НЕ ПРИДИРКА. Среди шестнадцати есть ПЕРЕСТРОЙКИ ТАБЛИЦ:
SQLite не умеет ALTER для CHECK, поэтому v58 копирует `usage_events` целиком
через временную таблицу. Перестройка пустой таблицы и перестройка таблицы с
шестьюдесятью тысячами строк — разные операции и по времени, и по тому, что
может пойти не так. `usage_events` в этом репозитории насчитывает 55 602 строки;
объём ниже взят с запасом.

ЧТО ЭТОТ ФАЙЛ НЕ УТВЕРЖДАЕТ: что данные ЧУЖОГО проекта устроены так же. Форма
чужих строк отсюда непроверяема, и заявлять обратное было бы утверждением шире
сделанного.
"""

from __future__ import annotations

import sqlite3
import sys
import time
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
for _p in (str(_REPO / "scripts"), str(_REPO / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from backend_migrations import MIGRATIONS, run_migrations  # noqa: E402
from backend_schema import SCHEMA_VERSION  # noqa: E402
from test_migrations import V1_SCHEMA  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/"]

#: Версия схемы, которую нёс тег v1.8.0. Прочитано из
#: `git show v1.8.0:scripts/backend_schema.py`, а не выведено из номера релиза.
SHIPPED_AT_1_8_0 = 44

#: Строк телеметрии в сиде. Живая база этого репозитория несёт 55 602; берём с
#: запасом, потому что предмет проверки — перестройка таблицы на объёме.
USAGE_ROWS = 60_000

#: Задач и записей памяти. Живые числа — 1575 и 679.
TASK_ROWS = 2_000
MEMORY_ROWS = 3_000

#: Потолок времени. Названо числом, потому что миграция, идущая минуты, —
#: отдельный факт, который потребитель обязан знать заранее, а не обнаружить.
CEILING_SECONDS = 30.0


def _apply_through(conn: sqlite3.Connection, ceiling: int) -> None:
    """Миграции по возрастанию до `ceiling` включительно, как их применяет
    `run_migrations`, но с остановкой на нужной версии."""
    for version in sorted(MIGRATIONS):
        if version > ceiling:
            break
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("BEGIN")
        try:
            for statement in MIGRATIONS[version]:
                text = statement.strip()
                if text and not text.startswith("--"):
                    conn.execute(text)
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        conn.execute("PRAGMA foreign_keys=ON")


def _columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]


@pytest.fixture(scope="module")
def loaded_v44() -> sqlite3.Connection:
    """База на схеме v1.8.0 с реалистичным объёмом.

    Строится подъёмом с v1 до 44 теми же миграциями, которыми её подняла бы
    настоящая установка, — а не сборкой по снимку схемы: снимок разошёлся бы с
    миграциями молча, и тогда тест проверял бы собственную копию.
    """
    conn = sqlite3.connect(":memory:")
    conn.executescript(V1_SCHEMA)
    conn.execute("INSERT INTO meta(key,value) VALUES('schema_version','1')")
    conn.execute(
        "INSERT INTO epics(slug,title,status,created_at) "
        "VALUES('e1','E','active','2025-01-01T00:00:00Z')"
    )
    conn.execute(
        "INSERT INTO stories(epic_id,slug,title,status,created_at) "
        "VALUES(1,'s1','S','open','2025-01-01T00:00:00Z')"
    )
    conn.commit()

    _apply_through(conn, SHIPPED_AT_1_8_0)

    stamp = "2025-06-01T00:00:00Z"
    conn.executemany(
        "INSERT INTO tasks(story_id,slug,title,status,created_at,updated_at) "
        "VALUES(1,?,?,'done',?,?)",
        [(f"t{i}", f"Задача {i}", stamp, stamp) for i in range(TASK_ROWS)],
    )
    # Колонки взяты из ЖИВОЙ схемы v44, а не по памяти: `memory.updated_at` и
    # шесть обязательных колонок `usage_events` первая редакция пропустила, и
    # фикстура упала на NOT NULL. Схема, поднятая миграциями, — единственный
    # источник правды о том, что здесь обязательно.
    conn.executemany(
        "INSERT INTO memory(type,title,content,created_at,updated_at) "
        "VALUES('pattern',?,?,?,?)",
        [
            (f"Память {i}", "содержимое с юникодом — тире и «ёлочки»", stamp, stamp)
            for i in range(MEMORY_ROWS)
        ],
    )
    conn.execute("INSERT INTO sessions(started_at) VALUES(?)", (stamp,))
    conn.executemany(
        "INSERT INTO usage_events"
        "(session_id,tokens_input,tokens_output,tokens_total,source,recorded_at) "
        "VALUES(1,?,?,?,'posttool',?)",
        [(10, 20, 30, stamp) for _ in range(USAGE_ROWS)],
    )
    conn.commit()
    return conn


@pytest.fixture(scope="module")
def migrated(loaded_v44):
    """Один прогон цепочки, потому что миграции НЕОБРАТИМЫ.

    Модульная фикстура, а не классовая: классовую pytest требует объявлять
    методом класса, и такое объявление deprecated с PytestRemovedIn10 —
    предупреждение на прогоне, которое здесь недопустимо.
    """
    before = {
        table: loaded_v44.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in ("tasks", "memory", "usage_events", "epics", "stories")
    }
    start = time.perf_counter()
    version = run_migrations(loaded_v44, SHIPPED_AT_1_8_0)
    elapsed = time.perf_counter() - start
    after = {
        table: loaded_v44.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in before
    }
    return loaded_v44, before, after, version, elapsed


class TestЦепочкаСРелизнойВерсииНаОбъёме:
    """AC-1..AC-3."""

    def test_цепочка_доходит_до_текущей_схемы(self, migrated):
        _conn, _before, _after, version, _elapsed = migrated
        assert version == SCHEMA_VERSION

    def test_объём_действительно_реалистичен(self, migrated):
        """Предпосылка. Проверка на пустых таблицах зелена по другой причине."""
        _conn, before, _after, _v, _e = migrated
        assert before["usage_events"] >= 55_602, "телеметрии меньше, чем в живой базе"
        assert before["tasks"] >= 1_500

    def test_ни_одна_таблица_не_потеряла_строк(self, migrated):
        _conn, before, after, _v, _e = migrated
        lost = {k: (before[k], after[k]) for k in before if before[k] != after[k]}
        assert not lost, f"потери при перестройке: {lost}"

    def test_целостность_и_внешние_ключи(self, migrated):
        conn, _b, _a, _v, _e = migrated
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []

    def test_время_названо_и_ограничено(self, migrated):
        _conn, _b, _a, _v, elapsed = migrated
        assert elapsed < CEILING_SECONDS, (
            f"{elapsed:.1f} с на шестнадцать миграций при {USAGE_ROWS} строках "
            "телеметрии — потребитель обязан знать это заранее, а не обнаружить"
        )

    def test_перестроенная_таблица_несёт_новые_колонки(self, migrated):
        """v58 перестраивает `usage_events` ради колонок токенов и стоимости.
        Строки на месте (выше) — здесь проверяется, что перестройка сделала то,
        ради чего затевалась, а не просто скопировала таблицу."""
        conn, _b, _a, _v, _e = migrated
        columns = set(_columns(conn, "usage_events"))
        assert {"tokens_input", "tokens_output", "cost_usd"} <= columns


class TestПроверкаУмеетУпасть:
    """AC-4. Прогон, который не может отказать, ничего не удостоверяет."""

    def test_повреждённая_база_даёт_отказ_а_не_молчаливый_успех(self, tmp_path):
        path = tmp_path / "broken.db"
        path.write_bytes(b"this is not a database at all")
        conn = sqlite3.connect(str(path))
        with pytest.raises(sqlite3.DatabaseError):
            run_migrations(conn, SHIPPED_AT_1_8_0)
        conn.close()

    def test_версия_релиза_не_выдумана(self):
        """`SHIPPED_AT_1_8_0` прочитан из тега, а не выведен из номера релиза.
        Если тег недоступен, тест не притворяется, что проверил."""
        import subprocess

        result = subprocess.run(
            ["git", "show", "v1.8.0:scripts/backend_schema.py"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(_REPO),
        )
        if result.returncode != 0:
            pytest.skip("тег v1.8.0 недоступен в этом чекауте")
        assert f"SCHEMA_VERSION = {SHIPPED_AT_1_8_0}" in (result.stdout or "")
