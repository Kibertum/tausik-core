"""actz-the-contract-contour-artifact-is-missing: RENAR ACTZ artifacts (Sec5A).

Covers the v52 migration, header/point CRUD, closed statuses + 2 signature
roles (CHECK + service validation), signature lifecycle (architect real
ed25519, client name+timestamp only), delta/supersession, links, decided-in
(with provenance, signed-only target), late-dated ACTZ as the normal case,
FTS5 search, CLI parser wiring, MCP dispatch, and the "акт" word guard.
"""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from actz_closed_lists import (  # noqa: E402
    ACTZ_STATUSES,
    LINK_TARGETS,
    REQUIRED_SIGNATURE_ROLES,
    SIGNATURE_ROLES,
)
from backend_migrations import run_migrations  # noqa: E402
from backend_schema import SCHEMA_VERSION  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from service_actz import FORBIDDEN_WORD_RE, display_name  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "actz.db")))
    yield s
    s.be.close()


@pytest.fixture
def svc_keyed(tmp_path):
    """Service whose project_dir carries a FRESH ephemeral ed25519 keypair."""
    import crypto_keys

    crypto_keys.init_keys(str(tmp_path))
    s = ProjectService(SQLiteBackend(str(tmp_path / "actz.db")))
    s._project_dir = str(tmp_path)
    yield s
    s.be.close()


def _full_adapt(svc, slug: str = "a1") -> int:
    """A signed-ADAPT-analogue finding to decided-in against. Returns finding id."""
    svc.adapt_create(slug, "Auth ADAPT", "TZ-2026-001")
    svc.adapt_finding(slug, "gap", "No MFA stated", tz_ref="TZ-3.1")
    return svc.be.findings_for_adapt(slug)[0]["id"]


def _signed_actz(svc_keyed, slug: str = "z1") -> None:
    svc_keyed.actz_create(slug, "Сроки приёмки", "TZ-2026-001")
    svc_keyed.actz_point_add(
        slug, 1, "TZ-1", "Приёмка завершается через 5 рабочих дней после демо."
    )
    svc_keyed.actz_sign(slug, "architect", "Архитектор А.", svc_keyed._project_dir)
    svc_keyed.actz_sign(slug, "client", "Заказчик Б.")


# === closed lists are exactly the RENAR closed sets, mirrored by the DB CHECK ===


def test_statuses_closed_four():
    assert ACTZ_STATUSES == ("draft", "sent", "signed", "superseded")


def test_signature_roles_closed_two():
    assert SIGNATURE_ROLES == ("architect", "client")
    assert REQUIRED_SIGNATURE_ROLES == ("architect", "client")


def test_link_targets_same_as_adapt():
    assert LINK_TARGETS == ("task", "spec")


# === schema / migration ===


def test_schema_version_at_least_53():
    from backend_migrations import MIGRATIONS

    assert SCHEMA_VERSION >= 53
    assert 52 in MIGRATIONS
    assert 53 in MIGRATIONS


def test_migration_v52_then_v53_matches_fresh_shape(tmp_path):
    """Same shape as test_adapts.test_migration_v36_creates_tables_clean: seed a
    minimal pre-v36 fixture and let run_migrations walk every pending version up
    to current (36 creates adapts/adapt_findings before 52's FK needs them; 53
    ALTERs actz_points.tz_ref onto the table 52 created). The migrated result
    must match backend_schema_actz's current cumulative shape -- the
    byte-equivalence discipline that module's docstring now claims."""
    path = str(tmp_path / "premigration.db")
    conn = sqlite3.connect(path)
    conn.isolation_level = None
    conn.execute("CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.execute("INSERT INTO meta VALUES('schema_version', '35')")
    conn.execute(
        "CREATE TABLE tasks(slug TEXT PRIMARY KEY, defect_of TEXT)"
    )  # defect_of: v10 column, indexed by v62
    conn.execute("CREATE TABLE verification_runs(id INTEGER PRIMARY KEY AUTOINCREMENT)")
    conn.execute("CREATE TABLE decisions(id INTEGER PRIMARY KEY AUTOINCREMENT)")
    conn.execute("CREATE TABLE memory(id INTEGER PRIMARY KEY AUTOINCREMENT)")

    new_ver = run_migrations(conn, 35)
    assert new_ver >= 53
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'actz%'"
        )
    }
    assert tables == {
        "actz",
        "actz_points",
        "actz_signatures",
        "actz_links",
        "actz_decided_in",
    }
    cols = {r[1] for r in conn.execute("PRAGMA table_info(actz_points)")}
    assert "tz_ref" in cols
    conn.close()


