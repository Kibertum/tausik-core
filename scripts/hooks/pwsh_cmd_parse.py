r"""What is this PowerShell command REALLY running — the dialect layer.

`powershell-tool-bypasses-bash-firewall`. Every hook in this directory answered
one shell: POSIX. On win32 — the platform CLAUDE.md, the docs and the `.cmd`
wrapper all call primary — the agent is handed a SEPARATE `PowerShell` tool,
matched by no PreToolUse hook at all. The supervision was whole by RULE and
holed by CHANNEL, which is the harder kind to notice: every test passed,
because every test asked the covered channel.

Reusing the POSIX tokenizer was tried and is wrong at the first character that
matters. `shlex(posix=True)` treats `\` as an escape, so `Remove-Item C:\`
either loses the backslash or raises; PowerShell's escape is a BACKTICK and `\`
is an ordinary path character. A dialect needs its own tokenizer or it silently
mis-reads exactly the operands that make a command dangerous.

What this parser does NOT claim — the pipeline as a target carrier,
`-EncodedCommand`, computed paths, .NET calls — and how every data-carrying
construct (`@'…'@`, quotes, script blocks, `$(…)`) is handled, live in
`docs/{ru,en}/enforcement-coverage.md`, once. A second copy here would be a
second copy of a boundary statement, and this whole module exists because a
second copy of a rule is what kept breaking these hooks. The contract permits
"close it or state the boundary" — it does not require stating it twice.

The bar this raises is the same one `bash_write_gate` raised for Bash: from
"the everyday spelling walks through" to "you must actively obfuscate".
"""

from __future__ import annotations

import os
import re

#: Operators that end one statement and start the next. A newline is normalised
#: to `;` by the tokenizer, so both arrive here as one symbol.
_SEPARATORS = frozenset({";", "|", "||", "&&", "&", "(", ")", "{", "}"})

#: `2>`, `>`, `>>`, `*>>`, `>&1` — a redirection operator as ONE token. Kept
#: whole so the write detector can tell `> file` (a write) from `2>&1` (an fd
#: dup, whose token carries `&`).
_REDIR_TOKEN_RE = re.compile(r"^(?:\d+|\*)?>>?&?\d*$")

_QUOTES = "'\"\u2018\u2019\u201c\u201d"

