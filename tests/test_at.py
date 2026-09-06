"""at-acceptance-tests-derived-by-an-isolated-agent: RENAR AT artifacts (Sec8A).

Covers the v54 migration, header CRUD, mandatory tz_text/generated_by,
freshness checking against final_tz_snapshot (fresh / stale-changed /
stale-orphaned), FTS5 search, CLI parser wiring, MCP dispatch, and the
at_freshness gate (red on a stale AT, green when everything matches).
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
from tausik_utils import ServiceError  # noqa: E402


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "at.db")))
    yield s
    s.be.close()


@pytest.fixture
def svc_keyed(tmp_path):
    """Service whose project_dir carries a FRESH ephemeral ed25519 keypair,
    needed to sign the ACTZ points AT is checked against."""
    import crypto_keys

    crypto_keys.init_keys(str(tmp_path))
    s = ProjectService(SQLiteBackend(str(tmp_path / "at.db")))
    s._project_dir = str(tmp_path)
    yield s
    s.be.close()


def _signed_governing_point(svc_keyed, actz_slug: str, tz_ref: str, text: str) -> str:
    """Create + fully sign an ACTZ point; returns its completed_at."""
    svc_keyed.actz_create(actz_slug, "T", "TZ-src")
    svc_keyed.actz_point_add(actz_slug, 1, tz_ref, text)
    svc_keyed.actz_sign(actz_slug, "architect", "A.", svc_keyed._project_dir)
    svc_keyed.actz_sign(actz_slug, "client", "C.")
    row = next(r for r in svc_keyed.final_tz_snapshot() if r["tz_ref"] == tz_ref)
    return row["completed_at"]


# === schema / migration ===


def test_schema_version_at_least_54():
    from backend_migrations import MIGRATIONS

    assert SCHEMA_VERSION >= 54
    assert 54 in MIGRATIONS


def test_migration_v54_creates_tables_clean(tmp_path):
    path = str(tmp_path / "premigration.db")
    conn = sqlite3.connect(path)
    conn.isolation_level = None
    conn.execute("CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.execute("INSERT INTO meta VALUES('schema_version', '35')")
    conn.execute("CREATE TABLE tasks(slug TEXT PRIMARY KEY)")
    conn.execute("CREATE TABLE verification_runs(id INTEGER PRIMARY KEY AUTOINCREMENT)")
    conn.execute("CREATE TABLE decisions(id INTEGER PRIMARY KEY AUTOINCREMENT)")
    conn.execute("CREATE TABLE memory(id INTEGER PRIMARY KEY AUTOINCREMENT)")

    new_ver = run_migrations(conn, 35)
    assert new_ver >= 54
    tables = {
        r[0]
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ats'")
    }
    assert tables == {"ats"}
    conn.close()


def test_fresh_backend_has_at_table(svc):
    row = svc.be._q1("SELECT name FROM sqlite_master WHERE name='ats'")
    assert row is not None
    idx = svc.be._q1("SELECT name FROM sqlite_master WHERE name='idx_ats_tz_ref'")
    assert idx is not None


# === header CRUD + validation ===


def test_create_and_show(svc):
    svc.at_create(
        "at-1",
        "TZ-3.1",
        "Клиент видит статус заказа в реальном времени.",
        "Открыть заказ, видеть статус",
        "2026-01-01T00:00:00Z",
        "orchestrator-1",
    )
    a = svc.at_show("at-1")
    assert a["tz_ref"] == "TZ-3.1"
    assert a["generated_by"] == "orchestrator-1"


@pytest.mark.parametrize(
    "field_index,field_name",
    [(2, "tz_text"), (5, "generated_by")],
    ids=["tz_text", "generated_by"],
)
def test_mandatory_field_rejected_when_blank(svc, field_index, field_name):
    args = ["at-1", "TZ-3.1", "text", "scenario", "2026-01-01T00:00:00Z", "orch"]
    args[field_index] = ""
    with pytest.raises(ServiceError, match=field_name):
        svc.at_create(*args)
    # A refused create must not have left a partial row.
    assert svc.at_list() == []


def test_duplicate_slug_rejected(svc):
    svc.at_create("at-1", "TZ-3.1", "text", "scenario", "2026-01-01T00:00:00Z", "orch")
    with pytest.raises(ServiceError):
        svc.at_create("at-1", "TZ-3.2", "text2", "scenario2", "2026-01-02T00:00:00Z", "orch")
    # The refused duplicate must not have touched the original row.
    assert svc.at_show("at-1")["tz_ref"] == "TZ-3.1"


def test_delete(svc):
    svc.at_create("at-1", "TZ-3.1", "text", "scenario", "2026-01-01T00:00:00Z", "orch")
    svc.at_delete("at-1")
    with pytest.raises(ServiceError):
        svc.at_show("at-1")


def test_delete_missing_errors(svc):
    svc.at_create("at-1", "TZ-3.1", "text", "scenario", "2026-01-01T00:00:00Z", "orch")
    with pytest.raises(ServiceError):
        svc.at_delete("no-such-at")
    # The refused delete of a DIFFERENT slug must not touch the real record.
    assert svc.at_show("at-1")["tz_ref"] == "TZ-3.1"


def test_list_filtered_by_tz_ref(svc):
    svc.at_create("at-1", "TZ-3.1", "text", "scenario", "2026-01-01T00:00:00Z", "orch")
    svc.at_create("at-2", "TZ-3.2", "text2", "scenario2", "2026-01-01T00:00:00Z", "orch")
    assert [r["slug"] for r in svc.at_list("TZ-3.1")] == ["at-1"]
    assert len(svc.at_list()) == 2


# === FTS5 search ===


def test_fts_search_finds_at(svc):
    svc.at_create(
        "at-1",
        "TZ-3.1",
        "Клиент видит статус заказа.",
        "сценарий проверки",
        "2026-01-01T00:00:00Z",
        "orch",
    )
    rows = svc.at_search("статус")
    assert any(r["slug"] == "at-1" for r in rows)


def test_malformed_fts_query_is_friendly_error(svc):
    svc.at_create("at-1", "TZ-3.1", "text", "scenario", "2026-01-01T00:00:00Z", "orch")
    with pytest.raises(ServiceError, match="unterminated"):
        svc.at_search('"unterminated')
    # The failed query must not have deleted or altered anything.
    assert svc.at_show("at-1")["tz_ref"] == "TZ-3.1"


# === freshness (§8A property 2) ===


def test_freshness_empty_when_no_at_records(svc):
    assert svc.at_check_freshness() == []
    assert svc.at_list() == []


def test_freshness_fresh_when_source_matches_current(svc_keyed):
    completed_at = _signed_governing_point(svc_keyed, "z1", "TZ-3.1", "governing clause text")
    svc_keyed.at_create("at-1", "TZ-3.1", "governing clause text", "scenario", completed_at, "orch")
    assert svc_keyed.at_check_freshness() == []


def test_freshness_stale_when_governing_point_changed(svc_keyed):
    old_completed_at = _signed_governing_point(svc_keyed, "z1", "TZ-3.1", "old text")
    svc_keyed.at_create("at-1", "TZ-3.1", "old text", "scenario", old_completed_at, "orch")

    # A later ACTZ supersedes the clause with a NEWER governing point.
    svc_keyed.actz_create("z2", "T2", "TZ-src2")
    svc_keyed.actz_point_add("z2", 1, "TZ-3.1", "new text")
    svc_keyed.actz_sign("z2", "architect", "A.", svc_keyed._project_dir)
    svc_keyed.actz_sign("z2", "client", "C.")
    svc_keyed.be._ex(
        "UPDATE actz_signatures SET signed_at=? WHERE actz_slug=?",
        ("2027-01-01T00:00:00Z", "z2"),
    )

    stale = svc_keyed.at_check_freshness()
    assert len(stale) == 1
    assert stale[0]["slug"] == "at-1"
    assert "changed" in stale[0]["reason"]


def test_freshness_stale_when_tz_ref_orphaned(svc):
    svc.at_create(
        "at-1", "TZ-9.9", "text nobody signed", "scenario", "2026-01-01T00:00:00Z", "orch"
    )
    stale = svc.at_check_freshness()
    assert len(stale) == 1
    assert "no signed governing point" in stale[0]["reason"]


def test_freshness_check_one_slug(svc_keyed):
    completed_at = _signed_governing_point(svc_keyed, "z1", "TZ-3.1", "text")
    svc_keyed.at_create("at-1", "TZ-3.1", "text", "scenario", completed_at, "orch")
    svc_keyed.at_create("at-2", "TZ-9.9", "orphan", "scenario", "2026-01-01T00:00:00Z", "orch")
    assert svc_keyed.at_check_freshness("at-1") == []
    stale = svc_keyed.at_check_freshness("at-2")
    assert len(stale) == 1 and stale[0]["slug"] == "at-2"


def test_freshness_check_missing_slug_errors(svc):
    with pytest.raises(ServiceError) as exc:
        svc.at_check_freshness("no-such-at")
    assert "no-such-at" in str(exc.value)


# === CLI parser wiring ===


def test_cli_parser_accepts_at_create():
    from project_parser import build_parser

    parser = build_parser()
    ns = parser.parse_args(
        [
            "at",
            "create",
            "at-1",
            "TZ-3.1",
            "text",
            "scenario",
            "--as-of",
            "2026-01-01T00:00:00Z",
            "--by",
            "orch",
        ]
    )
    assert ns.tz_ref == "TZ-3.1"
    assert ns.source_as_of == "2026-01-01T00:00:00Z"


def test_cli_parser_accepts_check_freshness_without_slug():
    from project_parser import build_parser

    parser = build_parser()
    ns = parser.parse_args(["at", "check-freshness"])
    assert ns.slug is None


# === MCP dispatch: full parity ===


def test_mcp_dispatch_registers_all_at_tools():
    sys.path.insert(
        0, os.path.join(os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project")
    )
    import handlers_at

    expected = {
        "tausik_at_create",
        "tausik_at_show",
        "tausik_at_list",
        "tausik_at_delete",
        "tausik_at_search",
        "tausik_at_check_freshness",
    }
    assert expected == set(handlers_at.AT_HANDLERS)


def test_mcp_tool_schema_matches_handler_set():
    sys.path.insert(
        0, os.path.join(os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project")
    )
    import handlers_at
    import tools_at

    tool_names = {t["name"] for t in tools_at.TOOLS_AT}
    assert tool_names == set(handlers_at.AT_HANDLERS)
    assert len(tool_names) == 6


def test_mcp_handler_create_and_check_freshness(svc_keyed):
    sys.path.insert(
        0, os.path.join(os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project")
    )
    import handlers_at

    completed_at = _signed_governing_point(svc_keyed, "z1", "TZ-3.1", "text")
    out = handlers_at.handle_at_create(
        svc_keyed,
        {
            "slug": "at-1",
            "tz_ref": "TZ-3.1",
            "tz_text": "text",
            "scenario": "scenario",
            "source_as_of": completed_at,
            "generated_by": "orch",
        },
    )
    assert "recorded" in out
    fresh = handlers_at.handle_at_check_freshness(svc_keyed, {})
    assert fresh == "[]"


# === at_freshness gate (warn) ===


def test_at_freshness_gate_reds_on_a_stale_at(tmp_path, monkeypatch):
    import crypto_keys
    import gate_at_freshness
    import project_config

    crypto_keys.init_keys(str(tmp_path))
    db_path = str(tmp_path / "tausik.db")
    be = SQLiteBackend(db_path)
    svc = ProjectService(be)
    svc._project_dir = str(tmp_path)
    svc.at_create("at-1", "TZ-9.9", "orphan text", "scenario", "2026-01-01T00:00:00Z", "orch")
    be.close()

    monkeypatch.setattr(project_config, "get_db_path", lambda: db_path)
    outcome = gate_at_freshness.run_at_freshness_gate({}, [])
    assert outcome.outcome == gate_at_freshness.gate_outcome.FAILED
    assert "at-1" in outcome.detail


def test_at_freshness_gate_greens_when_at_matches_the_current_final_tz(tmp_path, monkeypatch):
    import crypto_keys
    import gate_at_freshness
    import project_config

    crypto_keys.init_keys(str(tmp_path))
    db_path = str(tmp_path / "tausik.db")
    be = SQLiteBackend(db_path)
    svc = ProjectService(be)
    svc._project_dir = str(tmp_path)
    completed_at = _signed_governing_point(svc, "z1", "TZ-3.1", "text")
    svc.at_create("at-1", "TZ-3.1", "text", "scenario", completed_at, "orch")
    be.close()

    monkeypatch.setattr(project_config, "get_db_path", lambda: db_path)
    outcome = gate_at_freshness.run_at_freshness_gate({}, [])
    assert outcome.outcome == gate_at_freshness.gate_outcome.PASSED


def test_at_freshness_gate_not_applicable_without_a_database(tmp_path, monkeypatch):
    import gate_at_freshness
    import project_config

    missing = str(tmp_path / "nope.db")
    monkeypatch.setattr(project_config, "get_db_path", lambda: missing)
    outcome = gate_at_freshness.run_at_freshness_gate({}, [])
    assert outcome.outcome == gate_at_freshness.gate_outcome.NOT_APPLICABLE
    assert outcome.blocks is False
