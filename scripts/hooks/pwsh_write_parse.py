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


def write_targets_with_confidence(command: str) -> tuple[list[str], str]:
    """`(targets, confidence)` — see `write_confidence` for what to do with it.

    A command that will not tokenize used to yield an empty list here, which
    reads to every consumer as "this command writes nothing" — a silent allow,
    and the worst possible failure shape for a gate. The POSIX parser had
    already learned this and answers with a guess plus a confidence flag; the
    two channels must fail the same way or the weaker one becomes the route.
    """
    targets, confidence = _parse(command, 0)
    return [t for t in targets if _plausible_path(t)], confidence


def _parse(command: str, depth: int) -> tuple[list[str], str]:
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
        if depth < _MAX_WRAPPER_DEPTH:
            for payload in payloads(stmt):
                inner, inner_conf = _parse(payload, depth + 1)
                out += inner
                # An uncertain part makes the whole list uncertain: reporting
                # `parsed` because the OUTER command parsed is the more
                # confident of two readings, and the wrong one to hand a
                # consumer that fails closed on uncertainty.
                if inner_conf == CONFIDENCE_REGEX_FALLBACK:
                    confidence = CONFIDENCE_REGEX_FALLBACK
    return out, confidence


def write_targets(command: str) -> list[str]:
    """Every path this PowerShell command appears to write. Best-effort.

    Descends into wrapper payloads (`powershell -Command "…"`, `cmd /c "…"`,
    `iex "…"`) exactly as the POSIX parser does: a write hidden one quoting
    level down is the everyday bypass, not an exotic one.

    Confidence-blind on purpose, matching the POSIX signature: QG-0 wants the
    over-detecting answer. A caller that cannot afford a false positive asks
    `write_targets_with_confidence` instead.
    """
    targets, _confidence = write_targets_with_confidence(command)
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
