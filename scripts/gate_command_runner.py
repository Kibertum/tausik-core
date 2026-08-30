"""Command-gate executor — substitutes placeholders + runs subprocess.

Extracted from gate_runner.py for filesize compliance
(v14b-filesize-debt-paydown). Public surface:

    _SCOPED_SKIP_SENTINEL — return marker for skipped scoped runs
    run_command_gate(gate, files) -> (passed, output)
    split_scope(output) -> (label, body) — lift a genuine scope label off output

Behaviour is identical to the previous in-place implementation; gate_runner
re-exports both names for backwards compatibility with existing callers
(no import changes required elsewhere).
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
from typing import IO

import gate_outcome as _outcome
from gate_outcome import GateOutcome
from gate_test_resolver import count_test_files, resolve_test_files_for_relevant
from tausik_utils import cli_invocation

# How to spell the CLI in a remediation the reader's shell will accept.
_CLI = cli_invocation()


# Retired as a transport (check-result-conflates-could-not-run-with-passed): a
# non-execution is now an outcome, not a magic string riding the output channel.
# The name is kept because it is re-exported from gate_runner and asserted by
# existing tests; nothing produces it any more.
_SCOPED_SKIP_SENTINEL = "__TAUSIK_SCOPED_SKIP__"

# pytest says "I collected nothing" in its own exit code, and has since forever
# (EXIT_NOTESTSCOLLECTED). Collapsing it into "something failed" is the mirror
# half of this task's defect: session #182 measured `[FAIL] pytest (block)` on
# `5 deselected` — no test failed, none ran. Measured directly, not assumed:
# `python -m pytest tests/test_skill_cli_help.py -q` exits 5.
_PYTEST_NO_TESTS_COLLECTED = 5

# Recognise pytest as a TOKEN so `python.exe -m pytest ...` counts too — the
# same shape the TAUSIK_VERIFY_FULL injection below already relies on.
_PYTEST_TOKEN = re.compile(r"(^|\s)pytest(\s|$)")

# The remedy the #182 refusal never named. Kept next to the reason it belongs
# to so the two cannot drift apart, and spelled as the environment variable
# because `--full` DOES NOT EXIST: `verify --help` lists --task, --scope,
# --relevant-files and --no-tests-expected, and nothing else. pyproject.toml
# used to promise the flag as well; that promise was DELETED rather than
# implemented, so the environment variable is now the single true name for the
# full lane and this string cannot send anyone to a flag the product refuses.
_FULL_LANE_REMEDY = (
    "No test ran: the default lane is `-m 'not slow'` (pyproject.toml addopts) "
    "and every collected test was deselected. This is not a failure — nothing "
    "was checked. Re-run the gate over the full battery with "
    "TAUSIK_VERIFY_FULL=1 set in the environment."
)

# How many scoped test files to name before summarising the rest.
_SCOPE_LABEL_MAX_NAMED = 5

# The human-readable head of the coverage line. It is only a DISPLAY prefix now,
# not the trust signal: any subprocess can print "SCOPE:" too, so recognising a
# genuine label by this string let a stack command's stdout masquerade as the
# framework's own coverage disclosure (conventions #169/#297 — a gate must not
# render checked-party text as framework-trusted output).
SCOPE_PREFIX = "SCOPE:"

# The trust signal is this private sentinel instead. `_scoped` prepends it to the
# genuine label; a subprocess cannot emit a NUL-delimited token, so a spoofed
# "SCOPE:" line in tool stdout never carries it. It is internal transport only:
# gate_runner lifts the label off with `split_scope` at the one point it builds
# the result dict, so the sentinel never reaches stored output or a receipt.
_SCOPE_SENTINEL = "\x00\x00tausik-scope\x00\x00"


def split_scope(output: str) -> tuple[str, str]:
    """Lift a sentinel-marked scope label off the FRONT of `output`.

    Returns ``(label, body)``. ``label`` is the human-readable "SCOPE: ..." line
    with the private sentinel stripped, or ``""`` when the output carries no
    genuine label. Only a leading sentinel counts — a "SCOPE:" line a subprocess
    printed anywhere (including its own first line) has no sentinel and stays in
    ``body``, so it can never be mistaken for the framework's disclosure.
    """
    if not output.startswith(_SCOPE_SENTINEL):
        return "", output
    first, _, rest = output[len(_SCOPE_SENTINEL) :].partition("\n")
    return first, rest


def _scope_label(test_files: list[str], total: int) -> str:
    """One ASCII line stating WHAT a scoped pytest run actually covered.

    The gate answers "do the tests mapped to relevant_files pass?", but its
    output is a bare pytest tail ("42 passed") that a reader — and the signed
    verify receipt built from it — takes as a statement about the whole suite.
    Session #134 shipped a green receipt while the full suite was red: the
    failing test simply was not in scope. The denominator has to travel with
    the verdict, so the receipt cannot be read wider than it was earned.

    ASCII only: this line is read in Windows consoles that mangle UTF-8.
    """
    named = ", ".join(test_files[:_SCOPE_LABEL_MAX_NAMED])
    rest = len(test_files) - _SCOPE_LABEL_MAX_NAMED
    if rest > 0:
        named += f", +{rest} more"
    denominator = f" of {total}" if total else ""
    return (
        f"{SCOPE_PREFIX} scoped run over {len(test_files)}{denominator} test "
        f"file(s) mapped from relevant_files -- NOT the full suite: {named}"
    )


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


def run_command_gate(gate: dict, files: list[str]) -> GateOutcome:
    """Run a command-based gate. Substitutes {files} / {test_files_for_files}.

    Returns a `GateOutcome`. It unpacks as the historical ``(passed, output)``
    pair, so existing call sites keep working; callers that need to tell "did
    not run" from "ran and failed" read ``.outcome`` instead of the first slot.

    The non-execution cases used to be a sentinel string in the output channel;
    they are now NOT_APPLICABLE (a legitimately empty check — does not block)
    or COULD_NOT_RUN (the check could not execute — blocks, and says why).

    A run that WAS scoped prefixes its output with `_scope_label` — the verdict
    and the size of the thing it was earned on travel together.
    """
    cmd = gate.get("command", "")
    if not cmd:
        return _outcome.could_not_run(
            _outcome.REASON_NO_GATE_IMPLEMENTATION,
            "No command configured.",
            remedy=(
                f"Give gate '{gate.get('name', '?')}' a `command`, or remove it "
                "from `gates` in .tausik/config.json."
            ),
        )

    scope_label = ""

    file_exts_raw = gate.get("file_extensions") or []
    if file_exts_raw and "{files}" in cmd:
        allowed = {(e if e.startswith(".") else "." + e).lower() for e in file_exts_raw}
        files = [f for f in files if os.path.splitext(f)[1].lower() in allowed]
        if not files:
            return _outcome.not_applicable(
                _outcome.REASON_NO_MATCHING_FILES,
                "No files matching " + ", ".join(sorted(allowed)) + " — gate skipped.",
            )

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
            return _outcome.not_applicable(
                _outcome.REASON_NO_MATCHING_FILES,
                "No files matching " + ", ".join(patterns_raw) + " — gate skipped.",
            )

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
            # Both branches are LEGITIMATE emptiness, so both stay non-blocking
            # — the task's negative constraint is explicit that a change which
            # honestly matches no test must not be turned red. What changes is
            # that they stop being one indistinguishable SKIP: each now carries
            # its own reason code, so the record says which emptiness it was.
            #
            # NO_SCOPE_DECLARED is deliberately NOT promoted to COULD_NOT_RUN:
            # certification of an unscoped run is already refused upstream
            # (verification_runs.declared_scope_status), and blocking here would
            # turn every `gate_runner <trigger>` invocation without --files red.
            if files:
                return _outcome.not_applicable(
                    _outcome.REASON_NO_TEST_MAPPING,
                    "No test file maps to relevant_files via "
                    "tests/test_<basename>.py heuristic; gate skipped (scoped run).",
                )
            return _outcome.not_applicable(
                _outcome.REASON_NO_SCOPE_DECLARED,
                "No relevant_files passed; gate skipped.",
                # Name the whole line: a bare `--relevant-files` used to be
                # suggested against a command that has no such flag.
                remedy=(
                    f"Declare the scope: `{_CLI} verify --task <slug> --relevant-files <paths...>`."
                ),
            )
        scope_label = _scope_label(test_files, count_test_files())
        test_files_str = " ".join(shlex.quote(t) for t in test_files)
        cmd = cmd.replace("{test_files_for_files}", test_files_str)

    files_str = " ".join(shlex.quote(f) for f in files) if files else "."
    cmd = cmd.replace("{files}", files_str)
    # v14b-pytest-fast-lane: TAUSIK_VERIFY_FULL=1 reverts the default fast lane
    # (pyproject.toml addopts="-m 'not slow'") and runs the full battery. Detect
    # pytest as a TOKEN (works for `pytest …` AND `python.exe -m pytest …`) and
    # inject the override right after it; count=0 leaves non-pytest gates untouched.
    #
    # IT IS `-m ''`, NOT `--override-ini=addopts=`, SINCE full-lane-runs-serial-on-
    # a-twenty-core-machine. Wiping addopts removed the marker filter AND everything
    # else standing beside it — here `-n auto`, so the "full battery" was the one
    # run in the project that went back to a single core (32m24s against 3m48s,
    # measured session #186). A marker expression on the command line beats the one
    # in addopts because it is parsed later and -m keeps only the last value:
    # measured on this tree, `-m ''` and `--override-ini=addopts=` both collect
    # 7459 against the fast lane's 7317. Whatever else a consumer put in addopts
    # (coverage, timeouts, their own -p flags) now survives the full lane too.
    if os.environ.get("TAUSIK_VERIFY_FULL"):
        cmd = re.subn(r"(^|\s)pytest(\s|$)", r"\1pytest -m ''\2", cmd, count=1)[0]
    # Cross-platform truncation: strip `[2>&1] | head/tail -N`, filter later.
    # Windows note: shlex (posix) strips backslashes from paths and subprocess
    # cannot launch a relative forward-slash executable (WinError 2); the
    # shell-less runner normalizes each stage's argv[0] to the OS separator so a
    # configured path like backend/.venv/Scripts/python.exe resolves.
    cmd, line_filter = _extract_truncation_filter(cmd)
    timeout = gate.get("timeout", 120)

    def _scoped(text: str) -> str:
        """Every outcome of a scoped run carries its scope — pass, fail, timeout,
        spawn failure. The label is sentinel-marked so gate_runner can trust it;
        a non-scoped run (empty ``scope_label``) returns the text untouched."""
        return f"{_SCOPE_SENTINEL}{scope_label}\n{text}" if scope_label else text

    is_pytest = bool(_PYTEST_TOKEN.search(cmd))

    try:
        returncode, raw_output = _run_shellless(cmd, timeout)
        output = raw_output.strip()
        if line_filter:
            output = _apply_line_filter(output, line_filter)
        if returncode == 0:
            return _outcome.passed(_scoped(output or "Passed."))
        if is_pytest and returncode == _PYTEST_NO_TESTS_COLLECTED:
            # The distinction this task exists for: pytest ran, collected
            # nothing, and said so. Nothing failed — nothing was checked.
            return _outcome.could_not_run(
                _outcome.REASON_NO_TESTS_COLLECTED,
                _scoped(output or "No tests were collected."),
                remedy=_FULL_LANE_REMEDY,
            )
        return _outcome.failed(_scoped(output or f"Failed with exit code {returncode}."))
    except subprocess.TimeoutExpired:
        # A gate that ran out of clock produced no verdict either. It kept its
        # blocking behaviour, but it stops being reported as a finding.
        return _outcome.could_not_run(
            _outcome.REASON_TIMED_OUT,
            _scoped(f"Gate timed out ({timeout}s)."),
            remedy=(
                "Raise `timeout` for this gate in .tausik/config.json, or narrow "
                "the scope it runs over."
            ),
        )
    except (FileNotFoundError, PermissionError, NotADirectoryError) as e:
        # Spawn failure (binary missing / not executable) — distinct from an
        # honest non-zero exit. Log it so a misconfigured gate command is visible.
        import logging

        logging.getLogger("tausik.gates").warning("Gate command not runnable: %s", e)
        return _outcome.could_not_run(
            _outcome.REASON_COMMAND_NOT_RUNNABLE,
            _scoped(f"Gate command not runnable (check the configured path): {e}"),
            remedy="Fix the gate's `command` path in .tausik/config.json.",
        )
    except Exception as e:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
        return _outcome.could_not_run(
            _outcome.REASON_RUNNER_ERROR,
            _scoped(f"Gate error: {e}"),
            remedy="The gate runner itself failed; this is a framework defect.",
        )
