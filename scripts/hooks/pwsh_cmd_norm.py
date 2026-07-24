r"""What is this PowerShell statement REALLY running — the layer under detection.

Split out of `pwsh_cmd_parse` for the 400-line cap, along the SAME seam the
POSIX side already found twice (`bash_cmd_norm`): "what does this command
write / delete" and "what command is this, actually" are different questions,
and every bypass this project has recorded came from a detector that was right
about the first while being wrong about the second.

Anything asking "is this an interpreter?" or "what is it being handed?" must go
through here, or it is asking about the wrapper instead of the command.
"""

from __future__ import annotations

from pwsh_cmd_parse import Statement, canonical_verb, split_statements, tokenize

# A wrapper may nest (`powershell -Command "pwsh -c '…'"`). Same bound and same
# reasoning as the POSIX side: three levels is far past any real invocation, and
# a named constant makes exceeding it a decision rather than a crash.
_MAX_WRAPPER_DEPTH = 3

#: Programs that EXECUTE what they are handed. Mirrors the POSIX list, from the
#: other side of the fence: there `powershell` was already an interpreter, here
#: `bash` is. A win32 agent reaches both ways, and a gate that knows only its
#: own dialect's wrappers can be stepped around by naming the other one.
_INTERPRETERS = frozenset(
    {
        "powershell",
        "pwsh",
        "cmd",
        "wsl",
        "bash",
        "sh",
        "zsh",
        "invoke-expression",
        "start-process",
        "invoke-command",
        "python",
        "python3",
        "node",
        "perl",
        "ruby",
        "ssh",
        "sqlite3",
        "psql",
        "mysql",
    }
)

#: Parameters whose value is a COMMAND LINE, not a filename. `-File` is
#: excluded on purpose: it names a script on disk, which this hook cannot read
#: and does not pretend to.
_PAYLOAD_PARAMS = ("command", "argumentlist", "scriptblock")


def payloads(stmt: Statement) -> list[str]:
    """Command strings this statement carries as data for another interpreter."""
    if stmt.verb not in _INTERPRETERS:
        return []
    out: list[str] = []
    value = stmt.param(*_PAYLOAD_PARAMS)
    if value:
        out.append(value)
    # `cmd /c "…"`, `bash -c '…'`, and `iex '…'` / `powershell "…"` where the
    # payload is simply the next word.
    for i, tok in enumerate(stmt.tokens):
        if tok.lower() in ("/c", "/k", "-c") and i + 1 < len(stmt.tokens):
            out.append(stmt.tokens[i + 1])
    if stmt.verb == "invoke-expression" and stmt.positionals:
        out.append(stmt.positionals[0])
    return out


def mentions_interpreter(stmt: Statement) -> bool:
    """True when ANY token names a program that runs what it is given.

    Not limited to command position, for the reason the POSIX twin records: a
    wrapper hides the real interpreter behind itself, and checking only the
    first word let a confirmed bypass through.
    """
    return any(canonical_verb(tok) in _INTERPRETERS for tok in stmt.tokens)


#: Stands in for a token carrying free text rather than command words. Shares
#: the POSIX hook's choice of character for the same reason: it appears in no
#: BLOCKED or WARN pattern, so substituting it can never manufacture a match.
_PAYLOAD_PLACEHOLDER = "_"


def scan_target(command: str, depth: int = 0) -> str:
    """The part of `command` that can actually execute.

    Same discriminator as the POSIX scanner — token boundaries, not quoting. A
    real command's words arrive as separate tokens; a mention inside a quoted
    argument arrives as one. Statements naming an interpreter are joined raw,
    because there the quoted blob IS the command, and their payloads are
    re-scanned as the command lines they are, bounded by `_MAX_WRAPPER_DEPTH`.
    """
    tokens = tokenize(command)
    if tokens is None or not tokens:
        return command
    parts: list[str] = []
    for sub in split_statements(tokens):
        stmt = Statement(sub)
        if mentions_interpreter(stmt):
            parts.append(" ".join(sub))
            if depth < _MAX_WRAPPER_DEPTH:
                for payload in payloads(stmt):
                    parts.append(scan_target(payload, depth + 1))
        else:
            parts.append(
                " ".join(_PAYLOAD_PLACEHOLDER if len(tok.split()) > 1 else tok for tok in sub)
            )
    return " ; ".join(parts)
