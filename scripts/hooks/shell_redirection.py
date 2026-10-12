#!/usr/bin/env python3
"""POSIX shell redirections: which of them write a file, and which tokens they eat.

Split out of `bash_write_parse` for the reason `python_invocation` was split out
in #203 — a parsing rule that needs its own measurements deserves its own module
and its own tests, and the parent file was 438 lines against a 500-line gate.

WHAT WENT WRONG, MEASURED. `bash_write_parse` matched redirections with
`^\\d*>>?\\|?$`, a pattern that expects the file-descriptor number to arrive
GLUED to the operator (`2>`). It never does: `shlex(punctuation_chars=True)`
always splits it off as a word of its own, so `cp a b 2>/dev/null` tokenizes as
`['cp', 'a', 'b', '2', '>', '/dev/null']`. The `\\d*` was dead code written for a
tokenization that does not happen here, and the orphaned `2` stayed in the
command's argument list. For `cp`/`mv`/`install`, whose destination is the LAST
positional, that number then WAS the destination as far as the gate could tell:
the real path vanished from its view and a file named `2` took its place.

Session #203 met the visible half live — the gate refused an ordinary
`cp ... 2>/dev/null`. A 150-cell sweep (10 writer commands x 15 redirection
forms) found 70 cells inventing a target and 30 cells losing the real one. The
losing half never showed up as a bypass because the phantom digit is itself an
in-tree path outside the task's scope, so the block happened anyway — the right
verdict reached for the wrong reason, and reported against a file named `2`.

WHY THE RAW TEXT AND NOT THE TOKENS. `cp a b 2>out` and `cp a b 2 >out` produce
IDENTICAL token lists, and they mean different things: the first redirects
stderr, the second copies to a file named `2`. Bash separates them by adjacency
alone, and adjacency is exactly what tokenization discards. So the descriptor
number is removed from the COMMAND TEXT, where the whitespace still exists,
before anything is tokenized — the same evidence bash decides on. Eating digit
tokens after the fact would have broken `cp a 2 >out`, which is correct today.

RESIDUAL, MEASURED AND NAMED. Adjacency is read with a quote- and
escape-tracking scan, so `2>` inside `'...'`, `"..."` or behind a backslash is
left alone. Not handled: a descriptor number produced by expansion
(`cp a b ${fd}>log`) — the token still carries `$`, and `_plausible_path` drops
it as the documented unresolvable residual. `{fd}>log`, bash's named-descriptor
form, is likewise left as an ordinary word rather than guessed at.
"""

from __future__ import annotations

# Operators that CREATE or APPEND to a file — the only ones that are a write.
# `>|` is `>` with noclobber overridden; it truncates just the same.
WRITE_OPS = (">", ">>", ">|", "&>", "&>>")

# Operators that consume a target without writing a file. `>&`/`<&` duplicate a
# descriptor (`2>&1`, `2>&-`); `<`, `<<<` read. They are listed here because
# their TARGET must not be mistaken for one of the command's own arguments —
# that is how `cp a b <in` came to report the input file as a write and lose the
# destination `b`.
READ_OPS = ("<", "<<<", "<&", ">&")

_ALL_OPS = WRITE_OPS + READ_OPS

# A descriptor number is a word of its own only when nothing word-like precedes
# it: in `log2>x` the word is `log2` and `>x` is the redirection, exactly as bash
# reads it. `/`, `.`, `-` and `_` count as word-like so a filename such as
# `run-2>x` is not mistaken for a descriptor either.
_WORDISH = "._-/"


def strip_fd_prefixes(command: str) -> str:
    """`command` with each descriptor number that is GLUED to a redirection removed.

    `cp a b 2>/dev/null` -> `cp a b >/dev/null`; `cp a b 2 >out` is untouched,
    because there the `2` is an argument. Quoted and backslash-escaped text is
    copied through verbatim — a `2>` inside a filename is not a redirection.
    """
    out: list[str] = []
    i, n = 0, len(command)
    quote = ""
    while i < n:
        ch = command[i]
        if quote:
            out.append(ch)
            # Inside double quotes a backslash still escapes; inside single
            # quotes it does not, which is why the check names the quote.
            if ch == "\\" and quote == '"' and i + 1 < n:
                out.append(command[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = ""
            i += 1
            continue
        if ch in "'\"":
            quote = ch
            out.append(ch)
            i += 1
            continue
        if ch == "\\" and i + 1 < n:
            out.append(ch)
            out.append(command[i + 1])
            i += 2
            continue
        if ch.isdigit():
            j = i
            while j < n and command[j].isdigit():
                j += 1
            prev = out[-1] if out else ""
            glued = j < n and command[j] in "<>"
            standalone = not prev or not (prev.isalnum() or prev in _WORDISH)
            if glued and standalone:
                i = j  # drop the digits; the operator itself is kept
                continue
            out.append(command[i:j])
            i = j
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def split_redirections(sub: list[str]) -> tuple[list[str], list[str]]:
    r"""`(files written, remaining words)` for ONE already-split sub-command.

    Every redirection — writing or reading — is REMOVED from the word list, so
    what is left is the command and its own arguments. That is what makes the
    trailing-positional rule (`cp`/`mv`/`install` write their last argument)
    answer about the real destination instead of about whatever the redirection
    left lying around.

    Assumes `strip_fd_prefixes` already ran on the command text, so no bare
    descriptor number reaches this point. `>(`/`<(` are deliberately NOT
    redirections here: they open a process substitution and are left in the word
    list for the caller to stop at.

    INSIDE `[[ ... ]]` NOTHING IS A REDIRECTION, and this is grammar rather than
    a command name. `[[` is a bash compound command: the shell does not parse
    redirections between it and its `]]`, so `[[ "$a" > "$b" ]]` compares two
    strings and creates no file. `[ ... ]` is deliberately NOT given the same
    treatment, and the difference is not an oversight: `[` is an ordinary
    command, bash DOES read `[ "$a" > "$b" ]` as a redirection, and that is why
    the idiom requires `\>`. Escaping is handled one layer up, in
    `argument_data` — with both in place this parser agrees with bash on both
    spellings.

    A redirection AFTER the closing `]]` is outside the span and still caught.
    """
    targets: list[str] = []
    words: list[str] = []
    i, n = 0, len(sub)
    depth = 0
    while i < n:
        tok = sub[i]
        if tok == "[[":
            depth += 1
            words.append(tok)
            i += 1
            continue
        if tok == "]]" and depth:
            depth -= 1
            words.append(tok)
            i += 1
            continue
        if depth:
            words.append(tok)
            i += 1
            continue
        if tok in _ALL_OPS:
            tgt = sub[i + 1] if i + 1 < n else None
            if tgt is None:
                # A trailing operator with nothing after it: nothing to record,
                # and nothing to hand on as a word either.
                break
            # `&N` is descriptor duplication, never a file — the guard the
            # previous parser carried, kept verbatim. `-` gets NO such guard:
            # it closes a descriptor only after `>&`, which is a read op and
            # records nothing anyway, while `> -` creates an ordinary file
            # named `-`. Excluding it here would have dropped a real write
            # this parser used to catch.
            if tok in WRITE_OPS and not tgt.startswith("&"):
                targets.append(tgt)
            i += 2
            continue
        words.append(tok)
        i += 1
    return targets, words
