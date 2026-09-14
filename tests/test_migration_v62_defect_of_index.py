"""v62: the defect-escape lookup runs on an index, on both install paths.

Measured in session #261 on this project's live database (1654 tasks, 1504
done): `tausik status` took 5.3 s and 5.04 s of it was ONE statement —
`backend_defect_escape._done_rows`, whose `EXISTS(... WHERE d.defect_of =
t.slug)` had no index and scanned the wide `tasks` table once per done row. The
SessionStart hook, which calls `status`, took 5.9 s against a 6 s timeout and
was cancelled in a headless probe: the auto-injected context never arrived,
and nothing said so.

What is held here is not the timing (a CI runner's clock proves nothing about
a laptop) but the PLAN: the statement `_done_rows` actually issues must reach
`tasks.defect_of` through `idx_tasks_defect_of`, on a fresh database and on
one carried up by migrations. Presence of the index on both paths is already
held by tests/test_schema_index_parity.py, which reads
POST_MIGRATION_INDEXES_SQL; this file holds that the query USES it, so a
future rewrite of the statement cannot quietly fall back to the scan.
"""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
)

from backend_defect_escape import _done_rows  # noqa: E402
from backend_init import init_schema  # noqa: E402
from backend_migrations_v62 import MIGRATION_V62  # noqa: E402

_INDEX = "idx_tasks_defect_of"


def _plan_of_done_rows(conn: sqlite3.Connection) -> str:
    """The EXPLAIN QUERY PLAN of the exact SQL `_done_rows` issues."""
    plans: list[str] = []

    def q(sql: str, params: tuple = ()) -> list:
        plans.append(
            "\n".join(str(r[3]) for r in conn.execute("EXPLAIN QUERY PLAN " + sql, params))
        )
        return []

    _done_rows(q)
    return "\n".join(plans)


@pytest.fixture
def fresh(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "fresh.db"))
    init_schema(conn)
    yield conn
    conn.close()


class TestTheMigrationLiteral:
    def test_v62_creates_exactly_the_defect_of_index(self):
        """The literal is frozen (convention #646): one statement, one index,
        IF NOT EXISTS so a database that already has it through the current
        index set is not an error."""
        assert MIGRATION_V62 == [
            "CREATE INDEX IF NOT EXISTS idx_tasks_defect_of ON tasks(defect_of)"
        ]


class TestTheDefectOfLookupUsesTheIndex:
    def test_on_a_fresh_install(self, fresh):
        plan = _plan_of_done_rows(fresh)
        assert _INDEX in plan, f"the defect_of EXISTS does not use {_INDEX}:\n{plan}"
        assert "SCAN d" not in plan and "SCAN tasks AS d" not in plan, plan

    def test_negative_without_the_index_the_plan_is_a_scan(self, fresh):
        """The assertion above is only worth something if it goes red when
        the index is gone — so drop it and watch the plan fall back."""
        fresh.execute(f"DROP INDEX {_INDEX}")
        plan = _plan_of_done_rows(fresh)
        assert _INDEX not in plan
        assert "SCAN" in plan, plan

    def test_after_the_v62_migration_on_a_database_without_it(self, tmp_path):
        """A v61 database gets the index from the migration itself, not only
        from POST_MIGRATION_INDEXES_SQL — init_schema skips all DDL when the
        stamped version already equals SCHEMA_VERSION, so the bump is what
        reaches an existing install."""
        conn = sqlite3.connect(str(tmp_path / "v61.db"))
        init_schema(conn)
        conn.execute(f"DROP INDEX {_INDEX}")
        assert _INDEX not in _plan_of_done_rows(conn)
        for stmt in MIGRATION_V62:
            conn.execute(stmt)
        assert _INDEX in _plan_of_done_rows(conn)
        conn.close()