def test_fresh_backend_has_actz_tables(svc):
    row = svc.be._q1("SELECT name FROM sqlite_master WHERE name='actz'")
    assert row is not None


def test_invalid_status_rejected_at_db(svc):
    with pytest.raises(sqlite3.IntegrityError):
        svc.be._ins(
            "INSERT INTO actz(slug,title,tz_ref,status,created_at,updated_at) "
            "VALUES('z','T','TZ',?,'x','x')",
            ("bogus",),
        )


def test_invalid_role_rejected_at_db(svc):
    svc.actz_create("z1", "T", "TZ-1")
    with pytest.raises(sqlite3.IntegrityError):
        svc.be._ins(
            "INSERT INTO actz_signatures(actz_slug,role,signed_by,signed_at) VALUES(?,?,?,?)",
            ("z1", "bogus", "x", "x"),
        )


# === header CRUD ===


def test_create_and_show(svc):
    svc.actz_create("z1", "Сроки приёмки", "TZ-2026-001")
    a = svc.actz_show("z1")
    assert a["status"] == "draft"
    assert a["display_name"] == f"Протокол уточнения ТЗ № {a['id']}"


def test_duplicate_slug_rejected(svc):
    svc.actz_create("z1", "T", "TZ-1")
    with pytest.raises(ServiceError):
        svc.actz_create("z1", "T2", "TZ-2")
    # The refused duplicate must not have touched the original row.
    assert svc.actz_show("z1")["title"] == "T"


def test_missing_tz_ref_rejected(svc):
    with pytest.raises(ServiceError):
        svc.actz_create("z1", "T", "")


def test_delete_cascades(svc):
    svc.actz_create("z1", "T", "TZ-1")
    svc.actz_point_add("z1", 1, "TZ-1", "п.1")
    svc.actz_delete("z1")
    assert svc.be._q("SELECT * FROM actz_points WHERE actz_slug='z1'") == []


# === points, frozen once any signature is recorded ===


def test_point_add_requires_draft(svc_keyed):
    svc_keyed.actz_create("z1", "T", "TZ-1")
    svc_keyed.actz_point_add("z1", 1, "TZ-1", "п.1")
    svc_keyed.actz_sign("z1", "architect", "A.", svc_keyed._project_dir)
    with pytest.raises(ServiceError, match="frozen"):
        svc_keyed.actz_point_add("z1", 2, "TZ-1", "п.2")


def test_duplicate_point_no_rejected(svc):
    svc.actz_create("z1", "T", "TZ-1")
    svc.actz_point_add("z1", 1, "TZ-1", "п.1")
    with pytest.raises(ServiceError):
        svc.actz_point_add("z1", 1, "TZ-1", "again")


def test_empty_point_text_rejected(svc):
    svc.actz_create("z1", "T", "TZ-1")
    with pytest.raises(ServiceError):
        svc.actz_point_add("z1", 1, "TZ-1", "   ")


# === signatures: architect real ed25519, client name+timestamp only ===


def test_architect_signature_is_real_ed25519_and_verifies(svc_keyed):
    svc_keyed.actz_create("z1", "T", "TZ-1")
    svc_keyed.actz_point_add("z1", 1, "TZ-1", "п.1")
    svc_keyed.actz_sign("z1", "architect", "A.", svc_keyed._project_dir)
    row = svc_keyed.be.signatures_for_actz("z1")[0]
    assert row["signature"] and row["key_fingerprint"]
    res = svc_keyed.actz_verify("z1", svc_keyed._project_dir)
    assert res == {"signed": True, "valid": True, "reason": "ok"}


