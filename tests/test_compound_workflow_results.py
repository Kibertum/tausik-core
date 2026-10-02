"""Compound workflow results remove dependent turns without weakening state."""

from __future__ import annotations

import json

from project_backend import SQLiteBackend
from project_service import ProjectService
from task_start_result import start_with_context


def _service(tmp_path):
    svc = ProjectService(SQLiteBackend(str(tmp_path / "compound.db")))
    svc.epic_add("e", "E")
    svc.story_add("e", "s", "S")
    svc.task_add("s", "work", "Work", complexity="medium")
    svc.task_update(
        "work",
        goal="ship one bounded result",
        acceptance_criteria="AC-1 context is returned. Negative: QG-0 still refuses omissions.",
        scope_paths=["scripts/a.py"],
        relevant_files=json.dumps(["scripts/a.py"]),
        rollback_plan="git revert",
    )
    return svc


def test_start_with_context_returns_active_contract_in_one_result(tmp_path):
    svc = _service(tmp_path)
    try:
        result = start_with_context(svc, "work")
        assert result["ok"] is True
        assert result["started"] is True
        assert result["context"]["required"]["status"] == "active"
        assert result["context"]["required"]["goal"] == "ship one bounded result"
        assert "Relevant memory" not in result["start"]
    finally:
        svc.be.close()


def test_context_failure_reports_committed_partial_state(tmp_path, monkeypatch):
    svc = _service(tmp_path)
    monkeypatch.setattr(
        "task_start_result.build_task_context_package",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("projection failed")),
    )
    try:
        result = start_with_context(svc, "work")
        assert result["ok"] is False
        assert result["started"] is True
        assert svc.task_show("work")["status"] == "active"
        assert result["context"]["error"] == "RuntimeError"
        assert result["context"]["recovery"].endswith("task show work --package")
    finally:
        svc.be.close()
