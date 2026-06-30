"""v16r-conformance-yaml: honest RENAR-CONFORMANCE.yaml self-assessment.

Asserts (1) the manifest always carries every §14.4.2 mandatory field and
round-trips through YAML, (2) the level is derived from live DB state — an empty
artifact store yields pre-adoption (adapt-per-tz unmet, §14.4.3), and (3) the
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
from renar_conformance import (  # noqa: E402
    MANDATORY_FIELDS,
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


def _gen(svc):
    return generate(svc.be._conn, "architect-test", "2026-06-14")


# --- manifest shape ---------------------------------------------------------


def test_all_mandatory_fields_present(svc):
    manifest, _ = _gen(svc)
    for field in MANDATORY_FIELDS:
        assert field in manifest, f"missing mandatory §14.4.2 field {field!r}"
    assert set(manifest["quality-gates"]) == {"qg-0", "qg-1", "qg-2", "qg-3", "qg-4"}
    assert len(manifest["spec-types-supported"]) == 9
    sc = manifest["substrate-capabilities"]
    for v in ("v1-immutable-history", "v6-author-timestamp"):
        assert v in sc


def test_yaml_round_trips(svc):
    manifest, text = _gen(svc)
    loaded = yaml.safe_load(text)
    # The header comment is dropped by the loader; body must equal the manifest.
    assert loaded == manifest
    assert loaded["renar-version"] == "1.0"


# --- honest level inference -------------------------------------------------


def test_empty_db_is_pre_adoption(svc):
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


def test_single_adapt_reaches_renar_1(svc):
    """One ADAPT satisfies every mandatory clause → RENAR-1 (RENAR-2 needs SPEC)."""
    svc.adapt_create("ad1", "Adapt 1", "TZ-1")
    manifest, _ = _gen(svc)
    assert manifest["mandatory-clauses-confirmed"]["adapt-per-tz"] is True
    assert manifest["level"] == "RENAR-1"
    assert manifest["pre-adoption"] is False
    assert manifest["assessment-evidence"]["blocked-at"] == "RENAR-2"


def test_draft_adapt_does_not_reach_renar_2(svc):
    """A draft ADAPT is not an immutable TZ (§12.5.1) → tz_immutable stays False."""
    svc.adapt_create("ad1", "Adapt 1", "TZ-1")
    svc.adapt_delta("ad1", "ad1-d1", "Delta 1", "TZ-1")
    svc.spec_add("sp1", "API", "Spec 1", "v1", status="active")
    manifest, _ = _gen(svc)
    assert manifest["assessment-evidence"]["level-signals"]["tz_immutable"] is False
    assert manifest["level"] == "RENAR-1"  # blocked at RENAR-2 by tz_immutable


def test_signed_adapt_spec_delta_reach_renar_2(svc):
    """Signed ADAPT (immutable TZ) + SPEC + delta → RENAR-2; RENAR-3 blocked."""
    svc.adapt_create("ad1", "Adapt 1", "TZ-1")
    svc.adapt_delta("ad1", "ad1-d1", "Delta 1", "TZ-1")
    svc.spec_add("sp1", "API", "Spec 1", "v1", status="active")
    # Simulate a signed (immutable) ADAPT without the ed25519 key ceremony.
    svc.be._conn.execute("UPDATE adapts SET status='signed' WHERE slug='ad1'")
    svc.be._conn.commit()
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


def test_level_target_advances_when_conformant(svc):
    svc.adapt_create("ad1", "Adapt 1", "TZ-1")  # RENAR-1, pre_adoption False
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

    def test_current_level_empty_store_is_pre_adoption(self, svc):
        # AC: read-only verdict over a live (empty) store -> pre-adoption line.
        line = format_status_line(current_level(svc.be._conn))
        assert line.startswith("RENAR: pre-adoption")

    def test_current_level_reaches_renar1_with_adapt(self, svc):
        svc.adapt_create("ad1", "Adapt 1", "TZ-1")
        v = current_level(svc.be._conn)
        assert v["level"] == "RENAR-1"
        assert format_status_line(v).startswith("RENAR: RENAR-1")
