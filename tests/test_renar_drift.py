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
import renar_drift  # noqa: E402
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


def test_adapt_delta_non_numeric(svc):
    """A corrupt non-numeric delta_n is drift, not a detector crash (sweep #87)."""
    svc.be._conn.execute(
        "INSERT INTO adapts(slug,title,tz_ref,status,parent_adapt,delta_n,"
        "created_at,updated_at) VALUES('ad-bad','t','TZ','draft',NULL,'N/A','x','x')"
    )
    svc.be._conn.commit()
    kinds = _kinds(detect_schema_drift(svc.be._conn))
    assert "adapt-delta-invalid" in kinds
    # delta-relationship checks are skipped (delta_n is None), not double-reported
    assert "adapt-delta-orphan" not in kinds
    assert "adapt-delta-negative" not in kinds


def test_adapt_delta_invalid_does_not_mask_signature(svc):
    """Non-numeric delta_n + approved-without-signatures: BOTH must surface (sweep #87)."""
    svc.be._conn.execute(
        "INSERT INTO adapts(slug,title,tz_ref,status,parent_adapt,delta_n,"
        "created_at,updated_at) VALUES('ad-bs','t','TZ','approved',NULL,'oops','x','x')"
    )
    svc.be._conn.commit()
    kinds = _kinds(detect_schema_drift(svc.be._conn))
    assert "adapt-delta-invalid" in kinds
    assert "adapt-approved-incomplete-signature" in kinds


def test_adapt_base_has_parent(svc):
    """delta_n=0 base adapt that nonetheless chains a parent."""
    svc.adapt_create("ad-p", "Parent", "TZ")
    svc.be._conn.execute(
        "INSERT INTO adapts(slug,title,tz_ref,status,parent_adapt,delta_n,"
        "created_at,updated_at) VALUES('ad-b','t','TZ','draft','ad-p',0,'x','x')"
    )
    svc.be._conn.commit()
    assert "adapt-base-has-parent" in _kinds(detect_schema_drift(svc.be._conn))


def test_adapt_approved_without_the_architect_signature(svc):
    """status=approved but missing the ARCHITECT signature (§7.5).

    §13.3.3 p.77 requires 'approved' WITH an Architect signature. Before v50
    our own status 'signed' conflated the two facts; the status now names the
    acceptance and the signature stays a separate, checkable record. The test
    used to add a CLIENT signature too and only then expect the finding to
    clear — the dual signature ADR-011 withdrew, pinned by a test.
    """
    svc.be._conn.execute(
        "INSERT INTO adapts(slug,title,tz_ref,status,parent_adapt,delta_n,"
        "created_at,updated_at) VALUES('ad-s','t','TZ','approved',NULL,0,'x','x')"
    )
    svc.be._conn.commit()
    findings = detect_schema_drift(svc.be._conn)
    assert "adapt-approved-incomplete-signature" in _kinds(findings)
    # The architect's signature ALONE clears it — nobody else is required.
    svc.be._conn.execute(
        "INSERT INTO adapt_signatures(adapt_slug,role,signed_by,signed_at) "
        "VALUES('ad-s','architect','me','now')"
    )
    svc.be._conn.commit()
    assert "adapt-approved-incomplete-signature" not in _kinds(detect_schema_drift(svc.be._conn))


def test_a_surviving_client_signature_is_named_not_erased(svc):
    """NEGATIVE SCENARIO: history stays, and the detector says what it is.

    A consumer database may hold client signatures written before ADR-011.
    Deleting them would break V1; ignoring them would let a database go on
    looking conformant with a rule the standard has withdrawn. So the row
    survives and is reported — warn-only, naming the ADR.
    """
    svc.be._conn.execute(
        "INSERT INTO adapts(slug,title,tz_ref,status,parent_adapt,delta_n,"
        "created_at,updated_at) VALUES('ad-h','t','TZ','approved',NULL,0,'x','x')"
    )
    for role in ("client", "architect"):
        svc.be._conn.execute(
            "INSERT INTO adapt_signatures(adapt_slug,role,signed_by,signed_at) "
            "VALUES('ad-h',?,'me','now')",
            (role,),
        )
    svc.be._conn.commit()
    findings = detect_schema_drift(svc.be._conn)
    kinds = _kinds(findings)
    assert "signature-role-withdrawn" in kinds, "a withdrawn-norm record must be named"
    assert "signature-role-invalid" not in kinds, "it is history, not a corrupt value"
    assert "adapt-approved-incomplete-signature" not in kinds, "the architect did sign"
    withdrawn = next(f for f in findings if f["kind"] == "signature-role-withdrawn")
    assert "ADR-011" in withdrawn["message"] and withdrawn["severity"] == "warn"
    rows = svc.be._conn.execute("SELECT COUNT(*) FROM adapt_signatures").fetchone()[0]
    assert rows == 2, "the detector reads; it never deletes"


