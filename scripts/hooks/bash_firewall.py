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

# "What command is this sub-command REALLY running" — the same normalisation the
# write gate uses. Imported rather than re-derived: this file already had its own
# answer to that question, and the two disagreed at exactly one point (below).
from bash_cmd_norm import _MAX_WRAPPER_DEPTH, _shell_payloads
from rm_wipe_detect import wiped_root

# Patterns that should ALWAYS be blocked — matched against the *command*, not
# against quoted data (see `_scan_target`). The old assumption that these
# strings "are extremely unlikely to appear inside benign commands" turned out
# to be false: journaling the fix for this very bug (`tausik task add --goal
# "... DROP TABLE ..."`) was blocked twice on 2026-07-18.
#
# The `rm` forms that used to live here are NOT substrings — see `_rm_wipes_a_root`.
# Everything left is a phrase whose meaning does not depend on how the command
# around it is spelled, so a substring is the honest test for it: `mkfs.` names
# a program family, `DROP TABLE` is SQL keywords, `dd if=/dev/zero` is one
# idiom. Deliberate, not leftover.
BLOCKED_PATTERNS = [
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

    Both interpolated fragments are wrapped here rather than at the call sites.
    A caller that wrote a bare alternation (`-fd\\b|-df\\b`) handed a top-level
    `|` to this f-string, and that `|` split the WHOLE pattern: those branches
    then ran with no anchor, no path prefix and no `git` in front of them, so
    `ls -df` and `cat notes-df.txt` were both read as a destructive git clean.
    The version that introduced this constructor did so specifically to stop
    `mygit-helper push --force` from false-positiving, and reintroduced the same
    illness one line below. Grouping at the seam means the next pattern cannot
    make that mistake — it is not something each call site must remember.
    """
    # The connector stops at a command separator. `[^\n]*?` did not, so a
    # dangerous-looking argument belonging to the NEXT command could complete a
    # match started by this one (`git clean -n ; tar -fd x`).
    return re.compile(
        rf"{_CMD_START}{_OPT_PATH}git{_OPT_GIT_C}\s+(?:{subcmd})\b[^\n;&|]*?(?:{danger_arg_re})",
        re.IGNORECASE,
    )


# `rm` and everything up to the next command boundary. `_scan_target` has already
# joined sub-commands with ` ; `, so stopping at `;`/`&`/`|` keeps one command's
# operands from being read as another's. `git rm` is excluded by the negative
# lookbehind: it stages a deletion in the index and `git checkout` undoes it, so
# reporting it as "the whole working directory" was simply untrue.
_RM_RE = re.compile(
    rf"{_CMD_START}(?<!git ){_OPT_PATH}rm\b(?P<rest>[^\n;&|]*)",
    re.IGNORECASE,
)


def _rm_wipes_a_root(scanned: str) -> str | None:
    """The tree-root operand of a recursive `rm`, or None.

    This replaced three literal substrings (`rm -rf /`, `rm -rf /*`, `rm -rf .`)
    that were wrong in BOTH directions at once — they fired on any path that
    merely STARTED that way (`rm -rf .venv`, `rm -rf /tmp/scratch`), and missed
    every spelling of the wipe but one (`rm -fr /` and four others were allowed).

    The first attempt then swapped the substrings for an exact-match set of the
    same four spellings, and an exact match cannot see what a prefix match was
    catching by accident: seven operand spellings that had been blocked stopped
    being blocked. `normalise_operand` answers the question the set was
    pretending to — which place does this operand name — so a spelling that
    resolves to the same tree gets the same verdict.

    Residual, stated rather than left to be discovered: an operand that only
    becomes root-ish after expansion (`$HOME`, `${X:-/}`) is not resolvable
    here and is not claimed to be, and `find / -delete` carries its recursion
    in `find`, where no `rm` operand exists to inspect.
    """
    for match in _RM_RE.finditer(scanned):
        target = wiped_root(match.group("rest").split())
        if target is not None:
            return target
    return None


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
        # A flag cluster containing both `f` and `d`, in either order. Written
        # as two lookaheads rather than `-[a-zA-Z]*f[a-zA-Z]*d\b`: that form put
        # two unbounded quantifiers around a literal inside the constructor's
        # own lazy `[^\n]*?`, and the backtracking was super-linear — measured
        # 0.009s / 0.23s / 3.55s on `git clean -` followed by 1k / 5k / 20k
        # `f`s. Every Bash tool call goes through this hook, so that is a stall
        # of the whole session, reachable from one ordinary-looking line. Each
        # lookahead here scans forward once and fails fast.
        # Second branch: the flags written apart (`git clean -f -d`), which the
        # single-cluster form never matched. That gap was asserted closed in a
        # closed task's evidence and was not — the same "one spelling blocked,
        # the rest allowed" shape this file keeps producing.
        _git_subcmd_re(
            "clean",
            r"-(?=[a-zA-Z]*f)(?=[a-zA-Z]*d)[a-zA-Z]+\b"
            r"|-(?=[a-zA-Z]*f)[a-zA-Z]+\b[^\n;&|]{0,80}?-(?=[a-zA-Z]*d)[a-zA-Z]+\b",
        ),
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


def _scan_target(command: str, depth: int = 0) -> str:
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

    One level of that raw join was not enough. `bash -c "sh -c 'git push
    --force'"` reaches this function as three tokens, the last of which still
    carries its INNER quotes; joining them yields `… sh -c 'git push --force'`,
    where the character before `git` is an apostrophe. `_CMD_START` accepts a
    line start or a shell separator, neither of which an apostrophe is, so all
    four WARN patterns missed it while the anchor-less BLOCKED substrings still
    hit — which is why the hole showed up on `git push --force` but not on
    `rm -rf /`, and why nobody noticed. Confirmed allowed (rc=0) before this fix.

    So a shell payload is now RE-SCANNED as the command line it is, bounded by
    `_MAX_WRAPPER_DEPTH`. Widening `_CMD_START` to accept a quote was the
    cheaper edit and is deliberately NOT taken: it also blocks
    `bash -c 'echo "git push --force"'`, where the quoted text really is data.
    Descending keeps the token-vs-prose rule intact one level down instead of
    trading a missed command for a blocked echo.
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
            # …but only the OUTERMOST layer of it. A shell `-c` argument is a
            # command line, not a word: scan it as one.
            if depth < _MAX_WRAPPER_DEPTH:
                for payload in _shell_payloads(sub):
                    parts.append(_scan_target(payload, depth + 1))
        else:
            parts.append(" ".join(_PAYLOAD if len(tok.split()) > 1 else tok for tok in sub))
    return " ; ".join(parts)


def main() -> int:
    # This hook's block messages now quote the offending operand and use an
    # em dash, so they are no longer pure ASCII — and a block message that
    # renders as mojibake is a block whose reason the reader has to guess.
    # Local import: hooks/ is sys.path[0] only when run as a script.
    from _common import force_utf8_io

    force_utf8_io()

    if os.environ.get("TAUSIK_SKIP_HOOKS"):
        from _common import emit_supervision_bypass

        emit_supervision_bypass(
            os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()), "skip_hooks", "bash_firewall"
        )
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

    wiped = _rm_wipes_a_root(scanned)
    if wiped is not None:
        print(
            f"BLOCKED: recursive force-delete of {wiped!r} — that is the whole "
            f"filesystem or the whole working directory. Command: {command}",
            file=sys.stderr,
        )
        return 2

    for pattern, reason in BLOCKED_PATTERNS:
        if pattern.lower() in cmd_lower:
            print(f"BLOCKED: {reason}. Command: {command}", file=sys.stderr)
            return 2

    for regex, reason in WARN_PATTERNS_RE:
        if regex.search(scanned):
            # The old line said "ask the user for explicit confirmation first",
            # describing a mechanism that was never built: there is no
            # post-confirmation path here, so the user says yes and the hook
            # blocks identically. A remediation that cannot be carried out
            # teaches the reader that the messages are decorative. Name the
            # escape that exists — and that leaves a countable trace.
            print(
                f"BLOCKED: {reason}.\n"
                f"Command: {command}\n"
                "Confirming with the user does NOT unblock this - the gate has no "
                "approval path. Use a non-destructive equivalent, or (with the user's "
                "agreement) re-run that one command with TAUSIK_SKIP_HOOKS=1 set; the "
                "bypass is recorded as a supervision event.",
                file=sys.stderr,
            )
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
