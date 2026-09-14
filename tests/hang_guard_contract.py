"""One statement, one place: the hang guard's threshold and the promise beside it.

Convention #394 says a number in a constant and the promise in the docstring
next to it are ONE assertion, and both have to be checked. This module exists
because that convention was proved the hard way: ``pyproject.toml`` promised
"60 s = 11x the slowest real test (5.3 s)" while the slowest real test was
**77.09 s**. The number stayed true to itself; the promise beside it went false,
and it went false SILENTLY. Fourteen healthy tests were executed by nobody for
months as a result — killed in the full lane, ``--ignore``d in CI, deselected as
slow in the fast lane.

The 5.3 s was not a lie, it was the wrong lane: it was measured on the FAST lane,
where a hang guard is not needed, and then armed over the full lane, where it did
harm. So every number here records WHICH lane and WHICH session produced it, and
the live check in ``conftest.py`` compares the threshold against the run actually
executing, not against a constant somebody has to remember to update.
"""

from __future__ import annotations

# Slowest test of the FULL lane measured UNDER THE LOAD OF THE FULL RUN
# (`pytest -m '' -n auto`, 20 cores, Windows, session #190):
# tests/test_bootstrap_real.py::TestBootstrapReal::test_bootstrap_creates_tausik_dir.
# This is the number the threshold must be calibrated against. Measuring the
# same test in isolation gives 55.23 s and a comfortable, WRONG conclusion —
# the guard fires under load, so it must be sized under load.
#
# IT WENT UP WHEN THE GUARD WAS LIFTED, AND THAT IS NOT A REGRESSION. The
# previous value recorded here was 77.09 s (test_100_sessions, session #187),
# and it was measured in a run where twelve of these tests were being KILLED at
# 60 s. A run that executes fewer tests is a run under LIGHTER load, so the old
# maximum was an underestimate produced by the very defect being fixed. Only
# once all fourteen survived to the end (7434 passed, 24 skipped, exit 0,
# 793.51 s) did the tree show what its worst case actually costs.
SLOWEST_UNDER_LOAD_SECONDS = 93.57

# Slowest test measured IN ISOLATION with the guard lifted
# (`-o faulthandler_timeout=600`, serial, session #189):
# tests/test_bootstrap_skills_coverage.py::test_every_builtin_skill_lands_in_claude_skills.
# Recorded for contrast, not for calibration: twelve tests sit between 52.47 s
# and 65.35 s, i.e. the old 60 s threshold cut straight through the middle of a
# cluster. Seven of them exceeded it even unloaded — doomed always, not rarely.
SLOWEST_IN_ISOLATION_SECONDS = 65.35

# The promise, as a floor rather than as a boast. The threshold must be at least
# this many times the slowest test the run actually executed.
#
# This is an ALARM level, not the safety margin. The margin is 300 / 93.57 =
# 3.2x; the alarm sits lower on purpose, so it says "this is drifting" while
# there is still room, rather than at the moment tests start dying.
#
# Why 2 and not the 11 the old docstring claimed: 11x was never a design choice.
# It was an artefact of dividing 60 by a fast-lane measurement, and buying
# literal fidelity to an accident would cost twelve minutes on every REAL stall.
#
# Why 2 and not 3: 3 was set against the stale 77.09 s and, once the real
# maximum turned out to be 93.57 s, it put the alarm at a 150 s budget — 6%
# above the observed worst case. An alarm that close fires on an ordinary slow
# machine, and this module's whole subject is what happens to a guard that fires
# on honest work: it gets worked around, then deleted. At 2 the alarm sits at
# 187 s, i.e. it wants a test to have grown 100% over today's worst before it
# speaks, and still speaks 113 s before anything is killed.
#
# Do not shave this to make a number fit. Both directions are recorded decisions:
# the errors are asymmetric — a threshold that is too low poisons EVERY run
# (healthy tests killed, a thread dump that reads like a hang, which is the exact
# failure this guard was installed to stop), while one that is too high costs
# minutes RARELY.
DECLARED_HEADROOM = 2.0


