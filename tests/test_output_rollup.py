"""Tests for scripts/output_rollup.py + its wiring into events / task list.

AC coverage (tool-output-rollup):
  1. deterministic hierarchical aggregate (grouping + counts).
  2. budget knobs top_n / min_count / max_lines work and print the DENOMINATOR.
  3. wired into >=2 expensive commands (events + task list); --full → full output.
  4. NEGATIVE: below threshold NOT collapsed; --full ALWAYS bypasses.
  5. presentation only: --full is byte-identical to the pre-rollup output.
"""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from output_rollup import DEFAULT_THRESHOLD, render_rollup, should_rollup  # noqa: E402


def _events(n: int) -> list[dict]:
    """n synthetic events cycling through a few entity/action pairs."""
    kinds = [("task", "start"), ("task", "done"), ("epic", "add"), ("task", "start")]
    out = []
    for i in range(n):
        et, ac = kinds[i % len(kinds)]
        out.append(
            {
                "created_at": f"2026-07-27T00:00:{i:02d}Z",
                "entity_type": et,
                "entity_id": f"e{i}",
                "action": ac,
                "actor": "agent" if i % 2 else None,
                "details": "d" if i % 3 == 0 else None,
            }
        )
    return out


# ------------------------------------------------------------ should_rollup ---


class TestShouldRollup:
    def test_full_never_rolls_up(self):
        assert should_rollup(1000, full=True) is False

    def test_below_threshold_is_full(self):
        assert should_rollup(DEFAULT_THRESHOLD - 1, full=False) is False

    def test_at_or_above_threshold_rolls_up(self):
        assert should_rollup(DEFAULT_THRESHOLD, full=False) is True
        assert should_rollup(DEFAULT_THRESHOLD + 5, full=False) is True


# ------------------------------------------------------------ render_rollup ---


class TestRenderRollup:
    def test_deterministic_order_and_counts(self):
        rows = _events(8)  # task/start x4, task/done x2, epic/add x2
        lines = render_rollup(rows, ["entity_type", "action"], title="Events")
        assert lines[0].startswith("Events — 8 rows in 3 group(s)")
        body = lines[1:]
        # most frequent first; ties (2 vs 2) broken by key ascending
        assert body[0].strip().startswith("4")
        assert "task / start" in body[0]
        # epic/add sorts before task/done at equal count (key ascending)
        assert "epic / add" in body[1]
        assert "task / done" in body[2]

    def test_same_input_same_output(self):
        rows = _events(30)
        assert render_rollup(rows, ["entity_type", "action"], title="E") == render_rollup(
            rows, ["entity_type", "action"], title="E"
        )

    def test_top_n_prints_denominator(self):
        rows = _events(8)
        lines = render_rollup(rows, ["entity_type", "action"], title="Events", top_n=1)
        group_lines = [ln for ln in lines[1:] if not ln.strip().startswith("…")]
        assert len(group_lines) == 1
        footer = lines[-1]
        assert "…" in footer
        assert "2 more group(s)" in footer  # 3 groups, 1 shown
        assert "4 row(s) not shown" in footer  # 8 total - 4 shown

    def test_max_lines_is_stricter_of_the_two(self):
        rows = _events(30)
        lines = render_rollup(rows, ["entity_type", "action"], title="E", top_n=3, max_lines=1)
        group_lines = [ln for ln in lines[1:] if not ln.strip().startswith("…")]
        assert len(group_lines) == 1  # max_lines=1 wins over top_n=3

    def test_min_count_hides_and_counts(self):
        rows = _events(8)  # counts: 4, 2, 2
        lines = render_rollup(rows, ["entity_type", "action"], title="E", min_count=3)
        group_lines = [ln for ln in lines[1:] if not ln.strip().startswith("…")]
        assert len(group_lines) == 1  # only the count-4 group survives
        assert "min_count=3" in lines[-1]
        assert "2 more group(s)" in lines[-1]


