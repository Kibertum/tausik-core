"""An operator character that is QUOTED or ESCAPED is data, not an operator.

THE DEFECT THIS EXISTS FOR, measured on the live parser (session #238). These
seven commands all produced the target `zzz.txt` / `b.txt` with confidence
`parsed` — the reading was confident, and six of the seven were wrong:

    [ "$a" \\> "zzz.txt" ]              ->  ['zzz.txt']   comparison, not a write
    [[ "$a" > "zzz.txt" ]]             ->  ['zzz.txt']   comparison, not a write
    test "$a" \\> "zzz.txt"             ->  ['zzz.txt']   comparison, not a write
    if [ ... ]; then echo x; fi        ->  ['zzz.txt']   comparison, not a write
    echo a \\> b.txt                    ->  ['b.txt']     an escaped literal
    echo a ">" b.txt                   ->  ['b.txt']     a quoted literal
    echo a > b.txt                     ->  ['b.txt']     A REAL WRITE

WHY THE PARSER COULD NOT TELL THEM APART. `tokenize` runs shlex with
`posix=True`, which is what makes `"a b"` one token — and the same pass removes
quotes and resolves backslash escapes. After it, `\\>` and `">"` are the token
`>`, byte-identical to the operator. The evidence separating data from command
exists only in the ORIGINAL TEXT, which is exactly why `strip_fd_prefixes` and
`split_statement_breaks` also work on text: `cp a b 2>out` and `cp a b 2 >out`
tokenize identically too.

SO THE RULE IS STRUCTURAL AND LIVES IN ONE PLACE: walk the text once with the
same quoting state machine a shell uses, and mark every operator character that
is quoted or escaped. Marked characters ride through tokenization inside their
token and are restored afterwards. Nothing about which COMMANDS are involved,
no list of words, arrows or builtin names — `[`, `[[` and `test` are fixed by
the same rule that fixes prose, because in every one of those cases the author
wrote the character AS DATA and the shell would have agreed.

WHAT THIS DELIBERATELY DOES NOT DO. It does not touch the `regex_fallback`
path. That path handles a command that would not tokenize AT ALL, its trust
level is honest about being a guess, and the policy question of whether a
blocking gate may act on a guess is a separate decision that is not this
module's to make. Confidence in all seven rows above is `parsed`: nothing here
moves a verdict from "could not read" to "allowed".
"""

from __future__ import annotations

__all__ = ["mask_quoted_operators", "unmask", "OPERATOR_CHARS"]

#: The characters whose meaning flips between operator and data. Only the
#: redirection operators: `&` and `|` are not restored to operator status by
#: quoting in any way this parser reads, and `;` is handled as text upstream by
#: `split_statement_breaks` before tokenization.
OPERATOR_CHARS = "<>"

#: Private-use codepoints. Chosen because shlex treats them as ordinary word
#: characters, they cannot appear in a real path a shell would accept from this
#: repository's tooling, and a leak is visible rather than silent — an unmasked
#: sentinel reaching a caller would show up as an unprintable character in a
#: path, not as a plausible filename.
_MARK = {char: chr(0xE000 + index) for index, char in enumerate(OPERATOR_CHARS)}
_UNMARK = {mark: char for char, mark in _MARK.items()}


def mask_quoted_operators(command: str) -> str:
    """Replace every QUOTED or ESCAPED `<`/`>` with a sentinel.

    The state machine is the shell's, not an approximation of it:

    * outside quotes, a backslash escapes exactly the next character;
    * inside single quotes NOTHING escapes — a backslash is a literal
      backslash, which is why the single-quote branch has no escape handling;
    * inside double quotes a backslash escapes only a small set, but for our
      purpose the distinction does not matter: everything between the quotes is
      data either way, so the branch marks operators unconditionally;
    * an UNTERMINATED quote leaves the text unparseable. This returns it
      unchanged rather than guessing, so `tokenize` still fails and the caller
      still degrades to `regex_fallback`. Masking a half-open quote would be
      the one change here that could HIDE a real write.
    """
    if not any(char in command for char in OPERATOR_CHARS):
        return command

    out: list[str] = []
    quote: str | None = None
    index = 0
    length = len(command)

    while index < length:
        char = command[index]

        if quote is None and char == "\\":
            # Escaped: the next character is data whatever it is.
            if index + 1 < length:
                nxt = command[index + 1]
                out.append("\\")
                out.append(_MARK.get(nxt, nxt))
                index += 2
                continue
            out.append(char)
            index += 1
            continue

        if quote is None and char in "'\"":
            quote = char
            out.append(char)
            index += 1
            continue

        if quote is not None:
            if char == quote:
                quote = None
                out.append(char)
                index += 1
                continue
            if quote == '"' and char == "\\" and index + 1 < length:
                nxt = command[index + 1]
                out.append("\\")
                out.append(_MARK.get(nxt, nxt))
                index += 2
                continue
            out.append(_MARK.get(char, char))
            index += 1
            continue

        out.append(char)
        index += 1

    if quote is not None:
        # Unterminated. Hand back the original so nothing downstream is made
        # more confident by a rewrite this module could not finish.
        return command
    return "".join(out)


def unmask(text: str) -> str:
    """Restore sentinels. Cheap enough to call on every token unconditionally."""
    if not text:
        return text
    for mark, char in _UNMARK.items():
        if mark in text:
            text = text.replace(mark, char)
    return text
