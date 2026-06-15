"""v16r-model-pinning: per-task model pinning + mid-task mismatch + metrics.

Covers the v33 columns, started/done-model recording, the usage_events↔task
model link, mismatch detection, and the by-model metrics rollup.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from model_pinning import (  # noqa: E402
    format_model_usage_section,
    model_done_updates,
    session_model,
)
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from tausik_utils import utcnow_iso  # noqa: E402


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "mp.db")))
    s.epic_add("e", "Epic")
    s.story_add("e", "s", "Story")
    yield s
    s.be.close()


def _seed_task(svc, slug: str = "mp1") -> None:
    svc.task_add("s", slug, "T", role="developer", goal="g")
    svc.be.task_update(slug, acceptance_criteria="Returns 400 on invalid input.")


def _add_usage(
    svc, sid: int, slug: str | None, model: str | None, source: str = "posttool"
) -> None:
    svc.be._ins(
        "INSERT INTO usage_events(session_id, task_slug, model_id, tokens_input, "
        "tokens_output, tokens_total, cost_usd, tool_calls, source, recorded_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,?)",
        (sid, slug, model, 10, 5, 15, 0.01, 1, source, utcnow_iso()),
    )


# === schema / migration ===


def test_v33_columns_present(svc):
    cols = {r["name"] for r in svc.be._q("PRAGMA table_info(tasks)")}
    assert {
        "started_model_id",
        "started_model_version",
        "done_model_id",
        "done_model_version",
        "model_mismatch",
    } <= cols


# === AC1: started/done model pinning ===


def test_session_model_helper(svc, monkeypatch):
    monkeypatch.setenv("TAUSIK_AGENT_MODEL", "claude-opus-4-8")
    monkeypatch.setenv("TAUSIK_AGENT_MODEL_VERSION", "20260601")
    svc.be.session_start()
    assert session_model(svc.be) == ("claude-opus-4-8", "20260601")


def test_started_model_pinned_on_task_start(svc, monkeypatch):
    monkeypatch.setenv("TAUSIK_AGENT_MODEL", "claude-opus-4-8")
    monkeypatch.delenv("TAUSIK_AGENT_MODEL_VERSION", raising=False)
    svc.be.session_start()
    _seed_task(svc)
    svc.task_start("mp1", _internal_force=True)
    task = svc.task_show("mp1")
    assert task["started_model_id"] == "claude-opus-4-8"


# === AC2: mismatch detection + usage↔task link ===


def test_task_model_ids_distinct(svc, monkeypatch):
    monkeypatch.setenv("TAUSIK_AGENT_MODEL", "claude-opus-4-8")
    sid = svc.be.session_start()
    _seed_task(svc)
    _add_usage(svc, sid, "mp1", "claude-opus-4-8")
    _add_usage(svc, sid, "mp1", "claude-sonnet-4-6")
    _add_usage(svc, sid, "mp1", "claude-opus-4-8")
    assert svc.be.task_model_ids("mp1") == ["claude-opus-4-8", "claude-sonnet-4-6"]


def test_done_updates_no_mismatch_single_model(svc, monkeypatch):
    monkeypatch.setenv("TAUSIK_AGENT_MODEL", "claude-opus-4-8")
    sid = svc.be.session_start()
    _seed_task(svc)
    svc.task_start("mp1", _internal_force=True)
    _add_usage(svc, sid, "mp1", "claude-opus-4-8")
    task = svc.task_show("mp1")
    assert task["started_model_id"] == "claude-opus-4-8"  # pinned at start
    updates, msg = model_done_updates(svc.be, task)
    assert updates["model_mismatch"] == 0
    assert msg is None
    assert updates["done_model_id"] == "claude-opus-4-8"


def test_done_updates_flags_mismatch(svc, monkeypatch):
    """NEGATIVE: a task whose usage spans two models is flagged, and the
    message names both."""
    monkeypatch.setenv("TAUSIK_AGENT_MODEL", "claude-opus-4-8")
    sid = svc.be.session_start()
    _seed_task(svc)
    svc.task_start("mp1", _internal_force=True)
    _add_usage(svc, sid, "mp1", "claude-opus-4-8")
    _add_usage(svc, sid, "mp1", "claude-sonnet-4-6")
    task = svc.task_show("mp1")
    updates, msg = model_done_updates(svc.be, task)
    assert updates["model_mismatch"] == 1
    assert msg and "claude-opus-4-8" in msg and "claude-sonnet-4-6" in msg


def test_task_done_persists_mismatch_in_evidence(svc, monkeypatch):
    """Integration: task_done flags the mismatch and writes it to notes."""
    monkeypatch.setenv("TAUSIK_AGENT_MODEL", "claude-opus-4-8")
    sid = svc.be.session_start()
    _seed_task(svc)
    svc.task_start("mp1", _internal_force=True)
    _add_usage(svc, sid, "mp1", "claude-opus-4-8")
    _add_usage(svc, sid, "mp1", "claude-sonnet-4-6")
    # Pre-log AC + checklist so QG-2 doesn't block the close.
    svc.task_log("mp1", "AC verified: 1. covered ✓")
    svc.task_log("mp1", "Checklist: scope ok, tests cover edge case, no security surface.")
    svc.task_done("mp1", ac_verified=True, no_knowledge=True)
    task = svc.task_show("mp1")
    assert task["model_mismatch"] == 1
    assert "mismatch" in (task.get("notes") or "").lower()


# === AC3: metrics by model ===


def test_rollup_by_model_excludes_session_record(svc, monkeypatch):
    monkeypatch.setenv("TAUSIK_AGENT_MODEL", "claude-opus-4-8")
    sid = svc.be.session_start()
    _seed_task(svc)
    _add_usage(svc, sid, "mp1", "claude-opus-4-8", source="posttool")
    _add_usage(svc, sid, "mp1", "claude-sonnet-4-6", source="posttool")
    # session_record aggregate must NOT be counted in the by-model rollup.
    _add_usage(svc, sid, None, "claude-opus-4-8", source="session_record")
    rollup = {r["model_id"]: r for r in svc.be.usage_events_cost_rollup_by_model()}
    assert set(rollup) == {"claude-opus-4-8", "claude-sonnet-4-6"}
    assert rollup["claude-opus-4-8"]["event_count"] == 1  # session_record excluded


def test_format_model_usage_section():
    assert format_model_usage_section([]) == []
    rows = [{"model_id": "claude-opus-4-8", "event_count": 3, "tokens_total": 100, "cost_usd": 1.5}]
    out = format_model_usage_section(rows)
    assert any("LLM Usage by Model" in line for line in out)
    assert any("claude-opus-4-8" in line for line in out)