def test_a_role_that_is_neither_current_nor_historical_is_still_invalid(svc):
    """The withdrawn-norm branch must not swallow a genuinely corrupt value.

    THE TABLE IS REBUILT WITHOUT ITS CHECK, and that is the scenario, not a
    trick: this detector exists for databases the constraint did not police —
    an older schema, a rebuild migration run with foreign keys and checks off,
    a direct edit. A first version of this test tried a plain INSERT, the CHECK
    refused it, the test SKIPPED, and a mutation that deleted the whole branch
    survived unnoticed.
    """
    conn = svc.be._conn
    conn.execute(
        "INSERT INTO adapts(slug,title,tz_ref,status,parent_adapt,delta_n,"
        "created_at,updated_at) VALUES('ad-x','t','TZ','draft',NULL,0,'x','x')"
    )
    conn.execute("DROP TABLE adapt_signatures")
    conn.execute(
        "CREATE TABLE adapt_signatures (adapt_slug TEXT NOT NULL, role TEXT NOT NULL, "
        "signed_by TEXT NOT NULL, signed_at TEXT NOT NULL, key_fingerprint TEXT, "
        "signature TEXT, PRIMARY KEY (adapt_slug, role))"
    )
    conn.execute(
        "INSERT INTO adapt_signatures(adapt_slug,role,signed_by,signed_at) "
        "VALUES('ad-x','notary','me','now')"
    )
    conn.commit()
    kinds = _kinds(detect_schema_drift(conn))
    assert "signature-role-invalid" in kinds
    assert "signature-role-withdrawn" not in kinds, "a stranger is not withdrawn history"


def test_the_historical_roles_are_what_the_schema_actually_admits(svc):
    """The declaration is checked against the substrate, not against itself.

    Written because a mutation collapsing HISTORICAL_SIGNATURE_ROLES to the
    current one SURVIVED: 'client' is caught a branch earlier, so nothing
    noticed. What the tuple is FOR is saying which values the CHECK still
    accepts, and that is a claim about the schema — so it is read from the
    schema, the way every other closed list in this project now is.
    """
    from renar_clause_closed_lists import check_domain
    from service_adapts import HISTORICAL_SIGNATURE_ROLES, SIGNATURE_ROLES

    admitted = check_domain(svc.be._conn, "adapt_signatures", "role")
    assert admitted is not None, "the CHECK must be readable"
    assert set(admitted) == set(HISTORICAL_SIGNATURE_ROLES), (
        "the historical declaration and the constraint have drifted apart"
    )
    assert set(SIGNATURE_ROLES) < set(admitted), (
        "the writable roles must be a strict subset — the withdrawn one stays "
        "readable and stops being writable"
    )


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
    """Done task whose SPEC was edited after the VERIFICATION → stale provenance.

    drift7-dates-the-link-not-the-verification: the detector now dates the
    verification, not the link, so this fixture has to state WHEN the task was
    verified. It closed the task with a bare UPDATE, which leaves
    `completed_at` NULL and records no verification run — under the corrected
    rule that row is not stale, it is undateable, and it is now reported as
    such. Setting a completion time expresses what this test always meant.
    """
    _seed_linked(svc)
    # Close the task at a known instant, then bump the spec's updated_at past it.
    svc.be._conn.execute(
        "UPDATE tasks SET status='done', completed_at='2026-01-01T00:00:00Z' WHERE slug='t1'"
    )
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


# --- check-adapt-supersession: §10.11.1 / ADR-007's named gate ---------------


