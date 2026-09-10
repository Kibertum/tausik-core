"""Statement boundaries that only a NEWLINE marks, recovered from the raw text.

THE MEASUREMENT. `bash_cmd_scan._SEPARATORS` has always listed `"\\n"` among the
operators that end one command and start the next. It could never match. Tokens
reach `_split_subcommands` from `shlex(..., whitespace_split=True)`, and shlex
treats a newline as whitespace: it separates two words and then it is gone. So
the newline entry was dead code written for a tokenization that does not happen
— the same shape as the `\\d*` that session #204 found in the redirection
pattern, and the same lesson memory #505 paid for: a signal the tokenizer
destroys has to be read in the source text, where it still exists.

What that cost, measured over 9 separator forms x 10 writing commands = 90
cells, before this module existed:

    ;   &&   ||   |   `;` then newline  ->  0 of 10 writers lost
    newline, blank line, indented line, CRLF  ->  9 of 10 writers lost, each

36 of 90 cells lost the real target entirely. Not a phantom — a MISS. Only one
writer survived a bare newline, and it survived for the reason this module
exists: a redirection target is recovered from the text by `shell_redirection`,
so it never depended on the token stream at all.

WHY IT MATTERS MORE THAN A FALSE POSITIVE. `bash_write_gate` is a containment
control: it holds an agent's writes inside the task's declared scope. Verified
against the real hook, not this parser alone — a single-line write outside the
ACL is refused, and the SAME write with any command on a line above it went
through and put 723996 bytes outside the declared scope. A multi-line Bash call
is the ordinary way to work, so nobody has to be clever to defeat the gate; they
fall through it by accident.

WHAT COUNTS AS A BOUNDARY, AND WHAT ONLY LOOKS LIKE ONE. A newline ends a
statement only when the shell would treat it as one. Inside single or double
quotes it is data — a multi-line commit message is one argument, and splitting
it would manufacture commands out of prose, which is exactly the phantom this
project keeps having to remove. After a backslash it is a line continuation:
the shell joins the two lines into one command. Both cases are preserved here,
so this module can only ever RECOVER a boundary that bash sees, never invent
one.

Heredoc bodies are already gone by the time this runs (`_strip_heredocs`), which
is what makes a plain quote-aware scan sufficient rather than a shell parser.
"""

from __future__ import annotations

import re
from collections.abc import Callable

#: What an honest boundary is replaced WITH. `;` is already in `_SEPARATORS` and
#: already exercised by every test that uses it, so recovering a newline into a
#: semicolon reuses a splitter that works instead of adding a second one that
#: would have to be kept in step with it.
_BOUNDARY = " ; "


def split_statement_breaks(text: str) -> str:
    """`text` with every SHELL-SIGNIFICANT newline turned into a `;` separator.

    Quoted newlines and backslash line-continuations are left alone: the first
    is data, the second is not a boundary at all. Everything else — a bare
    newline, a blank line, an indented continuation of a script, a CRLF pair —
    ends the statement, because that is what bash does with it.
    """
    out: list[str] = []
    quote: str | None = None
    i = 0
    n = len(text)

    while i < n:
        ch = text[i]

        if quote is not None:
            # Inside single quotes bash gives the backslash no special meaning,
            # so only a double-quoted context can escape the closing character.
            if ch == "\\" and quote == '"' and i + 1 < n:
                out.append(ch)
                out.append(text[i + 1])
                i += 2
                continue
            out.append(ch)
            if ch == quote:
                quote = None
            i += 1
            continue

        if ch in ("'", '"'):
            quote = ch
            out.append(ch)
            i += 1
            continue

        if ch == "\\" and i + 1 < n:
            nxt = text[i + 1]
            if nxt == "\n" or (nxt == "\r" and i + 2 < n and text[i + 2] == "\n"):
                # Line continuation: the shell joins the lines, so this is the
                # opposite of a boundary. A space keeps the words apart.
                out.append(" ")
                i += 3 if nxt == "\r" else 2
                continue
            # An ordinary escape — carry both characters through untouched, or a
            # `\"` would be read below as an opening quote.
            out.append(ch)
            out.append(nxt)
            i += 2
            continue

        # No CRLF case here, and that is measured rather than assumed: shlex
        # counts `\r` as whitespace, so a carriage return left in front of the
        # newline neither survives into a token nor changes one. A branch for it
        # was written, then removed when a mutation could not make it matter —
        # a condition that cannot fail is the same dead code as the `"\n"` in
        # `_SEPARATORS` that this whole module exists to answer for. The
        # continuation branch above is a different story: there the `\r` IS
        # load-bearing, and there is a test that goes red without it.
        if ch == "\n":
            out.append(_BOUNDARY)
            i += 1
            continue

        out.append(ch)
        i += 1

    return "".join(out)


