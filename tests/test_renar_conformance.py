"""v16r-conformance-yaml: honest RENAR-CONFORMANCE.yaml self-assessment.

Asserts (1) the manifest always carries every §13.4.2 mandatory field and
round-trips through YAML, (2) the level is derived from live DB state — an empty
artifact store yields pre-adoption (adapt-per-tz unmet, §13.4.3), and (3) the
level rises honestly as ADAPT/SPEC/delta artifacts appear.
"""

from __future__ import annotations

import os
import sys

import pytest

# PyYAML is an OPTIONAL RENAR dependency (see test_no_hard_yaml_import). A clean
# checkout without it should SKIP these tests, not error at collection.
yaml = pytest.importorskip("yaml")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
import renar_conformance  # noqa: E402
from renar_conformance import (  # noqa: E402
    MANDATORY_FIELDS,
    UNKNOWN_STATE_SENTINEL,
    current_level,
    format_status_line,
    generate,
    render_yaml,
)


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "conf.db")))
    yield s
    s.be.close()


@pytest.fixture
def in_scope(monkeypatch):
    """Lift the §1.5.4 scope exclusion.

    The ladder tests below assert the VALUE half of a conformance level — do the
    §11.4.3–§11.8.2 observable signals rise honestly as artifacts appear. That question only arises
    for a project the standard's scope of application admits, so they run with
    the exclusion lifted. The RIGHT half (may a level be claimed at all) is
    asserted separately in TestScopeApplicability.
    """
    monkeypatch.setattr(renar_conformance, "SCOPE_EXCLUSION", None)


def _gen(svc):
    return generate(svc.be._conn, "architect-test", "2026-06-14")


def _satisfy_clause_13_3_3(svc):
    """Bring the store to a state §13.3.3 actually admits.

    Before the clause had real sub-checks, a bare ``adapt_create`` confirmed it
    and every ladder test below rode on that. The ladder tests are about the
    §11.4.3-§11.8.2 observable signals, not about §13.3.3, so they say so here
    explicitly rather than depending on a measurer that could not go red.

    The state built is conformant, not stubbed: an adversarial review issued
    (§13.3.3 p.73), an ADAPT with no backward finding (so the "findings
    present" branch has no subject, p.78), and every SPEC carrying provenance
    (p.90). Two of those need DDL because the production schema cannot yet hold
    them - the subject of adapt-status-enum-diverged-from-the-standards-closed-list
    and our-only-spec-is-derived-without-either-allowed-source-field.
    """
    conn = svc.be._conn
    conn.execute(
        "CREATE TABLE IF NOT EXISTS adversarial_reviews "
        "(id INTEGER PRIMARY KEY, tz_ref TEXT, verdict TEXT, produces_adapt TEXT, status TEXT)"
    )
    conn.execute(
        "INSERT INTO adversarial_reviews (tz_ref, verdict, produces_adapt, status) "
        "VALUES ('TZ-1','no-findings','','issued')"
    )
    if "source_adapt" not in [r[1] for r in conn.execute("PRAGMA table_info(specs)")]:
        conn.execute("ALTER TABLE specs ADD COLUMN source_adapt TEXT")
    conn.execute("UPDATE specs SET source_adapt='ad1'")
    conn.commit()


# --- manifest shape ---------------------------------------------------------


def test_all_mandatory_fields_present(svc):
    manifest, _ = _gen(svc)
    for field in MANDATORY_FIELDS:
        assert field in manifest, f"missing mandatory §13.4.2 field {field!r}"
    assert set(manifest["quality-gates"]) == {"qg-0", "qg-1", "qg-2", "qg-3", "qg-4"}
    # §13.3.4 closes the list at ELEVEN (§8.3); the manifest published nine
    # until v49. The literal stays a literal here on purpose — deriving it
    # from SPEC_TYPES would make any future shortfall arithmetically invisible.
    assert len(manifest["spec-types-supported"]) == 11
    sc = manifest["substrate-capabilities"]
    for v in ("v1-immutable-history", "v6-author-timestamp"):
        assert v in sc


