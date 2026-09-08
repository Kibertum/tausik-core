"""Which tests have ever been observed FAILING, and what that is good for.

RENAR §9.18.2. Author isolation proves the test was written before the code; it
does not prove the test checks anything. An empty test is green from birth and
passes every P8 axis. A test that has been seen RED at least once has, at that
moment, demonstrated it can distinguish one state of the world from another —
which is the smallest honest definition of "it checks something".

WHAT THIS DELIBERATELY DOES NOT CLAIM. A red history does not make a test GOOD:
a test can fail for a silly reason and still assert nothing useful afterwards.
It rules out exactly one thing — the test that has never, in its life, been able
to fail. That is a narrow claim and it is stated narrowly, because the wider one
("red history means the test is real evidence") is unearned and is the class of
statement this release exists to remove.

ONLY REDS ARE RECORDED. A green outcome carries no information — a test is green
by default — and writing a row per node per run would mean 10,357 upserts on
every suite run. In this same session the coverage observer took the suite from
14.5s to a five-minute timeout before it was cached; the lesson is recent and
cheap to apply.

DECLARED RESIDUAL, SAID HERE AND NOT ONLY IN THE TASK: `.tausik/tausik.db` is
not version-controlled. Red history therefore lives on the machine that
observed it and does NOT travel between machines or agents. A fresh clone starts
with an empty history, which is why the rule REPORTS rather than blocks — see
`REPORTING_ONLY` below. Anyone offering this as a framework guarantee has to say
that in the same breath.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone

__all__ = [
    "REPORTING_ONLY",
    "count",
    "ever_red",
    "record_reds",
    "reds_for_file",
    "unproven",
]

#: The rule reports and does not block, and the reason is arithmetic rather than
#: caution: red history accumulates only by running the suite, so on the day it
#: lands NO node has any. A blocking rule would mean nothing can be closed.
#:
#: THE THRESHOLD FOR FLIPPING IT, named as a number and a condition rather than
#: "someday": when the recorded set covers at least 200 distinct nodes AND at
#: least 30 days of runs have passed, the check has enough history to tell "this
#: test cannot fail" from "nobody has run the suite here yet". Until both hold,
#: a missing history is silence, not a verdict.
REPORTING_ONLY = True

#: How many distinct nodes must carry a red before the rule could block.
BLOCKING_NEEDS_NODES = 200

#: And how many days of accumulation.
BLOCKING_NEEDS_DAYS = 30


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _connect(db_path: str) -> sqlite3.Connection | None:
    """None rather than an exception: recording history must never break a run.

    A caller that cannot open the database has learned nothing about the tests,
    and saying so by returning None is different from saying "no test was ever
    red" — the second is a claim, and it would be false.
    """
    if not os.path.isfile(db_path):
        return None
    try:
        return sqlite3.connect(db_path, timeout=5)
    except sqlite3.Error:
        return None


def record_reds(db_path: str, nodeids: list[str], when: str | None = None) -> int:
    """Record that these nodes were observed failing. Returns rows written.

    Idempotent per node per call: a node failing twice in one run is one
    observation of one fact. The count column answers "how often", which is
    weaker evidence than "ever" and is kept only because it is free.
    """
    unique = sorted({n for n in nodeids if n})
    if not unique:
        return 0
    conn = _connect(db_path)
    if conn is None:
        return 0
    stamp = when or _now()
    try:
        with conn:
            conn.executemany(
                "INSERT INTO test_red_history (nodeid, first_red_at, last_red_at, reds) "
                "VALUES (?, ?, ?, 1) "
                "ON CONFLICT(nodeid) DO UPDATE SET "
                "  last_red_at = excluded.last_red_at, reds = reds + 1",
                [(nodeid, stamp, stamp) for nodeid in unique],
            )
    except sqlite3.Error:
        # The table may not exist yet on a database that has not migrated. That
        # is not a run failure and must not become one.
        return 0
    finally:
        conn.close()
    return len(unique)


def ever_red(db_path: str, nodeid: str) -> bool:
    """Has this exact node been observed failing?

    Exact, not prefix: `test_x[a]` and `test_x[b]` are different nodes and a red
    in one says nothing about the other. `reds_for_file` answers the wider
    question, and the two are kept apart so a caller cannot get the wider answer
    while believing it asked the narrow one.
    """
    conn = _connect(db_path)
    if conn is None:
        return False
    try:
        row = conn.execute("SELECT 1 FROM test_red_history WHERE nodeid = ?", (nodeid,)).fetchone()
    except sqlite3.Error:
        return False
    finally:
        conn.close()
    return row is not None


def reds_for_file(db_path: str, path: str) -> list[str]:
    """Every node of one test file that has been observed failing."""
    conn = _connect(db_path)
    if conn is None:
        return []
    try:
        rows = conn.execute(
            "SELECT nodeid FROM test_red_history WHERE nodeid LIKE ? ORDER BY nodeid",
            (f"{path}::%",),
        ).fetchall()
    except sqlite3.Error:
        return []
    finally:
        conn.close()
    return [str(r[0]) for r in rows]


def count(db_path: str) -> int:
    """How many distinct nodes carry any red history.

    Zero has two meanings — nothing was ever red, or nobody ran the suite here —
    and the caller is expected to keep them apart. `REPORTING_ONLY` exists
    because on a fresh clone the second is always the true one.
    """
    conn = _connect(db_path)
    if conn is None:
        return 0
    try:
        row = conn.execute("SELECT COUNT(*) FROM test_red_history").fetchone()
    except sqlite3.Error:
        return 0
    finally:
        conn.close()
    return int(row[0]) if row else 0


def unproven(db_path: str, nodeids: list[str]) -> list[str]:
    """Which of these CITED nodes have never been observed failing.

    The question is asked about a closure's citations, not about the whole
    suite, and that narrowing is the design rather than a shortcut.

    A GLOBAL RATCHET WAS CONSIDERED AND REJECTED, and the reason belongs here
    because the alternative looks obviously right until it is written down.
    "The number of nodes without red history may only shrink" is not
    well-formed: history only grows, so the count falls on its own, while every
    NEW test raises it — the ratchet would go red on ordinary work and be
    switched off within a week. "The number WITH red history may only grow" is
    well-formed and says nothing: it is monotone by construction and can fail
    only if somebody deletes the database.

    What IS well-formed is per-closure: a task citing a test it just wrote,
    where that test has never been seen failing, has cited something that has
    not yet shown it can fail. That is a statement about this closure, checkable
    now, and it does not devalue the 10,357 existing nodes by a single one.
    """
    return [nodeid for nodeid in nodeids if not ever_red(db_path, nodeid)]