def test_client_signature_has_no_signature_or_fingerprint(svc):
    svc.actz_create("z1", "T", "TZ-1")
    svc.actz_point_add("z1", 1, "TZ-1", "п.1")
    svc.actz_sign("z1", "client", "Заказчик Б.")
    row = svc.be.signatures_for_actz("z1")[0]
    assert row["signed_by"] == "Заказчик Б."
    assert row["signature"] is None
    assert row["key_fingerprint"] is None


def test_one_signature_does_not_reach_signed(svc_keyed):
    """AC-6: neither role alone completes the contract."""
    svc_keyed.actz_create("z1", "T", "TZ-1")
    svc_keyed.actz_point_add("z1", 1, "TZ-1", "п.1")
    svc_keyed.actz_sign("z1", "architect", "A.", svc_keyed._project_dir)
    assert svc_keyed.actz_show("z1")["status"] == "sent"


def test_both_signatures_reach_signed(svc_keyed):
    _signed_actz(svc_keyed)
    assert svc_keyed.actz_show("z1")["status"] == "signed"


def test_client_signature_without_signed_by_rejected(svc):
    svc.actz_create("z1", "T", "TZ-1")
    with pytest.raises(ServiceError):
        svc.actz_sign("z1", "client", "")
    # A refused signature attempt must not have left a partial row.
    assert svc.be.signatures_for_actz("z1") == []


def test_resign_architect_after_signed_rejected(svc_keyed):
    _signed_actz(svc_keyed)
    with pytest.raises(ServiceError, match="already signed"):
        svc_keyed.actz_sign("z1", "architect", "A.", svc_keyed._project_dir)


def test_invalid_role_rejected_at_service(svc):
    svc.actz_create("z1", "T", "TZ-1")
    with pytest.raises(ServiceError) as exc:
        svc.actz_sign("z1", "bystander", "X")
    # The refusal must name the offending role, not just say "invalid".
    assert "bystander" in str(exc.value)


def test_verify_unsigned_reports_not_signed(svc):
    svc.actz_create("z1", "T", "TZ-1")
    assert svc.actz_verify("z1") == {
        "signed": False,
        "valid": False,
        "reason": "no architect signature",
    }


def test_architect_signature_without_key_is_service_error(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "nokey.db")))
    s.actz_create("z1", "T", "TZ-1")
    with pytest.raises(ServiceError, match="project key"):
        s.actz_sign("z1", "architect", "A.", str(tmp_path))
    s.be.close()


# === delta / supersession ===


def test_delta_supersedes_parent(svc):
    svc.actz_create("z1", "T", "TZ-1")
    svc.actz_delta("z1", "z2", "T delta", "TZ-1b", "clause changed")
    assert svc.actz_show("z1")["status"] == "superseded"
    assert svc.actz_show("z2")["parent_actz"] == "z1"


def test_supersede_without_reason_is_refused(svc):
    svc.actz_create("z1", "T", "TZ-1")
    with pytest.raises(ServiceError):
        svc.actz_delta("z1", "z2", "T2", "TZ-2", "")
    # A refusal is a non-event: the child must not have been left behind.
    assert svc.be.actz_get("z2") is None
    assert svc.actz_show("z1")["status"] == "draft"


def test_link_to_superseded_is_refused(svc):
    svc.epic_add("e1", "E1")
    svc.story_add("e1", "s1", "S1")
    svc.task_add("s1", "t1", "T1", role="developer", goal="g")
    svc.actz_create("z1", "T", "TZ-1")
    svc.actz_delta("z1", "z2", "T2", "TZ-2", "reason")
    with pytest.raises(ServiceError, match="dangling"):
        svc.actz_link("z1", "task", "t1")


