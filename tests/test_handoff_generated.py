"""The handoff is generated from the journal (1.10, story E).

Task `handoff-is-generated-from-the-journal`. SENAR 1.5 §3.45/§7.3: the handoff
is required of every session and is the only route of context between them.
Before: it existed only when the agent hand-wrote a JSON, so sessions closed by
the host had none.
"""

from __future__ import annotations

from pathlib import Path

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from handoff_generate import EMPTY_WINDOW  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402


@pytest.fixture
def svc(tmp_path, monkeypatch):
    monkeypatch.setenv("TAUSIK_DISABLE_SESSION_METRICS", "1")
    s = ProjectService(SQLiteBackend(str(tmp_path / "gen.db")))
    s.epic_add("e", "E")
    s.story_add("e", "s", "S")
    yield s
    s.be.close()


def _task(svc, slug: str) -> None:
    svc.task_add("s", slug, f"Title {slug}", role="developer", goal="g")
    svc.be.task_update(slug, acceptance_criteria="Returns 400 on invalid input.")


def test_the_handoff_is_projected_from_the_window(svc):
    svc.session_start()
    _task(svc, "a")
    _task(svc, "b")
    svc.task_start("a")
    svc.task_log("a", "step 3 of 5: wiring the hook")
    svc.task_start("b")
    svc.be.task_update("b", status="done", completed_at=svc.be.session_current()["started_at"])
    svc.session_handoff()
    h = svc.session_last_handoff()
    assert h["generated_from"] == "journal"
    assert [p["slug"] for p in h["in_progress"]] == ["a"]
    assert h["in_progress"][0]["last_log"].startswith("step 3 of 5")
    assert h["completed"] and h["completed"][0].startswith("b:")
    assert "empty" not in h


def test_an_empty_window_says_so_in_words(svc):
    """NEGATIVE: no records — an explicit sentence, not {} and not invented steps."""
    svc.session_start()
    svc.session_handoff()
    h = svc.session_last_handoff()
    assert h["empty"] == EMPTY_WINDOW
    assert h["completed"] == [] and h["in_progress"] == []


def test_a_task_in_review_is_not_called_completed(svc):
    """NEGATIVE: only status done counts as completed."""
    svc.session_start()
    _task(svc, "r")
    svc.task_start("r")
    svc.be.task_update("r", status="review")
    svc.session_handoff()
    h = svc.session_last_handoff()
    assert h["completed"] == [] and h["in_review"] == ["r"]


def test_authored_fields_sit_on_top_and_are_marked(svc):
    svc.session_start()
    _task(svc, "a")
    svc.task_start("a")
    svc.session_handoff(
        {"next_steps": ["finish a"], "in_progress": [{"slug": "a", "state": "step 4 of 5"}]}
    )
    h = svc.session_last_handoff()
    assert h["next_steps"] == ["finish a"]
    assert h["in_progress"][0]["state"] == "step 4 of 5"
    assert "next_steps" in h["authored_fields"] and "in_progress[].state" in h["authored_fields"]


def test_session_end_writes_the_handoff_when_none_was(svc):
    """The session closed by its host ends WITH a handoff (§7.3)."""
    svc.session_start("host-A")
    _task(svc, "a")
    svc.task_start("a")
    svc.session_end(host_session_id="host-A")
    h = svc.session_last_handoff(1)
    assert h["generated_from"] == "journal" and h["in_progress"][0]["slug"] == "a"


def test_a_failing_generator_does_not_keep_the_session_open(svc, monkeypatch):
    """NEGATIVE: best-effort, but recorded — never silent."""
    import handoff_generate

    def boom(*_a, **_k):
        raise RuntimeError("generator broke")

    monkeypatch.setattr(handoff_generate, "generate", boom)
    svc.session_start()
    svc.session_end()
    assert svc.be.session_current() is None
    actions = [e["action"] for e in svc.be.events_list(entity_type="session", entity_id="1")]
    assert "handoff_generate_failed" in actions


def test_the_skills_call_the_generator_instead_of_a_json_template():
    """The skills stop teaching the agent to re-type what the records hold."""
    for name in ("checkpoint", "end"):
        text = Path(_ROOT, "harness", "skills", name, "SKILL.md").read_text(encoding="utf-8")
        assert "generated from the journal" in text, name
        assert '"completed": ["task-slug-1' not in text, name
