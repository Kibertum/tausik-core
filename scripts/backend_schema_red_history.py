"""The fresh-database definition of `test_red_history`.

WHY THIS FILE EXISTS AT ALL, and it is not symmetry for its own sake. A NEW
database never runs a migration: `backend_init` stamps `meta.schema_version` with
the current `SCHEMA_VERSION` and then calls `run_migrations(conn,
SCHEMA_VERSION)`, which applies only migrations ABOVE that number — none. So every
table a fresh install has comes from a `CREATE TABLE` executed on the fresh path,
and a table added ONLY as a migration exists in upgraded databases and in no new
one.

MEASURED (session #239, on a real fresh install into an empty project):
`meta.schema_version` said 60, the database had 91 tables, and
`test_red_history` was NOT among them. Red history therefore recorded nothing on
any new project — SILENTLY, because `red_history.record_reds` swallows the
sqlite error by design so that observation can never break a test run. A working
mechanism nobody calls, reporting success: the exact class this release was
assembled to remove, reproduced by the task that closed the last of it.

THE TWO COPIES AND WHY THEY DO NOT DRIFT. `backend_migrations_v60.MIGRATION_V60`
is a FROZEN snapshot (convention #646) — it must mean in five years what v60
meant the day it landed. The statement below is the LIVING definition and may be
extended by a later migration plus an edit here. They are not kept in step by
discipline: `tests/test_fresh_install_has_every_migrated_table.py` builds a fresh
database and requires every table any migration creates to be present in it, so
the next person who adds a migration and forgets this file is told immediately.
Same arrangement as `backend_schema_gate_runs.GATE_RUNS_SQL` against v39.
"""

from __future__ import annotations

RED_HISTORY_SQL = """
CREATE TABLE IF NOT EXISTS test_red_history (
    nodeid TEXT PRIMARY KEY,
    first_red_at TEXT NOT NULL,
    last_red_at TEXT NOT NULL,
    reds INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_test_red_history_file
    ON test_red_history(substr(nodeid, 1, instr(nodeid, '::') - 1));
"""