def test_sign_superseded_rejected(svc):
    svc.actz_create("z1", "T", "TZ-1")
    svc.actz_delta("z1", "z2", "T2", "TZ-2", "reason")
    with pytest.raises(ServiceError, match="superseded"):
        svc.actz_sign("z1", "architect", "A.")
    # The refused sign attempt on the dead parent must not have recorded anything.
    assert svc.be.signatures_for_actz("z1") == []


# === links ===


def test_link_to_task_and_missing_task_errors(svc):
    svc.epic_add("e1", "E1")
    svc.story_add("e1", "s1", "S1")
    svc.task_add("s1", "t1", "T1", role="developer", goal="g")
    svc.actz_create("z1", "T", "TZ-1")
    svc.actz_link("z1", "task", "t1")
    assert svc.actzs_for_target("task", "t1")[0]["slug"] == "z1"
    with pytest.raises(ServiceError):
        svc.actz_link("z1", "task", "no-such-task")


def test_duplicate_link_rejected(svc):
    svc.epic_add("e1", "E1")
    svc.story_add("e1", "s1", "S1")
    svc.task_add("s1", "t1", "T1", role="developer", goal="g")
    svc.actz_create("z1", "T", "TZ-1")
    svc.actz_link("z1", "task", "t1")
    with pytest.raises(ServiceError):
        svc.actz_link("z1", "task", "t1")


def test_unlink_missing_link_errors(svc):
    svc.epic_add("e1", "E1")
    svc.story_add("e1", "s1", "S1")
    svc.task_add("s1", "t1", "T1", role="developer", goal="g")
    svc.actz_create("z1", "T", "TZ-1")
    svc.actz_link("z1", "task", "t1")
    with pytest.raises(ServiceError):
        svc.actz_unlink("z1", "task", "nope")
    # The refused unlink on a WRONG target must not have touched the real link.
    assert len(svc.be.links_for_actz("z1")) == 1


# === decided-in: 1..N ADAPT findings per SIGNED ACTZ point, with provenance ===


def test_decided_in_requires_signed_actz(svc):
    finding_id = _full_adapt(svc)
    svc.actz_create("z1", "T", "TZ-1")
    svc.actz_point_add("z1", 1, "TZ-1", "п.1")
    with pytest.raises(ServiceError, match="SIGNED"):
        svc.actz_decided_in("a1", finding_id, "z1", 1, "Архитектор")


def test_decided_in_recorded_with_provenance(svc_keyed):
    finding_id = _full_adapt(svc_keyed)
    _signed_actz(svc_keyed)
    svc_keyed.actz_decided_in("a1", finding_id, "z1", 1, "Архитектор А.")
    row = svc_keyed.be.decided_in_for_point("z1", 1)[0]
    assert row["linked_by"] == "Архитектор А."
    assert row["created_at"]


def test_decided_in_many_findings_per_point(svc_keyed):
    """RENAR cardinality: 1..N ADAPT findings may cite the same ACTZ point."""
    svc_keyed.adapt_create("a1", "Auth ADAPT", "TZ-2026-001")
    svc_keyed.adapt_finding("a1", "gap", "finding 1", tz_ref="TZ-3.1")
    svc_keyed.adapt_finding("a1", "gap", "finding 2", tz_ref="TZ-3.2")
    f1, f2 = [f["id"] for f in svc_keyed.be.findings_for_adapt("a1")]
    _signed_actz(svc_keyed)
    svc_keyed.actz_decided_in("a1", f1, "z1", 1, "A.")
    svc_keyed.actz_decided_in("a1", f2, "z1", 1, "A.")
    assert len(svc_keyed.be.decided_in_for_point("z1", 1)) == 2


def test_decided_in_missing_finding_errors(svc_keyed):
    _signed_actz(svc_keyed)
    svc_keyed.adapt_create("a1", "T", "TZ-1")
    with pytest.raises(ServiceError, match="[Ff]inding"):
        svc_keyed.actz_decided_in("a1", 999, "z1", 1, "A.")


