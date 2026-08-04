"""The suite must be able to tell "stuck" apart from "long" without a human.

full-pytest-hangs-while-scoped-pytest-is-green. Three sessions in a row read
"slower than the timeout I chose" as "hung": the full suite was killed at 200 s,
420 s and 600 s, and a conclusion about a hang was written into a task, a
handoff and project memory. It never hung — it takes ~554 s and the cost is
flat (the 30 slowest tests are 10% of the total; the rest is ~0.09 s each).

The cheap half of the fix is a number in pyproject.toml. The half that survives
is this file: it asserts against the LIVE config of the run executing it, so
deleting the guard turns the suite red instead of quietly restoring the state
where nobody can distinguish a stall from a long wait.
"""

from __future__ import annotations

import pytest

# Slowest real test measured on the full suite (test_gen_doc_constants, 5.28 s).
# The guard has to sit far above it or it fires on honest work.
SLOWEST_REAL_TEST_SECONDS = 5.3

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
        """A guard that fires on real work gets deleted within a week."""
        timeout = float(_ini(request.config, "faulthandler_timeout") or 0.0)
        assert timeout >= SLOWEST_REAL_TEST_SECONDS * 5, (
            f"faulthandler_timeout={timeout}s is too close to the slowest honest "
            f"test ({SLOWEST_REAL_TEST_SECONDS}s). A false kill costs more than a "
            f"late one — keep a wide margin."
        )
