"""The SENAR version TAUSIK publicly claims, and the guard that keeps it single.

WHY THIS IS NOT PART OF THE version-ref SCANNER. ``doc_drift_common`` deliberately
lists ``SENAR`` in ``_FOREIGN_VERSION_PREFIXES`` so that a foreign standard's
version is never compared against TAUSIK's own. That exemption is correct and
stays: SENAR versions on an independent timeline, and a scanner that demanded
they move together would be wrong. What was missing is the *other* check — that
the version TAUSIK claims to implement is the SAME version everywhere it is
claimed. That is this module, and it is a separate mechanism on purpose.

WHAT WAS MEASURED (session #225, live tree). The product asserted three different
things at once: ``CLAUDE.md`` / ``AGENTS.md`` / ``CONTRIBUTING.md`` / ``QWEN.md``
and the bootstrap templates that generate them said v1.3; both compliance
matrices were titled "SENAR v1.5 Core" and closed with "compliance: 100%"; both
READMEs named no version at all. A ninth site the filing never mentioned —
``docs/ru/agent-contract.md`` — said v1.3 in a heading the first grep missed.

A CLAIM IS NOT A CITATION, AND A VERSION IS NOT A RULE NUMBER. Three shapes share
one spelling, and conflating them is how this guard would become either useless
or disabled:

* ``SENAR v1.3 Core`` — a CLAIM. TAUSIK says it implements that edition. Must
  equal :data:`DECLARED_SENAR_VERSION`.
* ``SENAR 1.4 §8.6(e)`` — a CITATION. It locates a requirement in the edition
  that phrased it, which is a fact about the standard, not a claim about us. Any
  version is legitimate here; ~30 such lines live in ``scripts/`` today.
* ``SENAR Rule 9.1``, ``SENAR 9.2`` — a RULE LOCATOR. "9.2" is a chapter, not an
  edition. The first draft of this scanner read all 57 mentions on the surface as
  versions and would have reddened on forty of them (convention #638: look at the
  noun beside the number before binding it).

THE AMBIGUOUS SHAPE IS REFUSED, NOT GUESSED. A bare ``SENAR N.M`` with no ``v``,
no ``Core`` and no ``§`` is genuinely undecidable from syntax alone. When ``N``
cannot be a SENAR edition major it is a rule locator and is ignored; when ``N``
COULD be one, this module reports it as unclassified and the check fails, naming
the file and line. Silence there would be indistinguishable from coverage —
SENAR 1.4 §8.6(e), applied to the guard itself.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple

from doc_drift_common import _strip_dynamic_block, _strip_fenced_blocks

__all__ = [
    "CLAIM_SURFACE_FILES",
    "CLAIM_SURFACE_GLOBS",
    "DECLARED_SENAR_VERSION",
    "EXEMPT_SURFACES",
    "REQUIRED_CLAIM_FILES",
    "Mention",
    "check_claim_surface",
    "classify",
    "iter_surface_paths",
    "scan_claim_surface",
]


#: The SENAR edition TAUSIK publicly claims to implement. Owner's decision #336
#: (session #225): v1.5 is in preparation and NOT ready, so claiming it anywhere
#: is forbidden; v1.3 is what the product states. This literal is the single
#: source — every claim site is checked against it, and none of them is allowed
#: to be the authority for another.
DECLARED_SENAR_VERSION = "1.3"

#: Files that speak to a user or an agent about which SENAR edition TAUSIK
#: implements. The bootstrap template module is here because it is the SOURCE of
#: three of the generated ones (CLAUDE.md, AGENTS.md, QWEN.md) — fixing only the
#: generated copies would let the next bootstrap put the old version back.
CLAIM_SURFACE_FILES: tuple[str, ...] = (
    "README.md",
    "README.ru.md",
    "CLAUDE.md",
    "AGENTS.md",
    "CONTRIBUTING.md",
    "QWEN.md",
    "docs/README.md",
    "bootstrap/bootstrap_templates.py",
)

#: Files that MUST carry the claim, not merely agree with it when they mention
#: it. Both READMEs are here because the measured defect was an ABSENCE: they
#: called TAUSIK "the reference implementation of SENAR" and named no edition at
#: all, which no divergence check can see — silence agrees with everything.
REQUIRED_CLAIM_FILES: tuple[str, ...] = (
    "README.md",
    "README.ru.md",
    "docs/en/senar-compliance-matrix.md",
    "docs/ru/senar-compliance-matrix.md",
)

#: Published documentation. Globbed rather than listed so a NEW document that
#: names a SENAR version is caught without anyone remembering to register it —
#: the failure mode the filing called out by name ("a guard that stays silent
#: when the version is named in a fourth place is useless").
CLAIM_SURFACE_GLOBS: tuple[str, ...] = ("docs/en/*.md", "docs/ru/*.md")

#: Trees that name SENAR versions and MUST NOT be checked against the declared
#: one, each with the reason it is out. Every pattern is asserted to match at
#: least one real path by the test suite (decision #335): an entry matching
#: nothing is a dead line guarding a file that no longer exists, and it would
#: read as coverage.
EXEMPT_SURFACES: tuple[tuple[str, str], ...] = (
    (
        "CHANGELOG.md",
        "a record of what PAST releases claimed; editing it to agree with today "
        "would rewrite history, which is the lie this guard exists to prevent",
    ),
    ("CHANGELOG.ru.md", "same as CHANGELOG.md — the Russian record of past claims"),
    ("ROADMAP.md", "generated projection of story titles from the database, not authored prose"),
    ("tausik/**/*.md", "state projection: tasks, decisions and memory record past statements"),
    ("tests/**/*.py", "fixtures deliberately carry divergent version strings to test scanners"),
    (
        "scripts/**/*.py",
        "code comments cite sections (SENAR 1.4 §8.6) as the provenance of a rule; "
        "provenance is not a conformance claim and the files are not published prose",
    ),
    (
        "harness/**/*.py",
        "vendored copy of the same code comments — same reason as scripts/",
    ),
    (
        "docs/research/*.md",
        "research notes and applicability studies, not statements the product makes",
    ),
)

# SENAR, then at most a short window of words, then a version-shaped number. The
# window is what catches "SENAR Compliance (v1.3 Core)" — a real heading in
# docs/ru/agent-contract.md that an anchored `SENAR\s+v?N.M` pattern misses
# entirely. Non-greedy, so each SENAR occurrence binds to the FIRST number after
# it and a trailing framework stamp ("... (SENAR Rule 10.15) - v1.5") cannot be
# mistaken for a second mention.
#
# ONE pattern, not an alternation of a v-prefixed and a bare form. The first
# draft tried the `v` branch first, and Python's alternation let it reach PAST
# an intervening rule number: "## Reviews (SENAR Rule 10.15) - v1.5" bound to
# the trailing FRAMEWORK stamp and was reported as a SENAR v1.5 claim on a line
# that claims nothing about SENAR at all. Making `v` optional inside a single
# non-greedy pattern binds to the first number after SENAR -- 10.15 -- which the
# rule-noun test then discards as the chapter it is.
_MENTION_RE = re.compile(r"SENAR(?P<between>[^\n]{0,24}?)\b(?P<v>v?)(?P<ver>\d+\.\d+)")

# A noun that turns the number into a chapter reference rather than an edition.
_RULE_NOUN_RE = re.compile(r"(?i)\b(rules?|sections?|правил[оаы]|глав[аы])\W*$")

# "Core" is SENAR's edition suffix ("SENAR v1.5 Core"); its presence right after
# the number marks an edition even when the `v` was dropped.
_CORE_SUFFIX_RE = re.compile(r"(?i)^\s*core\b")

# A section sign close behind the number makes it a citation of that edition.
_SECTION_RE = re.compile(r"^\s*(§|Section\b|§§)")


class Mention(NamedTuple):
    """One SENAR-version-shaped mention found on the claim surface."""

    path: str
    line: int
    version: str
    kind: str  # claim | citation | rule-locator | unclassified
    text: str


def classify(between: str, version: str, after: str, v_prefixed: bool) -> str:
    """Return the kind of a single mention.

    ``between`` is the text separating "SENAR" from the number, ``after`` the
    text immediately following it, ``v_prefixed`` whether the number was written
    as ``vN.M``. Order matters: a rule noun wins over everything, because
    "SENAR Rule 1.4" names a chapter no matter what follows it.
    """
    if _RULE_NOUN_RE.search(between):
        return "rule-locator"
    if v_prefixed or _CORE_SUFFIX_RE.search(after):
        return "claim"
    if _SECTION_RE.search(after):
        return "citation"
    # Bare `SENAR N.M`. Decidable only when N cannot be an edition major.
    if version.split(".", 1)[0] != DECLARED_SENAR_VERSION.split(".", 1)[0]:
        return "rule-locator"
    return "unclassified"


def iter_surface_paths(root: Path) -> Iterator[tuple[str, Path]]:
    """Yield (relative posix path, path) for every file on the claim surface."""
    seen: set[str] = set()
    for rel in CLAIM_SURFACE_FILES:
        path = root / rel
        if path.is_file() and rel not in seen:
            seen.add(rel)
            yield rel, path
    for pattern in CLAIM_SURFACE_GLOBS:
        for path in sorted(root.glob(pattern)):
            rel = path.relative_to(root).as_posix()
            if rel not in seen:
                seen.add(rel)
                yield rel, path


def scan_claim_surface(root: Path) -> list[Mention]:
    """Every SENAR-version-shaped mention on the claim surface, classified.

    Fenced code blocks and the generated DYNAMIC block are removed first, using
    the same helpers the doc-drift scanners use, so an example command or the
    injected memory tail cannot be read as a product claim. Both helpers
    preserve line numbers.
    """
    found: list[Mention] = []
    for rel, path in iter_surface_paths(root):
        text = path.read_text(encoding="utf-8", errors="replace")
        text = _strip_fenced_blocks(_strip_dynamic_block(text))
        for lineno, line in enumerate(text.splitlines(), 1):
            for match in _MENTION_RE.finditer(line):
                v_prefixed = bool(match.group("v"))
                version = match.group("ver")
                between = match.group("between")
                after = line[match.end() : match.end() + 16]
                found.append(
                    Mention(
                        path=rel,
                        line=lineno,
                        version=version,
                        kind=classify(between or "", version, after, v_prefixed),
                        text=line.strip()[:160],
                    )
                )
    return found


def check_claim_surface(root: Path) -> list[str]:
    """Failures, one human-readable line each. Empty means the surface agrees.

    Two ways to fail, and both name the file and line rather than reporting a
    count: a CLAIM naming an edition other than the declared one, and a mention
    this module refuses to classify. A citation is never a failure.
    """
    problems: list[str] = []
    mentions = scan_claim_surface(root)
    claimed_in = {m.path for m in mentions if m.kind == "claim"}
    for rel in REQUIRED_CLAIM_FILES:
        if not (root / rel).is_file():
            problems.append(f"{rel}: required claim site is missing from the tree")
        elif rel not in claimed_in:
            problems.append(
                f"{rel}: names no SENAR edition -- this file must state "
                f"`SENAR v{DECLARED_SENAR_VERSION} Core` explicitly; silence is not agreement"
            )
    for m in mentions:
        if m.kind == "claim" and m.version != DECLARED_SENAR_VERSION:
            problems.append(
                f"{m.path}:{m.line}: claims SENAR v{m.version}, but the declared "
                f"version is v{DECLARED_SENAR_VERSION} -- {m.text}"
            )
        elif m.kind == "unclassified":
            problems.append(
                f"{m.path}:{m.line}: ambiguous SENAR {m.version} -- write `v{m.version}` "
                f"for an edition claim or cite a section (`SENAR {m.version} §8.x`) "
                f"for provenance -- {m.text}"
            )
    return problems


def main(argv: list[str] | None = None) -> int:
    """Print failures for the tree rooted at argv[1] (default: repo root)."""
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path(args[0]).resolve() if args else Path(__file__).resolve().parent.parent
    problems = check_claim_surface(root)
    for line in problems:
        print(line)
    if not problems:
        print(f"SENAR claim surface agrees on v{DECLARED_SENAR_VERSION}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
