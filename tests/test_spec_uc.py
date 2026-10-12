"""SPEC-UC is the twelfth SPEC type (RENAR 1.1 §8.3, §8.5.12; task G2 of 1.10)."""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from backend_init import init_schema  # noqa: E402
from backend_migrations_v64 import maybe_widen_spec_types_v64  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from service_specs import SPEC_TYPES  # noqa: E402
from spec_uc import check_uc_body  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402

_GOOD = """---
role: agent
---
1. The agent opens the task list — SPEC-UI-tasks#1
2. The agent starts the first task — SPEC-PROC-start#2
"""


@pytest.fixture
def svc(tmp_path):
    (tmp_path / ".tausik").mkdir()
    s = ProjectService(SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db")))
    yield s, tmp_path
    s.be.close()


def test_the_closed_list_has_twelve_with_uc():
    assert len(SPEC_TYPES) == 12 and SPEC_TYPES[-1] == "UC"


def test_a_complete_uc_is_accepted(svc):
    s, root = svc
    (root / "uc.md").write_text(_GOOD, encoding="utf-8")
    s.spec_add("uc-start", "UC", "Start a task", "1.0", content_ref="uc.md")
    assert s.be.spec_get("uc-start")["type"] == "UC"


def test_a_step_without_a_ref_is_refused(svc):
    """NEGATIVE: §8.5.12.1 — a step without a statement ref breaks completeness."""
    s, root = svc
    (root / "uc.md").write_text(_GOOD + "3. The agent is happy\n", encoding="utf-8")
    with pytest.raises(ServiceError, match="step 3 has no statement ref"):
        s.spec_add("uc-bad", "UC", "Bad", "1.0", content_ref="uc.md")
    assert s.be.spec_get("uc-bad") is None


def test_a_uc_without_role_or_body_is_refused(svc):
    """NEGATIVE: no role; no body at all."""
    s, root = svc
    (root / "norole.md").write_text("1. x — SPEC-UI-a#1\n", encoding="utf-8")
    with pytest.raises(ServiceError, match="role"):
        s.spec_add("uc-norole", "UC", "No role", "1.0", content_ref="norole.md")
    with pytest.raises(ServiceError, match="readable body"):
        s.spec_add("uc-nobody", "UC", "No body", "1.0")


def test_role_must_be_human_or_agent():
    assert any(
        "not one of human | agent" in p for p in check_uc_body("role: robot\n1. x SPEC-UI-a#1\n")
    )


def test_an_older_specs_table_is_widened_and_keeps_rows(tmp_path):
    """The upgrade path: an 11-type CHECK is rebuilt to twelve, rows kept."""
    conn = sqlite3.connect(str(tmp_path / "old.db"))
    conn.isolation_level = None
    init_schema(conn)
    ddl = conn.execute("SELECT sql FROM sqlite_master WHERE name='specs'").fetchone()[0]
    old = ddl.replace(", 'UC'", "").replace("CREATE TABLE specs", "CREATE TABLE specs_old")
    conn.execute(old)
    conn.execute(
        "INSERT INTO specs_old(slug,type,title,version,created_at,updated_at) "
        "VALUES('a','DOC','t','1','x','x')"
    )
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute("DROP TABLE specs")
    conn.execute("ALTER TABLE specs_old RENAME TO specs")
    assert maybe_widen_spec_types_v64(conn) == 1
    assert "'UC'" in conn.execute("SELECT sql FROM sqlite_master WHERE name='specs'").fetchone()[0]
    assert conn.execute("SELECT slug, type FROM specs").fetchall() == [("a", "DOC")]
    assert maybe_widen_spec_types_v64(conn) == 0  # idempotent
    conn.close()
