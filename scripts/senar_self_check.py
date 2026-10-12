"""Do the conformance matrices still point at code that exists?

WHAT THIS IS NOT, said first because the whole value is in the distinction. It
is NOT a conformance assessment against SENAR v1.3. It cannot be: the normative
text of the standard is not in this tree — only our own restatement in
`docs/{en,ru}/senar.md` — so any rubric applied here is OURS, and calling it the
standard's would be exactly the move this release spent itself removing. The
matrices already say the conformance percentage is not computable here and is
deliberately left unnamed (decision #334). This module does not compute it.

WHAT IT IS. Every row of those matrices asserts a mechanism and cites the code
implementing it. That citation is checkable, and this checks it: it resolves
each named file and each named symbol against the tree and refuses when one of
them is gone. A renamed module turns a true claim into an unfalsifiable one
silently, and the page keeps reading as evidence.

MEASURED ON THE LIVE TREE (session #238). Each matrix carries 45 rows in a table
that has a citation column: 33 cite a file or a symbol, 12 cite nothing. Across
both pages that is 20 unique files and 16 unique symbols, and all of them
resolve. The green here is therefore a RATCHET on a state that already holds,
not a discovery — and the number that matters more is the other one.

THE OTHER NUMBER. Rows that cite NOTHING cannot be checked by anything: "keyword
detection in notes", "QG-0 + QG-2 joint enforcement". The totals underneath
("13/13 implemented") lean on them equally. So the report states that share
rather than averaging it away — unevenness of evidence is a finding, not noise.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from senar_version_claim import DECLARED_SENAR_VERSION

__all__ = [
    "MATRICES",
    "RUBRIC_PROVENANCE",
    "Claim",
    "Report",
    "check",
    "parse_claims",
    "render",
]

#: The pages this checks. Both languages, because a citation that rots in one
#: translation and not the other is the ordinary case, not the exotic one.
MATRICES: tuple[str, ...] = (
    "docs/ru/senar-compliance-matrix.md",
    "docs/en/senar-compliance-matrix.md",
)

#: Column headers that mark the citation column, lowercased. A table WITHOUT one
#: carries no citations and is not part of this check — which is why the column
#: is found by its own header rather than by the table's position or title. The
#: summary and gap tables are excluded by that rule automatically, and a table
#: added tomorrow is included by it automatically.
_EVIDENCE_HEADERS = frozenset({"evidence", "доказательство"})

#: Said in the report itself, not only here. A self-check whose provenance lives
#: in a docstring is a self-check whose reader never sees it.
RUBRIC_PROVENANCE = (
    "THE RUBRIC BELOW IS OURS, NOT THE STANDARD'S. SENAR's normative text is not "
    "vendored in this tree, so no check here can be an assessment against it. "
    f"TAUSIK claims SENAR v{DECLARED_SENAR_VERSION} (decision #336); this checks "
    "whether the pages making that claim still cite code that exists. It is not "
    "certification, not external attestation, and produces no conformance "
    "percentage — that value is not computable here and is left unnamed "
    "(decision #334)."
)

#: `module.py` and `path/to/module.py` — a citation of a file.
_FILE_REF = re.compile(r"`([A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:py|md|json|ya?ml|sh))`")

#: `some_function()` and `Class.method()` — a citation of a symbol. The
#: parentheses are REQUIRED: without them every backticked word in the cell would
#: be read as a symbol, and cells name config keys, table names and CLI flags in
#: backticks too. Demanding the call form is what keeps the checker from
#: inventing citations the author never made — and a checker that invents them
#: goes red on the author's correct page, which is the failure that gets a
#: checker deleted.
_SYMBOL_REF = re.compile(r"`([A-Za-z_][A-Za-z0-9_.]*)\(\)`")

#: How much of a row's subject a report line quotes before it stops being a
#: label and starts being the row.
_MAX_SUBJECT = 60

#: Where a bare file citation may resolve. A cell writes `gate_qg0_check.py`
#: without its directory because the reader knows where gates live.
_SEARCH_ROOTS = ("scripts", "tests", "bootstrap", "harness", "docs", "stacks")

#: How many rows of each list a report prints before stating the remainder.
EXAMPLES = 10


@dataclass(frozen=True)
class Claim:
    """One matrix row: what it asserts, and what it offers as proof."""

    path: str
    line: int
    subject: str
    files: tuple[str, ...]
    symbols: tuple[str, ...]

    @property
    def cites_anything(self) -> bool:
        return bool(self.files or self.symbols)

    def where(self) -> str:
        return f"{self.path}:{self.line}"


@dataclass
class Report:
    """The verdict and the two numbers it rests on."""

    claims: list[Claim]
    broken: list[tuple[Claim, str]]
    unparsable: list[str]

    @property
    def cited(self) -> list[Claim]:
        return [c for c in self.claims if c.cites_anything]

    @property
    def uncited(self) -> list[Claim]:
        return [c for c in self.claims if not c.cites_anything]

    @property
    def ok(self) -> bool:
        """Red on a broken citation, and on nothing else.

        Uncited rows are REPORTED, never fatal: this module cannot tell an
        unevidenced claim from one whose evidence is genuinely a paragraph, and
        refusing on that difference would make the check unrunnable rather than
        honest. The count is the finding; the verdict is about rot.
        """
        return not self.broken


def _cells(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return []
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def _is_separator(cells: list[str]) -> bool:
    return bool(cells) and all(set(c) <= set("-: ") and "-" in c for c in cells)


def _subject(cells: list[str], evidence_at: int) -> str:
    """A label the reader can find on the page.

    The rules table keys its rows by number — `1`, `9.1`, `QG-2` — so the first
    cell alone produces report lines reading "9.1" and nothing else, which
    names a row without identifying it. Where the key is short, the description
    beside it is carried along. The evidence column is never used: it is what
    the report is already talking about.
    """
    key = cells[0]
    if len(key) <= 5 and len(cells) > 1 and evidence_at != 1:
        return f"{key} — {cells[1]}"[:_MAX_SUBJECT]
    return key[:_MAX_SUBJECT]


def parse_claims(text: str, path: str) -> list[Claim]:
    """Rows of every table that HAS a citation column, and only those.

    The header drives it. A table whose columns are `Gap | План | Приоритет`
    makes no citation and yields nothing here; a table added later with an
    Evidence column is picked up without anyone registering it. Selecting by
    the table's title or position instead would need editing every time the
    page is reorganised, and would silently stop covering a renamed section.
    """
    claims: list[Claim] = []
    evidence_at: int | None = None
    header: list[str] = []

    for number, line in enumerate(text.splitlines(), start=1):
        cells = _cells(line)
        if not cells:
            evidence_at = None
            header = []
            continue
        if _is_separator(cells):
            # The row before was the header; decide now whether this table counts.
            evidence_at = next(
                (i for i, name in enumerate(header) if name.lower() in _EVIDENCE_HEADERS),
                None,
            )
            continue
        if evidence_at is None:
            header = cells
            continue
        if evidence_at >= len(cells):
            continue
        cell = cells[evidence_at]
        claims.append(
            Claim(
                path=path,
                line=number,
                subject=_subject(cells, evidence_at),
                files=tuple(dict.fromkeys(_FILE_REF.findall(cell))),
                symbols=tuple(dict.fromkeys(_SYMBOL_REF.findall(cell))),
            )
        )
    return claims


def _file_resolves(repo_root: Path, name: str) -> bool:
    """Resolve a citation the way its reader does.

    A cell writes `gate_qg0_check.py` without a directory because the reader
    knows where gates live, and `hooks/task_gate.py` with a PARTIAL one for the
    same reason — hooks live in `scripts/hooks/`, and no document in this tree
    writes that prefix out. Both are citations that a reader follows without
    difficulty, so both must resolve here.

    MEASURED: requiring a separator-bearing citation to resolve from the repo
    root turned three correct rows red on the first live run. A checker that
    reddens a correct page is not strict, it is wrong — and it is the kind of
    wrong that gets the checker switched off rather than the page fixed.

    Suffix matching under the known roots keeps it from being loose: it accepts
    `hooks/task_gate.py` and still rejects `nowhere/task_gate.py`, because the
    latter matches no real path's tail.
    """
    if (repo_root / name).exists():
        return True
    suffix = f"/{name}" if "/" in name else None
    base_name = name.rsplit("/", 1)[-1]
    for root in _SEARCH_ROOTS:
        base = repo_root / root
        if not base.is_dir():
            continue
        for candidate in base.rglob(base_name):
            if suffix is None or candidate.as_posix().endswith(suffix):
                return True
    return False


def check(repo_root: str | Path, matrices: tuple[str, ...] = MATRICES) -> Report:
    """Resolve every citation on the claim pages. An absent page is not a pass."""
    from symbol_index import defined_names, unparsable

    root = Path(repo_root)
    names = defined_names(root)
    claims: list[Claim] = []
    broken: list[tuple[Claim, str]] = []

    for relative in matrices:
        page = root / relative
        if not page.is_file():
            # Absence, stated as a broken citation rather than skipped: a claim
            # page that vanished took its evidence with it, and silence here
            # would read as "nothing to check" (decision #334).
            #
            # The sentinel is NOT added to `claims`. It carries no citation, so
            # counting it there put the same missing page into `broken` AND into
            # `uncited`, and the coherence lens reported one fact as two
            # findings — caught by the truncation test, which saw nine dropped
            # findings where it had set up seven.
            broken.append(
                (
                    Claim(path=relative, line=0, subject="(the page itself)", files=(), symbols=()),
                    f"{relative} does not exist",
                )
            )
            continue
        claims.extend(parse_claims(page.read_text(encoding="utf-8"), relative))

    for claim in claims:
        for name in claim.files:
            if not _file_resolves(root, name):
                broken.append((claim, f"file `{name}` is cited and not found"))
        for symbol in claim.symbols:
            if symbol.split(".")[-1] not in names:
                broken.append((claim, f"symbol `{symbol}()` is cited and not defined"))

    return Report(claims=claims, broken=broken, unparsable=unparsable(root))


def render(report: Report) -> str:
    """Provenance first, then the refusal, then the unevenness."""
    lines = [RUBRIC_PROVENANCE, ""]

    total = len(report.claims)
    cited = len(report.cited)
    uncited = len(report.uncited)
    share = (
        f"  ({100 * uncited // total}% of the rows the totals are computed from)" if total else ""
    )
    lines.append(f"claim rows on the citation pages: {total}")
    lines.append(f"  citing a file or a symbol: {cited}")
    lines.append(f"  citing nothing checkable:  {uncited}{share}")

    if report.broken:
        lines.append("")
        lines.append(f"BROKEN CITATIONS: {len(report.broken)}")
        for claim, why in report.broken:
            lines.append(f"  {claim.where()}  {claim.subject}")
            lines.append(f"      {why}")
    else:
        lines.append("")
        lines.append("every citation resolves.")

    if report.unparsable:
        lines.append("")
        lines.append(
            f"{len(report.unparsable)} file(s) could not be parsed, so a symbol "
            "reported missing may live in one of them:"
        )
        for name in report.unparsable[:5]:
            lines.append(f"  {name}")

    if report.uncited:
        lines.append("")
        lines.append(
            "ROWS ASSERTING WITHOUT CITING. Nothing can check these, and the "
            "totals on the page count them the same as the rest:"
        )
        for claim in report.uncited[:EXAMPLES]:
            lines.append(f"  {claim.where()}  {claim.subject}")
        if len(report.uncited) > EXAMPLES:
            lines.append(f"  ... {len(report.uncited) - EXAMPLES} more")

    return "\n".join(lines)


if __name__ == "__main__":
    # A route EXISTS for this check, so the module refuses rather than offering
    # a second way in. `python scripts/senar_self_check.py` would work and would
    # contradict the project's own rule that framework calls go through the
    # wrapper — and an unfollowable rule teaches that the rules here are
    # approximate, which is the lesson that generalises to the rules that
    # matter (route_map, session #233).
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__, "`.tausik/tausik coherence`")
