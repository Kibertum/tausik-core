"""Does anything notice when the STANDARD moves? Now something does.

Both gaps this epic exists for — ADR-011 withdrawing the ADAPT client signature,
ADR-013 widening the SPEC type list — were found by reading, months late, while
the CLI published a withdrawn edition. Every check below is a corpus that has
moved in one specific way; the green cases pin that an agreeing corpus, a
proposed ADR and a missing checkout each produce silence for a DIFFERENT and
stated reason.

The corpus fixtures are synthetic and tiny on purpose: a test that can only run
against the real sibling checkout has no expressible red branch (memory #484),
and CI has no such checkout at all.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import renar_standard_drift as std  # noqa: E402
from service_adapts import ADAPT_STATUSES, FINDING_CATEGORIES  # noqa: E402
from service_specs import SPEC_TYPES  # noqa: E402

OUR_VERSION = "1.0"


def _corpus(tmp_path, *, version=OUR_VERSION, spec_types=None, categories=None, statuses=None):
    """A corpus that agrees with us, unless a caller moves one thing."""
    spec_types = list(SPEC_TYPES) if spec_types is None else list(spec_types)
    categories = list(FINDING_CATEGORIES) if categories is None else list(categories)
    statuses = list(ADAPT_STATUSES) if statuses is None else list(statuses)
    chapters = tmp_path / "standard"
    chapters.mkdir(parents=True, exist_ok=True)
    # The corpus prefixes ONLY the first member — "`SPEC-ARCH`, `API`, `DATA`,
    # …" — and the fixture must carry that shape or the normalisation branch is
    # never exercised. Written flat at first, and a mutation proved the cost:
    # removing the normalisation left every synthetic case green, because the
    # synthetic corpus was the one shape the real one never uses.
    listed = ", ".join(f"`SPEC-{t}`" if i == 0 else f"`{t}`" for i, t in enumerate(spec_types))
    (chapters / std.CH_SPEC).write_text(
        f"> **Часть RENAR Standard v{version}**\n\n"
        f"Типов спецификаций ровно {len(spec_types)}, и список закрыт: {listed} — "
        "новый тип вводится только через формальную процедуру.\n",
        encoding="utf-8",
    )
    cats = ", ".join(f"`{c}`" for c in categories)
    (chapters / std.CH_ADAPT).write_text(
        f"1. **Backward finding обнаружена.** Рецензент выявил запись по одной из "
        f"{len(categories)} категорий §7.4.4 ({cats}) с корнем в языке ТЗ.\n\n"
        "```yaml\n"
        f"status: {' | '.join(statuses)}\n"
        "```\n",
        encoding="utf-8",
    )
    (chapters / std.CH_CONFORMANCE).write_text(
        f"> **Часть RENAR Standard v{version}**\n\n## 13.3 Обязательные положения\n",
        encoding="utf-8",
    )
    return str(tmp_path)


def _adr(tmp_path, number: int, status: str):
    d = tmp_path / "research" / "decisions"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"ADR-{number:03d}-synthetic.md").write_text(
        f"---\nadr: {number:03d}\ntitle: synthetic\nstatus: {status}\n---\n\nBody.\n",
        encoding="utf-8",
    )


def _kinds(findings):
    return [f["kind"] for f in findings]


# --- the corpus we agree with -------------------------------------------------


def test_an_agreeing_corpus_is_silent(tmp_path):
    root = _corpus(tmp_path)
    assert std.detect_standard_drift(root, our_version=OUR_VERSION, check_adrs=False) == []


def test_the_lists_are_parsed_in_the_shapes_the_corpus_writes_them(tmp_path):
    """Two shapes, and reading only one was this module's first defect: §8.3 and
    §7.4.4 enumerate with backticks, §7.8.1 with a pipe-separated frontmatter
    example. A single shape silently returned nothing for the statuses."""
    root = _corpus(tmp_path)
    spec = std._chapter(root, std.CH_SPEC)
    adapt = std._chapter(root, std.CH_ADAPT)
    assert std._normalise_spec_types(
        std.closed_list_from(spec, "Типов спецификаций ровно") or ()
    ) == tuple(SPEC_TYPES)
    assert std.closed_list_from(adapt, "категорий §7.4.4") == tuple(FINDING_CATEGORIES)
    assert std.closed_list_from(adapt, "status: draft", std.pipe_separated) == tuple(ADAPT_STATUSES)


# --- the corpus moved ---------------------------------------------------------


def test_a_twelfth_spec_type_is_a_finding(tmp_path):
    """ADR-013 widened this list once already, and nothing noticed for months."""
    root = _corpus(tmp_path, spec_types=[*SPEC_TYPES, "PLAN"])
    findings = std.detect_standard_drift(root, our_version=OUR_VERSION, check_adrs=False)
    assert _kinds(findings) == ["spec-types-drift"]
    assert "'PLAN'" in findings[0]["message"]
    assert "§8.3" in findings[0]["ref"]


def test_a_category_the_standard_dropped_is_a_finding(tmp_path):
    root = _corpus(tmp_path, categories=[c for c in FINDING_CATEGORIES if c != "scope"])
    findings = std.detect_standard_drift(root, our_version=OUR_VERSION, check_adrs=False)
    assert _kinds(findings) == ["finding-categories-drift"]
    assert "'scope'" in findings[0]["message"], "the message must name what moved"


def test_a_status_the_standard_renamed_is_a_finding(tmp_path):
    root = _corpus(
        tmp_path, statuses=[("signed" if s == "approved" else s) for s in ADAPT_STATUSES]
    )
    findings = std.detect_standard_drift(root, our_version=OUR_VERSION, check_adrs=False)
    assert _kinds(findings) == ["adapt-statuses-drift"]
    assert "'signed'" in findings[0]["message"] and "'approved'" in findings[0]["message"]


def test_a_newer_edition_is_a_finding(tmp_path):
    """§13.4.3 makes a corpus minor version a re-assessment trigger."""
    root = _corpus(tmp_path, version="1.1")
    findings = std.detect_standard_drift(root, our_version=OUR_VERSION, check_adrs=False)
    assert _kinds(findings) == ["version-behind"]
    assert "v1.1" in findings[0]["message"] and "1.0" in findings[0]["message"]


# --- accepted is not proposed --------------------------------------------------


def test_an_accepted_adr_nobody_mentions_is_a_finding(tmp_path):
    root = _corpus(tmp_path)
    _adr(tmp_path, 777, "accepted")
    findings = std.detect_standard_drift(root, our_version=OUR_VERSION, repo_mentions=set())
    assert _kinds(findings) == ["accepted-adr-unreckoned"]
    assert findings[0]["ref"] == "ADR-777"


def test_an_accepted_adr_we_have_read_is_silent(tmp_path):
    root = _corpus(tmp_path)
    _adr(tmp_path, 777, "accepted")
    assert std.detect_standard_drift(root, our_version=OUR_VERSION, repo_mentions={"ADR-777"}) == []


@pytest.mark.parametrize("status", ["proposed", "draft", "superseded", "rejected"])
def test_a_proposed_adr_is_never_a_finding(tmp_path, status):
    """THE CONSTRAINT THE TASK STATES AS A NEGATIVE: a detector that demanded
    implementation of every proposal would redden permanently and be switched
    off — which is worse than not having it."""
    root = _corpus(tmp_path)
    _adr(tmp_path, 778, status)
    assert std.detect_standard_drift(root, our_version=OUR_VERSION, repo_mentions=set()) == []


def test_accepted_pending_still_counts(tmp_path):
    """ADR-011 — one of the two we missed — is `accepted-pending-adr-012`."""
    root = _corpus(tmp_path)
    _adr(tmp_path, 779, "accepted-pending-adr-012")
    findings = std.detect_standard_drift(root, our_version=OUR_VERSION, repo_mentions=set())
    assert _kinds(findings) == ["accepted-adr-unreckoned"]


def test_not_being_able_to_ask_the_repo_is_stated_not_assumed(tmp_path):
    """`None` mentions is "we could not look", and must not read as "nothing to find"."""
    root = _corpus(tmp_path)
    _adr(tmp_path, 780, "accepted")
    findings = std.detect_standard_drift(root, our_version=OUR_VERSION, repo_mentions=None)
    assert _kinds(findings) == ["repo-unreadable"]


# --- three states --------------------------------------------------------------


def test_no_corpus_is_not_checked_and_says_so(monkeypatch):
    """A machine without the sibling checkout — which is every consumer, and CI.

    Absence is simulated rather than assumed: `root=None` means "ask the
    config", and on THIS machine the config names a real corpus, so the first
    draft of this test measured the live checkout while claiming to measure its
    absence.
    """
    monkeypatch.setattr(std, "corpus_root", lambda cfg=None: None)
    assert std.detect_standard_drift(None, our_version=OUR_VERSION) == []
    assert "NOT CHECKED" in std.corpus_status(None)
    assert std.CORPUS_CONFIG_KEY in std.corpus_status(None)


def test_a_configured_path_that_is_not_there_is_no_corpus(tmp_path):
    assert std.corpus_root({std.CORPUS_CONFIG_KEY: str(tmp_path / "nope")}) is None
    assert std.corpus_root({}) is None
    assert std.corpus_root({std.CORPUS_CONFIG_KEY: str(tmp_path)}) == str(tmp_path)


def test_a_chapter_that_will_not_parse_is_a_finding_not_a_silence(tmp_path):
    """NEGATIVE SCENARIO: a reworded chapter must be LOUD.

    A detector that reads nothing and reports nothing is indistinguishable from
    one that read everything and found nothing — the degeneracy ADR-021 names,
    and the exact way this project stayed months behind.
    """
    root = _corpus(tmp_path)
    (tmp_path / "standard" / std.CH_ADAPT).write_text("Полностью переписанная глава.\n", "utf-8")
    findings = std.detect_standard_drift(root, our_version=OUR_VERSION, check_adrs=False)
    assert _kinds(findings) == ["corpus-unreadable", "corpus-unreadable"]
    assert all("§7" in f["ref"] for f in findings)


def test_a_missing_chapter_is_a_finding(tmp_path):
    root = _corpus(tmp_path)
    (tmp_path / "standard" / std.CH_SPEC).unlink()
    findings = std.detect_standard_drift(root, our_version=OUR_VERSION, check_adrs=False)
    assert "corpus-unreadable" in _kinds(findings)


def test_a_corpus_without_a_version_banner_is_a_finding(tmp_path):
    root = _corpus(tmp_path)
    for name in (std.CH_CONFORMANCE, std.CH_SPEC):
        path = tmp_path / "standard" / name
        path.write_text(
            path.read_text(encoding="utf-8").replace("RENAR Standard v", "RS "), "utf-8"
        )
    findings = std.detect_standard_drift(root, our_version=OUR_VERSION, check_adrs=False)
    assert "corpus-unreadable" in _kinds(findings)


def test_a_partly_written_status_line_is_unreadable_not_a_shorter_list(tmp_path):
    """A part that is not a plain name makes the WHOLE line unreadable: a
    partial parse published as the standard's list is the failure this module
    exists to avoid."""
    assert std.pipe_separated("status: draft | review | (asked)") == ()
    assert std.pipe_separated("status: draft") == (), "one value is not an enumeration"
    assert std.pipe_separated("no colon here | at all") == ()


# --- the live corpus, when this machine has one ---------------------------------


def test_the_live_corpus_agrees_with_us():
    """Read-only against the real checkout; skipped where there is none."""
    root = std.corpus_root()
    if root is None:
        pytest.skip("no local standard corpus configured on this machine")
    findings = std.detect_standard_drift(root, check_adrs=False)
    assert findings == [], findings
