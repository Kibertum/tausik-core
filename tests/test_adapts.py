"""v16r-adapt: RENAR ADAPT artifacts (full §7, path A — no 'lite').

Covers the v36 migration, header/body CRUD, closed-7 finding categories + 2
signature roles (CHECK + service validation), forward interpretation §7.4.3,
dual signature §7.5 (architect ed25519 over canonical body), delta workflow §7.6
+ §7.6.4 dangling-ref guard, task_show integration, FTS5 search, CLI parser
wiring and MCP dispatch.
"""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from backend_migrations import run_migrations  # noqa: E402
from backend_schema import SCHEMA_VERSION  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from service_adapts import FINDING_CATEGORIES, LINK_TARGETS, SIGNATURE_ROLES  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "adapt.db")))
    yield s
    s.be.close()


@pytest.fixture
def svc_keyed(tmp_path):
    """Service whose project_dir carries a FRESH ephemeral ed25519 keypair.

    Generated in-fixture (not copied from the repo) so the architect-signature
    tests are fully self-contained and pass on any clean clone / CI environment.
    """
    import crypto_keys

    crypto_keys.init_keys(str(tmp_path))
    s = ProjectService(SQLiteBackend(str(tmp_path / "adapt.db")))
    s._project_dir = str(tmp_path)  # convenience: tests pass this as project_dir
    yield s
    s.be.close()


def _seed_task(svc, slug: str = "t1") -> None:
    svc.epic_add("e1", "Epic 1")
    svc.story_add("e1", "s1", "Story 1")
    svc.task_add("s1", slug, "Task 1", role="developer", goal="g")


def _full_adapt(svc, slug: str = "a1") -> None:
    svc.adapt_create(slug, "Auth ADAPT", "TZ-2026-001")
    svc.adapt_interpret(slug, "TZ-3.1", "User logs in", "OAuth2 PKCE", "login", "reset out")
    svc.adapt_finding(slug, "gap", "No MFA stated", tz_ref="TZ-3.1")


# === AC2: closed lists are exactly the RENAR closed sets ===


def test_finding_categories_closed_seven():
    assert FINDING_CATEGORIES == (
        "contradiction",
        "gap",
        "hidden-assumption",
        "feasibility",
        "regulatory",
        "terminology",
        "scope",
    )
    assert len(FINDING_CATEGORIES) == 7


def test_signature_roles_and_link_targets_closed():
    assert SIGNATURE_ROLES == ("client", "architect")
    assert LINK_TARGETS == ("task", "spec")


# === AC1: migration v36 + fresh-DB schema ===


def test_schema_version_at_least_36():
    assert SCHEMA_VERSION >= 36