#: PowerShell's smart-quote forms are REAL quotes to the parser — pasted text
#: routinely carries them, and treating them as ordinary characters would let a
#: quoted-out payload read as bare command words (or the reverse).
_SMART_TO_PLAIN = {"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'}


def _here_string(command: str, i: int) -> tuple[str, int] | None:
    """`(body, index_after)` if a here-string opens at `i`, else None.

    `@'\u2026'@` and `@"\u2026"@` carry DATA. PowerShell opens one only when the quote is
    the last thing on its line, and closes it only on a terminator that BEGINS
    a line \u2014 both conditions are enforced here, because relaxing either is how
    the body gets re-exposed as live shell.

    Why this exists: without it an apostrophe anywhere in the body ("the hook
    doesn't know") ended the ordinary quote scan, the command failed to tokenize,
    and the regex fallback \u2014 which deliberately over-detects \u2014 turned a bare `>`
    in prose into a write target. That blocked a `git commit -m @'\u2026'@` on the
    very commit closing the task that introduced this parser. The POSIX twin
    already carried `_strip_heredocs` against exactly this symptom; the new
    dialect inherited the detectors but not the false-positive defences.
    """
    quote = command[i + 1 : i + 2]
    if quote not in ("'", '"'):
        return None
    line_end = command.find("\n", i + 2)
    if line_end == -1 or command[i + 2 : line_end].strip():
        return None  # an opener must end its line \u2014 otherwise it is not one
    terminator = quote + "@"
    pos = line_end + 1
    while pos <= len(command):
        nl = command.find("\n", pos)
        line = command[pos : nl if nl != -1 else len(command)]
        if line.startswith(terminator):
            return command[line_end + 1 : pos].rstrip("\r\n"), pos + len(terminator)
        if nl == -1:
            break
        pos = nl + 1
    # Unterminated: PowerShell would refuse to run this at all, so the remainder
    # is data by definition. Returning it as ONE token is what stops a broken
    # command from being read as a series of live ones.
    return command[line_end + 1 :], len(command)


def tokenize(command: str) -> list[str] | None:
    """PowerShell tokens, or None when the command does not close its quotes.

    None means "unparseable" and every caller treats it the way the POSIX side
    does — scan raw, over-detect. A missed destructive command is a hole; an
    extra candidate costs a question.
    """
    out: list[str] = []
    cur: list[str] = []
    seen = False  # `cur` holds a token, even if it is the empty string ('')
    i, n = 0, len(command)

    def flush() -> None:
        nonlocal seen
        if seen or cur:
            out.append("".join(cur))
            cur.clear()
            seen = False

    while i < n:
        ch = _SMART_TO_PLAIN.get(command[i], command[i])
        if ch in " \t\r":
            flush()
            i += 1
        elif ch in ";\n":
            flush()
            out.append(";")
            i += 1
        elif ch == "@" and (here := _here_string(command, i)) is not None:
            cur.append(here[0])
            seen = True
            i = here[1]
        elif ch == "`":
            # Backtick escapes the next character — PowerShell's `\`.
            if i + 1 < n:
                cur.append(command[i + 1])
                seen = True
            i += 2
        elif ch == "'":
            i += 1
            seen = True
            while i < n:
                c = _SMART_TO_PLAIN.get(command[i], command[i])
                if c == "'":
                    # `''` inside a literal string is an escaped apostrophe.
                    if i + 1 < n and _SMART_TO_PLAIN.get(command[i + 1], command[i + 1]) == "'":
                        cur.append("'")
                        i += 2
                        continue
                    i += 1
                    break
                cur.append(command[i])
                i += 1
            else:
                return None  # ran off the end with the quote still open
        elif ch == '"':
            i += 1
            seen = True
            while i < n:
                c = _SMART_TO_PLAIN.get(command[i], command[i])
                if c == "`" and i + 1 < n:
                    cur.append(command[i + 1])
                    i += 2
                    continue
                if c == '"':
                    if i + 1 < n and _SMART_TO_PLAIN.get(command[i + 1], command[i + 1]) == '"':
                        cur.append('"')
                        i += 2
                        continue
                    i += 1
                    break
                cur.append(command[i])
                i += 1
            else:
                return None
        elif command[i : i + 2] in ("&&", "||"):
            flush()
            out.append(command[i : i + 2])
            i += 2
        elif ch in "|&(){}":
            flush()
            out.append(ch)
            i += 1
        elif ch == ">":
            # A digit/`*` already collected into `cur` is this operator's fd
            # prefix, not a word: `2>` must not arrive as the token `2` plus `>`.
            prefix = ""
            if cur and re.fullmatch(r"\d+|\*", "".join(cur)):
                prefix = "".join(cur)
                cur.clear()
                seen = False
            flush()
            m = re.match(r">>?&?\d*", command[i:])
            op = m.group(0) if m else ">"
            out.append(prefix + op)
            i += len(op)
        else:
            cur.append(command[i])
            seen = True
            i += 1
    flush()
    return out


def split_statements(tokens: list[str]) -> list[list[str]]:
    """Split a token stream into independently judged statements.

    Same rule, and same reason, as the POSIX splitter: without it one
    interpreter anywhere on the line forces a raw scan of the WHOLE line, and a
    journal entry sharing a line with a real command gets blocked for a phrase
    it merely quotes.
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


#: Alias -> cmdlet. Windows PowerShell 5.1 is the shell this project actually
#: runs on (the PowerShell tool states it), so its alias table is the one that
#: matters: `sc`/`ac` are Set-Content/Add-Content there, and `rm`/`del`/`rd`
#: are all Remove-Item. An alias is not a nicety — it is the spelling an agent
#: reaches for first, so a detector that only knows the long form knows nothing.
_ALIASES = {
    "rm": "remove-item",
    "del": "remove-item",
    "erase": "remove-item",
    "rd": "remove-item",
    "rmdir": "remove-item",
    "ri": "remove-item",
    "sc": "set-content",
    "ac": "add-content",
    "ni": "new-item",
    "echo": "write-output",
    "write": "write-output",
    "iex": "invoke-expression",
    "gc": "get-content",
    "cat": "get-content",
    "type": "get-content",
    "cpi": "copy-item",
    "copy": "copy-item",
    "cp": "copy-item",
    "mi": "move-item",
    "move": "move-item",
    "mv": "move-item",
    "ren": "rename-item",
    "rni": "rename-item",
    "tee": "tee-object",
    "sp": "set-itemproperty",
    "sls": "select-string",
    "ls": "get-childitem",
    "dir": "get-childitem",
    "gci": "get-childitem",
    "ii": "invoke-item",
    "curl": "invoke-webrequest",
    "wget": "invoke-webrequest",
    "iwr": "invoke-webrequest",
    "irm": "invoke-restmethod",
    "clear": "clear-content",
    "clc": "clear-content",
    "spps": "stop-process",
}

#: Parameters that take NO value. Needed to know whether the token after a
#: parameter is its argument or a positional: `Remove-Item -Recurse C:\` puts
#: the target in a positional, `Remove-Item -Path C:\ -Recurse` in a value.
#: Getting this backwards loses the operand entirely, which reads as "no target
#: found" — a silent allow, the worst failure shape for a gate.
_SWITCHES = frozenset(
    {
        "recurse",
        "force",
        "append",
        "nonewline",
        "passthru",
        "whatif",
        "confirm",
        "container",
        "usebasicparsing",
        "verbose",
        "debug",
        "noprofile",
        "noninteractive",
        "nologo",
        "wait",
        "asjob",
    }
)

#: cmd.exe switch spellings, mapped to the PowerShell switch they mean. `rd /s
#: /q C:\` and `del /f /s /q C:\` are the native Windows way to write the same
#: wipe, they reach this parser through `cmd /c …`, and `/s` looks like a path
#: to every rule above. One table beats a third dialect: the operand and the
#: verb are already understood, only the flag spelling was missing.
_CMD_SWITCHES = {"/s": "recurse", "/f": "force", "/q": "quiet", "/y": "force"}


def canonical_verb(token: str) -> str:
    """`token` reduced to a comparable cmdlet name: path, `.exe` and alias gone."""
    base = os.path.basename(token).lower().removesuffix(".exe").removesuffix(".cmd")
    return _ALIASES.get(base, base)


def _param_name(token: str) -> str | None:
    """`-Recurse` / `-Path:x` -> `recurse` / `path`; None when not a parameter.

    A lone `-` and a negative number (`-1`) are operands, not parameters.
    """
    if not token.startswith("-") or len(token) < 2:
        return None
    body = token[1:].lstrip("-")
    name = body.split(":", 1)[0]
    if not name or not name[0].isalpha():
        return None
    return name.lower()


def _is_switch(name: str) -> bool:
    """Prefix-matched against the switch table — PowerShell accepts any
    UNAMBIGUOUS abbreviation, so `-Rec`, `-Recu` and `-r` are all `-Recurse`.

    Ambiguity is deliberately not resolved. Real PowerShell would error on an
    ambiguous prefix, so an over-broad match here cannot let a working command
    through unjudged; under-matching would. The asymmetry decides it (#291).
    """
    return any(sw.startswith(name) for sw in _SWITCHES)


class Statement:
    """One parsed PowerShell command: its verb, its switches, its arguments."""

    __slots__ = ("verb", "params", "positionals", "switches", "tokens")

    def __init__(self, tokens: list[str]) -> None:
        self.tokens = tokens
        self.verb = canonical_verb(tokens[0]) if tokens else ""
        self.params: dict[str, str] = {}
        self.switches: set[str] = set()
        self.positionals: list[str] = []
        self._parse(tokens[1:] if tokens else [])

    def _parse(self, args: list[str]) -> None:
        i = 0
        while i < len(args):
            tok = args[i]
            if _REDIR_TOKEN_RE.match(tok):
                i += 2  # the operator and its target belong to the redirect scan
                continue
            cmd_switch = _CMD_SWITCHES.get(tok.lower())
            if cmd_switch is not None:
                self.switches.add(cmd_switch)
                i += 1
                continue
            name = _param_name(tok)
            if name is None:
                self.positionals.append(tok)
                i += 1
                continue
            if ":" in tok[1:]:
                value = tok[1:].split(":", 1)[1]
                if value.lower() in ("$true", "$false"):
                    self.switches.add(name)
                else:
                    self.params[name] = value
                i += 1
                continue
            if _is_switch(name):
                self.switches.add(name)
                i += 1
                continue
            nxt = args[i + 1] if i + 1 < len(args) else None
            if nxt is not None and _param_name(nxt) is None and not _REDIR_TOKEN_RE.match(nxt):
                self.params[name] = nxt
                i += 2
            else:
                self.switches.add(name)
                i += 1

    def has_switch(self, canonical: str) -> bool:
        """True when any given switch abbreviates `canonical` (`-Rec` -> recurse)."""
        return any(canonical.startswith(name) for name in self.switches)

    def param(self, *canonical: str) -> str | None:
        """Value of the first parameter abbreviating any of `canonical`."""
        for name, value in self.params.items():
            if any(c.startswith(name) for c in canonical):
                return value
        return None


def statements(command: str) -> list[Statement] | None:
    """Every statement in `command`, parsed. None when it does not tokenize."""
    tokens = tokenize(command)
    if tokens is None:
        return None
    return [Statement(sub) for sub in split_statements(tokens) if sub]


# The "what command is this really" layer lives in `pwsh_cmd_norm` (filesize
# cap), the same split the POSIX side made between `bash_write_parse` and
# `bash_cmd_norm`. Not re-exported: importing it here would make the two
# modules mutually dependent, and `pwsh_cmd_norm` is the one that needs THIS
# file's parser, not the other way round.
