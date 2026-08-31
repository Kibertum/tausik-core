"""§13.3.3 measurer: it must go RED on the violations it exists to catch.

The clause used to be confirmed by ``adapts > 0``. Two families of assertion
here, and both are needed:

* RED — each of the four violations live in this substrate reddens its OWN
  named sub-check, on a database built by the REAL migrations (so "specs has no
  provenance column" is the actual schema, not a fixture's opinion).
* GREEN — each sub-check goes green on a state where it must. Without that half
  an evaluator that returns False unconditionally is indistinguishable from a
  working one, and the fix would be the same degeneracy facing the other way.

The green half runs against the pure evaluator, which takes declared facts,
because two of the required states (``adapts.status = 'approved'``, a
``source`` column on ``specs``) the current schema physically cannot hold —
that unreachability is itself part of the finding, tracked by
adapt-status-enum-diverged-from-the-standards-closed-list and
our-only-spec-is-derived-without-either-allowed-source-field. Where the schema
DOES admit the green state, it is asserted through ``collect_state`` against a
real database, so the reader is proven to map reality and not only the
evaluator's dataclass.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from renar_clause_reactive_adapt import (  # noqa: E402
    BACKWARD_FINDING_CATEGORIES,
    ReactiveAdaptState,
    assess,
    collect_state,
    evaluate,
)


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "c333.db")))
    yield s
    s.be.close()


@pytest.fixture
def live_shape(svc):
    """The four violations this project actually has, on the real schema.

    One ADAPT whose ТЗ ref is a decision record, carrying a backward finding,
    left draft and unsigned; SPECs that exist and therefore owe provenance.
    """
    svc.adapt_create("adapt-renar-adoption", "RENAR adoption", "decisions#109")
    svc.adapt_finding("adapt-renar-adoption", "gap", "TZ is silent on drift classes")
    svc.spec_add("renar-adoption", "ARCH", "Adoption", "v1", status="active")
    svc.spec_add("team-state", "DATA", "Team state", "v1", status="active")
    return svc


def _by_name(checks):
    return {c.name: c for c in checks}


# --- AC-2: red on each of the four live violations --------------------------


def test_adversarial_review_class_absent_is_red(live_shape):
    """(a) AR does not exist as a class → no derivation carries a verdict."""
    c = _by_name(evaluate(collect_state(live_shape.be._conn)))["adversarial-review-issued"]
    assert c.ok is False
    assert "AR does not exist as an artifact class" in c.evidence
    # The reviews table must not be counted in our favour: it reviews task
    # closures and code, not ТЗ (decision #291).
    assert "reviews table is NOT counted" in c.evidence


def test_draft_adapt_with_findings_is_red(live_shape):
    """(b) findings present → ADAPT must be 'approved'; ours is draft."""
    c = _by_name(evaluate(collect_state(live_shape.be._conn)))["adapt-approved-when-findings"]
    assert c.ok is False
    assert "adapt-renar-adoption=draft" in c.evidence
    # Stronger than a wrong row value: the schema cannot hold the right one.
    assert "'approved' is not among them" in c.evidence


def test_unsigned_adapt_with_findings_is_red(live_shape):
    """(c) findings present → Architect signature required; we have none."""
    c = _by_name(evaluate(collect_state(live_shape.be._conn)))["architect-signature-when-findings"]
    assert c.ok is False
    assert "no Architect signature" in c.evidence


def test_specs_without_provenance_column_is_red(live_shape):
    """(d) SPECs exist and the specs table has no provenance column at all."""
    c = _by_name(evaluate(collect_state(live_shape.be._conn)))["spec-provenance-source"]
    assert c.ok is False
    assert "NO provenance column at all" in c.evidence
    assert "2 live SPEC(s)" in c.evidence


def test_clause_is_unmet_and_names_all_four(live_shape):
    verdict = assess(live_shape.be._conn)
    assert verdict["confirmed"] is False
    assert len(verdict["subchecks"]) == 4
    assert all(not s["ok"] for s in verdict["subchecks"])
    assert "4 of 4" in verdict["evidence"]


def test_the_row_count_measurer_would_have_confirmed_this(live_shape):
    """The defect, pinned: `adapts > 0` is true in exactly this state.

    Without this assertion the suite would pass just as happily against the old
    degenerate measurer, and the regression it guards would be invisible.
    """
    conn = live_shape.be._conn
    adapts = conn.execute("SELECT COUNT(*) FROM adapts").fetchone()[0]
    assert adapts > 0, "the old measurer's input"
    assert assess(conn)["confirmed"] is False, "the new measurer disagrees with the count"


# --- AC-4: green control per sub-check (the evaluator is not constant-false) -


def _conformant_state() -> ReactiveAdaptState:
    """A state in which every §13.3.3 sub-check MUST go green."""
    return ReactiveAdaptState(
        ar_table="adversarial_reviews",
        ar_issued_count=1,
        adapts_with_findings={"ad1": "approved"},
        adapt_signature_roles={"ad1": ("architect",)},
        spec_count=3,
        spec_provenance_columns=("source_adapt", "source_tz_section"),
        specs_without_provenance=0,
        adapt_status_domain=("draft", "approved", "signed", "superseded"),
    )


def test_conformant_state_confirms_the_clause():
    checks = evaluate(_conformant_state())
    assert all(c.ok for c in checks), [c.name for c in checks if not c.ok]


@pytest.mark.parametrize(
    ("name", "mutation"),
    [
        ("adversarial-review-issued", {"ar_table": None}),
        ("adversarial-review-issued", {"ar_issued_count": 0}),
        ("adapt-approved-when-findings", {"adapts_with_findings": {"ad1": "draft"}}),
        ("architect-signature-when-findings", {"adapt_signature_roles": {"ad1": ()}}),
        ("architect-signature-when-findings", {"adapt_signature_roles": {"ad1": ("client",)}}),
        ("spec-provenance-source", {"spec_provenance_columns": ()}),
        ("spec-provenance-source", {"specs_without_provenance": 1}),
    ],
)
def test_each_subcheck_reddens_on_its_own_violation(name, mutation):
    """One violation at a time: the named check reds, the others stay green."""
    from dataclasses import replace

    checks = _by_name(evaluate(replace(_conformant_state(), **mutation)))
    assert checks[name].ok is False, f"{name} stayed green on {mutation}"
    for other, c in checks.items():
        if other != name:
            assert c.ok is True, f"{other} reddened on a violation of {name}"


def test_findings_free_adapt_does_not_owe_the_findings_present_branch():
    """No backward finding → that branch has no subject (§13.3.3 p.77 vs p.78).

    Vacuity is legitimate HERE, unlike for SPEC provenance, and it is stated in
    the evidence rather than left to be read out of a bare `true`.
    """
    st = ReactiveAdaptState(
        ar_table="adversarial_reviews",
        ar_issued_count=1,
        adapts_with_findings={},
        spec_count=0,
    )
    checks = _by_name(evaluate(st))
    assert checks["adapt-approved-when-findings"].ok is True
    assert "no subject" in checks["adapt-approved-when-findings"].evidence
    assert checks["architect-signature-when-findings"].ok is True


# --- the reader maps reality, not only the dataclass ------------------------


def test_collect_state_sees_a_real_issued_ar_table(live_shape):
    """Green through collect_state where the schema admits it."""
    conn = live_shape.be._conn
    conn.execute(
        "CREATE TABLE adversarial_reviews (id INTEGER PRIMARY KEY, tz_ref TEXT, status TEXT)"
    )
    conn.execute("INSERT INTO adversarial_reviews (tz_ref, status) VALUES ('TZ-1','issued')")
    conn.commit()
    c = _by_name(evaluate(collect_state(conn)))["adversarial-review-issued"]
    assert c.ok is True
    assert "1 AR record(s) in status 'issued'" in c.evidence


def test_collect_state_reddens_on_a_draft_only_ar_table(live_shape):
    """The table existing is not the verdict being issued (§7.4.6)."""
    conn = live_shape.be._conn
    conn.execute(
        "CREATE TABLE adversarial_reviews (id INTEGER PRIMARY KEY, tz_ref TEXT, status TEXT)"
    )
    conn.execute("INSERT INTO adversarial_reviews (tz_ref, status) VALUES ('TZ-1','draft')")
    conn.commit()
    c = _by_name(evaluate(collect_state(conn)))["adversarial-review-issued"]
    assert c.ok is False
    assert "zero AR in status 'issued'" in c.evidence


def test_collect_state_sees_a_real_provenance_column(live_shape):
    """A provenance column added for real greens the check; a null one reds it."""
    conn = live_shape.be._conn
    conn.execute("ALTER TABLE specs ADD COLUMN source_adapt TEXT")
    conn.commit()
    c = _by_name(evaluate(collect_state(conn)))["spec-provenance-source"]
    assert c.ok is False, "column present but every value null is still bare"
    assert "carry none of" in c.evidence

    conn.execute("UPDATE specs SET source_adapt='adapt-renar-adoption'")
    conn.commit()
    c = _by_name(evaluate(collect_state(conn)))["spec-provenance-source"]
    assert c.ok is True
    assert "all 2 SPEC(s) carry a provenance source" in c.evidence


def test_collect_state_sees_a_real_architect_signature(live_shape):
    """Signature recorded directly: adapt_sign('architect') needs the ed25519 key."""
    conn = live_shape.be._conn
    conn.execute(
        "INSERT INTO adapt_signatures (adapt_slug, role, signed_by, signed_at) "
        "VALUES ('adapt-renar-adoption','architect','architect-test','2026-08-31T00:00:00Z')"
    )
    conn.commit()
    c = _by_name(evaluate(collect_state(conn)))["architect-signature-when-findings"]
    assert c.ok is True


def test_empty_substrate_still_reds_on_the_review_obligation(svc):
    """No artifacts at all: the AR obligation is NOT vacuous (§13.3.3 p.73).

    Every ТЗ owes an adversarial review; nothing about an empty requirements
    store makes that duty disappear, so an empty store must not read as green.
    """
    checks = _by_name(evaluate(collect_state(svc.be._conn)))
    assert checks["adversarial-review-issued"].ok is False
    assert assess(svc.be._conn)["confirmed"] is False


# --- the closed list is the standard's, not ours ----------------------------


def test_backward_finding_categories_match_the_standards_closed_list():
    """§7.4.4 closes the list at seven; cite the literal, not our constant.

    Memory #474: a test that compares a field with the constant that produced it
    is a tautology. The seven names below are transcribed from the standard.
    """
    assert set(BACKWARD_FINDING_CATEGORIES) == {
        "contradiction",
        "gap",
        "hidden-assumption",
        "feasibility",
        "regulatory",
        "terminology",
        "scope",
    }
    assert len(BACKWARD_FINDING_CATEGORIES) == 7


def test_every_closed_category_puts_an_adapt_on_the_findings_branch(svc):
    """Not just 'gap': any of the seven triggers the branch (§7.4.1.1)."""
    for i, cat in enumerate(BACKWARD_FINDING_CATEGORIES):
        svc.adapt_create(f"ad{i}", f"Adapt {i}", "TZ-1")
        svc.adapt_finding(f"ad{i}", cat, f"finding of category {cat}")
    st = collect_state(svc.be._conn)
    assert len(st.adapts_with_findings) == 7, st.adapts_with_findings
