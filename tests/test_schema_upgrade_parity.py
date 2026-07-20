"""Апгрейд-путь: сходится ли МИГРИРОВАННАЯ схема со СВЕЖЕЙ.

AC7 задачи test-ddl-drift-verification-runs. Гейт паритета фикстур
(test_ddl_fixture_parity.py) сверяет фикстуры с backend_schema.SCHEMA_SQL,
то есть со СВЕЖЕЙ схемой. У живого проекта БД свежая ровно один раз — при
инициализации; дальше это БД, доведённая миграциями с v1. Если два пути
расходятся, фикстура доказывает соответствие тому, чего в поле почти нет.

Поэтому вопрос AC7 («фикстура проверяет свежую схему или применённые
миграции?») отвечается не прозой, а этим файлом: свежая, И расхождение между
путями теперь измеряется механически.

Разведка сессии #121 нашла ДВА расхождения, оба реальные:

  1. ПОРЯДОК КОЛОНОК. ALTER TABLE ADD COLUMN дописывает в конец, поэтому в
     мигрированной БД tasks и memory имеют иной порядок, чем в свежей.
     Множество колонок совпадает, порядок — нет, и починить это можно только
     перестройкой таблиц, что дороже вреда. Практическое следствие названо
     ниже отдельным гейтом: позиционный `INSERT INTO t VALUES (...)`
     привязывается к порядку и потому означает РАЗНОЕ на свежей и на
     обновлённой БД.

  2. tasks.model_mismatch: в свежей схеме NOT NULL DEFAULT 0, на пути миграции
     — nullable. То есть в обновлённой БД колонка может быть NULL, и любой
     `WHERE model_mismatch = 0` такие строки пропустит. Это НЕ порядок, это
     разная строгость, и она чинится. Вынесено в задачу-преемника.

Список известных расхождений — храповик: новое расхождение красит гейт.
"""

from __future__ import annotations

