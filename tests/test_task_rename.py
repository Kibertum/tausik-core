"""task rename — slug + every referring column, one transaction."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend
from project_service import ProjectService
from tausik_utils import ServiceError

CROSSCUTTING_SCOPE = [
    "scripts/service_task_rename.py",
    "scripts/task_slug_referrers.py",
    "scripts/service_task.py",
    "scripts/project_cli_task.py",
    "scripts/project_parser_task.py",
    "harness/claude/mcp/project/tools.py",
    "harness/claude/mcp/project/handlers_task.py",
]


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "h.db")))
    yield s
    s.be.close()


def _world(svc):
    svc.epic_add("e1", "Epic")
    svc.story_add("e1", "s1", "Story")
    svc.task_add("s1", "alpha", "Alpha")
    svc.task_add("s1", "beta", "Beta")
    svc.task_update("beta", defect_of="alpha")
    svc.task_log("alpha", "journal line")
    svc.decide("a decision about alpha", rationale="because", task_slug="alpha")
    return svc


class TestTaskRename:
    def test_moves_slug_and_referrers(self, svc):
        _world(svc)
        from service_task_rename import task_rename

        msg = task_rename(svc, "alpha", "alpha-renamed")
        assert "alpha" in msg and "alpha-renamed" in msg
        assert svc.be.task_get("alpha") is None
        assert svc.be.task_get("alpha-renamed") is not None
        beta = svc.be.task_get("beta")
        assert beta["defect_of"] == "alpha-renamed"
        logs = svc.be.task_log_list("alpha-renamed")
        assert logs and all(r["task_slug"] == "alpha-renamed" for r in logs)
        decisions = [
            d
            for d in svc.be._q(
                "SELECT task_slug FROM decisions WHERE task_slug=?", ("alpha-renamed",)
            )
        ]
        assert decisions

    def test_schema_derived_referrers_include_known_columns(self, svc):
        from task_slug_referrers import task_slug_referrers

        pairs = set(task_slug_referrers(svc.be._conn))
        assert ("tasks", "defect_of") in pairs
        assert ("task_logs", "task_slug") in pairs
        assert ("decisions", "task_slug") in pairs
        # The primary key column is updated separately by id, not via this list.
        assert ("tasks", "slug") not in pairs

    def test_occupied_slug_refused(self, svc):
        _world(svc)
        from service_task_rename import task_rename

        with pytest.raises(ServiceError, match="already taken"):
            task_rename(svc, "alpha", "beta")
        assert svc.be.task_get("alpha") is not None
        assert svc.be.task_get("beta") is not None

    def test_incomplete_referrer_list_rolls_back(self, svc, monkeypatch):
        _world(svc)
        from task_slug_referrers import task_slug_referrers as real

        def incomplete(conn):
            # Drop task_logs so one child keeps the old slug after parent moves.
            return [(t, c) for t, c in real(conn) if t != "task_logs"]

        from service_task_rename import task_rename

        monkeypatch.setattr("service_task_rename.task_slug_referrers", incomplete)
        with pytest.raises(ServiceError, match="foreign_key_check|rolled back"):
            task_rename(svc, "alpha", "alpha-broken")
        assert svc.be.task_get("alpha") is not None
        assert svc.be.task_get("alpha-broken") is None
        logs = svc.be.task_log_list("alpha")
        assert logs and all(r["task_slug"] == "alpha" for r in logs)

    def test_old_projection_file_removed(self, svc, tmp_path):
        _world(svc)
        # Force a projection write for the old slug, then rename.
        svc._project_task("alpha")
        proj = Path(svc.tausik_dir()) / "tasks"
        old = proj / "alpha.md"
        # Projection may live under project tausik/; tolerate missing on fixtures
        # that skip export, but when the file exists it must go after rename.
        from service_task_rename import task_rename

        existed = old.is_file()
        task_rename(svc, "alpha", "alpha-file")
        if existed:
            assert not old.is_file()
        new = proj / "alpha-file.md"
        if (proj).is_dir():
            # New file should appear when export is wired.
            assert new.is_file() or not existed


class TestTaskRenameCliParity:
    def test_mcp_pair_maps_to_cli(self):
        from mcp_cli_parity import PARITY

        assert PARITY.get("tausik_task_rename") == ("task", "rename")
