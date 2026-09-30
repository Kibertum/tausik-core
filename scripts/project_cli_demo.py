"""`tausik demo` — watch TAUSIK catch a false "tests pass" in under a minute.

The first thing a new user met used to be a refusal (QG-0: no acceptance criteria).
This shows what the refusals are FOR: an agent claims the tests are green without
running them, the close is refused, the real check runs and is red, and only a real
fix closes the task.

Every line printed under a step is REAL output of the TAUSIK CLI run against a
throwaway project — nothing is staged. No network, no LLM key. The sandbox lives in
a temporary directory and is removed at the end; the current project is not touched.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time

_PROJECT_PY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "project.py")

_BUGGY = "def add(a, b):\n    return a - b\n"
_FIXED = "def add(a, b):\n    return a + b\n"
_TEST = "from calc import add\n\n\ndef test_add():\n    assert add(2, 2) == 4\n"
_PYPROJECT = '[tool.pytest.ini_options]\npythonpath = ["."]\n'

#: Lines of real output kept per step. The demo shows the verdict, not the whole log.
_TAIL = 6
_WIDTH = 150


def _say(text: str) -> None:
    print(f"\n== {text}", flush=True)


def _show(out: str, keep: int = _TAIL, pick: tuple[str, ...] = ()) -> None:
    """Print the verdict lines of real output: those containing a `pick` needle, else the tail.

    Progress lines (`[gates] 3/12 ...`) are the run's heartbeat, not its verdict. A line is
    cut at _WIDTH so a paragraph of advice does not bury the one sentence that matters.
    """
    lines = [ln.strip() for ln in out.splitlines() if ln.strip() and not ln.startswith("[gates]")]
    if pick:
        lines = [ln for ln in lines if any(n in ln for n in pick)]
    for ln in lines[-keep:]:
        print(f"   {ln[:_WIDTH]}{'...' if len(ln) > _WIDTH else ''}", flush=True)


def _cli(args: list[str], sandbox: str, env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, _PROJECT_PY, *args],
        cwd=sandbox,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )


def _git(args: list[str], sandbox: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=sandbox,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=True,
        timeout=30,
    )


def _write(sandbox: str, name: str, text: str) -> None:
    with open(os.path.join(sandbox, name), "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def _remove(sandbox: str) -> None:
    """Delete the sandbox, read-only git objects included (Windows), or SAY it stayed."""

    def _writable_then_retry(func, path, _exc):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    try:
        shutil.rmtree(sandbox, onerror=_writable_then_retry)
    except OSError as e:
        print(f"Could not remove the sandbox {sandbox}: {e}. Delete it by hand.", file=sys.stderr)


def run_demo(keep: bool = False) -> int:
    """Run the scripted scenario. Returns 0 when every step behaved as the demo says."""
    if shutil.which("git") is None:
        print("tausik demo needs git on PATH (the receipt is bound to a commit).", file=sys.stderr)
        return 2
    # A cp1252 console cannot print the check marks TAUSIK emits; replace, never crash.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    started = time.monotonic()
    sandbox = tempfile.mkdtemp(prefix="tausik-demo-")
    env = {**os.environ, "TAUSIK_DIR": os.path.join(sandbox, ".tausik"), "PYTHONUTF8": "1"}
    for leaked in ("TAUSIK_MANAGED_CONFIG", "CLAUDE_PROJECT_DIR", "TAUSIK_SKIP_HOOKS"):
        env.pop(leaked, None)
    ok = True
    try:
        os.makedirs(env["TAUSIK_DIR"])
        _git(["init", "-q"], sandbox)
        _git(["config", "user.email", "demo@tausik.local"], sandbox)
        _git(["config", "user.name", "tausik demo"], sandbox)
        _write(sandbox, "calc.py", _BUGGY)
        os.makedirs(os.path.join(sandbox, "tests"))
        _write(sandbox, os.path.join("tests", "test_calc.py"), _TEST)
        # The test must go red because of the bug, not because `calc` fails to import.
        _write(sandbox, "pyproject.toml", _PYPROJECT)
        _write(sandbox, ".gitignore", ".tausik/\n__pycache__/\n")
        _git(["add", "-A"], sandbox)
        _git(["commit", "-qm", "calc with a bug"], sandbox)
        _cli(["init", "--name", "demo"], sandbox, env)
        _cli(["key", "init"], sandbox, env)

        _say("A throwaway project: calc.py has a bug, tests/test_calc.py catches it.")
        _say("The agent opens a task with a definition of done.")
        r = _cli(
            [
                "task", "add", "Fix add()", "--slug", "fix-add",
                "--goal", "add() returns the sum",
                "--acceptance-criteria", "1. add(2, 2) == 4, checked by tests/test_calc.py. 2. Error if add(2, 2) returns anything else.",
            ],
            sandbox,
            env,
        )  # fmt: skip
        _show(r.stdout + r.stderr, 1)
        r = _cli(["task", "start", "fix-add"], sandbox, env)
        ok &= r.returncode == 0
        _show(r.stdout if r.returncode == 0 else r.stderr, 1)

        _say('The agent says "tests pass" without running them, and tries to close.')
        _cli(["task", "log", "fix-add", "AC verified: 1. tests pass"], sandbox, env)
        r = _cli(["task", "done", "fix-add", "--ac-verified"], sandbox, env)
        # Refused for the RIGHT reason: no check backs the claim. A refusal for any other
        # cause (a crashing gate, say) would be a demo showing something that is not there.
        ok &= r.returncode != 0 and "verify-first" in r.stderr + r.stdout
        _show(r.stderr + r.stdout, 1, pick=("verify-first",))

        _say("The real check runs. The claim was false.")
        r = _cli(
            ["task", "done", "fix-add", "--ac-verified", "--relevant-files", "calc.py", "--verify"],
            sandbox,
            env,
        )
        ok &= r.returncode != 0 and "FAILED tests/test_calc.py::test_add" in r.stdout + r.stderr
        _show(r.stdout + r.stderr, 4, pick=("FAILED", "failed in", "Receipt:"))

        _say("The agent actually fixes the bug. Now the close goes through, with a receipt.")
        _write(sandbox, "calc.py", _FIXED)
        _cli(
            [
                "task",
                "log",
                "fix-add",
                "NO-DEAD-END: the first claim was false; fixed the operator",
            ],
            sandbox,
            env,
        )
        r = _cli(
            ["task", "done", "fix-add", "--ac-verified", "--relevant-files", "calc.py", "--verify"],
            sandbox,
            env,
        )
        ok &= r.returncode == 0 and "Task 'fix-add' completed" in r.stdout + r.stderr
        _show(r.stdout + r.stderr, 3, pick=("passed in", "Receipt:", "completed."))
    finally:
        if keep:
            print(f"\nSandbox kept: {sandbox}")
        else:
            _remove(sandbox)

    took = time.monotonic() - started
    verdict = "as described" if ok else "NOT as described -- please file an issue"
    print(f"\nDemo finished in {took:.0f}s, {verdict}. Your own project was not touched.")
    return 0 if ok else 1


def build_demo_subparser(sub) -> None:
    p = sub.add_parser(
        "demo",
        help="Watch TAUSIK catch a false 'tests pass' in a throwaway sandbox (no network, no LLM)",
    )
    p.add_argument("--keep", action="store_true", help="Keep the sandbox directory for inspection")


def cmd_demo(svc, args) -> None:
    """`tausik demo`. The service is unused: the demo runs in its own sandbox project."""
    code = run_demo(keep=getattr(args, "keep", False))
    if code:
        sys.exit(code)


if __name__ == "__main__":  # pragma: no cover - run as `tausik demo`
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
