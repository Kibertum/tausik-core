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

    The DB now lives at `<tmp>/.tausik/tausik.db` and `find_tausik_dir` points at
    it, which makes this tmp DB genuinely THE project DB for the duration of the
    test. `decide` refuses to publish from a service bound to anything else — the
    hazard this fixture's comment described is now enforced rather than avoided
    by remembering to stub, so a test that wants the brain path must say so by
    being a well-formed project, not by being lucky.
    """
    tausik_dir = tmp_path / ".tausik"
    tausik_dir.mkdir(parents=True, exist_ok=True)
    be = SQLiteBackend(str(tausik_dir / "tausik.db"))
    s = ProjectService(be)

    import project_config

    monkeypatch.setattr(project_config, "find_tausik_dir", lambda *a, **k: str(tausik_dir))

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








# --- AC3: brain disabled → local fallback ---




def test_clean_content_keeps_backward_compat_recorded_word(svc):
    """Existing tests assert 'recorded' in msg — must stay true."""
    msg = svc.decide("Use REST API", rationale="Simpler than GraphQL")
    assert "recorded" in msg


# --- AC2: brain enabled + clean → routes brain ---




# --- v14b: brain enabled but misconfigured → loud warning, not silent fallback ---




# --- AC5: brain write failure → local fallback ---








# --- AC6: empty/whitespace text routes to local with "empty content" reason ---






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