def test_yaml_round_trips(svc):
    manifest, text = _gen(svc)
    loaded = yaml.safe_load(text)
    # The header comment is dropped by the loader; body must equal the manifest.
    assert loaded == manifest
    assert loaded["renar-version"] == "1.1"


# --- honest level inference -------------------------------------------------


def test_empty_db_is_pre_adoption(svc, in_scope):
    """No artifacts → adapt-per-tz unmet → pre-adoption, not a declared level."""
    manifest, _ = _gen(svc)
    assert manifest["level"] is None
    assert manifest["pre-adoption"] is True
    ev = manifest["assessment-evidence"]
    assert ev["blocked-at"] == "mandatory-clauses"
    assert "adapt-per-tz" in ev["unmet-clauses"]
    assert manifest["mandatory-clauses-confirmed"]["adapt-per-tz"] is False
    # Machinery clauses are confirmed even with no data.
    assert manifest["mandatory-clauses-confirmed"]["spec-types-closed-list"] is True


def test_single_adapt_reaches_renar_1(svc, in_scope):
    """A §13.3.3-conformant store satisfies every mandatory clause → RENAR-1."""
    svc.adapt_create("ad1", "Adapt 1", "TZ-1")
    _satisfy_clause_13_3_3(svc)
    manifest, _ = _gen(svc)
    assert manifest["mandatory-clauses-confirmed"]["adapt-per-tz"] is True
    assert manifest["level"] == "RENAR-1"
    assert manifest["pre-adoption"] is False
    assert manifest["assessment-evidence"]["blocked-at"] == "RENAR-2"


def test_a_bare_adapt_no_longer_buys_renar_1(svc, in_scope):
    """The removed degeneracy, pinned at the ladder level.

    A single ADAPT row used to confirm §13.3.3 and lift the store to RENAR-1.
    It no longer does: the ADAPT's ТЗ never passed an adversarial review, so the
    clause is unmet and the store stays pre-adoption. Without this the suite
    would pass against the old count-based measurer.
    """
    svc.adapt_create("ad1", "Adapt 1", "TZ-1")
    manifest, _ = _gen(svc)
    assert manifest["mandatory-clauses-confirmed"]["adapt-per-tz"] is False
    assert manifest["level"] is None
    assert manifest["pre-adoption"] is True
    subchecks = manifest["assessment-evidence"]["clause-13-3-3"]
    assert [c["check"] for c in subchecks if not c["ok"]] == ["adversarial-review-issued"]


def test_draft_adapt_does_not_reach_renar_2(svc, in_scope):
    """A draft ADAPT is not an immutable TZ (§7.5) → tz_immutable stays False."""
    svc.adapt_create("ad1", "Adapt 1", "TZ-1")
    svc.adapt_delta("ad1", "ad1-d1", "Delta 1", "TZ-1", "TZ§1 superseded by delta")
    svc.spec_add("sp1", "API", "Spec 1", "v1", status="active")
    _satisfy_clause_13_3_3(svc)
    manifest, _ = _gen(svc)
    assert manifest["assessment-evidence"]["level-signals"]["tz_immutable"] is False
    assert manifest["level"] == "RENAR-1"  # blocked at RENAR-2 by tz_immutable


