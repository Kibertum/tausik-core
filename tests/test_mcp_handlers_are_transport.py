"""MCP handlers must be transport, and the ratchet holds the line.

The defect class: an MCP handler that renders the service result is a SECOND
implementation of a command the CLI already implements, and two implementations
mean two possible verdicts. It has bitten this project repeatedly — the
`update_claudemd` handler silently dropped the memory injection, and
`tausik_task_next` reports the COUNT of withheld tasks where the CLI reports
their NAMES.

The subject is DERIVED (scripts/mcp_handler_shape) rather than listed: a
hand-written list of offenders is complete on the day it is written. What is
listed here is the BASELINE — the set measured when the ratchet was installed —
and it may only shrink. Both directions are asserted: a new second
implementation is a failure, and one that has been collapsed must leave the
baseline, or the baseline stops being a ratchet and becomes a list nobody prunes.
"""

from __future__ import annotations

import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
# The handler package too, and INSERTED HERE rather than inherited: a module
# that gets its path from whichever sibling test happened to run first is green
# by collection order, not by construction (memory #593).
sys.path.insert(0, os.path.join(_ROOT, "harness", "claude", "mcp", "project"))

from mcp_handler_shape import (  # noqa: E402
    HandlersUnreadable,
    dispatch_entries,
    handler_dir,
    renders_result,
    second_implementations,
)

# Reads the MCP handler tree, which no import edge connects to this file.
CROSSCUTTING_SCOPE = ["harness/claude/mcp/project/", "scripts/mcp_handler_shape.py"]

#: The second implementations that existed when this ratchet was installed.
#: Every entry is a command whose text is built twice — once here, once in the
#: CLI — and every one of them is work owed, not a permission. Remove an entry
#: the moment its handler stops rendering; `test_the_baseline_only_shrinks`
#: fails if you do not.
BASELINE = frozenset(
    {
        # Owned by mcp-task-show-hides-the-fields-the-agent-is-judged-by, whose
        # AC1 is exactly this handler's field list. Collapsing it here would
        # take that task's subject, not finish it.
        "tausik_task_show",
    }
)

#: A dispatch table that shrank to nothing would make every assertion here pass
#: while measuring an empty tree. The floor is far below the real count (105 at
#: installation) — it exists to catch a broken table convention, not to pin a
#: number that legitimately moves.
_MIN_TOOLS = 50


def _measured() -> dict[str, str]:
    return second_implementations(_ROOT)


def test_no_new_second_implementation():
    new = set(_measured()) - BASELINE
    assert not new, (
        "these MCP handlers build text out of the service result, so the command "
        "is implemented twice and the two renderings can disagree. Call the same "
        "shared renderer the CLI calls:\n  " + "\n  ".join(sorted(new))
    )


def test_the_baseline_only_shrinks():
    stale = BASELINE - set(_measured())
    assert not stale, (
        "these no longer render the result — remove them from BASELINE, or the "
        "ratchet stops being one:\n  " + "\n  ".join(sorted(stale))
    )


def test_the_measurement_is_not_blind():
    """A criterion with no subject passes vacuously. Hold it to the real tree."""
    entries = dispatch_entries(_ROOT)
    assert len(entries) >= _MIN_TOOLS, (
        f"only {len(entries)} dispatch entries found — the `*_HANDLERS` table "
        "convention likely changed and this control now measures nothing"
    )
    assert any(target for _, _, target in entries), "no entry names a handler"


def test_an_unreadable_tree_refuses_instead_of_reporting_zero(tmp_path):
    """Unreadable and clean are different answers, and only one of them is good."""
    with pytest.raises(HandlersUnreadable):
        second_implementations(str(tmp_path))
    with pytest.raises(HandlersUnreadable):
        handler_dir(str(tmp_path))


