r"""What does this PowerShell command WRITE, and does it wipe a root.

The dialect twin of `bash_write_parse` + the `Remove-Item` half of
`rm_wipe_detect`. Pure, side-effect-free parsing: the enforcement half stays in
the gates, which apply the SAME verdict to both channels by importing the same
decision functions rather than re-deriving them.

The split of responsibility is deliberate and is the whole architectural point
of the task that created this file:

  * WHICH PLACES COUNT AS "EVERYTHING" is one question, answered once, in
    `rm_wipe_detect.is_wipe_root`. Both dialects ask it.
  * HOW THIS DIALECT SPELLS "recursively, forcibly" is a different question,
    answered here, because `-Recurse` and `-rf` have nothing in common but
    meaning.

Two copies of the first question is how this file's POSIX twin acquired three
regressions in one session (see `rm_wipe_detect`'s header). One judge, two flag
parsers.

Residual, named rather than left to be found: see `pwsh_cmd_parse`'s header —
pipeline targets, `-EncodedCommand`, computed paths and .NET calls are not
parsed. `Remove-Item` of a project file is NOT reported as a write target,
which is exact parity with the Bash gate (`rm` is not a writer there either);
that gap belongs to both channels equally and is filed separately rather than
closed on one side only, which would put the two channels back out of step.
"""

from __future__ import annotations

import os
import re
import sys

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)

import python_source_writes  # noqa: E402 — shared with the POSIX channel, see `_parse`
from pwsh_cmd_norm import _MAX_WRAPPER_DEPTH, payloads  # noqa: E402
from pwsh_cmd_parse import (  # noqa: E402,F401 — `tokenize` re-exported: it is
    # this dialect's entry point in `shell_channel`'s table, alongside
    # `write_targets`. One table, so a consumer cannot pick a dialect by hand.
    _REDIR_TOKEN_RE,
    Statement,
    split_statements,
    tokenize,
)
from rm_wipe_detect import is_wipe_root  # noqa: E402
from write_confidence import CONFIDENCE_PARSED, CONFIDENCE_REGEX_FALLBACK  # noqa: E402

#: Cmdlet -> the parameters naming its write target, in the order PowerShell
#: binds them positionally. `positional` is the index of the bare argument that
#: lands on that parameter when it is not named: `Set-Content notes.md "x"`
#: writes notes.md, and its second bare argument is the CONTENT, not a file.
#: Getting that index wrong invents a phantom target, and a gate that blocks a
#: file the command never touches teaches the agent to route around it (#291).
_WRITERS: dict[str, tuple[tuple[str, ...], int | None]] = {
    "set-content": (("path", "literalpath"), 0),
    "add-content": (("path", "literalpath"), 0),
    "clear-content": (("path", "literalpath"), 0),
    "out-file": (("filepath", "literalpath"), 0),
    "new-item": (("path",), 0),
    "tee-object": (("filepath",), 0),
    "copy-item": (("destination",), 1),
    "move-item": (("destination",), 1),
    "rename-item": (("newname",), 1),
    "invoke-webrequest": (("outfile",), None),
    "invoke-restmethod": (("outfile",), None),
    "export-csv": (("path", "literalpath"), 0),
    "export-clixml": (("path",), 0),
    "set-itemproperty": (("path", "literalpath"), 0),
    "start-transcript": (("path",), 0),
}

#: A token still carrying an unexpanded variable or subexpression names no path
#: we can resolve — the documented residual, dropped rather than guessed at.
#: `$env:TEMP\x`, `$root`, `$(Join-Path a b)` all land here.
_UNRESOLVABLE = ("$", "`", "\n")


def _plausible_path(tok: str) -> bool:
    return bool(tok) and not any(ch in tok for ch in _UNRESOLVABLE)


def _redirect_targets(tokens: list[str]) -> list[str]:
    """Files created by `>` / `>>` in one statement.

    `2>&1` and `>&2` are fd dups, not files: their operator token carries `&`,
    which is why the tokenizer keeps the operator whole instead of splitting it.
    """
    out: list[str] = []
    for i, tok in enumerate(tokens):
        if not _REDIR_TOKEN_RE.match(tok) or "&" in tok:
            continue
        if i + 1 < len(tokens):
            nxt = tokens[i + 1]
            if not nxt.startswith("&") and not _REDIR_TOKEN_RE.match(nxt):
                out.append(nxt)
    return out


