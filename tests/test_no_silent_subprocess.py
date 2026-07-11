"""A discarded `subprocess.run(...)` must state `check=` explicitly.

The session's silent-error bugs shared a shape: a tool's exit code was thrown
away. `pin_eol_config` ran `git config` and ignored the result — if the pin
failed to write, the next `git pull` re-converted line endings and signature
verification broke again, with no signal.

Discarding a run's result is sometimes right (a formatter's exit code, a
best-effort journal write). The rule is not "never discard" — that would flag
those legitimate cases and become a gate that cries wolf. The rule is: make the
choice VISIBLE. A discarded run must pass `check=` explicitly — `check=True` to
fail loudly, `check=False` to say "I am ignoring this on purpose". A bare run
with a discarded result relies on the silent default, which is the exact swallow
we keep getting bitten by. This mirrors the BLE001 discipline for blind excepts.

Popen is exempt: it is asynchronous by nature and has no exit code at call time.
check_output / check_call raise on non-zero already, so discarding them is safe.
"""

from __future__ import annotations

import ast
import glob
import os

_ROOTS = ("scripts", "bootstrap")
_REPO = os.path.join(os.path.dirname(__file__), "..")


def _discarded_run_without_explicit_check(source: str) -> list[int]:
    """Line numbers of `subprocess.run(...)` used as a bare statement (result
    discarded) that do NOT pass an explicit `check=` keyword."""
    tree = ast.parse(source)
    hits: list[int] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)):
            continue
        call = node.value
        func = call.func
        if not (isinstance(func, ast.Attribute) and func.attr == "run"):
            continue
        base = func.value
        if not (isinstance(base, ast.Name) and base.id == "subprocess"):
            continue
        if not any(kw.arg == "check" for kw in call.keywords):
            hits.append(call.lineno)
    return hits


def _tracked_py_files() -> list[str]:
    out: list[str] = []
    for root in _ROOTS:
        out += glob.glob(os.path.join(_REPO, root, "**", "*.py"), recursive=True)
    return sorted(out)


def test_no_discarded_run_relies_on_the_silent_default():
    offenders: list[str] = []
    for path in _tracked_py_files():
        if os.sep + "__pycache__" + os.sep in path:
            continue
        with open(path, encoding="utf-8") as f:
            source = f.read()
        for line in _discarded_run_without_explicit_check(source):
            rel = os.path.relpath(path, _REPO).replace(os.sep, "/")
            offenders.append(f"{rel}:{line}")
    assert not offenders, (
        "discarded subprocess.run without explicit check= (silent exit-code "
        "swallow — add check=True to fail loud or check=False to ignore on "
        "purpose):\n  " + "\n  ".join(offenders)
    )


def test_the_probe_can_actually_say_no():
    """Guard: the detector must flag a bare discarded run, or it is worthless."""
    bad = "import subprocess\nsubprocess.run(['git', 'config', 'x', 'y'])\n"
    assert _discarded_run_without_explicit_check(bad) == [2]


def test_explicit_check_false_is_accepted():
    ok = "import subprocess\nsubprocess.run(['fmt', f], check=False)\n"
    assert _discarded_run_without_explicit_check(ok) == []


def test_check_true_is_accepted():
    ok = "import subprocess\nsubprocess.run(['x'], check=True)\n"
    assert _discarded_run_without_explicit_check(ok) == []


def test_assigned_result_is_not_flagged():
    """A used result can have its returncode inspected; only discards are the risk."""
    used = "import subprocess\nr = subprocess.run(['x'])\nprint(r.returncode)\n"
    assert _discarded_run_without_explicit_check(used) == []


def test_popen_is_exempt():
    """Popen returns immediately; there is no exit code to check at call time."""
    p = "import subprocess\nsubprocess.Popen(['x'])\n"
    assert _discarded_run_without_explicit_check(p) == []
