"""The conformance pages cite code, and the citations are checked.

WHY THIS IS NOT A CONFORMANCE TEST, and why saying so is half the point. SENAR's
normative text is not vendored here — only our own restatement — so no rubric
applied in this repository is the standard's. The matrices already state that the
conformance percentage is not computable here and leave it unnamed (decision
#334). What IS computable is whether the evidence those pages offer still points
at code that exists, and that is all this asserts.

THE TEST THAT DECIDES WHETHER THE REST MEANS ANYTHING is the negative one. A
self-check that cannot go red is decoration: it would keep printing "every
citation resolves" over a page citing modules deleted a year ago, and the green
would be read as evidence. So the refusal is exercised on a fixture whose
citations are deliberately gone, and the acceptance is exercised beside it —
either one alone proves nothing about the other.

MEASURED ON THE LIVE TREE (session #238): 45 rows per matrix in a table carrying
a citation column, 33 of them citing a file or a symbol, 12 citing nothing, 20
unique files and 16 unique symbols, all resolving. The green below is a ratchet
on that state, not a discovery.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import senar_self_check as ssc  # noqa: E402
from symbol_index import defined_names  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/", "docs/"]

#: A page shaped like the real ones: a table with a citation column, a table
#: without, and a row citing nothing.
_PAGE = """# Matrix

| Gate | Требование | Статус | Evidence |
|------|-----------|--------|----------|
| QG-0 | Цель обязательна | ✅ | `senar_self_check.py` `parse_claims()` |
| QG-2 | Verify cache | ✅ | таблица `verification_runs` — same hash |

## Gaps