class TestBothSurfacesSayTheSameThing:
    """Proof by RUNNING them, not by reading their shape.

    The structural ratchet says no handler renders the result any more. That is
    not the same statement as "the two surfaces answer alike" — a handler could
    call a different shared function and still be transport. These drive both
    surfaces over one database and compare what comes back.
    """

    @staticmethod
    def _svc(tmp_path):
        from project_backend import SQLiteBackend
        from project_service import ProjectService

        return ProjectService(SQLiteBackend(os.path.join(str(tmp_path), "t.db")))

    def test_task_next_names_the_withheld_tasks_on_both(self, tmp_path, capsys):
        """The live divergence this task was opened on.

        The handler reported HOW MANY tasks were withheld; the CLI reports
        WHICH. An agent on MCP could see that the plan was waiting and not on
        what.
        """
        from handlers import handle_tool
        from project_cli_task import cmd_task
        from service_task_order import task_depends

        svc = self._svc(tmp_path)
        svc.epic_add("e", "E")
        svc.story_add("e", "s", "S")
        for slug in ("ready-one", "waits-on-ready"):
            svc.task_add("s", slug, slug, complexity="simple", role="developer")
        task_depends(svc, "waits-on-ready", "ready-one")

        mcp = handle_tool(svc, "tausik_task_next", {})
        cmd_task(svc, _Args(task_cmd="next", agent=None))
        cli = capsys.readouterr().out.strip()

        assert "waits-on-ready" in mcp, "the MCP answer still hides WHICH task is withheld: " + mcp
        assert cli.split("\n") == mcp.split("\n")[: len(cli.split("\n"))]

    def test_memory_show_carries_the_same_fields_on_both(self, tmp_path, capsys):
        from handlers import handle_tool
        from project_cli_extra import cmd_memory

        svc = self._svc(tmp_path)
        svc.memory_add("gotcha", "A title", "The body", ["alpha", "beta"], None)

        mcp = handle_tool(svc, "tausik_memory_show", {"id": 1})
        cmd_memory(svc, _Args(memory_cmd="show", id=1))
        cli = capsys.readouterr().out.rstrip("\n")

        assert cli == mcp
        assert "Tags: alpha, beta" in mcp, (
            "tags are back on the MCP surface — they were dropped by the copy"
        )
        assert "Created:" in mcp

    @staticmethod
    def _pin_machine_tails(monkeypatch):
        """Silence the two report tails that read the MACHINE, not the service.

        `risk_summary` and the routing-adherence rollup read the live `.tausik`
        directory, so their answer can change BETWEEN the two calls this test
        makes — under a parallel full run it did, and the comparison failed on
        data neither surface produced. They come from one shared builder either
        way; what is under test is everything the service yields.
        """
        import render_metrics

        monkeypatch.setattr(render_metrics, "_risk_lines", lambda svc: [])
        monkeypatch.setattr(render_metrics, "_routing_lines", lambda: [])

    def test_metrics_is_the_whole_report_on_both(self, tmp_path, capsys, monkeypatch):
        """The MCP tool used to answer with one summary line."""
        from handlers import handle_tool
        from project_cli_metrics import cmd_metrics

        self._pin_machine_tails(monkeypatch)
        svc = self._svc(tmp_path)
        svc.epic_add("e", "E")
        svc.story_add("e", "s", "S")
        svc.task_add("s", "t", "T", complexity="simple", role="developer")

        mcp = handle_tool(svc, "tausik_metrics", {})
        cmd_metrics(svc, _Args(metrics_cmd=None))
        cli = capsys.readouterr().out.rstrip("\n")

        assert cli == mcp
        for section in ("Throughput:", "FPSR:", "DER:", "Knowledge CR:"):
            assert section in mcp, f"{section} missing from the MCP report"
        # A tail from `extended_metrics_lines`, asserted BY CONTENT. Comparing
        # the two surfaces cannot see a section dropped from the shared builder
        # — it disappears from both at once and they stay equal. A mutation that
        # removed the whole extended tail survived until this line existed.
        assert "--- Defect Escape (l26) ---" in mcp

    def test_metrics_on_an_empty_project_answers_rather_than_raising(
        self, tmp_path, capsys, monkeypatch
    ):
        """Negative: nothing measured yet is not the same as measured zero.

        A lead time of `0h` on a project with no closed task would be a claim
        about a measurement nobody took.
        """
        from handlers import handle_tool
        from project_cli_metrics import cmd_metrics

        self._pin_machine_tails(monkeypatch)
        svc = self._svc(tmp_path)
        mcp = handle_tool(svc, "tausik_metrics", {})
        cmd_metrics(svc, _Args(metrics_cmd=None))
        assert capsys.readouterr().out.rstrip("\n") == mcp
        assert "Lead Time:     n/a" in mcp
        assert "Cycle Time:    n/a" in mcp

    def test_team_is_identical_on_both(self, tmp_path, capsys):
        from handlers import handle_tool
        from project_cli import cmd_team

        svc = self._svc(tmp_path)
        mcp = handle_tool(svc, "tausik_team", {})
        cmd_team(svc, _Args())
        assert capsys.readouterr().out.rstrip("\n") == mcp


