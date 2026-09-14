"""§8.4.1 coverage completeness — the control, and the false positive it must not have.

The criterion this file exists to satisfy is unusual and worth stating up front:
ADR-023 §4 rejects the obvious implementation. A blacklist of adjectives
("key", "critical", "core") is wrong in BOTH directions — the same words are
legitimate when they name a property OF the subject and illegitimate when they
narrow what must be described — so a check built that way fails the criterion
EVEN IF it catches every case we have today.

`test_an_evaluative_adjective_naming_a_property_stays_green` is therefore not a
nice-to-have edge case. A red on that input would reproduce precisely the
mistake ADR-023 threw out, and would mean this task failed rather than passed.
"""

from __future__ import annotations

import json
import os

import pytest
from conftest import DORMANT_WITHOUT_LIVE_DB

import spec_completeness as sc
from spec_completeness import Finding, audit, check_body, reach

# A body that covers every member of its subject AND is thick with evaluative
# vocabulary. Each adjective names a PROPERTY of an element; none removes one.
GUARDED = [
    "qg0.scope_hard_gate",
    "risk.l3_block_on_high",
    "task_done.auto_verify",
    "gates.*.enabled",
]

OPINIONATED_BUT_COMPLETE = """
# Guarded keys

The single most critical of these is `task_done.auto_verify`: it is the key
switch, because turning it on bypasses the signed receipt entirely. The core
protection against scope creep is `qg0.scope_hard_gate`. `risk.l3_block_on_high`
matters mainly for under-evidenced closures, and is the least significant of the
four in day-to-day work. Finally `gates.<name>.enabled` is guarded per gate —
a largely mechanical case, but a mandatory one.
"""

NARROWED = """
# Guarded keys

We describe the key ones. `task_done.auto_verify` bypasses the signed receipt,
and `qg0.scope_hard_gate` blocks edits outside a declared scope. The remaining
guards are mechanical and are not described here.
"""


def _fake_specs(*slugs):
    return [{"slug": s, "content_ref": "docs/whatever.md"} for s in slugs]


def _reg(slug, enumerator="fake", body="body.md", subject="the four guarded keys"):
    return {slug: {"enumerator": enumerator, "body": body, "subject": subject}}


# --- AC3: the false positive that would mean failure ------------------------


def test_an_evaluative_adjective_naming_a_property_stays_green():
    """THE criterion of this task. "most critical", "key switch", "core",
    "least significant", "largely mechanical" — every one of them names a
    property of an element, and every element is still described. Green."""
    assert check_body(GUARDED, OPINIONATED_BUT_COMPLETE) == []


def test_measure_phrases_do_not_make_a_complete_body_red():
    """ "the least significant of the four" is a measure phrase, and a body is
    entitled to rank what it describes. Ranking is not narrowing."""
    assert "least significant" in OPINIONATED_BUT_COMPLETE
    assert check_body(GUARDED, OPINIONATED_BUT_COMPLETE) == []


def test_the_check_reads_no_vocabulary_at_all():
    """Stated as its own assertion because AC2 forbids the implementation, not
    just its symptoms: stripping every evaluative word from a COMPLETE body
    changes nothing, and adding them to a NARROWED one changes nothing either."""
    plain = OPINIONATED_BUT_COMPLETE
    for word in ("critical", "key", "core", "least significant", "largely mechanical"):
        plain = plain.replace(word, "")
    assert check_body(GUARDED, plain) == []
    assert check_body(GUARDED, NARROWED + " critical key core") == [
        "risk.l3_block_on_high",
        "gates.*.enabled",
    ]


# --- AC1: a concrete SPEC and a concrete omission ---------------------------


def test_narrowing_a_body_to_a_subset_names_every_missing_element():
    report = audit(
        specs=_fake_specs("s"),
        registry=_reg("s"),
        repo_root="/nowhere",
        enumerators={"fake": lambda: GUARDED},
    )
    # The body cannot be read from /nowhere, so drive check_body directly for the
    # element-level claim and use the report for the shape of the finding.
    missing = check_body(GUARDED, NARROWED)
    assert missing == ["risk.l3_block_on_high", "gates.*.enabled"]
    assert report.findings and report.findings[0].spec == "s"


