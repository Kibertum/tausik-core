"""Host-context lifecycle policy: real thread identity, ceilings and degradation."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import service_host_context as policy
from project_backend import SQLiteBackend
from project_service import ProjectService
from tausik_utils import ServiceError


@pytest.fixture
def svc(tmp_path):
    service = ProjectService(SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db")))
    yield service
    service.be.close()


def measured(responses=1, input_tokens=100, context_tokens=50):
    return {
        "availability": "native",
        "responses": responses,
        "input_tokens": input_tokens,
        "context_tokens": context_tokens,
    }


def test_same_thread_reopen_is_not_fresh_but_a_new_thread_is(svc, monkeypatch):
    monkeypatch.setattr(policy, "load_config", lambda _path: {})
    first = policy.open_session(svc, host="codex", thread_id="thread-a", usage=measured())
    reopened = policy.open_session(svc, host="codex", thread_id="thread-a", usage=measured())
    another = policy.open_session(svc, host="codex", thread_id="thread-b", usage=measured())

    assert first["host_context"]["fresh_context"] is True
    assert reopened["host_context"]["reopened"] is True
    assert reopened["host_context"]["fresh_context"] is False
    assert reopened["session"]["id"] == first["session"]["id"]
    assert another["host_context"]["fresh_context"] is True
    assert another["session"]["id"] != first["session"]["id"]


def test_advisory_saves_one_checkpoint_and_returns_a_new_window_prompt(svc, monkeypatch):
    monkeypatch.setattr(policy, "load_config", lambda _path: {})
    usage = measured(responses=24)
    result = policy.open_session(svc, host="codex", thread_id="thread-a", usage=usage)
    repeated = policy.open_session(svc, host="codex", thread_id="thread-a", usage=usage)
    handoff = svc.session_last_handoff(result["session"]["id"])

    assert result["host_context"]["level"] == "advisory"
    assert result["host_context"]["checkpoint_saved"] is True
    assert repeated["host_context"]["checkpoint_saved"] is False
    assert result["host_context"]["fresh_window_prompt"] in handoff["next_steps"]


def test_hard_ceiling_refuses_an_old_unbound_thread_and_stops_a_bound_one(svc, monkeypatch):
    monkeypatch.setattr(policy, "load_config", lambda _path: {})
    hard = measured(responses=32)
    refused = policy.open_session(svc, host="codex", thread_id="old-thread", usage=hard)
    policy.open_session(svc, host="codex", thread_id="bound-thread", usage=measured())
    stopped = policy.open_session(svc, host="codex", thread_id="bound-thread", usage=hard)

    assert refused["session"]["ended_at"] is not None
    assert svc.be.session_current("old-thread") is None
    assert refused["host_context"]["allow_continue"] is False
    assert stopped["host_context"]["allow_continue"] is False
    assert stopped["host_context"]["checkpoint_saved"] is True


def test_hard_ceiling_checkpoints_a_legacy_unbound_session_without_reopening_it(svc, monkeypatch):
    monkeypatch.setattr(policy, "load_config", lambda _path: {})
    svc.session_start()
    legacy_id = svc.session_current()["id"]

    result = policy.open_session(
        svc, host="codex", thread_id="old-thread", usage=measured(responses=32)
    )

    assert result["session"]["id"] == legacy_id
    assert result["host_context"]["checkpoint_saved"] is True
    assert result["host_context"]["allow_continue"] is False
    assert svc.be.session_current("old-thread") is None


def test_missing_native_usage_is_explicit_and_never_claims_fresh_context(svc, monkeypatch):
    monkeypatch.setattr(policy, "load_config", lambda _path: {})
    result = policy.open_session(
        svc,
        host="claude",
        thread_id="thread-a",
        usage={"availability": "unavailable", "reason": "no native signal"},
    )

    assert result["host_context"]["level"] == "unavailable"
    assert result["host_context"]["fresh_context"] is False
    assert result["host_context"]["usage"]["reason"]


@pytest.mark.parametrize(
    "config",
    [
        {"host_context_budget": {"advisory": {"responses": 0}}},
        {
            "host_context_budget": {
                "advisory": {"responses": 40},
                "hard": {"responses": 32},
            }
        },
    ],
)
def test_invalid_budget_configuration_fails_before_opening_a_session(svc, monkeypatch, config):
    monkeypatch.setattr(policy, "load_config", lambda _path: config)
    with pytest.raises(ServiceError):
        policy.open_session(svc, host="codex", thread_id="thread-a", usage=measured())
    assert svc.be.session_current("thread-a") is None
