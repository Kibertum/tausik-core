r"""Does this `rm` invocation delete a whole tree root — and which one?

Split out of `bash_firewall` for the 400-line cap, along the seam the second
review of the same code exposed. "Is this command an `rm -r -f`?" and "does this
operand mean *everything*?" are different questions, and the fix that got the
first one right got the second one wrong:

* Three literal substrings (`rm -rf /`, `rm -rf /*`, `rm -rf .`) were replaced by
  an exact-match set of the same four spellings. Substrings matched by PREFIX,
  so `rm -rf ./*`, `rm -rf .*`, `rm -rf ../*`, `rm -rf /.`, `rm -rf //` and
  `rm -rf /./` had all been blocked by accident — and stopped being blocked the
  moment the comparison became exact. Closing five missing flag spellings opened
  seven operand spellings, which is the same trade the fix was written to end.

So the operand is NORMALISED before it is judged, rather than looked up. A
spelling that resolves to the same place gets the same answer, which is the
property the set could never have.

`find / -delete` and `find / -exec rm -rf {} \;` are NOT covered here: `find`
carries the recursion and `rm` never sees a root operand. That is a different
detector, filed as its own task rather than half-built into this one.

`wiped_root` parses POSIX `rm` FLAGS. The PowerShell channel spells the same
intent `Remove-Item -Recurse`, and its flag parsing lives in `pwsh_write_parse`
— but both ask `is_wipe_root` which places count as "everything". One judge, two
dialect-specific flag parsers: a second copy of the root SET is exactly the
drift conventions #266/#289 warn about, and this file's own history is the
argument — every regression above came from two spellings of one rule
disagreeing.
"""

from __future__ import annotations

import posixpath
import re

# Operands that mean "the whole tree", after normalisation. `..` is here because
# the old prefix match covered `../*` and dropping it would be a silent narrowing.
# `~` was added by the policy task (decision #177): `rm -rf ~` wipes the whole
# home directory — every project, every SSH/GPG key, every credential — which is
# not milder than `/`, and unlike a bare `*` there is no routine operation that
# legitimately deletes all of home. It is a literal tilde in the command BEFORE
# the shell expands it, so it is catchable here without resolving anything.
# A bare `*` is NOT listed and does not need to be: `normalise_operand` already
# reduces a trailing glob to its directory, so `*`, `./*` and `.*` all resolve to
# `.` and are judged the same as `rm -rf .` — the earlier docstring claim that
# `rm -rf *` was allowed was wrong about the code, which the policy task confirmed
# by test. `$HOME` and `${X:-/}` stay OUT: they need environment/parameter
# expansion, and resolving those would mean running a shell (see `is_wipe_root`).
_WIPE_ROOTS = frozenset({"/", ".", "..", "~"})

# A Windows volume root, after normalisation: `C:\` and `C:/` both reduce to
# `C:` (posixpath.normpath drops the trailing separator). This is NOT the policy
# widening deferred above — it is the SAME rule as `/`, spelled for the platform
# the project calls primary. Leaving it out meant the root of the disk was the
# one root the firewall did not recognise, on the only OS where it exists.
#
# Cost of error, weighed the way convention #291 asks: on Windows a colon
# cannot appear in a filename, so `C:` can never name a relative directory and
# a false positive is unreachable. On POSIX a directory literally named `C:` is
# legal but would have to be deleted with `rm -rf C:` — vanishingly rare, and
# the escape (TAUSIK_SKIP_HOOKS, recorded) exists. Missing a volume wipe on the
# primary platform is not recoverable at all.
_DRIVE_ROOT_RE = re.compile(r"^[A-Za-z]:$")


def is_wipe_root(operand: str) -> bool:
    """Does this operand name "everything" — after normalisation, not as spelled.

    The single judge both channels ask. `operand` is raw as written; the
    normalisation that makes `./*`, `/.`, `//` and `C:\\` answer the same as `.`
    and `/` happens here, so no caller can get it half-right. `~`, `~/` and `~/*`
    all resolve to home and answer True (decision #177).

    Residual, by design: an operand that only becomes root-ish after SHELL
    expansion (`$HOME`, `${X:-/}`) reads as itself and answers False — resolving
    it would mean running a shell. `~` is the exception because tilde-expansion is
    a fixed literal that needs no environment, so it is judged here directly.
    """
    normalised = normalise_operand(operand)
    if not normalised:
        return False
    if normalised == "~":
        # A tilde is the shell's home only when it LEADS the word: `~`, `~/`,
        # `~/*` expand to $HOME, but `./~`, `dir/~`, `a/../~` name a literal file
        # called `~` and the shell never touches home for them. `posixpath.normpath`
        # is blind to that — it collapses all of them to `~` — so the leading test
        # is done on the raw operand, or `rm -rf ./~` false-blocks as a home wipe
        # (review s126, supersedes the `./~` note in decision #177).
        cleaned = operand.strip().strip(_LEADING_JUNK).rstrip(_TRAILING_JUNK).replace("\\", "/")
        return cleaned.startswith("~")
    return normalised in _WIPE_ROOTS or bool(_DRIVE_ROOT_RE.match(normalised))


# Shell punctuation that can ride along on a token when the command was not
# fully split — a backtick substitution (``echo `rm -rf /` ``) leaves the
# closing backtick glued to the last operand, which was enough for an exact
# match to miss the root entirely.
_TRAILING_JUNK = "`)\"';"
_LEADING_JUNK = "`(\"'"

_GLOB_CHARS = "*?["


def normalise_operand(raw: str) -> str:
    """`raw` reduced to the path it actually names, or `''` if it names none.

    A trailing glob component is replaced by its directory: `./*` empties `.`
    exactly as `.` does, and judging the literal string could not see that.
    """
    tok = raw.strip().strip(_LEADING_JUNK).rstrip(_TRAILING_JUNK)
    if not tok:
        return ""
    tok = tok.replace("\\", "/")
    head, sep, tail = tok.rpartition("/")
    if any(ch in _GLOB_CHARS for ch in tail):
        # `foo/*` → `foo`; a bare `*` or `.*` → the current directory.
        tok = head if sep else "."
        if not tok:
            tok = "/"
    elif any(ch in _GLOB_CHARS for ch in tok):
        return ""
    if not tok:
        return ""
    normalised = posixpath.normpath(tok)
    # normpath keeps a leading `//` (POSIX leaves it implementation-defined);
    # for "is this the root" it is the root.
    return "/" if set(normalised) == {"/"} else normalised


def wiped_root(tokens: list[str]) -> str | None:
    """The tree-root operand of a recursive `rm`, or None.

    Force (`-f`) is deliberately NOT required. The pair `-r -f` was described as
    "what makes the command unrecoverable", but every command this hook sees is
    run non-interactively, and there `rm -r /` has no tty to prompt at: it
    deletes everything not write-protected and asks nobody. Requiring `-f`
    costs nothing to an attacker and one word to a mistake. Dropping it adds no
    false positives either, because a non-root operand is still not judged.
    """
    recursive = False
    targets: list[str] = []
    end_of_flags = False
    for tok in tokens:
        if tok == "--" and not end_of_flags:
            end_of_flags = True
            continue
        low = tok.lower()
        if not end_of_flags and tok.startswith("--"):
            recursive = recursive or low == "--recursive"
        elif not end_of_flags and tok.startswith("-") and len(tok) > 1:
            recursive = recursive or "r" in low
        else:
            targets.append(tok)
    if not recursive:
        return None
    for target in targets:
        if is_wipe_root(target):
            return target
    return None
