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
def svc(tmp_path, monkeypatch):
    """Isolated service fixture. v1.3.2: also stub brain_config.load_brain
    so decide() doesn't read the real project's enabled brain (which would
    cause writes to a live Notion). Tests that need brain enabled override.
    """
    be = SQLiteBackend(str(tmp_path / "test.db"))
    s = ProjectService(be)

    # Force brain disabled by default — individual tests can re-monkeypatch.
    import brain_config

    monkeypatch.setattr(brain_config, "load_brain", lambda: {"enabled": False})

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
        patch("brain_config.validate_brain", return_value=[]),
        patch(
            "brain_runtime.try_brain_write_decision",
            return_value=(True, "page-abc-123"),
        ) as mock_brain,
    ):
        msg = svc.decide("Prefer context managers for file I/O in Python")

    mock_brain.assert_called_once()
    assert "mirrored to brain" in msg
    assert "page-abc-123" in msg
    # The local write is UNCONDITIONAL (decision #203). This used to assert
    # `len(svc.decisions()) == 0` — the data loss was the specified contract, not
    # an oversight: a brain-routed decision existed only as a Notion page, absent
    # from `tausik decisions`, from tausik/, and from the memory block injected at
    # session start. Routing picks where a decision is ALSO published, never
    # whether the project records it.
    assert len(svc.decisions()) == 1


# --- v14b: brain enabled but misconfigured → loud warning, not silent fallback ---


def test_brain_enabled_with_empty_database_ids_returns_loud_warning(svc, monkeypatch):
    """Defect v14b-defect-brain-decisions-empty: when brain.enabled=true but
    database_ids are empty, decide() must save locally AND surface a LOUD
    warning instead of the quiet "brain write failed" fallback. Without this,
    users accumulate local-only decisions that should have been mirrored.
    """
    brain_cfg = {
        "enabled": True,
        "notion_integration_token_env": "TEST_TOKEN",
        "database_ids": {"decisions": "", "patterns": "", "gotchas": "", "web_cache": ""},
    }
    monkeypatch.setenv("TEST_TOKEN", "fake-token")
    import brain_config

    monkeypatch.setattr(brain_config, "load_brain", lambda cfg=None: brain_cfg)
    monkeypatch.setattr(
        brain_config,
        "validate_brain",
        lambda cfg=None: [
            "brain.database_ids.decisions is empty but brain is enabled",
            "brain.database_ids.patterns is empty but brain is enabled",
            "brain.database_ids.gotchas is empty but brain is enabled",
            "brain.database_ids.web_cache is empty but brain is enabled",
        ],
    )

    msg = svc.decide("Use SQLite for project DB")

    assert "BLOCKED" in msg
    assert "LOCALLY ONLY" in msg
    assert "brain init" in msg
    assert "brain.enabled = false" in msg
    assert "decisions is empty" in msg
    assert "brain move --to-brain" in msg
    # Decision still saved locally so user data is never lost.
    assert len(svc.decisions()) == 1


# --- AC5: brain write failure → local fallback ---


def test_brain_write_failure_falls_back_local(svc):
    brain_cfg = {"enabled": True, "notion_integration_token_env": "TEST_TOKEN"}
    with (
        patch("brain_config.load_brain", return_value=brain_cfg),
        patch("brain_config.validate_brain", return_value=[]),
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
        patch("brain_config.validate_brain", return_value=[]),
        patch("brain_notion_client.NotionClient"),
        patch("brain_sync.open_brain_db"),
        patch(
            "brain_mcp_write.store_record",
            return_value={
                "status": "scrub_blocked",
                "issues": [
                    {
                        "detector": "filesystem_paths",
                        "severity": "block",
                        "match": "/home/secret/path",
                        "hint": "Remove absolute path.",
                    },
                    {
                        "detector": "emails",
                        "severity": "block",
                        "match": "attacker@example.com",
                        "hint": "Remove email.",
                    },
                ],
            },
        ),
    ):
        msg = svc.decide("Clean generic text")

    assert "saved to local" in msg
    assert "scrub_blocked" in msg
    assert "filesystem_paths" in msg
    assert "emails" in msg
    # CRIT-1 regression: raw match values must NOT leak into the user-facing
    # reason (they can contain user content / ANSI / prompt-injection payloads).
    assert "/home/secret/path" not in msg
    assert "attacker@example.com" not in msg
    assert "unknown" not in msg
    assert len(svc.decisions()) == 1


