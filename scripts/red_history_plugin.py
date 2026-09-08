"""The pytest hooks that record red history, as a PLUGIN rather than a conftest.

WHY A SEPARATE MODULE, decided by a failing test rather than by taste. The hooks
first lived in `tests/conftest.py`, and the end-to-end test — a nested pytest run
over one deliberately failing test — could not exercise them: that conftest
imports a dozen project modules and does not load outside this repository, so
the nested run died at collection with `ModuleNotFoundError` and recorded
nothing. Copying the hooks into the fixture instead would have tested a copy,
which is the shape that lets the real one rot unnoticed.

As a plugin the same code is loadable with `-p red_history_plugin` anywhere, so
the test exercises the module the suite actually runs. `tests/conftest.py`
imports these names, and pytest treats hooks found in the conftest namespace as
its own — registration stays where a reader expects it, the behaviour lives
where it can be tested.

ONLY FAILURES ARE COLLECTED, AND ONLY THE CALL PHASE. A green outcome carries no
information; an error during setup says something about a fixture rather than
about the test's ability to fail. Nothing touches the database during the run:
node ids accumulate in memory and are written once, in one transaction, at
session end. That is the lesson from session #237, where a per-event observer
took the suite from 14.5s to a five-minute timeout before it was cached.
"""

from __future__ import annotations

import os

__all__ = ["RED_NODES", "pytest_runtest_logreport", "pytest_sessionfinish"]

#: Node ids seen failing in this process. Under xdist each worker keeps its own
#: and writes its own few rows; the upsert is idempotent per node.
RED_NODES: list[str] = []


def pytest_runtest_logreport(report) -> None:
    """Collect failing node ids. No I/O here — this runs for every test."""
    if getattr(report, "when", None) == "call" and getattr(report, "failed", False):
        RED_NODES.append(report.nodeid)


def _project_root(session) -> str:
    """The tree whose `.tausik/tausik.db` this run belongs to.

    `rootpath` rather than this file's location: the plugin may be loaded from
    another checkout — that is the point of it being a plugin — and the history
    belongs to the project under test, not to the project that lent the code.
    """
    root = getattr(getattr(session, "config", None), "rootpath", None)
    return str(root) if root else os.getcwd()


def pytest_sessionfinish(session, exitstatus) -> None:
    """One write, at the end, and never fatal.

    Wrapped whole: a lost observation is a weaker history, a crashed run is a
    broken suite, and the second is much worse.
    """
    if not RED_NODES:
        return
    try:
        import red_history

        db = os.path.join(_project_root(session), ".tausik", "tausik.db")
        red_history.record_reds(db, RED_NODES)
    except Exception:  # noqa: BLE001 — recording must never break a run
        pass
    finally:
        RED_NODES.clear()
