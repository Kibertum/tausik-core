"""v79 adds review cohorts without rewriting legacy review evidence."""

from __future__ import annotations

import sqlite3

from backend_migrations import run_migrations
from backend_schema import SCHEMA_SQL, SCHEMA_VERSION


def test_v79_preserves_legacy_review_rows_and_adds_bounded_tables():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    conn.executescript(
        "DROP TABLE review_cohort_packets;"
        "DROP TABLE review_cohort_results;"
        "DROP TABLE review_cohort_rounds;"
        "DROP TABLE review_cohorts;"
    )
    conn.execute("UPDATE meta SET value='78' WHERE key='schema_version'")
    conn.execute(
        "INSERT INTO tasks(slug,title,status,created_at,updated_at) "
        "VALUES('legacy','Legacy','active','2026-01-01','2026-01-01')"
    )
    conn.execute(
        "INSERT INTO reviews(task_slug,run_type,critical_findings,warnings,run_at,notes) "
        "VALUES('legacy','L3',0,2,'2026-01-01','keep me')"
    )
    before = dict(conn.execute("SELECT * FROM reviews").fetchone())
    conn.commit()

    assert run_migrations(conn, 78) == SCHEMA_VERSION

    assert dict(conn.execute("SELECT * FROM reviews").fetchone()) == before
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'review_cohort%'"
        )
    }
    assert tables == {
        "review_cohorts",
        "review_cohort_rounds",
        "review_cohort_results",
        "review_cohort_packets",
    }
    cohort_columns = {row[1] for row in conn.execute("PRAGMA table_info(review_cohorts)")}
    result_columns = {row[1] for row in conn.execute("PRAGMA table_info(review_cohort_results)")}
    assert {"family_key", "generation", "parent_cohort_pk"} <= cohort_columns
    assert {
        "author_model",
        "dependency_map_complete",
        "critical_reason",
        "finding_refs_json",
    } <= result_columns
    conn.close()