def test_the_finding_names_the_spec_and_the_element_not_a_percentage(tmp_path):
    body = tmp_path / "body.md"
    body.write_text(NARROWED, encoding="utf-8")
    report = audit(
        specs=_fake_specs("sec-x"),
        registry=_reg("sec-x", body="body.md"),
        repo_root=str(tmp_path),
        enumerators={"fake": lambda: GUARDED},
    )
    assert not report.ok
    assert {f.kind for f in report.findings} == {"OMISSION"}
    assert {f.spec for f in report.findings} == {"sec-x"}
    rendered = report.render()
    assert "risk.l3_block_on_high" in rendered
    assert "gates.*.enabled" in rendered
    assert "%" not in rendered, "the criterion asks for the missing element, not its cardinality"


def test_a_complete_body_is_reported_complete(tmp_path):
    body = tmp_path / "body.md"
    body.write_text(OPINIONATED_BUT_COMPLETE, encoding="utf-8")
    report = audit(
        specs=_fake_specs("sec-x"),
        registry=_reg("sec-x", body="body.md"),
        repo_root=str(tmp_path),
        enumerators={"fake": lambda: GUARDED},
    )
    assert report.ok, report.render()
    assert report.complete == ["sec-x"]


# --- Family keys: a subject element, spelled however prose spells it --------


@pytest.mark.parametrize(
    "spelling",
    ["gates.<name>.enabled", "gates.<имя>.enabled", "gates.mypy.enabled", "gates.x.enabled"],
)
def test_a_family_key_is_covered_however_the_placeholder_is_written(spelling):
    """`gates.*.enabled` is ONE guard covering every gate. Demanding the literal
    asterisk would have failed four keys the real body describes perfectly well —
    a check about typography, where the criterion is about the subject."""
    assert check_body(["gates.*.enabled"], f"see {spelling} for details") == []


@pytest.mark.parametrize(
    "prose",
    [
        "gates are enabled by default",
        "gates.enabled",
        "the gates section and the enabled switch",
        "gates. Some are enabled.",
    ],
)
def test_the_wildcard_cannot_swallow_its_way_across_a_sentence(prose):
    """The looser matcher must not become a free pass. A segment excludes
    whitespace, dots and backticks precisely so an unrelated mention cannot be
    scored as coverage."""
    assert check_body(["gates.*.enabled"], prose) == ["gates.*.enabled"]


# --- Not passing is not the same as passing ---------------------------------


def test_a_spec_with_no_entry_is_unchecked_and_named_not_passed():
    """The absence of a negative finding is not a positive verdict
    (SENAR 1.4 §8.6(e))."""
    report = audit(specs=_fake_specs("orphan"), registry={}, repo_root="/nowhere")
    assert [f.kind for f in report.findings] == ["UNCHECKED"]
    assert report.findings[0].spec == "orphan"
    assert report.complete == []


@pytest.mark.parametrize(
    "ref,because",
    [
        pytest.param("decisions#109", "points at a record", id="record_not_a_file"),
        pytest.param("docs/gone.md", "names no file", id="missing_file"),
        pytest.param("", "declares no content_ref", id="no_ref"),
    ],
)
def test_a_body_the_control_cannot_read_is_named_not_scored_green(ref, because):
    report = audit(
        specs=[{"slug": "s", "content_ref": ref}],
        registry=_reg("s", body=ref),
        repo_root="/nowhere",
        enumerators={"fake": lambda: GUARDED},
    )
    assert [f.kind for f in report.findings] == ["UNREADABLE_BODY"]
    assert because in report.findings[0].detail


def test_an_entry_naming_an_absent_enumerator_is_reported():
    report = audit(specs=_fake_specs("s"), registry=_reg("s", enumerator="nope"), enumerators={})
    assert [f.kind for f in report.findings] == ["NO_ENUMERATOR"]


def test_an_entry_for_a_spec_the_project_does_not_have_is_reported():
    report = audit(specs=[], registry=_reg("ghost"), repo_root="/nowhere")
    assert [f.kind for f in report.findings] == ["STALE_ENTRY"]
    assert report.findings[0].spec == "ghost"