def test_brain_ok_not_mirrored_treated_as_success(svc, monkeypatch):
    """status='ok_not_mirrored' (Notion ok, the brain's own mirror lagged) still
    counts as a successful publish — and the project row is written regardless.

    The original version of this test demanded the opposite, on the grounds that a
    local write would mean the decision was "double-written". That premise was
    wrong (decision #203): `brain_sync.open_brain_db` opens a SEPARATE
    cross-project mirror file and never touches the project DB, so a row in each
    is the project's record plus the shared one — not a duplicate. Conflating the
    two stores is what made the routing exclusive and lost decisions.
    """
    brain_cfg = {
        "enabled": True,
        "notion_integration_token_env": "TEST_TOKEN",
        "database_ids": {"decisions": "db-dec-1"},
    }
    monkeypatch.setenv("TEST_TOKEN", "fake-token")
    with (
        patch("brain_config.load_brain", return_value=brain_cfg),
        patch("brain_config.validate_brain", return_value=[]),
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

    assert "mirrored to brain" in msg
    assert "page-partial-xyz" in msg
    assert len(svc.decisions()) == 1  # the project keeps its own record


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


# --- decide-field-limit-cyrillic-unfair: symbol-based limit, no byte penalty ---


def test_decision_limit_counts_symbols_not_bytes_cyrillic_not_penalised(svc):
    """AC1/AC4 (dead-end #324): the limit is in CHARACTERS. A 1000-symbol
    Cyrillic headline is 2000 UTF-8 bytes yet must be accepted — the old
    'byte penalty' theory is false. Below MAX_DECISION=1024 → stored."""
    from tausik_utils import MAX_DECISION

    assert MAX_DECISION == 1024
    cyr = "ы" * 1000  # 1000 code points, 2000 UTF-8 bytes
    assert len(cyr.encode("utf-8")) == 2000
    msg = svc.decide(cyr)
    assert "saved to local" in msg
    assert len(svc.decisions()) == 1


def test_decision_over_symbol_limit_rejected_with_symbol_message(svc):
    """AC4: >MAX_DECISION symbols is rejected, and the message speaks in
    CHARACTERS (not bytes), so the agent knows the real budget."""
    from tausik_utils import MAX_DECISION, ServiceError

    with pytest.raises((ValueError, ServiceError)) as exc:
        svc.decide("ы" * (MAX_DECISION + 1))
    assert "char" in str(exc.value).lower()
    assert str(MAX_DECISION) in str(exc.value)


def test_rationale_also_gets_wide_symbol_limit(svc):
    """AC3: rationale is validated symmetrically against MAX_DECISION so a
    verbose Cyrillic rationale is not the new pain point."""
    from tausik_utils import MAX_DECISION

    svc.decide("Short decision", rationale="ю" * 1000)
    decs = svc.decisions()
    assert len(decs) == 1
    assert len(decs[0]["rationale"]) == 1000
    from tausik_utils import ServiceError

    with pytest.raises((ValueError, ServiceError)):
        svc.decide("Short decision 2", rationale="ю" * (MAX_DECISION + 1))


def test_task_title_still_capped_at_max_title_not_widened(svc):
    """AC5 NEGATIVE: widening the decision limit must NOT touch the task-title
    limit — task titles stay at MAX_TITLE=512."""
    from tausik_utils import MAX_DECISION, MAX_TITLE, ServiceError, validate_length

    assert MAX_TITLE == 512
    assert MAX_DECISION > MAX_TITLE
    # A title between the two limits is fine for a decision but not a task title.
    mid = "t" * 800
    validate_length("decision", mid, MAX_DECISION)  # no raise
    with pytest.raises((ValueError, ServiceError)):
        validate_length("title", mid)  # default MAX_TITLE → raises
