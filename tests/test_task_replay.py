"""v16r-task-replay: chronological task-timeline reconstruction.

Covers the merged timeline (logs + reasoning + events + verification with
receipt), deterministic ordering across sources, graceful behaviour on
historical tasks with missing sources, file export, and the bad-slug error.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "replay.db")))
    yield s
    s.be.close()


def _seed_task(svc, slug: str = "rp1") -> None:
    svc.epic_add("e1", "Epic 1")
    svc.story_add("e1", "s1", "Story 1")
    svc.task_add("s1", slug, "Replay Task", role="developer", goal="reconstruct timeline")


def _insert_log(svc, slug, msg, ts):
    svc.be._ins(
        "INSERT INTO task_logs(task_slug,message,created_at) VALUES(?,?,?)", (slug, msg, ts)
    )


def _insert_reason(svc, slug, seq, kind, content, ts):
    svc.be._ins(
        "INSERT INTO reasoning_steps(task_slug,seq,kind,content,created_at) VALUES(?,?,?,?,?)",
        (slug, seq, kind, content, ts),
    )


def _insert_event(svc, slug, action, ts, actor=None, details=None):
    svc.be._ins(
        "INSERT INTO events(entity_type,entity_id,action,actor,details,created_at) "
        "VALUES('task',?,?,?,?,?)",
        (slug, action, actor, details, ts),
    )


def _insert_verify(svc, slug, scope, cmd, exit_code, ts, receipt_json=None):
    svc.be._ins(
        "INSERT INTO verification_runs"
        "(task_slug,scope,command,exit_code,files_hash,ran_at,receipt_json) "
        "VALUES(?,?,?,?,?,?,?)",
        (slug, scope, cmd, exit_code, "deadbeef", ts, receipt_json),
    )


# === AC1: merged chronological timeline across all four sources ===


def test_replay_merges_and_sorts_all_sources(svc):
    _seed_task(svc)
    # Insert deliberately out of order; expect: event < log < reason < verify
    _insert_log(svc, "rp1", "did the thing", "2026-01-01T10:00:00Z")
    _insert_reason(svc, "rp1", 1, "intent", "achieve X", "2026-01-01T10:00:05Z")
    _insert_event(svc, "rp1", "started", "2026-01-01T09:59:00Z", actor="dev")
    _insert_verify(svc, "rp1", "standard", "pytest", 0, "2026-01-01T10:01:00Z")

    md = svc.task_replay("rp1")
    assert "# Replay — rp1" in md
    assert "Replay Task" in md and "reconstruct timeline" in md
    # source tags present
    for tag in ("**event**", "**log**", "**reason**", "**verify**"):
        assert tag in md
    # chronological order: event first, verify last
    i_event = md.index("**event**")
    i_log = md.index("**log**")
    i_reason = md.index("**reason**")
    i_verify = md.index("**verify**")
    assert i_event < i_log < i_reason < i_verify
    # per-source footer counts (events also include the auto 'created'
    # lifecycle event from task_add, so assert on content not an exact count)
    assert "logs: 1" in md
    assert "reasoning steps: 1" in md
    assert "verification runs: 1" in md
    assert "started by dev" in md
    # events source is wired: at least the inserted 'started' + auto 'created'
    assert "events: 2" in md


def test_replay_renders_verdict_and_receipt(svc):
    _seed_task(svc)
    envelope = json.dumps({"signature": {"key_fingerprint": "abc123"}})
    _insert_verify(svc, "rp1", "critical", "tsc", 1, "2026-01-01T10:00:00Z", receipt_json=envelope)
    md = svc.task_replay("rp1")
    assert "FAIL(exit=1)" in md
    assert "receipt: signed (key abc123)" in md


# === AC2: graceful on historical tasks missing sources ===


def test_replay_graceful_zero_reasoning_and_verification(svc):
    """A historical task with only a log — no reasoning_steps, no verify runs —
    must replay without crashing and mark absent sources explicitly."""
    _seed_task(svc)
    _insert_log(svc, "rp1", "legacy note", "2026-01-01T10:00:00Z")
    md = svc.task_replay("rp1")
    assert "legacy note" in md
    assert "reasoning steps: 0 (none)" in md
    assert "verification runs: 0 (none)" in md


def test_render_empty_timeline_marker():
    """Unit-test the renderer's empty branch directly — a real task always has
    at least a 'created' lifecycle event, so exercise the no-entries path here."""
    from service_replay import ReplayMixin

    md = ReplayMixin._render({"slug": "x", "title": "T", "status": "done"}, [], {"logs": 0})
    assert "(none — no logs, reasoning, events, or verification recorded)" in md
    assert "logs: 0 (none)" in md


def test_replay_bad_slug_raises(svc):
    """NEGATIVE: replay on a nonexistent task is a friendly error, not a traceback."""
    with pytest.raises(ServiceError):
        svc.task_replay("ghost")


# === AC3: file export ===


def test_replay_writes_to_file(svc, tmp_path):
    _seed_task(svc)
    _insert_log(svc, "rp1", "exported entry", "2026-01-01T10:00:00Z")
    out = tmp_path / "timeline.md"
    result = svc.task_replay("rp1", output=str(out))
    assert "written to" in result and str(out) in result
    assert out.is_file()
    content = out.read_text(encoding="utf-8")
    assert "exported entry" in content and "# Replay — rp1" in content


def test_replay_refuses_protected_memory_path(svc, tmp_path):
    """NEGATIVE: writing into a .claude/**/memory/ dir is refused (open()
    bypasses the memory-write pretool hook)."""
    _seed_task(svc)
    bad = tmp_path / ".claude" / "projects" / "x" / "memory" / "out.md"
    with pytest.raises(ServiceError, match="protected agent-memory"):
        svc.task_replay("rp1", output=str(bad))
    assert not bad.exists()


# === CLI parser wiring ===


def test_cli_parser_accepts_replay():
    from project_parser import build_parser

    parser = build_parser()
    ns = parser.parse_args(["task", "replay", "rp1", "--output", "x.md"])
    assert ns.slug == "rp1"
    assert ns.output == "x.md"