def test_migration_v36_creates_tables_clean(tmp_path):
    path = str(tmp_path / "v35.db")
    conn = sqlite3.connect(path)
    conn.isolation_level = None
    conn.execute("CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.execute("INSERT INTO meta VALUES('schema_version', '35')")
    conn.execute("CREATE TABLE tasks(slug TEXT PRIMARY KEY)")
    # ALTER target for v38 — run_migrations walks every version up to current,
    # not just the one under test here.
    conn.execute("CREATE TABLE verification_runs(id INTEGER PRIMARY KEY AUTOINCREMENT)")

    new_ver = run_migrations(conn, 35)
    assert new_ver >= 36

    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {
        "adapts",
        "adapt_interpretations",
        "adapt_findings",
        "adapt_signatures",
        "adapt_links",
        "fts_adapts",
    } <= tables
    trigs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
    assert {"adapts_ai", "adapts_ad", "adapts_au"} <= trigs
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    conn.close()


def test_fresh_backend_has_adapt_tables(svc):
    rows = svc.be._q(
        "SELECT name FROM sqlite_master WHERE type IN ('table','trigger') AND name LIKE '%adapt%'"
    )
    names = {r["name"] for r in rows}
    assert {"adapts", "adapt_interpretations", "adapt_findings", "adapt_signatures"} <= names
    assert {"adapts_ai", "adapts_ad", "adapts_au"} <= names


# === AC1/AC2: header + body CRUD ===


def test_create_and_show(svc):
    msg = svc.adapt_create("a1", "Auth", "TZ-2026-001")
    assert "a1" in msg and "draft" in msg
    a = svc.adapt_show("a1")
    assert a["tz_ref"] == "TZ-2026-001"
    assert a["status"] == "draft"
    assert a["interpretations"] == [] and a["findings"] == []


def test_interpret_and_finding_recorded(svc):
    _full_adapt(svc)
    a = svc.adapt_show("a1")
    assert a["interpretations"][0]["engineering_interpretation"] == "OAuth2 PKCE"
    assert a["findings"][0]["category"] == "gap"


def test_delete_cascades_body(svc):
    _full_adapt(svc)
    svc.adapt_delete("a1")
    assert svc.adapt_list() == []


# === AC2 NEGATIVE: closed lists enforced at both layers ===


def test_invalid_category_rejected_at_service(svc):
    svc.adapt_create("a1", "T", "TZ-1")
    with pytest.raises(ServiceError, match="Invalid finding category"):
        svc.adapt_finding("a1", "bogus", "x")


def test_invalid_category_rejected_at_db(svc):
    svc.adapt_create("a1", "T", "TZ-1")
    with pytest.raises(sqlite3.IntegrityError):
        svc.be.finding_add("a1", "bogus", "x")


def test_invalid_role_rejected_at_db(svc):
    svc.adapt_create("a1", "T", "TZ-1")
    with pytest.raises(sqlite3.IntegrityError):
        svc.be.signature_set("a1", "reviewer", "X", "2026-01-01T00:00:00Z")


def test_mandatory_interpretation_fields(svc):
    svc.adapt_create("a1", "T", "TZ-1")
    with pytest.raises(ServiceError, match="mandatory"):
        svc.adapt_interpret("a1", "TZ-3.1", "", "interp", "in", "out")


def test_duplicate_slug_rejected(svc):
    svc.adapt_create("a1", "T", "TZ-1")
    with pytest.raises(ServiceError, match="already exists"):
        svc.adapt_create("a1", "T2", "TZ-2")


def test_missing_tz_ref_rejected(svc):
    with pytest.raises(ServiceError, match="tz_ref"):
        svc.adapt_create("a1", "T", "")


# === AC4: dual signature §7.5 ===


def test_dual_signature_completes_and_verifies(svc_keyed):
    _full_adapt(svc_keyed)
    pd = svc_keyed._project_dir
    svc_keyed.adapt_sign("a1", "client", "Acme", pd)
    assert svc_keyed.be.adapt_get("a1")["status"] == "draft"  # one sig only
    svc_keyed.adapt_sign("a1", "architect", "Claude", pd)
    assert svc_keyed.be.adapt_get("a1")["status"] == "signed"
    res = svc_keyed.adapt_verify("a1", pd)
    assert res["signed"] and res["valid"]


def test_architect_signature_without_key_is_service_error(svc, tmp_path):
    """NEGATIVE: architect sign without a project key is a friendly error, not a traceback."""
    _full_adapt(svc)
    with pytest.raises(ServiceError, match="project key"):
        svc.adapt_sign("a1", "architect", "X", str(tmp_path / "nokey"))


def test_body_frozen_after_sign(svc_keyed):
    _full_adapt(svc_keyed)
    pd = svc_keyed._project_dir
    svc_keyed.adapt_sign("a1", "client", "Acme", pd)
    svc_keyed.adapt_sign("a1", "architect", "Claude", pd)
    with pytest.raises(ServiceError, match="frozen"):
        svc_keyed.adapt_finding("a1", "scope", "late finding")


def test_verify_unsigned_reports_not_signed(svc):
    _full_adapt(svc)
    res = svc.adapt_verify("a1")
    assert res["signed"] is False and res["valid"] is False


def test_resign_after_signed_is_rejected(svc_keyed):
    """NEGATIVE: a fully-signed ADAPT is sealed — re-signing would silently
    overwrite the record; the caller must create a delta instead (§7.6)."""
    _full_adapt(svc_keyed)
    pd = svc_keyed._project_dir
    svc_keyed.adapt_sign("a1", "client", "Acme", pd)
    svc_keyed.adapt_sign("a1", "architect", "Claude", pd)
    with pytest.raises(ServiceError, match="already signed"):
        svc_keyed.adapt_sign("a1", "architect", "Mallory", pd)


# === AC5: delta workflow §7.6 + §7.6.4 dangling-ref guard ===


def test_delta_supersedes_parent(svc):
    svc.adapt_create("a1", "T", "TZ-1")
    svc.adapt_delta("a1", "a1-d1", "T delta", "TZ-1-delta-1")
    assert svc.be.adapt_get("a1")["status"] == "superseded"
    d = svc.adapt_show("a1-d1")
    assert d["parent_adapt"] == "a1" and d["delta_n"] == 1


def test_link_to_superseded_is_fatal(svc):
    _seed_task(svc)
    svc.adapt_create("a1", "T", "TZ-1")
    svc.adapt_delta("a1", "a1-d1", "T delta", "TZ-1-delta-1")
    with pytest.raises(ServiceError, match="FATAL"):
        svc.adapt_link("a1", "task", "t1")
    # the live delta links fine
    assert "linked" in svc.adapt_link("a1-d1", "task", "t1")


def test_sign_superseded_rejected(svc):
    svc.adapt_create("a1", "T", "TZ-1")
    svc.adapt_delta("a1", "a1-d1", "T delta", "TZ-1-delta-1")
    with pytest.raises(ServiceError, match="superseded"):
        svc.adapt_sign("a1", "client", "X")


# === AC3 NEGATIVE: linking integrity ===


def test_link_to_missing_task_errors(svc):
    svc.adapt_create("a1", "T", "TZ-1")
    with pytest.raises(ServiceError, match="Task 'ghost' not found"):
        svc.adapt_link("a1", "task", "ghost")


def test_link_to_missing_spec_errors(svc):
    svc.adapt_create("a1", "T", "TZ-1")
    with pytest.raises(ServiceError, match="SPEC 'ghost' not found"):
        svc.adapt_link("a1", "spec", "ghost")


def test_duplicate_link_rejected(svc):
    _seed_task(svc)
    svc.adapt_create("a1", "T", "TZ-1")
    svc.adapt_link("a1", "task", "t1")
    with pytest.raises(ServiceError, match="already links"):
        svc.adapt_link("a1", "task", "t1")


def test_invalid_target_type_rejected(svc):
    svc.adapt_create("a1", "T", "TZ-1")
    with pytest.raises(ServiceError, match="Invalid target_type"):
        svc.adapt_link("a1", "epic", "e1")


# === AC6: task_show integration ===


def test_task_show_includes_linked_adapts(svc):
    _seed_task(svc)
    svc.adapt_create("a1", "Auth", "TZ-1")
    svc.adapt_link("a1", "task", "t1")
    task = svc.task_show("t1")
    assert "adapts" in task
    assert task["adapts"][0]["slug"] == "a1"


def test_adapt_links_to_spec(svc):
    svc.spec_add("auth-spec", "ARCH", "Auth spec", "v1")
    svc.adapt_create("a1", "Auth", "TZ-1")
    svc.adapt_link("a1", "spec", "auth-spec")
    assert svc.adapts_for_target("spec", "auth-spec")[0]["slug"] == "a1"


# === FTS5 search ===


def test_fts_search_finds_adapt(svc):
    svc.adapt_create("payments-adapt", "Payment gateway reconciliation", "TZ-9")
    assert any(h["slug"] == "payments-adapt" for h in svc.adapt_search("gateway"))


def test_fts_delete_trigger_removes_entry(svc):
    svc.adapt_create("ghost", "Ephemeral interpretation", "TZ-9")
    assert svc.adapt_search("Ephemeral")
    svc.adapt_delete("ghost")
    assert svc.adapt_search("Ephemeral") == []


def test_malformed_fts_query_is_friendly_error(svc):
    svc.adapt_create("a1", "T", "TZ-1")
    with pytest.raises(ServiceError, match="Invalid search query"):
        svc.adapt_search('"unbalanced')


# === CLI parser wiring ===


def test_cli_parser_accepts_adapt_create():
    from project_parser import build_parser

    parser = build_parser()
    ns = parser.parse_args(["adapt", "create", "a1", "Title", "--tz-ref", "TZ-1"])
    assert ns.tz_ref == "TZ-1"


def test_cli_parser_rejects_bad_finding_category():
    from project_parser import build_parser

    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["adapt", "finding", "a1", "bogus", "desc"])


