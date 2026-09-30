"""Any past session's handoff is readable, not only the newest (github#137).

Measured in session #181: `session last-handoff` returned only the freshest
handoff and nothing read an older one, so a table recorded in session #179's
handoff had to be recovered from the IDE transcript — outside the framework.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.join(_ROOT, "harness", "claude", "mcp", "project"))

from project_backend import SQLiteBackend  # noqa: E402
from project_parser import build_parser  # noqa: E402
from project_service import ProjectService  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402


@pytest.fixture
def svc(tmp_path, monkeypatch):
    monkeypatch.setenv("TAUSIK_DISABLE_SESSION_METRICS", "1")
    s = ProjectService(SQLiteBackend(str(tmp_path / "ho.db")))
    s.session_start()
    s.session_handoff({"next_steps": ["the table from the first session"]})
    s.session_end()
    s.session_start()
    s.session_handoff({"next_steps": ["second"]})
    yield s
    s.be.close()


def test_the_handoff_of_an_earlier_session_is_readable(svc):
    assert svc.session_last_handoff(1)["next_steps"] == ["the table from the first session"]
    assert svc.session_last_handoff()["next_steps"] == ["second"]


def test_a_missing_session_is_named_not_answered_with_another(svc):
    """NEGATIVE: no fallback onto the live handoff."""
    with pytest.raises(ServiceError, match="does not exist"):
        svc.session_last_handoff(99)


def test_a_session_without_a_handoff_says_so(svc):
    """NEGATIVE: an empty answer and a missing session are different refusals."""
    svc.session_end()
    svc.session_start()
    with pytest.raises(ServiceError, match="no handoff recorded"):
        svc.session_last_handoff(3)


def test_the_cli_and_the_mcp_tool_take_the_session_number(svc):
    args = build_parser().parse_args(["session", "last-handoff", "--session", "1"])
    assert args.session == 1
    from handlers_session import _do_session_last_handoff

    out = _do_session_last_handoff(svc, {"session_id": 1})
    assert json.loads(out)["next_steps"] == ["the table from the first session"]