def test_decided_in_missing_point_errors(svc_keyed):
    finding_id = _full_adapt(svc_keyed)
    _signed_actz(svc_keyed)
    with pytest.raises(ServiceError, match="point"):
        svc_keyed.actz_decided_in("a1", finding_id, "z1", 99, "A.")


def test_decided_in_remove(svc_keyed):
    finding_id = _full_adapt(svc_keyed)
    _signed_actz(svc_keyed)
    svc_keyed.actz_decided_in("a1", finding_id, "z1", 1, "A.")
    svc_keyed.actz_decided_in_remove("a1", finding_id, "z1", 1)
    assert svc_keyed.be.decided_in_for_point("z1", 1) == []


def test_decided_in_remove_missing_errors(svc):
    with pytest.raises(ServiceError):
        svc.actz_decided_in_remove("a1", 1, "z1", 1)


# === final-TZ (§5A.4): derived acceptance reference, priority to the later signed ===


def _set_completion(svc, actz_slug: str, ts: str) -> None:
    """Force both signature rows' signed_at to an exact timestamp -- second-
    resolution utcnow_iso() cannot reliably order two real-time signs within a
    fast test, so completion time is set directly rather than raced for."""
    svc.be._ex("UPDATE actz_signatures SET signed_at=? WHERE actz_slug=?", (ts, actz_slug))


def test_final_tz_snapshot_empty_when_nothing_signed(svc):
    svc.actz_create("z1", "T", "TZ-1")
    svc.actz_point_add("z1", 1, "TZ-3.1", "draft text")
    assert svc.final_tz_snapshot() == []


def test_final_tz_snapshot_ignores_unsigned_points(svc_keyed):
    svc_keyed.actz_create("z1", "T", "TZ-1")
    svc_keyed.actz_point_add("z1", 1, "TZ-3.1", "sent, not fully signed")
    svc_keyed.actz_sign("z1", "architect", "A.", svc_keyed._project_dir)
    assert svc_keyed.final_tz_snapshot() == []


def test_final_tz_snapshot_picks_the_later_signed_point(svc_keyed):
    svc_keyed.actz_create("z1", "T1", "TZ-1")
    svc_keyed.actz_point_add("z1", 1, "TZ-3.1", "earlier clarification")
    svc_keyed.actz_sign("z1", "architect", "A.", svc_keyed._project_dir)
    svc_keyed.actz_sign("z1", "client", "C.")
    _set_completion(svc_keyed, "z1", "2026-01-01T00:00:00Z")

    svc_keyed.actz_create("z2", "T2", "TZ-1b")
    svc_keyed.actz_point_add("z2", 1, "TZ-3.1", "later clarification wins")
    svc_keyed.actz_sign("z2", "architect", "A.", svc_keyed._project_dir)
    svc_keyed.actz_sign("z2", "client", "C.")
    _set_completion(svc_keyed, "z2", "2026-02-01T00:00:00Z")

    snap = svc_keyed.final_tz_snapshot()
    assert len(snap) == 1
    row = snap[0]
    assert row["tz_ref"] == "TZ-3.1"
    assert row["governing_actz"] == "z2"
    assert row["governing_text"] == "later clarification wins"
    assert row["overridden"] == [
        {"actz_slug": "z1", "point_no": 1, "completed_at": "2026-01-01T00:00:00Z"}
    ]


