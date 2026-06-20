"""qa-task-update-notes-guard: task_update(notes=…) must not silently clobber
the append-only journal.

`notes` is crash-safe history written by `task log`. A blind
task_update(notes=…) used to overwrite the whole blob (memory #160 footgun).
The service layer now refuses to overwrite a NON-empty journal unless the
caller explicitly opts in with notes_overwrite=True.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService, ServiceError  # noqa: E402


@pytest.fixture
def svc(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TAUSIK_QUIET", "1")
    s = ProjectService(SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db")))
    s.task_add(None, "t1", "Task one")
    return s


def _notes(svc, slug):
    return svc.be.task_get(slug).get("notes") or ""


class TestNotesOverwriteGuard:
    def test_overwrite_nonempty_journal_refused(self, svc):
        # AC-1: a real journal exists, blind notes= must be refused and preserve it.
        svc.task_log("t1", "step one")
        svc.task_log("t1", "step two")
        before = _notes(svc, "t1")
        with pytest.raises(ServiceError) as ei:
            svc.task_update("t1", notes="clobber")
        assert "OVERWRITE" in str(ei.value)
        assert "task log" in str(ei.value)
        # journal untouched
        assert _notes(svc, "t1") == before
        assert "step one" in _notes(svc, "t1")

    def test_overwrite_allowed_with_flag(self, svc):
        # AC-2: explicit opt-in replaces the journal; flag never reaches backend.
        svc.task_log("t1", "step one")
        msg = svc.task_update("t1", notes="intentional replace", notes_overwrite=True)
        assert "updated" in msg
        assert _notes(svc, "t1") == "intentional replace"

    def test_empty_string_notes_on_nonempty_journal_refused(self, svc):
        # Setting notes='' (clearing) against a real journal is still a clobber.
        svc.task_log("t1", "history line")
        with pytest.raises(ServiceError):
            svc.task_update("t1", notes="")
        assert "history line" in _notes(svc, "t1")

    def test_whitespace_notes_on_nonempty_journal_refused(self, svc):
        svc.task_log("t1", "history line")
        with pytest.raises(ServiceError):
            svc.task_update("t1", notes="   ")
        assert "history line" in _notes(svc, "t1")

    def test_overwrite_flag_without_notes_is_noop(self, svc):
        # notes_overwrite with no notes key: guard pops the flag and does nothing.
        svc.task_log("t1", "history line")
        svc.task_update("t1", notes_overwrite=True)  # no notes -> no clobber
        assert "history line" in _notes(svc, "t1")

    def test_notes_on_empty_journal_allowed(self, svc):
        # AC-3: no false positive — first note via update on an empty journal is fine.
        assert _notes(svc, "t1") == ""
        svc.task_update("t1", notes="first note")
        assert _notes(svc, "t1") == "first note"

    def test_task_log_append_unaffected(self, svc):
        # Negative: the append path is never blocked by the guard.
        svc.task_update("t1", notes="seed")  # empty -> allowed
        svc.task_log("t1", "appended")
        body = _notes(svc, "t1")
        assert "seed" in body and "appended" in body

    def test_other_fields_unaffected(self, svc):
        # Negative: guard only touches notes; updating goal with a live journal is fine.
        svc.task_log("t1", "history")
        svc.task_update("t1", goal="new goal")
        row = svc.be.task_get("t1")
        assert row["goal"] == "new goal"
        assert "history" in (row.get("notes") or "")
