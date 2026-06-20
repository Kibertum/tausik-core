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
from typing import IO

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


# --- shell-less execution -------------------------------------------------
# Historically the runner fell back to `shell=True` whenever a command held a
# pipe / `&&` / redirect. For custom stacks (whose command templates are
# attacker-controllable) that is a command-injection vector: a stack gate
# `ruff {files}; rm -rf ~` would run the `rm` via the shell. We never spawn a
# shell now — commands are tokenized with shlex (quoting honoured) and the only
# operators we act on are `&&` (sequential AND) and `|` (pipe). Every other
# shell metacharacter shlex surfaces (`;`, `||`, `&`, `(`, `)`, `<`, `>`, `>>`)
# is refused, so the gate fails safely instead of executing an unknown tail.
_SEQ_OP = "&&"
_PIPE_OP = "|"
_KNOWN_OPS = frozenset({_SEQ_OP, _PIPE_OP})
_SHELL_PUNCT = "();<>|&"


class _GateCommandError(ValueError):
    """Raised for a gate command the shell-less runner refuses to execute."""


def _tokenize_command(cmd: str) -> list[str]:
    """shlex-tokenize, surfacing shell operators (&&, |, ;, ...) as own tokens.

    posix=True so quoting works; punctuation_chars=True makes runs of the
    shell metacharacters their own tokens, letting us detect — and reject —
    anything beyond the `&&`/`|` we support instead of handing it to a shell.
    """
    lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    return list(lex)


def _split_tokens(tokens: list[str], op: str) -> list[list[str]]:
    """Split a token list on a separator operator into groups."""
    groups: list[list[str]] = [[]]
    for tok in tokens:
        if tok == op:
            groups.append([])
        else:
            groups[-1].append(tok)
    return groups


def _exec_pipeline(stages: list[list[str]], timeout: int) -> tuple[int, str]:
    """Run one `|`-connected pipeline (argv stages). Returns (rc, output)."""
    if len(stages) == 1:
        argv = list(stages[0])
        argv[0] = os.path.normpath(argv[0])
        r = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
        return r.returncode, r.stdout + r.stderr
    # Multi-stage: chain stdout->stdin. We capture only the final stage's
    # stdout+stderr (gate semantics); intermediate stderr is discarded to
    # avoid pipe-buffer deadlocks. Pipelines are rare once truncation pipes
    # (`| head/tail`) are stripped upstream.
    procs: list[subprocess.Popen[str]] = []
    prev_stdout: IO[str] | None = None
    for i, raw in enumerate(stages):
        argv = list(raw)
        argv[0] = os.path.normpath(argv[0])
        is_last = i == len(stages) - 1
        proc = subprocess.Popen(
            argv,
            stdin=prev_stdout if prev_stdout is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE if is_last else subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if prev_stdout is not None:
            prev_stdout.close()  # let upstream see SIGPIPE when downstream exits
        prev_stdout = proc.stdout
        procs.append(proc)
    last = procs[-1]
    try:
        out, err = last.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        for proc in procs:
            proc.kill()
        for proc in procs:
            proc.wait()
        raise
    for proc in procs[:-1]:
        # Last stage already finished; upstream stages should have seen EOF/
        # SIGPIPE and be exiting. Bound the reap so a stage that ignores the
        # signal (or otherwise hangs) cannot wedge the gate forever.
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    return last.returncode, out + err


def _run_shellless(cmd: str, timeout: int) -> tuple[int, str]:
    """Execute a gate command without a shell. Honours `&&` and `|` only."""
    cmd = re.sub(r"\s*2>&1", "", cmd)  # stderr is always merged by the caller
    tokens = _tokenize_command(cmd)
    for tok in tokens:
        if tok in _KNOWN_OPS:
            continue
        if tok and all(ch in _SHELL_PUNCT for ch in tok):
            raise _GateCommandError(
                f"unsupported shell operator '{tok}' in gate command — "
                "shell-less runner refuses to chain on it"
            )
    returncode, output = 0, ""
    for seq in _split_tokens(tokens, _SEQ_OP):
        stages = _split_tokens(seq, _PIPE_OP)
        if any(not stage for stage in stages):
            raise _GateCommandError("empty command segment in gate pipeline")
        returncode, seg_out = _exec_pipeline(stages, timeout)
        output += seg_out
        if returncode != 0:  # `&&` short-circuits on first failure
            break
    return returncode, output


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
    # Windows note: shlex (posix) strips backslashes from paths and subprocess
    # cannot launch a relative forward-slash executable (WinError 2); the
    # shell-less runner normalizes each stage's argv[0] to the OS separator so a
    # configured path like backend/.venv/Scripts/python.exe resolves.
    cmd, line_filter = _extract_truncation_filter(cmd)
    timeout = gate.get("timeout", 120)
    try:
        returncode, raw_output = _run_shellless(cmd, timeout)
        output = raw_output.strip()
        if line_filter:
            output = _apply_line_filter(output, line_filter)
        if returncode == 0:
            return True, output or "Passed."
        return False, output or f"Failed with exit code {returncode}."
    except subprocess.TimeoutExpired:
        return False, f"Gate timed out ({timeout}s)."
    except (FileNotFoundError, PermissionError, NotADirectoryError) as e:
        # Spawn failure (binary missing / not executable) — distinct from an
        # honest non-zero exit. Log it so a misconfigured gate command is visible.
        import logging

        logging.getLogger("tausik.gates").warning("Gate command not runnable: %s", e)
        return False, f"Gate command not runnable (check the configured path): {e}"
    except Exception as e:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
        return False, f"Gate error: {e}"