def _paths_for_host(argv: list[str]) -> list[str]:
    """The path-shaped tokens of `argv` in the HOST's separator.

    In PowerShell a backslash is a path separator, on every host, for the
    shell's OWN path handling. For an argument handed to a NATIVE command
    (`python .\\helper.py`) pwsh on Linux forwards the token verbatim, and
    Python then fails to open `.\\helper.py` — so the command would not have
    run the script at all. The gate normalises anyway, and the reason is the
    gate's stated policy, not the shell's: it OVER-detects. Measured on the
    first Linux run of this lane (pipeline #6658): the dialect handed the token
    to the dialect-neutral resolver as it stood, `os.path` on POSIX found no
    such file, and fail-soft turned "unresolved" into "writes nothing" — gate
    0 for this spelling while the other four refused. Reading the script the
    author plainly meant, on either host, is the direction that errs toward a
    task, and it keeps the two channels from disagreeing about one command.
    On Windows `os.sep` IS the backslash and this is the identity.

    Only tokens that can be a path are touched: not the payload after `-c`
    (Python source, where `\\n` is an escape) or the name after `-m`, and
    nothing carrying a quote or a newline — a path may carry a space (`'my
    dir\\x.py'` arrives as one token), a quote it may not. A POSIX shell reads the same
    backslash as an ESCAPE, so this stays in the PowerShell dialect and the
    Bash channel keeps reading `.\\helper.py` as `.helper.py`.
    """
    out: list[str] = []
    prev = ""
    for tok in argv:
        if "\\" in tok and prev not in ("-c", "-m") and not any(ch in tok for ch in "\n'\""):
            tok = tok.replace("\\", os.sep)
        out.append(tok)
        prev = tok
    return out


def _script_argv(stmt: Statement) -> list[str]:
    """The tokens naming the program this statement runs, and its arguments.

    Usually the statement's own tokens: `& python helper.py` arrives here with
    the call operator already split off as a separator, and `python .\\x.py`
    needs only its separator spelled for the host (`_paths_for_host` — on POSIX
    the backslash is otherwise a character of the file name). The one shape
    that hides the program is `Start-Process`, which takes it as an operand
    instead of standing in command position — the PowerShell spelling of the
    wrapper problem the POSIX side solves with `_strip_prefixes`.

    RESIDUAL, STATED: `-ArgumentList` is split on whitespace, so a single quoted
    argument containing a space is read as two. That mis-splits an argument, it
    does not lose the SCRIPT, which is the first operand either way — and the
    reader below only ever uses the script. `Start-Process` behind a variable,
    or an argument list built at runtime, is not read at all; that is the same
    computed-path residual both channels already document.
    """
    if stmt.verb != "start-process":
        return _paths_for_host(stmt.tokens)
    argv: list[str] = []
    target = stmt.param("filepath")
    if target is not None:
        argv.append(target)
    argv += stmt.positionals
    arguments = stmt.param("argumentlist")
    if arguments:
        argv += arguments.split()
    return _paths_for_host(argv)


def _writer_targets(stmt: Statement) -> list[str]:
    """Files the cmdlet itself writes, by named parameter or by position."""
    spec = _WRITERS.get(stmt.verb)
    if spec is None:
        return []
    names, positional = spec
    named = stmt.param(*names)
    if named is not None:
        return [named]
    if positional is None or positional >= len(stmt.positionals):
        return []
    return [stmt.positionals[positional]]


#: Fallback for a command that does not tokenize. Catches `> file`, `>> file`
#: and the named target of the common writer parameters. Over-detects on
#: purpose, exactly like its POSIX counterpart: a missed write is a hole, an
#: extra candidate at worst asks for a task the write would have needed anyway.
_FALLBACK_RE = re.compile(
    r"(?<![0-9*])>>?\s*([^\s;&|<>()]+)"
    r"|-(?:Path|LiteralPath|FilePath|Destination|OutFile)\s+([^\s;&|<>()]+)",
    re.IGNORECASE,
)


def _fallback_targets(command: str) -> list[str]:
    out: list[str] = []
    for redirect, named in _FALLBACK_RE.findall(command):
        tgt = redirect or named
        if tgt and not tgt.startswith("&"):
            out.append(tgt.strip("\"'"))
    return out


