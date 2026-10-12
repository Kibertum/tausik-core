"""An outcome for a closure citation that no longer resolves (github#150).

closure-citations-rot-is-detected-but-never-acted-on (1.10). The audit found
rotted and invented citations and only reported them: a reconciliation note
appended to the journal did not retire the finding, so every coherence pass
reopened the same list and nobody acted on it (108 rotted, 39 invented, on a
declared remainder of 99 and 36 — already exceeded).

A closure receipt is never rewritten. The outcome is an APPENDED journal line,
one of three, each naming the citation exactly as `tausik audit evidence`
prints it:

    EVIDENCE-MOVED: <old ref> => <new ref>      the coverage lives on there
    EVIDENCE-RETIRED: <ref> — <reason>          the subject was removed on purpose
    EVIDENCE-UNPROVEN: <ref> — <reason>         no coverage: the closure is unproven

A finding is retired only when EVERY task citing it carries an outcome, and a
MOVED outcome only when its new ref resolves. Retired findings keep their own
counts: a number that silently drops entries is how this started.
"""

from __future__ import annotations

import re
from typing import Final

MOVED: Final[str] = "moved"
RETIRED: Final[str] = "retired"
UNPROVEN: Final[str] = "unproven"

_LINE = re.compile(
    r"EVIDENCE-(MOVED|RETIRED|UNPROVEN):\s*(\S+)\s*(?:=>\s*(\S+)|[—-]+\s*(.+))?",
)


#: Punctuation that ends a SENTENCE, never an address. A journal line is prose, so an author
#: who finishes the thought puts one of these right after the reference — and `\S+` took it
#: into the address, which then resolved to nothing and the answer was silently not counted.
#: The first real use of the mechanism lost its answer exactly this way: one full stop, and
#: nothing said so.
#:
#: Stripped from the RIGHT only, and only these: a dot INSIDE an address is load-bearing
#: (`tests/x.py::test_y`), and trimming by class rather than by position would eat the
#: extension. `::` is excluded for the same reason a colon is not in this set.
_SENTENCE_TAIL: str = ".,;!?"


def _address(raw: str) -> str:
    """An address with sentence punctuation taken off its tail.

    Only the tail: `tests/x.py` keeps its dot because the dot is not last. A reference that IS
    only punctuation is left alone rather than reduced to an empty string, so the caller sees a
    ref it can report instead of a blank one it cannot.
    """
    trimmed = raw.rstrip(_SENTENCE_TAIL)
    return trimmed or raw


def parse(notes: str) -> dict[str, tuple[str, str]]:
    """{old ref: (outcome, new ref or reason)} for every outcome line in notes.

    Addresses are trimmed of sentence punctuation; REASONS are not. A reason is free text and
    the author's full stop belongs to it — trimming there would edit what somebody wrote.
    """
    out: dict[str, tuple[str, str]] = {}
    for m in _LINE.finditer(notes or ""):
        kind, ref, new, reason = m.group(1).lower(), m.group(2), m.group(3), m.group(4)
        ref = _address(ref)
        if kind == MOVED:
            if new:
                out[ref] = (MOVED, _address(new))
        elif reason and reason.strip():
            out[ref] = (kind, reason.strip())
    return out


def outcome_for(
    ref: str,
    citing: list[str],
    per_task: dict[str, dict[str, tuple[str, str]]],
    resolves: dict[str, bool],
) -> str | None:
    """The retiring outcome of `ref`, or None while any citing task lacks one.

    `resolves` answers whether a MOVED target resolves today; a target that
    does not resolve is no outcome at all.
    """
    kinds: list[str] = []
    for slug in citing:
        got = (per_task.get(slug) or {}).get(ref)
        if got is None:
            return None
        kind, value = got
        if kind == MOVED and not resolves.get(value, False):
            return None
        kinds.append(kind)
    if not kinds:
        return None
    for worst in (UNPROVEN, RETIRED, MOVED):
        if worst in kinds:
            return worst
    return None


def template(ref: str, slug: str, successor: str | None) -> str:
    """The command a reader runs to give `ref` an outcome in `slug`."""
    if successor:
        body = f"EVIDENCE-MOVED: {ref} => {successor}"
    else:
        body = f"EVIDENCE-RETIRED|UNPROVEN: {ref} — <reason>"
    return f'tausik task log {slug} "{body}"'
