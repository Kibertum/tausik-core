"""A count of a closed list, written out instead of derived from the list.

NOT A TEST MODULE — a contract shared by the tests that guard each closed list
(SPEC types, ADAPT backward-finding categories). It lives here rather than being
copied into each of them for the reason the defect itself teaches: a second copy
of a detector is the same defect one level up.

WHAT THE DEFECT IS. A closed list is enumerated in one place and its length is
written beside it in prose, help text, error messages and clause evidence. While
the two agree nothing is observable. They stop agreeing the day the standard is
amended — and every written copy then lies independently, in its own file, at
its own moment. That is not hypothetical here: it is exactly what happened to
the SPEC type list when ADR-013 widened it from nine to eleven.

WHAT THE ACCEPTABLE FORM IS. A count formatted from ``len(...)``. It leaves no
literal in the source at all, which is what makes the green branch of this
matcher expressible rather than merely asserted: there is no number to find.

WHY THE MATCHER IS PARAMETERISED BY SUBJECT. Its predecessor was hard-wired to
the SPEC type list and searched for one literal phrase, ``closed list of N``. It
was therefore reading a FORMULATION and not a property, and five sentences
saying the same thing in other words walked past it — one of them in the very
module the list had just been consolidated into (memory #488). Adding a second
hard-wired matcher for ADAPT categories would have repeated that mistake with
better manners, so the subject is data and the matching is one implementation.
"""

from __future__ import annotations

import io
import os
import re
import sys
from dataclasses import dataclass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, os.path.join(ROOT, "scripts"))

from service_adapts import FINDING_CATEGORIES  # noqa: E402 — path must be set first
from service_specs import SPEC_TYPES  # noqa: E402

# The trees these detectors walk. Declared, never baselined (memory #478): a
# change anywhere in them must pull the guarding tests in.
SCAN_DIRS = ("scripts", "harness", "tests")
CROSSCUTTING_SCOPE = ["scripts/", "harness/", "tests/"]

# A decimal that is a COUNT, and not something else that merely carries digits.
# Rejected by the lookarounds: v49 and v16r-spec-types (glued to an identifier),
# §8.3 and 1.5 (part of a dotted number), ADR-013 and QG-0 (a hyphenated
# designator). Each of those sets a digit beside the subject while asserting
# nothing whatever about how many members the list has.
_DIGIT = r"(?<![0-9A-Za-z_.§-])[0-9]{1,3}(?![0-9A-Za-z_.-])"

# The SAME digit with the hyphen guard lifted, usable ONLY where an explicit
# counting cue has already been matched — see _CLOSED_N below. Never use it on
# its own: without the cue it is exactly the weakening that a mutation proved
# this module cannot afford.
_DIGIT_AFTER_CUE = r"[0-9]{1,3}(?![0-9A-Za-z_.])"

# Counts spelled as words. "our closed list has nine" is a form `\d+` cannot see
# at all. Russian is here because half the prose in this tree is Russian and the
# defect does not care which language it is written in.
#
# THE FLOOR AT THREE IS DELIBERATE AND DECLARED, not an oversight: English "one"
# and "two" are pronouns far more often than counts ("one of the closed types"),
# so admitting them would buy two more catchable phrasings at the price of a
# matcher too noisy to keep. No closed list in this codebase is shorter than
# seven.
_NUMBER_WORDS = (
    r"three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen"
    r"|fifteen|sixteen|seventeen|eighteen|nineteen|twenty"
    r"|тр[её]х|четыр\w*|пят\w*|шест\w*|сем\w*|восьм\w*|восем\w*|девят\w*"
    r"|десят\w*|одиннадцат\w*|двенадцат\w*|тринадцат\w*|двадцат\w*"
)
_NUM = r"(?:" + _DIGIT + r"|(?:" + _NUMBER_WORDS + r"))"

