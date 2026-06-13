"""v16r-drift-detectors: RENAR drift-1 (schema) + drift-7 (provenance).

Two warning-mode detectors over the RENAR artifact store. Tests cover both the
POSITIVE path (dirty data → exactly the expected finding kinds) and the NEGATIVE
path (legitimately service-created data → zero findings — the false-positive
guard the task AC demands). Enum-violation branches are unreachable through the
service/CHECK-constrained schema, so they are exercised against a permissive
in-memory table that mirrors only the columns the detector reads.
"""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from renar_drift import (  # noqa: E402
    detect_provenance_drift,
    detect_schema_drift,
    format_findings,
    run_all,
    run_detector,
)


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "drift.db")))
    yield s
    s.be.close()


def _kinds(findings, detector=None):
    return {f["kind"] for f in findings if detector is None or f["detector"] == detector}


# --- NEGATIVE: legitimately created artifacts must not drift -----------------


def test_clean_artifacts_zero_findings(svc):
    """Service-created specs / adapts / task↔spec links → no drift (FP guard)."""
    svc.epic_add("e1", "Epic 1")
    svc.story_add("e1", "s1", "Story 1")
    svc.task_add("s1", "t1", "Task 1", role="developer", goal="g")
    svc.spec_add("sp1", "API", "Spec 1", "v1", status="active")
    svc.spec_link("t1", "sp1", "implements")
    svc.adapt_create("ad1", "Adapt 1", "TZ-1")  # draft, delta_n=0, no parent

    assert run_all(svc.be._conn) == []
    assert detect_schema_drift(svc.be._conn) == []
    assert detect_provenance_drift(svc.be._conn) == []


def test_empty_store_zero_findings(svc):
    """Fresh DB (no artifacts) is the real-world base case — silent."""
    assert run_all(svc.be._conn) == []


def test_missing_tables_return_empty():
    """Older DB without specs/adapts tables → detectors no-op, not crash."""
    conn = sqlite3.connect(":memory:")
    assert detect_schema_drift(conn) == []
    assert detect_provenance_drift(conn) == []
    conn.close()


# --- POSITIVE drift-1: cross-field invariants (reachable via direct insert) ---


def test_adapt_delta_orphan(svc):
    """delta_n>0 with no parent_adapt — DB CHECK can't express this."""
    svc.be._conn.execute(
        "INSERT INTO adapts(slug,title,tz_ref,status,parent_adapt,delta_n,"
        "created_at,updated_at) VALUES('ad-d','t','TZ','draft',NULL,2,'x','x')"
    )
    svc.be._conn.commit()
    assert "adapt-delta-orphan" in _kinds(detect_schema_drift(svc.be._conn))


def test_adapt_base_has_parent(svc):
    """delta_n=0 base adapt that nonetheless chains a parent."""
    svc.adapt_create("ad-p", "Parent", "TZ")
    svc.be._conn.execute(
        "INSERT INTO adapts(slug,title,tz_ref,status,parent_adapt,delta_n,"
        "created_at,updated_at) VALUES('ad-b','t','TZ','draft','ad-p',0,'x','x')"
    )
    svc.be._conn.commit()
    assert "adapt-base-has-parent" in _kinds(detect_schema_drift(svc.be._conn))


def test_adapt_signed_incomplete_signature(svc):
    """status=signed but missing the dual signature (§7.5)."""
    svc.be._conn.execute(
        "INSERT INTO adapts(slug,title,tz_ref,status,parent_adapt,delta_n,"
        "created_at,updated_at) VALUES('ad-s','t','TZ','signed',NULL,0,'x','x')"
    )
    svc.be._conn.commit()
    findings = detect_schema_drift(svc.be._conn)
    assert "adapt-signed-incomplete-signature" in _kinds(findings)
    # A signed adapt with BOTH signatures clears the finding.
    for role in ("client", "architect"):
        svc.be._conn.execute(
            "INSERT INTO adapt_signatures(adapt_slug,role,signed_by,signed_at) "
            "VALUES('ad-s',?,'me','now')",
            (role,),
        )
    svc.be._conn.commit()
    assert "adapt-signed-incomplete-signature" not in _kinds(detect_schema_drift(svc.be._conn))


def test_spec_blank_version(svc):
    """Empty version string slips past NOT NULL but is schema drift."""
    svc.be._conn.execute(
        "INSERT INTO specs(slug,type,title,version,status,created_at,updated_at) "
        "VALUES('sp-b','API','T','','draft','x','x')"
    )
    svc.be._conn.commit()
    assert "spec-version-missing" in _kinds(detect_schema_drift(svc.be._conn))


