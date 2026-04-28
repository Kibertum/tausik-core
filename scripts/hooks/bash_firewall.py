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
import sys

# Patterns that should ALWAYS be blocked. Substring match is acceptable
# here because these strings are extremely unlikely to appear inside benign
# commands or quoted strings worth supporting (no one echoes "rm -rf /").
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

    cmd_lower = command.lower()

    for pattern, reason in BLOCKED_PATTERNS:
        if pattern.lower() in cmd_lower:
            print(f"BLOCKED: {reason}. Command: {command}", file=sys.stderr)
            return 2

    for regex, reason in WARN_PATTERNS_RE:
        if regex.search(command):
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
