"""Tests for service_knowledge.decide() auto-routing via brain_classifier."""

from __future__ import annotations

import os
import sys
from unittest.mock import patch

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402


@pytest.fixture
def svc(tmp_path):
    be = SQLiteBackend(str(tmp_path / "test.db"))
    s = ProjectService(be)
    yield s
    be.close()


# --- AC4: task_slug forces local regardless of content ---


def test_task_slug_forces_local_even_for_clean_generic_content(svc):
    svc.epic_add("e1", "Epic")
    svc.story_add("e1", "s1", "Story")
    svc.task_add("s1", "t1", "T1")
    msg = svc.decide("Use exponential backoff for retries", task_slug="t1")
    assert "saved to local" in msg
    assert "linked to task t1" in msg
    assert len(svc.decisions()) == 1


def test_task_slug_forces_local_does_not_call_brain(svc):
    svc.epic_add("e1", "Epic")
    svc.story_add("e1", "s1", "Story")
    svc.task_add("s1", "t1", "T1")
    with patch("brain_runtime.try_brain_write_decision") as mock_brain:
        msg = svc.decide("Generic tip about HTTP/2", task_slug="t1")
    mock_brain.assert_not_called()
    assert "saved to local" in msg


# --- AC1: markers content routes local ---


def test_content_with_src_file_marker_routes_local(svc):
    msg = svc.decide("See scripts/brain_runtime.py for the wiring")
    assert "saved to local" in msg
    assert "src_file marker" in msg
    assert len(svc.decisions()) == 1


def test_content_with_abs_path_marker_routes_local(svc):
    msg = svc.decide("Bug in D:\\Work\\Personal\\claude\\scripts\\foo.py")
    assert "saved to local" in msg
    assert "marker" in msg


def test_content_with_tausik_cmd_marker_routes_local(svc):
    msg = svc.decide("Run tausik_task_start before coding")
    assert "saved to local" in msg


# --- AC3: brain disabled → local fallback ---


def test_clean_content_brain_disabled_falls_back_local(svc):
    msg = svc.decide("HTTP/2 negotiates via ALPN in TLS handshake")
    assert "saved to local" in msg
    assert "brain not enabled" in msg
    assert len(svc.decisions()) == 1


def test_clean_content_keeps_backward_compat_recorded_word(svc):
    """Existing tests assert 'recorded' in msg — must stay true."""
    msg = svc.decide("Use REST API", rationale="Simpler than GraphQL")
    assert "recorded" in msg


# --- AC2: brain enabled + clean → routes brain ---


def test_clean_content_brain_enabled_routes_brain(svc):
    brain_cfg = {
        "enabled": True,
        "notion_integration_token_env": "TEST_TOKEN",
        "database_ids": {"decisions": "db-dec-1"},
    }
    with (
        patch("brain_config.load_brain", return_value=brain_cfg),
        patch(
            "brain_runtime.try_brain_write_decision",
            return_value=(True, "page-abc-123"),
        ) as mock_brain,
    ):
        msg = svc.decide("Prefer context managers for file I/O in Python")

    mock_brain.assert_called_once()
    assert "saved to brain" in msg
    assert "page-abc-123" in msg
    # Local fallback did NOT fire.
    assert len(svc.decisions()) == 0


# --- AC5: brain write failure → local fallback ---


def test_brain_write_failure_falls_back_local(svc):
    brain_cfg = {"enabled": True, "notion_integration_token_env": "TEST_TOKEN"}
    with (
        patch("brain_config.load_brain", return_value=brain_cfg),
        patch(
            "brain_runtime.try_brain_write_decision",
            return_value=(False, "notion_error: 429 Too Many Requests"),
        ),
    ):
        msg = svc.decide("A generic useful lesson about APIs")

    assert "saved to local" in msg
    assert "brain write failed" in msg
    assert "429" in msg
    assert len(svc.decisions()) == 1