# "closed-7", "closed to 7", "closed at eleven".
#
# THIS FORM EXISTS BECAUSE OF THE HYPHEN, and the hyphen is why the SPEC matcher
# could not simply be pointed at the ADAPT categories: seven of the eleven ADAPT
# sites write the count as `closed-7`, and _DIGIT rejects a digit after a hyphen
# ON PURPOSE, so that ADR-013 and QG-0 are not read as counts. The discriminator
# is not the punctuation but what precedes it: the literal word "closed" IS a
# counting cue, and "ADR" is not. So the cue is matched first and the digit guard
# is relaxed only behind it.
_CLOSED_N = (
    r"closed(?:[-\s]|\s+(?:to|at)\s+)(?:" + _DIGIT_AFTER_CUE + r"|(?:" + _NUMBER_WORDS + r"))"
)


@dataclass(frozen=True)
class ClosedList:
    """One closed list, and the words that mean a line is talking about it."""

    name: str
    # Does this line concern the list at all? Keeps the ADAPT matcher off SPEC
    # prose and vice versa, so neither task can silently widen the other.
    subject: str
    # The list's own plural noun, as it appears in prose ("types", "categories").
    noun: str
    # The members themselves, imported from the one place they live. NEVER typed
    # out here: a second literal copy of them is the defect `literal_list_re`
    # detects, and a detector that carried one would be the same defect a level up.
    values: tuple[str, ...] = ()

    def literal_list_re(self, run: int = 4) -> re.Pattern[str]:
        """Matches ``run`` consecutive quoted members — i.e. a second copy of the list.

        DERIVED FROM ``values``, so an amendment to the standard widens the
        detector in the same edit that widens the list. Its ancestor was a
        hand-written alternation of the nine SPEC type names living in
        test_spec_types_closed_list, and ADR-013 made the point for us: adding
        TEST and DOC meant editing the detector of literal copies BY HAND,
        because it was one.

        FOUR IN A ROW, NOT THE WHOLE LIST. A copy is a copy from the moment it
        starts, and requiring every member would let a TRUNCATED mirror walk
        past — which is the exact shape the drift takes (nine of eleven). Below
        four, ordinary prose that quotes a couple of members starts matching.
        """
        member = "|".join(re.escape(v) for v in self.values)
        # One capturing group per repetition — the quote — so the backreferences
        # run 1, 2, 3, 4. (Its SPEC ancestor also captured the member itself and
        # therefore counted 1, 3, 5, 7; copying that numbering here was an
        # `invalid group reference` on the first run.) The member alternation is
        # non-capturing on purpose: nothing needs its value, only its identity.
        parts = [rf"(['\"])(?:{member})\{i + 1}" for i in range(run)]
        return re.compile(r"\s*,\s*".join(parts))

    def forms(self) -> tuple[re.Pattern[str], ...]:
        return (
            # "9 closed SPEC types", "seven finding categories", "9 closed types"
            re.compile(_NUM + r"(?:\s+\w+){0,2}\s+(?:" + self.noun + r")\b", re.IGNORECASE),
            # "closed list of 9 RENAR types", "list of seven"
            re.compile(r"list\s+of\s+" + _NUM + r"\b", re.IGNORECASE),
            # "our closed list has nine", "Ours now carries the same eleven"
            re.compile(
                r"\b(?:has|have|carries|carry|holds|hold|contains|contain|enumerated|numbers)\s+"
                r"(?:the\s+same\s+|only\s+|now\s+|just\s+)?" + _NUM + r"\b",
                re.IGNORECASE,
            ),
            # "closed-7", "closed to 7" — see _CLOSED_N.
            re.compile(_CLOSED_N, re.IGNORECASE),
            # "7 closed types", "nine closed". The noun is NOT required here,
            # and that is the point: service_adapts.py called the ADAPT
            # CATEGORIES "the 7 closed types", so a form keyed on each list's
            # own noun missed it. The word "closed" is itself the counting cue,
            # so this form reads the claim without needing to know what the
            # members are called — a phrasing-independent net under the
            # noun-keyed forms above.
            re.compile(_NUM + r"\s+closed\b", re.IGNORECASE),
            # Russian: "доводится до одиннадцати", "в системе, знающей девять"
            re.compile(r"(?:до|из|в|на|знающ\w*)\s+(?:" + _NUMBER_WORDS + r")\b", re.IGNORECASE),
        )

    def subject_re(self) -> re.Pattern[str]:
        return re.compile(self.subject, re.IGNORECASE)


