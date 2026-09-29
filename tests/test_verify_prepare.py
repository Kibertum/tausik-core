"""Preparation runs inside the check, and a failed preparation never becomes a green.

THE MEASUREMENT. Two gates go red for reasons known before the run and fixed by a fixed
command: `ruff_format` until `ruff format` has run, `bootstrap_drift` after any edit under
`scripts/` until the profile is redeployed. Neither is a judgement, and each cost its own
call — about a million tokens per task at the project's measured 482 000 tokens of prefix
re-sent per call, against roughly 400 closures a month.

AND WHAT IT MUST NOT TOUCH. The first version ran `ruff format .` and rewrote 90 files on
its first real use, including ones deliberately held on the `ruff_format.legacy_unformatted`
list — a ratchet that only shrinks, quietly emptied by a convenience. So a step that takes
files gets the declared scope and nothing else, and is skipped OUT LOUD when there is none.

WHAT THESE TESTS GUARD IS THE MEANING OF GREEN. Preparation changes the tree the gates are
about to judge, so the dangerous failure is not a crash — it is a green produced over a
tree the agent believed was prepared and was not. Hence the negative half: a failed step
stops the run before any gate looks at anything, and the step list stays closed to
anything that would need judgement.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import verify_prepare as prep  # noqa: E402


def _runner(*, code=0, out="", err=""):
    """A recording stand-in for subprocess.run."""
    calls: list[list[str]] = []

    def run(argv, **kw):
        calls.append(list(argv))
        return subprocess.CompletedProcess(argv, code, out, err)

    run.calls = calls  # type: ignore[attr-defined]
    return run


class TestTheStepsAreDataAndStayClosed:
    def test_every_step_names_a_command_and_the_gate_it_answers(self):
        """AC-5. Assembling the list per run is how something that needs judgement gets in
        by looking convenient at the time; reading it as data is what lets a test refuse."""
        assert prep.STEPS, "an empty list would make --prepare a silent no-op"
        for step in prep.STEPS:
            assert step.argv, f"{step.name} runs nothing"
            assert len(step.because) > 40, f"{step.name} does not say why it is here"

    def test_the_list_is_exactly_formatting_and_redeployment(self):
        """Both operations produce a result that does not depend on what the code MEANS.
        A third kind would be a decision laundered through a flag, so this fails on one."""
        names = [s.name for s in prep.STEPS]
        assert names == ["ruff format", "bootstrap redeploy"], (
            "preparation is deterministic by definition; anything else belongs in a task, "
            f"not in a flag — found {names}"
        )

    def test_the_steps_cannot_be_edited_through_the_returned_objects(self):
        with pytest.raises(AttributeError):
            prep.STEPS[0].name = "something else"  # type: ignore[misc]


class TestAGreenIsNeverProducedOverAnUnpreparedTree:
    def test_a_failing_step_stops_the_run_and_carries_its_output(self):
        """NEGATIVE, AC-3. Going on would run the gates over a tree the caller believes was
        prepared and was not — and that green says the opposite of what it seems to."""
        run = _runner(code=1, err="ruff: cannot parse x.py")
        with pytest.raises(prep.PreparationFailed) as exc:
            prep.run(".", ["a.py"], runner=run)
        assert "ruff: cannot parse x.py" in str(exc.value)
        assert "NOT run" in str(exc.value), "the refusal says no gate looked at anything"
        assert len(run.calls) == 1, "it stopped at the first failure, not after all of them"  # type: ignore[attr-defined]

    def test_a_file_taking_step_is_given_the_declared_scope_and_nothing_else(self):
        """The whole lesson of the first run: `ruff format .` rewrote 90 files, among them
        ones the legacy ratchet holds unformatted on purpose."""
        run = _runner()
        prep.run(".", ["a.py", "b.py"], runner=run)
        assert run.calls[0] == ["ruff", "format", "a.py", "b.py"]  # type: ignore[attr-defined]
        assert "." not in run.calls[0][2:], "no tree-wide target sneaks in"  # type: ignore[attr-defined]

    def test_with_no_declared_scope_that_step_is_skipped_and_says_so(self):
        """NEGATIVE. Running it tree-wide instead would edit files nobody declared — Rule 2
        by another route — and skipping it in silence reads exactly like success."""
        run = _runner()
        said = prep.run(".", [], runner=run)
        assert said[0].startswith("NOT PREPARED: ruff format")
        assert all(c[:2] != ["ruff", "format"] for c in run.calls)  # type: ignore[attr-defined]
        assert len(run.calls) == 1, "the step that needs no files still ran"  # type: ignore[attr-defined]

    def test_the_steps_run_in_order(self):
        """Redeploying before formatting would deploy the unformatted copies, and the drift
        gate would then be red about exactly the files the formatter was about to change."""
        run = _runner()
        prep.run(".", ["a.py"], runner=run)
        argv = run.calls  # type: ignore[attr-defined]
        assert argv[0][:2] == ["ruff", "format"]
        assert "bootstrap.py" in " ".join(argv[1])

    def test_every_step_is_reported_by_name(self):
        """AC-2. Preparation changed the tree the gates then judged; a green that did not
        say so would quietly mean something narrower than a green without it."""
        said = prep.run(".", ["a.py"], runner=_runner(out="3 files reformatted"))
        assert len(said) == len(prep.STEPS)
        assert all(line.startswith("PREPARED: ") for line in said)
        assert "3 files reformatted" in said[0]

    def test_a_silent_step_still_reports_itself(self):
        """A command that prints nothing succeeded quietly; reporting nothing for it would
        read as though it had been skipped."""
        said = prep.run(".", ["a.py"], runner=_runner(out=""))
        assert said[0].endswith("ok")


class TestPreparationIsTheDefaultRatherThanAFlag:
    """It shipped behind `--prepare` first, and nothing ever named that flag — no skill, no
    CLAUDE.md line, no hint. This project has measured what a rule that is only ASKED for is
    worth: switched off the same week. A flag is weaker, because nobody even asks."""

    @staticmethod
    def _parsed(*argv):
        import argparse

        from project_parser_verify import add_verify_parsers

        parser = argparse.ArgumentParser()
        add_verify_parsers(parser.add_subparsers(dest="cmd"))
        return parser.parse_args(["verify", *argv])

    def test_opting_out_is_the_flag_now(self):
        """AC-1 and AC-2: nothing has to be remembered to get preparation."""
        assert self._parsed("--task", "t").no_prepare is False
        assert self._parsed("--task", "t", "--no-prepare").no_prepare is True

    def test_the_old_flag_is_still_accepted(self):
        """AC-6. A caller that already types it must not start failing."""
        assert self._parsed("--task", "t", "--prepare").prepare is True

    def test_the_handler_branches_on_the_opt_out_not_on_the_opt_in(self):
        text = (_REPO / "scripts" / "project_cli_verify.py").read_text(encoding="utf-8")
        assert 'if getattr(args, "no_prepare", False):' in text
        assert 'if getattr(args, "prepare", False):' not in text, "the opt-in gate is gone"

    def test_preparation_still_happens_before_anything_is_judged(self):
        text = (_REPO / "scripts" / "project_cli_verify.py").read_text(encoding="utf-8")
        assert text.index('if getattr(args, "no_prepare", False):') < text.index(
            "report = svc.run_verify_for_task("
        )

    @pytest.mark.parametrize(
        ("needle", "why"),
        [
            ("PREPARATION SKIPPED by --no-prepare", "the caller asked for it"),
            ("PREPARATION SKIPPED: no --task", "there is no declared scope to format"),
        ],
    )
    def test_every_skip_says_itself(self, needle, why):
        """AC-4 and AC-5. Silence about a skip reads exactly like "it ran", and the whole
        value of the default is that the reader knows which tree was judged."""
        text = (_REPO / "scripts" / "project_cli_verify.py").read_text(encoding="utf-8")
        assert needle in text, why

    def test_a_service_that_names_no_root_does_not_prepare_anything(self):
        """NEGATIVE. Preparation WRITES, so it must act on the project the service speaks
        for and no other. A fallback to the process's current directory made a verify held
        by a temporary service reformat and redeploy the LIVE tree — the suite's own guard
        caught it by the config file changing underneath 281 tests."""
        text = (_REPO / "scripts" / "project_cli_verify.py").read_text(encoding="utf-8")
        assert 'root_from_service(svc) or "."' not in text, "the cwd fallback is gone"
        assert "PREPARATION SKIPPED: this service names no project root" in text

    def test_a_run_without_a_task_does_not_format_the_tree(self):
        """NEGATIVE, AC-4. No task means no declared scope, and a tree-wide `ruff format`
        is what rewrote 90 files the first time this existed."""
        text = (_REPO / "scripts" / "project_cli_verify.py").read_text(encoding="utf-8")
        branch = text[text.index("elif not task_slug:") :]
        branch = branch[: branch.index("else:")]
        assert "run_preparation" not in branch
