"""Notion is optional, and this file is the proof rather than the promise.

Recon for kb-notion-publisher found that two of its three criteria were already
satisfied by the code — nothing in the agent loop fails when Notion does, and
the scrubber already sits on the publication boundary. What was missing was not
a mechanism but EVIDENCE: an unenforced property drifts, and this one is the
kind that drifts quietly, because breaking it produces no error at all — just a
decision that stopped being recorded.

So these tests are written against the ways the property could be lost, not
against the way it currently holds.
"""

from __future__ import annotations

import ast
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

CROSSCUTTING_SCOPE = [
    "scripts/service_decide.py",
    "scripts/brain_mcp_write.py",
    "scripts/project_cli_doctor.py",
]

_SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "scripts")


def _source(name: str) -> str:
    with open(os.path.join(_SCRIPTS, name), encoding="utf-8") as fh:
        return fh.read()


class TestTheAgentLoopSurvivesNotion:
    """AC1: a Notion failure never reaches the work.

    The local write is what must be unconditional. A test that merely watched a
    healthy run would pass whatever the ordering was, so the failure is injected
    and the ordering is asserted structurally as well.
    """

    def test_a_decision_is_recorded_locally_even_when_the_brain_write_explodes(
        self, tmp_path, monkeypatch
    ):
        """Drives `_record_with_mirror` directly, and asserts the mirror was TRIED.

        The first version of this test was green for the wrong reason and review
        caught it: `record()` only reaches the mirror when brain is enabled AND
        the target is "brain" AND the DB is a working project one. With the
        default config none of that holds, so the monkeypatched failure never
        fired — the decision survived because Notion was never attempted, which
        proves nothing about surviving Notion. The `except RuntimeError` was
        dead code catching an exception that could not occur.

        So the mirror path is entered on purpose, and a spy asserts it really
        was entered before the outcome is judged.
        """
        from types import SimpleNamespace

        import brain_config
        import brain_runtime
        import service_decide
        from project_backend import SQLiteBackend
        from project_service import ProjectService

        root = tmp_path / "proj"
        (root / ".tausik").mkdir(parents=True)
        monkeypatch.chdir(root)

        attempted: list[bool] = []

        def failing_mirror(*a, **k):
            attempted.append(True)
            return False, "Notion is down"

        # Both patched on their OWN modules: `_record_with_mirror` imports each
        # locally at call time, so patching the importer would miss.
        monkeypatch.setattr(brain_runtime, "try_brain_write_decision", failing_mirror)
        monkeypatch.setattr(brain_config, "validate_brain", lambda *a, **k: [])

        svc = ProjectService(SQLiteBackend(str(root / ".tausik" / "tausik.db")))
        try:
            out = service_decide._record_with_mirror(
                svc,
                "решение во время сбоя Notion",
                None,
                {"enabled": True},
                SimpleNamespace(reason="test", target="brain"),
            )
            assert attempted, "the mirror was never attempted — the test proves nothing"
            assert len(svc.decisions()) == 1, (
                "the decision was lost because the brain mirror failed — the local "
                "write is not unconditional"
            )
            assert "brain write failed" in out, "the failure was not reported to the caller"
        finally:
            svc.be.close()

    def test_the_mirror_really_cannot_raise_into_the_caller(self):
        """The contract `_record_with_mirror` relies on, checked rather than trusted.

        `try_brain_write_decision` promises "Never raises: caller falls back to
        local on False", and `_record_with_mirror` is written as if that holds —
        it calls the mirror BEFORE the local write and does not guard it. An
        earlier version of the test above injected a raising mirror and failed,
        which looked like a defect and was not: it was an impossible input.

        The honest test is therefore of the promise itself. If someone lets an
        exception escape that function, the local write becomes unreachable and
        decisions start vanishing on a network blip — so the wrapping is the
        thing to pin.
        """
        tree = ast.parse(_source("brain_runtime.py"))
        fn = next(
            n
            for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name == "try_brain_write_decision"
        )
        body = [s for s in fn.body if not isinstance(s, ast.Expr)]  # drop the docstring
        assert len(body) == 1 and isinstance(body[0], ast.Try), (
            "try_brain_write_decision is no longer a single wrapped block, so it can "
            "now raise into _record_with_mirror — where the local write comes AFTER it"
        )
        handlers = body[0].handlers
        assert any(h.type is None or getattr(h.type, "id", "") == "Exception" for h in handlers), (
            "the handler narrowed — some failures now escape to the caller"
        )

    def test_the_local_write_is_reached_unconditionally(self):
        """Structural: the mirror path ends in an UNGUARDED `write_local`.

        Injecting one failure proves one path; this proves the shape. The check
        is deliberately narrow — a `write_local` at the function body's TOP
        LEVEL, not merely somewhere inside it. My first draft flagged any
        occurrence inside any `if`, which is wrong: a branch that writes locally
        and returns is a complete, correct path, and the test failed on healthy
        code. What must hold is that after all the branching, the fall-through
        still writes.
        """
        tree = ast.parse(_source("service_decide.py"))
        funcs = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        target = funcs["_record_with_mirror"]

        top_level = [
            stmt
            for stmt in target.body
            if not isinstance(stmt, (ast.If, ast.Try, ast.For, ast.While))
            and any(
                isinstance(n, ast.Call) and getattr(n.func, "id", "") == "write_local"
                for n in ast.walk(stmt)
            )
        ]
        assert top_level, (
            "no unguarded write_local in _record_with_mirror — every call is nested, "
            "so the project's own copy now depends on some branch being taken"
        )

    def test_memory_add_does_not_reach_the_network(self):
        """The universality hint is a local heuristic, and so is what it delegates to.

        Scanning one file was not enough: `emit_universality_hint` calls into
        `brain_universality_semantic`, so a network call added there would have
        left this green while `memory add` gained a remote dependency. Review
        caught the gap; the chain is followed now.
        """
        modules = ["brain_universality.py"]
        chain = _source("brain_universality.py")
        for extra in ("brain_universality_semantic.py",):
            if extra[:-3] in chain:
                modules.append(extra)
        assert len(modules) > 1, (
            "the semantic delegate is no longer reached from the hint — either the "
            "chain changed or this guard has gone stale"
        )

        for module in modules:
            src = _source(module).lower()
            for banned in (
                "import urllib",
                "import requests",
                "http://",
                "https://",
                "pages_create",
            ):
                assert banned not in src, (
                    f"{banned} appeared in {module} — memory add would then depend on "
                    "a remote service"
                )

    @pytest.mark.parametrize("module", ["service_task_done.py", "hooks/session_start.py"])
    def test_closing_a_task_and_starting_a_session_do_not_touch_the_brain(self, module):
        path = os.path.join(_SCRIPTS, module)
        # Asserted, not skipped. A skip here would turn a rename into a silent
        # loss of coverage: the test stays green while checking nothing, which
        # is worse than not having it, because it also reports that it looked.
        assert os.path.isfile(path), (
            f"{module} no longer exists — this guard now covers nothing. Point it at "
            "the file that closes tasks / starts sessions today."
        )
        with open(path, encoding="utf-8") as fh:
            src = fh.read().lower()
        assert "brain" not in src, (
            f"{module} references the brain — the two paths that must never depend "
            "on a wiki are closing work and starting a session"
        )