def test_an_unreadable_registry_makes_everything_unchecked_not_green(tmp_path, monkeypatch):
    """Direction of degradation: broken registry must be loud, never quiet."""
    bad = tmp_path / "tausik" / "spec_coverage.json"
    bad.parent.mkdir(parents=True)
    bad.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(sc, "registry_path", lambda start=None: str(bad))
    assert sc.load_registry() == {}


# --- AC4: reach stated as a number, honestly --------------------------------


def test_reach_is_now_eleven_of_eleven_and_names_no_absentee():
    """Reach was 9 of 11 until v49 admitted SPEC-TEST and SPEC-DOC.

    Reporting "all types covered" over a nine-type list would have been the
    exact narrowing §8.4.1 forbids — the convenient subset called the whole.
    That is why the denominator is an independent transcription of the standard
    and not len(SPEC_TYPES): now that the two sides agree, a derived denominator
    would make the NEXT shortfall arithmetically invisible.
    """
    r = reach()
    assert r["types_known"] == 11
    assert r["types_in_standard"] == 11
    assert r["absent"] == []
    assert "11 of 11" in r["note"]
    # The note may no longer cite the task that closed the gap as though the
    # gap were still open.
    assert "spec-closed-list-is-nine-while-the-standard-has-eleven" not in r["note"]


def test_reach_still_names_the_shortfall_when_there_is_one():
    """The counter-control: with the gap closed, every assertion above is
    satisfied by a reach() that has forgotten how to report a gap at all."""
    r = reach(known_types=("ARCH", "API"))
    assert r["types_known"] == 2
    assert r["absent"] == [t for t in sc.STANDARD_SPEC_TYPES if t not in ("ARCH", "API")]
    assert "2 of 11" in r["note"]
    assert "SPEC-TEST" in r["note"] and "SPEC-DOC" in r["note"]


def test_reach_reports_full_coverage_only_when_all_eleven_types_exist():
    """The number is computed, not asserted: widening the closed list is what
    makes this control's reach complete, and nothing else."""
    r = reach(known_types=sc.STANDARD_SPEC_TYPES)
    assert r["absent"] == []
    assert "11 of 11" in r["note"]


# --- The live repository ----------------------------------------------------

#: This control's subject is named in its own test: the LIVE repository. SPEC
#: bodies live in the project database, which `.gitignore` keeps out of every
#: clone, so in a bare checkout `audit()` reports an empty world and the pin
#: below compares against nothing. It used to FAIL there rather than stand down
#: — measured in a clean `git worktree` (four-tests-fail-in-a-bare-checkout).
PROJECT_DB = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".tausik", "tausik.db"
)


@pytest.mark.skipif(
    not os.path.isfile(PROJECT_DB),
    reason=DORMANT_WITHOUT_LIVE_DB,
)
def test_the_live_repository_reports_exactly_the_gap_it_has():
    """Pinned rather than asserted green, because the control's first real
    finding is a real one: `renar-adoption` has no entry naming the enumerable
    subject its body owes a description of. Two SPEC bodies are complete.

    `at-generation-procedure` (at-acceptance-tests-derived-by-an-isolated-agent,
    PROC) joined the same UNCHECKED state for the same honest reason: a
    step-by-step procedure has no naturally enumerable subject the way a SPEC
    describing N guarded config keys does, so no spec_coverage.json entry was
    invented to force one — see spec_completeness.py's own module docstring on
    why UNCHECKED beats a fabricated enumerator.
    """
    report = audit()
    assert report.complete == ["sec-config-trust-tiers", "team-state-in-git-format"]
    assert [(f.spec, f.kind) for f in report.findings] == [
        ("at-generation-procedure", "UNCHECKED"),
        ("renar-adoption", "UNCHECKED"),
    ]


def test_the_committed_registry_is_valid_json_with_a_reach_note():
    path = sc.registry_path()
    assert path, "no committed tausik/spec_coverage.json found"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    assert "_reach" in data and "9 of the standard's 11" in data["_reach"]
    for slug, entry in sc.load_registry().items():
        assert entry.get("subject"), f"{slug}: no subject named"
        assert entry.get("enumerator") in sc.ENUMERATORS, f"{slug}: unknown enumerator"


def test_finding_describes_itself_with_kind_spec_and_detail():
    assert Finding("s", "OMISSION", "why").describe() == "OMISSION s: why"
