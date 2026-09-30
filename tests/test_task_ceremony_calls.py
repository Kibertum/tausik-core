"""Two calls per task removed, and the two that stay are the ones a driver reads.

THE MEASUREMENT. `task add` could not set acceptance criteria, and QG-0 refuses a start
without them — so every creation was followed by a `task update` supplying the one field the
next step requires. Nine tasks in one shift, nine extra calls. `budget-check` was a second
call after every close. At roughly 482,000 tokens of re-sent prefix per call, and with cost
growing as the calls accumulate, ceremony is not a rounding error: the median task went from
6 calls in April to 32 in September.

WHAT IS NOT REMOVED, and the distinction is the point. `budget-check` still exists and still
answers with an EXIT CODE, because a shell chain reads a status and cannot read a printed
line. What `task done` now prints is the same verdict for the reader who is already looking
at the output — it saves the call without taking the command away.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))


@pytest.fixture
def parser():
    import argparse

    from project_parser_task import add_task

    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd")
    add_task(sub)
    return p


class TestATaskIsStartableAfterOneCommand:
    def test_add_accepts_the_criteria_qg0_demands(self, parser):
        args = parser.parse_args(
            ["task", "add", "T", "--acceptance-criteria", "1. it holds. 2. NEGATIVE: it does not"]
        )
        assert args.acceptance_criteria.startswith("1. it holds")

    def test_the_criteria_reach_the_task(self, tmp_path, monkeypatch):
        """Routed through the same follow-up update that already carried the rollback plan —
        one code path for the fields the creating command sets."""
        monkeypatch.setenv("TAUSIK_DIR", str(tmp_path / ".tausik"))
        (tmp_path / ".tausik").mkdir()
        from project_backend import SQLiteBackend
        from project_service import ProjectService

        be = SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db"))
        svc = ProjectService(be)
        try:
            svc.task_add(None, "t", "Title")
            svc.task_update("t", acceptance_criteria="1. holds. 2. NEGATIVE: refuses")
            assert svc.task_show("t")["acceptance_criteria"].startswith("1. holds")
        finally:
            be.close()

    def test_the_help_says_why_it_is_here(self, parser):
        """A flag with no reason is the next one somebody removes as redundant."""
        import io
        from contextlib import redirect_stdout

        out = io.StringIO()
        with redirect_stdout(out), pytest.raises(SystemExit):
            parser.parse_args(["task", "add", "--help"])
        text = out.getvalue()
        assert "--acceptance-criteria" in text
        assert "QG-0" in text


class TestTheBudgetVerdictArrivesWithTheClosure:
    def test_task_done_prints_it(self):
        source = (_REPO / "scripts" / "project_cli_task.py").read_text(encoding="utf-8")
        head = source.index('elif c == "done"')
        tail = source.index('elif c == "obsolete"', head)
        assert "call_budget_guard" in source[head:tail]
        assert "breach" in source[head:tail]

    def test_the_note_cannot_undo_a_close_that_already_happened(self):
        """The task is closed by the time this runs; a failure while reporting must not turn
        a successful closure into a traceback."""
        source = (_REPO / "scripts" / "project_cli_task.py").read_text(encoding="utf-8")
        head = source.index('elif c == "done"')
        tail = source.index('elif c == "obsolete"', head)
        assert "must not undo it" in source[head:tail]

    def test_budget_check_survives_as_its_own_command(self, parser):
        """NEGATIVE, AC-3: a driver reads the exit code, and removing the command to save a
        call would break every chain built on `&&`."""
        args = parser.parse_args(["task", "budget-check", "some-slug"])
        assert args.task_cmd == "budget-check"

    def test_the_exit_code_path_is_untouched(self):
        source = (_REPO / "scripts" / "project_cli_task.py").read_text(encoding="utf-8")
        head = source.index('elif c == "budget-check"')
        # The branch is the last one, so there is no next `elif` to bound it — read to the
        # end rather than assuming a sibling that may never exist.
        assert "SystemExit(1)" in source[head:]


class TestTheDriftGateStillRefusesToFixItself:
    def test_it_is_declared_a_check_and_not_a_write(self):
        """NEGATIVE, AC-4: auto-redeploying was considered and refused. A gate that rebuilt
        the copies it evaluates would mutate the state it judges — the defect class this
        project already caught in a toggle that was declared a check and executed as a write.
        Saving a call is not worth reintroducing it.
        """
        source = (_REPO / "scripts" / "gate_bootstrap_drift.py").read_text(encoding="utf-8")
        assert "Deliberately FAILS rather than auto-redeploying" in source
        assert "mutating the state it judges" in source
        # And the refusal is not merely documented: the gate NAMES the command for a human
        # to run and never runs it itself.
        body = source.split('"""', 2)[2]
        assert "subprocess" not in body, "the gate must not execute the bootstrap it checks"