def headroom_breach(
    timeout_seconds: float,
    slowest_nodeid: str,
    slowest_seconds: float,
) -> str | None:
    """The live check: has the slowest EXECUTED test eaten the declared margin?

    Returns an explanatory message when the margin is gone, ``None`` otherwise.

    This is the half of the fix that survives. A test asserting ``60 >= 5.3 * 5``
    stays green forever, because both numbers are frozen in the file — that is
    precisely how the promise rotted unnoticed. This function is handed the
    duration the CURRENT run measured, so the suite reddens when reality drifts
    toward the threshold instead of when somebody remembers to re-measure.

    Pure on purpose: ``conftest.py`` only collects the durations, so the decision
    can be tested by calling it with values rather than by staging a slow run.
    """
    if timeout_seconds <= 0 or slowest_seconds <= 0:
        return None
    budget = timeout_seconds / DECLARED_HEADROOM
    if slowest_seconds <= budget:
        return None
    return (
        f"HANG GUARD HEADROOM IS GONE. The slowest test this run executed took "
        f"{slowest_seconds:.2f} s ({slowest_nodeid}), against faulthandler_timeout="
        f"{timeout_seconds:g} s. That is {timeout_seconds / slowest_seconds:.2f}x, "
        f"below the declared floor of {DECLARED_HEADROOM:g}x (budget {budget:.2f} s).\n"
        # Plain ASCII punctuation on purpose: this string is written straight to
        # the terminal, and a Windows console in cp866/cp1251 turns an em dash
        # into a replacement char right in the middle of the remedy.
        f"This is a WARNING SHOT, not the failure itself: nothing was killed. It "
        f"fires early so the guard never starts killing healthy tests again - that "
        f"cost this project fourteen tests executed by nobody for months.\n"
        f"Fix it deliberately, one of: (a) make the test faster; (b) raise "
        f"faulthandler_timeout in pyproject.toml AND update the promise beside it "
        f"AND the measurement in tests/hang_guard_contract.py, all three together; "
        f"(c) lower DECLARED_HEADROOM, which is a decision about how much warning "
        f"you want, and belongs in a recorded decision, not in a quiet edit."
    )


# --- one floor down: the budget a single subprocess gets inside a test --------
#
# tests/test_bootstrap_real.py spawns a real bootstrap (venv + pip install) four
# times and gives each spawn a subprocess.run timeout. That number was 120 s,
# repeated as a bare literal, and it repeated this module's own mistake one floor
# down: SIZED IN ISOLATION, ARMED UNDER LOAD.
#
# Measured, session #191. `test_bootstrap_init_creates_session` takes 63.23 s on
# its own (`-n0`), which makes 120 s look like 1.9x of headroom. But this file
# only ever executes inside the FULL lane, and this tree's load inflation there is
# measured at 1.7-1.8x (#189/#190: 43.43 -> 77.09 and 55.23 -> 93.57 for the same
# test alone versus under the full run). 63.23 x 1.8 = 114 s. The budget stood
# four seconds above the expected worst case — so the full lane passed twice in
# #190 and failed the third time with `subprocess.TimeoutExpired: ...
# bootstrap.py --init ... timed out after 120 seconds`. A coin toss, reported as
# a bug in bootstrap.
#
# 200 s is 3.2x the isolated cost — the same margin decision #275 chose for the
# guard above (300 / 93.57 = 3.2x). It stays STRICTLY BELOW faulthandler_timeout
# on purpose, and test_pytest_hang_guard.py asserts that ordering against the
# RUNNING configuration: if the two ever cross, the guard fires first, kills the
# whole process, and the report says "worker crashed" instead of naming the
# subprocess that overran. The cheaper limit must always be the one that speaks.
BOOTSTRAP_SUBPROCESS_BUDGET_S = 200