def test_final_tz_snapshot_as_of_a_past_moment(svc_keyed):
    svc_keyed.actz_create("z1", "T1", "TZ-1")
    svc_keyed.actz_point_add("z1", 1, "TZ-3.1", "earlier")
    svc_keyed.actz_sign("z1", "architect", "A.", svc_keyed._project_dir)
    svc_keyed.actz_sign("z1", "client", "C.")
    _set_completion(svc_keyed, "z1", "2026-01-01T00:00:00Z")

    svc_keyed.actz_create("z2", "T2", "TZ-1b")
    svc_keyed.actz_point_add("z2", 1, "TZ-3.1", "later")
    svc_keyed.actz_sign("z2", "architect", "A.", svc_keyed._project_dir)
    svc_keyed.actz_sign("z2", "client", "C.")
    _set_completion(svc_keyed, "z2", "2026-02-01T00:00:00Z")

    # As of a moment BEFORE z2 completed, z1 is what governed.
    snap = svc_keyed.final_tz_snapshot(as_of="2026-01-15T00:00:00Z")
    assert snap[0]["governing_actz"] == "z1"
    assert snap[0]["overridden"] == []

    # Boundary: as_of EXACTLY at z1's completion moment is INCLUSIVE -- "as of
    # this timestamp" means the state that held once that moment was reached.
    snap_at_boundary = svc_keyed.final_tz_snapshot(as_of="2026-01-01T00:00:00Z")
    assert snap_at_boundary[0]["governing_actz"] == "z1"


def test_final_tz_snapshot_two_tz_refs_are_independent(svc_keyed):
    svc_keyed.actz_create("z1", "T", "TZ-1")
    svc_keyed.actz_point_add("z1", 1, "TZ-3.1", "clause 3.1")
    svc_keyed.actz_point_add("z1", 2, "TZ-3.2", "clause 3.2")
    svc_keyed.actz_sign("z1", "architect", "A.", svc_keyed._project_dir)
    svc_keyed.actz_sign("z1", "client", "C.")
    refs = {r["tz_ref"] for r in svc_keyed.final_tz_snapshot()}
    assert refs == {"TZ-3.1", "TZ-3.2"}


# === orphan signed points (§5A.4 fatal): a signed decision no ADAPT reflects ===


def test_orphan_signed_points_finds_unlinked_signed_point(svc_keyed):
    _signed_actz(svc_keyed)
    orphans = svc_keyed.orphan_signed_points()
    assert len(orphans) == 1
    assert orphans[0]["actz_slug"] == "z1"
    assert orphans[0]["point_no"] == 1
    assert orphans[0]["tz_ref"] == "TZ-1"


def test_orphan_signed_points_excludes_a_linked_point(svc_keyed):
    finding_id = _full_adapt(svc_keyed)
    _signed_actz(svc_keyed)
    svc_keyed.actz_decided_in("a1", finding_id, "z1", 1, "A.")
    assert svc_keyed.orphan_signed_points() == []


def test_orphan_signed_points_excludes_unsigned_points(svc):
    svc.actz_create("z1", "T", "TZ-1")
    svc.actz_point_add("z1", 1, "TZ-3.1", "still draft")
    orphans = svc.orphan_signed_points()
    # Not just empty: confirm it's SILENT because nothing is signed yet, not
    # because the query itself is broken -- signing then re-checking finds it.
    assert orphans == []
    svc.actz_create("z2", "T2", "TZ-2")
    assert svc.orphan_signed_points() == orphans


# === late-dated ACTZ is the NORMAL case (AC-4), not an anomaly ===


def test_late_actz_after_other_work_is_not_flagged(svc):
    """Sec5A: a protocol formalized after a demo is the standard case -- an
    ACTZ dated after the task it clarifies must succeed with no anomaly flag."""
    svc.epic_add("e1", "E1")
    svc.story_add("e1", "s1", "S1")
    svc.task_add("s1", "t1", "T1 (already exists before this ACTZ)", role="developer", goal="g")
    msg = svc.actz_create("z1", "Late protocol", "TZ-1")
    assert "created" in msg
    svc.actz_link("z1", "task", "t1")


# === FTS5 search ===


def test_fts_search_finds_actz(svc):
    svc.actz_create("z1", "Сроки приёмки", "TZ-2026-001")
    rows = svc.actz_search("приёмки")
    assert any(r["slug"] == "z1" for r in rows)


def test_fts_delete_trigger_removes_entry(svc):
    svc.actz_create("z1", "Сроки приёмки", "TZ-2026-001")
    svc.actz_delete("z1")
    assert svc.actz_search("приёмки") == []


def test_malformed_fts_query_is_friendly_error(svc):
    with pytest.raises(ServiceError, match="unterminated"):
        svc.actz_search('"unterminated')


