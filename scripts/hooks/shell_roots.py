r"""Which directories a relative path in ONE command may resolve against.

A write gate turns `helper.py` into an absolute path before it can ask whether
the write is inside the project. The directory it resolves against used to be a
single value, and the value kept being wrong in a new way each time it was
fixed:

1. It was the PROJECT directory, asserted to be the shell's cwd. False the
   moment the agent works in a second checkout (#204).
2. It became the event's `cwd` field, which is measured and real — but is where
   the shell stood BEFORE the command ran. `cd <project> && python helper.py`
   turned a block into an allow, a regression review #6 caught in the session
   that introduced it (#205, memory #524).
3. It became the UNION of those two: the pre-command cwd and the project root.
   That covers a command walking INTO the project and nothing else. A command
   walking into a THIRD directory — the ordinary shape when two checkouts are
   open — resolves against neither, and the memory-route gate went on reading a
   script out of a tree the command never enters.

The three fixes have one shape in common: each guessed a root instead of asking
where the command GOES. So this module asks. `cd`, `pushd`, `chdir` and
`env -C` name their destination in the command text; that destination is read
and returned alongside the starting directory.

WHY A LIST AND NOT AN ANSWER. A shell can end up somewhere this parser cannot
compute — `cd "$BUILD_DIR"`, `popd`, a destination behind a substitution. For a
containment gate the safe direction is settled: an extra candidate root costs a
task the write would have needed anyway, while missing the real one loses the
write entirely. So the roots are unioned and never chosen between, and the
starting directory and the project root always remain in the list no matter
what else is found.

Stdlib-only and import-light: this runs in a PreToolUse hook on every command.
"""

from __future__ import annotations

import os
import sys

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)

# Tokenization and statement splitting are the scanner's, not a second copy.
# `command_changes_directory` already answers the yes/no question for the
# dangerous-command gate; this module answers the follow-up it never asked.
from bash_cmd_scan import (  # noqa: E402
    _has_chdir_flag,
    _split_subcommands,
    _tokens_of,
    command_changes_directory,
)

#: Command words that name their destination as a positional argument. `popd`
#: is deliberately absent: it moves the shell to a directory recorded earlier in
#: a stack this parser never saw, so it has no literal to offer. It still counts
#: as a directory change to `command_changes_directory`, which is what makes the
#: fallback root below matter rather than being belt-and-braces.
_POSITIONAL_CHANGERS = frozenset({"cd", "pushd", "chdir"})

#: A destination still carrying one of these after posix tokenization is an
#: unexpanded variable or a command substitution — `cd "$BUILD_DIR"` arrives
#: here as the literal `$BUILD_DIR`. Joining that to anything produces a root no
#: filesystem has, which is not merely useless: it would read as a destination
#: FOUND, and the honest answer is that the shell moves somewhere this parser
#: cannot compute. Dropping it leaves `command_changes_directory` saying yes
#: with no literal to offer, which is exactly the case the fallback root covers.
#: Same reasoning, same characters, as the residual `bash_write_parse` documents
#: for write targets.
_UNRESOLVED = set("$`")


def default_root() -> str:
    """The root a relative path falls back to when no caller supplies one."""
    return os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def _chdir_value(args: list[str]) -> str | None:
    """The directory an `env -C DIR` / `env --chdir=DIR` prefix moves into."""
    for i, a in enumerate(args):
        if a in ("-C", "--chdir") and i + 1 < len(args):
            return args[i + 1]
        if a.startswith("--chdir="):
            return a.split("=", 1)[1]
    return None


def _first_operand(args: list[str]) -> str | None:
    """The first non-flag argument, honouring `--` as end-of-options.

    `cd -- -weird-dir` is how a directory whose name begins with a dash is
    named, and reading `-weird-dir` as a flag drops the real destination — the
    widening this module exists for then silently loses the root it was supposed
    to add. `bash_write_parse._positionals` already reads `--` this way; not
    doing so here was an inconsistency inside one package, found by review #7.
    """
    seen_end = False
    for a in args:
        if not seen_end and a == "--":
            seen_end = True
            continue
        if seen_end or not a.startswith("-"):
            return a
    return None


def destinations(command: str) -> list[str]:
    """Directories this command names as somewhere to move the shell to.

    Literal destinations only, in the order they appear. A destination that is
    a variable, a substitution or `cd -` yields nothing here — see the module
    docstring for why that is a widening rather than a hole.

    Asked of the TOKEN stream, so a path that merely contains the word
    (`cp cd.txt out`, `echo "cd /tmp"`) is not read as a directory change: only
    a command word counts, exactly as `command_changes_directory` decides it.
    """
    tokens = _tokens_of(command)
    if tokens is None:
        return []
    out: list[str] = []
    for sub in _split_subcommands(tokens):
        if not sub:
            continue
        base = os.path.basename(sub[0]).lower().removesuffix(".exe")
        value: str | None = None
        if base in _POSITIONAL_CHANGERS:
            value = _first_operand(sub[1:])
        elif base == "env" and _has_chdir_flag(sub[1:]):
            value = _chdir_value(sub[1:])
        if not value or value == "-":
            continue
        if _UNRESOLVED & set(value):
            continue
        if value not in out:
            out.append(value)
    return out


def resolution_roots(command: str, base_dir: str | None = None) -> list[str]:
    """Every directory a relative path in `command` may resolve against.

    The first element is where the shell stands when the command starts —
    `base_dir` when the caller measured it, the project root otherwise. That
    ordering matters to callers that keep the first answer's confidence: the
    starting directory is the reading that is right for a command which never
    moves, which is nearly all of them.

    Further elements appear only when the command moves the shell: each literal
    destination, resolved against the starting directory when itself relative,
    and then the project root — which stays in the list even when a destination
    was found, because a command can move more than once and only the last move
    before an interpreter runs decides, and this module does not model order.
    """
    start = base_dir or default_root()
    roots = [start]
    if not command_changes_directory(command):
        return roots
    for dest in destinations(command):
        # `cd ~/other` is an ordinary way to name the other checkout, and
        # without this the tilde is joined to `start` as a literal directory
        # name — a root no filesystem has, which reads as a destination FOUND
        # and quietly replaces the real one. Same omission, same commit, as the
        # script-path site in `bash_write_parse`.
        dest = os.path.expanduser(dest)
        cand = dest if os.path.isabs(dest) else os.path.join(start, dest)
        if cand not in roots:
            roots.append(cand)
    fallback = default_root()
    if fallback not in roots:
        roots.append(fallback)
    return roots