def test_signed_adapt_spec_delta_reach_renar_2(svc, in_scope):
    """Approved ADAPT (immutable TZ) + SPEC + delta → RENAR-2; RENAR-3 blocked."""
    svc.adapt_create("ad1", "Adapt 1", "TZ-1")
    svc.adapt_delta("ad1", "ad1-d1", "Delta 1", "TZ-1", "TZ§1 superseded by delta")
    svc.spec_add("sp1", "API", "Spec 1", "v1", status="active")
    # Simulate an approved (immutable) ADAPT without the ed25519 key ceremony.
    # §7.8.1 renamed our 'signed' to the standard's 'approved' in v50; the CHECK
    # now REJECTS 'signed', so this UPDATE also proves the list stayed closed.
    svc.be._conn.execute("UPDATE adapts SET status='approved' WHERE slug='ad1'")
    svc.be._conn.commit()
    _satisfy_clause_13_3_3(svc)
    manifest, _ = _gen(svc)
    assert manifest["level"] == "RENAR-2"
    assert manifest["assessment-evidence"]["blocked-at"] == "RENAR-3"
    sig = manifest["assessment-evidence"]["level-signals"]
    assert sig["tz_immutable"] is True
    assert sig["delta_tz_artifact"] is True
    assert sig["frontmatter_structured"] is True
    # RENAR-3 data signals genuinely absent in TAUSIK today.
    assert sig["coverage_autogen"] is False
    assert sig["verifies_version_pin"] is False


def test_level_target_advances_when_conformant(svc, in_scope):
    svc.adapt_create("ad1", "Adapt 1", "TZ-1")  # RENAR-1, pre_adoption False
    _satisfy_clause_13_3_3(svc)
    manifest, _ = _gen(svc)
    assert manifest["level-target"] == "RENAR-2"


def test_next_assessment_due_is_set(svc):
    manifest, _ = _gen(svc)
    assert manifest["next-assessment-due"] == "2026-09-12"  # 2026-06-14 + 90d


def test_render_yaml_is_deterministic(svc):
    m1, _ = _gen(svc)
    m2, _ = _gen(svc)
    assert render_yaml(m1) == render_yaml(m2)


class TestStatusLine:
    """renar-level-in-status: the rich-status one-liner (pure formatter)."""

    def test_pre_adoption_mandatory_unmet(self):
        v = {
            "level": None,
            "pre_adoption": True,
            "unmet_clauses": ["adapt_per_tz"],
            "blocked_at": "mandatory-clauses",
            "missing_signals": [],
        }
        assert format_status_line(v) == "RENAR: pre-adoption (1 mandatory clause(s) unmet)"

    def test_pre_adoption_signal_blocked(self):
        v = {
            "level": None,
            "pre_adoption": True,
            "unmet_clauses": [],
            "blocked_at": "RENAR-1",
            "missing_signals": ["adapt_per_tz"],
        }
        assert format_status_line(v) == "RENAR: pre-adoption (blocked at RENAR-1: adapt_per_tz)"

    def test_achieved_level_blocked_names_signals(self):
        v = {
            "level": "RENAR-1",
            "pre_adoption": False,
            "unmet_clauses": [],
            "blocked_at": "RENAR-2",
            "missing_signals": ["tz_immutable", "delta_tz_artifact"],
        }
        assert format_status_line(v) == (
            "RENAR: RENAR-1 (blocked at RENAR-2: tz_immutable, delta_tz_artifact)"
        )

    def test_top_level_no_blocker(self):
        v = {
            "level": "RENAR-5",
            "pre_adoption": False,
            "unmet_clauses": [],
            "blocked_at": None,
            "missing_signals": [],
        }
        assert format_status_line(v) == "RENAR: RENAR-5"

    def test_current_level_empty_store_is_pre_adoption(self, svc, in_scope):
        # AC: read-only verdict over a live (empty) store -> pre-adoption line.
        line = format_status_line(current_level(svc.be._conn))
        assert line.startswith("RENAR: pre-adoption")

    def test_current_level_reaches_renar1_with_adapt(self, svc, in_scope):
        svc.adapt_create("ad1", "Adapt 1", "TZ-1")
        _satisfy_clause_13_3_3(svc)
        v = current_level(svc.be._conn)
        assert v["level"] == "RENAR-1"
        assert format_status_line(v).startswith("RENAR: RENAR-1")


