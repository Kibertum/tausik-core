"""The call budget is advice interactively and a ceiling in an unattended run.

THE MULTIPLIER IS MEASURED, not borrowed from the project this idea came from. Over 651
closures carrying both a budget and an actual: median ratio 0.58 — the usual task lands
under two thirds of its estimate — p75 0.93, p90 1.60, p99 5.80, worst 47.5. Past 1.5x
sits 11% of closures, past 2x 8%, past 2.5x 4%, past 3x 3%. The warning keeps 1.5x; the
refusal takes 2x, where an overrun stops being calibration noise.

THE NEGATIVE HALF IS WHAT MAKES IT SAFE TO SHIP. Unarmed, nothing here can refuse
anything, at any overrun — interactive work must not change by a character. A task with no
declared budget cannot breach: absence of a budget is not a budget of zero, and treating it
as one would refuse every task nobody estimated.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import call_budget_guard as guard  # noqa: E402

ARMED = {guard.ARM_ENV: "1"}


def task(budget=40, actual=100, slug="t"):
    return {"slug": slug, "call_budget": budget, "call_actual": actual}


class TestUnarmedNeverRefuses:
    @pytest.mark.parametrize("actual", [41, 100, 4000, 400_000])
    def test_no_overrun_is_a_refusal_without_the_flag(self, actual):
        """Interactive work does not change, at any overrun. This is the whole guarantee."""
        assert guard.breach(task(actual=actual), {}) == ""

    @pytest.mark.parametrize("value", ["", "0", "false", "FALSE", "no", "off", " "])
    def test_a_falsy_looking_flag_does_not_arm(self, value):
        """`=0` and `=false` mean what a reader expects.

        A flag that armed on the string "false" would be a trap in a shell script, and
        this check exists because that trap is easy to ship by accident.
        """
        assert not guard.is_armed({guard.ARM_ENV: value})
        assert guard.breach(task(actual=4000), {guard.ARM_ENV: value}) == ""

    @pytest.mark.parametrize("value", ["1", "true", "yes", "on", "block"])
    def test_anything_else_arms(self, value):
        assert guard.is_armed({guard.ARM_ENV: value})


class TestArmedRefusesOnlyPastTheCeiling:
    @pytest.mark.parametrize(
        ("budget", "actual"),
        [(40, 40), (40, 60), (40, 79), (40, 80), (100, 200), (3, 6)],
    )
    def test_within_the_ceiling_is_silent(self, budget, actual):
        """2x inclusive is still inside: the refusal fires PAST the ceiling, not at it."""
        assert guard.breach(task(budget, actual), ARMED) == ""

    @pytest.mark.parametrize(("budget", "actual"), [(40, 81), (40, 106), (70, 141), (3, 7)])
    def test_past_the_ceiling_refuses(self, budget, actual):
        assert guard.breach(task(budget, actual), ARMED)

    def test_the_refusal_names_the_three_numbers_and_a_way_out(self):
        """A stop that does not say what to change gets worked around, not obeyed."""
        text = guard.breach(task(40, 106, slug="my-task"), ARMED)
        assert "my-task" in text
        assert "106" in text and "40" in text
        assert "2.6×" in text
        assert "разбейте задачу" in text or "Пересчитайте бюджет" in text


class TestAMissingBudgetIsNotAZeroBudget:
    @pytest.mark.parametrize(
        "task_dict",
        [
            pytest.param({"slug": "t", "call_actual": 900}, id="no_budget_key"),
            pytest.param({"slug": "t", "call_budget": None, "call_actual": 900}, id="budget_none"),
            pytest.param({"slug": "t", "call_budget": 0, "call_actual": 900}, id="budget_zero"),
            pytest.param(
                {"slug": "t", "call_budget": "40", "call_actual": 900}, id="budget_string"
            ),
        ],
    )
    def test_an_unestimated_task_cannot_breach(self, task_dict):
        assert guard.overrun(task_dict) is None
        assert guard.breach(task_dict, ARMED) == ""

    @pytest.mark.parametrize(
        "task_dict",
        [
            pytest.param({"slug": "t", "call_budget": 40}, id="no_actual"),
            pytest.param({"slug": "t", "call_budget": 40, "call_actual": None}, id="actual_none"),
            pytest.param({"slug": "t", "call_budget": 40, "call_actual": -1}, id="actual_negative"),
        ],
    )
    def test_a_task_with_no_measurement_cannot_breach(self, task_dict):
        assert guard.overrun(task_dict) is None
        assert guard.breach(task_dict, ARMED) == ""


class TestTheGuardCannotBreakACloseOrItself:
    def test_a_hostile_task_dict_is_silent(self):
        """A guard that raises is worse than one that misses: it stops the close."""

        class Hostile(dict):
            def get(self, *_a, **_k):
                raise RuntimeError("boom")

        assert guard.breach(Hostile(), ARMED) == ""

    def test_the_two_thresholds_are_read_side_by_side(self):
        """Both numbers live in one module so a reader compares them without hunting."""
        assert guard.WARN_MULTIPLIER == 1.5
        assert guard.BLOCK_MULTIPLIER == 2.0
        assert guard.WARN_MULTIPLIER < guard.BLOCK_MULTIPLIER


class TestTheDriverCanAskWithAnExitCode:
    """A printed warning is invisible to `&&`. The answer has to be an exit code."""

    def _run(self, slug, armed):
        import os

        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        env.pop(guard.ARM_ENV, None)
        if armed:
            env[guard.ARM_ENV] = "1"
        return subprocess.run(
            [sys.executable, str(_REPO / "scripts" / "project.py"), "task", "budget-check", slug],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            cwd=str(_REPO),
        )

    def test_a_breaching_task_exits_nonzero_only_when_armed(self):
        """Measured on a real closure: 106 calls against a budget of 40 is 2.6x."""
        slug = "is-code-needed-at-all-before-writing-it"
        armed = self._run(slug, armed=True)
        assert armed.returncode == 1, (armed.stdout, armed.stderr)
        assert "ПОТОЛОК ВЫЗОВОВ" in armed.stderr
        unarmed = self._run(slug, armed=False)
        assert unarmed.returncode == 0
        assert unarmed.stdout.strip() == "" and "ПОТОЛОК" not in unarmed.stderr

    def test_a_task_within_the_ceiling_is_silent_and_zero_even_armed(self):
        """1.77x on a real closure — inside the ceiling, so nothing is printed."""
        proc = self._run("683-structurally-identical-tests-in-294-groups", armed=True)
        assert proc.returncode == 0
        assert "ПОТОЛОК" not in (proc.stdout + proc.stderr)
