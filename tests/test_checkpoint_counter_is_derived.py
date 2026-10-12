"""The SENAR 9.3 checkpoint counter is derived from usage events (1.10, story E)."""

from __future__ import annotations

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.join(_ROOT, "harness", "claude", "mcp", "project"))

from checkpoint_signal import calls_since_checkpoint, checkpoint_advice, no_session_note  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402


@pytest.fixture
def svc(tmp_path, monkeypatch):
    monkeypatch.setenv("TAUSIK_DISABLE_SESSION_METRICS", "1")
    s = ProjectService(SQLiteBackend(str(tmp_path / "cp.db")))
    yield s
    s.be.close()


def _calls(svc, n: int) -> None:
    sid = svc.be.session_current()["id"]
    for _ in range(n):
        svc.be.usage_event_append(sid, None, 0, 0, 0, 0.0, 1, "", "posttool")


def test_the_count_is_the_ledger_since_the_last_handoff(svc):
    svc.session_start()
    _calls(svc, 12)
    assert calls_since_checkpoint(svc.be) == 12
    svc.session_handoff()
    _calls(svc, 5)
    assert calls_since_checkpoint(svc.be) == 5
    assert svc.be.meta_get("tool_call_count") is None  # nothing maintained


def test_advice_fires_once_per_ten_call_bucket(svc):
    """NEGATIVE: the advice does not repeat on every call."""
    svc.session_start()
    _calls(svc, 41)
    assert "41 tool calls" in checkpoint_advice(svc.be)
    assert checkpoint_advice(svc.be) == ""
    _calls(svc, 9)
    assert "50 tool calls" in checkpoint_advice(svc.be)


def test_without_a_session_it_says_so_aloud(svc):
    """NEGATIVE: no session is named as unmeasured, not shown as zero."""
    assert calls_since_checkpoint(svc.be) is None
    assert checkpoint_advice(svc.be) == ""
    assert "no open session" in no_session_note(svc.be)
