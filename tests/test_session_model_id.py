"""r14-senar-model-id: capture agent model on session_start.

SENAR Rule 10.13 mandates recording AI model id + version per session so
First-Pass Success Rate / cost / throughput can be re-calibrated when the
user switches between models mid-project. v1.4 adds two columns to the
`sessions` table and reads them from env vars on `session_start`.

These tests exercise the env-var precedence chain and confirm the schema
columns exist.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))


@pytest.fixture
def conn(tmp_path):
    from project_backend import SQLiteBackend

    db = str(tmp_path / "t.db")
    be = SQLiteBackend(db)
    yield be
    be.close()


def test_sessions_table_has_model_columns(conn):
    cur = conn._conn.execute("PRAGMA table_info(sessions)")
    cols = {row[1] for row in cur.fetchall()}
    assert {"model_id", "model_version"} <= cols


def test_session_start_with_no_env(conn, monkeypatch):
    for key in (
        "TAUSIK_AGENT_MODEL",
        "TAUSIK_AGENT_MODEL_VERSION",
        "CLAUDE_MODEL",
        "ANTHROPIC_MODEL",
        "OPENAI_MODEL",
        "CURSOR_MODEL",
    ):
        monkeypatch.delenv(key, raising=False)
    sid = conn.session_start()
    row = conn._conn.execute(
        "SELECT model_id, model_version FROM sessions WHERE id=?", (sid,)
    ).fetchone()
    assert row[0] is None and row[1] is None


def test_session_start_picks_tausik_env_first(conn, monkeypatch):
    monkeypatch.setenv("TAUSIK_AGENT_MODEL", "claude-opus-4.7")
    monkeypatch.setenv("CLAUDE_MODEL", "should-be-ignored")
    monkeypatch.setenv("TAUSIK_AGENT_MODEL_VERSION", "2026-05-01")
    sid = conn.session_start()
    row = conn._conn.execute(
        "SELECT model_id, model_version FROM sessions WHERE id=?", (sid,)
    ).fetchone()
    assert row[0] == "claude-opus-4.7"
    assert row[1] == "2026-05-01"


def test_session_start_falls_back_to_host_envs(conn, monkeypatch):
    monkeypatch.delenv("TAUSIK_AGENT_MODEL", raising=False)
    monkeypatch.setenv("CLAUDE_MODEL", "claude-3.5-sonnet")
    sid = conn.session_start()
    row = conn._conn.execute(
        "SELECT model_id FROM sessions WHERE id=?", (sid,)
    ).fetchone()
    assert row[0] == "claude-3.5-sonnet"