| Gap | План | Приоритет |
|-----|------|-----------|
| something | fix it | Done |
"""


def _write(tmp_path: Path, body: str, name: str = "page.md") -> tuple[str, tuple[str, ...]]:
    """A whole little project: the page, plus the code its citations point at.

    The cited module lives IN the fixture rather than being the real
    `scripts/senar_self_check.py`, so the positive case proves resolution
    against the tree it was handed. Pointing the fixture at this repository
    would make it pass for a reason the fixture does not control.
    """
    (tmp_path / "docs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / name).write_text(body, encoding="utf-8")
    scripts = tmp_path / "scripts"
    scripts.mkdir(exist_ok=True)
    (scripts / "senar_self_check.py").write_text(
        "MATRICES = ()\n\n\ndef parse_claims(text, path):\n    return []\n", encoding="utf-8"
    )
    return str(tmp_path), (f"docs/{name}",)


class TestItCanSayNo:
    """AC5, and the one the others rest on."""

    @pytest.mark.parametrize(
        "was,now",
        [
            pytest.param(
                "`senar_self_check.py`", "`module_deleted_last_year.py`", id="renamed_module"
            ),
            pytest.param(
                "`parse_claims()`", "`function_nobody_ever_wrote()`", id="renamed_symbol"
            ),
        ],
    )
    def test_a_citation_whose_target_is_gone_is_refused(self, tmp_path, was, now):
        """The two ways a page rots: the file moves, or the function is renamed
        inside it. Both leave the sentence on the page reading as true."""
        root, pages = _write(tmp_path, _PAGE.replace(was, now))
        report = ssc.check(root, pages)
        assert not report.ok
        assert any(now.strip("`()") in why for _c, why in report.broken)

    def test_the_refusal_names_where_to_look(self, tmp_path):
        body = _PAGE.replace("`senar_self_check.py`", "`gone.py`")
        root, pages = _write(tmp_path, body)
        text = ssc.render(ssc.check(root, pages))
        assert "docs/page.md:5" in text, "the reader is told what is broken and not where"
        assert "QG-0" in text

    def test_a_page_that_does_not_exist_is_refused_rather_than_skipped(self, tmp_path):
        """Absence is not a pass. A claim page that vanished took its evidence
        with it, and silence would read as 'nothing to check' (decision #334)."""
        report = ssc.check(str(tmp_path), ("docs/never-existed.md",))
        assert not report.ok
        assert any("does not exist" in why for _c, why in report.broken)

    def test_the_same_page_with_working_citations_is_accepted(self, tmp_path):
        """The other half. A verdict that is always the same says nothing, so
        acceptance is asserted on the same fixture the refusals used."""
        root, pages = _write(tmp_path, _PAGE)
        report = ssc.check(root, pages)
        assert report.ok, [why for _c, why in report.broken]


class TestOnlyTablesThatCiteAreRead:
    """The citation column is found by its own header, so reorganising the page
    cannot silently drop a section out of coverage."""

    def test_a_table_without_a_citation_column_yields_no_claims(self, tmp_path):
        claims = ssc.parse_claims(_PAGE, "docs/page.md")
        assert all("Gap" not in c.subject for c in claims)
        assert len(claims) == 2

    def test_the_english_header_is_recognised_too(self):
        page = "| Rule | Description | Evidence |\n|---|---|---|\n| 1 | x | `a.py` |\n"
        assert len(ssc.parse_claims(page, "p.md")) == 1

    def test_a_row_citing_nothing_is_kept_and_marked(self, tmp_path):
        claims = ssc.parse_claims(_PAGE, "docs/page.md")
        uncited = [c for c in claims if not c.cites_anything]
        assert len(uncited) == 1
        assert "Verify cache" in uncited[0].subject

    def test_a_backticked_word_without_parentheses_is_not_read_as_a_symbol(self):
        """`verification_runs` is a table name. Reading every backticked word as
        a symbol would redden a correct page, and a checker that reddens correct
        pages gets switched off rather than obeyed."""
        claims = ssc.parse_claims(_PAGE, "docs/page.md")
        assert all("verification_runs" not in c.symbols for c in claims)


class TestTheRubricIsDeclaredOurs:
    """AC1. Not in a docstring — in the report the reader actually sees."""

    @pytest.mark.parametrize(
        "needle",
        [
            pytest.param("OURS, NOT THE STANDARD'S", id="rubric_is_ours"),
            pytest.param("not vendored", id="why_it_is_ours"),
            pytest.param("not certification", id="not_certification"),
            pytest.param("not external attestation", id="not_attestation"),
        ],
    )
    def test_the_report_states_what_it_is_and_is_not(self, tmp_path, needle):
        root, pages = _write(tmp_path, _PAGE)
        assert needle in ssc.render(ssc.check(root, pages))

    def test_no_conformance_percentage_is_produced(self, tmp_path):
        """AC7. The one number this must never invent."""
        root, pages = _write(tmp_path, _PAGE)
        text = ssc.render(ssc.check(root, pages))
        assert "conformance percentage" in text and "not computable" in text
        # The only percentage in the report is the share of uncited rows, and it
        # is labelled as such.
        for line in text.splitlines():
            if "%" in line:
                assert "rows" in line, f"an unlabelled percentage: {line!r}"

    def test_the_claimed_edition_comes_from_the_single_source(self):
        """Not restated here. `senar_version_claim` owns it, and a second copy
        would drift from the first exactly as nine claim sites once did."""
        source = (_REPO / "scripts" / "senar_self_check.py").read_text(encoding="utf-8")
        assert "DECLARED_SENAR_VERSION" in source
        assert '"1.3"' not in source, "the edition is hardcoded beside its owner"


class TestUnevennessIsNamedNotAveraged:
    """AC3. The totals on the page count uncited rows the same as the rest."""

    def test_the_report_states_how_many_rows_cite_nothing(self, tmp_path):
        root, pages = _write(tmp_path, _PAGE)
        text = ssc.render(ssc.check(root, pages))
        assert "citing nothing checkable" in text, "the count is missing"
        assert "ASSERTING WITHOUT CITING" in text, "the rows themselves are not listed"
        assert text.index("citing nothing") < text.index("ASSERTING"), (
            "the reader meets the list before the number that frames it"
        )

    def test_uncited_rows_do_not_make_the_verdict_red(self, tmp_path):
        """This module cannot tell an unevidenced claim from one whose evidence
        is genuinely a paragraph. Refusing on the difference would make the
        check unrunnable rather than honest."""
        page = "| Rule | Description | Evidence |\n|---|---|---|\n| 1 | x | prose only |\n"
        root, pages = _write(tmp_path, page)
        report = ssc.check(root, pages)
        assert report.ok
        assert len(report.uncited) == 1

    def test_the_example_list_is_bounded_and_the_remainder_stated(self, tmp_path):
        rows = "".join(f"| {i} | subject {i} | prose |\n" for i in range(25))
        page = "| Rule | Description | Evidence |\n|---|---|---|\n" + rows
        root, pages = _write(tmp_path, page)
        text = ssc.render(ssc.check(root, pages))
        assert f"{25 - ssc.EXAMPLES} more" in text


class TestTheLiveMatricesStillCiteExistingCode:
    """The ratchet. Both real pages, on the real tree."""

    def test_every_citation_on_the_real_pages_resolves(self):
        report = ssc.check(_REPO)
        assert report.ok, "\n".join(f"{c.where()} {why}" for c, why in report.broken)

    def test_the_pages_are_actually_being_read(self):
        """A green produced by finding no rows at all would be meaningless. The
        floor is deliberately below the measured 33 per page so ordinary
        editing does not trip it — it exists to catch the parser going blind."""
        report = ssc.check(_REPO)
        assert len(report.cited) >= 40, f"only {len(report.cited)} cited rows found"

    @pytest.mark.parametrize("page", ssc.MATRICES)
    def test_both_languages_are_covered(self, page):
        assert (_REPO / page).is_file()
        report = ssc.check(_REPO)
        assert any(c.path == page for c in report.claims)


class TestTheSummaryTableStatesTheMeasuredNumber:
    """The column that replaced the percentage must not rot the way it did.

    A "Score" column printed **100%** five times while the paragraph beneath it
    said the value was not computable. That column was stale because nothing
    compared it to anything. Its replacement counts rows citing code — a number
    this module produces — so it is compared here, and a page edited without
    updating it goes red.
    """

    _TOTAL = re.compile(r"\*\*(\d+)\s+(?:из|of)\s+(\d+)\*\*")
    _SECTION = re.compile(r"\|\s*(\d+)\s+(?:из|of)\s+(\d+)\s*\|")

    @pytest.mark.parametrize("page", ssc.MATRICES)
    def test_the_total_matches_what_the_checker_counts(self, page):
        text = (_REPO / page).read_text(encoding="utf-8")
        stated = self._TOTAL.search(text)
        assert stated, "the summary no longer states a total"
        cited, rows = int(stated.group(1)), int(stated.group(2))

        # The summary covers the four SENAR categories, not the "additional
        # features" table — so the comparison is against the first `rows` claims
        # of the page, which is exactly those four sections in order.
        claims = [c for c in ssc.check(_REPO).claims if c.path == page][:rows]
        assert len(claims) == rows, f"the page no longer has {rows} rows in those sections"
        measured = sum(1 for c in claims if c.cites_anything)
        assert measured == cited, (
            f"{page} states {cited} of {rows} rows cite code; {measured} do. "
            "The stale-number failure this column was created to end."
        )

    @pytest.mark.parametrize("page", ssc.MATRICES)
    def test_the_section_rows_add_up_to_the_total(self, page):
        text = (_REPO / page).read_text(encoding="utf-8")
        sections = [(int(a), int(b)) for a, b in self._SECTION.findall(text)]
        stated = self._TOTAL.search(text)
        assert stated and sections, "the summary table lost its shape"
        assert sum(a for a, _ in sections) == int(stated.group(1))
        assert sum(b for _, b in sections) == int(stated.group(2))

    @pytest.mark.parametrize("page", ssc.MATRICES)
    def test_no_conformance_percentage_survives_in_the_summary(self, page):
        """AC4. The number a reader takes away instead of the caveat."""
        text = (_REPO / page).read_text(encoding="utf-8")
        summary = text[text.rfind("\n## ") :]
        assert "**100%**" not in summary, "the conformance score is back in the summary table"


class TestCitationsResolveTheWayAReaderFollowsThem:
    """A partial path is how these pages cite hooks, and it must resolve."""

    def test_a_partial_path_resolves_under_the_source_roots(self, tmp_path):
        """`hooks/task_gate.py` means `scripts/hooks/task_gate.py`; no document
        in this tree writes the prefix out. Demanding the full path turned three
        correct rows red on the first live run."""
        page = "| Rule | D | Evidence |\n|---|---|---|\n| 1 | x | `hooks/task_gate.py` |\n"
        root = _REPO
        report = ssc.check(root, ())
        assert report.ok  # premise: nothing else is broken
        claims = ssc.parse_claims(page, "p.md")
        assert claims[0].files == ("hooks/task_gate.py",)
        assert ssc._file_resolves(Path(root), "hooks/task_gate.py")

    def test_a_partial_path_that_matches_no_real_tail_is_still_refused(self):
        """The mirror. Suffix matching must not degrade into basename matching,
        or a citation could name any directory it liked."""
        assert not ssc._file_resolves(Path(_REPO), "nowhere/task_gate.py")


class TestTheLensCarriesItWithoutCryingWolf:
    """AC6. It runs inside `tausik coherence`, and it stays quiet where the
    pages were never ours to begin with."""

    def test_a_project_without_the_pages_produces_no_finding(self, tmp_path):
        """Every consumer installation is such a project. `check` is right to
        call a NAMED missing page a broken citation; a repository-wide audit
        applying that rule would report a defect in every install."""
        import repo_coherence

        assert repo_coherence._senar_claim_citations(tmp_path) == []

    def test_this_repository_reports_its_uncited_rows(self):
        import repo_coherence

        findings = repo_coherence._senar_claim_citations(_REPO)
        assert findings, "the lens carries the check but says nothing about our own pages"
        assert all(f.severity != "high" for f in findings), "\n".join(f.detail for f in findings)
        assert any("cite nothing checkable" in f.summary for f in findings)

    def test_a_broken_citation_reaches_the_lens_as_high(self, tmp_path):
        """The negative half of the wiring: a report the lens would rank first."""
        import repo_coherence

        docs = tmp_path / "docs" / "ru"
        docs.mkdir(parents=True)
        (docs / "senar-compliance-matrix.md").write_text(
            "| Gate | D | Evidence |\n|---|---|---|\n| QG-0 | x | `vanished_module.py` |\n",
            encoding="utf-8",
        )
        findings = repo_coherence._senar_claim_citations(tmp_path)
        assert any(f.severity == "high" for f in findings)
        assert any("vanished_module.py" in f.detail for f in findings)


class TestTheNameResolverSeesModuleConstants:
    """The matrices cite `SECURITY_KEYWORDS` and `NEGATIVE_SCENARIO_KEYWORDS`.

    `build_index` walks `tree.body` for functions and classes only, so resolving
    against it alone would report those as absent while they sit in plain sight —
    a false red, which is worse than no check because it teaches the reader to
    disbelieve the checker.
    """

    @pytest.mark.parametrize(
        "name",
        [
            pytest.param("MATRICES", id="module_constant"),
            pytest.param("DECLARED_SENAR_VERSION", id="constant_in_another_module"),
            pytest.param("parse_claims", id="function"),
            pytest.param("Claim", id="class"),
        ],
    )
    def test_every_kind_of_definition_is_a_defined_name(self, name):
        assert name in defined_names(_REPO)

    def test_a_name_nobody_defined_is_absent(self):
        assert "definitely_not_a_symbol_in_this_tree" not in defined_names(_REPO)
