"""v16r-spec-types: RENAR SPEC artifacts (9 closed types).

Covers the v35 migration, CRUD + closed-type/relation enforcement (CHECK +
service validation), task↔SPEC linking, task_show integration, FTS5 search,
CLI parser wiring, and MCP dispatch.
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
from service_specs import SPEC_RELATIONS, SPEC_TYPES  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402


def _make_service(db_path: str) -> ProjectService:
    return ProjectService(SQLiteBackend(db_path))


@pytest.fixture
def svc(tmp_path):
    s = _make_service(str(tmp_path / "spec.db"))
    yield s
    s.be.close()


def _seed_task(svc, slug: str = "t1") -> None:
    svc.epic_add("e1", "Epic 1")
    svc.story_add("e1", "s1", "Story 1")
    svc.task_add("s1", slug, "Task 1", role="developer", goal="g")


# === AC: closed list is exactly the 9 RENAR types ===


def test_spec_types_closed_nine():
    assert SPEC_TYPES == ("ARCH", "API", "DATA", "INT", "PROC", "UI", "AI", "SEC", "OPS")
    assert len(SPEC_TYPES) == 9


# === AC: migration v35 applies cleanly on a v34 DB ===


def test_schema_version_at_least_35():
    assert SCHEMA_VERSION >= 35


def test_migration_v35_creates_tables_clean(tmp_path):
    """A v34-shaped DB migrates forward with specs + task_specs + FTS + triggers
    and no FK violations."""
    path = str(tmp_path / "v34.db")
    conn = sqlite3.connect(path)
    conn.isolation_level = None  # autocommit — run_migrations drives its own BEGIN
    conn.execute("CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.execute("INSERT INTO meta VALUES('schema_version', '34')")
    conn.execute("CREATE TABLE tasks(slug TEXT PRIMARY KEY)")  # FK target

    new_ver = run_migrations(conn, 34)
    assert new_ver >= 35

    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"specs", "task_specs", "fts_specs"} <= tables
    trigs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
    assert {"specs_ai", "specs_ad", "specs_au"} <= trigs
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    conn.close()


def test_fresh_backend_has_spec_tables(svc):
    """Fresh-DB schema (not migration path) also creates the tables + triggers."""
    rows = svc.be._q(
        "SELECT name FROM sqlite_master WHERE type IN ('table','trigger') AND (name LIKE '%spec%')"
    )
    names = {r["name"] for r in rows}
    assert {"specs", "task_specs", "fts_specs"} <= names
    assert {"specs_ai", "specs_ad", "specs_au"} <= names


# === AC: CRUD ===


def test_add_and_list_and_show(svc):
    msg = svc.spec_add("auth-arch", "ARCH", "Auth architecture", "v1", "docs/auth.md")
    assert "auth-arch" in msg and "ARCH" in msg
    rows = svc.spec_list()
    assert [r["slug"] for r in rows] == ["auth-arch"]
    shown = svc.spec_show("auth-arch")
    assert shown["type"] == "ARCH"
    assert shown["version"] == "v1"
    assert shown["content_ref"] == "docs/auth.md"
    assert shown["status"] == "draft"
    assert shown["linked_tasks"] == []


def test_type_is_uppercased(svc):
    svc.spec_add("low", "api", "Lowercase type accepted + normalized", "v1")
    assert svc.spec_show("low")["type"] == "API"


def test_list_filtered_by_type(svc):
    svc.spec_add("a", "ARCH", "A", "v1")
    svc.spec_add("b", "API", "B", "v1")
    assert {r["slug"] for r in svc.spec_list("API")} == {"b"}


def test_update_mutable_fields(svc):
    svc.spec_add("s", "DATA", "T", "v1")
    svc.spec_update("s", title="New", version="v2", status="active")
    shown = svc.spec_show("s")
    assert shown["title"] == "New"
    assert shown["version"] == "v2"
    assert shown["status"] == "active"


def test_delete_cascades_links(svc):
    _seed_task(svc)
    svc.spec_add("s", "SEC", "T", "v1")
    svc.spec_link("t1", "s")
    svc.spec_delete("s")
    assert svc.spec_list() == []
    # link is gone (FK cascade) — task no longer references the SPEC
    assert svc.specs_for_task("t1") == []


# === NEGATIVE: closed list enforced at both layers ===


def test_invalid_type_rejected_at_service(svc):
    with pytest.raises(ServiceError, match="Invalid SPEC type"):
        svc.spec_add("x", "FOO", "T", "v1")


def test_invalid_type_rejected_at_db(svc):
    """The closed list is also a hard DB CHECK — a backend insert bypassing the
    service still cannot store a bogus type."""
    with pytest.raises(sqlite3.IntegrityError):
        svc.be.spec_add("x", "FOO", "T", "v1")


def test_duplicate_slug_rejected(svc):
    svc.spec_add("dup", "OPS", "T", "v1")
    with pytest.raises(ServiceError, match="already exists"):
        svc.spec_add("dup", "OPS", "T2", "v2")


def test_missing_version_rejected(svc):
    with pytest.raises(ServiceError, match="version is required"):
        svc.spec_add("nv", "UI", "T", "")


# === NEGATIVE: linking integrity ===


def test_link_to_missing_spec_errors(svc):
    """Linking a task to a nonexistent SPEC is a loud error, not a silent link."""
    _seed_task(svc)
    with pytest.raises(ServiceError, match="SPEC 'ghost' not found"):
        svc.spec_link("t1", "ghost")


def test_link_to_missing_task_errors(svc):
    svc.spec_add("s", "INT", "T", "v1")
    with pytest.raises(ServiceError, match="Task 'ghost' not found"):
        svc.spec_link("ghost", "s")


def test_duplicate_link_rejected(svc):
    _seed_task(svc)
    svc.spec_add("s", "PROC", "T", "v1")
    svc.spec_link("t1", "s")
    with pytest.raises(ServiceError, match="already links"):
        svc.spec_link("t1", "s")


def test_invalid_relation_rejected(svc):
    _seed_task(svc)
    svc.spec_add("s", "AI", "T", "v1")
    with pytest.raises(ServiceError, match="Invalid relation"):
        svc.spec_link("t1", "s", "supersedes")


def test_both_relations_supported(svc):
    _seed_task(svc)
    svc.spec_add("s", "ARCH", "T", "v1")
    for rel in SPEC_RELATIONS:
        svc.spec_link("t1", "s", rel)
    rels = {r["relation"] for r in svc.specs_for_task("t1")}
    assert rels == set(SPEC_RELATIONS)


# === AC: task_show integration ===


def test_task_show_includes_linked_specs(svc):
    _seed_task(svc)
    svc.spec_add("s", "ARCH", "Auth", "v1", "docs/auth.md")
    svc.spec_link("t1", "s", "implements")
    task = svc.task_show("t1")
    assert "specs" in task
    assert task["specs"][0]["slug"] == "s"
    assert task["specs"][0]["relation"] == "implements"


def test_spec_show_lists_linked_tasks(svc):
    _seed_task(svc)
    svc.spec_add("s", "ARCH", "T", "v1")
    svc.spec_link("t1", "s")
    linked = svc.spec_show("s")["linked_tasks"]
    assert [t["slug"] for t in linked] == ["t1"]


# === AC: FTS5 search ===


def test_fts_search_finds_spec(svc):
    svc.spec_add("payments-api", "API", "Payment gateway integration", "v1")
    hits = svc.spec_search("gateway")
    assert any(h["slug"] == "payments-api" for h in hits)


def test_fts_search_reflects_update(svc):
    svc.spec_add("s", "API", "Original title", "v1")
    svc.spec_update("s", title="Renamed widget endpoint")
    assert any(h["slug"] == "s" for h in svc.spec_search("widget"))
    assert not svc.spec_search("Original")


def test_fts_delete_trigger_removes_entry(svc):
    """specs_ad must drop the FTS row — a deleted SPEC is no longer searchable."""
    svc.spec_add("ghost-api", "API", "Ephemeral endpoint", "v1")
    assert svc.spec_search("Ephemeral")
    svc.spec_delete("ghost-api")
    assert svc.spec_search("Ephemeral") == []


def test_malformed_fts_query_is_friendly_error(svc):
    """NEGATIVE: an unbalanced FTS5 query is a ServiceError, not a raw crash."""
    svc.spec_add("s", "API", "T", "v1")
    with pytest.raises(ServiceError, match="Invalid search query"):
        svc.spec_search('"unbalanced')


# === NEGATIVE: validation surfaces as ServiceError (no raw traceback) ===


def test_invalid_slug_is_service_error(svc):
    """validate_slug raises ValueError internally; the service must convert it so
    the CLI/MCP ServiceError catch handles it instead of leaking a traceback."""
    with pytest.raises(ServiceError):
        svc.spec_add("Bad Slug!", "API", "T", "v1")


def test_overlong_version_rejected(svc):
    with pytest.raises(ServiceError):
        svc.spec_add("s", "API", "T", "v" * 200)


# === AC: CLI parser wiring ===


def test_cli_parser_accepts_spec_add():
    from project_parser import build_parser

    parser = build_parser()
    ns = parser.parse_args(
        ["spec", "add", "s", "ARCH", "Title", "--version", "v1", "--content-ref", "d.md"]
    )
    assert ns.type == "ARCH"
    assert ns.version == "v1"
    assert ns.content_ref == "d.md"


def test_cli_parser_rejects_bad_type():
    from project_parser import build_parser

    parser = build_parser()
    with pytest.raises(SystemExit):  # argparse choices rejection
        parser.parse_args(["spec", "add", "s", "FOO", "Title", "--version", "v1"])


# === AC: MCP dispatch ===


def test_mcp_dispatch_registers_spec_tools():
    sys.path.insert(
        0, os.path.join(os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project")
    )
    import handlers_spec

    expected = {
        "tausik_spec_add",
        "tausik_spec_list",
        "tausik_spec_show",
        "tausik_spec_update",
        "tausik_spec_delete",
        "tausik_spec_link",
        "tausik_spec_unlink",
        "tausik_spec_search",
    }
    assert expected <= set(handlers_spec.SPEC_HANDLERS)


def test_mcp_handler_add_and_show(svc):
    sys.path.insert(
        0, os.path.join(os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project")
    )
    import handlers_spec

    out = handlers_spec.handle_spec_add(
        svc, {"slug": "s", "type": "ARCH", "title": "T", "version": "v1"}
    )
    assert "created" in out
    shown = handlers_spec.handle_spec_show(svc, {"slug": "s"})
    assert '"type": "ARCH"' in shown


def test_mcp_handler_invalid_type_returns_error(svc):
    sys.path.insert(
        0, os.path.join(os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project")
    )
    import handlers_spec

    out = handlers_spec.handle_spec_add(
        svc, {"slug": "x", "type": "FOO", "title": "T", "version": "v1"}
    )
    assert out.startswith("Error:")