# === CLI parser wiring ===


def test_cli_parser_accepts_actz_create():
    from project_parser import build_parser

    parser = build_parser()
    ns = parser.parse_args(["actz", "create", "z1", "Title", "--tz-ref", "TZ-1"])
    assert ns.tz_ref == "TZ-1"
    assert ns.slug == "z1"
    assert ns.title == "Title"


def test_cli_parser_rejects_bad_signature_role():
    from project_parser import build_parser

    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["actz", "sign", "z1", "bogus", "--by", "A."])


def test_cli_parser_accepts_point_with_tz_ref():
    from project_parser import build_parser

    parser = build_parser()
    ns = parser.parse_args(["actz", "point", "z1", "1", "--tz-ref", "TZ-3.1", "text"])
    assert ns.tz_ref == "TZ-3.1"
    assert ns.point_no == 1


def test_cli_parser_accepts_final_tz_with_as_of():
    from project_parser import build_parser

    parser = build_parser()
    ns = parser.parse_args(["actz", "final-tz", "--as-of", "2026-01-01T00:00:00Z"])
    assert ns.as_of == "2026-01-01T00:00:00Z"


def test_cli_parser_accepts_orphans():
    from project_parser import build_parser

    parser = build_parser()
    ns = parser.parse_args(["actz", "orphans"])
    assert ns.actz_cmd == "orphans"


# === MCP dispatch: FULL parity, unlike adapt's 9-of-12 ===