# ---------------------------------------------------------------------------
# Heredoc bodies
# ---------------------------------------------------------------------------

# Opening marker of a heredoc. Group 1 = the `-` of `<<-` (tab-stripping form)
# or empty for a plain `<<`; group 3 = the delimiter word.
_HEREDOC_RE = re.compile(r"""<<(-?)\s*(['"]?)([A-Za-z_][A-Za-z0-9_]*)\2""")


def heredoc_bodies(command: str) -> list[tuple[str, str]]:
    """`(header, body)` for each real heredoc, without treating body as shell."""
    lines = command.split("\n")
    out: list[tuple[str, str]] = []
    i = 0
    while i < len(lines):
        header = lines[i]
        i += 1
        for match in _HEREDOC_RE.finditer(header):
            dash, delimiter = match.group(1), match.group(3)
            body: list[str] = []
            while i < len(lines):
                candidate = lines[i].rstrip("\r")
                if (candidate.lstrip("\t") == delimiter) if dash else (candidate == delimiter):
                    break
                body.append(lines[i])
                i += 1
            i += 1
            out.append((header, "\n".join(body)))
    return out


def strip_heredoc_bodies(
    command: str,
    keep_body: Callable[[str], bool] | None = None,
) -> str:
    """Remove heredoc BODIES, keeping the header line that holds the redirect.

    A heredoc body is DATA on its way to a file or a program's stdin, but it
    arrives in the same string as the command and tokenizes like live shell.
    Every consumer that reads that string has to answer for the difference, and
    two of them learned it separately:

      * the write gate manufactured a phantom redirect target from a `->` in
        prose (`def f() -> int:` -> target `int:`), blocking a compliant write;
      * the destructive-command firewall read prose NAMING a table drop as a
        table drop, so a docstring explaining why a migration rebuilds a table
        could not be written through a heredoc at all -- measured three times,
        the third while writing the acceptance criteria for the fix.

    The header line (`cat > f <<EOF`) is preserved so the real target and the
    real command are still seen; everything from the next line up to and
    including the terminator is dropped.

    `keep_body` DECIDES PER HEREDOC, and it is the whole safety story. It
    receives the header line and returns True to leave that body in place. The
    firewall passes a predicate that keeps the body whenever the header names
    an interpreter, because `bash <<EOF ... EOF` really does execute what it is
    handed -- dropping that body would turn a false positive into a hole. The
    write gate passes nothing: it only wants redirect targets, and a body never
    holds one.
    """
    lines = command.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        i += 1
        # A header line may open MORE THAN ONE heredoc (`cmd <<A <<B`); bash
        # consumes their bodies in order. finditer (not search) handles each, or
        # the second body leaks back into the scanned shell text.
        for m in _HEREDOC_RE.finditer(line):
            dash, delim = m.group(1), m.group(3)
            body: list[str] = []
            # bash: a plain `<<DELIM` needs an EXACT terminator line; `<<-DELIM`
            # strips only leading TABS. Using .strip() for the plain form let an
            # indented pseudo-delimiter inside the body end the scan early and
            # re-expose the rest of the body as live shell (phantom targets).
            while i < len(lines):
                base = lines[i].rstrip("\r")
                if (base.lstrip("	") == delim) if dash else (base == delim):
                    break
                body.append(lines[i])
                i += 1
            i += 1  # skip the terminator line itself (or past EOF if unterminated)
            if keep_body is not None and keep_body(line):
                out.extend(body)
    return "\n".join(out)
