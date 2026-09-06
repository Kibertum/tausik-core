"""Transaction ownership for SQLiteBackend -- one accounting, not nine copies.

WHY THIS MODULE EXISTS. `begin_tx` is a no-op inside an open transaction
(deliberate: there is no nesting), but `commit_tx` and `rollback_tx` act
unconditionally. So a function that opens and closes a transaction
unconditionally, called from INSIDE someone else's, ends THEIR transaction:
on a refusal it rolls back their rows and hands them back a closed
transaction they still believe they own, and no exception says so. Measured
live in session #211: an outer `begin_tx` + `epic_add` lost its epic to a
nested `adapt_delta` that refused.

The rule was known and written down -- in ONE call site's docstring, applied by
hand at two more as `owns_tx = not self.be._in_tx`, a service reaching into the
backend's private flag. Nine sites open a transaction; the count grew while the
rule stayed a thing each caller had to remember. `transaction()` is that rule
implemented once.

WHAT IT DOES, AND THE HALF THAT IS NEW:
  * OUTERMOST (no transaction open) -- exactly today's behaviour, deliberately
    unchanged: BEGIN IMMEDIATE, `commit_tx` on success, `rollback_tx` on an
    exception. `_ex`/`_ins` decide whether to commit by reading `_in_tx`, and
    the WAL checkpoint plus the projection flush hang off `commit_tx`; routing
    the outer case through SAVEPOINT instead would disturb both for no gain.
  * NESTED (a transaction is already open) -- a SAVEPOINT. On success RELEASE,
    so our writes stay in the caller's transaction and land with their commit.
    On an exception ROLLBACK TO + RELEASE: our part is undone, the caller's
    transaction stays OPEN and their rows untouched. That is the guarantee the
    backend could not previously make -- `adapt_delta` could only DELEGATE the
    cleanup to whoever owned the transaction, which left "a refusal is a
    non-event" conditional on the caller remembering to roll back.

SAVEPOINT semantics were MEASURED on this backend's exact connection setup
(WAL, foreign_keys=ON, default isolation_level), not taken from documentation:
a nested ROLLBACK TO leaves `conn.in_transaction` True and removes only the
nested rows.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING

# SAVEPOINT names are identifiers, not bindable parameters, so they can never
# come from caller input -- the counter below is the only source.
#
# THE COUNTER IS NOT LOAD-BEARING TODAY, AND THAT IS DECLARED RATHER THAN
# TESTED. Replacing it with one constant name is a mutation that SURVIVES the
# suite, and it survives honestly: SQLite resolves `ROLLBACK TO`/`RELEASE` to
# the MOST RECENT savepoint of that name, and a context manager can only
# produce strictly LIFO pairs, so a shared name gives identical results.
# Measured, both halves:
#   * LIFO, every ROLLBACK TO paired with its RELEASE -> reused names behave
#     exactly like unique ones;
#   * the one shape that differs -- rolling back to an outer name while an
#     inner savepoint of the SAME name is still open -- returns the inner rows
#     instead of unwinding to the outer point. `transaction()` cannot reach
#     that shape: its ROLLBACK TO and RELEASE sit in the same `except` block.
# So the counter buys independence from that resolution rule for whoever edits
# this next, not a behaviour difference now. Writing a test that "kills" the
# mutant would mean asserting the name strings themselves -- pinning the
# implementation instead of the guarantee.
_SAVEPOINT_PREFIX = "tausik_sp_"


class BackendTransactionMixin:
    """Explicit transactions plus the ownership rule, in one place."""

    _conn: sqlite3.Connection
    _in_tx: bool
    _pending_projection: list[tuple[str, str]]
    _savepoint_seq: int

    if TYPE_CHECKING:
        # Both live on SQLiteBackend itself and are reached through the
        # composed class. Declared under TYPE_CHECKING ONLY: a real `def` here
        # would be a live method that WINS the MRO over the backend's own,
        # silently replacing the projection flush with a no-op.
        def _checkpoint(self) -> None: ...

        def _flush_pending_projection(self) -> None: ...

    def begin_tx(self) -> None:
        """Begin explicit transaction for multi-step operations."""
        if self._in_tx:
            return  # already in transaction, no nesting
        self._conn.execute("BEGIN IMMEDIATE")
        self._in_tx = True

    def commit_tx(self) -> None:
        """Commit explicit transaction."""
        self._conn.commit()
        self._in_tx = False
        self._checkpoint()
        self._flush_pending_projection()

    def rollback_tx(self) -> None:
        """Rollback explicit transaction."""
        self._conn.rollback()
        self._in_tx = False
        # Discarded, not projected: these rows no longer exist as written.
        self._pending_projection.clear()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Run a block in a transaction we own, or a SAVEPOINT inside someone else's.

        Use this instead of hand-writing `owns_tx = not be._in_tx` around
        begin/commit/rollback. The difference is not style: the hand-written
        form leaves a nested refusal's writes sitting in the caller's
        transaction, because it has no way to undo just its own part.
        """
        if not self._in_tx:
            self.begin_tx()
            try:
                yield
            except BaseException:
                self.rollback_tx()
                raise
            self.commit_tx()
            return

        self._savepoint_seq += 1
        name = f"{_SAVEPOINT_PREFIX}{self._savepoint_seq}"
        # Everything the CALLER queued before us. A nested rollback must not
        # clear the whole queue -- that would drop projections for rows that
        # are still very much in the database.
        mark = len(self._pending_projection)
        self._conn.execute(f"SAVEPOINT {name}")
        try:
            yield
        except BaseException:
            self._conn.execute(f"ROLLBACK TO {name}")
            self._conn.execute(f"RELEASE {name}")
            del self._pending_projection[mark:]
            raise
        self._conn.execute(f"RELEASE {name}")
