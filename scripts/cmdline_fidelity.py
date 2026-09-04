r"""Refuse to run on a command line that cmd.exe silently ate part of.

WHY THIS EXISTS. `.tausik/tausik.cmd` is the documented Windows entry point.
A caller with no POSIX shell invokes it with an argument list, and Windows
turns that into `cmd.exe /c <wrapper> <args>`. cmd.exe then parses that line
before the batch file runs, so `>`, `<`, `&`, `|` and `^` inside an argument
are acted on as operators. Measured on this machine (session #209, Python
3.11.2), through the wrapper, 5 of 9 hostile arguments were corrupted; the
same 9 passed directly to python were all intact. Two of the corruptions were
SILENT:

    "48->49"  -> argv ["48-"],  rc 0, stdout diverted into a stray file "49"
    "a&b"     -> argv ["a"],    rc 1, the tail "b" executed as a command

The first is the one that cost a handoff in session #200: a truncated value
was stored and the command reported success.

WHAT THIS MODULE DOES, AND WHAT IT DOES NOT. The wrapper hands us the
untouched command line in an environment variable (env survives cmd.exe's
parser). We compare it with the argv that actually arrived. On a discrepancy
we exit non-zero and say what was lost. We do NOT reconstruct the intended
argv, although `CommandLineToArgvW` would return it: a recovered `>` is
indistinguishable from a deliberate `cmd /c "tausik.cmd status > out.txt"`,
and recovery would feed `>` and `out.txt` to the CLI as arguments.

The comparison is normalization-based, not byte-exact: quoting characters
(`"`, `\`, `^`) and whitespace are dropped from both sides before comparing,
because the caller's quoting is legitimately rewritten in transit. So this
detects text that DISAPPEARED or was appended, which is the measured failure
mode. It does not detect a re-ordering that preserves every character.
"""

from __future__ import annotations

import os
import sys
from typing import Mapping, MutableMapping, Sequence

#: Set by the .cmd wrapper to ``%CMDCMDLINE%`` — the line cmd.exe was started
#: with, before its own parser consumed any operator.
RAW_ENV = "TAUSIK_RAW_CMDLINE"

#: Escape hatch for the one legitimate case this guard cannot tell from the
#: defect: a script that deliberately writes ``cmd /c "wrapper ... > file"``.
GUARD_ENV = "TAUSIK_CMDLINE_GUARD"

#: Substring that marks where the wrapper path ends and its arguments begin.
WRAPPER_MARKER = "tausik.cmd"

#: Distinct from argparse's 2 (usage error) and from any handler's exit code,
#: so a caller can tell "your command line was mangled" from "your command
#: was wrong".
EXIT_MANGLED = 3

_QUOTING_CHARS = '"\\^'

#: Operators whose target cmd.exe CREATES at parse time. `<` is deliberately
#: absent: input redirection opens an EXISTING file to read from, so naming its
#: target as "already created, delete it" would be false, and the advice
#: destructive — the operator would be told to delete a file they still need.
#: Found by the fix review of session #209, record #26.
_CREATING_OPERATORS = (">>", ">")


def _normalize(text: str) -> str:
    """Drop quoting and whitespace — what survives is the payload characters."""
    return "".join(c for c in text if not c.isspace() and c not in _QUOTING_CHARS)


def guard_disabled(env: Mapping[str, str] | None = None) -> bool:
    """True when the operator has switched the guard off deliberately."""
    source: Mapping[str, str] = os.environ if env is None else env
    return source.get(GUARD_ENV, "").strip().lower() in {"off", "0", "false", "no"}