import os
import re
import sqlite3
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPTS = os.path.join(_ROOT, "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from backend_migrations import run_migrations  # noqa: E402
from backend_schema import SCHEMA_SQL, SCHEMA_VERSION  # noqa: E402

# Известные и объяснённые расхождения (таблица, колонка). Каждая запись обязана
# иметь причину в докстринге модуля. Список может только сокращаться.
_KNOWN_CONSTRAINT_DRIFT = {
    ("tasks", "model_mismatch"),  # NOT NULL в свежей, nullable на пути миграции
}

# Таблицы, чей ПОРЯДОК колонок расходится из-за ALTER TABLE ADD COLUMN. Это
# неизбежно и не чинится; фиксируется, чтобы список не рос молча.
_KNOWN_ORDER_DRIFT = {"tasks", "memory"}


def _schema_tables() -> list[str]:
    return sorted(set(re.findall(r"CREATE TABLE(?:\s+IF NOT EXISTS)?\s+([a-z_]+)", SCHEMA_SQL)))


def _columns(conn: sqlite3.Connection, table: str) -> list[tuple]:
    """(имя, тип, notnull, default) в порядке объявления."""
    return [(r[1], r[2], r[3], r[4]) for r in conn.execute(f"PRAGMA table_info({table})")]


@pytest.fixture(scope="module")
def fresh() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_SQL)
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def migrated() -> sqlite3.Connection:
    """БД, доведённая с v1 миграциями, — форма, в которой живут реальные БД.

    V1_SCHEMA берётся из test_migrations.py: это ЕДИНСТВЕННОЕ в репозитории
    объявление базовой схемы v1, и вторая его копия здесь была бы ровно тем
    дефектом, против которого написан весь этот гейт.
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from test_migrations import V1_SCHEMA

    conn = sqlite3.connect(":memory:")
    conn.isolation_level = None  # run_migrations ведёт свои транзакции
    conn.executescript(V1_SCHEMA)
    assert run_migrations(conn, 1) == SCHEMA_VERSION
    yield conn
    conn.close()


class TestUpgradePathMatchesFreshSchema:
    @pytest.mark.parametrize("table", _schema_tables())
    def test_column_sets_are_identical(self, table, fresh, migrated):
        """Набор колонок обязан совпадать по ИМЕНИ, ТИПУ, NOT NULL и DEFAULT.

        Сравнивается множество, а не список: расхождение порядка разбирается
        отдельным тестом ниже, иначе оно заслонило бы содержательные различия.
        """
        f = {c[0]: c for c in _columns(fresh, table)}
        m = {c[0]: c for c in _columns(migrated, table)}

        assert set(f) == set(m), (
            f"{table}: набор колонок разошёлся между путями. "
            f"только в свежей: {sorted(set(f) - set(m))}, "
            f"только в мигрированной: {sorted(set(m) - set(f))}"
        )

        drifted = [
            f"{table}.{name}: свежая {f[name][1:]} против мигрированной {m[name][1:]}"
            for name in sorted(f)
            if f[name] != m[name] and (table, name) not in _KNOWN_CONSTRAINT_DRIFT
        ]
        assert not drifted, (
            "объявление колонки различается между свежей БД и обновлённой — "
            "значит фикстура на каноне доказывает соответствие только свежей:\n"
            + "\n".join(drifted)
        )

    def test_known_constraint_drift_is_still_real(self, fresh, migrated):
        """Протухшая запись храповика прикрывала бы новое расхождение."""
        stale = []
        for table, column in sorted(_KNOWN_CONSTRAINT_DRIFT):
            f = {c[0]: c for c in _columns(fresh, table)}
            m = {c[0]: c for c in _columns(migrated, table)}
            if column not in f or column not in m or f[column] == m[column]:
                stale.append(f"{table}.{column}")
        assert not stale, f"расхождение исправлено — уберите запись из храповика: {stale}"

    def test_the_drift_list_only_ever_shrinks(self):
        assert len(_KNOWN_CONSTRAINT_DRIFT) <= 1, (
            f"расхождений стало {len(_KNOWN_CONSTRAINT_DRIFT)} — каждое обязано "
            "быть объяснено в докстринге модуля и заведено задачей"
        )


class TestColumnOrderDivergence:
    """Порядок колонок расходится неизбежно — важно, что из этого следует."""

    def test_order_drift_is_confined_to_known_tables(self, fresh, migrated):
        drifted = {
            t
            for t in _schema_tables()
            if [c[0] for c in _columns(fresh, t)] != [c[0] for c in _columns(migrated, t)]
        }
        assert drifted == _KNOWN_ORDER_DRIFT, (
            "список таблиц с разошедшимся порядком колонок изменился: "
            f"стало {sorted(drifted)}, ожидалось {sorted(_KNOWN_ORDER_DRIFT)}. "
            "Новая такая таблица — не беда сама по себе, но она расширяет зону, "
            "где позиционный INSERT означает разное на свежей и обновлённой БД."
        )

    def test_production_code_never_inserts_positionally(self):
        """Прямое следствие расхождения порядка.

        `INSERT INTO t VALUES (...)` без списка колонок привязывается к их
        ПОРЯДКУ, а он у свежей и обновлённой БД разный. Такой запрос поэтому
        означает разное на разных машинах — на CI зелено, у пользователя
        данные в чужих колонках.
        """
        offenders = []
        pattern = re.compile(r"INSERT\s+(?:OR\s+\w+\s+)?INTO\s+(\w+)\s*VALUES", re.IGNORECASE)
        for dirpath, _dirs, files in os.walk(_SCRIPTS):
            for name in files:
                if not name.endswith(".py"):
                    continue
                path = os.path.join(dirpath, name)
                with open(path, encoding="utf-8") as fh:
                    for i, line in enumerate(fh, 1):
                        if pattern.search(line):
                            offenders.append(f"{os.path.relpath(path, _ROOT)}:{i}: {line.strip()}")
        assert not offenders, (
            "позиционный INSERT привязан к порядку колонок, а порядок у свежей "
            "и обновлённой БД разный — перечислите колонки поимённо:\n" + "\n".join(offenders)
        )


class TestTheGateIsNotHollow:
    """Гейт, сравнивающий пустое с пустым, был бы зелен всегда."""

    def test_both_paths_actually_built_something(self, fresh, migrated):
        for conn, label in ((fresh, "fresh"), (migrated, "migrated")):
            tables = {
                r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            assert len(tables) >= 15, f"{label}: схема не построилась, таблиц {len(tables)}"

    def test_the_table_list_is_derived_not_hardcoded(self):
        tables = _schema_tables()
        assert len(tables) >= 15 and "tasks" in tables and "verification_runs" in tables

    def test_a_planted_constraint_difference_would_be_caught(self, fresh):
        """Проверка самого метода сравнения, а не только его результата."""
        probe = sqlite3.connect(":memory:")
        probe.execute("CREATE TABLE tasks (id INTEGER PRIMARY KEY, model_mismatch INTEGER)")
        f = {c[0]: c for c in _columns(fresh, "tasks")}
        m = {c[0]: c for c in _columns(probe, "tasks")}
        assert f["model_mismatch"] != m["model_mismatch"]
        probe.close()
