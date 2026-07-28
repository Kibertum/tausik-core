"""backlog-orphan-tasks-invisible-to-release-scope — doctor names epic-unreachable tasks.

The release boundary here is mechanical ("everything in epic X"), and both
`tausik roadmap` and `task list --epic` reach a task only through
story -> epic. A task off that path is counted as absent by every scope
question — which is how the release capstone task and a task named by the gate
config both fell out of the 1.8 count unnoticed.

The class had already been fixed once by hand, without adding a signal, and it
came back at the same size. These tests pin the signal, not the fix.

Coverage:
  - an open task with no story is named, with the repair command;
  - a task on a story whose epic is gone counts too (same invisibility);
  - a CLOSED orphan is silent — it moves no scope number;
  - a clean backlog reports OK rather than vanishing;
  - the check never blocks: it emits no `fail` severity;
  - a backend blowing up degrades to a WARN instead of crashing doctor.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from service_doctor_backlog import (  # noqa: E402
    check_backlog_hygiene,
    find_unreachable_open_tasks,
)


class _FakeBacklog:
    """Stands in for ProjectService.task_list, recording the status filter it got."""

    def __init__(self, rows):
        self.rows = rows
        self.seen_status = None

    def task_list(self, status=None):
        self.seen_status = status
        wanted = set((status or "").split(",")) if status else None
        if wanted is None:
            return list(self.rows)
        return [r for r in self.rows if r.get("status") in wanted]


def _row(slug, status="planning", story_slug=None, epic_slug=None):
    return {
        "slug": slug,
        "status": status,
        "story_slug": story_slug,
        "epic_slug": epic_slug,
    }


def test_open_task_with_no_story_is_named_with_repair_command():
    svc = _FakeBacklog([_row("redoc-1-8-final")])

    findings = check_backlog_hygiene(svc)

    assert len(findings) == 1
    severity, label, detail = findings[0]
    assert severity == "warn"
    assert label == "Backlog hygiene"
    assert "redoc-1-8-final" in detail
    assert "tausik task move" in detail


def test_task_on_story_without_epic_is_unreachable_too():
    """Story attachment is not the invariant — epic reachability is."""
    svc = _FakeBacklog([_row("stranded", story_slug="a-story", epic_slug=None)])

    assert find_unreachable_open_tasks(svc) == ["stranded"]


def test_closed_orphan_is_silent():
    """A done task is out of every scope count already; warning would be noise."""
    svc = _FakeBacklog([_row("ancient-history", status="done")])

    findings = check_backlog_hygiene(svc)

    assert [f[0] for f in findings] == ["ok"]


def test_only_open_statuses_are_queried():
    svc = _FakeBacklog([])

    check_backlog_hygiene(svc)

    assert svc.seen_status is not None
    assert "done" not in svc.seen_status.split(",")
    assert set(svc.seen_status.split(",")) == {"planning", "active", "blocked", "review"}


def test_clean_backlog_reports_ok_rather_than_vanishing():
    svc = _FakeBacklog(
        [
            _row("in-scope", story_slug="l26-arch-debt", epic_slug="landscape-2026-h2"),
            _row("also-fine", status="active", story_slug="s", epic_slug="e"),
        ]
    )

    findings = check_backlog_hygiene(svc)

    assert len(findings) == 1
    assert findings[0][0] == "ok"


def test_check_never_emits_fail():
    """A standalone task is documented as legitimate — this check cannot block."""
    svc = _FakeBacklog([_row(f"orphan-{i}") for i in range(9)])

    assert all(sev != "fail" for sev, _, _ in check_backlog_hygiene(svc))


def test_long_orphan_list_is_summarised_not_dumped():
    svc = _FakeBacklog([_row(f"orphan-{i}") for i in range(9)])

    _, _, detail = check_backlog_hygiene(svc)[0]

    assert "9 open task(s)" in detail
    assert "+6 more" in detail


def test_backend_failure_degrades_to_warn_and_does_not_crash_doctor():
    """The doctor call site wraps every check; assert this one is worth wrapping."""

    class _Exploding:
        def task_list(self, status=None):
            raise RuntimeError("database is locked")

    with pytest.raises(RuntimeError):
        check_backlog_hygiene(_Exploding())

    # ... and the call site turns that into a warning rather than an exit.
    import project_cli_doctor

    src = open(project_cli_doctor.__file__, encoding="utf-8").read()
    assert "check_backlog_hygiene" in src
    assert 'f"could not validate: {e}"' in src
