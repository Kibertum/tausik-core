#!/usr/bin/env python3
"""PreToolUse hook: block dangerous bash commands.

Blocks: rm -rf /, DROP TABLE, git reset --hard, git push --force to main.
Exit codes: 0 = allow, 2 = block.
Receives JSON on stdin with tool_name, tool_input.

v1.3.4 (med-batch-1-hooks #1): WARN patterns now use regex with word
boundaries instead of substring match — `echo "git push --force"` and
`mygit-helper push --force` no longer false-positive. Shape mirrors
`git_push_gate.py:_GIT_PUSH_RE`: command-start anchor (line start, or
shell separator) + optional path prefix + literal subcommand.
"""

import json
import os
import re
import shlex
import sys

# Patterns that should ALWAYS be blocked — matched against the *command*, not
# against quoted data (see `_scan_target`). The old assumption that these
# strings "are extremely unlikely to appear inside benign commands" turned out
# to be false: journaling the fix for this very bug (`tausik task add --goal
# "... DROP TABLE ..."`) was blocked twice on 2026-07-18.
BLOCKED_PATTERNS = [
    ("rm -rf /", "Recursive delete from root"),
    ("rm -rf /*", "Recursive delete from root"),
    ("rm -rf .", "Recursive delete from current directory"),
    ("DROP TABLE", "SQL table drop"),
    ("DROP DATABASE", "SQL database drop"),
    ("TRUNCATE TABLE", "SQL table truncate"),
    (":(){:|:&};:", "Fork bomb"),
    ("mkfs.", "Filesystem format"),
    ("dd if=/dev/zero", "Disk wipe"),
    ("> /dev/sda", "Disk overwrite"),
]

# Boundary that prefixes a command in a shell line: start of input, or
# any of the shell separators / operators. Mirrors git_push_gate.py.
_CMD_START = r"(?:^|[\s;&|()`])"
# Optional path prefix like `/usr/bin/git` or `./git` or `mygit\`. The
# path component must end with `/` or `\` so a bare token like `gitfoo`
# never matches.
_OPT_PATH = r"(?:[/\w.\\-]*[/\\])?"
# Optional `git -c key=val` flags between `git` and the subcommand.
_OPT_GIT_C = r"(?:\s+-c\s+\S+)*"


def _git_subcmd_re(subcmd: str, danger_arg_re: str) -> re.Pattern:
    """Build a regex that matches `git <subcmd> ... <dangerous-arg>`.

    Preserves git_push_gate's anchor + path-prefix + -c-flag handling.
    Dangerous arg can appear anywhere after the subcommand (including
    after positional args like `git push origin main --force`).
    """
    return re.compile(
        rf"{_CMD_START}{_OPT_PATH}git{_OPT_GIT_C}\s+{subcmd}\b[^\n]*?{danger_arg_re}",
        re.IGNORECASE,
    )


# Patterns that need confirmation (exit 2 with explanation).
# Each entry: (compiled_regex, human_reason).
WARN_PATTERNS_RE = [
    (
        _git_subcmd_re("reset", r"--hard\b"),
        "git reset --hard discards all local changes permanently",
    ),
    (
        _git_subcmd_re("push", r"(?:--force(?:-with-lease)?\b|--force\b|-f\b)"),
        "git push --force / -f can overwrite remote history",
    ),
    (
        _git_subcmd_re("clean", r"-[a-zA-Z]*f[a-zA-Z]*d\b|-fd\b|-df\b"),
        "git clean -fd removes untracked files permanently",
    ),
    (
        _git_subcmd_re("checkout", r"--\s+\."),
        "git checkout -- . discards all unstaged changes",
    ),
]


# Programs that EXECUTE their arguments rather than consuming them as data.
# For these, a dangerous phrase inside quotes is still a command and must stay
# in scope. For everything else, quoted text is payload — a journal entry, a
# commit message, a grep needle — and matching it is a false positive.
_INTERPRETERS = frozenset(
    {
        "sh",
        "bash",
        "zsh",
        "dash",
        "ksh",
        "fish",
        "csh",
        "tcsh",
        "sqlite3",
        "psql",
        "mysql",
        "mariadb",
        "mongosh",
        "redis-cli",
        "python",
        "python3",
        "perl",
        "ruby",
        "node",
        "deno",
        "php",
        "eval",
        "ssh",
        "env",
        "xargs",
        "nohup",
        "sudo",
        "doas",
    }
)

# Shell operators that put the NEXT token back into command position.
_SEPARATORS = frozenset({";", "&&", "||", "|", "&"})

_SQ_SPAN_RE = re.compile(r"'[^']*'")
_DQ_SPAN_RE = re.compile(r'"[^"]*"')


def _command_position_tokens(tokens: list[str]) -> list[str]:
    """Tokens that sit where a program name goes (start, or after a separator)."""
    out: list[str] = []
    expect_cmd = True
    for tok in tokens:
        if tok in _SEPARATORS:
            expect_cmd = True
            continue
        if expect_cmd:
            out.append(tok)
            expect_cmd = False
    return out


def _invokes_interpreter(command: str) -> bool:
    """True when any program being invoked executes its arguments.

    Unparseable input (unbalanced quotes) returns True: scanning too much is a
    false positive, scanning too little is a missed dangerous command.
    """
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        return True
    for tok in _command_position_tokens(tokens):
        base = os.path.basename(tok).lower()
        if base in _INTERPRETERS or base.removesuffix(".exe") in _INTERPRETERS:
            return True
    return False


def _scan_target(command: str) -> str:
    """The part of `command` that is actually a command.

    `sqlite3 db "DROP TABLE x"` executes its quoted argument, so the whole line
    is scanned. `tausik task log "... DROP TABLE ..."` merely stores it, so the
    quoted spans are blanked before matching. Without this split the firewall
    blocks its own project's journaling — observed twice while fixing it.
    """
    if _invokes_interpreter(command):
        return command
    return _DQ_SPAN_RE.sub(" ", _SQ_SPAN_RE.sub(" ", command))


def main() -> int:
    if os.environ.get("TAUSIK_SKIP_HOOKS"):
        return 0

    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    command = data.get("tool_input", {}).get("command", "").strip()
    if not command:
        return 0

    # Match against the command, not against quoted data it merely carries.
    scanned = _scan_target(command)
    cmd_lower = scanned.lower()

    for pattern, reason in BLOCKED_PATTERNS:
        if pattern.lower() in cmd_lower:
            print(f"BLOCKED: {reason}. Command: {command}", file=sys.stderr)
            return 2

    for regex, reason in WARN_PATTERNS_RE:
        if regex.search(scanned):
            print(
                f"BLOCKED: {reason}.\n"
                f"Command: {command}\n"
                f"If you really need this, ask the user for explicit confirmation first.",
                file=sys.stderr,
            )
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