# === MCP dispatch ===


def test_mcp_dispatch_registers_adapt_tools():
    sys.path.insert(
        0, os.path.join(os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project")
    )
    import handlers_adapt

    expected = {
        "tausik_adapt_create",
        "tausik_adapt_interpret",
        "tausik_adapt_finding",
        "tausik_adapt_sign",
        "tausik_adapt_show",
        "tausik_adapt_list",
        "tausik_adapt_delta",
        "tausik_adapt_link",
        "tausik_adapt_search",
    }
    assert expected <= set(handlers_adapt.ADAPT_HANDLERS)


def test_mcp_handler_create_and_show(svc):
    sys.path.insert(
        0, os.path.join(os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project")
    )
    import handlers_adapt

    out = handlers_adapt.handle_adapt_create(svc, {"slug": "a1", "title": "T", "tz_ref": "TZ-1"})
    assert "created" in out
    shown = handlers_adapt.handle_adapt_show(svc, {"slug": "a1"})
    assert '"tz_ref": "TZ-1"' in shown


def test_mcp_handler_invalid_category_returns_error(svc):
    sys.path.insert(
        0, os.path.join(os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project")
    )
    import handlers_adapt

    handlers_adapt.handle_adapt_create(svc, {"slug": "a1", "title": "T", "tz_ref": "TZ-1"})
    out = handlers_adapt.handle_adapt_finding(
        svc, {"adapt_slug": "a1", "category": "bogus", "description": "x"}
    )
    assert out.startswith("Error:")
