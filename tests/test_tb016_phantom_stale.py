"""TB-016: green verify then task done must not STALE on a phantom next run.

Dogfood (bugs.txt 2026-11-21): verify #93 PASS, immediate close named #94 as
STALE evidence. #94 was the cheap task-done gate record written BEFORE
Verify-First ran. Two fixes: last_run_kind only reads trigger=verify, and
_run_quality_gates_report redeems Verify-First before recording task-done.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend
from project_service import ProjectService

_SCOPE = ["scripts/x.py"]


@pytest.fixture
def svc(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "x.py").write_text("# product\n", encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text("## Unreleased\n- tb016\n", encoding="utf-8")
    be = SQLiteBackend(str(tmp_path / "t.db"))
    return ProjectService(be)


@pytest.fixture
def task_ready(svc):
    svc.epic_add("e", "E")
    svc.story_add("e", "s", "S")
    svc.task_add("s", "t", "TB-016", goal="Close after green verify", role="developer")
    svc.task_update(
        "t",
        acceptance_criteria=(
            "1. green verify then done closes\n"
            "2. STALE names the green verify, not a phantom\n"
            "Negative: edit between verify and done still STALE"
        ),
        relevant_files=json.dumps(_SCOPE),
    )
    svc.task_start("t")
    svc.task_log("t", "AC verified: green close path exercised")
    return svc


def _stub_verify_gates(monkeypatch):
    from project_config import get_gates_for_trigger as real

    def fake(trigger, cfg=None):
        if trigger == "verify":
            return [
                {
                    "name": "pytest",
                    "command": "true",
                    "trigger": ["verify"],
                    "severity": "block",
                }
            ]
        return real(trigger, cfg)

    monkeypatch.setattr(
        "project_config.load_config",
        lambda *a, **k: {"task_done": {"auto_verify": False}},
    )
    monkeypatch.setattr("project_config.get_gates_for_trigger", fake)


def _record_green_verify(svc, files):
    import service_verification as sv
    from verify_run_descriptor import VerificationRunDescriptor

    coverage_hash = sv.compute_files_hash(files)
    descriptor = VerificationRunDescriptor.create(
        trigger="verify",
        files=files,
        gate_signature=sv.resolve_gate_signature("verify"),
        replayable=True,
        presentable_once=False,
    )
    return sv.record_run(
        svc.be._conn,
        task_slug="t",
        scope="standard",
        command=sv._build_cache_command("verify", files),
        exit_code=0,
        summary="pytest=PASS",
        files_hash=coverage_hash,
        duration_ms=1,
        descriptor=descriptor,
    )


@pytest.mark.verify_first
def test_close_after_green_verify_survives_task_done_gate_touch(task_ready, monkeypatch, tmp_path):
    """Cheap task-done gates may touch coverage AFTER Verify-First; close still green."""
    _stub_verify_gates(monkeypatch)
    green_id = _record_green_verify(task_ready, _SCOPE)

    order: list[str] = []
    real_post = task_ready._run_post_scope_gates

    def tracking_post(*args, **kwargs):
        order.append("verify-first")
        return real_post(*args, **kwargs)

    monkeypatch.setattr(task_ready, "_run_post_scope_gates", tracking_post)

    cheap = [
        {
            "name": "filesize",
            "passed": True,
            "skipped": False,
            "severity": "block",
            "output": "ok",
        }
    ]

    def dirtying_gates(*_a, **_k):
        order.append("task-done-gates")
        # Mutate AFTER Verify-First — the old order would have made this STALE.
        Path("scripts/x.py").write_text("# product\n# touched by task-done\n", encoding="utf-8")
        return True, cheap

    with patch.dict(
        "sys.modules",
        {"gate_runner": MagicMock(run_gates=dirtying_gates)},
    ):
        msg = task_ready.task_done("t", ac_verified=True, no_changelog=True)
    assert order[:2] == ["verify-first", "task-done-gates"], order
    assert "completed" in msg or "done" in msg.lower()
    rows = list(
        task_ready.be._conn.execute(
            "SELECT id, run_trigger FROM verification_runs WHERE task_slug='t' ORDER BY id"
        )
    )
    assert any(int(r[0]) == int(green_id) and r[1] == "verify" for r in rows)
    assert any(r[1] == "task-done" and int(r[0]) > int(green_id) for r in rows)


@pytest.mark.verify_first
def test_honest_edit_between_verify_and_done_still_stales_on_green(task_ready, monkeypatch):
    """Negative: a real product edit before close STALE-names the green verify id."""
    _stub_verify_gates(monkeypatch)
    green_id = _record_green_verify(task_ready, _SCOPE)
    Path("scripts/x.py").write_text("# product\n# agent edit\n", encoding="utf-8")

    with patch.dict(
        "sys.modules",
        {"gate_runner": MagicMock(run_gates=MagicMock(return_value=(True, [])))},
    ):
        report = task_ready._run_quality_gates_report(
            "t", _SCOPE, trigger="task-done", no_changelog=True
        )
    assert report["passed"] is False
    text = " ".join(f.get("output", "") for f in report["blocking_failures"])
    assert "STALE" in text
    assert f"#{green_id}" in text
    # Must not claim a later task-done row as the verify subject.
    later = task_ready.be._conn.execute(
        "SELECT id FROM verification_runs WHERE task_slug='t' AND run_trigger='task-done' "
        "ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if later:
        assert f"#{later[0]}" not in text
