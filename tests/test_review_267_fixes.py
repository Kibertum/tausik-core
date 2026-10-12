"""Fixes for the two adversarial reviews of session #267
(session-267-review-findings-gates-and-closure,
 session-267-review-findings-migrations-and-backend)."""

from __future__ import annotations

import os
import sqlite3
import sys
import time

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.join(_ROOT, "harness", "claude", "mcp", "codebase-rag"))

import backend_migrations  # noqa: E402
import rag_indexer  # noqa: E402
import rag_languages  # noqa: E402
from metric_methods import method_lines, targets  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "r.db")))
    s.epic_add("e", "E")
    s.story_add("e", "s", "S")
    s.task_add("s", "t", "T", role="developer", goal="g")
    yield s
    s.be.close()


# --- gates and closure ---------------------------------------------------------


@pytest.mark.parametrize("rx", ["(a+)+$", r"(\w+\s?)*$", "(x{2,})+"])
def test_a_nested_quantifier_regex_is_refused_at_load(tmp_path, rx):
    (tmp_path / ".tausik").mkdir()
    (tmp_path / ".tausik" / "config.json").write_text(
        '{"rag": {"boundaries": {"x": %s}}}' % __import__("json").dumps(rx), encoding="utf-8"
    )
    langs = rag_languages.load(str(tmp_path), {})
    assert "x" not in langs.boundaries
    assert any("nests quantifiers" in p for p in langs.problems)


def test_a_long_line_cannot_make_a_boundary_regex_run_long():
    import re

    slow = re.compile(r"^(a|aa)+$")  # not refused by the nested check; bounded by the line cap
    started = time.monotonic()
    rag_indexer._chunk_by_boundaries(["a" * 5000 + "!"], slow)
    assert time.monotonic() - started < 5


def test_a_dead_end_naming_a_missing_task_is_refused(svc):
    with pytest.raises(ServiceError, match="does not exist"):
        svc.dead_end("Tried X", "Because Y", task_slug="typo-slug")
    assert svc.be._q1("SELECT COUNT(*) AS n FROM memory")["n"] == 0


def test_a_target_without_a_bound_is_not_used_and_the_report_survives():
    tg, notes = targets({"metric_targets": {"fpsr": {"basis": "hand-edited, no bound"}}})
    assert tg["fpsr"]["min"] == 85.0
    assert any("neither min nor max" in n for n in notes)
    method_lines({"fpsr": 90.0, "der": 3.0}, {"metric_targets": {"fpsr": {"basis": "b"}}})


def test_a_failing_escalation_is_said_out_loud(capsys):
    class _Broken:
        def meta_get(self, _k):
            raise RuntimeError("meta table gone")

    method_lines({"fpsr": 50.0, "der": 3.0}, {}, _Broken())
    assert "metric escalation for fpsr failed" in capsys.readouterr().err


# --- migrations and backend ----------------------------------------------------


def test_a_failed_version_reread_releases_the_write_lock(tmp_path):
    db = str(tmp_path / "m.db")
    conn = sqlite3.connect(db, isolation_level=None)
    conn.execute("CREATE TABLE meta (key TEXT, value TEXT)")
    conn.execute("INSERT INTO meta VALUES ('schema_version', 'garbage')")
    with pytest.raises(ValueError):
        backend_migrations.run_migrations(conn, max(backend_migrations.MIGRATIONS) - 1)
    assert not conn.in_transaction
    other = sqlite3.connect(db, timeout=1, isolation_level=None)
    other.execute("BEGIN IMMEDIATE")
    other.execute("ROLLBACK")


def test_a_read_only_close_does_not_checkpoint(tmp_path, caplog):
    db = str(tmp_path / "w.db")
    writer = SQLiteBackend(db)
    writer.epic_add("e2", "E")  # pending WAL from a live writer
    reader = SQLiteBackend(db, read_only=True)
    reader.close()
    writer.close()
    assert "checkpoint failed" not in caplog.text


def test_the_decision_listing_makes_no_per_row_graph_query(svc, monkeypatch):
    for i in range(5):
        svc.decide(f"D{i}", task_slug="t" if i % 2 else None)
    calls: list = []
    monkeypatch.setattr(svc.be, "edge_list", lambda *a, **k: calls.append(1) or [])
    svc.decisions(task="t")
    svc.decisions(status="active")
    assert calls == []


def test_a_failed_edge_leaves_no_decision(svc, monkeypatch):
    old = int(svc.decide("Old").split("#")[1].split(" ")[0])

    def boom(*_a, **_k):
        raise RuntimeError("edge write failed")

    monkeypatch.setattr(svc, "memory_link", boom)
    with pytest.raises(RuntimeError):
        svc.decide("New", rationale="because", supersedes=old)
    assert [d["decision"] for d in svc.decisions(status="all")] == ["Old"]
