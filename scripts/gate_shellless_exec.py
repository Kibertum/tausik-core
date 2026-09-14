"""Running a gate command WITHOUT a shell, and resolving what to run.

Extracted from `gate_command_runner` when that module crossed the 500-line cap
(session #235). The split is on a real boundary, not a convenient one: this is
"turn a command STRING into processes and an exit code", and the module it left
is "decide what a gate should be handed and what its result means". Nothing here
knows about gates, files or verdicts.

WHY NO SHELL. A gate command comes from configuration, and configuration is
edited by people. `ruff {files}; rm -rf ~` run through a shell would do exactly
what it says. So the command is tokenised here and the pieces are spawned
directly; only two operators are understood — `&&` and `|` — and anything else
is refused rather than guessed at.

The names stay private (`_`-prefixed) because they were private before the move
and three test modules import them by those names; renaming on a mechanical
extraction would turn one change into two.
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
from typing import IO

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


def _resolve_argv0(argv0: str) -> str:
    """Make a configured program name launchable by a shell-less spawn.

    js-test-gate-silent-on-windows-and-override-dropped (GitLab #9).

    TWO DISTINCT FAILURES, ONE PLACE. `os.path.normpath` was already here for
    configured paths written with forward slashes. The second failure is
    Windows-only and was invisible: `subprocess` spawns through `CreateProcess`,
    which does NOT consult PATHEXT, so a gate configured as `npm ...` dies with
    `[WinError 2]` even though npm is installed and on PATH. Measured, not
    assumed: `shutil.which("npm")` answers `...\\npm.CMD` on this machine while
    `subprocess.run(["npm"])` raises FileNotFoundError for the same name.

    WHY THIS AND NOT AN ALLOW-LIST ENTRY. Adding `npm.cmd` to
    ALLOWED_GATE_EXECUTABLES is the fix GitLab #9 explicitly names as the worst
    one: it treats the symptom, it makes the user responsible for knowing the
    platform, and it has to be repeated for yarn, pnpm, bun and every tool
    after them. Resolution happens here, on the SAME name the allow-list
    already approved — the guard keeps guarding, and it keeps guarding the
    bare name, because `_validate_custom_gate` runs against the command string
    long before this function sees an argv.

    THE WHOLE CLASS, NOT npm. All 26 command-carrying gates across every
    shipped stack name their tool by bare name (measured), so this is the one
    place that makes any of them launchable rather than a per-tool patch.

    An unresolvable name is returned unchanged ON PURPOSE: the caller's
    FileNotFoundError path turns it into COULD_NOT_RUN with the reason
    `command_not_runnable`, which is the honest answer for a tool that is
    genuinely not installed. Substituting something launchable here would hide
    that behind a different error.
    """
    normalised = os.path.normpath(argv0)
    return shutil.which(normalised) or normalised


def _exec_pipeline(stages: list[list[str]], timeout: int) -> tuple[int, str]:
    """Run one `|`-connected pipeline (argv stages). Returns (rc, output)."""
    if len(stages) == 1:
        argv = list(stages[0])
        argv[0] = _resolve_argv0(argv[0])
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
        argv[0] = _resolve_argv0(argv[0])
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