class TestTheScrubberGuardsEveryRouteOutward:
    """AC2: stated as a PROPERTY, because a list of call sites goes stale in silence.

    The guarantee is not "these four callers scrub". It is "the single function
    that talks to Notion scrubs, and it is the only one that talks to Notion".
    """

    def test_no_content_reaches_notion_outside_the_scrubbed_funnel(self):
        """Every CONTENT write goes through `store_record`, and the exceptions are named.

        Two corrections to an earlier version of this test, both found by review.
        It scanned `os.listdir(scripts)` — one directory, not a tree — so
        `scripts/hooks/`, `scripts/providers/` and all of `harness/` were blind
        spots. And it matched only `pages_create`, while the client also exposes
        `pages_update` and `databases_create`.

        With those fixed the original claim turned out to be FALSE: two callers
        do reach Notion outside the funnel. Neither carries user text — one
        archives a page by id, the other creates empty databases during setup —
        so the honest property is not "nothing writes" but "nothing writes
        CONTENT". They are listed with their reason, which means a THIRD caller,
        or a change of purpose in these two, fails this test.
        """
        write_methods = ("pages_create(", "pages_update(", "databases_create(")
        funnel = {"brain_mcp_write.py", "brain_notion_client.py"}
        allowed = {
            # Archives an existing page by id — sends `archived=True`, no text.
            ("brain_move.py", "pages_update("),
            # Creates the empty databases during setup — schema, no records.
            ("brain_init_schemas.py", "databases_create("),
        }

        offenders: list[str] = []
        for root_dir in (_SCRIPTS, os.path.join(os.path.dirname(__file__), "..", "harness")):
            for dirpath, _dirs, files in os.walk(root_dir):
                for name in files:
                    if not name.endswith(".py") or name in funnel:
                        continue
                    with open(os.path.join(dirpath, name), encoding="utf-8") as fh:
                        text = fh.read()
                    for method in write_methods:
                        # `client.<method>` only — a docstring mentioning the name
                        # is not a call, and several setup modules describe them.
                        if f".{method}" in text and (name, method) not in allowed:
                            offenders.append(f"{name}:{method}")

        assert offenders == [], (
            f"{sorted(set(offenders))} write to Notion outside store_record, so they "
            "bypass the scrubber. Route them through it, or — if the call carries no "
            "user content — add it to `allowed` WITH THE REASON, so the exception is "
            "auditable instead of assumed"
        )

    def test_a_blocked_scrub_RETURNS_before_the_write(self):
        """Structure, not text order — the difference is a leak that ships.

        The first version compared the positions of the substrings
        "scrub_blocked" and "pages_create". Review pointed out what that misses:
        drop the `return` and leave the dict literal behind, and execution falls
        through to the request while the strings stay in the same order. The
        test would be green on a run that DETECTED a leak and sent it anyway —
        worse than never looking, because someone would trust it.

        So: find the `if` that reacts to the scrub result, and require an actual
        `Return` inside it, positioned before the write call.
        """
        tree = ast.parse(_source("brain_mcp_write.py"))
        fn = next(
            n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "store_record"
        )

        scrub_calls = [
            n
            for n in ast.walk(fn)
            if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "scrub_inputs"
        ]
        assert scrub_calls, "store_record no longer scrubs at all"

        writes = [
            n
            for n in ast.walk(fn)
            if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "pages_create"
        ]
        assert writes, "store_record no longer writes — this guard is blind"
        assert scrub_calls[0].lineno < writes[0].lineno, (
            "the scrubber runs AFTER the write — it redacts nothing"
        )

        guarded_returns = [
            ret
            for node in ast.walk(fn)
            if isinstance(node, ast.If)
            for ret in ast.walk(node)
            if isinstance(ret, ast.Return)
            and ret.lineno > scrub_calls[0].lineno
            and ret.lineno < writes[0].lineno
        ]
        assert guarded_returns, (
            "nothing RETURNS between the scrub and the write — a blocked scrub would "
            "fall through and publish the very content it flagged"
        )