# -------------------------------------------------- events command wiring ---


def _full_events_oracle(events: list[dict]) -> str:
    """Exact pre-rollup per-event render — the byte-for-byte oracle for --full."""
    out = []
    for ev in events:
        actor = f" by {ev['actor']}" if ev.get("actor") else ""
        out.append(
            f"[{ev['created_at']}] {ev['entity_type']}/{ev['entity_id']}: {ev['action']}{actor}"
        )
        if ev.get("details"):
            out.append(f"  {ev['details']}")
    return "\n".join(out) + "\n"


class _FakeEventsSvc:
    def __init__(self, events):
        self._events = events

    def events_list(self, entity_type=None, entity_id=None, n=None):
        return self._events


def _events_args(full=False, top_n=None, max_lines=None):
    return SimpleNamespace(
        events_cmd=None,
        entity=None,
        entity_id=None,
        limit=100,
        full=full,
        top_n=top_n,
        max_lines=max_lines,
    )


class TestEventsWiring:
    def test_below_threshold_is_byte_identical(self, capsys):
        from project_cli_events import cmd_events

        events = _events(5)
        cmd_events(_FakeEventsSvc(events), _events_args())
        assert capsys.readouterr().out == _full_events_oracle(events)

    def test_above_threshold_rolls_up_by_default(self, capsys):
        from project_cli_events import cmd_events

        cmd_events(_FakeEventsSvc(_events(40)), _events_args())
        out = capsys.readouterr().out
        assert out.startswith("Events — 40 rows")
        assert "task / start" in out

    def test_full_flag_is_byte_identical_above_threshold(self, capsys):
        """AC5: --full on a large log reproduces the exact prior dump."""
        from project_cli_events import cmd_events

        events = _events(40)
        cmd_events(_FakeEventsSvc(events), _events_args(full=True))
        assert capsys.readouterr().out == _full_events_oracle(events)


# ------------------------------------------------ task list command wiring ---


class _FakeTaskSvc:
    def __init__(self, tasks):
        self._tasks = tasks

    def task_list(self, *a, **k):
        return self._tasks


def _tasks(n: int) -> list[dict]:
    statuses = ["planning", "done", "active", "done"]
    out = []
    for i in range(n):
        out.append(
            {
                "slug": f"t{i}",
                "title": f"Task {i}",
                "status": statuses[i % len(statuses)],
                "story_slug": "s1",
                "role": "developer",
                "stack": "python",
            }
        )
    return out


def _task_args(full=False):
    return SimpleNamespace(
        task_cmd="list",
        status=None,
        story=None,
        epic=None,
        role=None,
        stack=None,
        limit=None,
        include_archived=False,
        full=full,
        top_n=None,
        max_lines=None,
    )


class TestTaskListWiring:
    def test_below_threshold_is_byte_identical(self, capsys):
        from project_cli import _print_table
        from project_cli_task import cmd_task

        tasks = _tasks(5)
        cmd_task(_FakeTaskSvc(tasks), _task_args())
        got = capsys.readouterr().out
        _print_table(tasks, ["slug", "title", "status", "story_slug", "role", "stack"])
        oracle = capsys.readouterr().out
        assert got == oracle

    def test_above_threshold_rolls_up_by_default(self, capsys):
        from project_cli_task import cmd_task

        cmd_task(_FakeTaskSvc(_tasks(40)), _task_args())
        out = capsys.readouterr().out
        assert out.startswith("Tasks — 40 rows")

    def test_full_flag_is_byte_identical_above_threshold(self, capsys):
        """AC5: --full on a large list reproduces the exact prior table."""
        from project_cli import _print_table
        from project_cli_task import cmd_task

        tasks = _tasks(40)
        cmd_task(_FakeTaskSvc(tasks), _task_args(full=True))
        got = capsys.readouterr().out
        _print_table(tasks, ["slug", "title", "status", "story_slug", "role", "stack"])
        oracle = capsys.readouterr().out
        assert got == oracle