def _adapts_table(tmp_path, rows):
    """A permissive `adapts` table holding only the columns the detector reads.

    The states under test cannot be reached through the service: the write path
    refuses a supersession without a rationale, and nothing today creates a
    delta-ADAPT at all. Proving the detector's teeth therefore has to be done on
    SYNTHETIC state — the detector is a function of a CONNECTION precisely so
    that showing it can red never requires damaging the live store.
    """
    conn = sqlite3.connect(str(tmp_path / "sup.db"))
    conn.execute(
        "CREATE TABLE adapts (slug TEXT, status TEXT, parent_adapt TEXT, "
        "delta_n INTEGER, supersession_rationale TEXT)"
    )
    conn.executemany(
        "INSERT INTO adapts (slug, status, parent_adapt, delta_n, supersession_rationale) "
        "VALUES (?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    return conn


def test_superseded_status_is_one_the_closed_list_admits():
    """A detector watching a status the standard dropped would watch nothing.

    Checked here rather than by an `assert` at import: a value drifting out of
    the closed list must surface as a red test, not as a production exception.
    """
    from service_adapts import ADAPT_STATUSES

    assert renar_drift.SUPERSEDED_STATUS in ADAPT_STATUSES


def test_a_delta_hanging_off_a_superseded_parent_is_found(tmp_path):
    conn = _adapts_table(
        tmp_path,
        [
            ("adapt-parent", "superseded", None, None, "replaced by adapt-next"),
            ("adapt-parent-d1", "draft", "adapt-parent", 1, None),
        ],
    )
    try:
        findings = renar_drift.detect_supersession_drift(conn)
    finally:
        conn.close()
    assert _kinds(findings) == {"delta-of-superseded-parent"}
    assert findings[0]["ref"] == "adapt-parent-d1"
    assert findings[0]["detector"] == "check-adapt-supersession"


def test_a_supersession_without_a_rationale_is_found(tmp_path):
    """The write path refuses this today; a row written before it did not."""
    conn = _adapts_table(tmp_path, [("adapt-old", "superseded", None, None, "   ")])
    try:
        findings = renar_drift.detect_supersession_drift(conn)
    finally:
        conn.close()
    assert _kinds(findings) == {"supersession-without-rationale"}


def test_a_healthy_store_yields_no_supersession_findings(tmp_path):
    """NEGATIVE PATH: a detector that reports on clean data is indistinguishable
    from one that reports unconditionally.

    Every ingredient of both findings is present and correct here — a
    supersession WITH a rationale, and a delta-ADAPT whose parent is alive.
    """
    conn = _adapts_table(
        tmp_path,
        [
            ("adapt-live", "approved", None, None, None),
            ("adapt-live-d1", "draft", "adapt-live", 1, None),
            ("adapt-retired", "superseded", None, None, "superseded by adapt-live"),
        ],
    )
    try:
        assert renar_drift.detect_supersession_drift(conn) == []
    finally:
        conn.close()


def test_the_live_store_is_clean_and_the_detector_still_ran(svc):
    """On the service's own schema the detector runs and finds nothing.

    Distinct from the synthetic case above: this proves the SQL matches the real
    column names, which a hand-built table cannot show.
    """
    assert renar_drift.detect_supersession_drift(svc.be._conn) == []
    assert "supersession" in renar_drift._DETECTORS


def test_a_missing_adapts_table_is_a_no_op_but_a_missing_column_is_not(tmp_path):
    """NEGATIVE SCENARIO: silence is allowed for absence, never for "could not check".

    A database predating the ADAPT migrations has nothing to validate, so the
    detector is quiet. A database WITH the table but missing the column the
    detector reads is a different event: it must propagate so the gate degrades
    to could-not-run. "Could not be checked" is not "checked and fine".
    """
    empty = sqlite3.connect(str(tmp_path / "none.db"))
    try:
        assert renar_drift.detect_supersession_drift(empty) == []
    finally:
        empty.close()

    partial = sqlite3.connect(str(tmp_path / "partial.db"))
    partial.execute("CREATE TABLE adapts (slug TEXT, status TEXT)")
    partial.commit()
    try:
        with pytest.raises(sqlite3.OperationalError, match="no such column"):
            renar_drift.detect_supersession_drift(partial)
    finally:
        partial.close()


def test_the_gate_name_is_the_one_adr_007_promised():
    """The ADR named the gate; the registry must carry that name, not a synonym."""
    import gate_registry
    from gate_renar_drift import _GATE_TO_DETECTOR

    assert _GATE_TO_DETECTOR["check_adapt_supersession"] == "supersession"
    assert "check_adapt_supersession" in gate_registry.GATE_REGISTRY


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
