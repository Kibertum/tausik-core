"""Command-gate executor — substitutes placeholders + runs subprocess.

Extracted from gate_runner.py for filesize compliance
(v14b-filesize-debt-paydown). Public surface:

    _SCOPED_SKIP_SENTINEL — return marker for skipped scoped runs
    run_command_gate(gate, files) -> (passed, output)

Behaviour is identical to the previous in-place implementation; gate_runner
re-exports both names for backwards compatibility with existing callers
(no import changes required elsewhere).
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess

from gate_test_resolver import resolve_test_files_for_relevant


_SCOPED_SKIP_SENTINEL = "__TAUSIK_SCOPED_SKIP__"

# v1.5 v15p-fix-hadolint-windows-head: stack gate commands historically end
# with a unix truncation pipe (`hadolint {files} 2>&1 | head -30`). On Windows
# shell=True means cmd.exe, which has no head/tail — every such gate failed
# with "'head' is not recognized". The runner now strips that trailing pipe
# and applies the same first/last-N-lines truncation in Python, so stack.json
# stays declarative and works on every OS.
_TRUNCATION_PIPE_RE = re.compile(r"\s*(?:2>&1\s*)?\|\s*(head|tail)\s+-n?\s*(\d+)\s*$")


def _extract_truncation_filter(
    cmd: str,
) -> tuple[str, tuple[str, int] | None]:
    """Strip a trailing `[2>&1] | head/tail -N` from cmd.

    Returns (cmd_without_pipe, (mode, n)) or (cmd, None) when absent.
    stderr merging is unaffected: the runner already concatenates
    stdout + stderr itself.
    """
    m = _TRUNCATION_PIPE_RE.search(cmd)
    if not m:
        return cmd, None
    return cmd[: m.start()], (m.group(1), int(m.group(2)))


def _apply_line_filter(output: str, line_filter: tuple[str, int]) -> str:
    """Python-side equivalent of `| head -N` / `| tail -N` on gate output."""
    mode, n = line_filter
    lines = output.splitlines()
    if len(lines) <= n:
        return output
    marker = f"... (output truncated to {mode} -{n} by gate runner)"
    if mode == "head":
        return "\n".join(lines[:n] + [marker])
    return "\n".join([marker] + lines[-n:])


def run_command_gate(gate: dict, files: list[str]) -> tuple[bool, str]:
    """Run a command-based gate. Substitutes {files} / {test_files_for_files}.

    Special return: (True, _SCOPED_SKIP_SENTINEL) when {test_files_for_files}
    is in cmd and no test files map from a non-empty relevant_files. The
    caller (run_gates) translates this into a skipped_result entry so the
    UI shows SKIP, not PASS, and we don't run an irrelevant full suite.
    """
    cmd = gate.get("command", "")
    if not cmd:
        return True, "No command configured."

    file_exts_raw = gate.get("file_extensions") or []
    if file_exts_raw and "{files}" in cmd:
        allowed = {(e if e.startswith(".") else "." + e).lower() for e in file_exts_raw}
        files = [f for f in files if os.path.splitext(f)[1].lower() in allowed]
        if not files:
            return True, ("No files matching " + ", ".join(sorted(allowed)) + " — gate skipped.")

    # v1.5: filename-based scoping for gates whose targets have no extension
    # (Dockerfile, Containerfile, Makefile...). Without this, an empty match
    # left {files} = "." and e.g. `hadolint .` choked on the directory.
    patterns_raw = gate.get("file_patterns") or []
    if patterns_raw and "{files}" in cmd:
        import fnmatch

        files = [
            f
            for f in files
            if any(fnmatch.fnmatch(os.path.basename(f).lower(), p.lower()) for p in patterns_raw)
        ]
        if not files:
            return True, ("No files matching " + ", ".join(patterns_raw) + " — gate skipped.")

    if "{test_files_for_files}" in cmd:
        test_files = resolve_test_files_for_relevant(files)
        # Scoped-only semantics:
        #   - relevant_files non-empty + no test mapping → SKIP (scoped run for
        #     a module without test_<basename>.py — running the full suite for
        #     an unrelated module defeats the scoping promise).
        #   - relevant_files empty → SKIP (was: fall back to full suite).
        #     MCP task_done has a 10s budget; the suite always exceeds it and
        #     burns budget for zero verification value. Forces callers to pass
        #     relevant_files to opt in to actual verification.
        if not test_files:
            return True, _SCOPED_SKIP_SENTINEL
        test_files_str = " ".join(shlex.quote(t) for t in test_files)
        cmd = cmd.replace("{test_files_for_files}", test_files_str)

    files_str = " ".join(shlex.quote(f) for f in files) if files else "."
    cmd = cmd.replace("{files}", files_str)
    # v14b-pytest-fast-lane: TAUSIK_VERIFY_FULL=1 reverts the default fast lane
    # (pyproject.toml addopts="-m 'not slow'") and runs the full battery. Detect
    # pytest as a TOKEN (works for `pytest …` AND `python.exe -m pytest …`) and
    # inject the override right after it; count=0 leaves non-pytest gates untouched.
    if os.environ.get("TAUSIK_VERIFY_FULL"):
        cmd = re.subn(r"(^|\s)pytest(\s|$)", r"\1pytest --override-ini=addopts=\2", cmd, count=1)[0]
    # Cross-platform truncation: strip `[2>&1] | head/tail -N`, filter later.
    cmd, line_filter = _extract_truncation_filter(cmd)
    # Detect shell operators -- need shell=True for pipes and redirects
    needs_shell = any(op in cmd for op in ("|", "&&", ">>", "2>&1"))
    timeout = gate.get("timeout", 120)
    try:
        if needs_shell:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                stdin=subprocess.DEVNULL,
            )
        else:
            argv = shlex.split(cmd)
            # Windows: shlex (posix) strips backslashes from paths, and subprocess
            # cannot launch a relative forward-slash executable (WinError 2).
            # Normalize argv[0] to the OS-native separator so a configured path like
            # backend/.venv/Scripts/python.exe resolves. Bare executables (ruff,
            # mypy) are unaffected — normpath is a no-op on a name without a dir.
            if argv:
                argv[0] = os.path.normpath(argv[0])
            result = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                stdin=subprocess.DEVNULL,
            )
        output = (result.stdout + result.stderr).strip()
        if line_filter:
            output = _apply_line_filter(output, line_filter)
        if result.returncode == 0:
            return True, output or "Passed."
        return False, output or f"Failed with exit code {result.returncode}."
    except subprocess.TimeoutExpired:
        return False, f"Gate timed out ({timeout}s)."
    except Exception as e:
        return False, f"Gate error: {e}"