class TestVerifyReportIsBuiltOnce:
    """The last command that was implemented twice, and the drift ran both ways."""

    @staticmethod
    def _svc(tmp_path):
        from project_backend import SQLiteBackend
        from project_service import ProjectService

        return ProjectService(SQLiteBackend(os.path.join(str(tmp_path), "v.db")))

    @staticmethod
    def _report(**over):
        report = {
            "passed": True,
            "status": "ok",
            "trigger": "verify",
            "results": [{"name": "pytest", "passed": True, "skipped": False}],
            "duration_ms": 42,
            "run_id": 7,
            "relevant_files": ["a.py"],
            "verify_handle": "7.abc",
            "handle_expires_at": "2026-01-01T00:00:00Z",
        }
        report.update(over)
        return report

    def test_a_cache_hit_says_where_the_answer_came_from(self, tmp_path):
        """It used to reach only the CLI, so a cached green arrived at the agent
        as a header over an empty gate list — 'nothing executed' by any reading."""
        from render_verify import verify_lines

        svc = self._svc(tmp_path)
        hit = {"id": 3, "ran_at": "2026-01-01", "scope": "manual", "exit_code": 0}
        out = "\n".join(verify_lines(svc, {"cache_hit": hit}, "t", "manual"))
        assert "cache HIT" in out and "#3" in out

    def test_the_report_carries_what_only_the_cli_used_to_say(self, tmp_path):
        from render_verify import verify_lines

        svc = self._svc(tmp_path)
        out = "\n".join(verify_lines(svc, self._report(), "t", "manual"))
        assert "Duration: 42 ms" in out
        assert "Recorded verification_run #7" in out
        assert "Receipt:" in out
        assert "Verify handle: 7.abc" in out

    def test_the_report_carries_what_only_the_handler_used_to_say(self, tmp_path):
        """A SKIP is not a verification. The handler said so; the CLI did not."""
        from render_verify import verify_lines

        svc = self._svc(tmp_path)
        report = self._report(results=[{"name": "pytest", "passed": True, "skipped": True}])
        out = "\n".join(verify_lines(svc, report, "t", "manual"))
        assert "did NOT execute" in out
        assert "gates=['" not in out, "regressed to naming gates without verdicts"

    def test_a_failed_write_never_prints_the_word_passed(self, tmp_path):
        """Negative: no verdict beside the admission that no evidence exists."""
        from render_verify import verify_lines

        svc = self._svc(tmp_path)
        report = self._report(run_id=None, passed=False, status="record-failed")
        out = "\n".join(verify_lines(svc, report, "t", "manual"))
        assert "NOT RECORDED" in out
        assert "PASSED" not in out

    def test_a_red_run_exits_one_on_the_cli(self, tmp_path, monkeypatch, capsys):
        """Negative: the surfaces may share the text, not the exit code."""
        import pytest as _pytest

        from project_cli_verify import cmd_verify

        svc = self._svc(tmp_path)
        monkeypatch.setattr(svc, "run_verify_for_task", lambda *a, **k: self._report(passed=False))
        with _pytest.raises(SystemExit) as exc:
            cmd_verify(svc, _Args(task="t", scope="manual"))
        assert exc.value.code == 1
        assert "Verify (scope=manual, task=t)" in capsys.readouterr().out

    def test_both_surfaces_render_the_same_report(self, tmp_path, monkeypatch, capsys):
        from handlers import handle_tool
        from project_cli_verify import cmd_verify

        svc = self._svc(tmp_path)
        monkeypatch.setattr(svc, "run_verify_for_task", lambda *a, **k: self._report())
        mcp = handle_tool(svc, "tausik_verify", {"task_slug": "t", "scope": "manual"})
        cmd_verify(svc, _Args(task="t", scope="manual"))
        assert capsys.readouterr().out.rstrip("\n") == mcp