def write_targets_with_confidence(
    command: str, base_dir: str | None = None
) -> tuple[list[str], str]:
    """`(targets, confidence)` — see `write_confidence` for what to do with it.

    A command that will not tokenize used to yield an empty list here, which
    reads to every consumer as "this command writes nothing" — a silent allow,
    and the worst possible failure shape for a gate. The POSIX parser had
    already learned this and answers with a guess plus a confidence flag; the
    two channels must fail the same way or the weaker one becomes the route.

    `base_dir` is the directory a RELATIVE path in this command resolves
    against — the script this parser opens is named by the command, so it is
    relative to the shell, not to the project. The argument was already in this
    signature before there was anything to resolve, because the dispatcher used
    to ask `if module is bash_write_parse` before passing it: a dialect
    enumeration inside the module written to abolish dialect enumerations, and
    covered by no test. Removing that branch is what let this parser start
    reading files without anyone editing the dispatcher — which is the whole
    argument for a uniform signature, arriving one task later as a fact.
    """
    targets, confidence = _parse(command, 0, base_dir)
    return [t for t in targets if _plausible_path(t)], confidence


def _parse(command: str, depth: int, base_dir: str | None = None) -> tuple[list[str], str]:
    tokens = tokenize(command)
    if tokens is None:
        return _fallback_targets(command), CONFIDENCE_REGEX_FALLBACK
    out: list[str] = []
    confidence = CONFIDENCE_PARSED
    for sub in split_statements(tokens):
        if not sub:
            continue
        stmt = Statement(sub)
        out += _redirect_targets(sub)
        out += _writer_targets(stmt)
        # The code a command RUNS is a write vector, not just the code it
        # quotes. The POSIX channel learned this in #201; this one was left out
        # of that task deliberately, and stayed out long enough for the miss to
        # be measured here: `python helper.py` on the PLATFORM'S PRIMARY SHELL
        # put a file outside the task's ACL with the gate returning 0. Five
        # spellings, all of them the ordinary ones.
        #
        # Which paths a Python source opens is `python_source_writes`' answer,
        # shared verbatim with the POSIX channel — including the narrowness that
        # keeps `python -m pytest x.py` from being read as running `x.py`. Only
        # WHICH TOKENS name the program differs between the dialects, and that
        # difference is `_script_argv`, which is all of this module's business.
        argv = _script_argv(stmt)
        out += python_source_writes.writes_in_inline_code(argv)
        out += python_source_writes.writes_in_script_file(argv, base_dir)
        if depth < _MAX_WRAPPER_DEPTH:
            for payload in payloads(stmt):
                inner, inner_conf = _parse(payload, depth + 1, base_dir)
                out += inner
                # An uncertain part makes the whole list uncertain: reporting
                # `parsed` because the OUTER command parsed is the more
                # confident of two readings, and the wrong one to hand a
                # consumer that fails closed on uncertainty.
                if inner_conf == CONFIDENCE_REGEX_FALLBACK:
                    confidence = CONFIDENCE_REGEX_FALLBACK
    return out, confidence


def write_targets(command: str, base_dir: str | None = None) -> list[str]:
    """Every path this PowerShell command appears to write. Best-effort.

    Descends into wrapper payloads (`powershell -Command "…"`, `cmd /c "…"`,
    `iex "…"`) exactly as the POSIX parser does: a write hidden one quoting
    level down is the everyday bypass, not an exotic one.

    Confidence-blind on purpose, matching the POSIX signature: QG-0 wants the
    over-detecting answer. A caller that cannot afford a false positive asks
    `write_targets_with_confidence` instead.

    `base_dir` is part of the shared dialect signature; see the twin for why it
    is accepted here rather than branched around by the caller.
    """
    targets, _confidence = write_targets_with_confidence(command, base_dir)
    return targets


def wiped_root(command: str, depth: int = 0) -> str | None:
    """The tree-root operand of a recursive `Remove-Item`, or None.

    Force is deliberately NOT required, for the reason the POSIX twin records:
    every command this hook sees runs non-interactively, so there is no prompt
    for the missing `-Force` to suppress. Requiring it costs an attacker one
    word and a mistake nothing.

    `-Recurse` IS required — the same shape as the POSIX rule needing `-r`, so
    the two channels answer alike. Without it `Remove-Item C:\\` cannot empty a
    non-empty tree, and treating it as a wipe would block ordinary cleanup.
    """
    tokens = tokenize(command)
    if tokens is None:
        return None
    for sub in split_statements(tokens):
        if not sub:
            continue
        stmt = Statement(sub)
        if stmt.verb == "remove-item" and stmt.has_switch("recurse"):
            candidates = [c for c in (stmt.param("path", "literalpath"),) if c is not None]
            candidates += stmt.positionals
            for target in candidates:
                if is_wipe_root(target):
                    return target
        if depth < _MAX_WRAPPER_DEPTH:
            for payload in payloads(stmt):
                found = wiped_root(payload, depth + 1)
                if found is not None:
                    return found
    return None
