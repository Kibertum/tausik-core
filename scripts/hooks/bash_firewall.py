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
        "cmd",
        "powershell",
        "pwsh",
        "wsl",
        "exec",
        "timeout",
        "nice",
        "ionice",
        "taskset",
        "setsid",
        "stdbuf",
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

#: Stands in for a token carrying free text rather than command words. Contains
#: no character used by any BLOCKED or WARN pattern, so substituting it can
#: never manufacture a match.
_PAYLOAD = "_"


#: Operators that end one command and start the next.
_SEPARATORS = frozenset({";", "&&", "||", "|", "&", "(", ")", "\n"})


def _split_subcommands(tokens: list[str]) -> list[list[str]]:
    """Split a token stream into independent commands on shell operators.

    Each sub-command is judged on its own. Without this, one interpreter
    anywhere on the line forced a raw scan of the WHOLE line, so a journal entry
    sharing a line with `python -m pytest` was blocked again for the phrase it
    merely quoted — the false positive this control was fixed to stop.
    """
    out: list[list[str]] = []
    current: list[str] = []
    for tok in tokens:
        if tok in _SEPARATORS:
            if current:
                out.append(current)
                current = []
            continue
        current.append(tok)
    if current:
        out.append(current)
    return out


def _mentions_interpreter(tokens: list[str]) -> bool:
    """True when ANY token names a program that executes what it is given.

    Deliberately not limited to command position: a wrapper hides the real
    interpreter behind itself. A `timeout 10 bash -c "<payload>"` line puts
    `timeout` in command position and the shell two tokens later, and checking
    only the former let the payload straight through — a confirmed bypass.
    """
    for tok in tokens:
        base = os.path.basename(tok).lower()
        if base in _INTERPRETERS or base.removesuffix(".exe") in _INTERPRETERS:
            return True
    return False


def _scan_target(command: str) -> str:
    """The part of `command` that can actually execute.

    The discriminator is TOKEN BOUNDARIES, not quoting. Quoting does not make
    text inert: a quoted slash argument deletes exactly what a bare one does,
    and bash still expands inside double quotes. What separates a command from
    prose is how the words are split — a real command's words arrive as SEPARATE
    tokens, while a mention inside a quoted argument arrives as ONE token
    ("note: never DROP TABLE events"). So multi-word tokens become a placeholder
    and single-word tokens are kept verbatim.

    Anything naming an interpreter is scanned raw: there the quoted blob is the
    command, so token structure says nothing useful about it.

    An earlier version blanked quoted spans instead. That was unsound: it let a
    quoted-slash recursive delete, a quoted force flag, and a wrapper-hidden
    shell payload all pass — each of them blocked before the change and
    confirmed allowed after it, which is why the rule is token-based now.
    """
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        # Unparseable (unbalanced quotes): scan everything. Over-scanning is a
        # false positive; under-scanning is a missed destructive command.
        return command
    if not tokens:
        return command
    parts: list[str] = []
    for sub in _split_subcommands(tokens):
        if _mentions_interpreter(sub):
            # The quoted blob IS this sub-command; join it back so the payload
            # is scanned. Joining also drops the quoting, which is the point.
            parts.append(" ".join(sub))
        else:
            parts.append(" ".join(_PAYLOAD if len(tok.split()) > 1 else tok for tok in sub))
    return " ; ".join(parts)


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