class _Args:
    """A stand-in for argparse's namespace: the CLI reads attributes, not a dict."""

    def __init__(self, **kw):
        self.__dict__.update(kw)

    def __getattr__(self, name):  # unset flags read as absent, as argparse does
        return None


class TestTheDetectorCanSayNo:
    """The calibration: what it must catch, and what it must NOT."""

    @staticmethod
    def _fn(src: str):
        import ast
        import textwrap

        return ast.parse(textwrap.dedent(src)).body[0]

    def test_rendering_the_result_is_caught(self):
        fn = self._fn(
            """
            def _do_thing(svc, args):
                rows = svc.list_things(args["slug"])
                return "\\n".join(f"{r['id']}: {r['title']}" for r in rows)
            """
        )
        assert renders_result(fn) is not None

    def test_an_f_string_alone_is_rendering(self):
        """Not every rendering goes through `join`.

        Added because a mutation that stopped treating f-strings as rendering
        survived: after the collapse, the three handlers still in the baseline
        all happen to render through `.join`, so the live tree no longer
        exercises this branch at all.
        """
        fn = self._fn(
            """
            def _do_thing(svc, args):
                row = svc.thing(args["slug"])
                return f"{row['slug']}: {row['title']}"
            """
        )
        assert renders_result(fn) == "row"

    def test_an_error_envelope_is_not_a_second_implementation(self):
        """`return f"Error: {e}"` serialises a failure. Every handler does it."""
        fn = self._fn(
            """
            def handle_thing(svc, args):
                try:
                    return svc.thing(args["slug"])
                except ValueError as e:
                    return f"Error: {e}"
            """
        )
        assert renders_result(fn) is None

    def test_formatting_an_argument_is_not_a_second_implementation(self):
        """A transport MAY read and shape `args` — that is its job."""
        fn = self._fn(
            """
            def _do_thing(svc, args):
                limit = int(args.get("limit", 10))
                return svc.thing(f"top-{limit}")
            """
        )
        assert renders_result(fn) is None

    def test_the_flow_is_followed_through_a_loop(self):
        """The rendering usually sits inside the loop, not beside the call."""
        fn = self._fn(
            """
            def _do_thing(svc, args):
                rows = svc.list_things()
                out = []
                for row in rows:
                    out.append(f"{row['slug']}")
                return "|".join(out)
            """
        )
        # WHICH name is named is incidental — the loop variable and the
        # accumulator are both results, and either answer means the same thing.
        assert renders_result(fn) is not None

    def test_joining_a_shared_renderer_s_lines_is_transport(self):
        """Stitching lines someone else built is not building them.

        A handler that must hold the result to wrap its errors was flagged for
        the join alone — the false positive that made this exception necessary.
        """
        fn = self._fn(
            """
            def _handle_thing(svc, args):
                try:
                    report = svc.run_thing()
                except ValueError as e:
                    return f"Error: {e}"
                return "\\n".join(thing_lines(svc, report))
            """
        )
        assert renders_result(fn, {"_handle_thing"}) is None

    def test_joining_a_LOCAL_helper_s_lines_is_still_a_second_implementation(self):
        """The hole the exception must not open: rendering behind a private helper."""
        fn = self._fn(
            """
            def _handle_thing(svc, args):
                report = svc.run_thing()
                return "\\n".join(_fmt(report))
            """
        )
        assert renders_result(fn, {"_handle_thing", "_fmt"}) is not None

    def test_passing_the_service_answer_through_is_transport(self):
        fn = self._fn(
            """
            def _do_thing(svc, args):
                return svc.thing(args["slug"], verbose=args.get("verbose", False))
            """
        )
        assert renders_result(fn) is None
