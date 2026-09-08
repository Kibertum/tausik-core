"""Migration v60: a test that was never observed RED leaves a trace of that.

RENAR §9.18.2. Author isolation guarantees the test was written before the code;
it does not guarantee the test CHECKS anything. An empty test, honestly written
by an isolated agent, is green from birth and passes every P8 axis. Red history
closes exactly that remainder: a test never seen failing stops counting as
evidence, so writing one "just in case" stops paying.

ONLY RED IS STORED, and that is a design decision rather than an economy. A
green outcome carries no information — a test is green by default — while
writing a row per node per run means 10,357 upserts every time anyone runs the
suite. The cost is not hypothetical: in this same session the coverage observer
took the suite from 14.5s to a five-minute timeout until a cache was added.
Reds are rare, few per run, and are the whole signal.

MEASURED BEFORE THE SHAPE WAS CHOSEN (session #239): `tests/` defines 7,524 test
functions, pytest collects 10,357 nodes, and `docs/_generated/constants.json`
says 10,240 — three different numbers for three different questions. The task
description said 5,722, which was true earlier in the release and is not now.
The key here is the NODE id, because that is what a run reports and what a
closure cites; a question about a function rolls up from its nodes.

THE LITERAL BELOW IS FROZEN (convention #646). A migration that read the live
schema would mean whatever that schema means today, so a database migrated in
June and one migrated now would differ while both reported v60.
"""

from __future__ import annotations

#: What a run reports and what a closure cites: `tests/test_x.py::TestY::test_z`,
#: with the parameter id when there is one.
MIGRATION_V60: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS test_red_history (
        nodeid TEXT PRIMARY KEY,
        first_red_at TEXT NOT NULL,
        last_red_at TEXT NOT NULL,
        reds INTEGER NOT NULL DEFAULT 1
    )
    """,
    # Answering "which tests in this file were ever red" without scanning the
    # table: a closure cites a file far more often than a single node.
    """
    CREATE INDEX IF NOT EXISTS idx_test_red_history_file
        ON test_red_history(substr(nodeid, 1, instr(nodeid, '::') - 1))
    """,
]
