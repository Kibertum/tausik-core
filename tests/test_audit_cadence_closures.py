"""SENAR 9.5 audit cadence counts closures, not sessions (1.10, story E)."""

from __future__ import annotations

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from audit_cadence_helpers import make_audit_overdue  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402


@pytest.fixture
def svc(tmp_path, monkeypatch):
    monkeypatch.setenv("TAUSIK_DISABLE_SESSION_METRICS", "1")
    s = ProjectService(SQLiteBackend(str(tmp_path / "cad.db")))
    yield s
    s.be.close()


def test_the_threshold_of_closures_makes_the_audit_overdue(svc):
    make_audit_overdue(svc, closures=17)
    assert svc.audit_overdue_closures() == 17
    assert "17 tasks closed since the last audit" in svc.audit_check()


def test_under_the_threshold_it_is_not_overdue(svc):
    make_audit_overdue(svc, closures=16)
    assert svc.audit_overdue_closures() == 0 and svc.audit_check() is None


def test_a_mark_from_the_session_clock_is_still_read(svc):
    """NEGATIVE: an audit marked under the old clock (only last_audit_session)
    is read through that session's start — not reset to 'never audited'."""
    svc.session_start()
    sid = svc.be.session_current()["id"]
    svc.be.meta_set("last_audit_session", str(sid))
    assert "No audit has been performed" not in (svc.audit_check() or "")


def test_the_cadence_arrives_without_any_session(svc):
    """NEGATIVE: the old clock never arrived without sessions; this one does,
    and marking needs no session either."""
    make_audit_overdue(svc)
    assert svc.be.session_current() is None
    assert svc.audit_overdue_closures() >= 17
    assert "Audit marked" in svc.audit_mark()
    assert svc.audit_overdue_closures() == 0