class TestScopeApplicability:
    """decisions#292: the RIGHT to claim a level, evaluated ahead of the VALUE.

    §1.5.4 withholds RENAR-N from an internal product with no independent
    client representative. The generator reads its own data, so it can only
    ever see whether the signals hold; the applicability precondition is what
    keeps it from printing a level it has no right to print.
    """

    def test_every_signal_true_still_yields_no_level(self, svc):
        """AC-1 red-proof: not one signal state may produce a RENAR-N.

        Drives the store to the richest state the ladder recognises (signed
        ADAPT + SPEC + non-superseded delta) AND forces every level signal
        True, then asserts the verdict still refuses a level. Without the
        precondition this store alone reaches RENAR-2.
        """
        svc.adapt_create("ad1", "Adapt 1", "TZ-1")
        svc.adapt_delta("ad1", "ad1-d1", "Delta 1", "TZ-1", "TZ§1 superseded by delta")
        svc.spec_add("sp1", "API", "Spec 1", "v1", status="active")
        svc.be._conn.execute("UPDATE adapts SET status='approved' WHERE slug='ad1'")
        svc.be._conn.commit()

        bundle = renar_conformance.gather_signals(svc.be._conn)
        bundle["signals"] = {k: True for k in bundle["signals"]}
        clauses = renar_conformance.eval_mandatory_clauses(bundle)
        verdict = renar_conformance.infer_level(bundle, clauses)

        assert verdict["level"] is None
        assert verdict["blocked_at"] == "scope-applicability"
        assert verdict["scope_exclusion"]["clause"] == "§1.5.4"
        # Not pre-adoption: that would claim a trajectory towards RENAR-1.
        assert verdict["pre_adoption"] is False

    def test_lifting_the_exclusion_restores_the_ladder(self, svc, in_scope):
        """Counter-control: with the exclusion lifted the same store reaches a level.

        Guards against the precondition passing vacuously — a broken ladder
        would also return None, and the test above could not tell the two
        apart.
        """
        svc.adapt_create("ad1", "Adapt 1", "TZ-1")
        _satisfy_clause_13_3_3(svc)
        manifest, _ = _gen(svc)
        assert manifest["level"] == "RENAR-1"

    def test_manifest_declares_non_conformance(self, svc):
        """AC-2: the §1.5.4 declaration is explicit, not an omission."""
        svc.adapt_create("ad1", "Adapt 1", "TZ-1")
        manifest, text = _gen(svc)
        assert manifest["level"] is None
        assert manifest["level-target"] is None
        assert manifest["conformance-declaration"] == "non-conformant"
        assert manifest["scope-exclusion"]["clause"] == "§1.5.4"
        assert manifest["scope-exclusion"]["decided-in"] == "decisions#292"
        # §13.8.2 step-2 sentinel. Asserted against the LITERAL the standard
        # names, not against UNKNOWN_STATE_SENTINEL: comparing the field to the
        # constant that produces it is tautological — it survives any change to
        # the constant, which is exactly the mutation this line must catch.
        assert manifest["replaced-by"] == "<unknown-state>"
        assert UNKNOWN_STATE_SENTINEL == "<unknown-state>"
        assert manifest["replaced-by"] is not None
        # Survives serialization — the declaration is what a reader gets.
        loaded = yaml.safe_load(text)
        assert loaded["conformance-declaration"] == "non-conformant"
        assert loaded["level"] is None

    def test_status_line_never_says_pre_adoption(self, svc):
        """A scope exclusion is not a trajectory towards RENAR-1."""
        line = format_status_line(current_level(svc.be._conn))
        assert "pre-adoption" not in line
        assert "non-conformant by declaration" in line
        assert "§1.5.4" in line

    def test_no_renar_n_token_anywhere_in_the_manifest_text(self, svc):
        """AC-3 in the manifest: no RENAR-N reads as a claim.

        `renar-version: "1.1"` and the level ladder inside assessment-evidence
        are not claims, so the assertion is scoped to the claim-bearing keys.
        """
        svc.adapt_create("ad1", "Adapt 1", "TZ-1")
        manifest, _ = _gen(svc)
        for key in ("level", "level-target"):
            assert manifest[key] is None, f"{key} still carries a claim"
