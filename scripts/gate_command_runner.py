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
import subprocess

import gate_outcome as _outcome
from gate_outcome import GateOutcome
from gate_shellless_exec import (  # noqa: F401 — re-exported: three test modules import these by their old home
    _exec_pipeline,
    _GateCommandError,
    _resolve_argv0,
    _run_shellless,
    _split_tokens,
    _tokenize_command,
)
from gate_test_resolver import (
    count_test_files,
    deferred_global_crosscutting_for_relevant,
    direct_import_count_for_relevant,
    parse_errors_for_relevant,
    resolve_test_files_for_relevant,
)
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

# One scoped pytest command has a hard per-command budget.  Sending a large but
# still honest selection as a single argv makes its proof time out; `&&` is
# executed shelllessly and gives every batch that same budget without raising it.
# The slowest proof modules take roughly one transport window alone.  Four
# modules leave them room under the existing per-command timeout; a larger
# batch makes a complete, honest selection fail merely by aggregation.
_SCOPED_PYTEST_BATCH_SIZE = 4

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


def _scope_label(
    test_files: list[str], total: int, *, direct_imports: int = 0, deferred_global: int = 0
) -> str:
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
    deferred = (
        f"; global tree checks deferred to full/release lane: {deferred_global}"
        if deferred_global
        else ""
    )
    return (
        f"{SCOPE_PREFIX} scoped run over {len(test_files)}{denominator} test "
        f"file(s) mapped from relevant_files (direct-import subject tests: {direct_imports}) "
        f"-- NOT the full suite{deferred}: {named}"
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
    batch_commands: list[str] | None = None

    # `file_extensions` объявляет, КОГДА гейт применим, и это не зависит от
    # того, подставляет ли команда {files}. Прежнее условие требовало наличия
    # подстановки, поэтому у гейта без неё объявление «я про .py» не значило
    # НИЧЕГО и молча игнорировалось — гейт запускался на любой коммит. Сегодня
    # такой гейт ровно один (mypy, который проверяет набор источников из
    # pyproject целиком, а не переданные файлы), и для него область обязана
    # сохраниться: «проверяю проект целиком» и «проверяю на КАЖДЫЙ коммит» —
    # разные утверждения.
    file_exts_raw = gate.get("file_extensions") or []
    if file_exts_raw:
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
    if patterns_raw:
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
        parse_errors = parse_errors_for_relevant(files)
        if parse_errors:
            named = ", ".join(parse_errors[:10])
            more = "" if len(parse_errors) <= 10 else f" (+{len(parse_errors) - 10} more)"
            return _outcome.could_not_run(
                _outcome.REASON_TEST_SOURCE_PARSE_ERROR,
                f"Could not parse candidate test source(s): {named}{more}.",
                remedy="Fix the named test source before relying on scoped verification.",
            )
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
        scope_label = _scope_label(
            test_files,
            count_test_files(),
            direct_imports=direct_import_count_for_relevant(files),
            deferred_global=len(deferred_global_crosscutting_for_relevant(files)),
        )
        batches = [
            test_files[offset : offset + _SCOPED_PYTEST_BATCH_SIZE]
            for offset in range(0, len(test_files), _SCOPED_PYTEST_BATCH_SIZE)
        ]
        batch_commands = [
            cmd.replace("{test_files_for_files}", " ".join(shlex.quote(t) for t in batch))
            for batch in batches
        ]
        cmd = " && ".join(batch_commands)

    # A DELETED file cannot be read by a file gate, and until session #235 the
    # declared list went to the command verbatim: `ruff` was handed a path that
    # no longer existed and answered `E902 no such file`, so the whole verify run
    # came back exit=1 with no handle. The only way past it was to leave the
    # deletion OUT of `--relevant-files` — to under-declare on purpose, which is
    # exactly what `declared_scope_status` measures and what decision #348 put in
    # this release to fix. A framework that forces the dishonest answer has no
    # standing to measure honesty.
    #
    # HERE, at ARGUMENT construction, and not where applicability was decided.
    # Whether a gate APPLIES is a question about names — `file_extensions` and
    # `file_patterns` judge `Dockerfile` and `.py` without opening anything, and
    # filtering earlier made seventeen existing tests fail because they ask that
    # question with paths that never existed. Only what the command must OPEN has
    # to be on disk.
    #
    # The declaration and the signed receipt keep the full list, deletions
    # included: the receipt describes the CHANGE, and the change included
    # removing a file.
    # ONLY for a command that actually interpolates `{files}`. A gate whose
    # command never receives the list cannot be broken by a path that is gone —
    # `mypy` reads the source set from pyproject, `probe-tool` takes no
    # arguments at all — and filtering for them would answer "nothing to read"
    # about a command that was not going to read them anyway, masking the real
    # verdict (a missing tool is COULD_NOT_RUN, and that must not be hidden
    # behind NOT_APPLICABLE).
    if files and "{files}" in cmd:
        on_disk = [f for f in files if os.path.exists(f)]
        if not on_disk:
            return _outcome.not_applicable(
                _outcome.REASON_ALL_FILES_DELETED,
                f"All {len(files)} declared file(s) are gone from disk — a file gate "
                "has nothing to read, so this is not a verdict.",
                remedy=(
                    "A task whose product is deletions closes on the gates that CAN "
                    "judge it (tests, state checks), not on this one reporting green."
                ),
            )
        files = on_disk

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
        cmd = re.subn(r"(^|\s)pytest(\s|$)", r"\1pytest -m ''\2", cmd)[0]
        if batch_commands is not None:
            batch_commands = [
                re.subn(r"(^|\s)pytest(\s|$)", r"\1pytest -m ''\2", batch)[0]
                for batch in batch_commands
            ]
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
        if batch_commands is None:
            returncode, raw_output = _run_shellless(cmd, timeout)
        else:
            returncode = 0
            raw_output = ""
            saw_test_batch = False
            for batch in batch_commands:
                returncode, batch_output = _run_shellless(batch, timeout)
                raw_output += batch_output
                if returncode == 0:
                    saw_test_batch = True
                    continue
                # Pytest's exit 5 means this particular batch collected no
                # tests.  It cannot certify a wholly empty run, but it cannot
                # erase tests a prior batch already ran either.
                if is_pytest and returncode == _PYTEST_NO_TESTS_COLLECTED and saw_test_batch:
                    raw_output += "\npytest batch collected no tests; prior batch evidence retained\n"
                    returncode = 0
                    continue
                break
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