def argument_tail(raw: str, marker: str = WRAPPER_MARKER) -> str | None:
    """Return the part of ``raw`` that follows the wrapper path.

    ``None`` means the guard has nothing to say:

    * the raw line does not name the wrapper at all — this is what an
      interactive shell looks like, where ``%CMDCMDLINE%`` is just
      ``cmd.exe`` and a human's ``tausik status > out.txt`` is their own
      deliberate redirection, none of our business;
    * there is no raw line, i.e. we were not started through the .cmd
      wrapper (the POSIX wrapper passes ``"$@"`` and cannot lose anything).

    The FIRST occurrence of the marker is used, not the last: an argument may
    legitimately mention ``tausik.cmd``, the wrapper path may not follow it.
    """
    if not raw:
        return None
    index = raw.lower().find(marker.lower())
    if index == -1:
        return None
    tail = raw[index + len(marker) :]
    if tail.startswith('"'):
        tail = tail[1:]
    return tail


def redirection_targets(tail: str) -> list[str]:
    """Name the files cmd.exe CREATED before the batch file ever ran.

    cmd.exe opens an output-redirection target at parse time, so by the time
    this process can complain, the stray file already exists. Naming it is the
    difference between a warning and a warning the operator can act on.

    Only `>` and `>>` are read. An input redirection (`<`) names a file that
    already existed and that cmd.exe merely opened for reading; listing it here
    would put a file the operator still needs under the message "delete it".
    """
    targets: list[str] = []
    rest = tail
    while rest:
        # Sort by position, then by DESCENDING operator length: at the same
        # index `>>` and `>` both match, and taking `>` would leave the second
        # `>` as the target's first character.
        found = [
            (pos, -len(op), op)
            for pos, op in ((rest.find(op), op) for op in _CREATING_OPERATORS)
            if pos != -1
        ]
        if not found:
            break
        pos, _, op = min(found)
        rest = rest[pos + len(op) :].lstrip()
        if rest.startswith('"'):
            end = rest.find('"', 1)
            target, rest = (rest[1:end], rest[end + 1 :]) if end != -1 else (rest[1:], "")
        else:
            target, _, rest = rest.partition(" ")
        if target:
            targets.append(target)
    return targets


def describe_mismatch(argv: Sequence[str], raw: str | None) -> str | None:
    """Return a diagnostic when the command line lost text, else ``None``."""
    tail = argument_tail(raw or "")
    if tail is None:
        return None
    on_the_line = _normalize(tail)
    that_arrived = _normalize("".join(argv))
    if on_the_line == that_arrived:
        return None

    lines = [
        "Error: the Windows .cmd wrapper could not pass your arguments through",
        "cmd.exe without loss — refusing rather than acting on a truncated value.",
        "",
        f"  on the command line: {tail.strip()}",
        f"  reached this process: {list(argv)}",
    ]
    stray = redirection_targets(tail)
    if stray:
        lines.append(
            "  cmd.exe already created (delete it): " + ", ".join(stray),
        )
    lines += [
        "",
        "Cause: >, <, &, | and ^ stay operators for cmd.exe even inside a",
        "quoted argument list, because the caller's quoting is rewritten before",
        "cmd.exe parses the line.",
        "",
        "Fix: call the POSIX wrapper .tausik/tausik from bash, or use the MCP",
        "tools, neither of which goes through a shell.",
        f"If the redirection was deliberate, set {GUARD_ENV}=off.",
    ]
    return "\n".join(lines)


def enforce(
    argv: Sequence[str] | None = None,
    env: MutableMapping[str, str] | None = None,
    stream=None,
) -> None:
    """Check this process's command line and exit non-zero if text was lost.

    Consumes ``TAUSIK_RAW_CMDLINE`` from the environment: a child process the
    CLI spawns has its own argv and must not be measured against the wrapper's
    command line.
    """
    source: MutableMapping[str, str] = os.environ if env is None else env
    raw = source.pop(RAW_ENV, None)
    if raw is None or guard_disabled(source):
        return
    message = describe_mismatch(sys.argv[1:] if argv is None else argv, raw)
    if message is None:
        return
    print(message, file=sys.stderr if stream is None else stream)
    raise SystemExit(EXIT_MANGLED)
