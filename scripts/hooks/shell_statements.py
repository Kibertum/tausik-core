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