class TestDoctorDoesNotMakeAnOptionalSubsystemMandatory:
    """AC3 — the one place Notion was genuinely required, and both halves of the fix."""

    def _requirement(self, monkeypatch, *, config_raises: bool, enabled: bool = False):
        import project_cli_doctor as doc
        import project_config

        if config_raises:
            monkeypatch.setattr(
                project_config,
                "load_config",
                lambda *a, **k: (_ for _ in ()).throw(ValueError("broken json")),
            )
        else:
            monkeypatch.setattr(
                project_config, "load_config", lambda *a, **k: {"brain": {"enabled": enabled}}
            )
        return doc.brain_skill_requirement()

    def test_an_unreadable_config_no_longer_demands_the_brain_skill(self, monkeypatch):
        """The regression: a fresh project failing its doctor over a wiki it never used."""
        critical, undetermined = self._requirement(monkeypatch, config_raises=True)
        assert critical is False, (
            "an unreadable config still makes the opt-in brain skill mandatory"
        )
        assert undetermined is True, (
            "relaxing the requirement without saying so is how a check stops existing"
        )

    def test_an_enabled_brain_still_requires_the_skill(self, monkeypatch):
        """The other half: the check must not have been softened into uselessness."""
        critical, undetermined = self._requirement(monkeypatch, config_raises=False, enabled=True)
        assert critical is True
        assert undetermined is False

    def test_a_disabled_brain_does_not_require_it(self, monkeypatch):
        critical, undetermined = self._requirement(monkeypatch, config_raises=False, enabled=False)
        assert critical is False
        assert undetermined is False, "a readable config must not claim uncertainty"

    @pytest.mark.parametrize("value", [True, False, "enabled", 1, ["yes"]])
    def test_a_brain_key_that_is_not_a_mapping_does_not_crash_the_doctor(self, monkeypatch, value):
        """`{"brain": true}` is an ordinary typo — valid JSON, no exception from
        the loader — and it used to reach `.get()` on a bool and crash the whole
        health check through a call `cmd_doctor` does not guard.

        A doctor that dies on a malformed config is worse than one that misjudges
        it: it reports nothing at all, including the twelve checks that had
        already passed. So a non-mapping is treated as off AND flagged as
        undetermined, since something was clearly meant by it.
        """
        import project_cli_doctor as doc
        import project_config

        monkeypatch.setattr(project_config, "load_config", lambda *a, **k: {"brain": value})
        critical, undetermined = doc.brain_skill_requirement()
        assert critical is False
        assert undetermined is True, (
            "a brain key nobody can interpret was silently treated as a definite 'off'"
        )

    def test_an_absent_brain_key_is_a_definite_off_not_uncertainty(self, monkeypatch):
        """No key at all is the default state, not a puzzle — warning here would nag."""
        import project_cli_doctor as doc
        import project_config

        monkeypatch.setattr(project_config, "load_config", lambda *a, **k: {})
        assert doc.brain_skill_requirement() == (False, False)

    def test_the_warning_branch_does_not_count_as_a_failure(self):
        """The bug that survived four unit tests, because none of them ran the caller.

        Inserting the warning block stole the `failures += 1` that belonged to
        the "missing critical skills" branch. Two inversions at once: missing
        skills stopped failing the check, and an unreadable config STARTED
        failing it — the exact opposite of what the message in that same block
        promises, and of the criterion this task exists to fix.

        Testing the extracted pure function proved the rule and said nothing
        about its use. This reads the caller's structure: the counter must live
        with the FAIL branch, never inside the warning.
        """
        tree = ast.parse(_source("project_cli_doctor.py"))
        cmd = next(
            n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "cmd_doctor"
        )

        def increments_failures(node) -> bool:
            return any(
                isinstance(sub, ast.AugAssign)
                and isinstance(sub.target, ast.Name)
                and sub.target.id == "failures"
                for sub in ast.walk(node)
            )

        warn_blocks = [
            n
            for n in ast.walk(cmd)
            if isinstance(n, ast.If)
            and isinstance(n.test, ast.Name)
            and n.test.id == "brain_undetermined"
        ]
        assert warn_blocks, "the undetermined branch disappeared — this guard is now blind"
        for block in warn_blocks:
            assert not increments_failures(block), (
                "the undetermined-config warning increments `failures`, so doctor exits 1 "
                "for a project that merely has an unreadable config — contradicting the "
                "message printed in that very block"
            )

    def test_missing_critical_skills_still_fail_the_check(self):
        """The other half of the same slip, and the one that breaks CI silently.

        A doctor that prints FAIL and exits 0 is worse than one that does not
        check: the pipeline goes green on a broken install.
        """
        tree = ast.parse(_source("project_cli_doctor.py"))
        cmd = next(
            n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "cmd_doctor"
        )
        for node in ast.walk(cmd):
            if not isinstance(node, ast.If):
                continue
            calls_fail = any(
                isinstance(sub, ast.Call)
                and getattr(sub.func, "id", "") == "_print_fail"
                and sub.args
                and isinstance(sub.args[0], ast.Constant)
                and sub.args[0].value == "Core skills"
                for sub in ast.walk(node)
            )
            if not calls_fail:
                continue
            branch = node.orelse or node.body
            assert any(
                isinstance(sub, ast.AugAssign)
                and isinstance(sub.target, ast.Name)
                and sub.target.id == "failures"
                for stmt in branch
                for sub in ast.walk(stmt)
            ), "the missing-critical-skills branch prints FAIL without counting it"
            return
        raise AssertionError("no Core skills FAIL branch found — this guard is blind")

    def test_the_caller_actually_reads_the_uncertainty_flag(self):
        """The flag is only worth returning if something ACTS on it.

        A substring search was the first attempt and it was green for the wrong
        reason: replacing `if brain_undetermined:` with `if False:` left the name
        behind at its assignment, so the grep still found it while the warning
        had stopped being reachable. The AST distinguishes a name that is READ
        from one that is merely written, which is the property in question.
        """
        tree = ast.parse(_source("project_cli_doctor.py"))
        cmd = next(
            n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "cmd_doctor"
        )
        loads = [
            n
            for n in ast.walk(cmd)
            if isinstance(n, ast.Name)
            and n.id == "brain_undetermined"
            and isinstance(n.ctx, ast.Load)
        ]
        assert loads, (
            "cmd_doctor assigns the undetermined flag but never reads it — the "
            "warning is unreachable and the uncertainty is silent again"
        )
        assert "could not tell whether brain is enabled" in _source("project_cli_doctor.py")