def test_brain_scrub_blocked_falls_back_local(svc, monkeypatch):
    """Patches brain_mcp_write.store_record one layer deeper so the real
    try_brain_write_decision exercises issues-list → message formatting."""
    brain_cfg = {
        "enabled": True,
        "notion_integration_token_env": "TEST_TOKEN",
        "database_ids": {"decisions": "db-dec-1"},
    }
    monkeypatch.setenv("TEST_TOKEN", "fake-token")
    with (
        patch("brain_config.load_brain", return_value=brain_cfg),
        patch("brain_notion_client.NotionClient"),
        patch("brain_sync.open_brain_db"),
        patch(
            "brain_mcp_write.store_record",
            return_value={
                "status": "scrub_blocked",
                "issues": ["filesystem_paths", "slug_markers"],
            },
        ),
    ):
        msg = svc.decide("Clean generic text")

    assert "saved to local" in msg
    assert "scrub_blocked" in msg
    assert "filesystem_paths" in msg
    assert "slug_markers" in msg
    assert "unknown" not in msg
    assert len(svc.decisions()) == 1


def test_brain_ok_not_mirrored_treated_as_success(svc, monkeypatch):
    """AC1: status='ok_not_mirrored' (Notion ok, local mirror lagged) must
    NOT trigger local decision_add — otherwise decision is double-written."""
    brain_cfg = {
        "enabled": True,
        "notion_integration_token_env": "TEST_TOKEN",
        "database_ids": {"decisions": "db-dec-1"},
    }
    monkeypatch.setenv("TEST_TOKEN", "fake-token")
    with (
        patch("brain_config.load_brain", return_value=brain_cfg),
        patch("brain_notion_client.NotionClient"),
        patch("brain_sync.open_brain_db"),
        patch(
            "brain_mcp_write.store_record",
            return_value={
                "status": "ok_not_mirrored",
                "notion_page_id": "page-partial-xyz",
                "warning": "mirror write failed: disk full",
            },
        ),
    ):
        msg = svc.decide("Prefer async context managers for network I/O")

    assert "saved to brain" in msg
    assert "page-partial-xyz" in msg
    assert len(svc.decisions()) == 0  # NOT written locally


# --- AC6: empty/whitespace text routes to local with "empty content" reason ---


def test_empty_text_routes_local(svc):
    """validate_length only caps upper bound — empty passes through, classifier sends local."""
    msg = svc.decide("")
    assert "saved to local" in msg
    assert "empty content" in msg
    assert len(svc.decisions()) == 1


def test_whitespace_only_routes_local(svc):
    msg = svc.decide("   \n\t  ")
    assert "saved to local" in msg
    assert "empty content" in msg


# --- AC7: backward compat with rationale stored in local fallback ---


def test_rationale_preserved_on_local_fallback(svc):
    svc.decide("Generic decision text", rationale="Because it is simpler")
    decs = svc.decisions()
    assert len(decs) == 1
    assert decs[0]["rationale"] == "Because it is simpler"


# --- Edge: brain_runtime helper never raises ---


def test_try_brain_write_decision_returns_false_on_missing_token(monkeypatch):
    import brain_runtime

    monkeypatch.delenv("UNSET_TOKEN_VAR", raising=False)
    cfg = {"notion_integration_token_env": "UNSET_TOKEN_VAR"}
    ok, detail = brain_runtime.try_brain_write_decision("text", None, cfg)
    assert ok is False
    assert "token" in detail.lower()


def test_try_brain_write_decision_swallows_exceptions(monkeypatch):
    import brain_runtime

    monkeypatch.setenv("FAKE_TOKEN", "x")
    cfg = {
        "notion_integration_token_env": "FAKE_TOKEN",
        "database_ids": {"decisions": "nope"},
    }
    # Force Notion client to blow up on network call.
    with patch("brain_notion_client.NotionClient") as mock_cls:
        mock_cls.return_value.pages_create.side_effect = RuntimeError("boom")
        ok, detail = brain_runtime.try_brain_write_decision("text", None, cfg)

    assert ok is False
    # Either we return the structured error OR the exception branch.
    assert "notion_error" in detail or "exception" in detail or "boom" in detail