SPEC_TYPE_LIST = ClosedList(
    name="SPEC types",
    subject=r"SPEC|RENAR\s+type|перечн|тип",
    noun=r"types?",
    values=SPEC_TYPES,
)

ADAPT_FINDING_CATEGORY_LIST = ClosedList(
    name="ADAPT backward-finding categories",
    # Narrow on purpose. A bare "categor" also matches the Shared Brain's own
    # four categories ("Sync all 4 categories" in brain_sync.py) — the same
    # defect class over a DIFFERENT closed list, and one decision #256 puts
    # outside release 1.9 altogether. A subject that drags an unrelated list in
    # is how one task silently becomes three.
    subject=r"backward[-\s]?finding|finding[-\s]categor|FINDING_CATEGORIES|ADAPT|находк",
    noun=r"categor(?:y|ies)",
    values=FINDING_CATEGORIES,
)


def written_counts(text: str, closed_list: ClosedList) -> list[str]:
    """Every literal count of ``closed_list`` in ``text``, as matched fragments.

    Pure, and split out from the tree walk deliberately (memory #484). A detector
    that can only be run against the repository has no expressible green branch —
    the tree cannot be made to *not* contain a counting phrase — so a matcher
    that always reported a finding would be indistinguishable from one that
    works. Handed a string, it can be shown to stay silent on the derived form.

    THE SUBJECT WINDOW IS TWO LINES, AND A MUTATION BOUGHT THAT NUMBER. The
    count must appear on the line being examined, but the SUBJECT may sit on
    that line or the one before it. A single-line rule looked principled and
    was not: ruff wraps a long f-string, and the very message this guard exists
    to protect —

        f"Invalid finding category '{category}'. "
        f"Valid (closed list of {len(FINDING_CATEGORIES)}): ..."

    — splits so that the count lands on a line naming nothing. Writing the
    literal 7 back into it then went UNDETECTED while every test stayed green.
    The window is two lines and not more because the subject patterns are
    narrow on purpose: a wider one starts matching the Shared Brain's own four
    categories, an unrelated closed list that decision #256 puts outside this
    release entirely.
    """
    subject = closed_list.subject_re()
    forms = closed_list.forms()
    found: list[str] = []
    lines = text.splitlines()
    for n, line in enumerate(lines):
        # The subject may sit on this line or the one above it — see the
        # docstring: a wrapped f-string puts the count and its subject apart.
        on_subject = subject.search(line) or (n > 0 and subject.search(lines[n - 1]))
        if not on_subject:
            continue
        for rx in forms:
            m = rx.search(line)
            if m:
                found.append(m.group(0).strip())
                break
    return found


def sources():
    """Every Python source under SCAN_DIRS, as (repo-relative path, text)."""
    for d in SCAN_DIRS:
        for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, d)):
            dirnames[:] = [x for x in dirnames if x != "__pycache__"]
            for fn in filenames:
                if not fn.endswith(".py"):
                    continue
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, ROOT).replace(os.sep, "/")
                with io.open(full, encoding="utf-8", newline="") as fh:
                    yield rel, fh.read()


def scan_tree(closed_list: ClosedList, allowed: dict[str, str]) -> list[str]:
    """Written counts of ``closed_list`` across the tree, minus declared ones.

    ``allowed`` maps a repo-relative path to the REASON its count is legitimate.
    Two classes only, and neither is "not got round to it": a transcription of an
    EXTERNAL norm's literal (memory #474 — comparing a value against the constant
    that produced it is a tautology, so the standard's own number is the only
    honest reference), and the JOURNAL prose of a migration recording what it
    built. An entry admitted for a live present-tense claim would be baselining
    the gap these tests exist to close (memory #478).
    """
    offenders = []
    for rel, src in sources():
        if rel in allowed:
            continue
        for frag in written_counts(src, closed_list):
            offenders.append(f"{rel}: {frag!r}")
    return sorted(offenders)
