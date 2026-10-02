"""Tests for `tausik task delegate` — orchestrator-worker delegation (v15-ow-delegate-cli)."""

from __future__ import annotations

import os
import sys
import json
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend
from project_service import ProjectService, ServiceError


@pytest.fixture
def svc(tmp_path):
    be = SQLiteBackend(str(tmp_path / "t.db"))
    s = ProjectService(be)
    s.epic_add("v1", "V1")
    s.story_add("v1", "setup", "Setup")
    yield s
    be.close()


def _task(svc, slug, complexity):
    svc.task_add("setup", slug, slug, complexity=complexity, role="developer")


class TestTaskDelegate:
    def test_medium_records_delegation(self, svc):
        _task(svc, "feat-x", "medium")
        msg = svc.task_delegate("feat-x")
        assert "delegated" in msg.lower()
        rec = svc.task_delegation("feat-x")
        assert rec is not None
        assert rec["model"]  # a recommended model id was recorded
        assert "delegated_at" in rec

    def test_simple_is_delegable(self, svc):
        _task(svc, "feat-s", "simple")
        assert svc.task_delegation("feat-s") is None
        svc.task_delegate("feat-s")
        assert svc.task_delegation("feat-s") is not None

    def test_complex_refused(self, svc):
        _task(svc, "feat-c", "complex")
        with pytest.raises(ServiceError, match="complex"):
            svc.task_delegate("feat-c")
        assert svc.task_delegation("feat-c") is None  # nothing recorded

    def test_unknown_task_refused(self, svc):
        with pytest.raises(ServiceError, match="not found"):
            svc.task_delegate("nope")

    def test_done_task_refused(self, svc):
        _task(svc, "feat-d", "simple")
        svc.be.task_update("feat-d", status="done")
        with pytest.raises(ServiceError, match="done"):
            svc.task_delegate("feat-d")

    def test_idempotent_redelegate(self, svc):
        _task(svc, "feat-i", "medium")
        svc.task_delegate("feat-i")
        msg2 = svc.task_delegate("feat-i")
        assert "already delegated" in msg2.lower() and "no-op" in msg2.lower()

    def test_undelegate_clears(self, svc):
        _task(svc, "feat-u", "medium")
        svc.task_delegate("feat-u")
        assert svc.task_delegation("feat-u") is not None
        svc.task_undelegate("feat-u")
        assert svc.task_delegation("feat-u") is None

    def test_undelegate_noop_when_not_delegated(self, svc):
        _task(svc, "feat-n", "medium")
        assert "not delegated" in svc.task_undelegate("feat-n").lower()

    def test_undelegate_removes_meta_row(self, svc):
        _task(svc, "feat-r", "medium")
        svc.task_delegate("feat-r")
        svc.task_undelegate("feat-r")
        # No tombstone: the meta key is gone, not left as an empty string.
        assert svc.be.meta_get("delegation:feat-r") is None

    def test_task_delete_clears_delegation_meta(self, svc):
        _task(svc, "feat-del", "medium")
        svc.task_delegate("feat-del")
        svc.task_summary_back("feat-del", "done")
        svc.task_delete("feat-del")
        # No stale state a reused slug could inherit.
        assert svc.be.meta_get("delegation:feat-del") is None
        assert svc.be.meta_get("worker_summary:feat-del") is None

    def test_idempotent_message_no_session_shows_unknown(self, svc):
        # Fixture has no active session → parent_session is None; the no-op
        # message must read '#unknown', not the literal '#None'.
        _task(svc, "feat-q", "medium")
        svc.task_delegate("feat-q")
        msg = svc.task_delegate("feat-q")
        assert "#unknown" in msg and "#None" not in msg

    def test_unverified_host_is_advisory_and_never_delegated(self, svc, monkeypatch):
        _task(svc, "feat-kilo", "simple")
        monkeypatch.setattr(
            svc,
            "_recommended_route",
            lambda complexity: {
                "model": "glm-4.5-air",
                "display": "GLM-4.5-Air",
                "family": "glm",
                "host": "kilo",
                "reasoning_effort": "low",
                "speed_mode": "standard",
                "capability": "advisory",
            },
        )
        with pytest.raises(ServiceError, match="advisory"):
            svc.task_delegate("feat-kilo")
        assert svc.task_delegation("feat-kilo") is None

    def test_refuses_worker_when_startup_exceeds_remaining_work(self, svc, monkeypatch):
        _task(svc, "feat-short", "simple")
        monkeypatch.setattr(
            svc,
            "_recommended_route",
            lambda complexity: {
                "model": "gpt-5.6-terra",
                "display": "GPT-5.6 Terra",
                "family": "openai",
                "host": "codex",
                "reasoning_effort": "low",
                "speed_mode": "standard",
                "capability": "spawn_subagent",
            },
        )
        with pytest.raises(ServiceError, match="startup work 3 exceeds bounded remaining work 2"):
            svc.task_delegate("feat-short", startup_work=3, remaining_work=2)
        assert svc.task_delegation("feat-short") is None

    def test_allows_worker_when_startup_fits_remaining_work(self, svc, monkeypatch):
        _task(svc, "feat-fit", "simple")
        monkeypatch.setattr(
            svc,
            "_recommended_route",
            lambda complexity: {
                "model": "gpt-5.6-terra",
                "display": "GPT-5.6 Terra",
                "family": "openai",
                "host": "codex",
                "reasoning_effort": "medium",
                "speed_mode": "standard",
                "capability": "spawn_subagent",
            },
        )
        svc.task_delegate("feat-fit", startup_work=2, remaining_work=3)
        assert svc.task_delegation("feat-fit")["work_estimate"] == {
            "startup_work": 2,
            "remaining_work": 3,
        }

    @pytest.mark.parametrize(
        ("startup_work", "remaining_work", "message"),
        [(2, None, "require both"), ("two", 3, "non-negative integers")],
    )
    def test_rejects_incomplete_or_malformed_work_estimates(
        self, svc, startup_work, remaining_work, message
    ):
        _task(svc, "feat-estimate", "simple")
        with pytest.raises(ServiceError, match=message):
            svc.task_delegate(
                "feat-estimate", startup_work=startup_work, remaining_work=remaining_work
            )

    def test_selected_route_is_not_applied_until_worker_starts(self, svc, monkeypatch, tmp_path):
        store = Path(svc.tausik_dir())
        monkeypatch.setattr(
            svc,
            "_recommended_route",
            lambda complexity: {
                "model": "gpt-5.6-terra",
                "display": "GPT-5.6 Terra",
                "family": "openai",
                "host": "codex",
                "reasoning_effort": "low",
                "speed_mode": "standard",
                "capability": "spawn_subagent",
            },
        )
        _task(svc, "feat-codex", "simple")
        svc.task_delegate("feat-codex")
        assert svc.task_delegation("feat-codex")["applied"] is False

        # A failed/abandoned spawn never reaches task_start, so it remains
        # selected rather than being counted as applied.
        rows = [
            json.loads(line)
            for line in (store / "routing_adherence.jsonl").read_text().splitlines()
        ]
        assert [row["outcome"] for row in rows] == ["selected"]

        svc.be.task_update("feat-codex", status="active")
        notice = svc.task_start("feat-codex")
        assert notice and "Worker mode" in notice
        assert svc.task_delegation("feat-codex")["applied"] is True
        rows = [
            json.loads(line)
            for line in (store / "routing_adherence.jsonl").read_text().splitlines()
        ]
        assert [row["outcome"] for row in rows] == ["selected", "applied"]
        assert svc.task_delegation("feat-codex")["max_delegation_depth"] == 1
        _task(svc, "feat-nested", "simple")
        with pytest.raises(ServiceError, match="max depth 1"):
            svc.task_delegate("feat-nested")
        assert svc.task_delegation("feat-nested") is None

    def test_task_start_records_current_codex_route_beside_its_temp_backend(
        self, tmp_path, monkeypatch
    ):
        owned = tmp_path / "owned" / ".tausik"
        owned.mkdir(parents=True)
        foreign = tmp_path / "foreign" / ".tausik"
        foreign.mkdir(parents=True)
        isolated = ProjectService(SQLiteBackend(str(owned / "tausik.db")))
        try:
            isolated.epic_add("v1", "V1")
            isolated.story_add("v1", "setup", "Setup")
            _task(isolated, "host-route", "medium")
            isolated.be.task_update(
                "host-route",
                goal="record the current host route",
                acceptance_criteria="1. records route. negative: does not use cwd",
                scope="tests/test_ow_delegate.py",
                rollback_plan="git revert",
            )
            monkeypatch.chdir(foreign.parent)
            monkeypatch.setattr("skill_profile_detect.detect_ide", lambda: "codex")
            monkeypatch.setattr(
                "agent_model_source.resolve",
                lambda **_kwargs: {"model_id": "gpt-5.6-sol", "source": "test"},
            )
            isolated.task_start("host-route")
            path = Path(isolated.tausik_dir()) / "routing_adherence.jsonl"
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            route = next(row for row in rows if row["outcome"] == "recommended")
            assert route["host"] == "codex"
            assert route["model"] == "gpt-5.6-terra"
            assert route["route_reason"] == "bounded simple/medium worker work defaults to Terra"
            assert not (foreign / "routing_adherence.jsonl").exists()
        finally:
            isolated.be.close()
