"""Two MCP tool calls, one connection, one `_in_tx` flag: whose commit is it?

The MCP server hands EVERY tool call to its own thread (`asyncio.to_thread`)
over ONE process-wide `ProjectService` whose `sqlite3.Connection` is opened
`check_same_thread=False`, and the dispatch path takes no lock. So two
overlapping tool calls share the connection, the open transaction and the
single `_in_tx` flag that every write consults.

`verify_handle._write` already says this in prose -- it refuses to call
`conn.commit()` precisely because it "would commit whatever is pending on the
connection, including a half-written `task_done` from a CONCURRENT call". These
tests turn that paragraph into a measurement.

The damage is asserted on ROWS and on the flag, never on an exception, because
no exception is raised in any of these scenarios. That is the whole point: the
losing thread is told its call succeeded.
"""

from __future__ import annotations

import os
import sys
import threading

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend  # noqa: E402


@pytest.fixture
def be(tmp_path):
    backend = SQLiteBackend(str(tmp_path / "concurrent.db"))
    yield backend
    backend.close()


def _run_both(first, second, *, handoff_timeout=5.0):
    """Run `first` and `second` on two threads with a deterministic handoff.

    `first` gets an event to signal "I am mid-transaction"; `second` waits for
    it, runs, and signals back. No sleeps: the interleaving under test is a
    specific ordering, and a sleep would make the test both slower and flakier.
    """
    mid = threading.Event()
    done = threading.Event()
    errors: list[BaseException] = []

    def wrap(fn, *args):
        try:
            fn(*args)
        except BaseException as e:  # noqa: BLE001 -- reported, not swallowed
            errors.append(e)

    t2 = threading.Thread(target=wrap, args=(second, mid, done))
    t2.start()
    wrap(first, mid, done)
    t2.join(timeout=handoff_timeout)
    assert not t2.is_alive(), "the second thread never finished -- deadlock?"
    return errors


class TestAConcurrentCallCommitsSomebodyElsesHalfWrittenWork:
    def test_the_second_callers_commit_lands_the_firsts_unfinished_rows(self, be):
        """THE DEFECT. Thread A is mid-transaction; thread B commits it.

        A has written one row of a two-row change and has NOT committed. B --
        an unrelated tool call -- opens its own transaction (a no-op: the flag
        is already set), writes, and commits. B's commit is the CONNECTION's
        commit, so A's half-written change becomes durable while A still
        believes it holds an open transaction it can still abandon.
        """

        def thread_a(mid, done):
            be.begin_tx()
            be.epic_add("a-first-half", "A, first half", None)
            mid.set()
            done.wait(timeout=5.0)
            # A decides to abandon its change. It is already too late.
            be.rollback_tx()

        def thread_b(mid, done):
            mid.wait(timeout=5.0)
            be.begin_tx()
            be.epic_add("b-row", "B's own row", None)
            be.commit_tx()
            done.set()

        errors = _run_both(thread_a, thread_b)
        assert not errors, f"nobody is supposed to raise here: {errors}"

        # A rolled back. Its row is here anyway, committed by B.
        assert be.epic_get("a-first-half") is not None, (
            "A's abandoned half-write survived because B's commit was the connection's"
        )

    def test_the_second_callers_rows_vanish_with_the_firsts_rollback(self, be):
        """The mirror image: B succeeds, is told so, and loses its work.

        B's `commit_tx` never ran because A got there first with a rollback.
        B returned normally -- the agent on the other end of that tool call was
        told the write happened.
        """

        def thread_a(mid, done):
            be.begin_tx()
            be.epic_add("a-row", "A's row", None)
            mid.set()
            done.wait(timeout=5.0)
            be.rollback_tx()

        def thread_b(mid, done):
            mid.wait(timeout=5.0)
            # B does not open a transaction at all -- a plain write. `_ex`
            # commits only when `_in_tx` is False, and A has it True, so B's
            # row silently joins A's transaction.
            be.epic_add("b-row", "B's row", None)
            done.set()

        errors = _run_both(thread_a, thread_b)
        assert not errors, f"nobody is supposed to raise here: {errors}"

        assert be.epic_get("b-row") is None, (
            "B was told its write succeeded, and A's rollback took it"
        )
