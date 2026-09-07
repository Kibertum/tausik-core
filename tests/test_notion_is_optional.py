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


_BOOTSTRAP = os.path.join(os.path.dirname(__file__), "..", "bootstrap")

#: Entry points through which a task is CLOSED. Named as call signatures, not
#: as files: the question is which module carries the responsibility today, and
#: a second module that starts answering it is found by the same search.
_CLOSE_ENTRY_POINTS = ("def task_done(", "def _task_done_report(")


def _session_start_carriers() -> set[str]:
    """Hook scripts registered to run at SessionStart, read from the generator.

    `bootstrap_hooks` IS the wiring — it is what writes the host settings — so
    a second SessionStart hook added there is picked up here without anyone
    remembering this test exists. Parsed with `ast` rather than matched with a
    regex: the registration is a literal dict, and reading it as one keeps a
    commented-out or string-formatted mention from counting as a hook.
    """
    path = os.path.join(_BOOTSTRAP, "bootstrap_hooks.py")
    tree = ast.parse(open(path, encoding="utf-8").read())
    out: set[str] = set()
    for node in ast.walk(tree):
        # The key is the event name; everything under it is that event's table.
        if not (isinstance(node, ast.Dict)):
            continue
        for key, value in zip(node.keys, node.values):
            if not (isinstance(key, ast.Constant) and key.value == "SessionStart"):
                continue
            for call in ast.walk(value):
                if (
                    isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Name)
                    and call.func.id == "hook_cmd"
                    and call.args
                    and isinstance(call.args[0], ast.Constant)
                ):
                    out.add(os.path.join("hooks", str(call.args[0].value)))
    return out


def _task_close_carriers() -> set[str]:
    """Modules that DEFINE a task-close entry point, found by searching for it.

    A second close path gets a definition of its own and is found here; it does
    not need to be added to a list, which is the hole this replaces.
    """
    out: set[str] = set()
    for name in sorted(os.listdir(_SCRIPTS)):
        if not name.endswith(".py"):
            continue
        text = _source(name)
        if any(sig in text for sig in _CLOSE_ENTRY_POINTS):
            out.add(name)
    return out


class TestTheAgentLoopSurvivesNotion:
    """AC1: a Notion failure never reaches the work.

    Three tests lived here that drove `_record_with_mirror` — proving the local
    write survived a failing mirror, and that the mirror could not raise into
    its caller. Decision #221 removed automatic mirroring entirely, so that
    function is gone and the property it guarded became STRUCTURAL: `record` has
    no outward path to fail. `test_decide_never_autopublishes.py` states the
    stronger version — nothing is published by recording, whatever the text.

    Removed rather than adapted, because a test kept alive against a deleted
    mechanism teaches the next reader that the mechanism still exists.
    """

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

    def test_closing_a_task_and_starting_a_session_do_not_touch_the_brain(self):
        """The subject is DERIVED from the live wiring, not typed out here.

        This used to be parametrized over ["service_task_done.py",
        "hooks/session_start.py"]. Renaming either was already caught loudly
        (the isfile assert below survives, for the same reason it was written:
        a skip turns a rename into a green test that checks nothing). What a
        list cannot catch is a NEW carrier of the same responsibility — a
        second close path, a second session-start hook — which simply is not on
        it, leaving the guard green and the hole open.

        WHY DIRECT CARRIERS AND NOT EVERYTHING THEY IMPORT. Measured before
        choosing: the transitive import closure from these two roots is 221 of
        419 modules, and 42 of them mention the brain already — `backend_crud`,
        `backend_schema`, the migrations. They mention it legitimately, because
        storing brain configuration is the storage layer's job. A guard stated
        over the closure would have been red on the day it was written, for
        reasons that have nothing to do with what it guards. The claim is about
        the module that would itself reach outward while closing work or
        starting a session, so that is what is collected.

        NAMED RESIDUAL: derivation reads the SessionStart registration and the
        definitions of the close entry points. A carrier wired dynamically —
        `importlib` by name, a hook a host adds through its own config — is not
        seen. That is a smaller blind spot than a hand-typed list, not the
        absence of one.
        """
        modules = sorted(_session_start_carriers() | _task_close_carriers())
        # A derivation that quietly collapses to nothing is the failure mode a
        # list does not have, so it is asserted before anything is scanned.
        assert len(modules) >= 2, (
            f"derived only {modules} — the SessionStart registration or the close "
            "entry points moved, and this guard now covers almost nothing"
        )
        for module in modules:
            path = os.path.join(_SCRIPTS, module)
            assert os.path.isfile(path), (
                f"{module} was derived but does not exist — the wiring and the tree "
                "disagree, and this guard cannot say which is right"
            )
            with open(path, encoding="utf-8") as fh:
                src = fh.read().lower()
            assert "brain" not in src, (
                f"{module} references the brain — the two paths that must never "
                "depend on a wiki are closing work and starting a session"
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
