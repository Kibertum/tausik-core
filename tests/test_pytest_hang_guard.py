"""The suite must be able to tell "stuck" apart from "long" without a human.

full-pytest-hangs-while-scoped-pytest-is-green. Three sessions in a row read
"slower than the timeout I chose" as "hung": the full suite was killed at 200 s,
420 s and 600 s, and a conclusion about a hang was written into a task, a
handoff and project memory. It never hung.

Then the guard installed to stop that started doing it ITSELF. Measured in
sessions #187 and #189: at ``faulthandler_timeout = 60`` the full lane on
Windows killed FOURTEEN tests every run — never reaching a summary line, and
printing a dump of every thread's stack, which reads exactly like the hang that
was not happening. Lifting the threshold proved all fourteen HEALTHY: 22 passed
in 824 s, exit 0. They were slow, not broken, and the guard could not tell the
difference any better than the three sessions had.

The root cause was not the number. It was that the number's promise —
"11x the slowest real one, 5.3 s" — had been calibrated on the FAST lane and
armed over the FULL one, and that both halves of every check in this file were
frozen constants, so nothing could notice. The threshold is now 300 s
(decision #275), and the checks below compare it against the run EXECUTING them.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from hang_guard_contract import (
    BOOTSTRAP_SUBPROCESS_BUDGET_S,
    DECLARED_HEADROOM,
    SLOWEST_IN_ISOLATION_SECONDS,
    SLOWEST_UNDER_LOAD_SECONDS,
    headroom_breach,
)

# `faulthandler_exit_on_timeout` landed in pytest 9.0. The repo declares no
# pytest floor anywhere (it is not a runtime dependency), so an older install
# is a real possibility for a contributor.
_TOO_OLD = (
    "This pytest does not know '{key}' — the hang guard needs pytest >= 9.0. "
    "Upgrade rather than deleting the guard: without it a stuck test hangs the "
    "run and gets mistaken for a slow one (see the module docstring)."
)


def _ini(config, key: str):
    """`config.getini` for a key an older pytest may not have registered.

    A bare getini raises ValueError with no hint about what to do about it.
    """
    try:
        return config.getini(key)
    except ValueError:
        pytest.fail(_TOO_OLD.format(key=key), pytrace=False)


class TestHangGuardIsArmed:
    def test_a_single_test_may_not_run_forever(self, request):
        """faulthandler_timeout is set — reading the live config, not the file.

        A test that greps pyproject.toml proves the file contains a string. This
        asks the running pytest what timeout it is actually enforcing, which is
        the thing that matters when the suite is invoked from a gate, from CI,
        or with `-c` pointed somewhere else.
        """
        timeout = float(_ini(request.config, "faulthandler_timeout") or 0.0)
        assert timeout > 0, (
            "faulthandler_timeout is 0: a stuck test hangs the run forever and "
            "the next agent will again shorten its own timeout and call the "
            "result a hang. Set it in [tool.pytest.ini_options]."
        )

    def test_the_guard_kills_the_run_instead_of_only_printing(self, request):
        """exit_on_timeout=true: the dump is useless if the run then hangs anyway.

        pytest's faulthandler dumps tracebacks and, by default, lets the test go
        on sleeping. Then the outer timeout still kills the process, the dump is
        buried in output nobody reaches, and nothing is learned.
        """
        assert _ini(request.config, "faulthandler_exit_on_timeout") is True, (
            "faulthandler_exit_on_timeout is false: a stall would print a "
            "traceback and then keep hanging."
        )

    def test_the_threshold_leaves_room_for_the_slowest_honest_test(self, request):
        """A guard that fires on real work gets deleted within a week.

        The margin is taken against the full lane measured UNDER THE LOAD of the
        full run, because that is the only condition in which the guard has ever
        actually fired. The previous version of this assertion used a fast-lane
        measurement (5.3 s) and therefore passed comfortably at 60 s while the
        real worst case was 93.57 s — i.e. it was green throughout the entire
        period in which the guard was killing fourteen healthy tests per run.
        """
        timeout = float(_ini(request.config, "faulthandler_timeout") or 0.0)
        required = SLOWEST_UNDER_LOAD_SECONDS * DECLARED_HEADROOM
        assert timeout >= required, (
            f"faulthandler_timeout={timeout}s is below {DECLARED_HEADROOM:g}x the "
            f"slowest test measured under full-lane load "
            f"({SLOWEST_UNDER_LOAD_SECONDS}s -> {required:.1f}s required). A false "
            f"kill costs more than a late one, and it costs it on EVERY run."
        )

    def test_the_threshold_clears_the_cluster_it_used_to_cut_through(self, request):
        """60 s sat in the middle of a group of twelve tests spanning 52-65 s.

        Seven of them exceeded it even in isolation, so they were doomed always
        rather than occasionally. A threshold is only stable when it sits in an
        EMPTY part of the distribution: between 65.35 s and 300 s this suite has
        no test at all, which is the actual argument for 300 (decision #275) —
        not the multiplier.
        """
        timeout = float(_ini(request.config, "faulthandler_timeout") or 0.0)
        assert timeout > SLOWEST_IN_ISOLATION_SECONDS * 2, (
            f"faulthandler_timeout={timeout}s is inside the 52-65 s cluster's blast "
            f"radius (slowest in isolation: {SLOWEST_IN_ISOLATION_SECONDS}s). Any "
            f"threshold on that slope kills part of the cluster and calls it a hang."
        )


class TestTheMarginIsWatchedMechanically:
    """The promise must be re-checked by machine, because a human forgot for months.

    ``conftest.py`` feeds every run's slowest observed duration into
    ``headroom_breach``. These call it directly, with values, rather than staging
    a slow run — the guard is asked, not modelled (dead end #427).
    """

    def test_a_comfortable_run_does_not_trip_the_wire(self):
        """The measured worst case must NOT alarm, or the alarm gets deleted."""
        assert (
            headroom_breach(
                300.0, "tests/test_bootstrap_real.py::test_x", SLOWEST_UNDER_LOAD_SECONDS
            )
            is None
        )

    def test_a_test_eating_the_declared_margin_trips_the_wire(self):
        """Exactly the drift that went unnoticed: not a kill yet, but on its way."""
        breach = headroom_breach(300.0, "tests/test_slow.py::test_creeping", 200.0)
        assert breach is not None
        assert "200.00" in breach
        assert "test_creeping" in breach

    def test_the_old_configuration_would_have_been_caught(self):
        """The regression test for the failure this whole task is about.

        At timeout=60 with a 77.09 s test the wire must fire. It did not, for
        months, because nothing compared those two numbers.
        """
        assert headroom_breach(60.0, "tests/test_stress.py::test_100_sessions", 77.09) is not None

    def test_a_disarmed_or_empty_run_is_not_reported_as_a_breach(self):
        """--collect-only and a guard-less config are silence, not evidence.

        Reporting a breach there would be the mirror defect: a verdict about a
        measurement that never happened.
        """
        assert headroom_breach(0.0, "x", 10.0) is None
        assert headroom_breach(300.0, "x", 0.0) is None


class TestARealStallIsStillKilled:
    """The negative half: raising the threshold must not disarm the guard."""

    @pytest.mark.slow  # spawns a pytest subprocess that deliberately stalls
    def test_a_genuinely_stuck_test_is_cut_and_the_run_exits_non_zero(self, tmp_path):
        """Proved by stalling, not by reading the config back.

        Runs OUTSIDE this repo (tmp_path), so it exercises pytest's own guard
        with a small threshold rather than this project's configuration.
        """
        stall = tmp_path / "test_stall.py"
        stall.write_text(
            "import time\n\n\ndef test_stalls():\n    time.sleep(120)\n",
            encoding="utf-8",
        )
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(stall),
                "-o",
                "faulthandler_timeout=5",
                "-o",
                "faulthandler_exit_on_timeout=true",
                "-p",
                "no:cacheprovider",
            ],
            cwd=str(tmp_path),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
        )
        output = proc.stdout + proc.stderr
        assert proc.returncode != 0, (
            "a test sleeping for two minutes under a 5 s guard exited zero: the "
            f"guard is disarmed.\n{output[-800:]}"
        )
        assert "Timeout (0:00:05)!" in output, (
            f"the guard did not announce the timeout it enforced:\n{output[-800:]}"
        )
        assert "test_stalls" in output, (
            f"the dump does not name the test that stalled, so it cannot be acted "
            f"on:\n{output[-800:]}"
        )


class TestTheInnerBudgetIsOrderedUnderTheGuard:
    """One floor down: a test's own subprocess budget, and the same old mistake.

    ``tests/test_bootstrap_real.py`` gives each real bootstrap spawn
    ``BOOTSTRAP_SUBPROCESS_BUDGET_S``. It used to be 120 s — 1.9x of the 63.23 s
    the test costs alone, and BELOW the 114 s it costs under full-lane load, so
    the lane passed twice and failed the third time (#190/#191). The number moved;
    what has to stay true is the ORDER of the two limits and the fact that the
    inner one still cuts.
    """

    def test_the_subprocess_budget_stays_under_the_hang_guard(self, request):
        """If they cross, the wrong limit speaks first.

        The guard kills the whole process and the report says "worker crashed";
        the subprocess budget names the child that overran. The cheaper, more
        specific message must always be the one that fires, so this compares
        against the RUNNING configuration rather than against a copy of it.
        """
        timeout = float(_ini(request.config, "faulthandler_timeout") or 0.0)
        assert 0 < BOOTSTRAP_SUBPROCESS_BUDGET_S < timeout, (
            f"the bootstrap subprocess budget ({BOOTSTRAP_SUBPROCESS_BUDGET_S}s) is not "
            f"strictly inside faulthandler_timeout ({timeout}s): the hang guard would "
            f"fire first and the failure would be reported as a crashed worker instead "
            f"of naming the subprocess that overran."
        )

    def test_a_wedged_child_is_still_cut(self):
        """Proved by wedging a child, not by reading the constant back.

        A bigger budget must not mean a disarmed one: the mechanism the four
        bootstrap calls rely on is ``subprocess.run(timeout=...)``, and this
        stalls a child under a deliberately tiny budget to show it still raises
        rather than waiting forever.
        """
        with pytest.raises(subprocess.TimeoutExpired):
            subprocess.run(
                [sys.executable, "-c", "import time; time.sleep(30)"],
                capture_output=True,
                timeout=1,
            )
