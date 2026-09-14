"""One claimed SENAR edition, checked everywhere it is claimed.

Measured in session #225 on the live tree: the product asserted THREE editions
at once — v1.3 in `CLAUDE.md` / `AGENTS.md` / `CONTRIBUTING.md` / `QWEN.md` and
the bootstrap templates that generate them, v1.5 in both compliance matrices
("compliance: 100%", "All gaps closed"), and no edition at all in either README.
A ninth site the filing never named, `docs/ru/agent-contract.md:193`, said v1.3
in a heading the first grep missed.

The interesting half is not the divergence — that is four string edits. It is
that three different things share one spelling, and a guard that cannot tell
them apart is either useless or gets switched off:

* a CLAIM about which edition TAUSIK implements,
* a CITATION locating a requirement in the edition that phrased it, and
* a RULE LOCATOR, where the number is a chapter and not an edition at all.

The first draft of the scanner read all 57 mentions on the surface as editions
and would have reddened on forty live lines. The cases below pin every class
against real strings from this tree, and pin the ambiguous fourth shape to a
visible refusal rather than a silent pass.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from conftest import DORMANT_ON_PUBLIC_SNAPSHOT, IS_PUBLIC_SNAPSHOT  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from doc_drift_common import _FOREIGN_VERSION_PREFIXES  # noqa: E402
from senar_version_claim import (  # noqa: E402
    CLAIM_SURFACE_FILES,
    DECLARED_SENAR_VERSION,
    EXEMPT_SURFACES,
    REQUIRED_CLAIM_FILES,
    check_claim_surface,
    classify,
    scan_claim_surface,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]

# This file reads the live tree, so the scoped-pytest gate cannot infer from a
# filename which edits should re-run it. The scope is the claim surface itself:
# an edit to any document that states the SENAR edition must bring this test
# back, which is the only way the guard keeps working after the shift that
# wrote it.
CROSSCUTTING_SCOPE = [
    "README.md",
    "README.ru.md",
    "CLAUDE.md",
    "AGENTS.md",
    "CONTRIBUTING.md",
    "QWEN.md",
    "docs/",
    "bootstrap/bootstrap_templates.py",
    "scripts/senar_version_claim.py",
    "scripts/doc_drift_common.py",
]


def _tree(tmp_path: Path, rel: str, body: str) -> Path:
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def _minimal_valid_tree(tmp_path: Path) -> None:
    """A tree where every required claim site states the declared edition."""
    for rel in REQUIRED_CLAIM_FILES:
        _tree(tmp_path, rel, f"# doc\n\nImplements SENAR v{DECLARED_SENAR_VERSION} Core.\n")


# --- the live tree agrees -----------------------------------------------------


class TestLiveTree:
    def test_claim_surface_agrees_on_one_edition(self):
        assert check_claim_surface(_REPO_ROOT) == []

    def test_every_claim_on_the_surface_names_the_declared_edition(self):
        claims = [m for m in scan_claim_surface(_REPO_ROOT) if m.kind == "claim"]
        assert claims, "the surface must carry claims; an empty scan would pass vacuously"
        divergent = [
            f"{m.path}:{m.line} -> v{m.version}"
            for m in claims
            if m.version != DECLARED_SENAR_VERSION
        ]
        assert divergent == []

    def test_both_readmes_actually_name_the_edition(self):
        """The measured defect was an ABSENCE, which no divergence check can see."""
        claimed_in = {m.path for m in scan_claim_surface(_REPO_ROOT) if m.kind == "claim"}
        for rel in ("README.md", "README.ru.md"):
            assert rel in claimed_in, f"{rel} names no SENAR edition"

    def test_surface_carries_a_real_citation_that_is_not_treated_as_a_claim(self):
        """A citation of another edition is legitimate and must not redden."""
        citations = [m for m in scan_claim_surface(_REPO_ROOT) if m.kind == "citation"]
        assert citations, "expected the live `SENAR 1.4 §8.6(j)` headings in docs/{en,ru}/cli.md"
        assert any(m.version != DECLARED_SENAR_VERSION for m in citations), (
            "the point of the citation class is that it may name a DIFFERENT edition; "
            "if every live citation happened to match the claim, this case proves nothing"
        )

    def test_surface_carries_rule_locators_and_none_of_them_is_read_as_an_edition(self):
        locators = [m for m in scan_claim_surface(_REPO_ROOT) if m.kind == "rule-locator"]
        assert len(locators) > 10, "`SENAR Rule 9.1` / `SENAR 9.2` are all over the docs"

    def test_nothing_on_the_surface_is_unclassified(self):
        unknown = [
            f"{m.path}:{m.line} SENAR {m.version}"
            for m in scan_claim_surface(_REPO_ROOT)
            if m.kind == "unclassified"
        ]
        assert unknown == []


# --- classification, one case per shape ---------------------------------------


class TestClassify:
    @pytest.mark.parametrize(
        "between,version,after,v_prefixed,expected",
        [
            (" ", "1.3", " Core](https://senar.tech)", True, "claim"),
            (" Compliance (", "1.3", " Core)", True, "claim"),
            (" ", "1.5", " Core — Compliance Matrix", True, "claim"),
            (" ", "1.3", "](https://senar.tech).", True, "claim"),
            # `Core` marks the edition even when the `v` was dropped.
            (" ", "1.3", " Core compliance", False, "claim"),
            (" ", "1.4", " §8.6(e): the absence of a", False, "citation"),
            (" Rule ", "9.1", ")", False, "rule-locator"),
            (" Section ", "5.1", ")", False, "rule-locator"),
            (" rules ", "9.2", "/9.3/9.5", False, "rule-locator"),
            (" Правило ", "9.2", ")", False, "rule-locator"),
            # A bare chapter number whose major cannot be an edition major.
            (" ", "9.2", "), capacity 200", False, "rule-locator"),
            (" ", "10.15", ")", False, "rule-locator"),
            # A rule noun wins over a v prefix: `SENAR Rule 1.4` names a chapter
            # whatever follows it.
            (" Rule ", "1.4", "", True, "rule-locator"),
            # Bare, with no v, no Core and no § — undecidable, so it is refused
            # rather than guessed.
            (" ", "1.4", ". The next sentence.", False, "unclassified"),
        ],
    )
    def test_shapes(self, between, version, after, v_prefixed, expected):
        assert classify(between, version, after, v_prefixed) == expected


# --- the guard actually reddens (mutation) ------------------------------------


class TestMutation:
    @pytest.mark.parametrize(
        "rel,body,needle",
        [
            # A claim naming another edition, in a file the globs pick up.
            ("docs/en/whatever.md", "TAUSIK implements SENAR v1.5 Core.\n", "v1.5"),
            # The filing's named failure mode: a NEW file naming a NEW edition.
            # A closed registry of known sites would sail straight past this.
            ("docs/ru/brand-new-page.md", "Реализует SENAR v2.0 Core.\n", "v2.0"),
            # The measured README defect was an ABSENCE, which no divergence
            # check can see: silence agrees with every edition at once.
            (
                "README.md",
                "TAUSIK is the reference implementation of SENAR.\n",
                "names no SENAR edition",
            ),
        ],
    )
    def test_a_bad_surface_reddens_and_names_the_file(self, tmp_path, rel, body, needle):
        _minimal_valid_tree(tmp_path)
        _tree(tmp_path, rel, body)
        problems = check_claim_surface(tmp_path)
        assert any(rel in p and needle in p for p in problems), problems

    def test_an_ambiguous_mention_reddens_with_a_remedy(self, tmp_path):
        _minimal_valid_tree(tmp_path)
        _tree(tmp_path, "docs/en/ambiguous.md", "Conformance to SENAR 1.4 is the target.\n")
        problems = check_claim_surface(tmp_path)
        hit = [p for p in problems if "ambiguous.md" in p]
        assert hit, problems
        assert "§" in hit[0], "the refusal must say how to disambiguate, not just refuse"

    @pytest.mark.parametrize(
        "rel,body",
        [
            # A citation of ANOTHER edition is legitimate: ~30 live lines say
            # `SENAR 1.4 §8.6(...)`. Reddening on those is how this guard would
            # get switched off in a week.
            (
                "docs/en/cli.md",
                "## A bypassed gate leaves a record (SENAR 1.4 §8.6(j))\n\n"
                "Blocks by default (SENAR 1.4 §8.6(e)): the absence of a negative finding\n",
            ),
            # Rule locators: the number is a chapter, not an edition. The first
            # draft read forty of these as version claims.
            (
                "docs/ru/sessions.md",
                "| лимит 180 активных минут (SENAR 9.2), счётчик чекпоинта (SENAR 9.3) |\n"
                "## Периодический аудит (SENAR Rule 9.5)\n"
                "- правила SENAR 9.2/9.3/9.5.\n",
            ),
            # Inside a fence it is sample output, not something the product says.
            ("docs/en/quickstart.md", "Example output:\n\n```\nImplements SENAR v1.5 Core\n```\n"),
        ],
    )
    def test_these_shapes_stay_green(self, tmp_path, rel, body):
        _minimal_valid_tree(tmp_path)
        _tree(tmp_path, rel, body)
        assert check_claim_surface(tmp_path) == []


# --- the registries are alive -------------------------------------------------


class TestRegistriesAreAlive:
    """Decision #335: a registry entry that matches nothing is a dead line."""

    @pytest.mark.parametrize("pattern,reason", EXEMPT_SURFACES)
    def test_every_exemption_matches_a_real_path(self, pattern, reason):
        if IS_PUBLIC_SNAPSHOT and pattern.startswith("tausik/"):
            pytest.skip(DORMANT_ON_PUBLIC_SNAPSHOT)
        matches = list(_REPO_ROOT.glob(pattern))
        assert matches, (
            f"exemption {pattern!r} matches no file in the tree; an exemption guarding "
            f"nothing reads as coverage. Reason on record: {reason}"
        )

    @pytest.mark.parametrize("pattern,reason", EXEMPT_SURFACES)
    def test_every_exemption_states_why(self, pattern, reason):
        assert len(reason.split()) >= 6, f"{pattern}: an exemption needs a reason, not a label"

    @pytest.mark.parametrize("rel", CLAIM_SURFACE_FILES)
    def test_every_named_surface_file_exists(self, rel):
        assert (_REPO_ROOT / rel).is_file(), f"{rel} is registered as a claim site but is absent"

    @pytest.mark.parametrize("rel", REQUIRED_CLAIM_FILES)
    def test_every_required_site_is_also_on_the_surface_or_globbed(self, rel):
        scanned = {m.path for m in scan_claim_surface(_REPO_ROOT)}
        assert (_REPO_ROOT / rel).is_file()
        assert rel in scanned, f"{rel} is required to claim but the scanner never reads it"

    def test_no_exemption_pattern_covers_the_claim_surface(self):
        """An exemption that swallowed a claim site would disable the guard silently."""
        exempt: set[str] = set()
        for pattern, _reason in EXEMPT_SURFACES:
            exempt |= {p.relative_to(_REPO_ROOT).as_posix() for p in _REPO_ROOT.glob(pattern)}
        overlap = exempt & {m.path for m in scan_claim_surface(_REPO_ROOT)}
        assert overlap == set(), f"exempted paths are also scanned as claim sites: {overlap}"


# --- the foreign-version exemption is untouched -------------------------------


class TestForeignVersionExemptionSurvives:
    """This guard is a SEPARATE mechanism, not an extension of the version-ref scan."""

    def test_senar_is_still_a_foreign_version_prefix(self):
        assert "SENAR" in _FOREIGN_VERSION_PREFIXES, (
            "SENAR sits in _FOREIGN_VERSION_PREFIXES on purpose: a foreign standard's "
            "version must never be compared against TAUSIK's own release number. "
            "Removing it would make the version-ref scanner demand that SENAR move "
            "with us — the opposite of what this task set out to build."
        )

    def test_this_module_does_not_reuse_the_tausik_version_machinery(self):
        source = (_REPO_ROOT / "scripts" / "senar_version_claim.py").read_text(encoding="utf-8")
        for forbidden in ("_VERSION_REF", "scan_version_refs", "tausik_version"):
            assert forbidden not in source, (
                f"{forbidden} would tie the SENAR claim to TAUSIK's own version timeline"
            )
