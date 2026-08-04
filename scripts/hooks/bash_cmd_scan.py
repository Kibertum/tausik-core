r"""Which part of a POSIX command line can actually EXECUTE.

Split out of `bash_firewall` when a second shell dialect appeared. The hook held
three separable things: what is dangerous (now `danger_patterns`), how to read a
POSIX command line (here), and what to do about a hit (still the hook). Keeping
the reader in the hook meant the only way to add a dialect was to teach the hook
about both — and `shell_channel`, which already knew which tool speaks which
shell, could not reach this function without importing the hook that imports it.

The scanner is the same code it always was; only its address changed.
"""

from __future__ import annotations

import os
import shlex

from bash_cmd_norm import _MAX_WRAPPER_DEPTH, _interpreter_payloads

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


def scan_target(command: str, depth: int = 0) -> str:
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

    So a wrapper payload is RE-SCANNED as the command line it is, bounded by
    `_MAX_WRAPPER_DEPTH`. Widening `_CMD_START` to accept a quote was the
    cheaper edit and is deliberately NOT taken: it also blocks
    `bash -c 'echo "git push --force"'`, where the quoted text really is data.
    Descending keeps the token-vs-prose rule intact one level down instead of
    trading a missed command for a blocked echo.

    WHICH wrappers are descended is `_interpreter_payloads`' answer: the 7 POSIX
    shells plus PowerShell (`-c` / `-Command`) and `cmd` (`/c` / `/k`) — the
    command-carrying interpreters, brought to parity with the PowerShell
    scanner's `payloads`, which already descends its whole set. Named residuals,
    the same on both channels: `ssh host '<cmd>'` runs on a remote host this
    firewall cannot reason about; `wsl` has no `-c` form; a language
    interpreter's `-c` (`python -c '<code>'`) is code, not a shell line. For
    those the OUTERMOST layer is still raw-joined and judged, but an inner layer
    hidden behind a surviving quote is not descended into. `-EncodedCommand`
    (base64) is likewise a residual — it is not decoded here.
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
                for payload in _interpreter_payloads(sub):
                    parts.append(scan_target(payload, depth + 1))
        else:
            parts.append(" ".join(_PAYLOAD if len(tok.split()) > 1 else tok for tok in sub))
    return " ; ".join(parts)
