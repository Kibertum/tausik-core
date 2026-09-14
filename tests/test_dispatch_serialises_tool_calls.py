"""One tool call at a time, so a second one cannot commit the first one's half.

`tests/test_concurrent_dispatch_shares_a_transaction.py` measures the damage at
the BACKEND level, where it is still possible: two threads sharing one
connection lose each other's writes with no exception raised. The backend is
not where that gets fixed -- the losing path in the second measured case never
opens a transaction at all, so no lock inside `transaction()` could catch it.

It is fixed one level up, at the dispatch every MCP tool call goes through.
This file holds that: two calls entering `handle_tool` concurrently do not
overlap, and a handler that dispatches a second tool inside itself does not
deadlock on the way.
"""

from __future__ import annotations

import os
import sys
import threading

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project")
)

import handlers  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "dispatch.db")))
    yield s
    s.be.close()


@pytest.fixture
def registered(monkeypatch):
    """Install throwaway tools in the dispatch table, removed on teardown."""
    table = dict(handlers._DISPATCH)
    monkeypatch.setattr(handlers, "_DISPATCH", table)
    return table


def test_a_second_call_cannot_enter_while_the_first_is_inside(svc, registered):
    """THE GUARANTEE. Without the lock the second call runs mid-transaction.

    The slow tool signals that it is inside its transaction, waits out the
    window the defect lives in, and then RECORDS whether the second call got in
    during it. That recording is the assertion: waiting on an event the second
    call sets would only prove the two threads can signal each other, which
    they can with or without a lock.

    `second_finished` is the other half -- it shows the second call was BLOCKED
    rather than never started, by completing as soon as the first returns.
    """
    inside = threading.Event()
    second_entered = threading.Event()
    second_finished = threading.Event()
    overlapped: list[bool] = []

    def slow_tool(service, args):
        with service.be.transaction():
            service.be.epic_add("slow-epic", "Written by the slow tool", None)
            inside.set()
            # Not a handshake: an unserialised second call needs no permission
            # to run, so this is simply long enough that it certainly would
            # have. Serialised, nothing happens here and the wait times out.
            second_entered.wait(timeout=1.0)
            overlapped.append(second_entered.is_set())
        return "slow done"

    def quick_tool(service, args):
        second_entered.set()
        service.be.epic_add("quick-epic", "Written by the quick tool", None)
        return "quick done"

    registered["test_slow"] = slow_tool
    registered["test_quick"] = quick_tool

    def run_second():
        inside.wait(timeout=5.0)
        handlers.handle_tool(svc, "test_quick", {})
        second_finished.set()

    t = threading.Thread(target=run_second)
    t.start()
    result = handlers.handle_tool(svc, "test_slow", {})
    t.join(timeout=5.0)

    assert not t.is_alive(), "the second call never finished -- it should only have waited"
    assert overlapped == [False], (
        "a second tool call entered dispatch while the first was mid-transaction"
    )
    assert result.startswith("slow done")
    assert second_finished.is_set(), "the second call must run once the first one returns"
    # Both rows are here, each committed by its own call -- the point of the
    # lock is that neither commit belonged to the other.
    assert svc.be.epic_get("slow-epic") is not None
    assert svc.be.epic_get("quick-epic") is not None


def test_the_first_calls_rollback_cannot_take_the_second_calls_row(svc, registered):
    """The mirror of the backend measurement, at the level that fixes it.

    At the backend level this exact shape loses the second writer's row to the
    first one's rollback. Through dispatch it cannot happen, because the second
    call does not start until the first has finished unwinding.
    """
    inside = threading.Event()
    released = threading.Event()

    def failing_tool(service, args):
        try:
            with service.be.transaction():
                service.be.epic_add("doomed", "Rolled back by its own tool", None)
                inside.set()
                released.wait(timeout=1.0)
                raise RuntimeError("this tool fails")
        except RuntimeError:
            return "failed as designed"

    def writer_tool(service, args):
        released.set()
        service.be.epic_add("survivor", "Must outlive the other call", None)
        return "written"

    registered["test_failing"] = failing_tool
    registered["test_writer"] = writer_tool

    def run_writer():
        inside.wait(timeout=5.0)
        handlers.handle_tool(svc, "test_writer", {})

    t = threading.Thread(target=run_writer)
    t.start()
    handlers.handle_tool(svc, "test_failing", {})
    t.join(timeout=5.0)
    assert not t.is_alive()

    assert svc.be.epic_get("doomed") is None, "the failing tool's own write is gone"
    assert svc.be.epic_get("survivor") is not None, "the other call's write must survive"


def test_a_tool_that_dispatches_another_tool_does_not_deadlock(svc, registered):
    """Re-entrancy, held by a test rather than by hope.

    Nothing dispatches a tool from inside a tool today. A plain `Lock` would
    turn the day someone does into a silent hang instead of an error, which is
    why the dispatch lock is an `RLock`.
    """

    def inner_tool(service, args):
        service.be.epic_add("inner", "From the inner tool", None)
        return "inner done"

    def outer_tool(service, args):
        service.be.epic_add("outer", "From the outer tool", None)
        return "outer done + " + handlers.handle_tool(service, "test_inner", {})

    registered["test_inner"] = inner_tool
    registered["test_outer"] = outer_tool

    done = threading.Event()
    result: list[str] = []

    def run():
        result.append(handlers.handle_tool(svc, "test_outer", {}))
        done.set()

    t = threading.Thread(target=run)
    t.start()
    t.join(timeout=5.0)

    assert done.is_set(), "re-entering dispatch on one thread deadlocked"
    assert result == ["outer done + inner done"]
    assert svc.be.epic_get("inner") is not None
    assert svc.be.epic_get("outer") is not None
