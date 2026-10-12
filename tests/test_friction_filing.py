"""Friction filing is local, idempotent, redacted and transactionally recoverable."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))

from friction_detect import FrictionSignal  # noqa: E402
from friction_filing import FilingRefused, file_signal, pending_friction_count  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402


@pytest.fixture
def project(tmp_path, monkeypatch):
    root = tmp_path / "sample-project"
    tausik_dir = root / ".tausik"
    tausik_dir.mkdir(parents=True)
    (tausik_dir / "config.json").write_text(
        json.dumps({"state": {"auto_export": True}}), encoding="utf-8"
    )
    monkeypatch.setattr("friction_filing._publication_config", lambda _path: {})
    svc = ProjectService(SQLiteBackend(str(tausik_dir / "tausik.db")))
    yield root, svc
    svc.be.close()


def _signal(count: int = 3) -> FrictionSignal:
    return FrictionSignal(
        kind="nonzero-exit",
        signature="nonzero-exit:task done",
        count=count,
        sample="task done at C:\\Clients\\Secret\\repo for owner@example.com",
        remedy_hint="make the refusal actionable",
    )


def test_rerun_updates_one_unstarted_unclaimed_planning_task(project):
    root, svc = project
    slug, first = file_signal(svc, _signal(3), str(root / ".tausik"))
    same_slug, second = file_signal(svc, _signal(7), str(root / ".tausik"))
    projection_path = root / "tausik" / "tasks" / f"{slug}.md"
    before_noop = projection_path.read_bytes()
    log_count = len(svc.task_logs(slug))
    _, third = file_signal(svc, _signal(7), str(root / ".tausik"))

    assert (first, second, third, same_slug) == ("created", "updated", "unchanged", slug)
    tasks = [task for task in svc.task_list(include_archived=True) if task["slug"] == slug]
    assert len(tasks) == 1
    assert tasks[0]["status"] == "planning"
    assert tasks[0]["claimed_by"] is None and tasks[0]["started_at"] is None
    notes = tasks[0]["notes"]
    assert "collapsed_count=3" in notes and "collapsed_count=7" in notes
    assert len(svc.task_logs(slug)) == log_count
    assert projection_path.read_bytes() == before_noop


def test_redacted_identity_is_the_deduplication_key(project):
    root, svc = project
    first = _signal()
    first.signature = "nonzero-exit:owner@example.com"
    second = _signal()
    second.signature = "nonzero-exit:other@example.com"

    first_slug, _ = file_signal(svc, first, str(root / ".tausik"))
    second_slug, action = file_signal(svc, second, str(root / ".tausik"))

    assert first_slug == second_slug and action == "unchanged"
    assert len(svc.task_list(include_archived=True)) == 1


def test_created_task_is_qg0_ready(project):
    root, svc = project
    slug, _ = file_signal(svc, _signal(), str(root / ".tausik"))

    assert "started" in svc.task_start(slug).lower()


def test_pending_count_is_read_only_and_excludes_similarly_named_work(project):
    root, svc = project
    file_signal(svc, _signal(), str(root / ".tausik"))
    svc.task_add(None, "friction-manual-review", "A manually named task", goal="Review it")
    before = len(svc.task_list(include_archived=True))

    assert pending_friction_count(svc) == 1
    assert len(svc.task_list(include_archived=True)) == before


def test_every_persisted_field_and_projection_are_scrubbed(project):
    root, svc = project
    slug, _ = file_signal(svc, _signal(), str(root / ".tausik"))
    task = svc.task_show(slug)
    persisted = "\n".join(
        str(task.get(key) or "")
        for key in ("slug", "title", "goal", "acceptance_criteria", "notes")
    )
    projection = (root / "tausik" / "tasks" / f"{slug}.md").read_text(encoding="utf-8")

    assert "owner@example.com" not in persisted + projection
    assert "C:\\Clients\\Secret" not in persisted + projection
    assert "[redacted]" in persisted and "[redacted]" in projection


def test_canonical_credential_patterns_never_reach_db_or_projection(project):
    root, svc = project
    token = "ghp_" + "A" * 36
    signal = _signal()
    signal.signature = f"nonzero-exit:{token}"
    signal.sample = f"task done --token {token}"

    slug, _ = file_signal(svc, signal, str(root / ".tausik"))
    task = svc.task_show(slug)
    persisted = "\n".join(str(value) for value in task.values())
    projection = (root / "tausik" / "tasks" / f"{slug}.md").read_text(encoding="utf-8")

    assert token not in persisted + projection
    assert "[redacted]" in persisted and "[redacted]" in projection


def test_private_key_match_discards_the_complete_field(project):
    root, svc = project
    key_body = "opaque-key-body-must-not-survive"
    private_key = "-----BEGIN " + f"PRIVATE KEY-----\n{key_body}\n-----END PRIVATE KEY-----"
    signal = _signal()
    signal.sample = f"diagnostic before\n{private_key}\ndiagnostic after"

    slug, _ = file_signal(svc, signal, str(root / ".tausik"))
    task = svc.task_show(slug)
    persisted = "\n".join(str(value) for value in task.values())
    projection = (root / "tausik" / "tasks" / f"{slug}.md").read_text(encoding="utf-8")

    assert key_body not in persisted + projection
    assert "END PRIVATE KEY" not in persisted + projection
    assert "[redacted]" in persisted and "[redacted]" in projection


@pytest.mark.parametrize(
    "sensitive",
    ["owner@example.com", "C:\\Clients\\Secret\\repository"],
)
def test_sensitive_match_crossing_old_display_cutoff_is_scrubbed_first(project, sensitive):
    root, svc = project
    signal = _signal()
    signal.sample = "x" * 194 + " " + sensitive

    slug, _ = file_signal(svc, signal, str(root / ".tausik"))
    persisted = svc.task_show(slug)["notes"]

    assert sensitive not in persisted
    assert "[redacted]" in persisted


def test_existing_started_task_is_not_changed(project):
    root, svc = project
    slug, _ = file_signal(svc, _signal(), str(root / ".tausik"))
    svc.be.task_update(slug, status="active", started_at="2026-10-12T00:00:00+00:00")
    before = svc.task_show(slug)

    _, action = file_signal(svc, _signal(99), str(root / ".tausik"))

    after = svc.task_show(slug)
    assert action == "unchanged"
    assert after["notes"] == before["notes"]
    assert after["status"] == "active" and after["started_at"] == before["started_at"]


def test_scrubber_failure_refuses_without_a_task(project, monkeypatch):
    root, svc = project
    monkeypatch.setattr(
        "brain_scrubbing.scrub_with_config",
        lambda *_a, **_kw: (_ for _ in ()).throw(RuntimeError("broken scrubber")),
    )

    with pytest.raises(FilingRefused, match="scrubber failed"):
        file_signal(svc, _signal(), str(root / ".tausik"))
    assert svc.task_list(include_archived=True) == []


def test_partial_service_failure_leaves_no_task_or_projection(project, monkeypatch):
    root, svc = project
    expected_slug, _ = file_signal(svc, _signal(), str(root / ".tausik"))
    svc.task_delete(expected_slug)
    monkeypatch.setattr(
        svc,
        "task_update",
        lambda *_a, **_kw: (_ for _ in ()).throw(RuntimeError("mid-write")),
    )
    monkeypatch.setattr(
        "state_triggers.auto_export_entity",
        lambda *_a, **_kw: (_ for _ in ()).throw(AssertionError("eager projection")),
    )

    with pytest.raises(RuntimeError, match="mid-write"):
        file_signal(svc, _signal(), str(root / ".tausik"))

    assert svc.be.task_get(expected_slug) is None
    assert not os.path.exists(root / "tausik" / "tasks" / f"{expected_slug}.md")