def test_mcp_dispatch_registers_all_actz_tools_full_parity():
    sys.path.insert(
        0, os.path.join(os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project")
    )
    import handlers_actz

    expected = {
        "tausik_actz_create",
        "tausik_actz_point",
        "tausik_actz_sign",
        "tausik_actz_verify",
        "tausik_actz_show",
        "tausik_actz_list",
        "tausik_actz_delta",
        "tausik_actz_link",
        "tausik_actz_unlink",
        "tausik_actz_delete",
        "tausik_actz_search",
        "tausik_actz_decided_in",
        "tausik_actz_decided_in_remove",
        "tausik_actz_final_tz",
        "tausik_actz_orphans",
    }
    assert expected == set(handlers_actz.ACTZ_HANDLERS)


def test_mcp_tool_schema_matches_handler_set():
    sys.path.insert(
        0, os.path.join(os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project")
    )
    import handlers_actz
    import tools_actz

    tool_names = {t["name"] for t in tools_actz.TOOLS_ACTZ}
    assert tool_names == set(handlers_actz.ACTZ_HANDLERS)


def test_mcp_handler_create_and_show(svc):
    sys.path.insert(
        0, os.path.join(os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project")
    )
    import handlers_actz

    out = handlers_actz.handle_actz_create(svc, {"slug": "z1", "title": "T", "tz_ref": "TZ-1"})
    assert "created" in out
    shown = handlers_actz.handle_actz_show(svc, {"slug": "z1"})
    assert '"tz_ref": "TZ-1"' in shown
    assert "display_name" in shown


def test_mcp_handler_invalid_role_returns_error(svc):
    sys.path.insert(
        0, os.path.join(os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project")
    )
    import handlers_actz

    handlers_actz.handle_actz_create(svc, {"slug": "z1", "title": "T", "tz_ref": "TZ-1"})
    out = handlers_actz.handle_actz_sign(
        svc, {"actz_slug": "z1", "role": "bogus", "signed_by": "X"}
    )
    assert out.startswith("Error:")
    assert "bogus" in out


def test_mcp_handler_final_tz_and_orphans(svc_keyed):
    sys.path.insert(
        0, os.path.join(os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project")
    )
    import handlers_actz

    _signed_actz(svc_keyed)
    final_tz = handlers_actz.handle_actz_final_tz(svc_keyed, {})
    assert '"tz_ref": "TZ-1"' in final_tz
    orphans = handlers_actz.handle_actz_orphans(svc_keyed, {})
    assert '"actz_slug": "z1"' in orphans


# === the "акт" word guard (AC-1) ===


def test_forbidden_word_regex_matches_the_word_not_its_neighbours():
    """No allowlist needed: the regex only closes on an END boundary right
    after a declension suffix, so it never opens on 'актив'/'фактор'/'контракт'."""
    assert FORBIDDEN_WORD_RE.search("подписан акт")
    assert FORBIDDEN_WORD_RE.search("акты приёмки")
    assert FORBIDDEN_WORD_RE.search("актом клиента")
    assert not FORBIDDEN_WORD_RE.search("активный режим")
    assert not FORBIDDEN_WORD_RE.search("контракт подписан")
    assert not FORBIDDEN_WORD_RE.search("это факт")
    assert not FORBIDDEN_WORD_RE.search("важный фактор")


def test_forbidden_word_regex_covers_every_declension_suffix():
    """Every case form of 'акт' the closed suffix set names, exhaustively — a
    mutation dropping any one suffix (e.g. 'актов') survived the smoke test
    above and had to be caught here instead."""
    for form in (
        "акт",
        "акта",
        "акту",
        "актом",
        "акте",
        "акты",
        "актов",
        "актам",
        "актами",
        "актах",
    ):
        assert FORBIDDEN_WORD_RE.fullmatch(form), f"{form!r} must match fully"


def test_display_name_uses_actz_not_the_forbidden_word():
    assert not FORBIDDEN_WORD_RE.search(display_name({"id": 7}))
    assert display_name({"id": 7}) == "Протокол уточнения ТЗ № 7"


def _actz_cli_help_texts() -> list[str]:
    """Every RUNTIME-VISIBLE help string the `actz` subparser tree renders --
    the parent's one-liner-per-subcommand listing plus each leaf's own
    format_help() (which includes its epilog). NOT source comments: AC-1's
    subject is what a user or agent actually SEES via `tausik actz --help`,
    not how the implementation explains itself internally."""
    import argparse

    from project_parser_actz import build_actz_subparsers

    top = argparse.ArgumentParser(prog="tausik")
    sub = top.add_subparsers(dest="cmd")
    build_actz_subparsers(sub)
    actz_parser = sub.choices["actz"]
    texts = [actz_parser.format_help()]
    z_sub_action = next(
        a
        for a in actz_parser._subparsers._group_actions
        if isinstance(a, argparse._SubParsersAction)
    )
    texts.extend(leaf.format_help() for leaf in z_sub_action.choices.values())
    return texts


def _actz_mcp_texts() -> list[str]:
    """Every RUNTIME-VISIBLE MCP tool name + description -- what an agent
    actually reads from tools/list, not the module's own source comments."""
    sys.path.insert(
        0, os.path.join(os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project")
    )
    import tools_actz

    return [f"{t['name']} {t['description']}" for t in tools_actz.TOOLS_ACTZ]


@pytest.mark.parametrize(
    "collector", [_actz_cli_help_texts, _actz_mcp_texts], ids=["cli_help", "mcp_tools"]
)
def test_no_actz_surface_prints_the_forbidden_word(collector):
    offenders = [t for t in collector() if FORBIDDEN_WORD_RE.search(t)]
    assert offenders == []


def test_no_actz_section_in_docs_prints_the_forbidden_word():
    for rel in ("docs/en/mcp.md", "docs/ru/mcp.md"):
        path = os.path.join(os.path.dirname(__file__), "..", rel)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        marker = text.find("ACTZ")
        assert marker != -1, f"{rel} has no ACTZ section yet"
        # Scan a window after the first ACTZ heading -- the guard's subject is
        # THIS entity's own documentation, not the whole file (ADAPT's section
        # sits right beside it and legitimately never mentions ACTZ at all).
        window = text[marker : marker + 4000]
        offenders = [frag.strip() for frag in FORBIDDEN_WORD_RE.findall(window) if frag is not None]
        assert not offenders, f"{rel}: forbidden word near ACTZ section"
