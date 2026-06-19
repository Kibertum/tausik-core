"""r14-brain-metrics: brain_events table + tausik metrics integration."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


@pytest.fixture()
def conn(tmp_path):
    db = tmp_path / "test.db"
    from project_backend import SQLiteBackend  # type: ignore

    be = SQLiteBackend(str(db))
    yield be
    be.close()


def test_brain_events_table_exists(conn):
    cols = {
        row[1]
        for row in conn._conn.execute("PRAGMA table_info(brain_events)").fetchall()
    }
    assert {"id", "session_id", "event_type", "query", "result_count", "ts"} <= cols


def test_brain_event_record_validates_type(conn):
    with pytest.raises(ValueError):
        conn.brain_event_record("invalid_type")


def test_brain_event_metrics_empty(conn):
    m = conn.brain_event_metrics()
    assert m["session"] == {
        "searches": 0,
        "hits": 0,
        "writes": 0,
        "ignored": 0,
        "hit_rate_pct": 0.0,
    }
    assert m["all_time"]["hit_rate_pct"] == 0.0


def test_brain_event_metrics_aggregation(conn):
    sid = conn.session_start()
    conn.brain_event_record("search", query="q1", result_count=0, session_id=sid)
    conn.brain_event_record("search", query="q2", result_count=2, session_id=sid)
    conn.brain_event_record("hit", query="q2", result_count=2, session_id=sid)
    conn.brain_event_record("write", query="ww", session_id=sid)
    m = conn.brain_event_metrics(session_id=sid)
    s = m["session"]
    assert s["searches"] == 2
    assert s["hits"] == 1
    assert s["writes"] == 1
    assert s["hit_rate_pct"] == 50.0


def test_log_brain_event_helper_writes_into_project_db(tmp_path, monkeypatch):
    from project_backend import SQLiteBackend

    project = tmp_path / "proj"
    (project / ".tausik").mkdir(parents=True)
    db = project / ".tausik" / "tausik.db"
    be = SQLiteBackend(str(db))
    be.close()
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project))

    from brain_metrics_log import log_brain_event, read_metrics

    assert log_brain_event("search", query="x", result_count=3) is True
    assert log_brain_event("hit", query="x", result_count=3) is True
    metrics = read_metrics()
    assert metrics is not None
    assert metrics["all_time"]["searches"] == 1
    assert metrics["all_time"]["hits"] == 1
    assert metrics["all_time"]["hit_rate_pct"] == 100.0


def test_log_brain_event_no_db_returns_false(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.delenv("TAUSIK_PROJECT_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    from brain_metrics_log import log_brain_event

    assert log_brain_event("search") is False
