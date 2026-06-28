"""v15-failclosed-gate-audit: Rule 7 root cause warn -> hard gate.

Defect tasks (defect_of set) must document a root cause before closing;
config task_done.root_cause_hard=false restores the legacy warning.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402


@pytest.fixture
def svc(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TAUSIK_QUIET", "1")
    s = ProjectService(SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db")))
    s.task_add(None, "parent", "Parent task")
    s.task_add(None, "fix", "Defect fix", None, None, None, None, "parent")
    s.task_update(
        "fix",
        goal="g",
        acceptance_criteria="1. ok\n2. errors on bad input",
        scope="x.py",
    )
    s.task_start("fix")
    return s


def _close(svc):
    # no_knowledge=False: Rule 8 refuses --no-knowledge for defect tasks
    return svc.task_done("fix", None, True, False, evidence="AC verified: 1. OK 2. OK")


class TestRootCauseHardGate:
    def test_defect_without_root_cause_blocked(self, svc):
        with pytest.raises(ServiceError, match="root cause"):
            _close(svc)
        assert svc.be.task_get("fix")["status"] == "active"

    def test_defect_with_root_cause_closes(self, svc):
        svc.task_log("fix", "Root cause: off-by-one in pagination")
        assert "completed" in _close(svc)

    def test_russian_keyword_accepted(self, svc):
        svc.task_log("fix", "Причина: гонка при инициализации кэша")
        assert "completed" in _close(svc)

    def test_non_defect_task_unaffected(self, svc):
        svc.task_add(None, "plain", "Plain task")
        svc.task_update(
            "plain",
            goal="g",
            acceptance_criteria="1. ok\n2. errors on bad input",
            scope="x.py",
        )
        svc.task_start("plain")
        msg = svc.task_done("plain", None, True, True, evidence="AC verified: 1. OK 2. OK")
        assert "completed" in msg

    def test_opt_out_downgrades_to_warning(self, svc, monkeypatch):
        import service_task_done

        monkeypatch.setattr(service_task_done, "_root_cause_hard_enabled", lambda: False)
        msg = _close(svc)
        assert "completed" in msg
        assert "root cause" in msg  # warning still surfaced

    def test_remediation_in_error(self, svc):
        with pytest.raises(ServiceError, match="task log"):
            _close(svc)