# --- POSITIVE drift-1: enum branches via permissive (CHECK-free) table -------


def _permissive_specs_conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE specs(slug TEXT, type TEXT, status TEXT, version TEXT, title TEXT)")
    return conn


def test_spec_enum_invalid_permissive():
    conn = _permissive_specs_conn()
    conn.execute("INSERT INTO specs VALUES('x','BOGUS','weird','v1','T')")
    conn.commit()
    kinds = _kinds(detect_schema_drift(conn))
    assert "spec-type-invalid" in kinds
    assert "spec-status-invalid" in kinds
    conn.close()


# --- POSITIVE drift-7: provenance ------------------------------------------


def _seed_linked(svc, task="t1", spec="sp1", spec_status="active"):
    svc.epic_add("e1", "Epic 1")
    svc.story_add("e1", "s1", "Story 1")
    svc.task_add("s1", task, "Task", role="developer", goal="g")
    svc.spec_add(spec, "API", "Spec", "v1", status=spec_status)
    svc.spec_link(task, spec, "implements")


def test_stale_verification(svc):
    """Done task linked to a SPEC edited after the link → stale provenance."""
    _seed_linked(svc)
    # Mark task done and bump the spec's updated_at past the link timestamp.
    svc.be._conn.execute("UPDATE tasks SET status='done' WHERE slug='t1'")
    svc.be._conn.execute("UPDATE specs SET updated_at='9999-12-31T00:00:00Z' WHERE slug='sp1'")
    svc.be._conn.commit()
    findings = detect_provenance_drift(svc.be._conn)
    assert "stale-verification" in _kinds(findings, "drift-7-provenance")


def test_stale_not_fired_when_task_not_done(svc):
    """Same edit but task still active → not a verification claim, no drift."""
    _seed_linked(svc)
    svc.be._conn.execute("UPDATE specs SET updated_at='9999-12-31T00:00:00Z' WHERE slug='sp1'")
    svc.be._conn.commit()
    assert "stale-verification" not in _kinds(detect_provenance_drift(svc.be._conn))


def test_stale_not_fired_on_equal_timestamp(svc):
    """spec.updated_at == link.created_at (same instant) → strict > → no drift."""
    _seed_linked(svc)
    svc.be._conn.execute("UPDATE tasks SET status='done' WHERE slug='t1'")
    svc.be._conn.execute(
        "UPDATE specs SET updated_at=(SELECT created_at FROM task_specs "
        "WHERE spec_slug='sp1') WHERE slug='sp1'"
    )
    svc.be._conn.commit()
    assert "stale-verification" not in _kinds(detect_provenance_drift(svc.be._conn))


def test_stale_not_fired_when_spec_deprecated_after_done(svc):
    """Deprecating a SPEC after the task finished is settled history, not stale.

    The status change bumps updated_at past the link, but a deprecated SPEC is
    no longer a live requirement — stale-verification is scoped to active specs
    so it does NOT double-report alongside deprecated-requirement.
    """
    _seed_linked(svc)
    svc.be._conn.execute("UPDATE tasks SET status='done' WHERE slug='t1'")
    svc.be._conn.commit()
    svc.spec_update("sp1", status="deprecated")  # bumps updated_at
    kinds = _kinds(detect_provenance_drift(svc.be._conn))
    assert "stale-verification" not in kinds
    assert "deprecated-requirement" not in kinds  # task is done, not in-flight


def test_deprecated_requirement(svc):
    """In-flight task linked to a deprecated SPEC → drift."""
    _seed_linked(svc, spec_status="active")
    svc.spec_update("sp1", status="deprecated")
    svc.be._conn.commit()
    assert "deprecated-requirement" in _kinds(detect_provenance_drift(svc.be._conn))


def test_deprecated_not_fired_when_done(svc):
    """A done task against a deprecated SPEC is settled history, not drift."""
    _seed_linked(svc, spec_status="active")
    svc.spec_update("sp1", status="deprecated")
    svc.be._conn.execute("UPDATE tasks SET status='done' WHERE slug='t1'")
    svc.be._conn.commit()
    assert "deprecated-requirement" not in _kinds(detect_provenance_drift(svc.be._conn))


# --- misc -------------------------------------------------------------------


def test_run_detector_unknown_name(svc):
    with pytest.raises(ValueError):
        run_detector(svc.be._conn, "nonsense")


def test_format_findings_empty_and_nonempty():
    assert "No RENAR drift" in format_findings([])
    out = format_findings(
        [
            {
                "detector": "drift-1-schema",
                "kind": "k",
                "ref": "r",
                "message": "m",
                "severity": "warn",
            }
        ]
    )
    assert "drift-1-schema/k" in out and "r" in out
