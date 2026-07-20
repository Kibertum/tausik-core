"""Gate outcomes are persisted, and the two DDL paths agree (l26-gate-results-persist).

Gate results lived only in run_gates' return value, so TAUSIK could not answer
the simplest questions about its own enforcement: how often a gate blocks,
which gate has never fired, whether failures are trending. This suite covers
the table, its two creation paths, and the aggregates built on it.

Schema equivalence is checked by diffing sqlite_master between a migrated DB
and a fresh one — never against a hardcoded column list (convention #214).
A hardcoded list is precisely how the verification_runs tests drifted from the
schema they claim to describe.
"""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from backend_schema import SCHEMA_VERSION  # noqa: E402
from backend_schema_gate_runs import GATE_RUNS_SQL  # noqa: E402
from gate_run_record import gate_activity, record_gate_runs  # noqa: E402


def _objects(conn: sqlite3.Connection) -> set[tuple[str, str]]:
    """(type, normalised sql) for gate_runs objects, straight from sqlite_master."""
    rows = conn.execute(
        "SELECT type, name, sql FROM sqlite_master "
        "WHERE name LIKE 'gate_runs%' OR name LIKE 'idx_gate_runs%'"
    ).fetchall()
    return {(r[0], " ".join((r[2] or "").split())) for r in rows}


def _columns(conn: sqlite3.Connection) -> list[tuple]:
    return [(r[1], r[2], r[3], r[5]) for r in conn.execute("PRAGMA table_info(gate_runs)")]


@pytest.fixture
def conn(tmp_path):
    c = sqlite3.connect(str(tmp_path / "t.db"))
    c.execute("PRAGMA foreign_keys=ON")
    c.executescript("CREATE TABLE verification_runs (id INTEGER PRIMARY KEY AUTOINCREMENT);")
    c.executescript(GATE_RUNS_SQL)
    c.execute("INSERT INTO verification_runs DEFAULT VALUES")
    c.commit()
    yield c
    c.close()


def _results(*specs):
    """(name, severity, passed, skipped) tuples -> run_gates-shaped dicts."""
    return [
        {
            "name": n,
            "severity": sev,
            "passed": p,
            "skipped": sk,
            "duration_ms": 7,
            "output": "",
        }
        for n, sev, p, sk in specs
    ]


class TestSchemaPaths:
    def test_migration_is_derived_from_the_same_ddl(self):
        """Not mirrored by hand: drift between the paths is impossible."""
        from backend_migrations_v39 import MIGRATION_V39

        assert MIGRATION_V39
        joined = " ".join(" ".join(s.split()) for s in MIGRATION_V39)
        assert "CREATE TABLE IF NOT EXISTS gate_runs" in joined
        assert joined.count("CREATE INDEX") == 3

    def test_migrated_and_fresh_schemas_are_identical(self, tmp_path):
        fresh = sqlite3.connect(str(tmp_path / "fresh.db"))
        migrated = sqlite3.connect(str(tmp_path / "migrated.db"))
        for c in (fresh, migrated):
            c.executescript("CREATE TABLE verification_runs (id INTEGER PRIMARY KEY);")

        fresh.executescript(GATE_RUNS_SQL)
        from backend_migrations_v39 import MIGRATION_V39

        for stmt in MIGRATION_V39:
            migrated.execute(stmt)

        # Derived from sqlite_master, not from a list written by hand.
        assert _objects(migrated) == _objects(fresh)
        assert _columns(migrated) == _columns(fresh)
        fresh.close()
        migrated.close()

    def test_schema_version_advanced(self):
        assert SCHEMA_VERSION >= 39


class TestRecording:
    def test_rows_carry_duration_and_skip_state(self, conn):
        record_gate_runs(
            conn,
            verification_run_id=1,
            task_slug="t",
            trigger="verify",
            gate_results=_results(("filesize", "block", True, False), ("x", "warn", True, True)),
        )
        conn.commit()
        rows = conn.execute(
            "SELECT gate_name, severity, passed, skipped, duration_ms, task_slug, trigger "
            "FROM gate_runs ORDER BY gate_name"
        ).fetchall()
        assert rows[0] == ("filesize", "block", 1, 0, 7, "t", "verify")
        assert rows[1] == ("x", "warn", 1, 1, 7, "t", "verify")

    def test_empty_results_write_nothing(self, conn):
        assert (
            record_gate_runs(
                conn, verification_run_id=1, task_slug=None, trigger=None, gate_results=[]
            )
            == 0
        )

    def test_orphan_run_id_is_refused(self, conn):
        """FK is enforced (PRAGMA foreign_keys=ON), so evidence cannot dangle."""
        with pytest.raises(sqlite3.IntegrityError):
            record_gate_runs(
                conn,
                verification_run_id=999,
                task_slug="t",
                trigger="verify",
                gate_results=_results(("filesize", "block", True, False)),
            )

    def test_failure_leaves_no_partial_transaction(self, conn):
        """The caller's rollback must take the whole run down, not half of it."""
        conn.execute("INSERT INTO verification_runs DEFAULT VALUES")
        with pytest.raises(sqlite3.IntegrityError):
            record_gate_runs(
                conn,
                verification_run_id=999,
                task_slug="t",
                trigger="verify",
                gate_results=_results(("a", "block", True, False)),
            )
        conn.rollback()
        assert conn.execute("SELECT COUNT(*) FROM gate_runs").fetchone()[0] == 0


class TestAggregates:
    def test_counts_split_failures_blocks_and_skips(self, conn):
        record_gate_runs(
            conn,
            verification_run_id=1,
            task_slug="t",
            trigger="verify",
            gate_results=_results(
                ("filesize", "block", False, False),
                ("filesize", "block", True, False),
                ("lint", "warn", False, False),
                ("lint", "warn", True, True),
            ),
        )
        conn.commit()
        summary = gate_activity(conn, [])
        by_name = {g["gate"]: g for g in summary["gates"]}
        assert by_name["filesize"] == {
            "gate": "filesize",
            "runs": 2,
            "failures": 1,
            "blocking_failures": 1,
            "skips": 0,
        }
        assert by_name["lint"]["failures"] == 1
        assert by_name["lint"]["blocking_failures"] == 0  # warn never blocks
        assert by_name["lint"]["skips"] == 1
        assert summary["total_runs"] == 4
        assert summary["blocking_failure_rate"] == 0.25

    def test_configured_gate_that_never_ran_is_reported_as_zero(self, conn):
        """The most useful fact this table holds must not render as absence."""
        record_gate_runs(
            conn,
            verification_run_id=1,
            task_slug="t",
            trigger="verify",
            gate_results=_results(("filesize", "block", True, False)),
        )
        conn.commit()
        summary = gate_activity(conn, ["filesize", "hadolint", "never-used"])
        by_name = {g["gate"]: g for g in summary["gates"]}
        assert by_name["hadolint"]["runs"] == 0
        assert summary["never_fired"] == ["hadolint", "never-used"]

    def test_empty_table_reports_none_not_zero_rate(self, conn):
        """No runs means the rate is unknown, not 0% — absence isn't a value."""
        summary = gate_activity(conn, ["filesize"])
        assert summary["total_runs"] == 0
        assert summary["blocking_failure_rate"] is None
        assert summary["never_fired"] == ["filesize"]
