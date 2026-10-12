"""One live handoff holder, with a recorded supersedes edge (github#126).

Since schema v63 two host sessions can be open at once. The live handoff used
to be the one on the highest session id; when the OLDER session wrote last, the
answer to "where is the current handoff" was the stale one.
"""

from __future__ import annotations

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402


@pytest.fixture
def svc(tmp_path, monkeypatch):
    monkeypatch.setenv("TAUSIK_DISABLE_SESSION_METRICS", "1")
    s = ProjectService(SQLiteBackend(str(tmp_path / "slot.db")))
    yield s
    s.be.close()


def _write_as(svc, host: str, note: str) -> None:
    """Write a handoff from inside one host session (the service picks the
    newest open one, so close-reopen order is used to aim it)."""
    sid = svc.be.session_current(host)["id"]
    row = svc.be.session_last_handoff(sid)
    assert row is not None
    svc.session_handoff({"next_steps": [note]})


def test_the_handoff_written_last_is_live_even_on_an_older_session(svc, monkeypatch):
    svc.session_start("host-A")  # id 1
    svc.session_start("host-B")  # id 2, newest open
    svc.session_handoff({"next_steps": ["B wrote first"]})  # lands on #2
    svc.session_end(host_session_id="host-B")
    # Only A is open now; its later write must become the live holder even
    # though its id is lower.
    svc.session_handoff({"next_steps": ["A wrote last"]})
    live = svc.session_last_handoff()
    assert live["next_steps"] == ["A wrote last"]
    assert live["supersedes"] == 2


def test_the_previous_holder_stays_reachable(svc):
    """NEGATIVE: taking over is a transition, not a loss."""
    svc.session_start()
    svc.session_handoff({"next_steps": ["first"]})
    svc.session_end()
    svc.session_start()
    svc.session_handoff({"next_steps": ["second"]})
    assert svc.session_last_handoff(1)["next_steps"] == ["first"]
    assert svc.session_last_handoff()["supersedes"] == 1


def test_rewriting_in_the_same_session_does_not_supersede_itself(svc):
    """NEGATIVE: a second write of the same session is an update, not an edge to itself."""
    svc.session_start()
    svc.session_handoff({"next_steps": ["v1"]})
    svc.session_handoff({"next_steps": ["v2"]})
    live = svc.session_last_handoff()
    assert live["next_steps"] == ["v2"] and "supersedes" not in live
    assert "written_at" in live
