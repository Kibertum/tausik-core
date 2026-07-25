"""A remediation must name a command that exists, with flags that exist.

verify-warn-names-a-flag-verify-does-not-have. `tausik verify --task X` over an
empty scope printed "Pass --relevant-files for verification" — and `verify` had
no such flag. The only working move (`task update --relevant-files`) was named
nowhere. Ignoring the warning was therefore the RATIONAL response: the one
instruction on offer could not be carried out.

The tests here do not compare the message to an expected string — that pins the
wording and proves nothing about whether it works. They extract the command out
of the message and ask the real argparse parser whether it would accept it.
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

# `tausik <cmd> ...` inside backticks — how every remediation in the framework
# spells an instruction.
_COMMAND_IN_BACKTICKS = re.compile(r"`([^`]+)`")


def _build_parser() -> argparse.ArgumentParser:
    """The real top-level parser, with every subcommand registered."""
    from project_parser import build_parser

    return build_parser()


def _suggested_commands(message: str) -> list[list[str]]:
    """Every backticked command in `message`, as argv WITHOUT the CLI name.

    Placeholders (`<slug>`, `<paths...>`) are replaced with plausible values —
    the question is whether the FLAGS parse, not whether the slug exists.
    """
    out = []
    for raw in _COMMAND_IN_BACKTICKS.findall(message):
        text = raw.replace("<paths...>", "a.py b.py").replace("<slug>", "some-task")
        text = re.sub(r"<[^>]+>", "x", text)
        argv = shlex.split(text, posix=False)
        if not argv:
            continue
        # Drop the CLI invocation itself (`.tausik/tausik`, `.tausik\tausik`).
        out.append([a.strip('"') for a in argv[1:]])
    return out


def _parses(argv: list[str]) -> bool:
    parser = _build_parser()
    try:
        parser.parse_args(argv)
    except SystemExit:
        return False
    return True


class TestVerifyHasTheFlagItsMessagesName:
    def test_verify_accepts_relevant_files(self):
        """AC-2: the CLAUDE.md chain must be executable literally."""
        assert _parses(["verify", "--task", "some-task", "--relevant-files", "a.py", "b.py"])

    def test_the_empty_scope_warning_suggests_only_runnable_commands(self):
        """The WARN written into task notes by a scope-less verify."""
        import verify_cached_run as vcr

        message = (
            "WARN: no relevant_files passed — scoped gates SKIPPED. "
            "v1.3 removed full-suite fallback. Declare the scope: "
            f"`{vcr._CLI} verify --task some-task --relevant-files <paths...>` "
            f"(or `{vcr._CLI} task update some-task --relevant-files <paths...>` "
            "first). This receipt certifies nothing until you do."
        )
        suggestions = _suggested_commands(message)
        assert suggestions, "the warning names no command at all"
        for argv in suggestions:
            assert _parses(argv), f"warning suggests an unparseable command: {argv}"

    def test_the_gate_skip_reason_suggests_a_runnable_command(self):
        """The SKIP reason `run_gates` records when no scope was passed."""
        import gate_runner

        monkey_free_message = (
            "No relevant_files passed; gate skipped. Declare the "
            f"scope: `{gate_runner._CLI} verify --task <slug> --relevant-files "
            "<paths...>`."
        )
        suggestions = _suggested_commands(monkey_free_message)
        assert suggestions
        for argv in suggestions:
            assert _parses(argv), f"skip reason suggests an unparseable command: {argv}"

    def test_the_messages_in_the_source_are_the_ones_tested(self):
        """Guard against the tests above drifting from the real strings.

        Both messages are built inline in their modules, so the only honest way
        to keep this pair honest is to assert the distinctive fragment is still
        present in the source that emits it.
        """
        import inspect

        import gate_runner
        import verify_cached_run

        assert "--relevant-files" in inspect.getsource(verify_cached_run)
        assert "verify --task" in inspect.getsource(verify_cached_run)
        assert "verify --task" in inspect.getsource(gate_runner)


class TestScopeDeclarationIsRejectedWhenItCannotBeRecorded:
    def _args(self, **kw):
        ns = argparse.Namespace(
            task=None, scope="manual", no_tests_expected=False, relevant_files=None
        )
        for k, v in kw.items():
            setattr(ns, k, v)
        return ns

    def test_relevant_files_without_task_is_an_explicit_error(self, capsys):
        """Silently ignoring it would leave the caller thinking scope was set."""
        from project_cli_verify import cmd_verify

        with pytest.raises(SystemExit) as exc:
            cmd_verify(object(), self._args(relevant_files=["a.py"]))
        assert exc.value.code == 2
        assert "--task" in capsys.readouterr().out

    def test_an_empty_list_does_not_wipe_a_declared_scope(self, capsys):
        """A glob that matched nothing must not silently unscope the task.

        Wiping would put the task back in the state this whole task exists to
        remove — verified, signed, and covering nothing.
        """
        from project_cli_verify import cmd_verify

        class _Svc:
            updated: list = []

            def task_update(self, slug, **fields):
                self.updated.append((slug, fields))
                return "ok"

            def run_verify_for_task(self, *a, **k):
                raise SystemExit(0)  # stop before the gate run; scope is the subject

        svc = _Svc()
        with pytest.raises(SystemExit):
            cmd_verify(svc, self._args(task="some-task", relevant_files=[]))
        assert svc.updated == [], "an empty --relevant-files must not write anything"
        assert "keeping the scope" in capsys.readouterr().out


@pytest.mark.verify_first
class TestADeclarationSurvivesABlockedClose:
    """AC-4: `task done --relevant-files` used to throw the declaration away.

    The scope was written inside the `status=done` transaction, so a close
    blocked by Verify-First left the task exactly as unscoped as before. The
    agent was then told to run `verify`, which read the still-empty scope,
    skipped every gate, and signed a receipt that certified nothing. Neither
    command could get the task out of the state the other one required.
    """

    def _task(self, tmp_path):
        from project_backend import SQLiteBackend
        from project_service import ProjectService

        svc = ProjectService(SQLiteBackend(str(tmp_path / "t.db")))
        svc.epic_add("e", "E")
        svc.story_add("e", "s", "S")
        svc.task_add("s", "t", "Implement X", goal="Implement X", role="developer")
        svc.task_update("t", acceptance_criteria="1. X works\n2. Errors on invalid input")
        svc.task_start("t")
        svc.task_log("t", "AC verified: 1. X works ✓ 2. Errors on invalid input ✓")
        return svc

    def _close(self, svc, files):
        from unittest.mock import MagicMock, patch

        with patch.dict(
            "sys.modules",
            {"gate_runner": MagicMock(run_gates=MagicMock(return_value=(True, [])))},
        ):
            return svc._task_done_report(
                "t",
                relevant_files=files,
                ac_verified=True,
                no_knowledge=False,
                evidence=None,
            )

    def test_the_scope_is_recorded_even_when_the_close_is_blocked(self, tmp_path, monkeypatch):
        import json

        monkeypatch.setattr("project_config.load_config", lambda *a, **k: {})
        svc = self._task(tmp_path)
        try:
            report = self._close(svc, ["scripts/x.py", "tests/test_x.py"])
            assert report["ok"] is False, "expected Verify-First to block this close"
            stored = json.loads(svc.be.task_get("t")["relevant_files"] or "[]")
            assert stored == ["scripts/x.py", "tests/test_x.py"]
        finally:
            svc.be.close()

    def test_a_blocked_close_does_not_mark_the_task_done(self, tmp_path, monkeypatch):
        """Recording a declaration must not leak into recording an outcome."""
        monkeypatch.setattr("project_config.load_config", lambda *a, **k: {})
        svc = self._task(tmp_path)
        try:
            self._close(svc, ["scripts/x.py"])
            task = svc.be.task_get("t")
            assert task["status"] == "active"
            assert task["completed_at"] in (None, "")
        finally:
            svc.be.close()


class TestAnAlreadyDoneTaskScopeIsNotRewritten:
    """A close that FAILS must not have written anything first.

    persist_declared_scope used to run before the `status == 'done'` guard, so
    `task done <done-slug> --relevant-files X` overwrote the closed task's scope
    — the scope that fed its risk_score, verify-cache hash and receipt — and
    only THEN raised 'already done'. The caller saw the error; the certified row
    was already corrupted. The guard now fires before any write.
    """

    def _done_task(self, tmp_path):
        from project_backend import SQLiteBackend
        from project_service import ProjectService

        svc = ProjectService(SQLiteBackend(str(tmp_path / "t.db")))
        svc.epic_add("e", "E")
        svc.story_add("e", "s", "S")
        svc.task_add("s", "t", "Implement X", goal="Implement X", role="developer")
        svc.task_update("t", acceptance_criteria="1. X works\n2. Errors on invalid input")
        # Force the closed, certified end-state directly — the point under test is
        # what happens to a row that is ALREADY done, not how it got there.
        import json

        svc.be.task_update(
            "t",
            status="done",
            relevant_files=json.dumps(["scripts/original.py", "tests/test_original.py"]),
        )
        return svc

    def test_reclosing_with_different_files_neither_mutates_nor_succeeds(
        self, tmp_path, monkeypatch
    ):
        import json

        from tausik_utils import ServiceError

        monkeypatch.setattr("project_config.load_config", lambda *a, **k: {})
        svc = self._done_task(tmp_path)
        before = svc.be.task_get("t")["relevant_files"]
        try:
            with pytest.raises(ServiceError, match="already done"):
                svc._task_done_report(
                    "t",
                    relevant_files=["scripts/attacker.py"],
                    ac_verified=True,
                    no_knowledge=False,
                    evidence=None,
                )
            after = svc.be.task_get("t")["relevant_files"]
            assert after == before, "an already-done task's scope must survive a failed re-close"
            assert json.loads(after) == ["scripts/original.py", "tests/test_original.py"]
        finally:
            svc.be.close()
