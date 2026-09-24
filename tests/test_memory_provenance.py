"""A memory record says where its claim came from, and "observed" is earned
(memory-record-does-not-say-where-its-claim-came-from)."""

from __future__ import annotations

import hashlib
import os
import sqlite3
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from backend_init import init_schema  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from render_memory import memory_lint_lines  # noqa: E402
from service_knowledge_aggregates import build_memory_block  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402

FIXTURE = os.path.join(_ROOT, "tests", "fixtures", "schema_v44_tausik_1_8_0.sql")


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "p.db")))
    s.epic_add("e", "Epic")
    s.story_add("e", "s", "Story")
    s.task_add("s", "t", "T", role="developer", goal="g")
    yield s
    s.be.close()


def _prov(svc, msg):
    mid = int(msg.split("#", 1)[1].split(" ", 1)[0])
    return svc.be.memory_get(mid)["provenance"]


def test_the_default_is_the_weak_claim(svc):
    assert _prov(svc, svc.memory_add("gotcha", "G", "Something breaks")) == "inferred"


def test_observed_naming_a_test_or_a_run_stays_observed(svc):
    m1 = svc.memory_add("gotcha", "G1", "Shown by tests/test_x.py::test_y", provenance="observed")
    m2 = svc.memory_add("gotcha", "G2", "Seen in verify #2775", provenance="observed")
    assert _prov(svc, m1) == "observed" and _prov(svc, m2) == "observed"


def test_observed_linked_to_a_task_with_a_journal_stays_observed(svc):
    svc.task_log("t", "measured 123 ms on the live run")
    msg = svc.memory_add("pattern", "P", "Cache helps", task_slug="t", provenance="observed")
    assert _prov(svc, msg) == "observed"


def test_observed_backed_by_nothing_is_downgraded_out_loud(svc):
    msg = svc.memory_add("gotcha", "G", "Trust me, it is slow", provenance="observed")
    assert _prov(svc, msg) == "inferred"
    assert "DOWNGRADED to inferred" in msg


def test_told_is_kept_and_an_unknown_value_is_refused(svc):
    assert _prov(svc, svc.memory_add("context", "C", "Owner said so", provenance="told")) == "told"
    with pytest.raises(ServiceError, match="provenance must be one of"):
        svc.memory_add("context", "C", "x", provenance="certain")


def test_the_block_marks_inferred_records_and_not_observed_ones(svc):
    svc.memory_add("convention", "Guess", "No evidence")
    svc.memory_add("convention", "Measured", "tests/test_x.py::test_y", provenance="observed")
    block = build_memory_block(svc.be)
    assert "≈ Guess" in block
    assert "Measured" in block and "≈ Measured" not in block


def test_lint_counts_inferred_records_as_debt(svc):
    svc.memory_add("gotcha", "G", "No evidence")
    svc.memory_add("gotcha", "O", "tests/test_x.py::test_y", provenance="observed")
    assert any("Provenance debt: 1 of 2" in ln for ln in memory_lint_lines(svc))


def test_the_migration_keeps_every_row_and_marks_it_inferred(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "old.db"))
    conn.executescript(open(FIXTURE, encoding="utf-8").read())
    for i in range(25):
        conn.execute(
            "INSERT INTO memory(type,title,content,created_at,updated_at) VALUES(?,?,?,?,?)",
            ("gotcha", f"T{i}", f"C{i}", "2026-08-01T00:00:00Z", "2026-08-01T00:00:00Z"),
        )
    conn.commit()
    cols = "id,type,title,content,created_at"
    before = conn.execute(f"SELECT {cols} FROM memory ORDER BY id").fetchall()
    init_schema(conn)
    after = conn.execute(f"SELECT {cols} FROM memory ORDER BY id").fetchall()
    assert len(after) == len(before) == 25
    digest = lambda rows: hashlib.sha256(repr(rows).encode()).hexdigest()  # noqa: E731
    assert digest(after) == digest(before)
    assert conn.execute("SELECT DISTINCT provenance FROM memory").fetchall() == [("inferred",)]
